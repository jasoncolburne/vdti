# KEL Events — Per-Kind Reference

Per-kind structural reference for the KEL event taxonomy: eight event kinds across two inception variants, one content kind, two rotation kinds, one recovery kind, one federation-mutation kind, and one terminal kind. The cross-primitive field shape — common fields, the `manifest` model, `previousSeal` / `folded`, and the full per-kind field grid — is the [event-shape reference](../event-shape.md#kel); this doc states the KEL-specific semantics: the key-state fields, two-kind inception, the manifest roles a KEL event carries, forward-key commitments, the three-tier capability model, sort priority, and the seal-advance cap.

For chain lifecycle (states, the seal and spine, locked-portion bound, page model), see [`log.md`](log.md). For merge-layer routing, [`merge.md`](merge.md). For recovery doctrine, [`recovery.md`](recovery.md). For the verifier walk, [`verification.md`](verification.md).

## Event taxonomy

| Kind | Topic | Class | Tier | Purpose |
|---|---|---|---|---|
| `Fcp` | `vdti/kel/v1/events/fcp` | inception | 1 | Founder pre-federation inception (no federation exists yet). |
| `Icp` | `vdti/kel/v1/events/icp` | inception | 1 | Standard inception (member or end-user KEL) bound to an existing federation. |
| `Ixn` | `vdti/kel/v1/events/ixn` | content | 1 | Interaction. Hosts tier-1 anchors. Changes no keys and does not advance the seal. The **repairable** kind. |
| `Rot` | `vdti/kel/v1/events/rot` | privileged | 2 | Rotation. May host tier-2 anchors. Reveals the next signing key (committed by the prior establishment's `rotationHash`) and commits a new one. Seal-advancing. |
| `Ror` | `vdti/kel/v1/events/ror` | privileged | 3 | Rotate-recovery. May host tier-3 anchors. Dual-signed; rotates both signing and recovery keys. Seal-advancing. |
| `Rec` | `vdti/kel/v1/events/rec` | repair | 3 | Recover. Dual-signed; resolves a divergence by keeping the repairing branch and archiving the rest (committed in `folded.forks[]`). Returns the chain to Active. Seal-advancing. |
| `Fed` | `vdti/kel/v1/events/fed` | privileged | 3 | Federation-binding mutation. Dual-signed; changes `federation` and/or `witnesses` (must change at least one). On Fcp-rooted chains, the v=1 `Fed` declares both for the first time — the founder-binding pattern. Seal-advancing. |
| `Dec` | `vdti/kel/v1/events/dec` | terminal | 3 | Decommission. Dual-signed; ends the chain on a clean linear landing. Advances the seal to its own serial. |

The **class** column names the event's role under the [divergence-and-repair rules](../../../../protocol-doctrine.md#divergence-and-repair): only **content** (`Ixn`) is archivable; a **privileged** event is never archived or overturned; the **repair** kind (`Rec`) resolves a divergence; the **terminal** kind (`Dec`) ends the chain. The **tier** column names which key material is required to forge the event — see [§Three-tier capability model](#three-tier-capability-model).

## Two-kind inception

KEL inception is one of two structurally distinct kinds dispatched by the kind discriminator at v=0. The kind determines whether the chain is pre-federation or federation-bound, and what witnessing applies. KEL is concerned with key state only; delegation is an identity-layer concern handled at the IEL primitive (see [`../iel/`](../iel/)), not a KEL inception kind.

| Kind | When used | Federation binding | Witnesses | Eligible as federation member |
|---|---|---|---|---|
| `Fcp` | Founder pre-federation inception (no federation exists yet). | absent | forbidden | yes — a founder KEL becomes federation-bound via the v=1 `Fed` in the bootstrap atomic batch. |
| `Icp` | Standard inception (member or end-user KEL) under an existing federation. | `federation` + `federationPin` | the `witnesses` manifest role | yes. |

The verifier dispatches at v=0 on kind:

- `Fcp` → pre-federation chain. It carries no `federation` binding and no `witnesses`, and cannot stand alone — its binding `Fed` is the next event (v=1) in the same atomic bootstrap batch. The federation IEL `Icp` (a federation is an ordinary IEL) is brought into existence in that same batch (see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md)).
- `Icp` → federation-bound from inception. `federation` (the federation IEL prefix) and `federationPin` (the as-of federation position) declare the binding; the `witnesses` manifest role declares the chain's witnessing policy.

## Key-state fields

The canonical per-kind field grid — `publicKey` / `rotationHash` / `recoveryKey` / `recoveryHash` / `federation` / `federationPin` / `previousSeal` / `manifest`, with each kind's req / fbd / opt — is the [event-shape reference](../event-shape.md#kel). The KEL-specific key-state semantics:

| Kind | `publicKey` | `rotationHash` | `recoveryKey` | `recoveryHash` |
|---|---|---|---|---|
| `Fcp` / `Icp` | req | req | fbd | req |
| `Ixn` | fbd | fbd | fbd | fbd |
| `Rot` | req | req | fbd | fbd |
| `Ror` / `Rec` / `Fed` | req | req | req | req |
| `Dec` | req | fbd | req | fbd |

`publicKey` is the signing key effective at this event; `rotationHash` and `recoveryHash` are the forward-key digests committing the next signing and recovery keys; `recoveryKey` reveals the recovery-key preimage on the dual-signed kinds. The forward-key commitment fields drive the dual-signature mechanic — see [§Forward-key commitments](#forward-key-commitments). The seal-advancing kinds (`Rot` / `Ror` / `Rec` / `Fed` / `Dec`) additionally carry the top-level `previousSeal` spine back-link ([`log.md` §The spine](log.md#the-spine)).

## The manifest — roles a KEL event carries

A KEL event commits to lower-layer SAIDs, its witnessing policy, and its folded content run through a **`manifest`** — the SAID of a role-grouped SAD ([event-shape §The manifest](../event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role)). A KEL event's manifest may carry only these roles; one carrying any role outside this vocabulary is malformed and rejected, and a role is consumed only after dispatching on a kind permitted to carry it (read kind-first):

| Role | Carried by | Commits to |
|---|---|---|
| `anchors` | `Ixn` (req, ≥ 1) / `Rot` / `Ror` / `Rec` | lower-layer event / SAD SAIDs this event anchors |
| `witnesses` | `Icp` / `Fed` | the witness-config SAD `{ threshold, signers }` |
| `folded` | `Rot` / `Ror` / `Rec` / `Fed` / `Dec` | the content run folded since the prior seal — `{ canonical, forks[] }` plus the run's boundary SAIDs; `Rec` carries the `forks[]` (the archival tails it resolves) |

### Anchors

The `anchors` role is a flat, ordered list of generic SAIDs — an IEL event SAID, a SEL event SAID, a credential SAID, a custody pointer, or any other content-addressable target. The KEL does not constrain what a generic SAID points at; IEL / SEL anchoring is the canonical use named at the cross-primitive layer ([§Tiers](../../../../protocol-doctrine.md#tiers)). Two properties motivate the bare-SAID list shape:

- **Privacy.** The list carries bare SAIDs, never per-entry role tags. SAIDs are opaque — type-qualified base64 hashes that reveal nothing without fetching the target — so anchor structure opens no side-channel.
- **Batching.** `Ixn` / `Rot` / `Ror` may carry several anchors in one event, saving separate chain entries — and their signatures — when an operator legitimately anchors multiple SAIDs at one chain position.

`Ixn` carries the `anchors` role required (≥ 1) — anchoring is its purpose; `Rot` / `Ror` / `Rec` carry it optionally. **Identity-binding events (`Fcp` / `Icp` / `Fed`)** carry their federation binding in the top-level `federation` / `federationPin` fields and their witnessing policy in the `witnesses` role — never as anchors — and admit no generic batching, keeping binding declarations minimal. `Dec` carries no anchors; it ends the chain.

KEL verification validates anchor **format** only — each entry is a SAID-shaped token. Anchor **satisfaction** — what a SAID points to, and which tier-elevation rules apply — is downstream-verifier responsibility: IEL and SEL verifiers enforce anchor *kind* and *tier* per [§Tiers](../../../../protocol-doctrine.md#tiers) when resolving authorization against KEL anchors.

### Federation binding and witnesses

The federation context lives in two top-level fields plus the `witnesses` manifest role, on the kinds that establish or change it. `federation` is the federation IEL **prefix** (which federation — it follows the federation's evolution); `federationPin` is a **SAID** pinning the as-of federation position; the `witnesses` role commits the witness-config SAD `{ threshold, signers }`. The exact req / fbd / opt per kind is the [event-shape reference](../event-shape.md#kel)'s; the carriers are `Icp` and `Fed`, with `Rot` / `Ror` inheriting the most-recent prior context and `Fcp` / `Ixn` / `Rec` / `Dec` carrying none.

A `Fed` event **mutates federation context** and must change at least one of (`federation`, `witnesses`); a `Fed` that changes neither is a no-op and is rejected. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) for the bootstrap ceremony, the founder Fed-at-v=1 pattern, and the inter-federation re-binding mechanics. Because a founder `Fed`'s `federation` binding is the federation IEL's prefix and its `federationPin` is that IEL's inception position, `Fed` is structurally tier-3 — matching the federation IEL `Icp`'s tier-3 establishment.

## Authorization and signature shapes

The **authorization** column names which signature(s) the verifier requires for the event to be accepted. Tier-1 events are single-signed by the signing key in effect at this chain position — declared by the event itself for inception (`Fcp` / `Icp`), inherited from the most recent prior establishment for `Ixn`. Tier-2 events are single-signed by the new signing key the rotation preimage reveals. Tier-3 events are dual-signed by the new signing key AND the recovery key.

| Kind | Primary signature | Recovery signature |
|---|---|---|
| `Fcp` | new signing key (declared `publicKey`; self-authenticating against prefix derivation) | — |
| `Icp` | new signing key (declared `publicKey`; self-authenticating against prefix derivation) | — |
| `Ixn` | current signing key (most recent establishment's `publicKey`) | — |
| `Rot` | new signing key revealed by `publicKey` (preimage of prior `rotationHash`) | — |
| `Ror` | new signing key (preimage of prior `rotationHash`) | recovery key revealed by `recoveryKey` (preimage of prior `recoveryHash`) |
| `Rec` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |
| `Fed` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |
| `Dec` | new signing key (preimage of prior `rotationHash`) | recovery key (preimage of prior `recoveryHash`) |

`Ror` / `Rec` / `Fed` / `Dec` reveal the recovery key — they are the **recovery-revealing** sub-class. Once a recovery-revealing event lands, the recovery key it reveals is publicly known. Tracked via `lastRecoveryRevealingEvent` on the verification token — see [`log.md` §The seal, the spine, and the locked-portion bound](log.md#the-seal-the-spine-and-the-locked-portion-bound).

`Rot` / `Ror` / `Rec` / `Fed` / `Dec` advance the seal — they are the **seal-advancing** kinds, tracked via `lastSealAdvancingEvent`. The two sub-classes overlap on `Ror` / `Rec` / `Fed` / `Dec` but diverge on `Rot` (seal-advancing without revealing the recovery key); `Dec` belongs to both (it reveals the recovery key, advances the seal to its own serial, and is terminal).

## Three-tier capability model

KEL events are classified by **tier** — the cryptographic material an adversary must hold to forge the event. The tier names the captured material, not the number of signatures on the event.

- **Tier 1 — signing key alone.** Adversary holds the current signing key. They can land `Ixn`. Inception (`Fcp` / `Icp`) sits at tier 1 by signature shape — single-sig by the inception's declared signing key — but isn't a forge-target against an existing chain: the prefix derives from the whole-SAD content (see [`log.md` §Prefix derivation](log.md#prefix-derivation)), so a specific prefix's inception cannot be forged without a Blake3-256 collision. No hidden preimage is revealed.
- **Tier 2 — rotation-key preimage alone.** Adversary holds the preimage of the prior establishment's `rotationHash`. They can land `Rot`. The rotation preimage reveals what *becomes* the new signing key for `Rot`'s single signature — the old signing key is **not** a prerequisite for tier 2. Rotation exists precisely so an operator can recover when the old signing key is compromised; requiring the old signing key to authorize rotation would defeat the purpose.
- **Tier 3 — rotation-key preimage AND recovery-key preimage.** Adversary holds both preimages: the preimage of the prior `rotationHash` AND the preimage of the prior `recoveryHash`. They can land `Ror` / `Rec` / `Fed` / `Dec`. The dual signature is over (new signing key revealed by the rotation preimage) + (recovery key revealed by the recovery preimage) — two signatures, two roles, neither requiring the old signing key.

**Common framing mistake.** Tier 2 is not "signing + rotation preimage"; tier 3 is not "signing + rotation + recovery preimage." The old signing key is not a prerequisite for tier 2 or tier 3. Adding "signing +" to tier 2 or tier 3 conflates "what an adversary needs to compromise to produce this event" with "what keys are referenced by this event." The signing key applies *only* to tier 1.

The three tiers define the [anchor-tier-elevation surface](../../../../protocol-doctrine.md#tiers): each IEL or SEL operation requires a KEL anchor of at-least the corresponding tier. The tier hierarchy makes the cryptographic cost of forging a governance act, binding establishment, or terminal event on an IEL or SEL strictly higher than the cost of forging routine extension events on its contributing KELs.

### Tier-3 events satisfy tier-2 anchor requirements

A tier-3 KEL event (`Ror` or `Fed`) reveals both the rotation preimage and the recovery preimage; either one already satisfies the rotation-preimage requirement that tier-2 anchoring is checking against. The verifier-side leaf-anchor check is **minimum-tier-capability**, not **exact-event-kind**: any KEL event of at-least the required capability tier matches. See [§Tiers](../../../../protocol-doctrine.md#tiers).

## Forward-key commitments

Establishment events (every kind except `Ixn`) commit one or both forward-key digests:

| Kind | `rotationHash` | `recoveryHash` |
|---|---|---|
| `Fcp` / `Icp` | required | required |
| `Rot` | required | forbidden (`Rot` does not change the recovery commitment) |
| `Ror` / `Rec` / `Fed` | required | required |
| `Dec` | forbidden (terminal) | forbidden (terminal) |
| `Ixn` | forbidden | forbidden |

The verifier seeds tracked `rotationHash` / `recoveryHash` from the inception event and updates them on each establishment event. Future revelations are checked against the tracked digest: at each `Rot`, the verifier checks `digest(publicKey) == prior.rotationHash`; at each tier-3 event, it additionally checks `digest(recoveryKey) == prior.recoveryHash`.

## Seal-advance cap

KEL has one protocol-enforced cap (the seal-advance cap) plus operator guidance on recovery-preimage rotation cadence.

**Seal-advance cap (protocol-enforced).** A seal-advancing event (`Rec` / `Ror` / `Rot` / `Fed`; the terminal `Dec` also advances the seal but ends the chain) must land at least every `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events. The cap bounds the chain-state-advance window: divergence on a chain since the last seal-advancing event is capped at 62 events on either branch, so the discriminator's archival window fits in one page. The `− 2` headroom accommodates an atomic 2-event lifecycle batch — `[Rec, Rot]` (recovery followed by the conditional rotation when the archived branch had rotated past the surviving one) — in one `MINIMUM_PAGE_SIZE`-bounded page on every conformant deployment. See [`log.md` §Seal-advance cap](log.md#seal-advance-cap) and [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).

**Recovery-preimage rotation (operator guidance).** Operators SHOULD rotate the recovery-key preimage commitment via `Ror` periodically. Cadence depends on the operator's threat model, custody arrangement (cold storage versus active HSM), and acceptable preimage-staleness exposure; the protocol does not enforce a specific number. Recovery keys are typically hardware-held and preimage-identified rather than usage-degraded, so protocol-forced cadence would impose access on cold-stored or separated-custody recovery keys on a fixed schedule the operator's threat model is designed to avoid.

**Adversary bound.** The seal-advance cap bounds an adversary's fork at 62 events before they must produce a seal-advancing event — which requires at least tier-2 capability (rotation-key preimage for `Rot`) or tier-3 capability (rotation + recovery preimages for `Ror` / `Fed`). A tier-1 adversary lacking the rotation preimage cannot extend beyond the cap. Builders should auto-insert `Rot` when an `Ixn` would exceed the cap; the operator's recovery-preimage rotation cadence guidance selects `Ror` over `Rot` when the operator wants to refresh the recovery-key preimage commitment.

## Per-kind sort priority

The merge layer orders events at the same serial deterministically by `(serial ASC, kind sort_priority ASC, said ASC)`. Sort priorities:

| Kind | Sort priority |
|---|---|
| `Fcp` | 0 |
| `Icp` | 1 |
| `Ixn` | 2 |
| `Rot` | 3 |
| `Ror` | 4 |
| `Fed` | 5 |
| `Rec` | 6 |
| `Dec` | 7 |

The ordering matters for adversarial-input diagnostics. Two competing `Ixn` events in a fork get the same priority and break the tie by SAID — identical ordering across all nodes, so deduplication and divergence detection produce the same result on every node. The privileged sort priorities keep privileged events ordered after `Ixn` within a batch for consistent merge-layer evaluation: a privileged event whose landing would create or join a divergence cannot extend the canonical chain past the seal — it is **retained as non-canonical evidence** rather than landing as a canonical sibling (per [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair)); a clean linear-extension privileged event lands normally.

The `said` tiebreaker is for determinism only and has no semantic meaning.

## Typical chain shapes

### Pre-federation founder bootstrap

```
s0  kind=fcp  publicKey=k0,  rotationHash=h(k1),  recoveryHash=h(r0)
s1  kind=fed  publicKey=k1,  rotationHash=h(k2),  recoveryHash=h(r1),
              federation=fed_iel.prefix,  federationPin=fed_iel_icp.said,
              previousSeal=fcp.said,  manifest={ witnesses: {threshold, signers} }
              ← reveals k1 + r0; dual-signed (k1 + r0)
```

The `Fcp` inception is pre-federation (no `federation`, no `witnesses`, no witnessing). The `Fed` at v=1 declares the federation binding — `federation` is the federation IEL prefix and `federationPin` its inception position — and is the first seal, so it carries `previousSeal = fcp.said` (the spine root). That federation IEL `Icp` is brought into existence in the same atomic bootstrap batch — see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md).

### Standard inception

```
s0  kind=icp  publicKey=k0, rotationHash=h(k1), recoveryHash=h(r0),
              federation=fed_iel.prefix,  federationPin=fed_iel_pos.said,
              manifest={ witnesses: {threshold, signers} }
```

The `Icp` binds to an existing federation at v=0 via `federation` / `federationPin`; its `witnesses` role declares the chain's witnessing policy. End-user chains and post-bootstrap federation-member chains use this shape.

### Normal lifecycle

```
s0   kind=icp  publicKey=k0,  rotationHash=h(k1),  recoveryHash=h(r0),
                federation=fed_iel.prefix, federationPin=..., manifest={witnesses}
s1   kind=ixn  manifest={ anchors: [said_a] }                ← signed by k0
s2   kind=rot  publicKey=k1,  rotationHash=h(k2),            ← reveals k1; signed by k1
                previousSeal=icp.said,  manifest={ folded }
s3   kind=ixn  manifest={ anchors: [said_b, said_c] }        ← batched; signed by k1
...
s62  kind=ror  publicKey=kN,  recoveryKey=r0,                ← proactive recovery-rotation
                rotationHash=h(kN+1), recoveryHash=h(r1),       signed by kN + r0
                previousSeal=<prior seal>.said, manifest={ folded }
```

The `Rot` at s2 is the first seal, so `previousSeal = icp.said` (the spine root); each later seal back-links to its predecessor. `Ror` at s62 keeps the chain inside the seal-advance cap. A `Rot` at s62 would also satisfy the cap; an operator who wants to refresh the recovery-key preimage commitment chooses `Ror` per their operator-guidance cadence.

### Divergence resolved by recovery

```
s0..s4   normal chain (seal at the most recent prior seal-advancing event)
s5a  kind=ixn  manifest={ anchors: [said_a] }          ← content fork
s5b  kind=ixn  manifest={ anchors: [said_b] }          ← content fork
     — chain is Divergent (frozen); recoverable via Rec —
s6   kind=rec  previous=s5a.said,                       ← Rec extends the branch its author keeps
                publicKey=k6, recoveryKey=r0,            dual-signed (k5 + r0)
                rotationHash=h(k7), recoveryHash=h(r1),
                previousSeal=<prior seal>.said,
                manifest={ folded: { forks: [s5b-tail] } }
```

The `Rec` keeps the branch its submitter authored and archives the rest; the archival tail (here the `s5b` branch) is committed in the `Rec`'s `folded.forks[]`. The merge layer walks the retained branch from `Rec.previous` and archives everything at `serial >= d` not on it. See [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes) for the two attachment patterns and the structural property that makes the divergence-ancestor-extending shape cross-node-validatable.

### Clean decommission

```
s0..sN   normal chain
sN+1     kind=dec   ← Dec ends the KEL cleanly; dual-signed (kN + recovery key);
                      advances the seal to its own serial; previousSeal=<prior seal>.said
```

After `Dec`, the chain is fully terminal. Two independent merge-layer mechanisms reject every subsequent submission: a sibling to the `Dec` (sharing parent `v_{N}`) is rejected by the seal-cap (`SiblingLocked`), and a submission chaining from the `Dec` is rejected by the kind-schema rule (`KelDecommissioned` — no kind admits a `Dec` parent). See [`merge.md` §Routing order](merge.md#routing-order). A concurrent privileged event racing the `Dec` at the same serial on another node is retained as non-canonical evidence and read data-locally — see [`recovery.md` §Cross-node privileged-vs-privileged races](recovery.md#cross-node-privileged-vs-privileged-races).

## Cross-references

- [`../event-shape.md`](../event-shape.md#kel) — cross-primitive event shape: common fields, the `manifest` model, `previousSeal` / `folded`, the canonical per-kind field grid.
- [`log.md`](log.md) — chain primitive: states, prefix derivation, the seal and spine, locked-portion bound, page model.
- [`merge.md`](merge.md) — merge-layer routing.
- [`recovery.md`](recovery.md) — recovery doctrine, Rec parent shapes, three-tier compromise model.
- [`verification.md`](verification.md) — verifier algorithm and kind dispatch.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — tiers and anchor-tier elevation, divergence and repair, forks-are-seal-bounded, inception tiers.
- [`../../sad/said.md`](../../sad/said.md#derivation) — SAID and prefix derivation algorithms.
- [`../iel/`](../iel/) — IEL primitive (subsequent sub-issue). Delegation is an identity-layer concern and lives there (delegated IEL inception; declare / rescind delegation); the `del(delegator)` policy node operates on IEL prefixes, not KEL prefixes.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing (subsequent sub-issue).
- [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) — federation bootstrap atomic batch (subsequent sub-issue).
