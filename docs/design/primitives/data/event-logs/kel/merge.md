# KEL Merge — Handler Rules

The KEL merge layer integrates submitted events into the existing chain. It is the protocol's
enforcement surface for the locked-portion bound, the divergence-and-repair rules, and the seal-cap.
The verifier produces a trust signal on a verification token; the merge layer composes that signal
with chain-state-dependent routing to admit or reject batches.

This doc states the merge-layer routing order, the merge outcomes, the routing rules per chain
state, and the adversarial-input diagnostic rationale that motivates the routing order. For per-kind
event rules, see [`events.md`](events.md); for the verifier walk,
[`verification.md`](verification.md); for the chain primitive, [`log.md`](log.md); for the
cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## Single entry point

`merge_events` is the single entry point for all write paths into a KEL — direct submissions, gossip
propagation, federation sync, and bootstrap atomic batches. It runs under a database advisory lock
for the duration of verification and write. Time-of-check-to-time-of-use is eliminated structurally:
the verifier reads under the same lock the merge handler will use to write (see
[§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).

The merge handler returns a `MergeOutcome` carrying the result variant, the divergence serial (when
divergence was detected), and the new tip SAID (when the chain advanced linearly).

## Merge outcomes

The merge outcomes name what happened to the chain — the structural verdicts the routing rules
produce.

| Outcome               | Chain effect                                                                                                                                                                             | Triggering condition                                                                                                                                                                                                                                                                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Accepted**          | Linear extension; new tip established; seal advances on seal-advancing kinds.                                                                                                            | Submitted events chain cleanly from the current tip on an Active chain (or from inception on an Empty chain).                                                                                                                                                                                                                                               |
| **Diverged**          | New content event lands as a fork at an earlier serial; chain transitions Active → Divergent (frozen).                                                                                   | Submitted batch contains a content event (`Ixn`) whose `previous` points at a pre-tip serial where the existing chain holds a competing event. Only the first conflicting event is written.                                                                                                                                                                 |
| **Recovered**         | Divergence resolved; the repairing branch is kept and the archival tails are committed in the `Rec`'s `folds.forks[]`; chain returns to Active; the seal advances to the `Rec`'s serial. | Submitted batch contains a `Rec` whose parent shape (branch-tip-extending or divergence-ancestor-extending) routes through the discriminator.                                                                                                                                                                                                               |
| **SiblingLocked**     | Not admitted as a canonical extension. A structurally-valid fork from a held ancestor is **retained as non-canonical evidence** (keep-all-data); no canonical state change.              | Submitted event's parent sits in the locked portion behind `lastSealAdvancingEvent` — its target serial already holds a locked sibling — or a privileged event's landing would otherwise create or join a divergence. On a Decommissioned chain this is the **sibling-to-`Dec`** case: an event sharing the `Dec`'s parent, racing the `Dec` at its serial. |
| **KelDecommissioned** | No state change. Submission rejected.                                                                                                                                                    | Submitted event chains _from_ a `Dec` (its parent's kind is `Dec`). Caught in structural validation by the kind-schema rule — no kind admits a `Dec` parent. Independent of the seal-cap; see [§Routing order](#routing-order) rule 1.                                                                                                                      |
| **RecoverRequired**   | No state change; guidance only (chain stays Divergent).                                                                                                                                  | The chain is Divergent (frozen) and the batch is neither a `Rec` nor a privileged event — only a `Rec` resolves a divergence.                                                                                                                                                                                                                               |

A subsumed variant — `RecoverRequired` — applies when the chain is Divergent and the submitted batch
is neither a `Rec` nor a privileged event (which would itself reject as `SiblingLocked`). The
routing rule signals that only `Rec` resolves divergence: a live divergence **freezes** the chain,
so no new event of any kind lands until the repair. Structurally, `RecoverRequired` is a guidance
signal; the chain state stays Divergent.

**Keep-all-data: rejected-as-canonical is not discarded.** When a `SiblingLocked` submission is a
structurally-valid fork from an ancestor the node holds, the node **retains it as non-canonical
evidence** rather than dropping it. The chain does not extend onto the competing branch, but the
proof a divergence occurred is never lost — a privileged branch is retained to ≥ 2 per spine
position, the uncommitted below-seal content flood is droppable. This is what lets any verifier read
`forked:` / `disputed:` by a data-local walk
([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair)).

## Routing order

The merge handler routes a submitted batch through four rule scopes in this **structural order**.
The order is chosen so adversarial-input diagnostics correctly name the structural
cause-of-rejection.

### 1. Structural validation

Per-kind field rules (per [`events.md` §Key-state fields](events.md#key-state-fields) and the
[event-shape reference](../event-shape.md#kel)), SAID integrity, prefix consistency, signature
shape, chain-linkage continuity. Any failure here is a structural error; the submission is rejected
regardless of chain state. The verifier walks each event and checks:

- SAID recomputation matches the declared SAID (per
  [`../../sad/said.md`](../../sad/said.md#derivation)).
- For the inception event: prefix recomputes from the canonical bytes with `said` and `prefix`
  blanked.
- Per-kind required / forbidden field presence per the
  [event-shape reference](../event-shape.md#kel) (including the `manifest` role vocabulary and the
  `previousSeal` presence rule).
- Signature shape (single-sig versus dual-sig per kind) per
  [`events.md` §Authorization and signature shapes](events.md#authorization-and-signature-shapes).
- Chain linkage: `previous` resolves to an event in the verifier's branch state; `previousSeal` (on
  a seal-advancing kind) resolves to the prior seal.
- **Kind-schema predecessor rule.** No kind admits a `Dec` parent. A submission whose parent's kind
  is `Dec` is rejected with `KelDecommissioned`. This is `Dec`-terminality expressed as a
  kind-schema property — the same class of structural rejection as a forbidden field appearing on an
  event, not a routing-order outcome. `Dec`'s kind semantics mean "no more events"; the kind-schema
  forbids any successor, so the rejection is caught here at merge entry rather than by a downstream
  rule.

### 2. Seal-cap

The submitted event's parent must sit at-or-after `lastSealAdvancingEvent` in chain order
(`parent_serial >= seal_serial`). A submission whose parent is in the locked portion is rejected as
a canonical extension with `SiblingLocked` — and, when it is a structurally-valid fork from a held
ancestor, retained as non-canonical evidence. This is the structural rule that enforces
current-state-only authority — see
[§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded) and
[`recovery.md` §Repair-event bound](recovery.md#repair-event-bound-condition-2b).

The seal-cap is **unconditional** on KEL: every event class is subject to it. A `Rec` whose
`previous.serial < seal_serial` is rejected — the locked-portion bound stops stale-authority revival
of the chain regardless of who holds the recovery key.

The seal-cap and `Dec`-terminality (rule 1's kind-schema check) are **independent** rejection
mechanisms. Both surface on a Decommissioned chain, but they catch different shapes:

- **Sibling to the `Dec`** — a submission whose parent is the `Dec`'s parent, racing the `Dec` at
  its serial. The `Dec` advanced the seal to its own serial, so the candidate's parent sits in the
  locked portion and the seal-cap rejects with `SiblingLocked`.
- **Chains from the `Dec`** — a submission whose parent IS the `Dec`. Its parent sits at the seal
  boundary, so it _passes_ the seal-cap and would append after the `Dec`. The seal-cap does **not**
  catch it; only the kind-schema rule in rule 1 does, rejecting with `KelDecommissioned`.

The kind-schema rule is load-bearing — the seal-cap does not subsume `Dec`-terminality. Without rule
1's check, an event could append after a `Dec`; the seal-cap alone would not stop it.

### 3. Fork-detect

The event's `(parent_said, serial)` is checked against the chain's existing events at that serial.
Three outcomes:

- **Privileged event whose landing would create or join a divergence** — not admitted as a canonical
  extension; retained as non-canonical evidence per
  [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair). Two subcases
  reach this:
  - **On a linear chain** with an existing event at `v_d`: a privileged event with
    `previous = v_{d-1}.said` would land as a sibling and form a divergence containing a privileged
    branch.
  - **On an already-divergent chain**: a privileged event with `previous = v_{d-1}.said` would join
    the existing fork.
- **Repair event** (`Rec`) — routes through the discriminator. Either parent shape
  (branch-tip-extending or divergence-ancestor-extending — see
  [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes)) is admitted to the
  discriminator path before any divergence check fires. The discriminator resolves the divergence;
  the outcome is `Recovered`.
- **Content event** (`Ixn`) — admitted. If a competing event already exists at the same serial, a
  fork forms and the outcome is `Diverged`. If no existing event sits at the candidate's serial, the
  event extends as a linear-chain landing.

### 4. Kind-specific authorization

For events admitted past rule 3, kind-specific authorization fires:

- **Single-sig signature verification** for `Ixn` / `Rot` / `Fcp` / `Icp` against the appropriate
  key (current signing key for `Ixn`; new signing key revealed by `rotationHash` preimage for `Rot`;
  declared `publicKey` for inception kinds).
- **Dual-sig signature verification** for `Ror` / `Rec` / `Wit` / `Dec` against the parent's
  `rotationHash` AND `recoveryHash` commitments.
- **Forward-key commitment checks** for establishment events (see
  [`events.md` §Forward-key commitments](events.md#forward-key-commitments)).
- **Seal-advance cap enforcement** — between successive seal-advancing events the count of
  non-seal-advancing events must not exceed `MINIMUM_PAGE_SIZE − 1 = 64`. See
  [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
- **Repair commits its divergence, content-only — validated, not trusted** — a `Rec` must carry a
  non-empty `folds.forks[]` (a `Rec` on a non-divergent tip — empty `forks[]` — is rejected). The
  merge layer does **not** trust that enumeration as proof the archived branches are content: it
  **independently** walks every branch off the retained (`Rec.previous`) walkback that it holds
  (keep-all-data retains every privileged branch) or the beacon enumerates, and **rejects the `Rec`
  if any such branch carries a privileged event** (any event above tier 1 — `Rot` / `Ror` / `Rec` /
  `Wit` / `Dec`) — a privileged branch is never archived
  ([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair), rule 1), so the
  fork is terminal (`disputed:`, reincept). The committed `forks[]` must match the content tails the
  verifier sees. Independent computation is load-bearing: otherwise a content-branch author could
  **omit** a competing privileged branch from `forks[]`, pass a content-only check over the _listed_
  tails, and let the `Rec` advance the seal past the omitted `Rot` — burying a rotation below the
  seal, the very overturn the rule forbids. The reserve defends the signing key, not the rotation
  key.
- **`Wit` change-requirement (user facet)** — a **user** (`Icp`-rooted) `Wit` is a **rebind**: it
  must change at least one of (`federation`, `witnesses`). A no-op is rejected; a same-federation
  re-pin (only `federationPin`) is **not** a `Wit` — it rides any body event. A
  **federation-witness** (`Fcp`-rooted) `Wit` is governance — its rotation (and `clock` advance) is
  itself the change, so no must-change applies.

Authorization failure here is HARD: an event whose signatures don't verify is rejected by the merge
handler and the new events never land. The verifier reports structural validity; the merge layer
gates writes against it — see
[§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported).

## Why this routing order — adversarial-input diagnostics

The routing order is chosen so attacker diagnostics correctly name the structural
cause-of-rejection. Consider attacker input where the candidate event's
`parent.serial < seal.serial` (it targets the locked portion) AND a conflicting event already exists
at `candidate.serial`:

- **Rule 2 (seal-cap) before rule 3 (fork-detect)** emits `SiblingLocked`, accurately naming the
  structural rule the attacker violated — the parent sits in the locked portion.
- **Fork-detect before seal-cap** would find the conflict in locked history first and reject as an
  immutable-history violation, naming the symptom (the conflict in locked storage) rather than the
  cause (the attacker's parent reference into the locked portion).

The recommended order — structural → seal-cap → fork-detect → kind-specific — produces correct
cause-of-rejection diagnostics under adversarial input. The security outcome (reject) is identical
regardless of order; only the cause-of-rejection **diagnostic** differs. The order is therefore
**required**, not advisory: "outcomes commute under valid input, so pick any order" is exactly the
benign-input reasoning the adversarial-first posture rejects — doctrine flows from adversarial-input
correctness, and naming the _cause_ rather than the _symptom_ is part of that posture
([`../../../../system-thesis.md` §Adversarial-first posture](../../../../system-thesis.md#adversarial-first-posture)).

The four-rule sequence is what guarantees the chain's three per-node states (Active, Divergent,
Decommissioned) are the only states the rules can produce. The seal never forks (rule 2 plus rule 3
jointly); a Decommissioned chain accepts nothing — a sibling to the `Dec` is rejected by the
seal-cap (rule 2, `SiblingLocked`) and any chain-from-`Dec` submission by the kind-schema rule (rule
1, `KelDecommissioned`).

## Routing by chain state

The merge layer routes a batch through three handlers based on the verifier's `KelVerification`
output: normal append, new KEL, or full path. Each handler operates under the merge transaction's
advisory lock.

### Normal append (~99% of submissions)

The submitted events chain directly from the current tip of an Active chain. The verifier resumes
from the prior tip, walks the new events as a continuation, checks seal-advance cap compliance, and
inserts. Outcome: **Accepted**.

A privileged event extending `v_{d-1}` (rather than the tip) is not a normal append — its
`previous = v_{d-1}.said` does not chain from the current tip and routes to the full path, where the
merge layer's fork-detect rule declines to extend the canonical chain onto it per
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).

### New KEL

The submitted events start from inception (`previous` is absent on the first event) and no KEL
exists yet for the prefix. The verifier walks from inception via
[`KelVerifier::new`](verification.md#constructors), runs the inception kind dispatch (`Fcp` /
`Icp`), and inserts. Outcome: **Accepted**.

### Full path (divergence, recovery, overlap)

The full path handles batches that don't chain from the current tip on a non-empty chain. It
subdivides into deduplication, divergent-state routing, and overlap-state routing.

**Deduplication.** Submitted SAIDs are checked against existing SAIDs in the chain log. Events
already present are filtered — two byte-identical events are one event (SAID-addressable), so a
re-submission dedups, never lands as a second branch. If all events are duplicates, the outcome is
`Accepted` with no change. If the remaining batch chains from the tip after dedup, it falls back to
normal-append. This handles partial re-submissions (e.g., gossip sending a full KEL including events
already held).

**Divergent KEL.** When the chain is already Divergent it is **frozen** — only a `Rec` resolves it:

- Batch contains a `Rec` → discriminator runs; outcome `Recovered`. If a seal-advancing event has
  already landed in a branch (a privileged event landed via a competing operator's local extension
  that wasn't gossiped before the divergence formed), the seal-cap rejects the `Rec` whose parent
  sits in the locked portion; outcome `SiblingLocked`.
- Batch contains a privileged event (`Rot` / `Ror` / `Wit` / `Dec`) with `previous = v_{d-1}.said`
  (which would join the fork) → not admitted as a canonical extension, retained as non-canonical
  evidence per [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair);
  outcome `SiblingLocked`.
- Otherwise → `RecoverRequired`.

**Overlap (non-divergent chain).** Submitted events chain from an earlier point in a linear chain,
creating a potential fork. The branch point is the existing event whose SAID matches the first
submitted event's `previous`. The verifier walks from the branch point; the merge layer checks:

- If a seal-advancing event has already landed between the branch point and the chain's current
  state → the locked-portion bound rejects any extension whose parent sits in the locked portion;
  outcome `SiblingLocked` (retained as evidence if a valid fork).
- If the batch contains a `Rec` → discriminator runs; outcome `Recovered`.
- If the batch contains a privileged event (`Rot` / `Ror` / `Wit` / `Dec`) with
  `previous = v_{d-1}.said` → not admitted as a canonical extension, retained as evidence; outcome
  `SiblingLocked`.
- Otherwise → the first conflicting content event is inserted as the fork event; outcome `Diverged`.

## Discriminator algorithm

When the routing path admits a `Rec`, the discriminator identifies the retained branch and resolves
the rest into the `Rec`'s committed `folds.forks[]`. The algorithm is bounded by the seal-advance
cap and fits in a single page fetch:

1. **Detect repair.** The batch contains an event with `kind == Rec`. Its `folds.forks[]` enumerates
   the archival tails it resolves; an empty `forks[]` is rejected (no repairing a non-divergent
   tip).
2. **Compute archive lower bound.** `L = serial of divergence_ancestor + 1` — the divergence serial
   `v_d`.
3. **Page fetch.** Read events at `serial >= L` for the prefix, ordered
   `(serial ASC, kind sort_priority ASC, said ASC)`, capped at `MINIMUM_PAGE_SIZE`. One database
   round-trip.
4. **Trust gate.** Feed the page through the verifier resume mode — re-check SAID, prefix, chain
   linkage, and re-verify each event's signatures against the establishment-declared keys.
   Verification failure aborts the repair (fail-secure on tampered DB rows).
5. **Build the SAID-keyed map.** Index the verified page and the batch's new events not yet on the
   chain. Events that `Rec.previous` references must be addressable.
6. **Walkback.** Starting at `Rec.previous`, follow `event.previous` links through the map,
   accumulating the retained-branch SAIDs for every event with `serial >= L`. Stop when serial drops
   below `L` or the SAID is not in the map. The walkback is bounded by the seal-advance cap (well
   below `MINIMUM_PAGE_SIZE` iterations).
7. **Resolve the archival tails, content-only.** The merge layer **independently** walks every
   branch at `serial >= L` off the retained walkback that it holds or the beacon enumerates, and
   **rejects the `Rec` on any privileged event** in those branches (the fork is `disputed:` →
   reincept) — it never trusts the submitter's `folds.forks[]` as proof that no privileged branch
   was omitted (per §4); privileged branches are always retained (keep-all-data), so an omitted
   `Rot` is caught, not buried by sealing past it. The committed content tails are validated
   **by-prefix** and need not co-reside in the discriminator's hot page (which is the retained
   branch plus the `Rec`). The resolved tails move out of the canonical live chain into
   non-canonical retained storage; the `folds.forks[]` is the on-chain audit record of what was
   resolved.
8. **Insert.** Land the batch's new events: pending first (if any), then the `Rec`.

The page-plus-resume-verify pattern means a single hot-page fetch plus in-memory traversal, with no
per-hop queries; the privileged-check additionally reads the bounded retained competing branches (≤
2 per spine position, each ≤ 64), which the node already holds or the beacon enumerates. The
seal-advance cap bounds the fold, so the discriminator's hot page covers the retained branch (≤ 64,
the fold) plus the `Rec`; the competing branches and archival tails are validated from retained
storage / by-commitment, not held in the hot page.

## Branch-scoped Rec verification

When verifying a `Rec` batch, the verifier seeds from `Rec.previous` (the submitter's chosen anchor
— branch tip in branch-tip-extending shape, or `v_{d-1}` in divergence-ancestor-extending shape) and
walks only that branch plus the batch's new events. The to-be-archived tails are validated against
the `Rec`'s committed `folds.forks[]`; the repair runs only after verification succeeds.

This honors the no-extend-adversary rule: the walker's running state never carries a competing
branch across the repair boundary. After the repair, the chain has a single linear walkback from
`Rec`; the verifier's resume state is consistent with the post-repair shape.

## Cross-node privileged-vs-privileged races

When two federation nodes each accept a competing privileged event extending `v_{d-1}` via
independent local linear-chain extensions, cross-node convergence runs **data-locally**:

- Each event lands cleanly on its submitting node as a linear-chain extension; the seal advances
  locally.
- Gossip delivers each event to the other node; on each peer, the gossip-arriving event's parent
  sits in the locked portion (behind the now-advanced seal). The seal-cap **rejects it as a
  canonical extension but retains it as non-canonical evidence** (keep-all-data) — so each node ends
  up holding both branches.
- Each node **reads the divergence by a data-local walk** over the retained branches: two privileged
  branches past the fork read `disputed:`. The witness beacon propagates the competing branch SAIDs
  to a node that lacks them, but the verdict is the node's own.

The merge layer enforces local invariants strictly; convergence is the data-local walk, not a
federation verdict. See
[`recovery.md` §Cross-node privileged-vs-privileged races](recovery.md#cross-node-privileged-vs-privileged-races),
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair), and
[§Federation convergence](../../../../protocol-doctrine.md#federation-convergence).

## Gossip send-side partitioning

Propagating a divergent KEL chain to another node requires more than ordering events by canonical
chain order. The receiver's merge handler routes batches by content predicates
(recovery-versus-rejection versus divergent-rejection); a single batch that contains both
pre-divergence events and a post-divergence fork event would route through the overlap branch and
the second branch's events would be rejected on the second pass. To make propagation succeed, the
**sender** partitions the chain into sub-batches the receiver will accept under its routing rules
and sends them in sequence.

The partitioning algorithm sends the longer chain first as a sequence of non-divergent appends, then
sends the fork event from the shorter chain as an atomic batch (which creates the divergence on the
receiver). The send-side responsibility is structural — receive-side ordering can sort what arrived
but cannot fix composition problems where the receiver's merge handler will reject a particular
batch composition.

See [`reconciliation.md` §Transfer ordering](reconciliation.md#transfer-ordering) for the per-state
matrix.

## Pagination

All KEL queries are deterministically ordered by `(serial ASC, kind sort_priority ASC, said ASC)`
for stable pagination across divergent events sharing a serial. `MINIMUM_PAGE_SIZE` controls the
page size for both reads and the merge handler's full path; responses carry a `has_more` indicator
for truncation.

## Key invariants

1. **Events are sorted deterministically by `(serial, kind_priority, said)`.** The SAID tiebreaker
   is for determinism only; it carries no semantic meaning. See
   [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority).
2. **Only one divergent event added per overlap.** When divergence is detected, only the first
   conflicting event is written as the fork event; a byte-identical re-submission dedups
   (SAID-addressable), while a further **distinct** competing event is retained as non-canonical
   evidence (keep-all-data), not added as another canonical branch.
3. **Seal advance in a branch prevents normal recovery.** Once any seal-advancing event lands in a
   branch (typically via a node-local extension that hasn't gossiped to peers), the locked-portion
   bound rejects further `Rec` submissions against `v_{d-1}`, and non-privileged submissions return
   `SiblingLocked`.
4. **Decommissioned KEL is fully terminal.** No event of any kind lands. A submission chaining from
   the `Dec` is rejected by the kind-schema rule (`KelDecommissioned`); a sibling to the `Dec` —
   sharing its parent — is rejected by the seal-cap (`SiblingLocked`).
5. **Branch-scoped verifier input on `Rec`.** Rec verification is branch-scoped, not chain-scoped;
   the repair runs only after verification succeeds, and commits the archival tails it resolves in
   `folds.forks[]`.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: key-state fields, authorization, the manifest
  roles, sort priority, seal-advance cap.
- [`recovery.md`](recovery.md) — recovery doctrine: Rec parent shapes, repair-event bound, pre-seal
  verifiability.
- [`verification.md`](verification.md) — verifier algorithm: `KelVerifier::new` / `resume` /
  `from_branch_tip`, signature verification, anchor checking.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof; race matrix;
  effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-repair) —
  divergence and repair (cross-primitive): freeze, tier-resolution, keep-all-data retention.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking)
  — merge verification and advisory locking.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#operation-categories) —
  operation categories (serving, consuming, resolving).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (subsequent sub-issue): the beacon, cross-node propagation.
