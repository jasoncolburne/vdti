# Event Shape — KEL / IEL / SEL

Canonical reference for the event-log primitives' event taxonomy, field shape, and per-kind
structural-validation rules. The per-primitive docs reference this for the underlying shape;
doctrine specific to a primitive (the exact anchor matrix, divergence and repair rules, federation
mechanics, prefix-derivation specifics) lives in the per-primitive docs and in
[`../../../protocol-doctrine.md`](../../../protocol-doctrine.md).

This is a **shape reference** — it states what fields exist, which kinds populate them, and how the
verifier enforces per-kind field rules. **Authorization is structural:** a KEL, IEL, or SEL event is
authorized by its own key state, its identity's threshold, or its owner. Policy is a property of
**documents**; see [`../../policy/policy.md`](../../policy/policy.md).

## Reading order

- [`kel/`](kel/) — KEL primitive specs. _(Per-primitive doctrine; landed separately.)_
- [`iel/`](iel/) — IEL primitive. _(Per-primitive doctrine; landed separately.)_
- [`sel/`](sel/) — SEL primitive. _(Per-primitive doctrine; landed separately.)_
- [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md) — cross-primitive doctrine:
  tiers, divergence and repair, the seal bound, federation convergence, the verification walk.
- [`../../policy/policy.md`](../../policy/policy.md) — the document authorization layer (the policy
  language that lives on documents, not on these events).
- [`../sad/sad.md`](../sad/sad.md) — the SAD layer: chain events are SADs.

## Common fields

Five fields appear on every event across all log types. The per-kind shape (§Per-kind structural
validation) adds fields per kind.

| Field      | Type      | Description                                                                                                                                                                                                                                                             |
| ---------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `said`     | Digest256 | Blake3-256 hash of the canonical event content with the `said` field blanked (and `prefix` populated with its real value). Identifies the event uniquely.                                                                                                               |
| `prefix`   | Digest256 | Hash of the canonical event content with both `said` and `prefix` blanked. Identifies the chain. Derives from the **whole-event content** — not a special tuple. Two distinct inceptions for the same chain are structurally impossible without a Blake3-256 collision. |
| `serial`   | u64       | Chain position. Inception events have `serial == 0`; all others have `serial >= 1`, monotonic per branch.                                                                                                                                                               |
| `previous` | Digest256 | SAID of the parent event. Forbidden at inception (no parent); required elsewhere.                                                                                                                                                                                       |
| `kind`     | String    | Log-type × event-kind discriminator. Drives per-kind structural validation, tier dispatch, and the role vocabulary the event's `manifest` may carry.                                                                                                                    |

Signatures are **not part of event content** — see
[§Authentication & signatures](#authentication--signatures).

## Authentication & signatures

Signatures are not part of the event content — events are pure SAD content. The `said` is the hash
of the content; embedding a signature would make the SAID depend on a signature taken over the prior
SAID, which is circular. Signatures live **adjacent** to the event as separate data.

- **KEL events** are signed by the controller **when authored**: a primary signature on every KEL
  event, plus a **recovery signature** on the dual-signed kinds (`Ror` / `Rec` / `Wit` / `Dec`). The
  recovery key behind that second signature is the **break-glass reserve** for high-assurance
  operations — not a device-loss recovery mechanism (a lost or compromised device is rotated out at
  the identity layer via an IEL roster change).
- **IEL / SEL events** carry no adjacent signatures. They authenticate via their **KEL anchor** — a
  member's KEL event commits to the IEL event it participates in (and an IEL event commits to the
  SEL events it authorizes), and that KEL event's adjacent signature provides the authentication.
  The verifier walks from the IEL / SEL event to its anchoring event and validates the signature
  there.

This composition is what makes the three-tier capability model uniform across primitives — an IEL /
SEL operation inherits its authentication tier from the event that anchors it. See
[`../../../protocol-doctrine.md` §Tiers](../../../protocol-doctrine.md#tiers).

## Structural authorization — the three mechanisms

Each primitive authorizes its own events structurally.

- **KEL — a device's own key.** A KEL event is authorized by the key state the chain itself commits:
  a signing key (tier 1), a revealed rotation preimage (tier 2), a revealed rotation + recovery
  preimage (tier 3). The KEL is the root — self-authorizing, with no chain above it.
- **IEL — an identity's threshold vector over its member devices.** An IEL is a roster of member
  KELs plus a **threshold vector** `{t_use, t_govern, t_delegate, t_recover}`, indexed by the kind
  of event being authored (below). It composes no multi-party policy internally; "who is this
  identity" is the roster, "how many must act for this kind of act" is the threshold vector.
- **SEL — single-owner ownership.** A SEL is owned by exactly one IEL. Its events are authorized by
  that owner IEL: the owner's IEL event anchors the SEL event (commits to its SAID), and the
  required count is set by the SEL event's kind. A SEL hosts no roster of its own.

**The threshold vector and its bounds.** Each IEL kind draws its required count from one slot of the
vector: content (`Ixn`) from `t_use`; a roster/threshold change (`Evl`) from `t_govern`; a
delegation (`Del`) from `t_delegate`; a repair (`Rpr`) from `t_recover`; a kill-anchor (`Kil`) from
the `govern` or `delegate` slot it names; a federation rebind (`Wit`) and the terminal `Dec` from
`t_govern`. The bounds:

- `t_use >= 1` (`t_use = 1` is single-device by choice — no content resilience).
- The authority slots (`t_govern`, `t_delegate`, `t_recover`) carry **two bounds**: a **security
  floor** `>= 2` (hard, every identity — no single member exercises authority) and a
  **recoverability ceiling** `<= |roster| − 1` (lets the identity evict a compromised member or
  recover a lost one without it). The recoverability ceiling is **advisory at `|roster| = 2`** (a
  two-device identity is valid but cannot evict/recover without both — the wallet warns) and **hard
  at `|roster| >= 3`** (a threshold equal to `|roster|` is a gratuitous hostage config — rejected).
  A singleton (`|roster| = 1`) sets all thresholds to 1.
- **`t_govern <= t_recover` is a hard floor** — verifier-enforced wherever a threshold is declared
  or changed (`Icp` and every roster-delta event). Recovery reveals the reserve, and a repair may
  now carry a roster `cut` (the repair-and-evict fold — [`iel/`](iel/)), so recovery must never be
  priced below governance. (Vacuous for a federation, which declares no `t_recover`, and for a
  singleton.)
- The roster is **never emptied**: post-delta **`|roster| = |roster| + |add| − |cut| >= 1`** — an
  absolute floor beneath the security floor and the singleton exception. A roster is a **set**, so a
  delta is well-formed only with `add ∉` the current roster, `cut ⊆` it, and `cut ∩ add = ∅` (the
  size arithmetic then holds). This makes every singleton's roster downward-immutable — a singleton
  `cut` computes `1 + 0 − 1 = 0 < 1` and is rejected — while still allowing singleton
  evict-and-replace via an `Evl` (`cut 1 + add 1` stays 1).
- The bounds are re-checked on the post-delta roster at **every** roster-delta event — a user `Evl`,
  a **user `Rpr`-cut** (the repair-and-evict fold), or a federation `Wit` — not only at inception. A
  `Rpr`-cut (and any `threshold` it carries) is authorized at the **outgoing** `t_recover` (the
  pre-change gate — as a user `Evl` rides `t_govern`-of-outgoing — so a `Rpr` cannot lower its own
  gate before cutting).

The per-kind threshold/tier mapping and the bound derivations are the IEL primitive's —
[`iel/`](iel/). The credential acceptance and authorizing conditions that ride **above** this — on
documents — are the policy layer's ([`../../policy/policy.md`](../../policy/policy.md)).

## The manifest — what an event commits to, grouped by role

An event commits to the things below it through a **`manifest`**: the SAID of a SAD that groups
those commitments **by named role**. The manifest SAD reads
`{ said, <role>: <said-or-list-or-scalar>, … }`, and each role reads as "the things this event
{anchors / roster / delegates / …}." The event row holds only the manifest SAID; the grouped
commitments live in the SAD, separately custody-able. A role value is either an **inline list** of
SAIDs/prefixes — `anchors` / `content` / `delegates` / `forks` — a **single SAID** naming a further
structured SAD (`roster`, `witnesses`), a **single event-SAID pointer** (`bound`), or a **direct
scalar** (the federation `clock` — an inline timestamp value, the lone non-SAID, non-list role).

**Role vocabulary:**

| Role        | Carried by                                                                     | Commits to                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `anchors`   | KEL `Ixn` (req, ≥1) / `Rot` / `Ror` / `Wit`; IEL `Ixn` / `Evl` / `Kil` / `Rpr` | an inline **list** of lower-layer event/SAD SAIDs — `[ said, … ]`. The **one** anchoring vocabulary, discriminated by the **anchored event's kind** (not a role label): a KEL `Wit` anchors the IEL `Wit` it participates in; an IEL `Ixn` anchors content SEL events **and** credential-SEL inceptions (issuance), an IEL `Evl` the SEL `Fld`s it re-seals, an IEL `Kil` the SEL `Dec`s it seals (revocation / closure / rescission), an IEL `Rpr` the SEL `Rpr`s it realizes                                                                                                                                                                                                                                                                                                            |
| `roster`    | IEL `Icp` / `Evl` / `Rpr` (user); federation `Fcp` / `Wit`                     | a SAID → the roster/threshold **delta** SAD `{ add: prefix[], cut: prefix[], …changed thresholds }` — membership + threshold _changes_ only, never a full snapshot. On a user `Rpr` (the repair-and-evict fold) the delta is restricted to a **required non-empty `cut` + an optional `threshold`, never an `add`** — a cut-less, `threshold`-only, or `add`-bearing `Rpr` roster is malformed → rejected (IEL doctrine)                                                                                                                                                                                                                                                                                                                                                                  |
| `delegates` | IEL `Del`                                                                      | an inline **list** of delegate **prefixes** — `[ prefix, … ]` (a grant/inclusion proof, batched; rescission is a separate lookup-SEL, never a list edit)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `content`   | SEL `Ixn`                                                                      | an inline **list** of content-SAD SAIDs — `[ said, … ]` the SEL `Ixn` records (a credential SEL's `Icp` uses `data`, not a manifest)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `bound`     | SEL `Dec` (rescission)                                                         | the SAID of the **last valid (honoured) event** on a delegated chain — a rescission's grandfather boundary (the dial: the delegate's tip → its inception)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `witnesses` | KEL `Icp` / `Wit`; IEL `Icp` / `Wit`; federation `Fcp` / `Wit`                 | a SAID → the witness-config SAD `{ threshold, signers }` (mandatory iff federated at inception; present-iff-changed on `Wit`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `clock`     | federation `Fcp` / `Wit` / `Dec`                                               | the federation-clock **timestamp** carried **inline** — a UTC RFC3339 microsecond string (fixed-width, JCS-canonical), not a nested SAD (federation doctrine)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `forks`     | a **repair only** — KEL `Rec`; IEL / SEL `Rpr` (req, non-empty)                | an inline **list** of the **archived-branch tip SAIDs** the repair resolves — `[ said, … ]`, each reconstructing its branch by walking `previous` back to the divergence ancestor. **Required and non-empty on a repair; forbidden on every other kind** (a non-divergent tip has nothing to repair). The retained (canonical) run is **not** committed — it is the linear chain `[previousSeal..previous]`, recovered by the flat walk (nodes keep full bodies; the flat query returns them), and "content was folded since the prior seal" is the derived predicate `previous != previousSeal`, no field. Validated, not trusted — the verifier recomputes the archival set from the retained branches (+ the beacon) and rejects a repair that leaves a privileged branch un-committed |

**Top-level structural vs. manifest.** An event's _own links_ stay top-level: `said`, `previous`,
**`previousSeal`** (on every seal-advancing event — the back-link to the prior seal that renders the
spine; see [§Divergence is scoped to content](#divergence-is-scoped-to-content) and
protocol-doctrine §Forks are Seal-Bounded), the down-pins (`pin` on a SEL, `pins` on an IEL), the
federation `prefix`, `federationPin`, the `Kil` `threshold` enum. The `manifest` (role-labeled)
carries everything the event _commits to below it_ — lower-layer event SAIDs and documents. Entities
are named by **prefix**; positions and documents by **SAID**. A SAID here is an integrity
**commitment**, not a lookup key — there is no global SAID→event index, so a SAID harvested off a
public manifest does not invert to a (possibly private) chain's prefix for any party outside the
federation mesh; logs are fetched by prefix
([`../../../protocol-doctrine.md` §Negative checks are positive lookups](../../../protocol-doctrine.md#negative-checks-are-positive-lookups)).

**Read the manifest kind-first.** Each kind may carry **only** the roles in its closed vocabulary
(the table above); a manifest carrying any role outside its kind's vocabulary is **malformed →
rejected**, and a role is consumed only after dispatching on a kind permitted to carry it. The
manifest SAID commits the role labels (the hash is over the keys), so a third party cannot relabel a
fixed event; the kind→role allowlist closes _author_-mislabel. This is load-bearing for the
directly-consumed roles (`roster`, `delegates`, `witnesses`, `clock`) — they have no downstream
type-check, so the allowlist is their sole protection. The back-checked role `anchors` is
additionally caught when each referenced event is validated against its required kind — the anchor
matrix is **kind-strict** both directions: an IEL `Kil`'s anchors resolve **only** to SEL `Dec`s, an
IEL `Ixn`'s only to content or a credential-SEL inception, and neither the reverse.

## Cross-cutting fields

Beyond the common fields, these appear on multiple kinds with consistent meaning. **Logs** names the
subset of {KEL, IEL, SEL} the field appears on; **Events** the kinds that carry it.

| Field           | Type      | Logs          | Events                                                                                                                                                                           | Description                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------------- | --------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `manifest`      | Digest256 | KEL, IEL, SEL | KEL `Icp` / `Ixn` / `Rot` / `Ror` / `Rec` / `Wit` / `Dec`; IEL `Icp` / `Ixn` / `Evl` / `Del` / `Kil` / `Rpr` / `Dec` / `Wit`; SEL `Ixn` / `Fld` / `Rpr` / `Dec`                  | SAID of the role-grouped commitment SAD (above).                                                                                                                                                                                                                                                                                                                                                                                     |
| `previousSeal`  | Digest256 | KEL, IEL, SEL | the **seal-advancing** kinds (KEL `Rot`/`Ror`/`Rec`/`Wit`/`Dec`; IEL `Evl`/`Del`/`Kil`/`Rpr`/`Dec`/`Wit`; SEL `Fld`/`Rpr`/`Dec`)                                                 | Back-link to the prior seal-advancing event; renders the **spine** ([§Divergence is scoped to content](#divergence-is-scoped-to-content)). `fbd` on `Icp` / `Fcp` / `Ixn`.                                                                                                                                                                                                                                                           |
| `federation`    | Digest256 | KEL, IEL      | KEL `Icp` / `Wit`; user IEL `Icp` / `Wit` — **all opt** (present-iff-changed: on `Icp` absent ⇒ direct-mode; on `Wit` present only on a rebind)                                  | The federation IEL **prefix** a chain (KEL) or identity (IEL) binds to — which federation; follows the federation's evolution. The **identity's** authoritative binding lives on its IEL `Icp`/`Wit`; each member KEL's binding is field-matched to it (kind-strict `Wit ↔ Wit`). A SEL inherits its owner IEL's binding. The **federation IEL itself** carries neither field — it _is_ the federation, never self-bound.           |
| `federationPin` | Digest256 | KEL, IEL      | KEL `Icp` (req iff federated); **opt on `Wit` + every KEL body event** (`Ixn`/`Rot`/`Ror`/`Rec`/`Dec`) — present-iff-re-pinned; user IEL `Icp` (req iff federated) / `Wit` (opt) | A **SAID** pinning the as-of federation position. Present = a forward **re-pin** within the inherited federation; absent = inherit the prior pin — so a same-federation re-pin rides whatever KEL body event the chain authors next (`Wit` is reserved for a **rebind** — it changes the `federation` prefix or the `witnesses` config). The prefix/SAID split: `federation` is _which_ federation, `federationPin` is _as of when_. |
| `pin`           | Digest256 | SEL           | `Ixn` / `Pin` / `Fld` / `Dec` / `Rpr` (req); **`fbd` on `Icp`**                                                                                                                  | SAID of the owner IEL event this SEL event floors up to (the SEL's **down-pin**). The `Icp` carries **no** `pin` — it must stay recomputable for lookup (§Prefix derivation) — so the SEL's first pin rides a **serial-1 `Pin` event batched with the `Icp`**, uniformly for every SEL (a rescission lookup-SEL is `{Icp, Dec}`; its terminal `Dec` carries the `bound`).                                                            |
| `pins`          | Digest256 | IEL           | every IEL kind (`Icp`/`Ixn`/`Evl`/`Del`/`Kil`/`Rpr`/`Dec`/`Wit`)                                                                                                                 | SAID of a small SAD listing the participating member **KEL event SAIDs** — the IEL's **down-pins**, the complement of fresh-participation up-anchoring (a federation `Wit`'s are the witness KELs). Every IEL event is anchored by a threshold of members, so every one carries it. (Schema is IEL doctrine — [`iel/`](iel/).)                                                                                                       |
| `nonce`         | Nonce256  | IEL           | `Icp`                                                                                                                                                                            | Opaque random bytes chosen by the inceptor; makes the IEL prefix unpredictable. Required at inception, forbidden elsewhere.                                                                                                                                                                                                                                                                                                          |
| `threshold`     | enum      | IEL           | `Kil`                                                                                                                                                                            | Which authority slot the sealed kill-anchor is priced at — `govern` (a revocation/closure) or `delegate` (a rescission). A slot **name**, never a raw integer.                                                                                                                                                                                                                                                                       |
| `owner`         | Digest256 | SEL           | `Icp`                                                                                                                                                                            | The **owner IEL prefix** — which IEL owns this SEL. On the `Icp` only and **immutable** (a SEL has one owner for life). Participates in the SEL prefix derivation.                                                                                                                                                                                                                                                                   |
| `topic`         | String    | SEL           | `Icp`                                                                                                                                                                            | Application discriminator; participates in the SEL prefix derivation.                                                                                                                                                                                                                                                                                                                                                                |
| `data`          | Digest256 | SEL           | `Icp` (opt)                                                                                                                                                                      | The content the SEL is rooted on. For a credential SEL, `data` **is the credential's SAID** (the whole reference; the `Icp` carries no manifest). For a lookup SEL, `data` is the recompute input (e.g. the rescinded prefix). Optional — absent for an `owner`+`topic`-only SEL. Participates in the SEL prefix derivation.                                                                                                         |

The KEL key-state fields (`publicKey`, `rotationHash`, `recoveryKey`, `recoveryHash`) and the
witness-config SAD are KEL-specific — see [`kel/`](kel/).

## Tiers — the three-tier capability model

**Tier** names the cryptographic capability required to forge an event, set by
**danger-or-permanence**, and is **orthogonal to count** (the threshold vector). Tier is dispatched
from the event kind, never stored.

- **Tier 1 — signing key only.** Content. A `t_use`-counted `Ixn` is tier 1 even at a high count.
- **Tier 2 — rotation preimage.** Establishment-mutation, authority-grant, and **any sealed kill**
  (a kill must be permanent on arrival).
- **Tier 3 — rotation preimage + recovery preimage.** Repair and identity-kill.

The reserve (rotation / recovery preimage, held apart from the signing key) is required when a
forgery would be high-harm or irreversible, **or** when the act must be permanent on arrival
(sealed). A **kill** (revoke / close / rescind / decommission) is the permanence case: low-danger
(it only removes trust) but monotone (a third party relies on it), so it is sealed on a dedicated
kill-anchor and is tier 2 (identity-kill → tier 3). Tier semantics and the **kind-strict** anchor
rule (each IEL / SEL kind is anchored by **exactly** the KEL / IEL kind that reveals the matching
capability — no higher-tier stand-in) are the protocol doctrine's —
[`../../../protocol-doctrine.md` §Tiers](../../../protocol-doctrine.md#tiers).

## Event taxonomy

### KEL — 8 kinds

| Kind  | Tier | Sig    | Role                                                                                                                                                                                                                                                                 |
| ----- | ---- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Fcp` | 1    | single | Founder **pre-federation** inception; self-attested, carries no `witnesses`, and cannot stand alone — its v=1 `Rot` anchors the federation IEL's `Fcp` marker in the same batch.                                                                                     |
| `Icp` | 1    | single | Standard inception — **federation-bound** (carries `federation` / `federationPin` + `witnesses`) or **direct-mode** (omits them; un-federated until a later `Wit` binds it).                                                                                         |
| `Ixn` | 1    | single | Content; anchors lower-layer SAIDs via `manifest` (`anchors`, ≥1). The **repairable** kind.                                                                                                                                                                          |
| `Rot` | 2    | single | Rotation — reveals the next signing key, commits the new one. Seal-advancing.                                                                                                                                                                                        |
| `Ror` | 3    | dual   | Proactive rotate-recovery (hygiene); rotates signing **and** recovery keys.                                                                                                                                                                                          |
| `Rec` | 3    | dual   | **Recover** — the KEL's repair kind: resolves `Ixn` divergence by archiving the losing branch. Reveals the recovery key (hence dual-sig); does **not** terminate the chain (returns it to **Active**).                                                               |
| `Wit` | 3    | dual   | Federation (re)bind on a **user** (`Icp`-rooted) KEL — changes `federation` and/or `witnesses`, anchors the user IEL `Wit`; on an **`Fcp`-rooted** witness KEL it is federation **governance** (anchors the federation IEL `Wit`, never self-bound). Seal-advancing. |
| `Dec` | 3    | dual   | Terminal (decommission).                                                                                                                                                                                                                                             |

A KEL has **one inception root**: either a founder **`Fcp → Rot`** pair (a pre-federation founder
anchoring the federation IEL `Fcp` it helps incept) **or** a standalone **`Icp`** (joining an
existing federation) — **never** `Fcp → Icp`. A pre-federation `Fcp` is **self-attested**, carries
**no `witnesses`** (there is no federation yet to witness it — which keeps the federation IEL's own
bootstrap non-circular), and **cannot stand alone**: its v=1 is a **`Rot`** that anchors the
federation IEL's **`Fcp`** marker (kind-strict, tier-2 → tier-2 — there is no founder `Wit`) in the
**same atomic batch** (`Fcp` v=0 → `Rot` v=1). The full ceremony is KEL + federation doctrine —
[`kel/`](kel/), [`federation/`](../../../federation/).

### IEL — 8 kinds

| Kind  | Tier | Count                                      | Role                                                                                                                                                                                                                                                                                                                                                         |
| ----- | ---- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Icp` | 2    | all initial members consent                | Inception; pins the initial roster + threshold vector, the initial federation binding (`federation` / `federationPin`, top-level) and witness-config (`witnesses`). A **federation IEL** instead incepts the **`Fcp`** marker (the restricted-set note below), not `Icp`.                                                                                    |
| `Ixn` | 1    | `t_use`                                    | Content; anchors content SEL events **and** credential-SEL inceptions (issuance) via `anchors`, batched. The **repairable** kind.                                                                                                                                                                                                                            |
| `Evl` | 2    | all added consent ∧ `t_govern` of outgoing | **Evolve state** — roster/threshold change (carries a roster/threshold **delta** (`add` + `cut`) in `roster`); also anchors the SEL `Fld`s that re-seal at this fold boundary (`anchors`); anchors no kills (those ride `Kil`). (Added members consent at tier 1 via their own KEL anchor; the binding authorization is tier 2 from the continuing quorum.)  |
| `Del` | 2    | `t_delegate`                               | Delegation declaration — a **positive inclusion list** of delegate prefixes (`delegates`).                                                                                                                                                                                                                                                                   |
| `Kil` | 2    | `threshold` slot                           | **Sealed kill-anchor** — anchors the SEL `Dec`(s) it seals (`anchors`), at the `govern` (revocation/closure) or `delegate` (rescission) slot. Carries **no roster delta**, but **forces a `Rot`** (a permanent act needs a ≥ tier-2 KEL anchor). Sealed on arrival, terminal-on-divergence.                                                                  |
| `Rpr` | 3    | `t_recover`                                | Divergence repair. May carry a `roster` **`cut` + optional `threshold`** — the repair-and-evict fold: it evicts the fork-causing member atomically with the repair (a **required non-empty `cut`, never an `add`, never `threshold`-only**). Priced at the **outgoing** `t_recover`; the post-cut roster is re-checked against the threshold-vector bounds.  |
| `Dec` | 3    | `t_govern`                                 | Terminal; freezes all the IEL's SELs.                                                                                                                                                                                                                                                                                                                        |
| `Wit` | 3    | `t_govern`                                 | **Federation rebind** — records the identity's federation (`federation` / `federationPin`, top-level) + witness-config (`witnesses`); anchored by member KEL `Wit`s (kind-strict, tier-3 ↔ tier-3). `{Wit, Wit}` terminal. The **one** witness/federation kind; on a **federation** IEL it is governance (roster + rotation) — see the restricted-set note. |

A federation is a **restricted IEL** rooted at an **`Fcp`** inception marker — `Fcp` / `Wit` / `Dec`
only (`Wit` is its governance kind — witness rotation and/or a roster delta — replacing the user
`Evl`; no `Ixn`, so it never has a **reconcilable** fork and needs no `Rpr`; a competing-privileged
`{Wit, Wit}` / `{Dec, Dec}` is still possible but **terminal**, not repairable; no `Del`, since
trust is per-federation and non-transitive). Its roster is witness KELs directly. See
[`../../../protocol-doctrine.md` §Federation convergence](../../../protocol-doctrine.md#federation-convergence)
and [`federation/`](../../../federation/).

### SEL — 6 kinds

| Kind  | Count                                               | Tier                  | Anchored by (IEL)               | Role                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----- | --------------------------------------------------- | --------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Icp` | `t_use`                                             | 1                     | `Ixn`                           | Inception. Carries **no** `pin` — it stays recomputable for lookup (§Prefix derivation), so the SEL's first pin rides a **serial-1 `Pin`** batched with it (uniform). A credential SEL's `data` **is** the credential's SAID (and the `Icp` carries no manifest); a lookup SEL's `data` is the recompute input (e.g. the rescinded prefix).                                                                                                                                                                                                            |
| `Ixn` | `t_use`                                             | 1                     | `Ixn`                           | Content SAD(s) + re-`pin`; ≤ 1 per SEL per IEL `Ixn`. The **only repairable** SEL kind.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `Dec` | `t_govern` (revocation) · `t_delegate` (rescission) | 2 (identity-kill → 3) | `Kil` @ `govern` / @ `delegate` | The SEL **kill**: `Kil`@`govern` decommissions a credential SEL (revocation / closure); `Kil`@`delegate` seals a delegation **rescission** (the lookup SEL is `{Icp, Dec}` born to kill, and the `Dec` additionally carries `manifest.bound`). **Sealed on arrival** (a kill is monotone — no delayed form). The killed thing is identified by _which SEL its `Dec` extends_.                                                                                                                                                                          |
| `Pin` | `t_use`                                             | 1                     | `Ixn`                           | The **floor re-pin** — re-pins the SEL to its owner IEL's current tip, carrying only the top-level `pin` (no `manifest` / `previousSeal`). Its job is the **serial-1 issuance floor** (the `Icp` can't hold a pin). Tier-1, repairable; **not** seal-advancing — it promotes nothing.                                                                                                                                                                                                                                                                  |
| `Fld` | `t_govern`                                          | 2                     | `Evl`                           | The SEL **re-seal** (a _pure fold_ — the KEL `Rot` / IEL re-seal-`Evl` analog, for a primitive with no roster or keys to evolve). Carries `previousSeal` (no `forks` — it is a non-repair seal; the folded run `[previousSeal..previous]` is derivable), caps the content run so a divergence repair stays page-atomic, and promotes below-fold content to durable. **Privileged, seal-advancing.** Anchored by an owner IEL `Evl` (which commits the `Fld`'s SAID via its `anchors` role) — a SEL fold lands at one of the IEL's own fold boundaries. |
| `Rpr` | `t_recover`                                         | 3                     | `Rpr`                           | Divergence repair; owner-authorized, bottom-up cascade.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

Content rides the IEL `Ixn` rail (tier 1); a kill rides the IEL `Kil` rail (tier 2, sealed);
roster/threshold changes ride the IEL `Evl` rail. A SEL's **trust-finality** floors to the owner
IEL's seal — it has no seal of its own for that; but its own seal-advancing kinds (`Fld` / `Rpr` /
`Dec`) cap its **local divergence/repair window** and carry `previousSeal` like any spine (only the
repair `Rpr` additionally carries `forks`). Credential issuance, revocation, and status are a
**feature** layered on the SEL primitive — [`features/credentials/`](../../../features/credentials/)
_(landed separately)_.

## Per-kind structural validation

The verifier enforces per-kind field rules: **req** (must be set), **fbd** (must be unset), **opt**
(may be either). Common fields (`said`, `prefix`, `kind`) are always required; `previous` is
forbidden on inception kinds and required elsewhere; `serial` is 0 on inception, `>=1` elsewhere;
signatures live adjacent (§Authentication & signatures).

### KEL

| Kind  | publicKey | rotationHash | recoveryKey | recoveryHash | federation | federationPin | previousSeal | manifest                         |
| ----- | --------- | ------------ | ----------- | ------------ | ---------- | ------------- | ------------ | -------------------------------- |
| `Fcp` | req       | req          | fbd         | req          | fbd        | fbd           | fbd          | fbd                              |
| `Icp` | req       | req          | fbd         | req          | opt        | opt           | fbd          | opt (`witnesses`)                |
| `Ixn` | fbd       | fbd          | fbd         | fbd          | fbd        | opt           | fbd          | req (`anchors`, ≥1)              |
| `Rot` | req       | req          | fbd         | fbd          | fbd        | opt           | req          | opt (`anchors`)                  |
| `Ror` | req       | req          | req         | req          | fbd        | opt           | req          | opt (`anchors`)                  |
| `Rec` | req       | req          | req         | req          | fbd        | opt           | req          | req (`forks`, ≥1)                |
| `Wit` | req       | req          | req         | req          | opt\*      | opt\*         | req          | req (`anchors`; `witnesses` opt) |
| `Dec` | req       | fbd          | req         | fbd          | fbd        | opt           | req          | fbd                              |

The dual-signed kinds (`Ror` / `Rec` / `Wit` / `Dec`) carry an adjacent recovery signature
(§Authentication & signatures). On an `Icp`, `federation` / `federationPin` are **optional**:
present ⇒ federation-bound, absent ⇒ a **direct-mode** chain (un-federated, unwitnessed until a
later `Wit` binds it), and `witnesses` is **mandatory iff federated** (present iff `federation` is;
**forbidden** on a direct-mode `Icp`). **\*The `Wit` row is the user (`Icp`-rooted) facet** — the
federation rebind, `federation` / `federationPin` **present-iff-changed (`opt`)** (present on an
actual rebind / re-pin; a witness-config-only `Wit` carries neither — inv 18); on an **`Fcp`-rooted
federation-witness `Wit`** (federation governance) both are **fbd** — the witness is never
self-bound. Exact key-state semantics, the witness-config SAD, and the direct-mode / facet doctrine
are KEL + federation doctrine — [`kel/`](kel/), [`../../../federation/`](../../../federation/).

### IEL

| Kind  | nonce | pins | previousSeal | manifest                                                                             | threshold                    |
| ----- | ----- | ---- | ------------ | ------------------------------------------------------------------------------------ | ---------------------------- |
| `Icp` | req   | req  | fbd          | req (`roster`; `witnesses` mandatory iff federated; a federation `Fcp` adds `clock`) | fbd                          |
| `Ixn` | fbd   | req  | fbd          | req (`anchors`)                                                                      | fbd                          |
| `Evl` | fbd   | req  | req          | opt (`roster`, `anchors`)                                                            | fbd                          |
| `Del` | fbd   | req  | req          | req (`delegates`)                                                                    | fbd                          |
| `Kil` | fbd   | req  | req          | req (`anchors`)                                                                      | req (`govern` \| `delegate`) |
| `Rpr` | fbd   | req  | req          | req (`forks`, ≥1; `anchors`, `roster` opt)                                           | fbd                          |
| `Dec` | fbd   | req  | req          | opt (a federation `Dec` carries `clock` req)                                         | fbd                          |
| `Wit` | fbd   | req  | req          | opt (`witnesses`; a federation `Wit` adds `clock` req + `roster` opt)                | fbd                          |

A **user IEL `Icp`** mirrors the KEL `Icp` on the federation binding: `federation` / `federationPin`
are **optional** (absent ⇒ a direct-mode identity), and `witnesses` is **mandatory iff federated**
(**forbidden** on a direct-mode IEL `Icp`); on a `Wit` all three are **present-iff-changed** (inv
18). The `nonce` (inception only) drives prefix unpredictability (§Prefix derivation). `pins` is the
IEL's top-level **down-pins** — a scalar SAID naming a small SAD of the participating member **KEL
event SAIDs** (a federation `Wit`'s are the witness KELs); every IEL event is anchored by a
threshold of members, so every IEL event carries it. On a `Rpr`, `roster` is
**present-iff-evicting** and restricted to a **non-empty `cut` + an optional `threshold`**: a `Rpr`
`roster` SAD carrying an `add`, or an empty `cut` (a `threshold`-only change), is **malformed →
rejected** — a bare threshold change or a replacement `add` rides a later `Evl`, the chain being
unfrozen after the repair. The kind→role allowlist gates the role's _presence_; this content check
gates its _shape_. The exact roster delta SAD and pins-SAD schemas, the consent rule for additions,
and the per-kind anchor matrix are IEL doctrine — [`iel/`](iel/).

### SEL

| Kind  | owner | topic | data | pin | previousSeal | manifest                      |
| ----- | ----- | ----- | ---- | --- | ------------ | ----------------------------- |
| `Icp` | req   | req   | opt  | fbd | fbd          | fbd                           |
| `Ixn` | fbd   | fbd   | fbd  | req | fbd          | opt (`content`)               |
| `Pin` | fbd   | fbd   | fbd  | req | fbd          | fbd                           |
| `Fld` | fbd   | fbd   | fbd  | req | req          | fbd                           |
| `Dec` | fbd   | fbd   | fbd  | req | req          | opt (`bound` on a rescission) |
| `Rpr` | fbd   | fbd   | fbd  | req | req          | req (`forks`, ≥1)             |

`owner` (the owner IEL prefix, immutable — `Icp` only), `topic`, and `data` participate in the SEL
prefix derivation (§Prefix derivation), so the `Icp` carries **no `pin`**: a pin field would make
the prefix non-recomputable for lookup. The SEL's up-pin to its owner IEL therefore rides a
**serial-1 `Pin` event batched with the `Icp`** (and re-pins on each `Ixn`) — uniformly for every
SEL, credentials included. The exact SEL shapes are SEL doctrine — [`sel/`](sel/).

## Anchoring — committing down, flooring up

An event commits to the layer that depends on it through its `manifest`, and the dependent floors
back up to its authority's current tip:

- A **KEL** event anchors the **IEL** events it authorizes (the IEL event's SAID rides in the KEL
  event's `manifest.anchors`); the IEL event authenticates via that KEL event's signature. A member
  participates in an IEL event by authoring a **fresh KEL event at its own current tip**, of
  **exactly** the kind that reveals the capability the act exercises (**kind-strict**): content ←
  `Ixn`; tier-2 establishment/governance ← `Rot` (incl. the federation `Fcp` inception); tier-3
  recovery/terminal ← `Ror`; tier-3 federation rebind (the IEL `Wit`) ← `Wit`. No higher-tier
  stand-in, and a `Rec` hosts **no** anchor (a recovered member participates via the subsequent
  `Ror`). A rotated-out key cannot produce one, which closes the rotated-out-member backdate.
- An **IEL** event anchors the **SEL** events it authorizes — an `Ixn` for content and
  credential-SEL inceptions, a `Kil` for the SEL `Dec`s it seals, an `Evl` for a SEL `Fld` re-seal,
  an `Rpr` for a SEL `Rpr` — each via `anchors`, **kind-strict** (each SEL kind is valid only when
  anchored by its matching IEL kind, and each IEL kind anchors only its matching SEL kinds). The SEL
  event floors up to the owner IEL tip via its `pin`, carried uniformly on the serial-1 `Pin` (the
  `Icp` itself stays pin-free for recomputability). The as-of authority is the **anchoring
  position** — the committing IEL event, append-only — so it cannot select a more permissive past
  ([`../../policy/documents.md`](../../policy/documents.md)).

The per-kind anchor matrix (which KEL kind anchors which IEL kind; the `Kil`-slot backing-and-demand
check) and the forward-only floor are per-primitive and protocol doctrine — [`kel/`](kel/),
[`iel/`](iel/), [`sel/`](sel/), and
[`../../../protocol-doctrine.md`](../../../protocol-doctrine.md).

## Divergence is scoped to content

Only the **content** kind (`Ixn`) is **repairable** — privileged kinds can diverge too, but only
terminally. A privileged event (a rotation, a `Evl`, a `Kil`, a terminal) is **never** archived or
overturned — reversing it would resurrect retired key material or un-do a sealed act. A divergence
is resolved by **tier**: a repair (`Rec` on the KEL, `Rpr` on the IEL / SEL) keeps the at-most-one
privileged branch and archives the all-content branch(es). The **terminal** condition is
**branch-level** — two or more branches each carrying a privileged event past the fork — and any
verifier determines it **data-locally** by walking the retained branches: a node retains a competing
branch as non-canonical evidence (rather than discarding it at the seal-cap), bounded to ≥ 2
privileged branches per spine position — the uncommitted below-seal content flood is droppable,
since a privileged event re-validates from the spine, not from below-seal content. The
seal-advancing events form a `previousSeal`-linked **spine** on which a privileged divergence, held
across retained branches, shows up as a single fork. The full divergence-and-repair doctrine is the
protocol doctrine's —
[`../../../protocol-doctrine.md` §Divergence and repair](../../../protocol-doctrine.md#divergence-and-repair).

## Prefix derivation is whole-content

A prefix derives from the entire inception body (with `said` and `prefix` blanked) — not a special
tuple. Whatever fields the inception populates participate.

- **KEL**: the device's key state. The prefix is the device-key commitment.
- **IEL**: the roster + threshold vector + the `nonce`. The `nonce` makes the prefix
  **unpredictable** from outside (camping defense) — so an IEL is located only by parties told its
  prefix.
- **SEL**: the populated inception fields — `owner` (the owner IEL prefix), `topic`, and `data`.
  (Writing it `derive(owner, topic, data)` is shorthand for _constructing that inception and taking
  its prefix_, **not** a hash of those three values pulled into a separate tuple — the prefix is the
  whole-content digest like every other event, so any field on the `Icp` enters it.) A credential
  SEL's `data` is the credential's SAID, so any two non-identical credentials get distinct prefixes
  automatically and byte-identical ones dedupe. A private credential's `data` includes a
  high-entropy nonce in the credential body, keeping the prefix unguessable; a public credential's
  prefix is recomputable from the credential itself (self-locating), which is safe because authority
  rests on **owner-rooting** (only the owner IEL anchors at the locus), not on prefix secrecy.
  Because lookup **recomputes** this prefix, the `Icp` must hold only fields the looker-up already
  has — so it carries **no `pin`** (the pin rides a batched serial-1 `Pin` event instead).

The verifier reconstructs the prefix from canonical serialization and rejects any event whose
computed prefix doesn't match its declared `prefix`.

## Batching requirements

Some kinds land only as part of a multi-event atomic batch, enforced at the merge layer:

- **Credential issuance** — a credential SEL's serial-1 `Pin` (its `v1`) is anchored by an IEL `Ixn`
  under `manifest.anchors` (the `Icp` rides `v1.previous` and is **never** itself anchored); one IEL
  `Ixn` may batch many issuances.
- **A SEL kill** — a credential-SEL `Dec` (revocation, `govern` slot) or a lookup-SEL `Dec`
  (rescission, `delegate` slot) is anchored by an IEL `Kil` under `manifest.anchors` at the matching
  `threshold` slot (one `Kil` may batch many kills).
- **Multi-identity document authorization** — the document names a custodied `issuers` SAD and each
  authorizing identity issues its **own** attestation independently (its own SEL, self-flooring via
  its serial-1 `Pin` and self-locating via `derive`); there are no per-party document pins
  ([`../../policy/documents.md`](../../policy/documents.md)).
- **Federation genesis** — the founder KEL `[Fcp, Rot]` pairs, the federation IEL `Fcp`, and the
  cross-attestation receipts land as one atomic batch. See [`federation/`](../../../federation/).

The full enforcement rules are per-primitive and federation doctrine.

## Naming conventions

- **Three-letter kind codes**, consistent across log types: `Fcp` / `Icp` / `Ixn` / `Rot` / `Ror` /
  `Rec` / `Wit` / `Dec` (KEL); `Icp` / `Ixn` / `Evl` / `Del` / `Kil` / `Rpr` / `Dec` / `Wit` (IEL);
  `Icp` / `Pin` / `Ixn` / `Fld` / `Dec` / `Rpr` (SEL).
- **Inception** is `Icp` on every log (`Fcp` for a founder pre-federation KEL); the log type
  disambiguates structural differences.
- **`Dec`** (terminal) appears on all three logs; **`Ixn`** (content) on all three; the repair kind
  is **`Rec`** on the KEL and **`Rpr`** on the IEL / SEL (the same operation, named for the KEL's
  recovery-key reveal). When a doc needs to disambiguate the shared `Dec` across layers it qualifies
  it (`KEL-Dec` / `IEL-Dec` / `SEL-Dec`).
- **`Evl`** (IEL) changes the roster/threshold only; **`Kil`** (IEL) seals a kill; on the SEL,
  **`Pin`** re-pins the floor only (tier-1, not sealing), **`Fld`** is the pure re-seal (tier-2,
  folds — the `Evl`/`Rot` analog), and a kill (cred revocation or delegation rescission) is a
  **`Dec`** (the rescission `Dec` additionally carrying the `bound`). These are distinct kinds
  because they do distinct jobs — a roster change can never ride at a kill's count, and a kill
  carries no roster delta.
