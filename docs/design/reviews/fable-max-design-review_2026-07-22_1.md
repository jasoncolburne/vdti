# Design review — Fable (max), 2026-07-22, pass 1 (cold)

> please read the design documents in this repository and provide a comprehensive review focused on
> correctness/soundness and consistency. the natural entrypoint is ./README.md - start there for a
> high level overview and proceed to docs/design/README.md for reading order. produce a document
> named docs/design/reviews/fable-max-design-review_2026-07-22_1.md. create it iteratively and
> continue to edit throughout this task, since the fable model may be flagged and this will retain
> fable thinking and results. place this prompt, verbatim, at the top of the file as a quote (>).
> the document should not use jargon and have clear voicing. it should be broken into logical groups
> for easy digestion. when you finish create a summary table of the findings, above their details.
> ignore the existing files in docs/design/review. use scripts/grep-terms.pl to search through
> decoration and line breaks.

**Reviewer:** Claude (Fable 5, max effort), cold pass — no prior context from the design sessions,
reading only the current files. **Date:** 2026-07-22. **Scope:** every document under `docs/design/`
in the reading order given by `docs/design/README.md`, plus the root `README.md`, `MODEL.md`, and
`USES.md` where they make claims the design must back. Existing review files under
`docs/design/reviews/` were not read. **Axes:** correctness/soundness (does the mechanism do what
the document claims, under an adversary) and consistency (do the documents agree with each other).

**How findings are labeled.** Each finding gets a severity:

- **Critical** — a soundness break: the mechanism as written does not deliver the property the
  design claims, and an attacker or ordinary operation can exploit the gap.
- **High** — a real hole in the argument or a contradiction between documents that would mislead an
  implementer into building something unsound.
- **Medium** — the design is likely sound but the text under-specifies or conflicts in a way that
  two implementers would resolve differently.
- **Low** — drift, stale phrasing, or a small gap that does not threaten soundness.
- **Note** — an observation worth recording; no change strictly required.

**Status: review in progress.** Findings are appended per layer as reading proceeds; the summary
table is added last, once all layers are read.

## Headline

The core design is sound. Reading every document under `docs/design/` adversarially — the data
substrate, the cross-cutting doctrine, all three event-log primitives (KEL / IEL / SEL) and their
correctness-proof matrices, the federation and witnessing layer, the policy layer, and the six
protocol primitives — I found **no soundness break and no contradiction in the core**. The chain
machinery, the seal/divergence/recovery rules, the tier model, the kind-strict anchoring, and the
witnessing floor all hold together and agree across the documents that describe them. The constants
(`MAXIMUM_UNSEALED_RUN = 64`, `MINIMUM_PAGE_SIZE = 129`, `MAXIMUM_ROSTER_SIZE = 32`,
`MAXIMUM_SEL_LINEAGE = 64`, `MAXIMUM_MANIFEST_LIST = 128`, `MAXIMUM_DELEGATION_DEPTH = 8`, the
365-day witness window, the 1-minute clock band) are identical at every appearance.

The findings below sit at the **seams** — the feature and cross-cutting layers where the primitives
compose. Two are genuine gaps worth closing before the affected features are built; two are minor
consistency nits. None is a break in the verified core.

## Summary table

| #   | Severity   | Area                                   | Finding (one line)                                                                                                                                                                                                                                                                                |
| --- | ---------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Medium     | Delegation (`del(X, N)`), policy + IEL | Multi-hop delegation needs the verifier to walk _up_ from the presented party to the root, but the on-chain delegation marker only commits a _downward_ reference, and no document shape carries the intermediate path — so the up-walk is unspecified for `N ≥ 2`.                               |
| 2   | Medium     | Effective-SAID, cross-cutting          | For a **nested** fork, the `disputed` synthetic is specified to key on "the earliest divergence carrying ≥ 2 sealed branches," but the verification token's `divergence_ancestor` is defined as the **first** divergence — the token exposes a different value than the synthetic is told to use. |
| 3   | Low        | Membership / shared-documents          | `MAXIMUM_GRANT_ADDS = 64` is stated only in `shared-documents.md`, not in the `membership` primitive whose `{grants, rescinds}` delta it bounds — so `chat-membership`'s add-list has no documented cap.                                                                                          |
| 4   | Low / Note | README ↔ residuals                    | The README pitches logs and event-sourcing as "free," but a plain content log owned by a multi-device identity must run a governance-tier (`t_govern`) re-seal every 64 events — a recurring cost only surfaced in `residuals.md`.                                                                |
| 5   | Note       | Policy evaluation                      | The distinct-identity counting under `thr`/`wgt` is an assignment search (set-packing) — correctly bounded, fail-secure, and non-consensus-critical, but the implementation should budget for it. Verified sound.                                                                                 |
| 6   | Note       | Witnessed time                         | An event's witnessed time is not per-verifier-identical across verifiers holding different receipt subsets — the security-critical "cannot be pushed later" direction is sound, but the value is not a single canonical timestamp. Verified sound.                                                |

**Scope note.** This pass covered every file under `docs/design/` plus the root `README.md`. The
root-level `MODEL.md` and `USES.md` (user-facing summaries) were read only where they bear on a
design claim, not audited line-by-line; if they restate protocol rules, a quick consistency pass
against them is worth doing separately.

## Reading log

- [x] Layer 0 — orientation: `system-thesis.md`, `glossary.md`
- [x] Layer 1 — data substrate: `sad.md`, `said.md`, `custody.md`, `availability.md`,
      `compaction.md`, catalogues (`kinds.md`, `shapes.md`, `tags-and-topics.md`)
- [x] Layer 2 — doctrine: `protocol-doctrine.md`, `residuals.md`, `monitoring.md`
- [x] Layer 3 — event logs: `event-shape.md` ✓; KEL (6 docs) ✓; IEL (6 docs) ✓; SEL (5 docs) ✓
- [x] Layer 4 — federation: `bootstrap.md`, `witnessing.md`, `topics.md`, `mesh-transport.md`
- [x] Layer 5 — policy: `policy.md`, `documents.md`, `evaluation.md`
- [x] Layer 6 — protocol primitives: `essr.md`, `ipex.md`, `receive-key-directory.md`,
      `group-key.md`, `membership.md`, `authored-dag.md`
- [x] Layer 7 — features: `credentials.md`, `exchange.md`, `shared-documents.md`

_Layers 0–2 read as internally consistent and unusually rigorous; no findings raised there on their
own. A handful of cross-layer claims to re-check against the primitives that own them are tracked
inline as I read layer 3 onward (e.g., the constants `MAXIMUM_UNSEALED_RUN = 64`,
`MINIMUM_PAGE_SIZE = 129`, `MAXIMUM_ROSTER_SIZE = 32`, `MAXIMUM_SEL_LINEAGE = 64`; the content-SEL
re-seal cost vs. the "logs, free" framing; the federation witness-config bounds)._

## Findings — detail

### 1 — Multi-hop delegation: the up-walk has no committed path to follow (Medium)

**Where:** `primitives/policy/policy.md` (`del(X, N)` leaf), `primitives/policy/documents.md`
(§Delegation in a document), `primitives/data/event-logs/iel/verification.md` (§The bounded
delegation walk), `primitives/data/event-logs/iel/delegation.md`, and the delegation-marker shape in
`primitives/data/sad/shapes.md` / `primitives/data/event-logs/sel/events.md`.

**The mechanism as written.** Answering `del(X, N)` — "is the presenter a live delegate of X within
N hops?" — is done by walking **up** from the presented party toward X, one hop at a time. The
design is explicit that it must be an up-walk and **not** a walk down from X, because X's transitive
delegate set fans out and is unbounded (`iel/verification.md` §The bounded delegation walk). Each
hop is a delegating-link lookup SEL whose address is derived from
`(delegator, delegation-topic, delegate)` and which lives **on the delegator's own chain**
(owner-rooted).

**The gap.** To take one step up — from a delegate `E` to whoever delegated to it — the verifier has
to compute the address `derive(D, topic, E)`, which requires knowing the delegator `D`. But the only
thing the on-chain delegation marker commits is a **downward** "blinded reference to the delegate."
Three documents state this identically:

- `shapes.md`: the `vdti/sel/v1/grants/delegation` marker "commits a **blinded reference to the
  delegate**."
- `sel/events.md`: "a `vdti/sel/v1/grants/delegation` marker committing a blinded reference to the
  delegate."
- `iel/delegation.md`: "it commits a **blinded reference to the delegate**."

So the marker tells you who the delegate is (which you already know — you are standing on it); it
does **not** tell you who the delegator is. There is no upward pointer to compute the next hop's
address from.

`documents.md` papers over this by asserting the link is "**committed on the delegator's own
identity** … and **pinning up to X**, so the verifier **derives** the authorizing chain from
committed data and walks it — **the presenter furnishes nothing to prune**." Two problems:

1. "Pinning up to X" is stated but nothing carries an up-pin — the marker's only committed reference
   is downward (to the delegate). The two statements contradict.
2. "The verifier derives the authorizing chain from committed data" and "the presenter furnishes
   nothing to prune" together mean the ordered path (the intermediate delegator prefixes) is neither
   presented nor derivable from a downward-only marker. No document shape — not the credential
   (`credentials.md` / `shapes.md`), not the IPEX `grant`, not the version SAD — defines a field
   that carries that path.

**Why single-hop is fine and multi-hop is not.** For `del(X, 1)` the verifier knows **both**
endpoints: X from the relying party's own policy, and the issuer (the direct delegate) from the
credential's `issuer` field. It derives `derive(X, topic, issuer)` and checks the one hop — no path
needed. The gap bites only at `N ≥ 2`, where the middle delegators are neither in the policy nor in
the credential and cannot be recovered from a downward-only marker.

**Failure scenario.** A relying party's policy is `del(root, 3)`. A credential arrives whose issuer
is three hops below `root`. The verifier holds `root` and the issuer prefix but has no way to learn
the two intermediate delegator prefixes, so it cannot compute the two middle delegating-link
addresses, cannot confirm those hops were granted (or check them for rescission), and cannot
complete the up-walk. Either the whole multi-hop leaf is unbuildable, or an implementer invents an
undocumented path field — and two implementers will invent different ones.

**Suggested resolution.** At the delegation-feature encode, pin exactly where the authorizing path
is committed and reconcile the two descriptions: either (a) define a document/credential field that
carries the ordered delegator prefixes the verifier verifies hop-by-hop (making "the presenter
furnishes nothing to prune" mean "the committed path is fixed, not chosen at presentation"), or (b)
give the delegation marker a committed **upward** reference (to the delegator / the next link up) so
the up-walk is genuinely derivable, and fix `shapes.md` / `sel/events.md` / `iel/delegation.md` to
say so. Today's "downward reference to the delegate" and `documents.md`'s "pinning up to X" cannot
both be the whole story.

### 2 — Nested-fork `disputed` synthetic keys on a value the token does not carry (Medium)

**Where:** `primitives/data/event-logs/tags-and-topics.md` (the `forked`/`disputed` synthetic
derivation), against `primitives/data/event-logs/kel/verification.md` and `iel/verification.md` (the
`divergence_ancestor` token field), with the cross-cutting statement in `protocol-doctrine.md`
§Effective-SAID comparison.

**The two statements.** The effective-SAID synthetic for a diverged chain is
`hash('{tag}:{prefix}:{position}')`, and the design is emphatic that every node must compute the
identical value:

- `tags-and-topics.md`: `{position}` "is the SAID of the fork point: the verification token's
  `divergence_ancestor` for **both** `forked` and `disputed` (the divergence, not the seal positions
  … **for a nested fork it is the earliest divergence carrying ≥ 2 sealed branches**)."
- `kel/verification.md`: the verifier records `divergence_ancestor (the SAID of v_{d-1})` **"if
  first divergence,"** and the token field is documented as "SAID of `v_{d-1}` on a divergent
  chain." `iel/verification.md` matches.

So `tags-and-topics.md` says the `disputed` synthetic keys on **the earliest divergence carrying ≥ 2
sealed branches**, and _also_ says it keys on `divergence_ancestor` — while the token defines
`divergence_ancestor` as **the first divergence on the chain**. For an ordinary (single) fork these
coincide. For a **nested** fork they can differ: if the first divergence is content-only (0 sealed,
a `forked` sub-state that formed under witness compromise) and a _deeper_ divergence carries the two
accepted sealed branches, then "first divergence" (what the token exposes) ≠ "earliest divergence
carrying ≥ 2 sealed branches" (what the synthetic is told to use). The token exposes no separate
field for the latter.

**Failure scenario.** A witness-compromise content fork forms at serial _d_ (both branches content,
reads `forked`); deeper, on one branch, two rotations both reach threshold at serial _d′ > d_ (reads
`disputed`). The design's own "nested fork" clause says the `disputed` synthetic's `{position}` must
be _d′_ (the earliest ≥ 2-sealed divergence). But an implementer building `effective_said()` from
the token has only `divergence_ancestor = d` available. If one implementation reads the
`tags-and-topics.md` rule (uses _d′_) and another reads the token field (uses _d_), the two compute
**different** `disputed` synthetics for the same event set — a violation of the cross-node
determinism the whole effective-SAID story rests on.

**Impact is bounded, but it is a real internal contradiction.** Because both synthetics still carry
the `disputed` type tag and so differ structurally from any real SAID, anti-entropy still fires —
the worst case is an extra fetch round / the "cross-implementation encoding drift" that
`residuals.md` already rates Low. Reachability requires a compound compromise (a content fork
_above_ a sealed dispute). But the design repeatedly calls this value determinism-critical and
set-independent _precisely so_ every node agrees, and here two authoritative docs disagree about
which divergence it keys on, with the token unable to supply the value one of them names.

**Suggested resolution.** Reconcile the two docs. Either (a) define the `disputed` synthetic to key
uniformly on `divergence_ancestor` (the first divergence) and drop the "earliest divergence carrying
≥ 2 sealed branches" clause — simpler, and the first divergence is already a data-local invariant
every node computes identically; or (b) if the deeper anchor is deliberate, add a distinct token
field (e.g. `disputed_divergence_ancestor` = the earliest divergence with ≥ 2 accepted sealed
branches), have the `disputed` synthetic use it, and state that the `forked` synthetic uses
`divergence_ancestor` while the `disputed` one uses the new field. Right now the token and the tag
derivation cannot both be right for a nested fork.

### 3 — The grant add-list cap lives in the wrong doc (Low)

**Where:** `features/shared-documents.md` introduces `MAXIMUM_GRANT_ADDS = 64` ("a grant event's
add-list totals at most that many entries, enforced as the verifier accumulates the event's adds and
bails the instant it breaches"). It appears **nowhere else** in `docs/design/`.

**The issue.** The `{ grants, rescinds }` membership-delta is the `membership` primitive's shape
(`primitives/protocols/membership.md`), shared by all four instances — the three
`document-*-membership` sets **and** `chat-membership`. The verifier-work bound on how many adds one
grant event may carry is a property of that shared shape, but it is stated only by one consumer
(shared documents). `membership.md` describes the delta with no cap, and a `chat-membership` grant's
add-list therefore has no documented bound — the same accumulation DoS the constant exists to stop
is left unbounded for the chat instance.

**Suggested resolution.** State `MAXIMUM_GRANT_ADDS` (or the general "a grant delta's add-list is
capped, verifier bails on breach" rule) in `membership.md`, the primitive that owns the delta shape,
so every instance inherits it; keep the shared-documents mention as a back-reference. Confirm the
cap is intended to apply to `chat-membership` too.

### 4 — "Logs, free" under-states an acknowledged recurring governance cost (Low / Note)

**Where:** `README.md` line 19 ("**Logs** — single-owner, append-only, tamper-evident. Audit trails
and event sourcing, free.") against `residuals.md` §Ranked summary → "Roster / seal caps."

**The issue.** The seal-advance cap is unconditional on the SEL: a content log must land a
seal-advancer at least every `MAXIMUM_UNSEALED_RUN = 64` content events. A plain content log has no
natural `Gnt` or `Trm`, so its only seal-advancer is a `Sea`, which is anchored by an owner-IEL
`Evl` priced at **`t_govern`**. For a single-device owner (`t_govern = 1`) that is cheap; for a
multi-device identity it is a **governance-quorum ceremony every 64 events**. `residuals.md` states
this honestly ("a plain content log's periodic re-seal is priced at governance tier … a high-volume
log recurs that ceremony every 64 content events — a deployment planning one should budget the
cadence"), but the README's headline framing and the "logs / event sourcing, free" pitch give no
hint of it — and a high-volume audit log is exactly the use case that framing targets.

This is a marketing-vs-reality consistency nit, not a soundness issue. The mechanism is correct and
the cost is acknowledged where it counts. Worth either qualifying the README claim ("free to build;
a high-volume log budgets a periodic re-seal") or consciously accepting the shorthand.

## Notes — checked and sound (recorded so the read is auditable)

These are places a cold review is expected to probe; I confirmed each is sound and flag only what an
implementer should budget for.

- **Distinct-identity counting is an assignment search.** `policy.md`'s rule that a signer fills at
  most one branch of a `thr`/`wgt` (with quorum sub-policies) makes satisfaction a set-packing /
  matching search, not a greedy pass. The design handles this correctly: the search is bounded by
  the verifier-wide work budget, **denies fail-secure** on budget exhaustion (so two verifiers can
  differ only toward denial, never toward a wrongful accept), and is explicitly **not**
  consensus-critical (each relying party evaluates its own policy). Sound — but the encode should
  budget the search and document the bound, since a deep/wide policy is where it bites.

- **Witnessed time is not a single canonical value across verifiers.** `witnessing.md` §An event's
  witnessed time is candid that with `signers > threshold`, a verifier holding only the _latest_
  `threshold` receipts computes a _later_ crossing than one holding the earliest, and that a
  receipt-curating (eclipse-class) adversary can inflate a computed boundary by the honest receipt
  spread. The security-critical direction — the crossing **cannot be pushed later** past the durable
  honest receipts, so a stale key can never read current — is argued correctly and holds. Recorded
  only because an implementer might otherwise assume a single deterministic timestamp; it is a
  bounded interval, fail-secure, and that is by design.

- **Other load-bearing seams read against their adversary and found sound:** severance never
  downgrading `Disputed` (accepted sealed branches rest on accepted, never-buried IEL anchors); the
  `content: true` biconditional making a content squat at a lookup address unconstructable; the
  honored-window predicate `F_x ≤ V_x ≤ B_x` being intra-chain, append-only, and backdate-proof both
  ways; the ESSR two-binding shape and the IPEX single-signature double-duty (ownership +
  freshness); the federation bootstrap non-circularity (trust roots in the config-pin, not a receipt
  count); the witnessing floor / fork-cost / first-seen composition; and the chat-lane
  `[anchored root … bound]` interval check that closes a removed member's backdate structurally. No
  findings.

## Closing assessment

VDTI's core is in strong shape: the substrate, doctrine, and the three event-log primitives form a
single interlocking system whose documents agree with each other and whose adversarial arguments
hold. The two Medium findings are both at the **delegation** and **effective-SAID nested-fork**
seams — features/edges where the composition rules outran the shape/token definitions — and both are
fixable by pinning a commitment location and reconciling two documents, not by re-opening the core.
The two Low items are hygiene. I would treat findings 1 and 2 as blockers for the delegation feature
and for a conformant multi-implementation effective-SAID, respectively, and 3 and 4 as clean-up.
