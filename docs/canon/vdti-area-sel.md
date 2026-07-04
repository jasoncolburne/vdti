# vdti — area note: SEL (single-owner data log)

**Status: FIRST CUT (2026-06-20).** This note **supersedes design-pass §3** (and the SEL-inception parts of
§2.1/§2.2) for the SEL primitive — it folds in `inv 15` (inception tier + the uniform serial-1 `Pin`) and the document-layer
decisions (cred-as-a-SEL, SEL `Trm`, no registry). **Note:** §2.1's `≤1 Ixn per SEL` rule + seal-bounding still
*hold* — only its inception-pair description changes. Driven *down* from the document/policy area, exactly as the
document-first sequencing intended.
**Invariants referenced:** [inv 2] single-locus, [inv 3] layers-isolated, [inv 4] manifest-down/pin-up,
[inv 5] pin-floored, [inv 10] lookup-SELs, [inv 13] divergence-scoped-to-`Ixn`, [inv 15] inception/pin.

## Sources
- `vdti-log-primitive-reshape-design-pass.md` §2.1, §3 — the prior SEL model; **partially superseded here**
  (the "every SEL is `Icp`+`Evl`" + "no SEL `Trm`" claims).
- `vdti-area-document-policy.md` §A/§F + `inv 15` — the driving decisions.

## 1. Locked-candidate — the current SEL model
- **SEL = a single-owner data log.** Owner = exactly one **IEL** (its prefix). No policy, no roster, no
  multi-party governance internally [inv 2]. Layers isolated: a SEL pins/anchors only its owner IEL [inv 3].
- **Prefix = the `Icp`'s whole-content digest** over its populated fields — **`owner`** + `topic` + `data`
  (shorthand `derive(owner, topic, data)`, **not** a side-tuple hash: it's the same whole-content prefix every
  event has, so **any** field on the `Icp` enters it — adding a `pin` would break recomputation). **`owner`** =
  the owner IEL prefix, **`Icp`-only and immutable** (a SEL has one owner for life). `topic` = an application
  discriminator; `data` (**optional**) = nonce (non-discoverable / private) or meaningful bytes (discoverable /
  recomputable — e.g. a rescission's `data=P`). **`topic` + derivation replace KERI's registry identifier** — no
  registry object exists.
- **★ `data` entropy is load-bearing (clear rule, Jason 2026-06-20).** When `data` is used for an **unpredictable**
  prefix (a *private* SEL — the nonce that makes the prefix unguessable), it **MUST be high-entropy**. Otherwise an
  attacker brute-forces it, recomputes the prefix, and **confirms / de-anonymizes** the locus (and a predictable
  prefix weakens collision/uniqueness too). **Digesting `data` does NOT substitute** — a hash of low-entropy input
  is still brute-forceable; the *input* must carry the entropy. (Parallels the IEL `Icp` `nonce` requirement.)
  Where `data` is **deliberately discoverable** (a public cred-SEL, a lookup-SEL `data=P`), unpredictability is
  *not* the goal — the protection there is **owner-rooting** (only the owner IEL anchors events at the locus →
  prediction ≠ forgery), not entropy. *(Propagate to the doctrine prefix-derivation rules.)*
- **Classification criterion = blind-recomputability, NOT discoverability (F10).** A SEL is a **lookup SEL**
  *iff* a verifier **blind-recomputes its prefix** `derive(owner, topic, data)` from data it already holds; a
  **content SEL** is one you are *handed*. A cred-SEL is **content** (the holder presents the cred), but it is
  **self-locating**: `data` = the credential's SAID, so a verifier *holding the cred* recomputes `said(cred)` →
  `derive(issuer, CRED_TOPIC, that)` → the SEL prefix → walks it for revocation. Recomputing needs the **full cred
  body** (a private cred's body carries a high-entropy `nonce`), so an attacker without the cred can't locate it —
  privacy rests on entropy-in-the-body, not on a non-recomputable prefix. *(This refines the earlier
  `data = {pin, body-digest}` / "non-blind-recomputable" framing — `data` is now the whole-cred SAID, 2026-06-21.)*
  - **Content SEL** (e.g. a cred-SEL): **`data` IS the credential's SAID** → **T1** [inv 15]; the
    `Icp` carries **no manifest** (the `data` is the whole reference) and **no `pin`** (it must stay recomputable
    for lookup). **The `Icp` is floored by its serial-1 event** — any event carries the pin the `Icp` can't, so a bare
    **`Pin` is the fallback**, used only when inception batches no other first event (2026-06-27). **Authentication
    is the v1's anchor, not the recomputable `Icp` (S1):** an `Icp` with no resolvable anchored v1 on the owner IEL
    is **not** validly issued (inv 15). *(The cred body
    carries **no `pin`** — the doc-layer pin was dropped 2026-06-26; the as-of is the anchoring position (inv 5).
    Every SEL event still pins; the structural floor rides the serial-1 event, never a document field.)* Lifecycle: a
    cred is **incept-and-sit** — `{Icp, Pin}` (the `Pin` floors; issued, then sits) → optional `Trm`; a multi-party-doc
    leg is the same shape (endorse `{Icp, Pin}`, edit later). The non-`Pin` inception is one that **carries a first
    event** — e.g. `{Icp, Trm}` (a rescission). A **cred is exactly the first shape**.
    - **Addressing + privacy (F2 / F3, inv 16):** the cred-SEL is referenced **by prefix only** — logs are never
      looked up by SAID, and the `said(v1)` in the issuer IEL's `anchors[]` is an **opaque commitment** (`said(Icp)
      == v1.previous`, one hop back; neither inverts to the prefix). A **private** cred's **body is not published** to the shared store (issuer/holder-held,
      disclosed peer-to-peer); a **public** cred's body is published (discoverable by design). The cred-SEL *events*
      (`Icp`/`Trm`) **are witnessed** — under the **owner IEL's** witness-config (inherited; single-owner, like its federation context — D1 2026-06-28) — so revocation is multi-source-confirmable — but prefix-addressed, so only a
      holder (who derives the prefix from the cred) or a party it's disclosed to can find them. Residual: the public
      IEL leaks issuance volume/timing ("at most correlate").
  - **Lookup SEL** (rescission, any blind-recomputed locus): `data` *is* the recompute input (e.g. `data=P`). The
    `Icp` can't carry a pin either — the same recompute constraint, now a **universal** rule, not lookup-specific —
    so the lookup-SEL is `{Icp, Trm}` — the **`Trm` is the kill**, carrying the `pin` (uniform — every event pins)
    **plus `manifest.bound`** (the last honoured event on P's delegated chain). **Count = `t_authorize`**
    (symmetric inverse of `Ath`'s grant). **Always sealed:** the `Trm` is **IEL-`Dth`-anchored** (`t_authorize`)
    (the `Dth`'s `manifest.anchors` names the `Trm`), sealed on arrival — a rescission is a **kill**, monotone, so
    there is **no delayed un-rescind**. Restoring a delegate is a **fresh grant**, never a retraction. Protected by
    **owner-rooting**, not entropy. *(Archived events are still exposed for repair-archived content — see vdtid
    §5 — but no longer as an un-rescind mechanism.)*

### The three axes — never conflate them (count⊥tier kept; delayed-`Trm` reversed 2026-06-21)
1. **Count** = how many owner-IEL members must authorize (delivered via the **anchoring IEL event's** signatures):
   `t_use` (content / issue) · `t_govern` (terminate / revoke / close) · `t_authorize` (grant / rescind a delegate or doc-member) ·
   `t_recover` (repair).
2. **Tier** = is the **reserve** required? (the rotation/recovery preimage held *apart* from the signing key) —
   **T1** = signing key only (**content only**) · **T2** = + rotation reserve (establishment-mutation /
   authority-grant / **any kill** — a kill must be *sealed*, and a seal is a governance act) · **T3** = + recovery
   reserve (repair / identity-kill). Set by **danger-of-forgery OR need-for-permanence**, **⊥ count** — count is a
   dial, tier is set by kind (a content `Ixn` is T1 even at a high `t_use`).
3. **Anchor → finality follows the KIND (2026-06-21)**: a content **`Ixn`** rides an IEL **`Ixn`** → **delayed /
   repairable** (the **only divergeable kind** — an unsealed window is fine, content is repairable anyway); a
   **kill** (`Trm`) rides an IEL **`Rev`/`Dth`** → **sealed on arrival** (it *must* be — a kill is
   monotone). **There is no delayed kill.** The anchor **kind** matches the event kind (kind-strict, inv 4); tier-elevation is then a trivial floor, not the check. *(The round-3 `content: user |
   governing` flag is **removed** — its only intended user was the federation clock, which is **not a SEL kind**:
   it's an **inline timestamp on each federation `Wit`'s manifest** (federation §1f). `Ixn` is plain content. Finding 8/9.)*

### Exhaustive taxonomy

  | SEL kind | Count | Tier | Anchored by (IEL) | Finality | |
  |---|---|---|---|---|---|
  | `Icp` | `t_use` | **T1** | — (not anchored; v1 via `previous`) | delayed | `owner` (the owner IEL prefix, immutable) + `topic` + `data` (opt — the cred SAID for a cred-SEL); **no manifest, no `pin`** (stays recomputable for lookup). Establishes the SEL; the pin rides the batched serial-1 `Pin`. |
  | `Ixn` (content) | `t_use` | T1 | `Ixn` | delayed | content SAD(s) + re-`pin`; **≤1 per SEL per IEL `Ixn`**; the **only divergeable / repairable kind**. |
  | `Trm` | **`t_govern`** (revoke) · **`t_authorize`** (rescind) | **T2** (identity-kill → T3) | **`Rev`** (`t_govern`) / **`Dth`** (`t_authorize`) | **sealed on arrival** | The SEL **kill** (the kill-anchor's `manifest.anchors` names the `Trm`). `Rev` = cred revocation / closure; `Dth` = a delegation **or doc-membership** **rescission** (lookup-SEL `{Icp, Trm}`; the `Trm` carries `manifest.bound`). **Always sealed** — monotone, terminal-on-divergence (can't be repaired-away **F-B** / un-done **LF1**). The killed thing = which SEL its `Trm` extends. |
  | `Gnt` (grant) | `t_authorize` | **T2** | **`Ath`** | **sealed on arrival** | The doc-governance **grant** — the **additive twin of `Trm`** (opens editor/commenter validity periods; the `Gnt`'s `manifest` names the gated grant-doc `G`). Anchored by the owner IEL's **`Ath`** (kind-strict — an `Ath` anchors **only** `Gnt`s). Privileged / seal-advancing, **non-archivable** — walked back by a rescission (a SEL `Trm` via `Dth`, or reincept), never a repair. Doc-governance SELs only (a plain SEL has no membership). |
  | `Pin` (floor re-pin) | `t_use` | **T1** | `Ixn` | delayed | Re-pins the SEL→owner-IEL floor, carrying only the top-level `pin` (no manifest/seal/fold). The **fallback serial-1 floor** — used only when inception batches no other event (the `Icp` can't hold a pin). **Not** seal-advancing — promotes nothing; repairable like content. |
  | `Fld` (re-seal) | `t_govern` | **T2** | `Evl` | sealed | The SEL **fold** — a *pure re-seal* (KEL `Rot` / IEL re-seal-`Evl` analog). Carries `previousSeal` (no `folds` — non-repair; the run `[previousSeal..previous]` is derivable), caps the content run for page-atomic repair, promotes below-fold content to durable. **Privileged, seal-advancing.** Rides an owner IEL `Evl` (a SEL fold lands at an IEL fold boundary). |
  | `Rpr` | `t_recover` | T3 | `Rpr` | (atomic repair batch) | divergence repair; owner-authorized; bottom-up cascade. |

- **Imposes on the IEL side:** an IEL **`Ixn`** anchors a SEL's **serial-1 (v1) event** (a `Pin` for issue-and-sit,
  the first content `Ixn` otherwise) via `manifest.anchors` — the **`Icp` is never anchored**, it rides via
  `v1.previous`; a SEL **kill** is anchored by an IEL **`Rev`/`Dth`** via `manifest.anchors` —
  a cred-SEL `Trm` by a `Rev` (`t_govern`), a rescission lookup-SEL `Trm` by a `Dth` (`t_authorize`), sealed. **The kill rides
  a `Rev`/`Dth` because the back-check demands it** (a SEL `Trm` is valid only anchored by a `Rev`/`Dth` — inv 4), not
  a role label. So **content rides the IEL `Ixn` rail; kills ride the IEL `Rev`/`Dth` rail** (roster/threshold changes ride
  `Evl`). **The matrix is kind-strict (C1):** a `Rev`/`Dth` anchors **only** `Trm`s, an `Ath` **only** `Gnt`s, an `Ixn` **only** content/v1, an
  `Evl` **only** `Fld`s, an `Rpr` **only** `Rpr`s — tier-elevation is an *additional* floor, not the check (else a
  T2 `Rev`/`Dth` could host T1 content onto the durable rail — inv 4). The IEL `Ixn` stays **T1**, the `Rev`/`Dth` is **T2** — count ⊥ tier still holds. *(The federation clock is not
  an SEL event at all — it's an inline timestamp on each federation `Wit`'s manifest; federation §1f.)*
- **The SEL seals itself via `Fld`; trust-finality floors to the owner IEL.** A content `Ixn` sits in the SEL's
  unsealed window until the SEL's next **`Fld`** (the re-seal, riding an owner IEL `Evl`) — then permanent (and
  repairable until then); `Fld`/`Rpr`/`Trm` are the SEL's seal-advancers (`previousSeal`; a repair `Rpr` also carries `fork` — the single losing-branch root, inv 4). The SEL's
  **trust-finality** additionally floors to the owner IEL's seal via its `pin` (it holds no trust-seal of its own).
  A **kill** is **`Rev`/`Dth`-anchored → sealed on arrival**, owner-proof immediately and terminal-on-divergence.
  **There is no delayed kill.**
- **Divergence resolution — the archival-tail rule** [inv 13]: **content `Ixn` and the floor `Pin` are
  archivable** (both T1); a repair (`Rpr`) attaches at **your last event**, retaining your branch and archiving the
  **archival tail(s)**; **permitted iff no archival tail holds a privileged event** (a `Fld`/`Trm`/`Rpr` — the
  seal-advancing SEL kinds — never overturned) — else → reincept. Node-agnostic, **data-local** condition: **≥ 2 retained branches each carrying a
  privileged event past the fork → irreconcilable/disputed** (any verifier walks it — inv 13/17; the beacon
  propagates the branches, it does not decide). E.g. `{Trm, Ixn}` → the `Trm` is the single privileged branch, so it **wins on tier-rank with no `Rpr` authored**
  (a terminal `Trm` admits no successor to carry one): the kill stands, the content is archived non-canonical. The
  `Rpr`-attaches-at-your-last-event form applies only when the retained tip is **privileged-but-not-terminal**
  (`Fld`/`Rot`/`Evl`); to both resolve a content fork **and** kill, a `Trm` on the winning branch does both in one
  event (it buries the content loser via the seal-cap and terminates); a repair-first is only for an explicit
  condemnation record. An adversary's `Trm` in an archival tail → reincept.
- **Cross-layer anchor rules — the IEL is the SEL's clock (2026-07-01, closes cold F1).** A SEL is anchored to its
  owner IEL (kind-strict — content `Ixn` ↔ IEL `Ixn`, etc.). Two rules govern the cross-layer:
  - **Anchor-monotonicity** — a SEL event is valid **only if it extends its SEL's latest IEL-anchored tip** (computed
    over the **canonical/retained IEL walk**). The check runs at SEL-validation over the anchors a node can
    **attribute** (holds the body for); the anchor SAID is *opaque* (inv 16), so an anchor whose body a node lacks is
    **skipped, not blocking** (*skip-unattributable* — else a withheld/lost/private body would wedge the SEL). A
    re-anchor at an already-attributed serial is **malformed → inert** (the carrying IEL event stays valid; an inert
    anchor never advances the tip). So a node extends each SEL it can attribute correctly.
  - **Cross-layer deadness-descends** — a SEL event whose anchoring IEL event is dead (condemned / below-seal-inert)
    is itself dead (the **IEL→SEL** anchor edge only — not KEL→IEL, which is forward-only).
  **Content-fork prevention rides the theorem transitively (2026-07-02):** a witnessed SEL content fork would force
  its two same-serial siblings to anchor at IEL content siblings at one IEL position — which the majority floor +
  option (b) prevent on the witnessed owner IEL (federation §1e / inv 4) — so a witnessed SEL content fork carries
  the **same fork-cost** and needs **no SEL-local witness gate**; the residual (direct-mode / witness-compromise /
  roster-delta straddle) is the IEL's residual inherited.
  These give the theorem *a valid SEL fork implies an IEL fork beneath it*: a SEL **never forks under a linear IEL**
  (no unrepairable deadlock — skip-unattributable prevents the wedge; cold-r5 F2's transient withheld-body split
  auto-resolves by seal order),
  and every genuine SEL fork rides an IEL `Rpr` (condemning the losing IEL branch → its SEL events die by descent —
  and cascade-anchoring the SEL `Rpr` for the retained branch). A **signing-key (T1) compromise is fully deadenable**:
  no reserve → no privileged SEL `Trm` (needs a `Rev`/`Dth`) → one recovery `Rpr` archives the whole tail (all content) →
  every anchored SEL event dead by descent, no reincept. The benign residual (two owner devices racing) is inert by
  anchor-monotonicity; serialize the content rail (area-iel §5) as the operator answer.

## 2. Superseded — do NOT carry (from design-pass §3)
- **"Every SEL is `Icp`+`Evl`"** → **lookup-SELs** are `Icp` + `Trm` (the rescission kill); content/cred SELs are `Icp` + a serial-1 event (the first `Ixn`, or a bare `Pin` when incept-and-sit) + `Ixn`s. The serial-1-event floor is universal; the old SEL `Evl` / rescission-`Pin` is gone.
- **"No SEL `Trm`; soft-close only"** → SEL **`Trm`** is back — **`t_govern` count, T2, always sealed (via `Rev`/`Dth`)** =
  revoke/close. The removal was premised on a *tier-3*-anchor problem that the **count⊥tier** decoupling sidesteps.
  *(The "T2, sealed-on-arrival via a dedicated kill-anchor" framing was right all along; the F3 **delayed-`Trm`** was the error and
  is **reversed** 2026-06-21 — a kill is monotone, so it can't be unsealed.)*
- **Registry SEL / registry identifier** → gone; each cred is its own SEL, addressed by `derive(...)`.

## 3. Requirements satisfied / imposed
- Satisfies **R1** (no policy on the SEL — auth is the owner IEL's structural threshold), **R2** (SEL
  verification must be tokenizable — position-addressable), **R3** (a `pin` to a SEL position yields the state
  token + committed-anchor proof).
- **Imposes on the IEL:** the IEL anchors (a) a content SEL's **v1** (a serial-1 `Pin`, or the first content `Ixn`) via an IEL `Ixn` (`t_use`, ≤1/SEL —
  cred-SEL **v1**s (the serial-1 `Pin`) **batch** under one IEL `Ixn` via `manifest.anchors[]` — the `Icp` rides `v1.previous`, never anchored — inv 4), (b) a
  lookup `Icp` + its `Trm` (rescission kill) via an IEL `Dth` (sealed), (c) a cred-SEL `Trm` (kill) via an IEL
  `Rev` (sealed), (d) a SEL `Fld` (re-seal) via an IEL `Evl`'s `anchors` (symmetric with the IEL `Rpr`
  anchoring a SEL `Rpr`), (e) a doc-governance **`Gnt`** (grant) via an IEL **`Ath`**@`authorize` (sealed — the
  additive twin of the `Dth`-rescission). **Kills ride the IEL `Rev`/`Dth` rail; grants the IEL `Ath` rail; content the
  IEL `Ixn` rail; a SEL `Fld` the IEL `Evl` rail; a SEL `Rpr` the IEL `Rpr` rail.**
- **Count travels with the anchored event's KIND — re-scoped: every IEL kind prices itself (Jason 2026-06-20/21).**
  The required count for an anchored SEL event is set by **its kind** (`t_use` content · `t_govern` `Trm`-kill ·
  `t_authorize` `Gnt` grant / lookup-SEL `Trm` rescind) and checked as a **parameter of the anchor-verification call**: when the walk
  resolves the anchor it already holds both the anchored event (kind ⇒ required count) and the anchoring IEL event
  (counts its sigs), so it checks in one pass. Content rides an IEL `Ixn` (T1); a kill rides an IEL **`Rev`/`Dth`** (T2,
  sealed), whose kind (`Rev` = `t_govern`, `Dth` = `t_authorize`) names the count — **backed** by the kill-anchor's own
  sigs and **demanded** by the anchored kill's kind. **Re-scoped (2026-06-21):** the rule is safe because **every
  IEL kind does exactly one job** ([inv 12]); the old IEL `Evl`-anchors-a-kill conflation (a roster change riding
  at a kill's count, **S1**) is gone — `Evl` is roster-only. *(IEL + vdtid-services notes to absorb.)*

## 4. Open / for the adversarial pass
- **`Pin` (re-pin) vs `Fld` (fold) — SEPARATED (Jason 2026-06-27, post-review).** Making one `Pin` both `t_use`/T1
  *and* seal-advancing broke the tier model: a reserve-less `t_use` compromise could forge content + a seal-advancing
  `Pin` and self-promote it to consumer-trusted (cold C1 / warm blocker). Fix — **split the two jobs:**
  - **`Pin`** = the floor re-pin (`t_use`/**T1**): carries only the top-level `pin`, **not** seal-advancing, promotes
    nothing, repairable. Job = the **fallback** serial-1 floor (when inception batches no other event; the `Icp` can't
    hold a pin). Each content `Ixn` re-pins itself, so a `Pin` is needed only for an incept-and-sit SEL.
  - **`Fld`** = the pure re-seal (`t_govern`/**T2**, privileged, seal-advancing): carries `previousSeal` (no `folds` — `Fld` is non-repair),
    caps the content run so a SEL divergence repair stays page-atomic, promotes below-fold content to durable. The
    SEL's analog of KEL `Rot` / IEL re-seal-`Evl` — *pure* fold because a SEL has no roster/keys to ride it on.
  This keeps **"seal-advancing ⇒ privileged"** intact (the `Pin` simply isn't seal-advancing) — **no** inv 13/17
  carve-out. SEL seal-advancers = **`Fld`/`Trm`/`Rpr`**; tier-1/archivable = `Ixn`/`Pin`. A **rescission** is a terminal
  **`Trm`** (`t_authorize`, T2, sealed, carries the `bound`) — not a `Pin`/`Fld`.
- **The `Fld`'s IEL anchor = IEL `Evl` — RESOLVED (Jason 2026-06-27).** A SEL `Fld` rides an owner **IEL `Evl`** — a
  SEL fold lands at one of the IEL's own fold boundaries (which T2 implies, and is sensible: that's where the IEL
  folds too). A busy SEL re-seals when its owner authors an IEL `Evl` (incl. a roster-less re-seal one).
- **Page boundary is needed on the SEL too — NOT transitive (Jason 2026-06-27).** "≤1 content `Ixn` per SEL per IEL
  `Ixn`" bounds the *rate*, not the *total*: a SEL accumulates one event per anchoring IEL `Ixn` across as many IEL
  seal-windows as it lives, and the IEL's own re-seal doesn't fold the SEL's chain. So the SEL must fold itself (`Fld`);
  "just don't fold the SEL" was a rejected carve-out.
- **Cred body `pin` — DROPPED (Jason 2026-06-26).** The body `pin` and the structural serial-1 `Pin` encoded the
  same issuer-IEL position at two layers; the body copy was redundant (the as-of is the **anchoring position**, inv 5,
  not a self-asserted value). So the cred body carries **no `pin`**; the SEL still floors structurally via its `Pin`
  event, and the doc-layer as-of is read from the anchoring `IEL Ixn`. Propagated to documents.md / protocol-doctrine /
  inv 5 / inv 15.
- **Naming — RESOLVED (Finding 12; refined 2026-06-27):** the SEL **floor re-pin** kind is **`Pin`** (carries only
  the `pin`); the SEL **re-seal** is the **`Fld`** (the IEL `Evl` analog); the rescission `bound` rides the rescission
  **`Trm`**. The old SEL `Evl` is fully retired — its jobs split into `Pin` (pin) + `Fld` (fold). Cross-layer `Trm` (KEL/SEL/IEL) is **not**
  renamed (same act at three layers) — the docs just **qualify it by layer** (`KEL-Trm` / `SEL-Trm` / `IEL-Trm`).
- **Field placement + public-cred uniqueness — RESOLVED (G4, refined 2026-06-21).** **`data` = the credential's
  SAID** (`said(cred body)`); the body holds `pin` + (`nonce` if private). Because `data` is the SAID over the
  **whole** body, **any two non-identical creds get distinct prefixes** automatically — `derive(issuer, topic,
  data)` differs whenever *any* body field differs (`claims`, `policy`, `issuee`, `expires`, `pin`, `nonce`). So the
  public-cred collision is closed **by construction**: two public creds with the same `claims` but a different
  `policy` have different SADs → different `data` → different prefixes; only **byte-identical** creds share a prefix
  → **dedup** (content-addressed, idempotent submit). *(This subsumes the round-4 `data = {pin, body-digest}` fix —
  `data` is now the full-body SAID, i.e. the body-digest taken to its limit, with the `pin` riding inside the body
  rather than beside it.)* Private creds get unpredictability from the `nonce`-in-body.
- **Lookup-SEL rescission = `{Icp, Trm}` — RESOLVED (Jason 2026-06-26).** The rescission's terminal event **is** a
  `Trm` (a kill — `Trm` is the kill kind; symmetric with cred revocation: both → a SEL `Trm` under a kill-anchor, differing
  only by kind — a `Rev` for the revocation, a `Dth` for the rescission). Sealed on arrival, monotone — you never un-rescind (restoring a delegate is a **fresh grant**). The
  `Trm` carries the `bound`; the `Dth` names it via `manifest.anchors`. *(Supersedes the earlier "no `Trm` needed,
  the pin-carrier is the kill" — the kill is now correctly a `Trm`; the `Pin` is the floor re-pin and the SEL re-seal is the `Fld`.)*
- **Content `Icp` collision/divergence — RESOLVED (2026-06-20): rests on the high-entropy-`data` rule (§1).**
  "Collision needs a Blake3 preimage → no" is **insufficient alone** — it silently assumes high-entropy `data`.
  With low-entropy/predictable `data` the prefix is guessable and collision/camping/de-anon reopen. The actual
  guarantee is the **`data`-entropy rule** (§1) for unpredictable prefixes **+ owner-rooting** for discoverable ones.

## 5. Drift → land backlog
- **Reconcile design-pass §3** (+ the §2.2 SEL-inception row) to this note (the `Icp`+`Evl`-always + no-`Trm`
  claims). §2.1's `≤1 Ixn` rule is unchanged.
- Write `docs/design/primitives/data/event-logs/sel/` fresh from this note.

## 6. Confidence
- §1 — high (direct consequence of `inv 15` + the document-layer decisions, which Jason drove this session).
- §4 — the field-placement + repair-window items are detail for the adversarial pass; not load-bearing blockers.
