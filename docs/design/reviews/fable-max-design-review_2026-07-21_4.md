# Design review — correctness, soundness, and consistency (2026-07-21, pass 4)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness nad consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-21_4.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. ignore the existing files in docs/design/review.

## Scope and method

This is a fresh, standalone review of the design documents under `docs/design/`, read at commit
`4e53701` on 2026-07-21. I read the repository `README.md` for orientation, then followed the
reading order in `docs/design/README.md` from top to bottom: orientation, the data substrate, the
cross-cutting doctrine, the three event-log primitives, federation and witnessing, the
document-authorization layer, the protocol primitives, and the features. Prior review files in
`docs/design/reviews/` were deliberately not read, so nothing here is inherited from an earlier
pass.

The review asks two questions of every document:

- **Correctness and soundness** — do the stated rules actually deliver the properties the design
  claims? Where a document argues "this cannot happen," does the argument hold against an adversary
  who controls timing, ordering, and any data not protected by a signature or a hash?
- **Consistency** — do the documents agree with each other? When two documents describe the same
  rule, field, or walk, do they describe the same thing?

Each finding says where it lives (file and section), what the documents say, why I believe it is a
problem (or worth attention), and how severe it looks from here. Severity labels:

- **Critical** — appears to break a stated security property.
- **Major** — a soundness gap, a contradiction between documents, or a rule an implementer would
  plausibly get wrong by following the text as written.
- **Minor** — a smaller inconsistency, an incomplete statement, or wording that misleads.
- **Note** — an observation or a question for the designers; no defect claimed.

## Status

**Review complete.** All 41 design documents in the reading order were read, plus the repository
`README.md`, `MODEL.md`-adjacent orientation, and the two identifier catalogues.

## Verdict summary

The design is in strong shape and, on the whole, unusually rigorous — the divergence-and-recovery
core, the two-tier compromise model, the witnessing floor, and the correctness-proof matrices all
hold together under an adversary I tried hard to hand an advantage. I found **one Major consistency
contradiction** worth fixing before implementation, **one Minor completeness gap**, and a set of
notes and questions that are mostly "state this a little more explicitly" rather than "this is
wrong."

The findings, most to least severe:

| #   | Severity  | Where                                                | In one line                                                                                                                                                                                                               |
| --- | --------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Major** | SEL primitive (Group 6) vs. delegation (Groups 5, 8) | The delegating-link lookup log is `{Icp, Pin}` — a tier-1 serial-1 event at a lookup address — which the SEL's own verifier-enforced discriminator rule declares invalid.                                                 |
| 2   | **Minor** | `kinds.md` (Group 2)                                 | The "canonical enumeration of every SAD kind" omits the gated rescind-doc kind that `shapes.md` describes, so the completeness claim is not quite true.                                                                   |
| 3   | Note      | `custody.md` (Group 2)                               | The "blinded" commitment hash is deterministic and unsalted; its privacy depends on the target identifier being unguessable, which the general custody rule does not require (the nonce discipline elsewhere is the fix). |
| 4   | Note      | Glossary (Group 1)                                   | The glossary states precise boundary rules, making it a second normative surface to keep in lockstep with the owning docs.                                                                                                |
| 5   | Note      | Federation (Group 7)                                 | A federation carries two distinct thresholds (governance vs. witnessing) whose relationship is spread across two docs; a worked minimum-federation example would remove doubt.                                            |
| 6   | Note      | Credentials / operations (Group 10)                  | "Revoke before terminating" is a real irreversible operational hazard that should reach the operations docs.                                                                                                              |

Only finding #1 is a genuine cross-document contradiction. Everything else is a smaller gap, an
observation, or a place where the design is correct but a reader could be helped by one more
sentence. I did not find a soundness break in the security core.

The one thing I want to be direct about: this review is a **read for internal consistency and stated
soundness**, not a proof. The design's own thesis is that correctness is the only metric and that a
wrong rule ships permanently, so the value of finding #1 is precisely that it is the kind of seam —
two internally-reasonable documents that contradict at their boundary — that a single-document read
would miss and that code would then encode one way or the other. I recommend resolving it in the
design before any implementation depends on delegation.

## Group 1 — Orientation and framing

Documents read: the repository `README.md`, `docs/design/system-thesis.md`,
`docs/design/glossary.md`, and the design directory's own `README.md`.

These documents are internally coherent and agree with each other on the story they tell: every
record proves itself from its own bytes, any reader can check everything with no service to trust,
and when two histories conflict the conflict is either prevented (for witnessed writes) or made
visible and resolved by a fixed rule (never silently merged). The glossary is unusually careful — it
distinguishes near-identical terms (for example the three one-letter-apart words for "ended chain,"
"rejected successor," and "the ending event itself") and says explicitly that the owning document
wins where definitions differ.

No correctness findings in this group. One observation:

- **[Note] The glossary is doing doctrinal work, not just defining terms.** Several entries (for
  example "witnessed vs accepted," "confirmed tip," and the narrow sense of "governance") state
  precise rules — including boundary conditions like "a below-threshold event is never counted
  toward a verdict" — that a reader might not find stated as crisply in the owning document. That is
  fine while the glossary and the owning documents agree (and I checked the ones below against their
  owners), but it makes the glossary a second normative surface that must be kept in lockstep. The
  glossary's own header mitigates this by declaring the linked document canonical.

## Group 2 — The data substrate

Documents read: `sad.md`, `said.md`, `custody.md`, `availability.md`, `compaction.md`, `kinds.md`,
`shapes.md` (all under `docs/design/primitives/data/sad/`), and
`docs/design/primitives/data/event-logs/tags-and-topics.md`.

This layer is in strong shape. The two-hash rule for a chain's first event (one hash names the
chain, a second names the event, so a logged event identifier never doubles as the chain's lookup
key) is correctly argued, including the honest hedge that the two values differ "with overwhelming
probability" rather than certainly. The rule that a record's identifier is computed over its
most-compact form, and the companion rule that any inline-embedded child must be verified before its
identifier is substituted in, close the substitution gap the second rule's own text describes. The
set-valued-list rule (sorted and duplicate-free, else rejected) correctly plugs the "one logical
set, many byte forms" hole that canonical JSON leaves open for arrays.

Findings:

- **[Minor] `kinds.md` claims to be a complete catalogue but at least one record type has no
  entry.** `kinds.md` opens with "This doc is the canonical enumeration of every SAD kind" and later
  says exactly one further kind is owed (the replica-set record). But `shapes.md` (Shared documents
  section, and its Forthcoming table) also describes a "gated rescind-doc" — the record a
  membership-removal terminator points at through its `bound` role — whose kind appears nowhere in
  `kinds.md` (the shared-document row enumerates `inception` / `version` / `comment` /
  `comment-resolution` and trails off with an ellipsis). Either the rescind-doc's kind should be
  named (even as forthcoming), or the "one further kind is owed" sentence is wrong. A completeness
  claim that is almost-but-not-quite true is worth fixing precisely because readers will rely on it.
- **[Note] "Blinded" commitment hashes are deterministic and unsalted — the blinding is only as
  strong as the target identifier's guessability.** The custody anchor commits
  `hash(tag:{owner}:{said})` so the owned record's identifier "never appears raw on the public
  chain." Anyone who already holds the record can compute the same hash and locate the anchor — that
  is intended (it is how attribution is verified). The privacy claim therefore depends on the
  record's identifier being unguessable to everyone else. The design is aware of this — credentials,
  files, chat messages, and private-document records all carry a mandatory high-entropy `nonce`
  specifically to make their identifiers unguessable — but the general custody rule does not require
  a nonce on every owned record. An owned record of a guessable shape (small, enumerable content, no
  nonce) would let an observer confirm by dictionary that a given owner anchored it. Worth a
  sentence in `custody.md` stating that the blinding assumes an unguessable identifier, with the
  nonce discipline as the fix.

## Group 3 — Cross-cutting doctrine

Document read: `docs/design/protocol-doctrine.md` (the largest document in the tree).

This is the conceptual core, and it is impressively thorough — it enumerates the divergence cases,
argues each resolution, and repeatedly returns to the same adversary (someone who holds an old key,
or a current key, or colluding witnesses) to test each rule. The central chain of reasoning holds
together: only tier-1 content can be buried; a sealed event can never be buried; therefore two
accepted sealed branches can never be reconciled and the chain is stuck (Disputed); therefore
recovery is always "attach a burying sealed event at your own last good position." I checked the
boundary arithmetic on the threshold bounds and it is self-consistent (see below).

Findings and observations (several of these are questions I will confirm or drop when I reach the
primitive docs that own the detail):

- **[Note — to verify downstream] The two authority-threshold bounds are only jointly satisfiable
  because one of them is declared advisory at a roster of two.** The document requires both an
  "authorization floor" (`t_govern`, `t_authorize` must exceed half the roster) and a
  "recoverability ceiling" (they must be at most the roster size minus one, so the identity can
  always evict one member). At a two-member roster the floor forces the count to 2 while the ceiling
  would force it to 1 — a direct contradiction — and the document resolves this by making the
  ceiling "advisory at |roster| = 2, hard at |roster| ≥ 3." That is coherent, but it means a
  two-member identity structurally cannot evict a member without reincepting. I will confirm the IEL
  events document states the same thing and draws the same conclusion, since a reader who only sees
  the "can always evict one member" framing elsewhere would be misled.
- **[Note] The page-size constant is asserted, and the whole page-atomic recovery argument leans on
  it.** The doctrine pins `MINIMUM_PAGE_SIZE = 129 = 2·MAXIMUM_UNSEALED_RUN + 1`, i.e. an unsealed
  run of at most 64 per lineage, so a two-branch fork plus its burying seal always fits one page.
  The safety of "a source-to-sink transfer delivers the whole fork atomically" rests entirely on
  this. It is a clean argument; I flag only that it is a hard protocol constant doing load-bearing
  work, so every place that enforces the unsealed-run cap must use the same number. I will check the
  KEL/IEL/SEL docs agree on 64 and do not each restate a different bound.
- **[Note] "You can't seal a buried chain" (dead-on-ascent) is the linchpin and is stated as
  self-evident.** The claim that a seal built on a first-seen-losing lineage is itself dead, which
  is what collapses every dispute to a same-last-seal question, is asserted rather than proved in
  the doctrine. It is correct given first-seen witnessing (an honest witness declines the descendant
  of a losing sibling), but it depends on the witnessing layer actually declining those descendants.
  I will verify the witnessing document makes that decline explicit, because if a witness would sign
  the descendant of a losing branch, the dead-on-ascent property fails and disputes could form at
  arbitrary positions.

## Group 4 — The key event log

_Pending._

## Group 4 — The key event log

Documents read: `event-shape.md` (the shared taxonomy) and the KEL group — `kel/log.md`,
`kel/events.md`, `kel/verification.md`, `kel/merge.md`, `kel/compromise.md`, and
`kel/reconciliation.md`.

This is the most carefully worked part of the design, and I could not break it. The two-tier story
is airtight: a stolen signing key can only post content, and one rotation buries all of it; a stolen
rotation reserve is an unrecoverable takeover, and the design says so plainly rather than pretending
otherwise. The reconciliation document enumerates every combination of chain state, submitted event,
and cross-node timing, and each case resolves consistently with the merge rules. The page-size
constant (129 = 2×64 + 1) is stated identically in the doctrine, the log, the events, and the
reconciliation proof, and the "a fork plus its burying seal fits one page" argument depends on
exactly that arithmetic.

Two of my earlier doctrine-level questions are resolved here:

- **The dead-on-ascent linchpin is backed by an explicit witness decline.** `kel/compromise.md`
  (Federation witnessing) and `kel/reconciliation.md` (Matrix 4 safety guards) both state that a
  seal forged on a first-seen-losing lineage never reaches threshold because "honest witnesses,
  having accepted the winner at the fork, decline it." So the "you can't seal a buried chain"
  property is grounded in the witnessing layer declining the descendants of a losing branch, not
  merely asserted. I will still confirm the witnessing document itself makes that decline explicit
  (it is the load-bearing half), but the KEL side is sound.
- **The page constant is consistent everywhere in this group.**

No correctness or consistency findings in the KEL group. One small observation:

- **[Note] `region()` returns `trusted` for a takeover you did not author, which is correct but
  worth a consumer warning.** `kel/verification.md` is explicit that a single accepted sealed branch
  reads Active/`trusted` "node-agnostically," even when it is a reserve-theft takeover the rightful
  operator did not author — the rightful operator's only recourse is out-of-band reincept. The
  document states this honestly. The residual risk is entirely at the consumer: a relying party that
  treats `trusted` as "the rightful operator is in control" is wrong in exactly this case. This is
  inherent to the model (chain data cannot tell operator from thief), so it is not a defect — but it
  is the sharpest edge in the whole design for a downstream integrator, and the residuals catalog is
  the right place to make sure it is stated in consumer-facing terms. I will check that it is when I
  reach `residuals.md`.

## Group 5 — The identity event log

Documents read: `iel/log.md`, `iel/events.md`, `iel/verification.md`, `iel/merge.md`,
`iel/reconciliation.md`, and `iel/delegation.md`.

The IEL group is sound and consistent with the doctrine and the KEL group. It answered the open
question from Group 4 cleanly: an identity's inception (a tier-2 establishment) is anchored by _all_
initial members' KEL rotations, each consenting at tier 2, while a member _added later_ (via an
evolve event) consents at tier 1 with the continuing governance quorum authorizing at tier 2. That
asymmetry is deliberate and correct — at inception everyone is a founder, so everyone rotates;
later, a joiner only needs to consent while the existing quorum governs. The threshold-bound
arithmetic (security floor of 2, recoverability ceiling of roster-minus-one that is advisory at a
two-member roster and hard at three-plus, majority authorization floor) is stated identically here
and in the doctrine, including the "two-member identity is valid but unrecoverable" conclusion. The
facet-dispatch discipline — establish whether a chain is a user identity or a federation _before_
reading any witness-event payload, on every code path including a resumed walk — is carefully and
repeatedly enforced, which is the right instinct given that the payload allowlist is the only gate
on the directly-consumed governance roles.

No correctness or consistency findings in the IEL group.

- **[Note] The delegating-link lookup shape introduced in `iel/delegation.md` is where the Group 6
  finding below originates.** The IEL side is self-consistent; the tension is with the SEL
  primitive's address-discriminator rule.

## Group 6 — The data event log

Documents read: `sel/log.md`, `sel/events.md`, `sel/verification.md`, `sel/merge.md`, and
`sel/reconciliation.md`.

The SEL model is elegant — a single-owner log that witnesses _itself_ (because the owning identity
cannot see, and so cannot prevent, an equivocation of one of its own data logs), and that inherits
"deadness" from its owner when the owner buries a branch the log was anchored to. The two-axis
correctness proof (the log's own fork, crossed with inherited owner deadness, resolved
deadness-first) is complete and the severance rule is well-argued. But there is one real
contradiction:

- **[Major] The delegating-link lookup log has a tier-1 serial-1 event, which the log's own
  address-discriminator rule declares invalid.** Three SEL documents (`sel/log.md`, `sel/events.md`,
  `sel/verification.md`), plus `event-shape.md` and the glossary, state a _verifier-enforced
  biconditional_: a log carrying the `content: true` flag must have a tier-1 serial-1 event, and a
  log _without_ the flag (a "lookup," located by recomputing its address) must have a tier-2
  serial-1 event. `sel/verification.md` spells out the enforcement in as many words: "a v1-T1
  without `content: true` ... is invalid and rejected," and gives the security reason — it stops a
  tier-1 content log from squatting at a value-lookup address, where a consumer expects an
  unswappable (tier-2, reserve-backed) value.

  But the delegating-link lookup log — introduced in `iel/delegation.md` and catalogued as a lookup
  shape in `sel/log.md` and `sel/events.md` — is `{Icp, Pin}`: a _lookup_ (so it omits the `content`
  flag) whose serial-1 event is a `Pin`, which is _tier 1_. That is exactly the combination the
  biconditional rejects ("a tier-1 serial-1 event without `content: true` is invalid"). A verifier
  that enforces the biconditional as written would reject every delegating-link lookup, which would
  break the positive-delegation-path mechanism entirely.

  The delegating-link is not actually _unsafe_ — `iel/delegation.md` says its tier-1 anchoring is
  "discoverability only," and a verifier re-derives the address, reads the pinned position, and
  "re-checks the `Ath` grant directly" at tier 2, so a squatted delegating-link grants no authority.
  So the shape is safe by a _different_ mechanism (re-verification against the actual grant) than
  the one the biconditional relies on. The problem is purely that the biconditional, as stated in
  five places, is absolute and admits no third category, while the delegating-link _is_ that third
  category: a tier-1 lookup. And the fix cannot simply scope the rule by topic, because the same
  documents insist the discriminator is read "with no tier-check on the read path" and "never the
  topic's meaning" — the verifier is deliberately meaning-blind, so it cannot special-case the
  delegation topic.

  Failure scenario: an implementer builds the SEL verifier to the biconditional exactly as written
  in `sel/verification.md` (v1-T1 ⟺ `content: true`), then delegation is implemented to
  `iel/delegation.md`; every delegating-link the delegation layer mints is rejected as structurally
  invalid at its serial-1 `Pin`, and no `del(X, N)` document can have its authorizing path
  re-derived. Because "VDTI ships once," this is the kind of seam that has to be reconciled in the
  design, not discovered in code. The reconciliation is a design decision I won't make here: either
  the biconditional gains an explicit third case (a "pointer lookup" whose tier-1 serial-1 event is
  permitted because the grant it points at is re-verified at tier 2), or the delegating-link takes a
  different shape. I flag it because the current text asserts both halves as absolute and they
  cannot both hold.

## Group 7 — Federation and witnessing

_Pending._

## Group 7 — Federation and witnessing

Documents read: `substrate/federation/bootstrap.md`, `substrate/federation/witnessing.md`,
`substrate/federation/topics.md`, and `substrate/infrastructure/mesh-transport.md`.

This layer is the soundness floor under all three logs, and it holds up. The bootstrap document is
careful about the one genuinely circular-looking spot — who witnesses the federation's own first
event — and resolves it honestly: nobody does; trust in a federation comes entirely from the
consumer's configured set of trusted federation prefixes, and the inception event is only a marker
that says "read me as a federation," never a claim to be trusted. The witnessing floor (a strict
majority of selected witnesses) is correctly shown to force any two quorums to overlap, which is
what makes two competing same-kind events un-co-witnessable. The clock and key-window machinery
closes the "harvest an old key and forge a backdated fork years later" attack by making such a
forgery read as stale.

This layer resolved my Group 3 dead-on-ascent question decisively:

- **The dead-on-ascent linchpin is grounded here.** `witnessing.md` states it directly: "a seal on a
  dead lineage — one that lost first-seen at any earlier position — is itself dead on ascent (you
  cannot seal a buried chain), so it never counts," and "in the honest case only one branch's
  lineage survives first-seen." Combined with the acceptance-is-per-lineage rule, this makes "you
  can't seal a buried chain" a data-local walk property (the verifier sees the ancestor lost
  first-seen), not a bare assertion. The whole dispute-collapses-to-the-last-seal argument rests on
  solid ground.

No correctness or consistency findings. Two observations:

- **[Note] A federation carries two distinct thresholds, and the relationship is spread across two
  documents.** A federation identity has a governance count (how many witness members must co-author
  a governance event — subject to the authorization floor and the hard "can always evict one"
  ceiling, so it is 3 at the minimum four-member federation) _and_ a witness-config threshold (how
  many selected witnesses must sign a receipt — which is 2 at that same minimum federation, via the
  recoverability cap). Both are correct and jointly satisfiable, and `witnessing.md` does say
  "needing `t_govern` authors and `threshold` self-attestation," so they are not conflated. But the
  two numbers being different at the same roster size (3 vs 2) is the kind of thing a reader can
  trip on, and no single place lays the two side by side with their minimum-federation values. A
  short worked example ("at a four-witness federation: govern = 3, witness threshold = 2, signers =
  3") would remove all doubt. Not a defect.
- **[Note] The witnessed-time "cannot be pushed later" argument is subtle and load-bearing, and it
  is stated well.** The claim that an eclipse-class receipt-curating adversary can only inflate a
  computed time boundary by the honest receipt spread — and that the security-critical direction
  (pushing a key-window-closing boundary later) is pinned in the past by the durable threshold
  receipts — is the crux of the freshness argument. I could not break it. Flagging only that it is
  one of the few places where the safety property depends on a quantitative bound (the honest
  spread) rather than a structural impossibility.

## Group 8 — Document authorization

Documents read: `primitives/policy/policy.md`, `primitives/policy/documents.md`, and
`primitives/policy/evaluation.md`.

The separation this layer is built on — chain events authorize themselves structurally, while
documents are accepted against a policy the _relying party_ holds, never one the document carries —
is the right call and is argued well. The reason it matters is stated plainly: a document that
carried its own acceptance policy would just say "accept me." The counting rules are careful about
the one thing a naive threshold gets wrong (one signer must not fill two slots of a threshold over
multi-identity sub-policies), and the fix — search for a satisfying assignment, deny fail-secure if
the budget runs out — never wrongly permits. The as-issued-versus-current-trust distinction in
`evaluation.md` is exactly the distinction a relying party needs and is easy to get wrong: a
document issued under a below-seal state is validly-issued forever, but _newly_ relying on the
issuer now additionally requires the current region to be trusted and fresh.

No new findings in this group. One note:

- **[Note — reinforces the Group 6 finding] `documents.md` independently confirms the
  delegating-link shape.** Its delegation section states each hop's delegating link is "the
  content-addressed prefix recomputed from `(delegator, delegation-topic, delegate)`," i.e. the same
  recomputed-lookup shape whose serial-1 event is a tier-1 `Pin`. So three separate documents
  (`iel/delegation.md`, `sel/*`, and `documents.md`) build on a delegating-link lookup that the SEL
  biconditional would reject. That the mechanism appears in the policy layer too raises the blast
  radius of the Group 6 contradiction: `del(X, N)` policy evaluation depends on it.

## Group 9 — The protocol primitives

Documents read: `primitives/protocols/essr.md`, `ipex.md`, `receive-key-directory.md`,
`group-key.md`, `membership.md`, and `authored-dag.md`.

This group is clean. The sealed envelope (ESSR) states its four guarantees precisely and credits the
prior art it adapts; its "sender appears twice, by design" point (inside the sealed content to
defeat strip-and-re-sign, in the signed cleartext to route and bind the recipient) is exactly right
and not redundant. The disclosure exchange (IPEX) folds ownership-proof and replay-defense into one
signature over one envelope, which is what makes its baseline a single round trip, and its verifier
gate is exhaustive and correctly ties "presenting is a live use action" to the
identity-freeze-on-divergence rule from the IEL layer. The membership primitive's central trick — a
requester discloses its own blinded commitment so an untrusted store can _perform_ the default
fail-secure check, and a leaked commitment is not a bearer token because the disclosed value must
resolve to the live signer — is carefully reasoned. The authored-DAG's single-parent-is-equivocation
/ multi-parent-is-legitimate split, and the anchored-root-plus-removal-bound interval that
structurally closes a removed writer's backdate, are sound.

No correctness or consistency findings in this group. Two observations:

- **[Note] The receive-key directory is flagged as the first consumer of the value-lookup lineaged-
  kill obligation, and it correctly restates that the primitive does not backstop it.** This is the
  same feature-layer invariant `sel/verification.md` describes (a value-lookup rescission must
  declare the matching lineaged kill target, or a withholding node serves a stale value). The
  directory doc names itself as the first place this bites and points at the SEL verification doc.
  Consistent — and worth watching as more value-lookups are added, since each inherits the
  obligation.
- **[Note] Group-key and membership draw the bounded-versus-unbounded line clearly.** The repeated
  point that a keyed group needs _both_ a bounded wrap roster (to distribute the key) and an
  unbounded membership set (to authorize a requester), because wrapping forces enumeration and
  authorizing does not, is a genuinely easy thing to conflate and both documents keep it straight.

## Group 10 — The features

Documents read: `features/credentials.md`, `features/exchange.md`, and
`features/shared-documents.md`.

The three features compose the primitives without adding chain machinery, and each is consistent
with the layers it builds on. I spot-checked the derivation formulas against the tag catalogue and
they match: a credential's revocation target is `hash(revocation-tag : issuer : cred.said)` and its
issuance commitment is `hash(commitment-tag : issuer : cred.said)`, both exactly the generic custody
forms with issuer standing in for owner. The exchange feature's sender-key-currency check correctly
reuses the witnessed-time machinery and ties "a divergent sender chain freezes a current read" to
the same identity-freeze rule that IPEX and credentials use. Shared-documents draws a subtle
distinction correctly: a per-member removal is a rescission (`t_authorize`), while freezing the
whole document is a revocation of the creator's own grant chains (`t_govern`) — two different
terminate events with two different anchor kinds, matching the SEL anchor matrix.

No correctness or consistency findings in the features. Three observations:

- **[Note] Credentials states the "revoke before terminating" operational hazard clearly, and it is
  a real one.** Because a terminate freezes an identity's logs, a terminated issuer can no longer
  revoke its outstanding credentials, and a terminated issuer of single-use bearer credentials can
  no longer mark them spent (so they read reusable). Both are called out. This is the sort of
  irreversible operational footgun that belongs in a deployment runbook, not just a design doc —
  worth making sure it lands in the forthcoming operations docs.
- **[Note] A new protocol constant, `MAXIMUM_GRANT_ADDS = 64`, appears only in
  `shared-documents.md`.** It caps a grant event's add-list and is enforced as the verifier
  accumulates. It is distinct from the manifest-list cap (128) because a grant-doc is a grant-value
  record, not an inline manifest list, so the different number is fine — but it is a protocol
  constant introduced in a feature document, and every verifier must agree on it. Worth confirming
  it lands in whatever central constant registry the encode produces, alongside the page-size and
  roster-size constants.
- **[Note] Chat authenticity is one device's signature, not a quorum — deliberately, and stated as a
  residual.** Mail authenticates with the sender's use-quorum (through the sealed envelope), but a
  chat message is signed by a single writing device and attributed to its owning identity, so one
  compromised member device can author chat history in that identity's name (bounded by the device's
  key window, its epoch membership, and its own lane). This is a lower bar than mail and is called
  out as an accepted residual. Correct to flag; a consumer treating chat attribution as
  identity-quorum- strong would over-trust it.

## Group 11 — Cross-document consistency sweep

After the layer-by-layer read, I checked the load-bearing facts that appear in many documents to
confirm they agree everywhere. These are the things that would silently break the system if two
documents disagreed.

- **Protocol constants agree across every document that states them.** The page-size relation
  (`MINIMUM_PAGE_SIZE = 129 = 2 × MAXIMUM_UNSEALED_RUN + 1`, so the unsealed run is 64) is stated
  identically in the doctrine, all three KEL docs, and both IEL and SEL. The manifest-list cap
  (128), roster cap (32), lineage cap (64), delegation-depth cap (8), clock tolerance (1 minute),
  and key-window maximum (365 days) each appear consistently. No document contradicts another on a
  constant.
- **The kind-strict anchor matrix is identical everywhere it is drawn.** The event-shape reference,
  the doctrine's tiers section, and the per-primitive events docs all give the same matrix: a KEL
  witness-event anchors only the IEL witness-event; an IEL interaction anchors content and a
  credential's issuance commitment; authorize→grant, revoke/deauthorize→terminate, evolve→re-seal.
  The SEL and IEL sides of each pairing match.
- **The effective-SAID / chain-state / trust-region projection agrees across KEL, IEL, and SEL.**
  All three verification docs give the same four-way table (Active→trusted→real tip; Forked→forked
  synthetic; Disputed→disputed synthetic; Terminated→trusted→real terminate SAID), and all three
  describe the synthetic the same way (type-tagged, keyed on prefix plus divergence ancestor, never
  a digest over the competing tips). The tag catalogue's `forked`/`disputed` state codes line up
  with this.
- **The derivation-tag formulas are used consistently by their feature callers.** The commitment,
  revocation, rescission, and delegation tags defined in `tags-and-topics.md` are consumed with the
  matching `(owner, data)` arguments in custody, credentials, delegation, membership, and
  shared-documents. I found no formula stated one way in the catalogue and another way at a call
  site.
- **The one place two documents genuinely disagree is the delegating-link lookup shape** (the Group
  6 Major finding). The SEL address-discriminator rule (five documents) says a lookup log has a
  tier-2 serial-1 event; the delegation mechanism (three documents) builds a lookup log with a
  tier-1 serial-1 event. That is the single cross-document contradiction this sweep surfaced.

## Closing assessment

Read end to end, VDTI is a coherent single system rather than a pile of features, and the documents
reflect that: the same handful of ideas — a record is its own hash, only tier-1 content can be
buried, a sealed event can never be overturned, authority is judged at an append-only position,
witnessing prevents same-kind forks and detects cross-kind ones — recur at every layer and compose
cleanly. The correctness-proof matrices for the three logs are genuinely load-bearing and I could
not find a case they miss. The adversarial framing is applied consistently, and the honest residuals
(reserve theft is unrecoverable, a live-tip dispute is a deliberate brick, detection is eventual not
instant, chat trusts one device) are stated as residuals rather than hidden.

The single contradiction I found (the delegating-link's tier-1 serial-1 event versus the SEL
discriminator rule) is real and worth resolving, but it is narrow and the mechanism it sits in is
demonstrably safe by a different argument (re-verification against the actual grant), so the fix is
most likely a stated carve-out rather than a redesign. The rest of what I flagged is refinement.

If I were to prioritize one thing for the design team: reconcile the delegating-link shape with the
SEL discriminator, because `del(X, N)` policy evaluation depends on it and the current text asserts
both halves as absolute. After that, the completeness gap in the kind catalogue and the
two-threshold worked example are quick wins that reduce the chance a future reader trips where I
nearly did.

_End of review._
