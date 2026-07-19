# vdti — area note: Exchange (published receive keys + delivery; consumes the ESSR primitive)

**Status: FIRST CUT — drafted with Jason 2026-07-12 (this session). Adapts the built `../kels` exchange +
mail design; not yet dual-pass reviewed.** A **feature** over the SAD + SEL primitives: parties exchange
**authenticated, confidential** point-to-point messages using **ESSR** (the 1:1 sealed authenticated
envelope, now a protocol primitive — [`vdti-area-essr.md`](vdti-area-essr.md)), delivered store-and-forward by a
**mail** transport, keyed by **published ML-KEM receive keys**. **No new primitive** — a receive key is a
**value-bearing lookup SEL** established `{Icp, Gnt}` (area-sel §1f + the generalized `Gnt` seal-a-typed-
value mechanism). **This is the kels exchange/mail design re-expressed on vdti primitives**, with one
deliberate vdti divergence (the encap key at **T2** not T1) and one stated verifier requirement
(**sender-key currency**, checked against the witnessed KEL — an optional message-anchor gives provable
liveness). **Lands at** `docs/design/features/exchange/exchange.md` (design-voice, forthcoming).

**Invariants:** [inv 14] witnessing prevents content forks, [inv 8] multi-source freshness (the sender's
key-lookup + the recipient's sender-KEL read), [inv 10] value-bearing lookup fails-closed on ambiguity,
[inv 16] addressing by prefix + data-entropy, [inv 17] chain validity is content-independent. Primitive
precedent: area-sel §1b (`Gnt` = a T2 sealed value-establishment), §1f (value-bearing lookup + `lineage`);
federation §1e (ML-KEM-1024 + AES-256-GCM; the lookup-prefix residual).

## Sources

- **`../kels` — the built design (adopted, not reinvented):** `docs/design/features/exchange.md` (ESSR +
  key publication + IPEX-style exchange messages), `docs/design/features/mail.md` (the store-and-forward
  transport), `lib/exchange/src/essr.rs` (the reference implementation). ESSR's origin + adaptation credit
  now lives in the primitive note's Attribution ([`vdti-area-essr.md`](vdti-area-essr.md)).
- This session's design conversation (the `{Icp, Gnt}` T2 key tier, the `data` = device-KEL-prefix / alias
  keying, the swap-vs-rescind split, the sender-key-currency requirement). Captured in
  `.working/vdti-receive-key-establishment-design.md`.
- The `shared-documents` note's exchange-layer forward ideas (per-doc content confidentiality) — a
  **consumer** of this feature (§7).

## The model in one paragraph

ESSR seals a message so that **only the recipient can read it** (ML-KEM-encapsulated to a published receive
key → AES-256-GCM) and **the sender is provably the author** (the sender ML-DSA-**signs**
the envelope SAID; the sender prefix rides **inside** the ciphertext; the recipient prefix rides **inside**
the signed plaintext). A **receive key** is a party's current public ML-KEM key, published as a
**value-bearing lookup SEL** at a **deterministic address** any sender computes from the party's IEL prefix
+ the receive-key directory topic + a `data` selector (the receive-key directory, §2). Exchange addresses by
**identity**: by default it **fans out** — one envelope sealed to **each** of the recipient's device receive
keys (enumerated from the recipient's IEL roster), so the message opens on **any** device; an optional
**`key_label`** targets a **single** key instead (resolved by the directory at `data = key_label`,
point-to-point). The published key is a **T2 sealed `Gnt`** (`vdti divergence`:
kels signs it with the ordinary key; vdti puts it behind `t_authorize`@T2 so a signing-key theft can't swap
it). Sealed envelopes are delivered by a **mail** service that stores opaque blobs and gossips only routing
metadata. On open, the recipient **verifies the signature against the sender's *current* witnessed key
state** (a verifier requirement the infra already supports, so rotation recovers messaging; an optional
message-anchor gives *provable* liveness). The feature is a **verification +
discovery + transport** layer; confidentiality/authenticity is ESSR, integrity of the key is the chain.
That is **mode 1** (ESSR, one-offs); a second **session mode** carries long-lived, ratcheting group chat
over the same spine (§1a / §7a).

## 1. ESSR — the sealed authenticated envelope (now a protocol primitive)

**ESSR moved to its own protocol primitive — [`vdti-area-essr.md`](vdti-area-essr.md) (2026-07-16).** The
1:1 sealed, authenticated envelope — a lattice KEM to the recipient's receive key → AES-256-GCM, the sender
prefix bound **inside** the ciphertext, the recipient prefix bound in the **signed** cleartext, a lattice
signature over the envelope SAID (Encrypt-Sender-Sign-Receiver; the four guarantees) — is no longer defined
here. See the primitive for the construction, the divergence ledger, and the capability boundary.

Exchange **consumes** it. ESSR is thin: it holds no key material, does no chain lookup, and seals an
**opaque** payload (a message timestamp or a topic multiplexer is application payload inside the ciphertext,
not an ESSR field; the `senderPin` is a SAID, not a serial). This feature adds what ESSR leaves out: the
**published receive keys** (§2) that resolve a recipient prefix to a receive key, the **sender-key
currency** check (§3), the mail delivery + serve-time gate, and the **session / group** mode (§1a / §7).

**Every message here is a kinded SAD** — the universal vdti rule (all data is a kinded, SAID-addressed SAD),
so an envelope, its inner, and every exchange message are SADs, anchorable by SAID (§3).

## 1a. Two modes — ESSR one-offs and a ratcheting session (Jason 2026-07-14)

Exchange **encapsulates two modes** over one shared spine — published receive keys (§2), sender-key
currency (§3), the crypto suite, and mail (§5). **One feature, two modes:**

- **ESSR — one-offs.** Per-message, stateless, sealed to the recipient's device receive keys — **fanned out**
  across them by default (so the message opens on any of the recipient's devices), or to a **single** key when a
  `key_label` is supplied (§2). The **async baseline**: mail, one-offs, and any time the recipient is offline.
  Always available; the construction is §1 (the fan-out is exchange calling ESSR once per key).
- **Session — chat.** A **long-lived** (assume years), **ratcheting**, **group-capable** session
  (§7a). Chosen for an ongoing conversation.

It is **not "secure vs weaker"** — it is **async baseline vs. the ongoing/online path.** ESSR needs
no live handshake (it seals to a static published key, so an offline recipient opens it later); the
session gains forward secrecy from ratcheting but only fits an ongoing chat. The client selects by
usage — one-off or offline → ESSR; an ongoing chat → the session.

**Layering (Jason): the durable _data_ is SAD / SEL / IEL; _transport_ is a separate layer; _UI_ is
later.** Members are IEL identities; group membership and key epochs are SELs; messages are SADs — the
whole data model is vdti primitives, no bespoke off-chain structure. **Transport** (mail §5 for async;
the live mesh channel — `docs/design/substrate/infrastructure/mesh-transport.md` — when peers are
online) moves that data but is not it. The `examples/chat` + `examples/mail` apps compose these modes;
the canon's job is to keep the primitives + substrate able to support them.

## 2. Receive-key resolution — the receive-key directory (shared-core)

An identity's device receive keys are published and resolved through the **receive-key directory**
([`vdti-area-receive-key-directory.md`](vdti-area-receive-key-directory.md)) — a value-bearing lookup SEL the
identity's IEL owns, `{Icp, Gnt}` at T2, keyed by `data` = a device KEL prefix or an opaque alias. It is
**shared-core** (ESSR, group-key, and shared-documents read it too), not exchange-internal. Exchange **consumes**
it: because it addresses by **identity**, a send **fans out** by default — it enumerates the recipient's device
keys (from its IEL roster) and ESSR-seals **once per key**, so the message opens on any device. An optional
**`key_label`** narrows a send to the **single** key at `data = key_label` (point-to-point; the opaque-alias
case). The T2 publication (a signing-key theft can't swap the
key — `vdti divergence` from kels' T1), the deterministic discoverable address, the opaque-alias correlation
discipline, the hardware-resident keys, and optional attestation are the directory's — see the note.

## 3. Sender-key currency — verify against the witnessed KEL; anchor for provable liveness

- **Default: verify against the sender's _current_ witnessed key state.** ESSR's `open` extracts the sender's
  key at `senderPin` (a SAID, §1); the recipient MUST also confirm that pinned key-state is the sender's
  **current** establishment state, read from the witnessed KEL/IEL (multi-source, inv 8) — **the infra
  already provides it.** A stale pin (a **captured-then-rotated** key signing under its old key-state) reads
  stale and is **refused**, so a rotation recovers messaging and the concern collapses back into the stated
  signing-key-compromise residual. A verifier **requirement** to state in the primitive (the kels doc leaves
  it to the client); no new mechanism — just read the chain.
- **Optional: anchor the message for _provable_ liveness (Jason 2026-07-12).** A message is already a
  **kinded SAD** (with a **nonce** for entropy — the universal rule), so proving the key was live at send
  time is just **anchoring its SAID on an IEL or SEL `Ixn`** — no wrapping step. The `Ixn` is authored by the
  **current** signing key at the current position, so a stale/captured key can't produce it, and **any**
  verifier (not just the recipient) reads the anchor on the sender's witnessed chain → provably current.
  Cost: a **chain event + metadata per anchored message**, so it is the opt-in for high-value /
  non-repudiable messages, not routine mail (which uses the lightweight check above).

## 4. Two attacks on a receive key — both T2 (`vdti divergence`; kels' T1 makes the swap cheap)

- **Swap → read your mail (worse).** Forge a `Gnt` (`t_authorize`@T2) → the live key is the attacker's →
  senders encapsulate to it → the attacker reads. A **confidentiality** break; **owner-detectable** (an
  unexpected `Gnt`, like a governance-quorum takeover); silent to senders until the owner reincepts + notifies.
  Recovery: reincept the key (fresh `lineage`) + notify. **(Under kels' T1 publication this needs only the
  signing key — the residual vdti's T2 removes.)**
- **Rescind → unreachable.** Forge a `Trm` (`t_authorize`/`t_govern`@T2) → the key reads dead → senders fail
  closed. An **availability** DoS — higher cost, lesser harm. Recovery: republish at a fresh `lineage`.
- **A _forced dispute_** (two competing accepted `Gnt`s/`Trm`s at one position) additionally needs the
  witness-collusion continuum on top of the T2 quorum — `threshold − k` colluders for `k` witnesses an
  attacker can partition onto the rival, floored at `2·threshold − signers` (area-sel §1c / federation §1e).

## 5. Mail — the store-and-forward transport (adopted from kels)

- **Payload-agnostic transport.** A mail node stores opaque **`SignedEssrEnvelope`** blobs (object store, at
  the **origin node** only) and gossips **routing metadata** (`{ sender, recipient, sourceNode, blobDigest,
  size, created, expires }`) to all nodes. Lifecycle: **send** (store blob(s) + gossip metadata — a **fan-out**
  send (§1a) stores **one blob per recipient device key**, each sealed to that key and all addressed to the
  recipient identity, so the recipient's device fetches the blob sealed to **its** key; a `key_label` send stores
  one) → **discover** (recipient queries any node's inbox) → **fetch** (from the origin node, authenticated —
  unauthenticated fetch would allow offline attacks on the ciphertext) → **open** (§1, with currency §3) →
  **ack** (origin deletes the blob, gossips removal). Rate limits: per-sender/day, per-recipient inbox cap,
  per-node storage cap, per-IP token bucket, message TTL, a short nonce-dedup window.
- **Residual — the communication graph is metadata-visible (stated, worth scoping).** Because routing
  metadata is gossiped network-wide, every node sees **who mails whom, when, and how large** — the
  **payload** is sealed but the **social graph + timing + size** are not. The message *type* is hidden (the
  `topic` is inside the ciphertext), but traffic analysis is open. This is the delivery-metadata residual; a
  vdti-specific tightening (scope inbox metadata to the recipient's node rather than gossiping it globally)
  is a **forward option**, at a discoverability cost. **(vdti has no single-node standalone mode — the kels
  standalone mail mode does not carry over; a floored federation is assumed.)**
- **Replay:** an envelope's SAID is stable, so a recipient **dedups by SAID** (the nonce-window guards only
  the transport short-term). State this in the primitive — the kels doc leans on the 60s window alone.

## 6. Privacy

- **The receive-key prefix is public (accepted).** A discoverable key rides a deterministic address, so its
  prefix reaches the witnesses carrying its receipts; a witness holding a **candidate** prefix can
  confirm-a-known-subject (never enumerate/invert). The inv-16 lookup-prefix residual — the point of a
  receive key is reachability.
- **Traffic is confidential, metadata is not** (§5). Delivery-metadata privacy (mixing, cover traffic,
  scoped metadata) is a forward direction.
- **`data`-alias correlation (§2).** An opaque alias hides *which device*; a descriptive one leaks it.

## 7. Consumers — credential exchange, and shared-documents content

- **IPEX credential exchange (now a protocol primitive — [`vdti-area-ipex.md`](vdti-area-ipex.md)).** Apply /
  Offer / Agree / Grant / Admit / Spurn messages (a thread chained by `previous`, topic
  `vdti/exchange/v1/topics/exchange`) negotiate issuance and presentation; they **MAY ride ESSR for a private
  disclosure** (IPEX carries cleartext-structured SADs — sealing is the consumer's choice, wired here). The
  vdti realization tracks the credential model (a credential = a direct-anchored SAD) — **detail deferred** to
  the exchange feature encode.
- **shared-documents off-node content.** A shared doc's private content (`shared-documents §5`) is delivered
  member-to-member as **ESSR payloads** (each recipient gets the content — or a wrapped per-doc symmetric key
  — sealed to their receive key). The `shared-documents §9` "KEM-wrapped group key / re-key on removal / key
  epochs" ideas **are the [group-key primitive](vdti-area-group-key.md)** — the group key rides a **key-epoch
  SEL**, ESSR-wrapped to per-period members, ratcheting on membership change + a time cadence; group chat and
  shared-doc content are its two consumers. (Resolves the former "open: whether the group key rides a SEL / the
  re-key cadence / the epoch commitment" — the primitive owns them now.)

## 7a. The session mode — the chat consumer of the group-key primitive (Jason 2026-07-14)

**Group keying is a protocol primitive — [`vdti-area-group-key.md`](vdti-area-group-key.md).** The epoch-key
distribution machinery — the bounded gated/blinded member roster, the key-epoch SEL, the
ESSR-wrap-once-per-member, and the membership + time-cadence ratchet — lives there, shared with
shared-documents content keying (which is why it is a primitive, not exchange-internal). This section is the
**chat consumer's** usage of it: the message model chat builds over the epoch key the primitive hands it.

The session mode (§1a) is **chat** — 1:1 and group, assumed to last **years**, so it **ratchets** for forward
secrecy. It is built **entirely from SAD / SEL / IEL**: members are IEL identities, the group's epochs and
roster are the primitive's SELs, and messages are SADs. Chat **composes** the group-key primitive for its
keying — the primitive supplies the current epoch key (unwrappable by each current member) plus the
per-writer-subkey nonce discipline — and adds the per-sender-lane message model below. A **1:1 chat is the
degenerate group of two.**

- **Messages = per-sender lanes; each a kinded, nonce'd SAD signed by its writer (Jason 2026-07-17).**
  Group messages form a **DAG of per-writer lanes** — each writing device's messages are its own
  `previous`-linked chain, merged into the group view, the way the shared-documents version DAG attributes
  each version to its writer ([`vdti-area-shared-documents.md`](vdti-area-shared-documents.md)). **The lane
  _is_ the writer:** a receiver reads which lane a message sits on, derives that lane's **per-writer subkey**
  (the primitive's nonce-safety discipline — `blake3::derive_key(epoch_key, device_kel_prefix)`, keyed on the
  device signing KEL prefix) to decrypt, and verifies the signature against that device's key — so **no sender
  field is carried on the message** (it would only duplicate the lane), and
  attribution is to the writer's **owning identity** (the IEL that rosters the writing device's KEL — a device is
  a KEL, never its own IEL). This is a **dedup, not
  sender-hiding**: the lane reveals the writer the way custody attributes a doc version — visible to members,
  and outside the ciphertext of necessity (you need it to pick the subkey). Confidentiality rides the
  per-sender subkey; **authenticity rides the writer's own signature over the message's fully-compacted
  SAID** ([inv 19]) — ML-DSA with the device's current `t_use` key, and **timestamped**. The epoch key
  proves only _"a group member"_; the signature proves _which_ member (ESSR's sender-unforgeability, restored
  for group mode). **Off-chain by default**, optionally **anchored** for non-repudiation.
- **Message currency binds to the witnessed epoch, not the self-asserted timestamp (Jason 2026-07-15,
  "A2 is a good finding").** A long-lived chat accumulates messages signed under a **sequence** of the
  sender's keys as it rotates, so the §3 one-off check ("refuse any key that is not current-**now**")
  does **not** apply — old messages must stay verifiable under **since-rotated** keys. But accepting "a
  key that was valid at some point" plus a **self-asserted** `timestamp` would let a
  **captured-then-rotated** key backdate a message (no anchor witnesses an off-chain message to a
  position). The sound binding is the **epoch window**: a message decrypts **only** under epoch _N_'s
  per-sender subkey, and epoch _N_ is a **witnessed** SEL event carrying a federation-clock window — so
  the check is _"the signing `t_use` key was the device's current establishment state **within epoch
  _N_'s witnessed window**."_ A rotated-away key is current only for the epochs it actually spanned, and
  injecting into epoch _N_ still needs epoch _N_'s subkey (a current member's secret) — bounded. The
  self-asserted timestamp only orders messages **within** the window; it never establishes currency.

**The ratchet is the primitive's.** Epochs advance on a membership change or a time cadence — that, with
the forward-secrecy and switchover discipline, is the group-key primitive's ([`vdti-area-group-key.md`](vdti-area-group-key.md));
chat only observes the current epoch. What chat adds over the primitive is the **volume** (the per-sender-lane
nonce discipline, above) and the **per-message sender signatures** — the two properties a high-traffic chat
needs that a shared-document does not.

**Open items (§7a — the chat consumer's):** how an **offline** member catches up across missed epochs; the
1:1 path; the message-anchoring policy (off-chain by default, optionally anchored). The roster storage, the
epoch-SEL length bound / checkpoint cadence, the `SESSION_RATCHET_INTERVAL` value, and the never-raw
epoch-key rule are the **primitive's** — see [`vdti-area-group-key.md`](vdti-area-group-key.md).

## 8. Reserved names + schemas (convention `vdti/<concept>/v1/<category>/<thing>`; concept **`exchange`**)

- **SEL topics:** the **receive-key** topic moved to the directory primitive —
  `vdti/directory/v1/topics/receive-key` (see
  [`vdti-area-receive-key-directory.md`](vdti-area-receive-key-directory.md)). The exchange **message** topic
  (inside the ciphertext) stays here: `vdti/exchange/v1/topics/exchange`.
- **KDF context (ESSR):** moved to the primitive — `vdti/essr/v1/protocols/kdf` (see
  [`vdti-area-essr.md`](vdti-area-essr.md)). The session-mode **per-writer-subkey** KDF context also lives with
  a primitive now — `vdti/groupkey/v1/protocols/kdf` (see [`vdti-area-group-key.md`](vdti-area-group-key.md)),
  since the epoch key and its subkey discipline are the group-key primitive's.
- **Grant-value kinds** — the convention is `vdti/sel/v1/grants/<owner>-<detail>` (the owner — a feature, or a
  stateful protocol primitive like group-key — first, ≤ 64 chars). Exchange defines none of its own: the
  **receive-key** grants moved to the directory primitive (`vdti/sel/v1/grants/directory-ml-kem-1024` /
  `directory-ml-kem-768`, the public ML-KEM key scheme-tagged — see
  [`vdti-area-receive-key-directory.md`](vdti-area-receive-key-directory.md)), and the group **epoch-key** grant
  is `groupkey-epoch-key` (below).
- **Exchange SADs** (`vdti/exchange/v1/schemas/*`): the exchange-message shapes (Apply/Offer/…); field
  layout at the encode, tracking `../kels lib/exchange`. (The ESSR envelope + inner moved to the primitive —
  `vdti/essr/v1/schemas/*`; see [`vdti-area-essr.md`](vdti-area-essr.md).)
- **Session / group names (§7a).** The chat **message SAD** `vdti/exchange/v1/schemas/message`
  (sender-signed + timestamped, epoch-window currency) is the chat consumer's — field layout at the encode.
  The epoch-key **distribution** names are the **group-key primitive's**
  ([`vdti-area-group-key.md`](vdti-area-group-key.md)): SEL topics `vdti/groupkey/v1/topics/roster` (the bounded
  member roster) and `vdti/groupkey/v1/topics/key-epoch` (the key-epoch log); the grant-value kind
  `vdti/sel/v1/grants/groupkey-epoch-key` (the ESSR-wrapped epoch key); the per-writer-subkey KDF context
  `vdti/groupkey/v1/protocols/kdf` (above); and the constant `SESSION_RATCHET_INTERVAL` (~6–12h, value TBD).

## 9. Adversarial pass (Jason 2026-07-12 — "try to break it")

ESSR itself holds: nonce reuse is unreachable (per-message keys), ciphertext/recipient swaps fail (the
signature binds the SAID), the receiver can't forge sender attribution (sender-in-ciphertext), and anti-KCI
holds (sender-auth is the sender's own signature). Every remaining concern is a **stated residual** or an
**integration requirement**: **(a)** signing-key compromise (bounded/recoverable — and vdti closes the
messaging-recovery gap via the §3 currency binding); **(b)** the encap-key swap (vdti's §2 T2 removes kels'
T1 exposure); **(c)** eclipse on the key-lookup / sender-KEL read (inv 8 multi-source, fail-secure); **(d)**
the §5 metadata / traffic-analysis residual; **(e)** inbox spam (a send-access-credential gate — forward).

## 10. Drift → land

- Write `docs/design/features/exchange/exchange.md` fresh from this note (greenfield voice).
- **Depends on the area-sel encode** of the generalized `Gnt` (seal a typed value under `grants/*`) + the
  `{Icp, Gnt}` value-bearing-lookup establishment — **not yet in canon** (captured in
  `.working/vdti-receive-key-establishment-design.md`). Leading edge; the primitive encode follows.
- **New invariant owed:** the 64-char kind cap + the `vdti/sel/v1/grants/*` naming convention; **and the §3
  sender-key-currency rule** (a verifier requirement, plus the optional message-anchor-for-liveness pattern).
- **The session mode (§1a / §7a) is the chat consumer of the group-key primitive.** The exchange encode owns
  the two modes, the **per-sender-lane message model** (per-writer subkeys, per-message sender signatures,
  epoch-window currency) and the chat **message SAD**; `examples/chat` + `examples/mail` compose it. The
  **epoch-key distribution** — the bounded gated/blinded roster, the key-epoch SELs, the ESSR-wrap, and the
  ratchet — is the **group-key primitive's** ([`vdti-area-group-key.md`](vdti-area-group-key.md)) and lands at
  the `protocols/group-key.md` encode, not here.
- **Open (flagged):** the chat consumer's session-mode items (§7a — offline catch-up, the 1:1 path,
  message-anchoring); scoped delivery metadata (§5); the IPEX exchange-message detail (§7); whether **mail** is
  a sibling feature note rather than a section here. (The roster storage, epoch-SEL length bound, and ratchet
  interval are the group-key primitive's — see [`vdti-area-group-key.md`](vdti-area-group-key.md).)
