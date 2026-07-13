# SEL — SAD Event Log

The **SAD Event Log** (SEL) is a **single-owner data log** — a per-owner chain of
cryptographically-linked events recording one owner's data over time. Its owner is exactly one
**identity**, named by that identity's [IEL](../iel/log.md) prefix and fixed for the SEL's whole
life. A SEL composes no policy, no roster, and no multi-party governance of its own; it pins and
anchors **only its owner IEL**, and its finality floors down to that IEL. Each event is a
[SAD](../../sad/sad.md) carrying chain-linkage fields (`prefix`, `previous`, `serial`, `kind`) plus
kind-specific commitments. The per-kind field shape is the cross-primitive
[event-shape reference](../event-shape.md#sel); this doc and its siblings state the SEL-specific
doctrine.

A SEL relates to its owner IEL in two distinct ways, and keeping them apart is the heart of the
model:

- **It is anchored by the owner IEL.** Every SEL event is committed by one of the owner's IEL events
  (`manifest.anchors`), which supplies two things: the **owner's authorization** (a SEL has no key
  of its own — the anchoring IEL event carries the members' threshold) and the **finality floor**
  (the down-pin to the owner IEL,
  [`../iel/log.md` §Pre-seal verifiability](../iel/log.md#pre-seal-verifiability)).
- **It is its own witnessed chain.** Fork-prevention and fork-detection are the SEL's **own**
  witnessing at its **own position** — not the owner IEL's. The anchor cannot prevent a SEL fork
  (below), so witnessing does.

The layering principle holds throughout: the chain validates **structure only** (event chaining, the
owner's anchoring, per-kind schemas), never topic labels or application semantics, and a chain never
reads invalid because of the application it serves
([`../../../../protocol-doctrine.md` §Structural authorization](../../../../protocol-doctrine.md#structural-authorization)).

Like the KEL and IEL, the SEL is a **mixed chain**: tier-1 **content** (`Ixn` and the floor `Pin`,
first-seen and buriable) rides alongside tier-2 **sealed** events (`Gnt` / `Trm` / `Sea`, sealed on
arrival and never overturned). It reuses the KEL and IEL's four-state per-node machine, the seal /
spine / locked-portion, and the merge-outcome vocabulary.

This doc states the chain primitive: prefix and lineage derivation, the lookup-versus-content
distinction, the per-node chain states, the SEL's own witnessing, the seal and its advancers, the
severance a dead owner-IEL anchor causes, the down-pin, and inception. Per-kind reference lives in
[`events.md`](events.md); merge-handler routing in [`merge.md`](merge.md); the verifier walk in
[`verification.md`](verification.md); the cross-node correctness proof in
[`reconciliation.md`](reconciliation.md).

## Prefix derivation

A SEL inception event (`Icp`) is a
[prefix-deriving SAD](../../sad/said.md#chain-inception-events-prefix-deriving-sads): its prefix is
the whole-content two-hash digest of the inception body —
[`said.md` §Derivation](../../sad/said.md#derivation) owns the mechanic (`prefix ≠ said`, for
correlation resistance). What the **SEL** prefix commits to is the populated inception fields —
shorthand `derive(owner, topic, data)`:

- **`owner`** — the owner IEL prefix. It is **`Icp`-only and immutable**: a SEL has one owner for
  life, and no later event may change it.
- **`topic`** — an application discriminator (the SEL's namespace or schema), opaque bytes to the
  chain. Together `owner` + `topic` + derivation **locate a SEL directly**: its address is a
  function of its content, so a SEL is found by re-deriving or being handed its prefix, with no
  separate registry object to consult.
- **`data`** — optional. The recompute input a discoverable SEL roots on: a private nonce, or
  meaningful bytes such as a kill locus's grant-instance reference.
- **`lineage`** — present only on a re-incepted lookup SEL (§The lineage field). Absent means
  lineage zero.

The prefix is the **whole-content digest of the inception body**, so any populated `Icp` field
enters it. Because of that the `Icp` carries **no `pin` and no manifest**: either would change the
prefix and break the recomputation a lookup SEL depends on. The `Icp` is therefore unsigned,
recomputable content — it proves nothing on its own, so authentication rides its serial-1 event
(§Inception).

### The `data`-entropy rule

Whether `data` must be high-entropy depends on why the prefix must be hard to predict:

- **A private SEL** derives an **unpredictable** prefix from `data` — the nonce that keeps its
  location unguessable. That `data` **must be high-entropy**. Otherwise an attacker brute-forces it,
  recomputes the prefix, and confirms or de-anonymizes the locus. Digesting low-entropy `data` does
  not help — a hash of a guessable input is still guessable, so the **input** must carry the
  entropy.
- **A discoverable SEL** uses `data` a verifier can recompute (a grant-instance reference), so
  unpredictability is not the goal. Its protection is **owner-rooting**: only the owner IEL anchors
  events at that locus, so predicting the address is not forging one.

### The lineage field

A discoverable lookup SEL has a prefix that is a pure function of fixed inputs, so it **cannot
re-incept by rerolling randomness** — the same inputs recompute the same address. `lineage` is a
monotonic counter that gives it a fresh address: lineage zero omits the field; a re-incept adds
`lineage: 1`, `lineage: 2`, and so on, each a distinct whole-content and so a distinct prefix. The
**canonical instance is the lowest non-dead lineage**; anything above a live one is inert (an
equivocation attempt fails safe, since only the owner anchors at the locus). The verifier's uniform,
meaning-blind walk over the lineages — and why it is load-bearing for a published value but inert
for a kill — is [`verification.md` §The lineage walk](verification.md#the-lineage-walk).

## Lookup SEL versus content SEL

A SEL is classified by **whether a verifier can recompute its address**, not by whether its data is
discoverable:

- A **lookup SEL** is one whose prefix a verifier **recomputes** — `derive(owner, topic, data)` —
  from data it already holds, then fetches by that prefix. Two shapes: a **kill lookup**
  `{Icp, Trm}` (a revocation or rescission locus — the read strategy the fail-secure kill check
  consumes) and a **value lookup** `{Icp, Gnt}` (a published value such as an encryption receive-key
  — §The seal and its advancers).
- A **content SEL** is one a verifier is **handed** rather than recomputing. It records data over
  time (`Icp` → serial-1 event → further `Ixn`s).

A **credential is neither** — it is not a SEL at all, but a direct-anchored immutable SAD (its
issuance is a commitment anchored on the issuer's IEL by an `Ixn`, and that anchor is the validity
proof). The credential feature and the kill read strategy live at the feature layer
([`../../../policy/documents.md`](../../../policy/documents.md)); this primitive states only the
lookup-SEL **structure**.

## Per-node chain states

A SEL is in exactly one of **four** states **on any given node** — Active, Forked, Disputed, or
Terminated — the machine the KEL and IEL reuse
([`../iel/log.md` §Per-node chain states](../iel/log.md#per-node-chain-states)). Every state is
**computed by a data-local walk** over the events the node holds, never tracked as a separate flag.
A SEL's state has **two independent inputs**, composed by the rule that deadness comes first
(§Severance):

1. **Its own witnessed divergence** — a content fork (which only forms under witness compromise) is
   recovered by a burying seal-advancer; two accepted sealed branches are Disputed.
2. **Inherited owner-IEL deadness** — a SEL event anchored on a dead owner-IEL branch **severs** the
   SEL there.

| State          | Description                                                                                                                                                                                                                      | Accepts new events?                                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Active**     | Linear chain; the tip extends cleanly via `previous`, each event witnessed and owner-IEL-anchored.                                                                                                                               | Yes — `Ixn` / `Pin` content, and `Gnt` / `Trm` / `Sea` per their anchor and count requirements.                                |
| **Forked**     | A live content fork — witnesses declined it, so it only forms under witness compromise. Recoverable: a burying seal-advancer (`Gnt` / `Trm` / `Sea`) on the winning branch drops the loser below the new seal.                   | Only the resolving event — a burying seal-advancer on the winning branch. A second accepted sealed branch → Disputed.          |
| **Disputed**   | A live fork with **two or more accepted sealed branches** — proof the witnesses colluded (an honest split cannot produce it). No sealed branch can be buried, so the owner must **re-incept** (a lookup SEL at a fresh lineage). | None (barring a partition) — witnesses decline any extension.                                                                  |
| **Terminated** | A terminal `Trm` landed cleanly — the SEL is retired. `Trm` advances the seal to its own serial and admits no successor.                                                                                                         | None. A content sibling to the `Trm` is buried below its seal; a sealed sibling is a second accepted sealed branch → Disputed. |

Two byte-identical events at one serial **are one event** — they dedupe by SAID, never a second
branch; only distinct events collide. **Severed** is not a fifth state — it shrinks the SEL to its
last live-anchored event, after which the chain reads one of the four above.

## The SEL is its own witnessed chain

An owner-IEL anchor **cannot** prevent a SEL fork, so the SEL witnesses itself. The reason is
structural: an IEL anchor is an **opaque SAID** — it names the SEL event by digest, so a private
lookup SEL's body never reaches the IEL. So **one IEL `Ixn` can name two competing SEL events** at
one `(SEL-prefix, serial)` in its anchors, and the IEL cannot tell they conflict — two opaque
digests look unrelated. A node that holds only the first attributes it as the tip and, skipping the
anchor whose body it lacks, never sees the second; a node that holds only the second reads the
second. Both see a **linear** owner IEL and a **single** tip — but **different** tips. An owner can
therefore equivocate its own SEL under a linear owner IEL, which is exactly what witnessing must
close. (SELs are one-to-many with IELs, so a SEL's divergence is not a function of the owner IEL's.)

The SEL is a witnessed chain in the IEL's mold, **inheriting the owner IEL's federation** — the same
witnesses, no new trust root; witness selection is deterministic on `(SEL-prefix, serial)` and the
inherited roster, and the SEL inherits the owner IEL's witness-config and federation binding. The
mechanics are the federation's, applied at the SEL's own position
([`../../../../federation/witnessing.md`](../../../../federation/witnessing.md)):

- **Content (`Ixn` / `Pin`) is first-seen** — a selected witness signs the first content event at a
  position and declines the copies. With the **witnessing floor** (a strict majority of the selected
  witnesses must sign), two content siblings cannot both reach the acceptance threshold, so a
  content fork **cannot form** — it is prevented, not detected. The residual is a **witness
  compromise** that owns the whole quorum intersection; such a fork reads Forked (a fail-secure
  reading) and is resolved by a burying seal-advancer.
- **Sealed events (`Gnt` / `Trm` / `Sea`) are first-seen too, and retained for detection** — a
  witness signs the first sealed sibling and declines later ones, yet every branch is retained so
  the data-local walk sees two. A sealed branch is never buriable, so a **second accepted sealed
  branch is Disputed** — it requires a strict majority of witnesses to double-sign, which is
  provable collusion. A witness-**declined** sealed sibling reaches no threshold and is held
  pending, forcing nothing.

**Anchoring and witnessing ride one batch, so witnessing also closes authorship-forgery.** A SEL
event is committed only together with its owner-IEL anchor: it is event-kinded, so it cannot enter
the plain SAD store, and an `Icp` is not valid without its anchored serial-1 event (§Inception). The
batched anchor is an owner-signed IEL event the witness validates as part of its ordinary job, so
**acceptance requires owner-authorization** — a non-owner produces no valid anchor, so nothing lands
at any locus. Witnessing thus closes both threats: **equivocation** (first-seen at the SEL position)
and **authorship-forgery** (the owner-signed anchor rides the batch). A verifier still re-derives
the prefix and re-checks the anchor against the data it holds — trusting the data, not the witness —
as its independent end-verifiability check
([`verification.md` §Owner-rooting](verification.md#owner-rooting--the-authentication-check)).

**Witnesses see the SEL's structural fields — including a lookup SEL's prefix — as acceptable
trust-infrastructure exposure.** Witnessing a SEL puts its structural fields onto the witness mesh,
but that mesh is **encrypted** and reaches **federation members only**, who are semi-trusted
infrastructure (trusted not to be broadly compromised, never trusted for end-verifiability). A
lookup SEL's prefix is an unguessable value decorrelated from a credential's issuance commitment and
kill target, so a witness holding it can only confirm a subject it already suspects, never invert or
enumerate; and a private lookup SEL's data-bearing `Icp` is **never published**, so no credential
secret reaches a witness. The residual is a witness compromised before its compromise is detected
exfiltrating the structural data it holds — bounded by detection-and-eviction and by the prefixes
being unguessable, the same class as the federation's accepted trust assumption.

## The seal and its advancers

A SEL's tier-2 kinds — **`Gnt`** (grant), **`Trm`** (kill), and **`Sea`** (re-seal) — are its
**seal-advancers**. Each carries a top-level `previousSeal` back-link and renders a **spine** on the
SEL, as the sealing kinds do on a KEL or IEL. **Any of the three buries a content fork** by
advancing the seal past the loser — the loser's first event locks below the new seal and its growth
is dead. The tier-1 kinds — content **`Ixn`** and the floor **`Pin`** — do not advance the seal;
they sit in the unsealed window, buriable until the next seal-advancer.

The three advancers differ by what else they do:

- **`Gnt`** seals a **typed value** — a published value a third party depends on. Its
  `manifest.grant` names a grant-value SAD, and a **value lookup SEL** is established `{Icp, Gnt}`:
  the value rides a sealed event, never tier-1 content, because a value a sender encrypts to must
  not be swappable by a bare signing key. Rotating the value stacks another `Gnt` (the live sealed
  tip is served); the value-bearing instances (a document-governance grant, an encryption
  receive-key) are the feature layer's
  ([`../../../../features/shared-documents/documents.md`](../../../../features/shared-documents/documents.md),
  [`../../../../features/exchange/exchange.md`](../../../../features/exchange/exchange.md), both
  forthcoming). A `Gnt` is non-terminal and is walked back only by a later rescission, never
  overturned.
- **`Trm`** is the **kill** — a revocation or rescission. It is terminal: it advances the seal to
  its own serial and admits no successor, so it buries a content sibling by winning as the sole
  sealed branch. A `Trm` is monotone and can never be un-done.
- **`Sea`** is the **neutral** advancer — a re-seal with no value and no kill, authored purely to
  bury a content fork on a SEL that has no natural `Gnt` or `Trm` to do the job (§Why the neutral
  advancer is needed).

### Why the neutral advancer is needed

The owner IEL is **structurally blind** to a SEL fork — it anchors digests it cannot interpret and
seals by its own clock, so nothing at the IEL layer can hold back a seal on account of a SEL fork.
When a witness-compromise content fork forms and the owner IEL then seals **past** the IEL event
that anchored it, that anchor becomes **live and locked**: it sits on the canonical IEL chain (so it
is not dead — severance cannot reach it) but below the IEL's seal (so it cannot be re-buried by the
IEL). The live SEL content fork it created is now beyond both remedies. The exit is a **fresh SEL
seal-advancer at the SEL's own tip** that buries the loser below its own seal. A document-governance
SEL can do this with a `Gnt`, a kill lookup with a `Trm` — but a **plain content SEL has neither**,
so it uses a **`Sea`**: the SEL analog of the KEL's recovery rotation and the IEL's roster-less
evolve. The same IEL blindness forces both halves symmetrically — the SEL cannot lean on the IEL to
**see** its forks (so it witnesses itself) or to **resolve** them (so it carries its own recovery
advancer).

## Severance — a dead owner-IEL anchor truncates the SEL

The SEL's second state input is inherited from the owner IEL. **Deadness flows upward along the
anchoring edge** — an event whose parent is dead is dead — so a SEL event anchored on an owner-IEL
branch the IEL later buries becomes dead. (This orientation, deadness rising from a dead authorizer
to what it authorized, is the one the SEL states; the rest of the doctrine is being brought to the
same label as a separate change — recorded in the applied notes for this encode.)

A dead anchor does more than mark one event dead — it **severs the chain**. The SEL's later events
were anchored **through** that now-dead IEL lineage, and with **no repair event** to re-root them,
the portion after the **earliest** dead anchor cannot be connected to a valid anchor lineage, so it
**cannot be verified** — verifying it would mean trusting the buried IEL branch. So the SEL is valid
up to the earliest dead-anchor point and severed (dead and un-verifiable) from there; the pre-sever
portion stays live; there is no continuation on the same chain. A SEL portion that **pre-exists**
the IEL fork rides the shared pre-fork lineage and is not severed; a SEL with no anchor on a dead
IEL branch is untouched.

**Deadness takes precedence over the neutral advancer.** You never bury something already dead: a
content fork with one severed branch auto-resolves to the live branch (the SEL shrinks to the shared
tip and the surviving author extends from there — no `Sea`); both branches dead means severed at the
fork. Severance also **downgrades a Disputed**: if one of two accepted sealed branches is severed,
it is un-verifiable and not counted, so the reading drops to the live branch and recovers. A
Disputed under a **linear** owner IEL — where both anchors are locked-live and no severance is
available — stays terminal and forces re-incept. The full enumeration is the correctness proof in
[`reconciliation.md`](reconciliation.md).

## The down-pin and the manifest

A SEL event carries two structural surfaces beyond its common fields.

**The down-pin (`pin`) — how a SEL floors to its owner IEL.** Every non-inception SEL event carries
a top-level scalar **`pin`**: the SAID of the owner IEL event this SEL floors down to. The floor is
a chain link, not a self-asserted claim — a serial-1 event's `pin` equals its anchoring IEL event's
`previous`, and each `Ixn` re-pins forward. The `Icp` carries **no `pin`** (it must stay
recomputable), so the first pin rides the SEL's **serial-1 event**, never the `Icp`.

**The role-qualified manifest.** A SEL event commits to what sits above it through a **`manifest`**
— the SAID of a role-grouped SAD
([event-shape §The manifest](../event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role)).
A SEL event may carry only these roles; one carrying any role outside its kind's vocabulary is
malformed and rejected (read kind-first):

| Role      | Carried by | Commits to                                                           |
| --------- | ---------- | -------------------------------------------------------------------- |
| `content` | `Ixn`      | the content-SAD SAID(s) this `Ixn` records (single-owner data)       |
| `grant`   | `Gnt`      | the grant-value SAD this `Gnt` seals (a `vdti/sel/v1/grants/*` kind) |

The `Icp` (recomputable), the floor `Pin` (a pure re-pin), and the neutral `Sea` carry **no
manifest**; a `Trm`'s termination validity is carried by its anchoring `Rev` / `Dth`, though a
feature layer may commit a gated document in a `Trm`'s manifest (a rescission's participant-blind
bound, for instance) — the primitive assigns it no role. The `owner` / `topic` / `data` / `lineage`
derivation inputs and the down-`pin` stay **top-level structural**. See
[`events.md` §The manifest](events.md#the-manifest--roles-a-sel-event-carries) for the per-kind
detail.

## Inception

A SEL's `Icp` establishes single-owner **data**, not governance, so it is **tier 1**. It carries no
pin, so it is floored by its **serial-1 event** (its v1), which carries the pin the `Icp` cannot
(`pin == the anchoring IEL event's previous`). **The owner IEL anchors the v1, never the `Icp`** —
the `Icp` rides via `v1.previous`. So every SEL reads `{Icp, v1, …}`, and a fabricated bare `{Icp}`
naming a victim owner is **not** evidence of anything — authentication is the v1's anchor
([`verification.md` §Owner-rooting](verification.md#owner-rooting--the-authentication-check)).

Which event is the v1 depends on why the SEL was born: a content SEL's is the first content `Ixn`,
or a bare **`Pin`** for a SEL that incepts and sits (a document author who endorses before editing);
a kill lookup's is its **`Trm`** (`{Icp, Trm}`, born to kill); a value lookup's is its **`Gnt`**
(`{Icp, Gnt}`). The `Pin` kind, when used, does **only** the floor re-pin.

## End-verifiability

The SEL's contribution to end-verifiability over data-from-any-source is two structural properties.
Whole-content prefix derivation lets a lookup SEL's holder **re-derive its address** from data it
already holds and fetch it **by prefix** — no global index, no trusted directory — so a credential's
revocation status or a published receive-key is located from the held reference alone. And the
owner-anchoring means a SEL event's authority never rests on a service, a database, or a peer: it
authenticates by resolving **down** to the owner IEL event that anchors it, and thence to a
threshold of member KEL signatures, every one re-checked from the data. The cross-primitive framing
(verify the data, not the source) is canonical in
[`../../../../system-thesis.md` §End-verifiability](../../../../system-thesis.md#end-verifiability).

## Cross-references

- [`../event-shape.md`](../event-shape.md#sel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind SEL field grid.
- [`events.md`](events.md) — per-kind reference: the six kinds, the three axes, the threshold
  vector, kind-strict cross-layer anchoring, the `Gnt` typed value, the `Sea` re-seal, the lineage
  field.
- [`merge.md`](merge.md) — merge-handler routing: witnessed first-seen, seal-advancer burial,
  inherited severance, the merge outcomes.
- [`verification.md`](verification.md) — the verifier walk: owner-rooting, the witnessed divergence
  read, the severance read, the uniform lineage walk.
- [`reconciliation.md`](reconciliation.md) — the exhaustive correctness proof: the SEL's own
  divergence crossed with inherited owner-IEL deadness.
- [`../iel/log.md`](../iel/log.md) — the owner IEL: the chain that anchors this SEL and the
  four-state machine, seal, and page model this reuses.
- [`../kel/log.md`](../kel/log.md) — the KEL chain primitive the machine originates in.
- [`../../sad/sad.md`](../../sad/sad.md), [`../../sad/said.md`](../../sad/said.md) — the SAD shape
  SEL events compose on; two-hash prefix and SAID derivation.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — structural authorization,
  tiers and kind-strict anchoring, divergence and recovery, the layering principle.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor, first-seen, and disputed detection the SEL
  inherits.
- [`../../../../features/shared-documents/documents.md`](../../../../features/shared-documents/documents.md),
  [`../../../../features/exchange/exchange.md`](../../../../features/exchange/exchange.md) — the
  value-bearing `Gnt` consumers (both forthcoming).
