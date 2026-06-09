Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Leaf semantics

Each leaf evaluates against chain state and a signed request. Leaves return satisfied / unsatisfied. (`del` and `mem` are bracket-only forms, not leaves — `del` is matched by self-traversing issuers, `mem` flattens to `iel` member leaves; both are covered below.)

### `iel(prefix)` — IEL authentication

The leaf is satisfied iff the controlling party satisfies the IEL's own **authentication** policy at the IEL state the flow fixes — the **pinned `Evl`/`Icp` state-marker** in the anchored flow (the verifier reconstructs the authentication state as-of that marker), the **IEL tip** in the current-state flow. `iel(X)` *defers to X's authentication*: it treats X as an autonomous entity and accepts X's own rule for who acts as X. You don't reach inside X's factors, and you inherit X's threshold — if X's authentication is 2-of-3, `iel(X)` demands 2-of-3. (Authentication is the entity's outward-facing act-as policy — distinct from its **governance**, which gates X's own self-mutation and is never what an external `iel(X)` evaluates.)

This is recursive — `iel(P)`'s check evaluates P's authentication policy, which may itself contain `iel(...)` (directly, or via a one-arg `mem(group)` in an aggregate). The recursion terminates at a singleton's `kel` leaves — the base case of member resolution.

`iel(X)` and `mem(X, group)` both reach entity X, but differently. `iel(X)` **defers** to X's autonomy — it accepts X's own authentication, at X's own threshold, for who acts as X (X authorizes as an institution). `mem(X, group)`, by contrast, takes X's **published roster** for the named group and lets the *referencing* policy compose over those members at a threshold/weights **it** chooses — see [`mem`](#mem--membership-roster-array). Both are first-class for foreign X in **general** policies (application, issuance, withdrawal); the difference is *who sets the bar* (X's authentication vs. the referencing policy).

Within an IEL's *own* `governance` / `authentication` / `delegation` policies, `iel` is **never hand-written**. Those policies use only a one-arg `mem(group)` (aggregate) or `kel()` (singleton); `iel` appears solely as what `mem(group)` expands into and as the resolution primitive each member recurses through — see [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

### `mem` — membership-roster array

`mem` names a **group** of a membership roster and resolves to one `iel(member_i)` leaf per member of that group. It has two arities:

- **two-arg `mem(prefix, group)`** — names the `group` group of the roster published by **foreign IEL `prefix`**. The reference is **explicit** (both the IEL prefix and the group) because a foreign roster is referenced from outside the owning entity, so the policy must name which IEL's roster and which group. First-class in **general** policies (application, issuance, withdrawal): any such policy may splice IEL X's `executives` group via `mem(X, executives)`.
- **one-arg `mem(group)`** — names the `group` group of the **host** IEL's own roster, with the prefix **implicit**: it is supplied by the enclosing `iel(X)` descent (the marker the anchored walk pinned, or the tip in the current flow). It is the **only** `mem` form an IEL's own three policies may use (its own roster only, never a foreign one), and it is **cycle-forced**, not mere sugar: the IEL's prefix commits to its `(authentication, governance, …)` policies, so an own-policy that named its own prefix would close a content-address cycle (the prefix depends on the policy that would have to name it). See [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

The `group` label matches `^[a-z_-]{1,16}$` (lowercase `a`–`z`, underscore, hyphen; 1–16 characters; no digits, no uppercase). The roster is a SAD that the IEL commits to — its SAID burned into the IEL, distinct from `governance` / `authentication` / `delegation` — mapping group labels to sets of member IEL prefixes (a member may sit in several groups). `mem(X, group)` is distinct from `iel(X)`: `iel(X)` defers to X's whole authentication, while `mem(X, group)` takes X's published group and composes over it at the referencing policy's own bar.

`mem` is an **array value**, not a standalone leaf — only legal inside a composer's `[...]`, where it flattens in place and concatenates with its siblings:

- inside `thr(k, [mem(prefix, group)])` → `thr(k, [iel(m1), …, iel(mn)])` — *k of that group's members*, with **k chosen by the referencing policy**, not by any member's own threshold. Each member still authenticates via their own authentication policy (`iel(mi)`).
- inside `wgt(M, [([mem(prefix, group)], w), …])` → each member becomes `(iel(mi), w)` — every member of the group carries weight `w`.
- the enclosing `[...]` is a **concat container**: multiple `mem` groups and single expressions mix freely — `thr(2, [mem(org, execs), mem(org, board), kel(K)])` flattens to one child list (`execs` members ++ `board` members ++ `kel(K)`).

This is the membership/composition split. Two levels compose: the **roster level** (which group, how many, or what weight — chosen by the referencing policy) and the **member level** (how each individual proves they act — their own `iel` authentication). The roster lives with the entity (who is in each group); the thresholds/weights live with the policy (how much each member counts here). Adding a member edits the roster, never the policy; changing the bar edits the policy, never the roster.

**Canonical flatten order.** A `mem` array flattens its members in a **canonical order — member
prefix ascending (qb64 byte order)** — so the issuer and verifier lay down identical pin slots and
the [walk-order pinning](pinning.md#pinning-evidence-pins) stays deterministic across parties. Order within
the enclosing `[...]` is preserved between siblings (each `mem` expands in place); only the members
*within* one `mem` are canonically ordered.

**Rosters carry groups, not weights.** A roster maps group → member set; weight is the *referencing
policy's* per-group assignment on the `wgt` branch. So weight only exists post-flatten. Overlap
resolves at **satisfaction**, not expansion: if a member sits in two spliced groups (e.g.
`mem(org, admins)` at weight 2 and `mem(org, members)` at weight 1), each occurrence still lays down
its own pin slot, but the member is **credited once, at its maximum weight** — it counts once, at its
highest group, toward the threshold. (In a `thr` splice there are no weights, so the member simply
counts once — standard distinct-party threshold.)

**Crediting is recursive; pins are not.** Deduplication is a **satisfaction-counting** operation, not
an expansion one. The full expansion fixes the **pin slots** positionally — every occurrence keeps
its slot (the [walk-order pinning](pinning.md#pinning-evidence-pins) stays deterministic, *independent of
roster overlap*), and a duplicate occurrence the issuer doesn't rely on is simply `null`. Crediting,
by contrast, collapses same-prefix duplicates across the **whole recursive credited set** — every
flattened member of the composer's `[...]`, any explicit `iel(member)` sibling in the same bracket,
*and* the same prefix reached through a nested `thr` / `wgt` / `pol` / `and`. So a member reachable
both via `mem(org, staff)` and as an explicit `iel(alice)` sibling is credited **once** (max weight
on a `wgt`), never double toward the threshold, while still occupying every pin slot its occurrences
lay down. This is the fail-secure choice — one identity reached two ways cannot clear a multi-party
gate alone.

The roster's point-in-time resolution rides the IEL state the flow already fixes. The DSL leaf names a **group** (and, for the foreign form, a **prefix**), not a roster SAID. In the anchored flow a **two-arg `mem(prefix, group)`** resolves against `prefix`'s tip-current roster; a **one-arg `mem(group)`** resolves against the roster in the **reconstructed snapshot of the enclosing `iel(X)` state-marker** — the *same* snapshot that marker fixed the authentication from, **reused** rather than separately pinned (NEW-B). Reuse is the security choice: a dedicated roster slot would let an issuer pin an authentication-recent marker against a roster-stale one and resurrect a removed member, so the one-arg roster is bound to the same marker the authentication came from. In the current-state flow both forms resolve at the IEL tip.

### `kel(prefix)` — KEL key match (tier-agnostic)

The leaf is satisfied iff the request is backed by the **current key material** of the KEL identified by `prefix`, **at the key role the operation requires**. `kel(K)` says only "K authorizes" — it is **tier-agnostic**. The operation's `required_tier` selects *which* of K's key roles must be exercised: tier-1 (signing key), tier-2 (rotation material), tier-3 (rotation + recovery material). A policy is authored once, naming who and at what threshold; the event being authorized supplies the key-role context. This is how dual-sig governance works without a separate dual-sig policy: a governance event's tier raises every `kel(K)` leaf's key-role demand (a tier-3 recovery-class event makes each leaf require K's tier-3 material), while the policy stays tier-agnostic. "Current" means the material in effect at the KEL's tip (the most-recent establishment event). The common case — an ordinary signed request — is tier-1, the signing key.

`kel` is the only leaf that resolves directly to cryptographic key material — no recursive policy evaluation. It's the base case of authorization at the device layer, and `satisfies_kel` is already tier-parameterized (`s.tier >= required_tier`). The precise **tier → key-role mapping** (which key material each tier demands) settles with the key-role model and is tracked in the deviations log; the framing here — tier-agnostic leaf, operation supplies the key role — is fixed.

### `del(prefix, N)` — delegation placeholder (self-traversing)

`del(prefix, N)` is a **non-enumerable placeholder**, not a leaf with a pinned slot. It names a
delegating IEL `prefix` and a maximum delegation **depth** `N` (a natural number ≥ 1, counting
hops; `del(X)` is sugar for `del(X, 1)` — a direct delegate). It is satisfied by a **presented
issuer** that **self-traverses up** its own delegation chain to `prefix` within `N` hops.

It is **never expanded**: a delegator's delegated set is unbounded and lives delegate-side, so the
verifier cannot materialize "all delegates of X." Instead each presented issuer carries the
evidence on its *own* chain (the self-recording handshake — see [*Delegation handshake*](delegation.md#delegation-handshake--self-recording)),
and the verifier walks **up** from the issuer, at each hop:

- **consent** — the lower link's `Icp.delegating` names its parent's prefix, and its serial-1
  `Evl.delegating` names the parent's `Del`-event SAID (the back-pointer);
- **authorization** — the verifier **direct-looks-up** the back-pointed event on the parent's chain
  (no enumeration of any delegated set). The resolved event **must be a `Del`** — the lookup rejects
  any other kind — and the verifier confirms it **adds** the lower link in its `delegated` list. This
  kind constraint is load-bearing: both `Del` and `Rsc` carry a `delegated` list (`Del` adds, `Rsc`
  removes), so a back-pointer permitted to resolve to a `Rsc` would let a *removal* read as an
  authorization. Authorization is read only from a `Del`'s additions.
- **no rescission** — the verifier walks the parent IEL to its **tip** confirming no `Rsc` of the
  lower link. Independent of the kind constraint above (which pins the back-pointer to an authorizing
  event); this catches a rescission landed *after* the `Del`. Defense in depth.

The rescission check is at the parent's **current tip** (F), so a delegate rescinded after issuance
denies — this is the [loss-of-trust semantic](../event-logs/iel/) (`Rsc` invalidates downstream
attestations from a delegated party). It is **always** performed, independent of the credential's
`immune` flag (`immune` scopes to withdrawal only — see [*Withdrawal*](withdrawal.md#withdrawal)).

**Depth is policy-level.** The verifier checks the self-traversed chain length `≤ N`. On-chain
delegation is **unbounded** — a delegator delegates freely; any context that needs to bound
re-delegation writes a tighter `del(X, M)` in **its own** policy. There is no on-chain per-edge
budget and no sub-delegator tightening (and so no `Del` event-shape change for depth). Traversal is
additionally bounded by the always-passed `max_depth`; exceeding either `N` or `max_depth` denies
(fail-secure).

**`del(X)` is not `X`.** It authorizes `X`'s *delegates*, not `X` itself — self-issuance needs
`X` to self-delegate, or a separate leaf naming `X`.

**Multi-issuer — count distinct.** `del` lives only inside a composer's `[...]` (set-valued like
`mem`) but is never expanded; composers count **distinct presented issuers** (deduped by prefix).
So `thr(2, [del(A), del(B)])` = "2 distinct issuers, each delegated by A *or* B, any combination";
`thr(1, [del(A)])` is the common single case. Each contributing issuer independently supplies its
own anchor pinning (the two-pinning split does not collapse — see [*Policies and Pinnings*](evaluation.md#policies-and-pinnings)).

**Weighted delegation (`wgt`-over-`del`).** `del` is a legal `wgt` subject, so an issuance policy can
weight delegators: `wgt(M, [([del(A, N)], wA), ([del(B, K)], wB), …])` credits an issuer delegated by
`A` within `N` at `wA`, by `B` within `K` at `wB`. An issuer matching several placeholders — e.g. a
deep delegate satisfying both `del(A, ≥1)` and `del(B, ≥2)` on one lineage — is credited **once at its
maximum weight**, distinct issuers summed, `sum ≥ M` (identical dedup-by-max to a member in two `mem`
groups; one issuer cannot stack delegators' weights — fail-secure). The self-traversals are driven by
which `del` placeholders exist, not by weights; weight is aggregation-side metadata applied at the
composer, so weighted delegation adds no extra walk cost.

### `pol(said)` — Policy nesting

The leaf is satisfied iff the nested policy is also satisfied.

### Nesting

Composers can wrap any expression — leaves, or other composers:

```
thr(2, [
    iel(P1),
    wgt(50, [([kel(K1)], 30), ([kel(K2)], 30)])
])
```

The verifier evaluates inside-out: each leaf evaluates against its chain state; composers aggregate results.

### `and([expr, ...])` — conjunction (separation of duties)

`and([expr, ...])` is the **conjunction** composer: satisfied iff **every** child expression is
*independently* satisfied. Where `thr` / `wgt` count distinct parties over a **union**, `and` imposes
a **per-branch** requirement — the tool for **separation of duties** ("≥1 board member **and** ≥1
executive"), which a union threshold cannot express. `thr(2, [mem(board), mem(exec)])` is cleared by
two board members, and even nested `thr(2, [thr(1, [mem(board)]), thr(1, [mem(exec)])])` collapses to
the same union under the recursive-dedup rule (see *Leaf semantics → `mem`*). A conjunction is the
only way to require *each* pool independently.

- **No threshold / weight argument** — it is all-of. Its children are full `expr`s (a leaf or a
  composer), **never** a bare `mem` / `del`: set-valued forms flatten only inside `thr` / `wgt`, so to
  conjunct a pool you wrap it (`and([thr(1, [mem(org, board)]), thr(1, [mem(org, execs)])])`).
- **At least two children.** A one-child `and` is just the child; an empty `and([])` is vacuously
  satisfied (a no-op gate, the same hazard as `thr(0)`) — the parser **rejects** fewer than 2 children.
- **Evaluation.** Every child is evaluated (no short-circuit — children must drain their pin slots so
  the cursor stays deterministic, exactly like `thr` / `wgt`). `and` is satisfied iff **all** children's
  credited sets are non-empty; on success it returns the **union** of those sets (so an enclosing
  threshold still counts distinct parties), else ∅. Identical in all three evaluators (anchored
  pin-walk, issuance, current-mode).

**Distinctness caveat — `and` does not force distinct people over overlapping pools.** `and`
guarantees each *branch* is satisfied; it guarantees the *satisfiers* are **distinct only when the
branches draw from disjoint identity pools** (board ∩ execs = ∅). If the pools **overlap**, one party
who sits in both branches **satisfies both alone** — `and([thr(1, [mem(org, board)]), thr(1, [mem(org,
execs)])])` is cleared by a single person who is both a board member and an executive (the credited
union is just `{alice}`). An author must **not** assume `and` enforces "two different people"; it
enforces "each pool is met." Guaranteed-distinct separation of duties over *overlapping* pools needs a
matching / max-flow construct, which is **out of scope** — `and` covers the disjoint-pool case, the
usual SoD setup (different roles staffed by different people). **When distinctness matters, the policy
author is responsible for ensuring the branches' pools are disjoint.**

**Scope.** Allowed wherever any composer is (general, IEL/SEL `governance` / `authentication` /
`delegation` / `operation`, issuance, withdrawal, current-mode), under the same leaf constraints as
`thr` / `wgt` (an aggregate's own policy may use only one-arg `mem(group)`; a singleton only `kel`). Child
order is preserved (author-meaningful for pin slots, like `thr` siblings), and the
[canonical DSL string form](verifier-behavior.md#verifier-behavior) applies.

