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
**u64** — an unsigned integer; **bool**; **bytes**; **timestamp** — an RFC 3339 time; **list⟨T⟩**.

## The two shapes

A SAD is one of two shapes ([`sad.md` §Structural shapes](sad.md#structural-shapes)):

- A **chain event** — a SAD with chain-linkage fields (`prefix`, `previous`, `serial`) that lives on
  a KEL / IEL / SEL and replicates as an indivisible unit. Its schema has **no** slot for `custody`
  or `availability`.
- A **standalone SAD** — everything else (a receipt, a config, a credential, a policy, an exchange
  envelope, the content payloads an event anchors). It is stored in the SAD object store and served
  by SAID, and MAY carry `custody` and `availability` on its wrapper.

## The standalone-SAD wrapper

Every standalone SAD carries these top-level fields, then its kind-specific content:

| Field          | Type   | Required | Meaning                                                                       |
| -------------- | ------ | -------- | ----------------------------------------------------------------------------- |
| `said`         | SAID   | yes      | The SAD's self-addressing identifier ([`said.md`](said.md)).                  |
| `kind`         | string | yes      | The versioned type name ([`kinds.md`](kinds.md)); drives validation.          |
| `custody`      | struct | no       | Per-object authority — who may write and read ([`custody.md`](custody.md)).   |
| `availability` | struct | no       | Where the bytes live and for how long ([`availability.md`](availability.md)). |

`custody` and `availability` are inline structs, each sub-field independently optional:

- **`custody { owner, pin, readers }`** — `owner` is the writer's IEL prefix and `pin` locates the
  owner-IEL `Ixn` that anchored the write (both-or-neither; the SAD's own `kind` names its type, so
  no separate `topic`), `readers` the prefix of a read-authorization SEL that gates reads (`None` →
  public).
- **`availability { replicas, ttl, once }`** — `replicas` the SAID of a replica-set SAD (absent →
  everywhere), `ttl` a retention bound, `once` a destructive-read flag.

## The file payload — `vdti/sad/v1/schemas/file`

The SAD layer's general content wrapper: a standalone SAD that names **bulk opaque bytes** — an
encrypted payload, a file, media — as a **content-addressed blob** rather than inlining them
([`sad.md` §Bulk opaque bytes](sad.md#bulk-opaque-bytes--the-content-addressed-blob)).

| Field       | Type   | Required | Meaning                                                           |
| ----------- | ------ | -------- | ----------------------------------------------------------------- |
| `said`      | SAID   | yes      | The file SAD's SAID.                                              |
| `kind`      | string | yes      | `vdti/sad/v1/schemas/file`.                                       |
| `digest`    | digest | yes      | Blake3-256 content-address of the raw blob — committed by `said`. |
| `size`      | u64    | yes      | The blob's byte length.                                           |
| `mediaType` | string | no       | Advisory MIME type.                                               |
| `name`      | string | no       | Advisory filename.                                                |
| `nonce`     | bytes  | yes      | High-entropy — makes `said` unguessable for a private file.       |

The `custody` / `availability` wrapper applies as to any standalone SAD: `custody.readers` gates who
may fetch, and `availability` governs the referenced **blob** (its replicas, TTL, one-shot) as well
as the SAD. The blob is opaque bytes — not a SAD, no `kind` of its own — fetched **by digest** from
the store's blob path and accepted only when its recomputed digest matches `digest`.

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
`federation` / `federationPin`, the IEL's `pins` and `nonce`, the SEL's `owner` / `topic` / `data` /
`content` / `lineage` / `pin`. Each event kind's full required/optional/forbidden table is
[`event-shape.md` §Per-kind structural validation](../event-logs/event-shape.md); the shared field
meanings are its §Common fields and §Cross-cutting fields.

## Commitment SADs — what a `manifest` names

A committing event's `manifest` is the SAID of a **role-grouped commitment SAD**:
`{ said, <role>: <value>, … }`, where each role is a named commitment. The role vocabulary and which
kind may carry which role are [`event-shape.md` §The manifest](../event-logs/event-shape.md); the
roles that resolve to their **own** SAD are catalogued here.

### `vdti/event/v1/roles/witnesses` — the witness-config

| Field       | Type   | Meaning                                                       |
| ----------- | ------ | ------------------------------------------------------------- |
| `said`      | SAID   | The config SAD's SAID.                                        |
| `kind`      | string | `vdti/event/v1/roles/witnesses`.                              |
| `threshold` | u64    | Valid receipts a consumer requires before it trusts an event. |
| `signers`   | u64    | Witnesses selected per event; `signers ≥ threshold`.          |

Bounded `signers/2 < threshold ≤ signers ≤ |roster|`, with a tighter recoverability cap on the
federation IEL
([`../../../substrate/federation/witnessing.md`](../../../substrate/federation/witnessing.md)).

### `vdti/event/v1/roles/roster` — a roster / threshold delta

Carried by an IEL `Icp` (the initial roster + threshold vector), an `Evl` (a delta), and a
federation `Fcp` / `Wit`:

| Field            | Type                         | Meaning                                                                                          |
| ---------------- | ---------------------------- | ------------------------------------------------------------------------------------------------ |
| `said`           | SAID                         | The delta SAD's SAID.                                                                            |
| `kind`           | string                       | `vdti/event/v1/roles/roster`.                                                                    |
| `add`            | list⟨prefix⟩                 | Member KEL prefixes added (the full initial set at inception).                                   |
| `cut`            | list⟨prefix⟩                 | Member KEL prefixes removed (a `cut` on an `Evl` evicts).                                        |
| threshold vector | `{ use, authorize, govern }` | The declared or changed threshold counts — content (tier 1), governance, authorization (tier 2). |

A delta is a **set** change — well-formed only with `add ∉` the roster, `cut ⊆` it, `cut ∩ add = ∅`,
and the post-delta size `|roster| + |add| − |cut|` between `1` and `MAXIMUM_ROSTER_SIZE` (32); the
threshold bounds are re-checked on the post-delta config
([`../event-logs/iel/events.md`](../event-logs/iel/events.md)). On a **federation `Wit`**, `add` is
a **single** prefix (one witness KEL added at a time), not a list.

### `vdti/event/v1/roles/pins` — the participating member KEL SAIDs

| Field  | Type       | Meaning                                                                |
| ------ | ---------- | ---------------------------------------------------------------------- |
| `said` | SAID       | The pins SAD's SAID.                                                   |
| `kind` | string     | `vdti/event/v1/roles/pins`.                                            |
| `pins` | list⟨SAID⟩ | Each participating member's KEL event SAID (an IEL event's down-pins). |

The remaining roles — `anchors`, `delegates`, `payload`, `kills`, and the scalar `clock` — are
carried **inline** in the manifest SAD, so they have no SAD of their own ([`kinds.md`](kinds.md));
the `bound` and `grant` roles each name a SAD of their own (the gated rescind-doc, and the grant
value — §Grant values below). Their value shapes are
[`event-shape.md` §The manifest](../event-logs/event-shape.md).

## Witness receipts

A receipt is itself a SAD; its witness signature rides **adjacent**, never in the body (a SAD cannot
sign over its own `said`). One kind per witnessed chain — `vdti/witness/v1/receipts/{kel,iel,sel}`.

| Field            | Type      | Meaning                                                           |
| ---------------- | --------- | ----------------------------------------------------------------- |
| `said`           | SAID      | The receipt's own SAID.                                           |
| `kind`           | string    | `vdti/witness/v1/receipts/{kel,iel,sel}`.                         |
| `threshold`      | u64       | The witness-config threshold in effect at the witnessed position. |
| `signers`        | u64       | The selection size in effect at that position.                    |
| `federationPin`  | SAID      | The chain's federation binding there — resolves the as-of roster. |
| `chain_prefix`   | prefix    | The witnessed chain's prefix.                                     |
| `event_said`     | SAID      | The one committing SAID of the witnessed event.                   |
| `event_serial`   | u64       | Its serial.                                                       |
| `timestamp`      | timestamp | The witness's asserted time (inside the signed payload).          |
| `witness_prefix` | prefix    | The signing witness's KEL prefix.                                 |

## Grant values — what a SEL `Gnt` seals

A SEL `Gnt`'s `manifest.grant` names a **grant-value SAD** whose kind is `vdti/sel/v1/grants/*`. The
value it carries is the sealed thing itself.

| Kind                                                 | Carries                                                                                                                                                                                                                     | Status      |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `vdti/sel/v1/grants/directory-ml-kem-1024`           | A published ML-KEM-1024 receive key (scheme-tagged public key + optional hardware attestation) + inbox-node hints.                                                                                                          | forthcoming |
| `vdti/sel/v1/grants/directory-ml-kem-768`            | The reduced-tier ML-KEM-768 receive key + inbox-node hints.                                                                                                                                                                 | forthcoming |
| `vdti/sel/v1/grants/groupkey-epoch-key`              | A group epoch key, ESSR-wrapped once per member device.                                                                                                                                                                     | forthcoming |
| `vdti/sel/v1/grants/shared-document-governance`      | The grant-doc — `editors` / `commenters` role-lists.                                                                                                                                                                        | forthcoming |
| `vdti/sel/v1/grants/shared-document-read-governance` | The read grant-doc — the `readers` role-list only.                                                                                                                                                                          | forthcoming |
| `vdti/sel/v1/grants/chat-membership`                 | The `{ grants, rescinds }` membership-delta grant-doc (exchange) — a `grants` entry anchors a writing device's body-less lane root; a `rescinds` entry records its lane-tip `bound` on the rescission `Trm`'s `bound` role. | forthcoming |

Each grant value is a SAD (`said` + `kind` + its value); the concrete value layouts land at the
encoding library (the scheme-tagged keys and ESSR wraps) and the shared-documents encode (the
role-lists).

The **directory receive-key** grant value carries the reachability a sender needs — the key to seal
to and where to deliver:

| Field         | Type         | Meaning                                                            |
| ------------- | ------------ | ------------------------------------------------------------------ |
| `said`        | SAID         | The grant value's SAID.                                            |
| `kind`        | string       | `vdti/sel/v1/grants/directory-ml-kem-1024` (or `-768`).            |
| `receiveKey`  | bytes        | The scheme-tagged ML-KEM public key others seal to.                |
| `attestation` | bytes        | Optional — a vendor-signed hardware attestation.                   |
| `nodeHints`   | list⟨string⟩ | The storage nodes where a message sealed to this key is deposited. |

(The scheme-tagged key and attestation byte layouts land at the encoding library; the structural
fields — including the `nodeHints` exchange delivers against — are fixed here.)

## Protocol SADs

### ESSR — `vdti/essr/v1/*`

The **envelope** (`vdti/essr/v1/schemas/envelope`) — the signed cleartext; its signature rides
adjacent ([`../../protocols/essr.md`](../../protocols/essr.md)):

| Field           | Type   | Meaning                                                                                                               |
| --------------- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| `said`          | SAID   | The envelope SAID — commits every field below; the signature is over it.                                              |
| `kind`          | string | `vdti/essr/v1/schemas/envelope`.                                                                                      |
| `sender`        | prefix | The sender's IEL prefix (cleartext — routes and fetches the verify key).                                              |
| `senderPin`     | SAID   | The sender's establishment event current at signing — the verifying state.                                            |
| `recipient`     | prefix | The recipient's IEL prefix (signed — the recipient binding).                                                          |
| `kemCiphertext` | bytes  | The key-encapsulation to the recipient's receive key — small, inline (derives the key).                               |
| `payloadDigest` | digest | Commitment to the sealed inner (the encrypted payload) — a content-addressed blob, not the bytes (integrity-bearing). |
| `payloadSize`   | u64    | The encrypted payload's byte length — advisory (allocation / pre-fetch bound), not integrity.                         |
| `nonce`         | bytes  | The sealing nonce (fresh random per message).                                                                         |

The **inner** (`vdti/essr/v1/schemas/inner`, sealed) is `{ said, kind, sender, payload }` — the
sender prefix (the binding that rides inside the sealed content) and the opaque payload; a message
timestamp or protocol label rides _inside_ `payload`, not as an envelope field. The **sealed inner
(the ciphertext) is not carried in the envelope** — it rides as a content-addressed blob named by
the envelope's `payloadDigest` (+ `payloadSize`), fetched by digest and checked before decryption:
the **digest is integrity-bearing** (a recomputed-digest mismatch is the only tamper signal), the
**size advisory** (an allocation / pre-fetch bound, never treated as tamper-evidence). The
**message** (`vdti/essr/v1/schemas/message`) is `{ said, kind, envelope, signature }` — the envelope
SAD plus the sender's signature over `envelope.said`.

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

The other five messages (`apply` / `offer` / `agree` / `admit` / `spurn`) are lightweight
negotiation and acknowledgement SADs, each `{ said, kind, previous?, … }` signed by its sender;
their shapes land with [`../../protocols/ipex.md`](../../protocols/ipex.md).

## Feature SADs

### Credentials — `vdti/cred/v1/schemas/*`

A credential is a **direct-anchored** SAD (its issuance is a commitment hash on the issuer's IEL
`Ixn` — [`../../../features/credentials.md`](../../../features/credentials.md)), not a chain event.
Its `kind` names its **type** (application-registered — a diploma, an accreditation); the wrapper
below is common to every type.

| Field       | Type      | Required | Meaning                                                                         |
| ----------- | --------- | -------- | ------------------------------------------------------------------------------- |
| `said`      | SAID      | yes      | The credential's SAID — its immutable anchor.                                   |
| `kind`      | string    | yes      | `vdti/cred/v1/schemas/*` — the credential's registered type.                    |
| `issuer`    | prefix    | yes      | The issuer's IEL prefix.                                                        |
| `issuerPin` | SAID      | yes      | The anchoring `Ixn`'s `previous` — locates the anchor at `previous.serial + 1`. |
| `issuee`    | prefix    | no       | The issuee's IEL prefix; **absent → a bearer credential**.                      |
| `claims`    | SAD       | yes      | A claims SAD (nested → partial disclosure).                                     |
| `terms`     | SAD       | no       | An issuer-set terms-of-use SAD (nested); travels with the credential.           |
| `issued`    | timestamp | yes      | Issuance time (advisory).                                                       |
| `expires`   | timestamp | no       | Expiry (advisory).                                                              |
| `nonce`     | bytes     | yes      | High-entropy — every credential has one; makes `said` unguessable.              |

The `claims` field is the SAID of a **claims SAD** (`vdti/cred/v1/claims/*`, application-defined).
Each gated predicate it carries is a **uniformly-shaped blinded claim** — `{ said, nonce, data }`:
the per-claim `said` is what the credential commits, a high-entropy `nonce` blinds it so a compacted
claim leaks neither presence nor value, and `data` is the application-shaped value (a boolean
bracket like `ageOver18`, a field). Disclosing a claim reveals its `{ nonce, data }` and recomputes
the `said` against the commitment ([claim-gating](../../../features/credentials.md#claim-gating)).

### Shared documents — `vdti/doc/v1/schemas/*`

The **V0 constitution** (derives the doc prefix):

| Field     | Type   | Meaning                                                                                                  |
| --------- | ------ | -------------------------------------------------------------------------------------------------------- |
| `said`    | SAID   | V0's SAID.                                                                                               |
| `kind`    | string | `vdti/doc/v1/schemas/*` (the constitution schema).                                                       |
| `creator` | prefix | The creator's IEL prefix — governs membership and sharing.                                               |
| `readers` | prefix | The initial read gate — the prefix of a read-authorization SEL, walked for membership (`None` → public). |
| `nonce`   | bytes  | High-entropy — makes the doc prefix unguessable if private.                                              |

A **version** SAD (custody-attributed, chained into the version DAG):

| Field       | Type       | Meaning                                            |
| ----------- | ---------- | -------------------------------------------------- |
| `said`      | SAID       | The version's SAID.                                |
| `kind`      | string     | `vdti/doc/v1/schemas/*`.                           |
| `custody`   | struct     | `{ owner: the editor's IEL, pin, readers }`.       |
| `ancestors` | list⟨SAID⟩ | Parent version SAID(s) — the multi-parent DAG.     |
| `nonce`     | bytes      | High-entropy — makes the version SAID unguessable. |

The **grant-doc** (`shared-document-governance`, editors/commenters role-lists), the **read
grant-doc** (`shared-document-read-governance`, the `readers` role-list only), and the **gated
rescind-doc** (a `bound` position sealing a membership period) are **forthcoming** — shapes at the
shared-documents encode
([`../../../features/shared-documents.md`](../../../features/shared-documents.md)).

### Exchange — `vdti/exchange/v1/*`

Exchange defines one message SAD of its own — the **chat message**, on a per-sender lane. The
one-off async message is the **ESSR message** (Protocol SADs above — its envelope names the payload
by digest), scoped to the recipient's inbox nodes by `availability`; the issuance/presentation
messages (`apply` / `offer` / …) are **IPEX**'s (above).

The **chat message** (`vdti/exchange/v1/schemas/message`) — sender-signed, on the writer's lane:

| Field           | Type      | Meaning                                                                                                                                                                                                                                            |
| --------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said`          | SAID      | The message SAID; the writer signs it.                                                                                                                                                                                                             |
| `kind`          | string    | `vdti/exchange/v1/schemas/message`.                                                                                                                                                                                                                |
| `previous`      | SAID      | The writer's **own** prior node on this lane — the join **marker** at lane start, else a prior message. A message always chains; it never roots a lane (the body-less marker does, carrying the device prefix, attributed to its owning identity). |
| `epoch`         | SAID      | The group-key epoch the body is encrypted under (the witnessed epoch window).                                                                                                                                                                      |
| `payloadDigest` | digest    | The encrypted message body — a content-addressed blob (integrity-bearing).                                                                                                                                                                         |
| `payloadSize`   | u64       | The body's byte length — advisory (allocation/pre-fetch bound), not integrity.                                                                                                                                                                     |
| `timestamp`     | timestamp | Orders messages within the epoch window (advisory; never establishes currency).                                                                                                                                                                    |
| `nonce`         | bytes     | High-entropy — makes `said` unguessable, so a **guessable** message body can't be confirmed against the public SAID (a known-plaintext oracle on the symmetric-encrypted chat content). Mandatory.                                                 |

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

### Policy — `vdti/policy/v1/{group}/*`

A policy is a SAD carrying one **expression** ([`../../policy/policy.md`](../../policy/policy.md)):

| Form                     | Kind     | Meaning                                                                                      |
| ------------------------ | -------- | -------------------------------------------------------------------------------------------- |
| `id(prefix)`             | leaf     | An identity.                                                                                 |
| `del(prefix, N)`         | leaf     | A live delegate of an identity, within `N` hops (`del(X)` = `del(X, 1)`).                    |
| `pol(said)`              | leaf     | Another policy, by its SAID (the reference graph is acyclic).                                |
| `thr(M, [expr, …])`      | composer | At least `M` of the listed sub-policies.                                                     |
| `wgt(M, [(expr, w), …])` | composer | Sub-policies carry weights; satisfied when the satisfied weights total `≥ M`.                |
| `and(expr, …)`           | composer | Every listed sub-policy (`≥ 2`); pools independent only when the author makes them disjoint. |

## Forthcoming shapes

The kinds whose role is fixed but whose exact field layout is owed, with where each lands:

| Kind / SAD                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Lands at                                                     |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Cryptographic grant values (`directory-ml-kem-*`, `groupkey-epoch-key`)                                                                                                                                                                                                                                                                                                                                                                                          | the encoding library (scheme-tagged key + ESSR-wrap layouts) |
| Shared-document grant values (`shared-document-governance`, `shared-document-read-governance`) + grant-doc + read grant-doc + rescind-doc                                                                                                                                                                                                                                                                                                                        | the shared-documents encode                                  |
| Chat-membership grant value (`chat-membership`) — the `{ grants, rescinds }` membership-delta grant-doc (a grant-chain entry anchors a writing device's body-less lane-root marker; a `rescinds` entry records each device lane's `bound` on the rescission `Trm`'s `bound` role) + the body-less join-marker shape (commits the **device prefix + group prefix + membership period / grant-instance** — structurally bound to one group, single-use per period) | the exchange encode                                          |
| Mail-payload inner shape (`vdti/exchange/v1/schemas/mail-payload`) — `{ topic, timestamp, body }`, the ESSR inner a mail message seals                                                                                                                                                                                                                                                                                                                           | the exchange encode                                          |
| Replica-set SAD (the `availability.replicas` target)                                                                                                                                                                                                                                                                                                                                                                                                             | the vdtid encode                                             |

## Cross-references

- [`kinds.md`](kinds.md) — the kind catalogue (the identifier for each SAD type).
- [`sad.md`](sad.md) — what a SAD is; the wrapper; the fetch-by-SAID rule.
- [`custody.md`](custody.md) / [`availability.md`](availability.md) — the two wrapper structs.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the authoritative per-kind
  chain-event shapes and the manifest role model.
