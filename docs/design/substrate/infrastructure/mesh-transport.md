# Mesh transport — the authenticated, encrypted witness channel

The federation's nodes exchange receipts and events over the gossip mesh —
[`../federation/topics.md`](../federation/topics.md) catalogues the channels, and
[`../federation/witnessing.md`](../federation/witnessing.md) states the guarantees that rest on
propagation. This doc specs the **wire underneath**: the point-to-point channel every mesh link runs
over — how two nodes authenticate each other, agree a key, and encrypt every frame so that reuse of
a key or a nonce is not a discipline an implementer must remember but a property of the channel's
structure.

The transport carries **confidentiality only**. Trust is never delegated to it: a verifier trusts
the data — signed, anchored, and witnessed — not the channel it arrived on
([`../../protocol-doctrine.md`](../../protocol-doctrine.md)). Encryption keeps mesh contents within
the roster; it never decides what is true.

## One crypto suite — vdti's own primitives

The mesh is not a bespoke cryptographic stack. It is **vdti's crypto suite applied to the
transport** — the same algorithm choices the rest of the system runs on:

- **ML-KEM** — key establishment (the handshake's shared secret).
- **ML-DSA** — authentication (each side signs the handshake).
- **AES-256-GCM** — frame encryption.
- **blake3** — key derivation from the shared secret.

The mesh runs the **infrastructure tier** (ML-KEM-1024, ML-DSA-87 — the infrastructure parameter),
matching [`../federation/topics.md`](../federation/topics.md)'s statement that all inter-node
traffic is ML-KEM-1024 + AES-256-GCM. This is the same suite and the same tier-as-a-parameter shape
ESSR ([`../../primitives/protocols/essr.md`](../../primitives/protocols/essr.md)) uses for
end-to-end messages; the transport reuses the choices rather than inventing new ones.

## The channel — one session per connection

A mesh link is an authenticated, encrypted session established once per connection:

- **Authenticate.** The two nodes exchange identity prefixes and run an ML-KEM key exchange — the
  initiator offers a **fresh, per-connection** encapsulation key, the responder encapsulates to it —
  yielding a shared secret. Each side then signs the handshake transcript with ML-DSA, and each
  **verifies the peer's signature against that peer's witnessed identity**. A node whose signing key
  does not match its current witnessed key state is refused: authentication is mutual and bound to
  the witnessed chain, not to a self-asserted key. Because the encapsulation key is **ephemeral** —
  generated for the connection, never a published or persistent key — the channel has **forward
  secrecy**: a later compromise of a node's signing key cannot decrypt a past session, whose key
  material is already gone.
- **Derive.** From the shared secret, blake3 derives **two** AES-256-GCM keys — one per direction —
  under a domain-separated context — `vdti/gossip/v1/protocols/kdf` — on the `vdti/gossip/v1/*`
  convention. The two directions never share a key.
- **Scope.** The keys last the connection's lifetime. Nothing rides the mesh in the clear.

## Nonce discipline — reuse is structural, not a convention

Each direction advances a **monotonic 64-bit counter**, rendered into the 96-bit AES-GCM nonce and
incremented once per frame. Because the two directions use **different keys**, and each key sees a
**strictly increasing** counter, a `(key, nonce)` pair can never recur. AES-256-GCM's one
load-bearing rule — never reuse a nonce under a key — therefore holds **by construction**, not by an
implementer following a rule.

This is the same shape ESSR relies on: there, a fresh per-message key makes a random nonce safe;
here, a per-connection key with a per-direction counter makes the nonce safe. Either way the unsafe
state is unreachable, so "get the nonce wrong" is not an operator or author risk — it is ruled out
by the transport code that owns the counters.

## Rekey — a fresh handshake per connection

Keys and counters are scoped to a single connection. A dropped or re-dialed link runs a new
handshake and starts fresh keys and counters from zero. There is no mid-session rekey and none is
needed: a connection never exhausts a 64-bit per-direction counter within its lifetime, its per-key
data volume stays orders of magnitude below AES-256-GCM's confidentiality margin, and any transient
fault triggers a reconnect that refreshes the material anyway. **There is no persistent mesh key to
rotate** — a node's only long-lived key on the mesh is its **signing** key, and rotating that simply
forces reconnection: the next handshake authenticates under the new witnessed key, so identity-key
rotation reaches the transport without a special path.

## What rides above — the epidemic protocol

The logic layered on top of this channel — which peers a node keeps in view, how a witnessed event
floods to the roster, how a node that has only _heard about_ a message pulls the body — is an
**epidemic gossip protocol**: a partial-view membership layer over a broadcast-tree layer. It is
transport-agnostic and pinned to the reference implementation rather than to doctrine; its
parameters (view sizes, fan-out, timers) are build detail specified against the encoding library,
not design invariants. What the design fixes **here** is the security of the channel it runs over.

## Adversarial framing

- **Trust never rides the channel.** A peer that intercepts a link, or a compromised link itself,
  cannot forge an event — events are signed, anchored, and witnessed, and a verifier re-checks all
  three from the data. The transport's job is confidentiality: keeping receipts and event bodies
  inside the roster, not vouching for them.
- **Authentication is witnessed-key-bound.** A peer proves its identity by signing the transcript
  with a key the other side verifies against the **witnessed** KEL — so an impersonator lacking the
  current signing key is refused, and a captured-then-rotated key reads stale exactly as it does
  everywhere else. Signing the transcript (not merely a challenge) binds the identity to the
  session's own key material.
- **Nonce reuse is unreachable.** Per-direction keys and strictly-increasing counters make a
  `(key, nonce)` collision impossible within a session, and a session never outlives its counter
  space — so AES-256-GCM's confidentiality holds without an implementer having to keep a discipline.
- **The tier is not negotiated down.** Both endpoints are infrastructure nodes running the
  infrastructure parameter; the algorithm choice is fixed by their configuration, not offered in the
  clear for an attacker to steer toward a weaker option.

## Cross-references

- [`../federation/topics.md`](../federation/topics.md) — the gossip channels the mesh carries and
  the two-scope (roster-wide / selected-witness) transport this wire runs under.
- [`../federation/witnessing.md`](../federation/witnessing.md) — the witnessing guarantees that rest
  on propagation; the mesh is their delivery layer.
- [`../federation/bootstrap.md`](../federation/bootstrap.md) — genesis: the mesh forms once nodes
  set their federation prefix; before that, arrangement is point-to-point.
- [`../../primitives/data/sad/kinds.md`](../../primitives/data/sad/kinds.md#the-naming-convention) —
  the `vdti/gossip/v1/*` naming convention the mesh's derivation contexts follow.
