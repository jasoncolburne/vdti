Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## IEL policy structure — aggregate vs. singleton

An IEL is one of two kinds, fixed at inception by an optional boolean **`aggregate`** flag on its
`Icp` event — absent or `false` ⇒ **singleton**, `true` ⇒ **aggregate**. The flag is **immutable**:
an identity does not change kind over its life ("it's an identity, not a choose-your-own-adventure").
The kind constrains what the IEL's three policies (`governance`, `authentication`, `delegation`)
may contain. (This is a constraint on an IEL's *own* three policies only; general policies —
application, issuance, withdrawal — keep the full DSL surface, including `id(X)` and foreign
`grp(X, group)`.)

- **Singleton** — bottoms out at device keys; it has **no roster** (the `Icp` simply omits the
  roster field). Its three policies may contain only `dev()` leaves, composed with `thr` / `wgt` —
  no `grp`, `id`, `del`, or `pol`. A singleton is the **base case** that `id(...)` resolution
  terminates at: every chain of member resolution ends at some singleton's `dev()`. Its
  `authentication` must be non-empty (≥ 1 satisfiable `dev`), or the identity can never act.

- **Aggregate** — composed of other identities (its members). It carries a **roster**: a SAD
  mapping group labels to sets of member IEL prefixes (see [`grp`](leaf-semantics.md#grp--membership-roster-array)).
  Its three policies may contain only one-arg `grp(group)` arrays, composed with `thr` / `wgt` — the
  **host** IEL's **own** roster only, never a foreign one. No bare `id` / `dev` / `del`, no `pol`.
  An aggregate must be **born with a non-empty roster**, or it is ungovernable. The one-arg form is
  **cycle-forced, not mere convenience**: the IEL's prefix is the content-address of its
  `(authentication, governance, …)` commitment, so an own-policy that named its own prefix
  (`grp(own_prefix, group)`) would close a content-address cycle — the prefix would depend on a
  policy that names it. The prefix is therefore left implicit and supplied by the enclosing `id(X)`
  descent. (Because the one-arg form carries no prefix, IEL policies stay prefix-free — reducing to
  a smaller complete set, and under content-addressed dedup identical expressions like
  `thr(2, [grp(directors)])` collapse to a single Policy SAD shared across every IEL of that shape,
  saving stored bytes.)

`id(member)` is **never hand-written** in an IEL policy. It exists only as the form
one-arg `grp(group)` **expands into** — one `id(member_i)` per current member of the group — and as
the recursion primitive each member resolves through: `id(member)` defers to that member's
`authentication`, which (if the member is itself an aggregate) is again `grp(group)` → `id(…)`,
terminating at a singleton's `dev()`. So each IEL policy kind has exactly **one** writable leaf —
`dev` for singletons, `grp` for aggregates — and `id` is purely the internal resolution form. The
DSL itself is unchanged: `id` remains a first-class leaf elsewhere (general policies, and the
verifier-constructed `id(subject)` / `id(issuer)` of the identity and anchor flows).

**Naming one specific member** uses a **one-element group**: to single out `alice`, give her a group
(`founder = {alice}`) and reference `grp(founder)`. Every individual reference therefore goes
through a labelled roster entry rather than a bare prefix — a policy can never name a non-member,
and because `grp(group)` yields in-roster members *by construction*, no reference can dangle.
(The residual caution is the generic threshold one: shrinking a group below a threshold that gates
it self-bricks — true of any threshold — not a dangling-reference hazard.)

**Group labels** match `^[a-z_-]{1,16}$` — lowercase `a`–`z`, underscore, hyphen; 1–16 characters;
no digits, no uppercase.

**Cycles.** Aggregate-of-aggregate membership forms a graph that must be **acyclic**. The verifier
carries a visited-set / cycle guard in its `id(...)`-resolution walk so a membership cycle denies
rather than loops; roster-write may additionally forbid self-membership as a first line.

The `aggregate` flag, the roster field, and the roster-less singleton `Icp` shape are **event-shape
facts** (VDTI-10) — provisional here pending [`event-shape.md`](../event-logs/event-shape.md). This
section states only the **DSL-level constraint** the two kinds impose on policy contents.

> SELs have no identity and no roster — only `governance` + `operation` policies — so the
> aggregate/singleton distinction is **IEL-only**.

