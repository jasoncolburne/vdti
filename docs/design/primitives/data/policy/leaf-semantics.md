Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Leaf semantics

Each leaf evaluates against chain state and a signed request. Leaves return satisfied / unsatisfied. (`del` and `grp` are bracket-only forms, not leaves — `del` is matched by self-traversing issuers, `grp` resolves to `id` member leaves; both are covered below.)

### `id(prefix)` — IEL authentication

The leaf is satisfied iff the controlling party satisfies the IEL's own **authentication** policy at the IEL state the flow fixes — the **pinned `Evl`/`Icp` state-marker** in the anchored flow (the verifier reconstructs the authentication state as-of that marker), the **IEL tip** in the current-state flow. `id(X)` *defers to X's authentication*: it treats X as an autonomous entity and accepts X's own rule for who acts as X. You don't reach inside X's factors, and you inherit X's threshold — if X's authentication is 2-of-3, `id(X)` demands 2-of-3. (Authentication is the entity's outward-facing act-as policy — distinct from its **governance**, which gates X's own self-mutation and is never what an external `id(X)` evaluates.)

This is recursive — `id(P)`'s check evaluates P's authentication policy, which may itself contain `id(...)` (directly, or via a one-arg `grp(group)` in an aggregate). The recursion terminates at a singleton's `dev` leaves — the base case of member resolution.

`id(X)` and `grp(X, group)` both reach entity X, but differently. `id(X)` **defers** to X's autonomy — it accepts X's own authentication, at X's own threshold, for who acts as X (X authorizes as an institution). `grp(X, group)`, by contrast, takes X's **published roster** for the named group and lets the *referencing* policy compose over those members at a threshold/weights **it** chooses — see [`grp`](#grp--membership-roster-array). The difference is *who sets the bar* (X's authentication vs. the referencing policy). They also differ in **reach**: `id(X)` is matched in **all** general policies (application, issuance, withdrawal), while a foreign `grp(X, group)` resolves its roster only where its marker is **context-supplied** — a general current-mode policy (X's tip), and SEL-gated anchored policies (the SEL's floored `policyPin`) — and credits **nobody** in a credential's **issuance** policy (group issuance authority is the creds registry-SEL; see [`grp`](#grp--membership-roster-array)).

Within an IEL's *own* `governance` / `authentication` / `delegation` policies, `id` is **never hand-written**. Those policies use only a one-arg `grp(group)` (aggregate) or `dev()` (singleton); `id` appears solely as what `grp(group)` resolves to and as the resolution primitive each member recurses through — see [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

### `grp` — membership-roster array

`grp` names a **group** of a membership roster and resolves to one `id(member_i)` leaf per member of that group. It has two arities:

- **two-arg `grp(prefix, group)`** — names the `group` group of the roster published by **foreign IEL `prefix`**. The reference is **explicit** (both the IEL prefix and the group) because a foreign roster is referenced from outside the owning entity, so the policy must name which IEL's roster and which group. It composes over X's **raw roster members at the *referencing* policy's bar** — it does **not** inherit X's own authentication threshold (that is the membership/composition split, below; contrast `id(X)`, which defers to X's threshold). It resolves wherever its marker is **context-supplied** — **general current-mode** policies (X's tip) and **SEL-gated anchored** policies (the SEL's floored `policyPin`) — so e.g. an application policy may splice IEL X's `executives` group via `grp(X, executives)`. In a credential's **issuance** policy a foreign `grp` credits **nobody** (group issuance authority is the creds registry-SEL — see the roster-resolution paragraph below).
- **one-arg `grp(group)`** — names the `group` group of the **host** IEL's own roster, with the prefix **implicit**: it is supplied by the enclosing `id(X)` descent (the marker the anchored walk pinned, or the tip in the current flow). It is the **only** `grp` form an IEL's own three policies may use (its own roster only, never a foreign one), and it is **cycle-forced**, not mere sugar: the IEL's prefix commits to its **whole inception content** (its `authentication` / `governance` / `delegation` policy SAIDs, roster, and nonce), so an own-policy that named its own prefix would close a content-address cycle (the prefix depends on the policy that would have to name it). See [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

The `group` label matches `^[a-z_-]{1,16}$` (lowercase `a`–`z`, underscore, hyphen; 1–16 characters; no digits, no uppercase). The roster is a SAD that the IEL commits to — its SAID burned into the IEL, distinct from `governance` / `authentication` / `delegation` — mapping group labels to sets of member IEL prefixes (a member may sit in several groups). `grp(X, group)` is distinct from `id(X)`: `id(X)` defers to X's whole authentication, while `grp(X, group)` takes X's published group and composes over it at the referencing policy's own bar.

`grp` is an **array value**, not a standalone leaf — only legal inside a composer's `[...]`, where it resolves in place and concatenates with its siblings:

- inside `thr(k, [grp(prefix, group)])` → `thr(k, [id(m1), …, id(mn)])` — *k of that group's members*, with **k chosen by the referencing policy**, not by any member's own threshold. Each member still authenticates via their own authentication policy (`id(mi)`).
- inside `wgt(M, [([grp(prefix, group)], w), …])` → each member becomes `(id(mi), w)` — every member of the group carries weight `w`.
- the enclosing `[...]` is a **concat container**: multiple `grp` groups and single expressions mix freely — `thr(2, [grp(org, execs), grp(org, board), id(X)])` resolves to one child list (`execs` members ++ `board` members ++ `id(X)`).

This is the membership/composition split. Two levels compose: the **roster level** (which group, how many, or what weight — chosen by the referencing policy) and the **member level** (how each individual proves they act — their own `id` authentication). The roster lives with the entity (who is in each group); the thresholds/weights live with the policy (how much each member counts here). Adding a member edits the roster, never the policy; changing the bar edits the policy, never the roster.

**Canonical member order.** Within one `grp`, members are **canonically ordered — member prefix
ascending (qb64 byte order)**. In the deep evidence a `grp`'s [`GrpBlock`](pinning.md#pinning-evidence-pins)
lists its signers in this order (sorted-by-prefix, dedup'd) for **content-addressing**; membership itself is
by-prefix set-contains, **order-independent**. Order within the enclosing `[...]` is preserved between
siblings (each `grp` resolves in place); only the members *within* one `grp` are canonically ordered.

**Rosters carry groups, not weights.** A roster maps group → member set; weight is the *referencing
policy's* per-group assignment on the `wgt` branch. So weight only exists post-resolution. Overlap
resolves at **satisfaction**, not expansion: if a member sits in two spliced groups (e.g.
`grp(org, admins)` at weight 2 and `grp(org, members)` at weight 1), the member is named in **each**
group's `GrpBlock`, but is **credited once, at its maximum weight** — it counts once, at its
highest group, toward the threshold. (In a `thr` splice there are no weights, so the member simply
counts once — standard distinct-party threshold.)

**Crediting dedups recursively; the evidence layer does not.** Deduplication is a **satisfaction-counting**
operation, not an evidence-layer one. The evidence layer has two shapes (see
[*Pinning*](pinning.md#pinning-evidence-pins)): the **policy-text walk** (`id` / `dev`) is **positional** — every
occurrence keeps its slot, and an occurrence the issuer doesn't evidence is simply `null`; a **`grp` leaf** lays
**one `GrpBlock`** naming only the signers (sorted-by-prefix, dedup'd, **no per-member `null`**), so a member
spliced through two groups is named in **each** group's block. Crediting, by contrast, collapses same-prefix
duplicates across the **whole recursive credited set** — every member a `grp` resolves to, any explicit
`id(member)` sibling in the same bracket, *and* the same prefix reached through a nested `thr` / `wgt` / `pol` /
`and`. So a member reachable both via `grp(org, staff)` and as an explicit `id(alice)` sibling is credited
**once** (max weight on a `wgt`), never double toward the threshold, whatever evidence form each occurrence
took. This is the fail-secure choice — one identity reached two ways cannot clear a multi-party gate alone.

The roster's point-in-time resolution rides the IEL state the flow fixes — and in the anchored flow **both forms resolve as-of pinned state** (authored data is anchored; nothing in it reads a live roster). The DSL leaf names a **group** (and, for the foreign form, a **prefix**), not a roster SAID. A **one-arg `grp(group)`** resolves against the roster in the **reconstructed snapshot of the enclosing `id(X)` state-marker** — the *same* snapshot that marker fixed the authentication from, **reused** rather than separately pinned (NEW-B). Reuse is the security choice: a dedicated roster slot would let an issuer pin an authentication-recent marker against a roster-stale one and resurrect a removed member, so the one-arg roster is bound to the same marker the authentication came from. A **two-arg `grp(prefix, group)`** has no enclosing `id(prefix)` descent to ride, so it resolves X's roster as-of a **context-supplied** marker — one the *evaluation context* fixes, never one the invoking party chooses. In the **current-state** flow that marker is X's **tip** (the live read-time identity proof). In an **anchored SEL-gated** policy it is the gating SEL's **governance-ratcheted, floored `policyPin`** entry for X (already ratcheted forward along the per-chain floor), **not** a credential's issuer-supplied issuance pin. That X-marker is **read from context** — there is **no issuer-laid roster-source slot**: a foreign `grp`'s deep evidence is a sparse **`GrpBlock`** naming only the members who signed (see [*Pinning*](pinning.md#pinning-evidence-pins)), and the verifier checks each named signer against X's roster as-of the context marker. The governance gate that resolves a foreign `grp` this way is the general anchored single-policy evaluator (see [`evaluation.md`](evaluation.md)). Membership change stays **forward-only**: a later roster change on X never reaches back to invalidate a document authored against the pinned state — an authorization stays valid until explicitly withdrawn, and loss-of-trust is carried by the rescission and withdrawal walks, which run to tip in both flows, never by tip-resolving a roster.

**Foreign `grp` is not an issuer-pinned issuance leaf.** Because the two-arg marker is context-supplied
(X's tip, or the gating SEL's governance-ratcheted, floored `policyPin`) and **never chosen by the invoking
party**, no one can pick the X-state a foreign `grp` resolves against — so a member X *removed* cannot
backdate an old marker where they were still rostered to credit themselves. This is the structural fix
for the ex-member exposure **on the foreign-`grp` arm**: there is no issuer-supplied marker to backdate, so
the leaf needs **no freshness floor of its own** — the marker it consumes is the gating SEL's `policyPin`
entry for X, already ratcheted forward at the SEL layer. The **`id(issuer)` arm** — a directly-named
aggregate issuer resolving its own authority — is **not** closed by this leaf; it is closed separately by the
floored **registry-SEL composition** (issuance authority resolves against floored state on each entity's own
registry-SEL, composed by reference — see the *grandfather* block in [`pinning.md`](pinning.md)). **Group
issuance authority** — letting a member of X issue credentials while X rotates membership without reissuing
and cuts off a removed member — is therefore **not** this leaf; it is a **registry-SEL** governed by `id(X)`,
where each issuance `Ixn` inherits the SEL's governance-ratcheted, floored `policyPin` (forward-only,
per-event) rather than any issuer-chosen pin. That registry-SEL's **provisioning** (one per IEL, eagerly at
inception, regardless of credential activity — generalized to *every* IEL, issuer or not) is an
IEL/SEL-primitive (**layer-4**) obligation; **issuance** on it is **layer-5** creds-feature work — a
forthcoming feature that composes this primitive — not the policy primitive itself.

**Thresholds count distinct *identities*, not distinct *controllers* (C6).** Every counting composer
(`thr`, `wgt`) credits by **prefix**, and the protocol **cannot** tell whether two named identities
share a controller — pseudonymity is free (a fresh `Icp` nonce mints a new prefix at will). So
`thr(2, [id(A), id(B)])` is satisfiable by a **single** controller holding both `A` and `B`, and a
`grp` whose roster lists two such prefixes counts them as two. An author who needs genuine multi-party
assurance must choose **independently-controlled** identities; the threshold enforces "two prefixes,"
not "two people." (This generalizes the [`and` distinctness caveat](#andexpr----conjunction-separation-of-duties),
the same fact for overlapping pools.)

### `dev(prefix)` — KEL key match (tier-agnostic)

`dev` is legal **only** inside a **singleton** IEL's own `governance` / `authentication` / `delegation` policies — the identity base case. In an aggregate IEL's own policies and in **every** general policy (application, issuance, withdrawal, `readPolicy`) a hand-written `dev` is a **policy-validity error**; a device is named there through a singleton `id` that wraps it (`id(X')` strictly dominates a bare `dev(K)` — the same terminal key-check plus the owner's rotation / recovery / decommission lifecycle, and all other authorization is by identity). See [IEL policy structure — aggregate vs. singleton](iel-policy-structure.md#iel-policy-structure--aggregate-vs-singleton).

This placement is **verifier-enforced at evaluation time, over the fully-`pol`-expanded graph, fail-closed** (DQ2) — *not* an author- or submit-time convention. The verifier threads a `dev_legal` context flag through the one eval walk: it flips **true only on an `id`→singleton descent** (the one legal placement) and is inherited unchanged through `thr` / `wgt` / `and` / `pol`. A `dev` reached with `dev_legal` false — in any general or composed position, or **behind a `pol(said)`** (a `dev`-bearing policy SAD *is* a singleton's own policy, and a singleton's own policies cannot use `pol`, so `dev_legal` is never carried true into a `pol` → such a SAD is rejected when reached from another policy, from **any** source) — is a **policy-validity error**: the verifier returns an error and the **whole** policy denies (never credit-nobody, which would let a sibling leg of `thr(1, [dev(K_bad), id(legit)])` pass). The only legitimate way to reach a device from a general policy is `id(X)`, resolved through X's identity lifecycle. This matters because the verifier's `dev` arm credits `{K}` for **any** `dev` it resolves; the placement check on the expanded graph — not the comment "a bare `dev` never reaches here" — is the actual guard, and an **untrusted-authored** policy (a malicious issuer's `withdrawal: Some(…)`, an attacker-set `readPolicy`/`pol(said)`) cannot bypass the lifecycle defense the rule exists to provide. See [*Verifier behavior*](verifier-behavior.md#verifier-behavior) (the `dev_legal` mechanism + the two attacks it rejects).

The leaf is satisfied iff the request is backed by the device key material of the KEL identified by `prefix`, **at the key role the operation requires** and at the **KEL state the flow fixes**. `dev(K)` says only "K authorizes" — it is **tier-agnostic**. The operation's `required_tier` selects *which* of K's key roles must be exercised: tier-1 (signing key), tier-2 (rotation material), tier-3 (rotation + recovery material). A policy is authored once, naming who and at what threshold; the event being authorized supplies the key-role context. This is how dual-sig governance works without a separate dual-sig policy: a governance event's tier raises every `dev(K)` leaf's key-role demand (a tier-3 recovery-class event makes each leaf require K's tier-3 material), while the policy stays tier-agnostic. The common case — an ordinary signed request — is tier-1, the signing key.

Like `id` and `grp`, `dev` resolves against the state the flow fixes. In the **current-state flow** the material is read at the **KEL tip** (the most-recent establishment event) — the live read-time key proof. In the **anchored flow** the leaf is the credential's **anchor** on K's KEL: its pinned slot holds the SAID of the KEL event *just prior* to the anchoring event, and the verifier resolves the anchoring child on the **surviving branch** and checks the anchor there (see [*Pinning*](pinning.md#pinning-evidence-pins)). Because `dev` is the **base case of `id` recursion**, a `dev` reached through an `id(X)` descent rides that descent's flow — an anchored `id(X)` fixes it as-of the pinned state, a current `id(X)` at the tip.

`dev` is the only leaf that resolves directly to cryptographic key material — no recursive policy evaluation. It's the base case of authorization at the device layer, and `satisfies_dev` is already tier-parameterized (`s.tier >= required_tier`). The precise **tier → key-role mapping** (which key material each tier demands) settles with the key-role model and is tracked in the deviations log; the framing here — tier-agnostic leaf, operation supplies the key role — is fixed.

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
attestations from a delegated party). It is **always** performed, independent of any `immune` flag —
`immune` is a creds-feature concept that scopes the credential **withdrawal** scan only (a forthcoming
feature), never this rescission walk.

**Depth is policy-level.** The verifier checks the self-traversed chain length `≤ N`. On-chain
delegation is **unbounded** — a delegator delegates freely; any context that needs to bound
re-delegation writes a tighter `del(X, M)` in **its own** policy. There is no on-chain per-edge
budget and no sub-delegator tightening (and so no `Del` event-shape change for depth). Traversal is
additionally bounded by the always-passed `max_depth`; exceeding either `N` or `max_depth` denies
(fail-secure).

**`del(X)` is not `X`.** It authorizes `X`'s *delegates*, not `X` itself — self-issuance needs
`X` to self-delegate, or a separate leaf naming `X`.

**Multi-issuer — count distinct.** `del` lives only inside a composer's `[...]` (set-valued like
`grp`) but is never expanded; composers count **distinct presented issuers** (deduped by prefix).
So `thr(2, [del(A), del(B)])` = "2 distinct issuers, each delegated by A *or* B, any combination";
`thr(1, [del(A)])` is the common single case. Each contributing party independently supplies its
own anchor pinning (the per-party anchor pinnings do not collapse — see the anchored evaluator in [`evaluation.md`](evaluation.md)).

**Weight-based delegation (`wgt`-over-`del`).** `del` is a legal `wgt` subject, so an issuance policy can
weight delegators: `wgt(M, [([del(A, N)], wA), ([del(B, K)], wB), …])` credits an issuer delegated by
`A` within `N` at `wA`, by `B` within `K` at `wB`. An issuer matching several placeholders — e.g. a
deep delegate satisfying both `del(A, ≥1)` and `del(B, ≥2)` on one lineage — is credited **once at its
maximum weight**, distinct issuers summed, `sum ≥ M` (identical dedup-by-max to a member in two `grp`
groups; one issuer cannot stack delegators' weights — fail-secure). The self-traversals are driven by
which `del` placeholders exist, not by weights; weight is aggregation-side metadata applied at the
composer, so weighted delegation adds no extra walk cost.

### `pol(said)` — Policy nesting

The leaf is satisfied iff the nested policy is also satisfied.

### Nesting

Composers can wrap any expression — leaves, or other composers:

```
thr(2, [
    id(P1),
    wgt(50, [([id(P2)], 30), ([id(P3)], 30)])
])
```

The verifier evaluates inside-out: each leaf evaluates against its chain state; composers aggregate results.

### `and([expr, ...])` — conjunction (separation of duties)

`and([expr, ...])` is the **conjunction** composer: satisfied iff **every** child expression is
*independently* satisfied. Where `thr` / `wgt` count distinct parties over a **union**, `and` imposes
a **per-branch** requirement — the tool for **separation of duties** ("≥1 board member **and** ≥1
executive"), which a union threshold cannot express. `thr(2, [grp(board), grp(exec)])` is cleared by
two board members, and even nested `thr(2, [thr(1, [grp(board)]), thr(1, [grp(exec)])])` collapses to
the same union under the recursive-dedup rule (see *Leaf semantics → `grp`*). A conjunction is the
only way to require *each* pool independently. (Worked side-by-side — how a duplicated party lands under
`and` vs `thr` vs `wgt`, and disjoint vs overlapping pools — in *[examples](examples.md#worked-examples)*.)

- **No threshold / weight argument** — it is all-of. Its children are full `expr`s (a leaf or a
  composer), **never** a bare `grp` / `del`: set-valued forms resolve only inside `thr` / `wgt`, so to
  conjunct a pool you wrap it (`and([thr(1, [grp(org, board)]), thr(1, [grp(org, execs)])])`).
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
who sits in both branches **satisfies both alone** — `and([thr(1, [grp(org, board)]), thr(1, [grp(org,
execs)])])` is cleared by a single person who is both a board member and an executive (the credited
union is just `{alice}`). An author must **not** assume `and` enforces "two different people"; it
enforces "each pool is met." Guaranteed-distinct separation of duties over *overlapping* pools needs a
matching / max-flow construct, which is **out of scope** — `and` covers the disjoint-pool case, the
usual SoD setup (different roles staffed by different people). **When distinctness matters, the policy
author is responsible for ensuring the branches' pools are disjoint.**

**Scope.** Allowed wherever any composer is (general, IEL/SEL `governance` / `authentication` /
`delegation` / `operation`, issuance, withdrawal, current-mode), under the same leaf constraints as
`thr` / `wgt` (an aggregate's own policy may use only one-arg `grp(group)`; a singleton only `dev`). Child
order is preserved (author-meaningful for pin slots, like `thr` siblings), and the
[canonical DSL string form](verifier-behavior.md#verifier-behavior) applies.

