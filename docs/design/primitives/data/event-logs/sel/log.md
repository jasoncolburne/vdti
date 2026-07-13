# SEL — SAD Event Log

The **SAD Event Log** (SEL) is a **single-owner data log** — a per-owner chain of
cryptographically-linked events recording one owner's data over time. Its owner is exactly one
**identity**, named by that identity's [IEL](../iel/log.md) prefix and fixed for the SEL's whole
life. A SEL composes no policy, no roster, and no multi-party governance of its own; it pins and
anchors **only its IEL**. Each event is a [SAD](../../sad/sad.md) carrying chain-linkage fields
(`prefix`, `previous`, `serial`, `kind`) plus kind-specific commitments; a SEL event carries **no
signature of its own** — like an IEL event, it authenticates through its anchor. The per-kind field
shape is the cross-primitive [event-shape reference](../event-shape.md#sel); this doc and its
siblings state the SEL-specific doctrine.

The SEL sits above the IEL. It **is anchored by** its IEL — every SEL event is committed by one of
the owner's IEL events (`manifest.anchors`), and the required count is set by the SEL event's own
kind, drawn from the IEL's threshold vector and delivered by that anchoring IEL event's member
participations
([`../event-shape.md` §Authentication & signatures](../event-shape.md#authentication--signatures)).
So a SEL hosts no authority machinery: the **owner IEL is the SEL's clock and its authority**. The
layering principle holds throughout — the chain validates **structure only** (event chaining, the
owner's anchoring, per-kind schemas), never topic labels or application semantics, and a chain never
reads invalid because of the application it serves
([`../../../../protocol-doctrine.md` §Structural authorization](../../../../protocol-doctrine.md#structural-authorization)).

Like the KEL and IEL, the SEL is a **mixed chain**: tier-1 **content** (`Ixn` and the floor `Pin`,
first-seen and buriable) rides alongside tier-2 **sealed** events (`Gnt` / `Trm`, sealed on arrival
and never overturned). Two things distinguish it from the IEL. First, a SEL is **rooted in and
anchored to its IEL** — it has no key state and no roster to accumulate; its state is the data it
records and the pin that floors it. Second, a **plain content SEL never self-seals**: with no `Gnt`
or `Trm` it holds no seal of its own, so its trust-finality **floors to the IEL** through a
down-pin, and a content fork on it resolves **cross-layer** — the IEL's burying seal drops the loser
and the dead line descends across the anchor edge.

This doc states the chain primitive: prefix derivation, the lookup-versus-content distinction, the
per-node chain states, the seal-advancers and the trust-finality floor, the down-pin, and the two
cross-layer rules that make the IEL the SEL's clock. Per-kind reference lives in
[`events.md`](events.md); merge-handler routing in [`merge.md`](merge.md); the verifier walk in
[`verification.md`](verification.md); the cross-layer correctness proof in
[`reconciliation.md`](reconciliation.md).

## Prefix derivation

A SEL inception event (`Icp`) is a
[prefix-deriving SAD](../../sad/said.md#chain-inception-events-prefix-deriving-sads): its prefix is
the whole-content digest of the inception body —
[`said.md` §Derivation](../../sad/said.md#derivation) owns the two-hash mechanic (`prefix ≠ said`,
for correlation resistance). What the **SEL** prefix commits to is the populated inception fields:

- **`owner`** — the IEL prefix. It is **`Icp`-only and immutable**: a SEL has one owner for life,
  and no later event may change it.
- **`topic`** — an application discriminator (the SEL's namespace or schema). Together `owner` +
  `topic` + derivation **locate a SEL directly**: its address is a function of its content, so a SEL
  is found by re-deriving or being handed its prefix, with no separate registry object to consult.
- **`data`** — optional. It is the recompute input a lookup SEL roots on (below): a private nonce,
  or discoverable / recomputable bytes such as a grant-instance reference.

The prefix is the **whole-content digest of the inception body**, exactly like every chain's prefix
— **not** a hash of a separate `(owner, topic, data)` tuple. Because any field on the `Icp` enters
the prefix, the `Icp` carries **no `pin` and no manifest**: adding either would change the prefix
and break the recomputation a lookup SEL depends on. The `Icp` is therefore unsigned, recomputable
content — it proves nothing on its own (see
[§Authentication rides the v1](#authentication-rides-the-v1)).

### The `data`-entropy rule

Whether `data` must be high-entropy depends on why the prefix must be hard to predict:

- **A private SEL** derives an **unpredictable** prefix from `data` — the nonce that keeps the SEL's
  location unguessable. That `data` **must be high-entropy**. Otherwise an attacker brute-forces it,
  recomputes the prefix, and de-anonymizes the SEL. Digesting low-entropy `data` does not help — a
  hash of a guessable input is still guessable, so the **input** must carry the entropy.
- **A discoverable lookup SEL** uses `data` a verifier can recompute (a grant-instance reference),
  so unpredictability is **not** the goal. Its protection is **owner-rooting**: only the IEL anchors
  events at that locus, so predicting the address is not forging one — prediction ≠ forgery.

## Lookup SEL versus content SEL

A SEL is classified by **blind-recomputability**, not by whether its data is discoverable:

- A **lookup SEL** is one whose prefix a verifier **blind-recomputes** —
  `derive(owner, topic, data)` — from data it already holds, then fetches by that prefix. Its `data`
  is the recompute input (a grant-instance reference), and its shape is `{Icp, Trm}`: the terminal
  `Trm` is a kill (§The seal-advancers). Lookup SELs are the structure the fail-secure revocation
  and rescission reads consume.
- A **content SEL** is one a verifier is **handed** rather than re-deriving. It records data over
  time (`Icp` → serial-1 event → further `Ixn`s).

A **credential is neither** — it is not a SEL at all, but a direct-anchored immutable SAD (its
issuance is a commitment anchored on the issuer's IEL by an `Ixn`, and that anchor is the validity
proof). The credential feature, and the read strategy that consumes the lookup-SEL structure, are
the feature layer's — [`../../../../features/credentials/`](../../../../features/credentials/)
_(forthcoming)_; this primitive states only the lookup-SEL **structure**.

## Per-node chain states

A SEL is in exactly one of **four** states **on any given node** — Active, Forked, Disputed, or
Terminated — the same machine the KEL and IEL use
([`../iel/log.md` §Per-node chain states](../iel/log.md#per-node-chain-states)). Every state is
**computed by a data-local walk** over the events the node holds, never tracked as a separate flag.
The difference on a SEL is **where the fork resolves**: a plain content SEL holds no seal of its
own, so a content fork on it is resolved by the **owner IEL** (§The owner IEL is the SEL's clock),
and the verdict is read from the number of **accepted sealed** branches past the fork — a lens the
theorem below makes exact.

| State          | Description                                                                                                                                                                                                                                    | Accepts new events?                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Active**     | Linear chain; the tip extends cleanly via `previous`, each event anchored on the IEL.                                                                                                                                                          | Yes — `Ixn` / `Pin` content, and `Gnt` / `Trm` per their anchor and count requirements.                               |
| **Forked**     | A live content fork with **≤ 1 accepted sealed branch** past it — recoverable. A plain content fork carries no sealed branch and resolves cross-layer: the IEL's burying seal drops the losing anchor and the SEL loser dies by descent.       | Only the cross-layer resolution (the IEL buries its fork). A second accepted sealed branch would move it to Disputed. |
| **Disputed**   | A live fork with **≥ 2 accepted sealed branches** past it — which, by the theorem, means the **IEL forked with two accepted sealed branches beneath it** (quorum subversion or witness collusion). Terminal; the owner reincepts.              | None. The only exit is reincept of the owner.                                                                         |
| **Terminated** | A `Trm` kill landed — the SEL is closed. A `Trm` advances the SEL's seal to its own serial and admits no successor; a content sibling to it is buried by tier-rank. When the **IEL** terminates (its `Trm`), **all its SELs freeze** likewise. | None. A content sibling to the `Trm` is buried; a submission chaining from a `Trm` is rejected.                       |

Two byte-identical SEL events at one serial **are one event** — they dedupe by SAID, never a second
branch; only distinct events collide. The cross-primitive freeze-and-recover rule is the protocol
doctrine's — [§Divergence and recovery](../../../../protocol-doctrine.md#divergence-and-recovery).

## The seal-advancers and the trust-finality floor

A SEL's tier-2 kinds — **`Gnt`** (grant) and **`Trm`** (kill) — are its **seal-advancers**. Each
carries a top-level `previousSeal` back-link and renders a **spine** on the SEL, exactly as the
sealing kinds do on a KEL or IEL, and caps the SEL's local divergence window at its own serial. The
tier-1 kinds — content **`Ixn`** and the floor **`Pin`** — do not advance the seal; they sit in the
unsealed window until the SEL's next `Gnt` / `Trm`, buriable until then.

The load-bearing difference from the KEL and IEL is what a **plain content SEL** — one with no `Gnt`
or `Trm` — does for finality. It never self-seals, so it holds **no trust-seal of its own**. Instead
its **trust-finality floors to the IEL's seal**, through the down-pin every content event carries:
the SEL is trust-final exactly as far as the IEL event it pins to is sealed. A content fork on such
a SEL resolves **cross-layer** (§The owner IEL is the SEL's clock) — the owner IEL's burying seal
drops the loser — rather than by a SEL-local burying seal.

A **kill** (`Trm`), by contrast, is sealed on arrival (anchored by an IEL `Rev` / `Dth`),
owner-proof immediately and terminal-on-divergence — it can never be un-done. Where a `Trm` competes
with content at one SEL position, the `Trm` is the single sealed branch and **wins on tier-rank**:
the kill stands and the content buries non-canonical (`{Trm, Ixn}`), the SEL analogue of the IEL's
`{Trm, content}`. A `Gnt` is likewise sealed and non-buriable — walked back only by a later
rescission (a `Trm` under a `Dth`) or by reincept, never overturned.

## The down-pin and the manifest

A SEL event carries two structural surfaces beyond its common fields.

**The down-pin (`pin`) — how a SEL floors to its IEL.** Every non-inception SEL event carries a
top-level scalar **`pin`**: the SAID of the IEL event this SEL floors down to. The floor is a chain
link, not a self-asserted claim — a serial-1 event's `pin` equals its anchoring IEL event's
`previous` (the SEL extends the IEL's tip as it stood), and each `Ixn` re-pins forward. The `Icp`
carries **no `pin`** (it must stay recomputable — §Prefix derivation), so the first pin rides the
SEL's **serial-1 event** (its _v1_), never the `Icp`.

**The role-qualified manifest.** A SEL event commits to what sits above or beside it through a
**`manifest`** — the SAID of a role-grouped SAD
([event-shape §The manifest](../event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role)).
A SEL event may carry only these roles; one carrying any role outside its kind's vocabulary is
malformed and rejected (read kind-first):

| Role      | Carried by | Commits to                                                           |
| --------- | ---------- | -------------------------------------------------------------------- |
| `content` | `Ixn`      | the content-SAD SAID(s) this `Ixn` records (single-owner data)       |
| `grant`   | `Gnt`      | the gated grant-doc SAD a doc-membership grant opens                 |
| `anchors` | `Trm`      | the higher-layer SAID(s) a `Trm` commits (a kill's committed target) |

The `Icp` (recomputable) and the floor `Pin` (a pure re-pin) carry **no manifest**. The `owner` /
`topic` / `data` derivation inputs and the down-`pin` stay **top-level structural**, never a
manifest role. See [`events.md` §The manifest](events.md#the-manifest--roles-a-sel-event-carries)
for the per-kind detail.

## The owner IEL is the SEL's clock

A SEL is anchored to its IEL (kind-strict — content `Ixn` rides an IEL `Ixn`, a `Gnt` an IEL `Ath`,
a `Trm` an IEL `Rev` / `Dth`; [`events.md`](events.md#the-kind-strict-cross-layer-anchor-matrix)),
and the IEL is what totally-orders it. Two cross-layer rules govern the edge; both are stated here
and enforced in [`verification.md`](verification.md).

- **Anchor-monotonicity.** A SEL event is valid **only if it extends its SEL's latest IEL-anchored
  tip** — the tip computed over the IEL's **canonical / retained walk**. The anchor SAID is opaque,
  so an anchor whose body a node cannot **attribute** (it lacks the body) is **skipped, not
  blocking** (_skip-unattributable_) — a withheld, lost, or private anchor body never wedges the
  SEL. A re-anchor at an **already-attributed** SEL serial is malformed → the SEL event is **inert**
  (the carrying IEL event stays valid; an inert anchor never advances the tip). So a node appending
  to a **linear** IEL always extends each SEL correctly.
- **Cross-layer deadness-descends.** A SEL event whose anchoring IEL event is dead (condemned or
  buried below the IEL's seal) is **itself dead** — the **IEL → SEL** anchor edge only, never the
  KEL → IEL edge (which is forward-only).

Together they give the **theorem**: **a valid SEL fork implies an IEL fork beneath it**. A SEL
**never forks under a linear IEL** (skip-unattributable prevents any wedge), and every genuine SEL
fork rides an IEL fork — resolved by the IEL's burying seal, the losing SEL events dying by descent
across the anchor edge. Content-fork prevention on a witnessed SEL **rides this theorem**: a
witnessed SEL content fork would force its two same-serial siblings to anchor at content siblings at
one IEL position, which the IEL's witnessing floor prevents, so a witnessed SEL content fork carries
the **same fork-cost** as its IEL's and needs **no SEL-local witness gate** (the witnessing floor is
over the IEL's witness signers — federation doctrine,
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md), forthcoming). The
proof and its case matrix are [`reconciliation.md`](reconciliation.md).

A consequence is that a **signing-key (tier-1) compromise is fully deadenable**: a signing key can
author content but has no rotation reserve, so it can mint **no sealed SEL `Trm`**; one **IEL
rotation** (a plain `Rot` that buries the forked content tail) leaves the whole anchored content
tail dead by descent, with **no reincept** — see
[`reconciliation.md` §The tier-1 compromise is fully deadenable](reconciliation.md#the-tier-1-compromise-is-fully-deadenable).

## Authentication rides the v1

A SEL's `Icp` is unsigned, recomputable content, so it proves nothing on its own — a fabricated bare
`{Icp}` naming a victim owner is **not** evidence the owner authored anything. A SEL is validly
established **only** if its **serial-1 event (its v1)** resolves to a real event on the **claimed
owner's** IEL: the v1 is named in that IEL event's `manifest.anchors`, its `pin` links to the
anchoring position, and the anchoring IEL prefix equals the SEL's `owner`. A SEL whose v1 is absent,
or whose v1-anchor sits on a different owner, is rejected. The `Icp` rides via `v1.previous`; it is
**never itself anchored**. The v1 is a bare **`Pin`** when inception carries no other first event
(an issue-and-sit SEL), a `Trm` for a born-to-kill lookup SEL, or the first content `Ixn` otherwise.
See [`events.md` §Inception and the serial-1 floor](events.md#inception-and-the-serial-1-floor).

## Page model

Like the KEL and IEL, a SEL is read, verified, written, and replicated in **pages** of bounded size
— the unit of memory budget for the verifier walk, the round-trip for storage reads, and the
atomicity for the merge handler.

- **`MINIMUM_PAGE_SIZE` = 129** — the same protocol constant every conformant deployment supports,
  so a page produced anywhere validates anywhere.
- **Page boundaries align with generations.** A generation is the set of events at one serial; the
  verifier processes events in generation order (`serial ASC, kind sort_priority ASC, said ASC`) and
  re-fetches an incomplete generation at the next boundary, so a divergent generation spanning two
  pages is never processed half-observed. The per-kind `sort_priority` is
  [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority); the `said` tiebreaker is
  for determinism only and carries no meaning.

Because a plain content SEL's fork resolution is **cross-layer** — the IEL buries the fork — the
bounded region a fork's resolution touches is the IEL's
([`../iel/log.md` §Page model](../iel/log.md#page-model)). The verifier's `max_pages` cap (default
64 pages ≈ 8K events; configurable) caps resource use even on adversarial chains.

## End-verifiability

The SEL's contribution to end-verifiability over data-from-any-source is two structural properties.
Whole-content prefix derivation lets a lookup SEL's holder **re-derive its address** from data it
already holds and fetch it **by prefix** — no global SAID index, no trusted directory — so a
credential's revocation status or a delegate's rescission is located from the held reference alone.
And the owner-anchoring means a SEL event's authority never rests on a service, a database, or a
peer: it authenticates by resolving **down** to the IEL event that anchors it, and thence to a
threshold of member KEL signatures, every one re-checked from the data. The cross-primitive framing
(verify the data, not the source) is canonical in
[`../../../../system-thesis.md` §End-verifiability](../../../../system-thesis.md#end-verifiability).

## Cross-references

- [`../event-shape.md`](../event-shape.md#sel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind SEL field grid.
- [`events.md`](events.md) — per-kind reference: the five kinds, the three orthogonal axes, the
  threshold vector, kind-strict cross-layer anchoring, the recomputable `Icp`, the floor `Pin`, the
  `Gnt` grant, the `Trm` kill.
- [`merge.md`](merge.md) — merge-handler routing: content first-seen, `Gnt` / `Trm` sealed on
  arrival, cross-layer fork resolution, anchor-monotonicity, cross-layer deadness-descends.
- [`verification.md`](verification.md) — the verifier walk: anchor-monotonicity over the IEL walk,
  the cross-layer deadness read, lookup-SEL two-pass derivation, the `Trm` kill structure.
- [`reconciliation.md`](reconciliation.md) — the exhaustive cross-layer correctness proof: the
  theorem, the verdict by sealed-branch count, the tier-1-fully-deadenable result.
- [`../iel/log.md`](../iel/log.md) — the IEL: the chain that anchors this SEL and is its clock; the
  four-state machine, seal, and page model this reuses.
- [`../kel/log.md`](../kel/log.md) — the KEL chain primitive the machine originates in.
- [`../../sad/sad.md`](../../sad/sad.md), [`../../sad/said.md`](../../sad/said.md) — the SAD shape
  SEL events compose on; two-hash prefix and SAID derivation.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — structural authorization,
  tiers and kind-strict anchoring, divergence and recovery, the layering principle.
- [`../../../../features/credentials/`](../../../../features/credentials/) — the credential feature
  (forthcoming): a credential is a direct-anchored SAD, not a SEL; it consumes the lookup-SEL
  structure for revocation.
- [`../../../../features/shared-documents/documents.md`](../../../../features/shared-documents/documents.md)
  — the doc-membership grant a `Gnt` opens (forthcoming).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor the content-fork-prevention theorem cites.
