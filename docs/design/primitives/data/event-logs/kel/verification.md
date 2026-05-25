# KEL Verification — Verifier Walk

The KEL verifier walks a chain from inception to tip, validating structural integrity (SAID, prefix, chain linkage, per-kind field rules), cryptographic authority (single-signature for tier-1 / tier-2 kinds; dual-signature for tier-3 kinds), forward-key commitments (rotation-preimage and recovery-preimage commitments), and anchor presence (the per-kind `anchors` count / positional schema; per [§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation)). It returns a verification token — `KelVerification` — that downstream consumers hold as proof-of-verification and use to access trusted chain data.

This doc states the walk algorithm, the kind dispatch at inception, per-event checks, divergence handling, the token surface, and the federation-witnessing-layer signals consumers read. For per-kind reference (fields, authorization, anchor relationships), see [`events.md`](events.md); for chain lifecycle, [`log.md`](log.md); for merge-layer routing, [`merge.md`](merge.md); for recovery doctrine, [`recovery.md`](recovery.md); for the cross-node correctness proof, [`reconciliation.md`](reconciliation.md).

## What verification ensures

For every event the verifier walks, it ensures:

- Events match their kind-specific schemas (required and forbidden fields per [`events.md` §Per-kind field rules](events.md#per-kind-field-rules)).
- Serials start at 0 and increment by 1 with no gaps; the inception event has serial 0.
- The inception event has a valid prefix (the prefix re-derives from the canonical bytes with `said` and `prefix` blanked — see [`../../sad/said.md` §Derivation](../../sad/said.md#derivation)).
- All event prefixes match the chain's prefix (set at inception).
- All events have valid SAIDs (the SAID re-derives from the canonical bytes with `said` blanked).
- Events chain correctly from inception to tip via `previous` links.
- Pre-rotation commitments are honored: each `Rot` / `Ror` / `Fed` / `Rec` / `Dec` reveals a `publicKey` whose digest matches the prior establishment's `rotationHash`.
- Recovery commitments are honored: each tier-3 event (`Ror` / `Fed` / `Rec` / `Dec`) reveals a `recoveryKey` whose digest matches the prior establishment's `recoveryHash`.
- All signatures verify against the SAID bytes — single-signature for tier-1 / tier-2 kinds, dual-signature for tier-3 kinds.

Events are linked by their `previous` SAID. The serial in the canonical bytes makes each event's position structurally unambiguous; the `previous` pointer makes the chain linkage cryptographically verifiable.

## Walk algorithm

The verifier processes events in a single forward pass, verifying structure and cryptography simultaneously. Events must arrive in canonical order `(serial ASC, kind sort_priority ASC, said ASC)` with complete generations.

A **generation** is the set of all events at a given serial. The verifier processes events in generation order and tracks per-branch state. Divergence forks per-branch state — when a second non-privileged event appears at the same serial as the first, the verifier records `divergenceAncestor` (the SAID of `v_{d-1}`) and tracks both branches independently.

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
    validate_structure(event)  # Required / forbidden fields per kind

    # 4. Serial continuity
    if event.serial != expected_serial:
        return Error("Serial gap or regression")

    # 5. Chain continuity
    match event to a branch via event.previous
    if no matching branch:
        return Error("Previous SAID not found")

    # 6. Anchor format + per-kind anchor-list schema
    for said in event.anchors:
        verify said is a valid type-qualified base64 SAID
    assert anchors satisfy the per-kind count / positional schema (§Anchor-list dispatch)
```

The verifier checks **anchor format** here — each `anchors` entry is a valid SAID-shaped token, and the array satisfies the per-kind count / positional schema in [§Anchor-list dispatch](#anchor-list-dispatch) below. Anchor **kind** and **tier** validation are downstream — IEL and SEL verifiers enforce them when resolving policy satisfaction against KEL anchors per [§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation). The KEL token exposes the anchoring event's kind on each matched anchor so callers can apply tier-appropriate checks.

### Inception kind dispatch

KEL inception is one of two kinds — `Fcp`, `Icp` (see [`events.md` §Two-kind inception](events.md#two-kind-inception)). At v=0, the verifier dispatches on kind:

| Inception kind | `anchors` at v=0 | Verifier behavior |
|---|---|---|
| `Fcp` | empty | Pre-federation chain. No federation binding; no witnessing applies. The chain must be followed by a `Fed` event at v=1 to enter the federation-bound lifecycle (founder bootstrap). |
| `Icp` | `[federation_iel_said]` | Federation-bound chain. The verifier reads `anchors[0]` as the federation context and records it per event; witnessing applies per the inherited witness params. |

The kind discriminator is structural — encoded in the chain data — so the verifier dispatches the carve-out from chain data alone rather than consulting consumer configuration. Consumer trust composes through the [trusted federation `Fcp` SAID set](../../../../protocol-doctrine.md#federation-witnessing-in-verification) as a separate trust decision.

### Anchor-list dispatch

The `anchors` array is a flat, ordered sequence of SAIDs (see [`events.md` §Anchors](events.md#anchors)). The verifier interprets it positionally by event kind — there are no per-entry role tags in the data; the kind (already in the event) selects the schema:

```
match event.kind:
    Fcp            -> assert len(anchors) == 0
    Icp            -> assert len(anchors) == 1; federation = anchors[0]
    Fed            -> assert len(anchors) == 1; federation = anchors[0]
    Ixn            -> assert len(anchors) >= 1; generics = anchors[:]
    Rot, Ror       -> generics = anchors[:]            # len >= 0
    Rec, Dec       -> assert len(anchors) == 0
```

The verifier knows the kind and reads positional anchors per the kind's schema; the dispatch tells it which index holds which structural role. Federation IEL SAID resolution (for `Icp` / `Fed`) happens at verification time per the existing pattern — the position dispatch only assigns roles. Generic anchors on `Ixn` / `Rot` / `Ror` are checked for SAID format only; their satisfaction is downstream-verifier business per [§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation).

### Generation processing

Events at the same serial form a **generation**. The verifier processes all events in a generation together:

```
verify_generation(events_at_serial):
    if events_at_serial.len() > branches.len():
        # More events than branches → divergence detected
        fork BranchState for new branches
        record divergenceAncestor (the SAID of v_{d-1}) if first divergence

    for each event:
        match to branch via event.previous
        verify crypto for that branch
```

When a divergent generation spans a page boundary, the verifier re-fetches the incomplete generation at the next page so partial state never leaks into the walker.

### Establishment-event processing

When an establishment event is encountered (`Fcp` / `Icp` / `Rot` / `Ror` / `Fed` / `Rec` / `Dec`), the verifier checks the forward-key commitments made by the previous establishment event. The branch's tracked `rotationHash` and `recoveryHash` are the digests committed by the prior establishment; the current event must reveal a public key whose digest matches.

```
process_establishment(event, branch):
    new_public_key = parse(event.publicKey)

    # Verify rotation-hash commitment (forward commitment from prior establishment)
    if branch.tracked_rotation_hash exists:
        expected = digest(new_public_key)
        if branch.tracked_rotation_hash != expected:
            return Error("Public key does not match rotation hash")

    # Verify recovery-hash commitment (tier-3 events only)
    if branch.tracked_recovery_hash exists AND event.reveals_recovery_key():
        expected = digest(event.recoveryKey)
        if branch.tracked_recovery_hash != expected:
            return Error("Recovery key does not match recovery hash")

    # Update branch state
    branch.current_public_key = new_public_key
    branch.tracked_rotation_hash = event.rotationHash
    branch.tracked_recovery_hash = event.recoveryHash
    branch.establishment_tip = event
```

The forward-key-commitment mechanism is what makes the three-tier capability model cryptographic rather than policy-bound. See [`events.md` §Forward-key commitments](events.md#forward-key-commitments) and [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model).

### Signature verification

```
verify_signatures(signed_event, public_key):
    # SAID is Blake3-256 of canonical content; signing the SAID bytes is
    # equivalent to signing the content but more efficient (and stable
    # under extension — see ../../sad/said.md §Signing surface).
    data = signed_event.event.said.as_bytes()

    # Primary signature
    signature = parse_signature(signed_event.signature)
    public_key.verify(data, signature)

    # Recovery signature (dual authorization for tier-3 kinds)
    if signed_event.recovery_signature exists:
        recovery_key = parse_key(signed_event.event.recoveryKey)
        recovery_sig = parse_signature(signed_event.recovery_signature)
        recovery_key.verify(data, recovery_sig)
```

Per-kind signature shapes are documented in [`events.md` §Authorization and signature shapes](events.md#authorization-and-signature-shapes). Tier-3 events (`Ror` / `Fed` / `Rec` / `Dec`) require both signatures to verify and both digest commitments to match.

## KelVerification token

`KelVerifier::into_verification()` produces a `KelVerification` token — the proof-of-verification type:

```
KelVerification:
    prefix: String
    branch_tips: Vec<BranchTip>                  # one per branch (1 = linear, 2 = divergent)
    divergence_ancestor: Option<SAID>            # SAID of v_{d-1} on a divergent chain; None on linear
    last_seal_advancing_event: Option<SAID>      # most recent Rec/Ror/Rot/Fed that landed cleanly
    last_recovery_revealing_event: Option<SAID>  # most recent Rec/Ror/Fed/Dec
    federation_context_per_event: ...            # per-event federation binding (for chains that have re-bound)
    anchored_saids: BTreeSet<SAID>               # anchors observed during the walk
    queried_saids: BTreeSet<SAID>                # caller-registered SAIDs of interest
    witnessed: bool                              # threshold-many federation receipts under consistent state
    divergent: bool                              # federation-layer divergence at the queried chain position
    minority_dissent: ...                        # receipts below threshold; forensic signal
    witnessed_anchors: BTreeSet<SAID>            # subset of anchored SAIDs that are witnessed on the canonical branch
    policy_satisfied: bool                       # monotonic-falsy aggregate signal (per ../../../../protocol-doctrine.md §policy_satisfied)

BranchTip:
    tip: SignedKeyEvent              # chain head (latest event on this branch)
    establishment_tip: SignedKeyEvent  # last establishment event (provides signing key)
```

Token fields are private with no public constructor — the only way to obtain one is through `KelVerifier`. Holding the token proves the corresponding chain was verified. The seal tracking (`last_seal_advancing_event`, `last_recovery_revealing_event`) is per [`log.md` §Seal-tracking and the locked-portion bound](log.md#seal-tracking-and-the-locked-portion-bound).

### Derived accessors

- `current_public_key()` → `None` if divergent (ambiguous which branch's key is current).
- `last_establishment_event()` → `None` if divergent.
- `is_decommissioned()` → `true` when the linear branch tip is a `Dec` event (`Dec` whose landing would create or join a divergent set is rejected at merge per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal)).
- `is_divergent()` → `branch_tips.len() > 1`.
- `effective_said()` → single tip SAID, or `hash_effective_said("divergent:{prefix}")` for divergent, or `hash_effective_said("irreconcilable:{prefix}")` when the federation-witnessing layer surfaces the prefix as in-dispute. See [§Effective-SAID synthetic comparison](../../../../protocol-doctrine.md#effective-said-synthetic-comparison).
- `is_said_anchored()`, `anchors_all_saids()` → inline anchor-checking results for SAIDs the caller registered before the walk.

## Inline anchor checking

The caller registers SAIDs of interest before the walk via `verifier.check_anchors(saids)`. As the verifier processes events, it checks each event's `anchors` entries against the registered SAIDs. Results are available on the token via `is_said_anchored()` and `anchors_all_saids()`.

The `anchors` array is interpreted positionally by event kind (see [`events.md` §Anchors](events.md#anchors) and [§Anchor-list dispatch](#anchor-list-dispatch)). Generic anchors live on `Ixn` (≥ 1), `Rot`, and `Ror`; the `check_anchors` scan over generic anchors matches these three kinds. On `Icp` / `Fed` the anchor is the federation IEL SAID (federation binding at `anchors[0]`) rather than a generic anchor — the bootstrap case where a founder `Fed`'s federation-binding entry satisfies the federation IEL's own anchor requirement is a federation-layer mechanic (see [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md)), distinct from generic anchoring. Cross-chain consumers (IEL and SEL verifiers) need to know not just that a SAID is anchored but in which kind of KEL event — the token surfaces the anchoring event's kind so callers can enforce tier-appropriate anchor checks per [§Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation).

Registration before the walk lets the verifier record observations without a second database pass. The pattern is uniform across all primitive verifiers (KEL, IEL, SEL) and is the realization of the [§Operation Categories §Consuming](../../../../protocol-doctrine.md#operation-categories) rule: data access happens via a verification token, never via separate database queries between verification and use.

## Divergence detection and terminal-state determination

Verification does **not** fail on divergence — divergence is a chain state, not an error. The verifier:

- Forks per-branch state when a second non-privileged event appears at the same serial.
- Records the divergence ancestor (`v_{d-1}`'s SAID) and exposes it via `divergence_ancestor` on the token.
- Verifies both branches independently.
- Surfaces `is_divergent() = true` and the per-branch state via `branch_tips`.

The merge layer is responsible for resolving divergence (via `Rec` admitted through the discriminator path); the verifier reports findings.

### Terminal-state determination rule

The verifier's terminal-state-determination rule simplifies to:

- Divergent at `v_d`? (a divergent set exists in the chain data; on KEL only non-privileged `Ixn`-`Ixn` divergent sets can form per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal))
  - Yes → Divergent (recoverable via `Rec`).
  - No → Linear (Active, or Decommissioned via `Dec`).

`Rec` is archiving — its discriminator removes the divergent set before any divergent-set check fires, so `Rec` never appears in the divergent set at terminal-state-determination time.

### Verifier soft-fail versus merge-layer hard-fail

> **Verifier-merge composition.** The verifier itself does not reject events — it records signature-check results on the verification token and surfaces authorization failures via `policy_satisfied = false`. The merge layer rejects candidate batches whose verifier output is `policy_satisfied = false`; the new events never land. See [§Verifier and merge are distinct treatments](../../../../protocol-doctrine.md#verifier-and-merge-are-distinct-treatments).

Hard-fail at the verifier is reserved for structural integrity violations: SAID mismatch, prefix mismatch, broken chain linkage. Chain validity stays separable from policy satisfaction — the verifier reads through pathology to expose it; the merge layer reads `policy_satisfied` to gate against it.

Per-kind signature verification produces:

- **`Ixn` / `Rot`** — single-sig verified against the appropriate key. Failure flips `policy_satisfied = false`; the event lands at the merge layer only if the batch's verifier post-walk shows `policy_satisfied = true`.
- **`Ror` / `Fed` / `Rec` / `Dec`** — dual-sig verified against the rotation-preimage and recovery-preimage commitments at the parent event. Both signatures must verify; both digest commitments must match. Failure flips `policy_satisfied = false`.
- **`Fcp` / `Icp`** — single-sig verified against the declared `publicKey`. Prefix re-derives from canonical bytes; SAID re-derives independently.

The merge layer applies the `policy_satisfied` gate uniformly across all event kinds — no per-kind carve-outs — see [`merge.md` §Routing order §Kind-specific authorization](merge.md#4-kind-specific-authorization).

## Federation witnessing in verification

The verifier surfaces federation-witnessing signals on the verification token. Full witnessing mechanics live in [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) (subsequent sub-issue); this section names what the KEL verifier enforces.

**`witnessed`.** True iff the event has accumulated threshold-many receipts under a consistent federation state. Witnesses are sort-selected by chain position `(prefix, serial)`; all competing candidate events at the same chain position route to the same witness set by construction. The verifier independently re-checks each receipt's `witnessedSaid` against structural validity — receipt counts alone do not satisfy `witnessed`.

**`divergent`** (federation-layer). True iff the chain position `(prefix, serial)` has receipts from threshold-many witnesses for two or more distinct `witnessedSaid` values, AND each `witnessedSaid` resolves to a structurally valid event. Single-rogue protection: a rogue who signs receipts on a fake `witnessedSaid` cannot trigger divergence — the fake event fails structural re-check; honest witnesses don't sign for fakes. Threshold-many colluding rogues can only produce threshold-many receipts on a fake; the structural re-check rejects the fake. Both branches must reach threshold AND both events must be structurally valid for federation-layer divergence to fire.

**`minority_dissent`.** Receipts below threshold for some `witnessedSaid` that don't contribute to pinning. Forensic signal for potentially-compromised witnesses; not load-bearing for trust decisions.

**`witnessed_anchors` (KEL-specific).** The subset of anchored SAIDs that are witnessed on the canonical branch. IEL and SEL verifiers consult this set during anchor-tier policy resolution — only witnessed anchors count toward threshold.

### Acceptance gating for non-witnesses

A federation node that is **not** sort-selected as a witness for event `E` MUST NOT accept `E` into the chain's live state until `E` has accumulated threshold receipts. Witness nodes accept `E` upon their own signing (direct evidence of structural validity and self-attestation). Non-witnesses hold `E` in deferred-pending state until receipts arrive via witness gossip. This is the structural property that makes federation witnessing the source-of-truth for cross-node convergence on privileged events.

### Inheritance via the anchor walk

IEL and SEL events do not carry a federation context field; they inherit federation context via their KEL anchors. KEL is the leaf of trust composition: each IEL or SEL leaf-anchor check resolves to a KEL event, which carries the federation context declared in the most-recent `Fcp` / `Icp` / `Fed` at-or-before that anchor's serial. The KEL token surfaces `federation_context_per_event` so cross-chain verifiers can apply the right federation state per anchor.

### Trust composition through trusted federation `Fcp` SAIDs

For each event the verifier walks the chain's current federation context back to the federation IEL's `Fcp`. If the `Fcp` SAID is in the verifier's trusted set (compile-time-baked + runtime override), the federation is trusted for that event. Multi-federation chains (KELs that have transferred federations via `Fed` events) require each federation in the chain's history to be independently in the verifier's trusted set — no transitive trust. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) (subsequent sub-issue).

Consumers refuse to bind under `divergent = true` (federation cannot agree at this position) or `witnessed = false` (insufficient attestation), and consult the trusted federation `Fcp` SAID set as the trust ground. Anchors at serials strictly below the federation-divergent serial remain canonical per [§Pre-seal verifiability](../../../../protocol-doctrine.md#pre-seal-verifiability).

## Streaming

KEL verification follows the cross-primitive streaming pattern. The verifier walks events page by page rather than loading the full chain into memory.

### Constructors

- **`KelVerifier::new(prefix)`** — Start from inception. Full verification of an untrusted chain.
- **`KelVerifier::resume(prefix, &KelVerification)`** — Resume from a verified token. Used by the merge handler's normal-append fast path to verify appended events without re-verifying the entire chain.
- **`KelVerifier::from_branch_tip(prefix, &BranchTip)`** — Resume verification from a specific branch tip. Used for verifying events against a specific branch in divergence / recovery scenarios. The walker's input stream contains only events on that branch; the to-be-archived branch sits in storage but is excluded from the input stream.

### Paginated verification helper

`completed_verification(loader, prefix, page_size, max_pages, anchors)` pages through a `PageLoader`, calling `truncate_incomplete_generation()` at page boundaries to handle divergent generations that span pages. Returns a trusted `KelVerification` token. The `max_pages` parameter prevents resource exhaustion (default 64 pages ≈ 2K events; configurable via env var).

### PageLoader

KEL implements the cross-primitive `PageLoader` trait. Multiple implementations cover the read paths:

- **Non-locking reads** — wraps a chain-log store reference; serves the consumer (per [§Operation Categories §Serving](../../../../protocol-doctrine.md#operation-categories)).
- **Advisory-locked reads** — wraps a database transaction holding the advisory lock; the same transaction is used for the subsequent write under the merge handler. This eliminates time-of-check-to-time-of-use vulnerabilities (per [§Advisory Locking](../../../../protocol-doctrine.md#advisory-locking)).

### Walk usage

```
let mut verifier = KelVerifier::new(prefix)
loop:
    let (events, has_more) = source.fetch_page(prefix, since, limit)
    verifier.verify_page(events)
    sink.store_page(prefix, events)
    if not has_more: break
    since = events.last().said

let verification = verifier.into_verification()
```

The walker is single-pass forward; generation-aligned page boundaries mean a divergent generation spanning two pages re-fetches at the next page rather than being processed half-observed.

## Per-event check summary

| Property | Verification method |
|---|---|
| SAID integrity | Re-derive the SAID from canonical bytes with `said` blanked; compare to declared. |
| Prefix integrity | At inception: re-derive prefix with `said` and `prefix` blanked; compare. Subsequent events: inherit and check consistency. |
| Prefix consistency | Every event's `prefix` equals the chain's prefix. |
| Event chaining | `previous` resolves to a verified prior event SAID. |
| Chain completeness | All `previous` references resolve to existing events. |
| Serial monotonicity | Each event's serial equals previous event's serial + 1. |
| Inception serial | Inception events (no `previous`) have serial 0. |
| Inception kind dispatch | Verifier branches on `Fcp` / `Icp` per [§Inception kind dispatch](#inception-kind-dispatch). |
| Pre-rotation commitment | `digest(publicKey) == prior.rotationHash` on each `Rot` / `Ror` / `Fed` / `Rec` / `Dec`. |
| Recovery commitment | `digest(recoveryKey) == prior.recoveryHash` on each `Ror` / `Fed` / `Rec` / `Dec`. |
| Single-signature validity | `Ixn` / `Rot` / `Fcp` / `Icp`: signature verifies against the appropriate key per [§Signature verification](#signature-verification). |
| Dual-signature validity | `Ror` / `Fed` / `Rec` / `Dec`: primary signature against revealed `publicKey`; recovery signature against revealed `recoveryKey`. |
| Anchor format + schema | Each `anchors` entry is a valid SAID-shaped token; the array satisfies the per-kind count / positional schema ([§Anchor-list dispatch](#anchor-list-dispatch)). |
| Federation context | Verifier records federation binding per event (declared by inception or `Fed`). |
| Witness state | Token surfaces `witnessed`, `divergent`, `minority_dissent`, `witnessed_anchors` per the federation-witnessing layer. |

## Cross-references

- [`log.md`](log.md) — chain primitive: states, seal-tracking, locked-portion bound, page model.
- [`events.md`](events.md) — per-kind reference: fields, authorization, anchor relationships, three-tier capability model.
- [`merge.md`](merge.md) — merge handler routing: how the verifier output composes with the merge gate.
- [`recovery.md`](recovery.md) — recovery doctrine: Rec parent shapes, three-tier compromise model, pre-seal verifiability.
- [`reconciliation.md`](reconciliation.md) — cross-node correctness proof.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#verification-tokens-as-proof-of-verification) — verification tokens (cross-primitive pattern).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#streaming) — streaming and `PageLoader` (cross-primitive pattern).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#policy_satisfied) — `policy_satisfied` definition and walk-time pathologies.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#anchor-tier-elevation) — anchor tier elevation (cross-chain anchor checks).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#federation-witnessing-in-verification) — federation witnessing in verification.
- [`../../sad/said.md`](../../sad/said.md#derivation) — SAID and prefix derivation algorithms.
- [`../../sad/said.md`](../../sad/said.md#signing-surface) — signing over SAID bytes; stability under extension.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing mechanics (subsequent sub-issue).
- [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) — federation bootstrap and trusted federation `Fcp` SAID set (subsequent sub-issue).
