# Policy DSL

Canonical specification of vdti's policy DSL — the expression language used to encode authorization rules across the event-log primitives.

A **policy** is a [SAD](sad/sad.md) whose content is a DSL expression. The IEL primitive references policies (governance, delegation, and authentication); the SEL primitive references policies (governance); applications reference policies for their own authorization needs. The DSL is the language; Policy SADs are the storage format; the verifier evaluates DSL expressions against signed requests and the relevant chain state.

This doc states the surface (the primitives that make up the DSL), their semantics, and how composition works. It does not enumerate per-primitive doctrine (which lives in [`event-logs/event-shape.md`](event-logs/event-shape.md), the per-primitive specs, and [`../../protocol-doctrine.md`](../../protocol-doctrine.md)) and does not specify the verifier implementation algorithm (which lives in `lib/vdti` planning material).

## Where policies appear

Policies are referenced by Policy SAD SAIDs from chain-event fields:

- **IEL `governance`** (required at inception; evolved via `Evl`) — gates IEL self-mutation events (key rotation, policy/roster changes, decommission).
- **IEL `authentication`** (required at inception; evolved via `Evl`) — the entity's act-as policy: what every `iel(prefix)` leaf (and each `mem` member) evaluates against. Outward-facing — it never gates the IEL's own chain events.
- **IEL `delegation`** (optional at inception; evolved via `Evl`) — gates IEL delegation events (`Del` / `Rsc`).
- **SEL `governance`** (declared at SEL `Icp`; evolved via SEL `Evl`) — gates SEL events (`Est` / `Ixn` / `Evl` / `Rpr` / `Dec`).
- **Application-defined policy references** — applications may attach policy SAIDs to their own data structures (credentials, signed requests, custody SADs) following the same pattern.

In each case the field holds a `Digest256` pointing at a Policy SAD. The verifier dereferences, parses the DSL expression, and evaluates it.

## The DSL surface — 7 primitives

```
kel(prefix)        iel(prefix)        del(prefix)        mem(prefix, class)
pol(said)
thr(M, [...])      wgt(M, [...])
```

Three chain-state **leaves** (`kel`, `iel`, `del`), one policy-reference **leaf** (`pol`), one
**membership array** (`mem`), two **composers** (`thr`, `wgt`). `mem(prefix, class)` is not a
leaf: it is an **array value** — it names the *`class`* class of IEL `prefix`'s membership roster
and resolves to one `iel(member_i)` leaf per member of that class. It is only legal **inside a
composer's `[...]`**, where it flattens in place. The `[...]` is a concat container, so
member-arrays and single expressions mix freely (`[mem(org, staff), kel(K)]` = org's staff
members followed by `kel(K)`). Members are IELs (individuals are IELs; devices are KELs), so each
flattened member authenticates via their own authentication policy (`iel(mi)`), while the referencing policy
composes over them at the threshold/weights it chooses (see *Leaf semantics*). The grammar:

```
expr     ::= leaf | composer
leaf     ::= kel(prefix) | iel(prefix) | del(prefix) | pol(said)
array    ::= mem(prefix, class)                 # IEL prefix's `class` roster: an array of iel(member) leaves
composer ::= thr(M, [elem, ...]) | wgt(M, [(elem, w), ...])
elem     ::= expr | array                       # an array element flattens its members in place
```

`mem` appears only as an `elem` (inside `[...]`), never as a standalone `expr`. In a `wgt` pair
`(array, w)`, the weight grafts onto each flattened member. Every well-formed policy is built from
these primitives.

### Shape

Take the policy `thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])`, where the nested
policy `A_said` is `kel(A_prefix)` and IEL `X_prefix`'s authentication is `kel(Y_prefix)`. The
verifier *expands the whole graph* — descending through `pol()` and through each `iel`'s
authentication (and each `del`'s delegating IEL) — to the *multiset* of prefixes it references:
`{A_prefix, X_prefix, Y_prefix, Y_prefix}`. `Y_prefix` appears twice — once as the top-level
`kel(Y_prefix)` branch, once reached through `X`'s authentication — and each occurrence gets its
own slot. The issuer pins one
SAID per prefix occurrence; satisfying 2 of the 3 top-level branches is enough to clear the
threshold.

#### Policy (resource holder's gate)

```json
{
    "said": "...",
    "policy": "thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])"
}
```

#### Pinning (evidence pins)

Expanding `thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])` — descend through `pol()` and
through each `iel` authentication, taking one slot per prefix occurrence:

```
  thr(2)
  ├─ pol(A_said) ──▶ kel(A_prefix)        ▷ A_prefix   (pol → kel)
  ├─ iel(X_prefix)                         ▷ X_prefix   (the iel leaf itself)
  │    └─ authentication ──▶ kel(Y_prefix) ▷ Y_prefix   (via X's authentication)
  └─ kel(Y_prefix)                         ▷ Y_prefix   (top-level branch)

  sort the occurrences into the pin multiset:

    slot 0     slot 1     slot 2                  slot 3
    A_prefix   X_prefix   Y_prefix                Y_prefix
    pol→kel    iel event  via X's authentication  top-level kel
```

`iel(X)` contributes two slots — its own (the IEL event) and `Y_prefix` from its authentication —
and `Y_prefix` lands twice, the via-authentication occurrence ordered before the top-level one.

A Pinning SAD carries `pins`: one `Option<Digest256>` per *prefix occurrence* in the expanded
policy graph, with the prefixes held as a **sorted multiset** (a prefix reached through two
branches gets two slots — one per occurrence, so each can pin a different chain position).
The verifier reconstructs the same sorted multiset from the policy and zips it against `pins`,
so slot position binds to a prefix occurrence without any per-entry type tag. Equal-prefix
slots are ordered by the graph traversal that reaches them, so the k-th time the walk reaches
a prefix it reads that prefix's k-th slot. A `null` slot means that occurrence is
un-evidenced (it contributes nothing toward thresholds), letting an issuer pin only the
branches it satisfies.

What each non-null entry holds depends on the prefix's kind, which the verifier reads from
its position in the policy:

- **kel prefix** → the SAID of the KEL event *just prior* to the anchoring event. The
  anchoring event carries the credential, so its own SAID is unconstructable here (see the
  SAID-cycle note under *Verifier behavior*); the verifier resolves it as the unique child
  `S` where `S.previous == pin` and checks the credential anchor on `S`.
- **iel prefix** → the SAID of the IEL event itself. This fixes the IEL's authentication at that
  state; satisfaction recurses into that authentication policy, whose leaves carry their own pins.
  An IEL event doesn't carry the credential anchor, so there's no cycle and no prior-event trick.
- **del prefix** → the SAID of the *delegating* IEL's own event, fixing which delegation state
  the membership is tested against. The verifier walks that IEL's chain and confirms the
  delegate identifier (supplied by verifier context — in the credential flow, the issuer) is
  currently in its delegated set. The delegate's own authentication is *not* reached here: the
  delegate isn't named by the policy, so it's evidence-shaped and can't occupy a fixed, sortable
  slot. When a
  credential needs to prove both delegation and where it's anchored, the anchor rides in a
  separate anchor pinning over the issuer's authentication (see *Policies and Pinnings*).

Pinning eliminates the verifier's search-for-evidence step — slot position names the prefix
occurrence, the pinned SAID names the chain position — while the verifier still walks each
chain to verify integrity (per the trust-boundary principle). Listing a prefix twice doesn't
force two full walks: the verifier collects every pinned SAID that falls on a given log and
checks them inline in that log's single paged verification walk — the SAIDs to check are the
positions supplied before the walk, the walk validates each event as it pages through, and the
caller confirms every required SAID was reached.

For the policy above, the prefixes sort to `[A_prefix, X_prefix, Y_prefix, Y_prefix]`. An
issuer satisfying all three branches pins every slot — kel prefixes → prior-event SAIDs, the
iel prefix → its IEL event SAID; a `null` would appear for any prefix left un-evidenced:

```json
{
    "said": "{pinning_said}",
    "pins": [
        "{A_prior_kel_event_said}",
        "{X_iel_event_said}",
        "{Y_prior_kel_event_said_1}",
        "{Y_prior_kel_event_said_2}"
    ]
}
```

#### Rust

These are suitable Rust shapes. `Policy` carries a recursive `PolicyExpr` so the DSL grammar (nesting, `pol(said)`) maps directly onto the data structure.

```rust
pub enum PolicyExpr {
    Iel(Digest256),                       // chain prefix
    Kel(Digest256),                       // chain prefix
    Del(Digest256),                       // delegator IEL prefix
    Mem(Digest256, String),               // (IEL prefix, class label); an array of iel(member) leaves — only valid as a composer element (inside [...]), flattens in place
    Pol(Digest256),                       // nested Policy SAD SAID
    Thr(u64, Vec<PolicyExpr>),            // threshold M, sub-expressions
    Wgt(u64, Vec<(PolicyExpr, u32)>),     // threshold M, (sub, weight) pairs
}

pub struct Policy {
    said: Digest256,
    expr: PolicyExpr,
    withdrawn: Option<String>,            // optional withdrawal-authorization expression (DSL); None = issuance authority may withdraw
    immune: bool,                         // when true, the credential can never be withdrawn
}

pub struct Pinning {
    said: Digest256,
    pins: Vec<Option<Digest256>>,
}
```

## API Surface

The public evaluation entry points are `evaluate_anchored_policy` (pinned, reads chains via the verification walk) and `evaluate_current_policy` (live signatures). The anchored entry is fed by a pure `bind_pins` phase and composes a single-policy helper, `evaluate_single_policy`. The leaf checks ride inline on the verifier's verification walk (`source`) — the single paged pass each referenced log gets for end-verifiability; there is no separate evidence-gathering walk.

```rust
// Bind phase — PURE, no I/O, no log traversal. Binds every (policy, pinning)
// pair's slots to their pinned SAIDs: it expands each policy graph to its sorted
// prefix multiset and zips with `pinning.pins`, producing one cursor per policy.
// The `anchor` binding is the anchoring hop: `bind_pins` records `expected_anchors`
// as the required-anchor set on the ANCHOR CURSOR — every kel leaf reached under the
// issuer's authentication is an anchoring leaf (one chain each, several under a
// multi-KEL threshold). Every other binding's cursor carries an empty required set,
// so an issuance-policy kel leaf that names a chain the issuer's authentication also
// reaches never inherits the requirement. `satisfies_kel` reads the required set off
// the cursor it evaluates under and the hosted anchors off the event the verification
// walk validates — the requirement is scoped to the issuer's binding, never a property
// of the shared chain. Bounded by policy size; returns the per-policy `Cursors`.
pub fn bind_pins(
    delegations: &[(&Policy, &Pinning)],
    anchor: (&Policy, &Pinning),
    expected_anchors: &HashSet<(Digest256, Tier)>,
) -> Result<Cursors, PolicyError>;

// Anchored check (public entry) — delegation + anchoring for a credential whose issuer
// may sit at the end of a delegation chain. Self-contained: it builds the hop policies,
// binds the pins (pure), folds the per-hop evaluations — whose leaves read their pinned
// events inline from the verification walk (`source`) — and returns the verdict. The
// caller just supplies the credential's pinnings, not pre-bound `Cursors` or a bindings
// list. `delegation_path` is the ordered list of delegation hops
// `(prefix, membership_pinning)`: hop 0 is delegated by `issuance_policy` (its pinning is
// the issuance pinning), each later hop by `del(prior_prefix)` (the linkage check), and the
// last hop's prefix is the issuer. `anchor_pinning` anchors the credential through the
// issuer's `iel`. `expected_anchors` is the set of (SAID, minimum-tier) pairs the anchoring
// event must host (e.g. the credential SAID, plus any co-anchored SADs, each with the tier
// its hosting event must meet); it is handed to `bind_pins` as the anchor hop's requirement —
// `bind_pins` records it on the anchor cursor and `satisfies_kel` reads it from there, so it
// is scoped to the issuer and never threaded through the per-hop checks.
// Single-hop case: `delegation_path == [(issuer, issuance_pinning)]`.
pub fn evaluate_anchored_policy(
    issuance_policy: &Policy,
    delegation_path: &[(Digest256, &Pinning)],
    anchor_pinning: &Pinning,
    expected_anchors: &HashSet<(Digest256, Tier)>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError>;

// Single-policy helper (internal) — tree walk over the bound `Cursors` for ONE policy.
// `evaluate_anchored_policy` calls this once per hop; not a public entry. Each leaf takes
// its slot's pinned SAID and reads that event inline from the verification walk (`source`);
// composers aggregate. The Pinning was consumed in the bind phase, not here. The anchor
// requirement is not threaded in: it rides on the cursor (`bind_pins` set it on the anchor
// cursor) and `satisfies_kel` reads it from there. `delegate` is the identifier under test
// for `del` membership (the prefix the hop must confirm is delegated); pass `None` when the
// policy has no `del` leaves (e.g. the terminal `iel` anchor hop).
fn evaluate_single_policy(
    policy: &Policy,
    cursors: &Cursors,
    source: &impl EventSource,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError>;
```

```rust
// Current-state check — challenge-response / fresh-control verification. Establishes who
// CURRENTLY controls `policy` and confirms they signed the `challenge`. The policy tree may
// carry `iel`/`del` leaves, so a delegated controller's delegation still has to check out — it
// reuses `evaluate_single_policy` at the chain TIP (no pinning: tip membership is implied; empty
// anchors: nothing is being proven anchored here — that's the anchored check's job) to fix the
// current authorized signer set, then verifies the live attestations. The bearer presents one
// or more attestations over `challenge` (a digest); each is the signer's KEL prefix + a primary
// signature, plus optionally a recovery signature for tier-3 dual-sig contexts. The verifier
// checks each attestation against the signer's CURRENT signing key (and recovery key, when
// present) at the KEL's tip, and aggregates per the policy's structure.
pub struct Attestation {
    signer: Digest256,                       // signer's KEL prefix
    signature: Signature,                    // signature by current signing key
    recovery_signature: Option<Signature>,   // signature by current recovery key (tier-3)
}

pub fn evaluate_current_policy(
    policy: &Policy,
    challenge: &Digest256,
    attestations: &[Attestation],
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError>;
```

`evaluate_anchored_policy` returns `Ok(true)` iff the issuer is reached through the full delegation path AND the expected anchors are each hosted on the issuer's authentication at its required tier or above AND no satisfying withdrawal anchor was found (see *Withdrawal*). `evaluate_current_policy` returns `Ok(true)` iff the provided signatures over `challenge` cover the policy's leaves at current chain state with the required tier. Both return `Ok(false)` for clean unsatisfied; `Err(_)` for malformed inputs / fetch failures.

The auth flow typically calls both kinds of check. `evaluate_anchored_policy` is self-contained: internally it builds the hop policies, calls `bind_pins` once (pure — binds every pinning's slots across *all* of the credential's pinnings), then folds the per-hop evaluations over the shared `Cursors`, their leaves reading pinned events inline from the verification walk (`source`): one **delegation** hop per step (the **issuance pinning** confirms the first delegate; each subsequent hop's `del` pinning confirms the next), then one terminal **anchoring** hop over the issuer's `iel` (the **anchor pinning**) proving the cred is anchored on the issuer's authentication (see *Policies and Pinnings*). The verification walk pages each referenced log once, so a chain referenced by several pinnings is checked inline in that one pass. The **current-state** check (`evaluate_current_policy`) validates that the bearer presently controls the policy the cred names — it reuses the same delegation machinery over current chain state and then verifies the challenge signed under current state.

### Policies and Pinnings

#### Use case

Let's say we declare an **issuance policy** that governs which credentials a resource will
accept — it names the IELs whose delegates may issue credentials bound to user identities. A
credential SAID must be anchored in a way that satisfies the issuance policy for the credential
to be valid.

The credential issuance policy the server is configured with may be:

```
thr(1, del(iel_prefix_1), del(iel_prefix_2), del(iel_prefix_3))
```

which says that prefixes 1 through 3 may delegate to other prefixes, and only a single signature
from any delegate of prefixes 1 through 3 is required to satisfy the policy.

When a credential is issued, the issuer burns **two pinnings** into it. The issuance policy
names the *delegating* IELs but not their delegates, so the issuer — itself a delegate,
discovered from evidence — can't be pre-positioned in the issuance policy's slot layout. Rather
than let the slot count depend on what's evidenced, the evidence splits into two pinnings, each
sized against a policy whose shape is known up front:

- an **issuance pinning** over the server's issuance policy — proves *delegation* (the issuer is
  a current delegate of one of the delegating IELs);
- an **anchor pinning** over the issuer's own **IEL**, `iel(dlg_prefix)` — proves the *anchor*
  while binding identity to authentication: the issuer's IEL names its authentication KEL, and the
  credential is anchored on that KEL at the required tier (issuing a credential is the issuer
  acting *as* itself, so the anchor rides the authentication KEL). Routing through the IEL (rather
  than naming the authentication KEL directly) is what ties the anchoring KEL to the *delegated*
  identity — otherwise the issuer's authentication would be an unbound, credential-supplied claim.

Both ride on the credential. Say the credential is issued by `dlg_prefix`, a delegate of
`iel_prefix_2`, whose IEL authentication is `kel(dlg_kel_prefix)`.

Two graphs, two pinnings. The issuance policy expands to one slot per `del` and STOPS — `del`
never descends into the delegate. Proving where the credential is anchored is a separate graph
rooted at the issuer's own IEL, `iel(dlg_prefix)`, which expands through the issuer's authentication
to the anchoring KEL event:

```
  issuance policy                           issuance pinning
  ───────────────────────────────────      ───────────────
  thr(1)
  ├─ del(iel_prefix_1)  ▷ iel_prefix_1     null               — un-evidenced
  ├─ del(iel_prefix_2)  ▷ iel_prefix_2     {iel2_event_said}
  │     └─ is dlg_prefix in its delegated set?  (delegate, from verifier context)
  └─ del(iel_prefix_3)  ▷ iel_prefix_3     null               — un-evidenced

  dlg_prefix (the issuer) is NOT a slot here — it's evidence-shaped, found in
  iel_prefix_2's delegated set. Its anchor rides in a separate pinning, rooted at the
  issuer's own IEL so the anchoring KEL is bound to the delegated identity:

  iel(dlg_prefix)  (identity → authentication → anchor)  anchor pinning
  ─────────────────────────────────────────────────     ────────────────
  iel(dlg_prefix)                       ▷ dlg_prefix     {dlg_iel_event_said}
  └─ authentication kel(dlg_kel_prefix) ▷ dlg_kel_prefix {dlg_kel_prior_kel_said}
        └─ prior event; its child anchors the credential at the required tier
```

**Issuance pinning.** The issuance policy `thr(1, del(iel_prefix_1), del(iel_prefix_2),
del(iel_prefix_3))` expands to one slot per `del` — the *delegating* IEL's own event, fixing which
delegation state the issuer claims membership against. (The delegate's authentication is not
expanded here; it's evidence-shaped, so it lives in the anchor pinning.) The issuer evidences
only the `iel_prefix_2` branch:

```
{
    "said": "{issuance_pinning_said}",
    "pins": [
        null,                   // iel_prefix_1 — un-evidenced
        "{iel2_event_said}",    // iel_prefix_2 — the IEL event whose delegated set holds dlg_prefix
        null                    // iel_prefix_3 — un-evidenced
    ]
}
```

**Anchor pinning.** The issuer's IEL policy `iel(dlg_prefix)` expands to two slots — the
issuer's IEL event (fixing which authentication state applies) and, through that authentication
`kel(dlg_kel_prefix)`, the KEL event just *prior* to the anchoring event (the anchoring event
commits to the credential, so its own SAID is unconstructable here; see the SAID-cycle note):

```
{
    "said": "{anchor_pinning_said}",
    "pins": [
        "{dlg_iel_event_said}",      // dlg_prefix — IEL event fixing the authentication state
        "{dlg_kel_prior_kel_said}"   // dlg_kel_prefix — prior event; its child anchors the credential
    ]
}
```

(slots labelled by branch for readability; on the wire they follow sorted prefix order.)

**Verifying.** The credential is valid iff *both* hold:

- **Delegation** — evaluating the issuance policy against the issuance pinning, the
  `del(iel_prefix_2)` leaf reads its pinned IEL event, walks `iel_prefix_2`'s chain, and
  confirms `dlg_prefix` (the issuer, supplied by verifier context) is currently in that IEL's
  delegated set. A single satisfied delegate branch clears the `thr(1, ...)`.
- **Anchor** — evaluating `iel(dlg_prefix)` against the anchor pinning, the `iel(dlg_prefix)`
  leaf reads its pinned IEL event (binding the issuer to its authentication `kel(dlg_kel_prefix)`)
  and recurses into that authentication policy; the `kel(dlg_kel_prefix)` leaf resolves the anchoring event
  `S` (`S.previous == dlg_kel_prior_kel_said`) and checks `S` is at the required tier and anchors
  the credential SAID. Because the anchor is reached *through* the delegated issuer's IEL, the
  anchoring KEL is bound to the delegated identity rather than asserted by the credential.

The two pinnings exist only to make each policy's slot count self-determining. Verification
groups the pinned SAIDs from both pinnings by the log they fall on and checks each log's set
inline in that log's single paged verification walk: the SAIDs to check are the positions
supplied up front, the walk validates each event as it pages through, and the caller confirms
every required SAID was reached. So a chain reached on both paths is paged once, not twice.

```rust
let iel_prefix_1 = Digest256::from_qb64("KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")?;
let iel_prefix_2 = Digest256::from_qb64("KBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")?;
let iel_prefix_3 = Digest256::from_qb64("KCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")?;

let issuance_policy = parse_policy(&format!(
    "thr(1, del({}), del({}), del({}))",
    iel_prefix_1, iel_prefix_2, iel_prefix_3
))?;

let dlg_prefix = cred.issuer_prefix; // the issuer: a delegate of iel_prefix_2, AND the anchor host

// Both pinnings ride on the credential.
let issuance_pinning  = parse_pinning_sad(&sadd_fetch(&cred.issuance_pinning_said)?)?;
let anchor_pinning = parse_pinning_sad(&sadd_fetch(&cred.anchor_pinning_said)?)?;

// each required anchor names the minimum tier its hosting event must satisfy
let cred_anchor: HashSet<(Digest256, Tier)> = [(credential_said, Tier::One)].into_iter().collect();

// One self-contained call: it builds the issuer's `iel` policy internally, binds the pins
// once (pure), folds the per-hop delegation checks — their leaves reading pinned events
// inline from the verification walk — and confirms the credential anchor off the anchoring
// event the walk validates. The caller supplies only the credential's pinnings and the anchor
// set — no manual bind, no pre-built `iel(dlg_prefix)`. Single-hop here: dlg_prefix is delegated directly by
// the issuance policy and is itself the issuer. For a delegate-of-a-delegate, extend
// `delegation_path` with that hop's `(prefix, del_pinning)`.
let satisfied = evaluate_anchored_policy(
    &issuance_policy,
    &[(dlg_prefix, &issuance_pinning)], // delegation_path = [(issuer, issuance_pinning)]
    &anchor_pinning,
    &cred_anchor,
    source,
    Tier::One,
)?;
```

> **TODO (pending [event-shape.md](event-logs/event-shape.md)).** The evaluation architecture below — two-pinning model, the bind/evaluate split (`bind_pins` is pure and produces `Cursors`; `evaluate_*` read pinned events inline from the verifier's verification walk), the multi-hop delegation-path fold (delegation hops + one terminal anchor hop, anchor checked only on the terminal), sorted-multiset slotting / `PinCursor`, `delegate` threading, `del` as membership-only, and the supply-SAIDs-up-front / one-paged-walk-per-log / inline-check mechanism — is stable. What may still shift is the per-primitive **leaf field access** that depends on the settled event shapes: the kel anchor model and prior-event/SAID-cycle rederivation (`s.anchors`, `s.previous`), the iel `governance` / `authentication` field names (`iel(X)` recurses into `authentication`; `governance` gates the IEL's own events), the `del` delegated-set construction (`Del`/`Rsc` walk, `delegated_set_contains`), the membership **roster** field on the IEL that `mem(prefix, class)` resolves against (a roster-SAD SAID the IEL commits to — not yet in `event-shape.md`) and the composer-time flattening that expands `mem` elements into `iel(member)` leaves, and where `tier` lives on the event. Treat those specifics as provisional until `event-shape.md` lands.

Implementation:

```rust
// bind_pins is PURE — no source arg, no log traversal. For each (policy, pinning):
// expand the policy graph — descending through pol() and through each iel authentication —
// to its multiset of referenced prefix occurrences, sort into wire slot order (by prefix,
// equal prefixes kept in traversal order), then zip with `pinning.pins` to bind each
// occurrence to its pinned SAID. A `del` leaf contributes exactly one occurrence — its
// delegating IEL prefix — and does NOT descend into the delegate's authentication: the
// delegate is evidence-shaped (not named by the policy), so its subtree can't be sized
// here; it rides in a separate anchor pinning. Produce one cursor per policy (the
// `delegations` plus the single `anchor`). The expansion mirrors the eval walk below, so
// issuer and verifier agree on slot order. The `anchor` binding is the anchoring hop:
// `bind_pins` attaches `expected_anchors` to the ANCHOR CURSOR as its required-anchor set —
// every kel leaf reached under the issuer's authentication is an anchoring leaf (one chain
// each, several under a multi-KEL threshold); every other binding's cursor gets an empty
// required set. The requirement travels with the cursor, scoped to the issuer's binding, so
// an issuance-policy kel leaf naming a chain the issuer's authentication also reaches never
// inherits it. The hosted anchors are read later off the event the verification walk
// validates; `satisfies_kel` reads the required set off the cursor and the anchors off that
// event, so the requirement is never a property of the shared chain. Bounded by policy size.
pub fn bind_pins(
    delegations: &[(&Policy, &Pinning)],
    anchor: (&Policy, &Pinning),
    expected_anchors: &HashSet<(Digest256, Tier)>,
) -> Result<Cursors, PolicyError> {
    // for each pair (delegations + anchor): expand graph -> sorted prefix multiset ->
    // zip with pinning.pins -> per-policy cursor; attach expected_anchors to the anchor cursor
}

// evaluate_anchored_policy is self-contained: it builds the hop policies, binds the pins
// ONCE (pure), then folds the delegation chain into one conjunction of single-policy
// evaluations — whose leaves read pinned events inline from the verification walk (`source`) —
// and returns the verdict. `delegation_path` is the ordered list of delegation hops
// `(prefix, membership_pinning)`: hop 0 is delegated by issuance_policy (its pinning is the
// issuance pinning), each later hop by `del(prior_prefix)`, and the last hop's prefix is the
// issuer; `anchor_pinning` anchors through the issuer's `iel`. Each hop is a term: delegation
// hops test the next delegate; the terminal hop tests no delegate. The anchor is checked ONLY
// on the terminal hop, but not here — `bind_pins` records `expected_anchors` on the anchor
// cursor and `satisfies_kel` confirms it. The linkage invariant — hop k's policy names the
// prefix the prior hop established — is enforced here by CONSTRUCTING `del(prior_prefix)` from
// the path, not by trusting a policy lifted off the cred.
pub fn evaluate_anchored_policy(
    issuance_policy: &Policy,
    delegation_path: &[(Digest256, &Pinning)],
    anchor_pinning: &Pinning,
    expected_anchors: &HashSet<(Digest256, Tier)>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let (issuer, _) = match delegation_path.last() {
        Some(hop) => hop,
        None => return Ok(false),    // no path, nothing to check
    };

    // Build hop policies (linkage: hop k names the prefix the prior hop established) and the
    // terminal anchor policy, then bind every (policy, pinning) in ONE pure pass. The anchor
    // binding is passed distinctly so `bind_pins` knows which cursor carries the credential's
    // anchor requirement.
    let issuer_iel = parse_policy(&format!("iel({})", issuer))?;
    let hop_policies: Vec<Policy> = (1..delegation_path.len())
        .map(|k| parse_policy(&format!("del({})", delegation_path[k - 1].0)))
        .collect::<Result<_, _>>()?;

    let mut delegations: Vec<(&Policy, &Pinning)> = vec![(issuance_policy, delegation_path[0].1)];
    for (k, hop_policy) in hop_policies.iter().enumerate() {
        delegations.push((hop_policy, delegation_path[k + 1].1)); // membership pinning for hop k+1
    }

    let cursors = bind_pins(&delegations, (&issuer_iel, anchor_pinning),
                            expected_anchors)?;

    // Fold over the bound cursors; leaves read pinned events inline from `source`. Hop 0 —
    // issuance policy delegates the first prefix.
    if !evaluate_single_policy(issuance_policy, &cursors, source,
                               Some(&delegation_path[0].0), required_tier)? {
        return Ok(false);
    }

    // Hops 1..n — each delegator (the prefix the prior hop established) must delegate the next.
    for (k, hop_policy) in hop_policies.iter().enumerate() {
        if !evaluate_single_policy(hop_policy, &cursors, source,
                                   Some(&delegation_path[k + 1].0), required_tier)? {
            return Ok(false);
        }
    }

    // Terminal — the issuer's authentication anchors the credential. `satisfies_kel` reads the
    // anchor requirement off the anchor cursor; no anchor arg threaded in here.
    evaluate_single_policy(&issuer_iel, &cursors, source, None, required_tier)
}

fn evaluate_single_policy(
    policy: &Policy,
    cursors: &Cursors,
    source: &impl EventSource,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    // Tree walk over the bound cursors. `cursors` carries this policy's leaf->SAID cursor
    // (fixed during bind); each leaf reads its slot's SAID and reads that event inline from
    // the verification walk (`source`). No traversal is triggered here.
    let mut pins = cursors.cursor_for(&policy.said)?;
    eval_expr(&policy.expr, &mut pins, source, delegate, required_tier)
}

// `pins` is a cursor: per prefix, the pins for that prefix's occurrences in traversal
// order. Each leaf takes the NEXT pin for its prefix and reads that event inline from
// `source` (the verification walk); composers aggregate sub-results. The walk is exhaustive
// (composers evaluate every branch — no short-circuit) so the k-th leaf reaching a
// prefix consumes that prefix's k-th slot, matching the order bind_pins laid them down. No
// traversal is triggered here beyond the verifier's one paged verification walk per log,
// against which these checks run inline.
fn eval_expr(
    expr: &PolicyExpr,
    pins: &mut PinCursor,
    source: &impl EventSource,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    match expr {
        PolicyExpr::Kel(prefix) => match pins.take(prefix) {
            Some(prior_said) => {
                let required = pins.required_anchors(); // this binding's set: expected_anchors on the anchor cursor, {} elsewhere
                satisfies_kel(&prior_said, prefix, required, source, required_tier)
            }
            None => Ok(false),
        },
        PolicyExpr::Iel(prefix) => match pins.take(prefix) {
            Some(iel_event_said) => {
                satisfies_iel(&iel_event_said, prefix, pins, source, delegate, required_tier)
            }
            None => Ok(false),
        },
        PolicyExpr::Del(delegating_prefix) => match pins.take(delegating_prefix) {
            Some(iel_event_said) => satisfies_del(&iel_event_said, delegating_prefix, source, delegate),
            None => Ok(false),
        },
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, pins, source, delegate, required_tier)
        }
        PolicyExpr::Thr(m, subs) => {
            let mut count: u64 = 0;
            for sub in subs {
                if eval_expr(sub, pins, source, delegate, required_tier)? {
                    count += 1;
                }
            }
            Ok(count >= *m)
        }
        PolicyExpr::Wgt(m, weighted) => {
            let mut sum: u64 = 0;
            for (sub, w) in weighted {
                if eval_expr(sub, pins, source, delegate, required_tier)? {
                    sum += *w as u64;
                }
            }
            Ok(sum >= *m)
        }
    }
}

// kel(prefix): the credential is anchored on this KEL itself. `prior_said` names
// the event JUST BEFORE the anchoring event — the anchoring event commits to the
// credential, so its own SAID is unconstructable here (see the SAID-cycle note).
// `S` is its unique child (`S.previous == prior_said`) — the next event the verification
// walk reaches after the pinned `prior_said` — validated inline by that walk (trust-
// boundary principle); its facts (prefix, tier, anchors) are read from that event. The
// anchor requirement (`required`) is supplied by the caller off the binding's cursor —
// `expected_anchors` under the issuer's authentication, empty otherwise — so an issuance-
// policy kel leaf naming the same chain never inherits it. Check anchor + tier.
fn satisfies_kel(
    prior_said: &Digest256,
    leaf_prefix: &Digest256,
    required: &HashSet<(Digest256, Tier)>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let s = source.anchoring_child(leaf_prefix, prior_said)?; // S where S.previous == prior_said, validated by the walk
    // required_tier is the baseline floor for the hosting event; each required anchor may
    // additionally demand a higher tier (a high-assurance SAD co-anchored with a routine one).
    Ok(
        s.prefix == *leaf_prefix
            && s.tier >= required_tier
            && required.iter().all(|(anchor, tier)| s.anchors.contains(anchor) && s.tier >= *tier)
    )
}

// iel(prefix): `iel_event_said` is the IEL event itself — NOT an anchoring event,
// so it carries no credential anchor and needs no prior-event trick. It fixes the
// IEL's authentication at that state; satisfaction recurses into that authentication
// policy, whose leaves carry their own pins (the credential anchor is checked at the
// terminal kel leaves the recursion reaches). The IEL event is read inline from the
// verification walk, which validates it.
fn satisfies_iel(
    iel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    pins: &mut PinCursor,
    source: &impl EventSource,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let iel = source.iel_event(leaf_prefix, iel_event_said)?;
    if iel.prefix != *leaf_prefix {
        return Ok(false);
    }
    let authentication = parse_policy_sad(&sadd_fetch(&iel.authentication)?)?;
    eval_expr(&authentication.expr, pins, source, delegate, required_tier)
}

// del(prefix): `iel_event_said` is the DELEGATING IEL's own event (its prefix == leaf_prefix),
// fixing which delegation state membership is tested against. Confirm the delegate (the
// issuer, from verifier context) is in that IEL's delegated set as of the pinned event. No
// anchor check and no authentication recursion: the delegate's authentication and the credential
// anchor are proven separately, by the anchor pinning. The delegating IEL's event is read
// inline from the verification walk, which validates it.
fn satisfies_del(
    iel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    source: &impl EventSource,
    delegate: Option<&Digest256>,
) -> Result<bool, PolicyError> {
    let delegate = match delegate {
        Some(c) => c,
        None => return Ok(false), // no identifier to test membership against
    };
    let iel = source.iel_event(leaf_prefix, iel_event_said)?; // delegating IEL's event, validated by the walk
    Ok(iel.prefix == *leaf_prefix && iel.delegated_set_contains(delegate))
}
```

## Withdrawal

A credential can be **withdrawn** — invalidated after issuance — without mutating the credential
itself (it is immutable and content-addressed). Withdrawal works by anchoring a derived digest,
exactly the way the credential's own SAID was anchored:

```
withdrawal_digest = qb64( Blake3-256( "withdrawn:" ‖ said(credential) ) )
```

To withdraw credential `C`, an authorized party anchors `withdrawal_digest(C)` on a KEL. The
verifier — having already walked the issuer's KEL during the anchored check — scans that same
verified walk for the digest. Because the digest is itself anchored and tamper-evident,
withdrawal inherits the same end-verifiability as issuance: no revocation list, no online check.
What counts as *authorized to withdraw* — and whether the scan happens at all — is set by two
fields on the credential's `Policy`:

- **`immune: true`** — the credential can never be withdrawn; the verifier does not scan for a
  withdrawal digest. For credentials whose validity must not depend on a later anchor (e.g. a
  one-shot attestation).
- **`withdrawn: Some(expr)`** — withdrawal is gated by its own policy expression. `C` is
  withdrawn iff `withdrawal_digest(C)` is anchored *and* that anchor satisfies `expr` (evaluated
  like any other policy, against its own pinning). This lets a named authority that is **not** the
  issuer hold the withdrawal right.
- **`withdrawn: None`, `immune: false`** (default) — `C` is withdrawn iff `withdrawal_digest(C)`
  is anchored under the same issuance authority that may issue it (the issuer, or a recognized
  delegate on the issuance policy).

When the verifier finds a satisfying withdrawal anchor, `evaluate_anchored_policy` returns
`Ok(false)`: the credential is structurally well-formed and validly issued, but withdrawn.

> **TODO (pending [event-shape.md](event-logs/event-shape.md) and the credential shape).** The
> withdrawal-digest label (`"withdrawn:"`), the anchor-scan step (reading the issuer-KEL walk's
> token for the digest), and the `withdrawn` / `immune` field placement on `Policy` are
> provisional. The three modes (immune / gated / default-issuer) are grounded in the kels poison
> model; the exact default-authority semantics (issuer-only vs. any issuance-path delegate) want
> a confirmation pass against that model.

## Leaf semantics

Each leaf evaluates against chain state and a signed request (or delegate identifier, for `del`). Leaves return satisfied / unsatisfied.

### `iel(prefix)` — IEL authentication

The leaf is satisfied iff the signing party satisfies the IEL's own **authentication** policy at the IEL's current chain tip. `iel(X)` *defers to X's authentication*: it treats X as an autonomous entity and accepts X's own rule for who acts as X. You don't reach inside X's factors, and you inherit X's threshold — if X's authentication is 2-of-3, `iel(X)` demands 2-of-3. (Authentication is the entity's outward-facing act-as policy — distinct from its **governance**, which gates X's own self-mutation and is never what an external `iel(X)` evaluates.)

This is recursive — `iel(P)`'s check evaluates P's authentication policy, which may itself contain `iel(...)`. The recursion terminates at non-`iel` leaves (`kel`, `del`).

`iel(X)` and `mem(X, class)` both reach entity X, but differently. `iel(X)` **defers** to X's autonomy — it accepts X's own authentication, at X's own threshold, for who acts as X (X authorizes as an institution). `mem(X, class)`, by contrast, takes X's **published roster** for the named class and lets the *referencing* policy compose over those members at a threshold/weights **it** chooses — see [`mem(prefix, class)`](#memprefix-class--membership-roster-array). Both are first-class for foreign X; the difference is *who sets the bar* (X's authentication vs. the referencing policy).

### `mem(prefix, class)` — membership-roster array

`mem(prefix, class)` names the **`class`** class of the membership roster published by **IEL `prefix`**, and resolves to one `iel(member_i)` leaf per member of that class. The roster is a SAD that IEL commits to — its SAID burned into the IEL, distinct from `governance` / `authentication` / `delegation` — mapping class labels to sets of member IEL prefixes (a member may sit in several classes). The reference is **explicit** (both the IEL prefix and the class): a roster is referenced by *multiple* policies — the owning entity's own policies and any number of foreign policies — so the policy must name which IEL's roster and which class. Foreign reach is first-class: any policy may splice IEL X's `executives` class via `mem(X, executives)`. This is distinct from `iel(X)`, which defers to X's whole authentication; `mem(X, class)` takes X's published class and composes over it at the referencing policy's own bar.

`mem(prefix, class)` is an **array value**, not a standalone leaf — only legal inside a composer's `[...]`, where it flattens in place and concatenates with its siblings:

- inside `thr(k, [mem(prefix, class)])` → `thr(k, [iel(m1), …, iel(mn)])` — *k of that class's members*, with **k chosen by the referencing policy**, not by any member's own threshold. Each member still authenticates via their own authentication policy (`iel(mi)`).
- inside `wgt(M, [(mem(prefix, class), w), …])` → each member becomes `(iel(mi), w)` — every member of the class carries weight `w`.
- the enclosing `[...]` is a **concat container**: multiple `mem` classes and single expressions mix freely — `thr(2, [mem(org, execs), mem(org, board), kel(K)])` flattens to one child list (`execs` members ++ `board` members ++ `kel(K)`).

This is the membership/composition split. Two levels compose: the **roster level** (which class, how many, or what weight — chosen by the referencing policy) and the **member level** (how each individual proves they act — their own `iel` authentication). The roster lives with the entity (who is in each class); the thresholds/weights live with the policy (how much each member counts here). Adding a member edits the roster, never the policy; changing the bar edits the policy, never the roster.

**Rosters carry classes, not weights.** A roster maps class → member set; weight is the *referencing policy's* per-class assignment on the `wgt` branch. So weight only exists post-flatten — which is also when overlap resolves: if a member sits in two spliced classes (e.g. `mem(org, admins)` at weight 2 and `mem(org, members)` at weight 1), the flattened leaves are **deduplicated by member prefix, keeping the maximum weight** — that member counts once, at its highest class. (In a `thr` splice there are no weights, so dedup simply collapses duplicate members — standard threshold.)

The roster's point-in-time resolution mirrors `del`. The DSL leaf names a **prefix**, not a SAID; the pinning supplies the point-in-time IEL event the roster is resolved against — taken as of the pinned IEL event in the anchored flow, at the IEL tip in the current-state flow. (The pin already fixes the IEL state, and the roster rides that state, so the policy need not bake a roster SAID in.)

### `kel(prefix)` — KEL signing-key match

The leaf is satisfied iff the signed request was authored by the **current signing key** of the KEL identified by `prefix`. "Current" means the signing key in effect at the KEL's tip (the most-recent establishment event's `publicKey`).

`kel` is the only leaf that resolves directly to a cryptographic key — no recursive policy evaluation. It's the base case of authorization at the device layer.

### `del(prefix)` — IEL delegated-set membership

The leaf is satisfied iff the delegate identifier is in the delegated set of the IEL identified by `prefix`. The delegate is provided by the verifier context (in the credential flow, the issuer). The delegated set is computed by walking the IEL's chain and tracking `Del` / `Rsc` events. In the anchored flow the pinned slot names the IEL's own event, so the set is taken as of that event; absent a pin it's taken at the chain tip.

The delegated set's content is **point-in-time** — `del` evaluates against the delegated state at the pinned event (or the tip, absent a pin). Earlier delegations rescinded via `Rsc` are not in the set; this is the [loss-of-trust semantic](event-logs/iel/) (Rsc retroactively invalidates downstream attestations from delegated parties).

### `pol(said)` — Policy nesting

The leaf is satisfied iff the nested policy is also satisfied.

### Nesting

Composers can wrap any expression — leaves, or other composers:

```
thr(2, [
    iel(P1),
    wgt(50, [(kel(K1), 30), (kel(K2), 30)])
])
```

The verifier evaluates inside-out: each leaf evaluates against its chain state; composers aggregate results.

## Worked examples

**Single-key authorization** — prove a device attested to something:
```
kel(prefix)
```

**IEL authentication** — prove a link to a basic identity:
```
iel(prefix)
```

**Membership threshold** — k-of-a-class authentication, with k chosen by this policy (not by the org or its members):
```
thr(2, [mem(prefix, staff)])
```

With org `prefix`'s `staff` class = `{m1, m2, m3}` (resolved from that IEL's roster), expands to `thr(2, [iel(m1), iel(m2), iel(m3)])` — any two staff. Adding a fourth member edits the roster; this policy is unchanged. Concatenate classes by listing them: `thr(2, [mem(prefix, staff), mem(prefix, board)])` pools both into one flat child list.

**Emergency override**:
```
thr(1, [
    thr(3, [mem(prefix, members)]),
    kel(emergency)
])
```

Any three members satisfy, or the emergency key alone.

**Weighted membership classes** — an org weights executive / admin / member classes at 3 / 2 / 1, threshold 3 (the classes live in the org's one roster; weight is this policy's per-class valuation):
```
wgt(3, [
    (mem(prefix, executives), 3),
    (mem(prefix, admins),     2),
    (mem(prefix, members),    1)
])
```

With `prefix`'s roster `executives = {E1, E2}`, `admins = {A1, A2, A3}`, `members = {M1, …}`, this flattens to `wgt(3, [(iel(E1), 3), (iel(E2), 3), (iel(A1), 2), (iel(A2), 2), (iel(A3), 2), (iel(M1), 1), …])`. Satisfied by: one executive (3), two admins (4), three members (3), or one admin + one member (3); one admin alone (2) does not clear. The weights are this policy's valuation of each class — a stricter resource could set `member → 0`; the roster is unchanged. A member in two classes is deduplicated to its highest weight (see *Leaf semantics → `mem`*).

## Composition semantics

- **Leaves evaluate independently.** One leaf's satisfaction never depends on another's. The shared pin cursor and the per-log single paged verification walk are plumbing (slot assignment, walk reuse), not satisfaction coupling.
- **Composers are pure aggregators.** They take leaf / sub-composer results and produce satisfaction signals. No side effects.
- **Boundedness.** Bounded cost. `bind_pins` is pure and bounded by policy size (it expands the expression trees and zips pins — no log access). The leaf checks ride inline on the verifier's verification walk, the single paged pass each referenced log gets for end-verifiability anyway: a log referenced by several leaves is paged once, and a million-event log is paged through once in O(chain length), parallelizable across logs (resident cost bounded by the page — the chain is never materialized whole). Evaluation itself is a cheap tree walk.
- **Deterministic.** Given a fixed chain state and signed request, evaluation is deterministic. Verifiers across nodes converge.

## Verifier behavior

The verifier first **binds pins**: `bind_pins` expands each policy graph to its sorted prefix *multiset* and zips that with the corresponding `pinning.pins` to bind each prefix occurrence to its pinned SAID, producing one cursor per policy. This is pure — it derives the prefix positions from the policy graph and touches no log. It then **evaluates** each policy as a tree walk over those cursors, whose leaves read their pinned events inline from the verifier's **verification walk** (`source`), the single paged pass each referenced log gets for end-verifiability anyway: each leaf takes the next pin for its prefix (a `null`/absent slot fails that leaf) and reads that event as the walk reaches it — kel prefixes read the anchoring child and check the credential anchor at the required tier; iel prefixes read the named IEL event and recurse into its authentication policy; del prefixes read the delegating IEL event and confirm the delegate is in its delegated set (no authentication recursion — the delegate's authentication and the credential anchor are proven by a separate anchor pinning). The anchored entry point `evaluate_anchored_policy` **folds** these single-policy evaluations across the delegation path: one delegation hop per step (each hop's `del` policy constructed from the prefix the prior hop established, which is the linkage check), then one terminal anchor hop over the issuer's `iel` — ANDed, with the credential anchor checked only on the terminal hop.

High-level pseudo-code matching `bind_pins` + `evaluate_anchored_policy` + `evaluate_single_policy`:

```
bind_pins(delegations, anchor, expected_anchors) -> Cursors:        # PURE: no source arg, no log traversal
    cursors = {}
    for (policy, pinning) in delegations + [anchor]:
        cursors[policy.said] = zip(sorted_prefix_multiset(policy), pinning.pins)   # expand graph -> sorted prefix multiset -> zip with pins -> per-prefix cursor
    cursors[anchor.policy.said].required_anchors = expected_anchors                # anchor cursor only; every other cursor's set is {}
                                         # every kel leaf under the issuer's authentication is an anchoring leaf
    return cursors                       # just the positions of the prefixes in the policy graph, bound to their pinned SAIDs

# Orchestrator: build the hop policies + issuer iel, bind the pins (pure), then fold the delegation
# path [P0 .. Pn] into one conjunction of single-policy evaluations. The events the leaves read are
# validated INLINE by the verifier's verification walk (`source`): each referenced log is paged
# through once — that walk runs anyway for end-verifiability — and the pinned SAIDs are the positions
# it checks as it iterates, so a log referenced by several leaves is paged once and nothing
# materializes the whole chain (resident cost is bounded by the page, not the chain length). Linkage:
# hop k's policy is del(P_{k-1}), CONSTRUCTED from the prefix the prior hop established. Anchor checked
# ONLY on the terminal hop — bind_pins tagged it onto the anchor cursor, satisfies_kel confirms it.
evaluate_anchored_policy(issuance_policy, delegation_path, anchor_pinning, expected_anchors, source, required_tier) -> bool:
    if delegation_path is empty: return false
    issuer = delegation_path[last].prefix
    issuer_iel = parse_policy("iel(" + issuer + ")")
    delegations = [(issuance_policy, delegation_path[0].pinning)]
    for k in 1 .. len(delegation_path):
        hop = parse_policy("del(" + delegation_path[k-1].prefix + ")")   # linkage: prefix the prior hop established
        delegations.append((hop, delegation_path[k].pinning))
    cursors = bind_pins(delegations, (issuer_iel, anchor_pinning), expected_anchors)   # pure; no walking

    if not evaluate_single_policy(issuance_policy, cursors, source, Some(delegation_path[0].prefix), required_tier): return false
    for k in 1 .. len(delegation_path):
        hop = delegations[k].policy
        if not evaluate_single_policy(hop, cursors, source, Some(delegation_path[k].prefix), required_tier): return false
    return evaluate_single_policy(issuer_iel, cursors, source, None, required_tier)

evaluate_single_policy(policy, cursors, source, delegate, required_tier) -> bool:
    pins = cursors.cursor_for(policy.said)
    return eval_expr(policy.expr, pins, source, delegate, required_tier)

# Leaves take the NEXT pin for their prefix (slot order fixed by bind_pins) and read that event
# from the verification walk (`source`); composers aggregate. A prefix reached k times reads its
# k-th slot (occurrences ordered by traversal); the walk is exhaustive so that ordering holds. No
# walking is triggered here beyond the verifier's one paged verification walk per log, against which
# these checks run inline.
eval_expr(expr, pins, source, delegate, required_tier) -> bool:
    match expr:
        kel(prefix) => pins.take(prefix) is Some(prior) ? satisfies_kel(prior, prefix, pins.required_anchors(), source, required_tier) : false
        iel(prefix) => pins.take(prefix) is Some(ev)    ? satisfies_iel(ev, prefix, pins, source, delegate, required_tier) : false
        del(prefix) => pins.take(prefix) is Some(ev)    ? satisfies_del(ev, prefix, source, delegate) : false
        pol(said)   => eval_expr(parse_dsl(sadd.fetch(said).content).expr,
                                 pins, source, delegate, required_tier)
        thr(M, ss)  => count(eval_expr(s, pins, source, delegate, required_tier) for s in ss) >= M
        wgt(M, ws)  => sum(w for (s, w) in ws if eval_expr(s, pins, source, delegate, required_tier)) >= M

# kel: `prior` is the pinned event just before the anchoring event; its child S
# (S.previous == prior) is the next event the verification walk reaches — checking it there, inline,
# both dodges the SAID cycle and needs no search. The anchor requirement comes from the cursor
# (expected_anchors under the issuer's authentication, {} elsewhere). iel: the pin is an IEL event
# (not an anchoring event, so cycle-free); recurse into its authentication — the credential anchor is
# checked at the terminal kel leaves the recursion reaches. del: the pin is the DELEGATING IEL's own
# event; confirm the delegate is in its delegated set — no authentication recursion (the delegate's
# authentication / the credential anchor ride in a separate anchor pinning). Every event a leaf reads
# is validated by the paged verification walk per the trust-boundary principle; the pin names the
# position, so there is no search.

satisfies_kel(prior, leaf_prefix, required, source, required_tier):
    S = source.anchoring_child(leaf_prefix, prior)       # the anchoring child S where S.previous == prior, validated by the walk
    # `required` is the cursor's set of (anchor, min-tier) pairs: expected_anchors under the
    # issuer's authentication, {} elsewhere. required_tier is the baseline floor for the event.
    return S.prefix == leaf_prefix
        AND S.tier >= required_tier
        AND for all (anchor, tier) in required: S.anchors.contains(anchor) AND S.tier >= tier

satisfies_iel(iel_event, leaf_prefix, pins, source, delegate, required_tier):
    E = source.iel_event(leaf_prefix, iel_event)         # the IEL event, validated by the walk
    return E.prefix == leaf_prefix
        AND eval_expr(parse_dsl(sadd.fetch(E.authentication).content).expr,
                      pins, source, delegate, required_tier)

satisfies_del(iel_event, leaf_prefix, source, delegate):
    if delegate is None: return false                   # no identifier to test membership against
    E = source.iel_event(leaf_prefix, iel_event)         # the DELEGATING IEL's own event, validated by the walk
    return E.prefix == leaf_prefix
        AND E.delegated_set_contains(delegate)
```

**Semantics notes:**

- **Pinning context propagates uniformly.** A `pol(said)` recursion — and an `iel` authentication recursion — uses the same `pins` cursor, `source`, `delegate`, and `required_tier` as the outer evaluation. The credential-anchor requirement rides on the `pins` cursor itself (`bind_pins` set it on the anchor cursor, empty on the others), so it propagates with that recursion to every kel leaf reached under the issuer's authentication — and, being cursor-scoped rather than chain-scoped, never leaks onto an issuance-policy kel leaf that names the same chain. The whole expanded graph evaluates against one set of cursors, each occurrence consuming its own slot in traversal order. A `del` leaf does not recurse: it consumes its one slot (the delegating IEL's event), tests delegate membership, and stops — the delegate's authentication and the credential anchor are proven by a separate anchor pinning, not this cursor.
- **The SAID cycle, and why kel prefixes pin the *prior* event.** A SAID is the hash of the SAD with its own said-field zeroed, so it depends on every other field. The event that anchors credential `C` lists `said(C)` in its `anchors`; `C` commits to the Pinning (`said(P)`); `P` lists the pinned event's SAID. Pinning the anchoring event directly would close the loop `said(anchor) → said(C) → said(P) → said(anchor)` — unconstructable. So a kel prefix pins the event *just prior* and the verifier rederives the anchoring child. iel/del prefixes are cycle-free: they pin IEL events (fixing the authentication / delegation state), which never carry the credential anchor. This is orthogonal to the sorted-multiset slotting, which only decides slot order; avoiding a second walk of a shared log is handled by the verification walk paging that log once and checking all of its pinned positions inline (the pinned SAIDs are supplied up front as the positions to check), not by the wire format. `bind_pins` itself only fixes slot order and touches no log.
- **`pol(said)` reference cycles are structurally impossible.** Content-addressed references can't form a cycle without a Blake3-256 collision (two Policy SADs mutually containing each other's SAIDs). No runtime cycle check needed.
- **Depth bound.** Implementations should impose a soft depth limit on `pol()` recursion (e.g., 16 levels) and deny on exceeding — implementation concern, out of scope here.
- **Tier check is in the leaf helpers, not the composers.** A kel prefix's `satisfies_kel` rejects an anchoring event hosted below `required_tier`; the tier requirement propagates unchanged through the iel authentication recursion to the terminal kel leaves. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized expression kinds → deny.** Forward-compatibility: older verifiers encountering newer DSL primitives return unsatisfied for that sub-expression; composer aggregation propagates this as a clean deny rather than a verification crash.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

- **IEL `Evl` / `Dec`** — gated by `governance`
- **IEL `Del` / `Rsc`** — gated by `delegation`
- **SEL `Est` / `Ixn` / `Evl` / `Rpr` / `Dec`** — gated by `governance`
- **Application-defined gates** — credentials, signed requests, etc. — gated by application-specific policy references

## End-to-end access example

Putting the two entry points together: a resource grants an action iff the presented credential
is **validly issued and not withdrawn** AND the bearer **currently controls the credential's
subject** AND the credential's **roles cover the action's permission**. Three independent checks,
three different mechanisms:

```rust
// A bearer requests `action` on a resource, presenting `cred` (with its two pinnings)
// and a fresh signature over `challenge` (a server-issued nonce digest).
fn authorize(
    cred: &Credential,
    action: Action,
    challenge: &Digest256,
    attestations: &[Attestation],
    issuance_policy: &Policy,       // the resource's configured issuance policy
    source: &impl EventSource,
) -> Result<bool, PolicyError> {
    // 1. Validity — the credential is anchored by a recognized issuer (through the
    //    delegation path) at the required tier, and no withdrawal anchor was found.
    let cred_anchor: HashSet<(Digest256, Tier)> =
        [(cred.said, Tier::One)].into_iter().collect();
    let valid = evaluate_anchored_policy(
        issuance_policy,
        &cred.delegation_path(),     // [(issuer, issuance_pinning)] in the single-hop case
        &cred.anchor_pinning,
        &cred_anchor,
        source,
        Tier::One,
    )?;
    if !valid {
        return Ok(false);            // not issued by a recognized authority, or withdrawn
    }

    // 2. Identity — the bearer presently controls the credential's SUBJECT. The subject is
    //    an IEL; `iel(subject)` defers to the subject's own authentication policy, so a rotated
    //    or multi-sig subject still authenticates correctly. The challenge defeats replay.
    let subject_policy = parse_policy(&format!("iel({})", cred.subject))?;
    let is_holder = evaluate_current_policy(
        &subject_policy,
        challenge,
        attestations,
        source,
        Tier::One,
    )?;
    if !is_holder {
        return Ok(false);            // credential presented by someone who isn't the subject
    }

    // 3. Authorization — the application maps the credential's roles to permissions and
    //    grants iff the action's required permission is covered. This step is pure
    //    application policy; the DSL's job ended once validity + identity were established.
    let granted = cred.roles
        .iter()
        .flat_map(permissions_for_role)              // application-defined role → permissions
        .any(|p| p == action.required_permission()); // application-defined action → permission
    Ok(granted)
}
```

The three checks are deliberately separable, each answering a different question:

- **Validity** (`evaluate_anchored_policy`) is about the *issuer* — did a recognized authority
  anchor this credential at the required tier, and is it still withdrawal-free? It checks the
  pinned events inline in the verification walk; it says nothing about who is holding the
  credential right now.
- **Identity** (`evaluate_current_policy`) is about the *bearer* — does whoever is presenting the
  credential currently control its subject identity? It checks live attestations over a fresh
  challenge at the chain tip; it says nothing about whether the credential was validly issued.
- **Authorization** is the *application's* — given a valid credential held by its rightful
  subject, does the carried role grant the requested action? This is outside the DSL: roles and
  permissions are the app's vocabulary, not the chain's.

Splitting them this way keeps each failure mode independent: a stolen credential is useless
(identity fails), a withdrawn credential is useless (validity fails), and an over-broad
credential is still bounded by the app's role→permission map (authorization fails).

## Open items

1. **Verifier evaluation algorithm.** Recursion semantics (`iel(P)` evaluating against P's own policy, which may itself contain `iel(...)`), cycle detection, depth limits, caching strategies. Belongs in implementation specs once `lib/vdti` planning advances.

2. **Extension points.** The DSL is closed at the primitive level (7 primitives — leaves, the `mem` membership array, composers). Future primitives (new chain types; new leaf semantics) would require DSL extension. The forward-compat deny rule (§Verifier behavior) makes additions soft-compatible — old verifiers safely deny on unrecognized expressions.

## Forward-refs

- [`event-logs/iel/`](event-logs/iel/) — IEL primitive (subsequent sub-issue); references this doc for governance / delegation / authentication policy evaluation
- [`event-logs/sel/`](event-logs/sel/) — SEL primitive (subsequent sub-issue); references this doc for SEL governance
- `lib/vdti` — verifier implementation; evaluates DSL expressions per this spec
