# KERI/ACDC vs vdti — convergence, differentiators, and the ex-member-issuance deep-dive

**Status: comparison note.** Merged 2026-07-10 from two sources — a broad positioning discussion
(2026-07-06) and a keripy-grounded deep-dive on ex-member issuance / backdating. Ground truth for the
deep-dive is keripy, read directly (the sandboxed research agent couldn't reach it). The broad
differentiators below carry **[TO VALIDATE]** where the KERI side is design-level knowledge (KEL,
witnesses, receipts, first-seen duplicity, ACDC, delegated + group AIDs, weighted multi-sig,
rotation/recovery) not re-checked against keripy or the whitepapers — validate before banking a
comparative claim.

## The most important bit

Both systems recover ordinary key compromises the same way and both lean on rotation hygiene. 
They diverge only at **equivocation** — two validly-signed competing histories — and the split is
what each does with the **second** event. **KERI ignores it:** the duplicity is watcher-local
out-of-band state, the identifier stays alive, and consumers decide which history is real — a
decision the data doesn't fix, so two honest verifiers can disagree and never converge. **vdti
accepts it:** two competing seals at a position is admitted to the log and read, from the data alone,
as **`disputed`** — the identifier is provably dead, every verifier agrees, and the owner rebuilds
out of band. You pay a heavier recovery to buy a deterministic, observer-independent verdict about a
trust anchor.

**The current signing key is the killswitch — never a takeover.** Under single-stream pre-rotation
the current signing key **is** the reserve that was revealed to author the current sealing event, so
a thief can re-reveal it in a **competing rotation at the same serial** → two seals → `disputed`.
That is the brick: your current signing key **plus a coerced witness quorum** can dispute you (you
probably lose — the determinism price). It **cannot take you over** — a takeover needs the _next_,
committed-but-unrevealed reserve to rotate forward and win. And it reaches only the **current** seal:
a below-seal straggler is declined (the witness mirrors the seal-cap), or an old exposed key would
backdate the same trick. The collusion is the hard part — the second seal needs `2·threshold −
signers` self-incriminating double-signers (federation §1e), so the real bar is **your key _and_ a
byzantine federation majority.**

**And "you" here is a device, not an identity — that's the point.** The brick above is a **KEL**
(device) event. An identity is an **IEL — a threshold over device KELs** (§1), so a bricked device is
an **eviction** (`Evl`-cut the dead KEL), not an identity loss: the identity continues on the
remaining threshold. Your device getting bricked is what devices are _for_. Three caveats keep this
honest: it needs **roster redundancy** (`roster > threshold` — a singleton identity has no device to
absorb the loss, it _is_ its one KEL); the **identity itself** can still brick, but only at the far
higher bar of **threshold-many member devices double-participating + witness collusion**; and it
assumes **distinct custody** (a correlated compromise of threshold-many devices meets the threshold
and takes the identity, exactly as a correlated witness compromise does one layer down). KERI can
build threshold identifiers too (group / multi-sig AIDs), but it puts the multi-sig **inside the
identifier's own key log**; vdti keeps identity governance in a **separate** log from any device, so
device churn never touches it (§1 — the KEL/IEL split; **[TO VALIDATE]** the overlap with KERI group
AIDs).

## The honest starting point: the backbone is KERI

After subtracting complexity — the repair-completeness proof, root-condemnation, the T3 reserve, explicit
archival, all deleted in favor of **burying + the spine** — vdti's core has converged on KERI's proven model:

- a hash-chained key event log,
- witnesses giving receipts,
- first-seen duplicity detection,
- recovery by superseding rotation.

This is a **good** outcome, not a failure. That core is the minimal correct design for decentralized key
management; you land on it by subtracting, not by accident. The failure mode would have been keeping the NIH
machinery as false differentiation.

## Where vdti genuinely differs (and how sure we are)

### 1. The KEL/IEL split — identity is a threshold over device KELs

- **vdti:** KEL = one device's key lifecycle (single locus). IEL = the identity, a threshold over member
  KELs. SEL = per-owner data logs.
- **KERI:** the identifier (AID) _is_ the KEL; multi-sig and delegation are properties of that one log.
- **Claim:** separating the device axis (KEL) from the governance axis (IEL) is cleaner — a device rotating
  doesn't entangle identity governance, and the threshold is first-class and separate. The strongest form:
  **one reusable "threshold over KELs" primitive, used for BOTH identities and the federation** (below).
  It is also what **absorbs the device-level killswitch** ("the most important bit," above): a bricked or
  stolen device is an **eviction**, not an identity loss, because the identity never rode on it (given
  roster redundancy + distinct custody).
- **[TO VALIDATE]:** KERI has **weighted multi-sig, delegated AIDs, and group AIDs** that overlap the IEL's
  ground. Confirm the IEL is a structural improvement, not a rename of KERI delegation/group identifiers — and
  that KERI doesn't already unify identity + witness-pool the way the IEL does.

### 2. Federation as a restricted IEL → witnessing-as-a-service

- **vdti:** the federation is a restricted IEL — a governed, rotating, evictable threshold over witness KELs —
  with structural safety floors (roster ≥ 4, signers ≥ 3, majority, availability). A user binds to a
  federation and _consumes_ witnessing; they never run witnesses.
- **Adoption thesis:** one wall for KERI is that "be witnessed" and "run witnesses" tend to be the same act, so a
  user typically needs infrastructure and the skill to run it — part of why adoption skews expert / enterprise.
  vdti splits them: **witnessing becomes a service run by trusted operators.**
- **Safety property (the non-obvious part):** you offload **operation, not trust**. End-verifiability keeps
  trust with your keys (an operator can't forge you — they never hold your keys); `< threshold` byzantine
  members are bounded and attributably evicted; the **floors make a malformed federation unhonored by the
  verifier**, so a non-expert can trust an operator _without auditing it_. That last point is why the
  byzantine/floor work is the adoption foundation, not just correctness hygiene.
- **The honest cost (the disadvantage vs KERI):** because you don't run the witnesses, **you can't
  tell them to stop.** In KERI, running your own witnesses gives a unilateral **freeze** — on
  suspected compromise you halt witnessing and deny an attacker any witnessed event (malicious content
  _or_, if they also hold your reserve, a takeover rotation) while you recover. vdti has no such
  switch. Its value is bounded, though: it is a detection-race either way (a fast attacker acts before
  you would halt), it is a self-DoS lever (a compromised owner-key could freeze your own identity),
  and in the case it uniquely helps — **both** signing key and reserve compromised — freezing only
  defers an inevitable reincept. The **reserve-theft takeover is shared with KERI**: if someone
  rotates your next position before you do (they hold your un-revealed reserve), you have lost
  control → **reincept + notify out of band**, the chain carrying no structural signal. vdti's
  one-sealing-per-position rule makes a _late_ competing rotation a first-seen-**declined** sibling
  (no durable grief — federation §1e), but the _rotate-first_ takeover is inherent to pre-rotation,
  not a vdti-specific gap. Net: vdti trades the run-your-own-witnesses freeze for **zero-infrastructure
  adoption** — and the freeze's cost (the infrastructure + expertise to run witnesses) is one of
  KERI's adoption walls.
- **The counterweight (a marginal security gain — it splits _one_ vector, the brick):** because you
  **don't** run the witnesses, coercing **you** does **not** let an attacker unilaterally **brick**
  the prefix (force `disputed`). A brick needs a witnessed competing **sealed sibling**, and the
  independent federation **declines** the second one (one-sealing-per-position, federation §1e), so a
  forced `disputed` additionally needs **federation-majority collusion**, not just the identity
  holder — and even that isn't enough alone, since witnessing is over a **validly-signed** event, so
  the attacker still needs **your** keys to author the sibling (you cannot double-witness _nothing_).
  That is **two independent compromises**, and the colluding witnesses self-incriminate (a provable
  double-sign → eviction). In KERI, where the operator runs the witnesses, coercion could yield
  witnessed duplicity in one act. **What it does _not_ stop is a coerced _takeover_:** forcing the
  operator to extend the tip with a `Rot` to the attacker's key is a clean linear extension,
  witnessed like any other event — lost control → **reincept + notify out of band**, the KERI-shared
  case above. So the split is real but **marginal**: it raises the bar on bricking, not on a coerced
  tip-rotation.
- **The witnessing posture is itself a security _and_ reliability strength (2026-07-11):** the live-quorum
  compromise (path (b) in *Direct mode is a bad idea* — the _only_ remaining way to backdate or brick) is a
  **high bar by construction**, and the liveness anchor stays **available** rather than best-effort. The vdti
  deployment model **mandates** it on three axes: witnessing is run by **disjoint operators** (hard to bring
  down; a forced `disputed` needs a self-incriminating cross-operator double-sign — federation §1e), the
  witness keys are **HSM-backed** (operators who can afford the hardware hold them in hardware → resist
  extraction, raising the path-(b) bar), and operators run at **high availability** (the liveness anchor is
  reliable — **not** a spotty best-effort gossip mesh, whose unreliable propagation would weaken the
  first-seen / liveness guarantee the whole model rests on). A typical **self-run** witness (commodity infra,
  no HSM, few or correlated hosts, best-effort uptime) lowers every one of those bars. **[TO VALIDATE —
  comparative posture, not a protocol claim]:** this describes the vdti _deployment model_ (mandatory,
  disjoint, HSM-backed, HA operator witnessing) vs. typical self-run KERI witnessing — KERI witnesses _can_ be
  professionally operated too, so confirm the comparison is against typical adoption posture, not KERI's
  ceiling.
- **[TO VALIDATE — the most important check, because it's the pitch]:** KERI witnesses **can already be run by
  third parties**, so "offload witnessing to operators" is not obviously novel. vdti's actual contribution
  appears to be the **governance + trust-bounding around the witness pool** (the federation-as-IEL: rotation,
  eviction, the clock, the floors) that makes it _consumer-safe by construction_. **Confirm KERI lacks an
  equivalent governed, trust-bounded, first-class witness-pool primitive.** If KERI already enables a safe
  managed-witness service, the "huge win" is a better-formalized version of something KERI enables, not a new
  capability.

### 3. `said != prefix` (two-hash derivation)

- **vdti:** an inception event's SAID ≠ its prefix (two separate hashes), so logging event SAIDs doesn't leak
  the prefix — correlation resistance.
- **[TO VALIDATE]:** check KERI's AID/SAID self-addressing derivation — whether a KERI AID has the same
  correlation exposure (coupling the inception SAID to the identifier) or already separates them. Real gap if
  coupled; parity if not.

### 4. Forked / Disputed formalization + effective-SAID — a formalization, not a new capability

- **vdti:** an explicit Forked/Disputed state machine + effective-SAID synthetics (a queryable divergence
  state).
- **Honest read:** KERI already has **duplicity detection**; this is a cleaner _formalization_ of the same
  concept, not a new capability. Modest differentiator. **[TO VALIDATE]** whether the queryable/synthetic-SAID
  framing offers anything KERI's duplicity handling doesn't (sharpened by the deep-dive checklist below).
- **The genuine differentiator (2026-07-11) — deterministic, observer-independent _resolution_, not detection.**
  Both systems _detect_ equivocation; the difference is what _resolving_ it costs. vdti has **no superseding
  recovery** (burial is forward-only by position), so two **accepted** seals at one serial has **exactly one
  meaning** — witness collusion — and the verdict is **forced, deterministic, and identical on every node**
  (`disputed` → reincept), because a collision is irrecoverable by construction (both reveal the same key but
  commit different next reserves → neither can bury the other; kel/compromise §The live-tip dispute). KERI's
  **superseding recovery** buys **in-band recoverability** (a recovery rotation can override earlier events), but
  then a conflicting event at a sequence number is **ambiguous** — legitimate recovery vs malicious duplicity —
  needing precedence rules to adjudicate. So the trade is real and **not** a strict win: vdti spends
  recoverability to buy an **unambiguous, globally-consistent** resolution — the right trade for a trust anchor
  whose product is a data-alone, same-answer verdict; KERI spends that determinism to buy recover-without-reincept.
  **[TO VALIDATE against KERI specs]:** KERI's superseding-recovery + duplicity precedence rules — we are **not**
  the KERI authority; confirm the contrast against keripy before asserting it.

### 5. Policy on documents + the SEL shape

- **vdti:** a formalized policy layer on documents; SEL = structured per-owner data logs;
  revocable-without-reissue issuance (a credential is a direct-anchored SAD validated as-of its anchoring
  position — the deep-dive below is the worked treatment).
- **[TO VALIDATE]:** compare against **ACDC** (rules, edges, schema, graph) — whether vdti's policy layer is a
  genuine gap or a different expression of what ACDC already does — and against **TEL** (the transaction event
  log / credential registry) for the SEL shape.

## Direct mode is a bad idea — three independent reasons

- **Structural — the deepest (2026-07-11):** a static signed log has **no intrinsic "now."** Verifying a
  chain purely by replaying its events — a direct, un-witnessed mode — gives no way, **from the data alone**,
  to tell the real chain from a fabricated alternate history minted by a **total historical key compromise**
  (the target positions' signing + witness keys). Timestamps don't anchor it — they're forgeable. So an
  un-witnessed log has **no answer to "what is current,"** and the **backdate is unavoidable** there.
  **Witnessing is the liveness anchor:** a live quorum's fresh receipts are the data-level proxy for "this
  happened now, and honest infra saw it first." A backdated event **cannot obtain fresh receipts** — the
  honest quorum first-seen-declines it, or it lands below the seal (the witness mirrors the seal-cap) — so the
  only paths left are (a) **forge the receipts** = break the witness signatures (outside the crypto threat
  model) or (b) **compromise the live quorum now** = a live attack, never a cheap historical one. This is the
  _fundamental_ security reason for mandatory witnessing; the two below are its consequences. **We demand it.**
- **Technical (established):** an un-federated `Icp` forces the merge engine to handle multi-branch /
  retroactive-recovery cases it can't cleanly bound. Subtract the case, keep the guarantees.
- **Product:** direct mode = "run your own witnessing / no federation" = _exactly_ the KERI adoption problem.
  It reintroduces the burden the federation model exists to remove, so it contradicts the entire value
  proposition.

All three point the same way: forbid un-federated inception; every chain federated + witnessed from birth (the
`Fcp`-rooted infra is the substrate exception). **DECIDED (2026-07-07): direct mode is removed** — every
identity is federation-witnessed.

## The defensible position

Take KERI's verifiable core as-is. Differentiate on **the KEL/IEL split** (one "threshold over KELs"
primitive, reused for identities and the federation) and **witnessing-as-a-service** (operators run the
witnesses; users keep their keys and end-verifiable data). _If_ the [TO VALIDATE] items hold — especially #2 —
the pitch is **"KERI's proven backbone, with the operational burden lifted onto operators who can't betray
you,"** which is a stronger position than "a new protocol."

## Deep-dive: ex-member issuance / backdating (keripy-grounded)

Ground truth = keripy, read directly. Specs not re-read this pass; KERI core semantics cited from the code +
foundational model, flagged where corroborated rather than directly read.

**The question.** Group X authorizes members to issue credentials. Member A is removed. Can A forge a **new**
cred today claiming old authority? Does closing it force reissuing the legit old creds, or lean on out-of-band
infra?

### Q1 — authority-by-membership: chained ACDCs + edge operators (and multisig group AIDs)

ACDC expresses "issuer authorized via X" two ways:

- **Chained credentials** with edge operators **I2I / NI2I / DI2I** — `vdr/verifying.py:336 verifyChain()`.
  **I2I** ("issuer-to-issuee"): the downstream cred's **issuer must equal the upstream (authority) cred's
  issuee** (`verifying.py:365` — `if op == 'I2I' and issuer != creder.attrib['i']: return None`). So "X
  granted A a membership/authority ACDC; A issues downstream creds edged back to it." This is the `del`-analog
  (delegation). (`DI2I` = delegated-issuer; `raise NotImplementedError()` at `:369`.)
- **Multisig group AID** — the group issues **as the group** from the group's own KEL/registry (see Q3).

### Q2 — revocation timing: gate-current (TEL tip), retroactive

`verifyChain` resolves the node (authority) cred's status as **`tever.vcState(nodeSaid)`**
(`verifying.py:376`) — the **current** TEL state, i.e. the latest registry event (`vdr/eventing.py:526
vcstate()` / `:422 state()` build state from the **latest** `sn`/`eilk` ∈ {iss, bis, rev, brv}). There is
**no "as-of the downstream cred's issuance" parameter** — it's read at tip. So **revoking the upstream
authority cred fails the edge for every downstream cred, old and new alike** — gate-current, retroactive,
all-or-nothing per authority-cred. Identical to our DQ1 gate-current floor behaviour.

### Q3 — backdating (the crux): the chained model has the fork; the multisig model resolves it

- **Chained-ACDC model: same fork, not specially closed.** Nothing binds _when_ A issued a downstream cred to
  A's authority being current then. `verifyChain` checks only (a) the I2I issuer==issuee link and (b) the
  authority cred's **current** status. So if A's authority cred is **not revoked**, A keeps issuing valid
  downstream creds forever (no issuance-time bound). To stop A you **revoke the authority cred → gate-current →
  kills A's legit old downstream creds too.** No grandfathering. = the fork.
- **Multisig group-AID model: resolves it structurally.** Issue **as the group**: the issuance (TEL `iss`) is
  anchored in the **group's own append-only KEL** via a seal, signed by the group's **current** signing
  threshold. Then:
  - **member rotation** = a group KEL rotation dropping A's key;
  - **old creds** anchored at pre-rotation KEL positions validate **as-of that anchoring key state** (which
    included A) → **stay valid, no reissue**;
  - **A forging new creds** would need to anchor in the group KEL and satisfy the **current** threshold — A is
    out, and A **cannot append to the group KEL's past** (append-only + witnessed) → **blocked**.
    No revocation-kill, no reissue. _(Rests on KERI's foundational as-of-anchoring-key-state validation —
    corroborated from the model + the seal-anchoring in `vcstate`'s `a` seal, not a line re-read this pass.)_

### Q4 — watcher/first-seen: an equivocation tool, NOT a credential-issuance-time tool

KERI's temporal/ordering anchor is the **first-seen number** (`fn`, `FirstSeenReplayCouples` —
`core/counting.py:62,221`; `core/parsing.py:1837+`), assigned **locally** by each observer when it first sees
a KEL event, used for **duplicity/equivocation detection** (`core/eventing.py:4189+` "maybe duplicitous"). It
is **watcher/witness-local out-of-band state**, and — critically — **the credential authority/revocation path
(`verifyChain`) never consults it.** So KERI does **not** use first-seen to bound _when a credential was
issued_; first-seen solves KEL equivocation, a different problem. KERI has **no** magic issuance-time tool for
the backdating question.

### Bottom line

KERI/ACDC's **chained-credential** authority makes the **exact same gate-current tradeoff** as our
foreign-`grp` fork: block an ex-member only by revoking their authority cred, which retroactively kills their
legit old creds (forced reissue). It has **no** out-of-band trick that beats this — first-seen is for
equivocation, not issuance-time. **But KERI's multisig group-AID model resolves the actual requirement**
(rotate the issuing set without reissue, block ex-members) by making issuance a **governed write on the
group's own append-only chain**, validated **as-of its anchoring position** — old creds grandfather across
rotation, removed members can't append. That is exactly the "issue as the aggregate from its own chain"
direction. **vdti mapping (B1 fail-secure rework 2026-07-09):** revocable-without-reissue issuance ⇒ **a
credential is an anchored SAD issued by the issuer IEL** — issuance = the issuer anchors the issuance
commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` on its IEL via an `Ixn` (T1), so it validates
**as-of the anchoring position** and grandfathers across rotation; revocation = a **`kills[]` declaration** on
the issuer's witnessed IEL `Rev` + a `{Icp, Trm}` lookup SEL (fail-secure, read on the same fresh walk).
**Not** a foreign-`grp(X, group)` splice (the reshape dropped foreign-`grp` and `policyPin` entirely): a
unilateral-claim splice can't be made forgery-proof end-verifiably; issuing-as-the-aggregate — each cred
anchored under the issuer IEL — sidesteps the whole fork.

## Validation checklists (do against keripy / KERI + ACDC specs)

### Broad differentiators

- [ ] IEL vs KERI delegated + group AIDs / weighted multi-sig — genuine structural gap? (#1)
- [ ] **Managed/third-party witnesses in KERI — is a governed, trust-bounded witness-pool service already
      possible?** (#2 — the pitch depends on this)
- [ ] KERI AID/SAID derivation — same prefix-correlation exposure, or already separated? (#3)
- [ ] Duplicity handling in KERI vs the Forked/Disputed + effective-SAID framing (#4)
- [ ] ACDC rules/edges vs the document-policy layer; TEL vs the SEL log (#5)

### First-seen model (2026-07-07) — verify against keripy

Added after the first-seen pivot + two-tier collapse. The vdti side is framed from the current model; the KERI
answers need the keripy scan. **Questions, not claims** — don't bank the KERI side from memory.

- [ ] **First-seen, exact semantics.** vdti uses per-witness first-seen (a witness signs the _first_ event it
      sees at a position, _per tier_, and refuses later same-tier copies). Confirm KERI's first-seen is the
      same per-witness rule, and whether KERI has the **cross-tier co-sign** (`{≤ 1 content, ≤ 2 sealed}` at
      one serial) or treats a position as strictly one-event.
- [ ] **Two tiers / no recovery key.** vdti collapsed to T1 (signing) / T2 (rotation) and **dropped the
      recovery key** — recovery is a plain rotation. Does KERI have a distinct recovery reserve beyond
      pre-rotation, or is pre-rotation its only reserve? (No recovery key ⇒ convergence; a recovery key ⇒ vdti
      diverged deliberately.)
- [ ] **Recovery = root-bury vs KERI superseding rotation.** vdti recovers by rotating at the _first_
      compromised position (the whole run below dies on ascent). Is KERI's superseding-recovery the same
      "attach at the root, deadness-ascends" mechanic, or does it attach/supersede differently?
- [ ] **Disputed/forked outcome, not just detection.** KERI _detects_ duplicity; vdti formalizes the
      **outcome** (content fork → recoverable/buried; key-change fork → terminal/reincept) plus the
      **observable-breach guarantee** (fork-cost = forced attributable double-signers). Does KERI formalize the
      terminal-vs-recoverable outcome, or stop at "duplicity detected, handle out-of-band"? (Sharpens #4.)
- [ ] **SEL vs TEL/registry.** vdti's per-artifact SEL is anchored to its owner IEL for authorization + the finality-floor, and is its own witnessed chain for fork-prevention (witnessed-SEL redesign). Map to
      KERI's **TEL** (transaction event log / credential registry) — same "data log anchored to a KEL" shape,
      or different? (Extends #5 from ACDC to the _log_ layer.)
- [ ] **Witness/governance bounds.** vdti added a **roster cap (32)**, an **authorization floor on governance**
      (`t_govern` / `t_authorize > |roster|/2`), and the **witnessing floor** (`threshold > signers/2`,
      fork-cost = `2·threshold − signers`). Does KERI constrain its witness threshold (`toad`) with a
      majority/attribution requirement, or leave it unconstrained? (Feeds #2 — the federation pitch rests on
      these being a real governance layer KERI lacks.)
- [ ] **Freshness + witness-sig monotonicity.** vdti's dormant-forgery defense: receipts must march forward in
      time, so a harvested _retired_ witness key can't forge onto an active chain. Does KERI defend the
      harvested-old-witness-key attack, and how?
