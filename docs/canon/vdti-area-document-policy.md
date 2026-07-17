# vdti — area note: Document / policy layer

**Status: IN-PROGRESS DESIGN PASS (2026-06-20).** The **foundational feature layer** — specced *first* (Jason's
call) because its requirements flow **down** to the primitives. This is a genuine design pass (not a reconcile),
but grounded in the archived policy-DSL canon + this session's cred work. **Invariants referenced:** [inv 1]
policy-on-documents, [inv 8] walk-semantics, [inv 10] negative-checks-are-lookup-SELs, + the two-function model
(`[needs-reconciliation]`).

**★ CREDENTIALS MOVED (2026-07-17) → [`vdti-area-credentials.md`](vdti-area-credentials.md).** Credentials now
has its own area note (per "every component gets a canon area"), which is **authoritative** for the credential
shape, issuance (anchor) + compaction, the two questions, accepting a presented credential, IPEX presentation,
targeted-vs-bearer, claim-gating, revocation, and the registrar. The credential shape, issuance, revocation, presentation,
claim-gating, and registrar all live there. **§A is now trimmed to the document-layer context** (the anchoring
position + the multi-identity `issuers[]` issuance model); **§F is a pointer** to the credentials note. This
note keeps the **policy DSL** (§B) and the **evaluation model** (§C) — the generic authorization engine that
credentials is one caller of.

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

### A. Document authorization context — the anchoring position + multi-identity issuance

**The credential shape, issuance (anchor + compaction), revocation, presentation, who-may-present, and
claim-gating now live in [`vdti-area-credentials.md`](vdti-area-credentials.md)** (the credentials feature
note). What remains here is the **document-layer** concern the policy engine owns: how any policy-bearing
document fixes its issuer context, and how a **multi-identity** authorizing policy is satisfied.

- **Issuer context = the anchoring position** (no body `pin`, dropped 2026-06-26). A document — a credential,
  or any policy-bearing SAD — fixes its issuer context by the **anchoring position**: the issuer IEL `Ixn` that
  commits it via `manifest.anchors` (append-only). The as-of authority is that position, never a self-asserted
  body value, so nothing can select a permissive past while the issuance anchors in the restrictive present
  (closes F1). The anchoring `Ixn` **transitively commits** the issuer IEL (roster / threshold) + the whole
  delegation chain via committed `delegating` links [inv 4]. [inv 5]
- **Who-may-present is NOT a policy; the only document-layer policy is the authorizing condition.** A credential
  carries **no `policy` field** — ownership is the uniform challenge-the-issuee step (IPEX), not the policy layer
  (details in `vdti-area-credentials.md`). The **only** surviving document-layer policy is a document's
  *authorizing* condition (who could issue it): single-issuer is **structural** (the owner IEL threshold, R1);
  multi-identity is evaluated **as-issued** via independent attestations (below). Policies are **as-issued only**
  — live checks don't compose for a passive verifier (§C).
- **Multi-identity authorization — an `issuers[]` SAD + independent attestations (Jason 2026-06-26).** A document
  whose *authorizing* policy spans **separate identities** (e.g. `thr(2, [id(A), id(B), id(C)])`) can't collapse
  to a joint IEL (a device-threshold ≠ an identity-threshold). It names a custodied **`issuers` SAD**
  `{ issuers: [prefix, …] }`, and **each authorizing identity issues its own attestation independently** — its own
  SEL over the document, self-flooring via that SEL's serial-1 `Pin` and self-locating via `derive`. The
  authorizing policy is satisfied by the **positive lookup** of each named issuer's attestation [inv 10]; the
  threshold counts **distinct** attesting prefixes. **No per-party pins, no scan, no cross-issuer quiesce** — each
  issuer anchors on its own chain at its own pace, and the verifier reads each one's authorization as-of its own
  anchoring position. A non-attesting issuer contributes no anchored position and is not credited (a co-issuer
  can't manufacture another's attestation). [inv 5]
- **Recursive** — a document `D` issued under credential `C` is anchored just as `C` is: `D` is committed by its
  **own** anchoring `Ixn` on its issuer's IEL, and authority-affecting as-of resolution is judged by that
  **anchoring position** (append-only: `D` ← its SEL ← IEL `Ixn` ← KEL `Ixn`, each `previous`-linked) — no body
  pin at any level. **The append-only chain _is_ the clock.** [inv 5, F1]

### F. Revocation → [`vdti-area-credentials.md`](vdti-area-credentials.md)

**Credential revocation now lives in the credentials note** (§Revocation): a `kills[]` declaration on the
issuer's witnessed IEL `Rev` (`target = hash('vdti/sel/v1/actions/revocation:{issuer}:{cred.said}')`) plus a
sealed `{Icp, Trm}` lookup SEL; status read **fail-secure by default** (walk the fresh IEL, forward-match the
target — inv 8 / inv 10) with a content-addressed **fail-open** lookup as the opt-out; the check is the
**consumer's**, not `vdtid`'s; and the privacy closure (`cred.said` appears nowhere raw — inv 16).

**Shared mechanism, other homes:** **delegate rescission** uses the same fail-secure `kills[]` + lookup-SEL
shape on the delegator's witnessed IEL ([`vdti-area-delegation.md`](vdti-area-delegation.md) §1 / inv 10). The
**to-tip freshness** step every trust-granting acceptance must run — and the effective-SAID **verdict** it
reads on a divergent chain (the **seal** is the boundary; a non-single-tip chain grounds no new trust) — is
the cross-cutting acceptance rule in [`vdti-area-vdtid-services.md`](vdti-area-vdtid-services.md) §1e / inv 8,
13, 17, surfaced in the credentials note's accept-case. (Historical F8-closure / primitive-drift breadcrumbs
that lived here are superseded — inv 15; see the git history if needed.)
