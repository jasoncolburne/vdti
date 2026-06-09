# Policy DSL

Canonical specification of vdti's policy DSL — the expression language used to encode authorization rules across the event-log primitives.

A **policy** is a [SAD](../sad/sad.md) whose content is a DSL expression. The IEL primitive references policies (governance, delegation, and authentication); the SEL primitive references policies (governance and operation); applications reference policies for their own authorization needs. The DSL is the language; Policy SADs are the storage format; the verifier evaluates DSL expressions against signed requests and the relevant chain state.

This doc states the surface (the primitives that make up the DSL), their semantics, and how composition works. It does not enumerate per-primitive doctrine (which lives in [`event-logs/event-shape.md`](../event-logs/event-shape.md), the per-primitive specs, and [`../../protocol-doctrine.md`](../../../protocol-doctrine.md)) and does not specify the verifier implementation algorithm (which lives in `lib/vdti` planning material).

**Reading order for the policy primitive group**: this doc (surface + grammar) → [`leaf-semantics.md`](leaf-semantics.md) → [`iel-policy-structure.md`](iel-policy-structure.md) → [`pinning.md`](pinning.md) → [`delegation.md`](delegation.md) → [`evaluation.md`](evaluation.md) → [`withdrawal.md`](withdrawal.md) → [`examples.md`](examples.md) → [`verifier-behavior.md`](verifier-behavior.md).

## Where policies appear

Policies are referenced by Policy SAD SAIDs from chain-event fields:

- **IEL `governance`** (required at inception; evolved via `Evl`) — gates IEL self-mutation events (key rotation, policy/roster changes, decommission).
- **IEL `authentication`** (required at inception; evolved via `Evl`) — the entity's act-as policy: what every `iel(prefix)` leaf (and each `mem` member) evaluates against. Outward-facing — it never gates the IEL's own chain events.
- **IEL `delegation`** (optional at inception; evolved via `Evl`) — gates IEL delegation events (`Del` / `Rsc`).
- **SEL `governance`** (declared at SEL `Icp`; evolved via `Evl`) — gates SEL events (`Evl` / `Rpr` / `Dec`).
- **SEL `operation`** (declared at SEL `Icp`; evolved via `Evl`) — gates SEL operational events (`Est` / `Ixn`).
- **Application-defined policy references** — applications may attach policy SAIDs to their own data structures (credentials, signed requests, custody SADs) following the same pattern.

An IEL's three policies — `governance` / `authentication` / `delegation` — are further constrained in *what they may contain* by whether the IEL is **aggregate** or **singleton**; see [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

In each case the field holds a `Digest256` pointing at a Policy SAD. The verifier dereferences, parses the DSL expression, and evaluates it.

## The DSL surface — 8 primitives

```
kel(prefix)        iel(prefix)        pol(said)
mem(group)   mem(prefix, group)   del(prefix, N)
thr(M, [...])      wgt(M, [...])      and([...])
```

Two chain-state **leaves** (`kel`, `iel`), one policy-reference **leaf** (`pol`), two
**bracket-only** forms — a **membership array** (`mem`) and a **delegation placeholder** (`del`)
— and three **composers** (`thr`, `wgt`, `and`). Neither bracket-only form is a leaf:

- `mem(group)` / `mem(prefix, group)` is an **array value** — it names a *`group`* of a
  membership roster and resolves to one `iel(member_i)` leaf per member of that group. The
  **two-arg** form names a *foreign* IEL `prefix`'s roster; the **one-arg** form names the
  **host** IEL's own roster (the prefix is implicit — the enclosing `iel(X)` descent supplies it),
  and is the only form an IEL's own three policies may use. It flattens in place inside a
  composer's `[...]`.
- `del(prefix, N)` is a **non-enumerable placeholder** — it names a *delegating* IEL `prefix` and
  a maximum delegation **depth** `N` (a natural number ≥ 1, counting hops; `del(X)` is sugar for
  `del(X, 1)` = direct delegate). It is **never expanded** (a delegator's delegated set is
  unbounded and delegate-side, so the verifier cannot materialize it); instead it is matched by
  the **distinct presented issuers** that self-traverse up to `prefix` within `N` hops (see
  [`del`](leaf-semantics.md#delprefix-n--delegation-placeholder-self-traversing) and *Policies and Pinnings*). `del(X)` is
  not the same as naming `X`: it authorizes `X`'s *delegates*, not `X` itself.

Both `mem` and `del` are legal only **inside a composer's `[...]`**, never as a standalone
`expr`. The `[...]` is a concat container, so member-arrays, delegation placeholders, and single
expressions mix freely (`[mem(org, staff), kel(K)]` = org's staff members followed by `kel(K)`).
Members are IELs (individuals are IELs; devices are KELs), so each flattened `mem` member
authenticates via their own authentication policy (`iel(mi)`), while the referencing policy
composes over them at the threshold/weights it chooses (see *Leaf semantics*). The grammar:

```
expr      ::= leaf | composer
leaf      ::= kel(prefix) | iel(prefix) | pol(said)
bracketed ::= mem(group)                    # host IEL's own `group` roster (one-arg; prefix implicit): flattens to iel(member) leaves
            | mem(prefix, group)            # foreign IEL prefix's `group` roster: flattens to iel(member) leaves
            | del(prefix, N)                # delegation placeholder: never expanded; matched by distinct presented issuers
composer  ::= thr(M, [elem, ...]) | wgt(M, [([wgt_elem, ...], w), ...]) | and([expr, ...])
elem      ::= expr | bracketed              # a bracketed form appears only here; mem flattens its members in place
wgt_elem  ::= kel(prefix) | iel(prefix) | mem(group) | mem(prefix, group) | del(prefix, N)   # wgt subjects are membership-style ONLY — no pol, no composer (NEW-E)
```

`mem` and `del` appear only as an `elem` (inside `[...]`), never as a standalone `expr`. Every
counting composer's threshold is `M ≥ 1` — a zero threshold is satisfied by the empty set (a no-op
gate), so the parser rejects `M = 0`. `and([expr, ...])` is the **conjunction** composer — no
threshold (it is all-of), but its children are full `expr`s (a bracketed `mem` / `del` must be
wrapped in a `thr` / `wgt` first) and it requires **≥ 2** of them (a one-child `and` is just the
child; an empty `and([])` is a vacuous no-op gate, rejected); see
[`and`](leaf-semantics.md#andexpr----conjunction-separation-of-duties). A `wgt` entry's subject is a bracketed
array `[wgt_elem, ...]` paired with a weight `w` that every one of its flattened children carries,
**but `wgt` subjects are restricted to the membership-style forms `kel` / `iel` / `mem` / `del`** —
**no `pol`, no composer** (NEW-E). A composer or `pol` subject would let one weight spread per
*credited prefix* across a nested set (threshold-easing), whereas these four credit a clear
membership-style set; the parser **rejects** a composer/`pol` `wgt` subject (fail-secure — see
*Composition semantics*). So `([mem(group)], w)` weights each member of that group at `w`, and a
single leaf is just the one-element case `([kel(K)], w)`. The bracket carries no bloc semantics:
`([a, b], w)` desugars losslessly to `(a, w), (b, w)`, so the array is purely a concise way to
attach one weight to several subjects. Every well-formed policy is built from these primitives.

#### Rust

These are suitable Rust shapes. `Policy` carries a recursive `PolicyExpr` so the DSL grammar (nesting, `pol(said)`) maps directly onto the data structure. `Prefix` and `Said` are distinct newtypes over `Digest256` — a chain identifier vs. a point-in-time event SAID — so the two never silently interchange (see *Verifier behavior*).

```rust
pub struct Prefix(Digest256);             // chain identifier (entity / log)
pub struct Said(Digest256);               // SAID of a specific event or SAD (point-in-time / ordering)

pub enum PolicyExpr {
    Kel(Prefix),                          // chain prefix — device key (tier-agnostic; required_tier picks the role)
    Iel(Prefix),                          // chain prefix — IEL authentication
    Mem(Option<Prefix>, String),          // (roster owner, group label ^[a-z_-]{1,16}$); None = own/host-implicit (one-arg mem(group)), Some(p) = foreign (two-arg mem(p, group)); roster array — only valid as a composer element (inside [...]), flattens in place
    Del(Prefix, u32),                     // (delegator IEL prefix, max delegation depth N ≥ 1 in hops); placeholder — only valid as a composer element, never expanded
    Pol(Said),                            // nested Policy SAD SAID
    Thr(u64, Vec<PolicyExpr>),            // threshold M ≥ 1, sub-expressions
    Wgt(u64, Vec<(PolicyExpr, u32)>),     // threshold M ≥ 1; (sub, weight) pairs. Each sub is membership-style ONLY — kel/iel/mem/del, no pol/composer (NEW-E). Source brackets desugar to per-element pairs (each element carries w); a Mem sub expands to per-member (iel, w) at flatten
    And(Vec<PolicyExpr>),                 // conjunction — satisfied iff EVERY child satisfied; ≥ 2 children (separation of duties). Children are full exprs, never bare mem/del
}

pub struct Policy {
    said: Said,
    expr: PolicyExpr,
}
// Withdrawal authority and immunity are NOT properties of a generic Policy — they live on the
// CREDENTIAL (see §Withdrawal): an optional `withdrawal: Option<String>` DSL field and an
// `immune: bool` flag. A bare Policy carries no withdrawal state.

pub struct Pinning {
    said: Said,
    pins: Vec<Option<Said>>,              // one per prefix occurrence, in the verifier's pre-order walk order
}
```

## Open items

1. **Verifier evaluation algorithm.** Recursion semantics (`iel(P)` evaluating against P's own policy, which may itself contain `iel(...)`), cycle detection, depth limits, caching strategies. Belongs in implementation specs once `lib/vdti` planning advances.

2. **Extension points.** The DSL is closed at the primitive level (8 primitives — leaves, the `mem` membership array, the `del` delegation placeholder, the `thr` / `wgt` / `and` composers). Future primitives (new chain types; new leaf semantics) would require DSL extension. The fail-secure rule (§Verifier behavior) makes additions safe under skew — an old verifier encountering an unrecognized primitive denies the **whole** policy rather than silently ignoring a possibly-restrictive new term.

## Forward-refs

- [`event-logs/iel/`](../event-logs/iel/) — IEL primitive (subsequent sub-issue); references this doc for governance / delegation / authentication policy evaluation
- [`event-logs/sel/`](../event-logs/sel/) — SEL primitive (subsequent sub-issue); references this doc for SEL governance / operation
- `lib/vdti` — verifier implementation; evaluates DSL expressions per this spec
