# KEL Merge — Handler Rules

The KEL merge layer integrates submitted events into the existing chain. It is the protocol's enforcement surface for the locked-portion bound, the privileged-divergence-terminal rule, and the seal-cap. The verifier produces a trust signal on a verification token; the merge layer composes that signal with chain-state-dependent routing to admit or reject batches.

This doc states the merge-layer routing order, the four merge outcomes, the routing rules per chain state, and the adversarial-input diagnostic rationale that motivates the routing order. For per-kind event rules, see [`events.md`](events.md); for the verifier walk, [`verification.md`](verification.md); for the chain primitive, [`log.md`](log.md); for the cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## Single entry point

`merge_events` is the single entry point for all write paths into a KEL — direct submissions, gossip propagation, federation sync, and bootstrap atomic batches. It runs under a PostgreSQL advisory lock for the duration of verification and write. Time-of-check-to-time-of-use is eliminated structurally: the verifier reads under the same lock the merge handler will use to write.

The merge handler returns a `MergeOutcome` carrying the result variant, the divergence serial (when divergence was detected), and the new tip SAID (when the chain advanced linearly).

## Merge outcomes

The four merge outcomes name what happened to the chain — they are the structural verdicts the routing rules produce.

| Outcome | Chain effect | Triggering condition |
|---|---|---|
| **Accepted** | Linear extension; new tip established; seal advances on seal-advancing kinds. | Submitted events chain cleanly from the current tip on an Active chain (or from inception on an Empty chain). |
| **Diverged** | New non-privileged event lands as a fork at an earlier serial; chain transitions Active → Divergent. | Submitted batch contains a non-privileged event whose `previous` points at a pre-tip serial, where the existing chain at that child serial holds a competing non-privileged event. Only the first conflicting event is written. |
| **Recovered** | Divergence resolved; the discriminator-losing branch is archived; chain returns to Active; the seal advances to the `Rec`'s serial. | Submitted batch contains a `Rec` whose parent shape (branch-tip-extending or divergence-ancestor-extending) routes through the discriminator. |
| **SiblingLocked** | No state change. Submission rejected. | Submitted event's parent sits in the locked portion behind `lastSealAdvancingEvent` — its target serial already holds a locked sibling — or a privileged event's landing would otherwise create or join a divergent set. On a Decommissioned chain this is the **sibling-to-`Dec`** case: an event sharing the `Dec`'s parent, racing the `Dec` at its serial. |
| **KelDecommissioned** | No state change. Submission rejected. | Submitted event chains *from* a `Dec` (its parent's kind is `Dec`). Caught in structural validation by the kind-schema rule — no kind admits a `Dec` parent. Independent of the seal-cap; see [§Routing order](#routing-order) rule 1. |

A subsumed variant — `RecoverRequired` — applies when the chain is Divergent and the submitted batch is neither a `Rec` nor a privileged event (which would itself reject as `SiblingLocked`). The routing rule signals that only `Rec` resolves divergence. Structurally, `RecoverRequired` is a guidance signal; the chain state stays Divergent.

## Routing order

The merge handler routes a submitted batch through four rule scopes in this **structural order**. The order is chosen so adversarial-input diagnostics correctly name the structural cause-of-rejection.

### 1. Structural validation

Per-kind field rules (per [`events.md` §Per-kind field rules](events.md#per-kind-field-rules)), SAID integrity, prefix consistency, signature shape, chain-linkage continuity. Any failure here is a structural error; the submission is rejected regardless of chain state. The verifier walks each event and checks:

- SAID recomputation matches the declared SAID (per [`../../sad/said.md`](../../sad/said.md#derivation)).
- For the inception event: prefix recomputes from the canonical bytes with `said` and `prefix` blanked.
- Per-kind required / forbidden field presence per [`events.md` §Structural fields](events.md#structural-fields), [§Anchors](events.md#anchors) (including the per-kind anchor-list count / positional schema), and [§Witness params](events.md#witness-params).
- Signature shape (single-sig versus dual-sig per kind) per [`events.md` §Authorization and signature shapes](events.md#authorization-and-signature-shapes).
- Chain linkage: `previous` resolves to an event in the verifier's branch state.
- **Kind-schema predecessor rule.** No kind admits a `Dec` parent. A submission whose parent's kind is `Dec` is rejected with `KelDecommissioned`. This is `Dec`-terminality expressed as a kind-schema property — the same class of structural rejection as a `custody` field appearing on a chain event ([§Routing order](../../../../protocol-doctrine.md#routing-order)), not a routing-order outcome. `Dec`'s kind semantics mean "no more events"; the kind-schema forbids any successor, so the rejection is caught here at merge entry rather than by a downstream rule.

### 2. Seal-cap

The submitted event's parent must sit at-or-after `lastSealAdvancingEvent` in chain order (`parent_serial >= seal_serial`). Submissions whose parent is in the locked portion are rejected with `SiblingLocked`. This is the structural rule that enforces current-state-only authority — see [§Forks are Seal-Bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded) and [`recovery.md` §Repair-event bound (condition 2b)](recovery.md#repair-event-bound-condition-2b).

The seal-cap is **unconditional** on KEL: every event class is subject to it. A `Rec` whose `previous.serial < seal_serial` is rejected — the locked-portion bound stops stale-authority revival of the chain regardless of who holds the recovery key.

The seal-cap and `Dec`-terminality (rule 1's kind-schema check) are **independent** rejection mechanisms. Both surface on a Decommissioned chain, but they catch different shapes:

- **Sibling to the `Dec`** — a submission whose parent is the `Dec`'s parent, racing the `Dec` at its serial. The chain is sealed at its `Dec` (the `Dec`'s terminality locks its serial; `Dec` is not a seal-*advancing* kind in the `lastSealAdvancingEvent` tracking sense, but a Decommissioned chain admits no event at-or-below the `Dec`'s serial). The candidate's parent sits in that locked portion, so the seal-cap rejects with `SiblingLocked`.
- **Chains from the `Dec`** — a submission whose parent IS the `Dec`. Its parent sits at the seal boundary, so it *passes* the seal-cap and would append after the `Dec`. The seal-cap does **not** catch it; only the kind-schema rule in rule 1 does, rejecting with `KelDecommissioned`.

The kind-schema rule is load-bearing — the seal-cap does not subsume `Dec`-terminality. Without rule 1's check, an event could append after a `Dec`; the seal-cap alone would not stop it.

### 3. Fork-detect

The event's `(parent_said, serial)` is checked against the chain's existing events at that serial. Three outcomes:

- **Privileged event whose landing would create or join a divergent set** — rejected with `SiblingLocked` per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal). Two subcases reach this rejection:
  - **On a linear chain** with an existing event at `v_d`: a privileged event with `previous = v_{d-1}.said` would land as a sibling and create a 2-event divergent set containing a privileged event.
  - **On an already-divergent chain**: a privileged event with `previous = v_{d-1}.said` would join the existing divergent set.
- **Archiving event** (`Rec`) — routes through the discriminator. Either parent shape (branch-tip-extending or divergence-ancestor-extending — see [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes)) is admitted to the discriminator path before any divergent-set check fires. The discriminator resolves the divergent set; the outcome is `Recovered`.
- **Non-privileged event** — admitted. If a competing non-privileged event already exists at the same serial, a divergent set forms and the outcome is `Diverged`. If no existing event sits at the candidate's serial, the event extends as a linear-chain landing (only relevant when the candidate is itself non-privileged — privileged candidates take the linear-extension path through rule 4, not fork-detect).

### 4. Kind-specific authorization

For events admitted past rule 3, kind-specific authorization fires:

- **Single-sig signature verification** for `Ixn` / `Rot` / `Fcp` / `Icp` against the appropriate key (current signing key for `Ixn`; new signing key revealed by `rotationHash` preimage for `Rot`; declared `publicKey` for inception kinds).
- **Dual-sig signature verification** for `Ror` / `Fed` / `Rec` / `Dec` against the parent's `rotationHash` AND `recoveryHash` commitments.
- **Forward-key commitment checks** for establishment events (see [`events.md` §Forward-key commitments](events.md#forward-key-commitments)).
- **Seal-advance cap enforcement** — between successive seal-advancing events the count of non-seal-advancing events must not exceed `MINIMUM_PAGE_SIZE − 2 = 62`. See [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
- **`Fed` change-requirement** — `Fed` must change at least one of (anchor, witness params). A no-op `Fed` is rejected.

Authorization failure here is HARD: an event whose signatures don't verify is rejected by the merge handler and the new events never land. See [§Verifier and merge are distinct treatments](../../../../protocol-doctrine.md#verifier-and-merge-are-distinct-treatments).

## Why this routing order — adversarial-input diagnostics

The routing order is chosen so attacker diagnostics correctly name the structural cause-of-rejection. Consider attacker input where the candidate event's `parent.serial < seal.serial` (it targets the locked portion) AND a conflicting event already exists at `candidate.serial`:

- **Rule 2 (seal-cap) before rule 3 (fork-detect)** emits `SiblingLocked`, accurately naming the structural rule the attacker violated — the parent sits in the locked portion.
- **Fork-detect before seal-cap** would find the conflict in locked history first and reject as an immutable-history violation, naming the symptom (the conflict in locked storage) rather than the cause (the attacker's parent reference into the locked portion).

The recommended order — structural → seal-cap → fork-detect → kind-specific — produces correct cause-of-rejection diagnostics under adversarial input. Implementations MAY commute scopes whose outcomes match under valid input, but SHOULD follow the recommended order so attacker submissions are diagnosed by structural cause rather than by downstream symptom.

The four-rule sequence is what guarantees the chain's three per-node states (Active, Divergent, Decommissioned) are the only states the rules can produce. The seal never forks (rule 2 plus rule 3 jointly); divergent sets contain only non-privileged events (rule 3); a Decommissioned chain accepts nothing — a sibling to the `Dec` is rejected by the seal-cap (rule 2, `SiblingLocked`) and any chain-from-`Dec` submission by the kind-schema rule (rule 1, `KelDecommissioned`).

## Routing by chain state

The merge layer routes a batch through three handlers based on the verifier's `KelVerification` output: normal append, new KEL, or full path. Each handler operates under the merge transaction's advisory lock.

### Normal append (~99% of submissions)

The submitted events chain directly from the current tip of an Active chain. The verifier resumes from the prior tip, walks the new events as a continuation, checks seal-advance cap compliance, and inserts. Outcome: **Accepted**.

A privileged event extending `v_{d-1}` (rather than the tip) is not a normal append — its `previous = v_{d-1}.said` does not chain from the current tip and routes to the full path, where the merge layer's fork-detect rule rejects it per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal).

### New KEL

The submitted events start from inception (`previous` is absent on the first event) and no KEL exists yet for the prefix. The verifier walks from inception via [`KelVerifier::new`](verification.md#constructors), runs the inception kind dispatch (Fcp / Icp), and inserts. Outcome: **Accepted**.

### Full path (divergence, recovery, overlap)

The full path handles batches that don't chain from the current tip on a non-empty chain. It subdivides into deduplication, divergent-state routing, and overlap-state routing.

**Deduplication.** Submitted SAIDs are checked against existing SAIDs in the chain log. Events already present are filtered. If all events are duplicates, the outcome is `Accepted` with no change. If the remaining batch chains from the tip after dedup, it falls back to normal-append. This handles partial re-submissions (e.g., gossip sending a full KEL including events already held).

**Divergent KEL.** When the chain is already Divergent, routing depends on the batch:

- Batch contains a `Rec` → discriminator runs; outcome `Recovered`. If the existing chain has advanced the seal in a divergent branch (a privileged event landed via a competing operator's local extension that wasn't gossiped to this node before the divergent state formed), the seal-cap rejects the `Rec` whose parent sits in the locked portion; outcome `SiblingLocked`.
- Batch contains a privileged event (`Rot` / `Ror` / `Fed` / `Dec`) with `previous = v_{d-1}.said` (which would join the divergent set) → rejected per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal); outcome `SiblingLocked`.
- Otherwise → `RecoverRequired`.

**Overlap (non-divergent chain).** Submitted events chain from an earlier point in a linear chain, creating a potential fork. The branch point is the existing event whose SAID matches the first submitted event's `previous`. The verifier walks from the branch point; the merge layer checks:

- If a seal-advancing event has already landed between the branch point and the chain's current state → the locked-portion bound rejects any extension whose parent sits in the locked portion; outcome `SiblingLocked`.
- If the batch contains a `Rec` → discriminator runs; outcome `Recovered`.
- If the batch contains a privileged event (`Rot` / `Ror` / `Fed` / `Dec`) with `previous = v_{d-1}.said` → rejected per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal); outcome `SiblingLocked`.
- Otherwise → first conflicting event is inserted as the fork event; outcome `Diverged`.

## Discriminator algorithm

When the routing path admits a `Rec`, the discriminator identifies the surviving branch and archives the rest. The algorithm is bounded by the seal-advance cap and fits in a single page fetch:

1. **Detect recovery.** The batch contains an event with `kind == Rec`.
2. **Compute archive lower bound.** `L = serial of divergence_ancestor + 1` — the divergence serial `v_d`.
3. **Page fetch.** Read events at `serial >= L` for the prefix, ordered `(serial ASC, kind sort_priority ASC, said ASC)`, capped at `MINIMUM_PAGE_SIZE`. One database round-trip.
4. **Trust gate.** Feed the page through the verifier resume mode — re-check SAID, prefix, chain linkage, and re-verify each event's signatures against the establishment-declared keys. Verification failure aborts archival (fail-secure on tampered DB rows).
5. **Build the SAID-keyed map.** Index the verified page and the batch's new events not yet on the chain. Bundled events that `Rec.previous` references must be addressable.
6. **Walkback.** Starting at `Rec.previous`, follow `event.previous` links through the map, accumulating the surviving-branch SAIDs for every event with `serial >= L`. Stop when serial drops below `L` or the SAID is not in the map. The walkback is bounded by the seal-advance cap (well below `MINIMUM_PAGE_SIZE` iterations).
7. **Archive.** Page events at `serial >= L` whose SAID is NOT on the surviving-branch walkback. Insert into the archive tables; create a `RecoveryRecord` audit row and link rows for each archived event.
8. **Delete.** Remove archived events from the live chain log by SAID (not by serial range — surviving-branch events at the same serials must remain).
9. **Insert.** Land the batch's new events: pending first (if any), then `Rec` (plus the optional `Rot` follow-up — see [`recovery.md` §Conditional `Rot` follow-up](recovery.md#conditional-rot-follow-up)).

The page-plus-resume-verify pattern means one database round-trip plus in-memory traversal — no per-hop queries. The seal-advance cap bounds the archival window so the page covers both branches and the bundled `[Rec, ?Rot]` worst-case batch.

## Branch-scoped Rec verification

When verifying a `Rec` batch, the verifier seeds from `Rec.previous` (the submitter's chosen anchor — branch tip in branch-tip-extending shape, or `v_{d-1}` in divergence-ancestor-extending shape) and walks only that branch plus the batch's new events. The to-be-archived branch is in storage but never in the walker's input stream; archival runs only after verification succeeds.

This honors the [§One Divergent Generation at a Time](../../../../protocol-doctrine.md#one-divergent-generation-at-a-time) invariant: the walker's running state never carries a divergent set across the archival boundary. After archival, the chain has a single linear walkback from `Rec`; the verifier's resume state is consistent with the post-archival shape.

## Cross-node priv-vs-priv races

When two federation nodes each accept a competing privileged event extending `v_{d-1}` via independent local linear-chain extensions, the cross-node convergence breaks at the protocol layer:

- Each event lands cleanly on its submitting node as a linear-chain extension; the seal advances locally.
- Gossip delivers each event to the other node; on each peer, the gossip-arriving event's parent sits in the locked portion (behind the now-advanced seal) and the seal-cap rejects.
- Per-node, each chain is linear with its own first-receive as tip; cross-node, the chains do not match.

The merge layer enforces local invariants strictly. Federation-level convergence is provided by the federation witnessing layer via divergent witness receipts; the prefix surfaces as federation-irreconcilable at-and-beyond the divergent serial. See [`recovery.md` §Cross-node priv-vs-priv races](recovery.md#cross-node-priv-vs-priv-races), [§Limit of the doctrine — concurrent privileged event races](../../../../protocol-doctrine.md#concurrent-privileged-event-races), and [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

## Gossip send-side partitioning

Propagating a divergent KEL chain to another node requires more than ordering events by canonical chain order. The receiver's merge handler routes batches by content predicates (recovery-versus-rejection versus divergent-rejection); a single batch that contains both pre-divergence events and a post-divergence fork event would route through the overlap branch and the second branch's events would be rejected on the second pass. To make propagation succeed, the **sender** partitions the chain into sub-batches the receiver will accept under its routing rules and sends them in sequence.

The partitioning algorithm sends the longer chain first as a sequence of non-divergent appends, then sends the fork event from the shorter chain as an atomic batch (which creates the divergence on the receiver). The send-side responsibility is structural — receive-side ordering can sort what arrived but cannot fix composition problems where the receiver's merge handler will reject a particular batch composition.

See [`reconciliation.md` §Transfer ordering](reconciliation.md#transfer-ordering) for the per-state matrix.

## Pagination

All KEL queries are deterministically ordered by `(serial ASC, kind sort_priority ASC, said ASC)` for stable pagination across divergent events sharing a serial. `MINIMUM_PAGE_SIZE` controls the page size for both reads and the merge handler's full path; responses carry a `has_more` indicator for truncation.

## Key invariants

1. **Events are sorted deterministically by `(serial, kind_priority, said)`.** The SAID tiebreaker is for determinism only; it carries no semantic meaning. See [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority).
2. **Only one divergent event added per overlap.** When divergence is detected, only the first conflicting event is written; subsequent conflicting submissions dedup-reject.
3. **Seal advance in a divergent branch prevents normal recovery.** Once any seal-advancing event lands in a divergent branch (typically via a node-local extension that hasn't gossiped to peers), the locked-portion bound rejects further `Rec` submissions against `v_{d-1}`, and non-privileged submissions return `SiblingLocked`.
4. **Decommissioned KEL is fully terminal.** No event of any kind lands. A submission chaining from the `Dec` is rejected by the kind-schema rule (`KelDecommissioned`); a sibling to the `Dec` — sharing its parent — is rejected by the seal-cap (`SiblingLocked`).
5. **Branch-scoped verifier input on `Rec`.** Rec verification is branch-scoped, not chain-scoped; archival runs only after verification succeeds.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, locked-portion bound, page model.
- [`events.md`](events.md) — per-kind reference: structural fields, authorization, anchor, sort priority, seal-advance cap.
- [`recovery.md`](recovery.md) — recovery doctrine: Rec parent shapes, repair-event bound, conditional `Rot` follow-up, pre-seal verifiability.
- [`verification.md`](verification.md) — verifier algorithm: `KelVerifier::new` / `resume` / `from_branch_tip`, signature verification, anchor checking.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof; race matrix; effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#routing-order) — canonical routing-order doctrine (cross-primitive).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#privileged-divergence-is-terminal) — privileged-divergence-is-terminal rule.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) — seal-cap and locked-portion bound.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#operation-categories) — operation categories (serving, consuming, resolving).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing (subsequent sub-issue): cross-node convergence at the federation layer.
