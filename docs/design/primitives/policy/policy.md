# Policy — the document authorization layer

VDTI has **two authorization mechanisms, kept separate**:

- **Chain events are authorized structurally.** A KEL, IEL, or SEL event is valid by its own
  structure — a device's own key (KEL), an identity's threshold over its member devices (IEL),
  single-owner ownership (SEL). The chain primitives carry **no policy** and evaluate no policy
  for their own events.
- **Documents are authorized by policy.** A credential — or any other document — carries an
  authorization condition written in a small composable **policy language**, matched at the
  application.

This layer is that policy language plus how it is evaluated. It sits **above** the chain
primitives: it consumes their verification (an identity's members and threshold as of a position,
a delegation's live status, the events a chain has committed to) and never the reverse. Keeping
the dependency pointing one way — the policy layer depends on the primitives' verification
interface, the primitives depend on nothing here — is what keeps the layering acyclic. The
interface the layer declares is the **verification-token** seam in [`evaluation.md`](evaluation.md).

Keeping the two mechanisms apart is a security decision, not a convenience. A chain event that
chose its own authorization policy would let the author point that policy at a stale, more
permissive past — the backdate surface the structural rules exist to close. Authorization that a
third party relies on (who issued a credential, who may present it) is exactly where a policy
language earns its keep, and that lives on the document, never on the chain.

**Reading order for this layer:** this doc (the language and the two mechanisms) →
[`documents.md`](documents.md) (where policy lives and how a document anchors its context) →
[`evaluation.md`](evaluation.md) (the two ways a policy is evaluated, and the seam to the
primitives).

## A policy is a SAD

A policy is a [SAD](../data/sad/sad.md) whose content is a policy-language expression, identified
by its [SAID](../data/sad/said.md). Two byte-identical policies derive the same SAID, so an
identical authorization rule is one shared object the whole system can reference. A document names
a policy by that SAID; the verifier fetches it, parses the expression, and evaluates it.

## The policy language

Three things a policy can name, and three ways to combine them.

```
expr     ::= id(prefix)            # an identity
           | del(prefix)           # a live delegate of an identity
           | pol(said)             # another policy, by its SAID
           | thr(M, [expr, ...])   # M of the listed sub-policies
           | wgt(M, [(expr, w), ...])   # weighted: sub-policies carry weights, total ≥ M
           | and(expr, ...)        # every listed sub-policy, each independently

prefix   ::= an entity's IEL prefix        # identity = prefix
said     ::= the SAID of another policy    # a point-in-time reference
M, w     ::= positive integers (≥ 1)
```

Every counting threshold `M` is `≥ 1`; a zero threshold is satisfied by the empty set (a gate
that authorizes nobody), so it is rejected. `and(...)` takes `≥ 2` sub-policies — a one-child
`and` is just the child, and an empty `and` is a vacuous gate — and is rejected otherwise.

### The leaves

- **`id(X)` — an identity.** Satisfied when entity `X`'s identity is satisfied: the verifier
  resolves `X`'s IEL (its member devices and its threshold over them) and checks that enough of
  `X`'s devices acted. `id(X)` *defers to X*: it accepts whatever rule `X`'s own identity sets for
  who acts as `X`, at `X`'s own threshold. This is the recursive base of the language — a policy
  that names other identities bottoms out in their IELs, which bottom out in member device keys.

- **`del(X)` — a live delegate of `X`.** Satisfied by a party that holds a live, non-rescinded
  delegation from `X`. Whether a delegation is still live is answered by a **positive lookup** —
  the verifier derives one address and reads it (present → rescinded; absent → live) — never by
  scanning a chain for the absence of a rescission. `del(X)` is **not** `id(X)`: it authorizes
  `X`'s delegates, not `X` itself. See [`documents.md`](documents.md) for how a delegate's
  authorizing chain is committed and walked.

- **`pol(said)` — another policy.** Satisfied when the referenced policy is satisfied. This lets a
  reusable rule be named once and composed into many policies; the reference is by SAID, so the
  nested policy is fixed (a different rule is a different SAID).

### The composers

- **`thr(M, [...])` — threshold.** Satisfied when at least `M` of the listed sub-policies are
  satisfied. The common single case is `thr(1, [id(P)])` — "`P`."

- **`wgt(M, [(expr, w), …])` — weighted threshold.** Each sub-policy carries a weight; satisfied
  when the satisfied sub-policies' weights total at least `M`. A threshold is the special case
  where every weight is `1`.

- **`and(e1, e2, …)` — all-of, over independent pools.** Satisfied when **every** listed
  sub-policy is satisfied. Where a threshold counts satisfiers over one combined pool, `and`
  requires each pool independently — the tool for separation of duties ("a board member **and** an
  executive"), which a single threshold cannot express.

## Composition rules

These four rules govern how the composers count and combine, and are identical wherever a policy
is evaluated (see [`evaluation.md`](evaluation.md)).

- **Count distinct identities, not controllers.** A counting composer (`thr`, `wgt`) credits by
  **identity prefix**. The protocol cannot tell whether two named identities share a controller —
  pseudonymity is free, since a fresh inception mints a new prefix at will — so `thr(2, [id(A),
  id(B)])` is satisfiable by one controller who holds both `A` and `B`, and counts as two. An
  author who needs genuine multi-party assurance must name **independently-controlled**
  identities; the threshold enforces "two prefixes," not "two people." An identity reached more
  than one way (named directly and again through a nested policy) is credited **once**.

- **Weight is per-identity-max.** When an identity is reached through several weighted branches, it
  is credited **once, at its highest** weight — never summed across branches. One party cannot
  stack a policy's weights to clear a threshold alone (fail-secure).

- **`and` ranges over disjoint pools.** `and` guarantees each branch is satisfied; it guarantees
  the *satisfiers* are distinct only when the branches draw from **disjoint** identity pools. If
  the pools overlap, one party who sits in both satisfies both — `and` enforces "each pool is
  met," not "two different people." When distinctness matters, the author makes the branches'
  pools disjoint.

- **An unrecognized construct denies the whole policy.** A verifier that meets a language construct
  it does not recognize fails the **entire** policy closed — never ignores the unknown term and
  never credits its siblings. This is fail-secure and forward-compatible: a future addition cannot
  be silently dropped by an older verifier into a more-permissive evaluation.

## Forward references

- [`documents.md`](documents.md) — where a policy lives (a document's authorizing and acceptance
  conditions), the pin a document carries to its issuer context, and how that pin is anchored.
- [`evaluation.md`](evaluation.md) — the two evaluation modes (as-issued and current), the shared
  composer with two leaf resolvers, and the verification-token interface this layer declares.
- [`../data/event-logs/iel/`](../data/event-logs/iel/) — the IEL primitive: the identity an `id`
  leaf resolves (members + threshold vector) and the delegate list a `del` leaf reads. *(Per-primitive
  doctrine; landed separately.)*
- [`../data/event-logs/sel/`](../data/event-logs/sel/) — the SEL primitive: the single-owner data
  log a delegation's rescission lookup is read from. *(Per-primitive doctrine; landed separately.)*
