# Design Review — Fable (max) — 2026-07-22, pass 0

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_0.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

## Scope and method

This is a cold review: a fresh read of the whole design surface, in the reading order given by
[`docs/design/README.md`](../README.md), with no reliance on earlier review passes. Every document
in the reading order was read in full — the orientation pair, the five data-substrate docs and their
three identifier catalogues, the cross-cutting doctrine trio, all seventeen event-log docs (the
shared shape reference plus the KEL, IEL, and SEL groups), the four federation and transport docs,
the three policy docs, the six protocol primitives, and the three features — plus the root
`README.md`, `MODEL.md`, and a check of `USES.md`, roughly 17,500 lines. Cross-document phrase
sweeps were run with `scripts/grep-terms.pl` (which sees through markdown decoration and line wraps)
to confirm each consistency finding's full site list and to hunt for stale terminology.

The two axes under review:

- **Correctness / soundness** — does each stated rule actually hold under an adversary? Are the
  arguments valid? Can every stated check actually be performed by the party asked to perform it?
- **Consistency** — do the documents agree with each other? Does a term mean the same thing at every
  site? Do cross-references point at what they claim?

Each finding names the file and section it lives in, quotes the text at issue, and explains the
problem in plain language. Severity is one of:

- **High** — a soundness break: a rule that does not hold, a check that cannot be performed, an
  argument whose conclusion does not follow — or a contradiction on a rule where two conforming
  implementations would disagree about the same data.
- **Medium** — a gap or contradiction that would mislead an implementer, but with a recoverable
  reading.
- **Low** — a consistency slip, stale pointer, or missing specification with an obvious repair.
- **Note** — an observation worth recording; no change strictly required.

## Summary of findings

Eleven findings: one High, two Medium, six Low, two Notes. The one High finding is a genuine
contradiction between documents on an acceptance rule (what a valid roster-change event may
contain); nothing in the review found a broken security argument — the load-bearing soundness
arguments were attacked and held (see "What was attacked and held" at the end).

| #   | Severity | Where                                                     | Finding (one line)                                                                                                                     |
| --- | -------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | High     | `protocol-doctrine.md`, `event-shape.md`, `iel/events.md` | The "a `cut` `Evl` never carries an `add`" rule contradicts the device-swap example and the IEL doc's singleton evict-and-replace      |
| B2  | Medium   | `iel/delegation.md`                                       | "Tip `Gnt` → live" reads as concluding delegation liveness from an absence — the withholdable leg the rest of the design refuses       |
| C1  | Medium   | `protocol-doctrine.md` §Verification tokens               | "An unwitnessed chain degrades to single-source, flagged" contradicts no-direct-mode and the refuse-never-flag posture                 |
| A1  | Low      | `residuals.md`                                            | Mojibake ("â" for an em-dash) in the inherent trade-offs table                                                                         |
| A2  | Low      | doctrine, thesis, `event-shape.md`, SEL docs              | "The floor `Pin`" as the epithet for the buriable content kind conflicts with `Pin`'s any-serial definition                            |
| A3  | Low      | `protocol-doctrine.md` §Kills                             | The rescission `bound` is described as living only in `kills[]`; the gated SEL-`Trm` custody mode is elided                            |
| B3  | Low      | `kel/log.md` §Per-node chain states                       | The Forked row omits `Trm` as a legal fork-resolving move (bury-and-terminate)                                                         |
| D1  | Low      | `policy/documents.md` §Multi-identity                     | The multi-identity attestation SEL's topic and derivation inputs are specified nowhere                                                 |
| D2  | Low      | `sel/events.md` §`Gnt`                                    | A 64-character kind-string cap is asserted "like any event or SAD kind" but the kind catalogue states no such cap                      |
| A4  | Note     | doctrine §Query-scoping, glossary                         | Absolute "a non-witness holds only witnessed-in-full events" phrasing vs. the ancestry-acceptance rule stated in `kel/verification.md` |
| A5  | Note     | `residuals.md`                                            | The "Forced-dead receive key" table row and its detailed entry describe different attack paths to the same outcome                     |

## Reading progress

- [x] 0 — Orientation: `system-thesis.md`, `glossary.md`
- [x] 1 — Data substrate: `sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`,
      catalogues (`kinds.md`, `shapes.md`, `tags-and-topics.md`, federation `topics.md`)
- [x] 2 — Cross-cutting doctrine: `protocol-doctrine.md`, `residuals.md`, `monitoring.md`
- [x] 3 — Event logs: `event-shape.md`; KEL (6 docs); IEL (6 docs); SEL (5 docs)
- [x] 4 — Federation and witnessing: `bootstrap.md`, `witnessing.md`, `topics.md`,
      `mesh-transport.md`
- [x] 5 — Document authorization: `policy.md`, `documents.md`, `evaluation.md`
- [x] 6 — Protocol primitives: `essr.md`, `ipex.md`, `receive-key-directory.md`, `group-key.md`,
      `membership.md`, `authored-dag.md`
- [x] 7 — Features: `credentials.md`, `exchange.md`, `shared-documents.md`
- [x] Root docs for consistency: `README.md`, `MODEL.md`, `USES.md`
- [x] Cross-cutting terminology sweeps (`scripts/grep-terms.pl`)

## Open threads (raised early, resolved against later docs)

Questions the early layers raised whose answers live in later docs, kept here as the record of how
each resolved — into a finding, or into "no issue."

1. **Stalled content made canonical by a seal above it.** **Resolved → finding A4 (Note).** The
   doctrine's split-stall exit lets an accepted seal commit a content sibling that never
   individually reached its receipt threshold, while the query-scoping passage says a non-witness
   holds only fully-witnessed events. `kel/verification.md` §"Acceptance gates the tip; an accepted
   event commits its ancestry" states the reconciliation explicitly; the doctrine and glossary
   absolutes just lack a pointer to it.
2. **Where a rescission's `bound` lives.** **Resolved → finding A3 (Low).** Two custody modes exist
   (public in `kills[]`; gated on the sealing SEL `Trm`'s `bound` role), stated in `event-shape.md`
   and `iel/events.md`; the doctrine's §Kills names only the public one.
3. **"Unwitnessed chain degrades to single-source, flagged."** **Resolved → finding C1 (Medium).**
   `witnessing.md` states the opposite posture ("refuses, never proceeds with a flag") and
   eliminates the premise (there is no unwitnessed mode).
4. **"The SEL's floor `Pin`" as the buriable-content qualifier.** **Resolved → finding A2 (Low).**
   Every `Pin` (at any serial) is tier-1 buriable content per the taxonomy; "floor `Pin`" turns out
   to be a pervasive epithet, used even inside the SEL's own docs, that literally conflicts with the
   any-serial definition.
5. **The `cut` `Evl`'s "never an `add`" rule vs. the device-swap example.** **Resolved → finding B1
   (High).** `iel/events.md` explicitly allows singleton evict-and-replace (`cut 1 + add 1`),
   directly contradicting the "never an `add`" clauses.
6. **What anchors a user IEL `Icp`.** **Resolved — no issue.** `kel/events.md` §The identity bond: a
   founding member's serial-1 event is a `Rot` anchoring the identity's inception; an added member's
   is a consent `Ixn` anchoring the admitting `Evl`. Consistent with kind-strict anchoring and the
   taxonomy.
7. **The multi-identity attestation SEL.** **Resolved → finding D1 (Low).** `documents.md` describes
   it, but no catalogue pins its topic or derivation inputs, and the forthcoming-shapes table does
   not name it.

## Findings

### Group A — Orientation and cross-cutting doctrine

#### A1. Mojibake in `residuals.md` (encoding defect) — Low

`residuals.md`, "Roster / seal caps" row of the inherent trade-offs table:

> so a high-volume log recurs that ceremony every 64 content events â a deployment planning one
> should budget the cadence

The "â" is a mangled em-dash (a UTF-8 encoding slip, the known hazard of editing multibyte text with
a byte-oriented tool). One-character fix.

#### A2. "The floor `Pin`" as the name of the buriable content kind — Low

`protocol-doctrine.md` §Terminology and §Forks are Seal-Bounded define the buriable content class
as:

> **content** is tier 1 — `Ixn` (and the SEL's floor `Pin`)

`system-thesis.md` §Divergence uses the same phrase, and the sweep found the pattern throughout the
SEL's own docs (`sel/log.md`, `sel/events.md`, `sel/merge.md`) and in `event-shape.md`'s
`previousSeal` field row. But `Pin` is defined — in the glossary, `event-shape.md`, and
`sel/events.md` itself — as "the pin-only re-pin **at any serial**," with only its serial-1 instance
being the issuance floor; every `Pin` is tier-1 buriable content. So "the floor `Pin`" is
functioning as an epithet for the kind (like "the neutral `Sea`"), not as a restriction — but read
literally it excludes a later re-pin `Pin` from the content class, and the content-versus- sealed
split is exactly what the divergence rules dispatch on. Since the epithet is pervasive and evidently
deliberate, the cheapest repair is a one-line gloss (in the glossary's `Pin` entry, or at the
doctrine's first use): "the floor `Pin`" names the kind whose serial-1 instance is the floor, and
every `Pin` at any serial is content. Alternatively drop "floor" at the class-defining sites.

#### A3. §Kills describes only the public custody mode of a rescission `bound` — Low

`protocol-doctrine.md` §Kills are sealed:

> A **validity bound** removes a **contiguous suffix** of a chain — whether it is a rescission's
> `bound` (declared in the `Dth`'s `kills[]`) …

`event-shape.md` and `iel/events.md` define **two** custody modes for the same `bound` concept: the
inline-public `kills[].bound` (a delegate rescission — not participant-identifying) **and** the
gated `bound` role on the sealing SEL `Trm` (a doc-member or chat-membership rescission, where the
cutoff would identify a participant, so `kills[]` carries only the blind target). The doctrine
paragraph names only the first, so a reader of the doctrine alone would conclude every rescission
bound is public in `kills[]`. One clause ("or, when participant-identifying, gated on the sealing
SEL `Trm`'s `bound` role") aligns it.

#### A4. Query-scoping and "confirmed tip" absolutes vs. ancestry acceptance — Note

`protocol-doctrine.md` §Query-scoping states "a non-witness therefore holds only witnessed-in-full
events," and the glossary's "confirmed tip" entry states "(a non-witness never even holds a
sub-threshold event — query-scoping)." Both read as absolutes. But the split-stall exit (§Federation
convergence) lets an accepted seal commit a **sub-threshold content sibling** as canonical ancestry,
and the stale-pin recovery path in `witnessing.md` does the same for a run of deferred events.
`kel/verification.md` §"Acceptance gates the tip; an accepted event commits its ancestry" states the
reconciliation explicitly: an accepted event's whole `previous`-chain becomes canonical **with** it,
including ancestors that never individually reached threshold — which a non-witness then must hold.
The design is coherent (an ancestor committed this way is no longer a _pending_ event, which is what
query-scoping withholds), but the doctrine/glossary absolutes and the KEL-verification
reconciliation live far apart; a one-line pointer from §Query-scoping or the glossary entry to the
ancestry-acceptance rule would prevent the apparent contradiction.

#### A5. Ranked-table requirements vs. detailed entry for the forced-dead receive key — Note

`residuals.md`: the irreducible table's "Forced-dead receive key" row names its requirement as "a
`t_authorize` reserve quorum — forge a `Trm` rescind," while the corresponding detailed entry (§9,
"Value-bearing lookup DoS (collusion-forced)") describes a different attack path — witness collusion
forcing the locus into dispute. Both paths exist and both end in the same outcome (senders fail
closed until the owner republishes at a fresh lineage); the table prices the higher-risk one, which
is conservative. Worth a cross-note so the two entries read as the same residual reached two ways.

### Group B — Event-log primitives (KEL / IEL / SEL)

#### B1. The `cut` `Evl` "never an `add`" rule contradicts the worked examples and the IEL authority — High

Three statements of an acceptance rule disagree with two worked examples and the per-primitive
authority. The rule, as stated:

- `protocol-doctrine.md` §Divergence and recovery: "The `cut` `Evl` carries a **required non-empty
  `cut` + an optional `threshold` change — never an `add`, never a `threshold`-only change**."
- `event-shape.md`, the `roster` role description: "a `cut` `Evl` carries a **required non-empty
  `cut`** + optional `threshold`, **never** an `add`."
- `event-shape.md`, §Per-kind structural validation (IEL notes): "On a `cut` `Evl`, `roster` carries
  a **non-empty `cut` + an optional `threshold`**, never an `add`."

Against:

- `event-shape.md`'s own device-swap walkthrough: "replacing device X with Y is an IEL `Evl`
  carrying a roster delta (`cut X, add Y`)" — one event carrying both, with the anchor diagram
  showing the joiner's consent riding the same `Evl`.
- `iel/events.md` §The threshold vector and its bounds: "a singleton roster is downward-immutable
  **while still allowing singleton evict-and-replace (`cut 1 + add 1` stays 1)**" — an `Evl`
  carrying both, and load-bearing for the never-emptied derivation: a lone `cut` on a singleton
  computes an empty roster and is rejected, so under the "never an `add`" rule a single-device
  identity could never swap its device at all.
- `shapes.md`'s general roster-delta well-formedness, which permits `add` and `cut` together
  (disjoint), restricting `add` cardinality only on a federation `Wit`.
- `protocol-doctrine.md` itself, for the federation facet: "evict-and-replace is
  `cut: [..], add: one`."

This is a contradiction on a **consensus-relevant acceptance rule**: an implementer following the
doctrine/event-shape statements rejects a combined `{cut, add}` `Evl` that an implementer following
`iel/events.md` accepts — and the combined event is exactly the device-swap and singleton-replace
flow. Two conforming verifiers would then disagree about the same event, which is the class of
divergence the design everywhere else eliminates.

A scoped reading exists and has support: the doctrine's sentence sits inside the fork-recovery
eviction passage ("one sealing event that buries the fork **and** evicts"), so "the `cut` `Evl`" may
mean specifically the **fork-burying** eviction, with an ordinary (no-fork) `Evl` free to carry
`cut` and `add` together. Under that reading everything reconciles except `event-shape.md`'s two
statements, which present the rule as unscoped per-kind validation. But the scoped rule has its own
problem: whether an `Evl` is fork-burying is a property of its attach position and the validator's
view of the fork, not of the event's payload — the witnesses selected for the `Evl`'s serial are not
the witnesses of the fork serial below it, so a payload restriction conditional on fork-shape would
make the same event's validity view-dependent, a property the design forbids everywhere else. My
read is that the cleanest repair is to drop the "never an `add`" clause entirely (an eviction MAY be
pure-cut as operational guidance) and fix the three sites; if the restriction is genuinely wanted,
it must be scoped explicitly at all three sites and its enforcement point named (presumably the same
witness shape-validity gate that runs the no-burying-a-sealed-branch check, with the same
accepted-state semantics). Either way, one reading must be made canonical at all five places.

#### B2. "Tip `Gnt` → live" reads as a fail-open conclusion on the delegation-liveness check — Medium

`iel/delegation.md` §Delegate, then rescind:

> The check reads the delegating-link SEL **first** (O(1) — tip `Gnt` → live, tip `Trm` →
> rescinded); on a miss it is **fail-secure by default** — walk the delegator's fresh IEL …

"Tip `Trm` → rescinded" is sound unconditionally: a kill is monotone, so presence proves it. But
"tip `Gnt` → live" as an O(1) conclusion infers **liveness from the absence of a `Trm`** on whatever
the store served — and a store that withholds the `Trm` serves exactly `{Icp, Gnt}`. The rest of the
design treats that leg as withholdable and backstops it:

- `iel/verification.md` §The bounded delegation walk: "Each hop's liveness is a `kills[]`
  forward-match … **never a scan for the absence of a rescission**."
- `protocol-doctrine.md` §Negative checks: the O(1) read concludes only **present → killed**; "a
  withheld object reads not-found, so a miss is authoritative only after the walk."
- `residuals.md` §Fail-open negative-check opt-out names "a rescinded delegation … read as valid"
  under withholding as the **opt-down** failure mode, not the default.
- `sel/verification.md` is careful in exactly this spot: its `is_killed` accessor labels the
  SEL-side read "the **fail-open fast path** at the monotone address; the authoritative fail-secure
  `kills[]` walk is the feature layer's."

The charitable reading is that "miss" in the delegation sentence means "the kill not found" (SEL
absent **or** tip `Gnt`), so the live conclusion always runs the fall-through — but the
parenthetical as written presents "tip `Gnt` → live" as an O(1) verdict, and an implementer taking
it literally builds a fail-open default on a security-critical path (a withheld `Trm` keeps a
rescinded delegate alive). Recommend rephrasing so the O(1) leg concludes only "rescinded" from
presence, with "live" requiring either the fresh-IEL `kills[]` walk (which the delegation walk
performs anyway to confirm the `Ath`) or a freshness-confirmed witnessed SEL tip.

#### B3. `kel/log.md`'s Forked row omits `Trm` as a legal resolving move — Low

`kel/log.md` §Per-node chain states (Forked row) says the way forward is "a **burying
seal-advancer** (a `Rot` / `Wit`) on the winning branch … after which the chain re-reads Active,"
mentioning `Trm` only in the same-serial `{Trm, content}` tier-rank carve-out. But the doctrine, the
glossary, and `kel/merge.md` (its Terminated transition: "a `Trm` … buries a content loser below its
own seal") all allow a `Trm` authored **above** the fork on the winning branch as a
bury-and-terminate in one event. The Forked row's "(a `Rot` / `Wit`)" is scoped to the
re-reads-Active outcome, but as written it under-states the legal exits from Forked. One clause
fixes it.

### Group C — Federation and witnessing

#### C1. "An unwitnessed chain degrades to single-source, flagged" contradicts the witnessing doctrine — Medium

`protocol-doctrine.md` §Verification tokens as proof of verification:

> a loss-of-trust decision confirms each dependency's effective-SAID **multi-source** (a
> witness-signed effective-SAID is multi-source by construction; an unwitnessed chain degrades to
> single-source, flagged).

Two problems. First, the premise: "an unwitnessed chain" does not exist in the current design —
`witnessing.md` §No direct mode ("Every identity is federation-witnessed … a chain cannot incept
un-federated, and there is no 'witnessing starts from a later `Wit`, early range unwitnessed'
allowance"), with the same statement in `event-shape.md`, `kel/events.md`, `iel/events.md`, and
`MODEL.md`. The sweep confirms this is the doctrine's only "unwitnessed chain" site. Second, the
posture: "degrades to single-source, **flagged**" implies the loss-of-trust decision proceeds with a
flag, while `witnessing.md` §No direct mode states the opposite — "A loss-of-trust decision … that
cannot **multi-source-confirm** (any eclipse or single-source) **refuses**, never proceeds with a
flag." The parenthetical reads like a leftover from a design stage that had a direct (unwitnessed)
mode. Recommend rewriting it to the current posture: multi-source confirmation or refuse — the only
degraded case being a federation outside the consumer's trusted set, which is a trust miss, not a
flagged proceed.

### Group D — Policy, protocols, and features

#### D1. The multi-identity attestation SEL's derivation is specified nowhere — Low

`policy/documents.md` §Multi-identity authorization describes the construct that satisfies a
several-identities policy:

> each authorizing identity issues its **own attestation independently**: each authors its own
> attestation SEL over the document, self-flooring to its own IEL through that SEL's serial-1 `Pin`
> and self-locating by re-deriving its prefix.

"Self-locating by re-deriving its prefix" requires the SEL's inception inputs — its topic and what
its `data` field carries — to be pinned somewhere, and they are not: the sweep finds "attestation
SEL" only in `documents.md`; `tags-and-topics.md` (the topic catalogue) has no attestation topic;
`kinds.md`'s forthcoming-shapes table does not name it; and no feature doc owns it (`credentials.md`
covers only single-issuer issuance, and its multi-issuer machinery is the `issuers` SAD this
construct serves). A verifier cannot re-derive an address whose derivation inputs are unspecified,
so as it stands the described check is not performable from the docs. Smallest fix: catalogue the
attestation topic (and which feature owns the shape) or add it to the forthcoming table with an
owner, so the gap is a declared forward-reference rather than a silent one.

#### D2. A 64-character kind-string cap is asserted only in `sel/events.md` — Low

`sel/events.md` §`Gnt`:

> Its `manifest.grant` names a **grant-value SAD** whose kind sits under `vdti/sel/v1/grants/*` (an
> owner-first namespace, capped at 64 characters **like any event or SAD kind**).

The "like any event or SAD kind" clause asserts a general rule, but `kinds.md` — the canonical kind
catalogue, which states the naming convention and the no-fifth-segment rule — carries no length cap,
and the sweep finds no other site stating one. Either the cap is real and belongs in `kinds.md`
(where every other kind-shape rule lives), or it is not a rule and the parenthetical should drop the
"like any" claim. As written, an implementer reading the catalogue would enforce no cap while one
reading the SEL doc would enforce 64 — a small acceptance divergence of the same class as B1, at
much lower stakes.

## What was attacked and held

A correctness review should also say what it tried to break and could not. The load-bearing
arguments below were each read adversarially — looking for a way the stated conclusion fails — and
held up, including at their edges:

- **The two-hash prefix/SAID derivation and the compact-down canonical form.** The
  substitution-resistance argument (an inception substitution needs two independent hash
  collisions), Rule 2's downward recursion (an expanded child cannot lie about its SAID), the
  ascending-set and exhaustive-schema gates that keep one content to one SAID, and the
  correlation-resistance claim all check out.
- **The custody direct anchor.** The `pin`-as-checked-locator scheme is non-circular, the tip-atomic
  mint argument holds (an intervening append breaks `previous == pin` and the SAD re-mints), and the
  backdate defense reduces correctly to append-only anchoring.
- **The seal machinery.** The seal-cap arithmetic (a seal-sibling's parent sits one below the seal;
  a strictly-below parent lands strictly below), deadness-ascends as the growth-proof closure, the
  `MINIMUM_PAGE_SIZE = 2·MAXIMUM_UNSEALED_RUN + 1` sizing for the fork-and-recover page, and the
  backdate defense (a below-seal sealed straggler is dropped, so the clean seal never retreats to a
  fabricated historical fork) are internally consistent across all three chain types.
- **The live-tip brick argument** (`kel/compromise.md`). The claim that a competing seal at an
  already-sealed position needs the _current signing key_ (the revealed reserve), not the next
  reserve, follows correctly from single-stream pre-rotation — the prior `rotationHash` forces the
  same revealed key, so the rival is signed with the now-current key; the three responses analysis
  (brick / grindable data rule / observer-dependent first-seen) is sound.
- **The Disputed verdict.** The per-branch accepted-sealed-branch count, the dead-on-ascent
  exclusion ("you can't seal a buried chain"), the collusion-proof arithmetic
  (`2·threshold − signers` double-signers), and the one honest-witness exception (cross-federation
  rebinds over disjoint witness sets, proven author-side) fit together with no gap I could find; the
  reconciliation matrices' cell-level checks I ran (seal-sibling positions, the stale-`Trm` pitfall
  in edge case 3, the transfer-matrix guarded cells) were right.
- **The threshold and witness-config bounds.** The federation floor derivation (`signers ≥ 3` +
  exclude-self ⇒ `|roster| ≥ 4`; the `min(|roster| − 2, signers − 1)` cap's joint satisfiability at
  the minimum; the eviction self-attest pool of `|roster| − 2`) and the worked minimum-federation
  example are arithmetically correct and consistent between `iel/events.md`, `witnessing.md`, and
  the doctrine.
- **The `≤ 1` SEL-`Ixn`-per-owner-`Ixn` rule is enforceable.** It is checked by anchor-identity
  dedup at the SEL verifier, which holds both sides of the identity — a real check, not a stated one
  (a specific enforceability class this system's history says to attack).
- **The `issuerPin` earliest-anchor argument** (`documents.md`): a re-anchor cannot move the as-of
  because an anchor earlier than the pinned position would require a hash cycle (the commitment
  embeds the credential's SAID, which embeds `issuerPin`), and later re-anchors are never consulted.
  Sound, and it closes the tier-inversion (un-revoke by re-anchor) it names.
- **The witnessed-time construction** (`witnessing.md`): the threshold-th-smallest receipt timestamp
  is monotone-downward under receipt accumulation, so a curator can only inflate a boundary within
  the honest receipt spread and cannot push a crossing later — the fail-secure direction survives
  the subset-dependence the doc itself flags.
- **ESSR's two bindings and IPEX's freshness gate.** The four-property argument (who can forge
  what), the recipient-key-substitution and strip-and-re-sign defenses, the per-message-key nonce
  safety, and the `grant` envelope's replay analysis (nonce dedup keyed on signer, audience binding,
  cache-retention-matches-acceptance-window) hold; the bearer copy-race is honestly scoped as
  inherent.
- **The honored predicate and its seal-locate** (`shared-documents.md`): the `F_x ≤ V_x ≤ B_x`
  interval check is genuinely intra-chain and clock-free; the doc itself spots and closes the
  cited-grant bypass ("the grant must be sealed, not merely fetched"), and the grant-frontier floor
  (a version cannot predate the grant it cites, by hash-preimage order) is correct.
- **The lane bracket** (`membership.md` / `authored-dag.md` / `exchange.md`): the anchored-root +
  witnessed-bound interval check is a local check needing no fork visibility, the fresh-root and
  two-marker holes are closed at the verifier, and the surviving residual (a dormant current
  member's in-window forward-append) is correctly confined and declared.
- **The residuals catalog is honest.** Spot-checking entries against the mechanism docs found the
  claimed mitigations real and the claimed losses accurate; the catalog's cross-cutting assumptions
  match what the mechanisms actually lean on. (The only mismatch found is the A5 labeling note.)

Two general observations, not findings: the design's strongest habit is that nearly every "is X
still true?" check is either a monotone positive lookup or rides an already-required freshness gate,
so the withholding attack surface is consistently reduced to denial rather than forgery; and the
honest declaration of residuals (including the unreachable-by-construction rows in the SEL matrix
and the "reported unconfirmed" dispute-attribution case) made the adversarial read markedly cheaper
— the places where the design knows it is weak are labeled, and checking them confirmed the labels.

## Closing

The design surface is in strong shape for its stated phase: the interlocking pieces — tiers, seals,
first-seen witnessing, the verdict walk, the negative-check discipline — agree with each other
across seventeen event-log documents and their consumers to a degree that took deliberate effort to
fault. The one High finding (B1) is a genuine must-fix before implementation, since it sits on an
acceptance rule where implementations must agree byte-for-byte; the two Mediums are each a single
passage whose literal reading would mislead an implementer into a fail-open or stale posture the
rest of the design explicitly rejects; the rest is polish. Nothing found undermines a security
argument the system rests on.
