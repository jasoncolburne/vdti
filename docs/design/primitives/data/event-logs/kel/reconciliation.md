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
[`log.md`](log.md). For per-kind reference (event kinds, fields, two-tier capability model),
[`events.md`](events.md). For the merge-layer routing rules being proved sound,
[`merge.md`](merge.md). For recovery doctrine (recovery attach shapes, the reserve boundary),
[`compromise.md`](compromise.md). For the verifier walk, [`verification.md`](verification.md).

## Proof structure

The proof composes four matrices:

1. **Local submissions matrix** — what every submission to every chain state produces on a single
   node. Demonstrates that the merge-layer routing rules are exhaustive and terminate correctly.
2. **Source → sink transfer matrix** — what gossip propagation between two nodes produces, for every
   combination of source and sink chain states. Demonstrates that gossip-driven sync converges
   per-node states under the merge rules.
3. **Race matrix** — what concurrent sealed-event races produce across federation peers.
   Demonstrates that the seal-cap and locked-portion bound are sound under adversarial concurrency,
   and that keep-all-data retention plus the witness beacon make the divergence readable
   **data-locally** on every node.
4. **Recovery-completeness matrix** — the recovery-side dual of matrices 1–3. Detection answers _"is
   this position Forked or Disputed?"_; this matrix answers _"is a landed recovery **final** (chain
   → Active), or does it prove the fork **terminal** (Disputed → reincept)?"_ — for every
   combination of losing-branch tier and delivery timing. Demonstrates that burial by position + on
   ascent terminates every case correctly and all honest nodes converge on one reading.

All four matrices depend on the same protocol-enforced invariants, stated next.

## Invariants

The cases below depend on these protocol-enforced invariants. They are stated structurally — the
protocol's safety claims hold _by construction_, not by observation.

1. **Seal-advance cap compliance.** Every KEL has a seal-advancing event (`Rot` / `Wit`) at least
   every `(MINIMUM_PAGE_SIZE − 1)/2 = 64` non-seal-advancing events (per lineage). Surfaced by the
   verifier and enforced by the merge handler. See
   [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
2. **Bounded divergence.** A fork can only form at-or-after the last seal-advancing event — a
   competing **content** event **below** the seal is dead on arrival (never a live fork; a competing
   **sealed** event below the seal is **dropped** too — inert, not witnessable past the seal, the
   backdate defense), and one **at** the seal's own serial forms a live fork (a sealed one →
   **Disputed** only if a second reaches threshold — witness collusion). Combined with invariant 1,
   the fork is bounded on both axes: **depth** — each fork lineage extends at most 64 events past
   the last seal (an adversary holding less than the rotation reserve can only submit `Ixn` events,
   so a deeper lineage needs a seal-advancer — tier-2 capability per
   [`compromise.md` §Two-tier compromise model](compromise.md#two-tier-compromise-model)); and
   **breadth** — nodes retain ≥ 2 competing events per position as fork evidence and drop the rest,
   with the one-content-sibling witnessing rule on top
   ([§Matrix 4](#matrix-4-recovery-completeness)).
3. **Bounded operations.** `MINIMUM_PAGE_SIZE = 129 = 2·64 + 1`, sized so the **canonical two-branch
   content fork anchored at the last seal** — both lineages (≤ 64 each) plus the burying
   seal-advancer — fits one page. This is what a **source → sink transfer** of that shape needs: the
   sink holds neither branch (it is receiving the fork fresh), so the transfer carries both
   competing branches plus the burying seal-advancer in one atomic page. **Two permitted shapes
   exceed one page and ride later pages**: **(a)** an own-`Rot` in the retained tail spans two seal
   windows, so the pre-`Rot` run rides earlier plain-linear pages; **(b)** a **≥ 3-branch** residual
   fork (the retention floor is ≥ 2, not = 2) exceeds `2·64 + 1` — extra branches ride later pages,
   and a late sealed one makes the chain Disputed (the eclipse-class residual). (A **local** node
   that already holds the competing branches in storage needs only the retained branch (≤ 64) plus
   the burying seal-advancer, validating the loser from storage.)
4. **A sealed divergence is terminal; a content divergence is recoverable.** A sealed event (`Rot` /
   `Wit` / `Trm`) that would create or join a divergence does **not** extend the canonical chain —
   it is retained as non-canonical evidence (keep-all-data) rather than discarded. A fork with **at
   most one** sealed branch is **Forked** (recoverable): a burying seal-advancer on the winning
   branch buries the content loser by position + ascent. A fork with **two or more witnessed**
   sealed branches past it is **Disputed** (reincept). Any verifier reads which by a data-local walk
   over the retained branches. A sealed branch is never buried — that would resurrect retired key
   material. See
   [§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery).
5. **Locked-portion bound is unconditional.** No event class is exempt from the seal-cap — not even
   a recovery `Rot`: a clean canonical extension requires `event.parent.serial >= seal_serial`, so
   nothing ever _extends the canonical chain_ from a parent in the locked portion, and
   stale-authority revival is structurally impossible. That refusal-as-a-canonical-extension is
   unconditional; the **disposition** of the refused event is not. A parent **strictly** below the
   seal is inert for **both tiers** — a content child is rejected `Sealed`, and a sealed child is
   **dropped** too (inert — not witnessable past the seal; the backdate defense — _not_ read
   `Disputed`). A **sibling at the seal's own serial** (parent `v_{seal−1}`) is not in the locked
   portion at all: it forms a **live fork** (Forked / Disputed, invariant 2), retained as evidence —
   the cap bounds content extended **from** the seal, not a sibling to it.
   (Retention-versus-rejection is the witnessing-gated matter — see
   [`merge.md` §Merge outcomes](merge.md#merge-outcomes).)

These invariants make synchronous resolution, single-page recovery, and atomic batched submissions
feasible. The proof matrices below rely on invariants 4–5.

## KEL chain states (proof states)

The per-node state enumeration covers every shape that can arise under the merge rules. A live fork
is **two distinct states**, not one: **Forked** (≤ 1 sealed branch past it — recoverable) and
**Disputed** (≥ 2 — terminal), each a first-class per-node state a verifier **derives** by a
data-local walk over the branches it holds (the walk is how the state is computed, not a reading
layered on a single divergent state).

| State          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Empty**      | No events for this prefix on this node.                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Active**     | Linear chain; the current tip extends cleanly via `previous`.                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Forked**     | A live fork with **≤ 1 sealed branch** past it — recoverable. The chain is **origination-frozen** (a node originates no new work onto the live fork); the state is the pure walk of the events held. A sealed event extending `v_{d-1}` is retained as non-canonical evidence per invariant 4, not extended onto. Resolved by a **burying seal-advancer** on the winning branch (a `Rot` / `Wit`), which buries the content loser below the new seal → **Active**. |
| **Disputed**   | A live fork with **≥ 2 accepted sealed branches** past it — terminal. No sealed branch can be buried (that would resurrect retired keys), so nothing resolves it and the prefix must **reincept**. Derived by the same data-local walk as Forked; the discriminator is the sealed count (≥ 2). Witnesses decline any extension of a disputed chain (barring a partition), so a new submission is `Ignored`; the only exit is reincept.                             |
| **Terminated** | The `Trm` is the **permanent** end of the canonical chain (its tier-2 signature authorizes ending it there). **Not absorbing**: a submission chaining _from_ the `Trm` → `Terminal`; a sealed sibling beside or beyond → `Disputed`; a content sibling → `Sealed`.                                                                                                                                                                                                 |

**Empty** is the pre-inception (no-chain) case, included for matrix completeness; the four
**live-chain** states are **Active** / **Forked** / **Disputed** / **Terminated**. A "proof state"
counts Empty alongside those four (five rows), while the state _machine_ is four-state.

## Merge outcomes — the cell vocabulary

Every cell in Matrices 1–2 is a **transition** (the chain moved to or held a state) or a
**rejection** (nothing changed) — the `Result<MergeTransition, MergeRejection>` the real merge
engine returns per submission ([`merge.md` §Merge outcomes](merge.md#merge-outcomes) is
authoritative).

**Transitions** — each is named for its action or resulting state (`Extended` and `Recovered` both
land **Active**):

| Transition     | Verdict                                                                                 | Chain after               |
| -------------- | --------------------------------------------------------------------------------------- | ------------------------- |
| **Extended**   | admitted, linear                                                                        | → **Active**              |
| **Recovered**  | a burying seal-advancer buries the content loser and re-reads Active                    | → **Active**              |
| **Terminated** | a `Trm` admitted — ends the chain                                                       | → **Terminated**          |
| **Forked**     | a fork with one sealed branch (or a content fork) forms or is joined                    | → **Forked**              |
| **Disputed**   | an irrecoverable fork (≥ 2 sealed) forms or is joined, or a burial hits a sealed branch | → **Disputed** (terminal) |

**Rejections** — chain unchanged:

| Rejection    | Verdict                                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Sealed**   | inert below-seal parent — not admitted                                                                               |
| **Terminal** | a `Trm` admits no successor                                                                                          |
| **Invalid**  | structurally inapplicable here                                                                                       |
| **Ignored**  | a well-formed event the witnesses decline (content-fork prevention, or a new event on a Disputed / Terminated chain) |

## Matrix 1: Local submissions

What happens when a client submits an event to the merge engine on a single node. The outcome turns
on **where the new event sits** relative to the chain's **tip** and its **last seal** (the last
seal-advancing event; below it is the locked portion). For an **Active** chain, every valid
submission is in exactly one of three **attach-positions**, mutually exclusive — the new event's
parent fixes which.

1. **Extends the tip** — the new event continues the chain from the current tip.
2. **Adjacent to the last seal** — the new event sits at the seal's own serial, competing with the
   seal. The **seal is sealed**, so it competes with a sealed event.
3. **On the run past the last seal** — the new event competes with a **content** event on the
   seal→tip run (content-only by definition); its parent may be the seal, or any later run event up
   to the tip's predecessor.

A new event whose **own serial is below the seal's** (its parent below `v_{seal−1}`) is none of
these three — it lands in the locked portion, so by the seal-cap (invariants 2, 5) it is rejected
`Sealed` (a content child) or reads `Disputed` (a sealed child), independent of attach-position. A
sibling **at** the seal's own serial (parent `v_{seal−1}`) is Position 2 — a live fork, not below
it.

The attach-position, not the chain state, carries this distinction — the state stays one of the four
live-chain states. Outcomes are the `Result<MergeTransition, MergeRejection>` vocabulary above.

### Position 1 — the new event extends the tip (trivial: linear)

| new event     | outcome                            |
| ------------- | ---------------------------------- |
| `Ixn`         | `Extended`                         |
| `Rot` / `Wit` | `Extended` (the seal advances)     |
| `Trm`         | `Terminated`                       |
| `Icp` / `Fcp` | `Invalid` (a chain already exists) |

### Position 2 — the new event is adjacent to the last seal (competes with the sealed seal)

| new event     | outcome                                                                                                                                         |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `Ixn`         | `Forked` — the sealed seal + one content sibling, a mixed race (one sealed)                                                                     |
| `Rot` / `Wit` | `Disputed` — a second _accepted_ sealed branch beside the seal (two accepted sealed; a witness-declined sibling is deferred-pending, no change) |
| `Trm`         | `Disputed` — a second _accepted_ sealed branch (else witness-declined, deferred-pending)                                                        |
| `Icp` / `Fcp` | `Invalid`                                                                                                                                       |

### Position 3 — the new event is on the run past the last seal (competes with content)

| new event     | outcome                                                                                                                                                                           |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Ixn`         | `Ignored` — a content sibling of a content event is declined by witnessing; the chain stays `Active`                                                                              |
| `Rot` / `Wit` | `Recovered` — the seal-advancer buries the run past its attach point below its new seal; the content there is dead on ascent → **Active**. Never `Disputed` — the run is content. |
| `Trm`         | `Terminated` — the content events adjacent to and beyond the `Trm` are **dead**; the `Trm` becomes the **permanent** end of the canonical chain                                   |
| `Icp` / `Fcp` | `Invalid`                                                                                                                                                                         |

### The other states

No position split is needed — each is one rule:

- **Empty** — only `Icp` / `Fcp` → `Extended`; every other kind → `Invalid`.
- **Forked** — origination-frozen; resolved by a **burying seal-advancer** on the winning branch (a
  `Rot` / `Wit` that buries the content loser → `Recovered`, Active) or a `Trm` on the winning tip
  (→ `Terminated`). A sealed event that lands as a **second** accepted sealed branch (rather than
  burying the content loser) → `Disputed`. A content event → `Forked` (retained; a second content
  sibling at a position → `Ignored`).
- **Disputed** — terminal. Witnesses **never** witness an extension of a disputed chain, so a new
  submission is `Ignored`; a branch **already** witnessed before the dispute stays retained (it
  arrives via gossip, not as a new submission). The only exit is reincept.
- **Terminated** — a submission chaining _from_ the `Trm` → `Terminal`; a **sealed** sibling beside
  or beyond the `Trm` → `Disputed`; a content sibling → `Sealed`.

### Batch submissions

The merge engine handles batches atomically:

- **`[..content.., Rot]`** — the winning-branch context plus the burying seal-advancer. The retained
  branch (≤ 64) plus the `Rot` fits one page. Processed as a single overlap or forked submission;
  the `Rot` buries the content loser by position + ascent synchronously.
- **`[Rot, Ixn]`** — auto-inserted by the builder when an `Ixn` would exceed the seal-advance cap
  interval.
- **`[Fcp, Rot]` plus the federation IEL `Fcp` and receipts** — the founder bootstrap atomic batch.
  The v=1 `Rot` anchors the federation IEL's `Fcp` marker; the KEL events land alongside that
  federation IEL `Fcp` and the cross-attestation receipts in a single transaction. See
  [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) (forthcoming) for the
  bootstrap protocol.

## Matrix 2: Source → sink transfer (gossip sync)

When a **source** node propagates a KEL to a **sink**, the transfer reads the source's chain state
and submits to the sink's merge engine. Each cell is the **merge outcome at the sink** (the
vocabulary above). Independently, a sink **retains** any competing branch it receives as
non-canonical evidence (keep-all-data) — and that retention, when it changes the sink's
**held-state**, is what moves its effective SAID and drives convergence.

"Active (winning)" means the sink holds the eventual winning branch's non-divergent chain. "Active
(losing)" means the sink holds the eventual buried branch's non-divergent chain (submitted to that
node before the divergence was detected elsewhere). The protocol cannot distinguish the two from
chain data alone.

| Source ↓ / Sink →              | Empty    | Active (winning) | Active (losing) | Forked                  | Terminated |
| ------------------------------ | -------- | ---------------- | --------------- | ----------------------- | ---------- |
| **Active**                     | Extended | Extended         | Forked          | Extended / Forked ᵈ     | Sealed     |
| **Recovered** (source burying) | Extended | Extended         | Recovered ᵈ     | Recovered / Disputed ᵈ  | Sealed     |
| **Forked** (unrecovered)       | Forked   | Forked           | Forked          | Extended ᵃ              | Sealed     |
| **Terminated**                 | Extended | Extended         | Terminated ᵇ    | Terminated / Disputed ᵈ | Extended ᶜ |

**Column note (the Active-source row).** "winning" / "losing" are relative to the **source's**
branch: a sink on the _same_ branch as the source reads "winning" (→ `Extended`, dedup); a sink on a
_different_ branch reads "losing" (→ `Forked`, a fork forms). For a not-yet-recovered Active source,
which branch is eventually kept isn't known — the outcome depends only on same-vs-different-branch.

**Row note (no Disputed source).** A **Disputed** source (≥ 2 accepted sealed branches past a fork)
needs no separate row: it transfers like a **Forked** source — its retained sealed branches
propagate (§Transfer ordering), and the sink reads **Disputed** by sealed-count (the Forked →
Disputed escalation below, [§Matrix 3](#matrix-3-race-matrix)). **Terminated** gets its own row
because it resolves by tier-rank, not by sealed-count.

**Column note (no Disputed sink).** A **Disputed** sink is a terminal fixed point: every transfer
dedups or retains the incoming branches as evidence and leaves the reading **Disputed**; a new
canonical extension is `Ignored` (the Disputed rule in [Matrix 1](#matrix-1-local-submissions)). No
column is needed.

**Guarded cells:**

- **ᵃ Forked → Forked** — both nodes already hold the fork; the transfer exchanges any competing
  branch each lacks and each **retains** it as evidence (keep-all-data — this branch ingestion, not
  a canonical merge outcome, is what moves the digest), so they converge on the same value. No new
  canonical state.
- **ᵇ Terminated → Active (losing)** — the incoming `Trm` and the sink's content branch form a
  divergence; the `Trm` wins on **tier-rank** and the content is buried dead → the sink reads
  **Terminated**.
- **ᶜ Terminated → Terminated** — both already hold the `Trm` (dedup); already converged.
- **ᵈ A burying source → Forked / Active (losing)** — when the source's run carries a
  **seal-advancer on the winning branch** (an Active source that sealed past the fork, or a `Trm`),
  transferring it to a sink that holds the losing branch **buries** the sink's competing **content**
  loser below the new seal: the sink re-reads **Active** (`Extended` / `Recovered`) or
  **Terminated** (a `Trm`, by seal-cap burial / tier-rank). A content-only source (no seal-advancer
  past the fork) lands as evidence and the sink stays **Forked** → `Forked`. A sealed loser makes
  the fork **Disputed** (never buried).

### Notes on cell routing

- **Sink terminal state** (Terminated). The source branched before the sink's `Trm`, so its
  competing event shares the `Trm`'s parent — a **sibling to the `Trm`**, not a chain _from_ the
  `Trm`. A content sibling is inert below the `Trm`'s seal → `Sealed`; a sealed sibling →
  `Disputed`. (The `Terminal` diagnostic — a chain-_from_-`Trm` — arises for local tip-extension as
  in [Matrix 1](#matrix-1-local-submissions), not for gossiped chains, which never carry an event
  built on the sink's `Trm`.)
- **Send-side partitioning** (Source: Forked). The source partitions the chain into sub-batches the
  sink will accept under its routing rules. The structural requirement is on the sender:
  receive-side ordering can sort what arrived, but cannot fix composition problems where the sink's
  merge handler will reject a particular batch composition. See
  [`merge.md` §Gossip send-side partitioning](merge.md#gossip-send-side-partitioning) and
  [§Transfer ordering](#transfer-ordering) below.
- **Forked → Forked sink.** The effective SAID is a **verdict-recoupled synthetic** (below), so two
  sinks converge **once they hold the same branches** — anti-entropy exchanges the competing branch
  events each lacks (keep-all-data + `since: last_seal.said`); until then their held state differs,
  which is itself the signal to sync. A one-branch holder escalates a **Forked** reading to
  **Disputed** when a second accepted sealed branch arrives.
- **Cross-node sealed-vs-sealed races.** When the source and sink hold different competing sealed
  events at the same serial, first-seen witnessing at that position accepts one and declines the
  other — absent collusion the nodes converge **Active** on the accepted sibling (the declined one
  retained as non-canonical evidence); two **accepted** siblings (witness collusion) read
  **Disputed** data-locally — see [§Matrix 3](#matrix-3-race-matrix).

### Transfer ordering

For divergent source chains, the sender reorders events so the chain reconstructs the same way at
the sink. A recovered source chain is a clean linear chain — the content loser is below the seal. In
normal operation, only unrecovered divergent cases reach the partitioning path.

- **Unrecovered (`Ixn`-`Ixn` fork)** — longer chain first as non-divergent appends; only the fork
  event from the shorter chain is sent. Receiver routes the fork event through the overlap path →
  Forked state.
- **A retained sealed branch** (a burying seal-advancer the content-only guard rejected, counted as
  the second accepted sealed branch of a **Disputed** fork) is evidence and **must** propagate, like
  any other retained sealed branch — dropping it would split the reading across nodes.

### Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each prefix — the chain's canonical
wire-format identifier, exchanged during anti-entropy. It is:

- **A single confirmed tip** (a linear chain, or a fork settled below the seal — Active / Recovered
  / Terminated) → **that tip's real SAID** (a terminated chain's is its `Trm`).
- **No single tip** (an unresolved fork — a live content fork, or ≥ 1 sealed branch past it) → a
  **type-tagged synthetic recoupled to the verdict** (`forked` / `disputed`), qualified by
  **prefix + position**, and **structurally distinct from any real SAID**. It is **not** a digest
  over the competing tips.

| State                  | Effective SAID (the value)                                                                                                                                               | Converges?                                                                                                                                                                                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active / Recovered** | the canonical **tip event SAID**                                                                                                                                         | ✓ (identical chains after gossip)                                                                                                                                                                                                                        |
| **Terminated**         | the `Trm`'s SAID — the canonical **tip** (dead events at higher serials don't move it)                                                                                   | ✓ where the `Trm` landed uncontested; a competing sealed sibling racing it is first-seen-declined (the accepted `Trm` wins → Terminated); only two **accepted** siblings (collusion) read **Disputed** data-locally ([§Matrix 3](#matrix-3-race-matrix)) |
| **Forked / Disputed**  | a **type-tagged synthetic** recoupled to the verdict (`forked` / `disputed`), qualified by prefix + position — set-independent, **not** a digest over the competing tips | ✓ **once the branches propagate** — the verdict and the value are both pure functions of the held event set, so identical held sets yield identical values; **fail-secure under partition**                                                              |

**A set-independent synthetic, not a digest over the tips.** The competing-branch set is
adversarially extensible (a subverted quorum can threshold-witness an Nth sealed sibling), so a
digest over it would be **flood-unstable**; a **set-independent synthetic** is flood-stable and
still triggers anti-entropy (a single-tip SAID ≠ a synthetic). Why set-independence is the right
trade — verdict-sufficiency, since burial by position kills all content branches, `disputed`
reincepts, and attribution walks the stored events — is
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison)'s.

**The verdict rides the synthetic (they converge).** A data-local walk reads `forked` (≤ 1 sealed
branch past the fork) or `disputed` (≥ 2 sealed), with the seal **derived** from the held events.
The synthetic **carries** that reading. Both the value and the verdict are pure functions of the
held event set — no arrival-order dependence: identical held sets yield an identical verdict **and**
an identical value, and a settled content fork drops both back to the canonical tip (verdict →
Active, value → the real tip SAID), in lockstep on every node. The **one** thing a set-independent
value gives up — forensic eviction-completeness needing the exact union of competing sealed events —
rides the independent receipt / event-gossip channel, best-effort, not the effective-SAID
anti-entropy. See
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison) for the
cross-primitive framing.

## Matrix 3: Race matrix

Concurrent sealed-vs-sealed races between federation peers — both submitting sealed events extending
the same parent `v_{d-1}` at serial `d` to different nodes — resolve through **first-seen witnessing
at position `d`** (the position gate is universal — sealed events included). The two are competing
**siblings at one position**: a selected witness signs the **first** it sees and **declines** the
second, so — absent collusion — only **one** reaches threshold (**accepted**) and the other stays
sub-threshold (**deferred-pending**). No node advances its seal to a fresh sealed event before that
event is threshold-witnessed (acceptance gating), so neither sibling "lands" pre-threshold; the
accepted sibling becomes the canonical tip on every node as receipts propagate, and the declined
party **re-issues** as an extension of the winner (stall-and-re-issue) → **Active**. A **Disputed**
reading requires **both** siblings to reach threshold at position `d` — two accepted seal-siblings,
a provable **witness double-sign** (`2·threshold − signers` colluding witnesses) — never an honest
race.

The race participants — any pairing across `{Rot, Wit, Trm}` — produce identical structural
outcomes. **Absent collusion (the honest race):**

- Each node holds the sibling it first receives as **deferred-pending** until threshold; the sibling
  honest witnesses first-saw reaches threshold and becomes the canonical tip on every node as
  receipts propagate.
- The competing sibling is **witness-declined** — permanently sub-threshold — retained as
  non-canonical evidence (keep-all-data), never admitted as a canonical extension. On the Trm'd side
  the treatment is identical — a Terminated chain is sealed at its `Trm`, so the seal-cap rejects a
  late sibling per
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).
- Every node converges on **Active** (or **Terminated**) at the accepted tip; the declined party
  **re-issues**. The witness beacon enumerates the competing branch SAIDs so a lagging holder
  fetches and walks the evidence.

**Under witness collusion (the residual):** both siblings reach threshold at position `d`, each node
holds two **accepted** sealed branches past the fork, and reads **Disputed** by a data-local walk —
the collusion is a provable double-sign, surfaced for forensics/eviction.

### Worked race: `Trm` versus `Rot` / `Trm` at `v_d`

Two parties submit concurrent sealed events extending `v_{d-1}` at the same serial `d` to different
nodes: party 1 submits `Trm` (clean retirement); party 2 submits another sealed event (e.g., `Rot`
or `Trm`) extending the same parent. Both are competing **siblings at position `d`**, so the
position gate first-seen-resolves them — only one reaches threshold absent collusion.

```
Pre-state (linear at v_{d-1}):

  Both nodes:  ... → v_{d-1}    (tip)

Concurrent submissions (neither is accepted until threshold-witnessed):

  Party 1 → Node A:    trm.previous     = v_{d-1}.said, trm.serial     = d
  Party 2 → Node B:    rot_alt.previous = v_{d-1}.said, rot_alt.serial = d

  Each node holds its first-receive deferred-pending; witnesses selected for
  position d first-seen ONE sibling and decline the other.

Honest resolution (no collusion) — say trm is first-seen:

  trm reaches threshold (accepted); rot_alt is witness-declined (sub-threshold).
  Node A: canonical tip = trm → Terminated at v_d.
  Node B: holds rot_alt deferred-pending; as receipts arrive it learns trm is
          accepted → converges: canonical tip = trm → Terminated. rot_alt is
          retained as non-canonical evidence (seal-cap rejects it: parent d-1 <
          seal d), never counted.
  Both nodes converge on Terminated; party 2 re-issues against trm. No dispute.

Collusion residual — both trm and rot_alt reach threshold at d:

  Each node holds two ACCEPTED sealed branches past v_{d-1}
    → data-local walk → disputed (a provable witness double-sign at d)
    → both nodes converge on the same verdict-recoupled synthetic.
```

Convergence in this scenario is **data-local**: the honest case converges on the **accepted** tip as
receipts propagate; the collusion case, once keep-all-data retention plus the witness beacon deliver
both **accepted** branches to each node, has every node read **Disputed** from the same retained
branches. A selected witness signs the **first** structurally-valid **sealed** sibling per chain
position and declines later ones (first-seen, like content); a node accepts up to **two witnessed**
sealed branches per position (two are the **Disputed** proof), and a witness-declined sibling is
deferred-pending; adjacent receipts at the same chain position carrying different `witnessed_said`
values are the evidence that a divergence exists there — the beacon **propagates** the branches, the
data-local walk **decides** the verdict. The prefix is disputed at-and-beyond the divergent serial;
events strictly below the last clean seal stay canonical. See
[§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery) and
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) _(forthcoming)_.

The seal-cap stays unconditional. Relaxing it to admit a competing event as a canonical extension at
a sealed serial would re-open the stale-authority killswitch surface that the locked-portion bound
was designed to close — so the competing branch is retained as evidence, never extended onto.

### The reserve-compromise reading

A `{Rot, Rot}` divergence is moreover a **proof of rotation-reserve compromise** — two valid
rotations reveal the one reserve preimage in force at `v_{d-1}`. The forging bar for a sealed event
is tier-2 (the reserve); once an adversary's rotation has landed on any federation node, no in-band
protocol recourse exists (the reserve defends the signing key, not the rotation key —
[`compromise.md`](compromise.md)). Any sealed-vs-sealed race resolves to the same data-local
**Disputed** reading. See
[§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery).

## Matrix 4: Recovery completeness

The recovery-side dual of matrices 1–3. Matrices 1–3 prove **detection** — every node reads the same
**Forked** / **Disputed** verdict from the data it holds. This matrix proves **recovery
completeness**: a landed burying seal-advancer is **final** (chain → Active) or proves the fork
**terminal** (Disputed → reincept), for every combination of {tier of the losing branch} ×
{delivered before or after the seal} — and every honest node converges on the same reading. The
merge-layer rules being proved sound are
[`merge.md` §How a burying seal-advancer resolves a content fork](merge.md#how-a-burying-seal-advancer-resolves-a-content-fork)
and
[`merge.md` §A burying seal-advancer is validated on arrival](merge.md#a-burying-seal-advancer-is-validated-on-arrival-not-auto-applied).

### Burial by position + ascent

On a **witnessed** chain, content forks are **prevented** below fork-cost — the witnessing floor
plus one-content-sibling-per-position witnessing makes two content siblings un-co-witnessable
([§Federation convergence](../../../../protocol-doctrine.md#federation-convergence)) — so the
population this matrix recovers is the **residual**: witness compromise at fork-cost, roster-delta
straddles (the partition/eclipse family's entrance), split-stalls (the burying seal-advancer is the
exit), and mixed `{sealed, content}` races. The machinery below is uniform — the same rules run
everywhere.

A divergence at a fork point `v_{d-1}`: distinct events extend it at `v_d`; one branch is retained,
the rest lose; the chain freezes. Recovery is a **burying seal-advancer** (a `Rot` / `Wit`) on the
winning branch — there is no repair event and no losing-branch commitment. It advances the seal, so
every losing **content** branch has its **first event locked below the seal** (the seal-cap) and
**everything built on it dead on ascent** — **deadness ascends: an event whose parent is dead is
dead**. So a losing branch a lagging node **grows after the burial** is dead on ascent — no
follow-up event, growth-proof. Either way the loser rides the **forked chain** — a **bounded**
region: each dead **lineage** extends at most **64 events past the last seal** (the seal-advance
cap; a deeper event needs a seal-advancer, which on this dead branch is itself **dead on ascent** —
dropped), and its **breadth** is bounded by **retention** (nodes keep **≥ 2 competing events per
position** as evidence and drop the rest), with the **one-content-sibling witnessing rule** on top
(a witness signs the first structurally-valid content sibling at a position and declines later ones;
a witness signs one sealed sibling per position too (first-seen); a node accepts up to **two
witnessed** sealed branches per position — two prove **Disputed**). Dead events are **witnessed and
propagated** yet **never canonical**; an adversary can _author_ extra siblings, but they are
droppable — never making the retained fork unbounded (a query-DoS surface only).

### The completeness matrix

Rows = {tier of the losing branch} × {delivery timing}. Cell = reading + closing rule. (The
cross-layer rows — a SEL event on a dead owner-IEL anchor; a SEL fork riding an IEL fork — land with
the `sel/` + `iel/` anchor-validation doctrine, forward-referenced below.)

| losing branch                                                                                   | reading                                                                                                      | closes with                                                                                                                                                                                                                                                |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **content**, buried below the seal                                                              | first event below the seal, subtree dead on ascent → **Active** on the winning chain                         | seal-cap (first event) + deadness-ascends (growth); the seal-cap bounds each dead lineage's depth (≤ 64 past the seal)                                                                                                                                     |
| **content**, branch **grows** after the burial (lagging node)                                   | grown events dead **on ascent** — no follow-up event → **Active**                                            | condemnation is over the subtree, not a tip; growth past depth-64 needs a seal-advancer, itself dead on ascent → dropped                                                                                                                                   |
| **content**, held when the burying seal-advancer arrives                                        | burial **accepted**, the branch drops below the advanced seal → inert → **Active**                           | an under-covering burial is accepted; the branch inerts rather than freezing the chain                                                                                                                                                                     |
| **sealed** (non-content) — a burial attempted against it, or a 2nd one present at the last seal | ≥ 2 **witnessed** sealed at the last seal → **Disputed** → reincept                                          | a sealed branch at the last seal is never buried; two **witnessed** sealed branches read **Disputed** (needs a provable witness double-sign); a **below-seal** sealed straggler is **dropped** (inert, backdate-safe — it does not retreat the clean seal) |
| **sealed** (non-content) — a **lone unretained** branch, no burial                              | one sealed branch → **Forked**-frozen (recoverable only by its author; reincept is the operational exit)     | invariant 4 (≥ 2 sealed is the **Disputed** threshold; one is **Forked**) — _not_ **Disputed**                                                                                                                                                             |
| **≥ 2 accepted sealed branches**                                                                | **Disputed** → reincept                                                                                      | invariant 4; [§Matrix 3](#matrix-3-race-matrix)                                                                                                                                                                                                            |
| **`{Trm, content}` terminal tip** (no burial)                                                   | `Trm` wins on tier-rank, content buried non-canonical → **Terminated**; a late sealed sibling → **Disputed** | tier-rank, no burial authored; the after-seal sealed asymmetry                                                                                                                                                                                             |

### Safety — the guards

- **No buried rotation.** A would-be-buried subtree is walked; a **witnessed** sealed event in it
  means ≥ 2 witnessed sealed branches past the fork → **Disputed**, not buried (validated, not
  trusted). So burial can never dead-mark a witnessed rotation to un-rotate it. The closer,
  detectable by either walk (spine or flat): every sealed KEL event is a **seal-advancer**, so a
  **witnessed** competing seal at the last seal is a **spine fork** → **Disputed** (a below-seal or
  witness-declined straggler is dropped / deferred, not counted).
- **No stale-authority revival.** Burial reaches no _live_ state — it **marks a subtree dead** (by
  position + ascent), never extends or revives an event. There is **no below-seal write operation**,
  so the seal-cap stays unconditional.
- **No self-burial.** A burying seal-advancer that siblings its own retained chain (its `previous`
  is known from the walkback) is rejected — a node buries only competing branches, never the branch
  it keeps.
- **Bounded fork (depth _and_ breadth).** **Depth** ≤ 64 events past the last seal per lineage (the
  seal-advance cap — a deeper event must author a seal-advancer, sealed → **Disputed**). **Breadth**
  is bounded by **retention**: nodes keep ≥ 2 competing events per position as evidence and drop the
  rest ("two prove the fork, then stop"), so the _queryable_ set is bounded and there is no query
  DoS. The **one-content-sibling witnessing rule** is the _kind-aware layer_ on top: a witness signs
  the **first** structurally-valid _content_ sibling at a position and **declines every later one**
  — while a witness signs **one sealed sibling per position** too (first-seen); a node accepts up to
  **two witnessed** sealed branches per position (two are the **Disputed** proof — competing seals
  form a spine fork; a witness-declined sibling is deferred-pending and droppable). The **single
  burying seal-advancer** on a content-only divergence is simply the first sealed sibling at that
  position (a _second_, competing seal-advancer forms `{Rot, Rot}` — two **witnessed** →
  **Disputed** via collusion, else the second is first-seen-declined; at most one buries a
  content-only divergence). With the witnessing floor this bounds co-witnessed content breadth to ≤
  1 absent fork-cost byzantine witnesses; arrival order decides only _which_ content sibling is the
  witnessed one — the bound rests on **retention + kind-awareness**, arrival-independent. A
  signing-key (tier-1) re-forker can _author_ more content siblings, but they sit beyond the
  retained ≥ 2 → droppable + declined. Every dead event is non-canonical and never flips a reading.
  A **sealed** event forged on a **dead** branch is itself **dead on ascent** — you can't seal a
  buried chain: honest witnesses, having accepted the winner at the fork, decline it, so it never
  reaches threshold and is **dropped** (inert), never `Disputed`. The depth-cap still bounds the
  dead lineage (its would-be seal is dropped, so it cannot grow past the cap into the retained set).
  The only terminal-compromise case is a **witnessed** competing seal **at the last (live) seal** —
  reachable solely by witness collusion (the no-buried-rotation guard, below) — not a straggler on a
  dead branch.

### Convergence

Under eventual beacon delivery and `< threshold` byzantine, every honest node's known set converges
to the true competing set. Then:

- **All-content** → every node reads the winning chain as canonical; the losing branches inert by
  the seal-cap (their growth dead on ascent); the effective SAID is the real winning tip on every
  node. **Converges to Active.** No follow-up burial, no reincept.
- **One sealed branch, kept by its author** → Active once the culprit's minting capability is
  neutralized (the recovery `Rot` rotates it out — vacuous for a benign fork) and beacon-confirmed
  (barring eclipse). A non-author's attempt to bury the author's **witnessed** sealed branch is
  **rejected (the no-buried-rotation guard); the competing seal is witnessed at its own position,
  its burial-effect void, so two witnessed sealed branches → Disputed** — retain-and-count is the
  convergent semantics for **witnessed** branches (a witness-declined or below-seal straggler, by
  contrast, is dropped, not counted — backdate-safe). So a burial against a fork that holds a
  **witnessed** sealed branch at the last seal **permanently terminalizes the prefix** →
  **Disputed** — the fail-secure outcome of a witnessed sealed event landing into a contested
  window.
- **≥ 2 witnessed sealed at the last seal** → **Disputed** everywhere (a node that holds two
  branches **each witnessed at threshold** reads it directly; a node holding only receipts fetches
  the branches first; a **below-seal** sealed straggler is dropped, not counted — backdate-safe);
  the effective SAID is the **verdict-recoupled synthetic** (all nodes converge on it once the
  branches propagate).

### Termination

The forked chain is **depth-capped at 64 past the last seal, per lineage** — that is the bound, not
a count of recoveries. One burying seal-advancer closes the whole current content fork (every losing
branch below the seal, growth dead on ascent — growth-proof within the depth-cap); the recovery
`Rot`'s key rotation then closes the culprit's ability to mint a **new** fork (on an IEL, an `Evl`
`cut` plays this role — an IEL burial rotates no identity key, so a culprit is neutralized by
eviction). So termination is qualitative but strict: each fork a sustained adversarial re-forker
mints costs it one bounded fork window, and once the neutralizing event — the rotation, or the cut —
propagates, it can mint no more; a benign gossip-lag terminates as soon as its node catches up.
Content-rail serialization is an **operator precondition** of the benign bound — absent it, honest
content can self-cascade (a liveness cost, not a safety one); sealing serialization is a liveness
discipline too — an honest double-seal is first-seen-declined, so two honest sealers
stall-and-re-issue rather than brick the `{Evl, Evl}` case at the IEL (only collusion yields two
accepted). On a **witnessed** chain the witnessing floor narrows even the self-cascade to
stall-and-re-issue — a competing content sibling never goes live — so the discipline is a
**liveness** concern (every chain is federation-witnessed; the residual safety concern is only a
witness compromise).

### Residuals (stated, fail-secure)

- **Eclipse / unwitnessed-branch residual:** detection is eventual; a reader eclipsed from a branch
  sees the true reading later. Sealed-completeness fails secure in that window. Pre-existing — the
  detection residual, not a recovery-specific one.
- **Historical rotation-reserve compromise — prevented, not a residual:** an old rotation reserve
  **cannot** flip a buried position. A below-seal sealed event is first-seen-declined and
  seal-cap-rejected → **dropped**, inert (it does not retreat the clean seal — the backdate
  defense). The one reachable residual is a **live-tip** compromise: forging a second **witnessed**
  seal at the current last seal needs the live signing key **plus** a colluding witness quorum
  (detectable, recoverable — reincept + out of band), never a backdated historical mint.

The cross-layer (SEL ↔ owner IEL) behavior is the SEL primitive's own. A SEL is its **own witnessed
chain** — fork-prevention is the SEL's first-seen at its own position, so an owner-IEL anchor cannot
prevent a SEL fork (an earlier reading, that a valid SEL fork implies an IEL fork beneath it, is
retired). The owner IEL's cross-layer contribution is **severance**: a buried owner-IEL branch
severs an anchored SEL — dead **and** un-verifiable from the earliest dead anchor, a truncation with
no repair. The anchor's re-anchor-at-an-already-attributed-serial-is-inert rule survives only as a
defense-in-depth check, not as fork-prevention or a total-order. These are worked out in
[`../sel/reconciliation.md`](../sel/reconciliation.md); the KEL-level matrix above is self-contained
without them.

## Edge cases

### 1. A burying seal-advancer requires a divergence to bury; the chain stays recoverable

A `Rot` on a **linear** tip is a plain `Extended` (position 1) — it advances the seal and commits
the next reserve, so the chain stays recoverable afterward. A `Rot` that buries content (position 3,
or a Forked chain's winning branch) resolves the fork and commits a fresh `rotationHash`. The
genuinely-unrecoverable states are a **reserve compromise** (an adversary holds the reserve →
takeover) and a **Disputed** prefix (≥ 2 accepted sealed branches past a fork) — both → reincept,
neither produced by a clean recovery `Rot`.

### 2. Multiple competing content events injected across nodes

Different `Ixn` events at the same serial are submitted to different nodes (federation race or
threshold compromise — chain-indistinguishable). When gossip syncs, a fork forms. Only one extra
event is written per overlap (the fork event). A burying seal-advancer resolves it. All nodes
converge after it propagates via gossip.

```
Pre-state (linear at v_{d-1}, replicated to nodes A and B):

  Node A:  v_0 → ... → v_{d-1}    (tip)
  Node B:  v_0 → ... → v_{d-1}    (tip)

Different events submitted at v_d on each node:

  Node A receives ixn_a:  v_0 → ... → v_{d-1} → ixn_a @ v_d
  Node B receives ixn_b:  v_0 → ... → v_{d-1} → ixn_b @ v_d
```

Gossip propagates `ixn_a → B`, `ixn_b → A`. Each node's merge engine observes overlap at `v_d` and
writes the second event as the fork event (one extra canonical branch per overlap; a byte-identical
re-submission dedupes, a further distinct event is retained as non-canonical evidence):

```
  Both nodes:  v_0 → ... → v_{d-1} ─┬─ ixn_a @ v_d   (Forked — frozen)
                                    └─ ixn_b @ v_d
```

The owner submits a burying `Rot` on the branch it keeps (`ixn_a`) to any single node → the `Rot`
advances the seal past `ixn_b`, which drops below it (dead on ascent) → recovery propagates via
gossip → all nodes converge on the post-`Rot` linear state.

### 3. Local events buried by a competing recovery

If one reserve holder submits a burying `Rot` keeping another party's branch, that other party's
local store detects missing canonical events when it next attempts to flush. Detection works by
loading the last page of locally-held events, then walking backward checking each SAID against the
server until finding the boundary — everything after that boundary lies below the seal the `Rot`
advanced. The party then resubmits those missing events (plus any continuation work) as an atomic
batch.

```
Pre-state (divergent at v_d; local store holds branch A):

  Server:  v_0 → ... → v_{d-1} ─┬─ branch_A @ v_d → branch_A' @ v_{d+1}
                                └─ branch_B @ v_d

  Local:   v_0 → ... → v_{d-1} → branch_A → branch_A'   (local view)
```

A second reserve holder submits a burying `Rot` keeping `branch_B` (branch-tip-extending shape):
`rot_B` extends `branch_B` and advances the seal; `branch_A` / `branch_A'` now sit below the seal,
dead on ascent; `rot_B` lands at `v_{d+1}`.

```
  Server (post-recovery):  v_0 → ... → v_{d-1} → branch_B → rot_B
```

The local party detects via an existence-check on the server that `branch_A` / `branch_A'` are no
longer the canonical chain. **The pitfall to avoid: do NOT append a sealed event to the stale branch
— it accomplishes nothing.** Submitting a `Trm` that extends the party's local tip (`branch_A'` at
`v_{d+2}`, or `branch_A`) does not cleanly terminate — the `Trm` lands on a branch below `rot_B`'s
seal at `v_{d+1}`. The seal-cap (invariant 5) refuses it as a canonical extension, **and a
below-seal sealed event is dropped — the witness mirrors the seal-cap, so it never reaches
threshold; it is inert (backdate-safe), not a Disputed-flip.** So the stale `Trm` is simply wasted,
not a brick. Correct recourse: re-fetch the server state, confirm the canonical tip (`rot_B`), then
either submit `Trm` extending that tip cleanly or accept the server-side state without terminating —
never append a sealed event to a branch not confirmed canonical.

### 4. Post-recovery events synced to a node holding the buried branch

After recovery on node A, new events (e.g., `Ixn`) are appended. When synced to node B (which still
has the now-buried branch as its canonical chain), the overlap handler applies the burying
seal-advancer (the seal advances past B's branch) and resolves it synchronously in the merge
transaction.

```
Pre-sync state (post-recovery on A; buried branch still canonical on B):

  Node A:  v_0 → ... → v_{d-1} → branch_A @ v_d → rot → ixn_new
           (clean linear chain after rot buried branch_B below the seal)

  Node B:  v_0 → ... → v_{d-1} → branch_B @ v_d
           (still has the alternate branch as canonical; rot hasn't propagated)

Gossip propagates Node A's chain (including rot) to Node B. Node B's merge engine observes overlap at v_d (its branch_B vs incoming branch_A), sees the burying rot in the batch, advances the seal past branch_B, and buries it synchronously (dead on ascent).

  Node B (post-sync):  v_0 → ... → v_{d-1} → branch_A → rot → ixn_new
                       (matches Node A; branch_B in retained storage below the seal)

All nodes converge on the same effective SAID (tip event SAID).
```

### 5. Concurrent sealed race at `v_d` — data-local disputed reading

See [§Matrix 3](#matrix-3-race-matrix). Per-node, each chain keeps its own first-receive as the
canonical tip and retains the competing branch as evidence; every node reads **Disputed** by a
data-local walk over the two retained sealed branches. The witness beacon delivers a missing branch
to a one-branch holder. The seal-cap stays unconditional.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: kinds, fields, two-tier capability model,
  seal-advance cap.
- [`merge.md`](merge.md) — merge engine routing being proved sound.
- [`compromise.md`](compromise.md) — recovery doctrine: recovery attach shapes, two-tier compromise
  model, pre-seal verifiability.
- [`verification.md`](verification.md) — verifier walk.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#federation-convergence) —
  federation convergence (cross-primitive doctrine).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery; sealed-divergence terminality; keep-all-data retention.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) —
  seal-cap and locked-portion bound.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#effective-said-comparison) —
  effective-SAID comparison (cross-primitive).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the kind-scoped witnessing ladder, the witnessing floor, the beacon,
  divergent witness receipts.
