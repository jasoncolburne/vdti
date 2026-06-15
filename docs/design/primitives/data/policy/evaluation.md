Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## API Surface

The policy primitive is **general** — it is the authorization language IELs (governance / authentication /
delegation), SELs (governance / operation), and features (credentials, read gates) all evaluate. It knows
nothing about credentials; credentials are a **feature** that *composes* it (see *Credentials are a feature*,
below). Three public entry points:

- **`evaluate_gate_policy`** — the **general anchored single-policy governance gate**. Evaluates **one**
  del-free policy against **one** pinning, resolving leaves **as-of** the pinned state. This is what an
  IEL / SEL governance gate calls to authorize an `Evl` / `Ixn` / `Est` against the chain's tracked,
  **floored `policyPin`** (event-shape [`§policyPin`](../event-logs/event-shape.md#policypin)). A foreign
  `grp(X, group)` in the gated policy resolves X's roster from the **gate context** — the gating SEL's
  floored `policyPin`, never an invoker-chosen marker.
- **`evaluate_anchored_policy`** — **multi-party** anchored validity. Given presented parties + their anchor
  pinnings + the anchors to check, it confirms enough distinct parties satisfy a policy (with `del`
  self-traversal) and anchor the named SADs on the **surviving branch** at the required tier. Returns the
  credited set + a general anchored proof token.
- **`evaluate_current_policy`** — live **challenge-response control**: who *currently* controls a policy,
  evaluated at the chain **tip**.

All three run their leaf checks **inline on a single paged verification walk per referenced log** — the pass
each log gets for end-verifiability anyway — and all three read chain state **only through verified chain
tokens**, never a live `EventSource` (see *Chain-verification provider*). `del(prefix, N)` is resolved by
**self-traversal** in both anchored and current modes (no delegation pin: the candidate walks *up* its own
delegation chain to the named delegator). There is no separate pure bind phase and no evidence-gathering
walk: the policy graph is expanded as the walk descends, and pins are consumed positionally (see *Pinning*).

### Chain-verification provider (the dependency-inversion seam)

The evaluators never re-walk a referenced chain and never read a live source. Each referenced chain is walked
**once** by its own chain verifier, which yields an immutable **verification token**; the evaluator
**consumes** the tokens. The cross-chain dependency rides **content-addressed tokens passed between
independent walks** — there is **no cross-chain atomic batching** (a joint walk plus a two-table atomic
insert is reserved for tight ceremonies — delegated `[Icp, Evl]`, bootstrap — and is not a general
requirement).

```rust
// The provider is the DEPENDENCY-INVERSION SEAM: this trait is DECLARED in the policy primitive (layer 3)
// and IMPLEMENTED by the chain verifiers (layer 4). Policy sits below the chain primitives; neither depends
// on the other's implementation — this is what breaks the policy <-> iel cycle. Given a prefix, the provider
// runs (or resumes from cache, keyed by prefix — one paged walk per log) the appropriate chain verifier and
// returns a VERIFIED token. The evaluator reads chain state ONLY off these tokens; it holds no EventSource.
// Possession of a token IS the proof the chain was verified (verify-before-use). A chain that fails
// verification surfaces as Err(PolicyError::ChainUnverifiable) — caught per-party as a SOFT failure (E1);
// a structural/malformed condition is a HARD error.
//
// FORTHCOMING (provisional dependency — design-now posture): `KelVerification` is concrete today (the kels
// chain-verifier precedent — KelVerifier::into_verification()). `IelVerification` / `SelVerification` are
// the forthcoming vdti chain-verifier work this interface front-runs; the accessors below are the contract
// those verifiers must satisfy.
pub trait VerificationProvider {
    fn verify_iel(&self, prefix: &Prefix) -> Result<IelVerification, PolicyError>;
    fn verify_kel(&self, prefix: &Prefix) -> Result<KelVerification, PolicyError>;
    fn verify_sel(&self, prefix: &Prefix) -> Result<SelVerification, PolicyError>;
}

// Token accessors the evaluator needs (the contract the layer-4 verifiers must expose). The marker-keyed
// accessors are O(1) MAP LOOKUPS — never a search, never a per-call replay: the token holds no EventSource and
// never re-walks. The evaluator REGISTERS the marker SAIDs it will query (all known up front — from the SEL's
// `policyPin` and the deep per-event evidence) with the verifier BEFORE its single inception->tip walk (the
// kels `check_anchors` register-before-walk pattern; the `id` analog of `is_said_anchored`); that one walk
// reconstructs the state AT each registered marker and records it into a `marker_said -> IelStateSnapshot` map
// on the token. A lookup MISS — a marker the walk never recorded, i.e. not a genuine `Evl`/`Icp` on this chain
// — is a HARD reject, so the lookup doubles as marker validation.
//
//  IelVerification:
//    - snapshot_as_of(marker_said) -> IelStateSnapshot  // O(1) lookup of the snapshot recorded at the marker:
//                                                        // authentication policy SAID + roster + is_singleton
//                                                        // + prefix (NEW-B). Miss -> reject.
//    - tip() -> IelStateSnapshot                         // the same, at tip (current mode)
//    - roster_at(marker_said, group) -> Vec<Prefix>      // O(1): the group's members read off that marker's
//                                                        // snapshot roster (canonical order). Miss -> reject.
//    - delegating_prefix() / delegating_del_said()       // this IEL's Icp.delegating + serial-1 Evl.delegating (consent)
//    - del_event(del_said) -> DelEvent                   // direct lookup on THIS IEL; MUST be a `Del` (rejects `Rsc`)
//    - rescinded_by_tip(lower) -> bool                   // walk THIS IEL to tip for an `Rsc` of `lower` (F)
//    - said() -> Said                                    // the token's SAID (folded into consumed_chain_tokens)
//  KelVerification (kels precedent — mostly exists):
//    - anchoring_child_on_surviving_branch(prior_said) -> Option<AnchoringEvent>  // the `dev` prior-event trick
//    - is_said_anchored(said) -> bool                    // a SAID anchored on the surviving branch
//    - verify_attestation(attestation, challenge, required_tier) -> bool          // current-mode signature check
//    - said() -> Said
//  SelVerification (forthcoming):
//    - policy_pin_marker(prefix) -> Option<Said>         // the tracked, FLOORED policyPin's entry for `prefix`
//                                                        // (the D3b foreign-`grp` marker source) — never invoker-chosen
//    - said() -> Said

// Walk — the single verification pass's accumulator. It wraps the provider, drives one paged walk per
// referenced log (the provider caches by prefix), and RECORDS the SAIDs of every chain token it consumes plus
// the id-marker snapshots it reconstructs, so the final policy token can BIND them: `consumed_chain_tokens`
// (D2 — the chain -> policy hand-off is tamper-evident) and `snapshots` (NEW-B). `iel` / `kel` / `sel` return
// the verified token AND register its SAID; `register(said)` binds an externally-fetched token's SAID (e.g.
// the gate context's SEL token); the convenience methods `snapshot_as_of(prefix, marker)` and
// `tip(prefix)` consume the IEL token AND record the reconstructed snapshot (NEW-B); `fold` absorbs a
// sub-evaluation's accumulated tokens + snapshots (so a multi-party walk carries every sub-walk's proven
// facts); `consumed_tokens()` / `snapshots()` drain them when the entry point builds its result. SAD content
// (policy text, rosters-as-SADs) is fetched by the free, content-addressed `sadd_fetch` — trusted by SAID,
// NOT a chain token, so it never enters `consumed_chain_tokens`.
struct Walk<'p, P: VerificationProvider> {
    provider: &'p P,
    consumed: BTreeSet<Said>,            // SAIDs of consumed *Verification tokens (D2)
    snapshots: Vec<IelStateSnapshot>,    // id-marker snapshots reconstructed on this walk (NEW-B)
}
```

### Policy-verification tokens

A satisfied evaluation yields a **proof token**, never a bare `true` — token-existence *is* the proof of
satisfaction, type-enforced from the evaluator outward. The token splits by mode so an *anchored-validity*
proof and a *current-control* proof are **distinct types** (a swap is compile-impossible), and each binds its
own context.

```rust
// Shared surface across both modes.
pub trait PolicyVerified {
    fn said(&self) -> &Said;            // content digest of the verified result (equal SAID => same result)
    fn policy_said(&self) -> &Said;     // the policy this token proves was satisfied (A — binds the token to THIS policy)
    fn credited(&self) -> &HashSet<Prefix>;   // the distinct parties that satisfied the policy
    fn party_outcomes(&self) -> &HashMap<Prefix, Outcome>;     // per-party result (E1)
    fn consumed_chain_tokens(&self) -> &BTreeSet<Said>;        // SAIDs of the *Verification tokens this walk consumed
}

// E1 — per-party outcome. A single party's chain-verification failure is SOFT (-> Unverifiable, uncredited,
// not a global Err); the policy threshold then runs over the Credited set. A CONSUMER may apply a stricter
// rule by reading `party_outcomes` (e.g. the creds feature's `verify_credential` requires EVERY committed
// issuer to be Credited, not just the threshold). STRUCTURAL failures (leftover pins, max_depth, a NEW-B
// roster desync, a misplaced `dev`) stay HARD `Err` — they are policy-validity / adversarial-pinning errors,
// not a party's bad luck. Fail-secure: softening can only SHRINK the credited set, never validate spuriously.
pub enum Outcome { Credited, Unverifiable, Unsatisfied }

// Anchored-mode proof: a policy was satisfied AS-OF pinned state against verified chains.
pub struct AnchoredPolicyVerification {
    said: Said,
    policy_said: Said,                       // (A) binds the token to THIS policy
    credited: HashSet<Prefix>,
    anchored_saids: BTreeSet<Said>,          // the generic `anchors_to_check` proven on the surviving branch
    snapshots: Vec<IelStateSnapshot>,        // the Evl/Icp-marker state snapshots the walk reconstructed (NEW-B)
    party_outcomes: HashMap<Prefix, Outcome>,    // (E1)
    consumed_chain_tokens: BTreeSet<Said>,       // binds the chain -> policy hand-off into this result's SAID (D2)
}

// Current-mode proof: a party presently controls a policy, proven over a fresh challenge at tip.
pub struct CurrentPolicyVerification {
    said: Said,
    policy_said: Said,                       // (A)
    challenge: Digest256,                    // (A) NON-Optional — always present in current mode
    credited: HashSet<Prefix>,
    party_outcomes: HashMap<Prefix, Outcome>,    // (E1)
    consumed_chain_tokens: BTreeSet<Said>,       // (D2)
}

impl AnchoredPolicyVerification {
    pub fn is_said_anchored(&self, said: &Said) -> bool { self.anchored_saids.contains(said) }  // anchored-mode only
    pub fn anchored_saids(&self) -> &BTreeSet<Said> { &self.anchored_saids }
    pub fn snapshots(&self) -> &[IelStateSnapshot] { &self.snapshots }
    // `new` is crate-private (no public constructor): verifier-only construction is the guarantee. It derives
    // the content SAID over the verified result INCLUDING `policy_said` (A) and `consumed_chain_tokens` (D2).
    fn new(policy_said: Said, credited: HashSet<Prefix>, anchored_saids: BTreeSet<Said>,
           snapshots: Vec<IelStateSnapshot>, party_outcomes: HashMap<Prefix, Outcome>,
           consumed_chain_tokens: BTreeSet<Said>) -> Self { /* … derive said over all fields … */ }
}
impl CurrentPolicyVerification {
    pub fn challenge(&self) -> &Digest256 { &self.challenge }   // current-mode only — always present (A)
    // crate-private; derives the SAID INCLUDING `policy_said` + `challenge` (A) + `consumed_chain_tokens` (D2).
    fn new(policy_said: Said, challenge: Digest256, credited: HashSet<Prefix>,
           party_outcomes: HashMap<Prefix, Outcome>, consumed_chain_tokens: BTreeSet<Said>) -> Self { /* … */ }
}
// Both implement PolicyVerified (said / policy_said / credited / party_outcomes / consumed_chain_tokens).
```

- **Why two types, not one.** A function taking `&AnchoredPolicyVerification` is compiler-guaranteed an
  *anchored-validity* proof; one taking `&CurrentPolicyVerification`, a *current-control* proof. The swap is
  compile-impossible — no runtime `debug_assert!` guarding `is_said_anchored(...)` vs `challenge().is_some()`.
  The modes also carry genuinely different evidence (anchored: `anchored_saids` + marker snapshots; current: a
  bound `challenge`), so one struct with mode-empty Optionals would let a consumer call `is_said_anchored()` on
  a current token and silently get `false`.
- **Fields are PRIVATE with no public constructor.** The ONLY way to obtain a token is to run a verifier to a
  satisfied result; the SAID is derived over the verified result **including** `policy_said` (+ `challenge` in
  current mode) and `consumed_chain_tokens`, so an equal SAID means the same policy + challenge + credited set
  + anchored SADs + snapshots + consumed chain tokens. Verifier-only construction is the whole guarantee
  (mirrors the kels `KelVerification` precedent).
- **`consumed_chain_tokens` is the D2 verify-before-use proof.** Each evaluator folds the SAIDs of the chain
  tokens it consumed into its own result SAID, so the chain -> policy hand-off is itself tamper-evident: the
  policy proof binds *which verified chain states* it read.

```rust
// Hard cap on caller-supplied items a verifier will consider in one evaluation: presented parties (anchored
// mode), and BOTH claimed delegates and presented attestations (current mode — each dev(K) leaf verifies
// against every matching attestation, so the set is an amplifier). Refused up front, at the trust boundary,
// before any chain work — an unbounded presented set cannot amplify cost. See §Boundedness.
const MAX_PRESENTED: usize = 128;

// Gate context — where a foreign `grp(X, group)`'s X-state-marker comes from. It is ALWAYS context-supplied,
// never invoker-chosen — the structural fix for the ex-member backdate on the foreign-`grp` arm (the
// `id(issuer)` arm is closed separately by the floored registry-SEL composition; see pinning.md). Three cases (Copy: it threads
// unchanged through the recursive composer arms):
#[derive(Clone, Copy)]
pub enum GateContext<'a> {
    SelGate(&'a SelVerification),  // anchored governance gate: the marker is this SEL's tracked, FLOORED policyPin entry for X (D3b)
    Tip,                           // current mode: resolve X's roster at X's TIP (the live read-time proof)
    None,                          // anchored party-auth walk: a foreign `grp` credits NOBODY (no context marker; fail-secure)
}

// Governance gate (public) — evaluate ONE del-free policy against ONE pinning, resolving leaves AS-OF the
// pinned state. This is what an IEL / SEL governance gate calls (gating an Evl / Ixn / Est against the
// chain's tracked, floored policyPin). Consumes `pinning.pins` positionally in pre-order walk order: a
// single cursor advances one slot per leaf the walk reaches. After the walk any LEFTOVER pins are a malformed
// pinning and deny (`Err`). A foreign `grp(X, group)` resolves X's roster from `gate_context` (D3b) — the
// gating SEL's floored policyPin, never the pinning's invoker-set value; with `GateContext::None` a foreign
// `grp` credits nobody. `anchors_to_check` rides the walk so the gated event's SAID(s) are checked on the
// surviving branch at the required tier (a nested `pol` inherits it). The deep per-event evidence pinning the
// gate constructs from the shallow policyPin + the gated event's anchors is SEL-primitive (layer-4) detail;
// this evaluator is the layer-3 mechanism it calls. Returns Ok(Some(AnchoredPolicyVerification)) on
// satisfaction, Ok(None) on a clean miss, Err on a structural failure (leftover pins, max_depth, misplaced
// `dev`, NEW-B roster desync).
pub fn evaluate_gate_policy(
    policy: &Policy,
    pinning: &Pinning,
    anchors_to_check: &HashSet<(Said, Tier)>,
    gate_context: GateContext,
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<AnchoredPolicyVerification>, PolicyError>;

// Multi-party anchored validity (public) — do enough DISTINCT presented parties satisfy `policy`, each
// anchoring the `anchors_to_check` SADs on its own authentication (surviving branch, required tier)? Each
// presented party carries its own anchor pinning. `del(X, N)` placeholders are matched by parties that
// self-traverse UP their own delegation chain to `X` within `N` hops (delegation is for scaling; every hop
// authorized + consented + un-rescinded to the delegator's tip). A foreign `grp` here credits NOBODY (no
// gate context — group authority is supplied only through a SEL gate, above). NO credential coupling: the
// anchors are GENERIC `(Said, Tier)` pairs, and there is no committed-issuer set, no withdrawal, no immune —
// those are creds-feature concerns (see *Credentials are a feature*). E1: a single party's chain-verification
// failure is SOFT (Unverifiable, uncredited); the threshold runs over the Credited set. The token carries the
// credited set, the anchored SAIDs, the marker snapshots, the per-party outcomes, and the consumed chain
// tokens.
pub fn evaluate_anchored_policy(
    policy: &Policy,
    parties: &[(Prefix, &Pinning)],          // presented parties + their anchor pinnings
    anchors_to_check: &HashSet<(Said, Tier)>,
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<AnchoredPolicyVerification>, PolicyError>;

// Current-state control (public) — challenge-response / fresh-control. Establishes who CURRENTLY controls
// `policy` and confirms they signed `challenge`. Evaluated at the chain TIP (no pinning — tip is implied; no
// anchors — nothing is proven anchored). The bearer presents attestations over `challenge`; each is a signer
// KEL prefix + a primary signature, plus optionally a recovery signature for tier-3 dual-sig contexts. Leaf
// semantics in current mode:
//   - dev(K)         satisfied by an attestation whose signer == K, valid against K's CURRENT signing key
//                    (and recovery key, when required) at K's tip.
//   - id(X) / grp    satisfied by attestation(s) meeting X's authentication at its tip (recurse; one-arg
//                    grp(group) resolves to the enclosing id descent's roster at tip). X is NAMED — no claim
//                    needed; crediting is by the LEAF's prefix, so thr(2, [id(A), id(B)]) counts both
//                    identities even under one controlling key.
//   - grp(X, group)  a foreign roster resolved at X's TIP (the context-supplied marker in the live flow).
//   - del(X, N)      the bearer NAMES the delegate IEL D it acts as (presented in `named_delegates`, capped at
//                    128 — del is non-enumerable and there is no document to carry the name); credit each
//                    DISTINCT named D whose attestations meet D's authentication at tip AND that self-traverses
//                    up to X within N hops (delegation valid to tip, F).
// `required_tier` here is a requirement on the ATTESTATION SHAPE (which signatures must be present and valid),
// not an anchoring-event tier. `challenge` must be unpredictable, single-use, and context-bound (see *Verifier
// behavior — challenge binding*). Both `attestations` and `named_delegates` are refused up front if longer
// than MAX_PRESENTED. The token carries the credited prefixes (no anchored SAIDs, no snapshot — current mode
// reads the tip live), the per-party outcomes, the bound challenge, and the consumed chain tokens.
pub struct Attestation {
    signer: Prefix,                          // signer's KEL prefix
    signature: Signature,                    // signature by current signing key
    recovery_signature: Option<Signature>,   // signature by current recovery key (tier-3)
}

pub fn evaluate_current_policy(
    policy: &Policy,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],              // claimed delegate IELs for del(X, N) leaves; capped at 128, empty
                                             // when the policy has no del
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<CurrentPolicyVerification>, PolicyError>;
```

All three entry points are **policy verifiers**: a satisfied evaluation yields a proof token, not a bare
`true`. `evaluate_gate_policy` returns `Ok(Some(token))` iff the pinned, del-free policy is satisfied
as-of the pinned state with every `anchors_to_check` SAID hosted at its tier on the surviving branch;
`evaluate_anchored_policy` returns `Ok(Some(token))` iff enough distinct presented parties satisfy `policy`
(each self-traversing any `del` within depth and anchoring the named SADs); `evaluate_current_policy` returns
`Ok(Some(token))` iff the attestations over `challenge` cover `policy`'s leaves at current chain state with
the required attestation shape. All return `Ok(None)` for a clean unsatisfied — including an unknown
primitive, which fails the **whole** policy closed (see *Verifier behavior*); `Err(_)` for malformed inputs /
verification failures, including leftover pins (more pins than the policy has occurrences), an over-cap
presented set, a `max_depth` breach, a NEW-B roster desync, or a misplaced `dev`. Token-existence *is* the
proof of satisfaction — a caller holding a token cannot have reached it on an unsatisfied policy.

### General governance-gate + current-control example

A typical authorization composes two checks, each answering a different question, each yielding a **distinct**
token type:

```rust
// 1. GOVERNANCE GATE — is this chain event authorized by the chain's own governance/operation policy,
//    resolved AS-OF the chain's tracked, FLOORED policyPin? The gating event's anchors supply the evidence;
//    the SEL's policyPin supplies the membership snapshot; a foreign `grp(X, g)` in the policy resolves X's
//    roster from the SEL's floored policyPin via the gate context (D3b). On satisfaction it yields an
//    AnchoredPolicyVerification. (A SEL `Evl` is gated by `governance`, an `Ixn`/`Est` by `operation`;
//    constructing the deep pinning from the policyPin is the SEL primitive's job — layer 4.)
let sel = provider.verify_sel(&sel_prefix)?;                       // the gating SEL's verified token (carries the floored policyPin)
let event_anchor: HashSet<(Said, Tier)> =
    [(event.said, Tier::Two)].into_iter().collect();        // the Evl's own SAID, anchored per governance member
let Some(gate) = evaluate_gate_policy(
    &governance_policy,
    &governance_pinning,                                    // the deep evidence pinning the SEL gate built from the policyPin + the event's anchors
    &event_anchor,
    GateContext::SelGate(&sel),                             // foreign `grp` markers come from the SEL's floored policyPin (D3b)
    provider,
    Tier::Two,
    16,
)? else {
    return Ok(false);                                       // not authorized under the chain's current governance
};

// 2. CURRENT-CONTROL — does whoever is acting presently control the identity? Challenge-response at tip.
//    Yields a CurrentPolicyVerification. The challenge defeats replay.
let identity_policy = parse_policy(&format!("id({})", actor))?;
let Some(control) = evaluate_current_policy(
    &identity_policy,
    challenge,
    attestations,
    &[],                                                    // no `del` in id(actor) -> no claimed delegates
    provider,
    Tier::One,
    16,
)? else {
    return Ok(false);                                       // acted on by someone who isn't the actor
};

// 3. A consumer composes the two TYPED tokens — e.g. mints a capability. The two distinct token types make it
//    compile-impossible to pass a current-control proof where an anchored-validity proof is required, and vice
//    versa. The verified facts ride in the tokens (no re-fetch, no TOCTOU): `gate.credited()` /
//    `gate.is_said_anchored(&event.said)` name the authorizing parties; `control.challenge()` confirms the
//    live proof is over THIS request's challenge.
Ok(grant(&gate, &control))

// The ONLY path to a grant — it cannot be called without BOTH typed tokens in hand, so a caller that skipped
// a check simply has no token to pass.
fn grant(gate: &AnchoredPolicyVerification, control: &CurrentPolicyVerification) -> bool { /* application policy */ }
```

The two checks are deliberately separable: the **governance gate** is about *authority as authored* (it reads
pinned events on the verification walk, says nothing about who is acting now); **current control** is about
*the actor now* (live attestations over a fresh challenge at tip, says nothing about past authorization).
Splitting them keeps each failure mode independent.

### Implementation

```rust
// evaluate_gate_policy — positional pin-walk over ONE del-free policy. A single cursor advances one slot
// per leaf the walk reaches; consumption is driven by the STRUCTURAL walk, not by satisfaction (a failed leaf,
// and a present-but-unsatisfied `id` whose subtree still drains, cannot desync later slots). After the walk
// any LEFTOVER pins are a malformed pinning and deny. On satisfaction it emits an AnchoredPolicyVerification —
// the SAD(s) this walk proved anchored, the id-marker snapshot(s) it reconstructed, and the chain tokens it
// consumed. Ok(None) => the policy is unsatisfied.
pub fn evaluate_gate_policy(
    policy: &Policy,
    pinning: &Pinning,
    anchors_to_check: &HashSet<(Said, Tier)>,
    gate_context: GateContext,
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<AnchoredPolicyVerification>, PolicyError> {
    let mut walk = Walk::new(provider);          // tracks consumed chain-token SAIDs + reconstructed snapshots
    if let GateContext::SelGate(sel) = gate_context {
        walk.register(sel.said());               // bind the gate's SEL token into the result SAID (D2)
    }
    let mut cur = PinCursor::new(&pinning.pins);  // positional; `take_next()` advances one slot
    // Seed dev_legal=false (DQ2): this walk's top-level policy is a GENERAL construction (a governance gate,
    // a nested `pol`), never a singleton's own dev-policy evaluated top-level. A `dev` becomes legal only when
    // satisfies_id DESCENDS into a singleton's authentication. (A future singleton self-gating entry that
    // evaluates a singleton's OWN policy top-level would seed true — D2-B — but evaluate_gate_policy is
    // never that entry.)
    let credited = eval_expr(&policy.expr, &mut cur, anchors_to_check, None, gate_context,
                             &mut walk, required_tier, max_depth, false)?;
    if cur.remaining() > 0 {
        return Err(PolicyError::LeftoverPins);   // more pins than occurrences — malformed
    }
    if credited.is_empty() {
        return Ok(None);                         // policy unsatisfied
    }
    // Satisfied. The walk proved every `anchors_to_check` SAID hosted at its tier on the surviving branch and
    // reconstructed the id-marker snapshot(s) (NEW-B); both ride in the token, along with the SAIDs of the
    // chain tokens consumed (D2 — binds the chain -> policy hand-off into the result SAID).
    let anchored_saids = anchors_to_check.iter().map(|(said, _)| said.clone()).collect();
    let outcomes = credited.iter().map(|p| (p.clone(), Outcome::Credited)).collect();
    Ok(Some(AnchoredPolicyVerification::new(
        policy.said.clone(), credited, anchored_saids, walk.snapshots(), outcomes, walk.consumed_tokens(),
    )))
}

// evaluate_anchored_policy — multi-party anchored validity, runs inline on the verification walk. Each
// presented party is checked two independent ways:
//   (a) ANCHOR — its anchor pinning proves the `anchors_to_check` SADs are anchored on the party's OWN
//       authentication (surviving branch, required tier), via `id(party)`.
//   (b) DELEGATION — it self-traverses UP its own delegation chain to a delegator `policy` names, within
//       that placeholder's depth.
// The policy's composers then count DISTINCT anchored parties per `del(X, N)` / `id(X)`. E1: a party whose
// chain verification fails is recorded Unverifiable (uncredited, SOFT) and the threshold runs over the
// Credited set; STRUCTURAL failures propagate HARD. NO credential coupling.
pub fn evaluate_anchored_policy(
    policy: &Policy,
    parties: &[(Prefix, &Pinning)],
    anchors_to_check: &HashSet<(Said, Tier)>,
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<AnchoredPolicyVerification>, PolicyError> {
    if parties.len() > MAX_PRESENTED {           // K <= 128 — up-front trust-boundary pre-check, zero chain work
        return Err(PolicyError::TooManyParties);
    }
    if parties.is_empty() {
        return Ok(None);                         // nothing to anchor or delegate-check
    }
    let mut walk = Walk::new(provider);
    let mut outcomes: HashMap<Prefix, Outcome> = HashMap::new();

    // (a) Anchor proof per party. `id(party)` walks to the party's `Evl`/`Icp` state-marker and, through its
    // reconstructed authentication, the anchoring KEL(s); `anchors_to_check` rides this walk so the anchor is
    // checked on the PARTY'S authentication (surviving branch, required tier) — never on a chain a `del`
    // placeholder names. GateContext::None: a foreign `grp` in a party's own authentication credits nobody (no
    // gate). E1: a ChainUnverifiable error for this party -> Unverifiable (soft); structural errors propagate.
    let mut anchored: Vec<&Prefix> = Vec::new();
    for (party, anchor_pinning) in parties {
        let party_id = parse_policy(&format!("id({})", party))?;
        match evaluate_gate_policy(&party_id, anchor_pinning, anchors_to_check,
                                     GateContext::None, provider, required_tier, max_depth) {
            Ok(Some(token)) => {
                walk.fold(token);                          // fold its snapshots + consumed tokens
                anchored.push(party);
                outcomes.insert((*party).clone(), Outcome::Credited);
            }
            Ok(None) => { outcomes.insert((*party).clone(), Outcome::Unsatisfied); }
            Err(PolicyError::ChainUnverifiable) => {       // E1 SOFT — this party's chain didn't verify
                outcomes.insert((*party).clone(), Outcome::Unverifiable);
            }
            Err(e) => return Err(e),                       // structural — HARD
        }
    }

    // (b) + composition. Evaluate `policy`: each `del(X, N)` is matched by the distinct anchored parties that
    // self-traverse up to `X` within `N` hops; `id(X)` is matched against the anchored set; a foreign `grp`
    // credits NOBODY (no gate context here). Composers count DISTINCT prefixes; `pol` recurses; `dev` is a
    // misplaced-dev hard reject (DQ2). The multi-party policy reads no chain state THROUGH itself, so it carries
    // no pinning of its own — the per-party anchor pinnings are consumed inside each `evaluate_gate_policy`,
    // where leftover pins deny.
    let credited = anchored_credited(&policy.expr, &anchored, &mut walk, max_depth)?;
    if credited.is_empty() {
        return Ok(None);
    }
    // Satisfied. anchored_saids fold up from the per-party walks (anchors proven on the surviving branch).
    Ok(Some(AnchoredPolicyVerification::new(
        policy.said.clone(), credited,
        anchors_to_check.iter().map(|(s, _)| s.clone()).collect(),
        walk.snapshots(), outcomes, walk.consumed_tokens(),
    )))
}

// Self-traversal: does `candidate` reach `delegator` walking UP its own delegation chain within `max_hops`
// hops? No delegation path is carried — each link self-records its parent, so the verifier reconstructs the
// chain from the candidate alone, reading IelVerification tokens. At each hop:
//   - read the lower link's self-recorded `delegating` — its `Icp.delegating` (the parent prefix) and its
//     serial-1 `Evl.delegating` (the parent's `Del`-event SAID) — both CONSENT;
//   - direct-look-up that event on the parent's IEL (no enumeration). It MUST resolve to a `Del` — `del_event`
//     REJECTS any other kind. Both `Del` and `Rsc` carry a `delegated` list (`Del` ADDS, `Rsc` REMOVES);
//     reading authorization off a `Rsc` would invert the check. Confirm the `Del` lists the lower link in its
//     ADDITIONS and resolves to the consented parent prefix;
//   - walk the parent IEL to TIP confirming no `Rsc` of the lower link (F — ALWAYS, even for an immune
//     credential; immune scopes to the creds withdrawal scan only, never this walk). The `Del`-kind constraint
//     and the tip-walk are independent — defense in depth.
// Bounded by `min(max_hops, max_depth)`; reaching neither `delegator` nor a valid parent denies.
fn self_traverses(
    candidate: &Prefix,
    delegator: &Prefix,
    max_hops: u32,
    walk: &mut Walk,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    let mut lower = candidate.clone();
    for _hop in 0..max_hops.min(max_depth) {
        let lower_iel = walk.verify_iel(&lower)?;                     // consumes the IelVerification token
        let parent = lower_iel.delegating_prefix()?;           // lower.Icp.delegating (consent)
        let del_said = lower_iel.delegating_del_said()?;       // lower.Evl[1].delegating (consent back-pointer)
        let parent_iel = walk.verify_iel(&parent)?;
        let del = parent_iel.del_event(&del_said)?;            // direct lookup; MUST be a `Del` (not `Rsc`)
        if del.host != parent || !del.lists(&lower) {          // authorization: the Del ADDS `lower`
            return Ok(false);
        }
        if parent_iel.rescinded_by_tip(&lower) {               // F — walk parent to tip; any Rsc denies
            return Ok(false);
        }
        if parent == *delegator {
            return Ok(true);                                   // reached the named delegator in <= N hops
        }
        lower = parent;
    }
    Ok(false)                                                  // ran out of hops without reaching `delegator`
}

// ── dev-placement enforcement (DQ2) ──────────────────────────────────────────────────────────────
// The `dev`-placement rule ("a bare `dev` is legal ONLY inside a singleton IEL's own three policies;
// forbidden in every general / composed policy") is enforced HERE — at the VERIFIER, at EVALUATION, over the
// FULLY-`pol`-EXPANDED graph — never as an author/submit-time convention. The policy may be authored by an
// UNTRUSTED party (an attacker-set `readPolicy` / `pol(said)` -> a `dev`-bearing SAD, a creds-feature
// withdrawal policy); only the verifier is the trust boundary, so the check rides the ONE eval walk (NOT a
// separate `validate_policy` pass — that would re-walk chains to re-derive singleton-ness and open a TOCTOU
// seam). `dev_legal` is a context flag threaded through that walk:
//   - SEEDED false at every general entry (the governance gate, a `readPolicy`, the `id(party)` anchor
//     wrapper). A singleton evaluating its OWN governance/operation as a TOP-LEVEL policy seeds it TRUE
//     (caller-supplied: the caller KNOWS it is a singleton's own policy — trustworthy context, D2-B), or wraps
//     the check in `id(singleton)`;
//   - flips TRUE only when the walk DESCENDS INTO A SINGLETON's authentication (satisfies_id, and
//     current_credited's `id`/`del` arms, know roster-presence at the descent point) — the ONE legitimate base case;
//   - INHERITED UNCHANGED through `thr`/`wgt`/`and`/`pol`. A singleton's own policy CANNOT use `pol`
//     (iel-policy-structure.md), so the flag is NEVER carried true into a `pol`; therefore a `dev` reached via
//     `pol(said)` — from ANY source — always has dev_legal=false -> rejected. This is what makes
//     "fully-`pol`-expanded" sound: `pol` only propagates context; the check sits in the `dev` arm.
// A misplaced `dev` is a policy-VALIDITY error: `check_dev_placement` returns Err, which `?` propagates to the
// entry point so the WHOLE policy denies (hard, fail-closed) — NOT credit-nobody, which would let a sibling
// leg of `thr(1, [dev(K_bad), id(legit)])` clear the gate via the other leg.
fn check_dev_placement(dev_legal: bool) -> Result<(), PolicyError> {
    if dev_legal {
        Ok(())
    } else {
        Err(PolicyError::MisplacedDev)   // verifier-enforced placement, fail-closed (whole policy denies)
    }
}

// anchored_credited — returns the set of distinct parties `expr` credits if satisfied, else the empty set, so
// a containing composer dedups by prefix when it unions children. Multi-party anchored evaluation accepts
// DELEGATED parties (`del(X, N)` — anchored parties self-traversing up to `X` within `N`) and DIRECT named
// parties (`id(X)` — anchored parties matching the named prefix). A foreign `grp(prefix, group)` credits
// NOBODY here (no gate context — group authority is supplied only through a SEL gate). `pol` recurses;
// `thr`/`wgt`/`and` compose (union / max-weight / conjunction) over DISTINCT prefixes. `dev` is a
// misplaced-dev hard reject (DQ2 — this evaluator never descends a singleton authentication, so dev_legal is
// invariantly false). It reads no chain state THROUGH the policy and consumes no pin slots.
fn anchored_credited(
    expr: &PolicyExpr,
    anchored: &[&Prefix],
    walk: &mut Walk,
    max_depth: u32,
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // del(X, N): every anchored party self-traversing up to X within N hops. Never expanded.
        PolicyExpr::Del(delegator, n) => {
            let mut set = HashSet::new();
            for party in anchored {
                if self_traverses(party, delegator, *n, walk, max_depth)? {
                    set.insert((*party).clone());
                }
            }
            Ok(set)
        }
        // id(X): credit {X} iff X is a DIRECT named party — it anchored the SAD itself (no delegation hop).
        PolicyExpr::Id(prefix) => Ok(if anchored.iter().any(|a| **a == *prefix) {
            HashSet::from([prefix.clone()])
        } else {
            HashSet::new()
        }),
        // grp(prefix, group): a foreign roster splice credits NOBODY in the multi-party path — there is no gate
        // context here, and an invoker-chosen marker is exactly the ex-member exposure the design forecloses on
        // this (foreign-`grp`) arm. The id(issuer) arm is closed by the floored registry-SEL composition.
        // (Foreign-`grp` authority is supplied only through a SEL gate — evaluate_gate_policy with
        // GateContext::SelGate, D3b.) The one-arg own-form grp(group) likewise credits nobody (no host
        // context — this evaluator never descends an `id`). Fail-secure.
        PolicyExpr::Grp(_, _) => Ok(HashSet::new()),
        // pol(said): recurse (pure factoring — propagate the nested credited set; decrement depth).
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            anchored_credited(&nested.expr, anchored, walk, max_depth - 1)
        }
        // thr(M, …): union the credited children; met iff >= M distinct, then return the union. Decrement on
        // every composer (depth bounded across the composer tree too).
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for sub in subs {
                union.extend(anchored_credited(sub, anchored, walk, max_depth - 1)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt(M, …): per-party weight, dedup-by-max across branches — a party matching several `del`
        // placeholders is credited once at its MAX weight, distinct parties summed; met iff sum >= M.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (sub, w) in weighted {
                for p in anchored_credited(sub, anchored, walk, max_depth - 1)? {
                    best.entry(p).and_modify(|cur| *cur = (*cur).max(*w)).or_insert(*w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and(…): conjunction — every child must credit >= 1 party; on success return the union, else ∅
        // (separation of duties; distinct only over disjoint pools — see §`and`). Every child is evaluated.
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = anchored_credited(child, anchored, walk, max_depth - 1)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // dev(K): FORBIDDEN in a multi-party policy — parties are IELs; the distinct count is over IEL
        // prefixes. This evaluator never descends a singleton's authentication, so dev_legal is invariantly
        // FALSE here — the shared placement check HARD-REJECTS (DQ2). Fail-closed.
        PolicyExpr::Dev(_) => {
            check_dev_placement(false)?;     // always Err here — a general policy
            Ok(HashSet::new())               // unreachable
        }
    }
}

// eval_expr — the positional pin-walk for a single anchored policy. `cur` is a SINGLE positional cursor; each
// leaf takes the NEXT slot when the walk reaches it. Consumption is driven by the STRUCTURAL walk, not by
// satisfaction. Returns the SET of distinct prefixes this expression CREDITS if satisfied, else ∅. A satisfied
// leaf credits the prefix it authenticates — `dev(K)`->K, `id(X)`->X — where the prefix comes from the
// STRUCTURE, not the pin. A composer returns the UNION of its children's credited sets iff its threshold is
// met (else ∅); `wgt` keeps each prefix's MAX weight, summed once. Dedup is RECURSIVE — a prefix counts ONCE
// toward every ancestor. An `id` boundary is OPAQUE: `id(X)` credits `{X}`, never X's internal members.
// `max_depth` bounds `pol`/`id` recursion; a breach denies. `gate_context` supplies a foreign `grp`'s marker.
fn eval_expr(
    expr: &PolicyExpr,
    cur: &mut PinCursor,
    anchors_to_check: &HashSet<(Said, Tier)>,
    self_context: Option<HostContext>,
    gate_context: GateContext,
    walk: &mut Walk,
    required_tier: Tier,
    max_depth: u32,
    dev_legal: bool,                                 // DQ2: true only inside an id->singleton descent
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // dev: VERIFIER-ENFORCED PLACEMENT (DQ2). Legal ONLY as the base case of an id->SINGLETON descent
        // (dev_legal=true); a bare `dev` in any general / composed position (incl. via `pol(said)` -> a
        // `dev`-bearing SAD from any source) is a policy-validity error — `check_dev_placement` HARD-REJECTS
        // and the WHOLE policy denies (never credit-nobody). On the LEGAL path: take this leaf's slot; a
        // present SAID names the event just-prior to the anchoring event — resolve its surviving-branch child
        // and check the anchor + tier; a null/exhausted slot consumes the slot and credits nobody.
        PolicyExpr::Dev(prefix) => {
            check_dev_placement(dev_legal)?;
            match cur.take_next() {
                Some(Some(prior_said)) => {
                    if satisfies_dev(&prior_said, prefix, anchors_to_check, walk, required_tier)? {
                        Ok(HashSet::from([prefix.clone()]))
                    } else {
                        Ok(HashSet::new())
                    }
                }
                _ => Ok(HashSet::new()),             // null slot / exhausted — slot still consumed
            }
        }
        // id: take this leaf's slot (the Evl/Icp state-marker). A present SAID fixes the IEL's state;
        // reconstruct the snapshot as-of it and recurse into the snapshot's authentication, threading the host
        // context = prefix so an aggregate member's one-arg `grp(group)` resolves against the SAME snapshot's
        // roster (NEW-B), draining the subtree's slots even if the member fails. Satisfied => credit {prefix}
        // (opaque boundary — X's internal members do NOT propagate). A null slot consumes ONE slot and does
        // NOT descend (the state-marker is un-evidenced — see *Pinning -> Issuer-side construction*).
        PolicyExpr::Id(prefix) => match cur.take_next() {
            Some(Some(marker_said)) => {
                if satisfies_id(&marker_said, prefix, cur, anchors_to_check, gate_context,
                                 walk, required_tier, max_depth)? {
                    Ok(HashSet::from([prefix.clone()]))
                } else {
                    Ok(HashSet::new())
                }
            }
            _ => Ok(HashSet::new()),
        },
        // pol: dereference + recurse; pure factoring — propagate the nested credited set UNCHANGED.
        // `anchors_to_check`, `self_context`, `gate_context`, and `dev_legal` are inherited UNCHANGED — and
        // since a singleton's own policy can't use `pol`, dev_legal is never carried TRUE into a `pol`, so a
        // `dev`-bearing SAD reached here always sees dev_legal=false -> rejected (DQ2).
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, cur, anchors_to_check, self_context, gate_context,
                      walk, required_tier, max_depth - 1, dev_legal)
        }
        // thr: evaluate every element (Grp children expand inline into id(member) leaves — see `flatten`).
        // A one-arg `grp(group)` resolves against the enclosing id(X) marker's frozen roster snapshot (NEW-B);
        // a foreign two-arg `grp(prefix, group)` resolves X's roster from the `gate_context` marker (D3b — the
        // gating SEL's floored policyPin; GateContext::None credits nobody). Members flatten in canonical
        // order. UNION the children; met iff >= M DISTINCT prefixes, then return the union (recursive dedup).
        // `del` is not a single-policy element (no slot, no self-traversal here): it appears only in the
        // multi-party policy, evaluated by `anchored_credited`.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, gate_context, walk)? {
                union.extend(eval_expr(&child, cur, anchors_to_check, self_context, gate_context,
                                       walk, required_tier, max_depth - 1, dev_legal)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt: per-prefix MAX weight across branches (associative/commutative -> order-independent;
        // fail-secure vs. sum — one party can't stack roles' weight), each distinct prefix summed once; met iff
        // `sum >= M`, then return the credited prefixes.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (child, w) in flatten_weighted(weighted, self_context, gate_context, walk)? {
                for p in eval_expr(&child, cur, anchors_to_check, self_context, gate_context,
                                   walk, required_tier, max_depth - 1, dev_legal)? {
                    best.entry(p).and_modify(|e| *e = (*e).max(w)).or_insert(w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and: separation of duties — evaluate EVERY child (no short-circuit; children must drain their pin
        // slots for cursor determinism). Satisfied iff ALL children's credited sets are non-empty; then return
        // their UNION (so an enclosing threshold still counts distinct parties), else ∅. Distinct SATISFIERS
        // are guaranteed only when the branches draw from disjoint identity pools — see §`and`.
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = eval_expr(child, cur, anchors_to_check, self_context, gate_context,
                                         walk, required_tier, max_depth - 1, dev_legal)?;
                if credited.is_empty() {
                    all_satisfied = false;            // keep draining the remaining children's slots
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // del / grp standing alone are not valid `expr` (bracket-only) — fail-secure.
        _ => Ok(HashSet::new()),
    }
}

// dev(prefix): the SAD is anchored on this KEL. `prior_said` names the event JUST BEFORE the anchoring event —
// the anchoring event commits to the SAD, so its own SAID is unconstructable here (the SAID-cycle note).
// Resolve the anchoring child `s` on the SURVIVING branch (`s.previous == prior_said`) off the KelVerification;
// an anchor on a divergent or later-archived branch is invalid (per kel/reconciliation.md, merge.md), so a
// missing surviving-branch child denies. Check every required anchor is hosted at its tier floor and `s` clears
// `required_tier`.
fn satisfies_dev(
    prior_said: &Said,
    leaf_prefix: &Prefix,
    anchors_to_check: &HashSet<(Said, Tier)>,
    walk: &mut Walk,
    required_tier: Tier,
) -> Result<bool, PolicyError> {
    let kel = walk.verify_kel(leaf_prefix)?;                  // consumes the KelVerification token
    let s = match kel.anchoring_child_on_surviving_branch(prior_said)? {
        Some(s) => s,                  // surviving-branch child; validated by the walk
        None => return Ok(false),      // divergent / archived — no valid anchor
    };
    // required_tier is the baseline floor for the hosting event; each required anchor may additionally demand a
    // higher tier (a high-assurance SAD co-anchored with a routine one).
    Ok(
        s.prefix == *leaf_prefix
            && s.tier >= required_tier
            && anchors_to_check.iter().all(|(anchor, tier)| s.anchors.contains(anchor) && s.tier >= *tier)
    )
}

// id(prefix): `marker_said` pins the IEL's most-recent `Evl`/`Icp` **state-marker** — NOT an anchoring event,
// so it carries no anchor and needs no prior-event trick. The verifier reconstructs X's **state snapshot**
// (authentication AND roster) AS-OF that marker (NEW-B) off the IelVerification — `Del`/`Rsc` don't move it.
// Satisfaction recurses into the snapshot's authentication (threading the host context = leaf_prefix so a
// member's one-arg `grp(group)` resolves), whose leaves consume the FOLLOWING slots — the anchor is checked at
// the terminal `dev` leaves. A one-arg `grp(group)` in X's authentication reads its roster FROM THIS SAME
// reconstructed snapshot — REUSE of the `id(X)` marker, no second pin — so the authentication-recent /
// roster-stale split is structurally impossible. The descent runs regardless of prefix match so the subtree's
// slots always DRAIN (structural consumption). Returns whether to credit `leaf_prefix` upward — the inner
// credited set (X's members/keys) is X's PRIVATE evidence, consumed at this boundary, never propagated.
fn satisfies_id(
    marker_said: &Said,
    leaf_prefix: &Prefix,
    cur: &mut PinCursor,
    anchors_to_check: &HashSet<(Said, Tier)>,
    gate_context: GateContext,
    walk: &mut Walk,
    required_tier: Tier,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    // Reconstruct X's snapshot as-of the marker — authentication AND roster from this one snapshot, off X's
    // IelVerification token (consumes the token, records the snapshot for the result — NEW-B).
    let snapshot = walk.snapshot_as_of(leaf_prefix, marker_said)?;   // validated by the walk
    let authentication = parse_policy_sad(&sadd_fetch(&snapshot.authentication)?)?;
    // The descent threads `leaf_prefix` as the host context, with the roster pinned AT THE MARKER
    // (`AtMarker(&snapshot)`, NEW-B); a one-arg `grp(group)` it reaches resolves against THIS snapshot's roster
    // — reuse of the same marker, not a fresh pin.
    let host = HostContext { prefix: leaf_prefix, roster: RosterSource::AtMarker(&snapshot) };
    // DQ2: dev_legal flips TRUE only when descending into a SINGLETON's authentication (the one legal `dev`
    // placement). `snapshot.is_singleton()` is roster-presence — a singleton has no roster, so its dev-based
    // authentication credits its devs; an AGGREGATE's grp-based authentication descends with dev_legal=false.
    let sub = eval_expr(&authentication.expr, cur, anchors_to_check, Some(host), gate_context,
                        walk, required_tier, max_depth - 1, snapshot.is_singleton())?;  // drains the subtree's slots
    Ok(snapshot.prefix == *leaf_prefix && !sub.is_empty())      // X's authentication met => credit X
}
```

`flatten` / `flatten_weighted` expand each `grp` element to `id(member)` leaves in canonical order, reading the
roster via `self_context` (one-arg) and `gate_context` (foreign two-arg). A **one-arg `grp(group)`** reads the
HOST's roster: `AtMarker(snap)` => `snap.roster` (the frozen marker snapshot, NEW-B); `AtTip` => the host's
live roster (current mode); `None` => credits nobody (no enclosing host). A **foreign two-arg
`grp(prefix, group)`** reads X's roster as-of the **context-supplied** marker, by `gate_context`:

- `SelGate(sel)` (anchored governance gate) => the marker is `sel.policy_pin_marker(prefix)` — the gating SEL's
  floored `policyPin` entry for X (D3b) — reconstructed via `walk.verify_iel(prefix).roster_at(marker, group)`;
- `Tip` (current mode) => X's roster at X's tip (the live read-time context marker);
- `None` (a party's own anchor walk, the multi-party path) => a foreign `grp` credits nobody — there is no
  context marker, and an invoker-chosen one is exactly the ex-member exposure the design forecloses on the
  foreign-`grp` arm (the `id(issuer)` arm is closed by the floored registry-SEL composition).

The marker **value** is thus always context-supplied, never the pinning's invoker-set value. The G1
X-state-marker slot is laid and consumed positionally for cursor alignment only (see *Pinning*).

```rust
// Host context for resolving a one-arg `grp(group)` inside an `id(X)` descent (NEW-B): the host prefix plus
// WHERE that host's roster is read. `AtMarker` pins the roster to the `id(X)` marker's reconstructed snapshot
// (FROZEN — reused, no second pin). `AtTip` reads the live roster (current mode). A `None` self_context means
// no enclosing id descent — a one-arg `grp(group)` there credits nobody (fail-secure).
#[derive(Clone, Copy)]
struct HostContext<'a> {
    prefix: &'a Prefix,
    roster: RosterSource<'a>,
}
#[derive(Clone, Copy)]
enum RosterSource<'a> {
    AtMarker(&'a IelStateSnapshot),   // roster frozen at the id(X) Evl/Icp marker (NEW-B)
    AtTip,                            // live roster (tip)
}

// del has NO single-policy helper: `del(X, N)` is never a pinned leaf and never appears in a party's
// authentication. It lives only in the multi-party policy, where `anchored_credited` matches it by
// SELF-TRAVERSAL (`self_traverses`) — walk UP each presented party's own chain to a named delegator, checking
// authorization + consent + no `Rsc` to the delegator's TIP (F, ALWAYS).
```

#### Current-mode evaluation

`evaluate_current_policy` is the third credited-set evaluator — it shares the anchored model and differs only
in **leaf satisfaction** (live attestation at the chain tip vs. the anchored pin-walk). There is no pinning
and nothing is proven anchored; every leaf is checked at the referenced chain's **tip**, read off that chain's
verification token. Composition is identical to `eval_expr` / `anchored_credited`: `thr` = `|distinct-prefix
union| >= M`, `wgt` = per-prefix max-weight summed `>= M`, `and` = all branches non-empty -> union, with the
same recursive dedup. The structural addition is the **named-delegates input**: `del` is non-enumerable and
there is no document to carry the name, so the bearer **names the delegate IEL it acts as**, capped at 128. The
presented **`attestations`** are capped at the same 128: each `dev(K)` leaf verifies against *every* matching
attestation, so an uncapped set is a cost amplifier — refused up front before any chain work. On satisfaction
the entry point returns `Ok(Some(CurrentPolicyVerification))` (credited set + bound challenge + per-party
outcomes + consumed tokens — current mode pins no marker and proves nothing anchored); `Ok(None)` when cleanly
unsatisfied; `Err(_)` on a cap breach or verification failure.

```rust
// Current-state evaluation (challenge-response at the chain TIP). `current_credited` returns the set of
// distinct prefixes an expression credits if satisfied at tip, else ∅; the public entry wraps a non-empty set
// into a CurrentPolicyVerification (Ok(None) if empty). Crediting is by the LEAF's prefix (dev(K)->K,
// id(X)->X), so an id boundary is opaque and distinct identities count even under one controlling key.
pub fn evaluate_current_policy(
    policy: &Policy,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],
    provider: &impl VerificationProvider,
    required_tier: Tier,
    max_depth: u32,
) -> Result<Option<CurrentPolicyVerification>, PolicyError> {
    if attestations.len() > MAX_PRESENTED {          // each dev(K) leaf verifies against EVERY matching
        return Err(PolicyError::TooManyAttestations); // attestation; cap the amplifier up front
    }
    if named_delegates.len() > MAX_PRESENTED {       // K <= 128 — same cap as presented parties; fail-secure
        return Err(PolicyError::TooManyDelegates);
    }
    let mut walk = Walk::new(provider);
    // Seed dev_legal=false (DQ2): a `readPolicy` / application policy / `id(subject)` is a GENERAL policy — a
    // bare `dev` (directly or via `pol(said)`) is rejected; a `dev` becomes legal only when the walk descends
    // into a SINGLETON's authentication.
    let credited = current_credited(&policy.expr, challenge, attestations, named_delegates,
                                    None, &mut walk, required_tier, max_depth, false)?;
    if credited.is_empty() {
        return Ok(None);                             // cleanly unsatisfied
    }
    // Current mode proves nothing anchored and pins no marker, so the token carries only the credited set. It
    // DOES bind the policy SAID and the `challenge` (A), and the consumed chain tokens (D2). Token-existence
    // still proves satisfaction.
    let outcomes = credited.iter().map(|p| (p.clone(), Outcome::Credited)).collect();
    Ok(Some(CurrentPolicyVerification::new(
        policy.said.clone(), challenge.clone(), credited, outcomes, walk.consumed_tokens(),
    )))
}

// Mirrors `eval_expr` / `anchored_credited`; the leaf base cases are live attestation at the tip.
fn current_credited(
    expr: &PolicyExpr,
    challenge: &Digest256,
    attestations: &[Attestation],
    named_delegates: &[Prefix],
    self_context: Option<HostContext>,
    walk: &mut Walk,
    required_tier: Tier,
    max_depth: u32,
    dev_legal: bool,                                 // DQ2: true only inside an id->singleton descent
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // dev(K): VERIFIER-ENFORCED PLACEMENT (DQ2). Legal ONLY as the base case of an id->SINGLETON descent;
        // a bare `dev` in a general policy (application / readPolicy / a creds withdrawal-expr), incl. via
        // `pol(said)`, HARD-REJECTS and the WHOLE policy denies (the attacker-set-`readPolicy` attack — see
        // *Verifier behavior*). On the LEGAL path, credit {K} iff an attestation by K validates against K's
        // CURRENT signing key (and recovery key, per the required_tier ATTESTATION SHAPE) over the challenge.
        // `verify_attestation` returns false for a non-verifying EXTERNAL attestation — junk, not credited, so
        // a flood of bad attestations can't grief the eval into an error — and Err only for a CHAIN-integrity
        // failure, which `?` propagates.
        PolicyExpr::Dev(prefix) => {
            check_dev_placement(dev_legal)?;          // reject a misplaced dev before any verify work
            let kel = walk.verify_kel(prefix)?;
            let mut credited = HashSet::new();
            for a in attestations {
                if a.signer == *prefix && kel.verify_attestation(a, challenge, required_tier)? {
                    credited.insert(prefix.clone());
                    break;
                }
            }
            Ok(credited)
        }
        // id(X): credit {X} iff the attestation set meets X's authentication at X's TIP (recurse, host context
        // = {X, AtTip} — current mode reads the roster LIVE, NEW-B). X is named in the policy. DQ2: dev_legal
        // flips TRUE only when X is a SINGLETON (`tip.is_singleton()`).
        PolicyExpr::Id(prefix) => {
            let tip = walk.tip(prefix)?;
            let auth = parse_policy_sad(&sadd_fetch(&tip.authentication)?)?;
            let host = HostContext { prefix, roster: RosterSource::AtTip };
            let sub = current_credited(&auth.expr, challenge, attestations, named_delegates,
                                       Some(host), walk, required_tier, max_depth - 1, tip.is_singleton())?;
            Ok(if sub.is_empty() { HashSet::new() } else { HashSet::from([prefix.clone()]) })
        }
        // pol: dereference + recurse; propagate the nested credited set unchanged. `dev_legal` is inherited
        // UNCHANGED — never carried true into a `pol`, so a `dev`-bearing SAD reached via `pol(said)` here is
        // rejected (DQ2).
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            current_credited(&nested.expr, challenge, attestations, named_delegates,
                             self_context, walk, required_tier, max_depth - 1, dev_legal)
        }
        // thr: flatten grp at the host (one-arg) / named foreign owner's TIP (two-arg — current mode is
        // tip-live, NEW-B), union the children; met iff >= M distinct.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, GateContext::Tip, walk)? {   // current mode: foreign grp -> X's tip
                union.extend(current_credited(&child, challenge, attestations, named_delegates,
                                              self_context, walk, required_tier, max_depth - 1, dev_legal)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt: per-prefix MAX weight, each distinct prefix summed once; met iff sum >= M.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (child, w) in flatten_weighted(weighted, self_context, GateContext::Tip, walk)? {
                for p in current_credited(&child, challenge, attestations, named_delegates,
                                          self_context, walk, required_tier, max_depth - 1, dev_legal)? {
                    best.entry(p).and_modify(|e| *e = (*e).max(w)).or_insert(w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and: every child must credit >= 1 prefix; on success return the union, else ∅. Evaluate ALL.
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = current_credited(child, challenge, attestations, named_delegates,
                                                self_context, walk, required_tier, max_depth - 1, dev_legal)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // del(X, N): the live analogue of anchored del-matching — NO del-pin. Credit each DISTINCT named
        // delegate D (`named_delegates`) whose attestations meet D's authentication at D's tip AND that
        // self-traverses up to X within N hops (delegation valid to X's TIP, F). DQ2: the descent into D's
        // authentication flips dev_legal TRUE only when D is a SINGLETON.
        PolicyExpr::Del(delegator, n) => {
            let mut set = HashSet::new();
            for d in named_delegates {
                let d_tip = walk.tip(d)?;
                let d_auth = parse_policy_sad(&sadd_fetch(&d_tip.authentication)?)?;
                let d_host = HostContext { prefix: d, roster: RosterSource::AtTip };  // tip-live (NEW-B)
                let met = current_credited(&d_auth.expr, challenge, attestations, named_delegates,
                                           Some(d_host), walk, required_tier, max_depth - 1, d_tip.is_singleton())?;
                if !met.is_empty() && self_traverses(d, delegator, *n, walk, max_depth)? {
                    set.insert(d.clone());
                }
            }
            Ok(set)
        }
        // grp standing alone is bracket-only (flattened inside thr/wgt before reaching here).
        PolicyExpr::Grp(..) => Ok(HashSet::new()),
    }
}
```

(The tip-state token accessors — `tip()`, `verify_attestation` — are illustrative shapes over the settled
event/attestation event-shapes; their exact signatures settle with the forthcoming chain verifiers.)

### Credentials are a feature (forward reference)

Credential validity is **not** part of the policy primitive — credentials are a **feature** (a data feature
that *composes* the primitives), and the dependency points feature -> primitive, never the reverse. A
forthcoming creds feature provides `verify_credential`, which **wraps** `evaluate_anchored_policy`: it reads a
SAID-verified credential's committed issuers + issuance policy + issuance pinning, passes `cred.said` as a
generic anchor-to-check, runs the **withdrawal** scan (the `withdrawal` / `immune` model), and emits a
`CredentialVerification` binding the credential SAID. Because the primitive takes generic anchors, there is no
caller-supplied committed set to mistrust — `verify_credential` reads the committed set from the SAID-verified
credential itself, so the equality assert the interim design carried dissolves; and it enforces the stricter
**every-committed-issuer-Credited** rule by reading the token's `party_outcomes` (E1). The `withdrawal` /
`immune` model, the issuance "use case", and the 3-check `authorize` access flow are all **creds-feature**
content, born in the creds feature. The policy primitive knows nothing about credentials — it provides the
general anchored / current evaluators the feature builds on.

`del` self-traversal stays **here**, in the primitive: delegation is a general DSL leaf (IEL delegation gates
use it too), not a credential concept.
