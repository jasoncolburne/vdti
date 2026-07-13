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
  epochs" ideas are **this**, made concrete: ESSR to each current member; re-key = seal a fresh key to the
  remaining members; epochs align to `[from, bound]` membership periods. **Open:** whether the group key rides
  a SEL, the re-key cadence, and the epoch commitment — settle when shared-documents forces them.

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
- **Open (flagged):** the group-key mechanism (§7); scoped delivery metadata (§5); the IPEX exchange-message
  detail (§7); whether **mail** is a sibling feature note rather than a section here.
