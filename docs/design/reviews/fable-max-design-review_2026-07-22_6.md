# Design Review — Fable (max), 2026-07-22, round 6 (cold read)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_6.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks. don't bother checking that every constant is defined and that every
> formula matches - they do. we've been through at least 11 prior rounds of review in this PR.
> instead focus on inconsistencies or any unsoundness that affects the read.

**Reviewer:** Claude (Fable, max effort) — cold read, no context carried in from earlier rounds.
**Scope:** every document under `docs/design/` (excluding `reviews/`), plus the top-level
`README.md`, `MODEL.md`, and `USES.md` where they make claims about the design. All 41 design docs
in the reading order were read in full, in order; cross-cutting phrase sweeps were run with
`scripts/grep-terms.pl`. **Focus:** per the brief — not re-verifying constants or formula
arithmetic; looking for places where the documents contradict each other, where a stated rule does
not hold up, or where the text would mislead a careful reader.

**Status: complete.**

## Verdict

The design surface is in very good shape. Across a full cold read I found **no soundness break** —
no case where a stated rule, followed as written from its canonical definition, produces a wrong or
unsafe outcome. The parallel KEL / IEL / SEL document sets track each other closely, the cross-layer
anchor rules are stated identically from both sides of each edge, the residuals catalog matches what
the feature and primitive docs actually claim, and the narrative docs (`README.md`, `MODEL.md`,
`USES.md`) track the design — with one exception, below.

What survives eleven-plus rounds is three consistency findings: two are leftover instances of a
phrasing sweep that evidently already ran (the precise wording landed in most sites but missed a
few), and one is a flat disagreement between the plain-English narrative (`MODEL.md`) and the design
surface about what a takeover victim can do. None undermines the design; all three can mislead a
careful reader who lands on the wrong site first.

## Summary of findings

| #   | Kind        | Severity | Where                                                                       | One line                                                                                                                                                                                                                       |
| --- | ----------- | -------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F1  | consistency | moderate | `iel/log.md` §The seal; `protocol-doctrine.md` §Terminology + §Divergence   | The tracked-seal definition survives in a superseded "no competing sealed **sibling**" form at three sites; read alone, it computes the wrong seal when two accepted sealed branches seal at different serials.                |
| F2  | consistency | minor    | `kel/verification.md` `region()` + terminal-state rule                      | The compressed "at the last seal" locative survives in the KEL verifier's two operative Disputed statements, where the IEL and SEL twins carry the precise "per branch, wherever their seals sit" gloss.                       |
| F3  | consistency | moderate | `MODEL.md` §The one guarantee to remember vs `iel/log.md` + `witnessing.md` | `MODEL.md` says a takeover victim "has no way to turn it into a visible dispute"; the design surface says a cross-federation rebind can force Disputed with no collusion. Both absolutes are wrong — the truth is conditional. |

No other findings. Everything else checked is catalogued under "What was checked and reads sound."

## Findings

### F1 — The tracked-seal definition exists in two non-equivalent forms (consistency, moderate)

The chain's **tracked seal** (also "derived seal") is the anchor for the seal-cap, the locked
portion, and the pre-seal finality claims — one of the most load-bearing definitions in the design.
It is stated in two registers:

- **The precise form** — "the most recent seal-advancing event with no competing accepted sealed
  **branch from the divergence onward** (… a fork with ≥ 2 accepted sealed branches has no clean
  seal above the divergence)". This is the form at the definitional site (`protocol-doctrine.md`
  §Forks are Seal-Bounded, ~line 304), in `kel/log.md`'s seal table (~line 121), and in all three
  verification tokens (`kel/verification.md` ~228, `iel/verification.md` ~240, `sel/verification.md`
  ~243).
- **A superseded form** — "the most recent seal-advancing event with no competing accepted sealed
  **sibling**" — at three sites:
  1. `iel/log.md` ~line 122 (the seal table — the direct twin of `kel/log.md`'s corrected row), with
     no compensating clause;
  2. `protocol-doctrine.md` ~line 440 (§Divergence and recovery, "the reading is a pure walk"), with
     no compensating clause on the seal derivation itself;
  3. `protocol-doctrine.md` ~line 75 (§Terminology, the "Locked" bullet) — the least severe, since
     the same sentence continues "a seal-advancing event that is one of two competing accepted
     sealed **branches** never becomes the lock," which restores the branch-level meaning.

**Why the difference matters.** The two forms disagree exactly in the case the docs elsewhere take
pains to cover: a dispute whose two accepted seals sit at **different serials**. Take a fork at
serial `d` where branch A's divergent event is itself a seal and branch B runs content at `d`,
`d+1`, then seals at `d+2` (both branches accepted — the collusion or cross-federation case). The
two seals are not siblings of each other — A's seal's same-serial sibling is B's _content_ event —
so under the "no competing accepted sealed sibling" reading, A's seal qualifies as the tracked seal.
Under the canonical reading it does not: there is no clean seal above the divergence, and the
finality boundary retreats to the event before the fork (`v_{d-1}`), which is what the Disputed
reading, the effective-SAID synthetic, and the pre-seal-verifiability retreat all assume ("counted
per branch, wherever their seals sit"). A reader — or an implementer — who takes the definition from
`iel/log.md`'s table or from `protocol-doctrine.md` ~440 alone derives a seal one branch deep into a
disputed fork, and the finality boundary, the `Sealed`-rejection line, and the sealed-branch count
all shift with it.

**This looks like straggler residue of an already-applied fix.** The KEL-side table and all three
tokens carry the precise wording; the IEL-side table and two doctrine sentences do not. The design
intent is unambiguous — every full statement of the Disputed rule is branch-level — so this is a
wording repair, not a design question: bring the three sites onto the "sealed branch from the
divergence onward" form (the §Terminology site can keep its compensating clause or drop it once the
definition itself is precise).

### F2 — "At the last seal" survives in the KEL verifier's operative Disputed statements (consistency, minor)

The Disputed condition is stated across the surface in two registers: the precise "≥ 2 accepted
sealed branches, counted **per branch, wherever their seals sit**" and a compressed locative, "≥ 2
accepted sealed branches **at the last seal**." In most places the compressed form is harmless — it
names where the fork is _anchored_ (the window at or above the last clean seal, as opposed to a
below-seal straggler, which is dropped) and a nearby sentence carries the per-branch gloss.

Two sites are the exception, because they are the operative definitions and their sibling docs were
evidently updated while they were not:

- `kel/verification.md`, the `region()` accessor (~line 263): "**disputed** (two or more branches
  each carry an accepted (witnessed-at-threshold) sealed event **at the last seal** — terminal,
  reincept)".
- `kel/verification.md`, the terminal-state determination rule (~line 361): "Two or more accepted
  (witnessed-at-threshold) sealed branches **at the last seal** → disputed".

The IEL twin of both sentences says "per branch, wherever the seal sits" (`iel/verification.md` ~277
and ~365), and the SEL twin says simply "two or more accepted sealed branches"
(`sel/verification.md` ~276). Read cold, the KEL wording invites the same-position misreading — that
both seals must sit at the seal's own serial — which the KEL's own reconciliation doc explicitly
rules out ("the count is per branch, wherever their seals sit"). Since a dispute with seals at
different serials still forms a single spine fork (both seals share one back-link to the prior
seal), nothing else in the KEL docs bails the reader out at these two sites. Recommend the same
per-branch gloss the IEL twin carries. (The remaining "at the last seal" sites — e.g.
`kel/reconciliation.md` Matrix 4's row 4 — are internally glossed by their own §Convergence text,
"at or above the last clean seal," and read fine.)

### F3 — `MODEL.md` denies the dispute-forcing option the design documents (consistency, moderate)

On what a victim of a rotation-reserve takeover can do, the narrative and the design surface flatly
disagree:

- `MODEL.md`, §The one guarantee to remember: "**The owner has no way to turn it into a visible
  dispute — there is no forced fork to surface.** Watching the chain doesn't change that; it only
  means the owner notices sooner. **To a third party the takeover reads as an ordinary rotation
  either way.**"
- `iel/log.md`, §Forked versus Disputed: "(A **cross-federation** rebind **can force Disputed** with
  no collusion — the owner still knows the reserve — but that recovers nothing, and reincept is the
  recourse either way.)"

The design surface backs `iel/log.md`: `witnessing.md` §Rebinding states that two rebinds at one
serial naming different federations select disjoint witness sets, so **both** reach threshold with
no witness double-sign (the dispute is proven author-side), and `protocol-doctrine.md`'s
misbehavior-proof section carries the same cross-federation arm. Theft copies the reserve rather
than removing it, so after the attacker's rotation lands, the owner still holds the revealed
preimage and can author the competing rebind. The mechanism exists.

The precise truth is **conditional**, and neither sentence carries the condition: per
`witnessing.md`, "a verifier trusting only one side of such a race reads only that side accepted" —
so the forced dispute is visible only to relying parties whose configured trusted-federation set
includes **both** federations. A relying party pinned only to the original federation still reads
the attacker's chain as clean. So `MODEL.md`'s "no way" is wrong as stated (and materially so — it
tells an owner planning incident response that no in-band surfacing exists, when rebinding toward a
federation their relying parties also trust would flip those parties from trusting the attacker to
refusing, which is not nothing), while `iel/log.md`'s "can force Disputed" is right but silently
scoped to two-federation verifiers, and its "recovers nothing" undersells the notification value for
exactly those verifiers.

Recommended repair: fix `MODEL.md` to the conditional statement (the takeover itself forces nothing
and double-signs nothing — that part is right — but a vigilant owner _can_ surface it in-band to
verifiers that trust both federations, at no recovery benefit to the prefix itself); optionally have
`residuals.md`'s rotation-reserve-theft entry mention the option alongside "reincept + notify
relying parties," since notification is exactly what that entry is about. (`residuals.md`'s own
"there is no structural veto" and `monitoring.md`'s "no competing branch, no dispute, no veto"
describe the takeover moment and stay accurate; only `MODEL.md` makes the absolute forward-looking
claim.)

## What was checked and reads sound

For digestibility, grouped by the reading-order layers. "Sound" here means: internally consistent,
consistent with the docs it cites and the docs that cite it, and — where the doc argues a security
property — the argument holds up under the adversarial readings I could construct against it.

### Orientation and narrative (README, system-thesis, glossary, MODEL, USES)

- The thesis's two decision trees (prevention view in `system-thesis.md`, resolution view in
  `protocol-doctrine.md`) agree with each other and with the four-state machine everywhere it is
  restated; each explicitly names the other as its companion.
- The glossary's one-liners match the owning docs' definitions, including the deliberately tricky
  entries — the two senses of "retain," the `Terminated` / `Terminal` / `Trm` near-homographs, the
  narrow sense of "governance," the "floor `Pin`" epithet (explicitly disambiguated: every `Pin`, at
  any serial, is tier-1 buriable content), and the witnessed-versus-accepted split.
- `MODEL.md`'s simplifications track the design (the roster cap of 32, the three-device floor and
  the two-device freeze, first-seen for both event classes, the forensic reading of a double
  rotation versus a double roster change, the stable conflict marker never listing competing
  versions, revocation as a positive declaration with the fail-open fast path as an opt-down) — with
  the single exception in F3.
- `USES.md` claims only what the features provide; the composition lists match the feature docs' own
  dependency statements.

### The data substrate (sad, said, custody, availability, compaction, kinds, shapes, tags-and-topics)

- The two-hash inception derivation, the placeholder rule, the compact-down canonical form (Rules 1
  and 2), the ascending-set rule, and the exhaustive-schema gate are stated once and referenced
  consistently everywhere else; the signing-surface discipline (schema-detected full expansion with
  an explicit override) is coherent with compaction's "one SAID covers every faithful disclosure."
- Custody's `owner`/`pin` pair, the direct-anchor commitment formula, and the four combinations are
  restated identically in `shapes.md`, `event-shape.md`, `documents.md`, and `credentials.md` (the
  credential is consistently the named instance, with body fields standing in for the custody pair).
- The kinds and shapes catalogues, the tags/topics catalogue, and the gossip-topics catalogue keep
  the three identifier families (SAD kinds, derivation tags + SEL topics, mesh channels) cleanly
  apart, and every family member referenced from another doc appears in its catalogue (per the brief
  I did not re-verify the constants and formulas — spot checks along the way all agreed).
- The store's served-by-SAID line ("hands back a SAD by SAID only when learning that SAID already
  meant holding the chain, or when the SAD is public by design") is consistently applied: events by
  prefix only, commitment SADs and grant values served, wraps member-delivered, blobs by digest
  through the request gate.

### Cross-cutting doctrine (protocol-doctrine, residuals, monitoring)

- The tier model (two tiers, kind-strict anchoring, no recovery key, single-stream pre-rotation) is
  stated identically at every site; sweeps for "recovery key," "dual signature," and a third tier
  find only the deliberate negations.
- The divergence-and-recovery machinery — freeze as an origination posture, the pure-walk reading,
  burial by position + ascent, deadness-ascends, retention floors versus the accept-up-to-two cap,
  the below-seal straggler drop (the backdate defense), the no-buried-rotation guard with
  retain-and-count for accepted seals versus drop for declined ones, and the tier-rank `Trm`
  carve-out — is consistent between the doctrine and all three primitives' merge/reconciliation
  docs, including the arrival-order-independence arguments.
- The `Rev`/`Dth`-are-non-terminal rule is uniformly applied (`{Rev, content}` recovers like
  `{Evl, content}` everywhere it appears), as is the "a `Rev` proceeds on `forked`" consequence.
- `residuals.md`'s entries each match the mechanism docs they price (severity axes and the ranked
  rows agree with the entries; the feature-level residuals — chat's single-signature authenticity,
  the open-epoch future-dating, the lane-backdate decomposition, the communication-graph and
  inbox-hint exposures, the batch-anchor linkage — are restated verbatim-in-substance in
  `exchange.md` and the primitives).
- `monitoring.md`'s claims (detects, never prevents; the effective-SAID comparison as the whole
  detector; a lying monitor costs latency never correctness) are consistent with the effective-SAID
  and witnessing doctrine.

### The event-log primitives (event-shape; kel/, iel/, sel/)

- The manifest role vocabulary, the kind→role allowlist, the per-kind field grids, and the
  cross-layer anchor matrices are mutually consistent between `event-shape.md` and the per-log docs,
  and the two sides of every anchor edge state the same matrix (IEL→SEL from both `iel/events.md`
  and `sel/events.md`; KEL→IEL from `kel/events.md` and `iel/verification.md`).
- The three verification docs' tokens expose parallel surfaces, and their accessors' state tables
  (chain state × region × effective-SAID, plus the IEL's roster projection and its
  freeze-T1/seal-out-with-T2 gate) are consistent with the doctrine and with each feature that
  consumes them (IPEX's and credentials' divergence-freeze clauses cite and match the IEL gate).
- The four reconciliation proofs are internally coherent and mutually consistent: the KEL and IEL
  matrices mirror each other with the mixed-chain and eviction deltas called out; the SEL's two-axis
  matrix composes deadness-precedence correctly, and its two "unreachable by construction" cells are
  each justified by a stated invariant (a `Trm`'s sealed anchor is never buried alone; SEL
  acceptance gates on an accepted — hence sealed, hence never-buried — anchor) with the honest
  for-completeness fallback given anyway.
- The enforceability of the SEL's "≤ 1 content `Ixn` per owner-IEL `Ixn`" rule is now explicit
  (anchor-identity dedup in the verifier's per-event checks), and the identity bond's two
  enforcement points (serial-1 anchor check; roster-admission check) close the re-add and
  two-identity cases they claim to.
- The facet-dependent `Wit` is guarded on every reading path in every doc that touches it (`events`,
  `verification`, `merge` on the IEL side; the KEL's `root_facet` token field), with the same
  rationale (the allowlist is the directly-consumed roles' only gate).

### Federation and witnessing (bootstrap, witnessing, topics, mesh-transport)

- The bootstrap's non-circularity story (authorization ordinary, trust-rooting out-of-band, the
  `Fcp` a marker not a carve-out) is the same story `kel/events.md` and `event-shape.md` tell; the
  dependency-ordered bundle and the joining-witness pair match on all sites.
- The witnessing floor, fork-cost and its partition slide, the tier-scoped first-seen ladder with
  the cross-tier co-sign, the split-stall and its exit, the currency gate versus the clock's two
  jobs, exclude-self peer-witnessing and the recoverability cap arithmetic (`|roster| ≥ 4`,
  `{threshold 2, signers 3}` at the floor), the witnessed-time definition and its
  byzantine-robustness argument, query-scoping, and the rebind rules (including the one honest
  no-collusion dispute) are each stated once here and consumed consistently by the doctrine, the
  primitives, and the features.
- The mesh transport's claims (confidentiality only; witnessed-key-bound authentication; nonce reuse
  structural) stay inside what the witnessing docs assume of it.

### Policy and documents (policy, documents, evaluation)

- The two-mechanism split (structural chain authorization; relying-party document policy) is stated
  identically at every boundary it touches, and the language's composition rules (distinct-identity
  counting as set-packing with deny-on-budget, per-identity-max weight, `and` over pools,
  unknown-construct denial) are self-consistent and fail-secure throughout.
- The anchoring-position model — `issuerPin` as a checked locator, provably the earliest anchor by
  hash-preimage order, re-anchors never consulted (closing the tier-inversion un-revoke) — is
  consistent between `documents.md`, `credentials.md`, and `custody.md`.
- The delegation surface (committed `delegationPath`, per-hop grandfather on each hop's own chain,
  the delegating-link as a re-verified signpost with the blinded delegate reference, monotone
  rescission with replace-don't-resume) matches across `policy.md`, `documents.md`,
  `iel/delegation.md`, and the residuals' delegation-scope entries.

### Protocol primitives and features (essr, ipex, receive-key-directory, group-key, membership, authored-dag; credentials, exchange, shared-documents)

- ESSR's four guarantees and two bindings, IPEX's two proofs and single-round-trip freshness gate
  (with its full clause list), the directory's tier-2 publish rule and the first lineaged-target
  obligation, group-key's two-structure model with the derivation rule that keeps the wrap roster
  and the membership set from drifting, membership's two check modes with the
  disclose-your-own-entry mechanism that keeps the fail-secure walk store-performable, and the
  authored DAG's two variants with the anchored-root and `[root … bound]` interval checks — each is
  stated once, consumed by name elsewhere, and the boundary ("what this is not") lists are mutually
  exclusive and jointly cover what the features then wire together.
- `credentials.md`'s acceptance conjunction, bearer redemption-as-revocation, claim-gating (uniform
  bracket sets, renewal-on-threshold), edges, terms acceptance-requires-sight, bulk issuance trade,
  and registrar migration flow are consistent with the primitives they cite and with the residuals
  catalog.
- `exchange.md`'s two modes, payload-by-digest with the integrity/advisory split, the two-axis
  sender-key currency (with the divergence freeze matching the IEL gate), the mail serve-time gate
  (IEL-roster, not quorum), and chat's lane/epoch/bound machinery are consistent with group-key,
  membership, authored-dag, witnessing (witnessed times), and the residuals catalog.
- `shared-documents.md`'s honored predicate (all three positions on the editor's own chain), the
  sealed-not-fetched grant rule with its stated seal-locate cost, disjoint periods at document
  validation, freeze as bound-all + terminate with no `lineage` (permanence), comments mirroring the
  window but not the citation path, and the off-node sovereignty mode ("no node operation may
  require a content SAD") are internally coherent and consistent with membership, authored-dag,
  group-key, custody, and `shapes.md`.

## Reading log

- [x] README.md (top level)
- [x] docs/design/README.md
- [x] 0 — system-thesis.md, glossary.md
- [x] 1 — sad.md, said.md, custody.md, availability.md, compaction.md, kinds.md, shapes.md,
      tags-and-topics.md
- [x] 2 — protocol-doctrine.md, residuals.md, monitoring.md
- [x] 3 — event-shape.md; kel/ (log, events, verification, merge, compromise, reconciliation); iel/
      (log, events, verification, merge, reconciliation, delegation); sel/ (log, events,
      verification, merge, reconciliation)
- [x] 4 — federation/ (bootstrap, witnessing, topics); infrastructure/mesh-transport.md
- [x] 5 — policy/ (policy, documents, evaluation)
- [x] 6 — protocols/ (essr, ipex, receive-key-directory, group-key, membership, authored-dag)
- [x] 7 — features/ (credentials, exchange, shared-documents)
- [x] MODEL.md, USES.md (consistency with design)
