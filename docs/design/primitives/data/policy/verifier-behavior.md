Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Composition semantics

- **Leaves evaluate independently.** One leaf's satisfaction never depends on another's. The shared pin cursor and the per-log single paged verification walk are plumbing (slot assignment, walk reuse), not satisfaction coupling.
- **Composers are pure aggregators.** They take their children's **credited sets** (the distinct prefixes each child satisfied) and produce a credited set of their own — `thr`/`and` union the children, `wgt` sums per-prefix max weights — emitting that union iff the threshold is met, else `∅`. Crediting is by *structural* prefix and dedups recursively (a prefix counts once toward every ancestor), so the same identity reached two ways satisfies once, not twice. Pins are never deduped. No side effects (see §Leaf semantics, §Composition).
- **Boundedness.** Bounded cost. There is no separate pure bind phase: the policy graph is *expanded as it is walked* (descending through `pol`, `id` authentication, and `grp` rosters), consuming pins positionally and reading chain state off the verified chain tokens the provider yields — one paged pass per referenced log, the pass each log gets for end-verifiability anyway. A log referenced by several leaves is paged once, and a million-event log is paged through once in O(chain length), parallelizable across logs (resident cost bounded by the page — the chain is never materialized whole). Every recursion/walk depth is capped by the always-passed `max_depth`; a foreign `grp`'s roster contributes its sparse `GrpBlock` signers (anchored mode, capped at `MAX_PRESENTED`) or its enumerated roster (current mode, capped by a roster-width bound); and a **per-policy work cap** (NEW-G) bounds the *total* across all rosters, `pol` nesting, and `id` recursion — so neither a malicious foreign roster nor many moderate ones can amplify cost without bound. The **presented-party count** (anchored mode) and the **claimed-delegate count** *and* **attestation count** (current mode) are each capped at `MAX_PRESENTED` (128) by an up-front trust-boundary pre-check — a sibling bound to `max_depth`, roster-width, and the per-policy expansion cap — so a caller cannot amplify cost by presenting an unbounded party / delegate / attestation set; exceeding it refuses (`TooManyParties` / `TooManyDelegates` / `TooManyAttestations`) before any chain work. Self-traversal of a `del` chain is bounded by the placeholder's `N`. Evaluation itself is a cheap tree walk.
- **Deterministic.** Given a fixed chain state and signed request, evaluation is deterministic. Verifiers across nodes converge.

## Verifier behavior

The verifier **expands the policy graph as it walks it** — there is no separate pure bind phase, and it
reads chain state **only through verified chain tokens** the provider yields (never a live `EventSource`).
The **multi-party** anchored evaluator (`evaluate_anchored_policy`) refuses up front if more than
`MAX_PRESENTED` (128) parties are presented (`TooManyParties`) — a count cap at the trust boundary before
any chain work, sibling to `max_depth`, the roster-width bound, and the per-policy expansion cap (NEW-G).
Current mode applies the same `MAX_PRESENTED` cap to **both** `named_delegates` (`TooManyDelegates`) and the
presented `attestations` (`TooManyAttestations`, NEW-A) — see *Current-mode evaluation*. Then, for each
presented party, two independent checks ride inline on the verification walk:

- **Anchor** — evaluate `id(party)` against that party's **anchor pinning**, consuming pins
  positionally in pre-order walk order (a single cursor advances one slot per leaf; a `null`/absent
  slot fails that leaf but still consumes its slot; *leftover pins after the walk deny*). The `id`
  leaf reads the pinned `Evl`/`Icp` state-marker off the party's `IelVerification` (the verifier
  reconstructs the snapshot fixing the authentication state) and recurses into that authentication; the
  terminal `dev` leaves resolve the anchoring child **on the surviving branch** off the `KelVerification`
  and check the anchor at the required tier. `anchors_to_check` rides this walk, so the anchor is checked
  on the party's *own* authentication.
- **Delegation** — `self_traverses` walks **up** the party's own delegation chain to a delegator the
  policy names (`del(X, N)`, `≤ N` hops), direct-looking-up each `Del` (no enumeration) and checking
  authorization + consent + **no `Rsc` to the delegator's tip** (F, always).

`evaluate_anchored_policy` then evaluates the policy, where each `del(X, N)` placeholder is matched by the
**distinct anchored parties** that self-traverse to `X` within `N`; composers count distinct parties, and a
foreign `grp` credits **nobody** here (no gate context — group authority is supplied only through a SEL gate;
see `evaluate_gate_policy`). **E1**: a single party's chain-verification failure is **soft** (recorded
`Unverifiable`, uncredited) and the threshold runs over the `Credited` set; structural failures stay hard
`Err`. The public entry points are **policy verifiers**: on satisfaction they return
`Ok(Some(AnchoredPolicyVerification))` / `Ok(Some(CurrentPolicyVerification))` — the unforgeable proof token —
`Ok(None)` for a clean unsatisfied, and `Err(_)` for a structural / verification failure (see *API Surface*).
The full Rust under [*evaluation.md → Implementation*](evaluation.md#implementation) is canonical; the sketch
below shows the shape — the internal helpers elide the token (returning sets / bools) for readability, but the
public entry points return it:

```
# All three read chain state via the verified-token PROVIDER, never a live source. `walk` records consumed
# chain-token SAIDs (D2) + reconstructed snapshots (NEW-B). SAD content is fetched content-addressed (sadd_fetch).

# evaluate_gate_policy — the GENERAL governance gate (D3a): ONE del-free policy + ONE pinning. `gate_context`
# supplies a foreign grp's marker (SelGate(sel) -> the SEL's FLOORED policyPin, D3b; Tip; None -> credit nobody).
evaluate_gate_policy(policy, pinning, anchors_to_check, gate_context, provider, required_tier, max_depth)
        -> Result<Option<AnchoredPolicyVerification>>:
    walk = Walk(provider)
    if gate_context is SelGate(sel): walk.register(sel.said())            # bind the gate's SEL token (D2)
    cur  = PinCursor(pinning.pins)
    credited = eval_expr(policy.expr, cur, anchors_to_check, None, gate_context, walk, required_tier, max_depth, dev_legal=false)
    if cur.remaining() > 0: error(LeftoverPins)                           # more pins than occurrences — malformed
    if credited is empty: return Ok(None)
    return Ok(Some(AnchoredPolicyVerification::new(policy.said, credited,             # bind policy SAID (A)
                       anchored_saids(anchors_to_check), walk.snapshots(),
                       {p: Credited for p in credited}, walk.consumed_tokens())))     # party_outcomes (E1) + consumed tokens (D2)

# evaluate_anchored_policy — MULTI-PARTY validity (de-cred: GENERIC anchors, no committed-set / withdrawal /
# immune). Each party (a) anchors the SADs on its OWN authentication via id(party); (b) self-traverses any del.
evaluate_anchored_policy(policy, parties, anchors_to_check, provider, required_tier, max_depth)
        -> Result<Option<AnchoredPolicyVerification>>:
    if len(parties) > MAX_PRESENTED: error(TooManyParties)                # count cap, up front
    if parties is empty: return Ok(None)
    walk = Walk(provider); outcomes = {}
    anchored = []                                                         # (a) anchor proof per party
    for (party, anchor_pinning) in parties:
        match evaluate_gate_policy(id(party), anchor_pinning, anchors_to_check, None, provider, required_tier, max_depth):
            Ok(Some(t)) => walk.fold(t); anchored.append(party); outcomes[party] = Credited
            Ok(None)    => outcomes[party] = Unsatisfied
            Err(ChainUnverifiable) => outcomes[party] = Unverifiable      # E1 SOFT — uncredited, not a global error
            Err(e)      => return Err(e)                                  # structural — HARD
    credited = anchored_credited(policy.expr, anchored, walk, max_depth)  # (b) del self-traverse / id match; foreign grp credits NOBODY (no gate)
    if credited is empty: return Ok(None)
    return Ok(Some(AnchoredPolicyVerification::new(policy.said, credited,
                       anchored_saids(anchors_to_check), walk.snapshots(), outcomes, walk.consumed_tokens())))

# self_traverses: walk UP candidate's chain to delegator, <= max_hops, F-rescission-to-tip ALWAYS (immune ignored).
self_traverses(candidate, delegator, max_hops, walk, max_depth) -> bool:
    lower = candidate
    for _ in 0 .. min(max_hops, max_depth):
        parent   = walk.verify_iel(lower).delegating_prefix()       # lower.Icp.delegating       (consent)
        del_said = walk.verify_iel(lower).delegating_del_said()     # lower.Evl[1].delegating     (consent back-ptr)
        del      = walk.verify_iel(parent).del_event(del_said)      # direct lookup; MUST be a `Del` (rejects `Rsc`/other)
        if del.host != parent or not del.lists(lower):       return false   # authorization (reads `Del` additions)
        if walk.verify_iel(parent).rescinded_by_tip(lower):         return false   # F — ALWAYS
        if parent == delegator:                              return true
        lower = parent
    return false

# Leaves take the NEXT slot (positional, pre-order) and read chain state off the walk's tokens; consumption is
# structural (a failed/present-unsatisfied id still drains its subtree). Returns the SET of distinct prefixes
# CREDITED if satisfied, else ∅ (recursive dedup; an id boundary is opaque). Unknown primitive => whole policy
# denies (fail-secure). `gate_context` supplies a foreign grp's marker (SelGate -> floored policyPin, D3b; Tip;
# None -> credit nobody).
eval_expr(expr, cur, anchors_to_check, host, gate_context, walk, required_tier, max_depth, dev_legal) -> set<Prefix>:
    if max_depth == 0: error(MaxDepthExceeded)
    match expr:
        # dev: VERIFIER-ENFORCED PLACEMENT (DQ2). check_dev_placement(dev_legal) HARD-REJECTS unless this `dev`
        # sits at the base of an id→singleton descent; a bare dev in any general / composed / pol-reached position
        # denies the WHOLE policy (never credit-nobody). Then resolve the anchor as before.
        dev(prefix) => check_dev_placement(dev_legal); cur.take_next() is Some(Leaf(Some(prior))) and satisfies_dev(prior, prefix, anchors_to_check, walk, required_tier) ? {prefix} : {}   # Some(Grp(_)) where a leaf was due ⇒ error(PinKindMismatch)
        id(prefix)  => cur.take_next() is Some(Leaf(Some(marker))) and satisfies_id(marker, prefix, cur, anchors_to_check, gate_context, walk, required_tier, max_depth) ? {prefix} : {}   # Some(Grp(_)) ⇒ error(PinKindMismatch)
        pol(said)   => eval_expr(parse_dsl(sadd_fetch(said)).expr, cur, anchors_to_check, host, gate_context, walk, required_tier, max_depth - 1, dev_legal)   # never carries dev_legal true into a pol
        thr(M, ss)  => U = union(eval_expr(s, …) for s in ss);            |U| >= M ? U : {}                          # no flatten — a grp child hits the grp arm
        wgt(M, ws)  => B = per-prefix MAX weight over [(eval_expr(sub, …), w) for (sub, w) in ws];   sum(B.values) >= M ? B.keys : {}   # children inherit dev_legal
        and(cs)     => sets = [eval_expr(c, …) for c in cs];   all(s nonempty for s in sets) ? union(sets) : {}   # eval ALL (drain slots)
        # grp: SPARSE — consume ONE GrpBlock; credit each named signer that is in-roster (as-of the context X-marker) AND authenticates via its own sub_pins (sub-cursor; per-block leftover denies — blast radius contained).
        grp(maybe_prefix, group) =>
            block = cur.take_next() is Some(Grp(b)) ? b : (cur.take_next() is Some(Leaf(_)) ? error(PinKindMismatch) : return {});
            check_block_canonical(block);                                            # sorted-by-prefix + dedup'd + |signers| <= MAX_PRESENTED, else error
            roster = resolve_roster(maybe_prefix, group, host, gate_context, walk) or return {};   # context-supplied X-marker; None ⇒ nobody
            { signer.prefix for signer in block.signers
                  if roster.contains(signer.prefix)
                  and satisfies_id(signer.marker_said, signer.prefix, PinCursor(signer.sub_pins), anchors_to_check, gate_context, walk, required_tier, max_depth - 1) }
        _           => {}                                    # del standing alone is bracket-only

# dev: `prior` is the pinned event just before the anchoring event; resolve its SURVIVING-BRANCH child S
# (S.previous == prior) off the KelVerification — dodges the SAID cycle, needs no search. A divergent / archived
# branch has no valid anchor. id: the pin is the Evl/Icp state-marker (cycle-free); reconstruct the snapshot
# AS-OF it off the IelVerification and recurse into the snapshot's authentication (host = {prefix, AtMarker(snap)};
# a one-arg grp(group) under it REUSES this same snapshot's roster, NEW-B); the descent drains the subtree's slots
# even on mismatch (structural consumption).
satisfies_dev(prior, leaf_prefix, anchors_to_check, walk, required_tier):
    S = walk.verify_kel(leaf_prefix).anchoring_child_on_surviving_branch(prior)  # None if divergent/archived
    if S is None: return false
    return S.prefix == leaf_prefix
        AND S.tier >= required_tier
        AND for all (anchor, tier) in anchors_to_check: S.anchors.contains(anchor) AND S.tier >= tier

satisfies_id(marker_said, leaf_prefix, cur, anchors_to_check, gate_context, walk, required_tier, max_depth):
    snap = walk.snapshot_as_of(leaf_prefix, marker_said)                 # reconstruct state AS-OF the Evl/Icp marker (NEW-B)
    host = HostContext{ prefix: leaf_prefix, roster: AtMarker(snap) }          # NEW-B — roster frozen at the marker
    sub  = eval_expr(parse_dsl(sadd_fetch(snap.authentication)).expr,          # one-arg grp(group) reuses snap.roster
                    cur, anchors_to_check, Some(host), gate_context, walk, required_tier, max_depth - 1, snap.is_singleton())  # DQ2: dev_legal TRUE only for a singleton
    return snap.prefix == leaf_prefix AND sub nonempty                   # X's authentication met ⇒ credit X; drains subtree regardless of match
```

**Semantics notes:**

- **Anchor requirement propagates uniformly.** A `pol(said)` recursion — and an `id`
  authentication recursion — threads the same positional `cur` cursor, `anchors_to_check`, `gate_context`,
  `walk`, `required_tier`, and `max_depth` as the outer evaluation (and `self_context` set to the enclosing
  `id` prefix). When `evaluate_gate_policy` is used for a party's *anchor* walk, every `dev` leaf reached
  under it is an anchoring leaf, so `anchors_to_check` flows down to all of them; a multi-party `del(X, N)` is
  matched separately by self-traversal and never carries the anchor requirement. The whole expanded graph
  consumes one positional pin cursor, each occurrence taking its own slot in pre-order order; leftover pins
  after the walk deny.
- **The SAID cycle, and why dev prefixes pin the *prior* event.** A SAID is the hash of the SAD with its own said-field zeroed, so it depends on every other field. The event that anchors an anchored SAD `C` lists `said(C)` in its `anchors`; `C` commits to the Pinning (`said(P)`); `P` lists the pinned event's SAID. Pinning the anchoring event directly would close the loop `said(anchor) → said(C) → said(P) → said(anchor)` — unconstructable. So a dev prefix pins the event *just prior* and the verifier rederives the anchoring child on the surviving branch. id prefixes are cycle-free: they pin `Evl`/`Icp` state-markers (the verifier reconstructs the authentication snapshot as-of them), which never carry an anchored SAD. Avoiding a second walk of a shared log is handled by the verification walk paging that log once and checking all of its pinned positions inline (the pinned SAIDs are supplied up front as the positions to check), not by the pin array order.
- **`pol(said)` reference cycles are structurally impossible.** Content-addressed references can't form a cycle without a Blake3-256 collision (two Policy SADs mutually containing each other's SAIDs). No runtime cycle check needed.
- **Hard depth cap (`max_depth`, always passed).** Every recursive/walk depth in evaluation — `del` self-traversal, `pol` nesting, `id` authentication recursion — is bounded by an **explicit `max_depth` the caller always passes**; never implicit or unbounded. It is sourced from data where a governing bound exists (a `del(X, N)` chain caps at `N`) and from a sensible default otherwise (`pol`/`id` nesting, e.g. 16). Exceeding it **denies** (fail-secure). This also backstops the aggregate-membership cycle guard.
- **Roster bound (foreign `grp`).** A foreign `grp(prefix, group)` resolves against `X`'s roster, and `X` controls it. In **anchored** evaluation the deep evidence is a sparse `GrpBlock` whose signer count is capped at `MAX_PRESENTED`; membership is an `roster.contains` check per signer, so the block scan is bounded by `MAX_PRESENTED` × roster width — no enumeration of the roster as leaves. In **current** mode the verifier enumerates the roster at tip to match attestations; that enumeration is capped by a **width bound**, and a roster exceeding it denies (fail-secure) — a large or malicious foreign group cannot amplify verifier cost without bound.
- **Per-policy work cap (NEW-G).** Beyond the per-roster bound, the **total** work a single policy resolves to — summed across every `grp` roster resolution (the `GrpBlock` signers in anchored mode, the enumerated roster in current mode), `pol` nesting, and `id` authentication recursion — is capped by a per-policy bound, a sibling to `max_depth`, the roster bound, and `MAX_PRESENTED`. A policy whose resolved total exceeds it denies (fail-secure) before the walk completes, so neither a deeply nested composition (including nested `GrpBlock`s) nor many moderate rosters can multiply past the cap even when no single roster is over-wide.
- **Tier check is in the leaf helpers, not the composers.** A dev prefix's `satisfies_dev` rejects an anchoring event hosted below `required_tier`; the tier requirement propagates unchanged through the id authentication recursion to the terminal dev leaves. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized primitive → the WHOLE policy denies (fail-secure).** An older verifier encountering a newer DSL primitive must **not** treat it as a merely-unsatisfied sub-expression: `thr(1, [new_restrictive_thing, old_permissive_thing])` would then silently ignore the restriction and pass. Instead an unknown primitive fails the **entire** policy closed (`Ok(None)` for the whole evaluation — no proof token is produced). Greenfield ships one DSL version, but this keeps safety intact under any skew.
- **`dev` placement is verifier-enforced at evaluation, fail-closed (DQ2).** The rule "a bare `dev` is legal only inside a singleton IEL's own three policies, forbidden in every general / composed policy" is enforced **at the verifier, at evaluation time, over the fully-`pol`-expanded graph** — not as an author/submit-time convention (the policy may be authored by an untrusted party — an attacker-set `readPolicy`/`pol(said)` → a `dev`-bearing SAD, a creds-feature withdrawal policy — and only the verifier is the trust boundary). A context flag `dev_legal` threads the one eval walk: seeded **false** at a general entry (or **true** for a singleton self-gating its own governance/operation top-level — D2-B, caller-supplied), flipped **true only on an `id`→singleton descent** (the one legal placement), inherited unchanged through `thr`/`wgt`/`and`/`pol`. Because a singleton's own policy cannot use `pol`, `dev_legal` is never carried true into a `pol`, so a `dev` reached via `pol(said)` from any source always has `dev_legal=false`. A misplaced `dev` is a **policy-validity error** — `check_dev_placement` returns `Err` and the **whole** policy denies (like the unknown-primitive rule, but `Err` not `Ok(None)`, since it must propagate past sibling legs); it is **not** credit-nobody, which would let `thr(1, [dev(K_bad), id(legit)])` pass via the `id(legit)` leg. The legal base case (a singleton's own `dev`) still credits `{K}`. This is the same mechanism in all three evaluators (anchored `eval_expr`, `anchored_credited`, current-mode `current_credited`) and in any untrusted-authored general policy a feature evaluates through them (e.g. a creds withdrawal policy).
- **Pinned canonical DSL string form.** Policies are stored as DSL **strings** inside a SAD, and JCS canonicalizes the surrounding JSON but treats the DSL as opaque — so `thr(2,[a,b])` and `thr(2, [a, b])` would otherwise produce different SAIDs. The DSL has a **pinned canonical string form** (the analog of `said.md`'s normatively-pinned JCS): no insignificant whitespace, arguments comma-separated without spaces, `grp` members emitted in canonical order, and **`wgt` entries fully split to single-element brackets** (next bullet). Every cross-party-agreement and content-addressed dedup claim (the prefix-free one-arg `grp` collapse, where identical own-policies share a Policy SAD; two parties independently authoring "the same" policy) depends on it.
- **Canonical `wgt` desugar.** A multi-element `wgt` bracket and its split equivalent parse to the *same* AST — `wgt(M, [([a, b], w), …])` and `wgt(M, [([a], w), ([b], w), …])` both yield two weight-`w` entries (the array is lossless concise sugar — `([a, b], w)` desugars to `(a, w), (b, w)`). They must therefore canonicalize to one string, or their SADs' SAIDs diverge and `wgt`'s cross-party agreement breaks. **Canonical form splits every entry to single-element brackets `([elem], w)`, in source order**: `([a, b], w)` → `([a], w), ([b], w)`; a `grp` / `del` element stays whole inside its own single-element bracket (`([grp(X, g)], w)`, `([del(X, N)], w)`) — `wgt` subjects are membership-style only, no composer/`pol` (NEW-E). Only the bracket grouping is normalized — source/sibling order is preserved (the analog of the `grp`-order rule).
- **The trust boundary is the verified token.** The evaluator reads chain state **only** through the verified chain tokens the provider yields — never a live source — so it cannot be made to trust a substituted or leaked chain state; possession of a token is the proof the chain verified. The presented parties + their anchor pinnings are caller-supplied, but a foreign `grp` credits nobody without a gate context, the multi-party threshold counts only `Credited` parties (E1), and a misplaced `dev` denies — so an over-broad presented set can only **shrink** the credited set, never validate spuriously. Binding the presented set to a **document's committed authors** (e.g. a credential's committed issuer set) is a **feature** concern: the creds feature's `verify_credential` reads the committed set from the SAID-verified credential itself and requires every committed issuer `Credited` — no caller-supplied set for the primitive to mistrust.
- **Challenge binding (current-state flow).** The `challenge` `evaluate_current_policy` verifies must be **unpredictable, single-use, and context-bound** (to the resource, action, and request at hand) — otherwise an attestation over a reused challenge replays across contexts. The server constructs it (e.g. a random nonce hashed with the request context); the verifier rejects a stale or context-mismatched challenge before checking signatures.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](../event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

- **IEL `Evl` / `Dec`** — gated by `governance`
- **IEL `Del` / `Rsc`** — gated by `delegation`
- **SEL `Evl` / `Rpr` / `Dec`** — gated by `governance`
- **SEL `Est` / `Ixn`** — gated by `operation`
- **Application-defined gates** — credentials, signed requests, etc. — gated by application-specific policy references

## Composing the entry points

The two entry points compose: an **anchored** check (authority *as authored* — a governance gate via
`evaluate_gate_policy`, or multi-party validity via `evaluate_anchored_policy`) and a **current** check
(control *now* — `evaluate_current_policy`) yield **distinct typed tokens** (`AnchoredPolicyVerification` vs
`CurrentPolicyVerification`) a consumer combines. The two types make it compile-impossible to pass a
current-control proof where an anchored-validity proof is required (and vice versa), so verify-before-use is
type-enforced and the runtime `debug_assert!`s an unsplit token needed disappear. A worked general example —
an SEL governance gate composed with a current-control check, minting a capability from the two tokens — is in
[*evaluation.md → General governance-gate + current-control example*](evaluation.md#general-governance-gate--current-control-example).

The three-question split is general:

- **Authority as authored** (anchored) — was this authorization validly produced (the right parties anchored
  it as-of the pinned state)? It checks pinned events inline; it says nothing about who is acting now.
- **Control now** (current) — does whoever is acting presently control the named identity? Live attestations
  over a fresh challenge at tip; it says nothing about how the authorization was produced.
- **Application authorization** — given a valid authorization held by its rightful controller, does it grant
  the requested action? Outside the DSL — the app's role→permission vocabulary.

Splitting them keeps each failure mode independent. The credential `authorize` 3-check flow (validity +
identity + role→permission, with a credential's withdrawal scan) is a **creds-feature** application of this
pattern — `verify_credential` wraps `evaluate_anchored_policy`, the role map is the application's — and is
forward-pointed to the creds feature, not the policy primitive.

## Worked rejections — the `dev`-placement attacks (DQ2)

Both attacks supply a policy authored by an **untrusted** party but evaluated by **your** verifier; the
`dev_legal` check (above) rejects each, fail-closed, at the verifier. Each is a `dev` reached with
`dev_legal=false`.

**Attack 1 — untrusted-authored policy `dev`-bypass (e.g. a creds-feature hard withdrawal policy).** A
feature evaluates an untrusted-authored general policy that reaches a bare `dev` — for instance a credential's
hard withdrawal authority `withdrawal: Some(pol(P))` where `P`'s content is `dev(K_attacker)` (or
`thr(1, [dev(K_attacker)])`). The feature runs it through the general evaluator, rooted at **`dev_legal=false`**
(a withdrawal policy is a general policy). The walk hits `pol(P)`, fetches `P`, recurses **inheriting
`dev_legal=false`** (a `pol` never carries it true), reaches `dev(K_attacker)` → `check_dev_placement(false)`
→ `Err(MisplacedDev)`. The `?` propagates: the **whole policy denies**. Because DQ2 is enforced in the
**primitive's** evaluator, the feature gets this protection for free — the lifecycle-bypass the rule exists to
prevent never happens.

**Attack 2 — `readPolicy` `dev`-bypass (attacker-set `readPolicy` reaching a bare `dev`).** A SAD author
(or an adversary who can set a SAD's custody) writes `readPolicy = dev(K_retired)` — or
`readPolicy = thr(1, [dev(K_retired), id(legit_reader)])`, hoping the `id(legit_reader)` leg carries the
read while the bare `dev` slips through. At fetch time the read side runs
`evaluate_current_policy(readPolicy, …)` rooted at **`dev_legal=false`** (a `readPolicy` is a general
policy). `current_credited` reaches `dev(K_retired)` → `check_dev_placement(false)` → `Err(MisplacedDev)`,
which propagates: the **whole read denies** (the `id(legit_reader)` leg cannot rescue it — the `Err`
short-circuits the composer, which is exactly why the check errors rather than crediting-nobody). A
retired device can never be granted a read it was rotated out of.

**The legal case still works.** `withdrawal: Some(thr(2, [id(admin_a), id(admin_b)]))` (admins are
singletons) descends — via `id(admin_a)` / `id(admin_b)` — into each admin's `dev`-based authentication
with `dev_legal` flipped **true** at the singleton descent, so each admin's `dev` credits `{K_admin}` and
admin/third-party kill is unaffected; the same holds for a `readPolicy = id(reader)` resolving through a
singleton's device.

