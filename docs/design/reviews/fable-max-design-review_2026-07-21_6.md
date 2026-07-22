# Fable (max) design review — 2026-07-21 (6)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_6.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

## Method

This is a cold review: the reviewer read the current files fresh, in the order given by
`docs/design/README.md`, without consulting any earlier review documents. The axes are
**correctness/soundness** (does each mechanism actually deliver the property it claims, including
against an adversary) and **consistency** (do the documents agree with each other — names, rules,
matrices, cross-references). All 41 documents in the reading order were read in full, plus
`README.md`, `MODEL.md` (checked against the design surface as the user-facing statement of the same
rules), and the identifier catalogues. Cross-document phrase and constant sweeps were run with
`scripts/grep-terms.pl`. Findings cite the file and section they rest on. Severity:

- **Critical** — a soundness hole: the mechanism does not deliver the claimed security property.
- **Major** — a real gap or contradiction that would mislead an implementer or weaken a guarantee.
- **Minor** — an inconsistency or unclear statement; low risk of a wrong implementation.
- **Note** — an observation or polish item; no correctness impact.

## Summary of findings

No Critical or Major findings. The design surface is exceptionally internally consistent; the
findings below are five Minor items and two Notes.

| #   | Severity | Area                          | Finding                                                                                                                                                                                                              |
| --- | -------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Minor    | Schema consistency            | The roster-change record's `add` field is a list on user identities but "a single prefix, not a list" on a federation governance event — one SAD kind with two shapes, straining the one-kind-one-schema rule        |
| 2   | Minor    | KEL reference consistency     | The KEL event table describes the witness-side `Wit` as "rotation + `clock`", but the clock value is a federation-IEL manifest role the KEL event may not carry                                                      |
| 3   | Minor    | Soundness — dispute forensics | The cross-federation rebind dispute's advertised proof (a "reserve double-reveal") does not cover the sequential-anchoring variant, which produces the same dispute with no double-reveal                            |
| 4   | Minor    | Underspecification            | Whether a member device's own federation binding must match its identity's is enforced only at a rebind, never at inception or in between — mixed-federation membership is representable but unaddressed             |
| 5   | Minor    | Security-parameter framing    | Fork-cost is priced per selected witness set, but deterministic, precomputable selection lets an attacker who can choose or await the attacked position succeed by owning fork-cost witnesses anywhere in the roster |
| 6   | Note     | Wording drift (batched)       | Four small wording drifts: V0 "carries" the reserved topics; one unqualified "each SEL's serial-1 v1"; "deferred-pending" versus "pending"; an environment-variable mention in doctrine voice                        |
| 7   | Note     | Operational cost visibility   | A busy plain-content data log forces a governance-priced re-seal every 64 content events; deliberate, but the recurring ceremony cost is not surfaced in the honest-limits catalog                                   |

## Overall verdict

The design holds together. Its central claims — that any consumer can verify any chain from the data
alone; that a content conflict is recoverable while a second accepted key-change branch is terminal;
that everything below the last clean seal is final; that a revocation check is a positive match on a
fresh chain rather than a scan for absence — are each backed by machinery that survived deliberate
attack during this review, and the three per-primitive correctness-proof documents (KEL, IEL, SEL
reconciliation) agree with the doctrine they instantiate. Section "What was attacked and held" below
records the specific attacks tried and why they fail, so this verdict is checkable rather than an
impression.

Consistency across the ~17,000-line surface is unusually strong. Every protocol constant appears
with the same value at every mention (verified by sweep: page size 129, unsealed-run 64, roster cap
32, manifest-list cap 128, lineage cap 64, delegation depth 8, grant-adds cap 64, witness key window
365 days, clock tolerance 1 minute). The event-kind tables, anchor matrices, threshold slots, sort
priorities, and seal-advancer sets agree across the shape reference, the per-primitive documents,
the glossary, and the doctrine. The residuals catalog's risk arithmetic (severity × exploitability,
and the band thresholds) checks out on every row. The plain-English `MODEL.md` matches the design
surface — including one subtle dependency: its claim that "an artifact can't go wrong on its own" (a
competing data-log event always forces fresh identity-chain activity) rests on the rule that at most
one content event per data log may ride one anchoring identity event, which the SEL documents both
state and make enforceable (the verifier dedups by anchor identity).

## Findings — detail

### 1. The roster-change record's `add` field has two shapes under one kind (Minor)

The roster/threshold delta is one SAD kind — `vdti/event/v1/roles/roster` in the kind catalogue —
and the schema rule in `kinds.md` §Schema is that a kind's field set is fixed for its version ("A
SAD carries only the fields its own kind defines"; changing the fields means a new versioned kind).
But the surface gives `add` two different shapes depending on which chain carries the delta:

- `shapes.md` §roster types `add` as `list⟨prefix⟩`, then says "On a **federation `Wit`**, `add` is
  a **single** prefix (one witness KEL added at a time), not a list."
- `event-shape.md` §The manifest: "`add` is a list on the user kinds and a **single** prefix on a
  federation `Wit`".
- `witnessing.md` §Roster governance writes the federation delta as
  `{ add: Prefix, cut: Prefix[], …thresholds }` — a scalar next to a list.
- `protocol-doctrine.md` §Federation convergence: "**`add` is a single prefix**".

If `add` is genuinely a scalar on a federation governance event and a list on a user identity's
event, one kind has two incompatible serializations — two producers can disagree on the canonical
bytes, which is exactly what the exhaustive-schema rule exists to prevent, and an implementer
reading only one site will build the wrong one. The cheapest fix is to declare `add` a list
everywhere and state the federation rule as a **cardinality constraint** (length exactly one on a
federation `Wit`, checked by the facet-aware validation the `Wit` already runs); the phrase "not a
list" should then go. Alternatively mint a separate federation-delta kind. Either way the four sites
should say the same thing.

### 2. The KEL event table attaches the clock to the wrong layer (Minor)

`kel/events.md` §Event taxonomy, the `Wit` row: "Federation **rebind** (user KEL — changes
`federation` / `witnesses`) / federation **governance** (witness KEL — rotation + `clock`)."

The clock is an inline value in a **federation IEL** event's manifest — `event-shape.md`'s role
table carries `clock` on federation IEL `Fcp` / `Wit` / `Trm` only, and the KEL manifest allowlist
(`kel/events.md` §The manifest) is `anchors` and `witnesses` with nothing else. What actually
happens is that the witness's KEL `Wit` **anchors** the federation IEL `Wit`, and _that_ event
carries the clock. The same document later says this correctly ("A governance `Wit` is **always a
rotation** of its participants and advances the monotonic federation `clock`" — where the advance
rides the anchored IEL event). The taxonomy row, read alone, invites an implementer to put a `clock`
role on the KEL event, which the role allowlist would then reject. Suggest rewording the row to
something like "rotation, anchoring the federation governance event (which carries the clock)".

### 3. The cross-federation rebind dispute's proof form is overstated (Minor)

Five sites state that when two competing federation rebinds at one position name **different**
federations — so each federation's witnesses honestly accept their own side and the chain reads
disputed with no witness misbehavior — the proof of what happened is the author's **reserve
double-reveal** (the same secret revealed twice): `system-thesis.md` §Federation convergence,
`protocol-doctrine.md` §Terminology and §Divergence and recovery ("only the reserve double-reveal
proves it") and §Pre-seal verifiability, and `witnessing.md` §Rebinding ("both reach threshold with
no witness double-sign — `disputed`, proven by the author's reserve double-reveal").

That proof form assumes the two competing events reveal one secret twice. It holds unconditionally
on a **device chain** (two competing key changes at one position must both reveal the preimage of
the same forward commitment). But an **identity's** rebind is an IEL event with no key of its own —
its members authorize it by anchoring it from their own device chains — and nothing forces the two
competing identity rebinds to be anchored from the _same_ device-chain position. A quorum can anchor
rebind A from one device event and rebind B from the **next** device event on each member's chain
(two sequential `Wit` events per device, each revealing a _different_, successive reserve). Both
identity rebinds still reach acceptance under their respective federations — the exact scenario
`witnessing.md` describes — and the chain is Disputed, but **no secret was revealed twice**, so the
`confirmed_reserve_double_reveal` predicate never fires and the cause reports unconfirmed.

Nothing unsafe follows: the doctrine already says attribution never gates the verdict ("When neither
is confirmable from held evidence, the verdict is still Disputed and the cause is reported
unconfirmed"), and the sequential shape _is_ still attributable evidence — the member device chains
linearly record two fresh participations anchoring competing siblings at one identity position,
which is undeniable double-dealing by those members. But the doctrine's claim that a dispute "always
carries a provable cryptographic misbehavior" is then carried by an evidence shape neither named
predicate captures, and the five sites saying the proof "is" the double-reveal are wrong for this
variant. Suggest either (a) naming the sequential double-anchoring shape as a third confirmable
proof form (a member's two chained participations anchoring competing siblings at one position), or
(b) softening the five sites to "a reserve double-reveal, or the members' double-anchoring, proves
it".

### 4. Member-device federation bindings are constrained only at rebind (Minor)

Every device chain must be federation-bound at inception (`kel/events.md` §Two-kind inception), and
every identity records its own binding on its inception. The only rule tying the two together is the
rebind field-match: an identity `Wit`'s `{federation, federationPin}` "must **match exactly** those
of every anchoring KEL `Wit`" (`iel/events.md` §The facet-dependent `Wit`; `iel/merge.md` rule 4).
At **inception** the members anchor via `Rot` events, which carry no federation fields — so no check
relates the members' own bindings to the identity's — and between rebinds nothing re-checks
(ordinary participations carry no federation fields either).

So an identity whose member devices are bound to _different_ federations than the identity itself is
representable, and the docs never say whether that is intended. It is not unsound — each event is
witnessed under the binding of the layer that owns it, and a consumer must independently trust every
federation involved, which the per-layer-context rules already imply — but it has real consequences
an implementer must decide: (a) should inception validation require member-KEL bindings to match the
identity's (there is currently no stated check)? (b) a device serving two identities in different
federations has one KEL binding that cannot match both, and each identity rebind it participates in
flips its own chain's binding; (c) an `Fcp`-rooted witness device structurally cannot anchor a user
identity's rebind (its `Wit` facet is federation governance), so if a witness KEL were admitted to a
user identity's roster that identity could never count it toward a rebind — whether witness KELs are
barred from user rosters at all is likewise unstated. One explicit sentence for each —
same-federation membership required or not; witness KELs admissible or not — would pin the intent.

### 5. Fork-cost reads stronger than it is for a position-choosing attacker (Minor)

`witnessing.md` prices manufacturing a fork at "the number of selected witnesses an attacker must
own _and expose_" — the fork-cost `2·threshold − signers`, over the witnesses **selected** for the
attacked position. Selection is deterministic and public: `select(prefix, serial, roster, signers)`
is a stable sort of the roster by a position-keyed digest, computable by anyone in advance for any
future serial. An attacker who can **choose or await** the attacked position — an owner equivocating
its own chain picks the serial it forks at; an attacker on a victim's chain can wait for a favorable
future serial — therefore does not need its owned witnesses to be selected by luck: it computes the
selection for upcoming serials and strikes at one where its owned set is included. The effective
requirement for such an attacker is owning fork-cost witnesses **anywhere in the roster**, with
waiting time in place of per-position probability.

The documents almost say this: the fork-cost-1 warning notes "deterministic selection makes a thin
intersection a precomputable target, so the single gating witness for a position can be identified
in advance", and the residuals table's "Under-provisioned witness set" row prices at roster level
("N compromised witnesses forks you"). No number changes and no mechanism is wrong — selection
deliberately excludes the event's bytes so an attacker cannot _mint_ favorable sets, and that holds.
The finding is presentation: the general fork-cost statements ("selected witnesses an attacker must
own") read stronger than the position-choosing case, and the precomputability remark is attached
only to the fork-cost-1 warning. One sentence generalizing it — deterministic selection means
fork-cost witnesses anywhere in the roster suffice for an attacker able to pick the position — would
make operator provisioning guidance match the real bar.

### 6. Small wording drifts (Note, batched)

- **`shared-documents.md` §The constitution** lists "**the reserved topics** — a holder derives the
  governance chains from the document prefix" among the fields V0 "carries". The V0 shape in
  `shapes.md` has no topics field — the topics are protocol-reserved strings, and the governance
  chains are derived from the document prefix plus those constants. The bullet's placement under "V0
  carries:" suggests a field that does not exist.
- **`event-shape.md` §Event taxonomy (IEL), the `Ixn` row** says it "anchors content SEL events,
  each SEL's serial-1 **v1**" — the one site that drops the "content" qualifier every other site
  carries ("each **content** SEL's v1"). A lookup log's first event is anchored by the kill or grant
  anchors, not by `Ixn`; the row is technically readable as broader than the matrix allows.
- **Sub-threshold vocabulary** drifts between "deferred-pending" (KEL/IEL documents, and parts of
  the SEL merge document) and bare "pending" / "held pending" (`sel/merge.md` §Merge outcomes,
  `sel/log.md` §The SEL is its own witnessed chain). Same concept; one term would help a reader
  grepping for the state.
- **"configurable via env var"** (`kel/log.md`, `kel/verification.md`, `iel/log.md`,
  `iel/verification.md`, on the verifier's page budget) is implementation phrasing inside design
  doctrine. The budget being local and configurable is fine (it is a work bound, not a consensus
  value — the docs elsewhere make that distinction carefully); naming the configuration mechanism is
  the only drift.

### 7. The governance price of a busy plain-content data log (Note)

Every chain must land a seal-advancing event at least every 64 content events (the seal-advance
cap), so the recoverable-fork page stays bounded. On a device chain the re-seal is that device's own
rotation (cheap); on an identity it is a roster-less evolve at the governance threshold; and on a
**plain content data log** — which has no natural grant or kill to advance its seal — it is the
neutral re-seal `Sea`, anchored by an identity `Evl` at **`t_govern`** (`sel/events.md`
§Seal-advance cap). So a high-volume content log costs its owner a governance-threshold ceremony
every 64 events — e.g. two-of-three devices co-signing, recurring with content volume. This is
plainly deliberate (a seal-advancer must be above content tier, or a stolen signing key could pick
fork winners), and the mechanics are stated; what is missing is the cost's visibility. The residuals
catalog's "Roster / seal caps" row mentions that long content runs force periodic re-seals but not
that a plain data log's re-seal is priced at governance tier. One line there would let a deployment
planning a high-volume log see the ceremony cadence it is signing up for.

## What was attacked and held

This section records the deliberate attacks and edge-case probes tried during the review that the
design withstood — so the "no Critical/Major findings" verdict is inspectable. Grouped by layer.

**Data substrate (SAD / SAID / custody / compaction).**

- _Lying embedded children:_ an expanded wire form whose inline child claims a digest that does not
  match its bytes is caught by Rule 2 (verify each child before substituting its digest into the
  parent's canonical form) — the gap the rule exists for, and `said.md` argues it explicitly.
- _Set-order malleability:_ two orderings or a duplicate-bearing copy of an order-free list would
  yield two digests for one logical content; the strictly-ascending rule plus reject-on-violation
  closes it, and the undeclared-fields rule closes junk-padding variants. Both are stated as
  validation gates protecting the canonical form, which is the right enforcement posture.
- _Backdated write attributions:_ a standalone record's writer-binding is corroborated by an
  append-only anchor on the writer's identity chain, located (never trusted) by the record's pin;
  the mint-and-anchor step is tip-atomic and an intervening append makes verification fail closed.
  The earliest-anchor argument for credentials (a hash-cycle would be needed to anchor earlier than
  the pinned position) is sound.
- _Anchor-locator confusion:_ the pin points at the anchor's parent, so any child of that parent
  passes the parent-link check — but the commitment-membership check is the discriminator, and an
  intervening event lacks the commitment. Verified coherent.

**Cross-cutting doctrine (tiers, seals, divergence, effective state).**

- _Threshold arithmetic:_ the identity threshold bounds (security floor, recoverability ceiling with
  its advisory-at-two / hard-at-three split, strict-majority authorization floor, never-empty
  roster, singleton rules) are mutually satisfiable at every roster size, and the federation's
  tighter bounds (`|roster| ≥ 4`, `threshold ≤ min(|roster| − 2, signers − 1)`, exclude-self pool)
  check out at the minimum federation exactly as the worked example states (three to govern, two to
  witness).
- _Backdating a dispute onto settled history:_ a below-seal sealed straggler is declined by
  witnesses (the witness mirrors the seal-cap) and dropped by the walk, so a harvested old secret
  cannot retreat the clean seal; the only reachable dispute is at the live seal, which needs the
  current signing key plus witness collusion. The brick-versus-takeover key analysis (the just-
  revealed reserve _is_ the current signing key; the next reserve only extends forward) is
  consistent across `kel/log.md`, `kel/events.md`, `compromise.md`, and the residuals catalog.
- _Ancestry smuggling:_ "an accepted event commits its ancestry" (for stale-pin recoveries and
  split-stall exits) cannot be used to sneak a first-seen loser back in, because a descendant of a
  buried or declined lineage is dead on ascent and honest witnesses decline it — the ancestry rule
  only ever commits ancestors that never lost a first-seen contest.
- _Fingerprint stability:_ the forked/disputed marker is keyed on the chain and the divergence
  ancestor (a single, earliest, deterministic position even for nested forks), is type-tagged so it
  can never collide with a real digest, and is deliberately not a digest over the competing tips
  (adversarially extensible). Every site states the same construction.
- _Enforceability of stated checks_ (the axis a prior round found a hole on): the one-content-
  event-per-anchoring-event rule is enforceable and placed — the data log's own verifier holds both
  events and dedups by anchor identity (`sel/events.md`, `sel/verification.md`); the "grant must be
  sealed, not merely fetched" rule in shared documents names its own bypass and the pass that closes
  it; the membership walk is performable by a store because the requester discloses its own entry;
  the lineaged-kill obligation that the primitive cannot backstop is called out as a feature-layer
  invariant in three places rather than silently assumed.

**Event-log primitives (KEL / IEL / SEL).**

- The three reconciliation matrices were checked against the merge and verification documents cell
  by cell where they overlap: the attach-position split, the sibling-at-the-seal tier resolution,
  the tier-rank terminate carve-out, the under-covering-burial acceptance, the retain-and-count rule
  for an accepted competing seal versus drop for declined/below-seal stragglers, and the
  transfer-ordering rules agree everywhere, including the subtle "no Disputed source/sink row
  needed" arguments.
- _Severance versus dispute:_ the claim that severance can never downgrade a Disputed data log holds
  — acceptance of a sealed data-log event gates on its identity-side anchor being accepted, and an
  accepted sealed anchor is never buried, so a disputed log's branches cannot lose their anchors.
  The unreachable-by-construction rows in the SEL crossing matrix are argued, not asserted.
- _Owner equivocation of a data log under a linear identity:_ correctly identified as un-
  preventable by anchoring (opaque anchors cannot be deduped by the identity) and closed by the log
  witnessing itself at its own position; the `Sea` re-seal exists precisely for the live-and-locked
  anchor case, and the matrix enumerates it.
- _Self-delegation collapse:_ an authorization listing the delegator's own prefix is rejected, so a
  delegate-of leaf cannot be collapsed into the identity leaf by self-grant.

**Federation and witnessing.**

- _Genesis circularity:_ the no-self-witnessing argument is honest — authorization is ordinary
  member anchoring, trust is the configured prefix, and the inception marker is interpretation only.
  A partial genesis reads sub-threshold, fail-secure.
- _Witnessed-time manipulation:_ the threshold-th-smallest receipt-time rule was probed — adding
  late receipts cannot move the crossing later, moving it earlier needs a full threshold compromise,
  and each receipt time is capped by the consumer's clock band and its signer's key window. The
  stated monotone-downward property and its eclipse bound are right.
- _Currency-gate reasoning:_ the no-grace-window argument (any grace re-admits the pre-cut roster
  exactly during the window the cut exists for), the membership-change-not-rotation trigger, and the
  stale-pin recovery path (defer, re-pin, ancestors committed by the accepted re-pin) are coherent,
  as is the receipt validity conjunction (signature, in-window key, selected signer, exact
  committed-config match — where a _higher_ self-asserted threshold is still invalid).
- _Escape from a compromised federation:_ the rebind self-bootstraps into the federation it
  declares; the graceful overlap is cooperative-only and escape is a synchronized hard cutover —
  stated consistently in the residuals catalog and the witnessing document.

**Policy, protocols, features.**

- _Policy evaluation:_ zero thresholds and empty/one-child conjunctions are rejected as vacuous
  gates; unknown constructs deny the whole policy; the distinct-identity crediting is defined as an
  existential assignment (set-packing) with budget-exhaustion denying — so differing budgets can
  only differ toward denial; the acyclicity-by-digest termination argument is sound.
- _The sealed envelope:_ the two identity bindings (sender inside the sealed content, recipient in
  the signed cleartext) close strip-and-re-sign and recipient-key substitution respectively, and the
  boundary list (currency, replay, delivery, hiding are the caller's) is complete and matches the
  callers' documents. The per-message key makes nonce reuse unreachable; the mesh transport gets the
  same property from per-direction counters under per-connection keys.
- _Presentation freshness:_ the replay analysis (same-verifier replay hits the nonce cache;
  cross-verifier replay fails the audience binding; credential-swap breaks the recomputed digest the
  signature covers; the cache-retention window and the acceptance window expire together) is
  airtight for the targeted case, and the bearer copy-race is honestly confined to single-use
  instruments with redemption-as-revocation.
- _Chat and shared documents:_ the lane bracketing (anchored root in, witnessed removal bound out,
  interval check needing no fork detection), the honored-window predicate (all three positions on
  the editor's own append-only chain; the effective floor from hash-preimage order; open-by-absence
  answered by the fail-secure kill walk), and the disjointness pass (per-document validation,
  withheld grant reads conservative) each survived probing; the accepted residuals (dormant-member
  window, one-device chat authenticity, home-node visibility, open-epoch future-dating) are all
  present in the honest-limits catalog with the same statements.

## Coverage

Read in full, in reading order: `README.md`; `docs/design/README.md`; `system-thesis.md`;
`glossary.md`; the SAD group (`sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`,
`kinds.md`, `shapes.md`, `tags-and-topics.md`); `protocol-doctrine.md`; `residuals.md`;
`monitoring.md`; `event-shape.md`; the KEL group (`log.md`, `events.md`, `verification.md`,
`merge.md`, `compromise.md`, `reconciliation.md`); the IEL group (`log.md`, `events.md`,
`verification.md`, `merge.md`, `reconciliation.md`, `delegation.md`); the SEL group (`log.md`,
`events.md`, `verification.md`, `merge.md`, `reconciliation.md`); the federation group
(`bootstrap.md`, `witnessing.md`, `topics.md`, `mesh-transport.md`); the policy group (`policy.md`,
`documents.md`, `evaluation.md`); the protocol primitives (`essr.md`, `ipex.md`,
`receive-key-directory.md`, `group-key.md`, `membership.md`, `authored-dag.md`); the features
(`credentials.md`, `exchange.md`, `shared-documents.md`); and `MODEL.md` as the user-facing
consistency check. Existing files under `docs/design/reviews/` were not consulted (cold review, as
instructed; they appeared only as unread hits in constant sweeps). Sweeps run with
`scripts/grep-terms.pl`: all protocol constants; the roster-`add` phrasing; the witness-side clock
phrasing; every "reserve double-reveal" site; recovery-key mentions (all correctly negative — "no
recovery key").
