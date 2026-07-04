# vdti — area note: IEL (Identity Event Log)

**Status: FIRST CUT (2026-06-20) — also the area-note format exemplar.** Audited against the post-reshape
core. Load-bearing claims marked for the adversarial pass; nothing here is locked until it survives that.
**Invariants referenced:** [inv 1] policy-on-documents, [inv 2] single-locus, [inv 3] layers-isolated,
[inv 4] manifest-down/pin-up, [inv 5] pin-floored, [inv 11] tier, [inv 12] threshold-vector, [inv 13] divergence/repair.

## Sources audited (disposition)
- `vdti-log-primitive-reshape-design-pass.md` §1–4, §12 + `vdti-federation-inception-reference.md` — **authoritative / current.**
- `vdti-iel-primitive-stub.md` (active) — **~90% superseded** (built on IEL-carries-policy); mine §Verifier-walk + §Postgres for patterns (→ §2 below), then archive. Stale-taxonomy banner is honest.
- `archived/vdti-iel-policies-audit.md`, `…-fix-applied.md` — flagged **superseded** (the whole "IEL policies" surface is gone); ⚠ not yet deep-read — confirming glance owed before lock.
- Canonical: `docs/design/primitives/data/event-logs/event-shape.md` — **reconciled to the reshape** (the `Ath`/`Rev`/`Dth`/`Wit` taxonomy encode landed 2026-07-04); a dedicated `iel/` dir is still to write.

## 1. Locked-candidate — the current IEL model
- **IEL = one identity = a threshold over member KELs** (roster + threshold *vector*). Not a policy host. [inv 2, 12]
- **9 kinds** (general/user IEL: `Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Rpr`/`Trm`/**`Wit`**); a **federation** IEL is the
  restricted set **`Fcp`/`Wit`/`Trm`**, where **`Fcp`** is its inception marker (a structural disambiguator the
  verifier dispatches on — federation-ref §2 — **not** a trust carve-out; the config-pin still roots trust) and
  **`Wit`** is its governance kind (T3 — replaces `Evl` for the federation; cold-4 B1 / 2026-06-28; the federation
  has **no `Evl`**). The **one `Wit` kind** spans both layers: on a **user** IEL it is the federation rebind, on a
  **federation** IEL it is governance — `Wit` anchors `Wit` uniformly (anchor-kind); facet-specific field-match (§ the `Wit` row below):

  | Kind | Tier | Count | Role |
  |---|---|---|---|
  | `Icp` | T2 | all initial members (Rule A) | inception; pins initial roster. **User IEL only** — a **federation** IEL incepts **`Fcp`** (the marker), not `Icp`. |
  | `Ixn` | T1 | `t_use` | content / **SEL-binding manifest** (the `anchors` role — inv 4); **the divergeable kind** (→ §4). |
  | `Evl` | T1 added / T2 outgoing | all added consent (Rule A) ∧ `t_govern` of outgoing | **roster/threshold change** — carries a roster/threshold **delta** (`add` + `cut`, not a full snapshot — [inv 14]); **anchors no kills** (those ride `Rev`/`Dth`) but **anchors the SEL `Fld`s it re-seals** (`anchors`, opt — a SEL fold lands at an IEL fold boundary). **Added members consent at T1** (sign + declare key commitments — they're joining, not rotating). **`t_govern` of outgoing approve at T2** — each reveals a rotation preimage via a `Rot` that anchors the `Evl` (this is "forces a `Rot`"). |
  | `Ath` | T2 | `t_authorize` | **the unified "authorize a party to act" anchor** (was `Del`, generalized 2026-07-04). Two manifest roles, **both permitted at once** (batchable; same cost): **`delegates`** — a positive inclusion list of delegate prefixes (the party acts **for the delegator**); **`anchors`** — the downstream SEL **`Gnt`**(s) it seals (a doc-membership grant; the party acts **as itself**; kind-strict — names **only** `Gnt`s). The **additive counterpart of the kill-anchors** (no own-state delta; seals a downstream **grant** at T2). **Forces a `Rot`.** Sealed-on-arrival; privileged, non-terminal. |
  | `Rev` | T2 | `t_govern` | **sealed kill-anchor — revoke an owned artifact**: via `anchors`, names the SEL `Trm`(s) it seals (**only** `Trm`s — kind-strict, C1) — a cred-SEL `Trm` (revocation / closure). Carries **no roster delta** → can't mutate establishment state (closes **S1**). Count implied by kind (`t_govern`), **backed** by sigs at the walk. **Forces a `Rot`** (each `t_govern` member — a T2/permanent act needs a ≥T2 KEL anchor; the `Evl`-vs-kill-anchor distinction is the **roster delta**, not the rotation — corrects R3-2, A). Sealed-on-arrival; **privileged but NOT a terminal tip** — seals a kill on a *target*, not its host IEL, so the IEL continues (`{Rev, content}` is recoverable like `{Evl, content}`, the `Rev` retained and the content archived); terminal only as one of ≥ 2 privileged branches. |
  | `Dth` | T2 | `t_authorize` | **sealed kill-anchor — deauthorize a grant**: via `anchors`, names the SEL `Trm`(s) it seals (**only** `Trm`s) — a lookup-SEL rescission `Trm` (delegation **or** doc-membership). The **polarity-inverse of `Ath`** (grant → deauthorize, same `t_authorize`). Carries **no roster delta**. **Forces a `Rot`.** Sealed-on-arrival; **privileged, non-terminal** (like `Rev`). |
  | `Rpr` | T3 | `t_recover` | divergence repair (threshold-gated cascade); **may carry a roster `cut` (+ optional `threshold`) — the `cut` is *required* when the `roster` role is present; *never* an `add`, never `threshold`-only** (the repair-and-evict fold, 2026-06-30: the eviction rides the repair, priced the **outgoing** `t_recover` (pre-change, as `Evl` is `t_govern`-of-outgoing), sound because `t_govern ≤ t_recover` is now hard; post-cut roster re-checked against the inv 12 bounds; the cut target is operator-chosen (the fork-causer is the motivating case, not a structural check) — inv 12 / inv 13). |
  | `Trm` | T3 | `t_govern` | terminal; freezes all the IEL's SELs. |
  | `Wit` | T3 | `t_govern` | **the one witness/federation kind — `Wit` anchors `Wit` uniformly (anchor-kind); the field-match is facet-specific (Q3); `Wit` IS the T3 rotation** (refreshes signing + recovery; `pins = Wit.previous`). Two facets by layer: <br>**(user IEL) federation rebind** — records the identity's federation (`federation` prefix + `federationPin`, top-level). Anchored by member KEL `Wit`s (**kind-strict, T3 ↔ T3** — inv 4). The IEL `Wit`'s **two federation-binding fields `{federation, federationPin}`** (a **closed set** — no optional fields, cold-5 C4) must **match exactly** those of every anchoring KEL `Wit`, checked on **every walk** — so all `t_govern` anchoring members are pinned to the **same federation position** (cold-5 C5), and the IEL `Wit` records **only** what its members signed (auditable, never self-asserted). **Binding validation also checks the `federation` prefix resolves to an `Fcp`-rooted IEL** — a binding pointing at an `Icp`-rooted (user) IEL is malformed → rejected (Q2; trust still roots in the config-pin). The **identity's federation is the IEL's own authoritative binding** (its most-recent `Wit`/`Icp`); it inherits **nothing** sub-threshold or unmatched — so a lone/desync'd member KEL (it anchors a sub-threshold IEL `Wit` → verifiably broken, inert) **cannot straddle the identity** (cold-3 B2). **Initial binding rides the `Icp`** — **or the first `Wit` for a direct-mode chain whose `Icp` omits the federation** (cold-5 C1a, federation §1d); a later `Wit` rebinds, under a **hard cap on `Wit`s/chain** (DoS — over-cap rejected, inv-14 pattern). During a rebind, members below `t_govern` lag on the old federation until they each rebind — bridged by **overlapping federation trust** (cooperative-migration only — federation §1d). **`{Wit, Wit}` terminal, `{Wit, content}` recoverable (cold-5 B2).** **A user `Wit` must change `federation` (the prefix) or `witnesses`** — a same-federation re-pin (advancing `federationPin` only) is **not** a `Wit` (it rides any body event), and pure rotation is `Ror`, so a `Wit` that changes neither is a no-op → **rejected** (the old `Fed` rebind requirement survives on the **user** facet; the federation-governance facet has no such rule — below). <br>**(federation IEL) governance** — the analog of `Evl`, doing **everything** (roster add/cut **and** witness rotation), at **T3**. Every federation governance act is a `Wit` (the **terminal `Trm`** aside — terminate is **`Ror`-anchored** (kind `Trm`, not a `Wit`), and carries the federation `clock`, self-attesting under the new windows its `Ror`s reveal — the same clock carve-out, §1e/§1f), anchored by the participating witnesses' KEL **`Wit`s** (kind-strict, T3 ↔ T3) — a **rotation ceremony** (the *participating* witnesses refresh signing+recovery) that may also carry a **roster delta** (`add`/`cut`); a synchronized **all-witness** rotation ~yearly is the operational norm (clean timeline advance + forward secrecy for all), **not** a hard per-`Wit` requirement (a non-participating witness keeps its open key-window until it rotates, **bounded by the 365-day `MAX_WINDOW` auto-expiry — §1f**). `pins` = the participants' **pre-rotation KEL tips** (`Wit.previous`) — the clock's `T_end` for retiring receipt keys + the honored-vs-off-ceremony commitment (§1a/§1f) — **plus, on a roster-add, the joiner's `Ixn.previous`** (a `T_join`, never a `T_end`; cold-7 F2). Carries the inline `clock` timestamp, (optional) roster delta, and the federation's **own witness-config** (`witnesses` — D1 / cold-7 F1). **The `Wit↔Wit` field-match here is the witness-config only (Q3, Jason 2026-06-28)** — and that matched `witnesses` is the **federation's new config the approvers jointly endorse** (a consensus vote: each approver's KEL `Wit` carries it, all matching the IEL `Wit`'s — exactly analogous to the user facet's `{federation, federationPin}` consensus), **not** a member's independent KEL-event config (D1's "per-layer independent / not matched" describes a **user** IEL vs its member KELs — different chains; the federation's witnesses **are** its members, so they jointly govern the one federation config — cold-9 C1). **The roster delta does not match** (it rides the IEL `Wit`'s manifest, `Evl`-style — SAID-committed, anchored by the `t_govern` member `Wit`s; each member endorses the exact delta by anchoring the IEL `Wit`'s SAID), and the **`clock` does not match** (one authoritative value on the IEL `Wit`, monotonic + `≤ now+band` — §1f). **The federation `Wit` is *self-attested* by its witnessed KEL anchors (Q1)** — not gated on a separate aggregate receipt count, so an all-witness rotation never bricks (inv 4:`witnesses`). **`{Wit, Wit}` terminal. Roster-add consent (A1):** a *joining* witness consents via a KEL `Ixn` alongside (joining-not-rotating — the user-`Evl` joiner pattern), the pre-add witnesses approve via their KEL `Wit`s — **`t_govern` counts only KEL `Wit`s whose author ∈ the pre-add (outgoing) roster** (cold-8 F5), so a colluding `W_new` authoring a `Wit` can't manufacture a vote; the **kind split** (`Ixn` joiner vs `Wit` approver) is the *secondary* backstop keeping the joiner's consent out of `t_govern` (Rule-A only, restoring the C6 backstop) — diagram example 6. **Why roster + rotation in one kind** (vs §4's "split different jobs") — read the invariant first, then the per-facet mechanism: **a `Wit` is *never* a no-op** (a bare KEL rotation with no IEL `Wit` to anchor is an `Ror`, not a `Wit`), but *what* makes it non-trivial is **facet-specific** — the user facet states an explicit must-change because its rotation **alone** would be an `Ror`, while the federation facet's rotation **is itself** the change. <br>• **User facet** — a user `Wit` is a **rebind**: it **must change `federation` or `witnesses`** (a same-federation re-pin advancing only `federationPin` rides any body event, not a `Wit`; a pure key rotation is an `Ror`), so a user `Wit` changing **neither** is a no-op → **rejected**. <br>• **Federation facet** — a federation `Wit` is **governance**: it is **always a rotation** (the participating witnesses refresh signing + recovery; the IEL `Wit` **pins** their pre-rotation KEL tips, the member KEL `Wit`s **anchor** it, kind-strict) **and advances the monotonic `clock`**, with a roster delta **optional on top** — so the **rotation + clock advance IS the change**, and there is **no** "must change `federation`/`witnesses`" predicate. *(The federation chain carries **no `federationPin`** to ratchet — F3, cold-10; the remodel dropped the A2 must-also-change-roster framing. The earlier "the federationPin ratchets" phrasing here was a user-facet field wrongly attributed to the federation facet — corrected 2026-06-30.)* |
  | `Fcp` *(federation IEL only)* | T2 | all founders (Rule A) | **federation inception marker** — the federation IEL's inception (replaces the old federation `Icp`; 2026-06-28). Anchored kind-strict by each founder's KEL **`Rot`** (T2 ↔ T2 — genesis `Fcp → Rot`, federation §1c). Carries the initial roster, the initial **witness-config** (`witnesses`), and the initial **`clock`** (the founders' `T_join` = genesis time). The marker lets a verifier **recognize** a federation IEL from its own data (restricted kinds, exclude-self witnessing) — **interpretation, not trust** (the config-pinned `FEDERATION_IEL_PREFIX` still roots trust; the self-witnessing carve-out killed in federation-ref §4 does **not** return). **The `Fcp` is *checked* at two times (Q2, Jason 2026-06-29): during witnessing checks** (resolving `roster(F @ context)`) **and during federation-binding validation** — the latter **rejects** a user `{federation, federationPin}` whose target prefix is **not** `Fcp`-rooted (a binding pointing at an `Icp`-rooted user IEL is malformed). *(Plus its structural role as the **spine root** of the federation IEL — `previousSeal` walks terminate there, inv 17 — same as any inception.)* |

- **`roster` = KELs only.** No aggregate-of-IELs recursion; identity composition lives in the policy/document layer. [inv 1]
- **Threshold vector** `{t_use, t_govern, t_authorize, t_recover}` (the **count** axis, ⊥ tier — inv 11); Rule A (unanimous-additions); removal is a **`Evl`** (the general path) or, when it must be atomic with a repair, a **`Rpr` `cut`** (the repair-and-evict fold — one event, supersedes the old `{…, Rpr, Evl}` batch; 2026-06-30, inv 13). **Bounds (F-K, inv 12):** `t_use ≥ 1`; the authority kinds (`t_govern`/`t_authorize`/`t_recover`) have **two bounds of different kinds** — **`≥ 2`** (security: no single-member authority — **hard, every identity**) and **`≤ |roster| − 1`** (recoverability: evict/recover without one — **advisory only at `|roster| = 2`** (verifier accepts, wallet warns), **hard at `|roster| ≥ 3`** for every identity); singleton → all = 1. A **2-member identity is valid but unrecoverable** (warned — a compromised device can *freeze* you, not just self-lockout; add a 3rd key). **At `|roster| ≥ 3` a threshold `= |roster|` is rejected** (gratuitous hostage — Finding 3); recoverable governance needs `|roster| ≥ 3`. **`t_govern ≤ t_recover` is now a hard floor** (2026-06-30, inv 12 — the `Rpr`-cut fold rides `t_recover`). [inv 11, 12; G1]
- **Threshold declaration (locked 2026-06-25).** The **`Icp` declares the active threshold set** — exactly the
  authority kinds the IEL will ever use — **a threshold is declared iff its consuming kind is in the IEL's kind set**
  (`Ixn`→`t_use`, `Ath`/`Dth`→`t_authorize`, `Rpr`→`t_recover`, `Evl`/`Rev`/`Wit`/`Trm`→`t_govern`). A **user** IEL → `t_govern` +
  `t_recover` **mandatory**, `t_use` + `t_authorize` **optional and lockable**; a **federation** IEL (`Fcp`/`Wit`/`Trm` —
  no `Ixn`/`Ath`/**`Rpr`**) declares **exactly `{t_govern}`** (`t_use`/`t_authorize`/`t_recover` forbidden → a federation
  `Fcp` declaring any is malformed, rejected — the threshold-declaration analog of the facet-dependent role allowlist,
  2026-06-29). A kind **omitted at `Icp` can never be exercised** (no first-introducing it on a later event). Thereafter
  a roster delta carries a threshold field **only when it changes** (present ⇒ **must** change; absent ⇒ unchanged)
  — the same present=delta / absent=inherit shape as the membership `add`/`cut` and the federationPin re-pin. [inv 12]
- **`Evl` carries a roster/threshold *delta* (`add` + `cut`), no separate floor** (append-only chain is the floor;
  current roster = **accumulate every delta while walking**, with the hard live-set cap — [inv 14]; **not** "latest `Evl`"). [I2]
- **Manifest is role-qualified (inv 4).** An IEL event's `manifest` groups what it commits to below by named role
  ("the things this event {anchors/roster/delegates/…}"): `Icp`/`Evl` (user) → `roster` (the roster/threshold delta SAD), and a user `Rpr` → `roster` = a required `cut` + optional `threshold` (the repair-and-evict fold, 2026-06-30 — no `add`, no `threshold`-only) + `anchors` (the SEL `Rpr`s the repair cascade commits) + `fork` (req — the **root** of the fork it resolves, a single SAID — root-pointing, inv 4/13/17: the root condemns its whole subtree; every other competing branch closes below the seal + by descent, 2026-07-02); a
  **federation** `Fcp`/`Wit` → `roster` + `clock`, the terminal `Trm` → `clock` (the inline timestamp value — the federation has no `Evl`, `Wit` is its sole governance kind; `Trm` carries the clock but no roster); `Evl` also → `anchors` (the SEL `Fld`s it re-seals,
  opt); `Ath` → `delegates` (delegate prefixes, act-for-delegator) + `anchors` (the SEL `Gnt`s it seals, opt — kind-strict); `Ixn` → `anchors`
  (anchored SEL events, incl. the cred-SEL **v1**s — the serial-1 `Pin`, the `Icp` via `v1.previous` — it issues, batched; **anchor-monotonicity, inv 4:** each anchored SEL event must extend that SEL's latest IEL-anchored tip — a re-anchor is malformed/inert, so the IEL totally-orders each SEL → a SEL never forks under a linear IEL, cross-layer cold F1); `Rev`/`Dth` → `anchors` (the SEL `Trm`s it seals —
  `Rev` names cred-SEL `Trm`s (`t_govern`), `Dth` names lookup-SEL `Trm`s (`t_authorize`) — batched). The federation `prefix`/`federationPin` (on `Icp`/`Wit`) stay
  **top-level structural** (the event's own links). The killed cred is identified by *which SEL its `Trm` extends*,
  not by a prefix in the kill-anchor.
- **Down-pins are top-level structural, not a manifest role (`pins`, locked 2026-06-25)** [inv 4]. The complement
  of fresh participation (inv 5): a member participates by anchoring a fresh KEL event **up** to the IEL event — of
  **exactly** the kind that reveals the capability it exercises (**kind-strict, inv 4:** content ← KEL `Ixn`; T2
  establishment/governance ← KEL `Rot` (incl. the federation `Fcp` inception ← KEL `Rot`); T3 recovery/terminal ←
  KEL `Ror`; **T3 witness/federation (IEL `Wit` — the user federation-binding AND federation governance, uniformly)
  ← KEL `Wit`** (the one `Wit` kind is the T3 rotation; facet-specific field-match); **no higher-tier stand-in**, and
  `Rec` anchors nothing — a recovered member uses the subsequent `Ror`). The
  IEL event records the **down-pins** — each participating member's **prior KEL tip** (the event its fresh
  participation *extends* — `participation.previous`, the SEL `pin → anchor.previous` analog, so the IEL's `said`
  never depends on the participation events that anchor it; no SAID cycle, cold-3 B1) — as **`pins`**, a top-level
  field (a scalar SAID → a small **pins-SAD**, since the list can't be an inline event-body field). Every IEL event
  is anchored by a threshold of members (inv 12), so **every IEL event carries `pins`**. A **federation** `Wit`'s
  `pins` are the participants' `participation.previous`: the approvers' **pre-rotation witness KEL tip SAIDs**
  (`Wit.previous`) — the clock's `T_end` for the retiring receipt key + the cold-F7 commitment that lets a verifier
  tell an honored synchronized rotation from an off-ceremony `Ror` — **plus, on a roster-add, the joiner's
  `Ixn.previous`** (a `T_join` for the joining key, never a `T_end`; cold-7 F2). (A **SEL**'s analog is the singular top-level `pin` → its owner IEL event.)
  `pins`/`pin` are kept top-level so a verifier walks the layered structure **without fetching the manifest**; the
  manifest is for content commitments. *(Exact pins-SAD schema + any per-kind nuance: this doctrine pass.
  `sealPins` — a seal-level analog — was dropped: divergence-view only, subsumed by the flat walk, inv 17.)*
- **Read the manifest kind-first (inv 4 F1) — load-bearing.** Each kind may carry **only** the roles in
  `allowed(kind)` above; a role outside it is **malformed → rejected**. **For `Wit`, `allowed(kind)` is *facet-dependent* (cold-8 F3):** dispatched on the **root** — a `Wit` on an `Icp`-rooted (user) chain may carry `{federation, federationPin}` (top-level) + `witnesses`, and **must not** carry `roster`/`clock`; a `Wit` on an `Fcp`-rooted (federation) chain may carry `roster`/`clock`/`witnesses`, and **must not** carry `{federation, federationPin}`. So the verifier **establishes the chain's root facet (`Fcp` vs `Icp`) before reading the `Wit` payload** on **every** `Wit`-reading path — the from-scratch walk, a `resume` from a cached token, **and** a `search_only` walk that ends early (cold-9 Q3); the **verification token carries the root facet** so a `resume` can't process a `Wit` payload facet-blind. A facet-blind allowlist would admit a governance-shaped payload (a roster delta) on a user `Wit` — and since the kind→role allowlist is the *only* gate on the directly-consumed governance roles, **"facet dispatch on every `Wit`-reading path" is a done-criterion** for the doctrine-land + impl. Critically, the *directly-consumed* roles
  (`roster` on `Icp`/`Evl` (user), a `cut`-only `roster` on a user `Rpr` (the fold), or `Fcp`/`Wit` (federation); `delegates` on `Ath`, `clock` on a federation `Fcp`/`Wit`/`Trm`) have **no** downstream
  type-check — the kind→role gate is their *only* protection, so an `Ixn` carrying `roster`/`delegates`
  must be rejected (else governance/grants at `t_use` → **S1** reopens; killing at `t_use` is closed separately by
  the back-check — a SEL `Trm` demands a `Rev`/`Dth`). The label is checked against the kind, never trusted on its own.
  (`anchors` is additionally back-checked when the referenced SEL event is validated against its required kind —
  incl. the rule that a `Trm` is valid only anchored by a `Rev`/`Dth` — **this back-check is now what keeps kills sealed,
  replacing the former `revokes`/`rescinds`-are-`Kil`-only binding**; and the matrix is **kind-strict** both
  directions (a `Rev`/`Dth` anchors only `Trm`s, an `Ath` only `Gnt`s, an `Ixn` only content/v1, an `Evl` only `Fld`s, an `Rpr` only `Rpr`s —
  tier-elevation is an additional floor, not the check, inv 4 C1).)
- **Repair** = threshold-gated cascade: surviving members `Ror` (satisfy `t_recover`) anchor the IEL `Rpr`; a compromised member `Rec`→`Ror`; **mandatorily atomic** (manifest-bound, batched, one DB txn — a *partial* repair is **rejected**, closing the re-divergence race by construction; cold-5 C3). **A repair that also evicts folds the eviction *into* the `Rpr` as a `cut` (the repair-and-evict fold, 2026-06-30):** one event, `Ror`-anchored exactly as a plain `Rpr` (no separate `Evl`, no `Rot`, no mixed-kind anchoring — it is a `Rpr` with a field), priced the **outgoing** `t_recover` (pre-change, like `Evl` at `t_govern`-of-outgoing — so a `Rpr` can't lower its own gate then cut; the cut covered by the now-hard `t_govern ≤ t_recover` — inv 12), with the **post-cut roster re-checked against the inv 12 bounds** (a stranding/hostage cut is rejected, forcing a simultaneous `threshold` drop or reincept). The cut target is operator-chosen (the fork-causer is the motivating case, not a structural check). The eviction **must** be atomic with the repair — a later `Evl` lets the still-rostered member race an `Ixn` at the repaired tip → re-fork → endless repair (a timing attack) — and the fold makes it atomic **by construction** (the member is gone the instant the fork resolves at `v_{d-1}`). **This supersedes the two-event `{…, Rpr, Evl}` batch + cold-4 A2's `Ror`+`Rot`.** An **add** (evict-and-replace) is non-urgent → a later `Evl`. **A repair is not final-on-arrival (inv 13, refined to root-pointing 2026-07-01; witness-scoped 2026-07-02):** a `Rpr` landing at a **gossip-lagging** node collides with content that node accepted in the interim → the repair is **accepted** (the chain reads *incompletely-repaired*, not frozen dead). **On a witnessed chain the collision never goes live** — the repair is always-witnessed and seals on arrival; a witness holding it declines the racing content (federation §1e) — so this narrative is the **residual's** (direct-mode/solo + witness compromise). The `Rpr`'s `fork` names a losing branch's **root** (ONE root — the list collapsed, inv 4, 2026-07-02), condemning the whole subtree — so interim content that grew that branch is dead **by descent**, and any unnamed sibling forks below the seal → **inert**, growth dead by descent; both ride the forked chain (capped at 64), witnessed but never canonical. **No second `Rpr`, no `{Rpr, Rpr}` collision, no reincept** — the **content-completeness** of the repair proof. A sustained **adversarial** re-forker (one that keeps minting *new* forks) is separately terminated by a `Rpr` **`cut`** evicting it (the KEL `Rec` gets this for free by rotating its key out — the IEL has **no identity key**, so it needs the roster change); a **benign** gossip-lag `Ixn` is condemned/inert + re-issued once honest members catch up. Operational — the same re-fork family as the repair-and-evict timing attack, seen from the propagation side. [inv 4, 12, 13, 17]
- **Divergence resolution — the archival-tail rule (2026-06-22)** [inv 13]. Two rules: only `Ixn` (T1 content) is **archivable** (a privileged `Evl`/`Ath`/`Rev`/`Dth`/`Wit`/rotation is **never** overturned — resurrects keys / reverses establishment), and you never extend an adversarial event. So recovery (`Rpr`) attaches at **your last event**, retaining your branch and archiving the **archival tail(s)**; **permitted iff no archival tail holds a privileged event** — else → **reincept** (you can't archive it — rule 1, extend it — rule 2, or fork it — terminal). So an adversary's content `Ixn`s in an archival tail → recoverable; an adversary's `Evl`/`Ath`/`Rev`/`Dth` in an archival tail → reincept (the recovering party retains only its *own* branch, gated cryptographically by its recovery commitment — the chain can't tell operator from adversary). The **node-agnostic federation condition** is **≥ 2 privileged branches → irreconcilable/disputed** (any party retains only one branch, so a second privileged branch always lands in some party's archival tail). [→ §4★/§4★★, inv 13]
- **IEL distrust is forward-only (locked 2026-06-22)** [inv 12, 13]. An IEL event is trusted iff a **threshold** of members anchored it (fresh participation, inv 5), so a **rogue member KEL is inert alone** — it can't reach `t_use`/`t_govern`, so the quorum's "don't trust this" *is* **non-participation** (stop co-anchoring) **+ a `Evl` eviction**; you don't *also* anchor the rogue's attempts, and satisfaction is never met. A **retroactive** per-event distrust declaration is **forbidden** — a quorum that could retroactively un-trust its own history would hold the **backdate kill-switch** vdti closes. Trust is decided at participation time; an event the quorum co-signed (even alongside a since-compromised member) **stands**, and remediation is **forward** (revoke what it granted, evict the member). A member KEL un-resolvable at the KEL layer (clean adversarial multi-rotation — no divergence to challenge) **does not propagate** to the identity: the IEL evicts it and leans on the quorum. **No cut-member cap** (the member's own seal bounds its past; the SAID-pin bound survives only for delegate-rescission — inv 14 / delegation §5).
- **Seal-cap on the content window — REQUIRED, like KEL/SEL (2026-06-22)** [inv 13]. The IEL bounds the run of
  non-seal-advancing events between seal-advancing (privileged) events at `(MINIMUM_PAGE_SIZE − 1)/2` = 64 (per lineage) — the **same**
  bound as the KEL and SEL — so a content-divergence repair (`Rpr` attaching at the divergence ancestor `v_{d-1}`)
  fits one page → cross-node-validatable. This is **not optional:** `Ixn` is content and does **not** advance the
  seal (only `Evl`/`Ath`/`Rev`/`Dth`/`Rpr`/`Trm`/`Wit` do — the one `Wit` kind, both facets; cold-5 B2), and **issuance — the frequent op — rides `Ixn`** (`anchors[]`),
  so without the cap the post-seal window grows unbounded and the IEL faces the same recovery-page pressure the
  KEL/SEL cap answers. (The IEL repair is a single `Rpr`, so it takes the **one** repair slot the atomic page reserves beside
  the two competing branches (`2·64 + 1 = 129` — area-kel) — **a repair *with* an eviction
  is still a single `Rpr`** (the `cut` folds in — the repair-and-evict fold, 2026-06-30, retiring the 2-event
  `{Rpr, Evl}` batch that would otherwise have needed a second slot, `2·64 + 2`); the KEL
  no longer carries a 2-event `[Rec, Rot]` batch either; the `Rot` follow-up was residue, dropped 2026-06-24.)
  A busy issuer that fills the window **re-seals with a roster-less `Evl`** (a pure re-seal — **omits `roster`** per inv 18; the seal advance via `previousSeal` is the change, *not* an empty `{add:[],cut:[]}`) — the IEL analogue
  of the KEL re-sealing via `Rot`, **reusing `Evl`, no new kind, no marker.** The re-seal `Evl` is **valid**
  (no added members → no consent needed; `t_govern` of the unchanged roster) and content-addressed like any event,
  so two identical re-seal `Evl`s at one position **dedupe** (idempotent re-seal) while a re-seal `Evl` vs a real
  `Evl` at one position diverges as `{Evl, Evl}` → terminal — exactly as any two privileged events would. Validation
  must **accept** a roster-less re-seal `Evl`. *(Closes the round-5 cold-review M1: the doctrine's "the IEL has no cap"
  was a pre-reshape artifact — true when every IEL event was privileged, false now that issuance rides `Ixn`.)*
- **Federation IEL = a restricted IEL** (`Fcp`/`Wit`/`Trm`; `Fcp` = its inception marker) whose roster is witness KELs directly. [inv 14]

## 2. Mined from the stub — buried implementation patterns (reshape-compatible; confirm before lock)
These predate the reshape but appear to survive it (`Ath` is still a positive inclusion list, so "is Y delegated by X?" still walks X's `Ath`s):
- **Delegation verifier walk — never materialize the cumulative delegated set** (it's unbounded). Stream X's IEL with the candidate(s) in scope, carry **bounded per-candidate scalar state** (`Ath` sets true), return scalars. State = O(candidates), never the full set.
- **Source-agnostic transfer pattern** — `transfer_iel_events` / `verify_iel_events_with` (parallel to KEL), one linear streaming pass; same verifier for merge / local-verify / anti-entropy.
- **Postgres modeling** — per-kind rows; **no cumulative-state denormalization** (chain log is source of truth); GIN on `delegated[]` only for ancillary/forensic queries, never for verification-time delegation checks.

## 3. Superseded — do NOT carry forward
- **IEL-carries-policy** — `policies` field, `PoliciesSet` SAD, `policies["governance"/"delegation"/"sel"]`, `verify_iel_policy`. Gone; policy moved up to documents. [inv 1]
- **`Dip`** (delegated inception), **`Evl`** (→ `Evl`), **`Rsc`-as-an-event** carrying `delegated` removals (→ rescission is a derived **lookup SEL**, [inv 10]), the **`Delegate(X)` policy node**.
- **Seven kinds** (`Fcp`/`Icp`/`Dip`/`Evl`/`Ath`/`Rsc`/`Trm`) → **six** (`Icp`/`Ixn`/`Evl`/`Ath`/`Rpr`/`Trm`); **now seven** with the sealed kill-anchor `Kil` (`Icp`/`Ixn`/`Evl`/`Ath`/`Kil`/`Rpr`/`Trm`, 2026-06-21 — later split into `Rev`/`Dth`); **now eight** with the witness/federation kind **`Wit`** (`Icp`/`Ixn`/`Evl`/`Ath`/`Kil`/`Rpr`/`Trm`/`Wit`, 2026-06-28 — `Fed` was renamed/merged to `Wit`, the one kind that does both user binding and federation governance). **The kind shown as `Ath` here was named `Del` until 2026-07-04**, when it was renamed/generalized to the unified "authorize a party to act" anchor — `delegates` (delegation) **or** `anchors`→SEL `Gnt` (doc-membership grant); see the §1 kinds table. The single kill-anchor `Kil` was later split into **`Rev`** (`t_govern`, revoke an owned artifact) and **`Dth`** (`t_authorize`, deauthorize a grant), so the current general/user IEL is **9 kinds** (`Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Rpr`/`Trm`/`Wit`). The **federation** IEL is the restricted set `Fcp`/`Wit`/`Trm` (`Fcp` = its inception marker).
- **"IEL is content-free; no divergent state"** — *partially* superseded: the IEL gained a divergeable content
  kind (`Ixn`), but the protection **survives for establishment events** (`Evl` / rotations stay
  terminal-on-divergence, §1/§4★). Not a blanket reversal.

## 4. Open / route to the adversarial pass (load-bearing)
- **★ The sealed kill-anchors `Rev` / `Dth` — RESOLVED (kill = sealed/T2, Jason 2026-06-21; split into two kinds 2026-07-04).**
  A kill (a cred-SEL `Trm`, a lookup-SEL rescission `Trm`) no longer rides `Evl`; it rides a **dedicated sealed
  kill-anchor** (T2; **no roster delta**; but **forces a `Rot`** like `Evl` — a T2/permanent act needs a ≥T2 KEL
  anchor; the distinction is the roster delta, not the rotation — A). `Evl` is now **roster/threshold-change only**
  (always `t_govern`). This closes **S1** (a roster change can't be priced at a kill's count — the old
  `Evl`-anchors-a-kill-while-changing-the-roster conflation is gone). *(**R3-2 corrected 2026-06-27, A:** a kill is
  **not** "signatures, not a rotation ceremony" — a T2/permanent kill-anchor forces a `Rot` like `Evl`; the real
  distinction is the **roster delta** (S1), which the kill-anchors lack, not the rotation.)* The count is **backed**
  at the IEL walk and **demanded** by the anchored kill's kind, so every IEL kind prices itself ([inv 12]) and
  IEL-validity needs no SEL input. *Principle (evolved):* the kill was **first parametrized** (2026-06-21) as one
  `Kil` kind carrying a `threshold` slot (`govern` vs `authorize`) — parametrize when it's one job at multiple
  gravities. **On 2026-07-04 it was split** into **`Rev`** (revoke an owned artifact, `t_govern`) and **`Dth`**
  (deauthorize a granted authorization, `t_authorize`): a kill genuinely spans **two governance domains** (your own
  artifact vs a grant to another party), so they are distinct jobs, not one-job-two-gravities. The split **retires
  the `threshold` slot-name field** and removes the last count-parametrized kind (every kind now prices from exactly
  one slot), and pairs `Dth` symmetrically with `Ath` (grant → deauthorize). *(Split into separate kinds for
  different jobs — `Evl` = change the roster, `Rev`/`Dth` = seal a kill.)* *(**R3-1 RESOLVED (2026-06-21): no merge — corrected rationale (round 4).**
  `{kill, kill}` of **distinct** kills is terminal → reincept. You can't **reorder** events (SAIDs lock `previous`) or
  **archive a privileged event**, so a "merge" isn't a reorder — it's *removing* both kills and **re-authoring**
  new ones with the full `t_govern`/`t_authorize` (enough devices re-signing), a carve-out against
  privileged-divergence-is-terminal. Kills **commute** (key-less → no resurrection), so it's sound *in principle* —
  declined for model-cleanliness / don't-relax-finality, **not** the wrong "zero availability gain" (a merge would
  keep the identity; no-merge = reincept + reissue). Identical kills **dedup** (same target/position → same SAID),
  so only distinct kills collide — rare, avoided by serializing kills. Decouples R3/R3-8.)* [inv 11, 12, 13, 15]
- **★ Divergence scoped to `Ixn` — RESOLVED (Jason 2026-06-20), locked.** Pre-reshape doctrine made *every*
  IEL event privileged/terminal-on-divergence. The reshape makes only `Ixn` (T1, advances no key state)
  divergeable-and-repairable via `Rpr`; **`Evl` and all rotation/establishment events stay terminal-on-
  divergence.** *Rationale (load-bearing):* a repair means *picking a branch*; picking among competing
  *rotation* branches would **reverse a rotation and resurrect a retired key** (the backdate/resurrection
  class). A T1 `Ixn` advances no key state, so reconciling its ordering reverses nothing — safe to repair. The
  "can't go backward" protection is therefore *preserved* for establishment events; only the content layer
  gained divergeability. The adversarial pass may still probe the boundary (an `Ixn` repair that indirectly
  moves key state; any establishment-ish kind that could smuggle a reversal), but the decision + rationale are
  locked.
- **★★ A governance change during a network split (F7) — RESOLVED, REFINED 2026-06-21; witness-scoped 2026-07-02.**
  When the network splits, one half can change the roster (a `Evl`) while the other half keeps issuing content. Both
  land at the same chain position; on heal they collide. **Under the majority floor (federation §1e) the collision
  mostly doesn't form:** a half holding only a witness *minority* has its content stall sub-majority (fail-secure —
  never witnessed; non-witness nodes defer it), so that side contributes no live branch — the `Evl` (privileged —
  witnessed, federation §1e) wins and the stalled content re-issues, a no-collision. The collision still forms when the
  *content* half holds the witness majority (its content is witnessed; the `Evl` co-witnesses on heal) — and
  resolves exactly as below. **The refinement (the tier rule, inv 13):** a collision of **governance vs.
  content** is **recoverable** — the repair **keeps the governance change and archives the content** (you never
  overturn a `Evl`; content is archivable and re-issuable). So `Evl`-vs-content does **not** brick. The identity
  only bricks when **both halves did governance** (`Evl`-vs-`Evl`, or a branch carries two privileged events) —
  then neither branch can be archived → reincept. An attacker can still force the brick by inducing a split **and**
  getting both honest sub-quorums to perform governance, but the everyday case (one side governs, the other just
  issues) now recovers.
  **Decision: handle the residual operationally, not in the protocol** — but the bar is now only "don't let both
  sides do governance during a split." (1) One designated governance submitter (everyone hands that person their
  signature) so two governance events never race. (2) Under a suspected split, hold off on governance until the
  network is clearly back. (3) A `{Evl, Evl}` brick recovers by reincept — witnesses make it **detectable** on
  heal. **Rejected: a protocol check that blocks a `Evl` unless its parent is witness-confirmed** — during a split
  each half's own witnesses confirm that half's events (they report, they don't pick a winner), so the check passes
  inside the split; and if a half lacks enough witnesses it freezes all governance (a halt-by-DoS lever).
  Ineffective *and* a new weakness. *(Precedent: kels' Multi-Party Governance Synchronization. NB: kels' old "Raft"
  registry is removed — don't carry that name.)* [→ §5 land: operations note]
- **Rescission semantics — RESOLVED in the delegation area** (`vdti-area-delegation.md` §4). The stub's
  "retroactive-invalidate-all" was the *oldest* conception, superseded *before* the reshape by
  grandfather-to-cutoff (the `T_rev` generation); the reshape changed only the *mechanism* (→ lookup-SEL). Not
  an IEL open.
- **Initial roster/threshold constraints** on a freshly-incepted (incl. delegated) IEL — is there any structural floor beyond Rule A?
- **Federation IEL's delegation surface — RESOLVED** (`vdti-area-federation-witnessing.md` §1a): no — a federation
  is a **restricted IEL** (`Fcp`/`Wit`/`Trm` only — `Fcp` is its inception marker, `Wit` its sole governance kind; no `Ath`, and no `Ixn` → never diverges → no `Rpr`).
- **`Trm`-vs-`Rpr` concurrency** under terminal-event precedence (design-pass §12 sub-detail).
- **Repair-authorizing roster when the `Evl` branch is retained — RESOLVED (Finding 14a, 2026-06-21).** When a
  `{Evl, content}` divergence is resolved by **retaining the `Evl` branch** (the content is an archival tail of
  content), the resolving `Rpr` authorizes under the **post-`Evl`** roster — the retained `Evl` is canonical, so the
  repair operates in the world after it. Any members the
  `Evl` *added* are already T1-consent-anchored (a precondition of that `Evl`'s validity), so the post-`Evl`
  authorizing set is well-defined with no new consent at repair time. (Both threshold bounds are re-checked on the
  post-delta roster at every roster-delta event — here the user-IEL `Evl` — inv 12.)

## 5. Drift → land backlog (canonical docs)
- **Write `docs/design/primitives/data/event-logs/iel/` fresh** from this note (no dir exists). Likely `log.md` / `events.md` / `merge.md` / `reconciliation.md` / `verification.md` (drop the pre-reshape `policies.md`). **`events.md` must carry the sealed kill-anchors `Rev` (`t_govern`) and `Dth` (`t_authorize`)**, the **`Wit` kind** (the one witness/federation kind — T3, `t_govern`, **`Wit`-anchored**, field-match **facet-specific**; on a **user** IEL it is the federation rebind — `{federation, federationPin}` exact-matched (C4) on every walk; on a **federation** IEL it is governance — roster + rotation, match = the witness-config only; general/user IEL is **9 kinds**), the **`Fcp` marker** (the federation IEL's inception kind, T2, founder-`Rot`-anchored — replaces the old federation `Icp`), and `Evl` = the **user**-IEL roster/threshold-change kind. The **federation** IEL is the restricted set `Fcp`/`Wit`/`Trm`.
- **The `Del → Ath` merge + the new SEL `Gnt` (2026-07-04) → land in `iel/events.md` + the anchoring matrix.**
  `Del` is renamed/generalized to **`Ath`** — the unified T2 `t_authorize` "authorize a party to act" anchor
  carrying **`delegates`** (IEL prefixes; act-for-delegator) and/or **`anchors`** (the downstream SEL **`Gnt`**
  grant; act-as-self; kind-strict `Ath.anchors → Gnt` only), **both roles permitted at once**. The
  external-authorization lifecycle: **add** via `Ath`, **remove** via `Dth` (rescind either). Propagate the
  `t_delegate → t_authorize` count rename + the kill-anchor split (`Rev` = `t_govern`, `Dth` = `t_authorize`;
  count implied by kind, the `threshold` slot field retired). New anchoring pair **`Ath ↔ Gnt`** (passthrough,
  beside `` `Rev`/`Dth` ↔ `Trm` ``). Rationale +
  the T2-non-archivable consequence: area-multi-party §7; the SEL `Gnt` row: area-sel.
- **The repair-and-evict fold (2026-06-30) → land in the `iel/` repair doctrine + the role-allowlist:** a `Rpr` may
  carry a `roster` role restricted to `cut` + `threshold` (no `add`); one event repairs *and* evicts at `t_recover`,
  superseding the two-event `{Rpr, Evl}` batch (cold-4 A2 retired). Propagate the **`t_govern ≤ t_recover` hard
  floor** (inv 12) to the threshold-bounds doc; add `Rpr`'s `cut`-only `roster` to the manifest role-allowlist +
  `event-shape.md`'s IEL role grid + per-kind field-presence; the timing-attack rationale (eviction must be atomic
  with the repair) belongs in the repair/merge doc. **Plus (dual review, 2026-06-30):** extend the **post-delta
  `≥ 2` / recoverability-ceiling re-check** to the `Rpr`-cut (inv 12); state the `Rpr`-cut + its `threshold` change
  are authorized at the **outgoing** `t_recover` (as `Evl` is `t_govern`-of-outgoing); and add an explicit
  **"`Rpr` roster SAD requires a non-empty `cut`, carries no `add`" content check** (no `threshold`-only `Rpr`; the
  allowlist gates the role's presence, not the cut-required / add-empty sub-restrictions);
  and enforce the **kind-set gate** so a `roster` `cut` rides a `Rpr` only where the kind set admits `Rpr` (a user
  IEL or the degenerate key-SEL IEL — never the federation, which has no `Rpr`).
- **`event-shape.md`** IEL sections are **reconciled to the reshape** — the current `Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Rpr`/`Trm`/`Wit` taxonomy is landed and the old `Dip`/`policies` shapes are gone (this backlog item is done).
- **Naming (Finding 12):** docs qualify `Trm` by layer (`KEL-Trm` / `SEL-Trm` / `IEL-Trm`) and use the
  **SEL `Pin`** (was SEL `Evl`) for the floor re-pin (the SEL re-seal is a **`Fld`**); the lookup-SEL rescission is a **`Trm`**. The IEL `Evl` is roster/threshold-change only.
- **Write an operations note** (mirror kels' `operations/multi-party-governance.md`, in plain words): one
  designated submitter for governance changes; pause everyday issuing during a governance change; hold governance
  while a network split is suspected; a split-bricked identity recovers by reincept (detectable on heal). This is
  the F7 resolution — operator guidance, no protocol change. **Add a content-rail line (CORRECTED round-4, cold-S-D — the round-5 "recoverable all-content" was UNSAFE; witness-scoped 2026-07-02):** a
  split during **high-volume issuance** is recoverable **only within one seal-cap window** (≤ `(MINIMUM_PAGE_SIZE − 1)/2`
  = 64 content events): keep one branch, archive + reissue the other (SAIDs lock `previous` — can't interleave).
  **Beyond one window it is NOT recoverable** — both halves fill the cap and are *forced* to re-seal with a
  roster-less `Evl`; the two re-seals differ by `previous` → `{Evl, Evl}` → **terminal → reincept**. **On a witnessed
  chain the majority floor demotes this discipline from safety-critical to LIVENESS (federation §1e):** the
  witness-minority half's content never witnesses (every event reads sub-threshold — a loud fail-secure signal), and
  honest members following acceptance-gating never extend an unwitnessed tip into a re-seal `Evl` — so reaching
  `{Evl, Evl}` by cap-fill requires *ignoring* the signal and governing into a suspected split (negligence, not a
  race); the un-serialized cost is stalls + re-issuance. **For a direct-mode/solo chain the discipline remains
  SAFETY-critical** (nothing gates either half). So a high-volume issuer still **serializes its content submissions**
  (a fenced single content submitter — a discipline **separate from, and additional to,** governance/kill
  serialization, which **stays safety-critical everywhere**: an `Evl` is privileged, never gated by the floor). KEL analogue: an
  HA-replicated **reserve** lets two partition halves both `Rot` → a false `{Rot, Rot}` "reserve-compromise" — don't
  replicate the reserve across partitionable nodes. **Add a cred-SEL line (S2 aside):** a `t_use`-induced
  content-content divergence on a cred-SEL **freezes** it and **blocks a pending revocation** until a T3 `Rpr` (a
  `t_use`→delays-a-kill window — recoverable; the kill lands once the `Rpr` resolves the fork). Serialize cred-SEL
  content too where a timely revocation matters. *(Refined 2026-07-01: under a **linear** owner IEL a cred-SEL cannot
  fork — anchor-monotonicity makes a re-anchor inert (inv 4); a genuine cred-SEL fork rides an IEL fork and is
  repaired by the same IEL `Rpr` cascade, so the freeze-and-block window opens only on a real IEL fork, not a
  two-device SEL race — cold F1.)*

## 6. Confidence / what's owed
- §1, §3 — high confidence (direct from design-pass).
- §2 — medium; the patterns look reshape-safe but need a functional check against the new `Ath`/lookup-SEL shapes.
- §4 ★ — the divergeable-IEL question is genuinely load-bearing and unresolved; it should gate "IEL locked."
- Owed: confirming glance at `archived/vdti-iel-policies-audit.md`; the adversarial pass on §4.
