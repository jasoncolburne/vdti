# Service architecture — one verification core, four daemons

The deployable shape of the system: a **verification core** every party links, and thin daemons over
it — **`logsd`**, the chain-log daemon ([`logsd.md`](logsd.md)); **`sadd`**, the SAD store daemon
([`sadd.md`](sadd.md)); **`witnessd`**, the witness ([`witnessd.md`](witnessd.md)); and
**`gossipd`**, the sync daemon ([`gossipd.md`](gossipd.md)). This doc states the decomposition and
the boundary rules that make it sound: why the verifier is a library rather than a service, what the
core owns, how consumers reach the system, and how a consumer's trust decisions stay fresh without
trusting any single node.

**The federation exists to verify chains and to witness — nothing else.** It holds only what a
verification walk must resolve: chain events, manifests and role SADs, grant values, receipts and
freshness statements. Application data lives **off the federation**, on stores anyone can deploy
([`../../primitives/data/sad/rooting.md`](../../primitives/data/sad/rooting.md)). The store daemons
are **general infrastructure**: an application developer runs their own `sadd` /
[`blobsd`](blobsd.md) / `gossipd` and owns its admission policy, durability, and spam bounds. **Only
`witnessd` is federation-only**, because it is the witnessing apparatus; `gossipd` is a federation
service that is not federation-_only_ — an application fleet runs the same daemon over the same peer
model, with different stores wired.

The framing rule for everything here is
[end-verifiability](../../system-thesis.md#end-verifiability): trust attaches to the **data** —
signed, anchored, witnessed — never to a service, a database, or a channel. The daemons are
plumbing; every correctness rule lives in the core and runs wherever the data is consumed.

## The decomposition

```mermaid
flowchart TD
  subgraph consumer["a consumer (client · app server · wallet)"]
    capp["application"]:::app
    clib["<b>lib/vdti</b> — the verification core"]:::lib
    tks["token store"]:::lib
  end
  subgraph node["a federation node"]
    logsd["<b>logsd</b><br/>chain log"]:::svc
    sadd["<b>sadd</b><br/>SAD store, deletes off"]:::svc
    witnessd["<b>witnessd</b><br/>witness · HSM · never public"]:::svc
    gossipd["<b>gossipd</b><br/>the sync daemon"]:::svc
    infra[("shared infra<br/>Postgres · object store · Redis · HSM")]:::peer
  end
  capp --> clib
  clib --> tks
  consumer -->|"HTTP — the home-node relationship"| logsd
  consumer -->|HTTP| sadd
  logsd --- infra
  sadd --- infra
  witnessd --- infra
  gossipd --- infra
  gossipd <-->|"encrypted mesh"| peers["peer nodes"]:::peer
  classDef app fill:#2b1a3d,stroke:#9c36b5,color:#fff
  classDef lib fill:#1a2547,stroke:#4263eb,color:#fff
  classDef svc fill:#12331c,stroke:#2f9e44,color:#fff
  classDef peer fill:#20263a,stroke:#868e96,color:#e9ecef
```

- **`lib/vdti`** — the verification core: the chain verifiers and their tokens, merge, the transfer
  engine, effective-SAID computation, the deferred-dependency types, SAD custody and compaction, and
  policy evaluation — layered as store → server → client → source/sink
  ([`../../primitives/stores/log-store.md`](../../primitives/stores/log-store.md),
  [`../../compositions/log-server.md`](../../compositions/log-server.md)). **All correctness lives
  here.** Every daemon links it — and so does **every consumer**, which is the load-bearing point
  (below).
- **A federation node = `logsd` + `sadd` (deletes off) + `witnessd` (HSM, never public) +
  `gossipd`**, co-deployed over shared infra, addressable `logs.` / `sad.` / `witness.<node>`. A
  deployable is a thin composition of servers plus a wire adapter — the same code runs in-process
  where an application embeds it.
- **Off-federation storage** is the same `sadd` with **deletes on**, plus `blobsd` — separate,
  end-verifying consumers of the federation: no witnessing apparatus, no HSM, no witness role
  ([`sadd.md`](sadd.md), [`blobsd.md`](blobsd.md)).
- **Clients** — build and verify locally with the core, compact before submitting, and maintain the
  consumer-side **token store** (below).

## The core is a library because consumers must verify

End-verifiability means a consumer **cannot trust a store daemon** — a hostile or compromised daemon
can serve anything, so the consumer re-verifies every chain and SAD itself, with the **same
verifier** the daemon runs. That forces the boundary: the verifier is a **library both the daemons
and every consumer link**, never service-internal logic.

Two properties make the boundary hold:

- **The token is the proof.** The only way to consume chain data is through a verification token
  (`KelVerification` / `IelVerification` / `SelVerification`), constructable only by the verifier —
  so verification and access happen in one pass, and nothing downstream can skip the walk
  ([verification tokens](../../protocol-doctrine.md#verification-tokens-as-proof-of-verification)).
- **The database is never trusted.** A daemon re-verifies what it reads before consuming it, under
  the same advisory lock it writes with
  ([merge verification](../../protocol-doctrine.md#merge-verification-and-advisory-locking)). The
  daemon's store is a cache of the world, not an authority over it.

The daemons are therefore **thin**: `logsd` and `sadd` are routing, storage, and locking around the
core's merge and serve compositions; `witnessd` is key custody and signing around the core's
verification; `gossipd` is transport and scheduling around the core's transfer engine. A bug class
that lives in a daemon is an availability bug; the correctness surface is the core.

## The transfer engine — the one sanctioned data-mover

Every cross-process movement of chain events runs through the core's **transfer engine**: one paged
walk with swappable **source**, **sink**, and **verifier** — verify-into-a-sink, forward without
verifying (the receiver verifies), or stream through a callback. Merge intake, anti-entropy sync,
deferred-dependency replay, and client-side verification all reuse it.

The rule is strict because the engine is where tamper-evidence is enforced in motion: it pages in
generation-aligned units (a divergent generation spanning a page boundary re-fetches rather than
being processed half-observed) and it partitions a divergent run into sub-batches a receiving merge
handler accepts ([`gossipd.md` §Send-side partitioning](gossipd.md#send-side-partitioning)).
Hand-rolled pagination bypasses those guarantees — no other data-mover is permitted.

## The cascading store — one interface, composed in sequence

The store traits themselves — `LogStore`, `SadStore`, `BlobStore`, and the server / client /
source-sink stack over them — are the storage primitives'
([`../../primitives/stores/log-store.md`](../../primitives/stores/log-store.md),
[`../../primitives/stores/sad-store.md`](../../primitives/stores/sad-store.md),
[`../../primitives/stores/blob-store.md`](../../primitives/stores/blob-store.md)). What this doc
keeps is the composition doctrine: a consumer instantiates a store over a **sequence** of
implementations, searched in order — memory, then filesystem, then one or more remotes — so caching
tiers and fallback stores compose with no new machinery: the **cascading store**. Content addressing
is what makes the cascade sound — any store returns the same bytes for a SAID or digest, so the
sequence changes **where** an answer comes from and what it costs, never what it means. Stores
legitimately differ in what they _hold_: a read-gated record lives only where its gates admit, and
some data stays local-only — a miss at one tier falls through to the next, and the serve rules hold
at whichever store answers. A remote tier is a store daemon's API surfaced as a trait implementation
— `get` and gated-`exists`, no enumeration
([`../../primitives/stores/sad-store.md`](../../primitives/stores/sad-store.md)).

**Write placement rides the same sequence, within what each tier admits.** A SAD carries no
placement field: the client chooses which of **its own** tiers a write lands on — local disk, a
private store, a service's replicated roster — and what the federation holds is fixed by the
verification-necessary test, never by client choice: application data has no federation tier to
choose ([`../../primitives/data/sad/rooting.md`](../../primitives/data/sad/rooting.md)). Placement
is application and deployment policy, never a field in the bytes
([`../../primitives/data/sad/availability.md` §What availability declares](../../primitives/data/sad/availability.md#what-availability-declares)).

## Features are libraries — there are no feature daemons

Credentials, exchange, and shared documents are **libraries over the core and the store daemons'
APIs**, never daemon modules and never daemons of their own. **An application composes its storage
at the client**: mail, chat, drive, a PDS all live in the client, fanning writes and reads across
the generic `logsd` / `sadd` / `blobsd` stores, with no backend link between them and no per-app
store daemon — the only services are the generic stores, and they all look the same. The scope of
the rule is **storage**: anything that genuinely wants a server — a search index, a matchmaking
service, an app-curated feed — is an **application** deploying its own app-layer service on top,
outside this architecture.

## Dependencies

Stated as plain dependencies — deployment topology (which services share an instance, what runs
where) is an operational choice, not part of the design:

- **`logsd` / `sadd`** depend on **PostgreSQL** (the chain log and receipt rows), an **S3-compatible
  object store** for SAD bytes (the reference deployment uses SeaweedFS), and **Redis**.
- **`witnessd`** depends on Postgres and Redis and an **HSM** — the witness signing keys
  ([`witnessd.md` §Key custody](witnessd.md#the-witness-identity-and-key-custody)).
- **`gossipd`** depends on Redis and the stores it syncs.

Redis is the coordination layer **between processes** — cache, pub-sub (the post-merge notification
the drain listens on), and the shared ephemeral state: the park map, the stale set, rate counters,
token bundles, freshness statements, the unseen-nonce cache, and the staged (pre-promote) side.
Data-plane durable state lives only in PostgreSQL and the object store (key material is custodied in
the HSM); merge serialization rides PostgreSQL advisory locks, so replicas over one database
serialize correctly with no extra machinery.

**The federation never deletes stored data, and the rule is enforced beneath the services.** A
service that _could_ delete but chooses not to buys nothing against a compromised service, which is
the threat. So: each service connects as its **own Postgres role, and no role holds `DELETE` or
`TRUNCATE`** on the durable tables — grants, not triggers (a trigger is droppable by whoever can
drop it, and Postgres has no append-only table flag). The object store's policy denies the delete
action, with object-lock as the stronger option that survives credential theft. **The scope is the
federation's**: "no delete, ever" is the federation's grant, and an off-federation `sadd` / `blobsd`
runs deletes — the capability split
([`../../primitives/stores/sad-store.md`](../../primitives/stores/sad-store.md)). What is durable
and what stages is the three-promote-reasons boundary
([`../../compositions/log-server.md` §Durability](../../compositions/log-server.md#durability--the-three-promote-reasons)).

**Three single-writer roles, kept distinct** — conflating them is the easy failure:

- the **migration owner** — per data scope, a **separate role** used only during expand/contract
  ([`../../compositions/log-server.md` §Migration ownership](../../compositions/log-server.md#migration-ownership--one-owner-several-writers));
- the **store write-owner** — per scope, and **not** exclusive at runtime: a scope has several
  runtime writers, serialized by the per-prefix advisory lock and content-addressed idempotency;
- the **stamper** — per **store**, the single writer of the commit-ordered listing ordinal
  ([`../../primitives/stores/log-store.md` §`list(since)`](../../primitives/stores/log-store.md#listsince--the-enumeration-ordered-by-commit)).
  It sits off the admission path and is not the migration owner, and it does **not** make the store
  single-writer for admissions.

**A restore takes the services entirely down first — then restore, then up.** A bounded outage
rather than a running service against a mid-restore store: restoring under a live service tier is
already wrong for ordinary reasons (stale pools, caches newer than the store, killed in-flight
transactions), and the ordering keeps the in-memory head check — the stamper's process-scoped
high-water reference — a backstop and hygiene rather than a load-bearing detector
([`gossipd.md`](gossipd.md)).

### Operational surfaces

Two node-local signals, both **ops surfaces, never protocol queries** — each makes no verifiability
claim and lives in the transient carve-out beside the park map and rate counters:

- **The burial leaderboard.** The merge layer already computes `Buried`, so a **per-prefix counter
  increments where the burial is decided** — no scan, no second detection path — held in Redis,
  **windowed**, surfaced as a sorted top-N by **recent** burials. Recency is the signal: honest
  burials trickle (a genuine content race resolved by a burying seal), abuse runs at up to
  `MAXIMUM_UNSEALED_RUN` per rotation — roughly two orders of magnitude apart. The lever is
  **blocking** ([`../federation/blocking.md`](../federation/blocking.md)), not monitoring.
- **The structural-validity alarm.** A durable row that fails canon's byte-pure structural-validity
  set is **impossible via the protocol** — every durable event write is a merge-layer promote and
  every durable receipt passes the admission gate, both of which validate — so its presence means
  **direct database access**: tampering, corruption, or a bad migration. It is a statement about
  **this node**, so it **pages an operator** rather than joining the leaderboard's sort-and-block
  loop. The predicate is **well-formedness only** — the locked-portion bound is not in it and must
  never page anyone (a below-current-seal parent is the ordinary condition of every historical row).
  The walk already computes this and the change is to count and alarm instead of silently skipping.

## Transport

- **Node-to-node (the mesh)** — the authenticated, encrypted channel of
  [`mesh-transport.md`](mesh-transport.md), carrying the gossip topics
  ([`../federation/topics.md`](../federation/topics.md)), terminated by `gossipd`.
- **Consumer-to-node is HTTP.** Reads use a **safe, body-carrying query method**, because a prefix
  in a request line or query string leaks into ordinary access and proxy logs
  ([negative checks](../../protocol-doctrine.md#negative-checks-are-positive-lookups)); mutations
  use POST.
- **There is no trusted backend data RPC.** A server never consumes another server's **answer** —
  the daemons couple only through the shared stores, each programming against the store trait
  ([`../../compositions/log-server.md`](../../compositions/log-server.md)). A server may fetch data
  it **end-verifies itself** — an off-federation store's federation query is a consumer read, not
  backend RPC.
- **`witnessd` is never public.** Its protection is **never-public + local infrastructure + the
  kind-gate on its signing endpoint** — not host separation: signing capability is custodied behind
  a service no public face reaches, whatever hosts the deployment uses
  ([`witnessd.md`](witnessd.md)).

## The consumer topology — the home node

A consumer does not roam the federation. It has a **home node** — one node it calls for everything:
chain pages, SADs, effective-SAIDs, freshness evidence. The same relationship the submit path
already runs (a user submits to a **preferred witness**, which routes on their behalf —
[`gossipd.md` §On-receiving-node routing](gossipd.md#on-receiving-node-routing)) extends to the
consume side.

The home node is a **mirror**: everything flows through it, and **nothing is trusted from it**.
Chain data end-verifies; SADs re-derive their SAIDs; receipts carry witness signatures the consumer
checks itself. A lying home node can **withhold** — which degrades to refusal or staleness, below —
but it can forge nothing.

One claim a mirror cannot self-serve is **freshness**: "no newer events exist" is not in the data a
node hands over, and a single node can withhold a newer revocation, rotation, or fork branch
indefinitely. That claim is exactly what the freshness statement carries.

## The token store — cached verification, gated reuse

A consumer caches verification tokens keyed by prefix and reuses them instead of re-walking, under
the doctrine's reuse rules
([caching and continuation](../../protocol-doctrine.md#caching-and-continuation)). The store
enforces three gates:

- **The transitive effective-SAID gate.** A cached token is reusable only when the effective-SAID of
  **every** chain it transitively leans on still matches — the KELs beneath an IEL, the IEL beneath
  a SEL, every delegator above it, and the federation that witnesses it. A lower-layer recovery can
  break an upper event while the upper chain's own value never moves; only the transitive check
  catches it. Any moved value → fetch `since` the held position and `resume` — incremental rather
  than from-scratch (a cursor the source cannot resolve, such as a fork or dispute synthetic, falls
  back to a full, re-verified re-walk —
  [caching and continuation](../../protocol-doctrine.md#caching-and-continuation)) — with the to-tip
  negative checks — revocation, rescission, divergence — re-run against the new tip.
- **The wall-clock overlay, recomputed at decision time.** The effective-SAID gate certifies
  **structure** (nothing moved ⇒ the walk stands); it does not certify **freshness**. Staleness is
  time-triggered — a witness key-window lapses with zero chain events — so the store caches
  **freshest-valid witnessing times** (data), never a fresh/stale verdict, and every loss-of-trust
  decision recomputes staleness against current wall-clock time regardless of whether anything
  moved.
- **The multi-source bar.** A **loss-of-trust decision** — is this chain forked or disputed, is this
  credential revoked, is this delegation rescinded, is this tip still current — must confirm each
  transitively-pinned chain's effective-SAID **multi-source**
  ([token reuse is transitive](../../protocol-doctrine.md#verification-tokens-as-proof-of-verification)).
  A decision that cannot meet the bar **refuses** — it never proceeds on a flag. The bar is met with
  freshness statements, below.

## The freshness statement

A **freshness statement** is a witness-signed attestation of held state: _"my held effective-SAID
for each of these prefixes is this value, as of this time."_ It is how the multi-source bar is met
through a single untrusted pipe — the independent views a loss-of-trust decision needs are **signed
data relayed by the home node**, not connections the consumer must hold open.

It is a SAD, on the same discipline as the witness receipt
([`../federation/witnessing.md` §The witness receipt](../federation/witnessing.md#the-witness-receipt)):
the witness signature rides **adjacent, never in the body**, and the timestamp sits **inside** the
signed payload so a harvested statement cannot be re-stamped fresh. Its body:

```
{
  said,           // the statement's own SAID
  kind,           // vdti/witness/v1/states/freshness
  statements,     // [{ prefix, effectiveSaid }, …] — the attested pairs, strictly ascending
                  //   by prefix, capped at MAXIMUM_MANIFEST_LIST entries (the shared list bound)
  timestamp,      // the witness's asserted time τ (inside the signed payload)
  nonce,          // optional — a consumer-supplied challenge (the live variant, below)
  witnessPrefix   // the signing witness's KEL prefix
}
```

For a chain with no single confirmed tip, `effectiveSaid` **is the verdict-tagged synthetic**
(`forked` / `disputed` —
[effective-SAID comparison](../../protocol-doctrine.md#effective-said-comparison)) — a statement can
therefore deliver "this chain is disputed" as signed evidence, and any non-single-tip value grounds
refusal directly.

**Who signs, and how a statement verifies.** Any **current federation-roster member** may sign — a
witnessed event propagates roster-wide (receipts and announcements flood; bodies follow —
[`topics.md`](../federation/topics.md)), so every member's held state is equally informative; no
per-position selection applies. A consumer counts a statement when all of the following hold,
checked with machinery it already runs for receipts:

- the signature verifies against the member's **witnessed** KEL signing key, and `τ` falls inside
  that key's window;
- the signer is in the current roster of a federation the consumer trusts (the config-pinned set),
  read from the federation IEL the consumer verifies anyway;
- `τ` is at most `now + CLOCK_TOLERANCE_BAND`, and no older than the consumer's **staleness
  threshold** for this decision.

**The bar.** A prefix's freshness is confirmed when **federation-`threshold`-many distinct current
members** agree on the same value — the `threshold` of the **federation's own witness-config**, in
effect at the consumer's verified federation tip. That is the quantity the standing byzantine
assumption is stated in ("fewer than `threshold` byzantine members" — the federation's receipting
threshold, not its governance quorum), and the signers are drawn from the whole roster, so the bar
must clear the roster-level tolerance: with byzantine members below it, any bar-meeting agreeing set
includes an honest one. What one honest signer guarantees is an honest **view as of `τ`** — an
honest member can itself lag propagation and truthfully attest a value it has not yet seen
superseded — so the bar defeats **fabrication**; propagation lag stays inside the standing
eventual-detection residual. A consumer may demand more for a high-value decision; it never accepts
fewer. A statement naming a **different** value than the consumer holds is not a failure — it is the
anti-entropy signal: fetch, verify, re-evaluate.

**Amortization.** Statements are demand-driven and cache-shaped: a witness re-signs a prefix only
when its held value moves or its cached statement ages out of its serving window (an operational
knob sized to typical consumer staleness thresholds — the consumer's own threshold governs
acceptance regardless), the home node gathers federation-`threshold`-many over its existing mesh
sessions and re-serves the bundle to every consumer behind it, and the multi-prefix `statements`
list covers a decision's whole transitive dependency set in one signature per witness — per
federation: a chain clears the bar of the federation that witnesses it, so a set spanning
federations gathers from each. Nothing floods — statements move by request and cache, unlike
receipts. The staleness threshold is the cost dial: tighter freshness buys proportionally more
signing.

**The live variant.** A consumer that cannot trust its own clock — or wants replay bounded to a
single exchange rather than a staleness window — supplies a **`nonce`**, and the statement is signed
fresh with the nonce inside the payload (the challenge-response path
[`../federation/witnessing.md`](../federation/witnessing.md) names for the no-local-clock case). The
live variant defeats caching by construction, so it is the high-assurance opt-in, never the default.

**Relationship to the beacon and to monitoring.** The receipt query at a position (the beacon)
enumerates a position's admitted competing branches to nodes; the freshness statement is how a
**node's resulting held view exits the federation to a consumer** with its provenance intact. The
owner-side twin is [`monitoring.md`](../../monitoring.md) — the same effective-SAID compared against
the owner's own expectation rather than a peer's.

## Adversarial framing

- **A hostile home node can only starve, never feed.** Every byte it serves end-verifies; freshness
  statements are signed by keys it does not hold. Withholding chain data is denial; withholding
  statements makes the bar unmeetable → the decision **refuses** (fail-secure). Serving stale
  statements fails the consumer's staleness check; serving a stale _value_ under fresh signatures
  requires the signing members themselves to lie — the next point.
- **Forging agreement costs the federation itself.** Fabricating "still current" for a chain that
  moved requires **federation-`threshold`-many** distinct current-member signatures — exactly the
  federation's own byzantine bar, so any bar-meeting agreeing set contains an honest signer and a
  stale-value set cannot be assembled below the federation-compromise class (the same arithmetic
  closes the withhold-honest-while-supplying-byzantine channel: the byzantine members alone can
  never reach the bar). It is the system's irreducible residual, and **detectable after the fact**:
  the signed statements are durable evidence contradicting the chain.
- **The federation chain's own freshness rides the same bar.** A cut-out quorum attesting a stale
  roster as current is bounded by the key-window auto-expiry (`MAXIMUM_WITNESS_KEY_WINDOW`) and
  broken by a single honest member's statement (disagreement → fetch). Sustaining the illusion is a
  full eclipse plus a byzantine quorum — the standing
  [eclipse residual](../../residuals.md#3-eclipse-and-freshness), degraded to refusal past the
  window.
- **Replaying a statement is bounded by its `τ`.** The timestamp is inside the signed payload, so a
  harvested statement ages out at the staleness threshold; the nonce variant closes replay entirely
  for the decisions that warrant it. A backward-drifting consumer clock re-opens the window — the
  standing NTP deployment invariant
  ([`residuals.md`](../../residuals.md#consumer-clock-drifts-backward)).
- **The library boundary is the trust boundary.** No daemon-side check is load-bearing for a
  consumer: a compromised store daemon yields wrong availability, wrong caching, wrong routing —
  never a wrong verified answer downstream, because the consumer's own linked core re-derives every
  answer that matters.

## Cross-references

- [`logsd.md`](logsd.md) / [`sadd.md`](sadd.md) / [`blobsd.md`](blobsd.md) /
  [`witnessd.md`](witnessd.md) / [`gossipd.md`](gossipd.md) — the daemons.
- [`../../primitives/stores/log-store.md`](../../primitives/stores/log-store.md) — the store traits;
  [`../../compositions/log-server.md`](../../compositions/log-server.md) — the composed layer.
- [`mesh-transport.md`](mesh-transport.md) — the authenticated, encrypted node-to-node channel.
- [`../../protocol-doctrine.md`](../../protocol-doctrine.md) — operation categories, verification
  tokens, caching and continuation, effective-SAID comparison.
- [`../federation/witnessing.md`](../federation/witnessing.md) — receipts, the witnessing floor, the
  clock and key-windows, query-scoping.
- [`../../monitoring.md`](../../monitoring.md) — the owner-side effective-SAID watcher.
- [`../../residuals.md`](../../residuals.md) — eclipse and freshness residuals; cross-cutting
  assumptions.
