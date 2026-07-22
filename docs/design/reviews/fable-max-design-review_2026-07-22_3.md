# Fable (max) design review — 2026-07-22 (3)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_3.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

**Reviewer:** Claude (Fable 5, max effort) — a cold review: a fresh read of the current files, with
no carry-over from earlier review sessions and no reference to the earlier review documents.
**Scope:** every document reachable from the reading order in `docs/design/README.md` (41 files,
about 17,000 lines), plus the repository `README.md` it routes through and a consistency skim of the
plain-English companion `MODEL.md`. **Axes:** correctness/soundness (does the stated design hold
together and resist the attacks it claims to resist) and consistency (do the documents agree with
each other).

**Method:** read in the layer order the design README prescribes (orientation → data substrate →
doctrine → event logs → federation → policy → protocol primitives → features), attacking each
load-bearing claim as it appeared and cross-checking every rule against the other documents that
state it. Phrase sweeps used `scripts/grep-terms.pl` (decoration- and wrap-tolerant), plus plain
greps for every named protocol constant and for terms that should only ever appear as negations.

**Status: complete.**

## Verdict

The design surface holds up. I set out to break it — the posture its own thesis demands — and found
**no structural soundness break**: every attack path I constructed is already closed by a stated
rule, and the rule is stated consistently at each site that needs it. The three chain primitives,
the witnessing layer, the policy layer, and the features interlock the way the documents claim they
do, and the exhaustive case-matrix documents (the per-primitive "reconciliation" proofs) agree
cell-by-cell with the write-path and read-path documents they are proving sound.

What I did find is a small set of **consistency and completeness gaps**, listed below. One is a
front-page overstatement worth fixing (F1); the rest are places where a rule stated in several
documents is missing or worded differently at one of them. None of them changes the design's
behavior; each is a place where a reader — or an implementer following the wrong copy of a rule —
could be misled.

## Summary of findings

| #   | Where                                        | Axis                             | Severity | Finding (one line)                                                                                                                                                                                                           |
| --- | -------------------------------------------- | -------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | `README.md` (and `system-thesis.md`, softer) | consistency (soundness of claim) | medium   | The front page says a verifier can determine from the data whether an identity "has been compromised"; the design's own documents say the worst compromise is invisible to third parties and rests on owner-side monitoring. |
| F2  | `residuals.md`                               | consistency                      | low      | The "Two-member identity" row is scored on the availability axis (ceiling 2) while its own detailed entry says what is lost is recoverability (ceiling 6).                                                                   |
| F3  | the five `sel/` documents                    | consistency / completeness       | low      | The "a late key-change event below the seal is dropped" rule (the backdate defense) is restated in the KEL and IEL merge and proof documents but never in the SEL's, where it equally applies.                               |
| F4  | `membership.md` vs `shared-documents.md`     | consistency                      | low      | The two documents derive the removal-lookup address from different inputs: the member's blinded entry identifier alone, versus that identifier hashed together with its grant document's identifier.                         |
| F5  | `tags-and-topics.md` / `exchange.md`         | completeness                     | low      | The chat membership's fast removal-lookup needs a derivation topic; the shared-documents counterpart is named, the chat one never is.                                                                                        |
| F6  | `MODEL.md`                                   | consistency                      | very low | "A second key change gets backed only when an attacker corrupts enough witnesses" is stated as absolute; the design carries one stated exception (two re-bindings to different federations).                                 |

Everything else I checked — the protocol constants, the risk-table arithmetic, the event-kind
tables, the anchor rules, the threshold bounds, the state machines, and the cross-document
statements of every load-bearing rule — is consistent. The soundness probes and the verification
sweeps are written up after the findings, so the basis for "no structural break" is inspectable.

## Findings in detail

### F1 — The front page overstates what a verifier can see (consistency, medium)

`README.md` says:

> VDTI lets any verifier determine system-wide state — including whether an identity has **diverged
> or been compromised** — from the data itself, with no watcher infrastructure.

`system-thesis.md` opens with the softer "including attack exposure."

The "diverged" half is true and is the genuine contrast with KERI: a fork or a dispute is a
data-local verdict any verifier computes from the events it holds, and the design proves it
carefully. The "been compromised" half is broader than what the design itself claims. The design's
own documents are explicit that the most severe compromise — theft of the rotation reserve, the
secret that authorizes key changes — produces **no structural trace a third party can see**:

- `monitoring.md`: "The dangerous ones leave **nothing structural to catch** … witnesses sign it as
  an ordinary next event. There is no competing branch, no dispute, no veto."
- `kel/compromise.md`: a takeover-by-extend is "**silent to third parties on a dormant chain**
  (caught only by owner vigilance)."
- `MODEL.md`: "To a third party the takeover reads as an ordinary rotation either way."

Detection of that class is deliberately **owner-side** (the owner compares the chain's fingerprint
against what its own key state predicts — `monitoring.md`), which is a cheap watcher, not no
watcher. So the honest claim is: divergence, disputes, and forged forks are determinable from the
data by anyone; a clean takeover is not — it is detectable only by its owner, promptly if the owner
monitors.

Suggested fix: scope the README sentence (and the thesis's "attack exposure") to what the design
actually proves — e.g. "including whether an identity has diverged or been disputed" — or add the
qualifier the rest of the documentation carries ("a takeover that leaves no fork is caught by
owner-side monitoring, not by verifiers"). The design is unusually honest about this limit
everywhere else; the front page should match.

### F2 — One residual is scored on the wrong axis (consistency, low)

In `residuals.md`, the ranked "Avoidable" table scores **Two-member identity** as "Availability · 2"
(outcome: "One bad device freezes you; reincept"). The detailed entry for the same residual
("Two-member identity freeze," §10) states what is actually lost:

> **Lost** — **Recoverability** of a two-member identity — an indefinite freeze forcing reinception.

Recoverability carries ceiling 6 on the document's own severity scale, availability ceiling 2. Under
the entry's own text the row should score Recoverability · (up to 6), giving 6 × 300 = 1800 rather
than 2 × 300 = 600. Both land in the same "High" band, so the ranking outcome does not change — but
the table and the entry disagree about which property is at stake, and the document elsewhere takes
care to score a freeze-that-forces-reinception as a recovery cost. Suggested fix: either re-axis the
row to Recoverability, or add a line to the entry explaining why the freeze is deliberately scored
as availability (for instance, because the reinception itself is priced by other rows).

### F3 — The SEL documents never restate the backdate defense (consistency/completeness, low)

A key rule everywhere else: a **late sealed event whose parent sits below the chain's current seal
is dropped** — inert, never counted toward a dispute — because honoring it would let an attacker who
eventually cracks an old, retired secret fabricate a historical conflict years later. The KEL and
IEL document sets restate this at every relevant site:

- `kel/merge.md` and `iel/merge.md`, the `Sealed` rejection row: "a dead-on-arrival content **or
  sealed** sibling behind an advanced seal — a below-seal sealed straggler is dropped,
  backdate-safe."
- `kel/reconciliation.md` and `iel/reconciliation.md`, invariants 2 and 5: the same rule, with the
  "not witnessable past the seal; the backdate defense" explanation.

The five SEL documents never state it. `sel/merge.md`'s `Sealed` row mentions only "a
dead-on-arrival **content** sibling behind an advanced seal"; the word "backdate" appears nowhere
under `sel/` (verified by sweep); `sel/reconciliation.md`'s invariants have no counterpart to the
KEL/IEL bounded-divergence clause. The rule clearly must apply to the SEL too — the SEL is its own
witnessed chain with its own seal, and a harvested owner reserve could mint a below-seal grant,
re-seal, or kill event against it — and the cross-cutting documents do cover it generically
(`protocol-doctrine.md` states the drop rule for all three logs; `witnessing.md`'s "the witness
mirrors the seal-cap" is chain-generic). So this is not a soundness hole; it is the one place the
per-primitive restatement discipline (which the KEL and IEL sets follow rigorously) lapses.
Suggested fix: add the "or sealed … dropped, backdate-safe" clause to `sel/merge.md`'s `Sealed` row
and a matching invariant to `sel/reconciliation.md`.

### F4 — Two derivations for the same removal-lookup address (consistency, low)

Both documents describe the fast, one-fetch check for "has this member been removed?" — a tiny
lookup log at an address derived from the member's grant. They disagree on the derivation input:

- `membership.md` (the primitive): the lookup is "derived from
  `{ group, the rescission topic, the member's grant instance }` (**the member's high-entropy
  blinded-claim `said`**, not the bare prefix …)". The parenthetical reads as a definition: the
  grant instance _is_ the member's blinded entry identifier (`said_b`).
- `shared-documents.md` (the feature): the removal is "keyed per period — on **`hash(G : said_b)`**,
  the grant-doc's SAID joined with the member's nonce'd entry SAID", and the kill target is
  `hash('vdti/sel/v1/actions/rescission:{creator}:{hash(G : said_b)}')`.

`said_b` alone and `hash(G : said_b)` are different values, so the two texts derive **different
addresses** for the same object. Either construction works (the entry identifier is high-entropy in
both, so neither is guessable), but an implementer following the primitive document alone would
derive an address the feature's verifier never reads. Since the feature document is the one that
pins the concrete instance, the likely fix is to soften the primitive's parenthetical — say the
grant instance is feature-defined and merely _contains_ the blinded entry identifier (which is what
supplies the entropy) — or to align it to the `hash(G : said_b)` form outright.

### F5 — The chat removal-lookup's topic is never named (completeness, low)

`membership.md` requires every membership instance to have the fast removal lookup (for chat it is
load-bearing: its terminating event carries the per-lane cutoff the verifier enforces). The
shared-documents feature names its lookup's derivation topic explicitly —
`vdti/doc/v1/topics/rescission`, in its reserved-names list. The chat instance names none: neither
`exchange.md`'s "Reserved names" section nor the `tags-and-topics.md` catalogue (which presents
itself as the complete discriminator enumeration) carries a chat counterpart, and the forthcoming
table in `shapes.md` does not list it among the owed shapes either. The exchange encode is marked
forthcoming, so the gap may be intentional deferral — but the catalogue's completeness claim and the
parallel with the documents feature make the omission read as an oversight rather than a deferral.
Suggested fix: name the topic now (it costs one row), or note it in the forthcoming list.

### F6 — The plain-English narrative states one rule as absolute (consistency, very low)

`MODEL.md` (outside `docs/design/`, but billed by the README as the plain-language statement of the
rules) says a second key change at one step "gets backed only when an attacker corrupts enough
witnesses to force it." The design carries one deliberate exception: **two re-bindings that name
different federations** at the same step are each honestly backed by their own federation's
witnesses — disjoint witness sets, so no witness signs twice — and the proof of wrongdoing is on the
author's side instead (the same secret revealed twice, or one member endorsing both). This is stated
in `protocol-doctrine.md`, `witnessing.md` (twice), and `iel/log.md`. `MODEL.md`'s closing "no
silent forgery" section survives the exception (the evidence still always exists in the data — it is
just author-side rather than witness-side), so the narrative's headline guarantee stands; only the
"only via witness corruption" sentence overstates. Given `MODEL.md` announces itself as "the
concepts, not the full detail," this is a judgment call — flagged because the sentence is phrased as
the rule itself, not as a simplification.

## Soundness — what was attacked, and what held

A cold review that reports "no break" owes its basis. These are the attack probes I ran, grouped;
each is a place I tried to construct a failure and found the design already closes it, with the
closing rule stated where it needs to be.

### The two-secret model and the seal

- **Reverse a key change / resurrect a retired key.** Closed by "only content is buriable" plus the
  no-buried-rotation guard at the merge layer: a recovery that would drop a branch carrying an
  accepted key change is rejected, and once the recovery event is itself accepted the chain reads
  disputed — never a silent overwrite. Stated identically in the doctrine, all three merge
  documents, and all three proof matrices.
- **Append below the seal with stale authority.** The seal-cap is unconditional (no event class is
  exempt, recovery events included); a below-seal submission is rejected, and a below-seal _sealed_
  straggler is additionally dropped rather than counted (the backdate defense — see F3 for the one
  restatement gap). The "can't seal a buried chain / deadness ascends" rule closes growth on dead
  branches without follow-up events.
- **Race the legitimate rotation at the live tip.** The design's analysis is exact: after a rotation
  lands, the revealed secret's private half _is_ the current signing key, so a late rival needs the
  live signing key plus colluding witnesses, and can only force a loud, terminal dispute (a denial)
  — never a takeover. The takeover path needs the still-secret next reserve, which is the
  separately-priced reserve-theft residual. The two paths are kept distinct everywhere they appear.
- **Fabricate a historical dispute after harvesting old keys.** Closed twice over: the witness
  declines a below-seal sealed event (mirroring the seal-cap), and even a colluding-witness signing
  of one cannot overturn the live seal because the position is spent and the straggler is dead on
  ascent. The finality boundary ("the last clean seal") only ever retreats on _more_ data, the
  fail-secure direction.

### Witnessing, the floor, and convergence

- **Split one position across two witness quorums.** The witnessing floor (`threshold > signers/2`,
  a strict majority of the selected witnesses) forces any two quorums at one position to share a
  witness, and a witness signs one sibling per tier per position — so two same-tier siblings cannot
  both be accepted without a provable double-signature. The fork-cost arithmetic
  (`2·threshold − signers`, sliding with partition reach) is stated the same way in the thesis, the
  doctrine, the witnessing document, and the residuals catalogue.
- **Mint a sibling-specific witness set.** Selection is a function of position and the as-of roster
  only — never the event's bytes — so an attacker can predict a set but cannot craft an event that
  draws a favorable one. The one deliberate exception (a re-binding declares its own federation
  context, hence its own selection) is priced: it opens exactly the disjoint-federations dispute
  with author-side proof, and the documents state that exception at every site (see F6 for the one
  narrative-layer omission).
- **Exploit the stall.** A contested content position with no majority stalls rather than forks
  (signed witnesses cannot switch), and the exit — a sealed event the same witnesses may co-sign
  across tiers — is explicitly permitted by the position gate's tier scoping, with the retained
  sibling made canonical through the accepted event's ancestry. The ancestry-commit rule
  ("acceptance gates the tip; an accepted event commits its ancestry") is stated in
  `kel/verification.md` precisely where this would otherwise look like a contradiction.
- **Backdate against the clock.** Receipts carry their timestamp inside the signed payload;
  key-validity windows close at governance events and auto-expire at 365 days; superseded private
  keys are wiped; the consumer caps everything at its own clock plus one minute of tolerance. The
  "witnessed time" (the threshold-crossing receipt timestamp) is analyzed against adversarial
  receipt curation and the security-critical direction — the crossing cannot be pushed later — is
  argued from receipt durability, correctly.
- **Skew a verdict with sub-threshold noise.** Query-scoping keeps sub-threshold events on the
  selected witnesses only; every verdict counts accepted events only; the opt-in audit query is
  walk-ignored. Consistent across the doctrine, witnessing, and all three verification documents.

### Addressing, custody, and anchors

- **Two canonical forms for one content.** The canonicalization is pinned normatively (one
  serialization, integers only in the safe range, order-independent lists carried sorted-distinct,
  undeclared fields rejected), and the verify-before-substitute rule closes the lying-embedded-child
  gap. The correlation-resistance argument (two hashes, so a logged event identifier never doubles
  as the chain's lookup key) is coherent, and the store's serve-by-kind rule keeps event bodies
  unfetchable by identifier.
- **Backdate a write attribution.** The direct anchor on the owner's own chain closes it: the pin is
  a checked locator (never trusted), the anchor is append-only, and the mint-and-anchor step is
  tip-atomic (an intervening append makes the pin check fail and the object is re-minted). I probed
  the intervening-append case and the check catches it.
- **Move a credential's as-of forward or backward by re-anchoring.** The committed pin is provably
  the _earliest_ possible anchor — an earlier one would need a hash cycle, since the anchoring
  commitment embeds the credential's identifier which embeds the pin — so later re-anchors are never
  consulted and the tier-inversion (a cheap re-anchor landing after a revocation) cannot move the
  as-of. The argument is stated in `documents.md` and checks out.
- **Squat a lookup address or equivocate a data log under a linear identity.** The content flag
  rides the address derivation (content and lookups occupy different address spaces, enforced
  against the first event's tier), owner-rooting means nothing lands at a derived address without
  the owner's anchor, and the data log witnesses itself at its own position precisely because the
  owner's chain cannot see through opaque anchors. The "one content event per anchoring event" rule
  is enforceably stated (anchor-identity duplicate rejection in the SEL verifier) — an
  enforceability question I checked deliberately.
- **Hide a kill.** Negative checks are positive lookups: present means killed with no freshness
  caveat (kills are monotone); a miss is authoritative only after a walk that reached the fresh
  witnessed tip, and a walk that cannot reach it refuses rather than reporting not-killed. The
  lineaged-target discipline for re-establishable values — the one leg the primitive cannot backstop
  — is honestly flagged as a feature-layer obligation in three places and carried into the residuals
  catalogue.

### Policy, delegation, and evaluation

- **Grind a threshold with one controller.** The composition rules are explicit that counting is by
  identity prefix, that one signer fills at most one counted branch (satisfaction is a searched
  assignment, denying on budget exhaustion — so differing budgets can disagree only toward denial),
  that weights are per-identity-max, and that `and` guarantees distinct satisfiers only over
  disjoint pools. Zero thresholds and single-child/empty `and` are rejected as vacuous fail-open
  gates. An unrecognized construct denies the whole policy.
- **Collapse a delegation into the delegator, or enumerate its tree.** A self-grant is rejected; the
  walk goes up the one committed path (never down the unbounded tree), bounded by the policy's hop
  limit and the fixed depth backstop, denying on either. Rescission is a positive match with the
  grandfather bound read per hop on that hop's own chain — no cross-chain clock is ever assumed.
- **Fake the delegation signpost.** The marker grants nothing (authority is always the delegator's
  own grant list, re-verified), commits a blinded reference to the delegate that the walk
  cross-checks, and sits at tier 2 so a stolen signing key cannot plant one.

### Messaging and the features

- **Strip-and-re-sign or re-address a sealed message.** The two identity bindings (sender inside the
  sealed content, recipient in the signed cleartext) close both, and the document credits the
  construction's origin. The per-message key makes nonce reuse unreachable; the transport's
  per-direction counters do the same at the mesh layer.
- **Replay or borrow a presentation.** The one-signature-two-jobs design (ownership proof plus
  audience/nonce/time binding) closes copy-replay of a targeted credential within a single message;
  the bearer copy-race is honestly scoped to single-use instruments and "reusable transferable
  bearer" is correctly rejected as incoherent rather than deferred.
- **Backdate into a group conversation.** The lane's monotone ordering key forces a backdater to
  fork its own lane (self-proving), a removed member is bracketed by the anchored lane root and the
  witnessed removal cutoff (a local interval check needing no fork detection), and a fresh
  parentless lane is rejected because roots are anchored by the governing grant chain — with the
  two-anchored-markers case also rejected, closing the colluding-governor variant. The one accepted
  residual (a dormant, never-removed member late-filling an epoch it legitimately held) is stated
  and carried into the residuals catalogue verbatim.
- **Desynchronize the key roster from the authorization set.** The epoch's wrap set is _derived_
  (roster minus everyone rescinded, both read at the epoch's own anchoring position), so a wrap to a
  rescinded member is a visible violation rather than silent drift, and a consumer reads a member as
  removed the instant either structure records it. A partial state costs availability, never a key.
- **Un-freeze a frozen document.** Grant chains carry no re-establishment counter (monotone), so a
  freeze is permanent by construction and un-freeze is a fresh constitution — matching the
  replace-don't-resume posture used everywhere else.

### The proof matrices

I checked the three reconciliation documents (KEL, IEL, SEL) cell-by-cell against the merge and
verification documents they claim to prove sound: the local-submission positions, the source-to-sink
transfer cells (including the four guarded cells), the race matrices, the recovery-completeness
rows, and the SEL's two-axis crossing (own divergence × inherited deadness, deadness first). No cell
contradicts a rule stated elsewhere; the two "unreachable by construction" cells in the SEL's
crossing matrix are argued from acceptance gating (a sealed branch's anchor is an accepted sealed
event, never buried) and the argument holds. The disputed-owner case — not a severance case at all —
is correctly routed to the cascade-reincept rule instead.

## Verification sweeps

Mechanical checks, all clean unless noted:

- **Protocol constants** — every occurrence of every named constant agrees:
  `MINIMUM_PAGE_SIZE = 129`, `MAXIMUM_UNSEALED_RUN = 64` (and the `129 = 2·64 + 1` derivation at
  every site), `MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_MANIFEST_LIST = 128`,
  `MAXIMUM_DELEGATION_DEPTH = 8`, `MAXIMUM_SEL_LINEAGE = 64` (inclusive, stated once and
  consistently), `MAXIMUM_GRANT_ADDS = 64`, `CLOCK_TOLERANCE_BAND = 1 minute`,
  `MAXIMUM_WITNESS_KEY_WINDOW = 365 days`. The residuals catalogue's "every 64 content events"
  re-seal cadence matches.
- **Risk arithmetic** — every Severity × Exploitability product and band assignment in both ranked
  tables of `residuals.md` recomputes correctly (checked every row). The one axis-choice
  inconsistency is F2.
- **Threshold bounds** — the identity-side bounds (floor ≥ 2, ceiling ≤ roster − 1 with the
  two-member advisory case, the authorization floor, never-empty, cap 32) and the federation-side
  bounds (hard ceiling, roster ≥ 4, `threshold ≤ min(|roster| − 2, signers − 1)`,
  `signers ≤ |roster| − 1`, `signers ≥ 3`) are stated identically in the doctrine, `event-shape.md`,
  `iel/events.md`, `shapes.md` (with its general-case qualifier), `bootstrap.md`, and
  `witnessing.md`; the worked minimum-federation example (govern at 3, witness at 2 of 3) satisfies
  all of them.
- **Kind tables** — the event-kind sets, tier assignments, count slots, sort priorities, anchor
  pairings, and per-kind field rules agree across the glossary, `kinds.md`, `event-shape.md`, and
  the per-primitive documents; the receipt shape in `shapes.md` matches `witnessing.md` field for
  field.
- **Negation-only terms** — "recovery key," "repair event," and "third tier" appear only inside
  explicit negations ("there is no …"), confirming no stale positive references to retired
  constructs survive; the fingerprint-of-a-conflict is nowhere described as a digest over the
  competing versions (the retired construction) outside of explicit "not a digest over the tips"
  statements.
- **State/reading agreement** — the four-state machine, the trust-region projection, and the
  fingerprint (effective identifier) forms agree across the three verification documents and the
  doctrine, including the two tables that map them and the orthogonal termination accessor.

## Reading log

A running record of what was read, in order, so partial progress is legible if this document is
picked up mid-task.

- [x] `README.md` (repo root)
- [x] `docs/design/README.md`
- [x] 0 — Orientation: `system-thesis.md`, `glossary.md`
- [x] 1 — Data substrate: `sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`,
      `kinds.md`, `shapes.md`, `tags-and-topics.md`, `substrate/federation/topics.md`
- [x] 2 — Doctrine: `protocol-doctrine.md`, `residuals.md`, `monitoring.md`
- [x] 3 — Event logs: `event-shape.md`; KEL (`log`, `events`, `verification`, `merge`, `compromise`,
      `reconciliation`); IEL (`log`, `events`, `verification`, `merge`, `reconciliation`,
      `delegation`); SEL (`log`, `events`, `verification`, `merge`, `reconciliation`)
- [x] 4 — Federation: `bootstrap.md`, `witnessing.md`, `mesh-transport.md`
- [x] 5 — Policy: `policy.md`, `documents.md`, `evaluation.md`
- [x] 6 — Protocol primitives: `essr.md`, `ipex.md`, `receive-key-directory.md`, `group-key.md`,
      `membership.md`, `authored-dag.md`
- [x] 7 — Features: `credentials.md`, `exchange.md`, `shared-documents.md`
- [x] Companion skim: `MODEL.md` (consistency with the design surface; F6)
