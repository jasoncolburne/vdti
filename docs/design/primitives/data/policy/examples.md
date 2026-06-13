Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Worked examples

**Single-device authentication** — a singleton IEL's own `authentication`, naming one device directly. `dev` is legal **only** inside a singleton IEL's own three policies; everywhere else, authorize by identity (`id`, below):
```
dev(prefix)
```

**IEL authentication** — prove a link to a basic identity:
```
id(prefix)
```

**Membership threshold** — k-of-a-group authentication, with k chosen by this policy (not by the org or its members). The first argument is a **floor `said`** — an IEL event of the org X (it carries X's prefix); the issuer's pinned X-state-marker must be at-or-after it, and the roster resolves at that marker:
```
thr(2, [grp(org_said, staff)])
```

With org X's `staff` group = `{m1, m2, m3}` (resolved from X's roster as-of the issuer's marker, which must be ≥ `org_said`), expands to `thr(2, [id(m1), id(m2), id(m3)])` — any two staff. Adding a fourth member edits the roster; this policy is unchanged. Concatenate groups by listing them: `thr(2, [grp(org_said, staff), grp(org_said, board)])` pools both into one flat child list. Set `org_said` to X's **current tip** (and re-template on rotation) to mean "effectively current members," or to X's **inception event** to mean "anyone *ever* in the group" — the floor makes the freshness intent explicit (see [operations](../../../../operations/credential-issuance-freshness.md)).

**Emergency override**:
```
thr(1, [
    thr(3, [grp(org_said, members)]),
    id(emergency)
])
```

Any three members satisfy, or the emergency identity alone.

**Weight-based membership groups** — an org weights executive / admin / member groups at 3 / 2 / 1, threshold 3 (the groups live in the org's one roster; weight is this policy's per-group valuation):
```
wgt(3, [
    ([grp(org_said, executives)], 3),
    ([grp(org_said, admins)],     2),
    ([grp(org_said, members)],    1)
])
```

With X's roster (as-of the marker, ≥ `org_said`) `executives = {E1, E2}`, `admins = {A1, A2, A3}`, `members = {M1, …}`, this flattens to `wgt(3, [(id(E1), 3), (id(E2), 3), (id(A1), 2), (id(A2), 2), (id(A3), 2), (id(M1), 1), …])`. Satisfied by: one executive (3), two admins (4), three members (3), or one admin + one member (3); one admin alone (2) does not clear. The weights are this policy's valuation of each group — a stricter resource could set `member → 0`; the roster is unchanged. A member in two groups is deduplicated to its highest weight (see *Leaf semantics → `grp`*).

**Aggregate IEL authentication** — an aggregate's own `authentication` composes only over its own roster (one-arg `grp`), never bare prefixes:
```
thr(2, [grp(directors)])
```
"Any 2 current directors authenticate as the aggregate." To require a specific individual, give them a one-element group — `grp(founder)` with `founder = {alice}`. A **singleton's** authentication, by contrast, is `dev`-only — e.g. `thr(2, [dev(device_a), dev(device_b)])` — the base case the `id(...)` recursion bottoms out at (see *[IEL policy structure](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton)*).

**Separation of duties** — `and` requires *each* branch independently, which a union threshold cannot:
```
and([
    thr(1, [grp(org_said, board)]),
    thr(1, [grp(org_said, execs)])
])
```
≥1 board member **and** ≥1 executive. If `board` and `execs` are disjoint this is two different
people; if someone sits on both, that one person satisfies both branches alone — `and` enforces "each
pool is met," not "distinct people" (see *[`and`](leaf-semantics.md#andexpr----conjunction-separation-of-duties)*). For
dual control mixing a pool with a named identity: `and([thr(2, [grp(org_said, admins)]), id(emergency_cosigner)])`
— 2 admins **and** the co-signer. `and` composes inside other composers: `thr(1, [and([id(a), id(b)]),
id(break_glass)])` = (a **and** b) **or** break-glass.

**Distinct identities, not distinct controllers (C6).** Every counting composer credits by **prefix**,
and the protocol cannot tell whether two named identities share a controller (pseudonymity is free).
So `thr(2, [id(a), id(b)])` — and a `grp` whose roster lists `a` and `b` — is satisfiable by a single
controller holding both. Where multi-party assurance matters, the author must choose
**independently-controlled** identities; the threshold counts prefixes, not people (see *[`grp`](leaf-semantics.md#grp--membership-roster-array)* / *[`and`](leaf-semantics.md#andexpr----conjunction-separation-of-duties)*).

