# SAD shapes — the field catalogue

Every piece of content in VDTI is a [SAD](sad.md), and its [`kind`](kinds.md) names its type. This
doc is the companion to those two: [`kinds.md`](kinds.md) enumerates the kinds, and this doc gives
each kind's **shape** — the fields it carries. It covers the **standalone SADs** in full (receipts,
configs, grant values, credentials, shared-document SADs, the ESSR and IPEX protocol messages, file
payloads, policy). For the **chain events**, the authoritative per-kind field tables live in
[`../event-logs/event-shape.md`](../event-logs/event-shape.md); this doc summarizes their common
envelope and points there rather than restating them.

A field marked **forthcoming** has its role fixed but its exact field layout deferred to the feature
or primitive encode named in its source; the [Forthcoming shapes](#forthcoming-shapes) table
collects them.

Types read as: **SAID** / **prefix** — a 256-bit digest (a SAID addresses content, a prefix names a
chain); **digest** — a 256-bit content-address of a raw opaque **blob** (Blake3-256 of the bytes;
distinct from a **SAID**, which addresses a canonical SAD); **SAD** — a **nested sub-SAD** at that
position (referenced by its SAID, but expandable content the signing discipline must have seen —
distinct from a scalar **SAID** reference like a `previous`, a pin, or an anchor); **string**;
**u64** — a non-negative JSON-number integer in the double-safe range ±(2⁵³−1)
([`said.md`](said.md)); **bool**; **bytes**; **timestamp** — an RFC 3339 time; **list⟨T⟩**.

**The examples.** Each shape below carries one example instance — a plausible object, not every
optional field populated. **Every example's `said` derives from exactly the JSON printed beside
it**: JCS-canonicalized, `said` — and `prefix`, where the SAD is prefix-deriving — at the
fixed-value placeholder, Blake3-256, qualified ([`said.md`](said.md)). The one slice, the wrapper
example below, carries the `said` of the whole SAD it was lifted from. Text primitives carry the
encoding library's type qualifiers: a Blake3-256 digest — every SAID, prefix, and blob digest — is a
44-character `V` token, a 256-bit nonce an `N` token, an authenticated-cipher sealing nonce a `1AAN`
token, a timestamp an RFC 3339 instant. A key, signature, ciphertext, or inlined payload runs to
hundreds or thousands of characters, so those values print **elided**, their full length in place of
the middle; a value naming something not shown — a blob's storage key, a reference to an object
elsewhere — is illustrative. Nested sub-SADs print **compacted**, by SAID, the form the canonical
bytes carry; where the catalogue gives such a child a shape of its own, that shape carries its own
example. Fields follow the table's order, wrapper fields first; JCS sorts keys, so an example is a
logical view of a SAD, never its canonical bytes.

## The two shapes

A SAD is one of two shapes ([`sad.md` §Structural shapes](sad.md#structural-shapes)):

- A **chain event** — a SAD with chain-linkage fields (`prefix`, `previous`, `serial`) that lives on
  a KEL / IEL / SEL and replicates as an indivisible unit. Its kind declares no `custody` or
  `availability` field — the exhaustive-schema rule
  ([`kinds.md`](kinds.md#schema--exhaustive-and-versioned)) rejects either on a chain event.
- A **standalone SAD** — everything else (a receipt, a config, a credential, a policy, an exchange
  envelope, the content payloads an event anchors). It is stored in the SAD object store and served
  by SAID, and MAY carry `custody` and `availability` on its wrapper.

## The standalone-SAD wrapper

Every standalone SAD carries these top-level fields, then its kind-specific content:

| Field          | Type   | Required | Meaning                                                                                              |
| -------------- | ------ | -------- | ---------------------------------------------------------------------------------------------------- |
| `said`         | SAID   | yes      | The SAD's self-addressing identifier ([`said.md`](said.md)).                                         |
| `kind`         | string | yes      | The versioned type name ([`kinds.md`](kinds.md)); drives validation.                                 |
| `custody`      | struct | no       | Per-object authority — who may write and read ([`custody.md`](custody.md)).                          |
| `availability` | struct | no       | How long the bytes live and whether retrieval is destructive ([`availability.md`](availability.md)). |

`custody` and `availability` are inline structs, each sub-field independently optional:

- **`custody { owner, pin, readers[] }`** — `owner` is the writer's IEL prefix and `pin` locates the
  owner-IEL `Ixn` that anchored the write (both-or-neither; the SAD's own `kind` names its type, so
  no separate `topic`), `readers[]` an optional **strictly ascending (sorted, distinct), non-empty
  list** of read-authorization SEL prefixes gating reads — a requester in **any** listed set may
  read (omitted → public; one element the common case, several a union like a shared document's edit
  ∪ comment ∪ read gate).
- **`availability { expiry, once }`** — `expiry` a timestamp (the absolute instant past which the
  bytes need not be retained), `once` a destructive-read flag. Where the bytes live is not an
  availability axis — placement is the client's cascading store
  ([`availability.md`](availability.md#what-availability-declares)).

The wrapper of a private file SAD — an attested write, read gated to the union of two sets, bytes
retained until a stated instant (§The file payload shows the same SAD in full):

```json
{
  "said": "VPXFC5bUlkbqJVWincvPXgfm7pivPjEgmaRH2J5ZdQZf",
  "kind": "vdti/sad/v1/schemas/file",
  "custody": {
    "owner": "VMBm6mFNau5nMYbH4QuqFMHEx0t-LAgQzV9RSYU0vO70",
    "pin": "VFkQ1XqZ9jFcefWJU1_tIIgWU0O0-bcWOwyyIIpckJAC",
    "readers": [
      "VAVpQsAJhhkWHmdc2GTPRJVFiq5EsdmfSfJ6O278AlqX",
      "VN1qO8PqWQYOcjTa8u2luHTyMNkEA5sibS51eIeVR7_E"
    ]
  },
  "availability": {
    "expiry": "2027-05-01T00:00:00Z"
  }
}
```

## The file payload — `vdti/sad/v1/schemas/file`

The SAD layer's general content wrapper: a standalone SAD that names **bulk opaque bytes** — an
encrypted payload, a file, media — as a **content-addressed blob** rather than inlining them
([`sad.md` §Bulk opaque bytes](sad.md#bulk-opaque-bytes--the-content-addressed-blob)).

| Field       | Type   | Required | Meaning                                                                                                                    |
| ----------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| `said`      | SAID   | yes      | The file SAD's SAID.                                                                                                       |
| `kind`      | string | yes      | `vdti/sad/v1/schemas/file`.                                                                                                |
| `digest`    | digest | yes      | The **storage key `S`** — `hash(bundle.said ‖ blob)`, committing the stored payload (bundle + blob) — committed by `said`. |
| `size`      | u64    | yes      | The stored payload's byte length — advisory (allocation / pre-fetch bound), not integrity.                                 |
| `mediaType` | string | no       | Advisory MIME type.                                                                                                        |
| `name`      | string | no       | Advisory filename.                                                                                                         |
| `nonce`     | bytes  | yes      | High-entropy — makes `said` unguessable for a private file.                                                                |

A file SAD naming an encrypted attachment — the storage key its `said` commits, the advisory size
and labels, and the mandatory nonce:

```json
{
  "said": "VPXFC5bUlkbqJVWincvPXgfm7pivPjEgmaRH2J5ZdQZf",
  "kind": "vdti/sad/v1/schemas/file",
  "custody": {
    "owner": "VMBm6mFNau5nMYbH4QuqFMHEx0t-LAgQzV9RSYU0vO70",
    "pin": "VFkQ1XqZ9jFcefWJU1_tIIgWU0O0-bcWOwyyIIpckJAC",
    "readers": [
      "VAVpQsAJhhkWHmdc2GTPRJVFiq5EsdmfSfJ6O278AlqX",
      "VN1qO8PqWQYOcjTa8u2luHTyMNkEA5sibS51eIeVR7_E"
    ]
  },
  "availability": {
    "expiry": "2027-05-01T00:00:00Z"
  },
  "digest": "VA3Ku19KbyCznq9XX2icil1P-oypkbgSeYPeouSpJIHz",
  "size": 2456123,
  "mediaType": "application/pdf",
  "name": "quarterly-report.pdf",
  "nonce": "NIbQXTQa4Og-JXWKz7H4mwn5Gh5LwhwTrhrJindl-nu1"
}
```

The `custody` / `availability` wrapper applies as to any standalone SAD: `custody.readers` gates who
may fetch the SAD, and the SAD's `availability` governs the **SAD**. The **payload's** availability
rides its own **bundle** (§The blob bundle below), and the coupling is the covering rule —
**`D ⊇ payload`**: the committing SAD's availability must cover the payload's
(`D.expiry ≥ payload.expiry`, and a `once` `D` roots nothing), checked at blob admission
([`blobsd.md`](../../../substrate/infrastructure/blobsd.md)). The blob is opaque bytes — not a SAD,
no `kind` of its own — fetched **by `S`** from a blob store and accepted only when `hash(payload)`
recomputes to `S` and the split-out blob matches `bundle.blobDigest`
([`sad.md` §Bulk opaque bytes](sad.md#bulk-opaque-bytes--the-content-addressed-blob)).

## The blob bundle — access and availability on the stored object

Bulk opaque bytes are stored as a **payload** — `bundle.said ‖ blob` — addressed by the **storage
key `S = hash(payload)`**, where the **bundle** is a small SAD the **client** composes to carry the
blob's access and availability
([`sad.md` §Bulk opaque bytes](sad.md#bulk-opaque-bytes--the-content-addressed-blob)):

| Field        | Type      | Required | Meaning                                                                                                                                   |
| ------------ | --------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `said`       | SAID      | yes      | The bundle's SAID — the payload's first, fixed-width, self-framing segment.                                                               |
| `kind`       | string    | yes      | One of the **two bundle kinds** (below) — carries the encrypted/plaintext distinction structurally.                                       |
| `nonce`      | bytes     | yes      | **Mandatory high-entropy** — makes a private blob's `S` unguessable; a low-entropy nonce would reopen an offline `S`-confirmation oracle. |
| `blobDigest` | digest    | yes      | `hash(blob)` — the bundle **commits its blob**, so a `bundle.said` pairs with exactly one blob.                                           |
| `access`     | SAD       | no       | The read gate the serving store enforces (the descriptor below). **`access` authorizes reads only.**                                      |
| `once`       | bool      | no       | Destructive read — burns on the first serve, **gated or ungated** (an ungated `once` is a bearer one-time link).                          |
| `expiry`     | timestamp | no       | GC horizon — composes with either ([`availability.md`](availability.md)).                                                                 |

The two bundle kinds are `vdti/sad/v1/schemas/blob-metadata` (**plaintext** payload → the strict
serve-currency tier) and `vdti/sad/v1/schemas/sealed-blob-metadata` (**encrypted** payload → the
light tier). The distinction is a **kind, not a declared flag**: serve-currency must tier on
something the store holds at serve time, and "is this ciphertext?" is not answerable from opaque
bytes — and it is not self-asserted, because blob admission **validates the bundle kind against the
committing document's own kind** (a structurally sealed document — an ESSR envelope, an epoch-sealed
message — must carry the sealed kind; an ambiguous one defaults to **plaintext, fail-secure**, and
opts down deliberately). An unmappable kind is **refused, fail-closed**
([`blobsd.md`](../../../substrate/infrastructure/blobsd.md)).

The bundle stored with that file's payload — the encrypted kind, a gated read, and a GC horizon its
committing SAD's own availability covers:

```json
{
  "said": "VNFE67girUzYaoSSWQwF-4FPqKqHXfg5T7fIzMmpbQ0s",
  "kind": "vdti/sad/v1/schemas/sealed-blob-metadata",
  "nonce": "NBTEYq-bDifJdNzmKtkjKkUMidiu6QSpRf4-vY0pnkej",
  "blobDigest": "VA33V2wXbe7CwnAWwIVPH4cLHe-jgqB6mqC6nNPJgrgm",
  "access": "VNTubie0UynSagEC61vVLk4T5AQxswMrighSYHlUDKBd",
  "expiry": "2027-05-01T00:00:00Z"
}
```

The bundle is **unsigned** — availability is anchored transitively by the committing document, which
commits `S`, which fixes the bundle ([`sad.md`](sad.md)). And it is **not on the served-by-SAID
list**: like the mesh handshake SADs it is internal to its server, reachable only through the
payload at `S`, so a bare `bundle.said` fetch is refused by default. Two submitters of one blob
produce different bundles — a different `nonce` alone — hence different `S`: **separate stored
objects, no cross-submitter dedup**, which is a privacy gain (dedup was a confirmation oracle).
Public vs private is **inherited, not a flag**: a private blob's `S` is learned only from its
(gated) committing document; a public blob's committing document is public, so its `S` is
discoverable.

The **`access` descriptor** dispatches on `check`:

```
access = { check: "roster",     identity }   // a current member DEVICE of the named recipient IEL
        | { check: "membership", sets }      // a current member of any named grant chain, union over sets
```

A `roster` check admits a current member device of the named recipient IEL; a `membership` check
admits a current member of any named grant-chain set
([`../../protocols/membership.md`](../../protocols/membership.md)) — the same membership primitive
wherever it appears. The gate is **operational, never the confidentiality boundary**
([`custody.md`](custody.md)) — it is enforced on a live-signed request by the serving store
([`blobsd.md`](../../../substrate/infrastructure/blobsd.md)), and an unmappable `check` is
**refused, fail-closed**. `access` authorizes **reads only**: deletion authority is not a bundle
field and not a SAD-layer rule — who may remove an object is the deploying application's predicate
([`blobsd.md` §Deletion](../../../substrate/infrastructure/blobsd.md#deletion-is-the-applications)).

## Rooting SADs — `vdti/rooting/v1/*`

The store's admission wrapper and its two root pointers ([`rooting.md`](rooting.md)): a submission
names the SAD being admitted and the **root** that commits it, and the store dispatches on the
root's `kind`. These ride the `submit SAD` write path
([`../../../substrate/infrastructure/sadd.md` §The SAD store write path](../../../substrate/infrastructure/sadd.md#the-sad-store-write-path));
the envelope is the wire form the store unwraps, not a stored, serve-by-SAID object.

The **submission envelope** — `vdti/rooting/v1/submission/envelope`:

| Field  | Type   | Required | Meaning                                                                                |
| ------ | ------ | -------- | -------------------------------------------------------------------------------------- |
| `said` | SAID   | yes      | The envelope's own SAID.                                                               |
| `kind` | string | yes      | `vdti/rooting/v1/submission/envelope`.                                                 |
| `sad`  | SAD    | yes      | The SAD being admitted (nested; travels compacted or expanded — the store recomputes). |
| `root` | SAD    | yes      | The root pointer — one of the two nested rooting SADs below.                           |

A submission admitting the file SAD above under an event root:

```json
{
  "said": "VExubYy5x9bur0WGg3lZeUEkAAG0y7HhX6IvJbn1wWMy",
  "kind": "vdti/rooting/v1/submission/envelope",
  "sad": "VPXFC5bUlkbqJVWincvPXgfm7pivPjEgmaRH2J5ZdQZf",
  "root": "VBc_qdCh5aZWmG-RBokYws9wF6u0duD7f1OeqCrhIKvn"
}
```

The **event-root pointer** — `vdti/rooting/v1/{kel,iel,sel}/event`, when a chain event commits the
SAD:

| Field    | Type   | Required | Meaning                                                                                                                                                      |
| -------- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `said`   | SAID   | yes      | The pointer's own SAID.                                                                                                                                      |
| `kind`   | string | yes      | `vdti/rooting/v1/{kel,iel,sel}/event` — the log whose event commits the SAD.                                                                                 |
| `prefix` | prefix | yes      | The committing chain's prefix.                                                                                                                               |
| `event`  | SAID   | yes      | The anchoring event's `previous` — the committing event sits at its serial + 1, the same locator `custody.pin` uses.                                         |
| `field`  | string | yes      | The committing event-body field — `manifest` or `pins`, the only two that name a store SAD ([`../event-logs/event-shape.md`](../event-logs/event-shape.md)). |

The event-root pointer it carries — the owner IEL `Ixn` at `event`'s serial + 1 commits the SAD in
its `manifest`:

```json
{
  "said": "VBc_qdCh5aZWmG-RBokYws9wF6u0duD7f1OeqCrhIKvn",
  "kind": "vdti/rooting/v1/iel/event",
  "prefix": "VMBm6mFNau5nMYbH4QuqFMHEx0t-LAgQzV9RSYU0vO70",
  "event": "VFkQ1XqZ9jFcefWJU1_tIIgWU0O0-bcWOwyyIIpckJAC",
  "field": "manifest"
}
```

The **SAD-field-root pointer** — `vdti/rooting/v1/sad/field`, when an accepted parent SAD commits
the SAD:

| Field    | Type   | Required | Meaning                                                                                       |
| -------- | ------ | -------- | --------------------------------------------------------------------------------------------- |
| `said`   | SAID   | yes      | The pointer's own SAID.                                                                       |
| `kind`   | string | yes      | `vdti/rooting/v1/sad/field`.                                                                  |
| `parent` | SAID   | yes      | The accepted parent SAD's identifier.                                                         |
| `field`  | string | yes      | The parent field that commits the child (a manifest role, a credential's `terms` / `claims`). |

A SAD-field-root pointer instead, when an accepted parent commits the child — here a credential's
claims SAD:

```json
{
  "said": "VDjRixereZ3LSIo7V4UJ1rqhiMe-BEchhGCF0TFFGoSI",
  "kind": "vdti/rooting/v1/sad/field",
  "parent": "VE4zuHh228ik_6Y2kKSdrEJsrUyfLBonw3DfhZvLfZFa",
  "field": "claims"
}
```

The child does **not** name its parent in its own bytes (that would bind it to one parent and leak
the composition), so the `sad/field` pointer is a checked request hint, not part of the admitted
SAD. The store reads `field`'s declared type from the root kind's schema and confirms accordingly —
a direct child reference by **identifier equality**, a blinded-commitment list (`anchors`) by
**recompute-and-membership** ([`rooting.md` §The submission](rooting.md#the-submission)); a failed
confirm is a rejection, not a fall-through to the anonymous floor.

## Chain events

Every event (KEL, IEL, SEL) shares one envelope; the per-kind fields on top of it — and which
`manifest` roles each kind may carry — are the subject of
[`../event-logs/event-shape.md`](../event-logs/event-shape.md), which is authoritative. The common
envelope:

| Field          | Type   | Meaning                                                             |
| -------------- | ------ | ------------------------------------------------------------------- |
| `said`         | SAID   | The event's own SAID.                                               |
| `prefix`       | prefix | The chain identifier, derived from the inception content.           |
| `serial`       | u64    | Monotonic position — `0` at inception, `≥ 1` after.                 |
| `previous`     | SAID   | The parent event's SAID; forbidden at inception, required after.    |
| `kind`         | string | The log-and-kind discriminator.                                     |
| `manifest`     | SAID   | On committing kinds — the role-grouped commitment SAD (below).      |
| `previousSeal` | SAID   | On sealing kinds — the back-link to the prior seal-advancing event. |

Kind-specific fields sit alongside — the KEL's `publicKey` / `rotationHash`, the federation binding
`federation` / `federationPin`, the IEL's `pins` and `nonce`, the SEL's `authority` / `topic` /
`data` / `content` / `lineage` / `pin`. Each event kind's full required/optional/forbidden table is
[`event-shape.md` §Per-kind structural validation](../event-logs/event-shape.md); the shared field
meanings are its §Common fields and §Cross-cutting fields.

A KEL inception — `serial` 0, no `previous`, and a `prefix` derived from the whole inception content
by the two-hash algorithm:

```json
{
  "said": "VCCzeYhTBehR1gmWlt1PvPogGEFVQfPZIkEaJ-7YR0fs",
  "prefix": "VAWux8uFtRyQ3v7ezyy3fBE4fTCRtAqCXcRPg267wPHG",
  "serial": 0,
  "kind": "vdti/kel/v1/events/icp",
  "publicKey": "QGGIOk…2604 chars…JsfQ",
  "rotationHash": "VDxHh07WH1k946HaX_WdYoRq6yr5KUpyKDv5yTgG9Pt9",
  "federation": "VD1dGfv6l7xpf4oVIQqo0cQMhEXlOFRmmYCKHkvn4d5h",
  "federationPin": "VGJJA8UftIdbz5TBFzP74lp3z493h2uWsQS6ehIs3Hz0",
  "manifest": "VGKfdUpKACqeFzvg2ky2qRRcCf9e5_Sk11ABKuTZAZfd"
}
```

The rotation that follows it — the inherited `prefix`, `previous` to the inception, and the
`previousSeal` back-link that renders the spine:

```json
{
  "said": "VEd1wXILtDgPJVAYII4y2atic3yJCQ95kwz53d6oPKqW",
  "prefix": "VAWux8uFtRyQ3v7ezyy3fBE4fTCRtAqCXcRPg267wPHG",
  "serial": 1,
  "previous": "VCCzeYhTBehR1gmWlt1PvPogGEFVQfPZIkEaJ-7YR0fs",
  "kind": "vdti/kel/v1/events/rot",
  "publicKey": "Q5xqNP…2604 chars…uYJe",
  "rotationHash": "VPpytkYGz_X7lDx8w3DJVJoIbloaNzhVvtXk7LQJEXLd",
  "previousSeal": "VCCzeYhTBehR1gmWlt1PvPogGEFVQfPZIkEaJ-7YR0fs"
}
```

## Commitment SADs — what a `manifest` names

A committing event's `manifest` is the SAID of a **role-grouped commitment SAD**:
`{ said, kind, <role>: <value>, … }`, where each role is a named commitment. The role vocabulary and
which kind may carry which role are [`event-shape.md` §The manifest](../event-logs/event-shape.md);
the roles that resolve to their **own** SAD are catalogued here.

The manifest that inception names — one role, the witness-config SAD below:

```json
{
  "said": "VGKfdUpKACqeFzvg2ky2qRRcCf9e5_Sk11ABKuTZAZfd",
  "kind": "vdti/event/v1/roles/manifest",
  "witnesses": "VDiGA02z3PUYCWNrVbxlh3folbGskM8OhuZvXR3KwdVx"
}
```

### `vdti/event/v1/roles/witnesses` — the witness-config

| Field       | Type   | Meaning                                                       |
| ----------- | ------ | ------------------------------------------------------------- |
| `said`      | SAID   | The config SAD's SAID.                                        |
| `kind`      | string | `vdti/event/v1/roles/witnesses`.                              |
| `threshold` | u64    | Valid receipts a consumer requires before it trusts an event. |
| `signers`   | u64    | Witnesses selected per event; `signers ≥ threshold`.          |

Bounded `signers/2 < threshold ≤ signers ≤ |roster|` (here `|roster|` is the **federation's**
witness roster, not the identity's own member roster), with a tighter recoverability cap on the
federation IEL
([`../../../substrate/federation/witnessing.md`](../../../substrate/federation/witnessing.md)).

A witness-config — five signers selected per event, three receipts required:

```json
{
  "said": "VDiGA02z3PUYCWNrVbxlh3folbGskM8OhuZvXR3KwdVx",
  "kind": "vdti/event/v1/roles/witnesses",
  "threshold": 3,
  "signers": 5
}
```

### `vdti/event/v1/roles/roster` — a roster / threshold delta

Carried by an IEL `Icp` (the initial roster + threshold vector), an `Evl` (a delta), and a
federation `Fcp` / `Wit`:

| Field             | Type                         | Meaning                                                                                                                                                                                                                                                                                                                                               |
| ----------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said`            | SAID                         | The delta SAD's SAID.                                                                                                                                                                                                                                                                                                                                 |
| `kind`            | string                       | `vdti/event/v1/roles/roster`.                                                                                                                                                                                                                                                                                                                         |
| `add`             | list⟨prefix⟩                 | Member KEL prefixes added (the full initial set at inception).                                                                                                                                                                                                                                                                                        |
| `cut`             | list⟨prefix⟩                 | Member KEL prefixes removed (a `cut` on an `Evl` evicts).                                                                                                                                                                                                                                                                                             |
| `threshold`       | `{ use, authorize, govern }` | The threshold vector — the declared or changed counts for content (tier 1), authorization, governance (both tier 2). Prose writes a slot as `t_use` / `t_authorize` / `t_govern`; those are documentation labels, and these are the data keys ([`../event-logs/iel/events.md`](../event-logs/iel/events.md#the-threshold-vector-and-its-bounds)).     |
| `stepUpThreshold` | u64                          | The **step-up bar** (`t_stepup` in prose), beside the vector, not in it: **required** at a user inception, **delta** thereafter (present ⇒ changed, absent ⇒ unchanged); `1 ≤ t_stepup ≤ \|roster\|`, `≥ 2` hard for `\|roster\| ≥ 2`; **forbidden on the federation facet**; no consuming event kind — read by live checks, never by event validity. |

A delta is a **set** change — well-formed only with `add ∉` the roster, `cut ⊆` it, `cut ∩ add = ∅`,
and the post-delta size `|roster| + |add| − |cut|` between `1` and `MAXIMUM_ROSTER_SIZE` (32); the
threshold bounds — `t_stepup`'s included — are re-checked on the post-delta config
([`../event-logs/iel/events.md`](../event-logs/iel/events.md)). On a **federation `Wit`**, `add`
must carry **exactly one** prefix (one witness KEL added at a time) — the type stays `list⟨prefix⟩`;
the one-at-a-time rule is a cardinality check on the federation facet, not a second shape.

An initial roster and threshold vector, carried by a user IEL `Icp` — three member devices, content
at one, authority at two:

```json
{
  "said": "VAe8bvQ1V8siW7uypKubPG76UvdQu3cBdM3O5rdKIwTB",
  "kind": "vdti/event/v1/roles/roster",
  "add": [
    "VGPYmZDJUlWpsnQZzPhXsbvzHnQZ9cNWpsf2pjhHpjkm",
    "VJiNH-8Yoqb6uuw9qqGB4Qs6RhvOBgXCY8O3agYRJha6",
    "VOQCxejR14GK2VrqbLeFezR7mQfwSiKweS2I7FixKKGj"
  ],
  "threshold": {
    "use": 1,
    "authorize": 2,
    "govern": 2
  },
  "stepUpThreshold": 2
}
```

### `vdti/event/v1/roles/pins` — the participating member KEL SAIDs

| Field  | Type       | Meaning                                                                                                                                                          |
| ------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said` | SAID       | The pins SAD's SAID.                                                                                                                                             |
| `kind` | string     | `vdti/event/v1/roles/pins`.                                                                                                                                      |
| `pins` | list⟨SAID⟩ | Each participating member's **prior KEL tip** (`participation.previous`; the anchoring KEL event sits one past it, so no SAID cycle) — an IEL event's down-pins. |

The down-pins of an IEL event two of its members participated in:

```json
{
  "said": "VLEOBGKW2yfAJdufFh6FCq1H3v4WatD1wU3f5oOSQB1j",
  "kind": "vdti/event/v1/roles/pins",
  "pins": [
    "VAZMLlulk61LIwPe4T0StYk5UuTIf7TOghJ9lZGu7HtD",
    "VPKhZf3wVE3gq-YRsq4TyqUDl4g135EZU1mzS0F3BnLM"
  ]
}
```

The remaining roles — `anchors`, `delegates`, `payload`, `kills`, and the scalar `clock` — are
carried **inline** in the manifest SAD, so they have no SAD of their own ([`kinds.md`](kinds.md));
the `bound` and `grant` roles each name a SAD of their own (the gated rescind-doc, and the grant
value — §Grant values below). Their value shapes are
[`event-shape.md` §The manifest](../event-logs/event-shape.md).

## Witness receipts

A receipt is itself a SAD; its witness signature rides **adjacent**, never in the body (a SAD cannot
sign over its own `said`). One kind per witnessed chain — `vdti/witness/v1/receipts/{kel,iel,sel}`.

| Field           | Type      | Meaning                                                           |
| --------------- | --------- | ----------------------------------------------------------------- |
| `said`          | SAID      | The receipt's own SAID.                                           |
| `kind`          | string    | `vdti/witness/v1/receipts/{kel,iel,sel}`.                         |
| `threshold`     | u64       | The witness-config threshold in effect at the witnessed position. |
| `signers`       | u64       | The selection size in effect at that position.                    |
| `federationPin` | SAID      | The chain's federation binding there — resolves the as-of roster. |
| `chainPrefix`   | prefix    | The witnessed chain's prefix.                                     |
| `eventSaid`     | SAID      | The one committing SAID of the witnessed event.                   |
| `eventSerial`   | u64       | Its serial.                                                       |
| `timestamp`     | timestamp | The witness's asserted time (inside the signed payload).          |
| `witnessPrefix` | prefix    | The signing witness's KEL prefix.                                 |

A witness receipt over an IEL event at serial 17:

```json
{
  "said": "VE0ByZRMYKXrCWntTQFGKaVKpLQSGkQSO-eshM1MkCSk",
  "kind": "vdti/witness/v1/receipts/iel",
  "threshold": 3,
  "signers": 5,
  "federationPin": "VGJJA8UftIdbz5TBFzP74lp3z493h2uWsQS6ehIs3Hz0",
  "chainPrefix": "VMBm6mFNau5nMYbH4QuqFMHEx0t-LAgQzV9RSYU0vO70",
  "eventSaid": "VHCaP6Pbt9BCPhA3VJQoksW1hwD9IWdRh-HD_Q99vahF",
  "eventSerial": 17,
  "timestamp": "2026-11-04T18:22:07Z",
  "witnessPrefix": "VKC51nmrADoKjgHLv9jhETUzRXrDsmHI99viOQsjEG8g"
}
```

## Freshness statements

A **freshness statement** is a witness-signed attestation of held state — the multi-source freshness
evidence a consumer's loss-of-trust decisions gather
([`../../../substrate/infrastructure/architecture.md` §The freshness statement](../../../substrate/infrastructure/architecture.md#the-freshness-statement)).
Like a receipt, it is a SAD whose witness signature rides **adjacent**, never in the body.

| Field           | Type      | Required | Meaning                                                                                                                 |
| --------------- | --------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `said`          | SAID      | yes      | The statement's own SAID.                                                                                               |
| `kind`          | string    | yes      | `vdti/witness/v1/states/freshness`.                                                                                     |
| `statements`    | list      | yes      | `[{ prefix, effectiveSaid }, …]` — the attested pairs, strictly ascending by prefix, capped at `MAXIMUM_MANIFEST_LIST`. |
| `timestamp`     | timestamp | yes      | The witness's asserted time (inside the signed payload).                                                                |
| `nonce`         | bytes     | no       | A consumer-supplied challenge — present in the live (challenge-response) variant.                                       |
| `witnessPrefix` | prefix    | yes      | The signing witness's KEL prefix.                                                                                       |

A freshness statement answering a consumer's challenge, attesting the state it holds for two chains:

```json
{
  "said": "VDoxg3e4nw10MjIv6cjjUBhF6xhHntTwGTvJiaMpHUbp",
  "kind": "vdti/witness/v1/states/freshness",
  "statements": [
    {
      "prefix": "VGWHQrCmXQ8RH-yINgLvg2HEg8pGCs67ecpZ6-ufT6WN",
      "effectiveSaid": "VOVT1Vtze8OZQNRiV8zE6xEq4BqJk3r6g3LEQlI9AjaT"
    },
    {
      "prefix": "VMBm6mFNau5nMYbH4QuqFMHEx0t-LAgQzV9RSYU0vO70",
      "effectiveSaid": "VOq34m01F38MB3V5UkRCawpGhrx8Gz0s7XyFLaeHBRGb"
    }
  ],
  "timestamp": "2026-11-04T18:22:09Z",
  "nonce": "NFOC50W3Xgv2eKcKdYUXEjqd1UuRXI0c_psct3Le9iFd",
  "witnessPrefix": "VKC51nmrADoKjgHLv9jhETUzRXrDsmHI99viOQsjEG8g"
}
```

## Grant values — what a SEL `Gnt` seals

A SEL `Gnt`'s `manifest.grant` names a **grant-value SAD** whose kind is `vdti/sel/v1/grants/*`. The
value it carries is the sealed thing itself.

| Kind                                             | Carries                                                                                                                                                                                                                                                                                                                                                                                                                                      | Status       |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| `vdti/sel/v1/grants/directory-kem`               | A published receive key — a **scheme-tagged** KEM public key (the tag carries the scheme and parameter set, so one kind covers every set) + optional hardware attestation + the `receivers` service list. Owned by the [receive-key directory](../../protocols/receive-key-directory.md).                                                                                                                                                    | fields fixed |
| `vdti/sel/v1/grants/groupkey-epoch-key`          | A group epoch key, ESSR-wrapped once per member device. Owned by [group-key](../../protocols/group-key.md).                                                                                                                                                                                                                                                                                                                                  | forthcoming  |
| `vdti/sel/v1/grants/document-edit-membership`    | The `{ grants, rescinds }` membership-delta grant-doc (**editors**) — one shape shared by all three doc instances; a `rescinds` entry records the grandfather `bound` on the rescission `Trm`'s `bound` role. Owned by [shared documents](../../../features/shared-documents.md).                                                                                                                                                            | fields fixed |
| `vdti/sel/v1/grants/document-comment-membership` | The same shape, **commenters**. Owned by [shared documents](../../../features/shared-documents.md).                                                                                                                                                                                                                                                                                                                                          | fields fixed |
| `vdti/sel/v1/grants/document-read-membership`    | The same shape, **readers**. Owned by [shared documents](../../../features/shared-documents.md).                                                                                                                                                                                                                                                                                                                                             | fields fixed |
| `vdti/sel/v1/grants/chat-membership`             | The `{ grants, rescinds }` membership-delta grant-doc — a `grants` entry anchors a writing device's body-less lane root; a `rescinds` entry records its lane-tip `bound` on the rescission `Trm`'s `bound` role. Owned by [exchange](../../../features/exchange.md).                                                                                                                                                                         | forthcoming  |
| `vdti/sel/v1/grants/delegation`                  | A **delegation marker** — the tier-2 signpost a delegating-link `{Icp, Gnt}` seals; commits a **blinded reference to the delegate** (checked by the `del(X, N)` walk against the anchoring `Ath`'s `delegates`), and carries no authority itself — [`../event-logs/iel/delegation.md`](../event-logs/iel/delegation.md).                                                                                                                     | forthcoming  |
| `vdti/sel/v1/grants/block`                       | A **block marker** — the signpost a federation's [prefix-block](../../../substrate/federation/blocking.md) lineage `{Icp, Gnt}` seals; `{ said, kind, reason? }`, carrying an optional `reason` and no authority of its own (the live lineage _is_ the block).                                                                                                                                                                               | fields fixed |
| `vdti/sel/v1/grants/trusted-federation`          | The **trusted-federation grant value** — `{ remotePrefix, bound }`: the remote federation's prefix (must equal the derived address's input — self-describing, never a second authority) and the governance horizon `bound`, a remote-federation-event SAID, monotone non-decreasing across refreshes ([`witnessing.md` §The trust grant chain](../../../substrate/federation/witnessing.md#the-trust-grant-chain--the-federation-boundary)). | fields fixed |

Each grant value is a SAD (`said` + `kind` + its value); each is **owned by the component that
defines it** — the rows above point at the owning doc, and this catalogue is a registry, never the
definition. **Status** reads **fields fixed** where the field set is settled (here, or in the owning
doc — the three document-membership rows are one shape, defined by
[shared documents](../../../features/shared-documents.md)) and only the byte-level layout is owed at
the encoding library; **forthcoming** where the field set itself is still owed — the ESSR wrap of a
group epoch key, the chat-membership grant-doc at the exchange encode, and the delegation marker's
blinded reference.

The **directory receive-key** grant value carries the reachability a sender needs — the key to seal
to and where to deliver:

| Field         | Type         | Meaning                                                                                                                                                                                                              |
| ------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said`        | SAID         | The grant value's SAID.                                                                                                                                                                                              |
| `kind`        | string       | `vdti/sel/v1/grants/directory-kem`.                                                                                                                                                                                  |
| `receiveKey`  | bytes        | The **scheme-tagged** KEM public key others seal to — the tag names the scheme and parameter set, so the kind never multiplies per parameter set.                                                                    |
| `attestation` | bytes        | Optional — a vendor-signed hardware attestation.                                                                                                                                                                     |
| `receivers`   | list⟨prefix⟩ | The service identities whose deployments hold a message sealed to this key — each resolved to nodes via its roster and its endpoint lookup ([`receive-key-directory.md`](../../protocols/receive-key-directory.md)). |

(The scheme-tagged key and attestation byte layouts land at the encoding library; the structural
fields — including the `receivers` exchange delivers against — are fixed here.)

A published receive key and the services that hold a message sealed to it:

```json
{
  "said": "VK9FT_Yl8-hUpIMMlYv_Hf8ChWirN807E3Q6PK4_O8-0",
  "kind": "vdti/sel/v1/grants/directory-kem",
  "receiveKey": "MT7EEX…1580 chars…rd8A",
  "receivers": [
    "VKqIjrn0Jj_mSHIk5QnypzjJDSZ5OwqRViXS_PU4tGJn",
    "VLdfe34Rdsa_o-Z_29G9ZamDYCFTnA14wVbJ4ppLzW8e"
  ]
}
```

A prefix-block marker:

```json
{
  "said": "VAqX6Bx4NInGWkJJHH1BjHQiZ7rBL1fdhlg508v00R9M",
  "kind": "vdti/sel/v1/grants/block",
  "reason": "sustained malformed submissions"
}
```

A trusted-federation grant value — the remote federation and the governance horizon acceptance is
bounded by:

```json
{
  "said": "VK7xV6-Q6zqs_DCIKV6fGyNdxIKs0b9JVGB-SffxkhfX",
  "kind": "vdti/sel/v1/grants/trusted-federation",
  "remotePrefix": "VBI0tLmkTCs2Fls7eKB70Sqeu5wMtqtfwBbCYDyWzTkF",
  "bound": "VCBX_UfgTk01aSM1ptm1SLAQulH_4ue3IsSq8quExNE_"
}
```

## Protocol SADs

### ESSR — `vdti/essr/v1/*`

The **envelope** (`vdti/essr/v1/schemas/envelope`) — the signed cleartext; its signature rides
adjacent ([`../../protocols/essr.md`](../../protocols/essr.md)):

| Field           | Type   | Meaning                                                                                                                                                      |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `said`          | SAID   | The envelope SAID — commits every field below; the signature is over it.                                                                                     |
| `kind`          | string | `vdti/essr/v1/schemas/envelope`.                                                                                                                             |
| `sender`        | prefix | The sender's IEL prefix (cleartext — routes and fetches the verify key).                                                                                     |
| `senderPin`     | SAID   | The sender's establishment event current at signing — the verifying state.                                                                                   |
| `recipient`     | prefix | The recipient's IEL prefix (signed — the recipient binding).                                                                                                 |
| `kemCiphertext` | bytes  | The key-encapsulation to the recipient's receive key — small, inline (derives the key).                                                                      |
| `payloadDigest` | digest | Commitment to the sealed inner's stored **payload** — `bundle.said ‖ blob`, the ciphertext riding as the blob — the storage key **`S`** (integrity-bearing). |
| `payloadSize`   | u64    | The stored payload's byte length — advisory (allocation / pre-fetch bound), not integrity.                                                                   |
| `nonce`         | bytes  | The sealing nonce (fresh random per message).                                                                                                                |

An ESSR envelope — the signed cleartext, committing its sealed inner by storage key:

```json
{
  "said": "VH1Pe6mCOzc0HMaCy9-jfbRvI2geCSkaoFAdqsQKbGdV",
  "kind": "vdti/essr/v1/schemas/envelope",
  "sender": "VJXt6jL06zmOACv4c3WENNyxExknjh36ljnNDGbhSi_5",
  "senderPin": "VKCPOaGtw7Pwo5C9AcYDi2ncOIs3QCWemKzUwO7thN-R",
  "recipient": "VEpHnH2icPWTIkx3Jgfpt-MUqDvlE5eDtTFZwBtiViTe",
  "kemCiphertext": "Y4N0EN…1452 chars…QrgJ",
  "payloadDigest": "VHqv8IZiCBWcYL4zDh7BO7g7HDTP3fuppJg5ebPy4kod",
  "payloadSize": 4192,
  "nonce": "1AANiTHw6npkSzTNkRGB"
}
```

The **inner** (`vdti/essr/v1/schemas/inner`, sealed) is `{ said, kind, sender, payload }` — the
sender prefix (the binding that rides inside the sealed content) and the opaque payload; a message
timestamp or protocol label rides _inside_ `payload`, not as an envelope field. The **sealed inner
(the ciphertext) is not carried in the envelope** — it rides as the blob of a bundle-committed
stored payload the envelope's `payloadDigest` names by storage key (+ `payloadSize`), fetched by `S`
and checked before decryption: the **key is integrity-bearing** (a recomputed `hash(payload)`
mismatch, or a split-out blob failing `bundle.blobDigest`, is the tamper signal), the **size
advisory** (an allocation / pre-fetch bound, never treated as tamper-evidence). The **message**
(`vdti/essr/v1/schemas/message`) is `{ said, kind, envelope, signature }` — the envelope SAD plus
the sender's signature over `envelope.said`.

The inner it seals:

```json
{
  "said": "VFl7sd5qY0mHyiYIe40UsnkJB-ay7Bm4aL9pE2_L3N7N",
  "kind": "vdti/essr/v1/schemas/inner",
  "sender": "VJXt6jL06zmOACv4c3WENNyxExknjh36ljnNDGbhSi_5",
  "payload": "jA4YJ…3128 chars…Dvoc"
}
```

And the message handed to transport:

```json
{
  "said": "VEBc2yjMsZlPeneUPUjizin3e05d41dSa8fo2IFlaSJa",
  "kind": "vdti/essr/v1/schemas/message",
  "envelope": "VH1Pe6mCOzc0HMaCy9-jfbRvI2geCSkaoFAdqsQKbGdV",
  "signature": "1AAQtWdl_…4416 chars…swX6"
}
```

### IPEX — `vdti/ipex/v1/*`

Six message kinds `vdti/ipex/v1/schemas/{apply,offer,agree,grant,admit,spurn}`, each a signed SAD
threaded by `previous` ([`../../protocols/ipex.md`](../../protocols/ipex.md)). Only the **`grant`**
— the disclosure and its presentation-freshness envelope — carries content and a distinct shape:

| Field       | Type      | Required | Meaning                                                                                                     |
| ----------- | --------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| `said`      | SAID      | yes      | Commits every field below; the signature is over it.                                                        |
| `kind`      | string    | yes      | `vdti/ipex/v1/schemas/grant`.                                                                               |
| `previous`  | SAID      | no       | The `agree` this grant answers (absent for a minimal push).                                                 |
| `discloser` | prefix    | yes      | The discloser's IEL prefix — equals the SAD's committed issuee if targeted.                                 |
| `audience`  | prefix    | yes      | The verifier's IEL prefix — binds the disclosure to one recipient.                                          |
| `nonce`     | bytes     | yes      | Per-presentation, high-entropy — the replay-dedup entropy.                                                  |
| `created`   | timestamp | yes      | Bounds cache retention; never a trust input.                                                                |
| `challenge` | bytes     | no       | Echoes the verifier's `apply` challenge (stronger-liveness mode).                                           |
| `disclosed` | SAD       | yes      | The disclosed SAD (nested) — expanded inline at full disclosure, or the committed SAID at a graduated step. |

An IPEX grant disclosing a credential to one verifier, echoing that verifier's challenge:

```json
{
  "said": "VB594R2zxsPwt4GEezZiAMgvbXrS_uTaFsVxle4Rn5I_",
  "kind": "vdti/ipex/v1/schemas/grant",
  "previous": "VPqcFsdzU_0VNrwdacpCQpojFovhd9zeepSYeoGcazLJ",
  "discloser": "VHtuYkcj-xvUt10PlrALbz9G6W32t_faH62mLM24cI__",
  "audience": "VDlo7nhbKgLiU9BTODTJDy60RyRu1VHuOo7q7tvYN7zz",
  "nonce": "NBIVXGamcIf9k1r_atIcU3vvFW1Yd5n5SwJa3o9IgFei",
  "created": "2027-02-19T14:05:00Z",
  "challenge": "NGnHdpCYVbQBkE63BNBvNPXxkvE4r6ApJA25IQ9VXvzJ",
  "disclosed": "VE4zuHh228ik_6Y2kKSdrEJsrUyfLBonw3DfhZvLfZFa"
}
```

The other five messages (`apply` / `offer` / `agree` / `admit` / `spurn`) are lightweight
negotiation and acknowledgement SADs, each `{ said, kind, previous?, … }` signed by its sender;
their shapes land with [`../../protocols/ipex.md`](../../protocols/ipex.md).

## Feature SADs

### Credentials — `{namespace}/cred/v1/schemas/*`

A credential is a **direct-anchored** SAD (its issuance is a commitment hash on the issuer's IEL
`Ixn` — [`../../../features/credentials.md`](../../../features/credentials.md)), not a chain event.
Its `kind` names its **type** (application-registered — a diploma, an accreditation); the wrapper
below is common to every type.

| Field            | Type         | Required | Meaning                                                                                                                                                                                                                                                            |
| ---------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `said`           | SAID         | yes      | The credential's SAID — its immutable anchor.                                                                                                                                                                                                                      |
| `kind`           | string       | yes      | `{namespace}/cred/v1/schemas/*` — the credential's registered type, under the issuing application's own namespace.                                                                                                                                                 |
| `issuer`         | prefix       | yes      | The issuer's IEL prefix.                                                                                                                                                                                                                                           |
| `issuerPin`      | SAID         | yes      | The anchoring `Ixn`'s `previous` — locates the anchor at `previous.serial + 1`.                                                                                                                                                                                    |
| `issuee`         | prefix       | no       | The issuee's IEL prefix; **absent → a bearer credential**.                                                                                                                                                                                                         |
| `delegationPath` | list⟨prefix⟩ | no       | Present iff issued under **delegated** authority — the ordered committed path, the issuer's immediate delegator up to and including the policy root ([`../../policy/documents.md` §Delegation in a document](../../policy/documents.md#delegation-in-a-document)). |
| `claims`         | SAD          | yes      | A claims SAD (nested → partial disclosure).                                                                                                                                                                                                                        |
| `terms`          | SAD          | no       | An issuer-set terms-of-use SAD (nested); travels with the credential.                                                                                                                                                                                              |
| `issued`         | timestamp    | yes      | Issuance time (advisory).                                                                                                                                                                                                                                          |
| `expires`        | timestamp    | no       | Expiry (advisory).                                                                                                                                                                                                                                                 |
| `nonce`          | bytes        | yes      | High-entropy — every credential has one; makes `said` unguessable.                                                                                                                                                                                                 |

A credential — issued to a named issuee, its claims committed as a nested SAD:

```json
{
  "said": "VE4zuHh228ik_6Y2kKSdrEJsrUyfLBonw3DfhZvLfZFa",
  "kind": "edu.example/cred/v1/schemas/diploma",
  "issuer": "VElLsE-OyAXGgppj-erWYi8p9ZT8ESPM-mRG0mdGJWZs",
  "issuerPin": "VI_HNqk8NS8FZpndtBIxghQ7e9HCoBrUIlKkG7ZDHtBK",
  "issuee": "VHtuYkcj-xvUt10PlrALbz9G6W32t_faH62mLM24cI__",
  "claims": "VPZZwj5IkgYKm7Y8Id2PDQs8qdDlTObguJALSR3i4IVw",
  "issued": "2026-06-12T00:00:00Z",
  "nonce": "NGHI7PQOXzRpR1IW92XiGjlJqLmS5U7az6PF_H9-RfkP"
}
```

The `claims` field is the SAID of a **claims SAD** (`vdti/cred/v1/claims/*`, application-defined).
Each gated predicate it carries is a **uniformly-shaped blinded claim** —
`{ said, kind, nonce, data }`: the per-claim `said` is what the credential commits; its `kind` is a
**type-generic** blinded kind (`vdti/cred/v1/claims/blinded-{string,number,boolean,object,array}`,
naming the JSON type of `data`, never the predicate — it rides _inside_ the blinded `said`); a
high-entropy `nonce` blinds it so a compacted claim leaks neither presence nor value; and `data` is
the application-shaped value (a boolean bracket like `ageGTE18`, a field). Disclosing a claim
reveals its `{ kind, nonce, data }` and recomputes the `said` against the commitment
([claim-gating](../../../features/credentials.md#claim-gating)).

The claims SAD it commits, each position a blinded claim:

```json
{
  "said": "VPZZwj5IkgYKm7Y8Id2PDQs8qdDlTObguJALSR3i4IVw",
  "kind": "vdti/cred/v1/claims/diploma",
  "program": "VMAjOHlirOCjxmKvS9FhrB3rqY_wZDpgGDtt18LGwKCr",
  "honours": "VAIv1BuHZKhmsiwkkC9QWSFhGnOkQ4iVem1M64GYEf46"
}
```

And one of those blinded claims, disclosed:

```json
{
  "said": "VMAjOHlirOCjxmKvS9FhrB3rqY_wZDpgGDtt18LGwKCr",
  "kind": "vdti/cred/v1/claims/blinded-string",
  "nonce": "NJbXoEyJmx4UyRjsK1YzWYwtUPJIWvs8xEAZaIUMRbdi",
  "data": "Bachelor of Science, Mathematics"
}
```

### Shared documents — `vdti/doc/v1/schemas/*`

The **V0 constitution** (derives the doc prefix):

| Field     | Type   | Meaning                                                                                                                                    |
| --------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `said`    | SAID   | V0's SAID.                                                                                                                                 |
| `kind`    | string | `vdti/doc/v1/schemas/inception`.                                                                                                           |
| `creator` | prefix | The creator's IEL prefix — governs membership and sharing.                                                                                 |
| `prefix`  | prefix | The doc prefix — derived from V0's whole content (nonce'd → unguessable if private).                                                       |
| `custody` | struct | `{ readers[] }` — the initial read gate: the three `document-*-membership` SEL prefixes (edit ∪ comment ∪ read), sorted; omitted → public. |
| `nonce`   | bytes  | Required, high-entropy — the governance chains derive from it (their `data`); makes the doc prefix unguessable if private.                 |

A document constitution — the prefix derived from V0's whole content, read gated to the three
membership sets:

```json
{
  "said": "VCcxGlmMZoVFZkXRZaEVlTkKT1xIl7TWNfYojMGdm77z",
  "kind": "vdti/doc/v1/schemas/inception",
  "creator": "VPizZoOnwJRA49T4s4chJWaYitEGdaT9GnnfxLVJ3sOr",
  "prefix": "VJtuETsV6ilSO862FC0tZwFJcH_3KvPEmqcaCPSLv57i",
  "custody": {
    "readers": [
      "VAEG-JGv8VpxZDGLbgVSs2E2esUHNnhJIhZEQNbLEGU-",
      "VKR8MWlkqxaB66cX0eBGSevGDVJEfpBH3GEWypzQzijW",
      "VNn4P3wS2lsHKnHpgHuaQQdjQn4dLGI3CX2etZ3wyT4B"
    ]
  },
  "nonce": "NEzNnqgUYDVcAZWim_hSFTX6ikDMtRA5JWk7df5tV3jE"
}
```

A **version** SAD (custody-attributed, chained into the version DAG):

| Field       | Type       | Meaning                                                                                    |
| ----------- | ---------- | ------------------------------------------------------------------------------------------ |
| `said`      | SAID       | The version's SAID.                                                                        |
| `kind`      | string     | `vdti/doc/v1/schemas/version`.                                                             |
| `custody`   | struct     | `{ owner: the editor's IEL, pin, readers[] }` — the sorted union read gate.                |
| `ancestors` | list⟨SAID⟩ | Parent version SAID(s) — the multi-parent DAG.                                             |
| `prefix`    | prefix     | The doc prefix.                                                                            |
| `grant`     | SAID       | `said(G)` — the authorizing `document-edit-membership` grant.                              |
| `content`   | SAD        | The version body.                                                                          |
| `edited`    | timestamp  | Advisory feature timestamp.                                                                |
| `nonce`     | bytes      | High-entropy — makes the version SAID unguessable for a private doc (omitted when public). |

A version of that document, attributed to its editor:

```json
{
  "said": "VBkY_BEDBAxqATM51I1k34_kyzFEl8Be2cGcutMyoF3S",
  "kind": "vdti/doc/v1/schemas/version",
  "custody": {
    "owner": "VLvUNGfh7zI4LbYHGxAZncd0xPKEBIOtMbo3VmHcw91y",
    "pin": "VGHf6jFyEy8jA8XH8rWX4SraWj4brlnGF07QUrawiYxl",
    "readers": [
      "VAEG-JGv8VpxZDGLbgVSs2E2esUHNnhJIhZEQNbLEGU-",
      "VKR8MWlkqxaB66cX0eBGSevGDVJEfpBH3GEWypzQzijW",
      "VNn4P3wS2lsHKnHpgHuaQQdjQn4dLGI3CX2etZ3wyT4B"
    ]
  },
  "ancestors": ["VGRMaOp65WuBcYIQd_zafR5LneVUiAU5sBCqh4jwlKAZ"],
  "prefix": "VJtuETsV6ilSO862FC0tZwFJcH_3KvPEmqcaCPSLv57i",
  "grant": "VH-JkJsNTy1fqb0_2DgJA8XbHeX4QQR4Pf-udu-suBJs",
  "content": "VJgLs7j7PLDhX6DD_FJu999h3tg8N_8eqIk6wA-d9jpX",
  "edited": "2027-01-22T16:41:12Z",
  "nonce": "NDwiOm2W4zBEQbidp5g6Kq4juNc7VINJfXYnS4Fa8u-_"
}
```

The **grant-doc** — the `{ grants, rescinds }` delta a `Gnt` seals, one shape shared by the three
instances `document-edit-membership` / `document-comment-membership` / `document-read-membership`,
the kind naming the role — is `{ said, kind, custody{ readers[] }, grants, rescinds }`: `grants` a
list of nonce'd blinded commitments `{ said, kind, <role>, from, nonce, custody{ readers[] } }`
(each entry's role value is the member's IEL prefix, its `said` the rescission handle), `rescinds` a
list of blinded targets. Each rescind also carries a per-member `{ Icp, Trm }` lookup whose `Trm`
seals the grandfather cutoff in the gated **rescind-doc**
`{ said, kind, custody{ readers[] }, <role>, bound, nonce }`. Both are **owned and defined by**
[shared documents](../../../features/shared-documents.md) — this catalogue registers them; only
their byte-level layout is owed.

The **comment** kinds are direct-anchored SADs (no SEL topic, like a version), so both carry the
same `custody { owner, pin, readers[] }` wrapper, `prefix`, and `nonce?` a version does; the
may-comment capability (edit ∪ comment) gates them, and an edit (`supersedes`) is author-only
([`../../../features/shared-documents.md`](../../../features/shared-documents.md)).

A **comment** (`vdti/doc/v1/schemas/comment`):

| Field        | Type   | Meaning                                                                      |
| ------------ | ------ | ---------------------------------------------------------------------------- |
| `said`       | SAID   | The comment's SAID.                                                          |
| `kind`       | string | `vdti/doc/v1/schemas/comment`.                                               |
| `custody`    | struct | `{ owner: the commenter's IEL, pin, readers[] }` — may-comment gated.        |
| `prefix`     | prefix | The doc prefix.                                                              |
| `target`     | SAID   | The one version SAID this comments on.                                       |
| `locator`    | opaque | **App-defined** — where in the content it attaches. VDTI stays format-blind. |
| `content`    | opaque | **App-defined** — the comment body.                                          |
| `parent`     | SAID   | Optional — an earlier comment it replies to (threading, acyclic by SAID).    |
| `supersedes` | SAID   | Optional — an earlier comment it edits (VDTI checks same `owner`).           |
| `nonce`      | bytes  | High-entropy — makes the SAID unguessable for a private doc.                 |

A comment on that version:

```json
{
  "said": "VL4vaPWeNL6KsngSsHXn9FQMws3LrBIQK2ZfnBSOwFvu",
  "kind": "vdti/doc/v1/schemas/comment",
  "custody": {
    "owner": "VEQ7-Dq2NJDkTZM9p9XdLV5nnZcCtc6r1oRnYF3_6iH2",
    "pin": "VK-pt5WqdDIl7MVecGWmJW2-kKHV71nRzAM1lKkvcCF4",
    "readers": [
      "VAEG-JGv8VpxZDGLbgVSs2E2esUHNnhJIhZEQNbLEGU-",
      "VKR8MWlkqxaB66cX0eBGSevGDVJEfpBH3GEWypzQzijW",
      "VNn4P3wS2lsHKnHpgHuaQQdjQn4dLGI3CX2etZ3wyT4B"
    ]
  },
  "prefix": "VJtuETsV6ilSO862FC0tZwFJcH_3KvPEmqcaCPSLv57i",
  "target": "VBkY_BEDBAxqATM51I1k34_kyzFEl8Be2cGcutMyoF3S",
  "locator": "cGFyYToxNy1yYW5nZTo0MDgsNDQx",
  "content": "VGhpcyBjbGF1c2UgY29udHJhZGljdHMgwqcyLg",
  "nonce": "NGx38x3H9me1bfM-FZdcNgmPzWz-mcn0GawBaANo20iv"
}
```

A **comment-resolution** (`vdti/doc/v1/schemas/comment-resolution`, append-only):

| Field      | Type   | Meaning                                                      |
| ---------- | ------ | ------------------------------------------------------------ |
| `said`     | SAID   | The resolution's SAID.                                       |
| `kind`     | string | `vdti/doc/v1/schemas/comment-resolution`.                    |
| `custody`  | struct | `{ owner, pin, readers[] }` — may-comment gated.             |
| `prefix`   | prefix | The doc prefix.                                              |
| `comment`  | SAID   | The comment SAID resolved / reopened.                        |
| `resolved` | bool   | Resolved (`true`) or reopened (`false`).                     |
| `nonce`    | bytes  | High-entropy — makes the SAID unguessable for a private doc. |

And the resolution that closes it:

```json
{
  "said": "VHgLpqfiuB4B3uvKB0M6KLYKOk9YSUKdKfdtN4w2rqkt",
  "kind": "vdti/doc/v1/schemas/comment-resolution",
  "custody": {
    "owner": "VLvUNGfh7zI4LbYHGxAZncd0xPKEBIOtMbo3VmHcw91y",
    "pin": "VGHf6jFyEy8jA8XH8rWX4SraWj4brlnGF07QUrawiYxl",
    "readers": [
      "VAEG-JGv8VpxZDGLbgVSs2E2esUHNnhJIhZEQNbLEGU-",
      "VKR8MWlkqxaB66cX0eBGSevGDVJEfpBH3GEWypzQzijW",
      "VNn4P3wS2lsHKnHpgHuaQQdjQn4dLGI3CX2etZ3wyT4B"
    ]
  },
  "prefix": "VJtuETsV6ilSO862FC0tZwFJcH_3KvPEmqcaCPSLv57i",
  "comment": "VL4vaPWeNL6KsngSsHXn9FQMws3LrBIQK2ZfnBSOwFvu",
  "resolved": true,
  "nonce": "NBTxVRJ-9FE5A0bOhdoEaq-KTA585FzBysCwLnssgDIm"
}
```

### Exchange — `vdti/exchange/v1/*`

Exchange defines one message SAD of its own — the **chat message**, on a per-sender lane. The
one-off async message is the **ESSR message** (Protocol SADs above — its envelope commits its stored
payload by storage key), scoped to the recipient's inbox nodes by `availability`; the
issuance/presentation messages (`apply` / `offer` / …) are **IPEX**'s (above).

The **chat message** (`vdti/exchange/v1/schemas/message`) — sender-signed, on the writer's lane:

| Field           | Type      | Meaning                                                                                                                                                                                                                                            |
| --------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said`          | SAID      | The message SAID; the writer signs it.                                                                                                                                                                                                             |
| `kind`          | string    | `vdti/exchange/v1/schemas/message`.                                                                                                                                                                                                                |
| `previous`      | SAID      | The writer's **own** prior node on this lane — the join **marker** at lane start, else a prior message. A message always chains; it never roots a lane (the body-less marker does, carrying the device prefix, attributed to its owning identity). |
| `epoch`         | SAID      | The group-key epoch the body is encrypted under (the witnessed epoch window).                                                                                                                                                                      |
| `payloadDigest` | digest    | The encrypted message body's stored **payload** — the storage key `S` over `bundle.said ‖ blob` (integrity-bearing).                                                                                                                               |
| `payloadSize`   | u64       | The payload's byte length — advisory (allocation/pre-fetch bound), not integrity.                                                                                                                                                                  |
| `timestamp`     | timestamp | Orders messages within the epoch window (advisory; never establishes currency).                                                                                                                                                                    |
| `nonce`         | bytes     | High-entropy — makes `said` unguessable, so a **guessable** message body can't be confirmed against the public SAID (a known-plaintext oracle on the symmetric-encrypted chat content). Mandatory.                                                 |

A chat message on its writer's lane — no sender field, because the lane is the writer:

```json
{
  "said": "VDrwnP9OUhPgovSUYVEqjDPVFpurGBQHKmnlZUajYsWe",
  "kind": "vdti/exchange/v1/schemas/message",
  "previous": "VJxrsLs00bA2vthvN4ulLpdOQ3IsrpLpODTlkddIyfwZ",
  "epoch": "VIjxuCYW-bRg1uee5aopht-UGHsnGtQbAALYciLiwkBi",
  "payloadDigest": "VD7xHeI1Da4Ek6jq1xXq8Em_zojJd0om7fhBb7P9uiJ-",
  "payloadSize": 1184,
  "timestamp": "2027-03-08T21:14:33Z",
  "nonce": "NDqJesTL9DIP8CxmI74PF-WLuoOWoV41G2ikGq6bbZF5"
}
```

There is no `sender` field — the **lane is the writer**: the receiver derives the per-writer subkey
from the lane, decrypts, and verifies the writer's signature. A lane **roots at a body-less join
marker** the writing device mints — a distinct SAD carrying the device prefix and no body (its shape
is forthcoming, below) — and every message chains from it via `previous` and **inherits** the
writer, so no message carries a `writer` field. That marker is **anchored** by a `chat-membership`
grant-chain act, so each writing **device** has exactly one honored lane per membership period — an
unanchored root is rejected ([membership](../../protocols/membership.md) /
[exchange](../../../features/exchange.md)). The lane is a **single-parent
[authored DAG](../../protocols/authored-dag.md)**: `(epoch, timestamp)` is **non-decreasing** along
`previous` (a backdated tip-append is malformed), and a **second child of a message is a fork =
equivocation** (self-signed evidence; a crash-**resend** carries the same SAID — a dedup — so
whether a fork is misbehavior is the group's policy, not automatic). The writer's signature over
`said` rides **adjacent** (the universal rule — a SAD carries no signature over its own SAID), so
there is no signature field.

The **mail payload** (`vdti/exchange/v1/schemas/mail-payload`) — the ESSR inner payload a mail
message seals, so it rides inside the ciphertext and never on the envelope
([`../../../features/exchange.md`](../../../features/exchange.md)):

| Field       | Type      | Required | Meaning                                                                                            |
| ----------- | --------- | -------- | -------------------------------------------------------------------------------------------------- |
| `said`      | SAID      | yes      | The payload's own SAID.                                                                            |
| `kind`      | string    | yes      | `vdti/exchange/v1/schemas/mail-payload`.                                                           |
| `topic`     | string    | yes      | The message topic — `vdti/exchange/v1/topics/exchange`, the one exchange reserves.                 |
| `timestamp` | timestamp | yes      | The send time — checked **post-decrypt**, and **refuse-on-absent** (a missing one is fail-secure). |
| `body`      | bytes     | yes      | The content — a message, or a carried SAD such as an IPEX message riding inside.                   |

The payload a mail message seals — topic, the refuse-on-absent send time, and the body:

```json
{
  "said": "VGR33HkBiGxY4t1RzsLxeiEq4LqzuQwOaSxz2RqielPa",
  "kind": "vdti/exchange/v1/schemas/mail-payload",
  "topic": "vdti/exchange/v1/topics/exchange",
  "timestamp": "2027-04-02T11:38:20Z",
  "body": "BDk7d…2744 chars…h3yc"
}
```

### Policy — `vdti/policy/v1/{group}/*`

A policy is a SAD carrying one **expression** ([`../../policy/policy.md`](../../policy/policy.md)):

| Form                     | Kind     | Meaning                                                                                                                       |
| ------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `id(prefix)`             | leaf     | An identity.                                                                                                                  |
| `del(prefix, N)`         | leaf     | A live delegate of an identity, within `N` hops (`del(X)` = `del(X, 1)`).                                                     |
| `pol(said)`              | leaf     | Another policy, by its SAID (the reference graph is acyclic).                                                                 |
| `crd(kind, expr)`        | leaf     | A holder of a live credential of this kind, issued under `expr` ([`../../policy/evaluation.md`](../../policy/evaluation.md)). |
| `thr(M, [expr, …])`      | composer | At least `M` of the listed sub-policies.                                                                                      |
| `wgt(M, [(expr, w), …])` | composer | Sub-policies carry weights; satisfied when the satisfied weights total `≥ M`.                                                 |
| `and(expr, …)`           | composer | Every listed sub-policy (`≥ 2`); pools independent only when the author makes them disjoint.                                  |

## Forthcoming shapes

Each row is a kind whose **field set** is still owed, and where it lands. The **final row** is
different in kind: it collects the SADs whose fields are already fixed — here or in their owning doc
— and owe only a byte-level layout.

| Kind / SAD                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Lands at                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Group epoch-key grant value (`groupkey-epoch-key`) — the per-device ESSR wrap (each names its recipient in the clear; the epoch key's at-rest form)                                                                                                                                                                                                                                                                                                              | the encoding library (ESSR-wrap layout) |
| Chat-membership grant value (`chat-membership`) — the `{ grants, rescinds }` membership-delta grant-doc (a grant-chain entry anchors a writing device's body-less lane-root marker; a `rescinds` entry records each device lane's `bound` on the rescission `Trm`'s `bound` role) + the body-less join-marker shape (commits the **device prefix + group prefix + membership period / grant-instance** — structurally bound to one group, single-use per period) | the exchange encode                     |
| Delegation marker (`delegation`) — the blinded-reference layout (how the delegate reference is blinded and checked against the anchoring `Ath`'s `delegates`)                                                                                                                                                                                                                                                                                                    | the encoding library                    |
| **Fields fixed, byte-level layout owed** — the receive-key grant value (`directory-kem`, §Grant values), the block marker and trusted-federation grant value (`{ said, kind, reason? }`; `{ remotePrefix, bound }`), the mail payload (§Exchange), and the shared-document grant-doc / rescind-doc (§Shared documents)                                                                                                                                           | the encoding library                    |

## Cross-references

- [`kinds.md`](kinds.md) — the kind catalogue (the identifier for each SAD type).
- [`sad.md`](sad.md) — what a SAD is; the wrapper; the fetch-by-SAID rule.
- [`custody.md`](custody.md) / [`availability.md`](availability.md) — the two wrapper structs.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the authoritative per-kind
  chain-event shapes and the manifest role model.
