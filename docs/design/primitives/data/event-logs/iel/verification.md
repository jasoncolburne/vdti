# IEL Verification — Verifier Walk

The IEL verifier walks a chain from inception to tip, validating structural integrity (SAID, prefix,
chain linkage, per-kind field rules), **threshold authority** (a threshold of members' fresh KEL
participations anchor each event, resolved down to KEL signatures), roster and threshold state
(accumulated as a delta while walking), the facet-dependent `Wit` payload (dispatched on the chain's
root), and anchor presence (the `manifest` roles per kind). It returns a verification token —
`IelVerification` — that downstream consumers hold as proof-of-verification and use to access
trusted chain data.

Unlike a KEL, an IEL event carries **no adjacent signature of its own** — it authenticates entirely
by its KEL anchors
([`../event-shape.md` §Authentication & signatures](../event-shape.md#authentication--signatures)).
So the IEL verifier's authority check is a **down-walk**: for each IEL event, resolve the member KEL
participations that anchor it, verify each anchoring KEL (its signature and tier), and count them
against the threshold the IEL event's kind requires.

This doc states the walk algorithm, the root-facet dispatch, threshold anchoring and roster
accumulation, the bounded delegation walk, the `kills[]` forward-match, the token surface, and the
federation-witnessing signals consumers read. For per-kind reference, see [`events.md`](events.md);
for chain lifecycle, [`log.md`](log.md); for merge-layer routing, [`merge.md`](merge.md); for the
cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## What verification ensures

For every event the verifier walks, it ensures:

- Events match their kind-specific schemas (required and forbidden fields per the
  [event-shape reference](../event-shape.md#iel)), including the `manifest` role allowlist read
  kind-first and the `previousSeal` presence rule (present on every sealing kind, forbidden on `Icp`
  / `Fcp` / `Ixn`).
- Serials start at 0 and increment by 1 with no gaps; the inception event has serial 0 and a valid
  prefix (re-derived from the canonical bytes with `said` / `prefix` set to the placeholder — the
  roster, threshold vector, and `nonce` all participate).
- All event prefixes match the chain's prefix; all events have valid SAIDs; events chain correctly
  via `previous`; each sealing event's `previousSeal` resolves to the prior seal (the spine).
- **Every IEL event is anchored by a threshold of members' fresh KEL participations** — the required
  count drawn from the threshold vector by the event's kind, each participation kind-strict to the
  capability the act exercises, and each anchoring KEL signature valid.
- The **root facet** (`Fcp` vs `Icp`) is established before any `Wit` payload is read, and each
  `Wit` is read under the facet-correct allowlist.
- The current roster and threshold vector are the accumulation of every delta walked (with the
  live-set cap of `MAXIMUM_ROSTER_SIZE`); every config-changing event re-checks the post-delta
  bounds.

Events are linked by their `previous` SAID; the serial in the canonical bytes makes each event's
position structurally unambiguous, and the `pins`-SAD records the members' prior KEL tips so the
IEL's `said` never depends on the anchoring events.

## Walk algorithm

The verifier processes events in a single forward pass, verifying structure, authority, and state
simultaneously. Events must arrive in canonical order
`(serial ASC, kind sort_priority ASC, said ASC)` with complete generations. A **generation** is the
set of all events at a given serial; the verifier processes events in generation order and tracks
per-branch state. A fork forks per-branch state — when a second distinct event appears at the same
serial as the first, the verifier records `divergence_ancestor` (the SAID of `v_{d-1}`) and tracks
both branches independently.

### Per-event checks

For each event in the page:

```
verify_event(event):
    # 1. SAID and prefix integrity
    event.verify()  # Inception: verify both prefix and SAID; subsequent: verify SAID

    # 2. Prefix consistency
    if event.prefix != verifier.prefix:
        return Error("Prefix mismatch")

    # 3. Structure validation
    validate_structure(event)          # Required / forbidden fields per kind (event-shape)
    assert event.manifest carries only roles in allowed(event.kind, root_facet)   # read kind-first, facet-aware

    # 4. Serial + chain continuity
    if event.serial != expected_serial: return Error("Serial gap or regression")
    match event to a branch via event.previous       # else Error("Previous SAID not found")
    if event is seal-advancing and event.previousSeal != branch.last_seal:
        return Error("Spine back-link mismatch")

    # 5. Threshold authority (the down-walk)
    resolve_anchors(event)             # the member KEL participations that anchor this event
    verify_threshold(event, branch.roster, branch.thresholds)

    # 6. State + role consumption
    if event carries roster: accumulate_delta(branch, event.roster); recheck_bounds(branch)
    if event.kind in {Ath, Rev, Dth}:  record delegates / kills for the delegation + rescission surface
    if event.kind == Wit:              read_wit_payload(event, root_facet)   # facet-correct allowlist
```

The verifier checks the **manifest role vocabulary** here — a manifest carrying any role outside the
kind's (facet-aware) allowlist is malformed and rejected — and **anchor format** (each `anchors`
entry a SAID-shaped token). Anchor **kind** and **tier** validation of the SEL events an IEL anchors
are downstream (the SEL verifier enforces them when resolving against IEL anchors); the IEL
verifier's own anchor resolution is **downward** — to the member KEL participations that authorize
the event.

### Root-facet dispatch

An IEL's inception fixes its **root facet** — `Icp`-rooted (a user identity) or `Fcp`-rooted (a
federation) — for the whole chain. At `serial = 0` the verifier dispatches on the inception kind:

| Inception kind | Root facet | Verifier behavior                                                                                                                                                                                                                                                                    |
| -------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Icp`          | user       | Federation-bound (required — there is no direct mode): reads `{federation, federationPin}` and the `witnesses` config; pins the initial roster + threshold vector; anchored by all initial members' KEL `Rot`s (each consenting). An `Icp` omitting the binding is rejected.         |
| `Fcp`          | federation | The restricted facet: pins the witness-KEL roster, the `witnesses` config, and the `clock`; declares exactly `{t_govern}`; anchored kind-strict by each founder's KEL `Rot`. Recognizes a federation IEL from its own data — interpretation, not trust (the config-pin roots trust). |

The kind discriminator is structural — encoded in the chain data — so the verifier dispatches from
chain data alone. **The root facet is established before any `Wit` payload is read**, on **every**
`Wit`-reading path (the from-scratch walk, a `resume` from a cached token, and a `search_only` walk
that ends early). A `Wit` on an `Icp`-rooted chain may carry `{federation, federationPin}` +
`witnesses` and **must not** carry `roster` / `clock`; a `Wit` on an `Fcp`-rooted chain may carry
`roster` / `clock` / `witnesses` and **must not** carry `{federation, federationPin}`. The token
carries `root_facet` (set at inception) so a `resume` re-applies the dispatch without re-deriving it
— a `resume` can never process a `Wit` payload facet-blind. A facet-blind allowlist would admit a
governance-shaped roster delta on a user `Wit`, and since the kind → role allowlist is the **only**
gate on the directly-consumed governance roles, **the facet is established on every `Wit`-reading
path without exception**
([`merge.md` §Facet dispatch](merge.md#facet-dispatch-on-every-wit-reading-path)).

## Threshold anchoring — fresh participation up, `pins` down

An IEL event has no key of its own; its authority is a threshold of members' **fresh KEL
participations**. The verifier resolves and counts them:

- **Resolve the anchors down.** For each IEL event, find the member KEL events whose
  `manifest.anchors` names it. Each participation must be of **exactly** the kind that reveals the
  capability the act exercises (kind-strict up): content ← KEL `Ixn`; a tier-2 governance / kill /
  terminal act ← KEL `Rot`; the IEL `Wit` ← KEL `Wit`. A higher-tier stand-in does not count, and a
  rotated-out key cannot produce a fresh participation (closing the rotated-out-member backdate).
- **Verify each participation.** Each anchoring KEL is itself verified (its signature against the
  KEL's key state, its tier); only a KEL event that is **witnessed** on its own canonical branch
  counts toward threshold ([§Federation witnessing](#federation-witnessing-in-verification)).
- **Count against the kind's slot.** `Ixn` ← `t_use`; `Evl` / `Rev` / `Wit` / `Trm` ← `t_govern`;
  `Ath` / `Dth` ← `t_authorize`. An `Evl` **add** additionally requires each added member's tier-1
  KEL `Ixn` consent, counted toward consent-of-added, never `t_govern` — the kind split (joiner
  `Ixn` versus approver `Rot`) keeps it out of the governance count.

The IEL event records the members' prior KEL tips (`participation.previous`) in the top-level
`pins`-SAD; the verifier reads `pins` to locate each participation's chain without fetching the
manifest, and the fact that `pins` is top-level is what keeps the IEL's `said` independent of the
anchoring events (no SAID cycle).

### Roster accumulation — a delta, not a snapshot

The current roster and threshold vector are **not** stored as a snapshot; the verifier **accumulates
every delta while walking**. The `Icp` (or federation `Fcp`) pins the initial roster and the
declared threshold set; each `Evl` (user) or governance `Wit` (federation) carries a `roster` delta
(`add` + `cut` + changed thresholds), and the live roster is the running accumulation — a `cut`
`Evl` also evicts. The roster is a **set** (a delta is well-formed only with `add ∉ roster`,
`cut ⊆ roster`, `cut ∩ add = ∅`), and the verifier **re-checks the bounds on the post-delta config
at every config-changing event** — the security floor, the recoverability ceiling, the authorization
floor, the live-set cap of `MAXIMUM_ROSTER_SIZE`, and the non-empty floor. A delta pushing the live
set past `MAXIMUM_ROSTER_SIZE` is rejected (a DoS backstop). A `cut` is priced the **outgoing**
`t_govern` (the pre-change gate). This is why the token exposes the roster **as of a queried
position** — the accumulation up to that point, not a stored value.

## The bounded delegation walk

The `Ath` `delegates` role and the `Dth` `kills[]` rescission are the delegate surface (the full
doctrine is [`delegation.md`](delegation.md)). Answering "is party `P` a live delegate of `X`,
within `N` hops?" is a **bounded per-candidate walk**, never a materialization of the delegated set:

- **Never materialize the cumulative delegated set** — `X`'s transitive delegate closure is
  unbounded. The verifier streams `X`'s IEL with the candidate(s) in scope and carries **bounded
  per-candidate scalar state** (each candidate's `Ath` inclusion sets a boolean true), returning
  scalars. State is O(candidates), never the full set.
- **Walk up from the presented party, not down from `X`.** The verifier follows the **one
  authorizing path the document commits** — each hop a self-recorded `delegating` link chaining up
  toward `X` — confirming each hop's grant against that delegator's `Ath` inclusion list (a positive
  lookup). **Depth is the only quantity the walk adds.** Walking _up_ one committed path never
  enumerates the delegate tree beneath `X` — that tree **fans out** by design: a delegation
  hierarchy is how authority scales and how key management distributes across layers, so `X` need
  not authorize every actor directly. Each hop is a single `Ath`-inclusion lookup (itself bounded by
  `MAXIMUM_MANIFEST_LIST`) and its IEL verification is the ordinary per-IEL cost — no
  delegation-specific fan-out. The walk is bounded by the per-policy depth `N` **and** by a fixed
  protocol-wide **`MAXIMUM_DELEGATION_DEPTH = 4`** backstop; exceeding **either** denies
  (fail-secure). Four leaves room for a real hierarchy several layers deep (e.g. root → company →
  organization → team) while keeping chains shallow; a per-policy `N` sits tighter underneath. A
  fixed protocol constant, not a per-deployment knob.
- **Each hop's liveness is a `kills[]` forward-match** (below), never a scan for the absence of a
  rescission.

## The `kills[]` forward-match

Rescission (a delegate deauthorized, an owned artifact revoked) is answered by a **positive match**
on the owner's fresh IEL, never by scanning for absence. Given a killed locus, the verifier reads
**O(1) first, with a fail-secure fall-through**:

- **O(1) content-addressed read — first.** Read the derived lookup-SEL (its address is recomputed
  from `(owner, topic, data)`; fetch its `{Icp, Trm}`): **present → killed**. Tamper-evident and
  authoritative — and `Trm.pin` (= the killing `Rev` / `Dth`'s `previous`) points straight at that
  kill event, so a grandfather check reads the `bound` from its `kills[]` entry directly, with no
  exhaustive `kills[]` scan of the chain.
- **On a miss, fail-secure by default** — compute the flat domain-qualified
  `target = hash('{tag}:{owner}:{data}')` (the target **mirrors the killed address**:
  **non-lineaged** for a monotone kill, **lineaged** (`…:{lineage}`) for a **value rescission**,
  `:content` for a **content (app-SEL) closure** —
  [`sel/log.md`](../sel/log.md#the-content-and-lineage-fields)) and walk the owner's **fresh** IEL
  (from the relevant grant / issuance position to the tip), forward-matching the `target` against
  each `Rev` / `Dth`'s `kills[]`. In some `kills[]` → killed (grandfathered to that entry's
  `bound`); in none **on a walk that reached the fresh witnessed tip** → not killed. Being in a
  `kills[]` **is** the definition of killed, and it rides the same witnessed-IEL freshness gate as
  divergence, so a hidden kill needs a stale IEL the verifier already refuses when it trusts the
  owner at all. When it cannot freshness-confirm — any eclipse / single-source, **or a walk
  truncated at `max_pages` before the fresh witnessed tip** — it **refuses**, never reports
  not-killed.
- **Fail-open opts out of the walk** — under a latency budget a verifier may **opt down** to
  trusting the miss (best-effort not-killed), **never up**.

The `target` is **opaque to the IEL** — the verifier computes and matches it but never dereferences
it or interprets a `bound` (all revocation / grandfather logic is the feature layer's). A
**delegate**'s `bound` rides publicly in the `kills[].bound` field; a **doc-member**'s `bound` is
participant-identifying, so `kills[]` carries only the blind `target` and the verifier fetches the
`bound` from the **SEL `Trm`'s gated `bound` role** (a rescind-doc behind the read gate; withheld →
conservative, don't honor). See
[§Negative checks are positive lookups](../../../../protocol-doctrine.md#negative-checks-are-positive-lookups).

## `IelVerification` token

`IelVerifier::into_verification()` produces an `IelVerification` token — the proof-of-verification
type (in the field shapes below, `Vec<T>` is a list, `Option<T>` an optional value, and
`BTreeSet<T>` a sorted set):

```
IelVerification:
    prefix: String
    root_facet: RootFacet                  # Icp-rooted (user identity) vs Fcp-rooted (federation); fixed at inception, carried so a resume reads Wit payloads facet-correctly (never facet-blind)
    roster_at_tip: RosterState             # the accumulated live roster + threshold vector at the canonical tip (a delta accumulation, not a stored snapshot)
    branch_tips: Vec<BranchTip>            # one per branch (1 = linear, >1 = divergent)
    divergence_ancestor: Option<SAID>      # SAID of v_{d-1} on a divergent chain; None on linear
    last_seal_advancing_event: Option<SAID>  # the derived seal: most recent sealing event that landed cleanly on the linear run (not a competing sibling)
    federation_context_per_event: ...      # per-event federation binding, from the IEL's own Icp / Wit (user); a federation IEL carries none
    anchored_saids: BTreeSet<SAID>         # SEL-event SAIDs and credential issuance commitments found anchored on the canonical branch
    delegates_of: ...                      # per-candidate delegation-walk results (bounded scalar state)
    kills_matched: ...                     # kills[] forward-match results for the loci the caller registered
    structurally_valid: bool               # the structural-validity result (threshold anchoring, linkage, roster bounds)
    competing_branch_saids: Vec<SAID>      # the branch tips of a detected divergence (the beacon enumerates these)
    witnessed: bool                        # threshold-many federation receipts under consistent state (the IEL's own witness-config)
    witnessed_anchors: BTreeSet<SAID>      # subset of anchored SAIDs witnessed on the canonical branch

BranchTip:
    tip: IelEvent                          # chain head (latest event on this branch)
    roster_at_tip: RosterState             # the accumulated roster + thresholds on this branch
```

Token fields are private with no public constructor — the only way to obtain one is through
`IelVerifier`. Holding the token proves the corresponding chain was verified. The seal tracking is
per [`log.md` §The seal](log.md#the-seal-the-spine-and-the-locked-portion-bound).

### Derived accessors

- `roster_and_thresholds_at(position)` → the accumulated live roster + threshold vector as of a
  position (the delta accumulation up to it), for an `id(X)` policy leaf resolving `X`'s members and
  quorum.
- `is_delegate(candidate, N)` → the bounded delegation-walk result (live, within `N` hops).
- `is_killed(locus)` → the `kills[]` forward-match result (fail-secure by default).
- `is_terminated()` → `true` when the linear branch tip is a `Trm` (the identity retired; all its
  SELs freeze).
- `is_divergent()` → `branch_tips.len() > 1`.
- `region()` → the consumer-facing trust region computed **data-locally** against the **derived
  seal**: **trusted** (no fork reaching at-or-above the seal), **forked** (a fork at-or-above the
  seal with at most one sealed branch — a content fork recovers via a burying seal; a lone sealed
  branch you did not author reads forked but forces **your** reincept), or **disputed** (two or more
  branches each carry an **accepted** (witnessed-at-threshold) sealed event at the last seal —
  terminal, reincept).
- `effective_said()` → a fingerprint of the node's held state: a **single confirmed tip yields that
  tip's SAID** (the `Trm` SAID when terminated); a chain with **no single tip** yields a
  **type-tagged synthetic recoupled to the verdict** (`forked` / `disputed`), qualified by prefix
  and position, **not** a digest over the competing tips (that set is adversarially extensible →
  flood-unstable). A settled content branch drops out (forensic, reached by a by-prefix flat fetch);
  a **below-seal** sealed straggler drops out too (dropped, inert — backdate-safe). Only a
  **witnessed** sealed fork **at the last seal** keeps the chain in the synthetic (a spine fork →
  `disputed`). See
  [§Effective-SAID comparison](../../../../protocol-doctrine.md#effective-said-comparison).

The chain **states**, the `region()` trust projection, and the `effective_said` type tags are three
views of the one data-local walk:

| chain state | `region()` | `effective_said`     |
| ----------- | ---------- | -------------------- |
| Active      | `trusted`  | real tip SAID        |
| Forked      | `forked`   | `forked` synthetic   |
| Disputed    | `disputed` | `disputed` synthetic |
| Terminated  | `trusted`  | real `Trm` SAID      |

`region()` is the **divergence** axis, so Active and Terminated both project to `trusted`;
termination rides the orthogonal `is_terminated()` accessor.

## Inline anchor checking

The caller registers SAIDs of interest before the walk via `verifier.check_anchors(saids)`. As the
verifier processes events, it checks each event's `manifest.anchors` against the registered SAIDs —
the `anchors` role lives on `Ixn` (SEL v1s + credential issuance commitments), `Ath` (a `Gnt`), and
`Rev` / `Dth` (a `Trm`). Results are on the token via `is_said_anchored()` / `anchors_all_saids()`.
The token surfaces the **anchoring IEL event's kind** on each matched anchor, so a cross-chain
consumer (the SEL verifier) can enforce the kind-strict anchor matrix
([`events.md` §The kind-strict anchor matrix](events.md#the-kind-strict-anchor-matrix)).
Registration before the walk lets the verifier record observations without a second database pass —
the uniform verification-token pattern
([§Operation categories — consuming](../../../../protocol-doctrine.md#operation-categories)).

## Divergence detection and terminal-state determination

Verification surfaces divergence as a **structural condition** on the token — it reads through the
pathology to expose the chain's final portion rather than hard-failing. The verifier forks
per-branch state (roster and thresholds forked too) when a second distinct event appears at a
serial, records the divergence ancestor and the competing branch tips, verifies each branch
independently, and surfaces `is_divergent()` and `region()`.

### Terminal-state determination rule

- A **live** fork — a divergence at or above the **derived seal**?
  - **At most one sealed branch** → **forked** (recoverable); resolved by a burying seal on the
    winning branch.
  - **Two or more _accepted_ (witnessed-at-threshold) sealed branches at the last seal** →
    **disputed**; reincept.
- No live fork — linear, or a fork **buried below the seal** (its content loser inert) → **Active**
  (or Terminated via `Trm`); a `{Trm, content}` fork ends **Terminated** by tier-rank.

A `{Rev, content}` or `{Evl, content}` fork is one sealed branch → **forked**, recoverable (the
sealed branch survives, the content buries). A `{Evl, Evl}` (or any two sealed branches — the
federation IEL's every conflict) → **disputed**.

### Verifier reports; the merge layer gates

> **Verifier-merge composition.** The verifier itself does not reject submissions — it records the
> **structural-validity result** (`structurally_valid`) and the anchoring / divergence / roster
> signals on the token. The merge layer rejects candidate batches whose post-walk token reports a
> structural failure; the new events never land. See
> [§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported).

Hard-fail at the verifier is reserved for structural-integrity violations: SAID / prefix mismatch,
broken chain linkage, a threshold-unmet or signature-invalid anchor, a role outside the
(facet-aware) allowlist, a `kills` on an `Ixn`, a post-delta roster-bound violation, tamper. Chain
validity stays separable from the answer a consumer wants — the verifier reads through pathology to
expose the at-or-below-seal portion even on a chain with above-seal divergence; the merge layer
reads `structurally_valid` to gate against it.

### Pre-seal verifiability on the token

The trust an anchor carries splits at the **seal**, not the divergence point. An anchor hosted
at-or-below `last_seal_advancing_event` — a credential issued under a below-seal roster state, a SEL
bound at a below-seal `Ixn` — is **permanently final**, regardless of any later above-seal
divergence. (Against a **witnessed** sealed fork **at** the last (clean) seal the reading flips to
`disputed`, and permanence runs against the last **clean** seal; a below-seal sealed straggler is
**dropped**, not disputed.) So `anchored_saids` reflects the canonical branch, and a consumer
composes the anchor's seal position with `region()`: a below-seal anchor is honored even on a
`disputed` chain; an above-seal anchor on a `disputed` chain grounds no new trust.

## Federation witnessing in verification

The verifier surfaces federation-witnessing signals on the token. Full mechanics live in
[`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md);
this section names what the IEL verifier reads. **The data decides; witnessing propagates** —
receipts deliver competing branches and freshness, never a verdict.

- **`witnessed`.** An IEL event has **no key of its own**, so its witnessing **is** the witnessing
  of its **member KEL anchors** — the event is trusted when the required threshold of its anchoring
  member KEL participations are witnessed (the IEL's own `witnesses` config sets `threshold` /
  `signers`). A **user** IEL adds a second gate for **fork prevention** — the **position gate**: its
  events — content _and_ sealed — must also reach a **witness majority at their own
  `(IEL prefix, serial)`** (the position gate is **universal**), so two disjoint member sub-quorums
  cannot both land an event at one IEL serial, and a competing sealed sibling is declined
  first-seen. The **federation** IEL **realizes the position gate through exclude-self
  peer-witnessing** — its witnesses witness each other **exclude-self**, so a governance event needs
  a peer majority first-seen at its serial.
- **The divergence signal splits by provenance.** When a node holds two or more sealed branches
  **each accepted** — witnessed at threshold **and** its lineage accepted (a branch off a first-seen
  loss is dead on ascent and never counts) — at the **last seal**, it reads **`disputed` directly**
  — the walk decides. A sealed sibling held only as a **receipt** (not yet fetched), one **below
  threshold** (witness-declined), or one **below the seal** (dropped, backdate-safe) is not counted
  — it stays **`forked`** / deferred-pending. For content, a losing sibling never reaches threshold
  under the position gate, so the signal is a sub-threshold competing receipt set — the node fetches
  the event and the data-local walk decides.
- **`witnessed_anchors`.** The subset of the IEL's own anchored SEL SAIDs witnessed on the canonical
  branch; the SEL verifier consults it during kind-strict anchor authorization — only witnessed
  anchors count.

### Federation context per layer

Federation context attaches **per layer**. A **user IEL records its own** authoritative
`{federation, federationPin}` on its `Icp` / `Wit`, **field-matched** to its members' KEL `Wit`s on
every walk — it does **not** adopt a single member's KEL binding, so a lone or desynced member
cannot straddle the identity onto a different federation. A **federation IEL** carries **no**
federation field (it _is_ the federation, never self-bound — the `federationPin` currency gate does
not apply to it; its freshness is its clock). A **SEL** inherits its owner IEL's binding. The token
surfaces `federation_context_per_event` so a cross-chain verifier resolves each event to its
federation for witnessing while reading the binding from the layer that owns it. Trust composes
through the config-pinned federation prefix set (compile-time-baked + runtime override) — a
federation is trusted iff its prefix is in that set; multi-federation chains require each federation
independently trusted (no transitive trust). See
[§Federation witnessing in verification](../../../../protocol-doctrine.md#federation-witnessing-in-verification).

## Streaming

IEL verification follows the cross-primitive streaming pattern — the verifier walks page by page
rather than loading the full chain into memory, accumulating the roster as it goes.

### Constructors

- **`IelVerifier::new(prefix)`** — start from inception; full verification of an untrusted chain.
- **`IelVerifier::resume(prefix, &IelVerification)`** — resume from a verified token (the merge
  handler's normal-append fast path); it re-applies the token's `root_facet` so a `Wit` is never
  read facet-blind, and re-runs the to-tip negative checks (the `kills[]` forward-match) against the
  new tip whenever a transitively-pinned chain moves
  ([§Walk semantics](../../../../protocol-doctrine.md#walk-semantics)).
- **`IelVerifier::from_branch_tip(prefix, &BranchTip)`** — resume from a specific branch tip (its
  input stream contains only that branch's events; competing branches sit in retained storage,
  excluded), for verifying against a specific branch in divergence / recovery.

### Paginated verification helper

`completed_verification(loader, prefix, page_size, max_pages, anchors)` pages through a
`PageLoader`, calling `truncate_incomplete_generation()` at page boundaries so a divergent
generation spanning two pages re-fetches rather than being processed half-observed. Returns a
trusted `IelVerification`. `max_pages` prevents resource exhaustion (default 64 pages ≈ 8K events;
configurable).

## Per-event check summary

| Property                        | Verification method                                                                                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SAID / prefix integrity         | Re-derive from canonical bytes with the placeholder; compare to declared (inception re-derives the prefix from roster + thresholds + `nonce`).                                                    |
| Event chaining                  | `previous` resolves to a verified prior event; each sealing event's `previousSeal` resolves to the prior seal.                                                                                    |
| Serial monotonicity             | Each event's serial equals the previous serial + 1; inception is serial 0.                                                                                                                        |
| Inception kind + facet dispatch | Branch on `Icp` / `Fcp`; fix `root_facet`; read `Wit` payloads facet-correctly on every path.                                                                                                     |
| Threshold authority             | A threshold of members' fresh KEL participations (kind-strict up) anchor the event; each anchoring KEL signature valid and witnessed.                                                             |
| Roster accumulation + bounds    | Accumulate every `add` / `cut` / threshold delta; re-check the post-delta bounds (security floor, recoverability ceiling, authorization floor, cap `MAXIMUM_ROSTER_SIZE`) at every config change. |
| Manifest roles + anchor format  | The `manifest` carries only roles in the kind's facet-aware allowlist; each `anchors` entry a valid SAID-shaped token.                                                                            |
| Delegation / rescission         | Bounded per-candidate delegation walk; `kills[]` forward-match (fail-secure by default).                                                                                                          |
| Federation context              | Records the IEL's own binding per event (user); a federation IEL carries none.                                                                                                                    |
| Witness state                   | Token surfaces `witnessed` (member-anchor witnessing; a user IEL's own position gate), the divergence signal, `witnessed_anchors`.                                                                |

## Cross-references

- [`../event-shape.md`](../event-shape.md#iel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind field grid.
- [`log.md`](log.md) — chain primitive: states, the seal and spine, locked-portion bound, down-pins,
  page model.
- [`events.md`](events.md) — per-kind reference: the threshold vector, the manifest roles, the
  anchor matrix, the facet-dependent `Wit`, threshold anchoring.
- [`merge.md`](merge.md) — merge handler routing: how the verifier output composes with the merge
  gate; facet dispatch.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof.
- [`delegation.md`](delegation.md) — the delegate / rescind surface the bounded walk and `kills[]`
  forward-match serve.
- [`../kel/verification.md`](../kel/verification.md) — the KEL verifier that authorizes each IEL
  anchor.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#verification-tokens-as-proof-of-verification)
  — verification tokens; [§Walk semantics](../../../../protocol-doctrine.md#walk-semantics);
  [§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported);
  [§Negative checks are positive lookups](../../../../protocol-doctrine.md#negative-checks-are-positive-lookups);
  [§Federation witnessing in verification](../../../../protocol-doctrine.md#federation-witnessing-in-verification).
- [`../../../policy/policy.md`](../../../policy/policy.md) — the `id(X)` / `del(X, N)` policy leaves
  the token's `roster_and_thresholds_at` and `is_delegate` accessors resolve.
- [`../../../../substrate/federation/witnessing.md`](../../../../substrate/federation/witnessing.md)
  — federation witnessing mechanics.
