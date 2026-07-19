# vdti — area note: Membership (the gated-set primitive)

**Status: FIRST CUT — lifted 2026-07-19 (Jason) from the credential accept shape into its own protocol
primitive.** Round-3 exchange review found the chat store-authorization gate (cold **F3**) asserted twice and
realized nowhere: no structure on the surface was simultaneously **store-checkable**, **per-requester**, and
**non-enumerating**. The realizing shape is exactly the credential **accept** path (blinded per-member
commitments + a fail-secure walk / fail-open lookup), so it is lifted to a named primitive both the exchange
feature (group chat) and shared-documents (read / write authorization) compose, rather than each re-deriving it.
Design-doc twin: [`../design/primitives/protocols/membership.md`](../design/primitives/protocols/membership.md).

**What it is in one line:** an **unbounded, never-enumerated** set of identities, answered **one identity at a
time** — "is this party a current member?" — checkable by a **non-member store** against **self-identifying
requesters**, never materialized as a roster.

**Layering:** the SEL primitive (the grant chain + the content-addressed rescission lookups it rides) →
**membership** (the gated-set check) → {exchange (group chat), shared-documents (read / write)} features → apps.
It reuses the [credentials](vdti-area-credentials.md) **accept** construction wholesale; it is **not**
[group-key](vdti-area-group-key.md) — see "The cap is keying's."

**Invariants:** [inv 8] multi-source freshness (the walk reads to the tip; hiding a rescind needs a stale chain
the bar refuses), [inv 10] a value-bearing lookup fails **closed** (the happy-path rescission lookup; not-found
reads best-effort not-rescinded only as a deliberate opt-**down**), [inv 16] addressing by prefix + **gated /
blinded** membership (a downloader learns a count, never who), [inv 19] a request is authorized by a signature
over the fully-compacted SAID (the store resolves a live-signed request to one identity). Composes: the SEL
primitive; the credential accept shape.

## The two halves of a group — membership is the authorization half, not the keying half

A group has two independent concerns, with **opposite** shapes, and conflating them is the trap this note exists
to prevent:

- **Authorization — "may this one party act?"** A per-requester, one-at-a-time check. The set has **no cap** and
  is **never materialized**. This is **membership**.
- **Keying — "hand every member a shared key."** Wrapping a key to each member forces **enumerating** them → a
  **bounded, materialized** roster. This is [group-key](vdti-area-group-key.md)'s **wrap roster**, a separate
  structure.

Membership stays unbounded **because it never enumerates**. The cap a keyed group feels is group-key's, not
membership's (below).

## The grant chain

A group's membership lives on a **grant chain** — a single-owner SEL its **governing identity** owns. Each event
seals a **membership delta** — `{ grants, rescinds }`:

- **`grants`** — identities admitted, each a **blinded per-member commitment** `{ said, nonce, data }` (the same
  claim-gating construction [credentials](vdti-area-credentials.md) uses for per-predicate gating): the
  commitment names the member without publishing who, so a chain onlooker learns a **count**, never a roster.
- **`rescinds`** — identities removed, each a blinded target, optionally carrying a **grandfather boundary**
  (below).

One delta carries **both** — there is no separate "add" and "remove" event, the way an identity's own roster
change carries adds and cuts together. **The delta is what keeps the set unbounded:** the chain records only the
*changes*, never the standing set, so nothing on it grows with membership size and nothing ever needs to hold the
whole set to append to it.

## Checking one member — the two modes credentials already use

Membership reuses the credential **accept** shape verbatim: a party is a current member **iff its grant is validly
recorded and not since rescinded**. That runs in either mode — the same fail-secure / fail-open split a
credential's revocation check uses:

- **The fail-secure walk (default).** Walk the grant chain with the party as a **known search** — look for exactly
  this identity's grant and any later rescind of it — against the **multi-source-fresh** chain ([inv 8]). In some
  grant delta and not since rescinded → a member; in none → not. Sound because hiding a rescind would take a stale
  chain, which the freshness bar refuses.
- **The O(1) happy path (fail-open opt-out).** A rescinded member has a **content-addressed rescission lookup** —
  a tiny `{ inception, termination }` SEL derived from `{ group, the rescission topic, the member }` — whose
  **termination pins to the grant delta that rescinded it** (its `pin` is that delta event's `previous`, so the
  pin points straight at the delta carrying the rescind — a **checked locator**, [inv 5] discipline, never a
  self-asserted position). Fetch it: **found → rescinded**, no walk. The grant side is symmetric — a member's
  grant is located directly by its own pin. A consumer under a latency budget opts **down** to this;
  **not-found reads best-effort not-rescinded** ([inv 10] fail-open), a deliberate step **down** from the walk,
  never a step up.

Both modes check **one identity at a time**, against a **known** identity. Neither ever builds the set. This is
the exact triple round-3 F3 needed — **store-checkable** (the store resolves a live-signed request to an identity
and checks that one), **per-requester** (the requester self-identifies; the store confirms that one and nothing
else), and **non-enumerating** (no operation asks "who are all the members").

## No cap, no enumeration

The set is **unbounded** — a document may be readable by an open-ended audience — so it is **never materialized**.
Every operation is a check against a **known** identity: a store gates a deposit or a fetch by the **requester**,
which presents itself, so the store confirms that one party's membership and nothing else. There is **no**
operation that asks "who are all the members," because the answer has no bound and no party is entitled to it.
This is what lets a downloader of the chain learn only a **count**, and keeps the check cheap regardless of how
large the audience grows.

Where a group genuinely must reach **every** member — wrapping a shared key — that enumeration is
[group-key](vdti-area-group-key.md)'s **bounded wrap roster**, a separate structure. Membership never does it.

## Rescission and the grandfather boundary

Removing a member is one `rescinds` entry (plus, for the happy path, its content-addressed rescission lookup).
Two flavors, set by the composing feature:

- **Immediate** — out at once. A **keyed** group (chat) uses this: forward secrecy comes from the epoch turning
  in the same act (group-key), so nothing the removed member holds opens anything new.
- **Grandfathered** — the rescind carries a **boundary**: content the member authored (or was entitled to)
  **before** the boundary stays honored; only its reach **past** the boundary is cut. A shared document uses this
  so a removed editor's earlier versions do not retroactively vanish. The boundary is itself **blinded** when it
  would otherwise identify a participant (riding behind the read gate); a non-identifying boundary rides in the
  open.

## The cap is keying's, not membership's

The reason chat feels "limited" and an open document does not is **not** a property of membership — it is a
property of **key distribution**:

- A feature that hands members a **shared decryption key** must wrap it to each of them → **enumerating** them →
  a **bounded** roster ([group-key](vdti-area-group-key.md)). Chat, and any encrypted shared document behind a
  shared key, are capped for this reason.
- A feature that encrypts nothing — or delivers content **per request**, sealed to the one member who asks —
  never enumerates, so its membership stays **unbounded**.

So a **keyed** feature composes **both** — group-key's bounded wrap roster (to distribute the key) **and** a
membership instance (to authorize a requester) — while an **unkeyed** feature composes **only** membership. Two
structures, opposite shapes; a feature that needs both uses both. **Chat** is capped (the group-key wrap roster +
`chat-membership`), but the authorization check is still the same one-at-a-time membership lookup; **unprotected
shared documents** are uncapped (`document-membership` only).

## Instances

Features name their membership sets on the shared `vdti/{component}/v1/{category}/{name}` convention; the concrete
SEL topic, grant-value kind, and rescission tag are **each instance's** to register (as group-key registers its
own roster / key-epoch names), not the primitive's. Two instances exist:

- **`chat-membership`** (exchange feature, [`vdti-area-exchange.md`](vdti-area-exchange.md) §7a) — the set a
  chat's store checks to gate deposit and drain. Bounded **in practice** (the chat is a keyed group, so group-key
  already caps it), but checked the same one-at-a-time way; rescission is **immediate**. **Landed this PR.**
- **`document-membership`** (shared-documents feature — **forthcoming**) — the set a shared document's store
  checks. Genuinely **unbounded** (an open readership), **grandfather**-rescinded. See "Drift → land" — the
  rename + wiring is owed to the shared-documents encode, where the **read-vs-write split** is decided.

The read-versus-write distinction and the exact per-instance shapes are the composing feature's; membership
provides the one checked-set mechanism both sit on.

## The boundary — what membership is not

- **Not the wrap roster.** Enumerating members to wrap a key is [group-key](vdti-area-group-key.md)'s bounded
  roster. Membership never enumerates.
- **Not a policy.** Membership answers "is this one identity in the set" — a **single-party** lookup, not a
  multi-party expression evaluated live. Document authorization above it (who may do what) is the policy layer's;
  membership is the set it draws on.
- **Not keying, delivery, or the content structure.** What a group encrypts (group-key), how it delivers
  (the sealed-send core / transport), and how its content threads (the [authored DAG](vdti-area-authored-dag.md))
  are the composing feature's; membership only says **who is in**.

## Divergence / sources

Not lifted from kels — a **vdti-native** consolidation. The realizing shape is the credentials accept path
(blinded `{ said, nonce, data }` commitments + fail-secure walk / fail-open lookup — `vdti-area-credentials.md`,
2026-07-16/17) and the shared-documents grant/rescind machinery (per-participant, participant-blind, grant-docs —
`vdti-area-shared-documents.md`); this note promotes the shared shape to a primitive so the chat store-auth gate
(round-3 F3) has a home and shared-docs is a **variant** rather than a rebuild. The **flip-flop resolution**
(2026-07-19, Jason — recorded so it is not re-litigated): the grant doc **is** the `{ grants, rescinds }` delta
walked with **known searches** (never a materialized roster), **plus** the O(1) rescission lookup; the earlier
"pure-adds + a separate second doc" and "materialized roster" framings were both **wrong** (inherently bounded /
enumerating). **The cap is group-key's wrap roster, not membership** — a keyed feature composes both.

## Drift → land

- **DONE (2026-07-19).** Design-doc twin `../design/primitives/protocols/membership.md` written (greenfield);
  this canon note.
- **Owed (this PR — the exchange encode).** The [group-key](vdti-area-group-key.md) cross-ref (its wrap roster is
  the cap; membership is the separate unbounded authorization); the **`chat-membership`** instance in
  `vdti-area-exchange.md` §7a + `exchange.md` (per-requester store-auth, immediate rescission), replacing the
  round-2 "`readers`-grant" placeholder and retiring its recorded open. `custody.readers` is the read-authorization
  **pointer into** a membership set (a `readers` value is a membership-set prefix — already stated at
  `custody.md`).
- **⚠ Owed (the shared-documents PR — DO NOT DROP; deferred 2026-07-19, Jason "make sure it doesn't get
  dropped").** Rename **`shared-document-governance` → `document-membership`** and its sibling
  **`shared-document-read-governance`**, and wire shared-documents onto **membership** + the multi-parent
  [authored-dag](vdti-area-authored-dag.md). Deferred out of the exchange PR because shared-docs is not otherwise
  touched there (a naked cross-feature catalogue rename) **and** the rename hides a modeling call that belongs to
  the shared-docs encode: a document has **two** sets — read and edit — and membership is per-set, so
  `document-membership` **splits into a read-membership and a write-membership set**; decide the split against
  real shared-docs design. Register `document-membership`'s concrete SEL topic / grant-value kind / rescission tag
  in `kinds.md` + `tags-and-topics.md` at that encode.
