# vdti — design invariants (load-bearing, cross-cutting)

**Status: FIRST CUT, partially adjudicated (2026-06-20).** Sourced from the post-reshape authoritative core
(`vdti-log-primitive-reshape-design-pass.md`) + decisions settled this session. These cross-cutting rules
constrain all reasoning; every area note references them. Tags: `[locked]` = adjudicated with Jason;
`[locked-candidate]` = I believe settled, needs confirm; `[planned]` = agreed direction, not built;
`[needs-reconciliation]` = real but must be reconciled to the reshape.

## Structure & control
1. **Policy lives on documents, never on log primitives.** KEL/IEL/SEL carry no policy; policy lives on
   cred/content documents, matched at the application. *Why:* removes the issuer-chosen-marker backdate surface
   from the chain primitives entirely. *Src:* design-pass §1, §6. `[locked-candidate]`
2. **Single locus of control per primitive.** KEL = a device's keys; IEL = one identity (a threshold over member
   KELs); SEL = one owner's data log. No primitive composes a multi-party policy internally. *Src:* §1.
   `[locked-candidate]`
3. **Layers isolated, one direction.** KEL → IEL → SEL; an event pins down to the layer directly beneath it and
   anchors up to the layer directly above it — only ever the adjacent layer. Never anchor a SEL event in a KEL. *Why:* bounds blast radius; keeps the verification walk acyclic. *Src:* §1,
   §2. `[locked-candidate]`

## Binding & ordering
4. **Manifest-up + pin-down.** An event commits to the layer above via a `manifest` (a SAD); the higher event
   pins down to its owner's current tip. **A manifest *groups what the event commits to, by named role* (2026-06-21):**
   `{ said, <role>: <said-or-list-or-scalar>, … }`. Roles read as **"the things this event {anchors / roster / delegates / …}."**
   **Read kind-first, never label-first (F1, 2026-06-21):** each event kind has a **closed role vocabulary**
   (`allowed(kind)`); a manifest carrying any role outside it is **malformed → rejected**, and a role is consumed
   *only* after dispatching on a kind permitted to carry it — the label is checked against the kind, never trusted
   on its own. (The manifest SAID commits the labels — JCS over the keys — so a third party can't *relabel* a fixed
   event; the allowlist closes *author*-mislabel of the **directly-consumed** roles, which would otherwise let an
   `Ixn` carry `roster`/`delegates` and govern/grant at `t_use`, reopening **S1**. Killing at `t_use` is closed
   separately by the **back-check** (a SEL `Trm` demands an IEL `Rev` or `Dth`), not the allowlist.)

   **The `kind` string (Jason 2026-07-12):** a `/`-delimited namespaced discriminator
   `vdti/<concept>/v1/<category>/<thing>`, **capped ≤ 64 chars** (a DoS bound — the verifier rejects a
   longer `kind`). **Grant-values** — what a `Gnt`'s `manifest.grant` names — are kinded under
   **`vdti/sel/v1/grants/*`**, owner-first (a feature or a stateful primitive) so grants sort by owner
   (`directory-ml-kem-1024`, `shared-document-governance`; area-sel §1b). `[locked]`
   **The principle (Jason, 2026-06-21):**
   - **Top-level structural = the event's *own* links:** `said`, `previous`, **`previousSeal`** (seal-advancing
     events only — the back-link to the prior seal that renders the spine; inv 17), **`pin`** (a SEL's down-pin to
     its owner IEL event — a scalar SAID), **`pins`** (an IEL's down-pins to its member KEL **tips** — the event each fresh participation *extends*
     (`participation.previous`), exactly the SEL `pin → anchor.previous` analog, so the IEL's own `said` never
     depends on the participation events that anchor it (no SAID cycle — cold-3 B1); a *list*, so
     carried as a scalar SAID → a small **pins-SAD**, never an inline field — a roster-add federation `Wit`'s pins
     are each participant's `participation.previous`: the **approvers' `Wit.previous`** (the pre-rotation witness KEL
     tip SAIDs — the clock's `T_end` for the retiring receipt key + the cold-F7 commitment distinguishing an honored
     synchronized rotation from an off-ceremony `Rot`) **plus, on a roster-add, the joiner's `Ixn.previous`** (a
     `T_join` for the joining key, never a `T_end` — else the new witness bricks at birth, cold-7 F2)),
     `federationPin`, `manifest`, the federation `prefix`.
     *(Why top-level: these are the chain's own structural links — a verifier walks the layered structure from them
     **without fetching the manifest**; the manifest carries content commitments, looked up on demand. `pins`/`pin`
     are encoded in `event-shape.md` (landed with the IEL/SEL/federation doctrine). `sealPins`, a
     seal-level analog, was considered and dropped — it only reached the terminal-divergence view, which the flat walk
     subsumes, inv 17.)*
   - **Manifest (role-labeled) = everything it *commits to above*:** anchored higher-layer **event SAIDs** *and*
     **documents** (SADs). Entities are named by **prefix** (inv 7); events/positions and documents by **SAID**.
   **Role vocabulary:**
   - `anchors` — higher-layer SAD / event SAIDs this event commits to above. **Carried by** KEL `Ixn` (required, ≥ 1) /
     `Rot` / `Wit` (the KEL `Wit` anchors the IEL `Wit` — uniformly, user binding **and** federation governance; see the KEL→IEL kind-strict rule below) and IEL `Ixn` / `Ath` / `Rev` / `Dth` / `Evl` (optional on the non-`Ixn` kinds — a rotation
     commits the events it realizes; an IEL `Ath` commits the SEL `Gnt`(s) it seals, an IEL `Rev`/`Dth` the SEL `Trm`(s) it seals, and an IEL `Evl` the SEL `Sea`(s) it anchors — the burying-seal recovery, area-sel §1d). **Subsumes the former
     `issues`/`revokes`/`rescinds` (2026-06-27):** those were **credential / feature vocabulary on a log primitive**
     (inv 1 — features live on documents, never on primitives). The IEL is now **feature-blind** — it anchors a lower
     SEL event or SAD; **the feature layer names it** (an anchored **issuance commitment
     `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** on an IEL `Ixn` *is* an issuance — no cred-SEL,
     2026-07-09; a revocation lookup-SEL `Trm` on a `Rev` *is* a revocation, with the `Rev`'s `kills[]` naming the
     target; a lookup-SEL `Trm` on a `Dth` *is* a rescission). The discrimination was never the label (this
     invariant's own "never trust the label alone") — it is the **back-check** (below) plus, for the kill
     *declaration*, the kind-strict `kills` role. *(A bare issuance commitment is a **flat hash with no event behind
     it** — so it is **not** IEL-kind-back-checked; its validity is by-anchor-existence at the cred feature layer,
     R5/R1.)*
   - `roster` — the roster/threshold (delta) SAD (IEL `Icp`/`Evl` (user) + `Fcp`/`Wit` (federation) — the federation's `Wit` carries its roster delta + `clock` — its **`add` is a *single* prefix** (one witness per `Wit`, except `Fcp` inception; `cut` stays a list — cold-seam P5, 2026-07-02: ≤ 1 unsynced witness per transition can't reach a majority `threshold`, closing the multi-add straddle); E1, 2026-06-28. **Eviction rides a user `Evl` carrying a `cut`** (first-seen — there is no `Rpr`; an urgent eviction is an ordinary `Evl` with a required non-empty `cut`, an `add` rides a later `Evl`; priced the outgoing `t_govern`, the post-cut roster re-checked against the inv 12 bounds — the security floor, the recoverability ceiling, the authorization floor, the roster cap `MAXIMUM_ROSTER_SIZE`, and the roster-floor `|roster| ≥ 1`). *(`pins`/`pin` are **not** manifest roles —
     they are **top-level structural**, see the principle above; relocated 2026-06-25 from Jason's model.)*
   - `clock` — an **inline timestamp value** (a UTC RFC3339 µs string — the lone non-SAID role; nothing dereferences it by SAID, so no nested SAD); **federation `Fcp`/`Wit`/`Trm`** (the federation clock — inv 14 / federation §1f; carried by the genesis `Fcp`, every governance `Wit`, **and the terminal `Trm`** — cold-4 B1 + cold-14 F1, so an all-windows-lapsed federation can still terminate; the federation has no `Evl`). **A single authoritative value on the federation IEL `Wit`** (not matched/synced across members — Q3), constrained only **monotonic** vs the prior federation clock + **`≤ now + CLOCK_TOLERANCE_BAND`** (§1f). *(No ordering against member KELs — KELs are timestamp-free, inv 6; the earlier "ahead of member KELs" framing was a category error — F2, dropped 2026-06-29.)* *(The witness currency gate is **exact-tip, no grace window** — a `graceSeconds` forgiveness window was considered and dropped 2026-06-24 as redundant + a backdate sliver; see federation §1e.)*
   - `witnesses` — the witness-config `{threshold, signers}` SAD (KEL `Icp`/`Wit` **+ user IEL `Icp`/`Wit` + federation IEL `Fcp`/`Wit`** — D1, 2026-06-28). **Mandatory iff federated *at inception*** (`Icp` / federation IEL `Fcp`): a federated `Icp`/`Fcp` omitting it is **malformed → rejected, fail-secure**; **forbidden** on `Fcp`-pre-federation KEL inception — cold-7 F3. **On a `Wit` it is present-iff-changed (`opt`)** — the same delta discipline as `roster`/`threshold`/`federationPin`: a `Wit` re-states the config **only when it changes it** (the rotation itself — `pins` / key-state always advancing — is the non-empty change; otherwise inherited), and when present on a federation-governance `Wit` it **field-matches** the anchoring KEL `Wit`s (Q3 — the KEL carries, the IEL matches; never derive IEL-from-KEL). An **IEL event is witnessed too** — it could otherwise fork without *any* member KEL forking (two disjoint sub-quorums each author a valid event at one position → the IEL diverges, no KEL does — closed by the option-(b) position gate below, which is now **universal** (every event, content _or_ sealed; revised 2026-07-11) — a competing sealed sibling is declined first-seen too, so `{Evl, Evl}` no longer diverges on an honest split; only a witness-colluded double-sign yields `disputed`), and its effective-SAID is in the F-E transitive freshness set ([inv 8]); so the IEL carries its **own authoritative** witness-config for its events, **independent of every member KEL's** (a member's config witnesses that member's KEL events) — the same anti-straddle reasoning as the federation binding (cold-3 B2), **not** a match across members. The **federation IEL carries its own config too** (on `Fcp`/`Wit`, adjusted at each governance `Wit` — resolves cold-7 F1 / option b). *(No contradiction with the governance-facet field-match — C1, cold-9/10: "independent / not matched" scopes a member KEL's **own KEL-event config** (different chains); the federation-governance `Wit↔Wit` field-match is on the **federation config the approvers jointly endorse** — a consensus vote, area-iel:32 — i.e. the federation IEL's own config, not a member's.)* A **SEL inherits** its owner IEL's config (single-owner — nothing to declare, like the federation binding it already inherits). **How an IEL event is "witnessed" — self-attestation (Q1, Jason 2026-06-29):** an IEL has no signing key of its own (it is a *threshold over member KELs*), so an IEL event's witnessing **is** the witnessing of its **member KEL anchors** — the event is trusted when the member KEL anchors that authorize it are witnessed — concretely, the IEL event's own authorization count (inv 12: `t_use`/`t_govern`/… by kind) of its anchoring member KEL events are **each** witnessed at the witness-config `threshold`. **Two distinct counts (cold-9 Q1):** the IEL event's authorization count = *how many* anchoring KEL events must be witnessed; the witness-config `threshold` = *how many receipts* each one needs. IEL events still propagate + earn receipts **as per usual**. **Authorization** stays the witnessed KEL anchors (Q1); **fork-prevention** adds a second gate — **option (b), 2026-07-02, universalized 2026-07-11: a *user* IEL's events — content _and_ sealed — must also reach a majority quorum at their own `(IEL prefix, serial)`** (the same first-seen position gate as a KEL — federation §1e), closing the two-disjoint-sub-quorums fork; a competing **sealed** sibling (`{Evl, Evl}`, …) is declined first-seen too, so an honest split can't diverge — only a witness-colluded double-sign yields `disputed`. The **federation IEL realizes the position gate through exclude-self peer-witnessing** (a governance event needs a peer majority first-seen at its serial → a competing sibling declined): its member witness-KELs witness **each other's** KEL events **exclude-self** (a witness never receipts its own KEL event), pool **`|roster| − 1`** — so for federation member events `signers/2 < threshold ≤ min(|roster| − 2, signers − 1)` and `threshold ≤ signers ≤ |roster| − 1`; a user chain stays `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|` (external witnesses, no self-exclusion). **A structural witnessing floor `threshold > signers/2`** (a strict majority of the *selected* witnesses) makes two conflicting **content** siblings un-co-witnessable (sealed siblings are first-seen too now — one per position; a second *accepted* sealed branch needs `2·threshold − signers` colluding double-signers → `disputed`, provable — revised 2026-07-11, federation §1e) — with the option-(b) position gate — **universal** (every event) — closing the *partition / disjoint-sub-quorum* fork that otherwise lets an IEL diverge with no member KEL forking (a competing `{Evl, Evl}` is declined first-seen too; only witness collusion yields `disputed`); **fork-cost = `2·threshold − signers`** (own the whole quorum intersection), and a sub-majority config is **un-usable → rejected** (every config clears `signers ≥ 3` + the witnessing floor, federation §1e). **The recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)` (cold-9 B1 + F6, verifier-rejects higher)** is the direct analog of `t_govern`'s gratuitous-hostage rejection (inv 12): an eviction/recovery `Wit` is authored by the remaining members but must also **self-attest**, and the evicted/dead member won't co-witness — so the self-attest pool is `|roster| − 2`, and at **sub-pool selection** (`signers < |roster|`) the *selected* pool loses one too, so `threshold ≤ signers − 1` binds as well (the `|roster| − 2` leg is exact only at full-pool selection; with `signers ≥ 3` the `signers − 1` leg is `≥ 2` and always binds cleanly (no waiver, no `threshold ≤ 0` degenerate); the guaranteed evict-one begins at the `|roster| = 4` structural floor `{2, 3}` — federation §1e); capping `threshold` there guarantees the federation can always **evict one** compromised witness and get the cut trusted (the guarantee is *evict-one*; surviving `k` simultaneous unavailable members needs `threshold ≤ |roster| − 1 − k`, the operator's sizing choice — cold-10 F1 / federation §1c/§1e). The cap is **federation-only** (a user IEL's anchors are witnessed by the **external** federation pool, no self-exclusion, so evicting a user's member never shrinks it). At the `|roster| = 4` structural floor the minimal config is **`{threshold 2, signers 3}`** (fork-cost 1); `signers ≥ 3` gives real witnessing byzantine-tolerance — no forced lone-witness — and the `≥ 5` operator doctrine lifts the fork-cost dial (cold-10 F2); **the structural floor is `≥ 4`** (`≥ 5` recommended, a consequence of `signers ≥ 3`); a **config change** is **re-checked on the post-delta config** (inv 12 — any `Wit` changing roster/`threshold`/`signers`) — valid only if the **full cap `threshold ≤ min(|roster| − 2, signers − 1)`** **and the witnessing floor `threshold > signers/2`** hold after the change (the roster leg alone is the *slack* leg for `signers ≥ 2` — cold-seam F1), so a bare shrink that would strand the federation un-recoverable is rejected, forcing **evict-and-replace** or a simultaneous threshold-and-`signers` drop (a `threshold` drop to 1 forces `signers` to 1 — else sub-majority) — cold-13 F1). A **`Wit`'s own self-attestation is judged under the at-or-before witness-config + roster** (no self-weakening), **but under the NEW key-windows the rotation establishes** (the fresh keys its anchoring KEL `Wit`s reveal, F4-bounded — not the possibly-expired old windows; the clock axis is carved out of no-self-weakening — cold-11). So an all-windows-lapsed federation reads stale (fail-secure) then recovers via a catch-up rotation — never bricked; and a lone broken key still can't mint a current window (a rotation is honored only as a federation `Wit`, needing `t_govern` + self-attestation — federation §1e/§1a). The federation `Wit` thus **never bricks** even when every witness participates — its trust rides its (cross-witnessed, exclude-self) KEL anchors, not an exclude-all-participants aggregate count. Divergence stays data-local-detectable: a federation `Wit` fork's competing branches are each anchored by witnessed KEL `Wit`s that propagate, surfaced by the keep-all-data walk (inv 17). *(Supersedes the `|roster| − |participants|` aggregate-gate framing — that bricked an all-witness rotation; cold-8 F1.)*
   - `delegates` — delegate **prefixes** (the delegate-list SAD) (IEL `Ath`, `delegates` role).
     *(The former `issues` / `revokes` / `rescinds` lists are now plain `anchors` entries — an anchored issuance
     commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` on an IEL `Ixn` (issuance — no cred-SEL,
     2026-07-09), revocation lookup-SEL `Trm`s on a `Rev`, lookup-SEL
     `Trm`s on a `Dth` — discriminated by the anchored event's kind, not a role label; the **kill declaration** rides
     the `kills` role (above), not `anchors`. A revocation/rescission lookup-SEL `{Icp, Trm}` is born under its
     `Rev`/`Dth`, the anchor's `anchors` naming the sealing `Trm`, reachable to its `Icp` via `Trm.previous`.)*
   - `kills` — carried by an IEL **`Rev`/`Dth`** (kind-strict): the **revocation/rescission declaration**, a flat
     list `[{ target, bound? }]` **alongside** `anchors[]` (two separate roles, two separate concepts — `anchors` =
     the sealed `Trm`'s *termination validity*, `kills` = *what is revoked*; a `Trm` anchored but in no `kills[]` is
     a terminated SEL that isn't a revocation, so there is **no coverage rule and no hole** — "not in any `kills[]`"
     *is* not-revoked). **`target = hash('{topic}:{owner}:{data}')`** — a flat, `:`-delimited, domain-qualified hash
     (distinct `topic` per kind: `CRED_REVOCATION_TOPIC` / `DLG_RSC_TOPIC` / `DOC_RSC_TOPIC`; `data` = the
     grant-instance), the fail-secure walk's forward-match handle. It is **≠ the lookup SEL's prefix and said**
     (the SEL is a separate two-pass over `Icp{owner, topic, data}`), so the public `kills[]` target does **not**
     reveal the object's address (inv 10 / inv 16). **`bound`** (rescission only) = the SAID of the **last valid
     (honoured) event** on the subject's chain — the inclusive grandfather boundary (honoured iff its anchoring
     position is an ancestor of the `bound`; the dial runs tip → inception). **One concept, two custody modes:** a
     **delegate** rescission's bound is not participant-identifying → the **inline-public `kills[].bound` field** (on
     the IEL `Rev`/`Dth`, un-withholdable); a **doc-member** rescission's bound *is* participant-identifying → the
     **gated `bound` manifest role on the SEL `Trm`** (the rescind-doc behind the read gate; `kills[]` carries only
     the blind target). **`kills` is OPAQUE to the IEL** — placement (kind-strict to the T2 `Rev`/`Dth`; a `kills` on
     a T1 `Ixn` is malformed) is the **only** structural rule; the IEL never dereferences a target or interprets a
     bound (all revocation/version-honored logic is the credential/doc feature layer). *(`kills` added 2026-07-09
     — B1 fail-secure rework; the gated-custody `bound` reads as a dedicated manifest role on the SEL `Trm` — WF1,
     2026-07-13 — the twin of the additive `grant` role, distinct from the inline `kills[].bound` field; renamed
     from "cut-off"/"terminator" 2026-06-26.)*
   - `grant` — the gated grant-doc SAD `G` a **SEL `Gnt`** commits (the editors/commenters + their `from`
     validity-period starts). The additive twin of the rescission `Trm`'s `bound`; back-checked (a `Gnt` is valid
     only anchored by an `Ath` — kind-strict), so unlike `payload` it is *not* a directly-consumed role.
   - `payload` — the payload SAD(s) a **SEL `Ixn`** records (single-owner data — e.g. an app/doc SEL amendment; a
     credential is **not** a SEL and has no payload `Ixn` — it is an immutable anchored SAD, 2026-07-09).
     **Required** on an `Ixn` — a SEL `Ixn` must commit ≥ 1 payload SAD (the role is never empty; a manifest-less
     `Ixn` is malformed, and a pure re-pin is a `Pin`, not a payload-less `Ixn`). A
     lookup-SEL `Icp` uses `data` (the derive input), **not** a manifest; only the `Ixn` carries this role.
     *(The first SEL-borne manifest role — later joined by `grant` and the `bound` role; added 2026-06-22 — inv 4
     had no SEL role, but a SEL `Ixn` must commit its payload SADs, and the principle puts documents in the
     manifest. The role was named `content` before 2026-07-13; renamed `payload` to free the `Icp` `content`
     type-flag — area-sel §1f.)*
   - *(The **`fork` role is DELETED (first-seen, 2026-07-08)** — there is no repair event, so nothing commits a
     losing-branch root. A content loser is buried **by position + ascent** (the burying seal-advancer's seal-cap
     locks its first event; **deadness ascends** to its growth — an event whose parent is dead is dead; each dead
     lineage ≤ `MAXIMUM_UNSEALED_RUN` past the last seal, breadth bounded by retention ≥ 2 per position + the one-content-sibling
     witnessing rule — inv 13/17), and a **sealed** loser at the last seal is never buried (≥ 2 **witnessed** sealed → `disputed`, can't bury a
     rotation; a **below-seal** sealed straggler is **dropped**/inert — backdate-safe). The **retained (canonical) run is NOT committed** — it is the linear chain `[previousSeal..previous]`,
     recovered by the flat walk (nodes keep full bodies), its `Ixn`-only integrity checked on the flat walk (a sealed
     event in the span would itself be a seal, so `previousSeal` would name it — inv 17). **"Content was folded since
     the prior seal" is the derived predicate `previous != previousSeal`** — no field.)*
   **Two enforcement classes (F1):** `anchors`/`grant` are **back-checked** — a mislabel is caught when the
   referenced event is validated against its required kind. *(Exception — the **bare issuance commitment** (a cred's
   `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` in an IEL `Ixn`'s `anchors`) has **no event behind it** — it
   is a flat hash, not a SEL event — so there is **nothing to kind-back-check**. Its validity is **by-anchor-existence
   at the cred feature layer** (a matching commitment resolvable on the issuer's fresh IEL = validly issued; R5/R1);
   the chain treats it as an opaque anchored digest.)* **The anchor matrix is enforced *kind-strict* on both
   cross-layer legs — the IEL→SEL leg (C1, 2026-06-27) and the KEL→IEL member-participation leg (2026-06-28) — each
   direction:** on the IEL→SEL leg, each SEL kind is valid **only** when anchored by exactly its matching IEL kind,
   **and** each IEL kind anchors **only** its matching SEL kinds — content `Ixn` (and a content-SEL **v1**: a serial-1
   `Pin`, or the first content `Ixn`) ↔ IEL **`Ixn`**; SEL `Gnt` ↔ IEL **`Ath`**; SEL `Trm` ↔ IEL **`Rev`** (revoke) / **`Dth`** (rescind); SEL `Sea` ↔ IEL **`Evl`** (the burying-seal recovery, area-sel §1d).
   *(There is no SEL `Fld`/`Rpr` — no re-seal, no repair.)* **Tier-elevation (anchor tier ≥ event tier) is an *additional* floor, not the check** —
   a tier-only reading would let a T2 kill-anchor (`Rev`/`Dth`) host T1 content (2 ≥ 1), laundering content onto the
   seal-durable rail and breaking *only-tier-1-is-buriable* (inv 13); the kind-strict binding
   closes it. (On the IEL→SEL leg the laundering is a real single-owner hole; on the KEL→IEL leg the identity's
   threshold already subsumes it, so kind-strict there is correctness-by-construction — content always rides an
   archivable host structurally, not because the threshold backstops it.) **Anchor-monotonicity (the IEL's cross-layer SEL-anchor discipline, 2026-07-01; the total-order/fork-prevention reading RETIRED 2026-07-12 — below):** an IEL event's SEL anchor is valid **only if the anchored SEL event extends that SEL's latest IEL-anchored tip** — the anchor chain names each SEL's tip *by SAID* over the **canonical (retained) IEL walk**; the SAID is opaque (inv 16), so an anchor a node can't **attribute** (it lacks the body) is **skipped, not blocking** (*skip-unattributable* — else a withheld/lost body would wedge the SEL); an anchor at an **already-attributed** SEL serial is **malformed → the SEL event is inert** (back-checked at SEL-validation; the carrying IEL event stays valid — no IEL contamination). **The theorem this once supported — _a valid SEL fork implies an IEL fork beneath it_, "a SEL never forks under a linear IEL" — is RETIRED (witnessed-SEL redesign, 2026-07-12, area-sel §1c):** the **skip-unattributable** step is itself the hole — one IEL `Ixn` can name **two** competing SEL events at one `(SEL-prefix, serial)`, and a node holding only one attributes it as the tip while skipping the other → observer-dependent tips under a **linear** IEL (equivocation-by-withholding). Fork-prevention is therefore the SEL's **own witnessing** (first-seen at its `(prefix, serial)`, area-sel §1c), **not** the IEL's total-order; the anchor supplies **owner authorization** + the **finality-floor** (the down-`pin`) and — for a `Sea`'s recovery — its burying-seal anchor (the `Evl` rail, area-sel §1d). Whether the re-anchor-inert rule survives as defense-in-depth is an encode detail (area-sel §4). Concretely:
   - a SEL `Trm` is valid **only** anchored by an IEL **`Rev`** (a revocation lookup-SEL `Trm` — a cred's revocation / an app-SEL closure, `t_govern`)
     or an IEL **`Dth`** (a rescission lookup-SEL `Trm`, `t_authorize`), determined by its SEL-type; an IEL `Ixn`'s
     `anchors` resolving to a `Trm` is **rejected**, **and** a `Rev`'s or `Dth`'s `anchors` resolving to a
     **non-`Trm`** (content, a v1-`Pin`) is **rejected**. Symmetrically, a SEL **`Gnt`** (grant) is valid
     **only** anchored by an IEL **`Ath`** (kind-strict — an `Ath` anchors **only** `Gnt`s; the additive twin of the
     `Rev`/`Dth`→`Trm` kill); and a SEL **`Sea`** (the neutral burying seal-advancer) is valid **only** anchored by
     an IEL **`Evl`** (kind-strict — an `Evl` anchors **only** `Sea`s; the burying-seal recovery, area-sel §1d). **This back-check is now what keeps kills sealed** — it replaces the former
     `revokes`/`rescinds`-are-`Kil`-only binding (the `Rev`/`Dth` kinds seal on arrival; the
     `Trm`-demands-a-`Rev`-or-`Dth` rule is what forces every kill onto a sealed kill-anchor).
     **Kill-semantics → kill-anchor kind (the total rule, S5/D):** a `Trm` is anchored by **`Dth`** (`t_authorize`)
     **iff** it is an **authorization-rescission** — a lookup-SEL that closes a granted authorization: a
     **delegation**-rescission or a **doc-membership** rescission — and by **`Rev`** (`t_govern`) **otherwise**. So a
     **cred revocation** and a shared-doc-leg (a version-SEL closure) `Trm` are `Rev`-sealed; the rescission
     lookup-SELs are `Dth`-sealed; and an **arbitrary app-topic** SEL's `Trm` defaults to `Rev` (never the cheaper
     `Dth` when `t_authorize < t_govern`). *(The revocation/rescission lookup-SELs use **distinct topics per kind** —
     `CRED_REVOCATION_TOPIC` (Rev) / `DLG_RSC_TOPIC` / `DOC_RSC_TOPIC` (Dth), **never a shared `KILL_TOPIC`** —
     B1 fail-secure rework 2026-07-09; the topic makes the Rev-vs-Dth split explicit in the derivation, and a `Trm`'s
     anchor-kind (`Rev`/`Dth`) is the structural check.)*
     The **grant** side is the additive twin: a `Gnt` is `Ath`-sealed.
   - a **credential is anchored directly** by an IEL `Ixn` naming its **issuance commitment
     `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** (an immutable SAD, no cred-SEL — 2026-07-09; the anchor is
     the validity proof; `cred.said` never appears raw — inv 16). A **content SEL** is anchored by an IEL `Ixn` naming its
     **serial-1 event** (its *v1* — a `Pin` for issue-and-sit; `v1.pin == this Ixn.previous` is the floor). A
     **revocation/rescission** lookup-SEL's v1 **is** its `Trm`, anchored by the `Rev`/`Dth`, floored
     `Trm.pin == this (Rev/Dth).previous` (S4 — the floor rides whichever IEL kind anchors the v1, never the `Ixn`
     only). **The `Icp` is never anchored in a SEL** — it rides via `v1.previous`; it carries **no** manifest (a
     lookup-SEL `Icp`'s `data` IS `said(grant-instance)`).
   - **KEL→IEL (member participation):** each IEL event is anchored **only** by the member-KEL kind that reveals
     exactly the capability the member exercises — content ↔ KEL **`Ixn`**; T2 establishment, governance, kill & terminal
     (user `Icp` / `Evl` / `Ath` / `Rev` / `Dth` / `Trm`, **federation `Fcp`** inception & federation `Trm`) ↔ KEL **`Rot`**;
     **T2 witness/federation (IEL `Wit` — the user federation-binding AND federation
     governance) ↔ KEL `Wit`** (the **one `Wit` kind**: a single `Wit` is the rotation — refreshes
     the signing key + rotation reserve — and anchors the IEL `Wit`; `pins = Wit.previous`). The **anchor-kind is uniform** (`Wit ↔
     Wit` both facets), but the **field-match is facet-specific (Q3, Jason 2026-06-28):** the **user** facet matches
     the binding `{federation, federationPin}` (C4/C5, anti-straddle — each member carries its *own* binding); the
     **federation-governance** facet matches **only the witness-config** (the "witnessing stuff") — the **roster
     delta does not match** (it rides the IEL `Wit`'s manifest, `Evl`-style, committed by SAID + anchored by the
     `t_govern` member `Wit`s), and the **`clock` is not matched** (a single value on the federation IEL `Wit`,
     constrained monotonic + `≤ now+CLOCK_TOLERANCE_BAND` — inv 4 `clock` / federation §1f). The IEL `Trm` and the federation
     `Fcp`/`Trm`, formerly `Ror`-anchored, **re-home to `Rot`** now that every key change is a T2 rotation-reserve act.
     The anchor-hosting KEL kinds are `Ixn`/`Rot`/`Wit` (the `Wit` anchors **only** the IEL
     `Wit`). The **rotations are the core structural check**; an
     added member's **consent** (a joiner's KEL `Ixn` on an `Evl`, **or on a federation `Wit`** — a new witness
     joining-not-rotating, A1 2026-06-28) rides **alongside** — **valid only for a member in
     the `add` set, counted only toward Rule-A consent-of-added, never toward `t_govern` (which only the
     approvers' `Rot`s — the approvers' `Wit`s for a federation `Wit` — satisfy); over-count → laundering, blanket-reject → joiner lockout (cold-5 C6 / A1)** — not part of
     the anchor-kind check (the joiner `Ixn` rides alongside the approvers' kind-strict KEL `Wit` anchors, exactly as on an `Evl`). **Federation bootstrap — RESOLVED
     (2026-06-28):** the federation's own witness KELs are **`Fcp`-rooted** (federation infrastructure, governed
     *into* the roster, **single-federation**, never self-bound — §inv 14), so genesis is `Fcp` → `Rot` and the `Rot`
     anchors the federation IEL **`Fcp`** kind-strict (T2 ↔ T2); a `Wit` on an `Icp`-rooted user KEL is the
     identity's **federation rebind** (KEL `Wit` → IEL `Wit`, both T2 — auditable at the IEL, the IEL `Wit`'s **two
     federation-binding fields `{federation, federationPin}`** (a closed set, cold-5 C4) **exactly matching** those of
     every anchoring KEL `Wit` on every walk — so all `t_govern` members are pinned to the **same federation position**
     (cold-5 C5); the identity's federation is the **IEL's own authoritative binding**, inheriting
     nothing sub-threshold or unmatched — so no member KEL can straddle the identity, cold-3 B2). The **initial**
     binding rides the user `Icp`; a `Wit` only *changes* it.
   - the retained run (`[previousSeal..previous]`) resolves to `Ixn`-only events, checked on the flat walk (the spine can't enforce it).
   `roster`/`clock`/`witnesses`/`delegates` are **directly consumed** by the event with no downstream check → the
   kind→role allowlist is their *sole* protection (load-bearing). *(This is why `delegates` does **not** fold into
   `anchors` like the kill/issue roles did: it is directly-consumed and names grantee **prefixes** — authority state,
   not a back-checkable event.)*
   General (not federation-specific); the federation timestamp lives **inline in the manifest SAD** (data), keeping the chain event timestamp-free (inv 6). *(There is
   **no clock event / no `Tck` kind** — the clock is the `clock` role in a federation governance event's manifest (`Fcp`/`Wit`/`Trm`).)*
   *Src:* §2 + Jason 2026-06-21. `[locked-candidate]`
5. **Pin-everything-to-current, floored per-chain.** Every event pins its dependencies' current tips; the
   forward-only floor lives on the chain doing the pinning (intra-chain — no cross-chain clock). **Two distinct
   backdate mechanisms — keep them separate (F-C, clarified 2026-06-21):**
   - **(i) Fresh participation closes the *deep-member* backdate.** A member participates in an IEL event by
     authoring a **fresh KEL event at its own current tip**, of **exactly** the kind that reveals the capability it
     exercises (**kind-strict, inv 4:** `Ixn → IEL Ixn` content; `Rot → IEL Icp`/`Evl`/`Ath`/`Rev`/`Dth`/`Trm`/federation `Fcp`/federation `Trm` establishment,
     governance, kill & terminal; **`Wit → IEL Wit`** witness/federation — the user federation-binding **and** federation governance (the one `Wit` kind is the rotation; anchor-kind uniform, field-match facet-specific — Q3, cold-4 B1)), signed by its **current** key and committing to that
     specific IEL event. **Each counted member furnishes one**, so a T2+ IEL event (incl. a `Rev`/`Dth`) rotates **every**
     participating member — a threshold of T1 signing participations does **not** satisfy a T2+ event ("1 reserve +
     the rest signing" does not suffice; A, 2026-06-27). *(An added member's **consent** on an `Evl` — or on a federation `Wit` (a new witness) — rides alongside
     as a KEL `Ixn` — **valid only for a member in the `add` set, counted only toward Rule-A consent-of-added, never
     toward `t_govern` (only the approvers' `Rot`s — `Wit`s for a federation `Wit` — satisfy it); over-count → laundering, blanket-reject → joiner
     lockout (cold-5 C6 / A1)** — added-on, not the structural anchor-kind check, which is the approvers' rotations.)* A rotated-out key **can't** produce one (a KEL
     append needs the current key; an old event committed to something else). There is **no
     detached-signature-resolved-as-of-a-pin path** (Jason confirmed 2026-06-21). So the rotated-out-member-key
     backdate is closed by the *participation* mechanism — **not** the floor.
   - **(ii) The forward-floor closes the *as-of-context* backdate.** An event **can't pin a dependency at an old
     position** (an old roster / federation / authority context), because the per-chain floor only moves forward.
     This is a monotonicity backstop for as-of pins — don't credit it with closing the member backdate.
     **Exception — `federationPin` (the cross-chain case, 2026-06-25):** ordering two federation positions needs a
     *walk of the federation IEL* (cross-chain), which this **intra-chain** floor can't do; so for `federationPin`
     forward-only is **emergent, not structural** — a backward/stale pin lands chain-valid but **un-witnessed** (the
     currency gate refuses a non-current roster; the clock refuses closed-window keys), cleared by pinning forward.
     The other contexts (roster / authority, judged by the **anchoring position**) are intra-chain and floored
     normally. *Src:* §6 + federationPin-carrier review 2026-06-25.
   **As-of authority = the anchoring position, NOT the asserted `pin` (F1, locked 2026-06-20).** Any as-of
   resolution that affects *authority* (grandfather / rescission ancestry, roster / delegation state) is judged by
   the **anchoring position** — the serial of the committing IEL `Ixn`/`Evl`, append-only-fixed via the chain
   `cred ← IEL Ixn ← KEL Ixn` (each `previous`-linked; the cred is anchored **directly** — no cred-SEL, 2026-07-09) — the as-of is read directly from the anchoring position, which is append-only and can't be inserted in the past.
   **The anchoring position is named by the credential's committed `issuerPin` (R1, supersedes the earliest-scan —
   Jason 2026-07-18).** A cred's issuance commitment is a flat hash in `anchors[]` (not a SEL event), so nothing in
   the chain forbids re-anchoring it — and a **T1 `Ixn` re-anchor after a T2 `Rev` would, under a naive latest-anchor
   floor, move the as-of past the revocation, silently un-revoking (a *tier inversion*)**. The cred's **`issuerPin`**
   (= the anchoring `Ixn`'s `previous`, committed by `cred.said`) fixes the position at **`issuerPin.serial + 1`**: a
   **checked locator** (the `Ixn` there must carry `previous == issuerPin` **and** the commitment), and **provably the
   earliest** possible anchor — an earlier one would need a hash cycle, the commitment embedding `cred.said` which
   embeds `issuerPin = said(E_pin)`, and every event at-or-below `E_pin` feeds `said(E_pin)` via the `previous` chain.
   So a later re-anchor is **never consulted** — no scan reads `anchors[]` per event (the top-level-cues-only walk
   opens no manifest per event); the pinned position is the fixed range start for the revocation walk, alongside the
   fresh tip. The chain still **accepts** a re-anchoring `Ixn` as structurally valid; it just never bears on the
   pinned as-of. *(Cred-only — delegate/doc-member targets are grant-epoch-scoped, so a re-grant makes a *fresh*
   locus.)*
   **No self-asserted _authority_ pin (removed 2026-06-26)** — no issuer-chosen value is *trusted* as the as-of; the
   as-of is the **anchoring IEL `Ixn`** position (append-only). A **checked locator** pin is a different thing and is
   fine: the cred's `issuerPin` and a content/lookup SEL's `v1` down-pin both satisfy `pin == anchor.previous`, are
   **verified against the real anchor** (never trusted), and only *locate* it (at `pin.serial + 1`, one manifest — no
   scan), asserting no authority. Closes the pin-backdate forgery and the DI2I/delegated-issuer forge-as-of-old route:
   a *trusted* position claim is backdateable, a *checked* locator is not (the anchor must actually sit there,
   append-only). **A standalone SAD's custody follows the same split (2026-07-03; direct-anchor rework Jason
   2026-07-18):** an `owner`-bearing SAD is **directly anchored** on the owner's IEL — the owner authors an `Ixn`
   committing the SAD's `said`; the SAD's **`pin`** (a checked locator, `pin == anchor.previous`) finds it at
   `pin + 1`, and `owner ⟹ pin` (`custody { owner, pin, readers }` — the SAD's `kind` names its type, no `topic`),
   its as-of the append-only anchoring position. See inv 16. `[locked]`
6. **No timestamps in the log primitives.** In KEL/IEL/SEL, ordering and "as-of" are expressed only by pins
   (which event) + the chain walk — never wall-clock time. **Feature layers (creds / documents) MAY use
   timestamps** — there a timestamp is a feature semantic (e.g. a cred validity window), not a primitive
   ordering mechanism. *Why:* in the primitives the real attack is a backdated authorization *context*, not a
   clock; time fields at the primitive layer would invite exactly that.
   **Federation consensus clock (exception, 2026-06-21):** the federation publishes a coarse, consensus-attested
   clock for **freshness / staleness only** — the **`clock` role in each federation governance event's `manifest`** (`Fcp`/`Wit`/`Trm`) (an
   **inline timestamp value**, one per governance change — [inv 4] / federation §1f), sealed, **not** a field on any chain
   event; witness receipts carry a time. It **defeats** backdating
   (it bounds a key's receipt times to its validity window — federation §1f / S2) rather than inviting it, and
   intra-chain ordering stays pin-based — so it honors this rule's *intent*. The bytes live in the **manifest SAD** (data), so the
   primitives stay timestamp-free. *Src:* pinning note + Jason 2026-06-20/21.
   `[locked]`
7. **Prefix vs SAID.** Entity identity = prefix (follows the entity's evolution); a point-in-time position =
   SAID (a chain-binding anchor). *Src:* §2 + prior memory. `[locked-candidate]`

## Verification
8. **Walk semantics — full walk is the baseline; early termination is a caller-chosen optimization.** Every walk
   is preloaded with the SAIDs the caller cares about. Baseline: walk the full chain and return contextual
   information about which sought SAIDs were found (and divergence status). Whether the tip must be reached
   depends on the question: *"is the chain valid?"* → walk to tip; *"is this SAID anchored?"* → the walk may end
   once all sought digests are found, **provided the chain is non-divergent up to that point** (optimization).
   **The seal is the trust boundary on a divergent chain (inv 13):** the walk surfaces the
   at-or-below-`last_seal_advancing_event` portion as **final** even on a chain with above-seal divergence, and
   reports the above-seal tail as durable-only-once-cleanly-sealed-past. So a *recoverable* divergence's honored
   anchors are the sealed portion plus the surviving branch once its burying seal lands; a *terminal* divergence's post-seal window
   grounds **no new trust** (whole-*above-seal*-suspect — below-seal stays final).
   *Planned:* a `search_only` parameter that ends the walk when all digests are found; the verification token
   then points at the reached (possibly mid-chain) position, and a `resume` function takes that token forward to
   tip. **Token reuse is transitive (F5, 2026-06-20):** a cached token's reuse gates on the effective-SAID of
   **every chain it transitively pins** (the KEL(s) beneath an IEL, the IEL beneath a SEL), not the chain's own
   alone — else a lower-layer `Rot` (a recovery rotation) breaks an upper event invisibly to the warm cache.
   **Freshness composes — the transitive set + divergence + resume (F-E, locked 2026-06-21):** the three reuse
   rules only hold *together*. (a) **The multi-source / witnessed freshness bar (F8) applies to the *whole*
   transitive set** — every chain the token leans on (cred, issuer, *every* delegator above it, the devices
   beneath each identity, **and the federation IEL(s) the witnessing itself leans on — G3**), not "the chain"
   singular. (You can't multi-source your way out of a stale *federation roster*: an eclipsed view of `F` still
   counts a since-removed witness as "a source." The **federation clock** [federation §1f] supplies the absolute
   staleness metric that bounds this.) A single stale/malicious source on **any** one of them can
   hide a **positive-state break** — a fork/divergence, a dormant-chain forgery, a stale federation roster, **or a
   `kills[]` revocation/rescission** (now fail-secure via this same bar — B1 2026-07-09); so a
   *loss-of-trust* decision needs each dependency's **validity/freshness** confirmed multi-source
   (a witness-signed effective-SAID *is* multi-source by construction → cheap for witnessed chains — and a
   **no-single-tip chain's verdict-recoupled synthetic satisfies the bar too**: it isn't a single signable tip, but
   every node derives the same `forked`/`disputed` value from the held branches + their receipts, so the multi-source
   confirmation rides the competing branches' receipts, not one signature over the synthetic — inv 17 / §2a; an unwitnessed
   or eclipse-isolated chain **can't meet the bar → the loss-of-trust decision fails-secure: REFUSE**, never
   proceed-with-a-flag, cold-5 C2). **This fail-secure bar governs the whole loss-of-trust read (B1 fail-secure rework
   2026-07-09):** both the **positive trust chain** — is this cred *validly issued* by an authority I trust (the
   issuer's fresh IEL/KEL, where the issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` lives — confirm multi-source or refuse) — **and
   cred REVOCATION / delegate / doc-member RESCISSION**, which are **`kills[]` declarations on that same witnessed
   IEL** and so ride the same freshness gate (walk the fresh chain, forward-match the `target`; a hidden kill needs a
   stale IEL, which the bar already refuses — inv 10). The trust decision is **grant iff (validly-issued) AND
   (not-revoked AND not-rescinded)**, all confirmed on the multi-source fresh walk (**no positive-vs-negative
   carve-out** — the earlier best-effort overlay is dropped, its `attribute-all` escape hatch broke — cold/warm
   re-review-2 F1). A verifier may deliberately opt **down** to a **fail-open** content-addressed lookup for the kill
   (a consumer under a latency budget; an app server on a walk-timeout — the revocation check is the consumer's, not
   `vdtid`'s, R6; inv 10 / document-policy §F), never up.
   (b) **"Is this chain forked / disputed?" is itself a
   loss-of-trust question** — a one-branch holder computes a normal-looking tip and never sees a fork; only the
   federation dispute signal reveals it, so it must be in the multi-source bucket. (c) **`resume` must
   re-run the to-tip negative checks** (revocation / rescission / divergence) against the new tip whenever any
   transitively-pinned chain moves — an incremental resume that only extends chain state would advance the token
   *past* a revocation or fork without re-checking. *(The revocation / rescission checks re-run on the fresh walk
   alongside divergence/validity — **all fail-secure** now (no best-effort carve-out); the fail-open content-addressed
   lookup is the deliberate opt-out, inv 10.)* So F9's "a cross-layer break is detectable" is **a consequence of
   F5+F8 over the full set**, not a separate mechanism. **(d) Freshness/staleness is *time*-triggered, not only
   movement-triggered (cold-12 F1):** the federation staleness + 365-day key-window auto-expiry (federation §1f) fire
   with **no** chain event — nothing *moves* — so a loss-of-trust decision **recomputes staleness against wall-clock
   `now` even when nothing moved**; the token caches the witnessing-*time*, **never** a cached `fresh`/`stale` verdict
   (the effective-SAID-movement gate certifies *structure*, not *freshness* — vdtid-services §1d). *Src:* Jason 2026-06-20/21.
   baseline `[locked]` / `search_only`+`resume` `[planned]` / transitive-reuse + F-E `[locked]`
9. **Structural problems error; everything else is reported, not raised.** A *structural* problem (invalid
   chain, divergence, broken linkage, tamper) produces a descriptive error. A *non-structural* condition (a
   sought SAID not anchored, a policy unsatisfied, etc.) is returned as contextual information in the result,
   never raised as an error. *Why:* callers must distinguish "the data is broken" from "the answer is no";
   conflating them is a correctness and fail-secure hazard. *Src:* Jason 2026-06-20. `[locked]`
10. **Negative checks are a fail-secure `kills[]` declaration on the witnessed log — with a fail-open
    content-addressed opt-out.** "Is X revoked / rescinded / closed?" is answered by whether X's derived **`target`**
    appears in any **`kills[]`** on the owner's chain — never by scanning for absence. **Cred revocation AND
    delegate/doc-member rescission are FAIL-SECURE by default (B1 fail-secure rework 2026-07-09, reversing the
    create-on-revoke best-effort model — cold/warm re-review-2 F1):**
    - **Fail-secure walk (DEFAULT):** walk the owner's **fresh** IEL over `[issuance-position .. tip]` — **both range
      ends are load-bearing:** the floor is the **earliest** issuance anchor (a cred's re-anchor is inert — R1, else a
      T1 re-anchor after a T2 `Rev` moves the floor past the kill, a tier inversion), the ceiling the **fresh tip**
      (inv 8). Forward-match your computed `target = hash('{topic}:{owner}:{data}')` (a flat domain-qualified hash;
      distinct `topic` per kind, `data` = the grant-instance; the target **mirrors the killed address** —
      **non-lineaged** for a monotone kill (cred revocation, delegate/doc-member rescission), **lineaged**
      (`…:{lineage}`) for a **value rescission** (scoped to the one instance it kills, so `lineage: N+1`
      survives), a literal **`:content`** for a **content (app-SEL) closure** — area-sel §1f; both this
      forward-match and the fail-open O(1) derive use the same form) against each `Rev`/`Dth`'s `kills[]` (reading `bound`
      from the same entry — delegate `bound` public, doc-member `bound` gated). **In some `kills[]` → revoked/rescinded;
      in none on the fully-walked fresh chain → not-revoked** — being in a `kills[]` **is** the definition of revoked, so
      "in none" is exactly "not revoked", nothing to miss. This **rides inv 8's freshness gate**: the only way to hide
      a kill is a **stale** IEL, which the verifier already refuses when trusting the owner at all — so kill-freshness
      == authority-freshness. Streamed with the subject(s)-in-scope (bounded — O(subjects) memory, O(range) time, no
      lossy cap); self-contained (delegate `bound` on the IEL, un-withholdable; a doc-member's gated `bound` is
      fetched from the rescind-doc → withheld = conservative don't-honor).
    - **Fail-open lookup (OPT-OUT):** build the `Icp{owner, topic, data}` → two-pass → the SEL **prefix** → fetch its
      **`{Icp, Trm}` lookup SEL** (content-addressed, O(1), no index) — **found → revoked; not-found → best-effort
      not-revoked** (a withheld object reads not-found; `Trm`-existence is a **conservative proxy** for the
      authoritative `kills[]`-membership — equal only for a canonical revocation, over-refuse fail-safe, not
      walk-equivalent — area-sel §1). The `kills[]` `target` (flat hash) ≠ this prefix, so the public declaration
      never leaks the object's address. A verifier opts **down** to fail-open (a consumer under a latency budget; an
      app server on a walk-timeout — the revocation check is the consumer's, not `vdtid`'s, R6); it never opts up.
    So this is a **fail-secure lookup by default**, an inv-8 dependency (**no carve-out**) — the earlier best-effort
    "negative overlay / fails open by default" and its `attribute-all` escape hatch are **dropped** (cold/warm
    re-review-2 F1 broke that). *Why the declaration form:* a scan-for-absence forces deep-inspecting everything; the
    `kills[]` forward-match is O(range) over events the authority walk already streams, tamper-evident on the
    witnessed log. *Src:* design-pass §5 + B1 fail-secure 2026-07-09. `[locked-candidate]`

## Keys, tiers, thresholds
11. **Tier = whether the rotation *reserve* is required — orthogonal to count (two tiers, first-seen 2026-07-08).**
    **T1 = signing key only** (content — the everyday key); **T2 = the rotation reserve alone** (every key change) —
    the **old signing key is not a prerequisite at T2** (a rotation reveals the new key; you don't sign with the key
    you're abandoning). *(There is no T3 — the recovery key / recovery reserve is dropped; recovery is a plain `Rot`.)*
    The reserve (held *apart* from the signing key) is required when **either (a) a forgery would be high-harm or
    irreversible** (establishment-mutation, authority-grant, identity-kill) **or (b) the act must be permanent on
    arrival** — i.e. **sealed**, carried by a dedicated sealed kill-anchor (`Rev` or `Dth`). **A kill (revoke / close /
    rescind / terminate) is case (b):** low-danger (safe-direction — it only removes trust) but **monotone** (a third
    party relies on it), so it must be sealed → it rides a **`Rev`** or **`Dth`** (the dedicated sealed kill-anchors —
    no roster delta; but, being permanent, they **force a `Rot`** like `Evl` — each authorizing member authors a T2 KEL
    event; the `Evl`-vs-kill-anchor distinction is the **roster delta**, not the rotation — A, 2026-06-27) → **T2**
    (identity-kill → `Trm`, also **T2**). Only **content** (`Ixn`) is **T1**. Tier is still ⊥ count (count is a dial;
    tier is set by danger-or-permanence): a content `Ixn` is **T1 even at a high `t_use`**. **This reverses the F3 line
    "safe-direction removals are T1 / `Trm` may be delayed"** — a kill can't be unsealed (inv 13, 15); it re-aligns
    with `document-policy §F`. *Src:* §1 + the kill-cluster resolution, 2026-06-21; two-tier collapse 2026-07-08.
    `[locked]`
12. **IEL authorization is a threshold vector** `{ use, authorize, govern }` (the **count** axis,
    ⊥ tier per inv 11; `t_recover` is **dropped** — no repair, no recovery reserve), indexed by kind; additions
    require unanimous consent of the added; a `Evl` needs consent-of-added ∧ `t_govern`-of-outgoing (its `cut` also
    evicts). **Bounds (F-K, hardened 2026-06-21; authorization floor + roster cap added 2026-07-08):**
    - **`t_use ≥ 1`** — `t_use = 1` is **single-device by choice** (no content resilience); `t_use ≥ 2` makes a
      single compromised device unable to author content (F10a). **`t_use` is exempt from the authorization floor**
      (content is first-seen / recoverable).
    - **The roster is hard-capped at `MAXIMUM_ROSTER_SIZE`** (a DoS backstop — the verifier rebuilds the roster in memory as it walks;
      any delta pushing the live set past `MAXIMUM_ROSTER_SIZE` is rejected; **all IELs, federation included** — federation §1a).
    - **The authorization floor: `t_govern`, `t_authorize > |roster|/2`** (2026-07-08 — a strict majority signs every
      governance / grant, so any two authorizing quorums overlap (pigeonhole) and a sealed fork always names a
      double-dealer; closes the disjoint-quorum attribution loss — adversary-cases Pass 2). Added alongside the `≥ 2`
      security floor and the `≤ |roster| − 1` recoverability ceiling below (compatible for every `|roster| ≥ 3`).
    - **Authority kinds (`t_govern`, `t_authorize`), `|roster| ≥ 2` — TWO bounds of different kinds
      (split 2026-06-21):**
      - **`≥ 2` = the *security* floor — HARD, verifier-enforced, every identity.** No single member exercises
        authority (closes the `t_govern=1` seizure, the `t_authorize=1` rogue-delegate — LF2). A single compromised
        device must never govern / grant alone.
      - **`≤ |roster| − 1` = the *recoverability* ceiling — ADVISORY only at `|roster| = 2`, HARD at `|roster| ≥ 3`
        for every identity incl. the federation (G1, corrected twice 2026-06-21).** It lets you **evict a
        compromised member / recover a lost device without the missing one**. Violating it (a threshold `= |roster|`)
        is **NOT self-lockout — it's a hostage**: a *single compromised member* withholds consent → every eviction /
        recovery (`Evl` with a `cut`) needs **all** `|roster|` (incl. the compromised one) → the identity is
        **frozen until reincept, at the attacker's discretion** (an indefinite veto — the adversary *gains*, the
        owner doesn't merely lose access). So at `|roster| ≥ 3`, where a threshold `< |roster|` is available, a
        threshold `= |roster|` is a **gratuitous hostage config → the verifier REJECTS it** (Finding 3). The
        relaxation survives **only at `|roster| = 2`**, where `≥ 2` *forces* `t = 2 = |roster|` (no satisfying value
        otherwise) — there the verifier **accepts** + the wallet **warns** ("a 2-device identity can't evict/recover
        without both, and a compromised device can freeze you — add a 3rd key"). *(Reverses 'advisory at all sizes'
        / 'nobody seizes, only lock yourself out' — both wrong: it's a hostage, and it's only forced at 2.)*
    - **Singleton exception:** `|roster| = 1` → all thresholds = 1.
    - Ordering: `t_use ≤ t_govern`, `t_use ≤ t_authorize` (sanity, not load-bearing). *(The former `t_govern ≤
      t_recover` floor is **gone** — there is no `t_recover`; eviction rides an `Evl` `cut` priced the outgoing
      `t_govern`, so there is nothing to under-price.)*
    **Consequence (G1, corrected 2026-06-21):** a 2-member identity (phone + computer — the common case) is
    **VALID**: `≥ 2` forces every authority threshold to 2 (secure — no single-device seizure), and it simply can't
    also satisfy `≤ |roster| − 1` (= 1), so it's **unrecoverable → warned, not rejected** (a lost or *compromised*
    device freezes governance/recovery — a hostage, not just self-lockout — but nobody *seizes* you; add a 3rd key
    to become recoverable). **At `|roster| ≥ 3` a threshold `= |roster|` is REJECTED** (a gratuitous hostage —
    Finding 3); recoverable governance needs `|roster| ≥ 3` (a threshold both `≥ 2` and `≤ |roster| − 1`). The **federation — i.e. the witness IEL whose roster
    is the witness KELs — must be `≥ 4`** (structural — the `signers ≥ 3` witness-config floor plus the federation's exclude-self pool `signers ≤ |roster| − 1` forces `|roster| ≥ 4`; `≥ 5` recommended — federation §1a/§4; its recoverability ceiling is hard, so the witness IEL can never be brought
    to an unrecoverable / bricked size). *(Earlier "`|roster| = 2` is invalid / verifier rejects" was wrong — it conflated the security
    floor with the recoverability ceiling; there's no security reason to forbid the both-agree config.)* The
    reserve/tier each kind needs is inv 11. **The bounds are re-checked on the *post-delta* config at every config-changing event — a user `Evl` (including a `cut` `Evl` that evicts), *or* a federation `Wit` (including a config-only `Wit` that changes `threshold`/`signers` with no roster delta — cold-seam F2)**
    (Finding 14a, 2026-06-21; generalized to the federation `Wit` — cold-13 F1: the federation has **no `Evl`**, it governs via `Wit`) — not only at `Icp`; an event whose resulting roster/thresholds would violate any
    bound is rejected. **A third, absolute floor — the roster is never emptied: post-delta `|roster| = |roster| + |add| − |cut| ≥ 1`** (beneath the security floor / singleton exception; the roster is a **set**, so `add ∉` the current roster, `cut ⊆` it, `cut ∩ add = ∅` — the size arithmetic holds; the same set discipline the federation states at §1a (cold-9 Q2 / cold-14 F1), general to *every* roster delta). A `cut` that would zero the roster is rejected — **one general rule** that makes *every* singleton IEL's roster **downward-immutable**: a singleton `cut` `Evl` (no `add`) computes `1 + 0 − 1 = 0` (`< 1`) → rejected, so a singleton can't be zeroed — **not only** the federation-member key-SEL owner (federation §1e). It still **allows** singleton evict-and-replace via an `Evl` — `cut 1 + add 1` stays `1`, **authorized at `t_govern`-of-outgoing** (the *old* member signs, so this works only for a planned migration where the sole key is **uncompromised/available**; a lost or compromised singleton can't produce that signature → reincept); only the zeroing is forbidden. **For the federation this re-check also covers the witness-config recoverability cap** — the **full** post-delta `threshold ≤ min(|roster| − 2, signers − 1)` **plus the witnessing floor `threshold > signers/2`**, re-applied on **any `Wit` that changes roster, `threshold`, or `signers`** (not a roster `cut` alone) — so a **bare `cut`** that would strand the federation un-recoverable (`|roster| 5→4` at `threshold 3`), a `t_govern`-hostage (`|roster| 4→3` at `t_govern 3`), **or a `signers`/`threshold` change landing on the *binding* `signers − 1` leg** (`{s 4, t 3}@5 → {s 3, t 3}@5` passes `|roster| ≥ threshold + 2` yet violates `t ≤ min(3,2)`, cold-seam F1) is **rejected**, forcing evict-and-replace or a simultaneous threshold-and-`signers` drop. **This is what actually enforces the `[locked]` "the witness IEL can never be brought to an unrecoverable size" above** (cold-13 F1; the roster-leg-only phrasing corrected to the full `min` — cold-seam F1, 2026-07-02 — since for `signers ≥ 2` the `signers − 1` leg binds and the roster leg is slack).
    **Every IEL kind prices itself (S1 closure, 2026-06-21; count-parametrization retired 2026-07-04).** The
    required count of an IEL event is fixed by its **own kind**, never derived from the higher-layer payload it
    anchors, and **every kind draws from exactly one slot**: `Ixn` → `t_use`, `Evl` → `t_govern`, `Ath` →
    `t_authorize`, `Dth` → `t_authorize`, `Rev` → `t_govern`, `Trm` → `t_govern`, `Wit` → `t_govern`. **There is
    no count-parametrized kind and no `threshold` slot-name field** — the former `Kil` (a single kill-anchor
    parametrized by a `govern`/`authorize` slot) is **split into `Rev`** (revoke your own artifact, `t_govern`)
    **and `Dth`** (deauthorize a grant, `t_authorize`), so each kill-anchor's count is implied by its kind exactly
    like every other kind. So "count travels with the anchored kind" is safe *because* the invariant it protects is **count-integrity**: no kind
    anchors a payload at a count **below** its own establishment mutation's (no laundering — the old IEL
    `Evl`-anchors-a-kill-while-changing-the-roster, a kill's count riding a roster change). An **`Evl` anchoring a SEL
    `Sea`** (inv 4 / area-sel §1d) is safe under this: the `Sea` is `t_govern` = the `Evl`'s own count, so bundling a
    roster `cut` with the `Sea` anchor launders nothing, and the anchor role is back-checked (`Sea ← Evl` kind-strict,
    so the kind→role gate is untouched). Verifying an IEL chain's validity therefore needs **no SEL input** — each event prices from itself.
    *(Eviction is an ordinary `Evl` carrying a `cut` — it mutates establishment state, but at its own kind's
    `t_govern` (the outgoing threshold), so there is no separate, cheaper count to launder under; pricing stays
    self-contained — `Evl` → `t_govern` — and IEL validity still needs no SEL input.)*
    **Threshold declaration — the active set is fixed at `Icp` (locked 2026-06-25).** The `Icp` declares
    **exactly** the authority kinds the IEL will ever exercise — equivalently, **a threshold is declared iff its
    consuming kind is in the IEL's kind set** (`Ixn`→`t_use`, `Ath`/`Dth`→`t_authorize`,
    `Evl`/`Rev`/`Wit`/`Trm`→`t_govern`). A **user** IEL (kind set has `Ixn`/`Ath` + governance) → `t_govern`
    **mandatory**, `t_use` + `t_authorize` **optional and lockable**. A **federation** IEL (`Fcp`/`Wit`/`Trm`
    — no `Ixn`, no `Ath`) declares **exactly `{ govern }`** — `t_use` **and** `t_authorize`
    forbidden (a federation `Fcp` declaring any is **malformed → rejected** — the threshold-declaration analog of
    the facet-dependent role allowlist, cold-9 Q3 / 2026-06-29). A kind **omitted at `Icp` can never be exercised** — there is no
    first-introducing it on a later event (closes a mid-life authority-introduction). Thereafter a roster delta
    carries a threshold field **only when it changes** (present ⇒ **must** change; absent ⇒ unchanged) — the same
    present=delta / absent=inherit shape as the membership `add`/`cut` (inv 4) and the federationPin re-pin (inv 5).
    *Src:* design-pass §12 + F4 + F-K hardening
    2026-06-21 + threshold-declaration 2026-06-25. `[locked]`

## Divergence & federation
13. **Divergence is permanent and visible; it is scoped to T1 content; recovery is a plain rotation (first-seen,
    2026-07-08).** A **divergence** is two distinct events at one position. It splits by the one witnessing test
    (inv 17 / adversary-cases): **content (`Ixn`)** is single-key-authorable → **first-seen** (witnesses take the
    first, decline the copies) → recoverable; a **key change (sealed)** is not → **record-both** (both branches
    retained → the walk detects; witnessing is first-seen too now, one sibling — revised 2026-07-11) → a second
    *accepted* sealed branch is proof of subversion/collusion. **There is no repair *event* and no recovery key** — the `Rpr`/`Rec`/`Ror`
    machinery, the archival-tail rule, root-condemnation, and the `fork` role are all **deleted**. **Eviction is an `Evl` with a roster `cut` (first-seen, 2026-07-08):** evicting the divergence-causing member **must** be inseparable from the burying — were it a later event, the still-rostered member races a fresh `Ixn` at the resolved tip → re-fork → indefinitely (a timing attack) — so the eviction rides an **`Evl` carrying a `cut`** (a required `cut` + optional `threshold`, never an `add` and never `threshold`-only — inv 4 / inv 12), `Rot`-anchored like any `Evl`, priced the **outgoing** `t_govern` (pre-change, so an `Evl` can't lower its own gate before cutting — else a single actor could drop `t_govern` and cut everyone else out in one event), with the **post-cut roster re-checked against the inv 12 bounds** (a cut violating a hard bound — a hostage `threshold = |roster|` at `|roster| ≥ 3`, an emptied roster, or a sub-floor threshold — is rejected → a simultaneous `threshold` drop or reincept; a cut to `|roster| = 2` is accepted-with-warning). One sealing event **buries the fork *and* evicts at `v_{d-1}`**, so the member is gone the instant the fork resolves. The burying seal + the two competing content branches fit **one atomic page** (`2·MAXIMUM_UNSEALED_RUN + 1 = 129` — both branches ≤ `MAXIMUM_UNSEALED_RUN` + the burying seal, area-kel). The **cut target is operator-chosen** — the fork-causer is the motivating case, not a structural check (the verifier can't tell operator from adversary). **A burial is NOT final-on-arrival against a lagging node (the stale-burial re-fork):** a node **behind on gossip** may hold only one branch (reading the chain **Active**) and accept a fresh content `Ixn_c`; the incoming burying seal, attaching at the pre-burial tip, then lands as a **sibling of `Ixn_c`** → a new `{Ixn_c, seal}` fork. **On a witnessed chain this never goes LIVE:** the burying seal is always-witnessed and seals on arrival; a witness already holding it declines `Ixn_c` (dead / below-seal content — federation §1e), and non-witness nodes accept nothing sub-threshold — at worst `Ixn_c` earns receipts in the propagation window (durable, like all receipts), and is below-seal-inert the moment the seal lands (witnessed-but-dead, re-issued; no freeze). The residual is witness-compromise, where nothing gates `Ixn_c`. **The resolution is burial by position + ascent, not a second event:** any losing branch — held, missed, or **grown after** the burial — has its **first event locked below the advanced seal** (seal-cap) and **everything built on it dead on ascent** — **deadness ascends: an event whose parent is dead is dead** (the per-event seal-cap locks only the *first* event; the ascent rule kills the growth). So a signing-key (tier-1) adversary who keeps extending a dead content branch merely spews dead events into a **bounded** fork — depth-capped at `MAXIMUM_UNSEALED_RUN` per lineage, breadth bounded by **retention** (≥ 2 kept per position, the rest droppable) with the **one-content-sibling witnessing rule** on top (a witness signs the first content sibling at a position, declines later ones; **sealed** siblings witnessed **one** per position now (first-seen, like content — revised 2026-07-11, cold F1); a second sealed receipt is witness misbehavior, and two *accepted* sealed branches prove `disputed` via the data-local walk — federation §1e) — then the depth-cap forces a seal-advancer → `disputed`. Either way there is **no `{sealed, sealed}` collision from content and no reincept** — the all-content case converges to Active (the **content-completeness** of the model). **The KEL / IEL asymmetry:** a **KEL recovery `Rot` self-neutralizes the culprit** — it rotates the signing key out and re-commits the next rotation reserve (`rotationHash` req), locking out whoever forked with the old key, so the culprit can mint **no new fork** after it propagates → **one `Rot` terminates**, no re-fork loop (termination is the `MAXIMUM_UNSEALED_RUN` cap on the fork window + key-rotation closing new forks). An **IEL burying seal rotates no identity key** (an IEL is a threshold over member KELs), so an **adversarial** re-forker is *not* neutralized by the seal — termination needs a **roster change**: an `Evl` **`cut`** evicting the culprit. A **benign** gossip-lag `Ixn_c` (an honest member's content on a lagging node) needs no cut — it is re-issued as honest members catch up. **Operational, not a new mechanism** — freeze-on-collision, the `Evl`-cut, and content-rail serialization (the fenced single content submitter — area-iel §5) are the levers. **Content-rail serialization is a LIVENESS/waste discipline on a witnessed chain (2026-07-02):** the witnessing floor prevents the content fork forming, so the un-serialized cost is stalls + re-issuance, not terminality. **Sealing serialization is now liveness-only too (revised 2026-07-11, cold F1):** an honest double-seal is **declined** (first-seen, one sealed sibling per position) — it never reaches threshold, so two honest sealers racing stalls and re-issues, never bricks; only witness collusion (a provable double-sign) yields two *accepted* sealed → `disputed` (the floor never gates the first sealed sibling). **On-arrival completeness** splits on the **tier of the un-buried branch**, not a blanket freeze: (i) an **un-buried content** branch does **not** freeze the chain — the burying seal is **accepted**, the loser dead on ascent (a **bounded forked chain**, depth ≤ `MAXIMUM_UNSEALED_RUN` / lineage, breadth by retention + the one-content-sibling rule, witnessed but never canonical, re-issued forward — **never orphan-dropped**); (ii) an **un-buried key-change (sealed)** branch **at the last seal** is **never buriable** → ≥ 2 **witnessed** sealed → **`disputed`** (validated-not-trusted, inv 17) — you can't overturn a witnessed rotation; a **below-seal** sealed straggler, by contrast, is **dropped** (inert — not witnessable past the seal; the backdate defense, revised 2026-07-11). So a content fork is **final once its burying seal lands**, but a sealed fork is **terminal** (reincept) — strictly *final barring the eclipse residual*, fail-secure (the beacon is a detection oracle, not an absence-certifier; inv 8). **Cross-layer (SEL ↔ owner IEL) — the witnessed-SEL redesign (2026-07-12, area-sel):** a SEL is anchored to its owner IEL (kind-strict, inv 4) for **authorization + the finality-floor**, but it is **its own witnessed chain** for **fork-prevention / detection** (first-seen at its `(SEL-prefix, serial)`). **The theorem _a valid SEL fork implies an IEL fork beneath it_ is RETIRED** — one IEL `Ixn` can name two competing same-serial SEL events (opaque anchors) and skip-unattributable makes the tips observer-dependent under a **linear** IEL, so a SEL *does* fork under a linear IEL; the SEL's own witnessing closes it (area-sel §1c). **Inherited IEL deadness SEVERS the SEL** at the earliest dead anchor (no repair → the post-sever portion is un-verifiable), rather than the SEL riding the theorem; a live SEL content fork locked below an IEL seal is buried by a SEL-level **`Sea`** (anchored by an IEL `Evl` — area-sel §1d/§1e). A **signing-key (T1) compromise is fully deadenable** — no reserve → no sealed event → one recovery `Rot` buries the whole tail (all content) → every anchored SEL event severed, no reincept. **Two foundational rules govern every recovery:
    (1) only tier-1 content is *buriable* (content `Ixn`; on the SEL also the floor `Pin`) — a **sealed (T2)** event is never buried/overturned** (reversing
    a rotation resurrects retired keys — the backdate/resurrection class — and un-doing a kill breaks a third
    party's reliance); **(2) you never extend an adversarial event** — a recovery extends only the submitter's *own*
    event or the shared pre-divergence ancestor `v_{d-1}`. *(`Ixn` is plain content — the round-3
    `content: user | governing` flag is **removed**; its one intended user, the federation clock, is **not** an SEL
    event but an **inline timestamp value** on each federation `Wit`'s `manifest.clock` — inv 4 / federation §1f.)* A divergence
    is resolved by **tier, not identity** — chain data can't tell operator from adversary (both branches were
    authorized when they landed), so resolution turns on **tier**, never on who is presumed legitimate.
    **Recovery — the universal rule (first-seen):** you attach a **burying seal-advancer at your last good event** —
    a `Rot` / `Wit` / `Trm` on the KEL, a sealing event (an `Evl`, or a `cut` `Evl` when it also evicts) on the IEL — retaining your
    branch and burying every competing **content** branch below the new seal (they die on ascent). Rule 2 is
    automatic (you extend your own branch). **When the retained branch's own tip is *terminal* (a `Trm` — identity/SEL
    terminate), no burying seal is authored** — a terminal admits no successor; the sealed branch **wins on
    tier-rank** and the losing content is buried non-canonical (`{Trm, content}`, matching landed protocol-doctrine).
    **A kill-anchor (`Rev`/`Dth`) is NOT terminal** — it seals a kill on a *target*, not its host IEL, so the IEL
    continues; `{Rev|Dth, content}` is therefore **recoverable** exactly like `{Evl, content}` (the kill-anchor branch
    survives, the content buried + re-issued), terminal only when it is one of ≥ 2 accepted sealed branches. To both resolve a
    content fork **and** identity-kill, a `Trm` on the winning branch does both in **one** event (it buries the content
    loser below its own seal and terminates). *Not* the common/divergence ancestor unless you authored nothing past it
    (burying there would drop your own content when your `Ixn`s precede the adversary's). The check is one question:
    **is any competing branch you must bury a *sealed* branch (a `Rot`, `Evl`, `Ath`, or `Rev`/`Dth`)?** **No** (all
    content `Ixn`) → **recoverable** (your burying seal drops them; your retained branch may carry your *own* `Rot`,
    kept-not-buried). **Yes** → **not** recoverable (you can't bury a sealed event — rule 1; extend it — rule 2; or
    out-seal it — a second accepted sealed branch is `disputed`, terminal) → **reincept**. So the rotation reserve defends the
    **signing** key (a T1/content compromise), **not** the **rotation** key — a hostile `Rot` (reserve theft) is the
    point of no return.
    **The disputed / data-local view (node-agnostic):** the recovery check above is *party-relative*; the symmetric,
    node-agnostic condition is **branch-level** — **≥ 2 branches each carrying an accepted *sealed* event past the fork** is
    **disputed**, terminal for *everyone* (any party retains only its own branch, so a second accepted sealed branch always
    lands in *some* party's competing set). It is **data-local**: any verifier walks it from the retained branches — a
    node **retains** a competing branch as non-canonical evidence (keep-all-data, not discarded at the seal-cap), and
    the **witness beacon** enumerates the competing branch SAIDs so a one-branch holder fetches and walks the rest (the
    federation **propagates**, never decides). A **witnessed** sealed event competing **at the last seal** forces `disputed` (every
    sealed event is a seal-advancer → a spine fork, detectable by either walk), so an omitted **witnessed** `Rot` can't be hidden by sealing
    past it (its receipts enumerate it); a **below-seal** *un*witnessed sealed straggler is **dropped** (inert, backdate-safe — revised 2026-07-11). Unnamed content branches close below the seal, dead on ascent (inv 4). The seal-advancing events form a
    `previousSeal`-linked **spine** on which a sealed divergence is a single visible fork (inv 17). `{Rot, Rot}`
    is moreover a **confirmed reserve compromise** (two valid rotations reveal the *one* reserve preimage at `v_{d-1}`);
    `{Evl, Evl}` is terminal for the same branch-level reason but is **not** a reserve-compromise proof — disjoint
    sub-quorums reveal *different* preimages, so it can arise from an honest partition (hence content/sealing
    serialization). **Reincept** is what a party does when **no recovery exists for it**: a **reserve compromise**, or a
    **competing sealed branch it did not author** (a key-state branch you didn't author is un-buriable → the point of
    no return; the party that *did* author it recovers by **retaining** it). This is **broader than `disputed`** —
    `disputed` (≥ 2 witnessed sealed branches, node-agnostic) forces reincept on *everyone*, while a *single* sealed branch you
    didn't author reads `forked` yet still forces *your* reincept.
    *(The `../kels` diagnosis: kels classified `Rot` as **non-sealed**, so a `{Rot, *}` fork was "recoverable"
    and a recovery could *overturn* the forked `Rot` (its divergence-ancestor-extending shape) — un-rotating,
    resurrecting the retired key: **the backdating attack vdti exists to fix**. vdti treats `Rot` as a **sealed
    branch**, so a `Rot` you didn't author is un-buriable and recovery is forbidden. The one case
    kels lacked — a *single* sealed branch **kept by its author** (its competing branches all content) — is exactly
    what vdti permits; every other sealed-branch divergence stays terminal, as in kels's "sealed divergence
    is terminal". There is **no challenge
    event**: burial (rule 1) and extension (rule 2) are both out, and a challenge reaching a past serial would be
    the backdate kill-switch — that surface is closed structurally by the seal-cap + the spent-reserve-preimage
    rule (Rot'@v_M — a spent rotation reserve can only forge a late fork, declined), not by adding an event.)*
    **Trust on a divergent chain — the seal is the boundary (walk/trust, locked 2026-06-22).** What a consumer may
    honor splits on *recoverable vs terminal*, but the cut is always the **seal**, never the divergence point:
    everything **at-or-below `last_seal_advancing_event` is permanently final** and honored regardless of any later
    divergence — **with the tier qualifier (cold N7, 2026-07-01; revised 2026-07-11): "final" against later *content* divergence
    _and_ against a below-seal *sealed* straggler** — the sealed *linear* events are immutable, and a **competing
    *key-change* (sealed) branch that forks below the seal is _dropped_ (inert), not disputing:** it does not retreat
    the clean seal (the **backdate defense** — witnessing it would let a total-key-compromise adversary mint a
    fabricated historical fork years later; federation §1e). A sealed dispute forms **only at the last (clean) seal**
    — two *witnessed* seals there, needing a provable witness double-sign (inv 13 F4).
    (the verifier surfaces it — inv 8); everything **above the seal** carries tier-1-only durable auth and
    becomes durable only when a later seal-advancing event lands **cleanly** past it. A **recoverable** divergence's
    burying seal seals the surviving branch → its above-seal anchors become durable; a **terminal** divergence never seals
    → its post-seal window stays **suspect** (whole-*above-seal*-suspect — **not** whole-chain: below-seal stays
    **structurally** final — immutability, *not* a warrant of honest authorship; a current-key compromise that seals
    its own content below the seal is the separate current-state-compromise limit, which a divergence neither creates
    nor cures). Survivability of a member whose KEL goes terminal is decided **above** it, by **IEL threshold redundancy
    + a `Evl` eviction** (inv 12), never by salvaging the suspect chain's own tail.
    **IEL distrust is forward-only (locked 2026-06-22).** An IEL event is trusted iff a **threshold** of members
    anchored it (fresh participation, inv 5), so a rogue member KEL is **inert alone** — it can't reach
    `t_use`/`t_govern` — and the quorum's distrust *is* **non-participation** (don't co-anchor) **+ a `Evl`
    eviction**. A **retroactive** per-event distrust declaration is **forbidden**: a quorum that could retroactively
    un-trust its own history would hold the very **backdate kill-switch** this invariant closes. Trust is decided at
    participation time; an event the quorum co-signed (even alongside a since-compromised member) **stands**, and
    remediation is **forward** (revoke what it granted, evict the member), never retroactive. (So there is **no
    cut-member cap** at the IEL — the member's own seal bounds its past; the SAID-pin bound survives only for
    delegate-rescission, which has no quorum and no clock — inv 14 / delegation §5.)
    **A divergent chain freezes ORIGINATION; the reading is a pure walk (F-F, reframed 2026-07-03 — resolves cold F2 / warm H1).** Separate two things a node does — **originate/admit new work**, and **read the chain's state** — because conflating them made the reading arrival-order-dependent (the F2/H1 bug):
    - **Origination freezes.** The instant a chain holds a **live** fork (two **distinct** — different-SAID — events at one position, at-or-above the **derived** seal), a node **originates no new work** — content, governance, rotation, kill — that would **extend the forked position**; the only event it accepts is the one that **resolves** a content fork: a **burying seal-advancer** on the winning branch (a `Rot`/`Evl`/`cut` `Evl`), which attaches at the winning branch and seals past the loser rather than grow the fork (a sealed fork is never resolvable — it is `disputed`). This is a **merge-origination posture**, *not* a stored state flag.
    - **The reading is a pure walk of the held set (`region()`).** The verdict — Active / `forked` / `disputed` — is computed from the events the node holds, with the **seal derived** from them (the highest cleanly-linear seal-advancer). So "frozen" never makes identical held sets read differently: a **fork-first** node and a **seal-first** node holding the same events read the same thing. A **content** fork that a later-held seal-advancer buries below the new seal re-reads **Active** on every node, order-independent (the loser is below-seal-inert — you can't fork the past). A **sealed** fork **at the last seal** is never buried (two *witnessed* seals there → `disputed`), so its origination-freeze persists until reincept; a **below-seal** sealed straggler is **dropped** (inert — it does not retreat the clean seal, the backdate defense), so it never disputes the past. `log.md`'s "state is computed from the events the node holds, never a flag" is now literally true.
    - **The safety shape-gate runs at the acceptance point (Jason 2026-07-03).** Rejecting an **invalid shape change** — a seal-advancer that would bury a *sealed* branch — is enforced by the **witness** (refuse to witness → the shape never reaches threshold; a non-witness's merge pre-check is just "threshold met?"). Merge otherwise just integrates (keep-all-data) + the seal-cap; it does not stick-freeze the reading. Content-fork **prevention** (one-content-sibling + witnessing floor) is **witnessed** — and every chain is federation-witnessed (no direct mode); the residual is a **witness compromise**, where a content fork forms, reads `forked` (fail-secure), and resolves by burial.
    (**exception:** a `{Trm, content}` / terminal-tip divergence needs **no** burying seal — the terminal `Trm` is the single sealed branch and **wins on tier-rank**, the content buried non-canonical; see *Recovery — the universal rule* above.) This is the founding
    insight of the primitive (it's why `../kels` exists). **Divergence is *distinct*-events-at-one-position;
    identical events dedupe — SAIDs are content-addressable, so two byte-identical events ARE one event** (the
    submit path accepts an already-present event idempotently, never as a second branch; detection keys on distinct
    `witnessed_said`, federation §1e). So a `{kill, kill}` collision (two competing `Rev`/`Dth` kill-anchors) is always of **distinct** events — only an
    *idempotent re-submit* of byte-identical bytes dedupes; two **independently authored** kills are never byte-identical
    (each commits its own `pins`/position), so even the *same* kill by two sub-quorums is two SAIDs → a genuine collision,
    serialized away (one submitter), never a silent merge (R3-1). *(The "both revoking the same cred → dedupe" example was
    **wrong** — corrected 2026-07-05, freshread-8 E; a revocation rides the issuer IEL (its `kills[]`
    declaration — the authoritative fail-secure kill), and its fail-open lookup SEL is **majority-witnessed
    first-seen at its own `(prefix, serial)`** (witnessed-SEL redesign, area-sel §1c), so two parties revoking
    one cred **converge on the first-seen `Trm`** — not because a lookup can't fork under a linear IEL (it can;
    that theorem is retired), but because the SEL's own witnessing takes the first and declines the copy.)* It makes F-F's scenario *unreachable*: a sealing event can never sit
    *above* an **unresolved** divergence, because a node originates nothing onto a live fork — the only append onto
    one is a **content-fork-burying seal-advancer** (which resolves it), never a new sealing event. (A divergence with
    **≥ 2 accepted sealed branches** — e.g. `{Evl, Evl}` — is disputed → reincept; a `{Evl, content}` collision is
    **recoverable** — the `Evl` survives and its seal buries the content.)
    *Src:* §4 + Jason 2026-06-20/21. `[locked]`
    **Consequence — a network split + sealing (F7, refined 2026-06-21):** if the network splits, one half can
    author a `Evl` while the other issues content at the same position; on heal they collide. The `Evl` branch
    survives and its seal buries the content, so **`{Evl, content}` is RECOVERABLE**
    — **not** an automatic brick. Only **`{Evl, Evl}`** (both halves seal → ≥ 2 accepted sealed branches) is
    **disputed → reincept**.
    **The kept `Evl`'s roster is canonical (Finding 14a, 2026-06-21)** — a subsequent event operates in the world
    after it; any members the `Evl` *added* are already T1-consent-anchored (a precondition of that `Evl`'s validity),
    so the post-`Evl` authorizing set is well-defined and needs no new consent.
    **Handled operationally** (one designated sealing submitter + hold sealed events under a suspected split) — now
    only to avoid the *both-sides-sealing* terminal case, not every sealing-during-partition event; witnesses
    make a bricked state detectable on heal. A protocol-level "block a `Evl` unless its parent is witness-confirmed"
    gate was **rejected** — each half's own witnesses confirm its events, so it passes inside the split, and it
    freezes sealing whenever witnesses are unreachable (a halt-by-DoS lever). See `vdti-area-iel.md` §4 ★★.
    `[locked]`
    **Consequence — kills are always sealed; a validity bound is a hard contiguous boundary (LF1/F-B/F-H,
    locked 2026-06-21):** a **kill** (revoke/close/rescind/terminate) is always **sealed on arrival** (anchored
    in a **`Rev`** or **`Dth`** — the dedicated sealed kill-anchors, T2, distinct from `Evl`), so it is **terminal — never in the
    recoverable region** and can never be buried (closes the silent-un-revoke, F-B; there is no
    unsealed window to un-do, LF1). *(A kill-anchor (`Rev`/`Dth`) is sealed/terminal-on-divergence like any T2 event, so a
    `{kill, kill}` split-collision of **distinct** kills is **terminal → reincept**. **R3-1 RESOLVED (2026-06-21):
    no merge — corrected rationale (round 4).** You **cannot reorder** events (the SAID commits `previous`, locking
    the chain order) or **bury a sealed event**. So a "merge" is **not** a reorder — it would mean *removing*
    both colliding kills and **re-authoring** new ones with the full `t_govern`/`t_authorize` the IEL requires (enough
    devices re-signing): a carve-out against sealed-divergence-is-terminal. The kills **do commute** (a key-less
    kill-anchor resurrects no key), so the merge is **sound in principle** — we **decline** it on model-cleanliness /
    don't-relax-finality grounds (minimize carve-outs), **not** because it's unsound, and **not** the earlier wrong
    "zero availability gain" (a merge *would* preserve the identity; no-merge forces **reincept + reissue**).
    **Only a byte-identical re-submit dedups** (SAID over content; sigs are adjacent, but the `pins`/`pin` an event
    commits **are** in the content, so a different signer subset anchors different member-KEL tips → a *different* SAID —
    "same SAID regardless of signer subset" was **wrong**, corrected 2026-07-05 freshread-8 E), so "both sides revoke the
    same cred" is **not** a dedupe — two independent acts are distinct events (different pins), a genuine collision
    serialized away; only **distinct** kills at one position
    collide — rare, and avoided by serializing kills (one submitter; no free-for-all kills under a suspected split,
    which is load-bearing, not a nicety).)* Separately, a **validity
    bound** (a rescission's bound, or a compromise rewind) removes a **contiguous suffix** of a chain — by
    chain **linearity** every event builds on the prior, so you can only invalidate a contiguous tail, never a
    non-contiguous subset. **Nothing past the bound is honored — grants *and* kills alike**; there is **no
    per-kind exception across a validity bound** (honoring an event past the bound = trusting an un-anchored,
    invalidated event). In a compromise the invalidated suffix is exactly the attacker's contiguous tail from the
    divergence point — legit and attacker events never interleave into a subset you'd want to keep (even a
    multi-member IEL where a compromised member's event is silently extended yields one contiguous suspect tail).
    So "individually revoke a grandfathered cred of an already-rescinded issuer" (F-H) is not a structural
    operation — it would need a valid anchor past the bound; recovery is **reincept the delegate** (a new prefix —
    the rescinded prefix stays permanently capped) + re-grant, or reissue. *(No "rewind the bound" — a sealed kill
    is never retracted; the bound is **set once** at the rescission `Trm` — no move later (un-kill) and no tighten earlier.)* **I1:** a bound
    un-honoring a kill the rescinded party placed past it is **not** an un-doing of a kill (F-B) — it withdraws that
    party's *authority* wholesale (their later acts, kills included, go with it). The not-interleaved guarantee
    means a correctly-set bound catches only the distrusted party's contiguous tail; if it catches your own
    legitimate events, you mis-set it (operational — you broke your own chain). See `vdti-area-delegation.md` §5. `[locked]`
14. **Federation = a restricted IEL (kinds `Fcp`/`Wit`/`Trm` — `Fcp` is the federation IEL's inception marker (§inv 4 / federation-ref §2, a structural disambiguator the verifier dispatches on, *not* a trust carve-out), and `Wit` is the governance kind replacing the user `Evl`; the set is a restriction *plus* the `Fcp` marker + `Wit`, not a pure subset; A3 2026-06-28); witnessing is as-of-context — prevention for witnessed content (the witnessing floor, federation §1e), detection for the rest; the roster is a delta.**
    Receipts are adjacent (unanchored), evaluated as-of the event's `federationPin`, **never re-witnessed** —
    durability: a cut witness's *established* receipts keep counting. The **roster is a delta** — the federation's `Wit` carries
    `add: Prefix` (a **single** witness per `Wit`, except `Fcp` inception — cold-seam P5: standing up a witness is deliberate, and ≤ 1 unsynced witness per transition can't reach a majority `threshold`, closing the multi-add straddle) + `cut: Prefix[]` (a list — cuts remove synced witnesses, no straddle), reconstructed by accumulating while walking, with a
    **hard cap on the live set** (over-cap → reject as a DoS). A `cut` removes a witness **by prefix**; the
    **federation clock** then bounds *which* of its keys may still sign valid receipts (a receipt counts only
    within a federation-pinned key-window — §1f), so a cut witness's forward-rotated keys never count (being out of
    the roster, it can't earn a new pinned window). **The position-`terminator` is dropped (2026-06-21)** — the
    clock + rotation-pins subsume it (Finding 11); the witness's KEL stays usable. *(The cut-a-chain mechanism
    survives only as the **delegate-rescission** `bound` — delegations have no clock — inv 13 / delegation §5.)* **Backdate / dormant-chain forgery (S2) is closed
    by wipe + the federation clock — NOT the forward-floor alone** (corrected 2026-06-21). The forward-floor stops
    only an *active* chain pinning an old context; a **dormant** chain can be forged-extended with **harvested old
    witness keys** (the as-of-context roster still validates them, and there's no `B+1` to collide with). Closure:
    **(1) wipe-on-rotation-and-removal** (destroy superseded / removed *private* keys — durability unaffected, old
    receipts verify with *public* keys → no soft harvest target) **+ (2) the federation clock**
    (the **`clock`** role on each federation governance event's manifest (`Fcp`/`Wit`/`Trm`) — an **inline timestamp value**, one per governance event, sealed
    + monotonic) time-bounding each witness key-window so a closed-window key can only stamp old receipts → a dormant forgery
    reads **stale** → detectable, fail-secure. (The position-`terminator` is **dropped** — this time-bound replaces
    it; Finding 11, 2026-06-21.) **Rejected: history-pinning** (the clock gives detectability without per-chain tracking).
    Residual: a *current* threshold-compromise (open windows) = the accepted `< threshold` byzantine assumption;
    rotation closes windows → past forgeries become detectable. **Three clock guards + a residual:** (1) the **365-day `MAXIMUM_WITNESS_KEY_WINDOW`** —
    a never-rotated window **auto-closes at `T_join + 365 days`** (no unbounded open window; federation §1f, cold-9 C2 /
    cold-10 F4); (2) a consumer rejects / stale-flags any federation **clock** time beyond `now + CLOCK_TOLERANCE_BAND` (no **future-dating** by a
    `t_govern`-compromised federation — round-5 F4); (3) a **receipt `τ`** is likewise capped `≤ now + CLOCK_TOLERANCE_BAND` (symmetric with the clock ceiling — cold-12 F5). **Residual:** detection of a *just-closed* window lags by the staleness threshold (round-5 F5 — note `F5` is overloaded: round-5 = this detection-lag, cold-12 = the receipt-`τ` ceiling above) → tight thresholds on high-value
    bindings, and a recent `cut` is freshness-sensitive. Witness rotation is **only** a synchronized federation
    **`Wit`** (the witness's KEL `Wit` **is** the rotation and anchors the IEL `Wit`; an
    off-ceremony `Rot` is unhonored — F3). See §1a / §1f. *Src:* §7 + federation-ref + B/F-A +
    S2 resolution 2026-06-21 + round-5 F3/F4/F5. `[locked-candidate]`

## Inception & the pin mechanism
15. **Inception tier follows what it establishes; every SEL's `Icp` is floored by its serial-1 event.**
    - **KEL `Icp`** = T1 (the root, self-authorizing — no chain below it).
    - **IEL `Icp`** = T2 (it establishes *governance* — roster + thresholds; a genuine state-establishment).
    - **SEL `Icp`** = **T1** (it establishes single-owner *data*, not governance; an IEL `Ixn` anchors its v1, never the `Icp` itself — see below). The
      `Icp` carries **no `pin`** (it must stay recomputable for lookup), so it is **floored by its serial-1 event**,
      which carries the pin the `Icp` can't (`pin == anchoring IEL Ixn.previous`). Now that **every event pins**, that
      floor is **any event** — a content `Ixn`, a `Trm`, etc. — so a bare **`Pin` is the fallback floor, used only
      when inception carries no other first event** (an *incept-and-sit* SEL — e.g. a cred issued with no immediate
      content or kill must still floor at issuance, its as-of can't be deferred). A shared-doc author is also
      incept-and-sit (`{Icp, Pin}` — endorse before editing). Where the inception **does** carry a first event, that
      event floors instead — `{Icp, Trm}` (a rescission, born-to-kill) needs **no** separate `Pin` (generalized
      2026-06-27 from the former 'serial-1 `Pin`, uniformly'). **The IEL anchors this serial-1 event** (the *v1*) —
      `manifest.anchors` → the `v1`, **never the `Icp`**: the **`Icp` is never anchored in a SEL**; it rides via
      `v1.previous`. So a `Pin` **does** anchor (it's the `v1` when there's no other first event), and every SEL
      uniformly reads `{Icp, v1, …}` — anchor the `v1`, `Icp` via `previous` (2026-06-27).
      **Authentication is the v1's anchor, never the `Icp` (S1, 2026-06-27):** the `Icp` is unsigned, recomputable
      content (`prefix = derive(owner, topic, data)`), so it proves nothing alone — a SEL is validly issued **only**
      if its `v1` resolves to a real event on the **claimed owner's** IEL (`anchor.prefix == Icp.owner`, the `v1`
      named in that IEL event's `anchors`, `v1.previous == said(Icp)`); reject a SEL whose `v1` is absent or whose
      v1-anchor's prefix ≠ `Icp.owner`. A fabricated bare `{Icp}` naming a victim issuer is **not** evidence of issuance.
      A **credential is a direct-anchored SAD, not a SEL** (issuance SEL dropped 2026-07-09, area-sel §1): the issuer
      anchors the **issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** on its own IEL via an
      `Ixn`, and that anchor **is** the validity proof (an issuance commitment with no resolvable anchor on the
      issuer's fresh IEL is not validly issued). The cred body carries a checked-locator **`issuerPin`** (= the anchoring `Ixn`'s `previous`; the as-of is
      still the **anchoring position** it finds, never a trusted claim). The **revocation kill-target** `hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`
      is a separate flat hash of the same preimage → its `{Icp, Trm}` lookup SEL (built two-pass, prefix ≠ target);
      safety is **owner-rooting** (only the owner IEL declares a kill / anchors the cred), **not** prefix-secrecy.
      A *private* cred stays private because **`cred.said` appears nowhere raw** on the public IEL — issuance
      commitment, kill target, SEL prefix/said are all hashes of it, and the `nonce`-in-body keeps `cred.said`
      unguessable (fully closed — inv 16).
    - **Lookup-SELs** (built from `Icp{owner, topic, data}`, usual two-pass prefix/said; a lookup `Icp` carries
      **no `content` flag** — that marks content (area-sel §1f), and a **re-establishable value** lookup adds a
      **`lineage`** counter; the `kills[]` `target` is a
      separate flat `hash('{topic}:{owner}:{data}')` ≠ prefix): a **revocation / rescission** lookup-SEL is
      `{Icp, Trm}` — the terminal `Trm` is the kill (sealed via an IEL `Rev`/`Dth`). **The primitive says only: a
      `Trm` commits whatever its manifest commits (R3).** **Bound placement is per-feature:** cred — no bound, the
      `Trm` carries only its pin; **delegate** — the `Trm` carries only its pin, `bound` public in the `Rev`/`Dth`'s
      `kills[]`; **doc-member** — the `Trm` commits a **gated rescind-doc** (its manifest) carrying the `bound`
      (`kills[]` holds only the blind target — participant-blindness). So "the `Trm` carries only its pin" is
      **cred+delegate**, not universal (B1 fail-secure rework 2026-07-09; area-iel §1). The serial-1 **event** floor
      is universal (above), not lookup-specific — for the `{Icp, Trm}` the `Trm` **is** that floor (no separate
      `Pin`);
      the `Pin` *kind* does **only** the pin re-pin (`t_use`/T1, **not** sealing) and is the **pin-only re-pin at
      any serial** (its serial-1 instance is the issuance floor; a later content-less re-pin is also a `Pin`).
      **`Ixn` and `Pin` are disjoint:** an **`Ixn`'s manifest is required** (≥ 1 `payload` SAD — a manifest-less
      `Ixn` is malformed), so a pure re-pin is a `Pin`, never a payload-less `Ixn`; no event is expressible two
      ways. *(There is no SEL
      re-seal `Fld` — dropped with the repair machinery; a plain content SEL floors down to the owner IEL instead.)*
    - **SEL `Trm`** = the kill — **always sealed on arrival**, anchored in one of the two dedicated sealed
      kill-anchors (**T2**; the identity-kill `Trm` is also **T2**): an **IEL `Rev`** (revoke / close your own credential
      or app-SEL, **`t_govern`**) or an **IEL `Dth`** (deauthorize a granted delegation / doc-membership,
      **`t_authorize`**). **No delayed / unsealed form** — a kill is **monotone** and must be permanent on
      arrival, so it rides a sealed kill-anchor. Because a `Rev`/`Dth` is terminal-on-divergence, the kill's
      anchor can never be buried (silent un-revoke **F-B** closed by construction), and there is no
      unsealed window to un-do (**LF1**). Terminate = a cred's **revocation** / an app-SEL **closure** (via `Rev` — a revocation lookup-SEL `Trm` + the `Rev`'s `kills[]`);
      **rescission** is the same kill shape on a lookup-SEL — a lookup-SEL **`Trm`** anchored by a `Dth`
      (whose `kills[]` carries the `bound` — **delegate**, public; a **doc-member** rescission's participant-identifying
      `bound` instead rides a **gated rescind-doc committed by the `Trm`**, `kills[]` carrying only the blind target —
      R3, shared-documents §1; the **cred/delegate** `Trm` carries only its pin — 2026-07-09). The kill-anchors are **distinct from `Evl`** (roster/threshold-change only, always
      `t_govern`): they carry no roster delta, so a roster change can never ride at a kill's count (**S1**
      closed), and a `Rev`/`Dth` **forces a `Rot`** (each authorizing member — a T2/permanent act needs a ≥T2 KEL anchor;
    **R3-2's "signatures only" is corrected, A** — the `Evl`-vs-kill-anchor distinction is the roster delta, not the
    rotation). **Reverses the F3 delayed-`Trm`** —
      re-aligns with `document-policy §F`'s sealed-on-arrival (right all along). The *count ⊥ tier* principle
      (inv 11) survives; *count travels with the anchored kind* survives **re-scoped** — every IEL kind now prices
      itself ([inv 12]); only the optional/delayed finality is gone. **Restoring** a killed thing is **never a
      retraction**: the party **reincepts under a new prefix** and is granted / issued afresh — a re-grant of the
      *same* (rescinded / revoked) prefix does **not** restore it (its kill-locus / terminal `Trm` permanently caps
      that prefix). [R3-3]

    *Security:* a compromised T1 signing key can already issue content `Ixn`s in your name, so letting it also
    *create* a SEL adds no blast radius — T1 inception is sound. Revoking (T2) and establishing governance (T2)
    are the deliberate acts. **Boundary (F-I, 2026-06-21) — why issuing a credential is T1 but an authority-grant
    is T2:** a *credential* is **content** — one bounded, revocable claim to an external party (forging it = one
    revocable assertion). An *authority-grant* (a delegation, `Ath`) **expands who may act with your authority**
    going forward (forging it = an *ongoing* forgery — a new actor under your name). That asymmetry is why issuance
    is T1 (inv 11 "content") while a grant needs the reserve (inv 11 "authority-grant"). Residual: a T1-issuance
    compromise forges creds bounded by the **use-count** — an issuer a third party relies on should run
    `t_use ≥ 2` (inv 12, F10a). *Src:* Jason 2026-06-20 + F-I/F-J 2026-06-21. `[locked]`

## Addressing & lookup
16. **Logs are referenced by *prefix*; SAIDs are commitments, not lookup keys (F2, 2026-06-21).** A chain log
    (KEL/IEL/SEL) is fetched/queried **by its prefix**; within a log a query pages with **`since: <said>`** (a SAID
    cursor) — but `since` is **useless without the prefix** (not a global lookup key), and the **serial is never a
    reference**. The SAIDs an event commits (`manifest` roles, `previous`, `pin`, `since` cursors) are **integrity
    commitments**, verified against the by-prefix-fetched object — there is **no global SAID → event index**.
    **The two-hash prefix/said split is part of this (correlation resistance, 2026-07-03):** on a chain inception
    event `said(Icp) ≠ prefix` (two separate hashes — said.md §Derivation), so the inception's SAID is an opaque
    commitment like every other event's, **not** the lookup key. A single-hash design would set `said(Icp) == prefix`,
    so an application logging event SAIDs (audit / trace / debug — the SAID is effectively an event's primary key) would
    leak the prefix the moment it logged the **inception** event, correlating every other logged SAID back to the
    identity — the exact correlation this invariant otherwise closes. Everything *in the content* is already coupled to
    the prefix (the prefix is a content hash), so `v1.previous → said(Icp)` leaks nothing new; the SAID is the one
    derived handle that must not coincide with the lookup key.
    **Attribution on a standalone SAD requires a direct IEL anchor located by a checked `pin`, never a
    self-asserted *authority* pin — the custody fix (2026-07-03; direct-anchor rework 2026-07-18).** A binding a verifier must *resolve* (fetch the named chain and walk it) needs the entity
    **prefix** — a SAID has no global index (above) to invert. On a **chain event** a position pin is sound: it is a
    chain field corroborated by append-only `previous`-linkage (the SEL down-pin `owner`(prefix) + `pin`(SAID); the
    federation `federation`(prefix) + `federationPin`(SAID) — inv 5). But a **standalone SAD is not a chain event** —
    it sits on no chain, so a self-asserted position pin has **nothing to corroborate it** and is freely
    **backdateable**: pick an old position where a since-broken key was authorized → forge a "valid as-of-then" write
    (and over a long enough horizon *any* key breaks, so the backdate is real, not hypothetical). This is the exact
    self-asserted-pin forgery inv 5 already closed for documents. **Resolution (direct-anchor rework, Jason 2026-07-18) — an
    `owner`-bearing SAD is attributed by a direct append-only anchor on the owner's IEL:** the owner authors an
    `Ixn` whose `manifest.anchors[]` commits the SAD's `said` — a `t_use` content act only the owner's quorum can
    author, witnessed. That anchor **is** the write authorization. Custody carries **`owner`** (the writer IEL
    prefix) **+ `pin`** — the SAID of that anchoring `Ixn`'s `previous`, a **checked locator** (`pin ==
    anchor.previous`) finding the `Ixn` at `pin + 1`, one manifest, no scan. **`owner ⟹ pin`** (an `owner`-bearing
    SAD with no `pin` cannot be verified and is rejected — it reads ambiguous). A **credential** is the named
    instance (its `issuer` + `issuerPin` are `owner` + `pin`). The SAD's own `kind` names its type, so custody needs
    **no `topic`**. **`pin` is a checked locator, not the dropped self-asserted *authority* pin** — as-of authority
    stays the anchoring position (inv 5 — backdate-proof: forging it needs a fresh IEL `Ixn` at the owner's *current*
    tip, which a rotated-out key can't author and can't insert in the past → the threat reduces to
    current-key-compromise-at-current-time, the accepted limit, inv 13). **A SEL is a separate primitive** for
    *mutable* / *evolving* state or a *derived-address lookup* (the revocation / rescission lookup SELs); a SEL may
    *name* a SAD by `said` via its own action-topic, but never anchors the SAD's write. **Two orthogonal `Icp` fields carry the address model
    (area-sel §1f):** **`content: true`** discriminates content (v1-T1, handed) from a lookup (v1-T2,
    blind-recomputed) — verifier-enforced biconditional, and it **rides the prefix** (so content and lookups
    occupy distinct namespaces, and a content squat at a lookup address is impossible by construction — its
    prefix differs, and a v1-T1 at a lookup address is invalid). **`lineage`** (lookups only) is a pure
    re-establishment counter: a **re-establishable value** carries `lineage: 0, 1, …` (distinct prefixes) and is
    read by the **positive walk** (walk from `lineage: 0`, advance past a dead lineage, stop at the lowest live
    one); a **monotone** lookup omits it (absent-is-absent; `content` never carries it). **Structural, split by layer:** the SAD structural pass enforces only the **presence** rule (`owner ⟹ pin`; an
    `owner`-bearing SAD with no `pin` is rejected), and a consumer **verifies the anchor independently** —
    `verify_anchored_sad` locates the `Ixn` at `pin + 1`, confirms `said ∈ manifest.anchors[]`, and that the `Ixn`
    is a valid owner-authored event (the store is untrusted — end-verifiability; a generic `verify_sad` delegates to
    it whenever the SAD is owned). **Field rule: `owner` present ⟺ `pin` present** (an anonymous write carries
    neither). Because the SAD's SAID commits `owner` and `pin`, the pair `(owner, pin)` is tamper-evidently bound to
    the anchor location. **Reads are the separate axis** —
    `readers` (a read-authorization SEL membership, not a policy; the current-mode read policy is retired
    2026-07-16), independent of write attribution. **Encode:** `custody.md` (§The sub-fields, the direct-anchor
    §Attribution, §Two evaluation modes, §Four combinations, §Adversarial framing), the wrapper shape in
    `sad.md` / `availability.md`, landed `pin` refs (incl. `said.md`, `glossary.md`), and the `custody`
    refs in `vdti-area-shared-documents.md`. *Src:* Jason 2026-07-03. `[locked]`
    *Consequence (the private-cred boundary, F2 — B1 fail-secure rework 2026-07-09, CLOSED):* a credential is a
    **direct-anchored SAD** (no cred-SEL). **`cred.said` appears NOWHERE raw on the public IEL** — every public value
    is a hash of it: the issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`, the kill target
    `hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, the lookup SEL's prefix/said (two-pass over an `Icp` whose
    `data = cred.said`), and `said(Trm)` in `anchors[]` (opaque — needs the `Trm` body). A **holder** verifies
    issuance by recomputing the issuance commitment and matching it on the issuer's fresh IEL, and computes the kill
    target from the **preimage** `cred.said` — never from a public hash — to check status. A **private** cred's
    `cred.said` is high-entropy (body `nonce`) → not brute-forceable, so a non-holder recovers none of the hashes and
    can't compute the kill target. **"CLOSED" rests on BOTH halves (R4, warm F2 — the holder-vs-replica gap):** a
    non-holder can't *compute* the address, **and** the data-bearing lookup-SEL `Icp` (which carries `data = cred.said`
    **raw**) is **never published** — a holder *recomputes* the `Icp` locally to derive the prefix and fetches only the
    **pin-only `Trm`** by address, so no replica ever holds `cred.said` raw. (The never-publish is a **submission/serve
    build-constraint** — the write/serve path stores/serves only the pin-only `Trm`, so a by-prefix fetch of a
    revocation/rescission lookup SEL returns the `Trm`, never the `Icp` — **distinct** from the §1j by-SAID `kind`
    filter, which closes the separate by-SAID event-harvest vector; only a `cred.said`-holder can produce the `Icp`, so
    a stray submission self-reveals only.) State the never-publish rule or "CLOSED" over-reaches on the raw
    `data = cred.said` in the `Icp`. (The create-on-revoke `said(v1)` indirection is
    superseded — the qualified-hash-everywhere form does the same job, at issuance too.) **Confirm-a-known-subject, not
    bulk-enumerate.** (A **public** cred's `cred.said` is public and public revocation status is correct.)
    **Private cred bodies are not published to the shared store** (held by issuer/holder, disclosed peer-to-peer);
    only genuinely-public SADs every verifier must resolve for a public chain — the `roster`/`witnesses`
    config SADs (the `clock` rides inline in the federation manifest) and a *public* cred's body — are content-addressed by SAID (no privacy cost). *Build constraint:*
    the gossip / deferred-deps drain resolves missing deps by **gossip-push + by-prefix fetch**, never a by-SAID
    `get-post-sad`, for the revocation/rescission lookup-SELs (kels precedent — it never needed by-SAID); a public cred's SAD body is content-addressed by SAID. **Two rules added 2026-06-23:**
    (a) **every prefix-bearing query carries the prefix in the request body, not the address** (like HTTP QUERY — never a URL-encoding GET) — a path/query
    prefix leaks into common access/proxy logs that aren't otherwise privacy-controlled; (b) **all inter-node mesh
    traffic is encrypted** (ML-KEM-1024 KEM + AES-256-GCM AEAD) — receipts AND the events they propagate (generalized
    from gossip-only, 2026-06-23); confidentiality, not trust (trust is end-verifiable). Prefer **push over pull**
    (gossip events rather than an inter-node query → no second channel to secure; impl-notes). A private log's folded
    run stays **by-prefix** (never by-SAID-fetchable →
    the harvest stays closed; folding-idea Q4 — RESOLVED). **Residuals:** the public IEL still leaks issuance
    *volume/timing* — though folding issuances into the IEL's mixed `anchors[]` (alongside other SEL anchors) muddies
    the per-cred count for a passive observer, so the total *issuance* count stays muddied. The **receipt-based**
    `issuer ↔ prefix` correlation was formerly closed by not witnessing SELs (§2c Decision 1); **the witnessed-SEL
    redesign (2026-07-12, area-sel §1c) SUPERSEDES that** — a lookup-SEL prefix now rides its own receipt, an
    **unguessable** value decorrelated from the issuance commitment and kill target, exposed only to **semi-trusted
    federation infra** over the **encrypted** mesh (confirm-a-known-subject only, never invert; the
    exfiltration-during-a-compromise-window residual is the accepted `< threshold` byzantine class). The public IEL
    `anchors[]` still carry only **opaque** commitments. **The fail-secure revocation residual is grant-instance-gated
    confirm-a-known-subject (B1 fail-secure rework 2026-07-09):** revocation is a `kills[]` declaration on the
    issuer's IEL + a content-addressed lookup object, keyed by the flat hash `target =
    hash('{topic}:{owner}:{data}')` (distinct `topic` per kind; `data` = the grant-instance). You can only
    **confirm** a subject whose grant-instance you already hold (→ can compute its `target`); you **can't invert** a
    `target` back to a subject, so it is a bounded *confirm*, not a bulk-enumerate. A private cred / gated grant-doc
    keeps its `target` uncomputable because its `data` (`cred.said` / `hash(G | said_b)`) stays secret — and the
    `data` **never appears raw** on the public IEL (every public value is a hash of it, private-cred boundary
    consequence below), so this is **closed** for private subjects; a public cred's status is correctly public. So
    `issuer ↔ prefix` residual = **issuance stays muddied + confirm-a-known-subject on revocation** — the earlier
    create-on-revoke "revocation-list enumerable per issuer", and before that "leaks nothing" / "CLOSED", are both
    superseded. *Src:* Jason 2026-06-21 (kels addressing precedent); revised for §2c
    Decision 1 + B1 fail-secure 2026-07-09. `[locked-candidate]`

## The spine, the fold, and data-local detection
17. **The spine overlay + keep-all-data make divergence detectable from the data (2026-06-23).** The seal-advancing
    (sealed) events form a **spine**: every seal-advancing event carries a top-level **`previousSeal`** back-link
    to the prior one (the `Icp`, or the `Fcp` inception of a federation IEL / founder KEL, is the spine root). Following `previousSeal` renders the spine view
    (`Icp → seal → seal → …`); following `previous` renders the full **flat** chain. `serial` is **flat and
    unchanged** (no epoch re-count). No seal carries a `fork` role (the repair role is deleted — inv 4); a content
    loser closes below the burying seal, dead on ascent, committed by nothing. The retained run since the prior seal is **not committed** — it is the
    linear chain `[previousSeal..previous]` (nodes keep full bodies; the flat query returns them), and "content was
    folded here" is the derived predicate `previous != previousSeal`.
    - **Two views, one dataset.** The spine is verified by the **same walk algorithm** with `previousSeal` substituted
      for `previous`, yielding authority + a **terminal-divergence** view (a spine fork = two **witnessed** competing seals at the last seal = terminal) but **not recoverable content forks or content completeness** (that needs the flat
      walk). Served as body-carrying reads — `/folded` (spine) and `/flat` (full) — the prefix in the body, not the address (inv 16).
    - **Detection lives on the flat chain (the guarantee); the spine is a convenience pre-check.** Terminal = **≥ 2
      branches each carrying an accepted sealed event past the fork** (inv 13) — a **data-local** walk over **retained**
      branches (keep-all-data: a node retains a competing branch as non-canonical evidence rather than dropping it at
      the seal-cap). Skip-a-seal detection is the **flat walk's** (walking `previous` traverses the run; a skipped seal
      appears in it as a seal-advancing event, since a real seal carries its own `previousSeal`) plus **spine-fork
      detection** (the real skipped seal, once held, competes at its spine position). The spine alone trusts
      `previousSeal`; `/folded` is fail-secure — never a hidden authority forgery, worst case the eclipse residual.
      *(The former boundary-SAID O(1) pre-check is dropped 2026-07-01 — necessary-not-sufficient, and the guarantee is
      the flat walk regardless.)*
    - **Content-independence.** A sealed event self-validates against the **prior seal's key state** (on the
      retained spine, via `previousSeal`) + its own committed fields — content (`Ixn`) is key-state-inert, so
      re-validation never needs the content prefix. **So spine verification is content-independent** (it needs only
      the prior seal's key state) — yet nodes **keep the run's bodies** for the flat view (Jason 2026-07-01: the flat
      query returns them), which is what lets the `canonical` commitment go; **sealed retention bounds to ≥ 2 per spine position** (a spent preimage can
      mint unbounded distinct `Rot`s — two competing sealed branches prove terminal, then stop; the kels
      event-level rule lifted to the spine). There is **no `fork` commitment** (the repair role is deleted); every competing branch is **retained
      via keep-all-data** (a **content** loser is inert below the burying seal, its growth dead on ascent); the retained run's bodies
      are kept (retrievable by-prefix); only the truly *uncommitted* flood is dropped.
    - **Burial by position + ascent — growth-proof (first-seen, 2026-07-08).** There is no repair event and no
      `fork` root; a content loser is buried **by position**: its **first event** is locked below the burying
      seal (seal-cap) and **everything built on it dead on ascent** — **deadness ascends: an event whose parent is
      dead is dead** (the per-event seal-cap locks only the first event; the ascent rule kills its growth — so a
      losing branch a lagging node grows after the burial is dead on ascent, no follow-up). **A lineage is dead
      from its first loss, not only from a burying seal — you can't seal a buried chain (dead-on-ascent generalized,
      Jason 2026-07-11):** an event that **lost first-seen at its own position** (a sub-threshold competing sibling) is
      dead, and **everything built on it — including a `Rot`/`Evl` seal forged on it, or a buried chain built
      and then sealed — is dead on ascent**; a seal does **not** revive a dead lineage (honest witnesses, having
      first-seen-accepted the winner at the fork, decline the dead branch's descendants, so it never gathers the
      majority a seal needs — the first position wins). This **collapses every dispute to the fork:** two branches
      both **accepted** at a seal share their lineage down to a fork where **both** siblings are accepted — two
      majorities at **one position** — a **provable witness double-sign there** (§1e); no **cross-position** dispute
      exists (the below-seal straggler drop is this rule's seal-cap special case). Each dead **lineage** is
      **depth-capped at `MAXIMUM_UNSEALED_RUN` events past the last seal** (a deeper event forces a seal-advancer, sealed → `disputed`);
      breadth is bounded by **retention** (≥ 2 per position — the ≥ 2-per-spine-position bound above lifted to content
      — the rest droppable), with the **one-content-sibling witnessing rule** on top (a witness signs the first
      content sibling at a position and declines later ones; **sealed** siblings witnessed **one** per position now (first-seen — revised
      2026-07-11); a node still **accepts/retains up to two *witnessed*** sealed branches per position — two
      *accepted* prove `disputed` (the data-local walk), a witness-declined sibling is deferred-pending/droppable — federation §1e). Dead events are **propagated + retained** but never
      canonical. A **sealed** fork **at the last seal** is **never buried** (≥ 2 **witnessed** sealed → `disputed` — can't bury a
      rotation); a **below-seal** sealed straggler is **dropped** (inert — backdate-safe, revised 2026-07-11); a self-burial (a burying seal-advancer siblinging the retained chain, known from `previous`) is
      **rejected**. **The effective-SAID** is a **single confirmed tip → its real SAID**; a **no-single-tip** chain →
      a type-tagged **synthetic** recoupled to the verdict (`forked` / `disputed`), qualified by prefix + position —
      **not** a digest over the competing tips (that set is adversarially extensible → flood-unstable; §2a /
      area-vdtid-services §1e).
    - **The beacon propagates; the data decides (inv 14).** Witness receipts **enumerate** the competing branches so
      a one-branch holder fetches and walks them; the FORCE rule splits by **provenance (revised 2026-07-11)** — a node holding two or more
      **witnessed** sealed branches **at the last clean seal** forces `disputed` from the data; a **below-seal**
      sealed straggler is **dropped** (inert — it does not retreat the clean seal, backdate-safe), while a node
      holding only a **receipt**, or a **not-yet-witnessed** (below-threshold) sibling, waits for the **witness
      threshold** and never counts it (sealed; a losing *content* sibling never reaches threshold under the
      witnessing floor — its sub-threshold competing receipts are themselves the fetch signal, federation §1e). Receipts say *forked*; the
      data-local walk says *disputed*. The effective-SAID is a **single confirmed tip → its real SAID**; a
      **no-single-tip** chain → a type-tagged **synthetic** recoupled to the verdict (area-vdtid-services §1e);
      `forked` (reconcilable/pending fork) vs `disputed` (terminal, walk-found) is the **data-local** walk verdict the
      synthetic carries — **not** a digest over the competing tips (that set is flood-unstable; §2a).
    *Src:* `vdti-keep-all-data-rework.md` §9–§12 (four dual review rounds, all GO). `[locked]`

## What an event encodes
18. **Events carry only changes; the established state is *used*, not re-stated; and no event is empty
    (Jason 2026-06-30).** The chain's current state — roster, threshold vector, federation binding, witness-config,
    key state — is **established by the walk** (accumulated from prior events; the verifier already holds it). So an
    event **carries a field only when it *changes* that field**; anything unchanged is **inherited — used from the
    established state, never re-stated** (`present ⇒ change, absent ⇒ inherit`). *(Not "derive": the state isn't
    recomputed, it's the running state the walk already carries — re-encoding it would just be a second, forgeable
    copy to keep consistent.)* One rule, **many existing instances:** the roster/threshold delta ([inv 4] `roster` /
    [inv 12] — `add`/`cut`/threshold present-iff-changed), the `federationPin` re-pin ([inv 5] — present ⇒ forward
    re-pin, absent ⇒ inherit), the `witnesses` config ([inv 4] `witnesses` — present-iff-changed on `Wit`, mandatory
    only at inception where there is no prior to inherit).
    **Corollary — no empty events.** Every event must encode **≥ 1 change**, across **either layer** of the event: a
    **manifest role** (`anchors`/`roster`/`witnesses`/`clock`/`delegates`/`payload`/`grant`/`kills`/`bound`) **or** a **top-level
    structural field** (`pins`/`pin`, the rotation key-state + next-key commitment, `previousSeal`). An event that
    changes nothing is **malformed → rejected**. *(So a `Wit` is never a no-op even with an empty manifest — it **is**
    a rotation, so its structural side always moves: `pins` on an IEL `Wit`, the key-state on a KEL `Wit`. That is why
    `witnesses` can be `opt` wherever a prior config exists to inherit — the rotation, not the config, carries the
    non-emptiness. The user-`Wit` "must change `federation` or `witnesses`" rule, area-iel:32, is the *typed* instance
    of this corollary, not a separate mechanism.)*
    **Field-presence follows.** A field is **`req`** only when it is the kind's structural job and **cannot be
    inherited** (e.g. `anchors` on an `Ixn` / a `Wit`; `clock` on a federation governance event, which always
    advances) **or at inception** (no prior state — a federated `Icp` / federation `Fcp` declares roster + `witnesses`
    + binding); everything inheritable is **`opt` (present-iff-changed)**. *Src:* Jason 2026-06-30 (generalizing
    [inv 4]/[inv 5]/[inv 12]). `[locked-candidate]`

## Signatures & canonical form

19. **Every signature is over the fully-compacted SAID; verify by compacting-then-checking (Jason
    2026-07-17).** A SAD signature — and an anchor, which commits a SAID — is always taken over the SAD's
    **fully-compacted** SAID: the canonical, always-re-derivable form in which every nested SAD is replaced
    by its own SAID and the content is **JCS-canonicalized** (the digest said.md governs). A verifier **compacts the presented form to that canonical SAID first**, then checks
    the signature over it. Because compaction is a **recursive SAID commitment** (every faithful expansion
    of a SAD commits back to the same fully-compacted SAID — [inv 16]), one signature over the compacted
    SAID **validates any faithful disclosed form** — compact, partially expanded, or full. This is what lets
    **graduated disclosure** work without re-signing: sign once over the canonical SAID, and every variant a
    holder chooses to reveal verifies against it. **The fully-compacted SAID is the sole canonical identity**
    of a SAD; its other encodings are presentation forms, never the thing signed or addressed. Generalizes
    the credential / anchor rule (proof-of-issuance is over the fully-compact SAID; any variant verifies) to
    **every** signature in the system — ESSR envelopes, IPEX grants, exchange messages, receipts, group-chat
    messages. *Src:* Jason 2026-07-17 — closes the said.md / compaction "canonical = fully-compacted" fix.
    `[locked-candidate]`

    **Sign-time disclosure discipline (rider on [inv 19]; tooling, not a verifier check — Jason
    2026-07-18).** Because one signature validates any disclosed form, a signer handed a
    _partially-compacted_ SAD can commit to sub-content it never expanded — the signature is valid either
    way, and no verifier can later tell which form the signer saw (all disclosures share the one SAID). The
    verifier cannot police this; the **signer's tooling** must. A signing helper locates the compacted
    positions **by schema** — a typed SAD's `kind` names which fields are nested sub-SADs, so a bare SAID
    where the schema expects an expanded child is an unseen position — and **refuses to sign until the input
    is fully expanded there**, taking an explicit **override** only for a deliberate commit-by-reference
    (counter-signing a SAD authored elsewhere). An unknown-`kind` SAD is override-only (nothing to
    schema-check against). Fail-secure by default, opt-out is the signer's own (matches the status-read
    posture); a SAD's author holds its full form by construction, so this bites only when signing something
    handed over pre-compacted. **Kind-based detection + override is the limit** — compaction is not
    self-announcing, so a schema is the only sound detector: an expand-everything scan false-positives on
    scalar SAID references (`previous`, anchors) and false-negatives on positions it cannot fetch.

## Keys, devices & compromise

20. **A compromised device is a confidentiality loss, never a control loss (Jason 2026-07-18).** A device is a
    member KEL in an identity's IEL roster — **never its own IEL** (no per-device / "degenerate" IEL). It holds a
    **use-tier signing key** (a `t_use` share) and a **receive key** (an enclave-resident, non-extractable ML-KEM
    key). Compromising one device exposes **confidentiality** — what that device can decrypt — bounded by three
    independent limits: the receive key is **hardware-non-extractable** (a live attacker reads only during
    access, never walks off with the key), the group **ratchet** rots a grabbed epoch key, and **re-key on
    removal** locks the device out going forward. It never exposes **control**: taking over the identity —
    rotating keys, changing the device roster, terminating — is a **T2 governance** act needing `t_govern`, and
    one device is a single `t_use` (T1) share, which cannot meet it. So the identity **cannot be taken over by a
    single compromised device**; the holder rotates it out (a T2 act — a T1 device cannot re-admit itself). **This
    holds for the intended three-or-more-device identity:** a compromised device is one `t_use` share, and the
    identity's other devices meet the `t_govern` quorum that cuts it. A **single-device IEL is the degenerate
    exception** — its one device is the whole `t_govern` quorum, so a full compromise (its signing key and its
    on-device reserve together) is a control loss, with no other device to cut it. Recovering in place instead needs the
    **surviving** devices to meet `t_govern` and evict the compromised one — a strict-majority `t_govern` the
    survivors still reach after losing one, so a roster of **at least three** (at two, a majority `t_govern` = 2
    leaves a single survivor, too few to evict — the two-member freeze; a lower `t_govern` makes one stolen
    device a takeover). So a control-sensitive identity runs **three or more devices**; a one- or two-device IEL
    is an avoidable degenerate config (`residuals.md` §Degenerate configurations), not a property to patch by
    custodying the reserve off the device (which would only slow the immediate rotation recovery relies on). The hard floor — a live rooted device reads its own
    in-use plaintext — is a **universal endpoint limit, not a vdti property**. So confidentiality is **strong-at-rest, bounded-in-use**; control is **not takeable by a single compromised device** (the degenerate sub-three-device roster aside).
    Keep the two axes separate: conflating them (e.g. "compromise one device = compromise the person") is a
    category error that invites confidentiality creep into the control story. *Src:* Jason 2026-07-18.
    `[locked-candidate]`

## Document-layer evaluation (confirmed — see document-policy §C)
- **The evaluation model is a single as-issued function** — `evaluate_as_issued` (consumes the anchoring positions,
  resolves leaves as-of): one shared composer + one leaf resolver, reconciled to the reshape (leaf set, no
  `policyPin`, revocation-as-lookup-SEL). **`evaluate_current` is removed (2026-07-16 — live-policy removal):**
  live checks don't compose for a passive verifier, so there is no current-mode policy evaluation; who-may-present
  is the challenge-the-issuee auth step and read-gating is a `readers` membership, neither a policy
  (document-policy §C). `[locked-candidate]` *(F-L: was tagged `[needs-reconciliation]`; §C did the reconciliation
  — synced 2026-06-21. The two-function model collapsed to one — 2026-07-16.)* **Mode named `as-issued` (L1,
  2026-06-22):** `anchored` collided with the structural verb (`manifest.anchors`, "anchored by", "the anchoring
  position"); `as-issued` names the issuance-time mode unambiguously. Function: `evaluate_as_issued`.
