# SAD shapes — the field catalogue

Every piece of content in VDTI is a [SAD](sad.md), and its [`kind`](kinds.md) names its type. This
doc is the companion to those two: [`kinds.md`](kinds.md) enumerates the kinds, and this doc gives
each kind's **shape** — the fields it carries. It covers the **standalone SADs** in full (receipts,
configs, grant values, credentials, shared-document SADs, the ESSR and IPEX protocol messages,
policy). For the **chain events**, the authoritative per-kind field tables live in
[`../event-logs/event-shape.md`](../event-logs/event-shape.md); this doc summarizes their common
envelope and points there rather than restating them.

A field marked **forthcoming** has its role fixed but its exact field layout deferred to the feature
or primitive encode named in its source; the [Forthcoming shapes](#forthcoming-shapes) table
collects them.

Types read as: **SAID** / **prefix** — a 256-bit digest (a SAID addresses content, a prefix names a
chain); **string**; **u64** — an unsigned integer; **bool**; **bytes**; **timestamp** — an RFC 3339
time; **list⟨T⟩**.

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

- **`custody { owner, topic, readers }`** — `owner` is the writer's IEL prefix, `topic` the SEL
  namespace that locates the write's anchor (both-or-neither), `readers` the prefix of a
  read-authorization SEL that gates reads (`None` → public).
- **`availability { replicas, ttl, once }`** — `replicas` the SAID of a replica-set SAD (absent →
  everywhere), `ttl` a retention bound, `once` a destructive-read flag.

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

The remaining roles — `anchors`, `delegates`, `payload`, `kills`, `bound`, `grant`, and the scalar
`clock` — are carried **inline** in the manifest SAD, so they have no SAD of their own
([`kinds.md`](kinds.md)); their value shapes are
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

| Kind                                                 | Carries                                                                                         | Status      |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------- |
| `vdti/sel/v1/grants/directory-ml-kem-1024`           | A published ML-KEM-1024 receive key (scheme-tagged public key + optional hardware attestation). | forthcoming |
| `vdti/sel/v1/grants/directory-ml-kem-768`            | The reduced-tier ML-KEM-768 receive key.                                                        | forthcoming |
| `vdti/sel/v1/grants/groupkey-epoch-key`              | A group epoch key, ESSR-wrapped once per member device.                                         | forthcoming |
| `vdti/sel/v1/grants/shared-document-governance`      | The grant-doc — `editors` / `commenters` role-lists.                                            | forthcoming |
| `vdti/sel/v1/grants/shared-document-read-governance` | The read grant-doc — the `readers` role-list only.                                              | forthcoming |

Each grant value is a SAD (`said` + `kind` + its value); the value layouts land at the exchange and
shared-documents encodes.

## Protocol SADs

### ESSR — `vdti/essr/v1/*`

The **envelope** (`vdti/essr/v1/schemas/envelope`) — the signed cleartext; its signature rides
adjacent ([`../../protocols/essr.md`](../../protocols/essr.md)):

| Field              | Type   | Meaning                                                                    |
| ------------------ | ------ | -------------------------------------------------------------------------- |
| `said`             | SAID   | The envelope SAID — commits every field below; the signature is over it.   |
| `kind`             | string | `vdti/essr/v1/schemas/envelope`.                                           |
| `sender`           | prefix | The sender's IEL prefix (cleartext — routes and fetches the verify key).   |
| `senderPin`        | SAID   | The sender's establishment event current at signing — the verifying state. |
| `recipient`        | prefix | The recipient's IEL prefix (signed — the recipient binding).               |
| `kemCiphertext`    | bytes  | The key-encapsulation to the recipient's receive key.                      |
| `encryptedPayload` | bytes  | The sealed inner, under the key derived from the encapsulated secret.      |
| `nonce`            | bytes  | The sealing nonce (fresh random per message).                              |

The **inner** (`vdti/essr/v1/schemas/inner`, sealed) is `{ said, kind, sender, payload }` — the
sender prefix (the binding that rides inside the sealed content) and the opaque payload; a message
timestamp or protocol label rides _inside_ `payload`, not as an envelope field. The **message**
(`vdti/essr/v1/schemas/message`) is `{ said, kind, envelope, signature }` — the envelope SAD plus
the sender's signature over `envelope.said`.

### IPEX — `vdti/ipex/v1/*`

Six message kinds `vdti/ipex/v1/schemas/{apply,offer,agree,grant,admit,spurn}`, each a signed SAD
threaded by `previous` ([`../../protocols/ipex.md`](../../protocols/ipex.md)). Only the **`grant`**
— the disclosure and its presentation-freshness envelope — carries content and a distinct shape:

| Field       | Type      | Required | Meaning                                                                                                    |
| ----------- | --------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| `said`      | SAID      | yes      | Commits every field below; the signature is over it.                                                       |
| `kind`      | string    | yes      | `vdti/ipex/v1/schemas/grant`.                                                                              |
| `previous`  | SAID      | no       | The `agree` this grant answers (absent for a minimal push).                                                |
| `discloser` | prefix    | yes      | The discloser's IEL prefix — equals the SAD's committed issuee if targeted.                                |
| `audience`  | prefix    | yes      | The verifier's IEL prefix — binds the disclosure to one recipient.                                         |
| `nonce`     | bytes     | yes      | Per-presentation, high-entropy — the replay-dedup entropy.                                                 |
| `created`   | timestamp | yes      | Bounds cache retention; never a trust input.                                                               |
| `challenge` | bytes     | no       | Echoes the verifier's `apply` challenge (stronger-liveness mode).                                          |
| `disclosed` | SAID      | yes      | The disclosed SAD by SAID — expanded inline at full disclosure, or the committed SAID at a graduated step. |

The other five messages (`apply` / `offer` / `agree` / `admit` / `spurn`) are lightweight
negotiation and acknowledgement SADs, each `{ said, kind, previous?, … }` signed by its sender;
their shapes land with [`../../protocols/ipex.md`](../../protocols/ipex.md).

## Feature SADs

### Credentials — `vdti/cred/v1/schemas/*`

A credential is a **direct-anchored** SAD (its issuance is a commitment hash on the issuer's IEL
`Ixn` — [`../../../features/credentials/`](../../../features/credentials/)), not a chain event. Its
`kind` names its **type** (application-registered — a diploma, an accreditation); the wrapper below
is common to every type.

| Field     | Type      | Required | Meaning                                                            |
| --------- | --------- | -------- | ------------------------------------------------------------------ |
| `said`    | SAID      | yes      | The credential's SAID — its immutable anchor.                      |
| `kind`    | string    | yes      | `vdti/cred/v1/schemas/*` — the credential's registered type.       |
| `issuer`  | prefix    | yes      | The issuer's IEL prefix.                                           |
| `issuee`  | prefix    | no       | The issuee's IEL prefix; **absent → a bearer credential**.         |
| `claims`  | SAID      | yes      | A claims SAD (nested → partial disclosure).                        |
| `terms`   | SAID      | no       | An issuer-set terms-of-use SAD; travels with the credential.       |
| `issued`  | timestamp | yes      | Issuance time (advisory).                                          |
| `expires` | timestamp | no       | Expiry (advisory).                                                 |
| `nonce`   | bytes     | yes      | High-entropy — every credential has one; makes `said` unguessable. |

The `claims` field is the SAID of a **claims SAD** (`vdti/cred/v1/claims/*`, application-defined).
Each gated predicate it carries is a **uniformly-shaped blinded claim** — `{ said, nonce, data }`:
the per-claim `said` is what the credential commits, a high-entropy `nonce` blinds it so a compacted
claim leaks neither presence nor value, and `data` is the application-shaped value (a boolean
bracket like `ageOver18`, a field). Disclosing a claim reveals its `{ nonce, data }` and recomputes
the `said` against the commitment ([claim-gating](../../../features/credentials/#claim-gating)).

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
| `custody`   | struct     | `{ owner: the editor's IEL, topic, readers }`.     |
| `ancestors` | list⟨SAID⟩ | Parent version SAID(s) — the multi-parent DAG.     |
| `nonce`     | bytes      | High-entropy — makes the version SAID unguessable. |

The **grant-doc** (`shared-document-governance`, editors/commenters role-lists), the **read
grant-doc** (`shared-document-read-governance`, the `readers` role-list only), and the **gated
rescind-doc** (a `bound` position sealing a membership period) are **forthcoming** — shapes at the
shared-documents encode
([`../../../features/shared-documents/documents.md`](../../../features/shared-documents/documents.md)).

### Exchange — `vdti/exchange/v1/*`

The exchange-message and session-message shapes (`vdti/exchange/v1/schemas/*`) are **forthcoming** —
at the exchange encode. The sealed one-to-one envelope is its own protocol primitive — see
[Protocol SADs](#protocol-sads).

### Policy — `vdti/policy/v1/{group}/*`

A policy is a SAD carrying one **expression** ([`../../policy/policy.md`](../../policy/policy.md)):

| Form                     | Kind     | Meaning                                                                       |
| ------------------------ | -------- | ----------------------------------------------------------------------------- |
| `id(prefix)`             | leaf     | An identity.                                                                  |
| `del(prefix, N)`         | leaf     | A live delegate of an identity, within `N` hops (`del(X)` = `del(X, 1)`).     |
| `pol(said)`              | leaf     | Another policy, by its SAID (the reference graph is acyclic).                 |
| `thr(M, [expr, …])`      | composer | At least `M` of the listed sub-policies.                                      |
| `wgt(M, [(expr, w), …])` | composer | Sub-policies carry weights; satisfied when the satisfied weights total `≥ M`. |
| `and(expr, …)`           | composer | Every listed sub-policy, each over an independent pool (`≥ 2` sub-policies).  |

## Forthcoming shapes

The kinds whose role is fixed but whose exact field layout is owed, with where each lands:

| Kind / SAD                                                                                                                 | Lands at                                             |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Grant values (`directory-ml-kem-*`, `shared-document-governance`, `shared-document-read-governance`, `groupkey-epoch-key`) | the directory / shared-documents / group-key encodes |
| Shared-document grant-doc + read grant-doc + rescind-doc                                                                   | the shared-documents encode                          |
| Exchange + session message shapes                                                                                          | the exchange encode                                  |

## Cross-references

- [`kinds.md`](kinds.md) — the kind catalogue (the identifier for each SAD type).
- [`sad.md`](sad.md) — what a SAD is; the wrapper; the fetch-by-SAID rule.
- [`custody.md`](custody.md) / [`availability.md`](availability.md) — the two wrapper structs.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the authoritative per-kind
  chain-event shapes and the manifest role model.
