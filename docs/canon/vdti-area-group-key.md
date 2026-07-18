# vdti — area note: Group-key (the ratcheting shared-key primitive)

**Status: FIRST CUT — lifted from `vdti-area-exchange.md` §7a into its own protocol primitive (2026-07-17,
Jason).** Group keying is used by **both** the exchange feature (group chat) **and** shared-documents
(content confidentiality), and it is entirely feature-agnostic — so, like ESSR and IPEX, it is a **protocol
primitive** both features compose, not an exchange-internal mechanism. Lifting it kills the feature-on-feature
dependency (shared-documents would otherwise depend on exchange for its content keying). It **composes ESSR**
(the 1:1 seal — [`vdti-area-essr.md`](vdti-area-essr.md)); its consumers are the exchange and shared-documents
features.

**Layering:** ESSR (1:1 seal) → **group-key** (fan-out + epochs + ratchet) → {exchange, shared-documents}
features → apps. **Credentials never touches it** (credentials composes IPEX only, staying transport-agnostic).

**Invariants:** [inv 14] witnessing prevents content forks (the epoch SEL is its own witnessed chain), [inv 8]
multi-source freshness (a member reads the current epoch), [inv 10] value-bearing lookup fails-closed, [inv 16]
addressing by prefix + gated membership, [inv 19] signatures are over the fully-compacted SAID (the consumer's
per-message signatures). Composes: ESSR (§Distribution); the SEL primitive (the roster + key-epoch logs).

## What it is

A **ratcheting shared symmetric epoch key** over a **bounded member set**, distributed by **ESSR-wrapping the
epoch key once to each current member**. The primitive exposes one thing: **the current epoch key, unwrappable
by each current member** — nothing about *what* the consumer encrypts with it. Each epoch key is **freshly
generated (independent random), never derived from a prior epoch**, and the primitive **ratchets** it to a new
epoch on either trigger, whichever comes first: a **membership change** or a **time cadence**.

The blast radius on ESSR is exactly this: **ESSR is invoked once per member, only to wrap the epoch key.** A
consumer's bulk data (chat messages, document content) is **never** sealed with ESSR — it is encrypted under
the epoch key (or a subkey of it), by the consumer.

## The pieces

- **The member roster — a bounded, enumerable, gated/blinded SEL.** The epoch key must be wrapped to each
  current member, so the primitive must **enumerate** them — unlike the shared-documents access-list, which is
  deliberately unbounded and never materialized. So the roster is a **bounded, enumerable** set (capped like
  `MAXIMUM_ROSTER_SIZE`), **gated / blinded**: member prefixes ride **read-gated opaque SAIDs** — enumerable by
  members (a member materializes the wrap-set), **blind to witnesses** (who see only opaque anchors, never the
  membership graph). This applies the shared-documents read-gating discipline to a bounded enumerable set, so the
  bounded roster does **not** surrender participant-blindness ([inv 16]). Membership changes are governed at
  **T2** (the group creator's `Gnt` ← `Ath`, or a group policy), so a signing-key theft (T1) cannot add or
  remove a member, and a removed member cannot re-admit itself. **Members are person identities (IELs)**; each
  member's receive key is owned by that member's **own** identity IEL (the exchange feature's `{Icp, Gnt}`
  value-bearing lookup SEL), so the group **never controls a member's key** — a member establishes and rotates it
  self-service. Because a member is a **person**, the epoch key wraps **once per member** (never per device).
- **The key-epoch SEL** — a single-owner SEL advancing **one fresh independent symmetric key per epoch**. Each
  epoch SEL event references the per-member wrapped-key SADs for that epoch; a member unwraps its own with its
  receive-key private key. Because each epoch key is independent, a compromise of one epoch key exposes **only
  that epoch**, nothing forward.
- **Distribution = ESSR, once per member.** The epoch key is the **ESSR payload**; the primitive calls ESSR N
  times (once per current member), producing one wrapped-key SAD per member. The **epoch's authenticity is the
  T2-governed key-epoch SEL event** (a member trusts an epoch by validating that event and finding its own wrap
  committed by it); the ESSR **signature** on each wrap is uniform with the rest of the system but not
  load-bearing for that. The baseline wrap is therefore **full ESSR**; a lighter **KEM+AEAD-only** seal — ESSR's
  confidentiality core _without_ the signature, so **not ESSR proper** — is an available optimization, settled
  at the encode.
- **The wraps are member-delivered, never published.** Each ESSR wrap carries its `recipient` in cleartext (for
  routing + anti-KCI), so the wrap-set would **enumerate the members** to anyone holding it. The wrap **bodies**
  are therefore delivered member-to-member and **never served to the store / witnesses** — the same never-publish
  discipline [inv 16] imposes on a private credential body or a data-bearing `Icp` — so the key-epoch SEL event
  leaks only the **count** of wraps (the roster size, already bounded), never _who_. The cleartext `recipient` is
  seen only by the receiving member and the transport (the §5 delivery-metadata residual), not by chain
  verifiers. **This is what keeps the member set blind to witnesses** — the gated roster alone does not, since
  the wraps would otherwise re-expose it.
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
    symmetric-key leak; a compromise of a member's **receive (KEM) key** unwraps every epoch wrapped to it during
    its membership — that is what removal defends, and only forward.)
- **Epoch-based, not a per-message double-ratchet.** A fresh **independent** key per epoch, distributed by
  wrapping — in the spirit of MLS's epochs, but **not** a derived key schedule (nothing unrolls forward from a
  compromise). Fits the group case; not Signal's pairwise per-message ratchet.
- **The epoch key never rides any channel raw** — always ESSR-wrapped on the key-epoch SEL.
- **Checkpoints (bounded verification).** A long-lived session at ~6–12h accrues **thousands** of seal-advancing
  epoch events on one SEL, bounded by no existing cap, so a cold verifier would walk the whole history. The
  primitive **re-incepts a fresh key-epoch SEL every K epochs** (chained to its predecessor), so a cold verifier
  walks a bounded suffix. (The checkpoint cadence K is a parameter — settled at the encode.)

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
- **A member's receive key** — the member's own identity IEL (the exchange feature's published-receive-key
  lookup); the group never owns it.
- **The 1:1 degenerate case, offline catch-up across missed epochs** — consumer / feature concerns.

## Divergence / sources

Lifted from the exchange session-mode design (`vdti-area-exchange.md` §7a, Jason 2026-07-14 / 15) — the
member-owned key, once-per-member wrap, gated/blinded roster, fresh-independent-per-epoch key, and the
membership + time-cadence ratchet are all from there; this note promotes them from an exchange-internal
mechanism to the shared primitive both exchange and shared-documents compose. MLS-epoch in spirit (fresh key per
epoch distributed by wrapping), **not** a derived key schedule.

## Drift → land

- Write `docs/design/primitives/protocols/group-key.md` fresh from this note (greenfield voice), alongside
  `protocols/{essr,ipex}.md`.
- **Trim `vdti-area-exchange.md` §7a** to the **chat-consumer** usage (per-sender lanes, bulk AEAD, per-message
  signatures, epoch-window currency), pointing the roster / key-epoch / wrap / ratchet here (the primitive owns
  them now). **Update `vdti-area-shared-documents.md` §7 / §9** to compose this primitive for content keying.
  **Update the ESSR note's boundary** ("group keying … the exchange feature" → "group keying is a primitive both
  exchange and shared-documents compose").
- **Reserved names** (register in `kinds.md` / `tags-and-topics.md` at the encode; component **`groupkey`** —
  settleable): the **key-epoch SEL topic** and the **gated-roster SEL topic**; the **grant-value kind** for the
  ESSR-wrapped epoch key (was `vdti/sel/v1/grants/exchange-group-key`); the KDF context for the per-writer subkey;
  the constants `SESSION_RATCHET_INTERVAL` and the checkpoint cadence `K`.
