# trace — track-and-trace provenance

`trace` is an item's history across organizations that do not trust each other: food, pharma, luxury
goods, evidence — each actor recording its leg, each hand-off attested by both sides, the whole
chain verifiable end-to-end with no central tracker. It is the composition case for **credentials
plus logs plus exchange**, and it absorbs the catalogue's same-composition variants: **chain of
custody** (legal evidence, lab samples, cold chain) and **drug supply-chain provenance** are this
application with the nouns changed.

## The composition

The passport fixed one honest edge: a single-owner log has one custodian for life, so it makes a
registry, not a relay baton ([`passport.md`](passport.md)). `trace` is the shape for the baton —
**no shared log exists at all**; the chain of custody is a chain of cross-referenced acts on the
participants' own chains:

- **Each actor keeps its own leg.** A custodian records what it did with the item — received,
  stored, processed, shipped — on its **own** ledger (a content SEL it owns, the `ledger`
  composition per participant — [`ledger.md`](ledger.md)). Nobody writes on anyone else's chain, so
  no shared-write machinery is needed or invented.
- **A hand-off is a pair of credentials.** The sender issues a release attestation — item,
  time-bracket, condition, the receiver's identity — and the receiver issues an acceptance
  attestation naming the release by SAID (the plain-reference edge). Each is anchored on its
  issuer's own chain
  ([`../features/credentials.md` §Edges / chaining](../features/credentials.md#edges--chaining)).
  The item's custody chain is the alternating sequence of these pairs: release → acceptance →
  release → acceptance, each link a two-sided, independently-anchored commitment neither party can
  later deny or alter.
- **Exchange moves the dossier with the item.** At each hand-off the sender delivers the item's
  accumulated dossier — the prior attestations and leg records — sealed to the receiver
  ([`../features/exchange.md`](../features/exchange.md)), so the next custodian holds everything it
  needs to verify what it accepted, and the business relationship stays off any shared surface: the
  graph is visible to the parties and their chosen nodes, not to a platform.
- **A verifier walks the chain of pairs.** Handed the final acceptance, an auditor resolves each
  attestation against its issuer — anchored, unrevoked, fresh — and follows the reference edges back
  to origin. Authority composes where the domain has it: a certified carrier's attestation carries
  its accreditation path; a recall is the maker's cohort revocation striking every downstream check
  at once ([`permit.md`](permit.md)).

## Scenarios

- **A cold-chain leg.** The carrier's own ledger records temperature attestations on its leg; the
  acceptance credential at delivery commits the leg's summary. A break in the chain is either
  recorded (and permanent) or a refusal to attest — and a missing acceptance is exactly what the
  next buyer's verification surfaces.
- **Evidence custody.** The absorbed legal case verbatim: every transfer double-attested, every gap
  visible as a missing pair, no clerk able to rewrite the book afterward — the property courts
  currently establish by testimony carried instead by structure.
- **A recall.** The manufacturer revokes the lot's credentials; every custodian's next fresh check
  fails secure, wherever the goods are, with no notification infrastructure beyond the chains
  themselves.
- **An audit years later.** Every attestation still verifies from any source — issuers' chains are
  append-only and witnessed — and standing is read live: an attestor since discredited shows as
  revoked exactly as the passport's read prescribes.

## What this validates

- **Three features compose with nothing invented.** The hand-off pair is plain credentials; the legs
  are plain ledgers; the delivery is plain exchange. The catalogue's heaviest multi-feature entry
  decomposes entirely into landed machinery — the strongest evidence yet for the composition thesis.
- **Cross-organization truth without a platform.** No consortium database, no operator whose
  compromise rewrites history, no member whose exit strands the data — each party owns its own
  records and the item's story is the verifiable seam between them.
- **Two-sided attestation is the right primitive for custody.** A transfer neither party can
  unilaterally assert or deny falls directly out of paired issuance — no escrow, no countersigning
  ceremony, no shared document needed.

## Limits

- **The physical binding is out of band** — the passport's limit, compounded by motion: that the
  crate scanned is the crate attested rests on identifiers and seals structure cannot secure.
- **Omission is the honest gap.** A custodian who never attests leaves a hole; the composition makes
  the hole **visible** (the pair chain breaks) and non-repairable-in-hindsight, but it cannot force
  diligence — the ledger's omission limit, at supply-chain width.
- **Graph privacy is scoped, not absolute.** The parties to a hand-off and their chosen nodes see
  that leg; regulators see what they are handed. What the composition removes is the central tracker
  that sees everything — not the counterparty's knowledge of its own trades.
