# gossipd — the sync daemon

`gossipd` is the sync daemon: it terminates the encrypted mesh and runs the epidemic propagation and
the sync loops — routing, bootstrap, anti-entropy, send-side partitioning, and freshness gathering —
over whatever stores a deployment wires. "Gossip" names the **pattern** — the epidemic propagation
layer riding the mesh transport ([`mesh-transport.md`](mesh-transport.md),
[`../federation/topics.md`](../federation/topics.md)); `gossipd` is the service that speaks it. It
is a federation service that is not federation-**only**: an application deployment — a mail
service's fleet — runs the same daemon over its own stores
([`../../example-applications/mail.md`](../../example-applications/mail.md)).

**The peer model is not a parameter.** It is **one IEL whose roster is KELs**, and a peer is a
current member device of that identity — the federation's roster is its witnesses' KELs, a mail
service's roster is its deployments' KELs. The handshake, the peer check, and the scoping all rest
on that shape; swapping in a delegation tree or a published server list is not configuration but a
second protocol wearing the same name, and it fails on what a roster gives for free: a delegation
tree cannot be enumerated to know who to pull from, and no single act cuts one member of it.

**What varies is which stores are wired**, and that is composition, not a semantic knob: a
federation node wires the chain and SAD stores; a mail deployment wires [`sadd`](sadd.md) +
[`blobsd`](blobsd.md) and has no chain store. **The loops follow from what is wired.** Anti-entropy
and routing need a store — any store. Send-side partitioning and freshness gathering are chain work
and do not exist without [`logsd`](logsd.md). Bootstrap in its federation form is a chain
cold-preload; a deployment's version is anti-entropy from empty. Query-scoping and selected-witness
sub-gossip are witnessing and do not exist without [`witnessd`](witnessd.md). A deployment builds
only the loops it wires, so an application `gossipd` binary does not contain the chain or witnessing
paths — containment by construction, the same argument as `witnessd` never being public.

**`gossipd` never holds a signing key.** The kind-gated local sign endpoint belongs to whatever
holds the deployment's device key — in the federation that is `witnessd`, because the key is in an
HSM that must never be reachable from a public face; a mail deployment has no HSM and no `witnessd`,
and its device key is held by the deployment itself. Either way `gossipd` asks for a handshake
signature and gets only that kind, so a `gossipd` compromise is mesh impersonation and never
anything the identity can sign for.

## Peer authentication — the roster check

Peer authentication is the same question in every deployment: **is this peer's KEL a current member
of the identity this deployment belongs to?** An IEL carries no key of its own, so a handshake is
signed by **one current member device** of the identity, and the peer's check is that this device's
KEL is currently in the roster ([`mesh-transport.md`](mesh-transport.md) — the channel;
[`../federation/witnessing.md`](../federation/witnessing.md) — the witnessed key state it checks
against). Removal is **one roster act**, surgical, and cannot be delegated away.

**The divergence freeze does not close the mesh.** Authenticating a party as a current member of a
roster is **not a live check on that identity's authority** — the freeze binds acts that consume the
identity's authority to act now, on a chain that is not Active, and this is a member device
authenticating a **sibling member of its own identity** against the frozen roster a **Forked** read
deliberately returns
([`../../primitives/data/event-logs/iel/verification.md`](../../primitives/data/event-logs/iel/verification.md#derived-accessors)).
The exclusion holds on Forked and **not** on **Disputed** — the roster read errors there (two or
more competing key-state rosters), so a disputed fleet cannot resolve peer membership at all, its
mesh closes, and its recovery is reincept — which mints a new prefix and invalidates every
`receivers` entry pointing at the old one.

## Mesh endpoints — the federation-peer surface

Federation peers reach a second serving surface, authenticated by the mesh session
([`mesh-transport.md`](mesh-transport.md)); `gossipd` terminates it and drives the loops that page
it, over the stores the node's [`logsd`](logsd.md) and [`sadd`](sadd.md) hold. It exists for
replication and sync, and its admission rule differs from the consumer surface: **custody travels
with an object and gates the consumer serve, not replication** — no node identity is ever a
`readers[]` entry, confidential content protects itself with its seal, and the read gate limits
store-side harvesting — so a peer is admitted by **mesh membership**, never by the consumer gates. A
federation replicates every admitted SAD across all its witnesses, so there is no per-object scope
to narrow the peer serve. There are **no blobs on the federation** — nothing deletion-bearing rides
this surface.

| Endpoint               | Method | Carries / returns                                                                                                                                                                                  |
| ---------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **chain listing**      | QUERY  | the node's own update-sequence enumeration of chain changes, paged descending from the caller's per-peer watermark — the anti-entropy and bootstrap enumeration                                    |
| **SAD listing**        | QUERY  | the update-sequence enumeration of held standalone-SAD SAIDs — the SAD-object pass's presence compare (the enumeration leaks the existence of custody-gated objects, priced only for mesh members) |
| **chain fetch (peer)** | QUERY  | the same paged chain read as the public surface, mesh-authenticated — query-scoping still serves a sub-threshold event only to a selected witness for its position                                 |
| **SAD fetch (peer)**   | QUERY  | a held standalone SAD for replication — admitted by mesh membership; deletion-bearing data lives off the federation and never reaches this surface                                                 |

**There is no existence probe on this surface either.** A peer asks what the other holds — the
listings above — and fetches what it lacks; it never asks whether one named object is held. That is
not a leak argument (a mesh member already reads the SAD listing, which exposes the same existence)
but a **redundancy** one: enumeration is the sync path, and the probe would answer a question the
listing has already answered ([`sad-store.md`](../../primitives/stores/sad-store.md)).

An off-federation deployment's mesh serves the same shape for the stores it wires — the SAD listing
and fetch, and a **blob listing and fetch** over the object index's commit-ordered ordinal
([`../../primitives/stores/blob-store.md`](../../primitives/stores/blob-store.md)) — with the same
membership admission read from its own roster.

## Landing peer data — through the same gates as everything else

What arrives over the mesh lands through the ordinary admission machinery, never around it:

- **Peer events land through the merge layer** — stage → promote, **never a raw durable append**
  ([`../../compositions/log-server.md` §The merge layer](../../compositions/log-server.md#the-merge-layer--every-durable-event-write)).
  Every durable event write is a merge-layer write; gossip arrival is an instance of the rule, not
  an exception to it.
- **Peer receipts land through the receipt admission gate**, under the per-prefix advisory lock
  ([`../../compositions/log-server.md` §The receipt admission gate](../../compositions/log-server.md#the-receipt-admission-gate)).
  `gossipd` is a runtime writer of receipts — **and so is client submission, through the same
  gate**: a trusted-federation provisioning submission pages a foreign federation's chains in as
  bundles that **carry their receipts**, since no local `witnessd` mints a foreign federation's
  receipts and no mesh reaches that federation
  ([`../federation/witnessing.md` §The trust grant chain](../federation/witnessing.md#the-trust-grant-chain--the-federation-boundary)).
  Ownership of the receipt store's schema and migrations stays `witnessd`'s — the owner-versus-
  writer distinction
  ([`../../compositions/log-server.md` §Migration ownership](../../compositions/log-server.md#migration-ownership--one-owner-several-writers)).
- **It signals `witnessd`** that a candidate needs witnessing via shared infrastructure — a durable
  marker plus Redis pub-sub / PostgreSQL `NOTIFY` — never an RPC, and it holds no HSM
  ([`architecture.md`](architecture.md)).
- **Parking lives in the server compositions, not here.** The park map and its drain discipline are
  [`log-server.md` §Deferred-dependency parking](../../compositions/log-server.md#deferred-dependency-parking)'s;
  `gossipd` holds only the **mesh-observed drain triggers** — an awaited SAID or chain observed
  landing by sync replays the park through the full merge path.

## On-receiving-node routing

A user submits to their **preferred witness** — usually not one selected for the position, which is
fine:

- The receiving node computes the selection locally — `select(prefix, serial, roster, signers)` over
  the roster it holds — and routes the event body, **targeted**, to the selected witnesses.
- The selected witnesses verify and sign (each re-deriving its own selection —
  [`witnessd.md`](witnessd.md#the-signing-path--five-gates)) and sub-gossip the body among
  themselves; their **receipts flood** the roster. The body never floods — it moves targeted to the
  selected witnesses, and every other node fetches it when the chain's flooded announcement shows a
  value it lacks ([`../federation/topics.md`](../federation/topics.md)).
- The preferred witness answers "witnessed yet?" **from receipts alone** — counting `threshold`-many
  receipts agreeing on `(event SAID, threshold)`. The receipt-carried threshold is a **fast-path
  hint only**: on pull, the count is honored only on an exact match against the chain-committed
  witness-config in effect at the position — a mismatched receipt is invalid even if it names a
  higher bar
  ([witnessed-in-full is a receipt count](../federation/witnessing.md#query-scoping-and-the-serve-flags)).

**Two scopes ride the mesh**
([`../federation/topics.md` §Two meshes](../federation/topics.md#two-meshes)): **roster-wide
announce + fetch** for witnessed-in-full events — receipts and effective-SAID announcements flood,
and a node fetches the bodies it lacks — and **selected-witness sub-gossip** for an event still
gathering receipts. `gossipd` enforces the **query-scoping on the wire**, where it already knows the
peer's identity (every mesh link authenticates the peer against its witnessed KEL), so "is this a
selected witness for the position?" is a federation-IEL lookup — never `logsd`'s problem on this
surface.

## Bootstrap — a node serves nothing until it is in sync

A fresh node joining the mesh runs a deliberate sequence, and **readiness gates serving** throughout
([`logsd.md` §Scaling](logsd.md#scaling)):

- **Establish identity first.** Two cases, split by whether the identity already exists:
  - **A fresh replica or re-joining node of an existing member** authenticates as that member — its
    identity is long witnessed, its admission long landed — and preloads immediately.
  - **A brand-new witness** has no witnessed identity before admission: its `Fcp`-rooted chain's
    consent act rides the admitting `Wit` itself (the federation ceremony —
    [`../federation/witnessing.md` §Roster governance](../federation/witnessing.md#roster-governance)),
    and the mesh **is** the roster, so pre-admission it can reach neither the encrypted channel nor
    the member-only listing. Its preload **begins after admission lands** — its first duty cycle is
    the cold enumeration — and operators MAY warm it beforehand by **operator-arranged
    point-to-point provisioning** (the same posture genesis has: before the mesh, arrangement is
    point-to-point — [`../federation/bootstrap.md`](../federation/bootstrap.md)). A just-admitted
    witness is selectable while still preloading; the receipt redundancy (`signers − threshold`
    slack) is what makes that safe.
- **Preload is the anti-entropy enumeration, run cold.** There is no separate bootstrap protocol: a
  fresh node pages each peer's update-sequence listing from an **empty watermark** — which is the
  whole listing — and fetches everything that differs, **re-verifying each object by the proof it
  carries** (§Anti-entropy), so a joining node trusts no peer's word for what it admits.
- **Retry as a unit until clean.** The preload passes (each chain type, then the SAD-object pass)
  repeat until none reports a sync failure — the poll-based backstop beneath park-and-drain, and
  load-bearing for "we cannot serve until we are in sync." Peers' own readiness is probed before
  dialing, so a starting cluster does not race ahead of peers still coming up.
- **Only then mark ready** — and only then join the standing gossip and anti-entropy duty cycle.

An **off-federation deployment's** bootstrap is the same loop with no chain pass: anti-entropy from
an empty watermark over the object stores it wires.

## Anti-entropy

Gossip delivers what nodes announce and fetch; **anti-entropy repairs what the announce-and-fetch
cycle missed** — the periodic loops that find and close silent divergence between this node's held
state and its peers'. It has two phases — enumeration, then compare — and the **compare phase is a
wired strategy, selected by store type**, not by deployment:

- **The chain store wires the effective-SAID compare** — a chain prefix has evolving per-prefix
  state two nodes can disagree about, so the compare key is the effective-SAID
  ([the anti-entropy trigger](../../protocol-doctrine.md#effective-said-comparison)) and the fetch
  is `since` the querier's own seal (below).
- **The SAD and blob stores wire `presence`** — an immutable content-addressed object has no state
  to diff: a peer either holds it or it does not, and the fetch is _every key past my watermark that
  I lack_. This is not a degraded variant; it is the rule for the store type, and the federation's
  own SAD-object pass runs it (below). The blob half pages the **object index**'s commit-ordered
  ordinal ([`../../primitives/stores/blob-store.md`](../../primitives/stores/blob-store.md)), so a
  replicated deposit's payload syncs beside its SAD.

Both deployments run both rules for the store types they have — a federation node has all three
stores; a mail deployment has `sadd` + `blobsd` and only ever needed presence. Nothing here is
configured by _who_ you are.

**The chain pass:**

- **Phase one — targeted.** Prefixes known stale (a failed forward, a park that aged out, a peer
  mismatch observed in passing) sit in a Redis stale set — each entry carrying the peer that
  surfaced the difference, retried **source-first** with backoff and a bounded retry count (an
  unreachable answer ages out; it does not spin the loop forever). The loop queries peers'
  effective-SAIDs for them and syncs from any peer whose value differs.
- **Phase two — random sampling.** A random page of local prefixes against a random peer, skipped
  when phase one had work — the backstop that finds staleness nothing flagged. (Off-federation the
  sample is per-object — the same weakening canon already took for the object class on the
  federation's own SAD pass; what is genuinely absent off-federation is the chain pass, and a
  deployment with no chain loses nothing by its absence.)
- **Pull-only, with bounded fan-out.** A node only ever pulls what it lacks: a sample showing the
  peer **behind** is not this node's work — the peer pulls on its own cycle — so anti-entropy never
  becomes push-repair or write amplification. Concurrent repair fetches are capped, so a large stale
  set drains at a bounded rate instead of storming the store.
- **Echo suppression.** A local commit triggers an announcement (the effective-SAID moved), but a
  commit whose events just **arrived by gossip** must not re-announce them — the sync path keeps a
  short-lived record of what it stored so the announcement trigger skips it, breaking the
  announce-fetch-store-announce feedback loop.
- **The fetch is `since` the querier's own last seal.** On a mismatch, the syncing node pulls
  everything after its **own** last seal and dedupes by SAID. Bounded divergence makes this complete
  above the seal: a fork can only form after the last seal, so the response carries the **full
  retained set after the cursor** — the canonical tip, every competing branch after it (live or
  since-settled) with its burying seal-advancer, and the cursor's own siblings (so a node learns if
  the seal it anchors on is itself forked) —
  [`logsd.md` §The chain read](logsd.md#the-chain-read--keep-all-data-serve-the-accepted). A branch
  settled below **both** parties' seals produces no value mismatch and is not chased — below-cursor
  evidence is forensic, reached by the flat by-prefix read. When a value mismatch persists and
  `since` cannot close it (the escalation backstop — chiefly a cross-implementation
  synthetic-encoding drift, which the byte-exact encoding discipline exists to prevent — pinned at
  the encoding library, forthcoming;
  [residuals §Owed work](../../residuals.md#11-owed-work-and-unverified-assumptions)), the node
  escalates to a **flat by-prefix fetch**, so the loop converges rather than spins.

**Enumeration is by the peer's own update sequence — for every store type.** A syncing node pages a
peer's listing ordered by the peer's **local, monotone update sequence** — bumped whenever held
state changes, whatever the age of the arriving data — descending from the head down to a per-peer
**watermark**; the watermark then advances to the scan-start sequence (anything moving mid-scan
re-sorts above it and is caught next round). Delivery order is the one sound ordering for this
listing: ordering by any **data** time — a witnessed timestamp — misses a late-gossiped old event
permanently. The listing is **mesh-scoped** — a member-only surface riding the encrypted channel,
never public (an enumeration is itself correlation-sensitive data). The listing's ordinal is
assigned in **commit order** by the store's single-writer stamper, and the store publishes
`(incarnation, resumePoint, head)` as state beside it
([`../../primitives/stores/log-store.md`](../../primitives/stores/log-store.md)); on an incarnation
it has not seen, a peer **lowers** its watermark — `watermark := min(watermark, resumePoint)` — and
records the new incarnation, so a restored peer's rewound listing is re-fetched instead of silently
skipped, and an ordinary restart is a no-op. A syncing node **persists fetched objects before
advancing its watermark** — at-least-once on the pull, so a crash re-fetches rather than skips.

**The SAD-object pass.** Standalone SADs sync by the keys an immutable, content-addressed object
admits: **enumeration** by the peer store's update-sequence listing of SAD SAIDs, **compare =
presence**, and a fetch that pulls **every SAD the peer holds that this node lacks** — a federation
replicates every submitted SAD across all its witnesses, so there is no per-object scope to honor;
custody rides with the object, unenforced on this path, because it gates the **consumer** serve, not
replication (§Mesh endpoints). **Rootedness re-verifies on arrival — every object re-checks the
proof it carries**, so an honest node never takes a write on the sending peer's word
([`../../primitives/data/sad/rooting.md` §Adversarial framing](../../primitives/data/sad/rooting.md#adversarial-framing)).
A **direct-event-rooted** SAD (a manifest role-SAD, an IEL `pins` SAD) carries no in-bytes locator
and never rides this pass at all — it **arrives with its chain**, riding its committing event's
bundle on the chain sync, the event co-present, re-verified **forward**, exactly as a `sad/field`
child rides its parent. On the pass itself: an **owner-anchored** SAD is genuinely standalone (it
carries `owner` + `pin`) and recomputes its blinded anchor from its own fields; a **`sad/field`**
child re-confirms against its **parent** — co-present by `root ⊇ child` and shipped in the same
bundle, read **forward**, never a stored back-pointer (a child whose parent has not landed parks on
the **SAD-object await** until it does). There is **no retention window and no "trust the admitting
node" fallback**: every class re-verifies from permanent state (a chain) or a co-present root, so an
old SAD a bootstrapping node pulls re-verifies exactly as a fresh one does. On the federation,
deletion-bearing data never reaches this pass at all: `once` objects and recipient-scoped deposits
are application data and live off the federation — a federation `sadd` refuses a submission
declaring `once` or `expiry` ([`availability.md`](../../primitives/data/sad/availability.md)).

**Off-federation, the split is by direction, not by class.** An application client knows the node
set — the service's IEL is published and its roster **is** the node set — so the class carve-out
that protects a federation client does not apply, and mail replicates:

- **Deposits ride anti-entropy** (peer ⇄ peer). That is how a deployment the sender did not reach
  gets the message.
- **Deletes fan from the client**, directly to every node in the service's roster — `acknowledge`
  means `delete` on each, idempotent, no tombstone, and no "who may assert a deletion" question at
  the mesh layer: each store runs the same predicate it would run for a direct request, which is the
  deploying application's
  ([`blobsd.md` §Deletion is the application's](blobsd.md#deletion-is-the-applications)).

**The two sets cannot drift apart** — peer admission and the delete fan read the **same roster**, so
there is no node that replication reaches and deletion does not. The residual is bounded and
self-correcting: a delete reaches one node and not another, the next pass copies the object back,
and the client deletes again on its next poll. **Snapshots, honestly:** a restore re-seeds objects,
not deletions — a deployment restored from a pre-drain snapshot verifies correctly and anti-entropy
copies the drained objects back to peers that had correctly removed them, so a restore re-seeds the
fleet with everything deleted since the snapshot, the client re-drains on its next polls, and the
exposure window is snapshot-age plus poll interval. And `once` burns **per store**, so a replicated
deployment bounds reads per node, never globally — it relies on the explicit delete
([`availability.md`](../../primitives/data/sad/availability.md)).

**The blob sync path's floor is a signature.** A blob `Sink` can only check `hash(payload) == S` — a
tautology about bytes the peer just named; the committing document is never persisted, so no
`D`-relative check and no rate limit can run on the receiving side, and rate limiting is the
load-bearing floor for this class. So **for blobs, the forwarding deployment signs what it forwards,
and the receiver verifies that signature and that the signer's KEL is a current member of the
service's roster** — then takes the attestation, the federation's own shape: a node accepts an event
on receipts rather than re-deriving the submitter's admission. A **SAD** is the opposite case —
self-verifying, its anchor checkable by the receiver — so an honest node re-checks it rather than
taking the peer's word; the one SAD class with nothing to re-check, an **unrooted** SAD
off-federation, rides the forwarder's signature the same way the blob does. **The attestation covers
admission only**: derived state a gate dispatches on — a mail deposit's recipient index, a chat
lane's verified group — is an **authorization input** the receiver **re-derives, never inherits**
(inheriting would hand one compromised roster member a fleet-wide re-scope of read authorization;
re-deriving is one envelope read for mail, one lane hop for chat —
[`../../compositions/sad-server.md`](../../compositions/sad-server.md)). The bound is **attribution
and evictability**, not verification: a compromised deployment that floods signs every object it
pushes, is identified by that signature, and is cut from the roster in one act — and until that
operator act, a `Sink`'s **per-peer rate cap** is what bounds the flood. Anti-entropy is a **pull**,
so the signature says nothing about the read direction: **every node in the roster reads everything
the fleet holds** — the honest blast radius, bounded by the public, one-act-cuttable roster
([`../../residuals.md`](../../residuals.md)).

## Send-side partitioning

Propagating a divergent chain is a **sender-side** responsibility: a receiving merge handler routes
batches by content, so a single batch mixing pre-divergence events with a competing branch would be
part-rejected. The transfer engine partitions a divergent run into sub-batches the receiver accepts
in order — the shared history first (dedupes harmlessly), then each competing branch so every
event's parent precedes it, a burying seal-advancer last like any seal-advancer. Every seal-to-seal
window fits one page by construction — `MINIMUM_PAGE_SIZE` is sized to the full transfer window, the
floor position plus two content-only runs plus two sealed branch runs with their seals, and the
two-per-rail ceiling means no window exceeds it
([forks are seal-bounded](../../protocol-doctrine.md#forks-are-seal-bounded)).

## Freshness gathering

`witnessd` signs freshness statements; `gossipd` **gathers** them. As a consumer's home node's sync
engine, it collects statements from peer witnesses over the standing mesh sessions — enough distinct
current members to clear the consumer's bar (the federation's witness-config `threshold`, by
default) — and hands the bundle to [`logsd`](logsd.md)'s serving face to serve and cache. The
statements end-verify, so gathering and relaying are untrusted plumbing; a peer's refusal or silence
just shrinks the bundle, and an under-bar bundle makes the consumer refuse
([`architecture.md` §The freshness statement](architecture.md#the-freshness-statement)).

## Adversarial framing

- **A `gossipd` compromise is mesh impersonation only** — bounded, revocable by rotating the node
  key — never witnessing forgery: it holds no signing key, and the kind-gated sign endpoint answers
  only the handshake kind ([`witnessd.md`](witnessd.md)). It writes peer events and receipts as a
  runtime writer, and everything it writes lands through the merge layer and the receipt admission
  gate, re-verified there.
- **Anti-entropy is fail-secure under partition.** Nodes holding different state never falsely agree
  — the compare differs, driving a fetch where the peer is reachable and reading as distrust where
  it is not. The one thing the loops cannot deliver is a branch no reachable peer holds — the
  standing eclipse residual, surfaced by the beacon when it heals
  ([`residuals.md`](../../residuals.md#3-eclipse-and-freshness)).
- **A flooding peer is attributable and evictable.** Off-federation, everything a peer pushes
  carries its signature; the per-peer rate cap bounds the flood until the roster act cuts it.
- **A stalled stamper is not self-announcing.** A head that stops moving looks identical to an idle
  store from the listing alone, so detecting the stall is the **operator's**: admissions arriving
  while the published head stands still is the observable — the store's own admission state read
  against the head it already publishes
  ([`../../primitives/stores/log-store.md`](../../primitives/stores/log-store.md)), never a new
  signal — and the restore residual prices the window a stall widens
  ([`../../residuals.md`](../../residuals.md#9-availability-caps-and-dos-bounds)).

## Cross-references

- [`architecture.md`](architecture.md) — the decomposition, the transfer engine, the freshness
  statement and consumer bar.
- [`witnessd.md`](witnessd.md) — the verify-then-sign service this daemon signals and asks for
  handshake signatures.
- [`logsd.md`](logsd.md) / [`sadd.md`](sadd.md) / [`blobsd.md`](blobsd.md) — the stores the loops
  page.
- [`mesh-transport.md`](mesh-transport.md) — the authenticated, encrypted channel every mesh link
  runs over.
- [`../federation/topics.md`](../federation/topics.md) — the gossip channels and the two-scope
  transport.
- [`../federation/witnessing.md`](../federation/witnessing.md) — the witnessing rules the routing
  and scoping serve.
