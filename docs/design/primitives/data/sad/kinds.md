# SAD Kinds — the identifier catalogue

Every SAD carries a **`kind`** — a versioned string naming its type, which drives structural
validation, tier dispatch, the role vocabulary it may carry, and whether the store will serve it by
SAID; a kind's schema also names **which of its fields are nested sub-SADs** (the `SAD`-typed
positions in [`shapes.md`](shapes.md)) — the data the signing discipline reads to tell a compacted
sub-SAD from a scalar reference ([`said.md`](said.md)). This doc is the canonical enumeration of
every SAD kind. Sibling identifier families share the same naming scheme and live in their own
catalogues: **derivation tags and SEL topics**
([`../event-logs/tags-and-topics.md`](../event-logs/tags-and-topics.md)) and **gossip topics**
([`../../../substrate/federation/topics.md`](../../../substrate/federation/topics.md)).

## The naming convention

Every identifier is **`vdti/{component}/v1/{category}/{name}`** — four segments, always:

- **`component`** — the subsystem that owns it: `kel` / `iel` / `sel` / `sad` / `event` / `witness`
  / `log` / `doc` / `exchange` / `essr` / `ipex` / `groupkey` / `directory` / `cred` / `policy` /
  `gossip`.
- **`v1`** — the schema version.
- **`category`** — the family within the component: `events` / `grants` / `receipts` / `roles` /
  `schemas` / `claims` / `protocols` / `actions` / `states` / `topics`. This is the common set; a
  component may name its own family where these do not fit — policy groups by domain
  (`vdti/policy/v1/{group}/*`), and the gossip catalogue channels by log (plus a `witness` channel
  for receipts).
- **`name`** — the specific member.

A `*` below marks a family whose members are listed inline or defined by a feature. There is
**never** a fifth segment: grouping is carried by descriptive names, not extra path depth.

## SAD kinds — the `kind` field

Every SAD carries one of these. **The chain events:**

| Log | Kind                | Members                                               |
| --- | ------------------- | ----------------------------------------------------- |
| KEL | `…/kel/v1/events/*` | `fcp` `icp` `ixn` `rot` `wit` `trm`                   |
| IEL | `…/iel/v1/events/*` | `icp` `ixn` `evl` `ath` `rev` `dth` `trm` `wit` `fcp` |
| SEL | `…/sel/v1/events/*` | `icp` `ixn` `pin` `gnt` `trm` `sea`                   |

**The commitment SADs events reference:**

| Kind                            | What it is                                                                                                                                                                                                       |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vdti/event/v1/roles/manifest`  | the role-grouped commitment SAD an event names                                                                                                                                                                   |
| `vdti/event/v1/roles/roster`    | a roster / threshold delta                                                                                                                                                                                       |
| `vdti/event/v1/roles/witnesses` | a witness-config `{ threshold, signers }`                                                                                                                                                                        |
| `vdti/event/v1/roles/pins`      | each participating member's prior KEL tip (`participation.previous`; an IEL's down-pins)                                                                                                                         |
| `vdti/sel/v1/grants/*`          | a grant-value a SEL `Gnt` seals: `directory-ml-kem-1024`, `directory-ml-kem-768`, `document-edit-membership`, `document-comment-membership`, `document-read-membership`, `groupkey-epoch-key`, `chat-membership` |
| `vdti/witness/v1/receipts/*`    | a witness receipt, by witnessed chain: `kel` / `iel` / `sel`                                                                                                                                                     |

The remaining manifest roles — `anchors`, `delegates`, `payload`, `kills`, and the scalar `clock` —
are carried **inline** in the manifest SAD, so they are not separate SADs and have no kind of their
own.

**The SAD-layer content SADs:**

| Kind                       | What it is                                                                                                                                                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vdti/sad/v1/schemas/file` | a **file payload** — a general content wrapper that names a content-addressed binary blob by `{ digest, size }` ([`shapes.md`](shapes.md)); the blob itself is opaque bytes (no `kind`), fetched by digest |

**The protocol-primitive SADs:**

| Kind                     | What it is                                                          |
| ------------------------ | ------------------------------------------------------------------- |
| `vdti/essr/v1/schemas/*` | the ESSR envelope, inner, and message                               |
| `vdti/ipex/v1/schemas/*` | the IPEX messages (`apply` `offer` `agree` `grant` `admit` `spurn`) |

The ESSR key-derivation context `vdti/essr/v1/protocols/kdf` shares the naming convention but is
**not a SAD** — it is a domain-separation label used when deriving the sealing key, never stored or
served ([`../../protocols/essr.md`](../../protocols/essr.md)). The group-key primitive's
per-writer-subkey context `vdti/groupkey/v1/protocols/kdf` is the same kind of non-SAD label
([`../../protocols/group-key.md`](../../protocols/group-key.md)). The mesh transport's
per-connection key-derivation context `vdti/gossip/v1/protocols/kdf` is the same kind of non-SAD
label
([`../../../substrate/infrastructure/mesh-transport.md`](../../../substrate/infrastructure/mesh-transport.md)).

**The feature / application SADs:**

| Kind                         | What it is                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `vdti/doc/v1/schemas/*`      | shared-document SADs (`inception` / `version` / `comment` / `comment-resolution` / …) |
| `vdti/exchange/v1/schemas/*` | exchange SADs                                                                         |
| `vdti/cred/v1/schemas/*`     | credential SADs — the `kind` names the type (app-registered)                          |
| `vdti/cred/v1/claims/*`      | credential claim SADs (app-defined, blinded per predicate)                            |
| `vdti/policy/v1/{group}/*`   | policy documents, grouped by domain                                                   |

One further standalone kind is owed by a forthcoming encode: the **replica-set SAD** an
`availability.replicas` field names ([`availability.md`](availability.md)) — its `kind` and layout
land at the vdtid encode, alongside the storage service.

## Fetch by SAID — what the store hands back

`kind` also decides whether the store will hand back a SAD **by its SAID**. Two ways of reaching
data sit side by side: a **chain event is found by prefix** — you reach it only by walking the chain
whose prefix you already hold — while a **standalone SAD is found by SAID**, fetched directly. The
store keeps the two apart with a list of the kinds it will serve, and **turns away everything
else**:

- **Served by SAID** — the commitment SADs an event names (`vdti/event/v1/roles/*`), the grant
  values a `Gnt` seals (`vdti/sel/v1/grants/*`), the **framework SADs a verifier resolves to
  evaluate** — a **policy** expression (`vdti/policy/v1/*`), an authorizing **`issuers`** list, a
  credential's **`terms`** — and content SADs (a public credential body, the **file wrapper**
  `vdti/sad/v1/schemas/file`, or an application content kind the app has registered), each gated by
  its own custody `readers`. A verifier walking a chain has to resolve the role SADs an event
  commits to, so these have to be reachable by SAID. **Kind is only the first gate.** A served SAD
  that carries a custody `readers` gate ([`custody.md`](custody.md)) is handed back only to a
  requester that gate admits, and one delivered member-to-member rather than published (its
  `availability`) is never in the store to serve at all. So a _public_ grant value — a directory
  receive key — is served to anyone. A _member-private_ one is not: a `groupkey-epoch-key` wrap is
  **member-delivered** (**never published for fetch-by-SAID** — it names its recipient in the clear;
  it moves over recipient-scoped mail, not the public object store), and a read-gated
  shared-document grant is served only to a reader its `readers` gate admits. Serving the grant
  family by SAID therefore never enumerates who a private grant was sealed to. A **content-addressed
  blob** — the bulk bytes a `file` wrapper or an ESSR envelope names by **digest** — is **not**
  served by this rule at all: it is a bare object fetched **by digest** through its `availability` /
  serve-time request path, never by SAID.
- **Never served by SAID** — the chain events themselves (`vdti/{kel,iel,sel}/v1/events/*`). An
  event lives in the chain log and is reached by prefix; asking the store for an event body by SAID
  gets back the same "not present" answer a SAID that never existed would.
- **Everything else — refused.** A kind not on the served list is not handed back, so a later event
  kind, or some future free-standing SAD type, is turned away by default instead of quietly opening
  a way to fetch it.

The whole rule in one line: **the store hands back a SAD by SAID only when learning that SAID
already meant holding the chain, or when the SAD is public by design and its custody `readers` gate
admits the requester.** An event's SAID fails that test — it travels in the open as a commitment
inside a public identity's `anchors[]`, so if the store answered for event bodies by SAID, an
observer could gather those commitments and walk them back to the private positions they stand for,
turning the store into the very lookup that reaching events by prefix alone was meant to deny. A
commitment SAD's SAID passes the test — it appears only inside an event's `manifest`, which you
reach only after reading an event you already hold the chain for, so serving it tells an observer
nothing they could not already work out. [`event-shape.md`](../event-logs/event-shape.md) states the
"there is no SAID-to-event index" property that this makes real.

This is why every SAD carries a `kind` ([`sad.md`](sad.md)): the sort has no fallback — a SAD with
no kind cannot be placed on either side of it, so it is refused. The store's write path turns away a
kind it will not serve; that enforcement lives with the store
([`../../../substrate/infrastructure/vdtid.md`](../../../substrate/infrastructure/vdtid.md),
forthcoming), on the retrieval boundary [`availability.md`](availability.md) describes.

## Cross-references

- [`shapes.md`](shapes.md) — the field shape of each SAD kind (the companion to this catalogue).
- [`sad.md`](sad.md) — the SAD layer: what a SAD is, the `kind`-required rule.
- [`custody.md`](custody.md) — the per-object `readers` read gate that composes with the
  served-by-SAID list above.
- [`said.md`](said.md) — the two-pass digest that turns a SAD's canonical content into a SAID.
- [`../event-logs/tags-and-topics.md`](../event-logs/tags-and-topics.md) — the derivation tags and
  SEL topics that share this convention.
- [`../../../substrate/federation/topics.md`](../../../substrate/federation/topics.md) — the gossip
  topics (mesh channels) that share this convention.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the event taxonomy and the
  manifest role model these kinds instantiate.
