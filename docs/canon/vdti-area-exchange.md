# vdti — area note: Exchange (published receive keys + delivery; consumes the ESSR primitive)

**Status: FIRST CUT — drafted with Jason 2026-07-12 (this session). Adapts the built `../kels` exchange +
mail design; not yet dual-pass reviewed.** A **feature** over the SAD + SEL primitives: parties exchange
**authenticated, confidential** point-to-point messages using **ESSR** (the 1:1 sealed authenticated
envelope, now a protocol primitive — [`vdti-area-essr.md`](vdti-area-essr.md)), delivered store-and-forward by a
**mail** transport, keyed by **published ML-KEM receive keys**. **No new primitive** — a receive key is a
**value-bearing lookup SEL** established `{Icp, Gnt}` (area-sel §1f + the generalized `Gnt` seal-a-typed-
value mechanism). **This is the kels exchange/mail design re-expressed on vdti primitives**, with one
deliberate vdti divergence (the encap key at **T2** not T1) and one stated verifier requirement
(**sender-key currency** — the signature bound to the `senderPin` key-state's witnessed validity window, §3;
an optional message-anchor gives an end-verifiable send-time). **Lands at**
`docs/design/features/exchange.md` (design-voice, forthcoming).

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
it). Sealed envelopes are delivered by a **mail** service that stores opaque blobs **scoped to the
recipient's own inbox nodes** (`availability.replicas` = the recipient's published node hints — no
federation-wide gossip of the communication graph). On open, the recipient **binds the signature to the
sender's witnessed key-state _window_** — the `senderPin` key-state's validity window bounded by the sender's
own **witnessed establishment times** (each establishment event's threshold-crossing receipt τ, §3), so an
honest pre-rotation message is accepted and a captured-then-rotated key is bounded to its now-closed window; an
optional message-anchor gives an *end-verifiable* send-time. The feature is a **verification +
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

## 3. Sender-key currency — bind the signature to the witnessed key-state window; anchor for an end-verifiable send-time

- **Default: bind to the `senderPin` key-state's validity interval, bounded by the sender's own witnessed establishment times (reworked
  2026-07-19; spine / witnessed-time derivation 2026-07-19c, superseding the 2026-07-19b federation-clock derivation — which quantized to federation governance cadence (~yearly) → empty intervals → re-stranded honest mail, round-3 P0).** ESSR's `open` extracts the sender's key at `senderPin`
  (an **IEL key-state position**, §1); the recipient reads the sender's witnessed KEL/IEL to the tip under a **multi-source freshness bar** (inv 8; a single-source / eclipsed read **refuses**, fail-secure) and checks the signature was current on **both axes** at the message's `timestamp`: **(i)** `senderPin`'s **IEL establishment interval** is open — an eviction / roster change closes it though it never touches an evicted device's own KEL — and the signature meets that establishment's roster + `t_use`; **(ii)** each signing **device's KEL** key-window is open (a harvested rotated-out device key is closed here) — cold-F2. Each interval is bounded by the **witnessed times** of the sender's own establishment events (its IEL _spine_ + its devices' KEL rotations), where an event's **witnessed time** is the instant it became witnessed-in-full — the receipt τ that brought it to `threshold` (federation §An-event's-witnessed-time). `open` accepts iff the `timestamp` falls in the interval `senderPin`'s key-state was current for **and is not future-dated** (`≤ now + CLOCK_TOLERANCE_BAND`, cold-F11). A still-current key
  has an **open** interval (a live message passes); an honest message sent **before** a later rotation falls in
  the now-closed interval and is **accepted** — so a rotation no longer strands in-flight mail (this
  **supersedes** the earlier rigid "must be the _current_ tip"). **The threshold-crossing witnessed time is byzantine-robust where a per-witness or "newest-τ" reduction is not:** the security-critical direction can't be inflated — the establishment event's ≥ `threshold` **durable** honest receipts pin the crossing in the past (adding late receipts can't move the `threshold`-th-smallest later; read multi-source), so a stale key's upper boundary can't be pushed to "now"; each τ is capped at `now + CLOCK_TOLERANCE_BAND` and window-bounded. Boundaries have **per-event granularity** at any cadence (resolving the quantization) but are **not self-ordering**, so the verifier **checks** them in-bounds + non-decreasing along the chain and **reports** on its token — a structural violation bails (fail-secure), an out-of-order pair is reported, never a silent empty interval. The tolerance band
  (federation §1f) absorbs an honest sender's near-boundary skew. A verifier **requirement**, data-only, no new
  mechanism. **The send-time `timestamp` rides inside the sealed payload** (ESSR carries no cleartext timestamp
  — area-essr §privacy), is **required** on a mail payload, checked **post-decrypt**, and **refuse-on-absent**
  (fail-secure). **Residual (bounded, not prevented):** a **captured-then-rotated** key can still be backdated
  **within** its closed interval but is stuck there — it can never read as **current**, so a rotation recovers
  messaging forward. The ordinary signing-key-compromise limit (inv 13), the same residual the epoch and the
  federation clock accept. A self-asserted timestamp only places the message **within** its past interval; the
  sender's own witnessed establishment times are the trust
  anchor. (Aligns with [inv 21].)
- **Optional: anchor the message for an _end-verifiable_ send-time (Jason 2026-07-12/19).** A message is a
  **kinded SAD** (with a **nonce** — the universal rule), so an end-verifiable send-time is just **anchoring
  its SAID on an IEL `Ixn`** — no wrapping step. The `Ixn` is authored by the **current** signing key, so a
  stale/captured key can't produce it, and **any** verifier (not just the recipient) reads the anchor on the
  sender's witnessed chain, proving the message sat in a witnessed batch by a witness-asserted time — stronger
  than the window bound. **Batches like issuance** (several simultaneous messages share one `Ixn`, ≤
  `MAXIMUM_MANIFEST_LIST`, not a chain event apiece; no "one per `Ixn`" rule). The opt-in for high-value /
  non-repudiable messages, not routine mail (which uses the lightweight window check above).

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

- **Payload-agnostic transport, recipient-scoped.** A mail node stores opaque **`SignedEssrEnvelope`** blobs
  plus the sealed inner (a **content-addressed blob** named by the envelope's `payloadDigest` + `payloadSize`),
  **scoped to the recipient's own inbox nodes** — the sender sets `availability.replicas` to the recipient's
  published **node hints**, so the sealed content lives only there and the recipient polls **its own** nodes;
  there is **no federation-wide gossip** of who-mails-whom. Lifecycle: **send** (deposit the message + upload
  its payload blob — a **fan-out** send (§1a) seals **one envelope per recipient device key**, each to that key
  and all addressed to the recipient identity, so a device fetches the blob sealed to **its** key; a `key_label`
  send targets one) → **discover** (recipient polls its own inbox nodes) → **fetch** (through the **serve-time
  gate** — the store serves the bytes only to a live-signed requester that proves it controls the recipient
  prefix; the seal already protects confidentiality, so the gate limits store-side harvesting, not integrity) →
  **open** (§1, with currency §3) → **ack** (origin deletes the blob). Rate limits: per-sender/day,
  per-recipient inbox cap, per-node storage cap, per-IP token bucket, message TTL, a short nonce-dedup window.
- **Residual — the communication graph is visible to the recipient's home nodes (recipient-scoped, shipped).**
  Recipient-scoped delivery is the **shipped** model (**not** a forward option): it limits exposure to the
  storage nodes a recipient chose — far tighter than gossiping the graph federation-wide — but those nodes
  still see who mails their user, when, and how large; and the **node hints are themselves targeting metadata**
  (publishing where a recipient's mail lives). The scoping is also **sender-cooperative** (an honest sender
  honors `availability.replicas`; a determined one could leak). Mixing and cover traffic are out of scope.
  **(vdti has no single-node standalone mode — the kels standalone mail mode does not carry over; a floored
  federation is assumed.)**
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
  for group mode). The lane is a **single-parent [authored DAG](vdti-area-authored-dag.md)**: `(epoch,
  timestamp)` is **non-decreasing** along `previous` (a backdated tip-append is malformed) and a **second child
  of a message = a fork = self-signed equivocation** (self-signed evidence; a crash-**resend** carries the _same_
  SAID — a dedup — and a crash before persisting, re-authored with a fresh nonce, is a genuine honest sibling, so
  whether a fork is misbehavior is the group's policy, not automatic; consequence coupled to `chat-membership`
  removal + the epoch turn). A second **root** is **not** a fork (two roots share no parent, and two roots are not
  self-proving) — the writer's single lane is enforced by its **grant-anchored root** (admission registers it; an
  unanchored root is rejected), not by single-parenthood ([authored-DAG](vdti-area-authored-dag.md); PR#25 r2
  W1/cold-P1). **Off-chain by default**, optionally **anchored** for non-repudiation.
- **Message currency: auth against the writer's own IEL key-window; the epoch SEL bounds _when_ (Jason
  2026-07-15 "A2 is a good finding"; two-axis correction 2026-07-19).** Chat's **auth uses the same key-window
  as §3** — the signature verifies against the writer's signing key-state, valid per the **writer's own
  witnessed KEL/IEL** interval, each boundary the **witnessed time** of the writer's own establishment event
  (the receipt-threshold-crossing τ — §3; **not** a per-witness or newest-τ reduction). The **epoch is a _separate_ axis** — the
  **encryption** key, **not** the auth window: a message decrypts **only** under epoch _N_'s per-sender subkey
  (you must hold that epoch key to produce a readable message), and epoch _N_ is a **witnessed** SEL event whose
  **window — bounded by the witnessed times of epoch _N_'s and _N+1_'s SEL events** — **bounds when** the message was
  authored — the **epoch anchors the key-state selection**, so the chat message has **no** key-state pin and
  needs none. So the check composes two witnessed sources — the **IEL** says whether the signing key was valid,
  the **epoch SEL** says the message was authored within epoch _N_'s window — authentic iff the key was valid
  (per its IEL interval) at a time inside that window. **Backdating decomposes (cold-F4 + PR#25 r2 W1/cold-P1/W2):**
  the lane's `(epoch, timestamp)` monotonicity (the authored-DAG rule, below) kills tip-append backdating. A
  **current** member backdating below its advanced tip must **fork its own lane** — a self-signed equivocation any
  reader surfaces, confined, never forward. A **removed** member is **fully closed at the verifier**: its `chat-membership`
  removal recorded a **lane-tip `bound`** on the **witnessed** grant chain, so honored history is exactly the
  `bound`'s ancestor-chain `[anchored root … bound]` and **any node off it is not honored** — a frozen-tip
  forward-append past the bound (a descendant), a **fork below the bound** (a sibling of an on-chain node), and a
  **fresh parentless root** (unanchored — a grant-chain act anchored the one lane the verifier honors) alike (a
  local interval check against the durable `bound`, not fork detection; PR#25 r5 cold-P1). The **residual** is a **dormant current** member (never removed, valid key)
  forward-appending into an epoch it held but was silent for — the accepted backdate-within-a-held-window class,
  own lane, timestamp advisory; the opt-in anchor strengthens it. The self-asserted timestamp never establishes
  currency; the two witnessed windows do.

**The ratchet is the primitive's.** Epochs advance on a membership change or a time cadence — that, with
the forward-secrecy and switchover discipline, is the group-key primitive's ([`vdti-area-group-key.md`](vdti-area-group-key.md));
chat only observes the current epoch. What chat adds over the primitive is the **volume** (the per-sender-lane
nonce discipline, above) and the **per-message sender signatures** — the two properties a high-traffic chat
needs that a shared-document does not.

**Resolved (§7a — the chat consumer's store-auth, 2026-07-19):** the store checks a **`chat-membership`**
instance of the [membership](vdti-area-membership.md) primitive — a **distinct** grant chain, **not** a view of
the group-key wrap roster (the roster is member-materialized + blind to the store; chat composes **both** — the
roster to distribute the epoch key, `chat-membership` to authorize a requester). Per-requester (fail-secure walk
by default, O(1) content-addressed rescission lookup — keyed on the member's **grant instance**, not the bare
prefix (PR#25 r2 W5) — under a latency budget), never materializing the set. The store check is per **identity**
(any of a member's devices reads), while each writing **device** anchors its own lane **on-demand** — a body-less
join marker registered by a governing grant-chain act (never a member self-attestation: a removed member still
controls its own devices). **Removal rescinds the grant + records a per-device-lane `bound` on the rescission
`Trm`'s `bound` role as the same act turns the epoch** — bracketing each writing device's honored lane
**`[anchored root … bound]`** (disjoint per membership period; a fresh unanchored root is rejected; a
missing/unresolvable `bound` reads fail-secure — PR#25 r2 W1/cold-P1 + r3 cold-P1). A **divergent** sender/writer
chain freezes a **current** read like any live `t_use` consumer — **Forked or Disputed → refuse** a current
(open-interval) claim (the sender's live `t_use` is frozen on any divergence); already-witnessed **closed-interval**
history is **as-issued** and still reads (single-tipped in the past — even on a Disputed sender below its last
clean seal, so the refusal is the live-authority freeze, not "no single answer") — PR#25 r3 cold-P2-2 + r4 Y1. Retires round-3 F3 **and** the round-2
"readers-grant" open. The lane's monotonicity + fork rule + anchored root is the
[authored-DAG](vdti-area-authored-dag.md) single-parent variant (round-3 F4 + PR#25 r2 W1). _(Offline catch-up, the 1:1 path,
and the anchoring policy resolved — decisions 1/2/3.)_ The roster storage, the epoch-SEL length bound / checkpoint
cadence, the `SESSION_RATCHET_INTERVAL` value, and the never-raw epoch-key rule are the **primitive's** — see
[`vdti-area-group-key.md`](vdti-area-group-key.md).

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

- Write `docs/design/features/exchange.md` fresh from this note (greenfield voice).
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
- **DONE (2026-07-19, round-3 fold).** Sender-key currency reworked to the **spine / witnessed-time** mechanism
  (§3 + inv 21 + §Model + §7a — boundaries = the sender's own establishment events' witnessed times, the
  threshold-crossing receipt τ defined in federation §An-event's-witnessed-time; drops the 2026-07-19b
  federation-clock derivation, round-3 P0; two-axis IEL + KEL, cold-F2). Chat store-auth is the
  **`chat-membership`** instance of the new [membership](vdti-area-membership.md) primitive (round-3 F3); the
  chat lane is the single-parent [authored-DAG](vdti-area-authored-dag.md) with monotonicity +
  fork-is-equivocation (round-3 F4). Reserved `vdti/exchange/v1/topics/chat-membership` +
  `vdti/sel/v1/grants/chat-membership`; fixed the tags-and-topics SEL-vs-message-topic collision.
- **⚠ Deferred (shared-documents PR — DO NOT DROP):** the `shared-document-governance` → `document-membership`
  rename (+ its `shared-document-read-governance` sibling) and wiring shared-docs onto membership + the
  multi-parent authored-DAG — see [`vdti-area-membership.md`](vdti-area-membership.md) and
  [`vdti-area-authored-dag.md`](vdti-area-authored-dag.md) Drift → land.
