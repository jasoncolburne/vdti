# KEL Recovery — Structural Defense Doctrine

KEL recovery is the structural mechanism that lets a chain resolve divergence and defend against
tiered key compromise without surrendering the locked portion. This doc states the doctrine: what
compromise scenarios the design defends against, why dual-signature plus recovery-key preimage
closes those scenarios, why the locked-portion bound makes recovery cross-node-validatable, and how
pre-seal verifiability composes with the three-tier compromise model.

This is doctrine, not workflow. Operator CLI ceremony and the choreography for `Rec` / `Ror` / `Dec`
lives in
[`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md)
(subsequent sub-issue). Per-kind event-shape rules live in [`events.md`](events.md); merge-layer
routing in [`merge.md`](merge.md); the cross-node correctness proof in
[`reconciliation.md`](reconciliation.md).

## Three-tier compromise model

The defense surface KEL recovery covers is structured by tier — the cryptographic material an
adversary holds. Each tier names what the adversary needs and only what they need; the old signing
key is not a prerequisite for tier 2 or tier 3. See
[`events.md` §Three-tier capability model](events.md#three-tier-capability-model) for the canonical
capability statement.

| Tier | Adversary holds                                  | Adversary can forge            | Defense                                                                                                                                                                                                                                                          |
| ---- | ------------------------------------------------ | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Current signing key.                             | `Ixn`.                         | A forked content branch is archived by `Rec` (content is archivable — this is what the recovery reserve defends); a linear takeover is rotated out via `Rot`.                                                                                                    |
| 2    | Rotation-key preimage alone.                     | `Rot`.                         | **Proactive only:** rotate-recovery via `Ror` _before_ the adversary rotates, retiring the preimage they hold. Once their `Rot` lands it is a privileged event no repair can archive → **reincept** (the reserve defends the signing key, not the rotation key). |
| 3    | Rotation-key preimage AND recovery-key preimage. | `Ror` / `Rec` / `Wit` / `Dec`. | No in-band recourse. The protocol provides no recovery primitive against tier-3 compromise; defense is operational (custody separation, threshold redundancy at the IEL layer, abandon-and-reincept).                                                            |

The protocol's recovery primitive `Rec` closes the **tier-1 (content) surface** — it archives an
adversary's content branch, which is what the recovery reserve defends: the **signing** key, never
the rotation key. Tier-2 is defended only **proactively** (`Ror` before the adversary rotates); once
an adversary `Rot` lands it is a privileged event no repair can archive → **reincept**. Tier-3 has
no in-band defense. Post-rotation tier-2 and tier-3 defense is the responsibility of the layers
composed above KEL (IEL governance with threshold redundancy across distinct custodians; see
[§Limit of the doctrine — current-state compromise](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)).

## Rec versus Ror — repair versus proactive rotation

KEL has two distinct recovery primitives. They are not interchangeable.

- **`Rec` is the repair.** It resolves an already-divergent chain: `Rec` keeps the repairing branch
  and archives the rest — **content-only** archival tails, condemned by the roots committed in its
  `forks` (a privileged event in any competing branch makes the fork terminal → reincept, never
  archived) — and returns the chain to Active. Reveals the current recovery-key preimage as a side
  effect of dual-signing: that preimage is spent, but `Rec` commits a fresh recovery commitment (a
  new `recoveryHash`), so the chain stays recoverable.
- **`Ror` is proactive.** Used pre-emptively — to rotate both signing and recovery keys for
  forward-secrecy hygiene, or to refresh the recovery-key preimage commitment per operator cadence
  guidance. `Ror` is not divergence-driven; it lands as a linear extension of a non-divergent chain.

Both reveal the current recovery-key preimage and commit a new one (`Ror` and `Rec` both populate
`recoveryKey` + `recoveryHash`). The difference is structural lifecycle role:

- **Divergence has happened** → `Rec`. The chain is Divergent (frozen); `Rec` is the only event
  class that can resolve it without operator-side reincept under a new prefix.
- **Pre-emptive rotation** → `Ror`. The chain is Active; the operator wants to rotate both keys
  before any compromise indicator fires.

Don't conflate. Operator guidance for "the chain is divergent, what now?" is `Rec`. Operator
guidance for "scheduled rotation cadence" is `Ror`. The two primitives map to different lifecycle
moments and produce different chain-state outcomes.

## Dual-signature is the tier-3 defense

`Rec` / `Ror` / `Wit` / `Dec` are dual-signed: one signature by the new signing key (revealed by the
rotation-key preimage), one signature by the recovery key (revealed by the recovery-key preimage).
Both signatures must verify; both digest commitments (`digest(publicKey) == prior.rotationHash` and
`digest(recoveryKey) == prior.recoveryHash`) must match.

The dual-signature requirement is what makes these events structurally tier-3:

- **Forging the primary signature requires the rotation preimage.** A tier-1 adversary holding only
  the current signing key cannot satisfy this leg — the rotation preimage is committed by the prior
  establishment's `rotationHash` and not yet revealed.
- **Forging the recovery signature requires the recovery preimage.** A tier-2 adversary holding only
  the rotation preimage cannot satisfy this leg — the recovery preimage is independently committed
  by the prior establishment's `recoveryHash`.
- **Both signatures over the SAID.** The signatures commit to the event's content (via the SAID,
  which hashes the canonical bytes). An adversary cannot substitute a different recovery-key
  preimage to bypass the commitment check — the prior establishment's `recoveryHash` pins what
  preimage satisfies.

This is the structural property that makes recovery a real cryptographic boundary, not a policy
convention. A party who lacks the recovery-key preimage cannot produce a `Rec` against the parent's
commitments, regardless of what other key material they hold.

### A tier-2 `Rot` takeover is the point of no return

When an adversary holds the rotation-key preimage and lands `Rot_adversary` at `v_N`, the chain is
**the attacker's** — there is **no in-band recourse**; the legitimate party **reincepts** (for a
delegated KEL, the delegator `Kil`s it instead). The recovery reserve defends the **signing** key (a
tier-1 content compromise), **not** the rotation key. Three structural facts close every escape:

- **`Rec` cannot archive the `Rot`.** `Rot_adversary` is a privileged event, and only content
  (`Ixn`) is archivable
  ([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair), rule 1). A
  `Rec` that committed `Rot_adversary` to its `forks` would archive a privileged event — forbidden,
  and **identity-blind on purpose**: if a recovery-key holder could archive "the adversary's" `Rot`,
  they could archive **any** `Rot` (including a legitimate operator's), resurrecting retired key
  material — the backdate surface vdti closes by treating `Rot` as a privileged branch (never
  archivable).
- **The seal-cap blocks a repair at `v_{N-1}`.** `Rot_adversary` is seal-advancing, so it advances
  the seal to `v_N`; a `Rec` targeting `v_{N-1}` is then below the seal → `SiblingLocked`
  ([§Repair-event bound](#repair-event-bound-condition-2b)). The legitimate party cannot even submit
  it.
- **A competing `Rot` is a second privileged branch.** A `Rot_legitimate` extending `v_{N-1}` lands
  as a sibling of `Rot_adversary` — two privileged branches → `disputed:`, terminal
  ([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair)).

The legitimate party _does_ hold the recovery preimage the adversary lacks (the dual-signature
crypto boundary above) — but that buys nothing here, because there is no permitted move to spend it
on. The **only** tier-2 defense is therefore **proactive**: rotate-recovery via `Ror` _before_ the
adversary rotates, retiring the preimage they hold. Once their `Rot` lands, survivability is decided
one layer up — IEL threshold redundancy evicts the compromised member via a `Evl`
([§Defense layers above KEL](#defense-layers-above-kel)) — never by salvaging this chain.

## Locked-portion bound makes recovery cross-node-validatable

A `Rec` extends from one of two parent shapes (see [§Rec parent shapes](#rec-parent-shapes)). The
**divergence-ancestor-extending shape** — where `Rec.previous = v_{d-1}.said` (the divergence
ancestor) — has a structural property that makes recovery cross-node-validatable: `v_{d-1}` is the
unique shared parent of all events at `v_d`, and `v_{d-1}` itself lands cleanly on the linear chain
before any divergence. So `v_{d-1}` is structurally identical on every node that holds the chain,
regardless of which divergent contents each node received.

A `Rec` extending `v_{d-1}` therefore validates uniformly:

- Every node sees the same `v_{d-1}` content (it's part of the locked or pre-divergence portion).
- The `Rec` signs against the same commitments (`v_{d-1}.rotationHash`, `v_{d-1}.recoveryHash`) on
  every node.
- The repair's resolution is uniform: every node validates the same committed roots — each must be a
  competing child of the fork point `v_{d-1}`, off the full-span `Rec.previous` walkback (a root on
  the retained chain, or `v_{d-1}` itself, rejects the `Rec`) — and **independently** walks every
  competing branch it holds (or the beacon enumerates), rejecting the `Rec` if any carries a
  privileged event, rather than trusting the submitter's `forks`. Independent computation is what
  makes the resolution identical on every node.

This is what makes the divergence-ancestor-extending shape the structural primitive that solves
cross-node propagation. A tip-extension or combined-digest approach would not have this property —
the "tip" each node sees may differ across the divergence, and an attempt to recover by extending a
tip would commit to a node-local choice the rest of the federation can't replicate. A repair
attaching at the submitter's own tail instead is validated against that retained tail plus the
committed `forks[]` (fetched via keep-all-data / the beacon) — also cross-node-checkable, but only
the `v_{d-1}` attach needs no fetch.

### Repair-event bound (condition 2b)

The merge layer enforces the repair-event bound: `Rec.previous.serial >= seal_serial`. The bound
prevents revival attacks where a party holding stale authority (a recovery preimage revealed by an
earlier `Rec` / `Ror` / `Wit`, or a key that has since been rotated out) constructs a `Rec`
targeting the locked portion to rearrange the chain. Only current authority gates repair events.

When the bound holds vacuously — no privileged event has landed yet on the chain (only inception
plus content events) — `Rec.previous` may be any chain event including the inception. Once any
privileged event advances the seal past `v_{N-1}`, a `Rec` targeting `v_{N-1}` is rejected as
`SiblingLocked`.

See [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair) for the
structural rule and
[§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded) for the seal-cap
that derives from it.

## Rec parent shapes

`Rec` resolves divergence by committing, in its `forks`, the **root** of each losing branch — the
branch's first divergent event, which condemns its entire subtree. `Rec.previous` takes one of two
shapes:

### Branch-tip-extending shape

`Rec.previous` is a branch tip at `v_d`. Rec extends that branch at `v_{d+1}`; the other branch
becomes an archival tail, condemned by its root.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ retained-branch tip @ v_d
                   └─ other-branch root   @ v_d

Rec construction: rec.previous = retained-branch tip's said
                  rec.serial   = d + 1
                  rec.forks = [ other-branch root ]

Post-state (linear, recovered):
    ... → v_{d-1} → retained-branch tip @ v_d → rec @ v_{d+1}
                  ↑
                  other branch condemned via its root in rec.forks
```

The submitter (whoever holds the recovery key) keeps the branch they authored as the retained
branch; `Rec` extends it, naming the root of every losing branch (its first divergent event — here
the losing branch's head at `v_d`, which is its root) in `forks` — each root condemning its whole
subtree, so anything grown on the branch after the repair is dead by descent. The merge layer then
**independently** identifies the retained branch by walking back from `Rec.previous` over the full
span, **rejects** any committed root that lies on that walkback (no self-condemnation), and walks
every competing branch off it that it holds — content-only, rejecting the `Rec` if any carries a
privileged event. It never trusts the submitter's enumeration.

### Divergence-ancestor-extending shape

`Rec.previous` is `v_{d-1}`, the divergence ancestor. Rec lands at `v_d`. The root of every branch
at `v_d` is committed to `forks` (here each branch head at `v_d` is its root); `Rec` is the only
event at `v_d` after the repair runs.

```
Pre-state (divergent at v_d):
    ... → v_{d-1} ─┬─ branch-1 root @ v_d
                   └─ branch-2 root @ v_d

Rec construction: rec.previous = v_{d-1}.said
                  rec.serial   = d
                  rec.forks = [ branch-1 root, branch-2 root ]

Post-state (linear, recovered, Rec is the only event at v_d):
    ... → v_{d-1} → rec @ v_d
                  ↑
                  both prior branches condemned via their roots in rec.forks
```

The divergence-ancestor-extending shape is the structural primitive that gives recovery its
cross-node-validatable property (§Locked-portion bound makes recovery cross-node-validatable). It is
the recourse when the submitter does not want to preserve either of the existing branches at `v_d` —
for instance, when both branches were authored under tier-1 capability and neither carries content
the submitter wants to keep.

### Routing through the discriminator

Both parent shapes route through the merge layer's discriminator. `Rec` is the repair kind, not a
privileged extension — its acceptance resolves the divergence rather than producing one. A
privileged event (`Rot` / `Ror` / `Wit` / `Dec`) sharing the divergence-ancestor-extending parent
shape (`previous = v_{d-1}.said`) on a chain with an existing event at `v_d` is declined as a
canonical extension per
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair); the kind
discriminator (repair `Rec` versus privileged) determines whether the parent shape resolves the
divergence or is retained as evidence.

## Pre-seal verifiability

The locked-portion bound, the seal-cap, and the recovery primitives together produce a durable
consumer guarantee: events at-or-below `last_seal_advancing_event` remain structurally verifiable
indefinitely, regardless of subsequent divergence or a terminal `disputed:` verdict above the seal.
One qualifier: the permanence claims run against the last **clean** seal — one with no competing
privileged branch forking at-or-below it. Sealed events are never rewritten, but a below-seal
**privileged** fork is a spine fork that flips the prefix's reading to `disputed:`; permanence then
retreats to the last clean seal beneath the fork
([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair), _Pre-seal
verifiability_).

The argument has three legs:

- **Seal advances are clean.** `last_seal_advancing_event` advances only on seal-advancing events
  (`Rot` / `Ror` / `Rec` / `Wit` / `Dec`) that land cleanly on the linear chain. The seal never
  forks: a privileged event that would create or join a divergence does not extend the canonical
  chain, so every seal advance is a clean linear-chain landing.
- **At-or-below-seal events were authored under at-least-tier-2 capability.** Every seal advance is
  a clean privileged or repair landing — both classes require tier-2 or tier-3 capability. The
  protocol accepts that authoring as structurally valid sealing-level authority regardless of
  submitter identity (which the chain layer has no concept of).
- **The locked portion cannot be rearranged.** The repair-event bound denies any future `Rec` from
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
only when a later seal-advancing event lands cleanly past it — and on a `disputed:` chain (which
never seals past it) it grounds no new trust. See
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair) (_Pre-seal
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

## Cross-node privileged-vs-privileged races

Two federation nodes can each accept a competing privileged event extending `v_{d-1}` via
independent linear-chain extensions: each event lands cleanly on its submitting node (the seal
advances locally), gossip then delivers each event to the other node, and the seal-cap **rejects
each late arrival as a canonical extension but retains it as non-canonical evidence**
(keep-all-data) — the locally-landed first-receive already occupies the target serial behind the
now-advanced seal.

Per-node, each chain stays linear with its own first-receive as tip — but each node now **holds both
branches** and reads the divergence by a **data-local walk**: two privileged branches past the fork
read **`disputed:`**
([§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair)). The **witness
beacon** enumerates the competing branch SAIDs so a one-branch holder fetches and walks the rest —
federation members witness every structurally-valid event they observe (always-witness), and
adjacent receipts at the same chain position carrying different `witnessed_said` values are the
evidence that a divergence exists at that position. The federation **propagates** the branches; the
verdict is the verifier's own walk.

The cross-node race surface covers all privileged-event shapes:

- **Tier-2 path.** A tier-2 adversary (holding only the rotation preimage) can force non-convergence
  by racing `Rot_adversary` against an honest concurrent `Rot_operator` or `Ror_operator` on
  different federation nodes. The forging bar is tier-2 (one preimage), strictly easier than the
  tier-3 bar required for `Ror` / `Rec` / `Wit` / `Dec`. A `{Rot, Rot}` divergence is moreover a
  **proof of rotation-reserve compromise** — two valid rotations reveal the one rotation preimage in
  force at `v_{d-1}`.
- **Tier-3 path.** A tier-3 adversary (holding both preimages) can force non-convergence by racing
  any recovery-revealing event against operator submissions. Once an adversary's tier-3 event has
  landed on any federation node, no in-band protocol recourse exists.

The CAP-axis trade-off is structural. The seal-cap and locked-portion bound prevent stale-authority
chain rearrangement: a party holding past-position private keys must not be able to land an event
targeting the locked portion at any future time. Relaxing the bounds to admit a competing privileged
event as a _canonical_ extension at a sealed serial would re-open the long-tail killswitch surface.
The bounds stay unconditional; the competing branch is retained as evidence, not extended onto, and
the divergence is resolved data-locally rather than by fork-merging.

### Operator response to a disputed prefix

When a data-local walk finds a prefix **disputed** (two or more privileged branches past the fork),
no further extension on that prefix is consumer-trustable at-and-beyond the divergent serial.
Operator recourse is **reincept under a new prefix**. The pre-seal verifiability guarantee bounds
the damage: at-or-below-seal anchors, credentials, and SEL bindings stay verifiable; only
forward-extending operations against above-seal state lose their trust grounding. See
[§Cascade-reincept honesty](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
for the cross-primitive cascade rules.

## Defense layers above KEL

KEL recovery closes the tier-1 (content) surface structurally; tier-2 is defended only
**proactively** (`Ror` before the adversary rotates — once a `Rot` lands, the chain reincepts). The
post-rotation tier-2 and tier-3 surfaces are closed by the layers composed above KEL:

- **IEL threshold composition.** Threshold-redundant governance (`M > N` across distinct custodians,
  where `M` is the threshold count and the roster has more candidates than the threshold requires)
  tolerates single-KEL tier-3 compromise. The surviving members can rotate the compromised KEL out
  via the IEL's `Evl` event without losing the IEL prefix.
- **Custody separation.** KEL-internal custody hygiene (recovery key on a different device,
  HSM-resident, ceremony-gated) raises the practical bar to acquire both rotation and recovery
  preimages simultaneously. This is operational hardening; the protocol is custody-agnostic.
- **Federation witnessing.** Under always-witness, competing privileged events at the same chain
  position both accumulate receipts from the witness pool, and the beacon enumerates the branches as
  the evidence a verifier walks. Rotation-tier compromise without a federation partition cannot get
  a fork past detection — any verifier holding both branches reads the prefix as `disputed:` and
  refuses to bind.

The combined attack — rotation-tier compromise PLUS adversary-controlled federation partition — is
the structurally unavoidable CAP failure mode. KEL guarantees the divergence is **detectable**
post-resolution rather than preventing it: receipts are indexed at chain position rather than at
event SAID, so when gossip resolves the partition the competing receipts land in the same row group
on each node, the beacon enumerates the competing branches, and the divergence becomes structurally
observable in the data layer. See
[§Limit of the doctrine — current-state compromise](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: three-tier capability model, dual-signature shape,
  forward-key commitments, seal-advance cap.
- [`merge.md`](merge.md) — merge-layer routing: discriminator algorithm, privileged-event handling,
  repair-event bound enforcement.
- [`reconciliation.md`](reconciliation.md) — cross-node convergence proof; race matrix;
  effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-repair) —
  divergence and repair; the universal recovery rule; repair conditions.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound; the spine.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
  — limit of the doctrine; layered defense; adversary patience; cascade-reincept honesty.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (subsequent sub-issue): always-witness, the beacon, divergent witness receipts.
- [`../../../../operations/recovery-workflow.md`](../../../../operations/recovery-workflow.md) —
  operator CLI ceremony (subsequent sub-issue).
