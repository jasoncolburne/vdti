# SEL Merge — Handler Rules

The SEL merge layer integrates submitted events into the existing chain. It is the protocol's
enforcement surface for the two cross-layer rules — **anchor-monotonicity** and **cross-layer
deadness-descends** — that make the IEL the SEL's clock, routing a **mixed chain**: tier-1 content
(`Ixn` and the floor `Pin`) alongside two tier-2 sealed kinds (`Gnt` / `Trm`). The verifier produces
a trust signal on a verification token; the merge layer composes that signal with
chain-state-dependent routing to admit or reject batches.

The one thing that distinguishes SEL merge from IEL merge is **where a content fork resolves**. A
SEL holds no seal of its own on a plain content chain, so it does **not** bury a content loser with
a SEL-local seal — it resolves the fork **cross-layer**, under the IEL's burying seal, with the
losing SEL events dying by descent across the anchor edge. This doc states the merge-layer routing:
the content-versus-sealed split, cross-layer fork resolution, anchor-monotonicity, and cross-layer
deadness-descends. For per-kind event rules, see [`events.md`](events.md); for the verifier walk,
[`verification.md`](verification.md); for the chain primitive, [`log.md`](log.md); for the
cross-layer correctness proof, [`reconciliation.md`](reconciliation.md).

## Single entry point

`merge_events` is the single entry point for all write paths into a SEL — direct submissions, gossip
propagation, and federation sync. It runs under a database advisory lock for the duration of
verification and write, so time-of-check-to-time-of-use is eliminated structurally: the verifier
reads under the same lock the merge handler will use to write (see
[§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).

The merge handler returns either a **merge transition** (carrying the outcome, plus the resulting
state and new tip SAID) or a **merge rejection**, the same `Result<MergeTransition, MergeRejection>`
vocabulary the KEL and IEL use.

## The content-versus-sealed split

The SEL is a mixed chain, and the one test that routes divergence is: **could a single
already-revealed secret author a competing sealed sibling?**

- **Content (`Ixn`, `Pin`)** → **first-seen, buriable**. A content conflict is **recoverable** — but
  the recovery is **cross-layer**, not a SEL-local seal. Because a valid SEL fork implies an IEL
  fork beneath it (§Anchor-monotonicity), a content fork on a witnessed SEL is prevented at the
  IEL's own witnessing floor; where it forms (a witness compromise, or a gossip-lag straggler) it
  resolves when the **IEL buries its fork** and the losing SEL content dies by descent.
- **Sealed (`Gnt` / `Trm`)** → **record-both** (detected, never buried). A `Gnt` / `Trm` is anchored
  by a tier-2 IEL event (an `Ath` / `Rev` / `Dth`), so a competing sealed SEL sibling requires a
  competing sealed IEL sibling beneath it — which is exactly the IEL's own `disputed`-forcing case.
  A `Trm` versus content at one position resolves on **tier-rank** (the kill wins, the content
  buries: `{Trm, Ixn}`); two accepted sealed SEL branches mean the IEL is disputed → the owner
  reincepts.

Every SEL fork is therefore an image of an IEL fork. The SEL merge layer never runs a SEL-local
witness gate or a SEL-local burying seal; it enforces the cross-layer edge and lets the IEL resolve
the fork.

## Merge outcomes

A merge returns one of two things — a **`MergeTransition`** on success (what the batch did to the
chain, named by the resulting state) or a **`MergeRejection`** when the batch changes nothing.

**Transitions:**

| Transition     | Verdict                                                                                                                   | Triggering condition                                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Extended**   | Linear extension → **Active**; content re-pins and does not advance the seal, `Gnt` / `Trm` advance it.                   | Events chain cleanly from the current tip (or from inception on an Empty chain), each extending the SEL's latest IEL-anchored tip. |
| **Terminated** | A `Trm` admitted → **Terminated** (the SEL is closed); or the IEL terminated and all its SELs freeze.                     | A `Trm` lands as a linear extension, or buries a content sibling by tier-rank.                                                     |
| **Forked**     | A live content fork (≤ 1 accepted sealed branch) → **Forked**, origination frozen, awaiting the IEL's cross-layer burial. | A content event forks at a serial, or lands on an already-forked chain.                                                            |
| **Disputed**   | The IEL forked with ≥ 2 accepted sealed branches beneath the SEL → **Disputed** (terminal; the owner reincepts).          | A second accepted sealed branch joins a fork, mirroring the IEL's own dispute.                                                     |

**Rejections:**

| Rejection          | Verdict                                                                                                     | Triggering condition                                                                                                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Unattributable** | The anchoring IEL event's body is not held → the SEL event is **skipped**, not blocking.                    | Anchor-monotonicity: a node lacks the IEL anchor body, so it cannot attribute the tip (skip-unattributable — the SEL is never wedged by a withheld / private / lost anchor body).                          |
| **Inert**          | A re-anchor at an already-attributed SEL serial, or a dead-by-descent event. Nothing lands.                 | Anchor-monotonicity (a re-anchor at an attributed serial is malformed → inert), or cross-layer deadness-descends (the anchoring IEL event is dead).                                                        |
| **Terminal**       | The tip is a `Trm`, which admits no successor.                                                              | A submission chaining _from_ a `Trm` (parent kind `Trm`).                                                                                                                                                  |
| **Invalid**        | Structurally inapplicable to the chain state.                                                               | Structural-validation failure — inception on a non-empty chain, a non-inception on an Empty one, a role outside the kind's allowlist, a manifest on an `Icp` / `Pin`, a `content` role on a `Gnt` / `Trm`. |
| **Ignored**        | A well-formed event the IEL's witnesses decline (fork prevention), or one on a Disputed / Terminated chain. | The competing content sibling never reaches threshold on the IEL, so the SEL content fork does not form; or a new event on a Disputed / Terminated chain.                                                  |

## Routing order

The merge handler routes a submitted batch through these rule scopes in **structural order**, chosen
so adversarial-input diagnostics correctly name the structural cause-of-rejection.

### 1. Structural validation

Per-kind field rules (per the [event-shape reference](../event-shape.md#sel)), SAID integrity,
prefix consistency, chain-linkage continuity, and the **manifest role allowlist read kind-first**.
Any failure here is a structural error; the submission is `Invalid` regardless of chain state. In
particular:

- SAID recomputation matches the declared SAID; at inception, the prefix recomputes from the
  canonical bytes (the populated `owner` / `topic` / `data`) with `said` / `prefix` set to the
  placeholder.
- Per-kind required / forbidden field presence — the `Icp` carries no `pin` / `manifest`, the `Pin`
  carries only the down-`pin`, `previousSeal` is present on `Gnt` / `Trm` and forbidden on `Icp` /
  `Ixn` / `Pin`, and the manifest role vocabulary is enforced (a `content` role on a `Gnt` / `Trm`,
  or any manifest on an `Icp` / `Pin`, is malformed).
- **Kind-schema predecessor rule.** No kind admits a `Trm` parent. A submission whose parent's kind
  is `Trm` is rejected with `Terminal`.

### 2. Anchor-monotonicity

The submitted event must **extend the SEL's latest IEL-anchored tip**, computed over the owner IEL's
canonical / retained walk:

- **Skip-unattributable.** The anchor SAID is opaque, so an IEL anchor whose body the node does
  **not hold** cannot be attributed; the SEL event is **skipped, not blocking** (`Unattributable`) —
  a withheld, lost, or private anchor body never wedges the SEL. The node processes each SEL it can
  attribute correctly, and catches up when the anchor body arrives.
- **Re-anchor is inert.** An IEL anchor that names a SEL event at an **already-attributed** serial
  is malformed → the SEL event is **`Inert`** (the carrying IEL event stays valid; an inert anchor
  never advances the tip). This is what forbids re-writing a SEL's history by re-anchoring an old
  serial.

So on a **linear** IEL the SEL totally-orders and never forks; a SEL fork can only arise where the
IEL itself forked (§Anchor-monotonicity — the theorem).

### 3. Cross-layer deadness-descends

A SEL event whose **anchoring IEL event is dead** — condemned, or buried below the IEL's seal — is
**itself dead** (`Inert`), the **IEL → SEL** anchor edge only (never the KEL → IEL edge). This is
the mechanism a plain content SEL's fork resolves through: the IEL buries its losing branch, that
branch's SEL anchors die, and every SEL event they anchored dies by descent.

### 4. Fork-detect and cross-layer resolution

The event's `(parent_said, serial)` is checked against the chain's existing events at that serial:

- **Content event** (`Ixn` / `Pin`) — admitted (keep-all-data). If a competing content event already
  sits at the same serial, a fork forms; a second content sibling is `Ignored` when the IEL's
  witnesses decline it, and the residual is `Forked`, awaiting the IEL's cross-layer burial. If no
  event sits at the candidate's serial, it extends linearly (`Extended`).
- **`Gnt` / `Trm`** — a sealed extension advancing the local seal (`Extended`, or `Terminated` for a
  `Trm`). A `Trm` competing with content at one position wins on tier-rank — the content buries
  (`{Trm, Ixn}` → `Terminated`). A second **accepted** sealed branch mirrors the IEL's dispute →
  `Disputed`.

There is **no SEL-local burying seal**: a content fork is not resolved by a SEL event but by the
IEL's burying seal dropping the anchoring IEL event (rule 3). A node behind on gossip that holds a
losing SEL content branch re-reads it dead the instant it holds the IEL's burying seal — the SEL
content inerts by descent, and is re-issued forward by its owner.

### 5. Threshold authorization

For events admitted past the earlier rules, the verifier resolves the SEL event's **IEL anchor** and
checks that the anchoring IEL event carries the required count (the SEL event's kind draws its slot
from the IEL's threshold vector: `Ixn` / `Pin` ← `t_use`; `Gnt` ← `t_authorize`; `Trm` ← `t_govern`
for a revocation, `t_authorize` for a rescission), delivered by that IEL event's member KEL
participations. The anchor is **kind-strict** — content rides an IEL `Ixn`, a `Gnt` an `Ath`, a
`Trm` a `Rev` / `Dth`; tier-elevation is an additional floor, not the check
([`events.md` §The kind-strict cross-layer anchor matrix](events.md#the-kind-strict-cross-layer-anchor-matrix)).
Authorization failure here is HARD: a SEL event whose IEL anchor is absent, wrong-kind, or under
threshold is rejected and never lands. The verifier reports structural validity; the merge layer
gates writes against it
([§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported)).

### Why this order

Anchor-monotonicity (rule 2) precedes fork-detect (rule 4) so that a submission whose anchor a node
cannot attribute is named `Unattributable` — accurately, the anchor is unheld — rather than being
mis-diagnosed as a fork it merely appears to conflict with. The security outcome (do not advance the
tip) is identical either way; only the cause-of-rejection diagnostic differs, so the order is
**required**, not advisory. "Outcomes commute under valid input, so pick any order" is exactly the
benign-input reasoning the adversarial-first posture rejects
([`../../../../system-thesis.md` §Adversarial-first posture](../../../../system-thesis.md#adversarial-first-posture)).

## How a content fork resolves cross-layer

When a plain content SEL forks, no SEL event resolves it — the resolution rides the **IEL**:

1. **The IEL buries its fork.** The IEL's burying seal (an `Evl`, or a `cut` `Evl` when it also
   evicts) advances the IEL's seal past its losing branch — the standard IEL recovery
   ([`../iel/merge.md` §How a burying seal resolves a content fork](../iel/merge.md#how-a-burying-seal-resolves-a-content-fork)).
2. **The losing IEL anchor dies.** The IEL event that anchored the SEL content loser is now below
   the IEL's seal, inert.
3. **The SEL loser dies by descent.** Every SEL event anchored by that dead IEL event is dead by
   cross-layer deadness-descends (rule 3), and everything built on it is dead by descent (an event
   whose parent is dead is dead) — growth-proof: a losing SEL branch a lagging node grows after the
   burial is dead too.

The SEL re-reads **Active** on the winning IEL branch, order-independent. A **`{Trm, Ixn}`**
divergence needs no IEL burial — the sealed `Trm` wins on tier-rank locally and the content buries.
Only a fork with **≥ 2 accepted sealed SEL branches** — meaning the IEL is itself disputed beneath —
is terminal (`Disputed` → the owner reincepts).

## Eviction and the tier-1 compromise

A SEL has no roster and no eviction of its own — remediation always rides the **IEL**. A compromised
owner **signing key** can author SEL content (`Ixn` / `Pin`) but no sealed SEL `Gnt` / `Trm` (those
need the rotation reserve, delivered by a member KEL `Rot` anchoring a tier-2 IEL event). So a
signing-key compromise's whole SEL blast radius is content, and **one IEL rotation** buries the
forked content tail — every anchored SEL event on the event author's tail dead by descent, **no
reincept**
([`reconciliation.md` §The tier-1 compromise is fully deadenable](reconciliation.md#the-tier-1-compromise-is-fully-deadenable)).
A compromise that reaches the **reserve** — a **competing sealed branch**, riding a sealed IEL event
— is the IEL's `disputed` case → reincept — the point of no return the reserve defends.

## Cross-node races and gossip send-side partitioning

Because every SEL fork is an image of an IEL fork, cross-node SEL convergence **inherits** the
IEL's. Two nodes holding competing SEL content branches converge when they both hold the owner IEL's
burying seal — the loser inerts by descent. Propagating a divergent SEL chain requires the same
send-side partitioning the IEL uses: the sender partitions the chain into sub-batches the receiver
will accept under its routing rules (the longer chain first as non-divergent appends, then the fork
event as an atomic batch), because receive-side ordering can sort what arrived but cannot fix a
batch composition the receiver's merge handler would reject. See
[`reconciliation.md` §Transfer ordering](reconciliation.md#transfer-ordering) and the IEL's
[§Cross-node races](../iel/merge.md#cross-node-races-and-gossip-send-side-partitioning).

## Key invariants

1. **Events are sorted deterministically by `(serial, kind_priority, said)`** — the SAID tiebreaker
   carries no meaning ([`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)).
2. **A SEL event extends its SEL's latest IEL-anchored tip** — skip-unattributable (a withheld
   anchor never wedges the SEL); a re-anchor at an attributed serial is inert.
3. **A SEL event on a dead IEL anchor is dead** — cross-layer deadness-descends (the IEL → SEL edge
   only).
4. **A content fork resolves cross-layer** — under the IEL's burying seal, never a SEL-local seal.
5. **`Gnt` / `Trm` are sealed on arrival and never buried** — a `Trm` wins on tier-rank over content
   at one position; ≥ 2 accepted sealed branches mean the IEL is disputed → reincept.
6. **A `Trm` closes the SEL, and an IEL `Trm` freezes all its SELs** — a submission chaining from a
   `Trm` is `Terminal`.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal-advancers, the down-pin, the IEL clock.
- [`events.md`](events.md) — per-kind reference: the three axes, the manifest roles, the cross-layer
  anchor matrix, the lookup-SEL shape, sort priority.
- [`verification.md`](verification.md) — verifier walk: anchor-monotonicity over the IEL walk, the
  cross-layer deadness read, the `Trm` kill structure — how the verifier output composes with the
  merge gate.
- [`reconciliation.md`](reconciliation.md) — cross-layer correctness proof; the theorem; the
  tier-1-fully-deadenable result.
- [`../iel/merge.md`](../iel/merge.md) — the IEL merge routing that buries a SEL's fork cross-layer
  (the burying seal, the `cut` `Evl` eviction, send-side partitioning).
- [`../kel/merge.md`](../kel/merge.md) — the KEL merge routing the machine originates in.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery (cross-primitive);
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded);
  [§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor the content-fork-prevention theorem rides.
