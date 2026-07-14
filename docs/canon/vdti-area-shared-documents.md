# vdti — area note: Shared documents (collaborative, evolving, membership-governed)

**Status: SECOND CUT — crystallized with Jason 2026-07-03; dual-pass returned 2026-07-04 (warm HOLD-4 /
cold HOLD-with-findings — no BLOCKERs, the model verifies) and the findings are FOLDED here.** A **feature** over the SAD + SEL primitives: a
document several parties co-author, whose **membership and sharing evolve under a creator**, fully
end-verifiable — decentralized Google-Docs-with-sharing. **No new primitive.** **Supersedes the
first cut** (immutable `authors[]` + a per-author V0-content leg + folds + anchored-set attribution —
all retired); the review-hardened insights (claimed-vs-consent crediting, the size caps, the
residuals, the T1/T2 posture) **carry, re-homed**. The three prior review rounds reviewed the _first
cut_ — **this cut's fresh dual-pass is folded (2026-07-04).** Lands at
`docs/design/features/shared-documents/documents.md`.
**Invariants:** [inv 4] manifest roles / the `Rev`/`Dth` manifest total rule / anchor-monotonicity,
[inv 5] as-of = the anchoring position, [inv 8] the multi-source freshness bar (loss-of-trust reads),
[inv 10] negative-check-as-lookup, [inv 12] IEL self-pricing (grant tier), [inv 13] rescission `bound`
/ grandfather boundary / deadness-ascends, [inv 15] inception + attribution, [inv 16] addressing by
prefix + the custody `owner`+`topic`+SEL-anchor note (2026-07-03). Feature-layer precedent:
`document-policy §F` (the to-tip freshness step is mandatory for any trust-granting acceptance).

## Sources

- This session's design conversation (the collapse onto attributed SADs; membership-as-access-list;
  the backdate resolution via a member-IEL honored window; period-scoped re-add).
- The first-cut model + its three review rounds — `archived/vdti-multi-party-review-*`,
  `archived/vdti-document-authorship-thoughts-*`. Those reviewed the retired V0-leg model; the
  surviving insights are carried below, re-homed. The obsolete findings (V0-leg, folds, anchored-set)
  do not.
- Grounded in the landed SAD layer (`sad/{sad,custody,said,compaction}.md`), the SEL primitive
  (event-shape / area-sel), the delegation `bound` (delegation §5 / inv 13).

## The model in one paragraph

A shared document is **a DAG of _attributed_ SADs (versions), authored by **editors** whose
membership is a _creator-governed, per-period access list_.** The creator governs three document roles —
**view** (the document `readPolicy`), **comment** (`commenters[]`), **edit** (`editors[]`, who author
versions) — the Google-Docs triad; commenting is reserved, its mechanism deferred (§7). Each version is
a primitive attributed
SAD — `custody { owner, topic, readPolicy }`, owner-rooted by its own
`derive(owner, DOC_TOPIC, version_said)` SEL exactly like any bare SAD, so authorship is **provable
and non-repudiable** (only the editor's `t_use` produces it). **Membership is not delegation** — an
editor acts as _itself_, never with the creator's authority — it is an **access list** the creator
maintains on a doc-governance SEL: a **grant** opens a validity _period_ on the editor's own IEL
(`from` = the editor's IEL tip at grant), and a **rescission** — a period-scoped lookup-SEL carrying
a `bound` on the editor's IEL — closes it. A version by editor X (anchored at X-IEL position `V_x`) is
**honored iff `V_x` falls in some open period on X's own IEL** — `F ≤ V_x`, and `V_x ≤ B` when the
period is closed at a rescission bound `B` (else unbounded above) — an **intra-chain, append-only,
clock-free** test, so a removed or compromised editor **cannot backdate** into an old membership
state. Because rescissions are keyed **per-period** by `derive(creator, DOC_RSC_TOPIC, hash(G | said_b))`
— `G` the grant-doc's canonical SAID, `said_b` the nonce'd entry SAID — and **never** the participant
prefix, a removed participant **can be re-added** (a fresh grant → a new period) and the key is
**participant-blind AND grant-blind** (§5). Freeze = the creator
bounds every member **and** `Trm`s the governance SEL (structural, hard — §1). The feature is a
**verification layer** over primitives: primitive-verify each version, then check period-membership
(with the loss-of-trust freshness bar, inv 8) + DAG placement + read-invariance.

## 1. The construct

- **V0 → the doc prefix (the constitution + the doc's identity).** V0 is the genesis SAD (the DAG
  root), and — like a chain inception — it **derives a doc `prefix`** (nonce'd → unguessable for a
  private doc). **The doc is a DAG feature identified by that prefix, not a chain**; everything
  references the **doc prefix**, and event SAIDs are **uncorrelatable** to it (the prefix ≠ said
  discipline, `said.md` — the correlation a shared KERI-style identifier does not avoid). V0 carries:
  - **`creator`** — the creator IEL **prefix** [inv 7]: governs membership + sharing (may be
    multi-device/threshold; multi-admin is §7).
  - **the reserved topics** — a holder derives the governance chains from the **doc prefix**: the
    governance SEL `derive(creator, DOC_GOV_TOPIC, doc_prefix)`, per-period rescissions
    `derive(creator, DOC_RSC_TOPIC, hash(G | said_b))` (§Rescission; the full topic strings are in §7).
  - **`readPolicy₀`** — the initial read/sharing gate (custody; evolution §5).
  - **`nonce`** — high-entropy so the doc prefix (hence the governance / version chains) is unguessable
    for a **private** doc; a public doc may omit it.
  - V0 is **anonymous-write** (the shared constitution; no `owner`), so its legitimacy is
    social/out-of-band — a competing V0′ is always mintable (§4).
- **Membership is delegation-style unbounded; the only cap is adds-per-grant (Jason 2026-07-04).** A
  **live-set cap is the wrong tool** — knowing the live count would require resolving **every**
  rescission, which defeats the per-participant O(1) model. So membership works like **delegation**
  (delegation §1/§2): the total is **unbounded**, resolved **per-participant by direct lookup** — a
  version's honored-check reads its pinned grant `G_x` (governance SEL) + one rescission
  (`hash(G | said_b)`, O(1)), **never** a materialized live set. The **one amplification bound** is
  **`MAXIMUM_GRANT_ADDS = 64`** (generous, because the total is unbounded): a grant's `editors` +
  `commenters` add-lists total **≤ 64 per grant event**, enforced **as the verifier walks** (accumulate
  the event's adds; the instant it breaches 64, **bail**). Nothing else needs bounding — the
  governance-SEL length and the per-participant period count are the creator's own cost, cost-symmetric
  (warm F11 / cold N4).
- **Member names live in gated content, never in public structure (the core privacy discipline).** A
  SEL's structural fields (`owner` / `data` / manifest-role values) are witnessed → **public**, so a
  member prefix in any of them leaks. Every member reference is therefore a **readPolicy-gated content
  SAD** named by an **opaque SAID** from the event's `manifest`; the public chain carries only the
  opaque commitment (the inv-16 private-data pattern).
- **Governance SEL — the creator's access-list + sharing log.**
  `derive(creator, DOC_GOV_TOPIC, doc_prefix)`, owner = creator, `Icp` data = doc_prefix. Records:
  - **grants** — a SEL **`Gnt`** (the doc-membership grant kind, T2, `t_authorize`) anchored by the
    creator's IEL **`Ath`**; the `Gnt`'s `manifest` names a **gated grant-doc** `G`, submitted as
    **compacted chunks** (top level all canonical SAIDs — the canonical/fully-compacted form is the one
    everyone commits to, always re-derivable by compacting down; `project_vdti_compacted_only_submission`):
    `G = { said, kind, custody{ readPolicy }, editors, commenters }`, where `editors`/`commenters` are
    role-list SADs `{ said, kind, add:[ entry-SAID, … ] }` and each entry is a nested SAD
    `{ said, kind, <role>, from, nonce, custody{ readPolicy } }` (`<role>` = an `editor`/`commenter` IEL
    prefix; `from` = the period start). The **`nonce` (high-entropy) makes each entry SAID `said_b`
    unguessable** on public structure — a participant-blind commitment (the area-sel data-entropy rule at
    the feature layer; a low-entropy entry would be a brute-force oracle — §5). The **`Gnt` event's SAID
    `G_x`** (public on the governance SEL) **identifies the validity period** — it commits the editors,
    commenters, and their `from`-positions. Multiple grants for a participant = multiple periods (re-add).
    **One uniform rule for per-participant and batch grants:** the rescission handle is the nonce'd entry
    SAID `said_b` (below). _(The grant's `custody.readPolicy` gates the grant-doc itself; the **document**
    read gate — who may **view** the doc — is the separate, evolving `readPolicy`, §5.)_
  - **sharing changes** — `readPolicy` updates (§5).
  - A grant is a **T2 creator-governance act** (`Gnt` ← `Ath`, `t_authorize`, reserve-backed):
    a compromised creator _signing key_ (T1) **cannot** mint one — minting reveals a rotation preimage (the
    MFA elevation). Mechanically this is the **`Ath` merge** (`Del` generalized to carry `delegates` **or**
    a grant `anchors`→`Gnt`) — §7 for the full resolution. (cold N2: SELs are not secret-bearing; the
    minter would be a compromised T1 key, which T2 now rules out.)
- **Rescission — period-scoped membership removal (reuses the §5 `bound` mechanism, not the delegate-prefix cap).** To
  remove participant b's period: a rescission SEL keyed `derive(creator, DOC_RSC_TOPIC, hash(G | said_b))`
  — `G` the grant-doc's canonical SAID, `said_b` the nonce'd entry SAID — `{Icp, Trm}`, the `Trm` carrying
  **`bound = b-IEL@B_b`** in a **gated rescind-doc** (participant + bound behind the read gate).
  Present → that period is closed at `B_b`; absent → open. A negative-check-as-lookup (inv 10): O(1),
  per-period. **The key is participant-blind AND grant-blind, computable, non-reversible (folds cold F1 /
  warm F1 — the earlier "unguessable to a witness" claim was false):**
  - **participant-blind** — the member prefix is **never** a derivation input; the input is `hash(G |
    said_b)`, and `said_b = said({nonce_b, prefix_b})` is unguessable via `nonce_b`. So a witness (which
    _does_ hold member prefixes — the version-SEL v1 anchors on the editor's IEL, §5) **cannot
    brute-force candidate members** to confirm one. This is the property the review found load-bearing.
  - **grant-blind** — a witness **holds `G` and `G_x`** (both public — the grant-doc SAID and the
    governance `Ixn` SAID it witnesses), so "a witness can't derive it" was false as first written; but
    it does **not** hold `said_b` (nonce'd, inside the gated grant-doc), so it **cannot compute `hash(G |
    said_b)`** → can't even link the rescission to its grant. This **beats** a bare `{doc_prefix, G_x}`
    key, which a witness _could_ recompute for every `G_x` → leaking which grant each rescission closed.
  - **computable by a reader** — an authorized reader holds `G` (public) and `said_b` (from the gated
    grant-doc it can read) → derives and looks up. **Re-add** rides for free: a fresh grant → new `G` →
    new `said_b` → a new period key.
  _(Per-period keying is the deliberate divergence from the **delegation**-rescission's permanent-prefix
  cap (inv 15 R3-3) — it is what lets a removed participant be **re-added**. Two encoding notes vs
  delegation: (1) the `bound` rides the **gated `bound` role** on the SEL `Trm` (behind the read gate), not
  delegation's **inline-public `kills[].bound` field** — one concept, two custody modes, the shared name
  intentional — because a bound SAID is **participant-identifying by matching** (a witness holding the editor's IEL matches
  the SAID against its events, no inversion), so it can't sit on public structure (warm F8). (2) the `Trm`
  seals at **`Dth`** — with `delegate → authorize`, the slot is the general "authorize a party
  to act" lifecycle, and doc-membership rides it both ways: **add** via `Ath` (a `Gnt`),
  **remove** via `Dth` (this `Trm`). A `Rev`/`Dth` forces a `Rot`, so each removal is a **`t_authorize`
  ceremony — cost-symmetric with the grant** (both T2 / `t_authorize`); the asymmetry is now **finality**
  (the grant is additive / walkable-forward, the rescind a monotone terminal kill), not threshold. (Undoes
  the earlier `@govern`, forced only because `delegate` was too specific — cold F8 / warm F7.)_
- **Version — a primitive attributed SAD (the custody primitive, not a bespoke shape — Q2/F5).**
  `custody { owner = the editor's IEL prefix, topic = DOC_TOPIC, readPolicy = the current gate }` — and
  because custody lives **only** on standalone SADs (`custody.md`: chain events carry no custody slot), a
  version _is_ a custody-attributed standalone SAD, so the primitive fixes its shape: owner-rooted by its
  `derive(owner, DOC_TOPIC, version_said)` SEL (`data = version_said`), a short **`{Icp, Pin}`** SEL
  whose **`Pin` (the serial-1 v1) is anchored** by the editor's IEL `Ixn` at position `V_x` — the
  version's **as-of** (append-only). _(The `Icp` is never anchored — it rides `v1.previous`, inv 15; the
  `Pin` is the anchored v1, not a redundant floor. No `{Icp, Ixn}` content-on-a-log variant — that
  couldn't carry `custody`; no `{Icp, Trm}` seal variant — nothing consumes a version SEL past v1, and a
  `Trm` would move the as-of onto a `Rev` position, defeating the cheap-`t_use` authorship.)_
  The version SAD carries: a high-entropy **`nonce`** (private docs — so `version_said` is unguessable on
  public structure, §5), the **doc prefix** (doc-scoping + governance lookup, direct — no `ancestors[]`
  walk to root), the **authorizing grant `G_x`** (the period this version claims — reveals nothing new,
  the reader already holds `owner`; it lets the honored-check name a specific period, §Period-lifecycle),
  **`ancestors[]`** (parent version SAID(s), the DAG), and an advisory **`edited`** timestamp (feature,
  on the SAD, never the chain — inv 6). Nothing grows, no folds.
- **The honored predicate — the load-bearing check.** A version by X at `V_x` is **honored iff** its
  **pinned grant `G_x`** names a period with `from = F_x` and — letting `B_x` be that period's rescission
  bound (or open) — **`F_x ≤ V_x ≤ B_x`**. `F_x`, `V_x`, `B_x` are **all positions on X's own IEL**, so
  the test is **intra-chain, append-only, structural — no clock, no self-asserted pin.** _Backdate closed
  both ways: X can only append forward on its own IEL, so a post-removal version is past `B_x`; and X
  cannot make an old, immutable IEL event anchor a new version._
  - **Endpoint provenance (cold F3):** `F_x` and `B_x` are **creator-chosen referents into X's chain** —
    the membership authority's dial, _not_ structurally the tip-at-grant. The backdate argument rests on
    X's append-only chain, not on where `F`/`B` sit, so it holds regardless: a garbage `F_x` matches no
    version (fail-secure); a deep `F_x` retro-honors within creator authority.
  - **The open-by-absence read is FAIL-SECURE again (warm F4 → B1 fail-secure rework 2026-07-09).** `B_x`
    **absent → open** is answered like delegate rescission (area-delegation §1, inv 10): the doc-membership
    rescission is a **`kills[]` declaration on the creator's witnessed IEL `Dth`** + a `{Icp, Trm}` lookup SEL, with
    `target = hash('{DOC_RSC_TOPIC}:{creator}:{hash(G | said_b)}')` — the doc's existing **per-period,
    participant-/grant-blind** key `hash(G | said_b)` as the `data` (**kept, not retargeted to `said(Gnt)`** — flag #4
    resolved), so the target is safe in public. So honoring an open-period version **walks the creator's fresh IEL and
    forward-matches the `target`** — a stale / withheld view **can't** hide a closure (a hidden rescission needs a
    stale IEL, which the multi-source / witnessed bar (inv 8) already refuses — **REFUSE** on an unconfirmable read;
    the grant's governance SEL freshness rides the same bar). **Fail-secure by default.** *(This makes the **freeze
    version-stopper hard again** — cold F3; the earlier best-effort / `attribute-all` reclassification is dropped,
    cold/warm re-review-2 F1.)* **The bound `B_x` is GATED, not public** (unlike a delegate's public bound): a bound
    is **participant-identifying by matching** (a witness holding member `b`'s IEL would de-anonymize `b`), so
    `kills[]` carries **only the blind `target`** and the `B_x` lives in a **gated rescind-doc *committed by the
    rescission `Trm`'s `bound` role*** (so this `Trm` legitimately commits a manifest, R3; the "`Trm` carries only its
    pin / self-contained walk" phrasing is cred+delegate, not doc-member). The walk detects the rescission from the
    (un-gated) `target`, then **fetches** the gated rescind-doc for `B_x` (an authorized reader already holds it) →
    **withheld → conservative (don't honor)** — the narrow price of participant-blindness (flag #4). **Walk lower
    bound (R3/cold F6):** a `Dth` before this period's grant `G_x` existed can't rescind it, so the fresh-IEL
    forward-match runs `[G_x-anchor .. tip]` (a sound floor, not a lossy cap). **Asymmetry KEPT:** once `B_x` exists it
    is set-once / sealed, so **closed periods are freshness-insensitive** (fail-closed) — and now the
    open-by-**absence** read is fail-secure too.
- **Periods for a participant must be disjoint — enforced at doc-validation, not the SEL walk (Q1, folds cold
  F3's retroactive-`from` + the double-grant open).** A version pins its authorizing grant; the creator
  **may author** a retroactive or overlapping grant (a structurally-valid SEL event — the SEL walk does
  not reject it), but **doc-validation rejects a doc whose editor's periods overlap** on that editor's
  IEL. So a retroactive `from` (re-covering a rescinded window) or a plain double-grant (a fresh grant
  while a period is still open) makes the doc **invalid** — the creator _can_ author it, they just
  **break the doc**. Re-add stays valid because its periods are **disjoint** (`F₂ > B₁`,
  rescind-then-regrant). The "end-verifiability, not pristine data" posture: don't prevent the authoring,
  catch the broken state deterministically at validation (Jason 2026-07-04).
- **State = the version DAG** — possibly multiple tips; forks are legal and **presented**, never
  picked. Convergence = a multi-parent merge (a version whose `ancestors[]` names competing tips).
  Canonical = a **tag** (a feature assertion, itself an edit — tags can conflict; the app arbitrates).
- **Freeze — hard, structural.** Two distinct jobs: the creator **bounds every member** (closes all
  open periods → no `V_x` can fall in an open window → no new version honored — the version-stopper,
  per-participant intra-chain) **and** `Trm`s the governance SEL (blocks re-grant → makes it **permanent**,
  the irreversibility). Bound-all alone stops versions; `Trm`-governance alone does **not** (open
  periods stay open). Unfreeze = reincept to V0′.
- **Crediting is claimed-vs-consent (carried, cold-2 F5).** A grant _names_ a member, but credit only
  a member with ≥ 1 **honored** version — a malicious creator can _grant_ a non-consenting party but
  can't manufacture their `t_use`-signed versions. The grief of being _named_ is unmitigable (social,
  not structural); the rule gates _crediting_, not _naming_.

## 2. Attribution, self-location, and the work cap

- **Provable authorship (the point of the collapse).** Each version is `owner`-committed and
  owner-rooted by the editor's own SEL, so authorship is non-repudiable — anchoring proves
  _authorship_, not mere endorsement. (The first-cut anchored-set walk couldn't tell originator from
  endorser; this can.)
- **Self-location — inv-16-clean, all by-prefix (with V0 in hand — cold F6 / warm F10).** A **holder
  holds V0** (the constitution — it derived the doc prefix, so any V0-claimant self-authenticates against
  it), and V0 supplies `creator` + the reserved topics. The doc prefix **scopes**; V0 supplies the
  derivation inputs — the prefix alone is an opaque hash and yields nothing (the earlier "doc prefix →
  creator" arrow implied a derivation that doesn't exist). Then derive the governance SEL
  `derive(creator, DOC_GOV_TOPIC, doc_prefix)` (walk for the version's grant + `F_x`) and the period
  rescission `derive(creator, DOC_RSC_TOPIC, hash(G | said_b))` (→ `B_x` or open). No SAID is inverted;
  "no walk to the DAG root" means governance needs no `ancestors[]` resolution.
- **Work cap — per-version + hard size caps (carried, cold-2 F2 / cold-3 B1).** Attribution is
  per-version primitive verification (real author work, one `t_use`/version — not amplifiable). The
  floodable cost is `ancestors[]` resolution (an inline list): **O(1) set-membership** of each parent
  against the **built version set** (the versions the verifier holds — discovery is peer/availability-side,
  there is no registry, so completeness is availability, not structure; cold N5), never a recursive
  ancestor walk; dangling-parent fetches **bounded** (backoff → give-up → flag deferred). Hard size caps
  (inv-14 pattern, verifier rejects over-cap):
  **`|ancestors|`/version**, **grants/governance-step**. A junk flood denies **only the flooder's own
  placement**.

## 3. Two "forks" — don't conflate them

- **SEL-chain fork** (two events at one SEL serial) — **prevented by the SEL's own witnessing** (first-seen
  at its `(prefix, serial)`, inheriting the owner IEL's federation — witnessed-SEL redesign, area-sel §1c;
  the FIRST-CUT "forbidden by the cross-layer divergence model" rested on the retired theorem). So each
  version SEL and the governance SEL are **linear on a witnessed chain** — a fork needs witness collusion,
  reads Forked (fail-secure), and is buried by a SEL `Sea` (area-sel §1d).
- **Version fork** (two versions naming the same `ancestors` parent) — **allowed/presented**; the DAG
  branches at the document layer over linear SELs. Acyclic by SAID (a cycle = a Blake3 preimage
  cycle).
- **A editor's IEL divergence is handled by two composed rules, not one (cold F2 / warm F3).** A
  divergent editor's IEL **reads suspect** — _not_ "is compromised" (the data can't diagnose intent; a
  benign two-device race is a recoverable content fork, resolved first-seen — area-iel §5) — and a version
  anchored above that IEL's seal reads suspect until the IEL resolves (the seal-boundary rule, inv 13).
  - **The anchor edge severs the SEL (witnessed-SEL redesign, area-sel §1e).** If the IEL resolves with the
    version's v1 anchored in a **dead** (non-canonical) member event, the version SEL is **severed** at that
    anchor — dead + un-verifiable from there (no repair to re-root; the surviving IEL branch is a different
    author). _(The FIRST-CUT "dies by cross-layer deadness-descends via the cross-layer theorem" is
    superseded — the theorem is retired; inherited IEL deadness severs the SEL, area-sel §1e.)_
  - **DAG descent is _this feature's own_ rule, derived as a placement consequence — not inv 13/17.**
    `ancestors[]` is a feature-layer, **multi-parent** edge; deadness-ascends is defined only over
    `previous`-linkage and the IEL→SEL anchor edge, so claiming the primitives provide descent down the
    DAG over-reaches. The semantics still hold, by **placement**: a version places only against **live
    parents in the built version set** (§2), so a dead parent is not in that set → its descendants are
    **unplaceable**. `ancestors[]` is SAID-committed, so re-parenting = **re-authoring** on a live version
    — the content re-issue analog. On a merge with one dead and one live parent, the child is unplaceable
    (**any dead parent drops it**) and editing **re-authors from a live (canonical) version** — Jason
    2026-07-03: "their tails also die; they re-edit from a live part of the dag." Structural language
    throughout — canonical / non-canonical / dead, never "adversary."

## 4. Trust posture

- **External parties** can't inject/alter versions (owner-rooting + the honored window) or brick the
  doc (a junk flood denies only its own leg, §2).
- **A editor's T1 (signing-key) compromise is bounded + recoverable — and the bound is the operator dial
  (cold F4).** The attacker authors valid attributed versions **as that member** within its open period;
  they linger (durable, route-around-able). Recovery: the **creator rescinds the compromised period**,
  and **where the `bound` cuts is the operator's choice, not forced by inv 13.** The `bound` is the
  sanctioned wholesale retroactive lever (inv 13: "nothing past the bound is honored — grants _and_ kills
  alike"), so the creator chooses along the editor's chain:
  - `bound = detection tip` grandfathers **all** honored work including the attacker's in-window versions,
    stopping only future ones;
  - `bound = last-good event` (inv 4's own recipe — "the last honoured event") un-honors the malicious
    window at the cost of any honest same-window versions.
  That trade — honest collateral vs malicious survival — **is** the recovery decision, not something inv
  13 forecloses; "no retroactive distrust" is reserved for what inv 13 actually forbids (a quorum's
  **per-event self-history** un-trust, the backdate kill-switch). After the bound, the creator **re-adds**
  the member on a fresh **disjoint** period once it rotates the bad device out of its own IEL. Bounded,
  recoverable, **no whole-doc reincept.**
- **Creator-side divergence is the symmetric leg — Kill-sealing gives it a clean asymmetry (cold F5).**
  During the creator IEL's own divergence the doc reads suspect by the same seal-boundary rule. **Grants
  are now T2 (`Gnt` ← `Ath`) → `Ath`-sealed, sealed-on-arrival, non-buriable** (inv 13: a sealed
  event is never buried below a later seal), **same as** the rescission and governance `Trm`s. So **both** the
  additive act (a grant) and the monotone acts (a removal, a freeze) survive a burial — a rogue grant below a
  post-compromise tip can't be silently buried; it forces **reincept**. Walking back a grant is
  therefore **rescind-forward** (`Dth`), never an in-chain undo. The asymmetry that remains is
  **finality-shaped, not threshold**: a grant is additive (the SEL continues; walk it back by rescinding), a
  kill is terminal (monotone, un-undoable). _(Re-granting after a rescission is the retroactive-`from` case —
  caught by the disjoint-periods rule at validation, §1.)_ (This supersedes the earlier "grants are T1
  content `Ixn`s / a grant can be walked back by a repair" — grants became T2 at the tier resolution, §7.)
- **Creator (governance) compromise, or a rogue/unrecoverable creator → reincept the whole
  document.** A compromised creator can grant rogues, rescind honest members, or freeze — the
  governance locus is captured. Action: honest parties **abandon and reincept a fresh V0′** (new
  creator/constitution) seeded from the last good version; the old DAG stays verifiable.
  **Successor-auth is out-of-band** — nothing structural links V0′ to V0 (by design; a competing V0″
  is always mintable; legitimacy is social). Only the creator's compromise is whole-doc; members'
  are editor-local (above).

## 5. Custody, sharing, and privacy

- **`readPolicy` = the document read (view) gate** — evaluated current-mode at fetch by the store. It is
  **read-set invariance (integrity), not confidentiality** (carried, cold-2 F1 / cold-3 S2): a co-author
  can always read + exfiltrate; the rule keeps the _canonical_ DAG's read-set uniform, it does not hide
  bytes. **For confidentiality, encrypt** (a forward direction). **Two distinct `readPolicy`s (Jason
  2026-07-04):** the one inside a grant's / entry's `custody` gates **that gated doc itself**; the
  **document** read gate — who may **view** the doc content — is **separate and evolves**. Because it is
  integrity, not confidentiality, sharing is a **light axis** (§7): the creator publishes read-gate
  updates as **cheap T1 `Ixn`s** on the governance SEL, and a version declares the gate it was authored
  under; a read-invariance mismatch is **presented-but-flagged, app-arbitrated**, never a structural
  un-honor.
- **Attribution is opt-in-visible; privacy via the read gate.** A version carries `owner` (provable
  authorship) but read-gated — so `owner` is exposed only to authorized readers. Revealing authorship
  is the deliberate cost of _proving_ it; the private default hides it behind `readPolicy`.
- **The co-authorship + membership graphs close for a private doc.** A version SEL `Icp` carries
  `data = version_said` (a nonce'd, gated reference), and the version→V0 linkage rides read-gated
  `ancestors[]` — so a witness sees `(member, version_said)` pairs but **cannot group them by document**
  for a **private** doc; the strong on-chain co-authorship graph is **closed** (a public doc's graph is
  readable anyway). The **membership graph closes** because the rescission key is `hash(G | said_b)` —
  **participant-blind** (no member prefix as input) **and grant-blind** (a witness can't compute it without
  the gated `said_b`), so a witness can't even link a rescission to its grant, let alone its member.
  Given the grant records are read-gated for a private doc, a witness sees only **`creator ↔ doc`**
  (unavoidable — the governance SEL derives from `doc_prefix`) plus grant/rescission **volume-timing**.
- **The stated residual, completed (cold F9 / warm F9).** For a mesh witness the residual is
  `creator ↔ doc` **plus**: (a) **per-participant `DOC_TOPIC` volume-timing** — the `(member, version_said)`
  pairs above, and the **topic** itself (a version SEL `Icp` is recomputable content carrying
  `(owner, topic, data)`, so a witness learns _"member X authors shared-doc versions"_, unlinkable
  to a doc absent an oracle); (b) **cross-participant timing correlation** of version-SEL activity (co-editing
  clusters — the same inv-16 volume-timing class); (c) grant/rescission volume-timing. It is **never
  _who_ the members are** — the same inv-16 residual class accepted everywhere else, not the graph.
- **Every gated doc on public structure needs its own `readPolicy` AND a high-entropy nonce (warm F2 —
  the offline confirmation-oracle, a MAJOR the review found missable).** A parent's `readPolicy` does
  **not** transitively protect its referenced sub-SADs (`compaction.md` §Privacy contract). So the
  grant-doc's participant entries `{said, kind, <role>, from, nonce, custody}`, the rescind-doc
  `{<role>, bound}`, and a private
  doc's version SADs each carry **their own `readPolicy`** (else the content is publicly fetchable by
  SAID regardless of the parent's gate) **and a high-entropy `nonce`** (else the SAID is a **hash-match
  confirmation oracle** — compose candidate content, hash, compare the committed SAID; a member prefix +
  known `G` is candidate-composable). The store-side `denied ≈ absent` **cannot** defend a SAID already
  public on the chain — the entropy must be in the _input_ (the area-sel data-entropy rule at the
  feature layer; V0 already has its nonce by design). App-builder responsibility; the framework provides
  the per-SAD `readPolicy` + the nonce slot.
- **Content off-node — submit the SELs, hold the content (the sovereignty mode).** A participant may
  submit only the **SEL chains** (version, governance, rescission — pure opaque structure, witnessed)
  and **never land any content SAD** (versions, grant/rescind docs) on the node; the content is held
  on-device and shared peer-to-peer (exchange/mail, §9). This composes because **the node's role is
  chain-only** — chain validity + witnessing are content-independent (inv 17), and every feature check
  (membership window, DAG placement, the honored predicate) is **participant-side**, run by whoever
  holds the content. So the node hosts a fully opaque chain and **nothing content-readable** (the
  governance `Icp`'s `data = doc_prefix` and the version-SEL `(owner, DOC_TOPIC, version_said)` are
  structural — cold N1). Two tiers, a per-doc choice: **content off-node** (max privacy; participants
  bear availability) or **content on-node but gated** (`readPolicy` + nonce'd SADs — node availability,
  the mesh-correlation residual). **Feature invariant: no node operation may require a content SAD**
  (§7) — and the encode must add an **off-node carve-out to deferred-deps (warm F12):** a
  permanently-off-node anchored SAD is an **opaque commitment, never a pending dependency** (the existing
  `MissingSadObject` park/drain, vdtid-services §1h, predates off-node mode and would park-forever
  otherwise).

## 6. Credentials vs shared documents — two types, one substrate

|            | Credential (policy layer)                        | Shared document (this feature)                            |
| ---------- | ------------------------------------------------ | --------------------------------------------------------- |
| parties    | `issuer`(s) + an `issuee` — **asymmetric**       | a **creator** + **members** — governed, symmetric members |
| membership | fixed at issuance                                | **creator-governed, evolving** (grant / bound / re-add)   |
| policy     | authorizing + acceptance conditions              | none except `readPolicy` (the read/sharing gate)          |
| content    | frozen (single version)                          | evolves (the version DAG)                                 |
| kill       | revocation `Trm` (`Rev`)                | per-participant period-bound; **freeze** = bound-all + `Trm`-gov |
| home       | `primitives/policy/documents.md`                 | `features/shared-documents/documents.md`                  |

Shared substrate: documents are **attributed SADs** (`owner`+`topic`+SEL-anchor), located by
`derive`, in a DAG; membership reuses the §5 grandfather-`bound` mechanism. They specialize
differently and are **not** merged.

## 7. Resolutions + what actually stays open

_(2026-07-04: the dual-pass findings are folded into §1–§5; the remaining design opens are run down
and **resolved** below. Only one value and one landed-doc fix are left, at the bottom.)_

- **Grant tier — RESOLVED (Jason 2026-07-04): a grant is a T2, `t_authorize`, reserve-backed
  authorization — NOT a T1 `Ixn`.** `Ixn` uses `t_use` (inv 12), the everyday signing key — too weak for
  a who-is-authorized change, and forcing `t_use ≥ 2` breaks the common single-device case. A grant is an
  **authority-grant** (inv 15 F-I → **T2, reserve-backed** = the MFA/2FA elevation): minting one reveals a
  rotation preimage, so a compromised creator _signing key_ alone cannot mint one. Everyday
  version-authoring stays `t_use` (can be 1).
  - **Mechanism — merge `Del → Ath`, add one SEL kind `Gnt` (the grant's own footprint: `+Gnt` in the SEL, `Del`→`Ath` in the IEL; the concurrent `Kil`→`Rev`/`Dth` split is a separate taxonomy cleanup — "Rides with it" below).** The IEL **`Del`** is
    renamed/generalized to **`Ath`** — the unified T2 "authorize a party to act" anchor (`t_authorize`) —
    carrying **two manifest roles, both permitted at once** (batchable; same cost):
    - `delegates` — IEL prefixes (the old `Del` job; the authorized party acts **for the delegator**).
    - `anchors` — the downstream SEL **`Gnt`** event(s) (the doc-membership grant; the authorized party
      acts **as itself** on the doc). Kind-strict: `Ath.anchors` names **only** `Gnt`s.
    The new SEL kind **`Gnt`** is the doc-membership grant — the **additive twin of the SEL `Trm`**
    rescission (T2, `t_authorize`, anchored by `Ath`, sealed-on-arrival / sealed),
    carrying the gated grant-doc `G` (editors/commenters + `from` periods).
  - **Why not reuse an existing anchor.** `Evl` and old-`Del` carry an **IEL-own-state delta**
    (`roster` / `delegates`) — reusing either says "the creator's _own_ identity governance changed,"
    which is false (a grant mutates a **downstream** SEL, nothing on the creator's IEL). A `Rev`/`Dth` is the right
    shape (no own-state delta; purely seals a downstream SEL effect at T2) but the wrong polarity (a kill).
    `Ath` is a `Rev`/`Dth` with the polarity flipped — additive, not terminal. Anchoring is **passthrough** (each
    IEL kind carries its SEL counterpart atomically): the matrix gains one pair, **`Ath ↔ Gnt`**, beside
    `Ixn ↔ content` and `Rev`/`Dth` ↔ `Trm`. A single parametrized `Anc(tier, threshold)`
    was considered and rejected — it would leave every governing IEL event anchoring nothing, forcing a
    second event per SEL side-effect (no passthrough → double events, broken atomicity, seal-cap pressure).
  - **No S1 reopened.** Both `Ath` roles price at `t_authorize`, so carrying both in one event is
    cost-uniform (like `Evl`'s `roster`+`anchors`); `delegates` is a directly-consumed role (kind→role gate
    is its guard), `anchors→Gnt` is additionally back-checked (a `Gnt` is valid only anchored by an `Ath`,
    like `Trm ← Rev`/`Dth`). **"Membership is not delegation" survives:** the manifest role is the semantic switch
    (act-for-X vs act-as-self); same anchor, distinct effects.
  - **Grants are non-buriable (bless — the one consequence).** A T2 grant is **sealed-on-arrival, not
    T1-buriable.** "Walk back a grant by a repair" is gone (there is no repair event); the replacement is
    **rescind forward** (`Dth`, already in the model), and a rogue grant below a post-compromise
    tip → **reincept** (like any rogue `Ath`/`Rev`/`Dth`) — but minting it needed the **reserve** in the
    first place, so a bare signing-key compromise can't produce one at all. A net strengthening, consistent
    with "don't relax finality; recover operationally." (Supersedes the §4-F5 "a grant can be walked back"
    line — corrected there.)
  - **Rides with it (canon-wide rename + kill-anchor split, folded this pass):** `Del → Ath`;
    `t_delegate → t_authorize`; the terminal-kill `Dec → Trm` (reads "terminate", pairs with `Icp` — Jason
    2026-07-04); and the single kill-anchor `Kil` **split into `Rev`** (revoke an owned artifact, `t_govern`)
    **and `Dth`** (deauthorize a grant, `t_authorize`), which **retires the `threshold` slot-name field** —
    every IEL kind now prices from exactly one slot (no count-parametrized kind). Propagated across
    inv 4/11/12/15 + area iel/sel/delegation/federation + the landed doctrine
    (`event-shape`/`protocol-doctrine`/`glossary`/`policy`) + `.terminology-forbidden`. The
    external-authorization lifecycle: **add** via `Ath` (delegate or grant), **remove** via `Dth` (rescind
    either — a SEL `Trm` anchored by `Dth`); a credential revocation is a **revocation-SEL** `Trm` anchored by `Rev`. Net
    taxonomy **at the 2026-07-04 grant-tier resolution:** **SEL 6→7** (`+Gnt`; `Dec`→`Trm` rename), **IEL 8→9**
    (`Del`→`Ath` net-0; `Kil`→`Rev`/`Dth` split `+1`; `Dec`→`Trm` rename) — *the later first-seen pivot dropped
    `Fld`/`Rpr`, so the current counts are **SEL 5** / **IEL 8***. The `del(X, N)` policy leaf, the `delegates` manifest role, and
    "delegation" the concept are **unchanged** (only the kind/count tokens rename).
- **Sharing (`readPolicy`) evolution + read-invariance outcome (was warm F14, RESOLVED).** `readPolicy`
  is **read-set integrity, not confidentiality** (§5 — a co-author can exfiltrate regardless), so sharing
  is a **light axis**: the creator publishes `readPolicy` updates as **cheap T1 `Ixn`s** on the
  governance SEL (no membership-style freshness / backdate machinery — sharing is not trust-granting),
  and a version declares the `readPolicy` it was authored under. A **read-invariance violation is
  presented-but-flagged, app-arbitrated** (the canonical DAG's read-set uniformity, like a canonical
  tag) — **not** a structural un-honor, because a wrong-gate version is still a validly-authored version.
- **Reserved names + SAD schemas — DEFINED (2026-07-04, with Jason).** Convention
  `vdti/<concept>/v1/<category>/<thing>` (from the KEL kinds + `.terminology-forbidden`); concept **`doc`**.
  - **SEL topics** (`derive(owner, topic, data)`): `vdti/doc/v1/topics/version` (owner = an editor,
    data = `version_said`), `vdti/doc/v1/topics/governance` (owner = creator, data = `prefix`),
    `vdti/doc/v1/topics/rescission` (owner = creator, data = `hash(G | said_b)`). _(The `DOC_TOPIC` /
    `DOC_GOV_TOPIC` / `DOC_RSC_TOPIC` shorthands used in §1.)_ The grant `Gnt` is anchored by **`Ath`**, and
    the `rescission` (a SEL `Trm`) by **`Dth`** (add the rows at encode).
  - **Doc SADs** (`vdti/doc/v1/schemas/*`; every SAD carries `kind`; **`custody` is inline** — no `said`,
    so it can't be compacted away, the SAD's authority travels with it):
    - `inception` (V0): `{ said, kind, prefix, creator, custody{ readPolicy }, nonce? }`
    - `version`: `{ said, kind, custody{ owner, topic, readPolicy }, prefix, grant, ancestors[], content, nonce?, edited? }`
    - `grant` — the **grant-value** the `Gnt` seals: kind **`vdti/sel/v1/grants/shared-document-governance`**
      (the `grants/*` convention shared with exchange, ≤ 64 chars; the generalized seal-a-typed-value `Gnt`,
      area-sel §1b / `vdti-area-exchange`) — `{ said, kind, custody{ readPolicy }, editors, commenters }`, two
      role lists + the grant's own gate
    - `editors` / `commenters`: `{ said, kind, add:[ entry-SAID, … ] }` (the role lists)
    - `editor` / `commenter`: `{ said, kind, <role>, from, nonce, custody{ readPolicy } }` — `<role>` (= `editor`
      or `commenter`) is that participant's IEL prefix; `said` = `said_b` (the rescission handle); `from` = `F`
    - `rescind`: `{ said, kind, custody{ readPolicy }, <role>, bound, nonce }` — `bound` = `B`
  - **Comments — reserved, design DEFERRED.** `vdti/doc/v1/schemas/comment` + `vdti/doc/v1/topics/comment`
    are reserved but unspecified (commenting resolves / threads / references a version-range — future work).
    The `commenters` list is used now (the grant's second role array); the comment *mechanism* is not.
  - **Prefix-naming rule:** an unqualified **`prefix` = the chain/DAG the document is part of** (the doc's own
    prefix); every **external prefix is named by its role** (`editor`, `commenter`, `creator`, `custody.owner`)
    and documented as an IEL prefix — never a bare `prefix`, no `ielPrefix` qualifier. The only primitive SAD
    referenced is `vdti/sad/v1/schemas/policy` (the `readPolicy` DSL doc).
- **Gated-doc shapes — settled (§1); field layout is encode-mechanical (RESOLVED).** Grant-doc
  `G = {said, kind, custody{readPolicy}, editors, commenters}` (role lists of nonce'd `{said, kind, <role>,
  from, nonce, custody{readPolicy}}` entries); rescind-doc `{said, kind, custody{readPolicy}, <role>, bound,
  nonce}`; rescission key `hash(G | said_b)`. The precise field layout is above; JSON lands at encode.
- **Node-never-needs-content — VERIFIED + the off-node carve-out (was warm F12, RESOLVED).** Witnessing
  (over `(prefix, serial, event-said)`), merge (chain events), and chain-validity (the SEL walks) are all
  **chain-only**; every feature check (window, DAG placement, honored predicate) is **participant-side**.
  So no node op requires content — the off-node mode (§5) holds. The one **build** rule: the drain loop
  treats a permanently-off-node anchored SAD as an **opaque commitment**, never a park-forever
  `MissingSadObject` (vdtid-services §1h) — a checked property at build, not a design open.
- **Multi-admin — scoped (RESOLVED).** The **creator is a single IEL** (which may be
  multi-device/threshold internally — that covers a multi-key admin). **Co-equal separate-identity
  admins** (a governance threshold over distinct identities) is a **deliberate extension** — it needs a
  governance policy over identities (the `issuers[]` / policy-over-`id()` pattern), out of scope for this
  cut, not a gap.
- **Periods-per-participant — no cap (RESOLVED).** Each candidate period is one O(1) rescission lookup, and
  re-adds grow the creator's own governance SEL (cost-symmetric). Unbounded is fine; no inv-14 cap.
- **Doc-prefix derivation — reuses the primitive (RESOLVED).** V0 is a **prefix-deriving SAD**: the doc
  prefix is the standard **chain-inception two-hash** derivation (`said.md` §Chain inception) over V0's
  whole content **including its `nonce`** (unguessable for a private doc), with **`prefix ≠ said`** so
  event SAIDs don't correlate to the doc prefix (inv 16). Nothing bespoke.

**Deferred to the encode / future — scheduled, nothing to decide:**

- **`compaction.md` + `said.md` §Rule 1 SAID-invariance fix** — the truth is settled (one **canonical
  (fully-compacted) SAID**; references commit to it; a verifier re-derives it by compacting any form
  down — it must stay derivable from the data). A landed-doc correction to make at the next encode. See
  §8 + memory `project_vdti_said_form_dependent`; the `.working/` canon is grep-clean of the false claim.
- **Comments mechanism** (resolve / thread / version-range refs) — names reserved
  (`vdti/doc/v1/schemas/comment` + `topics/comment`), design deferred to future work.

## 8. Drift → land

- Write `docs/design/features/shared-documents/documents.md` fresh from this note (greenfield voice;
  credentials as the _contrast_). Forward-ref from `primitives/policy/documents.md` + the SEL
  primitive.
- Depends on the landed custody `owner`+`topic`+SEL-anchor model (inv 16 note) and the §5
  rescission-`bound` mechanism.
- **Encode-voice (cold N3 / warm N3):** the §5 first-cut-relative framing and the `cold Fn`/`warm Fn`
  citations throughout are working-note bookkeeping — restate every property in **absolute** greenfield
  terms at encode; drop "decentralized Google-Docs-with-sharing" (brand analogy).
- **Landed backport (warm F5, folded 2026-07-04):** `custody.md`'s "the SEL's inception is anchored"
  spans are corrected to "the v1 (`Pin`) is anchored, the `Icp` rides `v1.previous`" (inv 15) — same
  change, landed-docs-current rule. And the `compaction.md`/`said.md` SAID-invariance fix (§7).

## 9. Content confidentiality → the exchange feature

The off-node / private-content confidentiality thread — a per-doc symmetric key (AES-256-GCM) wrapped to
each member's published KEM receive key, re-key on removal for forward secrecy, key epochs aligned to the
honored `[from, bound]` membership periods (one notion of "since when," not two), tiered PQ crypto — is
**re-homed to `vdti-area-exchange`**: shared documents is a **consumer** of exchange. A doc's private
content is delivered member-to-member as **ESSR** payloads sealed to each member's receive key; re-key =
seal a fresh key to the **remaining** members (the past can't be un-shared — a co-author keeps what they
already read). Open items — group-key-on-a-SEL, re-key cadence, epoch commitment — live in the exchange
note (§7 there).
