# KEL Compromise & Structural Defense Doctrine

This doc states the KEL's compromise doctrine: what tiered key-compromise scenarios the design
defends against, why the rotation reserve is a real cryptographic boundary (and what it does **not**
defend), the durable guarantee that survives any divergence, and how the layers above KEL close what
the KEL alone cannot. Recovery is not a special action — it is a plain rotation that buries — so its
mechanics (burial by position + ascent, the two attach shapes) live with the merge layer, and
cross-node races with the correctness proof; this doc is the **why**, not the how.

**In short.** A KEL holds one identity's signing keys, and there are two things an attacker can
steal — with very different outcomes:

- **The current signing key** — the attacker can post ordinary content, but you recover: rotate to a
  fresh key, and that one rotation buries everything they did. Fully recoverable.
- **The rotation reserve** (the secret that authorizes the next rotation) — the attacker can rotate
  the chain to a key of their own, and there is no in-band fix; the chain is theirs, and you start
  over under a new identity. The defense against that lives one layer up, where several keys back
  one identity, so losing one is survivable.

This is doctrine, not workflow — the operator ceremony is simply issuing the burying recovery `Rot`
(or `Trm`) at the first compromised position with the standard tooling. Per-kind event-shape rules
live in [`events.md`](events.md); merge-layer routing — including how a burying seal-advancer
resolves a fork and the attach shapes — in [`merge.md`](merge.md); the cross-node correctness proof
in [`reconciliation.md`](reconciliation.md).

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
  and anything grown from a dead point is dead too (**deadness ascends** — an event whose parent is
  dead is dead). You go for the **root**, not their tip, so however long a run the thief piled on,
  it all hangs off that one point and dies at once.

**Burial is any seal-advancer's doing, not a `Rot`'s alone.** Any seal-advancer — a `Rot`, a `Wit`,
or a `Trm` (which buries then terminates) — advances the seal, and everything the new seal passes
drops by position + ascent. So a fork can resolve **incidentally**: a standard `Wit` (a federation
rebind) you were committing anyway lands past a content loser and buries it — you never set out to
recover, the seal-advance just did it. What is `Rot`-specific is the **deliberate** act: when you
set out to _resolve_ a fork, you author a **`Rot`**, for two reasons — a `Rot` is **always
available** (a `Wit` carries the must-change-substrate/federation/witnesses constraint, so you
cannot fire a bare `Wit` purely to recover), and its rotation is what **closes new forks** by
rotating the compromised signing key out: **recovery closes the fork window; the rotation closes new
forks.** One recovery `Rot` buries the whole current fork, and its key rotation then denies the
culprit the new signing key, so after it propagates they can mint no more. A sustained signing-key
adversary merely spews **dead** content into a **bounded** fork (depth-capped at
`MAXIMUM_UNSEALED_RUN` per lineage, breadth bounded by retention + the one-content-sibling
witnessing rule) — then the depth-cap forces a seal-advancer. (The burial mechanics and the two
attach shapes are the merge layer's —
[`merge.md` §How a burying seal-advancer resolves a content fork](merge.md#how-a-burying-seal-advancer-resolves-a-content-fork).)

There is **no repair kind, no recovery key, and nothing to prove** — no losing-branch commitment, no
content-only guard walk. A content fork on a witnessed chain is prevented earlier (the witnessing
floor); recovery is the resolution for the residual (an owner burying a compromised content run, or
a lagging-node content fork). Because the locked-portion bound
([`log.md` §The seal, the spine, and the locked-portion bound](log.md#the-seal-the-spine-and-the-locked-portion-bound))
holds the divergence ancestor `v_{d-1}` identical on every node, the resolution is
**cross-node-validatable** — its mechanics (both attach shapes) are the merge layer's
([`merge.md` §Recovery attach shapes](merge.md#recovery-attach-shapes)).

## The reserve defends the signing key, not the rotation key

The rotation reserve is what makes recovery a real cryptographic boundary, not a policy convention.
A party who lacks the reserve cannot produce a rotation against the parent's `rotationHash`
commitment, regardless of what other key material they hold. But that boundary defends the
**signing** key only:

- **A tier-1 (signing-key) compromise is fully recoverable.** The adversary can land `Ixn` content;
  a recovery `Rot` at the root buries the whole tail (all content) → every event anchored to that
  tail dead on ascent, no reincept.
- **A tier-2 (reserve) theft is the point of no return.** When an adversary holds the reserve and
  lands `Rot_adversary` at `v_N`, the chain is **the attacker's** — there is **no in-band
  recourse**; the legitimate party **reincepts** (for a delegate identity, the delegator `Dth`s it
  instead). Three structural facts close every escape:

  - **You cannot bury the `Rot`.** `Rot_adversary` is a sealed event, and only content (`Ixn`) is
    buriable — a sealed branch is never buried
    ([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)). Burying
    "the adversary's" `Rot` would require a rule that could bury **any** `Rot` (including a
    legitimate operator's), resurrecting retired key material — the backdate surface VDTI closes by
    treating `Rot` as a sealed branch (never buriable).
  - **The seal-cap blocks a recovery at `v_{N-1}`.** `Rot_adversary` is seal-advancing, so it
    advances the seal to `v_N`; a recovery `Rot` targeting `v_{N-1}` is then below the seal →
    `Sealed`. The legitimate party cannot even submit it.
  - **A competing `Rot` at `v_N` is first-seen-declined.** A `Rot_legitimate` extending `v_{N-1}`
    lands as a sibling of the witnessed `Rot_adversary` at `v_N` → **first-seen-declined**
    (deferred-pending, forcing nothing). It cannot overturn the takeover: the adversary's rotation
    is a witnessed linear extension, and the owner's sibling is inert
    ([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)).

  A hostile `Rot` at a _forked_ position is likewise the reserve-theft takeover, not a recoverable
  fork. So the only defense against reserve theft is one layer up — IEL threshold redundancy evicts
  the compromised member via an `Evl` ([§Defense layers above KEL](#defense-layers-above-kel)) —
  never by salvaging this chain. Reserve theft is unrecoverable → reincept.

## Pre-seal verifiability

The locked-portion bound, the seal-cap, and the recovery rotation together produce a durable
consumer guarantee: events at-or-below `last_seal_advancing_event` remain structurally verifiable
indefinitely, regardless of subsequent divergence or a terminal `disputed` verdict above the seal.
One qualifier: the permanence claims run against the last **clean** seal — the highest seal-advancer
with no **witnessed** competing sibling at its own position (forward-anchored). Sealed events are
never rewritten, and a **below-seal** sealed straggler is **dropped** (inert — not witnessable past
the seal, the backdate defense), so it does **not** retreat the clean seal. Only a **witnessed**
sealed fork **at the last seal** flips the reading to `disputed`
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

## The live-tip dispute is a killswitch, forced by structure

A `disputed` verdict needs two **accepted** seals at one serial — a witness double-sign
([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)). Two facts
about that state set the real attack surface and explain why the brick is a structural necessity,
not a policy choice.

**Forging the second seal at the live tip needs the current signing key, not the reserve.** A seal
at position `s` reveals this epoch's key — the one drawn from the reserve committed at `s−1` — and
is **signed by that revealed key**. The instant it is revealed, the reserve is **spent**: its public
half is on the chain, and its private half is simply the **current signing key**
([`log.md`](log.md), the spent-preimage). A competing seal at `s` must reveal the same key (the
prior `rotationHash` forces it) and sign with that key's private half — the current signing key. The
**next** reserve is not involved; it only authorizes extending **forward** to `s+1`, never a rival
at the current position. So the two acts split cleanly:

- **Racing the rotation (takeover).** _Before_ the legitimate rotation to `s` lands, that key is
  still secret — the reserve. Winning the first-seen race with it makes your next-reserve canonical:
  a **takeover**. This is the tier-2 reserve-theft path.
- **A late rival at the tip (brick).** _After_ the legitimate seal has won first-seen at `s`, that
  key is now the live signing key, and any rival signed with it is a **late** sibling —
  first-seen-declined. It cannot win. Its only reachable effect, **with witness collusion**, is to
  become a second accepted seal → `disputed` → **brick**. Never a takeover: first-seen is already
  spent on the legitimate seal.

So a live-tip dispute is a **killswitch**: the current signing key **plus** a colluding witness
quorum forces a brick (denial, not takeover). It is bounded by rotation frequency — once you rotate
past `s`, that key's position is below the seal and a rival there is dropped — and its collusion leg
is defended by the witnessing posture (disjoint operators, hardware-held keys). The mitigation is
operational: rotate to bound each key's window; keep witnesses independent so the collusion stays
expensive.

**The brick is forced, not chosen.** A collision — two accepted seals at one serial — is
**irrecoverable by construction**: both reveal the same key but commit **different next reserves**,
so each party can extend its own branch and **neither can bury the other** (sibling seals; nothing
below to bury). No winner is latent in the data to surface. Only three responses exist, and two are
unsound:

- **Abandon both → reincept.** Deterministic, observer-independent, no takeover. This is the brick.
- **Pick a winner by a data rule** (lowest SAID, most receipts). The attacker controls the rival's
  bytes and its colluder count, so the rule is grindable → **takeover**, strictly worse than a
  brick.
- **Pick by first-seen.** "First" is a function of receipt arrival order, which differs per observer
  → the same chain reads differently to different consumers. That breaks the data-alone, same-answer
  guarantee end-verifiability rests on, and the ambiguity leaks through composition — anything that
  trusts the identity inherits it.

For a system whose product is a consistent, verifiable answer, only the brick is sound. A
"first-seen-final, never brick" mode buys availability with silent inconsistency — for a trust
anchor, worse than a loud, recoverable failure: with a brick everyone agrees the chain is broken and
the owner reincepts; with silent divergence, consumers quietly disagree and no one knows to act. The
brick is the price of the guarantee, and the guarantee is the point.

## Operator response to a disputed prefix

When a data-local walk finds a prefix **disputed** (two or more accepted sealed branches past the
fork — the concurrent sealed-race shapes are enumerated in
[`reconciliation.md` §Matrix 3](reconciliation.md#matrix-3-race-matrix)), no further extension on
that prefix is consumer-trustable at-and-beyond the divergent serial. Operator recourse is
**reincept under a new prefix**. The pre-seal verifiability guarantee bounds the damage:
at-or-below-seal anchors, credentials, and SEL bindings stay verifiable; only forward-extending
operations against above-seal state lose their trust grounding. See
[§Cascade-reincept honesty](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
for the cross-primitive cascade rules.

## Defense layers above KEL

KEL recovery closes the tier-1 (content) surface structurally; tier-2 (reserve theft) has no in-band
defense — once an adversary rotation lands, the chain reincepts. The post-rotation tier-2 surface is
closed by the layers composed above KEL:

- **IEL threshold composition.** Threshold-redundant governance — a roster with more members than
  its threshold requires, spread across distinct custodians — tolerates single-KEL tier-2
  compromise. The surviving members rotate the compromised KEL out via the IEL's `Evl` event (a
  `cut`) without losing the IEL prefix.
- **Reserve residence.** The rotation reserve lives in the device's own hardware alongside its
  signing key — no cold storage, no separate custody. Holding it off-device does not raise the bar
  in this model; it only slows the immediate rotation recovery relies on. The reserve defends the
  **signing** key (a signing-key-only thief can append content but never a key change); defense
  against a _full_ device compromise is the identity layer's job (the threshold-composition bullet
  above), not reserve custody.
- **Federation witnessing.** A selected witness signs the **first** sealed sibling per position and
  declines later ones (first-seen). A **reserve-tier fork** is a competing rotation seal at **one
  position** — the reserve reveal, `{Rot, Rot}`. Without witness collusion only **one** rotation
  reaches threshold; the losing branch, and every seal built on it, is **dead on ascent** — you
  cannot seal a buried chain, and honest witnesses decline the dead branch's descendants. Two
  rotation seals **both** witnessed at that position are **not** producible by honest witnesses; a
  second reaches threshold only if enough selected witnesses collude: a full **`threshold`** with no
  partition (the rival's receipts are then all colluders), sliding to **`2·threshold − signers`** as
  an attacker partitions the `signers − threshold` redundancy onto the rival (feeds it first-seen) —
  **`threshold − k`** for `k` partitioned witnesses. Either way it is a **provable double-sign at
  the fork**. So a `disputed` reading requires that same-position collusion; reserve-tier compromise
  **without** it resolves to a single canonical branch (the first-seen winner) with the other
  **inert** — a takeover if the adversary won the race, a failed fork if the owner did, and either
  way the owner detects loss-of-control and reincepts, never a network-visible dispute. (The
  `{Rot, Rot}` reserve double-reveal is a separate, author-side proof of the theft, visible to any
  node holding both siblings.) A competing **content** sibling, by contrast, is declined after the
  first seen at a position — under the witnessing floor a content fork on a witnessed chain is
  prevented, not merely detected; federation doctrine.

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
- [`merge.md`](merge.md) — merge-layer routing: how a burying seal-advancer resolves a content fork,
  the recovery attach shapes, branch-scoped verification, locked-portion bound enforcement.
- [`reconciliation.md`](reconciliation.md) — cross-node convergence proof; the race matrix
  (concurrent sealed-vs-sealed races); effective-SAID convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery; the universal recovery rule; recovery conditions.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound; the spine.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise)
  — limit of the doctrine; layered defense; adversary patience; cascade-reincept honesty.
- [`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md)
  — federation witnessing: the kind-scoped witnessing ladder, the witnessing floor, the beacon,
  divergent witness receipts.
