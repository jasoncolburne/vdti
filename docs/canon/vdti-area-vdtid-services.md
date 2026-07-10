# vdti — area note: `vdtid` services (node service architecture)

**Status: FIRST CUT (2026-06-20).** The node service architecture — `vdtid` + `witnessd` over a shared
`lib/vdti`. Mirrors the kels service layout with two deliberate changes (merge chain+SAD; gossip→witnessd).
Grounded in the **kels build read on `main`** (the *mechanics* are correct; the *shape/taxonomy* is design-stale,
so mine the machinery not the kinds), the reshape design, and Jason's decomposition decisions this session.
**Not a primitive** — this note is the service/lib boundary and the cross-cutting runtime machinery.

## Sources audited (disposition)
- kels `main`: `services/{kels, sadstore, gossip, registry, mail, identity}`, `lib/{kels, gossip, derive, …}`;
  read in depth — `lib/kels/src/types/{iel,sad}/verification.rs` (tokens), `…/sync.rs` (transfer engine),
  `merge.rs` (merge), `types/deferred_deps.rs` + `services/gossip/src/pending.rs` (deferred-deps),
  `services/gossip/src/sync.rs` (anti-entropy). **Mechanics authoritative; taxonomy (`Cnt`/`Upd`/`Sea`/`Evl`)
  is the old design — do not carry.**
- kels roadmap (`kels#168`) — confirms design-ahead-of-build (many "design landed, code-side follow-up open").
- `vdti-token-store-idea.md`, `vdti-area-federation-witnessing.md` (witnessd's witness role), the SAD spec in
  this repo (custody — already covered, not re-read).
- Memories: `project_vdti_gossip_vs_witness`, `project_kels_transfer_abstractions`, `project_kels_end_verifiability`,
  `project_vdti_event_log_storage_constraint`, `project_vdti_effective_said_synthetics`,
  `feedback_verifier_is_trust_boundary`. ⚠ `project_vdti_compacted_only_submission` is **stale** on `eventsd`/`sadd`
  (§3) — fix.

## 1. Locked-candidate — the architecture

### 1a. Decomposition (mirrors kels; two changes)
- **`lib/vdti`** — the verification/merge/transfer **core**: the three primitive verifiers + their tokens, the
  transfer engine, merge, the policy/IEL resolvers, effective-SAID, deferred-deps types + collect-mode, sadstore
  custody, compaction. **Consumers link this too** (§1b). All correctness lives here; the daemons are plumbing.
- **`vdtid`** — thin daemon: **postgres chain-log + SAD store merged into one service** (kels' `kels`+`sadstore`).
  *Why merged:* events reference SADs by SAID, so a separate SAD store is an extra hop per SAD fetch — **several
  per request**; co-locating kills the hops (and keeps anchor + SAD in one txn). Hosts the API (submit / fetch /
  exists / effective-said), runs merge (advisory lock + DB txn), emits typed-422 deferred-deps.
- **`witnessd`** — kels' **`gossip` service wholesale** (renamed; "gossip" stays the *pattern* name
  [`project_vdti_gossip_vs_witness`]). Holds: gossip propagation, the deferred-deps **park/drain** map, the
  **anti-entropy** loops, and the federation **witness/receipt** role (`vdti-area-federation-witnessing.md` §1e —
  always-witness, by-`(prefix,serial)` selection). Holds HSM witness keys (destruction-on-witnessing) — isolated
  so a compromised `vdtid` can't mint receipts.
- **`clients` (cli, bench)** — build/verify locally with `lib/vdti`; **compact before submit**; maintain the
  client-side **token store** (§1d).
- **Backing stores:** postgres (chain + SAD, behind `vdtid`); Redis (park map + anti-entropy stale-tracking +
  cache, behind `witnessd`).
- **Features (creds / mail / exchange) are libraries** (`lib/vdti/*`), **never `vdtid` modules** — no
  loadable-module support; `vdtid` stays tight. (Whether any feature keeps a thin daemon like kels'
  `registry`/`mail` is §4.)

### 1b. The lib is the spine — *because consumers must verify* [end-verifiability]
End-verifiability means a consumer **cannot trust `vdtid`** — it re-verifies the data itself, with the **same**
verifier. So the verifier must be a **library both `vdtid` and consumers link**, never service-internal. The
token's unforgeability (§1c) + "the DB cannot be trusted" (§1g) mean trust attaches to the **data** (verified),
not the daemon [`feedback_verifier_is_trust_boundary`]. This is the entire reason for the lib/service split.

### 1c. Verification tokens
`KelVerification` / `IelVerification` / `SelVerification` are **unforgeable proof-of-verification** —
constructable **only** by the verifier. Structural problems = **HARD** (halt the walk); auth/policy = **SOFT**
(reported as unsatisfied via the contextual `satisfied`/`queried` sets, not raised — continue); terminal flags (`is_divergent`/`is_terminated`) from chain **content**
[inv 9]. **`queried`/`satisfied` SAIDs** = caller-bounded (consumer names the SAIDs it cares about up-front;
`satisfied` = anchored ∧ authorized ∧ before the divergence cut = valid-for-binding) [inv 8]. **`resume`** =
incremental re-hydration from a prior token. Tokens **compose**: a SEL resolves its IEL binding by consuming the
IEL token's `policy_history` + `satisfied_saids`, not by re-walking.

### 1d. Token store — vdti's refinement over kels' re-verify-every-write
Cache tokens keyed by prefix (tip SAID encoded); on use, compare the token's **full pinned-dependency
effective-SAID set** — the chain's own **and every chain it transitively pins** (the KEL(s) beneath an IEL, the
IEL beneath a SEL): **all match → reuse** (no walk); **any moved → `since`-query the new events + `resume`**
(incremental, not a re-walk). **Transitive is load-bearing (F5, 2026-06-20):** a lower-layer recovery `Rot` breaks an
upper event while the upper chain's *own* effective-SAID doesn't move — only the transitive check catches it
(the warm-cache path for the cross-layer cascade). This **refines** "DB cannot be trusted" — the effective-SAID
is the cheap integrity gate; any tamper/advance **moves it** → re-verify. **Freshness, made *detectable* (F8,
2026-06-20; B1 fail-secure rework 2026-07-09):** the to-tip loss-of-trust read — divergence / staleness **and cred
revocation / rescission** (a `kills[]` declaration on the same witnessed IEL — inv 10) — must use a **witnessed /
multi-source** effective-SAID (a single server can report a stale one to hide a divergence, a dormant-chain forgery,
**or a revocation**) — and the token carries that **provenance** (single-source vs witnessed, as-of-when) as
contextual info [inv 9], so "this decision used insufficient-freshness data" is **detectable** — and when it can't be
multi-source-confirmed the decision **fails-secure: REFUSE**, never proceeds on the flag (cold-5 C2, inv 8).
Revocation/rescission are **inv-8 dependencies now** (fail-secure by default — the earlier best-effort carve-out is
dropped, cold/warm re-review-2 F1). **Revocation is NOT `vdtid`'s concern (R6):** `vdtid` validates / serves / merges
chains + SADs, and a revoked subject is **still structurally-valid data** — the revocation check lives in the
**verifier** (`lib/vdti`) and is run by a **consumer** (client / app server) making a trust decision, so the
fail-secure / fail-open / timeout posture (and any bricking) is the **consumer's**, at the application layer — there
is **no revocation walk at `vdtid`** (nothing to brick there). The consumer may deliberately opt **down** to a
**fail-open content-addressed lookup** (a *verifier* read strategy over data `vdtid` serves by address — found +
validated → fast refuse; not-found → fall back to the walk, or best-effort not-revoked if it has opted fail-open / a
walk-timeout — §1g / document-policy §F). Not a mere prose obligation. Non-to-tip / resolving checks: a plain
single-source comparison is fine.
- **Freshness composes over the whole transitive set (F-E, 2026-06-21).** The multi-source bar above is **not**
  per-"the chain" — it applies to **every chain the token transitively pins** (cred · issuer · *every* delegator
  above it · the devices beneath each identity). A single stale source on **any** one of them can hide a
  **positive-state break** (a fork / dormant-chain forgery / stale roster), so a loss-of-trust decision confirms
  *each* dependency's effective-SAID multi-source (a witnessed
  effective-SAID *is* multi-source → cheap; an unwitnessed dependency **can't meet the bar → the decision fails-secure: REFUSE**, cold-5 C2). **"Is
  this chain forked / disputed?" is itself a loss-of-trust question** (a one-branch holder sees a normal
  tip; only the federation signal reveals the fork) → it goes in the multi-source bucket. And **`resume` re-runs
  the to-tip negative checks** (revocation / rescission / divergence) against the new tip whenever any pinned chain
  moves — never just staple on newer events, or it advances past a revocation. *(Revocation / rescission re-run on
  the fresh walk with divergence — all fail-secure now (no best-effort carve-out); the fail-open lookup is the opt-out, inv 10.)* (So F9's cross-layer-break
  detection is F5+F8 over the full set, not a separate mechanism.) [inv 8]
- **Freshness is a wall-clock overlay, recomputed at decision-time (cold-12 F1).** The effective-SAID-movement gate
  certifies **structure** (unchanged ⇒ skip the re-walk); it does **not** certify **freshness**. The federation
  staleness / 365-day key-window auto-expiry (federation §1f) is **time-triggered** — it fires with **zero chain
  events**, so nothing *moves* and a movement-only reuse path would miss it. So the token caches the **freshest-valid
  witnessing-time** (data), **never** a cached `fresh`/`stale` *verdict* (which is `now`-dependent), and **every
  loss-of-trust decision recomputes staleness against current `now`** (the §1f staleness threshold + the 365-day
  auto-expiry), **independent of** whether any effective-SAID moved. A token cached pre-lapse therefore reads **stale at
  decision-time** (its witnessing-time is now ancient) → **fail-secure REFUSE**, never a reused pre-lapse 'fresh'
  verdict. (The staleness *machinery* already exists, §1f; this names the **cache/reuse** path so it can't skip the
  wall-clock re-check.)

### 1e. Effective-SAID — single confirmed tip → real SAID; no single tip → a verdict-recoupled synthetic (first-seen, 2026-07-08 — REVERSES the earlier live-tips digest)

The effective SAID answers "**has my trust-relevant held state changed / do two nodes hold the same state?**" It is:

- **A single confirmed tip** (a linear active window, or a fork already settled below the seal — Active / Recovered /
  Terminated) → **that tip's real SAID** (a terminated chain's is its `Trm`).
- **No single tip** (an unresolved fork — a live content fork, or ≥ 1 **sealed** branch past it) → a **type-tagged
  `synthetic` marker recoupled to the verdict** (`forked` / `disputed`), qualified by **prefix + position**, and
  **structurally distinct from any real SAID** (a distinct type tag — so the "single-tip SAID ≠ synthetic"
  inequality that fires anti-entropy is *structural*, never a probabilistic collision; the encoder must not reduce it
  to a bare SAID-shaped digest — cold M3). **There is NO digest over the competing tips.**

**Why a synthetic, not a real digest (this REVERSES the earlier four-round-reviewed "real digest over LIVE held
tips, NO synthetics").** That real-digest was sound **under live, honest, first-seen witnesses** (which bound the
branch count); the **first-seen pivot + federation-death + the dishonest-signer adversary void that assumption.** A
digest over the competing branch set is **flood-unstable**: under dishonest signers the set is adversarially
extensible (no production cap — a compromised quorum can threshold-witness a 3rd/Nth sealed sibling), so the hash
changes as the set grows and differently-viewed verifiers disagree / thrash; "which 2" is view-dependent. The old
defense ("the un-witnessed flood is dropped") covered only *un*-witnessed floods — exactly the case first-seen
can't lean on. A **synthetic is set-independent → flood-stable**, still **triggers anti-entropy** (a single-tip SAID
≠ a synthetic), and is **verdict-sufficient** — the exact set is never needed for the value: **root-bury kills all
content branches by position** (masking is harmless — the value still moves on tip-advance and verdict-transition),
**Disputed reincepts** (outcome invariant to the set), and **attribution walks the stored events, not the digest.**

**The verdict rides the synthetic (they converge).** A data-local walk reads `forked` (≤ 1 sealed branch past the
fork — reconcilable) or `disputed` (≥ 2 sealed — terminal, reincept), inv 13/17, with the seal **derived** from the
held events (the highest cleanly-linear seal-advancer). The synthetic **carries** that reading. **Both the value and
the verdict are pure functions of the held event set** — no arrival-order dependence (the F2/H1 fix; a divergent
chain's "frozen" is a **merge-origination** posture, not the reading; §1i / inv 13). Identical held sets yield an
identical verdict **and** an identical value; a settled fork drops both back to the canonical tip (verdict → Active,
value → the real tip SAID), in lockstep, on every node. *(The `chainEffSaid` and `transientChainState` of §1h now
**converge** — the synthetic itself carries the forked/disputed reading.)*

**The value can't hide a revocation (cold B1 — verdict-based, refuse *any* non-single-tip chain).** A consumer's
*trust* decision reads the **verdict** (from held events), never branch content. **Any non-single-tip state —
`forked` *or* `disputed` — grounds no new trust → fail-secure refuse** (document-policy §F / inv 8): a `forked`
issuer IEL can't advance past the fork, so a pending revocation (a `Rev` declaring `kills[]`) can't land on a
confirmed tip; if `forked` granted trust, a T1 thief who wins one content race would read "not revoked" and get a
being-revoked cred accepted. So the value can't
*hide* a revocation, and no branch identity is needed. *(A `forked`→refuse degrades an induced fork to a *denial*,
never a *grant*.)*

**The one thing branch-sensitivity gave up (cold B2): forensic eviction-completeness rides the receipt/event-gossip
channel, not the digest.** Cheating-witness eviction needs the **union** of competing sealed events (which witness
double-signed which pair). The old real-digest synced that union for free via anti-entropy; the synthetic doesn't.
This is **not a safety break** — the identity outcome is set-independent, each fork stays detected/attributable, and
incomplete eviction only means "contained again next time" (a liveness/hygiene cost). The events are recoverable
from stored data **iff gossiped**, so **eviction-completeness rides the independent receipt/event-gossip channel
(best-effort, per-node)**, not the effective-SAID anti-entropy. State this so the narrowed claim isn't misread as
"the union is free."

**Convergence rests on propagation** — eventual barring partition, fail-secure under partition. Witnessed events
propagate and are never dropped, so all nodes converge to the **same held state → the same value** (a single tip's
real SAID, or a set-independent synthetic); the un-witnessed adversarial flood is declined by witnesses and
droppable, so it never perturbs the value. Per-node state stays {Active, Divergent, Terminated}; `disputed` is the
data-local terminal reading (≥ 2 sealed branches, walk-found), never a fourth per-node state. **This value is the
universal "has state changed?" comparison** behind token-reuse, deferred-deps drain, anti-entropy, and divergence.

### 1f. The transfer engine — the one sanctioned data-mover
One `transfer_*_events` walk with swappable **source / sink / verifier**: `verify_*` = +verifier, `forward_*` =
sink-only (no verify), `verify_*_with` = streaming callback. Source-agnostic (paged-source trait). **Merge,
anti-entropy sync, deferred-deps replay, local-verify, and CLI streaming all reuse it.** Manual pagination
bypasses tamper-evidence — forbidden [`project_kels_transfer_abstractions`].

### 1g. Merge — the write path
`vdtid` submit → fast sig-check → **merge** (advisory lock + DB txn): re-verify (or `resume` from a cached token
gated by effective-SAID, §1d) → route **normal-append** (~99%, linear non-divergent) / **new-chain** /
**full-path** (divergence / recovery / archival). **Never trusts the DB** — verification is recomputed, not cached
as trust, except behind the effective-SAID gate.

### 1h. Deferred-deps — the cross-chain race
An event can arrive before a dependency on **another** chain (independent gossip). Flow: verifier **collect-mode**
accumulates deferrable failures (`MissingIelEvent`/`MissingKelAnchor`/`MissingSadObject`) and continues soft →
`vdtid` emits a **typed 422** (`DeferredDepsResponse`: the missing deps each tagged with the dep chain's
`chainEffSaid` — which for a non-single-tip chain **is** the verdict-recoupled synthetic, so `chainEffSaid` and the
`transientChainState` forked/disputed reading now **converge**, §1e) → **`witnessd` parks** the message
in Redis (`pending:msg/said/chain`, **secondaries-before-primary** so a crash orphans a self-TTLing primary, never
dangling indexes) → **drains** (replays via the transfer engine / get-post-sad) when the awaited dep commits
(pubsub) or the chain's effective-SAID moves past `eff_said_at_park`.

### 1i. Anti-entropy — silent-divergence repair
`witnessd` periodic loops (per primitive — KEL/SAD/IEL): **Phase 1 targeted** (known-stale prefixes in a Redis
hash → query peers' effective-SAIDs → sync only from peers that differ) and **Phase 2 random sampling** (random
page vs random peer; skipped if Phase 1 had work). The **effective-SAID is the compare key**; sync moves through
the transfer engine.

**A plain by-prefix pull, no branch-assembly-for-repair (first-seen, 2026-07-08).** The effective-SAID delta is the
**trigger** (it moved → re-sync this prefix — the Phase-1 compare). The **fetch** is `since: {your-own-last-seal}.said`
— pull every event after the **querier's** last seal and dedup (SAID-addressable → clean reconcile). This works, for
state above your own last seal, because of **bounded divergence**: a fork can only form after the last seal, so
`since` your seal captures the canonical tip and every **above-seal** competing branch. `since` is **node-relative**:
a node that advanced its own seal past a content fork (accept-first-learn-later — accept `a`, seal-advance, then the
competing `b` arrives below the new seal) reads `b` as **inert** (you can't fork the past → **Active**); a
**fork-first** node still holding the loser at-or-above its **derived** seal reads `forked`, and converges the instant
it comes to hold a **burying seal-advancer** on the winning branch (its seal advances, the loser drops below it →
inert → **Active**), **no repair event required** (the seal-first node's outcome by a different arrival order — the
pure-walk reading, inv 13). *(There is no branch-assembly `since`-drag and no `fork`-commitment fetch — the repair
machinery is deleted; a settled content loser is buried by position, retained by keep-all-data, reached by a plain
by-prefix flat fetch, never gossiped through the value — §1e.)* **Two channels, by design:**

- **In your active window → the effective-SAID delta + `since` fetch** (pull). The value moves on any live-tip
  difference in the window (the canonical tip, or a live-fork surfacing as the synthetic — §1e), so the ordinary
  delta+`since` channel assembles an **unresolved** fork. A **settled** branch (a buried below-seal content sibling)
  does **not** move the value — reached by a plain by-prefix flat fetch, not `since`, so a fresh sink and an
  evidence-holder converge on the canonical tip without chasing the other's buried branch (the spin closed). The
  `since` **response includes the cursor's own siblings** so you learn if the seal you anchor on is itself forked
  (the `Divergent (sealed)` case).
- **Below your own seal → beacon / eclipse residual (out of the value).** A **sealed** event minted below your own
  seal (the harvested-reserve case) is out of the window, so `since` can't reach it and the value doesn't move for it
  — **not a gap**: whoever holds it reads `disputed` directly; a node without it is in the standing eclipse residual
  (inv 8), beacon-delivered if witnessed, inert if not.

So the effective SAID stays load-bearing (cheap change-detector **and** gating value, inv 8). **On a value mismatch
`since:seal` can't close** (chiefly cross-implementation encoding drift of the synthetic — which the pinned type-tag
discipline, §1e, exists to prevent), a node escalates to a **by-prefix flat fetch** (the full retained set) or a
**beacon-driven targeted fetch** — else the anti-entropy loop spins.

- **Send-side ordering (source → sink; the `transfer_*_events` order).** The **source** (ahead) partitions a
  divergent run into sub-batches the **sink** accepts in arrival order — the shared anchor seal first (dedups), then
  the pre-fork run, then each competing content branch, so every event's `previous` is present before it lands
  (`send_divergent_events`). *(There is no `fork`-root sequencing and no trailing repair event — a burying
  seal-advancer, when present, lands **last** like any seal-advancer.)* The **atomic unit** — the competing content
  branches (≤ 64 each) + the burying seal — fits **one `MINIMUM_PAGE_SIZE = 129` page** (area-kel); a ≥ 3-branch
  residual fork's extra branches ride later pages (reconciliation invariant 3).

### 1j. SAD-store write path — the `kind` filter (first-seen hardening, 2026-07-08; ⚠ NOT previously design-reviewed — the encode-review is its first decorrelated pass)

A pure subtraction enforcing **inv 16** at the storage boundary. **The attack:** event SAIDs float free of their
prefix by design (`said ≠ prefix`; the opaque `anchors[]` commitment — area-sel:129). From a **public** issuer IEL
an attacker harvests every `anchors[]` SAID (commitments to the issuer's **lookup-SEL events** — revocation /
rescission `Trm`s); if the SAD store answered a **fetch-by-SAID for an event body**, they look each up → get the SEL
`v1`/`Icp` → recompute `derive(owner, topic, data)` → recover the **lookup-SEL prefix** → correlate the issuer's
revocations, using vdti's own store as the inversion oracle. **The fix:** the `vdtid` SAD-store write path **detects
an event by `kind` and rejects it** — nothing legitimate needs an event body in the SAD store (events live in the
chain log, prefix-addressed — inv 16), so a fetch-by-SAID **physically cannot return an event**. *(A **credential**
is anchored as the **issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** — an immutable SAD,
**not** an event; the content/event `kind` split lets a **public** cred's body be fetched by SAID (intended) while a
**private** cred's body is unpublished. The private-cred privacy interaction is **closed** (inv 16): `cred.said`
appears **nowhere raw** on the public IEL — the issuance commitment, the revocation kill-target
`hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, and the lookup SEL's prefix/said are all hashes of the
high-entropy preimage, so a passive observer can compute none of them.)* Bypass-robust: stripping
the `kind` changes the content → changes the SAID → misses the attacker's harvested *real* event SAID. **`kind` is
required on SAD data** (a clean per-kind store policy — allow content kinds, reject event kinds; the authoritative
classifier, no fragile shape-match). Write it as the **principle** — *"nothing whose SAID must stay opaque is
fetchable by SAID from the store"* (catches a future free-floating opaque SAD type). **Scope to events (by kind)
now** — manifest-role SADs (roster/threshold delta, pins-SAD) also carry identifiers, but their SAIDs are reachable
only *through* a chain you already have the prefix for, so they give the attacker nothing new; events are the sharp
case. **Preferred over adding an availability field to every event.** *(One factual to-do before build: verify
`kind` is populated on every SAD kind.)*

### 1k. Receipt-encoded threshold + on-receiving-node routing (first-seen hardening, 2026-07-08; ⚠ NOT previously design-reviewed — the encode-review is its first decorrelated pass)

The match-check *safety* was verified this session; one *value*-scope point is **[REVIEW-PENDING]**. **Receipt-encoded
threshold:** each receipt carries the **witness-config `threshold`**, so witnessed-detection becomes **count
`threshold`-many agreeing receipts on `(event SAID, threshold)`** — no chain-walk to resolve the in-effect threshold.
On pull the receipts' threshold must **exactly match the chain-authoritative threshold** (the committed witness-config
in effect at that position, never the self-asserted receipt field); a mismatch is **invalid, even if higher**
(faithfulness — a witness misrepresenting one field can't be trusted on the rest; + liveness/DoS; + the `(SAID,
threshold)` agreement makes an inflated receipt disagree with honest ones → detected). The consistent lie (event +
receipts both say 2, real config 4) is defeated because the match is against the **committed SAD**, not the receipt
field. **Value scope (resolved):** the fast receipt-count is a **hint**; the **committed-config match on pull is
authoritative**. The count **defers, not eliminates**, the chain read — it saves the *in-effect-threshold walk*
specifically, **not** the roster/selection (the detecting witness already holds the live roster as mesh state), so
"no chain read" isn't read bigger than it is. Position-deterministic (the config committed
at-or-before the serial); a stale-config witness emits a non-matching receipt → discarded (a liveness cost around
config changes, not a safety hole). Composes with the key-window gate: a valid receipt needs {valid sig, inside
key-window, threshold-matches}. **On-receiving-node routing:** the mesh is witness-only + encrypted; the event body
never floods (targeted transfer), only receipts flood. Flow: user → their **preferred witness** (usually *not*
selected — fine) → that witness **computes the selection locally** from `(prefix, serial)` + the roster it holds →
routes the body to the ~`signers` selected witnesses → they receipt + sub-gossip the body → **receipts flood** → the
preferred witness answers "witnessed?" **from receipts alone** (no body, no walk) → the body is **pulled on-demand**
only when the content is wanted. Not load-bearing that the user reach the selected witnesses. **Keep straight:**
*witnessed*-detection (is it backed?) is distinct from *disputed*-detection (data-local, ≥ 2 sealed branches); they
compose — the receipt-threshold makes "should I pull" cheap, disputed stays a data-local re-validation.

## 2. Mined from kels (carries; confirm in build)
- Redis park-map **write-order invariant** (secondaries before primary; `DepRef` variant order is load-bearing
  for park-record SAID determinism — don't reorder).
- The per-primitive `verify` / `forward` / `verify_*_with` / `collect_*_saids` API surface.
- `compute_prefix_effective_said`; the post-merge cache-update + pubsub-publish path.
- Advisory-lock + single-txn-per-merge discipline; fast upfront sig/structure rejection before the lock.

## 3. Superseded — do NOT carry forward
- **The `eventsd` / `sadd` split** (vdti's *own earlier* conception, mirroring kels' `kels`/`sadstore`) →
  **merged into `vdtid`** (read-path hops, §1a). ⚠ fix `project_vdti_compacted_only_submission`.
- **kels' separate `registry` / `mail` / `identity` daemons + old taxonomy** (`Cnt`/`Upd`/`Sea`/`Evl`,
  `is_contested`) → vdti features are **libs**; taxonomy is the first-seen model's (`Icp`/`Ixn`/`Rot`/`Wit`/…, no `Cnt`, no `Rec`/`Rpr`).
- **kels' re-verify-every-write** (`completed_verification` each submit) → vdti **token-cache + effective-SAID +
  `resume`** (§1d). The kels code is the correctness baseline; the cache is the scale refinement.
- **"gossip" as a service name** → `witnessd` ("gossip" stays the pattern name).

## 4. Open / route to the adversarial pass
- **`vdtid` ↔ `witnessd` transport** — kels uses HTTP between `gossip` and `kels` services. Keep HTTP, or
  local IPC? (Affects the typed-422 / park / replay path.)
- **Redis** for park map / stale-tracking / cache — kels' choice. Carry, or reconsider a single backing store?
- **The witnessed effective-SAID source** for to-tip consuming decisions (§1d caveat) — exactly how a consumer
  obtains a federation-gossiped / multi-source effective-SAID. Cross-ref `vdti-area-federation-witnessing.md`.
- **Feature daemons** — do any features keep a thin daemon (kels `registry`/`mail` shape), or are all features
  purely client-side libs over `vdtid`? Jason leaned **tight**; confirm "no feature daemons."

## 5. Drift → land backlog
- Write the services/architecture doc under `docs/design/` (the `lib/vdti` + `vdtid` + `witnessd` boundary, the
  effective-SAID/transfer-engine spine, deferred-deps, anti-entropy).
- Define the `lib/vdti` crate layout (verifiers/tokens, transfer, merge, resolvers, effective-SAID, deferred-deps,
  custody, compaction) + the thin `vdtid`/`witnessd`/`cli` binaries.
- **Fix `project_vdti_compacted_only_submission`** (`eventsd`/`sadd` → `vdtid` + `witnessd`).
- **Buried-content-aware fetch (keep-all-data).** `vdtid`'s fetch endpoint must expose **buried** events (kels'
  `get_archived_events` shape), so a walk that returns the full graph/history also surfaces events **buried by a
  burying seal** (a content loser dropped below the seal by position + descent, retained by keep-all-data — inv 13/17,
  never dropped). *(Not for detecting a delayed un-rescind — kills are always sealed, there is no un-rescind, see
  `vdti-area-sel.md` §1.)*

## 6. Confidence / what's owed
- §1a–§1i — **high** on the decomposition + machinery (grounded in the kels `main` code + Jason's decisions). The
  *mechanics* are battle-tested; vdti's deltas (merge chain+SAD, token-cache refinement, witnessd rename) are
  Jason-confirmed.
- §4 — transport + backing-store choices are confirmables, not blockers.
- Owed: Jason's confirm on §4; the build itself (this note is the map, not the territory).
