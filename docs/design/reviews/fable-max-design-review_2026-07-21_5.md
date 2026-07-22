# Fable (max) design review — 2026-07-21 (5)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_5.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. ignore the existing files in docs/design/review.

## How this review was conducted

This is a cold review: it was produced by reading the current files in this repository only, with no
prior conversation context and without consulting the earlier review documents in this directory.
The reading followed the order prescribed by `docs/design/README.md`: orientation, then the data
substrate, then the cross-cutting doctrine, then the three event-log primitives (key event log,
identity event log, SAD event log), then federation and witnessing, then policy, then the protocol
primitives, then the features. The root `README.md` and `MODEL.md` were read for consistency with
the design surface.

The review focuses on two questions:

- **Correctness / soundness** — do the security arguments actually hold? Where a document claims a
  guarantee, is the mechanism it describes sufficient to deliver that guarantee against an
  adversary? Are the stated checks performable by the party asked to perform them?
- **Consistency** — do the documents agree with each other? Where two documents describe the same
  rule, field, or flow, do they describe it the same way?

Findings are grouped by layer, in reading order, with cross-cutting findings at the end. Each
finding carries a severity:

- **Blocking** — a hole in a security argument, or two documents that contradict each other on a
  load-bearing rule. Should be resolved before the design is called complete.
- **Major** — a real gap or ambiguity that could mislead an implementer into an unsound build, but
  with a plausible correct reading.
- **Minor** — a smaller inconsistency, an unclear passage, or a missing cross-reference.
- **Note** — an observation, not a defect.

_Status: complete. Every design document under `docs/design/` was read in full, in the prescribed
order, plus the root `README.md`, `MODEL.md`, and `USES.md`._

## Verdict summary

**The design surface is sound and internally consistent to an unusual degree, and nothing I found is
blocking.** I read every document adversarially — trying to construct disputes without collusion,
backdates past the seal, laundered tiers, unperformable checks, and cross-document contradictions —
and the load-bearing arguments all held: the
two-accepted-sealed-branches-implies-provable-misbehavior claim survives its hardest case (via the
witness-side seal-cap mirror), the backdate defense is stated identically at every layer, the
kind-strict anchor matrix agrees at all four statements, the page and threshold arithmetic is
correct everywhere, the effective-SAID synthetic design is consistent across all five documents that
describe it, the residuals catalog's risk arithmetic all recomputes, and the checks the design asks
parties to perform are, in each case I probed, actually performable by the party asked (the
membership walk's disclose-your-own-secret fix and the shared-document seal-locate rule being the
two places the documents visibly did that work).

Three findings are worth resolving before calling the design complete, none of which breaks the
underlying model:

- **2.1 (Major)** — "extension discipline" names two different concepts, and the schema-evolution
  rule (closed vs. open kind schemas) that several structural claims quietly depend on is defined
  nowhere.
- **4.1 (Major)** — the "retain-and-count" rule for a rejected burial omits, at every one of its six
  statements, the acceptance qualifier that prevents it reading as a no-collusion
  terminalize-the-prefix griefing vector; the qualifier exists but only as one global paragraph in
  the merge documents.
- **11.1 (Major)** — `MODEL.md`, the plain-language rules document, tells an owner it can turn a
  reserve-theft takeover into a Disputed reading; the design says the owner's counter-seal is
  declined and the response is reincept plus out-of-band notice.

The remaining findings are Minor (a vestigial "iff federated" hedge, a misleading tier/count label
on the SEL inception row, a garbled constraint name, a nonce-optionality inconsistency, a
resolution-tree ambiguity, an under-specified group-key roster carrier, and the serve-by-SAID rule's
enforcement living wholly in a forthcoming document) or Notes recording what was verified. Severity
definitions are in "How this review was conducted" above; findings are numbered by section.

## 1. Orientation layer (system thesis, glossary)

Read: `system-thesis.md`, `glossary.md`, plus the root `README.md` and `docs/design/README.md`.

The thesis states the load-bearing claims — end-verifiability from data alone, the two capability
tiers, seal-bounded forks, resolution by tier rather than identity, the 0 / 1 / ≥ 2
accepted-sealed-branch verdict, fail-secure defaults — and every downstream document I checked
restates these the same way. The glossary hedges correctly ("the linked doc is canonical wherever
they differ") and its one-line definitions match the owning documents on every term I compared
(tier, seal, effective-SAID, first-seen, record-both, deferred-pending, position gate, severance).

**1.1 (Note) The two companion decision trees agree.** The thesis carries the federation-side
prevention tree and the doctrine carries the entity-side resolution tree. I checked them against
each other case by case: same-kind forks prevented by the witnessing floor; mixed sealed/content
races resolving by tier; the 0 → Forked / 1 → Active / ≥ 2 → Disputed verdict counted per branch.
They agree, including on the subtle points (a terminal `Trm` winning on tier-rank with no burying
event; a seal on a buried lineage being dead on ascent).

**1.2 (Minor) The resolution tree's "recoverable" box conflates two situations.** In the doctrine's
divergence tree, the one-sealed-branch / on-your-retained-branch path leads to the same box as the
zero-sealed-branch path — a box that says a burying seal-advancer must be authored at your last good
event. When your retained branch already carries the accepted seal, no new event is needed: the
chain already reads Active, as the surrounding prose says. The tree is not wrong (the prose corrects
it), but a reader following only the diagram would author a redundant event. A separate terminal box
("already resolved — reads Active") would remove the ambiguity.

## 2. Data substrate (SAD, SAID, custody, availability, compaction, catalogues)

Read: `sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`, `kinds.md`,
`shapes.md`, `tags-and-topics.md`.

This layer is in strong shape. The two-hash prefix/SAID derivation and its correlation-resistance
argument are correct as stated; the compact-down rule (Rule 1) plus verify-before-substitute
(Rule 2) genuinely close the lying-embedded-child gap the document describes; the strictly-ascending
rule for set-valued lists correctly removes the one degree of freedom JCS leaves open; and the
sign-only-what-you-have-seen discipline is honestly framed as signer-side tooling rather than
something a verifier could police. The custody anchor design (pin the anchoring event's parent, so
the anchor sits at the next position) correctly avoids the circularity a direct pin would create,
and the write-attribution argument — backdate-proof because the anchor is at an append-only position
— holds.

**2.1 (Major) "Extension discipline" names two different concepts, and the schema-evolution rules
are undefined.** `said.md` (§Signing surface) says a SAD's schema may gain new fields "under
extension discipline" and links to `protocol-doctrine.md` §Extension Discipline. But that section is
about a different thing entirely: the rule that a submitter only chains new events onto its own
prior events or attested-shared state. Nothing anywhere in the design surface defines how a kind's
field set may evolve — whether a verifier rejects unknown fields, whether new fields require a new
`kind` version (`v2`), or what an old verifier does with a new field. This is not only a broken
cross-reference: several structural guarantees quietly depend on the answer. The claim that chain
events "cannot carry" custody or availability fields (`sad.md`, `custody.md`, `availability.md`) is
enforced by kind-schemas having "no slot" for them — which is only an enforcement mechanism if
schemas are closed (unknown fields rejected). If schemas are open, the merge layer's
structural-validation pass has nothing to reject on. The documents that assert the rejection
(`custody.md` §Adversarial framing, `availability.md` §Adversarial framing) implicitly assume closed
schemas; the document that would state closed-vs-open — the missing schema-evolution doctrine — does
not exist. Recommend: define the schema-evolution rule explicitly (closed schemas

- version-bump-by-kind would make every existing claim true), and repoint the `said.md` reference.

**2.2 (Minor) Whether a `nonce` is required on shared-document SADs is stated three slightly
different ways.** `custody.md` says the credential, file, chat, and **private-document** kinds carry
a _mandatory_ high-entropy nonce. `shapes.md`'s prose above the comment tables says comments carry
"the same … `nonce?` a version does" (the `?` suggesting optional), while the version table's own
`nonce` row carries no "Optional" marker (other optional rows are marked) and its meaning column
drops the "if private" qualifier that the V0 and comment rows carry. The intended rule is presumably
"required when the document is private, optional when public" — but no table says that, and the
residuals catalog scores an omitted nonce as a Critical-band operator error, so the requirement's
exact scope is worth pinning down in one place. (Confirmed later in the read: `shared-documents.md`
§Shapes writes `nonce?` on the version, comment, and resolution shapes — optional, "high-entropy for
a private doc" — so the `shapes.md` version table's unmarked `nonce` row is the outlier.)

**2.3 (Note) The store's serve-by-SAID sort is coherent.** The rule in `kinds.md` — serve a SAD by
SAID only when learning the SAID already implied holding the chain, or when the SAD is public by
design and its read gate admits the requester — is checked consistently against the event-privacy
argument in `sad.md` and the no-SAID-to-event-index property in the doctrine. The
member-delivered-never-published carve-out for group-key wraps is stated in both `kinds.md` and the
group-key direction. No inconsistencies found.

**2.4 (Note) Blob handling is cleanly separated.** The digest-vs-SAID split (raw blobs addressed by
content digest, never SAIDs; integrity via the referencing SAD committing `{digest, size}`; size
advisory, digest integrity-bearing) is stated identically in `sad.md`, `shapes.md` (file, ESSR
envelope, chat message), and the availability doctrine.

## 3. Cross-cutting doctrine (protocol doctrine, residuals, monitoring)

Read: `protocol-doctrine.md` (in full), `residuals.md`, `monitoring.md`.

The doctrine is the densest document and the one I pressed hardest, because everything above it
inherits its claims. Its central arguments held up under adversarial reading:

- **The claim that two accepted sealed branches always imply provable misbehavior** (a witness
  double-sign, or a reserve double-reveal across disjoint federations) survives the hardest case I
  could construct: an honest mixed race (content vs. seal at one position) followed by the losing
  side attempting to seal its buried lineage. The argument closes because the witness mirrors the
  seal-cap — once a sealed sibling is accepted at a position, the content loser's lineage is below
  the new seal, and honest witnesses decline seals attaching to it ("you can't seal a buried
  chain"). Every route I traced to two accepted sealed branches passes through a double-sign at some
  shared position, a disjoint-federation rebind (reserve double-reveal), or the acknowledged
  eclipse/partition residual. The reasoning is distributed across three passages (the ladder, the
  dead-lineage rule, the shape-validity gate) but is complete.
- **The stall-not-fork claim for honest races** (witnessing floor + one-per-position first-seen,
  both kinds) is arithmetically sound: two quorums at one position must share
  `2·threshold − signers ≥ 1` witnesses, and a shared honest witness signs at most one sibling per
  kind. The split-stall exit (a burying seal-advancer that all selected witnesses sign, including
  those that signed a content sibling — the cross-tier co-sign) is consistent with the
  one-content-one-sealed-per-position ladder.
- **The backdate defense** (a below-seal sealed straggler is dropped, never counted, and never
  retreats the clean seal) is stated identically in the terminology, the divergence rules, pre-seal
  verifiability, the effective-SAID section, and the residuals catalog ("Late sealed straggler
  dropped"). No contradiction found anywhere.
- **The page-size arithmetic is consistent everywhere it appears**:
  `MINIMUM_PAGE_SIZE = 129 = 2·MAXIMUM_UNSEALED_RUN + 1`, with the two fork lineages (≤ 64 each)
  plus the burying seal-advancer exactly filling one page, is restated with the same accounting in
  the KEL log, merge, and reconciliation documents and the SEL events document.
- **The residuals catalog's risk arithmetic is correct.** I recomputed every Severity ×
  Exploitability product in both ranked tables; all match their stated band. The catalog's entries
  are consistent with the doctrine's claims (the brick requires signing key + collusion; the
  takeover requires a reserve quorum; fork-cost slides from `threshold` down to
  `2·threshold − signers` under a full partition).

Findings:

**3.1 (Note) The "reserve vs. current signing key" vocabulary reconciles — canonically, in the KEL
documents.** The doctrine's `{Rot, Rot}` analysis says two same-position rotations "both reveal the
one rotation reserve preimage in force" at the fork's parent, while the residuals catalog's brick
entry says forging the rival seal "needs the **current signing key**, not the reserve." Read side by
side these look contradictory. They are not: the preimage the honest seal reveals _becomes_ the
current signing key at that instant, and the KEL documents state this reconciliation explicitly and
carefully — `kel/events.md` ("The boundary case") and `kel/compromise.md` ("The live-tip dispute is
a killswitch") both derive the takeover-vs-brick split from exactly this timing. I verified all four
passages agree on the substance. The only residue is that neither the doctrine's `{Rot, Rot}`
sentence nor the residuals entry points at the KEL passages that carry the reconciliation; a
cross-reference from either would spare a cold reader the apparent contradiction.

**3.2 (Minor) "Dead lineage" is defined narrowly in one passage and used broadly elsewhere.** The
witnessing ladder defines a dead lineage as one that "lost first-seen at an earlier position (a
competing same-kind sibling there reached threshold)." But the case that matters most for the
no-collusion-no-dispute argument — a content event buried by an accepted _cross-kind_ sealed
sibling, whose lineage honest witnesses must then decline seals on — is not a same-kind first-seen
loss; it is covered by the separate witness-mirrors-the-seal-cap rule. The argument is complete, but
the "dead lineage" definition reads as the whole rule when it is half of it. Folding the two (a
lineage is dead when it lost first-seen _or_ when its attach point fell below an accepted seal)
would make the load-bearing claim self-contained.

**3.3 (Note) The freeze/no-freeze split at `t_use = 1` is honestly handled.** The doctrine
explicitly notes that at `t_use = 1` (legal at any roster size) a single member acts alone and that
this is exactly the recoverable tier-1 compromise class — consistent with the residuals entry
("Requiring at least two signers … where configured"). No false comfort.

**3.4 (Note) Monitoring's claims are consistent with the doctrine's.** The monitor is correctly
scoped as detection-only, untrusted-for-correctness, and the silent-takeover class it covers matches
the residuals catalog's reserve-theft and dormant-forge entries. The claim that the effective SAID
is queryable by prefix with no watcher network matches the doctrine's effective-SAID section.

## 4. Key event log (KEL)

Read: `kel/log.md`, `kel/events.md`, `kel/verification.md`, `kel/merge.md`, `kel/compromise.md`,
`kel/reconciliation.md`.

This group is the most internally cross-checked set in the design surface, and it largely earns its
"correctness proof" label. Things I verified in detail:

- The four-state machine, the merge outcome vocabulary (`Extended` / `Recovered` / `Terminated` /
  `Forked` / `Disputed`; `Sealed` / `Terminal` / `Invalid` / `Ignored`), and the routing order are
  stated identically in `log.md`, `merge.md`, and `reconciliation.md`, and the reconciliation
  matrices' cells follow from the merge rules they cite.
- The two independent rejection mechanisms on a terminated chain (seal-cap for a sibling to the
  `Trm`; kind-schema no-`Trm`-parent for a successor) are correctly identified as non-overlapping,
  and the claim that neither subsumes the other is right.
- The pre-rotation key stream (reveal-becomes-signing-key, two live keys), the spent-reserve
  boundary case, and the takeover-vs-brick split are consistent across `events.md`, `compromise.md`,
  `log.md`, and the residuals catalog.
- The recovery attach shapes (branch-tip-extending and ancestor-extending) are consistent between
  `merge.md` and the doctrine, and the ancestor-extending shape's cross-node-validatability argument
  (the divergence ancestor is structurally identical on every node) holds.
- Edge case 3 in `reconciliation.md` (a party whose branch was buried must not append a sealed event
  to its stale branch) correctly concludes the stale event is wasted, not a brick — consistent with
  the acceptance-gated reading below.

**4.1 (Major) The "retain-and-count" rule for a rejected burial reads, in isolation, as if it
creates a no-collusion griefing vector; the qualifier that prevents this lives in one paragraph of
`merge.md` and is omitted where the rule is stated.** The rule appears in three places: the
doctrine's no-buried-rotation guard ("a reserve-revealing seal authored against a fork that turns
out to hold a sealed branch is **retained as a competing sealed branch and counted**"), `merge.md`
rule 4 (same wording), and `reconciliation.md` Matrix 4 ("a burial against a fork that holds a
witnessed sealed branch … **permanently terminalizes the prefix** → Disputed"). Read alone, these
say: anyone who authors a doomed burying seal against a fork carrying an accepted sealed branch
thereby _makes the prefix Disputed_. That would contradict the system's own brick-cost claim (a
second accepted seal takes a witness double-sign) and would hand the _victim_ of a takeover — or
anyone holding a spent-position signing key — a unilateral terminalize-the-prefix button. The design
does not actually have this hole: `merge.md`'s "Acceptance precedes the outcome — deferred-pending"
paragraph states globally that every merge transition names what an **accepted**
(threshold-witnessed) batch does, and an honestly-declined burial attempt stays deferred-pending and
dropped — so "counted" only ever applies to a burying seal that was itself accepted (the
propagation-lag / partition entrance the doctrine already prices). I verified this reading is the
only one consistent with `compromise.md`'s point-of-no-return analysis, `verification.md`'s
acceptance gating, and the glossary's "Disputed needs ≥ 2 **accepted** sealed branches." But the
load-bearing sentences themselves carry no "once accepted" qualifier, and the misreading produces an
unsound implementation (counting unaccepted burial attempts toward Disputed) that would pass a
casual read of the doctrine paragraph. The same unqualified phrasing recurs at every restatement —
`kel/merge.md` (rule 4 and the on-arrival section), `iel/merge.md` (rule 5), `sel/merge.md` (guard
step 4), `kel/reconciliation.md` (Matrix 4 and its convergence bullets), and `iel/reconciliation.md`
(convergence) — so the fix is one clause applied consistently: "retained as a competing sealed
branch and, **once accepted**, counted (a witness-declined attempt stays deferred-pending,
dropped)."

**4.2 (Minor) A garbled constraint name in `kel/compromise.md`.** "Burial is any seal-advancer's
doing" says a `Wit` carries "the must-change-substrate/federation/witnesses constraint." Every other
statement of this rule (`events.md`, `merge.md`) says a user `Wit` must change at least one of
`federation` / `witnesses`; "substrate" appears to be a stray word. Trivial, but the sentence is
stating a validation rule, so it should read cleanly.

**4.3 (Note) "At the last seal" vs. "wherever their seals sit."** The Disputed condition is phrased
in two registers — "≥ 2 accepted sealed branches **at the last seal**" (several places) and "counted
per branch, **wherever their seals sit**" (the canonical definition). These are consistent once "at
the last seal" is read as "in the window at or above the last clean seal," which the terminology
section supports, and I found no passage where the shorthand changes the verdict. Noting it only
because the shorthand's surface reading ("both seals sit at the seal's own serial") is exactly the
same-serial restriction the canonical definition explicitly rejects; a reader who quotes the
shorthand out of context inverts the rule.

## 5. Identity event log (IEL)

Read: `iel/log.md`, `iel/events.md`, `iel/verification.md`, `iel/merge.md`, `iel/reconciliation.md`,
`iel/delegation.md`, against `event-shape.md`.

The IEL set correctly reuses the KEL machinery and adds the mixed-chain and threshold layers without
contradicting it. Verified in detail:

- The threshold-vector bounds are stated identically in `event-shape.md`, `iel/events.md`, and the
  doctrine (security floor ≥ 2, recoverability ceiling ≤ roster − 1 with the advisory-at-2 /
  hard-at-≥ 3 split, authorization floor > roster/2, never-emptied, cap 32), and the arithmetic
  works at every roster size I checked (1, 2, 3, 4, 32). The singleton and two-member special cases
  match the residuals catalog's entries.
- The kind-strict anchor matrix is stated three times (event-shape, `iel/events.md` twice — prose
  and diagram) and once from the SEL side; all four agree, including the two-sided back-check
  argument (the kind → role allowlist protects directly-consumed roles; the anchor matrix
  back-checks `anchors`).
- The per-kind threshold pricing (`Ixn` ← use; `Evl`/`Rev`/`Wit`/`Trm` ← govern; `Ath`/`Dth` ←
  authorize) is identical everywhere it appears, and the claim that IEL validity needs no
  higher-layer input follows.
- The facet-dependent `Wit` (user rebind vs. federation governance) is handled with unusual care —
  the requirement that the root facet be established before any `Wit` payload is read, on every path
  including token resumes, is stated in four places and consistently; the failure it prevents (a
  governance roster delta smuggled onto a user `Wit`) is real, since the role allowlist is the only
  gate on directly-consumed roles.
- The `cut`-`Evl` atomicity argument (bury and evict in one event, or the still-rostered member
  re-forks the resolved tip) is sound, and the outgoing-quorum pricing (an `Evl` cannot lower its
  own gate before cutting) closes the self-weakening order dependence.
- The `kills[]` machinery — target formulas, the mirror rule (non-lineaged / lineaged / `:content`),
  the O(1)-then-fail-secure-walk shape, the `Trm.pin`-points-at-the-kill shortcut — is consistent
  across `iel/events.md`, `iel/verification.md`, `delegation.md`, `tags-and-topics.md`, and the
  doctrine.
- The reconciliation matrices mirror the KEL's cell-for-cell with the correct mixed-chain additions;
  I checked the cells against `iel/merge.md`'s routing rules and found no divergence.
- The delegation walk is correctly bounded (per-candidate scalar state, walk up the committed path,
  `MAXIMUM_DELEGATION_DEPTH = 8` backstop), and the delegating-link signpost design — the marker as
  a re-verified pointer that grants nothing on its own, with authority always in `Ath.delegates` —
  is checked from both ends (`delegation.md` and `iel/events.md`) and coheres. The discoverability
  of a delegating-link address (derivable from two public prefixes) is consistent with the residuals
  catalog's confirm-a-known-subject entry rather than contradicting the privacy posture.

**5.1 (Minor) "Witnesses mandatory iff federated" contradicts "there is no direct mode."** The IEL
per-kind table in `event-shape.md` says the `Icp` manifest carries "`witnesses` mandatory **iff
federated**." But the same document's footnote — and `iel/events.md`, and the doctrine — say every
identity is federation-witnessed and an `Icp` omitting the binding is malformed (no direct mode).
The only non-`Icp`-federated chain is the federation IEL itself, which incepts `Fcp` (where
`witnesses` is required too). The "iff federated" hedge reads as a vestige of an earlier design that
had a direct mode; as written it invites an implementer to make `witnesses` conditional on something
that can never vary. Recommend "req" with no qualifier.

**5.2 (Note) The initial-consent asymmetry is stated consistently but never motivated.** Initial
members consent to an `Icp` via KEL `Rot`s (tier 2); later joiners consent to an `Evl` via KEL
`Ixn`s (tier 1, counted toward consent-of-added only). Both documents state both sides consistently,
and the joiner split has a stated rationale (keeping joiner consent out of `t_govern`). What is
never said is why founding consent must be tier-2 while joining consent is tier-1 — presumably
because inception is itself the tier-2 establishment act and each founder co-establishes rather than
merely consents. One sentence would preempt the "why do founders pay more than joiners" question.

**5.3 (Note) The `roster()` live-act gating table is a good consistency artifact.** The
three-projections table in `iel/verification.md` (state × region × effective-SAID × roster × T1/T2
gate) encodes the freeze-T1 / seal-out-with-T2 rule compactly, and I verified each row against the
doctrine's freeze-origination and divergence rules. The rule that any T2 act may seal a forked
identity out (because a content fork's branches are T1-authored, so allowing T2 to seal out only
hands recovery to higher authority) is a correct argument.

## 6. SAD event log (SEL)

Read: `sel/log.md`, `sel/events.md`, `sel/verification.md`, `sel/merge.md`, `sel/reconciliation.md`,
against `event-shape.md` and the IEL side of the anchor matrix.

The SEL set is the most intricate of the three logs (two independent state inputs — its own
witnessed divergence and inherited owner-IEL deadness) and it holds together. Verified in detail:

- **The self-witnessing argument is sound.** The claim that an owner-IEL anchor cannot prevent a SEL
  fork (an anchor is an opaque digest, so one IEL event can name two competing SEL events and a
  partial holder sees a linear chain with the wrong tip) is a genuine hole the self-witnessing
  design closes; the batched-anchor rule (a SEL event is only committed with its owner-IEL anchor,
  and acceptance requires the anchor itself to be accepted) closes authorship-forgery at the same
  stroke. Both directions are argued, and the consumer's independent re-derivation keeps
  end-verifiability off the witness.
- **The "an accepted sealed branch is never severed" lemma checks out.** A SEL sealed event's anchor
  is an IEL sealed event; accepted IEL sealed events are never buried; SEL acceptance gates on
  anchor acceptance — so severance can never reach an accepted SEL sealed branch, which is what
  makes "Disputed is never downgraded by severance" and the two "unreachable by construction" rows
  in reconciliation Matrix 2 true. I traced the dependency chain across four documents and it is
  complete and circular-free.
- **The ≤ 1-content-`Ixn`-per-owner-IEL-`Ixn` rule is now enforceable as stated** — `sel/events.md`
  and `sel/verification.md` give the concrete mechanism (anchor-identity dedup during the SEL walk),
  distinct from the inert re-anchor guard. This closes what would otherwise be a stated rule with no
  performable check.
- **The `Sea` existence argument is complete.** The live-and-locked anchor case (a
  witness-compromise SEL content fork whose anchoring IEL event is canonical but below the IEL's
  seal — beyond both severance and IEL re-burial) genuinely requires a SEL-side neutral advancer;
  the case analysis in `log.md` and reconciliation Matrix 2 covers all three placements of the
  losing anchor (dead / live-at-or-above-seal / live-and-locked).
- **The lineage machinery is consistent everywhere** — the walk (stop at lowest live, advance on
  `Trm`/Disputed/severed, gap ends, cap 64 inclusive), the lineaged-vs-non-lineaged-vs-`:content`
  target mirror, and the honestly-flagged feature-layer obligation (a rescission must declare the
  matching lineaged target; the primitive does not backstop it) — which the residuals catalog lists
  verbatim as owed work.

**6.1 (Minor) The SEL `Icp` taxonomy row's tier and count labels describe only the content case.**
`event-shape.md` and `sel/events.md` both list `Icp` as tier 1, count `t_use`. But the documents are
equally clear that the `Icp` is unsigned, recomputable, never anchored, and "proves nothing on its
own" — establishment authority is the v1's anchor, which for a kill lookup is a `Rev`/`Dth`
(`t_govern`/`t_authorize`, tier 2) and for a value lookup an `Ath` (`t_authorize`, tier 2). The
glossary even says a value lookup is "established `{Icp, Gnt}` **at T2**." So the `Icp` row's "tier
1 / `t_use`" is accurate only for content SELs and vacuous-to-misleading for lookups; a reader
pricing "what does it cost to incept a lookup SEL" from the taxonomy table gets the wrong answer.
Recommend footnoting the row ("the `Icp` itself carries no authority; the establishment is priced by
the v1's anchor") or splitting the cell.

**6.2 (Note) The `Severed` rejection is a justified vocabulary extension.** `sel/merge.md` adds a
fifth rejection kind absent from the KEL/IEL vocabulary. This is correct rather than inconsistent
(severance exists only on the SEL), and the routing-order argument for severance-before-seal-cap
(name the dead anchor, not a mis-diagnosed stale tip) matches the diagnostics doctrine.

## 7. Federation, witnessing, and transport

Read: `substrate/federation/bootstrap.md`, `substrate/federation/witnessing.md`,
`substrate/federation/topics.md`, `substrate/infrastructure/mesh-transport.md`.

This layer supplies the assumptions everything in sections 4–6 leaned on, and I checked each
borrowed claim against its source here:

- **The witness-side seal-cap mirror is explicitly stated** ("A below-seal sealed event is declined
  — the witness mirrors the seal-cap"), with the correct two-layer framing: the decline is the fast
  prevention layer, and the guarantee is the walk (dead on ascent), so even a signed below-seal
  straggler cannot overturn the live seal. This is the passage the KEL/IEL/SEL
  no-collusion-no-dispute arguments depend on, and it says what they need it to say.
- **The selection function is pinned byte-exactly** (stable-sort by position-keyed digest over the
  currency-gated membership), competing siblings inherit the same pin and so the same set, and the
  one exception — a rebind declares its own pin and selects a different roster — is called out in
  the same section, matching the doctrine's cross-federation dispute case exactly.
- **The currency gate and clock compose without contradiction**: the gate governs roster membership
  (fires on add/cut, not pure rotation), the clock governs key-time-validity, receipts are counted
  as-of the event's own recorded binding forever (no re-witnessing), and the no-grace-window rule is
  given the right rationale (any grace revives the pre-cut backdate sliver). The 365-day
  auto-expiry, the at-risk flag, the all-windows-lapse recovery (stale-but-recoverable via a
  catch-up rotation judged under its own new windows), and the `now + CLOCK_TOLERANCE_BAND` sanity
  cap all match their residuals-catalog entries.
- **The witnessed-time definition (threshold-th smallest receipt time) is analyzed honestly** —
  including the one direction an adversary can move it (later opening boundary → fail-secure
  refusal; later closing boundary → the already-priced backdate sliver) and the monotone-downward
  property under accumulating receipts.
- **The federation bounds are arithmetically consistent everywhere**: `signers ≥ 3`, exclude-self
  `signers ≤ |roster| − 1`, the recoverability cap `threshold ≤ min(|roster| − 2, signers − 1)`, the
  `|roster| ≥ 4` floor with the worked `{threshold 2, signers 3}` minimum, and the three-to-govern /
  two-to-witness worked example. `shapes.md`'s generic bound is the correct superset with the
  federation tightening correctly deferred here.
- **The bootstrap's no-self-witnessing argument is sound** — the authorization/trust-rooting split
  is real (founder anchors satisfy the ordinary inception threshold; trust is only ever the
  configured prefix), and the "circular theatre" rejection of a self-witnessing carve-out is the
  right call, stated with the right reasoning.
- **The transport's nonce argument is correct**: per-direction keys derived under a domain-separated
  context, strictly increasing per-direction counters, no mid-session rekey needed within counter
  and volume margins, forward secrecy from the ephemeral encapsulation key, and authentication bound
  to the witnessed key state. The suite (ML-KEM-1024 + AES-256-GCM + ML-DSA-87 + blake3) matches
  every other statement of it (doctrine, topics, residuals).

**7.1 (Minor) `sad.md` promises the store rejects event kinds; the store document does not exist
yet, and `kinds.md` carries the enforcement in the meantime — but one link chain dead-ends.**
Several documents (`sad.md`, `custody.md`, `availability.md`, `kinds.md`, `compaction.md`) defer
storage-side enforcement to `substrate/infrastructure/vdtid.md`, marked forthcoming. That is a
legitimate forward reference and consistently flagged. The residual observation is only that the
serve-by-SAID allowlist — a load-bearing privacy rule ("nothing whose SAID must stay opaque is
fetchable") — currently lives in a catalogue document (`kinds.md`) rather than a doctrine document,
and its enforcement point is wholly in the forthcoming file. Worth keeping on the forthcoming-work
list as a soundness-relevant gap rather than a plumbing gap.

**7.2 (Note) "Witnesses are reporters, not deciders" is honored throughout.** I specifically looked
for places where a verdict quietly depends on witness say-so rather than data. The two candidates —
the beacon (explicitly a propagation channel, hint-not-authority in the stale-pin pre-check) and the
receipt-count shortcut (the carried `threshold` is a hint checked by exact match against the
chain-committed config) — both resolve on the data side. The one place trust does attach to
infrastructure — mesh confidentiality (lookup prefixes visible to federation members) — is declared
as exactly that in both `sel/log.md` and the residuals catalog.

## 8. Document authorization (policy)

Read: `policy/policy.md`, `policy/documents.md`, `policy/evaluation.md`.

The policy layer is small and clean, and its hard parts are handled with more care than most policy
languages get:

- **The set-packing satisfaction rule is the standout.** The rule that a signer fills at most one
  slot across a threshold's branches — making satisfaction existential over signer-to-branch
  assignments rather than a greedy per-branch pass — is exactly right, and the document correctly
  identifies both failure modes of the naive approach (wrongful denial, order-dependent disagreement
  between evaluators) and bounds the search fail-secure (budget exhaustion denies, so
  differently-budgeted verifiers differ only toward denial). The per-identity-max weight rule and
  the `and`-over-overlapping-pools caveat are the right companion rules, and the worked
  `thr(2, [pol(A), pol(B), pol(C)])` example makes the cross-branch no-double-count rule concrete.
- **The `issuerPin` earliest-anchor proof holds.** The claim that the pinned anchoring position is
  provably the earliest possible anchor (an earlier anchor would need a hash cycle, since the
  commitment embeds the credential's identifier which embeds the pin) is correct — I traced the
  cycle argument and it closes the tier-inversion re-anchor attack (`documents.md` names the attack:
  a later tier-1 re-anchor after a tier-2 revocation must never move the as-of forward).
- **The as-issued/current-trust split is consistently maintained** — the mandatory to-tip freshness
  step, the three-part report (anchor status / region / freshness), and the
  below-seal-anchors-stay-valid rule all match the token semantics in the primitive verifiers and
  the doctrine's pre-seal verifiability; the residuals catalog carries the matching entry
  ("as-issued resolve skips the to-tip step") at the right severity.
- **The unknown-construct rule** (an unrecognized policy term denies the whole policy — never
  skip-and-continue) is the correct forward-compatibility posture and is stated once, clearly.
- The per-hop grandfather rule (each hop judged on its own chain, no cross-chain clock) matches
  `delegation.md` and the residuals catalog's delegation-scope entries (naive rescission,
  route-around, no single-credential revoke).

No findings in this group beyond one observation:

**8.1 (Note) `id(X)` resolving `t_use` is stated with its rationale, in the right place.** The
choice that `id(X)` means the use quorum (issuance is a use act) with higher bars composed across
identities rather than by reinterpreting `id`, appears in `policy.md` with the rationale, and
`documents.md` repeats it consistently. This is the kind of choice that drifts between documents; it
has not.

## 9. Protocol primitives (envelope, exchange, key directory, group key, membership, authored DAG)

Read: `protocols/essr.md`, `protocols/ipex.md`, `protocols/receive-key-directory.md`,
`protocols/group-key.md`, `protocols/membership.md`, `protocols/authored-dag.md`.

These six are well-factored — each states its boundary explicitly, and I checked every "that is not
this primitive's job" claim for a matching owner on the other side. All of them have one: key
resolution → the directory; currency → the exchange feature; replay → IPEX's envelope or the mail
dedup; enumeration → group-key's roster vs. membership's per-requester check; the fork rule's
resolution → the feature's root anchor and removal bound. No orphaned responsibilities found.

Specific soundness checks that passed:

- **ESSR's two-binding argument is correct and correctly attributed.** The four guarantees, the
  recipient-key-substitution and strip-and-re-sign attacks the two bindings close, the
  per-message-key-makes-the-nonce-safe argument, and the explicit non-goals (replay, identity
  hiding, currency) are all stated accurately; the open-side check order (recompute the SAID before
  trusting the signature over it; assert recipient-is-me; check the inner sender matches the
  envelope sender) is the right order and complete.
- **IPEX's one-signature-two-jobs design holds.** The `grant` signature simultaneously proving
  ownership (required signer = the committed issuee for a targeted SAD, not the self-declared
  discloser) and binding `{audience, nonce, created}` is checked against each attack in the "why it
  holds" list, and each is genuinely closed. The signed-not-anchored decision for presentations,
  with its anti-surveillance rationale and the opt-in anchored mode, is coherent with the chain
  layer. The timestamp-as-cache-bound-never-trust-input rule is exactly right, and the
  cache-retention residual is declared.
- **The directory's tier claim is consistent**: publishing or changing a receive key is
  reserve-backed (`Gnt ← Ath`), so a stolen signing key cannot redirect mail — matching the SEL
  value-must-ride-a-`Gnt` rule and the residuals catalog's forced-dead-receive-key entry. The
  lineaged-target obligation is restated here with the directory correctly identified as the first
  consumer carrying it.
- **Group-key's independent-epochs model** (no derivation between epochs; removal = exclusion from
  future wraps; joiner reads nothing past; hardware bounds a still-a-member compromise to live
  access) is internally consistent, and the per-writer subkey rule is correctly justified (nonce
  partitioning under a many-writer shared key) with the right disclaimer (a subkey authenticates no
  one; authenticity is the signature).
- **Membership's disclose-your-own-`{nonce, data}` fix makes the fail-secure walk performable by the
  store** — with the check that the disclosed `data` names the identity the live signature resolves
  to, so a leaked disclosure is not a bearer token. This closes the is-the-check-performable
  question that would otherwise silently force fail-open, and the document says so in as many words.
- **The authored-DAG lane bracketing is closed at both ends**: the anchored root (rejecting fresh
  parentless roots, including the two-anchored-markers-in-one-period malformation, which even a
  colluding governing identity cannot exploit) and the witnessed removal `bound` (a local interval
  check needing no fork detection). The honest analysis of what remains — the dormant-current-member
  backdate-within-a-held-window — matches the residuals catalog's entry word for word.

**9.1 (Minor) Two names for the same set of grant kinds.** `membership.md` says a keyed group's
roster entries ride "read-gated opaque references" and membership changes are "`Gnt ← Ath`,
`t_authorize`" — the group-key roster and the membership grant chain are both `Gnt`-sealed SEL
structures, and `tags-and-topics.md` gives group-key its own `roster` topic while the grant values
in `kinds.md`/`shapes.md` list `chat-membership` and the three `document-*-membership` kinds plus
`groupkey-epoch-key` — but no grant-value kind for the group-key **roster** entries themselves. If
the bounded wrap roster is a distinct SEL (it has its own topic) its sealed entries presumably need
a grant-value kind of their own, which the catalogue does not list; if instead the roster rides the
membership grant chain, the separate `vdti/groupkey/v1/topics/roster` topic is unexplained. This
looks like a small catalogue gap left for the group-key encode rather than a design conflict, but as
written the two documents leave the roster's concrete carrier ambiguous.

## 10. Features (credentials, exchange, shared documents)

Read: `features/credentials.md`, `features/exchange.md`, `features/shared-documents.md`.

The feature layer composes the primitives without redefining any of them, and every mechanism it
leans on resolved to a matching statement in the layer that owns it:

- **Credentials**: the issuance-commitment formula, `issuerPin` semantics, the `{Icp, Trm}`
  revocation lookup, the fail-secure walk, the terminated-issuer freeze (and its
  revoke-before-terminating discipline), bearer redemption-as-revocation, and the tip-atomic
  mint-and-anchor step all match `custody.md`, the IEL/SEL docs, the doctrine, and the residuals
  catalog exactly. The claim-gating design (issuer-precomputed blinded predicates, uniform bracket
  sets for presence-privacy, renewal on threshold-crossing) is internally consistent and honest
  about there being no claims language in the protocol. The reusable-transferable-bearer
  impossibility argument is correct.
- **Exchange**: the sender-key currency check (two axes — IEL establishment interval × device KEL
  window, each bounded by witnessed times), the post-decrypt required mail timestamp with
  refuse-on-absent, the payload-endpoint gates (upload authenticated, fetch load-bearing), the
  IEL-roster-not-`t_use` polling rule, and the chat lane machinery all match the witnessing,
  group-key, membership, and authored-DAG documents. Every chat/exchange residual in the residuals
  catalog (dormant-member backdate, open-epoch future-dating with its non-monotone-validity wrinkle,
  one-device chat signature, home-nodes-see-the-writer-set, batch-anchor co-send linkage) appears in
  the feature document with the same content — the two surfaces were clearly maintained together.
- **Shared documents**: the honored predicate (`F_x ≤ V_x ≤ B_x`, all on the editor's own chain) is
  correctly clock-free and closed against backdating in both directions, including the subtle
  hash-preimage floor argument (a version cannot predate its own grant because the anchor commitment
  embeds the version identifier which embeds the grant reference). The grant-must-be-sealed rule
  ("skip the seal-locate and the gate is a total bypass — so it is stated here, not left to
  inference") shows exactly the enforceability discipline a reviewer wants to see, as does the
  disjointness pass's honest cost accounting (O(chain), enforceable because grants are public
  structural events, withheld-reads-conservative). The freeze construction (bound-all + terminate,
  permanent because grant chains carry no lineage) is consistent with the SEL lineage rules.

No new findings in this group; the one observation is that the `MAXIMUM_GRANT_ADDS = 64` constant
appears only in `shared-documents.md` — appropriate, since the feature owns it, and it follows the
protocol-constant conventions (a power of two, fixed not tunable).

## 11. Cross-cutting consistency (glossary, top-level documents, terminology)

Read across everything above, plus the root `MODEL.md` and `USES.md`.

**11.1 (Major) `MODEL.md` tells an owner they can convert a reserve-theft takeover into a dispute;
the design says the opposite.** In "The one guarantee to remember," `MODEL.md` says: "On a chain the
owner is watching, the owner sees a rotation they didn't make and **raises it (turning it into a
fork → disputed → start fresh)**." The design surface is explicit that this is exactly what cannot
happen: the thief's rotation is a witnessed linear extension, the owner's later competing seal is a
**first-seen-declined late sibling** that "forces nothing" (`iel/log.md`, `kel/compromise.md`, the
reserve-theft residual: "the owner's later attempt is a late, declined sibling. There is no
structural veto"), and the prescribed response is reincept plus out-of-band notification
(`monitoring.md`, residuals). The one structural way an owner _can_ force a Disputed reading — a
cross-federation rebind, honestly witnessed by a disjoint witness set — is mentioned once in
`iel/log.md` with the caveat that "that recovers nothing, and reincept is the recourse either way,"
and it is not what the `MODEL.md` sentence describes. Since `MODEL.md` is the plain-language rules
document a user or evaluator will act on, this is a real narrative-contradicts-canon defect, not a
simplification: a victim following it would attempt an on-chain counter-rotation the witnesses will
decline. Recommend rewording to match the design ("the owner sees the rotation, reincepts under a
new prefix, and warns relying parties out of band; the takeover reads as an ordinary rotation to
third parties").

**11.2 (Note) Terminology discipline is strong and the glossary earns its keep.** The near-collision
hazards the design creates for itself — witnessed vs. accepted, sealing vs. sealed, `Terminated` vs.
`Terminal` vs. `Trm`, the two senses of "retain," "governance" in the narrow sense, floor-as-count
vs. floor-as-position, the three identifier families (kinds, tags/topics, gossip topics) — are each
explicitly disambiguated in the glossary or the owning document, and I found no passage that uses
one against its declared sense. The one wobble I found is recorded as finding 4.3.

**11.3 (Note) The protocol constants are consistent everywhere they appear.**
`MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_MANIFEST_LIST = 128`, `MAXIMUM_UNSEALED_RUN = 64`,
`MINIMUM_PAGE_SIZE = 129 = 2·64 + 1`, `MAXIMUM_DELEGATION_DEPTH = 8`, `MAXIMUM_SEL_LINEAGE = 64`
(inclusive), `MAXIMUM_GRANT_ADDS = 64`, `MAXIMUM_WITNESS_KEY_WINDOW = 365 days`,
`CLOCK_TOLERANCE_BAND = 1 minute` — each is defined once with the same value at every mention, and
the derived relationships (page arithmetic; the federation bounds' joint satisfiability at roster 4)
hold.

**11.4 (Note) The root `README.md` and `USES.md` make no claim the design surface contradicts.** The
marketing-level claims (verify-with-no-network for authenticity, fresh-read-for-revocation,
fail-secure default with application fail-open opt-out, no watcher infrastructure) each match the
doctrine. The KERI comparison sentence appears identically in `README.md` and `system-thesis.md`.
