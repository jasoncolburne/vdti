# IEL — Identity Event Log

The **Identity Event Log** (IEL) is a per-identity chain of cryptographically-linked events
describing one identity's evolving membership and the authority it grants. An identity is **a
threshold over member KELs** — a roster of member device KELs plus a **threshold vector**
`{ use, authorize, govern }`. The IEL composes no policy internally (that is the document layer);
"who is this identity" is the roster, "how many must act for this kind of act" is the threshold
vector. Each event is a [SAD](../../sad/sad.md) carrying chain-linkage fields (`prefix`, `previous`,
`serial`, `kind`) plus kind-specific commitments; authority is asserted **not** by an adjacent
signature but by a threshold of members' fresh KEL participation anchoring the event
([`../event-shape.md` §Authentication & signatures](../event-shape.md#authentication--signatures)).
The per-kind field shape is the cross-primitive [event-shape reference](../event-shape.md#iel); this
doc and its siblings state the IEL-specific doctrine.

The IEL sits between the KEL and the SEL. It **is anchored by** member KEL events — every IEL event
is authorized by a threshold of members' fresh KEL events (the
[tier model](../../../../protocol-doctrine.md#tiers) ties the cost of forging a sealed IEL act to
the cost of forging the corresponding KEL anchors) — and it **anchors up** to the SEL events and
credentials its members authorize. The layering principle holds throughout: **the chain validates
structure only** — event chaining, the members' anchoring, per-kind schemas — never topic labels or
application semantics, and a chain never reads invalid because of the application it serves
([`../../../../protocol-doctrine.md` §Structural authorization](../../../../protocol-doctrine.md#structural-authorization)).

Like the KEL and SEL, the IEL is a **mixed chain**: tier-1 **content** (`Ixn`, first-seen and
recoverable) rides alongside a tier-2 **sealed** spine (`Evl` / `Ath` / `Rev` / `Dth` / `Wit` /
`Trm`, record-both and terminal-on-divergence). It reuses the KEL's four-state per-node machine, the
seal / locked-portion / seal-cap, and the merge-outcome vocabulary; the mixed-chain nuance is that
only content is buriable, so the same seal machinery separates a recoverable content fork from a
terminal schism.

This doc states the chain primitive: prefix derivation, the per-node chain states, the seal and the
spine over the content window, the locked-portion bound, the down-pins and the role-qualified
manifest, and the page model. Per-kind reference lives in [`events.md`](events.md); merge-handler
routing in [`merge.md`](merge.md); the verifier walk in [`verification.md`](verification.md); the
cross-node correctness proof in [`reconciliation.md`](reconciliation.md); the delegate / rescind
surface in [`delegation.md`](delegation.md).

## Prefix derivation

An IEL inception event is a
[prefix-deriving SAD](../../sad/said.md#chain-inception-events-prefix-deriving-sads): its prefix is
the whole-content digest of the inception body —
[`said.md` §Derivation](../../sad/said.md#derivation) owns the mechanic. What the **IEL** prefix
commits to is the initial **roster**, the **threshold vector**, and a high-entropy **`nonce`**.

The `nonce` makes the IEL prefix **unpredictable** from outside — a camping (prefix-squatting)
defense. Two distinct inception events cannot share a prefix without a Blake3-256 collision, and
because the prefix commits to a random nonce, an outsider cannot compute an identity's prefix from
its roster; an IEL is located only by parties told its prefix. Subsequent events inherit the
inception's `prefix` and derive only `said`.

IEL inception is dispatched by **kind** at `serial = 0`: a **user** identity incepts `Icp`
(federation-bound — it carries `{federation, federationPin}` and its `witnesses` config); a
**federation** identity incepts the restricted `Fcp` marker instead — see
[`events.md` §Two-kind inception](events.md#two-kind-inception). The kind determines the chain's
**root facet**, which the verifier fixes at inception and carries on the verification token —
load-bearing for reading the facet-dependent `Wit` payload (below, and
[`verification.md` §Root facet](verification.md#root-facet-dispatch)).

## Per-node chain states

An IEL is in exactly one of **four** states **on any given node** — Active, Forked, Disputed, or
Terminated — the KEL's machine reused
([`../kel/log.md` §Per-node chain states](../kel/log.md#per-node-chain-states)). Every state is
**computed by a data-local walk** over the events the node holds, never tracked as a separate flag.
A live fork is **two distinct states**: **Forked** (a content-only fork — no accepted sealed branch,
recoverable) and **Disputed** (≥ 2 **accepted** sealed branches — terminal). The walk that tells
them apart (counting the **accepted** sealed branches past the fork) **is** how the state is
computed.

| State          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Accepts new events?                                                                                                                                                                                                                 |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Active**     | Linear chain; the current tip extends cleanly via `previous`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Yes — `Ixn` content, and `Evl` / `Ath` / `Rev` / `Dth` / `Wit` / `Trm` per their threshold and seal-cap requirements.                                                                                                               |
| **Forked**     | A live **content-only** fork (no accepted sealed branch) past it — recoverable; a fork **carrying** an accepted sealed branch has that seal bury the content and reads Active, not a live fork. Origination onto the live fork is frozen. The way forward is a **burying seal** on the winning branch: any non-terminal seal-advancer (`Evl` / `Ath` / `Rev` / `Dth` / `Wit`, typically the `Evl` or the `cut` `Evl` that also evicts) buries the content loser below the new seal and the chain re-reads **Active**; a `Trm` on the winning tip buries the content but the chain goes **Terminated** (tier-rank). A below-seal content straggler is inert, retained as evidence, not a freeze. | Only the resolving event — a burying seal on the winning branch. A second accepted sealed branch joining the fork moves it to **Disputed**.                                                                                         |
| **Disputed**   | A live fork with **≥ 2 accepted sealed branches** past it — proof the quorum was subverted or the witnesses colluded (an honest partition cannot produce it), terminal. No sealed branch can be buried (that would resurrect a retired sealing decision), so nothing resolves it and the identity must **reincept**.                                                                                                                                                                                                                                                                                                                                                                            | None (barring a partition) — witnesses decline any extension of a disputed chain. The only exit is reincept.                                                                                                                        |
| **Terminated** | A terminal `Trm` landed cleanly — the identity is retired and all its SELs freeze. The `Trm` advances the seal to its own serial; the chain is sealed there.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | None. A content sibling to the `Trm` is inert below its seal (`Sealed`); a sealed sibling is a second accepted sealed branch → **Disputed**; a submission chaining from the `Trm` is rejected by the kind-schema rule (`Terminal`). |

Two byte-identical events at one serial **are one event** — they dedupe by SAID, never a second
branch; only distinct events collide. A busy issuer's re-seal `Evl` **redelivered** is exactly this
idempotent case (same ceremony, identical `pins`); two independent re-seal ceremonies carry
different `pins`, so they are byte-distinct and collide instead (§Seal-advance cap). The full
freeze-and-recover rule is the protocol doctrine's —
[§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery).

### Forked versus Disputed — the sealed-branch count

Which state a live fork is in turns on **tier**, read from the data by counting the **sealed**
branches past the fork. The IEL is a mixed chain, so the count discriminates content from sealed
directly:

- **Content (`Ixn`) is buriable.** A content conflict is **recoverable**: the next sealing event on
  the surviving branch buries the loser below the new seal, dead on ascent. Two competing content
  branches carry no sealed branch at all — the content count is irrelevant.
- **Sealed is record-both (detected, never buried).** A threshold chain cannot be forked by one
  stolen key (**except a singleton / `t_use = 1` roster, where one member acts alone**), so a
  **second _accepted_ sealed branch is proof the quorum was subverted or the witnesses colluded** —
  surfaced loudly (a witness-declined sibling is deferred-pending, forcing nothing).
  `{Evl, content}` (one accepted sealed branch) reads **Active** — the `Evl` buries the content
  sibling. `{Evl, Evl}` (two accepted sealed branches) is **Disputed → terminal → reincept**.

So the verdict turns on the number of accepted sealed branches past the fork: **zero → Forked** (a
content-only fork, recoverable), **exactly one → Active** (the sealed branch buries the content
sibling; a terminal `Trm` reads Terminated instead), **two or more → Disputed**. A single sealed
branch you did not author (a quorum takeover) is still your point of no return — reincept — but read
node-agnostically it reads **Active** (a clean sealed tip); an owner's counter-seal then makes it
two → Disputed. The witness beacon **propagates** the branches; the data-local walk **decides** the
verdict. See
[§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison) for how the
reading rides the effective SAID.

## The seal, the spine, and the locked-portion bound

The IEL verifier surfaces one forward-only watermark on its
[`IelVerification`](verification.md#ielverification-token) token, computed from the chain's events.

| Concept                     | Advances on                                   | Used for                                                                                                                                                                                                                                                                                                                                                        |
| --------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `last_seal_advancing_event` | `Evl` / `Ath` / `Rev` / `Dth` / `Wit` / `Trm` | Seal-cap — a new event's parent must sit at-or-after this serial (below is the locked portion; the seal event itself is a legal parent). The **derived seal**: the most recent seal-advancing event with no competing accepted **sealed** sibling (a content sibling is buried below it, not a competitor); computed from the events held, never arrival order. |

Every tier-2 event seals. Only content (`Ixn`) leaves the seal where it was. `Trm` advances the seal
to its own serial, where it is terminal — it opens no new window. `Rev` and `Dth` advance the seal
like any sealing event yet are **non-terminal**: they seal a kill on a _target_ (a downstream SEL /
declaration), not on the host IEL, so the identity continues — a `{Rev, content}` fork is
recoverable exactly like `{Evl, content}` (the `Rev` branch survives, the content is buried).

### The spine

The seal-advancing events form a **spine**: every sealing event carries a top-level
**`previousSeal`** back-link to the prior one, so following `previousSeal` renders a sealed-only
view (`Icp → seal → seal → …`) while `previous` renders the full flat chain. The inception (`Icp` /
federation `Fcp`) is the spine root and carries no `previousSeal`. A sealing event does **not**
commit its content run: the retained run since the prior seal is the derivable linear chain
`[previousSeal..previous]`, and "content was folded here" is the derived predicate
`previous != previousSeal`.

The spine is a **convenience** view — the same chain walk with `previousSeal` substituted for
`previous`, yielding state (the roster and threshold as of a position, the grants and kills sealed)
and a terminal-divergence view (a spine fork is two competing seals — sealed, hence terminal) but
not recoverable content forks. Any decision that turns on a content event uses the **flat** walk; a
skipped seal is caught by the flat walk plus spine-fork detection. The cross-primitive spine / fold
model is the protocol doctrine's —
[§Forks are seal-bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded); the event fields
are the [event-shape reference](../event-shape.md#iel)'s.

### The locked portion

The **locked portion** of an IEL is the segment **below** `last_seal_advancing_event` (strictly —
the seal-advancing event itself is a legal parent: the normal post-seal append extends it). Events
in this segment are structurally immutable within the chain:

- A new event whose `previous` points into the locked portion is **rejected as a canonical
  extension** with `Sealed`. Whether that rejected fork is **retained as non-canonical evidence** is
  a separate, witnessing-gated decision — a losing **content** sibling on a witnessed chain never
  forms (nothing to retain), while a sealed branch is kept, so the proof a sealed divergence
  occurred survives wherever a fork actually forms.
- The seal-cap's role is to deny revival attacks: a member holding stale authority (a rotation
  reserve already revealed by an earlier participation, or a since-evicted membership state) cannot
  construct an event targeting the locked portion to rearrange the chain. Only the current roster's
  threshold gates further extension.

### Pre-seal verifiability

The at-or-below-seal portion is permanently final — for the chain itself (no future event may target
it) and for consumers verifying anchors, credentials, and SEL bindings against it. An identity's
roster and threshold as-of a below-seal position, a credential issued under that state, and a SEL
bound there stay trust-evaluable indefinitely; the permanence claims run against the last **clean**
seal (a **witnessed** sealed fork **at the last seal** flips the reading to `disputed` without
rewriting any sealed event; a below-seal sealed straggler is dropped, inert — backdate-safe). See
[§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery) (_Pre-seal
verifiability_) for the cross-primitive framing.

## Down-pins and the role-qualified manifest

An IEL event carries two structural surfaces beyond its common fields.

**Down-pins (`pins`) — how a threshold of members anchors the event.** An IEL event has no key of
its own; a member participates by authoring a **fresh KEL event at its own current tip** — of
**exactly** the kind that reveals the capability the act exercises (kind-strict: content ← KEL
`Ixn`; a tier-2 governance / kill / terminal act ← KEL `Rot`; the federation binding `Wit` ← KEL
`Wit`) — whose `manifest.anchors` names the IEL event. The IEL event records the **down-pins**: each
participating member's **prior KEL tip** (the event its fresh participation extends —
`participation.previous`), gathered into a small **pins-SAD** named by the top-level scalar `pins`
field. Keeping `pins` top-level means the IEL event's `said` never depends on the anchoring events,
so there is no SAID cycle, and a verifier walks the layered structure without fetching the manifest.
Every IEL event is anchored by a threshold of members, so **every IEL event carries `pins`**. (A
federation `Wit`'s `pins` are the participating witnesses' pre-rotation KEL tips; the SEL analog is
the singular top-level `pin`.)

**The role-qualified manifest.** An IEL event commits to what sits above it through a **`manifest`**
— the SAID of a role-grouped SAD
([event-shape §The manifest](../event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role)).
An IEL event's manifest may carry only these roles; one carrying any role outside its kind's
vocabulary is malformed and rejected, and a role is consumed only after dispatching on a kind
permitted to carry it (read kind-first):

| Role        | Carried by                                       | Commits to                                                                                                                                                                  |
| ----------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `roster`    | `Icp` / `Evl` (user); `Fcp` / `Wit` (federation) | the roster / threshold **delta** SAD (`add` + `cut` + changed thresholds); an `Evl` `cut` also carries the eviction                                                         |
| `anchors`   | `Ixn` / `Evl` / `Ath` / `Rev` / `Dth`            | higher-layer SAIDs this event anchors — SEL v1s and a credential's issuance commitment (`Ixn`), the SEL `Sea` (`Evl`), the SEL `Gnt` (`Ath`), the SEL `Trm` (`Rev` / `Dth`) |
| `delegates` | `Ath`                                            | delegate **prefixes** — a positive inclusion list (the party acts **for** the delegator)                                                                                    |
| `kills`     | `Rev` / `Dth`                                    | the revocation / rescission declaration `[{ target, bound? }]` (below and [`events.md` §Kills](events.md#kills--the-fail-secure-revocation-declaration))                    |
| `witnesses` | `Icp` / `Wit`; `Fcp` / `Wit` (federation)        | the witness-config SAD `{ threshold, signers }`                                                                                                                             |
| `clock`     | `Fcp` / `Wit` / `Trm` (federation)               | the federation-clock timestamp (an inline scalar — the lone non-SAID role)                                                                                                  |

The killed locus is named by `kills[].target` (a flat domain-qualified hash), separate from
`anchors[]` (which names the sealing `Trm`): `anchors` establishes termination validity, `kills`
names _what_ is revoked. The federation `{federation, federationPin}` binding and the up-`pins` stay
**top-level structural**, never a manifest role. See
[`events.md` §The manifest](events.md#the-manifest--roles-an-iel-event-carries) for the per-kind
detail.

## Content window versus sealed spine

Because sealing events advance the seal and content does not, an IEL naturally has two regions
between any two seals: the **content window** (a run of `Ixn` events) and the **seals** that bound
it. This is what the seal-cap sizes and what a burying seal resolves.

- **The content window** is where routine issuance lives — a credential's issuance commitment and
  the SEL events its members author ride `Ixn` (`manifest.anchors`, tier 1). A content fork happens
  here and is recoverable.
- **The sealed spine** is where roster, threshold, delegation, revocation, federation binding, and
  termination live — every one sealed on arrival. A sealed fork is a spine fork, terminal on the
  second **accepted** sealed branch.

## Seal-advance cap

A sealing event (`Evl` / `Ath` / `Rev` / `Dth` / `Wit`; the terminal `Trm` also advances the seal
but ends the chain) must land at least every `MAXIMUM_UNSEALED_RUN` content events **per lineage**.
The cap bounds the content run since the last seal to `MAXIMUM_UNSEALED_RUN` events on each branch,
so the canonical two-branch content fork anchored at the last seal — both lineages (≤
`MAXIMUM_UNSEALED_RUN` each) plus the burying seal — fits one page.
`MINIMUM_PAGE_SIZE = 129 = 2·MAXIMUM_UNSEALED_RUN + 1` is a protocol constant, the same bound as the
KEL and SEL, so a fork-and-recover page produced on any conformant deployment fits on every other.

The cap is **not optional** on the IEL. `Ixn` is content and does not advance the seal, and
**issuance — the frequent operation — rides `Ixn`**, so without the cap the post-seal content window
would grow unbounded and the IEL would face the same recovery-page pressure the KEL / SEL cap
answers. A busy issuer that fills the window **re-seals with a roster-less `Evl`** — a pure re-seal
that **omits `roster`** (the seal advance via `previousSeal` is the change, not an empty
`{add:[], cut:[]}`) — the IEL analogue of the KEL re-sealing via `Rot`, reusing `Evl` with no new
kind and no marker. The **same** re-seal `Evl` redelivered (identical bytes — same ceremony, same
`pins`) **dedupes** by SAID (idempotent); two **independent** re-seal ceremonies carry different
`pins`, so they are byte-distinct and **collide**, not dedupe. A re-seal `Evl` versus a real `Evl`
at one position diverges as `{Evl, Evl}` → terminal when **both are accepted** (an honest race
first-seen-declines the second), exactly as any two sealed events would. Validation must **accept**
a roster-less re-seal `Evl`. See [`events.md` §Seal-advance cap](events.md#seal-advance-cap).

## Page model

Chains are read, verified, written, and replicated in **pages** of bounded size. The page is the
unit of memory budget for the verifier walk, the unit of round-trip for storage reads, and the unit
of atomicity for the merge handler.

- **`MINIMUM_PAGE_SIZE` = 129** — protocol constant; the floor every conformant deployment must
  support. The seal-advance cap — **`MAXIMUM_UNSEALED_RUN` = `(MINIMUM_PAGE_SIZE − 1)/2` = 64** per
  lineage — is derived from it so a two-branch fork-and-recover page produced anywhere validates
  anywhere.
- **Page boundaries align with generations.** A generation is the set of events at the same serial.
  The verifier processes events in generation order (`serial ASC, kind sort_priority ASC, said ASC`)
  and re-fetches an incomplete generation at the next page boundary, so a divergent generation
  spanning two pages is never processed half-observed.
- **Deterministic intra-generation ordering.** Per-kind `sort_priority` (see
  [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)) breaks intra-generation
  order so all nodes process the same batch identically. The `said` tiebreaker is for determinism
  only and carries no semantic meaning.

The verifier's `max_pages` cap (default 64 pages ≈ 8K events; configurable via env var) caps
resource use even on adversarial chains.

## The two facets — user and federation

One IEL kind set spans two structurally distinct chains, dispatched by the **root facet** the
inception fixes:

- A **user IEL** roots at `Icp` and uses all eight kinds. It is federation-bound (its `Icp` carries
  `{federation, federationPin}`), its content is majority-witnessed at its own position (the
  **position gate**, [`merge.md`](merge.md#the-content-versus-sealed-split)), and its `Wit` is the
  federation **rebind**.
- A **federation IEL** roots at the `Fcp` marker and uses the restricted set `Fcp` / `Wit` / `Trm`
  only — its roster is witness KELs directly, it authors no content, and its `Wit` is **governance**
  (roster + rotation + clock). Every federation event is sealed → record-both; a competing sealed
  sibling is first-seen-declined (exclude-self peer-witnessing), so only a witness-colluded
  two-accepted conflict is a schism (disputed / terminal).

The `Fcp` marker is a **structural disambiguator the verifier dispatches on, not a trust carve-out**
— the config-pinned federation prefix still roots trust. The facet governs which roles a `Wit` may
carry and how its fields are matched, so the verifier **establishes the root facet before reading
any `Wit` payload** on every `Wit`-reading path — no path is exempt (see
[`events.md` §The facet-dependent `Wit`](events.md#the-facet-dependent-wit) and
[`verification.md` §Root facet](verification.md#root-facet-dispatch)). The federation IEL is a
restricted IEL detailed here only where the primitive differs; the federation-witnessing mechanics
(the beacon, the witnessing floor, the clock, witness selection) are federation doctrine —
[`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md).

## End-verifiability

The IEL's contribution to end-verifiability over data-from-any-source is two structural properties.
Whole-content prefix derivation with a random `nonce` makes the inception tamper-evident and the
prefix unpredictable, and locked-portion immutability under the seal-cap means events at-or-below
`last_seal_advancing_event` cannot be rearranged by any future event — so an identity's roster and
threshold as-of a below-seal position, and every credential and SEL binding resolving to it, stay
structurally trustworthy indefinitely. Authority never rests on a service, a database, or a peer: an
IEL event authenticates by resolving **down** to a threshold of member KEL signatures, and every one
of those is re-checked from the data. The cross-primitive framing (verify the data, not the source)
is canonical in
[`../../../../system-thesis.md` §End-verifiability](../../../../system-thesis.md#end-verifiability).

## Cross-references

- [`../event-shape.md`](../event-shape.md#iel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind field grid.
- [`events.md`](events.md) — per-kind reference: the eight-kind user IEL and restricted federation
  IEL, the two tiers, the threshold vector and its bounds, kind-strict anchoring, the `kills[]`
  declaration, the facet-dependent `Wit`.
- [`merge.md`](merge.md) — merge-handler routing for the mixed chain: content first-seen, sealed
  record-both, burying-seal recovery, eviction, facet dispatch.
- [`verification.md`](verification.md) — the verifier walk: threshold anchoring, roster
  accumulation, root facet, the bounded delegation walk, the `kills[]` forward-match.
- [`reconciliation.md`](reconciliation.md) — the exhaustive cross-node correctness proof.
- [`delegation.md`](delegation.md) — the delegate / rescind surface (`Ath` / `Dth`).
- [`../kel/log.md`](../kel/log.md) — the KEL chain primitive this reuses (states, seal, spine, page
  model); IEL events anchor in KEL events.
- [`../../sad/sad.md`](../../sad/sad.md), [`../../sad/said.md`](../../sad/said.md) — the SAD shape
  IEL events compose on; prefix and SAID derivation.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — tiers and kind-strict
  anchoring, divergence and recovery, forks-are-seal-bounded and the spine, federation convergence,
  the layering principle.
- [`../sel/`](../sel/) — SEL primitive. IEL events anchor SEL events and credentials.
- [`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md)
  — federation witnessing: the beacon, the witnessing floor, the clock, witness selection,
  acceptance gating.
