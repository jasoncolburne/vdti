Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

### Shape

Take the policy `thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])`, where the nested
policy `A_said` is `kel(A_prefix)` and IEL `X_prefix`'s authentication is `kel(Y_prefix)`. The
verifier *expands the whole graph as it walks it* — descending through `pol()` and through each
`iel`'s authentication — visiting one **pinning slot** per prefix occurrence in **pre-order
(depth-first) walk order**: `[A_prefix, X_prefix, Y_prefix, Y_prefix]`. `Y_prefix` appears twice
— once reached through `X`'s authentication, once as the top-level `kel(Y_prefix)` branch — and
each occurrence gets its own slot. The issuer pins one SAID per occurrence, in that same walk
order; satisfying 2 of the 3 top-level branches is enough to clear the threshold.

`del(prefix, N)` is the one bracket form that contributes **no** slot — it is never expanded and
carries no pin. Its issuers prove delegation by self-traversing their own delegation chains, not
by a pinned slot (see [`del`](leaf-semantics.md#delprefix-n--delegation-placeholder-self-traversing) and *Policies and
Pinnings*).

#### Policies (resource holder's gate)

A

```json
{
    "said": "A_said",
    "policy": "kel(A_prefix)"
}
```

IEL(X).authentication

```json
{
    "said": "...",
    "policy": "kel(Y_prefix)"
}
```

Policy

```json
{
    "said": "...",
    "policy": "thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])"
}
```

#### Pinning (evidence pins)

Walking `thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])` in pre-order — descend through
`pol()` and through each `iel` authentication, taking one slot per prefix occurrence **as the
walk reaches it**:

```
  thr(2)
  ├─ pol(A_said) ──▶ kel(A_prefix)         ▷ slot 0  A_prefix   (pol → kel)
  ├─ iel(X_prefix)                         ▷ slot 1  X_prefix   (the iel leaf itself)
  │    └─ authentication ──▶ kel(Y_prefix) ▷ slot 2  Y_prefix   (via X's authentication)
  └─ kel(Y_prefix)                         ▷ slot 3  Y_prefix   (top-level branch)

  slots follow the walk — pre-order, depth-first, no sort:

    slot 0     slot 1       slot 2                  slot 3
    A_prefix   X_prefix     Y_prefix                Y_prefix
    pol→kel    state-marker via X's authentication  top-level kel
```

`iel(X)` contributes two slots — its own (the state-marker) and `Y_prefix` from its authentication,
in that descent order — and `Y_prefix` lands twice, the via-authentication occurrence ordered
before the top-level one because the walk reaches it first.

A Pinning SAD carries `pins`: one `Option<Said>` per *prefix occurrence* in the expanded policy
graph, **ordered by the verifier's pre-order walk** (a prefix reached through two branches gets
two slots — one per occurrence, so each can pin a different chain position). There is **no sort**:
the verifier walks the same graph the issuer did and advances a single positional cursor — the
*k*-th leaf the walk reaches reads `pins[k]`. Slot position binds to a prefix occurrence by walk
order alone, without any per-entry type tag or per-prefix grouping. A `null` slot means that
occurrence is un-evidenced (it contributes nothing toward thresholds), letting an issuer pin only
the branches it satisfies.

**Consumption is driven by the structural walk, not by satisfaction.** Each leaf consumes exactly
one slot when the walk reaches it, whether or not it ends up satisfied — so a failed leaf cannot
desync the slots of later leaves. An `iel` leaf whose pinned state-marker is *present but
unsatisfied* still descends into its authentication and drains that subtree's slots; a `null`
`iel` slot consumes its one slot and does **not** descend (the state-marker is un-evidenced, so its
authentication subtree is unreachable — its subtree's slots are *omitted*, see *Issuer-side
construction* below). After the walk, **any leftover pins are a malformed pinning and deny** (the
issuer pinned more slots than the policy has occurrences).

**Issuer-side construction (the mirror of the verifier's descent).** The issuer lays the pin array
by the same pre-order walk the verifier consumes it with, branching on null/present identically, so
the two stay aligned by construction:

- A **present `iel` slot is followed by its authentication-subtree's slots**, in pre-order — the
  verifier descends into that subtree, so the issuer must supply its slots.
- A **null `iel` slot is terminal** — emit exactly one `null` and **omit that `iel`'s
  authentication-subtree slots entirely**, because the verifier does not descend a null `iel` and
  so consumes no slots for the subtree. (A null `iel` cannot drain a subtree: with no state-marker
  its authentication policy is unresolvable, so the subtree's slot count is unknowable; the only
  sound rule is to lay no slots for it.)

These two rules are exact complements of the verifier's branch above. An issuer that lays
subtree slots under a null `iel` overruns the policy's occurrences and trips the leftover-pins
denial; one that omits a present `iel`'s subtree slots under-runs and desyncs every later leaf.
Both fail closed.

What each non-null entry holds depends on the prefix's kind, which the verifier reads from
its position in the policy:

- **kel prefix** → the SAID of the KEL event *just prior* to the anchoring event. The
  anchoring event carries the credential, so its own SAID is unconstructable here (see the
  SAID-cycle note under *Verifier behavior*); the verifier resolves the anchoring child
  `S` (`S.previous == pin`) **on the surviving branch** and checks the credential anchor on `S`.
  An anchor on a divergent or later-archived branch is invalid (see [`kel`](leaf-semantics.md#kelprefix--kel-key-match-tier-agnostic)).
- **iel prefix** → the SAID of the IEL's most-recent `Evl`/`Icp` **state-marker** (the last event
  that changed its authentication or roster; `Del`/`Rsc` don't move it). This fixes the IEL's
  **state snapshot** — both authentication *and* roster — as-of that marker (NEW-B): the verifier
  reconstructs the snapshot as-of the pinned marker, satisfaction recurses into the snapshot's
  authentication policy, whose leaves consume the following slots in walk order, and a one-arg
  `mem(group)` under that authentication reads its roster from this **same** reconstructed snapshot
  (reuse of the marker, no second pin — closing the authentication-recent / roster-stale
  resurrection gap). A state-marker doesn't carry the credential anchor, so there's no cycle and no
  prior-event trick.

There is **no del slot**: `del(prefix, N)` is never expanded and carries no pin — delegation is
proven by the verifier self-traversing the issuer's own delegation chain (bounded by `N`), not by
a pinned slot. When a credential is issued by a delegate, the issuer is *named* (not pinned) and
its anchor rides in a separate anchor pinning over its authentication (see *Policies and Pinnings*).

Pinning eliminates the verifier's search-for-evidence step — slot position (walk order) names the
prefix occurrence, the pinned SAID names the chain position — while the verifier still walks each
chain to verify integrity (per the trust-boundary principle). Listing a prefix twice doesn't
force two full walks: the verifier collects every pinned SAID that falls on a given log and
checks them inline in that log's single paged verification walk — the SAIDs to check are the
positions supplied before the walk, the walk validates each event as it pages through, and the
caller confirms every required SAID was reached.

For the policy above, the occurrences walk to `[A_prefix, X_prefix, Y_prefix, Y_prefix]`. An
issuer satisfying all three branches pins every slot — kel prefixes → prior-event SAIDs, the
iel prefix → its state-marker SAID; a `null` would appear for any prefix left un-evidenced:

```json
{
    "said": "{pinning_said}",
    "pins": [
        "{A_prior_kel_event_said}",
        "{X_iel_marker_said}",
        "{Y_prior_kel_event_said_1}",
        "{Y_prior_kel_event_said_2}"
    ]
}
```

