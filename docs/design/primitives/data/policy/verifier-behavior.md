Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Composition semantics

- **Leaves evaluate independently.** One leaf's satisfaction never depends on another's. The shared pin cursor and the per-log single paged verification walk are plumbing (slot assignment, walk reuse), not satisfaction coupling.
- **Composers are pure aggregators.** They take their children's **credited sets** (the distinct prefixes each child satisfied) and produce a credited set of their own — `thr`/`and` union the children, `wgt` sums per-prefix max weights — emitting that union iff the threshold is met, else `∅`. Crediting is by *structural* prefix and dedups recursively (a prefix counts once toward every ancestor), so the same identity reached two ways satisfies once, not twice. Pins are never deduped. No side effects (see §Leaf semantics, §Composition).
- **Boundedness.** Bounded cost. There is no separate pure bind phase: the policy graph is *expanded as it is walked* (descending through `pol`, `id` authentication, and `grp` rosters), consuming pins positionally and running leaf checks inline on the verifier's verification walk — the single paged pass each referenced log gets for end-verifiability anyway. A log referenced by several leaves is paged once, and a million-event log is paged through once in O(chain length), parallelizable across logs (resident cost bounded by the page — the chain is never materialized whole). Every recursion/walk depth is capped by the always-passed `max_depth`; `grp` foreign-roster expansion is capped by a roster-width bound; and a **per-policy expansion cap** (NEW-G) bounds the *total* post-flatten leaf count across all rosters, `pol` nesting, and `id` recursion — so neither a malicious foreign roster nor many moderate ones can amplify cost without bound. The **presented-issuer count** (anchored mode) and the **claimed-delegate count** *and* **attestation count** (current mode) are each capped at `MAX_PRESENTED` (128) by an up-front trust-boundary pre-check — a sibling bound to `max_depth`, roster-width, and the per-policy expansion cap — so a caller cannot amplify cost by presenting an unbounded issuer / delegate / attestation set; exceeding it refuses (`TooManyIssuers` / `TooManyDelegates` / `TooManyAttestations`) before any chain work. Self-traversal of a `del` chain is bounded by the placeholder's `N`. Evaluation itself is a cheap tree walk.
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

- **Anchor** — evaluate `id(issuer)` against that issuer's **anchor pinning**, consuming pins
  positionally in pre-order walk order (a single cursor advances one slot per leaf; a `null`/absent
  slot fails that leaf but still consumes its slot; *leftover pins after the walk deny*). The `id`
  leaf reads the pinned `Evl`/`Icp` state-marker (the verifier reconstructs the snapshot fixing the
  authentication state) and recurses into that authentication; the terminal `dev` leaves resolve the anchoring child **on the surviving branch**
  and check the credential anchor at the required tier. `expected_anchors` rides this walk, so the
  anchor is checked on the issuer's *own* authentication.
- **Delegation** — `self_traverses` walks **up** the issuer's own delegation chain to a delegator
  the issuance policy names (`del(X, N)`, `≤ N` hops), direct-looking-up each `Del` (no enumeration)
  and checking authorization + consent + **no `Rsc` to the delegator's tip** (F, always).

`evaluate_anchored_policy` then evaluates the issuance policy, where each `del(X, N)` placeholder is
matched by the **distinct anchored issuers** that self-traverse to `X` within `N`; composers count
distinct issuers, and the policy's foreign `grp(X, group)` splices resolve X's roster **as-of the
X-state-marker the credential's issuance-policy pinning supplies** (G1/G5 — issuing is authoring, so
the issuance check is anchored; the roster owner's tip is never read). Finally it scans each issuer
KEL to tip for a withdrawal anchor — skipped **only**
when the credential is `immune` (the F rescission walk above is never skipped). The public entry
points are **policy verifiers**: on satisfaction they return `Ok(Some(PolicyVerification))` — the
unforgeable proof token — `Ok(None)` for a clean unsatisfied, and `Err(_)` for a structural/source
failure (see *API Surface*). The full Rust under
[*Policies and Pinnings → Implementation*](evaluation.md#policies-and-pinnings) is canonical; the sketch below
shows the shape — the internal helpers elide the token (returning sets / bools) for readability, but
the public `evaluate_anchored_policy` returns it:

```
evaluate_anchored_policy(issuance_policy, issuance_pinning, issuers, committed_issuers,
                         expected_anchors, withdrawal, immune, source, required_tier, max_depth)
        -> Result<Option<PolicyVerification>>:
    if len(issuers) > MAX_PRESENTED: error(TooManyIssuers)                       # count cap, up front
    assert {prefix for (prefix, _) in issuers} == committed_issuers             # trust boundary (NEW-D)
    # INTERIM: Phase 3 reads `committed_issuers` from a `&Credential` input rather than as a separate
    # arg (`.working/vdti-12-policy-dsl-phase3-token-architecture.md`); the boundary check stays.
    if issuers is empty: return Ok(None)

    anchored = []; issuer_tokens = []                            # (a) anchor proof per issuer
    for (issuer, anchor_pinning) in issuers:
        if let Some(t) = evaluate_single_policy(parse_policy("id(" + issuer + ")"), anchor_pinning,
                                  expected_anchors, None, source, required_tier, max_depth):
            anchored.append(issuer); issuer_tokens.append(t)

    issuance_pins = PinCursor(issuance_pinning.pins)             # G5 — the cred-carried as-of state
    credited = issuance_credited(issuance_policy.expr, anchored, issuance_pins, source, max_depth)  # (b) count distinct
    if issuance_pins.remaining() > 0: error(LeftoverPins)        # malformed issuance pinning
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
# DIRECT issuers credited by id(X) (X in anchored) / grp(X, group) (anchored members of X's `group`
# AS-OF the X-state-marker its slot in the issuance-policy pinning supplies — G1/G5, never X's tip);
# pol recurses; thr/wgt/and count DISTINCT issuer prefixes (set union; wgt dedups by max weight;
# and = all branches non-empty). dev credits nobody. Never expands del; a foreign grp is the only
# occurrence kind that consumes an issuance-pinning slot. (eval_issuance wraps it as a
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
# inside an id descent; AtTip is current-mode only) for an aggregate member's one-arg grp(group).
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
# walk; consumption is structural (a failed/present-unsatisfied id still drains its subtree). Returns
# the SET of distinct prefixes CREDITED if satisfied, else ∅: a satisfied dev(K)/id(X) credits {K}/{X}
# (the prefix from the STRUCTURE, not the pin); a composer unions its children iff its threshold is met
# (recursive dedup — a prefix counts once toward every ancestor; an id boundary is opaque). del is NOT
# a single-policy element (no slot, no self-traversal here). Unknown primitive => whole policy denies
# (fail-secure), handled by the caller.
eval_expr(expr, cur, expected_anchors, host, source, required_tier, max_depth) -> set<Prefix>:
    if max_depth == 0: error(MaxDepthExceeded)
    match expr:
        # dev is reached only as the id-recursion base case (a singleton's own authentication); an
        # author-written bare dev in a general policy is a placement-validity error and never reaches here.
        dev(prefix) => cur.take_next() is Some(Some(prior))  and satisfies_dev(prior, prefix, expected_anchors, source, required_tier) ? {prefix} : {}
        id(prefix) => cur.take_next() is Some(Some(marker)) and satisfies_id(marker, prefix, cur, expected_anchors, source, required_tier, max_depth) ? {prefix} : {}
        pol(said)   => eval_expr(parse_dsl(sadd.fetch(said).content).expr, cur, expected_anchors, host, source, required_tier, max_depth - 1)   # propagate nested set
        thr(M, ss)  => U = union(eval_expr(s, cur, …) for s in flatten(ss, host, source));            |U| >= M ? U : {}
        wgt(M, ws)  => B = per-prefix MAX weight over (s, w) in flatten_weighted(ws, host, source);   sum(B.values) >= M ? B.keys : {}
        and(cs)     => sets = [eval_expr(c, cur, …) for c in cs];   all(s nonempty for s in sets) ? union(sets) : {}   # eval ALL (drain slots)
        _           => {}                                    # del/grp standing alone are bracket-only

# dev: `prior` is the pinned event just before the anchoring event; resolve its SURVIVING-BRANCH
# child S (S.previous == prior) — checking it there, inline, both dodges the SAID cycle and needs no
# search. A divergent / archived branch has no valid anchor. id: the pin is the Evl/Icp state-marker
# (cycle-free); reconstruct the snapshot AS-OF it and recurse into the snapshot's authentication
# (threading host = {prefix, AtMarker(snap)}; a one-arg grp(group) under it REUSES this same snapshot's roster, NEW-B) —
# the credential anchor is checked at the terminal dev leaves; the descent drains the subtree's slots
# even on mismatch (structural consumption).
satisfies_dev(prior, leaf_prefix, expected_anchors, source, required_tier):
    S = source.anchoring_child_on_surviving_branch(leaf_prefix, prior)    # None if divergent/archived
    if S is None: return false
    return S.prefix == leaf_prefix
        AND S.tier >= required_tier
        AND for all (anchor, tier) in expected_anchors: S.anchors.contains(anchor) AND S.tier >= tier

satisfies_id(marker_said, leaf_prefix, cur, expected_anchors, source, required_tier, max_depth):
    snap = source.snapshot_as_of(leaf_prefix, marker_said)               # reconstruct state AS-OF the Evl/Icp marker (NEW-B)
    host = HostContext{ prefix: leaf_prefix, roster: AtMarker(snap) }          # NEW-B — roster frozen at the marker
    sub  = eval_expr(parse_dsl(sadd.fetch(snap.authentication).content).expr,  # one-arg grp(group) reuses snap.roster
                    cur, expected_anchors, Some(host), source, required_tier, max_depth - 1)
    return snap.prefix == leaf_prefix AND sub nonempty                   # X's authentication met ⇒ credit X; drains subtree regardless of match
```

**Semantics notes:**

- **Anchor requirement propagates uniformly.** A `pol(said)` recursion — and an `id`
  authentication recursion — threads the same positional `cur` cursor, `expected_anchors`, `source`,
  `required_tier`, and `max_depth` as the outer evaluation (and `self_context` set to the enclosing
  `id` prefix). Because `evaluate_single_policy` is only ever called for an issuer's *anchor* walk,
  every `dev` leaf reached under it is an anchoring leaf, so `expected_anchors` flows down to all of
  them; an issuance-policy `del(X, N)` is matched separately by self-traversal and never carries the
  anchor requirement. The whole expanded graph consumes one positional pin cursor, each occurrence
  taking its own slot in pre-order order; leftover pins after the walk deny.
- **The SAID cycle, and why dev prefixes pin the *prior* event.** A SAID is the hash of the SAD with its own said-field zeroed, so it depends on every other field. The event that anchors credential `C` lists `said(C)` in its `anchors`; `C` commits to the Pinning (`said(P)`); `P` lists the pinned event's SAID. Pinning the anchoring event directly would close the loop `said(anchor) → said(C) → said(P) → said(anchor)` — unconstructable. So a dev prefix pins the event *just prior* and the verifier rederives the anchoring child on the surviving branch. id prefixes are cycle-free: they pin `Evl`/`Icp` state-markers (the verifier reconstructs the authentication snapshot as-of them), which never carry the credential anchor. Avoiding a second walk of a shared log is handled by the verification walk paging that log once and checking all of its pinned positions inline (the pinned SAIDs are supplied up front as the positions to check), not by the pin array order.
- **`pol(said)` reference cycles are structurally impossible.** Content-addressed references can't form a cycle without a Blake3-256 collision (two Policy SADs mutually containing each other's SAIDs). No runtime cycle check needed.
- **Hard depth cap (`max_depth`, always passed).** Every recursive/walk depth in evaluation — `del` self-traversal, `pol` nesting, `id` authentication recursion — is bounded by an **explicit `max_depth` the caller always passes**; never implicit or unbounded. It is sourced from data where a governing bound exists (a `del(X, N)` chain caps at `N`) and from a sensible default otherwise (`pol`/`id` nesting, e.g. 16). Exceeding it **denies** (fail-secure). This also backstops the aggregate-membership cycle guard.
- **Roster-width bound (foreign `grp`).** `grp(X, group)` with foreign `X` expands to one leaf per roster member, and `X` controls its roster. Expansion is capped by a **width bound**; a roster exceeding it denies with an "expansion truncated" signal (fail-secure) — a large or malicious foreign group cannot amplify verifier cost without bound.
- **Per-policy expansion cap (NEW-G).** Beyond the per-roster width bound, the **total** number of leaves a single policy expands to — summed across every `grp` flatten, `pol` nesting, and `id` authentication recursion — is capped by a per-policy expansion bound, a sibling to `max_depth`, the roster-width bound, and `MAX_PRESENTED`. A policy whose post-flatten leaf count exceeds it denies (fail-secure) before the walk completes, so neither a deeply nested composition nor many moderate rosters can multiply past the cap even when no single roster is over-wide.
- **Tier check is in the leaf helpers, not the composers.** A dev prefix's `satisfies_dev` rejects an anchoring event hosted below `required_tier`; the tier requirement propagates unchanged through the id authentication recursion to the terminal dev leaves. Composers aggregate satisfied/unsatisfied results; they don't see tier directly.
- **Unrecognized primitive → the WHOLE policy denies (fail-secure).** An older verifier encountering a newer DSL primitive must **not** treat it as a merely-unsatisfied sub-expression: `thr(1, [new_restrictive_thing, old_permissive_thing])` would then silently ignore the restriction and pass. Instead an unknown primitive fails the **entire** policy closed (`Ok(None)` for the whole evaluation — no proof token is produced). Greenfield ships one DSL version, but this keeps safety intact under any skew.
- **Pinned canonical DSL string form.** Policies are stored as DSL **strings** inside a SAD, and JCS canonicalizes the surrounding JSON but treats the DSL as opaque — so `thr(2,[a,b])` and `thr(2, [a, b])` would otherwise produce different SAIDs. The DSL has a **pinned canonical string form** (the analog of `said.md`'s normatively-pinned JCS): no insignificant whitespace, arguments comma-separated without spaces, `grp` members emitted in canonical order, and **`wgt` entries fully split to single-element brackets** (next bullet). Every cross-party-agreement and content-addressed dedup claim (the prefix-free one-arg `grp` collapse, where identical own-policies share a Policy SAD; two parties independently authoring "the same" policy) depends on it.
- **Canonical `wgt` desugar.** A multi-element `wgt` bracket and its split equivalent parse to the *same* AST — `wgt(M, [([a, b], w), …])` and `wgt(M, [([a], w), ([b], w), …])` both yield two weight-`w` entries (the array is lossless concise sugar — `([a, b], w)` desugars to `(a, w), (b, w)`). They must therefore canonicalize to one string, or their SADs' SAIDs diverge and `wgt`'s cross-party agreement breaks. **Canonical form splits every entry to single-element brackets `([elem], w)`, in source order**: `([a, b], w)` → `([a], w), ([b], w)`; a `grp` / `del` element stays whole inside its own single-element bracket (`([grp(X, g)], w)`, `([del(X, N)], w)`) — `wgt` subjects are membership-style only, no composer/`pol` (NEW-E). Only the bracket grouping is normalized — source/sibling order is preserved (the analog of the `grp`-order rule).
- **Issuer-set trust boundary.** The verifier confirms the presented `issuers` equal the credential's **committed issuer set** before crediting any of them — the issuer↔content↔anchor binding never depends on caller bookkeeping (the verifier is the trust boundary). (INTERIM: Phase 3 reads the committed set from a `&Credential` input rather than as a separate `committed_issuers` arg — `.working/vdti-12-policy-dsl-phase3-token-architecture.md` — and softens per-issuer failure (E1); the boundary check itself is unchanged.)
- **Challenge binding (current-state flow).** The `challenge` `evaluate_current_policy` verifies must be **unpredictable, single-use, and context-bound** (to the resource, action, and credential at hand) — otherwise an attestation over a reused challenge replays across contexts. The server constructs it (e.g. a random nonce hashed with the request context); the verifier rejects a stale or context-mismatched challenge before checking signatures.

The detailed verifier evaluation algorithm (chain-walk caching, parallelism, recursion termination, etc.) lives in the implementation specs — out of scope here.

## Authorization gating reference

Policy DSL evaluations gate the following event kinds (per [`event-logs/event-shape.md`](../event-logs/event-shape.md#authorization-gating-per-kind)). All gating evaluates against the chain's tracked policy at the parent event — for evolution events, that's the policy before this event changes it; for non-evolution events, the policy is simply unchanged from the parent's state.

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
    //    issuers clear the issuance threshold (its foreign `grp` splices resolved as-of the cred's
    //    issuance-policy pinning, G5); and no satisfying withdrawal anchor was found. The
    //    presented issuers are asserted equal to the credential's committed set INSIDE the verifier
    //    (NEW-D). On success it returns a PolicyVerification proof token.
    let cred_anchor: HashSet<(Said, Tier)> =
        [(cred.said, Tier::One)].into_iter().collect();
    let issuers: Vec<(Prefix, &Pinning)> = cred.issuers();   // committed set, sourced from the cred
    let committed: HashSet<Prefix> = cred.committed_issuers().into_iter().collect();
    let issuance_pinning: &Pinning = cred.issuance_pinning();   // cred-carried as-of state (G5)
    let Some(validity) = evaluate_anchored_policy(
        issuance_policy,
        issuance_pinning,
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
    //    `id(subject)` defers to the subject's own authentication policy, so a rotated or multi-sig
    //    subject still authenticates correctly. The challenge defeats replay. `id(subject)` has no
    //    `del`, so no delegates are claimed (&[]).
    let subject_policy = parse_policy(&format!("id({})", cred.subject))?;
    let Some(identity) = evaluate_current_policy(
        &subject_policy,
        challenge,
        attestations,
        &[],                         // no del leaves in id(subject) → no claimed delegates
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

