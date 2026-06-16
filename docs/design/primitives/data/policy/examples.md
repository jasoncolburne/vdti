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

**Membership threshold** — k-of-a-group authentication, with k chosen by this policy (not by the org or its members):
```
thr(2, [grp(prefix, staff)])
```

With org `prefix`'s `staff` group = `{m1, m2, m3}` (resolved from that IEL's roster), resolves to `thr(2, [id(m1), id(m2), id(m3)])` — any two staff. Adding a fourth member edits the roster; this policy is unchanged. Concatenate groups by listing them: `thr(2, [grp(prefix, staff), grp(prefix, board)])` pools both into one flat child list.

> **Reach (foreign `grp`).** A two-arg `grp(prefix, group)` resolves its roster only where its X-state
> marker is **context-supplied**: a **current-mode** policy (X's tip) or an **SEL-gated anchored** policy
> (the SEL's floored `policyPin`). In a credential's **issuance** policy a foreign `grp` credits **nobody** —
> group issuance authority is the creds registry-SEL (see *[leaf semantics →
> `grp`](leaf-semantics.md#grp--membership-roster-array)*). The foreign-`grp` examples below illustrate
> **member resolution / composition**, which is identical across contexts; they are not, on their own, all valid
> issuance policies.

**Emergency override**:
```
thr(1, [
    thr(3, [grp(prefix, members)]),
    id(emergency)
])
```

Any three members satisfy, or the emergency identity alone.

**Weight-based membership groups** — an org weights executive / admin / member groups at 3 / 2 / 1, threshold 3 (the groups live in the org's one roster; weight is this policy's per-group valuation):
```
wgt(3, [
    ([grp(prefix, executives)], 3),
    ([grp(prefix, admins)],     2),
    ([grp(prefix, members)],    1)
])
```

With `prefix`'s roster `executives = {E1, E2}`, `admins = {A1, A2, A3}`, `members = {M1, …}`, this resolves to `wgt(3, [(id(E1), 3), (id(E2), 3), (id(A1), 2), (id(A2), 2), (id(A3), 2), (id(M1), 1), …])`. Satisfied by: one executive (3), two admins (4), three members (3), or one admin + one member (3); one admin alone (2) does not clear. The weights are this policy's valuation of each group — a stricter resource could set `member → 0`; the roster is unchanged. A member in two groups is deduplicated to its highest weight (see *Leaf semantics → `grp`*).

**Aggregate IEL authentication** — an aggregate's own `authentication` composes only over its own roster (one-arg `grp`), never bare prefixes:
```
thr(2, [grp(directors)])
```
"Any 2 current directors authenticate as the aggregate." To require a specific individual, give them a one-element group — `grp(founder)` with `founder = {alice}`. A **singleton's** authentication, by contrast, is `dev`-only — e.g. `thr(2, [dev(device_a), dev(device_b)])` — the base case the `id(...)` recursion bottoms out at (see *[IEL policy structure](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton)*).

**`and` — separation of duties.** `and` requires *each* branch independently, which a union threshold cannot:
```
and([
    thr(1, [grp(org, board)]),
    thr(1, [grp(org, execs)])
])
```
≥1 board member **and** ≥1 executive. For dual control mixing a pool with a named identity:
`and([thr(2, [grp(org, admins)]), id(emergency_cosigner)])` — 2 admins **and** the co-signer. `and` composes
inside other composers: `thr(1, [and([id(a), id(b)]), id(break_glass)])` = (a **and** b) **or** break-glass.
Children are full `expr`s — wrap a pool as `thr(1, [grp(...)])`, never a bare `grp` — and there must be **≥2**
(see *[leaf semantics → `and`](leaf-semantics.md#andexpr----conjunction-separation-of-duties)*).

**`and` enforces "each pool is met," not "distinct people."** Each branch is satisfied by *anyone* in its
pool, and one party may clear several branches:

- **Disjoint pools** (`board ∩ execs = ∅`) — clearing both branches takes **two different people**, one per
  branch. Genuine separation of duties.
- **Overlapping pools** — if `alice` sits on **both** board and execs, her single authentication satisfies
  **both** branches, so she clears the gate **alone**. `and` guarantees distinct *people* only when the
  branches draw from **disjoint** pools.

**A duplicated party — `and` vs `thr` vs `wgt`.** This is the crux: a party reached through several slots
behaves differently per composer. Take `alice ∈ board ∩ execs`:

| Policy | What `alice` alone contributes | Cleared by alice alone? |
|---|---|---|
| `thr(2, [grp(org, board), grp(org, execs)])` | counts **once** in the union `{alice}` (1 < 2) | **No** — needs a 2nd distinct party |
| `wgt(3, [([grp(org, board)], 2), ([grp(org, execs)], 3)])` | credited **once at her max weight** (3, not 2+3) | **Yes** (3 ≥ 3) |
| `and([thr(1, [grp(org, board)]), thr(1, [grp(org, execs)])])` | satisfies **both** branches with one authentication | **Yes** |

The difference is **pooling**: `thr` / `wgt` pool their children into one set and count distinct parties, so a
duplicated party **collapses to one** (counted once / kept at its max weight); `and` **never pools** — it
evaluates **each branch on its own**, so a party in several branches satisfies each. Corollary: `and([id(a), id(a)])` ≡ `id(a)` — the dup is redundant,
`a`'s one authentication covers both branches. (Crediting + recursive-dedup rules: *[verifier behavior →
Composition semantics](verifier-behavior.md#composition-semantics)*; that distinct identities — not
controllers — are counted is **C6** below.)

**Distinct identities, not distinct controllers (C6).** Every counting composer credits by **prefix**,
and the protocol cannot tell whether two named identities share a controller (pseudonymity is free).
So `thr(2, [id(a), id(b)])` — and a `grp` whose roster lists `a` and `b` — is satisfiable by a single
controller holding both. Where multi-party assurance matters, the author must choose
**independently-controlled** identities; the threshold counts prefixes, not people (see *[`grp`](leaf-semantics.md#grp--membership-roster-array)* / *[`and`](leaf-semantics.md#andexpr----conjunction-separation-of-duties)*).

