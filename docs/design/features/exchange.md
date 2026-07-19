# Exchange — sealed store-and-forward messaging

**Exchange** is how parties send each other **authenticated, confidential** messages — one-to-one
and in groups — delivered when the recipient is offline. It is the feature `mail` and `chat` are
each a UI over. It composes the sealed-send primitives directly and adds **no new chain machinery**:
an identity publishes the keys others seal to, a sender seals and deposits a message, and the
recipient fetches and opens it, trusting the data alone.

Exchange is a **verification + discovery + transport** layer. Confidentiality and authenticity are
the [sealed envelope](../primitives/protocols/essr.md)'s; the integrity of a published key is the
chain's. What exchange adds is the parts the envelope leaves out — resolving a recipient to its
keys, checking the sender's key is still current, delivering the bytes, and carrying a long-lived
group conversation.

## What exchange composes

Everything below it already exists as a primitive:

- **[ESSR](../primitives/protocols/essr.md)** — the one-to-one sealed, authenticated envelope.
  Exchange calls it; sealing to more than one device is exchange calling ESSR once per key.
- **[The receive-key directory](../primitives/protocols/receive-key-directory.md)** — where an
  identity publishes the per-device keys others seal to it, and where a sender looks them up.
- **[group-key](../primitives/protocols/group-key.md)** — the ratcheting epoch key the session
  (chat) mode builds a conversation over.
- **[IPEX](../primitives/protocols/ipex.md)** — the credential issuance/presentation exchange, one
  consumer of exchange's transport.
- **The SAD store and mail** — a message is a [SAD](../primitives/data/sad/sad.md); its bytes live
  and move under [`availability`](../primitives/data/sad/availability.md) and the store's delivery
  path.

## Two modes over one spine

Both modes share the published receive keys, the sender-key-currency check, the crypto suite, and
mail.

- **One-offs (the async baseline).** A single sealed message per send — stateless, needing no live
  handshake because it seals to a static published key an offline recipient opens later. This is the
  default: mail, one-shot deliveries, and any time the recipient is offline.
- **Session (chat).** A long-lived (assume years), **ratcheting**, group-capable conversation for an
  ongoing exchange. It gains forward secrecy from the group-key ratchet, and only fits an ongoing
  chat.

This is not "secure versus weaker" — it is **async baseline versus the ongoing path**. The client
picks by usage: a one-off or an offline recipient takes the async path; an ongoing conversation
takes the session.

## Addressing and delivery — scoped to the recipient's own nodes

Exchange addresses by **identity**, not by key. A recipient publishes, in its receive-key directory,
both its per-device receive keys and a set of **inbox-node hints** — the storage nodes it reads its
mail from. A sender resolves those and, by default, **fans out**: it seals the message once to
**each** of the recipient's device keys, so the message opens on any of the recipient's devices. An
opaque `key_label` narrows a send to a **single** key instead, for a point-to-point delivery.

Delivery is **scoped to the recipient**, built from `availability` with no new mechanism:

- The sender sets the message SAD's
  [`availability.replicas`](../primitives/data/sad/availability.md) to the recipient's inbox-node
  hints, so the sealed content lives **only** on those nodes. The recipient polls **its own** nodes;
  nothing about who-is-messaging-whom is gossiped federation-wide.
- **Multiple hints replicate to all of them** — the recipient lists several nodes for redundancy,
  and a send deposits to each.
- **[`custody.readers`](../primitives/data/sad/custody.md)** MAY additionally gate who can fetch the
  bytes — defense in depth, since ESSR already seals the payload against anyone but the recipient.

This is a deliberate choice over gossiping routing metadata to the whole federation: the
communication graph — who mails whom, when, how large — is exposed only to the recipient's chosen
home nodes, not to every node. (See [Residuals](#residuals).)

## The payload — named by digest, uploaded against the message

A message carries structured, signed fields (who, the key-state pin, the sealed envelope) as SAD
content, but its **bulk payload** — the ciphertext, and any file attachment — is not inlined. A
canonical SAD is JCS text, so inlining large bytes base64-encodes them; instead the message **names
the payload by digest** as a content-addressed blob (the general
[file payload](../primitives/data/sad/shapes.md#the-file-payload--vdtisadv1schemasfile) and the
[content-addressed blob](../primitives/data/sad/sad.md#bulk-opaque-bytes--the-content-addressed-blob)
rule). Because the message's SAID commits the digest, the sender's signature covers the exact bytes
by binding, and a recipient accepts the blob only when its recomputed digest matches.

The bytes are uploaded through the store's **payload endpoint**, authorized by the message itself:

- The request carries the **message's SAID**, the blob, and a **live signature** over a fresh,
  store-issued challenge. The store looks the message up, reads its committed payload digest, hashes
  the blob and requires a match, and verifies the live signature authenticates the requester as the
  message's **sender**, under that sender's **current** key. Then it stores the blob, scoped to the
  message's `availability`.
- The live signature does double duty: it **authenticates the uploader** (the message's own stored
  signature could be replayed by anyone who saw the message, so the store demands a fresh one), and,
  being under the sender's current key, it **composes with sender-key currency** below — a
  captured-then-rotated key cannot produce it.
- The message is deposited **first** (the store needs its body to read the digest), then the payload
  is uploaded against it. A recipient that sees the message before the blob lands reads "payload
  pending" and retries; a digest that is referenced but never uploaded expires by the payload's TTL.

## Sender-key currency

Opening a message authenticates its sender, and that check is only sound if the sender's key is read
**as it stands now**, not as it once stood.

- **On open, confirm the sender's key is current.** The envelope names the sender's key-state
  position (`senderPin`); the recipient MUST additionally confirm that position is the sender's
  **current** establishment state, read against the **witnessed** KEL (multi-source, so no single
  stale source can hide a rotation). A **captured-then-rotated** key — a stolen old key signing
  under its abandoned key-state — reads stale and is **refused**. So a rotation recovers messaging,
  and the residual collapses back to the ordinary signing-key-compromise limit. This is a verifier
  **requirement** a conforming open performs — not new machinery, just a chain read the
  infrastructure already provides.
- **Optionally, anchor a message for provable liveness.** A message is a kinded SAD, so proving its
  key was live at send time is just anchoring its SAID on the sender's chain (an `Ixn` the current
  signing key authors at the current position, which a stale key cannot). Any verifier — not only
  the recipient — then reads the anchor on the sender's witnessed chain. This costs a chain event
  per message, so it is a **per-message opt-in** the app or user sets for a high-value,
  non-repudiable message; routine mail signs without anchoring.

## Mail — the store-and-forward transport

A mail deposit stores the sealed message (and its payload blob) at the recipient's nodes and lets
the recipient find and fetch it:

- **Deposit** the message SAD + upload its payload (above), scoped to the recipient's inbox nodes →
  the recipient **discovers** it by polling its own nodes → **fetches** the blob (authenticated — an
  unauthenticated fetch would let an attacker work offline on the ciphertext) → **opens** it (with
  sender-key currency) → **acknowledges**, and the origin node deletes the bytes.
- **Rate limits** bound abuse: per-sender-per-day, a per-recipient inbox cap, a per-node storage
  cap, a per-IP token bucket, a message TTL, and a short dedup window.
- **Replay** is closed by the stable SAID: a recipient dedups by the message's SAID (the short dedup
  window guards only the transport layer).

## The session mode — chat

Chat composes the [group-key](../primitives/protocols/group-key.md) primitive for its keying and
adds a message model over it. It is built entirely from SAD / SEL / IEL: members are IEL identities,
the group's epochs and roster are group-key's SELs, and messages are SADs. A **1:1 chat is the
degenerate group of two** — the same machinery, no separate two-party construction.

- **Messages are per-sender lanes.** Group messages form a DAG of per-writer lanes — each writing
  device's messages are its own `previous`-linked chain, merged into the group view, the way a
  shared document attributes each version to its writer. **The lane is the writer:** a receiver
  reads which lane a message sits on, derives that lane's per-writer subkey (group-key's
  nonce-safety discipline) to decrypt, and verifies the signature against that device's key — so
  **no sender field is carried**, it would only duplicate the lane. Confidentiality rides the
  subkey; **authenticity rides the writer's own signature over the message's fully-compacted SAID**
  — the system-wide rule that a signature is over the compacted SAID, so any faithful disclosure
  verifies against it. The epoch key proves only "a member"; the signature proves **which** member.
- **Currency binds to the witnessed epoch.** A long-lived chat accumulates messages under a sequence
  of the sender's rotating keys, so the one-off "must be current now" check does not apply — old
  messages stay verifiable under since-rotated keys. But "a key that was valid at some point" plus a
  self-asserted timestamp would let a captured-then-rotated key backdate a message. The sound
  binding is the **epoch window**: a message decrypts only under epoch _N_'s subkey, and epoch _N_
  is a witnessed SEL event carrying a federation-clock window, so the check is "the signing key was
  the device's current state **within epoch _N_'s window**." A self-asserted timestamp only orders
  messages within the window.
- **Catch-up is the union of your membership periods.** A member decrypts exactly the epochs during
  which it was a member — membership can be intermittent, and it reads **every period it was in**,
  none it was not. Catch-up after being offline is walking the key-epoch SEL from last-seen to
  current and unwrapping the epochs it was a member for; an epoch after a removal stays sealed to it
  (forward secrecy).
- **Anchoring is opt-in.** A message is signed for authenticity by default and anchored only when
  the app or user flags it for non-repudiation (as above).

The ratchet itself — epochs advancing on a membership change or a time cadence, the forward-secrecy
and switchover discipline, the bounded gated/blinded roster — is the group-key primitive's; chat
only observes the current epoch and adds the per-lane volume and the per-message signatures.

## Consumers

- **[IPEX](../primitives/protocols/ipex.md) credential exchange.** The apply / offer / agree / grant
  / admit / spurn thread (topic `vdti/exchange/v1/topics/exchange`) negotiates issuance and
  presentation. IPEX carries cleartext-structured SADs; a disclosure that must be private **rides
  ESSR**, sealed at the edge — exchange wires that in, but the message set and the acceptance gate
  are IPEX's.
- **[Shared-documents](shared-documents.md) off-node content.** A private document's content is
  delivered member-to-member as ESSR payloads — each recipient gets the content, or a
  group-key-wrapped symmetric key, sealed to its receive key.

## Reserved names

Concept `exchange`, on the `vdti/{component}/v1/{category}/{name}` convention
([`../primitives/data/sad/kinds.md`](../primitives/data/sad/kinds.md)):

- **Message topic** (inside the ciphertext): `vdti/exchange/v1/topics/exchange`.
- **Chat message SAD**: `vdti/exchange/v1/schemas/message` — sender-signed, timestamped,
  epoch-window currency. This is the one message shape exchange owns: the issuance/presentation
  messages (`apply` / `offer` / …) are IPEX's, and the one-off async message is the ESSR message.

The receive-key grants and directory topic, the ESSR envelope and its KDF context, and the group-key
epoch/roster/KDF names belong to those primitives; exchange defines none of them.

## Residuals

- **The communication graph is visible to the recipient's home nodes.** Recipient-scoped delivery
  limits the exposure to the storage nodes a recipient chose — far tighter than gossiping the graph
  to the whole federation, but those nodes still see who mails their user, when, and how large.
  Mixing and cover traffic are out of scope.
- **Signing-key compromise is bounded and recoverable.** A stolen key reaches only what the current
  key state authorizes, and the sender-key-currency binding means a rotation recovers messaging — a
  captured-then-rotated key is refused.
- **The receive key's swap and rescind attacks are tier-2.** Both changing an identity's published
  receive key and rescinding it require a `t_authorize` act, not a signing key — the primitive's
  concern; see [the directory](../primitives/protocols/receive-key-directory.md).
- **Eclipse on a key lookup or a sender-KEL read** is defeated by the multi-source freshness bar
  (fail-secure): a consumer eclipsed to a malicious subset sees the truth after the heal.
