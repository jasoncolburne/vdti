# vdti — area note: Federation & Witnessing

**Status: FIRST CUT (2026-06-20).** Federation = an ordinary (restricted) IEL; witnessing = as-of-context
**prevention for witnessed content + detection for everything else** (the majority floor, 2026-07-02 — content forks
are prevented on witnessed chains below fork-cost; privileged races, direct mode, and the byzantine residual are
detected), evolved from kels-216's detection-only model. Grounded in
design-pass §7 + the federation reference doc + `inv 14`, with the witnessing mechanism sourced from kels-216
(Jason confirmed 2026-06-20 it carries as-is, adapting only kind language). Load-bearing claims marked for the
adversarial pass.
**Invariants referenced:** [inv 1] policy-on-documents, [inv 2] single-locus, [inv 3] layers-isolated,
[inv 7] prefix-vs-SAID, [inv 12] threshold-vector, [inv 13] divergence-scoped-to-`Ixn`, [inv 14] federation/witnessing, [inv 15] inception-tier.

## Sources audited (disposition)
- `vdti-log-primitive-reshape-design-pass.md` §7 + §2.2 + §12, `vdti-federation-inception-reference.md`,
  `inv 14`/`12`/`13`/`7` — **authoritative / current** (federation structure, genesis, rebinding).
- `../kels/.working/kels-216-witnessing.md` + `…-witnessing-mechanics.md` — **the witnessing mechanism**;
  carries to vdti (Jason 2026-06-20). Mine: deterministic-by-`(prefix,serial)` selection, `threshold`/`signers`
  semantics, destruction-on-witnessing. *(kels' always-witness + threshold-two-events detection are since
  **superseded** by one-content-sibling-per-serial + the majority floor — §1e/§2, 2026-07-02.)*
- `../kels/.working/kels-214-doctrine-simplification.md` — the *federation-dispute* (no-`Cnt`) framing
  (already reflected; "contested" → "irreconcilable" → "disputed").
- `docs/design/protocol-doctrine.md` §Federation + `event-shape.md` (IEL `Fcp` row, `federationBinding`,
  self-signing carve-out) — **pre-reshape; superseded** (§3). The land targets.
- `vdti-area-kel.md` — the member-KEL witness-config + `Fcp`/`Wit`/federation fields (cross-ref; `Fed` → `Wit`).

## 1. Locked-candidate — the current model

### 1a. Federation = a restricted IEL
- **One IEL** (prefix `F`); **roster = witness KELs directly** (threshold over them); **no policy** [inv 1], no
  per-witness identity wrapper. Witnesses are **devices (KELs)**, HSM-backed, horizontally replicated (one logical
  KEL per witness key). A node is a **device in** the federation identity. A witness KEL is **single-federation**
  (`Fcp`-rooted infrastructure, governed *into* one roster, never self-bound — §1d; to serve another federation,
  spin up a **new KEL** and join it; the old KEL's events stay validly witnessed by the old federation). *(This
  reverses the earlier "a witness serves many federations / blast-radius fan-out": single-federation **contains** a
  witness compromise to one federation. The "why no `Fed`" rationale is now "`Fcp`-rooted infra, governed into the
  roster," not "serves many.")*
- **Restricted kind set: `Fcp` / `Wit` / `Trm` only** (Q1, Jason 2026-06-20; `Fcp` = the federation IEL's **inception
  marker** — a structural disambiguator the verifier dispatches on, §inv 4 / federation-ref §2, **not** a trust
  carve-out; `Wit` = the federation's single governance kind — roster + rotation, T3, replacing `Evl`; 2026-06-28,
  cold-4 B1). A federation authors **no `Ixn`**
  (no content) → it has **no *repairable* divergence → no `Rpr`** [inv 13] (a `{Wit, Wit}` race is terminal → `disputed` → reincept, never repaired); and **no `Ath`** (trust is
  per-federation, non-transitive). Lifecycle: incept (`Fcp`) → all governance (add/remove a witness, rotate) via `Wit` → `Trm`. Its threshold-vector
  is **exactly `{t_govern}`** (+ Rule A for additions): no `Ixn`/`Ath`/`Rpr` ⇒ no `t_use`/`t_authorize`/**`t_recover`** (a threshold is declared iff its consuming kind is in the kind set — inv 12; a federation `Fcp` declaring any of the three is malformed → rejected). **`t_recover` is *not* needed** — the federation never authors an `Rpr` (a `{Wit, Wit}` divergence is terminal → reincept, never repaired), so nothing consumes it. *(Corrects the earlier E4 "`t_recover` declared-but-moot-as-a-count, not-moot-as-a-tier" — a category confusion, tier ⊥ count (inv 11): the `Wit`'s **T3 tier** (each witness's KEL `Wit` refreshes signing + recovery) is enforced **structurally** by the kind-strict KEL `Wit` ↔ IEL `Wit` anchor and gated by the **`t_govern`** count — not by a `t_recover` threshold; the reserve is still exercised every `Wit`, there is simply no `t_recover` count to declare.)*
  **The recoverability ceiling `≤ |roster| − 1` is HARD for the federation** (unlike a general identity, where it's
  advisory — G1 / inv 12): the federation is critical infra and must always be able to evict **one** compromised
  witness and recover without it, so `|roster| ≥ 3` is required (no fragile 1–2-witness federation). *(Surviving
  `k > 1` simultaneous losses is the operator's sizing choice — set `threshold ≤ |roster| − 1 − k`, §1e.)*
  **Compromise recovery = re-incept under a new prefix, not repair** [inv 13; `feedback_end_verifiability_not_pristine`].
  **A LOST member key (operator lost access — can't rotate it) is an operational failure mode, not an in-chain repair
  (cold-11):** evict-and-replace the lost member promptly via a cut+add `Wit` **while `t_govern` is still reachable**;
  if too many members are lost to reach `t_govern`, **reincept + swap members** (new federation prefix, global rebind).
  **Eviction's value is *roster-removal*** (the lost key out of `t_govern`-counting), **not window-closure.** The
  365-day auto-expiry (§1f) backstops the **dormant-forgery staleness** (a lost key's *witnessing* reads stale at 365
  days) — it does **not** bound the **cumulative-reserve-break → takeover** threat: a broken *reserve* mints a **fresh**
  window via the clock carve-out (§1e), routing around the expired one, so enough lost-then-broken keys cumulatively
  reach `t_govern` (a takeover = the `< t_govern` byzantine assumption violated). Only **roster-removal** (a cut) takes
  the lost key out of `t_govern`-counting. So **never leave a lost key in the roster** — the **at-risk flag** (§1f)
  surfaces which member to remove.
  *(A **missed** synchronized ceremony — keys still held, just un-rotated — is the **distinct, recoverable** case:
  catch-up rotation, §1f, no reincept.)*
- Witness **key rotation** is **a federation `Wit`** that pins the
  **pre-rotation KEL state** — recording the retired key's boundary into the
  federation timeline (this is what gives the clock each key's `T_end`, closing Finding 1). **The `Wit` IS the
  rotation: `Wit` anchors `Wit` (kind-strict, T3 ↔ T3, inv 4 — the governance-facet match is the **witness-config only**, Q3; the roster rides the manifest `Evl`-style, the `clock` is a single IEL-side value, monotonic + `≤ now+band`) — each participating witness
  authors a *single* KEL `Wit` that refreshes signing + recovery **and** anchors the federation IEL `Wit`; no
  separate `Ror`, no phantom key, and `pins = Wit.previous` so the retiring receipt key's `T_end` lands correctly
  (cold-4 B1; supersedes the round-4 `Evl`-rotation-pin and the round-7 `Ror`-anchors-`Wit` framing).** **Add/remove a witness
  is *also* a `Wit` (the federation has no `Evl` — a `Wit` carries any roster delta too).** **Roster-add consent (A1, 2026-06-28):** a *joining* witness consents via a KEL `Ixn` (joining-not-rotating — its `Fcp`→`Ixn` anchors the `Wit`), exactly the user-`Evl` joiner pattern; the **pre-add** witnesses approve via their KEL `Wit`s, which **alone** satisfy `t_govern`. **The load-bearing gate is pre-add-(outgoing)-roster membership (cold-8 F5), not just the kind:** `t_govern` counts **only KEL `Wit`s whose author ∈ the pre-add roster** — so a colluding `W_new` authoring its own KEL `Wit` (instead of an `Ixn`) cannot manufacture a `t_govern` vote (it is not in the pre-add roster). The kind split (`Ixn` joiner vs `Wit` approver) is the *additional* backstop that keeps the joiner's consent out of `t_govern` (Rule-A only, never `t_govern` — restoring C6); but the primary count is gated on **outgoing-roster membership** (inv 12). This closes the joiner-authors-a-`Wit`-and-self-approves takeover. `Wit.pins` = each approver's `Wit.previous` (a `T_end`) + the joiner's `Ixn.previous` (a `T_join`, never a `T_end` — cold-7 F2; diagram example 6). **Every federation governance change — a `Wit` (a rotation always, optionally also a roster change — A2) —
  commits an inline `clock` timestamp in its manifest** (§1f) and carries the federation's **own witness-config** (D1 / cold-7 F1). **This is a RARE event:** witnesses rotate
  **at least once every 365 days** (a hard auto-expiry — §1f; ML-DSA-87 handles annual rotation easily), and rotations are **typically synchronized** (one `Wit` covering all witnesses is the
  operational **norm, not a hard per-`Wit` rule** — a non-participating witness keeps its open key-window until it
  rotates, §1f), so the federation timeline advances roughly **yearly**, not per-receipt. *(Corrects the earlier "rotation = `Ror`, no
  federation change," which created the Finding-1 gap — the federation always intended to pin rotations.)* Federation IEL **`Fcp`** (the inception marker) = **T2** (like any IEL inception, [inv 15]), anchored kind-strict by a founder **`Rot`** (T2 ↔ T2 —
  the federation's own witnesses are `Fcp`-rooted infrastructure, governed *into* the roster, never self-bound; genesis
  is `Fcp → Rot`, 2026-06-28; the old founder-`Fed`-via-tier-elevation is gone — inception-reference §2).
- **Roster is a *delta*, not a full snapshot (B / F-A resolution, 2026-06-21).** A `Wit` carries
  `{ said, add: Prefix, cut: Prefix[], …thresholds }` — members joined and members removed, not
  the whole list (this delta SAD is the **`manifest.roster`** role, inv 4). **`add` is a *single* prefix, not a list — one witness added per `Wit` (except inception `Fcp`, which stands up the founding roster wholesale) — cold-seam P5, 2026-07-02.** Both an operational match (standing up a witness is deliberate infra, never bulk) and a **structural closure of the multi-add straddle**: a governance `Wit` never introduces more than **one unsynced witness**, and one fresh witness alone cannot reach a majority `threshold` (`≥ 2` for `signers ≥ 2` — its co-selectees are synced and decline the fresh sibling by first-seen), so the benign multi-add straddle-enabler (two fresh witnesses co-signing from routine join latency) **collapses into the priced witness-compromise residual** (a fresh sibling now needs a *byzantine* synced co-signer); the `signers = 1` degenerate straddle is unchanged (the pre-existing lone-witness case, warned). **`cut` stays a list** (cuts remove *synced* witnesses — no fresh-witness straddle — so emergency multi-eviction is unaffected; evict-and-replace is `cut: [..], add: one`). **Reachability property (VERIFIED, encode review 2026-07-02):** every valid target config is reached from a valid config by single-adds through valid intermediates — and stronger than hedged: a `Wit` carries `add` **and** `threshold` **and** `signers` in one event and the post-delta re-check runs against the **target** config, so any valid config at `|roster| = n+1` is reachable in **one** `Wit` from any valid config at `n`, no forced invalid intermediate (worked `{1,1}@3 → {2,3}@4 → {3,4}@5`). The only friction is the authoring step's self-attestation under the at-or-before config (no-self-weakening), which "usable" already guarantees, modulo the standing `{1,1}` position-luck warning. The current roster is reconstructed by
  **accumulating add/cut while walking** (the live set is always in memory). A `cut` removes a witness **by
  prefix**; **which of its keys may still sign valid receipts is bounded by the federation clock** (§1f), not a
  position-`terminator` (**dropped 2026-06-21** — see below). *(The cut-a-chain primitive survives only as the
  **delegate rescission** `bound` — delegations have no clock — inv 13 / delegation §5; federation removal no
  longer shares it.)*
  - **Hard cap on the live set:** while accumulating, if the live roster would exceed a cap (≈128/256), **reject
    the event as invalid** (a likely DoS / resource-exhaustion attempt). Bounds signature/threshold work + memory.
  - **The live roster is a SET (cold-9 Q2):** a `Wit` whose `add` names an **already-live** prefix is **rejected** —
    re-adding a current member would reset its `T_join` (re-open its key-window); the set discipline removes that
    ambiguity (defense-in-depth; the `t_govern`/Rule-A double-count is already closed by the kind-split). **`add` membership is tested against the *pre-delta* roster** — so a same-event `cut` + `add` of the **same** prefix (`cut ∩ add ≠ ∅`) is rejected too (cutting `W1` then re-adding it with a fresh `T_join` in one event can't route around the set discipline by ordering); evict-and-replace (`cut W1`, `add W2`, disjoint) is unaffected — the rule is **order-independent** (cold-14 F1). A **config change**
    is **re-checked on the post-delta config** (inv 12 — on **any `Wit` that changes roster, `threshold`, or `signers`**, not a `cut` alone; for the federation, its `Wit`): valid
    only if the **full witness-config validity** holds after the change — the **recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)`** with the `signers = 1` waiver (a bare `cut` re-applies the roster leg; a `signers`/`threshold` change re-applies the tighter `signers − 1` leg — the leg that actually binds for `signers ≥ 2`, F-obs — so a `signers` drop `{s 4, t 3}@5 → {s 3, t 3}@5` that passes `|roster| ≥ threshold + 2` but violates `t ≤ min(3,2)` is **rejected**, cold-seam F1), the **majority floor `threshold > signers/2`**, and the `t_govern` bounds still hold. So a **bare `cut`** that would strand the federation un-recoverable —
    even one that passes a naive `≥ 3` floor (e.g. `|roster| 5→4` at `threshold 3`) — is **rejected**, forcing
    **evict-and-replace** (one `Wit` carrying both `cut` and `add`) or a simultaneous threshold-and-`signers` drop, never
    a bare shrink (cold-9 B1 / cold-13 F1 / §1e).
  - **Durability is kept (default):** a cut witness's **established receipts still count** (no re-witnessing); the
    cut only stops it from witnessing **new** events — which falls out of the as-of rule (it's no longer in the
    *current* roster, so its receipts on current-pinned events don't count). **A witness wipes superseded / removed
    *private* key material on rotation (a `Wit`) and on removal (cut)** — forward secrecy; durability is unaffected
    because old receipts verify with the witness's **public** keys, which persist in its KEL.
  - **The federation clock bounds the cut witness's receipting key-window (replaces the position-`terminator`,
    2026-06-21).** The clock pins each witness key-window at every federation `Wit` (a rotation, optionally also a roster change — §1f); a cut
    witness, being out of the roster, can earn **no new pinned window**, so its forward-rotated keys never count —
    exactly the back-fill the old `terminator` blocked, now by **time** (`τ ≤ T_end`) rather than KEL position. A
    receipt counts only if signed within a federation-pinned window. The witness's **KEL is untouched** — the
    protocol only stops respecting its receipts past its closed window.
  - **Old-key harvest (F-A / S2) is a real vector — the forward-floor does NOT close it; wipe + the federation
    clock do (corrected 2026-06-21).** A *dormant* chain (last event `B` at an old `federationPin`, gone inactive)
    can be forged-extended: forge `C'` (`previous = B`, same old context), sign threshold receipts with **harvested
    old witness keys** from `B`'s era. A consumer checks them against `roster(F @ old context)` — which included
    those witnesses → they validate; there is **no real `B+1` to collide with** (divergence detection never fires)
    and the **forward-floor is irrelevant** (it stops an *active* chain regressing its own pin, not a back-dated
    forgery on a chain that never moved). The earlier "nothing to attach to except a fresh inception" claim was
    **false** — a harvested old receipt attaches to any historical-context verification of a dormant chain.
    **Closure, two layers:** (1) **wipe-on-rotation-and-removal** destroys superseded / retired private keys → no
    soft harvest target; the only extant era-`B` keys sit on witnesses *still using them* (a current key →
    compromising it is a *current* compromise). (2) The **federation clock (§1f)** time-bounds every key's validity
    window, and a receipt counts only if its timestamp is inside that window → a forgery built on a *closed*-window
    key is forced to carry old timestamps → the tip reads **stale** → detectable, fail-secure. Residual: a *current*
    threshold-compromise (open key windows) — the accepted `< threshold` byzantine assumption — and rotation closes
    those windows, making past forgeries detectable. *(Reverses the earlier "no wipe needed"; both review passes
    flagged it, and the drop rested on the false "durability needs the key.")*

### 1b. KEL federation binding
- KEL keeps **`Fcp`** (federation-infrastructure inception, T1) + **`Wit`** (the one witness/federation kind, T3): on
  an `Icp`-rooted **user** KEL a `Wit` is its federation bind/rebind; on an `Fcp`-rooted **witness** KEL a `Wit` is
  federation governance (a witness never self-binds — it is governed *into* the roster). Two fields on
  `Fcp`/`Icp`/`Wit`: **`federation`** = the federation **prefix** (which F; follows F's evolution) and
  **`federationPin`** = a **SAID** pinning a specific F-event (the as-of position; ratcheted via `Wit`).
  Prefix-vs-SAID [inv 7]. **Binding validation checks the `federation` prefix resolves to an `Fcp`-rooted IEL**
  (reject an `Icp`-rooted target — Q2); this + witnessing checks are the two times a verifier specifically *checks*
  the federation's `Fcp` (plus its structural role as the federation IEL's spine root, inv 17).

### 1c. Genesis + trust root
- Founder `Fcp` (v0) → `Rot` (v1) anchoring the federation IEL **`Fcp`** (the inception marker — kind-strict, T2 ↔ T2;
  the federation's own witnesses are governed *into* the roster, never self-bound — 2026-06-28). The
  federation `Fcp` (roster = founder witness KELs) + the founder `Rot`s land in **one atomic batch**, point-to-point
  (a *coordinator* is an operational convention — no election/leader). The **clock is incepted in this same batch**
  (the federation `Fcp`'s `manifest.clock` sets the founders' `T_join` = genesis time), so the timeline has a lower bound from event zero
  (Finding 6 — otherwise the pre-first-`Wit` window is unbounded).
- **Run `≥ 5` live witnesses, not the bare `≥ 3` (operator doctrine, Finding 3).** The hard floor counts *roster
  membership*, but a witness KEL can die **without a `Wit` cut** (lost key, destroyed device → can't rotate). At
  `|roster| = 3`, two such silent deaths drop the *live* set below `t_govern` → the federation can't author the
  `Wit` to replace them → stuck → federation reincept (global rebind). `≥ 5` keeps **`t_govern` reachable** with 2 losses
  — **but authoring is not enough: the replacement `Wit` must also self-attest** (cold-10 F1), which with `k = 2`
  unavailable needs **`threshold ≤ |roster| − 3`** (§1e general form), not the `|roster| − 2` cap. So to *recover* from 2
  simultaneous losses an operator runs a larger roster **and** sets `threshold ≤ |roster| − 3` (e.g. `|roster| ≥ 5`,
  `threshold ≤ 2`); the bare `≥ 5` with `threshold = 3` can author the eviction but not get it trusted. *(Corrects the
  earlier "`≥ 5` tolerates 2 losses," which counted only `t_govern` authoring, not self-attestation.)*
- **Trust root = the consumer's config-pinned federation *set* (cold-8 F4).** A consumer trusts a federation **iff
  its prefix ∈ the set it is configured to trust** (compile default + runtime override — `FEDERATION_IEL_PREFIX(ES)`,
  a **set**, not necessarily singular). The prefix derives
  from the whole inception content `(roster, threshold, nonce)` → a binding commitment to the exact founder set
  (matching = a Blake3 preimage). **`Fcp`-rootedness is *well-formedness*, NOT trust (Q2):** the binding-validation
  check (a `federation` prefix must resolve to an `Fcp`-rooted IEL) only rejects a malformed binding (one pointing at
  a user IEL); it does **not** confer trust. An attacker can stand up a real `Fcp`-rooted federation, but a consumer
  honors a binding to it **only if that prefix is in the consumer's config-pinned set** — so a stood-up federation a
  consumer hasn't pinned earns no trust. Trust = set-membership; `Fcp`-rooted = well-formed. **No self-*witnessing* carve-out** (distinct from the `Fcp` *marker*, which
  returns — §inv 4 / federation-ref §2/§4): the `Fcp` does **interpretation** (the verifier recognizes a federation
  IEL from its inception kind), **not trust** — authorization is ordinary member-anchoring (the founders *are* the
  roster), trust-rooting is inherently out-of-band, and the config-pin is the honest version of it; the genesis is
  **not** self-witnessing (it is cross-witnessed exclude-self once the mesh forms, like every federation event).
  Everything post-genesis (`Wit` governance — a rotation, optionally also a roster change) is witnessed normally.

### 1d. Rebinding
- A **user KEL's `Wit`** = (re)declare which federation witnesses this KEL (one of the kind's two facets — §1b). A
  multi-`Wit` history → trust is **per-federation,
  non-transitive**: a verifier independently trusts *each* federation prefix the chain bound to, and each event is
  witnessed by whichever F was current when it landed — so witnessing is **range-based** (a contiguous run between
  `Wit`s shares one context). The verification token reports the **witnessing ranges** (`[from, to) → F | none`),
  **per range, not per event** (bounded by the `Wit` count — `Wit`s are rare privileged acts; a **hard cap on
  `Wit`s/chain** rejects a ping-pong DoS, inv-14 pattern — over-cap → reincept). A consumer **must not** assume "has a
  `Wit` ⇒ all events witnessed" (cold-5 C1a; the rule applies to rebind chains too, not only direct-mode).
- **The migration window is cooperative-only (cold-4 B2).** *(This is **user-identity** rebind overlap — distinct
  from a witness serving two federations, which is **dropped**: witnesses are single-federation, §1a.)* The
  overlapping-federation trust that bridges a **user-identity** rebind
  (members below `t_govern` lagging on the old federation until they each rebind) assumes **both** federations are
  **honest** — a graceful, app-coordinated migration both approve. It does **not** cover *escaping a compromised
  federation*: there the old F still counts during the overlap, and an IEL event mid-migration can't be verified under
  the target federation alone (its lagging members are old-F-witnessed). **Escaping a compromised federation is a
  hard cutover / reincept, not a graceful overlap.** Multi-federation migration is **application-level** — the
  framework gives the per-federation primitives + recommendations, not an orchestrated protocol.
- **Direct mode is a reachable mode (cold-5 C1a).** A user `Icp` **may omit** its `federation`/`federationPin`
  (*absent ⇒ direct-mode*, intentional; *present ⇒ federated*) — so a chain can incept **un-federated**. Its **first
  `Wit`** then binds a federation and witnessing **starts forward** from that event (the early range stays unwitnessed
  — a `Wit` never witnesses the past; the as-of-context rule, so no retroactive witnessing / no backdate vector). A
  direct-mode chain is fully **end-verifiable** (SAID + sig + chain linkage need no federation) but earns **no witness
  receipts**, and it **keeps *local* divergence detection** (a held fork freezes the chain, inv 13 / F-F) — it only
  lacks the **beacon's propagation** to one-branch holders + multi-source. **Fail-secure (cold-5 C2):** a loss-of-trust
  decision that can't multi-source-confirm a `Trm` (direct-mode, or any eclipse/single-source) **refuses**, never
  proceeds-with-a-flag. **Mixing** a direct-mode member into a *federated* identity silently degrades that identity's
  freshness (that member is single-source) → keep a direct-mode identity **whole-solo** (guidance, not a hard reject).
- **Multi-federation is out-of-scope-but-allowed** (the per-federation, non-transitive model **is** the whole
  allowance — no orchestration is designed). Multi-source *independence* is a **policy/app-layer** choice (`thr`/`and`;
  a consumer counts **distinct witness KELs**, not federations — document-policy R4).

### 1e. Witnessing — propagation of the divergence signal; the data detects (reframed 2026-06-23, supersedes "witnessing detects")
- **Receipts are adjacent attestation data** (unanchored), like a KEL's signatures.
- **Witnesses are reporters, not deciders** — they don't pick a canonical branch.
- **Content-fork prevention — the majority floor + one-content-sibling-per-serial (2026-07-02):** a selected witness
  signs the **first** structurally-valid **content** (tier-1 `Ixn`) event it sees at a `(prefix, serial)` and
  **declines any later content sibling** there (first-seen, per-serial). With the **majority floor `threshold >
  signers/2`** (§witness-config) two content siblings then **cannot both reach threshold** — their threshold-quorums
  share `2·threshold − signers ≥ 1` witnesses and that witness signed only one — so a **content divergence never forms
  on a witnessed chain**; it is **prevented, not detected**. This holds at **KEL positions and user-IEL positions**: a
  user-IEL content event is majority-witnessed **at its own position** — the fork-prevention gate alongside its
  anchor-based authorization (§witness-config / inv 12; **option (b)**, 2026-07-02) — and **SEL rides the cross-layer
  theorem** (a valid SEL fork ⇒ an IEL fork, so closing IEL content forks closes SEL content forks — inv 4 /
  repair-completeness proof). The **federation IEL is exempt** (it authors no content; its every fork is privileged →
  `disputed`). A content fork survives **only** where no majority gates it — **direct-mode / no-witness**, a
  **witness compromise** owning the whole intersection (`≥ 2·threshold − signers` witnesses, the fork-cost), or —
  rarely — **across a roster delta** (two full quorums under disjoint contexts, zero double-signers — the F5
  straddle, §witness-config: under the propagation premise below it additionally requires the new selectees cut off
  from the already-propagated old quorum, so it is an entrance to the partition/eclipse residual, not a
  freestanding race).
- **Privileged: sign up to TWO distinct siblings per position (Jason 2026-07-02 — subsumes the repair clause):** a
  selected witness signs the first **two** distinct structurally-valid **privileged** siblings
  (`Rot`/`Ror`/`Rec`/`Wit`/`Trm` + IEL/SEL analogs) at a `(prefix, serial)` and **declines further ones** — two
  both-witnessed privileged siblings ARE the **`disputed`** proof (≥ 2 privileged branches — terminal + absorbing; a
  third adds no evidence, and a spent preimage can mint unbounded distinct siblings, so the duty must cap where the
  proof completes — the witnessing twin of inv 17's ≥ 2-per-position retention). A privileged fork is **dispute
  evidence** that must reach the beacon; on a content-only divergence the first privileged sibling at the position is
  exactly the **single resolving repair** (a repair is privileged — no separate exemption needed), and a *second*
  competing repair is the proving pair `{Rec, Rec}` → `disputed`. So **divergence detection is now privileged-only**
  (content is prevented upstream). **Residual** content-fork
  evidence (direct-mode / witness-compromise) is still retention-bounded at **≥ 2 per position** (the content analog of
  inv 17's privileged **≥ 2-per-spine-position** — "two prove the fork, then stop"), depth ≤ 64 per lineage (the
  seal-cap); a witness holding a repair declines to re-witness dead content (efficiency only — deadness descends
  regardless).
- **The split/tie stall + its exit (warm F3):** one-content-sibling-per-serial partitions the receipts at a forked
  position (`a + b ≤ signers`); if neither content sibling reaches majority (an even-`signers` tie, or
  abstentions / a partition) the **position stalls, fail-secure** — signed witnesses cannot switch. A **minority
  partition therefore stalls, never forks** (consistency over availability — the CP corner of the floor). The **exit
  is the repair**: a `Rec`/`Rpr` at the position is privileged — the first privileged sibling there, signed by every
  selected witness under the two-cap above (including those that signed a content sibling) — and reaches
  majority. Attached at the author's own stalled sibling it **retains** that branch (the witnessed repair commits it
  as `previous` — local progress below) and the competing sibling closes below the seal; attached at the shared
  ancestor (the author authored neither) it archives both — `fork` names one root, the second closes below the seal +
  by descent (inv 4). Content-only → permitted; stalled honest content re-issues forward. **Odd
  `signers` avoids the pure tie** (operator guidance): with every selected witness voting, an odd set always yields a
  strict majority for one sibling — the stall then needs abstentions, not just a race.
- **Propagation premise (stated 2026-07-02, Jason — load-bearing for prevention, never for safety):** once an event
  is **witnessed in full**, prompt roster-wide propagation is assumed (the push-gossip mesh), barring a partition —
  a roster member ordinarily sees a completed quorum before any later sibling arrives, which is what arms the
  first-seen declines above (a newly-selected witness declines a sibling at a position it has already seen taken).
  The premise carries the prevention layer's **success rate** and detection **latency** only — **safety never rests
  on it**: a fork that forms despite it lands in freeze → repair (inv 13), and nothing false becomes canonical on
  any node. Without the premise the prevention leg falls apart; with it, the F5 roster-delta straddle requires the
  new selectees to have been **cut off from the already-propagated old quorum** — an entrance to the
  partition/eclipse residual, not a freestanding race. **The *benign* multi-add case is structurally closed
  (cold-seam P5, §1a):** `add` is one witness per `Wit`, so a transition never yields ≥ 2 fresh unsynced
  selectees co-signing from routine join latency — one fresh witness can't reach a majority `threshold`
  against synced co-selectees who decline by first-seen, so the straddle now needs a *byzantine* synced
  witness (the priced witness-compromise residual) or the `signers = 1` degenerate (the pre-existing
  lone-witness warn). So the residual is genuinely just partition/eclipse + witness-compromise, no benign
  race. **Rejected — the cold-F5 "prior-context receipt"
  hardening** (a witness declines a position for which it holds a threshold-real receipt set under any
  *prior* roster context): it is the **same trust class** as first-seen (witness behavior, honest-majority
  priced, unverifiable from chain data — not a structural rule), it only closes the *informed* half of the
  straddle (the new selectees must already hold the old quorum's receipts — which under this premise they
  hold *anyway*, so first-seen already declines), and it puts cross-context historical verification in the
  witnessing hot path. The straddle is a recoverable content fork (freeze → one repair); the honest fix is
  the per-context marker scoping above, not more witness machinery.
- **Dead-event gate (garbage reduction, 2026-07-01):** a witness that **already holds the repair** (`Rec`/`Rpr`)
  that condemned a fork **declines to witness** dead **content** events on a **dead** branch — one whose ancestry passes through a
  condemned `fork` root or a below-seal fork. **A privileged event is witnessed even in a dead subtree** (up to the two-per-position cap) — it
  is dispute evidence (it forces `disputed` and must reach the beacon; F5), never garbage. This is an **efficiency gate, not load-bearing:** deadness descends
  (inv 13 — an event whose parent is dead is dead), so a dead event that a lagging witness signs before it holds the
  repair is still **retained (keep-all-data) and dead-by-descent**, never canonical. It just keeps witnesses from
  amplifying a signing-key adversary's dead content — the one-content-sibling rule + retention above are the primary bounds (breadth ≥ 2-per-position, depth ≤ 64 per lineage; inv 4 / inv 13); this is their post-repair complement for a lagging witness.
- **Deterministic selection by `(prefix, serial)` + sub-mesh event-gossip (2026-06-23):** competing events at a
  position route to the **same** selected witness set (so the quorum-intersection is over **one** set), and the
  selected witnesses **sub-gossip the event among themselves**. A receipt counts toward an event's threshold **only if
  its signer ∈ `select(prefix, serial, …)`** — the *selected* set, not merely `roster(F @ context)` (F3, 2026-07-02;
  the intersection guarantee is over the selection, so the counting predicate must be selection-scoped). For a
  **privileged** event, sub-gossip means it reaches every selected witness → **no stable "witnessed but sub-threshold"
  state** (the only ways to hold it sub-threshold are pure eclipse or a byzantine witness signing-then-withholding, a
  rogue phantom receipt → discard + evict, bounded by `< T`); two competing privileged siblings therefore both reach
  threshold → `disputed` (further privileged siblings at the position are declined — the two-cap above). For
  **content**, first-seen-one-per-serial + the majority floor mean a competing content
  sibling **does not** reach threshold — the fork is prevented, so there is no sub-threshold content state to
  reconcile. **For a federation member's own KEL events** (a witness's `Wit`/`Ror`/etc.): the same algorithm with
  **that witness's own prefix removed** (exclude-self — a witness never receipts its own event), select from
  `roster − {self}` seeded by `(prefix, serial)` → pool `|roster| − 1` (Q1). *(The federation **IEL** `Wit` keeps pure
  **self-attestation** — no position gate — because its every fork is privileged → `disputed` anyway; the **user
  IEL** gets a position gate — option (b), §witness-config. So an all-witness federation rotation never bricks.)*
- **ALL inter-node mesh traffic is ENCRYPTED (2026-06-23, generalized from receipt-gossip-only):** ML-KEM-1024 KEM +
  AES-256-GCM AEAD — receipts AND the events they propagate. Confidentiality, not trust (trust is end-verifiable).
  The mesh = the federation roster, so mesh contents (including a cred-SEL receipt's `(prefix, said(v1))` pair) stay
  within the federation; a witness can correlate `issuer ↔ private-prefix` (passive, undetectable → a standing
  confidentiality property of membership — inv 16). AEAD nonce/key-scope discipline is owed at the doc layer.
  **Push over pull (Jason):** prefer gossiping events to a separate inter-node *query* — the sub-mesh event-gossip
  already pushes competing events to selected witnesses; extend it so a one-branch holder gets the branches by push,
  so there's no second channel to secure (the residual by-prefix fetch shrinks, rides the same encrypted mesh). Build
  detail → `vdti-implementation-notes.md`.
  **⚠ RESOLVED (Jason 2026-06-26):** the encryption **public key lives in a SEL** owned by a **degenerate per-device
  IEL** — a single-member IEL (`members = [the witness device KEL]`), **derivable from the KEL prefix** (+ a purpose
  discriminator). It's a **restricted IEL** whose kind set **excludes `Evl`**, and the general **post-delta `|roster| ≥ 1`** rule (inv 12) forbids cutting the
  sole member (a `Rpr`-cut computes `1 + 0 − 1 = 0`, rejected), so — with no `Evl` to grow — its roster is
  **immutable** (a general rule, not a federation-member special case); no new "immutable" manifest field, and
  `t_govern` stays mandatory (singleton exception → all thresholds = 1). Kind set ≈ `{Icp, Ixn, Rpr, Trm}`.
  **It does NOT break the `Fcp` bootstrap** — the IEL is *derived*, not separately incepted: the device KEL exists
  first (`Fcp`) → its degenerate IEL derives → it owns the key SEL; "reincept" = re-derive from the recovered KEL
  (the KEL carries the rotation/recovery story). Discovery: federation roster → witness KEL prefixes → derive each
  degenerate IEL → its key SEL.
- **Receipts ENUMERATE the branches; the data decides (reframed 2026-06-23; re-keyed post-floor 2026-07-02):**
  competing receipts at a position list the branches a verifier must gather — but **terminality is a data-local
  branch-level walk** (inv 13 / 17: ≥ 2 branches each with a privileged event past the fork, over **retained**
  branches), **not** a receipt count. The **FORCE rule splits by provenance:** a node that **holds and re-validates**
  ≥ 2 privileged branches forces `disputed` **immediately**, threshold-independent; a node holding only a **receipt**
  for a *privileged* event it hasn't fetched waits for the **witness `threshold`** before treating the signal as real
  (below threshold a rogue's receipt on a fake event is inert — the verifier re-checks validity). For **content** the
  signal re-derives (F1-consequence): a losing content sibling **never reaches threshold** under the floor, so
  waiting for threshold on it means waiting forever — the anomaly signal is a **sub-threshold competing receipt set
  at a position**, which *enumerates* → fetch the event (push/beacon) → the data-local walk decides; threshold
  authenticates only the *winning* branch. Receipts say *forked*; the data-local walk says *disputed*. Divergence
  stays **locally determinable on every node** (no watcher infra) — a first-class, queryable chain state — a
  **privileged** fork is **detected** once the branches reach a verifier; a **content** fork on a witnessed chain is
  **prevented** upstream (§1e), detected the same way in the residual.
- **Witness-config SAD** (the manifest **`witnesses`** role, inv 4) `{ said, threshold, signers }` on `Icp`/`Wit`
  (KEL **and** user IEL; the **federation IEL** carries its own on `Fcp`/`Wit`, adjusted each governance `Wit` — D1 /
  cold-7 F1, below), **mandatory iff federated** (else fail-secure reject — cold-7 F3): **`threshold`** = valid
  receipts required for **consumer trust** — app/operator choice **by chain criticality, above a structural majority floor `threshold > signers/2`** (a strict majority of the *selected* witnesses — two threshold-quorums **within one roster context** share `2·threshold − signers ≥ 1` witnesses, and an honest witness signs at most one **content** sibling per serial, so **two conflicting content siblings can never both be witnessed** (privileged siblings are always co-witnessed → `disputed` — §1e) → no partition / disjoint-sub-quorum **content** fork; manufacturing a content fork costs owning the whole intersection, **fork-cost = `2·threshold − signers`** — a priced, tunable security parameter, not a free consequence of the network (the dial trades against availability: `fork-cost = threshold − slack` where `slack = signers − threshold`, so fork resistance and receipt redundancy trade one-for-one — at `threshold = signers` fork-cost is maximal but one unreachable witness stalls the position; and the one-content-sibling **violation is attributable** — two receipts by one witness over **two distinct *content* `witnessed_said`s** at one position (or a **third** distinct privileged sibling past the two-cap) are cryptographic proof of misbehavior → the minority-dissent forensics → eviction, so paying fork-cost means owning *and exposing* the intersection — warm F7. **The predicate is tier-scoped (cold-2 F1):** an honest witness legitimately holds `{≤ 1 content} ∪ {≤ 2 privileged}` at a position — the mandated **cross-tier co-sign** (a content sibling **and** the resolving repair, when the repair attaches at the shared ancestor — split-stall exit above; or any `{Evl/Rev/Dth, content}` recoverable fork) is **not** misbehavior and must be excluded by construction, else the forensics would evict the honest witnesses the split-stall exit requires and muddy the clean attribution the fork-cost pricing rests on). **The intersection rests on the selection-input rule (warm F4):** selection is a function of **`(prefix, serial)` over the current roster membership only** — never the event's bytes or its pin — and the **currency gate** (below) pins the membership input (a stale-membership pin earns zero countable receipts), so an adversary cannot mint sibling-specific witness sets. **Across a roster delta the two quorums need not intersect (F5):** receipts are durable and judged as-of their own pin, so a sibling witnessed-in-full under the old membership + a fresh-pin sibling under the new can hold disjoint quorums with zero double-signers — a **residual** = a roster delta × a propagation failure (under the propagation premise, §1e, the new selectees have ordinarily seen the old quorum and first-seen declines the fresh sibling) — the partition/eclipse family's entrance, not a freestanding race; detection unaffected (the branches still collide and freeze on co-observation); so witnessed-in-full is a **per-context** uniqueness certificate, not an absolute one); **`signers`** (M ≥ threshold) = witnesses **selected per event**, over-provisioned for redundancy
  (M − threshold receipts can fail and the event stays trusted). Bounds `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|` (lower bound = the majority floor above). (this `|roster(F @ context)|` bound is the **user/KEL** chain's, external witnesses; the **federation IEL** is tighter — `threshold ≤ min(|roster| − 2, signers − 1)`, the recoverability cap below / cold-9 B1 + F6.) **Orthogonal** to the federation's own `t_govern` (Q3): that governs F's roster changes; this governs
  a member's receipt-gathering. (`signers` = kels `witness_selection_size`, renamed this session.) **Per-layer (D1, 2026-06-28):** a **KEL** carries its own config (for its KEL events); a **user IEL** carries its **own authoritative** config (for IEL events — an IEL event is witnessed and could otherwise fork without any member KEL forking, two disjoint sub-quorums each authoring a valid event at one position — the content case now closed by the option-(b) gate below, the privileged `{Evl, Evl}` remaining — so it needs its own), **independent** of member configs (not matched — different chains' events); the **federation IEL** carries its own (cold-7 F1); a **SEL inherits** its owner IEL's (single-owner). On `Icp`/`Wit` (user/KEL) or `Fcp`/`Wit` (federation IEL). **Q1 RESOLVED (Jason 2026-06-29) — self-attestation:** an IEL has no key of its own (it is a threshold over member KELs), so an IEL event's witnessing **is** the witnessing of its **member KEL anchors** — the event is trusted when a threshold of its anchoring KEL events are witnessed (this config's `threshold`/`signers` set that bar). IEL events propagate + earn receipts **as per usual**. **Authorization** stays the witnessed KEL anchors (Q1); **fork-prevention** adds a second gate — **option (b), 2026-07-02: a *user* IEL's content events must also reach a majority quorum at their own `(IEL prefix, serial)`** (the same content-fork prevention as a KEL — §1e), so two disjoint member sub-quorums can't both land a content event at one IEL serial (`{Evl, Evl}` and other **privileged** IEL forks are unaffected — always-witnessed → `disputed`). The **federation IEL keeps pure anchor-based self-attestation** (no position gate — its every fork is privileged → `disputed` anyway): its member witness-KELs witness **each other's** KEL events **exclude-self** (a witness never receipts its own), pool **`|roster| − 1`** — so for federation member events `signers/2 < threshold ≤ min(|roster| − 2, signers − 1)` (the majority floor **and** the **recoverability cap** — below) and `threshold ≤ signers ≤ |roster| − 1` (a user chain stays `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|`, external witnesses). **The quantifier (cold-9 Q1):** the IEL `Wit` is trusted when the **`t_govern`** member KEL `Wit`s that anchor it are **each** witnessed at the witness-config `threshold` — two distinct counts (`t_govern` = how many anchoring KEL `Wit`s; the witness-config `threshold` = receipts per anchor) — and the anchors counted are only those witnessed **consistently with the IEL `Wit`'s own at-or-before context** — for a **user** IEL its `federationPin` context, for the **federation** IEL its own position on the federation chain (which carries **no** `federationPin` — that's a user/SEL binding field, forbidden on the `Fcp`-rooted chain; the no-self-weakening rule already pins it — cold-10 F3) — or freshly, for a loss-of-trust read; so a stale-context KEL anchor (from an old roster where a since-cut witness still counted) can't self-attest a current-context IEL `Wit`. **Recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)` (cold-9 B1 + F6, verifier-rejects higher):** an eviction/recovery `Wit` is authored by the remaining members **and must self-attest** — the evicted/dead member won't co-witness, so the self-attest pool is `|roster| − 2`, and at **sub-pool selection** (`signers < |roster|`) the *selected* pool loses one too, so `threshold ≤ signers − 1` also binds (the `|roster| − 2` cap is exact only at full-pool selection — worked `{signers 3, threshold 3} @ |roster| 5` passes `≤ |roster| − 2` yet can't self-attest the eviction). **The `signers − 1` leg is WAIVED at `signers = 1`** (the lone-witness carve-out, exactly as the majority floor is vacuous there) — otherwise it would read `threshold ≤ 0` and empty the `|roster| = 3` config space, a de-facto floor bump the `≥ 3` decision rejected; the honest statement is that at `{1, 1}` **evict-one self-attestation is position-luck, not a guarantee** (the eviction anchor's selection of 1 from its pool of 2 may name the dead member → stuck → reincept) — **warned**; the *guaranteed* evict-one begins at `|roster| = 4` `{2, 3}` (full-pool: the dead member's absence still leaves `threshold = 2` receipts). *(Composition — the two legs never conflict, warm F-obs: for `signers ≥ 2`, `threshold ≤ signers − 1` together with `signers ≤ |roster| − 1` already gives `threshold ≤ |roster| − 2`, so the `min`'s **roster leg binds only at the waiver** (`signers = 1`, where the `signers − 1` leg is off); everywhere else the `signers − 1` leg is the tighter one.)* Capping `threshold` there (the direct analog of `t_govern`'s gratuitous-hostage rejection, inv 12) guarantees the federation can always evict **one** compromised witness and get the cut trusted. **General form (cold-10 F1):** self-attesting a governance `Wit` with `k` members unavailable needs `threshold ≤ |roster| − 1 − k` (each remaining author's KEL `Wit` is witnessed by the *other* available members, exclude-self → `|roster| − k − 1` receipts). The **hard cap is `|roster| − 2`** (`k = 1`, the *evict-one* guarantee); surviving `k > 1` simultaneous losses is the **operator's sizing choice** — choose the **tolerated simultaneous-loss count `k`** explicitly (an operator parameter, not buried in doctrine; cold-11), then set `threshold ≤ |roster| − 1 − k` and grow the roster to keep `t_govern` reachable too (§1c). At the `≥ 3` floor this forces **`{threshold 1, signers 1}`** at `|roster| = 3` (the majority floor rejects `{1, 2}` as sub-majority, so the `signers` collapse rides along) — **governance** stays safe (it rides `t_govern`, not this bar), but **witnessing byzantine-tolerance at `threshold = 1` is 0** (a single byzantine member's receipt makes a branch read "witnessed," so under eclipse one rogue can mask a fork — cold-10 F2; it *does* weaken witnessing, contra "weakens nothing"). That degenerate floor case is why the operator doctrine is **run `≥ 5`** (§1c), where `threshold` rises to give real witnessing fault-tolerance — and the **config-time warn family covers every fork-cost-1 config** (`signers = 2·threshold − 1`, the minimal majority — F11/cold-F4): deterministic selection makes a thin intersection a **precomputable target** — an attacker can enumerate in advance exactly which witness(es) gate a given `(prefix, serial)` — with the forced `{1, 1}` lone witness at `|roster| = 3` the extreme case (0 witnessing byzantine-tolerance isn't a free choice — analogous to the 2-device-identity warn-not-reject, inv 12; cold-11). **The rule (Jason 2026-06-29):** the verifier **rejects only *un-usable* configs** — a hostage `t_govern = |roster|`, a can't-self-attest `threshold > min(|roster| − 2, signers − 1)` (**both** cap legs — the `signers − 1` leg is the binding one for `signers ≥ 2`, cold-seam F1; waived at `signers = 1`), a **sub-majority `threshold ≤ signers/2`** (it re-opens the disjoint-sub-quorum fork the majority floor closes — witness-config bullet above), a sub-`≥3` roster (for the spine, *un-recoverable* counts as un-usable) — where **un-usable = cannot function, or cannot deliver the semantics the witnessed-in-full marker asserts** (F10: a sub-majority config *functions* — receipts flow, propagation + data-local detection work — but its marker no longer means per-position exclusivity, a consumer footgun; the intentional casualty is detection-only low-`threshold`/high-`signers` configs, e.g. `{3, 10}` for latency) — and **allows any *usable* config, warning of the consequences** (`threshold = 1` is usable + recoverable **only at `signers = 1`** — a lone-witness config, majority-vacuous with 0 byzantine-tolerance; any multi-signer config must clear the majority floor — cold-12 F4). The **floor stays `≥ 3`**, no bump; a `cut` is **re-checked on the post-delta config** (inv 12 — on any `Wit` changing roster, `threshold`, or `signers`) — valid only if the **full cap `threshold ≤ min(|roster| − 2, signers − 1)`** (with the `signers = 1` waiver) **and the majority floor `threshold > signers/2`** both hold after the change, so a bare shrink that would strand the federation un-recoverable (`|roster| 5→4` at `threshold 3`) **or a `signers`-drop landing on the binding leg** (`{s 4, t 3}@5 → {s 3, t 3}@5`, cold-seam F1) is rejected, forcing **evict-and-replace** or a threshold-and-`signers` drop, §1a (cold-13 F1). A **`Wit`'s own self-attestation is judged under the at-or-before witness-config + roster** (no self-weakening — a sub-quorum can't lower its own trust bar or pad its pool in the very event whose trust is in question), **but under the NEW key-windows the rotation establishes** — the fresh keys its anchoring KEL `Wit`s reveal (`T_join` = the rotation's own clock, F4-bounded), **not** the possibly-expired at-or-before windows (**the clock axis is carved out of no-self-weakening — cold-11**; judging a rotation's fresh-key receipts under expired old windows is a category error and would brick the federation on a single missed annual ceremony). So an **all-windows-lapsed federation reads stale (fail-secure), then recovers via a catch-up rotation** that self-attests under its new windows — stale-but-recoverable, never bricked. This does **not** let a lone broken/old key mint a current window: a witness rotation is honored **only** as a federation `Wit`, needing `t_govern` authors **and** `threshold` self-attestation — one key reaches neither (a current-window takeover needs `≥ t_govern` keys = the byzantine assumption violated → reincept; a *lost* key is evicted/reincepted operationally, §1a). The federation `Wit` thus **never bricks** even when every witness participates (its trust rides its cross-witnessed exclude-self KEL anchors, not an exclude-all-participants aggregate). Divergence stays data-local: a `Wit` fork's competing branches are anchored by witnessed KEL `Wit`s that propagate, surfaced by the keep-all-data walk. *(Supersedes the round-8-draft `|roster| − |participants|` aggregate-gate — it bricked an all-witness rotation; cold-8 F1.)*
- **As-of-context evaluation (durability):** a receipt counts iff its signer ∈ **`select(prefix, serial, roster(F @ federationPin), signers)`**
  — the deterministic selection derived over the as-of roster (the selection-scoped predicate, F3 — §1e above), the pin being the most-recent `Icp`/`Wit` at-or-before the event (an **IEL** event uses the identity's **own** authoritative `Wit`/`Icp` binding, never an individual member KEL anchor; a **SEL** inherits its owner IEL's — cold-3 B2),
  forward-floored on the KEL. **Never at F's current tip.** F and witness KELs are append-only, so an event stays
  witnessed **forever** — **no re-witnessing** of historical data.
- **Acceptance-time currency gate — exact-tip, NO grace window (reviewed 2026-06-24; `graceSeconds` dropped).** *(This gate is a **user/SEL-chain** mechanism — the **federation IEL itself carries no `federationPin`** (F3), so it does not apply to the federation chain; the federation's own freshness is its clock + the 365-day auto-expiry, §1f — cold-11.)*
  Witnesses refuse to witness an event whose `federationPin`'s **roster (membership)** isn't current, forcing an
  active chain to advance `federationPin` by carrying a fresh one on its **next event of any kind** (no `Wit` needed — `federationPin` is optional on every event, 2026-06-25) — **lazily, on next activity**. **The gate compares
  roster MEMBERSHIP, so it fires on a *cut* (a witness removed), NOT on a pure rotation-pin** (same witnesses, new
  keys — the clock §1f bounds key time-validity, so a pre-rotation pin is safe). This bounds the re-pin to **rare cuts**, not every rotation — and the re-pin is **cheap** now (it rides any event; a tier-3 `Wit` is needed only to *rebind*, or when a cut shrinks the roster below the chain's `signers`). **No grace window:** a since-cut witness earns **zero**
  countable receipts immediately — any `graceSeconds > 0` would re-admit the pre-cut roster for that window,
  reviving exactly the backdate sliver the gate exists to stop (and would have to be set to 0 in the very
  emergency it was sold for). A stale in-flight event is **not stranded** — it lands sub-threshold and the next
  `Wit` re-pins under the current roster and witnesses, transitively covering it (see *local progress* below).
- **Local progress on own un-witnessed events (load-bearing for exact-tip recovery, 2026-06-24).** A submitter's
  node accepts its **own** structurally-valid, sub-threshold events as the local tip — you can't extend a
  `Rot`/`Rec` you haven't landed — so it makes forward progress *ahead of* witnessing; the **re-pinning event**
  (any event carrying the current `federationPin`) is what earns **cross-node** acceptance for the run (peers defer an un-witnessed
  event but fetch it once the witnessed re-pin commits it as `previous`). This is what recovers a stranded
  irreversible `Rot` (extend it with a witnessed re-pin) and a frozen-chain `Rec` (land the repair → chain is
  locally Active → re-pin under the current roster) **without any grace window** — the recovery rests on the **recovery reserve**
  (the standing tier-3 requirement), never on retaining the old signing key (the "delay the wipe" idea was a
  no-op — the re-pin signs with the *next* rotation preimage + the recovery reserve, neither being the old key).
- **Backdate closure — wipe (forward secrecy) + the federation clock; the forward-floor covers only active chains
  (corrected 2026-06-21, F-A / S2).** The forward-floor stops an *active* chain pinning an old context — but a
  **dormant** chain's forged extension isn't an active chain, so the forward-floor doesn't reach it (§1a). The
  load-bearing closure is **(1) wipe-on-rotation-and-removal** (no harvestable retired keys) **+ (2) the federation
  clock (§1f)** time-bounding each witness's key-validity window, so a closed-window key can only stamp old
  receipts → a dormant forgery reads stale → **detectable, fail-secure**. **Rejected: history-pinning** (a CT-style
  threshold-signed checkpoint over the witnessed set) — the clock achieves the same detectability **without**
  per-chain tracking or anchoring every signature (it timestamps the federation's own infrequent `Wit`s; consumers
  check locally), so the checkpoint's burden isn't warranted. Also rejected: immutable / never-rotate witnesses
  (only *widens* the validity window — the opposite of what wipe + rotation give).
- **Non-witness acceptance gating:** a node *not* selected as a witness for E holds E **deferred-pending** until E
  reaches `threshold` receipts (so a non-witness can't accept attacker events the witness set rejected).
- **The witness decline IS the shape-validity acceptance gate; merge is relaxed (2026-07-03, inv 13 — resolves cold F2 / warm H1).**
  Merge integrates every structurally-valid event (keep-all-data) + the seal-cap and computes the reading as a
  **pure walk** (the seal derived from the held events); it does **not** stick-freeze the *reading* — that made it
  arrival-order-dependent. The **shape-validity gate** — reject a seal-advancer that would bury a *privileged*
  branch, a `Rec`/`Rpr` condemning a privileged branch or its own retained chain — runs at the
  **acceptance-to-trusted-state** point in **both** modes: a **selected witness** applies it before signing
  (decline → the shape never reaches `threshold`); a **non-witness** gates on `threshold` (above); and on a
  **direct-mode** chain the **merging node self-gates** at merge (no witness to defer to). "Frozen" survives only
  as a **merge-origination** posture (a node originates no new work onto a live fork), never as the reading — so a
  fork-first and a seal-first node holding the same events read identically. Content-fork **prevention** (the
  one-content-sibling floor above) stays **witnessed-only**; a direct-mode content fork forms, reads `forked`
  (fail-secure), and resolves by repair or by a burying seal-advancer — declining it by first-seen with no shared
  witness would silently split (fail-open).
- **Security assumption / residual:** **< `threshold` byzantine** federation members at attestation time; beyond
  that = operational + reincept (same posture as the divergence model). **The co-witnessing exclusivity carries its
  own, tighter bound (F4):** it holds against **< `2·threshold − signers` byzantine double-signers *within the
  selected set*** (the fork-cost) — and `2·threshold − signers < threshold` whenever `signers > threshold`, so for
  every over-provisioned config a coalition *within* the blanket `< threshold` assumption can manufacture a
  co-witnessed content fork (worked: `{threshold 3, signers 5}` — fork-cost 1, one double-signer + an arrival split
  of the honest four). The blanket `< threshold` assumption covers witnessing/receipt integrity; the exclusivity
  guarantee is priced at fork-cost — the slack identity in the witness-config bullet.
- **Global residual — detection is *eventual*, not at-decision-time (stated plainly, 2026-06-21).** Every
  detection guarantee here (divergence, a dispute, a moved effective-SAID, a cross-layer break) assumes the
  consumer can **reach enough honest witnesses / converged gossip** to *see* the competing branch or the changed
  state. A consumer **eclipsed** to a malicious subset, or reading **during an incomplete heal**, sees the
  detection **later**, not at decision time — so a binding made in that window can transiently trust the wrong
  branch. This is the standard cost of the **detection** leg (everything beyond witnessed-content prevention — the
  floor prevents a content fork *forming*, it can't make a formed privileged fork visible any sooner); the F8
  multi-source freshness bar *shrinks* the window (more independent sources → harder eclipse) but doesn't close it. Recovery is operational
  (re-verify before binding; reincept on a surfaced divergence).

### 1f. The federation clock — staleness detection without per-chain tracking (S2, 2026-06-21)
- **What it closes:** the dormant-chain forgery (§1a / S2) — converting it from *silently accepted* to
  **detectable-as-stale** (fail-secure), the bar wipe alone can't reach. Composes with wipe: wipe removes the soft
  harvest target; the clock makes the residual (a closed-window key) detectable.
- **The clock = the `clock` role in each federation `Wit`'s `manifest` (a rotation, optionally also a roster change) → an inline timestamp value.** It is **not** a
  separate SEL, **not** a new event kind, and **not** a nested SAD (reviewed 2026-06-25: nothing dereferences the
  clock by its own SAID — the manifest SAID commits the value directly, so a `{ timestamp }` wrapper bought only an
  extra fetch + hash-verify; both passes → direct). Every federation governance `Wit` — a **rotation** (§1a), optionally also a
  **membership change** — commits an **inline timestamp value as `manifest.clock`** (alongside `manifest.roster`), so **the
  timestamp lives in the data, never on a chain event** ([inv 4] role-grouped manifest, [inv 6] preserved). The
  `Wit` is **sealed** (terminal-on-divergence) and the timeline is **monotonic** (each `Wit`'s clock time ≥ the
  prior, enforced at the seal — can't be rolled back); the federation IEL is restricted to `Fcp`/`Wit`/`Trm` — the genesis `Fcp` and the **terminal `Trm` carry `manifest.clock` too** (the `Trm`'s clock ≥ the prior `Wit`; its `Ror`-revealed key-windows are clock-bounded and self-attest under the carve-out — so an all-windows-lapsed federation can still terminate).
  Consumers read the timeline by **walking the federation IEL they already walk for the roster** —
  reading each `Wit`'s `manifest.clock`. Witness key-windows change exactly at federation
  `Wit`s — **a rotation, optionally also a roster change (§1a)** — each carrying a clock timestamp, so timestamping
  them time-bounds every key's window (a retired key's `T_end` = its `Wit`'s clock time). `Wit`s are **rare** (§1a: ~yearly rotations, plus
  membership changes) — so the clock is cheap.
- **Receipt timestamps.** Each witness receipt carries the witness's asserted time (frequent, per-witnessing,
  self-asserted — individually untrusted). **A receipt's `τ` also gets a `≤ consumer-now + band` ceiling** (symmetric
  with the clock's F4 upper bound — cold-12 F5): a receipt claiming a future time beyond `now + band` is rejected /
  stale-flagged, so a forged receipt can't stamp ahead of real time.
- **The split — the clock bounds the receipts.** The clock (the `Wit`s' `manifest.clock` times) is the **sealed, trustworthy bound** (each key's
  validity window `[T_join, T_end]` in time); receipts are the **frequent values that get bounded.** **Load-bearing
  check:** a receipt counts only if its timestamp `τ ∈ [T_join(K) − band, T_end(K) + band]` per the clock. A
  harvested / rotated-out key (closed window) can therefore only validly stamp **old** receipts → a dormant forgery
  on it reads stale. Without this check the attacker just stamps "now"; with it, a closed-window key can't.
- **Staleness → fail-secure.** A consumer computes a tip's freshest *valid* witnessing time; an ancient one is
  **flagged stale** and not trusted for loss-of-trust / current-state decisions without fresh re-confirmation
  ([inv 8] / F-E). This is a **decision-time wall-clock** check, recomputed against current `now` on **every**
  loss-of-trust decision — **including the token-cache reuse path** (the effective-SAID gate certifies structure, not
  freshness; the 365-day auto-expiry is time-triggered, fires with no event — so the token caches the witnessing-*time*,
  never a `fresh` verdict — vdtid-services §1d / cold-12 F1). A forgery can't obtain fresh re-confirmation (current honest witnesses won't witness an old-context event). A
  legit *active* chain re-pins and is freshly witnessed → trusted; a legit *dormant* chain is also stale-flagged
  (correct — its owner re-activates by re-pinning to be trusted for current-state). The forgery gains nothing.
- **Tolerance band = 1 minute, a fixed protocol constant** (deterministic verification — every verifier agrees). It
  absorbs honest clock skew at a window boundary; its security cost is nil (the attack is *gross* staleness, not
  boundary-seconds). Distinct from the **staleness threshold** ("how old before flagged"), which is consumer /
  loss-of-trust policy (like the F8 bar).
- **Consumer clock sync — an operational requirement on the consumer (cold-13 F3).** Every consumer's staleness /
  at-risk / `clock ≤ now+band` (F4) / `receipt-τ ≤ now+band` (F5) check reads against the **consumer's own wall
  clock**. So a consumer **must stay synced (NTP) to within the `band` (1 minute)**; a consumer out of sync by **more
  than a minute can't trust its own freshness results** — it mis-judges window boundaries, and a backward skew is the
  fail-*open* direction (stale reads fresh, at-risk suppressed). This is on the consumer, not the framework (a
  verifier can't be defended against its own wrong clock). When the federation is reachable, **`evaluate_current`**
  (live challenge-response) is the **no-local-clock-trust** path.
- **Timestamp format:** **UTC, RFC3339, exactly 6 fractional digits (microseconds), fixed-width / zero-padded** so
  the manifest SAD canonicalizes byte-identically (JCS) — the same fixed-width rule whether the timestamp is inline or wrapped. The 6-place precision is for **deterministic serialization, not a
  claim of microsecond accuracy** — semantics stay coarse and skew-tolerant.
- **Rotation is via the federation-`Wit` channel only (F3, 2026-06-21; via `Wit` 2026-06-28; 'mandatory' clarified cold-9 C2).**
  'Mandatory' means a witness rotation is **legal only as a federation `Wit`** — **not** that every witness must rotate
  at every `Wit` (a synchronized all-witness rotation is the operational norm, not a hard per-`Wit` rule; a
  non-participating witness keeps its open key-window until it next participates). A key-window closes only at a federation `Wit`
  (the federation's only governance kind), so a witness rotation is **legal only as a synchronized federation
  `Wit`** (the witness's KEL `Wit` **is** the rotation and anchors the IEL `Wit` — no separate `Ror`) — an **off-ceremony `Ror`** (a witness `Ror` anchoring no `Wit`) on a witness KEL produces receipts the federation **does not honor** (the new
  key earns no pinned window; the old key's window is treated as closed at the most recent federation `Wit`), and an
  observed off-ceremony rotation is a **cut/eviction signal**. **Max-window auto-expiry — `MAX_WINDOW = 365 days` (cold-9 C2 / cold-10 F4, Jason 2026-06-29).** A key-window
  may stay open at most `MAX_WINDOW`: an un-refreshed window is treated as **closed at `T_join + 365 days`** (a fixed
  protocol constant, like the `band` — deterministic, every verifier agrees), **without** an explicit `cut`. So a
  witness that never participates in a `Wit` no longer keeps an *indefinitely* open key-window — it **auto-expires** at
  365 days and its later receipts read **stale**, the same closure a `cut` gives. This bounds **every** key-window to
  ≤ 365 days, so the never-rotated window collapses to the **ordinary `< threshold` current-key-compromise residual**
  (a key compromised *within* its ≤365-day window reads fresh, exactly like any active key — nothing special about a
  dormant one). **At-risk flag (cold-12 F2b):** a roster member whose window has **auto-expired** (quiet ≥ 365 days,
  not rotated or cut since) is **flagged at-risk** on the **verification token** — a **data-local computed** property
  (from the federation-IEL walk every verifier already does, vs wall-clock `now`; no new event/field — the shape of the
  staleness flag), **reported, not raised** (inv 9). It surfaces a *likely-lost* member so operators **evict-and-replace
  or reconfirm-by-rotation** before cumulative loss reaches `t_govern` (§1a). There is **no auto-eviction** (removing a
  member is governance — a `Wit` needing `t_govern` — which can't be auto-authored), so the flag is a *signal*; the
  structural effect (the expired window's receipts read stale) is what auto-expiry already gives. Operationally:
  **every witness rotates at least once a year** (standard practice; ML-DSA-87 handles the frequency easily). A slow-but-honest witness that lets its window lapse just reads stale until it rotates — no
  security cost, and the 365-day bound never bites a witness rotating with **margin** (rotate ~every 11 months, not riding the 365-day edge). **An *all-witness* lapse (a missed synchronized ceremony — every window expires together) is NOT a brick (cold-11):** the federation reads **stale** (fail-secure — loss-of-trust decisions refuse) until a **catch-up rotation `Wit`** lands, which **self-attests under the new windows it establishes** (§1e — the clock axis is carved out of no-self-weakening), restoring fresh witnessing. This **missed-ceremony** path (keys still held) is distinct from a **lost key** (can't rotate → evict-and-replace, or reincept+swap — §1a). A key's `T_end` between pins = the **next** federation
  governance event's clock time; the staleness check uses the **freshest valid clock time** as the upper reference. (Without
  this, an off-ceremony rotation would leave the retired key's window open and re-open the r4-F1 hole.)
- **Clock upper sanity bound (F4, 2026-06-21).** Monotonicity stops *rollback*, but the clock needs a ceiling too:
  a consumer **rejects / stale-flags any federation clock time beyond `consumer-now + band`.** Otherwise a
  compromised-but-unevicted federation **with `t_govern` members compromised** (setting the clock requires authoring a
  `Wit` — a *governance* act, so this is **beyond** the witnessing `< threshold` residual — cold-12 F3; the F4 guard is
  **defense-in-depth**, bounding an already-`t_govern`-compromised federation's blast radius to ~`band`) could
  **future-date** a `Wit`'s `manifest.clock` to push every key-window forward → closed windows read open →
  harvested-key forgeries read fresh.
  The consumer's own wall clock is the cheap external check; future-dating beyond `band` is prima facie suspect —
  bounding a clock-setting compromise's blast radius to ~`band`. (inv 14.)
- **Residual — detection is delayed by the staleness threshold (F5, 2026-06-21).** A forgery on a key whose window
  closed **within** the staleness threshold (a *recently* cut/rotated witness whose key an attacker harvested) can
  stamp `τ ≤ T_end` and read **fresh** until the threshold elapses past `T_end`. The position-`terminator` (dropped)
  had no time component; the clock is as strong for *forward-rotated* keys but has this time-granularity gap for a
  just-closed window. → use a **tight staleness threshold** on high-value bindings, and treat a **recent roster
  `cut`** as itself freshness-sensitive (demand extra-fresh confirmation near a recent cut). Composes with F4.
- **`terminator` — DROPPED (Finding 11, 2026-06-21).** The position-`terminator` was the hack standing in for the
  missing clock; with the clock the bound is **time** (a receipt counts only within a federation-pinned key-window —
  §1a). The federation roster `cut` is now `cut: Prefix[]`. *(The cut-a-chain mechanism survives only as the
  delegate rescission **`bound`**; the `terminator` name is fully retired — delegation §5.)*

## 2. Mined from kels-216 — patterns that carry (confirm in land)
- **Receipts indexed by `(prefix, serial)`**, *not* event SAID — structural; this is what lets **competing receipts
  at a position** aggregate into one detectable signal. *(kels' threshold-two-events — both branches at threshold —
  is under the majority floor precisely the impossible state for honest witnesses; it remains reachable only at
  fork-cost or for privileged siblings. Detection re-keys on competing receipts + fetched data — 2026-07-02.)*
- **Minority dissent** = sub-threshold receipts on a losing `witnessed_said`, attributable to specific members →
  a forensic signal for evicting a compromised member via a federation `Wit`.
- **Defense in depth — "the DB cannot be trusted":** receipts are *evidence*; the verifier **independently
  re-checks structural validity** of every `witnessed_said` it sees.
- **Single-rogue resilience:** a threshold-not-single-receipt bar stops one member from bricking a chain with a fake
  receipt; fakes don't resolve to structurally-valid events (kels named this threshold-two-events; the vdti signal is
  competing receipts + re-validation — above).

## 3. Superseded — do NOT carry forward
- **The self-*witnessing* carve-out** (`event-shape.md`'s IEL `Fcp` row's **v0 self-witnessing verifier
  dispatch** — witness-pool = the inception's own members) → **gone**; trust roots in the config-pinned prefix, and
  the genesis is cross-witnessed exclude-self once the mesh forms (federation-ref §4). *(Note: the **IEL `Fcp`
  kind** itself is **not** superseded — it **returns** as the federation IEL's inception **marker**, 2026-06-28
  (§inv 4 / federation-ref §2); the marker does interpretation, not trust. Only the self-witnessing **dispatch**
  stays dead.)*
- **`federationBinding` (single SAID)** → **`federation` (prefix) + `federationPin` (SAID)** split.
- **Fork-detect locality / "operator wins clean"** (kels' *original* spec) → dropped for **always-witness**
  (reliable, locally-determinable detection; operator recourse = reincept).
- **kels' federation-via-identity-policy** (federation composed from member identities via `identity()` policy
  leaves) → vdti roster = witness **KELs directly**, no policy [inv 1].
- **Design-pass §2.2 matrix** — the federation-inception cell becomes `Rot → IEL Fcp(federation)` (the `Fcp` marker, anchored by a founder **`Rot`**, kind-strict, T2 ↔ T2 — no founder `Fed`/`Wit`, 2026-06-28).

## 4. Open / route to the adversarial pass
- **Which vdti kinds get witnessed?** kels witnessed "privileged events"; vdti's taxonomy differs (`Ixn` diverges,
  rotations terminal-at-merge). Map kels' "privileged" onto vdti's kinds — likely **all chain-advancing /
  security-relevant events**, so federation-layer divergence is uniformly detectable. Doctrine-reconciliation
  detail, not a design blocker.
- **Receipt encoding** (the remaining mechanism detail): exact fields binding a receipt to (a) the event's
  `federationPin` context, (b) the signing witness's KEL position, and (c) the witness's **timestamp `τ`** — so the
  verifier resolves `witness ∈ select(prefix, serial, roster(F @ context), signers)` with the right key version and checks `τ` against that key's
  clock-window (§1f) — the receipt must bind the context so the selection is checkable (F3). **Hard requirement (round 4): `τ` is INSIDE the witness-signed payload** (alongside the
  `(prefix, serial)`, `witnessed_said`, and `federationPin`-context binding) — otherwise a harvested validly-signed
  receipt's `τ` is rewritable to "now" and the §1f clock check is moot. **The cut witness's key-range bound is the
  federation clock** (§1a/§1f) — a receipt from a cut witness counts only within a federation-pinned key-window
  (`τ ≤ T_end`); the position-`terminator` is dropped. Remaining detail: the exact field layout. Doctrine-reconciliation.
- **Federation `Trm` semantics** — terminating a federation: chains still bound to it must `Wit`-rebind or
  become unwitnessable. Confirm the intended consumer experience.
- **Per-witness address/discovery** — kels gives each witness a deterministic-prefix address SEL holding endpoints
  (discovery reads the roster, walks each peer's address SEL). **Infra concern, downstream of the primitive** —
  flag for the infra pass, not the primitive docs.

## 5. Drift → land backlog
- **Write `docs/design/federation/{bootstrap,witnessing}.md`** fresh from this note (genesis ceremony +
  the witnessing model). Reconcile `protocol-doctrine.md` §Federation and strip `event-shape.md`'s IEL `Fcp` row +
  self-signing carve-out + `federationBinding`.
- **Apply the design-pass §2.2 matrix fix** (federation inception = `Rot → IEL Fcp` (the marker); founder `Rot` anchor — kind-strict, T2 ↔ T2; no founder `Fed`/`Wit`, 2026-06-28).
- **`event-shape.md` KEL:** witness-config SAD `{ threshold, signers }` as the manifest **`witnesses`** role (shared with the KEL note's land item).
- Carry the witnessing mechanics (one-content-sibling-per-serial + privileged/repair always-witness · `(prefix,serial)`
  selection · the majority floor + fork-cost · competing-receipt detection · destruction-on-witnessing) into the vdti
  witnessing doctrine, in vdti kind language (kels-216's unconditional always-witness + threshold-two-events are
  superseded — §1e/§2).

## 6. Confidence / what's owed
- §1a–d (federation structure) — **high** (design-pass §7 + reference doc; Jason-confirmed Q1/Q3/Q4).
- §1e (witnessing) — **high** (kels-216 is detailed and was hardened over its own rounds; Jason confirmed it
  carries). The session-new pieces (restricted federation kind set; `signers` naming; exact-tip gate) are direct
  consequences, Jason-confirmed.
- §4 — the witnessed-kind mapping + receipt encoding are doctrine *detail*, not design blockers.
- Owed: the doctrine-land phase; the adversarial pass on §4; resolves the IEL note's "federation `Ath`?" open (no).
