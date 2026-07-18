# vdti — area note: Credentials (the feature)

**Status: FIRST CUT — carved into its own area note (2026-07-17), per the rule that every primitive,
feature, substrate component, and eventual example app gets a canon area. Supersedes the credential
content previously interleaved in `vdti-area-document-policy.md` §A/§F (now a pointer here); the policy
DSL + evaluation model stay there.** Credentials is a **feature that composes primitives** — it adds no
new chain machinery. It consumes **policy** (the generic authorization engine), **IPEX** (the disclosure
protocol), and the **anchor** + **compaction** SAD primitives. It **never** names ESSR; confidentiality
stacks at the edge (§Protocols).

**Invariants referenced:** [inv 1] policy-on-documents-not-chains, [inv 4] transitively-committed
key-state, [inv 5] as-of = the anchoring position, [inv 8] multi-source freshness, [inv 10]
negative-checks-are-lookup-SELs, [inv 16] addressing-by-prefix / private-SAID-unguessable, [inv 17]
chain validity is content-independent.

## The credential

A credential is a **direct-anchored SAD** — data that references identities, never a chain kind of its
own. Its **`kind` names its type** — `vdti/cred/v1/schemas/*`, app-registered (a diploma, an accreditation)
— so a relying party can dispatch on _which_ credential it is; the shape below is the common wrapper every
type carries.

```
cred = {
  said,
  issuer,     // issuer IEL prefix                       [inv 16: entity = prefix]
  issuee,     // issuee/holder IEL prefix; ABSENT → a bearer credential (§Targeted vs bearer)
  claims,     // → a nested SAD of kind vdti/cred/v1/claims/* (app-defined, opaque when compacted)
  terms?,     // → an issuer-set terms-of-use SAD; travels with the credential (§Terms-of-use)
  issued,     // advisory timestamp — always present     [inv 6: timestamps advisory]
  expires?,   // advisory timestamp
  nonce,      // high-entropy — every credential has one; makes the SAID unique and unguessable
}
```

- **No `policy` field.** A credential carries no acceptance policy and no authorizing structure (see
  §The two questions). The as-of authority is the **anchoring position**, never a self-asserted body
  value — nothing can select a permissive past while issuance anchors in the restrictive present.
- **`claims` is application-defined.** A nested SAD under `vdti/cred/v1/claims/*`; the compact SAID
  commits the whole claims SAD, and a verifier reads only the fields it needs — no closed schema, no
  built-in field validation. Claim-gating (below) shapes it for privacy.
- **Every credential carries a `nonce`.** A high-entropy value, so the SAID is unique and unguessable —
  not optional ([inv 16]).
- **The `kind` is the credential's type.** Every credential shares the wrapper above, but its `kind` names
  _which_ credential it is (app-registered under `vdti/cred/v1/schemas/*`). The framework validates the
  wrapper and that the `kind` is a **registered** credential kind; the **application** validates the claim
  contents (its helpers). Types are what edges and relying parties dispatch on (§Edges / chaining).
- **`terms` is issuer-set and optional.** A terms-of-use SAD the issuer commits at issuance, so conditions
  travel with the credential rather than being re-negotiated per exchange (§Terms-of-use).

## The two foundations — anchoring and compaction

These found the feature; both are existing primitives, reused unchanged.

- **Proof of issuance = the anchor.** Issuance is the issuer anchoring the credential's canonical
  (fully-compact) SAID on its **own** witnessed IEL via an `Ixn` (T1), committing
  `hash('vdti/iel/v1/actions/commitment:{issuer}:{cred.said}')` through `manifest.anchors`. **That
  anchor is the validity proof** — strictly stronger than a detached issuer signature: it is
  **witnessed** (federation-attested), **positioned** (a point in the issuer's chain, so it is
  time-ordered and revocable in place), and floored at the **earliest** matching anchor (the
  earliest-anchor floor closes re-anchor tier-inversion — [inv 5]). No registry object, no
  registry identifier, no cred-SEL: the credential is immutable and holder-presented, so it needs no
  lookup object. Non-circular — the cred SAID is fixed from its content, then the issuer authors the
  anchoring `Ixn` naming it. The anchoring `Ixn` transitively commits the issuer's roster / key-state
  and its whole delegation chain ([inv 4]).
- **Proof of disclosure = compaction.** Our compaction is a **recursive SAID commitment** (a SAD's
  SAID is a hash over its content with nested SADs replaced by their SAIDs) — **not** a Merkle root:
  a nested section is disclosed by revealing it and recomputing its SAID against the reference in its
  parent, no sibling-hash paths. Because the anchored SAID is over the compact form, **any faithful
  disclosed variant is verifiable against the one anchor**. Graduated disclosure is exactly this
  recursive check.

## The two questions — and the policy lives on neither the credential nor the chain

Verifying a presented credential is two independent questions:

1. **Validly issued — checked as-issued, against the anchor.** The issuance commitment is anchored on
   the issuer's IEL at the earliest matching position. Whether the *issuer* was entitled to issue —
   `id(issuer)` (the simple case, which collapses to the structural fact that the issuer's IEL anchored
   it) or `del(issuer_root, N)` (delegated issuance) — is resolved **as-issued** against that position.
   **Crucially, this policy is the relying party's, not the credential's.** The credential carries no
   authorizing structure; it names only `issuer` (a prefix). A relying party that will accept issuers
   delegated by a root `A` evaluates its **own** `del(A, N)` policy against the cred's `issuer` at
   accept-time, walking the issuer's on-chain delegation links ([inv 10], delegation area) — a walk
   over the **issuer's** chain, never over anything on the credential. So delegated issuance is
   **derived** (from the anchoring position + the issuer's chain), never **carried**. _"What
   credentials are acceptable"_ — which issuers, which claims, which freshness bar — is an
   **application** concern (Jason 2026-07-17).
2. **Ownership / who may present — not a policy; a uniform authentication step.** The presenter proves
   current control of whoever `issuee` names — satisfying the issuee IEL's own `t_use` quorum over a
   fresh, audience-bound challenge, realized as the IPEX `grant` signature (§Presentation). There is no
   per-credential rule to evaluate. A **bearer** credential (no `issuee`) skips this.

**The structural finding underneath (composition is as-issued only).** Multi-party authorization is
inherently as-issued: an **anchor** is fresh, positioned, non-repudiable, and composes across parties
**without coordination** (each commits on its own chain at its own pace), so you never need N parties
online at once. A **challenge-response** does the one thing an anchor cannot — prove "this identity
controls its keys, to this verifier, right now" — which is inherently **single-identity**. Even
"2-of-3 approve live" collapses to per-party fresh anchors read as-issued; the "quorum" in any live
check is only ever *within* one identity (its `t_use` over its own devices). Consequence: the policy
composer (`thr`/`wgt`/`and`/`del`/`pol`) is an **as-issued-only** concern — folded into
`vdti-area-document-policy.md` §C (the current-mode evaluator is removed); the design counterpart is the
`evaluation.md` "one composer, two modes" correction (owed).

## Accepting a presented credential — the core case

A relying party **grants** iff **all** hold:

- **Structural integrity** — the credential's SAID recomputes; `claims` is a well-formed SAD of the
  expected kind.
- **Validly issued (as-issued)** — the issuance commitment is anchored on the issuer's IEL at the
  earliest matching position, and the relying party's issuer condition (`id(issuer)` /
  `del(issuer_root, N)`) resolves there — and, for a **delegated** issuer, the delegation path is **not
  rescinded** (the fail-secure positive delegating-link lookup, [inv 10]).
- **Issuer trusted** — the relying party trusts the `issuer` prefix (application layer).
- **Current trust / freshness (to-tip)** — the issuer's chain is not forked, not disputed, and fresh,
  read against multi-source witnessed state ([inv 8]). **Mandatory** — an as-issued-only resolve is
  fooled by a forged dormant-chain linear extension; only the to-tip step catches it. Fail-secure: a
  no-single-tip or stale chain grounds no new trust (REFUSE).
- **Not revoked** — the fail-secure `kills[]` walk (§Revocation).
- **Ownership (current)** — the presenter satisfies the `issuee` IEL's `t_use` over the verifier's
  fresh, audience-bound challenge. Bearer credentials skip this.
- **Not expired** — advisory; the caller decides (an `is_expired()` helper surfaces it).

## Presentation — IPEX, single round trip

Presentation and issuance are both **IPEX** disclosures (Discloser → Disclosee; issuance is the case
where the Discloser is the issuer). The credential is long-lived (its freshness is the anchor +
revocation + advisory `expires`); a **presentation** is fresh per use via the IPEX `grant` envelope,
which carries `{ audience, nonce, created }` and is signed by the **issuee's current-tip `t_use`
quorum**. That one signature does double duty — it proves ownership (the required signer is the
credential's committed `issuee`, so control of the issuee's `t_use` is the "who may present" answer,
structural, not a policy) **and** binds the disclosure to `{ audience, nonce, created }` so it cannot be
replayed.

- **Copy-replay of a targeted credential is closed within a single `grant`** — replay to the same
  verifier hits the nonce dedup; replay elsewhere fails the `audience` binding; presenting someone
  else's targeted credential fails because the required signer is *its* committed issuee. **The
  baseline is one round trip (`grant → admit`); a verifier-issued `apply` challenge is the OPTIONAL
  stronger-liveness mode, not a requirement.** _(This revises the earlier "a bound credential MUST go
  through an `apply` challenge" framing — superseded by the single-round-trip freshness model in
  `vdti-area-ipex.md`.)_
- **Proof of issuance is the anchor, not the `grant` signature.** The `grant` signature authenticates
  delivery + current control, never issuance; issuance stays the on-chain anchor.
- **Proof of disclosure is compaction** — the graduated recursive-SAID reveal.
- IPEX is generic over anchored, compactable SADs; nothing credential-specific lives in it. Credentials
  is one consumer.

## Targeted vs bearer

A credential is **targeted** (names an `issuee`) by default — that is the whole value for VDTI's core
cases (identity, health, licensing, voting): binding a claim to a person, non-transferable by copy
because presentation requires the issuee's `t_use`.

- **Bearer (untargeted) credentials are supported, but single-use only.** A bearer credential names no
  `issuee`; whoever presents it is accepted (no ownership challenge). This fits a **transferable,
  single-use instrument** — a ticket, a voucher, a one-time capability — where transferability is the
  point and nobody cares who holds it. **Redemption = revocation:** on first acceptance the issuer
  revokes the credential (§Revocation — a `kills[]` strike, which is *additive* and so preserves the
  issuance proof; nothing is destroyed). A later copy reads **revoked** and is turned away. The door
  admits only after the revocation is confirmed witnessed (**witnessed-before-admit**, idempotent
  revoke) for fail-secure, or admits-and-reconciles for fail-open — the venue's latency-vs-risk choice,
  exactly the offline-card-payment trade.
  - **Residual (inherent to bearer):** between issuance and first redemption, copies **race** — the
    first presentation scanned wins, the rest are turned away. A photocopied paper ticket behaves
    identically; acceptable for single-use.
- **Reusable / re-entry / membership is NOT bearer — it is targeted.** Reusable + transferable + bearer
  is not a coherent thing: with no identity binding, a copy is indistinguishable from the original and
  reuses just as well — nothing to detect. So re-entry forces an identity binding. A **membership** is
  bound to an IEL prefix; re-entry is the ownership challenge; **transfer is re-grant** (add the new
  prefix, drop the old) via the shared-document grant machinery, never hand-off-of-a-copy.
  Reusable-transferable-bearer is a **non-goal** (a logical impossibility), not a deferral.
- IPEX stays generic over targeted / untargeted, so the protocol carries either at no cost; the
  credentials feature simply mints bearer credentials only in the single-use instrument shape.

## Claim-gating — blinded per-predicate claims

A relying party often needs to gate on **individual claim values**, not just the issuer — voting needs
`citizen ∧ age ≥ 18`. The policy DSL is WHO-only; claim-gating is a separate axis, solved **without ZK**
and **without a predicate language** by shaping the credential:

- **The issuer pre-computes useful predicates as individually-blinded claims**, each a nested SAD
  `{ said, nonce, data }` — e.g. `ageOver18`, `ageOver21`, `ageOver65`, `citizen`, plus `birthdate`
  (the recompute source). The per-claim `nonce` blinds the SAID, so a compacted claim leaks nothing.
- **Disclose only what is asked.** The holder reveals `{ nonce, data }` for the exact claim the verifier
  needs (say `ageOver18`) and the verifier recomputes its SAID against the credential's commitment
  (proof-of-disclosure) on top of the anchor (proof-of-issuance) — everything else stays blinded.
  Privacy without a range proof: the issuer already computed the boolean, so proving `age ≥ 18` never
  reveals the birthdate.
- **The verifier's check collapses to a boolean** — _"is `ageOver18` disclosed, `true`, and provably
  from a trusted issuer?"_ No predicate evaluation, no birthdate. So there is **no claims-DSL in the
  protocol**; claim-gating is app-layer. The reusable piece apps get is a **verify-the-disclosure
  helper** (confirm proof-of-disclosure + proof-of-issuance) — shipped so an app can't gate on an
  unverified claim.
- **Structural rule — a uniform bracket set (presence-privacy).** Every credential *of a type* carries
  the **same** claim keys, all blinded — differing only in the hidden `data`. If a minor's passport
  omitted `ageOver18`, the mere presence of the key would leak age. Uniform keys → presence reveals
  nothing. This is the one non-obvious rule.
- **Renewal (time-dependence).** A bracket is a fixed boolean, so crossing a threshold requires a
  **re-issue**: the holder fully discloses to the issuer (the birthdate is always in the credential),
  the issuer recomputes every bracket, revokes the old, and issues a fresh one with **new nonces** —
  unlinkable renewals (the issuer can link, but the issuer is trusted, the same boundary as the
  registrar). A new predicate the issuer didn't pre-bake → the holder **renews to add it**. The
  predicate set is issuer-defined and extensible by renewal — no protocol change, ever.
- **Canonicalization is code, in the application-helpers toolkit** — not a protocol registry. The
  canonical key derivation `predicateKey(field, op, required) → String` (e.g.
  `predicateKey("age", GTE, 18) → "ageGTE18"`) is called by **both** issuer and verifier, so keys match
  by construction; the issuer bakes with a value-producing helper (`gtePredicate("age", actual, 18)`).
  Operators are a small **total** set (`gt` / `gte` / `lt` / `lte` / `eq` / `in`) — decidable, no
  arbitrary computation (same discipline as the policy DSL's unrecognized-construct-denies-closed).
  Default eligibility to `gte` (voting = `ageGTE18`) so an issuer-`gt` / verifier-`gte` mismatch can't
  silently miss.

## Revocation

A credential needs no revocation object unless it is ever revoked. To revoke, the issuer signs a **`Rev`**
on its own witnessed IEL declaring `kills[] = [{ target }]` with
`target = hash('vdti/sel/v1/actions/revocation:{issuer}:{cred.said}')` (the tag the constant-named canon
writes as `CRED_REVOCATION_TOPIC`), alongside a sealed `{Icp, Trm}`
lookup SEL (the SEL prefix ≠ the flat `target`, so `kills[]` doesn't leak the object's address). A
non-issuer cannot declare it (no forged revocation); a witnessed `Rev` + sealed monotone `Trm` cannot be
rolled back (no silent un-revocation).

- **Status is read fail-secure by default** — compute the `target` and walk the issuer's **fresh** IEL
  over `[issuance-position .. tip]`, forward-matching `target` against each `Rev`/`Dth`'s `kills[]`
  ([inv 10]). In some `kills[]` → revoked; in none on the fully-walked fresh chain → not-revoked. This
  rides [inv 8]'s freshness gate — hiding a revocation needs a stale IEL, which a verifier trusting the
  issuer already refuses. A content-addressed **fail-open** lookup (`{Icp, Trm}` by SAID; found →
  revoked, not-found → best-effort not-revoked) is the opt-out.
- **The revocation check is the consumer's, not `vdtid`'s** — a revoked subject is still
  structurally-valid data, so `vdtid` runs no revocation walk. The fail-secure / fail-open / timeout
  posture is the consumer's, at the application layer.
- **Privacy ([inv 16]).** `cred.said` appears nowhere raw on the public IEL — the issuance commitment,
  the kill `target`, and the lookup SEL's prefix are all hashes of it; a private cred's high-entropy
  SAID keeps its revocation status private (you can only *confirm* a subject whose cred you hold, never
  invert a `target` or bulk-enumerate).

## Edges / chaining

A credential MAY reference another credential under a trust rule, so authority chains: a national accreditor
issues an accreditation to a university, which issues a diploma to a student. An **edge** is a claim naming
another credential's SAID plus a boolean **`transitive`**:

- **`transitive: true` — the authority chain.** The referenced (source) credential's `issuee` must equal
  **this** credential's `issuer`: the diploma's issuer (the university) must itself hold the accreditation
  the edge names. Verification **recurses** — the source credential must itself verify **valid, fresh,
  not-revoked, and issuer-trusted** (the §Accepting checks **minus the ownership / presentation step**: the
  source is _referenced_, not presented, so there is no live issuee to challenge) — bounded by a
  verifier-wide depth cap, fail-secure on exceed.
- **`transitive: false` — a plain reference.** The source is cited, with no issuer-chain requirement, for
  "this credential refers to that data" — no authority delegation.

Edges are optional (most credentials carry none). One boolean is the whole axis: authority chains through,
or it does not — a genuinely different trust rule would be a **new field**, not a third value here.

**A credential's `kind` is its type, and that is what dispatch keys on.** How a relying party knows *what it
is looking at* — a diploma vs an accreditation — is the credential's `kind` ([§The credential](#the-credential),
app-registered). So "a diploma accepts an accreditation as its source" is the **relying party's** application
decision, made by dispatching on the source's `kind` — never a rule baked onto the credential (policy stays
off the credential, §The two questions). The edge itself is purely structural (the source SAID + `transitive`);
the framework validates the credential wrapper and that the `kind` is registered, and the app validates the
claim contents with its helpers.

## Terms-of-use / chain-link confidentiality

Terms-of-use ride the **credential**, not just the exchange. The issuer commits an optional **`terms`** — a
terms-of-use SAD (e.g. "do not re-disclose") — at issuance, so the conditions **travel with the credential**
rather than being re-negotiated per presentation. A presentation then carries a **signed acceptance** of
those terms: the presenting party's `grant` (or, in the negotiated flow, the disclosee's `agree`) signs the
credential's terms — a non-repudiable record of who accepted what.

**Chain-link confidentiality is then structural.** Because the terms are on the credential, an onward
re-disclosure **inherits** them: a re-discloser's `grant` commits the same terms without having to choose
to, and the signed acceptances build a custody chain of who accepted the conditions. Enforcement is
**commitment + accountability**, not prevention — revealed bytes can't be un-revealed, but the signed
acceptance is non-repudiable evidence of a breach. Per-exchange conditions negotiated in IPEX (an `offer` /
`agree`) can still ride on top for one-off terms; the credential's own terms are the **issuer's**, and now
they are where you look.

## Bulk issuance

Issuing N credentials with N separate anchors is costly at scale (a university issuing thousands of
diplomas). Bulk issuance anchors **many at once**: the issuer names up to `MAXIMUM_ANCHOR_BATCH` credential
commitments in a **single** `Ixn`'s `manifest.anchors` — the same per-credential commitment
(`hash('vdti/iel/v1/actions/commitment:{issuer}:{cred.said}')`), just batched. Each credential's
proof-of-issuance is that shared anchor's position, floored at the **earliest** matching anchor (the same
earliest-anchor rule, closing re-anchor tier-inversion — [inv 5]). Revocation stays per-credential (a
`kills[]` targeting the individual `cred.said`). No new manifest role and no set-commitment SAD — bulk is
the ordinary anchor, at width.

**Bulk trades batch-unlinkability for cost, and that is the whole choice.** Single issuance anchors each
credential at its own position, so two credentials from a cohort are unlinked. Bulk co-locates N commitments
in one event, so a **presented** credential is linkable to its issuance batch (an onlooker who sees the
presentation and the public chain learns it was one of the N issued together — the issuer and rough time
were already visible, but the batch makes it exact). So there are **two modes, and the issuer picks by its
privacy need:**

- **Single issuance** — unlinkable, one anchor each. **Use it when the cohort must not be linkable** (a
  sensitive population).
- **Bulk issuance** — cheap, but batch-linkable. Use it when the cohort is not sensitive (a graduating class
  already public).

There is deliberately **no blinded-set third mode** (cheap _and_ unlinkable): the batch-linkability it would
remove is marginal over the issuer + time any presentation already reveals, and a use case that truly needs
unlinkability at scale issues singly and accepts the cost. `MAXIMUM_ANCHOR_BATCH` (the `anchors` list bound)
is a pinned constant — settle the exact value at the encode.

## Registrar — migration-first, single-binding, recovery

A **registrar** (a government, or any authority with a member roll) binds real people to IEL prefixes and
issues them credentials holding their data. The value proposition is **one person ↔ exactly one prefix**
— if a person can bind to *multiple* prefixes the registrar loses (double-vote, sybil). Enforcing that
single binding is the whole job.

**The primary path is migration, not greenfield enrollment.** Almost every adopting org already has its
users behind an existing login (a site, an app, an SSO). The realistic onboarding is to **migrate** those
users — get the data in the old system encoded into a self-sovereign VDTI credential issued to the right
party. Greenfield mailed-token enrollment (a person with no prior account) is the exception, one backend
among several.

**Single-binding comes for free from the old system.** An existing platform already enforces
one-account-per-person — that is just its user management. Migration binds each existing account to one
prefix, so the old system's account uniqueness **is** the uniqueness constraint; the nullifier-list
machinery (below) is only needed for greenfield enrollment, where no prior account exists.

**The migration flow binds two proofs in one exchange — both required:**

- **WHO** — the user authenticates to the old platform with its existing login, proving "I am account
  `X`." This is the org's own auth, whatever it already runs.
- **WHICH** — the migration request is signed by the user's new VDTI prefix `P` (its `t_use`), proving "I
  control `P`."
- The issuer then pulls `X`'s data, issues a credential with `issuee = P`, anchors it, and records
  `X ↔ P`. Drop the `P`-signature and someone could migrate `X`'s data onto an attacker's prefix; drop
  the login and anyone could claim to be `X`.

**Two auth modes — a normal login and a step-up login.** Step-up is a second factor out of band from the
login: a one-time code to a contact on file (low stakes); the **mailed token** (the greenfield mechanism
reused — physical possession of something sent to the address on record); a knowledge factor from the old
account (a recent statement / transaction); or an in-person / video ID check (highest stakes). Step-up is
**recommended on a first bind** and **enforced on any re-bind** (the `exists` case — see the trait and the
recovery ladder), so a stolen password alone can never re-bind an already-enrolled subject.

**The `Registrar` trait — "prove the requester, return their data."** The trait is the seam between
VDTI's generic issuance machinery and the org's private logic: the org implements **authenticate the
requester** (however it already does — an existing login, a mailed token, step-up factors) → return the
data to embed, or abort; plus a **binding check** — a **new** subject binds under either mode (normal login or step-up, step-up **recommended**); an
**already-bound** subject (`exists`) — every re-bind, including recovery — **enforces step-up** (a normal
login alone must not re-bind an existing subject), and the re-bind **replaces** the binding, preserving
single-binding. VDTI supplies the rest — receive the bind request over exchange, issue +
anchor the credential to the presented prefix, record the binding, and run the revoke-old / issue-new
recovery path. **One trait, three backends:** **migration** (an existing login), **greenfield** (a mailed
high-entropy token plus a public spent-token SEL of random nullifiers, enforcing single-use for people
with no prior account), and **recovery** (step-up factors). Same house pattern as the ESSR capability
traits and the replay-cache trait; interface shapes are implementation, not doctrine.

**The old system is a bridge — and this is the value.** During migration it stays up: users log in to
migrate, and it is the fallback if someone loses their new keys (log in again → revoke the old credential
→ re-issue to a new prefix). As migration completes it shrinks to just the binding map, then retires.
Crucially, **after** a user migrates, that credential is anchored and self-sovereign (they hold `P`'s
keys), so a *later* breach of the old system cannot **present** it (the holder alone controls `P`) **nor
re-bind** it — the subject now **exists** in the binding map, and a re-bind of an existing subject
**enforces step-up** (a normal login can do a _first_ bind, never a re-bind). So the old system's auth
strength bounds a **one-time enrollment window**, not a permanent takeover vector — the whole point is to
transfer trust off a central login onto a self-sovereign identity, once.

**Data encoding.** The trait hands back the org's data; VDTI shapes it into the credential's `claims`
(blinded per §Claim-gating where privacy matters). The org owns its data → claims mapping (app-layer,
toolkit-assisted). The only residual private state the org keeps is the **binding map** (subject `X` ↔
prefix `P`, for re-issuance / recovery) — minimal, and envelope-encryptable in a SEL.

**Recovery ladder — maps onto the KEL compromise tiers, no new mechanism:**

- **Lost signing key, prefix survives** (tier-1) — rotate with the reserve; the credential stays valid
  (same prefix); re-fetch its bytes from the replicated record store. No registrar.
- **Lost one device, multi-device IEL** — surviving members evict the dead member KEL via `Evl`/`cut`;
  the prefix survives, the credential stays valid. No registrar.
- **Total loss (reserve gone / whole IEL dead)** (tier-2) — reincept a **new** prefix, then re-run the bind.
  This is an **`exists`** case (the subject is already bound), so **step-up auth is enforced** (a normal login
  alone cannot re-bind): the registrar **revokes the old credential first, then issues** a new one to the new
  prefix, and the binding map **replaces** `X ↔ P_old` with `X ↔ P_new` (never a second binding for `X`).
  "True recovery." Credential loss can't destroy the data — the credential is a re-fetchable SAD and its
  source of truth is the registrar's own records, so re-issuance regenerates it (no credential-backup service;
  a user-encrypted backup is circular).

**Deployable services (so a registrar doesn't roll its own):** an **envelope-encryption service** (secures
the binding map with the org's own keys) and a **local sadstore-only service** (the org runs its own
record store).

**Honest soft spots — the registrar stays the trust boundary:** a compromised login can complete a **first**
enrollment (a first bind) — mitigate with step-up for high stakes; it **cannot re-bind** an already-enrolled
subject, because a re-bind is an `exists` case where **step-up is enforced**, so a login breach never becomes
a permanent takeover of an existing binding. Registry data quality (duplicate accounts → duplicate bindings);
and single-binding is registrar-**attested**, not independently verifiable by outsiders (only the registrar
holds the map). A **ZK nullifier** would remove even the map, but
production SNARKs aren't post-quantum; the token / login approach is the answer within our crypto suite.

## Protocols as primitives — compose, don't couple

The presentation flow uses a secure transport, but **credentials must not be transport-aware.** So:

- **Credentials depends on IPEX, never on ESSR.** IPEX gives integrity + attribution; it does not depend
  on ESSR. **ESSR composes at the edge** — a *private* disclosure runs IPEX-in-ESSR, chosen where the
  exchange is wired up, not baked into credentials. Confidentiality stacks without credentials knowing.
- **Exchange stays a feature.** The 1:1 authenticated-encryption envelope is the ESSR primitive; group
  keying + SAD-store delivery + custody are the exchange feature.
- Ship **one reference composition** (the mail example, or a documented IPEX-over-exchange adapter) so
  app authors don't re-wire the security-critical freshness binding and reintroduce replay.

## Attribution

The presentation/issuance protocol is **IPEX** (Smith & Feairheller, draft-ssmith-ipex-00) — credited
and linked in `vdti-area-ipex.md` and `protocols/ipex.md`, described in our own greenfield voice as an
independent, non-wire-compatible adaptation. Credentials adds no attribution of its own beyond that and
ESSR's.

## Boundary / residuals

- **What credentials are acceptable** (trusted issuers, required claims, freshness bar) is the relying
  party's application decision — not on the credential, not in the protocol.
- **Revocation freshness** is bounded by the consumer's read strategy (fail-secure walk vs. fail-open
  lookup vs. timeout) — an application choice, not a protocol guarantee.
- **Bearer copy-race** (issuance → first redemption) and **registrar attestation** (single-binding rests
  on the registrar not losing its own identity) are the standing residuals above.
