# KEL — Key Event Log

The **Key Event Log** (KEL) is a per-prefix chain of cryptographically-linked signed key events
describing a controller's evolving signing and recovery key state. Each event is a
[SAD](../../sad/sad.md) carrying chain-linkage fields (`prefix`, `previous`, `serial`, `kind`) plus
kind-specific commitments; authority is asserted by direct signature against keys committed by prior
establishment events. The per-kind field shape is the cross-primitive
[event-shape reference](../event-shape.md); this doc and its siblings state the KEL-specific
doctrine.

KEL is the foundation primitive in VDTI's chain-of-trust composition. IEL events and SEL events
anchor in KEL events — the [tier model](../../../../protocol-doctrine.md#tiers) ties the
cryptographic difficulty of forging a privileged IEL / SEL act to the difficulty of forging the
corresponding KEL anchor.

This doc states the chain primitive: prefix derivation, the per-node chain states, the seal and the
spine, the locked-portion bound, and the page / chunking model. Per-kind reference lives in
[`events.md`](events.md); merge-handler routing in [`merge.md`](merge.md); recovery doctrine in
[`recovery.md`](recovery.md); the verifier walk in [`verification.md`](verification.md); the
cross-node correctness proof in [`reconciliation.md`](reconciliation.md).

## Prefix derivation

A KEL inception event is a
[prefix-deriving SAD](../../sad/said.md#chain-inception-events-prefix-deriving-sads): the prefix and
SAID are derived via two separate Blake3-256 hashes over the canonical bytes. The prefix commits to
the **whole inception SAD content** with both `said` and `prefix` blanked to the fixed-value
placeholder; the SAID then commits to the same SAD with `prefix` populated and only `said` blanked.

Whole-content prefix commitment means an inception event's `publicKey`, `rotationHash`,
`recoveryHash`, kind discriminator, and — on a federation-bound `Icp` — its `federation` /
`federationPin` binding are all bound into the prefix. Two distinct inception events cannot share a
prefix without producing a Blake3-256 collision. Subsequent events inherit the inception's `prefix`
and derive only `said`.

KEL inception is dispatched by **kind** at v=0 — see
[`events.md` §Two-kind inception](events.md#two-kind-inception). The kind determines whether the
chain is pre-federation (`Fcp`) or federation-bound from inception (`Icp`). The verifier dispatches
structural behavior on the kind; consumer trust composes through the
[config-pinned federation prefix set](../../../../protocol-doctrine.md#federation-witnessing-in-verification).

## Per-node chain states

A KEL is in exactly one of three states **on any given node** — Active, Divergent, or
Decommissioned. State is computed from the events the node holds, never tracked as a separate flag.
Whether a divergence is **reconcilable** or **terminal** is a further fact any verifier reads
**data-locally** by walking the branches it holds (below) — not a fourth state.

| State              | Description                                                                                                                                                                                   | Accepts new events?                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active**         | Linear chain; the current tip extends cleanly via `previous`.                                                                                                                                 | Yes — `Ixn` / `Rot` / `Ror` / `Rec` / `Wit` / `Dec` per their authorization and seal-cap requirements.                                                                                                                                                                                                                                                                                                                  |
| **Divergent**      | A **fork**: two **distinct** (different-SAID) events at one serial, at or above the derived seal. The **reading** (below) is a pure walk of the events held; what freezes is **origination**. | **None originated** onto the live fork — the ways forward are a `Rec`, or (for a content fork) a seal-advancer on the winning branch that buries the loser, after which the chain re-reads Active (carve-out: a `{Dec, content}` fork resolves by tier-rank — the terminal `Dec` wins, no repair). A below-seal straggler arriving after the chain sealed past its serial is inert, retained as evidence, not a freeze. |
| **Decommissioned** | A terminal `Dec` landed cleanly. The `Dec` advances the seal to its own serial; the chain is sealed there.                                                                                    | None. A sibling to the `Dec` is rejected by the seal-cap (`SiblingLocked`); a submission chaining from the `Dec` is rejected by the kind-schema rule (`KelDecommissioned`).                                                                                                                                                                                                                                             |

A repair keeps the recovering party's own branch and archives the rest, returning the chain to
Active — possible only when no archived branch carries a privileged event (see
[`recovery.md`](recovery.md)). Two byte-identical events at one serial **are one event** — they
dedupe by SAID, never a second branch; only distinct events collide. The full freeze-and-repair rule
is the protocol doctrine's —
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair).

### Reconcilable versus terminal — a data-local walk

Whether a fork can be repaired turns on **tier**, read from the data:

- **Reconcilable** — at most one branch carries a privileged event past the fork. A `Rec` keeps the
  recovering party's own branch and archives the rest, naming one losing branch's **root** as its
  `fork` (every other competing branch closes below the seal and by descent, unnamed) — every
  competing branch must be content-only; the chain returns to Active. While the fork stands the
  chain reads `forked`; the effective SAID is the real digest over the **live tips** the log holds.
- **Terminal (disputed)** — **two or more branches each carry a privileged event** past the fork. No
  privileged branch can be archived (a privileged event is never overturned — that would resurrect
  retired keys), so no single chain can be chosen and the prefix must **reincept**. The chain reads
  `disputed` — the same real digest over the **live tips** as any live fork; the reading is the
  walk's, never encoded in the value.

Terminality is a **branch-level fact any verifier computes data-locally** by walking the
**retained** branches — a node retains a competing branch as non-canonical evidence rather than
discarding it at the seal-cap ([§The locked portion](#the-locked-portion)). A node holding both
privileged branches reads `disputed` directly; a node holding only one fetches the rest via the
**witness beacon**, which **enumerates** the competing branch SAIDs. The federation **propagates**
the branches; it does **not** decide the verdict. See
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair) and
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison).

## The seal, the spine, and the locked-portion bound

The KEL verifier surfaces two forward-only watermarks on its
[`KelVerification`](verification.md#kelverification-token) token, both computed from the chain's
events.

| Concept                         | Advances on                           | Used for                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `last_seal_advancing_event`     | `Rot` / `Ror` / `Rec` / `Wit` / `Dec` | Seal-cap rule: every new event's parent must sit at-or-after this serial. The locked portion is everything strictly below it (the seal-advancing event itself is a legal parent). This is the **derived seal** — the most recent such event that landed **cleanly** on the linear run (not a competing sibling) — and the chain's reading is computed against it, from the events held, never arrival order. |
| `last_recovery_revealing_event` | `Ror` / `Rec` / `Wit` / `Dec`         | Spent-key rule: tracks which recovery-key preimage is currently committed. Once a recovery-revealing event lands, the recovery key it reveals is publicly known.                                                                                                                                                                                                                                             |

The two memberships diverge only on `Rot` — it advances the seal without revealing the recovery key.
`Dec` does both: it reveals the recovery key (dual-signed) and advances the seal to its own serial,
where it is terminal — it opens no new window, since no successor may land. The orthogonality lets
the protocol bound chain-state changes (via the seal-advance cap, below) while leaving
recovery-preimage rotation cadence to operator guidance — recovery keys are hardware-held and
preimage-identified rather than usage-degraded, so a forced cadence adds no security — and, for an
operator who keeps the reserve in cold storage, could impose scheduled access their threat model is
designed to avoid.

### The spine

The seal-advancing events form a **spine**: every seal-advancing event carries a top-level
**`previousSeal`** back-link to the prior one, so following `previousSeal` renders a seal-only view
(`Icp → seal → seal → …`) while `previous` renders the full flat chain. The inception (`Icp` /
founder `Fcp`) is the spine root and carries no `previousSeal`. A seal-advancing event does **not**
commit its content run: the retained run since the prior seal is the derivable linear chain
`[previousSeal..previous]` (nodes keep the full bodies; the flat query returns them), and "content
was folded here" is the derived predicate `previous != previousSeal`. Only a **repair** carries a
manifest fold field — the **`fork`** role, a required single losing-branch **root** SAID the `Rec`
condemns (the root — a branch's first divergent event — condemns its entire subtree; every other
competing branch closes below the seal and by descent); `Rot` / `Ror` / `Wit` / `Dec` carry no such
role.

The spine is a **convenience** view — the same chain walk with `previousSeal` substituted for
`previous`, yielding authority state and a terminal-divergence view (a spine fork is two competing
seals — privileged, hence terminal) but not recoverable content forks or content completeness. The
detection guarantee, and any decision that turns on a content event, use the **flat** walk; a
skipped seal is caught by the flat walk (it appears as a seal-advancing event when `previous`
traverses the run) plus spine-fork detection (the real skipped seal, once held, competes at its
spine position). The spine alone trusts `previousSeal` — a fail-secure pre-check (a forged
`previousSeal` that skips a seal surfaces as a competing seal once the real one is held). The
cross-primitive spine / fold model is the protocol doctrine's —
[§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded); the event fields
are the [event-shape reference](../event-shape.md)'s.

### The locked portion

The **locked portion** of a KEL is the segment **below** `last_seal_advancing_event` (strictly — the
seal-advancing event itself is a legal parent: the normal post-`Rot` append extends it, and a repair
may attach at it). Events in this segment are structurally immutable within the chain:

- `Rec` cannot target the locked portion. The repair's `previous` must sit at-or-after the most
  recent seal-advancing event (see
  [`recovery.md` §Repair-event bound](recovery.md#repair-event-bound)).
- A new event whose `previous` points into the locked portion is **rejected as a canonical
  extension** with `SiblingLocked`. Whether that rejected fork is **retained as non-canonical
  evidence** is a separate, witnessing-gated decision — a losing **content** sibling on a witnessed
  chain never forms (nothing to retain), while a privileged branch, or any fork on a direct-mode
  chain, is kept, so the proof a divergence occurred survives wherever a fork actually forms.
- The seal-cap's role is to deny revival attacks: a party holding stale authority (a recovery
  preimage already revealed by an earlier `Rec` / `Ror` / `Wit`, or a key since rotated out) cannot
  construct an event targeting the locked portion to rearrange the chain. Only current authority
  gates further extension.

### Pre-seal verifiability

The at-or-below-seal portion is permanently final — for the chain itself (no future event may target
it) and for consumers verifying anchors, credentials, and SEL bindings against it; the permanence
claims run against the last **clean** seal (a below-seal **privileged** fork is a spine fork that
flips the reading to `disputed` without rewriting any sealed event). See
[`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability) for the structural
defense argument and
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair) (_Pre-seal
verifiability_) for the cross-primitive framing.

### Once-revealed-final invariant

Once a recovery-revealing event lands, the dual signature it proves is final. Subsequent compromise
or revocation of the keys it revealed does not retroactively unsatisfy the past authorization — the
chain's history at that serial is locked. Without this, history could be invalidated retroactively
by anyone who later comes to control the revealed key material, making terminal states (recovered,
decommissioned) unstable. The trade-off: a key controller who later turns adversarial cannot undo
their past contributions; only the going-forward spent-key effect applies.

## Seal-advance cap

A seal-advancing event (`Rec` / `Ror` / `Rot` / `Wit`; the terminal `Dec` also advances the seal but
ends the chain) must land at least every `(MINIMUM_PAGE_SIZE − 1)/2 = 64` non-seal-advancing events
**per lineage**. The cap bounds the **fold** — the content run since the last seal — to 64 events on
each branch, so the canonical two-branch fork anchored at the last seal — both lineages (≤ 64 each)
plus the resolving `Rec` — fits in one page.

`MINIMUM_PAGE_SIZE = 129 = 2·64 + 1` is a protocol constant — a deployment floor, not a
per-deployment knob — so a fork-and-repair page produced on any conformant deployment fits on every
other. The page carries **both** competing branches plus the `Rec` because a source → sink transfer
delivers the fork to a sink that holds neither branch in storage — the `Rec`'s content-only guard
must have every branch to walk within one atomic unit. A **local** discriminator needs less: its hot
page is the retained branch (≤ 64) plus the `Rec`; the losing branch named by the `Rec`'s `fork`
root is condemned — every other closes below the seal and by descent — validated from retained
storage, not held in the page. The shapes that exceed one page (an own-`Rot` in the retained tail; a
≥ 3-branch residual fork) ride earlier or later pages —
[`reconciliation.md` §Invariants](reconciliation.md#invariants) (invariant 3) carries the
derivation.

Recovery-preimage rotation cadence (how often `Ror` should land to refresh the commitment) is
**operator guidance**, not a protocol-enforced cap — see
[`events.md` §Seal-advance cap](events.md#seal-advance-cap).

The seal-advance cap composes with the divergence-and-repair rules to give the
[bounded-divergence invariant](reconciliation.md#invariants): an adversary holding less than the
rotation-key preimage can only submit `Ixn` events, and the cap limits each of their lineages to at
most 64 events past the last seal before they must produce a seal-advancing event (which requires at
least tier-2 capability — see
[`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)).

## Page model

Chains are read, verified, written, and replicated in **pages** of bounded size. The page is the
unit of memory budget for the verifier walk, the unit of round-trip for storage reads, and the unit
of atomicity for the merge handler's discriminator.

- **`MINIMUM_PAGE_SIZE` = 129** — protocol constant; the floor every conformant deployment must
  support. The seal-advance cap (`(MINIMUM_PAGE_SIZE − 1)/2 = 64` per lineage) is derived from this
  constant so a two-branch fork-and-repair page produced anywhere validates anywhere.
- **Page boundaries align with generations.** A generation is the set of events at the same serial.
  The verifier processes events in generation order (`serial ASC, kind sort_priority ASC, said ASC`)
  and re-fetches an incomplete generation at the next page boundary; a divergent generation that
  spans two pages re-fetches on the next page rather than being processed half-observed.
- **Deterministic intra-generation ordering.** Per-kind `sort_priority` (see
  [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)) breaks intra-generation
  order so all nodes process the same batch identically. The `said` tiebreaker is for determinism
  only and has no semantic meaning.

The page model lets every operation be bounded-resource. The discriminator's hot page — the retained
branch plus the `Rec` — fits in one page (per the seal-advance cap derivation above). The verifier's
`max_pages` cap (default 64 pages ≈ 8K events; configurable via env var) caps resource use even on
adversarial chains.

## Chain-lifecycle paths (per-node)

The structural rules above produce three lifecycle paths per node.

- **Active extension.** Each new event extends the linear chain via `previous = tip.said`.
  Seal-advancing kinds (`Rot` / `Ror` / `Rec` / `Wit` / `Dec`) advance `last_seal_advancing_event`
  to their own serial and carry `previousSeal`; the content kind (`Ixn`) leaves the seal where it
  was.
- **Divergence and recovery.** Two distinct events at one serial form a fork; the chain freezes
  further origination until a `Rec` repairs it — or, for a content fork, a seal-advancer on the
  winning branch buries the loser below the new seal. A `Rec` attaches at its submitter's own last
  event, **retaining** that branch and archiving the **archival tail(s)** — the competing branches:
  one is condemned by the root committed as the `Rec`'s `fork` (a root condemns its whole subtree;
  growth after the repair is dead by descent), every other closes below the seal and by descent
  without being named. Each dead lineage is depth-capped by the seal-advance cap; the retained
  branch plus the `Rec` fits in one page. See
  [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes) for the two ways a `Rec` can
  attach.
- **Clean retirement.** `Dec` lands as a linear extension of the current tip; the chain becomes
  Decommissioned. `Dec` advances the seal to its own serial and sits on the spine, but opens no new
  window — it permits no successor. Subsequent submissions are rejected by two independent
  mechanisms — the seal-cap rejects a sibling to the `Dec`; the kind-schema rule rejects a
  submission chaining from the `Dec` (see [`merge.md` §Routing order](merge.md#routing-order)). Past
  content keeps its meaning under the locked-portion bound.

Cross-node privileged-vs-privileged races — two federation nodes accepting different privileged
events at the same serial via independent clean linear extensions — are not a per-node state. Each
node's seal-cap **rejects the gossip-arriving competing event as a canonical extension but retains
it as non-canonical evidence**, so each node ends up holding both branches and reads the divergence
by a data-local walk; the witness beacon propagates the branches to a node that lacks them, but does
not decide the verdict. See
[`recovery.md` §Cross-node privileged-vs-privileged races](recovery.md#cross-node-privileged-vs-privileged-races),
[§Divergence and repair](../../../../protocol-doctrine.md#divergence-and-repair), and
[§Federation convergence](../../../../protocol-doctrine.md#federation-convergence).

## End-verifiability

KEL's contribution to end-verifiability over data-from-any-source is two structural properties:
whole-content prefix derivation makes the inception event tamper-evident (substituting content would
require a Blake3-256 collision against both `prefix` and `said`), and locked-portion immutability
under the seal-cap means events at-or-below `last_seal_advancing_event` cannot be rearranged by any
future event — so anchors, credentials, and SEL bindings resolving to the locked portion stay
structurally trustworthy indefinitely. The cross-primitive framing (verify the data, not the source)
is canonical in
[`../../../../system-thesis.md` §End-verifiability](../../../../system-thesis.md#end-verifiability);
the recovery-side composition with the three-tier compromise model is in
[`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability).

## Cross-references

- [`../event-shape.md`](../event-shape.md) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal` / `fork`, per-kind field tables.
- [`events.md`](events.md) — per-kind reference: two-kind inception, privileged and non-privileged
  kinds, three-tier capability model, anchor requirements, seal-advance cap.
- [`merge.md`](merge.md) — merge handler routing: routing order, outcomes, locked-portion
  enforcement.
- [`recovery.md`](recovery.md) — recovery doctrine: three-tier compromise model, dual-signature
  defense, pre-seal verifiability.
- [`verification.md`](verification.md) — verifier walk algorithm, kind dispatch at inception,
  signature verification, anchor checking.
- [`reconciliation.md`](reconciliation.md) — exhaustive case-matrix proof of cross-node convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — tiers and kind-strict
  anchoring, divergence and repair, forks-are-seal-bounded and the spine, operation categories,
  federation convergence, the effective-SAID comparison.
- [`../../sad/sad.md`](../../sad/sad.md), [`../../sad/said.md`](../../sad/said.md) — the SAD shape
  KEL events compose on; prefix and SAID derivation algorithms.
- [`../iel/`](../iel/) — IEL primitive (subsequent sub-issue). KEL events host the anchors that
  authorize tier-2 and tier-3 IEL acts per the tier model.
- [`../sel/`](../sel/) — SEL primitive (subsequent sub-issue). KEL events host the anchors that
  authorize tier-1, tier-2, and tier-3 SEL acts.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing doctrine (subsequent sub-issue): the kind-scoped witnessing ladder, the majority floor,
  the beacon, divergent witness receipts, acceptance gating.
- [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) — federation
  bootstrap (subsequent sub-issue): the atomic ceremony that brings `Fcp` / `Rot` and the federation
  IEL `Fcp` into existence together.
