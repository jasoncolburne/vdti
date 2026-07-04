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
  lock).** The effective SAID is a deterministic hash over the **live tips** the node holds for a
  prefix (the canonical tip + any **unresolved** competing branch tip — a live fork at-or-above the
  derived seal, or a below-seal **privileged** spine fork) — sorted `said` ASC, length-prefixed,
  concatenated, domain-tagged. A **settled** branch does **not** enter: a repair-**condemned** branch is
  already moved **out of the live table** into non-canonical retained storage (so the live-table leaf
  enumeration never sees it), and a below-seal-inert **content** leaf is excluded by the seal filter.
  This is the **real branch-derived digest** (live-tips; Jason 2026-07-03) replacing kels'
  `divergent:{prefix}` / `contested:{prefix}` synthetic — a pure live-tip fingerprint, decoupled from
  the `forked`/`disputed`/Active verdict **value** (the verdict is the separate walk; the seal it reads
  is itself derived from the held events, so both the digest and the verdict are pure functions of the
  held set — inv 13 / area-vdtid-services §1e; this is the cold-F2 / warm-H1 fix).
  - **The machinery already exists in kels** (`lib/derive/src/lib.rs::compute_prefix_effective_said`):
    leaves are found with a **`NOT EXISTS` correlated anti-join** (an event whose `said` is no other
    event's `previous`), `ORDER BY said ASC`; single live tip → its SAID, ≥ 2 → a deterministic hash. The
    vdti delta: (a) replace the synthetic (`divergent:`/`contested:` string hash, ~:344/:354) with
    `hash(sorted live-tip SAIDs)`; (b) drop the `is_contest` branch (no `Cnt` kind); (c) add the window
    bound below; (d) **filter the enumerated leaves to the live ones — every tip at serial ≥ the last
    clean seal** (Jason 2026-07-03). The **last clean seal** is the most recent seal-advancer with no
    competing privileged sibling at-or-below it — the trust boundary: a live fork sits above it; a
    resolved / buried loser is sealed past it (below it); and a competing **privileged** branch *retreats*
    the clean-seal line beneath itself (pre-seal verifiability, area-kel), so "≥ the clean seal" pulls the
    dispute back in — **F5 falls out of the query for free** (a privileged fork is always reported because
    it drags the clean-seal line down below it). A condemned **content** subtree is already off the live
    table (the repair moved it to non-canonical retained storage), so a grown dead branch never surfaces —
    only **content** ever leaves the digest; a privileged event never settles. All the query primitives
    exist in `verifiable-storage-rs` (`not_exists` + `CorrelatedSubquery`, `group_by` +
    `having_count_gt`, `gte`, `order_by`). **The last clean seal is cheap** — query (1)'s duplicate-serial
    check already finds any competing-privileged serial, so the clean-seal floor is the most recent
    seal-advancer above the last such fork (usually just `last_seal_advancing_event`).
  - **Why it must be bounded — the log is indefinite.** kels' anti-join and its divergence check
    (`GROUP BY prefix, serial HAVING COUNT > 1`, `services/kels/src/repository.rs:212`) scan the **whole
    prefix** — O(chain length). On an indefinite vdti chain that is unacceptable per computation, and
    the effective SAID is computed constantly (token-reuse gate, anti-entropy compare, post-merge). The
    **seal cap makes it boundable**: a live fork sits ≤ 64/lineage above a seal, an origination-frozen fork
    sits at the very top (nothing originates new work onto a live fork), and resolved-fork losers are archived
    out of the live table (below the last clean seal the live table is linear → no leaves there). So **every
    live tip lands within one page below `MAX(serial)`**. Bound both queries to
    `serial > MAX(serial) − MINIMUM_PAGE_SIZE` (129, generous — all leaves are within ≤ 64 of the seal
    and the seal is within ≤ 64 of `MAX`) and they stay O(page).
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
    forked (the `Divergent (sealed)` case) — otherwise it could anchor on a forked seal unaware. Once
    a divergence is seen at a position the cap bounds it — you need only the one competing event, never a
    rescan.
  - **The deep-mint case is not a digest gap (D1).** A privileged event injected **below a node's
    already-advanced seal** (harvested-reserve, `vdti-repair-completeness-proof.md` D1) is not reached by
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
- **The mesh-encryption key lives in a per-witness key SEL (RESOLVED 2026-06-26 — was the S-E / `Fcp`
  open item).** The `ML-KEM-1024` public key sits in a SEL owned by a **degenerate per-device IEL** — a
  single-member IEL (`members = [the witness KEL]`) **derived from the witness KEL prefix** (+ a purpose
  discriminator), not separately incepted, so it does **not** break the `Fcp` founder bootstrap (the
  device KEL incepts first via `Fcp`, its degenerate IEL derives, that IEL owns the key SEL; "reincept"
  = re-derive from the recovered KEL). Its kind set excludes `Evl` (≈ `{Icp, Ixn, Rpr, Trm}`), and the general **post-delta `|roster| ≥ 1`** rule (inv 12) forbids cutting the sole
  member (a `Rpr`-cut — the other roster-mutating kind since the 2026-06-30 fold — computes `1 + 0 − 1 = 0`,
  rejected), so it can neither grow (no `Evl`) nor shrink → roster immutable (no new field; singleton → all
  thresholds 1). Discovery: federation roster
  → witness KEL prefixes → derive each degenerate IEL → its key SEL. See
  `vdti-area-federation-witnessing.md` §1e.
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
- **`fork`-root membership test — the formal candidate-selection (2026-07-02).** Moved here out of
  `protocol-doctrine.md` §Divergence, which keeps only the prose ("the named root is a competing child of
  `v_{d-1}`, off the retained chain") — a formal selection rule is implementation, not doctrine. The
  verifier walks the **full-span** retained chain (from the repair's `previous` down to at least the
  pre-fork seal — at most one extra page), identifying the fork point `v_{d-1}` and the retained set
  (`walkback`). The committed `fork` root (a single SAID — the list collapsed 2026-07-02, inv 4) must satisfy
  **`root.parent = v_{d-1} ∧ root ∉ walkback`** — a
  competing (losing) child of the single fork point, off the retained chain. *Single fork point:* the chain
  freezes at the first fork, so there is one active divergence and the root is a sibling at `v_{d-1}`.
  *Why full-span:* it is load-bearing for the `root ∉ walkback` half and the censorship guard — a walk
  truncated at the divergence serial would read `v_{d-1}` and every trunk ancestor as off-chain, letting a
  root condemn the canonical chain. The parent test is **`= v_{d-1}`**, not the looser `∈ walkback` an
  earlier doctrine draft carried (the loose form is a safe superset but not the model).
