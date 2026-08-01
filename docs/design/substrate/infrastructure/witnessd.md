# witnessd — the witness

`witnessd` is the witness: a **verify-then-sign service**. It receives a payload, **verifies it via
the store interfaces**, gates it, signs the SAID, and **persists what it signed**. It runs **no mesh
and no sync** — routing, bootstrap, anti-entropy, send-side partitioning, and freshness gathering
are [`gossipd`](gossipd.md)'s; parking is the server compositions'
([`../../compositions/log-server.md`](../../compositions/log-server.md)) — and it is **never
public**: only co-located services reach it, over local infrastructure. The witnessing **rules** are
the federation's ([`../federation/witnessing.md`](../federation/witnessing.md)); this doc states the
daemon that runs them.

The principle, stated once: **the stores expose raw state with no auth gates, and every service
verifies before acting — everything in the system is a verifier.** `witnessd` re-derives whatever
the kind in front of it needs, from state it reads itself.

## The witness identity and key custody

The witness's signing keys — the keys that mint receipts and freshness statements — live in
`witnessd`, backed by an HSM. This is the reason the daemon boundary exists where it does: the store
daemons front the public API and carry the larger attack surface, so **a compromised store daemon
must not be able to mint receipts** — signing capability is custodied behind a service that is
**never public**, reached only over local infrastructure through its kind-gated signing endpoint
([`architecture.md` §Transport](architecture.md#transport)). Key rotation follows the federation
ceremony — a witness rotation **is** a federation `Wit`, and superseded private key material is
wiped on rotation and removal
([`../federation/witnessing.md` §The federation clock](../federation/witnessing.md#the-federation-clock)).

## The signing path — five gates

Witnessing an event is eight steps carrying **five gates**, and every gate is `witnessd`'s own —
none is delegated to the service that delivered the payload:

> verify via the store interfaces → **re-derive selection** → **block check** on the authoring
> prefix → **acceptance-time currency gate** → **first-seen check** at this position, tier-scoped →
> **kind-gate** → sign → persist.

- **Verification is the core's, against state read directly.** Structural validity is checked
  through the core against the chain state the node's stores hold — a witness signs nothing it has
  not verified, and the stores expose raw state, so there is nothing between the witness and the
  bytes it judges.
- **Selection is re-derived.** A witness acts for each `(prefix, serial)` **it is selected for**,
  computing `select(prefix, serial, roster, signers)` over the roster it reads itself
  ([`../federation/witnessing.md` §Deterministic selection](../federation/witnessing.md#deterministic-selection)).
  Routing lives in `gossipd`, and a reduced witness that signed whatever routing handed it would be
  consuming another server's answer — the trusted backend RPC this architecture bans — letting a
  compromised `gossipd` induce receipts at positions the node was never selected for. Re-deriving is
  what makes that compromise mesh impersonation only.
- **The block check runs before every signing.** A selected witness **declines to witness an event
  authored by a blocked prefix** — the federation's per-prefix block toggle
  ([`../federation/blocking.md` §The witness check](../federation/blocking.md#the-witness-check)).
  The check must be cheap, so `witnessd` holds the block state as an **on-demand, per-author cache**
  — a memoized constant-time lookup keyed on the authoring prefix, materialized from the derived
  block SEL and refreshed over Redis pub-sub — never enumerating the full set (the derived addresses
  are non-listable), only deriving the one address for the author in front of it.
- **The acceptance-time currency gate.** A witness **refuses to witness an event whose
  `federationPin`'s roster membership is not current**
  ([`../federation/witnessing.md` §As-of-context evaluation](../federation/witnessing.md#as-of-context-evaluation-and-the-currency-gate)).
  It compares roster **membership** — an add or a cut fires it; a pure rotation does not — and it is
  establishment-time: it never voids receipts already established, and the stale-in-flight event
  canon deliberately accommodates still lands.
- **First-seen, per tier, per position — including the seal-cap mirror.** For each
  `(prefix, serial)` it is selected for, it signs the **first** structurally-valid **content**
  sibling and the **first** structurally-valid **sealed** sibling, and declines every later one —
  including the seal-cap mirror (a below-seal sealed event is declined, the backdate defense). These
  are declines of events that **pass** verification; first-seen is the foundation of
  one-sealing-per-position, where a second sealed receipt is collusion proof. The tier scoping is
  load-bearing: one content sibling _and_ one sealed sibling per position is what makes the
  split-stall exit's cross-tier co-sign legal.
- **The kind-gate** dispatches what may be signed at all — receipts and freshness on the internal
  path, the mesh handshake on the local endpoint below — then the signature is minted under the HSM
  key and the act is **persisted**.

## The signing record

`witnessd` keeps its **own** first-seen record — one row per `(prefix, position, tier)` carrying
`{ eventSaid, signature }`, written inside the per-prefix lock at the moment it signs, **never
deleted**, unwritable by any other service, and read **signature-verified** against `witnessd`'s own
key. The first-seen check reads **this record**, declining only a **different** `eventSaid` — so a
compromised sync path can neither suppress the record (making the witness double-sign by clock) nor
plant one (making it decline the legitimate event forever), a re-submitted identical event never
stalls a position, and the spent vote outlives any staged copy of the event body.

Ownership follows the same line: `witnessd` **write-owns the witnessing scope** — receipts in the
chain store, freshness statements on the expiring side, and this signing record, which no other
service may write at all. Ownership is of **schema and migrations, never exclusivity**: `gossipd` is
a runtime writer of receipts, and so is client submission through the receipt admission gate — which
is exactly why the first-seen check reads `witnessd`'s own record instead of the receipt rows
([`../../compositions/log-server.md` §Migration ownership](../../compositions/log-server.md#migration-ownership--one-owner-several-writers)).

## Receipts

Its receipt SAD carries the as-of-position selection context and its asserted time `τ` inside the
signed payload ([the witness receipt](../federation/witnessing.md#the-witness-receipt)). What
happens to a receipt after minting is not this daemon's: receipts flood roster-wide once an event is
witnessed in full, a still-gathering event sub-gossips among its selected witnesses
([`gossipd.md`](gossipd.md)), and the position-indexed receipt read — **the beacon** — is a named
`LogServer` query served by [`logsd`](logsd.md) on the public face and `gossipd` on the mesh
([`logsd.md` §The chain read](logsd.md#the-chain-read--keep-all-data-serve-the-accepted)).

## Freshness-statement signing

`witnessd` signs the freshness statements the consumer-side multi-source bar consumes
([`architecture.md` §The freshness statement](architecture.md#the-freshness-statement));
**gathering** them from peers is `gossipd`'s
([`gossipd.md` §Freshness gathering](gossipd.md#freshness-gathering)).

- **On demand, it attests its node's held effective-SAID** for a set of prefixes, with `τ` (and a
  consumer nonce, in the live variant) inside the signed payload, under the HSM key. It caches its
  own signed statement per prefix and re-signs only when its held value moves or the statement ages
  out of its serving window (an operational knob; the consumer's own staleness threshold governs
  acceptance regardless) — so its signing rate is bounded by demanded-prefixes per window, never by
  decision volume.
- **The attested value is re-derived under a verification token**, the effective-SAID reuse gate and
  `resume` discipline
  ([`../../protocol-doctrine.md` §Caching and continuation](../../protocol-doctrine.md#caching-and-continuation))
  — never a bare recompute from held rows. The bare recompute is vacuous: a compromised sync path
  that flips a prefix's held state would have the recompute return the tampered answer, and
  freshness is the one signature class that feeds a consumer's trust decision. The token makes the
  signing **tamper-evident for injected or rewritten state** — a tampered body moves the tip SAID,
  which moves the effective-SAID, which trips the gate and forces the re-walk, and the re-walk fails
  on the forged signature.
- **The claim does not cover rollback, and canon does not need it to.** A writer that **truncates**
  a prefix to an earlier, genuinely-valid position moves the effective-SAID, trips the gate, and the
  re-walk **succeeds** — a valid prefix of a valid chain is a valid chain — so the statement asserts
  a stale tip as current. That is indistinguishable from a lagging node, and it is absorbed where
  lag already is: the storage surface is **availability and staleness**, converted to refusal by the
  consumer-side **multi-source bar**, with propagation lag in the standing eclipse/staleness
  residual ([`architecture.md`](architecture.md#adversarial-framing)).

## The local sign endpoint — a kind-gate

`gossipd` needs the node's identity on the mesh handshake, and `witnessd` holds the key. The
`gossipd`-facing endpoint is a **kind-gate**: sign iff the `kind` is the handshake kind
(`vdti/gossip/v1/protocols/handshake` — [`mesh-transport.md`](mesh-transport.md)), refuse all else.
Kind is committed in the SAID, so a compromised `gossipd` cannot dress a receipt as a handshake —
the custody boundary holds **by construction**. The call is **per-connection, local, and
low-frequency** — the one named exception to "no backend RPC," which bans per-event cross-service
_data_ RPC, not a per-connection local sign. `gossipd` → `witnessd` is authenticated by **local
infrastructure** (socket permissions, a deploy secret, a service account), not a chain identity —
co-located processes in one trust boundary. Receipt and freshness signing stays a **separate
internal path** `gossipd` never reaches.

## Adversarial framing

- **A compromised `logsd` mints nothing.** Receipts and freshness statements are signed here, under
  HSM custody, against state `witnessd` verifies through the core before signing — the daemon split
  is precisely this containment.
- **A compromised `gossipd` is mesh impersonation only** — bounded, revocable by rotating the node
  key — never witnessing forgery: the kind-gate answers only the handshake kind, and selection is
  re-derived here, so induced routing mints nothing.
- **A compromised `witnessd` is a compromised witness** — the priced case, not a new one: its
  double-signs are cryptographic proof that names it for eviction, forgery beyond its own signature
  requires the colluding quorum the fork-cost prices, and its withholding is bounded by every other
  node's anti-entropy
  ([fork-cost](../../residuals.md#fork-cost--threshold-colluders-dropping-to-2threshold--signers-under-partition)).
- **`witnessd` is never publicly exposed** — an external attacker must first compromise a
  public-facing service, and even then the kind-gate contains them.

## Cross-references

- [`architecture.md`](architecture.md) — the decomposition, the freshness statement and consumer
  bar.
- [`gossipd.md`](gossipd.md) — the sync daemon: the mesh, the loops, and the signal path into this
  daemon.
- [`logsd.md`](logsd.md) — the chain-log daemon: the merge path, receipt storage, the beacon on the
  serving face.
- [`mesh-transport.md`](mesh-transport.md) — the handshake SAD this daemon signs through the
  kind-gate.
- [`../federation/witnessing.md`](../federation/witnessing.md) — the witness role's rules:
  selection, first-seen, receipts, the clock and key-windows, query-scoping.
- [`../../protocol-doctrine.md`](../../protocol-doctrine.md) — federation convergence, the
  effective-SAID comparison, the eventual-detection premise.
