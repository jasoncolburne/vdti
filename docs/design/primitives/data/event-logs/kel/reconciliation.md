# KEL Reconciliation — Multi-Node Correctness Matrix

This doc is the **load-bearing correctness proof** for the KEL primitive. It exhaustively enumerates
every combination of (per-node chain state) × (submitted batch shape) × (cross-node gossip state),
and demonstrates that each case terminates correctly under the merge-layer routing rules and that
all nodes converge on the same effective SAID across the federation. Without this matrix, the merge
engine, the gossip layer, and the federation-witnessing layer are not proven sound — they are
designed against this enumeration. Cross-node convergence as a doctrinal property is stated upstream
at [§Federation convergence](../../../../protocol-doctrine.md#federation-convergence); this doc is
the per-primitive proof.

For lifecycle prose (states, the seal and spine, locked-portion bound, page model), see
[`log.md`](log.md). For per-kind reference (event kinds, fields, three-tier capability model),
[`events.md`](events.md). For the merge-layer routing rules being proved sound,
[`merge.md`](merge.md). For recovery doctrine (Rec parent shapes, dual-signature defense),
[`recovery.md`](recovery.md). For the verifier walk, [`verification.md`](verification.md).

## Proof structure

The proof composes four matrices:

1. **Local submissions matrix** — what every submission to every chain state produces on a single
   node. Demonstrates that the merge-layer routing rules are exhaustive and terminate correctly.
2. **Source → sink transfer matrix** — what gossip propagation between two nodes produces, for every
   combination of source and sink chain states. Demonstrates that gossip-driven sync converges
   per-node states under the merge rules.
3. **Race matrix** — what concurrent privileged-event races produce across federation peers.
   Demonstrates that the seal-cap and locked-portion bound are sound under adversarial concurrency,
   and that keep-all-data retention plus the witness beacon make the divergence readable
   **data-locally** on every node.
4. **Repair-completeness matrix** — the repair-side dual of matrices 1–3. Detection answers _"is
   this position forked or disputed?"_; this matrix answers _"is a landed repair **final** (chain →
   Active), or does it prove the fork **terminal** (`disputed:` → reincept)?"_ — for every
   combination of losing-branch tier, `fork` coverage, and delivery timing. Demonstrates that
   root-pointing condemnation terminates every case correctly and all honest nodes converge on one
   reading.

All four matrices depend on the same protocol-enforced invariants, stated next.

## Invariants

The cases below depend on these protocol-enforced invariants. They are stated structurally — the
protocol's safety claims hold _by construction_, not by observation.

1. **Seal-advance cap compliance.** Every KEL has a seal-advancing event (`Rec` / `Ror` / `Rot` /
   `Wit`) at least every `MINIMUM_PAGE_SIZE − 1 = 64` non-seal-advancing events. Surfaced by the
   verifier and enforced by the merge handler. See
   [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
2. **Bounded divergence.** A fork can only form after the last seal-advancing event (forking before
   triggers `SiblingLocked` per the locked-portion bound). Combined with invariant 1, the fork is
   bounded on both axes: **depth** — each fork lineage extends at most 64 events past the last seal
   (an adversary holding less than the rotation-key preimage can only submit `Ixn` events, so a
   deeper lineage needs a seal-advancing primitive — tier-2 or tier-3 capability per
   [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)); and
   **breadth** — nodes retain ≥ 2 competing events per position as fork evidence and drop the rest,
   with the one-content-sibling witnessing rule on top ([§Matrix 4](#matrix-4-repair-completeness)).
3. **Bounded operations.** A recovery batch (`[Rec]` plus the retained-branch context) fits in one
   `MINIMUM_PAGE_SIZE`-bounded page: the retained branch (≤ 64, the fold) plus the `Rec`. The losing
   branch named by the **root** committed as the `Rec`'s `fork` is condemned — every other closes
   below the seal and by descent — validated from retained storage (every competing branch walked
   for the content-only guard), not held in the page; the full-span membership walk adds at most one
   pre-fork page.
4. **A privileged divergence is terminal; a content divergence is repairable.** A privileged event
   (`Rot` / `Ror` / `Wit` / `Dec`) that would create or join a divergence does **not** extend the
   canonical chain — it is retained as non-canonical evidence (keep-all-data) rather than discarded.
   A fork with **at most one** privileged branch is **reconcilable** (`forked:`): a `Rec` keeps the
   single privileged-or-content branch and archives the **content-only** rest, naming one losing
   branch's **root** as its `fork` (the root condemns the branch's whole subtree; every other
   competing branch closes below the seal and by descent) — and a privileged branch is kept only by
   **its author** (a `Rec` that would condemn a privileged branch is rejected). A fork with **two or
   more** privileged branches past it is **terminal** (`disputed:`, reincept). Any verifier reads
   which by a data-local walk over the retained branches. See
   [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).
5. **Locked-portion bound is unconditional.** Every event class is subject to the seal-cap:
   `event.parent.serial >= seal_serial`. Stale-authority revival is structurally impossible; a valid
   fork below the seal is retained as evidence, never extended onto.

These invariants make synchronous resolution, single-page discriminator walks, and atomic batched
submissions feasible. The page-plus-resume-verify discriminator pattern relies on invariants 1–3.
The proof matrices below rely on invariants 4–5.

Recovery-preimage rotation cadence (how often `Ror` should land to refresh the recovery commitment)
is **operator guidance**, not a protocol-enforced invariant — see
[`events.md` §Seal-advance cap](events.md#seal-advance-cap). Reconciliation correctness does not
depend on a cap on `Rec` / `Ror` / `Dec` frequency.

## KEL chain states (proof states)

The per-node state enumeration covers every shape that can arise under the merge rules. Whether a
Divergent state is reconcilable (`forked:`) or terminal (`disputed:`) is a further data-local
reading, not a separate per-node state.

| State                  | Description                                                                                                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Empty**              | No events for this prefix on this node.                                                                                                                                                                                                                             |
| **Active**             | Linear chain; the current tip extends cleanly via `previous`.                                                                                                                                                                                                       |
| **Active, sealed**     | Sub-state of Active where a submitter's view lands at-or-before `last_seal_advancing_event`. Any extension whose parent sits in the locked portion returns `SiblingLocked` (a valid fork is retained as evidence).                                                  |
| **Divergent**          | A live fork: two distinct events at one serial; the chain is **frozen**. A privileged event extending `v_{d-1}` is retained as non-canonical evidence per invariant 4, not extended onto. Read `forked:` (≤ 1 privileged branch) or `disputed:` (≥ 2) data-locally. |
| **Divergent (sealed)** | Sub-state of Divergent where the seal has advanced past the fork — typically via a `Rec` / `Ror` / `Rot` / `Wit` that landed in a branch extension before resolution. The locked-portion bound rejects a competing `Rec` against `v_{d-1}`.                         |
| **Recovered**          | Clean chain after the `Rec` committed one losing branch's root as its `fork` in the merge transaction (the root condemning its subtree; every other competing branch closes below the seal and by descent). Equivalent to Active in subsequent rules.               |
| **Decommissioned**     | Exactly one `Dec`, ending a clean linear chain. Fully terminal: all submissions rejected by the seal-cap or the kind-schema rule.                                                                                                                                   |

## Matrix 1: Local submissions

What happens when a client submits events to the merge engine on a single node. Each cell names the
outcome (per [`merge.md` §Merge outcomes](merge.md#merge-outcomes)) and the structural reason.

| Chain state                                                          | `Icp` / `Fcp`                            | `Ixn`                      | `Rot`                                                                                     | `Ror` / `Wit`                                                               | `Rec`                                                                                                                                                                                                                                                                         | `Dec`                                                                              |
| -------------------------------------------------------------------- | ---------------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Empty**                                                            | **Append ✓ (inception creates the KEL)** | Reject (no KEL)            | Reject                                                                                    | Reject                                                                      | Reject                                                                                                                                                                                                                                                                        | Reject                                                                             |
| **Active**                                                           | Reject (KEL exists)                      | Append ✓                   | Append ✓ (linear extension; valid fork at `v_{d-1}` retained as evidence per invariant 4) | Append ✓ (linear extension; divergence-creating shape retained as evidence) | Append ✓ (gossip-sync of an already-recovered chain lands cleanly; a _bare_ `Rec` with no `fork` on a non-divergent tip is rejected — [§Edge cases](#edge-cases) case 1)                                                                                                      | Append ✓ → Decommissioned (linear); divergence-creating shape retained as evidence |
| **Active, sealed** (parent at-or-before `last_seal_advancing_event`) | Reject (KEL exists)                      | `SiblingLocked` (seal-cap) | `SiblingLocked` (seal-cap)                                                                | `SiblingLocked` (seal-cap)                                                  | `SiblingLocked` (locked-portion bound)                                                                                                                                                                                                                                        | `SiblingLocked` (seal-cap)                                                         |
| **Divergent** (frozen)                                               | Reject (KEL exists)                      | `RecoverRequired`          | `SiblingLocked` (invariant 4 — retained as evidence)                                      | `SiblingLocked` (invariant 4 — retained as evidence)                        | **Recovered** ✓ if every competing branch is content-only (one losing branch's root committed as `fork`; the rest close below the seal and by descent); **rejected → `disputed:`** if any competing branch holds a privileged event (the rejected `Rec` retained and counted) | `SiblingLocked` (invariant 4 — retained as evidence)                               |
| **Divergent (sealed)**                                               | Reject (KEL exists)                      | `SiblingLocked`            | `SiblingLocked` (seal-cap)                                                                | `SiblingLocked` (seal-cap)                                                  | `SiblingLocked` (locked-portion bound)                                                                                                                                                                                                                                        | `SiblingLocked` (seal-cap)                                                         |
| **Recovered**                                                        | Reject (KEL exists)                      | Same as Active             | Same as Active                                                                            | Same as Active                                                              | Same as Active                                                                                                                                                                                                                                                                | Same as Active                                                                     |
| **Decommissioned**                                                   | Reject (KEL exists)                      | `KelDecommissioned`        | `KelDecommissioned`                                                                       | `KelDecommissioned`                                                         | `KelDecommissioned`                                                                                                                                                                                                                                                           | `KelDecommissioned`                                                                |

### Notes on cell routing

- **Privileged event creating or joining a divergence (any chain state).** A privileged event
  (`Rot`, `Ror`, `Wit`, or `Dec`) with `previous = v_{d-1}.said` whose landing would create or join
  a divergence does not extend the canonical chain — it is retained as non-canonical evidence per
  invariant 4; the merge engine returns `SiblingLocked`. When the retained event is another
  federation peer's locally-landed privileged event (a cross-node privileged-vs-privileged race),
  each node now holds both branches and reads the divergence data-locally — a second privileged
  branch reads `disputed:`. See [§Matrix 3: Race matrix](#matrix-3-race-matrix).
- **Active, sealed and Divergent (sealed).** The seal-cap (`parent_serial >= seal_serial`) rejects
  every submission whose parent sits in the locked portion; a structurally-valid fork is retained as
  evidence. All extensions of `v_{seal-1}` / `v_{d-1}` return `SiblingLocked`. The pre-seal
  verifiability guarantee (per
  [`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability)) is what makes this
  rejection sound: the chain segment at-or-below the seal stays structurally trustworthy regardless
  of subsequent above-seal disruption.
- **Decommissioned.** Fully terminal. A local submission extends the chain's tip — the `Dec` — so
  its parent kind is `Dec` and the kind-schema rule rejects it with `KelDecommissioned` (see
  [`merge.md` §Routing order](merge.md#routing-order) rule 1). The distinct **sibling-to-`Dec`**
  case — a competing event sharing the `Dec`'s parent, which arises in cross-node races rather than
  local tip-extension — is rejected by the seal-cap with `SiblingLocked` (see
  [§Matrix 3](#matrix-3-race-matrix)).

### Batch submissions

The merge engine handles batches atomically:

- **`[events ..., Rec]`** — the retained-branch context plus the `Rec`. The retained branch (≤ 64)
  plus the `Rec` fits one page. Processed as a single overlap or divergent submission; the `Rec`
  commits one losing branch's root as its `fork` synchronously.
- **`[Rot, Ixn]` or `[Ror, Ixn]`** — auto-inserted by the builder when an `Ixn` would exceed the
  seal-advance cap interval. `Rot` is the cheaper choice; `Ror` is selected when the operator's
  recovery-preimage rotation cadence guidance calls for it.
- **`[Fcp, Rot]` plus the federation IEL `Fcp` and receipts** — the founder bootstrap atomic batch.
  The v=1 `Rot` anchors the federation IEL's `Fcp` marker; the KEL events land alongside that
  federation IEL `Fcp` and the cross-attestation receipts in a single transaction. See
  [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) (subsequent
  sub-issue) for the bootstrap protocol.

## Matrix 2: Source → sink transfer (gossip sync)

When node A propagates a KEL to node B, the transfer reads from A's local chain state and submits to
B's merge engine. Each cell describes the outcome at B for the named source / sink state pair.

"Active (retained)" means B has the eventual retained branch's non-divergent chain. "Active
(alternate)" means B has the eventual archived-tail branch's non-divergent chain (submitted to that
node before the divergence was detected elsewhere). The protocol cannot distinguish the two from
chain data alone — "retained" is the branch the `Rec` (whoever holds the recovery key) ultimately
keeps.

| Source                      | Sink: Empty                               | Sink: Active (retained)                 | Sink: Active (alternate)                | Sink: Divergent                             | Sink: Decommissioned                 |
| --------------------------- | ----------------------------------------- | --------------------------------------- | --------------------------------------- | ------------------------------------------- | ------------------------------------ |
| **Active**                  | Full chain appended ✓                     | Duplicates; no-op ✓                     | Overlap → Divergence                    | `RecoverRequired`                           | `SiblingLocked`                      |
| **Recovered**               | Full clean chain ✓                        | `Rec` append ✓                          | Overlap → `Rec` in batch → Recovery ✓   | `RecoverRequired` (sink awaiting recovery)  | `SiblingLocked`                      |
| **Divergent (unrecovered)** | Reordered: longer chain plus fork event ✓ | Fork event creates overlap → Divergence | Fork event creates overlap → Divergence | Effective SAIDs match (`forked:{prefix}`) ✓ | `SiblingLocked`                      |
| **Decommissioned**          | Full chain plus `Dec` ✓                   | `Dec` appends ✓                         | Overlap; `Dec` in chain ✓               | `RecoverRequired`                           | Effective SAIDs match (`Dec.said`) ✓ |

### Notes on cell routing

- **Sink terminal state** (Decommissioned). The source branched before the sink's `Dec`, so its
  competing event shares the `Dec`'s parent — it is a **sibling to the `Dec`**, not a chain _from_
  the `Dec`. The seal-cap rejects it with `SiblingLocked` and retains it as evidence. (The
  `KelDecommissioned` diagnostic — a chain-from-`Dec`, parent kind `Dec` — arises for local
  tip-extension as in [Matrix 1](#matrix-1-local-submissions), not for gossiped chains, which never
  carry an event built on the sink's `Dec`.) When the source carries a competing privileged event
  racing the sink's `Dec`, both nodes end up holding both branches and read `disputed:`
  data-locally.
- **Send-side partitioning** (Source: Divergent). The source partitions the chain into sub-batches
  the sink will accept under its routing rules. The structural requirement is on the sender:
  receive-side ordering can sort what arrived, but cannot fix composition problems where the sink's
  merge handler will reject a particular batch composition. See
  [`merge.md` §Gossip send-side partitioning](merge.md#gossip-send-side-partitioning) and
  [§Transfer ordering](#transfer-ordering) below.
- **Divergent → Divergent sink.** Effective SAIDs match by construction (both compute the synthetic
  `forked:{prefix}`). Full anti-entropy may reconcile any missing branch events even when SAIDs
  already match — keep-all-data means each node accumulates the competing branches it lacks, which
  is what lets a one-branch holder escalate a `forked:` reading to `disputed:` when a second
  privileged branch arrives.
- **Cross-node privileged-vs-privileged races.** When the source and sink hold different competing
  privileged events at the same serial, each node retains the other's event as non-canonical
  evidence and reads `disputed:` data-locally — see [§Matrix 3](#matrix-3-race-matrix).

### Transfer ordering

For divergent source chains, the sender reorders events to ensure the chain reconstructs the same
way at the sink. With synchronous resolution, a recovered source chain is always a clean linear
chain — a losing branch's root is committed as the `Rec`'s `fork` in the merge transaction. In
normal operation, only unrecovered divergent cases reach the partitioning path.

- **Divergent with `Rec`** — rejected with error. This state cannot exist through normal merge
  paths: synchronous resolution means a `Rec` immediately commits a losing branch's root as `fork`,
  leaving a clean canonical chain. A divergent chain with `Rec` in the live tables indicates
  possible DB tampering. The partitioner refuses to propagate it.
- **Unrecovered (`Ixn`-`Ixn` fork)** — longer chain first as non-divergent appends; only the fork
  event from the shorter chain is sent. Receiver routes the fork event through the overlap path →
  Divergent state.

### Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each prefix. The effective SAID is the
chain's canonical wire-format identifier; nodes exchange it during anti-entropy.

| State                                                | Effective SAID computation                                                           | Converges?                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active**                                           | Tip event SAID                                                                       | ✓ (identical chains after gossip)                                                                                                                                                                                                                                                                 |
| **Divergent (reconcilable)**                         | `hash_effective_said("forked:{prefix}")` — deterministic synthetic                   | ✓ (same value regardless of which fork events each node holds; avoids wasted anti-entropy sync)                                                                                                                                                                                                   |
| **Recovered**                                        | Tip event SAID                                                                       | ✓ (identical clean chains after gossip)                                                                                                                                                                                                                                                           |
| **Decommissioned**                                   | `Dec` event SAID                                                                     | ✓ (identical chains across all nodes where `Dec` landed without a competing privileged submission). When a competing privileged event racing `Dec`'s parent reaches a different node, both nodes retain both branches and read `disputed:` data-locally (see [§Matrix 3](#matrix-3-race-matrix)). |
| **Disputed** (≥ 2 privileged branches past the fork) | `hash_effective_said("disputed:{prefix}")` — deterministic synthetic, **data-local** | ✓ (deterministic; any verifier computes it from the retained branches — over the canonical chain plus the retained set; returned by chain-query responses regardless of per-node tip state).                                                                                                      |

The synthetics depend only on `(state, prefix)` — no chain history, no fork point, no serial — so
any node computes either synthetic without holding chain state, and two differently-forked nodes
compute the same value and recognize each other's state. Whether a fork is `forked:` or `disputed:`
is the **branch-walk's** result over the retained branches, not encoded in the synthetic. See
[§Effective-SAID synthetic comparison](../../../../protocol-doctrine.md#effective-said-synthetic-comparison)
for the cross-primitive framing.

**Finality of a Recovered reading is two-valued, per question** (the repair-completeness split —
[§Matrix 4](#matrix-4-repair-completeness)). The repair is **content-final** the instant it seals:
root-condemnation plus deadness-descends close every losing content branch, present or later-grown.
On the privileged side, two distinct properties: **no-resurrection** (unconditional — nothing
archived is ever un-archived, from the instant the repair lands) and **resolution-stability** (the
reading stays non-`disputed:`, once the minting capability is neutralized (the `Rec`'s rotation —
vacuous for a benign fork with no adversarial minter) **and** the beacon shows no omitted privileged
branch — stable barring the eclipse residual and a historical rotation-reserve compromise, both
fail-secure, each flipping the reading to `disputed:`). A **`disputed:`** reading is terminal
everywhere.

## Matrix 3: Race matrix

Concurrent privileged-vs-privileged races between federation peers — both submitting privileged
events extending the same parent `v_{d-1}` to different nodes — uniformly resolve via the same
structural shape: each event lands as a clean linear-chain extension on its submitting node and
advances the local seal; gossip then delivers each event to the other node, where the seal-cap
rejects it as a canonical extension (`parent_serial < seal_serial`) **but retains it as
non-canonical evidence** (keep-all-data). Each node ends up holding both branches and reads the
divergence by a **data-local walk** — two privileged branches past the fork read `disputed:`.

The race participants — any pairing across `{Rec, Ror, Rot, Wit, Dec}` — produce identical
structural outcomes per-node:

- Each node keeps its locally-landed first-receive as its canonical tip.
- The gossip-arriving competing event is not admitted as a canonical extension (the seal-cap returns
  `SiblingLocked`) but is retained as non-canonical evidence. On the Dec'd side the treatment is
  identical — a Decommissioned chain is sealed at its `Dec`, so the seal-cap rejects per
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).
- Each node reads the prefix as `disputed:` by a data-local walk over the two retained privileged
  branches; the witness beacon enumerates the competing branch SAIDs so a one-branch holder fetches
  and walks the rest.

### Worked race: `Dec` versus `Ror` / `Dec` at `v_d`

Two parties submit concurrent privileged events extending `v_{d-1}` at the same serial `d` to
different nodes: party 1 submits `Dec` (clean retirement); party 2 submits another privileged event
(e.g., `Ror` or `Dec`) extending the same parent.

```
Pre-state (linear at v_{d-1}):

  Both nodes:  ... → v_{d-1}    (tip)

Concurrent submissions:

  Party 1 → Node A:    dec.previous     = v_{d-1}.said, dec.serial     = d
  Party 2 → Node B:    ror_alt.previous = v_{d-1}.said, ror_alt.serial = d

Each event lands as a linear-chain extension on its submitting node.

Gossip propagates:

  Node A (Decommissioned at v_d via dec) receives ror_alt:
    ror_alt.parent_serial = d-1 < seal_serial = d
    → rejected as a canonical extension (SiblingLocked); retained as evidence.
    Node A canonical tip unchanged: dec. Node A now holds both branches.

  Node B (Active at v_d via ror_alt) receives dec:
    dec.parent_serial = d-1 < seal_serial = d
    → rejected as a canonical extension (SiblingLocked); retained as evidence.
    Node B canonical tip unchanged: ror_alt. Node B now holds both branches.

  Data-local walk on each node:
    two privileged branches past v_{d-1} → disputed:
    effective_said(A) = effective_said(B) = hash_effective_said("disputed:{prefix}")
    → both nodes converge on the disputed synthetic.
```

Convergence in this scenario is **data-local**: once keep-all-data retention plus the witness beacon
deliver both branches to each node, every node reads `disputed:` from the same retained branches. A
selected witness signs up to **two** distinct structurally-valid **privileged** siblings per chain
position (two both-witnessed siblings are the `disputed:` proof, then further ones are declined);
adjacent receipts at the same chain position carrying different `witnessed_said` values are the
evidence that a divergence exists at that position — the beacon **propagates** the branches, the
data-local walk **decides** the verdict. The prefix is disputed at-and-beyond the divergent serial;
events strictly below the last clean seal stay canonical. See
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair) and
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

The seal-cap stays unconditional. Relaxing it to admit a competing event as a canonical extension at
a sealed serial would re-open the stale-authority killswitch surface that the locked-portion bound
was designed to close — so the competing branch is retained as evidence, never extended onto.

### Race classes (tier-2 versus tier-3)

The race surface partitions by adversary tier (per
[`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)):

- **Tier-2 path.** An adversary holding the rotation-key preimage can force a `disputed:` divergence
  by racing `Rot_adversary` against an honest concurrent `Rot_operator` or `Ror_operator` on
  different federation nodes. The forging bar is tier-2 (one preimage), strictly easier than the
  tier-3 bar required to forge `Ror` / `Rec` / `Wit` / `Dec`. A `{Rot, Rot}` divergence is moreover
  a **proof of rotation-reserve compromise** — two valid rotations reveal the one rotation preimage
  in force at `v_{d-1}`.
- **Tier-3 path.** An adversary holding both preimages can force a `disputed:` divergence by racing
  any recovery-revealing event (`Ror` / `Rec` / `Wit` / `Dec`) against operator submissions. Once an
  adversary's tier-3 event has landed on any federation node, no in-band protocol recourse exists.

Both paths produce identical per-node structural outcomes (matrix above) and resolve to the same
data-local `disputed:` reading. See
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).

## Matrix 4: Repair completeness

The repair-side dual of matrices 1–3. Matrices 1–3 prove **detection** — every node reads the same
`forked:` / `disputed:` verdict from the data it holds. This matrix proves **repair completeness**:
a landed repair is **final** (chain → Active) or proves the fork **terminal** (`disputed:` →
reincept), for every combination of {tier of the losing branch} × {named by the `fork` root versus
unnamed} × {delivered before or after the seal} — and every honest node converges on the same
reading. The merge-layer rules being proved sound are
[`merge.md` §Discriminator algorithm](merge.md#discriminator-algorithm) and
[`merge.md` §A repair is validated on arrival](merge.md#a-repair-is-validated-on-arrival-not-auto-applied).

### The root-pointing model

On a **witnessed** chain, content forks are **prevented** below fork-cost — the witnessing majority
floor plus one-content-sibling-per-position witnessing makes two content siblings un-co-witnessable
([§Federation convergence](../../../../protocol-doctrine.md#federation-convergence)) — so the
population this matrix repairs is the **residual**: direct-mode / no-witness chains, witness
compromise at fork-cost, roster-delta straddles (the partition/eclipse family's entrance),
split-stalls (the repair is the exit), and mixed `{privileged, content}` races. The machinery below
is mode-independent — the same rules run everywhere; on a witnessed chain their population is that
residual rather than routine gossip-lag.

A divergence at a fork point `v_{d-1}`: distinct events — each a **root** — extend it at `v_d`; one
branch is retained, the rest lose; the chain freezes. A repair (`Rec`) retains one branch and names,
as its inline **`fork`** role, the **root of one losing branch** — its first divergent event, a
distinct child of `v_{d-1}` **off** the retained chain. **The named root condemns its entire
subtree**: every descendant is non-canonical forever. So a losing branch that a lagging node **grows
after the repair** is dead **by descent** — no follow-up repair, growth-proof (a `Rec.fork` naming a
competing `Ixn` condemns it and any later `Ixn` grown on it). A losing branch the repair does **not
name** (an additional held branch, or one truly missed — identical closure, which is why a single
named root suffices) has its **first event** locked below the advanced seal (the seal-cap) and
**everything built on it dead by descent** — **deadness descends: an event whose parent is dead is
dead** (the per-event seal-cap locks only the _first_ event; the descent rule kills the growth).
Either way it rides the **forked chain** — a **bounded** region: each dead **lineage** extends at
most **64 events past the last seal** (the seal-advance cap; a deeper event needs a seal-advancer,
privileged → `disputed:`), and its **breadth** is bounded by **retention** (nodes keep **≥ 2
competing events per position** as evidence and drop the rest — the content analog of the ≥
2-per-spine-position privileged bound; the queryable set is bounded), with the **one-content-sibling
witnessing rule** on top (a witness signs the first structurally-valid content sibling at a position
and declines later ones; privileged siblings are witnessed up to **two** per position — two
both-witnessed siblings prove `disputed:`, then further ones are declined; the repair is privileged,
so the single resolving repair needs no separate clause). Dead events are **witnessed and
propagated** yet **never canonical**; an adversary can _author_ extra siblings, but they are
droppable — never making the retained fork unbounded (a query-DoS surface only).

### The completeness matrix

Rows = {tier of the losing branch} × {named by the `fork` root versus unnamed} × {delivery timing}.
Cell = reading + closing rule. (Unnamed = an additional held branch or a truly-missed one —
identical closure either way, which is why a single named root suffices.) (The cross-layer rows — a
SEL event on a dead owner-IEL anchor; a SEL fork riding an IEL fork — land with the `sel/` + `iel/`
anchor-validation doctrine, forward-referenced below.)

| losing branch                                                                      | reading                                                                                                                                         | closes with                                                                                                                                                                                |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **content**, root named in `fork`                                                  | condemned subtree (all descendants dead, growth-proof) → **Active** on the retained chain                                                       | root-condemnation; the seal-cap bounds each dead lineage's _depth_ (≤ 64 past the seal)                                                                                                    |
| **content**, root named, branch **grows** after the repair (lagging node)          | grown events dead **by descent** — no follow-up repair → **Active**                                                                             | condemnation is over the subtree, not a tip; growth past depth-64 needs a seal-advancer → privileged → `disputed:`                                                                         |
| **content**, **unnamed** (additional or missed), delivered or grown after the seal | first event locked below the seal; growth dead by descent → **Active**                                                                          | seal-cap (first event) + deadness-descends (growth); no orphan-drop (kept, re-issued forward)                                                                                              |
| **content**, unnamed, held when the repair arrives                                 | repair **accepted**, the branch drops below the advanced seal → inert → **Active**                                                              | an unnamed-content repair is accepted; the branch inerts rather than freezing the chain                                                                                                    |
| **privileged** (non-content) — a repair attempted against it, or a 2nd one present | ≥ 2 privileged → **`disputed:` → reincept**                                                                                                     | validated-not-trusted (a condemned subtree with a privileged event rejects the `Rec`, which is retained and counted); FORCE-by-provenance; a below-seal privileged branch is **not** inert |
| **privileged** (non-content) — a **lone unretained** branch, **no repair attempt** | one privileged branch → **`forked:`-frozen** (reconcilable only by its author; reincept is the operational exit, the _reading_ stays `forked:`) | invariant 4 (≥ 2 privileged is the `disputed:` threshold; one is `forked:`) — _not_ `disputed:`                                                                                            |
| **≥ 2 privileged branches**                                                        | **`disputed:` → reincept**                                                                                                                      | invariant 4; [§Matrix 3](#matrix-3-race-matrix)                                                                                                                                            |
| **`{Dec, content}` terminal tip** (no repair)                                      | `Dec` wins on tier-rank, content archived non-canonical → **Decommissioned**; a late privileged sibling → **`disputed:`**                       | tier-rank, no repair authored; the after-seal privileged asymmetry                                                                                                                         |

### Safety — the guards

- **No self-condemnation, no censorship.** The `fork` root must be a competing child of `v_{d-1}`
  **off** the retained chain. The verifier knows the retained branch (walk `Rec.previous` back), so
  a root that lies on it — or `v_{d-1}` itself (which is on it) — is **rejected**. So a repair can
  never condemn its own retained branch, and there is no root whose subtree includes the canonical
  chain. **The membership walk spans the _full_ retained chain** — down to the fork point (walking
  to the pre-fork seal always suffices, one extra page at most); the root's parent must be `v_{d-1}`
  itself, and the root must not lie on that full-span walkback. A walk truncated at the divergence
  serial reads `v_{d-1}` and every trunk ancestor as _off_ the retained chain, so a root naming a
  trunk ancestor would condemn a subtree containing the whole canonical chain (and the `Rec` itself)
  — the exact censorship this guard forbids, reachable by any tier-3 holder including a buggy
  client. Condemnation is safe because each event has one `previous`, so a genuinely off-chain
  root's subtree is disjoint from the retained chain — a property the verifier can test only over
  the full-span walk.
- **No buried rotation.** A condemned subtree is walked; a **privileged** event in it means ≥ 2
  privileged branches past the fork → **`disputed:`**, not archived (validated, not trusted). So
  root-condemnation can never dead-mark a rotation to un-rotate it. The walk-independent closer:
  every privileged KEL event is a **seal-advancer** → a competing seal → a **spine fork** →
  `disputed:`, independent of any walk bound.
- **No stale-authority revival.** Root-condemnation reaches no _live_ state — it **marks a subtree
  dead**, never extends or revives an event. There is **no below-seal archival operation**, so the
  seal-cap stays unconditional.
- **Bounded fork (depth _and_ breadth).** **Depth** ≤ 64 events past the last seal per lineage (the
  seal-advance cap — a deeper event must author a seal-advancer, privileged → `disputed:`).
  **Breadth** is bounded by **retention**: nodes keep ≥ 2 competing events per position as evidence
  and drop the rest ("two prove the fork, then stop"), so the _queryable_ set is bounded and there
  is no query DoS. The **one-content-sibling witnessing rule** is the _kind-aware layer_ on top: a
  witness signs the **first** structurally-valid _content_ sibling at a position and **declines
  every later one** — while **privileged siblings are witnessed up to two per position** (two
  both-witnessed siblings are the `disputed:` proof — dispute evidence, competing seals form a spine
  fork; further spray is declined and droppable). The **single `Rec` repair** that lands on a
  content-only divergence is simply the first privileged sibling at that position (a _second_,
  competing repair is `{Rec, Rec}` → `disputed:`; at most one repair can resolve a content-only
  divergence). With the majority floor this bounds co-witnessed content breadth to ≤ 1 absent
  fork-cost byzantine witnesses; arrival order decides only _which_ content sibling is the witnessed
  one — the bound rests on **retention + kind-awareness**, arrival-independent. A signing-key
  (tier-1) re-forker can _author_ more content siblings, but they sit beyond the retained ≥ 2 →
  droppable + declined; unnamed siblings beyond the retained set are seal-cap-inert (the repair does
  not need them). Every dead event is non-canonical and never flips a reading, and the depth-cap
  forces the seal-advancer that turns the fork terminal. A **privileged** event on a dead branch (it
  needs the reserve — tier 2+) → `disputed:` regardless (the no-buried-rotation guard) — the
  terminal-compromise case, not a new attack.

### Convergence

Under eventual beacon delivery and `< threshold` byzantine, every honest node's known set converges
to the true competing set. Then:

- **All-content** → every node reads the retained chain as canonical; the named subtree dead by
  condemnation, every other branch inert by the seal-cap (its growth dead by descent — named and
  unnamed converge identically, which is the single-`fork` collapse's verification); the effective
  SAID is the real retained tip on every node. **Converges to Active.** No follow-up repair, no
  reincept.
- **One privileged branch, kept by its author** → Active once neutralized and beacon-confirmed
  (barring eclipse). A non-author's repair that would condemn the privileged branch is **rejected
  (the no-buried-rotation guard), retained as a competing privileged branch, and counted** —
  retain-and-count is the only convergent semantics (dropping the rejected repair would split the
  reading permanently). Only this guard's rejections count — the repair passed hard auth and
  revealed the reserve, so it is a real privileged event; a hard-auth failure, a missing `fork`,
  malformed roster, or self-condemning root is dropped, never counted. So any reserve-revealing
  repair against a fork that turns out to hold a privileged branch **permanently terminalizes the
  prefix** → `disputed:` — the fail-secure outcome of revealing tier-3 material into a contested
  window (Matrix 1's Divergent × `Rec` cell reads rejected → `disputed:`).
- **≥ 2 privileged** (including a beacon-late privileged branch) → **`disputed:`** everywhere
  (FORCE-by-provenance once a node holds ≥ 2; via receipt-then-fetch otherwise); the effective SAID
  is `hash_effective_said("disputed:{prefix}")`.

### Termination

The forked chain is **depth-capped at 64 past the last seal, per lineage** — that is the bound, not
a count of repairs. One repair closes the whole current fork (the named root's subtree condemned;
every other branch below the seal, growth dead by descent — growth-proof within the depth-cap); the
`Rec`'s key rotation then closes the culprit's ability to mint a **new** fork (on an IEL, the
`Rpr`'s roster `cut` plays this role — an IEL repair rotates no identity key). So termination is
qualitative but strict: each fork a sustained adversarial re-forker mints costs it one bounded fork
window, and once the neutralizing repair — the rotation, or the cut — propagates, it can mint no
more; a benign gossip-lag terminates as soon as its node catches up. Content-rail serialization is
an **operator precondition** of the benign bound — absent it, honest content can self-cascade (a
liveness cost, not a safety one), exactly as governance serialization backs the `{Evl, Evl}` /
`{Rpr, Rpr}` terminal cases at the IEL. On a **witnessed** chain the majority floor narrows even the
self-cascade to stall-and-re-issue — a competing content sibling never goes live — so the discipline
is safety-critical on direct-mode / solo chains (where cap-fill can force the terminal `{Evl, Evl}`)
and a liveness concern on witnessed ones.

### Residuals (stated, fail-secure)

- **Eclipse / unwitnessed-branch residual:** detection is eventual; a reader eclipsed from a branch
  sees the true reading later. Privileged-completeness fails secure in that window. Pre-existing —
  the detection residual, not a repair-specific one.
- **Historical rotation-reserve compromise:** an old rotation reserve can mint a privileged event on
  a dead or below-seal lineage years after beacon confirmation → flips the reading to `disputed:`
  (fail-secure — nothing is un-archived; the prefix terminalizes). Not an eclipse — the branch did
  not exist at confirmation, so the beacon was truthful.

The cross-layer completeness rows — **anchor-monotonicity** (an owner IEL totally-orders each SEL it
anchors, with **skip-unattributable** for an anchor whose body a node does not hold: skipped, not
blocking, so a withheld or lost body never wedges the SEL), **cross-layer deadness-descends** (a SEL
event on a dead IEL anchor is dead — the IEL→SEL anchor edge only), the theorem that a valid SEL
fork implies an IEL fork beneath it, and the **withheld-body transient-split residual** (a node
lacking an anchored body reads a later sibling valid while a node holding it reads it inert —
auto-resolved by seal order, fail-secure) — belong to the `sel/` + `iel/` anchor-validation doctrine
(subsequent sub-issues); the KEL-level matrix above is self-contained without them.

## Archival bounds

The `Rec` commits one losing branch's root as its `fork` synchronously within the merge transaction
that accepts the `Rec` batch (every other competing branch closes below the seal and by descent). No
background task, no async processing.

| Metric                                 | Bound                        | Source                                                                                                                                                                                                        |
| -------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fork` — a single losing-branch root   | condemns the whole subtree   | Root-pointing ([§Matrix 4](#matrix-4-repair-completeness)): the committed SAID is the branch's first divergent event; unnamed branches close below the seal and by descent.                                   |
| Dead-lineage depth                     | ≤ 64 past the last seal      | Seal-advance cap (invariant 1); a deeper event needs a seal-advancer — privileged, `disputed:` when competing.                                                                                                |
| Dead-branch breadth per position       | ≥ 2 retained, rest droppable | Retention (the bounded-fork guard), with the kind-aware divergent-position gate on top.                                                                                                                       |
| Resolution scope                       | Single transaction           | Synchronous in merge; bounded by `MINIMUM_PAGE_SIZE` (invariant 3).                                                                                                                                           |
| Retained-branch events never condemned | ✓                            | Full-span membership (the no-self-condemnation guard): a `fork` root on the `Rec.previous` walkback (or `v_{d-1}`) is rejected (see [`merge.md` §Discriminator algorithm](merge.md#discriminator-algorithm)). |

The retained (canonical) run's bodies are kept and retrievable by prefix (the flat query returns
them); the `Rec`'s `fork` root is committed, and the condemned branch is its root's **subtree**,
reconstructable from retained storage (every dead event's ancestry passes through the named root or
a below-seal first event). Only the uncommitted below-seal flood is droppable.

## Edge cases

### 1. A `Rec` requires a divergence to resolve; recovery commitments stay fresh

A `Rec` on a **non-divergent** tip is **rejected** — it carries no `fork`, and a repair must commit
the divergence it resolves
([`merge.md` §Kind-specific authorization](merge.md#4-kind-specific-authorization),
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair)). So a recovery-key
holder cannot "spend" the recovery preimage on a clean chain by appending a bare `Rec`. And a `Rec`
that _does_ resolve a divergence commits a **fresh** `recoveryHash` (it reveals the current preimage
and commits a new one —
[`recovery.md` §Rec versus Ror](recovery.md#rec-versus-ror--repair-versus-proactive-rotation)), so
the chain stays recoverable afterward.

The genuinely-unrecoverable states are a **tier-3 compromise** (the adversary holds both preimages)
and a **`disputed:`** prefix (≥ 2 privileged branches past a fork) — both → reincept, neither
produced by a clean `Rec`. The recovery preimage degrades only through a recovery-revealing event
that **also re-commits** a successor, so "the recovery key is spent" never leaves the chain without
a forward recovery commitment.

### 2. Multiple competing content events injected across nodes

Different `Ixn` events at the same serial are submitted to different nodes (federation race or
threshold compromise — chain-indistinguishable). When gossip syncs, a fork forms. Only one extra
event is written per overlap (the fork event). Recovery resolves it. All nodes converge after
recovery propagates via gossip.

```
Pre-state (linear at v_{d-1}, replicated to nodes A and B):

  Node A:  v_0 → ... → v_{d-1}    (tip)
  Node B:  v_0 → ... → v_{d-1}    (tip)

Different events submitted at v_d on each node:

  Node A receives ixn_a:  v_0 → ... → v_{d-1} → ixn_a @ v_d
  Node B receives ixn_b:  v_0 → ... → v_{d-1} → ixn_b @ v_d

Gossip propagates ixn_a → B, ixn_b → A. Each node's merge engine observes overlap at v_d and writes the second event as the fork event (one extra canonical branch per overlap; a byte-identical re-submission dedupes, a further distinct event is retained as non-canonical evidence):

  Both nodes:  v_0 → ... → v_{d-1} ─┬─ ixn_a @ v_d   (Divergent, forked: — frozen)
                                    └─ ixn_b @ v_d

A recovery-key holder submits Rec to any single node → the Rec keeps its branch and commits the other's root as fork (condemning it) → recovery propagates via gossip → all nodes converge on the post-Rec linear state.
```

### 3. Local events archived by a competing `Rec`

If one recovery-key holder submits `Rec` keeping another party's branch and resolving the rest
synchronously, that other party's local store detects missing canonical events when it next attempts
to flush. Detection works by loading the last page of locally-held events, then walking backward
checking each SAID against the server until finding the boundary — everything after that boundary
lies in the subtree condemned by the `Rec`'s `fork` (or below the seal it advanced). The party then
resubmits those missing events (plus any continuation work) as an atomic batch.

```
Pre-state (divergent at v_d; local store holds branch A):

  Server:  v_0 → ... → v_{d-1} ─┬─ branch_A @ v_d → branch_A' @ v_{d+1}
                                └─ branch_B @ v_d

  Local:   v_0 → ... → v_{d-1} → branch_A → branch_A'   (local view)

A second recovery-key holder submits Rec keeping branch_B (branch-tip-extending shape):

  rec_B keeps branch_B; rec_B.fork names branch_A (the losing branch's root — its first divergent
  event), condemning branch_A' with it by descent; rec_B lands at v_{d+1}.

  Server (post-recovery):  v_0 → ... → v_{d-1} → branch_B → rec_B

Local party detects via an existence-check on the server that branch_A / branch_A' are no longer the canonical chain — rec_B kept branch_B and condemned branch_A's subtree. The footgun to avoid: do NOT append a privileged event to the stale branch. Submitting a Dec that extends the party's local tip (branch_A' at v_{d+2}, or branch_A) does not cleanly decommission — the Dec is a dual-signed privileged event landing on a condemned branch below rec_B's seal at v_{d+1}. The seal-cap (invariant 5) refuses it as a canonical extension, but keep-all-data retains it, and a privileged event on a condemned branch is a second privileged branch past the fork → the reading flips to disputed: and the prefix terminalizes (the reserve was revealed into a contested window — fail-secure; a condemned subtree must stay content-only). Correct recourse: re-fetch the server state, confirm the canonical tip (rec_B), then either submit Dec extending that tip cleanly or accept the server-side state without decommissioning — never append a privileged event to a branch not confirmed canonical.
```

### 4. Post-recovery events synced to a node holding the archived branch

After recovery on node A, new events (e.g., `Ixn`) are appended. When synced to node B (which still
has the now-archived branch as its canonical chain), the overlap handler runs the discriminator (the
`Rec`'s `fork` names the losing branch's root) and resolves it synchronously in the merge
transaction.

```
Pre-sync state (post-recovery on A; archived branch still canonical on B):

  Node A:  v_0 → ... → v_{d-1} → branch_A @ v_d → rec → ixn_new
           (clean linear chain after rec committed branch_B's root as fork)

  Node B:  v_0 → ... → v_{d-1} → branch_B @ v_d
           (still has the alternate branch as canonical; rec hasn't propagated)

Gossip propagates Node A's chain (including rec) to Node B. Node B's merge engine observes overlap at v_d (its branch_B vs incoming branch_A), sees rec in the batch, runs the discriminator (the full-span walkback identifies branch_A as the retained branch; branch_B's root is named as rec.fork), and condemns branch_B synchronously.

  Node B (post-sync):  v_0 → ... → v_{d-1} → branch_A → rec → ixn_new
                       (matches Node A; branch_B in retained storage by commitment)

All nodes converge on the same effective SAID (tip event SAID).
```

### 5. Concurrent privileged race at `v_d` — data-local disputed reading

See [§Matrix 3](#matrix-3-race-matrix). Per-node, each chain keeps its own first-receive as the
canonical tip and retains the competing branch as evidence; every node reads `disputed:` by a
data-local walk over the two retained privileged branches. The witness beacon delivers a missing
branch to a one-branch holder. The seal-cap stays unconditional.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: kinds, fields, three-tier capability model,
  seal-advance cap.
- [`merge.md`](merge.md) — merge engine routing being proved sound.
- [`recovery.md`](recovery.md) — recovery doctrine: Rec parent shapes, three-tier compromise model,
  pre-seal verifiability.
- [`verification.md`](verification.md) — verifier walk.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#federation-convergence) —
  federation convergence (cross-primitive doctrine).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-repair) —
  divergence and repair; privileged-divergence terminality; keep-all-data retention.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#effective-said-synthetic-comparison)
  — effective-SAID synthetic comparison.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (subsequent sub-issue): the kind-scoped witnessing ladder, the majority floor, the
  beacon, divergent witness receipts.
