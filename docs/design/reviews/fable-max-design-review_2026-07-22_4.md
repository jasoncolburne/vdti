# Design Review — Fable (max), 2026-07-22, round 4

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_4.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

**Reviewer:** Claude (Fable, max effort), cold pass — no prior review files consulted. **Scope:**
every document in `docs/design/` per the reading order in `docs/design/README.md`, plus the
repository `README.md`, `MODEL.md`, and `USES.md` as entry points. **Focus:** correctness and
soundness (does the argument hold; is the check enforceable; does the rule survive an adversary) and
consistency (do the documents agree with each other).

**Status: COMPLETE.** All 41 design documents were read in the prescribed order, plus the three
root-level entry documents; the phrase sweeps ran over the whole tracked surface.

---

## How this review reads the design

Each layer is read in the order the design prescribes, bottom-up. For every finding I quote or cite
the exact line so it can be checked. Findings are graded:

- **[critical]** — the design as written is wrong or unsound: an attacker wins, or two documents
  give incompatible rules on a load-bearing point.
- **[major]** — the argument has a hole or an ambiguity big enough that an implementer could build
  the wrong thing in good faith.
- **[minor]** — a real inconsistency or gap, unlikely to mislead an implementer who reads carefully.
- **[note]** — an observation worth recording; no change strictly required.

---

## Verdict

The design surface is in very strong shape. I found **no critical and no major findings**: no place
where an attacker wins against the rules as written, no pair of documents giving incompatible rules
on a load-bearing point, and no stated check that turned out to be unenforceable when pressed. The
arguments I pressure-tested hardest — the honest-case single-accepted-sealed-branch claim, the
page-size accounting, the `issuerPin` earliest-anchor proof, the severance-cannot-downgrade-Disputed
claim, the re-seal dedupe-versus-collide distinction, and the shared-documents honored predicate
with its two bypass candidates — all held. The four findings below are two localized specification
gaps, one emphasis mismatch, and one narrative-layer mechanism misattribution; none blocks
implementation, and each has a small, local fix.

## Summary of findings

| ID  | Grade | Where                                                                                  | One-line summary                                                                                                                                                                                                         |
| --- | ----- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F1  | minor | `witnessing.md` §The recoverability cap (with `event-shape.md`, `iel/verification.md`) | The federation's "exclude-self" witnessing is specified at three altitudes the reader must assemble; no single passage says who receipts a federation IEL event, over which pool.                                        |
| F2  | minor | `witnessing.md` §Rebinding                                                             | No operational guidance for retrying a stalled rebind — a sibling retry toward a different federation self-disputes the prefix, while chaining the retry is safe; the safe pattern is derivable but never stated.        |
| F3  | note  | `protocol-doctrine.md` §Federation convergence vs `residuals.md` §Fork-cost            | Fork-cost is presented flatly as `2·threshold − signers` in the doctrine; the residuals catalog's sharper full-`threshold`-sliding-to-the-floor pricing deserves a pointer so evaluators do not under-price the defense. |
| F4  | minor | `MODEL.md` §An issued artifact rides its owner's identity                              | Artifact fork-prevention is attributed to the identity anchor; the design says the anchor cannot prevent a same-position artifact fork — the artifact log's own witnessing does.                                         |

Everything else this review checked — the layer-by-layer records are in the groups below — came back
consistent: the two-tier model, the divergence machinery, the constants, the kind-strict anchor
matrices, the threshold bounds, the negative-check discipline, the token surfaces, and the residuals
catalog's arithmetic and claims.

## Findings

Findings are numbered F1, F2, … in reading order and grouped by layer. Each names the file(s) and
line(s) it rests on.

### Group A — Orientation and the data substrate (thesis, glossary, SAD/SAID/custody/availability/compaction, catalogues)

**Read:** `README.md`, `system-thesis.md`, `glossary.md`, `sad.md`, `said.md`, `custody.md`,
`availability.md`, `compaction.md`, `kinds.md`, `shapes.md`, `tags-and-topics.md`.

This group is in strong shape. Cross-checks that came back clean:

- The two-tier capability model, the threshold-vector counts, and the four chain states are stated
  identically in the thesis, the glossary, and the doctrine.
- The custody anchor formula `hash('vdti/iel/v1/actions/commitment:{owner}:{said}')` in `custody.md`
  matches the tag catalogue's `vdti/iel/v1/actions/commitment` row and the credential instance in
  the doctrine (`{issuer}:{cred.said}`).
- The witness-config bounds in `shapes.md` (`signers/2 < threshold ≤ signers ≤ |roster|`) match the
  doctrine's witnessing floor, and the federation's tighter bounds
  (`threshold ≤ min(|roster| − 2, signers − 1)`, `|roster| ≥ 4`, `signers ≥ 3`) are jointly
  satisfiable exactly as the doctrine's worked example says (4 witnesses → 3 signers → threshold 2).
- The number rule in `said.md` (every JSON number an integer within ±(2⁵³−1), larger values as
  strings) is respected by the shapes catalogue: timestamps are RFC 3339 strings, not numeric epoch
  values, so no field risks the double-precision cliff.
- The strictly-ascending set rule (`said.md`, `custody.md` `readers[]`, the roster deltas) is stated
  with the same producer-sorts / verifier-rejects semantics at every site.
- The "events are never fetchable by SAID" rule (`sad.md`, `kinds.md`) is stated consistently with
  the serve-list in `kinds.md`, and the one-line test ("holding the SAID already meant holding the
  chain, or public by design") correctly classifies every kind the catalogue lists.

### Group B — Cross-cutting doctrine (protocol-doctrine, residuals, monitoring)

**Read:** `protocol-doctrine.md`, `residuals.md`, `monitoring.md`.

The doctrine is dense but internally coherent; the divergence machinery (freeze, burial by
position + ascent, accepted-sealed-branch counting, the below-seal-straggler drop) is stated the
same way in the thesis, the doctrine, and the glossary. The residuals catalog's risk arithmetic
(severity × exploitability = risk band) checks out row by row, and its entries match the doctrine's
claims (the brick residual correctly notes a same-position rival seal needs the current signing key
plus witness collusion, not the reserve).

Deferred verification points carried into the primitive-layer reading (resolved in later groups):

- The page constant `MINIMUM_PAGE_SIZE = 129 = 2·MAXIMUM_UNSEALED_RUN + 1` — confirm the accounting
  (two branches of ≤ 64 plus the burying seal) against the KEL paging rules, including whether the
  shared ancestor must fit the same page.
- The federation's "exclude-self" witnessing (`signers ≤ |roster| − 1`) — confirm how self-exclusion
  is defined when a quorum of the roster co-authors the event being witnessed.
- The cross-federation rebind: two rebind `Wit`s naming different federations are the author-side
  dispute case; confirm the witnessing doc addresses the honest-retry hazard (a stalled rebind
  re-issued toward a different federation would reveal the same reserve twice).
- The verification token's `divergence_ancestor` — confirm the verdict-coupled definition in
  `tags-and-topics.md` matches the token definition in the verification docs.

### Group C — Event shape and the KEL primitive

**Read:** `event-shape.md`, `kel/log.md`, `kel/events.md`, `kel/verification.md`, `kel/merge.md`,
`kel/compromise.md`, `kel/reconciliation.md`.

Three of the four deferred checks from Group B resolve cleanly here:

- **Page constant** — `kel/log.md` and `reconciliation.md` invariant 3 give the full accounting: the
  two fork branches (≤ 64 each) plus the burying seal-advancer are exactly 129 events, the shared
  ancestor is validated from earlier pages, and the two shapes that legitimately exceed one page (an
  own-rotation inside the retained tail; a three-or-more-branch residual fork) are explicitly
  enumerated with how they ride adjacent pages. No off-by-one.
- **`divergence_ancestor`** — `kel/verification.md` defines it verdict-coupled ("Forked: the first
  divergence; Disputed: the earliest divergence carrying ≥ 2 accepted sealed branches"), identical
  wording to the tag catalogue. Consistent.
- **Founding-member anchoring** — `kel/events.md` §The identity bond enumerates the four chain
  openings (genesis witness `Fcp→Rot`, added witness `Fcp→Ixn`, initial member `Icp→Rot`, added
  member `Icp→Ixn`), which resolves how a tier-2 IEL inception is anchored (each founder's serial-1
  `Rot`) while joiner consent stays tier-1. This matches the kind-strict matrix in the doctrine and
  `event-shape.md` exactly.

I specifically pressure-tested the honest-case claim that at most one accepted sealed branch can
exist without collusion, since the whole Disputed machinery rests on it. The argument holds: the
per-position gate admits one content and one sealed sibling; a sealed sibling at the fork position
buries the content sibling (its parent now sits below the seal, dead on ascent), so the content
lineage can no longer carry a countable seal; and a two-content fork requires a double-sign for both
to be accepted before either can seal. The three mechanisms interlock with no gap I could find, and
the same reasoning is stated consistently in the doctrine, `kel/log.md`, `kel/merge.md`, and
reconciliation Matrix 4.

Also verified: the merge outcomes vocabulary is byte-consistent between `merge.md` and
`reconciliation.md`; the spent-reserve reading ("the revealed reserve's private half is the current
signing key") is stated identically in `log.md`, `events.md`, `compromise.md`, and the residuals
catalog's brick entry; and Matrix 2's abbreviated cells are completed by their footnotes (the
Active-source → Terminated-sink cell covers only the honest content case in the cell, with the
sealed-sibling → Disputed case carried by the routing note).

### Group D — The IEL primitive

**Read:** `iel/log.md`, `iel/events.md`, `iel/verification.md`, `iel/merge.md`,
`iel/reconciliation.md`, `iel/delegation.md`.

Checks that came back clean:

- The threshold-vector bounds are identical in the doctrine, `event-shape.md`, and `iel/events.md`
  (floor ≥ 2 on authority slots, ceiling ≤ roster − 1 advisory at two members and hard at three or
  more, the authorization floor, roster cap 32, never-emptied), and the small-roster arithmetic
  works at every size (at two members the ceiling must be advisory or the floor would be
  unsatisfiable — the docs say exactly that, and the residuals catalog carries the two-member freeze
  as its own entry).
- Two independent re-seal ceremonies are claimed byte-distinct because their `pins` differ. I
  checked whether the claim is enforceable: it is — a member authoring two participations from one
  KEL tip would have to double-reveal its own reserve (a member-KEL dispute), so distinct ceremonies
  necessarily carry distinct pins. The dedupe-versus-collide line is real, not aspirational.
- The IEL merge/reconciliation matrices mirror the KEL's cell-for-cell with the mixed-chain
  additions (position gate on content, the `cut` `Evl` atomicity argument, the sealed sub-split),
  and the `{Evl, Evl}`-requires-collusion claim is consistent with the same-tier first-seen rule
  everywhere it appears.
- The delegation surface (`Ath.delegates` as the authority, the delegating-link SEL as a re-verified
  signpost, the rescission `target` mirroring the tag catalogue's `rescission` tag, the public
  delegate `bound` versus the gated doc-member `bound`) is stated identically in `delegation.md`,
  `iel/events.md`, `iel/verification.md`, and the tag catalogue.
- The facet-dependent `Wit` allowlist (user rebind versus federation governance) is enforced with
  the root facet established before any `Wit` payload read on every path, stated in `events.md`,
  `verification.md`, and `merge.md` with the same no-exemption language — this closes the
  governance-role smuggling hole the docs call out.

### Group F — The SEL primitive, federation, and witnessing

**Read:** `sel/log.md`, `sel/events.md`, `sel/verification.md`, `sel/merge.md`,
`sel/reconciliation.md`, `substrate/federation/bootstrap.md`, `substrate/federation/witnessing.md`,
`substrate/federation/topics.md`, `substrate/infrastructure/mesh-transport.md`.

Checks that came back clean:

- The historically-flagged "at most one content `Ixn` per SEL per owner-IEL `Ixn`" rule is now
  stated **with its enforcement mechanism**: the SEL verifier resolves every SEL event's anchor, so
  a second content event resolving to the same anchoring IEL event is detectable and rejected
  (anchor-identity dedup, `sel/events.md` and the `sel/verification.md` pseudocode). The check is
  performable from data the verifier already holds — the enforceability gap is closed.
- The lineage model is consistent everywhere it appears: `MAXIMUM_SEL_LINEAGE = 64` as an inclusive
  highest index, the lineaged versus non-lineaged versus `:content` kill-target mirror, the
  positive-walk-consumes-the-negative-check composition, and the honestly-flagged feature-layer
  obligation (a value rescission must declare the matching lineaged target — stated identically in
  `sel/verification.md`, `sel/reconciliation.md`, and the residuals catalog's §11).
- The two-axis SEL matrix (own divergence × inherited deadness) is careful about its "unreachable by
  construction" rows and gives a for-completeness fallback for each; the claim that severance can
  never downgrade a Disputed rests on "SEL acceptance gates on the anchor being accepted, and an
  accepted IEL sealed anchor is never buried" — which I verified against the IEL rules (sealed
  events are indeed never buried; a Disputed owner identity is folded into the both-anchors-dead row
  plus the cascade rule in the doctrine).
- The federation bootstrap's non-circularity argument (authorization is ordinary member anchoring;
  trust is the configured prefix pin; the `Fcp` marker is interpretation, not vouching) is honest
  and holds up; the genesis verification checklist is complete.
- The rebind model resolves the Group-B deferred check: two rebinds at one serial naming different
  federations are the one honest-witness route to Disputed, priced as author-side equivocation, and
  the migration-overlap-versus-hard-cutover split is stated plainly.
- The mesh transport's nonce argument (per-direction keys, strictly increasing counters, no
  mid-session rekey needed) is structurally sound, and the handshake binds identity to the session
  by signing the transcript against the witnessed key state.

The two real findings from this group:

**F1 [minor] — the federation's "exclude-self" witnessing is specified at three altitudes that the
reader must assemble, and "self" is never pinned for a collectively-authored event.**
`event-shape.md` says the federation IEL "realizes [the position gate] via exclude-self
peer-witnessing"; `iel/verification.md` says "its witnesses witness each other exclude-self, so a
governance event needs a peer majority first-seen at its serial"; `witnessing.md` §The
recoverability cap derives the bound from member witness-KELs witnessing "each other's KEL events, a
witness never receipting its own", with the eviction case's pool arithmetic (`|roster| − 2`,
`signers − 1`) resting on that per-KEL reading. The per-KEL reading is coherent and the arithmetic
works (at four witnesses: a survivor's anchoring event can be receipted by the other two survivors),
but an implementer has to reconstruct that the federation event's own-position gate is realized
through its anchoring member-KEL events' peer receipts plus quorum overlap — no single passage says
who signs a receipt _for a federation IEL event itself_, over which pool, and what first-seen
decline means at that position. Since the kind → role allowlist docs elsewhere insist on exactly
this kind of single-statement precision, the federation position gate deserves one canonical
statement in `witnessing.md`.

**F2 [minor] — no operational guidance for retrying a stalled rebind; the sibling-retry footgun
self-disputes the prefix.** `witnessing.md` §Rebinding explains that two rebinds at one serial
naming different federations both reach acceptance on disjoint witness sets and dispute the prefix,
proven author-side. What no doc states is the operational consequence: an owner whose rebind toward
federation B stalls (B unreachable) and who then re-issues toward federation C **as a sibling at the
same serial** destroys their own prefix — while chaining the second rebind **on top of** the stalled
one is safe (the design already supports it: a submitter's own sub-threshold events are its local
tip, and acceptance of a later event commits its ancestry). The safe pattern is derivable from three
separate passages but never stated; one sentence in §Rebinding ("retry a stalled rebind by chaining,
never as a sibling") would close a real self-brick hazard. The residuals catalog's related entry
(the replicated-reserve self-dispute) does not cover this case.

**F3 [note] — fork-cost is priced with different emphasis in the doctrine versus the residuals
catalog.** The doctrine and `witnessing.md` present `2·threshold − signers` as _the_ fork-cost
("manufacturing one costs owning the whole quorum intersection"), while `residuals.md` §Fork-cost
gives the sharper statement: a full `threshold` of colluders with no partition, sliding down to
`2·threshold − signers` only when the attacker also controls delivery to every honest witness (total
partition). The two are consistent — the floor is the same number — but an evaluator reading only
the doctrine could under-price the defense (the attacker needs delivery control _in addition to_ the
intersection). Since the residuals entry already says this well, a one-line pointer from the
doctrine's fork-cost definition would align the emphasis.

### Group G — The policy layer

**Read:** `policy/policy.md`, `policy/documents.md`, `policy/evaluation.md`.

Checks that came back clean:

- The `issuerPin` earliest-anchor argument in `documents.md` is a genuine proof, and I verified it:
  the issuance commitment embeds the credential's identifier, which embeds `issuerPin`, which is the
  identifier of the event immediately before the anchor — so an anchor at any earlier position would
  require a hash cycle. This is what closes the tier-inversion re-anchor attack (a later tier-1
  re-anchor silently moving the as-of past a revocation), and the argument is stated correctly.
- The distinct-identity counting rule is honest about its hardness: satisfaction over quorum
  branches is defined as an assignment search (a set-packing check, not a greedy pass), bounded by
  the verifier work budget, with budget exhaustion denying — so differently-budgeted verifiers can
  disagree only toward denial. That is the right fail-secure shape for a non-consensus-critical
  evaluation.
- The vacuous-gate rejections (zero thresholds, one-child `and`), the unknown-construct
  deny-the-whole-policy rule, and the acyclicity-by-hash termination argument are all sound and
  consistently stated.
- The `id(X)`-resolves-`t_use` decision is stated with its rationale in both `policy.md` and
  `documents.md`, and the as-issued-only mode (no live policy evaluation; who-may-present is a
  challenge, read-gating is a membership) is consistent with `evaluation.md`, `ipex.md`, and
  `credentials.md`.
- The attestation-SEL construction in `documents.md` (recomputable address from the attested
  document's identifier, `content: true`, serial-1 `Pin` at `t_use`) satisfies the SEL layer's
  biconditional and entropy rules exactly as the SEL docs state them — including the subtlety that a
  private document's high-entropy identifier is what keeps the attestation address unguessable.

### Group H — Protocol primitives and features

**Read:** `protocols/essr.md`, `protocols/ipex.md`, `protocols/receive-key-directory.md`,
`protocols/group-key.md`, `protocols/membership.md`, `protocols/authored-dag.md`,
`features/credentials.md`, `features/exchange.md`, `features/shared-documents.md`.

Checks that came back clean:

- ESSR's four guarantees are correctly derived from the two identity bindings, and the construction
  matches the shapes catalogue field-for-field (including the digest-is-integrity / size-is-advisory
  split and the fresh-per-message key that makes the nonce safe). The prior-art credits are accurate
  about what is adopted versus adapted.
- IPEX's single-round-trip freshness envelope holds up under the replay cases it enumerates
  (replay-to-me, replay-elsewhere, present-someone-else's, swap-into-captured-envelope, forge), and
  the two-sided timestamp window plus cache-retention coupling is correctly reasoned. The
  divergence-freeze on live presentation matches the IEL token's T1-freeze rule exactly.
- The membership/group-key pairing is coherently split (unbounded never-enumerated authorization
  versus bounded gated wrap roster), and the two-structure removal-drift question is answered with a
  derivation rule (wrap set = roster minus rescinded, both as of the epoch's anchoring position)
  plus removed-when-either-records-it — availability cost, never a key. The chat lane's
  `[anchored root … bound]` interval check is stated identically in `membership.md`,
  `authored-dag.md`, `exchange.md`, and the residuals table.
- The credentials accept gate is a complete fail-secure conjunction, and every non-obvious edge is
  explicitly priced: the buriable issuance anchor (with a pointer to the residual), the
  revoke-before-terminate discipline, the bearer redemption race, and the
  reusable-transferable-bearer impossibility argument.
- The shared-documents honored predicate (`F_x ≤ V_x ≤ B_x` on the editor's own chain) is
  enforceable as stated, and the doc closes its own two bypass candidates: the cited grant must
  resolve to a `Gnt` sealed on the creator's chain (the seal-locate rule, "stated here, not left to
  inference"), and the period-disjointness pass is enforceable because every grant is a public
  structural event on a witnessed chain, with a withheld grant-doc reading conservative.
- The exchange sender-key-currency model (two witnessed axes: the identity's establishment interval
  and the device's key window; the witnessed time as the threshold-crossing receipt) is consistent
  with the witnessing doc's definition, including its monotone-downward robustness argument, and
  chat's epoch-window variant composes the same pieces with the open-epoch residual honestly carried
  in both `exchange.md` and the residuals table.

### Group I — Root-level companion documents and the terminology sweeps

**Read:** `MODEL.md`, `USES.md`, plus `grep-terms.pl` sweeps across the whole surface.

The sweeps came back clean:

- Every protocol constant is stated with the same value at every site that states one:
  `MINIMUM_PAGE_SIZE = 129`, `MAXIMUM_UNSEALED_RUN = 64` (derived, `(129−1)/2`),
  `MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_MANIFEST_LIST = 128`, `MAXIMUM_SEL_LINEAGE = 64`,
  `MAXIMUM_DELEGATION_DEPTH = 8`, `MAXIMUM_GRANT_ADDS = 64`,
  `MAXIMUM_WITNESS_KEY_WINDOW = 365 days`, `CLOCK_TOLERANCE_BAND = 1 minute`.
- The issuance-commitment formula appears in three parameterizations of one shape (`{owner}:{said}`,
  `{issuer}:{cred.said}`, `{sender}:{message.said}`) — consistent.
- "Recovery key" and "repair event" appear only in negated form; no third tier survives anywhere;
  the witnessing-floor formula is identical at every site.

`USES.md` is a catalogue and is consistent with the feature layer. `MODEL.md` is accurate on the
conflict rules, the fingerprint, recovery, thresholds, and the no-silent-forgery guarantee — with
one finding:

**F4 [minor] — `MODEL.md`'s artifact section attributes fork-prevention to the anchor, which the
design explicitly says the anchor cannot provide.** "An issued artifact rides its owner's identity"
argues that an artifact "can't go wrong on its own" because every artifact event needs a fresh
identity anchor, so an attack "always shows up as activity on the identity — never as a lone
artifact fork the identity doesn't already reflect." The design surface says the opposite about the
mechanism: an identity anchor is an opaque digest the identity cannot deduplicate, so an owner (or a
signing-key thief) _can_ fork an artifact log under a linear identity — one fresh anchoring event
can name two competing artifact events — and that is exactly why an artifact log is its own
witnessed chain with its own first-seen gate and its own neutral re-seal (`sel/log.md` §The SEL is
its own witnessed chain, §Why the neutral advancer is needed). The healing claim ("recovering the
artifact is recovering the identity") holds for the compromise-burial case via severance, but the
prevention claim rests on the wrong mechanism. Since `MODEL.md` is the narrative layer, one added
sentence ("and the artifact's own log is witnessed at its own positions — the anchor alone cannot
prevent a same-position artifact fork") would make it faithful without adding detail.
