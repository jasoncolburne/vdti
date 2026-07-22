# VDTI — implementation notes

Build-shaping decisions that constrain the implementation but are **not** doctrine (they don't belong
in `docs/design/`, which states product-agnostic structural rules). Concise; one entry per decision.
Doctrine is the leading edge — these follow it.

## Storage

- **Event logs are Postgres.** Structured / variable-length data never inlines in an event body; it
  lives in a SAD referenced by a scalar SAID (the `manifest` SADs, `pin`, the roster/witnesses/clock
  config SADs). See `project_vdti_event_log_storage_constraint`.
- **Witness receipts: flat Postgres rows, keyed by `(prefix, serial)`.** A receipt is a single
  witness signature over `(prefix, serial, event-said)` — small and flat — so payload + index sit in
  one table; serving a page's receipts is one index scan, no second fetch. Fall back to **SAD storage
  + a thin-pointer table** (`(prefix, serial) → receipt-SAID`) **only if** receipts grow non-flat
  (aggregated/batched, or referencing a SAD). We are not in that case yet.
- **Serving bundles receipts with the page.** The server serves a chain page **with** its receipts
  (cheap index scan, no verification — never trust the DB); the verifier re-checks signatures. Don't
  push the *lookup* to the verifier: the divergence model needs a one-branch holder to get the
  competing-branch SAIDs from the receipts, so a separate round-trip would add detection latency.

- **Effective-SAID computation — on-demand, bounded by the seal cap (no side table, no dedicated
  lock).** The effective SAID is derived from the **live tips** the node holds for a
  prefix (the canonical tip + any **unresolved** competing branch tip — a live fork at-or-above the
  derived seal; a **below-seal** sealed straggler is **not** a live tip — it is dropped, backdate-safe
  (revised 2026-07-11)): **a single confirmed tip → its real SAID; no
  single tip → a type-tagged `synthetic` marker recoupled to the verdict** (`forked:{prefix}` / `disputed:{prefix}`,
  qualified by position), **NOT a hash over the competing tips** (that set is adversarially extensible under
  dishonest signers → flood-unstable; a set-independent synthetic is flood-stable, still distinct from any
  single-tip SAID so it still triggers anti-entropy, and is verdict-sufficient — REVERSES the earlier "real
  branch-derived digest over live tips", area-vdtid-services §1e). A **settled** branch does **not** enter: a
  **buried** loser is already moved **out of the live table** into non-canonical retained storage (so the
  live-table leaf enumeration never sees it), and a below-seal-inert **content** leaf is excluded by the seal
  filter. The verdict is the separate held-set walk (the seal it reads is itself derived from the held events
  — inv 13 / area-vdtid-services §1e), and the synthetic **carries** that verdict value; both are pure
  functions of the held set (the cold-F2 / warm-H1 fix).
  - **The synthetic's exact bytes are a cross-node protocol constant (SS-2).** The "qualified by position" encoding —
    the type tag, the `prefix`, and the position field, with a fixed delimiter and ordering — must be
    **byte-identical across conforming implementations**: two impls holding the same event set must emit the same
    synthetic, or their effective-SAIDs mismatch permanently (a `since:seal` fetch can't close it — the events are
    identical on both sides) and anti-entropy spins (area-vdtid-services §1i). So the exact synthetic bytes are
    **pinned by the reference lib / at the encode**, not assumed. *(This resolves the apparent §1b-vs-§1i tension:
    the Rust `lib/vdti` is the **reference** impl, but the ecosystem is deliberately **multi-impl** — you audit it
    yourself and re-implement / bind from other languages — so the wire formats are pinned protocol constants, not
    "identical because there is only one lib".)*
  - **The machinery already exists in kels** (`lib/derive/src/lib.rs::compute_prefix_effective_said`):
    leaves are found with a **`NOT EXISTS` correlated anti-join** (an event whose `said` is no other
    event's `previous`), `ORDER BY said ASC`; single live tip → its SAID, ≥ 2 → **no single tip**. The
    vdti delta: (a) on ≥ 2 live tips emit the **verdict-recoupled synthetic** (`forked:{prefix}`/`disputed:{prefix}`
    qualified by position), **not** a hash over the tips (kels emitted its own `divergent:`/`contested:` string
    synthetic, ~:344/:354; vdti keeps a synthetic but recouples it to the verdict); (b) drop the `is_contest`
    branch (no `Cnt` kind); (c) add the window bound below; (d) **filter the enumerated leaves to the live ones — every tip at serial ≥ the last
    clean seal** (Jason 2026-07-03). The **last clean seal (forward-anchored, revised 2026-07-11)** is the highest
    seal-advancer with no **witnessed** competing sibling **at its own position** — found forward, **not** by
    walking its lineage backward. It is the trust boundary: a live fork sits above it; a resolved / buried loser
    is sealed past it (below it). A **below-seal** sealed straggler is **dropped** — it does **not** retreat the
    clean-seal line (that retreat was the **backdate** hole: it let a total-key-compromise adversary drag a
    dispute onto a buried position; killing it closes the backdate — pre-seal verifiability, area-kel). **F5 is a
    dispute at the _last_ seal:** the query reports a sealed fork iff the last clean seal itself carries two
    **witnessed** siblings (`disputed`), never a below-seal straggler. A **buried content** subtree is already
    off the live table (the burial moved it to non-canonical retained storage), so a grown dead branch never
    surfaces — and a below-seal sealed straggler is filtered the same way: **only a seal-vs-seal collision at the
    last seal yields `disputed`; a below-seal sealed event settles (is dropped), it does not un-settle the chain.** All the query primitives
    exist in `verifiable-storage-rs` (`not_exists` + `CorrelatedSubquery`, `group_by` +
    `having_count_gt`, `gte`, `order_by`). **The last clean seal is cheap** — query (1)'s duplicate-serial
    check finds any competing-sealed serial; the clean seal is the highest seal-advancer whose **own position**
    carries no witnessed competing sibling (forward-anchored — a below-seal competing serial is **dropped**, not
    retreated into), usually just `last_seal_advancing_event`.
  - **Why it must be bounded — the log is indefinite.** kels' anti-join and its divergence check
    (`GROUP BY prefix, serial HAVING COUNT > 1`, `services/kels/src/repository.rs:212`) scan the **whole
    prefix** — O(chain length). On an indefinite vdti chain that is unacceptable per computation, and
    the effective SAID is computed constantly (token-reuse gate, anti-entropy compare, post-merge). The
    **seal cap makes it boundable**: a live fork sits ≤ `MAXIMUM_UNSEALED_RUN`/lineage above a seal, an origination-frozen fork
    sits at the very top (nothing originates new work onto a live fork), and resolved-fork losers are archived
    out of the live table (below the last clean seal the live table is linear → no leaves there). So **every
    live tip lands within one page below `MAX(serial)`**. Bound both queries to
    `serial > MAX(serial) − MINIMUM_PAGE_SIZE` (129, generous — all leaves are within ≤ `MAXIMUM_UNSEALED_RUN` of the seal
    and the seal is within ≤ `MAXIMUM_UNSEALED_RUN` of `MAX`) and they stay O(page).
  - **Two queries** (matches kels' two-step and the expected shape): **(1)** `MAX(serial)` + a
    duplicate-serial check over the window (`GROUP BY serial HAVING COUNT > 1`, `serial > floor`) — cheap;
    a linear result (no duplicate) fast-paths to the max-serial tip's SAID. **(2)** only when divergent,
    the `NOT EXISTS` tip enumeration over the window → the sorted-tip hash. The `NOT EXISTS` subsumes the
    "end-of-a-duplicate-run tip **plus** n-tips-at-the-final-serial" enumeration uniformly (every leaf,
    canonical included), so no serial-run bookkeeping is needed.
  - **Why the 129 bound is sound (Jason 2026-07-03).** A **divergent chain is origination-frozen** — a node
    does not originate a seal-advancer onto a **live** fork it holds (inv 13; a burying seal-advancer from a
    peer resolves the fork, it does not extend it) — so a node's **own last seal always sits at-or-below any
    live fork it holds**, and `since: {own last seal}` reaches that fork within the cap. **Events can't be backdated**
    (serial is fixed by `previous`), so a fork can't be re-dated to slip below where a node looks. So all
    live divergence is caught by ordinary since-sync + the windowed digest — each node's window is
    anchored at its **own** `MAX(serial)`, so a behind node's value already differs and its own
    since-fetch pulls the fork. **Include the cursor's own siblings in the `since` response**
    (adjacent-to-cursor, Jason): a node then also learns if the seal it is anchoring on is **itself**
    forked (the `Disputed` sealed-spine-fork case) — otherwise it could anchor on a forked seal unaware. Once
    a divergence is seen at a position the cap bounds it — you need only the one competing event, never a
    rescan.
  - **The deep-mint case is not a digest gap (D1).** A sealed event injected **below a node's
    already-advanced seal** (the harvested-reserve deep-mint — inv 8) is not reached by
    that node's own since-fetch — but it is **not a hole the digest must close**: whoever **holds** it
    reads `disputed` directly (holds-and-revalidates, FORCE-by-provenance), and a node that does **not**
    hold it sits in the standing **eclipse residual** (inv 8) — if the event is witnessed it propagates
    via the beacon regardless; if it is not, a lone unwitnessed sibling forces no one's reading (inert).
    The windowed digest makes this no worse than the eclipse residual already accepted, so the bound
    holds.
  - **No side table / no dedicated advisory lock for the value.** It is a deterministic function of the
    live tips, computed on demand; the merge advisory lock (`save_with_merge`) already serializes writes,
    and the post-merge cache-update (kels `§2` pattern) is an **optional** latency optimization, not a
    correctness mechanism.

## Inter-node transport

- **All inter-node mesh traffic is encrypted** (`ML-KEM-1024` KEM + `AES-256-GCM` AEAD) — receipts
  and the events they propagate alike. The mesh is the federation roster. This is **confidentiality**,
  not trust (trust is end-verifiable: SAIDs + sigs survive any transport); it closes the
  metadata/correlation residuals (inv 16). The KEM/AEAD mechanism already exists in `../kels` for
  gossip; extend it to the data path.
- **The mesh channel is an ephemeral, signature-authenticated handshake — no published per-witness key
  (revised 2026-07-15).** Each connection runs a fresh `ML-KEM` exchange and both sides sign the
  transcript against their **witnessed** identity, so the peer is authenticated from its witnessed
  **signing** key and the channel gains **forward secrecy** —
  `docs/design/substrate/infrastructure/mesh-transport.md`. There is **no persistent published witness
  encryption key**. _(An earlier plan rooted a published per-witness key in a derived **degenerate IEL** —
  considered, then not built once the handshake removed any published key to own; the thinking, the
  deterministic nonce, and why it is not general-purpose are captured in
  `supplemental/degenerate-iel-idea.md`, retired — at the `canon-final` tag.)_
- **Push over pull.** Prefer gossiping events (push, over the encrypted mesh) to a separate inter-node
  *query* — then there is no second channel to secure, and a one-branch holder receives competing
  branches by push rather than a detection-time fetch (the sub-mesh event-gossip already does this for
  selected witnesses; extend it). The residual by-prefix fetch (a node genuinely missing a dep)
  shrinks rather than vanishes, and rides the same encrypted mesh.
- **Query content in the body, not the address (inv 16).** A prefix in the request line / query
  string leaks into common access/proxy logs, so a prefix-bearing request carries it in the body.
  **The reference implementation uses HTTP QUERY (RFC 10008)** — a safe, idempotent, body-carrying
  method — for reads, and POST for submit (a mutation).

## Merge / locking

- **Advisory locking on all log-prefix operations.** Verify-then-write paths hold a **database
  advisory lock** (the `../kels` pattern: `pg_advisory_lock` keyed by prefix) for the duration of both
  verification and write — verify the existing chain under the lock, obtain a trusted token, verify
  the incoming events against it, write, never re-querying the DB between verify and use. Doctrine
  names the *mechanism* (advisory lock); the Postgres specifics live here.
- **No `fork`-root membership test (first-seen, 2026-07-08).** The `fork` manifest role — a repair naming a
  losing branch's root — is **deleted** (no repair event, no root-condemnation; inv 4 / inv 13). Recovery is
  **burial by position + deadness-ascends**: a recovery `Rot` (KEL) / a burying seal-advancer (IEL)
  attaches at the surviving line, the per-event **seal-cap** locks the first losing sibling below the advanced
  seal, and **everything built on it dies on ascent** — so the verifier applies the seal-cap + deadness-ascent
  **directly**, with **no candidate-root to select or validate** and no full-span walkback membership test.
  *(Supersedes the 2026-07-02 formal `fork`-root candidate-selection `root.parent = v_{d-1} ∧ root ∉ walkback` —
  gone with the `fork` role.)*
