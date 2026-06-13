# Operating the foreign-`grp` freshness floor

Operator guidance for the policy DSL's floored foreign membership splice
`grp(said, group)` (the design lives in
[`leaf-semantics.md` §`grp`](../design/primitives/data/policy/leaf-semantics.md#grp--membership-roster-array)).
The protocol gives you an **end-verifiable freshness floor**; this doc is the tooling pattern that
turns it into the freshness you actually want.

## What the floor is

A general policy (issuance, application, withdrawal, `readPolicy`) that splices foreign entity X's
roster writes `grp(said, group)`, where `said` is a specific **IEL event of X** — the **floor**. When
a credential is issued against such a policy, the issuer pins an **X-state-marker**; the verifier
requires `marker ≥ said` on X's chain and then resolves X's `group` roster **at the marker**. So:

- members X **adds after** `said` can still issue (the floor is a lower bound, not a freeze at `said`);
- a member X **removed** can only backdate **down to the floor**, never below it.

The floor is enforced by a bounded walk between two static chain positions — **no tip-read** — so it
stays end-verifiable.

## Why you, the operator, have to choose the floor

`grp(said, group)` resolved at an issuer-chosen marker means **"anyone who was in `group` at any state
≥ `said`,"** not "current members." A resource that wants *current* members and leaves the floor at X's
inception event is exposed to the **ex-member**: someone X removed still holds their own KEL and can
keep issuing valid credentials by pinning an old (but ≥ floor) marker where they were still rostered.
No loss-of-trust walk catches a roster removal (it is not an `Rsc`, not a withdrawal anchor) — this is
the same accepted residual class the doctrine documents for SEL `Est`'s `id(P)`
([`protocol-doctrine.md` §SEL `Est`](../design/protocol-doctrine.md)). The floor is the lever that
bounds it; **where you set it is an operational decision.**

## The two endpoints

| Intent | Set `said` to | Result |
|---|---|---|
| "anyone *ever* in the group" | X's **inception event** (`grp(genesis_said, group)`) | accepts a marker anywhere in X's history — the explicit, auditable form of the old unbounded splice |
| "effectively current members" | X's **current tip**, re-templated on cadence | the freshness window equals the re-template interval |

There is no separate unbounded form — the grammar has only `grp(said, group)` — so "ever" is always
written explicitly as `grp(genesis_said, group)`, never hidden in a bare prefix.

## The fetch-current-`said` template (recommended for "current members")

To approximate "current members," run a **template** that re-configures the issuance policy on a
cadence:

1. Fetch X's **current tip `said`** (its latest `Evl`/`Icp` state-marker).
2. Re-config the issuance policy to `grp(current_said, group)` (a new Policy SAD; point the resource at
   it).
3. Re-run on your chosen cadence — **on every X rotation** ≈ "current members"; daily/weekly ≈ a looser
   window.

The **re-template cadence sets the freshness window.** The protocol provides the end-verifiable floor;
the template provides the ergonomics. A stale floor is *your* risk, not a verification hole — the
protocol stays end-verifiable regardless of how fresh the floor is.

## The cost: floor-advance is a retroactive kill

The floor lives in the issuance-policy **text**, read at the resource's **current** configuration
(gate-current). So advancing the floor governs **all** outstanding credentials at once:

- **It is your revocation lever.** Raise the floor → every credential pinned **below** the new floor
  now fails `marker ≥ said` and **denies immediately**. This is the resource-side "expire stale-roster
  credentials" control a bare-prefix splice never had.
- **It also kills legitimate sub-floor credentials.** A credential's validity is bounded by floor
  advance — a long-lived credential must be issued **above** the floor you intend to keep, or an
  auto-advance template will expire it along with the stale ones.

Pick the cadence accordingly: tighter floors mean fresher rosters **and** shorter credential lifetimes.
For credentials that must outlive floor churn, either pin them above a slow-moving floor or use a
distinct, slower-advancing issuance policy.

## Fail-closed edges

The floored form derives X's prefix from `said`, so the verifier rejects (hard error, credential
denies) a pinned marker that:

- orders **before** the floor `said`,
- is **not on X's chain** (wrong-chain / substituted marker), or
- references a `said` that resolves to **no chain** at all.

Only a *null* marker (the issuer declining that leg) is a clean credit-nobody — a present-but-invalid
marker is treated as adversarial.
