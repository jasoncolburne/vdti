Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## API Surface

The public evaluation entry points are `evaluate_anchored_policy` (anchored validity of a credential — reads chains via the verification walk) and `evaluate_current_policy` (live challenge-response control). Both run their leaf checks **inline on the verifier's verification walk** (`source`) — the single paged pass each referenced log gets for end-verifiability — and both resolve `del(prefix, N)` by **self-traversal** (no delegation pin: the candidate walks *up* its own delegation chain to the named delegator). There is no separate pure bind phase and no evidence-gathering walk: pins are consumed positionally as the one walk descends (see *Pinning*). `evaluate_single_policy` is the internal pin-walk helper for a del-free sub-policy (the issuer's authentication during the anchor check).

```rust
// Hard cap on the number of caller-supplied items a verifier will consider in one evaluation:
// presented issuers (anchored mode), and BOTH claimed delegates and presented attestations (current
// mode — NEW-A; each dev(K) leaf verifies against every matching attestation, so the set is an
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
    snapshots: Vec<IelStateSnapshot>,        // the Evl/Icp-marker state snapshot(s) the walk reconstructed (NEW-B); bundles the IEL state fields settled in event-shape.md, exact struct an implementation detail
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
// not withdrawn? The credential NAMES its issuers and carries one anchor pinning per issuer plus
// an ISSUANCE-POLICY pinning (issuing is authoring, so the issuance check is anchored — G5); it
// carries NO delegation pins. Each presented issuer (a) self-traverses its own delegation chain
// to show it is a delegate of some del(prefix, N) named in `issuance_policy`, within N hops, every
// hop authorized + consented + un-rescinded to the delegator's tip; and (b) proves, via its anchor
// pinning, that the credential is anchored on its authentication at `required_tier`, on the
// surviving branch. The issuance policy's composers count DISTINCT contributing issuers per del
// placeholder. Self-contained: builds each issuer's `id` policy internally, walks delegation
// chains + anchor pinnings inline on `source`, then runs the withdrawal scan.
//
//  issuance_pinning the credential-carried pinning over `issuance_policy` (G5): issuing is
//                   authoring, so the issuance check resolves AS-OF pinned state, never at a
//                   roster owner's tip. In THIS PR the issuance evaluator reads NO chain state
//                   through the policy — `id` is matched against the anchored set, `del`
//                   self-traverses, `dev` is a misplaced-dev hard reject (DQ2), and a foreign `grp`
//                   credits NOBODY (group issuance authority is the creds REGISTRY-SEL, not an
//                   issuer-pinned issuance splice — see the `Grp` arm). So this pinning consumes no
//                   occurrence-slots here; the anchored foreign-`grp`-via-`policyPin` governance gate
//                   that fills the G1 slot from a SEL's pin is Phase-3 wiring. The exact pin-SAD
//                   serialization is implementer/SEL-primitive detail.
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
//                   (sourced from the del placeholder's N), pol/id nesting (a sensible default,
//                   e.g. 16). Exceeding it denies (fail-secure).
//
// Returns Err(PolicyError) on structural/source failure (malformed input, fetch failure, leftover
// pins, max_depth breach, presented != committed, a misplaced `dev`); Ok(None) on a clean
// unsatisfied result; and
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
// only STRUCTURAL failures (leftover pins, max_depth, malformed input, a NEW-B roster desync, a
// misplaced `dev`) stay hard `Err` — they are policy-validity / adversarial-pinning errors, not a
// single issuer's bad luck. Fail-secure: softening can only SHRINK the credited set, never validate
// spuriously.
pub fn evaluate_anchored_policy(
    issuance_policy: &Policy,
    issuance_pinning: &Pinning,              // cred-carried as-of state for the policy's own leaves (G5)
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
// `grp(group)` inside an aggregate member's authentication — it carries the enclosing `id()`
// descent's prefix AND its roster source (None at the top; set to `{X, AtMarker(snapshot)}` when
// recursing into id(X)'s authentication, so the member roster is read from the SAME frozen marker
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
//   - dev(K)         satisfied by an attestation whose signer == K, valid against K's CURRENT
//                    signing key (and recovery key, when required) at K's tip.
//   - id(X) / grp   satisfied by attestation(s) meeting X's authentication at its tip (recurse;
//                    one-arg grp(group) resolves to the enclosing id descent's roster, as in the
//                    anchored walk). X is NAMED in the policy — no claim needed; crediting is by the
//                    LEAF's prefix, so thr(2, [id(A), id(B)]) counts both identities even under
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
// (NEW-A / NEW-5) — each dev(K) leaf signature-verifies against every matching attestation, so an
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

Both entry points are **policy verifiers**: a satisfied evaluation yields a `PolicyVerification` proof token, not a bare `true`. `evaluate_anchored_policy` returns `Ok(Some(token))` iff the presented issuers (asserted equal to the credential's committed set, NEW-D) satisfy `issuance_policy` — each self-traversing to a named delegator within depth and anchoring the credential on its authentication at the required tier on the surviving branch — AND no satisfying withdrawal anchor was found (see *Withdrawal*); the token carries the credited issuer set, the anchored credential SAID(s), and the marker snapshot(s) the walk fixed. `evaluate_current_policy` returns `Ok(Some(token))` iff the attestations over `challenge` cover `policy`'s leaves at current chain state with the required attestation shape; the token carries the credited prefixes (no anchored SAIDs, no snapshot — current mode is tip-live). Both return `Ok(None)` for a clean unsatisfied — including an unknown primitive, which fails the **whole** policy closed (see *Verifier behavior*); `Err(_)` for malformed inputs / fetch failures, including leftover pins (more pins than the policy has occurrences), a presented≠committed mismatch, an over-cap presented set, a `max_depth` breach, or a misplaced `dev`. Token-existence *is* the proof of satisfaction — a caller holding a `PolicyVerification` cannot have reached it on an unsatisfied policy.

The auth flow typically calls both kinds of check. `evaluate_anchored_policy` is self-contained: it confirms each named issuer is a current delegate by **self-traversing that issuer's own delegation chain** up to a delegator named by the issuance policy (no cred-supplied path — the chain self-records the linkage; see *Delegation handshake*), proves each issuer's anchor through its `id` (the **anchor pinning**), counts distinct issuers against the issuance policy's thresholds (a foreign `grp` in an issuance policy credits **nobody** here — group issuance authority is the creds registry-SEL, not an issuer-pinned issuance splice), then runs the withdrawal scan. The verification walk pages each referenced log once, so a chain reached by several anchor pinnings or self-traversals is checked inline in that one pass. The **current-state** check (`evaluate_current_policy`) validates that the bearer presently controls the policy the cred names — it matches live attestations over a fresh challenge against the policy's leaves at the chain tip (`del` leaves self-traverse from a **named delegate** the bearer presents, as in the anchored flow).

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

The credential **names its issuer(s)** and carries **one anchor pinning per issuer**, plus **one
issuance-policy pinning** — issuing is authoring, so the issuance check is anchored (G5). A foreign
`grp` in an issuance policy credits **nobody** (group issuance authority is the creds registry-SEL,
not an issuer-pinned issuance splice — see [`grp`](leaf-semantics.md#grp--membership-roster-array)),
so the issuance-policy pinning supplies no occurrence markers here; the per-issuer **anchor pinnings**
carry the as-of anchor evidence. It carries **no delegation pinning**: delegation is
proven by the verifier self-traversing the issuer's own delegation chain, which self-records the
link to its delegator. Only the anchors and the issuance-policy state need pinnings.

The **gate** and the **evidence** resolve at different times (gate-current, C1): the issuance-policy
*text* is read at the resource's **current** state — an author must not grandfather a superseded gate
by pinning a policy version; the policy in force is whatever the resource holds now — while each
issuer's **anchor pinning** supplies its as-of evidence (proving the issuer anchored the credential on
its authentication as-of pinned state). With foreign-`grp` crediting nobody in the issuance path, the
issuance-policy pinning carries no occurrence-slots in this PR, so the anchor pinnings are the only
as-of evidence the issuance check consumes; a stale anchor pinning whose slots no longer line up with
the issuer's authentication structure denies deterministically (fail-closed, the leftover-pins rule),
never silently mis-binds.

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

// G5 — issuing is authoring: the credential carries an issuance-policy pinning for the issuance
// check's as-of state. In this PR it carries no occurrence-slots (a foreign grp credits nobody —
// group issuance is the creds registry-SEL; the only as-of evidence is the per-issuer anchor pinnings).
let issuance_pinning = parse_pinning_sad(&sadd_fetch(&cred.issuance_pinning_said)?)?;

// each required anchor names the minimum tier its hosting event must satisfy
let cred_anchor: HashSet<(Said, Tier)> = [(cred.said, Tier::One)].into_iter().collect();

// The issuer set the credential COMMITS to, read from the SAID-verified credential (NEW-D). The
// verifier asserts the presented `issuers` prefixes equal this INSIDE the call, at the trust
// boundary, before crediting — the equality is not the caller's to vouch for. (INTERIM: Phase 3
// passes the `&Credential` itself and reads `committed` internally, dissolving this separate arg.)
let committed: HashSet<Prefix> = cred.committed_issuers().into_iter().collect();

// One self-contained call: for each named issuer it self-traverses the issuer's own delegation
// chain up to a delegator named by the issuance policy (≤ N hops, bounded by max_depth), proves
// the issuer's anchor through its `id` (the anchor pinning), counts distinct issuers against the
// issuance policy's thresholds, and runs the withdrawal scan. No cred-supplied delegation path.
// On success it returns Some(PolicyVerification) — the proof token downstream steps consume.
let verification = evaluate_anchored_policy(
    &issuance_policy,
    &issuance_pinning,                           // G5: the policy's leaves resolve as-of this, not at tip
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

Implementation:

```rust
// evaluate_anchored_policy is self-contained and runs inline on the verification walk — there is
// NO separate pure bind phase. Each presented issuer is checked two independent ways:
//   (a) ANCHOR — its anchor pinning proves the credential is anchored on the issuer's OWN
//       authentication (surviving branch, required tier), via `id(issuer)`;
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
    issuance_pinning: &Pinning,              // cred-carried as-of state for the policy's own leaves (G5)
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

    // (a) Anchor proof per issuer. `id(issuer)` walks to the issuer's `Evl`/`Icp` state-marker and,
    // through its reconstructed authentication, the anchoring KEL(s); `expected_anchors` rides this walk so the credential
    // anchor is checked on the ISSUER'S authentication (surviving branch, required tier) — never on
    // a chain a `del` placeholder names. An issuer that anchors yields a per-issuer token (its
    // proven anchored SAD(s) + reconstructed marker snapshot); Ok(None) ⇒ not a contributor.
    let mut anchored: Vec<&Prefix> = Vec::new();
    let mut issuer_tokens: Vec<PolicyVerification> = Vec::new();
    for (issuer, anchor_pinning) in issuers {
        let issuer_id = parse_policy(&format!("id({})", issuer))?;
        if let Some(token) = evaluate_single_policy(&issuer_id, anchor_pinning, expected_anchors,
                                                    None, source, required_tier, max_depth)? {
            anchored.push(issuer);
            issuer_tokens.push(token);
        }
    }

    // (b) + composition. Evaluate the issuance policy: each `del(X, N)` placeholder is matched by
    // the distinct anchored issuers that self-traverse up to `X` within `N` hops; composers count
    // DISTINCT issuer prefixes. `id(X)` is matched against the anchored set; a foreign `grp` credits
    // NOBODY here (group issuance authority is the creds REGISTRY-SEL, not an issuer-pinned issuance
    // splice — see `issuance_credited`'s `Grp` arm). So the issuance evaluator reads no chain state
    // through the policy and consumes no slots; any leftover slots deny, mirroring the single-policy
    // discipline. An empty credited set is a clean unsatisfied (Ok(None)).
    let mut issuance_pins = PinCursor::new(&issuance_pinning.pins);
    let credited = issuance_credited(&issuance_policy.expr, &anchored, &mut issuance_pins,
                                     source, max_depth)?;
    if issuance_pins.remaining() > 0 {
        return Err(PolicyError::LeftoverPins);   // any pins are leftover — the issuance evaluator consumes none
    }
    if credited.is_empty() {
        return Ok(None);
    }

    // Withdrawal. `immune` skips THIS scan only — the F rescission tip-walk inside `self_traverses`
    // always ran. Otherwise scan to tip for a satisfying withdrawal anchor (soft per-contribution
    // default, or hard against `withdrawal`'s expr). See §Withdrawal. DQ2: `withdrawal: Some(expr)` is
    // an UNTRUSTED-author general policy (a malicious issuer sets it) evaluated at tip — `is_withdrawn`
    // roots its credited-set walk over `expr` at dev_legal=FALSE and routes every `dev` through
    // `check_dev_placement`, so a bare `dev` (directly, or via `pol(said)` → a `dev`-bearing SAD)
    // HARD-DENIES the credential; the `?` propagates the Err. A legitimate `id(admin)` withdrawal
    // authority still descends into the admin singleton's `dev` authentication (dev_legal flips true on
    // that descent), so admin/third-party kill is unaffected.
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

// ── dev-placement enforcement (DQ2) ──────────────────────────────────────────────────────────────
// The `dev`-placement rule ("a bare `dev` is legal ONLY inside a singleton IEL's own three policies;
// forbidden in every general / composed policy") is enforced HERE — at the VERIFIER, at EVALUATION,
// over the FULLY-`pol`-EXPANDED graph — never as an author/submit-time convention. The policy may be
// authored by an UNTRUSTED party (a malicious issuer's `withdrawal: Some(…)`, an attacker-set
// `readPolicy`/`pol(said)` → a `dev`-bearing SAD); only the verifier is the trust boundary, so the
// check rides the ONE eval walk (NOT a separate `validate_policy` pass — that would re-walk chains to
// re-derive singleton-ness and open a TOCTOU seam). `dev_legal` is a context flag threaded through
// that walk:
//   - SEEDED false at every general entry (issuance policy, `readPolicy`, the withdrawal `Some(expr)`,
//     the `id(issuer)` anchor wrapper). A singleton evaluating its OWN governance/operation as a
//     TOP-LEVEL policy (future IEL/SEL self-gating — verifier-behavior.md §Authorization gating) seeds
//     it TRUE (caller-supplied: the caller KNOWS it is a singleton's own policy — trustworthy context,
//     not caller-vouched authorization), or wraps the check in `id(singleton)` (D2-B);
//   - flips TRUE only when the walk DESCENDS INTO A SINGLETON's authentication (satisfies_id, and
//     current_credited's `id` / `del` arms, know roster-presence at the descent point) — the ONE
//     legitimate base case;
//   - INHERITED UNCHANGED through `thr`/`wgt`/`and`/`pol`. A singleton's own policy CANNOT use `pol`
//     (iel-policy-structure.md), so the flag is NEVER carried true into a `pol`; therefore a `dev`
//     reached via `pol(said)` — from ANY source — always has dev_legal=false → rejected. This is what
//     makes "fully-`pol`-expanded" sound: `pol` only propagates context; the check sits in the `dev` arm.
// A misplaced `dev` is a policy-VALIDITY error: `check_dev_placement` returns Err, which `?` propagates
// to the entry point so the WHOLE policy denies (hard, fail-closed) — NOT credit-nobody, which would
// let a sibling leg of `thr(1, [dev(K_bad), id(legit)])` clear the gate via the other leg. The legal
// base case (dev_legal=true at a singleton's own `dev`) passes the check and credits {K} as before.
fn check_dev_placement(dev_legal: bool) -> Result<(), PolicyError> {
    if dev_legal {
        Ok(())
    } else {
        Err(PolicyError::MisplacedDev)   // verifier-enforced placement, fail-closed (whole policy denies)
    }
}

// eval_issuance walks the issuance policy and reports whether its threshold is met by DISTINCT
// recognized issuers. It returns satisfaction; the helper `issuance_credited` returns, per
// subexpression, the SET of distinct issuers that subexpression credits IF satisfied (else empty) —
// so a containing composer dedups by prefix when it unions children. An issuance policy accepts both
// DELEGATED issuers (`del(X, N)` — anchored issuers self-traversing up to `X` within `N`, delegation
// is for scaling) and DIRECT named issuers (`id(X)` — anchored issuers matching the named prefix).
// A foreign `grp(prefix, group)` in an issuance policy credits **nobody** (group issuance authority
// is the creds registry-SEL, not an issuer-pinned issuance splice — see `issuance_credited`'s `Grp`
// arm). `pol`
// recurses; `thr`/`wgt`/`and` compose
// (union / max-weight / conjunction). A bare `dev` is a **policy-validity error** in an issuance
// policy (a general policy — `dev` is legal only in a singleton IEL's own three policies; validation
// rejects it, issuers being IELs, not bare devices); the defensive `Dev` arm below is the fail-secure
// floor. `thr(M, …)` is met iff the child union holds ≥ M distinct issuers; `wgt` sums per-issuer
// weight (dedup-by-max, mirroring `grp` — weighted delegation composes identically).
fn eval_issuance(
    expr: &PolicyExpr,
    anchored: &[&Prefix],
    issuance_pinning: &Pinning,
    source: &impl EventSource,
    max_depth: u32,
) -> Result<bool, PolicyError> {
    let mut pins = PinCursor::new(&issuance_pinning.pins);
    let credited = issuance_credited(expr, anchored, &mut pins, source, max_depth)?;
    if pins.remaining() > 0 {
        return Err(PolicyError::LeftoverPins);   // any pins are leftover — the issuance evaluator consumes none
    }
    Ok(!credited.is_empty())
}

// Returns the set of distinct issuers `expr` credits if satisfied, else the empty set. Issuance
// accepts DELEGATED (`del`) and DIRECT (`id`) issuers; `pol` recurses; `dev` is a misplaced-dev hard
// reject (DQ2); a foreign `grp` credits NOBODY (group issuance authority is the creds REGISTRY-SEL,
// not an issuer-pinned issuance splice — see the `Grp` arm). `pins` is the positional cursor over the
// credential's issuance-policy pinning (G5); in this PR NOTHING here reads chain state through the
// policy (`id` is matched against the anchored set, `del` self-traverses, `dev` hard-rejects, a
// foreign `grp` credits nobody), so the evaluator consumes NO slots.
fn issuance_credited(
    expr: &PolicyExpr,
    anchored: &[&Prefix],
    pins: &mut PinCursor,
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
        // id(X): credit {X} iff X is a DIRECT named issuer — it anchored the credential itself (no
        // delegation hop), so X ∈ anchored.
        PolicyExpr::Id(prefix) => Ok(if anchored.iter().any(|a| **a == *prefix) {
            HashSet::from([prefix.clone()])
        } else {
            HashSet::new()
        }),
        // grp(prefix, group): foreign roster splice. In the CREDENTIAL issuance path it credits NOBODY
        // and consumes NO slot — a foreign `grp` is NOT an issuer-pinned issuance leaf. That was the
        // ex-member exposure: the issuer freely chose the as-of marker, so a member X *removed* could
        // backdate an old roster where they were still listed and issue NEW valid creds. The fix is
        // STRUCTURAL — there is no issuer-supplied marker to backdate (the marker, where a foreign `grp`
        // does resolve, is context-supplied: X's tip in current mode, or a gating SEL's
        // governance-ratcheted `policyPin` in an anchored SEL-gated policy). GROUP ISSUANCE AUTHORITY —
        // letting a member of X issue creds while X rotates membership without reissuing and cuts off a
        // removed member — is a credentials-feature REGISTRY-SEL governed by `iel(X)`: an issuance `Ixn`
        // is validated against the registry's `operation` policy resolved AS-OF the SEL's
        // governance-ratcheted `policyPin` (forward-only, per-event — never an issuer-chosen pin). That
        // anchored SEL-gated resolution of a foreign `grp` (the G1 slot filled from the pin) is the
        // general governance-gate path — Phase-3 wiring, NOT this credential-issuance evaluator. Here:
        // fail-secure, credit nobody. The one-arg own-form grp(group) (Grp(None, _)) likewise credits
        // nobody — no host context in a general policy (`issuance_credited` threads no self-context and
        // never descends an `id`).
        PolicyExpr::Grp(_, _) => Ok(HashSet::new()),
        // pol(said): recurse (pure factoring — propagate the nested credited set; the nested
        // policy's occurrences consume from the SAME cursor, in pre-order, exactly as `eval_expr`'s
        // `pol` inherits its cursor — though in this PR the issuance evaluator consumes no slots).
        // Decrement depth.
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            issuance_credited(&nested.expr, anchored, pins, source, max_depth - 1)
        }
        // thr(M, …): union the credited children; met iff ≥ M distinct issuers, then return the
        // union. Children recurse at `max_depth - 1` (NEW-C — decrement on every composer, matching
        // eval_expr / current_credited, so composer-tree depth is bounded too).
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for sub in subs {
                union.extend(issuance_credited(sub, anchored, pins, source, max_depth - 1)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt(M, …): per-issuer weight, dedup-by-max across branches (mirrors `grp`; weighted
        // DELEGATION composes identically — an issuer matching several `del`/`grp` placeholders is
        // credited once at its MAX weight, distinct issuers summed); met iff the summed weight ≥ M.
        // Children recurse at `max_depth - 1` (NEW-C).
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (sub, w) in weighted {
                for p in issuance_credited(sub, anchored, pins, source, max_depth - 1)? {
                    best.entry(p).and_modify(|cur| *cur = (*cur).max(*w)).or_insert(*w);
                }
            }
            let sum: u64 = best.values().map(|w| *w as u64).sum();
            Ok(if sum >= *m { best.into_keys().collect() } else { HashSet::new() })
        }
        // and(…): conjunction — every child must credit ≥ 1 issuer; on success return the union, else
        // ∅ (separation of duties over issuers; distinct only over disjoint pools — see §`and`).
        // Every child is evaluated (no short-circuit — the conjunction needs each child's credited
        // set). Children recurse at `max_depth - 1` (NEW-C).
        PolicyExpr::And(children) => {
            let mut union = HashSet::new();
            let mut all_satisfied = true;
            for child in children {
                let credited = issuance_credited(child, anchored, pins, source, max_depth - 1)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // dev(K): FORBIDDEN in an issuance policy — `dev` is legal only in a singleton IEL's own three
        // policies (issuers are IELs; the distinct-issuer count is over IEL prefixes). issuance_credited
        // NEVER descends a singleton's authentication (its `id` arm matches against the anchored set, it
        // does not recurse into an authentication), so dev_legal is invariantly FALSE here — the shared
        // placement check HARD-REJECTS (DQ2). Fail-closed, never credit-nobody (a sibling leg must not
        // pass): the `?` denies the whole issuance policy.
        PolicyExpr::Dev(_) => {
            check_dev_placement(false)?;     // always Err here — issuance is a general policy
            Ok(HashSet::new())               // unreachable
        }
    }
}

// Host context for resolving a one-arg `grp(group)` inside an `id(X)` descent (NEW-B): the host
// prefix plus WHERE that host's roster is read. `AtMarker` pins the roster to the `id(X)`
// `Evl`/`Icp` marker's reconstructed snapshot (FROZEN — reused, no second pin, closing the
// authentication-recent / roster-stale split that a free roster slot would open). `AtTip` reads the
// owner's LIVE roster (current mode only — the read-time identity proof). A foreign two-arg `grp`
// never resolves a roster at tip in an anchored evaluator: it consumes its OWN X-state-marker slot
// (G1 — `issuance_credited` takes it from the credential's issuance-policy pinning; an anchored
// general-policy walk takes it from that policy's pinning). A `None`
// `self_context` means no enclosing id descent — a one-arg `grp(group)` there credits nobody
// (fail-secure). The struct carries the snapshot to the expansion site so `flatten` can reach it;
// the as-of-marker roster READ itself stays provisional (EventSource/pagination), like `snapshot_as_of`.
#[derive(Clone, Copy)]                 // all-reference fields — Copy, so it threads through the
struct HostContext<'a> {              // recursive composer arms (flatten + the child eval) freely
    prefix: &'a Prefix,
    roster: RosterSource<'a>,
}
#[derive(Clone, Copy)]
enum RosterSource<'a> {
    AtMarker(&'a IelStateSnapshot),   // roster frozen at the id(X) Evl/Icp marker (NEW-B)
    AtTip,                            // owner's live roster (tip)
}

// `flatten` / `flatten_weighted` expand each `grp` element to `id(member)` leaves in canonical
// order, reading the roster via `self_context`. A two-arg `grp(prefix, group)` reads
// `source.roster_members(prefix, group)` at the foreign owner's tip in CURRENT MODE — the
// context-supplied marker for a foreign `grp` in the live read-time flow. It never appears in the
// own-policies this single-policy pin-walk descends (see `eval_expr`'s thr note); in the credential
// issuance evaluator a foreign `grp` credits nobody (group issuance is the creds registry-SEL — see
// `issuance_credited`), and its anchored SEL-gated resolution (the roster as-of the gating SEL's
// `policyPin`) is Phase-3 wiring. A one-arg `grp(group)` reads
// the HOST's roster: `AtMarker(snap)` ⇒ `snap.roster` (the frozen marker snapshot, NEW-B); `AtTip`
// ⇒ `source.roster_members(host.prefix, group)`; `None` ⇒ credits nobody (no enclosing host).

// Single-policy pin-walk over ONE del-free policy (the issuer's authentication during the anchor
// check, or a nested `pol`). Consumes `pinning.pins` POSITIONALLY in pre-order walk order: a single
// cursor advances one slot per leaf the walk reaches. After the walk any LEFTOVER pins are a
// malformed pinning and deny (`Err`) — the issuer pinned more slots than the policy has occurrences.
// On satisfaction it emits a per-issuer PolicyVerification — the SAD(s) this walk proved anchored
// and the id marker snapshot(s) it reconstructed — which the anchored entry point folds into its
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
    // Seed dev_legal=false: this walk's top-level policy is always a GENERAL construction (the
    // `id(issuer)` anchor wrapper, or a nested `pol`), never a singleton's own dev-policy evaluated
    // top-level. A `dev` becomes legal only when satisfies_id DESCENDS into a singleton's authentication
    // (DQ2). (A future singleton self-gating entry that evaluates a singleton's OWN policy top-level
    // would seed true — D2-B — but evaluate_single_policy is never that entry.)
    let credited = eval_expr(&policy.expr, &mut cur, expected_anchors, self_context,
                             source, required_tier, max_depth, false)?;
    if cur.remaining() > 0 {
        return Err(PolicyError::LeftoverPins);       // more pins than occurrences — malformed
    }
    if credited.is_empty() {
        return Ok(None);                             // authentication unsatisfied — not a contributor
    }
    // Satisfied. The walk proved every `expected_anchors` SAID hosted at its tier floor on the
    // surviving branch (satisfies_dev) and reconstructed the id marker snapshot(s) (NEW-B); both
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
// and a present-but-unsatisfied `id` whose subtree still drains — cannot desync later slots.
// Composers evaluate every branch (no short-circuit) so slot order is deterministic.
//
// Returns the SET of distinct prefixes this expression CREDITS if satisfied, else the empty set
// (mirrors `issuance_credited`). A satisfied leaf credits the prefix it authenticates — `dev(K)`→K,
// `id(X)`→X — where the prefix comes from the STRUCTURE, not the pin (`satisfies_id` already
// checks `event.prefix == leaf_prefix`). A composer returns the UNION of its children's credited
// sets iff its threshold is met (else ∅), satisfied iff `|set| ≥ M`; `wgt` keeps each prefix's MAX
// weight, summed once. Dedup is RECURSIVE — the union propagates through nested `thr` / `wgt` /
// `pol` / `and`, so a prefix counts ONCE toward every ancestor threshold (`thr(2, [pol(P1),
// pol(P2)])` with `P1` = `P2` = `id(alice)` FAILS). An `id` boundary is OPAQUE: `id(X)` credits
// `{X}`, never X's internal members — X is the party. `max_depth` bounds `pol`/`id` recursion (and
// backstops the membership cycle guard); a breach denies.
fn eval_expr(
    expr: &PolicyExpr,
    cur: &mut PinCursor,
    expected_anchors: &HashSet<(Said, Tier)>,
    self_context: Option<HostContext>,
    source: &impl EventSource,
    required_tier: Tier,
    max_depth: u32,
    dev_legal: bool,                                 // DQ2: true only inside an id→singleton descent
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // dev: VERIFIER-ENFORCED PLACEMENT (DQ2). Legal ONLY as the base case of an id→SINGLETON descent
        // (dev_legal=true); a bare `dev` in any general / composed position (dev_legal=false), including
        // one reached via `pol(said)` → a `dev`-bearing SAD from any source, is a policy-validity error —
        // `check_dev_placement` HARD-REJECTS and the WHOLE policy denies (never credit-nobody, which a
        // sibling leg of `thr(1, [dev(bad), id(ok)])` could exploit). On the LEGAL path (a singleton's own
        // authentication) it still credits {K}: take this leaf's slot; a present SAID names the event
        // just-prior to the anchoring event — resolve its surviving-branch child and check the anchor +
        // tier; a null slot (or exhausted cursor) consumes the slot and credits nobody.
        PolicyExpr::Dev(prefix) => {
            check_dev_placement(dev_legal)?;          // reject a misplaced dev before any resolution
            match cur.take_next() {
                Some(Some(prior_said)) => {
                    if satisfies_dev(&prior_said, prefix, expected_anchors, source, required_tier)? {
                        Ok(HashSet::from([prefix.clone()]))
                    } else {
                        Ok(HashSet::new())
                    }
                }
                _ => Ok(HashSet::new()),              // null slot / exhausted — slot still consumed
            }
        }
        // id: take this leaf's slot (the Evl/Icp state-marker). A present SAID fixes the IEL's state;
        // reconstruct the snapshot as-of it and recurse into the snapshot's authentication, threading
        // the host context = prefix so an aggregate member's one-arg `grp(group)` resolves against the
        // SAME snapshot's roster (NEW-B), and draining the subtree's slots even if the member fails.
        // Satisfied ⇒ credit {prefix} (the boundary is opaque — X's internal members do NOT propagate).
        // A null slot consumes ONE slot and does NOT descend (the state-marker is un-evidenced, so its
        // authentication subtree is unreachable — see *Pinning → Issuer-side construction*).
        PolicyExpr::Id(prefix) => match cur.take_next() {
            Some(Some(marker_said)) => {
                if satisfies_id(&marker_said, prefix, cur, expected_anchors,
                                 source, required_tier, max_depth)? {
                    Ok(HashSet::from([prefix.clone()]))
                } else {
                    Ok(HashSet::new())
                }
            }
            _ => Ok(HashSet::new()),
        },
        // pol: dereference + recurse; pure factoring — propagate the nested credited set UNCHANGED
        // (so a prefix reached through two `pol`s dedups in the enclosing union). `expected_anchors`,
        // the host context (`self_context`), and `dev_legal` are inherited UNCHANGED — and since a
        // singleton's own policy can't use `pol`, dev_legal is never carried TRUE into a `pol`, so a
        // `dev`-bearing SAD reached here always sees dev_legal=false → rejected (DQ2).
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            eval_expr(&nested.expr, cur, expected_anchors, self_context,
                      source, required_tier, max_depth - 1, dev_legal)
        }
        // thr: evaluate every element (Grp children expand inline into id(member) leaves). In this
        // pinned own-authentication walk a member is always one-arg `grp(group)`, resolved against the
        // enclosing id(X) marker's reconstructed roster snapshot (FROZEN, NEW-B) — a foreign two-arg
        // `grp(prefix, group)` does not appear here (own-policies structurally exclude it). Where a
        // foreign `grp` IS resolved anchored — a SEL's pinned policy, the governance-gate — it consumes
        // its own X-state-marker slot filled from the SEL's `policyPin` (G1; Phase-3 wiring); in the
        // credential issuance evaluator it credits nobody (group issuance is the creds registry-SEL).
        // Members flatten in canonical order; see §Leaf semantics. UNION the children's credited sets;
        // met iff ≥ M DISTINCT prefixes, then return the union (recursive dedup). `del` is not a
        // single-policy element (no slot, no self-traversal here): it appears only in the issuance
        // policy, evaluated by `eval_issuance`.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, source)? {
                union.extend(eval_expr(&child, cur, expected_anchors, self_context,
                                       source, required_tier, max_depth - 1, dev_legal)?);
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
                                   source, required_tier, max_depth - 1, dev_legal)? {
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
                                         source, required_tier, max_depth - 1, dev_legal)?;
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

// dev(prefix): the credential is anchored on this KEL. `prior_said` names the event JUST BEFORE
// the anchoring event — the anchoring event commits to the credential, so its own SAID is
// unconstructable here (see the SAID-cycle note). Resolve the anchoring child `s` on the SURVIVING
// branch (`s.previous == prior_said`); an anchor on a divergent or later-archived branch is invalid
// (G — per kel/reconciliation.md, merge.md), so a missing surviving-branch child denies. The walk
// validates `s` inline (trust-boundary). Check every required anchor is hosted at its tier floor and
// `s` clears `required_tier`.
fn satisfies_dev(
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

// id(prefix): `marker_said` pins the IEL's most-recent `Evl`/`Icp` **state-marker** — NOT an
// anchoring event, so it carries no credential anchor and needs no prior-event trick. The verifier
// reconstructs X's **state snapshot** (authentication AND roster) AS-OF that marker (NEW-B) — the
// same running snapshot the walk already builds; `Del`/`Rsc` don't move it, so the marker is the
// last state-changing event. Satisfaction recurses into the snapshot's authentication policy
// (threading the host context = leaf_prefix so a member's one-arg `grp(group)` resolves), whose
// leaves consume the FOLLOWING slots in walk order — the credential anchor is checked at the
// terminal `dev` leaves the recursion reaches. A one-arg `grp(group)` in X's authentication reads
// its roster FROM THIS SAME reconstructed snapshot — REUSE of the `id(X)` marker, no second pin —
// so the authentication-recent / roster-stale split is structurally impossible (a free roster slot
// would let an issuer pin authentication-recent + roster-stale and resurrect a removed member). The
// descent runs regardless of prefix match so the subtree's slots always DRAIN (structural
// consumption); the leaf is satisfied only if the marker really is this prefix's and its
// authentication holds. Returns whether to credit `leaf_prefix` upward — the inner credited set
// (X's members/keys) is X's PRIVATE evidence, consumed at this boundary, never propagated (the
// caller credits `{X}`). The marker is read inline from the verification walk, which validates it.
fn satisfies_id(
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
    // (`AtMarker(&snapshot)`, NEW-B); a one-arg `grp(group)` it reaches resolves against THIS
    // snapshot's roster (`snapshot.roster`) — reuse of the same marker, not a fresh pin.
    let host = HostContext { prefix: leaf_prefix, roster: RosterSource::AtMarker(&snapshot) };
    // DQ2: dev_legal flips TRUE only when descending into a SINGLETON's authentication (the one legal
    // `dev` placement). `snapshot.is_singleton()` is roster-presence — a singleton has no roster, so its
    // dev-based authentication credits its devs; an AGGREGATE's grp-based authentication descends with
    // dev_legal=false (no bare `dev` is legal there — it composes one-arg `grp(group)` → id(member)).
    let sub = eval_expr(&authentication.expr, cur, expected_anchors, Some(host),
                        source, required_tier, max_depth - 1, snapshot.is_singleton())?; // drains the subtree's slots
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
(NEW-5). The presented **`attestations`** are capped at the same 128 (NEW-A): each `dev(K)` leaf
verifies against *every* matching attestation, so an uncapped set is a cost amplifier — the
up-front `TooManyAttestations` pre-check refuses it before any chain work, a sibling to the
delegate cap. On satisfaction the entry point returns `Ok(Some(PolicyVerification))` (credited set
only — current mode pins no marker and proves nothing anchored); `Ok(None)` when cleanly
unsatisfied; `Err(_)` on a cap breach or source failure.

```rust
// Current-state evaluation (challenge-response at the chain TIP). `current_credited` returns the set
// of distinct prefixes an expression credits if satisfied at tip, else ∅; the public entry wraps a
// non-empty set into a PolicyVerification token (Ok(None) if empty). Crediting is by the LEAF's
// prefix (dev(K)→K, id(X)→X), so an id boundary is opaque and distinct identities count even under
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
    if attestations.len() > MAX_PRESENTED {          // NEW-A — each dev(K) leaf verifies against EVERY
        return Err(PolicyError::TooManyAttestations); // matching attestation; cap the amplifier up front
    }
    if named_delegates.len() > MAX_PRESENTED {       // K ≤ 128 (NEW-5) — same cap as presented issuers;
        return Err(PolicyError::TooManyDelegates);   // up-front pre-check, fail-secure, zero work done
    }
    // Seed dev_legal=false (DQ2): a `readPolicy` / application policy / `id(subject)` is a GENERAL
    // policy — a bare `dev` (directly or via `pol(said)` → a `dev`-bearing SAD) is rejected; a `dev`
    // becomes legal only when the walk descends into a SINGLETON's authentication. (A future singleton
    // self-gating entry evaluating a singleton's OWN governance/operation top-level would seed true —
    // D2-B; this entry never does.)
    let credited = current_credited(&policy.expr, challenge, attestations, named_delegates,
                                    None, source, required_tier, max_depth, false)?;
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
    dev_legal: bool,                                 // DQ2: true only inside an id→singleton descent
) -> Result<HashSet<Prefix>, PolicyError> {
    if max_depth == 0 {
        return Err(PolicyError::MaxDepthExceeded);   // fail-secure
    }
    match expr {
        // dev(K): VERIFIER-ENFORCED PLACEMENT (DQ2). Legal ONLY as the base case of an id→SINGLETON
        // descent (dev_legal=true); a bare `dev` in a general policy (application / readPolicy /
        // withdrawal-expr), including one reached via `pol(said)` → a `dev`-bearing SAD from any source,
        // is a policy-validity error — `check_dev_placement` HARD-REJECTS and the WHOLE policy denies
        // (this is exactly the attacker-set-`readPolicy` attack — see *Verifier behavior*). On the LEGAL
        // path, credit {K} iff an attestation by K validates against K's CURRENT signing key (and
        // recovery key, per the required_tier ATTESTATION SHAPE) over the challenge. NEW-F: the prior
        // `.unwrap_or(false)` that swallowed errors is gone. `verify_current_attestation` returns
        // Ok(false) for a non-verifying EXTERNAL attestation-over-challenge signature — junk, not
        // credited, so a flood of bad attestations can't grief the eval into an error — and Err only
        // for a CHAIN-integrity / source failure (can't resolve K's current key state), which `?`
        // propagates.
        PolicyExpr::Dev(prefix) => {
            check_dev_placement(dev_legal)?;          // reject a misplaced dev before any verify work
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
        // id(X): credit {X} iff the attestation set meets X's authentication at X's TIP (recurse,
        // host context = {X, AtTip} — current mode reads the roster LIVE, NEW-B; terminal kels
        // matched by attestation signer). X is named in the policy. DQ2: dev_legal flips TRUE only when
        // X is a SINGLETON (`tip.is_singleton()` — roster-presence is the kind signal); an aggregate's
        // grp-based authentication descends dev-illegal.
        PolicyExpr::Id(prefix) => {
            let tip = source.iel_tip(prefix)?;
            let auth = parse_policy_sad(&sadd_fetch(&tip.authentication)?)?;
            let host = HostContext { prefix, roster: RosterSource::AtTip };
            let sub = current_credited(&auth.expr, challenge, attestations, named_delegates,
                                       Some(host), source, required_tier, max_depth - 1, tip.is_singleton())?;
            Ok(if sub.is_empty() { HashSet::new() } else { HashSet::from([prefix.clone()]) })
        }
        // pol: dereference + recurse; propagate the nested credited set unchanged. `dev_legal` is
        // inherited UNCHANGED — and never carried true into a `pol` (a singleton's own policy can't use
        // `pol`), so a `dev`-bearing SAD reached via `pol(said)` here is rejected (DQ2).
        PolicyExpr::Pol(said) => {
            let nested = parse_policy_sad(&sadd_fetch(said)?)?;
            current_credited(&nested.expr, challenge, attestations, named_delegates,
                             self_context, source, required_tier, max_depth - 1, dev_legal)
        }
        // thr: flatten grp at the host (one-arg) / named foreign owner (two-arg `grp(prefix, group)`)
        // roster's TIP (current mode is tip-live, NEW-B — the foreign `grp`'s context-supplied marker
        // is X's tip here), union the children; met iff ≥ M distinct.
        PolicyExpr::Thr(m, subs) => {
            let mut union = HashSet::new();
            for child in flatten(subs, self_context, source)? {
                union.extend(current_credited(&child, challenge, attestations, named_delegates,
                                              self_context, source, required_tier, max_depth - 1, dev_legal)?);
            }
            Ok(if union.len() as u64 >= *m { union } else { HashSet::new() })
        }
        // wgt: per-prefix MAX weight, each distinct prefix summed once; met iff sum ≥ M.
        PolicyExpr::Wgt(m, weighted) => {
            let mut best: HashMap<Prefix, u32> = HashMap::new();
            for (child, w) in flatten_weighted(weighted, self_context, source)? {
                for p in current_credited(&child, challenge, attestations, named_delegates,
                                          self_context, source, required_tier, max_depth - 1, dev_legal)? {
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
                                                self_context, source, required_tier, max_depth - 1, dev_legal)?;
                if credited.is_empty() {
                    all_satisfied = false;
                }
                union.extend(credited);
            }
            Ok(if all_satisfied { union } else { HashSet::new() })
        }
        // del(X, N): the live analogue of anchored del-matching — NO del-pin. Credit each DISTINCT
        // named delegate D (`named_delegates`) whose attestations meet D's authentication at D's tip
        // AND that self-traverses up to X within N hops (delegation valid to X's TIP, F). DQ2: the
        // descent into D's authentication flips dev_legal TRUE only when D is a SINGLETON.
        PolicyExpr::Del(delegator, n) => {
            let mut set = HashSet::new();
            for d in named_delegates {
                let d_tip = source.iel_tip(d)?;
                let d_auth = parse_policy_sad(&sadd_fetch(&d_tip.authentication)?)?;
                let d_host = HostContext { prefix: d, roster: RosterSource::AtTip };  // tip-live (NEW-B)
                let met = current_credited(&d_auth.expr, challenge, attestations, named_delegates,
                                           Some(d_host), source, required_tier, max_depth - 1, d_tip.is_singleton())?;
                if !met.is_empty() && self_traverses(d, delegator, *n, source, max_depth)? {
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

(The tip-state source accessors — `iel_tip`, `verify_current_attestation` — are illustrative shapes
over the settled event/attestation event-shapes; their exact signatures are an implementation detail.)

