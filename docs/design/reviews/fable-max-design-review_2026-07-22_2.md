# Fable (max) design review — 2026-07-22 (2)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_2.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

## Scope and method

This review reads the full design surface in the order `docs/design/README.md` prescribes —
orientation, data substrate, cross-cutting doctrine, event-log primitives (KEL, IEL, SEL),
federation and witnessing, document authorization, protocol primitives, and features — plus the
repository `README.md`, `MODEL.md`, and `USES.md` for consistency with the design surface. It
focuses on two questions:

- **Correctness / soundness** — do the rules, as written, actually deliver the properties the
  documents claim? Where a document argues "an attacker cannot X," does the argument hold against an
  adversary who controls the data, the network, or a subset of keys?
- **Consistency** — do the documents agree with each other? Where two documents describe the same
  rule, field, or flow, do they describe it the same way?

Existing files in `docs/design/reviews/` were not read; this is an independent pass. Searches used
`scripts/grep-terms.pl` to tolerate line wrapping and decoration.

Findings are numbered F1, F2, … in reading order of discovery, then summarized in a table once the
pass is complete. Severity vocabulary: **high** (a stated security property does not hold as
written), **medium** (a rule is wrong, ambiguous, or two documents conflict in a way that could
mislead an implementer), **low** (minor drift, unclear wording with a safe reading, or a gap worth
noting).

## Headline

The design is **sound and consistent as written** on the two axes this review targets. I read the
full surface adversarially, chased the load-bearing arguments to their premises, and found **no
place where a stated security property fails**, and **no hard contradiction between two documents**.
The event-log core (KEL / IEL / SEL), the federation/witnessing layer, and the cross-cutting
doctrine cross-check cleanly: the kind taxonomies, the kind-strict anchor matrices, the
threshold-vector bounds, and every protocol constant are stated identically wherever they recur, and
the "witnessed vs. accepted" distinction that a divergence verdict hinges on is used consistently
throughout.

What follows is therefore a short list of **low-severity items** — one coordination gap that a
forthcoming encode should pin down, and a few places where an orientation-level or feature-level doc
compresses or omits a nuance that the authoritative doc states precisely. None of them is a break.
The larger part of the value is the **positive record** in the "What I verified" section: it names
the specific arguments I stress-tested so a later reader knows what was actually scrutinized.

## Summary of findings

| #      | Area                              | Severity   | One-line                                                                                                                                                                                       |
| ------ | --------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **F1** | Group keying / chat membership    | low–medium | A keyed group keeps two independently-maintained member sets (the wrap roster and the membership set); the invariant that a removal updates **both** is not pinned.                            |
| **F2** | Orientation docs vs. witnessing   | low        | The thesis/glossary compress the "one witnessed sibling **per kind** per position" ladder into "one-per-position," under-stating the cross-tier co-sign the split-stall exit relies on.        |
| **F3** | Credentials — the issuance anchor | low        | `credentials.md` presents the issuance anchor as durable without noting it is buriable content until the issuer's next seal, so a fork-recovery can orphan it.                                 |
| **F4** | Availability replica-set kind     | low        | The `availability.replicas` target is a SAID of a "replica-set SAD" whose `kind` is still owed; when it lands it must be added to the store's served-by-SAID list, which does not list it yet. |

Severity: **high** = a stated security property does not hold; **medium** = a rule is wrong,
ambiguous, or two docs conflict in a way that could mislead an implementer; **low** = minor drift, a
compression with a safe careful reading, or a completeness gap with a benign default. Nothing in
this pass reached high or medium.

## Findings

### F1 — A keyed group's two member sets must be kept in lockstep, and the invariant is not stated (low–medium)

**Where:** `primitives/protocols/group-key.md`, `primitives/protocols/membership.md`,
`features/exchange.md` (the chat section).

A chat is a **keyed group**, and the design is explicit that a keyed group **composes two different
member structures**, deliberately:

- the **group-key wrap roster** — bounded, enumerable, materialized by members to seal each epoch
  key to every current member's devices (`group-key.md` §The pieces); and
- a **membership set** (`chat-membership`) — unbounded, per-requester, never materialized, used to
  gate store deposit/fetch (`membership.md`).

Both are owned by the group's governing identity, and both change through a tier-2 `Gnt ← Ath` act.
`exchange.md` ties a removal to both at once: "A member removal rescinds the `chat-membership` grant
… as the same act turns the epoch," and the epoch turn re-keys **only to the survivors** — which
reads the **wrap roster** to know who the survivors are.

So the load-bearing invariant is: **a removal must update the wrap roster and the membership set
together.** If they can drift, the two failure directions are real:

- Wrap roster **not** updated, membership set updated → the removed member still gets the next epoch
  key sealed to its device (forward secrecy on removal is lost — the property `group-key.md` §The
  ratchet promises), even though the store now refuses it (it can still obtain the ciphertext from
  another member and decrypt).
- Membership set updated wrongly / roster updated but membership not → a current member is locked
  out of the store, or a removed member retains store access.

The design's **intent** is clearly "one removal does all of it," but three distinct SELs are
involved (the group-key epoch log, the group-key roster, and the `chat-membership` grant chain), the
shapes are marked **forthcoming**, and no normative statement pins the atomicity/ordering that
prevents a partial removal. This is the one item I'd ask the exchange/group-key encode to state
explicitly — either as a single atomic multi-SEL act, or as a defined order with a fail-secure
reading of the in-between state (e.g., "a member counts as removed the instant **either** structure
records it").

**Not a break today** (nothing in the current docs is wrong), but it is exactly the kind of
cross-structure invariant an implementer can miss, so it belongs in the design surface rather than
being left to inference.

### F2 — The orientation docs compress the witnessing "ladder" in a way that hides the cross-tier co-sign (low)

**Where:** `system-thesis.md` §Federation convergence, `glossary.md` (the "position gate" entry) —
against the authoritative `substrate/federation/witnessing.md` §First-seen.

The precise, load-bearing rule (`witnessing.md`) is a **ladder**: a selected witness signs at most
one sibling **per kind, per position** — so at one `(prefix, serial)` a witness may legitimately
sign **both** a content sibling **and** a sealed sibling. That cross-tier co-sign is not incidental:
it is exactly what the **split-stall exit** relies on — a burying seal-advancer at a stalled content
position "signed by every selected witness **including those that signed a content sibling** (the
permitted cross-tier co-sign)." `witnessing.md` §The predicate is tier-scoped states it plainly: "An
honest witness legitimately holds `{≤ 1 content} ∪ {≤ 1 sealed}` at a position."

The orientation docs compress this. The thesis writes "**one-per-position witnessing (content _and_
sealed — the position gate is universal)**," and the glossary's `position gate` entry reads
"first-seen witnessing at a chain's own `(prefix, serial)` — the **universal** fork-prevention
primitive, applied to **every event, content _and_ sealed**." On a careful reading the thesis is
salvageable (its next clause says "two competing **same-kind** events … can never both be
witnessed"), but the standalone phrase "one-per-position witnessing" and the glossary's "applied to
every event, content and sealed" both read naturally as _one event per position_ — which would
contradict the cross-tier co-sign a reader needs in order to understand how a stalled content
position ever gets its burying seal.

**Suggested fix:** in the glossary `position gate` entry, say "one first-seen sibling **per kind**
(one content, one sealed) per position," so a reader who lands there without `witnessing.md` open
does not infer a stricter, wrong rule. The thesis is lower-risk but would read cleaner with the same
"per kind" qualifier on the compressed phrase.

### F3 — The credential's proof-of-issuance anchor is buriable content until the issuer's next seal (low)

**Where:** `features/credentials.md` §The two foundations — against `protocol-doctrine.md`
§Terminology (cross-chain anchor satisfaction) and `residuals.md` ("Burying rotation orphans a
dependent anchor").

`credentials.md` presents the issuance anchor as durable — "**witnessed** … **positioned** … read
**as-of that position**" — which is true, but it omits that the anchoring event is a **tier-1 `Ixn`
on the issuer's IEL**, and tier-1 content is **buriable until the issuer's next seal**. The
cross-chain-anchor rule (`protocol-doctrine.md` §Terminology) is explicit: "a tier-1 (`Ixn`) anchor
(buriable) drops when a later burying seal buries its host … the dependent answer flips to
unsatisfied." So a credential whose issuance `Ixn` sits in the issuer's **current unsealed content
window** can have its proof-of-issuance orphaned if that window forks and the issuer recovers by
burying the branch the `Ixn` rode — after which the credential reads _not validly issued_ and must
be re-minted (fresh `issuerPin`, fresh SAID).

Two things bound this so it stays **low**, and both are why it is not a soundness break:

- **Pre-seal verifiability locks it quickly.** The moment the issuer authors its next seal-advancer
  (routine — any governance act, or the roster-less re-seal `Evl` at the cap), the issuance `Ixn`
  falls at-or-below the clean seal and can **never** be buried. The exposure window is only the
  current content run (≤ `MAXIMUM_UNSEALED_RUN`).
- **It is largely self-inflicted / adversarial-only.** A content fork on the witnessed issuer IEL
  requires a witness compromise to form at all, and an honest issuer recovering a fork **retains its
  own branch** (which carries its own issuance `Ixn`); the anchor is only orphaned if the real
  issuance rode _on top of_ adversarial forked content that gets buried.

The general consequence is already in `residuals.md` ("Burying rotation orphans a dependent anchor …
detected, not prevented; recovered operationally"), and the parallel case is stated directly for
shared-document versions ("A version whose IEL anchor resolves onto a **dead** branch …
**un-attributes**"). The gap is only that **`credentials.md` itself does not cross-reference it** —
so a reader of the credentials feature could come away believing the issuance anchor is
unconditionally durable. A one-line pointer to the orphaned-anchor residual (and the "re-mint on a
fresh pin" recovery) in §The two foundations would close it.

### F4 — The replica-set SAD kind is owed and not yet on the served-by-SAID list (low)

**Where:** `primitives/data/sad/availability.md`, `primitives/data/sad/kinds.md`,
`primitives/data/sad/shapes.md` (Forthcoming shapes).

`availability.replicas` is "the SAID of a replica-set SAD" that a verifier/store must **fetch by
SAID** to resolve the replication scope, and `availability.md` §Adversarial framing specifies
fail-secure resolution ("a replica set that cannot be resolved … MUST default to skip"). The
replica-set SAD's `kind` is explicitly **forthcoming** (`kinds.md` names it among the kinds "owed by
forthcoming encodes … land at the vdtid encode"; likewise the `shapes.md` Forthcoming-shapes table).
The one place it is **not** yet reflected is `kinds.md` §Fetch by SAID — the section that enumerates
exactly which kinds the store serves by SAID and then "**turns away everything else**." When the
replica-set kind lands it must be added there too, or `availability.replicas` resolution will
fail-secure (skip) by construction and silently narrow replication below the author's declared
scope. This is a **completeness note for the vdtid encode**, not a current defect — the fail-secure
default is the safe direction, and `kinds.md` already knows the kind is owed — but the
served-by-SAID allowlist and this resolvable-by-SAID field are the one forward-reference pair not
yet reconciled.

## What I verified holds (the positive record)

For a review whose main output is "no break found," the useful thing to record is **which
load-bearing arguments were actually stress-tested**, so a later reader knows the ground that was
covered rather than trusting an unqualified "looks fine." Each item below is a claim I tried to
break from the adversary's side and could not.

**The divergence / recovery core.**

- **Content forks are recoverable, sealed forks are terminal, and the line between them is the
  "accepted" (witnessed-at-threshold) sealed-branch count** — 0 → Forked, 1 → Active, ≥ 2 →
  Disputed, counted **per branch wherever the seals sit**. This is stated identically in
  `protocol-doctrine.md`, all three `log.md` / `merge.md` / `reconciliation.md` sets, and the
  glossary, and the "accepted ≠ merely witnessed" distinction (which is what makes Disputed require
  collusion) is used consistently — a past hazard that now reads clean.
- **Burial by position + ascent is growth-proof and needs no repair event or fork record.** The
  seal-cap locks a loser's first event; deadness-ascends kills its growth; a seal on a dead lineage
  is itself dead ("you can't seal a buried chain"). The retain-and-count vs. drop split (an
  _accepted_ competing seal is retained and counted → Disputed; a witness-declined or below-seal
  straggler is dropped, backdate-safe) is coherent across `merge.md` and `reconciliation.md` on all
  three chains.
- **The backdate defense** — a below-seal sealed straggler is first-seen-declined _and_ seal-cap
  dropped, so a harvested old reserve cannot fabricate a historical fork; the only reachable dispute
  is a live-tip seal collision needing a provable witness double-sign. The "clean seal retreats to
  `v_{d-1}` on a real dispute, fail-secure direction" argument holds.
- **The reserve defends the signing key, not the rotation key** — the three structural facts that
  make reserve theft a takeover with no in-band recourse (can't bury a `Rot`, the seal-cap blocks a
  recovery at `v_{N-1}`, a competing `Rot` at `v_N` is first-seen-declined) each check out.

**Witnessing and the federation.**

- **The witnessing floor `threshold > signers/2` forces quorum overlap**, and `select()` is pinned
  byte-exactly and keyed on position + as-of roster (never event bytes), so an attacker cannot mint
  sibling-specific witness sets within one federation. The one honest-witness dispute path (two
  rebinds naming disjoint federations) is correctly carved out and its author-side proof is
  consistent.
- **The federation minimum-roster arithmetic is internally exact.** At `|roster| = 4`: governance
  needs `t_govern = 3` (floor `> |roster|/2` meeting ceiling `≤ |roster| − 1`), witnessing needs
  `threshold = 2, signers = 3` (`threshold ≤ min(|roster| − 2, signers − 1)` and `> signers/2`). I
  confirmed `|roster| = 3` is genuinely _un-configurable_ for a federation (the floor and the cap
  cannot both hold), which is exactly why `|roster| ≥ 4` is required and a bare cut to 3 is rejected
  (forcing evict-and-replace, or a bare cut only from ≥ 5). No contradiction.
- **The currency gate + clock + wipe close the harvested-old-key forgery**, and the "an event stays
  witnessed forever, counted by re-deriving its then-current selection, never re-selected at the
  current tip" rule is stated the same way in `witnessing.md` and both verification docs.
- **The witnessed-time reduction** (the `threshold`-th-smallest receipt τ) is robust in the
  security-critical direction — the crossing cannot be pushed later by adding late receipts — and is
  correctly distinguished from the federation clock (no circularity, per-event granularity).

**The layering and the anchor model.**

- **The kind-strict anchor matrices agree everywhere** (KEL→IEL: content ← `Ixn`, tier-2 ← `Rot`,
  `Wit` ← `Wit`; IEL→SEL: `Ixn` ← `Ixn`, `Gnt` ← `Ath`, `Sea` ← `Evl`, kill `Trm` ← `Rev`/`Dth`),
  across `event-shape.md`, the three `events.md`, and the doctrine.
- **The SEL "witnesses itself" argument is sound** — an owner can equivocate its SEL under a linear
  owner IEL because an IEL anchor is an opaque SAID the IEL cannot dedupe, so fork-prevention must
  be the SEL's own first-seen; and **severance** (a dead owner-IEL anchor truncates the SEL,
  deadness first) composes with the SEL's own divergence exactly as `sel/reconciliation.md` Matrix 2
  claims — including "a Disputed SEL is never downgraded by severance, because its accepted sealed
  branches rest on accepted (never-buried) IEL anchors."
- **Policy is kept off the chain and evaluated as-issued**, the `del(X,N)` self-grant collapse is
  closed (an `Ath` naming its own delegator is rejected), the delegation walk is bounded (walk _up_
  the committed `delegationPath`, `MAXIMUM_DELEGATION_DEPTH`), and the set-packing distinctness rule
  fails toward _denial_, never a wrongful accept.
- **The credential accept conjunction is fail-secure**, the presentation-freshness envelope closes
  copy-replay within a single `grant` (nonce dedup + audience binding + committed-issuee signer),
  and "who may present" is a live `t_use` action correctly frozen on any divergence.

**Structural hygiene.**

- **The effective-SAID synthetic is a set-independent, verdict-coupled marker** (`forked` /
  `disputed`, keyed on the divergence ancestor, structurally distinct from any real SAID) — the
  right choice against an adversarially-extensible competing-branch set; value and verdict are both
  pure functions of held events, so convergence-once-propagated holds.
- **The mesh transport makes nonce reuse unreachable by construction** (per-direction keys +
  monotonic counter), authentication is witnessed-key-bound, and trust never rides the channel.
- **Every protocol constant is stated identically wherever it recurs** — verified by sweep
  (`MINIMUM_PAGE_SIZE = 129`, `MAXIMUM_UNSEALED_RUN = 64`, `MAXIMUM_ROSTER_SIZE = 32`,
  `MAXIMUM_MANIFEST_LIST = 128`, `MAXIMUM_DELEGATION_DEPTH = 8`, `MAXIMUM_SEL_LINEAGE = 64`,
  `MAXIMUM_GRANT_ADDS = 64`, `MAXIMUM_WITNESS_KEY_WINDOW = 365 days`,
  `CLOCK_TOLERANCE_BAND = 1 minute`).
- **`MODEL.md` and `USES.md` do not overclaim** relative to the design — the plain-English "no
  silent forgery" guarantee is correctly narrowed to exclude the reserve-theft takeover, and the
  crypto tiers (everyday ML-DSA-65 / ML-KEM-768; infrastructure ML-DSA-87 / ML-KEM-1024) are
  consistent across `residuals.md`, `mesh-transport.md`, `essr.md`, and the directory grant kinds.
- **Forward-references are correctly xref-ignored.** `substrate/infrastructure/vdtid.md` is
  genuinely forthcoming and listed on `.docs-xref-ignore` as an exact path (not a subtree glob), per
  the repo's own discipline; the docs that lean on it state the invariants it will enforce.

## Subtle spots I believe are sound but flag for a second look

These are **not** findings — I could not break them — but they are the most intricate arguments in
the design, so a second reviewer confirming them is worthwhile.

- **The `disputed` synthetic in a nested fork.** The `disputed` effective-SAID keys on "the
  **earliest** divergence carrying ≥ 2 accepted sealed branches," which the docs note "coincides
  with the first divergence **except in a nested fork**" (a fork within a fork). Two nodes should
  converge on the same value once they hold the same accepted sealed branches (the pre-convergence
  disagreement is the intended anti-entropy signal), but this is the single most intricate
  convergence claim and would benefit from an explicit worked example if one is ever added.
- **`region()` "seal your way out of a fork with any T2 act."** `iel/verification.md` generalizes
  the freeze rule to "a forked identity seals its way back to Active with any non-terminal T2 sealed
  act." The soundness argument (what a seal-out buries is the T1 content loser, and no T1 actor
  holds a T2 quorum) holds and matches `merge.md`'s burying-seal recovery — but the generalization
  from "the resolving `Evl`" to "any `Ath` / `Rev` / `Dth` / `Wit`" is worth keeping an eye on as
  the feature encodes land, since an `Ath` / `Rev` seal-out also performs its grant / kill side
  effect.

## Closing

This is a mature, unusually well-cross-checked design. On the two axes asked for — soundness and
consistency — it holds: the adversarial arguments defend at the algorithm / primitive level, the
fail-secure defaults point the right way, and the documents agree with each other on the rules,
fields, and constants they share. The items above are refinements, not repairs. **F1** is the only
one I would call load-bearing, and it is a _forthcoming-encode_ invariant (keep a keyed group's two
member sets in lockstep) rather than a defect in the current text; the rest are a one-line
cross-reference (**F3**), a glossary phrasing tweak (**F2**), and a served-list reconciliation to
land with the storage encode (**F4**).
