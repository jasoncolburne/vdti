# SEL Verification — Verifier Walk

The SEL verifier walks a chain from inception to tip, validating structural integrity (SAID, prefix,
chain linkage, per-kind field rules), **owner-rooting** (the SEL authenticates by resolving down to
its owner-IEL anchor), the SEL's **own witnessed divergence**, the **severance** a dead owner-IEL
anchor causes, and — for a lookup SEL — the uniform **lineage walk**. It returns a verification
token, `SelVerification`, that downstream consumers hold as proof-of-verification.

Like an IEL event, a SEL event carries **no adjacent signature of its own** — it authenticates by
its owner-IEL anchor
([`../event-shape.md` §Authentication & signatures](../event-shape.md#authentication--signatures)).
So the SEL verifier's authority check is a **two-layer down-walk**: for each SEL event, resolve the
owner-IEL event that anchors it, confirm that IEL event carries the required count (drawn from the
owner IEL's threshold vector by the SEL event's kind), and let the IEL verifier resolve that count
down to member KEL signatures. The SEL never re-does the IEL's threshold arithmetic — it consults
the owner IEL's verification token. Fork-prevention, by contrast, is the SEL's **own** witnessing at
its own position, not the anchor's.

This doc states the walk algorithm, owner-rooting, the witnessed divergence read, the severance
read, the lineage walk, and the token surface. For per-kind reference, see [`events.md`](events.md);
for chain lifecycle, [`log.md`](log.md); for merge-layer routing, [`merge.md`](merge.md); for the
correctness proof, [`reconciliation.md`](reconciliation.md).

## What verification ensures

For every event the verifier walks, it ensures:

- Events match their kind-specific schemas (required and forbidden fields per the
  [event-shape reference](../event-shape.md#sel)), including the `manifest` role allowlist read
  kind-first (a `content` role only on `Ixn`, a `grant` role only on `Gnt`; no manifest on `Icp` /
  `Pin` / `Trm` / `Sea`) and the `previousSeal` presence rule (present on `Gnt` / `Trm` / `Sea`,
  forbidden on `Icp` / `Ixn` / `Pin`).
- Serials start at 0 and increment by 1 with no gaps; the inception `Icp` has serial 0 and a valid
  prefix (re-derived from the canonical bytes — the populated `owner` / `topic` / `data` / `lineage`
  — with `said` / `prefix` set to the placeholder), carries no `pin` and no manifest, and is **never
  itself anchored** (its serial-1 v1 is).
- All event prefixes match the chain's prefix; all events have valid SAIDs; events chain via
  `previous`; each seal-advancer's `previousSeal` resolves to the prior seal (the spine).
- **Owner-rooting** — the serial-1 v1 resolves to a real event on the claimed owner's IEL, and each
  event is authorized by the threshold its anchoring IEL event carries.
- **The anchor is live** — a SEL event anchored on a dead owner-IEL branch severs the chain (§The
  severance read).
- The down-`pin` floors to the owner IEL: a serial-1 v1's `pin` equals its anchoring IEL event's
  `previous`, and each `Ixn` re-pins forward.

## Walk algorithm

The verifier processes events in a single forward pass, verifying structure, the owner-IEL edge, and
the SEL's own divergence simultaneously. Events must arrive in canonical order
`(serial ASC, kind sort_priority ASC, said ASC)` with complete generations. A **generation** is the
set of events at a given serial; a fork forks per-branch state — when a second distinct event
appears at the same serial, the verifier records the divergence ancestor and tracks both branches
independently. Such a fork is the SEL's own (an owner can equivocate its SEL even under a linear
owner IEL —
[`log.md` §The SEL is its own witnessed chain](log.md#the-sel-is-its-own-witnessed-chain)).

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
    if event.kind in {Gnt, Trm, Sea} and event.previousSeal != branch.last_seal:
        return Error("Spine back-link mismatch")

    # 5. Owner-rooting (the down-walk) + liveness
    anchor = resolve_owner_iel_anchor(event)         # the owner-IEL event naming this SEL event
    if anchor is on a dead owner-IEL branch: sever here            # inherited owner-IEL deadness → sever
    verify_kind_strict(event.kind, anchor.kind)      # Ixn<-Ixn, Gnt<-Ath, Trm<-Rev/Dth, Sea<-Evl
    verify_count(event.kind, anchor, owner_iel_token)  # the owner IEL delivers the count

    # 6. Floor + role consumption
    if event.kind != Icp:  assert event.pin floors to the owner IEL (v1: == anchor.previous)
    if event.kind == Ixn:  record content SADs
    if event.kind == Gnt:  record the grant-value
    if event.kind == Trm:  record the kill (its anchor, its committed target)
```

The verifier checks the **manifest role vocabulary** here — a manifest carrying any role outside the
kind's allowlist is malformed and rejected. As a lightweight structural guard, an owner-IEL anchor
naming a SEL event at an **already-attributed** SEL serial is treated as malformed → inert;
fork-prevention itself is the SEL's own witnessing, not this rule, which survives only for a node
validating without full witnessing state.

## Owner-rooting — the authentication check

A SEL's `Icp` is unsigned, recomputable content, so it proves nothing on its own — a fabricated bare
`{Icp}` naming a victim owner is **not** evidence the owner authored anything. A SEL is validly
established **only** if its **serial-1 event (its v1)** resolves to a real event on the **claimed
owner's** IEL: the v1 is named in that IEL event's `anchors`, its `pin` links to the anchoring
position, and the anchoring IEL prefix equals the SEL's `owner`. A SEL whose v1 is absent, or whose
v1-anchor sits on a different owner, is rejected. The `Icp` rides via `v1.previous`; it is **never
itself anchored**.

This is the SEL's end-verifiability barrier and it is **independent of the witness**: a witness
gates structure, first-seen, and threshold, but the consumer re-derives the SEL prefix and re-checks
the anchor against the data it holds — trusting the data, not the witness. For a private lookup SEL
whose `Icp` is never published, the witness never holds the `Icp` body (and must not — else a
credential secret would reach it), yet the owner-signed anchor still closes authorship-forgery
whether or not the witness can derive the prefix
([`log.md` §The SEL is its own witnessed chain](log.md#the-sel-is-its-own-witnessed-chain)).

## The witnessed divergence read

The SEL's own divergence is read data-locally, exactly as the KEL and IEL read theirs, but at the
SEL's own `(prefix, serial)`:

- **A live content fork** — two content events at one position — reads **Forked**. It forms only
  under witness compromise (first-seen prevents an honest one), reads fail-secure, and is resolved
  by a burying seal-advancer.
- **A `{Trm, content}` divergence** reads **Terminated** by tier-rank — the sealed `Trm` wins, the
  content buries.
- **Two or more accepted sealed branches** read **Disputed** — a data-local walk over the accepted
  (that is, witnessed-at-threshold) sealed branches counts two, which requires provable witness
  collusion. A witness-declined sealed sibling is not accepted and never counts.

An accepted sealed event is one witnessed at threshold **and** on a live lineage — a branch off a
first-seen loss is dead on ascent and never counts. The witness beacon **propagates** the competing
branch SAIDs so a one-branch holder fetches the rest; the data-local walk **decides** the verdict.

## The severance read

The verifier's second divergence input is inherited from the owner IEL. When it resolves a SEL
event's owner-IEL anchor to an event on a **dead** owner-IEL branch — one the owner IEL has buried —
it **severs** the SEL at that anchor: the anchored event and everything after it are dead and
un-verifiable, because they were anchored **through** the buried IEL lineage and there is no repair
event to re-root them. The verifier truncates the SEL to the last live-anchored event and reads that
shortened chain's state.

**Deadness comes first.** A content fork with one severed branch auto-resolves to the live branch
(no burying seal-advancer needed); a Disputed with one severed branch downgrades to the live branch
(the severed branch is not counted). A Disputed under a **linear** owner IEL — no severance
available — stays terminal. The full enumeration is
[`reconciliation.md` §Matrix 2](reconciliation.md#matrix-2-axis-a-crossed-with-axis-b-the-load-bearing-matrix).

## The lineage walk

A lookup SEL is located by recomputing its prefix, and a re-incepted one is located by walking its
lineages. The walk is **uniform and meaning-blind** — it never inspects what the SEL is _for_ (topic
opacity):

```
resolve_lookup(owner, topic, data):
    for n in 0 .. MAXIMUM_SEL_LINEAGE:        # 64
        sel = fetch(derive(owner, topic, data, lineage = n))   # lineage 0 omits the field
        if sel is absent:            return (not established, at lineage n)   # a gap ends the walk
        if sel reads dead (Disputed / severed):  continue      # advance to the next lineage
        if sel reads live or validly Terminated: return sel    # STOP here
    return (no live instance, fail-secure)     # past the cap
```

- **Contiguous from zero** — a gap ends the walk (also the anti-equivocation property: anything
  above a live one is inert, so an equivocation attempt fails safe).
- **`Terminated` is a STOP, not a DEAD.** A kill lookup's `Trm` is its **success** — the locus was
  killed. Treating a `Terminated` locus as dead and advancing past it would walk past a real
  revocation to an empty lineage and read not-revoked — a **fail-open** hole. So `Terminated` stops
  the walk.
- **The cap `MAXIMUM_SEL_LINEAGE = 64`** bounds the walk; past it there is no live instance, which
  reads fail-secure.

The walk is uniform, but the _need_ differs by semantics at the feature layer, never in the
verifier. A **monotone kill** has an authoritative fail-secure fallback on the owner IEL, so its
fail-open fast path is a single fetch at lineage zero (any `Trm` present → killed, a disputed locus
included), and it never advances — a dead kill locus stays at lineage zero. A **value lookup** — a
published value whose own live state is the sole authority — has no fallback, so a disputed or
severed locus is a real denial and the `lineage` walk is what re-establishes the value at a
discoverable address.

## `SelVerification` token

`SelVerifier::into_verification()` produces a `SelVerification` token — the proof-of-verification
type (in the field shapes below, `Vec<T>` is a list, `Option<T>` an optional value, and
`BTreeSet<T>` a sorted set):

```
SelVerification:
    prefix: String
    owner: String                          # the owner IEL prefix (Icp-only, immutable)
    topic: String                          # the application discriminator
    lineage: u32                            # this instance's lineage (0 when the field is absent)
    kind_class: SelClass                    # content SEL vs kill-lookup vs value-lookup
    branch_tips: Vec<BranchTip>            # one per branch (1 = linear, >1 = the SEL's own divergence)
    divergence_ancestor: Option<SAID>      # SAID of v_{d-1} on a divergent chain; None on linear
    severed_at: Option<SAID>                # the last live-anchored event when a dead owner-IEL anchor truncates the chain
    last_seal_advancing_event: Option<SAID>  # the derived seal: the most recent Gnt / Trm / Sea that landed cleanly
    owner_anchor_per_event: ...            # per-event owner-IEL anchor (kind + liveness)
    content_saids: BTreeSet<SAID>          # content-SAD SAIDs recorded on the canonical branch
    grant_value: Option<SAID>               # a value lookup's live grant-value (the live sealed tip)
    kill: Option<KillStructure>             # a kill lookup's Trm: its anchor kind (Rev / Dth) + committed target
    structurally_valid: bool               # the structural-validity result (owner-rooting, linkage, anchor kinds)
    competing_branch_saids: Vec<SAID>      # the branch tips of a detected divergence (the beacon enumerates these)
    witnessed: bool                        # threshold-many federation receipts at the SEL's own position

BranchTip:
    tip: SelEvent                          # chain head (latest event on this branch)
    pin: SAID                              # the owner-IEL position this branch floors to
```

Token fields are private with no public constructor — the only way to obtain one is through
`SelVerifier`. Holding the token proves the corresponding chain was verified against its owner IEL
and its own witnessing.

### Derived accessors

- `owner()` → the owner IEL prefix (a consumer resolves it to walk the owner for authority and
  liveness).
- `kind_class()` → content SEL, kill lookup, or value lookup.
- `grant_value()` → a value lookup's live sealed value (the served tip; a retired value never
  surfaces).
- `is_killed(locus)` → the kill-lookup read (the fail-open fast path at lineage zero; the
  authoritative fail-secure `kills[]` walk is the feature layer's —
  [`../iel/verification.md` §The kills forward-match](../iel/verification.md#the-kills-forward-match)).
- `is_terminated()` → `true` when the tip is a `Trm`.
- `is_divergent()` → `branch_tips.len() > 1`.
- `is_severed()` → `severed_at.is_some()`.
- `region()` → the consumer-facing trust region computed **data-locally**: **trusted** (no live
  fork), **forked** (a content fork awaiting a burying seal-advancer), or **disputed** (two or more
  accepted sealed branches — terminal). A severed branch drops out before this is computed.
- `effective_said()` → a fingerprint of the node's held state: a **single confirmed tip yields that
  tip's SAID** (the `Trm` SAID when terminated); a chain with **no single tip** yields a
  **type-tagged synthetic recoupled to the verdict** (`forked` / `disputed`), qualified by prefix
  and position, **not** a digest over the competing tips (that set is adversarially extensible →
  flood-unstable). A buried content branch and a severed portion both drop out. See
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

## Federation witnessing in verification

The SEL is its **own** witnessed chain, so the verifier surfaces witnessing at the SEL's own
position. Full mechanics live in
[`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) (forthcoming); this
section names what the SEL verifier reads. **The data decides; witnessing propagates.**

- **`witnessed`.** A SEL event is witnessed when the required threshold of the owner IEL's
  federation signs it **at the SEL's own `(prefix, serial)`** — the SEL inherits the owner IEL's
  federation and witness-config, and witness selection is deterministic on the SEL position and the
  inherited roster. The batched owner-IEL anchor makes acceptance also require owner-authorization,
  so witnessing closes both equivocation and authorship-forgery.
- **The divergence signal.** When a node holds two or more accepted sealed branches at the SEL's own
  position, it reads **disputed** directly — the walk decides. A sealed sibling held only as a
  receipt, or below threshold, is not counted.
- **Privacy.** Witnesses see the SEL's structural fields — including a lookup SEL's prefix — over
  the encrypted mesh, an acceptable trust-infrastructure exposure (federation members only,
  unguessable prefixes → confirm-a-known-subject at most, and a private lookup SEL's data-bearing
  `Icp` is never published).

## Streaming

SEL verification follows the cross-primitive streaming pattern — the verifier walks page by page
rather than loading the full chain into memory, resolving each event's owner-IEL anchor as it goes.

### Constructors

- **`SelVerifier::new(prefix, &owner_iel_token)`** — start from inception; full verification of an
  untrusted chain against its owner IEL's verified token.
- **`SelVerifier::resume(prefix, &SelVerification, &owner_iel_token)`** — resume from a verified
  token (the merge handler's normal-append fast path); it re-runs the to-tip severance and
  divergence checks against the new tip whenever the owner IEL moves, so a SEL is never advanced
  past an owner-IEL burial it did not re-read
  ([§Walk semantics](../../../../protocol-doctrine.md#walk-semantics)).
- **`SelVerifier::from_branch_tip(prefix, &BranchTip, &owner_iel_token)`** — resume from a specific
  branch tip, for verifying against a specific branch in divergence or recovery.

### Paginated verification helper

`completed_verification(loader, prefix, owner_iel_token, page_size, max_pages, anchors)` pages
through a `PageLoader`, calling `truncate_incomplete_generation()` at page boundaries so a divergent
generation spanning two pages re-fetches rather than being processed half-observed. Returns a
trusted `SelVerification`. `max_pages` prevents resource exhaustion (default 64 pages ≈ 8K events;
configurable).

## Per-event check summary

| Property                | Verification method                                                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SAID / prefix integrity | Re-derive from canonical bytes with the placeholder; compare to declared (inception re-derives the prefix from `owner` / `topic` / `data` / `lineage`). |
| Event chaining          | `previous` resolves to a verified prior event; each seal-advancer's `previousSeal` resolves to the prior seal.                                          |
| Serial monotonicity     | Each event's serial equals the previous + 1; inception is serial 0.                                                                                     |
| Owner-rooting           | The serial-1 v1 resolves to a real owner-IEL event whose prefix equals `owner`; each event authorized by the anchor's threshold.                        |
| Kind-strict anchoring   | The anchoring owner-IEL event is the matching kind (`Ixn` / `Ath` / `Rev` / `Dth` / `Evl`); tier-elevation is an added floor, not the check.            |
| Severance               | A SEL event on a dead owner-IEL branch severs the chain at the earliest dead anchor.                                                                    |
| Down-pin floor          | A serial-1 v1's `pin` equals its anchoring IEL event's `previous`; each `Ixn` re-pins forward.                                                          |
| Manifest roles          | The `manifest` carries only roles in the kind's allowlist (`content` on `Ixn`, `grant` on `Gnt`; none on `Icp` / `Pin` / `Trm` / `Sea`).                |
| Witnessed divergence    | The SEL's own first-seen at `(prefix, serial)`; two accepted sealed branches → disputed.                                                                |
| Lineage walk            | Uniform, meaning-blind; dead → advance, live / validly-Terminated / absent → stop; cap 64.                                                              |

## Cross-references

- [`../event-shape.md`](../event-shape.md#sel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind SEL field grid.
- [`log.md`](log.md) — chain primitive: states, the witnessed chain, the seal and its advancers,
  severance, the down-pin.
- [`events.md`](events.md) — per-kind reference: the three axes, the manifest roles, the anchor
  matrix, the lookup-SEL shapes, the lineage field.
- [`merge.md`](merge.md) — merge handler routing: how the verifier output composes with the merge
  gate.
- [`reconciliation.md`](reconciliation.md) — the correctness proof.
- [`../iel/verification.md`](../iel/verification.md) — the owner-IEL verifier whose token delivers
  each SEL event's count and liveness; the `kills[]` forward-match the kill read consumes.
- [`../kel/verification.md`](../kel/verification.md) — the KEL verifier the owner IEL resolves down
  to.
- [`../../sad/said.md`](../../sad/said.md#derivation) — the two-hash prefix / SAID derivation a
  lookup SEL recomputes.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#verification-tokens-as-proof-of-verification)
  — verification tokens; [§Walk semantics](../../../../protocol-doctrine.md#walk-semantics);
  [§Negative checks are positive lookups](../../../../protocol-doctrine.md#negative-checks-are-positive-lookups).
- [`../../../policy/documents.md`](../../../policy/documents.md) — the feature layer that interprets
  a matched kill and a grant value.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation
  witnessing (forthcoming): the witnessing floor and first-seen the SEL inherits at its own
  position.
