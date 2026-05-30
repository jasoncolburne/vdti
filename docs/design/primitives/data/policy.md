# Policy DSL

Canonical specification of vdti's policy DSL — the expression language used to encode authorization rules across the event-log primitives.

A **policy** is a [SAD](sad/sad.md) whose content is a DSL expression. The IEL primitive references policies (governance and delegation); the SEL primitive references policies (governance); applications reference policies for their own authorization needs. The DSL is the language; Policy SADs are the storage format; the verifier evaluates DSL expressions against signed requests and the relevant chain state.

This doc states the surface (the primitives that make up the DSL), their semantics, and how composition works. It does not enumerate per-primitive doctrine (which lives in [`event-logs/event-shape.md`](event-logs/event-shape.md), the per-primitive specs, and [`../../protocol-doctrine.md`](../../protocol-doctrine.md)) and does not specify the verifier implementation algorithm (which lives in `lib/vdti` planning material).

## Where policies appear

Policies are referenced by Policy SAD SAIDs from chain-event fields:

- **IEL `governance`** (required at inception; evolved via `Evl`) — gates IEL self-mutation events.
- **IEL `delegation`** (optional at inception; evolved via `Evl`) — gates IEL delegation events (`Del` / `Rsc`).
- **SEL `governance`** (declared at SEL `Icp`; evolved via SEL `Evl`) — gates SEL events (`Est` / `Ixn` / `Evl` / `Rpr` / `Dec`).
- **Application-defined policy references** — applications may attach policy SAIDs to their own data structures (credentials, signed requests, custody SADs) following the same pattern.

In each case the field holds a `Digest256` pointing at a Policy SAD. The verifier dereferences, parses the DSL expression, and evaluates it.

## The DSL surface — 6 primitives

```
kel(prefix)        iel(prefix)        del(prefix)
pol(said)
thr(M, [...])      wgt(M, [...])
```

Three chain-state **leaves** (`kel`, `iel`, `del`), one policy reference **leaf** (`pol`), two **composers** (`thr`, `wgt`). The grammar:

```
expr   ::= leaf | composer
leaf   ::=  kel(prefix) | iel(prefix) | del(prefix) | pol(said)
composer ::= thr(M, [expr, ...]) | wgt(M, [(expr, w), ...])
```

Every well-formed policy is built from these primitives.

### Shape

If the SAID we are verifying is anchored in the KEL event with `kel.prefix == kel_prefix`
and also satisfies one of the IELs (`iel_prefix_1` or `iel_prefix_2`) governance policies by being anchored in
its descendent KELs, the policy below is satisfied.

#### Policy (resource holder's gate)

```json
{
    "said": "...",
    "policy": "wgt(3, (kel(X_prefix), 2), (iel(Y_prefix), 1), (iel(Z_prefix), 1))"
}
```

#### Pinning (issuer's evidence pins)

A Pinning SAD carries a list of `Pin` entries. Each pin names a `kel_said` (the anchoring KEL event SAID) and optionally an `iel_said` (the IEL event SAID being vouched for). `iel_said` is present when the pin's purpose is to vouch for an IEL state via its anchoring KEL event; it's absent when the pin is a direct KEL anchor (for bare `kel(P)` leaves in policies that reference the KEL directly — e.g., an IEL's own governance policy with `kel(device)` leaves).

The verifier dispatches by leaf kind: `iel(P)` / `del(P)` leaves use only pins with `iel_said` set; `kel(P)` leaves can use any pin (looking at its `kel_said`). Pairing the anchoring KEL with the vouched-for IEL eliminates the verifier's search-for-anchor step; the verifier still walks each chain to verify integrity per the trust-boundary principle.

```json
{
    "said": "{pinning_said}",
    "saids": [
        {
            "said": "{pin_said_1}",
            "iel_said": "{Z_iel_event_said}",
            "kel_said": "{Z_anchoring_kel_event_said}"
        },
        {
            "said": "{pin_said_2}",
            "iel_said": null,
            "kel_said": "{X_kel_event_said}"
        }
    ]
}
```

#### Rust

These are suitable Rust shapes. `Policy` carries a recursive `PolicyExpr` so the DSL grammar (nesting, `pol(said)`) maps directly onto the data structure.

```rust
pub enum PolicyExpr {
    Iel(Digest256),                       // chain prefix
    Kel(Digest256),                       // chain prefix
    Del(Digest256),                       // delegator IEL prefix
    Pol(Digest256),                       // nested Policy SAD SAID
    Thr(u64, Vec<PolicyExpr>),            // threshold M, sub-expressions
    Wgt(u64, Vec<(PolicyExpr, u32)>),     // threshold M, (sub, weight) pairs
}

pub struct Policy {
    said: Digest256,
    expr: PolicyExpr,
}

pub struct Pin {
    said: Digest256,
    iel_said: Option<Digest256>,
    kel_said: Digest256,
}

pub struct Pinning {
    said: Digest256,
    saids: Vec<Pin>,
}
```

## API Surface

Two entry points covering the two halves of the auth flow:

```rust
// Anchored check — cred / SAD validation against issuer-provided evidence.
// Uses the Pinning as the evidence claim; pinned events are the chain state
// the policy evaluates against.
pub fn evaluate_anchored_policy(
    policy: &Policy,
    pinning: &Pinning,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError>;
```

```rust
// Current-state check — challenge-response / fresh-control verification.
// No pinning, no anchors. The bearer presents one or more attestations over
// `commitment` (a digest). Each attestation is the signer's KEL prefix +
// a primary signature, plus optionally a recovery signature for tier-3
// dual-sig contexts. The verifier checks each attestation against the
// signer's CURRENT signing key (and recovery key, when present) at the
// KEL's tip, and aggregates per the policy's structure.
pub struct Attestation {
    signer: Digest256,                       // signer's KEL prefix
    signature: Signature,                    // signature by current signing key
    recovery_signature: Option<Signature>,   // signature by current recovery key (tier-3)
}

pub fn evaluate_policy(
    policy: &Policy,
    commitment: &Digest256,
    attestations: &[Attestation],
    required_tier: Tier,
) -> Result<bool, PolicyError>;
```

`evaluate_anchored_policy` returns `Ok(true)` iff the pinned evidence shows the expected anchors hosted at the required tier or above. `evaluate_policy` returns `Ok(true)` iff the provided signatures over `commitment` cover the policy's leaves at current chain state with the required tier. Both return `Ok(false)` for clean unsatisfied; `Err(_)` for malformed inputs / fetch failures.

The auth flow typically calls both: `evaluate_anchored_policy` validates the cred is genuinely issued (anchored to a delegating chain); `evaluate_policy` validates the bearer currently controls the policy the cred names (challenge-response signed under current state).

### Policies and Pinnings

#### Use case

Let's say we have an access control policy we declare that permits resource access by specifying
prefixes of IELs that endorse credentials bound to user identities. A credential SAID must be
anchored in a way that satisfies the control policy for the credential to be valid.

The credential control policy the server is configured with may be:

```
thr(1, del(iel_prefix_1), del(iel_prefix_2), del(iel_prefix_3))
```

which says that prefixes 1 through 3 may delegate to other prefixes, and only a single signature
from any delegate of prefixes 1 through 3 is required to satisfy the policy.

When a credential is issued, a 'pinning' is burned into it to pin the events that satisfy the
policy:

```
{
    "saids": [
        {"iel_said": "iel_said_2", "kel_said": "kel_anchoring_said"}
    ]
}
```

When verifying, first a check is done to ensure the pinning satisfies the bounds of the
control policy (is the pinned said a valid event from an iel delegated from one of prefixes 1
through 3?) and the signature requirements (is the credential said anchored in KEL descendents of
the pinned IEL?).

```rust
let iel_prefix_1 = Digest256::from_qb64("KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")?;
let iel_prefix_2 = Digest256::from_qb64("KBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")?;
let iel_prefix_3 = Digest256::from_qb64("KCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")?;

let policy_string = format!(
    "thr(1, del({}), del({}), del({}))",
    iel_prefix_1, iel_prefix_2, iel_prefix_3
);
let policy = parse_policy(&policy_string)?;

// The cred carries a Pinning SAD; the issuer constructed it to name the IEL
// event SAID(s) on the delegated chain that anchor the credential.
let pinning = parse_pinning_sad(&sadd_fetch(&cred.pinning_said)?)?;

let expected_anchors: HashSet<Digest256> = [credential_said].into_iter().collect();

let satisfied = evaluate_anchored_policy(
    &policy,
    &pinning,
    &expected_anchors,
    Tier::One,
)?;
```

Implementation:

```rust
pub fn evaluate_anchored_policy(
    policy: &Policy,
    pinning: &Pinning,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    eval_expr(&policy.expr, pinning, expected_anchors, required_tier)
}

fn eval_expr(
    expr: &PolicyExpr,
    pinning: &Pinning,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    match expr {
        PolicyExpr::Iel(prefix) => {
            for pin in &pinning.saids {
                if let Some(iel_said) = &pin.iel_said {
                    if satisfies_iel(iel_said, &pin.kel_said, prefix, expected_anchors, required_tier)? {
                        return Ok(true);
                    }
                }
            }
            Ok(false)
        }
        PolicyExpr::Kel(prefix) => {
            for pin in &pinning.saids {
                if satisfies_kel(&pin.kel_said, prefix, expected_anchors, required_tier)? {
                    return Ok(true);
                }
            }
            Ok(false)
        }
        PolicyExpr::Del(delegating_prefix) => {
            for pin in &pinning.saids {
                if let Some(iel_said) = &pin.iel_said {
                    if satisfies_del(iel_said, &pin.kel_said, delegating_prefix, expected_anchors, required_tier)? {
                        return Ok(true);
                    }
                }
            }
            Ok(false)
        }
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, pinning, expected_anchors, required_tier)
        }
        PolicyExpr::Thr(m, subs) => {
            let mut count: u64 = 0;
            for sub in subs {
                if eval_expr(sub, pinning, expected_anchors, required_tier)? {
                    count += 1;
                }
            }
            Ok(count >= *m)
        }
        PolicyExpr::Wgt(m, weighted) => {
            let mut sum: u64 = 0;
            for (sub, w) in weighted {
                if eval_expr(sub, pinning, expected_anchors, required_tier)? {
                    sum += *w as u64;
                }
            }
            Ok(sum >= *m)
        }
    }
}

// Each satisfies_* helper walks the relevant chain(s) to verify integrity per
// the trust-boundary principle, then checks the structural relationships
// between the verified events.

fn satisfies_iel(
    iel_event_said: &Digest256,
    kel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let kel = verify_kel_event(kel_event_said)?;
    let iel = verify_iel_event(iel_event_said)?;
    Ok(
        iel.prefix == *leaf_prefix
            && kel.anchors.contains(iel_event_said)
            && kel.tier >= required_tier
            && expected_anchors.is_subset(&kel.anchors)
    )
}

fn satisfies_kel(
    kel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let kel = verify_kel_event(kel_event_said)?;
    Ok(
        kel.prefix == *leaf_prefix
            && kel.tier >= required_tier
            && expected_anchors.is_subset(&kel.anchors)
    )
}

fn satisfies_del(
    iel_event_said: &Digest256,
    kel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    expected_anchors: &HashSet<Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let kel = verify_kel_event(kel_event_said)?;
    let iel = verify_iel_event(iel_event_said)?;
    // iel_event is on a chain that leaf_prefix delegated to
    Ok(
        iel.delegating_prefix == *leaf_prefix
            && kel.anchors.contains(iel_event_said)
            && kel.tier >= required_tier
            && expected_anchors.is_subset(&kel.anchors)
    )
}
```

## Leaf semantics

Each leaf evaluates against chain state and a signed request (or candidate identifier, for `del`). Leaves return satisfied / unsatisfied.

### `iel(prefix)` — IEL member-set membership

The leaf is satisfied iff the signed request was authored by a current member of the IEL identified by `prefix`. "Member" means: the request's signing party satisfies the IEL's own `governance` policy at the IEL's current chain tip.

This is recursive — `iel(P)`'s leaf check delegates to P's own governance policy evaluation. The recursion terminates at non-`iel` leaves (`kel` and `del`).

### `kel(prefix)` — KEL signing-key match

The leaf is satisfied iff the signed request was authored by the **current signing key** of the KEL identified by `prefix`. "Current" means the signing key in effect at the KEL's tip (the most-recent establishment event's `publicKey`).

`kel` is the only leaf that resolves directly to a cryptographic key — no recursive policy evaluation. It's the base case of authorization at the device layer.

### `del(prefix)` — IEL delegated-set membership

The leaf is satisfied iff the candidate identifier is currently in the delegated set of the IEL identified by `prefix`. The candidate is provided by the verifier context (typically: the chain whose authority is being evaluated). The delegated set is computed by walking the IEL's chain and tracking `Del` / `Rsc` events.

The delegated set's content is **point-in-time** at the IEL's chain tip — `del` evaluates against current delegated state by default. Earlier delegations rescinded via `Rsc` are not in the current set; this is the [loss-of-trust semantic](event-logs/iel/) (Rsc retroactively invalidates downstream attestations from delegated parties).

### `pol(said)` — Policy nesting

The leaf is satisfied iff the candidate policy is also satisfied.

### Nesting

Composers can wrap any expression — leaves, or other composers:

```
thr(2, [
    iel(P1),
    wgt(50, [(kel(K1), 30), (kel(K2), 30)])
])
```

The verifier evaluates inside-out: each leaf evaluates against its chain state; composers aggregate results.

## Worked examples

**Single-key authorization** — used by simple SEL governance where one device controls the SEL:
```
kel(operator_kel_prefix)
```

**IEL membership** — used by IEL governance for a basic identity:
```
iel(self_iel_prefix)
```

**Multi-IEL threshold** — federation governance with 3-of-5:
```
thr(3, [iel(member1), iel(member2), iel(member3), iel(member4), iel(member5)])
```

**Federation weighted with emergency override**:
```
wgt(60, [
    (iel(member1), 40),
    (iel(member2), 40),
    (iel(member3), 40),
    (kel(emergency_key), 100)
])
```

Any two members satisfy (80 ≥ 60), or the emergency key alone (100 ≥ 60).

## Composition semantics

- **Leaves evaluate independently.** Each leaf's chain walk is independent; the verifier doesn't share state across sibling leaves.
- **Composers are pure aggregators.** They take leaf / sub-composer results and produce satisfaction signals. No side effects.
- **Boundedness.** Per-policy evaluation has bounded cost — finite expression tree, finite chain walks per leaf. Million-event chains evaluate in O(chain length) per leaf, parallelizable across leaves.
- **Deterministic.** Given a fixed chain state and signed request, evaluation is deterministic. Verifiers across nodes converge.

## Verifier behavior

The verifier evaluates an anchored policy by checking that the issuer-provided Pinning contains pin SAIDs which, when dereferenced, satisfy the policy expression AND host the expected anchors at the required tier.

High-level pseudo-code matching `evaluate_anchored_policy`:

```
evaluate_anchored_policy(policy, pinning, expected_anchors, required_tier) -> bool:
    return eval_expr(policy.expr, pinning, expected_anchors, required_tier)

eval_expr(expr, pinning, expected_anchors, required_tier) -> bool:
    match expr:
        iel(prefix) => any(satisfies_iel(pin.iel_said, pin.kel_said, prefix, expected_anchors, required_tier)
                           for pin in pinning.saids if pin.iel_said is Some)
        kel(prefix) => any(satisfies_kel(pin.kel_said, prefix, expected_anchors, required_tier)
                           for pin in pinning.saids)
        del(prefix) => any(satisfies_del(pin.iel_said, pin.kel_said, prefix, expected_anchors, required_tier)
                           for pin in pinning.saids if pin.iel_said is Some)
        pol(said)   => eval_expr(parse_dsl(sadd.fetch(said).content).expr,
                                 pinning, expected_anchors, required_tier)
        thr(M, ss)  => count(eval_expr(s, pinning, expected_anchors, required_tier) for s in ss) >= M
        wgt(M, ws)  => sum(w for (s, w) in ws if eval_expr(s, pinning, expected_anchors, required_tier)) >= M

# Each satisfies_* helper walks both chains for verification, then checks the structural
# relationships between the verified events. Walks are required per the trust-boundary
# principle; pinning eliminates the search step (knowing the anchoring KEL event up-front)
# but not the verification step.

satisfies_iel(iel_event_said, kel_event_said, leaf_prefix, expected_anchors, required_tier):
    kel = verify_kel_event(kel_event_said)
    iel = verify_iel_event(iel_event_said)
    return iel.prefix == leaf_prefix
        AND kel.anchors.contains(iel_event_said)
        AND kel.tier >= required_tier
        AND expected_anchors.is_subset(kel.anchors)

satisfies_kel(kel_event_said, leaf_prefix, expected_anchors, required_tier):
    kel = verify_kel_event(kel_event_said)
    return kel.prefix == leaf_prefix
        AND kel.tier >= required_tier
        AND expected_anchors.is_subset(kel.anchors)

satisfies_del(iel_event_said, kel_event_said, leaf_prefix, expected_anchors, required_tier):
    kel = verify_kel_event(kel_event_said)
    iel = verify_iel_event(iel_event_said)
    # iel_event is on a chain that leaf_prefix delegated to
    return iel.delegating_prefix == leaf_prefix
        AND kel.anchors.contains(iel_event_said)
        AND kel.tier >= required_tier
        AND expected_anchors.is_subset(kel.anchors)
```

**Semantics notes:**

- **Pinning context propagates uniformly.** A `pol(said)` recursion uses the same `pinning`, `expected_anchors`, and `required_tier` as the outer evaluation. Nested policies see the same evidence.
- **Cycles are structurally impossible.** `pol(said)` references are content-addressed; a cycle would require two Policy SADs to mutually contain each other's SAIDs, requiring a Blake3-256 collision. No runtime cycle check needed.
- **Depth bound.** Implementations should impose a soft depth limit on `pol()` recursion (e.g., 16 levels) and deny on exceeding — implementation concern, out of scope here.
- **Tier check is in the leaf helpers, not the composers.** `verify_*_anchors_by_said` consults the KEL anchor chain and rejects anchors hosted on KEL events below `required_tier`. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized expression kinds → deny.** Forward-compatibility: older verifiers encountering newer DSL primitives return unsatisfied for that sub-expression; composer aggregation propagates this as a clean deny rather than a verification crash.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

- **IEL `Evl` / `Dec`** — gated by `governance`
- **IEL `Del` / `Rsc`** — gated by `delegation`
- **SEL `Est` / `Ixn` / `Evl` / `Rpr` / `Dec`** — gated by `governance`
- **Application-defined gates** — credentials, signed requests, etc. — gated by application-specific policy references

## Open items

1. **Verifier evaluation algorithm.** Recursion semantics (`iel(P)` evaluating against P's own policy, which may itself contain `iel(...)`), cycle detection, depth limits, caching strategies. Belongs in implementation specs once `lib/vdti` planning advances.

2. **Extension points.** The DSL is closed at the primitive level (6 primitives — leaves, composers). Future primitives (new chain types; new leaf semantics) would require DSL extension. The forward-compat deny rule (§Verifier behavior) makes additions soft-compatible — old verifiers safely deny on unrecognized expressions.

## Forward-refs

- [`event-logs/iel/`](event-logs/iel/) — IEL primitive (subsequent sub-issue); references this doc for governance / delegation policy evaluation
- [`event-logs/sel/`](event-logs/sel/) — SEL primitive (subsequent sub-issue); references this doc for SEL governance
- `lib/vdti` — verifier implementation; evaluates DSL expressions per this spec
