# vdti — area note: KEL (Key Event Log)

**Status: FIRST CUT (2026-06-20).** The last primitive. **KEL barely changed in the reshape** — the three-tier
key-state machine is intact; the deltas are (a) the archiving kind's name, (b) the federation field split, and
(c) divergence scoped to `Ixn`. Audited against the post-reshape core + the canonical `event-shape.md` +
the archived VDTI-10 build. Load-bearing claims marked for the adversarial pass; nothing locks until it survives.
**Invariants referenced:** [inv 2] single-locus, [inv 3] layers-isolated, [inv 4] manifest-down/pin-up,
[inv 7] prefix-vs-SAID, [inv 11] tier, [inv 13] divergence-scoped-to-T1-content, [inv 14] federation/witnessing,
[inv 15] inception-tier.

## Sources audited (disposition)
- `vdti-log-primitive-reshape-design-pass.md` §1 (KEL taxonomy), §2.2 (anchor matrix), §4 (repair cascade —
  KEL `Rec`/`Ror` roles), §7 (federation fields, `Fcp`/`Wit` — `Fed` renamed/merged to `Wit`) + `inv 11`/`13`/`15` — **authoritative / current.**
- `docs/design/primitives/data/event-logs/event-shape.md` — **canonical but pre-reshape.** KEL field/kind
  shape is mostly current; **two field/kind facts are superseded** (§3 below). The land target for the doctrine phase.
- `archived/vdti-10-kel-primitive.md` (build kickoff) + `archived/vdti-10-kel-pending-items.md` — **mine the
  6-doc structure + three-state machine + locked-portion bound + seal cap** (§2); these survive the reshape.
  ⚠ the pending-items doc's `Rec`→`Rpr` rename (item 2) is **stale/reversed** by the reshape (§3).
- Memory `project_kels_two_key_roles` (tier roles). ⚠ `project_kels_ror_vs_rec` (the **kels** "Rec = reactive,
  locks the KEL" framing) **does NOT carry to vdti** — vdti `Rec` = **recover** (= repair on the KEL, reveals the
  recovery key, does not lock). Importing the kels meaning was the mistake this note corrects (§4).
- The six `kel/` docs landed via PR #11 — `event-shape.md` remains the shared shape reference.

## 1. Locked-candidate — the current KEL model
- **KEL = one device's key state.** The **root** primitive — self-authorizing, **no chain above it** [inv 2].
  It is the bottom layer: nothing anchors *into* a KEL; a KEL anchors the IEL above it via its members' KEL
  events [inv 3]. **`Icp` = T1** (the root is self-authorizing — there is no governance to establish) [inv 15].
- **8 kinds:**

  | Kind | Tier | Sig | Role |
  |---|---|---|---|
  | `Fcp` | T1 | single | **federation-infrastructure** inception (a federation witness KEL) — **self-attested, no `witnesses`** at genesis (can't commit to a federation IEL that doesn't exist yet), **single-federation** (§inv 14 / federation §1d — serves **one** federation; to serve another, spin up a new KEL). **Bound by founding:** its v=1 is a **`Rot` that anchors the federation IEL `Fcp`** (the federation inception marker — kind-strict, T2 ↔ T2) in the same atomic genesis batch — `Fcp`(v=0) → `Rot`(v=1). The witness is bound by being **named in the roster it founds / joins**, governed *into* the roster — **never self-bound** (it carries no user-style `{federation, federationPin}`). On an `Fcp`-rooted KEL a **`Wit` is federation governance** (it anchors the federation IEL `Wit`; the witness's own rotation), **never a user rebind** — `Fcp`-rooted = infrastructure, the `Icp`-rooted/user `Wit` is the rebind. Trust roots in the config-pinned `FEDERATION_IEL_PREFIX`. |
  | `Icp` | T1 | single | inception — the **alternative root** (vs `Fcp`); an **ordinary user KEL**. **Federation binding is optional (cold-5 C1a):** carries `federation`/`federationPin` to join an *existing* federation (**federated**), **or omits both for a direct-mode chain** (un-federated, unwitnessed — federation §1d); a later `Wit` may bind a direct-mode chain forward (witnessing starts from that event; the early range stays unwitnessed). **Never preceded by `Fcp`** (a chain has `Fcp → Rot` *or* `Icp`, never `Fcp → Icp`). |
  | `Ixn` | T1 | single | content; anchors SADs via `manifest` (≥1); **the divergeable kind** [inv 13]. |
  | `Rot` | T2 | single | rotation (reveals next signing key, commits new); **seal-advancing**. |
  | `Ror` | T3 | dual | proactive rotate-recovery (hygiene); rotates signing **and** recovery keys. |
  | `Rec` | T3 | dual | **recover** — the KEL's **repair** kind (the *same operation* as IEL/SEL `Rpr`, applied to the KEL): resolves `Ixn` divergence by archiving the losing branch. KEL-specific trait: it **reveals the recovery key** (hence dual-sig). It does **not** lock the chain. |
  | `Wit` | T3 | dual | **the one witness/federation kind — `Wit` anchors `Wit` (anchor-kind uniform; field-match facet-specific — Q3); IS the T3 rotation** (refreshes signing + recovery; `pins = Wit.previous`). On an **`Icp`-rooted user KEL:** the federation bind/**rebind** — carries `federation`/`federationPin`/`witnesses` **each present-iff-changed** (inv 18; **must change `federation` or `witnesses`** — a rebind carries `federation`+`federationPin`, a config change carries `witnesses`; a same-federation `federationPin`-only re-pin rides a body event, not a `Wit`; pure rotation is `Ror`; a no-op `Wit` is rejected); **anchors the IEL `Wit`** (kind-strict, T3 ↔ T3; field-match = `{federation, federationPin}`, C4). On an **`Fcp`-rooted federation witness KEL:** the governance rotation — **anchors the federation IEL `Wit`** (kind-strict, T3 ↔ T3; field-match = the **witness-config only**, *not* C4 — roster rides the manifest `Evl`-style). *(Was `Fed` — renamed/merged to `Wit`; the federation governance, formerly a witness `Ror` anchoring a federation `Wit`, is now this `Wit` directly. 2026-06-28.)* |
  | `Trm` | T3 | dual | terminal (terminate). |

- **Three-tier capability model** [inv 11]: T1 = signing key; T2 = + rotation preimage; T3 = + rotation+recovery
  preimages. The **old signing key is NOT a prerequisite** for T2/T3 — the rotation preimage reveals the new
  signing key. `Rot` single-sig; `Ror`/`Rec`/`Wit`/`Trm` dual-sig (new signing + recovery). The recovery key is
  a **break-glass reserve** for high-assurance ops — *not* a device-loss recovery (a lost device is rotated out
  at the IEL layer).
- **Divergence resolution is by tier** [inv 13]. Two rules: **(1) only `Ixn` (T1 content) is *archivable*** — a
  privileged (`Rot`/`Ror`/`Wit`/`Trm`) event is **never archived/overturned** (overturning a rotation resurrects a
  retired key); **(2) you never extend an adversarial event** — a repair extends only the submitter's own branch.
  Recovery is one archival-tail rule + a permission check (F6 below); the node-agnostic federation condition is
  **≥ 2 privileged branches → irreconcilable/disputed**.
- **Recovery scope (F6 — scope corrected 2026-06-22).** A repair resolves a divergence by **attaching at your last
  event and archiving the archival tail(s)** — and **you can NEVER archive a privileged (T2/T3) event** (a `Rot`
  makes the chain immutable below it). The `../kels` flaw was classifying `Rot` as *non-privileged*, so a `Rec`
  could *archive* a forked `Rot` (un-rotating — the backdating attack vdti exists to fix); vdti treats `Rot` as a
  **privileged branch**, kept-not-archived. So:
  - **Universal rule:** a `Rec` attaches at **your last event**, **retaining** your branch (the **retained tail**)
    and archiving every other branch (the **archival tail(s)** — there may be several; the adversary can submit
    divergent `Ixn`s and you archive all of them). Rule 2 is automatic (you extend *your own* branch). *Not* the
    common/divergence ancestor unless you authored nothing past it (then every branch is archival; with your `Ixn`s
    preceding the adversary's, recovering at the ancestor would archive **your own** content). The permission check
    is one question about the archival tails — **does any contain a privileged event (a `Rot`/`Evl`/`Ath`/`Rev`/`Dth`)?**
    - **No** — every archival tail is content (`Ixn`) → **permitted**: `Rec` at your last event archives them, then
      `Ror` forward. (Your retained tail may carry your *own* `Rot` — kept, not archived; only the archival tails are
      checked.) A T1 adversary can't counter a T3 `Rec`: **this is what the recovery reserve is *for* — it defends
      the *signing* key.** Bounded by the seal-cap — a content tail that fills the window forces a `Rot`, which puts
      a privileged event in an archival tail → reincept.
    - **Yes** — a `Rot` (forked or tip-appended), `Evl`, `Ath`, or `Rev`/`Dth` in any archival tail → **not permitted →
      reincept** (or, for a **delegated KEL, the delegator `Dth`s it**). You can't *archive* it (rule 1), *extend*
      it (rule 2), or *fork* it (`{Rot, Ror}` → ≥ 2 priv → terminal). **A `Rot` in an archival tail is the point of
      no return; the recovery reserve does *not* defend the rotation key** — "if the attacker rotates, they have
      your chain." *(This subsumes "≥ 2 privileged → terminal": you retain only your own branch, so a second
      privileged branch always lands in an archival tail. `{Rot, Rot}` is additionally a **confirmed reserve
      compromise** — two valid rotations reveal the *one* preimage at `v_{d-1}`.)*
    *(Earlier "tip-appended / forked `Rot` recoverable by keeping it" + "anchor realized on recovery" + the
    singleton residual were **wrong** — they archived/extended an adversary's `Rot` (rules 1/2), or recovered at the
    ancestor and archived your own content.)*
  *Principle:* by **tier, not identity** (the chain can't tell operator from adversary) — a repair attaches at your
  last event, archives the **archival tail(s)**, and is **permitted iff no archival tail holds a privileged event**.
  Genuine reincept = a privileged event in an archival tail, a T3 compromise, or a second privileged branch surfaced data-locally once the beacon delivers it (node-agnostic:
  **≥ 2 privileged branches → irreconcilable/disputed**). [inv 13]
- **A member KEL going terminal does not take the identity (walk/trust, 2026-06-22).** The **seal is the trust
  boundary**: the at-or-below-`last_seal_advancing_event` portion stays **final** even on a terminally-divergent
  KEL (the verifier surfaces it — inv 8); the post-seal window grounds **no new trust**. The *identity* survives by
  **IEL threshold redundancy + a `Evl` eviction** of the rogue member (inv 12) — a rogue member KEL is **inert
  alone** (below `t_use`/`t_govern`), so the quorum stops co-anchoring it and evicts. A **clean adversarial
  multi-rotation** (no divergence at all — nothing on-chain to challenge) is the same outcome: no divergence, no
  archival → evict at the IEL / `Dth` if delegated / reincept. [inv 8, 12, 13]
- **Three-state per-node machine: Active / Divergent / Terminated** (no four-state residue; **no per-node
  `Cnt` state**). The **`disputed`** signal is *separate* — a **data-local** walk verdict (the effective-SAID is a **real digest over the live tips**, not a synthetic — area-vdtid-services §1e):
  any verifier walks the **retained branches** and finds ≥ 2 each carrying a privileged event past the fork (inv
  13/17); the witness beacon propagates the branches, it does not decide. Not a fourth per-node state. [F2; `vdti-area-vdtid-services.md` §1e]
- **Locked-portion bound.** Events at-or-below the last seal-advancing event are immutable; a submission whose
  `previous` points into the locked portion is rejected at merge (**`SiblingLocked`** — renamed from `ParentLocked`,
  synced to the landed docs 2026-06-22: a parent *at* the seal is **extendable** (`parent_serial == seal_serial`
  passes the cap), so the rejection condition is a **sibling** already occupying that position, not a "locked
  parent"). **Cap-satisfying seal-advancers = `{Rot, Ror, Rec, Wit}`** (`Trm` also advances the seal — `previousSeal`, on the spine — but is terminal, so not a mid-chain cap-satisfier) — `Rot` is the default cap-satisfier (auto-inserted when
  an `Ixn` would exceed the cap); `Ror` only when also refreshing the recovery preimage. The bound makes recovery
  cross-node-validatable.
- **Federation binding = the prefix/SAID split** [inv 7, 14]: **`federation`** = the federation IEL **prefix**
  (which F; follows its evolution) and **`federationPin`** = a **SAID** pinning the as-of F-position (ratcheted
  via `Wit`). **Two inception roots, never sequenced:** `Fcp` (federation-infrastructure founder) **or** `Icp`
  (a user KEL joining an existing federation) — **never `Fcp → Icp`**. An `Fcp` **is bound by founding**: its v=1 is
  a **`Rot` that anchors the federation IEL `Fcp`** (the federation inception marker — kind-strict, T2 ↔ T2) in the
  **same atomic genesis batch** (`Fcp` v=0 → `Rot` v=1) — the witness is bound by being **named in the roster it
  founds**, never self-bound (governed *into* the roster — 2026-06-28). Genesis pattern: founder `Fcp → Rot`, the
  `Rot` anchoring the federation IEL `Fcp` (roster = founder witness KELs). A **user KEL's `Wit`** is its federation
  (re)bind — it moves *its* identity to a federation and **anchors the identity's IEL `Wit`**, which records the
  federation choice at the IEL (the closed set `{federation, federationPin}` — cold-5 C4 — exact-matched across the
  chains on every walk).
- **Anchoring (manifest-down), kind-strict [inv 4, 2026-06-28]:** a member anchors an IEL event with **exactly** the
  kind that reveals the capability it exercises — `Ixn → IEL Ixn` (T1 content); `Rot → {IEL Icp, Evl, Ath, Rev, Dth, federation Fcp}`
  (T2 establishment, governance, & the federation inception); `Ror → {IEL Rpr, Trm}` (T3 recovery & terminal);
  **`Wit → IEL Wit`** (T3 — the **one `Wit` kind**: a user KEL's `Wit` anchors the user IEL `Wit` (federation rebind),
  a federation witness KEL's `Wit` anchors the federation IEL `Wit` (governance); the anchor-kind is uniform, but the field-match is **facet-specific** (Q3): user facet matches `{federation, federationPin}` (C4), the federation-governance facet matches **only the witness-config** (roster rides the manifest `Evl`-style; the `clock` is a single IEL-side value, monotonic + `≤ now+band`); a *joining*
  witness instead rides a KEL `Ixn` alongside as consent-of-added, A1/E2 2026-06-28). **No higher-tier stand-in** —
  the former "a T3 KEL event satisfies a T2 anchor (anchor-tier elevation)" is **removed**; a `Ror` can no longer
  host a T2 anchor. **`Rec` hosts no anchor at all** — a recovered member participates via the subsequent `Ror`
  (examples 3/4: `Rec`→`Ror`, the `Ror` carries the participation anchor). Anchor-hosting KEL kinds are
  **`Ixn`/`Rot`/`Ror`/`Wit`** (the `Wit` hosts **only** the IEL `Wit`); `Rec`/`Trm` host none. **Federation
  bootstrap — RESOLVED (2026-06-28):** the federation's own witness KELs are **`Fcp`-rooted infrastructure**
  (governed *into* the roster, never self-bound); genesis is `Fcp` → `Rot`, the `Rot` anchoring the federation IEL
  `Fcp` kind-strict. A `Wit` on an `Icp`-rooted user KEL is the identity's rebind; a `Wit` on an `Fcp`-rooted
  witness KEL is federation governance — **the same kind, dispatched by the inception marker** (§inv 4). *(Landed
  `kel/events.md`'s `Fed` kind + "Fed carries no anchors" is now stale — reconcile to `Wit` in §5.)*
- **`manifest` is role-qualified (inv 4)** = SAID → a SAD grouping committed SADs by role: **`anchors`** (anchored
  IEL-event / SAD SAIDs) — **required on `Ixn`** (≥1), optional on `Rot`/`Ror`/`Wit`; **`fork`** (the archived-branch **root** a repair resolves — a single SAID, root-pointing, inv 4/13/17; the list collapsed 2026-07-02) **required on `Rec`**; **`witnesses`** (the witness-config
  SAD) on `Icp`/`Wit` (§4 — mandatory iff federated at `Icp`; **present-iff-changed on `Wit`**). The `federation` prefix + `federationPin` stay **top-level structural** (not roles).

## 2. Mined from the VDTI-10 build — structure + patterns (reshape-compatible; confirm before lock)
- **6-doc layout** to land: `log.md` (chain primitive, three-state machine, prefix derivation, locked-portion
  bound, page/chunk), `events.md` (taxonomy, three-tier model, anchor reqs, seal cap), `recovery.md` (recovery
  **doctrine** — Rec-vs-Ror, dual-sig defense, locked-portion role; *not* the operator workflow), `merge.md`
  (privileged-divergence-terminal, ParentLocked, merge outcomes, canonical routing), `reconciliation.md`
  (**correctness-proof matrix** — leads with the proof role, not a pointer), `verification.md` (the walk).
- **Seal cap** — worst-case repair batch `[Rec]` (single-event; the `[Rec, Rot]` follow-up was residue,
  dropped 2026-06-24 — the conditional `Rot` would archive a rotated branch, which the archival-tail rule
  forbids); the 64-event **fold** bound (per lineage) is a seal-advancer property (any `Rot`/`Ror`/…), not `Ror`-required.
  **`MINIMUM_PAGE_SIZE = 129`, fold/cap = `(MINIMUM_PAGE_SIZE − 1)/2` = 64 (per lineage).** The page is `2·64 + 1`
  so one fetch/txn carries a **full two-branch fork — both lineages (≤ 64 each) plus the resolving `Rec`** — atomically:
  a source→sink transfer must carry **both** competing branches (the sink holds neither in storage; it is receiving the
  fork fresh), so the `Rec`'s content-only guard has every branch to walk under one advisory lock (Jason 2026-07-03;
  the former `65` sized only the *local* discriminator's retained-branch-plus-`Rec`, which validated the competing
  branch from local storage — a size that breaks the transfer mechanics).
- **Vocabulary lock-in** — type-qualified base64 / Blake3-256 / JCS; **no CESR-named terminology, no fixed
  character counts** [memory: doctrine names structural properties, not brands].

## 3. Superseded — do NOT carry forward
- **KEL archiving kind `Rpr` → `Rec`.** `event-shape.md`'s KEL table + cross-log analogy name the archiving kind
  **`Rpr`**; in vdti the KEL's repair kind is **`Rec`** ("recover" — it reveals the recovery key), with `Rpr`
  reserved for the IEL/SEL repair (which ride a KEL anchor). See §4 (resolved). The 2026-06-15 pending-items
  `Rec`→`Rpr` rename is **un-applied** (the reshape settled on `Rec`); do not apply it.
- **`federationBinding` (single SAID) → `federation` (prefix) + `federationPin` (SAID).** `event-shape.md`'s
  one `federationBinding` field on `Icp`/`Wit` becomes the two-field prefix/SAID split [inv 7].
- **The `manifest`-feeds-the-`dev`-leaf reconciliation** (`event-shape.md` §"Policy DSL reconciliations",
  `s.anchors == manifest.anchors`) — `dev` is dropped and policy moved up to documents; the `manifest` field
  **survives**, but its policy-DSL consumer is **gone**. (Anchors are now read by the document-layer composer/
  resolver, not a chain leaf.)
- **kels#218 three-kind KEL inception** → vdti **two-kind** (`Fcp`/`Icp`); delegation is an IEL concern, **no
  `Dip` at the KEL layer** (already correct in the build doc — keep).
- **kels' `Cnt` self-terminal ("break this chain — I know I'm compromised") — considered for revival, REJECTED (Jason 2026-07-02).**
  kels' version reached back **beyond seals**, so it was a **backdating killswitch** (invalidating sealed history) —
  the exact attack the seal/spine boundary exists to close. A seal-bounded revival was explored (attach only beside
  the most recent seal, no reach behind it) but is **still rejected**, on the tier model: **T3 security is 2-of-2** —
  both preimages required, and **neither preimage does anything alone** (that inertness *is* the property; T2 = the
  rotation preimage alone, a strictly smaller action set, inv 11). A `Cnt` gated on the **recovery preimage alone**
  makes the deepest-reserve secret individually capable of an **irreversible terminal act** — a **single-secret
  killswitch** on the most-destructive operation, inverting the tier logic (the most irreversible act should need the
  *most* authority, not half). And it fills **no gap:** **`Trm`** (full-T3) already gives deliberate terminal
  terminate; **reincept + rebind** is the structurally-forced path for unrecoverable compromise; and compromise
  **surfaces data-locally** (`disputed` / terminal from the walk), so an owner-asserted "I'm compromised" flag adds
  no detection and is not trustworthy as a positive signal. Every **safe** framing collapses into `Trm` (spend both
  preimages beside a `Rot` = just `Trm`); every framing that **beats** `Trm` is the killswitch. So terminality stays
  at full-T3 `Trm`; "more events for no gain."

## 4. Open / route to the adversarial pass (load-bearing)
- **`Rec` vs `Rpr` — RESOLVED (Jason 2026-06-20): keep `Rec`, document the name + usage clearly.** `Rec` =
  **recover**, *not* "reactive" (the kels framing does not carry). It is the KEL's **repair** kind — the **same
  operation** as IEL/SEL `Rpr`, applied to the KEL — and it does **not** lock the chain. The defining
  KEL-specific trait is that it **reveals the recovery key** (dual-sig, T3). `Rpr` is reserved for the IEL/SEL
  (which ride a KEL anchor). Drives the `event-shape.md` rename (§5); the stale VDTI-10 `Rec`→`Rpr` stays un-applied.
- **Design-pass §2.2 matrix is stale (found drift).** Its T3 cell reads `Ror → {IEL Fcp(federation), Trm}` — wrong
  on both counts: the federation inception is anchored by a founder **`Rot`** (T2 ↔ T2, kind-strict), not `Ror`; and
  the federation IEL **does** incept `Fcp` — but as the **inception marker** (2026-06-28; a structural disambiguator,
  *not* the old self-witnessing carve-out, which stays dead — federation-ref §4). KEL-side fact: **a founder `Rot`
  (T2) anchors the federation IEL `Fcp`** (kind-strict, T2 ↔ T2). The federation area note owns the full detail;
  flag the §2.2 cell for reconciliation.
- **Member-KEL witness config (Jason 2026-06-20).** A member KEL declares its own witnessing preference
  (app/user choice) — *distinct* from the federation IEL's internal thresholds [inv 14, orthogonal: those govern
  the federation's *own* roster changes, not a member's receipt-gathering]. Shape: the manifest **`witnesses`** role
  → a witness-config SAD `{ said, threshold, signers }` on `Icp`/`Wit` (inv 4 — mandatory iff federated). `count` renamed **`signers`** = the number of
  witness signers gathered per event, chosen *above* `threshold` for redundancy; `threshold` = the minimum valid
  receipts for the event to verify as witnessed (it's a *subset* of the roster, not the whole roster). Consistent
  with the SAD-by-SAID pattern (manifest / roster / policy / pin — reuse, not a new mechanism). **Replaces** the
  flat `witnessThreshold` / `witnessSelectionSize`. Structural bounds: `signers/2 < threshold ≤ signers ≤
  |roster(F @ federationPin)|` (the lower bound = the **majority floor**, 2026-07-02 — federation §1e). **Per-layer (D1, 2026-06-28):** this is the **KEL's own** config (its KEL events; on `Icp`/`Wit`); a
  **user IEL carries its own authoritative** config (on `Icp`/`Wit`) for IEL events — an IEL is witnessed and could
  otherwise fork without any member KEL forking (disjoint sub-quorums — the content case now closed by the option-(b)
  position gate, federation §1e; privileged forks remain → `disputed`), so it needs its own, **independent** of member configs (not
  matched — a *user* IEL vs its member KELs, different chains); the **federation IEL carries its own** (on `Fcp`/`Wit`,
  adjusted each governance `Wit` — cold-7 F1), and at the **federation-governance facet that own config *is*
  field-matched** by the approvers' KEL `Wit`s (a consensus vote — area-iel:32 / cold-9 C1; not a contradiction with
  "independent," which is about member KELs' own configs); a **SEL inherits** its owner IEL's (single-owner). See inv 4:61 / federation §1e. **Resolved (federation area, 2026-07-02):** the majority floor `threshold > signers/2`
  **is structurally required** — with one-content-sibling-per-serial witnessing it *prevents* content forks on
  witnessed chains (below fork-cost `2·threshold − signers`); sub-majority configs are rejected; privileged forks and
  the direct-mode/byzantine residual stay detection — federation §1e.
- **KEL self-seal vs IEL `Evl` seal — RESOLVED (Jason 2026-06-20): independent, no cross-layer enforcement.**
  The verifier **always fully walks every involved log and re-resolves every anchor** (inv 8) — there is **no**
  seal-vouched shortcut (an earlier "frozen / seal-vouched prefix" idea was wrong). The KEL is the autonomous
  bottom layer: it can't look up to its IELs (inv 3, one-way) and composes many — and even setting direction
  aside, the operation **can't be performed**: you'd find dependents by looking up the archived SAIDs, but a
  `manifest` doesn't only carry lookupable SADs (it points at a **prefix**, and other things), so dependents
  can't be enumerated from a SAID lookup (Jason 2026-06-20). Wrong-direction *and* unimplementable. So an
  owner's `Rec` **can** archive an `Ixn` a dependent IEL event
  anchored, leaving that event with an unresolvable anchor = **verifiably broken**. That is **acceptable, not a
  bug to prevent**: a *valid* `Ixn` archived = the owner broke their own IEL (their fault); an *invalid* `Ixn`
  archived = the break is correct. Design target = **end-verifiability of whatever state exists, not pristine
  data** — broken data is expected (it's software); recovery is **operational** (reissue / re-incept). No
  requirement, no mechanism. **"Permanent" = intra-chain, NOT cross-layer-unbreakable (F9):** a `Evl` seal locks a
  chain's own events against *repair within that chain*; it does **not** protect that event's lower-layer anchors
  — a sealed IEL event's KEL anchor can still be archived by a lower `Rec`, breaking it (detectably). The seal
  bounds repair, not the cross-layer cascade. [memory: `feedback_end_verifiability_not_pristine`]

## 5. Drift → land backlog (canonical docs) — **LANDED via PR #11** (the six `kel/` docs are written; kept as the original plan, for trace)
- **Write `docs/design/primitives/data/event-logs/kel/{log,events,recovery,merge,reconciliation,verification}.md`
  fresh** from this note + the VDTI-10 build — **done in PR #11**, reshape-current.
- **`event-shape.md` KEL fixes:** archiving kind `Rpr` → `Rec` (resolved §4); `federationBinding` →
  `federation` + `federationPin`; replace flat `witnessThreshold` / `witnessSelectionSize` with the
  witness-config SAD SAID (§4 — pending the constraint floor); drop the `manifest`-feeds-`dev` paragraph.
- **Design-pass §2.2 matrix:** the federation-inception cell becomes `Rot → IEL Fcp(federation)` (kind-strict,
  T2 ↔ T2 — the federation IEL incepts the `Fcp` marker, anchored by a founder `Rot`; no founder `Fed`/`Wit`, 2026-06-28) (§4 found-drift).
- **Landed-doc reconciliation owed (2026-06-28) — kind-strict + the `Fed`→`Wit` remodel + federation** *(immediate —
  we keep all landed docs current, NOT gated on PR #11)*: landed
  `kel/events.md` still has (a) the **"minimum-tier-capability, not exact-event-kind"** rule + the **"Tier-3
  satisfies tier-2 anchor"** paragraph → make it **exact-event-kind** (kind-strict, inv 4); (b) **`Rec` in the
  anchor-host list** → drop it (anchor-hosting KEL kinds = `Ixn`/`Rot`/`Ror`/`Wit`; `Wit` anchors only the IEL
  `Wit`); (c) the **KEL `Fed` kind** → rename/merge to **`Wit`** (the one witness/federation kind — user rebind on an
  `Icp`-rooted KEL, federation governance on an `Fcp`-rooted KEL); the **`Fcp → Fed` genesis** → genesis is
  **`Fcp → Rot`** (the `Rot` anchors the federation IEL **`Fcp`**); (d) the founder-binding pattern → bound by being
  **named in the roster it founds** (governed in, never self-bound; single-federation); (e) the KEL anchor matrix
  gains **`Wit → IEL Wit`** (facet-specific field-match — Q3; the federation governance is now `Wit`-anchored, was `Ror` — E2) and the
  witness-config note gains the **IEL-carries-its-own + mandatory-iff-federated** rules (D1 / cold-7 F1/F3, 2026-06-28).
- **Do NOT apply** the VDTI-10 pending-items `Rec`→`Rpr` rename (item 2) — reversed by the reshape.

## 6. Confidence / what's owed
- §1 — **high.** The KEL is the least-changed primitive; `inv 11`/`13`/`15` + `event-shape.md` + the build doc
  converge. The key-state machine (three tiers, `Rot`/`Ror`/`Rec`/`Wit`/`Trm`, locked-portion bound) is intact.
- §4 — the `Rec` naming and the seal-layer composition are both **resolved** (Jason 2026-06-20); neither was deep
  KEL redesign. The one remaining open is the **witness-config constraint floor**, which is federation-area.
- Owed: the federation area note (witness-config constraint floor + the federation-inception anchor / §2.2 fix).
