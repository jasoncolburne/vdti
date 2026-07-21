# Cold design review — 2026-07-21 (second pass)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_2.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion.

> you can ignore the design/reviews directory

## About this review

This is a cold review: it was produced by reading the current design documents from scratch, in the
reading order given by `docs/design/README.md`, without consulting any earlier review in this
directory. The goal is to judge the design as written, on two axes:

- **Correctness / soundness** — do the stated rules actually deliver the properties the design
  claims? Is every stated check one a verifier can actually perform? Does anything break when an
  attacker, rather than an honest participant, supplies the input?
- **Consistency** — do the documents agree with each other? Where two documents describe the same
  rule, do they describe the same rule?

Each finding says which documents it comes from, quotes or points at the exact text, and explains
the problem in plain language. Findings are graded:

- **[serious]** — if the reading is right, a stated security property does not hold, or two
  documents disagree on something that changes verifier behavior.
- **[moderate]** — a gap or ambiguity that a careful implementer would have to resolve by guessing;
  the guess could go wrong.
- **[minor]** — wording, drift, or small inconsistencies that do not change behavior but will
  mislead a reader.
- **[note]** — an observation worth recording; not a defect.

**Coverage.** All 41 documents in the reading order were read in full, plus `glossary.md`,
`residuals.md`, `monitoring.md`, and the top-level `README.md`, `MODEL.md`, and `USES.md` — every
design document in the repository outside `docs/canon/` (working notes, deliberately not consulted)
and this reviews directory.

## Shared vocabulary used in this review

Plain-language versions of the handful of design terms the findings below need. (The design's own
glossary is the canonical source; these are simplified restatements.)

- A **chain** is an append-only log of events, each linking to the one before it. Three kinds exist:
  a device's key log (KEL), an identity's log (IEL, a group of devices acting by threshold), and a
  data log (SEL, owned by one identity).
- An event is either **content** (ordinary, forgeable with the everyday signing key — "tier 1") or
  **sealed** (key changes, membership changes, grants, kills — forgeable only with a separately-held
  reserve key, "tier 2"). Sealed events also advance the chain's **seal**: everything at or below
  the most recent seal is locked and can never be rearranged.
- A **fork** is two different events claiming the same position. Content forks are **recoverable**:
  a later sealed event "buries" the losing content below the new seal, and everything built on the
  loser dies with it. Sealed events can never be buried.
- **Witnesses** (a federation) sign a receipt for the first valid event they see at each position.
  An event is **accepted** once a threshold of the selected witnesses signed it. Because the
  threshold is a strict majority, two rival events of the same kind at one position can never both
  be accepted without witness misbehavior.
- The chain's per-position state is one of **Active** (one clean tip), **Forked** (a live,
  recoverable fork), **Disputed** (two accepted sealed branches — unrecoverable; the identity must
  start over under a new identifier, called **reincepting**), or **Terminated**.
- The **effective SAID** is a one-value fingerprint of a chain's state: the tip's hash when the
  chain is clean, or a special "forked"/"disputed" marker when it is not.

## Summary of findings

Two serious findings, both consistency defects on load-bearing rules rather than design flaws; one
moderate; a handful of minors. Full detail in the group sections.

| #   | Grade    | Finding                                                                                                                                                                                                                                                                                                                                            |
| --- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 | serious  | The design surface states two incompatible answers to what a fork with exactly **one** accepted sealed branch reads as (resolved-to-Active with the content buried, versus Forked-for-everyone). ~10 stale sites across 7 files, including inside both correctness-proof documents; the resolved-to-Active model is demonstrably the intended one. |
| 1.2 | serious  | The "no self-burial" admission guard is stated in five documents but is undecidable, vacuous, or recovery-breaking under every candidate reading — and its one concrete application (`sel/reconciliation.md` Matrix 3) contradicts the Position-3 burial rule in the same file. Delete it or replace it with a precise, data-only rule.            |
| 8.1 | moderate | `MODEL.md`'s "core rule" section draws the keep-both / take-first line at single-key versus group, where the design draws it at content versus sealed; its recoverability claim for single-key rotation conflicts contradicts the KEL brick analysis.                                                                                              |
| 1.3 | minor    | `protocol-doctrine.md` states the authority-threshold floor "≥ 2" unconditionally, then the singleton exception; `iel/events.md` carries the exception cleanly — doctrine-side drift only.                                                                                                                                                         |
| 1.4 | minor    | `protocol-doctrine.md`'s own table of contents omits its "Caching and continuation" section.                                                                                                                                                                                                                                                       |
| 2.1 | minor    | `sad.md` equates "prefix-deriving SADs" with chain inceptions; `said.md` (correctly) adds the shared-document constitution V0.                                                                                                                                                                                                                     |
| 2.2 | minor    | `shapes.md`'s witness-config bound reuses `\|roster\|` to mean the federation's roster without saying so.                                                                                                                                                                                                                                          |
| 3.1 | minor    | `kel/log.md` states the Forked definition twice, once correctly and once in the stale form (a 1.1 site, listed for the sweep).                                                                                                                                                                                                                     |
| 3.2 | minor    | "≥ tier-2" wording nit in `iel/events.md` (there is no tier above 2).                                                                                                                                                                                                                                                                              |
| 4.1 | minor    | Witness-receipt field spellings differ between `shapes.md` (camelCase) and `witnessing.md` (snake_case) — load-bearing for a hashed, signed record.                                                                                                                                                                                                |
| 5.1 | minor    | "A shared policy must evaluate identically everywhere" versus an unpinned per-verifier work budget — deny-on-budget can differ at the margin (fail-secure, but the claim overreaches).                                                                                                                                                             |
| 8.2 | minor    | The `issuers` list and credential `terms` records are named by the kind catalogue's serve rule but have no kind entries and no forthcoming-shapes rows.                                                                                                                                                                                            |

## Group 1 — Orientation and cross-cutting doctrine

_(system-thesis.md, glossary.md, protocol-doctrine.md, residuals.md, monitoring.md)_

These five documents were read in full. The thesis, glossary, residuals catalog, and monitoring note
are in strong shape: internally consistent, honest about limits, and the residuals catalog's risk
arithmetic checks out line by line (I verified every Severity × Exploitability product against its
stated band — all correct). The doctrine document is the one with problems, and they cluster on a
single load-bearing question.

### Finding 1.1 [serious] — the documents disagree on what a fork with exactly one accepted sealed branch reads as

This is the most consequential finding of the group, because the answer decides what a relying party
does: trust the chain (treat it as Active, follow the sealed branch) or refuse it (treat it as
Forked, grounding no new trust). The design surface currently states both answers.

**The "it resolves to Active" position** (a lone accepted sealed event buries a competing content
event at the same position, immediately and automatically):

- `protocol-doctrine.md`, "Cross-node races converge data-locally": "A **seal-advancer siblinging a
  content event buries it** — the content's parent sits below the new seal, so it is dead on ascent
  — and that seal-advancer **becomes the tracked seal**: the chain reads **Active**."
- `protocol-doctrine.md`, the "Locked" definition: the tracked seal is "the most recent
  seal-advancing event **with no competing accepted sealed sibling** (a content sibling is buried
  below it, not a competitor)" — so a sealed event with only a content rival still becomes the lock,
  which is the Active reading.
- `glossary.md`, the Forked chain state: "a live **content-only** fork (no accepted sealed branch) …
  a lone accepted sealed branch buries the content and reads Active."
- `residuals.md`, rotation-reserve theft: "if the adversary rotates at the identity's next position
  first, the owner's later attempt is a late, declined sibling. **There is no structural veto**" —
  i.e. the thief's accepted rotation stands and the chain reads clean.

**The "it reads Forked" position** (one accepted sealed branch plus a content branch is still a live
fork, visible to everyone):

- `protocol-doctrine.md`, the "Forked" state definition: "two **distinct** events at one serial,
  with **≤ 1 sealed branch** past it" — the "≤ 1" bucket includes the one-sealed-branch case — and,
  explicitly: "A lone sealed branch a party did **not** author **reads Forked node-agnostically**,
  yet still forces **that** party's reincept."
- `protocol-doctrine.md`, "Effective-SAID comparison": the synthetic (marker) form applies when
  there is "**no single tip** (an unresolved fork — a live content fork, **or ≥ 1 sealed branch past
  it**)" — again treating one sealed branch as unresolved.
- `system-thesis.md`, the federation-convergence decision tree: the "accepted sealed branches at the
  last seal ≤ 1" arm is labeled "**Forked** (recoverable)" — a bucket that includes the
  one-accepted-sealed-branch case.

Both positions cannot hold; the walk must return one answer. The contradiction sits **inside**
`protocol-doctrine.md` itself (its "Forked" bullet against its own "Locked" bullet and its
cross-node-races paragraph), not merely between documents.

**Why the "resolves to Active" model appears to be the intended one.** The design's own resolution
principle — "divergence is resolved by tier, not by identity; chain data cannot tell the rightful
operator from an adversary" — makes the Forked reading unsupportable as stated: the recovery story
_requires_ that a sealed event bury an accepted (witnessed) content rival, because that is exactly
how an honest owner buries a signing-key thief's forged-but-witnessed content. A rule that instead
kept the chain Forked whenever an accepted sealed branch faces an accepted content branch would also
freeze every legitimate recovery of a witness-compromise content fork — the same shape with the
roles reversed, which no verifier can distinguish. The residuals catalog ("no structural veto") and
the glossary agree. The cost of that model is honestly recorded in `residuals.md`: a reserve-theft
victim gets no in-band distress signal; detection is monitoring plus out-of-band warning.

**Recommendation.** Normalize all four "Forked-leaning" passages to one authoritative statement:
Forked = a live fork with **zero** accepted sealed branches; exactly **one** accepted sealed branch
= resolved (Active, or Terminated when it is a terminal event), with "the non-author of that sealed
branch must reincept" kept as an operational consequence, not a chain state; **two or more** =
Disputed. Concretely: (a) the Forked bullet's "≤ 1 sealed branch past it" and its "reads Forked
node-agnostically" sentence; (b) the effective-SAID "no single tip" parenthetical's "≥ 1 sealed
branch past it" (should be the disputed threshold, ≥ 2, or simply "an unresolved fork"); (c) the
system-thesis tree's "≤ 1 → Forked (recoverable)" label (the = 1 case is resolved, not Forked); (d)
the divergence decision tree's N=1 "on your retained branch? → yes" arm, which points at a node
describing an _unresolved_ fork's recovery even though a one-accepted-sealed-branch chain is already
resolved by that seal.

**Verified against the KEL primitive (Group 3) — the finding is confirmed and wider than first
stated.** The KEL documents settle which model is intended, and they carry the same stale phrasing
in several of their own passages:

- Authoritative statements of the "one accepted sealed branch resolves to Active" model:
  `kel/log.md` state table ("a fork **carrying** an accepted sealed branch has that seal bury the
  content and reads Active, not a live fork"); `kel/merge.md` transitions table ("0 → Forked; a
  single accepted sealed branch buries the content → Recovered/Active; ≥ 2 → Disputed");
  `kel/verification.md` `region()` ("a **single** accepted sealed branch buries the content and
  reads **trusted** — a reserve-theft takeover you did not author is clean on-chain … **not surfaced
  here**") and its terminal-state rule; `kel/reconciliation.md` invariant 4 and its proof-states
  table.
- Stale "≤ 1 / ≥ 1 sealed branch" or "reads Forked" passages that contradict the above:
  `protocol-doctrine.md` (the three sites in the original finding); `system-thesis.md` (the tree
  label); `kel/log.md` §Forked versus Disputed ("**Forked** — at most one branch carries a sealed
  event past the fork"); `kel/merge.md`'s routing flowchart (the "Forked (≤ 1 sealed)" node —
  contradicting the transitions table forty lines above it); `kel/reconciliation.md`'s merge-outcome
  cell vocabulary ("**Forked** — a fork with **one sealed branch** (or a content fork) forms or is
  joined"), its effective-SAID section ("a live content fork, or ≥ 1 sealed branch past it" as the
  no-single-tip case, and "`forked` (≤ 1 sealed branch past the fork)"), and — most seriously for a
  correctness proof — **completeness-matrix row 5** ("**sealed** … a lone unretained branch, no
  burial → one sealed branch → **Forked**-frozen (recoverable only by its author; reincept is the
  operational exit)", citing "invariant 4 (≥ 2 sealed is the Disputed threshold; **one is Forked**)"
  — which is not what invariant 4 in the same document says).
- The IEL and SEL documents repeat the same split: `iel/log.md`'s state table is correct, while its
  §Forked versus Disputed section says "**one or fewer → Forked** … A single sealed branch you did
  not author … read node-agnostically **it stays Forked until a second accepted sealed branch
  lands**" — the most explicit statement of the abandoned model anywhere in the design surface.
  `iel/reconciliation.md` mirrors the KEL proof doc exactly (correct invariant 4 and state table;
  stale cell vocabulary "`Forked` (≤ 1 sealed)"; stale completeness-matrix row 5 "Forked-frozen";
  stale "`forked` (≤ 1 sealed)" in its effective-SAID section). `sel/reconciliation.md` has the
  correct invariant 4 ("a single accepted sealed branch buries the content → Active") but the stale
  "`forked` (≤ 1 accepted sealed)" in its own effective-SAID section.
- Why the resolved-to-Active model must be the intended one, beyond the site count: under the "reads
  Forked" model, an attacker holding only the everyday signing key could freeze the chain repeatedly
  at almost no cost — author a content rival beside each legitimate sealed event, and the chain
  reads Forked (relying parties refuse) until the owner spends another sealed event, and so on. The
  auto-burial model closes that denial-of-service exactly because the accepted sealed event buries
  the content rival the moment it lands. The cost — the rightful owner of a stolen reserve gets no
  in-band alarm — is the position `residuals.md` and `monitoring.md` already own ("no structural
  veto"; detection is monitoring).

**Recommendation (final form).** One authoritative statement, propagated to every listed site: a
fork's state is decided by the count of accepted sealed branches at the last seal — **0 → Forked**
(live, recoverable; the effective-SAID synthetic applies), **1 → resolved** (Active, or Terminated
for a terminal event; real tip hash; the non-author's forced reincept is an operational consequence,
not a chain state), **≥ 2 → Disputed** (terminal synthetic). The reconciliation documents'
completeness-matrix row 5 needs a rewrite, not a rewording — as written it asserts a state
("Forked-frozen") the rest of the proof says cannot exist.

### Finding 1.2 [serious] — the "no self-burial" admission guard is stated in terms no verifier can check, and any literal implementation of it would forbid legitimate recovery

`protocol-doctrine.md`, "Divergence and recovery," defines two admission-time shape guards for a
burying sealed event. The second ("no buried rotation" — the buried set must be content-only) is
crisp and checkable. The first is not:

> "**No self-burial.** A burying seal-advancer that siblings its own retained chain — burying
> content **it authored** below its own attach point — is rejected. The verifier knows the retained
> chain (it walks the seal's `previous` back), so a seal that would bury a subtree **including the
> canonical chain** is refused; each event has one `previous`, so a genuinely off-chain loser's
> subtree is disjoint from the retained chain."

Three problems:

- "Content **it authored**" is not decidable from chain data — the same document states repeatedly
  that chain data carries no authorship ("chain data cannot tell the rightful operator from an
  adversary"). A guard phrased on authorship is not a performable check.
- "A seal that would bury a subtree including **the canonical chain** is refused" — if "canonical"
  means the currently-accepted (first-seen, witnessed) extension, this sentence forbids the
  document's own recovery move: an owner shedding a signing-key thief's tail attaches _below_ their
  current tip and buries events that were, until that moment, the accepted extension. It also
  forbids the burying event in the mixed fork of Finding 1.1.
- The closing clause ("each event has one `previous`, so a genuinely off-chain loser's subtree is
  disjoint from the retained chain") says the buried set is _structurally always_ disjoint from the
  seal's own lineage — in which case it is unclear what shape the guard ever rejects.

The guard needs a precise, data-only statement of what is checked and what is rejected — or it needs
to be removed in favor of the checks that actually do the work.

**Verified against the KEL primitive (Group 3) — no precise form exists, and the mechanics
contradict every candidate reading.** `kel/merge.md` names "no self-burial" in its preamble as one
of the shape-validity gates, but its routing rules (§Kind-specific authorization, and §How a burying
seal-advancer resolves a content fork — which says explicitly "no discriminator, no losing-branch
commitment, no content-only guard walk") specify only the sealed-branch guard; no merge rule
performs a self-burial check. `kel/reconciliation.md`'s Matrix-4 guard restates it ("a burying
seal-advancer that siblings its own retained chain … is rejected — a node buries only competing
branches, never the branch it keeps") without an operational definition. Every candidate reading
fails:

- _"Siblings its own retained chain"_ read literally (the seal is a sibling of an event on its own
  ancestry) is geometrically impossible — an event's parent cannot also be its sibling's parent
  along its own ancestry — which the doctrine's own closing clause concedes ("each event has one
  `previous`, so a genuinely off-chain loser's subtree is disjoint from the retained chain"). A
  guard that can never fire is dead text.
- _"Buries content it authored"_ is undecidable — chain data carries no authorship, as the design
  states repeatedly.
- _"Would bury a subtree including the canonical chain"_ (the doctrine's parenthetical) would reject
  two moves the design explicitly permits: the shed-the-tail recovery ("the attach may sit below the
  current tip to shed an adversarial content extension" — the buried tail was the accepted canonical
  extension until that moment; `kel/merge.md` Matrix-1 Position 3 routes exactly this to
  `Recovered`), and the ancestor-attach recovery, which `kel/merge.md` says buries "the submitter's
  own content included."

**The IEL and SEL documents make the incoherence concrete.** `iel/merge.md` promotes the guard to a
numbered routing rule (rule 5: "A burying seal that would sibling **its own** retained chain (its
`previous` is known from the walkback) is rejected as a **self-burial**"), and
`iel/reconciliation.md` repeats it in its Matrix-4 guards — still with no operational definition.
The decisive evidence is in `sel/reconciliation.md`, Matrix 3, last row — the **only place in the
design surface where the guard is applied to a concrete case**: "a `Sea` extending the live tip is a
valid no-op re-seal, while one **attaching below the resolved tip** is caught by the self-burial
guard." But attaching a seal below the tip and burying the run past the attach point is exactly what
Position 3 of the submission matrices — **in this same file** and in the KEL and IEL versions —
routes to `Recovered` ("the seal buries the content run past its attach point; the content dies on
ascent → Active"), and what the doctrine's shed-the-tail recovery depends on. So the one concrete
reading the docs give the guard directly contradicts a routing rule stated a few sections earlier.

The protections that actually hold are the ones already specified: hard authorization (the reserve
signature or the anchoring threshold), the content-only burial guard (a witnessed sealed event in a
would-be-buried branch → Disputed), and the unconditional seal-cap. Recommendation: delete "no
self-burial" from all its sites (`protocol-doctrine.md` §Divergence and recovery, `kel/merge.md`
preamble, `kel/reconciliation.md` Matrix-4 guards, `iel/merge.md` rule 5, `iel/reconciliation.md`
Matrix-4 guards, `sel/reconciliation.md` Matrix 3), or replace it everywhere with a precise,
data-only rule that does not conflict with Position-3 burial and ancestor-attach recovery — as it
stands, an implementer who takes "runs wherever an event is admitted to trusted state" seriously
will either implement nothing (the vacuous reading) or break the recovery story (the
protect-the-canonical-chain reading).

### Finding 1.3 [minor] — the singleton-roster exception contradicts the stated authority floor as written

`protocol-doctrine.md`, threshold-vector bounds: "The authority slots (`t_govern` / `t_authorize`)
carry a **security floor `≥ 2`** (no single member exercises authority)" — and, three bullets later,
"a singleton (`|roster| = 1`) sets all thresholds to 1." The second statement is a real exception to
the first, but the first is stated unconditionally. A one-line qualifier on the floor ("for rosters
of two or more; a singleton sets all thresholds to 1") would remove the contradiction. _(The IEL
events document owns the full statement — checked in Group 3; if it carries the exception cleanly,
this is drift in the doctrine's summary only.)_

### Finding 1.4 [minor] — the doctrine's own table of contents omits a section

`protocol-doctrine.md`'s Part 3 listing at the top of the file omits "Caching and continuation,"
which exists as a section between "Walk semantics" and "Structural problems error…". Trivial, but
this is the document that tells readers to use its map.

### Notes (no defect)

- The `{Rot, Rot}` dispute-proof reasoning (two rival rotations at one position must both reveal the
  same committed reserve, so the pair proves the reserve's key signed twice) is sound, and
  `residuals.md`'s sharper framing — the second rotation needs the _revealed_ key, which by then is
  the current signing key, not the still-secret next reserve — is consistent with it and correctly
  drives the exploitability scoring.
- The federation threshold arithmetic is consistent everywhere it appears (roster ≥ 4, signer pool
  excludes at least one member, signers ≥ 3, threshold a strict majority capped at min(roster − 2,
  signers − 1); a 4-witness federation: 3 signers, threshold 2, one evictable).
- The effective-SAID synthetic being a verdict marker rather than a hash over the competing tips is
  well-argued (an attacker who can mint extra branches would otherwise churn the value), and the
  "masking is harmless" argument holds because no decision reads the branch _set_ off the value.
- `monitoring.md` is consistent with the doctrine and honest that it detects rather than prevents.

## Group 2 — The data substrate

_(sad.md, said.md, custody.md, availability.md, compaction.md, kinds.md, shapes.md,
tags-and-topics.md)_

All eight documents read in full. This group is in very good shape. The load-bearing arguments are
sound as written: the two-hash split between a chain's stable identifier and its inception event's
own hash (so a logged event hash never doubles as the chain's lookup key); the "canonical form is
the fully-compacted form" rule and its companion "verify every inline child before substituting"
rule (which closes the lying-embedded-child gap and is argued correctly); the sorted-and-distinct
requirement for set-valued lists (without which one logical set would have many hashes); the
write-attribution anchor design (attribution is corroborated by an append-only anchor on the
writer's identity chain, located by a checked pointer, so it cannot be backdated even by a broken
old key — the non-circularity of pointer-then-anchor is handled); and the store's fetch-by-SAID
sorting rule with its stated rationale. The privacy contract (a parent's read gate does not protect
its children) is honestly stated three times over rather than hidden.

### Finding 2.1 [minor] — sad.md defines "prefix-deriving SADs" as exactly the chain inceptions; said.md adds one more

`sad.md` (Required fields): "For **chain inception events** (the prefix-deriving SADs): a `prefix`
field…" — the parenthetical reads as a definition equating the two. `said.md` (Derivation):
"prefix-deriving SADs — the chain inception events, **and the document constitution V0** (a
standalone prefix-deriving SAD)." The shared-documents V0 is a real prefix-deriving standalone SAD
(confirmed by its shape in `shapes.md`), so sad.md's parenthetical is wrong by omission.

### Finding 2.2 [minor] — the witness-config bound in shapes.md silently reuses "|roster|" for a different roster

`shapes.md`, the witness-config table: "Bounded `signers/2 < threshold ≤ signers ≤ |roster|`…". In
every nearby use of `|roster|` (the roster-delta table directly below it, the IEL bounds) the symbol
means the identity's own member roster; here it must mean the **federation's** witness roster, since
witnesses are drawn from the federation. One clarifying word ("the federation roster") would prevent
a reader from concluding a user identity needs as many witnesses as it has devices.

### Open question carried forward (resolved in later groups)

`kinds.md` calls itself "the canonical enumeration of every SAD kind," and its fetch-by-SAID rule
names two framework SADs a verifier resolves — "an authorizing **`issuers`** list, a credential's
**`terms`**" — that appear in no kind table and no forthcoming-shapes row (`terms` appears in the
credential shape as a nested SAD with no kind named). Checked again at Groups 5 and 7 to confirm
whether these have kinds somewhere or are a genuine catalogue gap.

## Group 3 — The event-log primitives

_(event-shape.md; kel/: log, events, verification, merge, compromise, reconciliation; iel/: log,
events, verification, merge, reconciliation, delegation; sel/: log, events, verification, merge,
reconciliation)_

### 3A — Event shape and the KEL

`event-shape.md` and all six KEL documents were read in full. Apart from the two doctrine-level
findings whose evidence lands here (1.1 and 1.2 above — both confirmed against these files), this
group is strong, and several load-bearing arguments deserve explicit sign-off:

- The **two-tier key model** is stated consistently everywhere (the reserve is the sole tier-2
  prerequisite; the old signing key is never required; the reserve defends the signing key, never
  the rotation key), and the subtle boundary case — after a rotation lands, the revealed reserve
  _is_ the current signing key, so a late rival seal at that one position is a signing-key forgery,
  not a reserve forgery — is handled identically in `kel/events.md`, `kel/compromise.md`, and
  `residuals.md`, including its consequence (a brick needs a signing key plus witness collusion; a
  takeover needs the reserve).
- The **brick-is-forced argument** in `kel/compromise.md` (choosing a winner between two accepted
  seals by any data rule is attacker-grindable; choosing by first-seen makes the answer
  observer-dependent; so abandon-and-reincept is the only sound resolution) is a correct and
  well-made piece of reasoning.
- The **page arithmetic** is coherent: `MINIMUM_PAGE_SIZE = 129 = 2 × MAXIMUM_UNSEALED_RUN + 1` with
  `MAXIMUM_UNSEALED_RUN = 64` appears identically in `protocol-doctrine.md`, `kel/log.md`,
  `kel/events.md`, and `kel/reconciliation.md`, and the two shapes that legitimately exceed one page
  are enumerated rather than hidden.
- The **per-kind field grids** in `event-shape.md` agree with the per-primitive prose (I checked
  every KEL row against `kel/events.md`, the manifest role vocabulary against `kinds.md`, and the
  taxonomy counts against the glossary).
- `kel/reconciliation.md` edge case 3's warning ("do NOT append a sealed event to the stale branch")
  correctly follows from the below-seal-sealed-straggler-is-dropped rule — the stale terminate is
  wasted, not a brick — a good example of the backdate defense composing correctly.

### Finding 3.1 [minor] — `kel/log.md` states the Forked definition twice, once correctly and once in the stale form

Recorded here for completeness of the 1.1 site list: `kel/log.md`'s state table gives the correct
content-only definition, while its own "Forked versus Disputed — a data-local walk" section thirty
lines later says "at most one branch carries a sealed event past the fork." Same document, both
forms. (Fold into the 1.1 sweep.)

### 3B — The IEL and the SEL

All six IEL documents and all five SEL documents were read in full. Beyond the 1.1 / 1.2 sites
already recorded above, both primitives are in strong shape, and several designs deserve explicit
sign-off:

- **The threshold vector and its bounds** (`iel/events.md`) are stated precisely, with the singleton
  exception carried cleanly ("hard for every identity of |roster| ≥ 2 … a singleton sets all
  thresholds to 1") — confirming Finding 1.3 is drift in the doctrine summary only. The
  never-emptied floor's arithmetic (a singleton cut computes 1 + 0 − 1 = 0 and is rejected;
  evict-and-replace stays legal) is checked and correct.
- **The facet-dependent `Wit`** is handled with unusual care: the root facet is fixed at inception,
  carried on the verification token, and re-applied on every `Wit`-reading path including resumes —
  and the docs explain _why_ it must be (the directly-consumed governance roles have no downstream
  type-check, so a facet-blind allowlist would let a user rebind smuggle a roster delta).
- **The atomic `cut` eviction** (one sealed event buries the fork and evicts, because a two-event
  sequence would let the still-rostered member re-fork the resolved tip) is argued the same way in
  `protocol-doctrine.md`, `iel/merge.md`, and `iel/reconciliation.md`.
- **The SEL's self-witnessing argument** (`sel/log.md`) is exactly right and closes a real hole: an
  identity-chain anchor is an opaque hash the identity chain cannot deduplicate, so a linear owner
  chain cannot prevent the owner equivocating its own data log — the data log must be witnessed at
  its own positions. The companion argument for the neutral re-seal `Sea` (an owner-chain anchor can
  end up live-and-locked, beyond both severance and re-burial, so the data log needs its own
  seal-advancer) is also sound.
- **The one-content-event-per-anchoring-`Ixn` rule is now enforceable as stated**:
  `sel/events.md`/`sel/verification.md` specify anchor-identity dedup inside the SEL walk (a second
  content event resolving to the same anchoring identity-chain event is rejected), which is a check
  the verifier can actually perform — unlike older formulations that would have required the
  identity chain to deduplicate opaque hashes. The old formulation survives only as an explicitly
  demoted defense-in-depth guard.
- **The severance model** (`sel/reconciliation.md`) is a genuine exhaustive crossing of the two
  state inputs, and its two "unreachable by construction" cells are _argued_ (acceptance gates on
  the anchor being accepted; a sealed anchor is never buried once accepted) rather than asserted.
- **The lineage walk** for re-establishable published values is honest about its one soft spot — the
  rescission must declare the matching lineaged kill target, which the primitive cannot check — and
  that obligation appears consistently in `sel/verification.md`, `sel/reconciliation.md`, and
  `residuals.md` §Owed work.

### Finding 3.2 [minor] — the IEL's "T2 seals out of a fork" rule and the frozen-roster rule could collide for a reader, but are consistent; one wording nit

`iel/verification.md`'s roster/live-authority table is internally consistent (a fork freezes tier-1
acts; any tier-2 act seals out of it; Disputed and Terminated refuse both), and the justification
("what a seal-out buries is the tier-1 content loser; no tier-1 actor holds a tier-2 quorum") is
sound. One wording nit: `iel/events.md` says a permanent kill "needs a **≥ tier-2** KEL anchor" —
there is no tier above 2; "tier-2" is meant.

## Group 4 — Federation and witnessing

_(bootstrap.md, witnessing.md, topics.md, mesh-transport.md)_

All four documents read in full. This group is the strongest of the design surface: dense but
internally consistent, with the adversarial cases argued rather than asserted. Checks performed and
passed:

- **The arithmetic all holds.** The witnessing floor, fork-cost (`2·threshold − signers`), the
  federation's recoverability cap (`threshold ≤ min(|roster| − 2, signers − 1)`, with the
  self-attest pool correctly derived as roster minus the evicted member minus the receipting witness
  itself), the `|roster| ≥ 4` floor, and the minimal 4-witness configuration (3 signers,
  threshold 2) are consistent everywhere they appear — doctrine, IEL events, shapes, witnessing,
  bootstrap.
- **The clock design composes.** Key-windows bounded by the governance clock, the wipe rule, the
  365-day auto-expiry with the at-risk flag (which `residuals.md` references and this doc actually
  defines), the `now + CLOCK_TOLERANCE_BAND` upper sanity bound (which caps the future-dated-clock
  attack residuals mentions), and the no-self-weakening rule with its deliberate clock-axis
  carve-out (so an all-windows-lapsed federation reads stale-but-recoverable, not bricked) — each
  cross-reference checked out.
- **The witnessed-time definition** (the threshold-th smallest receipt timestamp) comes with a
  correct one-sided-manipulation analysis: adding late receipts cannot move the crossing later,
  pushing it earlier requires a full witness compromise, and the eclipse-bounded inflation is
  confined to already-accepted residual classes.
- **The split-stall exit composes with acceptance rules**: the exit seal extending a sub-threshold
  stalled sibling makes that sibling canonical via the "an accepted event commits its ancestry" rule
  stated in `kel/verification.md` — the docs anticipated the composition rather than leaving it
  implicit.
- **The bootstrap non-circularity argument** (authorization is ordinary member-anchoring; trust is
  the configured prefix; the `Fcp` marker is interpretation, not vouching) is correct and clearly
  made, and the genesis ceremony's dependency-order-not-atomicity framing is honest.
- **The mesh transport** is a sound, conservative construction (mutual signatures over the
  transcript bound to witnessed key state; ephemeral encapsulation key → forward secrecy;
  per-direction keys with strictly-increasing counters making nonce reuse unreachable), and it
  correctly claims only confidentiality, never trust.

### Finding 4.1 [minor] — the witness-receipt field names differ between the shape catalogue and the witnessing doc

`shapes.md` (the authoritative field catalogue) spells the receipt fields `chainPrefix`,
`eventSaid`, `eventSerial`, `witnessPrefix`; `witnessing.md`'s receipt body block spells them
`chain_prefix`, `event_said`, `event_serial`, `witness_prefix`. For a record whose canonical bytes
are hashed and signed, field spelling is load-bearing — two implementers reading different docs
would produce receipts with different hashes. One of the two spellings should be corrected to match
the other.

## Group 5 — Document authorization

_(policy.md, documents.md, evaluation.md)_

All three read in full. The layer is well-designed and consistent: the two-mechanism split (chains
authorize structurally, documents are accepted against the relying party's policy — never their
own), the as-issued-only evaluation with the mandatory to-tip freshness step, and the
verification-token seam that keeps the dependency one-way. Specific checks that passed:

- The **earliest-anchor proof** in `documents.md` is correct: the credential's committed locator
  pins the anchoring position, and an _earlier_ anchor carrying the commitment is impossible because
  the commitment embeds the credential's hash, which embeds the locator, which is the hash of the
  event just before the anchor — a hash cycle. This is what closes the re-anchor tier inversion (a
  later tier-1 re-anchor after a tier-2 revocation can never move the as-of forward, because later
  anchors are simply never consulted).
- The composition rules are unusually careful: distinct-identity counting with the existential
  (assignment-search) semantics rather than a greedy pass — with the correct observation that a
  greedy evaluator can wrongly deny and that two differently-ordered greedy evaluators would
  disagree; per-identity-max weighting; `and` over disjoint pools with the overlap caveat stated;
  unknown-construct-denies-whole-policy; zero thresholds and degenerate `and` rejected as fail-open
  gates.
- The delegation story (walk up the one committed path, positive rescission match per hop,
  grandfather per hop on that hop's own chain, `MAXIMUM_DELEGATION_DEPTH` backstop) is consistent
  across `policy.md`, `documents.md`, `evaluation.md`, and `iel/delegation.md`, and its
  operator-facing sharp edges are honestly listed in `residuals.md`.

### Finding 5.1 [minor] — "a shared policy must evaluate identically everywhere" is in tension with a per-verifier work budget

`policy.md` (Composition rules) requires the assignment search precisely so that "a shared policy
must evaluate identically everywhere," but the search — and the whole evaluation — is bounded by "a
verifier-wide budget," which is not a pinned protocol constant. Two verifiers with different budgets
can disagree at the margin: one finds a satisfying assignment, the other exhausts its budget and
denies. Since deny-on-budget is fail-secure, this is not a safety hole — but the document should
either pin the budget (as it pins `MAXIMUM_DELEGATION_DEPTH`) or soften the evaluates-identically
claim to "never wrongly permits."

## Group 6 — Protocol primitives

_(essr.md, ipex.md, receive-key-directory.md, group-key.md, membership.md, authored-dag.md)_

All six read in full. No correctness findings. This group is notable for how consistently each
primitive states its boundary (what it is _not_) and its residuals, which match the entries in
`residuals.md` line for line. Sign-offs worth recording:

- **ESSR**: the four guarantees and the two-bindings argument (recipient in the signed cleartext
  defeats recipient-key substitution; sender inside the sealed content defeats strip-and-re-sign)
  are correct and properly credited to the prior art; the open procedure checks everything it needs
  to (recompute the envelope hash, verify signature, assert recipient-is-me, digest-check the
  fetched sealed payload, assert inner sender equals envelope sender); the per-message-key argument
  for nonce safety is right.
- **IPEX**: the single-round-trip freshness envelope is sound — the one signature doing double duty
  (ownership via the required-signer rule resolving to the _committed_ issuee, never the
  self-declared discloser; replay-binding via audience + nonce + two-sided time window) is analyzed
  attack-by-attack, and the self-asserted timestamp is correctly confined to cache-retention, never
  trust. The presenter-must-not-be-divergent rule composes correctly with the IEL's
  tier-1-frozen-on-fork rule.
- **Receive-key directory**: publish/rotate under the reserve (so a stolen signing key cannot
  redirect mail — the load-bearing property), fan-out semantics, opaque-label trade-off, and the
  explicitly-carried lineaged-kill obligation (named as the first value-lookup consumer, matching
  `residuals.md` §Owed work).
- **Group-key**: independent per-epoch keys (no derivation chain), member-delivered never-published
  wraps (with the correct observation that the gated roster alone would not keep membership blind —
  the wraps would re-expose it), the per-writer subkey nonce-partitioning discipline with the honest
  note that subkeys authenticate no one, and the hardware / removal / ratchet three-way analysis.
- **Membership**: the disclose-your-own-nonce mechanism that keeps the fail-secure walk _performable
  by the store_ (with the check that the disclosed data names the live-signature identity, so a
  leaked commitment is not a bearer token) — this directly answers the "is the stated check actually
  enforceable?" concern this class of design invites; the blinded rescission address (keyed on the
  grant instance, not the raw prefix) closing the confirm-a-guessed-removal oracle.
- **Authored DAG**: the two-variant fork rule; the honest treatment of the forest problem (a second
  parentless root is _not_ self-proving, hence the anchored-root requirement carried by the
  feature); the removed-writer interval check (`[anchored root … bound]`) correctly characterized as
  a local check needing no fork visibility; and the dormant-current-writer backdate residual stated
  here, in `membership.md`, and in `residuals.md` consistently.

## Group 7 — Features

_(credentials.md, exchange.md, shared-documents.md)_

All three read in full. No serious findings; the feature layer's distinguishing quality is that
every residual it accepts is stated in the feature doc, in the primitive doc it composes, _and_ in
`residuals.md` — I cross-checked each (the self-lane backdate cases, the open-epoch future-dating,
chat's single-device-signature bar, the home-nodes communication graph, the bearer copy-race, the
terminated-issuer freeze, the delegation-scope surprises) and found no drift. Sign-offs:

- **Credentials**: the accept gate is a complete fail-secure conjunction, and its interlocks with
  earlier layers hold — the frozen-on-divergence rule for the presenting issuee matches the IEL's
  live-tier-1 gate; the terminated-issuer-passes rule matches pre-seal finality, with the
  revoke-before-terminate discipline carried in both directions; the tip-atomic mint (an intervening
  append breaks the locator, forcing a re-mint) is the same construction custody uses.
  Claim-gating's uniform-bracket rule (presence-privacy) and renewal-crossing model are clean. The
  bearer analysis (redemption-is-revocation; reusable-transferable-bearer correctly identified as a
  logical impossibility rather than a missing feature) is right.
- **Exchange**: the sender-key-currency check is the design's most intricate composition (two
  witnessed axes — the identity's establishment intervals and each device's key-windows — with the
  self-asserted timestamp confined to selecting _within_ witnessed bounds) and it holds together;
  the closed-interval/as-issued versus open-interval/live-authority split composes correctly with
  the divergence freeze. The upload/fetch gates are correctly asymmetric (upload authenticates the
  writer; fetch is the load-bearing serve-time gate, deliberately an identity-roster check rather
  than a quorum so polling stays a single-device act). The chat currency model (epoch window bounds
  _when_; the writer's own key-window bounds _who_; no key-state pin needed because the witnessed
  epoch anchors time) is sound, and its one soft spot — the open epoch's missing upper bound — is
  flagged with the mitigation.
- **Shared documents**: the honored predicate (`F_x ≤ V_x ≤ B_x`, all three positions on the
  editor's own append-only chain) is correct and clock-free; the "grant must be sealed, not merely
  fetched" paragraph explicitly closes the cite-your-own-grant bypass, and the doc is candid that
  skipping the seal-locate is a total bypass; the effective-floor argument (a version cannot predate
  its own grant, by hash-preimage order) is right, as is the demotion of `F_x` to disjointness
  bookkeeping. The freeze construction (bound-all + terminate, with the grant chains deliberately
  carrying no re-establishment counter so the freeze is permanent) composes correctly with the SEL
  lineage rules. The comment window mirroring the version predicate — but with no cited grant, hence
  walk-only — is correctly reasoned.

## Group 8 — Cross-cutting consistency

_(Findings that span groups, plus the top-level docs README.md, MODEL.md, USES.md against
doctrine.)_

`README.md` and `USES.md` are consistent with the design surface (claims checked against the
doctrine: the "no watcher infrastructure" contrast, the fail-secure revocation summary, the
composition table). `MODEL.md` has one real problem.

### Finding 8.1 [moderate] — MODEL.md's "core rule" draws the keep-both / take-first line in the wrong place

`MODEL.md` §The core rule presents the conflict rule as two questions, the second being "could one
key have signed the competing version, or did it take several of the identity's keys agreeing?" —
with "one key could → take the first, drop the copy" (device rotations, solo-identity governance)
and "it took several → keep both, raise the alarm" (multi-device roster changes, federation acts).
That is not the design's split. In the primitives:

- Honest witnesses take the first and decline the second for **every** sealed event — group
  decisions included (`{Evl, Evl}` in an honest race is first-seen-declined; "the position gate is
  universal"). Nothing is deliberately double-accepted.
- Keep-both (retain-as-evidence, Disputed at two accepted) applies to **every** witnessed sealed
  conflict — single-key device rotations included: `{Rot, Rot}` with both accepted is Disputed and
  terminal for the device chain (`kel/reconciliation.md` Matrix 3; the live-tip killswitch in
  `kel/compromise.md`).

So the real line is content versus sealed (MODEL's Question 1), and Question 2's asymmetry is an
invention — its claim that a single-key rotation conflict is "take first, drop the copy … a stolen
key must stay _recoverable_, not terminal" contradicts the KEL's brick analysis (under witness
collusion a stolen _signing_ key does terminalize the device chain — the design argues at length
that this is forced and correct). MODEL's own "What disputed means" section then quietly contradicts
Question 2 by allowing any conflict to become disputed under witness corruption. Since `MODEL.md` is
the plain-language on-ramp, a reader will carry this wrong taxonomy into the design docs.
Recommendation: collapse the section onto the real rule — ordinary activity is
first-seen-and-recoverable; key changes are first-seen honestly, kept-both when both get backing,
and two backed key changes are terminal _whoever_ could have signed them — and keep the
"single-stolen-key versus group betrayal" contrast only as what a dispute _proves_ (forensics),
which is where the primitives use it.

### Finding 8.2 [minor] — two framework record types have no entry in the type catalogue

`kinds.md` presents itself as "the canonical enumeration of every SAD kind," and its fetch-by-SAID
rule explicitly lists "an authorizing **`issuers`** list, a credential's **`terms`**" among the
framework records a verifier resolves. Neither has a kind row, and neither appears in `shapes.md`'s
forthcoming-shapes table (the `issuers` record is defined in prose in `documents.md` §Multi-identity
authorization; `terms` appears in the credential shape as a nested record with no type named).
Either they need kinds (and rows), or the catalogue's completeness claim needs qualifying.

### Notes (no defect)

- The glossary's definitions were checked against each owning doc as those docs were read; apart
  from the 1.1 sites already listed, no drift was found. The three-way naming hazard the design
  itself flags (`Terminated` / `Terminal` / `Trm`; the `pin` field versus the `Pin` event kind) is
  consistently disambiguated where it appears.
- Protocol constants are consistent across every appearance: `MINIMUM_PAGE_SIZE = 129`,
  `MAXIMUM_UNSEALED_RUN = 64`, `MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_MANIFEST_LIST = 128`,
  `MAXIMUM_SEL_LINEAGE = 64` (with the inclusive-index clarification in `sel/events.md`),
  `MAXIMUM_DELEGATION_DEPTH = 8`, `MAXIMUM_GRANT_ADDS = 64`,
  `MAXIMUM_WITNESS_KEY_WINDOW = 365 days`, `CLOCK_TOLERANCE_BAND = 1 minute`.
- The residuals catalog is genuinely complete against what the primitive and feature docs disclose —
  every accepted limit I encountered while reading the 41 docs has a corresponding entry. That is
  rare and worth preserving as the docs move.

## Verdict

**The design is sound. The two serious findings are documentation-integrity defects on load-bearing
rules, not holes in the security model — but they sit exactly where an implementer would read, so
they should be fixed before implementation begins.**

On the correctness axis, the load-bearing arguments hold up under adversarial reading: the two-tier
key model and its boundary cases (the spent-reserve rival, the brick-versus-takeover split), the
witnessing floor and fork-cost arithmetic, the seal-cap and burial-by-position-and-ascent machinery,
the backdate defenses (below-seal stragglers dropped, the currency gate, the clock and key-windows,
the earliest-anchor hash-cycle proof), the effective-SAID synthetic's flood-stability, the SEL's
self-witnessing and severance model, and the feature-layer compositions (sender-key currency, the
honored predicate, the membership walk's performability). Where checks are stated, they are
performable — this pass specifically hunted for stated-but-unenforceable rules and found the
historical ones fixed (the one-content-event-per-anchor rule now has a checkable form; the
membership walk carries its own disclosure mechanism) with a single new instance: the "no
self-burial" guard (Finding 1.2), which should be removed or made precise.

On the consistency axis, the surface is in better shape than its size would predict — constants,
anchor matrices, field grids, glossary entries, and residuals align across 40-plus documents — with
one systemic exception: the divergence-state question of Finding 1.1, where a superseded "≤ 1 sealed
branch → Forked" formulation survives alongside the current "0 → Forked / 1 → resolved / ≥ 2 →
Disputed" model in roughly ten places, including inside the two documents whose job is to be the
exhaustive proof. Both proof documents currently assert, in different sections, two different chain
states for the same input. The fix is mechanical (the intended model is clearly identifiable, and
this review argues independently that it is the right one), but it should be a single sweep with a
checklist of the listed sites, not piecemeal edits — this is the kind of drift that decorrelated
reviews will otherwise keep re-flagging.

Recommended order of work: (1) the 1.1 sweep; (2) resolve 1.2 by deletion or precise restatement;
(3) rewrite `MODEL.md`'s core-rule section (8.1); (4) the minors, which are one-line fixes.
