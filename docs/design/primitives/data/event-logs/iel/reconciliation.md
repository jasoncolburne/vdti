# IEL Reconciliation — Multi-Node Correctness Matrix

This doc is the **load-bearing correctness proof** for the IEL primitive. It exhaustively enumerates
every combination of (per-node chain state) × (submitted batch shape) × (cross-node gossip state) on
the IEL's **mixed chain** — tier-1 content alongside a tier-2 sealed spine — and demonstrates that
each case terminates correctly under the merge-layer routing rules and that all nodes converge on
the same effective SAID across the federation. Without this matrix the merge engine, the gossip
layer, and the federation-witnessing layer are not proven sound — they are designed against this
enumeration. Cross-node convergence as a doctrinal property is stated upstream at
[§Federation convergence](../../../../protocol-doctrine.md#federation-convergence); this doc is the
per-primitive proof, and it mirrors the KEL's
([`../kel/reconciliation.md`](../kel/reconciliation.md)), adding the content-versus-sealed routing
the mixed chain introduces.

For lifecycle prose (states, the seal and spine, locked-portion bound, page model), see
[`log.md`](log.md). For per-kind reference (kinds, the threshold vector, the anchor matrix),
[`events.md`](events.md). For the merge-layer routing rules being proved sound,
[`merge.md`](merge.md). For the verifier walk, [`verification.md`](verification.md).

## Proof structure

The proof composes four matrices:

1. **Local submissions matrix** — what every submission to every chain state produces on a single
   node, split by whether the submission is content or sealed. Demonstrates the routing rules are
   exhaustive and terminate correctly.
2. **Source → sink transfer matrix** — what gossip propagation between two nodes produces, for every
   combination of source and sink chain states. Demonstrates gossip-driven sync converges per-node
   states.
3. **Race matrix** — what concurrent sealed races produce across federation peers, including the
   federation IEL's always-sealed case. Demonstrates the seal-cap and locked-portion bound are sound
   under adversarial concurrency and that keep-all-data plus the beacon make the divergence readable
   **data-locally** on every node.
4. **Recovery-completeness matrix** — the recovery-side dual: is a landed burying seal **final**
   (chain → Active), or does it prove the fork **terminal** (Disputed → reincept)? For every
   combination of losing-branch tier and delivery timing, including the atomic `cut` `Evl` eviction.

All four depend on the same protocol-enforced invariants, stated next.

## Invariants

The cases below depend on these protocol-enforced invariants. They are stated structurally — the
safety claims hold _by construction_, not by observation.

1. **Seal-advance cap compliance.** Every IEL has a sealing event (`Evl` / `Ath` / `Rev` / `Dth` /
   `Wit`) at least every `(MINIMUM_PAGE_SIZE − 1)/2 = 64` content events per lineage. Surfaced by
   the verifier, enforced by the merge handler
   ([`events.md` §Seal-advance cap](events.md#seal-advance-cap)).
2. **Bounded divergence.** A fork can only form at-or-after the last seal — a competing **content**
   event below the seal is dead on arrival (never a live fork; a competing **sealed** event below
   the seal is _not_ inert — it is a spine fork that makes the chain **Disputed**), and one **at**
   the seal's own serial forms a live fork. Combined with invariant 1 the fork is bounded on both
   axes: **depth** — each content-fork lineage extends at most 64 events past the last seal (a
   member holding less than a rotation reserve can only author content participations, so a deeper
   lineage needs a sealing event — tier 2); **breadth** — nodes retain ≥ 2 competing events per
   position as evidence and drop the rest, with the one-content-sibling witnessing rule on top.
3. **Bounded operations.** `MINIMUM_PAGE_SIZE = 129 = 2·64 + 1`, sized so the canonical two-branch
   content fork anchored at the last seal — both lineages (≤ 64 each) plus the burying seal — fits
   one page, which a source → sink transfer of that shape needs (the sink holds neither branch).
4. **A sealed divergence is terminal; a content divergence is recoverable.** A sealing event (`Evl`
   / `Ath` / `Rev` / `Dth` / `Wit` / `Trm`) that would create or join a divergence does **not**
   extend the canonical chain — it is retained as non-canonical evidence rather than discarded. A
   fork with **at most one** sealed branch is **Forked** (recoverable): a burying seal on the
   winning branch buries the content loser by position + descent. A fork with **two or more** sealed
   branches past it is **Disputed** (reincept). Any verifier reads which by a data-local walk. A
   sealed branch is never buried — that would resurrect a retired sealing decision. See
   [§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery).
5. **Locked-portion bound is unconditional.** No event class is exempt from the seal-cap — not even
   a burying `Evl`: a clean canonical extension requires `event.parent.serial ≥ seal_serial`, so
   nothing ever extends the canonical chain from a parent in the locked portion, and stale-authority
   revival is structurally impossible. A parent strictly below the seal is inert — a content child
   is `Sealed`, a sealed child is retained and read `Disputed`. A sibling at the seal's own serial
   forms a **live fork** (Forked / Disputed), retained as evidence.
6. **Threshold anchoring; roster accumulation.** Every IEL event is authorized by a threshold of
   members' fresh KEL participations (kind-strict up), and the current roster is the **accumulation
   of every delta while walking** (a `cut` `Evl` also evicts) with the hard live-set cap of 32 —
   never "latest `Evl`". A rogue member KEL is **inert alone** (it cannot reach `t_use` /
   `t_govern`), so distrust is non-participation + an `Evl` eviction, forward-only.

These invariants make synchronous resolution, single-page recovery, and atomic batched submissions
feasible. The proof matrices below rely on invariants 4–6.

## IEL chain states (proof states)

The per-node enumeration covers every shape the merge rules can produce. A live fork is **two
distinct states**: **Forked** (≤ 1 sealed branch past it — recoverable) and **Disputed** (≥ 2 —
terminal), each a first-class state a verifier **derives** by a data-local walk.

| State          | Description                                                                                                                                                                      |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Empty**      | No events for this prefix on this node.                                                                                                                                          |
| **Active**     | Linear chain; the tip extends cleanly via `previous`.                                                                                                                            |
| **Forked**     | A live fork with **≤ 1 sealed branch** past it — recoverable; origination-frozen; resolved by a burying seal on the winning branch → Active.                                     |
| **Disputed**   | A live fork with **≥ 2 sealed branches** — a proof of quorum subversion, terminal. Nothing resolves it; the identity must reincept. Witnesses decline any extension → `Ignored`. |
| **Terminated** | A `Trm` is the permanent end (all the identity's SELs freeze). Not absorbing — a chain _from_ `Trm` → `Terminal`; a sealed sibling → `Disputed`; a content sibling → `Sealed`.   |

**Empty** is the pre-inception case, included for completeness; the four **live-chain** states are
Active / Forked / Disputed / Terminated (the state machine is four-state).

## Merge outcomes — the cell vocabulary

Every cell in Matrices 1–2 is a **transition** (the chain moved to or held a state) or a
**rejection** (nothing changed) — the `Result<MergeTransition, MergeRejection>` the merge engine
returns per submission ([`merge.md` §Merge outcomes](merge.md#merge-outcomes) is authoritative).

**Transitions** — `Extended` / `Recovered` both land **Active**; `Terminated`; `Forked` (≤ 1
sealed); `Disputed` (≥ 2 sealed, or a burial hitting a sealed branch). **Rejections** — `Sealed`
(inert below-seal parent), `Terminal` (a `Trm` admits no successor), `Invalid` (structurally
inapplicable — including a role-outside-allowlist, a `kills` on `Ixn`, a facet-wrong `Wit`),
`Ignored` (a well-formed event the witnesses decline).

## Matrix 1: Local submissions

What happens when a client submits an event to the merge engine on a single node. The outcome turns
on **where the new event sits** relative to the **tip** and the **last seal**, and on **whether it
is content or sealed**. For an **Active** chain, every valid submission is in exactly one of three
**attach-positions**, mutually exclusive:

1. **Extends the tip** — the new event continues the chain from the current tip.
2. **Adjacent to the last seal** — the new event sits at the seal's own serial, competing with the
   seal.
3. **On the run past the last seal** — the new event competes with a **content** event on the
   seal→tip run (content-only by definition).

A new event whose own serial is below the seal's lands in the locked portion → `Sealed` (a content
child) or reads `Disputed` (a sealed child), independent of attach-position. The attach-position,
not the chain state, carries this distinction — the state stays one of the four live-chain states.

### Position 1 — the new event extends the tip (trivial: linear)

| new event                             | outcome                            |
| ------------------------------------- | ---------------------------------- |
| `Ixn`                                 | `Extended`                         |
| `Evl` / `Ath` / `Rev` / `Dth` / `Wit` | `Extended` (the seal advances)     |
| `Trm`                                 | `Terminated`                       |
| `Icp` / `Fcp`                         | `Invalid` (a chain already exists) |

### Position 2 — adjacent to the last seal (competes with the seal)

| new event                             | outcome                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| `Ixn`                                 | `Forked` — the seal + one content sibling, a mixed race (one sealed)                |
| `Evl` / `Ath` / `Rev` / `Dth` / `Wit` | `Disputed` — a second sealed branch beside the seal (two sealed → quorum subverted) |
| `Trm`                                 | `Disputed` — a second sealed branch                                                 |
| `Icp` / `Fcp`                         | `Invalid`                                                                           |

### Position 3 — on the run past the last seal (competes with content)

| new event                             | outcome                                                                                                                                               |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Ixn`                                 | `Ignored` — a content sibling of a content event is declined by witnessing; the chain stays `Active`                                                  |
| `Evl` / `Ath` / `Rev` / `Dth` / `Wit` | `Recovered` — the seal buries the content run past its attach point; the content dies by descent → **Active**. Never `Disputed` — the run is content. |
| `Trm`                                 | `Terminated` — the content adjacent to and beyond the `Trm` is dead; the `Trm` is the permanent end                                                   |
| `Icp` / `Fcp`                         | `Invalid`                                                                                                                                             |

### The other states

- **Empty** — only `Icp` (user) / `Fcp` (federation) → `Extended`; every other kind → `Invalid`.
- **Forked** — origination-frozen; resolved by a burying seal on the winning branch (→ `Recovered`,
  Active) or a `Trm` on the winning tip (→ `Terminated`). A second sealed event joining the fork →
  `Disputed`. A content event → `Forked` (retained; a second content sibling at a position →
  `Ignored`).
- **Disputed** — terminal. Witnesses never witness an extension of a disputed chain, so a new
  submission is `Ignored`; a branch already witnessed before the dispute stays retained (it arrives
  via gossip). The only exit is reincept.
- **Terminated** — a submission chaining _from_ the `Trm` → `Terminal`; a sealed sibling beside or
  beyond → `Disputed`; a content sibling → `Sealed`.

### The sealed sub-split

The IEL's sealing kinds are not uniform, and the matrix cells above collapse them because the
**divergence** treatment is identical (all record-both, all sealed, all never buried). The finality
differs, and shows up only in Position 1 and on a Terminated chain:

- **`Evl` / `Ath` / `Rev` / `Dth` / `Wit`** are sealed **non-terminal** — a clean landing is
  `Extended` and the chain stays Active (a `Rev` / `Dth` seals a kill on a _target_, not the host
  IEL). A `{Rev, content}` at a fork is one sealed branch → `Forked`, recoverable; the `Rev` branch
  survives.
- **`Trm`** is sealed **terminal** — a clean landing is `Terminated`.
- Distinct **kills** at one position (`{Rev, Rev}`) are two sealed branches → `Disputed`; identical
  kills dedupe by SAID (idempotent). A busy issuer's two identical roster-less re-seal `Evl`s at one
  position likewise dedupe; a re-seal `Evl` versus a real `Evl` is `{Evl, Evl}` → `Disputed`.

### Batch submissions

- **`[..content.., Evl]`** — the winning-branch content plus the burying `Evl`. The retained branch
  (≤ 64) plus the `Evl` fits one page; the `Evl` buries the content loser by position + descent
  synchronously.
- **`[Evl(re-seal), Ixn]`** — auto-inserted by the builder when an `Ixn` would exceed the
  seal-advance cap (the roster-less re-seal).
- **`[Evl(cut), ..]`** — the atomic eviction: one sealing event buries the fork and evicts the
  divergence-causing member.
- **the federation `Fcp` plus the founder `Rot`s and receipts** — the federation genesis atomic
  batch (see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md)).

## Matrix 2: Source → sink transfer (gossip sync)

When a **source** node propagates an IEL to a **sink**, the transfer reads the source's chain state
and submits to the sink's merge engine. Each cell is the **merge outcome at the sink**.
Independently, a sink **retains** any competing branch it receives as non-canonical evidence, and
that retention, when it changes the sink's held-state, is what moves its effective SAID and drives
convergence.

"Active (winning)" means the sink holds the eventual winning branch; "Active (losing)" the eventual
buried branch. The protocol cannot distinguish the two from chain data alone.

| Source ↓ / Sink →              | Empty    | Active (winning) | Active (losing) | Forked                  | Terminated |
| ------------------------------ | -------- | ---------------- | --------------- | ----------------------- | ---------- |
| **Active**                     | Extended | Extended         | Forked          | Extended / Forked ᵈ     | Sealed     |
| **Recovered** (source burying) | Extended | Extended         | Recovered ᵈ     | Recovered / Disputed ᵈ  | Sealed     |
| **Forked** (unrecovered)       | Forked   | Forked           | Forked          | Extended ᵃ              | Sealed     |
| **Terminated**                 | Extended | Extended         | Terminated ᵇ    | Terminated / Disputed ᵈ | Extended ᶜ |

**Row note (no Disputed source).** A **Disputed** source (≥ 2 sealed branches) needs no separate
row: it transfers like a **Forked** source — its retained sealed branches propagate, and the sink
reads **Disputed** by sealed-count. **Terminated** gets its own row because it resolves by
tier-rank, not by sealed-count.

**Column note (no Disputed sink).** A **Disputed** sink is a terminal fixed point: every transfer
dedups or retains the incoming branches and leaves the reading **Disputed**; a new canonical
extension is `Ignored`.

**Guarded cells:**

- **ᵃ Forked → Forked** — both nodes already hold the fork; the transfer exchanges any competing
  branch each lacks and each retains it (keep-all-data — this branch ingestion, not a canonical
  merge outcome, is what moves the digest), so they converge. No new canonical state.
- **ᵇ Terminated → Active (losing)** — the incoming `Trm` and the sink's content branch form a
  divergence; the `Trm` wins on tier-rank and the content buries dead → the sink reads
  **Terminated**.
- **ᶜ Terminated → Terminated** — both already hold the `Trm` (dedup); already converged.
- **ᵈ A burying source → Forked / Active (losing)** — when the source's run carries a **sealing
  event on the winning branch** (an Active source that sealed past the fork, or a `Trm`),
  transferring it to a sink holding the losing branch **buries** the sink's competing **content**
  loser: the sink re-reads **Active** (`Extended` / `Recovered`) or **Terminated** (a `Trm`). A
  content-only source lands as evidence and the sink stays **Forked**. A **sealed** loser makes the
  fork **Disputed** (never buried).

### Transfer ordering

For divergent source chains the sender reorders events so the chain reconstructs the same way at the
sink. A recovered source is a clean linear chain (the content loser is below the seal). Only
unrecovered divergent cases reach the partitioning path:

- **Unrecovered content fork (`Ixn`-`Ixn`)** — the longer chain first as non-divergent appends; only
  the fork event from the shorter chain is sent, routed through the overlap path → Forked.
- **A retained sealed branch** (a `{Evl, Evl}` or a burying seal the guard rejected, counted as the
  second sealed branch of a Disputed fork) is evidence and **must** propagate — dropping it would
  split the reading across nodes.

### Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each prefix — the value exchanged during
anti-entropy:

- **A single confirmed tip** (a linear chain, or a fork settled below the seal — Active / Recovered
  / Terminated) → **that tip's real SAID** (a terminated chain's is its `Trm`).
- **No single tip** (an unresolved fork — a live content fork, or ≥ 1 sealed branch past it) → a
  **type-tagged synthetic recoupled to the verdict** (`forked` / `disputed`), qualified by
  **prefix + position**, **structurally distinct from any real SAID**, and **not** a digest over the
  competing tips.

| State                  | Effective SAID (the value)                                                                                                                    | Converges?                                                                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active / Recovered** | the canonical **tip event SAID**                                                                                                              | ✓ (identical chains after gossip)                                                                                                            |
| **Terminated**         | the `Trm`'s SAID — the canonical **tip** (dead events at higher serials don't move it)                                                        | ✓ where the `Trm` landed uncontested; a competing sealed event racing it → both nodes hold both branches → **Disputed** data-locally         |
| **Forked / Disputed**  | a **type-tagged synthetic** recoupled to the verdict (`forked` / `disputed`), qualified by prefix + position — **not** a digest over the tips | ✓ **once the branches propagate** — the verdict and the value are both pure functions of the held event set; **fail-secure under partition** |

**The effective-SAID value converges — a set-independent synthetic.** For Forked / Disputed the
value is a **type-tagged synthetic** recoupled to the verdict, **not** a digest over the competing
tips (that set is adversarially extensible → flood-unstable; the design rationale for choosing a
set-independent synthetic is
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison)'s). What
this proof relies on: the verdict rides the synthetic — a data-local walk reads `forked` (≤ 1
sealed) or `disputed` (≥ 2 sealed), the seal derived from the held events — and both value and
verdict are **pure functions of the held event set**, in lockstep on every node.

## Matrix 3: Race matrix

Concurrent sealed-versus-sealed races between federation peers — both submitting sealing events
extending the same parent `v_{d-1}` to different nodes — uniformly resolve via the same structural
shape: each event lands as a clean linear extension on its submitting node and advances the local
seal; gossip then delivers each to the other node, where the seal-cap rejects it as a canonical
extension (`parent_serial < seal_serial`) but retains it as non-canonical evidence (keep-all-data).
Each node ends up holding both branches and reads **Disputed** by a data-local walk over the two
retained sealed branches.

The race participants — any pairing across the sealing kinds `{Evl, Ath, Rev, Dth, Wit, Trm}` —
produce identical structural outcomes per-node: each node keeps its locally-landed first-receive as
its canonical tip; the gossip-arriving competing event is retained but not admitted; each node reads
**Disputed** by the data-local walk. The witness beacon enumerates the competing branch SAIDs so a
one-branch holder fetches the rest (a selected witness signs up to two distinct sealed siblings per
position — two both-witnessed siblings are the `Disputed` proof).

### The `{Evl, Evl}` reading and its network-split origin

A `{Evl, Evl}` divergence is a **proof of quorum subversion** — two distinct sealed decisions at one
position mean either a compromised quorum or a network split during which **both halves sealed**.
The everyday split case — one half seals while the other issues content — is **recoverable**
(`{Evl, content}` → the `Evl` survives and its seal buries the content); the identity only bricks
when both halves sealed. The residual is handled **operationally**: one designated sealing submitter
so two sealing events never race, and pausing sealing while a split is suspected. A `{Evl, Evl}`
brick recovers by reincept, made detectable on heal by witnessing. The operator playbook lands in
[`../../../../operations/sealing-serialization.md`](../../../../operations/sealing-serialization.md)
(forthcoming); the doctrine — that sealed is record-both and a second sealed branch is terminal — is
the chain's.

### The federation IEL — the always-sealed schism

A **federation** IEL authors **no content** (`Fcp` / `Wit` / `Trm` only), so **every** federation
conflict is a sealed-versus-sealed race → **Disputed → terminal → reincept** (a global federation
rebind). There is no `{sealed, content}` recoverable case on the federation chain — it is the pure
case of this matrix. A `{Wit, Wit}` federation race reads `disputed` data-locally exactly as
`{Evl, Evl}` does on a user chain; the federation's own witnesses witness each other exclude-self,
and the beacon propagates the competing branches. The federation-witnessing mechanics
(self-attestation, the clock, the recoverability cap) are federation doctrine —
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

The seal-cap stays **unconditional**: relaxing it to admit a competing event as a canonical
extension at a sealed serial would re-open the stale-authority killswitch surface the locked-portion
bound closes — so the competing branch is retained as evidence, never extended onto, and the
divergence resolves data-locally.

## Matrix 4: Recovery completeness

The recovery-side dual of matrices 1–3. Matrices 1–3 prove **detection** — every node reads the same
Forked / Disputed verdict. This matrix proves **recovery completeness**: a landed burying seal is
**final** (chain → Active) or proves the fork **terminal** (Disputed → reincept), for every
combination of {tier of the losing branch} × {delivered before or after the seal}.

### Burial by position + descent

On a **witnessed** IEL, content forks are **prevented** below fork-cost (the position gate plus
one-content-sibling-per-position witnessing, at both the user IEL's own position and, cross-layer,
its SELs), so the population this matrix recovers is the **residual**: witness compromise at
fork-cost, roster-delta straddles, split-stalls (the burying seal is the exit), and mixed
`{sealed, content}` races. The machinery is uniform.

Recovery is a **burying seal** on the winning branch — any non-terminal seal-advancer, typically an
`Evl` or the `cut` `Evl` when it also evicts — with no repair event and no losing-branch commitment.
It advances the seal, so every losing **content** branch has its first event locked below the seal
and everything built on it dead by descent (**deadness descends: an event whose parent is dead is
dead**) — so a losing branch a lagging node grows after the burial is dead by descent, growth-proof.
The loser rides the **forked chain**, a bounded region: each dead lineage extends at most 64 events
past the last seal (a deeper event needs a sealing event, sealed → Disputed), and its breadth is
bounded by retention (≥ 2 competing events per position) with the one-content-sibling witnessing
rule on top.

### The completeness matrix

Rows = {tier of the losing branch} × {delivery timing}. Cell = reading + closing rule.

| losing branch                                                 | reading                                                                                                                 | closes with                                                                                                                                                    |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **content**, buried below the seal                            | first event below the seal, subtree dead by descent → **Active** on the winning chain                                   | seal-cap (first event) + deadness-descends (growth); the seal-cap bounds each dead lineage's depth (≤ 64 past the seal)                                        |
| **content**, branch **grows** after the burial (lagging node) | grown events dead **by descent** — no follow-up event → **Active**                                                      | condemnation is over the subtree, not a tip; growth past depth-64 needs a sealing event → sealed → **Disputed**                                                |
| **content**, held when the burying seal arrives               | burial **accepted**, the branch drops below the advanced seal → inert → **Active**                                      | an under-covering burial is accepted; the branch inerts rather than freezing the chain                                                                         |
| **sealed** — a burial attempted against it, or a 2nd present  | ≥ 2 sealed → **Disputed** → reincept                                                                                    | a sealed branch is never buried; the burying event is retained and counted; a node holding ≥ 2 sealed branches reads Disputed directly (threshold-independent) |
| **sealed** — a **lone unretained** branch, no burial          | one sealed branch → **Forked**-frozen (recoverable only by its author's burying seal; reincept is the operational exit) | invariant 4 (≥ 2 sealed is the Disputed threshold; one is Forked) — _not_ Disputed                                                                             |
| **≥ 2 sealed branches**                                       | **Disputed** → reincept                                                                                                 | invariant 4; [§Matrix 3](#matrix-3-race-matrix)                                                                                                                |
| **`{Trm, content}` terminal tip** (no burial)                 | `Trm` wins on tier-rank, content buried non-canonical → **Terminated**; a late sealed sibling → **Disputed**            | tier-rank, no burial authored; the after-seal sealed asymmetry                                                                                                 |

### Eviction is atomic — the `cut` `Evl`

Evicting a compromised or divergence-causing member is a **`cut` `Evl`** — one sealing event buries
the fork **and** evicts, in a single event. The atomicity is load-bearing for completeness: were it
two events, the still-rostered member would race fresh content at the resolved tip and re-fork it,
so the fork would not close. The `cut` `Evl` makes it atomic by construction — the member leaves the
roster the instant the fork resolves. The `cut` is priced the **outgoing** `t_govern` (so an `Evl`
cannot lower its own gate then cut), and the post-cut roster is re-checked against the bounds (a
stranding / hostage cut is rejected). On an IEL, the `cut` plays the role the KEL recovery `Rot`'s
key rotation plays — an IEL burial rotates no identity key, so a culprit is neutralized by
**eviction**, not by rotation.

### Safety — the guards

- **No buried sealed event.** A would-be-buried subtree is walked; a **sealed** event in it means ≥
  2 sealed branches → **Disputed**, not buried (validated, not trusted). The walk-independent
  closer: every sealed IEL event is a seal-advancer → a competing seal → a spine fork →
  **Disputed**.
- **No stale-authority revival.** Burial marks a subtree dead (by position + descent), never extends
  or revives an event; there is no below-seal write operation, so the seal-cap stays unconditional.
- **No self-burial.** A burying seal that siblings its own retained chain is rejected — a node
  buries only competing branches, never the branch it keeps.
- **Bounded fork.** Depth ≤ 64 events past the last seal per lineage; breadth bounded by retention
  (≥ 2 per position) plus the one-content-sibling witnessing rule (a witness signs the first content
  sibling and declines later ones; sealed siblings up to two per position). A signing-key (tier-1)
  re-forker can author more content siblings, but they sit beyond the retained ≥ 2 → droppable +
  declined.

### Convergence and termination

Under eventual beacon delivery and `< threshold` byzantine, every honest node's known set converges
to the true competing set. **All-content** → every node reads the winning chain as canonical, the
effective SAID the real winning tip; converges to Active. **One sealed branch** → Active once the
culprit is neutralized (the `cut` `Evl` evicts it) and beacon-confirmed; a non-author's attempt to
bury the sealed branch is rejected, retained, and counted — retain-and-count is the only convergent
semantics — so any burial against a fork that holds a sealed branch permanently terminalizes the
prefix → **Disputed**. **≥ 2 sealed** → **Disputed** everywhere; the effective SAID is the
verdict-recoupled synthetic.

The forked chain is depth-capped at 64 past the last seal per lineage — one burying seal closes the
whole current content fork, and the `cut` `Evl` then closes the culprit's ability to re-fork (by
eviction). **Sealing serialization** (one designated submitter) backs the `{Evl, Evl}` terminal
cases; **content-rail serialization** is a liveness precondition of the benign bound. On a witnessed
IEL the position gate narrows even the self-cascade to stall-and-re-issue — a competing content
sibling never goes live — so the discipline is a liveness concern (every chain is
federation-witnessed; the residual safety concern is only a witness compromise).

### Cross-layer completeness (forward-referenced)

The cross-layer rows — a SEL event on a dead owner-IEL anchor is dead (**cross-layer
deadness-descends** across the IEL → SEL anchor edge), **anchor-monotonicity** (a linear IEL
totally-orders each SEL it anchors, so a SEL never forks under a linear IEL), and the theorem that a
valid SEL fork implies an IEL fork beneath it — land with the `sel/` anchor-validation doctrine
(forthcoming). The IEL-level matrix above is self-contained without them; the IEL states the anchor
edge from its side, the SEL-side detail lands with [`../sel/`](../sel/).

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: kinds, the threshold vector, the anchor matrix,
  seal-advance cap.
- [`merge.md`](merge.md) — merge engine routing being proved sound.
- [`verification.md`](verification.md) — verifier walk.
- [`../kel/reconciliation.md`](../kel/reconciliation.md) — the KEL correctness matrix this mirrors.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#federation-convergence) —
  federation convergence;
  [§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery);
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded);
  [§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor, the beacon, the federation-IEL schism mechanics.
- [`../../../../operations/sealing-serialization.md`](../../../../operations/sealing-serialization.md)
  — the sealing-serialization operator playbook (forthcoming).
