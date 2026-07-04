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
- **A. What a document / cred IS** — `{said, issuer, issuee, claims, policy, issued, expires?, nonce?}`. **[DONE — §A]**
- **B. The policy DSL** — leaves `id`/`del`/`pol` + composers `thr`/`wgt`/`and`; `dev` and `grp` dropped. **[DONE — §B]**
- **C. The two evaluation functions** — one shared composer + two leaf resolvers (as-issued: anchoring position / as-of /
  on-chain proof; current: tip / attestations / challenge). **[DONE — §C]**
- **D. Document context** — fixed by the **anchoring position** (no body `pin`, dropped 2026-06-26); multi-identity
  uses an `issuers[]` SAD + independent attestations. **[RESOLVED — §A]**
- **E. Policy-satisfaction matching** — how a server/verifier decides "satisfied." [fresh]
- **F. Revocation** — a cred is its **own SEL**; revocation = the cred-SEL's **`Trm`** (T2 governance, anchored
  in an IEL `Rev` via manifest). Status = walk the cred-SEL, `Trm` present → revoked. **[RESOLVED — §F]**
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
  already lets an identity relate to several federations; no orchestration is added. **Direct mode is a reachable mode**
  (cold-5 C1a — the KERI analogy): a user `Icp` **may omit** its federation binding (*absent ⇒ direct-mode*); its first
  `Wit` binds forward (witnessing starts from that event, early range unwitnessed). A direct-mode chain is fully
  **end-verifiable** (SAID + sig + chain linkage need no federation) but earns **no witness receipts**, keeping only
  **local** divergence detection (a held fork freezes the chain, inv 13) — it lacks beacon **propagation** +
  multi-source. **A loss-of-trust decision it can't multi-source-confirm fails-secure: REFUSE** (cold-5 C2), never
  proceed-with-a-flag. Witnessing is **range-based**, reported by the token **per range** (federation-witnessing §1d).

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

### C. Evaluation model — the canon has THREE functions; the reshape keeps TWO
The landed canon (`evaluation.md`):
1. **`evaluate_gate_policy`** — anchored single-policy GATE for *chain governance events* (IEL `Evl`/`Trm`, SEL
   `Evl`/`Rpr`/`Trm`), driven by the chain's floored `policyPin`.
2. **`evaluate_anchored_policy`** — multi-party anchored validity (cred *issuance*; parties present pinnings;
   resolves as-of).
3. **`evaluate_current_policy`** — challenge-response *current* control (attestations at chain tip).

**Reshape reconciliation:**
- **★ Function (1), the gate, DISSOLVES.** Primitives carry no policy [inv 1] → there is no chain-governance
  policy to evaluate. Chain-event authorization becomes **structural** (IEL threshold vector + tier, §12; SEL
  single-owner via manifest+pin). `policyPin` + the governance/operation/authentication/delegation policy-kinds
  go with it. → **R1.**
- **Functions (2) + (3) ARE the document layer's "two-function model"** Jason flagged. `evaluate_as_issued`
  (was-it-validly-issued — pins, as-of) + `evaluate_current` (current control — attestations, tip). The "minor
  reconciliation" = drop the gate, strip `policyPin`, reconcile the leaves (B).
- **Rescission:** the canon's `del` self-traversal walks to *tip* for an `Rsc`; the reshape replaces that with
  the positive **lookup-SEL** check [inv 10] — no to-tip rescission scan.

**The function structure — one composer, two resolvers (confirmed 2026-06-20).** The two surviving functions
share their core:
- **Shared composer** — the `thr`/`wgt`/`and`/`pol` logic (credited-set union, distinct-by-prefix counting,
  per-prefix-max weight, `and`-over-disjoint-pools, threshold check). **Identical** in both modes.
- **Mode-specific leaf resolver** — each leaf needs **state** (the chain's roster/keys, from a verification
  *token*) and **proof** (that the named party acted). Both differ by mode:

  | | State (token) | Proof |
  |---|---|---|
  | **as-issued** | as-of the **anchoring position** | the **committed on-chain anchors** (reached via that position) — proof is already in the chain |
  | **current** | at **tip** | **live attestations** over a fresh **challenge** |

  `del` differs the same way (as-issued: self-traverse + ancestry-to-cutoff, as-of; current: live control +
  self-traverse + rescission-not-present, at tip).
- **Shape:** `evaluate(policy, resolver)` is the shared composer; `evaluate_as_issued` / `evaluate_current` are
  thin wrappers that pick the resolver and assemble its inputs. **The composer never knows the mode.**
- **Anchoring positions feed the as-issued resolver** (state token at a position + the committed-anchor proofs); **attestations
  are the current resolver's analog.** Same evaluator, two ways of feeding it.

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

### A. What a document / cred IS — 2026-06-20 (cred = a per-cred SEL; refined 2026-06-21)

**A cred IS its own per-cred SEL** — prefix `derive(issuer, CRED_TOPIC, data)` where **`data` = the credential's
SAID**; **no registry object, no registry identifier** (KERI needs one because creds live *in* a registry; vdti's
SEL **topic + derivation** already give the grouping/addressing a registry identifier provided). Lifecycle:
`Icp` (issued, T1) → optional content `Ixn`s → optional `Trm` (revoked, T2, §F). The **credential is a SAD**; the
cred-SEL `Icp` carries **no manifest** — its `data` IS that SAD's `said`, the whole reference.

**Shape (the credential SAD; the cred-SEL `Icp`'s `data` = its `said`):**
```
cred = {
  said,
  issuer,     // issuer IEL prefix          [inv 7: entity = prefix]
  issuee,     // issuee IEL prefix
  claims,     // → a SAD said (nested → partial disclosure); app payload, opaque to the core
  policy,     // → a SAD said; acceptance condition (DSL: id/del/pol + thr/wgt/and) — evaluated CURRENT
  // no `pin` — issuer context is fixed by the anchoring position (the issuing IEL Ixn), not a body field (2026-06-26)
  issued,     // timestamp (feature-level — inv 6 allows; advisory)
  expires?,   // optional timestamp (advisory)
  nonce?,     // optional — public vs private issuance (high-entropy → unguessable prefix)
}
```
- **No body `pin` (dropped 2026-06-26).** The cred body carries **no** `pin`; its issuer context is fixed by the
  **anchoring position** — the issuer IEL `Ixn` that commits the cred-SEL via `manifest.anchors` (anchoring its serial-1 v1; the `Icp` rides `v1.previous`, never itself anchored) (append-only).
  The cred-SEL floors to the issuer IEL **structurally**, via its **serial-1 `Pin`** (a chain field, not a doc
  field); the as-of authority is the anchoring position, never a self-asserted value, so nothing can select a
  permissive past while the issuance anchors in the restrictive present (closes F1). The anchoring `Ixn`
  **transitively commits** the issuer IEL (roster/threshold) + the whole delegation chain via committed `delegating`
  links [inv 4]. Non-circular: the cred SAID is fixed from its content, *then* the issuer authors the anchoring
  `Ixn` naming it. [inv 5] *(A `public` cred's prefix is
  recomputable from the cred itself — **self-locating** revocation, area-sel §1 — yet still safe by **owner-rooting**
  [F-J]. A `private` cred's privacy rests on three things together (F2, inv 16): the `nonce` keeps the prefix
  unguessable, logs are **referenced by prefix only** (the `said(v1)` in the public `anchors[]` is an opaque
  commitment that doesn't invert to the prefix (`said(Icp) == v1.previous`, one hop back) — no by-SAID lookup), and the **private cred body is not published**
  to the shared store.)*
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
- **Two policies, two modes:** the cred's **`policy`** is the *acceptance* condition (who can present) →
  evaluated **current**. A document's *authorizing* policy (who could issue it), when multi-identity → evaluated
  **as-issued** via the independent attestations (the `issuers[]` SAD). Single-issuer authorization is **structural** (the owner IEL threshold),
  not a DSL eval (R1).
- **Timestamps are advisory** [inv 6]: `issued`/`expires` never fail crypto/structural checks; an expired cred
  is *expired*, inspected by the caller via an **`is_expired()` helper** + surfaced in the **verification
  token**. All ordering/grandfather uses the **anchoring position** (append-only ancestry) — with the `pin` verified `==
  anchor.previous` so it can't backdate — never the clock [inv 5, F1].
- **`nonce` = public vs private issuance:** omit → SAID derivable (observers can tell you issued it from your
  logs); add an unguessable `nonce` → SAID not reconstructable → private issuance.

### F. Revocation — a cred IS a SEL (2026-06-20)

**A cred is its own per-cred SEL** (not content on a shared registry):
- **Issuance** = the cred-SEL's **`Icp`** — T1, **`data` = the credential's SAID** (no body `pin`; floored by its serial-1 `Pin`/v1);
  the IEL `Ixn` anchors the **v1** (the `Pin`) via `manifest.anchors[]` (cheap, frequent, batched) and the `Icp` rides `v1.previous` — never itself anchored
  (inv 4). Plus content `Ixn`s if needed.
- **Revocation** = the cred-SEL's **`Trm`** — T2 governance, anchored in an IEL `Rev` via
  `manifest.anchors`; sealed-on-arrival (can't be un-revoked by repair). Batchable (one IEL `Rev` revokes many
  cred-SELs). The killed cred is identified by *which SEL its `Trm` extends* — no prefix in the `Rev`.
- **Status** = **self-locating** — from the cred you hold, compute `said(cred)` → `derive(issuer, CRED_TOPIC, that)`
  → the cred-SEL prefix → walk it; `Trm` present → revoked. Positive check, no separate registry pointer. [inv 10
  in spirit — positive, not a scan]
  **Freshness (F8 / F3):** revocation is a to-tip loss-of-trust check, so the status must be read against a
  **witnessed / multi-source** effective-SAID (provenance surfaced on the token, `vdti-area-vdtid-services.md` §1d)
  — never a single server's possibly-stale claim, which could hide the `Trm`. **So cred-SELs ARE witnessed** (their
  effective-SAID is multi-source → hiding a `Trm` is *detected*, not merely flagged). **Addressing (F2, inv 16):**
  the cred-SEL is reached **by prefix only** (logs are never looked up by SAID; the `said(v1)` in `anchors[]` is an
  opaque commitment; `said(Icp) == v1.previous`), so only a holder (who derives the prefix from the cred) or a party it's disclosed to can
  locate it; a non-holder can't — which is the private-cred boundary, and why a *private* cred's revocation is
  third-party-checkable only at disclosure.
- **The to-tip freshness step is MANDATORY for any trust-granting acceptance (round 4).** An *as-issued*-only resolve
  (was-this-validly-issued, as-of the pin) is **fooled by a forged dormant-chain extension** — the forgery is a
  clean linear extension (no divergence to detect), and the as-issued path doesn't check current-state freshness.
  Only the **to-tip step** (F-E: is the issuer revoked / rescinded / divergent? + the federation-clock **staleness**
  flag — §1f) catches it. So accepting a cred or honoring a grant **must** run the as-issued resolve **and** the
  to-tip freshness/staleness step; the as-issued resolver alone is **insufficient** for binding.
- **What the to-tip step *returns* on a divergent / terminal chain — the seal is the boundary (locked 2026-06-22)**
  [inv 8, 13]. The honor decision splits on *recoverable vs terminal*, but the cut is the **seal**, never the
  divergence point: an anchor **at-or-below `last_seal_advancing_event`** is **final** and honored regardless of any
  later divergence; an anchor **above the seal** is durable only once a later seal-advancing event lands cleanly
  past it. So **as-issued** over a sealed anchor stays answerable even on a forked chain (the verifier surfaces the
  below-seal portion); **current** over a *frozen-divergent* chain is suspect (no clean tip). A **recoverable**
  divergence's repair seals the surviving branch → its above-seal anchors become durable; a **terminal** (≥ 2
  privileged / disputed) chain never seals → its post-seal window grounds **no new trust** (whole-*above-seal*-
  suspect — below-seal still final). A dependent surviving an issuer's *member*-KEL terminal is a **composition-
  redundancy** outcome (`M > N` anchors clear the threshold without the suspect member — inv 12), not prefix-salvage.
- **Cost allocation:** cheap T1 issuance (the frequent op), governance-gated T2 revocation (rarer, deliberate).
- See **[inv 15]** (inception tier + SEL `Trm`).

**★ Ripples (confirmed 2026-06-20):**
- **A reworked ✓** — cred = a per-cred SEL (above); **no registry object / no registry identifier** (the SEL
  topic + derivation replaces KERI's registry identifier).
- **F8 closure → `Trm` ✓** — closing any SEL = terminate it (T2); the F8 derived-lookup-SEL-for-closure is
  **superseded by SEL `Trm`**. (Rescission *stays* a lookup-SEL — it cuts off a *foreign* delegate's chain,
  which the delegator can't `Trm`.) Fold into §H.
- **Primitive drift (owed):** design-pass §2.1/§3 ("every SEL is `Icp`+`Evl`", "no SEL `Trm`") superseded by
  inv 15 — SEL taxonomy regains `Trm`; SEL `Icp` is T1 (cred-SEL: `data` = cred SAID, no body pin; a serial-1 **`Pin`**
  floors every SEL; the rescission lookup-SEL is `Icp` + `Trm`). Owed: a SEL
  area note + design-pass reconciliation. *(The delegation note's "registry-SEL" wording is already fixed — LF8c
  2026-06-21.)*
