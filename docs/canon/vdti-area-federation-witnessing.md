# vdti — area note: Federation & Witnessing

**Status: FIRST CUT (2026-06-20).** Federation = an ordinary (restricted) IEL; witnessing = as-of-context
**prevention for witnessed content + detection for everything else** (the witnessing floor, 2026-07-02 — content forks
are prevented on witnessed chains below fork-cost; sealed races and the byzantine residual are detected — every identity is federation-witnessed, there is no direct
mode, §1d), evolved from kels-216's detection-only model. Grounded in
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
  **superseded** by one-content-sibling-per-serial + the witnessing floor — §1e/§2, 2026-07-02.)*
- `../kels/.working/kels-214-doctrine-simplification.md` — the *federation-dispute* (no-`Cnt`) framing
  (already reflected; "contested" → "irreconcilable" → "disputed").
- `docs/design/protocol-doctrine.md` §Federation + `event-shape.md` are **reconciled to the reshape** — the
  landed docs carry the current `Fcp`-marker + `federation`/`federationPin` model, not the old
  `federationBinding` or the self-signing carve-out (§3). The remaining land targets are the `federation/` docs.
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
  carve-out; `Wit` = the federation's single governance kind — roster + rotation, T2, replacing `Evl`; 2026-06-28,
  cold-4 B1). A federation authors **no `Ixn`**
  (no content) → **every federation event is a key change → record-both**; a competing sealed sibling is first-seen-declined (exclude-self peer-witnessing), so an honest conflict does **not** dispute — only a witness-colluded `{Wit, Wit}` (two accepted) is `disputed` → reincept [inv 13]; and **no `Ath`** (trust is
  per-federation, non-transitive). Lifecycle: incept (`Fcp`) → all governance (add/remove a witness, rotate) via `Wit` → `Trm`. Its threshold-vector
  is **exactly `{t_govern}`** (+ Rule A for additions): no `Ixn`/`Ath` ⇒ no `t_use`/`t_authorize` (a threshold is declared iff its consuming kind is in the kind set — inv 12; a federation `Fcp` declaring either is malformed → rejected). *(There is no `t_recover` — no repair anywhere; tier ⊥ count (inv 11): the `Wit`'s **T2 tier** (each witness's KEL `Wit` refreshes the signing key + rotation reserve) is enforced **structurally** by the kind-strict KEL `Wit` ↔ IEL `Wit` anchor and gated by the **`t_govern`** count.)*
  **The recoverability ceiling `≤ |roster| − 1` is HARD for the federation** (unlike a general identity, where it's
  advisory — G1 / inv 12): the federation is critical infra and must always be able to evict **one** compromised
  witness and recover without it, so `|roster| ≥ 4` is **structurally required** — the `signers ≥ 3` witness-config floor (§4) plus the federation's exclude-self pool (`signers ≤ |roster| − 1`) forces `|roster| ≥ signers + 1 ≥ 4`; **≥ 5 recommended** (§1c). No fragile 1–3-witness federation. *(Surviving
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
  rotation: `Wit` anchors `Wit` (kind-strict, T2 ↔ T2, inv 4 — the governance-facet match is the **witness-config only**, Q3; the roster rides the manifest `Evl`-style, the `clock` is a single IEL-side value, monotonic + `≤ now+CLOCK_TOLERANCE_BAND`) — each participating witness
  authors a *single* KEL `Wit` that refreshes the signing key + rotation reserve **and** anchors the federation IEL `Wit`; no
  phantom key, and `pins = Wit.previous` so the retiring receipt key's `T_end` lands correctly
  (cold-4 B1).** **Add/remove a witness
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
  the whole list (this delta SAD is the **`manifest.roster`** role, inv 4). **`add` is a *single* prefix, not a list — one witness added per `Wit` (except inception `Fcp`, which stands up the founding roster wholesale) — cold-seam P5, 2026-07-02.** Both an operational match (standing up a witness is deliberate infra, never bulk) and a **structural closure of the multi-add straddle**: a governance `Wit` never introduces more than **one unsynced witness**, and one fresh witness alone cannot reach a majority `threshold` (`≥ 2` for `signers ≥ 2` — its co-selectees are synced and decline the fresh sibling by first-seen), so the benign multi-add straddle-enabler (two fresh witnesses co-signing from routine join latency) **collapses into the priced witness-compromise residual** (a fresh sibling now needs a *byzantine* synced co-signer) — and with `signers ≥ 3` (§4) there is no lone-witness degenerate to carve out. **`cut` stays a list** (cuts remove *synced* witnesses — no fresh-witness straddle — so emergency multi-eviction is unaffected; evict-and-replace is `cut: [..], add: one`). **Reachability property (VERIFIED, encode review 2026-07-02):** every valid target config is reached from a valid config by single-adds through valid intermediates — and stronger than hedged: a `Wit` carries `add` **and** `threshold` **and** `signers` in one event and the post-delta re-check runs against the **target** config, so any valid config at `|roster| = n+1` is reachable in **one** `Wit` from any valid config at `n`, no forced invalid intermediate (worked `{2,3}@4 → {3,4}@5`, from the `|roster| ≥ 4` floor). The only friction is the authoring step's self-attestation under the at-or-before config (no-self-weakening), which "usable" already guarantees (with `signers ≥ 3` there is no lone-witness position-luck case). The current roster is reconstructed by
  **accumulating add/cut while walking** (the live set is always in memory). A `cut` removes a witness **by
  prefix**; **which of its keys may still sign valid receipts is bounded by the federation clock** (§1f), not a
  position-`terminator` (**dropped 2026-06-21** — see below). *(The cut-a-chain primitive survives only as the
  **delegate rescission** `bound` — delegations have no clock — inv 13 / delegation §5; federation removal no
  longer shares it.)*
  - **Hard cap on the live set = `MAXIMUM_ROSTER_SIZE`** (first-seen, 2026-07-08 — the same cap as every user IEL, inv 12): while
    accumulating, if the live roster would exceed **32**, **reject the event as invalid** (a likely DoS /
    resource-exhaustion attempt). Bounds signature/threshold work + memory. *(Operator doctrine is ≥ 5 witnesses, so
    32 leaves ~6× headroom; the max federation shrank 4–8× from the old ≈128/256, intended — §L8.)*
  - **The live roster is a SET (cold-9 Q2):** a `Wit` whose `add` names an **already-live** prefix is **rejected** —
    re-adding a current member would reset its `T_join` (re-open its key-window); the set discipline removes that
    ambiguity (defense-in-depth; the `t_govern`/Rule-A double-count is already closed by the kind-split). **`add` membership is tested against the *pre-delta* roster** — so a same-event `cut` + `add` of the **same** prefix (`cut ∩ add ≠ ∅`) is rejected too (cutting `W1` then re-adding it with a fresh `T_join` in one event can't route around the set discipline by ordering); evict-and-replace (`cut W1`, `add W2`, disjoint) is unaffected — the rule is **order-independent** (cold-14 F1). A **config change**
    is **re-checked on the post-delta config** (inv 12 — on **any `Wit` that changes roster, `threshold`, or `signers`**, not a `cut` alone; for the federation, its `Wit`): valid
    only if the **full witness-config validity** holds after the change — the **recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)`** (a bare `cut` re-applies the roster leg; a `signers`/`threshold` change re-applies the tighter `signers − 1` leg — the leg that actually binds for `signers ≥ 2`, F-obs — so a `signers` drop `{s 4, t 3}@5 → {s 3, t 3}@5` that passes `|roster| ≥ threshold + 2` but violates `t ≤ min(3,2)` is **rejected**, cold-seam F1), the **witnessing floor `threshold > signers/2`**, and the `t_govern` bounds still hold. So a **bare `cut`** that would strand the federation un-recoverable —
    even one that passes the bare `≥ 4` structural floor (§4) (e.g. `|roster| 5→4` at `threshold 3`) — is **rejected**, forcing
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
- KEL keeps **`Fcp`** (federation-infrastructure inception, T1) + **`Wit`** (the one witness/federation kind, T2): on
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
  federation `Fcp` (roster = founder witness KELs) + the founder `Rot`s land as a **dependency-ordered bundle** (not all-or-nothing — a partial genesis is sub-threshold, fail-secure; revised 2026-07-14), point-to-point
  (a *coordinator* is an operational convention — no election/leader). The **clock is incepted in this same bundle**
  (the federation `Fcp`'s `manifest.clock` sets the founders' `T_join` = genesis time), so the timeline has a lower bound from event zero
  (Finding 6 — otherwise the pre-first-`Wit` window is unbounded).
- **Run `≥ 5` live witnesses, not the bare `≥ 4` structural floor (operator doctrine, Finding 3).** The hard floor counts *roster
  membership*, but a witness KEL can die **without a `Wit` cut** (lost key, destroyed device → can't rotate). At
  the `|roster| = 4` floor, two such silent deaths drop the *live* set below `t_govern` → the federation can't author the
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
  **per range, not per event** (bounded by the `Wit` count — `Wit`s are rare sealed acts; a **hard cap on
  `Wit`s/chain** rejects a ping-pong DoS, inv-14 pattern — over-cap → reincept). A consumer **must not** assume "has a
  `Wit` ⇒ all events witnessed" (cold-5 C1a; the rule applies to rebind chains — a run bound to a since-changed federation).
- **The migration window is cooperative-only (cold-4 B2).** *(This is **user-identity** rebind overlap — distinct
  from a witness serving two federations, which is **dropped**: witnesses are single-federation, §1a.)* The
  overlapping-federation trust that bridges a **user-identity** rebind
  (members below `t_govern` lagging on the old federation until they each rebind) assumes **both** federations are
  **honest** — a graceful, app-coordinated migration both approve. It does **not** cover *escaping a compromised
  federation*: there the old F still counts during the overlap, and an IEL event mid-migration can't be verified under
  the target federation alone (its lagging members are old-F-witnessed). **Escaping a compromised federation is a
  hard cutover / reincept, not a graceful overlap.** Multi-federation migration is **application-level** — the
  framework gives the per-federation primitives + recommendations, not an orchestrated protocol.
- **There is no direct mode (first-seen, 2026-07-08).** Every identity is **federation-witnessed** — witnessing is
  what every guarantee rests on. A user `Icp` **must** carry its `federation`/`federationPin` (a user `Icp` omitting
  them is malformed → rejected — inv 4); a chain **cannot** incept un-federated, and there is no "witnessing starts
  from a later `Wit`, early range unwitnessed" allowance. **Fail-secure (cold-5 C2):** a loss-of-trust decision that
  can't multi-source-confirm a `Trm` (any eclipse/single-source) **refuses**, never proceeds-with-a-flag. *(The `Fcp`
  federation-genesis bootstrap is **not** direct mode — the `Fcp` genesis is unwitnessed only because it is the
  config-pinned trust root, kept — §1a. The residual where a content fork can still form is a **witness compromise**,
  not an un-witnessed chain — §1e.)*
- **Multi-federation is out-of-scope-but-allowed** (the per-federation, non-transitive model **is** the whole
  allowance — no orchestration is designed). Multi-source *independence* is a **policy/app-layer** choice (`thr`/`and`;
  a consumer counts **distinct witness KELs**, not federations — document-policy R4).

### 1e. Witnessing — propagation of the divergence signal; the data detects (reframed 2026-06-23, supersedes "witnessing detects")
- **Receipts are adjacent attestation data** (unanchored), like a KEL's signatures.
- **Witnesses are reporters, not deciders** — they don't pick a canonical branch.
- **Content-fork prevention — the witnessing floor + one-content-sibling-per-serial (2026-07-02):** a selected witness
  signs the **first** structurally-valid **content** (tier-1 `Ixn`) event it sees at a `(prefix, serial)` and
  **declines any later content sibling** there (first-seen, per-serial). With the **witnessing floor `threshold >
  signers/2`** (§witness-config) two content siblings then **cannot both reach threshold** — their threshold-quorums
  share `2·threshold − signers ≥ 1` witnesses and that witness signed only one — so a **content divergence never forms
  on a witnessed chain**; it is **prevented, not detected**. This holds at **KEL positions and user-IEL positions**: a
  user-IEL content event is majority-witnessed **at its own position** — the fork-prevention gate alongside its
  anchor-based authorization (§witness-config / inv 12; **option (b)**, 2026-07-02) — and the **SEL is prevented at its own position too** (witnessed-SEL redesign, 2026-07-12, area-sel §1c — the "SEL rides the cross-layer theorem" claim is RETIRED: a SEL forks under a linear IEL, so it is majority-witnessed first-seen at its own `(SEL-prefix, serial)`, inheriting the owner IEL's federation). The **federation IEL authors no content** (so the content gate is moot); its **sealed** events are gated by exclude-self peer-witnessing (§1e) — a competing sealed sibling is declined first-seen, only witness collusion yields
  `disputed` (revised 2026-07-11). A content fork survives **only** where no majority gates it — a
  **witness compromise** owning the whole intersection (`≥ 2·threshold − signers` witnesses, the fork-cost), or —
  rarely — **across a roster delta** (two full quorums under disjoint contexts, zero double-signers — the F5
  straddle, §witness-config: under the propagation premise below it additionally requires the new selectees cut off
  from the already-propagated old quorum, so it is an entrance to the partition/eclipse residual, not a
  freestanding race).
- **Sealed: sign ONE sibling per position — first-seen, like content (revised 2026-07-11, cold F1; supersedes the
  2026-07-02 sign-up-to-TWO rule, which co-witnessed a signing-key thief's competing rotation and thereby handed
  tier-1 a durable deny):** a selected witness signs the **first** structurally-valid **sealed** sibling
  (`Rot`/`Wit`/`Trm` + IEL/SEL analogs) at a `(prefix, serial)` and **declines every later sealing sibling** there —
  the same first-seen rule content follows. (It may still hold `{≤ 1 content, ≤ 1 sealed}` at a position — the
  cross-tier co-sign the split-stall exit needs, §witness-config.) A **second sealed receipt from one witness at one
  position is cryptographic proof of that witness's misbehavior** (the sealed twin of the one-content-sibling rule).
  So a competing sealed sibling reaches `threshold` only if `≥ 2·threshold − signers` selected witnesses
  **double-sign** — the sealed fork now carries the **same fork-cost as a content fork**: a **both-witnessed** sealed
  pair is itself proof the witnesses colluded (provable → eviction), while a **witness-declined** sealed sibling is
  **deferred-pending, non-propagating, droppable** (a spent-preimage or partition race — no witness fault). The
  `disputed` verdict is unchanged and rides the **data-local walk over *accepted* branches** (inv 13/17 — receipts
  attribute, they do not decide; an unwitnessed sibling a node merely holds is not an accepted branch). On a
  content-only divergence the resolving burying seal-advancer (a `Rot`/`Evl`) is that **one** witnessed sealing event;
  a *second* witnessed seal-advancer is the proving pair `{Rot, Rot}` (or `{Evl, Evl}`) → `disputed`, now necessarily
  collusion. So **divergence detection is now sealed-only** (content is prevented upstream). **Residual** content-fork
  evidence (the witness-compromise residual) is still retention-bounded at **≥ 2 per position** (the content analog of
  inv 17's sealed **≥ 2-per-spine-position** — "two prove the fork, then stop"), depth ≤ `MAXIMUM_UNSEALED_RUN` per lineage (the
  seal-cap); a witness holding the burying seal-advancer declines to re-witness dead content (efficiency only — deadness ascends
  regardless).
- **The split/tie stall + its exit (warm F3):** one-content-sibling-per-serial partitions the receipts at a forked
  position (`a + b ≤ signers`); if neither content sibling reaches majority (an even-`signers` tie, or
  abstentions / a partition) the **position stalls, fail-secure** — signed witnesses cannot switch. A **minority
  partition therefore stalls, never forks** (consistency over availability — the CP corner of the floor). The **exit
  is a burying seal-advancer**: a `Rot`/`Evl` at the position is sealed — the first sealed sibling there, signed by every
  selected witness under the one-sealing rule above — the cross-tier co-sign (a content signer may also sign this one sealing event) — and reaches
  majority. Attached at the author's own stalled sibling it **retains** that branch (the witnessed seal commits it
  as `previous` — local progress below) and the competing sibling closes below the seal; attached at the shared
  ancestor (the author authored neither) it buries both — the losing roots close below the new seal, dead on ascent,
  no `fork` role (inv 4 / inv 17). Content-only → permitted; stalled honest content re-issues forward. **Odd
  `signers` avoids the pure tie** (operator guidance): with every selected witness voting, an odd set always yields a
  strict majority for one sibling — the stall then needs abstentions, not just a race.
- **Propagation premise (stated 2026-07-02, Jason — load-bearing for prevention, never for safety):** once an event
  is **witnessed in full**, prompt roster-wide propagation is assumed (the push-gossip mesh), barring a partition —
  a roster member ordinarily sees a completed quorum before any later sibling arrives, which is what arms the
  first-seen declines above (a newly-selected witness declines a sibling at a position it has already seen taken).
  The premise carries the prevention layer's **success rate** and detection **latency** only — **safety never rests
  on it**: a fork that forms despite it lands in freeze → burying-seal recovery (inv 13), and nothing false becomes canonical on
  any node. Without the premise the prevention leg falls apart; with it, the F5 roster-delta straddle requires the
  new selectees to have been **cut off from the already-propagated old quorum** — an entrance to the
  partition/eclipse residual, not a freestanding race. **The *benign* multi-add case is structurally closed
  (cold-seam P5, §1a):** `add` is one witness per `Wit`, so a transition never yields ≥ 2 fresh unsynced
  selectees co-signing from routine join latency — one fresh witness can't reach a majority `threshold`
  against synced co-selectees who decline by first-seen, so the straddle now needs a *byzantine* synced
  witness (the priced witness-compromise residual) — with `signers ≥ 3` there is no lone-witness degenerate. So the residual is genuinely just partition/eclipse + witness-compromise, no benign
  race. **Rejected — the cold-F5 "prior-context receipt"
  hardening** (a witness declines a position for which it holds a threshold-real receipt set under any
  *prior* roster context): it is the **same trust class** as first-seen (witness behavior, honest-majority
  priced, unverifiable from chain data — not a structural rule), it only closes the *informed* half of the
  straddle (the new selectees must already hold the old quorum's receipts — which under this premise they
  hold *anyway*, so first-seen already declines), and it puts cross-context historical verification in the
  witnessing hot path. The straddle is a recoverable content fork (freeze → one burying seal); the honest fix is
  the per-context marker scoping above, not more witness machinery.
- **Dead-event gate (garbage reduction, 2026-07-01):** a witness that **already holds the burying seal-advancer** (a `Rot`/`Evl`)
  that condemned a fork **declines to witness** dead **content** events on a **dead** branch — one whose ancestry passes
  below the burying seal or through a below-seal fork. **A below-seal sealed event is declined too** — the witness **mirrors the seal-cap** (a parent below the tracked seal is inert, content _or_ sealed; revised 2026-07-11): it never reaches threshold, so it is neither dispute evidence nor able to retreat the clean seal. **The sealed leg is load-bearing — the backdate defense:** a below-seal sealed straggler must **not** be witnessed, or a total-key-compromise adversary could mint a fabricated historical fork years after the fact; the only reachable dispute is a **seal-vs-seal collision at the last (live) seal** (two accepted seals there, a provable witness double-sign). **The gate generalizes — you can't seal a buried chain (dead-on-ascent, Jason 2026-07-11):** a lineage is dead from its **first-seen loss** at any position, not only below a burying seal. A selected witness that first-seen-accepted the winner at a fork **declines every descendant of the loser — content _or_ a `Rot`/`Evl` seal forged on it** — so a buried branch never gathers the majority a seal needs; a seal does not revive it. This is what **collapses a dispute to the fork** (inv 13): two branches both **accepted** at a seal share their lineage to a fork where **both** siblings are accepted — a same-position double-sign — so no **cross-position** dispute forms. **The content leg is an efficiency gate, not load-bearing:** deadness ascends
  (inv 13 — an event whose parent is dead is dead), so a dead event that a lagging witness signs before it holds the
  burying seal is still **retained (keep-all-data) and dead-on-ascent**, never canonical. It just keeps witnesses from
  amplifying a signing-key adversary's dead content — the one-content-sibling rule + retention above are the primary bounds (breadth ≥ 2-per-position, depth ≤ `MAXIMUM_UNSEALED_RUN` per lineage; inv 4 / inv 13); this is their post-burial complement for a lagging witness.
- **Deterministic selection by `(prefix, serial)` + sub-mesh event-gossip (2026-06-23):** competing events at a
  position route to the **same** selected witness set (so the quorum-intersection is over **one** set), and the
  selected witnesses **sub-gossip the event among themselves**. **Sub-threshold events are witness-scoped
  (query-scoping, Jason 2026-07-11):** a **not-yet-witnessed** event (below threshold — living on the selected
  witnesses' sub-gossip mesh while it gathers receipts) is returned by a query **only to a selected witness** for
  that position; to everyone else — a non-witness, or a witness not selected here — it is **noise, not returned**. So
  **non-witnesses only ever hold witnessed-in-full events** (deferred-pending is a **witness-only** state), and an
  attacker cannot feed a sub-threshold competing event to a non-witness to skew its reading — the only competing
  branch that reaches it is a genuine witnessed-in-full (collusion) one. **An opt-in audit query is the exception
  (Jason 2026-07-11):** a non-default `all-data` flag returns **every event and receipt the node holds** — sub-threshold
  noise included — in line with keep-all-data. It is **walk-ignored** (a sub-threshold event never enters the verdict,
  so surfacing it cannot skew a reading); its value is **forensic** — a suppressed competing sibling is evidence of an
  *injection / collusion attempt*, so the flag makes attack-attempt detection **possible** (it requires an auditor to
  interpret, but it makes it possible). The default stays scoped. A receipt counts toward an event's threshold
  **only if its signer ∈ `select(prefix, serial, …)`** — the *selected* set, not merely `roster(F @ context)` (F3,
  2026-07-02; the intersection guarantee is over the selection, so the counting predicate must be selection-scoped).
  **Receipt-encoded threshold — exact-match (§2b, hardening thread; ⚠ NOT previously design-reviewed — this is the
  encode-reviewer's first decorrelated pass):** each receipt also **carries the witness-config `threshold`**, so
  witnessed-detection is a receipt count — count `threshold`-many agreeing on `(event SAID, threshold)`, **no
  chain-walk to resolve the in-effect threshold** (the detecting witness already holds the live roster as mesh
  state, so the receipt saves the *in-effect-threshold walk* specifically — **not** the roster/selection, still
  needed to know a receipt is from a selected witness). **The count is load-bearing on an exact match against the
  chain-authoritative committed witness-config SAD in effect at that position** (committed at-or-before the serial —
  position-deterministic), **never the self-asserted receipt field**: a mismatch is **invalid even if higher** (a
  low bar under-counts a forgery; a high bar is a faithfulness + liveness/DoS failure and disagrees with honest
  receipts on `(SAID, threshold)` → detected; the consistent lie — event and receipts both understate — is defeated
  because the match is against the committed SAD, not the field). A **stale-config** witness (lagging a governance
  `Wit`) emits a non-matching receipt → **discarded** (a liveness cost around config changes, not a safety hole);
  composes with the key-window gate (§1a/§1f) — a valid receipt needs {valid sig, inside key-window,
  threshold-matches}. *Witnessed*-detection (is it backed?) stays distinct from *disputed*-detection (data-local,
  ≥ 2 sealed branches) — they compose: the receipt-threshold makes "should I pull?" cheap, disputed stays a
  data-local re-validation. *(The value-scope point is **resolved** in vdtid-services §1k — the fast receipt-count is
  a hint; the committed-config match on pull is authoritative.)* For a
  **sealed** event, sub-gossip means it reaches every selected witness → **no stable "witnessed but sub-threshold"
  state** (the only ways to hold it sub-threshold are pure eclipse or a byzantine witness signing-then-withholding, a
  rogue phantom receipt → discard + evict, bounded by `< T`); the **first** sealed sibling reaches threshold this way,
  a **second** is **declined** by honest witnesses (first-seen, one-per-position — revised 2026-07-11, cold F1), so
  two *accepted* sealed branches → `disputed` require `≥ 2·threshold − signers` colluding double-signers (provable → evict). For
  **content**, first-seen-one-per-serial + the witnessing floor mean a competing content
  sibling **does not** reach threshold — the fork is prevented, so there is no sub-threshold content state to
  reconcile. **For a federation member's own KEL events** (a witness's `Wit`/`Rot`/etc.): the same algorithm with
  **that witness's own prefix removed** (exclude-self — a witness never receipts its own event), select from
  `roster − {self}` seeded by `(prefix, serial)` → pool `|roster| − 1` (Q1). *(The federation **IEL** `Wit` **realizes
  the position gate through exclude-self peer-witnessing** (revised 2026-07-11): a governance event needs a **peer
  majority first-seen at its serial**, so a competing sibling — content _or_ sealed — is declined. The gate is
  **universal** — every event, every witnessed chain — the federation just realizes it through its own roster peers
  rather than a distinct external witness set; the **user IEL** gates via option (b), §witness-config. So an
  all-witness federation rotation never bricks.)*
- **ALL inter-node mesh traffic is ENCRYPTED (2026-06-23, generalized from receipt-gossip-only):** ML-KEM-1024 KEM +
  AES-256-GCM AEAD — receipts AND the events they propagate. Confidentiality, not trust (trust is end-verifiable).
  The mesh = the federation roster, so mesh contents stay within the federation. **REVISED (witnessed-SEL redesign, 2026-07-12, area-sel §1c): the SEL IS witnessed, so a lookup-SEL
  prefix DOES ride a receipt** (as `chain_prefix`) — the `issuer ↔ private-subject` correlation is **not**
  "closed at the source" but **downgraded** to **confirm-a-known-subject** over the **encrypted** mesh (an
  unguessable prefix, exposed only to semi-trusted `< threshold` infra; the exfiltration-during-a-compromise
  -window residual, inv 16). `cred.said` still **never** enters a receipt: the cred is anchored as its
  issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` in an IEL `Ixn`'s opaque
  `anchors[]` (cred = anchored SAD, no cred-SEL; `cred.said` never raw, never on a witness), so what a SEL
  receipt carries is the lookup-SEL's own (unguessable) `chain_prefix`. The residual receipt prefix is
  therefore a public **IEL/KEL identity** prefix **or** an unguessable lookup-SEL prefix (§1g Decision 2),
  both route-metadata fine under the trust model. The AEAD nonce/key-scope discipline is now specified
  in `docs/design/substrate/infrastructure/mesh-transport.md` (per-connection session keys + a
  per-direction monotonic counter → nonce reuse is structural, not an implementer's discipline).
  **Push over pull (Jason):** prefer gossiping events to a separate inter-node *query* — the sub-mesh event-gossip
  already pushes competing events to selected witnesses; extend it so a one-branch holder gets the branches by push,
  so there's no second channel to secure (the residual by-prefix fetch shrinks, rides the same encrypted mesh). Build
  detail → `vdti-implementation-notes.md`.
  **⚠ RESOLVED (Jason 2026-06-26):** the encryption **public key lives in a SEL** owned by a **degenerate per-device
  IEL** — a single-member IEL (`members = [the witness device KEL]`), **derivable from the KEL prefix** (+ a purpose
  discriminator). It's a **restricted IEL** whose kind set **excludes `Evl`**, and the general **post-delta `|roster| ≥ 1`** rule (inv 12) forbids cutting the
  sole member (a lone-member `cut` would compute `1 + 0 − 1 = 0`, rejected — and with no `Evl` there is no kind to carry a `cut` regardless), so — with no `Evl` to grow — its roster is
  **immutable** (a general rule, not a federation-member special case); no new "immutable" manifest field, and
  `t_govern` stays mandatory (singleton exception → all thresholds = 1). Kind set ≈ `{Icp, Ixn, Trm}`.
  **It does NOT break the `Fcp` bootstrap** — the IEL is *derived*, not separately incepted: the device KEL exists
  first (`Fcp`) → its degenerate IEL derives → it owns the key SEL; "reincept" = re-derive from the recovered KEL
  (the KEL carries the rotation/recovery story). Discovery: federation roster → witness KEL prefixes → derive each
  degenerate IEL → its key SEL.
- **Receipts ENUMERATE the branches; the data decides (reframed 2026-06-23; re-keyed post-floor 2026-07-02):**
  competing receipts at a position list the branches a verifier must gather — but **terminality is a data-local
  branch-level walk** (inv 13 / 17: ≥ 2 branches each with a sealed event past the fork, over **retained**
  branches), **not** a receipt count. **_Witnessed_ (= accepted) is threshold, and it is
  distinct from the first-seen-decline trigger — two different predicates, do not conflate them (Jason 2026-07-11;
  corrects the earlier "signed-it-itself = witnessed" framing):** **acceptance** is a per-node judgment — an event
  is _witnessed_ / accepted to a node when the node holds **threshold-many valid receipts** for it (a selected
  witness's own receipt counts as **one** of the threshold, never a shortcut past it); threshold-only, for witness
  and non-witness alike; this is the acceptance / position gate and the verdict-counting predicate.
  **First-seen-decline** is the separate signing discipline: a selected witness declines to sign a sibling at a
  position when it has **already signed** there **or** the position is **already witnessed at threshold** (by
  anyone) — it bounds only the witness's own next signature, confers acceptance on nothing. A witness that has
  signed a **still-sub-threshold** event holds it **deferred** — it knows the event structurally valid (direct
  evidence: it re-checked before signing) and has spent its first-seen vote, but the event is **not accepted** until
  threshold, the **same held-state a non-witness holds a sub-threshold event in**: a witness's own signature is
  **admits-valid / commits-first-seen**, never accepted-as-canonical. The **FORCE rule splits by provenance (revised 2026-07-11):** a node that holds two or more
  **witnessed** sealed branches **at the last clean seal** forces `disputed` from the data — the walk decides, no
  re-tally. A **below-seal** sealed straggler is **dropped** (inert — it does not retreat the clean seal, the
  backdate defense); a sealed event a node holds only as a **receipt** it hasn't fetched, or that is **not yet
  witnessed** (below threshold — a witness-declined sibling), is **deferred-pending**, never counted (below
  threshold a rogue's receipt on a fake event is inert — the verifier re-checks validity). For **content** the
  signal re-derives (F1-consequence): a losing content sibling **never reaches threshold** under the floor, so
  waiting for threshold on it means waiting forever — the anomaly signal is a **sub-threshold competing receipt set
  at a position**, which *enumerates* → fetch the event (push/beacon) → the data-local walk decides; threshold
  authenticates only the *winning* branch. Receipts say *forked*; the data-local walk says *disputed*. Divergence
  stays **locally determinable on every node** (no watcher infra) — a first-class, queryable chain state — a
  **sealed** fork is **detected** once the branches reach a verifier; a **content** fork on a witnessed chain is
  **prevented** upstream (§1e), detected the same way in the residual.
- **Witness-config SAD** (the manifest **`witnesses`** role, inv 4) `{ said, threshold, signers }` on `Icp`/`Wit`
  (KEL **and** user IEL; the **federation IEL** carries its own on `Fcp`/`Wit`, adjusted each governance `Wit` — D1 /
  cold-7 F1, below), **mandatory iff federated** (else fail-secure reject — cold-7 F3): **`threshold`** = valid
  receipts required for **consumer trust** — app/operator choice **by chain criticality, above a structural witnessing floor `threshold > signers/2`** (a strict majority of the *selected* witnesses — two threshold-quorums **within one roster context** share `2·threshold − signers ≥ 1` witnesses, and an honest witness signs at most one **content** sibling per serial, so **two conflicting content siblings can never both be witnessed** (sealed siblings are also first-seen now — one per position; a durable sealed fork needs the same `2·threshold − signers` colluding double-signers, provable → `disputed` via the data-local walk — §1e) → no partition / disjoint-sub-quorum **content** fork; manufacturing a content fork costs owning the whole intersection, **fork-cost = `2·threshold − signers`** (the floor: the colluder count slides `threshold − k` for `k` honest witnesses an attacker can partition onto the rival — from a full `threshold` with no partition down to `2·threshold − signers` at a full partition of the `signers − threshold` redundancy) — a priced, tunable security parameter, not a free consequence of the network (the dial trades against availability: `fork-cost = threshold − slack` where `slack = signers − threshold`, so fork resistance and receipt redundancy trade one-for-one — at `threshold = signers` fork-cost is maximal but one unreachable witness stalls the position; and the one-content-sibling **violation is attributable** — two receipts by one witness over **two distinct *content* `witnessed_said`s** at one position (or a **second** distinct sealed sibling — sealed is now one-per-position too) are cryptographic proof of misbehavior → the minority-dissent forensics → eviction, so paying fork-cost means owning *and exposing* the intersection — warm F7. **The predicate is tier-scoped (cold-2 F1):** an honest witness legitimately holds `{≤ 1 content} ∪ {≤ 1 sealed}` at a position — the mandated **cross-tier co-sign** (a content sibling **and** the resolving burying seal-advancer, when the seal attaches at the shared ancestor — split-stall exit above; or any `{Evl/Rev/Dth, content}` recoverable fork) is **not** misbehavior and must be excluded by construction, else the forensics would evict the honest witnesses the split-stall exit requires and muddy the clean attribution the fork-cost pricing rests on). **The intersection rests on the selection-input rule (warm F4):** selection is a function of **`(prefix, serial)` over the current roster membership only** — never the event's bytes or its pin — and the **currency gate** (below) pins the membership input (a stale-membership pin earns zero countable receipts), so an adversary cannot mint sibling-specific witness sets. **Across a roster delta the two quorums need not intersect (F5):** receipts are durable and judged as-of their own pin, so a sibling witnessed-in-full under the old membership + a fresh-pin sibling under the new can hold disjoint quorums with zero double-signers — a **residual** = a roster delta × a propagation failure (under the propagation premise, §1e, the new selectees have ordinarily seen the old quorum and first-seen declines the fresh sibling) — the partition/eclipse family's entrance, not a freestanding race; detection unaffected (the branches still collide and freeze on co-observation); so witnessed-in-full is a **per-context** uniqueness certificate, not an absolute one); **`signers`** (M ≥ threshold) = witnesses **selected per event**, over-provisioned for redundancy
  (M − threshold receipts can fail and the event stays trusted). Bounds `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|` (lower bound = the witnessing floor above). (this `|roster(F @ context)|` bound is the **user/KEL** chain's, external witnesses; the **federation IEL** is tighter — `threshold ≤ min(|roster| − 2, signers − 1)`, the recoverability cap below / cold-9 B1 + F6.) **Orthogonal** to the federation's own `t_govern` (Q3): that governs F's roster changes; this governs
  a member's receipt-gathering. (`signers` = kels `witness_selection_size`, renamed this session.) **Per-layer (D1, 2026-06-28):** a **KEL** carries its own config (for its KEL events); a **user IEL** carries its **own authoritative** config (for IEL events — an IEL event is witnessed and could otherwise fork without any member KEL forking, two disjoint sub-quorums each authoring a valid event at one position — closed by the option-(b) gate below, now **universal** (every event, content _and_ sealed; revised 2026-07-11) — a competing sealed sibling is declined first-seen too, only witness collusion yields `disputed` — so it needs its own), **independent** of member configs (not matched — different chains' events); the **federation IEL** carries its own (cold-7 F1); a **SEL inherits** its owner IEL's (single-owner). On `Icp`/`Wit` (user/KEL) or `Fcp`/`Wit` (federation IEL). **Q1 RESOLVED (Jason 2026-06-29) — self-attestation:** an IEL has no key of its own (it is a threshold over member KELs), so an IEL event's witnessing **is** the witnessing of its **member KEL anchors** — the event is trusted when a threshold of its anchoring KEL events are witnessed (this config's `threshold`/`signers` set that bar). IEL events propagate + earn receipts **as per usual**. **Authorization** stays the witnessed KEL anchors (Q1); **fork-prevention** adds a second gate — **option (b), 2026-07-02, universalized 2026-07-11: a *user* IEL's events — content _and_ sealed — must also reach a majority quorum at their own `(IEL prefix, serial)`** (the same first-seen position gate as a KEL — §1e), so two disjoint member sub-quorums can't both land an event at one IEL serial; a competing sealed sibling (`{Evl, Evl}`, …) is declined first-seen too, so an honest split can't diverge — only a witness-colluded double-sign yields `disputed`. The **federation IEL realizes the position gate through exclude-self peer-witnessing** (a governance event needs a peer majority first-seen at its serial → a competing sibling declined): its member witness-KELs witness **each other's** KEL events **exclude-self** (a witness never receipts its own), pool **`|roster| − 1`** — so for federation member events `signers/2 < threshold ≤ min(|roster| − 2, signers − 1)` (the witnessing floor **and** the **recoverability cap** — below) and `threshold ≤ signers ≤ |roster| − 1` (a user chain stays `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|`, external witnesses). **The quantifier (cold-9 Q1):** the IEL `Wit` is trusted when the **`t_govern`** member KEL `Wit`s that anchor it are **each** witnessed at the witness-config `threshold` — two distinct counts (`t_govern` = how many anchoring KEL `Wit`s; the witness-config `threshold` = receipts per anchor) — and the anchors counted are only those witnessed **consistently with the IEL `Wit`'s own at-or-before context** — for a **user** IEL its `federationPin` context, for the **federation** IEL its own position on the federation chain (which carries **no** `federationPin` — that's a user/SEL binding field, forbidden on the `Fcp`-rooted chain; the no-self-weakening rule already pins it — cold-10 F3) — or freshly, for a loss-of-trust read; so a stale-context KEL anchor (from an old roster where a since-cut witness still counted) can't self-attest a current-context IEL `Wit`. **Recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)` (cold-9 B1 + F6, verifier-rejects higher):** an eviction/recovery `Wit` is authored by the remaining members **and must self-attest** — the evicted/dead member won't co-witness, so the self-attest pool is `|roster| − 2`, and at **sub-pool selection** (`signers < |roster|`) the *selected* pool loses one too, so `threshold ≤ signers − 1` also binds (the `|roster| − 2` cap is exact only at full-pool selection — worked `{signers 3, threshold 3} @ |roster| 5` passes `≤ |roster| − 2` yet can't self-attest the eviction). With `signers ≥ 3` (§4) the `signers − 1` leg is `≥ 2` — it always binds cleanly (no waiver, no `threshold ≤ 0` degenerate, no floor-bump concern) — and the **guaranteed** evict-one begins at the `|roster| = 4` structural floor `{threshold 2, signers 3}` (full-pool: the dead member's absence still leaves `threshold = 2` receipts). *(Composition — the two legs never conflict, warm F-obs: for `signers ≥ 3`, `threshold ≤ signers − 1` together with `signers ≤ |roster| − 1` already gives `threshold ≤ |roster| − 2`, so the `signers − 1` leg is always the tighter one and the `min`'s roster leg is always slack.)* Capping `threshold` there (the direct analog of `t_govern`'s gratuitous-hostage rejection, inv 12) guarantees the federation can always evict **one** compromised witness and get the cut trusted. **General form (cold-10 F1):** self-attesting a governance `Wit` with `k` members unavailable needs `threshold ≤ |roster| − 1 − k` (each remaining author's KEL `Wit` is witnessed by the *other* available members, exclude-self → `|roster| − k − 1` receipts). The **hard cap is `|roster| − 2`** (`k = 1`, the *evict-one* guarantee); surviving `k > 1` simultaneous losses is the **operator's sizing choice** — choose the **tolerated simultaneous-loss count `k`** explicitly (an operator parameter, not buried in doctrine; cold-11), then set `threshold ≤ |roster| − 1 − k` and grow the roster to keep `t_govern` reachable too (§1c). At the `|roster| = 4` structural floor the minimal config is **`{threshold 2, signers 3}`** (fork-cost `2·2 − 3 = 1`); `signers ≥ 3` gives real witnessing byzantine-tolerance — there is no forced lone-witness. The operator doctrine is nonetheless **run `≥ 5`** (§1c), where `threshold` rises to lift the fork-cost dial — and the **config-time warn family covers every fork-cost-1 config** (`signers = 2·threshold − 1`, the minimal majority — F11/cold-F4): deterministic selection makes a thin intersection a **precomputable target** — an attacker can enumerate in advance exactly which witness(es) gate a given `(prefix, serial)` — so a fork-cost-1 config is warned (not a free choice — analogous to the 2-device-identity warn-not-reject, inv 12; cold-11). **The rule (Jason 2026-06-29):** the verifier **rejects only *un-usable* configs** — a hostage `t_govern = |roster|`, a can't-self-attest `threshold > min(|roster| − 2, signers − 1)` (**both** cap legs — the `signers − 1` leg is the binding one for `signers ≥ 3`, cold-seam F1), a **sub-majority `threshold ≤ signers/2`** (it re-opens the disjoint-sub-quorum fork the witnessing floor closes — witness-config bullet above), a **sub-`signers ≥ 3`** witness pool (byzantine tolerance), a sub-`≥ 4` federation roster (for the spine, *un-recoverable* counts as un-usable) — where **un-usable = cannot function, or cannot deliver the semantics the witnessed-in-full marker asserts** (F10: a sub-majority config *functions* — receipts flow, propagation + data-local detection work — but its marker no longer means per-position exclusivity, a consumer footgun; the intentional casualty is detection-only low-`threshold`/high-`signers` configs, e.g. `{3, 10}` for latency) — and **allows any *usable* config, warning of the consequences** (every config clears `signers ≥ 3` + the witnessing floor + the recoverability cap; a fork-cost-1 config is the warned minimum — cold-12 F4). The structural **floor is `|roster| ≥ 4`** (`≥ 5` recommended — a consequence of `signers ≥ 3`, §4); a `cut` is **re-checked on the post-delta config** (inv 12 — on any `Wit` changing roster, `threshold`, or `signers`) — valid only if the **full cap `threshold ≤ min(|roster| − 2, signers − 1)`** **and the witnessing floor `threshold > signers/2`** both hold after the change, so a bare shrink that would strand the federation un-recoverable (`|roster| 5→4` at `threshold 3`) **or a `signers`-drop landing on the binding leg** (`{s 4, t 3}@5 → {s 3, t 3}@5`, cold-seam F1) is rejected, forcing **evict-and-replace** or a threshold-and-`signers` drop, §1a (cold-13 F1). A **`Wit`'s own self-attestation is judged under the at-or-before witness-config + roster** (no self-weakening — a sub-quorum can't lower its own trust bar or pad its pool in the very event whose trust is in question), **but under the NEW key-windows the rotation establishes** — the fresh keys its anchoring KEL `Wit`s reveal (`T_join` = the rotation's own clock, F4-bounded), **not** the possibly-expired at-or-before windows (**the clock axis is carved out of no-self-weakening — cold-11**; judging a rotation's fresh-key receipts under expired old windows is a category error and would brick the federation on a single missed annual ceremony). So an **all-windows-lapsed federation reads stale (fail-secure), then recovers via a catch-up rotation** that self-attests under its new windows — stale-but-recoverable, never bricked. This does **not** let a lone broken/old key mint a current window: a witness rotation is honored **only** as a federation `Wit`, needing `t_govern` authors **and** `threshold` self-attestation — one key reaches neither (a current-window takeover needs `≥ t_govern` keys = the byzantine assumption violated → reincept; a *lost* key is evicted/reincepted operationally, §1a). The federation `Wit` thus **never bricks** even when every witness participates (its trust rides its cross-witnessed exclude-self KEL anchors, not an exclude-all-participants aggregate). Divergence stays data-local: a `Wit` fork's competing branches are anchored by witnessed KEL `Wit`s that propagate, surfaced by the keep-all-data walk. *(Supersedes the round-8-draft `|roster| − |participants|` aggregate-gate — it bricked an all-witness rotation; cold-8 F1.)*
- **As-of-context evaluation (durability):** a receipt counts iff its signer ∈ **`select(prefix, serial, roster(F @ federationPin), signers)`**
  — the deterministic selection derived over the as-of roster (the selection-scoped predicate, F3 — §1e above; **`select` is a cross-node protocol constant — every conforming node must compute the *identical* selected set (receipt-counting and the fork-cost math rest on it), so its exact algorithm (a fixed, deterministic hash-to-index scheme over `(prefix, serial)` + roster membership) is pinned byte-exactly by the reference lib / at the encode, not left to the implementation — SS-1; independent re-implementations must match it exactly**), the pin being the most-recent `Icp`/`Wit` at-or-before the event (an **IEL** event uses the identity's **own** authoritative `Wit`/`Icp` binding, never an individual member KEL anchor; a **SEL** inherits its owner IEL's — cold-3 B2),
  forward-floored on the KEL. **Never at F's current tip.** F and witness KELs are append-only, so an event stays
  witnessed **forever** — **no re-witnessing** of historical data.
- **Acceptance-time currency gate — exact-tip, NO grace window (reviewed 2026-06-24; `graceSeconds` dropped).** *(This gate is a **user/SEL-chain** mechanism — the **federation IEL itself carries no `federationPin`** (F3), so it does not apply to the federation chain; the federation's own freshness is its clock + the 365-day auto-expiry, §1f — cold-11.)*
  Witnesses refuse to witness an event whose `federationPin`'s **roster (membership)** isn't current, forcing an
  active chain to advance `federationPin` by carrying a fresh one on its **next event of any kind** (no `Wit` needed — `federationPin` is optional on every event, 2026-06-25) — **lazily, on next activity**. **The gate compares
  roster MEMBERSHIP, so it fires on a *cut* (a witness removed), NOT on a pure rotation-pin** (same witnesses, new
  keys — the clock §1f bounds key time-validity, so a pre-rotation pin is safe). This bounds the re-pin to **rare cuts**, not every rotation — and the re-pin is **cheap** now (it rides any event; a `Wit` (T2) is needed only to *rebind*, or when a cut shrinks the roster below the chain's `signers`). **No grace window:** a since-cut witness earns **zero**
  countable receipts immediately — any `graceSeconds > 0` would re-admit the pre-cut roster for that window,
  reviving exactly the backdate sliver the gate exists to stop (and would have to be set to 0 in the very
  emergency it was sold for). A stale in-flight event is **not stranded** — it lands sub-threshold and the next
  `Wit` re-pins under the current roster and witnesses, transitively covering it (see *local progress* below).
- **Local progress on own un-witnessed events (load-bearing for exact-tip recovery, 2026-06-24).** A submitter's
  node accepts its **own** structurally-valid, sub-threshold events as the local tip — you can't extend a
  `Rot` you haven't landed — so it makes forward progress *ahead of* witnessing; the **re-pinning event**
  (any event carrying the current `federationPin`) is what earns **cross-node** acceptance for the run (peers defer an un-witnessed
  event but fetch it once the witnessed re-pin commits it as `previous`). This is what recovers a stranded
  irreversible `Rot` (extend it with a witnessed re-pin) and a frozen-chain recovery `Rot` (land the burying `Rot` → chain is
  locally Active → re-pin under the current roster) **without any grace window** — the recovery rests on the **rotation reserve**
  (the standing T2 requirement), never on retaining the old signing key (the "delay the wipe" idea was a
  no-op — the re-pin signs with the rotation reserve preimage committed at the prior event, not the old key).
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
  arrival-order-dependent. The **shape-validity gate** — reject a seal-advancer that would bury a *sealed*
  branch, or a self-burial (a burying seal-advancer siblinging its own retained chain) — runs at the
  **acceptance-to-trusted-state** point: a **selected witness** applies it before signing
  (decline → the shape never reaches `threshold`); a **non-witness** gates on `threshold` (above). Every chain is
  federation-witnessed — there is no direct-mode self-gate. "Frozen" survives only
  as a **merge-origination** posture (a node originates no new work onto a live fork), never as the reading — so a
  fork-first and a seal-first node holding the same events read identically. Content-fork **prevention** (the
  one-content-sibling floor above) is **witnessed** — and every chain is federation-witnessed (no direct mode);
  the residual is a **witness compromise**, where a content fork forms, reads `forked`
  (fail-secure), and resolves by a burying seal-advancer.
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
  floor prevents a content fork *forming*, it can't make a formed sealed fork visible any sooner); the F8
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
  prior, enforced at the seal — can't be rolled back); the federation IEL is restricted to `Fcp`/`Wit`/`Trm` — the genesis `Fcp` and the **terminal `Trm` carry `manifest.clock` too** (the `Trm`'s clock ≥ the prior `Wit`; its `Rot`-revealed key-windows are clock-bounded and self-attest under the carve-out — so an all-windows-lapsed federation can still terminate).
  Consumers read the timeline by **walking the federation IEL they already walk for the roster** —
  reading each `Wit`'s `manifest.clock`. Witness key-windows change exactly at federation
  `Wit`s — **a rotation, optionally also a roster change (§1a)** — each carrying a clock timestamp, so timestamping
  them time-bounds every key's window (a retired key's `T_end` = its `Wit`'s clock time). `Wit`s are **rare** (§1a: ~yearly rotations, plus
  membership changes) — so the clock is cheap.
- **Receipt timestamps.** Each witness receipt carries the witness's asserted time (frequent, per-witnessing,
  self-asserted — individually untrusted). **A receipt's `τ` also gets a `≤ consumer-now + CLOCK_TOLERANCE_BAND` ceiling** (symmetric
  with the clock's F4 upper bound — cold-12 F5): a receipt claiming a future time beyond `now + CLOCK_TOLERANCE_BAND` is rejected /
  stale-flagged, so a forged receipt can't stamp ahead of real time.
- **The split — the clock bounds the receipts.** The clock (the `Wit`s' `manifest.clock` times) is the **sealed, trustworthy bound** (each key's
  validity window `[T_join, T_end]` in time); receipts are the **frequent values that get bounded.** **Load-bearing
  check:** a receipt counts only if its timestamp `τ ∈ [T_join(K) − CLOCK_TOLERANCE_BAND, T_end(K) + CLOCK_TOLERANCE_BAND]` per the clock. A
  harvested / rotated-out key (closed window) can therefore only validly stamp **old** receipts → a dormant forgery
  on it reads stale. Without this check the attacker just stamps "now"; with it, a closed-window key can't.
- **Second conjunct — forward-of-the-last-confirmed tip (backdate defense, §5; `vdti-adversary-cases` case 8).**
  Key-window containment (above) is conjunct (a); a counted receipt must **also** be **forward of the chain's last
  confirmed — fully-witnessed — tip.** It is a **current-vs-ancient** test, not a fine-grained ordering: on an
  **active** chain the confirmed tip is recent, so a **harvested old key** (closed window) satisfies **neither**
  conjunct (its window is old; the check demands current); on a **dormant** chain the confirmed tip is old, so a
  harvested receipt can read forward — the known **reserve-theft-takeover residual** (owner vigilance, "no silent
  *forgery*", §5 / inv 8). The reference is the **last confirmed tip** — deliberately **not** the
  immediately-preceding event, **not** a cross-witness pairwise aggregate over adjacent events (per-witness
  wall-clock skew breaks the pairwise form), and **not** the seal (the earlier "forward-of-the-seal" patch had no
  margin right after a seal — retired). **Batching reintroduces no skew:** every witnessed unit is a **single** IEL / KEL / **SEL** event
  (witnessed-SEL redesign, area-sel §1c — a SEL's inception batch witnesses atomically as its **v1**, the
  `Icp` riding `v1.previous`; across a SEL chain the client serializes forward-of-confirmed-tip, like
  IEL/KEL), and any structural batch is witnessed **atomically** (the verifier knows it is one unit → no
  intra-batch ordering claim); **across** batches the client **serializes** — waits until batch N is fully
  witnessed before N+1 (the same key-deletion-recourse discipline, `area-iel §5`) — so the confirmed tip is
  well-defined at **batch granularity**. Plus **per-witness monotonicity** — a witness never backdates *its own*
  receipt stream. **Event *order* stays the chain's job** (`previous`-linkage); the receipts carry only this
  **forward-of-confirmed-tip + key-window** requirement, never a pairwise aggregate.
- **Staleness → fail-secure.** A consumer computes a tip's freshest *valid* witnessing time; an ancient one is
  **flagged stale** and not trusted for loss-of-trust / current-state decisions without fresh re-confirmation
  ([inv 8] / F-E). This is a **decision-time wall-clock** check, recomputed against current `now` on **every**
  loss-of-trust decision — **including the token-cache reuse path** (the effective-SAID gate certifies structure, not
  freshness; the 365-day auto-expiry is time-triggered, fires with no event — so the token caches the witnessing-*time*,
  never a `fresh` verdict — vdtid-services §1d / cold-12 F1). A forgery can't obtain fresh re-confirmation (current honest witnesses won't witness an old-context event). A
  legit *active* chain re-pins and is freshly witnessed → trusted; a legit *dormant* chain is also stale-flagged
  (correct — its owner re-activates by re-pinning to be trusted for current-state). The forgery gains nothing.
- **`CLOCK_TOLERANCE_BAND` = 1 minute, a fixed protocol constant** (deterministic verification — every verifier agrees). It
  absorbs honest clock skew at a window boundary; its security cost is nil (the attack is *gross* staleness, not
  boundary-seconds). Distinct from the **staleness threshold** ("how old before flagged"), which is consumer /
  loss-of-trust policy (like the F8 bar).
- **Consumer clock sync — a load-bearing DEPLOYMENT INVARIANT (cold-13 F3 / C-2).** Every consumer's staleness /
  at-risk / `clock ≤ now+CLOCK_TOLERANCE_BAND` (F4) / `receipt-τ ≤ now+CLOCK_TOLERANCE_BAND` (F5) check reads against the **consumer's own wall
  clock**. So a consumer **must stay synced (NTP) to within the `CLOCK_TOLERANCE_BAND` (1 minute)**; a consumer out of sync by **more
  than a minute can't trust its own freshness results** — it mis-judges window boundaries, and a backward skew is the
  fail-*open* direction (stale reads fresh, at-risk suppressed). **Because it is fail-open, a drifted clock silently
  defeats the entire dormant-forgery / backdate defense (§1f) — so NTP sync to within `CLOCK_TOLERANCE_BAND` is a *security control*,
  not best-effort, and belongs in every deployment's operating requirements.** This is on the consumer, not the framework (a
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
  `Wit`** (the witness's KEL `Wit` **is** the rotation and anchors the IEL `Wit` — no separate rotation event) — an **off-ceremony `Rot`** (a witness `Rot` anchoring no `Wit`) on a witness KEL produces receipts the federation **does not honor** (the new
  key earns no pinned window; the old key's window is treated as closed at the most recent federation `Wit`), and an
  observed off-ceremony rotation is a **cut/eviction signal**. **Max-window auto-expiry — `MAXIMUM_WITNESS_KEY_WINDOW = 365 days` (cold-9 C2 / cold-10 F4, Jason 2026-06-29).** A key-window
  may stay open at most `MAXIMUM_WITNESS_KEY_WINDOW`: an un-refreshed window is treated as **closed at `T_join + 365 days`** (a fixed
  protocol constant, like the `CLOCK_TOLERANCE_BAND` — deterministic, every verifier agrees), **without** an explicit `cut`. So a
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
  a consumer **rejects / stale-flags any federation clock time beyond `consumer-now + CLOCK_TOLERANCE_BAND`.** Otherwise a
  compromised-but-unevicted federation **with `t_govern` members compromised** (setting the clock requires authoring a
  `Wit` — a *governance* act, so this is **beyond** the witnessing `< threshold` residual — cold-12 F3; the F4 guard is
  **defense-in-depth**, bounding an already-`t_govern`-compromised federation's blast radius to ~`CLOCK_TOLERANCE_BAND`) could
  **future-date** a `Wit`'s `manifest.clock` to push every key-window forward → closed windows read open →
  harvested-key forgeries read fresh.
  The consumer's own wall clock is the cheap external check; future-dating beyond `CLOCK_TOLERANCE_BAND` is prima facie suspect —
  bounding a clock-setting compromise's blast radius to ~`CLOCK_TOLERANCE_BAND`. (inv 14.)
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

### 1g. Witness receipt — shape + scope (§2c, RESOLVED 2026-07-08; ⚠ NOT previously design-reviewed — flag to the encode-review as its first decorrelated pass)

- **Scope (Decision 1) — REVISED: the SEL IS witnessed (witnessed-SEL redesign, 2026-07-12, area-sel §1c).** A witness receipts an **IEL, KEL, or SEL** event; a SEL is **its own witnessed chain** (first-seen at its `(SEL-prefix, serial)`, inheriting the owner IEL's federation), because the FIRST-CUT integrity justification — anchor-monotonicity + the cross-layer theorem — is **false** (a SEL forks under a linear IEL). The correlation reasoning below is **superseded**: a lookup-SEL prefix now rides a receipt, an **unguessable** value exposed only to **semi-trusted federation infra** over the **encrypted** mesh (confirm-a-known-subject only; the exfiltration-during-a-compromise-window residual is the accepted `< threshold` class, inv 16). _Historical rationale for the retired "never witnessed" choice:_ a SEL rode its IEL anchor (integrity via anchor-monotonicity + the cross-layer theorem; freshness via
  the anchoring IEL event's receipts — a revocation/rescission lookup-SEL `Trm` is sealed by a witnessed IEL
  `Rev`/`Dth`, whose `kills[]` declares the target — §7 / `area-sel`). This is the load-bearing **correlation
  protection**: a sensitive **subject prefix / `cred.said`** **never enters a receipt** (a cred is anchored as its
  issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` in an IEL `Ixn`'s opaque `anchors[]` — cred
  = anchored SAD, no cred-SEL, 2026-07-09; `cred.said` never raw; the lookup-SEL flat `kills[]` target lives only on a
  witnessed `Rev`/`Dth`, ≠ the SEL's prefix). Retires the former cred-SEL
  `(prefix, said(v1))` receipt. *Verify-first (confirmed against the SEL kind list, `area-sel`):* every SEL event that
  needs witnessing rides an IEL anchor (`Icp` via its v1's `previous`; content/`Pin` via IEL `Ixn`; `Gnt`/`Trm` via
  `Ath`/`Rev`/`Dth`) — nothing needs a standalone SEL receipt.
- **The prefix rides in the clear (Decision 2).** A receipt is only ever gossiped **witness-only + encrypted** or
  **bundled with the event it witnesses**, so any holder already has the body (+ prefix) or the bundled document
  (which already carries the `prefix ↔ said` link). **REVISED (witnessed-SEL redesign, area-sel §1c):** a SEL
  receipt's `chain_prefix` is a lookup-SEL prefix (unguessable, confirm-a-known-subject over the encrypted
  mesh), **plus** the public **IEL/KEL identity** prefix — both mesh route-metadata, fine under the trust
  model (federation infra, `< threshold` byzantine). `cred.said` stays un-linkable to a receipt (the cred is
  an anchored SAD under the issuer's opaque `anchors[]`; the lookup-SEL prefix is a hash of `cred.said`, not
  `cred.said`). No `basis`, no computed selection-input — plain `prefix`.
- **The receipt is itself a SAD (Decision 3)** (own `said`, own `kind` — §9's kind-required-on-SAD applied to the
  receipt); its **signature rides adjacent, never in the body** (a SAD cannot contain a signature over its own
  `said`; receipts are adjacent attestation data, §1e). Body:

  ```
  {
    said,            // the RECEIPT's own SAID
    kind,            // a receipt kind (§9 kind-required)
    threshold,       // witness-config threshold IN EFFECT at this position — stateful (§2b; cheap detect + match-on-pull)
    signers,         // witness-config selection size IN EFFECT at this position — stateful (select() needs it with the roster)
    federationPin,   // the chain's federation binding at this position → resolves roster(F @ federationPin) for selection
    chain_prefix,    // the witnessed chain's prefix (plain — Decision 2)
    event_said,      // the one committing SAID of the witnessed event
    event_serial,    // its serial
    timestamp,       // witness's asserted time (§1f key-window + §5 forward-of-confirmed-tip; τ INSIDE the signed payload)
    witness_prefix   // signing witness's KEL prefix (resolve its key-window; confirm selected)
  }
  ```

  \+ the witness **signature adjacent** (over `said`). A **batch** is witnessed by the **one committing SAID**
  (`event_said` — committed in the event body by chain linkage `tip.previous` or the anchoring event's `anchors[]`),
  never an enumerated list — single-SAID keeps receipts small → floodable (§2b).
- **Binds the full as-of-position selection context `{federationPin, threshold, signers}` (Decision 4).** Binding
  `federationPin` + `signers` (+ `threshold` for the count) lets a **mesh witness resolve `roster(F @ federationPin)`
  from its OWN federation IEL and validate `witness_prefix ∈ select(chain_prefix, event_serial, roster, signers)`
  without the chain body** → sound cheap detection, fakes dropped at the mesh edge. The context is **stateful** (the
  value in effect at this event's position, not a chain constant). **Both IEL and KEL carry `federationPin`,
  matched** (the user IEL's `{federation, federationPin}` matched on its anchoring member-KEL `Wit`s; the
  **federation IEL carries none** — it *is* the federation; a SEL inherits). The checks are **equality**, not
  `> chain-pin`: the receipt context must **equal** the chain's actual as-of-position config, **plus** the currency
  gate — a stale-membership pin earns **zero** countable receipts. **Orthogonal to §5's tip-ordering:** that gates
  *time* (freshness/backdate); `federationPin` gates *roster version* (which witnesses are selected).
- **Federation-pin currency (Decision 5).** *Stale* = a governance `Wit` moved the roster **since** the pin, by
  **more than the key-window `CLOCK_TOLERANCE_BAND`** (§1f). Detection is a **local pre-check at the receiving node returning a SIGNAL
  only** (any node the user reaches is a current F member holding F's state): stale → a positive "stale — rebind"
  signal (not an absence-of-receipts timeout). **The signal is a hint, not authoritative** — the consumer **walks
  the federation chain** from the config-pinned `FEDERATION_IEL_PREFIX` to the **verified** current position and
  rebinds to a value **it verified**, never the node's asserted value (end-verifiability — trust the data, not the
  service). **Witnesses refuse a beyond-band-stale event** (not sign-then-not-count — a signed stale event would
  consume the position's first-seen slot and block the rebind `Wit`). **The submitter's own node likewise drops a
  declined stale-pin local tip** — it is **not carried forward** as local progress (§1e), so it can't self-collide
  with the rebind at the same serial; the rebind `Wit` takes the serial cleanly (C2). **Rebind = a `Wit` carrying the verified
  current `{federation, federationPin}`** (**T2** — the rotation reserve; `t_govern`; member-KEL-`Wit`-anchored +
  matched): it declares the current pin, so its own selection is `roster(F @ current)` = current witnesses →
  witnessed → **self-bootstraps** into the current federation; takes the clean serial; content `Ixn`s inherit the
  new pin. **Recourse-safe** — the stale event was never confirmed → keys never deleted (§5 wait-until-witnessed) →
  the rebind is always authorable. **Resubmit is idempotent (dedup by SAID) → dedup doubles as a liveness check**
  (resubmit any event to learn live-vs-declined); resubmitting a *stale-pin* event never fixes it (the pin is baked
  into its SAID) — rebind + submit a **new** event.
  - **The roster-change race** (event accepted at current pin P, then F rotates before the selectees receipt): the
    selection is **fixed by P** (as-of-context) — the rotation doesn't change who should witness *this* event. A
    selectee **cut during the race still receipts within the key-window `CLOCK_TOLERANCE_BAND`** (§1f); if threshold is reached the
    event is **witnessed and durable** (established receipts keep counting after F advances past P). The currency
    gate is an **establishment-time** check (can't *start* gathering under a beyond-band-stale pin) — it **never
    voids** receipts established under a then-current pin. **One `CLOCK_TOLERANCE_BAND`, three jobs:** cut-witness receipting,
    just-stale-pin grace, race absorption. Beyond `CLOCK_TOLERANCE_BAND` → refuse → rebind + resubmit (recoverable).
- **Batching — REVISED (witnessed-SEL redesign, 2026-07-12, area-sel §1c): SEL events now earn their own receipts,** so the receipt scope expands beyond IEL/KEL and the intra-batch receipt-skew / forward-of-confirmed-tip machinery (§5) applies to SELs too. _(The FIRST-CUT "batching collapses out — no multi-event witnessing batch remains; SEL batches become `anchors[]` content under one IEL `Ixn`" rested on the SEL not being witnessed; superseded.)_
  Client serialization stays, at **IEL granularity**. The one remaining multi-event batch — federation genesis
  (`Fcp` + founder `Rot`s) — is the **bootstrap exception**, not a receipt batch: its trust is the config-pinned
  `FEDERATION_IEL_PREFIX` (`vdti-federation-inception-reference.md`), not a receipt count; serial-0 root → nothing
  to be forward-of → it sidesteps the receipt-monotonicity machinery entirely.
- **KERI reference.** A KERI `rct` `{v, t, d, i, s}` binds `prefix ↔ said` the same way (no threshold/timestamp);
  VDTI's receipt is that shape **plus** `threshold` + a payload-`timestamp`, scoped to IEL / KEL / **SEL** (the
  SEL is witnessed now, area-sel §1c) — VDTI relies on `cred.said` never entering a receipt for cred privacy
  (a SEL receipt carries only an unguessable lookup-SEL prefix), not on hiding the prefix (KERI AIDs are
  public).

## 2. Mined from kels-216 — patterns that carry (confirm in land)
- **Receipts indexed by `(prefix, serial)`**, *not* event SAID — structural; this is what lets **competing receipts
  at a position** aggregate into one detectable signal. *(kels' threshold-two-events — both branches at threshold —
  is under the witnessing floor precisely the impossible state for honest witnesses; it remains reachable only at
  fork-cost or for sealed siblings. Detection re-keys on competing receipts + fetched data — 2026-07-02.)*
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
- **Which vdti kinds get witnessed? — REVISED (witnessed-SEL redesign, 2026-07-12, area-sel §1c).** **IEL, KEL, _and_ SEL events are witnessed** — a SEL is its own witnessed chain (first-seen at its `(SEL-prefix, serial)`, inheriting the owner IEL's federation), because the FIRST-CUT "rides the theorem, never witnessed directly" integrity justification is false (a SEL forks under a linear IEL). Witnesses see SEL structural fields (incl. a lookup-SEL prefix) — **acceptable trust-infra exposure** over the encrypted mesh (semi-trusted `< threshold`; confirm-a-known-subject only; the exfiltration-during-a-compromise-window residual, inv 16). _(Superseded: the "sensitive subject prefix / `said(cred)` never enters a receipt" correlation protection.)_ Within KEL/IEL, all
  chain-advancing / security-relevant events earn receipts, so federation-layer divergence stays uniformly
  detectable.
- **Receipt encoding — RESOLVED (§1g / §2c).** The receipt-SAD shape (the fields binding the event's
  `federationPin` context, the signing witness's KEL position, and the payload-`timestamp` `τ`), the witnessing scope (IEL, KEL, **and SEL** — the SEL is witnessed now, area-sel §1c),
  and the currency/rebind machinery are settled in **§1g**. `τ` is **inside** the witness-signed
  payload (else a harvested receipt's `τ` is rewritable to "now" and the §1f clock check is moot); a cut witness's
  receipt counts only within its federation-pinned key-window (`τ ≤ T_end`, §1a/§1f); the position-`terminator` is
  dropped.
- **Federation `Trm` semantics** — terminating a federation: chains still bound to it must `Wit`-rebind or
  become unwitnessable. Confirm the intended consumer experience.
- **Per-witness address/discovery** — kels gives each witness a deterministic-prefix address SEL holding endpoints
  (discovery reads the roster, walks each peer's address SEL). **Infra concern, downstream of the primitive** —
  flag for the infra pass, not the primitive docs.

## 5. Drift → land backlog
- **Write `docs/design/substrate/federation/{bootstrap,witnessing}.md`** fresh from this note (genesis ceremony +
  the witnessing model). (`protocol-doctrine.md` §Federation and `event-shape.md` are already reconciled — the
  old `federationBinding` and self-signing carve-out are gone; only the `federation/` docs remain to write.)
- **Apply the design-pass §2.2 matrix fix** (federation inception = `Rot → IEL Fcp` (the marker); founder `Rot` anchor — kind-strict, T2 ↔ T2; no founder `Fed`/`Wit`, 2026-06-28).
- **`event-shape.md` KEL:** witness-config SAD `{ threshold, signers }` as the manifest **`witnesses`** role (shared with the KEL note's land item).
- Carry the witnessing mechanics (one-content-sibling-per-serial + one-sealed-sibling-per-position-first-seen (revised 2026-07-11) · `(prefix,serial)`
  selection · the witnessing floor + fork-cost · competing-receipt detection · destruction-on-witnessing) into the vdti
  witnessing doctrine, in vdti kind language (kels-216's unconditional always-witness + threshold-two-events are
  superseded — §1e/§2).

## 6. Confidence / what's owed
- §1a–d (federation structure) — **high** (design-pass §7 + reference doc; Jason-confirmed Q1/Q3/Q4).
- §1e (witnessing) — **high** (kels-216 is detailed and was hardened over its own rounds; Jason confirmed it
  carries). The session-new pieces (restricted federation kind set; `signers` naming; exact-tip gate) are direct
  consequences, Jason-confirmed.
- §4 — the witnessed-kind mapping + receipt encoding are doctrine *detail*, not design blockers.
- Owed: the doctrine-land phase; the adversarial pass on §4; resolves the IEL note's "federation `Ath`?" open (no).
