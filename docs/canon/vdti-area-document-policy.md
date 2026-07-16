# vdti — area note: Document / policy layer

**Status: IN-PROGRESS DESIGN PASS (2026-06-20).** The **foundational feature layer** — specced *first* (Jason's
call) because its requirements flow **down** to the primitives. This is a genuine design pass (not a reconcile),
but grounded in the archived policy-DSL canon + this session's cred work. **Invariants referenced:** [inv 1]
policy-on-documents, [inv 8] walk-semantics, [inv 10] negative-checks-are-lookup-SELs, + the two-function model
(`[needs-reconciliation]`).

## Sources to ground / reconcile
- `archived/vdti-12-policy-dsl.md`, `…-leaf-semantics`, `…-evaluation` (the pre-reshape DSL canon — reconcile).
- `archived/vdti-policy-pinning-model.md` (the anchored/current two-function model — reconcile, don't re-derive).
- This session: the worked cred examples; `vdti-area-delegation.md` §2/§5; the revocation correction
  (withdraw-`Ixn` + lookup-SEL status); F8 closure; the `project_vdti_credentials_layering` memory.

## Scope — the sub-questions this layer must answer
- **A. What a document / cred IS** — `{said, issuer, issuee, claims, issued, expires?, nonce?}` (**no `policy`** — who-may-present is challenge-the-issuee, not a policy; 2026-07-16). **[DONE — §A]**
- **B. The policy DSL** — leaves `id`/`del`/`pol` + composers `thr`/`wgt`/`and`; `dev` and `grp` dropped. **[DONE — §B]**
- **C. The evaluation function** — one shared composer + **one** leaf resolver (as-issued: anchoring position /
  as-of / on-chain proof). The current-mode function is **removed** (2026-07-16 — live checks don't compose;
  who-may-present is challenge-the-issuee, read-gating is a `readers` membership lookup, neither a policy). **[DONE — §C]**
- **D. Document context** — fixed by the **anchoring position** (no body `pin`, dropped 2026-06-26); multi-identity
  uses an `issuers[]` SAD + independent attestations. **[RESOLVED — §A]**
- **E. Policy-satisfaction matching** — how a server/verifier decides "satisfied" **is the shared composer of §C**
  (distinct-by-prefix counting · per-prefix-max weight · `and`-over-disjoint-pools · fail-secure-on-unknown ·
  `max_depth`/work caps); there is no separate satisfaction mechanism. Its **exact composer mechanics are imported at
  the feature encode** from the policy-DSL canon (SS-4). **[RESOLVED — = §C]**
- **F. Revocation** — a cred is a **direct-anchored SAD** (no cred-SEL; issuance commitment
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`); revocation is a **`kills[]` declaration** on the issuer's
  witnessed IEL `Rev` (`target = hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, a flat qualified hash) + a
  sealed `{Icp, Trm}` lookup SEL. Status = **fail-secure by default** (walk the fresh IEL, forward-match
  `kills[].target`); a content-addressed **fail-open** lookup is the opt-out (vdtid / walk-timeout).
  **[RESOLVED — §F / B1 reworked]**
  (Supersedes the earlier "`withdraw` `Ixn` on a shared registry" — that was a pre-reshape revert.)
- **G. Delegation in documents** — the `del(X)` node; the multi-delegator path commitment (delegation §5);
  the cred's transitive authorizing-chain commitment (delegation §2). [integrate]
- **H. Closure** — = **`Trm` the SEL** (T2 governance); supersedes the F8 derived-lookup-SEL. **[RESOLVED — §F]**

## ★ Requirements flowing DOWN to the primitives (the key output — accumulated as A–H are worked)
- **R1 — Chain-event authorization is STRUCTURAL, not policy-evaluated.** From C below: the reshape deletes the
  canon's gate evaluator. IEL/SEL events are authorized by the **threshold vector + tier** (IEL §12) and
  **single-owner ownership** (SEL), never by evaluating a DSL policy. So the policy DSL is a **pure
  document-layer concern** — the primitives carry no policy and need no policy evaluator for their own events.
  (This *confirms* [inv 1] and sharpens it: two distinct authorization mechanisms — chain = structural,
  documents = DSL.)
- **R2 — Primitive verification must produce reusable *tokens*.** The evaluator consumes verification tokens
  (chain state as-of a position / at tip), not raw chains. So KEL/IEL/SEL verification must be **tokenizable** —
  position-addressable and resumable ([inv 8] walk-semantics + the token-store idea + the `resume` function).
- **R3 — A document's anchoring position must source the as-issued resolver's inputs.** An anchoring position must yield
  (a) the state token at that position and (b) the committed on-chain anchors as proof — which
  pin-everything-floored [inv 5] + manifest/anchors already provide. The primitives must keep positions
  pin-addressable with roster/key state transitively committed.
- _(more as F–H are worked)_
- **R4 — Multi-source independence + multi-federation trust are policy/app-layer, not structural (F8, 2026-06-28).**
  F8's multi-source bar (inv 8) rests on *independent* sources, but **overlapping federation rosters** (a witness KEL
  can sit in several federations) mean a naive "two federations agree" can be **one shared witness** — so a consumer
  counts **distinct witness KELs**, never distinct federations. The composition primitives are already here: **`thr`**
  (distinct-by-prefix) + **`and`** (disjoint pools) — a document needing independence **establishes it in its own
  policy** and picks non-overlapping sources; the system guarantees no fixed independence. **Multi-federation
  operation is out-of-scope-but-allowed** — the per-federation, non-transitive trust model (federation-witnessing §1d)
  already lets an identity relate to several federations; no orchestration is added. **There is no direct mode** (removed,
  first-seen 2026-07-08 — federation-witnessing §1d / §6): every identity is federation-witnessed, so a user `Icp`
  **must** carry its `{federation, federationPin}` binding (a federated `Icp` omitting it is malformed → rejected,
  fail-secure — inv 4). The `Fcp` federation-genesis bootstrap is **not** direct mode (it is the config-pinned trust
  root — kept). So there is no unwitnessed early range and no receipt-less chain. **A loss-of-trust decision that
  can't multi-source-confirm fails-secure: REFUSE** (cold-5 C2), never proceed-with-a-flag. Witnessing is
  **range-based**, reported by the token **per range** (federation-witnessing §1d).

## Open decisions (the real design work, to adjudicate with Jason)
1. **Confirm the gate dissolves** (C) — chain-event authorization is purely structural (IEL threshold vector +
   SEL ownership); `policyPin` and the `governance`/`operation`/`authentication`/`delegation` policy-KINDS are
   gone. *(I'm confident, but it's load-bearing — confirm.)*
2. **`grp` — DROPPED (resolved 2026-06-20).** It pulled *subsets of an identity-aggregate's roster*; the reshape
   made rosters flat **device** sets + simple threshold, so there's nothing to pull. Identity composition =
   `thr`/`wgt`/`and` over `id()`. Dropping it collapses foreign-`grp`, the context-supplied marker, the
   roster-source slot, `GrpBlock`, and the DQ1 floor. Reusable *fixed* group → `pol`; reusable *evolvable*
   membership is **deferred to a feature if ever needed**, not a DSL primitive.
3. **Issuer context — RESOLVED (§A).** Fixed by the **anchoring position** (no body `pin`, dropped 2026-06-26);
   multi-identity uses an `issuers[]` SAD + independent attestation-SELs, not per-party pins.

## Worked — C (evaluation model) + B (leaf set) — 2026-06-20

### C. Evaluation model — the canon had THREE functions; ONE survives (as-issued)
The landed canon (`evaluation.md`) had three:
1. **`evaluate_gate_policy`** — anchored single-policy GATE for *chain governance events* (IEL `Evl`/`Trm`, SEL
   `Trm`), driven by the chain's floored pin.
2. **`evaluate_anchored_policy`** — multi-party anchored validity (cred *issuance*; parties present pinnings;
   resolves as-of).
3. **`evaluate_current_policy`** — challenge-response *current* control (attestations at chain tip).

**Reconciliation — the gate dissolved (R1), then the current-mode function dissolved too (2026-07-16):**
- **★ Function (1), the gate, DISSOLVES.** Primitives carry no policy [inv 1] → there is no chain-governance
  policy to evaluate. Chain-event authorization becomes **structural** (IEL threshold vector + tier, §12; SEL
  single-owner via manifest+pin). `policyPin` + the governance/operation/authentication/delegation policy-kinds
  go with it. → **R1.**
- **★ Function (3), the current-mode function, ALSO DISSOLVES (2026-07-16 — live-policy removal).** Live checks
  don't compose for a passive verifier, so there is no live policy composition to evaluate. What used it —
  who-may-present (creds), the document read gate — is **not** a policy: who-may-present is the single-identity
  **challenge-the-issuee** auth step (presentation exchange / IPEX), and read-gating is a **`readers`** membership
  lookup (a read-authorization SEL — shared-documents §5), neither evaluated by the composer. `evaluate_current`
  is removed. **Policies are as-issued only.**
- **Function (2), `evaluate_as_issued`, is the sole survivor** — was-it-validly-issued (as-of the anchoring
  position, committed on-chain anchors); the document layer's authorizing-condition check for a multi-identity
  issuer.
- **Rescission:** the canon's `del` self-traversal walks to *tip* for an `Rsc`; the reshape replaces that with
  the positive **lookup-SEL** check [inv 10] — no to-tip rescission scan.

**The function structure — one composer, ONE resolver (as-issued; current-mode removed 2026-07-16).** After the
current-mode function dissolves (above), a single evaluation function survives:
- **Shared composer** — the `thr`/`wgt`/`and`/`pol` logic (credited-set union, distinct-by-prefix counting,
  per-prefix-max weight, `and`-over-disjoint-pools, threshold check).
- **As-issued leaf resolver** — each leaf needs **state** (the chain's roster/keys, from a verification *token*,
  as-of the **anchoring position**) and **proof** (the **committed on-chain anchors** reached via that position —
  the proof is already in the chain). `del` resolves the same way (self-traverse + ancestry-to-cutoff, as-of; the
  rescission check is the positive lookup-SEL, inv 10 — no to-tip scan).
- **Shape:** `evaluate(policy, resolver)` is the composer; the as-issued entry point is the thin wrapper that
  assembles the resolver's inputs (the anchoring positions + the committed-anchor proofs).
- **Why no current-mode resolver:** live checks don't compose (a passive verifier can't gather async parties'
  live signatures), so there is no live policy composition. The live acts that *look* like a current policy —
  who-may-present (creds), a read gate (docs) — are **single-identity** authentication (challenge-the-issuee /
  challenge-the-requester) or a **membership lookup** (`readers`), neither of which is a policy; they live in the
  presentation exchange / the SAD read gate, not here. A chain's current-state freshness (divergence / staleness /
  revocation) is the **to-tip freshness step**, a separate thing from policy evaluation.

### B. Leaf set — reconciled (one real decision = grp)
- **`dev`** — **DROPPED** (reshape §4; `id(X)` resolves X's IEL threshold-over-KELs). Deletes the whole
  `dev_legal`/DQ2 placement-enforcement surface the canon spends much of `leaf-semantics`/`verifier-behavior` on.
- **`id(X)`** — kept; resolves X's IEL **roster + threshold** (structural), not "X's authentication policy."
- **`del(X, N)`** — kept; rescission via lookup-SEL, not a to-tip `Rsc` scan.
- **`pol` / `thr` / `wgt` / `and`** — kept; composition, reshape-neutral (keep the canon's mechanics: distinct-
  by-prefix counting, per-prefix-max weight, `and` over disjoint pools, fail-secure-on-unknown).
- **`grp`** — **DROPPED.** It pulled subsets of an *identity*-roster; reshape rosters are flat *device* sets +
  simple threshold → nothing to pull. Compose identities with `thr`/`wgt`/`and` over `id()`. Collapses
  foreign-`grp` / `GrpBlock` / context-marker / DQ1 floor.
- **policy-KINDS** (governance/operation/authentication/delegation) — **GONE** (chain auth is structural).

**Resulting DSL (after reshape):** leaves/reference = `id`, `del`, `pol`; composers = `thr`, `wgt`, `and`. Both
`dev` and `grp` dropped → the DSL is dramatically smaller, and the `dev_legal`/DQ2 + foreign-`grp`/DQ1 +
`GrpBlock` + `policyPin` machinery is all deleted. Keep the canon's surviving mechanics for the composers
(distinct-by-prefix counting, per-prefix-max weight, `and` over disjoint pools, fail-secure-on-unknown,
`max_depth`/work caps).

### A. What a document / cred IS — 2026-06-20 (cred = a per-cred SEL; refined 2026-06-21; cred = anchored SAD, B1 fail-secure 2026-07-09)

**A cred is an anchored SAD — not a SEL** (issuance SEL dropped, B1 fail-secure rework 2026-07-09 — area-sel §1),
plus — **iff it is ever revoked** — a **`kills[]` declaration** on the issuer's witnessed IEL and a content-addressed
lookup SEL.
- **Issuance = a direct-anchored SAD** — the issuer anchors the **issuance commitment
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** on its own IEL via an **`Ixn`** (`manifest.anchors` names
  it); **that anchor is the validity proof** (an issuance commitment with no resolvable anchor on the issuer's fresh
  IEL is not validly issued). **No registry object / identifier**, **no cred-SEL** (the cred is immutable and
  presented by the holder — never looked up by address). As-of = the **anchoring position** (inv 5). T1 content.
  *(Drops the `{Icp, Pin}` / "serial ≥ 2 inert" cred-SEL scaffolding — there is no cred-SEL to junk.)*
- **Revocation = a `kills[]` declaration + a lookup SEL** — to revoke, the issuer signs a **`Rev`** on its own IEL
  declaring `kills[] = [{ target }]` with `target = hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, alongside
  a sealed `{Icp, Trm}` lookup SEL (built two-pass from `Icp{owner, topic, data=cred.said}`; prefix ≠ target). Revocation is read
  **fail-secure by default** (walk the issuer's fresh IEL, forward-match the `target` in `kills[]`), with a
  content-addressed **fail-open** lookup opt-out (§F) — never a cred-SEL (there is none).

**Shape (the credential SAD; the issuer anchors `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` on its IEL — no cred-SEL):**
```
cred = {
  said,
  issuer,     // issuer IEL prefix          [inv 7: entity = prefix]
  issuee,     // issuee IEL prefix
  claims,     // → a SAD said (nested → partial disclosure); app payload, opaque to the core
  // no `policy` — who-may-present is challenge-the-issuee, not a policy field (2026-07-16); no current-mode policy eval
  // no `pin` — issuer context is fixed by the anchoring position (the issuing IEL Ixn), not a body field (2026-06-26)
  issued,     // timestamp (feature-level — inv 6 allows; advisory)
  expires?,   // optional timestamp (advisory)
  nonce?,     // optional — public vs private issuance (high-entropy → unguessable prefix)
}
```
- **No body `pin` (dropped 2026-06-26).** The cred body carries **no** `pin`; its issuer context is fixed by the
  **anchoring position** — the issuer IEL `Ixn` that commits the **issuance commitment
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** via `manifest.anchors` (the cred is anchored **directly**, no
  cred-SEL — 2026-07-09) (append-only). The as-of authority is the anchoring position,
  never a self-asserted value, so nothing can select a permissive past while the issuance anchors in the restrictive
  present (closes F1). The anchoring `Ixn` **transitively commits** the issuer IEL (roster/threshold) + the whole
  delegation chain via committed `delegating` links [inv 4]. Non-circular: the cred SAID is fixed from its content,
  *then* the issuer authors the anchoring `Ixn` naming it. [inv 5] *(A `public` cred's `cred.said` is public →
  public revocation status via `hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, safe by **owner-rooting**
  [F-J]. A `private` cred stays private because **`cred.said` appears nowhere raw** on the public IEL — issuance
  commitment, kill target, and the lookup SEL's prefix/said are all hashes of it, and the `nonce`-in-body keeps
  `cred.said` unguessable (fully closed — F2, inv 16).)*
- **Multi-identity authorization — `issuers[]` SAD + independent attestations (Jason 2026-06-26).** A document whose
  *authorizing* policy spans **separate identities** (e.g. `thr(2,[id(A),id(B),id(C)])`) can't collapse to a joint
  IEL (a device-threshold ≠ an identity-threshold). It names a custodied **`issuers` SAD** `{ issuers: [prefix, …] }`,
  and **each authorizing identity issues its own attestation independently** — its own SEL over the doc, self-flooring
  via that SEL's serial-1 `Pin` and self-locating via `derive`. The authorizing policy is satisfied by the **positive
  lookup** of each named issuer's attestation [inv 10]; the threshold counts **distinct** attesting prefixes. **No
  per-party pins, no scan, no cross-issuer quiesce** — each issuer anchors on its own chain at its own pace, and the
  verifier reads each one's authorization as-of its own anchoring position. A non-attesting issuer contributes no
  anchored position and is not credited (a co-issuer can't manufacture another's attestation). *(Supersedes the
  per-party-pin / F-D / R5-quiesce model — that machinery is gone with the doc `pin`.)* [inv 5]
- **Recursive** — a document `D` issued under cred `C` is anchored just as `C` is: `D` is committed by its **own**
  anchoring `Ixn` on its issuer's IEL, and authority-affecting as-of resolution is judged by that **anchoring
  position** (append-only: `D` ← its SEL ← IEL `Ixn` ← KEL `Ixn`, each `previous`-linked) — no body pin at any level.
  No separate machinery to establish time — **the append-only chain *is* the clock.** [inv 5, F1]
- **Who-may-present is NOT a policy (2026-07-16 — live-policy removal).** A cred carries **no `policy` field**.
  Ownership / who-may-present is the uniform **challenge-the-issuee** step — the issuee satisfies its own IEL
  `use` quorum live (single-identity auth); a bearer cred skips it. This is authentication, not policy
  composition, so it lives in the presentation exchange (IPEX), not the policy layer. The **only** surviving
  document-layer policy is a document's *authorizing* condition (who could issue it), when multi-identity →
  evaluated **as-issued** via the independent attestations (the `issuers[]` SAD); single-issuer authorization is
  **structural** (the owner IEL threshold), not a DSL eval (R1). Policies are **as-issued only** — live checks
  don't compose for a passive verifier, so there is no current-mode policy evaluation.
- **Timestamps are advisory** [inv 6]: `issued`/`expires` never fail crypto/structural checks; an expired cred
  is *expired*, inspected by the caller via an **`is_expired()` helper** + surfaced in the **verification
  token**. All ordering/grandfather uses the **anchoring position** (append-only ancestry) — with the `pin` verified `==
  anchor.previous` so it can't backdate — never the clock [inv 5, F1].
- **`nonce` = public vs private issuance:** omit → SAID derivable (observers can tell you issued it from your
  logs); add an unguessable `nonce` → SAID not reconstructable → private issuance.

### F. Revocation — a `kills[]` declaration on the issuer's witnessed IEL + a lookup SEL (2026-06-20; B1 fail-secure rework 2026-07-09)

**A cred is an anchored SAD; revocation is a `kills[]` declaration on the issuer's witnessed IEL + a
content-addressed lookup SEL** (not content on a shared registry, not a cred-SEL):
- **Issuance** = **the issuer anchors the issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`
  directly** on its own IEL via one `Ixn` (`manifest.anchors` names it; the anchor **is** the validity proof). **No
  cred-SEL** (dropped 2026-07-09 — the cred is immutable + presented, so it needs no lookup object; **custody rule:**
  direct-anchor an immutable presented SAD, SEL-wrap anything mutable / looked-up); no `{Icp, Pin}` scaffolding, no
  "serial ≥ 2 inert" machinery.
- **Revocation = a `kills[]` declaration + a lookup SEL.** To revoke, the issuer signs a **`Rev`** on its own IEL
  declaring **`kills[] = [{ target }]`** with **`target = hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`** (a
  flat, `:`-delimited, domain-qualified hash), alongside the unchanged `anchors[] = [said(Trm)]` and a sealed
  `{Icp, Trm}` lookup SEL (built from `Icp{owner, topic, data=cred.said}`, usual two-pass — its **prefix ≠ the flat
  `target`**, so `kills[]` doesn't leak the object's address; the `Trm` v1 carries only its pin, `Rev`-anchored,
  `t_govern`/T2). A non-issuer can't declare it (**no forged revocation**); a witnessed `Rev` + a sealed monotone
  `Trm` can't be rolled back (**no silent un-revocation**). A `Trm` whose target is in **no** `kills[]` is a
  terminated SEL that isn't a revocation → reads not-revoked (no coverage hole).
- **Status = two reads; fail-secure is the DEFAULT.**
  - **Fail-secure walk (default):** compute `target = hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')` and walk the issuer's
    **fresh** IEL over `[issuance-position .. tip]`, forward-matching `target` against each `Rev`/`Dth`'s `kills[]`.
    **In some `kills[]` → revoked; in none on the fully-walked fresh chain → not-revoked** (being in a `kills[]` **is**
    the definition of revoked — nothing to miss). This **rides inv 8's freshness gate**: hiding a revocation needs a
    **stale** IEL, which the verifier already refuses when trusting the issuer at all — so revocation is fail-secure,
    not best-effort. Bounded (streams the subject-in-scope, O(range) time, no lossy cap); self-contained (a cred has
    **no bound** to fetch — a doc-member rescission's gated bound is fetched instead, R3 / shared-documents §1).
  - **Fail-open lookup (opt-out):** recompute the `target`, fetch its `{Icp, Trm}` lookup SEL (content-addressed,
    O(1)) — **found → revoked; not-found → best-effort not-revoked** (a withheld object reads not-found;
    `Trm`-existence is a conservative proxy for the authoritative `kills[]`-membership — equal only for a canonical
    revocation, over-refuse fail-safe — area-sel §1). A verifier opts **down** to fail-open, never up.
- **Who does which — the revocation check is the consumer's, not `vdtid`'s (R6).** **`vdtid` is a structural store,
  not a revocation authority** — it validates / serves / merges chains + SADs; a revoked subject is **still
  structurally-valid data**, so there is **no revocation walk at `vdtid`** (nothing to brick there). The revocation
  check lives in the **verifier** (`lib/vdti`) and is run by a **consumer** (client / app server) making a trust
  decision; the fail-secure / fail-open / timeout posture (and any bricking) is the **consumer's**, at the
  application layer. A consumer under a latency budget may opt down to the O(1) fail-open lookup or run the walk with
  a **timeout, fail-secure on timeout where it matters** — its own read strategy over data `vdtid` serves by address.
- **inv 8 — revocation IS an inv-8 dependency (no carve-out).** inv 8's fail-secure freshness gate governs the
  **whole** loss-of-trust read: validly-issued **and** not-revoked/not-rescinded, both confirmed on the multi-source
  fresh walk (revocation is a `kills[]` declaration on the same witnessed IEL). Trust = **grant iff (validly-issued)
  AND (not-revoked AND not-rescinded)**, all fail-secure. The earlier best-effort "negative overlay" /
  positive-vs-negative carve-out / `attribute-all` escape hatch is **dropped** (cold/warm re-review-2 F1 broke it);
  the fail-open lookup is a deliberate opt-out (vdtid / walk-timeout), not the default. R4's "loss-of-trust that
  can't confirm → REFUSE" now **stands** for the default walk.
- **Addressing + privacy (F2, inv 16 — CLOSED).** `cred.said` appears **nowhere raw** on the public IEL: issuance
  commitment, kill `target`, and the lookup SEL's prefix/said are all hashes of it; the kill target derives from the
  **preimage** `cred.said`, never from a public hash. A private cred's `cred.said` is high-entropy (`nonce`), so a
  non-holder recovers none of them → **its revocation status stays private**. **Residual:** revocation is
  **grant-instance-gated confirm-a-known-subject** — you can only *confirm* a subject whose cred you hold, never
  invert a `target` or bulk-enumerate (the earlier create-on-revoke "revocation-list enumerable per issuer" is
  superseded — inv 16).
- **The to-tip freshness step is MANDATORY for any trust-granting acceptance (round 4).** An *as-issued*-only resolve
  (was-this-validly-issued, as-of the pin) is **fooled by a forged dormant-chain extension** — the forgery is a
  clean linear extension (no divergence to detect), and the as-issued path doesn't check current-state freshness.
  Only the **to-tip step** (F-E: is the issuer divergent / stale, and is the cred revoked / the grant rescinded — all
  fail-secure on the fresh walk, inv 10 — via the federation-clock **staleness** flag, §1f) catches it. So accepting a cred or honoring a grant
  **must** run the as-issued resolve **and** the to-tip freshness/staleness step; the as-issued resolver alone is
  **insufficient** for binding. **The to-tip step is uniformly fail-secure (B1 fail-secure rework 2026-07-09):** the
  **divergence / staleness** read **and** the **revocation / rescission** checks all confirm on the multi-source
  fresh walk — a no-single-tip or stale chain grounds no new trust (REFUSE), and a revocation/rescission is a
  `kills[]` declaration on that same witnessed IEL, so hiding one needs a stale IEL the bar already refuses (inv 8,
  inv 10). The **fail-open** content-addressed lookup is a deliberate opt-out (vdtid / walk-timeout), not the default.
- **What the to-tip step *returns* on a divergent chain — read the VERDICT; the seal is the boundary (locked
  2026-06-22; verdict-based first-seen 2026-07-08)** [inv 8, 13, 17]. The consumer reads the chain's **effective-SAID
  verdict** (a single confirmed tip → its real SAID; **no** single tip → a type-tagged synthetic recoupled to
  `forked` / `disputed` — `vdti-area-vdtid-services.md` §1e / inv 17), never reconstructing a winner itself. The cut
  is the **seal**, never the divergence point: an anchor **at-or-below `last_seal_advancing_event`** is **final** and
  honored regardless of any later divergence; an anchor **above the seal** is durable only once a later
  seal-advancing event lands cleanly past it. So **as-issued** over a sealed anchor stays answerable even on a forked
  chain (the verifier surfaces the below-seal portion). **B1 — any non-single-tip chain grounds no *new* trust
  (fail-secure refuse):** a loss-of-trust / current-state read requires a **single confirmed tip**, so **both**
  verdicts short of that refuse — a **`forked`** chain (M ≤ 1 sealed, operationally recoverable) as well as a
  **`disputed`** one (M ≥ 2 sealed, terminal → reincept). A forked chain grounds no new trust until its **burying
  seal-advancer** (a recovery `Rot` / a sealing-event burial — inv 13; **not** a repair event) resolves it back to
  a single tip and re-establishes a clean seal past the fork; a disputed chain never resolves (its post-seal window
  is whole-*above-seal*-suspect — below-seal still final). A dependent surviving an issuer's *member*-KEL terminal is
  a **composition-redundancy** outcome (`M > N` anchors clear the threshold without the suspect member — inv 12), not
  prefix-salvage.
- **Cost allocation:** cheap T1 issuance (the frequent op), governance-gated T2 revocation (rarer, deliberate).
- See **[inv 15]** (inception tier + SEL `Trm`).

**★ Ripples (confirmed 2026-06-20):**
- **A reworked ✓** — cred = an **anchored SAD** (no cred-SEL); revocation = a **`kills[]` declaration** on the
  issuer's witnessed IEL `Rev` + a **`{Icp, Trm}` lookup SEL** (above); **no registry object / no registry
  identifier** (the topic + derivation replaces KERI's registry identifier).
- **F8 closure → `Trm` ✓** — closing any SEL = terminate it (T2); the F8 derived-lookup-SEL-for-closure is
  **superseded by SEL `Trm`**. (Rescission *stays* a lookup-SEL — it cuts off a *foreign* delegate's chain,
  which the delegator can't `Trm` — and, like cred revocation, it is **fail-secure by default** (the `Dth`'s
  `kills[]` on the delegator's witnessed IEL — inv 10; area-delegation §1), with a fail-open lookup opt-out.) Fold into §H.
- **Primitive drift (owed):** design-pass §2.1/§3 ("every SEL is `Icp`+`Evl`", "no SEL `Trm`") superseded by
  inv 15 — SEL taxonomy regains `Trm`; SEL `Icp` is T1 (a credential is **not** a SEL — an anchored SAD; a serial-1 **`Pin`**
  floors a content SEL; the revocation/rescission lookup-SEL is `Icp` + `Trm`). Owed: a SEL
  area note + design-pass reconciliation. *(The delegation note's "registry-SEL" wording is already fixed — LF8c
  2026-06-21.)*
