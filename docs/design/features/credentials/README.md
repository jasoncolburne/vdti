# Credentials

A **credential** is signed, verifiable data an **issuer** makes about a **subject** — a diploma, a
licence, a prescription, a ballot eligibility. The credentials feature is how VDTI issues one, and —
the case that carries the weight — how a **relying party accepts** one someone presents. It composes
the primitives below it and adds **no new chain machinery**: a credential is a piece of content,
issued by anchoring it and presented by disclosing it.

The presentation is a disclosure, so credentials builds on the
[presentation exchange](../../primitives/protocols/ipex.md) (IPEX) — and only on it.
Confidentiality, when a disclosure must be private, stacks underneath at the transport edge without
credentials knowing; see [Composing the protocols](#composing-the-protocols).

## The credential

A credential is a **standalone SAD** — data that references identities, never a chain of its own.
Its **`kind` names its type** (`vdti/cred/v1/schemas/*`, application-registered — a diploma, an
accreditation), so a relying party can dispatch on _which_ credential it is looking at. The shape
below is the common wrapper every type carries.

```
credential = {
  said,       // its self-address; the immutable anchor
  kind,       // vdti/cred/v1/schemas/* — the registered type (see below)
  issuer,     // the issuer's identity prefix
  issuee?,    // the subject's identity prefix; ABSENT → a bearer credential
  claims,     // a nested SAD of the issuer's assertions (application-shaped)
  terms?,     // an issuer-set terms-of-use SAD; travels with the credential
  issued,     // an advisory timestamp — always present
  expires?,   // an advisory timestamp
  nonce,      // high-entropy; every credential has one
}
```

- **No policy field.** A credential carries no acceptance policy and no authorizing structure —
  _what_ makes a credential acceptable is the relying party's decision, not something the credential
  asserts about itself (see [The two questions](#the-two-questions)). Its as-of authority is the
  **anchoring position**, never a self-declared body value, so nothing can select a permissive past
  while issuance anchors in the present.
- **The `kind` is the type.** Every credential shares the wrapper above, but its `kind` names which
  credential it is. The framework validates the wrapper and that the `kind` is a **registered**
  credential kind; the **application** validates the claim contents, with helpers the feature ships.
  Types are what edges and relying parties dispatch on.
- **`claims` is application-shaped.** A nested SAD whose SAID the credential commits; a verifier
  reads only the fields it needs. There is no closed schema and no built-in field validation —
  [claim-gating](#claim-gating) shapes it for privacy.
- **Every credential carries a `nonce`.** A high-entropy value, so the SAID is unique and
  unguessable — not optional.
- **`terms` is issuer-set and optional** — a terms-of-use the issuer commits at issuance, so
  conditions travel with the credential rather than being re-negotiated each exchange
  ([Terms of use](#terms-of-use)).

## The two foundations

Both are existing primitives, reused unchanged.

- **Proof of issuance is the anchor.** To issue, the issuer **anchors** the credential's canonical
  SAID on its **own** chain — committing a hash of the credential's identity through an ordinary
  interaction event. That anchor is the validity proof, and it is strictly stronger than a detached
  issuer signature: it is **witnessed** (the federation attests it), **positioned** (a point in the
  issuer's chain, so it is time-ordered and revocable in place), and floored at the **earliest**
  matching anchor (so a later re-anchor cannot launder a credential past a change in the issuer's
  authority). No registry object and no lookup record: the credential is immutable and
  holder-presented, so it needs none. The anchoring event transitively commits the issuer's key
  state and its whole authority chain.
- **Proof of disclosure is compaction.** A SAD's SAID is a hash over its content with nested SADs
  replaced by their own SAIDs, so a section is disclosed by revealing it and recomputing its SAID
  against the reference in its parent — no sibling-hash paths. Because the anchored SAID is over the
  compact form, **any faithful disclosed variant verifies against the one anchor**. Graduated
  disclosure is exactly that recursive check.

## The two questions

Accepting a credential answers two independent questions, and **only structure answers them — no
policy lives on the credential or the chain.**

- **Was it validly issued?** Read **as issued**: the issuance is anchored on the issuer's chain at
  the earliest matching position, and the relying party's issuer condition resolves _there_. The
  simple case is "the issuer is who I trust"; the delegated case is "the issuer holds authority
  delegated N hops from a root I trust," evaluated by walking the **issuer's** chain — never carried
  on the credential. Delegated issuance is thus **derived**, not asserted.
- **Does the presenter own it?** The uniform **ownership proof**: the presenter must satisfy the
  `issuee` identity's `t_use` quorum, live, binding the disclosure to a fresh, audience-scoped
  `{ audience, nonce, created }` — realized as the IPEX `grant` signature, in one round trip, not a
  separate challenge exchange. This is the whole "who may present" answer — structural, not a
  policy. A bearer credential (no `issuee`) skips it.

Why these are as-issued and a live ownership proof, never a live multi-party policy: anchors compose
without coordination (each party commits on its own chain at its own pace, so you never need several
parties online at once), while a live check does the one thing an anchor cannot — prove "this
identity controls its keys, to this verifier, right now" — which is inherently about **one**
identity. So credential composition is as-issued only, and the one live act is the single-identity
ownership proof.

## Accepting a presented credential

The core case. A relying party grants **only if every one of these holds** — a fail-secure
conjunction:

- **Structural integrity** — the SAID recomputes and `claims` is a well-formed SAD of the expected
  kind.
- **Validly issued** — the issuance is anchored at the earliest matching position and the issuer
  condition resolves there; for a **delegated** issuer, the delegation path is **not rescinded**.
- **Issuer trusted** — the relying party trusts the `issuer` (its application decision).
- **Fresh to the tip** — the issuer's chain is not forked, not disputed, and current, read against
  multi-source witnessed state. This is **mandatory**: an as-issued read alone is fooled by a forged
  linear extension of a dormant chain, and only the to-tip check catches it. A no-single-tip or
  stale chain grounds no new trust and is refused.
- **Not revoked** — the fail-secure revocation walk ([Revocation](#revocation)).
- **Owned** — the presenter satisfies the `issuee`'s `t_use`, bound to a fresh, audience-scoped
  `{ audience, nonce, created }` (the `grant` signature; a verifier-issued challenge is the optional
  stronger-liveness mode). This resolves at the issuee's **current tip**: a forked or disputed
  issuee grounds no single tip, so it grounds no ownership and is refused — the same fail-secure bar
  the issuer's chain meets above. Bearer credentials skip this.
- **Not expired** — advisory; the caller decides.

## Presentation

Issuance and presentation are both **[IPEX](../../primitives/protocols/ipex.md)** disclosures (from
a discloser to a disclosee; issuance is the case where the discloser is the issuer). The credential
is long-lived — its freshness is the anchor, revocation, and the advisory `expires`. A
**presentation** is made fresh per use by the IPEX `grant` envelope, which carries
`{ audience, nonce, created }` and is signed by the **issuee's current-tip `t_use` quorum**. That
one signature does double duty: it proves **ownership** (the required signer is the credential's
committed `issuee`, so control of the issuee's keys is the "who may present" answer) **and** binds
the disclosure to its audience, nonce, and time so it cannot be replayed.

- **Copy-replay of a targeted credential is closed within a single `grant`.** Replay to the same
  verifier hits the nonce dedup; replay elsewhere fails the audience binding; presenting someone
  else's targeted credential fails because the required signer is _its_ committed issuee. The
  baseline is **one round trip**; a verifier-issued challenge is an optional stronger-liveness mode,
  not a requirement.
- **Proof of issuance stays the anchor, not the `grant` signature** — the signature authenticates
  delivery and current control, never issuance.
- **Proof of disclosure is compaction** — the graduated recursive reveal.
- IPEX is generic over anchored, compactable SADs; nothing credential-specific lives in it.
  Credentials is one caller.

## Targeted vs bearer

A credential is **targeted** by default — it names an `issuee`, and that binding is the whole value
for the core cases (identity, health, licensing, voting): a claim bound to a person,
non-transferable by copy because presenting it requires the issuee's keys.

- **Bearer credentials are supported, but single-use only.** A bearer credential names no `issuee`;
  whoever presents it is accepted. This fits a **transferable, single-use instrument** — a ticket, a
  voucher, a one-time capability — where transferability is the point and no one cares who holds it.
  **Redemption is revocation:** on first acceptance the issuer revokes the credential (a revocation
  strike is _additive_, so the issuance proof is preserved — nothing is destroyed), and a later copy
  reads revoked and is turned away. A venue admits only after the revocation is confirmed witnessed
  (fail-secure) or admits-and-reconciles (fail-open) — the latency-versus-risk choice offline card
  payments already make.
  - **The inherent residual:** between issuance and first redemption, copies **race** — the first
    presentation scanned wins. A photocopied paper ticket behaves identically; acceptable for
    single-use.
- **Reuse, re-entry, and membership are targeted, not bearer.** Reusable + transferable + bearer is
  not a coherent thing: with no identity binding a copy is indistinguishable from the original and
  reuses just as well, so there is nothing to detect. Re-entry therefore forces an identity binding:
  a **membership** is bound to a prefix, re-entry is the ownership challenge, and **transfer is a
  re-grant** (add the new prefix, drop the old), never the hand-off of a copy.
  Reusable-transferable-bearer is a non-goal — a logical impossibility, not a missing feature.

## Claim-gating

A relying party often needs to gate on **individual claim values**, not just the issuer — voting
needs `citizen ∧ age ≥ 18`. This is solved **without zero-knowledge proofs and without a predicate
language**, by shaping the credential:

- **The issuer pre-computes useful predicates as individually-blinded claims** — each a nested SAD
  `{ said, nonce, data }`, e.g. `ageOver18`, `ageOver21`, `citizen`, alongside `birthdate` (the
  recompute source). The per-claim `nonce` blinds each SAID, so a compacted claim leaks nothing.
- **Disclose only what is asked.** The holder reveals the `{ nonce, data }` for the exact claim the
  verifier needs and the verifier recomputes its SAID against the credential's commitment;
  everything else stays blinded. Proving `age ≥ 18` never reveals the birthdate, because the issuer
  already computed the boolean.
- **The verifier's check collapses to a boolean** — _is this claim disclosed, true, and provably
  from a trusted issuer?_ No predicate evaluation, no birthdate, so there is **no claims language in
  the protocol**. The reusable piece is a **verify-the-disclosure helper** (confirming
  proof-of-disclosure on top of proof-of-issuance), shipped so an application cannot gate on an
  unverified claim.
- **A uniform bracket set gives presence-privacy.** Every credential _of a type_ carries the
  **same** claim keys, all blinded, differing only in the hidden `data`. If a minor's passport
  omitted `ageOver18`, the mere presence of the key would leak age; uniform keys mean presence
  reveals nothing. This is the one non-obvious rule.
- **Crossing a threshold is a renewal.** A bracket is a fixed boolean, so a birthday that flips one
  is handled by re-issue: the holder discloses fully to the issuer (the birthdate is always in the
  credential), the issuer recomputes every bracket, revokes the old credential, and issues a fresh
  one with **new nonces** — unlinkable renewals. A predicate the issuer did not pre-bake is added
  the same way. The predicate set is issuer-defined and extensible by renewal, with no protocol
  change.
- **Key derivation is application code, not a protocol registry.** Issuer and verifier call the
  **same** canonical key derivation, so keys match by construction; operators are a small **total**
  set (`gt`/`gte`/`lt`/`lte`/`eq`/`in`), decidable, with no arbitrary computation, and eligibility
  defaults to `gte` so a `gt`/`gte` mismatch cannot silently miss.

## Revocation

A credential needs no revocation object unless it is ever revoked. To revoke, the issuer declares a
**kill** on its own chain naming the credential's derived revocation target, alongside a small
sealed lookup log (so the declaration does not leak the object's address). A non-issuer cannot
declare it, and a witnessed kill cannot be rolled back — no forged revocation, no silent
un-revocation.

- **Status is read fail-secure by default** — compute the target and walk the issuer's **fresh**
  chain from the issuance position to the tip, matching the target against each kill. Found →
  revoked; absent on a fully-walked fresh chain → not revoked. This rides the freshness gate: hiding
  a revocation would need a stale chain, which a verifier trusting the issuer already refuses.
- A content-addressed **fail-open** lookup is available where a consumer prefers availability over
  fail-secure — its own choice, not the framework's.

## Edges / chaining

A credential MAY reference another under a trust rule, so authority chains — a national accreditor
issues an accreditation to a university, which issues a diploma to a student. An **edge** is a claim
naming another credential's SAID plus a boolean **`transitive`**:

- **`transitive: true` — the authority chain.** The referenced (source) credential's `issuee` must
  equal **this** credential's `issuer`: the diploma's issuer must itself hold the accreditation the
  edge names. Verification **recurses** — the source must itself verify valid, fresh, not-revoked,
  and issuer-trusted (the accepting checks **minus** ownership, since the source is referenced, not
  presented) — bounded by a verifier-wide depth cap, fail-secure on exceed.
- **`transitive: false` — a plain reference.** The source is cited with no issuer-chain requirement
  — "this refers to that data," no authority delegation.

One boolean is the whole axis: authority chains through, or it does not. Whether a diploma _accepts_
an accreditation as its source is the **relying party's** decision, made by dispatching on the
source's `kind` — never a rule baked onto the credential. The edge itself is purely structural.
Though it rides in `claims`, an edge has a **uniform, framework-recognized shape** — the source SAID
plus `transitive` — so the framework locates it and drives the recursive check, the same way the
[claim-gating](#claim-gating) verify helper is framework-supplied over otherwise app-shaped claims.

## Terms of use

Terms-of-use ride the **credential**, not just the exchange. The issuer commits an optional `terms`
at issuance, so conditions (e.g. "do not re-disclose") travel with the credential. A presentation
then carries a **signed acceptance** of those terms: the presenting party's IPEX `grant` discloses
the terms-bearing credential and so commits its terms — no separate acceptance field — or, in the
negotiated flow, the disclosee's `agree` signs them. Either way it is a non-repudiable record of who
accepted what. Because the terms are on the credential, an onward re-disclosure **inherits** them
structurally, and the signed acceptances build a custody chain. Enforcement is **commitment and
accountability**, not prevention: revealed bytes cannot be un-revealed, but the signed acceptance is
non-repudiable evidence of a breach. One-off per-exchange conditions can still be negotiated in the
exchange on top; the credential's own terms are the issuer's.

## Bulk issuance

Issuing N credentials with N separate anchors is costly at scale (a university issuing thousands of
diplomas). Bulk issuance names **many commitments in a single anchoring event** — the same
per-credential commitment, batched — up to a pinned batch bound. Each credential's proof of issuance
is that shared anchor's position; revocation stays per-credential. No new machinery: bulk is the
ordinary anchor, at width.

The trade is deliberate. Single issuance anchors each credential at its own position, so two from a
cohort are unlinked; bulk co-locates them, so a **presented** credential is linkable to its issuance
batch (the issuer and rough time were already visible; the batch makes it exact). So the issuer
picks by privacy need: **single issuance** when a cohort must not be linkable (a sensitive
population), **bulk** when it need not be (a graduating class already public). There is deliberately
no cheap-and-unlinkable third mode — a use case that truly needs unlinkability at scale issues
singly and accepts the cost.

## The registrar

A **registrar** — a government, or any authority with a member roll — binds real people to identity
prefixes and issues them credentials holding their data. Its value is **one person ↔ exactly one
prefix**; if a person could bind to several, the registrar loses (double-vote, sybil). Enforcing
that single binding is the whole job.

**The primary path is migration, not fresh enrollment.** Almost every adopting organization already
has its users behind an existing login. The realistic onboarding is to **migrate** them — get the
data in the old system into a self-sovereign credential issued to the right party. A person with no
prior account is the exception, handled by a mailed one-time token whose single use a public
spent-token log enforces.

**Single binding comes for free from the old system.** An existing platform already enforces
one-account-per-person, so migrating each account to one prefix inherits that uniqueness — the
nullifier machinery is only needed for the no-prior-account case.

A migration **binds two proofs in one exchange, both required:** the user authenticates to the **old
platform** ("I am account X," the org's own auth) **and** signs the request with its **new prefix
P** ("I control P"). The issuer then pulls X's data, issues a credential to `issuee = P`, anchors
it, and records `X ↔ P`. Drop the P-signature and someone could migrate X's data onto an attacker's
prefix; drop the login and anyone could claim to be X.

**Two auth modes — a normal login and a step-up login.** Step-up is a second factor out of band from
the login (a one-time code to a contact on file, the mailed token, a knowledge factor, or an
in-person check). Step-up is **recommended on a first bind** and **enforced on any re-bind**, so a
stolen password alone can never re-bind an already-enrolled subject.

**The old system is a bridge, and that is the value.** During migration it stays up and is the
fallback if someone loses their keys; as migration completes it shrinks to just the binding map,
then retires. Crucially, once a user has migrated, the credential is anchored and self-sovereign, so
a later breach of the old system can neither **present** it (the holder alone controls P) nor
**re-bind** it (the subject now exists, and a re-bind enforces step-up). So the old login's strength
bounds a **one-time enrollment window**, not a permanent takeover — the whole point is to transfer
trust off a central login onto a self-sovereign identity, once.

**Recovery maps onto the identity's own compromise tiers, with no new mechanism:** a lost signing
key is a rotation (the credential stays valid on the same prefix); a lost device on a multi-device
identity is an eviction by the surviving devices; total loss reincepts a **new** prefix and re-runs
the bind — an existing subject, so step-up is enforced, and the registrar revokes the old
credential, issues to the new prefix, and **replaces** the binding (never a second one). Credential
loss cannot destroy the data: the credential is a re-fetchable record whose source of truth is the
registrar's own records.

The `Registrar` seam is "prove the requester, return their data": the organization implements
_authenticate the requester_ and _return the data to embed_, plus the binding check (a new subject
binds under either mode; an existing subject enforces step-up and the re-bind replaces); the
framework supplies the rest — receiving the request, issuing and anchoring, recording the binding,
and the revoke-old/issue-new recovery path.

## Composing the protocols

The presentation flow uses a secure transport, but **credentials must not be transport-aware.**

- **Credentials depends on [IPEX](../../primitives/protocols/ipex.md), never on the
  [sealed envelope](../../primitives/protocols/essr.md).** IPEX gives integrity and attribution and
  does not itself require the seal. A **private** disclosure runs IPEX-inside-a-seal, chosen where
  the exchange is wired up, not baked into credentials — confidentiality stacks without credentials
  knowing.
- Ship **one reference composition** so application authors don't re-wire the security-critical
  freshness binding and reintroduce replay.

## Boundary / residuals

- **What credentials are acceptable** — trusted issuers, required claims, the freshness bar — is the
  relying party's application decision, not on the credential and not in the protocol.
- **Revocation freshness** is bounded by the consumer's read strategy (fail-secure walk vs.
  fail-open lookup vs. timeout) — an application choice, not a protocol guarantee.
- **The bearer copy-race** (issuance to first redemption) and **registrar attestation** (single
  binding rests on the registrar not losing its own identity, and is attested by it rather than
  independently verifiable) are the standing residuals.

## Cross-references

- [`../../primitives/protocols/ipex.md`](../../primitives/protocols/ipex.md) — the disclosure
  exchange issuance and presentation are, and the freshness envelope a presentation rides.
- [`../../primitives/protocols/essr.md`](../../primitives/protocols/essr.md) — the seal a private
  disclosure stacks under at the edge.
- [`../../primitives/policy/policy.md`](../../primitives/policy/policy.md) — the authorization
  language a relying party's issuer condition (`id` / `del`) is written in.
- [`../../primitives/data/sad/compaction.md`](../../primitives/data/sad/compaction.md) — the
  recursive SAID commitment that makes graduated disclosure verifiable against one anchor.
