# KEL Events — Per-Kind Reference

Per-kind structural reference for the KEL event taxonomy: nine event kinds across three inception variants, two non-archiving extension kinds, two recovery-revealing kinds, one federation-mutation kind, and one terminal kind. This doc states the per-kind fields, authorization, anchor relationships, the three-tier capability model, and the seal-advance cap.

For chain lifecycle (states, locked-portion bound, page model), see [`log.md`](log.md). For merge-layer routing, [`merge.md`](merge.md). For recovery doctrine, [`recovery.md`](recovery.md). For the verifier walk, [`verification.md`](verification.md).

## Event taxonomy

| Kind | Topic | Class | Tier | Purpose |
|---|---|---|---|---|
| `Fcp` | `vdti/kel/v1/events/fcp` | inception | special | Founder pre-federation inception (no federation exists yet). |
| `Icp` | `vdti/kel/v1/events/icp` | inception | special | Standard inception (member or end-user KEL) bound to an existing federation. |
| `Dip` | `vdti/kel/v1/events/dip` | inception | special | Delegated inception. Same shape as `Icp` plus a delegator declared at `anchors[1]`. |
| `Ixn` | `vdti/kel/v1/events/ixn` | content | 1 | Interaction. Hosts tier-1 anchors. Does not change keys. |
| `Rot` | `vdti/kel/v1/events/rot` | privileged | 2 | Rotation. May host tier-2 anchors. Reveals the next signing key (committed by the prior establishment's `rotationHash`) and commits a new one. |
| `Ror` | `vdti/kel/v1/events/ror` | privileged | 3 | Rotate-recovery. May host tier-3 anchors. Dual-signed; proactively rotates both signing and recovery keys. |
| `Fed` | `vdti/kel/v1/events/fed` | privileged | 3 | Federation-binding mutation. Dual-signed; founder binding (v=1 after `Fcp`), inter-federation re-binding (v>1), or witness-params update. Must change at least one of (federation binding, witness params). |
| `Rec` | `vdti/kel/v1/events/rec` | archiving | 3 | Recovery. Dual-signed; resolves a divergent chain by archiving the discriminator-losing branch. |
| `Dec` | `vdti/kel/v1/events/dec` | privileged | 3 | Decommission. Dual-signed; terminal event ending the chain on a clean linear landing. |

The **class** column names the event's chain-state effect on its own chain when its landing would create or join a divergent set (per [§Event-class taxonomy](../../../../protocol-doctrine.md#event-class-taxonomy)). The **tier** column names which key material is required to forge the event — see [§Three-tier capability model](#three-tier-capability-model) below.

## Three-kind inception

KEL inception is one of three structurally distinct kinds dispatched by the kind discriminator at v=0. The kind determines whether the chain is pre-federation or federation-bound, what witnessing applies, and whether the chain may serve as a federation member.

| Kind | When used | `anchors` at v=0 | Witness params at v=0 | Eligible as federation member |
|---|---|---|---|---|
| `Fcp` | Founder pre-federation inception (no federation exists yet). | absent / empty | forbidden | yes — founder KELs become federation-bound via `Fed` at v=1 in the bootstrap atomic batch. |
| `Icp` | Standard inception (member or end-user KEL) under an existing federation. | `[federation_iel_said]` | required | yes. |
| `Dip` | Delegated inception. The chain declares its delegator as `anchors[1]`; the delegator's KEL anchors the inception. | `[federation_iel_said, delegator_kel_prefix]` | required | **no** — see [§No-Dip-federation-member rule](#no-dip-federation-member-rule). |

The verifier dispatches at v=0 on kind:

- `Fcp` → pre-federation chain. No witnessing applies until a subsequent `Fed` at v=1 declares federation binding. The federation Fcp itself is brought into existence in the same atomic bootstrap batch (see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md)).
- `Icp` / `Dip` → federation-bound from inception. `anchors[0]` declares which federation (it is the federation IEL SAID — see [§Anchors](#anchors)); witness params declare the chain's witnessing policy.

### No-Dip-federation-member rule

A `Dip` event declares its delegator at `anchors[1]`; the delegator has structural authority over the delegate's KEL — the delegator can withhold or revoke the anchoring `Ixn` events that authorize the delegate. This authority lives **outside** the federation's `authPolicy` / `governancePolicy` surface, so a Dip-based federation member would appear peer-equal in the federation IEL's `authPolicy.identity_leaves` while being structurally subordinate to its delegator in a way the federation cannot see or govern.

The constraint is verifier-enforced at federation IEL `Evl` time: an `Evl` that would add an identity IEL endorsing a `Dip`-based KEL to `authPolicy.identity_leaves` is rejected. End-user (non-member) KELs may be any of the three inception kinds; the constraint applies only to federation membership. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md).

### Dip delegation resolution

`Dip` declares its delegator at `anchors[1]`, captured into the verification token but not checked at submit time. The delegation relationship is verified at **policy-evaluation time** via a `Delegate(delegator)` policy node: any KEL whose `anchors[1]` equals `delegator` and which the delegator anchors (via an `Ixn` in the delegator's KEL) satisfies the node. The single-argument form (`Delegate(delegator)`) lets the delegator rotate their delegate fleet — decommission, replace, add — without changing any policy that references them.

## Per-kind field rules

`KeyEvent` structural validation enforces these rules per kind. The verifier and merge layer add chain-state checks on top (e.g., seal-advance cap; dual-signature verification against prior establishment commitments).

### Structural fields

| Kind | `serial` | `previous` | `publicKey` | `rotationHash` | `recoveryKey` | `recoveryHash` |
|---|---|---|---|---|---|---|
| `Fcp` | `== 0` | forbidden | required | required | forbidden | required |
| `Icp` | `== 0` | forbidden | required | required | forbidden | required |
| `Dip` | `== 0` | forbidden | required | required | forbidden | required |
| `Ixn` | `>= 1` | required | forbidden | forbidden | forbidden | forbidden |
| `Rot` | `>= 1` | required | required | required | forbidden | forbidden |
| `Ror` | `>= 1` | required | required | required | required | required |
| `Fed` | `>= 1` | required | required | required | required | required |
| `Rec` | `>= 1` | required | required | required | required | required |
| `Dec` | `>= 1` | required | required | forbidden | required | forbidden |

The forward-key commitment fields (`rotationHash`, `recoveryKey`, `recoveryHash`) drive the dual-signature mechanic — see [§Forward-key commitments](#forward-key-commitments). The `anchors` array and witness params are separate fields — see [§Anchors](#anchors) and [§Witness params](#witness-params). A `Dip`'s delegator is `anchors[1]`, not a standalone field.

### Anchors

Events that carry anchors carry an **`anchors`** array — a flat, ordered sequence of SAIDs. Three properties motivate the flat-array shape:

- **Privacy.** No in-data role labels: the array carries bare SAIDs, never per-entry `kind` tags. SAIDs are opaque — type-qualified base64 hashes that reveal nothing without fetching the target. Each entry's structural role is dispatched from the event kind (already in the event) by position, not from in-data tagging, so anchor structure opens no new side-channel.
- **Storage compatibility.** A homogeneous-typed sequence of SAIDs maps cleanly onto native array storage; heterogeneous tagged entries would force parallel arrays or per-entry typing.
- **Batching.** `Ixn` / `Rot` / `Ror` may carry several anchors in one event, saving separate chain entries — and their signatures — when an operator legitimately anchors multiple SAIDs at one chain position.

The verifier dispatches the array's interpretation by event kind via per-kind positional rules. Structural anchors come first by position; generic anchors (where allowed) follow.

| Kind | `anchors` | Count | Per-position role |
|---|---|---|---|
| `Fcp` | absent / empty | 0 | — (pre-federation) |
| `Icp` | `[federation_iel_said]` | exactly 1 | `[0]` federation binding |
| `Dip` | `[federation_iel_said, delegator_kel_prefix]` | exactly 2 | `[0]` federation binding; `[1]` delegator |
| `Fed` | `[federation_iel_said]` | exactly 1 | `[0]` federation binding |
| `Ixn` | `[generic, ...]` | ≥ 1 | all generic; tier-1 host |
| `Rot` | `[generic, ...]` | ≥ 0 | all generic; tier-2 host |
| `Ror` | `[generic, ...]` | ≥ 0 | all generic; tier-3 host |
| `Rec` | absent / empty | 0 | — |
| `Dec` | absent / empty | 0 | — |

**Identity-binding events (`Fcp` / `Icp` / `Dip` / `Fed`) are structural-only** — they carry exactly their binding declaration(s) and admit no generic batching, keeping binding declarations minimal. **Chain-extension events (`Ixn` / `Rot` / `Ror`) carry generic anchors** for batching. **Archival / terminal events (`Rec` / `Dec`) carry none** — `Rec`'s role is divergence resolution, `Dec` ends the chain; the protocol does not conflate anchor emission with the recovery or terminal primitives. Each event kind carries one explicit purpose; operators compose them rather than combining behaviors in a single event.

A generic anchor is **any SAID** — an IEL event SAID, a SEL event SAID, a credential SAID, a policy SAID, a custody pointer, or any other content-addressable target. IEL/SEL anchoring is the canonical use case named at the cross-primitive layer ([§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation)), but an `anchors` entry is generic; the KEL does not constrain what a generic SAID points at.

`Fed`'s anchor is the federation binding, **not** a generic anchor. A chain that needs to both change federation and anchor a SAID uses two events — a `Fed` for the binding change plus an `Ixn` / `Rot` / `Ror` for the anchor. The bootstrap special case follows directly: founder `Fed` events anchor the federation IEL `Fcp` precisely because `Fed`'s federation-binding entry (= the federation IEL `Fcp` SAID) is itself an IEL event SAID, and a tier-3 `Fed` satisfies the federation IEL's tier-2 anchor requirement (see [§Tier-3 events satisfy tier-2 anchor requirements](#tier-3-events-satisfy-tier-2-anchor-requirements)). See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md).

KEL verification validates anchor **format** only — each entry is a SAID-shaped token, and the count / positional schema above holds. Anchor **satisfaction** — what a SAID points to, and which tier-elevation rules apply — is downstream-verifier responsibility. Anchor *kind* and *tier* validation are cross-chain: IEL and SEL verifiers enforce them per [§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation) when resolving policy satisfaction against KEL anchors.

### Witness params

Witness params (`witnessThreshold`, `witnessSelectionSize`) declare the chain's witnessing policy. They appear on the kinds that establish or change the chain's federation context:

| Kind | Witness params |
|---|---|
| `Icp` / `Dip` | required (at inception) |
| `Fed` | required |
| `Rot` / `Ror` | inherited from the most-recent prior `Icp` / `Dip` / `Fed` |
| `Fcp` / `Ixn` / `Rec` / `Dec` | forbidden |

A `Fed` event **mutates federation context** and MUST change at least one of (federation binding, witness params); a `Fed` whose federation binding (`anchors[0]`) matches the chain's current binding AND whose witness params match the current params is a no-op and is rejected. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) for the bootstrap ceremony, the founder Fed-at-v=1 pattern, and the inter-federation re-binding mechanics.

## Authorization and signature shapes

The **authorization** column names which signature(s) the verifier requires for the event to be accepted. Tier 1 events are single-signed by the current signing key; tier 2 events are single-signed by the new signing key the rotation preimage reveals; tier 3 events are dual-signed by the new signing key AND the recovery key.

| Kind | Primary signature | Recovery signature |
|---|---|---|
| `Fcp` | new signing key (declared `publicKey`; self-authenticating against prefix derivation) | — |
| `Icp` | new signing key (declared `publicKey`; self-authenticating against prefix derivation) | — |
| `Dip` | new signing key (declared `publicKey`); delegator (`anchors[1]`) checked at policy-evaluation time | — |
| `Ixn` | current signing key (most recent establishment's `publicKey`) | — |
| `Rot` | new signing key revealed by `publicKey` (preimage of prior `rotationHash`) | — |
| `Ror` | new signing key (preimage of prior `rotationHash`) | recovery key revealed by `recoveryKey` (preimage of prior `recoveryHash`) |
| `Fed` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |
| `Rec` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |
| `Dec` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |

`Rec` / `Ror` / `Fed` / `Dec` reveal the recovery key — they are the **recovery-revealing** sub-class. They commit to the spent-key rule: once a recovery-revealing event lands, the recovery key it reveals is publicly known. Tracked via `lastRecoveryRevealingEvent` on the verification token — see [`log.md` §Seal-tracking and the locked-portion bound](log.md#seal-tracking-and-the-locked-portion-bound).

`Rec` / `Ror` / `Rot` / `Fed` advance the seal — they are the **seal-advancing** kinds. Tracked via `lastSealAdvancingEvent`. The two sub-classes overlap on `Rec` / `Ror` / `Fed` but diverge on `Rot` (seal-advancing only) and `Dec` (recovery-revealing only).

## Three-tier capability model

KEL events are classified by **tier** — the cryptographic material an adversary must hold to forge the event. The tier names the captured material, not the number of signatures on the event.

- **Tier 1 — signing key alone.** Adversary holds the current signing key. They can land `Ixn`. No hidden preimage is revealed.
- **Tier 2 — rotation-key preimage alone.** Adversary holds the preimage of the prior establishment's `rotationHash`. They can land `Rot`. The rotation preimage reveals what *becomes* the new signing key for `Rot`'s single signature — the old signing key is **not** a prerequisite for tier 2. Rotation exists precisely so an operator can recover when the old signing key is compromised; requiring the old signing key to authorize rotation would defeat the purpose.
- **Tier 3 — rotation-key preimage AND recovery-key preimage.** Adversary holds both preimages: the preimage of the prior `rotationHash` AND the preimage of the prior `recoveryHash`. They can land `Ror` / `Fed` / `Rec` / `Dec`. The dual signature is over (new signing key revealed by the rotation preimage) + (recovery key revealed by the recovery preimage) — two signatures, two roles, neither requiring the old signing key.

**Common framing mistake.** Tier 2 is not "signing + rotation preimage"; tier 3 is not "signing + rotation + recovery preimage." The old signing key is not a prerequisite for tier 2 or tier 3. Adding "signing +" to tier 2 or tier 3 conflates "what an adversary needs to compromise to produce this event" with "what keys are referenced by this event." The signing key applies *only* to tier 1.

The three tiers define the [anchor-tier-elevation surface](../../../../protocol-doctrine.md#anchor-tier-elevation): each IEL or SEL operation class requires a KEL anchor of at-least the corresponding tier per contributing policy member. The tier hierarchy makes the cryptographic cost of forging a governance act, binding establishment, or terminal event on an IEL or SEL strictly higher than the cost of forging routine extension events on its contributing KELs.

### Tier-3 events satisfy tier-2 anchor requirements

A tier-3 KEL event (`Ror` or `Fed`) reveals both the rotation preimage and the recovery preimage; either one already satisfies the rotation-preimage requirement that tier-2 anchoring is checking against. The verifier-side leaf-anchor check is **minimum-tier-capability**, not **exact-event-kind**: any KEL event of at-least the required capability tier matches. This matters at the bootstrap ceremony, where founder `Fed` events at v=1 are the tier-2 anchors for the in-batch federation IEL `Fcp`.

## Forward-key commitments

Establishment events (every kind except `Ixn`) commit one or both forward-key digests:

| Kind | `rotationHash` | `recoveryHash` |
|---|---|---|
| `Fcp` / `Icp` / `Dip` | required | required |
| `Rot` | required | forbidden (`Rot` does not change the recovery commitment) |
| `Ror` / `Fed` / `Rec` | required | required |
| `Dec` | forbidden (terminal) | forbidden (terminal) |
| `Ixn` | forbidden | forbidden |

The verifier seeds tracked `rotationHash` / `recoveryHash` from the inception event and updates them on each establishment event. Future revelations are checked against the tracked digest: at each `Rot`, the verifier checks `digest(publicKey) == prior.rotationHash`; at each tier-3 event, it additionally checks `digest(recoveryKey) == prior.recoveryHash`.

## Seal-advance cap

KEL has one protocol-enforced cap (the seal-advance cap) plus operator guidance on recovery-preimage rotation cadence.

**Seal-advance cap (protocol-enforced).** A seal-advancing event (`Rec` / `Ror` / `Rot` / `Fed`) must land every `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events. The cap bounds the chain-state-advance window: divergence on a chain since the last seal-advancing event is capped at 62 events on either branch, so the discriminator's archival window fits in one page. The `− 2` headroom accommodates an atomic 2-event lifecycle batch — `[Rec, Rot]` (recovery followed by the conditional rotation when the archived branch had rotated past the surviving one) — in one `MINIMUM_PAGE_SIZE`-bounded page on every conformant deployment. See [`log.md` §Seal-advance cap](log.md#seal-advance-cap) and [§Forks are Seal-Bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).

**Recovery-preimage rotation (operator guidance).** Operators SHOULD rotate the recovery-key preimage commitment via `Ror` periodically. Cadence depends on the operator's threat model, custody arrangement (cold storage versus active HSM), and acceptable preimage-staleness exposure; the protocol does not enforce a specific number. Recovery keys are typically hardware-held and preimage-identified rather than usage-degraded, so protocol-forced cadence would impose access on cold-stored or separated-custody recovery keys on a fixed schedule the operator's threat model is designed to avoid.

**Adversary bound.** The seal-advance cap bounds an adversary's fork at 62 events before they must produce a seal-advancing event — which requires at least tier-2 capability (rotation-key preimage for `Rot`) or tier-3 capability (rotation + recovery preimages for `Ror` / `Fed`). A tier-1 adversary lacking the rotation preimage cannot extend beyond the cap. Builders should auto-insert `Rot` when an `Ixn` would exceed the cap; the operator's recovery-preimage rotation cadence guidance selects `Ror` over `Rot` when the operator wants to refresh the recovery-key preimage commitment.

## Per-kind sort priority

The merge layer orders events at the same serial deterministically by `(serial ASC, kind sort_priority ASC, said ASC)`. Sort priorities:

| Kind | Sort priority |
|---|---|
| `Fcp` | 0 |
| `Icp` | 1 |
| `Dip` | 2 |
| `Ixn` | 3 |
| `Rot` | 4 |
| `Ror` | 5 |
| `Fed` | 6 |
| `Rec` | 7 |
| `Dec` | 8 |

The ordering matters for adversarial-input diagnostics. Two competing `Ixn` events in a divergent fork get the same priority and break the tie by SAID — identical ordering across all nodes, so deduplication and divergence detection produce the same result on every node. The privileged sort priorities keep privileged events ordered after `Ixn` within a batch for consistent merge-layer evaluation: a batch ending in a privileged event whose landing would create or join a divergent set is rejected per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal); a clean linear-extension privileged event lands normally.

The `said` tiebreaker is for determinism only and has no semantic meaning.

## Typical chain shapes

### Pre-federation founder bootstrap

```
s0  kind=fcp  publicKey=k0,  rotationHash=h(k1),  recoveryHash=h(r0)
s1  kind=fed  publicKey=k1,  rotationHash=h(k2),  recoveryHash=h(r1),
              anchors=[federation_fcp.said],
              witnessParams={threshold, selectionSize}
              ← reveals k1 + r0; dual-signed (k1 + r0)
```

The Fcp inception is pre-federation (no anchors, no witness params, no witnessing). The Fed at v=1 declares the federation binding — its `anchors[0]` is the federation IEL `Fcp` SAID. That federation Fcp is brought into existence in the same atomic bootstrap batch — see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md).

### Standard inception

```
s0  kind=icp  publicKey=k0, rotationHash=h(k1), recoveryHash=h(r0),
              anchors=[federation_iel.said],
              witnessParams={threshold, selectionSize}
```

The Icp binds to an existing federation at v=0; its `anchors[0]` is the federation IEL SAID. End-user chains and post-bootstrap federation-member chains use this shape.

### Delegated inception

```
s0  kind=dip  publicKey=k0, rotationHash=h(k1), recoveryHash=h(r0),
              anchors=[federation_iel.said, delegator_kel_prefix],
              witnessParams={threshold, selectionSize}
```

Acceptance: structural (SAID and prefix re-derive; signature by `k0`; `anchors` has exactly 2 entries) AND the delegator's KEL contains an `Ixn` anchoring the Dip's prefix. Verifiers check the delegator (`anchors[1]`) at policy-evaluation time per [§Dip delegation resolution](#dip-delegation-resolution).

### Normal lifecycle

```
s0   kind=icp  publicKey=k0,  rotationHash=h(k1),  recoveryHash=h(r0),
                anchors=[federation_iel.said], witnessParams=...
s1   kind=ixn  anchors=[said_a]                               ← signed by k0
s2   kind=rot  publicKey=k1,  rotationHash=h(k2)              ← reveals k1; signed by k1
s3   kind=ixn  anchors=[said_b, said_c]                       ← batched; signed by k1
...
s62  kind=ror  publicKey=kN,  recoveryKey=r0,                 ← proactive recovery-rotation
                rotationHash=h(kN+1), recoveryHash=h(r1)        signed by kN + r0
```

`Ror` at s62 keeps the chain inside the seal-advance cap. A `Rot` at s62 would also satisfy the cap; an operator who wants to refresh the recovery-key preimage commitment chooses `Ror` per their operator-guidance cadence.

### Divergence resolved by recovery

```
s0..s4   normal chain
s5a  kind=ixn  anchors=[said_a]                         ← non-privileged fork
s5b  kind=ixn  anchors=[said_b]                         ← non-privileged fork
     — chain is Divergent; recoverable via Rec —
s6   kind=rec  previous=s5a.said,                       ← Rec extends s5a (branch-tip-extending shape)
                publicKey=k6, recoveryKey=r0,             dual-signed (k5+r0)
                rotationHash=h(k7), recoveryHash=h(r1)
```

The `Rec` extends the branch the operator chose to preserve. The merge layer's discriminator walks back from `Rec.previous` to identify the surviving branch; the other branch is archived. See [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes) for the two attachment patterns and the structural property that makes the divergence-ancestor-extending shape cross-node-validatable.

### Clean decommission

```
s0..sN   normal chain
sN+1     kind=dec   ← Dec ends the KEL cleanly; dual-signed (kN + recovery key)
```

After `Dec`, the chain is fully terminal. Two independent merge-layer mechanisms reject every subsequent submission: a sibling to the `Dec` (sharing parent `v_{N}`) is rejected by the seal-cap (`SiblingLocked`), and a submission chaining from the `Dec` is rejected by the kind-schema rule (`KelDecommissioned` — no kind admits a `Dec` parent). See [`merge.md` §Routing order](merge.md#routing-order). Concurrent priv-vs-priv races at the federation layer surface via divergent witness receipts — see [`recovery.md` §Cross-node priv-vs-priv races](recovery.md#cross-node-priv-vs-priv-races) and [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, prefix derivation, locked-portion bound, page model.
- [`merge.md`](merge.md) — merge-layer routing.
- [`recovery.md`](recovery.md) — recovery doctrine, Rec parent shapes, three-tier compromise model.
- [`verification.md`](verification.md) — verifier algorithm and kind dispatch.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — anchor tier elevation, event-class taxonomy, forks-are-seal-bounded, privileged-divergence-is-terminal, KEL inception.
- [`../../sad/said.md`](../../sad/said.md#derivation) — SAID and prefix derivation algorithms.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing (subsequent sub-issue).
- [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) — federation bootstrap atomic batch (subsequent sub-issue).
