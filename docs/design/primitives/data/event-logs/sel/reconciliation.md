# SEL Reconciliation — Cross-Layer Correctness Matrix

This doc is the **load-bearing correctness proof** for the SEL primitive. It exhaustively enumerates
every combination of (per-node SEL state) × (submitted event shape) × (IEL state beneath it) and
demonstrates that each case terminates correctly under the merge-layer routing rules and that all
nodes converge on the same effective SAID. The SEL's proof is **cross-layer** — its central result
is a theorem that reduces every SEL divergence to a divergence of the IEL beneath it — so this
matrix is read alongside the IEL's own correctness proof
([`../iel/reconciliation.md`](../iel/reconciliation.md)), not in isolation. Without this matrix the
SEL merge engine and the cross-layer anchor rules are not proven sound; they are designed against
this enumeration.

For lifecycle prose (states, the seal-advancers, the down-pin, the IEL clock), see
[`log.md`](log.md). For per-kind reference (the five kinds, the three axes, the anchor matrix),
[`events.md`](events.md). For the merge-layer routing rules being proved sound,
[`merge.md`](merge.md). For the verifier walk, [`verification.md`](verification.md).

## The theorem — a valid SEL fork implies an IEL fork beneath it

The SEL's entire divergence story rests on one theorem, from which the matrices below follow:

> **A valid SEL fork implies an IEL fork beneath it. A SEL never forks under a linear owner IEL.**

The proof is the two cross-layer rules ([`merge.md`](merge.md#the-content-versus-sealed-split),
[`verification.md`](verification.md#anchor-monotonicity--the-owner-iel-is-the-clock)):

1. **Anchor-monotonicity.** A SEL event is valid only if it extends the SEL's latest IEL-anchored
   tip, computed over the IEL's canonical / retained walk. Two valid same-serial SEL events
   therefore force their anchors to be **two IEL events at one IEL position** — i.e. an IEL fork. On
   a **linear** IEL there is exactly one anchored tip at each serial, so a SEL cannot present two
   valid same-serial events: a re-anchor at an already-attributed serial is malformed → inert, and
   an unheld anchor is skipped (not a wedge). No SEL fork forms.
2. **Cross-layer deadness-descends.** When the IEL resolves its fork (its burying seal drops the
   losing branch), the SEL events anchored on that dead IEL branch die by descent across the anchor
   edge — so the SEL fork resolves exactly as, and only when, the IEL's does.

The theorem is what lets the SEL delegate **all divergence handling to the IEL**: it runs no witness
gate and no burying seal of its own. Every SEL divergence is an image of an IEL divergence, resolved
by the IEL, and read data-locally by the SEL verifier through the anchor edge.

## Invariants

The cases below depend on these protocol-enforced invariants, stated structurally — the safety
claims hold _by construction_.

1. **Anchor-monotonicity.** A SEL event extends its SEL's latest IEL-anchored tip
   (skip-unattributable; a re-anchor at an attributed serial is inert). So a SEL forks only where
   its IEL forks (§The theorem).
2. **Cross-layer deadness-descends.** A SEL event whose anchoring IEL event is dead is itself dead —
   the IEL → SEL edge only, never KEL → IEL.
3. **Content is buriable; a seal is not.** Content (`Ixn`, `Pin`) is tier-1 and first-seen; `Gnt` /
   `Trm` are sealed on arrival and never overturned. A content fork on a plain SEL resolves
   cross-layer; a `{Trm, Ixn}` divergence resolves on tier-rank (the kill wins, the content buries).
4. **The verdict is by accepted-sealed-branch count.** At most one accepted sealed branch past a
   fork → **Forked** (recoverable via the IEL); two or more → **Disputed** (which, by the theorem,
   means the IEL is disputed beneath) → the owner reincepts.
5. **The owner IEL is the SEL's authority.** A SEL event's count is drawn from the owner IEL's
   threshold vector and delivered by the anchoring IEL event's member participations; a SEL hosts no
   roster and no witnesses of its own. Content-fork prevention on a witnessed SEL rides the owner
   IEL's witnessing floor (federation doctrine).

These make cross-layer resolution and single-owner recovery feasible. The matrices below rely on
invariants 1–4.

## SEL states (proof states)

| State          | Description                                                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Empty**      | No events for this prefix on this node.                                                                                                                                    |
| **Active**     | Linear chain; the tip extends cleanly via `previous`, each event anchored on the IEL.                                                                                      |
| **Forked**     | A live content fork with **≤ 1 accepted sealed branch** — recoverable cross-layer (the IEL's burying seal drops the losing anchor; the SEL loser dies by descent).         |
| **Disputed**   | A live fork with **≥ 2 accepted sealed branches** — by the theorem, the IEL is disputed beneath. Terminal; the owner reincepts.                                            |
| **Terminated** | A `Trm` closed the SEL, or the IEL terminated and all its SELs freeze. Not absorbing — a chain _from_ `Trm` → `Terminal`; a sealed sibling → `Disputed`; content → buried. |

## Matrix 1: Local submissions

What happens when a client submits an event on a single node, holding a given IEL anchor. The
outcome turns on **where the new event sits** relative to the tip and on **whether its IEL anchor is
attributable and live**.

### An Active chain, anchor attributable and live

| new event     | extends the tip                | competes at an existing serial                                                                                |
| ------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `Ixn` / `Pin` | `Extended` (re-pins)           | `Forked` — a content sibling; the residual awaits the IEL's cross-layer burial (a second sibling → `Ignored`) |
| `Gnt`         | `Extended` (the seal advances) | `Disputed` — a second accepted sealed branch mirrors the IEL's dispute                                        |
| `Trm`         | `Terminated`                   | `{Trm, Ixn}` → `Terminated` (tier-rank, content buries); `{Trm, Gnt/Trm}` → `Disputed`                        |
| `Icp`         | `Invalid` (a chain exists)     | `Invalid`                                                                                                     |

### The IEL anchor is not attributable or not live

| IEL anchor state                                 | outcome                                                                                                                      |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| body not held (unattributable)                   | `Unattributable` — the SEL event is **skipped, not blocking**; it re-enters routing when the anchor body arrives (no wedge). |
| already-attributed serial (a re-anchor)          | `Inert` — the re-anchor is malformed; the carrying IEL event stays valid, the SEL event never advances the tip.              |
| the anchoring IEL event is dead (below its seal) | `Inert` — cross-layer deadness-descends; the SEL event is dead on arrival, retained as evidence, never canonical.            |

### The other states

- **Empty** — only `Icp` batched with its serial-1 v1 (a bare `Pin`, a first `Ixn`, or a lookup
  SEL's `Trm`) → `Extended`; every other shape → `Invalid`. A bare `{Icp}` with no v1 authenticates
  nothing ([`log.md` §Authentication rides the v1](log.md#authentication-rides-the-v1)).
- **Forked** — origination-frozen; resolved when the IEL buries its fork (the SEL loser dies by
  descent → `Active`). A content event → `Forked` (retained; a second sibling → `Ignored`); a second
  accepted sealed branch → `Disputed`.
- **Disputed** — terminal; a new submission is `Ignored`. The exit is the owner's reincept.
- **Terminated** — a submission chaining _from_ the `Trm` → `Terminal`; a sealed sibling →
  `Disputed`; a content sibling is buried by tier-rank.

## Matrix 2: Cross-layer resolution

The SEL's characteristic matrix: for each combination of (SEL divergence shape) × (IEL state beneath
it), what the SEL reads. Every row is an image of the IEL's own state.

| SEL divergence          | IEL beneath              | SEL reads                                                                                       |
| ----------------------- | ------------------------ | ----------------------------------------------------------------------------------------------- |
| none (linear)           | linear                   | **Active** — the theorem: no SEL fork under a linear IEL                                        |
| content fork            | linear                   | **impossible** (invariant 1) — a content fork requires two IEL content siblings                 |
| content fork            | forked (≤ 1 sealed)      | **Forked** → resolves to **Active** when the IEL buries its fork; the SEL loser dies by descent |
| `{Trm, Ixn}`            | linear (one `Rev`/`Dth`) | **Terminated** — the `Trm` wins on tier-rank, the content buries; no IEL burial needed          |
| `{Gnt, content}`        | forked (≤ 1 sealed)      | **Forked** → the sealed `Gnt` branch survives, the content buries when the IEL buries its fork  |
| ≥ 2 sealed SEL branches | disputed (≥ 2 sealed)    | **Disputed** → the owner reincepts (a sealed SEL branch requires a sealed IEL sibling beneath)  |

The single load-bearing observation: the SEL's **column is a function of the IEL's state**. A plain
content SEL never self-seals, so it can only reach `Forked` / `Disputed` by riding an IEL fork; the
`{Trm, Ixn}` row is the lone SEL-local resolution, and it is a tier-rank read, not a fork the IEL
must bury.

## The tier-1 compromise is fully deadenable

A signing-key (tier-1) compromise is the SEL's cleanest case. A stolen **signing key** can author
SEL content (`Ixn` / `Pin`, riding IEL `Ixn`s), but it holds **no rotation reserve**, so it can mint
**no sealed SEL `Gnt` / `Trm`** (those need a tier-2 IEL event, anchored by member KEL `Rot`s).
Every event it can forge is therefore **buriable content**.

So one **IEL rotation** — a plain `Rot` that buries the forked content tail — leaves the **whole
anchored content tail dead by descent**: every SEL event on the **event author's tail** hangs off
IEL content events now below the IEL's advanced seal, dead across the anchor edge. **No reincept**
is needed. This is the SEL image of the KEL result — the rotation reserve defends the **signing**
key, so a tier-1 compromise is **fully deadenable**. A compromise that reaches the **reserve** — a
**competing sealed branch**, riding a sealed IEL event — is a second accepted sealed branch →
**Disputed** → reincept, the point of no return. The chain reads two competing branches and cannot
tell which author is legitimate, so resolution turns on **tier, never identity**.

## Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each SEL prefix — the value exchanged
during anti-entropy:

| State                 | Effective SAID (the value)                                                                                                                    | Converges?                                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active**            | the canonical **tip event SAID**                                                                                                              | ✓ (identical chains after gossip and after the IEL's burial floors the content)                                                                |
| **Terminated**        | the `Trm`'s SAID — the canonical **tip** (a `{Trm, Ixn}` buries the content by tier-rank)                                                     | ✓ where the `Trm` landed uncontested; two accepted sealed siblings (the IEL disputed beneath) read **Disputed**                                |
| **Forked / Disputed** | a **type-tagged synthetic** recoupled to the verdict (`forked` / `disputed`), qualified by prefix + position — **not** a digest over the tips | ✓ **once the IEL resolution propagates** — the verdict and the value are pure functions of the held event set; **fail-secure under partition** |

For a fork with no single confirmed tip the value is a **type-tagged synthetic** recoupled to the
verdict, **not** a digest over the competing tips (that set is adversarially extensible →
flood-unstable; the rationale for a set-independent synthetic is
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison)'s). Because
every SEL divergence is an image of the IEL's, the SEL's synthetic **tracks the IEL's verdict** — a
data-local walk reads `forked` (≤ 1 sealed) or `disputed` (≥ 2 sealed), the value and verdict in
lockstep on every node. A content branch buried by the IEL's seal drops out of the synthetic
(forensic, reached by a by-prefix flat fetch).

## Transfer ordering

For a divergent SEL the sender partitions events so the chain reconstructs the same way at the sink,
inheriting the IEL's send-side discipline:

- **A content fork awaiting cross-layer burial** — the sink needs both branches to read `forked`,
  and the IEL's burying seal (once it propagates) resolves it; the sender sends the longer chain
  first as non-divergent appends, then the fork event as an atomic batch through the overlap path.
- **A resolved SEL** (the IEL buried its fork) is a clean linear chain — the losing content is dead
  by descent below the IEL's seal, retained as forensic evidence and reached by a by-prefix flat
  fetch, not on the canonical run.

Receive-side ordering can sort what arrived but cannot fix a batch composition the receiver's merge
handler would reject — the same reason the IEL partitions send-side
([`../iel/merge.md` §Cross-node races](../iel/merge.md#cross-node-races-and-gossip-send-side-partitioning)).

## Convergence and termination

Under eventual gossip delivery and `< threshold` byzantine on the IEL, every honest node's held set
converges to the true competing set, and the SEL's verdict tracks the IEL's:

- **All-content** (IEL recovers via a burying seal) → every node reads the winning IEL branch's SEL
  chain as canonical, the losing SEL content dead by descent; converges **Active**. The effective
  SAID is the real winning tip.
- **`{Trm, Ixn}`** → the `Trm` wins on tier-rank locally; converges **Terminated**, no IEL burial
  needed.
- **≥ 2 accepted sealed SEL branches** → the IEL is disputed beneath → **Disputed** everywhere; the
  effective SAID is the verdict-recoupled synthetic, and recovery is the **owner's reincept**.

The SEL adds no new termination argument of its own: it terminates exactly when and because its IEL
does. The IEL's bounded-fork, single-page recovery, and atomic `cut` `Evl` eviction
([`../iel/reconciliation.md` §Matrix 4](../iel/reconciliation.md#matrix-4-recovery-completeness))
close the SEL's recovery by descent across the anchor edge.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal-advancers, the down-pin, the IEL clock.
- [`events.md`](events.md) — per-kind reference: the three axes, the cross-layer anchor matrix, the
  lookup-SEL shape.
- [`merge.md`](merge.md) — merge engine routing being proved sound; anchor-monotonicity; cross-layer
  deadness-descends.
- [`verification.md`](verification.md) — the verifier walk that reads the cross-layer edge.
- [`../iel/reconciliation.md`](../iel/reconciliation.md) — the IEL correctness proof this composes
  with; the burying seal and `cut` `Evl` that resolve a SEL fork cross-layer.
- [`../kel/reconciliation.md`](../kel/reconciliation.md) — the KEL correctness matrix the machine
  originates in.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery (cross-primitive);
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded);
  [§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor the content-fork-prevention theorem rides.
