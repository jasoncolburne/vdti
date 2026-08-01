# LogServer — the chain-log composition

`LogServer` is the logic layer over a [`LogStore`](../primitives/stores/log-store.md): the merge
write path, acceptance, the receipt admission gate, durability, and serving. With `LogClient` (the
interface to a server — the same library, so a client binds in-process for tests or over the wire
for a deployment) and `LogSource` / `LogSink` (transfer built from clients), it is the whole
chain-log stack between the dumb store and the daemons that compose it
([`logsd`](../substrate/infrastructure/logsd.md),
[`witnessd`](../substrate/infrastructure/witnessd.md),
[`gossipd`](../substrate/infrastructure/gossipd.md)).

**A server composes stores, never other servers.** A `LogServer` that must resolve a manifest
role-SAD reaches the `SadStore` directly — a read — never a `SadServer` over RPC. Stated precisely:
**no _trusted_ backend RPC** — a server never consumes another server's **answer**; it may fetch
data it **end-verifies itself**, which is what makes an off-federation store's federation query
legitimate (a consumer, trusting nothing) while a server-to-server call is not.

## The merge layer — every durable event write

Every path that writes an event to the durable side goes through the **merge layer** — stage →
promote, never a raw append. Client submission, fetch-on-threshold, the anti-entropy bulk page, and
a `Sink` are **instances** of arrival; a new path inherits the rule by construction. The merge layer
runs the two checks canon states at the primitives
([`kel/merge.md`](../primitives/data/event-logs/kel/merge.md)): **structural validation on every
durable write**, and the **two-per-rail acceptance ceiling** evaluated only where a write would mark
a branch **accepted** — against admitted receipts, exact-match re-checked against the
chain-committed witness-config.

**Acceptance criteria dispatch per class.** For the witnessed classes, acceptance is threshold
receipts under the ceiling. For an `Fcp`-rooted chain's **unwitnessed steps** — serials 0–1 of a
witness KEL, and a federation IEL's genesis `Fcp` — receipts never exist, and acceptance is **the
admission dispatch's own grounds** (below): the configured-prefix match for a genesis, the
roster-membership-plus-identity-bond for a witness KEL's pair. Serial ≥ 2 is witnessed normally.

## The admission dispatch — three legs on the root kind

A chain submission dispatches on its **root kind**, then on binding and holding
([`witnessing.md` §The trust grant chain](../substrate/federation/witnessing.md#the-trust-grant-chain--the-federation-boundary)):

1. **`Icp`-rooted** — dispatch on the **binding in force for the submitted events**: the `Icp`'s pin
   governs only when the submission carries the `Icp`; a submission on a **held** chain reads the
   chain's current binding as held; a **rebind `Wit`** is the one event whose binding is
   **declared**, not inherited. A binding is in force iff its federation is the node's **own, or a
   trust lineage exists for it** — live, or killed — in the federation's trust chain; a
   **never-granted** federation (no established trust lineage at any lineage index) is **refused
   pre-stage**, with no carve-out. A **migrating** chain whose origin is trust-granted is **ordinary
   traffic** — submitted in sequence, accepted and durable page by page, receipts counted per the
   origin's trust-lineage windows, the rebind last, under the ordinary rate limits and the resumable
   admission walk (§Token bundles). The blocked-author fast-reject runs here for every class.
2. **`Fcp`-rooted federation IEL** — carries no pin and needs none: **respect it iff its recomputed
   prefix is the node's own or trust-granted**, then walk forward from that prefix. The genesis
   `Fcp` is accepted by the full genesis verification — recomputed prefix match, well-formedness,
   **all founders' `Rot`s anchoring the `Fcp`**, `manifest.clock` present
   ([`bootstrap.md`](../substrate/federation/bootstrap.md)) — decidable without deadlock because
   structural cross-chain checks read staged bytes (below). An unconfigured prefix needs **no
   refusal rule**: it grounds nothing, is never accepted, own-signed, or dragged, and ages out under
   the three promote reasons.
3. **`Fcp`-rooted witness KEL** — no pin, and its prefix is not a federation prefix: its as-of
   roster is the own-or-granted-and-held federation whose **walked roster history ever names it** —
   unique because of the **serial-1 identity bond** (the serial-1 slot anchors exactly one
   identity-establishment act; a two-match is unreachable from validly-held state — **refuse and
   alarm, never pick one**). Serials 0–1 — the `Fcp` and the specific consent event the admitting
   act itself commits — are accepted on this ground; serial ≥ 2 is witnessed normally.

**Structural cross-chain checks read held-or-staged bytes, and a park drains on presence.** The
roster-delta bond check, pin resolution, and anchor satisfaction are pure functions of immutable
content-addressed bytes and confer no acceptance — so a joiner's pair ⇄ admitting-`Wit` cycle
resolves against each other's **staged** bytes, and acceptance then lands in dependency order, with
no batching requirement (genesis is dependency-ordered, never atomic). The staged-read license
covers **structural** resolution only: roster and selection resolution for countability runs on
**accepted** state, always.

**A submission that cannot ground gets a typed refusal.** A submission whose federation context is
missing returns **`unresolvable`, naming the federation prefix and which condition holds** —
_untrusted_ or _trusted-but-unheld_ — so an out-of-order provisioning submission gets a signal
instead of silent staging-then-expiry. Never the deferred-dependencies response: that park would
never drain.

## The receipt admission gate

A receipt is admitted iff it is the signer's **first admitted** receipt at that `(position, tier)`
and countable by canon's test, **or** the signer's **second admitted** receipt there naming a
**different `eventSaid`** — the attested event's SAID, never the receipt SAD's own (one signer can
mint receipt SADs freely by varying its asserted `τ`) — from a signer **selected as-of the
position** with its key in window. Everything further from that signer at that position is
**refused**. The letter's parts are each load-bearing:

- **First/second are ranks over ADMITTED receipts** — a refused or discarded arrival consumes no
  slot (ranked over arrivals, a colluder leads with junk to burn the slot and halve the beacon); a
  re-arrival of the **same receipt SAD** is content-addressed dedup before the gate.
- **Selection is as-of the position, forever** — a current-roster reading would discard an evicted
  colluder's late double-sign proof.
- **The second leg deliberately admits non-countable rows** — they are the collusion evidence. So
  **the gate bounds and pre-filters; it does not make the held set countable**: every acceptance and
  verdict consumer — the merge ceiling, the `effective` join — **re-checks full countability per
  receipt, exact-match included**.
- **An unevaluable receipt parks** — body-not-held, keyed on the awaited **event**; "held" is
  evaluated **as the batch lands**, never once at ingress against pre-batch state, so a receipt
  whose grounding state arrives earlier in the same bundle is evaluated after that state lands — the
  ordinary body-not-held park, discharged intra-batch.
- **The park and the fetch trigger are bounded per signer, in the stated order: verify the signature
  against the signer's held KEL → charge that signer's quota → park.** Failed-signature receipts are
  bounded and attributed to the **delivery channel** (the gossip peer or submitter), never the
  claimed signer — else forged junk frames an honest witness toward the cut-in-one-act lever.
  Signature-unevaluable-yet receipts park under the delivery channel's budget, re-attributed on
  verification; repeated fetch failures against one signer's receipts feed the ops surface.

**Countability itself — whose receipts count, and within what windows — is the federation's trust
doctrine**, stated with the witnessing rules
([`witnessing.md`](../substrate/federation/witnessing.md)): a receipt counts iff its signer resolves
to a selected witness of a federation that is the node's own, or **trust-granted in the federation's
trust chain and held**, within the granting lineages' windows.

**Three runtime receipt writers, one gate.** `witnessd` (its own receipts), `gossipd` (peer
receipts), and **client submission** — a provisioning or migration bundle paged from another
federation must carry that federation's receipts, since no local `witnessd` mints them and no mesh
reaches that federation. All three pass this gate.

## Durability — the three promote reasons

The store answers "must this survive?", never "is this canonical?" — canonicity is the walk's, from
receipts. An event is promoted to the durable side iff:

1. **it is accepted** — the merge layer accepted it (criteria per class, above); or
2. **this node signed it** — a selected witness has spent its first-seen vote and must re-serve what
   it signed: a durability reason, never acceptance; or
3. **something promoted commits it as `previous`** — the ancestry drag.

Everything else **stages and ages out** — the witness-declined sibling, the submitter's own declined
beyond-band-stale tip, the park map, rate counters, token bundles, freshness statements, the
unseen-nonce cache.

**The drag is atomic with its tip and per-row validated.** An accepted event commits ancestors that
never individually reached threshold, so promote-on-threshold alone would leave an accepted tip
whose `previous` is missing — every promote drags its unpromoted ancestry, atomically: a tip whose
ancestry cannot be produced stays staged and is fetched. Each dragged row passes **canon's byte-pure
structural-validity set** — the per-event checks (SAID and prefix integrity, per-kind fields, serial
continuity, `previous` / `previousSeal` linkage, manifest vocabulary) **plus the two crypto legs**:
each event's signature against the lineage-derived key, and the forward-key commitment, key state
accumulated from the range plus its held prefix rows on a partial drag. The **per-lineage
seal-advance cap** is checked per range — computed over the dragged range together with its held
prefix rows, since a straddling run undercounts in isolation. The **locked-portion bound is never
applied to committed ancestry** — it is a tip-relative admission gate, and the ancestry's standing
comes from the accepted tip committing it; re-applying it would fail every dragged row under a
seal-advancing tip and every row of an honest migration, and it must not be restated
lineage-relative either, which is vacuous against a backdate attempt. A validation failure in
**committed** ancestry is not a fetch case — same bytes forever: the tip is **refused and the node
alarms**, collusion evidence about the signers, and honest nodes converge on the refusal (same
bytes, same validation). `witnessd`'s pre-sign verification **is** this same validation, invoked
pre-sign — one module.

**Never-delete is enforced beneath the service** — on a federation node no role holds `DELETE`; the
physical mechanisms and the single-writer roles are the architecture's
([`architecture.md` §Dependencies](../substrate/infrastructure/architecture.md#dependencies)).

## Serving — the acceptance gate and the spine

**One gate: serve iff accepted, or an ancestor of an accepted event this node holds** — acceptance
per class, so the gate covers witnessed-in-full for the witnessed classes and the admission
dispatch's grounds for an `Fcp`-rooted chain's unwitnessed steps. Never "which store answered."
Sub-threshold witnessed-class events stay witness-scoped; staged-only content is never served
outward (the merge layer's staged reads are its own, not a serve path).

**A second, independent axis: buried content is not served.** The receipts gate asks _did this reach
threshold_; this asks _is this on the canonical spine_:

> Below the last clean seal, serve the **spine only**. At-or-above it, serve up to the **seal
> frontier** — every retained branch whose ancestry passes through the **current floor seal** (the
> operative test; a lineage whose attach point — its last **on-spine** ancestor, never its immediate
> parent — sits below the floor is `non-canonical` wherever its rows sit) and the seal that closes
> it. Content above a branch's own seal is that branch's **next** window.

The mechanics **descend the spine, never scan-and-filter, and never ascend by serial**:

1. Descend `previousSeal` from the clean seal — deterministic; each seal carries exactly one.
2. Walk `previous` back from each spine seal to the one below and emit that window's spine — bounded
   by `MAXIMUM_UNSEALED_RUN`, never by the chain.
3. Serve the live region at-or-above the floor position, up to the seal frontier, only lineages not
   dead on ascent.

Ascending is poisonable on an **honest** node: a losing sealed sibling carries the **same
`previousSeal`** as the true spine seal and is durable there by own-sign promote — ascending returns
both and can serve a **sub-threshold event to a non-witness on the default path**. Serial stays an
index accelerator, never the boundary. Scan-and-filter stalls: a window with a large buried
population exhausts the scan limit before any seal appears. No spine is materialized — the descent's
hops are indexed lookups over **seals only**, so a cold page costs O(spine seals above `since`) hops
— the chain's rotation count, never its event count. Partial pages are normal; `MINIMUM_PAGE_SIZE`
is a floor on capacity, never a promise a page is full.

Why the axis exists: an owner buries its own accepted run with **one rotation and no collusion** — a
seal-advancer siblinging the run's first event, the same one-event resolution whichever arrived
first — and those rows were accepted, so they are permanent. Serving them turns bounded paging into
O(buried).

**The serve boundary and `effective`'s floor are one boundary** — the last clean seal **is** the
derived seal — and the live-region step is **one traversal shared** with
[`LogStore.effective`](../primitives/stores/log-store.md#effective-is-a-bounded-read--not-a-walk-and-not-the-raw-tip)'s
read: same population, same dead-on-ascent prune. Wiring the two to different boundaries silently
diverges exactly on `Disputed` chains.

### The two serve flags — `non-canonical` and `sub-threshold`, orthogonal

> **`non-canonical`** — everything held that is not on the served spine. **`sub-threshold`** —
> events that never reached threshold. Independent; pass either, both, or neither.

They gate for different reasons: `sub-threshold` lifts **witness-scoping** (noise that must not skew
a reading — the walk ignores anything not accepted, so surfacing it cannot move a verdict; an audit
obligation attaches), while `non-canonical` lifts a **cost** boundary (the data is
accepted-and-dead, verifiable, and skews nothing — off the default path because it is expensive,
never because it is dangerous). `non-canonical`, not "buried": the off-spine set is defined
**structurally** — buried content losers plus inert below-seal sealed stragglers — and on an honest
node the straggler class is unpopulated (a declined straggler is never accepted, own-signed, or
dragged, so it stages and ages out; it is durable only at a witness that own-signed it). Note the
reading risk: `non-canonical` reads naturally as "not accepted," which is the **other** flag.

**The classification is structural** — tier from a kind column, position against the clean seal,
on-spine from the walk the server already performs, liveness by ascent — **never an acceptance
determination, and never a timestamp or arrival-order mechanism**: arrival order is not in the data,
and the only state it would classify is collusion-made, where a timestamp is forged. The backdate
defense's **guarantee** — the walk drops a below-seal sealed straggler, whatever its receipt count —
must never come to rest on a receipt count or a clock; that is the one defense here that does not
degrade with witness compromise ([`witnessing.md`](../substrate/federation/witnessing.md)).

**Receipts follow their events** — off-spine receipts leave the default page with their events;
below the seal there is no live divergence, so the beacon loses nothing.

**Two query shapes, not unified.** The default is next-seal-then-walk, shaped to avoid touching
off-spine rows. `non-canonical` is a range scan minus the spine — a page of dead events **is** the
answer there, so the stall argument does not apply.

## Migration ownership — one owner, several writers

A data scope has exactly **one migration/schema owner** — `logsd` for events, `witnessd` for
receipts (both in `LogStore`); `sadd` for content-SADs; `witnessd` for freshness, on the expiring
side, which has no schema to migrate — and that owner is the single backfiller a migration needs.
Runtime writing is **not** exclusive: `gossipd` lands peer events (through the merge layer) and peer
receipts (through the admission gate), and client submissions land events **and receipts** beside
`logsd` — serialized by the **per-prefix advisory lock** and made safe by content-addressed
idempotency. A migration is a store-library version rolled through expand/contract over a
compatibility window; indexes are derived from immutable content, so a backfill is a re-derivation,
never a risky in-place transform. The content format never migrates relationally — a format change
is a new `kind` version, and old bytes stay verifiable.

## Deferred-dependency parking

An event can arrive before something it depends on lands on another chain — a race, not an error —
and parking is a **server** concern: the park map (Redis, keyed by awaited SAID and awaited chain,
secondaries written before the primary so a landed park is always drain-reachable, every key
carrying the expiry) lives in the server compositions over shared infra;
[`gossipd`](../substrate/infrastructure/gossipd.md) contributes only the drain triggers it observes
on the mesh. A parked batch replays through the full merge path — parking defers verification, never
substitutes for it. Structural cross-chain dependencies drain on **presence** (staged or durable),
never on acceptance (§The admission dispatch). On the federation, expiry bounds are safety-free — a
lost park re-arrives by sync; **off-federation that premise is gone**, and the split is by await
class: a chain await re-drives itself off the store's own federation-client poll, while a
`sad/field` await has no such source — a dropped one returns the deferred response to the
**client**, which is the backstop.

## Capability tokens and token bundles

A verification result is a token the **server** mints and hands to the store's write path — `Rooted`
/ `Verified` / `RateOk` — non-constructable by type: only the check that establishes the property
can produce one, so a local write cannot skip verification.

The three things this doc calls a token bind to different subjects, and the distinction is
load-bearing. A **capability token** (`Rooted` / `Verified` / `RateOk`) binds to a **code path** —
non-constructable by type, it establishes that the check ran, never that any particular batch was
its subject, which is why it gates the writer handle rather than riding a call's arguments
([`log-store.md`](../primitives/stores/log-store.md)). The **verification token** the merge write
path holds is what binds a verification to the batch it verified — the chain verified under the
per-prefix lock, the batch verified against that token, the write in the same transaction
([`logsd.md` §The merge write path](../substrate/infrastructure/logsd.md#the-merge-write-path)). A
**token bundle** names its subject by SAID because it alone outlives a single request. A **`Sink`**
trusts no token and re-verifies — a token from another node is worthless. Receipts and freshness
statements are the **wire's** proof tokens; no new signed replay or rate tokens cross the wire
(replay and rate are node-local, and a signed per-request token is a correlation surface bought for
nothing).

An admission walk can be arbitrarily long — confirming a root or verifying a migrating chain can
mean walking from inception — so the walk is **resumable across requests** and its accumulated
result is a **token bundle**: a request carries `{ request, tokenSetId }`, the server advances one
page per request and records progress against the bundle, the bundle names its subject by SAID —
and, for a blob, by hash, with the bytes arriving **last** against a completed bundle they must
match. This is how **all** submissions work, not a blob special case. The scope of the claim is
load-bearing:

- **A token bundle makes no verifiability claim to any consumer.** It gates **admission** — whether
  this node stores the thing — never correctness. It lives in shared infra (Redis), joining the
  rate-limit counters in the carve-out for node-local admission state; nothing a consumer trusts may
  live there.
- **TTL is set by the conclusion class.** A **rooting** bundle records a conclusion **as of** a
  point in a chain, and chain state moves: short TTL, re-checked at use. A **structural-walk**
  bundle — a migration admission — records a conclusion over a fixed run of immutable
  content-addressed events, which cannot go stale: its TTL is **sized to the walk** and refreshed
  per continuation, since the walk is unbounded in length and paced by the client's clock. An
  expired walk **restarts from the inception**, priced as a resubmission (idempotent, dedup by SAID)
  — never a silent ceiling on migratable chain length. Staged pages carry the same requirement:
  their TTL must exceed the walk plus the witnessing window, or early pages age out from under the
  pre-sign read and stall the one signature the migration needs. The staged working set is ingress
  rate × TTL — an operational Redis bound; eviction under pressure degrades honest walks to
  restarts, never correctness.
- **`RateOk` is keyed to the authenticated submitter, never to the data** — in a data-keyed bundle,
  one submitter would complete a walk and another would ride their allowance.

## Cross-references

- [`../primitives/stores/log-store.md`](../primitives/stores/log-store.md) — the dumb store this
  composition drives.
- [`sad-server.md`](sad-server.md) / [`blob-server.md`](blob-server.md) — the sibling compositions;
  parking, tokens, and the no-trusted-RPC rule are shared.
- [`../primitives/data/event-logs/kel/merge.md`](../primitives/data/event-logs/kel/merge.md) — the
  merge outcomes, the two checks, and the two-per-rail bound (IEL and SEL analogues in their own
  docs).
- [`../substrate/federation/witnessing.md`](../substrate/federation/witnessing.md) — countability,
  selection, the trust chain, query-scoping.
- [`../substrate/federation/bootstrap.md`](../substrate/federation/bootstrap.md) — the genesis
  verification and the trust root.
- [`../substrate/infrastructure/architecture.md`](../substrate/infrastructure/architecture.md) — the
  decomposition, never-delete's physical enforcement, the ops surfaces.
