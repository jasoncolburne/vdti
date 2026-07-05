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
3. **Layers isolated, one direction.** SEL → IEL → KEL; an event pins/anchors only the layer directly below.
   Never anchor a SEL event in a KEL. *Why:* bounds blast radius; keeps the verification walk acyclic. *Src:* §1,
   §2. `[locked-candidate]`

## Binding & ordering
4. **Manifest-down + pin-up.** An event commits to the layer below via a `manifest` (a SAD); the lower event
   pins up to its owner's current tip. **A manifest *groups what the event commits to, by named role* (2026-06-21):**
   `{ said, <role>: <said-or-list-or-scalar>, … }`. Roles read as **"the things this event {anchors / roster / delegates / …}."**
   **Read kind-first, never label-first (F1, 2026-06-21):** each event kind has a **closed role vocabulary**
   (`allowed(kind)`); a manifest carrying any role outside it is **malformed → rejected**, and a role is consumed
   *only* after dispatching on a kind permitted to carry it — the label is checked against the kind, never trusted
   on its own. (The manifest SAID commits the labels — JCS over the keys — so a third party can't *relabel* a fixed
   event; the allowlist closes *author*-mislabel of the **directly-consumed** roles, which would otherwise let an
   `Ixn` carry `roster`/`delegates` and govern/grant at `t_use`, reopening **S1**. Killing at `t_use` is closed
   separately by the **back-check** (a SEL `Trm` demands an IEL `Rev` or `Dth`), not the allowlist.)
   **The principle (Jason, 2026-06-21):**
   - **Top-level structural = the event's *own* links:** `said`, `previous`, **`previousSeal`** (seal-advancing
     events only — the back-link to the prior seal that renders the spine; inv 17), **`pin`** (a SEL's down-pin to
     its owner IEL event — a scalar SAID), **`pins`** (an IEL's down-pins to its member KEL **tips** — the event each fresh participation *extends*
     (`participation.previous`), exactly the SEL `pin → anchor.previous` analog, so the IEL's own `said` never
     depends on the participation events that anchor it (no SAID cycle — cold-3 B1); a *list*, so
     carried as a scalar SAID → a small **pins-SAD**, never an inline field — a roster-add federation `Wit`'s pins
     are each participant's `participation.previous`: the **approvers' `Wit.previous`** (the pre-rotation witness KEL
     tip SAIDs — the clock's `T_end` for the retiring receipt key + the cold-F7 commitment distinguishing an honored
     synchronized rotation from an off-ceremony `Ror`) **plus, on a roster-add, the joiner's `Ixn.previous`** (a
     `T_join` for the joining key, never a `T_end` — else the new witness bricks at birth, cold-7 F2)),
     `federationPin`, `manifest`, the federation `prefix`.
     *(Why top-level: these are the chain's own structural links — a verifier walks the layered structure from them
     **without fetching the manifest**; the manifest carries content commitments, looked up on demand. `pins`/`pin`
     are encoded in `event-shape.md` (landed with the IEL/SEL/federation doctrine). `sealPins`, a
     seal-level analog, was considered and dropped — it only reached the terminal-divergence view, which the flat walk
     subsumes, inv 17.)*
   - **Manifest (role-labeled) = everything it *commits to below*:** anchored lower-layer **event SAIDs** *and*
     **documents** (SADs). Entities are named by **prefix** (inv 7); events/positions and documents by **SAID**.
   **Role vocabulary:**
   - `anchors` — lower-layer SAD / event SAIDs this event commits to below. **Carried by** KEL `Ixn` (required, ≥ 1) /
     `Rot` / `Ror` / `Wit` (the KEL `Wit` anchors the IEL `Wit` — uniformly, user binding **and** federation governance; **`Rec` hosts no anchor** — see the KEL→IEL kind-strict rule below) and IEL `Ixn` / `Evl` / `Ath` / `Rpr` / `Rev` / `Dth` (optional on the non-`Ixn` kinds — a rotation or a
     repair cascade commits the events it realizes; an IEL `Evl` commits the SEL `Fld`s it re-seals at one of the
     IEL's own fold boundaries; an IEL `Ath` commits the SEL `Gnt`(s) it seals, and an IEL `Rev`/`Dth` the SEL `Trm`(s) it seals). **Subsumes the former
     `issues`/`revokes`/`rescinds` (2026-06-27):** those were **credential / feature vocabulary on a log primitive**
     (inv 1 — features live on documents, never on primitives). The IEL is now **feature-blind** — it anchors a lower
     SEL event; **the feature layer names it** (a cred-SEL `Icp` on an IEL `Ixn` *is* an issuance; a cred-SEL `Trm` on
     a `Rev` *is* a revocation; a lookup-SEL `Trm` on a `Dth` *is* a rescission). The
     discrimination was never the label (this invariant's own "never trust the label alone") — it is the **back-check**
     (below).
   - `roster` — the roster/threshold (delta) SAD (IEL `Icp`/`Evl` (user) + `Fcp`/`Wit` (federation) — the federation's `Wit` carries its roster delta + `clock` — its **`add` is a *single* prefix** (one witness per `Wit`, except `Fcp` inception; `cut` stays a list — cold-seam P5, 2026-07-02: ≤ 1 unsynced witness per transition can't reach a majority `threshold`, closing the multi-add straddle); E1, 2026-06-28 — **plus a user IEL `Rpr`, restricted to a `cut` (+ optional `threshold` change), *never* an `add` and never `threshold`-only** (the repair-and-evict fold, 2026-06-30: the urgent eviction of the divergence-causing member rides the repair; an `add` rides a later, non-urgent `Evl` — inv 13). On the `Rpr` it is **directly consumed**: the kind→role allowlist admits the `roster` role's *presence*, and a **separate content check requires a non-empty `cut` and rejects a non-empty `add`** (a cut-less, `threshold`-only, or `add`-bearing `Rpr` `roster` is malformed → rejected — a threshold change on a `Rpr` **must** ride with a cut; a bare threshold change is a post-repair `Evl`). It is priced by the `Rpr`'s own **outgoing** `t_recover` — sound because `t_govern ≤ t_recover` is now a **hard** floor (inv 12), so the cut is never under-priced — and the post-cut roster is re-checked against the inv 12 bounds — the security floor, the recoverability ceiling, and the roster-floor `|roster| ≥ 1`). *(`pins`/`pin` are **not** manifest roles —
     they are **top-level structural**, see the principle above; relocated 2026-06-25 from Jason's model.)*
   - `clock` — an **inline timestamp value** (a UTC RFC3339 µs string — the lone non-SAID role; nothing dereferences it by SAID, so no nested SAD); **federation `Fcp`/`Wit`/`Trm`** (the federation clock — inv 14 / federation §1f; carried by the genesis `Fcp`, every governance `Wit`, **and the terminal `Trm`** — cold-4 B1 + cold-14 F1, so an all-windows-lapsed federation can still terminate; the federation has no `Evl`). **A single authoritative value on the federation IEL `Wit`** (not matched/synced across members — Q3), constrained only **monotonic** vs the prior federation clock + **`≤ now + band`** (§1f). *(No ordering against member KELs — KELs are timestamp-free, inv 6; the earlier "ahead of member KELs" framing was a category error — F2, dropped 2026-06-29.)* *(The witness currency gate is **exact-tip, no grace window** — a `graceSeconds` forgiveness window was considered and dropped 2026-06-24 as redundant + a backdate sliver; see federation §1e.)*
   - `witnesses` — the witness-config `{threshold, signers}` SAD (KEL `Icp`/`Wit` **+ user IEL `Icp`/`Wit` + federation IEL `Fcp`/`Wit`** — D1, 2026-06-28). **Mandatory iff federated *at inception*** (`Icp` / federation IEL `Fcp`): a federated `Icp`/`Fcp` omitting it is **malformed → rejected, fail-secure**; **forbidden** on `Fcp`-pre-federation KEL inception and a direct-mode `Icp` — cold-7 F3. **On a `Wit` it is present-iff-changed (`opt`)** — the same delta discipline as `roster`/`threshold`/`federationPin`: a `Wit` re-states the config **only when it changes it** (the rotation itself — `pins` / key-state always advancing — is the non-empty change; otherwise inherited), and when present on a federation-governance `Wit` it **field-matches** the anchoring KEL `Wit`s (Q3 — the KEL carries, the IEL matches; never derive IEL-from-KEL). An **IEL event is witnessed too** — it could otherwise fork without *any* member KEL forking (two disjoint sub-quorums each author a valid event at one position → the IEL diverges, no KEL does — the **content** case is now closed by the option-(b) position gate below; the privileged case `{Evl, Evl}` remains → `disputed`), and its effective-SAID is in the F-E transitive freshness set ([inv 8]); so the IEL carries its **own authoritative** witness-config for its events, **independent of every member KEL's** (a member's config witnesses that member's KEL events) — the same anti-straddle reasoning as the federation binding (cold-3 B2), **not** a match across members. The **federation IEL carries its own config too** (on `Fcp`/`Wit`, adjusted at each governance `Wit` — resolves cold-7 F1 / option b). *(No contradiction with the governance-facet field-match — C1, cold-9/10: "independent / not matched" scopes a member KEL's **own KEL-event config** (different chains); the federation-governance `Wit↔Wit` field-match is on the **federation config the approvers jointly endorse** — a consensus vote, area-iel:32 — i.e. the federation IEL's own config, not a member's.)* A **SEL inherits** its owner IEL's config (single-owner — nothing to declare, like the federation binding it already inherits). **How an IEL event is "witnessed" — self-attestation (Q1, Jason 2026-06-29):** an IEL has no signing key of its own (it is a *threshold over member KELs*), so an IEL event's witnessing **is** the witnessing of its **member KEL anchors** — the event is trusted when the member KEL anchors that authorize it are witnessed — concretely, the IEL event's own authorization count (inv 12: `t_use`/`t_govern`/… by kind) of its anchoring member KEL events are **each** witnessed at the witness-config `threshold`. **Two distinct counts (cold-9 Q1):** the IEL event's authorization count = *how many* anchoring KEL events must be witnessed; the witness-config `threshold` = *how many receipts* each one needs. IEL events still propagate + earn receipts **as per usual**. **Authorization** stays the witnessed KEL anchors (Q1); **fork-prevention** adds a second gate — **option (b), 2026-07-02: a *user* IEL's content events must also reach a majority quorum at their own `(IEL prefix, serial)`** (the same content-fork prevention as a KEL — federation §1e), closing the two-disjoint-sub-quorums content fork; **privileged** IEL forks (`{Evl, Evl}`, …) are unaffected — always-witnessed → `disputed`. The **federation IEL keeps pure anchor-based self-attestation** (no position gate — its every fork is privileged → `disputed`): its member witness-KELs witness **each other's** KEL events **exclude-self** (a witness never receipts its own KEL event), pool **`|roster| − 1`** — so for federation member events `signers/2 < threshold ≤ min(|roster| − 2, signers − 1)` and `threshold ≤ signers ≤ |roster| − 1`; a user chain stays `signers/2 < threshold ≤ signers ≤ |roster(F @ context)|` (external witnesses, no self-exclusion). **A structural majority floor `threshold > signers/2`** (a strict majority of the *selected* witnesses) makes two conflicting **content** siblings un-co-witnessable (privileged siblings are always co-witnessed → `disputed` — dispute evidence, federation §1e) — with the option-(b) position gate, closing the *partition / disjoint-sub-quorum* **content** fork that otherwise lets an IEL diverge with no member KEL forking (`{Evl, Evl}` remains → `disputed`); **fork-cost = `2·threshold − signers`** (own the whole quorum intersection), and a sub-majority config is **un-usable → rejected** (`threshold = 1` is usable **only at `signers = 1`** — the lone-witness carve-out, federation §1e). **The recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)` (cold-9 B1 + F6, verifier-rejects higher)** is the direct analog of `t_govern`'s gratuitous-hostage rejection (inv 12): an eviction/recovery `Wit` is authored by the remaining members but must also **self-attest**, and the evicted/dead member won't co-witness — so the self-attest pool is `|roster| − 2`, and at **sub-pool selection** (`signers < |roster|`) the *selected* pool loses one too, so `threshold ≤ signers − 1` binds as well (the `|roster| − 2` leg is exact only at full-pool selection; **the `signers − 1` leg is WAIVED at `signers = 1`** — the lone-witness carve-out, else the `|roster| = 3` config space empties into a de-facto floor bump; at `{1, 1}` evict-one self-attestation is **position-luck, warned** — reincept the fallback; guaranteed evict-one begins at `|roster| = 4` `{2, 3}` — federation §1e); capping `threshold` there guarantees the federation can always **evict one** compromised witness and get the cut trusted (the guarantee is *evict-one*; surviving `k` simultaneous unavailable members needs `threshold ≤ |roster| − 1 − k`, the operator's sizing choice — cold-10 F1 / federation §1c/§1e). The cap is **federation-only** (a user IEL's anchors are witnessed by the **external** federation pool, no self-exclusion, so evicting a user's member never shrinks it). At the `≥ 3` floor it forces **`{threshold 1, signers 1}`** at `|roster| = 3` — the majority floor rejects `{1, 2}` as sub-majority, so the `signers` collapse rides along (a lone-witness config; governance stays safe — it rides `t_govern`, not this bar — though witnessing byzantine-tolerance is then 0, the degenerate floor case the `≥ 5` operator doctrine answers, cold-10 F2; **the floor stays `≥ 3`**, no bump; a **config change** is **re-checked on the post-delta config** (inv 12 — any `Wit` changing roster/`threshold`/`signers`) — valid only if the **full cap `threshold ≤ min(|roster| − 2, signers − 1)`** (with the `signers = 1` waiver) **and the majority floor `threshold > signers/2`** hold after the change (the roster leg alone is the *slack* leg for `signers ≥ 2` — cold-seam F1), so a bare shrink that would strand the federation un-recoverable is rejected, forcing **evict-and-replace** or a simultaneous threshold-and-`signers` drop (a `threshold` drop to 1 forces `signers` to 1 — else sub-majority) — cold-13 F1). A **`Wit`'s own self-attestation is judged under the at-or-before witness-config + roster** (no self-weakening), **but under the NEW key-windows the rotation establishes** (the fresh keys its anchoring KEL `Wit`s reveal, F4-bounded — not the possibly-expired old windows; the clock axis is carved out of no-self-weakening — cold-11). So an all-windows-lapsed federation reads stale (fail-secure) then recovers via a catch-up rotation — never bricked; and a lone broken key still can't mint a current window (a rotation is honored only as a federation `Wit`, needing `t_govern` + self-attestation — federation §1e/§1a). The federation `Wit` thus **never bricks** even when every witness participates — its trust rides its (cross-witnessed, exclude-self) KEL anchors, not an exclude-all-participants aggregate count. Divergence stays data-local-detectable: a federation `Wit` fork's competing branches are each anchored by witnessed KEL `Wit`s that propagate, surfaced by the keep-all-data walk (inv 17). *(Supersedes the `|roster| − |participants|` aggregate-gate framing — that bricked an all-witness rotation; cold-8 F1.)*
   - `delegates` — delegate **prefixes** (the delegate-list SAD) (IEL `Ath`, `delegates` role).
     *(The former `issues` / `revokes` / `rescinds` lists are now plain `anchors` entries — cred-SEL **v1**s (the
     serial-1 `Pin`; the `Icp` rides `v1.previous`) on an
     IEL `Ixn`, cred-SEL `Trm`s on a `Rev`, lookup-SEL `Trm`s on a `Dth` — discriminated by the
     anchored event's kind, not a role label; a rescission's lookup-SEL `{Icp, Trm}` is still born under its `Dth`,
     the `Dth`'s `anchors` naming the sealing `Trm`, reachable to its `Icp` via `Trm.previous`.)*
   - `bound` — carried by the rescission `Trm`: the SAID of the **last valid (honoured) event** on the delegated
     chain — the inclusive grandfather boundary (a cred is honoured iff its anchoring position is an ancestor of the
     `bound`; the dial runs tip → inception). *(Renamed from "cut-off"/"terminator" — 2026-06-26.)*
   - `grant` — the gated grant-doc SAD `G` a **SEL `Gnt`** commits (the editors/commenters + their `from`
     validity-period starts). The additive twin of the rescission `Trm`'s `bound`; back-checked (a `Gnt` is valid
     only anchored by an `Ath` — kind-strict), so unlike `content` it is *not* a directly-consumed role.
   - `content` — the content SAD(s) a **SEL `Ixn`** records (single-owner data — e.g. a cred-SEL amendment). The
     cred-SEL `Icp` itself uses `data` (= the cred's SAID), **not** a manifest; only the content `Ixn` carries this
     role. *(The first SEL-borne manifest role — later joined by `bound`, `fork`, and `grant`; added 2026-06-22 — inv 4 had no SEL role, but a SEL `Ixn` must commit
     its content SADs, and the principle puts documents in the manifest.)*
   - `fork` — the **fork a repair resolves**: a **single inline root SAID** (an inline scalar, like `previous`),
     carried **ONLY by a repair** (KEL `Rec`; IEL·SEL `Rpr`) — **required** (a repair with no
     `fork` is invalid — no repairing a non-divergent tip), and **no non-repair event ever carries it** (a `Trm`
     never carries one — caught in a divergence it resolves **directly**, burying a content loser via the seal-cap or
     winning a same-serial `{Trm, content}` race by tier-rank; a privileged loser is `disputed`, un-buriable). **The committed SAID is a losing branch's ROOT — its first
     divergent event (a distinct child of the fork point, *off* the retained chain), NOT its tip (root-pointing, Jason
     2026-07-01; the list collapsed to ONE root 2026-07-02 — below).** The root **condemns that branch's entire subtree**: every descendant is non-canonical **forever**, so
     a losing branch that **grows after the repair** (a lagging node extends it) is dead **by descent** and needs **no
     follow-up repair** — growth-proof (example 9: `Rec.fork → Ixn#2` kills `Ixn#2` *and* its later `Ixn#3`).
     **Every OTHER competing branch — held, missed, or later-grown — closes structurally without being named** (the
     collapse's verification, 2026-07-02): its first event sits below the repair-advanced seal *off* the retained
     chain → **inert**; its growth is **dead by descent**; a privileged event in it → `disputed` (every privileged
     event is a seal-advancer → a spine fork — walk-independent) — the same closure a *missed* branch always had, so
     named-vs-missed was a distinction without an outcome difference. With content-fork prevention (federation §1e) a
     witnessed chain never yields two live content siblings to enumerate, and in the residual (direct-mode /
     witness-compromise) that unnamed-branch machinery closes every branch — a **list** of roots was a redundant
     commitment. An author holding several losing branches names any one (typically the only one); the verifier still
     **independently computes the competing set** (validated, not trusted — inv 13), so no branch escapes by being
     unnamed. **Two
     guards:** (i) **no self-condemnation** — a root on the retained chain (the verifier knows it from `previous`) is
     rejected, so you can never archive your own branch, and the shared ancestor `v_{d-1}` is never a root (it is on
     the retained chain); (ii) a condemned subtree must be **content-only** — a **privileged** event in it is ≥ 2
     privileged → `disputed` (can't bury a rotation; inv 13, validated-not-trusted). **Deadness descends (inv 13):**
     an event whose parent is dead is itself dead — the per-event seal-cap locks only a losing branch's *first* event,
     the descent rule kills everything built on it (the named root's whole subtree; every other branch's growth). Each dead
     **lineage** extends at most **64 events past the last seal** (the seal-advance cap — a deeper event must author a
     seal-advancer, privileged → `disputed`); breadth is bounded per position by **retention** (≥ 2 kept per
     position, the rest droppable — the content analog of inv 17's ≥ 2-per-spine-position) with the
     **one-content-sibling witnessing rule** on top (a witness signs the first content event at a position and
     declines later content siblings; privileged siblings are witnessed up to **two** per position — two prove
     `disputed`, then declined; the repair is privileged, no separate clause — federation §1e). So
     the fork is **bounded on both axes** — an adversary can author
     extra siblings but they are declined + droppable. Dead events are
     propagated + retained but never canonical (example 9's description; receipt-bearing only where the fork is witnessed — a losing content sibling is declined on a witnessed chain). *(Supersedes the tip-pointing + stacking idea: a tip covers only what existed at author time, so
     growth escaped it and needed a second repair; a root covers the whole subtree, growth included — stacking, the
     valid-pointer set, and the below-seal carve-out all drop out. 2026-07-01.)* The **retained (canonical) run is NOT committed** — it is the linear
     chain `[previousSeal..previous]`, recovered by the flat walk (nodes keep full bodies; the flat query returns
     them), and its `Ixn`-only integrity is **checked on the flat walk**, not trusted from a field (a privileged
     event in the span would itself be a seal, so `previousSeal` would name it — inv 17). **"Content was folded since
     the prior seal" is the derived predicate `previous != previousSeal`** — no field. Renders the spine's fork view
     (inv 17). *(Simplified 2026-07-01: the `folds` SAD `{ canonical, forks[] }` + boundary-SAIDs collapsed to one
     `forks` role — `canonical` is the derivable linear run, the boundary-SAIDs were a non-sufficient pre-check;
     both redundant. Collapsed again 2026-07-02: the `forks` list → the single **`fork`** root, above. Supersedes
     folds-2026-06-23 / the `folded`→`folds` rename-2026-06-29. Landed `docs/design/`
     still carries the old `folds` shape → reconcile on the encode after review.)*
   **Two enforcement classes (F1):** `anchors`/`fork`/`grant` are **back-checked** — a mislabel is caught when the
   referenced event is validated against its required kind. **The anchor matrix is enforced *kind-strict* on both
   cross-layer legs — the IEL→SEL leg (C1, 2026-06-27) and the KEL→IEL member-participation leg (2026-06-28) — each
   direction:** on the IEL→SEL leg, each SEL kind is valid **only** when anchored by exactly its matching IEL kind,
   **and** each IEL kind anchors **only** its matching SEL kinds — content `Ixn` (and a content-SEL **v1**: a serial-1
   `Pin`, or the first content `Ixn`) ↔ IEL **`Ixn`**; SEL `Gnt` ↔ IEL **`Ath`**; SEL `Trm` ↔ IEL **`Rev`** (revoke) / **`Dth`** (rescind); SEL `Fld` ↔ IEL **`Evl`**;
   SEL `Rpr` ↔ IEL **`Rpr`**. **Tier-elevation (anchor tier ≥ event tier) is an *additional* floor, not the check** —
   a tier-only reading would let a T2 kill-anchor (`Rev`/`Dth`) host T1 content (2 ≥ 1), laundering content onto the
   seal-durable/repair-surviving rail and breaking *only-tier-1-is-archivable* (inv 13); the kind-strict binding
   closes it. (On the IEL→SEL leg the laundering is a real single-owner hole; on the KEL→IEL leg the identity's
   threshold already subsumes it, so kind-strict there is correctness-by-construction — content always rides an
   archivable host structurally, not because the threshold backstops it.) **Anchor-monotonicity (the IEL totally-orders each SEL, cross-layer, 2026-07-01):** an IEL event's SEL anchor is valid **only if the anchored SEL event extends that SEL's latest IEL-anchored tip** — the anchor chain names each SEL's tip *by SAID* over the **canonical (retained) IEL walk**; the SAID is opaque (inv 16), so an anchor a node can't **attribute** (it lacks the body) is **skipped, not blocking** (*skip-unattributable* — else a withheld/lost body would wedge the SEL); an anchor at an **already-attributed** SEL serial is **malformed → the SEL event is inert** (back-checked at SEL-validation; the carrying IEL event stays valid — no IEL contamination). So a node appending to a *linear* IEL always extends each SEL correctly, and a **valid SEL fork implies an IEL fork beneath it** (two valid same-serial SEL events force their anchors to be IEL siblings) — a SEL never forks under a linear IEL; every genuine SEL fork rides an IEL fork (one IEL `Rpr` condemns the losing IEL branch → its SEL events die **by descent across the anchor edge**, inv 13 — and cascade-anchors the SEL `Rpr`). No SEL-under-linear-IEL deadlock (cold F1). Concretely:
   - a SEL `Trm` is valid **only** anchored by an IEL **`Rev`** (a cred-SEL `Trm` — revocation / closure, `t_govern`)
     or an IEL **`Dth`** (a rescission lookup-SEL `Trm`, `t_authorize`), determined by its SEL-type; an IEL `Ixn`'s
     `anchors` resolving to a `Trm` is **rejected**, **and** a `Rev`'s or `Dth`'s `anchors` resolving to a
     **non-`Trm`** (content, a v1-`Pin`, a `Fld`) is **rejected**. Symmetrically, a SEL **`Gnt`** (grant) is valid
     **only** anchored by an IEL **`Ath`** (kind-strict — an `Ath` anchors **only** `Gnt`s; the additive twin of the
     `Rev`/`Dth`→`Trm` kill). **This back-check is now what keeps kills sealed** — it replaces the former
     `revokes`/`rescinds`-are-`Kil`-only binding (the `Rev`/`Dth` kinds seal on arrival; the
     `Trm`-demands-a-`Rev`-or-`Dth` rule is what forces every kill onto a sealed kill-anchor).
     **Topic → kill-anchor kind (the total rule, S5/D):** a `Trm` is anchored by **`Dth`** (`t_authorize`) **iff** it
     is an **authorization-rescission** — a lookup-SEL that closes a granted authorization: a **delegation**-rescission
     (keyed on a delegate prefix) or a **doc-membership** rescission (keyed on `hash(G | said_b)`) — and by **`Rev`**
     (`t_govern`) **otherwise**. So cred-SEL (`CRED_TOPIC`) and multi-party-doc-leg (`DOC_TOPIC`, a version-SEL closure)
     `Trm`s are `Rev`-sealed, the rescission lookup-SELs (`RSC_TOPIC` + the doc-rescission topic) are `Dth`-sealed, and
     an **arbitrary app-topic** SEL's `Trm` defaults to `Rev` (never the cheaper `Dth` when `t_authorize < t_govern`).
     The **grant** side is the additive twin: a `Gnt` is `Ath`-sealed.
   - a cred-SEL is anchored by an IEL `Ixn` naming its **serial-1 event** (its *v1* — a `Pin` for issue-and-sit;
     `v1.pin == this Ixn.previous` is the floor). A **rescission** lookup-SEL's v1 **is** its `Trm`, anchored by the
     `Dth`, floored `Trm.pin == this Dth.previous` (S4 — the floor rides whichever IEL kind anchors the v1, never the
     `Ixn` only). **The `Icp` is never anchored in a SEL** — it rides via `v1.previous`; it carries **no** manifest
     (its `data` IS the credential's SAID).
   - **KEL→IEL (member participation):** each IEL event is anchored **only** by the member-KEL kind that reveals
     exactly the capability the member exercises — content ↔ KEL **`Ixn`**; T2 establishment & governance
     (user `Icp` / `Evl` / `Ath` / `Rev` / `Dth`, **federation `Fcp`** inception) ↔ KEL **`Rot`**; T3 recovery & terminal
     (`Rpr` / `Trm`) ↔ KEL **`Ror`**; **T3 witness/federation (IEL `Wit` — the user federation-binding AND federation
     governance) ↔ KEL `Wit`** (the **one `Wit` kind**: a single `Wit` is the T3 rotation — refreshes
     signing + recovery — and anchors the IEL `Wit`; `pins = Wit.previous`). The **anchor-kind is uniform** (`Wit ↔
     Wit` both facets), but the **field-match is facet-specific (Q3, Jason 2026-06-28):** the **user** facet matches
     the binding `{federation, federationPin}` (C4/C5, anti-straddle — each member carries its *own* binding); the
     **federation-governance** facet matches **only the witness-config** (the "witnessing stuff") — the **roster
     delta does not match** (it rides the IEL `Wit`'s manifest, `Evl`-style, committed by SAID + anchored by the
     `t_govern` member `Wit`s), and the **`clock` is not matched** (a single value on the federation IEL `Wit`,
     constrained monotonic + `≤ now+band` — inv 4 `clock` / federation §1f). **No higher-tier KEL event stands in** — the former "a T3
     (`Ror`/`Rec`) reveals a superset, so it satisfies a T2 anchor" elevation is **removed (2026-06-28)**. **`Rec`
     hosts no anchor at all** — a recovered member participates via the **subsequent `Ror`** (the repair diagram's
     `Rec`→`Ror`); so the anchor-hosting KEL kinds are `Ixn`/`Rot`/`Ror`/`Wit` (the `Wit` anchors **only** the IEL
     `Wit`; a `Ror` anchors `Rpr`/`Trm`). The **rotations are the core structural check**; an
     added member's **consent** (a joiner's KEL `Ixn` on an `Evl`, **or on a federation `Wit`** — a new witness
     joining-not-rotating, A1 2026-06-28) rides **alongside** — **valid only for a member in
     the `add` set, counted only toward Rule-A consent-of-added, never toward `t_govern` (which only the
     approvers' `Rot`s — the approvers' `Wit`s for a federation `Wit` — satisfy); over-count → laundering, blanket-reject → joiner lockout (cold-5 C6 / A1)** — not part of
     the anchor-kind check (the joiner `Ixn` rides alongside the approvers' kind-strict KEL `Wit` anchors, exactly as on an `Evl`). **Federation bootstrap — RESOLVED
     (2026-06-28):** the federation's own witness KELs are **`Fcp`-rooted** (federation infrastructure, governed
     *into* the roster, **single-federation**, never self-bound — §inv 14), so genesis is `Fcp` → `Rot` and the `Rot`
     anchors the federation IEL **`Fcp`** kind-strict (T2 ↔ T2); a `Wit` on an `Icp`-rooted user KEL is the
     identity's **federation rebind** (KEL `Wit` → IEL `Wit`, both T3 — auditable at the IEL, the IEL `Wit`'s **two
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
     exercises (**kind-strict, inv 4:** `Ixn → IEL Ixn` content; `Rot → IEL Icp`/`Evl`/`Ath`/`Rev`/`Dth`/federation `Fcp` establishment &
     governance; `Ror → IEL Rpr`/`Trm` recovery & terminal; **`Wit → IEL Wit`** witness/federation — the user federation-binding **and** federation governance (the one `Wit` kind is the T3 rotation; anchor-kind uniform, field-match facet-specific — Q3, cold-4 B1); **no higher-tier stand-in**; `Rec` anchors nothing, a
     recovered member participates via the subsequent `Ror`), signed by its **current** key and committing to that
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
   `cred ← cred-SEL ← IEL Ixn ← KEL Ixn` (each `previous`-linked) — the as-of is read directly from the anchoring position, which is append-only and can't be inserted in the past.
   **The document carries NO self-asserted pin (removed 2026-06-26)** — there's no issuer-chosen value to constrain;
   the *structural* SEL down-pin (on the cred-SEL's serial-1 `Pin`) still satisfies `pin == anchor.previous` as a
   chain link, but it's a chain field, not a document claim. Closes the pin-backdate forgery and the
   DI2I/delegated-issuer forge-as-of-old route. **A standalone SAD's custody follows the same rule (2026-07-03):** no
   self-asserted position pin — an `owner`-bearing SAD is attributed via a SEL anchor (`derive(owner, topic, said)`),
   its as-of the append-only anchoring position; the self-asserted `pin` is dropped (`custody { owner, topic,
   readPolicy }`) — see inv 16. `[locked]`
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
   anchors are the sealed portion plus the repaired surviving branch; a *terminal* divergence's post-seal window
   grounds **no new trust** (whole-*above-seal*-suspect — below-seal stays final).
   *Planned:* a `search_only` parameter that ends the walk when all digests are found; the verification token
   then points at the reached (possibly mid-chain) position, and a `resume` function takes that token forward to
   tip. **Token reuse is transitive (F5, 2026-06-20):** a cached token's reuse gates on the effective-SAID of
   **every chain it transitively pins** (the KEL(s) beneath an IEL, the IEL beneath a SEL), not the chain's own
   alone — else a lower-layer `Rec` breaks an upper event invisibly to the warm cache.
   **Freshness composes — the transitive set + divergence + resume (F-E, locked 2026-06-21):** the three reuse
   rules only hold *together*. (a) **The multi-source / witnessed freshness bar (F8) applies to the *whole*
   transitive set** — every chain the token leans on (cred, issuer, *every* delegator above it, the devices
   beneath each identity, **and the federation IEL(s) the witnessing itself leans on — G3**), not "the chain"
   singular. (You can't multi-source your way out of a stale *federation roster*: an eclipsed view of `F` still
   counts a since-removed witness as "a source." The **federation clock** [federation §1f] supplies the absolute
   staleness metric that bounds this.) A single stale/malicious source on **any** one of them can
   hide a revocation; so a *loss-of-trust* decision needs each dependency's effective-SAID confirmed multi-source
   (a witness-signed effective-SAID *is* multi-source by construction → cheap for witnessed chains; an unwitnessed
   or eclipse-isolated chain **can't meet the bar → the loss-of-trust decision fails-secure: REFUSE**, never
   proceed-with-a-flag, cold-5 C2). (b) **"Is this chain forked / disputed?" is itself a
   loss-of-trust question** — a one-branch holder computes a normal-looking tip and never sees a fork; only the
   federation dispute signal reveals it, so it must be in the multi-source bucket. (c) **`resume` must
   re-run the to-tip negative checks** (revocation / rescission / divergence) against the new tip whenever any
   transitively-pinned chain moves — an incremental resume that only extends chain state would advance the token
   *past* a revocation without surfacing it. So F9's "a cross-layer break is detectable" is **a consequence of
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
10. **Negative checks are positive lookup-SEL reads — never scans.** "Is X rescinded / revoked / closed?" is
    answered by recomputing one derived lookup-SEL locus `derive(owner, topic, data)` (present → yes, O(1)),
    never by scanning a chain or list for absence. *Why:* a scan-for-absence forces deep-inspecting everything
    it touches; the positive locus is O(1) and tamper-evident. *Src:* design-pass §5 + session 2026-06-20.
    `[locked-candidate]`

## Keys, tiers, thresholds
11. **Tier = whether the *reserve* is required — orthogonal to count.** T1 = signing key only; T2 = the rotation
    preimage alone; T3 = rotation + recovery preimages — the **old signing key is not a prerequisite at T2/T3**
    (a rotation reveals the new key; you don't sign with the key you're abandoning). The reserve (held *apart* from the signing key) is required
    when **either (a) a forgery would be high-harm or irreversible** (establishment-mutation, authority-grant,
    repair, identity-kill) **or (b) the act must be permanent on arrival** — i.e. **sealed**, carried by a dedicated
    sealed kill-anchor (`Rev` or `Dth`). **A kill (revoke / close / rescind / terminate) is case (b):** low-danger
    (safe-direction — it only removes trust) but **monotone** (a third party relies on it), so it must be sealed
    → it rides a **`Rev`** or **`Dth`** (the dedicated sealed kill-anchors — no roster delta; but, being T2/permanent, they
    **force a `Rot`** like `Evl` — each authorizing member authors a ≥T2 KEL event; the `Evl`-vs-kill-anchor distinction is
    the **roster delta**, not the rotation — A, 2026-06-27) → **T2** (identity-kill → `Trm`, **T3**). Only **content** (`Ixn`) is **T1**. Tier is still ⊥ count
    (count is a dial; tier is set by danger-or-permanence): a content `Ixn` is **T1 even at a high `t_use`**.
    **This reverses the F3 line "safe-direction removals are T1 / `Trm` may be delayed"** — a kill can't be
    unsealed (inv 13, 15); it re-aligns with `document-policy §F`. *Src:* §1 + the kill-cluster resolution,
    2026-06-21. `[locked]`
12. **IEL authorization is a threshold vector** `{t_use, t_govern, t_authorize, t_recover}` (the **count** axis,
    ⊥ tier per inv 11), indexed by kind; additions require unanimous consent of the added; a `Evl` needs
    consent-of-added ∧ `t_govern`-of-outgoing. **Bounds (F-K, hardened 2026-06-21 — supersedes the F4 floors):**
    - **`t_use ≥ 1`** — `t_use = 1` is **single-device by choice** (no content resilience); `t_use ≥ 2` makes a
      single compromised device unable to author content (F10a).
    - **Authority kinds (`t_govern`, `t_authorize`, `t_recover`), `|roster| ≥ 2` — TWO bounds of different kinds
      (split 2026-06-21):**
      - **`≥ 2` = the *security* floor — HARD, verifier-enforced, every identity.** No single member exercises
        authority (closes the `t_govern=1` seizure, the `t_authorize=1` rogue-delegate, the `t_recover=1`
        rogue-repair — LF2). A single compromised device must never govern / grant / recover alone.
      - **`≤ |roster| − 1` = the *recoverability* ceiling — ADVISORY only at `|roster| = 2`, HARD at `|roster| ≥ 3`
        for every identity incl. the federation (G1, corrected twice 2026-06-21).** It lets you **evict a
        compromised member / recover a lost device without the missing one**. Violating it (a threshold `= |roster|`)
        is **NOT self-lockout — it's a hostage**: a *single compromised member* withholds consent → every eviction
        (`Evl`) and recovery (`Rpr`/`Rec`) needs **all** `|roster|` (incl. the compromised one) → the identity is
        **frozen until reincept, at the attacker's discretion** (an indefinite veto — the adversary *gains*, the
        owner doesn't merely lose access). So at `|roster| ≥ 3`, where a threshold `< |roster|` is available, a
        threshold `= |roster|` is a **gratuitous hostage config → the verifier REJECTS it** (Finding 3). The
        relaxation survives **only at `|roster| = 2`**, where `≥ 2` *forces* `t = 2 = |roster|` (no satisfying value
        otherwise) — there the verifier **accepts** + the wallet **warns** ("a 2-device identity can't evict/recover
        without both, and a compromised device can freeze you — add a 3rd key"). *(Reverses 'advisory at all sizes'
        / 'nobody seizes, only lock yourself out' — both wrong: it's a hostage, and it's only forced at 2.)*
    - **Singleton exception:** `|roster| = 1` → all thresholds = 1.
    - Ordering: `t_use ≤ t_govern`, `t_use ≤ t_authorize` (sanity, not load-bearing); **`t_govern ≤ t_recover` is a
      HARD floor — verifier-enforced wherever a threshold is declared or changed (`Icp` + every roster-delta event),
      alongside the security floor + recoverability ceiling (2026-06-30, hardening R3-8).** *Why now hard:* R3-8
      (2026-06-21) kept it sanity-only because a **plain** repair "can only **select among already-authorized
      branches** and **realize an already-`t_govern`-valid privileged branch** (the tier rule, inv 13) — it can't
      manufacture authority," so a sub-`t_govern` repair coalition granted **no new power**. **The repair-and-evict
      fold (inv 4 / inv 13) breaks that premise:** a `Rpr` may now carry a roster **cut**, which *does* manufacture
      authority (it evicts a member). The cut rides the `Rpr`'s own `t_recover` (no separate count), so it is soundly
      authorized **only if `t_recover ≥ t_govern`** — hence the hard floor. **Vacuous for the federation** (declares no
      `t_recover` — federation §1a) and for a singleton (all = 1). It forecloses `t_recover < t_govern`
      (easy-recover-hard-govern), which loses little — the recoverability ceiling already guarantees
      recover-without-one-member without dropping below `t_govern`, and recovery reveals the **reserve**, so it should
      never be *cheaper* than a roster change. *(The R3-1/`{kill, kill}` decoupling — §13 below — stands on its own,
      unaffected.)*
    **Consequence (G1, corrected 2026-06-21):** a 2-member identity (phone + computer — the common case) is
    **VALID**: `≥ 2` forces every authority threshold to 2 (secure — no single-device seizure), and it simply can't
    also satisfy `≤ |roster| − 1` (= 1), so it's **unrecoverable → warned, not rejected** (a lost or *compromised*
    device freezes governance/recovery — a hostage, not just self-lockout — but nobody *seizes* you; add a 3rd key
    to become recoverable). **At `|roster| ≥ 3` a threshold `= |roster|` is REJECTED** (a gratuitous hostage —
    Finding 3); recoverable governance needs `|roster| ≥ 3` (a threshold both `≥ 2` and `≤ |roster| − 1`). The **federation — i.e. the witness IEL whose roster
    is the witness KELs — must be `≥ 3`** (its recoverability ceiling is hard, so the witness IEL can never be brought
    to an unrecoverable / bricked size). *(Earlier "`|roster| = 2` is invalid / verifier rejects" was wrong — it conflated the security
    floor with the recoverability ceiling; there's no security reason to forbid the both-agree config.)* The
    reserve/tier each kind needs is inv 11. **The bounds are re-checked on the *post-delta* config at every config-changing event — a user `Evl`, a user `Rpr`-cut, *or* a federation `Wit` (including a config-only `Wit` that changes `threshold`/`signers` with no roster delta — cold-seam F2)**
    (Finding 14a, 2026-06-21; generalized to the federation `Wit` — cold-13 F1: the federation has **no `Evl`**, it governs via `Wit`; and to the **user `Rpr`-cut** — the repair-and-evict fold, 2026-06-30, makes a `Rpr` roster-shrinking, so a `Rpr`-cut that strands the identity or lands at a hostage `threshold = |roster|` is **rejected**, forcing a simultaneous `threshold` drop (which the `Rpr` may carry) or reincept) — not only at `Icp`; an event whose resulting roster/thresholds would violate any
    bound is rejected. **A third, absolute floor — the roster is never emptied: post-delta `|roster| = |roster| + |add| − |cut| ≥ 1`** (beneath the security floor / singleton exception; the roster is a **set**, so `add ∉` the current roster, `cut ⊆` it, `cut ∩ add = ∅` — the size arithmetic holds; the same set discipline the federation states at §1a (cold-9 Q2 / cold-14 F1), general to *every* roster delta). A `cut` that would zero the roster is rejected — **one general rule** that makes *every* singleton IEL's roster **downward-immutable**: a singleton `Rpr`-cut (no `add`) computes `1 + 0 − 1 = 0` (`< 1`) → rejected, so a singleton can't be zeroed by a repair — **not only** the federation-member key-SEL owner (federation §1e). It still **allows** singleton evict-and-replace via an `Evl` — `cut 1 + add 1` stays `1`, **authorized at `t_govern`-of-outgoing** (the *old* member signs, so this works only for a planned migration where the sole key is **uncompromised/available**; a lost or compromised singleton can't produce that signature → reincept); only the zeroing is forbidden. **For the federation this re-check also covers the witness-config recoverability cap** — the **full** post-delta `threshold ≤ min(|roster| − 2, signers − 1)` (with the `signers = 1` waiver) **plus the majority floor `threshold > signers/2`**, re-applied on **any `Wit` that changes roster, `threshold`, or `signers`** (not a roster `cut` alone) — so a **bare `cut`** that would strand the federation un-recoverable (`|roster| 5→4` at `threshold 3`), a `t_govern`-hostage (`|roster| 4→3` at `t_govern 3`), **or a `signers`/`threshold` change landing on the *binding* `signers − 1` leg** (`{s 4, t 3}@5 → {s 3, t 3}@5` passes `|roster| ≥ threshold + 2` yet violates `t ≤ min(3,2)`, cold-seam F1) is **rejected**, forcing evict-and-replace or a simultaneous threshold-and-`signers` drop. **This is what actually enforces the `[locked]` "the witness IEL can never be brought to an unrecoverable size" above** (cold-13 F1; the roster-leg-only phrasing corrected to the full `min` — cold-seam F1, 2026-07-02 — since for `signers ≥ 2` the `signers − 1` leg binds and the roster leg is slack).
    **Every IEL kind prices itself (S1 closure, 2026-06-21; count-parametrization retired 2026-07-04).** The
    required count of an IEL event is fixed by its **own kind**, never derived from the lower-layer payload it
    anchors, and **every kind draws from exactly one slot**: `Ixn` → `t_use`, `Evl` → `t_govern`, `Ath` →
    `t_authorize`, `Dth` → `t_authorize`, `Rev` → `t_govern`, `Rpr` → `t_recover`, `Trm` → `t_govern`, `Wit` → `t_govern`. **There is
    no count-parametrized kind and no `threshold` slot-name field** — the former `Kil` (a single kill-anchor
    parametrized by a `govern`/`authorize` slot) is **split into `Rev`** (revoke your own artifact, `t_govern`)
    **and `Dth`** (deauthorize a grant, `t_authorize`), so each kill-anchor's count is implied by its kind exactly
    like every other kind. So "count travels with the anchored kind" is safe *because* every kind does exactly one job: no kind
    both anchors a payload **and** mutates establishment state (the old IEL `Evl`-anchors-a-kill-while-changing-the-
    roster). Verifying an IEL chain's validity therefore needs **no SEL input** — each event prices from itself.
    *(The **repair-and-evict fold** (2026-06-30) is the one kind that does its own job **and** mutates establishment
    state — a `Rpr` carrying a `cut` — yet it does **not** reopen **S1**: the cut rides the `Rpr`'s own `t_recover`
    (no separate, cheaper count to launder under), and `t_govern ≤ t_recover` being a **hard** floor (above) guarantees
    `t_recover ≥ t_govern`, so the cut is priced **≥** its governance count, never below. Pricing stays self-contained —
    `Rpr` → `t_recover` from its own kind — and IEL validity still needs no SEL input.)*
    **Threshold declaration — the active set is fixed at `Icp` (locked 2026-06-25).** The `Icp` declares
    **exactly** the authority kinds the IEL will ever exercise — equivalently, **a threshold is declared iff its
    consuming kind is in the IEL's kind set** (`Ixn`→`t_use`, `Ath`/`Dth`→`t_authorize`, `Rpr`→`t_recover`,
    `Evl`/`Rev`/`Wit`/`Trm`→`t_govern`). A **user** IEL (kind set has `Ixn`/`Ath`/`Rpr` + governance) → `t_govern` +
    `t_recover` **mandatory**, `t_use` + `t_authorize` **optional and lockable**. A **federation** IEL (`Fcp`/`Wit`/`Trm`
    — no `Ixn`, no `Ath`, **no `Rpr`**) declares **exactly `{t_govern}`** — `t_use`, `t_authorize`, **and `t_recover`**
    all forbidden (a federation `Fcp` declaring any is **malformed → rejected** — the threshold-declaration analog of
    the facet-dependent role allowlist, cold-9 Q3 / 2026-06-29; the federation never repairs, so nothing consumes
    `t_recover`). A kind **omitted at `Icp` can never be exercised** — there is no
    first-introducing it on a later event (closes a mid-life authority-introduction). Thereafter a roster delta
    carries a threshold field **only when it changes** (present ⇒ **must** change; absent ⇒ unchanged) — the same
    present=delta / absent=inherit shape as the membership `add`/`cut` (inv 4) and the federationPin re-pin (inv 5).
    *Src:* design-pass §12 + F4 + F-K hardening
    2026-06-21 + threshold-declaration 2026-06-25. `[locked]`

## Divergence & federation
13. **Divergence is permanent and visible; repair is atomic; and repair is scoped to T1 content.** `Rpr`/`Rec`
    are permanent on-chain divergence markers; a repair is a manifest-bound cascade, authored bottom-up /
    committed top-down, submitted as one batch + one DB transaction (**mandatorily atomic — a *partial* repair is rejected**, closing the re-divergence race by construction; cold-5 C3). **Repair-and-evict is a *single* event (the fold, 2026-06-30):** evicting the divergence-causing member **must** be inseparable from the repair — were it a later event, the still-rostered member races a fresh `Ixn` at the repaired tip → re-fork → repair again, indefinitely (a timing attack) — so the eviction **folds into the `Rpr`** as a `cut` (a `Rpr` `roster` is a required `cut` + optional `threshold`, never an `add` and never `threshold`-only — inv 4 / inv 12), `Ror`-anchored exactly as a plain `Rpr`, priced the **outgoing** `t_recover` (pre-change — as the `Evl` is `t_govern`-of-outgoing, so a `Rpr` can't lower its own gate before cutting — else a **single actor could drop `t_recover` to 1 and `Rpr` everyone else out in one event** (a takeover); the outgoing threshold forces the *pre-drop* coalition to authorize the cut), with the **post-cut roster re-checked against the inv 12 bounds** (a cut violating a **hard** inv 12 bound — a hostage `threshold = |roster|` at `|roster| ≥ 3`, an emptied roster, or a sub-floor threshold — is rejected → a simultaneous `threshold` drop, which the `Rpr` may carry, or reincept; a cut to `|roster| = 2` is accepted-with-warning, per inv 12): **one event that repairs *and* evicts at `v_{d-1}`**, so the member is gone the instant the fork resolves and no post-repair window exists (atomic **by construction**, not merely one txn). This **supersedes the two-event `{Rpr, Evl}` batch + cold-4 A2's `Ror`+`Rot`** — no separate `Evl`, no `Rot`, no mixed-kind anchoring (it is a `Rpr` with a field), so the repair stays a **single event** and the atomic page holds at `2·64 + 1 = 129` (both competing branches ≤ 64 + the one repair — area-kel; a two-event repair batch would need `2·64 + 2` and break the single-page transfer). An **add** (evict-and-replace's replacement) is non-urgent → a later `Evl`; a **kill** (`Trm`) likewise stays a separate subsequent event (kills are always sealed — below). The **cut target is operator-chosen** — the fork-causer is the motivating case, not a structurally-bound check (the verifier can't tell operator from adversary); cutting any member is sound because `t_recover ≥ t_govern`. **A repair is NOT final-on-arrival — the stale-repair / gossip-advanced-state re-fork (2026-07-01; witness-scoped 2026-07-02):** a repair resolves the divergence it was *authored against*, but a node **behind on gossip** may hold only one branch (reading the chain **Active**) and accept a fresh content `Ixn_c` extending it; the incoming repair, attaching at the pre-repair tip, then lands as a **sibling of `Ixn_c`** → a **new** `{Ixn_c, repair}` fork its `fork` never covered (`Ixn_c` didn't exist when it was authored). A repair is **privileged-but-non-terminal** (unlike a `Trm`, which wins on tier-rank with no successor), so this does **not** auto-resolve by tier-rank. **On a witnessed chain this re-fork never goes LIVE (2026-07-02):** the repair is always-witnessed and seals on arrival; a witness already holding it declines `Ixn_c` (dead / below-seal content — federation §1e), and non-witness nodes accept nothing sub-threshold — at worst `Ixn_c` earns receipts in the propagation window before the repair reaches its witnesses (durable, like all receipts), and it is below-seal-inert the moment the repair lands (witnessed-but-dead, re-issued; no freeze, no second repair). The narrative below is the **residual's** story — direct-mode/solo chains and witness compromise, where nothing gates `Ixn_c`. **The resolution is root-pointing, not a second repair (Jason 2026-07-01):** a repair's `fork` names a losing branch's **root** (its first divergent event — ONE root; the list collapsed 2026-07-02, inv 4), which **condemns the whole subtree** — so a losing branch a lagging node **grew after the repair** is dead **by descent**, no follow-up needed (example 9: `Rec.fork → Ixn#2` condemns `Ixn#2` *and* its later `Ixn#3`; per example 9's own description the grown `Ixn` "is witnessed but will be considered as part of the forked chain, which is capped at 64 events since the last sealing event — it will not contribute to the canonical branch"). Any branch the repair does **not name** (an additional held branch, or a truly-missed one — identical closure, which is what let the list collapse) has its **first event** locked below the advanced seal (seal-cap) and **everything built on it dead by descent** — **deadness descends: an event whose parent is dead is dead** (the per-event seal-cap locks only the *first* event; the descent rule kills the growth — cold-r3 F1, which correctly caught that the seal-cap alone leaves a missed branch's *growth* unclassified). So a signing-key (tier-1) adversary who keeps extending a missed dead branch merely spews dead events into a **bounded** fork — depth-capped at 64 per lineage, breadth bounded by **retention** (≥ 2 kept per position, the rest droppable) with the **one-content-sibling witnessing rule** on top (a witness signs the first content sibling at a position, declines later ones; privileged siblings witnessed up to **two** per position — two prove `disputed`, then declined; the repair is privileged, no separate clause — federation §1e) — then the depth-cap forces a seal-advancer → `disputed` — **harmless** (they lose the ability after that; a *privileged* event on the branch would need the reserve → `disputed` anyway, the tier-2 terminal case). Either way there is **no `{Rec, Rec}` collision and no reincept** — the all-content case converges to Active. This is the **content-completeness** of the repair-completeness proof; the only machinery beyond root-condemnation is the **one-line deadness-descends rule** (with the `Trm`-seal-sibling precedent) plus an **optional witnessing gate** (a witness holding the repair declines to witness competing dead *content* events — reduces the garbage; one that slips through is retained but dead-by-descent — federation §1e). **The KEL / IEL asymmetry (Jason 2026-07-01):** a **KEL `Rec` self-neutralizes the culprit** — it rotates the signing **and** recovery key (`recoveryHash` is re-committed, so the reserve persists and the next `Rec` is always authorable), locking out whoever forked with the old key, so the culprit can mint **no new fork** after the `Rec` propagates; and the `Rec`'s `fork` root **already condemns the current fork's subtree** (growth-proof, capped at 64; unnamed branches close below the seal + by descent) → **one `Rec` terminates**, no re-fork loop (cold F3: termination is the 64-cap on the fork window + key-rotation closing new forks, *not* "the second `Rec` is the last"). An **IEL `Rpr` rotates no identity key** (an IEL is a threshold over member KELs), so an **adversarial** re-forker is *not* neutralized by the repair — termination needs a **roster change**: the second `Rpr` carries a **`cut`** (the repair-and-evict fold, above) evicting the culprit. A **benign** gossip-lag `Ixn_c` (an honest member's content on a lagging node) needs no cut — it is archived and re-issued, terminating as honest members catch up to the repaired tip. No reserve-exhaustion either way (each participating member's `Ror` re-commits its reserve — the KEL `Rec` likewise: `recoveryHash` req, inv 15 / event-shape). **Operational, not a new mechanism** — freeze-on-collision, the repair-and-evict `cut`, and content-rail serialization (the fenced single content submitter — area-iel §5) are the levers; this is the *propagation-side* view of the same re-fork family as the repair-and-evict timing attack. **Content-rail serialization is, on a witnessed chain, a LIVENESS/waste discipline, no longer safety-critical (2026-07-02):** the floor prevents the content fork forming, so the un-serialized cost is stalls + re-issuance, not terminality; it stays the load-bearing lever for direct-mode/solo chains. **Governance serialization remains safety-critical** — `{Evl, Evl}` is privileged, always co-witnessed → `disputed` (the floor never gates privileged events). **The on-arrival completeness rule (F4, refined to root-pointing + tier 2026-07-01):** a node validates an incoming `Rec`/`Rpr` as an **ordinary event at its attach-position** (never auto-applying it as a resolution). The outcome splits on the **tier of the un-covered branch**, not on a blanket freeze: (i) an **un-covered ordinary-data** branch does **not** freeze the chain dead — the repair is **accepted**; the branch the repair **named by root** is condemned (subtree dead), and a branch it did **not name** has its first event locked below the seal and **everything built on it dead by descent** (**deadness descends** — an event whose parent is dead is dead); both ride a **bounded forked chain** (depth ≤ 64 per lineage; breadth per position by retention + the one-content-sibling rule), witnessed but never canonical, content re-issued forward — **never orphan-dropped**. (ii) An **un-covered key-change (privileged)** branch is **never archivable** → ≥ 2 privileged → **`disputed`** (validated-not-trusted + FORCE-by-provenance, inv 17), regardless of seal — a privileged branch below a seal is **not** inert (archiving it would bury a rotation). So a repair is **content-final** once it seals (root-condemnation + the seal-cap close every content branch, present *or* grown), but **privileged-final only once the minting capability is neutralized** (the `Rec` rotation / `Rpr` cut, above) **and** the beacon confirms no omitted privileged branch — strictly, *final barring the eclipse residual*, fail-secure (the beacon is a detection oracle, not an absence-certifier; cold F2 / inv 8). The full matrix (safety + convergence, adversarial) is the **repair-completeness correctness proof** — `.working/vdti-repair-completeness-proof.md`, structured as content-completeness (root-condemnation + cap) / privileged-completeness (neutralization + dispute) / the tier framing — encoded into `kel/reconciliation.md` + `kel/merge.md`. **Cross-layer (SEL ↔ owner IEL, 2026-07-01):** a SEL is anchored to its owner IEL (kind-strict, inv 4), which is its **clock**. Two rules close the cross-layer case: **anchor-monotonicity** (a SEL event is valid only if it extends its SEL's latest IEL-anchored tip — a re-anchor is malformed/inert, inv 4) and **cross-layer deadness-descends** (a SEL event on a dead IEL anchor is dead). Together they give the theorem *a valid SEL fork implies an IEL fork beneath it* — so a SEL never forks under a *linear* IEL (no unrepairable deadlock), and every genuine SEL fork rides an IEL `Rpr`. Cross-layer safety is airtight by tier: a dead IEL event is always a content `Ixn`, so a dead-anchored SEL event is always content; a **signing-key (T1) compromise is fully deadenable** — no reserve → no privileged event → one recovery `Rpr` archives the whole tail (no privileged event in it) → every anchored SEL event dead by descent, no reincept. **Two foundational rules govern every repair:
    (1) only tier-1 events are *archivable* (content `Ixn`; on the SEL also the floor `Pin`) — a privileged (T2/T3) event is never archived/overturned** (reversing
    a rotation resurrects retired keys — the backdate/resurrection class — and un-doing a kill breaks a third
    party's reliance); **(2) you never extend an adversarial event** — a repair extends only the submitter's *own*
    event or the shared pre-divergence ancestor `v_{d-1}`. *(`Ixn` is plain content — the round-3
    `content: user | governing` flag is **removed**; its one intended user, the federation clock, is **not** an SEL
    event but an **inline timestamp value** on each federation `Wit`'s `manifest.clock` — inv 4 / federation §1f.)* A divergence
    is resolved by **tier, not identity** — chain data can't tell operator from adversary (both branches were
    authorized when they landed), so resolution turns on **tier**, never on who is presumed legitimate.
    **Recovery — the universal rule:** a `Rec`/`Rpr` attaches at **your last event**, **retaining** your branch
    (the **retained tail**) and archiving every other branch (the **archival tail(s)** — there may be several; the
    adversary can submit divergent `Ixn`s and you archive all of them). Rule 2 is automatic (you extend your own
    branch). **When the retained branch's own tip is *terminal* (a `Trm` — identity/SEL terminate), no `Rpr` is authored** — a terminal
    admits no successor to carry one; the privileged branch **wins on tier-rank** and the losing content is archived
    non-canonical (`{Trm, content}`, matching landed protocol-doctrine). **A kill-anchor (`Rev`/`Dth`) is NOT terminal** — it seals a kill
    on a *target*, not its host IEL, so the IEL continues; `{Rev|Dth, content}` is therefore **recoverable** exactly like
    `{Evl, content}` (retain the kill-anchor branch, archive + re-issue the content via an `Rpr`), terminal only when it is
    one of ≥ 2 privileged branches. The attach-at-your-last-event form is for a
    **privileged-but-not-terminal** retained tip (`Evl`/`Rot`/`Ath`/`Fld`/`Rev`/`Dth`); to both resolve a content fork **and**
    identity-kill, a `Trm` on the winning branch does both in **one** event — it buries the content loser below its own
    seal and terminates; a separate repair-first is only for an explicit condemnation record (a privileged loser is
    `disputed`, un-killable anyway). *Not* the common/divergence ancestor unless you authored nothing past it (recovering there archives
    your own content when your `Ixn`s precede the adversary's). The permission check is one question about the
    archival tails — **does any contain a privileged event?** **No** (all content `Ixn`) → **permitted** (`Rec` at
    your last event; your retained tail may carry your *own* `Rot`, kept-not-archived). **Yes** (a `Rot` — forked
    *or* tip-appended — `Evl`, `Ath`, or `Rev`/`Dth` in any archival tail) → **not** permitted (can't archive — rule 1, extend —
    rule 2, or fork — `{Rot, Ror}` ≥ 2 priv → terminal) → **reincept**. So the recovery reserve defends the
    **signing** key (a T1/content compromise), **not** the **rotation** key — a `Rot` in an archival tail is the
    point of no return.
    **The irreconcilable / data-local view (node-agnostic):** the archival-tail rule is *party-relative* (your
    tails); the symmetric, node-agnostic condition is **branch-level** — **≥ 2 branches each carrying a privileged
    event past the fork** is **irreconcilable**, terminal for *everyone* (any party retains only its own branch, so a
    second privileged branch always lands in *some* party's archival tail). It is **data-local**: any verifier walks
    it from the retained branches — a node **retains** a competing branch as non-canonical evidence (keep-all-data,
    not discarded at the seal-cap), and the **witness beacon** enumerates the competing branch SAIDs so a one-branch
    holder fetches and walks the rest (the federation **propagates**, never decides). **A repair's `fork` (the losing-branch root)
    is validated, not trusted** — the verifier independently computes the competing set from the retained branches
    (+ the beacon), and a privileged event in **any** competing branch, named or not, forces `disputed` (every
    privileged event is a seal-advancer → a spine fork — walk-independent), so an omitted `Rot` can't
    be hidden by sealing past it (round-2 review fix, 2026-06-24; re-based off the list 2026-07-02 — unnamed content
    branches close below the seal + by descent, inv 4). The seal-advancing events form a
    `previousSeal`-linked **spine** on which a privileged divergence is a single visible fork (inv 17). `{Rot, Rot}`
    is moreover a **confirmed reserve compromise** (two valid rotations reveal the *one* preimage at `v_{d-1}`);
    `{Evl, Evl}` is terminal for the same branch-level reason but is **not** a reserve-compromise proof — disjoint
    sub-quorums reveal *different* preimages, so it can arise from an honest partition (hence content/governance
    serialization). **Reincept** is what a party does when **no valid repair exists for it**: a **T3 compromise**, or a **competing
    branch it must archive carries a privileged event it did not author** (a key-state branch you didn't author is
    un-archivable → the point of no return; the party that *did* author it recovers by **retaining** it). This is
    **broader than `disputed`** — `disputed` (≥ 2 privileged branches, node-agnostic) forces reincept on *everyone*, while a
    *single* privileged branch you didn't author reads `forked` yet still forces *your* reincept. *(Clarified 2026-07-05,
    freshread-8 B: "genuine reincept ≡ a privileged event in an archival tail" wrongly equated the party-relative recovery
    block with the node-agnostic `disputed` condition; a branch you *archive* is content-only, so a privileged competing
    branch is what blocks recovery, not an "archival tail.")*
    *(Removed as wrong: "anchor realized on recovery," the "singleton residual," and "tip-appended `Rot` recoverable
    by forward `Ror`" — each had the victim extend, archive, or realize an adversary's `Rot` (rules 1/2), or recover
    at the ancestor and archive their own content.)*
    *(The `../kels` diagnosis: kels classified `Rot` as **non-privileged**, so a `{Rot, *}` fork was "recoverable"
    and a `Rec` could *archive* the forked `Rot` (its divergence-ancestor-extending shape) — un-rotating,
    resurrecting the retired key: **the backdating attack vdti exists to fix**. vdti treats `Rot` as a **privileged
    branch**, so a `Rot` you didn't author lands in an **archival tail** and the repair is forbidden. The one case
    kels lacked — a *single* privileged branch **kept by its author** (its archival tails all content) — is exactly
    what vdti permits; every other privileged-branch divergence stays terminal, as in kels's "privileged divergence
    is terminal". There is **no challenge
    event**: archival (rule 1) and extension (rule 2) are both out, and a challenge reaching a past serial would be
    the backdate kill-switch — that surface is closed structurally by the seal-cap + the spent-recovery-preimage
    rule, not by adding an event.)*
    **Trust on a divergent chain — the seal is the boundary (walk/trust, locked 2026-06-22).** What a consumer may
    honor splits on *recoverable vs terminal*, but the cut is always the **seal**, never the divergence point:
    everything **at-or-below `last_seal_advancing_event` is permanently final** and honored regardless of any later
    divergence — **with the tier qualifier (cold N7, 2026-07-01): "final" is against later *content* divergence** (the
    sealed *linear* events are immutable); **a competing *key-change* (privileged) branch that forks below the seal is
    a spine fork and still forces `disputed`** — it is never inert (archiving it would bury a rotation; inv 13 F4).
    (the verifier surfaces it — inv 8); everything **above the seal** carries tier-1-only durable auth and
    becomes durable only when a later seal-advancing event lands **cleanly** past it. A **recoverable** divergence's
    repair seals the surviving branch → its above-seal anchors become durable; a **terminal** divergence never seals
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
    - **Origination freezes.** The instant a chain holds a **live** fork (two **distinct** — different-SAID — events at one position, at-or-above the **derived** seal), a node **originates no new work** — content, governance, rotation, kill — that would **extend the contested position**; the only events it accepts are the ones that **resolve** the fork: the repair (`Rec`/`Rpr`), or — for a **content** fork — a **burying seal-advancer** on the winning branch (below), which attach at the winning branch and seal past the loser rather than grow the fork. This is a **merge-origination posture**, *not* a stored state flag.
    - **The reading is a pure walk of the held set (`region()`).** The verdict — Active / `forked` / `disputed` — is computed from the events the node holds, with the **seal derived** from them (the highest cleanly-linear seal-advancer). So "frozen" never makes identical held sets read differently: a **fork-first** node and a **seal-first** node holding the same events read the same thing. A **content** fork that a later-held seal-advancer buries below the new seal re-reads **Active** on every node, order-independent (the loser is below-seal-inert — you can't fork the past). A **privileged** fork is never buried (a below-seal privileged branch is a spine fork → `disputed`), so its origination-freeze persists until reincept. `log.md`'s "state is computed from the events the node holds, never a flag" is now literally true.
    - **The safety shape-gate runs at the acceptance point in BOTH modes (Jason 2026-07-03).** Rejecting an **invalid shape change** — a seal-advancer that would bury a *privileged* branch, a `Rec` condemning a privileged branch or its own retained chain — is enforced by the **witness** on a witnessed chain (refuse to witness → the shape never reaches threshold; a non-witness's merge pre-check is just "threshold met?") and by the **merging node itself** on a direct-mode chain (no witness to defer to — it self-gates). Merge otherwise just integrates (keep-all-data) + the seal-cap; it does not stick-freeze the reading. Content-fork **prevention** (one-content-sibling + majority floor) stays **witnessed-only**; a direct-mode content fork forms, reads `forked` (fail-secure), and resolves by repair or burial (declining it by first-seen with no shared witness would silently split — fail-open).
    (**exception:** a `{Trm, content}` / terminal-tip divergence needs **no** `Rpr` — the terminal `Trm` is the single privileged branch and **wins on tier-rank**, the content archived non-canonical; see *Recovery — the universal rule* above.) This is the founding
    insight of the primitive (it's why `../kels` exists). **Divergence is *distinct*-events-at-one-position;
    identical events dedupe — SAIDs are content-addressable, so two byte-identical events ARE one event** (the
    submit path accepts an already-present event idempotently, never as a second branch; detection keys on distinct
    `witnessed_said`, federation §1e). So a `{kill, kill}` collision (two competing `Rev`/`Dth` kill-anchors) is always of **distinct** events — only an
    *idempotent re-submit* of byte-identical bytes dedupes; two **independently authored** kills are never byte-identical
    (each commits its own `pins`/position), so even the *same* kill by two sub-quorums is two SAIDs → a genuine collision,
    serialized away (one submitter), never a silent merge (R3-1). *(The "both revoking the same cred → dedupe" example was
    **wrong** — corrected 2026-07-05, freshread-8 E; a cred-SEL moreover can't fork under a *linear* issuer IEL
    (anchor-monotonicity), so two parties revoking one cred only forks if the issuer IEL forked — resolved by the IEL `Rpr`.)* It makes F-F's scenario *unreachable*: a governance event can never sit
    *above* an **unresolved** divergence, because a node originates nothing onto a live fork — the only appends onto
    one are the resolving repair or a **content-fork-burying seal-advancer** (which resolves it), never new governance. (A divergence with
    **≥ 2 privileged branches** — e.g. `{Evl, Evl}` — is irreconcilable → reincept; a `{Evl, content}` collision is
    **recoverable** — the `Evl` author retains the `Evl` branch and archives the content archival tail.)
    *Src:* §4 + Jason 2026-06-20/21. `[locked]`
    **Consequence — a network split + governance (F7, refined 2026-06-21):** if the network splits, one half can
    author a `Evl` while the other issues content at the same position; on heal they collide. The operator retains
    the `Evl` branch and archives the content (an archival tail of content), so **`{Evl, content}` is RECOVERABLE**
    — **not** an automatic brick. Only **`{Evl, Evl}`** (both halves do governance → ≥ 2 privileged branches) is
    **irreconcilable → reincept**.
    **The resolving `Rpr` authorizes under the *post-`Evl`* roster (Finding 14a, 2026-06-21)** — the kept `Evl` is
    canonical, so the repair operates in the world after it; any members the `Evl` *added* are already T1-consent-
    anchored (a precondition of that `Evl`'s validity), so the post-`Evl` authorizing set is well-defined and needs
    no new consent at repair time.
    **Handled operationally** (one designated governance submitter + hold governance under a suspected split) — now
    only to avoid the *both-sides-governance* terminal case, not every governance-during-partition event; witnesses
    make a bricked state detectable on heal. A protocol-level "block a `Evl` unless its parent is witness-confirmed"
    gate was **rejected** — each half's own witnesses confirm its events, so it passes inside the split, and it
    freezes governance whenever witnesses are unreachable (a halt-by-DoS lever). See `vdti-area-iel.md` §4 ★★.
    `[locked]`
    **Consequence — kills are always sealed; a validity bound is a hard contiguous boundary (LF1/F-B/F-H,
    locked 2026-06-21):** a **kill** (revoke/close/rescind/terminate) is always **sealed on arrival** (anchored
    in a **`Rev`** or **`Dth`** — the dedicated sealed kill-anchors, T2, distinct from `Evl`), so it is **terminal — never in the
    repairable region** and can never be archived by a repair (closes the silent-un-revoke, F-B; there is no
    unsealed window to un-do, LF1). *(A kill-anchor (`Rev`/`Dth`) is privileged/terminal-on-divergence like any T2 event, so a
    `{kill, kill}` split-collision of **distinct** kills is **terminal → reincept**. **R3-1 RESOLVED (2026-06-21):
    no merge — corrected rationale (round 4).** You **cannot reorder** events (the SAID commits `previous`, locking
    the chain order) or **archive a privileged event**. So a "merge" is **not** a reorder — it would mean *removing*
    both colliding kills and **re-authoring** new ones with the full `t_govern`/`t_authorize` the IEL requires (enough
    devices re-signing): a carve-out against privileged-divergence-is-terminal. The kills **do commute** (a key-less
    kill-anchor resurrects no key), so the merge is **sound in principle** — we **decline** it on model-cleanliness /
    don't-relax-finality grounds (minimize carve-outs), **not** because it's unsound, and **not** the earlier wrong
    "zero availability gain" (a merge *would* preserve the identity; no-merge forces **reincept + reissue**).
    **Only a byte-identical re-submit dedups** (SAID over content; sigs are adjacent, but the `pins`/`pin` an event
    commits **are** in the content, so a different signer subset anchors different member-KEL tips → a *different* SAID —
    "same SAID regardless of signer subset" was **wrong**, corrected 2026-07-05 freshread-8 E), so "both sides revoke the
    same cred" is **not** a dedupe — two independent acts are distinct events (different pins), a genuine collision
    serialized away; only **distinct** kills at one position
    collide — rare, and avoided by serializing kills (one submitter; no free-for-all kills under a suspected split,
    which is load-bearing, not a nicety). This **decouples R3/R3-8** — `t_govern ≤ t_recover` stands on its own (and is now a **hard** floor — inv 12 / 2026-06-30).)* Separately, a **validity
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
14. **Federation = a restricted IEL (kinds `Fcp`/`Wit`/`Trm` — `Fcp` is the federation IEL's inception marker (§inv 4 / federation-ref §2, a structural disambiguator the verifier dispatches on, *not* a trust carve-out), and `Wit` is the governance kind replacing the user `Evl`; the set is a restriction *plus* the `Fcp` marker + `Wit`, not a pure subset; A3 2026-06-28); witnessing is as-of-context — prevention for witnessed content (the majority floor, federation §1e), detection for the rest; the roster is a delta.**
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
    rotation closes windows → past forgeries become detectable. **Three clock guards + a residual:** (1) the **365-day `MAX_WINDOW`** —
    a never-rotated window **auto-closes at `T_join + 365 days`** (no unbounded open window; federation §1f, cold-9 C2 /
    cold-10 F4); (2) a consumer rejects / stale-flags any federation **clock** time beyond `now + band` (no **future-dating** by a
    `t_govern`-compromised federation — round-5 F4); (3) a **receipt `τ`** is likewise capped `≤ now + band` (symmetric with the clock ceiling — cold-12 F5). **Residual:** detection of a *just-closed* window lags by the staleness threshold (round-5 F5 — note `F5` is overloaded: round-5 = this detection-lag, cold-12 = the receipt-`τ` ceiling above) → tight thresholds on high-value
    bindings, and a recent `cut` is freshness-sensitive. Witness rotation is **only** a synchronized federation
    **`Wit`** (the witness's KEL `Wit` **is** the rotation and anchors the IEL `Wit` — no separate `Ror`; an
    off-ceremony `Ror` is unhonored — F3). See §1a / §1f. *Src:* §7 + federation-ref + B/F-A +
    S2 resolution 2026-06-21 + round-5 F3/F4/F5. `[locked-candidate]`

## Inception & the pin mechanism
15. **Inception tier follows what it establishes; every SEL's `Icp` is floored by its serial-1 event.**
    - **KEL `Icp`** = T1 (the root, self-authorizing — no chain above it).
    - **IEL `Icp`** = T2 (it establishes *governance* — roster + thresholds; a genuine state-establishment).
    - **SEL `Icp`** = **T1** (it establishes single-owner *data*, not governance; an IEL `Ixn` anchors its v1, never the `Icp` itself — see below). The
      `Icp` carries **no `pin`** (it must stay recomputable for lookup), so it is **floored by its serial-1 event**,
      which carries the pin the `Icp` can't (`pin == anchoring IEL Ixn.previous`). Now that **every event pins**, that
      floor is **any event** — a content `Ixn`, a `Trm`, etc. — so a bare **`Pin` is the fallback floor, used only
      when inception carries no other first event** (an *incept-and-sit* SEL — e.g. a cred issued with no immediate
      content or kill must still floor at issuance, its as-of can't be deferred). A multi-party-doc author is also
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
      For a **cred-SEL**, **`data` = the credential's SAID**, so the `Icp` carries **no manifest**; the cred body
      carries **no pin** either (the doc-layer pin was dropped 2026-06-26 — the as-of is the anchoring position). The cred prefix is then **recomputable from the
      held cred** (self-locating revocation — area-sel §1), which is fine: safety is **owner-rooting** (only the
      owner IEL anchors at the locus), **not** prefix-secrecy. "Discoverable" ≠ "blind-recomputed-for-lookup" [F-J;
      F10b; area-sel §1]. A *private* cred stays private by **three things together** (F2, inv 16): the `nonce`
      keeps the prefix unguessable, logs are referenced **by prefix only** (no by-SAID lookup → the public
      `said(v1)` in `anchors[]` is an opaque commitment — `said(Icp) == v1.previous`, one hop back, equally
      opaque), and the **private cred body is not published**.
    - **Lookup-SELs** (verifier blind-recomputes `derive(owner, topic, data)` from data it already holds, e.g.
      `data = P`): a **rescission** lookup-SEL is `{Icp, Trm}` — the terminal `Trm` is the kill (sealed via an IEL
      `Dth`) carrying the **`bound`**; it pins like every event. The serial-1 **event** floor is universal
      (above), not lookup-specific — for the rescission `{Icp, Trm}` the `Trm` **is** that floor (no separate `Pin`);
      the `Pin` *kind*, when used, does **only** the floor re-pin (`t_use`/T1, **not** sealing) — the SEL re-seal is
      the separate **`Fld`** (T2, seal-advancing; the `Evl`/`Rot` analog) (2026-06-27).
    - **SEL `Trm`** = the kill — **always sealed on arrival**, anchored in one of the two dedicated sealed
      kill-anchors (**T2**; identity-kill → `Trm`, **T3**): an **IEL `Rev`** (revoke / close your own credential
      or app-SEL, **`t_govern`**) or an **IEL `Dth`** (deauthorize a granted delegation / doc-membership,
      **`t_authorize`**). **No delayed / unsealed form** — a kill is **monotone** and must be permanent on
      arrival, so it rides a sealed kill-anchor. Because a `Rev`/`Dth` is terminal-on-divergence, the kill's
      anchor can never be archived by a repair (silent un-revoke **F-B** closed by construction), and there is no
      unsealed window to un-do (**LF1**). Terminate = (cred-SEL) **revocation** / **closure** (via `Rev`);
      **rescission** is the same kill shape on a lookup-SEL — a lookup-SEL **`Trm`** anchored by a `Dth`
      (carrying the `bound`). The kill-anchors are **distinct from `Evl`** (roster/threshold-change only, always
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
    is T2/T3:** a *credential* is **content** — one bounded, revocable claim to an external party (forging it = one
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
    **Attribution on a standalone SAD requires a SEL anchor, never a self-asserted pin — the custody fix
    (2026-07-03).** A binding a verifier must *resolve* (fetch the named chain and walk it) needs the entity
    **prefix** — a SAID has no global index (above) to invert. On a **chain event** a position pin is sound: it is a
    chain field corroborated by append-only `previous`-linkage (the SEL down-pin `owner`(prefix) + `pin`(SAID); the
    federation `federation`(prefix) + `federationPin`(SAID) — inv 5). But a **standalone SAD is not a chain event** —
    it sits on no chain, so a self-asserted position pin has **nothing to corroborate it** and is freely
    **backdateable**: pick an old position where a since-broken key was authorized → forge a "valid as-of-then" write
    (and over a long enough horizon *any* key breaks, so the backdate is real, not hypothetical). This is the exact
    self-asserted-pin forgery inv 5 already closed for documents. **Resolution — an `owner`-bearing SAD is attributed
    *only* via a SEL anchor (the credential pattern, inv 15, generalized to every attested doc):** custody carries
    **`owner`** (the writer IEL prefix) **+ `topic`** (the doc's namespace / schema), and the SAD **must be anchored by
    a SEL** whose prefix is `derive(owner, topic, said)` and whose `data` is the SAD's SAID. Then **as-of authority =
    the SEL's append-only anchoring position** (inv 5 — backdate-proof: forging it needs a fresh IEL `Ixn` at the
    owner's *current* tip, which a rotated-out key can't author and can't insert in the past → the threat reduces to
    current-key-compromise-at-current-time, the accepted limit, inv 13); the **self-asserted `pin` is dropped** —
    `custody { owner, topic, readPolicy }`; and the anchor is **self-locating** — a holder re-derives the SEL prefix
    from the held doc's `owner` / `topic` / `said` and walks it **by prefix** (inv-16-clean, no SAID inversion —
    exactly the cred-holder mechanism, inv 15). **Structural at two levels:** the write path **pre-auths** (the
    sadstore refuses an `owner`-bearing SAD without its corroborating SEL — `SEL.owner == owner ∧ SEL.data == said`),
    **and** a consumer **verifies independently** (self-location above; the store is untrusted — end-verifiability).
    **Field rule: `owner` present ⟺ `topic` present ⟺ the anchoring SEL exists** (an anonymous write carries none of
    them); a `topic` is a **vdti-reserved** namespace (`CRED_TOPIC`, `RSC_TOPIC`, …) **or** an author-defined topic +
    schema, anchored ("SEL'd up") the same way. Because the doc's SAID commits `owner` and `topic`, the triple
    `(owner, topic, said)` is tamper-evidently bound to the anchor location. **Reads are the separate axis** —
    `readPolicy`, current-mode, independent of write attribution. **Encode:** `custody.md` (§The sub-fields, the new
    §SEL-anchor doctrine, §Two evaluation modes, §Four combinations, §Adversarial framing), the wrapper shape in
    `sad.md` / `availability.md`, landed `pin`/`ownerPin` refs (incl. `said.md`, `glossary.md`), and the `custody`
    refs in `vdti-area-multi-party-documents.md`. *Src:* Jason 2026-07-03. `[locked]`
    *Consequence (the private-cred boundary, F2):* a `said(v1)` (= `said(Pin)` for a cred) harvested from a public
    IEL `anchors[]` does **not** invert to the cred-SEL prefix and can't be looked up (`prefix = derive(...)` ≠
    `said(v1)`; and `said(Icp) == v1.previous` is one hop back, itself not in `anchors[]`), so a non-holder can't
    reach a private cred; a **holder**
    derives the prefix from the cred it holds (`derive(issuer, topic, cred_said)`) and walks the SEL by prefix.
    **Private cred bodies are not published to the shared store** (held by issuer/holder, disclosed peer-to-peer);
    only genuinely-public SADs every verifier must resolve for a public chain — the `roster`/`witnesses`
    config SADs (the `clock` rides inline in the federation manifest) and a *public* cred's body — are content-addressed by SAID (no privacy cost). *Build constraint:*
    the gossip / deferred-deps drain resolves missing deps by **gossip-push + by-prefix fetch**, never a by-SAID
    `get-post-sad`, for cred-SELs (kels precedent — it never needed by-SAID). **Two rules added 2026-06-23:**
    (a) **every prefix-bearing query carries the prefix in the request body, not the address** (like HTTP QUERY — never a URL-encoding GET) — a path/query
    prefix leaks into common access/proxy logs that aren't otherwise privacy-controlled; (b) **all inter-node mesh
    traffic is encrypted** (ML-KEM-1024 KEM + AES-256-GCM AEAD) — receipts AND the events they propagate (generalized
    from gossip-only, 2026-06-23); confidentiality, not trust (trust is end-verifiable). Prefer **push over pull**
    (gossip events rather than an inter-node query → no second channel to secure; impl-notes). A private log's folded
    run stays **by-prefix** (never by-SAID-fetchable →
    the harvest stays closed; folding-idea Q4 — RESOLVED). **Residuals:** the public IEL still leaks issuance
    *volume/timing* — though folding issuances into the IEL's mixed `anchors[]` (alongside other SEL anchors) muddies
    the per-cred count for a passive observer (a witness resolving each SAID can still correlate); and the **witness
    beacon** floods receipts that pair a cred-SEL prefix with its
    `said(v1)`, so a **federation witness** (it holds the receipt and can read the public `anchors[]`) can correlate
    `issuer ↔ private-prefix`. This is **passive and undetectable** → a standing **confidentiality property of
    federation membership** (the mesh = the federation roster; joining means being in it), not enforced by rotate-out.
    So the non-invertibility holds **for any party outside the federation mesh**; a witness inside it can correlate. *Src:* Jason 2026-06-21 (kels addressing precedent). `[locked-candidate]`

## The spine, the fold, and data-local detection
17. **The spine overlay + keep-all-data make divergence detectable from the data (2026-06-23).** The seal-advancing
    (privileged) events form a **spine**: every seal-advancing event carries a top-level **`previousSeal`** back-link
    to the prior one (the `Icp`, or the `Fcp` inception of a federation IEL / founder KEL, is the spine root). Following `previousSeal` renders the spine view
    (`Icp → seal → seal → …`); following `previous` renders the full **flat** chain. `serial` is **flat and
    unchanged** (no epoch re-count). A **repair** seal's `manifest` carries a **`fork`** role (inv 4) — the single losing-branch root it resolves (every
    other competing branch closes below the seal + by descent — inv 4, 2026-07-02); a
    non-repair seal carries no such role. The retained run since the prior seal is **not committed** — it is the
    linear chain `[previousSeal..previous]` (nodes keep full bodies; the flat query returns them), and "content was
    folded here" is the derived predicate `previous != previousSeal`.
    - **Two views, one dataset.** The spine is verified by the **same walk algorithm** with `previousSeal` substituted
      for `previous`, yielding authority + a **terminal-divergence** view (a spine fork = two competing seals = privileged = terminal) but **not recoverable content forks or content completeness** (that needs the flat
      walk). Served as body-carrying reads — `/folded` (spine) and `/flat` (full) — the prefix in the body, not the address (inv 16).
    - **Detection lives on the flat chain (the guarantee); the spine is a convenience pre-check.** Terminal = **≥ 2
      branches each carrying a privileged event past the fork** (inv 13) — a **data-local** walk over **retained**
      branches (keep-all-data: a node retains a competing branch as non-canonical evidence rather than dropping it at
      the seal-cap). Skip-a-seal detection is the **flat walk's** (walking `previous` traverses the run; a skipped seal
      appears in it as a seal-advancing event, since a real seal carries its own `previousSeal`) plus **spine-fork
      detection** (the real skipped seal, once held, competes at its spine position). The spine alone trusts
      `previousSeal`; `/folded` is fail-secure — never a hidden authority forgery, worst case the eclipse residual.
      *(The former boundary-SAID O(1) pre-check is dropped 2026-07-01 — necessary-not-sufficient, and the guarantee is
      the flat walk regardless.)*
    - **Content-independence.** A privileged event self-validates against the **prior seal's key state** (on the
      retained spine, via `previousSeal`) + its own committed fields — content (`Ixn`) is key-state-inert, so
      re-validation never needs the content prefix. **So spine verification is content-independent** (it needs only
      the prior seal's key state) — yet nodes **keep the run's bodies** for the flat view (Jason 2026-07-01: the flat
      query returns them), which is what lets the `canonical` commitment go; **privileged retention bounds to ≥ 2 per spine position** (a spent preimage can
      mint unbounded distinct `Rot`s — two competing privileged branches prove terminal, then stop; the kels
      event-level rule lifted to the spine). An `Rpr` commits one losing branch's root as **`fork`**; every competing branch is **retained
      via keep-all-data** (the named root's subtree condemned; the rest inert below the seal, growth dead by
      descent); the retained run's bodies
      are kept (retrievable by-prefix); only the truly *uncommitted* flood is dropped. effective-SAID is computed on
      the canonical (retained) chain + the **unresolved** retained set (a repair-condemned or below-seal-inert
      **content** branch drops out of the digest — forensic, via the `fork` commitment; a **privileged** event never
      settles → it stays a live tip, §1e).
    - **Root-pointing — `fork` condemns a subtree, growth-proof (2026-07-01; single root 2026-07-02).** A repair's
      `fork` names **one** losing branch's **root** (its first divergent event, a distinct child of the fork point *off*
      the retained chain); the
      root **condemns its whole subtree** — every descendant is non-canonical forever, so a losing branch a lagging node
      grows after the repair is dead **by descent**, no follow-up repair (this retires tip-pointing + stacking + the
      below-seal carve-out — inv 4). Any **unnamed** branch (additional, or truly missed) has its **first event** locked below the advanced
      seal (seal-cap) and **everything built on it dead by descent** — **deadness descends: an event whose parent is dead
      is dead** (the per-event seal-cap locks only the first event; cold-r3 F1 caught that the seal-cap alone leaves the
      *growth* unclassified). Each dead **lineage** is **depth-capped at 64
      events past the last seal** (a deeper event forces a seal-advancer, privileged → `disputed`); breadth is bounded by
      **retention** (≥ 2 per position — the ≥ 2-per-spine-position bound above lifted to content — the rest droppable),
      with the **one-content-sibling witnessing rule** on top (a witness signs the first content sibling at a position
      and declines later ones; privileged siblings witnessed up to **two** per position — two prove `disputed`, then
      declined; the repair is privileged, no separate clause — federation §1e). Dead events are
      **propagated + retained** but never canonical (example 9's description — receipt-bearing only where the fork is witnessed; a losing content sibling is declined on a witnessed chain). A witness holding the repair **declines to
      witness** competing dead *content* events (reduces the garbage; one that slips through is retained but dead-by-descent —
      federation §1e). **Two guards:** a `fork` root **on the retained chain** (or the shared
      ancestor `v_{d-1}`) is **rejected** — no self-condemnation, the verifier knows the retained branch from `previous`;
      a condemned subtree carrying a **privileged** event is ≥ 2 privileged → `disputed` (can't bury a rotation).
      Root-condemnation reaches no *live* state — it marks a subtree dead, never extends or revives — so it grounds no
      authority, and there is **no below-seal archival operation, hence no carve-out to guard.** effective-SAID is over
      the **live tips** — every tip at serial ≥ the last clean seal (the canonical tip + every **unresolved** competing
      branch tip in the active window); only a **content** branch settles out (condemned, or below-seal-inert), while a
      **privileged** event never settles (a spine fork → `disputed`, always a live tip) — live-tips, §1e.
    - **The beacon propagates; the data decides (inv 14).** Witness receipts **enumerate** the competing branches so
      a one-branch holder fetches and walks them; the FORCE rule splits by **provenance** — a node that **holds and
      re-validates** ≥ 2 privileged branches forces `disputed` immediately (threshold-independent), while a node
      holding only a **receipt** waits for the **witness threshold** (privileged; a losing *content* sibling never
      reaches threshold under the majority floor — its sub-threshold competing receipts are themselves the fetch
      signal, federation §1e). Receipts say *forked*; the
      data-local walk says *disputed*. The effective-SAID is a **real digest over the live tips** (the canonical tip +
      every **unresolved** competing branch tip — a settled **content** branch drops out, a privileged event never
      does; **no synthetics**; area-vdtid-services §1e); `forked` (reconcilable/pending fork) vs `disputed` (terminal,
      walk-found) is the separate **data-local** walk verdict (not federation-sourced, never in the digest).
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
    **manifest role** (`anchors`/`roster`/`witnesses`/`clock`/`delegates`/`fork`/`content`/`grant`/`bound`) **or** a **top-level
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

## Document-layer evaluation (confirmed — see document-policy §C)
- **The as-issued / current two-function model** — `evaluate_as_issued` (consumes the anchoring positions, resolves
  leaves as-of) vs `evaluate_current` (live attestations at tip) — is **confirmed** as the document/policy
  evaluation model (document-policy §C, 2026-06-20): one shared composer + two leaf resolvers, reconciled to the
  reshape (leaf set, no `policyPin`, revocation-as-lookup-SEL). `[locked-candidate]` *(F-L: was tagged
  `[needs-reconciliation]`; §C did the reconciliation — synced 2026-06-21.)* **Mode renamed `anchored` → `as-issued` (L1, 2026-06-22):** `anchored` collides with the structural verb (`manifest.anchors`, "anchored by", "the anchoring position"); `as-issued` names the issuance-time mode unambiguously. Function: `evaluate_as_issued`.
