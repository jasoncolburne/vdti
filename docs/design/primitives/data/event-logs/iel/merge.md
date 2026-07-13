# IEL Merge — Handler Rules

The IEL merge layer integrates submitted events into the existing chain. It is the protocol's
enforcement surface for the locked-portion bound, the divergence-and-recovery rules, and the
seal-cap — the same surface as the KEL's, routing a **mixed chain**: tier-1 content (`Ixn`)
alongside a tier-2 sealed spine (`Evl` / `Ath` / `Rev` / `Dth` / `Wit` / `Trm`). The verifier
produces a trust signal on a verification token; the merge layer composes that signal with
chain-state-dependent routing to admit or reject batches.

The merge layer integrates every structurally valid event (keep-all-data) and reads the chain's
state as a **pure walk** over the events held: a live fork freezes further **origination**, never
the reading, so two nodes holding the same events read the same state. Its structural checks — the
seal-cap, no-burying-a-sealed-branch, no self-burial — are the **shape-validity gate**: every IEL is
federation-witnessed, so a selected witness mirrors them before signing, and a shape it declines
never reaches threshold (see
[`../../../../protocol-doctrine.md` §Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)).

This doc states the merge-layer routing for the mixed chain: the routing order, the merge outcomes,
the content-versus-sealed split, the burying-seal recovery of a content fork, eviction as a `cut`
`Evl`, the seal-cap and the roster-less re-seal `Evl`, and **facet dispatch on every `Wit`-reading
path**. For per-kind event rules, see [`events.md`](events.md); for the verifier walk,
[`verification.md`](verification.md); for the chain primitive, [`log.md`](log.md); for the
cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## Single entry point

`merge_events` is the single entry point for all write paths into an IEL — direct submissions,
gossip propagation, federation sync, and bootstrap atomic batches. It runs under a database advisory
lock for the duration of verification and write. Time-of-check-to-time-of-use is eliminated
structurally: the verifier reads under the same lock the merge handler will use to write (see
[§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).

The merge handler returns either a **merge transition** (carrying the outcome, plus the resulting
state and new tip SAID) or a **merge rejection**.

## The content-versus-sealed split

The IEL is a mixed chain, and the one test that routes divergence is: **could a single
already-revealed secret author a competing sealed sibling?**

- **Content (`Ixn`)** → **first-seen**. Witnesses take the first content event at a position and
  decline the copies. A **user** IEL's content additionally must reach a **witness majority at its
  own `(prefix, serial)`** — the **position gate**, alongside its anchor-based authorization — so
  two disjoint member sub-quorums cannot both land a content event at one IEL serial, closing the
  two-disjoint-sub-quorums content fork. A content conflict is **recoverable**: the next sealing
  event buries the loser below the seal, no repair event.
- **Sealed (`Evl` / `Ath` / `Rev` / `Dth` / `Wit` / `Trm`)** → **first-seen at its own position too
  (the position gate is universal) + record-both** (detected, never buried): witnesses sign the
  first sealed sibling and decline later ones, so a threshold chain cannot be forked by one stolen
  key (except a singleton / `t_use = 1`), and a second **accepted** sealed decision is proof the
  quorum was subverted or the witnesses colluded, surfaced loudly (a witness-declined sibling is
  deferred-pending, forcing nothing). `{Evl, Evl}` (any two **accepted** sealed branches at the last
  seal) → **≥ 2 witnessed sealed → Disputed → terminal → reincept**; `{Evl, content}` is
  **recoverable** (the `Evl` branch survives, the content is buried).

The **federation** IEL is the pure case — every event is sealed; a competing sealed sibling is
first-seen-declined (exclude-self peer-witnessing), so only a witness-colluded **two-witnessed**
race is disputed / terminal. The witnessing mechanics that make content first-seen work (the
position gate, one-content-sibling-per-position witnessing, the beacon) are federation doctrine —
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md); this doc states the
chain-scoped routing that composes with them.

## Merge outcomes

A merge returns one of two things — a **`MergeTransition`** on success (what the batch did to the
chain, named by the resulting state) or a **`MergeRejection`** when the batch changes nothing.

**Transitions** — each is named for its action or the state the chain is in after the batch lands
(`Extended` and `Recovered` both land **Active**). The Forked-versus-Disputed split is by the
**accepted** sealed-branch count at the last seal (≤ 1 → Forked, ≥ 2 → Disputed); the content-branch
count does not affect it.

| Transition     | Verdict                                                                                                                  | Triggering condition                                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Extended**   | Linear extension → **Active**; new tip established; content does not advance the seal, all other events do.              | Events chain cleanly from the current tip (or from inception on an Empty chain).                                                                                               |
| **Recovered**  | A burying seal resolved a fork → **Active**: it extends the winning branch and advances the seal past the content loser. | An `Evl` (or another sealing kind) extends a fork's winning-branch tip (or, on a linear chain, buries the run past its attach point) — the content loser drops below the seal. |
| **Terminated** | A `Trm` admitted → **Terminated** (the identity retires, all its SELs freeze).                                           | A `Trm` lands as a linear extension, or buries a content loser below its own seal.                                                                                             |
| **Forked**     | A **recoverable** fork (≤ 1 sealed branch past it) → the chain is **Forked**, origination frozen.                        | A content event forks at an earlier serial, or a sealing event forms the fork's first sealed branch, or a content event lands on an already-forked chain.                      |
| **Disputed**   | An **irrecoverable** fork (≥ 2 accepted sealed branches past it) → **Disputed** (terminal, reincept).                    | A second accepted sealed branch joins a fork that already carries one, or a burying seal would bury a competing sealed branch.                                                 |

**Rejections** — nothing lands; the chain is unchanged (retention of the rejected event as evidence
is a separate, witnessing-gated matter — below).

| Rejection    | Verdict                                                               | Triggering condition                                                                                                                                                                                                                                 |
| ------------ | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sealed**   | Parent sits below the seal and the event is **inert** — not admitted. | An inert below-seal parent (a stale tip-view, or a dead-on-arrival content **or sealed** sibling behind an advanced seal — a below-seal sealed straggler is dropped, backdate-safe); on a Terminated chain, the **sibling-to-`Trm`** race (content). |
| **Terminal** | The tip is a `Trm`, which admits no successor.                        | Chains _from_ a `Trm` (parent kind `Trm`) — the kind-schema rule ([§Routing order](#routing-order) rule 1).                                                                                                                                          |
| **Invalid**  | Structurally inapplicable to the chain state.                         | Structural-validation failure — the kind does not apply (inception on a non-empty chain, a non-inception on an Empty one, a role outside the kind's allowlist, a `kills` on an `Ixn`, a facet-wrong `Wit` payload).                                  |
| **Ignored**  | A well-formed event the witnesses decline.                            | Fork prevention — a second **content** sibling, or a second **sealed** sibling (the position gate is universal), at a position; or a new event on a **Disputed** / **Terminated** chain (barring a partition).                                       |

`Sealed` is the **inert** case only — a below-seal event that changes nothing (content _or_ sealed:
a below-seal **sealed** straggler is dropped, inert — not witnessable past the seal, the backdate
defense; it does **not** → `Disputed`). A competing event that **forms or joins a live fork
at-or-above the seal** is a transition, not a rejection: it moves the chain to `Forked` or
`Disputed` even though it lands as retained evidence rather than a canonical tip.

**Rejection and retention are separate; retention is witnessing-gated.** Whether the node also
**retains** a competing branch as non-canonical evidence is governed by witnessing — a **sealed**
competing branch is witnessed first-seen (one per position); a node accepts and retains up to two
**witnessed** sealed branches per position (two are the `Disputed` proof); a losing **content**
sibling on a witnessed chain is **prevented** (a selected witness declines it), so it never reaches
threshold and the content fork does not form (outcome `Ignored`). Retained evidence — sealed
branches, plus the residual content-fork evidence — is what lets any verifier read the chain as
`Forked` / `Disputed` by a data-local walk
([§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery)).

**Acceptance precedes the outcome — `deferred-pending`.** The transitions above name what an
**accepted** batch does; the canonical routing runs on threshold-witnessed input. A
structurally-valid submission not yet at threshold is held **`deferred-pending`** — retained and
gossiped for witnessing, not advancing the tip or seal, not counted toward a verdict — and re-enters
routing once accepted, or becomes `Ignored` if declined as a later sibling. No node advances to a
sub-threshold event, its own fresh submission included (see [`verification.md`](verification.md),
acceptance requires threshold).

## Routing order

The merge handler routes a submitted batch through five rule scopes in this **structural order**.
The order is chosen so adversarial-input diagnostics correctly name the structural
cause-of-rejection.

### 1. Structural validation

Per-kind field rules (per the [event-shape reference](../event-shape.md#iel)), SAID integrity,
prefix consistency, chain-linkage continuity, and the **manifest role allowlist read kind-first**.
Any failure here is a structural error; the submission is `Invalid` regardless of chain state. In
particular:

- SAID recomputation matches the declared SAID; at inception, the prefix recomputes from canonical
  bytes with `said` / `prefix` set to the placeholder.
- Per-kind required / forbidden field presence, the `manifest` role vocabulary (a role outside
  `allowed(kind)` is malformed — a `kills` on an `Ixn`, a `roster` / `delegates` on an `Ixn`), and
  the `previousSeal` presence rule (present on every sealing kind, forbidden on `Icp` / `Fcp` /
  `Ixn`).
- **Facet-dependent `Wit` allowlist** (below,
  [§Facet dispatch](#facet-dispatch-on-every-wit-reading-path)) — established from the chain root
  **before** the `Wit` payload is read.
- Chain linkage: `previous` resolves to an event in the verifier's branch state; `previousSeal` (on
  a sealing kind) resolves to the prior seal.
- **Kind-schema predecessor rule.** No kind admits a `Trm` parent. A submission whose parent's kind
  is `Trm` is rejected with `Terminal` — `Trm`-terminality expressed as a kind-schema property,
  caught here at merge entry rather than by a downstream rule.

### 2. Seal-cap

The submitted event's parent must sit at-or-after `last_seal_advancing_event`
(`parent_serial ≥ seal_serial`). A submission whose parent is in the locked portion and would change
nothing is rejected `Sealed`; one that would **form or join a live fork** at the seal's own serial
is a `Forked` / `Disputed` transition instead (retained evidence). The seal-cap is **unconditional**
on the IEL: every event class is subject to it, including a burying seal — one whose
`previous.serial < seal_serial` (targeting the locked portion, not the current seal) is rejected.
This is the structural rule that enforces current-roster-only authority.

The seal-cap and `Trm`-terminality are **independent** rejection mechanisms; both surface on a
Terminated chain but catch different shapes — a **content** sibling to the `Trm` is inert below its
seal → `Sealed`; a **sealed** sibling is a second sealed branch → `Disputed`; a submission chaining
**from** the `Trm` passes the seal-cap (its parent sits at the seal boundary) and is caught only by
rule 1 → `Terminal`.

### 3. Fork-detect

The event's `(parent_said, serial)` is checked against the chain's existing events at that serial:

- **Sealing event whose landing would create or join a divergence** (a sealing event extending
  `v_{d-1}`, the last common event before the fork) — not admitted as a canonical extension;
  retained as non-canonical evidence. The chain moves to `Forked` (the fork's first sealed branch)
  or `Disputed` (its second).
- **Content event** (`Ixn`) — admitted. If a competing event already exists at the same serial, a
  fork forms; a second content sibling on a witnessed chain is `Ignored`, and the residual is
  `Forked`. If no event sits at the candidate's serial, the event extends linearly (`Extended`).

A **burying seal** that extends the **winning branch's own tip** (its `previous` is a branch tip
above `v_{d-1}`) is not a competing sibling — it advances the seal, so the content loser drops below
the new seal, inert, and the chain re-reads Active → `Recovered`.

### 4. Threshold authorization

For events admitted past rule 3, the verifier resolves the IEL event's KEL anchors and counts them
against the threshold vector, kind-strict:

- **Threshold satisfaction** — the required count (drawn from the kind's slot: `Ixn` ← `t_use`;
  `Evl` / `Rev` / `Wit` / `Trm` ← `t_govern`; `Ath` / `Dth` ← `t_authorize`) of members' fresh KEL
  participations anchor the event, each of **exactly** the kind that reveals the capability (content
  ← KEL `Ixn`; tier-2 ← KEL `Rot`; the IEL `Wit` ← KEL `Wit`), and each anchoring KEL signature
  verifies. An **`Evl` add** additionally requires each added member's tier-1 KEL `Ixn` consent,
  counted toward consent-of-added, never `t_govern`.
- **Roster-delta bounds** re-checked on the post-delta config (the security floor, the
  recoverability ceiling, the authorization floor, the roster cap; a `cut` priced the **outgoing**
  `t_govern`).
- **`Wit` change-requirement (user facet)** — a user `Wit` is a rebind: it must change `federation`
  or `witnesses`, and its `{federation, federationPin}` must field-match every anchoring KEL `Wit`.
  A no-op user `Wit` is `Invalid`. A federation `Wit` is governance — its rotation + clock advance
  is the change, so no must-change applies.
- **`kills` placement** — kind-strict to `Rev` / `Dth`; the target is opaque (never dereferenced at
  merge).

### 5. No burying a sealed branch; no self-burial

A burying seal that extends a fork's winning branch buries the competing **content** below its new
seal. If a competing branch it would bury carries a **witnessed (accepted)** sealed event, the
burial is **rejected** — a sealed branch is never buried (that would resurrect a retired sealing
decision) — the fork is ≥ 2 accepted sealed → `Disputed` (reincept), and the burying event is itself
retained as a competing sealed branch and counted (retain-and-count — dropping it would split the
reading permanently across nodes). Sealed branches are always retained (keep-all-data), so an
unnamed sealed sibling is caught, never sealed past. A burying seal that would sibling **its own**
retained chain (its `previous` is known from the walkback) is rejected as a **self-burial** — a node
buries only competing branches, never the branch it keeps.

Authorization failure here is HARD: an event whose anchors do not reach threshold, or whose
anchoring signature does not verify, is rejected and the new events never land. The verifier reports
structural validity; the merge layer gates writes against it — see
[§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported).

### Why this order

The order is chosen so attacker diagnostics correctly name the structural cause-of-rejection. When a
candidate's `parent.serial < seal.serial` (it targets the locked portion) **and** a conflicting
event already exists at `candidate.serial`, running the **seal-cap (rule 2) before fork-detect
(rule 3)** emits `Sealed` — accurately naming the rule the attacker violated — rather than naming
the symptom (the conflict in locked storage). The security outcome (reject) is identical regardless
of order; only the cause-of-rejection diagnostic differs, so the order is **required**, not
advisory. "Outcomes commute under valid input, so pick any order" is exactly the benign-input
reasoning the adversarial-first posture rejects
([`../../../../system-thesis.md` §Adversarial-first posture](../../../../system-thesis.md#adversarial-first-posture)).

## Facet dispatch on every `Wit`-reading path

The `Wit` kind is facet-dependent, and its manifest role allowlist differs by the chain's **root
facet** (`Fcp`-rooted federation versus `Icp`-rooted user —
[`events.md` §The facet-dependent `Wit`](events.md#the-facet-dependent-wit)). The merge layer
**establishes the root facet before reading any `Wit` payload** — on **every** `Wit`-reading path:
the from-scratch walk, a `resume` from a cached token, and a `search_only` walk that ends early. The
verification token carries the root facet, so a `resume` re-applies the dispatch without re-deriving
it. **No `Wit`-reading path is exempt.**

A facet-blind allowlist would admit a governance-shaped payload (a roster delta) on a user `Wit` —
and the directly-consumed governance roles have **no** downstream type-check, so the kind → role
allowlist is their only gate:

- A `Wit` on an **`Icp`-rooted (user)** chain may carry `{federation, federationPin}` (top-level)
  and `witnesses`, and **must not** carry `roster` / `clock`. It must field-match its anchoring KEL
  `Wit`s' `{federation, federationPin}` and must change `federation` or `witnesses`.
- A `Wit` on an **`Fcp`-rooted (federation)** chain may carry `roster` / `clock` / `witnesses`, and
  **must not** carry `{federation, federationPin}` (a federation witness is never self-bound).

Reading a `Wit` payload facet-blind — or a `resume` that processed a `Wit` without the token's root
facet — would let a user `Wit` smuggle a governance roster delta or a federation `Wit` smuggle a
self-binding. Both are rejected `Invalid`.

## How a burying seal resolves a content fork

When the routing path admits a sealing event (typically an `Evl`) extending a fork's **winning
branch tip**, the merge layer advances the seal past the loser — no discriminator, no losing-branch
commitment, no content-only guard walk. The mechanics are pure position + ascent:

1. **Verify the burying event.** It is an ordinary sealed extension of its `previous` (the winning
   branch tip). Re-check SAID, prefix, chain linkage, the threshold of anchoring KEL participations
   and their signatures, and any roster-delta bounds. Verification failure aborts (fail-secure on
   tampered DB rows).
2. **Advance the seal.** The event advances `last_seal_advancing_event` to its own serial. Every
   competing branch whose first event now sits below the advanced seal is inert.
3. **Kill on ascent.** Mark every below-seal loser dead — non-canonical forever, its growth dead on
   ascent (an event whose parent is dead is dead). Move it into non-canonical retained storage; then
   land the winning-branch new events.
4. **Guard the sealed case.** If a would-be-buried branch carries a **witnessed (accepted)** sealed
   event, the burial is rejected — the fork is `Disputed` (≥ 2 accepted sealed), and the burying
   event is itself retained as a competing sealed branch and counted; a sealed straggler that isn't
   accepted — witness-declined, below-seal, or **dead on ascent** (its fork-sibling is buried by
   this very seal, so its own later seal lands on the buried chain) — is **dropped**, not counted,
   and does not block the burial. Sealed branches are always retained, so an unnamed sealed sibling
   is caught, never sealed past.

The hot page covers the retained (winning) branch (≤ 64, the fold) plus the burying event; the
competing content loser is validated from retained storage and need not co-reside in the hot page. A
burying seal is **validated on arrival, not auto-applied** — the merge layer validates it as an
ordinary event at its attach-position (the same sibling / seal-cap / divergence checks any event
faces) and only then advances the seal. An **under-covering** burial (a node behind on gossip holds
content the burial never covered) is **accepted** (`Recovered`); the uncovered content inerts on the
bounded forked chain and is re-issued forward by its author. An **un-covered sealed** branch makes
the fork terminal (`Disputed`).

## Eviction — a `cut` `Evl` buries and evicts atomically

Evicting a compromised or divergence-causing member is an **ordinary `Evl` carrying a roster `cut`**
— one sealing event buries the fork **and** evicts, in a single event. There is no repair-and-evict
fold; the eviction _is_ an ordinary `Evl`.

The eviction **must be atomic** with the burying: if it were two events, the still-rostered member
would race fresh content at the resolved tip and re-fork it. The `cut` `Evl` makes it atomic by
construction — the member is gone the instant the fork resolves, because the same event that buries
the loser removes the member from the roster. The `cut` is priced the **outgoing** `t_govern`
(pre-change — so an `Evl` cannot lower its own gate then cut), and the post-cut roster is re-checked
against the bounds (a stranding / hostage cut is rejected, forcing a simultaneous `threshold` drop
or reincept). The cut target is operator-chosen.

A member KEL that goes terminal on its own (a reserve-theft takeover, with no on-chain fork to
challenge) is likewise handled by the quorum: it is inert alone (it cannot reach `t_use` /
`t_govern`), and the honest members evict it with an `Evl` `cut` (or `Dth` it if it was a delegate,
or reincept). **IEL distrust is forward-only** — a retroactive per-event distrust declaration is
forbidden (it would be the backdate kill-switch VDTI closes); trust is decided at participation
time, an event the quorum co-signed stands, and remediation is forward (revoke what it granted,
evict the member).

## The seal-cap and the roster-less re-seal `Evl`

The seal-advance cap is enforced here: between successive sealing events the content run must not
exceed `(MINIMUM_PAGE_SIZE − 1)/2 = 64` per lineage
([`events.md` §Seal-advance cap](events.md#seal-advance-cap)). A busy issuer that fills the window
re-seals with a **roster-less `Evl`** (omitting `roster`). Validation must **accept** it: no added
members means no consent needed, and it is `t_govern`-authorized on the unchanged roster. Two
identical re-seal `Evl`s at one position **dedupe** (SAID-addressable, idempotent), while a re-seal
`Evl` versus a real `Evl` at one position diverges as `{Evl, Evl}` → `Disputed`, exactly as any two
sealed events would.

## Routing by chain state

The merge layer routes a batch through three handlers based on the verifier's `IelVerification`
output: normal append, new IEL, or full path. Each operates under the merge transaction's advisory
lock.

- **Normal append (~99% of submissions).** The submitted events chain directly from the current tip
  of an Active chain. The verifier resumes from the prior tip, walks the new events, checks seal-cap
  compliance, resolves anchors, and inserts. Outcome: **Extended**. A sealing event extending
  `v_{d-1}` (rather than the tip) is not a normal append — it routes to the full path.
- **New IEL.** The submitted events start from inception (`previous` absent on the first event) and
  no IEL exists yet for the prefix. The verifier walks from inception via the inception kind
  dispatch (`Icp` / federation `Fcp`), pins the initial roster and threshold vector, and inserts.
  Outcome: **Extended**.
- **Full path (divergence, recovery, overlap).** Handles batches that do not chain from the current
  tip on a non-empty chain — deduplication (byte-identical events are one event), forked-state
  routing (a burying seal → `Recovered`; a second sealed branch → `Disputed`; otherwise a content
  event → `Forked`, a second content sibling → `Ignored`), and overlap-state routing (a submission
  chaining from an earlier point in a linear chain, forming a potential fork).

## Branch-scoped verification

When verifying a burying-`Evl` batch, the verifier seeds from the burying event's `previous` (the
winning branch tip, or `v_{d-1}` in the ancestor-extending shape) and walks only that branch plus
the batch's new events. The competing branches are buried by position + ascent; the seal advances
only after verification succeeds. This honors the no-extend-adversary rule: the walker's running
state never carries a competing branch across the recovery boundary — after recovery the chain has a
single linear walkback and the verifier's resume state is consistent with the post-recovery shape.

## Cross-node races and gossip send-side partitioning

When two federation nodes each receive a competing **sealed** event extending `v_{d-1}` at the same
serial, cross-node convergence runs **data-locally** under acceptance gating. Neither event is
accepted until it is threshold-witnessed; the two are competing **siblings at one position**, so a
selected witness first-seen-signs one and **declines** the other — absent collusion, only one
reaches threshold (**accepted**) and advances the seal, the nodes converge **Active** (or
**Terminated**), and the declined sibling is retained as non-canonical evidence (keep-all-data)
while the declined party **re-issues**. Only under **witness collusion** do both siblings reach
threshold: each node then holds two **accepted** sealed branches and reads **Disputed** by a
data-local walk. A `{Evl, Evl}` (two **accepted** sealed branches) is the disputed proof — a
provable double-sign; the witness beacon enumerates the competing branch SAIDs but the verdict is
the node's own.

Propagating a divergent IEL chain to another node requires more than ordering events by canonical
chain order: the **sender partitions** the chain into sub-batches the receiver will accept under its
routing rules and sends them in sequence (the longer chain first as non-divergent appends, then the
fork event from the shorter chain as an atomic batch). Receive-side ordering can sort what arrived
but cannot fix composition problems where the receiver's merge handler would reject a particular
batch composition. See
[`reconciliation.md` §Transfer ordering](reconciliation.md#transfer-ordering).

## Key invariants

1. **Events are sorted deterministically by `(serial, kind_priority, said)`** — the SAID tiebreaker
   carries no semantic meaning
   ([`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)).
2. **Only one divergent event added per overlap** — the first conflicting event is written as the
   fork event; a byte-identical re-submission dedupes; a further distinct competing event is
   retained as non-canonical evidence, not added as another canonical branch.
3. **A sealing event in a branch resolves or terminalizes the fork** — it buries a content loser (→
   `Recovered`, Active) or, if it would bury a sealed branch, the fork is `Disputed`; the
   locked-portion bound then rejects further inert extensions against `v_{d-1}` with `Sealed`.
4. **A `cut` `Evl` buries and evicts atomically** — the eviction and the burying are one event, so a
   still-rostered member cannot race the resolved tip.
5. **Terminated IEL is fully terminal** — a submission chaining from the `Trm` is `Terminal`; a
   content sibling to the `Trm` is `Sealed`; a sealed sibling is `Disputed`; and all the identity's
   SELs freeze.
6. **Facet dispatch precedes every `Wit` payload read** — the root facet is established from the
   chain root before any `Wit` role is consumed, on every `Wit`-reading path.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, page
  model.
- [`events.md`](events.md) — per-kind reference: threshold vector, the manifest roles, the anchor
  matrix, `kills[]`, the facet-dependent `Wit`, sort priority, seal-advance cap.
- [`verification.md`](verification.md) — verifier algorithm: threshold anchoring, roster
  accumulation, the root facet, the `kills[]` forward-match — how the verifier output composes with
  the merge gate.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof; race matrix;
  effective-SAID convergence.
- [`../kel/merge.md`](../kel/merge.md) — the KEL merge routing this reuses (single-key chain).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#divergence-and-recovery) —
  divergence and recovery (cross-primitive): freeze, tier-resolution, keep-all-data retention;
  [§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded);
  [§Merge verification and advisory locking](../../../../protocol-doctrine.md#merge-verification-and-advisory-locking).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor, the beacon, content-fork prevention, cross-node
  propagation.
