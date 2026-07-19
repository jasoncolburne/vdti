# vdti — area note: IEL (Identity Event Log)

**Status: FIRST CUT (2026-06-20) — also the area-note format exemplar.** Audited against the post-reshape
core. Load-bearing claims marked for the adversarial pass; nothing here is locked until it survives that.
**Invariants referenced:** [inv 1] policy-on-documents, [inv 2] single-locus, [inv 3] layers-isolated,
[inv 4] manifest-up/pin-down, [inv 5] pin-floored, [inv 11] tier, [inv 12] threshold-vector, [inv 13] divergence.

## Sources audited (disposition)
- `vdti-log-primitive-reshape-design-pass.md` §1–4, §12 + `vdti-federation-inception-reference.md` — **authoritative / current.**
- `vdti-iel-primitive-stub.md` (active) — **~90% superseded** (built on IEL-carries-policy); mine §Verifier-walk + §Postgres for patterns (→ §2 below), then archive. Stale-taxonomy banner is honest.
- `archived/vdti-iel-policies-audit.md`, `…-fix-applied.md` — flagged **superseded** (the whole "IEL policies" surface is gone); ⚠ not yet deep-read — confirming glance owed before lock.
- Canonical: `docs/design/primitives/data/event-logs/event-shape.md` — **reconciled to the reshape** (the `Ath`/`Rev`/`Dth`/`Wit` taxonomy encode landed 2026-07-04); a dedicated `iel/` dir is still to write.

## 1. Locked-candidate — the current IEL model
- **Layering — the chain validates STRUCTURE only (fail-secure re-review, 2026-07-10)** [inv 1, 4]. The IEL and SEL
  validate **structure**: event chaining, signatures, and their own **event-kind** schemas (and, for a SEL, the
  `topic` as an opaque **derivation input**). They **never** interpret topic *labels* or any application semantics,
  and **a chain never returns invalid because of the application it serves**. The cut is **kinds vs topic-labels**:
  `Rev`/`Dth`/`Ixn` are the chain's own vocabulary, so the IEL may key schema on them (`kills[]` is a field only
  `Rev`/`Dth` carry — a *schema* rule, kept); but `CRED_REVOCATION_TOPIC` and friends are **application vocabulary
  the chain treats as opaque bytes**. Everything decided *about* a topic — that a `CRED_REVOCATION_TOPIC` target
  must sit in a `Rev` (R2), that a re-anchored issuance commitment is never consulted — the cred's `issuerPin` fixes the position (R1) — lives at the **cred / delegate /
  doc feature layer**, which reads the (structurally-valid) chain and enforces its own rules. So an application bug
  can never make a chain read invalid: the chain **accepts** the well-formed event; the feature layer decides what
  it *means*.
- **IEL = one identity = a threshold over member KELs** (roster + threshold *vector*). Not a policy host. [inv 2, 12]
- **8 kinds** (general/user IEL: `Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Trm`/**`Wit`**); a **federation** IEL is the
  restricted set **`Fcp`/`Wit`/`Trm`**, where **`Fcp`** is its inception marker (a structural disambiguator the
  verifier dispatches on — federation-ref §2 — **not** a trust carve-out; the config-pin still roots trust) and
  **`Wit`** is its governance kind (T2 — replaces `Evl` for the federation; cold-4 B1 / 2026-06-28; the federation
  has **no `Evl`**). *(The `Rpr` repair kind is **dropped** in the first-seen pivot — there is no repair event;
  content forks resolve first-seen + burial, sealed forks are `disputed`/terminal, and evicting a
  divergence-causing member rides an **`Evl` with a roster `cut`** — §4.)* The **one `Wit` kind** spans both
  layers: on a **user** IEL it is the federation rebind, on a **federation** IEL it is governance — `Wit` anchors
  `Wit` uniformly (anchor-kind); facet-specific field-match (§ the `Wit` row below):

  | Kind | Tier | Count | Role |
  |---|---|---|---|
  | `Icp` | T2 | all initial members (Rule A) | inception; pins initial roster. **User IEL only** — a **federation** IEL incepts **`Fcp`** (the marker), not `Icp`. |
  | `Ixn` | T1 | `t_use` | content / **SEL-binding manifest** (the `anchors` role — inv 4); **the divergeable/first-seen content kind** (→ §4). |
  | `Evl` | T1 added / T2 outgoing | all added consent (Rule A) ∧ `t_govern` of outgoing | **roster/threshold change** — carries a roster/threshold **delta** (`add` + `cut`, not a full snapshot — [inv 14]); **anchors no kills** (those ride `Rev`/`Dth`) but **anchors a SEL `Sea`** (the burying-seal recovery — `Sea ← Evl`, area-sel §1d). **Eviction of a compromised / divergence-causing member is an `Evl` with a roster `cut`** — one sealing event buries the fork *and* evicts, atomically (there is no repair-and-evict fold — there is no `Rpr`; §4). **Added members consent at T1** (sign + declare key commitments — they're joining, not rotating). **`t_govern` of outgoing approve at T2** — each reveals the rotation reserve via a `Rot` that anchors the `Evl` (this is "forces a `Rot`"). |
  | `Ath` | T2 | `t_authorize` | **the unified "authorize a party to act" anchor** (was `Del`, generalized 2026-07-04). Two manifest roles, **both permitted at once** (batchable; same cost): **`delegates`** — a positive inclusion list of delegate prefixes (the party acts **for the delegator**); **`anchors`** — the downstream SEL **`Gnt`**(s) it seals (a doc-membership grant; the party acts **as itself**; kind-strict — names **only** `Gnt`s). The **additive counterpart of the kill-anchors** (no own-state delta; seals a downstream **grant** at T2). **Forces a `Rot`.** Sealed-on-arrival; sealed, non-terminal. |
  | `Rev` | T2 | `t_govern` | **sealed kill-anchor — revoke an owned artifact**: via `anchors`, names the SEL `Trm`(s) it seals (**only** `Trm`s — kind-strict, C1) — a **revocation lookup-SEL** `Trm` (a cred's revocation) / app-SEL closure — **plus a `kills[] = [{target}]`** declaration (the fail-secure revocation, a **separate array alongside `anchors[]`**; `target = hash('{CRED_REVOCATION_TOPIC}:{owner}:{cred.said}')` — a flat domain-qualified hash, the walk's forward-match handle; **opaque to the IEL** — placement kind-strict is the only structural rule, the IEL never dereferences it; B1 fail-secure rework 2026-07-09). Carries **no roster delta** → can't mutate establishment state (closes **S1**). Count implied by kind (`t_govern`), **backed** by sigs at the walk. **Forces a `Rot`** (each `t_govern` member — a T2/permanent act needs a ≥T2 KEL anchor; the `Evl`-vs-kill-anchor distinction is the **roster delta**, not the rotation — corrects R3-2, A). Sealed-on-arrival; **sealed but NOT a terminal tip** — seals a kill on a *target*, not its host IEL, so the IEL continues (`{Rev, content}` is recoverable like `{Evl, content}`, the `Rev` branch surviving and the content buried); terminal only as one of ≥ 2 sealed branches. |
  | `Dth` | T2 | `t_authorize` | **sealed kill-anchor — deauthorize a grant**: via `anchors`, names the SEL `Trm`(s) it seals (**only** `Trm`s) — a lookup-SEL rescission `Trm` (delegation, doc-membership, **or** chat-membership) — **plus a `kills[] = [{target, bound?}]`** declaration (the fail-secure rescission, alongside `anchors[]`; `target = hash('{topic}:{owner}:{data}')` — a flat domain-qualified hash, `topic` = `DLG_RSC_TOPIC` (delegate) / `DOC_RSC_TOPIC` (doc-member); `bound` = the grandfather cutoff, one concept in two custody modes — **the inline-public `kills[].bound` field for a delegate** (un-withholdable), **the gated `bound` role on the SEL `Trm` for a doc-member or chat-membership rescission** (`kills[]` carries only the blind target — participant-blindness; chat-membership carries a per-lane bound list); **opaque to the IEL**; B1 fail-secure rework 2026-07-09, gated-role custody WF1 2026-07-13). The **polarity-inverse of `Ath`** (grant → deauthorize, same `t_authorize`). Carries **no roster delta**. **Forces a `Rot`.** Sealed-on-arrival; **sealed, non-terminal** (like `Rev`). |
  | `Trm` | T2 | `t_govern` | terminal; freezes all the IEL's SELs. |
  | `Wit` | T2 | `t_govern` | **the one witness/federation kind — `Wit` anchors `Wit` uniformly (anchor-kind); the field-match is facet-specific (Q3); `Wit` IS the rotation** (refreshes the signing key + rotation reserve; `pins = Wit.previous`). Two facets by layer: <br>**(user IEL) federation rebind** — records the identity's federation (`federation` prefix + `federationPin`, top-level). Anchored by member KEL `Wit`s (**kind-strict, T2 ↔ T2** — inv 4). The IEL `Wit`'s **two federation-binding fields `{federation, federationPin}`** (a **closed set** — no optional fields, cold-5 C4) must **match exactly** those of every anchoring KEL `Wit`, checked on **every walk** — so all `t_govern` anchoring members are pinned to the **same federation position** (cold-5 C5), and the IEL `Wit` records **only** what its members signed (auditable, never self-asserted). **Binding validation also checks the `federation` prefix resolves to an `Fcp`-rooted IEL** — a binding pointing at an `Icp`-rooted (user) IEL is malformed → rejected (Q2; trust still roots in the config-pin). The **identity's federation is the IEL's own authoritative binding** (its most-recent `Wit`/`Icp`); it inherits **nothing** sub-threshold or unmatched — so a lone/desync'd member KEL (it anchors a sub-threshold IEL `Wit` → verifiably broken, inert) **cannot straddle the identity** (cold-3 B2). **Initial binding rides the `Icp`** (which always carries the federation — there is no direct mode, federation §1d); a later `Wit` rebinds, under a **hard cap on `Wit`s/chain** (DoS — over-cap rejected, inv-14 pattern). During a rebind, members below `t_govern` lag on the old federation until they each rebind — bridged by **overlapping federation trust** (cooperative-migration only — federation §1d). **`{Wit, Wit}` terminal, `{Wit, content}` recoverable (cold-5 B2).** **A user `Wit` must change `federation` (the prefix) or `witnesses`** — a same-federation re-pin (advancing `federationPin` only) is **not** a `Wit` (it rides any body event), and a pure key rotation is a `Rot`, so a `Wit` that changes neither is a no-op → **rejected** (the old `Fed` rebind requirement survives on the **user** facet; the federation-governance facet has no such rule — below). <br>**(federation IEL) governance** — the analog of `Evl`, doing **everything** (roster add/cut **and** witness rotation), at **T2**. Every federation governance act is a `Wit` (the **terminal `Trm`** aside — terminate is **`Rot`-anchored** (kind `Trm`, not a `Wit`), and carries the federation `clock`, self-attesting under the new windows its `Rot`s reveal — the same clock carve-out, §1e/§1f), anchored by the participating witnesses' KEL **`Wit`s** (kind-strict, T2 ↔ T2) — a **rotation ceremony** (the *participating* witnesses refresh the signing key + rotation reserve) that may also carry a **roster delta** (`add`/`cut`); a synchronized **all-witness** rotation ~yearly is the operational norm (clean timeline advance + forward secrecy for all), **not** a hard per-`Wit` requirement (a non-participating witness keeps its open key-window until it rotates, **bounded by the 365-day `MAXIMUM_WITNESS_KEY_WINDOW` auto-expiry — §1f**). `pins` = the participants' **pre-rotation KEL tips** (`Wit.previous`) — the clock's `T_end` for retiring receipt keys + the honored-vs-off-ceremony commitment (§1a/§1f) — **plus, on a roster-add, the joiner's `Ixn.previous`** (a `T_join`, never a `T_end`; cold-7 F2). Carries the inline `clock` timestamp, (optional) roster delta, and the federation's **own witness-config** (`witnesses` — D1 / cold-7 F1). **The `Wit↔Wit` field-match here is the witness-config only (Q3, Jason 2026-06-28)** — and that matched `witnesses` is the **federation's new config the approvers jointly endorse** (a consensus vote: each approver's KEL `Wit` carries it, all matching the IEL `Wit`'s — exactly analogous to the user facet's `{federation, federationPin}` consensus), **not** a member's independent KEL-event config (D1's "per-layer independent / not matched" describes a **user** IEL vs its member KELs — different chains; the federation's witnesses **are** its members, so they jointly govern the one federation config — cold-9 C1). **The roster delta does not match** (it rides the IEL `Wit`'s manifest, `Evl`-style — SAID-committed, anchored by the `t_govern` member `Wit`s; each member endorses the exact delta by anchoring the IEL `Wit`'s SAID), and the **`clock` does not match** (one authoritative value on the IEL `Wit`, monotonic + `≤ now+CLOCK_TOLERANCE_BAND` — §1f). **The federation `Wit` is *self-attested* by its witnessed KEL anchors (Q1)** — not gated on a separate aggregate receipt count, so an all-witness rotation never bricks (inv 4:`witnesses`). **`{Wit, Wit}` terminal. Roster-add consent (A1):** a *joining* witness consents via a KEL `Ixn` alongside (joining-not-rotating — the user-`Evl` joiner pattern), the pre-add witnesses approve via their KEL `Wit`s — **`t_govern` counts only KEL `Wit`s whose author ∈ the pre-add (outgoing) roster** (cold-8 F5), so a colluding `W_new` authoring a `Wit` can't manufacture a vote; the **kind split** (`Ixn` joiner vs `Wit` approver) is the *secondary* backstop keeping the joiner's consent out of `t_govern` (Rule-A only, restoring the C6 backstop) — diagram example 6. **Why roster + rotation in one kind** (vs §4's "split different jobs") — read the invariant first, then the per-facet mechanism: **a `Wit` is *never* a no-op** (a bare KEL rotation with no IEL `Wit` to anchor is a `Rot`, not a `Wit`), but *what* makes it non-trivial is **facet-specific** — the user facet states an explicit must-change because its rotation **alone** would be a plain `Rot`, while the federation facet's rotation **is itself** the change. <br>• **User facet** — a user `Wit` is a **rebind**: it **must change `federation` or `witnesses`** (a same-federation re-pin advancing only `federationPin` rides any body event, not a `Wit`; a pure key rotation is a `Rot`), so a user `Wit` changing **neither** is a no-op → **rejected**. <br>• **Federation facet** — a federation `Wit` is **governance**: it is **always a rotation** (the participating witnesses refresh signing + recovery; the IEL `Wit` **pins** their pre-rotation KEL tips, the member KEL `Wit`s **anchor** it, kind-strict, T2 ↔ T2) **and advances the monotonic `clock`**, with a roster delta **optional on top** — so the **rotation + clock advance IS the change**, and there is **no** "must change `federation`/`witnesses`" predicate. *(The federation chain carries **no `federationPin`** to ratchet — F3, cold-10; the remodel dropped the A2 must-also-change-roster framing. The earlier "the federationPin ratchets" phrasing here was a user-facet field wrongly attributed to the federation facet — corrected 2026-06-30.)* |
  | `Fcp` *(federation IEL only)* | T2 | all founders (Rule A) | **federation inception marker** — the federation IEL's inception (replaces the old federation `Icp`; 2026-06-28). Anchored kind-strict by each founder's KEL **`Rot`** (T2 ↔ T2 — genesis `Fcp → Rot`, federation §1c). Carries the initial roster, the initial **witness-config** (`witnesses`), and the initial **`clock`** (the founders' `T_join` = genesis time). The marker lets a verifier **recognize** a federation IEL from its own data (restricted kinds, exclude-self witnessing) — **interpretation, not trust** (the config-pinned `FEDERATION_IEL_PREFIX` still roots trust; the self-witnessing carve-out killed in federation-ref §4 does **not** return). **The `Fcp` is *checked* at two times (Q2, Jason 2026-06-29): during witnessing checks** (resolving `roster(F @ context)`) **and during federation-binding validation** — the latter **rejects** a user `{federation, federationPin}` whose target prefix is **not** `Fcp`-rooted (a binding pointing at an `Icp`-rooted user IEL is malformed). *(Plus its structural role as the **spine root** of the federation IEL — `previousSeal` walks terminate there, inv 17 — same as any inception.)* |

- **`roster` = KELs only.** No aggregate-of-IELs recursion; identity composition lives in the policy/document layer. [inv 1]
- **Threshold vector** `{ use, authorize, govern }` (the **count** axis, ⊥ tier — inv 11; `t_recover` is
  **dropped** — no repair, no recovery reserve); Rule A (unanimous-additions); removal of a member is an **`Evl` with
  a roster `cut`** (one sealing event evicts + buries; there is no `Rpr`-cut fold — inv 13). **Bounds (F-K, inv
  12):** `t_use ≥ 1`; the authority kinds (`t_govern`/`t_authorize`) have **two bounds of different kinds** — **`≥ 2`**
  (security: no single-member authority — **hard, every identity**) and **`≤ |roster| − 1`** (recoverability:
  evict/recover without one — **advisory only at `|roster| = 2`** (verifier accepts, wallet warns), **hard at
  `|roster| ≥ 3`** for every identity); singleton → all = 1. **Plus an authorization floor: `t_govern`, `t_authorize >
  |roster|/2`** (2026-07-08 — closes the disjoint-quorum attribution loss; `t_use` is **exempt**, content being
  first-seen / recoverable). A **2-member identity is valid but unrecoverable** (warned — a compromised device can
  *freeze* you, not just self-lockout; add a 3rd key). **At `|roster| ≥ 3` a threshold `= |roster|` is rejected**
  (gratuitous hostage — Finding 3); recoverable governance needs `|roster| ≥ 3`. **The roster is hard-capped at `MAXIMUM_ROSTER_SIZE`**
  (a DoS backstop — the verifier rebuilds the roster in memory as it walks; any delta pushing the live set past `MAXIMUM_ROSTER_SIZE` is
  rejected). [inv 11, 12; G1]
- **Two distinct floors — don't conflate (2026-07-10).** The **witnessing floor** (`threshold > signers/2`, over
  the **witness signers** — federation §1e) and the **authorization floor** (`t_govern`/`t_authorize > |roster|/2`,
  over the **roster members** — above) are distinct thresholds over distinct sets; the **position gate** is the IEL
  applying the **witnessing floor at its own `(prefix, serial)`** (option (b), federation §1e). Both are separate
  again from the **roster-floor `|roster| ≥ 1`** (never-emptied) and the **security floor `≥ 2`**. [inv 12]
- **Threshold declaration (locked 2026-06-25).** The **`Icp` declares the active threshold set** — exactly the
  authority kinds the IEL will ever use — **a threshold is declared iff its consuming kind is in the IEL's kind set**
  (`Ixn`→`t_use`, `Ath`/`Dth`→`t_authorize`, `Evl`/`Rev`/`Wit`/`Trm`→`t_govern`). A **user** IEL → `t_govern`
  **mandatory**, `t_use` + `t_authorize` **optional and lockable**; a **federation** IEL (`Fcp`/`Wit`/`Trm` —
  no `Ixn`/`Ath`) declares **exactly `{ govern }`** (`t_use`/`t_authorize` forbidden → a federation
  `Fcp` declaring any is malformed, rejected — the threshold-declaration analog of the facet-dependent role allowlist,
  2026-06-29). A kind **omitted at `Icp` can never be exercised** (no first-introducing it on a later event). Thereafter
  a roster delta carries a threshold field **only when it changes** (present ⇒ **must** change; absent ⇒ unchanged)
  — the same present=delta / absent=inherit shape as the membership `add`/`cut` and the federationPin re-pin. [inv 12]
- **`Evl` carries a roster/threshold *delta* (`add` + `cut`), no separate floor** (append-only chain is the floor;
  current roster = **accumulate every delta while walking**, with the hard live-set cap — [inv 14]; **not** "latest `Evl`"). [I2]
- **Manifest is role-qualified (inv 4).** An IEL event's `manifest` groups what it commits to above by named role
  ("the things this event {anchors/roster/delegates/…}"): `Icp`/`Evl` (user) → `roster` (the roster/threshold delta
  SAD — an `Evl` `cut` also carries the eviction); a
  **federation** `Fcp`/`Wit` → `roster` + `clock`, the terminal `Trm` → `clock` (the inline timestamp value — the federation has no `Evl`, `Wit` is its sole governance kind; `Trm` carries the clock but no roster);
  `Ath` → `delegates` (delegate prefixes, act-for-delegator) + `anchors` (the SEL `Gnt`s it seals, opt — kind-strict); `Ixn` → `anchors`
  (anchored SEL events **and a credential's issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** at issuance (an immutable SAD, no cred-SEL — issuance SEL dropped 2026-07-09; the anchor is the validity proof); **anchor-monotonicity, inv 4** — the anchor extends that SEL's latest IEL-anchored tip (a re-anchor is malformed/inert); its **fork-prevention/total-order reading is RETIRED (witnessed-SEL redesign, 2026-07-12)** — a SEL *does* fork under a linear IEL (opaque anchors + skip-unattributable), so fork-prevention is the SEL's **own witnessing**, area-sel §1c); `Rev`/`Dth` → `anchors` (the SEL `Trm`s it seals —
  `Rev` names revocation lookup-SEL `Trm`s (a cred's revocation, `t_govern`), `Dth` names lookup-SEL `Trm`s (`t_authorize`) — batched) **+ `kills` (new — `[{target, bound?}]`, the revocation/rescission declaration: `target = hash('{topic}:{owner}:{data}')` (a flat domain-qualified hash; per-kind `topic`; the target **mirrors the killed address** (area-sel §1f): **non-lineaged** `hash('{topic}:{owner}:{data}')` for a **monotone kill** (cred revocation, delegate / doc-member rescission), **lineaged** `hash('{topic}:{owner}:{data}:{lineage}')` for a **value rescission** (scoped to the one instance it kills, so the re-established `lineage: N+1` survives), and a literal **`:content`** segment for a **content (app-SEL) closure** (mirroring the `content: true` prefix). A value's positive resolution reads its own SEL chain; its per-lineage negative check consults this lineaged target), `bound` rescission-only; kind-strict, uniform across `Rev`/`Dth`; **opaque to the IEL** — the IEL never dereferences a target or interprets a bound, placement is the only structural rule)**. The federation `prefix`/`federationPin` (on `Icp`/`Wit`) stay
  **top-level structural** (the event's own links). **The killed locus is named by `kills[].target`** (a flat qualified hash — this resolves the earlier "no prefix in the kill-anchor"; `anchors[]` names the sealing `Trm` (termination validity), `kills[]` names *what* is revoked (the declaration) — two separate roles, two separate concepts; the target ≠ the lookup SEL's prefix, so `kills[]` doesn't leak the object's address).
- **Down-pins are top-level structural, not a manifest role (`pins`, locked 2026-06-25)** [inv 4]. The complement
  of fresh participation (inv 5): a member participates by anchoring a fresh KEL event **up** to the IEL event — of
  **exactly** the kind that reveals the capability it exercises (**kind-strict, inv 4:** content ← KEL `Ixn`; T2
  establishment/governance/kill/terminal ← KEL `Rot` (incl. the federation `Fcp` inception, and the IEL/federation
  `Trm`, all ← KEL `Rot`); **T2 witness/federation (IEL `Wit` — the user federation-binding AND federation
  governance, uniformly) ← KEL `Wit`** (the one `Wit` kind is the rotation; facet-specific field-match)). The
  IEL event records the **down-pins** — each participating member's **prior KEL tip** (the event its fresh
  participation *extends* — `participation.previous`, the SEL `pin → anchor.previous` analog, so the IEL's `said`
  never depends on the participation events that anchor it; no SAID cycle, cold-3 B1) — as **`pins`**, a top-level
  field (a scalar SAID → a small **pins-SAD**, since the list can't be an inline event-body field). Every IEL event
  is anchored by a threshold of members (inv 12), so **every IEL event carries `pins`**. A **federation** `Wit`'s
  `pins` are the participants' `participation.previous`: the approvers' **pre-rotation witness KEL tip SAIDs**
  (`Wit.previous`) — the clock's `T_end` for the retiring receipt key + the cold-F7 commitment that lets a verifier
  tell an honored synchronized rotation from an off-ceremony `Rot` — **plus, on a roster-add, the joiner's
  `Ixn.previous`** (a `T_join` for the joining key, never a `T_end`; cold-7 F2). (A **SEL**'s analog is the singular top-level `pin` → its owner IEL event.)
  `pins`/`pin` are kept top-level so a verifier walks the layered structure **without fetching the manifest**; the
  manifest is for content commitments. *(Exact pins-SAD schema + any per-kind nuance: this doctrine pass.
  `sealPins` — a seal-level analog — was dropped: divergence-view only, subsumed by the flat walk, inv 17.)*
- **Read the manifest kind-first (inv 4 F1) — load-bearing.** Each kind may carry **only** the roles in
  `allowed(kind)` above; a role outside it is **malformed → rejected**. **For `Wit`, `allowed(kind)` is *facet-dependent* (cold-8 F3):** dispatched on the **root** — a `Wit` on an `Icp`-rooted (user) chain may carry `{federation, federationPin}` (top-level) + `witnesses`, and **must not** carry `roster`/`clock`; a `Wit` on an `Fcp`-rooted (federation) chain may carry `roster`/`clock`/`witnesses`, and **must not** carry `{federation, federationPin}`. So the verifier **establishes the chain's root facet (`Fcp` vs `Icp`) before reading the `Wit` payload** on **every** `Wit`-reading path — the from-scratch walk, a `resume` from a cached token, **and** a `search_only` walk that ends early (cold-9 Q3); the **verification token carries the root facet** so a `resume` can't process a `Wit` payload facet-blind. A facet-blind allowlist would admit a governance-shaped payload (a roster delta) on a user `Wit` — and since the kind→role allowlist is the *only* gate on the directly-consumed governance roles, **"facet dispatch on every `Wit`-reading path" is a done-criterion** for the doctrine-land + impl. Critically, the *directly-consumed* roles
  (`roster` on `Icp`/`Evl` (user) — the `Evl` `cut` also evicts — or `Fcp`/`Wit` (federation); `delegates` on `Ath`, `clock` on a federation `Fcp`/`Wit`/`Trm`, **`kills` on `Rev`/`Dth`**) have **no** downstream
  type-check — the kind→role gate is their *only* protection, so an `Ixn` carrying `roster`/`delegates`/**`kills`**
  must be rejected (else governance/grants/**revocations** at `t_use` → **S1** reopens). **`kills` is directly consumed by the fail-secure walk** (it names *what* is revoked — the walk forward-matches `kills[].target`), so it is **kind-strict to the T2 `Rev`/`Dth`**: a `kills` on a T1 `Ixn` is malformed → rejected, closing declare-a-revoke-at-`t_use`. The sealed `Trm` object is *additionally* back-checked (a SEL `Trm` demands a `Rev`/`Dth`) — that back-check keeps the *object* sealed; the kind→role gate keeps the *declaration* T2. The label is checked against the kind, never trusted on its own.
  (`anchors` is additionally back-checked when the referenced SEL event is validated against its required kind —
  incl. the rule that a `Trm` is valid only anchored by a `Rev`/`Dth` — **this back-check is now what keeps kills sealed,
  replacing the former `revokes`/`rescinds`-are-`Kil`-only binding**; and the matrix is **kind-strict** both
  directions (a `Rev`/`Dth` anchors only `Trm`s, an `Ath` only `Gnt`s, an `Ixn` only content/v1, an
  `Evl` only `Sea`s — tier-elevation is an additional floor, not the check, inv 4 C1).)
- **Witnessing is scoped by chain (first-seen pivot, 2026-07-08)** [inv 13]. The IEL is a **mixed** chain — its
  content (`Ixn`) is single-key-authorable, its sealed spine is not — so the two buckets split by the one test (*could a
  single already-revealed secret author a competing sealed sibling?*):
  - **Content (`Ixn`)** → **first-seen**: witnesses take the first content event at a position and decline the
    copies; a **user** IEL's content additionally must reach a **majority quorum at its own `(prefix, serial)`** (the
    option-(b) position gate), which — with the witnessing floor — closes the two-disjoint-sub-quorums content fork.
    A content conflict is **recoverable**: the next sealing event (or the agreed next content) buries the
    loser below the seal (deadness-ascends), no repair event.
  - **Sealed (`Evl`/`Ath`/`Rev`/`Dth`/`Wit`/`Trm`)** → **record-both (detected, never buried) — but witnessed
    first-seen now, one sibling (revised 2026-07-11, cold F1):** witnesses sign the **first** sealed sibling at a
    position and decline later ones (like content — federation §1e), yet both branches are still **recorded/retained**
    so the data-local walk detects `≥ 2` → `disputed`; a sealed branch is **never buriable**, so a *second accepted*
    sealed branch is terminal. A threshold chain can't be forked by one stolen key (**except a singleton / `t_use = 1` roster,
    where one member acts alone**), so a second **accepted** sealed decision is proof the quorum was **subverted or
    the witnesses colluded** — surfaced loudly; a witness-**declined** sealed sibling is deferred-pending (a
    spent-preimage or partition race, no fault). `{Evl, Evl}` (any two **accepted** sealed branches) → **≥ 2 sealed →
    disputed → terminal → reincept**; `{Evl, content}` is **recoverable** (the `Evl` branch survives, the content is
    buried).
  The **federation** IEL is the pure case — every event is sealed → record-both; a competing sealed sibling is first-seen-declined (exclude-self peer-witnessing), so only a witness-colluded two-accepted conflict is a
  schism (disputed/terminal). [inv 4, 12, 13, 17]
- **Recovery + eviction — no repair event** [inv 13]. Recovery of a content fork is the **burying seal** above it
  (the winning branch's next sealing event seals past the loser; deadness ascends). **Evicting** a
  compromised / divergence-causing member is an **`Evl` with a roster `cut`** — one sealing event buries the fork
  **and** evicts, atomically (the eviction *must* be atomic, else the still-rostered member races fresh content at the
  resolved tip → re-fork; the `Evl` makes it atomic by construction — the member is gone the instant the fork
  resolves). The cut is priced the **outgoing** `t_govern` (pre-change — so an `Evl` can't lower its own gate then
  cut), the post-cut roster re-checked against the inv 12 bounds (a stranding / hostage cut is rejected, forcing a
  simultaneous `threshold` drop or reincept); the cut target is operator-chosen. There is **no** `Rpr` repair-and-evict
  fold — the eviction *is* an ordinary `Evl`. A member KEL going terminal (a reserve-theft takeover, no
  on-chain fork to challenge) is likewise handled by the quorum: it is inert alone, and the honest members evict it
  (an `Evl` `cut`) / `Dth` if delegated / reincept.
- **Divergence resolution turns on the sealed-branch count, node-agnostic** [inv 13]. The verdict rides **M**, the
  number of **sealed** branches past the fork (the content count N is irrelevant — all content is buriable):
  **M ≤ 1 = Forked** (recoverable — a content fork the burying seal resolves), **M ≥ 2 = Disputed → terminal →
  reincept**. A single sealed branch you didn't author (a takeover) is still *your* point of no return (reincept), but
  node-agnostically it reads Forked until a second sealed branch lands. The beacon propagates the branches; the
  data-local walk decides. [inv 13]
- **IEL distrust is forward-only (locked 2026-06-22)** [inv 12, 13]. An IEL event is trusted iff a **threshold** of members anchored it (fresh participation, inv 5), so a **rogue member KEL is inert alone** — it can't reach `t_use`/`t_govern`, so the quorum's "don't trust this" *is* **non-participation** (stop co-anchoring) **+ a `Evl` eviction**; you don't *also* anchor the rogue's attempts, and satisfaction is never met. A **retroactive** per-event distrust declaration is **forbidden** — a quorum that could retroactively un-trust its own history would hold the **backdate kill-switch** vdti closes. Trust is decided at participation time; an event the quorum co-signed (even alongside a since-compromised member) **stands**, and remediation is **forward** (revoke what it granted, evict the member). A member KEL un-resolvable at the KEL layer (clean adversarial multi-rotation — no divergence to challenge) **does not propagate** to the identity: the IEL evicts it and leans on the quorum. **No cut-member cap** (the member's own seal bounds its past; the SAID-pin bound survives only for delegate-rescission — inv 14 / delegation §5).
- **Seal-cap on the content window — REQUIRED, like KEL/SEL (2026-06-22)** [inv 13]. The IEL bounds the run of
  non-seal-advancing events between seal-advancing (sealed) events at `MAXIMUM_UNSEALED_RUN` (per lineage) — the **same**
  bound as the KEL and SEL — so a recoverable content fork + its burying seal
  fits one page → cross-node-validatable. This is **not optional:** `Ixn` is content and does **not** advance the
  seal (only `Evl`/`Ath`/`Rev`/`Dth`/`Trm`/`Wit` do — the one `Wit` kind, both facets; cold-5 B2), and **issuance — the frequent op — rides `Ixn`** (`anchors[]`),
  so without the cap the post-seal window grows unbounded and the IEL faces the same recovery-page pressure the
  KEL/SEL cap answers. (The burying event is a single ordinary sealing event (an `Evl`, or the `cut` `Evl` when it
  also evicts), so the atomic page carries the two competing content branches + the one burying seal — `2·MAXIMUM_UNSEALED_RUN + 1 =
  129`, area-kel; there is no separate repair event.)
  A busy issuer that fills the window **re-seals with a roster-less `Evl`** (a pure re-seal — **omits `roster`** per inv 18; the seal advance via `previousSeal` is the change, *not* an empty `{add:[],cut:[]}`) — the IEL analogue
  of the KEL re-sealing via `Rot`, **reusing `Evl`, no new kind, no marker.** The re-seal `Evl` is **valid**
  (no added members → no consent needed; `t_govern` of the unchanged roster) and content-addressed like any event,
  so two identical re-seal `Evl`s at one position **dedupe** (idempotent re-seal) while a re-seal `Evl` vs a real
  `Evl` at one position diverges as `{Evl, Evl}` → terminal — exactly as any two sealed events would. Validation
  must **accept** a roster-less re-seal `Evl`. *(Closes the round-5 cold-review M1: the doctrine's "the IEL has no cap"
  was a pre-reshape artifact — true when every IEL event was sealed, false now that issuance rides `Ixn`.)*
- **Federation IEL = a restricted IEL** (`Fcp`/`Wit`/`Trm`; `Fcp` = its inception marker) whose roster is witness KELs directly. [inv 14]

## 2. Mined from the stub — buried implementation patterns (reshape-compatible; confirm before lock)
These predate the reshape but appear to survive it (`Ath` is still a positive inclusion list, so "is Y delegated by X?" still walks X's `Ath`s):
- **Delegation verifier walk — never materialize the cumulative delegated set** (it's unbounded). Stream X's IEL with the candidate(s) in scope, carry **bounded per-candidate scalar state** (`Ath` sets true), return scalars. State = O(candidates), never the full set.
- **Source-agnostic transfer pattern** — `transfer_iel_events` / `verify_iel_events_with` (parallel to KEL), one linear streaming pass; same verifier for merge / local-verify / anti-entropy.
- **Postgres modeling** — per-kind rows; **no cumulative-state denormalization** (chain log is source of truth); GIN on `delegated[]` only for ancillary/forensic queries, never for verification-time delegation checks.

## 3. Superseded — do NOT carry forward
- **IEL-carries-policy** — `policies` field, `PoliciesSet` SAD, `policies["governance"/"delegation"/"sel"]`, `verify_iel_policy`. Gone; policy moved up to documents. [inv 1]
- **`Dip`** (delegated inception), **`Evl`** (→ `Evl`), **`Rsc`-as-an-event** carrying `delegated` removals (→ rescission is a derived **lookup SEL**, [inv 10]), the **`Delegate(X)` policy node**.
- **Seven kinds** (`Fcp`/`Icp`/`Dip`/`Evl`/`Ath`/`Rsc`/`Trm`) → **six** (`Icp`/`Ixn`/`Evl`/`Ath`/`Rpr`/`Trm`); **now seven** with the sealed kill-anchor `Kil` (`Icp`/`Ixn`/`Evl`/`Ath`/`Kil`/`Rpr`/`Trm`, 2026-06-21 — later split into `Rev`/`Dth`); **now eight** with the witness/federation kind **`Wit`** (`Icp`/`Ixn`/`Evl`/`Ath`/`Kil`/`Rpr`/`Trm`/`Wit`, 2026-06-28 — `Fed` was renamed/merged to `Wit`, the one kind that does both user binding and federation governance). **The kind shown as `Ath` here was named `Del` until 2026-07-04**, when it was renamed/generalized to the unified "authorize a party to act" anchor — `delegates` (delegation) **or** `anchors`→SEL `Gnt` (doc-membership grant); see the §1 kinds table. The single kill-anchor `Kil` was later split into **`Rev`** (`t_govern`, revoke an owned artifact) and **`Dth`** (`t_authorize`, deauthorize a grant). **The `Rpr` repair kind is dropped in the first-seen pivot (2026-07-08)** — no repair event, no `t_recover` — so the current general/user IEL is **8 kinds** (`Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Trm`/`Wit`). The **federation** IEL is the restricted set `Fcp`/`Wit`/`Trm` (`Fcp` = its inception marker).
- **"IEL is content-free; no divergent state"** — *partially* superseded: the IEL gained a divergeable content
  kind (`Ixn`), but the protection **survives for establishment events** (`Evl` / rotations stay
  terminal-on-divergence, §1/§4★). Not a blanket reversal.

## 4. Open / route to the adversarial pass (load-bearing)
- **★ The sealed kill-anchors `Rev` / `Dth` — RESOLVED (kill = sealed/T2, Jason 2026-06-21; split into two kinds 2026-07-04).**
  A kill (a revocation lookup-SEL `Trm` — a cred's revocation, or a lookup-SEL rescission `Trm`) no longer rides `Evl`; it rides a **dedicated sealed
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
  **archive a sealed event**, so a "merge" isn't a reorder — it's *removing* both kills and **re-authoring**
  new ones with the full `t_govern`/`t_authorize` (enough devices re-signing), a carve-out against
  sealed-divergence-is-terminal. Kills **commute** (key-less → no resurrection), so it's sound *in principle* —
  declined for model-cleanliness / don't-relax-finality, **not** the wrong "zero availability gain" (a merge would
  keep the identity; no-merge = reincept + reissue). Identical kills **dedup** (same target/position → same SAID),
  so only distinct kills collide — rare, avoided by serializing kills. Decouples R3/R3-8.)* [inv 11, 12, 13, 15]
- **★ Divergence scoped to `Ixn` — RESOLVED (Jason 2026-06-20); first-seen, 2026-07-08.** Pre-reshape doctrine made
  *every* IEL event terminal-on-divergence. Only `Ixn` (T1, advances no key state) is the **divergeable/first-seen**
  kind — a content conflict is recoverable (the burying seal drops the loser); **`Evl` and all key-change /
  establishment events are record-both → terminal-on-divergence** (≥ 2 **accepted** sealed **at the last seal** → disputed — revised 2026-07-11). *Rationale (load-bearing):*
  reconciling a content ordering reverses no key state; overturning a competing *rotation* / establishment branch
  would **resurrect a retired key** (the backdate/resurrection class), so those can never be buried — a second **witnessed** sealed
  branch at the last seal is disputed (a provable witness double-sign), and a **below-seal** sealed straggler is **dropped** (inert — it cannot retreat the clean seal, which _is_ the backdate defense: a total-key-compromise adversary can't mint a fabricated historical fork). The "can't go backward" protection is *preserved* for establishment events; only the content
  layer is recoverable.
- **★★ A governance change during a network split (F7) — RESOLVED, REFINED 2026-06-21; witness-scoped 2026-07-02.**
  When the network splits, one half can change the roster (a `Evl`) while the other half keeps issuing content. Both
  land at the same chain position; on heal they collide. **Under the witnessing floor (federation §1e) the collision
  mostly doesn't form:** a half holding only a witness *minority* has its content stall sub-majority (fail-secure —
  never witnessed; non-witness nodes defer it), so that side contributes no live branch — the `Evl` (sealed —
  witnessed, federation §1e) wins and the stalled content re-issues, a no-collision. The collision still forms when the
  *content* half holds the witness majority (its content is witnessed; the `Evl` co-witnesses on heal) — and
  resolves exactly as below. **The refinement (the tier rule, inv 13):** a collision of **sealed vs.
  content** is **recoverable** — the sealing event **survives and its seal buries the content** (you never
  overturn a `Evl`; content is buriable and re-issuable). So `Evl`-vs-content does **not** brick. The identity
  only bricks when **both halves sealed** (`Evl`-vs-`Evl`, or a branch carries two sealed events) —
  then neither branch can be buried → reincept. **Under one-sealing-per-position (revised 2026-07-11, cold F1) the honest double-seal is structurally
  prevented:** the witnessing floor stops two disjoint sub-quorums from each reaching `threshold`, and on heal
  first-seen **declines** the second sealed sibling (deferred-pending, never accepted) — an honest split yields **at
  most one accepted sealed branch** and resolves to it, never a brick. Two *accepted* sealed branches now
  necessarily mean **witness collusion** (a provable double-sign — the general witness-compromise residual), not a
  partition race. **The former operational bar ("don't let both sides seal during a split") is thereby subsumed** —
  kept below only as defense-in-depth, no longer a correctness requirement: (1) One designated sealing submitter (everyone hands that person their
  signature) so two sealing events never race. (2) Under a suspected split, hold off on sealing until the
  network is clearly back. (3) A `{Evl, Evl}` brick recovers by reincept — witnesses make it **detectable** on
  heal. **Rejected: a protocol check that blocks a `Evl` unless its parent is witness-confirmed** — during a split
  each half's own witnesses confirm that half's events (they report, they don't pick a winner), so the check passes
  inside the split; and if a half lacks enough witnesses it freezes all sealing (a halt-by-DoS lever).
  Ineffective *and* a new weakness. *(Precedent: kels' Multi-Party Governance Synchronization. NB: kels' old "Raft"
  registry is removed — don't carry that name.)* [→ §5 land: operations note]
- **Rescission semantics — RESOLVED in the delegation area** (`vdti-area-delegation.md` §4). The stub's
  "retroactive-invalidate-all" was the *oldest* conception, superseded *before* the reshape by
  grandfather-to-cutoff (the `T_rev` generation); the reshape changed only the *mechanism* (→ lookup-SEL). Not
  an IEL open.
- **Initial roster/threshold constraints** on a freshly-incepted (incl. delegated) IEL — is there any structural floor beyond Rule A?
- **Federation IEL's delegation surface — RESOLVED** (`vdti-area-federation-witnessing.md` §1a): no — a federation
  is a **restricted IEL** (`Fcp`/`Wit`/`Trm` only — `Fcp` is its inception marker, `Wit` its sole governance kind; no `Ath`, and no `Ixn` → sealed-only; a competing sealed sibling is **first-seen-declined** (exclude-self peer-witnessing, federation §1e), so only a witness-colluded **two accepted** sealed branches → disputed/terminal — revised 2026-07-11).
- **`{Evl, content}` recovery — RESOLVED (Finding 14a, 2026-06-21; first-seen 2026-07-08).** When a `{Evl, content}`
  divergence is resolved by the **`Evl` branch surviving** (its seal buries the content loser), there is no separate
  repair event — the `Evl` *is* the burying seal. Any members the `Evl` *added* are already T1-consent-anchored (a
  precondition of that `Evl`'s validity). Both threshold bounds are re-checked on the post-delta roster at every
  roster-delta event (here the user-IEL `Evl` — inv 12).

## 5. Drift → land backlog (canonical docs)
- **Write `docs/design/primitives/data/event-logs/iel/` fresh** from this note (no dir exists). Likely `log.md` / `events.md` / `merge.md` / `reconciliation.md` / `verification.md` (drop the pre-reshape `policies.md`). **`events.md` must carry the sealed kill-anchors `Rev` (`t_govern`) and `Dth` (`t_authorize`)**, the **`Wit` kind** (the one witness/federation kind — T2, `t_govern`, **`Wit`-anchored**, field-match **facet-specific**; on a **user** IEL it is the federation rebind — `{federation, federationPin}` exact-matched (C4) on every walk; on a **federation** IEL it is governance — roster + rotation, match = the witness-config only; general/user IEL is **8 kinds**), the **`Fcp` marker** (the federation IEL's inception kind, T2, founder-`Rot`-anchored — replaces the old federation `Icp`), and `Evl` = the **user**-IEL roster/threshold-change kind (an `Evl` `cut` also evicts). The **federation** IEL is the restricted set `Fcp`/`Wit`/`Trm`.
- **The `Del → Ath` merge + the new SEL `Gnt` (2026-07-04) → land in `iel/events.md` + the anchoring matrix.**
  `Del` is renamed/generalized to **`Ath`** — the unified T2 `t_authorize` "authorize a party to act" anchor
  carrying **`delegates`** (IEL prefixes; act-for-delegator) and/or **`anchors`** (the downstream SEL **`Gnt`**
  grant; act-as-self; kind-strict `Ath.anchors → Gnt` only), **both roles permitted at once**. The
  external-authorization lifecycle: **add** via `Ath`, **remove** via `Dth` (rescind either). Propagate the
  `t_delegate → t_authorize` count rename + the kill-anchor split (`Rev` = `t_govern`, `Dth` = `t_authorize`;
  count implied by kind, the `threshold` slot field retired). New anchoring pair **`Ath ↔ Gnt`** (passthrough,
  beside `` `Rev`/`Dth` ↔ `Trm` ``). Rationale +
  the T2-non-archivable consequence: area-shared-documents §7; the SEL `Gnt` row: area-sel.
- **Eviction is an `Evl`-with-`cut` (first-seen, 2026-07-08) → land in the `iel/` doctrine + the
  role-allowlist:** evicting a compromised / divergence-causing member is an **ordinary `Evl` carrying a roster
  `cut`** (there is **no** `Rpr` repair-and-evict fold — there is no `Rpr`). One sealing event buries the fork
  *and* evicts, atomically. The `cut` is priced the **outgoing** `t_govern` (pre-change); the post-cut roster is
  re-checked against the inv 12 bounds (`≥ 2`, recoverability ceiling, authorization floor, roster cap `MAXIMUM_ROSTER_SIZE`); a stranding /
  hostage cut is rejected, forcing a simultaneous `threshold` drop or reincept. The timing-attack rationale (the
  eviction must be atomic with the burying, else the still-rostered member re-forks the resolved tip) belongs in the
  merge/reconciliation doc.
- **`event-shape.md`** IEL sections must drop `Rpr` (first-seen, 2026-07-08) — the taxonomy is
  `Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Trm`/`Wit` (8 kinds; the old `Dip`/`policies`/`Rpr` shapes gone).
- **Naming (Finding 12):** docs qualify `Trm` by layer (`KEL-Trm` / `SEL-Trm` / `IEL-Trm`) and use the
  **SEL `Pin`** (was SEL `Evl`) for the floor re-pin; the lookup-SEL rescission is a **`Trm`**. The IEL `Evl` is
  roster/threshold-change only (its `cut` also evicts). *(The SEL `Fld` re-seal is dropped — no page-atomic repair
  requirement — §area-sel.)*
- **Write an operations note** (mirror kels' `operations/multi-party-governance.md`, in plain words): one
  designated submitter for sealing events; pause everyday issuing during a sealing event; hold sealed events
  while a network split is suspected; a split-bricked identity recovers by reincept (detectable on heal). This is
  the F7 resolution — operator guidance, no protocol change. **Add a content-rail line (CORRECTED round-4, cold-S-D — the round-5 "recoverable all-content" was UNSAFE; witness-scoped 2026-07-02):** a
  split during **high-volume issuance** is recoverable **only within one seal-cap window** (≤ `MAXIMUM_UNSEALED_RUN`
  content events): keep one branch, archive + reissue the other (SAIDs lock `previous` — can't interleave).
  **Beyond one window it is NOT recoverable** — both halves fill the cap and are *forced* to re-seal with a
  roster-less `Evl`; the two re-seals differ by `previous` → `{Evl, Evl}` → **terminal → reincept**. **On a witnessed
  chain the witnessing floor demotes this discipline from safety-critical to LIVENESS (federation §1e):** the
  witness-minority half's content never witnesses (every event reads sub-threshold — a loud fail-secure signal), and
  honest members following acceptance-gating never extend an unwitnessed tip into a re-seal `Evl` — so reaching
  `{Evl, Evl}` by cap-fill requires *ignoring* the signal and governing into a suspected split (negligence, not a
  race); the un-serialized cost is stalls + re-issuance. Since **every chain is federation-witnessed** (there is no
  direct mode), content-serialization is a **liveness** discipline everywhere — the residual safety concern is only a
  **witness compromise** (a byzantine quorum). So a high-volume issuer still **serializes its content submissions**
  (a fenced single content submitter — a discipline **separate from, and additional to,** sealing
  serialization, which **stays safety-critical everywhere**: an `Evl` is sealed, never gated by the floor). KEL analogue: an
  HA-replicated **reserve** lets two partition halves both `Rot` → a false `{Rot, Rot}` "reserve-compromise" — don't
  replicate the reserve across partitionable nodes. **Cred revocation is decoupled from cred content (B1 fail-secure rework 2026-07-09):** a credential is an
  **anchored SAD** (no issuance SEL) and revocation is a **`kills[]` declaration on the issuer's witnessed IEL `Rev`**
  (`t_govern`, sealed) + a sealed `{Icp, Trm}` lookup SEL, so a content divergence can't **freeze-and-block a pending
  revocation**: the `kills[]` rides a T2 `Rev` sealed on arrival and the cred SAD is immutable, so neither depends on
  any mutable SEL state. *(The general content-SEL principle still holds for **mutable** app/doc SELs:
  a `t_use` content-content divergence freezes *that* SEL until a SEL `Sea` (or an IEL burying seal)
  resolves it. A mutable SEL **can** fork under a **linear** owner IEL (the retired theorem — opaque anchors +
  skip-unattributable, area-sel §1c), so the SEL's **own witnessing** (first-seen at its `(prefix, serial)`) is
  what prevents an honest fork; the freeze window opens only on a **witness-compromise** content fork, not a
  two-device SEL race — witnessed-SEL redesign.)*

## 6. Confidence / what's owed
- §1, §3 — high confidence (direct from design-pass).
- §2 — medium; the patterns look reshape-safe but need a functional check against the new `Ath`/lookup-SEL shapes.
- §4 ★ — the divergeable-IEL question is genuinely load-bearing and unresolved; it should gate "IEL locked."
- Owed: confirming glance at `archived/vdti-iel-policies-audit.md`; the adversarial pass on §4.
