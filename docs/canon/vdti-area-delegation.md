# vdti — area note: Delegation & rescission

**Status: FIRST CUT (2026-06-20).** Audited against design-pass §5 + the pre-reshape creds/rescission arc.
**Invariants referenced:** [inv 5] pin-floored, [inv 8] walk-semantics (loss-of-trust walks fully), [inv 10]
negative-checks-are-lookup-SELs, [inv 12] thresholds (`t_authorize`).

## Sources audited (disposition)
- `vdti-log-primitive-reshape-design-pass.md` §5 — **authoritative / current.**
- `archived/vdti-creds-revocation-perdelegator-validation.md` (2026-06-16) — pre-reshape; **mechanism superseded,
  but holds buried-still-valid security *requirements*** (→ §2). Deep-read.
- `archived/vdti-creds-issuance-31-realization.md` (T_rev), `…-revocation-model.md`, `…-correction/refine.md` —
  the `T_rev` arc; **superseded** (T_rev dissolved); skim-confirmed, not re-mined (their structural insights are
  captured in the perdelegator doc).
- `vdti-iel-primitive-stub.md` §Rsc / §Delegate(X) — pre-reshape (`Rsc`-as-IEL-event, retroactive semantics);
  **superseded** (already mined in the IEL area note).
- Canonical: a `delegation.md` is referenced by the archived docs — **confirm whether it exists / its state**
  (land backlog §6).

## 1. Locked-candidate — current model
- **`Ath` (positive — "is P delegated?")** — an IEL `Ath` whose `manifest.delegates` lists delegate prefixes
  (inv 4); an inclusion proof. Cheap batch authoring. `t_authorize`-gated (T2). [inv 12]
- **Multi-hop `del(X, N)`** = the single-hop primitive per hop; each hop = a self-recorded `delegating` link +
  that delegator's rescission lookup-SEL + ancestry check. Cost O(N) O(1)-reads; depth cap = hop count.
- **Rescission (negative — "is P *not* rescinded?")** = a **derived lookup SEL**, NOT an IEL event, NOT a list.
  [inv 10]
  - prefix = `derive(owner = X, RSC_TOPIC, data = P)` — recomputable by any verifier from `(X, P)`; `data = P`
    makes it discoverable; no decoy substitution.
  - `Icp` + a **`Trm`** (the terminal kill — anchored via X's IEL `Dth`, whose **`anchors`** names
    the lookup-SEL's `Trm`). The `Trm` carries `pin` → X's tip (uniform — every event pins) and **`manifest.bound`** →
    SAID of the last valid event on P's delegated chain. *(Split: the `pin` is the event's own structural link →
    **top-level**; the `bound` commits a position on **P's** chain → a **manifest** role, inv 4. The `bound` is the
    surviving rescission boundary — the federation roster cut dropped its copy, inv 14. Renamed from
    "cut-off"/"terminator" 2026-06-26; the second event is a `Trm` not a `Pin`, 2026-06-26.)*
  - Check = recompute the prefix, read that one locus → present → rescinded (with the bound), absent → not. A
    **positive O(1) read** — the verifier *derives* the locus; the presenter furnishes nothing.
  - **Grandfather = ancestry:** a cred from P stays valid iff its **anchoring position** (the IEL `Ixn` that
    committed it — append-only-fixed, *not* the cred's self-asserted `pin`, which the verifier checks `==
    anchor.previous`) is an **ancestor of** the bound SAID. A rescinded-but-live P can author a fresh cred only
    at its current tip (post-cutoff) → not grandfathered. [inv 5, F1]
  - **Multi-hop is judged per-hop by the committed grant position (LF4, 2026-06-21).** With a chain `X → D1 → D2`,
    there is **no cross-chain clock** [inv 6], so each hop's grandfather is judged by the **committed grant
    position** (`D1`'s `Ath`-of-`D2`), not the downstream cred's issuance time. So **rescinding `D1` does NOT
    automatically stop `D2`**: a sub-delegate `D1` granted *before* `X`'s bound keeps minting grandfathered creds.
    To stop such a sub-delegate, `X` must move the bound **before that grant**. **The bound field is
    always present; its range is tip → inception (2026-06-21):** pin it at the current tip → grandfather
    everything; pin it lower → grandfather ≤ it; pin it at the **inception** → keep only the inception (no cred
    grandfathers — the only ancestor of the inception is itself). **No "omit / absent" case** — the inception is
    **inert** (anchors nothing, grants nothing), so keeping it is practically identical to a total nuke, and it
    **honors the immutable fact that the add happened** (don't assert a real on-chain event invalid; the add
    itself lives on the grantor's append-only chain regardless). State as usage doctrine — don't let "rescind `D1`
    ⇒ everything under `D1` dies" be assumed.

## 2. Mined from archived — buried-still-valid SECURITY REQUIREMENTS (carry into the document layer)
The per-delegator doc's *mechanism* is superseded, but it proved requirements the reshape must still meet:
- **Hidden-revocation / check-set forgery — CLOSED by transitive pins (corrected 2026-06-20).** Concern (from
  the per-delegator doc's "Attack 1"): a presenter routes around a rescinder via a pruned/alternate authorizing
  chain. **Structurally closed in the reshape:** a cred pins the issuer-IEL prior event directly ([inv 15]) → that IEL
  state commits its roster + the committed `delegating` links pin up the delegation chain to `X`. The
  **verifier derives** the authorizing chain from committed data and traverses it fully ([inv 8], loss-of-trust
  walks the whole chain); the presenter furnishes nothing to prune. The Attack-1 model (presenter *assembles*
  the chain via non-membership proofs) doesn't exist here. **No leaf-only hole.** Residual is the scope detail in
  §5, not a forgery requirement.
- **Root `X` is the guaranteed rescinder; intermediates are routable-around.** `X` terminates every
  authorizing chain, so `X` can always rescind; an intermediate only cuts creds whose committed path includes
  it. **Bulk-kill backstop** = `X` rescinds with bound at genesis (= nuke all of the delegate's work).
- **Multi-path:** a cred commits the *one* path it was issued under; to give several delegators kill-authority,
  issue under a **threshold** spanning their legs (all legs land in the committed chain).
- **Temporal split — "frozen-which, current-whether."** The check-*set* is frozen (the cred's committed chain at
  issuance); the *whether-rescinded* query is current (fresh effective-SAID per hop). No collision.
- **Cost: O(N = depth), parallelizable, no rollup** (a rollup reintroduces the cross-chain coupling the
  per-locus model exists to avoid). N is small (hop-cap).

## 3. Superseded — do NOT carry forward
- **Per-delegator revocation registries** `R_{D_i}` with `gov = op = id(D_i)` → reshape: single-owner lookup
  SEL `derive(X, RSC_TOPIC, P)`, no policy (policy moved up). [inv 1]
- **Non-membership proofs / status-accumulator / compact-witness** → reshape: **positive O(1) read**
  (present → rescinded). The whole non-membership-witness machinery is gone. [inv 10]
- **`T_rev` / positioned-issuance (§3.1)** → dissolved; pin-everything-floored closes backdate by construction.
  [inv 5]
- **`Rsc` as an IEL event** carrying `delegated` removals → gone; rescission is the lookup SEL.

## 4. Reconciliation — "retroactive vs grandfather" (corrects my earlier framing)
In the IEL note I flagged "old = retroactive-invalidate-all → reshape = grandfather-to-cutoff" as a reshape
semantic change. **The audit corrects this:** retroactive-invalidate-all was the *oldest* conception (the
`iel-primitive-stub` §Rsc); it was already superseded **before the reshape** by the positioned-cutoff /
grandfather model in the `T_rev` generation (the per-delegator doc's "pre-seal grandfather, post-seal void").
**The reshape changed the *mechanism* (T_rev → lookup-SEL), not the semantics** — grandfather-to-cutoff is stable
since the T_rev generation. Retroactive-all is recoverable as the special case **bound = genesis**. So this is
a reconciliation, not an open decision. (My earlier "load-bearing semantic shift" overstated it — it came from
reading the oldest doc.)

## 5. Open / route to the adversarial pass
- **Multi-delegator scope — RESOLVED (G5, 2026-06-21).** A rescission of the `X → P` delegation reaches **only
  creds whose committed authorizing path runs through that delegation** — *not* `P`'s independent-identity acts
  (`P`'s own self-rooted creds, `P`'s own delegations). `X`'s authority is bounded to what `X` delegated, so `X`
  cannot void `P`'s independent chain. A cred commits the *specific* path it was issued under (the `delegating`
  links pin up to `X`), so the check-set is well-defined; an intermediate has kill-authority only over creds it
  actually authorized, and `X` is always on the chain. **Restate F-H accordingly:** "de-grandfather the delegated
  creds whose committed path runs through this delegation, anchored past the bound" — **not** "void `P`'s whole
  chain suffix." The contiguity argument lives at the level of *delegated-cred anchoring positions within the
  delegated context*, not all of `P`'s IEL.
- **The bound is a hard *contiguous* boundary — RESOLVED (F-H, locked 2026-06-21).** A rescission pins the last
  valid event on P's chain (the bound = its SAID). **Nothing past the bound is honored — grants *and* kills
  alike.** There is **no per-kind exception across a validity bound** (honoring an event past the bound would be
  trusting an un-anchored, invalidated event — see [inv 13]). Why it's clean: chain **linearity** — every event
  builds on the prior, so a bound removes a **contiguous suffix**; you can never retain a non-contiguous subset.
  In a compromise the invalidated suffix is exactly the attacker's contiguous tail from the divergence point
  (legit and attacker events never interleave into a keep-some subset; even a multi-member IEL where a compromised
  member's event is silently extended yields one contiguous suspect tail). **Bound granularity is the dial:**
  pin it at the last valid event (default), earlier, or at the **inception** (≈ total nuke — the inception is
  inert; **no "omit/absent" case**, per [inv 13] / §1). **F-H consequence:** individually revoking a grandfathered
  cred of an *already-rescinded* issuer is **not a structural operation** — the revocation would need a valid anchor
  past the bound (none exists), and there is no way to invalidate just that cred without taking the whole
  contiguous suffix. Recovery is **reincept the delegate** (a new prefix — the rescinded prefix stays permanently
  capped, so a re-grant of the *same* prefix doesn't restore it) + re-grant, or reissue. *(No "rewind the bound"
  — a sealed kill is never retracted; the bound is **set once** at the rescission `Trm` (no move later to un-kill, no tighten earlier; a mis-set bound is recovered operationally). **I1:** a
  bound un-honoring a kill the rescinded party placed past it isn't un-doing a kill — it withdraws that party's
  authority wholesale; with the not-interleaved guarantee, a correctly-set bound catches only the distrusted
  tail.)*
- **Loss-of-trust vs clean-lifecycle** distinction survives: rescission (X cuts off P, with a chosen bound =
  trust-boundary judgment) vs clean lifecycle (P's own `Trm`, no rescission, past stays valid). The bound
  choice is security-critical — when X doesn't know when trust was lost, cut at genesis. Capture as usage doctrine.

## 6. Drift → land backlog (canonical docs)
- **Confirm/locate `delegation.md`** (referenced by archived docs) — likely needs a greenfield rewrite to the
  lookup-SEL model (it predates the reshape). The `del(X)` policy leaf lands in the policy/document layer.
- IEL `Ath` kind → the `iel/events` doc (IEL area).

## 7. Confidence / owed
- §1 — high (direct from design-pass §5).
- §2 — high; the hidden-revocation forgery vector is **closed by transitive pins** (corrected). The remaining
  mined items (root-`X` guaranteed rescinder, multi-path = commit one path, frozen-which/current-whether, O(N)
  parallel) are valid and carry forward.
- §4 — high; the audit resolved it (mechanism change, not semantic).
- §5 — the multi-delegator *scope* detail is a document-layer well-definedness item (not security); the bound-
  covers-revocation-too confirm is owed.
- Owed: confirm `delegation.md` state; the §5 confirms.
