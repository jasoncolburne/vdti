# Event Shape — KEL / IEL / SEL

Canonical reference for the event-log primitives' event taxonomy, field shape, and per-kind
structural-validation rules. The per-primitive docs reference this for the underlying shape;
doctrine specific to a primitive (the exact anchor matrix, divergence and repair rules, federation
mechanics, prefix-derivation specifics) lives in the per-primitive docs and in
[`../../../protocol-doctrine.md`](../../../protocol-doctrine.md).

This is a **shape reference** — it states what fields exist, which kinds populate them, and how the
verifier enforces per-kind field rules. **Chain events carry no policy.** A KEL, IEL, or SEL event
is authorized **structurally** — by its own key state, its identity's threshold, or its owner —
never by evaluating a policy expression. Policy is a property of **documents**, not chain events;
see [`../../policy/policy.md`](../../policy/policy.md).

## Reading order

- [`kel/`](kel/) — KEL primitive specs. *(Per-primitive doctrine; landed separately.)*
- [`iel/`](iel/) — IEL primitive. *(Per-primitive doctrine; landed separately.)*
- [`sel/`](sel/) — SEL primitive. *(Per-primitive doctrine; landed separately.)*
- [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md) — cross-primitive doctrine:
  tiers, divergence and repair, the seal bound, federation convergence, the verification walk.
- [`../../policy/policy.md`](../../policy/policy.md) — the document authorization layer (the policy
  language that lives on documents, not on these events).
- [`../sad/sad.md`](../sad/sad.md) — the SAD layer: chain events are SADs.

## Common fields

Five fields appear on every event across all log types. The per-kind shape (§Per-kind structural
validation) adds fields per kind.

| Field | Type | Description |
|---|---|---|
| `said` | Digest256 | Blake3-256 hash of the canonical event content with the `said` field blanked (and `prefix` populated with its real value). Identifies the event uniquely. |
| `prefix` | Digest256 | Hash of the canonical event content with both `said` and `prefix` blanked. Identifies the chain. Derives from the **whole-event content** — not a special tuple. Two distinct inceptions for the same chain are structurally impossible without a Blake3-256 collision. |
| `serial` | u64 | Chain position. Inception events have `serial == 0`; all others have `serial >= 1`, monotonic per branch. |
| `previous` | Digest256 | SAID of the parent event. Forbidden at inception (no parent); required elsewhere. |
| `kind` | String | Log-type × event-kind discriminator. Drives per-kind structural validation, tier dispatch, and the role vocabulary the event's `manifest` may carry. |

Signatures are **not part of event content** — see [§Authentication & signatures](#authentication--signatures).

## Authentication & signatures

Signatures are not part of the event content — events are pure SAD content. The `said` is the hash
of the content; embedding a signature would make the SAID depend on a signature taken over the
prior SAID, which is circular. Signatures live **adjacent** to the event as separate data.

- **KEL events** are signed by the controller **when authored**: a primary signature on every KEL
  event, plus a **recovery signature** on the dual-signed kinds (`Ror` / `Rec` / `Fed` / `Dec`).
  The recovery key behind that second signature is the **break-glass reserve** for high-assurance
  operations — not a device-loss recovery mechanism (a lost or compromised device is rotated out at
  the identity layer via an IEL roster change).
- **IEL / SEL events** carry no adjacent signatures. They authenticate via their **KEL anchor** —
  a member's KEL event commits to the IEL event it participates in (and an IEL event commits to the
  SEL events it authorizes), and that KEL event's adjacent signature provides the authentication.
  The verifier walks from the IEL / SEL event to its anchoring event and validates the signature
  there.

This composition is what makes the three-tier capability model uniform across primitives — an IEL
/ SEL operation inherits its authentication tier from the event that anchors it. See
[`../../../protocol-doctrine.md` §Tiers](../../../protocol-doctrine.md#tiers).

## Structural authorization — the three mechanisms

Each primitive authorizes its own events structurally. There is no policy field on any chain
event.

- **KEL — a device's own key.** A KEL event is authorized by the key state the chain itself
  commits: a signing key (tier 1), a revealed rotation preimage (tier 2), a revealed rotation +
  recovery preimage (tier 3). The KEL is the root — self-authorizing, with no chain above it.
- **IEL — an identity's threshold vector over its member devices.** An IEL is a roster of member
  KELs plus a **threshold vector** `{t_use, t_govern, t_delegate, t_recover}`, indexed by the kind
  of event being authored (below). It composes no multi-party policy internally; "who is this
  identity" is the roster, "how many must act for this kind of act" is the threshold vector.
- **SEL — single-owner ownership.** A SEL is owned by exactly one IEL. Its events are authorized
  by that owner IEL: the owner's IEL event anchors the SEL event (commits to its SAID), and the
  required count is set by the SEL event's kind. A SEL hosts no roster and no policy.

**The threshold vector and its floors.** Each IEL kind draws its required count from one slot of
the vector: content (`Ixn`) from `t_use`; a roster/threshold change (`Gov`) from `t_govern`; a
delegation (`Del`) from `t_delegate`; a repair (`Rpr`) from `t_recover`; a kill-anchor (`Kil`) from
the `govern` or `delegate` slot it names; the terminal `Dec` from `t_govern`. The floors:

- `t_use >= 1` (`t_use = 1` is single-device by choice — no content resilience).
- The authority slots (`t_govern`, `t_delegate`, `t_recover`) carry **two floors**: a **security
  floor** `>= 2` (hard, every identity — no single member exercises authority) and a
  **recoverability floor** `<= |roster| − 1` (lets the identity evict a compromised member or
  recover a lost one without it). The recoverability floor is **advisory at `|roster| = 2`** (a
  two-device identity is valid but cannot evict/recover without both — the wallet warns) and
  **hard at `|roster| >= 3`** (a threshold equal to `|roster|` is a gratuitous hostage config —
  rejected). A singleton (`|roster| = 1`) sets all thresholds to 1.
- Both floors are re-checked on the post-change roster at **every** `Gov`, not only at inception.

The per-kind threshold/tier mapping and the floor derivations are the IEL primitive's —
[`iel/`](iel/). The credential acceptance and authorizing conditions that ride **above** this — on
documents — are the policy layer's ([`../../policy/policy.md`](../../policy/policy.md)).

## The manifest — what an event commits to, grouped by role

An event commits to the things below it through a **`manifest`**: the SAID of a SAD that groups
those commitments **by named role**. The manifest SAD reads `{ said, <role>: <said-or-list>, … }`,
and each role reads as "the things this event {anchors / issues / revokes / …}." The event row
holds only the manifest SAID; the grouped commitments live in the SAD, separately custody-able.

**Role vocabulary:**

| Role | Carried by | Commits to |
|---|---|---|
| `anchors` | KEL `Ixn` (req, ≥1) / `Rot` / `Ror` / `Rec`; IEL `Ixn` / `Rpr` | lower-layer event / SAD SAIDs this event anchors (a rotation or a repair cascade commits the events it realizes) |
| `roster` | IEL `Icp` / `Gov` | the roster/threshold (delta) SAD |
| `delegates` | IEL `Del` | the delegate-prefix list SAD |
| `issues` | IEL `Ixn` | a list of credential SEL `Icp` SAIDs this event issues (batched) |
| `revokes` | IEL `Kil` | a list of SEL kill SAIDs this event seals (batched) |
| `content` | SEL `Ixn` | the content SAD(s) a SEL records — the only SEL-borne manifest role (a credential SEL's `Icp` uses `data`, not a manifest) |
| `witnesses` | KEL `Icp` / `Fed` | the witness-config SAD `{ threshold, signers }` |
| `clock` | federation IEL `Icp` / `Gov` | a timestamp SAD (the federation clock — federation doctrine) |
| `folded` | seal-advancing kinds (KEL `Rot`/`Ror`/`Rec`/`Fed`; IEL `Gov`/`Del`/`Kil`/`Rpr`; SEL `Pin`/`Rpr`) | a SAD committing the content run folded since the prior seal — `{ canonical, forks[] }` plus the run's **boundary SAIDs** (so a spine walk confirms `previousSeal` consistency without expanding). `Ixn`-only; the content-only property is back-checked on expansion. Absent when no content was folded |

**Top-level structural vs. manifest.** An event's *own links* stay top-level: `said`, `previous`,
**`previousSeal`** (on every seal-advancing event — the back-link to the prior seal that renders the
spine; see [§Divergence is scoped to content](#divergence-is-scoped-to-content) and protocol-doctrine
§Forks are Seal-Bounded), `pin`, the federation `prefix`, `federationPin`, the `Kil` `threshold` enum. The `manifest`
(role-labeled) carries everything the event *commits to below it* — lower-layer event SAIDs and
documents. Entities are named by **prefix**; positions and documents by **SAID**. A SAID here is an
integrity **commitment**, not a lookup key — there is no global SAID→event index, so a SAID
harvested off a public manifest does not invert to a (possibly private) chain's prefix; logs are
fetched by prefix ([`../../../protocol-doctrine.md` §Negative checks are positive
lookups](../../../protocol-doctrine.md#negative-checks-are-positive-lookups)).

**Read the manifest kind-first.** Each kind may carry **only** the roles in its closed vocabulary
(the table above); a manifest carrying any role outside its kind's vocabulary is **malformed →
rejected**, and a role is consumed only after dispatching on a kind permitted to carry it. The
manifest SAID commits the role labels (the hash is over the keys), so a third party cannot relabel
a fixed event; the kind→role allowlist closes *author*-mislabel. This is load-bearing for the
directly-consumed roles (`roster`, `delegates`, `witnesses`, `clock`) — they have no downstream
type-check, so the allowlist is their sole protection. The back-checked roles
(`anchors` / `issues` / `revokes`) are additionally caught when the referenced event is validated
against its required kind (an `issues` entry must resolve to a credential SEL `Icp`; a `revokes`
entry to a SEL kill).

## Cross-cutting fields

Beyond the common fields, these appear on multiple kinds with consistent meaning. **Logs** names
the subset of {KEL, IEL, SEL} the field appears on; **Events** the kinds that carry it.

| Field | Type | Logs | Events | Description |
|---|---|---|---|---|
| `manifest` | Digest256 | KEL, IEL, SEL | KEL `Ixn` / `Rot` / `Ror` / `Rec` / `Icp` / `Fed`; IEL `Icp` / `Ixn` / `Gov` / `Del` / `Kil` / `Rpr`; SEL `Ixn` | SAID of the role-grouped commitment SAD (above). |
| `federation` | Digest256 | KEL | `Icp` / `Fed` | The federation IEL **prefix** this chain binds to (which federation; follows the federation's evolution). |
| `federationPin` | Digest256 | KEL | `Icp` / `Fed` | A **SAID** pinning the as-of federation position (ratcheted via `Fed`). The prefix/SAID split: `federation` is *which* federation, `federationPin` is *as of when*. |
| `pin` | Digest256 | SEL | `Ixn` / `Pin` (and inherited) | SAID of the owner IEL event this SEL event floors up to. A credential SEL's `Icp` carries no `pin` field — its `data` is the credential's SAID and the pin lives **inside** the credential (below); a lookup SEL's `Pin` event carries the pin (plus the rescission cut-off). |
| `nonce` | Nonce256 | IEL | `Icp` | Opaque random bytes chosen by the inceptor; makes the IEL prefix unpredictable. Required at inception, forbidden elsewhere. |
| `threshold` | enum | IEL | `Kil` | Which authority slot the sealed kill-anchor is priced at — `govern` (a revocation/closure) or `delegate` (a rescission). A slot **name**, never a raw integer. |
| `topic` | String | SEL | `Icp` | Application discriminator; participates in the SEL prefix derivation. |
| `data` | Digest256 | SEL | `Icp` | The content the SEL is rooted on. For a credential SEL, `data` **is the credential's SAID** (the whole reference; the `Icp` carries no manifest). For a lookup SEL, `data` is the recompute input (e.g. the rescinded prefix). Participates in the SEL prefix derivation. |

The KEL key-state fields (`publicKey`, `rotationHash`, `recoveryKey`, `recoveryHash`) and the
witness-config SAD are KEL-specific — see [`kel/`](kel/).

## Tiers — the three-tier capability model

**Tier** names the cryptographic capability required to forge an event, set by **danger-or-permanence**, and is **orthogonal to count** (the threshold vector). Tier is dispatched
from the event kind, never stored.

- **Tier 1 — signing key only.** Content. A `t_use`-counted `Ixn` is tier 1 even at a high count.
- **Tier 2 — rotation preimage.** Establishment-mutation, authority-grant, and **any sealed
  kill** (a kill must be permanent on arrival).
- **Tier 3 — rotation preimage + recovery preimage.** Repair and identity-kill.

The reserve (rotation / recovery preimage, held apart from the signing key) is required when a
forgery would be high-harm or irreversible, **or** when the act must be permanent on arrival
(sealed). A **kill** (revoke / close / rescind / decommission) is the permanence case: low-danger
(it only removes trust) but monotone (a third party relies on it), so it is sealed on a dedicated
kill-anchor and is tier 2 (identity-kill → tier 3). Tier semantics and the anchor-tier-elevation
rule (a higher-tier anchor satisfies a lower-tier requirement) are the protocol doctrine's —
[`../../../protocol-doctrine.md` §Tiers](../../../protocol-doctrine.md#tiers).

## Event taxonomy

### KEL — 8 kinds

| Kind | Tier | Sig | Role |
|---|---|---|---|
| `Fcp` | 1 | single | Founder **pre-federation** inception; self-attested, carries no `witnesses`, and cannot stand alone — its binding `Fed` follows at v=1 in the same batch. |
| `Icp` | 1 | single | Standard **federation-bound** inception; carries `federation` / `federationPin`. |
| `Ixn` | 1 | single | Content; anchors lower-layer SAIDs via `manifest` (`anchors`, ≥1). The **divergeable** kind. |
| `Rot` | 2 | single | Rotation — reveals the next signing key, commits the new one. Seal-advancing. |
| `Ror` | 3 | dual | Proactive rotate-recovery (hygiene); rotates signing **and** recovery keys. |
| `Rec` | 3 | dual | **Recover** — the KEL's repair kind: resolves `Ixn` divergence by archiving the losing branch. Reveals the recovery key (hence dual-sig); does **not** lock the chain. |
| `Fed` | 3 | dual | Federation bind / rebind; carries `federation` / `federationPin`. |
| `Dec` | 3 | dual | Terminal (decommission). |

A KEL has **one inception root**: either a founder **`Fcp → Fed`** pair (a pre-federation founder
binding into the federation it helps incept) **or** a standalone **`Icp`** (joining an existing
federation) — **never** `Fcp → Icp`. A pre-federation `Fcp` is **self-attested**, carries **no
`witnesses`** (there is no federation yet to witness it — which keeps the federation IEL's own
bootstrap non-circular), and **cannot stand alone**: its binding `Fed` is the **next event (v=1)**
in the **same atomic batch** (`Fcp` v=0 → `Fed` v=1). The full ceremony is KEL + federation doctrine
— [`kel/`](kel/), [`federation/`](../../../federation/).

### IEL — 7 kinds

| Kind | Tier | Count | Role |
|---|---|---|---|
| `Icp` | 2 | all initial members consent | Inception; pins the initial roster + threshold vector. There is **no federation inception kind** — a federation is an ordinary IEL `Icp`. |
| `Ixn` | 1 | `t_use` | Content; anchors SEL events (`anchors`) and/or issues credential SELs (`issues`, batched). The **divergeable** kind. |
| `Gov` | 1 added / 2 outgoing | all added consent ∧ `t_govern` of outgoing | **Roster / threshold change only** — carries a roster/threshold **delta** (`add` + `cut`) in `roster`. Anchors no kills. |
| `Del` | 2 | `t_delegate` | Delegation declaration — a **positive inclusion list** of delegate prefixes (`delegates`). |
| `Kil` | 2 | `threshold` slot | **Sealed kill-anchor** — anchors the SEL kill(s) it seals (`revokes`), at the `govern` (revocation/closure) or `delegate` (rescission) slot. Carries **no roster delta**; signatures only (no forced rotation). Sealed on arrival, terminal-on-divergence. |
| `Rpr` | 3 | `t_recover` | Divergence repair; carries no roster removal. |
| `Dec` | 3 | `t_govern` | Terminal; freezes all the IEL's SELs. |

A federation is a **restricted IEL** — `Icp` / `Gov` / `Dec` only (no `Ixn`, so it never diverges
and needs no `Rpr`; no `Del`, since trust is per-federation and non-transitive). Its roster is
witness KELs directly. See [`../../../protocol-doctrine.md` §Federation
convergence](../../../protocol-doctrine.md#federation-convergence) and [`federation/`](../../../federation/).

### SEL — 5 kinds

| Kind | Count | Tier | Anchored by (IEL) | Role |
|---|---|---|---|---|
| `Icp` | `t_use` | 1 | `Ixn` | Inception. For a credential SEL, `data` **is** the credential's SAID (the pin lives inside the credential) and the `Icp` carries **no** manifest. For a lookup SEL, `data` is the recompute input and a `Pin` event carries the pin. |
| `Ixn` | `t_use` | 1 | `Ixn` | Content SAD(s) + re-`pin`; ≤ 1 per SEL per IEL `Ixn`. The **only divergeable / repairable** SEL kind. |
| `Dec` | `t_govern` | 2 (identity-kill → 3) | `Kil` @ `govern` | Decommission = revocation / closure. **Sealed on arrival** (a kill is monotone — no delayed form). The killed thing is identified by *which SEL its `Dec` extends*. |
| `Pin` | `t_delegate` | 2 | `Kil` @ `delegate` | A **lookup SEL's** pin-carrier (rescission): carries a `pin` + a **cut-off** (the SAID of the last valid event on the rescinded chain), not a roster. Sealed on arrival. |
| `Rpr` | `t_recover` | 3 | `Rpr` | Divergence repair; owner-authorized, bottom-up cascade. |

Content rides the IEL `Ixn` rail (tier 1); a kill rides the IEL `Kil` rail (tier 2, sealed);
roster/threshold changes ride the IEL `Gov` rail. A SEL has no seal of its own — its finality
boundary is the owner IEL's. Credential issuance, revocation, and status are a **feature** layered
on the SEL primitive — [`features/credentials/`](../../../features/credentials/).

## Per-kind structural validation

The verifier enforces per-kind field rules: **req** (must be set), **fbd** (must be unset), **opt**
(may be either). Common fields (`said`, `prefix`, `kind`) are always required; `previous` is
forbidden on inception kinds and required elsewhere; `serial` is 0 on inception, `>=1` elsewhere;
signatures live adjacent (§Authentication & signatures).

### KEL

| Kind | publicKey | rotationHash | recoveryKey | recoveryHash | federation | federationPin | manifest |
|---|---|---|---|---|---|---|---|
| `Fcp` | req | req | fbd | req | fbd | fbd | fbd |
| `Icp` | req | req | fbd | req | req | req | opt (`witnesses`) |
| `Ixn` | fbd | fbd | fbd | fbd | fbd | fbd | req (`anchors`, ≥1) |
| `Rot` | req | req | fbd | fbd | fbd | fbd | opt (`anchors`) |
| `Ror` | req | req | req | req | fbd | fbd | opt (`anchors`) |
| `Rec` | req | req | req | req | fbd | fbd | opt (`anchors`) |
| `Fed` | req | req | req | req | req | req | opt (`witnesses`) |
| `Dec` | req | fbd | req | fbd | fbd | fbd | fbd |

The dual-signed kinds (`Ror` / `Rec` / `Fed` / `Dec`) carry an adjacent recovery signature
(§Authentication & signatures). Exact key-state semantics and the witness-config SAD are KEL
doctrine — [`kel/`](kel/).

### IEL

| Kind | nonce | manifest | threshold |
|---|---|---|---|
| `Icp` | req | req (`roster`; federation `Icp` adds `clock`) | fbd |
| `Ixn` | fbd | req (`anchors` and/or `issues`) | fbd |
| `Gov` | fbd | req (`roster`; federation `Gov` adds `clock`) | fbd |
| `Del` | fbd | req (`delegates`) | fbd |
| `Kil` | fbd | req (`revokes`) | req (`govern` \| `delegate`) |
| `Rpr` | fbd | opt (`anchors`) | fbd |
| `Dec` | fbd | fbd | fbd |

The `nonce` (inception only) drives prefix unpredictability (§Prefix derivation). The exact roster
delta SAD schema, the consent rule for additions, and the per-kind anchor matrix are IEL doctrine
— [`iel/`](iel/).

### SEL

| Kind | topic | data | pin | manifest |
|---|---|---|---|---|
| `Icp` | req | req | fbd | fbd |
| `Ixn` | fbd | fbd | req | opt (`content`) |
| `Dec` | fbd | fbd | fbd | fbd |
| `Pin` | fbd | fbd | req | fbd |
| `Rpr` | fbd | fbd | fbd | fbd |

`topic` + `data` participate in the SEL prefix derivation (§Prefix derivation). A credential SEL's
pin rides inside the credential its `data` names; a lookup SEL's pin rides on a `Pin` event. The
exact SEL shapes are SEL doctrine — [`sel/`](sel/).

## Anchoring — committing down, flooring up

An event commits to the layer that depends on it through its `manifest`, and the dependent floors
back up to its authority's current tip:

- A **KEL** event anchors the **IEL** events it authorizes (the IEL event's SAID rides in the KEL
  event's `manifest.anchors`); the IEL event authenticates via that KEL event's signature. A member
  participates in an IEL event by authoring a **fresh KEL event at its own current tip** committing
  to that IEL event — a rotated-out key cannot produce one, which is what closes the rotated-out-member backdate.
- An **IEL** event anchors the **SEL** events it authorizes (`anchors` / `issues` for content;
  `revokes` for kills); the SEL event floors up to the owner IEL tip via its `pin` (or, for a
  credential SEL, via the pin inside the credential its `data` names). The verifier enforces a
  document's pin `== (its anchoring event).previous`, so a pin cannot select a more permissive past
  ([`../../policy/documents.md`](../../policy/documents.md)).

The per-kind anchor matrix (which KEL kind anchors which IEL kind; the `Kil`-slot backing-and-demand check) and the forward-only floor are per-primitive and protocol doctrine —
[`kel/`](kel/), [`iel/`](iel/), [`sel/`](sel/), and
[`../../../protocol-doctrine.md`](../../../protocol-doctrine.md).

## Divergence is scoped to content

Only the **content** kind (`Ixn`) is divergeable and repairable. A privileged event (a rotation,
a `Gov`, a `Kil`, a terminal) is **never** archived or overturned — reversing it would resurrect
retired key material or un-do a sealed act. A divergence is resolved by **tier**: a repair
(`Rec` on the KEL, `Rpr` on the IEL / SEL) keeps the at-most-one privileged branch and archives the
all-content branch(es). The **terminal** condition is **branch-level** — two or more branches each
carrying a privileged event past the fork — and any verifier determines it **data-locally** by walking
the retained branches: a node retains a competing branch as non-canonical evidence (rather than
discarding it at the seal-cap), and the seal-advancing events form a `previousSeal`-linked **spine** on
which a privileged divergence is a single visible fork. The full divergence-and-repair doctrine is the
protocol doctrine's — [`../../../protocol-doctrine.md` §Divergence and
repair](../../../protocol-doctrine.md#divergence-and-repair).

## Prefix derivation is whole-content

A prefix derives from the entire inception body (with `said` and `prefix` blanked) — not a special
tuple. Whatever fields the inception populates participate.

- **KEL**: the device's key state. The prefix is the device-key commitment.
- **IEL**: the roster + threshold vector + the `nonce`. The `nonce` makes the prefix
  **unpredictable** from outside (camping defense) — so an IEL is located only by parties told its
  prefix.
- **SEL**: `derive(owner, topic, data)`. A credential SEL's `data` is the credential's SAID, so any
  two non-identical credentials get distinct prefixes automatically and byte-identical ones dedup. A
  private credential's `data` includes a high-entropy nonce in the credential body, keeping the
  prefix unguessable; a public credential's prefix is recomputable from the credential itself
  (self-locating), which is safe because authority rests on **owner-rooting** (only the owner IEL
  anchors at the locus), not on prefix secrecy.

The verifier reconstructs the prefix from canonical serialization and rejects any event whose
computed prefix doesn't match its declared `prefix`.

## Batching requirements

Some kinds land only as part of a multi-event atomic batch, enforced at the merge layer:

- **Credential issuance** — a credential SEL `Icp` is anchored by an IEL `Ixn` that references it
  under `manifest.issues` (one IEL `Ixn` may batch many issuances).
- **A SEL kill** — a SEL `Dec` (or a lookup SEL's `Pin`) is anchored by an IEL `Kil` that
  references it under `manifest.revokes`, at the matching `threshold` slot (one `Kil` may batch
  many kills).
- **Multi-identity document authorization** — each authorizing identity anchors the document on its
  own IEL, with the document's per-party pin `== that party's anchoring event's `previous``; the
  issuers quiesce their identities between finalizing and anchoring
  ([`../../policy/documents.md`](../../policy/documents.md)).
- **Federation genesis** — the founder KEL `[Fcp, Fed]` pairs, the federation IEL `Icp`, and the
  cross-attestation receipts land as one atomic batch. See [`federation/`](../../../federation/).

The full enforcement rules are per-primitive and federation doctrine.

## Naming conventions

- **Three-letter kind codes**, consistent across log types: `Fcp` / `Icp` / `Ixn` / `Rot` / `Ror`
  / `Rec` / `Fed` / `Dec` (KEL); `Icp` / `Ixn` / `Gov` / `Del` / `Kil` / `Rpr` / `Dec` (IEL); `Icp`
  / `Ixn` / `Dec` / `Pin` / `Rpr` (SEL).
- **Inception** is `Icp` on every log (`Fcp` for a founder pre-federation KEL); the log type
  disambiguates structural differences.
- **`Dec`** (terminal) appears on all three logs; **`Ixn`** (content) on all three; the repair kind
  is **`Rec`** on the KEL and **`Rpr`** on the IEL / SEL (the same operation, named for the KEL's
  recovery-key reveal). When a doc needs to disambiguate the shared `Dec` across layers it qualifies
  it (`KEL-Dec` / `IEL-Dec` / `SEL-Dec`).
- **`Gov`** (IEL) changes the roster/threshold only; **`Kil`** (IEL) seals a kill; **`Pin`** (SEL)
  carries a lookup SEL's pin + cut-off. These are distinct kinds because they do distinct jobs — a
  roster change can never ride at a kill's count, and a kill carries no roster delta.
