# vdti — area note: `vdtid` services (node service architecture)

**Status: FIRST CUT (2026-06-20).** The node service architecture — `vdtid` + `witnessd` over a shared
`lib/vdti`. Mirrors the kels service layout with two deliberate changes (merge chain+SAD; gossip→witnessd).
Grounded in the **kels build read on `main`** (the *mechanics* are correct; the *shape/taxonomy* is design-stale,
so mine the machinery not the kinds), the reshape design, and Jason's decomposition decisions this session.
**Not a primitive** — this note is the service/lib boundary and the cross-cutting runtime machinery.

## Sources audited (disposition)
- kels `main`: `services/{kels, sadstore, gossip, registry, mail, identity}`, `lib/{kels, gossip, derive, …}`;
  read in depth — `lib/kels/src/types/{iel,sad}/verification.rs` (tokens), `…/sync.rs` (transfer engine),
  `merge.rs` (merge), `types/deferred_deps.rs` + `services/gossip/src/pending.rs` (deferred-deps),
  `services/gossip/src/sync.rs` (anti-entropy). **Mechanics authoritative; taxonomy (`Cnt`/`Upd`/`Sea`/`Evl`)
  is the old design — do not carry.**
- kels roadmap (`kels#168`) — confirms design-ahead-of-build (many "design landed, code-side follow-up open").
- `vdti-token-store-idea.md`, `vdti-area-federation-witnessing.md` (witnessd's witness role), the SAD spec in
  this repo (custody — already covered, not re-read).
- Memories: `project_vdti_gossip_vs_witness`, `project_kels_transfer_abstractions`, `project_kels_end_verifiability`,
  `project_vdti_event_log_storage_constraint`, `project_vdti_effective_said_synthetics`,
  `feedback_verifier_is_trust_boundary`. ⚠ `project_vdti_compacted_only_submission` is **stale** on `eventsd`/`sadd`
  (§3) — fix.

## 1. Locked-candidate — the architecture

### 1a. Decomposition (mirrors kels; two changes)
- **`lib/vdti`** — the verification/merge/transfer **core**: the three primitive verifiers + their tokens, the
  transfer engine, merge, the policy/IEL resolvers, effective-SAID, deferred-deps types + collect-mode, sadstore
  custody, compaction. **Consumers link this too** (§1b). All correctness lives here; the daemons are plumbing.
- **`vdtid`** — thin daemon: **postgres chain-log + SAD store merged into one service** (kels' `kels`+`sadstore`).
  *Why merged:* events reference SADs by SAID, so a separate SAD store is an extra hop per SAD fetch — **several
  per request**; co-locating kills the hops (and keeps anchor + SAD in one txn). Hosts the API (submit / fetch /
  exists / effective-said), runs merge (advisory lock + DB txn), emits typed-422 deferred-deps.
- **`witnessd`** — kels' **`gossip` service wholesale** (renamed; "gossip" stays the *pattern* name
  [`project_vdti_gossip_vs_witness`]). Holds: gossip propagation, the deferred-deps **park/drain** map, the
  **anti-entropy** loops, and the federation **witness/receipt** role (`vdti-area-federation-witnessing.md` §1e —
  always-witness, by-`(prefix,serial)` selection). Holds HSM witness keys (destruction-on-witnessing) — isolated
  so a compromised `vdtid` can't mint receipts.
- **`clients` (cli, bench)** — build/verify locally with `lib/vdti`; **compact before submit**; maintain the
  client-side **token store** (§1d).
- **Backing stores:** postgres (chain + SAD, behind `vdtid`); Redis (park map + anti-entropy stale-tracking +
  cache, behind `witnessd`).
- **Features (creds / mail / exchange) are libraries** (`lib/vdti/*`), **never `vdtid` modules** — no
  loadable-module support; `vdtid` stays tight. (Whether any feature keeps a thin daemon like kels'
  `registry`/`mail` is §4.)

### 1b. The lib is the spine — *because consumers must verify* [end-verifiability]
End-verifiability means a consumer **cannot trust `vdtid`** — it re-verifies the data itself, with the **same**
verifier. So the verifier must be a **library both `vdtid` and consumers link**, never service-internal. The
token's unforgeability (§1c) + "the DB cannot be trusted" (§1g) mean trust attaches to the **data** (verified),
not the daemon [`feedback_verifier_is_trust_boundary`]. This is the entire reason for the lib/service split.

### 1c. Verification tokens
`KelVerification` / `IelVerification` / `SelVerification` are **unforgeable proof-of-verification** —
constructable **only** by the verifier. Structural problems = **HARD** (halt the walk); auth/policy = **SOFT**
(reported as unsatisfied via the contextual `satisfied`/`queried` sets, not raised — continue); terminal flags (`is_divergent`/`is_terminated`) from chain **content**
[inv 9]. **`queried`/`satisfied` SAIDs** = caller-bounded (consumer names the SAIDs it cares about up-front;
`satisfied` = anchored ∧ authorized ∧ before the divergence cut = valid-for-binding) [inv 8]. **`resume`** =
incremental re-hydration from a prior token. Tokens **compose**: a SEL resolves its IEL binding by consuming the
IEL token's `policy_history` + `satisfied_saids`, not by re-walking.

### 1d. Token store — vdti's refinement over kels' re-verify-every-write
Cache tokens keyed by prefix (tip SAID encoded); on use, compare the token's **full pinned-dependency
effective-SAID set** — the chain's own **and every chain it transitively pins** (the KEL(s) beneath an IEL, the
IEL beneath a SEL): **all match → reuse** (no walk); **any moved → `since`-query the new events + `resume`**
(incremental, not a re-walk). **Transitive is load-bearing (F5, 2026-06-20):** a lower-layer `Rec` breaks an
upper event while the upper chain's *own* effective-SAID doesn't move — only the transitive check catches it
(the warm-cache path for the cross-layer cascade). This **refines** "DB cannot be trusted" — the effective-SAID
is the cheap integrity gate; any tamper/advance **moves it** → re-verify. **Freshness, made *detectable* (F8,
2026-06-20):** a to-tip loss-of-trust decision (rescission / revocation / withdrawal) must use a **witnessed /
multi-source** effective-SAID (a single server can report a stale one to hide a revocation) — and the token
carries that **provenance** (single-source vs witnessed, as-of-when) as contextual info [inv 9], so "this decision
used insufficient-freshness data" is **detectable** — and when it can't be multi-source-confirmed the decision **fails-secure: REFUSE**, never proceeds on the flag (cold-5 C2, inv 8). Not a mere prose obligation. Non-to-tip / resolving checks: a
plain single-source comparison is fine.
- **Freshness composes over the whole transitive set (F-E, 2026-06-21).** The multi-source bar above is **not**
  per-"the chain" — it applies to **every chain the token transitively pins** (cred · issuer · *every* delegator
  above it · the devices beneath each identity). A single stale source on **any** one of them can hide a
  revocation, so a loss-of-trust decision confirms *each* dependency's effective-SAID multi-source (a witnessed
  effective-SAID *is* multi-source → cheap; an unwitnessed dependency **can't meet the bar → the decision fails-secure: REFUSE**, cold-5 C2). **"Is
  this chain forked / disputed?" is itself a loss-of-trust question** (a one-branch holder sees a normal
  tip; only the federation signal reveals the fork) → it goes in the multi-source bucket. And **`resume` re-runs
  the to-tip negative checks** (revocation / rescission / divergence) against the new tip whenever any pinned chain
  moves — never just staple on newer events, or it advances past a revocation. (So F9's cross-layer-break
  detection is F5+F8 over the full set, not a separate mechanism.) [inv 8]
- **Freshness is a wall-clock overlay, recomputed at decision-time (cold-12 F1).** The effective-SAID-movement gate
  certifies **structure** (unchanged ⇒ skip the re-walk); it does **not** certify **freshness**. The federation
  staleness / 365-day key-window auto-expiry (federation §1f) is **time-triggered** — it fires with **zero chain
  events**, so nothing *moves* and a movement-only reuse path would miss it. So the token caches the **freshest-valid
  witnessing-time** (data), **never** a cached `fresh`/`stale` *verdict* (which is `now`-dependent), and **every
  loss-of-trust decision recomputes staleness against current `now`** (the §1f staleness threshold + the 365-day
  auto-expiry), **independent of** whether any effective-SAID moved. A token cached pre-lapse therefore reads **stale at
  decision-time** (its witnessing-time is now ancient) → **fail-secure REFUSE**, never a reused pre-lapse 'fresh'
  verdict. (The staleness *machinery* already exists, §1f; this names the **cache/reuse** path so it can't skip the
  wall-clock re-check.)

### 1e. Effective-SAID — a real digest over LIVE held tips (NO synthetics; live-tips, Jason 2026-07-03)

The effective SAID is a **live-tip fingerprint** — a deterministic hash over the **live tips** a node holds for a
prefix in its active window: the canonical tip plus any **unresolved** competing branch the walk still reads as
live (a live fork at-or-above the seal, or a below-seal **privileged** spine fork). It answers "**has my
trust-relevant held state changed / do two nodes hold the same live events?**" and is **decoupled from the
`forked` / `disputed` / Active verdict value** (the verdict label is the separate walk, below — the digest hashes
tips, never the label).

Concretely — the query intuition: **the last clean seal → every live-table tip at serial ≥ it.** A live fork sits
above the seal; a resolved/buried loser is sealed past (below it); and a competing **privileged** branch retreats
the clean-seal line beneath itself (pre-seal verifiability, area-kel), so "≥ the clean seal" pulls it back in — the
dispute is always reported.

A **settled CONTENT** branch does **not** enter the digest: a content branch a landed repair **condemned** (its
`fork` root, or content dead by descent below it — moved off the live table by the repair), or a content sibling
**buried** below the node's derived seal (inert). These are forensic — reached by the on-chain `fork` commitment +
a by-prefix fetch, never gossiped through the digest — so a resolved fork converges on its canonical tip on
**every** node, and anti-entropy never spins on dead content (each node retains a non-deterministic ≥ 2-per-position
subset of it, so a digest that counted it could never converge — which is *why* it must be excluded).

**A privileged event never settles.** Even on a condemned or below-seal lineage, a privileged event is a competing
seal — a spine fork → `disputed` (inv 13/17: you cannot bury a rotation) — so it stays a **live tip** and enters
the digest. That is how a dispute propagates: a node holding it and a node without it compute different digests, so
anti-entropy delivers the dispute proof. Only **content** ever leaves the digest.

- **A single live tip** (a purely linear active window, or a fork already settled below the seal — Active /
  Recovered / Terminated) → that tip's real SAID (a terminated chain's is its `Trm`).
- **Multiple live tips** (an unresolved fork — a live content fork, or ≥ 1 privileged branch past it) → a
  **domain-separated hash of all live tip SAIDs, sorted** (sort ascending, length-prefix, concatenate, hash, apply
  the domain tag — distinct from a single-tip SAID so a linear and a forked state can't collide). **All** live
  tips, the canonical one included — **not** a selected subset among the live ones.

**The verdict label is separate — never hashed into the value.** A data-local walk reads `forked` (≤ 1 privileged
branch past the fork — reconcilable, pending its repair) or `disputed` (≥ 2 privileged — terminal, reincept), inv
13/17. **Both the digest and the verdict are pure functions of the held event set.** The seal the verdict reads is
itself **derived** from the held events (the highest cleanly-linear seal-advancer the node holds), **not** tracked
by arrival order — so there is no separate "own seal" input and no acceptance-order dependence. Identical held
sets therefore yield an identical verdict **and** an identical digest: a fork-first node that comes to hold a
burying seal-advancer re-reads exactly as a seal-first node does (the F2/H1 fix — a divergent chain's "frozen" is
a **merge-origination** posture, not the reading; §1i / inv 13). A settled fork drops out of both — its condemned
or buried loser leaves the live-tip set, so the digest returns to the canonical tip and the verdict returns to
Active, in lockstep, on every node.

**Boundedly computable — the seal cap** (build detail: `vdti-implementation-notes.md`). The log is indefinite, but
every **live** tip lands within one page below `MAX(serial)`: a live fork sits ≤ 64/lineage above a seal, a chain
that has stopped originating onto a live fork sits at the very top, and events can't be backdated — so the digest
is a bounded on-demand walk over `serial > MAX(serial) − MINIMUM_PAGE_SIZE`, no side table (a settled branch
already dropped out — §1e above — so nothing below the window needs hashing). A privileged event minted **below a node's own last
seal** (the harvested-reserve case, `vdti-repair-completeness-proof.md` D1) falls outside the window — **not a
digest gap**: whoever holds it reads `disputed` directly, and a node without it sits in the standing eclipse
residual (inv 8 — beacon-delivered if witnessed, inert if not), no worse than any eclipse. **Deterministic
construction is a conformance requirement** — two implementations that disagree on the bytes produce a permanent
digest mismatch; the exact bytes are the implementer's to pin, the sort / length-prefix / tag discipline is
load-bearing.

**Why real, not synthetic (supersedes the kels-inherited synthetics — retires `project_kels_effective_said_synthetics`
§vdti).** kels used `hash("forked:"/"disputed:" + prefix)` because it **could not guarantee every node holds the same
branches**, so it faked convergence with a branch-_agnostic_ value — two differently-forked nodes "agree" without
syncing. vdti has **true convergence**: witnessed events always propagate (don't-drop-witnessed + the
`since` anti-entropy, §1i), so all nodes eventually hold the same branches and compute a **real** value
over them. Not just simpler — **required and safer**:

- **Required** — the anti-entropy trigger _is_ the effective-SAID delta (§1i). For a missing branch to trigger a fetch
  the value must be **branch-sensitive**; the synthetic (branch-agnostic) would not move → would not trigger → the
  exact **R4 masking** below.
- **Safer** — under partition/eclipse two nodes with different branch sets compute **different** real values, so
  disagreement drives a fetch (reachable) or reads as multi-source loss-of-trust (**fail-secure**). The synthetic made
  them **falsely agree** (fail-open).
- **R4 caveat — RESOLVED (not annotated).** The old caveat (a branch-agnostic synthetic masks a missing branch _after_
  detection, so anti-entropy detects but cannot assemble the branches for repair) is **gone**: a real digest differs
  the instant the held branch sets differ, and `since` (§1i) assembles them.

**Convergence rests on propagation** — eventual barring partition, fail-secure under partition. Witnessed events
propagate and are never dropped, so all nodes converge to the **same held-tip set → the same digest**; the
un-witnessed adversarial flood is declined by witnesses and droppable, so it self-limits and doesn't perturb the
converged value; a direct-mode chain has no such guarantee and is **fail-secure** (different held sets → different
digests → distrust/fetch, never false agreement). Per-node state stays {Active, Divergent, Terminated};
`disputed` is the data-local terminal reading (≥ 2 privileged branches, walk-found), never a fourth per-node state.
**This digest is the universal "has state changed?" comparison** behind token-reuse, deferred-deps drain,
anti-entropy, and divergence.

### 1f. The transfer engine — the one sanctioned data-mover
One `transfer_*_events` walk with swappable **source / sink / verifier**: `verify_*` = +verifier, `forward_*` =
sink-only (no verify), `verify_*_with` = streaming callback. Source-agnostic (paged-source trait). **Merge,
anti-entropy sync, deferred-deps replay, local-verify, and CLI streaming all reuse it.** Manual pagination
bypasses tamper-evidence — forbidden [`project_kels_transfer_abstractions`].

### 1g. Merge — the write path
`vdtid` submit → fast sig-check → **merge** (advisory lock + DB txn): re-verify (or `resume` from a cached token
gated by effective-SAID, §1d) → route **normal-append** (~99%, linear non-divergent) / **new-chain** /
**full-path** (divergence / recovery / archival). **Never trusts the DB** — verification is recomputed, not cached
as trust, except behind the effective-SAID gate.

### 1h. Deferred-deps — the cross-chain race
An event can arrive before a dependency on **another** chain (independent gossip). Flow: verifier **collect-mode**
accumulates deferrable failures (`MissingIelEvent`/`MissingKelAnchor`/`MissingSadObject`) and continues soft →
`vdtid` emits a **typed 422** (`DeferredDepsResponse`: the missing deps each tagged with the dep chain's
`chainEffSaid`, plus the `transientChainState` reading for forked/disputed — the effective-SAID itself is now the real branch-derived digest, §1e) → **`witnessd` parks** the message
in Redis (`pending:msg/said/chain`, **secondaries-before-primary** so a crash orphans a self-TTLing primary, never
dangling indexes) → **drains** (replays via the transfer engine / get-post-sad) when the awaited dep commits
(pubsub) or the chain's effective-SAID moves past `eff_said_at_park`.

### 1i. Anti-entropy — silent-divergence repair
`witnessd` periodic loops (per primitive — KEL/SAD/IEL): **Phase 1 targeted** (known-stale prefixes in a Redis
hash → query peers' effective-SAIDs → sync only from peers that differ) and **Phase 2 random sampling** (random
page vs random peer; skipped if Phase 1 had work). The **effective-SAID is the compare key**; sync moves through
the transfer engine.

**The explicit branch-assembly fetch — `since: last_seal.said` (Jason 2026-07-03; resolves the R4 caveat above,
lines ~102-110).** The effective-SAID delta is only the **trigger** (it moved → re-sync this prefix — the Phase-1
compare). The **fetch** that assembles the branches the compare misses is `since: {your-own-last-seal}.said` — pull
every event after the **querier's** last seal and dedup (SAID-addressable → clean reconcile, no special-casing).
This works, **for state above your own last seal**, because of **bounded divergence**: a fork can only form after
the last seal, so `since` your seal captures the canonical tip, every **above-seal** competing/dead branch, and a
resolving `Rec` (even one that advanced a *peer's* seal past the fork — you anchor on **your** seal). But `since` is
**node-relative**: a node that advanced its **own** seal past a content fork **accept-first-learn-later** (accept
`a`, seal-advance on it, then the competing `b` arrives below the new seal) reads `b` as **inert** — you can't fork
the past, so a below-seal loser is dead and the node reads **Active** (reconciliation Divergent (sealed)). A
**fork-first** node still holding the loser at-or-above its **derived** seal reads `forked` — and converges the
instant it comes to hold a **burying seal-advancer** on the winning branch: its seal advances, the loser drops
below it → inert → the walk re-reads **Active**, **no `Rec` required** (the seal-first node's outcome, reached by a
different arrival order — the pure-walk reading, inv 13). A `Rec` is needed only for an **all-content open fork**
with no seal-advancer above it — there the repair *is* the burying seal-advancer (it archives the loser and
advances the seal). Under the **live-tips** digest (§1e) a live fork shows in **both** nodes' digests (driving the
sync that assembles it) and drops out of both the instant it is buried or repaired — digest and verdict converge
in lockstep, with **no** same-tips-different-verdict window. **So there are two channels, by design:**

- **In your active window (the last page, at-or-around your last seal) → the effective-SAID delta + `since`
  fetch** (pull). Under **live-tips** (§1e) the digest moves on any **live**-tip difference in the window — the
  canonical tip or a live-fork sibling — so the ordinary delta+`since` channel assembles an **unresolved** fork
  (exactly what needs syncing). A **settled** branch (repair-condemned, or a buried below-seal content sibling)
  does **not** move the digest — it is forensic, reached by the on-chain `fork` commitment + by-prefix fetch, not
  `since` — so a fresh sink and an evidence-holder converge on the canonical tip without either chasing the
  other's condemned branch (the cold-F1 spin, closed). Bounded: the seal-advance cap keeps your last seal ≤ 64
  events back in steady state. The `since` **response includes the cursor's own siblings** (adjacent-to-cursor),
  so you also learn if the seal you anchor on is **itself** forked (the `Divergent (sealed)` case — else you'd
  anchor on a forked seal unaware).
- **Below your own seal → beacon / eclipse residual (out of the digest).** A privileged event minted below your
  own seal (the harvested-reserve D1 case) is out of the window, so `since` can't reach it and the digest doesn't
  move for it — **not a gap**: whoever holds it reads `disputed` directly; a node without it is in the standing
  eclipse residual (inv 8), beacon-delivered if witnessed, inert if not. Old below-window forensic evidence
  (a long-buried `{Trm, content}` loser, `Rot`-buried unnamed branches) rides the on-chain `fork` commitment +
  by-prefix fetch, not `since`.

So the effective SAID stays load-bearing (cheap change-detector **and** gating value, inv 8), and a
**Merkle-root-over-all-events was considered and dropped** — the delta triggers and the seal bounds. **On a digest
mismatch `since:seal` can't close** (chiefly cross-implementation digest-encoding drift — which the pinned
deterministic construction, §1e, exists to prevent), a node escalates to a **by-prefix flat fetch** (the full
retained set) or a **beacon-driven targeted fetch** — else the anti-entropy loop spins.
- **Live vs. historical split.** While the fork is above the seal, `since: seal` carries it. Once a `Rec` buries it
  below the *new* seal, a **from-scratch** node (no prior seal) reaches the dead branches via the on-chain **`fork`
  commitment** + by-prefix fetch of the retained bodies (reconstructable from the root — inv 17 archival bounds); a
  **lagging** node with an old seal just uses `since: {old-seal}` and gets everything in one pull.

- **Send-side ordering (source → sink; the `transfer_*_events` order).** The **source** (ahead, at `seal2`) partitions
  the run for a **sink** behind at `seal1` so each sub-batch is acceptable in arrival order:
  **`seal1` (shared anchor, dedups) → Ixns(`seal1` → fork point) → the condemned branch(es) (`seal2`'s `fork` root) →
  Ixns(fork point → `seal2`) → `seal2` (the resolving `Rec`)**. Every event's `previous` is present before it lands
  (the pre-fork Ixns precede the fork roots — a mid-window fork's roots chain off them, not off `seal1`), all
  competing branches are in the sink's store before the `Rec` so its content-only guard can walk them, and the `Rec`
  lands **last**. A fork anchored right at `seal1` has an empty pre-fork run and collapses to
  `seal1 → forks → Ixns → seal2`. This is the recovered-chain specialization of send-side partitioning (a
  divergent-but-unrecovered source just omits the trailing `Rec`). The **atomic unit** — the condemned branch
  (≤ 64) + the post-fork retained window (≤ 64) + the `Rec` — fits **one `MINIMUM_PAGE_SIZE = 129` page** (area-kel);
  any pre-fork run (and, for an own-`Rot` in the retained tail, the pre-`Rot` window) rides earlier plain-linear
  pages, and a ≥ 3-branch residual fork's extra branches ride later pages (reconciliation invariant 3) — the
  whole run is **not** one page, only each seal-window atomic unit is.

## 2. Mined from kels (carries; confirm in build)
- Redis park-map **write-order invariant** (secondaries before primary; `DepRef` variant order is load-bearing
  for park-record SAID determinism — don't reorder).
- The per-primitive `verify` / `forward` / `verify_*_with` / `collect_*_saids` API surface.
- `compute_prefix_effective_said`; the post-merge cache-update + pubsub-publish path.
- Advisory-lock + single-txn-per-merge discipline; fast upfront sig/structure rejection before the lock.

## 3. Superseded — do NOT carry forward
- **The `eventsd` / `sadd` split** (vdti's *own earlier* conception, mirroring kels' `kels`/`sadstore`) →
  **merged into `vdtid`** (read-path hops, §1a). ⚠ fix `project_vdti_compacted_only_submission`.
- **kels' separate `registry` / `mail` / `identity` daemons + old taxonomy** (`Cnt`/`Upd`/`Sea`/`Evl`,
  `is_contested`) → vdti features are **libs**; taxonomy is the reshape's (`Icp`/`Ixn`/`Evl`/`Rec`/…, no `Cnt`).
- **kels' re-verify-every-write** (`completed_verification` each submit) → vdti **token-cache + effective-SAID +
  `resume`** (§1d). The kels code is the correctness baseline; the cache is the scale refinement.
- **"gossip" as a service name** → `witnessd` ("gossip" stays the pattern name).

## 4. Open / route to the adversarial pass
- **`vdtid` ↔ `witnessd` transport** — kels uses HTTP between `gossip` and `kels` services. Keep HTTP, or
  local IPC? (Affects the typed-422 / park / replay path.)
- **Redis** for park map / stale-tracking / cache — kels' choice. Carry, or reconsider a single backing store?
- **The witnessed effective-SAID source** for to-tip consuming decisions (§1d caveat) — exactly how a consumer
  obtains a federation-gossiped / multi-source effective-SAID. Cross-ref `vdti-area-federation-witnessing.md`.
- **Feature daemons** — do any features keep a thin daemon (kels `registry`/`mail` shape), or are all features
  purely client-side libs over `vdtid`? Jason leaned **tight**; confirm "no feature daemons."

## 5. Drift → land backlog
- Write the services/architecture doc under `docs/design/` (the `lib/vdti` + `vdtid` + `witnessd` boundary, the
  effective-SAID/transfer-engine spine, deferred-deps, anti-entropy).
- Define the `lib/vdti` crate layout (verifiers/tokens, transfer, merge, resolvers, effective-SAID, deferred-deps,
  custody, compaction) + the thin `vdtid`/`witnessd`/`cli` binaries.
- **Fix `project_vdti_compacted_only_submission`** (`eventsd`/`sadd` → `vdtid` + `witnessd`).
- **Archived-aware fetch (repair-archived content).** `vdtid`'s fetch endpoint must expose **archived** events
  (kels' `get_archived_events` / `get_recovery_archived_events` shape), so a walk that returns the full
  graph/history also surfaces events archived by a **repair** (a divergence cascade archives the losing branch).
  *(Updated 2026-06-21: this is no longer for detecting a delayed un-rescind — kills are always sealed now, there
  is no un-rescind, see `vdti-area-sel.md` §1. The endpoint stays for repair-archived content.)*

## 6. Confidence / what's owed
- §1a–§1i — **high** on the decomposition + machinery (grounded in the kels `main` code + Jason's decisions). The
  *mechanics* are battle-tested; vdti's deltas (merge chain+SAD, token-cache refinement, witnessd rename) are
  Jason-confirmed.
- §4 — transport + backing-store choices are confirmables, not blockers.
- Owed: Jason's confirm on §4; the build itself (this note is the map, not the territory).
