# Fable design review — 2026-07-21, round 2 — resolution

Companion to [`fable-max-design-review_2026-07-21_2.md`](fable-max-design-review_2026-07-21_2.md).
It records what we did about each finding — what changed, where, and why. It was written after
working the findings through, so it reflects the landed state, and it is honest that the two serious
findings existed because round 1's sweep was **incomplete**, not because the design was unsettled.

## The headline: round 1's Model-I sweep was incomplete, and it reached the canon

Round 1 chose **Model I** — a content event beside a seal is buried, so the chain reads **Active**,
whichever order the two arrived in — and claimed to have swept it everywhere. It had not. The
round-1 grep searched for one phrasing (`≤ 1 sealed = Forked`) while the live stale text used a
dozen others (`≤ 1 sealed branch past it`, `at most one branch carries a sealed event`,
`one or fewer → Forked`, `reads Forked node-agnostically`, `Forked-frozen`, `forked (≤ 1 sealed)`,
`≥ 1 sealed branch past it` in the effective-SAID sections, …). So a superseded "one sealed branch
is still Forked" model survived in about a dozen places — **including inside both correctness-proof
documents**, which asserted two different states for the same input. This is Finding 1.1, and it is
real.

It also reached the **canon**. The canon was internally split: `vdti-area-kel.md` and
`vdti-invariants.md` were already Model I and correct, but `vdti-area-iel.md` still said "**M ≤ 1 =
Forked** … node-agnostically it reads Forked until a second sealed branch lands" and
`vdti-area-vdtid-services.md`'s effective-SAID still treated "≥ 1 sealed branch" as no-single-tip.
Those two were the stragglers; the fix was to bring them to the Model I already stated in
`vdti-area-kel.md`, which is the direction Jason has stated repeatedly ("forked is impossible; it's
Active if only one sealing event exists").

**The precise reading, now stated the same way in every design doc and every canon file:** the state
is decided by the count of **accepted sealed branches** past the fork — **0 → Forked** (a
content-only fork, recoverable; the effective-SAID synthetic applies), **1 → Active** (the single
accepted seal buries the content sibling — the content can't land if the seal is first, and the seal
buries it if the seal is second, so it reads Active either way; a terminal `Trm` reads Terminated
instead; the real tip's SAID), **≥ 2 → Disputed** (terminal, reincept; the synthetic). A single
accepted seal you did **not** author reads Active node-agnostically (a clean sealed tip) yet still
forces **your** reincept — an operational consequence, not a chain state.

**Sites swept (1.1):** `protocol-doctrine.md` (the Forked-state definition, the effective-SAID
no-single-tip case, the reincept-conditions paragraph); `system-thesis.md` (the
federation-convergence tree — the `N = 1` mixed-fork arm now routes to **Active**, a new node);
`kel/log.md`, `kel/merge.md` (routing-flowchart node + the transitions-table Forked row),
`kel/reconciliation.md` (the effective-SAID sections, the transitions table, and
**completeness-matrix row 5**, rewritten from the "Forked-frozen" state the proof says cannot
exist); `iel/log.md`, `iel/verification.md`, `iel/reconciliation.md` (the transitions bullet, the
`{Rev, content}` cell, the effective-SAID sections, completeness-matrix row 5); the SEL
effective-SAID section; the glossary and system thesis were already correct. **Canon:**
`vdti-area-iel.md`, `vdti-area-vdtid-services.md`, and one straggler in `vdti-invariants.md`
("didn't author reads `forked`" → reads **Active**). A search for every stale phrasing now comes
back empty across both trees, and the reworked tree renders cleanly.

## 1.2 (no self-burial): deleted — you cannot guard against self-burial

The "no self-burial" admission guard — "reject a burying seal-advancer that siblings its own
retained chain" — was undecidable (authorship is not in chain data), vacuous (an event has one
`previous`, so a loser's subtree is structurally disjoint from the retained chain), or
recovery-breaking (read as "don't bury the canonical chain," it forbids the shed-the-tail and
ancestor-attach recoveries the design explicitly permits). Its one concrete application
(`sel/reconciliation.md` Matrix 3) directly contradicted the Position-3 burial rule in the same
file. Per Jason ("we can't guard against self-burial, that's ridiculous") the guard is **deleted**
from all its sites — `protocol-doctrine.md` (the shape-validity gate line, the guard bullet, the
dropped-never-counted line), `kel/merge.md` + `kel/reconciliation.md`, `iel/merge.md` (numbered
rule 5) + `iel/reconciliation.md`, and the two canon sites (`vdti-invariants.md`,
`vdti-area-federation-witnessing.md`). The **real** guards do the work and stay: hard authorization
(the reserve signature / anchoring threshold), **no burying a sealed branch** (a witnessed sealed
event in a would-be-buried branch → Disputed), and the unconditional seal-cap. The one concrete
application (SEL Matrix 3) was reframed to the correct data-only reading: a `Sea` that would attach
below the resolved tip to bury an already-severed loser reaches only dead events, so it changes no
live state.

## 8.1 (MODEL.md): the core rule is content-vs-sealed, not single-key-vs-group

`MODEL.md`'s "core rule" drew the keep-both / take-first line at single-key versus group, and
claimed a single-key rotation conflict "must stay recoverable, not terminal" — which contradicts the
KEL brick analysis (a stolen signing key plus witness collusion _does_ terminalize a device chain).
The real line is **content versus a key change**: honest witnesses take the first and decline the
second for **every** event kind, so a second of _anything_ reaches backing only under witness
corruption; two backed **key changes** (single-key `{rotate, rotate}` included) are Disputed and
terminal _whoever_ could have signed them. The section was rewritten to that rule, keeping the
single-key-versus-group contrast only as what a dispute **proves** (the forensics — who to evict
versus who to walk away from). The "What disputed means" section's companion error ("on a group
decision the design records both on purpose") was corrected to the uniform first-seen framing.

## Every finding, and what we did

| #   | Grade    | Disposition                                                                                                                                                                                                                                                  |
| --- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1.1 | serious  | **Folded** — completed the Model-I sweep across ~10 design files + 3 canon files (`vdti-area-iel`, `vdti-area-vdtid-services`, `vdti-invariants`); residual grep empty; tree re-rendered.                                                                    |
| 1.2 | serious  | **Folded** — deleted the "no self-burial" guard from all 6 design sites + 2 canon sites; kept hard-auth / no-buried-rotation / seal-cap; reframed the SEL Matrix-3 application.                                                                              |
| 8.1 | moderate | **Folded** — rewrote `MODEL.md` §The core rule and §What disputed means to content-vs-sealed; the single-key/group split kept only as forensics.                                                                                                             |
| 1.3 | minor    | **Folded** — the doctrine's authority floor `≥ 2` now qualified "(for `\|roster\| ≥ 2`; a singleton sets all thresholds to 1)".                                                                                                                              |
| 1.4 | minor    | **Folded** — the doctrine's Part 3 table of contents now lists "Caching and continuation".                                                                                                                                                                   |
| 2.1 | minor    | **Folded** — `sad.md` now names the shared-document constitution `V0` alongside chain inceptions as the prefix-deriving SADs.                                                                                                                                |
| 2.2 | minor    | **Folded** — `shapes.md`'s witness-config bound now says `\|roster\|` is the **federation's** witness roster, not the identity's own.                                                                                                                        |
| 3.1 | minor    | **Folded** into 1.1 — `kel/log.md`'s second (stale) Forked definition swept with the rest.                                                                                                                                                                   |
| 3.2 | minor    | **Folded** — `iel/events.md`'s "≥ tier-2" corrected to "tier-2" (there is no tier above 2).                                                                                                                                                                  |
| 4.1 | minor    | **Folded** — `witnessing.md`'s receipt **record** fields renamed to `camelCase` (`chainPrefix` / `eventSaid` / `eventSerial` / `witnessPrefix`) to match `shapes.md` (JSON = camelCase); the `select()` pseudocode and its call-args stay snake_case (Rust). |
| 5.1 | minor    | **Folded** — `policy.md`'s "evaluates identically everywhere" softened to the true property: a shared policy **never wrongly permits** (budget-exhaustion denies, fail-secure).                                                                              |
| 8.2 | minor    | **Folded** — `kinds.md` (the canonical kind list) gained rows for `vdti/cred/v1/schemas/terms` and `vdti/cred/v1/schemas/issuers`.                                                                                                                           |

## Verification

`make all` passes — terminology 0, cross-references 0 errors, prettier clean (89 files after this
log is added). A search for the round-1 stale phrasings (`≤ 1 sealed`, `at most one branch`,
`Forked-frozen`, `reads Forked node-agnostically`, `≥ 1 sealed branch past it`, `self-burial`) comes
back empty across both the design docs and the canon. The one modified mermaid diagram
(`system-thesis.md`'s convergence tree) was rendered with `mmdc` and its geometry inspected.
