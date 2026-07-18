# vdti — area note: the receive-key directory (identity → device receive keys)

**Status: FIRST CUT — lifted from `vdti-area-exchange.md` §2 into its own shared-core primitive (2026-07-18,
Jason).** An identity's published **receive keys** — the ML-KEM encapsulation keys a sender seals to — are
resolved through a value-bearing lookup SEL the identity's IEL owns. This directory is composed by **ESSR** (which
seals to a receive key), by **exchange** (mail + chat), by the **group-key** primitive (it wraps the epoch key to
each device's receive key), and by **shared-documents** — so, like ESSR and group-key, it is **shared-core**, not
exchange-internal. Lifting it lets the group-key primitive reuse the sealed-send machinery without re-coupling
shared-documents to the exchange feature.

**Layering:** the SEL primitive → **receive-key directory** (identity → device receive keys) → consumed by
{ESSR, exchange, group-key, shared-documents}. It is one leg of the **sealed-send core** (ESSR + this directory +
substrate transport) that "deliver sealed bytes to a device" composes.

**Invariants:** [inv 20] a device is a KEL in the identity's roster (never its own IEL); a receive-key compromise
is a confidentiality loss, never a control loss. [inv 2] single locus of control (the directory SEL is
single-owner — the identity IEL). [inv 10] a value-bearing lookup fails closed (a rescinded key reads dead →
senders fail closed). [inv 8] multi-source freshness (the lookup serves the live tip). Composes: the SEL
primitive (the lookup log); the IEL (the owner + its T2 authorization tier).

## What it is

The **directory of an identity's device receive keys** — a `{Icp, Gnt}` **value-bearing lookup SEL** the
identity's IEL owns, mapping each of the identity's devices to its published ML-KEM receive key. A sender resolves
`(identity, device) → receive key`; to reach the whole identity, it **enumerates the entries and fans out** (the
sealed-send core wraps to each — see the group case in [`vdti-area-group-key.md`](vdti-area-group-key.md)).

## The pieces

- **The address is deterministic (discoverable).** A receive key lives at `derive(owner, RECEIVE_KEY_TOPIC,
  data)` — `owner` = the identity IEL prefix, topic = `vdti/directory/v1/topics/receive-key`. A receive key is
  meant to be **found**, so it is **not** nonce-blinded; any sender holding the recipient's prefix computes it
  (the cost is the lookup-prefix residual). `lineage` (area-sel §1f) handles reincept after a forced-dead key.
- **`data` = a device KEL prefix _or_ an opaque alias — a flat set, one entry per device.** The publishing
  identity's IEL has a roster of member KELs (devices); setting `data` = a **member KEL prefix** yields a
  per-device receive key that discloses the device, setting `data` = an **opaque alias** yields the same
  per-device key **without** disclosing which device. Either way the entry is one device's key — there is **no
  default / identity-wide slot** (a single "the identity's key" would funnel every message through one device;
  senders reach all devices by enumerating the entries and fanning out). This is vdti's resolution of the kels
  "key-per-KEL vs key-per-identity" question (kels #137 / #140) — support both addressings of the same per-device
  key, selected by `data`.
  - **Alias-naming discipline (correlation warning — load-bearing for the operator).** `data` is **public** on
    the mesh. A **descriptive** alias (`basement-mac`, `personal-iphone`) leaks **which device to steal** to read
    a correspondent's mail. Aliases MUST be **opaque** (`primary`, `a`, a random label) so an observer can't map
    a key to a physical device. A framework warning; the app / wallet enforces the naming.
- **Fan-out enumerates the identity's IEL roster; opaque aliases are opt-in and point-to-point.** To reach
  **all** of an identity's devices, a sender enumerates the identity's **IEL roster** (its member KEL prefixes —
  its devices) and derives each device's receive-key address `derive(owner, RECEIVE_KEY_TOPIC,
  device_kel_prefix)`, so a device published under its **KEL prefix** is automatically fanned-out-to. A device
  published under an **opaque alias** is **not** roster-derivable (the alias is unguessable by design), so it is
  reachable only by a sender given the alias **out-of-band** — a **point-to-point** address, not part of the
  default fan-out. That is the deliberate trade: an alias buys device-privacy at the cost of automatic
  discoverability; a consumer targets such a key by supplying its label (the exchange feature's **`key_label`**,
  which becomes the lookup `data`). The roster a sender enumerates is the one a verifier **already walks** — the
  membership roster maintained during verification and carried on the verification token — so fan-out needs no
  extra lookup. (An identity's **own device roster** is resolvable by a correspondent this way; a **group's**
  membership graph stays participant-blind — a different thing.)
- **The published value is a T2 sealed `Gnt`, hardware-resident.** The `Icp` establishes the lookup; a **`Gnt`**
  (area-sel §1b — T2 `t_authorize`, anchored by the owner IEL's `Ath`) seals the key. `manifest.grant` names a
  grant-value SAD of kind **`vdti/sel/v1/grants/directory-ml-kem-1024`** (the public ML-KEM-1024 encapsulation
  key; the reduced-tier sibling is `directory-ml-kem-768`). The private half is an **enclave-resident,
  non-extractable ML-KEM key — always in hardware, no software path** (a ships-once system on the scale horizon;
  a software fallback would be a permanent downgrade surface). A **signing-key theft (T1) cannot swap it** —
  publishing needs `t_authorize`@T2; the key is never T1 content. (Contrast kels, which signed its key
  publication with the ordinary T1 signing key, so a signing-key theft swapped the key and read the victim's
  mail.)
  - `t_authorize` here is the identity's own authorization tier (the generalized `Gnt` / `Ath` applies to any
    identity's value establishment). Single-device → the reserve at T2; multi-device → its `t_authorize` quorum.
  - **Attestation is optional, and a policy-layer concern.** A published key is just bytes — vdti cannot _force_
    hardware. The grant value MAY carry a hardware **attestation** (`{ format, statement }` — Android key
    attestation / Apple SE / TPM certify), a vendor-signed statement binding the public key to a non-extractable
    private key in genuine hardware. A **counterparty that needs the guarantee** (a group, a relying party) opts
    into requiring it — "admit only attested keys." This is a **policy knob at the edge, never in the
    substrate**: requiring attestation reintroduces a fixed vendor root, which a rootless system keeps confined
    to whoever chooses to demand it. Prefer **non-interactive** attestation (a self-contained cert chain) so any
    verifier checks offline. The grant SAD's `said` binds the key and its attestation together — neither can be
    swapped without breaking the SAID (and the `Gnt` is T2-governed + anchored).
- **Rotation = stack `Gnt`s** (the latest sealed key is live; the lookup serves only the live tip, so a retired
  key is never handed to a sender). Routine rotation is a **T2 act**. Removing a compromised device's key is the
  same T2 act; a T1 device cannot re-admit itself ([inv 20]).
- **Rescission = `Trm`** (area-sel §1b, T2) — terminal kill → the key reads **dead** → senders **fail closed**
  ([inv 10]). Loss-of-control only; recovery is republish at a fresh `lineage`. Routine key change is a rotation
  (stacked `Gnt`), never a rescind.

## The boundary — what is not the directory

- **The 1:1 seal** — ESSR (the directory hands a sender the recipient's receive key; ESSR seals to it).
- **Reaching all devices — the fan-out + the epoch-key wrap** — the sealed-send core + the group-key primitive.
- **Transport** — mail / mesh (substrate); the directory is a lookup, not a delivery channel.
- **Sender-key currency** (verifying the sender's signing key is current) — the exchange feature (§3).
- **A device's signing key** — the KEL / the identity's use-and-govern authority; the directory publishes only
  the receive (KEM) key.
- **The federation / witnesses** — witnesses have **no published receive key**; their mesh channel is an
  ephemeral, signature-authenticated handshake (`vdti-area-federation-witnessing.md` §1e), forward-secret. The
  directory is a person-identity mechanism; the federation does not participate.

## Divergence / sources

Lifted from the exchange session's receive-key publication (`vdti-area-exchange.md` §2, Jason 2026-07-12) — the
deterministic address, `data` = device-prefix-or-opaque-alias, the T2 `Gnt` (vdti divergence from kels' T1), the
correlation-warning naming discipline, and stack-`Gnt` rotation are all from there; this note promotes them from
an exchange-internal section to the shared-core directory that ESSR, exchange, group-key, and shared-documents
all read. A **device is a KEL with a directory entry — never a per-device / "degenerate" IEL** (that idea
predates the SEL `data` field; the federation case that once motivated it uses the ephemeral handshake instead —
`supplemental/degenerate-iel-idea.md`).

## Drift → land

- Write the design doc fresh from this note (greenfield voice) alongside the other primitives, and **pull
  `vdti-area-exchange.md` §2** into a pointer (exchange is a consumer).
- **Reserved names** (register in `kinds.md` / `tags-and-topics.md`; component **`directory`** — settleable):
  SEL topic `vdti/directory/v1/topics/receive-key`; grant-value kinds `vdti/sel/v1/grants/directory-ml-kem-1024`
  and `directory-ml-kem-768` (moved from `exchange-ml-kem-*`); the `RECEIVE_KEY_TOPIC` derivation tag. The
  attestation shape (`{ format, statement }`) settles at the encode.
- Update the consumers' boundaries to name this directory: the **ESSR note** (key resolution), the **group-key
  note** (per-device wrapping reads it), **exchange §2 / §7a**, **shared-documents**.
