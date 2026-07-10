# vdti — area note: KEL (Key Event Log)

**Status: FIRST CUT (2026-06-20); first-seen encode (2026-07-08).** The last primitive. **KEL collapsed to two
tiers in the first-seen pivot** — the recovery key and everything that existed only for it are gone. The deltas
are (a) **two tiers** (signing key / rotation reserve), (b) **dropped kinds** `Ror`/`Rec` — recovery is now just a
`Rot` (there is no repair *kind* and no recovery key), (c) the federation field split, and (d) **first-seen
witnessing** on single-key chains (the divergeable kind is still `Ixn`; a KEL rotation conflict is first-seen).
Audited against the first-seen model (`.working/vdti-model-plain-english.md` / `vdti-event-kinds.md` /
`vdti-adversary-cases.md`) + the canonical `event-shape.md`. Load-bearing claims marked for the adversarial pass.
**Invariants referenced:** [inv 2] single-locus, [inv 3] layers-isolated, [inv 4] manifest-down/pin-up,
[inv 7] prefix-vs-SAID, [inv 11] tier, [inv 13] divergence-scoped-to-T1-content, [inv 14] federation/witnessing,
[inv 15] inception-tier.

## Sources audited (disposition)
- The first-seen model — `.working/vdti-model-plain-english.md`, `vdti-event-kinds.md`, `vdti-adversary-cases.md`
  — **authoritative / current** (the two-tier collapse + first-seen pivot; `Ror`/`Rec` dropped, recovery = a
  plain `Rot`).
- `docs/design/primitives/data/event-logs/event-shape.md` — **canonical.** KEL field/kind shape reconciled to
  first-seen in the same encode (five KEL kinds, two tiers, no recovery key).
- The three-state machine + locked-portion bound + seal cap survive the pivot; the seal-cap satisfiers narrow to
  `{Rot, Wit}` (§2), and the burying event is a plain `Rot` (no `Rec`/`Ror`).

## 1. Locked-candidate — the current KEL model
- **KEL = one device's key state.** The **root** primitive — self-authorizing, **no chain above it** [inv 2].
  It is the bottom layer: nothing anchors *into* a KEL; a KEL anchors the IEL above it via its members' KEL
  events [inv 3]. **`Icp` = T1** (the root is self-authorizing — there is no governance to establish) [inv 15].
- **5 kinds** (`Icp`/`Ixn`/`Rot`/`Wit`/`Trm`); a **federation-infrastructure** KEL is the same working set rooted
  with **`Fcp`** (`Fcp`/`Ixn`/`Rot`/`Wit`/`Trm`):

  | Kind | Tier | Sig | Role |
  |---|---|---|---|
  | `Fcp` | T1 | single | **federation-infrastructure** inception (a federation witness KEL) — **self-attested, no `witnesses`** at genesis (can't commit to a federation IEL that doesn't exist yet), **single-federation** (§inv 14 / federation §1d — serves **one** federation; to serve another, spin up a new KEL). **Bound by founding:** its v=1 is a **`Rot` that anchors the federation IEL `Fcp`** (the federation inception marker — kind-strict, T2 ↔ T2) in the same atomic genesis batch — `Fcp`(v=0) → `Rot`(v=1). The witness is bound by being **named in the roster it founds / joins**, governed *into* the roster — **never self-bound** (it carries no user-style `{federation, federationPin}`). On an `Fcp`-rooted KEL a **`Wit` is federation governance** (it anchors the federation IEL `Wit`; the witness's own rotation), **never a user rebind** — `Fcp`-rooted = infrastructure, the `Icp`-rooted/user `Wit` is the rebind. Trust roots in the config-pinned `FEDERATION_IEL_PREFIX`. *(The `Fcp` genesis is unwitnessed — a config-pinned trust root — but this is **not** direct mode; it is the federation bootstrap, kept.)* |
  | `Icp` | T1 | single | inception — the **alternative root** (vs `Fcp`); an **ordinary user KEL**. **Federation-bound, always** (`federation`/`federationPin` required): every identity is federation-witnessed — **there is no direct mode** (§inv 14 / federation §1d). **Never preceded by `Fcp`** (a chain has `Fcp → Rot` *or* `Icp`, never `Fcp → Icp`). |
  | `Ixn` | T1 | single | content; anchors SADs via `manifest` (≥1); **the divergeable kind** — a content conflict is first-seen (recoverable) [inv 13]. |
  | `Rot` | T2 | single | rotation — reveals the next signing key, commits the next rotation reserve (the reserve persists — `rotationHash` re-committed); signed with **the rotation reserve** alone (the old signing key is not required). **Seal-advancing.** **Recovery is a `Rot`** (rotate at the first compromised position → the thief's run below dies by descent — §1 divergence). A rotation conflict on this single-key chain is **first-seen** (the Rot'@v_M fix — a stolen signing key can only forge the *late* competing rotation, already declined; a genuinely competing rotation needs the reserve, which is takeover). |
  | `Wit` | T2 | single | **the one witness/federation kind — `Wit` anchors `Wit` (anchor-kind uniform; field-match facet-specific — Q3); IS the rotation** (refreshes the signing key + rotation reserve; `pins = Wit.previous`); signed with the rotation reserve. On an **`Icp`-rooted user KEL:** the federation bind/**rebind** — carries `federation`/`federationPin`/`witnesses` **each present-iff-changed** (inv 18; **must change `federation` or `witnesses`** — a rebind carries `federation`+`federationPin`, a config change carries `witnesses`; a same-federation `federationPin`-only re-pin rides a body event, not a `Wit`; a pure key rotation is a `Rot`, not a `Wit`; a no-op `Wit` is rejected); **anchors the IEL `Wit`** (kind-strict, T2 ↔ T2; field-match = `{federation, federationPin}`, C4). On an **`Fcp`-rooted federation witness KEL:** the governance rotation — **anchors the federation IEL `Wit`** (kind-strict, T2 ↔ T2; field-match = the **witness-config only**, *not* C4 — roster rides the manifest `Evl`-style). |
  | `Trm` | T2 | single | terminal (terminate); signed with the rotation reserve. |

- **Two-tier capability model** [inv 11]: **T1 = signing key** (content — the everyday key); **T2 = the rotation
  reserve** (every key change — reveals the new signing key). **Key-state = single-stream pre-rotation (KERI-style):**
  the reserve committed at each epoch (via `rotationHash`) is **revealed to sign the next rotation and thereby becomes
  that epoch's signing key**, and that same rotation commits the next reserve — so a device holds exactly **two live
  keys**, the **current signing key** (last epoch's revealed reserve, for content) and the **next reserve** (committed,
  unrevealed, for the next key change); the two tiers are the *current* and *next* members of **one** key stream, not
  two independent keys (this is why "today's signing key **is** the secret that authored the current epoch's rotation",
  §1 first-seen — SS-3). The **old signing key is NOT a prerequisite** for T2
  (a rotation reveals the new key; you don't sign with the key you're abandoning). **All key changes are
  single-signed with the rotation reserve** — `Rot`/`Wit`/`Trm` (no dual-sig, no recovery key). The rotation reserve
  is held *apart* from the signing key in the device's hardware, and lets that device heal a suspected signing-key
  leak by itself; healing a *fully* compromised device (both keys) is the identity's job — the other devices vote
  it out (an IEL roster change). *(The old third "recovery" reserve — the deeper key that protected the rotation
  key — is gone: it protected nothing you couldn't protect more simply.)*
- **Witnessing is scoped by chain; the KEL is a single-key chain → first-seen** [inv 13]. One test decides:
  *could a single already-revealed secret author a competing sealed sibling?* On a KEL — **yes** (a device's own
  key), so the witnessing rule is **first-seen**: witnesses take the **first** event they see at a position and
  **decline** the copies. This holds for **both** buckets:
  - **Content (`Ixn`)** → first-seen; a content conflict is **recoverable** (the next rotation buries the loser).
  - **A key change (`Rot`/`Wit`/`Trm` — sealed)** → *also* first-seen (the **Rot'@v_M** fix). The trap: today's
    signing key **is** the secret that authored the current epoch's rotation, so it can forge a *competing* rotation
    — but only **after** that rotation revealed it, by which point the witnesses have already sealed the position.
    A signing-key thief can only land a **late** fork → declined (zero honest receipts — case 4); a *genuinely*
    competing rotation needs the **rotation reserve**, which is a **takeover**, not a recoverable fork.
- **Recovery is a plain `Rot` that buries at the root** — no repair *kind*, no recovery key, nothing to prove. When
  your signing key is stolen, you rotate to a fresh key at the **first** event that isn't yours; that single rotation
  locks the thief out (they lack the new key) **and** buries their run — everything below the rotation that isn't on
  the surviving line is dead, and anything grown from a dead point is dead too (deadness descends). You go for the
  **root**, not their tip, so however long a run the thief piled on, it all hangs off that one point and dies at once.
  **The rotation reserve defends the *signing* key, never the rotation key:** a thief who steals the **reserve** can
  just *extend* the chain with a rotation to their own key (a takeover-by-extend, case 3) — witnesses sign it
  willingly as an ordinary next event, so it forces nothing and is **silent to third parties on a dormant chain**
  (caught only by owner vigilance; reserve theft is unrecoverable → reincept). A hostile `Rot` at a *forked*
  position is likewise the reserve-theft takeover, **not** a recoverable fork.
- **Forked vs Disputed are distinct, derived states** [inv 13]. A fork is read by counting the **sealed** branches
  past it (a sealed event = a seal-advancing key change; the content count is irrelevant — all content is buriable):
  - **Forked** = **≤ 1 sealed branch** past the fork — **recoverable *if* that surviving sealed tip is the owner's
    recovery `Rot`** (a burying rotation at the root). A *hostile* sealed tip at a forked position is the
    reserve-theft takeover (terminal/silent, owner-vigilance only) — an owner's counter-`Rot` then makes it two
    sealed branches → **disputed** (cold C1).
  - **Disputed** = **≥ 2 sealed branches** past the fork → **terminal → reincept** (you can't un-change a key). A
    `{Rot, Rot}` disputed is moreover a **confirmed reserve compromise** — two valid rotations reveal the *one*
    reserve preimage at `v_{d-1}`.
- **Cross-tier co-sign + the per-serial bound.** A witness's slot at one serial is **`{≤ 1 content, ≤ 2 sealed}`**.
  Content and a key change are different **tiers**, so a witness signing one of each is **not** a double-sign — a
  cross-tier `{content, sealed}` pair is a **legit co-sign** (it is what lets a recovery rotation get witnessed and
  bury content the witnesses already signed), never misbehaviour. **Two *same-tier* signatures** (`{content, content}`
  or `{sealed, sealed}`) is the cheat → attributable, evictable. The verifier **early-terminates at 2 witnessed
  sealed SAIDs → Disputed → terminal** (monotone — a 3rd is redundant, reincept regardless); a **sub-threshold**
  sealed event is **fail-secure ignored** (a lone dishonest witness's flood never reaches "real"). So per-serial
  materialization is **O(1), flood-independent** — **≤ 2 content + ≤ 2 sealed** worst-case, **≤ 3** on the
  recoverable path — no matter how many an adversary mints; the bound is *early-termination*, not a production cap.
- **A member KEL going terminal does not take the identity (walk/trust, 2026-06-22).** The **seal is the trust
  boundary**: the at-or-below-`last_seal_advancing_event` portion stays **final** even on a terminally-divergent
  KEL (the verifier surfaces it — inv 8); the post-seal window grounds **no new trust**. The *identity* survives by
  **IEL threshold redundancy + a `Evl` eviction** of the rogue member (inv 12) — a rogue member KEL is **inert
  alone** (below `t_use`/`t_govern`), so the quorum stops co-anchoring it and evicts. A **clean adversarial
  multi-rotation** (a reserve-theft takeover-by-extend — no divergence, nothing on-chain to challenge) is the same
  outcome: the honest members recognize a rotation they didn't authorize → evict at the IEL / `Dth` if delegated /
  reincept. [inv 8, 12, 13]
- **Three-state per-node machine: Active / Divergent / Terminated** (no four-state residue; **no per-node
  `Cnt` state**). The **`disputed`** signal is *separate* — a **data-local** walk verdict: any verifier walks the
  **retained branches** and finds ≥ 2 each carrying a **sealed** event past the fork (inv 13/17); the witness beacon
  propagates the branches, it does not decide. Not a fourth per-node state. The **effective-SAID** is a single
  confirmed tip → **its real SAID**; **no single tip → a type-tagged `synthetic`** marker recoupled to the verdict
  (`forked`/`disputed`), qualified by prefix + position — **not** a digest over the competing tips (that set is
  adversarially extensible → flood-unstable; area-vdtid-services §1e). [F2; `vdti-area-vdtid-services.md` §1e]
- **Locked-portion bound.** Events at-or-below the last seal-advancing event are immutable; a submission whose
  `previous` points into the locked portion is rejected at merge (**`SiblingLocked`** — renamed from `ParentLocked`,
  synced to the landed docs 2026-06-22: a parent *at* the seal is **extendable** (`parent_serial == seal_serial`
  passes the cap), so the rejection condition is a **sibling** already occupying that position, not a "locked
  parent"). **Cap-satisfying seal-advancers = `{Rot, Wit}`** (`Trm` also advances the seal — `previousSeal`, on the
  spine — but is terminal, so not a mid-chain cap-satisfier) — `Rot` is the default cap-satisfier, auto-inserted when
  an `Ixn` would exceed the cap. The bound makes recovery cross-node-validatable.
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
- **Anchoring (manifest-down), kind-strict [inv 4, 2026-06-28; re-homed under two tiers 2026-07-08]:** a member
  anchors an IEL event with **exactly** the kind that reveals the capability it exercises —
  `Ixn → IEL Ixn` (T1 content); `Rot → {IEL Icp, Evl, Ath, Rev, Dth, Trm, federation Fcp}` (T2 establishment,
  governance, kill, terminal, & the federation inception — the IEL `Trm` and the federation `Fcp`/`Trm`, formerly
  `Ror`-anchored, **re-home to `Rot`** now that every key change is a T2 rotation-reserve act);
  **`Wit → IEL Wit`** (T2 — the **one `Wit` kind**: a user KEL's `Wit` anchors the user IEL `Wit` (federation
  rebind), a federation witness KEL's `Wit` anchors the federation IEL `Wit` (governance); the anchor-kind is
  uniform, but the field-match is **facet-specific** (Q3): user facet matches `{federation, federationPin}` (C4),
  the federation-governance facet matches **only the witness-config** (roster rides the manifest `Evl`-style; the
  `clock` is a single IEL-side value, monotonic + `≤ now+band`); a *joining* witness instead rides a KEL `Ixn`
  alongside as consent-of-added, A1/E2 2026-06-28). Anchor-hosting KEL kinds are **`Ixn`/`Rot`/`Wit`** (the `Wit`
  hosts **only** the IEL `Wit`); `Trm` hosts none. **Federation bootstrap — RESOLVED (2026-06-28):** the
  federation's own witness KELs are **`Fcp`-rooted infrastructure** (governed *into* the roster, never self-bound);
  genesis is `Fcp` → `Rot`, the `Rot` anchoring the federation IEL `Fcp` kind-strict. A `Wit` on an `Icp`-rooted
  user KEL is the identity's rebind; a `Wit` on an `Fcp`-rooted witness KEL is federation governance — **the same
  kind, dispatched by the inception marker** (§inv 4).
- **`manifest` is role-qualified (inv 4)** = SAID → a SAD grouping committed SADs by role: **`anchors`** (anchored
  IEL-event / SAD SAIDs) — **required on `Ixn`** (≥1), optional on `Rot`/`Wit`; **`witnesses`** (the witness-config
  SAD) on `Icp`/`Wit` (§4 — mandatory iff federated at `Icp`; **present-iff-changed on `Wit`**). The `federation`
  prefix + `federationPin` stay **top-level structural** (not roles). *(The `fork` role is gone — there is no repair
  event; recovery is a plain `Rot` that buries structurally by position + descent, naming no fork root.)*

## 2. Mined from the VDTI-10 build — structure + patterns (first-seen-current; confirm before lock)
- **6-doc layout** to land: `log.md` (chain primitive, three-state machine, prefix derivation, locked-portion
  bound, page/chunk), `events.md` (taxonomy, **two-tier** model, anchor reqs, seal cap), `recovery.md` (recovery
  **doctrine** — recovery is a **plain `Rot` that buries at the root**, the reserve defends the signing key not the
  rotation key; *not* the operator workflow), `merge.md` (**sealed**-divergence-terminal, first-seen decline,
  `SiblingLocked`, merge outcomes, canonical routing), `reconciliation.md` (the first-seen convergence walk —
  root-bury + deadness-descends; forked vs disputed), `verification.md` (the walk).
- **Seal cap** — the 64-event **content-run** bound (per lineage) is a seal-advancer property (any `Rot`/`Wit`).
  **`MINIMUM_PAGE_SIZE = 129`, cap = `(MINIMUM_PAGE_SIZE − 1)/2` = 64 (per lineage).** The page is `2·64 + 1` so one
  fetch/txn carries a **full recoverable content fork — both lineages (≤ 64 each) plus the burying `Rot`** —
  atomically: a source→sink transfer must carry **both** competing content branches (the sink holds neither in
  storage; it is receiving the fork fresh), so the burying `Rot`'s content-only guard has every branch to walk under
  one advisory lock (Jason 2026-07-03). *(There is no repair batch — the burying event is a single ordinary `Rot`.)*
- **Vocabulary lock-in** — type-qualified base64 / Blake3-256 / JCS; **no CESR-named terminology, no fixed
  character counts** [memory: doctrine names structural properties, not brands].

## 3. Superseded — do NOT carry forward
- **No KEL archiving/repair kind at all (first-seen collapse, 2026-07-08).** The KEL is **five kinds**
  (`Icp`/`Ixn`/`Rot`/`Wit`/`Trm`). The pre-first-seen `Ror` (proactive rotate-recovery), `Rec` (the KEL repair —
  reveals the recovery key), and the whole three-tier / recovery-key apparatus are **dropped**: there is no
  recovery key, no repair *event*, and **recovery is just a `Rot`** (rotate at the root, bury by descent). Anything
  naming a KEL `Ror`/`Rec`, a `t_recover`, or "T3" describes the dead model.
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
  the most recent seal, no reach behind it) but is **still rejected**, on the two-tier model: a terminal act is a
  **key change → T2**, needing the **rotation reserve**. A `Cnt` gated on the **signing key alone** would let a
  stolen everyday key perform an **irreversible terminal act** — a **single-secret
  killswitch** on the most-destructive operation, inverting the tier logic (the most irreversible act should need the
  reserve, not the everyday key). And it fills **no gap:** **`Trm`** (T2, the rotation reserve) already gives deliberate terminal
  terminate; **reincept + rebind** is the structurally-forced path for unrecoverable compromise; and compromise
  **surfaces data-locally** (`disputed` / terminal from the walk), so an owner-asserted "I'm compromised" flag adds
  no detection and is not trustworthy as a positive signal. Every **safe** framing collapses into `Trm` (spend the
  reserve to terminate = just `Trm`); every framing that **beats** `Trm` is the killswitch. So terminality stays
  at `Trm`; "more events for no gain."

## 4. Open / route to the adversarial pass (load-bearing)
- **No repair kind (first-seen collapse, 2026-07-08).** The former `Rec`-vs-`Rpr` naming question is moot — there
  is **no KEL repair kind** and no IEL/SEL `Rpr`. Recovery is a **plain `Rot` that buries at the root**; the
  divergence machinery it replaced (archival tails, root-condemnation, the `fork` role) is deleted (§3, inv 13).
- **Member-KEL witness config (Jason 2026-06-20).** A member KEL declares its own witnessing preference
  (app/user choice) — *distinct* from the federation IEL's internal thresholds [inv 14, orthogonal: those govern
  the federation's *own* roster changes, not a member's receipt-gathering]. Shape: the manifest **`witnesses`** role
  → a witness-config SAD `{ said, threshold, signers }` on `Icp`/`Wit` (inv 4 — mandatory iff federated). `count` renamed **`signers`** = the number of
  witness signers gathered per event, chosen *above* `threshold` for redundancy; `threshold` = the minimum valid
  receipts for the event to verify as witnessed (it's a *subset* of the roster, not the whole roster). Consistent
  with the SAD-by-SAID pattern (manifest / roster / policy / pin — reuse, not a new mechanism). **Replaces** the
  flat `witnessThreshold` / `witnessSelectionSize`. **Witness-config floors (2026-07-08):** every witnessed chain
  satisfies **`signers ≥ 3`** (byzantine tolerance), a **majority `threshold > signers/2`** (the fork-cost floor),
  and **availability `threshold ≤ signers − 1`** (no single-witness brick) — with `signers ≤ |roster(F @
  federationPin)|`. **The `signers = 1` waiver machinery is deleted** (the `{1,1}` lone-witness config, position-luck
  evict-one, the `signers − 1`-leg waivers) — `signers ≥ 3` removes the degenerate. `fork-cost = 2·threshold −
  signers` is a **dial**, floored at 1 (majority) with `slack = signers − threshold ≥ 1` (availability), raised toward
  `threshold` via `{signers, threshold}`; there is no `minForkCost` field (cost 1 is the structural floor, not a
  footgun). **Per-layer (D1, 2026-06-28):** this is the **KEL's own** config (its KEL events; on `Icp`/`Wit`); a
  **user IEL carries its own authoritative** config (on `Icp`/`Wit`) for IEL events — an IEL is witnessed and could
  otherwise fork without any member KEL forking (disjoint sub-quorums — the content case now closed by the option-(b)
  position gate, federation §1e; sealed forks remain → `disputed`), so it needs its own, **independent** of member configs (not
  matched — a *user* IEL vs its member KELs, different chains); the **federation IEL carries its own** (on `Fcp`/`Wit`,
  adjusted each governance `Wit` — cold-7 F1), and at the **federation-governance facet that own config *is*
  field-matched** by the approvers' KEL `Wit`s (a consensus vote — area-iel:32 / cold-9 C1; not a contradiction with
  "independent," which is about member KELs' own configs); a **SEL inherits** its owner IEL's (single-owner). See inv 4:61 / federation §1e. **Resolved (federation area, 2026-07-02):** the majority floor `threshold > signers/2`
  **is structurally required** — with one-content-sibling-per-serial witnessing it *prevents* content forks on
  witnessed chains (below fork-cost `2·threshold − signers`); sub-majority configs are rejected; sealed forks and
  the witness-compromise (byzantine) residual stay detection — federation §1e.
- **KEL self-seal vs IEL `Evl` seal — RESOLVED (Jason 2026-06-20): independent, no cross-layer enforcement.**
  The verifier **always fully walks every involved log and re-resolves every anchor** (inv 8) — there is **no**
  seal-vouched shortcut (an earlier "frozen / seal-vouched prefix" idea was wrong). The KEL is the autonomous
  bottom layer: it can't look up to its IELs (inv 3, one-way) and composes many — and even setting direction
  aside, the operation **can't be performed**: you'd find dependents by looking up the archived SAIDs, but a
  `manifest` doesn't only carry lookupable SADs (it points at a **prefix**, and other things), so dependents
  can't be enumerated from a SAID lookup (Jason 2026-06-20). Wrong-direction *and* unimplementable. So an
  owner's burying `Rot` **can** bury an `Ixn` a dependent IEL event
  anchored, leaving that event with an unresolvable anchor = **verifiably broken**. That is **acceptable, not a
  bug to prevent**: a *valid* `Ixn` buried = the owner broke their own IEL (their fault); an *invalid* `Ixn`
  buried = the break is correct. Design target = **end-verifiability of whatever state exists, not pristine
  data** — broken data is expected (it's software); recovery is **operational** (reissue / re-incept). No
  requirement, no mechanism. **"Permanent" = intra-chain, NOT cross-layer-unbreakable (F9):** a seal locks a
  chain's own content against *burial within that chain*; it does **not** protect that event's lower-layer anchors
  — a sealed IEL event's KEL anchor can still be buried by a lower `Rot`, breaking it (detectably). The seal
  bounds burial, not the cross-layer cascade. [memory: `feedback_end_verifiability_not_pristine`]

## 5. Drift → land backlog (canonical docs)
- **`docs/design/primitives/data/event-logs/kel/` reconciled to first-seen (2026-07-08):** five KEL kinds
  (`Icp`/`Ixn`/`Rot`/`Wit`/`Trm`), two tiers, no recovery key. `recovery.md` becomes recovery-as-a-plain-`Rot`
  (root-bury + deadness-descends); `merge.md`/`reconciliation.md` drop the repair machinery for first-seen
  (decline-copies, sealed-divergence-terminal, forked vs disputed); the `fork` role is deleted everywhere.
- **`event-shape.md` KEL fixes (2026-07-08):** drop the `Ror`/`Rec` kinds and the `recoveryKey`/`recoveryHash`
  key-state; all key changes single-sig; the `fork` role removed; seal-cap satisfiers `{Rot, Wit}`.
- **Design-pass §2.2 matrix:** the federation-inception cell is `Rot → IEL Fcp(federation)` (kind-strict, T2 ↔ T2
  — the federation IEL incepts the `Fcp` marker, anchored by a founder `Rot`).

## 6. Confidence / what's owed
- §1 — **high.** The first-seen collapse simplifies the KEL to two tiers / five kinds; the key-state machine
  (signing key + rotation reserve, `Rot`/`Wit`/`Trm`, locked-portion bound, first-seen decline) is settled against
  the first-seen model + `event-shape.md`.
- §4 — the witness-config floors (`signers ≥ 3`, majority, availability) are federation-area; the seal-layer
  composition is unchanged.
- Owed: the federation area note (witness-config floors + the federation-inception anchor / §2.2 fix); this is the
  first-seen encode's federation-witnessing pass.
