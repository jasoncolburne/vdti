# vdti — area note: SEL (single-owner data log)

**Status: SECOND CUT (2026-07-12) — the witnessed-SEL redesign.** Supersedes the FIRST CUT's
**divergence / witnessing** model (an unwitnessed SEL that "rides the IEL's witnessing," resolved
cross-layer only, under the theorem _a valid SEL fork implies an IEL fork beneath it_). That model was
**unsound** — an owner can equivocate its own SEL under a **linear** IEL (§1c), so the theorem is false.
The shape-level decisions carry unchanged and are **re-homed** here: the kind set (now +`Sea`), the two
tiers, the prefix derivation, cred-as-a-direct-anchored-SAD, the lookup mechanics, the fail-secure /
fail-open reads, and the three axes (count / tier / anchor-kind). This note is written in the
**`deadness ascends`** orientation (§1e); the system-wide `descends → ascends` sweep is a **separate
change** (§5).
**Invariants referenced:** [inv 2] single-locus, [inv 3] layers-isolated, [inv 4] manifest-up/pin-down +
the anchor matrix, [inv 5] pin-floored, [inv 10] lookup-SELs, [inv 12] IEL self-pricing, [inv 13]
divergence, [inv 14] federation/witnessing, [inv 15] inception/pin, [inv 16] addressing + correlation,
[inv 17] spine + data-local detection.

## Sources

- The FIRST-CUT area note (this file's prior content) — **the delta-comparison guide**; correct on shape,
  wrong on divergence/witnessing (the retired theorem, unwitnessed SEL, `deadness descends`). Mined, not
  copied.
- `.working/sel-witnessing-redesign.md` — the settled redesign this note encodes.
- `docs/canon/vdti-area-iel.md` (the structural mold — the SEL is now a witnessed chain in the IEL's
  shape), `docs/canon/vdti-area-federation-witnessing.md` §1e (the witnessing floor / first-seen / disputed
  detection the SEL now inherits) — **§1g Decision 1 is REVISED by this note** (the SEL _is_ witnessed now).
- `docs/canon/vdti-area-shared-documents.md` (doc / governance / version SELs), `…-delegation.md`,
  `…-document-policy.md` §F (the kill lookup SELs).

## 1. The current SEL model

### 1a. SEL = a single-owner data log

- **SEL = a single-owner data log.** Owner = exactly one **IEL** (its prefix). No policy, no roster, no
  multi-party governance internally [inv 2]. Layers isolated: a SEL pins/anchors only its owner IEL, and
  its finality floors down to that IEL [inv 3].
- **Prefix = the `Icp`'s whole-content two-pass digest** over its populated fields — **`owner`** + `topic`
  + `data` (+ `content: true` for a content SEL, + `lineage` for a re-establishable value lookup — §1f),
  shorthand `derive(owner, topic, data)`. It is
  the same whole-content prefix every event has, so **any** populated `Icp` field enters it (adding a `pin`
  would break recomputation; the `Icp` therefore carries **no** `pin` and is floored by its serial-1 event
  — §1h). **`owner`** = the owner IEL prefix, **`Icp`-only and immutable** (one owner for life). `topic` =
  an application discriminator (opaque bytes to the chain — inv 3). `data` (**optional**) = a nonce
  (non-discoverable / private) or meaningful bytes (discoverable / recomputable — e.g. a kill locus's
  grant-instance). **`topic` + derivation replace KERI's registry identifier** — no registry object exists.
- **★ `data` entropy is load-bearing.** Where `data` gives an **unpredictable** prefix (a private SEL — the
  nonce that makes the prefix unguessable), it **MUST be high-entropy** — else an attacker brute-forces it,
  recomputes the prefix, and confirms / de-anonymizes the locus. **Digesting `data` does NOT substitute** —
  a hash of low-entropy input is still brute-forceable; the _input_ must carry the entropy. Where `data` is
  **deliberately discoverable** (a lookup-SEL `data = said(grant-instance)`), unpredictability is not the
  goal — the protection is **owner-rooting** (only the owner IEL anchors events at the locus → prediction ≠
  forgery), not entropy.
- **Classification = blind-recomputability, not discoverability — and it is carried structurally.** A SEL is
  a **lookup SEL** _iff_ a verifier **blind-recomputes its prefix** `derive(owner, topic, data)` from data it
  already holds; a **content SEL** is one you are _handed_. The distinction now rides a structural field: a
  content SEL's `Icp` carries **`content: true`** (a lookup's does not), verifier-enforced against the v1's tier
  (the biconditional, §1f). **A credential is neither — it is a direct-anchored SAD, not a
  SEL** (issuance SEL dropped, B1 fail-secure rework 2026-07-09): the issuer anchors an **issuance
  commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** on its own IEL via an `Ixn`, and _that_
  anchor is the validity proof — the holder **presents** the cred, it is **never looked up by address**.
  **Revocation** is a **`kills[]` declaration** on the issuer's **witnessed** IEL `Rev` (fail-secure by
  default, inv 8/10) + a content-addressed **lookup SEL** giving a fail-open fast path (§document-policy
  §F). **Custody rule:** direct-anchor an immutable SAD that is _presented_; SEL-wrap anything _mutable_ or
  _looked-up-by-address_ (inv 16).

### 1b. Kinds — six (the `Sea` seal-advancer is new)

| SEL kind | Count | Tier | Anchored by (IEL) | Seal-advancing? | Finality |
|---|---|---|---|---|---|
| `Icp` | `t_use` | **T1** | — (not anchored; v1 via `previous`) | no | delayed — `owner` (immutable) + `topic` + `data`? + `content: true`? (content only) + `lineage`? (re-establishable value lookup only); **no manifest, no `pin`** (stays recomputable). |
| `Ixn` (content) | `t_use` | T1 | `Ixn` | no | delayed — payload SAD(s) (the `payload` role, **required** — always ≥ 1) + re-`pin`; **≤ 1 per SEL per IEL `Ixn`** (counting content); the **divergeable / first-seen content kind** (buriable). A payload-less `Ixn` is malformed. |
| `Pin` (pin-only re-pin) | `t_use` | T1 | `Ixn` | no | delayed — re-pins the SEL→owner-IEL floor (top-level `pin` only, **no manifest**); the **pin-only re-pin at any serial**. Its serial-1 instance is the **issuance floor** (incept-and-sit); a pure re-pin is always a `Pin`, never a payload-less `Ixn` (disjoint). Buriable like content. |
| `Gnt` (grant) | `t_authorize` | **T2** | **`Ath`** | **yes** | **sealed on arrival** — **seals a typed value**: `manifest.grant` names a grant-value SAD kinded under **`vdti/sel/v1/grants/*`** (feature-first naming, any kind ≤ **64 chars**). Instances: the doc-governance grant-doc `G` (`grants/shared-document-governance` — opens editor/commenter periods, shared-documents §1); an **exchange receive-key** (`grants/exchange-ml-kem-1024` — the value-bearing lookup §1f, vdti-area-exchange). Non-buriable; walked back by a `Dth` rescission, never overturned. |
| `Trm` (kill) | `t_govern` (revoke) · `t_authorize` (rescind) | **T2** | **`Rev`** (revoke) / **`Dth`** (rescind) | **yes** | **sealed on arrival** — the SEL kill. `Rev` = a revocation lookup-SEL `Trm` / app-SEL closure; `Dth` = a delegation / doc-membership rescission. Monotone, terminal-on-divergence; can't be overturned or un-done. |
| **`Sea`** (re-seal / bury) | **`t_govern`** | **T2** | **`Evl`** | **yes** | **sealed on arrival** — the SEL's **neutral** seal-advancer (§1d): a re-seal that buries a content fork below its own seal, authored when no natural `Gnt` / `Trm` advances the seal (a plain content SEL) — the SEL analog of the KEL recovery `Rot` / the IEL roster-less `Evl`. Anchored by an IEL `Evl` (empty for a pure re-seal, or the `Evl` carries a `cut` to evict the colluding owner member(s) atomically). |

**Seal-advancers = `Gnt` / `Trm` / `Sea`** (each carries `previousSeal` — the spine, inv 17). **Any of them
buries** a content fork by advancing the seal past the loser (loser below the new seal → dead —
the SEL analog of the IEL's `Evl`/`Ath`/`Rev`/`Dth` and the KEL's `Rot`/`Wit`, where any sealing event
buries). **`Trm` is the terminal subset** — it advances the seal but admits no successor, so it buries the
loser by winning on tier-rank as the sole sealed branch; `Gnt` / `Sea` are non-terminal (bury by advancing
the seal, the chain continues). **`Sea` is the neutral one** — authored when no natural `Gnt` / `Trm`
advances the seal (a plain content SEL), the KEL recovery-`Rot` / IEL roster-less-`Evl` analog. **Buriable /
tier-1 = `Ixn` / `Pin`**. **Dropped in the first-seen pivot:** `Fld` (the SEL re-seal — its burying job is
now `Sea`, its page-atomic-repair job is gone with the repair machinery) and `Rpr` (no repair event).

### 1c. Witnessing — the SEL is its own witnessed chain (the core of the redesign) [inv 13, 14, 17]

**The FIRST-CUT theorem is FALSE — an owner can equivocate its own SEL under a _linear_ IEL.** IEL anchors
are **opaque** (SAID-only — inv 16, the private-lookup case), so **one IEL `Ixn` can name two competing SEL
events at one `(SEL-prefix, serial)`** in its `anchors[]`, and the IEL cannot dedupe them (it can't tell
two opaque SAIDs are the same SEL/serial). A node that holds only branch A attributes A as the tip and, by
**skip-unattributable** (inv 4 — an anchor whose body a node lacks is skipped, not blocking), never sees B;
a node holding only B reads B. Both read a **linear** IEL and a **single** tip — but **different** tips.
That is equivocation-by-withholding under a linear IEL, so _a valid SEL fork implies an IEL fork_ is false.
(Two _separate_ IEL `Ixn`s naming competing SEL events is fine — IEL order disambiguates convergently; only
the **one-`Ixn`-names-two** case breaks it. A position-token bolted onto the opaque anchor was rejected — it
would leak the SEL prefix onto the public IEL _and_ only work if SELs were 1:1 with IELs, which they never
are.) SELs are **one-to-many** with IELs, so SEL divergence is **not** a function of IEL divergence — the
SEL needs its **own** witnessed state.

**The model — the SEL is a witnessed chain in the IEL's mold:**

- **First-seen at its own `(prefix, serial)`**, threshold-acceptance, **inheriting the owner IEL's
  federation** (same witnesses, no new trust root; selection deterministic on `(SEL-prefix, serial)` +
  the inherited `roster(F @ context)`, and the SEL inherits the owner IEL's witness-config and
  `federationPin` — inv 4:`witnesses` / federation §1e).
- **Content (`Ixn` / `Pin`) → first-seen:** witnesses take the first content event at a position and
  decline the copies; with the **witnessing floor** `threshold > signers/2` (federation §1e) two content
  siblings can't both reach threshold, so an honest content fork **cannot form** — it is _prevented_, not
  detected. The residual (a content fork that forms) is a **witness compromise** owning the intersection
  (fork-cost `2·threshold − signers`) — it reads `forked` (fail-secure) and resolves by a burying
  seal-advancer (§1e).
- **Seals (`Gnt` / `Trm` / `Sea`) → first-seen at the position + retained for detection:** witnesses sign
  the **first** sealed sibling and decline later ones (the sealed twin of one-content-sibling — federation
  §1e, revised 2026-07-11), yet both branches are **retained** so the data-local walk detects `≥ 2`. A
  sealed branch is **never buriable**, so a **second accepted** sealed branch → **`disputed` → reincept**
  (it requires `≥ 2·threshold − signers` colluding double-signers — provable witness collusion). A
  witness-**declined** sealed sibling is **deferred-pending / droppable** (a spent-preimage or partition
  race, no fault).
- **Anchoring and witnessing are distinct roles now.** Each SEL event is still **IEL-anchored** — the
  anchor supplies **owner authorization** (the anchoring IEL event's threshold — a SEL has no key of its
  own) and the **finality floor** (the down-`pin`, inv 5). The SEL's **own witnessing** supplies
  **fork-prevention / detection** (first-seen at `(SEL-prefix, serial)`). The anchor no longer carries the
  fork-prevention it could not deliver (skip-unattributable defeated it); witnessing does.
- **The anchor and the witnessing ride one batch — so witnessing prevents authorship-forgery too, not only
  equivocation.** A SEL event is committed **only as a batch with its owner-IEL anchor**: it is event-kinded,
  so it cannot enter the SAD store (the `kind` filter — vdtid-services §1j / inv 16), and on the event path an
  `Icp` is invalid without its **anchored `v1`** (§1h). The batched anchor is an **owner-signed IEL event**
  the witness validates (its normal IEL-witnessing job), so **witness-acceptance requires owner-authorization**
  — a **non-owner produces no valid anchor → nothing lands at any locus**, value-bearing or private-cred alike
  (there is no "well-formed-but-unanchored event witnessed first-seen"). Witnessing thus closes **both**
  threats: **equivocation** (first-seen at the SEL `(prefix, serial)` — one owner double-authoring two SEL
  events at one position, the hole diagnosed above) **and authorship-forgery** (the owner-signed anchor rides
  the batch). The witness **needn't recompute `derive(owner, topic, data)`** for a lookup SEL whose `Icp` is
  **never published** (inv 16 R4) — it holds the `v1`'s SAID / kind / linkage and the anchor, never the `Icp`
  body (and must not — else `cred.said` would reach a witness); that is a **privacy** property, **not** a
  forgery gap, since the owner-signed anchor closes forgery whether or not the witness can derive the prefix.
  The consumer's **owner-rooting / `Icp.owner` check (inv 15 S1)** is **end-verifiability** — independently
  re-deriving the prefix and re-checking the anchor against the data it holds (trust the data, not the witness)
  — **not** the sole barrier.
- **Privacy — witnesses see SEL structural fields; acceptable trust-infra exposure.** Witnessing the SEL
  puts its structural fields — including a lookup-SEL **prefix** — onto the witness mesh (in the receipt's
  `chain_prefix`, and in the event bodies witnesses sub-gossip). This is **not** a public leak: all mesh
  traffic is **encrypted** (ML-KEM-1024 + AES-256-GCM — federation §1e), so the exposure is to
  **federation members only**, who are **semi-trusted infra** (trusted _not to be generally compromised_ —
  the `< threshold` byzantine assumption — never trusted for end-verifiability). The **credential meaning is
  never a witness's concern** — a witness gates **structure + first-seen + threshold**; the `Icp.owner`
  check, revocation status, and policy live at the **application/consumer** layer (`lib/vdti`,
  document-policy R1), and the data-bearing lookup-SEL `Icp` (carrying `data = cred.said` raw) is **never
  published** (inv 16 R4), so `cred.said` never reaches a witness. A lookup-SEL prefix in a receipt is an
  **unguessable** value decorrelated from the issuance commitment and kill target (three hashes of the same
  preimage), so a witness holding it can only **confirm-a-known-subject** (the residual inv 16 already
  accepts), never invert or bulk-enumerate. **Residual — exfiltration during the compromise window:** a
  witness compromised _before_ its compromise is obvious and it is **cut** (federation `Wit`) could
  exfiltrate the SEL structural data it holds; bounded by (a) compromise being **loud → eviction** and (b)
  the exfiltrated prefixes being unguessable (confirm-a-known-subject only). Same class as the existing
  `< threshold`-byzantine detection residual, not a new hole. **This REVISES federation-witnessing §1g
  Decision 1** ("a SEL is never witnessed directly") — the SEL _is_ witnessed now; the receipt-batching
  "collapses out" claim and inv 16's "no receipt carries a lookup-SEL prefix" clause are superseded (§2).

### 1d. `Sea` — the SEL's neutral seal-advancer (the locked-below-seal residual) [inv 4, 12, 13]

- **Why `Sea` is genuinely needed.** The IEL is **structurally blind** to SEL forks (layer isolation inv 3
  + opaque anchors inv 16): it anchors SAIDs it cannot interpret and seals by its own clock, so **nothing
  at the IEL layer can constrain a seal on account of a SEL fork**. When a witness-compromise content fork
  forms and the IEL then seals **past** the double-anchoring `Ixn`, that anchor is **live _and_ locked** —
  on the canonical IEL chain (so not dead → not severable) but below the IEL seal (so not buriable → the
  locked-portion bound). The live SEL content fork it created is now unreachable by **both** severance
  (§1e) and IEL-rebury. The exit is a **fresh SEL seal-advancer at the tip** that buries the loser below its own seal — and for a
  **plain content SEL** (no natural `Gnt` / `Trm`) that seal-advancer is a **`Sea`** (the neutral re-seal),
  anchored by a **fresh IEL `Evl`** at the IEL tip. (A doc-governance SEL could bury the same fork with a
  `Gnt`, a lookup SEL with a `Trm`; `Sea` is the option for the SEL that has neither.)
  Severance is **not** the SEL's recovery: it is an incidental byproduct of IEL divergences that happen for
  the IEL's own reasons (the common-case cleanup), never something to rely on. The same IEL blindness forces
  **both** halves symmetrically — the SEL can't lean on the IEL to _see_ its forks (→ witness itself) or to
  _resolve_ them (→ own recovery `Sea`).
- **`Sea` is `t_govern`, anchored by an IEL `Evl` (kind-strict `Sea ← Evl`).** It **overrides content**
  (picks a winner among competing branches), so it must be gated **above** content-authoring by the owner's
  governance authority — matching the KEL recovery `Rot` (T2) and the IEL burying `Evl` (`t_govern`). The
  `Evl` is **empty** for a pure re-seal, or carries a **`cut`** to evict the colluding owner member(s)
  **atomically** with the bury (the same timing-attack closure as an IEL eviction, inv 13 — a still-rostered
  culprit would else race a fresh fork at the resolved tip). `Sea` is a busy owner's re-seal channel too —
  the SEL analog of the IEL re-sealing via a roster-less `Evl` (area-iel §1), reusing `Evl`, no new IEL
  kind.
- **`Sea ← Evl` gives the IEL `Evl` an `anchors` role — RESOLVED (Jason 2026-07-12: "put `anchors` on
  `Evl`"; landed in inv 4).** A `Sea` anchor is **back-checked** (kind-strict `Sea ← Evl`, like `Trm ←
  Rev`/`Dth`), so it is _not_ a directly-consumed role and the kind→role gate (S1) is untouched. And `Sea`
  is `t_govern` = the `Evl`'s own count, so there is **no count-laundering** (the original S1 concern — a
  roster change priced at a kill's count). The precedent that an IEL kind carries a role _and_ `anchors` is
  `Ath` (`delegates` + `anchors → Gnt`). inv 12's "no kind both anchors a payload **and** mutates
  establishment state" is restated as **count-integrity** (landed): a `+cut` `Evl` anchoring a `Sea` mutates
  its own roster _and_ anchors a payload, but at **one** count (`t_govern`), so nothing is laundered.

### 1e. Divergence & recovery — `deadness ascends`; deadness-precedence; severance-truncation [inv 13, 17]

- **Directional orientation — `deadness ascends`.** The trust model is foundation-at-bottom (KEL → IEL →
  SEL, built upward); deadness flows along the anchoring edge from a dead authorizer (below) to what it
  authorized (above) = **up**. The rule keeps its statement — **an event whose parent is dead is dead** —
  only the label flips from the FIRST CUT's `deadness descends`. (System-wide relabel = a **separate
  change**, §5; this note is written in the new orientation from the start.)
- **A SEL's state has two independent inputs:** (1) its **own witnessed divergence** (a content fork via
  witness collusion → `Sea`-recover; `≥ 2` sealed → `disputed`), and (2) **inherited IEL deadness** (an
  anchor on a dead IEL branch **severs** the SEL — below).
- **Inherited IEL deadness SEVERS the SEL chain.** When an IEL burial kills a SEL event's anchor, it does
  not merely mark that event dead — it **disconnects the chain**. The SEL's later events were anchored
  **through** that now-dead IEL lineage, and with **no repair event** to re-root, the portion after the
  **earliest** dead anchor **cannot be connected to a valid anchor lineage → cannot be verified** (verifying
  it means trusting the buried IEL branch — a lie). So the SEL is valid up to the earliest dead-anchor point
  and **severed (dead + un-verifiable) from there**; the pre-sever portion stays live; there is **no
  continuation on the same chain**. The severed portion is the **dead-branch author's** work — un-rescuable
  by re-pointing to the surviving IEL branch (a different author). A SEL portion that **pre-exists** the IEL
  fork rides the shared pre-fork lineage → not severed. If no anchor sits on a dead IEL branch, the SEL is
  untouched.
- **`Severed` is a truncation, NOT a fifth state.** It shrinks the SEL to its last live-anchored event;
  after that the chain reads one of the four live states — **Active / Forked / Disputed / Terminated** —
  mirroring the IEL's four-state machine.
- **Deadness takes precedence over `Sea`.** You never bury something already dead. A content fork with one
  **dead** (severed) branch **auto-resolves** to the live branch — the SEL shrinks to the shared tip and the
  surviving author extends from there; **no `Sea`**. Both branches dead → severed at the fork. `Sea` (and the
  sealed → `disputed` escalation) exist **only** for the **all-live** case. **Severance downgrades a
  Disputed:** one of `≥ 2` sealed branches severed → un-verifiable → **not counted** → the reading drops to
  the live branch (recoverable); a Disputed under a **linear** IEL (both anchors locked-live, no severance
  available) stays terminal → **reincept**.
- **Content-fork resolution keys on where the losing anchor sits:** dead IEL branch → **severance** (free,
  common case); live and at/above the IEL seal → the owner's choice (an IEL-rebury → severance, _or_ a
  `Sea`); live and **below the seal** (locked) → a **SEL seal-advancer at the tip** (a `Gnt` / `Trm` if
  natural, else a **`Sea`** — §1d); losing branch **sealed** (`≥ 2`) → **`disputed` → reincept** (no
  seal-advancer can bury a seal). Crossed cases all resolve: SEL-forked-under-a-linear-IEL → a SEL
  seal-advancer (`Sea` for a plain content SEL); linear-SEL-under-a-forked-IEL → severance-truncation; both →
  deadness takes precedence.
- **The full case matrix lands in `sel/reconciliation.md`** (mirroring `iel/reconciliation.md`'s four-matrix
  structure — a correctness proof), not in this note.
- **No true threat at resolution — accommodate the data shape.** The SEL is the owner's own log; a fork is
  the owner's own mess (racing devices / a confused sub-quorum), not external attack. The one real threat —
  **equivocation** on a kill-bearing SEL — is neutralized **upstream** by witnessing (a live fork reads
  Forked/Disputed → the consumer fails secure). So at resolution there's no adversary to race; we just make
  every resulting shape verifiable (end-verifiability).

### 1f. The two axes of a lookup — `content: true` + `lineage` [inv 10, 16]

- **The problem.** A lookup SEL's prefix `derive(owner, topic, data)` is a pure function of fixed inputs
  (no nonce to reroll), so a killed / disputed value lookup **cannot reincept** by rerolling randomness — the
  same inputs recompute the same dead address; and a value's base sits at a **discoverable** address a squatter
  could try to occupy. Two **orthogonal** fields close both, each doing exactly **one** job. (An earlier draft
  collapsed both onto `lineage`, which is what created the content-squat hole — kept apart, they don't.)
- **Axis 1 — `content: true` (the content discriminator).** `content: true` on the `Icp` **⟺ the SEL is
  content** (handed; its v1 is a T1 `Ixn` / `Pin`). **Absent ⟺ the SEL is a lookup** (blind-recomputed; its v1
  is a T2 seal-advancer — a `Gnt` value or a `Trm` kill). The verifier **enforces the biconditional** — it
  confirms the `Icp`'s `content` flag matches the v1's tier: a v1-T1 SEL without `content: true` is **invalid**,
  and a `content: true` SEL with a v1-T2 v1 is **invalid**. The flag **moves the address in both derivation
  families:** the **prefix** is the `Icp`'s whole-content two-pass digest, so `content: true` **rides in
  automatically** (content lands at a distinct prefix); a **flat domain-qualified hash** (the kill `target`,
  §1i) never sees `Icp` fields, so a **content (app-SEL) target appends a literal `:content`** segment there.
  Thread the discriminator **per derivation family** — the field for the whole-content digests (prefix / said),
  the `:content` suffix for the flat hash — and check each site (the prefix change does **not** carry to the
  flat target). **The squat is impossible by construction:** a `content: true` event can't derive **to** a
  lookup address (its prefix differs), and a v1-T1 at a lookup address (flag absent) is invalid — so a lookup
  address only ever holds a **v1-T2** form, and the read path needs **no tier-check**. Content and lookups may
  share `(owner, topic, data)` — they are simply **different addresses** (an app uses one or the other anyway).
- **Axis 2 — `lineage` (lookups only, a pure re-establishment counter).** **Present** (`lineage: 0`, reincept
  `lineage: 1`, `lineage: 2`, …) → a **re-establishable value** (a T2 `Gnt` — a KEM receive-key), found by the
  **positive walk** (below). **Absent** → a **monotone** lookup: a **kill (`Trm`) is always monotone**, but not
  every monotone form is a kill (the slot also admits a non-re-establishable value). **Absent is absent** — a
  no-lineage `Icp` and a `lineage: 0` `Icp` are different whole-content → **different addresses**; nothing
  bridges them. `lineage` now means exactly **one** thing, a re-establishment counter — **content never carries
  it** (content uses `content: true`). For a value chain the **canonical instance is the lowest non-dead
  lineage**; a lineage above a live one is **inert** (owner-rooted → an equivocation attempt fails safe).
- **The kill target mirrors the killed address** [inv 10]. A `Trm`'s anchoring `Rev`/`Dth` declares a `kills[]`
  **target** whose shape follows the thing it kills: a **monotone kill** (cred revocation, delegate / doc-member
  rescission) → **non-lineaged** `hash('{topic}:{owner}:{data}')` (the killed thing has no lineage); a **value
  rescission** → **lineaged** `hash('{topic}:{owner}:{data}:{lineage}')` (scoped to the **one** instance it
  kills, so the re-established `lineage: N+1` survives — a non-lineaged target would match every lineage and
  condemn `N+1` too, the original lock-out); a **content (app-SEL) closure** → append **`:content`** (the content
  namespace). The check asks "is `lineage: N` killed?" for a **specific known `N`** (the one the positive walk
  landed on) — one target, one match, no set to enumerate.
- **The positive walk and the per-lineage negative check are one act, not two mechanisms.** Reading a value
  (`resolve_lookup`) walks its **own lineage chain** from `lineage: 0`, stopping at the lowest **live** one and
  advancing past a **dead** one. `lineage: N` reads dead **because** a `Trm` sits on `N`'s own SEL chain
  (Disputed or severed count too) **and/or** `N`'s lineaged target is present in the owner's **fresh** `Rev`/`Dth`
  `kills[]` (the fail-secure, un-withholdable authority). `Trm` **advances** (it kills one lineage, not the
  address). Contiguous from `0` — a gap ends the walk. Cap **`MAXIMUM_SEL_LINEAGE = 64`** (reusing the existing
  64 bound; past it → no live instance → fail-secure). So the two claims below are **both true**, not a
  contradiction: a value's **positive** resolution ("what is the live value?") has **no IEL fallback** — the
  SEL's own live state is the authority; but its **negative** per-lineage check ("is `lineage: N` killed?")
  **does** consult the owner IEL's lineaged `kills[]`.
- **Why load-bearing — the _value-bearing_ lookup, not the monotone kill.** A **monotone kill** (revocation /
  rescission) is authoritative on the IEL `kills[]` with a fail-secure fallback; its lookup is a **single
  monotone read** (a present `Trm` → killed, a disputed locus included), so there is nothing to resolve and no
  chain to walk (which is why the kill SELs don't _need_ witnessing for correctness, though they get it
  uniformly). A **value-bearing lookup** — a **KEM public key** (a _system_ capability: witnesses and users
  both) — has **no IEL fallback for its positive resolution**: the SEL's own live state _is_ the authority for
  "what is the live value", a dispute is genuine ambiguity (a sender can't safely pick a key → fails closed),
  and a collusion-forced dead lineage is a real **DoS on secure receive**. It carries the `lineage` field, and
  the **positive walk** re-establishes a live key at a discoverable address. (Its **negative** per-lineage check
  — "is `lineage: N` killed" — still consults the owner IEL's lineaged `kills[]`, above.)
- **The value is a T2 sealed `Gnt` — established `{Icp, Gnt}`.** The published key rides a **`Gnt`**
  (`manifest.grant` → a `grants/*` grant-value — §1b), **not** T1 content: a value a sender encrypts to must
  not be swappable by a bare signing key, so establishing or changing it needs `t_authorize`@T2 (a signing-key
  theft cannot redirect secure receive). **Rotation = stack `Gnt`s** at the same lineage (the walk serves the
  **live** sealed tip; a retired key is never served). **Rescission = a monotone `Trm`** on that lineage's chain (the
  positive walk sees it), anchored by a **`Dth`** whose **`kills[]` declares the lineaged target**
  `hash('{topic}:{owner}:{data}:{lineage}')` — so `lineage: N` reads dead by either path, and the re-established
  `lineage: N+1` is untouched. That lineage is then dead; senders fail closed; the owner republishes by
  re-incepting at the **next** lineage (loss-of-control only, never routine rotation — rotation stacks `Gnt`s at
  the same lineage). The two attacks — a `Gnt`-swap (confidentiality) vs a `Trm`-rescind (availability), **both
  T2** — and only the ML-KEM / ESSR send-receive payload live in **vdti-area-exchange**.
- **Soundness.** Establishing a value **or** a kill at a lookup address requires a **T2** act (a `Gnt` rides an
  `Ath`, a `Trm` a `Rev`/`Dth`). The one T1-reachable move — a content squat — is **impossible by
  construction** (content derives to its own namespace; a v1-T1 at a lookup address is invalid). So blocking a
  value again costs **T2** (takeover), the already-stated worst case; an uncompromised owner always outruns a
  kill by standing up a higher lineage. Bounded residual: `MAXIMUM_SEL_LINEAGE = 64` caps the kill/re-establish
  race (lineage increments only on a death; rotation stacks `Gnt`s at one lineage) — recorded in `residuals.md`.

### 1g. The three axes — never conflate them (count ⊥ tier)

1. **Count** = how many owner-IEL members must authorize (delivered via the **anchoring IEL event's**
   signatures): `t_use` (content) · `t_govern` (revoke / close / **`Sea` bury**) · `t_authorize` (grant /
   rescind). _(No `t_recover` — there is no repair.)_
2. **Tier** = is the **rotation reserve** required? **T1** = signing key only (**content only**: `Ixn` /
   `Pin`) · **T2** = + rotation reserve (any seal-advancer: `Gnt` / `Trm` / **`Sea`**). Set by
   danger-of-forgery **OR** need-for-permanence, **⊥ count** (a content `Ixn` is T1 even at a high `t_use`).
3. **Anchor → finality follows the KIND.** A content **`Ixn`** / **`Pin`** rides an IEL **`Ixn`** →
   first-seen / buriable; a **`Gnt`** rides an IEL **`Ath`**, a **`Trm`** an IEL **`Rev`/`Dth`**, a **`Sea`**
   an IEL **`Evl`** → **sealed on arrival**. The anchor **kind** matches the event kind (**kind-strict**,
   inv 4); tier-elevation is a trivial floor, not the check.

### 1h. Inception — every SEL's `Icp` is floored by its serial-1 event [inv 15]

- **SEL `Icp` = T1** (it establishes single-owner _data_, not governance). It carries **no `pin`** (must stay
  recomputable) → it is **floored by its serial-1 event** (its **v1**), which carries the pin the `Icp`
  can't (`pin == anchoring IEL event.previous`). **The IEL anchors the v1, never the `Icp`** — the `Icp`
  rides via `v1.previous`. So every SEL reads `{Icp, v1, …}`; a fabricated bare `{Icp}` naming a victim owner
  is **not** evidence of issuance (authentication is the v1's anchor — inv 15 S1).
- **Which event is v1:** a content SEL's is the first content `Ixn`, or a bare **`Pin`** for an
  incept-and-sit SEL (a doc author who endorses before editing); a **kill lookup's is its `Trm`** (`{Icp,
  Trm}` — born-to-kill, no separate `Pin`); a **value lookup's is its `Gnt`** (`{Icp, Gnt}`). The `Pin` kind
  does **only** the pin re-pin (`t_use` / T1, not sealing) and is the **pin-only re-pin at any serial** — its
  serial-1 instance is the issuance floor here; a later content-less re-pin is also a `Pin`. **`Ixn` and `Pin`
  are disjoint:** an `Ixn` always carries payload (required), a `Pin` never does, so no event is expressible
  two ways.
- **The `content: true` flag is the v1-tier discriminator (§1f biconditional).** A content SEL (v1-T1 —
  `Ixn` / `Pin`) carries **`content: true`** on its `Icp`; a lookup SEL (v1-T2 — `Gnt` / `Trm`) carries **no**
  `content` flag. The verifier rejects a mismatch (a v1-T1 without the flag, or a `content: true` with a v1-T2
  v1), so content and lookups occupy structurally distinct address namespaces.

### 1i. Imposes on the IEL side

- **Content rides the IEL `Ixn` rail; grants the `Ath` rail; kills the `Rev`/`Dth` rail; `Sea` the `Evl`
  rail.** An IEL **`Ixn`** anchors a content SEL's **v1** (a `Pin`, or the first content `Ixn`) and each
  later content `Ixn` (≤ 1 per SEL per IEL `Ixn`), **and** a credential's **issuance commitment**
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` directly (an immutable SAD, no cred-SEL). An IEL
  **`Ath`** anchors a **`Gnt`**; an IEL **`Rev`/`Dth`** anchors a **`Trm`** (the `Rev`/`Dth` also carrying
  the **`kills[]`** declaration naming the killed locus); an IEL **`Evl`** anchors a **`Sea`** (§1d — the new
  pairing). **The matrix is kind-strict both directions** (a `Rev`/`Dth` anchors only `Trm`s, an `Ath` only
  `Gnt`s, an `Evl` only `Sea`s, an `Ixn` only content/v1) — tier-elevation is an additional floor, not the
  check (inv 4 C1).
- **The SEL inherits its owner IEL's witness-config and federation** (single-owner — nothing to declare,
  like the federation binding it already inherits) for its own witnessing (§1c).

## 2. Superseded — do NOT carry (from the FIRST CUT)

- **"The SEL is unwitnessed / rides the IEL's witnessing."** → The SEL is its **own witnessed chain** (§1c).
- **The theorem _a valid SEL fork implies an IEL fork beneath it_ / "a SEL never forks under a linear IEL" /
  anchor-monotonicity as the fork-prevention.** → **RETIRED** (§1c): a SEL forks under a linear IEL via the
  opaque-anchor hole. Fork-prevention is now the SEL's **own witnessing** (first-seen). The anchor's
  re-anchor-at-an-already-attributed-serial-is-inert rule may survive as defense-in-depth (§4), but no longer
  bears fork-prevention. **This ripples to** inv 4 (the anchor-monotonicity paragraph), inv 13 (the
  cross-layer theorem), area-iel §1 (anchor-monotonicity), federation-witnessing §1e/§1g/§4 (the "SEL rides
  the theorem" + "never witnessed" claims), and shared-documents §3 (version-SEL linearity + "dies by cross-layer
  deadness-descends") — targeted edits LANDED 2026-07-12 (§5).
- **"Content fork resolves cross-layer only" / "`{Trm, Ixn}` wins on tier-rank cross-layer" / the
  cross-layer anchor rules ("Cross-layer deadness-descends", anchor-monotonicity as the total-order).** →
  Divergence is now the SEL's own witnessed state (`Sea` / `disputed`) **×** inherited IEL-deadness
  **severance** (§1e).
- **`deadness descends`** → **`deadness ascends`** (§1e; system-wide sweep is separate, §5).
- **"So the SEL is 5 kinds."** → **six** — `Icp`/`Ixn`/`Pin`/`Gnt`/`Trm`/**`Sea`**.
- **federation-witnessing §1g Decision 1 "a SEL is never witnessed directly" + the receipt-batching
  "collapses out" claim + inv 16's "no receipt carries a lookup-SEL prefix" clause** → the SEL **is**
  witnessed (§1c); witnesses see SEL structural fields as acceptable trust-infra exposure, with the
  exfiltration-during-compromise residual stated. Targeted edits to those canon sites LANDED 2026-07-12 (§5).

## 3. Requirements satisfied / imposed

- Satisfies **R1** (no policy on the SEL — auth is the owner IEL's structural threshold + the SEL's own
  witnessing), **R2** (position-addressable, tokenizable verification), **R3** (a `pin` yields the state
  token + committed-anchor proof).
- **Imposes on the IEL:** the `Sea ← Evl` anchor pairing (§1d/§1i — the inv-4/inv-12 refinement, §4); a SEL
  is witnessed at its own `(prefix, serial)` inheriting the owner IEL's federation (§1c — the
  federation-witnessing §1g revision).
- **Imposes on the witnessing layer:** SEL events earn their own receipts (the receipt scope expands beyond
  IEL/KEL — federation §1g), so the receipt-skew / forward-of-confirmed-tip machinery (federation §5)
  applies to SELs too.

## 4. Open / for the adversarial pass

- **The `Sea ← Evl` anchor + the inv-12 restatement — RESOLVED (Jason 2026-07-12: "put `anchors` on `Evl`").**
  The IEL `Evl` gains an `anchors` role (inv 4) so it can anchor a `Sea`, and inv 12's "no kind both anchors
  a payload **and** mutates establishment state" is restated as the **count-integrity** invariant it actually
  protects (no anchor of a payload at a count _below_ its establishment mutation's — no laundering). A `+cut`
  `Evl` anchoring a `Sea` mutates its roster _and_ anchors a payload, but both at `t_govern`, so nothing is
  laundered (§1d); the `Sea` anchor is back-checked (`Sea ← Evl` kind-strict), so the kind→role gate is
  untouched. Landed in inv 4 / inv 12 / area-iel §1.
- **Anchor-monotonicity's residual role.** With witnessing bearing fork-prevention, does the
  re-anchor-at-an-already-attributed-serial-is-inert rule survive as a structural defense-in-depth check (a
  node validating without full witnessing state), or is it fully subsumed by first-seen? Decide at the
  encode.
- **The full divergence matrix** (Axis A: the SEL's own witnessed state × Axis B: inherited IEL deadness,
  composed by deadness-precedence) is worked out (§1e) but its **cells are drawn in `sel/reconciliation.md`**
  at the design-doc encode, not here.

## 5. Drift → land backlog (canonical docs)

- **Write `docs/design/primitives/data/event-logs/sel/` fresh** from this note (greenfield voice, no jargon,
  human-readable slug refs): `log.md` (four-state machine, prefix + `lineage` derivation, witnessed chain,
  locked-portion bound), `events.md` (the six kinds incl. `Sea`, two tiers, anchor reqs, seal cap),
  `merge.md` (first-seen decline, the merge outcomes), `reconciliation.md` (the **exhaustive divergence
  matrix** — the correctness proof, mirroring `iel/reconciliation.md`), `verification.md` (the walk incl.
  the meaning-blind `lineage` positive walk).
- **Targeted interlocking canon edits — LANDED 2026-07-12 (the theorem-retirement + witnessed-SEL ripple):**
  inv 4 (anchor-monotonicity reading retired; `Evl` gains the `anchors` role for `Sea`), inv 12 (count-integrity
  restatement), inv 13 (cross-layer theorem → severance + witnessed-SEL divergence), inv 16 (the "no receipt
  carries a lookup-SEL prefix" clause superseded), **area-iel §1** (the `Evl` row + anchor-monotonicity),
  **federation-witnessing §1e/§1g/§4** (the SEL now witnessed; §1g Decision 1 revised; receipt scope expands;
  the exfiltration residual), **shared-documents §3** (version-SEL linearity via witnessing; "dies by severance").
- **`iel/reconciliation.md`** lines 352-354 + the 433-440 forward-ref block carry the retired SEL theorem —
  update at the design-doc encode.
- **`deadness descends → ascends` doctrine-wide sweep — LANDED 2026-07-12** (KEL / IEL / federation /
  invariants / protocol-doctrine + design docs). The whole doctrine now reads `deadness ascends` / `dead on
  ascent` / `by position + ascent` (foundation-at-bottom: KEL → IEL → SEL, built upward); structural nouns
  (`descendant`, the feature-DAG `ancestor → descendant` / "DAG descent") are unchanged. **Still open — the
  `inv 13` tier-1-deadenable SEL leg (mechanism, not label):** that clause reads "every anchored SEL event
  dead on ascent," but area-sel §1e makes inherited IEL deadness **sever** the SEL, so the SEL leg should
  read "severed" (the KEL/IEL cascade there is the label-only flip; warm round-2 low obs).

## 6. Confidence / what's owed

- §1a–§1b, §1g–§1i (shape) — **high** (carried from the FIRST CUT, which was correct on shape).
- §1c (witnessing) — **high on the diagnosis** (the equivocation hole is mechanically verified) and the
  privacy resolution (Jason-confirmed: trust-infra exposure over the encrypted mesh + the exfiltration
  residual). The receipt-scope expansion is a federation-area detail (§5).
- §1d (`Sea`) — settled: the **necessity** (the locked-below-seal residual) and the **`Sea ← Evl` anchor +
  inv-12 count-integrity restatement** (Jason 2026-07-12; landed in inv 4 / inv 12 / area-iel §1).
- §1e (divergence) — **high** (deadness-precedence / severance-truncation / `deadness ascends` are
  settled); the cell-by-cell proof is owed at `sel/reconciliation.md`.
- §1f (the two axes) — **high** (the `content: true` biconditional making the squat impossible by
  construction; `lineage` a pure re-establishment counter with a positive walk, `Trm`-advances; the kill target
  mirrors the killed address — non-lineaged monotone, **lineaged for a value rescission**, `:content` for
  content; the positive walk consumes the per-lineage `kills[]`; cap 64; value-bearing driving case — all
  settled).
