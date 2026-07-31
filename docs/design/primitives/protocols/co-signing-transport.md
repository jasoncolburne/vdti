# The co-signing transport — how a quorum's devices reach each other

Thresholds above one require **multi-device co-signing**: the authority slots carry a hard security
floor of `≥ 2` for every identity with `|roster| ≥ 2` — no single member exercises authority — so
any identity with a phone and a laptop needs its devices to co-sign **every** governance act (key
rotation, evicting a compromised device, revocation, federation rebind, the terminal `Trm`), and
**step-up** ([`t_live`](../data/event-logs/iel/events.md#the-threshold-vector-and-its-bounds)) is a
declared capability nobody can exercise without a way for devices to co-sign. This doc states that
transport: its security properties are the substance; the medium is deliberately unconstrained.

## The construction — the mesh handshake, with one substitution

- **An ephemeral post-quantum KEM per session** — forward secrecy, nothing stored, no key-management
  service.
- **The handshake is a SAD committing its per-session transcript** (the ephemeral KEM material plus
  a nonce), signed over its SAID. This is what makes a captured handshake non-replayable.
- **Each side authenticates the peer's device KEL**, and both must resolve into the **same
  identity's IEL roster**. Free — an IEL is a threshold over member KELs, so the roster walk names
  both devices. (Resolving a peer into the roster is **identification, not an exercise of
  authority** — which is why the session stays reachable on a `Forked` chain, where recovery needs
  it — [`iel/verification.md`](../data/event-logs/iel/verification.md#derived-accessors).)
- **The handshake SAD is transient** — never stored, never served by SAID.
- **Transport is out of band and unconstrained.** A QR exchange, a local link, anything carrying the
  bytes.

The KEM is named by its structural property — a post-quantum KEM — never by product.

## What the session is for

The co-signature itself does not need a confidential channel: it is a signature over a SAID,
verifiable against the co-signing device's KEL, and a substituted SAID produces a signature over the
wrong SAID, which fails at quorum assembly. What the session buys:

- **Anti-relay binding — the load-bearing property.** Without it, a remote attacker induces a device
  to sign out of band.
- **Replay resistance** — the nonce the transcript commits.
- **Transcript confidentiality** — minor; a private object's SAID is unguessable by its nonce, but
  observing it confirms the object exists.

## The co-signing device verifies independently

**The co-signing device resolves and verifies what it signs, and displays it.** Required by the
system's own tenet — everything is a verifier — and without it step-up buys nothing against the
threat it exists for: a compromised device driving a rubber-stamp second device. Fan-out past two
devices is N pairwise sessions — no new construction.

## There is no asynchronous path, and that is the point

**All required devices are physically in hand.** The session exists so the user is not transcribing
a nonce from one screen to another — that is its whole job. It is not a way to reach a device that
is somewhere else. So **nothing is deposited**: no co-signing-request kind, no shape, no admission
floor, no discovery index, no cleanup.

This is what makes step-up's assurance claim precise: **step-up's strength is requiring physical
possession of `t_live` devices at one moment** — not multi-party approval over time. An asynchronous
path would spend exactly the property step-up exists to buy. The medium is irrelevant to the
security — local link, QR, or over the network, the session is KEL-authenticated and forward-secret
either way; proximity buys the assurance claim, it is not what protects the channel.

## Considered — encapsulating to the published receive key

The [receive-key directory](receive-key-directory.md) already publishes a hardware-held,
non-extractable KEM public key per device, so a session could encapsulate straight to it with no
handshake. Rejected as the whole answer: that key is **long-lived**, so a captured transcript
decrypts later if the device is seized. Fine as a bootstrap for the first message, with an ephemeral
key taking over.

## Primitive vs tooling

The **primitive** is the transport's security properties, so independent wallets interoperate and
anti-relay is guaranteed rather than vendor-discretionary: mutual device-KEL authentication, the
ephemeral KEM, the transcript-committing handshake SAD, replay resistance, independent verification,
and display-what-you-sign. The **tooling** is orchestration and interface — who prompts whom,
presentation, batching, retry — the same line the federation's block console draws
([`../../substrate/federation/blocking.md` §Operator posture](../../substrate/federation/blocking.md#operator-posture)).

## Cross-references

- [`../data/event-logs/iel/events.md`](../data/event-logs/iel/events.md) — the threshold vector, its
  floors, and `t_live` (the step-up bar).
- [`../data/event-logs/iel/verification.md`](../data/event-logs/iel/verification.md) — the
  divergence freeze, and why roster resolution succeeds on a forked chain.
- [`receive-key-directory.md`](receive-key-directory.md) — the published KEM keys this transport
  deliberately does not rest on.
- [`../../substrate/infrastructure/mesh-transport.md`](../../substrate/infrastructure/mesh-transport.md)
  — the mesh handshake this construction adapts.
