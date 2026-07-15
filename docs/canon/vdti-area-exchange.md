# vdti — area note: Exchange (ESSR authenticated encryption + published receive keys)

**Status: FIRST CUT — drafted with Jason 2026-07-12 (this session). Adapts the built `../kels` exchange +
mail design; not yet dual-pass reviewed.** A **feature** over the SAD + SEL primitives: parties exchange
**authenticated, confidential** point-to-point messages using **ESSR** (Encrypt-Sender-Sign-Receiver, the
KERI-lineage construction — sound, adversarially checked below), delivered store-and-forward by a
**mail** transport, keyed by **published ML-KEM receive keys**. **No new primitive** — a receive key is a
**value-bearing lookup SEL** established `{Icp, Gnt}` (area-sel §1f + the generalized `Gnt` seal-a-typed-
value mechanism). **This is the kels exchange/mail design re-expressed on vdti primitives**, with one
deliberate vdti divergence (the encap key at **T2** not T1) and one stated verifier requirement
(**sender-key currency**, checked against the witnessed KEL — an optional message-anchor gives provable
liveness). **Lands at** `docs/design/features/exchange/exchange.md` (design-voice, forthcoming).

**Invariants:** [inv 4] witnessed-in-full uniqueness, [inv 8] multi-source freshness (the sender's
key-lookup + the recipient's sender-KEL read), [inv 10] value-bearing lookup fails-closed on ambiguity,
[inv 16] addressing by prefix + data-entropy, [inv 17] chain validity is content-independent. Primitive
precedent: area-sel §1b (`Gnt` = a T2 sealed value-establishment), §1f (value-bearing lookup + `lineage`);
federation §1e (ML-KEM-1024 + AES-256-GCM; the lookup-prefix residual).

## Sources

- **`../kels` — the built design (adopted, not reinvented):** `docs/design/features/exchange.md` (ESSR +
  key publication + IPEX-style exchange messages), `docs/design/features/mail.md` (the store-and-forward
  transport), `lib/exchange/src/essr.rs` (the reference implementation). ESSR is from the KERI lineage.
- This session's design conversation (the `{Icp, Gnt}` T2 key tier, the `data` = device-KEL-prefix / alias
  keying, the swap-vs-rescind split, the sender-key-currency requirement). Captured in
  `.working/vdti-receive-key-establishment-design.md`.
- The `shared-documents` note's exchange-layer forward ideas (per-doc content confidentiality) — a
  **consumer** of this feature (§7).

## The model in one paragraph

ESSR seals a message so that **only the recipient can read it** (ML-KEM-encapsulated to the recipient's
published receive key → AES-256-GCM) and **the sender is provably the author** (the sender ML-DSA-**signs**
the envelope SAID; the sender prefix rides **inside** the ciphertext; the recipient prefix rides **inside**
the signed plaintext). A **receive key** is a party's current public ML-KEM key, published as a
**value-bearing lookup SEL** at a **deterministic address** any sender computes from the party's IEL prefix
+ the exchange topic + a `data` selector. The published key is a **T2 sealed `Gnt`** (`vdti divergence`:
kels signs it with the ordinary key; vdti puts it behind `t_authorize`@T2 so a signing-key theft can't swap
it). Sealed envelopes are delivered by a **mail** service that stores opaque blobs and gossips only routing
metadata. On open, the recipient **verifies the signature against the sender's *current* witnessed key
state** (a verifier requirement the infra already supports, so rotation recovers messaging; an optional
message-anchor gives *provable* liveness). The feature is a **verification +
discovery + transport** layer; confidentiality/authenticity is ESSR, integrity of the key is the chain.
That is **mode 1** (ESSR, one-offs); a second **session mode** carries long-lived, ratcheting group chat
over the same spine (§1a / §7a).

## 1. ESSR — the authenticated-encryption construction (adopted from kels; sound)

**Every message here is a kinded SAD** — the universal vdti rule (all data is a kinded, SAID-addressed SAD),
so an envelope, its inner, and every exchange message are SADs, anchorable by SAID (§3).

- **Encrypt-Sender-Sign-Receiver**, four UnForgeability properties: **TUF-PTXT/CTXT** (a third party forges
  neither plaintext nor ciphertext), **RUF-PTXT** (the receiver can't forge sender attribution — the sender
  prefix is **inside** the ciphertext), **RUF-CTXT** (an attacker can't strip/replace the signature — the
  recipient is **in** the signed plaintext, anti-KCI).
- **Inner (encrypted):** `{ sender, topic, payload }` — `sender` = the sender IEL prefix (RUF-PTXT); `topic`
  multiplexes protocols **without** exposing the message type to the transport (it is inside the ciphertext);
  `payload` opaque.
- **Envelope (signed plaintext):** `{ said, sender, sender_serial, recipient, kem_ciphertext,
  encrypted_payload, nonce, createdAt }` — `sender` plaintext for routing, `recipient` signed (anti-KCI),
  `sender_serial` = the sender's establishment serial at signing time, `kem_ciphertext` the ML-KEM
  encapsulation, `encrypted_payload` the AES-256-GCM ciphertext, `nonce` its 12-byte AEAD nonce. The
  **signature is ML-DSA over the envelope SAID**, and the SAID commits to every field — so the signature
  binds the ciphertext, the KEM ciphertext, the recipient, and the nonce all at once.
- **Seal:** encapsulate to the recipient's receive key → shared secret → `blake3::derive_key(context,
  shared_secret)` (context = `vdti/exchange/v1/protocols/essr`) → AES key → **fresh random nonce** →
  AES-256-GCM(inner) → build envelope + SAID → ML-DSA-sign the SAID.
- **Open:** verify SAID → ML-DSA-verify against the sender's key **at the current establishment state**
  (§3) → decapsulate → derive AES key → AES-256-GCM-decrypt → assert `inner.sender == envelope.sender`.
- **Why the nonce is safe (adversarial note):** each message gets a **fresh** KEM shared secret → a **fresh**
  AES key used **exactly once**, so the random nonce never repeats under a key. The AEAD nonce/key-scope
  residual (federation §1e) does **not** bite here — the key is per-message.
- **Crypto (strength-paired, kels precedent):** ML-KEM-768/1024 (KEM), ML-DSA-65/87 (signatures), AES-256-GCM
  (AEAD), Blake3 KDF. Users may run **65/768**; infrastructure runs **87/1024**; the algorithms are
  integration-identical, so the tier is a parameter, not a code path (`../kels`).

## 1a. Two modes — ESSR one-offs and a ratcheting session (Jason 2026-07-14)

Exchange **encapsulates two modes** over one shared spine — published receive keys (§2), sender-key
currency (§3), the crypto suite, and mail (§5). **One feature, two modes:**

- **ESSR — one-offs.** Per-message, stateless, sealed to the recipient's published receive key. The
  **async baseline**: mail, one-offs, and any time the recipient is offline. Always available; the
  construction is §1.
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

## 2. Receive-key publication — a value-bearing lookup SEL, `{Icp, Gnt}` at T2

- **The address is deterministic (discoverable).** A receive key lives at `derive(owner, EXCHANGE_TOPIC,
  data)` — `owner` = the identity IEL prefix, topic = `vdti/exchange/v1/topics/receive-key`. A receive key is
  meant to be **found**, so it is **not** nonce-blinded; any sender holding the recipient's prefix computes
  it (the cost is the lookup-prefix residual, §6). `lineage` (area-sel §1f) handles reincept after a
  forced-dead key.
- **`data` = a device KEL prefix _or_ an alias (Jason 2026-07-12) — device-specific keys, elegantly.** The
  publishing identity's IEL has a **roster of member KELs (devices)**; setting `data` = a **member KEL
  prefix** yields a **per-device** receive key (a sender can target a specific device). Setting `data` = an
  **alias** (a short label) yields a key **without** the device lookup (same identity, no device disclosure).
  This is vdti's resolution of the kels in-flight "key-per-KEL vs key-per-identity" question (kels #137/#140)
  — **support both**, selected by `data`.
  - **Alias-naming discipline (correlation warning — load-bearing for the operator).** `data` is **public**
    on the mesh. A **descriptive** alias (`basement-mac`, `personal-iphone`) **leaks which device/key to
    steal** to read a given correspondent's mail. Aliases MUST be **opaque** (`primary`, `a`, a random
    label), so an observer can't map a key to a physical device — it raises the bar on *what to compromise*.
    A framework warning; the app/wallet enforces the naming.
- **The published value is a T2 sealed `Gnt` (`vdti divergence` from kels' T1).** The `Icp` establishes the
  lookup; a **`Gnt`** (area-sel §1b — T2 `t_authorize`, anchored by the owner IEL's `Ath`) seals the key.
  `manifest.grant` names a grant-value SAD of kind **`vdti/sel/v1/grants/exchange-ml-kem-1024`** (feature-
  first naming; the public ML-KEM-1024 encapsulation key). **kels signs its `kels/sel/v1/keys/mlkem`
  publication with the ordinary signing key (T1)** — so a signing-key theft swaps the key and reads the
  victim's mail. **vdti requires `t_authorize`@T2**, so a bare signing-key theft **cannot** swap it. The key
  is never T1 content.
  - `t_authorize` here is the **identity's own** authorization tier (the generalized `Gnt`/`Ath` applies to
    any identity's value establishment, not only doc-governance). Single-device → the reserve at T2;
    multi-device → its `t_authorize` quorum.
- **Rotation = stack `Gnt`s** (latest sealed key is live; the lookup serves only the live tip, so a retired
  key is never handed to a sender). Routine rotation is therefore a **T2 act**.
- **Rescission = `Trm`** (area-sel §1b, T2) — terminal kill → the key reads **dead** → senders **fail
  closed** (inv 10). Loss-of-control only; a rescinded key is respected; recovery is republish at a fresh
  `lineage`. Routine key change is a rotation (stacked `Gnt`), never a rescind.

## 3. Sender-key currency — verify against the witnessed KEL; anchor for provable liveness

- **Default: verify against the sender's _current_ witnessed key state.** ESSR's `open` extracts the sender's
  key at `sender_serial`; the recipient MUST also confirm that serial is the sender's **current**
  establishment state, read from the witnessed KEL/IEL (multi-source, inv 8) — **the infra already provides
  it.** A stale serial (a **captured-then-rotated** key signing under its old serial) reads stale and is
  **refused**, so a rotation recovers messaging and the concern collapses back into the stated
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
  size, createdAt, expiresAt }`) to all nodes. Lifecycle: **send** (store blob + gossip metadata) →
  **discover** (recipient queries any node's inbox) → **fetch** (from the origin node, authenticated —
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

- **IPEX-style credential exchange (kels precedent).** Apply / Offer / Agree / Grant / Admit / Reject
  messages (a thread chained by `previous`, topic `vdti/exchange/v1/topics/exchange`) ride ESSR to negotiate
  issuance and presentation. Adopted from kels' exchange messages; the vdti realization tracks the
  credential model (a credential = a direct-anchored SAD) — **detail deferred** to the exchange feature encode.
- **shared-documents off-node content.** A shared doc's private content (`shared-documents §5`) is delivered
  member-to-member as **ESSR payloads** (each recipient gets the content — or a wrapped per-doc symmetric key
  — sealed to their receive key). The `shared-documents §9` "KEM-wrapped group key / re-key on removal / key
  epochs" ideas are the **§7a session-mode group-key mechanism**: the group key rides a **key-epoch SEL**,
  ESSR-wrapped to per-period members, ratcheting on membership change + a time cadence — group chat and
  shared-doc content share it. (Resolves the former "open: whether the group key rides a SEL / the re-key
  cadence / the epoch commitment" — see §7a.)

## 7a. The session mode — long-lived ratcheting group sessions (Jason 2026-07-14)

The session mode (§1a) is **chat**: 1:1 and group, assumed to last **years**, so it **ratchets** for
forward secrecy. It is built **entirely from SAD / SEL / IEL**, and it **specializes** the
shared-documents group-key idea (§7) rather than reusing it wholesale — chat needs a bounded,
enumerable member set and a time-cadence ratchet the shared-documents access-list does not provide
(see "Relationship to shared-documents" below).

- **Members = person identities (IELs); the epoch key wraps once per member (Jason 2026-07-15).** Each
  member's **receive key** is owned by that member's **own identity IEL** — the `{Icp, Gnt}`
  value-bearing lookup SEL of §2 — so the group **never controls a member's key**: the member establishes
  and rotates it self-service, and no group governance can swap it. A member is a **person**, so
  **per-device key control is meaningless** — every one of a person's devices is the **same principal**
  (compromise one, you've compromised the person), so the epoch key wraps **once per member** (never per
  device), and a person's devices share that receive key's material. The per-message **subkey** stays
  device-keyed (see "Per-sender message keys") **purely for nonce-safety** (two of a person's devices
  must not collide under the shared epoch key), never as a control boundary. **Contrast the federation:**
  a witness has **no published receive key at all** — its mesh channel is an ephemeral,
  signature-authenticated handshake (`vdti-area-federation-witnessing.md` §1e), so the "who owns the
  key" question does not even arise there. Here it does, and the answer is the member's **own** identity
  IEL.
- **Group membership = a bounded, enumerable member roster (Jason 2026-07-14).** Unlike the
  shared-documents access-list — deliberately **unbounded**, resolved **per-participant** by O(1)
  lookup, **never materialized as a live set** (`vdti-area-shared-documents §1`) — the epoch wrap must
  **enumerate** the current members to seal the key to each, so chat carries a **bounded enumerable
  roster** (capped like `MAXIMUM_ROSTER_SIZE`), **gated / blinded** (below). Membership changes are
  governed at **T2** (the creator's `Gnt`←`Ath`, or a group policy), so a signing-key theft (T1) cannot
  add or remove a member and a removed member cannot re-admit itself. A **1:1 chat is the degenerate
  roster of two**.
  - **Roster privacy = gated / blinded (Jason 2026-07-15).** A **raw** IEL roster would list member
    prefixes **publicly** (witnesses verify anchoring against it), **leaking the group-membership
    graph** — who is in which group — to the witnesses, surrendering the **participant-blindness**
    shared-documents keeps (member names live in **gated** content, never public structure —
    `vdti-area-shared-documents §1`). So the roster is **gated / blinded**: member prefixes ride
    **read-gated opaque SAIDs** — **enumerable by members** (a member materializes the wrap-set), but
    **blind to witnesses** (who see only opaque anchors, never the member set). This is the
    shared-documents read-gating discipline applied to a **bounded enumerable** set — the answer to
    "does the bounded roster contradict a shared-docs guarantee?" is **no, once blinded**. (A **public**
    roster is therefore ruled out; the raw on-chain IEL-roster manifest is not the representation. How
    the gated set is stored — a gated SEL vs a membership policy — is the remaining representation
    detail, below.)
- **Key epochs = a SEL** advancing **one symmetric group key per epoch**. Each epoch key is **freshly
  generated (independent random), never derived from a prior epoch key** — so a compromise of one epoch
  key exposes **only that epoch**, nothing forward. It is **ESSR-wrapped to each current member** (one
  wrapped-key SAD per member — the §1 seal to each receive key), referenced by the epoch SEL event; a
  member unwraps with its receive-key private key. ESSR is used **only** for the per-epoch key.
- **Per-sender message keys — the nonce discipline (Jason 2026-07-14; device-keyed 2026-07-15).** Bulk
  messages are AES-256-GCM, but a **shared** epoch key has **many concurrent writers**, so a counter or
  naive nonce collides across senders (catastrophic for AES-GCM — the §1 fresh-key argument and the mesh
  single-writer counter both fail here). Each writer therefore encrypts under its **own derived subkey**
  `blake3::derive_key(epoch_key, device_kel_prefix)` — keyed on the **device (signing) KEL prefix, not
  the member identity**, so **two devices of one member are distinct writers** (an identity-keyed subkey
  would collide across a member's own two devices, reopening the reuse the subkey exists to close — and
  the message signature (below) is a device `t_use` key, so the device is the true writer). This restores
  the one-writer-per-key shape, so a device's per-message nonce cannot collide with another writer's. The
  epoch key is a **seed**, never used to encrypt directly.
- **Within-subkey nonce discipline.** A subkey has a **single writer** (one device), so its per-message
  nonce is that device's own sequence — a **persisted monotonic counter** (persisted across a restart,
  else a reset reuses a nonce) or a random nonce bounded by the epoch's message volume. The per-sender
  subkey removes the **cross**-writer collision; this removes the **within**-writer one.
- **Messages = kinded, nonce'd SADs, signed by their sender.** Confidentiality rides the per-sender
  subkey; **authenticity rides the sender's own signature** — each message SAD's SAID is
  **ML-DSA-signed with the sender's current `t_use` key** and **timestamped**. The epoch key proves only
  _"a group member"_; the signature proves _which_ member (ESSR's sender-unforgeability, restored for
  group mode). Thread-ordered by `previous`; **off-chain by default**, optionally **anchored** for
  non-repudiation.
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

**The ratchet — the epoch advances on either trigger, whichever comes first:**

- **Membership change** — add / remove → a **fresh** epoch sealed to the new member set. A removal
  gives **forward secrecy** (the removed member can't read new epochs); a joiner **can't read past
  epochs** (past keys were never wrapped to it, and epochs are independent). **Switchover discipline:** a
  removal **installs the new epoch immediately**; senders **must** encrypt under the new epoch once they
  observe the removal, and a message under the **retired** epoch is **rejected** after the removal
  boundary — else a lagging sender's old-epoch message stays readable/forgeable by the just-removed
  member. The wrap-set is bound to the membership rescission, not an author's local view.
- **Time cadence** — every `SESSION_RATCHET_INTERVAL` (~6–12h, a parameter — value TBD), advance to a
  **fresh** epoch even with stable membership, so a compromised **epoch key** exposes only **that
  window**. (This bounds a **symmetric-key** leak; a compromise of a member's **receive (KEM) key**
  unwraps **every** epoch wrapped to it during membership — that is what removal defends, and only
  forward.)

**Epoch-based, not a per-message double-ratchet** — a per-window group key (a fresh, **independent**
key per epoch distributed by wrapping, in the spirit of MLS's epochs but **not** a derived key schedule
— nothing unrolls forward from a compromise), matching the time-cadence ratchet and fitting the group
case, not Signal's pairwise per-message ratchet.

**Relationship to shared-documents.** This is the shared-documents §7/§9 "KEM-wrapped group key /
re-key on removal / key epochs" idea **specialized** for chat — the same wrap-to-members skeleton, but
chat **adds** (a) a **bounded enumerable roster** (the shared-docs access-list is unbounded, never
materialized), (b) a **time-cadence** ratchet (shared-docs re-keys on membership change only), (c)
higher message **volume** with the per-sender-subkey nonce discipline, and (d) per-message **sender
signatures**. So it is **related to, not identical with**, the shared-documents mechanism — both share
only the receive-key + ESSR-wrap primitive.

**Primitive-support check (Jason: "ensure the primitives + substrate can support it") — partially
answered.** A SEL `Gnt` **can** seal a per-epoch value and IEL identities supply the members and
receive keys (§2) — that much holds with no new primitive. The **per-sender subkey / nonce** discipline
and the **per-message sender signature** are **now specified on existing primitives**
(`blake3::derive_key` device-keyed + AES-256-GCM; ML-DSA `t_use` signing with epoch-window currency), so
they need no new primitive. The roster is **gated / blinded** (privacy resolved — above). **Still open:**
the **bounded enumerable member roster** is a new membership shape (not the shared-docs access-list) —
its **storage** (a gated SEL vs a membership policy) is the remaining representation detail; and the
**session-key SEL length bound**.
Epoch advance is **stacking `Gnt`s** (`area-sel §1f`) — **not** `lineage` (a loss-of-control
re-establishment counter capped at `MAXIMUM_SEL_LINEAGE`, irrelevant to the epoch count); over a
years-long chat at ~6–12h that is **thousands** of seal-advancing `Gnt`s on one SEL, bounded by no
existing cap (`MAXIMUM_UNSEALED_RUN` caps only non-seal-advancing runs), so a **cold** verifier walks
the whole SEL. Whether that is acceptable paged, or wants a periodic **checkpoint / re-inception** of
the session SEL, is open.

**Open items (§7a):** the `SESSION_RATCHET_INTERVAL` value; the epoch-SEL shape and its length bound
(checkpoint cadence); the **gated / blinded** roster's **storage** (a gated SEL vs a membership policy)
and its cap (**privacy resolved — gated / blinded, above**); the epoch key wraps **once per member**
(per-device dropped as meaningless — resolved above); how an **offline** member catches up across missed
epochs; the 1:1 path;
message-anchoring policy; whether the live channel ever carries epoch keys (resolve to **never raw** —
always ESSR-wrapped).

## 8. Reserved names + schemas (convention `vdti/<concept>/v1/<category>/<thing>`; concept **`exchange`**)

- **SEL topic:** `vdti/exchange/v1/topics/receive-key` (owner = identity IEL; `data` = device KEL prefix or
  opaque alias; `lineage` for reincept). Message topic (inside the ciphertext): `vdti/exchange/v1/topics/exchange`.
- **KDF context:** `vdti/exchange/v1/protocols/essr` (Blake3 derive-key).
- **Grant-value kinds** (`Gnt.manifest.grant` — `vdti/sel/v1/grants/<feature>-<detail>`, feature-first, ≤ 64
  chars): `vdti/sel/v1/grants/exchange-ml-kem-1024`, and the reduced-tier sibling
  `vdti/sel/v1/grants/exchange-ml-kem-768`. The grant value is the public ML-KEM key (scheme-tagged), named by
  its `grants/*` kind — no bespoke schema.
- **Exchange SADs** (`vdti/exchange/v1/schemas/*`): the ESSR envelope + inner + the exchange-message shapes
  (Apply/Offer/…); field layout at the encode, tracking `../kels lib/exchange`.
- **Session / group names (§7a — owed at encode):** SEL topics `vdti/exchange/v1/topics/group` (the
  bounded member roster) and `vdti/exchange/v1/topics/session-key` (the key-epoch log); grant-value kind
  `vdti/sel/v1/grants/exchange-group-key` (the ESSR-wrapped epoch key); KDF context
  `vdti/exchange/v1/protocols/session` (the per-sender subkey
  `blake3::derive_key(epoch_key, device_kel_prefix)` — device-keyed, §7a); message SAD
  `vdti/exchange/v1/schemas/message` (sender-signed + timestamped, epoch-window currency); constant
  `SESSION_RATCHET_INTERVAL` (~6–12h, value TBD).

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
- **The session mode (§1a / §7a) is part of the exchange encode** — the two modes, the bounded member
  roster + key-epoch SELs, the per-sender-subkey nonce discipline, per-message sender signatures, and the
  ratchet; the `examples/chat` + `examples/mail` apps compose it. The §7a primitive-support check is
  **partially** answered (a `Gnt` seals a value ✓; the per-sender-subkey nonce discipline + per-message
  sender signature are now specified on existing primitives ✓; the roster is **gated / blinded** ✓; the
  **bounded enumerable roster's storage** and the **SEL-length bound** remain open).
- **Open (flagged):** the session-mode open items (§7a — ratchet interval, epoch-SEL shape + length bound,
  the gated/blinded roster's storage, offline catch-up); scoped delivery metadata (§5); the IPEX
  exchange-message detail (§7); whether **mail** is a sibling feature note rather than a section here.
