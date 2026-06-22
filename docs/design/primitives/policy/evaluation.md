# Evaluating a policy — two modes, one composer

Part of the policy layer — see [`policy.md`](policy.md) for the language and
[`documents.md`](documents.md) for where a policy lives.

A policy is evaluated in one of **two modes**, depending on the question being asked:

- **As-issued — *was this validly issued?*** Resolve each leaf **as of the position the document
  pins** (the issuer's identity state at the moment of issuance). The proof that the named parties
  acted is **already on the chain** — the committed anchors the document's pins reach
  ([`documents.md`](documents.md)). This is how a document's **authorizing** condition is checked
  when it spans separate identities.
- **Current — *does the presenter control the named identities right now?*** Resolve each leaf at
  the **chain tip** (the identity's current members and keys). The proof is **live signatures over
  a fresh challenge** the verifier issues. This is how a document's **acceptance** condition is
  checked.

The split is by *question*, not by policy shape. The same policy expression can be evaluated in
either mode; what changes is where each leaf reads its state and what counts as proof that the
named party acted.

## One shared composer, two leaf resolvers

The two modes share their entire composing logic and differ only at the leaves.

- **The composer is identical in both modes.** The `thr` / `wgt` / `and` / `pol` logic — credited
  set, distinct-by-identity counting, per-identity-max weight, `and` over disjoint pools, the
  threshold check — is the same code regardless of mode. **The composer never knows which mode it
  is in.** It calls the leaf resolver, combines the results, and applies the
  [composition rules](policy.md#composition-rules).
- **The leaf resolver is mode-specific.** Each leaf needs two things: the **state** it resolves
  against, and the **proof** that the named party acted. Both differ by mode:

  | | State | Proof that the party acted |
  |---|---|---|
  | **as-issued** | the identity's members + threshold **as of the document's pin** | the **committed on-chain anchors** the pins reach — the proof is already in the chain |
  | **current** | the identity's members + threshold **at the chain tip** | **live signatures** over a fresh, single-use **challenge** |

  The `del(X, N)` leaf differs the same way, and is **bounded the same way** in both modes — the
  verifier walks **up** from the presented party at most `N` hops (and never beyond a verifier-wide
  work cap) to reach `X`, denying fail-secure if either is exceeded: as-issued, it resolves each
  hop's delegation as of the pin and checks the grant's grandfather ancestry against the rescission
  cut-off; current, it confirms the delegate controls its identity now and that no hop is rescinded
  as of the tip. In both modes "is this delegation rescinded?" is the **positive lookup** of
  [`policy.md`](policy.md), never a scan.

So evaluation is one function over the policy expression, parameterized by a resolver. The
as-issued and current entry points are thin wrappers that pick the resolver and assemble its
inputs (the pins, or the challenge and the presented signatures). Everything above the leaves is
shared.

## The to-tip freshness step is mandatory for trust

An **as-issued** resolution answers only "was this validly issued, as of its pin." It does **not**
answer "is the issuer still trustworthy now." A forged extension of a dormant chain is a clean
linear extension — there is no divergence for the as-issued path to notice — so as-issued alone
can be fooled into honoring an issuer that has since been revoked, rescinded, or has diverged.

Therefore **any trust-granting acceptance must run the as-issued resolution *and* a to-tip
freshness step**: walk each contributing chain to its current tip and confirm the issuer is not
revoked, not rescinded, and not divergent, and that the chain's current state is fresh (not stale
per the federation's freshness signal). This loss-of-trust check is read against
**multi-source / witnessed** current state, never a single source's possibly-stale claim — a
single stale or malicious source could hide a revocation. The as-issued resolver alone is
**insufficient** to grant trust; the to-tip step is what catches a since-revoked issuer or a
forged dormant extension. The walk semantics and freshness rules are the verification doctrine's —
[`../../protocol-doctrine.md`](../../protocol-doctrine.md).

## The verification-token interface — the seam to the primitives

The policy layer reads **no chain directly** and holds no live connection to a chain source.
Instead it consumes **verification tokens** produced by the chain primitives' verifiers. A token
is the immutable result of verifying one chain once — position-addressable and resumable — and
**holding a token is itself the proof the chain was verified** (verify-before-use, with no
opportunity to read unverified state). This interface is what the policy layer **declares** and
the primitives **implement** — the dependency is inverted, which is what breaks any
policy-depends-on-primitive / primitive-depends-on-policy cycle.

The resolver asks a token for exactly three things:

- **An identity's members and threshold as of a position** (or at the tip) — what `id(X)` resolves
  against. Supplied by the IEL verifier's token.
- **A delegation's live status** — whether `X` granted the delegation, whether it has been
  rescinded (the positive lookup), and the grandfather cut-off — what `del(X, N)` resolves against,
  walking up at most `N` hops. Supplied by the IEL and SEL verifiers' tokens.
- **The events a chain has committed to as of a position** — the committed anchors that prove, in
  as-issued mode, that the named party acted. Supplied by every contributing chain's token.

The primitives must therefore make their verification **tokenizable**: a token is bound to a
position, can be reused, and can be **resumed forward** to a later tip when the to-tip freshness
step needs current state. Token reuse is transitive — a token's reusability depends on every chain
it leans on (the devices beneath an identity, the delegators above it, the federation that
witnesses it), not on that one chain alone — so a change anywhere beneath an upper-layer event is
visible to a holder of the upper token. The token mechanics, resume semantics, and the transitive
freshness rule are the verification doctrine's
([`../../protocol-doctrine.md`](../../protocol-doctrine.md)); this layer only declares the three
questions above and consumes the answers.

## What the primitives implement

The tokens this layer names are produced by the per-primitive verifiers:

- [`../data/event-logs/iel/`](../data/event-logs/iel/) — resolves an identity's members + threshold
  at a position, and reads the delegate list a `del` leaf needs. *(Per-primitive doctrine; landed
  separately.)*
- [`../data/event-logs/kel/`](../data/event-logs/kel/) — resolves a member device's key state,
  the base case `id` recursion bottoms out in. *(Per-primitive doctrine; landed separately.)*
- [`../data/event-logs/sel/`](../data/event-logs/sel/) — the single-owner data log a delegation's
  rescission lookup is read from. *(Per-primitive doctrine; landed separately.)*
