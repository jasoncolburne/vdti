# SEL Verification — Verifier Walk

The SEL verifier walks a chain from inception to tip, validating structural integrity (SAID, prefix,
chain linkage, per-kind field rules), **owner-rooting** (the SEL authenticates by resolving down to
its owner-IEL anchor), the SEL's **own witnessed divergence**, the **severance** a dead owner-IEL
anchor causes, and — for a re-establishable value lookup — the **lineage walk**. It returns a
verification token, `SelVerification`, that downstream consumers hold as proof-of-verification.

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
  kind-first (a `payload` role only on `Ixn`, a `grant` role only on `Gnt`, an optional `bound` role
  only on `Trm` — the gated rescind-doc; no manifest on `Icp` / `Pin` / `Sea`) and the
  `previousSeal` presence rule (present on `Gnt` / `Trm` / `Sea`, forbidden on `Icp` / `Ixn` /
  `Pin`).
- Serials start at 0 and increment by 1 with no gaps; the inception `Icp` has serial 0 and a valid
  prefix (re-derived from the canonical bytes — the populated `owner` / `topic` / `data`, plus
  `content: true` on a content SEL and `lineage` on a re-establishable value lookup — with `said` /
  `prefix` set to the placeholder), carries no `pin` and no manifest, and is **never itself
  anchored** (its serial-1 v1 is).
- **The `content: true` flag matches the v1's tier — the biconditional.** A content SEL, whose v1 is
  `Ixn` / `Pin` (tier 1), carries **`content: true`** on its `Icp`; a lookup SEL, whose v1 is a
  `Gnt` or `Trm` (tier 2), carries **no** `content` flag. A SEL whose flag and v1 tier disagree — a
  v1-T1 without `content: true`, or a `content: true` with a v1-T2 v1 — is **invalid** and rejected.
  Because the flag rides the whole-content prefix, content and lookups derive to **different
  addresses**, so a content squat at a value's lookup address is impossible by construction
  ([§The lineage walk](#the-lineage-walk)).
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
    if event.kind == Ixn:  assert event.manifest has payload (>= 1 SAD)   # Ixn payload is required

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
    if event.kind == Ixn:  record payload SADs
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
available — stays terminal. A `{Trm, content}` fork with a severed branch likewise keeps the
survivor (a severed content leaves the `Trm` → Terminated). The full enumeration is
[`reconciliation.md` §Matrix 2](reconciliation.md#matrix-2-axis-a-crossed-with-axis-b-the-load-bearing-matrix).

## The lineage walk

A **re-establishable value lookup** — a published value re-establishable at a fresh address after a
rescission (a KEM receive-key) — carries a `lineage` counter and is resolved by a **positive walk**
over its own lineage chain. The walk is **meaning-blind** (topic opacity) — it reads chain state,
never what the value is _for_:

```
resolve_lookup(owner, topic, data):                       # a re-establishable value
    for n in 0 ..= MAXIMUM_SEL_LINEAGE:                   # lineage: 0, 1, 2, …
        sel = fetch(derive(owner, topic, data, lineage = n))
        if sel is absent:            return (not established, at lineage n)   # a gap ends the walk
        if lineage_n_dead(sel, n):   continue          # advance — a Trm on n's chain / Disputed / severed,
                                                        #   OR n's lineaged target in the owner's fresh kills[]
        return sel                                        # STOP — the lowest live lineage (Active / Forked)
    return (no live instance, fail-secure)                # past the cap
```

- **`Trm` advances.** A `Trm` on `lineage: n` kills **that lineage**, not the address, so the walk
  advances to `lineage: n+1`. A rescinded value is re-established by re-incepting at the next
  lineage, so a live key stays reachable at a discoverable address.
- **Any non-dead reading stops — `Forked` included.** Only `Trm` / Disputed / severed advance the
  walk; `Active` and `Forked` stop and return their reading (a `Forked` locus reads fail-secure).
  This is the anti-equivocation property too: anything above a live lineage is inert, so an
  equivocation attempt fails safe.
- **Contiguous from `lineage: 0`.** A gap — an absent lineage — ends the walk; a value is never
  established above an absent one.
- **The cap `MAXIMUM_SEL_LINEAGE = 64`** bounds the walk; past it there is no live instance, which
  reads fail-secure.

**The positive walk consumes the per-lineage negative check — one act, not two mechanisms.**
`lineage: n` reads dead when a `Trm` sits on its own SEL chain (Disputed or severed count too)
**or** its **lineaged** target `hash('{topic}:{owner}:{data}:{lineage}')` is present in the owner
IEL's **fresh** `Rev` / `Dth` `kills[]` — the fail-secure, un-withholdable authority
([`../iel/verification.md` §The kills forward-match](../iel/verification.md#the-kills-forward-match)).
So a value's **positive** resolution — "what is the live value?" — has no owner-IEL fallback (the
SEL's own live state is the authority, and a disputed or severed lineage is a real denial), yet its
**negative** per-lineage check — "is `lineage: n` killed?" — **does** consult that lineaged
`kills[]`. Both hold; they are not a contradiction. A **monotone kill** (a cred revocation, a
delegate / doc-member rescission) carries a **non-lineaged** target instead — the killed thing has
no lineage — and is read the same way, the O(1) `{Icp, Trm}` read (present → killed) with the
fail-secure `kills[]` walk behind it; it has no lineage chain to advance across, so a verified `Trm`
present → **killed** (a Disputed locus included). A non-re-establishable value is a single monotone
read at its own address.

**The lineaged target is a feature-layer obligation the primitive does not backstop.** The
un-withholdable leg — `lineage: n`'s **lineaged** `kills[]` target on the owner IEL — protects the
walk only when the value-lookup rescission actually **declares that matching lineaged target**.
Because `kills[]` is opaque to the IEL (it never dereferences a target), no primitive check can
assert that a value rescission's anchoring `Dth` carries the lineaged target for **this**
`(owner, topic, data, lineage)`; a rescission declaring only an on-chain `Trm`, or a non-lineaged /
wrong-lineage target, would leave the kill on the **withholdable** leg (a node missing lineage `n`'s
`Trm` reads it live and serves a stale value). So it is a **stated, load-bearing feature-layer
invariant**: every value-lookup rescission carries the matching lineaged `kills[]` target on the
witnessed IEL, constructed against the rule through the primitive-composition helpers (the helper
lands with the value-lookup feature). The primitive **consumes** the lineaged target when present;
it does not manufacture or require it.

**Content is neither walked nor negative-checked.** A content SEL is **handed**, and `content: true`
gives it its own address namespace — so it can never occupy a lookup address (the acceptance
biconditional, [§What verification ensures](#what-verification-ensures)). The
value-vs-kill-vs-content split is **structural** (the `content` flag and the `lineage` field's
presence), read without any tier-check on the read path.

## `SelVerification` token

`SelVerifier::into_verification()` produces a `SelVerification` token — the proof-of-verification
type (in the field shapes below, `Vec<T>` is a list, `Option<T>` an optional value, and
`BTreeSet<T>` a sorted set):

```
SelVerification:
    prefix: String
    owner: String                          # the owner IEL prefix (Icp-only, immutable)
    topic: String                          # the application discriminator
    content: bool                          # the content discriminator (true iff the Icp carries content: true — a v1-T1 content SEL); a lookup's Icp omits the flag
    lineage: Option<u32>                    # Some(n) only on a re-establishable value lookup; None on content or a monotone lookup
    kind_class: SelClass                    # content SEL vs kill-lookup vs value-lookup
    branch_tips: Vec<BranchTip>            # one per branch (1 = linear, >1 = the SEL's own divergence)
    divergence_ancestor: Option<SAID>      # SAID of v_{d-1} on a divergent chain; None on linear
    severed_at: Option<SAID>                # the last live-anchored event when a dead owner-IEL anchor truncates the chain
    last_seal_advancing_event: Option<SAID>  # the derived seal: the most recent Gnt / Trm / Sea that landed cleanly
    owner_anchor_per_event: ...            # per-event owner-IEL anchor (kind + liveness)
    payload_saids: BTreeSet<SAID>          # payload SAD SAIDs recorded on the canonical branch
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
- `is_killed(locus)` → the kill-lookup read (the fail-open fast path at the monotone address; the
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

| Property                | Verification method                                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SAID / prefix integrity | Re-derive from canonical bytes with the placeholder; compare to declared (inception re-derives the prefix from `owner` / `topic` / `data` / `lineage`).                                                                                                                                                                                    |
| Event chaining          | `previous` resolves to a verified prior event; each seal-advancer's `previousSeal` resolves to the prior seal.                                                                                                                                                                                                                             |
| Serial monotonicity     | Each event's serial equals the previous + 1; inception is serial 0.                                                                                                                                                                                                                                                                        |
| Owner-rooting           | The serial-1 v1 resolves to a real owner-IEL event whose prefix equals `owner`; each event authorized by the anchor's threshold.                                                                                                                                                                                                           |
| Kind-strict anchoring   | The anchoring owner-IEL event is the matching kind (`Ixn` / `Ath` / `Rev` / `Dth` / `Evl`); tier-elevation is an added floor, not the check.                                                                                                                                                                                               |
| Severance               | A SEL event on a dead owner-IEL branch severs the chain at the earliest dead anchor.                                                                                                                                                                                                                                                       |
| Down-pin floor          | A serial-1 v1's `pin` equals its anchoring IEL event's `previous`; each `Ixn` re-pins forward.                                                                                                                                                                                                                                             |
| Manifest roles          | The `manifest` carries only roles in the kind's allowlist (`payload` on `Ixn`, `grant` on `Gnt`; none on `Icp` / `Pin` / `Sea`; a `Trm`'s manifest is opt — the `bound` role, a feature-layer gated rescind-doc). An `Ixn`'s manifest is **required** (≥ 1 `payload` SAD) — a manifest-less `Ixn` is malformed (a pure re-pin is a `Pin`). |
| Witnessed divergence    | The SEL's own first-seen at `(prefix, serial)`; two accepted sealed branches → disputed.                                                                                                                                                                                                                                                   |
| Lineage walk            | A re-establishable value's positive walk over its own lineage chain: walk `lineage: 0, 1, …`; a dead lineage (a `Trm` on its chain / Disputed / severed, or its **lineaged** `kills[]` target) → advance, a live one → stop; a gap ends it; cap `MAXIMUM_SEL_LINEAGE = 64`. A monotone kill uses a non-lineaged target; content is handed. |
| `content: true` ⟺ v1-T1 | The verifier confirms the `Icp`'s `content` flag matches the v1's tier — a v1-T1 without `content: true`, or a `content: true` with a v1-T2 v1, is invalid. The flag rides the prefix, so content and lookups occupy distinct namespaces and the content squat is impossible by construction.                                              |

## Cross-references

- [`../event-shape.md`](../event-shape.md#sel) — cross-primitive event shape: common fields, the
  `manifest` model, `previousSeal`, the per-kind SEL field grid.
- [`log.md`](log.md) — chain primitive: states, the witnessed chain, the seal and its advancers,
  severance, the down-pin.
- [`events.md`](events.md) — per-kind reference: the three axes, the manifest roles, the anchor
  matrix, the lookup-SEL shapes, the content and lineage fields.
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
