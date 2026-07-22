# Fable (max) Design Review — 2026-07-22, round 7

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_7.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks. don't bother checking that every constant is defined and that every
> formula matches - they do. we've been through at least 11 prior rounds of review in this PR.
> instead focus on inconsistencies or any unsoundness that affects the read.

**Reviewer:** Claude (Fable, max effort) — cold review: a fresh read with no context carried in from
earlier rounds. **Scope:** the full design surface in the prescribed reading order — the top-level
README, USES, and MODEL, then all forty-one documents of `docs/design/` layers 0 through 7.
**Focus:** soundness (does the argument hold together) and consistency (do the documents agree with
each other), per the brief; constant-definition and formula checking were skipped as instructed,
except where arithmetic fell out of an argument I was already checking.

**Status: COMPLETE.** Every document in the reading order was read in full, in order. Findings were
accumulated iteratively during the read and consolidated below.

## Verdict in brief

The design surface is in strong shape. Across roughly 18,000 lines, the layered story —
self-addressed data, the two capability tiers, the seal and its bound, first-seen witnessing,
divergence resolved by tier, fail-secure defaults — is told the same way at every layer, and the
three per-primitive correctness-proof documents mirror each other faithfully. I found **one
soundness problem**: the shared-documents constitution, as specified, cannot actually be constructed
for a private document, because its read gate and the document's own identifier are each defined as
a hash of the other (finding 1). The remaining findings are consistency and wording issues that
create friction for a careful reader but do not break the model.

## Reading log

- [x] README.md, USES.md, MODEL.md (top level)
- [x] docs/design/README.md
- [x] 0 — system-thesis.md, glossary.md
- [x] 1 — sad.md, said.md, custody.md, availability.md, compaction.md, kinds.md, shapes.md,
      tags-and-topics.md
- [x] 2 — protocol-doctrine.md, residuals.md, monitoring.md
- [x] 3 — event-shape.md; kel/ (log, events, verification, merge, compromise, reconciliation); iel/
      (log, events, verification, merge, reconciliation, delegation); sel/ (log, events,
      verification, merge, reconciliation)
- [x] 4 — bootstrap.md, witnessing.md, topics.md, mesh-transport.md
- [x] 5 — policy.md, documents.md, evaluation.md
- [x] 6 — essr.md, ipex.md, receive-key-directory.md, group-key.md, membership.md, authored-dag.md
- [x] 7 — credentials.md, exchange.md, shared-documents.md

## Summary of findings

| #   | Severity | Where                                                                  | Finding                                                                                                                                                                                                                                                                       |
| --- | -------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | major    | `features/shared-documents.md`, `primitives/data/sad/shapes.md`        | A private document's constitution cannot be built: its read gate lists chain addresses that are derived from the document's own identifier, which is in turn derived from the read gate — a hash cycle.                                                                       |
| 2   | minor    | `kel/` + `iel/` reconciliation, merge, log                             | A content event beside the chain's seal gets contradictory outcome labels: the proof invariant says it is "retained, not `Sealed`," but the same shape on a terminated chain is labeled `Sealed` throughout, and the local-submissions matrix names no outcome for it at all. |
| 3   | low      | `iel/reconciliation.md`                                                | The local-submissions preamble calls a sealed sibling at the seal's serial "the live-fork case (Forked / Disputed)"; a sealed sibling can never produce Forked, and the parallel KEL passage states it precisely.                                                             |
| 4   | minor    | `protocol-doctrine.md`, `kel/verification.md`, `kel/reconciliation.md` | Five references to a witness receipt's `witnessed_said` field survive from before the field was renamed `eventSaid`; the name they cite no longer exists in the receipt shape.                                                                                                |
| 5   | minor    | `features/credentials.md`                                              | The credential's field-shape block omits `delegationPath`, which the shape catalogue lists and this same document's acceptance rules rely on.                                                                                                                                 |
| 6   | minor    | `primitives/data/event-logs/sel/events.md`                             | The `Trm` taxonomy row reads "terminal-on-divergence" where the shape reference says "seal-advancing, terminal" — the phrase elsewhere describes the sealed class as a whole, and here it misreads as "terminal only on divergence."                                          |
| 7   | low      | `MODEL.md` vs. the design surface                                      | MODEL.md says "deadness spreads downward" across the anchoring link; the design documents fix the opposite direction word everywhere ("deadness ascends," "flows upward").                                                                                                    |

## Findings in detail

### Group A — soundness

#### 1. The private constitution's read gate is circularly derived (major)

**The three statements that jointly conflict.** For a shared document:

- The document's identifier (its prefix) is derived from the constitution V0's **whole content**.
  `features/shared-documents.md`: "Like a chain inception, V0 **derives a `prefix`** (its two-hash
  content digest)"; its shape block: "the doc prefix, derived from this SAD's whole content";
  `shapes.md`: "The doc prefix — derived from V0's whole content"; and `sad.md` fixes the general
  rule: "What content the prefix commits to is per-primitive — **always the whole inception SAD**."
  `custody.md` confirms the `custody` struct is part of that content: its sub-fields "participate in
  the SAD's canonical serialization and the SAID derivation."
- V0 **carries the read gate as content**: "`readers[]` — the initial read gate: the sorted union of
  the three `document-*-membership` SEL prefixes" (`features/shared-documents.md`; the same in
  `shapes.md`'s V0 table).
- Each of those three governance-chain prefixes is itself derived **from the document's prefix**:
  "the SEL's `owner` is the creator IEL …, its `topic` is the reserved membership topic …, and its
  `data` is the **document prefix**" (`features/shared-documents.md`).

**Why this is a genuine break, not a construction-order subtlety.** Write `P` for the document
prefix and `P_edit`, `P_comment`, `P_read` for the three governance-chain prefixes. The three
statements give: each `P_role` is a fixed hash function of `P`, and `P` is a fixed hash function of
the three `P_role` values (they sit inside `custody.readers`, which is inside the hashed content).
Substituting one into the other makes `P` a solution to `P = hash(f(P))` — a fixed point of a
256-bit hash. No minting order escapes this, because both directions are deterministic: to fill in
`readers[]` you need the chain addresses, which need the finished prefix, which needs `readers[]`
filled in. Finding such a fixed point is computationally infeasible by the same collision-resistance
assumption the rest of the design relies on. So, exactly as specified, **a gated (private) shared
document's V0 cannot be minted**. A public document (which omits `readers`) is unaffected — but the
gated case is the flagship confidential-collaboration case, and the read-gate union being "native to
custody" is presented as a load-bearing property ("the three-chain union **is** the custody gate —
no separate feature check").

**Why I believe this is an oversight rather than an unstated resolution.** The design solves this
exact class of problem one layer down and says so: a SEL inception "carries **no `pin` and no
manifest** — either would change the prefix and break the recomputation," so the circular field
rides the serial-1 event instead. V0 is a standalone SAD with no serial-1 event to displace the
field onto, and no analogous carve-out is stated for it anywhere — I checked `said.md`'s
prefix-derivation rules, `sad.md`'s prefix-deriving-SAD paragraph, `custody.md`, `shapes.md`, and
the shared-documents feature itself.

**Sketches of the available shapes for a fix** (the choice is a design decision, listed only to show
the break is repairable without disturbing the rest of the model):

- Key the governance chains on a committed V0 field that exists **before** the prefix — for example
  `data` = the constitution's `nonce` (or a dedicated discriminator field) instead of the document
  prefix. The dependency then runs one way: chains derive from the nonce, the prefix derives from
  everything. The stated rationale ("a creator's chains for two documents derive to distinct
  addresses") is preserved as long as the discriminator is per-document; a public document, which
  may omit the nonce, would need the discriminator to be required.
- Exclude `custody` from V0's prefix derivation with the placeholder mechanism (a documented third
  blanked position, the way `said` and `prefix` are blanked today). This keeps `data` = document
  prefix but weakens the rule that the prefix commits the whole content, so the gate would no longer
  be prefix-committed — a trade to weigh explicitly.
- Drop `readers` from V0 and let the gate ride only the later, non-prefix-deriving document SADs
  (versions, comments, grant-docs), with V0's privacy resting on the unguessable nonce'd prefix
  alone. This changes what the "initial read gate" means and would need the store-enforcement story
  restated.

### Group B — the correctness-proof documents (KEL / IEL)

These two findings are about the same spot — how the documents present a competing event that lands
**beside the chain's most recent seal** — and matter because they sit in the documents whose
explicit job is exhaustive precision.

#### 2. The outcome label for a content event beside the seal is contradictory (minor)

The proof invariant (`kel/reconciliation.md` invariant 5, mirrored in `iel/reconciliation.md`
invariant 5) states that a sibling at the seal's own serial "is **not** in the locked portion — it
is **retained, not `Sealed`**: a content sibling is buried below the seal … while a sealed sibling
is a second seal at that serial." But when the seal in question is a terminal `Trm`, the very same
shape — a content event racing the `Trm` at its serial — **is labeled `Sealed`** everywhere it
appears: `kel/merge.md`'s rejection table ("on a Terminated chain, the **sibling-to-`Trm`** race
(content)"), `kel/log.md`'s Terminated row ("a content sibling to the `Trm` is inert below its seal
(`Sealed`)"), and both reconciliation documents' "other states" summaries and transfer-matrix notes.
The `Trm` advances the seal to its own serial, so the sibling-to-`Trm` is exactly a "sibling at the
seal's own serial" — the case the invariant says is _not_ `Sealed`.

The behavior described is identical in every telling (the content event is non-canonical, buried,
kept as evidence, and the chain state is unchanged); only the outcome name flips depending on
whether the seal is a `Rot`-class event or a `Trm`. Relatedly, the local-submissions matrices
promise that "outcomes are the transition/rejection vocabulary above," yet the Position-2 content
cell in both (`kel/reconciliation.md`, `iel/reconciliation.md`) names no vocabulary outcome at all —
it says "chain stays `Active` — the content sibling is buried," which is not one of the named
transitions or rejections. One consistent statement — either the buried at-seal content sibling is
`Sealed` in both places, or it gets a name of its own in the outcome vocabulary and the
Terminated-chain passages use it — would remove the contradiction.

#### 3. The IEL matrix preamble mislabels a sealed sibling's possible outcomes (low)

`iel/reconciliation.md`'s Matrix-1 preamble says: "A sealed sibling **at the seal's own serial** is
the live-fork case (Forked / Disputed) — Position 2, not this one." A **sealed** sibling can never
yield Forked — Forked is defined throughout as a content-only fork; a sealed sibling at the seal is
Disputed if accepted, otherwise deferred-pending. The parallel KEL passage is precise ("a content
sibling buried → Active; a second accepted sealed sibling → Disputed") and would transplant cleanly.

### Group C — terminology drift

#### 4. Five references to a receipt field name that no longer exists (minor)

The witness receipt's field naming the witnessed event is **`eventSaid`** — in the receipt shape in
`substrate/federation/witnessing.md` and in `shapes.md`'s receipt table, and used correctly in
witnessing.md's prose ("a second receipt over two distinct content `eventSaid`s"). Five passages
still cite it as **`witnessed_said`**, a name that appears in no shape:

- `protocol-doctrine.md` ("two receipts by one witness over two distinct content `witnessed_said`s
  at one position"),
- `kel/verification.md`, three times ("re-checks each receipt's `witnessed_said`…"; "a rogue who
  signs receipts on a fake `witnessed_said`…"; "receipts below threshold for some
  `witnessed_said`…"),
- `kel/reconciliation.md` ("receipts at the same chain position carrying different `witnessed_said`
  values").

All five clearly mean the receipt's field (they are possessives of "receipt"), so a reader
cross-referencing the receipt shape finds nothing under the cited name. These read as stragglers
from the round that renamed the receipt's record fields to camelCase.

#### 6. "terminal-on-divergence" applied to the SEL kill event (minor)

In `kel/log.md` and `iel/log.md` the phrase "record-both and **terminal-on-divergence**" describes
the sealed spine as a class — sealed events are recorded on both sides of a divergence, and such a
divergence is terminal. `sel/events.md`'s taxonomy then uses the phrase for the `Trm` row alone:
"The **kill** — closes the SEL. Sealed on arrival, monotone, terminal-on-divergence." But the `Trm`
is terminal outright — `event-shape.md`'s SEL table says "Sealed on arrival, seal-advancing,
terminal" — and the row's sealed siblings carry "seal-advancing" (`Gnt`: "sealed on arrival,
seal-advancing, non-buriable"; `Sea`: "… non-terminal") while the `Trm` row drops it. As written the
row invites the reading "terminal only when a divergence occurs."

#### 7. MODEL.md's deadness direction contradicts the design surface's (low)

The design surface fixes one direction word for how deadness propagates: "**deadness ascends**: an
event whose parent is dead is dead" (glossary, protocol-doctrine, the reconciliation documents), and
across the anchoring link, "**Deadness flows upward** along the anchoring edge" (`sel/log.md` —
consistent with the stack diagrams, which draw the anchored log above its anchor). MODEL.md
describes the same phenomenon with the opposite word: "every artifact event the anchor named dies
with it: **deadness spreads downward** and crosses the anchor." Within MODEL.md's own narrative the
sentence is understandable, but a reader who moves from MODEL.md into the design documents meets the
same mechanism under an inverted direction word. Aligning MODEL.md's sentence (or making it
direction-neutral — "dies with it, and the deadness crosses the anchor") removes the flip.

### Group D — shape catalogues

#### 5. The credential wrapper block omits `delegationPath` (minor)

`shapes.md`'s credential table carries `delegationPath` ("Present iff issued under **delegated**
authority — the ordered committed path…"), and `features/credentials.md` itself relies on it in the
acceptance rules ("the committed delegation path (the credential's `delegationPath` field …) is not
rescinded past its grandfather bound") and `primitives/policy/documents.md` §Delegation defines its
well-formedness. But the credential's field-shape block at the top of `features/credentials.md` —
presented as "the common wrapper every type carries" — lists ten fields and omits `delegationPath`.
A reader comparing the two listings finds them disagreeing about what the wrapper is; adding the
optional field (marked present-only-when-delegated, as `shapes.md` has it) closes the gap.

## What was checked and held

For a cold review the clean results carry information too. The following were checked deliberately
and came out consistent; none of it is a finding.

- **The two-tier model and the kind-strict anchor matrix** are stated identically in the glossary,
  protocol-doctrine, event-shape, and all three per-primitive groups — including the subtle corners:
  the tier of each inception kind (KEL and SEL inceptions tier 1, IEL tier 2, with the KEL founder
  variant tier 1), the identity-bond openings (an initial member anchors the identity's inception
  with its serial-1 key-change while a later-added member consents with a serial-1 content event,
  the tier-2 authorization coming from the continuing quorum), and the rule that the reserve defends
  the signing key and never the rotation key (no inverted statement of it exists anywhere — swept
  with grep-terms).
- **The divergence story** — freeze on a live fork, resolution by tier, burial by position plus
  ascent, the accepted-sealed-branch count (0 → Forked, 1 → Active, 2+ → Disputed, counted per
  branch wherever the seals sit), below-seal stragglers dropped as the backdating defense, and the
  retained-evidence bounds — is told identically in the system thesis, the doctrine, and the three
  reconciliation proofs; the three merge documents' routing orders and outcome vocabularies mirror
  one another, including the deliberate diagnostic ordering rationale.
- **The effective-SAID (fingerprint) model** — a real tip when one confirmed tip exists, a
  verdict-tagged stable marker otherwise, never a digest over competing tips — matches across the
  doctrine, the tag catalogue's derivation entry, all three verification tokens, MODEL.md's
  plain-English telling, and the monitoring note.
- **Witnessing arithmetic and bounds**: the worked minimum-federation example (roster 4, three to
  govern, two-of-three to witness) satisfies every stated bound; the recoverability cap, the
  exclude-self pool, and the witnessing floor are stated identically in doctrine, the IEL events
  document, and witnessing.md; the risk products in the residuals catalog's ranked tables all
  multiply out to their stated bands.
- **The catalogues agree with their consumers**: every SEL topic, derivation tag, grant kind, and
  gossip topic used by delegation, documents, membership, exchange, and shared-documents appears in
  the catalogues under the same name and derivation shape (including the commitment formula and the
  lineaged/non-lineaged kill-target split); the receipt shape, ESSR envelope, IPEX grant, chat
  message, and document SAD shapes match between shapes.md and their owning documents (with the one
  exception in finding 5).
- **Earlier-round repairs held up under a fresh read**: the "at most one content event per SEL per
  owner-anchor" rule is now enforceable (anchor-identity dedup in the SEL verifier's per-event
  checks); the value-lookup lineaged-target obligation is stated at the primitive, the residuals
  catalog, and the receive-key directory consistently; MODEL.md's claim that every artifact event is
  "pinned to and named by" an identity-log event checks out (the recomputable inception is the
  documented exception, and a bare inception is explicitly evidence of nothing).
- **No stale vocabulary from sibling designs**: no third tier, no recovery key (outside its
  negation), no repair event (outside its negation) anywhere on the surface.

## Method

I read every document in the prescribed order in full, keeping a running note of claims that later
documents would either corroborate or contradict, and resolved each tracked thread before moving on.
Cross-document phrase checks used `scripts/grep-terms.pl` (decoration- and wrap-tolerant) with plain
`grep` for exact identifiers; the sweeps behind the findings above were: "terminal-on- divergence"
(three sites), `witnessed_said` versus `eventSaid` (five stale versus five canonical sites), the V0
derivation statements ("data is the document prefix" / "sorted union of the three" / "whole
inception SAD" / "whole content"), the deadness-direction vocabulary, and the stale- vocabulary
sweeps (tier 3, recovery key, repair event, reserve-defends inversions). Per the brief, existing
files in `docs/design/reviews/` were not consulted for findings; constants and formulas were not
audited except where an argument I was checking depended on one.
