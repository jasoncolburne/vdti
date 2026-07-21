# Fable design review — 2026-07-21, round 1 — resolution

Companion to [`fable-max-design-review_2026-07-21_1.md`](fable-max-design-review_2026-07-21_1.md).
It records what we did about each finding — what changed, where, and why. It was written after
working the findings all the way through, so it reflects the corrected understanding rather than the
first read, and it is honest about one wrong turn we took and undid along the way.

## The headline (3.1): one event set, two readings — we picked one and swept it

3.1 was the one real hole. Take a chain where, at the same position, there is a **seal** (a key
change) and a competing **content** event. The design read that pair two different ways in two
different places: some documents buried the content under the seal and read the chain **Active**
(one event, done); others left the pair as a live fork (**Forked**) that needed a second, later seal
to resolve. Same held events, two answers — and because the design promises every node computes the
same state from the same events, that is a correctness bug, not a wording nit. It sat in the
reconciliation matrices, which are the documents that are supposed to _prove_ the design converges.

**The decision (Model I): a content event beside a seal is buried — the chain reads Active,
whichever order the two arrived in.** A seal buries content at its own position exactly as it buries
content below it; the losing content is dead on ascent. A content event landing beside an
already-established seal cannot form honestly at all — it is a structural non-event — and if a
colluding witness set mints one anyway, it is buried the same way. We cannot see the order events
actually landed in, so we never read that pair as a dispute; the seal simply wins.

The precise reading, now stated the same way everywhere:

- **Forked** = a **content-only** fork — two competing content events, no accepted seal.
  Recoverable: a burying seal-advancer on the winning branch buries the content loser and the chain
  re-reads Active.
- **A single accepted seal buries the content → Active.** A fork that already carries its burying
  seal is not a live fork; it has recovered.
- **Two or more accepted seals → Disputed** — terminal, reincept.

This replaced the old "≤ 1 sealed branch = Forked" shorthand, which blurred the one-seal case
(really Active) with the no-seal case (really Forked). We swept the sharper reading through all
three correctness proofs (the seal-sibling cases, the state tables, invariants 2/4/5), the
merge-layer routing in all three primitives (a content-burying seal is a **recovery**, not a fork —
it was routing to Forked in one place while the same document's recovery section buried it), the
per-node state tables and the state-machine diagram, the verifier's region reading, the glossary,
the system thesis, the doctrine, and the machine-readable canon (`vdti-area-kel.md`). A search for
the old phrasing comes back empty.

**This also corrected a wrong turn from round 0.** The round-0 pass had encoded disputes as forming
_across_ positions ("past the fork") — a content-led branch that seals, meeting a burying seal that
cannot drop it. Under Model I that branch is buried before it can ever seal, so a dispute is
**same-position**: two accepted seals at one serial. We reverted the "past the fork" encoding back
to same-position throughout, and kept the two round-0 pieces that are still correct:

- **The cross-federation rebind is the one honest-witness dispute.** Two rebinds at one serial
  naming **different** federations select **disjoint** witness sets, so each is honestly accepted by
  its own federation and both reach threshold with no witness signing twice. That is still a genuine
  dispute; its proof is the author revealing one rotation reserve on both branches, not a witness
  double-sign.
- **The misbehavior proof is computed from the evidence, not asserted as a rule.** A verifier reads
  which proof a dispute carries (`confirmed_witness_double_sign` /
  `confirmed_reserve_double_reveal`); when neither is confirmable it still reads Disputed and
  reports the cause as unconfirmed (fail-secure). Attribution decides only forensics — who to evict
  versus who to walk away from — never whether to reincept.

**3.2 folded into this same edit.** Invariant 5 in the KEL proof contradicted its own formula (it
called a seal-sibling "not in the locked portion" while the formula it restated rejected it). We
restated the locked-portion bound as three clean cases by where the parent sits: two-or-more below
the seal → inert; exactly one below (a sibling of the seal) → content buried/Active or a second seal
→ Disputed; at-or-above → a clean extension.

One change worth your eye, because it touched key-takeover semantics: the verifier's region reading
said "a lone sealed branch you did not author reads Forked." Under Model I that lone seal buries the
content and reads **trusted** (clean on-chain) — a reserve-theft takeover is silent, caught by owner
vigilance and answered out-of-band by reincept, exactly as the canon already says. We aligned the
reading to the canon.

## 4.2 (genesis consent): conformed to the canon — every founder anchors

The review found two readings of who authorizes an inception: "all founders" (the taxonomy) versus
"a threshold of the founders" (the bootstrap doc). We first folded a third model invented mid-
conversation — a split where a quorum reveals rotation reserves and the rest sign lightly — then
checked the canon and undid it. **The canon is unambiguous: at an inception, every founder / initial
member anchors with a rotation (tier 2).** All-consent is the anti-conscription rule — no device
lands in a founding roster it never signed — and the light-signature path belongs only to a member
_joining_ an existing roster, never to an inception. So the taxonomy was right; the bug was the
bootstrap doc undercounting. We fixed the bootstrap doc up to "all founders' rotations anchor the
inception," restored every other genesis site to "all members/founders anchor at tier 2," and left
the canon as the source of truth it already was.

## Every finding, and what we did

| #   | Sev  | Disposition                                                                                                                                                                                                                                                                          |
| --- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 3.1 | HIGH | **Folded** — chose Model I (content beside a seal → buried → Active); swept the reading + merge routing across all three primitives, doctrine, canon.                                                                                                                                |
| 3.2 | MED  | **Folded** into 3.1 — invariant 5 restated as three parent-position cases; the self-contradiction is gone.                                                                                                                                                                           |
| 4.1 | MED  | **Folded** — stated once (`kel/verification.md`) that an accepted event commits its whole ancestry, and reconciled it with "no sub-threshold event is counted as a competing branch."                                                                                                |
| 4.2 | MED  | **Folded** — conformed to the canon (every founder anchors at tier 2); fixed the bootstrap doc's undercount up.                                                                                                                                                                      |
| 3.3 | LOW  | **Folded** (round-1) — `anchors` stated as a strictly-ascending set, not "ordered."                                                                                                                                                                                                  |
| 3.4 | LOW  | **Folded** (round-1) — `pins` described as the members' **prior** KEL tips, not a hash cycle, in both catalogues.                                                                                                                                                                    |
| 3.5 | LOW  | **Folded** (round-1) — the `{X, X} → terminal` sentences now say **accepted**.                                                                                                                                                                                                       |
| 3.6 | LOW  | **Folded** — the "two independent authorings dedupe" example is corrected: events carry `pins`, so independent re-seals are byte-distinct and collide; only the same authoring redelivered dedupes.                                                                                  |
| 3.7 | LOW  | **Folded** (round-1) — "severance downgrades a Disputed" corrected to **cannot** (the case is unreachable — an accepted sealed branch's anchor is never buried).                                                                                                                     |
| 3.8 | LOW  | **Folded** — named the enforcement point for "≤ 1 content event per anchoring event": the SEL verifier dedupes on the resolved anchor.                                                                                                                                               |
| 3.9 | LOW  | **Folded** (round-1) — the SEL seal-cap "dedupe" sentence got the same "accepted" + pins corrections as 3.5/3.6.                                                                                                                                                                     |
| 0.1 | LOW  | **Folded** (round-1) — the threshold-vector gloss reordered to `content, authorization, governance`.                                                                                                                                                                                 |
| 0.2 | LOW  | **Folded** — `prefix ≠ said` stated as overwhelming probability (collision resistance), not certainty; and neither value computes from the other.                                                                                                                                    |
| 1.1 | LOW  | **Folded** — `said.md` now states the consequence: a `said` key in app payloads makes them unverifiable; app content rides as opaque bytes / a blob.                                                                                                                                 |
| 1.2 | LOW  | **Folded** (round-1) — the second threshold-vector gloss (in `shapes.md`) reordered to match 0.1.                                                                                                                                                                                    |
| 1.3 | LOW  | **Folded** — renamed the four witness-receipt JSON fields to `camelCase` (`chainPrefix` / `eventSaid` / `eventSerial` / `witnessPrefix`) to match every other SAD shape (convention: JSON = camelCase, Rust = snake_case; `witnessing.md`'s `select()` pseudocode stays snake_case). |
| 1.4 | LOW  | **Folded** — `availability.md` now carries the "operational, not verifiable" caveat on TTL, matching one-shot.                                                                                                                                                                       |
| 2.3 | LOW  | **Folded** — "at least two signers" qualified "where configured" (`t_use = 1` is legal).                                                                                                                                                                                             |
| 7.1 | LOW  | **Folded** — the chat open-epoch gap stated honestly as an accepted, self-harming residual, with the option to add mail's future-side bound noted.                                                                                                                                   |
| 2.1 | HIGH | **Subsumed** by 3.1 (the review flagged it as the doctrine-layer view of the same contradiction).                                                                                                                                                                                    |
| 2.2 | MED  | **Subsumed** — the reviewer folded it into 3.4 on reading the owning document.                                                                                                                                                                                                       |
| 2.4 | LOW  | **Skipped** — moot after the revert to same-position disputes; "past the fork" is no longer used as a load-bearing phrase.                                                                                                                                                           |

## Verification

`make all` passes — terminology 0, cross-references 0 errors, prettier clean. A search for the old
Model-II phrasings (`≤ 1 sealed = Forked`, `first sealed branch → Forked`, `mixed race`,
`recovers by extending`) comes back empty across both the design docs and the canon.
