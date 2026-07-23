# permit — licensing and permits

`permit` is authority issued, verified, and withdrawn: a driving licence, a food-service permit, a
building consent — issued by an authority, held by the licensee, checked by anyone, revocable at the
issuer's word. It is the composition case for **credentials alone**, chosen because a licensing
system exercises the whole credential lifecycle — issue, verify, delegate, disclose selectively,
renew, revoke — in one application. It absorbs the catalogue's largest same-composition family
(below).

## The composition

- **A licence is a targeted credential.** The authority is the `issuer`, the licensee's identity the
  `issuee`, the licence class and conditions the `claims`, and issuance is the anchor on the
  authority's own chain — witnessed, positioned, revocable in place
  ([`../features/credentials.md` §The two foundations](../features/credentials.md#the-two-foundations)).
  Cohorts issue in bulk where linkage is harmless and singly where it is not, the feature's stated
  trade.
- **A check is the acceptance conjunction.** A roadside inspector, a venue, a counterparty — each
  runs the same fail-secure sequence: integrity, valid issuance at the pinned anchor, issuer trusted
  (the checker's list), fresh to the tip, **not revoked**, owned by the presenter live, not expired
  ([`../features/credentials.md` §Accepting a presented credential](../features/credentials.md#accepting-a-presented-credential)).
  Authenticity needs no network; the freshness and revocation reads are the one online leg, with the
  fail-open lookup as the checker's own availability trade.
- **Suspension and revocation are the kill.** The issuer declares the credential's derived
  revocation target on its own chain; every fail-secure check in the world turns the licence away
  from that moment, and no one — not the licensee, not a compromised verifier — can un-declare it
  ([`../features/credentials.md` §Revocation](../features/credentials.md#revocation)). Restoring a
  suspended licence is a re-issue: a fresh credential, the old one dead — strikes are additive and
  final, which is what makes them trustworthy.
- **Delegated issuing authority is the edge machinery.** A national authority accredits regional
  offices; a licence issued by an office carries the committed delegation path, and acceptance walks
  it — authority is derived by the verifier, never asserted by the office
  ([`../features/credentials.md` §Edges / chaining](../features/credentials.md#edges--chaining)).
  Rescinding an office's accreditation cuts future issuance without unwinding what it validly issued
  before the bound — the grandfather semantics a real licensing hierarchy needs.
- **Conditions disclose selectively.** The claims carry issuer-precomputed brackets — the age
  brackets, the licence-class booleans, the endorsement flags — so a check learns exactly the
  boolean it asks for and nothing else
  ([`../features/credentials.md` §Claim-gating](../features/credentials.md#claim-gating)). Renewal
  re-issues with fresh nonces: unlinkable across renewals, the bracket set extensible with no
  protocol change.

## The absorbed family

Nine catalogue entries are this application with the nouns changed, and each maps to a lifecycle
corner `permit` already exercises:

- **Age / identity verification** — a claim-gated check (`ageGTE18`, disclosed alone) against a
  government-issued credential; the offline-verify posture is the licence check with the network leg
  deferred.
- **Travel documents** — a licence held by the traveler: authenticity offline, revocation from a
  fresh read of the issuer's chain, from any source.
- **Prescriptions** — a licence to dispense once: issued to the patient, revoked by the issuer on
  fill (the single-use discipline; a pharmacy that must dispense before confirming is the fail-open
  trade, priced consciously).
- **Recall management** — revocation at cohort width: the issuer strikes a batch's credentials and
  every holder's check fails secure, everywhere, at once.
- **Certificate of authenticity** — the maker as issuer, the item's description as claims; often a
  bearer instrument where transfer-by-copy is the point and redemption-as-revocation closes reuse
  ([`../features/credentials.md` §Targeted vs bearer](../features/credentials.md#targeted-vs-bearer)).
- **API keys / capability tokens** — a licence whose issuee is a service identity: scoped by claims,
  checked by the resource on each use, revoked centrally, delegable down a committed path.
- **Supplier onboarding / KYB** — a reusable business-identity credential: verified once by the
  attestor, presented everywhere, revoked when standing lapses.
- **Reputation / endorsements** — accumulated attestations: many small credentials from many
  issuers, each independently verifiable and revocable; the aggregation and weighting is the relying
  party's policy, as it must be.
- **Compliance attestation** (credential half) — an auditor's attestation as a credential; where a
  trail matters the log composes in, which is the digital product passport's case
  ([`passport.md`](passport.md)).

## What this validates

- **One wrapper carries a regulatory domain.** Nothing licensing needed — hierarchy, suspension,
  selective disclosure, renewal, cohort recall, single-use — required a new field, a registry
  service, or a policy language. The claim that the credential is deliberately minimal and the
  relying party deliberately sovereign survives contact with the heaviest credential domain in the
  catalogue.
- **Fail-secure is the default posture end to end.** Every check in this doc refuses on uncertainty
  — unresolvable anchor, stale chain, unreachable revocation walk — and every fail-open softening is
  an explicit, local, priced choice by the checker.
- **Offline-first verification with principled online legs.** Authenticity from the data alone;
  freshness and revocation as the exactly-two reads that genuinely cannot be offline — the split the
  design promises, observed intact in the field's most offline-shaped use cases.

## Limits

- **Issuer trust is out of band.** Which authorities a checker accepts is configuration rooted in
  the real world; the structure proves issuance by a prefix, not that the prefix is the ministry it
  claims to be. Binding well-known authorities to prefixes is directory work above the protocol.
- **Revocation latency is the checker's dial.** Between the issuer's strike and a checker's next
  fresh read, a fail-open checker can accept a dead licence — the stated freshness residual, tuned
  per deployment, never hidden.
- **The credential attests the issuer's judgment, not the fact.** A licence proves the authority
  said the holder may drive — wrongly granted is wrongly granted, structurally perfect. Contesting
  the judgment is an institutional process; the structure contributes the unforgeable record of who
  judged what, when.
