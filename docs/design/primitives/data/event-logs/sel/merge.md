# SEL Merge — Handler Rules

The SEL merge layer integrates submitted events into the existing chain. It is the protocol's
enforcement surface for the SEL's **own witnessed first-seen**, the seal-cap, and the **severance**
a dead owner-IEL anchor causes — routing a **mixed chain**: tier-1 content (`Ixn` and the floor
`Pin`) alongside three tier-2 seal-advancers (`Gnt` / `Trm` / `Sea`). The verifier produces a trust
signal on a verification token; the merge layer composes that signal with chain-state-dependent
routing to admit or reject batches.

Two things distinguish SEL merge from IEL merge. First, the SEL is its **own** witnessed chain — a
linear owner IEL **cannot prevent** a SEL fork (the IEL is blind to it, so an owner can author two
competing SEL events), and the SEL's own first-seen at its `(prefix, serial)` is what **closes** the
equivocation — two accepted sealed branches then require witness collusion
([`log.md` §The SEL is its own witnessed chain](log.md#the-sel-is-its-own-witnessed-chain)). Second,
a SEL has a **second, inherited** state input: when the owner IEL buries a branch that a SEL event
anchored, the SEL is **severed** there — dead and un-verifiable from that point, with no repair.

This doc states the merge-layer routing: the content-versus-sealed split, the merge outcomes, the
routing order, how a burying seal-advancer resolves a content fork, and severance. For per-kind
event rules, see [`events.md`](events.md); for the verifier walk,
[`verification.md`](verification.md); for the chain primitive, [`log.md`](log.md); for the
cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## Single entry point

`merge_events` is the single entry point for all write paths into a SEL — direct submissions, gossip
propagation, and federation sync. It runs under a database advisory lock for the duration of
verification and write, so time-of-check-to-time-of-use is eliminated structurally: the verifier
reads under the same lock the merge handler will use to write
([§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).

The merge handler returns either a **merge transition** (carrying the outcome, plus the resulting
state and new tip SAID) or a **merge rejection**, the same `Result<MergeTransition, MergeRejection>`
vocabulary the KEL and IEL use.

## The content-versus-sealed split

The SEL is a mixed chain, and the one test that routes divergence is: **could a single
already-revealed secret author a competing sealed sibling?** The SEL answers it with its **own**
witnessing, at its own position (a SEL event still rides its owner-IEL anchor for authorization, so
acceptance also requires the owner to have authorized it):

- **Content (`Ixn` / `Pin`) → first-seen.** A selected witness takes the first content event at a
  position and declines the copies; with the witnessing floor, two content siblings cannot both
  reach threshold, so a content fork is **prevented, not detected**. The residual — a witness
  compromise that owns the whole quorum intersection — reads Forked (fail-secure) and is resolved by
  a burying seal-advancer.
- **Sealed (`Gnt` / `Trm` / `Sea`) → first-seen and retained for detection.** A witness signs the
  first sealed sibling and declines later ones, so a threshold chain cannot be forked by one stolen
  reserve, and a **second accepted sealed branch** is proof the witnesses colluded, surfaced loudly.
  Two accepted sealed branches → **Disputed → re-incept**; a sealed branch beside content is
  **recoverable** (the sealed branch survives and the content buries). A witness-declined sealed
  sibling is held pending, forcing nothing.

The witnessing mechanics — the floor, first-seen-per-position, the beacon — are the federation's
([`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md));
this doc states the chain-scoped routing that composes with them.

## Merge outcomes

A merge returns one of two things — a **`MergeTransition`** on success (what the batch did to the
chain, named by the resulting state) or a **`MergeRejection`** when the batch changes nothing.

**Transitions** — each is named for its action or the state the chain is in after the batch lands
(`Extended` and `Recovered` both land **Active**).

| Transition     | Verdict                                                                                                                           | Triggering condition                                                                                                                      |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Extended**   | Linear extension → **Active**; content re-pins and does not advance the seal, a seal-advancer does.                               | Events chain cleanly from the current tip (or from inception on an Empty chain).                                                          |
| **Recovered**  | A burying seal-advancer resolved a content fork → **Active**: it extends the winning branch and advances the seal past the loser. | A `Gnt` / `Trm` / `Sea` extends a fork's winning branch (or buries a run past its attach point) — the content loser drops below the seal. |
| **Terminated** | A `Trm` admitted → **Terminated** (the SEL is retired).                                                                           | A `Trm` lands as a linear extension, or buries a content loser below its own seal.                                                        |
| **Forked**     | A **recoverable** content fork → the chain is **Forked**, origination frozen.                                                     | A content event forks at a serial (a witness compromise), or a content event lands on an already-forked chain.                            |
| **Disputed**   | **Two or more accepted sealed branches** → **Disputed** (terminal; the owner re-incepts).                                         | A second accepted sealed branch joins a fork, or a seal-advancer would bury a competing sealed branch.                                    |

**Rejections** — nothing lands; the chain is unchanged.

| Rejection    | Verdict                                                             | Triggering condition                                                                                                                                                                               |
| ------------ | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Severed**  | The anchoring owner-IEL event is dead → the event is un-verifiable. | Inherited owner-IEL deadness (§Severance): the SEL event was anchored on an owner-IEL branch the IEL has since buried; it and everything after it are dead and un-verifiable, not admitted.        |
| **Sealed**   | Parent sits below the seal and the event is inert — not admitted.   | An inert below-seal parent (a stale tip-view, or a dead-on-arrival content sibling behind an advanced seal).                                                                                       |
| **Terminal** | The tip is a `Trm`, which admits no successor.                      | A submission chaining _from_ a `Trm` (parent kind `Trm`).                                                                                                                                          |
| **Invalid**  | Structurally inapplicable to the chain state.                       | Structural-validation failure — inception on a non-empty chain, a non-inception on an Empty one, a role outside the kind's allowlist, a manifest on an `Icp` / `Pin` / `Sea`, a wrong-kind anchor. |
| **Ignored**  | A well-formed event the witnesses decline.                          | Fork prevention — a second content sibling, or a second sealed sibling, at a position; or a new event on a Disputed / Terminated chain (barring a partition).                                      |

A structurally-valid submission not yet at threshold is held **pending** — retained and gossiped for
witnessing, not advancing the tip or seal, not counted toward a verdict — and re-enters routing once
accepted, or becomes `Ignored` if declined as a later sibling. No node advances to a sub-threshold
event, its own fresh submission included.

## Routing order

The merge handler routes a submitted batch through these rule scopes in **structural order**, chosen
so adversarial-input diagnostics correctly name the structural cause-of-rejection.

### 1. Structural validation

Per-kind field rules (per the [event-shape reference](../event-shape.md#sel)), SAID integrity,
prefix consistency, chain-linkage continuity, and the **manifest role allowlist read kind-first**.
Any failure here is a structural error; the submission is `Invalid` regardless of chain state. In
particular:

- SAID recomputation matches the declared SAID; at inception, the prefix recomputes from the
  canonical bytes (the populated `owner` / `topic` / `data`, plus `content: true` on a content SEL
  and `lineage` on a re-establishable value lookup) with `said` / `prefix` set to the placeholder.
- Per-kind required / forbidden field presence — the `Icp` carries no `pin` / `manifest`, the `Pin`
  carries only the down-`pin` (no manifest, at any serial), an **`Ixn`'s manifest is required** (≥ 1
  `payload` SAD — a manifest-less `Ixn` is malformed; a pure re-pin is a `Pin`), `previousSeal` is
  present on `Gnt` / `Trm` / `Sea` and forbidden on `Icp` / `Ixn` / `Pin`, and the manifest role
  vocabulary is enforced (a `payload` role only on `Ixn`, a `grant` role only on `Gnt`).
- **Kind-schema predecessor rule.** No kind admits a `Trm` parent. A submission whose parent's kind
  is `Trm` is rejected with `Terminal`.
- **Re-anchor defense-in-depth.** An owner-IEL anchor naming a SEL event at an
  **already-attributed** SEL serial is malformed → the SEL event is inert (the carrying owner-IEL
  event stays valid). Fork-prevention itself is the SEL's own witnessing, not this rule; the check
  survives as a lightweight structural guard for a node validating without full witnessing state.

### 2. Owner-IEL deadness — severance

Before routing a submission against the SEL's own state, resolve its **anchoring owner-IEL event**.
If that event sits on a **dead** owner-IEL branch — one the owner IEL has buried — the SEL is
**severed** at the earliest such anchor: the anchored event and everything after it are dead and
un-verifiable, so the submission is `Severed` and nothing lands past the sever point (§Severance).
Deadness comes first: a SEL event on a dead anchor is never routed as a live fork or bury.

### 3. Seal-cap

The submitted event's parent must sit at-or-after the last seal-advancer
(`parent_serial ≥ seal_serial`). A submission whose parent is in the locked portion and would change
nothing is rejected `Sealed`; one at the seal's own serial resolves by tier instead — a content
sibling is buried → Active, a second accepted sealed sibling → `Disputed` (retained evidence). The
seal-cap is **unconditional**: every event class is subject to it, including a burying seal-advancer
whose `previous` targets the locked portion.

### 4. Fork-detect

The event's `(parent_said, serial)` is checked against the chain's existing events at that serial:

- **Seal-advancer (`Gnt` / `Trm` / `Sea`) whose landing would create or join a divergence** —
  retained as evidence. Siblinging **content**, it is a burying seal-advancer: it buries the content
  and the chain re-reads **Active** → `Recovered`. Siblinging an **already-accepted sealed** branch,
  it is the **second** → `Disputed`.
- **Content event (`Ixn` / `Pin`)** — admitted. If a competing event already sits at the same
  serial, a fork forms; a second content sibling on a witnessed chain is `Ignored`, and the residual
  is `Forked`. If no event sits at the candidate's serial, the event extends linearly (`Extended`).

A **burying seal-advancer** that extends the winning branch's own tip is not a competing sibling —
it advances the seal, the content loser drops below the new seal, inert, and the chain re-reads
Active → `Recovered`.

### 5. Threshold authorization via the owner-IEL anchor

For events admitted past fork-detect, the verifier resolves the SEL event's **owner-IEL anchor** and
checks that the anchoring IEL event carries the required count — the SEL event's kind drawing its
slot from the owner IEL's threshold vector (`Ixn` / `Pin` ← `t_use`; `Gnt` ← `t_authorize`; `Trm` ←
`t_govern` for a revocation, `t_authorize` for a rescission; `Sea` ← `t_govern`) — delivered by that
IEL event's member KEL participations. The anchor is **kind-strict**: content rides an owner-IEL
`Ixn`, a `Gnt` an `Ath`, a `Trm` a `Rev` / `Dth`, a `Sea` an `Evl`; tier-elevation is an additional
floor, not the check
([`events.md` §The kind-strict cross-layer anchor matrix](events.md#the-kind-strict-cross-layer-anchor-matrix)).
Authorization failure here is HARD: a SEL event whose owner-IEL anchor is absent, wrong-kind, or
under threshold is rejected and never lands. The verifier reports structural validity; the merge
layer gates writes against it
([§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported)).

### Why this order

Severance (rule 2) precedes the seal-cap and fork-detect so a submission whose anchor is dead is
named `Severed` — accurately, the anchor is buried — rather than being mis-diagnosed as a fork or a
stale-tip `Sealed`. The security outcome (do not admit) is identical, but the cause-of-rejection
diagnostic differs, so the order is **required**, not advisory. "Outcomes commute under valid input,
so pick any order" is exactly the benign-input reasoning the adversarial-first posture rejects
([`../../../../system-thesis.md` §Adversarial-first posture](../../../../system-thesis.md#adversarial-first-posture)).

## How a burying seal-advancer resolves a content fork

When the routing path admits a seal-advancer (a `Gnt` / `Trm` / `Sea`) extending a content fork's
**winning branch tip**, the merge layer advances the seal past the loser — pure position and ascent,
no losing-branch commitment:

1. **Verify the burying event.** It is an ordinary sealed extension of its `previous` (the winning
   branch tip). Re-check SAID, prefix, chain linkage, the owner-IEL anchor and its threshold, and —
   for a `Sea` — its anchoring `Evl` (empty, or a `cut` that also evicts). Verification failure
   aborts.
2. **Advance the seal.** The event advances the last seal-advancer to its own serial. Every
   competing branch whose first event now sits below the advanced seal is inert.
3. **Kill on ascent.** Mark every below-seal loser dead — non-canonical forever, its growth dead on
   ascent (an event whose parent is dead is dead). Move it into non-canonical retained storage, then
   land the winning-branch new events.
4. **Guard the sealed case.** If a would-be-buried branch carries an **accepted** sealed event, the
   burial is rejected — a sealed branch is never buried — the fork is `Disputed` (two accepted
   sealed branches), and the burying event is itself retained as a competing sealed branch and
   counted.

A plain content SEL with no natural `Gnt` or `Trm` uses a **`Sea`** for step 1 — the neutral
advancer, anchored by an owner-IEL `Evl`. A `Sea` whose `Evl` carries a `cut` also evicts the
colluding owner member **atomically** with the bury, so a still-rostered culprit cannot race a fresh
fork at the resolved tip.

## Severance — inherited owner-IEL deadness

A SEL event's owner-IEL anchor can go dead when the owner IEL buries the branch that anchor sat on.
That does more than mark one SEL event dead — it **severs the chain**. The SEL's later events were
anchored **through** that now-dead owner-IEL lineage, and with no repair event to re-root them, the
portion after the **earliest** dead anchor cannot connect to a valid anchor lineage → it cannot be
verified. So the SEL is valid up to the earliest dead-anchor point and severed from there; the
pre-sever portion stays live.

**Deadness takes precedence over the neutral advancer.** You never bury something already dead:

- A content fork with one **severed** branch auto-resolves to the live branch — the SEL shrinks to
  the shared tip and the surviving author extends from there, **no `Sea`**. Both branches severed →
  severed at the fork.
- A **Disputed is never downgraded** by severance: its two sealed branches are **accepted**, and SEL
  acceptance gates on the owner-IEL anchor being accepted, so their (IEL sealed) anchors are never
  buried — no severance reaches an accepted sealed branch (§Matrix 2 in
  [`reconciliation.md`](reconciliation.md)). A Disputed stays terminal → re-incept.
- A **`{Trm, content}` fork** with a severed branch keeps the survivor — a severed content leaves
  the `Trm` standing (**Terminated**).

The `Sea` (and the sealed-to-Disputed escalation) exist **only** for the all-live case. Severance is
not the SEL's recovery — it is an incidental byproduct of owner-IEL divergences that happen for the
IEL's own reasons; the SEL never relies on it. The full enumeration is
[`reconciliation.md`](reconciliation.md).

## Cross-node races and gossip send-side partitioning

When two nodes each receive a competing **sealed** SEL event extending the same parent at the same
serial, convergence runs **data-locally** under acceptance gating: neither is accepted until
threshold-witnessed, and a selected witness first-seen-signs one and declines the other, so — absent
collusion — only one reaches threshold and advances the seal, the nodes converge Active (or
Terminated), and the declined party re-issues. Only under **witness collusion** do both reach
threshold: each node then holds two accepted sealed branches and reads Disputed by a data-local
walk.

Propagating a divergent SEL chain requires the same send-side partitioning the IEL uses: the sender
partitions the chain into sub-batches the receiver will accept under its routing rules (the longer
chain first as non-divergent appends, then the fork event as an atomic batch), because receive-side
ordering can sort what arrived but cannot fix a batch composition the receiver's merge handler would
reject. See [`reconciliation.md` §Transfer ordering](reconciliation.md#transfer-ordering) and the
IEL's [§Cross-node races](../iel/merge.md#cross-node-races-and-gossip-send-side-partitioning).

## Key invariants

1. **Events are sorted deterministically by `(serial, kind_priority, said)`** — the SAID tiebreaker
   carries no meaning ([`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)).
2. **The SEL prevents its own content forks by first-seen witnessing** at its own
   `(prefix, serial)`, not by the owner IEL — an owner can equivocate its SEL under a linear owner
   IEL, which witnessing closes.
3. **A dead owner-IEL anchor severs the SEL** at the earliest dead anchor — dead and un-verifiable
   from there, no repair; deadness comes before any bury.
4. **A content fork is buried by a seal-advancer** — a `Gnt` / `Trm` / `Sea` on the winning branch;
   a plain content SEL uses a `Sea`. A sealed branch is never buried → two accepted sealed branches
   are Disputed.
5. **A `Sea`'s `Evl` may carry a `cut`** — evicting the colluding owner member atomically with the
   bury, so a still-rostered culprit cannot re-fork the resolved tip.
6. **A `Trm` closes the SEL** — a submission chaining from a `Trm` is `Terminal`.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the witnessed chain, the seal and its advancers,
  severance, the down-pin.
- [`events.md`](events.md) — per-kind reference: the three axes, the manifest roles, the cross-layer
  anchor matrix, the lookup-SEL shapes, sort priority, the seal-advance cap.
- [`verification.md`](verification.md) — verifier algorithm: owner-rooting, the witnessed divergence
  read, the severance read, the lineage walk — how the verifier output composes with the merge gate.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof; the divergence matrix.
- [`../iel/merge.md`](../iel/merge.md) — the owner-IEL merge routing whose burial dead-anchors a SEL
  (severance), and the KEL/IEL send-side partitioning this reuses.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery (cross-primitive);
  [§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking).
- [`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md)
  — federation witnessing: the witnessing floor, first-seen, the beacon, cross-node propagation.
