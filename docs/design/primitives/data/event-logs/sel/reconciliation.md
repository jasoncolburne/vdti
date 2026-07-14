# SEL Reconciliation — Divergence Correctness Matrix

This doc is the **load-bearing correctness proof** for the SEL primitive. It exhaustively enumerates
every combination of **the SEL's own witnessed divergence** and **the owner-IEL deadness it
inherits**, composed by the rule that deadness comes first, and demonstrates that each case
terminates correctly and that all nodes converge on the same effective SAID. A SEL's reading is a
product of two independent axes, and this matrix is the enumeration of their crossing. Without it
the merge engine, the witnessing layer, and the severance rule are not proven sound — they are
designed against this enumeration.

For lifecycle prose (states, the witnessed chain, the seal and its advancers, severance), see
[`log.md`](log.md). For per-kind reference (the six kinds, the three axes, the anchor matrix),
[`events.md`](events.md). For the merge-layer routing rules being proved sound,
[`merge.md`](merge.md). For the verifier walk, [`verification.md`](verification.md). The IEL's own
correctness proof is the counterpart for the owner-IEL side of the anchor edge
([`../iel/reconciliation.md`](../iel/reconciliation.md)).

## The two axes

A SEL's reading composes two inputs that arise for entirely different reasons:

- **Axis A — the SEL's own witnessed divergence.** Two distinct SEL events at one
  `(prefix, serial)`. A content fork forms only under witness compromise (first-seen prevents it
  otherwise); a sealed fork with two accepted branches is provable witness collusion. Resolution is
  **by tier**: content is buriable by a seal-advancer, a sealed branch is not.
- **Axis B — inherited owner-IEL deadness.** A SEL event's owner-IEL anchor sits on a branch the
  owner IEL later buries. The dead anchor **severs** the SEL — dead and un-verifiable from the
  earliest dead anchor, with no repair.

They compose by **deadness-precedence**: you never bury something already dead, so Axis B is
resolved first. A severed branch drops out of every Axis-A verdict — it auto-resolves a content fork
to the live branch, it downgrades a Disputed to the live branch, and on a `{Trm, content}` shape it
drops the severed branch and leaves the survivor (the content → Active, or the `Trm` → Terminated).
Axis A's machinery (a burying seal-advancer, the sealed-to-Disputed escalation) runs **only** on the
all-live remainder.

## Invariants

The cases below depend on these protocol-enforced invariants, stated structurally — the safety
claims hold _by construction_.

1. **The SEL witnesses itself.** Content forks are prevented by first-seen at the SEL's own
   `(prefix, serial)` with the witnessing floor; a content fork that forms owns the whole quorum
   intersection (a witness compromise). Sealed events are first-seen and retained, so two accepted
   sealed branches are provable collusion. An owner cannot equivocate its SEL even under a linear
   owner IEL.
2. **Only tier-1 content is buriable.** A seal-advancer (`Gnt` / `Trm` / `Sea`) buries a content
   loser by advancing the seal past it; a sealed branch is never buried or overturned.
3. **A dead owner-IEL anchor severs the SEL** at the earliest dead anchor — dead and un-verifiable
   from there, no repair. Severed is a truncation, not a fifth state.
4. **The verdict is by accepted-sealed-branch count.** At most one accepted sealed branch past a
   fork → **Forked** (recoverable); two or more → **Disputed** → re-incept.
5. **Authorization is the owner IEL's threshold, delivered by the anchor.** A SEL event's count is
   drawn from the owner IEL's threshold vector and carried by the anchoring IEL event; a SEL hosts
   no roster of its own.

## SEL states (proof states)

| State          | Description                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Empty**      | No events for this prefix on this node.                                                                                                           |
| **Active**     | Linear chain; the tip extends cleanly via `previous`, each event witnessed and owner-IEL-anchored.                                                |
| **Forked**     | A live content fork (≤ 1 accepted sealed branch) — a witness compromise; recoverable by a burying seal-advancer on the winning branch.            |
| **Disputed**   | A live fork with **≥ 2 accepted sealed branches** — provable witness collusion; terminal. The owner re-incepts (a lookup SEL at a fresh lineage). |
| **Terminated** | A `Trm` is the permanent end. Not absorbing — a chain _from_ `Trm` → `Terminal`; a sealed sibling → `Disputed`; a content sibling → buried.       |

**Severed** is not a state — it truncates the SEL to its last live-anchored event, after which the
chain reads one of the four above (typically Active, or auto-resolved from a fork).

## Matrix 1: Axis A — the SEL's own witnessed divergence (owner IEL live)

With the owner IEL linear and live beneath, a SEL's reading is its own witnessed state. Every valid
submission on an Active chain is in one of three attach-positions.

### Position 1 — extends the tip (linear)

| new event     | outcome                            |
| ------------- | ---------------------------------- |
| `Ixn` / `Pin` | `Extended` (re-pins)               |
| `Gnt` / `Sea` | `Extended` (the seal advances)     |
| `Trm`         | `Terminated`                       |
| `Icp`         | `Invalid` (a chain already exists) |

### Position 2 — adjacent to the last seal (competes with the seal)

| new event     | outcome                                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| `Ixn` / `Pin` | `Forked` — a content sibling of a seal; a witness compromise formed it (first-seen would have declined it)    |
| `Gnt` / `Sea` | `Disputed` — a second accepted sealed branch (provable collusion); a witness-declined sibling is held pending |
| `Trm`         | `Disputed` — a second accepted sealed branch                                                                  |

### Position 3 — on the content run past the last seal

| new event     | outcome                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------ |
| `Ixn` / `Pin` | `Ignored` — a content sibling of content is declined by witnessing; the chain stays Active                   |
| `Gnt` / `Sea` | `Recovered` — the seal buries the content run past its attach point; the content dies on ascent → **Active** |
| `Trm`         | `Terminated` — the content adjacent to and beyond the `Trm` is buried; the `Trm` is the permanent end        |

### The other states

- **Empty** — only `Icp` batched with its serial-1 v1 (a bare `Pin`, a first `Ixn`, a lookup's `Trm`
  or `Gnt`) → `Extended`; every other shape → `Invalid`. A bare `{Icp}` with no v1 authenticates
  nothing.
- **Forked** — origination-frozen; resolved by a burying seal-advancer on the winning branch (→
  `Recovered`, Active) or a `Trm` on the winning tip (→ `Terminated`). A second accepted sealed
  branch → `Disputed`. A plain content SEL uses a `Sea` (the neutral advancer) when it has no
  natural `Gnt` / `Trm`.
- **Disputed** — terminal; a new submission is `Ignored`. The exit is re-incept (a lookup SEL at a
  fresh lineage).
- **Terminated** — a submission chaining _from_ the `Trm` → `Terminal`; a sealed sibling →
  `Disputed`; a content sibling → buried below the `Trm`'s seal.

## Matrix 2: Axis A crossed with Axis B (the load-bearing matrix)

The SEL's characteristic matrix: for each combination of (the SEL's own divergence shape) × (the
owner-IEL state beneath the losing anchor), what the SEL reads. Deadness-precedence resolves Axis B
first.

| SEL own state           | owner IEL beneath the losing / relevant anchor            | SEL reads                                                                                                                                                                                                                                          |
| ----------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| linear                  | linear                                                    | **Active**                                                                                                                                                                                                                                         |
| linear                  | a live-anchored event on a **dead** owner-IEL branch      | **Severed** at the earliest dead anchor → the pre-sever chain reads Active                                                                                                                                                                         |
| content fork            | losing anchor on a **dead** owner-IEL branch              | **auto-resolves** — the severed loser drops, the SEL shrinks to the shared tip → **Active** (no `Sea` needed)                                                                                                                                      |
| content fork            | losing anchor **live, at/above** the owner-IEL seal       | a **`Sea`** on the SEL is the normal path → **Active**; the owner IEL can instead deliberately fork and re-bury the losing anchor's branch (severance as a heavy side effect), not a symmetric free choice                                         |
| content fork            | losing anchor **live, below** the owner-IEL seal (locked) | a **SEL seal-advancer at the tip** (a `Gnt` / `Trm` if natural, else a `Sea`) → **Active** / **Terminated**                                                                                                                                        |
| `{Trm, content}`        | live                                                      | **Terminated** — the `Trm` wins on tier-rank, the content buries (no owner-IEL burial needed)                                                                                                                                                      |
| `{Trm, content}`        | the **`Trm`'s** anchor on a **dead** owner-IEL branch     | **unreachable by construction** — a `Trm`'s sealed `Rev`/`Dth` anchor is never buried alone (only content is buriable; a Disputed owner IEL kills both → the both-dead row). For completeness, were it severed the content would survive → Active. |
| `{Trm, content}`        | the **content's** anchor on a **dead** owner-IEL branch   | the content severs and drops → the `Trm` stands alone → **Terminated**                                                                                                                                                                             |
| `{Trm, content}`        | **both** anchors on **dead** owner-IEL branches           | **severed at the fork** — both branches drop, nothing past the fork is verifiable                                                                                                                                                                  |
| `{Gnt \| Sea, content}` | live                                                      | the non-terminal seal-advancer buries the content → **Recovered → Active**; crossed with owner-IEL deadness it resolves like `{Trm, content}` but a surviving seal-advancer leaves the chain **Active** (not Terminated)                           |
| ≥ 2 sealed branches     | both anchors **live** (linear owner IEL)                  | **Disputed** → re-incept (no severance available to downgrade it)                                                                                                                                                                                  |
| ≥ 2 sealed branches     | one branch's anchor on a **dead** owner-IEL branch        | severance **downgrades** it — the severed branch is un-verifiable, not counted → drops to the live branch → recoverable                                                                                                                            |

The load-bearing observation: **a content fork always resolves**, and _how_ keys on where the losing
anchor sits — a dead branch gives severance for free (the common case, since owner-IEL divergences
happen for the IEL's own reasons), a live-and-locked branch needs a SEL seal-advancer (which is
exactly why the neutral `Sea` exists —
[`log.md` §Why the neutral advancer is needed](log.md#why-the-neutral-advancer-is-needed)). The
crossed cases named in the design all appear here: a SEL forked under a linear owner IEL resolves by
a SEL seal-advancer; a linear SEL under a forked owner IEL resolves by severance-truncation;
both-diverged resolves by deadness-precedence.

## Matrix 3: Severance completeness

The severance-side dual of Matrix 1. It proves that inherited owner-IEL deadness always yields a
verifiable shape.

| the SEL relative to the dead owner-IEL anchor                   | reading                                                                                                                                                                                                                                         |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| no anchor on a dead owner-IEL branch                            | untouched — the SEL is unaffected                                                                                                                                                                                                               |
| a portion **pre-exists** the owner-IEL fork (shared lineage)    | not severed — it rides the pre-fork lineage; only the through-the-dead-branch portion severs                                                                                                                                                    |
| an anchor on a dead owner-IEL branch, later events through it   | **severed** at the earliest dead anchor — the pre-sever chain is live, the rest dead and un-verifiable, no repair                                                                                                                               |
| both branches of a SEL fork anchored on dead owner-IEL branches | **severed at the fork** — nothing past the fork is verifiable                                                                                                                                                                                   |
| a `Sea` authored to bury, but the loser was already severed     | deadness-precedence already resolved it, so the `Sea`'s burial effect is vacuous (nothing live to bury): a `Sea` extending the live tip is a valid no-op re-seal, while one attaching below the resolved tip is caught by the self-burial guard |

Severance is a **truncation**: it shrinks the SEL and the remaining chain reads one of the four live
states. There is no continuation on the same chain — the severed portion was the dead-branch
author's work, un-rescuable by re-pointing at the surviving owner-IEL branch (a different author).
Recovery of a severed lookup SEL is a **re-incept at a fresh lineage** (§Re-incepting a lookup SEL).

## A signing-key compromise is fully buriable

A signing-key (tier-1) compromise is the SEL's cleanest case. A stolen **signing key** can author
SEL content (`Ixn` / `Pin`, riding owner-IEL `Ixn`s), but it holds **no rotation reserve**, so it
can mint **no sealed advancer** — no `Gnt`, `Trm`, or `Sea` (each needs a tier-2 owner-IEL event,
anchored by member KEL `Rot`s). Every event the compromised key can forge is therefore **buriable
content**.

So the fork it authors is closed by a **burying seal-advancer** the owner authors with the reserve —
a `Sea` on the SEL (or a natural `Gnt` / `Trm`), or, where the losing anchor is on a dead owner-IEL
branch, severance for free. If the compromise also raced the owner IEL's content, one owner rotation
buries that owner-IEL tail and the SEL events on it die by severance. **No re-incept** is needed for
a signing-key compromise; the reserve defends the seal. A compromise that reaches the **reserve** (a
sealed branch the owner did not author) is the ≥ 2-accepted-sealed case → Disputed → re-incept — the
point of no return.

## Re-incepting a lookup SEL

The **`lineage`** counter and its positive walk are the field model in
[`log.md` §The content and lineage fields](log.md#the-content-and-lineage-fields); this section
states what **re-inception** adds. A content or random-prefix SEL re-incepts by rerolling its nonce
→ a fresh unguessable prefix. A **discoverable value lookup cannot** — its prefix is a pure function
of fixed inputs, so the same inputs recompute the same dead address; `lineage` is the remedy (a
re-incept at `lineage: n+1` is a distinct prefix, and the positive walk stops at the lowest live
lineage). This matters because a value lookup's own live state is the sole authority for its
**positive** resolution (no owner-IEL fallback there), so a Disputed or severed lineage is a real
denial that re-inception heals. Rescinding one lineage is a monotone `Trm` whose anchoring `Dth`
declares the **lineaged** target `hash('{tag}:{owner}:{data}:{lineage}')`, so the walk's per-lineage
check reads `lineage: n` dead (from its own chain **or** that target in the owner IEL's fresh
`kills[]`) while the re-established `n+1` survives — the positive walk consumes that per-lineage
check, not a separate mechanism. Declaring that **matching lineaged target** is a **feature-layer
obligation the primitive does not backstop** (the IEL never dereferences a target): the value-lookup
feature constructs the rescission against the rule via the primitive-composition helpers — a
rescission that named only an on-chain `Trm`, or a wrong-lineage target, would leave the kill on the
withholdable leg ([`verification.md` §The lineage walk](verification.md#the-lineage-walk)). A
**monotone kill** (a cred revocation, a delegate / doc-member rescission) carries **no** `lineage`
field and a **non-lineaged** target: it is answered by a single **negative check** (a verified `Trm`
→ killed), never walked. Content re-incepts by nonce-reroll and never carries `lineage` — its
`content: true` flag keeps it in a separate address namespace, so a content squat at a value's
lookup address is impossible by construction. The verifier reads the `content` flag and the
`lineage` field's presence — no tier-check on the read path — capped at `MAXIMUM_SEL_LINEAGE = 64`
([`verification.md` §The lineage walk](verification.md#the-lineage-walk)).

## Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each prefix — the value exchanged during
anti-entropy:

| State                  | Effective SAID (the value)                                                                                                                    | Converges?                                                                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active / Recovered** | the canonical **tip event SAID**                                                                                                              | ✓ (identical chains after gossip and after any burial or severance)                                                                          |
| **Terminated**         | the `Trm`'s SAID — the canonical **tip**                                                                                                      | ✓ where the `Trm` landed uncontested; two accepted sealed siblings (collusion) read **Disputed**                                             |
| **Forked / Disputed**  | a **type-tagged synthetic** recoupled to the verdict (`forked` / `disputed`), qualified by prefix + position — **not** a digest over the tips | ✓ **once the branches propagate** — the verdict and the value are both pure functions of the held event set; **fail-secure under partition** |

For a fork with no single confirmed tip the value is a **type-tagged synthetic** recoupled to the
verdict, **not** a digest over the competing tips (that set is adversarially extensible →
flood-unstable; the rationale is
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison)'s). A
data-local walk reads `forked` (≤ 1 accepted sealed) or `disputed` (≥ 2), and both the value and the
verdict are pure functions of the held event set, in lockstep on every node. A content branch buried
by a seal-advancer, and a severed portion, both drop out of the synthetic (forensic, reached by a
by-prefix flat fetch).

## Transfer ordering

For a divergent SEL the sender reorders events so the chain reconstructs the same way at the sink. A
recovered SEL is a clean linear chain (the content loser is below the seal). Only unrecovered
divergent cases reach the partitioning path:

- **An unrecovered content fork** — the longer chain first as non-divergent appends; only the fork
  event from the shorter chain is sent, routed through the overlap path → Forked.
- **A retained sealed branch** (a second accepted sealed branch of a Disputed fork) is evidence and
  **must** propagate — dropping it would split the reading across nodes.

Receive-side ordering can sort what arrived but cannot fix a batch composition the receiver's merge
handler would reject — the same reason the owner IEL partitions send-side
([`../iel/merge.md` §Cross-node races](../iel/merge.md#cross-node-races-and-gossip-send-side-partitioning)).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the witnessed chain, the seal and its advancers,
  severance.
- [`events.md`](events.md) — per-kind reference: the three axes, the cross-layer anchor matrix, the
  lookup-SEL shapes, the content and lineage fields.
- [`merge.md`](merge.md) — merge engine routing being proved sound; witnessed first-seen; severance.
- [`verification.md`](verification.md) — the verifier walk that reads both axes.
- [`../iel/reconciliation.md`](../iel/reconciliation.md) — the owner-IEL correctness proof whose
  burial dead-anchors a SEL (severance).
- [`../kel/reconciliation.md`](../kel/reconciliation.md) — the KEL correctness matrix the machine
  originates in.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery (cross-primitive);
  [§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing: the witnessing floor, first-seen, the federation-IEL schism mechanics the SEL
  inherits.
