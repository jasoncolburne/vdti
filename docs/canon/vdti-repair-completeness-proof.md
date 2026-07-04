# Repair-completeness — the correctness proof (root-pointing model)

**Role: a load-bearing correctness proof, not prose.** It is the **repair-side dual** of the
divergence-**detection** proof in `kel/reconciliation.md` (matrices 1–3, the `forked`/`disputed`
readings + the real branch-derived effective-SAID digest, the beacon, keep-all-data). Detection answers _"is this position forked or disputed?"_;
this proof answers _"is a landed repair **final** (chain → Active), or does it prove the fork
**terminal** (`disputed` → reincept)?"_ — and shows every case terminates correctly and all honest
nodes converge on one reading.

**This is the verification pass that settled the model.** A first draft used **tip-pointing +
stacking** (a second repair to catch a losing branch that grew past the first repair's cut). Two
review passes HELD on it; working their findings against the drawing (`vdti.excalidraw` example 9)
produced a strict simplification — **root-pointing** — that subtracts the stacking apparatus entirely.
The proof below is the root model, verified.

## The model (one paragraph)

**Premise — where forks still form (the majority floor, 2026-07-02).** On a **witnessed** chain,
content forks are **prevented** below fork-cost (`threshold > signers/2` + one-content-sibling-per-serial
witnessing — federation §1e), so the population this proof repairs is the **residual**: **direct-mode /
no-witness chains** (solo — content forks freely), **witness compromise** (≥ `2·threshold − signers`
double-signers), the **roster-delta straddle** (two full quorums under disjoint contexts, zero
double-signers — a content fork that needs the new selectees cut off from the already-propagated old
quorum, i.e. an entrance to the partition/eclipse family; federation §1e / witness-config F5),
**split-stalls** (no content sibling reached majority; the repair — privileged, witnessed —
is the exit), and **mixed `{privileged, content}` races** (co-witnessable by design — the author-kept-privileged
recovery path). The machinery below is unchanged — it runs against this residual population rather than
routine gossip-lag.

A divergence at a fork point `v_{d-1}`: distinct events (each a **root**) extend it at `v_d`; one
branch is retained, the rest lose; the chain freezes. A repair (`Rec` on a KEL, `Rpr` on an IEL/SEL)
retains one branch and names, in its inline **`fork`** field, the **root of ONE losing branch** — its
first divergent event, a distinct child of `v_{d-1}` **off** the retained chain (the list collapsed to
a single root 2026-07-02; every other branch closes as an unnamed one, below). **The named root
condemns its entire subtree**: every descendant is non-canonical forever. So a losing branch that a
lagging node **grows after the repair** is dead **by descent** — no follow-up repair, growth-proof
(example 9: `Rec.fork → Ixn#2` condemns `Ixn#2` and its later `Ixn#3`). A losing branch the repair
does **not name** (an additional held branch, or one truly missed) has its **first event** locked below the advanced seal (the seal-cap)
and **everything built on it dead by descent** — **deadness descends: an event whose parent is dead is
dead** (the per-event seal-cap locks only the *first* event; the descent rule kills the growth). Either
way it rides the **forked chain** — a **bounded** region: each dead **lineage** extends at most **64
events past the last seal** (the seal-advance cap; a deeper event → a seal-advancer, privileged →
`disputed`), and its *breadth* is bounded by **retention** (nodes keep **≥ 2 competing events per position** as evidence
and drop the rest — the content analog of inv 17's spine bound; the queryable set is bounded), with the
**one-content-sibling witnessing rule** on top (a witness signs the first content sibling at a position
and declines later ones; privileged siblings are witnessed up to **two** per position — two prove
`disputed`, then declined; the repair is privileged, so the single resolving repair needs no separate
clause — §Cross-layer, federation §1e). Dead events
are **propagated and retained** yet **never canonical** (example 9's description — receipt-bearing only where the fork is witnessed; a losing content sibling is declined on a witnessed chain); an adversary can
*author* extra siblings but they are droppable, never making the retained fork unbounded (a query DoS).

**Little new machinery:** root-condemnation is a read over `previous`-linkage; the additions are
**deadness-descends** (parent dead ⇒ child dead — same-chain *and* across the **IEL→SEL** anchor edge,
cross-layer — **not** the KEL→IEL participation edge, which is forward-only (inv 13); with the
`Trm`-seal-sibling precedent) and **anchor-monotonicity** (an owner IEL totally-orders each SEL
it anchors — §Cross-layer); everything else — the seal-cap, the depth-cap, validated-not-trusted,
FORCE-by-provenance, the beacon, the effective-SAID digest (real, branch-derived — no synthetics) — already exists. An **optional
witnessing gate** (a witness holding the repair declines to witness competing dead *content* events)
reduces the garbage but is not load-bearing.

## Dispositions (defaults — FLAGGED for veto / the review to vet)

- **D1 — finality is two-valued, per question.** A repair is **content-final the instant it seals**
  (root-condemnation + deadness-descends close every losing content branch, present *or* later-grown). On
  the privileged side, two **distinct** properties hide under one name — keep them apart:
  - **No-resurrection** (**unconditional**): nothing archived is ever un-archived — from the instant the
    repair lands (rule 1 + no below-seal archival), holding **even under** the residual below.
  - **Resolution-stability** (**conditional**): the repaired prefix stays non-`disputed`, treatable as
    stable once (a) the minting capability is **neutralized** (a KEL `Rec` rotates the key out; an IEL
    `Rpr` cuts the member — **vacuous for a benign cut-less repair**, a gossip-lag `Ixn` needing no
    eviction, where (b) alone gates; (a) binds only where an adversarial minter exists) **and** (b) the
    beacon shows no omitted privileged branch. The residual is **not only eclipse**: a historical
    rotation-preimage compromise (an old reserve harvested any time) can mint a privileged event on a
    dead / below-seal lineage **years after** confirmation — the branch did not exist then, so the beacon
    was truthful, yet the read flips to `disputed`. So resolution-stability is **stable barring that
    residual**, fail-secure (cold F2/F6: the beacon is a *detection* oracle, it cannot certify absence).
- **D2 — completeness ≡ the F8 multi-source bar, scoped to the privileged set.** For a loss-of-trust
  read only key-change branches matter; content completeness is closed by the seal + the cap, not the
  bar.
- **D3 — the safety surface is three rules** (there is no below-seal archival, so no carve-out): (a)
  **root-condemnation**, guarded by two checks — the `fork` root must be **off the retained chain** (no
  self-condemnation) and a condemned subtree must be **content-only** (a privileged event in it →
  `disputed`); (b) **deadness-descends** (parent dead ⇒ child dead) — closes a *missed* branch's growth,
  and, **across the IEL→SEL anchor edge** (not KEL→IEL — forward-only), a SEL event on a dead IEL anchor (§Cross-layer); (c)
  **privileged-precedence** — a privileged event on any competing branch → `disputed` regardless of
  deadness (it needs the reserve, so it is the tier-2 terminal case anyway; cold-r3 F3). **The cross-layer
  case adds no *fourth safety* rule:** anchor-monotonicity is a *validity* rule (a re-anchor is malformed),
  and cross-layer safety is airtight by tier — a dead IEL event is always a content `Ixn` (a privileged one
  on a losing branch → `disputed`, never condemned), so a dead-anchored SEL event is always content
  (§Cross-layer, cold F1 leg c).
- **D4 — extend `kel/reconciliation.md`** (a fourth matrix) + merge rules in `kel/merge.md`; state the
  cross-layer rules in the `sel/`+`iel/` anchor-validation doctrine.

*(Gone from the prior draft: the stacked second repair, the valid-pointer set, the below-seal-archival
carve-out, and fork-tip settle-out — all retired by root-pointing.)*

## The completeness matrix

Rows = {tier of the losing branch} × {named by the `fork` root vs unnamed} × {delivered before/after
the seal}, plus the cross-layer rows. Cell = reading + closing rule. *(Unnamed = an additional held
branch or a truly-missed one — identical closure either way, which is what let the list collapse.)*

| losing branch                                                        | reading                                                                                       | closes with                                                                                       |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **content**, root named in `fork`                                    | condemned subtree (all descendants dead, growth-proof) → **Active** on the retained chain      | root-condemnation; the seal-cap bounds each dead lineage's *depth* (≤ 64 past the seal)            |
| **content**, root named, branch **grows** after the repair (lagging) | grown events dead **by descent** — no follow-up → **Active**                                   | condemnation is over the subtree, not a tip (example 9's `Ixn#3`); growth past depth-64 → privileged → `disputed` |
| **content**, **unnamed** (additional or missed), delivered/grown after the seal | first event locked below the seal; **growth dead by descent** (deadness-descends) → **Active**   | seal-cap (first event) + deadness-descends (growth); no orphan-drop (kept, re-issued)              |
| **content**, unnamed, held when the repair arrives                   | repair **accepted**, the branch drops below the advanced seal → **inert** → **Active**         | unnamed-content repair accepted (F4); the branch inerts rather than freezing the chain         |
| **key-change** (privileged) — repair attempted, or a 2nd privileged branch present | ≥ 2 privileged → **`disputed` → reincept**                                 | validated-not-trusted (a condemned subtree with a privileged event); FORCE-by-provenance; a below-seal privileged branch is **not** inert |
| **key-change** (privileged) — a **lone unretained** branch, **no repair attempt** | one privileged branch → **`forked`-frozen** (reconcilable only by its author; reincept is the operational exit, the *reading* stays `forked`) | inv 13 (≥ 2 privileged is the `disputed` threshold; one is `forked`) — *not* `disputed` |
| **≥ 2 key-change branches**                                          | **`disputed` → reincept**                                                                     | inv 13/17 (existing)                                                                               |
| **`{Trm, content}` terminal tip** (no `Rpr`, example 10)             | `Trm` wins on tier-rank, content archived non-canonical → **Active-at-`Trm`**; a late privileged sibling → **`disputed`** | example 10 (tier-rank, no repair); the after-seal privileged asymmetry                             |
| **cross-layer: SEL event anchored to a dead IEL event**             | dead **by descent** across the **IEL→SEL** anchor edge → the SEL reads canonical without it                | cross-layer deadness-descends (§Cross-layer, inv 13); the anchor is condemned/inert, so is what it anchors |
| **cross-layer: SEL fork** (always rides an IEL fork — anchor-monotonicity) | one IEL `Rpr` condemns the losing IEL branch (its SEL events die by descent) + cascade-anchors the SEL `Rpr` for the retained branch → **Active** | the anchor-monotonicity theorem: a *valid* SEL fork ⇒ an IEL fork beneath it, so an IEL `Rpr` always exists to ride |
| **cross-layer: re-anchor at a taken SEL serial under a *linear* IEL** | the re-anchoring SEL event is **malformed → inert**; the SEL stays linear, no fork              | anchor-monotonicity — a SEL event must extend its SEL's latest IEL-anchored tip; no unrepairable deadlock |

## Safety (the two guards + the seal)

**S1 — no self-condemnation / no censorship.** The `fork` root must be a competing child of `v_{d-1}`
**off the retained chain**. The verifier knows the retained branch (walk `Rec.previous` back), so a root
that lies on it — or `v_{d-1}` itself (which is on it) — is **rejected**. So a repair can never condemn
its own retained branch, and there is no root whose subtree includes the canonical chain. *(This is
what a tip-pointing "add `v_{d-1}` to an anchor set" fix would have broken — `v_{d-1}`'s descendants
include the retained branch; root-pointing at the losing branch's own first event excludes it by
construction.)* **The membership walk spans the *full* retained chain** — down to at least the
`fork` root's parent-serial (walking to the pre-fork seal always suffices, one extra page at
most), and the root must satisfy `root.parent = v_{d-1} ∧ root ∉ walkback` over that same full-span
walk (the **tight** form — a competing child of the single fork point; the loose
`root.parent ∈ walkback` an earlier draft carried is a safe superset, not the model — see
`vdti-implementation-notes.md`). **Encode-guard (cold F4):** do **not** reuse `merge.md`'s L-bounded discriminator (it stops at the
divergence serial) — on that truncated set `v_{d-1}` and every trunk ancestor read as *off* the retained
chain, so a `fork` root naming a trunk ancestor would condemn a subtree containing the whole canonical
chain (and the `Rec` itself): the exact censorship this guard forbids, reachable by any T3 holder incl. a
buggy client. The tree-property argument (single `previous` ⇒ an off-chain root's subtree is disjoint
from the retained chain) holds **only** over the full-span walk.

**S2 — no buried rotation.** A condemned subtree is walked; a **privileged** event in it means ≥ 2
privileged branches past the fork → **`disputed`**, not archived (validated-not-trusted). So
root-condemnation can never dead-mark a rotation to un-rotate it. *(The walk-independent closer: every
privileged KEL event is a **seal-advancer** → a competing seal → a **spine fork** → `disputed`,
independent of any walk bound — inv 13/17.)*

**S3 — no stale-authority revival.** Root-condemnation reaches no *live* state — it **marks a subtree
dead**, never extends or revives an event. There is **no below-seal archival operation**, so the
below-seal-reach carve-out the prior draft worried about **does not exist**. The seal-cap stays
unconditional.

**S4 — bounded fork (depth *and* breadth).** The forked region is **bounded on both axes**. **Depth** ≤ 64
events past the last seal per lineage (the seal-advance cap — a deeper event must author a seal-advancer,
privileged → `disputed`). **Breadth** is bounded by **retention**: nodes keep **≥ 2 competing events per position** as evidence and
drop the rest (the content analog of inv 17's privileged ≥ 2-per-spine-position — "two prove the fork, then
stop"), so the *queryable* set is bounded and there is no query DoS. The **one-content-sibling witnessing
rule** is the *kind-aware layer* on top (federation §1e): a witness signs the **first** structurally-valid
content sibling at a position and **declines every later one** — while **privileged siblings are witnessed
up to two per position** (two both-witnessed siblings are the `disputed` proof — dispute evidence, spine
rule, inv 17; further spray is declined + droppable). The **single `Rec`/`Rpr` repair** that lands on a
content-only divergence is simply the first privileged sibling at that position (a *second* competing
repair is the proving pair `{Rec, Rec}`/`{Rpr, Rpr}` → `disputed`; at most
one repair lands on a content-only divergence). With the majority floor this bounds **co-witnessed content
breadth to ≤ 1 absent fork-cost byzantine witnesses**; arrival order decides only *which* sibling is the
witnessed one — the *bound* rests on **retention + kind-awareness**, arrival-independent
(cold F1). A signing-key (tier-1) re-forker can *author* more content siblings, but they sit beyond the
retained ≥ 2 → droppable + declined. Missed siblings beyond the retained set are **seal-cap-inert**
(the repair doesn't need them). Every dead event is
non-canonical and never flips a reading, and the depth-cap forces the seal-advancer that turns the fork
terminal (a spine fork → `disputed`, independent of any walk bound). A **privileged** event on a dead
branch (needs the reserve, tier-2) → `disputed` regardless (S2 / the D3 precedence) — the
terminal-compromise case, not a new attack.

## Cross-layer (SEL ↔ owner IEL)

A SEL's events are anchored to its **owner IEL** (each content event rides an IEL `Ixn` via
`manifest.anchors`; kind-strict, inv 4). The owner IEL is therefore the SEL's **clock**, and two rules —
both readable by walking the IEL anchors — close the cross-layer case with no SEL-local divergence
machinery:

- **Anchor-monotonicity.** An IEL event's SEL anchor is valid **only if the anchored event extends that
  SEL's latest IEL-anchored tip** — the tip computed over the **canonical (retained) IEL walk** (under a
  repaired fork, read from the retained branch, not a dead one). The check runs at **SEL-validation**, over
  the anchors a node can **attribute** (it holds the SEL bodies it validates); the anchor SAID is *opaque*
  (it does not invert to a prefix/serial — inv 16), so an anchor whose body a node does **not** hold is
  **skipped, not blocking** — *skip-unattributable*, else a withheld / lost / private body would wedge the
  SEL forever (the IEL is linear, no `Rpr` to ride). A SEL event that re-anchors an **already-anchored**
  serial is **malformed → inert** (an inert anchor never advances the SEL's tip; the carrying IEL event
  stays valid, so this never contaminates the IEL). So a node extends each SEL it can attribute correctly;
  an unattributable anchor resolves once its body propagates (the residual below).
- **Cross-layer deadness-descends.** A SEL event whose anchoring IEL event is **dead** (condemned by the
  `fork` root, or below-seal-inert) is itself dead — deadness crosses the anchor edge, not just
  `previous`-linkage.

**Theorem — a valid SEL fork implies an IEL fork beneath it.** For two SEL events to be *valid* at one
serial, each must extend the SEL's latest IEL-anchored tip when its anchor commits; on a *linear* IEL the
later anchor sees the earlier event as the tip, so a same-serial sibling is inert (anchor-monotonicity).
Two *valid* same-serial SEL events therefore force their anchors to be IEL siblings → an IEL fork. **So a
SEL never forks under a linear IEL; every genuine SEL fork rides an IEL fork,** resolved by one IEL `Rpr`
that condemns the losing IEL branch (its SEL events die by descent) and cascade-anchors the SEL `Rpr` for
the retained branch (kind-strict, IEL-first). There is **no unrepairable SEL-under-linear-IEL deadlock** —
skip-unattributable prevents the wedge, and in the **resolved state** (once bodies propagate) two *valid*
same-serial siblings still force an IEL fork. cold F1's deadlock assumed an unattributable anchor
*blocks*; it does not — and the anchor SAID's opacity (why attribution needs the body) causes only a
transient split, a residual, not a deadlock (below).

**Recoverability — a signing-key (tier-1) compromise is fully deadenable.** A T1 adversary holds no
reserve → can author **no privileged event** (no `Rot`/`Rev`/`Dth`/`Trm`/`Rpr`). If `t_use ≥ 2` a lone key is
inert (can't reach threshold) — nothing reaches the identity. If `t_use = 1` it can fork/spew content and
anchor spurious SEL content (it **cannot** author a SEL `Trm` — that needs a `Rev`/`Dth`, privileged) — but one
recovery `Rpr` (T3, from the reserve-holder) attaches at the last good event and archives the adversary's
whole tail: **permitted because no privileged event sits in the tail** (they can't author one) → every
adversary IEL event dead, every anchored SEL event dead by descent, no reincept. The only thing that
forces reincept instead of clean deadening is a **privileged event in the tail** — which requires the
reserve. So cross-layer safety *and* recoverability both reduce to the tier rule: the reserve defends
everything permanent; a signing-key compromise makes only **deadenable content**. **What remains of the
cross-layer question is a benign owner blunder** (two of the owner's own devices racing) — which
anchor-monotonicity renders **inert**, not even a fork; the operator answer is the SEL twin of content-rail
serialization (area-iel §5). *(This resolves cold F1's **deadlock** (skip-unattributable prevents the wedge) and its **safety** (leg c —
content-only). A **transient withheld-body split** remains — a node lacking an anchored body reads a later
sibling *valid*, a node holding it reads *inert*; auto-resolved by IEL/seal order (the next `Fld` fixes it,
seal order overriding anchor order), fail-secure — a residual, not a deadlock. The proof's earlier framing
only handled *simultaneous* SEL+IEL divergence and wrongly asserted the linear case "resolves identically";
"no longer a residual" was over-strong — see Residuals.)*

## Convergence

Under eventual beacon delivery and `< threshold` byzantine, every honest node's known set → the true
competing set. Then:

- **all-content** → every node reads the retained chain as canonical; the named subtree dead by
  condemnation, every other branch inert by the seal-cap (its growth dead by descent — named-vs-unnamed
  converge identically, the single-`fork` collapse's verification); effective-SAID = the
  real retained tip on every node. **Converges to Active.** No stacking, no reincept.
- **one privileged branch, kept by its author** → Active once neutralized + beacon-confirmed (barring
  eclipse). A non-author's repair that would condemn the privileged branch is **rejected (S2), retained
  as a competing privileged branch, and counted** — retain-and-count is the only convergent semantics
  (dropping the rejected repair splits the reading permanently). So **any reserve-revealing repair against
  a fork that turns out to hold a privileged branch permanently terminalizes the prefix** → `disputed` —
  the right fail-secure outcome (you revealed T3 into a window that turns out disputed; `reconciliation.md` Matrix 1
  already reads rejected → `disputed`), and it must be stated, not left readable as consequence-free.
- **≥ 2 privileged** (including a beacon-late privileged branch) → **`disputed`** everywhere
  (FORCE-by-provenance once a node holds ≥ 2; via receipt→fetch otherwise); effective-SAID =
  the real digest over the **live tips** (here the canonical tip + the competing privileged tips, all unresolved —
  live-tips, §1e) — all nodes converge on it once the branches propagate.

**Termination (cold F3, corrected).** The forked chain is **depth-capped at 64** — that is the bound, not
"the second `Rec` is the last." One repair condemns the whole current fork (roots + subtrees,
growth-proof within the depth-cap); the KEL `Rec`'s key-rotation / IEL `Rpr`'s cut then closes the
culprit's ability to mint a *new* fork. So a sustained adversarial re-forker terminates in (fork windows)
× (neutralization propagation); a benign gossip-lag terminates on catch-up. **Content-rail serialization
is an operator precondition** of the benign bound (area-iel §5) — absent it, honest content can
self-cascade (liveness, not safety), exactly as governance/recovery serialization backs `{Evl, Evl}` /
`{Rpr, Rpr}`. On a **witnessed** chain the floor narrows even the self-cascade to stall/waste (a competing
content sibling never goes live — federation §1e); the discipline stays load-bearing for direct-mode/solo.

## Adversarial closure

- **T1 under-gather → reincept (the prior HOLD's counterexample) — CLOSED.** A missed content branch has
  its first event locked below the seal (or, if named, is condemned by root) **and everything built on it
  dead by descent**; the node **accepts** the repair rather than freezing, so the honest all-content case
  converges to Active. No `{Rec, Rec}`, no reincept. The triple-node `{R, B, C}` case: the node holding
  the missed `C` accepts the repair, `C`'s first event locks below the seal and its growth is dead by
  descent → inert → Active, converging with the node that never saw `C`.
- **Withhold a key-change until the seal — CLOSED.** A late privileged branch is not inert (S2) → flips
  a *privileged-provisional* reading to `disputed`; no loss-of-trust decision treated the
  pre-neutralization repair as privileged-final, so nothing final is overturned. Residual: an
  *unwitnessed* branch under eclipse — the pre-existing detection residual (inv 8), fail-secure.
- **Condemn the retained branch (censorship) — CLOSED by S1.** A `fork` root on the retained chain (or
  `v_{d-1}`), tested over the **full-span** walk (F4), is rejected.
- **Grow a dead branch without bound — CLOSED by S4.** Depth-capped (growth past it forces a privileged
  seal-advancer → `disputed`); breadth bounded by retention (≥ 2 per position) + the one-content-sibling
  rule. Extra authored siblings are declined + droppable — the retained fork is bounded on both axes.
- **Signing-key (T1) compromise forks the SEL — CLOSED by §Cross-layer.** All content; one recovery `Rpr`
  deadens the whole tail (no privileged event in it), SEL events die by descent. Fully recoverable.

## Residuals (stated, fail-secure)

- **Eclipse / unwitnessed-branch residual** (inv 8): detection is eventual; a reader eclipsed from a
  branch sees the true reading later. Privileged-completeness fails-secure in that window. Pre-existing.
- **IEL multi-compromise past the evict-one margin** (inv 12): the evicting cut can't be authorized →
  reincept, not cut. Finite, but the lever is reincept.
- **Historical rotation-preimage compromise** (D1): an old reserve can mint a privileged event on a dead /
  below-seal lineage years after beacon confirmation → flips the read to `disputed` (fail-secure — nothing
  is un-archived; the prefix terminalizes). Not an eclipse (the branch did not exist at confirmation).

- **Withheld / lost SEL body** (cross-layer, cold F2): an anchored-but-unheld SEL body makes a later
  sibling read *valid* on nodes lacking it and *inert* on nodes holding it — a transient cross-node split,
  auto-resolved by IEL/seal order (the next `Fld`), fail-secure. Skip-unattributable keeps it a residual,
  not a wedge (§Cross-layer).

*(The cross-layer **deadlock** cold F1 feared does not exist — §Cross-layer; only the transient split above remains.)*

## Where it encodes

- **`kel/reconciliation.md`** — a fourth matrix (the dual): the model, the completeness matrix, the two
  guards, convergence, termination = the depth-cap. Effective-SAID table gains the content-final /
  privileged-final / disputed split.
- **`kel/merge.md`** — (a) `fork` names **one root**; the discriminator condemns its subtree
  (walk descendants), rejecting a root on the retained chain (S1, **full-span** membership — F4) or a
  subtree with a privileged event (S2 → `disputed`); every unnamed competing branch closes below the seal
  + by descent. (b) An unnamed-content repair is
  **accepted** (unnamed content inerts below the seal, growth dead by descent), not frozen. (c) The dead
  fork is bounded in *depth* by the seal-cap.
- **`sel/` + `iel/` anchor-validation doctrine** — **anchor-monotonicity** (a SEL event must extend its
  SEL's latest IEL-anchored tip; a re-anchor is inert, back-checked at SEL-validation, the IEL event stays
  valid) and **cross-layer deadness-descends** (a SEL event on a dead IEL anchor is dead).
- **inv 4 / inv 13 / inv 17** — updated: `fork` = one root + anchor-monotonicity (inv 4); the root-pointing
  F4 rule + deadness-descends (same-chain + cross-layer) + the depth-cap + the content-vs-key-change
  below-seal qualifier (inv 13); root-condemnation + the depth-cap (inv 17).
- **Stale-span inventory (F7 + cold F4 — overwrite on the encode; the tip/tail vocabulary is broader than
  F7 first listed):** `merge.md` — the re-freeze / "a second repair is required" / "stays frozen / archived
  **tip**" spans (~311-326) **and every `forks`-holds-*tails* / tip-walking span** (the discriminator
  narrative ~34 / ~148-161 / step 7); `reconciliation.md:326-327` (walk-the-tip-back) **and its invariant-3
  tail framing (~49-52)**; the `area-*` "tips" residue. All superseded by **roots** (a root condemns its
  subtree) + descent + accept-unnamed-content — a *partial* encode that leaves roots and tails
  side-by-side is self-contradictory, so the sweep must be complete. **The 2026-07-02 layer has since
  LANDED (the convergence encode, 2026-07-03):** `forks` (list) → `fork` (single root) across the landed
  role grids + repair doctrine, and the majority-floor reframe (prevention for witnessed content —
  federation §1e) are now in the landed KEL docs + `protocol-doctrine.md` §Federation Convergence — grep
  the content, the old `:871-890` / `:770-776` line refs are stale.

The whole repair-completeness question reduces to **condemn losing subtrees by root + deadness-descends
(same-chain + cross-layer) + anchor-monotonicity + two guards on condemnation**, sitting on machinery that
was already proven — which is why the prior draft's stacking / valid-pointer set / carve-out / settle-out
all drop out.
