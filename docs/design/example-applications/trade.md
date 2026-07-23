# trade — trade documents

`trade` is the paperwork of commerce between organizations that do not trust each other: bills of
lading, letters of credit, certificates of origin, customs declarations — multi-party documents
whose authenticity, endorsements, and current holder must be verifiable across companies, banks, and
borders. It is the composition case for **credentials plus shared documents plus exchange** — the
only three-feature composition in the set.

## The composition

Each feature carries the leg it is shaped for:

- **The instrument's issuance is a credential.** A bill of lading is the carrier attesting receipt
  of goods; a letter of credit is the bank attesting a payment commitment — issuer-signed, anchored,
  revocable claims with exactly the acceptance discipline a counterparty needs
  ([`../features/credentials.md`](../features/credentials.md)). Authority hierarchies (a customs
  broker under its licensing authority) ride the delegation path, verified never asserted.
- **The transaction file is a shared document.** The parties to a shipment — shipper, carrier,
  consignee, banks — collaborate on the evolving file: amendments, schedules, endorsement records,
  each an attributed, anchored version under a governed membership, disputes surfacing as the DAG's
  presented branches rather than as competing faxes
  ([`../features/shared-documents.md`](../features/shared-documents.md)).
- **Separation of duties is the policy language's `and`.** A release condition like "the carrier
  **and** the consignee's bank" is `and(id(carrier), id(bank))` — a committed policy SAD the relying
  party evaluates, satisfied by each party's **independent attestation** on its own chain at its own
  pace, no countersigning ceremony
  ([`../primitives/policy/documents.md` §Multi-identity authorization](../primitives/policy/documents.md#multi-identity-authorization--independent-attestations)).
- **Negotiation and delivery are sealed exchange.** Offers, amendments, and the documents themselves
  move between parties as sealed payloads — confidential against the world, attributed between the
  parties, delivered offline ([`../features/exchange.md`](../features/exchange.md)); a formal
  disclosure with a signed acceptance rides the presentation machinery, so terms travel with the
  credential and acceptance is non-repudiable
  ([`../features/credentials.md` §Terms of use](../features/credentials.md#terms-of-use)).
- **Title transfer is issuer re-grant, not endorsement-by-copy.** The negotiable instrument's hard
  property — exactly one current holder — is the design's standing uniqueness discipline: the issuer
  revokes the credential held by the endorser and issues to the endorsee, the transfer recorded on
  the issuer's chain
  ([`../features/credentials.md` §Targeted vs bearer](../features/credentials.md#targeted-vs-bearer)
  — transfer is a re-grant). A copied instrument is then just a dead credential; the current holder
  is always answerable from the issuer's chain, which is precisely the question a presenting party
  at a port needs answered.

## Scenarios

- **A documentary credit cycle.** The bank issues the letter of credit to the beneficiary; the
  carrier issues the bill of lading; the beneficiary presents both to the bank with selective
  disclosure (the bank sees the terms it needs, not the whole commercial relationship); the bank's
  acceptance is a signed, chained act. Every party verifies every instrument against its issuer — no
  SWIFT-style intermediary attesting authenticity.
- **Endorsing the bill.** The consignee sells the goods afloat: the carrier re-grants the bill to
  the new buyer. The port releases against the current holder's ownership proof — a live,
  audience-scoped signature, not possession of paper.
- **A dispute.** The shipper and consignee disagree on an amendment: both versions sit in the file's
  DAG, attributed and timestamped, and the arbitrator reads the actual sequence of acts from the
  data — the evidentiary posture the ledger and tracker already validated, at contract stakes.
- **Customs.** The declaration is a credential presented with claim-gating — the tariff-relevant
  brackets disclosed, the commercial invoice detail withheld — against issuers the authority
  recognizes.

## What this validates

- **Three features compose under one application without colliding.** Issuance, collaboration, and
  delivery each stay in their lane; the seams are SAIDs and prefixes; no coordinating machinery had
  to be invented — at three features the composition claim is under its heaviest load in the set,
  and it holds.
- **Uniqueness-bearing instruments are expressible.** The negotiable-instrument problem — the
  classic blocker for paperless trade — lands on the issuer-re-grant discipline the credential
  feature already fixed, with the issuer's chain as the title registry no one has to build or trust
  separately.
- **Mutually distrusting parties need no shared operator.** Each party trusts its own verification;
  the shared state is data everyone can check, not a platform someone must run.

## Limits

- **Legal recognition is out of band.** Whether a jurisdiction accepts the re-granted credential as
  the negotiable original is law, not structure; the composition supplies the verifiable substrate a
  legal framework can bind to.
- **The issuer is the uniqueness authority.** Title-by-re-grant makes the carrier's chain the
  registry of holders — a captured or vanished issuer breaks transfer (though never history). The
  structural mitigation is the issuer's own identity redundancy; the institutional one is the
  domain's existing regulation of carriers and banks, which this composition leans on knowingly.
- **Workflow semantics are the application's.** What sequence of documents closes a trade, which
  amendments need whose sign-off — encoded in the file's conventions and the parties' policies, not
  enforced by chains, exactly as the tracker's status lattice ([`tracker.md`](tracker.md)).
