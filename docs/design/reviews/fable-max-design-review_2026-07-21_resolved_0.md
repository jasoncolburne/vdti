# Fable design review — 2026-07-21 — resolution

Companion to [`fable-max-design-review_2026-07-21_0.md`](fable-max-design-review_2026-07-21_0.md).
It records what we did about each finding — what changed, where, and why — plus the two items (F3,
Q4) that needed a design call, since decided and folded. It was written after working the findings
all the way through, so it reflects the corrected understanding rather than the first read.

## The headline (F2): the finding was right, and it reached further than a wording fix

F2 said the doctrine's divergence terminology was too absolute: it claimed the **only**
irrecoverable dispute is two competing seals at the **same position**, provable as a **witness
double-sign**, and that a dispute can never form across positions. The reconciliation documents' own
retain-and-count rule contradicts that — it produces disputes whose two accepted seals sit at
**different** positions.

The first analysis pushed back on the finding, on the reasoning that any fork of two accepted
branches must trace to a witness signing two competing events at one position (a majority-threshold
overlap argument). That reasoning was wrong, and re-reading the witnessing rules settled it:
witnessing is **kind-scoped** — an honest witness legitimately signs one _content_ sibling **and**
one _sealed_ sibling at a position (`witnessing.md`, "the permitted cross-tier co-sign"). So a
**mixed** fork — a content event and a sealed event at the same position — forms with **every
witness honest**. When the content-led branch then seals, you have two accepted sealed branches at
different serials, and **no witness ever double-signed**. The proof of misbehavior there is
author-side: the author revealed its one rotation reserve on two branches (an "author reserve
double-reveal").

So the corrected model, now written throughout the design, is:

- **Disputed = two or more accepted sealed branches _past the fork_** (not "at the same serial").
- A dispute **always** carries a provable misbehavior, in one of two forms the data tells apart:
  - **a witness double-sign** — when the competing seals are siblings at one serial under one
    federation (they share a selected witness set, so both accepted means a witness signed both); or
  - **an author reserve double-reveal** — when they don't share a set, so every witness is honest.
    This happens two ways: **across serials** (a content-led branch that seals, meeting a burying
    seal that can't drop it) and **across federations** (two rebinds declaring different
    federations, whose witness sets are disjoint).
- The attribution is a **computed property of the verification token**, not a fixed claim — a
  verifier reads which proof a given dispute carries. `confirmed_*` means _proven from the evidence
  held_, never _proven absent_; the verdict is Disputed either way (the attribution only decides
  forensics: a witness double-sign names colluders to evict; author equivocation names no witness,
  so reincept and move on).

Safety was never in question — every path still ends Disputed → reincept, fail-secure, and nothing
buried is ever resurrected. What was wrong was the case enumeration, the attribution, and one
boundary definition (below). We also worked the ripples and confirmed they hold: the single-page
fork bound still fits (both branches stay within the unsealed-run cap), and retention still keeps
both seals (the fork evidence at the fork position plus keep-all-data on each sealed branch).

### The one soundness item inside F2: the "clean seal" boundary

F2's third point was not wording. The trust boundary — the line below which history is final — was
defined as "the highest seal with no competing sibling at its own position." In the cross-position
geometry a branch's seal above the fork has no sibling at its own serial, so it read "clean," and
the boundary climbed **above** the fork. That would wrongly treat contested anchors as final. Fixed:
the boundary is the **divergence position** (the single freeze point), never a lone seal above it —
which is what the anchor rule already used ("a tier-2 anchor at-or-beyond the divergent serial
drops"). The clean-seal definition now matches that.

### Where F2 landed (every site that restated the old claim)

The correction propagated to every place the old "only at one position / witness double-sign" claim
appeared:

- **Concept map:** `protocol-doctrine.md` (the Disputed terminology, the pre-seal-verifiability
  passage + the clean-seal definition, the kind-scoped-witnessing passage, the effective-SAID
  passage, and the new "misbehavior proof is computed" paragraph),
  `substrate/federation/witnessing.md` (the "dispute cannot form across positions" and "only
  reachable dispute" claims), `system-thesis.md` (the convergence one-liner, the decision-tree
  label, and the prose), and `glossary.md`.
- **Per-primitive proofs:** the `kel/`, `iel/`, and `sel/` reconciliation, verification, merge, log,
  and compromise documents — the Disputed-count locative ("at the last seal" → "past the fork"), the
  Matrix 3 race matrices (scoped to the same-serial race, with a pointer to the honest-witness
  cases), the Matrix 4 retain-and-count rows (attribution widened), and `kel/compromise.md`'s
  live-tip section (scoped to the same-serial killswitch, with the reserve-equivocation path named).
- **Supporting:** `event-shape.md`, the design `README.md`, and one residuals line.

The IEL documents already carried the more careful "quorum subverted **or** witnesses colluded"
phrasing the review praised; that phrasing already covers the author-equivocation case (for an IEL,
member equivocation _is_ quorum subversion), so those needed only the locative fix.

## The other findings

- **F4 — cross-federation rebind dispute (companion to F2).** Confirmed against `witnessing.md`: the
  "competing events route to the same selected set" claim holds only for events that **inherit**
  their pin; a rebind **declares** its own pin and selects over a different roster, so two rebinds
  to different federations select **disjoint** witness sets and both accept honestly. Named the
  exception in the deterministic-selection section and added the race (with its author-side proof)
  to the rebinding section.
- **F5 — convergence needs a shared-trust-set qualifier.** Added it where the F4 race is described:
  convergence holds among verifiers that share a trusted-federation set, and a verifier trusting
  only one side of a rebind race reads only that side accepted.
- **F6 — currency gate parenthetical.** The gate "fires on a cut" now reads "fires on any membership
  change — an add or a cut — not on a pure rotation," since an add also changes membership.
- **F7 — policy no-signer-reuse implies a search.** Added a sentence in `policy.md`: where branches
  are themselves quorum sub-policies, satisfaction is **existential** (satisfied iff some assignment
  of signers reuses none — a set-packing check); a naive greedy pass is non-conforming, and the
  search is bounded by the verifier's work budget. Noted it is each relying party's own decision but
  that shared policies must evaluate identically.
- **F1 — custody read-gate framing.** Added a sentence to the adversarial framing: the `readers`
  gate is **operational access control, not confidentiality** — once plaintext bytes escape they are
  readable, and secrecy against a leaky replica or hostile holder needs encryption, matching the
  residuals catalog's honest statement.
- **Q1 — "the earlier seal buries."** Folded into the F2 rewrite: the content-vs-content
  different-serial case is now pinned to **first-seen / acceptance order**, not an earlier-by-serial
  tiebreak (which no enforcement rule implements).
- **Q2 — the rebind attribution.** Resolved as F4.
- **Q3 — one data-log event per anchoring identity event.** The review confirmed this is genuinely
  closed (the data log is its own witnessed chain); no change.

## Resolved after a decision (F3, Q4)

Both were design questions, not wording; both were decided and are now encoded.

- **F3 — does accepting a data-log (SEL) event wait on its anchoring identity-log (IEL) event being
  accepted?** `sel/log.md` says the witness "validates" the batched owner-IEL anchor "as part of its
  ordinary job," which is not pinned to either "checks structurally" or "requires the anchor to be
  witnessed at threshold." This decides whether one reconciliation row (a severance downgrading a
  Disputed) is reachable at all. The fail-secure reading is that SEL acceptance **gates on the IEL
  anchor being accepted** — the SEL draws its authorization from that anchor, and an un-accepted
  anchor is not trusted authorization; under that reading the row is unreachable-by-construction.
  **Decided: yes — now encoded** in `sel/log.md` (the acceptance gate) and `sel/reconciliation.md`
  (the Matrix 2 row flips to **unreachable by construction** — an accepted sealed branch's IEL
  anchor is itself accepted and never buried).
- **Q4 — a device conscripted into a hostile roster.** A device consents to a roster via its own
  tier-1 act, and there is no unilateral "member resigns"; a signing-key-only-compromised device can
  be named in a hostile identity's roster and cannot remove itself. The review's own analysis is
  that the exposure is **correlation only** (its prefix appears in that roster's delta), not any
  authority the hostile identity gains — the roster grants it nothing over the device's keys.
  **Decided: by design** — roster membership is purely the identity's governance, and the only way
  the key acts under a hostile identity is if the attacker holds it (a device compromise, resolved
  by rotate-and-continue or cut/reincept). **Now encoded**: `iel/events.md` states it beside the
  added-member-consent rule, and `residuals.md` carries it as an inherent trade-off (Privacy,
  correlation-only).

## Where it landed

All tracked design docs pass the full gate: `make all` →
`checked 85 | OK: 1320 | errors: 0 | forward-refs: 8`, prettier clean. Twenty-two design docs
changed (plus this resolution log); no mechanism changed, only the divergence concept map, its
restatements, the trust-boundary definition, and the F1/F3/F4/F5/F6/F7/Q4 folds above.
