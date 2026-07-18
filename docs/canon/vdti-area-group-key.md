# vdti — area note: Group-key (the ratcheting shared-key primitive)

**Status: FIRST CUT — lifted from `vdti-area-exchange.md` §7a into its own protocol primitive (2026-07-17,
Jason).** Group keying is used by **both** the exchange feature (group chat) **and** shared-documents
(content confidentiality), and it is entirely feature-agnostic — so, like ESSR and IPEX, it is a **protocol
primitive** both features compose, not an exchange-internal mechanism. Lifting it kills the feature-on-feature
dependency (shared-documents would otherwise depend on exchange for its content keying). It **composes the
sealed-send core** — ESSR (the 1:1 seal — [`vdti-area-essr.md`](vdti-area-essr.md)) + the
[receive-key directory](vdti-area-receive-key-directory.md) + substrate transport — reusing it, not the exchange
feature; its consumers are the exchange and shared-documents features.

**Layering:** the sealed-send core (ESSR + receive-key directory + transport) → **group-key** (fan-out + epochs +
ratchet) → {exchange, shared-documents} features → apps. **Credentials never touches it** (credentials composes
IPEX only, staying transport-agnostic).

**Invariants:** [inv 14] witnessing prevents content forks (the epoch SEL is its own witnessed chain), [inv 8]
multi-source freshness (a member reads the current epoch), [inv 10] value-bearing lookup fails-closed, [inv 16]
addressing by prefix + gated membership, [inv 19] signatures are over the fully-compacted SAID (the consumer's
per-message signatures), [inv 20] a device compromise is a confidentiality loss, never a control loss. Composes:
the **sealed-send core** — ESSR + the [receive-key directory](vdti-area-receive-key-directory.md) + substrate
transport (§Distribution); the SEL primitive (the roster + key-epoch logs).

## What it is

A **ratcheting shared symmetric epoch key** over a **bounded member set**, distributed by **wrapping the epoch
key to each current member's device receive keys** (once per device, through the sealed-send core). The primitive
exposes one thing: **the current epoch key, unwrappable by each current member's devices** — nothing about *what*
the consumer encrypts with it. Each epoch key is **freshly generated (independent random), never derived from a
prior epoch**, and the primitive **ratchets** it to a new epoch on either trigger, whichever comes first: a
**membership change** or a **time cadence**.

The blast radius is exactly this: **the wrap seals only the (small) epoch key, once per device.** A consumer's
bulk data (chat messages, document content) is **never** wrapped — it is encrypted once under the epoch key (or a
subkey of it), by the consumer.

## The pieces

- **The member roster — a bounded, enumerable, gated/blinded SEL.** The epoch key must be wrapped to each
  current member's devices, so the primitive must **enumerate** the members (then, via each one's directory, their
  devices) — unlike the shared-documents access-list, which is deliberately unbounded and never materialized. So the roster is a **bounded, enumerable** set (capped like
  `MAXIMUM_ROSTER_SIZE`), **gated / blinded**: member prefixes ride **read-gated opaque SAIDs** — enumerable by
  members (a member materializes the wrap-set), **blind to witnesses** (who see only opaque anchors, never the
  membership graph). This applies the shared-documents read-gating discipline to a bounded enumerable set, so the
  bounded roster does **not** surrender participant-blindness ([inv 16]). Membership changes are governed at
  **T2** (the group creator's `Gnt` ← `Ath`, or a group policy), so a signing-key theft (T1) cannot add or
  remove a member, and a removed member cannot re-admit itself. **Members are person identities (IELs)**; each
  member's device receive keys live in that member's **own** [receive-key directory](vdti-area-receive-key-directory.md)
  (a shared-core lookup SEL its identity IEL owns), so the group **never controls a member's key** — a member
  establishes and rotates its devices' keys self-service. The epoch key is wrapped to **each member's devices**
  (once per device — the directory enumerates them), not to a single per-member key: a device receive key is
  hardware-resident, so per-device is what makes removal a genuine lockout (see "Hardware, compromise, and the two
  axes").
- **The key-epoch SEL** — a single-owner SEL advancing **one fresh independent symmetric key per epoch**. Each
  epoch SEL event references the **per-device** wrapped-key SADs for that epoch; a device unwraps its own with its
  hardware receive key. Because each epoch key is independent, a compromise of one epoch key exposes **only that
  epoch**, nothing forward.
- **Distribution = the sealed-send core, once per device.** The epoch key is distributed through the
  **sealed-send core** (ESSR + the [receive-key directory](vdti-area-receive-key-directory.md) + substrate
  transport): the primitive enumerates the roster (members) → each member's directory (its devices) → **seals the
  epoch key to each device's receive key**, producing one wrapped-key SAD per device. This is **KEM+DEM** — the
  epoch key is the (32-byte) payload, wrapped `Encaps(pk) → ss`, `AEAD(KDF(ss), epoch_key)`; the consumer's bulk
  data is never wrapped, only the key. Because it is the sealed-send core, **offline catch-up falls out**:
  transport is store-and-forward, so a device offline at ratchet time receives its wrap on reconnect. The
  **epoch's authenticity is the T2-governed key-epoch SEL event** (a member trusts an epoch by validating that
  event and finding its device's wrap committed by it); the ESSR **signature** on each wrap is uniform with the
  rest of the system but not load-bearing for that. The baseline wrap is **full ESSR**; a lighter **KEM+AEAD-only**
  seal — ESSR's confidentiality core _without_ the signature, so **not ESSR proper** — is an available
  optimization, settled at the encode.
- **The wraps are member-delivered, never published.** Each ESSR wrap carries its `recipient` in cleartext (for
  routing + anti-KCI), so the wrap-set would **enumerate the devices** (hence the members) to anyone holding it.
  The wrap **bodies** are therefore delivered device-to-device and **never served to the store / witnesses** — the
  same never-publish discipline [inv 16] imposes on a private credential body or a data-bearing `Icp` — so the
  key-epoch SEL event leaks only the **count** of wraps (the device count, already bounded), never _who_. The
  cleartext `recipient` is seen only by the receiving device and the transport (the §5 delivery-metadata
  residual), not by chain verifiers. **This is what keeps the member / device set blind to witnesses** — the
  gated roster alone does not, since the wraps would otherwise re-expose it.
- **The ratchet — the epoch advances on either trigger, whichever comes first:**
  - **Membership change** — add / remove → a **fresh** epoch sealed to the new member set. A removal gives
    **forward secrecy** (the removed member cannot read new epochs); a joiner **cannot read past epochs** (past
    keys were never wrapped to it, and epochs are independent). **Switchover discipline:** a removal **installs
    the new epoch immediately**, senders **must** encrypt under the new epoch once they observe the removal, and
    a message under the **retired** epoch is **rejected** after the removal boundary — else a lagging sender's
    old-epoch message stays readable / forgeable by the just-removed member. The wrap-set is bound to the
    membership rescission, not an author's local view. **Residual:** a message a lagging sender emits under the
    retired epoch **before** it observes the removal is still readable by the just-removed member (a removal
    can't retroactively unsend it); the window is bounded by how fast senders observe the removal, and closes
    once all have switched over.
  - **Time cadence** — every `SESSION_RATCHET_INTERVAL` (~6–12h, a parameter — value TBD), advance to a **fresh**
    epoch even with stable membership, so a compromised **epoch key** exposes only **that window**. (This bounds a
    symmetric-key leak. A member's **receive (KEM) key** is hardware-non-extractable, so a device compromise
    cannot walk off with it — it reads only during live access, and removal + the next ratchet lock it out; see
    "Hardware, compromise, and the two axes.")
- **Epoch-based, not a per-message double-ratchet.** A fresh **independent** key per epoch, distributed by
  wrapping — in the spirit of MLS's epochs, but **not** a derived key schedule (nothing unrolls forward from a
  compromise). Fits the group case; not Signal's pairwise per-message ratchet.
- **The epoch key never rides any channel raw** — always ESSR-wrapped on the key-epoch SEL.
- **Checkpoints (bounded verification).** A long-lived session at ~6–12h accrues **thousands** of seal-advancing
  epoch events on one SEL, bounded by no existing cap, so a cold verifier would walk the whole history. The
  primitive **re-incepts a fresh key-epoch SEL every K epochs** (chained to its predecessor), so a cold verifier
  walks a bounded suffix. (The checkpoint cadence K is a parameter — settled at the encode.)

## Hardware, compromise, and the two axes

The wrap targets are **device receive keys**, and each is an **enclave-resident, non-extractable ML-KEM key —
always in hardware** (the [receive-key directory](vdti-area-receive-key-directory.md)'s rule). Three consequences
the primitive relies on:

- **Removal is a genuine lockout.** A removed device's KEM key cannot be exfiltrated (hardware), so on a ratchet
  it simply is not among the wrap targets — it never held a key it could replay against the next epoch. (Contrast
  a software key, which a compromise could copy and use to unwrap every future epoch offline — hence hardware is
  required, no software path.)
- **Confidentiality ≠ control ([inv 20]).** A compromised device reads what it can decrypt — bounded by hardware
  non-extractability (read only during live access), the ratchet (a grabbed epoch key rots), and re-key on
  removal (locked out forward). It **cannot take over the identity** (governance is `t_govern`@T2; one device is
  a single `t_use` share). So a device compromise is a **confidentiality** loss, never a **control** loss — never
  conflate the two.
- **Attestation is the counterparty's policy, not the primitive's.** A group that needs assurance every member's
  device key is hardware-resident requires an **attestation** on the directory entry (the directory's optional
  `{ format, statement }`) — a policy knob at the group's edge, never in the substrate.

At-rest, a member need not store the epoch key in the clear: its at-rest form is the ESSR wrap on the key-epoch
SEL, unwrapped on demand by the hardware KEM key (biometric-gating the decapsulation is an optional device
policy). The hard floor — a live rooted device reads its own in-use plaintext — is universal, bounded by the
ratchet, not a group-key gap.

## Using the epoch key — the consumer's, with one primitive-provided discipline

The primitive hands the consumer the current epoch key; **what is encrypted with it is the consumer's.** One
discipline the primitive states because it is general and easy to get wrong:

- **Many concurrent writers → per-writer subkeys for nonce-safety.** A shared epoch key has **many** writers, so
  a counter or naive nonce **collides across writers** — catastrophic for an AEAD like AES-256-GCM. Each writer
  therefore encrypts under its **own derived subkey** `derive(epoch_key, writer)`, keyed on the **writing device
  (signing) KEL prefix** so two devices of one member are distinct writers. This restores a single writer per key,
  so a writer's per-message nonce (a persisted monotonic counter, or random bounded by the epoch's volume) cannot
  collide with another's. The epoch key is a **seed**, never used to encrypt directly. **A subkey authenticates
  nobody** — every member can derive every member's subkey from the shared epoch key, so it is purely a
  nonce-partitioning device; **authenticity is the writer's own signature** (below).

The two consumers realize the rest their own way:

- **Group chat (exchange feature — [`vdti-area-exchange.md`](vdti-area-exchange.md) §7a).** Messages are
  **per-sender lanes** (a DAG of per-writer chains — the lane *is* the writer, so no sender field is carried),
  encrypted under the writer's subkey, each signed by the writer's `t_use` over the message's **fully-compacted
  SAID** ([inv 19]) with **epoch-window currency**. The epoch key proves only *"a group member"*; the signature
  proves *which* member.
- **Shared-documents content (feature — [`vdti-area-shared-documents.md`](vdti-area-shared-documents.md)).** A
  per-document content key is wrapped under the epoch key; members unwrap and decrypt the document content.

## The boundary — what is not group-key

- **The 1:1 seal** — ESSR, below (the primitive calls it, does not define it).
- **Bulk data encryption, message structure (lanes), per-message signatures, delivery** — the consuming feature.
- **Membership governance** (who is admitted / removed, under what authority) — a **T2 act** the feature / app
  drives; the primitive consumes the resulting bounded roster.
- **A member's device receive keys** — the [receive-key directory](vdti-area-receive-key-directory.md)
  (shared-core, owned by the member's own identity IEL); the group reads it to fan out, never owns it.
- **The 1:1 degenerate case, offline catch-up across missed epochs** — consumer / feature concerns.

## Divergence / sources

Lifted from the exchange session-mode design (`vdti-area-exchange.md` §7a, Jason 2026-07-14 / 15) — the
member-owned key, gated/blinded roster, fresh-independent-per-epoch key, and the membership + time-cadence ratchet
are all from there; this note promotes them from an exchange-internal mechanism to the shared primitive both
exchange and shared-documents compose. The **per-device** wrapping, hardware-resident ML-KEM keys, the sealed-send
core reuse, and the confidentiality/control split ([inv 20]) are the 2026-07-18 clean-model refinement (Jason).
MLS-epoch in spirit (fresh key per epoch distributed by wrapping), **not** a derived key schedule.

## Drift → land

- **DONE (2026-07-17 lift-reconcile).** `vdti-area-exchange.md` §7a trimmed to the **chat-consumer** usage
  (per-sender lanes, per-message signatures, epoch-window currency), with the roster / key-epoch / wrap / ratchet
  pointed here; `vdti-area-shared-documents.md` §9 composes this primitive for content keying (§7 carried no
  keying); the ESSR note's boundary names this primitive.
- **DONE — reserved names registered** (`kinds.md` + `tags-and-topics.md`; the exchange §8 names moved out of the
  `exchange/` namespace): component **`groupkey`**; SEL topics `vdti/groupkey/v1/topics/key-epoch` (the key-epoch
  log) and `vdti/groupkey/v1/topics/roster` (the gated member roster); grant-value kind
  `vdti/sel/v1/grants/groupkey-epoch-key` (the ESSR-wrapped epoch key); KDF context
  `vdti/groupkey/v1/protocols/kdf` (the per-writer subkey); constant `SESSION_RATCHET_INTERVAL` and the
  checkpoint cadence `K`.
- **DONE (2026-07-18 clean-model fold).** Per-device wrapping (the epoch key wraps to each member's **device**
  receive keys via the [receive-key directory](vdti-area-receive-key-directory.md), not once per member);
  hardware-resident ML-KEM + attestation-as-policy; distribution reuses the **sealed-send core** (ESSR + directory
  + transport), so offline catch-up falls out; the KEM+DEM mechanism (encaps-then-AEAD, payload once); the
  confidentiality/control split ([inv 20]) replaces the old "compromise one = compromised the person" framing.
- **Owed (design encode).** Write `docs/design/primitives/protocols/group-key.md` fresh from this note
  (greenfield voice), alongside `protocols/{essr,ipex}.md`; the `SESSION_RATCHET_INTERVAL` value, the checkpoint
  cadence `K`, and the roster-storage / epoch-SEL length bound settle there.
