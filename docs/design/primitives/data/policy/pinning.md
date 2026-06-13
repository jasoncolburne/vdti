Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

### Shape

Take the policy `thr(2, [pol(A_said), id(X_prefix), id(W_prefix)])`, where the nested policy
`A_said` is `id(B_prefix)`, IELs `X_prefix` and `W_prefix` each authenticate via the same device
(both authentications are `dev(Y_prefix)`), and `B_prefix`'s authentication is `dev(A_prefix)`.
Every `dev` sits at the bottom of an `id`→singleton descent — never bare in the general policy
(the [`dev`-placement rule](leaf-semantics.md#devprefix--kel-key-match-tier-agnostic)). The verifier *expands the whole
graph as it walks it* — descending through `pol()` and through each `id`'s authentication —
visiting one **pinning slot** per prefix occurrence in **pre-order (depth-first) walk order**:
`[B_prefix, A_prefix, X_prefix, Y_prefix, W_prefix, Y_prefix]`. `Y_prefix` appears twice — once
reached through `X`'s authentication, once through `W`'s — and each occurrence gets its own slot,
so each can pin a different KEL position. The issuer pins one SAID per occurrence, in that same
walk order; satisfying 2 of the 3 top-level branches is enough to clear the threshold.

`del(prefix, N)` is the one bracket form that contributes **no** slot — it is never expanded and
carries no pin. Its issuers prove delegation by self-traversing their own delegation chains, not
by a pinned slot (see [`del`](leaf-semantics.md#delprefix-n--delegation-placeholder-self-traversing) and *Policies and
Pinnings*).

`grp`, the other bracket form, does lay slots: its flatten lays one `id(mi)` occurrence per
member, and a foreign **two-arg `grp(said, group)` additionally lays its own X-state-marker slot
first** (G1) — in pre-order where the `grp` occurs, before its members' slots. A foreign splice
has no enclosing `id(X)` descent to ride, so it pins its own roster source; the pinned marker must
sit **at-or-after the policy's floor `said`** (the freshness floor — see the slot kinds below). A
one-arg `grp(group)` lays no slot of its own — it rides the enclosing `id(X)` marker (NEW-B). See
the slot kinds below.

#### Policies (resource holder's gate)

A (the nested `pol(A_said)` policy)

```json
{
    "said": "A_said",
    "policy": "id(B_prefix)"
}
```

IEL(B).authentication

```json
{
    "said": "...",
    "policy": "dev(A_prefix)"
}
```

IEL(X).authentication

```json
{
    "said": "...",
    "policy": "dev(Y_prefix)"
}
```

IEL(W).authentication

```json
{
    "said": "...",
    "policy": "dev(Y_prefix)"
}
```

Policy

```json
{
    "said": "...",
    "policy": "thr(2, [pol(A_said), id(X_prefix), id(W_prefix)])"
}
```

#### Pinning (evidence pins)

Walking `thr(2, [pol(A_said), id(X_prefix), id(W_prefix)])` in pre-order — descend through
`pol()` and through each `id` authentication, taking one slot per prefix occurrence **as the
walk reaches it**:

```
  thr(2)
  ├─ pol(A_said) ──▶ id(B_prefix)           ▷ slot 0  B_prefix   (pol → id state-marker)
  │    └─ authentication ──▶ dev(A_prefix)   ▷ slot 1  A_prefix   (via B's authentication)
  ├─ id(X_prefix)                           ▷ slot 2  X_prefix   (the id leaf itself)
  │    └─ authentication ──▶ dev(Y_prefix)   ▷ slot 3  Y_prefix   (via X's authentication)
  └─ id(W_prefix)                           ▷ slot 4  W_prefix   (the id leaf itself)
       └─ authentication ──▶ dev(Y_prefix)   ▷ slot 5  Y_prefix   (via W's authentication)

  slots follow the walk — pre-order, depth-first, no sort:

    slot 0  B_prefix   id(B) state-marker (pol → id)
    slot 1  A_prefix   dev, via B's authentication
    slot 2  X_prefix   id(X) state-marker
    slot 3  Y_prefix   dev, via X's authentication
    slot 4  W_prefix   id(W) state-marker
    slot 5  Y_prefix   dev, via W's authentication
```

Each `id` contributes two slots — its own (the state-marker) and the prefix from its authentication
descent, in that descent order — so `id(X)` lays `[X_prefix, Y_prefix]` and `id(W)` lays
`[W_prefix, Y_prefix]`. `Y_prefix` lands twice, the via-`X` occurrence ordered before the via-`W`
one because the walk reaches it first; each occupies its own slot, so the two can pin different
positions on `Y`'s KEL.

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
desync the slots of later leaves. An `id` leaf whose pinned state-marker is *present but
unsatisfied* still descends into its authentication and drains that subtree's slots; a `null`
`id` slot consumes its one slot and does **not** descend (the state-marker is un-evidenced, so its
authentication subtree is unreachable — its subtree's slots are *omitted*, see *Issuer-side
construction* below). A foreign two-arg `grp`'s X-state-marker slot follows the same discipline: a
**present** marker fixes the roster the flatten expands, and the member `id(mi)` slots follow
(draining structurally whether or not each member satisfies); a **null** marker consumes its one
slot and the expansion is omitted entirely — with no marker the roster is unresolvable, so the
member subtree's slot count is unknowable, the same fail-closed rule as a null `id`. A **present
but below-floor** marker (ordering before the policy's `said`, or not on X's chain) is the one
case that **hard-denies** rather than credit-nobody — it is an adversarial backdate, not a declined
leg (see the floored slot kind below). After the
walk, **any leftover pins are a malformed pinning and deny** (the issuer pinned more slots than
the policy has occurrences).

**Issuer-side construction (the mirror of the verifier's descent).** The issuer lays the pin array
by the same pre-order walk the verifier consumes it with, branching on null/present identically, so
the two stay aligned by construction:

- A **present `id` slot is followed by its authentication-subtree's slots**, in pre-order — the
  verifier descends into that subtree, so the issuer must supply its slots.
- A **null `id` slot is terminal** — emit exactly one `null` and **omit that `id`'s
  authentication-subtree slots entirely**, because the verifier does not descend a null `id` and
  so consumes no slots for the subtree. (A null `id` cannot drain a subtree: with no state-marker
  its authentication policy is unresolvable, so the subtree's slot count is unknowable; the only
  sound rule is to lay no slots for it.)
- A foreign two-arg **`grp`'s X-state-marker slot follows the same two rules**: present ⇒ followed
  by the member `id(mi)` slots of the roster read as-of that marker, in canonical member order
  (each member then subject to the `id` rules above); null ⇒ terminal — one `null`, the member
  slots omitted (no marker ⇒ no roster ⇒ unknowable member count). The marker the issuer pins must
  be **at-or-after the policy's floor `said`**; an issuer that pins a sub-floor (or off-chain)
  marker is rejected by the verifier (a hard deny, not a null-style declined leg). Because both
  parties expand the member set from the **same pinned marker**, the expansion — and so the slot
  layout — is identical by construction; a tip-read roster could change between authoring and
  verification and desync every later slot.

These rules are exact complements of the verifier's branch above. An issuer that lays
subtree slots under a null `id` (or member slots under a null `grp` marker) overruns the policy's
occurrences and trips the leftover-pins denial; one that omits a present slot's subtree under-runs
and desyncs every later leaf. Both fail closed.

What each non-null entry holds depends on the prefix's kind, which the verifier reads from
its position in the policy:

- **dev prefix** → the SAID of the KEL event *just prior* to the anchoring event. The
  anchoring event carries the credential, so its own SAID is unconstructable here (see the
  SAID-cycle note under *Verifier behavior*); the verifier resolves the anchoring child
  `S` (`S.previous == pin`) **on the surviving branch** and checks the credential anchor on `S`.
  An anchor on a divergent or later-archived branch is invalid (see [`dev`](leaf-semantics.md#devprefix--kel-key-match-tier-agnostic)).
- **id prefix** → the SAID of the IEL's most-recent `Evl`/`Icp` **state-marker** (the last event
  that changed its authentication or roster; `Del`/`Rsc` don't move it). This fixes the IEL's
  **state snapshot** — both authentication *and* roster — as-of that marker (NEW-B): the verifier
  reconstructs the snapshot as-of the pinned marker, satisfaction recurses into the snapshot's
  authentication policy, whose leaves consume the following slots in walk order, and a one-arg
  `grp(group)` under that authentication reads its roster from this **same** reconstructed snapshot
  (reuse of the marker, no second pin — closing the authentication-recent / roster-stale
  resurrection gap). A state-marker doesn't carry the credential anchor, so there's no cycle and no
  prior-event trick.
- **foreign-`grp` X-state-marker** (G1) → for a two-arg `grp(said, group)`, the SAID of **X**'s
  most-recent `Evl`/`Icp` state-marker — the same marker kind an `id` slot pins, laid by the `grp`
  itself in pre-order where it occurs, before its member slots (a foreign splice has no enclosing
  `id(X)` descent to ride, so it pins its own roster source; contrast the one-arg form's reuse,
  NEW-B). X's prefix is **derived from the policy's `said`** (an event resolves its chain), so the
  marker carries no prefix of its own. The marker is subject to the **floor**: the verifier walks
  X's IEL from `said` to the pinned marker and **rejects a marker that orders before `said`** (or is
  not on X's chain, or a `said` resolving to no chain) — a **hard deny**, fail-closed, since the
  marker is then an adversarial backdate, not a declined leg. The floor walk runs between two
  **static** chain positions, so it adds **no tip-read** and stays end-verifiable. Having cleared
  the floor, the verifier reconstructs X's snapshot as-of the marker and reads the **roster** from
  it; the flatten expands that roster's members in canonical order, whose `id(mi)` slots follow.
  As-of resolution is the point: a document's membership splice is valid relative to the X-state it
  pins — a later roster change on X is forward-only and never reaches back (loss-of-trust comes
  from the rescission/withdrawal walks, which run to tip in both modes); the floor is what stops an
  ex-member from backdating *below* it (see [`grp` freshness floor](leaf-semantics.md#grp--membership-roster-array)).
  Like an `id` marker, a state-marker carries no credential anchor, so there's no cycle and no
  prior-event trick. In the credential's issuance-policy pinning the marker is the only slot —
  members lay none; their proofs ride in the per-issuer anchor pinnings (see *Policies and Pinnings*).

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

For the policy above, the occurrences walk to `[B_prefix, A_prefix, X_prefix, Y_prefix, W_prefix,
Y_prefix]`. An issuer satisfying all three branches pins every slot — dev prefixes (`A`, `Y`) →
prior-event SAIDs, id prefixes (`B`, `X`, `W`) → their state-marker SAIDs; a `null` would appear
for any prefix left un-evidenced:

```json
{
    "said": "{pinning_said}",
    "pins": [
        "{B_iel_marker_said}",
        "{A_prior_kel_event_said}",
        "{X_iel_marker_said}",
        "{Y_prior_kel_event_said_1}",
        "{W_iel_marker_said}",
        "{Y_prior_kel_event_said_2}"
    ]
}
```

