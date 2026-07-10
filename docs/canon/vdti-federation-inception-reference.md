# vdti — Federation inception: reference & reshape resolution

**Status (2026-06-19).** Design-pass output for the **federation half** of the log-primitive reshape
(`vdti-log-primitive-reshape-*`). Captures the reference material (kels prior art + vdti's current model)
and the resolution converged this session. Feeds the eventual designer note + brief edits.

## TL;DR — the resolution

- **Federation = a restricted IEL incepting `Fcp`** (the inception **marker** — a structural disambiguator the
  verifier dispatches on, **not** a trust carve-out; §4). The federation IEL is `Fcp`/`Wit`/`Trm`.
- **Roster = witness KELs *directly*** (threshold over them). No per-witness identity wrapper.
- **KEL keeps `Fcp`** (federation-infrastructure inception) **and `Wit`** (the one witness/federation kind, T2 —
  a **user** bind/rebind on an `Icp`-rooted KEL, **federation governance** on an `Fcp`-rooted KEL; `Wit` anchors `Wit`, anchor-kind uniform but field-match **facet-specific** — Q3).
- **Genesis trust = config-pinned `FEDERATION_IEL_PREFIX`** (out-of-band root) + ordinary founder-anchor
  authorization. **No self-*witnessing* carve-out** (the `Fcp` marker is interpretation, not trust — §4).
- **Witnessing = as-of-context, never tip** — receipts are adjacent/unanchored; durable with **no
  re-witnessing**; a **currency gate** makes witnesses refuse stale-`federationPin` events (the chain must
  advance `federationPin`, riding any event — a `Wit` to *rebind*); backdate closed by the gate + HSM key destruction (§5).
- **Taxonomies:** the general/user IEL is **8** (`Icp`/`Ixn`/`Evl`/`Ath`/`Rev`/`Dth`/`Trm`/`Wit` — `Rpr` dropped in the first-seen pivot; the `Kil`
  sealed kill-anchor was split out 2026-06-21 and later split into `Rev` (revocation, `t_govern`) + `Dth`
  (rescission, `t_authorize`), and **`Fed` was renamed/merged to `Wit`** 2026-06-28: the one kind
  that does both the user federation-binding and federation governance); a **federation** IEL is the restricted set
  **`Fcp`/`Wit`/`Trm`** (`Fcp` = its inception marker, `Wit` = governance — roster + rotation, **T2**, **`Wit`-anchored**
  (field-match = witness-config only, Q3) — replaces `Evl` for the federation; 2026-06-28, cold-4 B1); see `vdti-area-iel.md`. KEL is **6 labels**
  (`Fcp`/`Icp`/`Ixn`/`Rot`/`Wit`/`Trm`) but **5 per KEL** (`Fcp` **XOR** `Icp` as root — area-kel:33) — `Ror`/`Rec`
  dropped in the first-seen pivot; `Fed` → `Wit`.

Both layers carry `Fcp` (KEL = federation-infrastructure inception; IEL = the federation inception marker) — **dispatched by layer**, an intentional shared marker, not a collision.

## 1. What the federation is (reshape)

- A federation is **one IEL** — the *federation IEL*, prefix conventionally `F`. It is the witnessing/attestation
  authority the rest of the system trusts.
- Its **roster is the witness-server KELs**, with a threshold. Witnesses are **devices (KELs)**, not identities;
  a witness is one HSM-backed signing key, horizontally scaled by replication (deployment-invisible — the model
  sees one logical KEL per witness key).
- A **node is a device in the federation identity**, not its own identity. A witness KEL is **single-federation**
  (`Fcp`-rooted infrastructure, governed *into* one roster — §2/§4); to serve another federation, **spin up a new
  KEL** and join it (the old KEL's events stay validly witnessed by the old federation). This **contains** a witness
  compromise to one federation — no cross-federation fan-out. **Why no self-binding (2026-06-28):** a witness is
  **governed into** the roster (admitted / cut / rotation-captured — all by `Wit`, the federation's sole governance
  kind), never self-bound — it is `Fcp`-rooted infrastructure. A *user* key-log's `Wit` is its choice of who
  witnesses *it* (single-federation, anti-straddle — the rebind); a witness KEL's `Wit` is the **opposite role**
  (federation governance). *(This **reverses** the earlier "a witness serves many federations / blast-radius
  fan-out." **User-identity** federation migration via rebind + cooperative overlapping trust is a **separate**
  mechanism that **stays** — federation-witnessing §1d; it is the user's IEL rebinding, not a witness on two rosters.)*
- A witness rotates as a federation **`Wit`**: its KEL `Wit` **IS** the rotation (refreshes signing + rotation reserve) **and
  anchors the federation IEL `Wit`** (kind-strict, T2 ↔ T2; the governance-facet match is the **witness-config only**
  — Q3; roster rides the manifest `Evl`-style, `clock` is monotonic + `≤ now+band`; `pins = Wit.previous`, the
  pre-rotation KEL tip → the clock's `T_end`; the `Wit` is itself the rotation — **no separate rotation event**, no phantom key — cold-4 B1), with an inline
  **`clock`** timestamp in the `Wit`'s `manifest` — so the rotation boundary is recorded in the federation timeline
  (closes Finding 1). Adding/removing a witness is **also a `Wit`** (the federation has **no `Evl`** — `Wit` does all
  governance; a `Wit` is always a rotation, optionally also carrying a roster delta + its `manifest.clock`).
  **Rare:** ~yearly synchronized rotations at ML-DSA-87 (see federation-witnessing §1a/§1f).
- A KEL carries **two federation fields** (on `Fcp`/`Icp`/`Wit`): **`federation`** = the federation **prefix**
  (which F; follows F's evolution) and **`federationPin`** = a **SAID** pinning a specific federation event (the
  as-of F-position; ratcheted forward via `Wit`). Prefix-vs-SAID — the same split as the SEL's `owner`/`pin`.

## 2. Genesis ceremony (to draw)

No prior federation or gossip mesh exists yet, so the ceremony is point-to-point.

1. **Founder witness KELs incept pre-federation** — each `Fcp` (v=0). **Self-attested** (no federation exists yet
   to witness it — this is what makes the bootstrap non-circular: the federation is built *from* these KELs).
2. **Each founder anchors the federation inception** — a **`Rot`** (v=1, tier-2) on each founder KEL whose
   `manifest.anchors` names the federation IEL's **`Fcp`** (the inception marker — **kind-strict: tier-2 `Rot` →
   tier-2 `Fcp`, no founder `Fed`/`Wit`, no tier-elevation — 2026-06-28**). The founder is bound to the federation
   by being **named in the roster it founds**, not by self-binding: a federation's **own witnesses are governed
   *into* the roster, never self-bound** (a witness is `Fcp`-rooted infrastructure; the `Wit`-as-rebind is a *user*
   KEL's choice to be witnessed — it has no place on a witness's own KEL, whose `Wit` is governance). So genesis is
   `Fcp → Rot`, never `Fcp → Fed`/`Wit`-rebind. *(This replaces the old founder-`Fed`-anchors-the-`Icp`-via-tier-elevation
   bootstrap; the tier-elevation carve-out is gone — see `vdti-invariants.md` inv 4.)*
3. **Federation IEL `Fcp`** — the federation inception, marked `Fcp` (the structural disambiguator), whose roster is
   the founder witness KELs (threshold). It is authorized the ordinary way: its declared members (the founders)
   anchor it (step 2). The `Fcp` is the **marker**, **not** a self-witnessing rule — trust roots in the config-pin (§4).
4. **Atomic batch** — founder `Rot`s + the federation `Fcp` land together (all-or-nothing). Founder `Fcp`s are
   per-founder local pre-work.
5. **Gather → submit → redistribute** — founders push their bundles point-to-point to a *coordinator* (an
   operational convention, **not** a protocol leader / no election); the coordinator submits the `Fcp` once all
   anchors are locally present, then redistributes the full bundle to peers; nodes set `FEDERATION_IEL_PREFIX`
   and restart; the gossip mesh forms; subsequent sync flows through normal anti-entropy.

**Trust root:** every node is configured (compile-time default + runtime override) with the
`FEDERATION_IEL_PREFIX` it trusts; the verifier validates the received chain against that expected prefix. The
prefix derives from the whole inception content `(roster, threshold, nonce)`, so it is a binding commitment to
the exact founder set (matching it would require a Blake3 preimage). Tamper-protection for the root comes from
every node holding the same config-pinned prefix; a doctored root mismatches config and is rejected. Everything
*after* genesis (`Wit` governance changes — roster + rotation) is witnessed normally by the now-existing federation.

## 3. Rebinding (the user KEL/IEL `Wit`)

- **A user KEL's `Wit` = a *user* KEL (re)declaring which federation witnesses it** (one facet of the one
  witness/federation kind — §1b; the other is federation governance, on an `Fcp`-rooted witness KEL). A user KEL
  `Wit`s to move to a new witness set/federation. It carries **`federation = F`** (the **prefix** — binding is to the
  entity, so it follows F's roster evolution) and **`federationPin`** → the F-event it pins (the as-of context, §5).
  **T2** (changing who witnesses you is high-assurance — a forged rebind would move you to a malicious
  federation). *(There is **no** genesis `Wit`-rebind: a federation's own witnesses are `Fcp`-rooted, governed into
  the roster, never self-bound — §2.)*
- **The identity's federation is recorded at the IEL — the `IEL Wit` kind (2026-06-28; was `Fed`).** A user
  identity's federation choice is a first-class IEL event (**T2**, `t_govern`), **anchored by its members' KEL `Wit`s**
  (kind-strict, T2 ↔ T2 — inv 4; `Wit` anchors `Wit`; the user-rebind facet field-matches `{federation, federationPin}`, C4). The IEL `Wit`'s **federation-binding fields** —
  the **closed set `{federation, federationPin}`** (no optional fields; cold-5 C4) — must **match exactly** those of
  every anchoring KEL `Wit`, **checked on every walk** — so the IEL `Wit`
  records only what its members signed (auditable, never self-asserted). The **identity's federation is the IEL's own
  authoritative binding**; it inherits **nothing** that doesn't reach threshold or match, so a lone/desync'd member
  KEL (it anchors a sub-threshold IEL `Wit` → verifiably broken, inert) **cannot straddle the identity** (cold-3 B2).
  The **initial** binding rides the IEL `Icp` (mirroring the KEL `Icp`); the `IEL Wit` only *changes* it.
  Single-owner logs **inherit** their federation context from their owner identity's current binding. During a rebind,
  members below `t_govern` lag on the old federation until they each rebind — bridged by **overlapping federation
  trust** (the **user-identity** migration window, §1 / federation-witnessing §1d).
- A user KEL that has `Wit`'d across federations has a **multi-federation history**; trust is **per-federation and
  non-transitive** — a verifier must independently trust *each* federation prefix the chain was bound to, and
  each event is witnessed by whichever federation was current when it landed.

## 4. Why no self-*witnessing* carve-out (rationale) — and why the `Fcp` *marker* is different

The **self-witnessing carve-out** (vdti's old model, and the superseded kels-218) answers *"who witnesses the
federation's own inception, before the federation exists?"* by making the verifier — dispatched on an `IEL Fcp` kind
— treat the genesis as **self-witnessing** (witness pool = the inception's own declared members). **That dispatch
is dropped.** Note the distinction from the **`Fcp` marker** the remodel *keeps* (§2): the marker tells a verifier
*"this IEL is a federation IEL"* (apply restricted kinds, exclude-self witnessing) — **interpretation**, not a
witnessing or trust shortcut. The genesis is still cross-witnessed exclude-self once the mesh forms, and trust still
roots in the config-pin. So `IEL Fcp` returns as a marker while the self-witnessing **dispatch** stays dead.

The carve-out is dropped by separating two things it conflates:

- **Authorization** ("is this `Fcp` inception validly created?") — handled the **ordinary** way: anchored by its declared
  members' KEL events (the founders' `Rot`s — kind-strict, T2 ↔ T2). The founders *are* the roster, so their anchors satisfy the
  inception threshold. No special rule.
- **Trust-rooting** ("should a consumer trust this federation *at all*?") — **inherently out-of-band**; it cannot
  be derived cryptographically from nothing. Made explicit as the **config-pinned prefix**.

The insight: a "self-witnessed" genesis is only as trustworthy as the decision to accept its prefix — which *is*
the config-pin. The **self-witnessing dispatch** added a verifier branch without adding any trust the config-pin
doesn't already give — circular theatre, so it's dropped. The **`Fcp` kind itself** is retained, but for a
different job: a **marker** the verifier dispatches on to *interpret* an IEL as a federation (restricted kinds,
exclude-self witnessing), **never** to vouch its trust. The config-pin stays the honest trust root.

## 5. Witnessing — durable, as-of-context, never re-witnessed

Witness receipts are **adjacent attestation data** (like a KEL's signatures sit adjacent to its events) —
**not** chain-committed / anchored / floored. The model is three parts:

1. **As-of-context evaluation (durability).** A receipt counts iff its signer is in F's roster **as-of the
   event's `federationPin`** — the pin carried by the most-recent `Icp`/`Wit` at-or-before the event on its KEL
   chain (an **IEL** event uses the identity's **own** authoritative `Wit`/`Icp`, never a member KEL anchor; a **SEL** inherits from its owner IEL — cold-3 B2), forward-floored on the KEL. **Never evaluated at F's current
   tip.**
   `roster(F @ context)` and each witness's KEL key as-of the context are both fixed (F and the witness KELs are
   append-only), so an event stays witnessed **forever**, unchanged by later roster churn or witness key
   rotation — **no re-witnessing of historical data.**
2. **Acceptance-time currency gate.** Witnesses **refuse to witness an event whose `federationPin` isn't the
   current member set** (i.e. the chain hasn't advanced its `federationPin` to F's current state). This forces
   an *active* chain to advance its `federationPin` by carrying a fresh one on **any** next event — **lazily, one event on next activity**
   (a `Wit` is needed only to *rebind*) — not a rescan — to keep getting witnessed. A fresh / stale-`federationPin` event can't gather current-witness
   receipts, so it never enters honest accepted state.
3. **Backdate closure — destruction is the stance (F4 resolved 2026-06-20).** A backdated forgery would need
   threshold receipts as-of an old context (where since-removed witnesses were in). The currency gate (2)
   refuses honest witnessing of such events; the per-chain forward floor blocks an active chain from regressing
   its context; and **witnesses destroy old key material the moment they confirm an event is witnessed** (baked
   into the code, not an operator promise), so a harvested old key can't produce a forged "as-of-old" receipt.
   Destruction is *sufficient* because (a) firing on confirmed-witnessed leaves **no camping race**, and (b) the
   old key grants **zero incremental capability** — obtaining a not-yet-destroyed key requires compromising the
   *live* witness, which already lets the attacker mint a *fresh* receipt. The irreducible residual is therefore
   compromising **threshold-many *current* witness keys** = the federation itself is compromised (recovery /
   re-incept), **not** a backdate via stale keys.

   **Considered and rejected:** a CT-style transparency checkpoint (periodic threshold-signed Merkle roots over
   the witnessed set) — it defends only against destruction *not happening*, a residual strictly dominated by
   live-federation compromise; **burden outweighs gain.** Also rejected: immutable / never-rotate witnesses
   (a non-rotating key only *widens* its as-of-validity window — the wrong direction). Witnesses stay stable,
   rotatable members; destruction on confirmed-witnessing is the closure.

Drawn in `docs/design/vdti.excalidraw` examples **6** (member lifecycle — `federationPin` ratcheting forward when
the federation does a `Wit`) and **7** (a user KEL rebinding to a new federation, `federation` + `federationPin`
both moving).

**Durability vs. creds:** a cred is a durable *authorization* (a floored chain event, valid as-of issuance);
witnessing is a live *observation* re-affirmed as-of-context. The floored cred *gets* the as-of-context
witnessed signal; they compose.

**Remaining mechanism detail** (for the witnessing-doctrine reconciliation): the exact receipt encoding that
binds a dateless adjacent receipt to (a) the event's federation context and (b) the signing witness's KEL
position — so the verifier resolves `witness ∈ roster(F @ context)` with the correct key version — plus the
precise "current member set" tolerance the acceptance gate enforces (exact-tip vs a grace/overlap window).

## 6. Reference sources

- **kels canonical (the reference model — federation-as-plain-IEL):**
  `../kels/docs/design/infrastructure/federation.md` (2026-05-22; zero `Fcp`/`Fed`) +
  `../kels/docs/design/primitives/data/event-logs/iel/events.md` (the kels baseline taxonomy; vdti's first-seen
  kinds differ, above).
- **Reframe rationale:** `../kels/.working/kels-190-federation-as-identity.md` (why the registry-service /
  Raft-vote model collapses into an IEL).
- **Superseded `Fcp`/`Fed` model (what vdti's *pre-remodel* model mirrored — read only to see the old shape; the
  current model is `Fcp` marker + the one `Wit` kind):** `../kels/.working/kels-218-bootstrap.md`.
- **vdti's current (old) federation:** `docs/design/protocol-doctrine.md` §Federation Convergence (§562),
  §Federation witnessing (§677; self-signing carve-out §691); `event-shape.md` §Batching "Federation bootstrap"
  + the IEL `Fcp` row.

> Note: kels composes its federation from member *identities* via `identity()` **policy** leaves (its federation
> IEL carries policies). vdti's reshape has **no policy in primitives** and **roster = KELs only**, so vdti's
> federation IEL is a threshold over witness **KELs directly** — simpler than kels, and it needs no per-witness
> identity wrapper because a KEL prefix is stable across key rotation.

## 7. Still open / to include when drawing

- **Add the founder `KEL Fcp` inception** to the diagram (was omitted).
- **Per-witness address/discovery** — kels gives each member a deterministic-prefix address SEL holding its
  endpoints (discovery reads the federation roster, walks each peer's address SEL). Likely a vdti infra concern,
  downstream of the primitive; flag for the infra pass, not the primitive docs.
- **Witnessing model is settled (§5);** what remains is the *mechanism detail* there (receipt encoding binding
  it to context + witness KEL position, and the acceptance-gate currency tolerance) — folds into the
  witnessing-doctrine reconciliation.
- Inherits the reshape's remaining smaller opens: IEL `Evl` roster/threshold-delta field shape (proposed:
  full-state snapshot), and the rest of the doctrine reconciliation
  (effective-SAID, divergence "valid-for-binding" cutoff).
