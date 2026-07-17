# What you can build on VDTI

VDTI is a kit for building high-trust applications by **composing verifiable primitives** instead of
building a trusted backend. This is the catalogue: what you can build, and how each application
composes. See [`README.md`](README.md) for the pitch and
[`docs/design/system-thesis.md`](docs/design/system-thesis.md) for the model.

The shape of every entry below is the same — a short description, then **composes:** the building
blocks it snaps together. Everything here inherits, for free, the properties in
[§What they all share](#what-they-all-share).

## The building blocks

The **primitives** are the raw material; the **features** are pre-built machinery for the hard
problems; the **substrate** is the shared infrastructure underneath; and **applications** are what
you ship on top. Most applications are mostly primitives.

**Primitives** (the raw material):

- **Data with custody** — a self-describing record that carries a provable writer (who wrote it) and
  a controlled read-set (who may read it), plus where its bytes live. Storage, write-attribution,
  and read-gating in one primitive.
- **Log** — a single-owner, append-only, tamper-evident chain of records. Also the lookup/index
  layer: a log locates the data addressed to it.
- **Identity** — a person or organization as a threshold of their own devices. The unit an
  application authenticates and issues to; decoupled from any single device.

**Features** (pre-built machinery):

- **Shared documents** — collaborative, evolving, membership-governed data: a signed, attributed
  branch-and-merge DAG, indexed by logs. It is essentially git.
- **Exchange** — secure delivery and key distribution: published encryption keys looked up through
  logs, one-to-one and ratcheting group messaging. Layered with shared documents, a single seed keys
  a whole group so many parties can communicate.
- **Credentials** — issuing delegated, revocable authority: one identity vouches for another with a
  verifiable, revocable claim.

**Substrate** (the infrastructure): federation witnessing, encrypted mesh transport, and the record
store. Run by the organizations that issue and rely on trust — shared by everyone. You do not run
it; you write applications on it.

**Applications** (what you ship): your app, composing the tiers above — most of them mostly
primitives. A handful of **reference apps** ship with VDTI (`mail`, `chat`, `edit`, `bbs`, `health`,
and the `registrar` that `vote` builds on). This layer is also where an app plugs in logic VDTI
doesn't own, via a trait, when it must reach an **external authority** — e.g. a government's
`Registrar` (VDTI ships the binding and issuance glue; the org supplies only its private
verification).

## The core patterns

- **Store data with an owner and a read-set** → data with custody.
- **Keep an append-only history / audit trail** → a log.
- **Look something up** → a log (it indexes and locates).
- **Collaborate on evolving, linked, versioned data** → shared documents (the git-like DAG).
- **Move data secretly between parties** → exchange.
- **Let many parties share a secret to communicate under** → exchange (a seed derives per-party
  keys) + shared documents.
- **Vouch for someone, or delegate authority** → credentials.

## Applications

### Storage and data — primitives, no feature needed

- **File storage and sync (a Dropbox)** — a custodied record with an owner, a read-set, and
  replication. **Composes:** data with custody.
- **Blog / CMS / personal site** — publicly readable custodied records. **Composes:** data with
  custody.
- **Photo or document vault** — read-gated custodied records. **Composes:** data with custody.
- **Audit log / event sourcing / compliance ledger** — an append-only, tamper-evident trail.
  **Composes:** a log.
- **Personal data store / wallet backend** — your records, held and verified by you. **Composes:**
  data with custody + logs.

### Collaboration — shared documents (the git DAG)

- **Wiki / knowledge base** — linked, versioned, co-edited pages, located by logs. **Composes:**
  shared documents.
- **Code hosting / version control (a verifiable GitHub)** — shared documents _is_ the signed git
  DAG: every commit attributed and self-verifying, no central host. **Composes:** shared documents.
- **Collaborative editor (a Google-Docs)** — co-authored, branch-and-merge documents, delivered to
  members. **Composes:** shared documents + exchange. _(the `edit` example app)_
- **Issue / project tracker** — collaborative state with roles. **Composes:** shared documents +
  credentials (for roles).
- **Forum / message board** — threaded, co-authored posts. **Composes:** shared documents. _(the
  `bbs` example app)_

### Communication — exchange

- **Secure mail** — store-and-forward sealed messages. **Composes:** exchange. _(the `mail` example
  app)_
- **One-to-one and group chat** — a seed keys every member; the message thread is a shared document.
  **Composes:** exchange + shared documents. _(the `chat` example app)_
- **Notifications / pub-sub** — sealed, routed messages. **Composes:** exchange.
- **Secure file transfer / drop-box delivery** — hand a record to one recipient. **Composes:**
  exchange.
- **Key distribution** — publish and look up encryption keys. **Composes:** exchange.

### Identity and authority — credentials

- **Passwordless sign-in / SSO** — prove control of your identity; add third-party attestation for
  "and they are verified to be X." **Composes:** identity + credentials.
- **Access control / IAM** — delegate revocable authority to identities, verifiable with no central
  policy server. **Composes:** credentials.
- **API keys / capability tokens** — issue, scope, and revoke — all verifiable. **Composes:**
  credentials.
- **Reputation / endorsements** — accumulated attestations about an identity. **Composes:**
  credentials.

### Supply chain — credentials + a log, with exchange for hand-off

- **Track-and-trace / provenance** — each actor an identity, each hand-off an attestation, the
  item's history a log; verifiable end-to-end with no central tracker. **Composes:** credentials +
  logs + exchange. _(food, pharma, luxury goods, conflict minerals)_
- **Recall management** — the issuer revokes a batch's certificate and every holder's check fails
  secure, instantly and verifiably. **Composes:** credentials.
- **Digital Product Passport** — a per-product credential plus provenance log (increasingly
  mandated, e.g. in the EU). **Composes:** credentials + logs.
- **Chain of custody** — legal evidence, lab samples, cold-chain: a tamper-evident custody log with
  attested hand-offs. **Composes:** a log + credentials + exchange.
- **Certificate of authenticity / anti-counterfeit** — the maker attests; the item carries a
  verifiable claim. **Composes:** credentials.
- **Trade documents** — bills of lading, letters of credit, customs paperwork, verifiable across
  organizations that do not trust each other. **Composes:** credentials + shared documents +
  exchange.
- **Supplier onboarding / KYB** — a reusable, verified business-identity credential. **Composes:**
  credentials.
- **Warranty and service history** — a service record that travels with the good. **Composes:** a
  log + credentials.

### Government and regulated

- **Age or identity verification** — disclose only what is needed, verifiable offline. **Composes:**
  credentials.
- **Licensing and permits** — issue, verify, and revoke. **Composes:** credentials.
- **Travel documents** — held by the traveler, verifiable without a live lookup. **Composes:**
  credentials.
- **Compliance attestation** — an auditor attests; a log holds the trail. **Composes:**
  credentials + a log.
- **Voting / elections** — a government binds each citizen to **one** identity (one person, one
  vote) via a **registrar**, then collects anchored, auditable ballots with a durable tally.
  **Composes:** credentials + exchange + the `registrar` app. _(the `vote` example app, built on
  `registrar`. A fully **secret** ballot — voter privacy with coercion resistance — needs
  zero-knowledge proofs, which sit outside today's post-quantum crypto suite; the auditable-ballot
  form does not.)_

### Health

- **Patient-held records** — the patient holds their records and shares them with providers on their
  own terms. **Composes:** credentials + exchange. _(the `health` example app)_
- **Prescriptions** — an issued, revocable credential the pharmacy verifies. **Composes:**
  credentials.
- **Drug supply-chain provenance** — track-and-trace applied to pharmaceuticals. **Composes:**
  credentials + logs + exchange.

## The example apps, decomposed

The reference applications, built entirely from the same kit:

| Application                 | Composes                             |
| --------------------------- | ------------------------------------ |
| `mail`                      | exchange                             |
| `chat`                      | exchange + shared documents          |
| `bbs` (forum)               | shared documents                     |
| `edit` (collaborative docs) | exchange + shared documents          |
| `health`                    | exchange + credentials               |
| `registrar`                 | credentials + exchange               |
| `vote`                      | credentials + exchange + `registrar` |

All of them run over the shared substrate (federation, witnessing, the record store) — which you do
not build or operate.

## What they all share

Every application above inherits, by construction and with no extra work:

- **Tamper-evidence** — a changed record breaks its own proof.
- **Provenance** — who did what, when, and under what authority travels with the data.
- **Offline, end-to-end verification** — a client verifies everything itself, from any source.
- **Revocation** — an issuer can revoke; a verifier confirms not-revoked from a fresh read of the
  issuer's chain (any source), failing secure by default (an application may opt into fail-open).
- **No trusted backend** — you write the application; the infrastructure is run by the issuers who
  rely on it.

You write the app. The trust comes with the data.
