# Policy DSL

Canonical specification of vdti's policy DSL — the expression language used to encode authorization rules across the event-log primitives.

A **policy** is a [SAD](sad/sad.md) whose content is a DSL expression. The IEL primitive references policies (governance, delegation, and authentication); the SEL primitive references policies (governance and operation); applications reference policies for their own authorization needs. The DSL is the language; Policy SADs are the storage format; the verifier evaluates DSL expressions against signed requests and the relevant chain state.

This doc states the surface (the primitives that make up the DSL), their semantics, and how composition works. It does not enumerate per-primitive doctrine (which lives in [`event-logs/event-shape.md`](event-logs/event-shape.md), the per-primitive specs, and [`../../protocol-doctrine.md`](../../protocol-doctrine.md)) and does not specify the verifier implementation algorithm (which lives in `lib/vdti` planning material).

## Where policies appear

Policies are referenced by Policy SAD SAIDs from chain-event fields:

- **IEL `governance`** (required at inception; evolved via `Evl`) — gates IEL self-mutation events (key rotation, policy/roster changes, decommission).
- **IEL `authentication`** (required at inception; evolved via `Evl`) — the entity's act-as policy: what every `iel(prefix)` leaf (and each `mem` member) evaluates against. Outward-facing — it never gates the IEL's own chain events.
- **IEL `delegation`** (optional at inception; evolved via `Evl`) — gates IEL delegation events (`Del` / `Rsc`).
- **SEL `governance`** (declared at SEL `Icp`; evolved via `Evl`) — gates SEL events (`Evl` / `Rpr` / `Dec`).
- **SEL `operation`** (declared at SEL `Icp`; evolved via `Evl`) — gates SEL operational events (`Est` / `Ixn`).
- **Application-defined policy references** — applications may attach policy SAIDs to their own data structures (credentials, signed requests, custody SADs) following the same pattern.

An IEL's three policies — `governance` / `authentication` / `delegation` — are further constrained in *what they may contain* by whether the IEL is **aggregate** or **singleton**; see [IEL policy structure — aggregate vs. singleton](#iel-policy-structure--aggregate-vs-singleton).

In each case the field holds a `Digest256` pointing at a Policy SAD. The verifier dereferences, parses the DSL expression, and evaluates it.

## The DSL surface — 8 primitives

```
kel(prefix)        iel(prefix)        pol(said)
mem(group)   mem(prefix, group)   del(prefix, N)
thr(M, [...])      wgt(M, [...])      and([...])
```

Two chain-state **leaves** (`kel`, `iel`), one policy-reference **leaf** (`pol`), two
**bracket-only** forms — a **membership array** (`mem`) and a **delegation placeholder** (`del`)
— and three **composers** (`thr`, `wgt`, `and`). Neither bracket-only form is a leaf:

- `mem(group)` / `mem(prefix, group)` is an **array value** — it names a *`group`* of a
  membership roster and resolves to one `iel(member_i)` leaf per member of that group. The
  **two-arg** form names a *foreign* IEL `prefix`'s roster; the **one-arg** form names the
  **host** IEL's own roster (the prefix is implicit — the enclosing `iel(X)` descent supplies it),
  and is the only form an IEL's own three policies may use. It flattens in place inside a
  composer's `[...]`.
- `del(prefix, N)` is a **non-enumerable placeholder** — it names a *delegating* IEL `prefix` and
  a maximum delegation **depth** `N` (a natural number ≥ 1, counting hops; `del(X)` is sugar for
  `del(X, 1)` = direct delegate). It is **never expanded** (a delegator's delegated set is
  unbounded and delegate-side, so the verifier cannot materialize it); instead it is matched by
  the **distinct presented issuers** that self-traverse up to `prefix` within `N` hops (see
  [`del`](#delprefix-n--delegation-placeholder-self-traversing) and *Policies and Pinnings*). `del(X)` is
  not the same as naming `X`: it authorizes `X`'s *delegates*, not `X` itself.

Both `mem` and `del` are legal only **inside a composer's `[...]`**, never as a standalone
`expr`. The `[...]` is a concat container, so member-arrays, delegation placeholders, and single
expressions mix freely (`[mem(org, staff), kel(K)]` = org's staff members followed by `kel(K)`).
Members are IELs (individuals are IELs; devices are KELs), so each flattened `mem` member
authenticates via their own authentication policy (`iel(mi)`), while the referencing policy
composes over them at the threshold/weights it chooses (see *Leaf semantics*). The grammar:

```
expr      ::= leaf | composer
leaf      ::= kel(prefix) | iel(prefix) | pol(said)
bracketed ::= mem(group)                    # host IEL's own `group` roster (one-arg; prefix implicit): flattens to iel(member) leaves
            | mem(prefix, group)            # foreign IEL prefix's `group` roster: flattens to iel(member) leaves
            | del(prefix, N)                # delegation placeholder: never expanded; matched by distinct presented issuers
composer  ::= thr(M, [elem, ...]) | wgt(M, [([wgt_elem, ...], w), ...]) | and([expr, ...])
elem      ::= expr | bracketed              # a bracketed form appears only here; mem flattens its members in place
wgt_elem  ::= kel(prefix) | iel(prefix) | mem(group) | mem(prefix, group) | del(prefix, N)   # wgt subjects are membership-style ONLY — no pol, no composer (NEW-E)
```

`mem` and `del` appear only as an `elem` (inside `[...]`), never as a standalone `expr`. Every
counting composer's threshold is `M ≥ 1` — a zero threshold is satisfied by the empty set (a no-op
gate), so the parser rejects `M = 0`. `and([expr, ...])` is the **conjunction** composer — no
threshold (it is all-of), but its children are full `expr`s (a bracketed `mem` / `del` must be
wrapped in a `thr` / `wgt` first) and it requires **≥ 2** of them (a one-child `and` is just the
child; an empty `and([])` is a vacuous no-op gate, rejected); see
[`and`](#andexpr----conjunction-separation-of-duties). A `wgt` entry's subject is a bracketed
array `[wgt_elem, ...]` paired with a weight `w` that every one of its flattened children carries,
**but `wgt` subjects are restricted to the membership-style forms `kel` / `iel` / `mem` / `del`** —
**no `pol`, no composer** (NEW-E). A composer or `pol` subject would let one weight spread per
*credited prefix* across a nested set (threshold-easing), whereas these four credit a clear
membership-style set; the parser **rejects** a composer/`pol` `wgt` subject (fail-secure — see
*Composition semantics*). So `([mem(group)], w)` weights each member of that group at `w`, and a
single leaf is just the one-element case `([kel(K)], w)`. The bracket carries no bloc semantics:
`([a, b], w)` desugars losslessly to `(a, w), (b, w)`, so the array is purely a concise way to
attach one weight to several subjects. Every well-formed policy is built from these primitives.

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
by a pinned slot (see [`del`](#delprefix-n--delegation-placeholder-self-traversing) and *Policies and
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
  An anchor on a divergent or later-archived branch is invalid (see [`kel`](#kelprefix--kel-key-match-tier-agnostic)).
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

#### Rust

These are suitable Rust shapes. `Policy` carries a recursive `PolicyExpr` so the DSL grammar (nesting, `pol(said)`) maps directly onto the data structure. `Prefix` and `Said` are distinct newtypes over `Digest256` — a chain identifier vs. a point-in-time event SAID — so the two never silently interchange (see *Verifier behavior*).

```rust
pub struct Prefix(Digest256);             // chain identifier (entity / log)
pub struct Said(Digest256);               // SAID of a specific event or SAD (point-in-time / ordering)

pub enum PolicyExpr {
    Kel(Prefix),                          // chain prefix — device key (tier-agnostic; required_tier picks the role)
    Iel(Prefix),                          // chain prefix — IEL authentication
    Mem(Option<Prefix>, String),          // (roster owner, group label ^[a-z_-]{1,16}$); None = own/host-implicit (one-arg mem(group)), Some(p) = foreign (two-arg mem(p, group)); roster array — only valid as a composer element (inside [...]), flattens in place
    Del(Prefix, u32),                     // (delegator IEL prefix, max delegation depth N ≥ 1 in hops); placeholder — only valid as a composer element, never expanded
    Pol(Said),                            // nested Policy SAD SAID
    Thr(u64, Vec<PolicyExpr>),            // threshold M ≥ 1, sub-expressions
    Wgt(u64, Vec<(PolicyExpr, u32)>),     // threshold M ≥ 1; (sub, weight) pairs. Each sub is membership-style ONLY — kel/iel/mem/del, no pol/composer (NEW-E). Source brackets desugar to per-element pairs (each element carries w); a Mem sub expands to per-member (iel, w) at flatten
    And(Vec<PolicyExpr>),                 // conjunction — satisfied iff EVERY child satisfied; ≥ 2 children (separation of duties). Children are full exprs, never bare mem/del
}

pub struct Policy {
    said: Said,
    expr: PolicyExpr,
}
// Withdrawal authority and immunity are NOT properties of a generic Policy — they live on the
// CREDENTIAL (see §Withdrawal): an optional `withdrawal: Option<String>` DSL field and an
// `immune: bool` flag. A bare Policy carries no withdrawal state.

pub struct Pinning {
    said: Said,
    pins: Vec<Option<Said>>,              // one per prefix occurrence, in the verifier's pre-order walk order
}
```

## API Surface

The public evaluation entry points are `evaluate_anchored_policy` (anchored validity of a credential — reads chains via the verification walk) and `evaluate_current_policy` (live challenge-response control). Both run their leaf checks **inline on the verifier's verification walk** (`source`) — the single paged pass each referenced log gets for end-verifiability — and both resolve `del(prefix, N)` by **self-traversal** (no delegation pin: the candidate walks *up* its own delegation chain to the named delegator). There is no separate pure bind phase and no evidence-gathering walk: pins are consumed positionally as the one walk descends (see *Pinning*). `evaluate_single_policy` is the internal pin-walk helper for a del-free sub-policy (the issuer's authentication during the anchor check).

```rust
// Hard cap on the number of caller-supplied items a verifier will consider in one evaluation:
// presented issuers (anchored mode), and BOTH claimed delegates and presented attestations (current
// mode — NEW-A; each kel(K) leaf verifies against every matching attestation, so the set is an
// amplifier). Both entry points refuse > MAX_PRESENTED up front, at the trust boundary, before any
// chain work — an unbounded presented set cannot amplify cost. See §Boundedness, NEW-5, NEW-A.
const MAX_PRESENTED: usize = 128;

// Proof-of-verification token for a policy evaluation (NEW-F / Q3). It CANNOT be constructed
// directly — the ONLY way to obtain one is to run a policy verifier (`evaluate_anchored_policy` /
// `evaluate_current_policy`) to a SATISFIED result. The token BINDS the evaluated policy's SAID
// (both modes) and, in current mode, the `challenge` digest (A) into its own content/SAID, so
// possession PROVES that THE BOUND policy was satisfied against verified chain state — not merely
// that SOME policy passed: the credited parties, the SADs proven anchored, the marker state
// snapshot(s) the evaluation fixed, the policy SAID, and the challenge all ride in the token, so a
// downstream consumer reads data-AS-VERIFIED for the SPECIFIC policy/challenge — no re-fetch, no
// TOCTOU, no policy-confusion. A function taking `&PolicyVerification` is compiler-guaranteed its
// policy already passed. Fields are PRIVATE with NO public constructor; the verifier is the only
// builder. Verify-before-use is type-enforced FROM THE POLICY TOKEN ONWARD; making the verifier
// also CONSUME the underlying chain verification tokens (`IelVerification` / `KelVerification`) — so
// the chain -> policy -> authorize hand-off is token-enforced end to end — is the planned Phase-3
// token-architecture rewrite (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`); the
// current `source`-based walk is provisional pending it. (Mirrors the kels chain-verifier token
// pattern — `KelVerifier::into_verification()` -> `KelVerification`, and its `prefix()` context
// binding — NOT kels' submit-handler `AnchorEvaluation` / `PolicyChecker` deferral surface, which
// vdti's end-verification path does not need.)
pub struct PolicyVerification {
    said: Said,                              // content digest of the verified result (equal SAID ⇒ same result)
    policy_said: Said,                       // SAID of the evaluated policy — binds the token to THIS policy (A)
    challenge: Option<Digest256>,            // challenge digest bound in current mode; None in anchored mode (A)
    credited: HashSet<Prefix>,               // the distinct parties that satisfied the policy
    anchored_saids: BTreeSet<Said>,          // SADs proven anchored on the surviving branch (anchored mode; empty in current mode)
    snapshots: Vec<IelStateSnapshot>,        // the Evl/Icp-marker state snapshot(s) the walk reconstructed (NEW-B); provisional shape pending event-shape.md
}

impl PolicyVerification {
    pub fn credited(&self) -> &HashSet<Prefix> { &self.credited }        // who satisfied the policy
    pub fn is_said_anchored(&self, said: &Said) -> bool { self.anchored_saids.contains(said) }
    pub fn said(&self) -> &Said { &self.said }
    pub fn policy_said(&self) -> &Said { &self.policy_said }             // the policy this token proves (A)
    pub fn challenge(&self) -> Option<&Digest256> { self.challenge.as_ref() }  // bound challenge, current mode (A)
    // `new` is crate-private (no public constructor) — verifier-only construction is the whole
    // guarantee. Derives the content SAID over the verified result INCLUDING `policy_said` and
    // `challenge` (A), so an equal SAID means the same policy + challenge + credited set + anchored
    // SADs + snapshot(s); the token cannot be re-pointed at a different policy without changing its SAID.
    fn new(policy_said: Said, challenge: Option<Digest256>, credited: HashSet<Prefix>,
           anchored_saids: BTreeSet<Said>, snapshots: Vec<IelStateSnapshot>) -> Self {
        let mut token = Self {
            said: Said::placeholder(), policy_said, challenge, credited, anchored_saids, snapshots,
        };
        token.said = token.derive_said();    // SelfAddressed — bind the SAID over the fields above
        token
    }
}

// Anchored validity (public entry) — is `cred` validly issued by enough recognized issuers and
// not withdrawn? The credential NAMES its issuers and carries one anchor pinning per issuer; it
// carries NO delegation pins. Each presented issuer (a) self-traverses its own delegation chain
// to show it is a delegate of some del(prefix, N) named in `issuance_policy`, within N hops, every
// hop authorized + consented + un-rescinded to the delegator's tip; and (b) proves, via its anchor
// pinning, that the credential is anchored on its authentication at `required_tier`, on the
// surviving branch. The issuance policy's composers count DISTINCT contributing issuers per del
// placeholder. Self-contained: builds each issuer's `iel` policy internally, walks delegation
// chains + anchor pinnings inline on `source`, then runs the withdrawal scan.
//
//  issuers          presented issuers + their anchor pinnings. The verifier asserts (NEW-D, inside,
//                   at the trust boundary) that the presented prefixes equal `committed_issuers`
//                   before crediting any of them — the issuer<->content<->anchor binding never
//                   depends on caller bookkeeping. (INTERIM: Phase 3 takes `&Credential` and reads
//                   the committed set INTERNALLY, dissolving both this scaffolding and the assert — see NEW-D.)
//  committed_issuers the issuer set the credential COMMITS to, read from the SAID-verified
//                   credential (content-addressed, trusted). The verifier compares the presented
//                   `issuers` prefixes against this and refuses on mismatch (NEW-D); only then does it
//                   credit. INTERIM scaffolding only: it is a separate arg until the Phase-3
//                   credential-input model (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`)
//                   takes a single `&Credential` and reads `committed` internally — after which there
//                   is no caller-supplied set to compare and the equality assert disappears (NEW-D dissolved).
//  expected_anchors (SAID, minimum-tier) pairs each contributing issuer's anchoring event must
//                   host: the credential SAID, plus any co-anchored SADs, each with its tier floor.
//  withdrawal,      the credential's withdrawal config (see Withdrawal). immune ⇒ skip the
//  immune           withdrawal scan ONLY (the delegation rescission walk to tip still always runs);
//                   Some(expr) ⇒ hard scan against expr; None ⇒ soft per-contribution scan against
//                   each issuer's authentication threshold.
//  max_depth        the always-passed safety cap on every recursion/walk depth — delegation hops
//                   (sourced from the del placeholder's N), pol/iel nesting (a sensible default,
//                   e.g. 16). Exceeding it denies (fail-secure).
//
// Returns Err(PolicyError) on structural/source failure (malformed input, fetch failure, leftover
// pins, max_depth breach, presented != committed); Ok(None) on a clean unsatisfied result; and
// Ok(Some(PolicyVerification)) on satisfaction — the token carries the credited issuer set, the
// anchored credential SAID(s), and the marker snapshot(s) the walk fixed. Verify-before-use is
// type-enforced FROM THE POLICY TOKEN ONWARD; having the verifier also CONSUME the underlying chain
// verification tokens (so the chain -> policy hand-off is token-enforced too) is the planned Phase-3
// token-architecture rewrite (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`) — the
// current `source`-based walk is provisional pending it.
//
// NOTE (E1, Phase 3): today a single issuer's chain-verification failure propagates as a global Err
// (the `?` on `evaluate_single_policy` below). Phase 3 SOFTENS this — a single unverifiable issuer
// becomes UNCREDITED (not a global error) and the issuance threshold runs over the credited set;
// only STRUCTURAL failures (leftover pins, max_depth, malformed input, a NEW-B roster desync) stay
// hard `Err`. Fail-secure: softening can only SHRINK the credited set, never validate spuriously.
pub fn evaluate_anchored_policy(
    issuance_policy: &Policy,
    issuers: &[(Prefix, &Pinning)],
    committed_issuers: &HashSet<Prefix>,     // from the SAID-verified credential (NEW-D)
    expected_anchors: &HashSet<(Said, Tier)>,
    withdrawal: Option<&Policy>,
    immune: bool,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError>;

// Single-policy pin-walk (internal) — tree walk over ONE del-free policy (the issuer's
// authentication during the anchor check, or a nested pol()), consuming `pinning.pins`
// positionally in pre-order walk order. Each non-del leaf takes the next pin and reads that event
// inline from `source`; composers aggregate. `self_context` (a `HostContext`) resolves one-arg
// `mem(group)` inside an aggregate member's authentication — it carries the enclosing `iel()`
// descent's prefix AND its roster source (None at the top; set to `{X, AtMarker(snapshot)}` when
// recursing into iel(X)'s authentication, so the member roster is read from the SAME frozen marker
// snapshot the descent fixed, NEW-B). `expected_anchors` is the
// credential-anchor requirement scoped to this walk (the issuer's authentication carries it; a
// nested pol inherits it). Bounded by `max_depth`. Returns Ok(None) when this issuer's
// authentication is unsatisfied; Ok(Some(token)) — carrying the anchored SAD(s) proven on this walk
// and the Evl/Icp-marker snapshot it reconstructed (folded into the caller's token) — on success;
// Err on a structural/source failure (leftover pins, fetch failure, max_depth breach).
fn evaluate_single_policy(
    policy: &Policy,
    pinning: &Pinning,
    expected_anchors: &HashSet<(Said, Tier)>,
    self_context: Option<HostContext>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError>;
```

```rust
// Current-state control (public entry) — challenge-response / fresh-control. Establishes who
// CURRENTLY controls `policy` and confirms they signed `challenge`. Evaluated at the chain TIP (no
// pinning — tip state is implied; no anchors — nothing is proven anchored here). The bearer
// presents attestations over `challenge`; each is a signer KEL prefix + a primary signature, plus
// optionally a recovery signature for tier-3 dual-sig contexts. Leaf semantics in current mode:
//   - kel(K)         satisfied by an attestation whose signer == K, valid against K's CURRENT
//                    signing key (and recovery key, when required) at K's tip.
//   - iel(X) / mem   satisfied by attestation(s) meeting X's authentication at its tip (recurse;
//                    one-arg mem(group) resolves to the enclosing iel descent's roster, as in the
//                    anchored walk). X is NAMED in the policy — no claim needed; crediting is by the
//                    LEAF's prefix, so thr(2, [iel(A), iel(B)]) counts both identities even under
//                    one controlling key.
//   - del(X, N)      the bearer NAMES the delegate IEL D it acts as (presented up front in
//                    `named_delegates`, capped at 128 — del is non-enumerable and there is no
//                    credential here to carry the name, and there is NO del-pin); credit each
//                    DISTINCT named D whose attestations meet D's authentication at tip AND that
//                    self-traverses up to X within N hops (delegation valid to tip, F).
// `required_tier` here is a requirement on the ATTESTATION SHAPE (which signatures must be present
// and valid — primary alone vs. primary+recovery), not an anchoring-event tier; see *Leaf
// semantics* (precise tier→shape mapping in the deviations log). `challenge` must be unpredictable,
// single-use, and context-bound (see *Verifier behavior — challenge binding*).
//
// Both `attestations` and `named_delegates` are refused up front if longer than MAX_PRESENTED (128)
// (NEW-A / NEW-5) — each kel(K) leaf signature-verifies against every matching attestation, so an
// unbounded attestation set is a crypto-verify amplifier; the cap stops it before any chain work.
// Returns Err(PolicyError) on structural/source failure (over-cap input, fetch failure, max_depth
// breach); Ok(None) on a clean unsatisfied result; Ok(Some(PolicyVerification)) on satisfaction —
// the token carries the credited prefix set (anchored_saids empty, no snapshot: current mode reads
// the tip live and pins no marker).
pub struct Attestation {
    signer: Prefix,                          // signer's KEL prefix
    signature: Signature,                    // signature by current signing key
    recovery_signature: Option<Signature>,   // signature by current recovery key (tier-3)
}

pub fn evaluate_current_policy(
    policy: &Policy,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],              // claimed delegate IELs for del(X, N) leaves (the live
                                             // party names the delegate it acts as); capped at 128,
                                             // empty when the policy has no del. See NEW-3 / NEW-5.
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError>;
```

Both entry points are **policy verifiers**: a satisfied evaluation yields a `PolicyVerification` proof token, not a bare `true`. `evaluate_anchored_policy` returns `Ok(Some(token))` iff the presented issuers (asserted equal to the credential's committed set, NEW-D) satisfy `issuance_policy` — each self-traversing to a named delegator within depth and anchoring the credential on its authentication at the required tier on the surviving branch — AND no satisfying withdrawal anchor was found (see *Withdrawal*); the token carries the credited issuer set, the anchored credential SAID(s), and the marker snapshot(s) the walk fixed. `evaluate_current_policy` returns `Ok(Some(token))` iff the attestations over `challenge` cover `policy`'s leaves at current chain state with the required attestation shape; the token carries the credited prefixes (no anchored SAIDs, no snapshot — current mode is tip-live). Both return `Ok(None)` for a clean unsatisfied — including an unknown primitive, which fails the **whole** policy closed (see *Verifier behavior*); `Err(_)` for malformed inputs / fetch failures, including leftover pins (more pins than the policy has occurrences), a presented≠committed mismatch, an over-cap presented set, or a `max_depth` breach. Token-existence *is* the proof of satisfaction — a caller holding a `PolicyVerification` cannot have reached it on an unsatisfied policy.

The auth flow typically calls both kinds of check. `evaluate_anchored_policy` is self-contained: it confirms each named issuer is a current delegate by **self-traversing that issuer's own delegation chain** up to a delegator named by the issuance policy (no cred-supplied path — the chain self-records the linkage; see *Delegation handshake*), proves each issuer's anchor through its `iel` (the **anchor pinning**), counts distinct issuers against the issuance policy's thresholds, then runs the withdrawal scan. The verification walk pages each referenced log once, so a chain reached by several anchor pinnings or self-traversals is checked inline in that one pass. The **current-state** check (`evaluate_current_policy`) validates that the bearer presently controls the policy the cred names — it matches live attestations over a fresh challenge against the policy's leaves at the chain tip (`del` leaves self-traverse from a **named delegate** the bearer presents, as in the anchored flow).

### Policies and Pinnings

#### Use case

Let's say we declare an **issuance policy** that governs which credentials a resource will
accept — it names the IELs whose **delegates** may issue credentials bound to user identities. A
credential SAID must be anchored by a recognized issuer for the credential to be valid.

The credential issuance policy the server is configured with may be:

```
thr(1, [del(iel_prefix_1, 1), del(iel_prefix_2, 1), del(iel_prefix_3, 1)])
```

which says that prefixes 1 through 3 may delegate to issuers, and a single delegate (at depth 1 —
a direct delegate) of any of them satisfies the policy.

The credential **names its issuer(s)** and carries **one anchor pinning per issuer**. It carries
**no delegation pinning**: delegation is proven by the verifier self-traversing the issuer's own
delegation chain, which self-records the link to its delegator. Only the anchor needs a pinning.

#### Delegation handshake — self-recording

A delegate `D` is born under delegator `X` and **self-records** the link on its own chain, so the
verifier can walk *up* from `D` to `X` without enumerating `X`'s (unbounded, delegate-side)
delegated set:

- `D.Icp.delegating = X`'s **prefix**. `X`'s prefix is known a-priori (no SAID cycle) and
  participates in `D`'s prefix derivation, so `D`'s identity is cryptographically **bound to `X`**.
- A **serial-1 `Evl`, batched with the `Icp`**, evolves `delegating` to the **SAID of `X`'s `Del`
  event** (the event on `X`'s chain that lists `D`'s prefix — known only after `X.Del` exists, and
  still identifying `X` because the SAID resolves to an event on `X`'s chain). Reusing the
  privileged `Evl` avoids the IEL no-local-divergence break a content event would cause; the `Del`
  SAID is one of the things an `Evl` may change (alongside `governance` / `delegation`).

Two structural rules make the handshake unforgeable and keep it atomic (a merge-layer rule
parallel to the SEL `[Icp, Est]` pairing):

- `delegating`-as-SAID appears **only** on a serial-1 `Evl` that follows a `delegating`-`Icp`.
- A `delegating`-`Icp` **must** batch with that serial-1 `Evl` — the two land together or not at all.

Sequencing across the two chains needs **no cross-chain atomic transaction**: `X.Del` (listing
`D`'s prefix) lands first, then `D`'s atomic `[Icp, Evl]` batch references it. The verifier
**consistency-checks** that the serial-1 `Evl`'s `Del` SAID resolves to an event on the chain
`D.Icp.delegating` names.

Both the issuer set and the per-issuer anchor pinning ride on the credential. Say the credential
is issued by `dlg_prefix`, a direct delegate of `iel_prefix_2`, whose IEL authentication is
`kel(dlg_kel_prefix)`.

#### Self-traversing verification

The issuance policy names *delegators*, never their delegates, so the issuer — a delegate — is
**named on the credential**, not pinned into the issuance policy. The verifier confirms delegation
by self-traversal (walking *up* the issuer's own chain) and proves the anchor by a single pinning
rooted at the issuer's own IEL:

```
  issuance policy                              self-traversal (no pinning)
  ──────────────────────────────────────      ────────────────────────────
  thr(1)
  ├─ del(iel_prefix_1, 1)                      (not claimed)
  ├─ del(iel_prefix_2, 1)  ◀── dlg_prefix self-traverses 1 hop up to iel_prefix_2:
  │      dlg_prefix.Icp.delegating   == iel_prefix_2            (consent)
  │      dlg_prefix.Evl[1].delegating == said(iel_prefix_2.Del) (consent, the back-pointer)
  │      iel_prefix_2.Del lists dlg_prefix                      (authorization)
  │      no Rsc of dlg_prefix to iel_prefix_2's TIP            (F — always checked)
  └─ del(iel_prefix_3, 1)                      (not claimed)

  dlg_prefix (the issuer) is NAMED on the credential, not a pinned slot. Its anchor
  rides in a separate pinning, rooted at the issuer's own IEL so the anchoring KEL is
  bound to the delegated identity:

  iel(dlg_prefix)  (identity → authentication → anchor)  anchor pinning
  ─────────────────────────────────────────────────     ────────────────
  iel(dlg_prefix)                       ▷ slot 0  {dlg_iel_marker_said}
  └─ authentication kel(dlg_kel_prefix) ▷ slot 1  {dlg_kel_prior_kel_said}
        └─ prior event (surviving branch); its child anchors the credential at the required tier
```

**No issuance pinning.** The issuance policy's `del(iel_prefix_2, 1)` placeholder is **not
expanded** and pins nothing — the issuer is named, and the verifier confirms delegation by
self-traversing `dlg_prefix`'s own chain (above). The only pinning the credential carries is the
anchor pinning.

**Anchor pinning.** The issuer's IEL policy `iel(dlg_prefix)` walks to two slots in pre-order —
the issuer's `Evl`/`Icp` state-marker (the verifier reconstructs the snapshot that fixes which
authentication state applies) and, through that authentication `kel(dlg_kel_prefix)`, the KEL event
just *prior* to the anchoring event (the anchoring event commits to the credential, so its own SAID
is unconstructable here; see the SAID-cycle note):

```
{
    "said": "{anchor_pinning_said}",
    "pins": [
        "{dlg_iel_marker_said}",     // slot 0 — dlg_prefix state-marker fixing the authentication snapshot
        "{dlg_kel_prior_kel_said}"   // slot 1 — dlg_kel_prefix prior event; its surviving-branch child anchors the credential
    ]
}
```

(slots in pre-order walk order; per issuer there is one anchor pinning.)

**Verifying.** The credential is valid iff *both* hold:

- **Delegation (self-traversal)** — `dlg_prefix` self-traverses 1 hop up its own chain to
  `iel_prefix_2`: its `Icp.delegating` names `iel_prefix_2` and its serial-1 `Evl.delegating`
  names `said(iel_prefix_2.Del)`; the verifier direct-looks-up that `Del` (no enumeration),
  confirms it lists `dlg_prefix`, and walks `iel_prefix_2` to **tip** confirming no `Rsc` of
  `dlg_prefix` (F — always, even for an immune credential). One satisfied delegate clears the
  `thr(1, ...)`. Under `del(X, N)` with `N > 1` the verifier keeps walking up (`X`'s own
  delegator, …) until it reaches the named delegator within `N` hops or denies.
- **Anchor** — evaluating `iel(dlg_prefix)` against the anchor pinning, the `iel(dlg_prefix)`
  leaf reads its pinned `Evl`/`Icp` state-marker (reconstructing the snapshot that binds the issuer
  to its authentication `kel(dlg_kel_prefix)`) and recurses into that authentication policy; the
  `kel(dlg_kel_prefix)` leaf resolves the
  anchoring event `S` (`S.previous == dlg_kel_prior_kel_said`) **on the surviving branch** and
  checks `S` is at the required tier and anchors the credential SAID. Because the anchor is
  reached *through* the delegated issuer's IEL, the anchoring KEL is bound to the delegated
  identity rather than asserted by the credential.

For a multi-issuer policy (`thr(2, [del(A), del(B)])`), the credential names two distinct issuers,
each self-traversing to `A` or `B` and each carrying its own anchor pinning; the composer counts
**distinct issuers** (see *Leaf semantics → `del`*). Verification groups the pinned SAIDs (one
anchor pinning per issuer) by the log they fall on and checks each log's set inline in that log's
single paged verification walk: the SAIDs to check are the positions supplied up front, the walk
validates each event as it pages through, and the caller confirms every required SAID was reached.
So a chain reached on several paths is paged once, not repeatedly.

```rust
let iel_prefix_1 = Prefix::from_qb64("KAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")?;
let iel_prefix_2 = Prefix::from_qb64("KBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")?;
let iel_prefix_3 = Prefix::from_qb64("KCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")?;

let issuance_policy = parse_policy(&format!(
    "thr(1, [del({}, 1), del({}, 1), del({}, 1)])",
    iel_prefix_1, iel_prefix_2, iel_prefix_3
))?;

// The credential NAMES its issuers and carries one anchor pinning per issuer (no delegation
// pinning — delegation is self-traversed). Source the issuer set FROM THE CREDENTIAL, not from
// untrusted request input (the verifier is the trust boundary).
let issuers: Vec<(Prefix, &Pinning)> = cred
    .issuers()                                  // dlg_prefix: a delegate of iel_prefix_2, the anchor host
    .map(|i| (i.prefix, parse_pinning_sad(&sadd_fetch(&i.anchor_pinning_said)?)?))
    .collect::<Result<_, _>>()?;

// each required anchor names the minimum tier its hosting event must satisfy
let cred_anchor: HashSet<(Said, Tier)> = [(cred.said, Tier::One)].into_iter().collect();

// The issuer set the credential COMMITS to, read from the SAID-verified credential (NEW-D). The
// verifier asserts the presented `issuers` prefixes equal this INSIDE the call, at the trust
// boundary, before crediting — the equality is not the caller's to vouch for. (INTERIM: Phase 3
// passes the `&Credential` itself and reads `committed` internally, dissolving this separate arg.)
let committed: HashSet<Prefix> = cred.committed_issuers().into_iter().collect();

// One self-contained call: for each named issuer it self-traverses the issuer's own delegation
// chain up to a delegator named by the issuance policy (≤ N hops, bounded by max_depth), proves
// the issuer's anchor through its `iel` (the anchor pinning), counts distinct issuers against the
// issuance policy's thresholds, and runs the withdrawal scan. No cred-supplied delegation path.
// On success it returns Some(PolicyVerification) — the proof token downstream steps consume.
let verification = evaluate_anchored_policy(
    &issuance_policy,
    &issuers,
    &committed,                                  // NEW-D: asserted == presented, inside the verifier
    &cred_anchor,
    cred.withdrawal.as_deref().map(parse_policy).transpose()?.as_ref(),  // None = soft default
    cred.immune,
    source,
    Tier::One,
    16,                                          // max_depth (del's N bounds the delegation walk; this caps nesting)
)?;
```

> **TODO (pending [event-shape.md](event-logs/event-shape.md)).** The evaluation architecture below — credential-names-issuers + per-issuer anchor pinning, the self-traversing delegation walk (each issuer walks *up* its own chain via the serial-1 `Evl` back-pointer; `del` never expanded), pre-order pin slotting consumed inline on the one verification walk, `self`-context threading, distinct-issuer counting, and the supply-SAIDs-up-front / one-paged-walk-per-log / inline-check mechanism — is stable. What may still shift is the per-primitive **leaf field access** that depends on the settled event shapes: the kel anchor model and prior-event/SAID-cycle rederivation (`s.anchors`, `s.previous`), the surviving-branch resolution of the anchoring child (per `kel/reconciliation.md` / `merge.md`), the iel `governance` / `authentication` field names (`iel(X)` recurses into `authentication`; `governance` gates the IEL's own events), the self-recording delegation fields (`Icp.delegating` = delegator prefix; serial-1 `Evl.delegating` = the `Del`-event SAID; the `Del`/`Rsc` walk to tip), the membership **roster** field on the IEL that `mem(prefix, group)` resolves against (a roster-SAD SAID the IEL commits to — not yet in `event-shape.md`) and the composer-time flattening that expands `mem` elements into `iel(member)` leaves, and where `tier` lives on the event. Treat those specifics as provisional until `event-shape.md` lands.

Implementation:

```rust
// evaluate_anchored_policy is self-contained and runs inline on the verification walk — there is
// NO separate pure bind phase. Each presented issuer is checked two independent ways:
//   (a) ANCHOR — its anchor pinning proves the credential is anchored on the issuer's OWN
//       authentication (surviving branch, required tier), via `iel(issuer)`;
//   (b) DELEGATION — it self-traverses UP its own delegation chain to a delegator the issuance
//       policy names, within that placeholder's depth.
// The issuance policy's composers then count DISTINCT anchored issuers per `del(X, N)`. The
// issuer<->content<->anchor binding never depends on caller bookkeeping: the presented prefixes are
// asserted equal to the credential's COMMITTED issuer set (NEW-D) here, at the trust boundary,
// before any crediting (INTERIM — Phase 3 reads the committed set from a `&Credential` input and
// drops the assert). On satisfaction the verifier emits a PolicyVerification proof token, FOLDING
// the per-issuer PolicyVerification SUB-tokens it walked; having it ALSO consume the underlying
// chain verification tokens (verify-before-use chain -> policy too) is the Phase-3 rewrite.
pub fn evaluate_anchored_policy(
    issuance_policy: &Policy,
    issuers: &[(Prefix, &Pinning)],
    committed_issuers: &HashSet<Prefix>,
    expected_anchors: &HashSet<(Said, Tier)>,
    withdrawal: Option<&Policy>,
    immune: bool,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError> {
    if issuers.len() > MAX_PRESENTED {           // K ≤ 128 (NEW-5) — up-front trust-boundary pre-check,
        return Err(PolicyError::TooManyIssuers); // before the equality check; zero chain work done
    }
    // NEW-D: the presented prefixes MUST equal the credential's committed set, asserted HERE from
    // SAID-verified data — never trusted from caller bookkeeping. A mismatch is a structural failure.
    // INTERIM: Phase 3 (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`) takes a single
    // `&Credential` and reads `committed` internally, so there is no caller set to compare — this
    // whole check dissolves (NEW-D superseded). Kept until the token-architecture rewrite lands.
    let presented: HashSet<Prefix> = issuers.iter().map(|(p, _)| p.clone()).collect();
    if presented != *committed_issuers {
        return Err(PolicyError::IssuerSetMismatch);
    }
    if issuers.is_empty() {
        return Ok(None);              // no committed issuer — nothing to anchor or delegate-check
    }

    // (a) Anchor proof per issuer. `iel(issuer)` walks to the issuer's `Evl`/`Icp` state-marker and,
    // through its reconstructed authentication, the anchoring KEL(s); `expected_anchors` rides this walk so the credential
    // anchor is checked on the ISSUER'S authentication (surviving branch, required tier) — never on
    // a chain a `del` placeholder names. An issuer that anchors yields a per-issuer token (its
    // proven anchored SAD(s) + reconstructed marker snapshot); Ok(None) ⇒ not a contributor.
    let mut anchored: Vec<&Prefix> = Vec::new();
    let mut issuer_tokens: Vec<PolicyVerification> = Vec::new();
    for (issuer, anchor_pinning) in issuers {
        let issuer_iel = parse_policy(&format!("iel({})", issuer))?;
        if let Some(token) = evaluate_single_policy(&issuer_iel, anchor_pinning, expected_anchors,
                                                    None, source, required_tier, max_depth)? {
            anchored.push(issuer);
            issuer_tokens.push(token);
        }
    }

    // (b) + composition. Evaluate the issuance policy: each `del(X, N)` placeholder is matched by
    // the distinct anchored issuers that self-traverse up to `X` within `N` hops; composers count
    // DISTINCT issuer prefixes. An empty credited set is a clean unsatisfied (Ok(None)).
    let credited = issuance_credited(&issuance_policy.expr, &anchored, source, max_depth)?;
    if credited.is_empty() {
        return Ok(None);
    }

    // Withdrawal. `immune` skips THIS scan only — the F rescission tip-walk inside `self_traverses`
    // always ran. Otherwise scan to tip for a satisfying withdrawal anchor (soft per-contribution
    // default, or hard against `withdrawal`'s expr). See §Withdrawal.
    if !immune
        && is_withdrawn(expected_anchors, &anchored, withdrawal, source, required_tier, max_depth)?
    {
        return Ok(None);
    }

    // Satisfied. Build the proof token, CONSUMING the per-issuer PolicyVerification sub-tokens —
    // their anchored SADs and marker snapshots fold up, so possession of the result carries every
    // sub-walk's proven facts. (Consuming the underlying chain verification tokens themselves — so
    // the result proves every walked CHAIN verified, not just every sub-policy — is the Phase-3
    // token-architecture rewrite; the current `source`-based walk is provisional pending it.)
    let mut anchored_saids = BTreeSet::new();
    let mut snapshots = Vec::new();
    for t in issuer_tokens {                       // moves each sub-token (consumed, not borrowed)
        anchored_saids.extend(t.anchored_saids);
        snapshots.extend(t.snapshots);
    }
    // Bind the issuance policy's SAID (A); anchored mode has no challenge.
    Ok(Some(PolicyVerification::new(issuance_policy.said.clone(), None, credited, anchored_saids, snapshots)))
}

// Self-traversal: does `candidate` reach `delegator` walking UP its own delegation chain within
// `max_hops` hops? The credential carries no delegation path — each link self-records its parent,
// so the verifier reconstructs the chain from the candidate alone. At each hop:
//   - read the lower link's self-recorded `delegating` — its `Icp.delegating` (the parent prefix)
//     and its serial-1 `Evl.delegating` (the parent's `Del`-event SAID) — both CONSENT;
//   - direct-look-up that event on the parent's chain (no enumeration of any delegated set). It MUST
//     resolve to a `Del` event — `del_event` REJECTS any other kind. This matters because both `Del`
//     and `Rsc` carry a `delegated` prefix list (`Del` ADDS delegates, `Rsc` REMOVES them); reading
//     authorization off a `Rsc`'s removals would invert the check. Confirm the `Del` lists the lower
//     link in its ADDITIONS (AUTHORIZATION) and resolves to the consented parent prefix;
//   - walk the parent IEL to TIP confirming no `Rsc` of the lower link (F — ALWAYS, even when the
//     credential is immune; immune scopes to withdrawal only). The `Del`-kind constraint and this
//     tip-walk are independent: the former pins the back-pointer to an authorizing event, the latter
//     catches a later rescission. Defense in depth.
// Bounded by `min(max_hops, max_depth)`; reaching neither `delegator` nor a valid parent denies.
fn self_traverses(
    candidate: &Prefix,
    delegator: &Prefix,
    max_hops: u32,
    source: &impl EventSource,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    let mut lower = candidate.clone();
    for _hop in 0..max_hops.min(max_depth) {
        let parent = source.delegating_prefix(&lower)?;        // lower.Icp.delegating (consent)
        let del_said = source.delegating_del_said(&lower)?;    // lower.Evl[1].delegating (consent back-pointer)
        let del = source.del_event(&parent, &del_said)?;       // direct lookup; MUST be a `Del` (not `Rsc`)
        if del.host != parent || !del.lists(&lower) {          // authorization: the Del ADDS `lower`
            return Ok(false);
        }
        if source.rescinded_by_tip(&parent, &lower)? {         // F — walk parent to tip; any Rsc denies
            return Ok(false);
        }
        if parent == *delegator {
            return Ok(true);                                   // reached the named delegator in ≤ N hops
        }
        lower = parent;
    }
    Ok(false)                                                  // ran out of hops without reaching `delegator`
}

// eval_issuance walks the issuance policy and reports whether its threshold is met by DISTINCT
// recognized issuers. It returns satisfaction; the helper `issuance_credited` returns, per
// subexpression, the SET of distinct issuers that subexpression credits IF satisfied (else empty) —
// so a containing composer dedups by prefix when it unions children. An issuance policy accepts both
// DELEGATED issuers (`del(X, N)` — anchored issuers self-traversing up to `X` within `N`, delegation
// is for scaling) and DIRECT named issuers (`iel(X)` / `mem(prefix, group)` — anchored issuers
// matching the named prefix / the owner's `group` roster at its tip). `pol` recurses; `thr`/`wgt`/`and` compose
// (union / max-weight / conjunction); a bare `kel` credits nobody (issuers are IELs, not bare
// devices). `thr(M, …)` is met iff the child union holds ≥ M distinct issuers; `wgt` sums per-issuer
// weight (dedup-by-max, mirroring `mem` — weighted delegation composes identically).
fn eval_issuance(
    expr: &PolicyExpr,
    anchored: &[&Prefix],
    source: &impl EventSource,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    let credited = issuance_credited(expr, anchored, source, max_depth)?;
    Ok(!credited.is_empty())
}

// Returns the set of distinct issuers `expr` credits if satisfied, else the empty set. Issuance
// accepts DELEGATED (`del`) and DIRECT (`iel` / `mem`) issuers; `pol` recurses; `kel` credits nobody.
fn issuance_credited(
    expr: &PolicyExpr,
    anchored: &[&Prefix],
    source: &impl EventSource,
    max_depth: u32,
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // del(X, N): every anchored issuer self-traversing up to X within N hops. Never expanded.
        PolicyExpr::Del(delegator, n) => {
            let mut set = HashSet::new();
            for issuer in anchored {
                if self_traverses(issuer, delegator, *n, source, max_depth)? {
                    set.insert((*issuer).clone());
                }
            }
            Ok(set)
        }
        // iel(X): credit {X} iff X is a DIRECT named issuer — it anchored the credential itself (no
        // delegation hop), so X ∈ anchored.
        PolicyExpr::Iel(prefix) => Ok(if anchored.iter().any(|a| **a == *prefix) {
            HashSet::from([prefix.clone()])
        } else {
            HashSet::new()
        }),
        // mem(prefix, group): flatten to iel(member) and credit the anchored members of `prefix`'s
        // `group` ("any of X's executives may issue directly"). Roster resolved at the owner's TIP
        // (identity-current — the issuance policy is the resource's live config, unpinned). The
        // one-arg own-form mem(group) (Mem(None, _)) has NO host context in an issuance policy
        // (a general policy — `issuance_credited` threads no self-context and never descends an
        // `iel`), so it credits nobody (fail-secure).
        PolicyExpr::Mem(Some(prefix), group) => {
            let mut set = HashSet::new();
            for member in source.roster_members(prefix, group)? {
                if anchored.iter().any(|a| **a == member) {
                    set.insert(member);
                }
            }
            Ok(set)
        }
        PolicyExpr::Mem(None, _) => Ok(HashSet::new()),   // one-arg own-form — no host here
        // pol(said): recurse (pure factoring — propagate the nested credited set). Decrement depth.
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            issuance_credited(&nested.expr, anchored, source, max_depth - 1)
        }
        // thr(M, …): union the credited children; met iff ≥ M distinct issuers, then return the
        // union. Children recurse at `max_depth - 1` (NEW-C — decrement on every composer, matching
        // eval_expr / current_credited, so composer-tree depth is bounded too).
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for sub in subs {
                union.extend(issuance_credited(sub, anchored, source, max_depth - 1)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt(M, …): per-issuer weight, dedup-by-max across branches (mirrors `mem`; weighted
        // DELEGATION composes identically — an issuer matching several `del`/`mem` placeholders is
        // credited once at its MAX weight, distinct issuers summed); met iff the summed weight ≥ M.
        // Children recurse at `max_depth - 1` (NEW-C).
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (sub, w) in weighted {
                for p in issuance_credited(sub, anchored, source, max_depth - 1)? {
                    best.entry(p).and_modify(|cur| *cur = (*cur).max(*w)).or_insert(*w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and(…): conjunction — every child must credit ≥ 1 issuer; on success return the union, else
        // ∅ (separation of duties over issuers; distinct only over disjoint pools — see §`and`).
        // Children recurse at `max_depth - 1` (NEW-C).
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = issuance_credited(child, anchored, source, max_depth - 1)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // kel(K): a bare device is not an issuer unit (issuers are IELs; the distinct-issuer count is
        // over IEL prefixes) — credit nobody. Fail-secure clean line.
        PolicyExpr::Kel(_) => Ok(HashSet::new()),
    }
}

// Host context for resolving a one-arg `mem(group)` inside an `iel(X)` descent (NEW-B): the host
// prefix plus WHERE that host's roster is read. `AtMarker` pins the roster to the `iel(X)`
// `Evl`/`Icp` marker's reconstructed snapshot (FROZEN — reused, no second pin, closing the
// authentication-recent / roster-stale split that a free roster slot would open). `AtTip` reads the
// owner's LIVE roster (the current/issuance tip-live flows, and a foreign two-arg `mem`). A `None`
// `self_context` means no enclosing iel descent — a one-arg `mem(group)` there credits nobody
// (fail-secure). The struct carries the snapshot to the expansion site so `flatten` can reach it;
// the as-of-marker roster READ itself stays provisional (EventSource/pagination), like `snapshot_as_of`.
#[derive(Clone, Copy)]                 // all-reference fields — Copy, so it threads through the
struct HostContext<'a> {              // recursive composer arms (flatten + the child eval) freely
    prefix: &'a Prefix,
    roster: RosterSource<'a>,
}
#[derive(Clone, Copy)]
enum RosterSource<'a> {
    AtMarker(&'a IelStateSnapshot),   // roster frozen at the iel(X) Evl/Icp marker (NEW-B)
    AtTip,                            // owner's live roster (tip)
}

// `flatten` / `flatten_weighted` expand each `mem` element to `iel(member)` leaves in canonical
// order, reading the roster via `self_context`. A two-arg `mem(prefix, group)` ALWAYS reads
// `source.roster_members(prefix, group)` at the foreign owner's tip. A one-arg `mem(group)` reads
// the HOST's roster: `AtMarker(snap)` ⇒ `snap.roster` (the frozen marker snapshot, NEW-B); `AtTip`
// ⇒ `source.roster_members(host.prefix, group)`; `None` ⇒ credits nobody (no enclosing host).

// Single-policy pin-walk over ONE del-free policy (the issuer's authentication during the anchor
// check, or a nested `pol`). Consumes `pinning.pins` POSITIONALLY in pre-order walk order: a single
// cursor advances one slot per leaf the walk reaches. After the walk any LEFTOVER pins are a
// malformed pinning and deny (`Err`) — the issuer pinned more slots than the policy has occurrences.
// On satisfaction it emits a per-issuer PolicyVerification — the SAD(s) this walk proved anchored
// and the iel marker snapshot(s) it reconstructed — which the anchored entry point folds into its
// own token. Ok(None) ⇒ this issuer's authentication is unsatisfied.
fn evaluate_single_policy(
    policy: &Policy,
    pinning: &Pinning,
    expected_anchors: &HashSet<(Said, Tier)>,
    self_context: Option<HostContext>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError> {
    let mut cur = PinCursor::new(&pinning.pins);     // positional; `take_next()` advances one slot
    let credited = eval_expr(&policy.expr, &mut cur, expected_anchors, self_context,
                             source, required_tier, max_depth)?;
    if cur.remaining() > 0 {
        return Err(PolicyError::LeftoverPins);       // more pins than occurrences — malformed
    }
    if credited.is_empty() {
        return Ok(None);                             // authentication unsatisfied — not a contributor
    }
    // Satisfied. The walk proved every `expected_anchors` SAID hosted at its tier floor on the
    // surviving branch (satisfies_kel) and reconstructed the iel marker snapshot(s) (NEW-B); both
    // ride in the token so the caller folds them without re-fetching. How the walk surfaces each
    // reconstructed marker state settles with event-shape/pagination — provisional, like the leaf
    // accessors.
    let anchored_saids = expected_anchors.iter().map(|(said, _)| said.clone()).collect();
    let snapshots = source.reconstructed_snapshots();   // marker states this walk fixed (provisional, NEW-B)
    // Bind the issuer's authentication policy SAID (A); this per-issuer sub-token has no challenge.
    Ok(Some(PolicyVerification::new(policy.said.clone(), None, credited, anchored_saids, snapshots)))
}

// `cur` is a SINGLE positional cursor; each leaf takes the NEXT slot (`take_next`) when the walk
// reaches it. Consumption is driven by the STRUCTURAL walk, not by satisfaction: a failed leaf —
// and a present-but-unsatisfied `iel` whose subtree still drains — cannot desync later slots.
// Composers evaluate every branch (no short-circuit) so slot order is deterministic.
//
// Returns the SET of distinct prefixes this expression CREDITS if satisfied, else the empty set
// (mirrors `issuance_credited`). A satisfied leaf credits the prefix it authenticates — `kel(K)`→K,
// `iel(X)`→X — where the prefix comes from the STRUCTURE, not the pin (`satisfies_iel` already
// checks `event.prefix == leaf_prefix`). A composer returns the UNION of its children's credited
// sets iff its threshold is met (else ∅), satisfied iff `|set| ≥ M`; `wgt` keeps each prefix's MAX
// weight, summed once. Dedup is RECURSIVE — the union propagates through nested `thr` / `wgt` /
// `pol` / `and`, so a prefix counts ONCE toward every ancestor threshold (`thr(2, [pol(P1),
// pol(P2)])` with `P1` = `P2` = `iel(alice)` FAILS). An `iel` boundary is OPAQUE: `iel(X)` credits
// `{X}`, never X's internal members — X is the party. `max_depth` bounds `pol`/`iel` recursion (and
// backstops the membership cycle guard); a breach denies.
fn eval_expr(
    expr: &PolicyExpr,
    cur: &mut PinCursor,
    expected_anchors: &HashSet<(Said, Tier)>,
    self_context: Option<HostContext>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // kel: take this leaf's slot. A present SAID names the event just-prior to the anchoring
        // event; resolve its surviving-branch child and check the anchor + tier. Satisfied ⇒ credit
        // {prefix}; a null slot (or exhausted cursor) consumes the slot and credits nobody.
        PolicyExpr::Kel(prefix) => match cur.take_next() {
            Some(Some(prior_said)) => {
                if satisfies_kel(&prior_said, prefix, expected_anchors, source, required_tier)? {
                    Ok(HashSet::from([prefix.clone()]))
                } else {
                    Ok(HashSet::new())
                }
            }
            _ => Ok(HashSet::new()),                  // null slot / exhausted — slot still consumed
        },
        // iel: take this leaf's slot (the Evl/Icp state-marker). A present SAID fixes the IEL's state;
        // reconstruct the snapshot as-of it and recurse into the snapshot's authentication, threading
        // the host context = prefix so an aggregate member's one-arg `mem(group)` resolves against the
        // SAME snapshot's roster (NEW-B), and draining the subtree's slots even if the member fails.
        // Satisfied ⇒ credit {prefix} (the boundary is opaque — X's internal members do NOT propagate).
        // A null slot consumes ONE slot and does NOT descend (the state-marker is un-evidenced, so its
        // authentication subtree is unreachable — see *Pinning → Issuer-side construction*).
        PolicyExpr::Iel(prefix) => match cur.take_next() {
            Some(Some(marker_said)) => {
                if satisfies_iel(&marker_said, prefix, cur, expected_anchors,
                                 source, required_tier, max_depth)? {
                    Ok(HashSet::from([prefix.clone()]))
                } else {
                    Ok(HashSet::new())
                }
            }
            _ => Ok(HashSet::new()),
        },
        // pol: dereference + recurse; pure factoring — propagate the nested credited set UNCHANGED
        // (so a prefix reached through two `pol`s dedups in the enclosing union). `expected_anchors`
        // and the host context (`self_context`) are inherited.
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, cur, expected_anchors, self_context,
                      source, required_tier, max_depth - 1)
        }
        // thr: evaluate every element (Mem children expand inline into iel(member) leaves). In this
        // pinned own-authentication walk a member is always one-arg `mem(group)`, resolved against the
        // enclosing iel(X) marker's reconstructed roster snapshot (FROZEN, NEW-B) — a foreign two-arg
        // `mem(prefix, group)` does not appear here (it lives only in tip-resolved general policies).
        // Members flatten in canonical order; see §Leaf semantics. UNION the children's credited sets;
        // met iff ≥ M DISTINCT prefixes, then return the union (recursive dedup). `del` is not a
        // single-policy element (no slot, no self-traversal here): it appears only in the issuance
        // policy, evaluated by `eval_issuance`.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, source)? {
                union.extend(eval_expr(&child, cur, expected_anchors, self_context,
                                       source, required_tier, max_depth - 1)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt: per-prefix MAX weight across branches (associative/commutative → order-independent;
        // fail-secure vs. sum — one party can't stack roles' weight), each distinct prefix summed
        // once; met iff `sum ≥ M`, then return the credited prefixes.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (child, w) in flatten_weighted(weighted, self_context, source)? {
                for p in eval_expr(&child, cur, expected_anchors, self_context,
                                   source, required_tier, max_depth - 1)? {
                    best.entry(p).and_modify(|e| *e = (*e).max(w)).or_insert(w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and: separation of duties — evaluate EVERY child (no short-circuit; children must drain
        // their pin slots for cursor determinism). Satisfied iff ALL children's credited sets are
        // non-empty; then return their UNION (so an enclosing threshold still counts distinct
        // parties), else ∅. Distinct SATISFIERS are guaranteed only when the branches draw from
        // disjoint identity pools — see §`and`.
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = eval_expr(child, cur, expected_anchors, self_context,
                                         source, required_tier, max_depth - 1)?;
                if credited.is_empty() {
                    all_satisfied = false;            // keep draining the remaining children's slots
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // del / mem standing alone are not valid `expr` (bracket-only) — fail-secure.
        _ => Ok(HashSet::new()),
    }
}

// kel(prefix): the credential is anchored on this KEL. `prior_said` names the event JUST BEFORE
// the anchoring event — the anchoring event commits to the credential, so its own SAID is
// unconstructable here (see the SAID-cycle note). Resolve the anchoring child `s` on the SURVIVING
// branch (`s.previous == prior_said`); an anchor on a divergent or later-archived branch is invalid
// (G — per kel/reconciliation.md, merge.md), so a missing surviving-branch child denies. The walk
// validates `s` inline (trust-boundary). Check every required anchor is hosted at its tier floor and
// `s` clears `required_tier`.
fn satisfies_kel(
    prior_said: &Said,
    leaf_prefix: &Prefix,
    expected_anchors: &HashSet<(Said, Tier)>,
    source: &impl EventSource,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let s = match source.anchoring_child_on_surviving_branch(leaf_prefix, prior_said)? {
        Some(s) => s,                  // surviving-branch child; validated by the walk
        None => return Ok(false),      // divergent / archived — no valid anchor
    };
    // required_tier is the baseline floor for the hosting event; each required anchor may
    // additionally demand a higher tier (a high-assurance SAD co-anchored with a routine one).
    Ok(
        s.prefix == *leaf_prefix
            && s.tier >= required_tier
            && expected_anchors.iter().all(|(anchor, tier)| s.anchors.contains(anchor) && s.tier >= *tier)
    )
}

// iel(prefix): `marker_said` pins the IEL's most-recent `Evl`/`Icp` **state-marker** — NOT an
// anchoring event, so it carries no credential anchor and needs no prior-event trick. The verifier
// reconstructs X's **state snapshot** (authentication AND roster) AS-OF that marker (NEW-B) — the
// same running snapshot the walk already builds; `Del`/`Rsc` don't move it, so the marker is the
// last state-changing event. Satisfaction recurses into the snapshot's authentication policy
// (threading the host context = leaf_prefix so a member's one-arg `mem(group)` resolves), whose
// leaves consume the FOLLOWING slots in walk order — the credential anchor is checked at the
// terminal `kel` leaves the recursion reaches. A one-arg `mem(group)` in X's authentication reads
// its roster FROM THIS SAME reconstructed snapshot — REUSE of the `iel(X)` marker, no second pin —
// so the authentication-recent / roster-stale split is structurally impossible (a free roster slot
// would let an issuer pin authentication-recent + roster-stale and resurrect a removed member). The
// descent runs regardless of prefix match so the subtree's slots always DRAIN (structural
// consumption); the leaf is satisfied only if the marker really is this prefix's and its
// authentication holds. Returns whether to credit `leaf_prefix` upward — the inner credited set
// (X's members/keys) is X's PRIVATE evidence, consumed at this boundary, never propagated (the
// caller credits `{X}`). The marker is read inline from the verification walk, which validates it.
fn satisfies_iel(
    marker_said: &Said,
    leaf_prefix: &Prefix,
    cur: &mut PinCursor,
    expected_anchors: &HashSet<(Said, Tier)>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    // Reconstruct X's snapshot as-of the marker — authentication AND roster from this one snapshot.
    // How the verifier walks back to the marker (a `before`-pagination read + reversed sort) is an
    // EventSource/pagination concern, provisional like the other source accessors.
    let snapshot = source.snapshot_as_of(leaf_prefix, marker_said)?;  // validated inline by the walk
    let authentication = parse_policy_sad(&sadd_fetch(&snapshot.authentication)?)?;
    // The descent threads `leaf_prefix` as the host context, with the roster pinned AT THE MARKER
    // (`AtMarker(&snapshot)`, NEW-B); a one-arg `mem(group)` it reaches resolves against THIS
    // snapshot's roster (`snapshot.roster`) — reuse of the same marker, not a fresh pin.
    let host = HostContext { prefix: leaf_prefix, roster: RosterSource::AtMarker(&snapshot) };
    let sub = eval_expr(&authentication.expr, cur, expected_anchors, Some(host),
                        source, required_tier, max_depth - 1)?; // drains the subtree's slots
    Ok(snapshot.prefix == *leaf_prefix && !sub.is_empty())      // X's authentication met ⇒ credit X
}

// del has NO single-policy helper: `del(X, N)` is never a pinned leaf and never appears in an
// issuer's authentication. It lives only in the issuance policy, where `eval_issuance` matches it by
// SELF-TRAVERSAL (`self_traverses`) — the verifier walks UP each presented issuer's own chain to a
// named delegator, checking authorization + consent + no `Rsc` to the delegator's TIP (F, ALWAYS).
```

#### Current-mode evaluation

`evaluate_current_policy` is the **third credited-set evaluator** — it shares the anchored model and
differs only in **leaf satisfaction** (live attestation at the chain tip vs. the anchored pin-walk).
There is no pinning and nothing is proven anchored; every leaf is checked at the referenced chain's
**tip**. Composition is identical to `eval_expr` / `issuance_credited`: `thr` = `|distinct-prefix
union| ≥ M`, `wgt` = per-prefix max-weight summed `≥ M`, `and` = all branches non-empty → union,
with the same recursive dedup. The one structural addition is the **named-delegates input**: `del` is
non-enumerable and there is no credential here to carry the issuer's name, so the bearer **names the
delegate IEL it acts as** (the live analogue of the credential naming its issuer), capped at 128
(NEW-5). The presented **`attestations`** are capped at the same 128 (NEW-A): each `kel(K)` leaf
verifies against *every* matching attestation, so an uncapped set is a cost amplifier — the
up-front `TooManyAttestations` pre-check refuses it before any chain work, a sibling to the
delegate cap. On satisfaction the entry point returns `Ok(Some(PolicyVerification))` (credited set
only — current mode pins no marker and proves nothing anchored); `Ok(None)` when cleanly
unsatisfied; `Err(_)` on a cap breach or source failure.

```rust
// Current-state evaluation (challenge-response at the chain TIP). `current_credited` returns the set
// of distinct prefixes an expression credits if satisfied at tip, else ∅; the public entry wraps a
// non-empty set into a PolicyVerification token (Ok(None) if empty). Crediting is by the LEAF's
// prefix (kel(K)→K, iel(X)→X), so an iel boundary is opaque and distinct identities count even under
// one controlling key.
pub fn evaluate_current_policy(
    policy: &Policy,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<PolicyVerification>, PolicyError> {
    if attestations.len() > MAX_PRESENTED {          // NEW-A — each kel(K) leaf verifies against EVERY
        return Err(PolicyError::TooManyAttestations); // matching attestation; cap the amplifier up front
    }
    if named_delegates.len() > MAX_PRESENTED {       // K ≤ 128 (NEW-5) — same cap as presented issuers;
        return Err(PolicyError::TooManyDelegates);   // up-front pre-check, fail-secure, zero work done
    }
    let credited = current_credited(&policy.expr, challenge, attestations, named_delegates,
                                    None, source, required_tier, max_depth)?;
    if credited.is_empty() {
        return Ok(None);                             // cleanly unsatisfied
    }
    // Current mode proves nothing anchored and pins no marker, so the token carries only the credited
    // set (anchored_saids + snapshots empty). It DOES bind the policy SAID and the `challenge` (A), so
    // the token proves control over THIS policy under THIS challenge. Token-existence still proves satisfaction.
    Ok(Some(PolicyVerification::new(policy.said.clone(), Some(challenge.clone()), credited,
                                    BTreeSet::new(), Vec::new())))
}

// Mirrors `eval_expr` / `issuance_credited`; the leaf base cases are live attestation at the tip.
fn current_credited(
    expr: &PolicyExpr,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],
    self_context: Option<HostContext>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // kel(K): credit {K} iff an attestation by K validates against K's CURRENT signing key (and
        // recovery key, per the required_tier ATTESTATION SHAPE) over the challenge. NEW-F: the prior
        // `.unwrap_or(false)` that swallowed errors is gone. `verify_current_attestation` returns
        // Ok(false) for a non-verifying EXTERNAL attestation-over-challenge signature — junk, not
        // credited, so a flood of bad attestations can't grief the eval into an error — and Err only
        // for a CHAIN-integrity / source failure (can't resolve K's current key state), which `?`
        // propagates.
        PolicyExpr::Kel(prefix) => {
            let mut credited = HashSet::new();
            for a in attestations {
                if a.signer == *prefix
                    && source.verify_current_attestation(a, challenge, required_tier)? {
                    credited.insert(prefix.clone());
                    break;
                }
            }
            Ok(credited)
        }
        // iel(X): credit {X} iff the attestation set meets X's authentication at X's TIP (recurse,
        // host context = {X, AtTip} — current mode reads the roster LIVE, NEW-B; terminal kels
        // matched by attestation signer). X is named in the policy.
        PolicyExpr::Iel(prefix) => {
            let auth = parse_policy_sad(&sadd_fetch(&source.iel_tip(prefix)?.authentication)?)?;
            let host = HostContext { prefix, roster: RosterSource::AtTip };
            let sub = current_credited(&auth.expr, challenge, attestations, named_delegates,
                                       Some(host), source, required_tier, max_depth - 1)?;
            Ok(if sub.is_empty() { HashSet::new() } else { HashSet::from([prefix.clone()]) })
        }
        // pol: dereference + recurse; propagate the nested credited set unchanged.
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            current_credited(&nested.expr, challenge, attestations, named_delegates,
                             self_context, source, required_tier, max_depth - 1)
        }
        // thr: flatten mem at the host (one-arg) / named-prefix (two-arg) roster's TIP (current mode is
        // tip-live, NEW-B), union the children; met iff ≥ M distinct.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, source)? {
                union.extend(current_credited(&child, challenge, attestations, named_delegates,
                                              self_context, source, required_tier, max_depth - 1)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt: per-prefix MAX weight, each distinct prefix summed once; met iff sum ≥ M.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (child, w) in flatten_weighted(weighted, self_context, source)? {
                for p in current_credited(&child, challenge, attestations, named_delegates,
                                          self_context, source, required_tier, max_depth - 1)? {
                    best.entry(p).and_modify(|e| *e = (*e).max(w)).or_insert(w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and: every child must credit ≥ 1 prefix; on success return the union, else ∅. Evaluate ALL.
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = current_credited(child, challenge, attestations, named_delegates,
                                                self_context, source, required_tier, max_depth - 1)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // del(X, N): the live analogue of anchored del-matching — NO del-pin. Credit each DISTINCT
        // named delegate D (`named_delegates`) whose attestations meet D's authentication at D's tip
        // AND that self-traverses up to X within N hops (delegation valid to X's TIP, F).
        PolicyExpr::Del(delegator, n) => {
            let mut set = HashSet::new();
            for d in named_delegates {
                let d_auth = parse_policy_sad(&sadd_fetch(&source.iel_tip(d)?.authentication)?)?;
                let d_host = HostContext { prefix: d, roster: RosterSource::AtTip };  // tip-live (NEW-B)
                let met = current_credited(&d_auth.expr, challenge, attestations, named_delegates,
                                           Some(d_host), source, required_tier, max_depth - 1)?;
                if !met.is_empty() && self_traverses(d, delegator, *n, source, max_depth)? {
                    set.insert(d.clone());
                }
            }
            Ok(set)
        }
        // mem standing alone is bracket-only (flattened inside thr/wgt before reaching here).
        PolicyExpr::Mem(..) => Ok(HashSet::new()),
    }
}
```

(The tip-state source accessors — `iel_tip`, `verify_current_attestation` — depend on the settled
event/attestation shapes; treat them as provisional pending [`event-shape.md`](event-logs/event-shape.md),
like the anchored leaf accessors above.)

## Withdrawal

A credential can be **withdrawn** — invalidated after issuance — without mutating the credential
itself (it is immutable and content-addressed). Withdrawal works by anchoring a derived digest,
exactly the way the credential's own SAID was anchored:

```
withdrawal_digest = qb64( Blake3-256( "vdti/withdrawal:" ‖ said(credential) ) )
```

To withdraw credential `C`, an authorized party anchors `withdrawal_digest(C)` on a KEL. The
verifier — having already walked the issuer's KEL(s) during the anchored check — scans that same
verified walk **to tip** for the digest. Because the digest is itself anchored and tamper-evident,
withdrawal inherits the same end-verifiability as issuance: no revocation list, no online check.
All withdrawal checks are **identity-current (tip)** — consistent with F evaluating `del` at tip;
no credential-committed pinning is needed (pinning only ever served frozen *issuance* evidence).

Withdrawal is configured by **two fields on the credential itself** — *not* on the generic `Policy`
SAD (which has no withdrawal state, so identical Policy expressions still dedup): an optional
`withdrawal: Option<String>` DSL expression and an `immune: bool` flag. The three modes mirror the
kels poison model:

- **`withdrawal: None`, `immune: false`** (default) → **soft, per-contribution.** A withdrawal
  anchor by one of the **issuer's own authentication KELs** removes *that* contribution; `C` is
  withdrawn only when withdrawals drop the issuer's authentication below its threshold. A single
  key removes only its own anchor (no griefing surface), revocation still works once enough
  withdrawals cross the threshold, and it is symmetric with issuance.
- **`withdrawal: Some(expr)`** → **hard.** `expr` is evaluated as a full policy against the
  withdrawal anchors found at tip; if satisfied, the **whole** credential is unsatisfied. This is
  where admin / third-party kill lives ("2-of-3 admins withdraw") — a named authority that is
  **not** the issuer can hold the withdrawal right.
- **`immune: true`** → **no withdrawal checks ever.** The verifier does not scan for a withdrawal
  digest at all. For credentials whose validity must not depend on a later anchor (e.g. a one-shot
  attestation); permanent and unrevocable, a stated trade-off.

`immune` gates **only** this withdrawal scan. It is **orthogonal to delegation**: the F rescission
tip-walk (confirming no `Rsc` removed a presented delegate, inside `self_traverses`) is **always**
performed, even for an immune credential. The two are independent tip-walks — F is a structural
validity check that never opts out; the withdrawal scan is the one and only thing `immune` skips.

When the verifier finds a satisfying withdrawal anchor (soft: enough to cross the issuer's
authentication threshold; hard: `expr` satisfied), `evaluate_anchored_policy` returns `Ok(None)`:
the credential is structurally well-formed and validly issued, but withdrawn — so no proof token is
minted (a withdrawn credential must not yield a `PolicyVerification`).

> **TODO (pending [event-shape.md](event-logs/event-shape.md) and the credential shape).** The
> withdrawal-digest label (`"vdti/withdrawal:"`), the anchor-scan step (reading the issuer-KEL
> walk's token for the digest), and the `withdrawal` / `immune` field placement on the credential
> are provisional pending the settled credential shape. The three modes (soft / hard / immune) are
> grounded in the kels poison model (kels `docs/design/features/creds.md` §Poisoning).

## Leaf semantics

Each leaf evaluates against chain state and a signed request. Leaves return satisfied / unsatisfied. (`del` and `mem` are bracket-only forms, not leaves — `del` is matched by self-traversing issuers, `mem` flattens to `iel` member leaves; both are covered below.)

### `iel(prefix)` — IEL authentication

The leaf is satisfied iff the controlling party satisfies the IEL's own **authentication** policy at the IEL state the flow fixes — the **pinned `Evl`/`Icp` state-marker** in the anchored flow (the verifier reconstructs the authentication state as-of that marker), the **IEL tip** in the current-state flow. `iel(X)` *defers to X's authentication*: it treats X as an autonomous entity and accepts X's own rule for who acts as X. You don't reach inside X's factors, and you inherit X's threshold — if X's authentication is 2-of-3, `iel(X)` demands 2-of-3. (Authentication is the entity's outward-facing act-as policy — distinct from its **governance**, which gates X's own self-mutation and is never what an external `iel(X)` evaluates.)

This is recursive — `iel(P)`'s check evaluates P's authentication policy, which may itself contain `iel(...)` (directly, or via a one-arg `mem(group)` in an aggregate). The recursion terminates at a singleton's `kel` leaves — the base case of member resolution.

`iel(X)` and `mem(X, group)` both reach entity X, but differently. `iel(X)` **defers** to X's autonomy — it accepts X's own authentication, at X's own threshold, for who acts as X (X authorizes as an institution). `mem(X, group)`, by contrast, takes X's **published roster** for the named group and lets the *referencing* policy compose over those members at a threshold/weights **it** chooses — see [`mem`](#mem--membership-roster-array). Both are first-class for foreign X in **general** policies (application, issuance, withdrawal); the difference is *who sets the bar* (X's authentication vs. the referencing policy).

Within an IEL's *own* `governance` / `authentication` / `delegation` policies, `iel` is **never hand-written**. Those policies use only a one-arg `mem(group)` (aggregate) or `kel()` (singleton); `iel` appears solely as what `mem(group)` expands into and as the resolution primitive each member recurses through — see [IEL policy structure — aggregate vs. singleton](#iel-policy-structure--aggregate-vs-singleton).

### `mem` — membership-roster array

`mem` names a **group** of a membership roster and resolves to one `iel(member_i)` leaf per member of that group. It has two arities:

- **two-arg `mem(prefix, group)`** — names the `group` group of the roster published by **foreign IEL `prefix`**. The reference is **explicit** (both the IEL prefix and the group) because a foreign roster is referenced from outside the owning entity, so the policy must name which IEL's roster and which group. First-class in **general** policies (application, issuance, withdrawal): any such policy may splice IEL X's `executives` group via `mem(X, executives)`.
- **one-arg `mem(group)`** — names the `group` group of the **host** IEL's own roster, with the prefix **implicit**: it is supplied by the enclosing `iel(X)` descent (the marker the anchored walk pinned, or the tip in the current flow). It is the **only** `mem` form an IEL's own three policies may use (its own roster only, never a foreign one), and it is **cycle-forced**, not mere sugar: the IEL's prefix commits to its `(authentication, governance, …)` policies, so an own-policy that named its own prefix would close a content-address cycle (the prefix depends on the policy that would have to name it). See [IEL policy structure — aggregate vs. singleton](#iel-policy-structure--aggregate-vs-singleton).

The `group` label matches `^[a-z_-]{1,16}$` (lowercase `a`–`z`, underscore, hyphen; 1–16 characters; no digits, no uppercase). The roster is a SAD that the IEL commits to — its SAID burned into the IEL, distinct from `governance` / `authentication` / `delegation` — mapping group labels to sets of member IEL prefixes (a member may sit in several groups). `mem(X, group)` is distinct from `iel(X)`: `iel(X)` defers to X's whole authentication, while `mem(X, group)` takes X's published group and composes over it at the referencing policy's own bar.

`mem` is an **array value**, not a standalone leaf — only legal inside a composer's `[...]`, where it flattens in place and concatenates with its siblings:

- inside `thr(k, [mem(prefix, group)])` → `thr(k, [iel(m1), …, iel(mn)])` — *k of that group's members*, with **k chosen by the referencing policy**, not by any member's own threshold. Each member still authenticates via their own authentication policy (`iel(mi)`).
- inside `wgt(M, [([mem(prefix, group)], w), …])` → each member becomes `(iel(mi), w)` — every member of the group carries weight `w`.
- the enclosing `[...]` is a **concat container**: multiple `mem` groups and single expressions mix freely — `thr(2, [mem(org, execs), mem(org, board), kel(K)])` flattens to one child list (`execs` members ++ `board` members ++ `kel(K)`).

This is the membership/composition split. Two levels compose: the **roster level** (which group, how many, or what weight — chosen by the referencing policy) and the **member level** (how each individual proves they act — their own `iel` authentication). The roster lives with the entity (who is in each group); the thresholds/weights live with the policy (how much each member counts here). Adding a member edits the roster, never the policy; changing the bar edits the policy, never the roster.

**Canonical flatten order.** A `mem` array flattens its members in a **canonical order — member
prefix ascending (qb64 byte order)** — so the issuer and verifier lay down identical pin slots and
the [walk-order pinning](#pinning-evidence-pins) stays deterministic across parties. Order within
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
its slot (the [walk-order pinning](#pinning-evidence-pins) stays deterministic, *independent of
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
evidence on its *own* chain (the self-recording handshake — see [*Delegation handshake*](#delegation-handshake--self-recording)),
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
denies — this is the [loss-of-trust semantic](event-logs/iel/) (`Rsc` invalidates downstream
attestations from a delegated party). It is **always** performed, independent of the credential's
`immune` flag (`immune` scopes to withdrawal only — see [*Withdrawal*](#withdrawal)).

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
own anchor pinning (the two-pinning split does not collapse — see [*Policies and Pinnings*](#policies-and-pinnings)).

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
[canonical DSL string form](#verifier-behavior) applies.

## IEL policy structure — aggregate vs. singleton

An IEL is one of two kinds, fixed at inception by an optional boolean **`aggregate`** flag on its
`Icp` event — absent or `false` ⇒ **singleton**, `true` ⇒ **aggregate**. The flag is **immutable**:
an identity does not change kind over its life ("it's an identity, not a choose-your-own-adventure").
The kind constrains what the IEL's three policies (`governance`, `authentication`, `delegation`)
may contain. (This is a constraint on an IEL's *own* three policies only; general policies —
application, issuance, withdrawal — keep the full DSL surface, including `iel(X)` and foreign
`mem(X, group)`.)

- **Singleton** — bottoms out at device keys; it has **no roster** (the `Icp` simply omits the
  roster field). Its three policies may contain only `kel()` leaves, composed with `thr` / `wgt` —
  no `mem`, `iel`, `del`, or `pol`. A singleton is the **base case** that `iel(...)` resolution
  terminates at: every chain of member resolution ends at some singleton's `kel()`. Its
  `authentication` must be non-empty (≥ 1 satisfiable `kel`), or the identity can never act.

- **Aggregate** — composed of other identities (its members). It carries a **roster**: a SAD
  mapping group labels to sets of member IEL prefixes (see [`mem`](#mem--membership-roster-array)).
  Its three policies may contain only one-arg `mem(group)` arrays, composed with `thr` / `wgt` — the
  **host** IEL's **own** roster only, never a foreign one. No bare `iel` / `kel` / `del`, no `pol`.
  An aggregate must be **born with a non-empty roster**, or it is ungovernable. The one-arg form is
  **cycle-forced, not mere convenience**: the IEL's prefix is the content-address of its
  `(authentication, governance, …)` commitment, so an own-policy that named its own prefix
  (`mem(own_prefix, group)`) would close a content-address cycle — the prefix would depend on a
  policy that names it. The prefix is therefore left implicit and supplied by the enclosing `iel(X)`
  descent. (Because the one-arg form carries no prefix, IEL policies stay prefix-free — reducing to
  a smaller complete set, and under content-addressed dedup identical expressions like
  `thr(2, [mem(directors)])` collapse to a single Policy SAD shared across every IEL of that shape,
  saving stored bytes.)

`iel(member)` is **never hand-written** in an IEL policy. It exists only as the form
one-arg `mem(group)` **expands into** — one `iel(member_i)` per current member of the group — and as
the recursion primitive each member resolves through: `iel(member)` defers to that member's
`authentication`, which (if the member is itself an aggregate) is again `mem(group)` → `iel(…)`,
terminating at a singleton's `kel()`. So each IEL policy kind has exactly **one** writable leaf —
`kel` for singletons, `mem` for aggregates — and `iel` is purely the internal resolution form. The
DSL itself is unchanged: `iel` remains a first-class leaf elsewhere (general policies, and the
verifier-constructed `iel(subject)` / `iel(issuer)` of the identity and anchor flows).

**Naming one specific member** uses a **one-element group**: to single out `alice`, give her a group
(`founder = {alice}`) and reference `mem(founder)`. Every individual reference therefore goes
through a labelled roster entry rather than a bare prefix — a policy can never name a non-member,
and because `mem(group)` yields in-roster members *by construction*, no reference can dangle.
(The residual caution is the generic threshold one: shrinking a group below a threshold that gates
it self-bricks — true of any threshold — not a dangling-reference hazard.)

**Group labels** match `^[a-z_-]{1,16}$` — lowercase `a`–`z`, underscore, hyphen; 1–16 characters;
no digits, no uppercase.

**Cycles.** Aggregate-of-aggregate membership forms a graph that must be **acyclic**. The verifier
carries a visited-set / cycle guard in its `iel(...)`-resolution walk so a membership cycle denies
rather than loops; roster-write may additionally forbid self-membership as a first line.

The `aggregate` flag, the roster field, and the roster-less singleton `Icp` shape are **event-shape
facts** (VDTI-10) — provisional here pending [`event-shape.md`](event-logs/event-shape.md). This
section states only the **DSL-level constraint** the two kinds impose on policy contents.

> SELs have no identity and no roster — only `governance` + `operation` policies — so the
> aggregate/singleton distinction is **IEL-only**.

## Worked examples

**Single-key authorization** — prove a device attested to something:
```
kel(prefix)
```

**IEL authentication** — prove a link to a basic identity:
```
iel(prefix)
```

**Membership threshold** — k-of-a-group authentication, with k chosen by this policy (not by the org or its members):
```
thr(2, [mem(prefix, staff)])
```

With org `prefix`'s `staff` group = `{m1, m2, m3}` (resolved from that IEL's roster), expands to `thr(2, [iel(m1), iel(m2), iel(m3)])` — any two staff. Adding a fourth member edits the roster; this policy is unchanged. Concatenate groups by listing them: `thr(2, [mem(prefix, staff), mem(prefix, board)])` pools both into one flat child list.

**Emergency override**:
```
thr(1, [
    thr(3, [mem(prefix, members)]),
    kel(emergency)
])
```

Any three members satisfy, or the emergency key alone.

**Weighted membership groups** — an org weights executive / admin / member groups at 3 / 2 / 1, threshold 3 (the groups live in the org's one roster; weight is this policy's per-group valuation):
```
wgt(3, [
    ([mem(prefix, executives)], 3),
    ([mem(prefix, admins)],     2),
    ([mem(prefix, members)],    1)
])
```

With `prefix`'s roster `executives = {E1, E2}`, `admins = {A1, A2, A3}`, `members = {M1, …}`, this flattens to `wgt(3, [(iel(E1), 3), (iel(E2), 3), (iel(A1), 2), (iel(A2), 2), (iel(A3), 2), (iel(M1), 1), …])`. Satisfied by: one executive (3), two admins (4), three members (3), or one admin + one member (3); one admin alone (2) does not clear. The weights are this policy's valuation of each group — a stricter resource could set `member → 0`; the roster is unchanged. A member in two groups is deduplicated to its highest weight (see *Leaf semantics → `mem`*).

**Aggregate IEL authentication** — an aggregate's own `authentication` composes only over its own roster (one-arg `mem`), never bare prefixes:
```
thr(2, [mem(directors)])
```
"Any 2 current directors authenticate as the aggregate." To require a specific individual, give them a one-element group — `mem(founder)` with `founder = {alice}`. A **singleton's** authentication, by contrast, is `kel`-only — e.g. `thr(2, [kel(device_a), kel(device_b)])` — the base case the `iel(...)` recursion bottoms out at (see *[IEL policy structure](#iel-policy-structure--aggregate-vs-singleton)*).

**Separation of duties** — `and` requires *each* branch independently, which a union threshold cannot:
```
and([
    thr(1, [mem(org, board)]),
    thr(1, [mem(org, execs)])
])
```
≥1 board member **and** ≥1 executive. If `board` and `execs` are disjoint this is two different
people; if someone sits on both, that one person satisfies both branches alone — `and` enforces "each
pool is met," not "distinct people" (see *[`and`](#andexpr----conjunction-separation-of-duties)*). For
dual control mixing a pool with a named key: `and([thr(2, [mem(org, admins)]), kel(emergency_cosigner)])`
— 2 admins **and** the co-signer. `and` composes inside other composers: `thr(1, [and([iel(a), iel(b)]),
kel(break_glass)])` = (a **and** b) **or** break-glass.

## Composition semantics

- **Leaves evaluate independently.** One leaf's satisfaction never depends on another's. The shared pin cursor and the per-log single paged verification walk are plumbing (slot assignment, walk reuse), not satisfaction coupling.
- **Composers are pure aggregators.** They take their children's **credited sets** (the distinct prefixes each child satisfied) and produce a credited set of their own — `thr`/`and` union the children, `wgt` sums per-prefix max weights — emitting that union iff the threshold is met, else `∅`. Crediting is by *structural* prefix and dedups recursively (a prefix counts once toward every ancestor), so the same identity reached two ways satisfies once, not twice. Pins are never deduped. No side effects (see §Leaf semantics, §Composition).
- **Boundedness.** Bounded cost. There is no separate pure bind phase: the policy graph is *expanded as it is walked* (descending through `pol`, `iel` authentication, and `mem` rosters), consuming pins positionally and running leaf checks inline on the verifier's verification walk — the single paged pass each referenced log gets for end-verifiability anyway. A log referenced by several leaves is paged once, and a million-event log is paged through once in O(chain length), parallelizable across logs (resident cost bounded by the page — the chain is never materialized whole). Every recursion/walk depth is capped by the always-passed `max_depth`; `mem` foreign-roster expansion is capped by a roster-width bound; and a **per-policy expansion cap** (NEW-G) bounds the *total* post-flatten leaf count across all rosters, `pol` nesting, and `iel` recursion — so neither a malicious foreign roster nor many moderate ones can amplify cost without bound. The **presented-issuer count** (anchored mode) and the **claimed-delegate count** *and* **attestation count** (current mode) are each capped at `MAX_PRESENTED` (128) by an up-front trust-boundary pre-check — a sibling bound to `max_depth`, roster-width, and the per-policy expansion cap — so a caller cannot amplify cost by presenting an unbounded issuer / delegate / attestation set; exceeding it refuses (`TooManyIssuers` / `TooManyDelegates` / `TooManyAttestations`) before any chain work. Self-traversal of a `del` chain is bounded by the placeholder's `N`. Evaluation itself is a cheap tree walk.
- **Deterministic.** Given a fixed chain state and signed request, evaluation is deterministic. Verifiers across nodes converge.

## Verifier behavior

The verifier **expands the policy graph as it walks it** — there is no separate pure bind phase. It
first confirms the presented `issuers` equal the credential's **committed issuer set** (the
issuer↔content↔anchor binding must not depend on caller bookkeeping — the verifier is the trust
boundary), and refuses up front if more than `MAX_PRESENTED` (128) issuers are presented
(`TooManyIssuers`) — a count cap enforced at the trust boundary before any chain work, sibling to
`max_depth`, the roster-width bound, and the per-policy expansion cap (NEW-G). Current mode applies
the same `MAX_PRESENTED` cap to **both** `named_delegates` (`TooManyDelegates`) and the presented
`attestations` (`TooManyAttestations`, NEW-A) — see *Current-mode evaluation*. Then, for each issuer,
two independent checks ride inline on the **verification walk** (`source`), the single paged pass each
referenced log gets for end-verifiability anyway:

- **Anchor** — evaluate `iel(issuer)` against that issuer's **anchor pinning**, consuming pins
  positionally in pre-order walk order (a single cursor advances one slot per leaf; a `null`/absent
  slot fails that leaf but still consumes its slot; *leftover pins after the walk deny*). The `iel`
  leaf reads the pinned `Evl`/`Icp` state-marker (the verifier reconstructs the snapshot fixing the
  authentication state) and recurses into that authentication; the terminal `kel` leaves resolve the anchoring child **on the surviving branch**
  and check the credential anchor at the required tier. `expected_anchors` rides this walk, so the
  anchor is checked on the issuer's *own* authentication.
- **Delegation** — `self_traverses` walks **up** the issuer's own delegation chain to a delegator
  the issuance policy names (`del(X, N)`, `≤ N` hops), direct-looking-up each `Del` (no enumeration)
  and checking authorization + consent + **no `Rsc` to the delegator's tip** (F, always).

`evaluate_anchored_policy` then evaluates the issuance policy, where each `del(X, N)` placeholder is
matched by the **distinct anchored issuers** that self-traverse to `X` within `N`; composers count
distinct issuers. Finally it scans each issuer KEL to tip for a withdrawal anchor — skipped **only**
when the credential is `immune` (the F rescission walk above is never skipped). The public entry
points are **policy verifiers**: on satisfaction they return `Ok(Some(PolicyVerification))` — the
unforgeable proof token — `Ok(None)` for a clean unsatisfied, and `Err(_)` for a structural/source
failure (see *API Surface*). The full Rust under
[*Policies and Pinnings → Implementation*](#policies-and-pinnings) is canonical; the sketch below
shows the shape — the internal helpers elide the token (returning sets / bools) for readability, but
the public `evaluate_anchored_policy` returns it:

```
evaluate_anchored_policy(issuance_policy, issuers, committed_issuers, expected_anchors, withdrawal,
                         immune, source, required_tier, max_depth)
        -> Result<Option<PolicyVerification>>:
    if len(issuers) > MAX_PRESENTED: error(TooManyIssuers)                       # count cap, up front
    assert {prefix for (prefix, _) in issuers} == committed_issuers             # trust boundary (NEW-D)
    # INTERIM: Phase 3 reads `committed_issuers` from a `&Credential` input rather than as a separate
    # arg (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`); the boundary check stays.
    if issuers is empty: return Ok(None)

    anchored = []; issuer_tokens = []                            # (a) anchor proof per issuer
    for (issuer, anchor_pinning) in issuers:
        if let Some(t) = evaluate_single_policy(parse_policy("iel(" + issuer + ")"), anchor_pinning,
                                  expected_anchors, None, source, required_tier, max_depth):
            anchored.append(issuer); issuer_tokens.append(t)

    credited = issuance_credited(issuance_policy.expr, anchored, source, max_depth)  # (b) count distinct
    if credited is empty: return Ok(None)

    if not immune and is_withdrawn(expected_anchors, anchored, withdrawal,         # withdrawal at tip
                                   source, required_tier, max_depth):
        return Ok(None)
    # fold the issuer tokens' anchored SAIDs + reconstructed marker snapshots into the result — the
    # returned token carries every sub-walk's proven facts. (CONSUMING the underlying chain
    # verification tokens themselves — so the result proves every walked CHAIN verified, not just every
    # sub-policy — is the Phase-3 rewrite: `.working/vdti-12-policy-dsl-phase3-token-architecture.md`.)
    return Ok(Some(PolicyVerification::new(issuance_policy.said, None, credited,        # bind policy SAID (A)
                                           fold_anchored_saids(issuer_tokens),
                                           fold_snapshots(issuer_tokens))))

# issuance_credited: del(X, N) credited by distinct anchored issuers self-traversing up to X within N;
# DIRECT issuers credited by iel(X) (X in anchored) / mem(X, group) (anchored members at X's tip);
# pol recurses; thr/wgt/and count DISTINCT issuer prefixes (set union; wgt dedups by max weight;
# and = all branches non-empty). kel credits nobody. Never expands del. (eval_issuance wraps it as a
# bool — `not issuance_credited(...).is_empty()` — where only a yes/no is needed.)

# self_traverses: walk UP candidate's chain to delegator, <= max_hops, F-rescission-to-tip ALWAYS.
self_traverses(candidate, delegator, max_hops, source, max_depth) -> bool:
    lower = candidate
    for _ in 0 .. min(max_hops, max_depth):
        parent   = source.delegating_prefix(lower)           # lower.Icp.delegating       (consent)
        del_said = source.delegating_del_said(lower)         # lower.Evl[1].delegating     (consent back-ptr)
        del      = source.del_event(parent, del_said)        # direct lookup; MUST be a `Del` (rejects `Rsc`/other)
        if del.host != parent or not del.lists(lower):       return false   # authorization (reads `Del` additions)
        if source.rescinded_by_tip(parent, lower):           return false   # F — ALWAYS (immune ignored)
        if parent == delegator:                              return true
        lower = parent
    return false

# evaluate_single_policy: positional pin-walk over ONE del-free policy (the issuer's authentication).
# Leftover pins deny. self_context threads the host context (prefix + roster source: AtMarker(snapshot)
# inside an iel descent, AtTip otherwise) for an aggregate member's one-arg mem(group).
# Returns Some(token) (credited set + anchored SAIDs + reconstructed marker snapshots) on satisfaction,
# None on a clean miss — the anchored entry folds the token into its result.
evaluate_single_policy(policy, pinning, expected_anchors, self_context, source, required_tier, max_depth)
        -> Option<PolicyVerification>:
    cur = PinCursor(pinning.pins)
    credited = eval_expr(policy.expr, cur, expected_anchors, self_context, source, required_tier, max_depth)
    if cur.remaining() > 0: error(LeftoverPins)              # more pins than occurrences — malformed
    if credited is empty: return None                       # satisfied iff ≥ 1 prefix credited
    return Some(PolicyVerification::new(policy.said, None, credited,                    # bind policy SAID (A)
                                        anchored_saids(expected_anchors),
                                        source.reconstructed_snapshots()))

# Leaves take the NEXT slot (positional, pre-order order) and read that event from the verification
# walk; consumption is structural (a failed/present-unsatisfied iel still drains its subtree). Returns
# the SET of distinct prefixes CREDITED if satisfied, else ∅: a satisfied kel(K)/iel(X) credits {K}/{X}
# (the prefix from the STRUCTURE, not the pin); a composer unions its children iff its threshold is met
# (recursive dedup — a prefix counts once toward every ancestor; an iel boundary is opaque). del is NOT
# a single-policy element (no slot, no self-traversal here). Unknown primitive => whole policy denies
# (fail-secure), handled by the caller.
eval_expr(expr, cur, expected_anchors, host, source, required_tier, max_depth) -> set<Prefix>:
    if max_depth == 0: error(MaxDepthExceeded)
    match expr:
        kel(prefix) => cur.take_next() is Some(Some(prior))  and satisfies_kel(prior, prefix, expected_anchors, source, required_tier) ? {prefix} : {}
        iel(prefix) => cur.take_next() is Some(Some(marker)) and satisfies_iel(marker, prefix, cur, expected_anchors, source, required_tier, max_depth) ? {prefix} : {}
        pol(said)   => eval_expr(parse_dsl(sadd.fetch(said).content).expr, cur, expected_anchors, host, source, required_tier, max_depth - 1)   # propagate nested set
        thr(M, ss)  => U = union(eval_expr(s, cur, …) for s in flatten(ss, host, source));            |U| >= M ? U : {}
        wgt(M, ws)  => B = per-prefix MAX weight over (s, w) in flatten_weighted(ws, host, source);   sum(B.values) >= M ? B.keys : {}
        and(cs)     => sets = [eval_expr(c, cur, …) for c in cs];   all(s nonempty for s in sets) ? union(sets) : {}   # eval ALL (drain slots)
        _           => {}                                    # del/mem standing alone are bracket-only

# kel: `prior` is the pinned event just before the anchoring event; resolve its SURVIVING-BRANCH
# child S (S.previous == prior) — checking it there, inline, both dodges the SAID cycle and needs no
# search. A divergent / archived branch has no valid anchor. iel: the pin is the Evl/Icp state-marker
# (cycle-free); reconstruct the snapshot AS-OF it and recurse into the snapshot's authentication
# (threading host = {prefix, AtMarker(snap)}; a one-arg mem(group) under it REUSES this same snapshot's roster, NEW-B) —
# the credential anchor is checked at the terminal kel leaves; the descent drains the subtree's slots
# even on mismatch (structural consumption).
satisfies_kel(prior, leaf_prefix, expected_anchors, source, required_tier):
    S = source.anchoring_child_on_surviving_branch(leaf_prefix, prior)    # None if divergent/archived
    if S is None: return false
    return S.prefix == leaf_prefix
        AND S.tier >= required_tier
        AND for all (anchor, tier) in expected_anchors: S.anchors.contains(anchor) AND S.tier >= tier

satisfies_iel(marker_said, leaf_prefix, cur, expected_anchors, source, required_tier, max_depth):
    snap = source.snapshot_as_of(leaf_prefix, marker_said)               # reconstruct state AS-OF the Evl/Icp marker (NEW-B)
    host = HostContext{ prefix: leaf_prefix, roster: AtMarker(snap) }          # NEW-B — roster frozen at the marker
    sub  = eval_expr(parse_dsl(sadd.fetch(snap.authentication).content).expr,  # one-arg mem(group) reuses snap.roster
                    cur, expected_anchors, Some(host), source, required_tier, max_depth - 1)
    return snap.prefix == leaf_prefix AND sub nonempty                   # X's authentication met ⇒ credit X; drains subtree regardless of match
```

**Semantics notes:**

- **Anchor requirement propagates uniformly.** A `pol(said)` recursion — and an `iel`
  authentication recursion — threads the same positional `cur` cursor, `expected_anchors`, `source`,
  `required_tier`, and `max_depth` as the outer evaluation (and `self_context` set to the enclosing
  `iel` prefix). Because `evaluate_single_policy` is only ever called for an issuer's *anchor* walk,
  every `kel` leaf reached under it is an anchoring leaf, so `expected_anchors` flows down to all of
  them; an issuance-policy `del(X, N)` is matched separately by self-traversal and never carries the
  anchor requirement. The whole expanded graph consumes one positional pin cursor, each occurrence
  taking its own slot in pre-order order; leftover pins after the walk deny.
- **The SAID cycle, and why kel prefixes pin the *prior* event.** A SAID is the hash of the SAD with its own said-field zeroed, so it depends on every other field. The event that anchors credential `C` lists `said(C)` in its `anchors`; `C` commits to the Pinning (`said(P)`); `P` lists the pinned event's SAID. Pinning the anchoring event directly would close the loop `said(anchor) → said(C) → said(P) → said(anchor)` — unconstructable. So a kel prefix pins the event *just prior* and the verifier rederives the anchoring child on the surviving branch. iel prefixes are cycle-free: they pin `Evl`/`Icp` state-markers (the verifier reconstructs the authentication snapshot as-of them), which never carry the credential anchor. Avoiding a second walk of a shared log is handled by the verification walk paging that log once and checking all of its pinned positions inline (the pinned SAIDs are supplied up front as the positions to check), not by the pin array order.
- **`pol(said)` reference cycles are structurally impossible.** Content-addressed references can't form a cycle without a Blake3-256 collision (two Policy SADs mutually containing each other's SAIDs). No runtime cycle check needed.
- **Hard depth cap (`max_depth`, always passed).** Every recursive/walk depth in evaluation — `del` self-traversal, `pol` nesting, `iel` authentication recursion — is bounded by an **explicit `max_depth` the caller always passes**; never implicit or unbounded. It is sourced from data where a governing bound exists (a `del(X, N)` chain caps at `N`) and from a sensible default otherwise (`pol`/`iel` nesting, e.g. 16). Exceeding it **denies** (fail-secure). This also backstops the aggregate-membership cycle guard.
- **Roster-width bound (foreign `mem`).** `mem(X, group)` with foreign `X` expands to one leaf per roster member, and `X` controls its roster. Expansion is capped by a **width bound**; a roster exceeding it denies with an "expansion truncated" signal (fail-secure) — a large or malicious foreign group cannot amplify verifier cost without bound.
- **Per-policy expansion cap (NEW-G).** Beyond the per-roster width bound, the **total** number of leaves a single policy expands to — summed across every `mem` flatten, `pol` nesting, and `iel` authentication recursion — is capped by a per-policy expansion bound, a sibling to `max_depth`, the roster-width bound, and `MAX_PRESENTED`. A policy whose post-flatten leaf count exceeds it denies (fail-secure) before the walk completes, so neither a deeply nested composition nor many moderate rosters can multiply past the cap even when no single roster is over-wide.
- **Tier check is in the leaf helpers, not the composers.** A kel prefix's `satisfies_kel` rejects an anchoring event hosted below `required_tier`; the tier requirement propagates unchanged through the iel authentication recursion to the terminal kel leaves. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized primitive → the WHOLE policy denies (fail-secure).** An older verifier encountering a newer DSL primitive must **not** treat it as a merely-unsatisfied sub-expression: `thr(1, [new_restrictive_thing, old_permissive_thing])` would then silently ignore the restriction and pass. Instead an unknown primitive fails the **entire** policy closed (`Ok(None)` for the whole evaluation — no proof token is produced). Greenfield ships one DSL version, but this keeps safety intact under any skew.
- **Pinned canonical DSL string form.** Policies are stored as DSL **strings** inside a SAD, and JCS canonicalizes the surrounding JSON but treats the DSL as opaque — so `thr(2,[a,b])` and `thr(2, [a, b])` would otherwise produce different SAIDs. The DSL has a **pinned canonical string form** (the analog of `said.md`'s normatively-pinned JCS): no insignificant whitespace, arguments comma-separated without spaces, `mem` members emitted in canonical order, and **`wgt` entries fully split to single-element brackets** (next bullet). Every cross-party-agreement and content-addressed dedup claim (the prefix-free one-arg `mem` collapse, where identical own-policies share a Policy SAD; two parties independently authoring "the same" policy) depends on it.
- **Canonical `wgt` desugar.** A multi-element `wgt` bracket and its split equivalent parse to the *same* AST — `wgt(M, [([a, b], w), …])` and `wgt(M, [([a], w), ([b], w), …])` both yield two weight-`w` entries (the array is lossless concise sugar — `([a, b], w)` desugars to `(a, w), (b, w)`). They must therefore canonicalize to one string, or their SADs' SAIDs diverge and `wgt`'s cross-party agreement breaks. **Canonical form splits every entry to single-element brackets `([elem], w)`, in source order**: `([a, b], w)` → `([a], w), ([b], w)`; a `mem` / `del` element stays whole inside its own single-element bracket (`([mem(X, g)], w)`, `([del(X, N)], w)`) — `wgt` subjects are membership-style only, no composer/`pol` (NEW-E). Only the bracket grouping is normalized — source/sibling order is preserved (the analog of the `mem`-order rule).
- **Issuer-set trust boundary.** The verifier confirms the presented `issuers` equal the credential's **committed issuer set** before crediting any of them — the issuer↔content↔anchor binding never depends on caller bookkeeping (the verifier is the trust boundary). (INTERIM: Phase 3 reads the committed set from a `&Credential` input rather than as a separate `committed_issuers` arg — `.working/vdti-12-policy-dsl-phase3-token-architecture.md` — and softens per-issuer failure (E1); the boundary check itself is unchanged.)
- **Challenge binding (current-state flow).** The `challenge` `evaluate_current_policy` verifies must be **unpredictable, single-use, and context-bound** (to the resource, action, and credential at hand) — otherwise an attestation over a reused challenge replays across contexts. The server constructs it (e.g. a random nonce hashed with the request context); the verifier rejects a stale or context-mismatched challenge before checking signatures.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

- **IEL `Evl` / `Dec`** — gated by `governance`
- **IEL `Del` / `Rsc`** — gated by `delegation`
- **SEL `Evl` / `Rpr` / `Dec`** — gated by `governance`
- **SEL `Est` / `Ixn`** — gated by `operation`
- **Application-defined gates** — credentials, signed requests, etc. — gated by application-specific policy references

## End-to-end access example

Putting the two entry points together: a resource grants an action iff the presented credential
is **validly issued and not withdrawn** AND the bearer **currently controls the credential's
subject** AND the credential's **roles cover the action's permission**. Three independent checks,
three different mechanisms:

```rust
// A bearer requests `action` on a resource, presenting `cred` (which NAMES its issuers and
// carries one anchor pinning per issuer) and a fresh signature over `challenge` (a context-bound,
// single-use nonce digest).
fn authorize(
    cred: &Credential,
    action: Action,
    challenge: &Digest256,
    attestations: &[Attestation],
    issuance_policy: &Policy,       // the resource's configured issuance policy
    source: &impl EventSource,
) -> Result<bool, PolicyError> {
    // 1. Validity — each named issuer self-traverses to a delegator the issuance policy names and
    //    anchors the credential on its own authentication at the required tier; enough DISTINCT
    //    issuers clear the issuance threshold; and no satisfying withdrawal anchor was found. The
    //    presented issuers are asserted equal to the credential's committed set INSIDE the verifier
    //    (NEW-D). On success it returns a PolicyVerification proof token.
    let cred_anchor: HashSet<(Said, Tier)> =
        [(cred.said, Tier::One)].into_iter().collect();
    let issuers: Vec<(Prefix, &Pinning)> = cred.issuers();   // committed set, sourced from the cred
    let committed: HashSet<Prefix> = cred.committed_issuers().into_iter().collect();
    let Some(validity) = evaluate_anchored_policy(
        issuance_policy,
        &issuers,
        &committed,                  // NEW-D: asserted == presented, inside the verifier
        &cred_anchor,
        cred.withdrawal.as_deref().map(parse_policy).transpose()?.as_ref(),  // None = soft default
        cred.immune,
        source,
        Tier::One,
        16,                          // max_depth (del's N bounds the delegation walk; this caps nesting)
    )? else {
        return Ok(false);            // not issued by a recognized authority, or withdrawn
    };

    // 2. Identity — the bearer presently controls the credential's SUBJECT. The subject is an IEL;
    //    `iel(subject)` defers to the subject's own authentication policy, so a rotated or multi-sig
    //    subject still authenticates correctly. The challenge defeats replay. `iel(subject)` has no
    //    `del`, so no delegates are claimed (&[]).
    let subject_policy = parse_policy(&format!("iel({})", cred.subject))?;
    let Some(identity) = evaluate_current_policy(
        &subject_policy,
        challenge,
        attestations,
        &[],                         // no del leaves in iel(subject) → no claimed delegates
        source,
        Tier::One,
        16,                          // max_depth
    )? else {
        return Ok(false);            // credential presented by someone who isn't the subject
    };

    // 3. Authorization — the application maps the credential's roles to permissions and grants iff
    //    the action's required permission is covered. Pure application policy; the DSL's job ended
    //    once validity + identity were established. The grant is minted by `mint_grant`, which TAKES
    //    both proof tokens by reference — so it is type-impossible to reach a grant without having
    //    run both verifiers to satisfaction (verify-before-use enforced by the SIGNATURE, not a
    //    comment). No TOCTOU: the verified facts ride in the tokens (E2).
    Ok(mint_grant(cred, action, &validity, &identity))
}

// The ONLY path to a grant — and it cannot be called without BOTH proof tokens in hand, so a caller
// that skipped verification simply has no `&PolicyVerification` to pass (E2). A real system returns a
// capability object binding `validity`/`identity`; here it returns the bool grant for brevity. The
// tokens make the verified facts available WITHOUT re-fetching — e.g. `identity.challenge()` confirms
// the live-control proof is over the challenge this request issued, and `validity.credited()` /
// `validity.is_said_anchored(&cred.said)` confirm the anchoring issuers — bound before the role map
// decides. The role→permission map is application policy.
fn mint_grant(
    cred: &Credential,
    action: Action,
    validity: &PolicyVerification,    // anchored-mode proof: the credential is validly issued
    identity: &PolicyVerification,    // current-mode proof: the bearer controls the subject
) -> bool {
    debug_assert!(validity.is_said_anchored(&cred.said));   // the validity proof covers THIS credential
    debug_assert!(identity.challenge().is_some());          // the identity proof is challenge-bound (current mode)
    cred.roles
        .iter()
        .flat_map(permissions_for_role)              // application-defined role → permissions
        .any(|p| p == action.required_permission())  // application-defined action → permission
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

2. **Extension points.** The DSL is closed at the primitive level (8 primitives — leaves, the `mem` membership array, the `del` delegation placeholder, the `thr` / `wgt` / `and` composers). Future primitives (new chain types; new leaf semantics) would require DSL extension. The fail-secure rule (§Verifier behavior) makes additions safe under skew — an old verifier encountering an unrecognized primitive denies the **whole** policy rather than silently ignoring a possibly-restrictive new term.

## Forward-refs

- [`event-logs/iel/`](event-logs/iel/) — IEL primitive (subsequent sub-issue); references this doc for governance / delegation / authentication policy evaluation
- [`event-logs/sel/`](event-logs/sel/) — SEL primitive (subsequent sub-issue); references this doc for SEL governance / operation
- `lib/vdti` — verifier implementation; evaluates DSL expressions per this spec
