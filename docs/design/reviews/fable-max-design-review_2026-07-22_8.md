# Fable (max) design review — 2026-07-22, round 8

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_8.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks. don't bother checking that every constant is defined and that every
> formula matches - they do. we've been through at least 11 prior rounds of review in this PR.
> instead focus on inconsistencies or any unsoundness that affects the read.

## Scope and method

This is a cold review: every design document was read fresh, in the order
[`docs/design/README.md`](../README.md) prescribes, with no reliance on prior rounds' reviews
(deliberately not read, per the prompt). Read in full: `README.md`, `MODEL.md`, and `USES.md` at the
repository root; the orientation pair (`system-thesis.md`, `glossary.md`); the data substrate
(`sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`, `kinds.md`, `shapes.md`,
`tags-and-topics.md`); the cross-cutting doctrine (`protocol-doctrine.md`, `residuals.md`,
`monitoring.md`); the full event-log layer (`event-shape.md` and all sixteen KEL / IEL / SEL docs,
`iel/delegation.md` included); the federation layer (`bootstrap.md`, `witnessing.md`, `topics.md`,
`mesh-transport.md`); the policy layer (`policy.md`, `documents.md`, `evaluation.md`); the six
protocol primitives (`essr.md`, `ipex.md`, `receive-key-directory.md`, `group-key.md`,
`membership.md`, `authored-dag.md`); and the three features (`credentials.md`, `exchange.md`,
`shared-documents.md`).

The focus, per the prompt, was correctness / soundness and cross-document consistency that affects
the read — not re-verifying that every constant is defined or every formula matches.
`scripts/grep-terms.pl` was used for phrase sweeps across decoration and line wrapping (the
rescission identifier family, the inception-anchoring phrasing, the reincept spelling, and several
spot checks recorded under "What was checked and held").

## Verdict

The design surface is in strong shape. I traced the load-bearing arguments end to end — the
four-state divergence machine and its accepted-branch counting, the seal and burial machinery, the
witnessing floor and the witnessed-versus-accepted discipline, the kind-strict anchoring matrices,
the negative-check pipeline, severance, and the composition of the protocol and feature layers over
the primitives — and found them coherent, mutually consistent, and consistently worded across every
document that restates them. **No unsoundness was found.** What remains after eleven-plus rounds is
four low-severity consistency findings, all textual: one canonical-catalogue row that implies an
address class no document realizes, two summary sentences that state a core rule too narrowly, one
sentence whose pronoun points at the wrong derived value, and one defined term spelled two ways.
None of them changes what a precise implementor would build, because in each case the precise
statement exists elsewhere and is unambiguous — but each one can send a reader down a wrong path
first, which is exactly the "affects the read" bar this round was asked to apply.

## Summary of findings

| #   | Severity | Where                                                                    | Finding (one line)                                                                                            |
| --- | -------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| F1  | Low      | `tags-and-topics.md` (tags table + its follow-on note)                   | The `rescission` tag row claims it also derives "its lookup-SEL," but no documented rescission lookup uses it |
| F2  | Low      | `protocol-doctrine.md` §Inception tiers; `event-shape.md` SEL footnote ᵃ | "The v1 is what an IEL `Ixn` anchors" — stated as the general rule, but true only for a content SEL           |
| F3  | Low      | `features/credentials.md` §Revocation                                    | "Lookup log at that derived address" points the reader at the kill target, which is expressly not its address |
| F4  | Low      | SEL-family docs vs the rest of the surface                               | One defined term, two spellings: "reincept" (glossary, KEL/IEL) versus "re-incept" (SEL docs and neighbors)   |

Observations O1–O3 (below the findings) are compressions or summaries I judged deliberate and
self-correcting in place; they are recorded so the next round doesn't re-derive them, and need no
action unless the editor wants them.

## Findings

### F1 — The `rescission` tag row promises a lookup address that nothing uses (Low)

**What the catalogue says.** The tags table in
[`tags-and-topics.md`](../primitives/data/event-logs/tags-and-topics.md) describes
`vdti/sel/v1/actions/rescission` as "a `Dth`-anchored kill's target **+ its lookup-SEL**" —
mirroring the `revocation` row above it. The note beneath the table repeats the claim by contrast:
`delegation` and `attestation` serve "**only** as a SEL inception **topic** …, never as a flat
kills-target the way `revocation` / `rescission` **also** do" — implying both `revocation` and
`rescission` serve in both roles (kills-target _and_ lookup-SEL topic).

**What the rest of the surface says.** For `revocation` the double duty is real: a credential's kill
target is `hash('vdti/sel/v1/actions/revocation:{issuer}:{cred.said}')` and its `{Icp, Trm}` lookup
log derives from the same owner / topic / data inputs (the two values differ because a lookup
address is the whole-content two-hash derivation while the target is a flat hash — the "separate
two-pass derivation" of [`iel/events.md`](../primitives/data/event-logs/iel/events.md)). For
`rescission`, however, every documented rescission resolves its lookup elsewhere:

- A **delegate** rescission has **no separate rescission lookup at all** — its `Trm` rides the
  delegating-link SEL itself, whose topic is `vdti/sel/v1/actions/delegation`
  ([`iel/delegation.md`](../primitives/data/event-logs/iel/delegation.md): "there is **no separate
  rescission lookup**").
- A **document-member** removal lookup rides the feature topic `vdti/doc/v1/topics/rescission`
  ([`shared-documents.md`](../features/shared-documents.md) §Shapes: "the shared removal locus
  `…/rescission`").
- A **chat-member** removal lookup rides `vdti/exchange/v1/topics/rescission`
  ([`exchange.md`](../features/exchange.md) §Reserved names: "The removal lookup's SEL topic is
  `vdti/exchange/v1/topics/rescission`"). The topics table in `tags-and-topics.md` itself lists both
  feature `rescission` topics, agreeing with the features.

So the `actions/rescission` string is used **only** as the `kills[]` target tag (which
`shared-documents.md` states explicitly: "the primitive's derivation **tag** (never a feature
topic)"); no documented lookup SEL carries it as a `topic`.

**Why it matters for the read.** The catalogue is the canonical identifier surface. A reader
implementing the generic kill check from it would derive a rescission-lookup address that nothing
ever writes to. The default posture self-corrects — the O(1) read misses and falls through to the
fail-secure walk, which matches the target correctly — so there is no soundness break; but a
consumer that has opted down to the fail-open lookup would be **systematically** blind at the wrong
address, a worse condition than the per-object miss-risk fail-open is documented to accept.

**Suggested fix.** Trim the `rescission` row to the target role only (for example: "a `Dth`-anchored
kill's target — the rescission lookups themselves ride the delegating link or a feature removal
topic"), and adjust the follow-on note so only `revocation` is credited with the topic-plus-target
double duty.

### F2 — "The v1 is what an IEL `Ixn` anchors" is the content-only case stated as the rule (Low)

**Where.** Two summary sites state the SEL inception-anchoring rule with an `Ixn`-only phrasing:
[`protocol-doctrine.md`](../protocol-doctrine.md) §Inception tiers ("the SEL's serial-1 event (its
v1) is what an IEL `Ixn` anchors, and the `Icp` rides `v1.previous`") and the SEL `Icp` footnote ᵃ
in [`event-shape.md`](../primitives/data/event-logs/event-shape.md) (same sentence shape).

**Why it is wrong as stated.** The general rule — stated precisely in the same documents' anchor
matrices, and in [`sel/log.md`](../primitives/data/event-logs/sel/log.md) §Inception and
[`sel/events.md`](../primitives/data/event-logs/sel/events.md) §Inception and the serial-1 floor —
is that the owner IEL anchors the v1 **with the matching kind for what the v1 is**: an `Ixn` for a
content SEL's first `Ixn` or floor `Pin`, an `Ath` for a value lookup's `Gnt`, a `Rev` or `Dth` for
a kill lookup's `Trm`. The `Ixn`-only sentence contradicts the kind-strict matrix it sits next to
for two of the four inception shapes. Kind-strict anchoring is core doctrine ("no higher-tier
stand-in"), so a first-pass reader who internalizes the summary sentence carries a wrong model until
the matrix corrects them — and in a doc explicitly offered as the concept map to read before the
taxonomy, that is the reading that sticks.

**Corroboration.** The phrase sweep incidentally showed the same sentence was flagged in an earlier
round's review file (which I otherwise did not read, per the prompt). Independent passes re-flagging
one sentence is a signal the sentence, not the reviewers, is the friction.

**Suggested fix.** In both places: "the SEL's serial-1 event (its v1) is what the owner IEL anchors
— with the matching kind (`Ixn` for content; `Ath` / `Rev` / `Dth` for a lookup's `Gnt` / `Trm`) —
and the `Icp` rides `v1.previous`."

### F3 — "Lookup log at that derived address" names the wrong derived value (Low)

**Where.** [`credentials.md`](../features/credentials.md) §Revocation: "the issuer declares a kill
on its own chain naming the credential's derived revocation target —
`hash('vdti/sel/v1/actions/revocation:{issuer}:{cred.said}')` — alongside a small sealed
`{Icp, Trm}` lookup log **at that derived address** (so the declaration does not leak the object's
address)."

**Why it is wrong as stated.** "That derived address" grammatically points at the just-displayed
kill target — but the target is expressly **not** the lookup's address:
[`sel/events.md`](../primitives/data/event-logs/sel/events.md) ("The owner IEL's `kills[]` target is
a **separate** flat, domain-qualified hash — distinct from the lookup SEL's prefix and SAID") and
[`iel/events.md`](../primitives/data/event-logs/iel/events.md) ("The `target` is **not** the lookup
SEL's prefix (a separate two-pass derivation), so `kills[]` does not leak the killed object's
address"). The sentence's own parenthetical only makes sense when the two values differ, so the text
contradicts itself within one line: the reader is told the lookup lives at the target's address and,
in the same breath, that the target does not reveal that address.

**Suggested fix.** "…alongside a small sealed `{Icp, Trm}` lookup log at the credential's separately
derived lookup address (the same owner / topic / credential inputs, derived as a chain prefix rather
than a flat hash — so the public declaration does not leak the lookup's address)."

### F4 — One defined term, two spellings: "reincept" versus "re-incept" (Low)

**Where.** The glossary defines **reincept** ("the operational exit from a Disputed chain"), and the
thesis, doctrine, KEL and IEL docs, `monitoring.md`, `residuals.md`, and `credentials.md` use that
spelling. The SEL family — `sel/log.md`, `sel/merge.md`, `sel/reconciliation.md` (including a
section titled "Re-incepting a lookup SEL"), `sel/verification.md` — plus `group-key.md`, the
`event-shape.md` lineage footnote, and parts of `shared-documents.md` spell the same operation
**re-incept**. Three files carry both spellings (`glossary.md`, `event-shape.md`,
`shared-documents.md`).

**Why it matters for the read.** The split tracks the SEL documents closely enough that a careful
reader can take it for a deliberate distinction — "re-incept" looking like a separate, SEL-specific
operation (re-establishing a lookup at a fresh lineage) rather than the one glossary term. The
glossary's own lineage entry uses the hyphenated form while its chain-states entry defines the
unhyphenated one, which reinforces the impression. It is one operation — standing up a fresh prefix
— whether the prefix freshness comes from new randomness or from a lineage counter, and the surface
elsewhere goes to unusual lengths to keep one concept under one name (the "retain," "bound," and
"governance" disambiguation notes). One spelling should win; given the glossary entry, "reincept."

## Observations — recorded, no action needed

These are places where I initially suspected an inconsistency and concluded the text is a deliberate
compression that corrects itself in place. Recorded so a later round doesn't re-derive them.

- **O1 — Transfer-matrix cells for a Terminated sink.** In `kel/reconciliation.md` and
  `iel/reconciliation.md`, Matrix 2's cells for transfers into a Terminated sink read "Sealed /
  Buried," while the adjacent column note adds the third arm ("A sealed competitor → `Disputed`").
  The cells carry the honest outcomes; the collusion arm lives in the note directly beneath, and the
  two docs mirror each other exactly. Complete within the section — just split between cell and
  note.
- **O2 — Prefix-commitment enumerations read as exhaustive.** `kel/log.md` ("What the KEL prefix
  commits to is the inception's `publicKey`, `rotationHash`, kind discriminator, and … its
  `federation` / `federationPin` binding") and the parallel sentence in `iel/log.md` enumerate
  highlights after stating the governing rule (the prefix is the whole-content digest — so the
  `Icp`'s `manifest`, and with it the witness config, is committed too). The rule is stated first
  and `said.md` uses "including," so the enumerations are illustrative; a reader asking "can two
  inceptions differing only in witness config share a prefix?" still gets the right answer (no) from
  the whole-content rule.
- **O3 — The thesis prevention-tree's "same kind?" label.** The decision node reads "same kind? (two
  content, or two sealed)" where the property is same **tier** (a SEL `Ixn` and a `Pin` are
  different kinds, one tier). The parenthetical disambiguates in place, and the surrounding prose
  says "same-tier" consistently.

## What was checked and held

The substance of a cold pass is what it verified, not only what it flagged. The following
load-bearing threads were traced across every document that states them and found consistent — in
substance and, almost everywhere, in wording:

- **The divergence machine.** The four per-node states, the Forked-versus-Disputed discriminator
  (the count of accepted sealed branches, per branch, wherever each branch's seal sits), the freeze
  of origination versus the pure-walk reading, burial by position plus descent-of-deadness, the
  one-burying-seal recovery with its two attach shapes, tier-rank for a terminate racing content,
  and the eviction-is-atomic rule — identical across the thesis, the doctrine, the glossary, all
  three primitives' log / merge / reconciliation docs, and both token specifications. The KEL and
  IEL reconciliation matrices mirror each other exactly where they should and differ exactly where
  the mixed chain differs.
- **Witnessed versus accepted.** Every verdict-bearing sentence I checked counts **accepted**
  (threshold-witnessed) branches, never merely witnessed ones; the deferred-pending state, the
  query-scoping rule (a non-witness holds only witnessed-in-full events), the
  acceptance-commits-ancestry nuance, and the below-seal-straggler drop (the backdate defense) are
  stated compatibly at every site, including both places that could most easily drift (the merge
  outcome tables and the completeness matrices).
- **The seal machinery.** The derived seal, the clean-seal retreat to the divergence ancestor on a
  dispute, pre-seal verifiability, the seal-advance cap and its page arithmetic, and the spine as a
  convenience view agree across the doctrine, the three primitives, and the witnessing doc (the
  witness mirrors the seal-cap before signing).
- **Kind-strict anchoring.** The anchor matrices at `event-shape.md`, `kel/events.md`,
  `iel/events.md`, and `sel/events.md` state the same pairs at every site (content ← `Ixn`; `Gnt` ←
  `Ath`; `Trm` ← `Rev`/`Dth`; `Sea` ← `Evl`; the `Wit` ↔ `Wit` pair; tier-2 acts ← KEL `Rot`), and
  the "tier-elevation is a floor, not the check" warning appears wherever it is needed. F2 is the
  one summary sentence out of step.
- **The tier model.** Two tiers, single-stream pre-rotation, "the reserve defends the signing key,
  never the rotation key" — verbatim-consistent everywhere. The apparent tension between "two backed
  rotations prove a reserve compromise" (doctrine) and "the brick's second seal needs the current
  signing key" (`compromise.md`, `MODEL.md`, the residuals table) reconciles cleanly through the
  spent-reserve boundary case in `kel/events.md`: the revealed reserve _is_ the current signing key,
  and the two namings are the before/after of the same key material. `MODEL.md`'s plain-language
  forensics match the design exactly.
- **The federation numbers.** The witnessing floor, fork-cost and its partition slide, the
  federation's hard recoverability cap (`threshold ≤ min(|roster| − 2, signers − 1)`), exclude-self
  peer-witnessing, the four-witness minimum with its worked `{threshold 2, signers 3, t_govern 3}`
  example, the one-add-per-`Wit` rule, and the clock / key-window / wipe discipline agree across the
  doctrine, `iel/events.md`, `witnessing.md`, `bootstrap.md`, and `shapes.md` (whose general
  `signers ≤ |roster|` bound correctly defers to the federation's tighter cap).
- **The negative-check pipeline.** The O(1) read, the fail-secure walk over the fresh chain, the
  fail-open opt-down (never up), the target mirroring the killed address (plain, lineaged, or
  `:content`), the lineage walk consuming the per-lineage check, and the stated feature-layer
  obligation to declare the matching lineaged target — consistent across the doctrine,
  `iel/verification.md`, the SEL docs, the policy layer, `credentials.md`, `membership.md`,
  `receive-key-directory.md`, and the residuals catalog. F1 and F3 are wording issues at this
  pipeline's edges, not holes in it.
- **Severance.** Deadness-precedence, severance as truncation (never a fifth state), and the proof
  that a Disputed SEL cannot be downgraded by severance (its accepted sealed branches rest on
  accepted, never-buried anchors) hold identically in `sel/log.md`, `sel/merge.md`,
  `sel/verification.md`, and the crossing matrix in `sel/reconciliation.md`.
- **The effective SAID.** The verdict-recoupled, set-independent synthetic; its keying on the
  divergence ancestor (verdict-coupled, both spellings of the definition agree); the
  three-views-of-one-walk tables in all three verification docs; and `monitoring.md`'s and
  `MODEL.md`'s narrative versions all match.
- **Derivations and addressing.** The two-hash correlation-resistance argument, the pin-free
  recomputable SEL inception, the `content: true` ⟺ tier-1-v1 biconditional, whole-content prefix
  commitment, the strictly-ascending set rule, and the exhaustive-schema gate are stated compatibly
  at every site (`said.md`, `sad.md`, `kinds.md`, `shapes.md`, the SEL docs, the glossary).
- **The protocol and feature layers.** ESSR's two bindings and four guarantees; IPEX's gate clauses
  and the freshness envelope; the directory's reserve-gated publish and the lineaged-target
  obligation it carries; group-key's wrap-set derivation rule tying the roster to the membership
  instance; membership's store-performable fail-secure walk (the requester discloses its own entry);
  the authored DAG's anchored-root and interval check (`[root … bound]`); and each feature's
  residuals — all agree with the primitives they compose and with the corresponding rows in
  `residuals.md`. The `MAXIMUM_GRANT_ADDS` bound and the grant-doc shape agree between
  `membership.md`, `shared-documents.md`, and `shapes.md`.
- **The top level.** `README.md`, `MODEL.md`, and `USES.md` make no claim the design surface does
  not back: the no-unwitnessed-mode rule, the 32-device roster cap, the three-device floor and the
  two-device freeze, the fingerprint/marker story, the no-silent-forgery guarantee with its honest
  delivery-versus-existence and reserve-theft caveats, and the revocation comparison all trace
  cleanly.

Coverage boundaries, honestly stated: constants and formula arithmetic were not re-verified (per the
prompt); prior rounds' review files were not read (per the prompt — two incidental sweep hits
showing earlier rounds touched the same F2 sentence are noted above as corroboration only); and the
items the surface marks forthcoming (the storage service, the encoding library, the exact
grant-value layouts) were checked only for being consistently declared, which they are.
