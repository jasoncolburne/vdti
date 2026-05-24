# KEL Recovery — Structural Defense Doctrine

KEL recovery is the structural mechanism that lets a chain resolve divergence and defend against tiered key compromise without surrendering the locked portion. This doc states the doctrine: what compromise scenarios the design defends against, why dual-signature plus recovery-key preimage closes those scenarios, why the locked-portion bound makes recovery cross-node-validatable, and how pre-seal verifiability composes with the three-tier compromise model.

This is doctrine, not workflow. Operator CLI ceremony and the choreography for `Rec` / `Ror` / `Dec` lives in [`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md) (subsequent sub-issue). Per-kind event-shape rules live in [`events.md`](events.md); merge-layer routing in [`merge.md`](merge.md); the cross-node correctness proof in [`reconciliation.md`](reconciliation.md).

## Three-tier compromise model

The defense surface KEL recovery covers is structured by tier — the cryptographic material an adversary holds. Each tier names what the adversary needs and only what they need; the old signing key is not a prerequisite for tier 2 or tier 3. See [`events.md` §Three-tier capability model](events.md#three-tier-capability-model) for the canonical capability statement.

| Tier | Adversary holds | Adversary can forge | Defense |
|---|---|---|---|
| 1 | Current signing key. | `Ixn`. | Rotate out via `Rot` (single-sig under the new signing key the rotation preimage reveals). |
| 2 | Rotation-key preimage alone. | `Rot`. | Rotate-recovery via `Ror` (dual-signed) before the adversary rotates. Once the adversary's `Rot` lands, the new signing key is the rotation preimage they hold — recovery via `Rec` against the parent's `recoveryHash` remains because the recovery-key preimage is a distinct commitment. |
| 3 | Rotation-key preimage AND recovery-key preimage. | `Ror` / `Fed` / `Rec` / `Dec`. | No in-band recourse. The protocol provides no recovery primitive against tier-3 compromise; defense is operational (custody separation, threshold redundancy at the IEL layer, abandon-and-reincept). |

The protocol's recovery primitives — `Rec` and `Ror` — close the **tier-1 and tier-2 adversarial surfaces**. They do not close tier-3 compromise; tier-3 defense is the responsibility of the layers composed above KEL (IEL governance policies with threshold redundancy across distinct custodians; see [§Defense in Depth](../../../../protocol-doctrine.md#defense-in-depth)).

## Rec versus Ror — reactive versus proactive

KEL has two distinct recovery primitives. They are not interchangeable.

- **`Rec` is reactive.** Used to resolve an already-divergent chain. `Rec` archives the discriminator-losing branch and returns the chain to Active. Reveals the recovery-key preimage as a side effect of dual-signing; once revealed, the recovery key is spent for this chain.
- **`Ror` is proactive.** Used pre-emptively — to rotate both signing and recovery keys for forward-secrecy hygiene, or to refresh the recovery-key preimage commitment per operator cadence guidance. `Ror` is not divergence-driven; it lands as a linear extension of a non-divergent chain.

Both reveal the current recovery-key preimage and commit a new one (`Ror` and `Rec` both populate `recoveryKey` + `recoveryHash`). The difference is structural lifecycle role:

- **Divergence has happened** → `Rec`. The chain is in Divergent state; `Rec` is the only event class that can resolve it without operator-side reincept under a new prefix.
- **Pre-emptive rotation** → `Ror`. The chain is Active; the operator wants to rotate both keys before any compromise indicator fires.

Don't conflate. Operator guidance for "the chain is divergent, what now?" is `Rec`. Operator guidance for "scheduled rotation cadence" is `Ror`. The two primitives map to different lifecycle moments and produce different chain-state outcomes.

## Dual-signature is the tier-3 defense

`Rec` / `Ror` / `Fed` / `Dec` are dual-signed: one signature by the new signing key (revealed by the rotation-key preimage), one signature by the recovery key (revealed by the recovery-key preimage). Both signatures must verify; both digest commitments (`digest(publicKey) == prior.rotationHash` and `digest(recoveryKey) == prior.recoveryHash`) must match.

The dual-signature requirement is what makes these events structurally tier-3:

- **Forging the primary signature requires the rotation preimage.** A tier-1 adversary holding only the current signing key cannot satisfy this leg — the rotation preimage is committed by the prior establishment's `rotationHash` and not yet revealed.
- **Forging the recovery signature requires the recovery preimage.** A tier-2 adversary holding only the rotation preimage cannot satisfy this leg — the recovery preimage is independently committed by the prior establishment's `recoveryHash`.
- **Both signatures over the SAID.** The signatures commit to the event's content (via the SAID, which hashes the canonical bytes). An adversary cannot substitute a different recovery-key preimage to bypass the commitment check — the prior establishment's `recoveryHash` pins what preimage satisfies.

This is the structural property that makes recovery a real cryptographic boundary, not a policy convention. A party who lacks the recovery-key preimage cannot produce a `Rec` against the parent's commitments, regardless of what other key material they hold.

### Recourse against tier-2 `Rot` takeover

When an adversary holds the rotation-key preimage and lands `Rot_adversary` at `v_N` to take over the chain, the legitimate party's recourse is `Rec` extending the divergence ancestor at `v_{N-1}` (the divergence-ancestor-extending shape; see [§Rec parent shapes](#rec-parent-shapes) below). The dual signature on `Rec` is against `v_{N-1}`'s commitments:

- The rotation preimage at `v_{N-1}` is revealed by the adversary's `Rot_adversary` at `v_N` — both parties have it. The legitimate party's signature under the new signing key validates structurally.
- The recovery preimage at `v_{N-1}` is **not** revealed by `Rot` (`Rot` populates `rotationHash` only; `recoveryHash` is unchanged). Only the legitimate party — who prepared the recovery commitment at `v_{N-1}`'s parent — holds the recovery preimage. The adversary cannot produce the recovery signature.

The legitimate party's `Rec` lands at `v_N`; the merge layer's discriminator archives the adversary's branch (which is now a divergent-set member); the chain recovers, linear, tip = `Rec` at `v_N`. The chain shape after recovery has the legitimate party's keys current and the adversary's keys retired.

The legitimate party does **not** respond by submitting a competing `Rot` extending `v_{N-1}`. Such a `Rot_legitimate` would land as a sibling of `Rot_adversary` (both privileged) and the merge layer would reject it per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal). The `Rec` response routes through the archiving path and preserves the recovery.

## Locked-portion bound makes recovery cross-node-validatable

A `Rec` extends from one of two parent shapes (see [§Rec parent shapes](#rec-parent-shapes)). The **divergence-ancestor-extending shape** — where `Rec.previous = v_{d-1}.said` (the divergence ancestor) — has a structural property that makes recovery cross-node-validatable: `v_{d-1}` is the unique shared parent of all events at `v_d`, and `v_{d-1}` itself lands cleanly on the linear chain before any divergence. So `v_{d-1}` is structurally identical on every node that holds the chain, regardless of which divergent contents each node received.

A `Rec` extending `v_{d-1}` therefore validates uniformly:

- Every node sees the same `v_{d-1}` content (it's part of the locked or pre-divergence portion).
- The `Rec` signs against the same commitments (`v_{d-1}.rotationHash`, `v_{d-1}.recoveryHash`) on every node.
- The discriminator's archival decision (which events at `serial >= d` to remove) is uniform: archive everything at `serial >= d` not on the `Rec.previous` walkback.

This is what makes the divergence-ancestor-extending shape the structural primitive that solves cross-node propagation. A tip-extension or combined-digest approach would not have this property — the "tip" each node sees may differ across the divergent set, and an attempt to recover by extending a tip would commit to a node-local choice the rest of the federation can't replicate.

### Repair-event bound (condition 2b)

The merge layer enforces the repair-event bound: `Rec.previous.serial >= seal_serial`. The bound prevents revival attacks where a party holding stale authority (a recovery preimage revealed by an earlier `Rec` / `Ror` / `Fed`, or a key that has since been rotated out) constructs a `Rec` targeting the locked portion to rearrange the chain. Only current authority gates repair events.

When the bound holds vacuously — no privileged event has landed yet on the chain (only inception plus non-privileged events) — `Rec.previous` may be any chain event including the inception. Once any privileged event advances the seal past `v_{N-1}`, a `Rec` targeting `v_{N-1}` is rejected as `SiblingLocked`.

See [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal) for the structural rule and [§Forks are Seal-Bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded) for the seal-cap that derives from it.

## Rec parent shapes

`Rec` resolves divergence by archiving events via the discriminator. `Rec.previous` takes one of two shapes:

### Branch-tip-extending shape

`Rec.previous` is a branch tip at `v_d`. Rec extends that branch at `v_{d+1}`; the other branch is archived.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ surviving-branch tip @ v_d
                   └─ other-branch tip     @ v_d

Rec construction: rec.previous = surviving-branch tip's said
                  rec.serial   = d + 1

Post-state (linear, recovered):
    ... → v_{d-1} → surviving-branch tip @ v_d → rec @ v_{d+1}
                  ↑
                  other branch archived
```

The submitter (whoever holds the recovery key) chooses one of the two branches at `v_d` as the surviving branch; `Rec` extends it. The discriminator walks back from `Rec.previous` to identify the surviving branch and archives everything at `serial >= d` not on that walkback.

### Divergence-ancestor-extending shape

`Rec.previous` is `v_{d-1}`, the divergence ancestor. Rec lands at `v_d`. All events at `serial >= d` (both divergent-set members) are archived; `Rec` is the only event at `v_d` after the discriminator runs.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ branch-1 tip @ v_d
                   └─ branch-2 tip @ v_d

Rec construction: rec.previous = v_{d-1}.said
                  rec.serial   = d

Post-state (linear, recovered, Rec is the only event at v_d):
    ... → v_{d-1} → rec @ v_d
                  ↑
                  both prior branches archived
```

The divergence-ancestor-extending shape is the structural primitive that gives recovery its cross-node-validatable property (§Locked-portion bound makes recovery cross-node-validatable). It is the recourse when the submitter does not want to preserve either of the existing branches at `v_d` — for instance, when both branches were authored under tier-1 capability and neither carries content the submitter wants to keep.

### Routing through the discriminator

Both parent shapes route through the merge layer's discriminator **before** any divergent-set check fires. `Rec` is archiving, not privileged — its acceptance resolves the divergence rather than producing one. A privileged event (`Rot` / `Ror` / `Fed` / `Dec`) sharing the divergence-ancestor-extending parent shape (`previous = v_{d-1}.said`) on a chain with an existing event at `v_d` would be rejected at the merge layer per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal); the kind discriminator (archiving `Rec` versus privileged) determines whether the parent shape resolves divergence or is rejected.

## Conditional `Rot` follow-up

`Rec` reveals the rotation-key preimage that may be known to a second party (the preimage of the prior `rotationHash`). If the archived branch has already used it but the extending branch hasn't, the legitimate party's `Rec` extends from a position where the rotation preimage they reveal is still known to the second party. A follow-up `Rot` after `Rec` is needed to escape to a signing key only the `Rec` submitter knows.

The rule: `needs_extra_rot = archived_branch_rotated && !extending_branch_rotated`. The truth table:

| Extending branch rotated since divergence? | Archived branch rotated? | Extra `Rot` after `Rec`? |
|---|---|---|
| No | No | No |
| No | Yes | **Yes** |
| Yes | Yes | No |
| Yes | No | No |

The atomic batch `[Rec, Rot]` is the KEL worst-case recovery shape; the seal-advance cap reserves headroom (`MINIMUM_PAGE_SIZE − 2 = 62`) so this batch fits in one page on every conformant deployment. See [`events.md` §Seal-advance cap](events.md#seal-advance-cap).

## Pre-seal verifiability

The locked-portion bound, the seal-cap, and the recovery primitives together produce a durable consumer guarantee: events at-or-below `lastSealAdvancingEvent` remain structurally verifiable indefinitely, regardless of subsequent divergence or federation-layer irreconcilability.

The argument has three legs:

- **Seal advances are clean.** `lastSealAdvancingEvent` advances only on seal-advancing events (`Rec` / `Ror` / `Rot` / `Fed`) that land cleanly on the linear chain. The seal never forks: privileged events that would create or join a divergent set are rejected at the merge layer, so every seal advance is a clean linear-chain landing.
- **At-or-below-seal events were authored under at-least-tier-2 capability.** Every seal advance is a clean privileged or archiving landing — both classes require tier-2 or tier-3 capability. The protocol accepts that authoring as structurally valid sealing-level authority regardless of submitter identity (which the chain layer has no concept of).
- **The locked portion cannot be rearranged.** The repair-event bound denies any future `Rec` from targeting the locked portion; the seal-cap denies any forward extension whose parent is in the locked portion. Together they make the at-or-below-seal segment structurally immutable.

Consumers and dependents that resolve to at-or-below-seal state get the strongest protocol guarantee:

- **Anchors hosted at-or-below the seal stay anchored.** A KEL `Ixn` that anchored an IEL or SEL event at-or-below the seal continues to satisfy the cross-chain anchor check, regardless of subsequent divergence or federation-layer irreconcilability above the seal.
- **Credentials issued under an IEL state at-or-below the seal remain verifiable.** An issuance pinned to a KEL anchor in the locked portion stays trust-evaluable forever.
- **SELs bound to at-or-below-seal `ielEvent` stay trust-evaluable.** The cross-primitive bound that enforces this is checked by IEL / SEL verifiers; the KEL primitive's contribution is the locked-portion immutability.
- **Audit and forensic queries against the locked portion are truthful.** Above-seal events appear in the forensic record but are not structurally trustworthy (they may have been authored under captured tier-1 authority); the locked-portion events are.

Above-seal content is structurally indistinguishable from work authored under captured authority. The verifier signals this via `policy_satisfied`: queries against SAIDs anchored at-or-below the seal return `policy_satisfied = true`; queries against SAIDs above the seal return `policy_satisfied = false`. The boundary is the seal. See [§Pre-seal verifiability](../../../../protocol-doctrine.md#pre-seal-verifiability) for the cross-primitive framing and [§policy_satisfied](../../../../protocol-doctrine.md#policy_satisfied) for the consumer-side signal.

### Above-seal submitter indistinguishability

Above-seal events that landed under valid policy at the time they were processed do not carry "who actually submitted them" information. The same authorization that admitted a legitimate operator's event would admit an adversary's event under captured authority. The protocol has no trusted way to bring out-of-band claims about above-seal authorship into the chain — verification tokens cannot be augmented with claims that originated outside the chain. Consumers may apply their own out-of-band judgment about specific above-seal events; the protocol cannot make those judgments for them.

## Cross-node priv-vs-priv races

Two federation nodes can each accept a competing privileged event extending `v_{d-1}` via independent linear-chain extensions: each event lands cleanly on its submitting node (the seal advances locally), gossip then delivers each event to the other node, and the seal-cap rejects each late arrival with `SiblingLocked` — the locally-landed first-receive already occupies the target serial behind the now-advanced seal.

Per-node, each chain stays linear with its own first-receive as tip. Cross-node, the federation does not converge at the protocol layer for these races. Federation-level convergence is provided by **divergent witness receipts** at the federation layer: federation members witness every structurally-valid event they observe (always-witness), and adjacent receipts at the same chain position carrying different `witnessedSaid` values are the structural evidence that the federation cannot agree at that position. The prefix surfaces as **federation-irreconcilable** at-and-beyond the divergent serial. See [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) and [§Limit of the doctrine — concurrent privileged event races](../../../../protocol-doctrine.md#concurrent-privileged-event-races).

The cross-node race surface covers all privileged-event shapes:

- **Tier-2 path.** A tier-2 adversary (holding only the rotation preimage) can force federation-level non-convergence by racing `Rot_adversary` against an honest concurrent `Rot_operator` or `Ror_operator` on different federation nodes. The forging bar is tier-2 (one preimage), strictly easier than the tier-3 bar required for `Ror` / `Rec` / `Fed` / `Dec`.
- **Tier-3 path.** A tier-3 adversary (holding both preimages) can force non-convergence by racing any recovery-revealing event against operator submissions. Once an adversary's tier-3 event has landed on any federation node, no in-band protocol recourse exists.

The CAP-axis trade-off is structural. The seal-cap and locked-portion bound prevent stale-authority chain rearrangement: a party holding past-position private keys must not be able to land an event targeting the locked portion at any future time. Relaxing the bounds to admit competing privileged events at a sealed serial would re-open the long-tail killswitch surface. The bounds stay unconditional; federation-race non-convergence for concurrent privileged submissions is resolved at the federation layer via witness attestation rather than at the protocol layer via fork merging.

### Operator response to federation-layer non-convergence

When the federation surfaces a prefix as federation-irreconcilable, no further extension on that prefix is consumer-trustable at-and-beyond the divergent serial. Operator recourse is **reincept under a new prefix**. The pre-seal verifiability guarantee bounds the damage: at-or-below-seal anchors, credentials, and SEL bindings stay verifiable; only forward-extending operations against above-seal state lose their trust grounding. See [§Cascade-reincept honesty](../../../../protocol-doctrine.md#cascade-reincept-honesty) for the cross-primitive cascade rules.

## Defense layers above KEL

KEL recovery closes the tier-1 and tier-2 surfaces structurally. The tier-3 surface is closed by the layers composed above KEL:

- **IEL policy composition.** Threshold-redundant governance policies (`M > N` across distinct custodians, where `M` is the threshold count and the policy declares more candidates than the threshold requires) tolerate single-KEL tier-3 compromise. The surviving members can rotate the compromised KEL out via the IEL's `Evl` event without losing the IEL prefix.
- **Custody separation.** KEL-internal custody hygiene (recovery key on a different device, HSM-resident, ceremony-gated) raises the practical bar to acquire both rotation and recovery preimages simultaneously. This is operational hardening; the protocol is custody-agnostic.
- **Federation witnessing.** Under always-witness, competing privileged events at the same chain position both accumulate receipts from the full witness pool, and threshold-two-events fires divergent witness receipts as the structural evidence that the federation cannot agree. Rotation-tier compromise without federation partition cannot force a fork to ratify federation-wide; consumers see the prefix as federation-irreconcilable and refuse to bind.

The combined attack — rotation-tier compromise PLUS adversary-controlled federation partition — is the structurally unavoidable CAP failure mode. KEL guarantees the divergence is **detectable** post-resolution rather than preventing it: receipts are indexed at chain position rather than at event SAID, so when gossip resolves the partition the competing receipts land in the same row group on each node, threshold-two-events fires, and the divergence becomes structurally observable in the data layer. See [§Defense in Depth](../../../../protocol-doctrine.md#defense-in-depth) and [§Adversary Patience and Policy Redundancy](../../../../protocol-doctrine.md#adversary-patience-and-policy-redundancy).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, seal-tracking, locked-portion bound, page model.
- [`events.md`](events.md) — per-kind reference: three-tier capability model, dual-signature shape, forward-key commitments, seal-advance cap.
- [`merge.md`](merge.md) — merge-layer routing: discriminator algorithm, privileged-event rejection, repair-event bound enforcement.
- [`reconciliation.md`](reconciliation.md) — cross-node convergence proof; race matrix; effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#privileged-divergence-is-terminal) — privileged divergence is terminal, repair-event conditions.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#pre-seal-verifiability) — pre-seal verifiability (cross-primitive framing).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#defense-in-depth) — defense in depth; rotation-tier adversary federation-non-convergence path; adversary patience and policy redundancy.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing (subsequent sub-issue): always-witness, threshold-two-events, divergent witness receipts.
- [`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md) — operator CLI ceremony (subsequent sub-issue).
