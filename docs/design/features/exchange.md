# Exchange — sealed store-and-forward messaging

**Exchange** is how parties send each other **authenticated, confidential** messages — one-to-one
and in groups — delivered when the recipient is offline. It is the feature `mail` and `chat` are
each a UI over. It composes the sealed-send primitives directly and adds **no new chain machinery**:
an identity publishes the keys others seal to, a sender seals and deposits a message, and the
recipient fetches and opens it, trusting the data alone.

Exchange is a **verification + discovery + transport** layer. Confidentiality and authenticity are
the [sealed envelope](../primitives/protocols/essr.md)'s; the integrity of a published key is the
chain's. What exchange adds is the parts the envelope leaves out — resolving a recipient to its
keys, checking the sender's key was valid when it signed, delivering the bytes, and carrying a
long-lived group conversation.

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
- **[`custody.readers`](../primitives/data/sad/custody.md)** on the message SAD MAY additionally
  gate who fetches _it_ — defense in depth, since ESSR already seals the payload. The ciphertext
  **blob** is a bare content-addressed object with no `custody`, so its bytes are gated by the
  serve-time request instead (the payload endpoint, below).

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
by binding, and a recipient accepts the blob only when its recomputed digest matches. The message
also commits a `payloadSize`: the **digest alone is integrity-bearing** — a recomputed-digest
mismatch is the only tamper signal — while the **size is advisory**, a bound the recipient uses to
cap its allocation and refuse an over-large fetch before hashing, never treated as tamper-evidence.

The bytes are uploaded through the store's **payload endpoint**, authorized by the message itself —
**one round trip**, no store-issued challenge:

- The request carries the **message's SAID**, the blob, a client-chosen **nonce + timestamp**, and a
  signature over them. The store looks the message up, reads its committed payload digest, hashes
  the blob and requires a match, checks the timestamp is within a **tight freshness window (~10s)**
  and the nonce is unseen (a small, bounded replay cache), and verifies the signature **authorizes
  the requester to write for this message**: for an ESSR/mail message that is the **sender** named
  in the envelope, under its current key; for a sender-less **chat** message it is a **current group
  member** (the participant-blind membership check, the same `readers` machinery, resolved one
  requester at a time). Then it stores the blob, scoped to the message's `availability`.
- On upload the signature **authenticates the uploader** (rate-limiting who may write), and replay
  protection stays light because the write is **content-addressed and idempotent** — a replay
  re-stores identical bytes and changes nothing.
- **Fetch is the mirror**, and there the nonce + freshness window is **load-bearing** rather than
  belt-and-suspenders: the bytes are served only to a live-signed requester — an ESSR/mail blob to
  one that proves it controls the **recipient prefix**, a chat blob to a **current member** — and a
  captured signed fetch request, if replayable, would be a bearer token for the sealed bytes. A bare
  content-addressed blob carries no `custody` of its own, so this request gate — not `readers` — is
  what gates the bytes; the concrete endpoints are the store service's to specify.
- The message is deposited **first** (the store needs its body to read the digest), then the payload
  is uploaded against it. A recipient that sees the message before the blob lands reads "payload
  pending" and retries; a digest that is referenced but never uploaded expires by the payload's TTL.

## Sender-key currency

Opening a message authenticates its sender, and that check is only sound if the signing key is read
against the **window it was actually valid for** — not blindly, and not with a rigid "is it the tip
right now," which would strand honest mail sent before a routine rotation.

- **On open, place the message in the sender's witnessed rotation timeline.** The envelope names the
  sender's key-state position (`senderPin`), and the message carries a send-time `timestamp`. The
  recipient reads the sender's **witnessed** KEL and reads, for each rotation, the
  **federation-clock time of the federation position that rotation pins to** — a user rotation
  carries no clock of its own, but it binds to a federation position whose clock is a single,
  consensus, governance-authored value. Those form a **monotonic sequence of consensus timestamps**
  `t1 < t2 < t3 …`, and the message is accepted only if its `timestamp` falls in the interval its
  signing key-state was current for (`[t1, t2)` for the key established at the first rotation, and
  so on). A key that is still the tip has an **open** interval, so a live message just passes; an
  honest message sent before a later rotation still falls in the now-closed interval and is
  **accepted**, so a rotation no longer strands in-flight mail. The boundaries are **consensus**
  clock values — **not** a per-witness average of receipt times, so no single witness can move one —
  and the federation clock's **tolerance band** absorbs an honest sender's small skew right at a
  boundary. This is a chain read the infrastructure already provides — **data-only**, leaning on no
  node's word.
- **What it bounds, and what it doesn't.** A **captured-then-rotated** key — a stolen old key
  signing under its since-abandoned key-state — can still be backdated **within** the now-closed
  interval it was valid for, but it is **stuck there**: that interval lies in the past, and a
  message claiming a current time is rejected (the key was not current then), so it can never
  produce a message that reads as **current** — a rotation recovers messaging going forward. This is
  the ordinary signing-key-compromise limit — bounded, not prevented — the same residual the group
  epoch accepts. A self-asserted `timestamp` only places the message _within_ its past interval; the
  interval boundaries, which the federation clock fixes, are the trust anchor.
- **The send-time timestamp is a required mail-payload field, checked after decrypt.** ESSR carries
  **no cleartext timestamp** — a deliberate privacy call, keeping timing metadata off the envelope —
  so a mail message's send-time `timestamp` rides **inside the sealed payload**, and a conforming
  mail sender **must** include it. The window check is therefore **post-decrypt** (safe: the
  signature is verified first, and the recipient decrypts its own message), and a payload with
  **no** timestamp is **refused** — fail-secure, since accepting on the signature alone would
  silently void the currency check. (A chat message carries its `timestamp` as a SAD field.)
- **Optionally, anchor a message for an end-verifiable send-time.** For a high-value, non-repudiable
  message, the sender commits its SAID on an `Ixn` at its current position — which a stale key
  cannot forge, and which any verifier (not only the recipient) reads on the sender's witnessed
  chain, proving the message sat in a witnessed batch by a witness-asserted time, stronger than the
  window bound. It is a **per-message opt-in**; several messages sent at once share one `Ixn`, the
  way a batch of issuances does, so it need not cost a chain event apiece — which, like batch
  issuance, publishes on the sender's own chain that those messages were **co-sent in one batch** (a
  linkage a per-message anchor would not create, confined to the sender's own messages).

## Mail — the store-and-forward transport

A mail deposit stores the sealed message (and its payload blob) at the recipient's nodes and lets
the recipient find and fetch it:

- **Deposit** the message SAD + upload its payload (above), scoped to the recipient's inbox nodes →
  the recipient **discovers** it by polling its own nodes → **fetches** the blob through the
  **serve-time gate** — the store serves the bytes only to a requester that proves, with a live
  signature, that it controls the recipient prefix; the seal already protects confidentiality, so
  the gate limits store-side harvesting, it does not add integrity → **opens** it (with sender-key
  currency) → **acknowledges**, and the origin node deletes the bytes.
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
  nonce-safety discipline) to decrypt, and verifies the signature against that device's key.
  Mid-lane that is why **no sender field is carried** — it would only duplicate the lane. But a
  lane's **first** message has no `previous` to root it, so a message names its **writer iff
  `previous` is absent**: a lane-start message identifies the writing device, and every later
  message inherits it through `previous`. Confidentiality rides the subkey; **authenticity rides the
  writer's own signature over the message's fully-compacted SAID** — the system-wide rule that a
  signature is over the compacted SAID, so any faithful disclosure verifies against it — and the
  message is attributed to that device's **owning identity**, not merely the device. The epoch key
  proves only "a member"; the signature proves **which** member.
- **Currency: the signature is checked against the writer's own key-window; the epoch bounds when.**
  Chat's authenticity uses the **same key-window mail does** — the signature verifies against the
  writer's signing key-state, valid per the **writer's own witnessed KEL/IEL** interval, each
  boundary a **consensus federation-clock** value read via the federation position the rotation pins
  to (exactly as for mail — see [Sender-key currency](#sender-key-currency)). The **epoch is a
  separate axis** — the _encryption_ key — and it does two things, neither of them the auth check: a
  message decrypts only under epoch _N_'s subkey (so you must hold that epoch key to produce a
  readable message), and epoch _N_ is a witnessed SEL event whose **federation-clock window** (read
  the same way, via the position it pins to) **bounds when** the message was authored. The chat
  message carries **no key-state pin** and needs none, because the **witnessed epoch anchors the
  time**: the verifier resolves the writer's key-state among those valid **within epoch _N_'s
  window** and checks the signature, so the self-asserted `timestamp` only selects _within_ that
  witnessed bound, never outside it. So the check composes two witnessed sources: the **IEL** says
  whether the signing key was valid, the **epoch SEL** says the message was authored within epoch
  _N_'s window — authentic iff the key was valid (per its IEL interval) at a time inside that
  window. The **residual** is their intersection: a former member holding both a device's era-valid
  signing key and epoch _N_'s key can backdate a message within (that key's interval ∩ epoch _N_'s
  window) — confined, never forward. A self-asserted timestamp never establishes currency; the two
  witnessed windows do.
- **Catch-up is the union of your membership periods.** A member decrypts exactly the epochs during
  which it was a member — membership can be intermittent, and it reads **every period it was in**,
  none it was not. Catch-up after being offline is walking the key-epoch SEL from last-seen to
  current and unwrapping the epochs it was a member for; an epoch after a removal stays sealed to it
  (forward secrecy).
- **Store authorization is a per-requester membership grant.** A chat message is sender-less, so the
  store cannot gate its upload or fetch on "the sender" the way mail does. Instead the group
  maintains a **read/write-authorization grant** — the
  [`readers`](../primitives/data/sad/custody.md) mechanism — that the store checks
  **per-requester**: it resolves a live-signed request to an identity and confirms a **live grant**
  for it (a positive lookup, never materializing the set). This is a **different structure** from
  the group-key **wrap roster**: the wrap roster is materialized _by members_ (with the read gate)
  to key each epoch and is **blind to the store**, so the store cannot authorize against it —
  authorization rides the per-requester grant instead. A **member removal rescinds that grant** as
  it turns the epoch, so a removed member can no longer deposit or drain. A downloader enumerates
  nothing (the grant is participant-blind); the store, handed a self-identifying requester, only
  ever confirms that one — so a non-member can neither deposit a chat blob nor drain one, and
  learning that a requester who showed up holds a grant is the mechanism working, not a leak.
- **Delivery and retention are group-scoped.** A chat message's blob is one ciphertext readable by
  every member, scoped by `availability.replicas` to the **group's nodes** (the members' inbox
  hints, or a group-designated set) — the same recipient-scoping as mail, with the group as the
  "recipient." Unlike a mail deposit, which the recipient acks-and-deletes, a chat blob is
  **retained** across the catch-up window so a member offline for a while can still read the epochs
  it was in on return — bounded by the key-epoch log's checkpoint re-inception (the point past which
  a cold reader need not walk).
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
  to the whole federation, but those nodes still see who mails their user, when, and how large. The
  scoping is **sender-cooperative**: an honest sender sets `availability.replicas` to the
  recipient's inbox hints, but a sender bent on leaking could deposit elsewhere — so the bound
  tightens the recipient's own reads, it does not gag a determined sender. And the inbox-node hints
  are themselves **targeting metadata** — publishing "this identity's mail lives on these nodes"
  tells an observer where to look, the cost of resolving a recipient without a federation-wide
  gossip. Mixing and cover traffic are out of scope.
- **Signing-key compromise is bounded, and a rotation recovers messaging going forward.** A stolen
  key reaches only what its key-state authorizes, and the sender-key-currency window means a
  captured-then-rotated key can only produce messages that read as **stale** — backdated into the
  window that key was valid for, never as **current** — so a rotation recovers messaging forward. It
  does not un-forge messages a live stolen key could have sent inside its own window; that is the
  ordinary signing-key-compromise limit, the same residual the group epoch and the federation clock
  accept.
- **Inbox spam is bounded, not eliminated.** The rate limits (per-sender, per-inbox, per-node,
  per-IP, TTL, dedup) bound how much unwanted mail a recipient's nodes absorb, but an open inbox
  still accepts a deposit from anyone. Under an operator **lockdown**, the storage boundary MAY
  additionally gate deposits on a **credential or policy** write-gate (the `custody` write-gate), at
  the cost of open reachability.
- **The receive key's swap and rescind attacks are tier-2.** Both changing an identity's published
  receive key and rescinding it require a `t_authorize` act, not a signing key — the primitive's
  concern; see [the directory](../primitives/protocols/receive-key-directory.md).
- **Eclipse on a key lookup or a sender-KEL read** is defeated by the multi-source freshness bar
  (fail-secure): a consumer eclipsed to a malicious subset sees the truth after the heal.
