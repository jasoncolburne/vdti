# Fable (max) design review — 2026-07-22, round 9

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_9.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks. don't bother checking that every constant is defined and that every
> formula matches - they do. we've been through at least 11 prior rounds of review in this PR.
> instead focus on inconsistencies or any unsoundness that affects the read.

## How this review was done

This is a cold read: no prior review file was consulted, and every claim below comes from the
current files on this branch. I read the documents in the order the design README prescribes —
orientation, then the data substrate, then the cross-cutting doctrine, then the three event-log
primitives (the device key log, the identity log, the data log), then federation and witnessing,
then policy, the protocol primitives, and the features — with the top-level `README.md`, `MODEL.md`,
and `USES.md` first. Every design file was read in full. Phrase sweeps used `scripts/grep-terms.pl`
so decorated and line-wrapped forms were not missed.

The review looks for two kinds of problem, per the brief:

- **Soundness** — a stated rule or argument that does not hold, contradicts another rule, or leaves
  a hole an attacker or an honest implementer would fall into.
- **Consistency** — two places that describe the same thing differently, in a way that would mislead
  a reader or an implementer.

Per the brief, I did not re-verify every constant and formula — eleven prior rounds have done that
(although the ones I passed while reading all checked out). Findings are graded **High** (the design
or its guarantees read wrong), **Medium** (a reader or implementer would likely go astray), **Low**
(friction or a small mismatch), or **Note** (an observation, no change required).

## Verdict

**Four Low findings; no High or Medium.** After a complete cold read of the design surface — all
forty-eight design files plus the three top-level documents — the design reads as one system: the
same rules are stated the same way at every site I compared, the numeric bounds agree everywhere
they appear, and the soundness arguments I deliberately tried to break all held (the attack log is
in [What was attacked and held](#what-was-attacked-and-held) below). The four findings are small
precision gaps that cost a careful reader a re-read; none changes a guarantee, and each has a
one-or-two-sentence fix.

## Findings at a glance

| #   | Severity | Kind        | Where                                                                           | Finding                                                                                                    |
| --- | -------- | ----------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1   | Low      | consistency | `protocol-doctrine.md`, `system-thesis.md`, the three `log.md`s, the proof docs | The Forked definitions omit the "accepted" qualifier that every Disputed definition carries                |
| 2   | Low      | readability | `protocol-doctrine.md` §the split stall; `federation/witnessing.md` §First-seen | The split-stall exit compresses its two attach shapes into "a seal at the position"                        |
| 3   | Low      | consistency | `event-shape.md`; `iel/events.md`                                               | The identity log's content event never states its minimum anchor count; the key log's is stated three ways |
| 4   | Low      | consistency | `kinds.md` §Fetch by SAID; `features/exchange.md`                               | The fetch-by-identifier model has no slot for the chat serve-time membership gate                          |

Three further observations that need no change are listed under
[Minor observations](#minor-observations--no-change-required).

## Findings

### 1. The Forked definitions omit the "accepted" qualifier that Disputed's carry — Low, consistency

**Where.** `docs/design/protocol-doctrine.md` §Terminology ("**Forked** — a live, recoverable fork:
two **distinct content** events at one serial, with no accepted sealed branch past it");
`docs/design/system-thesis.md` §Divergence is resolved by tier ("two competing **content** events at
one serial"); the state tables and diagrams in `kel/log.md` ("two competing content events at one
serial (0 sealed)"), `iel/log.md`, and `sel/log.md`; the terminal-state rules in the three
`verification.md`s; and invariant 4 in `kel/reconciliation.md` and `iel/reconciliation.md` ("a
content-only fork … is Forked").

**What.** Every definition of Disputed is careful to say the two sealed branches must be
**accepted** (witnessed at threshold). The parallel definitions of Forked say only "two distinct
content events" or "a content-only fork" — the acceptance qualifier is never attached to the content
side. The precise counting rule does exist, but in one place: `protocol-doctrine.md` §Federation
convergence states "the Active / Forked / Disputed reading is over **accepted** events only" and
"**Forked** takes **two accepted content siblings** — a witness compromise," and the
deferred-pending machinery ("never counted toward a verdict") implies the same thing.

**Why it matters.** Read literally, the definitional sites say a chain holding one accepted content
event and one witness-declined sibling at a serial is Forked. It is not: a declined sibling is
deferred-pending and never counted, a non-witness never even holds one (query-scoping), and a
selected witness holding one is explicitly told its walk still reads Active (the minority-dissent
passage). The design is airtight — every seat that can hold an unaccepted sibling has an explicit
rule — but the reader has to assemble that from the convergence section and the deferred-pending
entries, while the definitions themselves, including the two load-bearing correctness-proof
documents, carry the looser wording. During this read the asymmetry (Disputed says accepted, Forked
does not) cost a stop-and-verify; a first-time implementer building the state predicate from the
state tables could build the wrong one.

**Suggested direction.** Add the one word at the definitional sites — "two **accepted** content
events at one serial" (or "two distinct accepted content events") — mirroring the Disputed
definitions, in `protocol-doctrine.md` §Terminology, `system-thesis.md`, the three `log.md` state
tables, and the reconciliation invariants.

### 2. The split-stall exit compresses two attach shapes into "a seal at the position" — Low, readability

**Where.** `docs/design/protocol-doctrine.md` §The propagation premise and the split stall; the same
wording in `docs/design/substrate/federation/witnessing.md` §First-seen (the split-stall paragraph).
These are the only two sites (confirmed by sweep).

**What.** Both paragraphs describe the exit from a stalled content position as: "The exit is a
burying seal-advancer: a rotation or evolve **at the position** is sealed — the first sealed sibling
**there**, signed by every selected witness (including those that signed a content sibling — the
cross-tier co-sign) — and reaches majority. **If it attaches at the author's own stalled sibling**
it retains that content …; if it attaches at the shared ancestor it buries both." A seal that
attaches at (extends) a stalled sibling does not sit **at** the contested position — it sits at the
next serial, is not a sibling of anything, and needs no cross-tier co-sign, because its position is
fresh. Only the ancestor-attaching shape is a sealed sibling at the contested position where the
cross-tier co-sign matters. The precise mechanics exist elsewhere and are correct — the two recovery
attach shapes in `kel/merge.md`, and "acceptance gates the tip; an accepted event commits its
ancestry" in `kel/verification.md` (which is what makes the retained stalled sibling canonical) —
but this paragraph presents both shapes as landing "at the position."

**Why it matters.** On a first read the paragraph briefly contradicts itself — an event cannot both
be a sibling at a serial and extend a sibling at that same serial — and the reader must reach for
the merge doc's attach shapes to resolve it. It is compression, not error.

**Suggested direction.** Split the sentence by attach shape at both sites: the ancestor-attaching
seal is the sealed sibling at the contested position (where the cross-tier co-sign applies and both
stalled siblings bury); the own-sibling-extending seal lands at the next serial and carries its
stalled ancestor to acceptance via the acceptance-commits-ancestry rule.

### 3. The identity log's content event never states its minimum anchor count — Low, consistency

**Where.** `docs/design/primitives/data/event-logs/event-shape.md` — the role table says "`anchors`
| KEL `Ixn` (**≥ 1**) / `Rot` / `Wit`; IEL `Ixn` / `Evl` / `Ath` / `Rev` / `Dth`", the KEL per-kind
grid says "req (`anchors`, ≥1)", and the KEL taxonomy row repeats "(`anchors`, ≥ 1)";
`kel/events.md` states it a third time ("`Ixn` carries the `anchors` role required (≥ 1) — anchoring
is its purpose"). For the identity log, the per-kind grid says only "req (`anchors`)" and
`iel/events.md` §`Ixn` is silent on a minimum.

**What.** The device key log's content event must anchor at least one thing — stated three times.
The identity log's content event has a required manifest carrying the anchors role, but no stated
minimum. Whether an identity-log content event may carry an **empty** anchors list is therefore open
where the key log is explicit.

**Why it matters.** The two logs are presented as mirrors ("the KEL's machine reused"), so a reader
carries the ≥ 1 expectation over — but an implementer writing the identity log's per-kind validation
finds nothing to cite. The question is not idle: an empty-anchors content event would be the natural
vehicle for a bare same-federation re-pin (the `federationPin` field is optional on every body
event), and whether that vehicle exists changes what a pin-refresh costs an identity with nothing to
anchor (nothing extra if allowed; wait for the next real event, or a roster-less evolve, if not).

**Suggested direction.** State the minimum once at the identity log's content event — presumably "≥
1", mirroring the key log — and, if it is ≥ 1, one clause on how a contentless same-federation
re-pin is authored on an identity log (it rides the next real event of any kind, or a roster-less
evolve).

### 4. The fetch-by-identifier model has no slot for the chat serve-time membership gate — Low, consistency

**Where.** `docs/design/primitives/data/sad/kinds.md` §Fetch by SAID — "the store hands back a SAD
by SAID only when learning that SAID already meant holding the chain, or when the SAD is public by
design and its custody `readers` gate admits the requester"; the same section names exactly two
protections for served content (a custody read gate, or member-delivery that keeps the object out of
the store entirely). Versus `docs/design/features/exchange.md` §The payload and §Store
authorization: a chat message carries **no** custody field (its shape in `shapes.md` has none), yet
the store gates both its upload and its fetch by a per-requester `chat-membership` check that rides
the signed request, not the SAD.

**What.** The catalogue's summary of the store model recognizes two ways a served record is
protected: its own custody read gate, or never being in the store at all. The chat content path uses
a third: the record is in the store (scoped to the group's nodes by its availability), carries no
custody gate, and is served only through a feature-defined serve-time membership check. The exchange
feature is explicit and self-consistent about this; the catalogue's one-line rule and its "kind is
only the first gate" paragraph simply have no slot for it.

**Why it matters.** A reader of the catalogue alone would conclude a chat message record — no
custody, an application content kind — is served ungated to anyone naming its identifier. In
practice its identifier is unguessable (the mandatory nonce) and the group's nodes apply the
membership gate, so nothing is exposed; but the store model as summarized and the store behavior as
specified disagree about **which mechanism** does the guarding. The storage-service document that
would reconcile them is forthcoming, which makes the catalogue's summary the only current statement
of the store-side rule.

**Suggested direction.** Either add the third mode to the catalogue's fetch-by-SAID section (a
feature-defined serve-time gate at the storage boundary, with chat as the instance), or note in the
chat shape that its read gate is expressed at the request layer rather than in custody — one
sentence either way.

## Minor observations — no change required

- **"An owner-first namespace."** `sel/events.md` §`Gnt` describes the grant-value kind family as
  "an owner-first namespace, capped at 64 characters" — the epithet "owner-first" is not defined
  anywhere and cannot be decoded from context (the surrounding rule is that each grant value's
  meaning belongs to its owning feature or primitive). Dropping or expanding the two words would
  remove a stumble.
- **The synthetic's "position" is an identifier, not a serial.** Most sites say the fingerprint
  synthetic is "qualified by prefix + position"; the two owning sites (`tags-and-topics.md` and
  `protocol-doctrine.md` §Effective-SAID comparison) pin "position" as the **identifier of the
  divergence ancestor** — the event just below the fork — verdict-coupled. The shorthand is
  adequately defined, but a reader meeting "position" first may briefly take it for a serial number;
  `kel/log.md`'s "qualified by prefix and position (below)" also points "below" at a section that
  links out rather than defining it.
- **The catalogue naming holds everywhere.** Every component and category the naming-convention
  section enumerates is actually used somewhere on the surface (including the easy-to-orphan `log`,
  `directory`, and `groupkey` components), and no identifier anywhere deviates from the four-segment
  convention.

## What was attacked and held

Per the adversarial-first posture the design itself prescribes, I spent a substantial part of the
read trying to break the load-bearing arguments rather than confirm them. These attacks failed —
each rule held as stated, with the closing rule found where the docs say it is:

- **The membership walk is performable by the store.** A fail-secure member check that rested on a
  secret the requester does not disclose would silently force the fail-open path. The membership
  primitive closes this explicitly: the requester disclosing its own blinded entry (nonce included)
  is what makes the store's walk runnable, and the disclosure is bound to the identity the live
  signature resolves, so a leaked disclosure is not a bearer token.
- **The document-membership disjointness pass is performable.** Overlap detection must open every
  grant on the chain; the docs make that enforceable by noting every grant is a public structural
  event (so a verifier knows exactly how many to open) and a withheld grant document reads
  conservative — the check degrades toward refusal, never toward a wrongful accept.
- **A disputed data log cannot be rescued by severance.** The claim that severance never downgrades
  a dispute rests on: a data-log sealed event's anchor is an identity-log sealed event; acceptance
  of the data-log event gates on that anchor being accepted; and an accepted sealed anchor is never
  buried. All three legs are stated, and the reconciliation matrix marks the would-be counterexample
  rows unreachable for exactly this reason.
- **The no-buried-rotation guard composes with the ancestor-attaching recovery.** A recovery that
  would bury a branch carrying an accepted sealed event is rejected, held, and — once itself
  accepted — counted as the second sealed branch (dispute), while a declined or below-seal straggler
  is dropped. The retain-and-count versus drop split is justified by which rejections are
  branch-dependent versus uniformly computable, and the same rule appears identically at every site.
- **The fingerprint synthetic is flood-stable but change-sensitive, and both are needed.** An
  attacker who can mint more accepted branches cannot move the value (it is not a digest over the
  branch set); an attacker who creates an earlier divergence does move it — which is correct,
  because the value must move whenever held state changes to drive the fetch.
- **The backdate defenses close both directions.** A below-seal sealed straggler is declined by
  witnesses (who mirror the seal-cap) and dropped by the walk, so a harvested old reserve cannot
  fabricate a historical fork; the witnessed-time crossing cannot be pushed later by adding receipts
  (the threshold-smallest is monotone downward), so a stale key cannot be made to read current.
- **The earliest-anchor argument for a credential's locator is a genuine hash argument.** An anchor
  earlier than the located one would need the credential's identifier to exist before the event it
  embeds — a hash cycle — so a later re-anchor can never move the as-of, closing the tier-inversion
  un-revoke.
- **The delegation walk is bounded and never enumerates.** Walking up the committed path, each hop a
  positive lookup against the delegator's own inclusion list, bounded by the per-policy hop count
  and the fixed depth backstop, with the marker re-verified against the same delegate — a stray
  marker grants nothing; a self-grant collapsing a delegate leaf into an identity leaf is rejected.
- **The negation-only vocabulary is clean.** Sweeps for "recovery key," "repair event," and "repair
  kind" find them only inside negations ("there is no …") across the entire surface, including the
  plain-English model document; the direction of "the reserve defends the signing key, never the
  rotation key" is uniform at all seventeen sites, with the single "does not defend the rotation
  key" being the explicit negation.

## Coverage and consistency sweeps

Everything below was read in full, in the prescribed order: `README.md`, `MODEL.md`, `USES.md`;
`system-thesis.md` and `glossary.md`; the data substrate (`sad.md`, `said.md`, `custody.md`,
`availability.md`, `compaction.md`, `kinds.md`, `shapes.md`, `tags-and-topics.md`, the federation
`topics.md`); `protocol-doctrine.md`, `residuals.md`, `monitoring.md`; `event-shape.md`; the full
KEL, IEL, and SEL groups (each `log.md`, `events.md`, `verification.md`, `merge.md`,
`reconciliation.md`, plus `iel/delegation.md`); federation (`bootstrap.md`, `witnessing.md`,
`mesh-transport.md`); policy (`policy.md`, `documents.md`, `evaluation.md`); the protocol primitives
(`essr.md`, `ipex.md`, `receive-key-directory.md`, `group-key.md`, `membership.md`,
`authored-dag.md`); and the features (`credentials.md`, `exchange.md`, `shared-documents.md`).

Clusters checked and found consistent across files:

- **The derivation story.** The two-hash prefix/identifier derivation, the fixed-value placeholder,
  the whole-content rule, and the correlation-resistance argument are told identically in `sad.md`,
  `said.md`, `event-shape.md`, and each log's prefix-derivation section.
- **The taxonomy and the anchor matrix.** Event kinds, tier assignments, the seal-advancer sets, and
  the kind-strict anchor matrix (both back-check directions) agree across `glossary.md`,
  `protocol-doctrine.md`, `event-shape.md`, and the per-primitive docs — including the edge rows
  (the terminate kind advances the seal but opens no window; inception roots the spine and advances
  none; the data log's pin-only re-pin is content at any serial).
- **The state machine and its projections.** The four chain states, the zero/one/two-or-more
  accepted-sealed-branch verdict counted per branch wherever the seals sit, the below-seal straggler
  drop, the verdict-tagged synthetic, and the three-views tables (state, trust region, fingerprint)
  are the same in the doctrine, the glossary, and all three primitive groups — with finding 1 the
  one wording gap.
- **The threshold bounds and the federation's harder ones.** The floor of two on authority counts,
  the strict-majority authorization floor, the eviction ceiling and where it is advisory versus
  hard, the roster cap, the never-emptied rule, the witness-config bounds including the
  recoverability cap and the exclude-self pool, and the worked minimum-federation example all agree
  across `protocol-doctrine.md`, `event-shape.md`, `iel/events.md`, `shapes.md`,
  `federation/bootstrap.md`, and `federation/witnessing.md`.
- **The kill model.** The declaration shape, the two tag names, the lineaged / non-lineaged /
  content-closure target forms, the mirrored killed-address rule, the public-versus-gated cutoff
  placement, and the "lineaged target is a feature-layer obligation the primitive does not backstop"
  caveat agree across the glossary, the doctrine, `tags-and-topics.md`, the identity- and data-log
  docs, `delegation.md`, the membership primitive, and both features — and the residuals catalog
  lists the caveat.
- **The witnessing mechanics.** The selection formula and its byte convention, the receipt shape
  (field-for-field between `shapes.md` and `witnessing.md`), the currency gate, the clock and its
  two constants, the wipe rule, the witnessed-time definition, query-scoping and the audit flag, and
  the beacon are stated once in the federation doc and referenced (never re-derived differently)
  everywhere else.
- **The merge layer.** The five transitions and five rejections, the routing order and its
  diagnostics rationale, the deferred-pending rule, and the retention bounds are identical across
  the three merge docs and their reconciliation proofs, with the data log's two additions
  (severance-first routing, the neutral re-seal) consistently motivated in its own group.
- **The features against their primitives.** The envelope and disclosure shapes match the field
  catalogue exactly; the chat lane, the join marker, the removal bracket, and the two-structure
  wrap-set derivation rule agree between the exchange feature, the membership and authored-graph
  primitives, and the residuals catalog's three chat rows; the shared-document topics, grant values,
  and shapes match the catalogues.
- **The plain-English layer.** `MODEL.md`, `USES.md`, and `README.md` make no claim the design
  surface contradicts — the roster cap, the three-device floor and the two-device freeze, the
  first-seen-for-key-changes rule, the stable conflict marker that never lists competing versions,
  and the narrowed "no silent forgery" guarantee (owner vigilance for a stolen reserve) all match
  the doctrine.

## Closing note

Eleven rounds in, the review question shifts from "is anything wrong" to "does anything still snag
the read," and the honest answer is: very little. The four findings above are the residue of a
full-surface read that was actively hunting; each is a wording-level fix. The documents repeat their
load-bearing rules at every site that needs them, and — unusual for a surface this large — the
repetitions agree.
