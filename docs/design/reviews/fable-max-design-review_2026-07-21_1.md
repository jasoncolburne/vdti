# Design Review — Fable (max), 2026-07-21, round 1 (cold pass)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_1.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion.

## What this review is

This is a fresh, standalone read of the entire design surface — every document listed in the reading
order of `docs/design/README.md`, read in that order, in its current state on the
`VDTI-30_design-stragglers` branch. The reviewer did not read the earlier review round
(`fable-max-design-review_2026-07-21_0.md`) before or during this pass, so these findings are
independent of it. Where this round re-discovers something the earlier round already found, that
agreement is worth knowing about; where it finds something new, it was not primed to look there.

Two questions drive every finding:

- **Correctness / soundness** — does the mechanism actually deliver the property the document
  claims? Can an attacker, or an unlucky sequence of honest events, produce a state the design says
  cannot happen?
- **Consistency** — do the documents agree with each other? When two documents describe the same
  rule, do they describe the same rule?

Each finding says where it lives, what the problem is in plain language, why it matters, and how
severe it seems. Severity uses three levels:

- **[HIGH]** — a hole in a security argument, or two documents that contradict each other on a rule
  a verifier must enforce. Someone implementing from these documents would build something wrong or
  exploitable.
- **[MEDIUM]** — the design is probably right but the documents underdetermine it: a gap, an
  ambiguity, or a claim asserted without the argument that would let a reader check it.
- **[LOW]** — small inconsistencies, stale cross-references, and readability hazards that could
  mislead but probably would not survive into an implementation.

The review is organized by layer, following the reading order. A final section collects observations
that cut across layers.

**Status: complete.** All forty-one documents in the reading order were read in full, in order.

## Findings at a glance

One high-severity finding, six medium, twelve low. Sorted by severity, then by where they live:

| #   | Sev    | One-line summary                                                                                                                                |
| --- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.1 | HIGH   | Two incompatible semantics for a recovery seal that siblings accepted content — the reconciliation matrices contain both (all three primitives) |
| 2.2 | MEDIUM | Member-participation construction reads circular at the doctrine layer (resolved by 3.4's owner doc)                                            |
| 3.2 | MEDIUM | Reconciliation invariant 5 contradicts the seal-cap formula it restates                                                                         |
| 3.4 | MEDIUM | `pins` described as a hash cycle in both catalogues; the owning doc has the non-circular rule                                                   |
| 3.7 | MEDIUM | "Severance downgrades a Disputed" stated as operative in two SEL docs; the proof marks it unreachable                                           |
| 4.1 | MEDIUM | A witnessed event committing its sub-threshold ancestry is relied on twice, stated nowhere                                                      |
| 4.2 | MEDIUM | Genesis threshold: "all founders consent" versus "`t_govern` of the founders"                                                                   |
| 0.1 | LOW    | Threshold-vector gloss swaps authorization and governance (`system-thesis.md`)                                                                  |
| 0.2 | LOW    | "`prefix ≠ said`" stated as certainty rather than collision-resistance                                                                          |
| 1.1 | LOW    | `said` is a reserved key at every nesting level — app-payload consequence unstated                                                              |
| 1.2 | LOW    | Threshold-vector gloss swap, second occurrence (`shapes.md`)                                                                                    |
| 1.3 | LOW    | Witness-receipt shape mixes two field-naming conventions                                                                                        |
| 1.4 | LOW    | TTL lacks the "operational, not cryptographic" caveat one-shot carries                                                                          |
| 2.3 | LOW    | "Requiring at least two signers" reads structural but is operator guidance                                                                      |
| 2.4 | LOW    | "Past the fork" never defined as inclusive of the fork position                                                                                 |
| 3.3 | LOW    | `anchors` called "ordered" against the sorted-set canonicalization rule                                                                         |
| 3.5 | LOW    | Several `{X, X} → terminal` sentences drop the "accepted" qualifier                                                                             |
| 3.6 | LOW    | The "independent authorings dedupe" example cannot hold for events carrying `pins`                                                              |
| 3.8 | LOW    | "≤ 1 content event per anchoring event" rule has no stated enforcement point                                                                    |
| 3.9 | LOW    | The SEL repeats 3.5/3.6's slips in its seal-advance-cap section                                                                                 |
| 7.1 | LOW    | Chat's open-epoch case escapes the future-dating bound the text claims closed                                                                   |

(2.2 is kept in the table for traceability; reading the primitive suites resolved it into 3.4.)

## Reading log

- [x] `README.md`, `docs/design/README.md`
- [x] Layer 0 — orientation: `system-thesis.md`, `glossary.md`
- [x] Layer 1 — data substrate: `sad.md`, `said.md`, `custody.md`, `availability.md`,
      `compaction.md` + catalogues (`kinds.md`, `shapes.md`, `tags-and-topics.md`, `topics.md`)
- [x] Layer 2 — doctrine: `protocol-doctrine.md`, `residuals.md`, `monitoring.md`
- [x] Layer 3 — event shape + KEL: `event-shape.md`, `kel/log.md`, `kel/events.md`,
      `kel/verification.md`, `kel/merge.md`, `kel/compromise.md`, `kel/reconciliation.md`
- [x] Layer 3 — IEL: `iel/log.md`, `iel/events.md`, `iel/verification.md`, `iel/merge.md`,
      `iel/reconciliation.md`, `iel/delegation.md`
- [x] Layer 3 — SEL: `sel/log.md`, `sel/events.md`, `sel/verification.md`, `sel/merge.md`,
      `sel/reconciliation.md`
- [x] Layer 4 — federation: `bootstrap.md`, `witnessing.md`, `topics.md`, `mesh-transport.md`
- [x] Layer 5 — policy: `policy.md`, `documents.md`, `evaluation.md`
- [x] Layer 6 — protocol primitives: `essr.md`, `ipex.md`, `receive-key-directory.md`,
      `group-key.md`, `membership.md`, `authored-dag.md`
- [x] Layer 7 — features: `credentials.md`, `exchange.md`, `shared-documents.md`

## Findings

### Layer 0 — Orientation (`system-thesis.md`, `glossary.md`)

The thesis is coherent and the glossary is genuinely consistent with it — the four chain states, the
two tiers, the witnessed-versus-accepted distinction, and the divergence decision tree all agree
between the two documents. Two items:

**0.1 [LOW] The threshold vector's plain-language gloss swaps two of its three parts.**
`system-thesis.md` (§What VDTI provides, IEL bullet) writes the vector as
`{ use, authorize, govern }` and then glosses it as "how many member devices must act for content,
governance, and authorization respectively." Read literally, "respectively" maps `authorize` to
governance and `govern` to authorization — backwards. The correct order for that sentence is
"content, authorization, and governance." This matters more than a typo normally would, because
wiring the `authorize` count to governance acts (or vice versa) is exactly the kind of mistake an
implementor could copy out of the orientation document. The same swap appears again in `shapes.md`
(see finding 1.2), which suggests it was copied once and propagated.

**0.2 [LOW] "The two hashes see different canonical bytes, so `prefix ≠ said`" is stated as a
certainty; it is an overwhelming probability.** (`said.md` §Derivation, echoed in
`system-thesis.md`'s framing of correlation resistance.) Two different inputs to a hash can in
principle produce the same output; what the design actually relies on — and delivers — is that
neither value is computable from the other and that the inception's event hash does not double as
the chain's lookup key. Harmless as written, but a document this careful elsewhere about
probabilistic-versus-structural distinctions (for example, the effective-SAID synthetic being
distinguishable "structurally, never by hash inequality") may want the same precision here.

### Layer 1 — Data substrate (`sad.md`, `said.md`, `custody.md`, `availability.md`,

`compaction.md`, catalogues)

This layer is in very good shape. The two-rule canonical-form story (nested content is always hashed
in its by-reference form; anything embedded inline must be verified before it is folded down) is
stated, motivated, and closed against the obvious attack (an embedded child lying about its own
hash). The custody anchor design — the locator points at the event _before_ the anchoring event,
avoiding a circular hash dependency — is internally consistent everywhere it appears (custody,
credentials, shapes). The sorted-and-distinct rule for set-valued lists is applied consistently
(custody `readers`, the constitution's reader union). Findings:

**1.1 [MEDIUM] The recognition rule reserves the field name `said` at every nesting level, but the
consequence for application payloads is stated only implicitly.** `said.md` §Canonical form says a
nested object is a sub-SAD exactly when it carries a `said` field, and that the field "is reserved
at every nesting level." The unstated consequence: any application that embeds arbitrary JSON in a
payload field whose objects happen to contain a `said` key will have those objects treated as
sub-SADs — and since they will not verify as SADs, the parent becomes permanently unverifiable.
Nothing in `sad.md`, `shapes.md`, or the application-facing feature docs warns app builders that
`said` is a forbidden key name in their own nested data. Worth one explicit sentence at the point
where applications learn to build payloads (and ideally a structural rule: app-defined opaque
content rides in `bytes`/blob form or under a schema the kind names, never as free-form JSON).

**1.2 [LOW] The threshold-vector gloss swap, second occurrence.** `shapes.md` §Roster delta writes
the vector `{ use, authorize, govern }` with the gloss "content (tier 1), governance, authorization
(tier 2)." Same swap as finding 0.1: in vector order the gloss should read "content (tier 1),
authorization, governance (both tier 2)." The parenthetical "(tier 2)" is also ambiguous about
whether it covers only the third entry or the last two.

**1.3 [LOW] The witness-receipt shape mixes two field-naming conventions.** `shapes.md` §Witness
receipts uses `chain_prefix`, `event_said`, `event_serial`, `witness_prefix` (underscore style)
alongside `federationPin` (camel style) in the same table — and every other SAD shape in the
catalogue uses camel style (`payloadDigest`, `senderPin`, `receiveKey`, `nodeHints`). Field names
are hashed: the receipt's SAID depends on the exact spelling, so the catalogue should commit to one
convention before anything is encoded. If the underscore names are deliberate (imported from an
existing implementation), a one-line note saying so would stop every future reader from flagging it.

**1.4 [LOW] "Enforcement is at the storage boundary" for TTL and one-shot is slightly at odds with
the trust model, and the tension is acknowledged only for one-shot.** `availability.md` correctly
says one-shot deletion is "operational, not cryptographic." The same caveat applies to TTL
(retention is a promise by the store operator, not a verifiable property — an adversarial replica
can retain expired bytes forever, and an honest one can lose bytes early), but the TTL bullet does
not say so. The residuals catalogue does state both honestly ("One-shot isn't deletion," "Referenced
content expires or is withheld"), so this is purely a primitive-doc gap: the doc an app builder
reads first should carry the same one-line caveat per sub-axis.

### Layer 2 — Cross-cutting doctrine (`protocol-doctrine.md`, `residuals.md`, `monitoring.md`)

The doctrine is the strongest document in the set. The two-tier model, the seal bound, the
divergence rules, the three distinct ways a dispute can form (same-position witness collusion; a
content-led branch that seals, meeting a seal that cannot drop it; two rebinds naming different
federations), the backdate defense (a late sealed event below the seal is dropped, never honored),
and the retention bound all connect, and the same rules reappear correctly in the thesis and the
glossary. The residuals catalogue is unusually honest, and its arithmetic is sound — I recomputed
every Severity × Exploitability product in both ranked tables and every one lands in the band the
table claims. Findings:

**2.1 [HIGH] Three passages disagree about what happens when the recovery seal lands as a sibling at
the contested position — one event or two?** The scenario: an attacker's content event at serial `d`
is accepted (witnessed at threshold), and the owner recovers by authoring a seal-advancing event
whose parent is the shared ancestor at `d−1` — so the recovery seal sits _at_ serial `d`, as a
sibling of the accepted content event.

- §Divergence and recovery says one event suffices: "You attach a burying seal-advancer at your last
  good event … **retaining** that branch and burying every competing **content** branch below the
  new seal," and explicitly contemplates the attach point being the divergence ancestor (placing the
  seal at the contested serial).
- §Federation convergence (kind-scoped witnessing) likewise: "On a content-only divergence the first
  sealed sibling at the position is exactly the **single resolving burying seal-advancer**."
- But the cross-node-races paragraph says the opposite: "a seal-advancing event that is **itself one
  of the competing siblings at `d` never becomes the tracked seal** … so the tracked seal stays
  below `d` and the fork is live," and "a mixed `{Rot, Ixn}` recovers **by extending the `Rot`**" —
  i.e., a further clean seal above the fork is needed before the loser is buried and the chain reads
  Active again. The Terminology section's lock definition ("the most recent seal-advancing event
  that landed **cleanly** on the linear chain") supports this reading, since a sibling-position seal
  did not land cleanly.

There is a reading that reconciles them: a sealed event at a contested serial becomes the tracked
seal when every competing sibling there is _below threshold_ (the stalled-race case — the seal is
then the only accepted event at that serial), but stays a live fork branch when it siblings an
_accepted_ event (the witness-compromise case), and then one more clean seal above completes the
recovery. If that is the intended rule, no passage states it as the discriminator, and the recovery
narrative reads as if one event always suffices. Both candidate semantics converge
deterministically, so this is not a divergence-of-nodes bug — but an implementor of the merge layer
and an implementor of the state walk could pick different answers and disagree about whether a chain
reads Forked or Active after a one-event recovery, which is exactly the kind of rule the verifier
must get bit-identical. The KEL merge/reconciliation documents own this; this finding is re-checked
against them below (see finding 3.x follow-up in the KEL section).

**2.2 [MEDIUM] The member-participation construction is stated in both directions but the
non-circular ordering is never shown at the doctrine layer.** §Pin everything to current says a
member participates in an identity-log event "by authoring a fresh KEL event at its own current tip
**that commits to that specific IEL event**," while the identity event's manifest carries `pins` —
"the participating member KEL event SAIDs." Read naively, the member's KEL event commits to the
identity event (by its hash) and the identity event commits to the member KEL events (by their
hashes) — which is circular and cannot both be by-SAID. The custody design solved exactly this shape
with the anchor-locator trick (point at the predecessor), so presumably the event-log layer has an
equivalent resolution (for example: member KEL events commit to a deterministic proposal digest of
the identity event's content minus `pins`, and the identity event then pins the KEL events).
Wherever the resolution lives, the doctrine's one-sentence summary should not imply mutual by-hash
commitment. (Checked against `event-shape.md` below — see the Layer 3 section for what the actual
construction turned out to be.)

**2.3 [LOW] "Requiring at least two signers for content means a single compromised device can't
author alone" reads like a structural rule but is operator guidance.** (`residuals.md`, signing-key
content-forgery entry.) The doctrine explicitly allows `t_use = 1` at any roster size. The sentence
is true only for deployments that choose `t_use ≥ 2`; one qualifying word ("Requiring at least two
signers — where configured — …") would stop it reading as a floor the protocol enforces.

**2.4 [LOW] "Past the fork" is used throughout but never defined as inclusive of the fork
position.** The Disputed rule counts "accepted sealed branches **past the fork**," and every worked
example (two sealed siblings at one serial, the mixed pair at the fork serial) counts a branch whose
seal sits _at_ the fork serial. So "past" must mean "at or after," and the exclusive reading would
make the rules incoherent — but nothing says so, and "past" naturally reads as "strictly after." One
parenthetical at first use ("past the fork — at or after the divergent serial") would remove the
trap.

### Layer 3a — Event shape and the KEL (`event-shape.md`, `kel/*`)

The KEL suite is thorough: the two-tier capability story is stated identically in five places, the
"spent reserve" boundary case (the just-revealed reserve _is_ the current signing key, so a
same-position rival seal needs the live signing key plus witness collusion) is worked consistently
in `events.md`, `log.md`, `compromise.md`, and the residuals catalogue, and the page arithmetic
(`129 = 2·64 + 1`) checks out once you notice the anchoring seal rides the _previous_ page. The
tier-rank resolution for a terminate racing content is stated the same way everywhere it appears.
One finding here is severe, and it subsumes finding 2.1:

**3.1 [HIGH] The documents assert two incompatible semantics for a recovery seal that lands as a
sibling of accepted content, and the reconciliation matrix — the designated correctness proof —
contains both.** This is finding 2.1 run to ground. The scenario: events `X` (content) and `S`
(seal-advancing, e.g. a rotation) share the same parent, so both sit at serial `d`; assume both end
up accepted (witnessed at threshold — exactly what the witness ladder permits: one content and one
sealed sibling per position). The question: once a node holds both, is the chain **Active** (the
seal advanced to `d` and buried the content sibling — recovery took one event) or **Forked** (a seal
that is itself a competing sibling never becomes the tracked seal, so the fork is live until a
further clean seal extends the sealed branch — recovery takes two events)?

**Model I — "the sibling seal buries" — is asserted by:**

- `kel/merge.md` §Recovery attach shapes, ancestor-extending shape: the recovery `Rot` whose parent
  is the divergence ancestor "lands at `v_d` … the `Rot` is the **only canonical event at `v_d`**
  after recovery"; post-state "linear, recovered."
- `kel/merge.md` §Routing by chain state, Forked-chain bullet: a burying seal-advancer in "either
  attach shape" (tip-extending _or_ ancestor-extending) "advances the seal … and the chain re-reads
  Active → outcome `Recovered`."
- `kel/reconciliation.md` Matrix 1, Position 3: a `Rot`/`Wit` landing against content on the
  post-seal run → "`Recovered` — the seal-advancer buries the run past its attach point below its
  new seal."
- `protocol-doctrine.md` §Divergence and recovery: "You attach a burying seal-advancer at your last
  good event … burying every competing content branch below the new seal," with the attach point
  explicitly allowed to be the divergence ancestor — one event, no follow-up mentioned.
- `protocol-doctrine.md` §Federation convergence: "On a content-only divergence the first sealed
  sibling at the position is exactly the **single resolving burying seal-advancer**."
- The terminate carve-out is Model I in spirit: a `{Trm, content}` race at one serial resolves
  immediately by tier-rank with no burying event — same-serial seal-over-content resolution is
  already in the design for `Trm`.

**Model II — "the sibling seal leaves the fork live" — is asserted by:**

- `protocol-doctrine.md` §Divergence and recovery, cross-node-races paragraph: "a seal-advancing
  event that is **itself one of the competing siblings at `d` never becomes the tracked seal** … so
  the tracked seal stays below `d` and the fork is live … a mixed `{Rot, Ixn}` recovers **by
  extending the `Rot`**."
- `kel/log.md` and `kel/verification.md`, the tracked-seal definition: "the most recent
  [seal-advancing event] to land **cleanly** (**not a competing sibling**)."
- `kel/reconciliation.md` Matrix 1, Position 2: an `Ixn` arriving adjacent to the established seal →
  "`Forked` — the sealed seal + one content sibling, a mixed race (one sealed)."
- `kel/merge.md` §Routing by chain state, Overlap bullet: "if the batch contains a sealed event …
  with `previous = v_{d-1}.said` → **not admitted as a canonical extension; the chain moves to
  Forked** (the fork's first sealed branch)."

**Why this is not a pedantic difference.** The two models give different answers to "what state is
this chain in" for the same held events, and the design's own convergence requirement ("identical
event sets yield identical state — arrival order does not enter", `protocol-doctrine.md` §Federation
convergence) makes that a correctness property, not a style choice. Concretely, Matrix 1's Positions
2 and 3 are the _same final event set_ reached in the two arrival orders: content-then-seal lands in
Position 3 (`Recovered` → Active), seal-then-content lands in Position 2 (`Forked`). Two honest
nodes that received the two events in different orders follow different cells of the correctness
matrix and permanently disagree — one grounds trust (an Active reading), the other refuses (a Forked
reading). The matrix whose stated purpose is proving arrival-order independence contains the
counterexample as two adjacent rows.

Each model is _internally_ coherent, so the fix is to pick one and sweep the other's statements:

- Under Model I, the tracked-seal rule becomes "a seal-advancing event with no **accepted sealed**
  sibling at its serial is clean; content siblings at the seal's serial are buried (their parent
  sits below the advanced seal)." Matrix 1 Position 2's `Ixn` row becomes buried/inert (not
  `Forked`), the cross-node-races paragraph loses the "never becomes the tracked seal" claim for the
  mixed case, and recovery is genuinely one event — matching the recovery doctrine,
  `compromise.md`'s "one recovery `Rot` buries the whole current fork," and the residuals table.
- Under Model II, `merge.md`'s ancestor-extending shape and Matrix 1 Position 3 must say the chain
  reads Forked (the resolving seal is a live sibling) until one further clean seal lands, and every
  "single resolving seal-advancer" claim gains a second step.

A tie-breaking consideration the docs already contain: under Model II, an adversary holding a
_retired_ signing key can mint a late content sibling at the last seal's serial (its signature
verifies against the pre-rotation key state, and the witness ladder's content rung at that position
may be unclaimed); if accepted, that flips the chain's reading from Active to Forked — a cheap
standing denial against any chain, since consumers refuse on Forked. Model I closes this
automatically (such a sibling is dead by parent-below-seal). That, plus the `Trm` tier-rank
precedent, suggests Model I is the intent and the Model II statements are leftovers of an earlier
design state — but that is the author's call to make, explicitly, in one place.

**3.2 [MEDIUM] Invariant 5's wording contradicts the seal-cap formula it restates.**
(`kel/reconciliation.md` §Invariants.) The seal-cap is "a new event's **parent** must sit
at-or-after the seal (`parent_serial ≥ seal_serial`)". A sibling at the seal's own serial has parent
serial `seal_serial − 1`, which fails that formula — yet invariant 5 says such a sibling "is **not
in the locked portion at all**: it forms a live fork … the cap bounds content extended **from** the
seal, not a sibling to it." The intended rule (visible from `merge.md` rule 2's carve-out) is that
cap failures split into inert (strictly-below parents) versus fork-forming (parent exactly one below
the seal — a seal-sibling); but as written, the invariant asserts the sibling passes a test its own
formula fails. State the cap as two explicit cases, or change the formula. (Which outcome the
fork-forming case then produces is finding 3.1's question.)

**3.3 [LOW] "The `anchors` role is a flat, ordered list" versus the set-canonicalization rule.**
`kel/events.md` §Anchors calls the list "flat, ordered"; `said.md` requires any order-independent
list to be carried strictly ascending, and an anchors list looks order-independent (a batch of
commitments). If anchors order is genuinely meaningful (it does not appear to be), say what it
means; if not, the list should be declared strictly-ascending like `readers`, or two honest
producers batching the same anchors can mint two different events for the same logical act — which
then _collide_ at one serial as a spurious content fork instead of deduplicating.

### Layer 3b — The IEL (`iel/*`)

The IEL suite is strong. The facet dispatch for the two-faced `Wit` (user rebind versus federation
governance) is airtight — established before any `Wit` payload is read, on every path, with the
rationale (the directly-consumed governance roles have no downstream type-check) stated where the
rule is. The atomic `cut`-eviction argument (a separate evict event would let the still-rostered
member race a re-fork) is sound. The threshold-slot mapping (`t_use` → content, `t_authorize` →
authorize/deauthorize, `t_govern` → roster/revoke/rebind/terminate) is stated identically in the
doctrine, the glossary, `event-shape.md`, and `iel/events.md` — which confirms findings 0.1 and 1.2
are one-off gloss errors, not ambiguity about the model. The delegation surface's "re-verified
pointer" posture (the discoverability link is tier 1, but the verifier re-checks the tier-2 grant it
points at) is exactly the enforceability discipline the design preaches. Findings:

**3.4 [MEDIUM] The `pins` field is described in the two catalogues in words that read as a hash
cycle; the owning document has the correct, non-circular construction.** This resolves finding 2.2.
`iel/log.md` §Down-pins is explicit and correct: `pins` records each participating member's
**prior** KEL tip (`participation.previous`) — the fresh anchoring KEL event sits one past it — "so
the IEL event's `said` never depends on the anchoring events, and there is no SAID cycle." But
`event-shape.md` (§Cross-cutting fields) describes `pins` as "a SAD listing the participating member
**KEL event SAIDs**," and `shapes.md` (§`vdti/event/v1/roles/pins`) as "each participating member's
KEL event SAID" — both naturally read as the SAIDs of the participation events themselves, which is
the circular construction (the KEL participation's `anchors` contains the IEL event's SAID, which
would then contain the participation's SAID). An implementor working from the catalogues would build
something impossible and only discover why in `iel/log.md`. Both catalogue entries should say "prior
KEL tip" the way the owner does.

**3.5 [LOW] Several sealed-versus-sealed statements drop the "accepted" qualifier that the rest of
the design is careful about.** The rule everywhere else: two sealed siblings at one position are
Disputed only when both are _accepted_ (witnessed at threshold — collusion); an honest race
first-seen-declines the second, which stalls and re-issues. But: `iel/log.md` §Seal-advance cap and
`iel/events.md` §Seal-advance cap ("a re-seal `Evl` versus a real `Evl` at one position diverges as
`{Evl, Evl}` → terminal"), `iel/events.md` §`Rev`/`Dth` ("Distinct kills at one position are
`{Rev, Rev}` → ≥ 2 sealed → terminal"), the `Wit` taxonomy row ("`{Wit, Wit}` terminal"),
`iel/merge.md` §The seal-cap and the roster-less re-seal, and `iel/reconciliation.md` §The sealed
sub-split all state the unqualified form. Read alone, each says an honest concurrent pair bricks the
identity — the exact misreading the doctrine works hard to prevent ("not an honest partition"). Each
needs the word "accepted" (or a pointer to the first-seen decline).

**3.6 [LOW] The "two independent authorings that commit the same bytes" dedupe example does not hold
for the event it names.** `protocol-doctrine.md` §Divergence and recovery offers the roster-less
re-seal `Evl` as an example of two independent authorings producing byte-identical events ("same
intent, no `nonce`"), and `iel/log.md` echoes it ("A busy issuer's re-seal `Evl` at one position is
exactly this idempotent case"). But every IEL event carries `pins` — the participating members'
prior KEL tips — and two independent re-seal ceremonies consume different fresh KEL participations,
so their `pins` differ and the events are byte-distinct: they collide (and the second is
first-seen-declined), they do not dedupe. The dedupe genuinely covers only the same ceremony's bytes
resubmitted (gossip redelivery, retry) — which is the case the merge layer actually needs. The
"independent authorings" framing should be cut or re-scoped, or a reader will expect a convergence
the data model does not provide.

### Layer 3c — The SEL (`sel/*`)

The SEL's two-axis model (its own witnessed divergence, crossed with deadness inherited from the
owner identity log) is well built. The "why the neutral re-seal exists" argument — the owner log is
structurally blind to a SEL fork, so the SEL must both witness itself and carry its own recovery
event — is one of the best-motivated pieces in the design surface, and the `content: true` ⟺
tier-1-v1 biconditional plus the whole-content prefix genuinely closes the content-squat-at-a-
lookup-address attack by construction. The lineage walk's fail-secure postures (gap ends the walk;
past the cap reads no-live-instance; Forked stops rather than advancing) are consistent. Findings:

**3.7 [MEDIUM] Two SEL documents state "severance downgrades a Disputed" as an operative rule; the
SEL correctness proof declares the case unreachable and denies the downgrade.** `sel/log.md`
(§Severance) and `sel/merge.md` (§Severance) both say: "A Disputed is downgraded by severance: if
one of two accepted sealed branches is severed, it is un-verifiable and not counted, so the reading
drops to the live branch and recovers." But `sel/reconciliation.md` (§The two axes, and Matrix 2's
"≥ 2 sealed branches, one anchor dead" row) argues the precondition can never hold: "a **Disputed**
SEL cannot be downgraded this way: its two sealed branches are accepted, and SEL acceptance gates on
the owner-IEL anchor being accepted, so their (IEL sealed) anchors are … never buried — no severance
reaches an accepted sealed branch," and marks the row "unreachable by construction." The
unreachability argument looks right (a SEL sealed event's anchor is an IEL _sealed_ event, which is
never buriable), so the operative-rule sentences in `log.md` and `merge.md` describe a transition
that cannot occur — and a reader of those two documents will believe a Disputed SEL has a severance
escape hatch the proof says it does not have. One related loose end: the doctrine's cross-chain
anchor-satisfaction rule says a tier-2 anchor _does_ drop when its host identity log becomes
**Disputed** (not buried) at-or-beyond the divergent serial — a third deadness mechanism the SEL
severance model (which recognizes only burial) never mentions. Since a disputed owner identity
forces the SEL into the reincept cascade anyway, the outcome is probably unaffected, but the three
documents should tell one story.

**3.8 [LOW] The "at most one content event per SEL per anchoring identity event" rule has no stated
enforcement point.** `sel/events.md` (`Ixn` row) and `event-shape.md` (SEL taxonomy) both state "≤ 1
per SEL per owner-IEL `Ixn` (counting content)," but neither `sel/verification.md`'s per-event
checks and summary table nor `sel/merge.md`'s routing rules contain a check that two SEL content
events resolving to the _same_ anchoring identity event is a violation. (The nearby "re-anchor at an
already-attributed SEL serial is inert" guard is a different rule — it bounds two anchors naming one
SEL position, not one anchor naming two SEL positions.) The rule is checkable — the SEL verifier
resolves every event's anchor and could dedupe on anchor identity — but as written it is a stated
constraint with no enforcing pass, which is exactly the "is the check performable, and who performs
it" gap this design is otherwise disciplined about. If the rule is load-bearing, name its
enforcement point; if it is advisory batching guidance, say so.

**3.9 [LOW] The seal-advance-cap "dedupe" sentence repeats on the SEL with the same two problems.**
`sel/events.md` §Seal-advance cap: "Two identical re-seals at one position dedupe (idempotent),
while a `Sea` versus a real seal-advancer at one position is two sealed branches → Disputed" —
missing the "accepted" qualifier (finding 3.5's class), and the byte-identical claim again holds
only for one ceremony's bytes redelivered, since independent `Sea` authorings carry different `pin`s
and anchoring events (finding 3.6's class).

**3.1 (addendum) The one-event-versus-two recovery contradiction replicates into the IEL
documents.** `iel/merge.md`'s fork-detect rule routes a sealing event extending the divergence
ancestor to "Forked (the fork's first sealed branch) or Disputed (its second)" — never Recovered —
while the same document's §Branch-scoped verification names "`v_{d-1}` in the ancestor-extending
shape" as a legitimate burying-`Evl` seed, and `iel/reconciliation.md` Matrix 1 reproduces the KEL's
Position 2 (content sibling of the seal → `Forked`) / Position 3 (seal against content →
`Recovered`) pair — the same final event set with two different outcomes by arrival order. Whichever
semantics is chosen for 3.1 must be swept through the IEL (and, presumably, SEL) mirrors in the same
pass. (Confirmed on reading the SEL: `sel/reconciliation.md` Matrix 1 reproduces the same Position 2
/ Position 3 pair, and `sel/merge.md`'s fork-detect routes an ancestor-attached seal-advancer to
Forked/Disputed only — so all three primitives need the sweep.)

### Layer 4 — Federation and witnessing (`bootstrap.md`, `witnessing.md`, `topics.md`,

`mesh-transport.md`)

This layer holds up well under pressure. I probed the quorum-overlap argument for the case of two
competing siblings carrying _different_ federation pins (which would select different witness sets
and defeat the overlap): the design already closes it — the currency gate forces both siblings' pins
to name the current roster membership, and selection runs over membership, so same membership means
same selected set; the one deliberate exception (a rebind declares its own pin, so two rebinds to
different federations select disjoint sets) is correctly surfaced as the honest-witness dispute case
everywhere it matters. The witnessed-time construction (the threshold-th smallest receipt time)
comes with an honest analysis of what a receipt-curating adversary can and cannot move. The genesis
non-circularity argument (authorization is ordinary member anchoring; trust is the configured
prefix; the `Fcp` marker is interpretation, not vouching) is one of the clearest pieces of security
writing in the repo, and the mesh transport's nonce-by-construction design is right. Findings:

**4.1 [MEDIUM] A witnessed event's power to commit its sub-threshold ancestry is used twice but
never stated — and it superficially contradicts the acceptance rule.** `kel/verification.md`
(§Acceptance requires threshold) says "no node — witness or not — treats a sub-threshold event as
accepted," and the merge docs say a sub-threshold submission is "not counted toward a verdict" and
never advances the tip. But two recovery paths depend on a witnessed event _carrying_ sub-threshold
ancestors into the canonical chain: the stale-pin recovery ("peers defer the un-witnessed events,
then fetch them once the witnessed re-pin commits them as `previous`", `witnessing.md`
§As-of-context) and the split-stall exit ("if it attaches at the author's own stalled sibling it
**retains** that content — the witnessed seal commits it as canonical", `witnessing.md` §First-seen
and `protocol-doctrine.md` §Federation convergence). In both, a threshold-witnessed event's
`previous` chain includes events that never individually reached threshold, and they become
canonical _by ancestry_. That is a coherent rule — acceptance gates the tip, and an accepted event
transitively commits its ancestry — but it is nowhere stated as a rule, and a careful implementor of
the "pure function of accepted state" walk would exclude those ancestors and be unable to reach the
accepted tip at all. State the ancestry-commitment principle once (and reconcile the "never counted"
phrasing with it).

**4.2 [MEDIUM] The genesis authorization threshold: "all founders consent" versus "a `t_govern`
threshold of the founders."** `iel/events.md`'s taxonomy gives the federation `Fcp` count as "all
founders consent" (and the user `Icp` as "all initial members consent"), and `iel/verification.md`'s
facet table repeats "anchored by all initial members' KEL `Rot`s." But `bootstrap.md` §Verifying the
genesis bundle requires only "a **`t_govern` threshold** of the founders' `Rot`s anchor the
federation `Fcp`" and calls a genesis "below `t_govern`" sub-threshold — implying a genesis with
`t_govern`-many of the founders (not all) verifies. These are different validity rules: under the
bootstrap reading, a founder can appear in a federation roster it never anchored (conscription at
genesis — exactly what the all-members rule prevents for user identities); under the taxonomy
reading, one unreachable founder blocks genesis entirely. Pick one and state it in both places (if
the answer differs between user `Icp` and federation `Fcp`, say that explicitly — right now each
document generalizes its own answer).

### Layer 5 — Policy (`policy.md`, `documents.md`, `evaluation.md`)

No findings. This layer is the cleanest in the surface, and two pieces deserve explicit credit as
_correct_, since both are places a design like this usually goes wrong. First, the composition rules
confront the double-counting problem honestly: crediting a signer to at most one satisfied branch
makes threshold satisfaction an existential assignment search (a set-packing check), and the
document says so, names the failure mode of the naive greedy pass (wrongly denying a satisfiable
policy, order-dependent disagreement between evaluators), and bounds the search under the work
budget with deny-on-exceed. Second, `documents.md`'s tier-inversion closure is a genuinely sound
argument: the credential's committed locator names the _earliest possible_ anchoring position
because any earlier anchor would need a hash cycle (the commitment embeds the credential's hash,
which embeds the locator), so a later re-anchor landing after a revocation can never be consulted
and cannot silently un-revoke. The as-issued/current-trust split (a below-seal anchor is valid
forever; _new_ trust additionally needs a fresh, undiverged tip) is stated identically here, in the
credentials feature, and in the verification doctrine.

### Layer 6 — Protocol primitives (`essr.md`, `ipex.md`, `receive-key-directory.md`,

`group-key.md`, `membership.md`, `authored-dag.md`)

No findings of substance — and this layer resolves a class of concern I was carrying from earlier
layers. I had been tracking whether "stated check" and "performable check" ever come apart (the
design's own discipline); the membership walk is the strongest counter-example in the good
direction: the fail-secure store-side check works because the requester _discloses its own blinded
commitment's preimage_ in the live-signed request, and the store additionally checks the disclosed
identity matches the request's signer — so a leaked preimage is not a bearer token, and the walk the
default posture depends on is actually runnable by the party that must run it. The prior-art
crediting in ESSR (An 2001) and IPEX (Smith/Feairheller) is specific and accurate about what was
adopted versus adapted. The signature-context question I probed at Layer 1 (could a signature over
one hash be replayed in another context?) closes cleanly: every signed subject is a kinded SAD whose
`kind` is inside the hashed bytes, so cross-context replay would need a hash collision across kinds.
One observation, not a defect: the authored-DAG's "two roots are not self-proving" insight — and the
resulting rule that lane roots must be _anchored_ by the governing grant chain, with two anchored
markers in one period reading fail-secure (honor neither) — is the kind of closure that suggests the
fresh-root attack was actually run against the design.

### Layer 7 — Features (`credentials.md`, `exchange.md`, `shared-documents.md`)

The features compose the primitives without inventing new chain machinery, as claimed; the
acceptance gates are fail-secure conjunctions; the residuals sections match the central catalogue
(bearer copy-race, terminated-issuer freeze, communication-graph-at-home-nodes, single-device chat
signature). The shared-documents honored predicate — three positions on the editor's own append-only
chain, with the seal-locate warning ("skip the seal-locate and the gate is a total bypass — so it is
stated here") and the one-time disjointness pass — is carefully built, and its floor argument (a
version cannot predate its own grant because the anchor commitment embeds the version hash, which
embeds the grant reference) is sound. One finding:

**7.1 [LOW] Chat's justification for dropping mail's future-dating bound does not cover the open
epoch.** `exchange.md` §The session mode says a chat message needs no `timestamp ≤ now + band` check
"because the witnessed epoch anchors the time … a future-dated stamp beyond the epoch window reads
outside it and is refused." That holds for a _closed_ epoch (both boundaries witnessed), but the
_current_ epoch's window has no upper boundary yet, so a writer can stamp a message arbitrarily far
in the future while its epoch is open and nothing refuses it. The damage is small and mostly
self-inflicted — monotonicity then forces the writer's own later messages to carry stamps at least
that large (or fork its own lane), and other lanes are unaffected — but it also means the message's
validity is not monotone: it reads acceptable while the epoch is open and falls outside the window
retroactively when the next epoch's witnessed time lands below its stamp. Either add mail's
two-sided bound for open-epoch messages or state the open-epoch case as an accepted (self-harming)
residual; right now the text claims a closure the mechanism only provides once the epoch closes.

## Cross-cutting observations

**What the surface gets right, structurally.** Reading all forty-one documents in one pass, the
things that impressed me are mostly _invisible_ properties — places where the same rule appears in
five documents and is the same rule all five times:

- The two-tier capability model, the kind-strict anchor matrix, and the threshold-slot mapping are
  stated identically everywhere they appear (doctrine, glossary, event-shape, all three primitive
  suites, both features that consume them). The only mismatches are the two prose glosses in
  findings 0.1/1.2.
- The predecessor-locator convention (point at the event _before_ the anchoring event, so the hash
  graph stays acyclic) is used five separate times — custody's `pin`, the credential's `issuerPin`,
  the identity log's `pins`, the SEL down-pin, the kill locator — and is the same trick each time.
  Finding 3.4 is about the catalogues describing it wrong, not about the construction.
- Fail-secure defaults are genuinely uniform: every "can't confirm" path I traced (truncated walks,
  withheld gated documents, unresolvable replica sets, missing timestamps, unrecognized policy
  constructs, absent lineages, sub-threshold genesis) reads refuse/deny/don't-honor, with fail-open
  always an explicit consumer opt-_down_.
- The residuals catalogue is real. I checked its arithmetic (every Severity × Exploitability product
  lands in its claimed band) and, more importantly, its _coverage_: every residual I independently
  derived while reading the primitives was already in the table.

**The one systemic weakness: the sibling-seal semantics (finding 3.1).** It is the only place I
found where the design asserts two incompatible rules rather than one rule stated unevenly — and it
sits at the exact center of the recovery story, replicated across all three chain primitives, inside
the documents that call themselves the correctness proofs. Everything else in this review is polish
by comparison. I would resolve 3.1 (and its satellites 3.2 and the Position-2/3 matrix cells) before
any other item, and before any implementation work touches the merge layer or the state walk.

**A pattern worth a sweep of its own: qualifiers that hold the security argument.** Findings 2.4,
3.5, and 4.1 are all instances of one failure shape — a sentence that is only true with a qualifier
("accepted", "at or after", "tip-gated") stated somewhere else. The design's security arguments are
load-bearing on those qualifiers; a sweep that finds every `{X, X} → terminal`-style sentence and
attaches its qualifier would cheaply harden the whole surface against the exact misreading an
implementor under deadline will make.

## Verdict

The design is coherent, unusually honest about its limits, and consistent to a degree I have rarely
seen in a surface this size — with one significant exception. Finding 3.1 (does a recovery seal
landing as a sibling of accepted content bury it, or leave the fork live?) is a genuine
two-models-in-the-text contradiction, embedded in the correctness matrices themselves, and it
determines observable behavior (Active versus Forked for the same held events; one recovery event
versus two). It needs an explicit decision and a sweep. The remaining findings are: two documents
disagreeing about a rule the proof says is unreachable (3.7), two under-specified principles the
recovery paths already rely on (4.1, and the genesis threshold 4.2), a described-wrong construction
in the catalogues (3.4), an unenforced stated rule (3.8), and a set of qualifier and gloss slips
(0.1, 1.2, 2.3, 2.4, 3.3, 3.5, 3.6, 3.9, 7.1) that are individually small but sit on load-bearing
sentences. Nothing I found undermines the architecture's central claims — the end-verifiability
story, the two-tier resolution model, the witnessing floor's overlap argument, and the backdate
defenses all held up under the attacks I could construct against them.
