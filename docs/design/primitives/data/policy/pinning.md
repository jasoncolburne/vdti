Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

### As-of resolution — grandfather, not freeze

Anchored evaluation resolves **as-of** the state a document pinned, and an authorization stays valid
**permanently** once a then-authorized party anchored it. The only thing that invalidates it is explicit
**withdrawal** (revocation) — never a later roster or policy change (**grandfather**). Resolution is as-of
**the inherited pin, never the owner's tip**; a tip-resolving branch would retroactively invalidate old
authorizations on a roster change, which the design rejects.

Grandfather does **not** reopen ex-member backdating **when the authority-resolution marker is floored** —
and a sound document never resolves against a freely chosen one. Two distinct markers must not be conflated:

- The credential's **anchor** — the issuer added a real event to its own chain, a **self-dating position**
  you cannot insert in the past. This fixes *when* the document was authored; it is genuinely
  non-backdatable.
- The **authority-resolution marker** — *which* roster / authentication state `id(issuer)` resolves
  against. This is a **separate** slot, and a self-dating anchor does **not** constrain it. It is safe only
  when it is **floored**, not issuer-chosen. In the **SEL-gated** path it is: the gating event resolves a
  foreign `grp` against the SEL's **governance-ratcheted, floored `policyPin`**
  (event-shape [`§policyPin`](../event-logs/event-shape.md#policypin)), already ratcheted forward along its
  per-chain floor.

A **freely chosen** authority-resolution marker is **unsafe** and is **not** how issuance works: a document
allowed to pin `id(issuer)` as-of an issuer-supplied, unfloored marker would let a departed member of an
aggregate issuer backdate to an epoch where they were still rostered and forge a credential "issued by" that
aggregate — recursively, one level per nesting tier. Issuance authority therefore resolves against **floored
state on each entity's own registry-SEL, composed by reference** — never a free-floating chosen marker. Every
IEL has a discoverable registry-SEL that floors its **own** marker *shallow* (forward-only, the per-chain
floor below), and an aggregate **references** each member's registry-SEL rather than re-pinning the subtree.
The floor then holds at **every depth** — but **only under one precondition**: every referenced entity must
**already** have a registry-SEL with a seeded floor, including a member that never issues anything (commonly a
singleton device-holder reached only by deep expansion). That precondition is **load-bearing, not cosmetic**:
a member with no provisioned registry-SEL has no floor, its marker falls back to issuer-choice, and the
backdate **re-opens one layer down**. So the composition splits into two forward-pointed obligations, at
**different layers**:

- **Provisioning** — every IEL is given a default registry-SEL **eagerly, at inception, regardless of
  credential activity** — is an **IEL/SEL-primitive (layer-4)** obligation. It is what makes the
  at-every-depth floor real: a member's **own** registry-SEL carries its floor, and a referencing entity's
  resolution is **checked against** that floor — so the member must already be floored **before** any
  reference, which is why provisioning cannot be lazy / on-first-issuance.
- **Issuance** — a floored `Ixn` on the issuer's registry-SEL — is the **credentials feature (layer-5)**.

Grandfather then rides **floored positions** (immutable, each at-or-above its own chain's floor): old
authorizations stay valid until explicitly withdrawn, while no backdated marker can be introduced. This
primitive states only the **rule** (*floored composition by reference against eagerly-provisioned
registry-SELs, never a chosen marker*); the registry-SEL machinery — including the
**fail-closed-on-absent-`R`** rule (a referenced registry-SEL that is absent **denies**; never a tip-fallback)
— is specified at those layers. The forward
floor blocks backdating; **recovery** (an `Rpr` archiving forged anchors — [`evaluation.md`](evaluation.md))
handles the terminal residual — a leaked **current** key. None of this alters a valid authorization's
validity.

### Two pinnings, one walk-ordered cursor

The walk-ordered cursor described below serves **two distinct pinnings** — do not conflate them:

- The **SEL `policyPin`** (standing; event-shape [`§policyPin`](../event-logs/event-shape.md#policypin)) is
  **shallow**: one slot per `id` / `grp` occurrence in the SEL's `governance` / `operation` policy **text**,
  every entry an IEL state-marker, **full — no nulls**, ratcheted forward along the per-chain floor. It fixes
  *which version of each directly-named IEL* an event resolves against — the membership / state layer.
- The **per-event evidence pinning** (this doc's subject) is **deep**: it walks the policy graph down to the
  terminal `dev` anchors, proving *who actually signed*, as-of authoring. Its **policy-text** leaves
  (`id` / `dev` / `pol`→`id`) are **positional** — one slot per occurrence, `null` for an occurrence the
  issuer doesn't evidence. A **`grp` leaf** is **sparse-named**: a single **`GrpBlock`** listing only the
  members who actually signed (by prefix), never one slot per roster member.

Everything below — the policy-text walk's positional slots, the `dev` prior-event slots, the `null`
discipline, and the `grp` leaf's sparse **`GrpBlock`** — is the **deep evidence** pinning. `null` slots live
**only** here (and only on the **policy-text** walk — `id` / `dev`), never in a `policyPin`. The shallow
`policyPin` is the membership/state layer that *supplies a foreign `grp`'s context marker* into this deep
walk.

**Deep does not mean unfloored.** Each IEL state-marker the deep walk reaches — at every level of the
`id`-recursion — must reference a **floored position on that entity's own chain**, never a bare prefix at tip
and never an issuer's free choice. The model is *shallow per chain, deep by composition*: every entity floors
its **own** marker shallow (its registry-SEL, forward-only along the per-chain floor), and the depth is the
**tree of those floored chains, composed by reference** — an aggregate references each member's registry-SEL
rather than re-pinning the subtree. So the as-of grandfather rides **floored positions all the way down** —
**given** the eager, universal registry-SEL provisioning the grandfather block names (the **layer-4**
obligation: every IEL has a registry-SEL at inception, so even a never-issuing member is floored). *Under that
precondition* the only marker the rule leaves unfloored is the terminal **`dev`** anchor (per-event and
self-dating — a leaked *current* device key is the recovery residual, [`evaluation.md`](evaluation.md), not a
backdating surface); absent a provisioned registry-SEL for a composed member, that member's marker is itself
unfloored and the backdate re-opens — which is why provisioning is unconditional. Registry-SEL
**provisioning** is the layer-4 obligation; **issuance** as a floored `Ixn` is the **layer-5** credentials
feature; this doc specifies only the per-event evidence pinning's *shape*, under the rule that every
state-marker it pins is a floored position.

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
by a pinned slot (see [`del`](leaf-semantics.md#delprefix-n--delegation-placeholder-self-traversing) and the
anchored evaluator in [`evaluation.md`](evaluation.md)).

`grp`, the other bracket form, lays a **`GrpBlock`** — a single deep-evidence element **naming the members
who actually signed**, never a slot per roster member. A `GrpBlock` is `{ signers: [SignerEntry] }`; each
**`SignerEntry`** is `{ prefix, marker_said, sub_pins }` — the member identified by **prefix** (not roster
index), its own `Evl`/`Icp` **state-marker** (floored by composition — the member's registry-SEL), and
`sub_pins`, the member's authentication evidence laid recursively (a nested aggregate carries a further
`GrpBlock`; a singleton carries the positional `dev` slots). The roster the signers are checked against is
**context-supplied** — a two-arg `grp(prefix, group)` reads X's marker from the gate (the gating SEL's
**governance-ratcheted, floored** `policyPin`, never the invoker's choice, never X's tip); a one-arg
`grp(group)` reuses the enclosing `id(X)` snapshot's marker (NEW-B). There is **no issuer-laid
roster-source slot** — a self-contained block needs no positional alignment marker. See the slot kinds below.

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

A Pinning SAD carries `pins`: one **`PinSlot`** per leaf the walk reaches, **ordered by the verifier's
pre-order walk**. A **policy-text** leaf (`id` / `dev` / `pol`→`id`) lays an `Option<Said>` (a prefix reached
through two branches gets two such slots — one per occurrence, so each can pin a different chain position); a
**`grp` leaf** lays a single **`GrpBlock`** (the sparse named signers, below). There is **no sort** across the
policy-text walk: the verifier walks the same graph the issuer did and advances a single positional cursor — the
*k*-th leaf the walk reaches reads `pins[k]`. Slot position binds to a prefix occurrence by walk
order alone, without any per-entry **prefix** tag or per-prefix grouping (the `Leaf` / `Grp` shape
discriminant is the one structural tag, checked by `PinKindMismatch`). A `null` slot means that
occurrence is un-evidenced (it contributes nothing toward thresholds), letting an issuer pin only
the branches it satisfies.

**Consumption is driven by the structural walk, not by satisfaction** — on the **policy-text** walk
(`id` / `dev` / `pol`→`id`). Each such leaf consumes exactly one slot when the walk reaches it, whether or
not it ends up satisfied — so a failed leaf cannot desync the slots of later leaves. An `id` leaf whose
pinned state-marker is *present but unsatisfied* still descends into its authentication and drains that
subtree's slots; a `null` `id` slot consumes its one slot and does **not** descend (the state-marker is
un-evidenced, so its authentication subtree is unreachable — its subtree's slots are *omitted*, see
*Issuer-side construction* below). A **`grp` leaf consumes one slot — its `GrpBlock`** — regardless of how
many members signed; there is **no per-member `null`** (a member absent from the block is simply
un-evidenced, contributing nothing). The block's `sub_pins` are drained by a **sub-cursor** when the walk
recurses into each signer's authentication, so a malformed block's blast radius is **contained to the
block** — its own leftover-pins denial fires per-block and cannot desync the rest of the policy walk. After
the walk, **any leftover pins are a malformed pinning and deny** (more slots than the policy has
occurrences) — the same rule, applied to the outer walk and within each block.

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
- A **`grp` leaf lays one `GrpBlock`** — **name the members who signed**, each a
  `SignerEntry { prefix, marker_said, sub_pins }`, with the signers **sorted by prefix, dedup'd within the
  block, and capped at `MAX_PRESENTED`** (non-canonical / duplicate / over-cap ⇒ **deny** — load-bearing for
  content-addressing *and* walk-cost). Each signer's `sub_pins` are laid by the same pre-order walk over that
  member's authentication (a nested aggregate ⇒ a further `GrpBlock`; a singleton ⇒ its positional `dev`
  slots). No roster enumeration, no per-non-signer `null`: an unmentioned member is un-evidenced. The roster
  the signers must belong to is read from context (the gate's floored marker, or the enclosing `id(X)`
  snapshot), never laid by the issuer.

These rules are exact complements of the verifier's branch above. On the policy-text walk, an issuer that
lays subtree slots under a null `id` overruns the policy's occurrences and trips the leftover-pins denial;
one that omits a present slot's subtree under-runs and desyncs every later leaf. A `GrpBlock` is
**self-delimiting** — its canonical-form and per-block leftover checks contain any malformation to the block.
Both fail closed.

What each non-null entry holds depends on the prefix's kind, which the verifier reads from
its position in the policy:

- **dev prefix** → the SAID of the KEL event *just prior* to the anchoring event. The
  anchoring event carries the anchored authorization (a credential is the canonical example), so its
  own SAID is unconstructable here (see the
  SAID-cycle note under *Verifier behavior*); the verifier resolves the anchoring child
  `S` (`S.previous == pin`) **on the surviving branch** and checks the anchor on `S`.
  An anchor on a divergent or later-archived branch is invalid (see [`dev`](leaf-semantics.md#devprefix--kel-key-match-tier-agnostic)).
- **id prefix** → the SAID of the IEL's most-recent `Evl`/`Icp` **state-marker** (the last event
  that changed its authentication or roster; `Del`/`Rsc` don't move it). This fixes the IEL's
  **state snapshot** — both authentication *and* roster — as-of that marker (NEW-B): the verifier
  reconstructs the snapshot as-of the pinned marker, satisfaction recurses into the snapshot's
  authentication policy, whose leaves consume the following slots in walk order, and a one-arg
  `grp(group)` under that authentication reads its roster from this **same** reconstructed snapshot
  (reuse of the marker, no second pin — closing the authentication-recent / roster-stale
  resurrection gap). A state-marker doesn't carry an anchored authorization, so there's no cycle and no
  prior-event trick.
- **`grp` leaf** → a **`GrpBlock`** (not a marker slot). Its signers are named by `(prefix, marker_said)`;
  the verifier checks each `marker_said` is an event **on `prefix`'s chain** (a prefix/marker mismatch denies
  — the same coupling check the `policyPin` floor uses), reconstructs that member's snapshot as-of the
  (floored) marker, recurses into the member's authentication draining the signer's `sub_pins`, and confirms
  the member is **in the group's roster** as-of the **context-supplied** X-marker. In an anchored SEL-gated
  policy that X-marker is the gating SEL's **governance-ratcheted, floored** `policyPin`
  (event-shape [`§policyPin`](../event-logs/event-shape.md#policypin)), **not** a credential's issuer-chosen
  issuance pin; a one-arg `grp(group)` reuses the enclosing `id(X)` snapshot's marker (NEW-B). Sourcing the
  X-marker from context — never letting an issuer pick it — is what forecloses the ex-member backdate on the
  `grp` arm: there is no issuer-supplied roster-source marker to choose
  (see [`grp`](leaf-semantics.md#grp--membership-roster-array)). As-of resolution is the point: a document's
  membership splice is valid relative to the X-state the gate fixes — a later roster change on X is
  forward-only and never reaches back (loss-of-trust comes from the rescission/withdrawal walks, which run to
  tip in both modes). Each signer's own `marker_said` stays **floored by composition** (the member's
  registry-SEL); membership and marker are both checked as-of floored positions, so grandfather rides floored
  positions exactly as for an `id` leaf. Like an `id` marker, a state-marker carries no credential anchor, so
  there's no cycle and no prior-event trick.

There is **no del slot**: `del(prefix, N)` is never expanded and carries no pin — delegation is
proven by the verifier self-traversing the authorizing party's own delegation chain (bounded by `N`),
not by a pinned slot. When an authorizing party is reached via delegation, the party is *named* (not
pinned) and its anchor rides in a separate anchor pinning over its authentication (see the anchored
evaluator in [`evaluation.md`](evaluation.md)).

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

