# Design Review — Correctness/Soundness and Consistency (Fable, max effort)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_5.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

## Scope and method

This is a cold review: it reads the current files fresh, in the reading order given by
`docs/design/README.md`, and judges each document on what it actually says — not on memory of
earlier drafts or on other reviews. The axes are **correctness/soundness** (does each stated rule
hold up under an adversarial reading; do the mechanisms actually deliver the properties claimed) and
**consistency** (do the documents agree with each other on names, rules, shapes, and numbers).

Documents read, in order: the repository `README.md`; `docs/design/README.md`; orientation
(`system-thesis.md`, `glossary.md`); the data substrate (`sad/` group and the identifier
catalogues); cross-cutting doctrine (`protocol-doctrine.md`, `residuals.md`, `monitoring.md`); the
event-log primitives (`event-shape.md`, then the KEL, IEL, and SEL groups); federation and
witnessing (`bootstrap.md`, `witnessing.md`, `topics.md`, `mesh-transport.md`); the
document-authorization layer (`policy/` group); the protocol primitives (`essr.md`, `ipex.md`,
`receive-key-directory.md`, `group-key.md`, `membership.md`, `authored-dag.md`); and the feature
layer (`credentials.md`, `exchange.md`, `shared-documents.md`).

Status: **complete.** All 41 documents were read in the reading order; the load-bearing machinery
(divergence and recovery, the effective-SAID model, federation witnessing, cross-layer severance,
the negative-check and disjointness enforceability arguments) was stress-tested rather than skimmed;
and the cross-reference graph and the named protocol constants were swept mechanically.

## Bottom line

The design is **sound and highly consistent.** On the two review axes:

- **Correctness / soundness** — I attacked the parts most likely to hide a break: the
  content-versus-sealed divergence resolution, the "two accepted sealed branches → Disputed"
  detection and its node-agnostic effective-SAID convergence, the SEL's self-witnessing plus
  inherited severance, the federation recoverability arithmetic, and the enforceability of the
  stated dedup / disjointness / negative checks. Every one held up. The design is also honest about
  the checks it does **not** fully enforce in the primitive (most notably the value-lookup lineaged
  `kills[]` target), labelling them as feature-layer obligations rather than hiding them.
- **Consistency** — the nine named protocol constants each carry one value everywhere; the glossary,
  the taxonomy tables, and the per-primitive docs agree on every kind's tier and threshold slot; and
  the internal link graph is clean (1283 links resolve, zero broken; the eight forward-references
  are all registered as forthcoming).

What follows are the few genuine items worth an edit. None is a soundness break; all are polish
(precision, coherence, and one explicitness note). They are grouped by theme, with a summary table
first. A closing section records the substantive properties that were checked **and hold**, so the
next reviewer sees what was actually exercised, not only what was flagged.

## Summary of findings

| #   | Group              | Severity | One-line                                                                                                                                                                                                                                                | Where                          |
| --- | ------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| F1  | Naming consistency | Low      | The four-segment identifier convention is written with different placeholder names (`<concept>/<thing>`) in one doc than in the canon (`{component}/{name}`).                                                                                           | `system-thesis.md`             |
| F2  | Factual precision  | Low      | "A power of two, like the other protocol constants" is not true of every protocol constant (129 and 365 are counterexamples).                                                                                                                           | `iel/verification.md`          |
| F3  | Coherence          | Low      | The anti-entropy fetch on a diverged chain is described two different ways (send the synthetic → whole-chain re-walk; vs. fetch `since: last seal` → post-seal window) without reconciling them.                                                        | `protocol-doctrine.md`         |
| F4  | Explicitness       | Low      | The three shared-document governance SELs are said to be "derived from the doc prefix" without stating the actual derivation inputs (owner = creator IEL, doc-prefix as `data`); it is determinable by composition but never written down in one place. | `features/shared-documents.md` |

## Findings — detail

### Group A — naming and precision

#### F1 — the identifier convention is described with non-canonical placeholder names (Low)

Every doc that introduces the shared identifier scheme writes it as
**`vdti/{component}/v1/{category}/{name}`** — four segments — and `kinds.md`
([§The naming convention](../primitives/data/sad/kinds.md)) is the canonical statement of it. The
one outlier is `system-thesis.md`, which writes the same scheme as
`vdti/<concept>/v1/<category>/<thing>` (in _Implications → Uniform data_). Two of the four
placeholders differ in name — "concept" for "component", "thing" for "name" — even though they refer
to the same positions. A reader who meets the convention first in the thesis (which is the doc the
reading order puts **first**) learns two labels that no other doc uses.

- **Why it matters:** it is purely cosmetic, but the thesis is the orientation doc, so its wording
  sets the reader's vocabulary. The mismatch is small friction, not an error.
- **Suggested fix:** change the thesis to `vdti/{component}/v1/{category}/{name}` (or
  `<component>`/`<name>`) so the first mention agrees with the catalogue that owns the convention.

#### F2 — "a power of two, like the other protocol constants" is imprecise (Low)

`iel/verification.md`, introducing `MAXIMUM_DELEGATION_DEPTH = 8`, says it is "**a power of two,
like the other protocol constants**, and fixed — not a per-deployment knob." Several of the size-cap
constants **are** powers of two (`MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_UNSEALED_RUN = 64`,
`MAXIMUM_SEL_LINEAGE = 64`, `MAXIMUM_GRANT_ADDS = 64`, `MAXIMUM_MANIFEST_LIST = 128`), but "the
other protocol constants" is not a set that is uniformly powers of two: `MINIMUM_PAGE_SIZE = 129` (=
`2·64 + 1`) and `MAXIMUM_WITNESS_KEY_WINDOW = 365 days` are protocol constants that are not, and
`CLOCK_TOLERANCE_BAND = 1 minute` is a time value.

- **Why it matters:** it is a throwaway justification, not a load-bearing rule, so nothing breaks —
  but as written the claim is falsifiable by two of the constants it appeals to.
- **Suggested fix:** narrow the comparison to the family it means — e.g. "a power of two, like the
  other **size-cap** constants" — or drop the "like the other protocol constants" clause.

### Group B — coherence and explicitness

#### F3 — two different anti-entropy cursors are described for a diverged chain (Low)

Two sections of `protocol-doctrine.md` describe how a node re-syncs a chain whose effective-SAID has
moved, and they give different pictures of the same diverged case:

- **§Caching and continuation** says the consumer "queries with the token's effective-SAID as a
  `since` cursor," and when that cursor "is not a stored event — a `forked` / `disputed`
  **synthetic** … the lookup simply misses and the source returns the **whole chain from the start**
  (the first page)," so "a fork or dispute just costs a full re-walk."
- **§Effective-SAID comparison** says "a node fetches `since: {its own last seal}` — pulling
  everything from that seal forward (the canonical tip, every competing branch above it, a burying
  seal-advancer) **plus the seal's own siblings**," a bounded post-seal window.

Both are safe (the two fetches converge, and a whole-chain re-walk is a superset of the post-seal
window), so this is **not** a soundness problem. But the two passages leave a reader implementing
anti-entropy with two different answers to "which cursor do I send when my effective-SAID is a
synthetic, and how much do I re-fetch?" The §Effective-SAID strategy (send the last seal, which is a
real SAID the node holds, and pull the bounded post-seal window) is strictly the better one; the
§Caching passage reads as if the only option on divergence is to send the synthetic and eat a full
re-walk.

- **Suggested fix:** reconcile the two — state in §Caching that a node whose effective-SAID is a
  synthetic fetches `since: {its last seal}` (a held real SAID) rather than sending the synthetic,
  so the diverged fetch is the bounded post-seal window of §Effective-SAID, and the "synthetic
  misses → whole chain from start" path is only the defensive fallback when a node has no held seal
  to anchor on. A one-line cross-reference between the sections would close it.

#### F4 — the shared-document governance-SEL derivation is left implicit (Low)

`features/shared-documents.md` says a holder "derives [the three governance chains] from the **document
prefix** plus the protocol's reserved topics," and that `said(G)` is honored only when it resolves to
a `Gnt` "sealed on the creator's `document-edit-membership` SEL (the chain **derived from the doc prefix**)."
The reserved topics are given (`vdti/doc/v1/topics/edit-membership`, …). What is never stated in one
place is the actual SEL derivation inputs: a SEL's address is the two-hash digest over its `Icp` body
— `owner`, `topic`, `data`, and the optional flags — and a SEL's `owner` **must be an IEL prefix** ([`sel/log.md`](../primitives/data/event-logs/sel/log.md)).
The document prefix is a **V0 constitution SAD** prefix, not an IEL prefix, so it cannot be the SEL's
`owner`.

Composing the pieces, the derivation is forced: `owner` = the **creator IEL** (the doc says the
creator **owns** the three grant chains), `topic` = the fixed reserved topic, and the **doc prefix
rides as `data`** (it has to — the topic string is identical across every document, so without the
doc-prefix as `data` a single creator's edit-membership SELs for two different documents would
collide at one address). So the derivation is fully determined by composition; it is just never
written down, and the phrase "derived from the doc prefix" can read as if the doc prefix were the
`owner`.

- **Why it matters:** the honored-predicate seal-locate is a total-bypass surface (the doc itself
  flags that "skip the seal-locate and the gate is a total bypass"), and it rests on the verifier
  deriving the **right** SEL address. Getting `owner`/`data` wrong there is a security-relevant
  implementation error, so the derivation deserves to be explicit rather than reconstructed.
- **Note on scope:** the concrete grant-doc / SEL shapes are marked **forthcoming** in `shapes.md`,
  so this is legitimately a feature-encode detail. The suggestion is only to state, at that encode,
  the derivation tuple `(owner = creator IEL, topic = the reserved topic, data = doc prefix)`
  explicitly — and, if cheap, to add a half-sentence to `shared-documents.md` now.

## What was checked and holds

A correctness review is as much about what was exercised as what was flagged. These are the
load-bearing properties I attacked and found **sound and internally consistent** — recorded so the
next pass knows they were genuinely tested, not assumed.

- **Divergence resolution is uniform and tier-scoped across KEL / IEL / SEL.** The
  content-first-seen / sealed-record-both split, the "burying seal-advancer resolves a content-only
  fork," and "≥ 2 accepted sealed branches → Disputed → reincept" are stated identically in the
  cross-cutting doctrine and specialised correctly per primitive (the IEL adds eviction via a `cut`
  `Evl`; the SEL adds the neutral `Sea` and inherited severance). The four reconciliation matrices
  (KEL 1–4, IEL 1–4, SEL 1–3) are mutually consistent and each terminates every case.
- **The effective-SAID model converges node-agnostically.** The `forked` / `disputed` synthetic is a
  type-tagged, set-independent value keyed on prefix + the divergence ancestor (never a digest over
  the competing tips), so it is flood-stable; a forked-reading node and a disputed-reading node
  compute structurally-distinct values (different `states/*` qualifier), which is exactly the
  anti-entropy signal, and both converge once the branches propagate. The "the value can't hide a
  revocation" argument (any non-single-tip state grounds no new trust → fail-secure) holds.
- **Federation recoverability arithmetic is self-consistent.** The witnessing floor
  (`threshold > signers/2`), the federation recoverability cap
  (`threshold ≤ min(|roster| − 2, signers − 1)`), and `|roster| ≥ 4` compose to the worked
  `{ threshold 2, signers 3 }` minimum, and the exclude-self self-attest pool of `|roster| − 2` is
  reflected consistently in `witnessing.md`, `iel/events.md`, `bootstrap.md`, and
  `protocol-doctrine.md`.
- **Stated checks are enforceable — including the ones the round-1 review class warned about.** The
  SEL "≤ 1 content `Ixn` per owner-IEL `Ixn`" dedup is performable during the SEL walk (the verifier
  holds the pin and the anchor). The shared-document per-member **period-disjointness** check opens
  every grant on the witnessed chain and reads **conservative on a withheld grant-doc** (can't
  establish disjointness → don't honor), so opacity degrades to fail-secure rather than defeating
  it. The negative-check-as-positive-lookup rule rides the same multi-source freshness gate as
  divergence, so hiding a kill needs a stale chain the verifier already refuses.
- **The one genuinely un-backstopped check is disclosed, not hidden.** The value-lookup lineaged
  `kills[]` target (the receive-key directory is its first consumer) is explicitly called out — in
  `sel/verification.md`, `sel/reconciliation.md`, `receive-key-directory.md`, and `residuals.md` §11
  — as a **feature-layer obligation the primitive does not enforce**, with the failure mode named (a
  rescission that declares only an on-chain `Trm`, or a wrong-lineage target, leaves the kill on the
  withholdable leg). This is the honest treatment the design should give an unenforced invariant.
- **Tier / threshold mapping agrees everywhere.** Every kind's tier and threshold slot
  (`Ixn`/`t_use`, `Evl`/`Rev`/`Wit`/`Trm`/`t_govern`, `Ath`/`Dth`/`t_authorize`, and the SEL `Gnt`
  `t_authorize` / `Sea` `t_govern` / `Trm` `t_govern`-or-`t_authorize`) is identical across
  `event-shape.md`, `glossary.md`, and the per-primitive `events.md` files.
- **The layering is acyclic and the seams are honest.** Policy declares the verification-token
  interface the primitives implement (dependency inverted); credentials depends on IPEX and never on
  ESSR; the SEL authenticates down to owner-IEL to member-KEL signatures with no upward dependency;
  and the "verifier reports, merge gates" split is applied uniformly.
- **Named constants and cross-references are mechanically clean.** All nine protocol constants carry
  a single value across the corpus; `check-doc-xrefs.py` reports 1283 resolved links, 0 errors, and
  8 forward-refs, each registered in `.docs-xref-ignore` against an exact forthcoming path.
