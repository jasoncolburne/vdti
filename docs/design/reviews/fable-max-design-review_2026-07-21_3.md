# Fable (max) design review — 2026-07-21, pass 3 (cold)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_3.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. ignore the existing files in docs/design/review.

## Scope and method

This is a cold review: it reads the design surface (`docs/design/`) on its own terms, in the
prescribed reading order, and judges what the documents actually say — not what an earlier session
remembers them saying. The earlier review files in `docs/design/reviews/` were deliberately not
read, so this pass is decorrelated from them. The design notes under `docs/canon/` were also not
read: a cold pass checks that the published design stands on its own.

Two axes, as requested:

- **Correctness / soundness** — do the stated rules actually deliver the properties the documents
  claim? Where a document argues "this cannot happen," does the argument hold against an adversary?
- **Consistency** — do the documents agree with each other? Same rule stated twice, stated the same
  way; a term defined in one place used the same way everywhere else.

Each finding says where it lives (file and section), what the documents say, why it is a problem,
and how severe it is:

- **Critical** — a hole in a security argument, or two rules that cannot both be true.
- **Major** — a real gap or contradiction that would mislead an implementer, but with a plausible
  repair that does not reshape the design.
- **Minor** — a local inconsistency, an overstated claim, or an ambiguity with a clear best reading.
- **Note** — an observation worth recording; no change strictly required.

The review is grouped by layer, following the reading order, with cross-document consistency
findings gathered at the end.

## Verdict

The design surface is in strong shape. This pass read all forty-one documents in the prescribed
order and checked the load-bearing arguments directly rather than taking the docs' own summaries on
faith: the substrate's canonicalization and two-hash derivation arguments, the seal/burial/dispute
machinery and its enumeration matrices, the witnessing floor arithmetic and the witnessed-time
construction, the policy layer's anchoring-position and composition rules, and the feature layer's
acceptance conjunctions all hold as written, and the corpus is honest about its residuals to an
unusual degree — the residuals catalog's scoring is arithmetically exact, and the feature docs'
residual lists match it entry for entry.

Three findings rise above local polish:

- **B2 (Critical)** — the two-accepted-seals-at-different-serials case has three load-bearing texts
  giving three different verdicts, the correctness-proof matrices never enumerate it, and the state
  is reachable inside the same collusion residual the Disputed machinery exists for. One rule (count
  accepted sealed branches past the fork wherever their seals sit — Disputed) should be chosen,
  stated once, and conformed everywhere.
- **B1 (Major)** — whether a witness-declined, never-accepted sibling can make a chain read Forked
  is answered both ways across the corpus; the accepted-only reading is clearly intended (the merge
  docs and the SEL docs state it), and the handful of contrary sentences should be conformed before
  an implementer builds the wrong verifier.
- **D1 (Major)** — one sentence tells an owner they can counter-seal a takeover into a dispute; the
  rest of the corpus proves they cannot. It should be inverted.

Everything else found is minor consistency drift of the kind a corpus this size accumulates: an
undeclared-but-real exception to the kind-strict anchor rule (D2), a catalogue that trails its
consumers in four small ways (A3, E2, H2, I2), one ambiguous composition rule (G2), one missing
config attribution (F3), and two orientation sentences that overclaim against the corpus's own
honest limits (J2). None of these reshapes the design; all are fixable with sentences, not
mechanisms. On correctness and consistency — the two axes this review was asked to judge — the
design earns trust: its hard arguments are right, its enumerations are nearly complete, and the gaps
found are at the seams the documents themselves flag as densest.

## Findings

Grouped by layer, in reading order. Findings that span layers are gathered in the cross-document
group at the end. A finding marked "(re-test at …)" was logged when first encountered and re-checked
against the later doc named; the final wording reflects both.

### Group A — Orientation and the data substrate (README, thesis, glossary, SAD group)

**A1 — Note. The foundations are internally consistent and the substrate arguments hold.** The SAD /
SAID layer was checked for the properties it claims: the two-hash inception derivation (prefix from
placeholder-both, SAID from placeholder-said-only) does deliver "no logged SAID reveals the chain's
lookup key," and the claimed independence holds — neither value is computable from the other without
inverting the hash. The two canonical-form rules (nested records reduced to their identifiers before
hashing; inline children verified before substitution) close the lying-embedded-child gap the second
rule describes, and the compaction doc's invariant is a faithful corollary. The sorted-and-distinct
rule for set-valued lists is stated in both `said.md` and `custody.md` consistently. No
contradiction was found inside the substrate group.

**A2 — Minor (consistency). The sort order for "strictly ascending" lists is never pinned.**
`said.md` §Adversarial framing and `custody.md` both require set-valued lists (e.g. the `readers`
list) to be carried "strictly ascending (sorted **and** distinct)," and a verifier must reject an
out-of-order list as non-canonical. No document says what ordering "ascending" means — bytewise over
the qualified text encoding, or over the raw digest bytes, which do not agree in general. Both
producer and verifier must agree exactly for the one-SAID-per-set property to hold. The encoding
library is listed as forthcoming and is the natural home, but the doctrine-level statement should
say the collation is deferred there; today the rule is stated as complete while missing the one
parameter that makes it checkable.

**A3 — Minor (consistency). The catalogue's "remaining roles are inline" sentence contradicts the
shapes doc.** `kinds.md` §SAD kinds says: "The remaining manifest roles — `anchors`, `delegates`,
`payload`, `kills`, and the scalar `clock` — are carried **inline** in the manifest SAD, so they are
not separate SADs and have no kind of their own." `shapes.md` §Commitment SADs adds: "the `bound`
and `grant` roles each name a SAD of their own (the gated rescind-doc, and the grant value)." So the
kinds catalogue's "remaining" enumeration silently omits two roles that are neither inline nor in
its role-SAD table — and the `bound` role's target (the rescind-doc) has no kind anywhere in the
catalogue (the grant values do, under `vdti/sel/v1/grants/*`). A reader using `kinds.md` as "the
canonical enumeration of every SAD kind" (its own claim) cannot place the rescind-doc. (Re-test at
`event-shape.md`: its role table confirms `grant` and `bound` are SAID-valued roles, so the
`kinds.md` sentence is the odd one out.)

**A4 — Note (soundness, positive). The residuals catalog's scoring is arithmetically consistent.**
Every row in both ranked tables was recomputed: Severity × Exploitability equals the stated Risk
number and band in all 27 scored rows, and the headline claims ("nothing irreducible reaches High or
Critical"; "every Critical is an avoidable operator opt-out") match the tables. This is worth
recording because the tables are the document's argument.

### Group B — Cross-cutting doctrine (`protocol-doctrine.md`, `residuals.md`, `monitoring.md`)

**B1 — Major (consistency / soundness). Two adjacent doctrine passages disagree about whether a
declined, sub-threshold sibling makes a chain read Forked.** The verdict machinery elsewhere is
explicit that verdicts read against **accepted** events only:

- Glossary, "deferred-pending": a structurally-valid event below the witness threshold "is retained
  and gossiped, does **not** advance the tip or seal, and is **never counted** toward a verdict."
- Glossary, "witnessed vs accepted": "the Active / `Disputed` boundary and the effective-SAID read
  against **accepted**, never merely witnessed."
- `protocol-doctrine.md` §Query-scoping: the audit query may surface sub-threshold events "but the
  walk **ignores** anything not accepted, so surfacing them cannot skew a verdict."

Against that, the content-signal passage in §Federation convergence says: "A **selected witness**
(which holds the sub-threshold sibling on the sub-gossip mesh) fetches it and its data-local walk
reads _forked_; a **non-witness** holds only witnessed-in-full events…the content fork is
**prevented** and reads **Active**." Taken literally, a witness's walk counts a never-accepted,
witness-declined sibling toward the Forked verdict — the exact thing the other three passages
forbid. The consequences of the literal reading are real, not cosmetic: the witness would freeze
origination and compute a `forked` synthetic effective-SAID while every non-witness computes the
real tip SAID, and the disagreement would drive an anti-entropy fetch that can never reconcile,
because query-scoping withholds the declined sibling from the non-witness by design — a permanent
false alarm between honest nodes.

The KEL group's own texts show which reading is intended, and repeat the loose one anyway:

- `kel/merge.md` is unambiguous for accepted-only: "Acceptance precedes the outcome…A
  structurally-valid submission that has not yet reached threshold is **neither a transition nor a
  rejection** — it is held deferred-pending…not counted toward a verdict," and its outcome table
  routes a second content sibling to **Ignored** (declined), with Forked reserved for "the residual"
  where both siblings are witnessed.
- `kel/verification.md` repeats the loose sense: "**Receipts tell a node it is _forked_**; only the
  data-local walk tells it _disputed_" — where the receipts in question are a **sub-threshold**
  competing set that, under the accepted-only rule, must not produce a Forked verdict at all (it is
  the token's minority-dissent forensic signal).
- The Terminology definition of Forked ("two **distinct content** events at one serial, with no
  accepted sealed branch past it") and its echoes in `kel/log.md` and `kel/reconciliation.md` never
  qualify the content siblings with "accepted," although the sealed side of the same definitions is
  carefully qualified. The `residuals.md` signing-key-forgery entry uses the same loose sense
  ("authoring at the owner's position is a **fork** the owner sees at once") for what the floor
  actually makes a declined-sibling stall.

The repair is small: define Forked over **accepted** content siblings (the witness-collusion
residual is the only way two content siblings are both accepted), and name the witness's view of a
declined sibling as the forensic signal it is (minority dissent), never a verdict. As written, an
implementer following §Federation convergence and one following `kel/merge.md` build different
verifiers.

**B2 — Critical (soundness / consistency). Two accepted seals at different serials: three rules,
three verdicts, and the correctness-proof matrix never enumerates the case.** §Terminology's
Disputed entry works the cases: "a content fork whose branches seal at **different** serials is
**also recoverable** — the **earlier** seal buries the other branch from the fork…so that branch's
later seal lands on a buried chain and is dropped. The **only** irrecoverable case is **two seals at
the same serial**."

The state in question is reachable inside the design's own modeled residual. Take a content fork at
serial d where **both** content siblings were accepted — that requires a witness double-sign at d,
and it is exactly the residual the docs name as producing the Forked state ("the residual is a
witness compromise, where a content fork forms, reads Forked"). Branch A then seals at d+2 —
honestly witnessed, the first sealed sibling at its position. Under a partition, the witnesses
selected at d+5 who have not yet seen A's seal read branch B's lineage as alive (its root at d
carries threshold receipts), so they honestly accept B's seal at d+5. Every node eventually holds:
two accepted content siblings at d, an accepted seal on branch A at d+2, an accepted seal on branch
B at d+5. (On a KEL this additionally needs the thief to hold the reserve to seal branch B; on an
IEL it needs an overlapping-quorum double-deal — both inside the priced Disputed-class residual, the
same collusion bar the specified same-serial dispute requires.)

Three load-bearing texts then give three different verdicts on that one held set:

1. **Earlier seal wins** (§Terminology, quoted above): branch A stands; B's later seal "lands on a
   buried chain and is dropped" — the chain reads Active on A.
2. **Count the branches** (`kel/log.md` §Forked versus Disputed: "two or more branches each carry an
   accepted sealed event past the fork" → Disputed; `kel/reconciliation.md` invariant 4: "a fork
   with two or more witnessed sealed branches past it is Disputed"): both branches carry accepted
   seals past the fork — Disputed, reincept.
3. **Most-recent tracked seal** (§Forks are Seal-Bounded and `kel/log.md`: the seal is "the most
   recent seal-advancing event with no competing accepted **sealed sibling**"): neither seal has a
   same-position sealed sibling, so "most recent" selects B's seal at d+5 as the lock — A's seal
   then sits below the tracked seal, and the below-seal-straggler rule says it is dropped — the
   chain reads Active on B.

The argument that was supposed to make this unreachable — "you can't seal a buried chain: honest
witnesses, **having accepted the winner at the fork**, decline a dead lineage's descendants"
(§Pre-seal verifiability; `kel/reconciliation.md` §Safety) — presumes a **single** accepted winner
at the fork, which is precisely what the double-sign residual violates. The refined acceptance
definition ("an accepted sealed branch is one whose seal is witnessed at threshold **and** whose
lineage is accepted — a branch built on a first-seen loss…never counts") resolves the honest case
cleanly, because there the loser's lineage is sub-threshold and its seal never counts — but in the
both-accepted residual neither lineage lost first-seen, so it selects reading 2, while §Terminology
asserts reading 1 and the tracked-seal definition implies reading 3. `kel/reconciliation.md` — the
document whose stated purpose is exhaustive enumeration — pins its dispute cases to seal-siblings
**at one position** (Matrix 3's races extend one parent at one serial; Matrix 4's Disputed rows say
"at the last seal") and never enumerates the different-serial shape, so the proof does not
adjudicate it either.

The consequence of leaving this unresolved is verdict divergence between conforming implementations
in exactly the residual the Disputed machinery exists for: some verifiers would read Active-on-A,
some Active-on-B, some Disputed — a canonical-chain split, which is the failure class the whole
design exists to make impossible ("you never act on two disagreeing current values"). Reading 1 as a
rule also has a backdate smell the design closes everywhere else: it lets a later-minted,
lower-serial accepted seal flip an established chain, and "below the seal is dropped" cannot rescue
it because which seal is "the" seal is the very question. The resolution consistent with the rest of
the design is reading 2, fail-secure: **two or more accepted sealed branches past the fork —
wherever their seals sit — read Disputed**; restate §Terminology's working-cases sentence as the
honest-case description it actually is (the later seal is dead because its **lineage lost
first-seen**, not because it is later), qualify the tracked-seal definition with lineage-acceptance,
and add the different-serial row to `kel/reconciliation.md`'s matrix. No honest-path behavior
changes under that fix; what changes is that the priced residual gets one verdict instead of three.

**B3 — Minor (consistency). An unexplained second path to a terminal `{Evl, Evl}`.**
`system-thesis.md` §Operational hardening: "A `{Evl, Evl}` terminal (→ reincept) needs **witness
collusion** (a provable double-sign), not an honest race." `protocol-doctrine.md` §Divergence and
recovery: "two **accepted** `{Evl, Evl}` branches require witness collusion (a provable double-sign)
**or a genuine distinct-branch fork**." The second clause has no referent anywhere else: two `Evl`s
at one serial share their inherited federation pin, so they select the same witnesses and the
intersection must double-sign — collusion. The one genuinely disjoint-witness path the doctrine
names is the cross-federation rebind, which is a `{Wit, Wit}` pair, not `{Evl, Evl}`. Either the
clause means the different-serial case (which is B2's knot and should say so) or it is a leftover;
either way the two docs currently disagree about whether an honest path exists.

**B4 — Minor (consistency). "What an IEL `Ixn` anchors" over-narrows the v1 anchor rule.**
`protocol-doctrine.md` §Inception tiers: "the SEL's **serial-1 event (its v1)** is what an IEL `Ixn`
anchors." For a content SEL that is right, but the same doctrine's kind-strict matrix routes a
lookup SEL's v1 elsewhere: a value-bearing lookup's v1 is a `Gnt`, anchored by an `Ath`; a
revocation lookup's v1 is a `Trm`, anchored by a `Rev` or `Dth` (both stated in §Tiers and in the
same section's own closing sentences). The sentence reads as the general rule while holding only for
the content case. One word ("what an IEL event **of the matching kind** anchors") fixes it.

**B5 — Note (soundness, positive). The page-size arithmetic checks out.**
`MINIMUM_PAGE_SIZE = 129 = 2·MAXIMUM_UNSEALED_RUN + 1` was verified against the stated bound (64
non-sealing events per lineage): worst case is a fork immediately above the last seal, two disjoint
lineages of 64, plus the one burying seal-advancer on the winning lineage — 129 events, exactly one
page, with the prior seal itself as the page's anchor rather than a member. The federation
threshold-bound example (roster 4 → signers ≤ 3 → threshold 2 > 3/2, within
`min(|roster|−2, signers−1)` = 2) is likewise satisfiable as claimed, and the residuals catalog's
fork-cost algebra (`fork-cost + slack = threshold`) is correct.

**B6 — Note. Monitoring's soundness inherits B1.** `monitoring.md` reduces owner-side detection to
"fetch the effective SAID for your prefix and compare." That is sound exactly when every honest node
computes the same effective SAID for the same accepted state — which is what B1's literal reading
breaks (a witness node holding a declined sibling would answer with a `forked` synthetic while
others answer the real tip). Resolving B1 in the accepted-only direction makes monitoring's one-line
detector unambiguous; no change needed here beyond that.

### Group C — The KEL primitive (`log`, `events`, `verification`, `merge`, `compromise`, `reconciliation`)

**C1 — Note (soundness, positive). The KEL core arguments hold.** The pieces that carry the most
weight were each checked and are sound as written: the single-stream pre-rotation model (two live
keys; the revealed reserve becomes the signing key; the old signing key never a prerequisite for a
key change) is stated identically in `events.md`, `event-shape.md`, and the doctrine. The
spent-reserve boundary argument in `compromise.md` §The live-tip dispute — a competing seal at an
already-sealed position needs the **current signing key**, not the next reserve, so a late rival can
brick (with collusion) but never take over — is correct and carefully argued, including why the
brick is forced (a data rule for picking a winner is grindable; first-seen-per-observer breaks the
same-answer guarantee). The merge routing order's rationale (seal-cap before fork-detect so the
diagnostic names the cause, with the security outcome order-independent) is coherent, and the
seal-cap / kind-schema independence argument (a sibling-to-the-terminal versus a chain-from-it need
different rules) is a genuine two-mechanism necessity, correctly identified. The two recovery attach
shapes and the argument that the ancestor-extending shape is cross-node-validatable (the divergence
ancestor is byte-identical on every node) also hold.

**C2 — Minor (consistency). The reconciliation doc's honest-race framing contradicts the prevention
model it depends on.** `kel/reconciliation.md` edge case 2 opens: "Different `Ixn` events at the
same serial are submitted to different nodes (**federation race** or threshold compromise…). When
gossip syncs, **a fork forms**." Under the witnessing floor plus acceptance gating — stated in the
same corpus — an honest federation race cannot form a content fork: only one sibling reaches
threshold, the other is declined and stalls, and "no node advances to a sub-threshold event"
(`kel/verification.md` §Acceptance requires threshold). The depicted both-branches-held fork is
reachable only in the witness-compromise residual (or as a deliberately-over-general proof state).
The same framing shows up in Matrix 2's "Active (losing)" column, glossed as "submitted to that node
before the divergence was detected elsewhere" — under acceptance gating a node never holds a
sub-threshold branch as its Active chain, so that column too is residual-only. Proving convergence
from unreachable states is good defensive posture, but the prose presents them as ordinary races,
which contradicts the prevention claim and will mislead a reader about how often this machinery
runs. One clause naming the residual (or the deliberate over-generality) at each site fixes it.

**C3 — Minor (consistency). Small enumeration drift around which kinds resolve a fork and where a
key's validity window starts.** Two small slips, both with a clear correct reading elsewhere:

- `kel/log.md`'s Forked row and state diagram name the resolving move "(a `Rot` / `Wit`)", while the
  doctrine's §Terminology and `kel/merge.md` both include the terminal kind ("a `Rot` / `Wit` /
  `Trm` on the KEL" — a terminal on the winning tip buries the loser below its own seal and
  terminates). `kel/log.md`'s diagram covers only the same-serial terminal-versus-content case
  (tier-rank), not the terminal-above-the-fork burial its siblings document.
- `kel/events.md` §Key-state fields defines a signing key's validity window as running "from the
  witnessed time of the `Rot` that reveals the key" — for the first key there is no such event (it
  is revealed by the inception), so a literal implementation gives the first key no window. The
  glossary's sender-key-currency entry says "establishment events," which is the right statement.

**C4 — Note. The page-model and retention derivations are internally consistent.** The
`kel/reconciliation.md` invariants were checked against `log.md` / `events.md`: the below-seal
arithmetic in invariant 5 (a parent two or more below the seal puts the child strictly below it; a
parent one below makes a sibling at the seal's own serial) is exact; the two shapes documented as
exceeding one page are genuine exceptions and are handled; and the retention floor (keep at least
two competing events per position) is kept distinct from the acceptance cap (accept at most two
witnessed sealed branches) everywhere it appears.

### Group D — The IEL primitive (`log`, `events`, `verification`, `merge`, `reconciliation`, `delegation`)

**D1 — Major (soundness). "An owner's counter-seal then makes it two → Disputed" claims a recourse
the witnessing model forbids.** `iel/log.md` §Forked versus Disputed, describing the takeover case
(a single accepted sealed branch you did not author): "read node-agnostically it reads **Active** (a
clean sealed tip); **an owner's counter-seal then makes it two → Disputed**." Under the model stated
everywhere else, the owner's counter-seal is a **late sibling at an already-witnessed position** —
first-seen-declined by honest witnesses, permanently sub-threshold, never accepted, never counted.
`kel/compromise.md` says this outright for the identical shape: "A competing `Rot` at `v_N` is
**first-seen-declined** (deferred-pending, forcing nothing). It cannot overturn the takeover," and
its §Live-tip dispute section derives that a second **accepted** seal requires witness collusion.
The IEL sentence, read as written, tells an operator that after a quorum takeover they can at least
force the prefix into Disputed and deny it to the attacker — they cannot, absent collusion; their
counter-seal changes nothing and the attacker keeps a clean Active chain. This is a doctrinal error
about the security model in the exact place an operator would look for their options. The fix is to
delete or invert the clause (the counter-seal is declined; the recourse is reincept plus out-of-band
notice, as the rest of the corpus says).

**D2 — Minor (consistency). The joiner-consent anchor is an undeclared exception to "kind-strict,
exact-event-kind" anchoring.** The categorical statements — `protocol-doctrine.md` §Compromise is
Permanent ("a member participates…by authoring a fresh KEL event…(`Ixn` → IEL `Ixn`, `Rot` → IEL
`Evl`)"), `kel/events.md` §Anchoring is kind-strict ("a leaf-anchor check is **exact-event-kind**…
content ← `Ixn`; tier-2 establishment / governance / kill / terminal ← `Rot`"), and
`iel/verification.md`'s threshold-anchoring bullet ("Each participation must be of **exactly** the
kind that reveals the capability the act exercises") — admit no case of a KEL `Ixn` anchoring an IEL
`Evl`. Yet the added-member consent rule requires exactly that: a joiner consents to an `Evl` via
its own KEL `Ixn` (stated in `iel/events.md`, `event-shape.md`'s device-swap diagram, and the
counting bullet in `iel/verification.md` itself). The two are reconciled only by an unstated
distinction — the joiner's anchor is "consent," not a "participation," so the exact-kind rule
doesn't apply to it. An implementer coding the categorical rule as written rejects every roster
addition. One sentence in each categorical site ("except the added-member consent anchor, a KEL
`Ixn` counted toward consent-of-added and never toward a threshold slot") closes it. The same
exception recurs at the federation (`witnessing.md` §Roster governance: a joining witness "pairs its
consenting KEL `Ixn`" with the pre-add witnesses' KEL `Wit`s — a KEL `Ixn` anchoring a federation
`Wit`, which the categorical "the IEL `Wit` ← KEL `Wit`" likewise forbids). The related asymmetry —
initial members consent to the `Icp` at tier 2 (KEL rotations) while a later joiner consents at tier
1 (a KEL `Ixn`) — is stated but never justified; a sentence saying why founding consent needs the
reserve and joining consent does not would keep a future editor from "fixing" it in either
direction.

**D3 — Note (soundness, positive). The IEL-specific machinery holds together.** The pieces unique to
this layer were each checked: the threshold-vector bounds are jointly satisfiable at every roster
size they admit (the two-member advisory case is honestly labeled and matches the residuals
catalog's freeze entry); the outgoing-quorum pricing of an eviction (so a roster change cannot lower
its own gate before cutting) and the atomic cut-plus-bury argument (a two-event sequence would leave
a re-fork window) are sound; the roster-less re-seal is distinguishable from a real roster change
and its idempotent-redelivery versus independent-ceremony split (identical member-tip pins versus
different pins) is correct; the facet dispatch for the shared federation kind is enforced on every
reading path including resumes, which closes the governance-payload-on-a-user-chain confusion; and
the delegation walk's bounded-per-candidate design (walk up the committed path, never materialize
the delegate set) is a genuine complexity bound.

**D4 — Note. The IEL docs replicate the B1 / B2 ambiguities verbatim.** `iel/log.md`,
`iel/merge.md`, `iel/verification.md`, and `iel/reconciliation.md` mirror the KEL texts — including
the unqualified Forked definitions, the "it stays forked / deferred-pending" divergence-signal
wording, and the same-position-only dispute enumeration. Whatever resolution B1 and B2 get should be
propagated here in the same pass; no separate finding.

### Group E — The SEL primitive (`log`, `events`, `verification`, `merge`, `reconciliation`)

**E1 — Note (soundness, positive). The SEL's two-axis model is the strongest-argued part of the
event-log layer.** The load-bearing claims were each checked and hold: the argument that an owner
IEL cannot prevent its own SEL's equivocation (an anchor is an opaque digest, so one IEL content
event can name two competing SEL events without the IEL being able to tell) is correct and honestly
motivates the SEL witnessing itself; the "one content event per SEL per anchoring IEL content event"
rule now carries a concrete enforcement mechanism (anchor-identity dedup — the anchor is derivable
from each SEL event's down-pin, so a verifier can perform the check from held data); the
acceptance-requires-accepted-anchor rule cleanly proves that severance can never reach an accepted
sealed SEL branch (its anchor is an IEL sealed event, never buried), which is what makes "severance
never downgrades a Disputed" sound rather than asserted; and the deadness-precedence composition
(resolve inherited owner-IEL deadness before the SEL's own divergence machinery) is enumerated
exhaustively in `sel/reconciliation.md` Matrix 2, including the two unreachable-by-construction
rows, each with a correct reason. The lineage-walk model (positive walk to the lowest live instance,
per-instance kill targets so a re-established successor survives, the feature-layer obligation
honestly flagged as un-backstopped and mirrored in `residuals.md`) is consistent across `log` /
`events` / `verification` / `reconciliation`.

**E2 — Minor (consistency). The kind-string length cap appears only outside the catalogue.**
`sel/events.md` §`Gnt` asserts a `vdti/sel/v1/grants/*` kind is "capped at 64 characters **like any
event or SAD kind**," and the glossary repeats "(≤ 64 chars)" — but `kinds.md`, the self-declared
canonical enumeration of kinds and their conventions, states no length cap anywhere, and neither
does `sad.md`'s `kind` field definition. Either the cap is real protocol validation (then the
catalogue and the SAD layer should state it once, authoritatively) or it is not (then the two
mentions overstate). As written, the only two places the constraint exists are a per-kind footnote
and a glossary aside.

### Group F — Federation and witnessing (`bootstrap`, `witnessing`, `topics`, `mesh-transport`)

**F1 — Note (soundness, positive). The bootstrap and witnessing arguments hold.** The genesis
argument — separating "is this inception validly created" (ordinary member anchoring, no special
rule) from "should anyone trust it" (the configured prefix, inherently out-of-band) — is the honest
resolution of the apparent circularity, and the doc says so without overselling. The witnessing
mechanics were checked in detail: the floor arithmetic (any two quorums share at least
`2·threshold − signers ≥ 1` witnesses), the fork-cost / slack trade, the federation's joint bounds
(the recoverability cap and the exclude-self pool are satisfiable together from the four-witness
floor up, with the worked minimum config `{threshold 2, signers 3}` correct), and the witnessed-time
construction (the threshold-th-smallest receipt time: monotone in the right direction, so an
adversary adding late receipts cannot push a crossing later, and pulling it earlier needs a full
witness compromise) are all internally consistent and correctly argued. The receipt shape's
load-bearing choices (the timestamp inside the signed payload; equality against the chain-committed
config rather than the receipt's self-asserted copy) each carry a stated attack they close, and the
stated attacks are the right ones. The mesh transport is a standard authenticated-key-exchange shape
with per-direction keys and counter nonces; its reuse-is-structural claim is justified.

**F2 — Note. The dispute-collapse argument repeats the single-winner premise.** `witnessing.md`
§First-seen states the same collapse B2 examines ("a seal on a dead lineage — one that **lost
first-seen at any earlier position** — is itself dead on ascent…so a dispute cannot form across
positions") — sound in the honest regime, and resting on the same premise the both-siblings-accepted
residual violates. Whatever rule B2's resolution picks should be stated here too.

**F3 — Minor (consistency). Which witness-config governs a federation member's own KEL events is
implied, never stated.** `witnessing.md` says every federated chain carries its own witness-config
and a founder `Fcp` carries none (`event-shape.md` marks `witnesses` forbidden on a KEL `Fcp`, and a
witness KEL is `Fcp`-rooted for life). Exclude-self peer-witnessing then witnesses those
`Fcp`-rooted KELs' events — under whose `{threshold, signers}`? The only coherent answer is the
federation IEL's own config, but no sentence says so, and the per-layer rule ("a KEL…carr[ies] its
**own** authoritative witness-config") points the other way for the one KEL class that never carries
one. One sentence closes it.

### Group G — The policy layer (`policy`, `documents`, `evaluation`)

**G1 — Note (soundness, positive). The separation argument and the anchoring-position machinery
hold.** The two-mechanism split (structural chain authorization; relying-party-held document policy)
is argued from the right attack (a self-chosen policy is a backdate or an "accept me" surface) and
enforced consistently across the three docs. The earliest-anchor argument for the credential's
committed locator — an earlier anchor carrying the commitment would need a hash cycle, because the
commitment embeds the credential's identifier which embeds the locator — was checked and is correct,
and it genuinely closes the tier-inversion re-anchor (a later content-tier re-anchor moving the
as-of past a revocation is never consulted). The fail-secure composition rules (zero thresholds
rejected, unknown constructs deny the whole policy, budget exhaustion denies) are the right
defaults, and the honest admission that threshold satisfaction over compound branches is a
set-packing search — with the divergence-between-verifiers bounded to the deny direction — is a
correct and unusually careful piece of analysis.

**G2 — Minor (consistency / soundness). The no-signer-reuse rule is pinned for `thr` but left
ambiguous for `wgt`, while claiming the two coincide.** `policy.md` states "a threshold is the
special case [of the weighted composer] where every weight is 1," and its composition rules open with
"a counting composer (`thr`, `wgt`) credits by identity prefix" — but the elaborated no-reuse machinery
(a signer fills at most one satisfied branch; satisfaction is an existential assignment search) is worded
for `thr` only, while `wgt` gets a different mechanism (per-identity-max crediting), stated for identities
reached through several branches, not for signers inside compound branch quorums. For `wgt` over compound
branches with overlapping pools the two mechanisms give different answers, so the claimed special-case
equivalence fails unless the assignment rule is declared to govern `wgt` too. Since a conforming-but-permissive
`wgt` evaluator could accept what the equivalent `thr` denies, this is worth one clarifying sentence
(the assignment rule governs both counting composers; per-identity-max additionally caps a repeated identity's
weight).

### Group H — The protocol primitives (`essr`, `ipex`, `receive-key-directory`, `group-key`, `membership`, `authored-dag`)

**H1 — Note (soundness, positive). The six primitives are tightly scoped and mutually consistent.**
Each doc's boundary section genuinely matches what its neighbors assume of it — the checks were made
pairwise (the sealed envelope's fields against the shapes catalogue; the disclosure exchange's gate
clauses against the credentials feature's acceptance list; the directory's tier-2 publish rule
against the SEL grant machinery; the group-key roster-versus-membership split against both
consumers). Three arguments were specifically probed and hold: the two-binding argument for the
sealed envelope (recipient in the signed cleartext defeats re-addressing; sender inside the sealed
content defeats strip-and-re-sign — and the first three properties genuinely need neither); the
presentation envelope's single-signature double duty (ownership plus replay binding, with the
dedup-cache retention window and the two-sided timestamp check leaving no gap between cache expiry
and acceptance expiry); and the membership walk's requester-discloses-its-own-secret design, whose
leaked-disclosure consequence is correctly bounded to status-checkability because the store matches
the disclosed identity against the live signature. The authored-DAG's honest admission that two
roots are _not_ self-proving — and that one-lane-per-writer therefore needs the anchored root, an
enforced rule rather than a derived one — closes what would otherwise be the removed-writer
fresh-lane hole, and the interval check against the durable removal cutoff is correctly a local
check needing no fork propagation.

**H2 — Minor (consistency). The rescission-lookup address model is inconsistent across its four
homes.** The address of the small killed-marker log a fail-open check fetches derives from
`(owner, topic, data)` — so every consumer must agree on the `topic`. The docs give three different
answers:

- A **delegate** rescission lookup uses the primitive tag as its topic (`iel/delegation.md`:
  `topic: vdti/sel/v1/actions/rescission`), and `tags-and-topics.md` endorses this generally — its
  tag-table row says the rescission tag serves as "a `Dth`-anchored kill's target **+ its
  lookup-SEL**."
- A **document-member** rescission lookup instead uses a feature topic
  (`features/shared-documents.md` §Shapes: "the shared removal locus
  `vdti/doc/v1/topics/rescission`"), contradicting the tag-table row's "+ its lookup-SEL" for
  exactly the `Dth`-anchored class it describes.
- A **chat-membership** rescission lookup has no topic at all: `membership.md` derives it from "{
  group, **the rescission topic**, the member's grant instance }", but `features/exchange.md`'s
  reserved-names section reserves no rescission topic for the exchange concept, and no catalogue row
  exists.

The kill **targets** are consistent everywhere (the primitive tag, per `iel/events.md`'s "one
rescission tag covers both") — the inconsistency is confined to the lookup object's address. It has
teeth in exactly one place: the opt-down fail-open path trusts a **miss**, so a killer and a checker
that derive the address under different topics silently turn "rescinded" into "best-effort
not-rescinded" for opted-down consumers. One catalogue decision (either the primitive tag is the
topic for every `Dth`-anchored lookup, or each feature reserves its own and the tag-table row drops
"+ its lookup-SEL") plus a reserved chat topic closes it.

### Group I — The features (`credentials`, `exchange`, `shared-documents`)

**I1 — Note (soundness, positive). The feature layer composes the primitives it claims and little
else.** The credentials acceptance conjunction was checked clause-by-clause against the primitives
each clause delegates to, and the delegation of each is real (nothing is silently assumed twice or
not at all); the bearer analysis (redemption-as-revocation, the copy-race residual, and the
reusable-transferable-bearer impossibility argument) is coherent and honestly bounded, including the
terminated-issuer interaction stated in both directions. The exchange feature's two-axis currency
model (the sender's own witnessed establishment intervals; the witnessed epoch window for chat) is
consistent with the witnessing doc's witnessed-time construction it leans on, and its residuals
section matches the residuals catalog entry-for-entry — including the open-epoch future-dating
non-monotonicity, correctly labeled self-harming. The shared-documents honored predicate (grant-open
position ≤ anchor position ≤ rescission bound, all three on the editor's own append-only chain) is
clock-free as claimed, the effective-floor observation (a version cannot predate the moment its
author could know its cited grant, by hash-preimage order) is correct, and the seal-locate warning
("the grant must be sealed, not merely fetched" — a cited grant-doc is honored only when the
creator's chain sealed it) closes what would otherwise be a total bypass and is rightly stated in
the doc instead of left to inference.

**I2 — Minor (consistency). The document-SAD field tables disagree on which fields are optional.**
`shapes.md`'s V0-constitution and version tables carry no required/optional column (its credential
table does), and their `nonce` rows read as unconditional ("High-entropy — makes the version SAID
unguessable"), while `features/shared-documents.md` §Shapes marks `nonce?` optional on V0, version,
comment, and comment-resolution ("high-entropy for a private doc; a public document may omit it").
An implementer validating from the catalogue rejects every public document. The catalogue should
carry the optionality (and, per A3, a kind for the rescind-doc, whose field shape the feature doc
now states while `shapes.md` still defers it wholesale to a forthcoming encode).

### Group J — Cross-document consistency

**J1 — Note (positive). Terminology is unusually disciplined.** The load-bearing terms were traced
across the corpus — the two floors (witnessing versus authorization) and the position gate; the
witnessed / accepted / confirmed-tip ladder; sealing-versus-sealed; the retain-two floor versus the
accept-two cap; the three near-homographs around termination — and outside the findings above they
are used consistently everywhere, including in the newest docs. The glossary's one-line definitions
match the owning docs in every case checked, and the constants (`MAXIMUM_UNSEALED_RUN` = 64,
`MINIMUM_PAGE_SIZE` = 129, `MAXIMUM_ROSTER_SIZE` = 32, `MAXIMUM_MANIFEST_LIST` = 128,
`MAXIMUM_DELEGATION_DEPTH` = 8, `MAXIMUM_SEL_LINEAGE` = 64, `MAXIMUM_GRANT_ADDS` = 64, the 365-day
witness key window, the one-minute clock tolerance) are quoted with the same values at every site
they appear.

**J2 — Minor (consistency / overstatement). The front-door claims a verifier can see what the corpus
says is invisible.** The top-level `README.md` says a verifier can determine "whether an identity
has **diverged or been compromised** — from the data itself," and `system-thesis.md` opens with
"system-wide state — including **attack exposure**." The corpus itself is careful to say the
opposite for the highest-severity compromise: a reserve-theft takeover is a **clean linear chain** —
"silent to third parties on a dormant chain," structurally indistinguishable from the operator
(`kel/compromise.md`, `monitoring.md`, `residuals.md`), which is exactly why the monitoring layer
exists and why its guarantee is phrased "no **undetected** takeover for a **monitored** chain."
Divergence-shaped compromise is verifier-visible; a clean takeover is owner-detectable only. The two
orientation sentences should be narrowed to what the design actually delivers — they are the first
thing an evaluator reads, and the honest version is still a strong claim.

**J3 — Note. Where a later doc quietly resolves an earlier doc's open texture, the resolution should
flow back.** Two instances beyond those already filed: `protocol-doctrine.md`'s §Terminology defines
Forked without the acceptance qualifier that `sel/verification.md` (its §Witnessed-divergence read)
states exactly right ("It forms only under witness compromise…An accepted sealed event is one
witnessed at threshold **and** on a live lineage"); and the `residuals.md` signing-key-forgery
entry's "a fork the owner sees at once" predates the prevention model's stall-and-decline behavior.
Both are the B1 cluster's edits; listed here so the propagation is not missed.

## Coverage

Read in full, in the design README's order: the top-level `README.md`; the orientation pair
(`system-thesis.md`, `glossary.md`); the five SAD docs plus the three identifier catalogues
(`kinds.md`, `shapes.md`, `tags-and-topics.md`, `substrate/federation/topics.md`);
`protocol-doctrine.md`, `residuals.md`, `monitoring.md`; `event-shape.md`; all six KEL docs, all six
IEL docs, all five SEL docs; `bootstrap.md`, `witnessing.md`, `mesh-transport.md`; the three policy
docs; the six protocol primitives; and the three features. Not read, by design of the pass: the
earlier reviews in this directory (decorrelation), the notes under `docs/canon/`
(standalone-soundness posture), and the top-level `MODEL.md` / `USES.md` (outside the design
surface; the top-level `README.md` was read as the entrypoint).
