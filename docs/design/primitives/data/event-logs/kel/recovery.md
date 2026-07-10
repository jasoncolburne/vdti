# KEL Recovery — Structural Defense Doctrine

KEL recovery is the structural mechanism that lets a chain resolve divergence and defend against
tiered key compromise without surrendering the locked portion. This doc states the doctrine: what
compromise scenarios the design defends against, why recovery is a plain rotation that buries the
adversary's run, why the locked-portion bound makes recovery cross-node-validatable, and how
pre-seal verifiability composes with the two-tier compromise model.

This is doctrine, not workflow. Operator CLI ceremony and the choreography for recovery `Rot` /
`Trm` lives in
[`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md)
(subsequent sub-issue). Per-kind event-shape rules live in [`events.md`](events.md); merge-layer
routing in [`merge.md`](merge.md); the cross-node correctness proof in
[`reconciliation.md`](reconciliation.md).

## Two-tier compromise model

The defense surface KEL recovery covers is structured by tier — the cryptographic material an
adversary holds. Each tier names what the adversary needs and only what they need; the old signing
key is not a prerequisite for tier 2. See
[`events.md` §Two-tier capability model](events.md#two-tier-capability-model) for the canonical
capability statement.

| Tier | Adversary holds       | Adversary can forge    | Defense                                                                                                                                                                                                                                |
| ---- | --------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Current signing key.  | `Ixn`.                 | A forked content branch is buried by a recovery `Rot`; a linear takeover is rotated out. Content is buriable — what the rotation reserve defends: the **signing** key.                                                                 |
| 2    | The rotation reserve. | `Rot` / `Wit` / `Trm`. | **None in-band.** A reserve holder just extends the chain with a rotation to their own key — a takeover-by-extend witnesses sign as an ordinary next event → **reincept** (the reserve defends the signing key, not the rotation key). |

The recovery `Rot` closes the **tier-1 (content) surface** — it buries an adversary's content
branch, which is what the rotation reserve defends: the **signing** key, never the rotation key.
Tier-2 has **no in-band recourse**: a reserve holder can just extend the chain with a rotation to
their own key, a takeover-by-extend that witnesses sign willingly as an ordinary next event, so it
forces nothing and is silent to third parties on a dormant chain (caught only by owner vigilance).
Once an adversary rotation lands, survivability is decided one layer up — IEL governance with
threshold redundancy across distinct custodians; see
[§Limit of the doctrine — current-state compromise](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise).

## Recovery is a plain `Rot` that buries at the root

Recovery is not a special kind — it is an ordinary `Rot`, applied at the right position. When your
signing key is stolen, you rotate to a fresh key at the **first** event that isn't yours. That
single rotation does two things at once:

- **It locks the thief out.** The rotation reveals the next reserve as the new signing key; the
  thief lacks it, so they can mint no new content on the recovered chain.
- **It buries their run.** Everything below the rotation that isn't on the surviving line is dead,
  and anything grown from a dead point is dead too (**deadness descends** — an event whose parent is
  dead is dead). You go for the **root**, not their tip, so however long a run the thief piled on,
  it all hangs off that one point and dies at once.

There is **no repair kind, no recovery key, and nothing to prove** — no losing-branch commitment, no
content-only guard walk. Burial is by **position + descent**: the burying `Rot`'s seal-cap locks the
loser's first event below the new seal, and the descent rule kills its growth. A content fork on a
witnessed chain is prevented upstream (the majority floor); the recovery `Rot` is the resolution for
the residual (an owner burying a compromised content run, or a lagging-node content fork).

**Recovery closes the fork window; the rotation closes new forks.** One recovery `Rot` buries the
whole current fork, and its key rotation then closes the culprit's ability to mint a **new** fork:
they lack the new signing key, so after the rotation propagates they can mint no more. A sustained
signing-key adversary merely spews **dead** content into a **bounded** fork (depth-capped at 64 per
lineage, breadth bounded by retention + the one-content-sibling witnessing rule) — then the
depth-cap forces a seal-advancer.

## The reserve defends the signing key, not the rotation key

The rotation reserve is what makes recovery a real cryptographic boundary, not a policy convention.
A party who lacks the reserve cannot produce a rotation against the parent's `rotationHash`
commitment, regardless of what other key material they hold. But that boundary defends the
**signing** key only:

- **A tier-1 (signing-key) compromise is fully recoverable.** The adversary can land `Ixn` content;
  a recovery `Rot` at the root buries the whole tail (all content) → every anchored downstream event
  dead by descent, no reincept.
- **A tier-2 (reserve) theft is the point of no return.** When an adversary holds the reserve and
  lands `Rot_adversary` at `v_N`, the chain is **the attacker's** — there is **no in-band
  recourse**; the legitimate party **reincepts** (for a delegated KEL, the delegator `Dth`s it
  instead). Three structural facts close every escape:

  - **You cannot bury the `Rot`.** `Rot_adversary` is a sealed event, and only content (`Ixn`) is
    buriable ([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery),
    rule 1). Burying "the adversary's" `Rot` would require a rule that could bury **any** `Rot`
    (including a legitimate operator's), resurrecting retired key material — the backdate surface
    vdti closes by treating `Rot` as a sealed branch (never buriable).
  - **The seal-cap blocks a recovery at `v_{N-1}`.** `Rot_adversary` is seal-advancing, so it
    advances the seal to `v_N`; a recovery `Rot` targeting `v_{N-1}` is then below the seal →
    `Sealed`. The legitimate party cannot even submit it.
  - **A competing `Rot` is a second sealed branch.** A `Rot_legitimate` extending `v_{N-1}` lands as
    a sibling of `Rot_adversary` — two sealed branches → `disputed`, terminal
    ([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)).

  A hostile `Rot` at a _forked_ position is likewise the reserve-theft takeover, not a recoverable
  fork. So the only defense against reserve theft is one layer up — IEL threshold redundancy evicts
  the compromised member via an `Evl` ([§Defense layers above KEL](#defense-layers-above-kel)) —
  never by salvaging this chain. Reserve theft is unrecoverable → reincept.

## Locked-portion bound makes recovery cross-node-validatable

A recovery `Rot` extends from one of two parent shapes (see
[§Recovery attach shapes](#recovery-attach-shapes)). The **ancestor-extending shape** — where
`Rot.previous = v_{d-1}.said` (the divergence ancestor) — has a structural property that makes
recovery cross-node-validatable: `v_{d-1}` is the unique shared parent of all events at `v_d`, and
`v_{d-1}` itself lands cleanly on the linear chain before any divergence. So `v_{d-1}` is
structurally identical on every node that holds the chain, regardless of which divergent contents
each node received.

A recovery `Rot` extending `v_{d-1}` therefore validates uniformly:

- Every node sees the same `v_{d-1}` content (it's part of the locked or pre-divergence portion).
- The `Rot` signs against the same commitment (`v_{d-1}.rotationHash`) on every node.
- The resolution is uniform: the `Rot` advances the seal past `v_d`, so every competing branch at
  `v_d` (and everything grown on it) sits below the new seal, dead by position + descent — an
  outcome every node computes identically, with no submitter-supplied fork commitment to trust.

This is what makes the ancestor-extending shape cross-node-validatable. A tip-extension that keeps
the submitter's own branch is also cross-node-checkable (validated against that retained tail), but
only the `v_{d-1}` attach needs no fetch.

### Locked-portion bound

The merge layer enforces the locked-portion bound: `Rot.previous.serial >= seal_serial`. The bound
prevents revival attacks where a party holding stale authority (a reserve already revealed — spent —
by an earlier `Rot` / `Wit`, or a signing key that has since been rotated out) constructs an event
targeting the locked portion to rearrange the chain. Only current authority gates further extension.

When the bound holds vacuously — no seal-advancing event has landed yet on the chain (only inception
plus content events) — a recovery `Rot`'s `previous` may be any chain event including the inception.
Once any seal-advancing event advances the seal past `v_{N-1}`, an event targeting `v_{N-1}` is
rejected as `Sealed`.

See [§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery) for the
structural rule and
[§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded) for the seal-cap
that derives from it.

## Recovery attach shapes

You attach the burying `Rot` at your **last good event**, retaining your branch and burying every
competing content branch below the new seal. `Rot.previous` takes one of two shapes.

### Branch-tip-extending shape

`Rot.previous` is your own branch tip at `v_d`. The `Rot` extends that branch at `v_{d+1}`; the
other branch's first event is below the new seal, dead by descent.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ retained-branch tip @ v_d
                   └─ other-branch root   @ v_d

Recovery: rot.previous = retained-branch tip's said
          rot.serial   = d + 1

Post-state (linear, recovered):
    ... → v_{d-1} → retained-branch tip @ v_d → rot @ v_{d+1}
                  ↑
                  other branch below the advanced seal → dead by descent
```

The submitter keeps the branch they authored; the burying `Rot` extends it and advances the seal, so
the competing branch (its first event now below the seal) and everything grown on it are dead by
descent — no submitter-supplied commitment, no content-only guard walk. Every competing content
branch closes the same way; a competing **sealed** branch is never buried (≥ 2 sealed → `disputed`).

### Ancestor-extending shape

`Rot.previous` is `v_{d-1}`, the divergence ancestor. The `Rot` lands at `v_d`; every branch at
`v_d` is a sibling of the `Rot`, barred by the seal-cap (its parent `v_{d-1}` now sits below the
advanced seal), its growth dead by descent; the `Rot` is the only canonical event at `v_d` after
recovery.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ branch-1 root @ v_d
                   └─ branch-2 root @ v_d

Recovery: rot.previous = v_{d-1}.said
          rot.serial   = d

Post-state (linear, recovered, rot is the only canonical event at v_d):
    ... → v_{d-1} → rot @ v_d
                  ↑
                  both branches below the advanced seal → dead by descent
```

The ancestor-extending shape is the structural primitive that gives recovery its
cross-node-validatable property (§Locked-portion bound makes recovery cross-node-validatable). It is
the recourse when the submitter authored nothing it wants to preserve at or beyond `d` — either it
authored nothing there, or it chooses to discard its own content branch: attaching at `v_{d-1}`
buries everything at or beyond `d`, the submitter's own content included. Every branch here is
tier-1 content, so nothing sealed is overturned.

### Routing through the merge layer

Both attach shapes route through the merge layer. A recovery `Rot` is an ordinary sealed extension —
its acceptance buries the losing content by position + descent rather than producing a divergence. A
sealed event sharing the ancestor-extending parent shape (`previous = v_{d-1}.said`) on a chain that
already holds a sealed event at `v_d` is a **second** sealed branch → `disputed`; a burying `Rot`
extending the winning branch's own tip is the recovery. See
[`merge.md` §Full path](merge.md#full-path-divergence-recovery-overlap).

## Pre-seal verifiability

The locked-portion bound, the seal-cap, and the recovery rotation together produce a durable
consumer guarantee: events at-or-below `last_seal_advancing_event` remain structurally verifiable
indefinitely, regardless of subsequent divergence or a terminal `disputed` verdict above the seal.
One qualifier: the permanence claims run against the last **clean** seal — one with no competing
sealed branch forking at-or-below it. Sealed events are never rewritten, but a below-seal **sealed**
fork is a spine fork that flips the prefix's reading to `disputed`; permanence then retreats to the
last clean seal beneath the fork
([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery), _Pre-seal
verifiability_).

The argument has three legs:

- **Seal advances are clean.** `last_seal_advancing_event` advances only on seal-advancing events
  (`Rot` / `Wit` / `Trm`) that land cleanly on the linear chain. The seal never forks — a sealed
  event that would create or join a divergence does not extend the canonical chain, so every seal
  advance is a clean linear-chain landing.
- **At-or-below-seal events were authored under tier-2 capability.** Every seal advance is a clean
  sealed landing, which requires the rotation reserve. The protocol accepts that authoring as
  structurally valid sealing-level authority regardless of submitter identity (which the chain layer
  has no concept of).
- **The locked portion cannot be rearranged.** The locked-portion bound denies any future event from
  targeting the locked portion; the seal-cap denies any forward extension whose parent is in the
  locked portion. Together they make the at-or-below-seal segment structurally immutable.

Consumers and dependents that resolve to at-or-below-seal state get the strongest protocol
guarantee:

- **Anchors hosted at-or-below the seal stay anchored.** A KEL `Ixn` that anchored an IEL or SEL
  event at-or-below the seal continues to satisfy the anchor check, regardless of subsequent
  divergence above the seal.
- **Credentials issued under an IEL state at-or-below the seal remain verifiable.** An issuance
  pinned to a KEL anchor in the locked portion stays trust-evaluable forever.
- **SELs bound at-or-below-seal via their top-level `pin` stay trust-evaluable.** The
  cross-primitive bound that enforces this is checked by IEL / SEL verifiers; the KEL primitive's
  contribution is the locked-portion immutability.
- **Audit and forensic queries against the locked portion are truthful.** Above-seal events appear
  in the forensic record but are not structurally trustworthy (they may have been authored under
  captured tier-1 authority); the locked-portion events are.

Above-seal content is structurally indistinguishable from work authored under captured authority.
The boundary is the **seal**: an anchor at-or-below the seal is canonical and final on a chain's
verification token regardless of any above-seal divergence; an anchor above the seal becomes durable
only when a later seal-advancing event lands cleanly past it — and on a `disputed` chain (which
never seals past it) it grounds no new trust. See
[§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery) (_Pre-seal
verifiability_) for the cross-primitive framing and
[§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported)
for the verifier-reports / consumer-composes split.

### Above-seal submitter indistinguishability

Above-seal events that landed under valid authorization at the time they were processed do not carry
"who actually submitted them" information. The same authorization that admitted a legitimate
operator's event would admit an adversary's event under captured authority. The protocol has no
trusted way to bring out-of-band claims about above-seal authorship into the chain — verification
tokens cannot be augmented with claims that originated outside the chain. Consumers may apply their
own out-of-band judgment about specific above-seal events; the protocol cannot make those judgments
for them.

## Cross-node sealed-vs-sealed races

Two federation nodes can each accept a competing sealed event extending `v_{d-1}` via independent
linear-chain extensions: each event lands cleanly on its submitting node (the seal advances
locally), gossip then delivers each event to the other node, and the seal-cap **rejects each late
arrival as a canonical extension but retains it as non-canonical evidence** (keep-all-data) — the
locally-landed first-receive already occupies the target serial behind the now-advanced seal.

Per-node, each chain stays linear with its own first-receive as tip — but each node now **holds both
branches** and reads the divergence by a **data-local walk**: two sealed branches past the fork read
**`disputed`**
([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)). The
**witness beacon** enumerates the competing branch SAIDs so a one-branch holder fetches and walks
the rest — a selected witness signs up to **two** distinct structurally-valid **sealed** siblings
per chain position (two both-witnessed siblings are the `disputed` proof, then further ones are
declined), and adjacent receipts at the same chain position carrying different `witnessed_said`
values are the evidence that a divergence exists at that position. The federation **propagates** the
branches; the verdict is the verifier's own walk.

The cross-node race surface covers all sealed-event shapes:

- **A `{Rot, Rot}` divergence is a proof of rotation-reserve compromise** — two valid rotations
  reveal the one reserve preimage in force at `v_{d-1}`. The forging bar is tier-2 (the reserve).
  Once an adversary's rotation has landed on any federation node, no in-band protocol recourse
  exists.
- **A `{Wit, Wit}` or `{Trm, *}` sealed divergence** is terminal the same way — any two sealed
  branches past the fork read `disputed`.

The CAP-axis trade-off is structural. The seal-cap and locked-portion bound prevent stale-authority
chain rearrangement: a party holding past-position private keys must not be able to land an event
targeting the locked portion at any future time. Relaxing the bounds to admit a competing sealed
event as a _canonical_ extension at a sealed serial would re-open the long-tail killswitch surface.
The bounds stay unconditional; the competing branch is retained as evidence, not extended onto, and
the divergence is resolved data-locally rather than by fork-merging.

### Operator response to a disputed prefix

When a data-local walk finds a prefix **disputed** (two or more sealed branches past the fork), no
further extension on that prefix is consumer-trustable at-and-beyond the divergent serial. Operator
recourse is **reincept under a new prefix**. The pre-seal verifiability guarantee bounds the damage:
at-or-below-seal anchors, credentials, and SEL bindings stay verifiable; only forward-extending
operations against above-seal state lose their trust grounding. See
[§Cascade-reincept honesty](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
for the cross-primitive cascade rules.

## Defense layers above KEL

KEL recovery closes the tier-1 (content) surface structurally; tier-2 (reserve theft) has no in-band
defense — once an adversary rotation lands, the chain reincepts. The post-rotation tier-2 surface is
closed by the layers composed above KEL:

- **IEL threshold composition.** Threshold-redundant governance (`M > N` across distinct custodians,
  where `M` is the roster size and `N` the threshold — the roster has more members than the
  threshold requires) tolerates single-KEL tier-2 compromise. The surviving members rotate the
  compromised KEL out via the IEL's `Evl` event (a `cut`) without losing the IEL prefix.
- **Custody separation.** KEL-internal custody hygiene (the reserve on a different device,
  HSM-resident, ceremony-gated) raises the practical bar to acquire the reserve. This is operational
  hardening; the protocol is custody-agnostic.
- **Federation witnessing.** Competing **sealed** events at the same chain position are both
  witnessed — a selected witness signs up to two distinct sealed siblings per position, and two
  both-witnessed siblings are the `disputed` proof — so both accumulate receipts from the witness
  pool, and the beacon enumerates the branches as the evidence a verifier walks. Reserve-tier
  compromise without a federation partition cannot get a fork past detection — any verifier holding
  both branches reads the prefix as `disputed` and refuses to bind. (A competing **content**
  sibling, by contrast, is declined after the first seen at a position — under the majority floor a
  content fork on a witnessed chain is prevented, not merely detected; federation doctrine.)

The combined attack — reserve-tier compromise PLUS adversary-controlled federation partition — is
the structurally unavoidable CAP failure mode. KEL guarantees the divergence is **detectable**
post-resolution rather than preventing it: receipts are indexed at chain position rather than at
event SAID, so when gossip resolves the partition the competing receipts land in the same row group
on each node, the beacon enumerates the competing branches, and the divergence becomes structurally
observable in the data layer. See
[§Limit of the doctrine — current-state compromise](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: two-tier capability model, signature shape,
  forward-key commitments, seal-advance cap.
- [`merge.md`](merge.md) — merge-layer routing: routing order, sealed-event handling, locked-portion
  bound enforcement.
- [`reconciliation.md`](reconciliation.md) — cross-node convergence proof; race matrix;
  effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery; the universal recovery rule; recovery conditions.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound; the spine.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
  — limit of the doctrine; layered defense; adversary patience; cascade-reincept honesty.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (subsequent sub-issue): the kind-scoped witnessing ladder, the majority floor, the
  beacon, divergent witness receipts.
- [`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md) —
  operator CLI ceremony (subsequent sub-issue).
