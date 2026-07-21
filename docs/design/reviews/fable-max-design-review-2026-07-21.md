# Fable design review — 2026-07-21

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-design-review-2026-07-21.md. create it iteratively and continue to
> edit throughout this task, since the fable model may be flagged and this will retain fable
> thinking and results. place this prompt, verbatim, at the top of the file as a quote (>). the
> document should not use jargon and have clear voicing. it should be broken into logical groups for
> easy digestion.

## How this review was done

This is a cold review: a fresh read of the design documents as they stand, in the reading order
given by [the design index](../README.md), with no prior working context consulted. Every claim
below cites the document it came from. The review asks two questions of every rule:

- **Soundness** — does the rule hold when someone is actively trying to break it, and can a verifier
  actually perform the check the rule depends on, from data the verifier is guaranteed to have?
- **Consistency** — do the documents agree with each other: same rule stated the same way
  everywhere, counts and tables matching their prose, terms used with one meaning.

The document was built iteratively while reading, and findings are grouped by the layer they live
in. Each finding is written to stand alone: what the documents say, what the problem is, and why it
matters, in plain language.

Severity labels used below:

- **Hole** — a gap that could let a guarantee fail against an adversary.
- **Underspecified** — the design cannot be implemented or verified as written; a reader must guess.
- **Disagreement** — two documents (or two places in one document) state conflicting things.
- **Minor** — wording, drift, or clarity; no behavior at stake.

## Verdict at a glance

The design is in strong shape. Across roughly forty-five documents, the layering holds (each layer
consumes only what the layers below define), the counts, tables, constants, and anchor rules agree
everywhere they are restated, and the security arguments are made at the level of structure rather
than of code paths — the stated posture, honored in practice. The honest-limits catalog
(`residuals.md`) genuinely matches what the feature documents concede. No finding in this review
breaks a security guarantee: every attack path I could construct ends in the fail-secure outcome the
design intends (refuse, freeze, or reincept), including the paths the documents describe
imprecisely.

What the review did find, in order of weight:

1. **One real disagreement inside the correctness-proof surface (F2, with F4 its federation-side
   companion).** The doctrine's divergence terminology claims every irrecoverable fork is two
   competing seals at a single position, provable as witness misbehavior. The merge and
   reconciliation documents — correctly — specify a rule ("retain-and-count") that produces
   irrecoverable forks with the two accepted seals at _different_ positions, reachable with every
   witness honest under partial views, and a second such path exists through federation rebinds. The
   safety outcome is identical on every path; what disagrees is the case enumeration, the "clean
   seal" definition, and the forensic attribution ("witness double-sign" versus the author-key
   double-reveal that actually holds in general). In documents whose stated role is a load-bearing
   proof, this is worth fixing.
2. **Two places where a definition is not pinned down enough to implement uniformly (F3, F7).**
   Whether a data-log event's acceptance waits on its anchoring identity-log event's acceptance; and
   the search semantics implied by the policy layer's "a signer fills at most one slot" rule.
3. **A handful of minor wording and scoping items (F1, F5, F6, Q4)** — places where a claim reads
   stronger than the mechanism (the custody read gate), where a qualifier is implicit (convergence
   across differing trust configurations), or where an example could mislead an implementer (the
   currency gate's cut-only parenthetical).

Everything else I checked — the derivation and canonicalization rules, the two-tier key model, the
recovery machinery, witnessing and its floor arithmetic, the negative-check design, the policy
layer's as-issued model, and the three features' composition of the primitives — is internally
consistent and sound against the adversarial readings I applied. The specific checks are listed in
"What was checked" below.

## Reading log

_Complete — every listed document was read in full during this review._

- [x] `README.md` (repository root)
- [x] `docs/design/README.md` (reading order and layer map)
- [x] Layer 0 — orientation: system thesis, glossary
- [x] Layer 1 — data substrate: SAD, SAID, custody, availability, compaction, catalogues (kinds,
      shapes, tags-and-topics)
- [x] Layer 2 — doctrine: protocol doctrine, residuals, monitoring
- [x] Layer 3 — event logs: event shape; KEL (log, events, verification, merge, compromise,
      reconciliation); IEL (log, events, verification, merge, reconciliation, delegation); SEL (log,
      events, verification, merge, reconciliation)
- [x] Layer 4 — federation and witnessing: bootstrap, witnessing, topics, mesh transport
- [x] Layer 5 — document authorization: policy, documents, evaluation
- [x] Layer 6 — protocol primitives: ESSR, IPEX, receive-key directory, group key, membership,
      authored DAG
- [x] Layer 7 — features: credentials, exchange, shared documents

Scope note: the review covers the design surface (`docs/design/**`) per its own reading order. The
root `README.md` was read for orientation; `USES.md`, `MODEL.md`, and the working notes under
`docs/canon/` are outside a cold review of the design canon and were deliberately not consulted, so
that this pass stays decorrelated from the notes the doctrine was written from.

## Findings

_Grouped by layer. Every finding was checked against the actual current files; quotes are verbatim._

**A few terms, in plain words, so the findings read standalone.** Every identity and data record in
this design lives on an append-only chain of events. Events come in two classes: **content**
(everyday acts, forgeable with a device's everyday signing key) and **sealed** (key changes,
membership changes, grants, revocations — forgeable only with a second, held-apart secret, the
"rotation reserve"). A **seal** is a sealed event's position; everything at or below the latest seal
is locked history. Independent **witnesses** (a federation) sign the first version of each event
they see at each chain position; an event signed by enough of them is **accepted**. A fork — two
different events claiming one position — resolves by class: a content fork is recoverable (a later
sealed event "buries" the loser), while two _accepted sealed_ branches are a **dispute**:
irrecoverable, and the identity must start over under a new identifier ("reincept"). The design's
central claims are that any verifier can compute all of this from the data alone, and that honest
operation never produces a dispute.

### Data substrate (layers 0–1)

**F1 — Minor. The custody doc's read-gate framing is softer than the residuals doc's honest
statement, and could mislead a reader into over-relying on `readers`.**
`primitives/data/sad/custody.md` (§Adversarial framing) says "`readers` evasion requires
membership-level compromise" and that an adversary who obtains the bytes "still cannot satisfy a
downstream verifier that re-checks the requester's `readers` membership." The residuals catalog
(§"Confidentiality is operational, not cryptographic") states the real position plainly: the read
gate controls access **through the store**; once bytes escape, the plaintext is readable, and
confidentiality requires encryption. Both statements are technically compatible (the custody bullet
is about authorized-read _status_, an integrity property), but the custody doc is where an
application designer first learns what `readers` buys, and its heading implies a confidentiality
property the mechanism does not provide. Suggest one added sentence in custody.md's adversarial
framing echoing the residuals position: the gate is operational access control; for secrecy against
a leaky replica or a hostile holder, encrypt.

### The event-log core (layer 3)

**F2 — Disagreement (the most substantive finding of this review). The doctrine's divergence
terminology says a dispute can only be two seals at the same position, but the merge and proof
documents specify a rule that produces disputes with accepted seals at different positions — and the
"every dispute is a provable witness double-sign" attribution does not cover those paths.**

Where the documents stand:

- `protocol-doctrine.md` §Terminology (Disputed) says: "The **only** irrecoverable case is **two
  seals at the same serial**: siblings at one position … which takes a **witness double-sign** at
  that seal position." Its pre-seal-verifiability passage repeats it: "two branches both accepted at
  a seal can only fork at their competing seals themselves. Every dispute collapses to two witnessed
  seal-siblings at **one position**." The system thesis flowchart, the glossary ("witnessed vs
  accepted"), `kel/compromise.md` ("A `disputed` verdict needs two accepted seals at one serial — a
  witness double-sign"), and `kel/reconciliation.md` Matrix 3 ("never an honest race") all carry the
  same attribution.
- But `kel/merge.md` §4 (and §How a burying seal-advancer resolves a content fork, step 4) states
  the **retain-and-count** rule: a burying seal-advancer whose burial would drop a branch carrying
  an **accepted** sealed event is rejected, the fork is Disputed, "and the burying event is itself
  retained as a competing sealed branch and counted." `kel/reconciliation.md` proves this exact rule
  (Matrix 4, the sealed row; §Convergence, second bullet: "two witnessed sealed branches → Disputed
  — retain-and-count is the convergent semantics"). In that geometry the two accepted seals sit at
  **different serials**: the sealed branch's own seal inside the fork, and the rejected burying seal
  at its own later position.

Why the different-position case is reachable without any witness signing twice: witnessing is
per-position; the branch's seal and the burying seal occupy different positions, so different
first-seen gates. The shape-validity gate is supposed to make a witness decline a burying seal that
would drop an accepted sealed branch — but that check runs over "the branches the verifier holds,"
and a witness that has not yet received the competing branch (partition, gossip lag — the
propagation premise failing, which is the exact residual this machinery exists for) validates the
burying seal as an ordinary extension and honestly signs it. Both seals are then accepted with every
witness honest. A cryptographic misbehavior proof still exists — both seals reveal the same reserve
preimage (the author-side double-reveal the doctrine notes for `{Rot, Rot}`) — but it names the
**author key**, not any witness, so the "forensics, then eviction" response the residuals catalog
attaches to disputes has no witness to evict on this path.

What should be reconciled (the safety outcome is not in question — every path converges to the
fail-secure Disputed/reincept verdict, and nothing buried is ever resurrected):

1. The Terminology claim "the only irrecoverable case is two seals at the same serial" should be
   restated to include the retain-and-count geometry, or the merge rule should be explicitly derived
   from it as the cross-position completion. Right now the concept map and the enforcement spec
   disagree on the case enumeration, in a doc whose stated role is a correctness proof.
2. "Two accepted sealed branches ⟹ a provable **witness** double-sign" should weaken to "⟹ a
   cryptographic misbehavior proof — a witness double-sign at one position, **or** an author-key
   double-reveal across positions." The same-position statement (Matrix 3) is correct as scoped; the
   global attribution is overbroad.
3. The **clean seal** definition ("a seal is clean iff it carries no competing witnessed sibling
   **at its own position**") does not classify the different-position dispute correctly: in that
   geometry each of the two accepted seals has no sibling at its own position, so both read "clean,"
   and "the last clean seal" would compute **above** the fork — but the trust boundary must sit
   below it. The definition needs a clause for a seal whose burial was rejected (or more generally:
   clean = no competing accepted sealed branch anywhere at-or-past its position).

Also folded here: **Q2 resolves the same way.** A second path to two accepted seals with no witness
double-sign is a race between two federation-rebind events at one position declaring different
target federations — each is witnessed by its own declared federation's selection, the two witness
sets are disjoint, and each set honestly accepts its first-seen sealed event. (The author-side
double-reveal proof again exists — both rebinds reveal the same reserve.) The witnessing doc's
fork-cost/intersection argument assumes competing siblings share a witness selection, which holds
for inherited pins (content) but not for two _declared_ pins. Worth an explicit statement wherever
the "sealed forks require collusion" claim appears, and in the witnessing doc's rebinding section. —
_Verified against the federation docs: F4 below confirms the gap in the witnessing doc's own text._

One scoping note for fairness: the identity-log documents are more careful than the KEL-side ones —
`iel/log.md` describes Disputed as "proof the quorum was subverted **or** the witnesses colluded,"
which is the accurate two-path statement. The recommendation is to make that phrasing the uniform
one (and extend it with the honest-witness partial-view path above), not to introduce a new idea.

**F3 — Underspecified. Does accepting a data-log (SEL) event wait on its anchoring identity-log
(IEL) event being accepted?** `sel/log.md` says a SEL event is committed "only together with its
owner-IEL anchor" and that "the batched anchor is an owner-signed IEL event the witness validates as
part of its ordinary job" — but "validates" is not pinned to either "checks structurally" or
"requires witnessed-at-threshold." The distinction is load-bearing in one corner:
`sel/reconciliation.md` Matrix 2's last row ("severance downgrades a Disputed" — one of two accepted
sealed branches severed by a dead owner-IEL anchor) is reachable **only** if a SEL sealed event can
reach acceptance while its anchoring IEL event is still short of threshold and later loses (a sealed
IEL anchor that was _accepted_ can never end up on a buried branch — the no-burying-a-sealed-branch
guard blocks that burial). The neighboring `{Trm, content}` row is honestly marked "unreachable by
construction"; this row deserves the same reachability analysis, and the witnessing/merge docs
should state explicitly whether SEL acceptance gates on IEL-anchor acceptance (and if it does, mark
the downgrade row unreachable-for-completeness too).

### Federation and witnessing (layer 4)

**F4 — Disagreement (companion to F2). The witnessing doc's same-selection claim has a stated
exception in the same document, and the two are not reconciled.**
`substrate/federation/witnessing.md` §Deterministic selection: "Competing events at one
`(prefix, serial)` therefore route to the **same** selected set, so the quorum-intersection the
floor relies on is over one set." But the same doc's rebind path (§The witness receipt,
federation-pin currency; §Rebinding) specifies that a rebind **declares** its own pin and "selects
over the new roster" — necessarily, or a prefix could never escape a dead federation. So two
competing rebind events at one position, each declaring a different target federation, select
**disjoint** witness sets; each set honestly first-seen-accepts its one sealed sibling, and both
branches end accepted with every witness honest. That is a reachable dispute with no witness
double-sign (the author-side proof stands: authoring two rebinds takes the rotation reserve, and
both siblings reveal the same reserve — so the verdict Disputed/reincept is still the right,
fail-secure outcome, and reaching it still requires a reserve compromise or author equivocation).
The doc's §First-seen closing claim — "the **only** reachable dispute is a seal-vs-seal collision at
the last (live) seal … which takes a provable witness double-sign" — inherits the same gap.
Suggested reconciliation: scope the same-selection claim to events with **inherited** pins, state
the declared-pin exception explicitly, and add the cross-federation rebind race to §Rebinding with
its verdict and its (author-side) misbehavior proof.

**F5 — Minor. Convergence language should carry its trust-set qualifier.** The convergence claims
("all nodes converge on the same verdict / effective value") are implicitly scoped to verifiers that
share a trusted-federation configuration. `bootstrap.md` is explicit that trust is per-federation
and non-transitive — so in the F4 race, a verifier that trusts only federation A does not count the
B-branch as accepted and reads the chain differently from a verifier that trusts both. That is
inherent to configured trust roots and not a defect, but the correctness-proof docs state
convergence without the qualifier. One sentence — "convergence claims are among verifiers sharing a
trusted-federation set; within one federation's mesh this always holds" — would make the scope
explicit.

**F6 — Minor. The currency gate's parenthetical could mislead an implementer.** `witnessing.md`
§As-of-context: the gate "compares roster **membership**, so it fires on a **cut** (a witness
removed), not on a pure rotation." An **add** also changes membership, so by the stated rule the
gate fires on adds too (an event pinned just before a witness joins is refused until it re-pins);
the parenthetical enumerates only the cut and could be read as a cut-only check. Saying "fires on
any membership change — an add or a cut — not on a pure rotation" would remove the ambiguity.

### Document authorization and the features (layers 5–7)

**F7 — Minor / implementation guidance. The policy layer's cross-branch counting rule implies a
search; say so, so implementations agree.** `primitives/policy/policy.md` (§Composition rules): a
threshold composer's count is over its branches, and "no single identity is counted toward more than
one of the satisfied branches — a signer fills at most one slot." Where branches are themselves
nested policies each needing a quorum (the doc's own worked example: two 20-identity quorums),
deciding satisfaction under that rule means asking whether there **exists an assignment** of signers
to branches with no signer reused — a set-packing style search, not a per-branch greedy check (a
greedy evaluator would wrongly deny some satisfiable policies, and differently-ordered greedy
evaluators would disagree with each other). The declarative semantics is well-defined as stated;
what is missing is one sentence telling implementers the evaluation is existential ("satisfied iff
some assignment works"), that naive greedy is non-conforming, and that the verifier-wide budget is
what bounds the search. This is not consensus-critical (policy evaluation is each relying party's
own decision), but shared policies should evaluate the same everywhere.

The features themselves produced no findings beyond what the earlier layers already carry: the
credentials, exchange, and shared-documents documents compose the primitives faithfully, and every
residual they concede appears in the residuals catalog (I checked the chat-authenticity,
writer-set-visibility, communication-graph, batch-linkage, bearer-race, and terminated-issuer-freeze
rows specifically — all present and accurately stated on both ends).

### What was checked and found consistent

For calibration, the checks that came back clean — this is what the absence of further findings
means:

- **Taxonomy and counts.** The kind sets (6 KEL / 9 IEL / 6 SEL kind strings in `kinds.md`) match
  the taxonomy tables in `event-shape.md`, the per-suite events docs, the glossary's kind table, and
  the reading-order blurbs ("five-kind plus founder variant", "eight-kind plus the federation
  marker", "six-kind").
- **Constants.** Every restatement agrees: unsealed-run cap 64 and page floor 129 (= 2·64 + 1)
  across the doctrine and all three suites; roster cap 32; manifest-list cap 128; delegation depth
  cap 8; lookup re-establishment cap 64 (inclusive); witness key window 365 days; clock tolerance 1
  minute; grant add-list cap 64; the verifier's page budget default 64.
- **The anchor rules.** The "each kind is anchored by exactly the matching kind" matrix is stated in
  four places (doctrine, `event-shape.md`, `iel/events.md`, `sel/events.md`) and is identical in all
  four, both directions, including the two kill-anchor discriminations and the recovery re-seal
  pairing.
- **The derivation surface.** The two-hash inception rule (chain identifier vs. per-event hash), the
  fixed-placeholder mechanics, the fully-compacted canonical form and its two rules, the sorted-set
  rule for order-independent lists, and the domain-tag byte convention are stated once each and
  referenced (not re-derived) everywhere else; the custody anchor tag, the revocation and rescission
  tags, and the forked/disputed synthetic identifiers in `tags-and-topics.md` match every consuming
  site.
- **Enforceability of stated checks.** For each stated rule I asked whether a verifier can actually
  perform it from data it is guaranteed to hold. The former gap in this area (one data-log event per
  anchoring identity event, previously uncheckable because anchors are opaque digests) is genuinely
  closed by making the data log its own witnessed chain; the negative-check design is performable
  end to end (the requester supplies its own blinded-claim secret for the membership walk; the kill
  walk rides the same freshness gate as ordinary trust); the one obligation a primitive cannot
  backstop (the lineaged kill target for published values) is explicitly flagged as a feature-layer
  invariant in three places, consistently.
- **Fail-secure posture.** Every "can't confirm" path I traced ends in refusal, not acceptance: an
  unconfigured trust set trusts nothing; a truncated walk reports incompleteness rather than
  not-killed; a withheld gated cutoff reads don't-honor; policy denies on unknown constructs and on
  budget exhaustion; the one-directional opt (fail-open is always an opt-down, never up) is stated
  identically at every site.
- **Honest-limits accounting.** Each residual I encountered inline in a primitive or feature doc has
  a matching row in `residuals.md`, and I found no residual row overstating a mitigation relative to
  the owning doc.

### Open questions raised and settled during the read

_These were carried forward while reading and are all resolved above or here; kept for the record of
what was probed._

- **Q1 — settled, with one wording note folded into F2.** The "content fork whose branches seal at
  different serials" case resolves deterministically through the acceptance rules: a branch rooted
  at a first-seen loss is dead on ascent, so its later seal is declined and never counts, and the
  one accepted seal buries the other branch. But the doctrine's phrasing — "the **earlier** seal
  buries the other branch" — reads as an earlier-**by-serial** tiebreak, and no such tiebreak exists
  in the enforcement docs: what actually decides is which seal reaches **acceptance** (first-seen at
  the witnesses), and if both reach acceptance under partial views the outcome is the
  retain-and-count Disputed of F2, not a serial-order winner. The case is sound; the word "earlier"
  should be pinned to acceptance order when F2's case enumeration is reworked. The reserve-theft
  takeover this machinery permits is the design's acknowledged point of no return, stated in the
  doctrine and the residuals catalog.
- **Q2 — settled: the "requires witness collusion" attribution is overbroad; promoted into F2 and
  F4.** Two competing federation-rebind events at one position, each declaring a _different_ target
  federation, are witnessed by _disjoint_ witness sets — each set honest, each accepting its one
  first-seen sealed event — so both branches end accepted with no witness having signed twice. The
  witnessing doc itself confirms a rebind "selects over the new roster," and nothing constrains the
  race. The author-side proof survives (both siblings reveal and sign with the same key, so the
  author key provably double-signed — authoring two rebinds takes the reserve), so detection and the
  Disputed verdict remain sound; only the attribution language is wrong.
- **Q3 — settled.** The "at most one data-log event per anchoring identity-log content event" rule
  is stated in `sel/events.md` (the `Ixn` row and §Per-kind semantics) and enforced as an explicit
  **defense-in-depth** guard (`sel/merge.md` §1, `sel/verification.md` per-event checks: "an
  owner-IEL anchor naming a SEL event at an already-attributed SEL serial is malformed → inert"),
  with the load-bearing fork-prevention correctly moved to the SEL's own witnessing. The old
  enforceability hole (an identity log cannot deduplicate opaque anchor digests) is precisely what
  `sel/log.md` §"The SEL is its own witnessed chain" closes. Consistent; no finding.
- **Q4 — settled as a minor observation (no doc change demanded, worth a line somewhere).** A device
  consents to joining a roster via a tier-1 act (its own KEL `Ixn` — `iel/events.md`, added-member
  consent), and the kind set has no unilateral "member resigns" act — leaving a roster is the
  identity's `Evl` cut, and a member's only self-serve exit is terminating its own device chain
  (`Trm`, drastic). So a device whose signing key alone is compromised can be conscripted into a
  hostile roster and cannot remove itself; the exposure is correlation (its prefix published in that
  roster's delta, visible to anyone who can walk that identity's chain) rather than any authority
  the hostile identity gains — the roster grants the identity nothing over the device's keys. If
  this is by design (roster membership is purely the identity's governance), one sentence saying so
  — and naming rotate-and-refuse-to-participate plus out-of-band dispute as the remedy — would close
  the question a reader is otherwise left with. The residuals catalog does not currently carry this
  row.
