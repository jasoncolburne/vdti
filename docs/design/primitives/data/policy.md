# Policy DSL

Canonical specification of vdti's policy DSL — the expression language used to encode authorization rules across the event-log primitives.

A **policy** is a [SAD](sad/sad.md) whose content is a DSL expression. The IEL primitive references policies (governance and delegation); the SEL primitive references policies (governance); applications reference policies for their own authorization needs. The DSL is the language; Policy SADs are the storage format; the verifier evaluates DSL expressions against signed requests and the relevant chain state.

This doc states the surface (the primitives that make up the DSL), their semantics, and how composition works. It does not enumerate per-primitive doctrine (which lives in [`event-logs/event-shape.md`](event-logs/event-shape.md), the per-primitive specs, and [`../../protocol-doctrine.md`](../../protocol-doctrine.md)) and does not specify the verifier implementation algorithm (which lives in `lib/vdti` planning material).

## Where policies appear

Policies are referenced by Policy SAD SAIDs from chain-event fields:

- **IEL `governance`** (required at inception; evolved via `Evl`) — gates IEL self-mutation events.
- **IEL `delegation`** (optional at inception; evolved via `Evl`) — gates IEL delegation events (`Del` / `Rsc`).
- **SEL `governance`** (declared at SEL `Icp`; evolved via SEL `Evl`) — gates SEL events (`Est` / `Ixn` / `Evl` / `Rpr` / `Dec`).
- **Application-defined policy references** — applications may attach policy SAIDs to their own data structures (credentials, signed requests, custody SADs) following the same pattern.

In each case the field holds a `Digest256` pointing at a Policy SAD. The verifier dereferences, parses the DSL expression, and evaluates it.

## The DSL surface — 6 primitives

```
kel(prefix)        iel(prefix)        del(prefix)
pol(said)
thr(M, [...])      wgt(M, [...])
```

Three chain-state **leaves** (`kel`, `iel`, `del`), one policy reference **leaf** (`pol`), two **composers** (`thr`, `wgt`). The grammar:

```
expr   ::= leaf | composer
leaf   ::=  kel(prefix) | iel(prefix) | del(prefix) | pol(said)
composer ::= thr(M, [expr, ...]) | wgt(M, [(expr, w), ...])
```

Every well-formed policy is built from these primitives.

### Shape

Take the policy `thr(2, [pol(A_said), iel(X_prefix), kel(Y_prefix)])`, where the nested
policy `A_said` is `kel(A_prefix)` and IEL `X_prefix`'s governance is `kel(Y_prefix)`. The
verifier *expands the whole graph* — descending through `pol()` and through each `iel`/`del`'s
governance — to the *multiset* of prefixes it references: `{A_prefix, X_prefix, Y_prefix,
Y_prefix}`. `Y_prefix` appears twice — once as the top-level `kel(Y_prefix)` branch, once
reached through `X`'s governance — and each occurrence gets its own slot. The issuer pins one
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
through each `iel`/`del` governance, taking one slot per prefix occurrence:

```
  thr(2)
  ├─ pol(A_said) ──▶ kel(A_prefix)        ▷ A_prefix   (pol → kel)
  ├─ iel(X_prefix)                         ▷ X_prefix   (the iel leaf itself)
  │    └─ governance ──▶ kel(Y_prefix)     ▷ Y_prefix   (via X's governance)
  └─ kel(Y_prefix)                         ▷ Y_prefix   (top-level branch)

  sort the occurrences into the pin multiset:

    slot 0     slot 1     slot 2              slot 3
    A_prefix   X_prefix   Y_prefix            Y_prefix
    pol→kel    iel event  via X's governance  top-level kel
```

`iel(X)` contributes two slots — its own (the IEL event) and `Y_prefix` from its governance —
and `Y_prefix` lands twice, the via-governance occurrence ordered before the top-level one.

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
- **iel prefix** → the SAID of the IEL event itself. This fixes the IEL's governance at that
  state; satisfaction recurses into that governance, whose leaves carry their own pins. An
  IEL event doesn't carry the credential anchor, so there's no cycle and no prior-event trick.
- **del prefix** → the SAID of the *delegating* IEL's own event, fixing which delegation state
  the membership is tested against. The verifier walks that IEL's chain and confirms the
  delegate identifier (supplied by verifier context — in the credential flow, the issuer) is
  currently in its delegated set. The delegate's own governance is *not* reached here: the
  delegate isn't named by the policy, so it's evidence-shaped and can't occupy a fixed, sortable
  slot. When a
  credential needs to prove both delegation and where it's anchored, the anchor rides in a
  separate issuance pinning over the issuer's governance (see *Policies and Pinnings*).

Pinning eliminates the verifier's search-for-evidence step — slot position names the prefix
occurrence, the pinned SAID names the chain position — while the verifier still walks each
chain to verify integrity (per the trust-boundary principle). Listing a prefix twice doesn't
force two full walks: the verifier collects every pinned SAID that falls on a given log and
locates them in a single verified walk — the SAIDs to find are supplied before the walk, the
walk's verification token reports which were found, and the caller confirms every required SAID
was found.

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
    Pol(Digest256),                       // nested Policy SAD SAID
    Thr(u64, Vec<PolicyExpr>),            // threshold M, sub-expressions
    Wgt(u64, Vec<(PolicyExpr, u32)>),     // threshold M, (sub, weight) pairs
}

pub struct Policy {
    said: Digest256,
    expr: PolicyExpr,
}

pub struct Pinning {
    said: Digest256,
    pins: Vec<Option<Digest256>>,
}
```

## API Surface

The public evaluation entry points are `evaluate_anchored_policy` (pinned, walks chains) and `evaluate_current_policy` (live signatures). The anchored entry is fed by a `gather_evidence` phase and composes a single-policy helper, `evaluate_single_policy`.

```rust
// Gather phase — walk each referenced chain exactly once. Binds every (policy,
// pinning) pair's slots to their pinned SAIDs (`bind_pins`), groups those SAIDs by
// the chain they fall on, and walks each chain a single time — registering the
// chain's SAIDs up front and reading them back out of the walk's verification
// token. A chain referenced by several pinnings is still walked once. The `issuance`
// binding is the anchoring hop: gather records `expected_anchors` as the required-
// anchor set on the ISSUANCE CURSOR — every kel leaf reached under the issuer's
// governance is an anchoring leaf (one chain each, several under a multi-KEL threshold).
// Every other binding's cursor carries an empty required set, so a control-policy kel
// leaf that names a chain the issuer's governance also reaches never inherits the
// requirement. `satisfies_kel` reads the required set off the cursor it evaluates under
// and the hosted anchors off the walked chain's token — the requirement is scoped to the
// issuer's binding, never a property of the shared chain. Returns the bound per-leaf
// SAIDs and one token per chain, packaged as `Evidence`.
pub fn gather_evidence(
    delegations: &[(&Policy, &Pinning)],
    issuance: (&Policy, &Pinning),
    expected_anchors: &HashSet<Digest256>,
    source: &impl EventSource,
) -> Result<Evidence, PolicyError>;

// Anchored check (public entry) — delegation + anchoring for a credential whose issuer
// may sit at the end of a delegation chain. Self-contained: it builds the hop policies,
// gathers `Evidence` (the only walking happens here), folds the per-hop evaluations, and
// returns the verdict — the caller just supplies the credential's pinnings, not a
// pre-gathered `Evidence` or a bindings list. `delegation_path` is the ordered list of
// delegation hops `(prefix, membership_pinning)`: hop 0 is delegated by `control_policy`
// (its pinning is the control pinning), each later hop by `del(prior_prefix)` (the linkage
// check), and the last hop's prefix is the issuer. `issuance_pinning` anchors the credential
// through the issuer's `iel`. `expected_anchors` is the set of SAIDs the anchoring event must
// host (e.g. the credential SAID, plus any co-anchored SADs); it is handed to `gather_evidence`
// as the issuance hop's requirement — gather records it on the issuance cursor and
// `satisfies_kel` reads it from there, so it is scoped to the issuer and never threaded
// through the per-hop walks.
// Single-hop case: `delegation_path == [(issuer, control_pinning)]`.
pub fn evaluate_anchored_policy(
    control_policy: &Policy,
    delegation_path: &[(Digest256, &Pinning)],
    issuance_pinning: &Pinning,
    expected_anchors: &HashSet<Digest256>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError>;

// Single-policy helper (internal) — pure tree walk over gathered `Evidence` for ONE policy.
// `evaluate_anchored_policy` calls this once per hop; not a public entry. No walking: each
// leaf reads its slot's pinned SAID and consults the relevant chain's token; composers
// aggregate. The Pinning is consumed in the gather phase, not here. The anchor requirement
// is not threaded in: it rides on the cursor (gather set it on the issuance cursor) and
// `satisfies_kel` reads it from there. `delegate` is the identifier under test for `del` membership
// (the prefix the hop must confirm is delegated); pass `None` when the policy has no `del`
// leaves (e.g. the terminal `iel` anchor hop).
fn evaluate_single_policy(
    policy: &Policy,
    evidence: &Evidence,
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

`evaluate_anchored_policy` returns `Ok(true)` iff the issuer is reached through the full delegation path AND the expected anchors are hosted on the issuer's governance at the required tier or above. `evaluate_current_policy` returns `Ok(true)` iff the provided signatures over `challenge` cover the policy's leaves at current chain state with the required tier. Both return `Ok(false)` for clean unsatisfied; `Err(_)` for malformed inputs / fetch failures.

The auth flow typically calls both kinds of check. `evaluate_anchored_policy` is self-contained: internally it builds the hop policies, calls `gather_evidence` once — walking each referenced chain a single time across *all* of the credential's pinnings — then folds the per-hop evaluations over that shared `Evidence`: one **delegation** hop per step (the **control pinning** confirms the first delegate; each subsequent hop's `del` pinning confirms the next), then one terminal **anchoring** hop over the issuer's `iel` (the **issuance pinning**) proving the cred is anchored on the issuer's governance (see *Policies and Pinnings*). Because every hop reads the shared `Evidence`, a chain referenced by several pinnings is still walked once. The **current-state** check (`evaluate_current_policy`) validates that the bearer presently controls the policy the cred names — it reuses the same delegation machinery over current chain state and then verifies the challenge signed under current state.

### Policies and Pinnings

#### Use case

Let's say we have an access control policy we declare that permits resource access by specifying
prefixes of IELs that endorse credentials bound to user identities. A credential SAID must be
anchored in a way that satisfies the control policy for the credential to be valid.

The credential control policy the server is configured with may be:

```
thr(1, del(iel_prefix_1), del(iel_prefix_2), del(iel_prefix_3))
```

which says that prefixes 1 through 3 may delegate to other prefixes, and only a single signature
from any delegate of prefixes 1 through 3 is required to satisfy the policy.

When a credential is issued, the issuer burns **two pinnings** into it. The control policy
names the *delegating* IELs but not their delegates, so the issuer — itself a delegate,
discovered from evidence — can't be pre-positioned in the control policy's slot layout. Rather
than let the slot count depend on what's evidenced, the evidence splits into two pinnings, each
sized against a policy whose shape is known up front:

- a **control pinning** over the server's control policy — proves *delegation* (the issuer is
  a current delegate of one of the delegating IELs);
- an **issuance pinning** over the issuer's own **IEL**, `iel(dlg_prefix)` — proves the *anchor*
  while binding identity to governance: the issuer's IEL names its governance KEL, and the
  credential is anchored on that KEL at the required tier. Routing through the IEL (rather than
  naming the governance KEL directly) is what ties the anchoring KEL to the *delegated*
  identity — otherwise the issuer's governance would be an unbound, credential-supplied claim.

Both ride on the credential. Say the credential is issued by `dlg_prefix`, a delegate of
`iel_prefix_2`, whose IEL governance is `kel(dlg_kel_prefix)`.

Two graphs, two pinnings. The control policy expands to one slot per `del` and STOPS — `del`
never descends into the delegate. Proving where the credential is anchored is a separate graph
rooted at the issuer's own IEL, `iel(dlg_prefix)`, which expands through the issuer's governance
to the anchoring KEL event:

```
  control policy                           control pinning
  ───────────────────────────────────      ───────────────
  thr(1)
  ├─ del(iel_prefix_1)  ▷ iel_prefix_1     null               — un-evidenced
  ├─ del(iel_prefix_2)  ▷ iel_prefix_2     {iel2_event_said}
  │     └─ is dlg_prefix in its delegated set?  (delegate, from verifier context)
  └─ del(iel_prefix_3)  ▷ iel_prefix_3     null               — un-evidenced

  dlg_prefix (the issuer) is NOT a slot here — it's evidence-shaped, found in
  iel_prefix_2's delegated set. Its anchor rides in a separate pinning, rooted at the
  issuer's own IEL so the anchoring KEL is bound to the delegated identity:

  iel(dlg_prefix)  (identity → governance → anchor)      issuance pinning
  ─────────────────────────────────────────────────     ────────────────
  iel(dlg_prefix)                    ▷ dlg_prefix        {dlg_iel_event_said}
  └─ governance kel(dlg_kel_prefix)  ▷ dlg_kel_prefix    {dlg_kel_prior_kel_said}
        └─ prior event; its child anchors the credential at the required tier
```

**Control pinning.** The control policy `thr(1, del(iel_prefix_1), del(iel_prefix_2),
del(iel_prefix_3))` expands to one slot per `del` — the *delegating* IEL's own event, fixing which
delegation state the issuer claims membership against. (The delegate's governance is not
expanded here; it's evidence-shaped, so it lives in the issuance pinning.) The issuer evidences
only the `iel_prefix_2` branch:

```
{
    "said": "{control_pinning_said}",
    "pins": [
        null,                   // iel_prefix_1 — un-evidenced
        "{iel2_event_said}",    // iel_prefix_2 — the IEL event whose delegated set holds dlg_prefix
        null                    // iel_prefix_3 — un-evidenced
    ]
}
```

**Issuance pinning.** The issuer's IEL policy `iel(dlg_prefix)` expands to two slots — the
issuer's IEL event (fixing which governance state applies) and, through that governance
`kel(dlg_kel_prefix)`, the KEL event just *prior* to the anchoring event (the anchoring event
commits to the credential, so its own SAID is unconstructable here; see the SAID-cycle note):

```
{
    "said": "{issuance_pinning_said}",
    "pins": [
        "{dlg_iel_event_said}",      // dlg_prefix — IEL event fixing the governance state
        "{dlg_kel_prior_kel_said}"   // dlg_kel_prefix — prior event; its child anchors the credential
    ]
}
```

(slots labelled by branch for readability; on the wire they follow sorted prefix order.)

**Verifying.** The credential is valid iff *both* hold:

- **Delegation** — evaluating the control policy against the control pinning, the
  `del(iel_prefix_2)` leaf reads its pinned IEL event, walks `iel_prefix_2`'s chain, and
  confirms `dlg_prefix` (the issuer, supplied by verifier context) is currently in that IEL's
  delegated set. A single satisfied delegate branch clears the `thr(1, ...)`.
- **Anchor** — evaluating `iel(dlg_prefix)` against the issuance pinning, the `iel(dlg_prefix)`
  leaf reads its pinned IEL event (binding the issuer to its governance `kel(dlg_kel_prefix)`)
  and recurses into that governance; the `kel(dlg_kel_prefix)` leaf resolves the anchoring event
  `S` (`S.previous == dlg_kel_prior_kel_said`) and checks `S` is at the required tier and anchors
  the credential SAID. Because the anchor is reached *through* the delegated issuer's IEL, the
  anchoring KEL is bound to the delegated identity rather than asserted by the credential.

The two pinnings exist only to make each policy's slot count self-determining. Verification
groups the pinned SAIDs from both pinnings by the log they fall on and locates each log's set in
a single verified walk: the SAIDs to find are supplied up front, the walk's verification token
reports which were found, and the caller confirms every required SAID was found. So a chain
reached on both paths is walked once, not twice.

```rust
let iel_prefix_1 = Digest256::from_qb64("KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")?;
let iel_prefix_2 = Digest256::from_qb64("KBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")?;
let iel_prefix_3 = Digest256::from_qb64("KCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")?;

let control_policy = parse_policy(&format!(
    "thr(1, del({}), del({}), del({}))",
    iel_prefix_1, iel_prefix_2, iel_prefix_3
))?;

let dlg_prefix = cred.issuer_prefix; // the issuer: a delegate of iel_prefix_2, AND the anchor host

// Both pinnings ride on the credential.
let control_pinning  = parse_pinning_sad(&sadd_fetch(&cred.control_pinning_said)?)?;
let issuance_pinning = parse_pinning_sad(&sadd_fetch(&cred.issuance_pinning_said)?)?;

let cred_anchor: HashSet<Digest256> = [credential_said].into_iter().collect();

// One self-contained call: it builds the issuer's `iel` policy internally, gathers
// Evidence once (every referenced chain walked a single time), folds the per-hop
// delegation checks, and confirms the credential anchor off the issuance chain's token. The
// caller supplies only the credential's pinnings and the anchor set — no manual gather,
// no pre-built `iel(dlg_prefix)`. Single-hop here: dlg_prefix is delegated directly by
// the control policy and is itself the issuer. For a delegate-of-a-delegate, extend
// `delegation_path` with that hop's `(prefix, del_pinning)`.
let satisfied = evaluate_anchored_policy(
    &control_policy,
    &[(dlg_prefix, &control_pinning)], // delegation_path = [(issuer, control_pinning)]
    &issuance_pinning,
    &cred_anchor,
    source,
    Tier::One,
)?;
```

> **TODO (pending [event-shape.md](event-logs/event-shape.md)).** The evaluation architecture below — two-pinning model, the gather/evaluate split (`gather_evidence` walks; `evaluate_*` are pure over `Evidence`), the multi-hop delegation-path fold (delegation hops + one terminal anchor hop, anchor checked only on the terminal), sorted-multiset slotting / `PinCursor`, `delegate` threading, `del` as membership-only, and the supply-SAIDs-up-front / one-walk-per-log / token mechanism — is stable. What may still shift is the per-primitive **leaf field access** that depends on the settled event shapes: the kel anchor model and prior-event/SAID-cycle rederivation (`s.anchors`, `s.previous`), the iel `governance` field name and its recursion, the `del` delegated-set construction (`Del`/`Rsc` walk, `delegated_set_contains`), and where `tier` lives on the event. Treat those specifics as provisional until `event-shape.md` lands.

Implementation:

```rust
// gather_evidence binds and walks. For each (policy, pinning): expand the policy
// graph — descending through pol() and through each iel governance — to its multiset
// of referenced prefix occurrences, sort into wire slot order (by prefix, equal
// prefixes kept in traversal order), then zip with `pinning.pins` to bind each
// occurrence to its pinned SAID. A `del` leaf contributes exactly one occurrence — its
// delegating IEL prefix — and does NOT descend into the delegate's governance: the
// delegate is evidence-shaped (not named by the policy), so its subtree can't be sized
// here; it rides in a separate issuance pinning. Union the `delegations` bindings with
// the single `issuance` binding, group the bound SAIDs across ALL pinnings by the chain
// they fall on, walk each chain once (registering its SAIDs up front, reading them back
// out of the verification token), and return the per-policy cursors plus one token per
// chain as `Evidence`. The expansion mirrors the eval walk below, so issuer and verifier
// agree on slot order. The `issuance` binding is the anchoring hop: gather attaches
// `expected_anchors` to the ISSUANCE CURSOR as its required-anchor set — every kel leaf
// reached under the issuer's governance is an anchoring leaf (one chain each, several
// under a multi-KEL threshold); every other binding's cursor gets an empty required set.
// The requirement travels with the cursor, scoped to the issuer's binding, so a control-
// policy kel leaf naming a chain the issuer's governance also reaches never inherits it.
// The hosted anchors come from the walked chain's token regardless; `satisfies_kel` reads
// the required set off the cursor and the anchors off the token, so the requirement is
// never a property of the shared chain.
pub fn gather_evidence(
    delegations: &[(&Policy, &Pinning)],
    issuance: (&Policy, &Pinning),
    expected_anchors: &HashSet<Digest256>,
    source: &impl EventSource,
) -> Result<Evidence, PolicyError> {
    // bind_pins each pair (delegations + issuance) -> group bound SAIDs by chain ->
    // walk each chain once -> tokens; attach expected_anchors to the issuance cursor
}

// evaluate_anchored_policy is self-contained: it builds the hop policies, gathers Evidence
// ONCE (the only walking), then folds the delegation chain into one conjunction of pure
// single-policy evaluations and returns the verdict. `delegation_path` is the ordered list
// of delegation hops `(prefix, membership_pinning)`: hop 0 is delegated by control_policy
// (its pinning is the control pinning), each later hop by `del(prior_prefix)`, and the last
// hop's prefix is the issuer; `issuance_pinning` anchors through the issuer's `iel`. Each hop
// is a term: delegation hops test the next delegate; the terminal hop tests no delegate. The
// anchor is checked ONLY on the terminal hop, but not here — `gather_evidence` records
// `expected_anchors` on the issuance cursor and `satisfies_kel` confirms it. The
// linkage invariant — hop k's policy names the prefix the prior hop established — is enforced
// here by CONSTRUCTING `del(prior_prefix)` from the path, not by trusting a policy lifted off
// the cred.
pub fn evaluate_anchored_policy(
    control_policy: &Policy,
    delegation_path: &[(Digest256, &Pinning)],
    issuance_pinning: &Pinning,
    expected_anchors: &HashSet<Digest256>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let (issuer, _) = match delegation_path.last() {
        Some(hop) => hop,
        None => return Ok(false),    // no path, nothing to check
    };

    // Build hop policies (linkage: hop k names the prefix the prior hop established) and the
    // terminal anchor policy, then bind every (policy, pinning) into ONE gather so each
    // referenced chain is walked exactly once. The issuance binding is passed distinctly
    // so gather knows which chain carries the credential's anchor.
    let issuer_iel = parse_policy(&format!("iel({})", issuer))?;
    let hop_policies: Vec<Policy> = (1..delegation_path.len())
        .map(|k| parse_policy(&format!("del({})", delegation_path[k - 1].0)))
        .collect::<Result<_, _>>()?;

    let mut delegations: Vec<(&Policy, &Pinning)> = vec![(control_policy, delegation_path[0].1)];
    for (k, hop_policy) in hop_policies.iter().enumerate() {
        delegations.push((hop_policy, delegation_path[k + 1].1)); // membership pinning for hop k+1
    }

    let evidence = gather_evidence(&delegations, (&issuer_iel, issuance_pinning),
                                   expected_anchors, source)?;

    // Fold over the gathered evidence. Hop 0 — control policy delegates the first prefix.
    if !evaluate_single_policy(control_policy, &evidence,
                               Some(&delegation_path[0].0), required_tier)? {
        return Ok(false);
    }

    // Hops 1..n — each delegator (the prefix the prior hop established) must delegate the next.
    for (k, hop_policy) in hop_policies.iter().enumerate() {
        if !evaluate_single_policy(hop_policy, &evidence,
                                   Some(&delegation_path[k + 1].0), required_tier)? {
            return Ok(false);
        }
    }

    // Terminal — the issuer's governance anchors the credential. `satisfies_kel` reads the
    // anchor requirement off the issuance cursor; no anchor arg threaded in here.
    evaluate_single_policy(&issuer_iel, &evidence, None, required_tier)
}

fn evaluate_single_policy(
    policy: &Policy,
    evidence: &Evidence,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    // Pure tree walk over already-gathered evidence. `evidence` carries this policy's
    // leaf->SAID cursor (bound during gather) and one verification token per chain; each
    // leaf reads its slot's SAID and consults the chain's token. No walking here.
    let mut pins = evidence.cursor_for(&policy.said)?;
    eval_expr(&policy.expr, &mut pins, evidence, delegate, required_tier)
}

// `pins` is a cursor: per prefix, the pins for that prefix's occurrences in traversal
// order. Each leaf takes the NEXT pin for its prefix and consults `evidence` (the
// chain's already-built token); composers aggregate sub-results. The walk is exhaustive
// (composers evaluate every branch — no short-circuit) so the k-th leaf reaching a
// prefix consumes that prefix's k-th slot, matching the order gather laid them down. No
// chain walking happens here — every referenced log was walked once during gather.
fn eval_expr(
    expr: &PolicyExpr,
    pins: &mut PinCursor,
    evidence: &Evidence,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    match expr {
        PolicyExpr::Kel(prefix) => match pins.take(prefix) {
            Some(prior_said) => {
                let required = pins.required_anchors(); // this binding's set: expected_anchors on the issuance cursor, {} elsewhere
                satisfies_kel(&prior_said, prefix, required, evidence, required_tier)
            }
            None => Ok(false),
        },
        PolicyExpr::Iel(prefix) => match pins.take(prefix) {
            Some(iel_event_said) => {
                satisfies_iel(&iel_event_said, prefix, pins, evidence, delegate, required_tier)
            }
            None => Ok(false),
        },
        PolicyExpr::Del(delegating_prefix) => match pins.take(delegating_prefix) {
            Some(iel_event_said) => satisfies_del(&iel_event_said, delegating_prefix, evidence, delegate),
            None => Ok(false),
        },
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, pins, evidence, delegate, required_tier)
        }
        PolicyExpr::Thr(m, subs) => {
            let mut count: u64 = 0;
            for sub in subs {
                if eval_expr(sub, pins, evidence, delegate, required_tier)? {
                    count += 1;
                }
            }
            Ok(count >= *m)
        }
        PolicyExpr::Wgt(m, weighted) => {
            let mut sum: u64 = 0;
            for (sub, w) in weighted {
                if eval_expr(sub, pins, evidence, delegate, required_tier)? {
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
// The chain was walked and verified to the anchoring event during gather (trust-
// boundary principle); `S` is its unique child (`S.previous == prior_said`), and its
// facts (prefix, tier, anchors) are read from the chain's token. The anchor requirement
// (`required`) is supplied by the caller off the binding's cursor — `expected_anchors`
// under the issuer's governance, empty otherwise — so a control-policy kel leaf naming
// the same chain never inherits it. Check anchor + tier.
fn satisfies_kel(
    prior_said: &Digest256,
    leaf_prefix: &Digest256,
    required: &HashSet<Digest256>,
    evidence: &Evidence,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let s = evidence.anchoring_child(leaf_prefix, prior_said)?; // S where S.previous == prior_said
    Ok(
        s.prefix == *leaf_prefix
            && s.tier >= required_tier
            && required.is_subset(&s.anchors)
    )
}

// iel(prefix): `iel_event_said` is the IEL event itself — NOT an anchoring event,
// so it carries no credential anchor and needs no prior-event trick. It fixes the
// IEL's governance at that state; satisfaction recurses into that governance, whose
// leaves carry their own pins (the credential anchor is checked at the terminal kel
// leaves the recursion reaches). The IEL event was verified during gather; its facts
// come from the chain's token.
fn satisfies_iel(
    iel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    pins: &mut PinCursor,
    evidence: &Evidence,
    delegate: Option<&Digest256>,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let iel = evidence.iel_event(leaf_prefix, iel_event_said)?;
    if iel.prefix != *leaf_prefix {
        return Ok(false);
    }
    let governance = parse_policy_sad(&sadd_fetch(&iel.governance)?)?;
    eval_expr(&governance.expr, pins, evidence, delegate, required_tier)
}

// del(prefix): `iel_event_said` is the DELEGATING IEL's own event (its prefix == leaf_prefix),
// fixing which delegation state membership is tested against. Confirm the delegate (the
// issuer, from verifier context) is in that IEL's delegated set as of the pinned event. No
// anchor check and no governance recursion: the delegate's governance and the credential
// anchor are proven separately, by the issuance pinning. The delegating IEL's chain was
// verified to this event during gather; its facts come from the chain's token.
fn satisfies_del(
    iel_event_said: &Digest256,
    leaf_prefix: &Digest256,
    evidence: &Evidence,
    delegate: Option<&Digest256>,
) -> Result<bool, PolicyError> {
    let delegate = match delegate {
        Some(c) => c,
        None => return Ok(false), // no identifier to test membership against
    };
    let iel = evidence.iel_event(leaf_prefix, iel_event_said)?; // delegating IEL's event, verified in gather
    Ok(iel.prefix == *leaf_prefix && iel.delegated_set_contains(delegate))
}
```

## Leaf semantics

Each leaf evaluates against chain state and a signed request (or delegate identifier, for `del`). Leaves return satisfied / unsatisfied.

### `iel(prefix)` — IEL member-set membership

The leaf is satisfied iff the signed request was authored by a current member of the IEL identified by `prefix`. "Member" means: the request's signing party satisfies the IEL's own `governance` policy at the IEL's current chain tip.

This is recursive — `iel(P)`'s leaf check delegates to P's own governance policy evaluation. The recursion terminates at non-`iel` leaves (`kel` and `del`).

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

**Single-key authorization** — used by simple SEL governance where one device controls the SEL:
```
kel(operator_kel_prefix)
```

**IEL membership** — used by IEL governance for a basic identity:
```
iel(self_iel_prefix)
```

**Multi-IEL threshold** — federation governance with 3-of-5:
```
thr(3, [iel(member1), iel(member2), iel(member3), iel(member4), iel(member5)])
```

**Federation weighted with emergency override**:
```
wgt(60, [
    (iel(member1), 40),
    (iel(member2), 40),
    (iel(member3), 40),
    (kel(emergency_key), 100)
])
```

Any two members satisfy (80 ≥ 60), or the emergency key alone (100 ≥ 60).

## Composition semantics

- **Leaves evaluate independently.** One leaf's satisfaction never depends on another's. The shared pin cursor and the per-log single-walk evidence gathering are plumbing (slot assignment, walk reuse), not satisfaction coupling.
- **Composers are pure aggregators.** They take leaf / sub-composer results and produce satisfaction signals. No side effects.
- **Boundedness.** Bounded cost — a finite expression tree, and one chain walk per referenced chain in gather (not per leaf). Million-event chains walk in O(chain length) once, parallelizable across chains; evaluation itself is a cheap tree walk over the resulting tokens.
- **Deterministic.** Given a fixed chain state and signed request, evaluation is deterministic. Verifiers across nodes converge.

## Verifier behavior

The verifier first **gathers evidence**: `gather_evidence` expands each policy graph to its sorted prefix *multiset*, zips that with the corresponding `pinning.pins` to bind each prefix occurrence to its pinned SAID, groups the bound SAIDs across all pinnings by chain, and walks each chain once into a verification token. It then **evaluates** each policy as a pure tree walk over that `Evidence`: each leaf takes the next pin for its prefix (a `null`/absent slot fails that leaf) and consults the chain's token — kel prefixes read the anchoring child and check the credential anchor at the required tier; iel prefixes read the named IEL event and recurse into its governance; del prefixes read the delegating IEL event and confirm the delegate is in its delegated set (no governance recursion — the delegate's governance and the credential anchor are proven by a separate issuance pinning). The anchored entry point `evaluate_anchored_policy` **folds** these single-policy evaluations across the delegation path: one delegation hop per step (each hop's `del` policy constructed from the prefix the prior hop established, which is the linkage check), then one terminal anchor hop over the issuer's `iel` — ANDed, with the credential anchor checked only on the terminal hop.

High-level pseudo-code matching `gather_evidence` + `evaluate_anchored_policy` + `evaluate_single_policy`:

```
gather_evidence(delegations, issuance, expected_anchors, source) -> Evidence:
    for (policy, pinning) in delegations + [issuance]:
        bind_pins(policy, pinning)      # expand graph -> sorted prefix multiset -> zip with pinning.pins -> per-prefix cursor
    group all bound SAIDs by chain      # a bare SAID needs its leaf's prefix to know which chain it's on
    walk each chain ONCE                 # register its SAIDs up front; read them out of the verification token
    set expected_anchors as the issuance cursor's required-anchor set
                                         # every kel leaf under the issuer's governance is an anchoring leaf; other cursors get {}
    return Evidence { per-policy cursors (issuance cursor carries required-anchor set), one token per chain }

# Orchestrator: build the hop policies + issuer iel, gather ONCE (the only walking), then fold
# the delegation path [P0 .. Pn] into one conjunction of single-policy evaluations over that
# evidence. Linkage: hop k's policy is del(P_{k-1}), CONSTRUCTED from the prefix the prior hop
# established. Anchor checked ONLY on the terminal hop — and not here: gather set it on the issuance
# cursor, satisfies_kel confirms it off that cursor.
evaluate_anchored_policy(control_policy, delegation_path, issuance_pinning, expected_anchors, source, required_tier) -> bool:
    if delegation_path is empty: return false
    issuer = delegation_path[last].prefix
    issuer_iel = parse_policy("iel(" + issuer + ")")
    delegations = [(control_policy, delegation_path[0].pinning)]
    for k in 1 .. len(delegation_path):
        hop = parse_policy("del(" + delegation_path[k-1].prefix + ")")   # linkage: prefix the prior hop established
        delegations.append((hop, delegation_path[k].pinning))
    evidence = gather_evidence(delegations, (issuer_iel, issuance_pinning), expected_anchors, source)

    if not evaluate_single_policy(control_policy, evidence, Some(delegation_path[0].prefix), required_tier): return false
    for k in 1 .. len(delegation_path):
        hop = delegations[k].policy
        if not evaluate_single_policy(hop, evidence, Some(delegation_path[k].prefix), required_tier): return false
    return evaluate_single_policy(issuer_iel, evidence, None, required_tier)

evaluate_single_policy(policy, evidence, delegate, required_tier) -> bool:
    pins = evidence.cursor_for(policy.said)
    return eval_expr(policy.expr, pins, evidence, delegate, required_tier)

# Leaves take the NEXT pin for their prefix and consult `evidence` (the chain's token);
# composers aggregate. A prefix reached k times reads its k-th slot (occurrences ordered
# by traversal); the walk is exhaustive so that ordering holds. No chain walking here —
# every log was walked once in gather. `bind_pins` (in gather) is the only place slot
# order matters.
eval_expr(expr, pins, evidence, delegate, required_tier) -> bool:
    match expr:
        kel(prefix) => pins.take(prefix) is Some(prior) ? satisfies_kel(prior, prefix, pins.required_anchors(), evidence, required_tier) : false
        iel(prefix) => pins.take(prefix) is Some(ev)    ? satisfies_iel(ev, prefix, pins, evidence, delegate, required_tier) : false
        del(prefix) => pins.take(prefix) is Some(ev)    ? satisfies_del(ev, prefix, evidence, delegate) : false
        pol(said)   => eval_expr(parse_dsl(sadd.fetch(said).content).expr,
                                 pins, evidence, delegate, required_tier)
        thr(M, ss)  => count(eval_expr(s, pins, evidence, delegate, required_tier) for s in ss) >= M
        wgt(M, ws)  => sum(w for (s, w) in ws if eval_expr(s, pins, evidence, delegate, required_tier)) >= M

# kel: `prior` is the event before the anchoring event; S is its child (S.previous ==
# prior), which dodges the SAID cycle. The anchor requirement comes from the cursor
# (expected_anchors under the issuer's governance, {} elsewhere). iel: the pin is an
# IEL event (not an anchoring event, so cycle-free); recurse into its governance — the credential
# anchor is checked at the terminal kel leaves the recursion reaches. del: the pin is the
# DELEGATING IEL's own event; confirm the delegate is in its delegated set — no governance
# recursion (the delegate's governance / the credential anchor ride in a separate issuance
# pinning). All chains were walked in gather per the trust-boundary principle; pinning names the
# chain position so no search.

satisfies_kel(prior, leaf_prefix, required, evidence, required_tier):
    S = evidence.anchoring_child(leaf_prefix, prior)     # child where S.previous == prior, verified in gather
    # `required` is the cursor's set: expected_anchors under the issuer's governance, {} elsewhere
    return S.prefix == leaf_prefix
        AND S.tier >= required_tier
        AND required.is_subset(S.anchors)

satisfies_iel(iel_event, leaf_prefix, pins, evidence, delegate, required_tier):
    E = evidence.iel_event(leaf_prefix, iel_event)       # the IEL event itself, verified in gather
    return E.prefix == leaf_prefix
        AND eval_expr(parse_dsl(sadd.fetch(E.governance).content).expr,
                      pins, evidence, delegate, required_tier)

satisfies_del(iel_event, leaf_prefix, evidence, delegate):
    if delegate is None: return false                   # no identifier to test membership against
    E = evidence.iel_event(leaf_prefix, iel_event)       # the DELEGATING IEL's own event, verified in gather
    return E.prefix == leaf_prefix
        AND E.delegated_set_contains(delegate)
```

**Semantics notes:**

- **Pinning context propagates uniformly.** A `pol(said)` recursion — and an `iel` governance recursion — uses the same `pins` cursor, `evidence`, `delegate`, and `required_tier` as the outer evaluation. The credential-anchor requirement rides on the `pins` cursor itself (gather set it on the issuance cursor, empty on the others), so it propagates with that recursion to every kel leaf reached under the issuer's governance — and, being cursor-scoped rather than chain-scoped, never leaks onto a control-policy kel leaf that names the same chain. The whole expanded graph evaluates against one evidence set, each occurrence consuming its own slot in traversal order. A `del` leaf does not recurse: it consumes its one slot (the delegating IEL's event), tests delegate membership, and stops — the delegate's governance and the credential anchor are proven by a separate issuance pinning, not this cursor.
- **The SAID cycle, and why kel prefixes pin the *prior* event.** A SAID is the hash of the SAD with its own said-field zeroed, so it depends on every other field. The event that anchors credential `C` lists `said(C)` in its `anchors`; `C` commits to the Pinning (`said(P)`); `P` lists the pinned event's SAID. Pinning the anchoring event directly would close the loop `said(anchor) → said(C) → said(P) → said(anchor)` — unconstructable. So a kel prefix pins the event *just prior* and the verifier rederives the anchoring child. iel/del prefixes are cycle-free: they pin governance/delegation IEL events, which never carry the credential anchor. This is orthogonal to the sorted-multiset slotting, which only decides slot order; avoiding a second walk of a shared log is handled by gather locating all of that log's pinned SAIDs in one verified walk (supplied up front, reported found in the walk's token), not by the wire format.
- **`pol(said)` reference cycles are structurally impossible.** Content-addressed references can't form a cycle without a Blake3-256 collision (two Policy SADs mutually containing each other's SAIDs). No runtime cycle check needed.
- **Depth bound.** Implementations should impose a soft depth limit on `pol()` recursion (e.g., 16 levels) and deny on exceeding — implementation concern, out of scope here.
- **Tier check is in the leaf helpers, not the composers.** A kel prefix's `satisfies_kel` rejects an anchoring event hosted below `required_tier`; the tier requirement propagates unchanged through iel/del governance recursion to the terminal kel leaves. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized expression kinds → deny.** Forward-compatibility: older verifiers encountering newer DSL primitives return unsatisfied for that sub-expression; composer aggregation propagates this as a clean deny rather than a verification crash.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

- **IEL `Evl` / `Dec`** — gated by `governance`
- **IEL `Del` / `Rsc`** — gated by `delegation`
- **SEL `Est` / `Ixn` / `Evl` / `Rpr` / `Dec`** — gated by `governance`
- **Application-defined gates** — credentials, signed requests, etc. — gated by application-specific policy references

## Open items

1. **Verifier evaluation algorithm.** Recursion semantics (`iel(P)` evaluating against P's own policy, which may itself contain `iel(...)`), cycle detection, depth limits, caching strategies. Belongs in implementation specs once `lib/vdti` planning advances.

2. **Extension points.** The DSL is closed at the primitive level (6 primitives — leaves, composers). Future primitives (new chain types; new leaf semantics) would require DSL extension. The forward-compat deny rule (§Verifier behavior) makes additions soft-compatible — old verifiers safely deny on unrecognized expressions.

## Forward-refs

- [`event-logs/iel/`](event-logs/iel/) — IEL primitive (subsequent sub-issue); references this doc for governance / delegation policy evaluation
- [`event-logs/sel/`](event-logs/sel/) — SEL primitive (subsequent sub-issue); references this doc for SEL governance
- `lib/vdti` — verifier implementation; evaluates DSL expressions per this spec
