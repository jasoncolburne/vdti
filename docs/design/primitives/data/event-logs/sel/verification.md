# SEL Verification — Verifier Walk

The SEL verifier walks a chain from inception to tip, validating structural integrity (SAID, prefix,
chain linkage, per-kind field rules), the **cross-layer anchor edge** (each SEL event extends its
SEL's latest IEL-anchored tip, and a SEL event on a dead IEL anchor is dead), the down-pin floor,
and anchor presence (the `manifest` roles per kind). It returns a verification token —
`SelVerification` — that downstream consumers hold as proof-of-verification.

Like an IEL event, a SEL event carries **no adjacent signature of its own** — it authenticates by
its IEL anchor
([`../event-shape.md` §Authentication & signatures](../event-shape.md#authentication--signatures)).
So the SEL verifier's authority check is a **two-layer down-walk**: for each SEL event, resolve the
IEL event that anchors it, confirm that IEL event carries the required count (drawn from the IEL's
threshold vector by the SEL event's kind), and let the IEL verifier resolve that count down to
member KEL signatures. The SEL never re-does the IEL's threshold arithmetic — it consults the IEL's
verification token.

This doc states the walk algorithm, anchor-monotonicity over the IEL walk, the cross-layer deadness
read, the lookup-SEL two-pass derivation, the `Trm` kill structure the fail-secure revocation read
consumes, and the token surface. For per-kind reference, see [`events.md`](events.md); for chain
lifecycle, [`log.md`](log.md); for merge-layer routing, [`merge.md`](merge.md); for the cross-layer
correctness proof, [`reconciliation.md`](reconciliation.md).

## What verification ensures

For every event the verifier walks, it ensures:

- Events match their kind-specific schemas (required and forbidden fields per the
  [event-shape reference](../event-shape.md#sel)), including the `manifest` role allowlist read
  kind-first (a `content` role only on `Ixn`, `grant` only on `Gnt`, `anchors` only on `Trm`; no
  manifest on `Icp` / `Pin`) and the `previousSeal` presence rule (present on `Gnt` / `Trm`,
  forbidden on `Icp` / `Ixn` / `Pin`).
- Serials start at 0 and increment by 1 with no gaps; the inception `Icp` has serial 0 and a valid
  prefix (re-derived from the canonical bytes — the populated `owner` / `topic` / `data` — with
  `said` / `prefix` set to the placeholder), carries no `pin` and no manifest, and is **never itself
  anchored** (its serial-1 v1 is).
- All event prefixes match the chain's prefix; all events have valid SAIDs; events chain via
  `previous`; each `Gnt` / `Trm`'s `previousSeal` resolves to the prior seal (the local spine).
- **Every non-inception event extends the SEL's latest IEL-anchored tip** (anchor-monotonicity) and
  **is live** (its anchoring IEL event is not dead — cross-layer deadness-descends).
- The down-`pin` floors to the IEL: a serial-1 v1's `pin` equals its anchoring IEL event's
  `previous`, and each `Ixn` re-pins forward.
- Authentication rides the v1 — a SEL is validly established only if its serial-1 v1 resolves to a
  real event on the **claimed owner's** IEL
  ([`log.md` §Authentication rides the v1](log.md#authentication-rides-the-v1)).

## Walk algorithm

The verifier processes events in a single forward pass, verifying structure, the cross-layer edge,
and state simultaneously. Events must arrive in canonical order
`(serial ASC, kind sort_priority ASC, said ASC)` with complete generations. A **generation** is the
set of events at a given serial; a fork forks per-branch state — when a second distinct event
appears at the same serial, the verifier records `divergence_ancestor` and tracks both branches
independently. By the theorem, such a fork exists only if the IEL forked beneath
([`reconciliation.md` §The theorem](reconciliation.md#the-theorem--a-valid-sel-fork-implies-an-iel-fork-beneath-it)).

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
    assert event.manifest carries only roles in allowed(event.kind)   # read kind-first

    # 4. Serial + chain continuity
    if event.serial != expected_serial: return Error("Serial gap or regression")
    match event to a branch via event.previous       # else Error("Previous SAID not found")
    if event.kind in {Gnt, Trm} and event.previousSeal != branch.last_seal:
        return Error("Spine back-link mismatch")

    # 5. Cross-layer anchor edge (the down-walk)
    anchor = resolve_owner_iel_anchor(event)         # the IEL event naming this SEL event
    if anchor is unattributable: skip (not blocking) # skip-unattributable
    if anchor.serial already-attributed for this SEL: mark inert   # re-anchor is malformed
    if anchor is dead (below the IEL's seal):   mark inert   # cross-layer deadness-descends
    verify_count(event.kind, anchor, owner_iel_token)  # the IEL delivers the count

    # 6. Floor + role consumption
    if event.kind != Icp:  assert event.pin floors to the IEL (v1: == anchor.previous)
    if event.kind == Ixn:  record content SADs
    if event.kind == Trm:  record the kill (its anchor, its committed target)
```

The verifier checks the **manifest role vocabulary** here — a manifest carrying any role outside the
kind's allowlist is malformed and rejected. **Anchor-kind and tier** validation is where the SEL
verifier does its cross-layer work: it confirms the anchoring IEL event is of exactly the matching
kind (content ← IEL `Ixn`; `Gnt` ← IEL `Ath`; `Trm` ← IEL `Rev` / `Dth`) and that tier-elevation
holds as an additional floor, not the check
([`events.md` §The kind-strict cross-layer anchor matrix](events.md#the-kind-strict-cross-layer-anchor-matrix)).

## Anchor-monotonicity — the owner IEL is the clock

A SEL has no clock of its own; the **IEL totally-orders it**. The verifier enforces the edge against
the IEL's **canonical / retained walk** (the IEL's own verification token):

- **Extend the latest anchored tip.** A SEL event is valid only if the IEL event that anchors it
  names the SEL's **current** tip — i.e. the SEL event extends the SEL's latest IEL-anchored
  position. This is what makes a **linear** IEL totally-order the SEL: exactly one anchored tip at
  each serial, so the SEL cannot present two valid same-serial events, and **a SEL never forks under
  a linear IEL**.
- **Skip-unattributable.** The anchor SAID is opaque, so an IEL anchor whose **body the node lacks**
  cannot be attributed; the SEL event is **skipped, not blocking** — a withheld, lost, or private
  anchor body never wedges the SEL. The verifier processes each SEL it can attribute, and a later
  page carrying the anchor body resumes it.
- **A re-anchor is inert.** An IEL anchor naming a SEL event at an **already-attributed** serial is
  malformed → the SEL event is inert; the carrying IEL event stays valid, but the inert anchor never
  advances the tip. This forbids re-writing a SEL's history by re-anchoring an old serial.

Because the check runs over what a node can **attribute**, a node appending to a linear IEL always
extends each SEL correctly, and a **valid SEL fork implies an IEL fork beneath it**
([`reconciliation.md`](reconciliation.md#the-theorem--a-valid-sel-fork-implies-an-iel-fork-beneath-it)).

### Cross-layer deadness-descends

A SEL event whose anchoring IEL event is **dead** — condemned, or buried below the IEL's seal — is
**itself dead** (the **IEL → SEL** anchor edge only, never KEL → IEL). This is how a plain content
SEL's fork resolves: when the IEL buries its losing branch, the SEL events that branch anchored die
by descent, and everything built on them dies by descent (an event whose parent is dead is dead).
The verifier reads deadness through the IEL's token — a SEL anchor that resolves to a
below-owner-seal IEL event is marked dead, its subtree with it — so a content fork the IEL has
resolved reads **Active** on the winning branch, and a **`{Trm, Ixn}`** divergence reads
**Terminated** by tier-rank without any IEL burial.

## Lookup-SEL two-pass derivation

A **lookup SEL** (a revocation or rescission locus) is located by **blind-recomputing** its prefix,
never by a global index. Given the data a verifier already holds — the `owner`, the `topic`, and the
grant-instance `data` — it re-derives the address:

- **Pass 1 — the prefix.** Populate both `said` and `prefix` on `Icp{owner, topic, data}` with the
  placeholder, canonicalize, hash, qualify → the **fetch prefix**.
- **Pass 2 — the SAID.** With the real prefix in place, populate only `said` with the placeholder,
  hash → the `Icp`'s **SAID**.

The two see different bytes, so `prefix ≠ said`
([`../../sad/said.md` §Derivation](../../sad/said.md#derivation)). The verifier fetches the
`{Icp, Trm}` lookup SEL **by prefix** (there is no SAID index —
[§Addressing](../../sad/said.md#chain-inception-events-prefix-deriving-sads)), confirms the `Trm` is
the SEL's v1 (`Trm.previous == said(Icp)`), and validates the `Trm`'s anchor (a real, sealed,
owner-authored IEL `Rev` / `Dth`). The IEL's `kills[]` `target` is a **separate** flat hash
`hash('{topic}:{owner}:{data}')`, distinct from this derived prefix — so matching the public
`target` never yields the lookup object's address
([`../iel/verification.md` §The kills forward-match](../iel/verification.md#the-kills-forward-match)).

## The `Trm` kill structure

The SEL primitive states the **structure** a kill leaves; the read strategy that consumes it is the
feature layer's. A `Trm` is valid **only** anchored by an IEL `Rev` (a governed revocation) or `Dth`
(a rescission), sealed on arrival — so the verifier surfaces, per matched kill:

- the `Trm`'s anchoring kind (`Rev` vs `Dth`), which the feature layer maps to revocation vs
  rescission;
- that the `Trm` sits under a **real, sealed, owner-authored** kill-anchor (the structural
  precondition for honoring a kill);
- the `Trm.pin` (= the killing `Rev` / `Dth`'s `previous`), which points straight at the kill event
  so a grandfather check reads the IEL's `bound` from that event's `kills[]` entry directly.

What a matched kill **means** — the fail-secure `kills[]` walk over the owner's fresh IEL, the
fail-open lookup opt-out, the per-hop grandfather `bound` — is the credential / document feature
layer's ([`../../../policy/documents.md`](../../../policy/documents.md);
[§Negative checks are positive lookups](../../../../protocol-doctrine.md#negative-checks-are-positive-lookups)).
The SEL verifier states only the structural facts the read consumes.

## `SelVerification` token

`SelVerifier::into_verification()` produces a `SelVerification` token — the proof-of-verification
type (in the field shapes below, `Vec<T>` is a list, `Option<T>` an optional value, and
`BTreeSet<T>` a sorted set):

```
SelVerification:
    prefix: String
    owner: String                          # the IEL prefix (Icp-only, immutable)
    topic: String                          # the application discriminator
    kind_class: SelClass                   # content SEL vs lookup SEL (blind-recomputable)
    branch_tips: Vec<BranchTip>            # one per branch (1 = linear, >1 = divergent — implies an IEL fork)
    divergence_ancestor: Option<SAID>      # SAID of v_{d-1} on a divergent chain; None on linear
    last_seal_advancing_event: Option<SAID>  # the local seal (a Gnt / Trm), if any; a plain content SEL has none — its finality floors to the IEL
    owner_anchor_per_event: ...            # per-event IEL anchor (kind + attributability + liveness)
    content_saids: BTreeSet<SAID>          # content-SAD SAIDs recorded on the canonical branch
    kill: Option<KillStructure>            # a lookup SEL's Trm: its anchor kind (Rev / Dth) + committed target
    structurally_valid: bool               # structural-validity result (linkage, anchor edge, floor)
    competing_branch_saids: Vec<SAID>      # branch tips of a detected divergence

BranchTip:
    tip: SelEvent                          # chain head (latest event on this branch)
    pin: SAID                              # the IEL position this branch floors to
```

Token fields are private with no public constructor — the only way to obtain one is through
`SelVerifier`. Holding the token proves the corresponding chain was verified against its IEL.

### Derived accessors

- `owner()` → the IEL prefix (a consumer resolves it to walk the owner for authority and liveness).
- `is_lookup()` → whether the SEL is blind-recomputable (a lookup locus) versus handed content.
- `kill_structure()` → a lookup SEL's `Trm` structure (anchor kind + committed target), for the
  feature-layer revocation / rescission read.
- `is_terminated()` → `true` when the tip is a `Trm`, or the IEL is terminated (all its SELs
  freeze).
- `is_divergent()` → `branch_tips.len() > 1` — which, by the theorem, means the IEL forked beneath.
- `region()` → the consumer-facing trust region, computed **data-locally** through the IEL edge:
  **trusted** (linear, or a content fork the IEL already buried), **forked** (a live content fork
  awaiting the IEL's cross-layer burial, or a lone sealed branch you did not author), or
  **disputed** (≥ 2 accepted sealed branches — the IEL disputed beneath, terminal, reincept).
- `effective_said()` → a fingerprint of the node's held state: a **single confirmed tip yields that
  tip's SAID** (the `Trm` SAID when terminated); a chain with **no single tip** yields a
  **type-tagged synthetic recoupled to the verdict** (`forked` / `disputed`), qualified by prefix
  and position, **not** a digest over the competing tips (that set is adversarially extensible →
  flood-unstable). A content branch buried by the IEL's seal drops out (forensic, reached by a
  by-prefix flat fetch). See
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

The caller registers content SAIDs of interest before the walk via `verifier.check_content(saids)`.
As the verifier processes events, it checks each `Ixn`'s `manifest.content` against the registered
SAIDs; results are on the token via `is_content_recorded()`. A consumer asking "did this owner
record this SAD on this SEL?" registers it before the walk, and the verifier records the observation
without a second database pass — the uniform verification-token pattern
([§Operation categories — consuming](../../../../protocol-doctrine.md#operation-categories)).

## Divergence detection and terminal-state determination

Verification surfaces divergence as a **structural condition** on the token — it reads through the
pathology to expose the chain's final portion rather than hard-failing. The verifier forks
per-branch state when a second distinct event appears at a serial, records the divergence ancestor
and competing tips, and surfaces `is_divergent()` and `region()`. Because a valid SEL fork implies
an IEL fork beneath it, the SEL verifier reads the verdict **through the IEL edge**:

- A **content** fork whose IEL is still forked → **forked**; it resolves to **Active** (or the loser
  dies) when the IEL's burying seal propagates (cross-layer deadness-descends).
- A **`{Trm, Ixn}`** divergence → **Terminated** by tier-rank, no IEL burial needed.
- **≥ 2 accepted sealed** SEL branches → the IEL is disputed beneath → **disputed** (reincept).

### Verifier reports; the merge layer gates

> **Verifier-merge composition.** The verifier itself does not reject submissions — it records the
> **structural-validity result** (`structurally_valid`) and the anchor-edge / divergence signals on
> the token. The merge layer rejects candidate batches whose post-walk token reports a structural
> failure; the new events never land. See
> [§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported).

Hard-fail at the verifier is reserved for structural-integrity violations: SAID / prefix mismatch,
broken chain linkage, a `content` role on a `Gnt` / `Trm`, a manifest on an `Icp` / `Pin`, a
wrong-kind or wrong-tier IEL anchor, a re-anchor at an attributed serial, tamper. A missing anchor
**body** is **not** a hard fail — it is skip-unattributable, so a withheld anchor never wedges the
SEL. Chain validity stays separable from the answer a consumer wants — the verifier reads through
pathology to expose the pre-fork portion even on a divergent chain.

## Federation witnessing in verification

A SEL has **no witnesses of its own** — it inherits its IEL's federation binding and witnessing. The
verifier surfaces the IEL's witnessing through the anchor edge: a SEL event counts only when its
anchoring IEL event is **witnessed** on the IEL's canonical branch (the IEL's own
`witnessed_anchors` —
[`../iel/verification.md`](../iel/verification.md#federation-witnessing-in-verification)). So
content-fork prevention on a witnessed SEL **rides the IEL's witnessing floor**: a witnessed SEL
content fork would force two IEL content siblings at one IEL position, which the IEL's floor
prevents — the SEL needs no witness gate of its own. The witnessing mechanics are federation
doctrine — [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md)
(forthcoming); **the data decides, witnessing propagates.**

## Streaming

SEL verification follows the cross-primitive streaming pattern — the verifier walks page by page
rather than loading the full chain into memory, resolving each event's IEL anchor as it goes.

### Constructors

- **`SelVerifier::new(prefix, &owner_iel_token)`** — start from inception; full verification of an
  untrusted chain against its IEL's verified token.
- **`SelVerifier::resume(prefix, &SelVerification, &owner_iel_token)`** — resume from a verified
  token (the merge handler's normal-append fast path); it re-runs the to-tip cross-layer checks
  against the new tip whenever the IEL moves, so a SEL is never advanced past an IEL recovery it did
  not re-read ([§Walk semantics](../../../../protocol-doctrine.md#walk-semantics)).
- **`SelVerifier::from_branch_tip(prefix, &BranchTip, &owner_iel_token)`** — resume from a specific
  branch tip, for verifying against a specific branch in divergence / recovery.

### Paginated verification helper

`completed_verification(loader, prefix, owner_iel_token, page_size, max_pages, content)` pages
through a `PageLoader`, calling `truncate_incomplete_generation()` at page boundaries so a divergent
generation spanning two pages re-fetches rather than being processed half-observed. Returns a
trusted `SelVerification`. `max_pages` prevents resource exhaustion (default 64 pages ≈ 8K events;
configurable).

## Per-event check summary

| Property                      | Verification method                                                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| SAID / prefix integrity       | Re-derive from canonical bytes with the placeholder; compare to declared (inception re-derives the prefix from `owner` / `topic` / `data`).  |
| Event chaining                | `previous` resolves to a verified prior event; each `Gnt` / `Trm`'s `previousSeal` resolves to the prior local seal.                         |
| Serial monotonicity           | Each event's serial equals the previous + 1; inception is serial 0.                                                                          |
| Cross-layer anchor edge       | The anchoring IEL event is of the matching kind, attributable, and live; the SEL event extends the latest anchored tip.                      |
| Anchor-monotonicity           | Extend the latest IEL-anchored tip; skip-unattributable; a re-anchor at an attributed serial is inert.                                       |
| Cross-layer deadness-descends | A SEL event on a dead IEL anchor (below the IEL's seal) is dead, its subtree with it.                                                        |
| Down-pin floor                | A serial-1 v1's `pin` equals its anchoring IEL event's `previous`; each `Ixn` re-pins forward.                                               |
| Manifest roles                | The `manifest` carries only roles in the kind's allowlist (`content` on `Ixn`, `grant` on `Gnt`, `anchors` on `Trm`; none on `Icp` / `Pin`). |
| Authentication rides the v1   | The serial-1 v1 resolves to a real event on the claimed owner's IEL (`anchor.prefix == owner`, `v1.previous == said(Icp)`).                  |
| Lookup-SEL derivation         | Blind-recompute the prefix two-pass from `Icp{owner, topic, data}`; fetch by prefix; confirm the `Trm` anchor.                               |

## Cross-references

- [`../event-shape.md`](../event-shape.md#sel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind SEL field grid.
- [`log.md`](log.md) — chain primitive: states, the seal-advancers, the down-pin, the IEL clock.
- [`events.md`](events.md) — per-kind reference: the three axes, the cross-layer anchor matrix, the
  lookup-SEL shape, the `Trm` kill.
- [`merge.md`](merge.md) — merge handler routing: how the verifier output composes with the merge
  gate; anchor-monotonicity; cross-layer deadness-descends.
- [`reconciliation.md`](reconciliation.md) — cross-layer correctness proof; the theorem.
- [`../iel/verification.md`](../iel/verification.md) — the IEL verifier whose token delivers each
  SEL event's count, liveness, and witnessing; the `kills[]` forward-match.
- [`../kel/verification.md`](../kel/verification.md) — the KEL verifier the IEL resolves down to.
- [`../../sad/said.md`](../../sad/said.md#derivation) — the two-hash prefix / SAID derivation a
  lookup SEL blind-recomputes.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#verification-tokens-as-proof-of-verification)
  — verification tokens; [§Walk semantics](../../../../protocol-doctrine.md#walk-semantics);
  [§Structural problems error; everything else is reported](../../../../protocol-doctrine.md#structural-problems-error-everything-else-is-reported);
  [§Negative checks are positive lookups](../../../../protocol-doctrine.md#negative-checks-are-positive-lookups).
- [`../../../policy/documents.md`](../../../policy/documents.md) — the feature layer that interprets
  a matched kill (the fail-secure revocation / rescission read).
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the IEL's witnessing floor the SEL inherits.
