# witnessd — the witness, gossip, and sync daemon

`witnessd` is the federation-facing daemon: it holds the node's **witness identity and signing
keys**, terminates the encrypted mesh, runs the witness role — first-seen signing, receipts,
sub-gossip, routing — parks events that arrive ahead of their cross-chain dependencies, and drives
the anti-entropy loops that repair silent divergence between nodes. The witnessing **rules** are the
federation's ([`../federation/witnessing.md`](../federation/witnessing.md)); this doc states the
daemon that runs them, and the sync machinery it owns.

"Gossip" names the **pattern** — the epidemic propagation layer riding the mesh transport
([`mesh-transport.md`](mesh-transport.md), [`../federation/topics.md`](../federation/topics.md));
`witnessd` is the service that speaks it.

## The witness identity and key custody

The witness's signing keys — the keys that mint receipts and freshness statements — live in
`witnessd`, backed by an HSM. This is the reason the daemon boundary exists where it does: `vdtid`
fronts the public API and carries the larger attack surface, so **a compromised `vdtid` must not be
able to mint receipts** — attestation capability is custodied one service away, and the two daemons
are separable onto distinct hosts ([`architecture.md` §Transport](architecture.md#transport)). Key
rotation follows the federation ceremony — a witness rotation **is** a federation `Wit`, and
superseded private key material is wiped on rotation and removal
([`../federation/witnessing.md` §The federation clock](../federation/witnessing.md#the-federation-clock)).

## The witness role

What `witnessd` runs, per the federation doctrine:

- **First-seen signing, per tier, per position.** For each `(prefix, serial)` it is selected for, it
  signs the first structurally-valid content sibling and the first structurally-valid sealed
  sibling, and declines every later one — including the seal-cap mirror (a below-seal sealed event
  is declined, the backdate defense). Structural validity is checked through the core against the
  chain state held in `vdtid`; a witness signs nothing it has not verified.
- **Receipts.** Its receipt SAD carries the as-of-position selection context and its asserted time
  `τ` inside the signed payload
  ([the witness receipt](../federation/witnessing.md#the-witness-receipt)). Receipts flood
  roster-wide once an event is witnessed in full; a still-gathering event sub-gossips only among its
  selected witnesses.
- **The beacon.** Receipts are keyed at `(prefix, serial)`, so the position-indexed receipt query
  enumerates every witnessed branch at a position — the detection signal a `disputed` read rests on.
  `witnessd` answers it from the receipt rows `vdtid` stores.

## On-receiving-node routing

A user submits to their **preferred witness** — usually not one selected for the position, which is
fine:

- The receiving node computes the selection locally — `select(prefix, serial, roster, signers)` over
  the roster it holds — and routes the event body, **targeted**, to the selected witnesses.
- The selected witnesses verify, sign, and sub-gossip the body among themselves; their **receipts
  flood** the roster. The body never floods — it moves targeted, and other nodes pull it on demand
  when its content is wanted.
- The preferred witness answers "witnessed yet?" **from receipts alone** — counting `threshold`-many
  receipts agreeing on `(event SAID, threshold)`. The receipt-carried threshold is a **fast-path
  hint only**: on pull, the count is honored only on an exact match against the chain-committed
  witness-config in effect at the position — a mismatched receipt is invalid even if it names a
  higher bar
  ([witnessed-in-full is a receipt count](../federation/witnessing.md#query-scoping-and-the-audit-flag)).

## Freshness-statement service

`witnessd` signs and gathers the freshness statements the consumer-side multi-source bar consumes
([`architecture.md` §The freshness statement](architecture.md#the-freshness-statement)):

- **Signing.** On demand, it attests its node's held effective-SAID for a set of prefixes — read
  from `vdtid`, computed by the core — with `τ` (and a consumer nonce, in the live variant) inside
  the signed payload, under the HSM key. It caches its own signed statement per prefix and re-serves
  it until the held value moves or the statement ages past the staleness window — so its signing
  rate is bounded by demanded-prefixes per window, never by decision volume.
- **Gathering.** As a consumer's home node, it collects statements from peer witnesses over the
  standing mesh sessions — enough distinct current members to clear the consumer's bar — and hands
  the bundle to `vdtid` to serve and cache. The statements end-verify, so gathering and relaying are
  untrusted plumbing; a peer's refusal or silence just shrinks the bundle, and an under-bar bundle
  makes the consumer refuse.

## Deferred-dependency parking and drain

When `vdtid` answers a submission with the typed deferred-dependencies response
([`vdtid.md`](vdtid.md#deferred-dependencies--the-typed-response)), `witnessd` **parks** the batch
and **drains** it when its dependencies land:

- **The park map** lives in Redis: a primary record per parked message, plus secondary indexes by
  awaited SAID and by awaited chain, each entry carrying the dependency chain's effective-SAID at
  park time. Writes go **secondaries before primary**, and the primary self-expires — so a crash
  orphans only a self-expiring primary, never dangling indexes.
- **Drain triggers.** A parked batch replays when an awaited SAID commits (the post-merge
  notification), or when an awaited chain's effective-SAID **moves past its parked value** — the
  chain changed, so the dependency may now be satisfiable. Replay runs through the transfer engine
  into the ordinary merge path; a replay that defers again re-parks against the new value.
- **Loss is tolerated by design.** The park map is reconstructible state: a lost park re-arrives by
  gossip or anti-entropy, so expiry bounds are safety-free — parking is a latency optimization on
  convergence the sync loops guarantee anyway.

## Anti-entropy

Gossip delivers what nodes push; **anti-entropy repairs what push missed** — the periodic loops that
find and close silent divergence between this node's held state and its peers'. The **effective-SAID
is the compare key** throughout
([the anti-entropy trigger](../../protocol-doctrine.md#effective-said-comparison)): two nodes
holding the same state compute the same value, so any difference — including a
real-SAID-versus-synthetic difference — marks a prefix to sync.

- **Phase one — targeted.** Prefixes known stale (a failed forward, a park that aged out, a peer
  mismatch observed in passing) sit in a Redis stale set; the loop queries peers' effective-SAIDs
  for them and syncs from any peer whose value differs.
- **Phase two — random sampling.** A random page of local prefixes against a random peer, skipped
  when phase one had work — the backstop that finds staleness nothing flagged.

**Enumeration is by the peer's own update sequence.** A syncing node pages a peer's prefix listing
ordered by the peer's **local, monotone update sequence** — bumped whenever a prefix's held state
changes, whatever the age of the arriving event — descending from the head down to a per-peer
**watermark**, comparing each listed prefix's effective-SAID against its own; the watermark then
advances to the scan-start sequence (anything moving mid-scan re-sorts above it and is caught next
round). Delivery order is the one sound ordering for this listing: ordering by any **data** time — a
witnessed timestamp — misses a late-gossiped old event permanently (its data-time sorts below the
watermark even though the peer's held state just changed). The listing endpoint is part of the
node-to-node surface, so conforming implementations expose the same shape.

**The fetch is `since` the querier's own last seal.** On a mismatch, the syncing node pulls
everything after its **own** last seal and dedupes by SAID. Bounded divergence makes this complete
above the seal: a fork can only form after the last seal, so the window captures the canonical tip
and every live competing branch, and the response includes the cursor's own siblings (so a node
learns if the seal it anchors on is itself forked). A settled, buried branch does not move the value
and is not chased — it is forensic, reached by the flat by-prefix fetch. When a value mismatch
persists and `since` cannot close it (the escalation backstop — chiefly a cross-implementation
synthetic-encoding drift, which the pinned encoding exists to prevent), the node escalates to a
**flat by-prefix fetch**, so the loop converges rather than spins.

## Send-side partitioning

Propagating a divergent chain is a **sender-side** responsibility: a receiving merge handler routes
batches by content, so a single batch mixing pre-divergence events with a competing branch would be
part-rejected. The transfer engine partitions a divergent run into sub-batches the receiver accepts
in order — the shared history first (dedupes harmlessly), then each competing branch so every
event's parent precedes it, a burying seal-advancer last like any seal-advancer. The atomic fork
unit — both competing branches plus the burying seal — fits one page by construction
(`MINIMUM_PAGE_SIZE` covers two capped runs plus the seal —
[forks are seal-bounded](../../protocol-doctrine.md#forks-are-seal-bounded)); a rarer wider fork's
extra branches ride later pages.

## Adversarial framing

- **A compromised `vdtid` mints nothing.** Receipts and freshness statements are signed here, under
  HSM custody, against state `witnessd` verifies through the core before signing — the daemon split
  is precisely this containment.
- **A compromised `witnessd` is a compromised witness** — the priced case, not a new one: its
  double-signs are cryptographic proof that names it for eviction, forgery beyond its own signature
  requires the colluding quorum the fork-cost prices, and its withholding is bounded by every other
  node's anti-entropy
  ([fork-cost](../../residuals.md#fork-cost--threshold-colluders-dropping-to-2threshold--signers-under-partition)).
- **Parking is not a trust surface.** A parked batch replays through the full merge path — parking
  defers verification, it never substitutes for it; poisoning the park map costs latency, not
  correctness, and the map's loss-tolerance means its Redis is never load-bearing for safety.
- **Anti-entropy is fail-secure under partition.** Nodes holding different state never falsely agree
  — the compare key differs, driving a fetch where the peer is reachable and reading as distrust
  where it is not. The one thing the loops cannot deliver is a branch no reachable peer holds — the
  standing eclipse residual, surfaced by the beacon when it heals
  ([`residuals.md`](../../residuals.md#3-eclipse-and-freshness)).

## Cross-references

- [`architecture.md`](architecture.md) — the decomposition, the transfer engine, the freshness
  statement and consumer bar.
- [`vdtid.md`](vdtid.md) — the storage daemon: the merge path this daemon feeds, the typed
  deferred-dependencies response, receipt storage.
- [`mesh-transport.md`](mesh-transport.md) — the authenticated, encrypted channel every mesh link
  runs over.
- [`../federation/topics.md`](../federation/topics.md) — the gossip channels and the two-scope
  transport.
- [`../federation/witnessing.md`](../federation/witnessing.md) — the witness role's rules:
  selection, first-seen, receipts, the clock and key-windows, query-scoping.
- [`../../protocol-doctrine.md`](../../protocol-doctrine.md) — federation convergence, the
  effective-SAID comparison, the eventual-detection premise.
