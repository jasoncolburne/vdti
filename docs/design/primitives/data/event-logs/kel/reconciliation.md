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
   Active), or does it prove the fork **terminal** (`disputed` → reincept)?"_ — for every
   combination of losing-branch tier, `fork` coverage, and delivery timing. Demonstrates that
   root-pointing condemnation terminates every case correctly and all honest nodes converge on one
   reading.

All four matrices depend on the same protocol-enforced invariants, stated next.

## Invariants

The cases below depend on these protocol-enforced invariants. They are stated structurally — the
protocol's safety claims hold _by construction_, not by observation.

1. **Seal-advance cap compliance.** Every KEL has a seal-advancing event (`Rec` / `Ror` / `Rot` /
   `Wit`) at least every `(MINIMUM_PAGE_SIZE − 1)/2 = 64` non-seal-advancing events (per lineage).
   Surfaced by the verifier and enforced by the merge handler. See
   [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
2. **Bounded divergence.** A fork can only form at-or-after the last seal-advancing event — a
   competing event **below** the seal is dead on arrival (never a live fork), and one **at** the
   seal's own serial is rejected as a canonical extension (`SiblingLocked`) yet forms a live fork.
   Combined with invariant 1, the fork is bounded on both axes: **depth** — each fork lineage
   extends at most 64 events past the last seal (an adversary holding less than the rotation-key
   preimage can only submit `Ixn` events, so a deeper lineage needs a seal-advancing primitive —
   tier-2 or tier-3 capability per
   [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)); and
   **breadth** — nodes retain ≥ 2 competing events per position as fork evidence and drop the rest,
   with the one-content-sibling witnessing rule on top ([§Matrix 4](#matrix-4-repair-completeness)).
3. **Bounded operations.** `MINIMUM_PAGE_SIZE = 129 = 2·64 + 1`, sized so the **canonical two-branch
   fork anchored at the last seal** — both lineages (≤ 64 each) plus the resolving `Rec` — fits one
   page. This is what a **source → sink transfer** of that shape needs: the sink holds neither
   branch (it is receiving the fork fresh), so the transfer carries both competing branches plus the
   `Rec` in one atomic page, and the `Rec`'s content-only guard has both branches to walk. **Two
   permitted shapes exceed one page and ride later pages** — correctness holds because the merge
   guard is walk-what-you-hold-or-the-beacon-enumerates (validated-not-trusted for late privileged
   arrivals — [`merge.md` §Discriminator algorithm](merge.md#discriminator-algorithm)), and the hard
   co-delivery floor is only the named `fork` **root's body** (`root.previous = v_{d-1}`; without it
   the `Rec` parks on a deferred dep): **(a)** an own-`Rot` in the retained tail spans two seal
   windows (`seal1→Rot`, `Rot→Rec`), so the pre-`Rot` run rides earlier plain-linear pages; **(b)**
   a **≥ 3-branch** residual fork (the retention floor is ≥ 2, not = 2) exceeds `2·64 + 1` — extra
   branches ride later pages, and a late privileged one flips the reading (the eclipse-class
   residual). (A **local** discriminator that already holds the competing branches in storage needs
   only the retained branch (≤ 64) plus the `Rec`, validating the competing branches from storage;
   the full-span membership walk adds at most one pre-fork page.)
4. **A privileged divergence is terminal; a content divergence is repairable.** A privileged event
   (`Rot` / `Ror` / `Wit` / `Dec`) that would create or join a divergence does **not** extend the
   canonical chain — it is retained as non-canonical evidence (keep-all-data) rather than discarded.
   A fork with **at most one** privileged branch is **reconcilable** (`forked`): a `Rec` keeps the
   single privileged-or-content branch and archives the **content-only** rest, naming one losing
   branch's **root** as its `fork` (the root condemns the branch's whole subtree; every other
   competing branch closes below the seal and by descent) — and a privileged branch is kept only by
   **its author** (a `Rec` that would condemn a privileged branch is rejected). A fork with **two or
   more** privileged branches past it is **terminal** (`disputed`, reincept). Any verifier reads
   which by a data-local walk over the retained branches. See
   [§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).
5. **Locked-portion bound is unconditional.** Every event class is subject to the seal-cap:
   `event.parent.serial >= seal_serial`. Stale-authority revival is structurally impossible; a valid
   fork below the seal is never extended onto. (Whether such a fork is retained as evidence is a
   separate, witnessing-gated matter — see [`merge.md` §Merge outcomes](merge.md#merge-outcomes);
   the seal-cap's _rejection_ is unconditional regardless.)

These invariants make synchronous resolution, single-page discriminator walks, and atomic batched
submissions feasible. The page-plus-resume-verify discriminator pattern relies on invariants 1–3.
The proof matrices below rely on invariants 4–5.

Recovery-preimage rotation cadence (how often `Ror` should land to refresh the recovery commitment)
is **operator guidance**, not a protocol-enforced invariant — see
[`events.md` §Seal-advance cap](events.md#seal-advance-cap). Reconciliation correctness does not
depend on a cap on `Rec` / `Ror` / `Dec` frequency.

## KEL chain states (proof states)

The per-node state enumeration covers every shape that can arise under the merge rules. Whether a
Divergent state is reconcilable (`forked`) or terminal (`disputed`) is a further data-local reading,
not a separate per-node state.

| State                  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Empty**              | No events for this prefix on this node.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Active**             | Linear chain; the current tip extends cleanly via `previous`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Active (sealed)**    | The chain is Active (linear); this row covers a submission whose parent sits **strictly below** `last_seal_advancing_event` — in the locked portion (a stale view of the tip, or an attempted fork below the seal). The seal-cap rejects it as `SiblingLocked`. Extending the seal event itself is a normal append and stays Active — only a **below-seal** parent is locked. (Whether the rejected fork is separately retained as evidence is witnessing-gated — see [`merge.md` §Merge outcomes](merge.md#merge-outcomes).)                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Divergent**          | A live fork: two distinct events at one serial; the chain is **frozen**. A privileged event extending `v_{d-1}` is retained as non-canonical evidence per invariant 4, not extended onto. Read `forked` (≤ 1 privileged branch) or `disputed` (≥ 2) data-locally.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Divergent (sealed)** | A live fork **at the seal** — a competing event at the seal-advancer's own serial `N` (both children of `v_{N-1}`). You can fork the **present**, not the **past**: below the seal is locked, so a competing event there is inert (dead), never a live fork. The node accepts the seal-advancer (`Rot`/`Ror`/`Wit`/`Rec` at `N`; seal → `N`), then a competing `Ixn@N` arrives — `SiblingLocked` (its parent `v_{N-1}` sits below the seal), retained as evidence — and the chain reads `forked` / `disputed` over its **at-or-above-seal** competing tips ([§Effective-SAID convergence](#effective-said-convergence)). A `Rot` doesn't resolve the fork; a `Rec` does. The `Rec` lands **after** the seal (`rec.previous = seal.said` ⇒ `rec.serial = N+1`; a `Rec` _at_ the seal's serial would itself be a competing event → dispute) and **condemns** the losing branch (root-condemnation marks it dead — distinct from the forbidden below-seal _extension_, invariant 5). |
| **Recovered**          | Clean chain after the `Rec` committed one losing branch's root as its `fork` in the merge transaction (the root condemning its subtree; every other competing branch closes below the seal and by descent). Equivalent to Active in subsequent rules.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Decommissioned**     | A terminal `Dec` with no competing privileged event at its position — the `Dec` is the canonical tip. Fully terminal: all submissions rejected by the seal-cap or the kind-schema rule. (A content event that raced the `Dec` lands as a dead sibling — the `Dec` wins on tier-rank; see [§Matrix 4](#matrix-4-repair-completeness).)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

## Merge outcomes — the cell vocabulary

Every cell in Matrices 1-2 names the **merge outcome** the engine returns for that (chain state,
submitted kind) — the single verdict the real merge engine produces per submission
([`merge.md` §Merge outcomes](merge.md#merge-outcomes) is authoritative). Each outcome is one
verdict with a fixed effect on the chain:

| Outcome               | Verdict                                                                                                       | Chain after                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Accepted**          | admitted                                                                                                      | extends linearly (→ **Decommissioned** on a `Dec`) |
| **Diverged**          | admitted as a fork                                                                                            | **Active → Divergent**                             |
| **Recovered**         | repair admitted — resolves a divergence, _forming_ it too when the repair attaches **before** the current tip | → **Active**                                       |
| **RecoverRequired**   | nothing lands (guidance)                                                                                      | stays **Divergent** (frozen)                       |
| **SiblingLocked**     | rejected — parent below the seal, or would fork the spine                                                     | unchanged                                          |
| **KelDecommissioned** | rejected — a `Dec` admits no successor                                                                        | unchanged (terminal)                               |
| **Rejected**          | rejected — structurally inapplicable here                                                                     | unchanged                                          |

## Matrix 1: Local submissions

What happens when a client submits events to the merge engine on a single node. Each cell is a merge
outcome (above); the structural _why_ is in [§Notes on cell routing](#notes-on-cell-routing).

| Chain state            | `Icp` / `Fcp` | `Ixn`             | `Rot`             | `Ror` / `Wit`     | `Rec`                  | `Dec`             |
| ---------------------- | ------------- | ----------------- | ----------------- | ----------------- | ---------------------- | ----------------- |
| **Empty**              | Accepted      | Rejected          | Rejected          | Rejected          | Rejected               | Rejected          |
| **Active**             | Rejected      | Accepted          | Accepted          | Accepted          | Accepted / Recovered ᵃ | Accepted          |
| **Active (sealed)**    | Rejected      | SiblingLocked     | SiblingLocked     | SiblingLocked     | SiblingLocked          | SiblingLocked     |
| **Divergent** (frozen) | Rejected      | RecoverRequired   | SiblingLocked     | SiblingLocked     | Recovered ᵇ            | SiblingLocked     |
| **Divergent (sealed)** | Rejected      | SiblingLocked     | SiblingLocked     | SiblingLocked     | Recovered ᶜ            | SiblingLocked     |
| **Recovered**          | Rejected      | as Active         | as Active         | as Active         | as Active              | as Active         |
| **Decommissioned**     | Rejected      | KelDecommissioned | KelDecommissioned | KelDecommissioned | KelDecommissioned      | KelDecommissioned |

### Guarded cells

- **ᵃ Active × `Rec`** — depends on the repair's shape: **Accepted** if it extends the current tip
  (syncing an already-recovered chain); **Recovered** if it attaches at the submitter's own last
  event **before** the current tip (retained tip ≠ tip) — it forms a fork and resolves it in one
  action, and **the archived branch must be content-only**; **Rejected** if it is a _bare_ `Rec`
  with no `fork` on a non-divergent tip. An archived branch carrying a privileged event → **Rejected
  → `disputed`**.
- **ᵇ Divergent × `Rec`** — **Recovered** if every competing branch is content-only; **Rejected →
  `disputed`** if any competing branch holds a privileged event (a repair can never archive a
  rotation — the fork is terminal).
- **ᶜ Divergent (sealed) × `Rec`** — **Recovered**: the resolving `Rec` attaches
  `rec.previous = seal.said` (landing at serial `N+1`) and condemns the competing branch at `N`; a
  `Rec` _at_ the seal's own serial `N` would itself be a competing event → dispute. Every other cell
  on this row is a below-seal-parent submission (`SiblingLocked`).

### Notes on cell routing

- **Privileged event creating or joining a divergence (any chain state).** A privileged event
  (`Rot`, `Ror`, `Wit`, or `Dec`) with `previous = v_{d-1}.said` whose landing would create or join
  a divergence does not extend the canonical chain — it is retained as non-canonical evidence per
  invariant 4; the merge engine returns `SiblingLocked`. When the retained event is another
  federation peer's locally-landed privileged event (a cross-node privileged-vs-privileged race),
  each node now holds both branches and reads the divergence data-locally — a second privileged
  branch reads `disputed`. See [§Matrix 3: Race matrix](#matrix-3-race-matrix).
- **Active (sealed) and Divergent (sealed).** The seal-cap (`parent_serial >= seal_serial`) rejects
  every submission whose parent sits in the locked portion; all extensions of `v_{seal-1}` /
  `v_{d-1}` return `SiblingLocked`. (Whether a rejected fork is separately retained as evidence is
  witnessing-gated — see [`merge.md` §Merge outcomes](merge.md#merge-outcomes).) The pre-seal
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

When a **source** node propagates a KEL to a **sink**, the transfer reads the source's chain state
and submits to the sink's merge engine. Each cell is the **canonical merge outcome at the sink**
(the vocabulary defined above, before Matrix 1); the transfer mechanics — reordering, send-side
partitioning — are in the notes below. The cell names the **canonical** result only. Independently,
a sink **retains** any competing branch it receives as non-canonical evidence (keep-all-data) — and
that retention, not the canonical outcome, is what moves the sink's effective SAID and drives digest
convergence (a `RecoverRequired` cell still ingests the branch as evidence even though nothing lands
canonically).

"Active (retained)" means the sink has the eventual retained branch's non-divergent chain. "Active
(alternate)" means the sink has the eventual archived-tail branch's non-divergent chain (submitted
to that node before the divergence was detected elsewhere). The protocol cannot distinguish the two
from chain data alone — "retained" is the branch the `Rec` (whoever holds the recovery key)
ultimately keeps.

| Source ↓ / Sink →           | Empty    | Active (retained) | Active (alternate) | Divergent       | Decommissioned |
| --------------------------- | -------- | ----------------- | ------------------ | --------------- | -------------- |
| **Active**                  | Accepted | Accepted          | Diverged           | RecoverRequired | SiblingLocked  |
| **Recovered**               | Accepted | Accepted          | Recovered          | Recovered ᵈ     | SiblingLocked  |
| **Divergent** (unrecovered) | Diverged | Diverged          | Diverged           | Accepted ᵃ      | SiblingLocked  |
| **Decommissioned**          | Accepted | Accepted          | Diverged ᵇ         | RecoverRequired | Accepted ᶜ     |

**Column note (the Active-source row).** "retained" / "alternate" are relative to the **source's**
branch: a sink on the _same_ branch as the source reads "retained" (→ `Accepted`, dedup); a sink on
a _different_ branch reads "alternate" (→ `Diverged`, a fork forms). For a not-yet-recovered Active
source, which branch is eventually retained isn't known — the outcome depends only on
same-vs-different-branch.

**Guarded cells:**

- **ᵃ Divergent → Divergent** — both nodes already hold the fork; the transfer exchanges any
  competing branch each lacks and each **retains** it as evidence (keep-all-data — this branch
  ingestion, not a canonical merge outcome, is what moves the digest), so they converge on the same
  real value. No new canonical state.
- **ᵇ Decommissioned → Active (alternate)** — the incoming `Dec` and the sink's content branch form
  a divergence; the `Dec` wins on **tier-rank** and the content archives dead → the sink reads
  **Decommissioned**. (This is the one fork that auto-resolves without a `Rec` — a terminal `Dec`
  admits no successor; the base outcome legend has no tier-rank token, so this two-step outcome is
  the exception.)
- **ᶜ Decommissioned → Decommissioned** — both already hold the `Dec` (dedup); already converged.
- **ᵈ Recovered → Divergent** — the source's chain carries the `Rec`, which lands in the sink's
  `since:{own seal}` window and resolves the sink's frozen divergence (edge case 2) → **Recovered**
  (merge.md's Divergent-KEL routing: a batch containing a `Rec` runs the discriminator → Recovered).
  **`disputed`** if the sink holds a competing privileged branch the `Rec` would condemn; a sink
  divergence that _postdates_ the source's `Rec` (a fresh fork above `seal2`, uncovered) stays
  **RecoverRequired**.

**Divergent (sealed) as a source/sink.** Not enumerated as its own row/column: it transfers as its
underlying branches — a below-seal competing branch rides along as evidence, adding no canonical
state — and its per-node classification + digest are pinned in the state table +
[§Effective-SAID convergence](#effective-said-convergence).

### Notes on cell routing

- **Sink terminal state** (Decommissioned). The source branched before the sink's `Dec`, so its
  competing event shares the `Dec`'s parent — it is a **sibling to the `Dec`**, not a chain _from_
  the `Dec`. The seal-cap rejects it with `SiblingLocked`. (The `KelDecommissioned` diagnostic — a
  chain-from-`Dec`, parent kind `Dec` — arises for local tip-extension as in
  [Matrix 1](#matrix-1-local-submissions), not for gossiped chains, which never carry an event built
  on the sink's `Dec`.) When the source carries a competing privileged event racing the sink's
  `Dec`, both nodes end up holding both branches and read `disputed` data-locally.
- **Send-side partitioning** (Source: Divergent). The source partitions the chain into sub-batches
  the sink will accept under its routing rules. The structural requirement is on the sender:
  receive-side ordering can sort what arrived, but cannot fix composition problems where the sink's
  merge handler will reject a particular batch composition. See
  [`merge.md` §Gossip send-side partitioning](merge.md#gossip-send-side-partitioning) and
  [§Transfer ordering](#transfer-ordering) below.
- **Divergent → Divergent sink.** The effective SAID is a **real digest over all held tips**, so two
  sinks converge **once they hold the same tips** — anti-entropy exchanges the competing branch
  events each lacks (keep-all-data + `since: last_seal.said`); until then their digests differ,
  which is itself the signal to sync. A one-branch holder escalates a `forked` reading to `disputed`
  when a second privileged branch arrives.
- **Cross-node privileged-vs-privileged races.** When the source and sink hold different competing
  privileged events at the same serial, each node retains the other's event as non-canonical
  evidence and reads `disputed` data-locally — see [§Matrix 3](#matrix-3-race-matrix).

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

All nodes must eventually agree on the effective SAID for each prefix — the chain's canonical
wire-format identifier, exchanged during anti-entropy. It is a **real digest over all the tips a
node holds** (no synthetics): a deterministic function of the events it holds.

| State                                    | Effective SAID (the value)                                                                                                                                                                                               | Converges?                                                                                                                                                                                                                                                                                                                                                         |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Active / Recovered**                   | the canonical **tip event SAID**                                                                                                                                                                                         | ✓ (identical chains after gossip)                                                                                                                                                                                                                                                                                                                                  |
| **Decommissioned**                       | the `Dec`'s SAID — the canonical **tip** (dead events at higher serials don't move it)                                                                                                                                   | ✓ where the `Dec` landed uncontested; a competing privileged event racing it → both nodes hold both branches → `disputed` data-locally ([§Matrix 3](#matrix-3-race-matrix))                                                                                                                                                                                        |
| **Divergent — `forked` _or_ `disputed`** | a **real digest over all held tips** (a deterministic hash of the sorted tip SAIDs, the canonical one included; the `forked` / `disputed` verdict is a _separate_ data-local walk — ≤ 1 vs ≥ 2 privileged past the fork) | ✓ **once the branches propagate** — true convergence rests on guaranteed witnessed propagation ([§Federation convergence](../../../../protocol-doctrine.md#federation-convergence)); **fail-secure under partition** — nodes holding different branch sets compute different digests, so disagreement drives a fetch (reachable) or reads as multi-source distrust |

The digest is **tip-sensitive** — it moves the instant a node's held tip set changes, which is what
lets the effective-SAID delta drive anti-entropy (a tip a node lacks shows up as a differing digest,
prompting the fetch that assembles it). Convergence is therefore **conditional on propagation** —
eventual barring partition, fail-secure under partition — not the unconditional convergence a
`(state, prefix)` synthetic would give: a branch-agnostic synthetic **masks** a missing branch (two
differently-forked nodes falsely agree), whereas the real digest **exposes** the difference. Whether
a fork is `forked` or `disputed` is the **branch-walk's** result over the retained branches,
separate from the digest. See
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison) for the
cross-primitive framing.

**Finality of a Recovered reading is two-valued, per question** (the repair-completeness split —
[§Matrix 4](#matrix-4-repair-completeness)). The repair is **content-final** the instant it seals:
root-condemnation plus deadness-descends close every losing content branch, present or later-grown.
On the privileged side, two distinct properties: **no-resurrection** (unconditional — nothing
archived is ever un-archived, from the instant the repair lands) and **resolution-stability** (the
reading stays non-`disputed`, once the minting capability is neutralized (the `Rec`'s rotation —
vacuous for a benign fork with no adversarial minter) **and** the beacon shows no omitted privileged
branch — stable barring the eclipse residual and a historical rotation-reserve compromise, both
fail-secure, each flipping the reading to `disputed`). A **`disputed`** reading is terminal
everywhere.

## Matrix 3: Race matrix

Concurrent privileged-vs-privileged races between federation peers — both submitting privileged
events extending the same parent `v_{d-1}` to different nodes — uniformly resolve via the same
structural shape: each event lands as a clean linear-chain extension on its submitting node and
advances the local seal; gossip then delivers each event to the other node, where the seal-cap
rejects it as a canonical extension (`parent_serial < seal_serial`) **but retains it as
non-canonical evidence** (keep-all-data). Each node ends up holding both branches and reads the
divergence by a **data-local walk** — two privileged branches past the fork read `disputed`.

The race participants — any pairing across `{Rec, Ror, Rot, Wit, Dec}` — produce identical
structural outcomes per-node:

- Each node keeps its locally-landed first-receive as its canonical tip.
- The gossip-arriving competing event is not admitted as a canonical extension (the seal-cap returns
  `SiblingLocked`) but is retained as non-canonical evidence. On the Dec'd side the treatment is
  identical — a Decommissioned chain is sealed at its `Dec`, so the seal-cap rejects per
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).
- Each node reads the prefix as `disputed` by a data-local walk over the two retained privileged
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
    two privileged branches past v_{d-1} → disputed
    effective_said(A) = effective_said(B) = hash(sorted competing privileged tips)
    → both nodes hold the same two branches → the same real digest → converge on disputed.
```

Convergence in this scenario is **data-local**: once keep-all-data retention plus the witness beacon
deliver both branches to each node, every node reads `disputed` from the same retained branches. A
selected witness signs up to **two** distinct structurally-valid **privileged** siblings per chain
position (two both-witnessed siblings are the `disputed` proof, then further ones are declined);
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

- **Tier-2 path.** An adversary holding the rotation-key preimage can force a `disputed` divergence
  by racing `Rot_adversary` against an honest concurrent `Rot_operator` or `Ror_operator` on
  different federation nodes. The forging bar is tier-2 (one preimage), strictly easier than the
  tier-3 bar required to forge `Ror` / `Rec` / `Wit` / `Dec`. A `{Rot, Rot}` divergence is moreover
  a **proof of rotation-reserve compromise** — two valid rotations reveal the one rotation preimage
  in force at `v_{d-1}`.
- **Tier-3 path.** An adversary holding both preimages can force a `disputed` divergence by racing
  any recovery-revealing event (`Ror` / `Rec` / `Wit` / `Dec`) against operator submissions. Once an
  adversary's tier-3 event has landed on any federation node, no in-band protocol recourse exists.

Both paths produce identical per-node structural outcomes (matrix above) and resolve to the same
data-local `disputed` reading. See
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).

## Matrix 4: Repair completeness

The repair-side dual of matrices 1–3. Matrices 1–3 prove **detection** — every node reads the same
`forked` / `disputed` verdict from the data it holds. This matrix proves **repair completeness**: a
landed repair is **final** (chain → Active) or proves the fork **terminal** (`disputed` → reincept),
for every combination of {tier of the losing branch} × {named by the `fork` root versus unnamed} ×
{delivered before or after the seal} — and every honest node converges on the same reading. The
merge-layer rules being proved sound are
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
privileged → `disputed`), and its **breadth** is bounded by **retention** (nodes keep **≥ 2
competing events per position** as evidence and drop the rest — the content analog of the ≥
2-per-spine-position privileged bound; the queryable set is bounded), with the **one-content-sibling
witnessing rule** on top (a witness signs the first structurally-valid content sibling at a position
and declines later ones; privileged siblings are witnessed up to **two** per position — two
both-witnessed siblings prove `disputed`, then further ones are declined; the repair is privileged,
so the single resolving repair needs no separate clause). Dead events are **witnessed and
propagated** yet **never canonical**; an adversary can _author_ extra siblings, but they are
droppable — never making the retained fork unbounded (a query-DoS surface only).

### The completeness matrix

Rows = {tier of the losing branch} × {named by the `fork` root versus unnamed} × {delivery timing}.
Cell = reading + closing rule. (Unnamed = an additional held branch or a truly-missed one —
identical closure either way, which is why a single named root suffices.) (The cross-layer rows — a
SEL event on a dead owner-IEL anchor; a SEL fork riding an IEL fork — land with the `sel/` + `iel/`
anchor-validation doctrine, forward-referenced below.)

| losing branch                                                                      | reading                                                                                                                                       | closes with                                                                                                                                                                                |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **content**, root named in `fork`                                                  | condemned subtree (all descendants dead, growth-proof) → **Active** on the retained chain                                                     | root-condemnation; the seal-cap bounds each dead lineage's _depth_ (≤ 64 past the seal)                                                                                                    |
| **content**, root named, branch **grows** after the repair (lagging node)          | grown events dead **by descent** — no follow-up repair → **Active**                                                                           | condemnation is over the subtree, not a tip; growth past depth-64 needs a seal-advancer → privileged → `disputed`                                                                          |
| **content**, **unnamed** (additional or missed), delivered or grown after the seal | first event locked below the seal; growth dead by descent → **Active**                                                                        | seal-cap (first event) + deadness-descends (growth); no orphan-drop (kept, re-issued forward)                                                                                              |
| **content**, unnamed, held when the repair arrives                                 | repair **accepted**, the branch drops below the advanced seal → inert → **Active**                                                            | an unnamed-content repair is accepted; the branch inerts rather than freezing the chain                                                                                                    |
| **privileged** (non-content) — a repair attempted against it, or a 2nd one present | ≥ 2 privileged → **`disputed` → reincept**                                                                                                    | validated-not-trusted (a condemned subtree with a privileged event rejects the `Rec`, which is retained and counted); FORCE-by-provenance; a below-seal privileged branch is **not** inert |
| **privileged** (non-content) — a **lone unretained** branch, **no repair attempt** | one privileged branch → **`forked`-frozen** (reconcilable only by its author; reincept is the operational exit, the _reading_ stays `forked`) | invariant 4 (≥ 2 privileged is the `disputed` threshold; one is `forked`) — _not_ `disputed`                                                                                               |
| **≥ 2 privileged branches**                                                        | **`disputed` → reincept**                                                                                                                     | invariant 4; [§Matrix 3](#matrix-3-race-matrix)                                                                                                                                            |
| **`{Dec, content}` terminal tip** (no repair)                                      | `Dec` wins on tier-rank, content archived non-canonical → **Decommissioned**; a late privileged sibling → **`disputed`**                      | tier-rank, no repair authored; the after-seal privileged asymmetry                                                                                                                         |

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
  privileged branches past the fork → **`disputed`**, not archived (validated, not trusted). So
  root-condemnation can never dead-mark a rotation to un-rotate it. The walk-independent closer:
  every privileged KEL event is a **seal-advancer** → a competing seal → a **spine fork** →
  `disputed`, independent of any walk bound.
- **No stale-authority revival.** Root-condemnation reaches no _live_ state — it **marks a subtree
  dead**, never extends or revives an event. There is **no below-seal archival operation**, so the
  seal-cap stays unconditional.
- **Bounded fork (depth _and_ breadth).** **Depth** ≤ 64 events past the last seal per lineage (the
  seal-advance cap — a deeper event must author a seal-advancer, privileged → `disputed`).
  **Breadth** is bounded by **retention**: nodes keep ≥ 2 competing events per position as evidence
  and drop the rest ("two prove the fork, then stop"), so the _queryable_ set is bounded and there
  is no query DoS. The **one-content-sibling witnessing rule** is the _kind-aware layer_ on top: a
  witness signs the **first** structurally-valid _content_ sibling at a position and **declines
  every later one** — while **privileged siblings are witnessed up to two per position** (two
  both-witnessed siblings are the `disputed` proof — dispute evidence, competing seals form a spine
  fork; further spray is declined and droppable). The **single `Rec` repair** that lands on a
  content-only divergence is simply the first privileged sibling at that position (a _second_,
  competing repair is `{Rec, Rec}` → `disputed`; at most one repair can resolve a content-only
  divergence). With the majority floor this bounds co-witnessed content breadth to ≤ 1 absent
  fork-cost byzantine witnesses; arrival order decides only _which_ content sibling is the witnessed
  one — the bound rests on **retention + kind-awareness**, arrival-independent. A signing-key
  (tier-1) re-forker can _author_ more content siblings, but they sit beyond the retained ≥ 2 →
  droppable + declined; unnamed siblings beyond the retained set are seal-cap-inert (the repair does
  not need them). Every dead event is non-canonical and never flips a reading, and the depth-cap
  forces the seal-advancer that turns the fork terminal. A **privileged** event on a dead branch (it
  needs the reserve — tier 2+) → `disputed` regardless (the no-buried-rotation guard) — the
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
  prefix** → `disputed` — the fail-secure outcome of revealing tier-3 material into a contested
  window (Matrix 1's Divergent × `Rec` cell reads rejected → `disputed`).
- **≥ 2 privileged** (including a beacon-late privileged branch) → **`disputed`** everywhere
  (FORCE-by-provenance once a node holds ≥ 2; via receipt-then-fetch otherwise); the effective SAID
  is the **real digest over all held tips** (all nodes converge on it once the branches propagate).

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
  a dead or below-seal lineage years after beacon confirmation → flips the reading to `disputed`
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
| Dead-lineage depth                     | ≤ 64 past the last seal      | Seal-advance cap (invariant 1); a deeper event needs a seal-advancer — privileged, `disputed` when competing.                                                                                                 |
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
and a **`disputed`** prefix (≥ 2 privileged branches past a fork) — both → reincept, neither
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

  Both nodes:  v_0 → ... → v_{d-1} ─┬─ ixn_a @ v_d   (Divergent, forked — frozen)
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

Local party detects via an existence-check on the server that branch_A / branch_A' are no longer the canonical chain — rec_B kept branch_B and condemned branch_A's subtree. The footgun to avoid: do NOT append a privileged event to the stale branch. Submitting a Dec that extends the party's local tip (branch_A' at v_{d+2}, or branch_A) does not cleanly decommission — the Dec is a dual-signed privileged event landing on a condemned branch below rec_B's seal at v_{d+1}. The seal-cap (invariant 5) refuses it as a canonical extension, but keep-all-data retains it, and a privileged event on a condemned branch is a second privileged branch past the fork → the reading flips to disputed and the prefix terminalizes (the reserve was revealed into a contested window — fail-secure; a condemned subtree must stay content-only). Correct recourse: re-fetch the server state, confirm the canonical tip (rec_B), then either submit Dec extending that tip cleanly or accept the server-side state without decommissioning — never append a privileged event to a branch not confirmed canonical.
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
canonical tip and retains the competing branch as evidence; every node reads `disputed` by a
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
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#effective-said-comparison) —
  effective-SAID comparison (cross-primitive).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (subsequent sub-issue): the kind-scoped witnessing ladder, the majority floor, the
  beacon, divergent witness receipts.
