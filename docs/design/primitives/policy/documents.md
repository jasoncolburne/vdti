# Documents — where policy lives

Part of the policy layer — see [`policy.md`](policy.md) for the language and the two authorization
mechanisms.

Policy lives on **documents**, never on a chain event. A document is a [SAD](../data/sad/sad.md): an
application-defined payload (a credential, an attestation, a signed declaration) that carries,
alongside its content, the policy that authorizes it. This doc states the generic shape every
policy-bearing document shares — the two conditions it can carry, and how its issuer context is
fixed by its **anchoring position** so it cannot name a more permissive past. The lifecycle of any
specific document kind (how a **credential** is issued and revoked, for instance) is a feature
layered above this one — see [`../../features/credentials/`](../../features/credentials/) _(a
feature; forthcoming)_.

## A document's two conditions

A policy-bearing document carries up to two policy references (each the SAID of a policy SAD —
[`policy.md`](policy.md)):

- **The authorizing condition — who could issue it.** When a single identity issues the document,
  this condition is **structural**: the issuer's own IEL **`t_use`** threshold authorizes the
  issuance, and there is no policy expression to evaluate (the structural mechanism,
  [`policy.md`](policy.md), covers it). The condition becomes an explicit policy only when issuance
  **spans separate identities** (for example `thr(2, [id(A), id(B), id(C)])` — any two of three
  institutions) — there it is evaluated **as-issued** ([`evaluation.md`](evaluation.md)).
- **The acceptance condition — who may present it.** The rule for who may later present or act on
  the document. This is evaluated **current** — against live proof at the time of presentation
  ([`evaluation.md`](evaluation.md)).

The composing logic is the same language in both cases; only how each leaf is resolved differs by
mode.

## The anchoring position — fixing the issuer context

A document **carries no self-asserted pin.** Its issuer context is fixed by the **anchoring
position**: the issuer commits the document to its IEL by authoring an **anchoring event** — an IEL
`Ixn` whose `manifest.anchors` names the document. For a **credential** — a direct-anchored SAD,
never a SEL — that is the issuance `Ixn` naming the **issuance commitment**
`hash('vdti/iel/v1/targets/commitment:{issuer}:{cred.said}')`, and that anchor **is** the validity
proof ([`../data/event-logs/event-shape.md`](../data/event-logs/event-shape.md)). That event sits at
a fixed serial on the append-only chain, and it fixes the context two ways at once:

- It **commits the point-in-time** so a verifier can find and verify the issuer's context — the
  state immediately **before** the anchoring event transitively commits the issuer's identity (its
  members and threshold) and its whole delegation chain, because each is committed by the events the
  anchoring event builds on.
- It **cannot be backdated.** The anchoring position is append-only — it cannot be inserted into the
  past — so the issuer cannot make the document appear authorized under a more permissive past while
  it actually anchors in the restrictive present.

So **authority-affecting resolution is judged by the anchoring position.** The _document_ carries no
self-asserted value the issuer chose — the as-of is read from where it is anchored, and there is no
separate machinery to establish "when": the append-only chain is the clock.

**Under multiple anchors of the same commitment, the anchoring position is the EARLIEST.** A cred's
issuance commitment is a flat hash in `anchors[]`, not a chain event, so nothing structurally
forbids re-anchoring it — and a later re-anchor must not move the as-of forward. Concretely: a **T1
`Ixn` re-anchor** landing _after_ a **T2 `Rev`** revoked the cred would push a naive latest-anchor
floor _past_ the revocation, silently un-revoking it — a **tier inversion**. So the feature layer
resolves the issuance position as the **first** matching anchor on the fresh inception→tip walk and
treats any later re-anchor as **inert** (never trusting a supplied or cached later position). The
earliest floor is load-bearing alongside the fresh tip — the two ends of the revocation walk's range
([`evaluation.md`](evaluation.md)).

A document that is instead **looked up by a derived address** rather than presented — a
multi-identity **attestation SEL** (below), or any looked-up attested SAD — is located through the
serial-1 `Pin` (its `v1`) of its anchoring SEL. That `Pin` names a position but is **checked, not
trusted**: the verifier enforces `Pin.pin ==` the anchoring `Ixn`'s `previous`, so a served `Pin`
can't resolve under a stale roster (the custody SEL-anchor mechanism,
[`../data/sad/custody.md`](../data/sad/custody.md)).

### Non-circular

The document's SAID is fixed from its content; only **then** does the issuer author the anchoring
event whose `manifest` names that SAID. So the anchoring event commits to a document that is already
fixed, and the document is found and dated through an event that already exists — no cycle, and no
value the document must carry to point back at the chain.

## Multi-identity authorization — independent attestations

A document whose **authorizing** condition spans separate identities cannot collapse to a single
joint identity (a threshold over devices is not a threshold over identities). The document instead
names a custodied **`issuers` SAD** — `{ issuers: [ prefix, … ] }` — and **each authorizing identity
issues its own attestation independently**: each authors its own attestation SEL over the document,
self-flooring to its own IEL through that SEL's serial-1 `Pin` and self-locating by re-deriving its
prefix. The authorizing policy (`thr` / `wgt` / `and` over `id()`) is satisfied by the **positive
lookup** of each named issuer's attestation — there are **no per-party pins**, no scan, and no
cross-issuer coordination: each issuer anchors on its own chain at its own pace, and the verifier
reads each one's authorization **as-of its own anchoring position**.

- An issuer that has **not** attested contributes no anchored position and is **not credited** — a
  malicious co-issuer cannot manufacture another's attestation, exactly as a single issuer cannot
  backdate its own.
- The threshold reads the count of **distinct** attesting identities (by prefix,
  [`policy.md`](policy.md)).

## Recursive

A document issued under another document is anchored just as a credential is. A document `D` issued
under credential `C` is committed by `D`'s **own** anchoring event on its issuer's IEL; `C`'s
context is committed by, and found through, that position, since the issuer holds and anchored `C`.
Authority is judged by `D`'s own anchoring position. The same append-only-chain-is-the-clock rule
applies at every level — with no self-asserted value carried at any level.

## Delegation in a document

A document may be authorized by a **delegate** of an identity — the `del(X, N)` leaf
([`policy.md`](policy.md)). The document commits the **one authorizing path** it was issued under:
each hop's delegating link is the content-addressed prefix recomputed from
`(delegator, vdti/sel/v1/targets/delegation, delegate)` (delegator = owner, delegate = data — the
same scheme as a rescission lookup,
[`../data/event-logs/iel/delegation.md`](../data/event-logs/iel/delegation.md)), **committed on the
delegator's (owner's) own identity** (owner-rooted — only the owner anchors at a derived locus) and
pinning up to `X`, so the verifier **derives** the authorizing chain from committed data and walks
it (up to `N` hops, and never beyond the verifier-wide work cap — exceeding either denies,
fail-secure) — the presenter furnishes nothing to prune. Per hop the verifier checks that the
delegation was granted and that the grant has not been **rescinded** (a positive `kills[]` match,
fail-secure by default — [`policy.md`](policy.md)).

The **grandfather** check is **per hop, on that hop's own chain** — there is no cross-chain clock:
the **issuer's own hop** is grandfathered iff the document's **anchoring position** is an ancestor
of the issuer's rescission bound; each **upstream hop** iff _that hop's committed grant position_ is
an ancestor of _that hop's_ bound, on the granting delegator's chain. The document is authorized iff
**every** hop is grandfathered. (A grant authored before trust was withdrawn at its hop stays valid;
one that post-dates that hop's bound does not — and the bound is **set once** at rescission — the
rescission is a terminal `Trm`, so it can't be moved later to un-kill, nor tightened earlier; a
mis-set bound is recovered operationally, not by adjusting it.)

To give several delegators kill-authority over a document, issue it under a threshold spanning their
legs, so every leg lands in the committed chain. The delegation mechanics — the delegate list, the
rescission lookup, and the bound — are the IEL primitive's; see
[`../data/event-logs/iel/`](../data/event-logs/iel/).

## Timestamps are advisory

A document may carry feature-level timestamps (an issued time, an expiry). They are **advisory**:
they never decide a structural or cryptographic check. An expired document is _expired_ — the caller
inspects that and decides — but all ordering and grandfather questions use the **anchoring
position** (append-only ancestry), never a clock. The chain primitives themselves carry no
timestamps at all; only feature layers do, and only as feature semantics.

## Public versus private issuance

Whether an outside observer can tell that an identity issued a particular document is a property of
how the document is located and disclosed, not of the policy layer. A document whose locating
address is derivable from its public content is **discoverable**; one whose content carries a
high-entropy nonce derives an unguessable address and stays **private** until its holder discloses
it. Either way the policy that authorizes the document, and the anchoring that fixes its context,
work identically. The addressing and privacy rules live with the SEL primitive and the credentials
feature — [`../data/event-logs/sel/`](../data/event-logs/sel/).
