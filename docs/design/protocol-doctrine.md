# Protocol Doctrine

The structural rules that govern VDTI — security invariants, cross-cutting doctrines, and
verification mechanics. Each part below is load-bearing for protocol correctness; per-primitive
design docs cross-reference these as the upstream source rather than re-deriving them.

Read [`system-thesis.md`](system-thesis.md) first. The thesis is the framing — adversarial-first
posture, end-verifiability over data-from-any-source, fail-secure default — and points back here for
the structural rules that realize those properties.

**[Part 1 — Security Invariants](#part-1-security-invariants):**

- [Terminology](#terminology) — locked portion, per-node chain states, cross-chain anchor
  satisfaction.
- [Operation categories](#operation-categories) — serving, consuming, resolving.
- [Compromise is permanent](#compromise-is-permanent) — authority belongs to current state only.
  - [Pin everything to current, floored per chain](#pin-everything-to-current-floored-per-chain)
  - [Tiers](#tiers) — the three-tier capability model
  - [Structural authorization](#structural-authorization) — no policy on chain events
  - [Forks are seal-bounded](#forks-are-seal-bounded)
  - [Divergence and repair](#divergence-and-repair)
  - [Kills are sealed; validity bounds are contiguous](#kills-are-sealed-validity-bounds-are-contiguous)
  - [Inception tiers](#inception-tiers)
  - [Decommission and clean retirement](#decommission-and-clean-retirement)
  - [Limit of the doctrine — current-state compromise](#limit-of-the-doctrine--current-state-compromise)

**[Part 2 — Cross-Cutting Doctrines](#part-2-cross-cutting-doctrines):**

- [Ordering without timestamps](#ordering-without-timestamps)
- [Federation convergence](#federation-convergence)
- [Extension discipline](#extension-discipline)

**[Part 3 — Verification Mechanics](#part-3-verification-mechanics):**

- [Verification tokens as proof of verification](#verification-tokens-as-proof-of-verification)
- [Walk semantics](#walk-semantics)
- [Structural problems error; everything else is reported](#structural-problems-error-everything-else-is-reported)
- [Negative checks are positive lookups](#negative-checks-are-positive-lookups)
- [Merge verification and advisory locking](#merge-verification-and-advisory-locking)
- [Federation witnessing in verification](#federation-witnessing-in-verification)
- [Effective-SAID comparison](#effective-said-comparison)

---

## Part 1: Security Invariants

The invariants below are load-bearing for VDTI security. They are stated structurally rather than
statistically: the protocol's safety claims hold _by construction_, not by observation. Verifier
implementations enforce them on every walk; an event or chain state that violates them is rejected
regardless of source.

### Terminology

Structural concepts referenced throughout. Distinct senses; not interchangeable.

- **Privileged / content** (for post-inception events): **content** is tier 1 — `Ixn` (and the SEL's
  floor `Pin`); **privileged** is every non-content kind — tier 2 or 3 ([§Tiers](#tiers)). Every
  **non-inception** privileged event advances the seal, and only privileged kinds do
  ([§Forks are Seal-Bounded](#forks-are-seal-bounded)). **Inception is the exception on both
  counts**: an `Icp` / `Fcp` is the spine root (it advances no seal) and may itself be tier 1 (KEL /
  SEL) or tier 2 (IEL) — it never enters fork dispatch, because two distinct inceptions for one
  prefix are impossible by whole-content prefix derivation.
- **Locked**: the portion of a chain before its most recent privileged event. **Within-chain rule**
  — locked events are structurally immutable within their own chain: a repair cannot target them,
  and within-chain historical authorizations are not retroactively unsatisfiable. The privileged
  event ratchets the lock forward. On a chain carrying a fork, the locked portion is still read
  against the tracked seal — the most recent seal-advancing event that landed cleanly on the linear
  chain; a seal-advancing event on a competing branch never becomes the lock (it is a privileged
  fork, and the divergence rules read it — see [§Divergence and repair](#divergence-and-repair)).
- **Chain states** (per-node — a chain is in exactly one, computed from the events a node holds):

  - **Active** — linear chain; accepts linear extension.
  - **Divergent** — a **fork**: two **distinct** events at one serial. While the fork is **live**
    (at or above the seal) the chain is **frozen** — it accepts no new event of any kind **except
    the resolving repair** (`Rec`/`Rpr`; a fork one of whose branches **ends in** a terminal `Dec`
    resolves by tier-rank with no repair) until the divergence is resolved (see
    [§Divergence and repair](#divergence-and-repair)). A fork is one of:
    - **reconcilable** (elsewhere: **recoverable**) — ≤ 1 privileged branch. A repair **retains one
      branch as the canonical chain** and **archives the rest** (archived ≠ discarded — they stay
      kept as non-canonical evidence, keep-all-data). The retained branch is the **repairer's own**;
      a lone privileged branch can be retained **only by its own author** — a different party's
      repair attaches at a different branch, which would have to archive the privileged one
      (forbidden), so only its author can resolve the fork. The chain returns to **Active**. When
      the lone privileged branch is a **terminal `Dec`** (an identity or SEL decommission — it
      admits no successor to carry a repair), the fork resolves by **tier-rank** with no repair —
      the terminal outranks the content, which is archived non-canonical; a `{Dec, content}` fork
      thus ends **Decommissioned**, the same reading as a cleanly-landed `Dec` (the effective SAID
      is the `Dec`'s own — a resolved fork carries no fork digest —
      [§Divergence and repair](#divergence-and-repair)). A `Kil` is **not** terminal (it seals a
      kill on a _target_, not its host chain, which continues), so a `{Kil, content}` fork is an
      ordinary reconcilable one — the `Kil` retained, the content archived, resolved by a repair
      like `{Evl, content}`.
    - **irreconcilable** (elsewhere: **terminal**) — **two or more branches each carry a privileged
      event at or beyond the divergent serial**. No branch can be archived (a privileged event is
      never archived), so no single chain can be chosen and the prefix must **reincept**. This is a
      **branch-level** condition (not a single-serial one), determined by **any verifier as a
      data-local walk over the retained branches**: a node retains a competing branch as
      non-canonical evidence rather than discarding it (see
      [§Divergence and repair](#divergence-and-repair)), so a node holding both privileged branches
      reads the condition directly, and a node holding only one assembles the others — the witness
      beacon enumerates the competing branch SAIDs, the node fetches and walks them. The federation
      **propagates** the branches; it does **not** decide terminality. A fork with no privileged
      branch, or only one, is **reconcilable**, not this.
  - **Decommissioned** — a terminal `Dec` has landed cleanly. Fully terminal: accepts no submission.

  _Divergence_ is the umbrella over every fork; the per-node state for a fork is **Divergent**
  (reading `forked`). A branch-level walk that finds two or more privileged branches reads the
  prefix as **disputed** (reading `disputed`) — a property **any verifier computes from the retained
  branches**, read over the chain's events at-and-beyond the divergent serial, where events strictly
  below stay canonical. The beacon's role is to deliver the branches to a one-branch holder, never
  to decide the verdict. It is **not** a fourth per-node state; the per-node states stay Active /
  Divergent / Decommissioned.

- **Cross-chain anchor satisfaction**: whether a document's or upper-layer event's authorization
  still holds is checked against its contributing lower-layer anchors. How a contributing anchor
  becomes non-canonical depends on its **tier**: a tier-1 (`Ixn`) anchor (archivable) drops when a
  later repair archives its host; a tier-2/3 anchor (on a seal-advancing event, durable against
  repair) drops only when it sits **at-or-beyond the divergent serial** on a host chain that becomes
  **disputed** — a tier-2/3 anchor below the last clean seal stays anchored. Either way the
  lower-layer verifier reports the SAID as not-anchored on the canonical branch, and the dependent
  answer flips to unsatisfied. Distinct from within-chain state — locked events stay locked within
  their own chains; cross-chain satisfaction is handled by composition redundancy (anchor count
  above the exact threshold).

### Operation Categories

The database cannot be trusted — it may have been altered. All operations on chain data fall into
three categories:

1. **Serving** — returning data to a client or peer. **No verification needed**; the receiver
   verifies what they get. (Read endpoints — effective-SAID lookups, paginated reads — which carry
   their query in the request body, not the address.)
2. **Consuming** — using data for a security decision (anchoring, key extraction, divergence
   routing, merge). **MUST verify the full chain first.** The only way to reach consumed data is
   through that primitive's **verification token** (`KelVerification` / `IelVerification` /
   `SelVerification`), obtainable only via the verifier — so verification and access happen in the
   same pass, eliminating time-of-check-to-time-of-use gaps.
3. **Resolving** — comparing state to decide whether to sync. A wrong answer triggers an unnecessary
   sync (which itself verifies), not a security hole; standalone functions are acceptable here.
   (Effective-SAID comparison, anti-entropy, proactive-rotation prechecks.)

### Compromise is Permanent

The protocol grants authority **only to a chain's current state** (and its most-recent shared
pre-divergence state, where divergence has occurred). Past keys, past members, past delegators —
anything rotated, evicted, or revoked out — has zero structural ability to act. Per primitive:

- **KEL** — a signing or rotation key compromised in the past cannot extend the chain today, even if
  the adversary still holds the key material. A new event requires the **current** key.
- **IEL** — a member evicted via a `Evl` cannot land further acts after their eviction.
- **SEL** — a SEL pins **up** to its owner IEL's current tip; a rotated-out party of that IEL has no
  authority over it.

This closes the **stale-state kill-switch problem**: without it, everyone who ever held authority
over a chain would retain a permanent kill switch. The structural mechanisms that enforce it are the
per-chain forward floor, the seal bound, the tier model, and fresh-participation — below.

#### Pin everything to current, floored per chain

Every event pins its dependencies' **current tips**, and a per-chain **forward-only floor** keeps
those pins from regressing. The floor lives on the chain doing the pinning (intra-chain — there is
no cross-chain clock for ordering). Two distinct backdate mechanisms are closed, and they are kept
separate:

- **Fresh participation closes the deep-member backdate.** A member participates in an IEL event by
  authoring a **fresh KEL event at its own current tip** that commits to that specific IEL event
  (`Ixn → IEL Ixn`, `Rot → IEL Evl`), signed by its **current** key. A rotated-out key cannot
  produce one — a KEL append needs the current key, and an old event already committed to something
  else. There is no detached-signature-resolved-as-of-a-pin path. So a rotated-out member cannot
  retroactively appear to have authorized an IEL event.
- **The forward floor closes the as-of-context backdate.** An event cannot pin a dependency at an
  old position (an old roster, an old federation context, an old authority state), because the
  per-chain floor only moves forward. This is the monotonicity backstop for the as-of pins.

**As-of authority is judged by the anchoring position, never by a self-asserted pin.** A document
carries **no** self-asserted pin; authority-affecting resolution — grandfather and rescission
ancestry, roster and delegation state — is judged by the **anchoring position**: the serial of the
committing event, append-only-fixed via the chain `document ← SEL ← IEL Ixn ← KEL Ixn` (each
`previous`-linked). There is no self-asserted document value to backdate: the as-of is read directly
from the anchoring position, which lives on the append-only chain and cannot be inserted into the
past. The structural SEL down-pin that floors each log to its owner still satisfies
`pin == anchor.previous` as a chain link, but that is a chain field, not a document's claim
([`primitives/policy/documents.md`](primitives/policy/documents.md)).

#### Tiers

**Tier** names the cryptographic capability required to forge an event. It is set by
**danger-or-permanence** and is **orthogonal to count** (how many members must act). Tier is
dispatched from the event kind, never stored.

| Tier | Capability                            | Used for                                                 |
| ---- | ------------------------------------- | -------------------------------------------------------- |
| 1    | signing key only                      | content (`Ixn`) — even at a high count                   |
| 2    | rotation preimage                     | establishment-mutation, authority-grant, any sealed kill |
| 3    | rotation preimage + recovery preimage | repair, identity-kill                                    |

Two **reserve** preimages back the upper tiers, both held apart from the signing key: the **rotation
reserve** (the rotation preimage) gates tier 2, and the **recovery reserve** (the recovery preimage)
gates tier 3 alongside it. A reserve is required when a forgery would be high-harm or irreversible,
**or** when the act must be **permanent on arrival** (sealed). A **kill** (revoke / close / rescind
/ decommission) is the permanence case: low-danger (it only removes trust) but **monotone** (a third
party relies on it), so it must be sealed — it rides a dedicated sealed kill-anchor and is tier 2
(an identity-kill is tier 3). Only content is tier 1.

The old signing key is **not** a prerequisite for tier 2 or 3 — the rotation preimage reveals the
new signing key. On the KEL, `Rot` is single-signed (tier 2); `Ror` / `Rec` / `Wit` / `Dec` are
dual-signed (tier 3, new signing + recovery). IEL and SEL events have no intrinsic key state, so
they reach a tier by **anchoring in a lower-layer event of the matching kind** — **kind-strict**:
each IEL / SEL kind is anchored by **exactly** the kind that reveals the capability it exercises
(content ← `Ixn`; tier-2 establishment/governance ← `Rot`; tier-3 recovery/terminal ← `Ror`; the
federation rebind, the IEL `Wit`, ← a KEL `Wit`). A KEL `Wit` anchors **only** the IEL `Wit`, and a
`Rec` hosts no anchor. Kind-strict binding keeps content on an archivable host and closes the
signing-key-only path to forging governance acts, grants, and terminals on the chains that root
other chains' authority. The per-primitive anchor matrix is in
[`primitives/data/event-logs/`](primitives/data/event-logs/).

#### Structural authorization

**Authorization is structural**, per primitive:

- **KEL** — the device's own key state (tier 1/2/3 above).
- **IEL** — a roster of member KELs plus a **threshold vector**
  `{t_use, t_govern, t_delegate, t_recover}`, indexed by the event's kind. Every IEL kind **prices
  itself**: `Ixn` from `t_use`, `Evl` from `t_govern`, `Del` from `t_delegate`, `Rpr` from
  `t_recover`, `Wit` and the terminal `Dec` from `t_govern`. The one count-parametrized kind is the
  sealed kill-anchor `Kil`, whose committed `threshold` slot (`govern` / `delegate`) names the count
  — **backed** by the `Kil`'s own signatures at the IEL walk and **demanded** by the anchored kill's
  kind at the SEL check. So verifying an IEL chain's validity needs **no SEL input** — each event
  prices from its own kind.
- **SEL** — single-owner ownership: the owner IEL anchors the SEL event, and the count is set by the
  SEL event's kind.

**Threshold-vector bounds** (re-checked on the post-delta config at every config-changing event — a
user `Evl`, a **user `Rpr`-cut** (the repair-and-evict fold below), or a federation `Wit`,
**including a config-only `Wit`** that changes `threshold` / `signers` with no roster delta — not
only at inception): `t_use >= 1`; the authority slots carry a **security floor** `>= 2` (hard for
every identity of `|roster| >= 2` — no single member exercises authority; the singleton below is the
degenerate case) and a **recoverability ceiling** `<= |roster| − 1` (evict/recover without one
member — advisory at `|roster| = 2`, hard at `|roster| >= 3`, where a threshold equal to `|roster|`
is a gratuitous hostage config and is rejected). **`t_govern <= t_recover` is a hard floor**
wherever a threshold is declared or changed — recovery reveals the reserve and a `Rpr` may carry a
roster cut, so it is never priced below governance. And the roster is **never emptied**: post-delta
**`|roster| = |roster| + |add| − |cut| >= 1`** (the roster is a set — `add ∉` it, `cut ⊆` it,
`cut ∩ add = ∅`), making every singleton's roster downward-immutable. A singleton (`|roster| = 1`)
sets all thresholds to 1. The federation IEL's recoverability ceiling is **hard** (it is critical
infrastructure and must always be able to evict a compromised witness), so a federation requires
`|roster| >= 3` — and its **witness-config** carries its own recoverability cap on top:
**`threshold <= min(|roster| − 2, signers − 1)`**, because an eviction `Wit` must self-attest
without the evicted member (the self-attest pool is `|roster| − 2`, and at sub-pool selection the
selected pool loses one too — the `signers − 1` leg is the one that binds for `signers >= 2`; that
leg is **waived at `signers = 1`**, the lone-witness carve-out, where evict-one self-attestation is
position-luck, warned). The full cap **plus the majority floor `threshold > signers/2`**
([§Federation convergence](#federation-convergence)) are re-applied on **any `Wit` that changes
roster, `threshold`, or `signers`** — not a `cut` alone — so a bare shrink that would strand the
federation un-recoverable (`|roster| 5→4` at `threshold 3`), or a `signers` drop landing on the
binding leg (`{signers 4, threshold 3} → {signers 3, threshold 3}` at `|roster| = 5`, which passes
the roster leg yet violates `threshold <= signers − 1`), is **rejected**, forcing evict-and-replace
or a simultaneous threshold-and-`signers` drop. This re-check is what actually enforces "the
federation can never be brought to an unrecoverable size" — for `signers >= 2` the roster leg alone
is the slack one.

Authorization that a third party relies on — who issued a credential, who may present it — is the
job of the **document policy layer** ([`primitives/policy/policy.md`](primitives/policy/policy.md)),
which sits above the primitives and consumes their verification. Keeping the two apart removes the
issuer-chosen-policy backdate surface from the chain entirely.

#### Forks are Seal-Bounded

The structural mechanism that enforces current-state-only authority is the chain's **seal**.

Each primitive tracks `last_seal_advancing_event` — the SAID of the chain's most recent
seal-advancing event that landed cleanly on the linear chain. A new event's parent must sit
at-or-after the seal (`parent_serial >= seal_serial`); a submission whose parent sits in the locked
portion is **rejected as a canonical extension**. Whether that rejected fork is **retained as
non-canonical evidence** is a separate, witnessing-gated decision — a losing **content** sibling on
a witnessed chain never forms (so there is nothing to retain), while a privileged branch, or any
fork on a direct-mode chain, is kept, so the proof that a divergence occurred survives wherever a
fork actually forms (see [§Divergence and repair](#divergence-and-repair)). This guarantees the
authorization context resolved at the event's parent is the chain's currently-tracked state, not a
stale one.

**Privileged** means any non-content kind — everything at tier 2 or 3 ([§Tiers](#tiers));
**content** (`Ixn`, plus the SEL's floor `Pin`) is tier 1. Every **non-inception** privileged kind
advances the seal, and only privileged kinds do — so **past inception** the two classes coincide,
which is why the divergence rules below can dispatch on either. (Inception is outside this: an `Icp`
/ `Fcp` is the spine root — it advances no seal — and may be tier 1 or tier 2; it never enters fork
dispatch, since one prefix admits only one inception.) The **seal-advancing** kinds (those that open
a new locked window, plus the terminal `Dec` which opens none) per primitive:

- **KEL**: `Rot` / `Ror` / `Rec` / `Wit` (and `Dec`).
- **IEL**: every non-inception **privileged** event advances the seal — `Ixn` is the lone content
  kind, and an IEL `Ixn` does not advance the seal; the privileged kinds (`Evl` / `Del` / `Kil` /
  `Rpr` / `Dec` / `Wit`) are the window-openers.
- **SEL**: `Fld` / `Rpr` (and `Dec`) — `Fld` is the SEL's re-seal, a tier-2 privileged kind (the
  `Rot` / re-seal-`Evl` analog for a primitive with no keys or roster to evolve); a content `Ixn`
  and a floor `Pin` do not advance the seal.

The terminal `Dec` advances the seal to its own serial and permits no successor. The seal-cap
rejects any submission whose parent sits before the `Dec`; a direct `Dec`-child passes the cap and
is rejected by the terminal-state gate.

KEL additionally tracks which recovery-key preimage is currently committed: once a recovery preimage
is spent (revealed by an `Ror` / `Rec` / `Wit` / `Dec`), it cannot be reused to recover against an
earlier divergence.

**Bounds on the post-seal window.** KEL, IEL, and SEL bound the gap between seal-advancing events at
`(MINIMUM_PAGE_SIZE − 1)/2 = 64` non-seal-advancing events **per lineage**, so the canonical
two-branch fork anchored at the last seal — both lineages (≤ 64 each) plus the resolving repair —
fits one page on any conformant deployment (`MINIMUM_PAGE_SIZE = 129 = 2·64 + 1`, a protocol
constant, not a per-deployment knob). The page carries **both** competing branches plus the repair
because a source → sink transfer delivers the fork to a sink holding neither branch — the repair's
content-only guard needs every branch to walk within one atomic unit. A **local** run of the
**discriminator** (the merge layer's repair-resolution walk,
[`kel/merge.md`](primitives/data/event-logs/kel/merge.md)) needs less: its hot page is the retained
branch plus the repair event, with the losing branch named by the root committed as `fork` condemned
— every other closing below the seal and by descent — validated from retained storage, not held in
the page. On the IEL the cap is just as load-bearing: content (`Ixn` — the **content rail**, the
stream issuance rides via `anchors[]`) does **not** advance the seal, so trailing issuances
accumulate and the seal lags the tip; without the cap the post-seal window grows unbounded and
page-atomic content-divergence repair breaks. A busy issuer that fills the window **re-seals with a
roster-less `Evl`** (**omits `roster`** — no roster change — the identity-layer analogue of a KEL
re-sealing via `Rot`; validation **accepts** a roster-less re-seal `Evl`), advancing the seal with
no new kind. (Under a network partition both halves can fill the cap and re-seal independently; the
two roster-less `Evl`s differ by `previous` and collide as `{Evl, Evl}` → terminal, so a
**high-volume issuer serializes its content submissions** — a discipline separate from, and
additional to, **serializing governance** (the operational rule that governance and kill events pass
through **one designated submitter** so two never race during a partition — else `{Evl, Evl}` /
`{Kil, Kil}` → terminal; operator doctrine, forthcoming). **Governance serialization is
safety-critical everywhere** — a governance race is privileged, and the witnessing majority floor
never gates privileged events. **Content-rail serialization splits by mode**: on a **witnessed**
chain the floor prevents a competing content sibling going live — a partitioned content rail
**stalls** rather than forks — so the discipline is a **liveness / waste** concern there; it stays
**safety-critical on direct-mode / solo** chains, where no majority gates content and an
un-serialized rail is the terminal-`{Evl, Evl}` path
([§Federation convergence](#federation-convergence)).) The exact constant, the roster-less re-seal,
and the content-rail serialization are IEL doctrine —
[`primitives/data/event-logs/iel/`](primitives/data/event-logs/iel/) (forthcoming).

**The spine.** The seal-advancing events form a **spine**: each carries a top-level `previousSeal`
back-link to the prior seal-advancing event, so following `previousSeal` renders a seal-only view
(`Icp → seal → seal → …`) while `previous` renders the full flat chain. A seal does **not** commit
its content run — the retained run since the prior seal is the derivable linear chain
`[previousSeal..previous]` (nodes keep the full bodies; the flat query returns them), and "content
was folded here" is the derived predicate `previous != previousSeal`. Only a **repair** seal carries
a manifest fold field: the **`fork`** role, the single losing-branch **root** it condemns — every
other competing branch closes below the seal and by descent (§Divergence and repair). The spine is a
**convenience** view, verified by the same chain walk with `previousSeal` substituted for
`previous`, yielding authority state and a terminal-divergence view (a spine fork is two competing
seals — privileged, hence terminal) but not recoverable content forks or content completeness. The
detection guarantee, and any decision that turns on a content event, use the **flat** walk; a
skipped seal is caught by the flat walk (it appears as a seal-advancing event when `previous`
traverses the run) plus spine-fork detection (the real skipped seal, once held, competes at its
spine position). The spine alone trusts `previousSeal`; it is fail-secure (a forged `previousSeal`
that skips a seal surfaces as a competing seal when the real one is held, and is otherwise bounded
by the **eclipse residual** — a reader cut off from a branch reads stale until the beacon delivers
it; [§Federation convergence](#federation-convergence)). Event structure:
[`event-shape.md`](primitives/data/event-logs/event-shape.md).

#### Divergence and repair

A chain **diverges** the instant it carries two **distinct** events at one serial. Distinct means
different-SAID: SAIDs are content-addressable, so two byte-identical events **are** one event (the
submit path accepts an already-present event idempotently, never as a second branch). So identical
acts dedupe — two parties revoking the same credential produce the same `Dec` SAID and there is no
divergence (signatures live adjacent to the event, outside the SAID'd bytes —
[event-shape](primitives/data/event-logs/event-shape.md) — so the same act by two parties is
byte-identical); only distinct events at one position collide.

**A live divergence freezes further origination; the reading is a pure walk.** A node's **reading**
of a chain — Active / `forked` / `disputed` — is a **pure function of the events it holds**: the
walk derives the seal from those events (the most recent seal-advancing event that landed cleanly on
a linear run) and reads the fork against it, so two nodes holding the same events read the same
state whatever order the events arrived in. What **freezes** is **origination**: while a node holds
a fork **at or above the derived seal**, it originates **no new event of any kind** — content,
governance, rotation, kill — onto that live fork. The ways forward are the repair or, for a
**content** fork, a **seal-advancer on the winning branch** that buries the loser below the new seal
(you cannot fork the past, so a below-seal content loser is inert). Freezing is an **origination
posture**, not a stored flag and not the reading: a node that comes to hold a burying seal-advancer
re-reads the chain **Active**, exactly as a node that sealed before it ever saw the loser. One
carve-out on the resolving move: a fork whose single privileged branch is a **terminal `Dec`** (an
identity/SEL decommission — no successor to carry a repair) resolves by **tier-rank** with no repair
(below). A `Kil` is **not** terminal (it kills a _target_, not its host chain), so `{Kil, content}`
repairs like `{Evl, content}`. (A below-seal **content** straggler that arrives after the chain
already sealed past its serial is kept as evidence or dropped as **uncommitted** content — content
condemned by no repair's `fork` and beyond the evidence bound; the keep-or-drop selector is the
retention bound below — never a freeze: the canonical branch is already sealed past it. A below-seal
**privileged** straggler is not inert — it is a spine fork and flips the reading to `disputed`; see
pre-seal verifiability, below.) Freezing origination on divergence is the founding insight of the
event-log primitives.

On a **witnessed** chain, a **content** fork rarely reaches this machinery at all: the witnessing
majority floor makes two competing content siblings un-co-witnessable, so the fork is **prevented**
from forming below fork-cost ([§Federation convergence](#federation-convergence)). The rules below
are what run in the **residual** — direct-mode / no-witness chains, a witness compromise at
fork-cost, split-stalls (where the repair is the exit), and **privileged** races, which the floor
never gates.

The **shape-validity gate** — reject a seal-advancer that would bury a **privileged** branch, or a
repair that would archive a privileged branch or condemn its own retained chain — runs wherever an
event is admitted to **trusted** state, in either mode. On a witnessed chain the **witness** applies
it before signing: a shape it declines never reaches threshold, and a non-witness admits nothing
below threshold. On a direct-mode chain the **merging node applies it itself**, since there is no
witness to defer to. Merge otherwise integrates every structurally valid event (keep-all-data) and
lets the walk read the state; it does not stick a divergence into the reading. Content-fork
**prevention** is the witnessed-only layer; a direct-mode content fork forms, reads `forked`
(fail-secure), and resolves by repair or by a burying seal-advancer.

**Divergence is resolved by tier, not by identity.** Chain data cannot tell the rightful operator
from an adversary — both branches were structurally authorized when they landed — so resolution
turns on **tier**, never on who is presumed legitimate. Two rules govern every repair — the first
**machine-enforced**, the second **automatic by construction**, not a check any verifier could run:

- **Only tier-1 events are archivable** (content `Ixn`; on the SEL, also the floor `Pin`). A
  privileged event — a rotation, a `Evl`, a `Kil`, a terminal — is **never** archived or overturned:
  reversing a rotation resurrects retired keys, and un-doing a kill breaks a third party's reliance.
  Enforced by the merge layer on every repair (the content-only guard below).
- **An honest repair never extends an adversarial event.** Chain data carries no authorship, so this
  is not enforceable as a check — it holds by construction for the honest submitter, who attaches at
  their **own** last event. (A dishonest submitter's "own branch" _is_ the adversarial branch; what
  protects everyone else there is rule 1 plus hard auth — a repair needs the recovery reserve.)

From those two rules, recovery is **one universal rule plus one permission check.** A repair (`Rec`
on the KEL, `Rpr` on the IEL / SEL — tier 3, requiring the **recovery reserve** held apart from the
signing key) attaches at **the controlling entity's last event** — the device's for a KEL, the
identity's for an IEL, the owner's for a SEL — **retaining** that branch (the **retained tail**) and
archiving every other branch (the **archival tails** — there may be several, since the adversary can
submit divergent `Ixn`s and they are all archived). On a multi-member IEL this is unambiguous even
though several devices operate the identity: **an identity is a single entity**, so the attach point
is the tip of the branch the recovering `t_recover` coalition retains as the identity's canonical
one — never a co-member's isolated event, and never a serial below the tracked seal.

Attaching at the entity's **own** last event satisfies the no-extend-adversary rule automatically,
and it reconciles with the fork point by construction. A divergence is **two or more** distinct
events at one serial `d`, and the chain **freezes** at the first fork, so there is a **single
divergence position**. `v_{d-1}` — the event at serial `d-1` — is therefore the **agreed common
ancestor**: it lies below the divergence, so every branch shares it — it is **attested-shared
state** ([§Extension Discipline](#extension-discipline)) — and it therefore **always lies on the
retained chain**. The repair attaches **at** `v_{d-1}` when the entity authored nothing at or beyond
`d`, and at its own later **tip** — above `v_{d-1}`, keeping those events — when it did: **either
way at or above `v_{d-1}`, never below it.** Each archival tail's root is a competing **child of
`v_{d-1}`** at serial `d`, off the retained chain — there may be several. When the entity did author
at or beyond `d` (its retained tip content, or a privileged tip —
`Evl`/`Rot`/`Del`/`Wit`/`Fld`/`Kil`/a prior repair — at or above the seal), attaching at `v_{d-1}`
would archive the entity's **own** events (its content, or **worse** a privileged tip, which rule 1
forbids archiving at all); it attaches at its retained **tip** instead (never in the locked
portion), so the repair's `previous` is that tip — at or above the seal.

The permission check is a single question about the **archival tails**: **does any of them contain a
privileged event?**

- **No — every archival tail is content** → **permitted.** A `Rec` at your last event archives them
  and advances forward. Your retained tail may carry your _own_ rotation — it is kept, not archived;
  only the archival tails are checked. An adversary holding your signing key can append only
  content, and a tier-3 `Rec` archives it — so **the recovery reserve defends the signing key.**
- **Yes — any privileged event sits in an archival tail** (a rotation, a `Evl`, a `Del`, a `Kil`, a
  `Wit`, a `Dec`, or a competing repair) → **forbidden → reincept** (for a **delegated** KEL — one
  chartered under an IEL delegation, whose doctrine is the IEL's — the delegator `Kil`s it instead).
  That event cannot be archived (rule 1), cannot be extended (rule 2 — it is not your branch), and
  forking past it is a second privileged branch (terminal). So **the recovery reserve does not
  defend the rotation key: a `Rot` in an archival tail is the point of no return** — the chain is
  the attacker's. (This check asks only about the branches you **archive**. A _winning_ terminal
  `Dec` sits on the **retained** branch and resolves by tier-rank, above — it never triggers this
  arm; a `Kil`, being non-terminal, is likewise retained in a `{Kil, content}` repair. A `Kil` or
  `Dec` reaches an _archival_ tail only alongside a **second** privileged branch — and then that
  second branch is the trigger.)

A divergence with two or more privileged branches is **irreconcilable**
([§Terminology](#terminology)) — terminal for _everyone_, not just the recovering party: any party
retains only its own branch, so a second privileged branch always lands in some party's archival
tail and no single branch can be chosen. This is a **node-agnostic, data-local** condition: a
branch-level fact any verifier computes by walking the branches it holds — the canonical branch plus
the competing branches **kept as evidence** (**keep-all-data** — a node retains competing branches
as non-canonical evidence rather than discarding them at the seal-cap; the witness beacon enumerates
the branch SAIDs so a one-branch holder can fetch and walk the rest). The federation **propagates**
the branches; it does not pronounce the verdict. A `{Rot, Rot}` collision is moreover a **proof of
rotation-reserve compromise** — two valid rotations both reveal the one rotation preimage in force
at `v_{d-1}`, which an honest, correctly-implemented holder never does; `{Evl, Evl}` is terminal for
the same branch-level reason but is **not** a rotation-reserve-compromise proof — its two governance
events reveal _different_ preimages and can arise from an honest partition (which is why high-volume
issuance and governance are serialized). Genuine reincept is an **irreconcilable** divergence — **≥
2 competing privileged branches** (`{Rot, Rot}`, `{Evl, Evl}`, any pair — **tier 2 or 3**),
equivalently a privileged event in an archival tail — which a one-branch holder detects once the
beacon delivers the second branch.

**Repair-and-evict is a single event.** When the divergence was caused by a member that must be
removed, the eviction **folds into the `Rpr`** as a roster `cut` rather than a following `Evl`, and
this **must** be atomic: were the eviction a later event, the still-rostered member could race a
fresh `Ixn` at the repaired tip → re-fork → repair again, indefinitely (a timing attack). So a user
IEL `Rpr` may carry a `roster` role restricted to a **required non-empty `cut` + an optional
`threshold` change — never an `add`, never a `threshold`-only change** (a `roster` role present
without a `cut` — or `threshold`-only, or `add`-bearing — is malformed → rejected; a bare threshold
change or a replacement `add` rides a later `Evl`, the chain being unfrozen after the repair). A
`Rpr` carrying **no roster role at all** is the normal benign repair — nothing to evict, nothing to
reject. The event is `Ror`-anchored exactly as a plain `Rpr` — no separate `Evl`, no mixed-kind
batch — so the member is gone the instant the fork resolves and no post-repair window exists (atomic
by construction, not merely one transaction). The cut is priced at the **outgoing** `t_recover` (the
pre-change gate — as a user `Evl` rides `t_govern`-of-outgoing, a `Rpr` cannot lower its own gate
before cutting), sound because `t_govern <= t_recover` is a hard floor
([§Structural authorization](#structural-authorization)); the post-cut roster is re-checked against
the threshold-vector bounds (a stranding or hostage cut is rejected, forcing a simultaneous
`threshold` drop the `Rpr` may carry, or reincept). The cut target is **operator-chosen** — the
fork-causer is the motivating case, not a structural check, since chain data cannot tell operator
from adversary. This is IEL-only (the KEL and SEL repairs carry no roster).

**Condemnation is by root — growth-proof, and a repair is accepted on arrival.** A repair's `fork`
names **one** losing branch's **root** — its first divergent event, a distinct child of the fork
point `v_{d-1}` **off** the retained chain, never its tip. It does **not** enumerate the losing
branches: an author holding several names any one (typically the only one), and **every other
competing branch — held, missed, or later-grown — closes without being named**, by the seal-cap +
deadness-descends (below); named and unnamed close identically, which is why a single committed root
suffices (the verifier still independently computes the competing set — validated, not trusted — so
no branch escapes by being unnamed). The root is a sibling at `v_{d-1}` — the chain freezes at the
first fork, so there is a single active divergence. The named root **condemns its entire subtree** —
every descendant is non-canonical forever. (Vocabulary: a repair **condemns** a losing branch by
naming its root — the mechanism; the condemned events are **dead** — the state; the branch as a
whole is **archived** non-canonical — the outcome. The three words name one operation.) So a repair
resolves more than the branches as they stood when it was authored: a losing branch that a
gossip-lagging node **grows after the repair** is dead **by descent**, with no follow-up repair
needed. A content branch the repair **did not name** (an additional held one, or one truly missed —
e.g. a fresh `Ixn` a lagging node accepted while reading the chain Active, the incoming repair then
landing as that `Ixn`'s sibling) does not freeze the chain either: the repair is **accepted**, the
unnamed branch's **first event** now sits below the seal the repair advanced — the seal-cap bars
**that first event** from being a canonical extension — and everything built on it is dead by
descent — **deadness descends: an event whose parent is dead is dead** (the per-event seal-cap bars
only a branch's _first_ event by its attach point; the descent rule kills the growth). Either way
the losing content rides the **forked chain** — the bounded dead region (the retention bound below)
— **propagated and retained**, never canonical, and **never orphan-dropped** (it is receipt-bearing
only where it was witnessed — a witnessed chain declines a losing content sibling under the majority
floor, so this is the direct-mode / residual population): the events stay kept per the retention
bound, and an honest author **re-issues its own benign content** forward on the repaired chain once
it catches up (adversarial dead content is simply non-canonical — nobody re-issues it). At most
**one** repair can resolve a content-only divergence; a _second_, competing repair is a `{Rec, Rec}`
/ `{Rpr, Rpr}` divergence — two privileged branches → `disputed`. An un-covered **privileged**
(non-content) branch is the other tier entirely: it is never archivable, so ≥ 2 privileged branches
→ **`disputed`** regardless of the seal — a privileged branch below a seal is **not** inert
(archiving it would bury a rotation).

**Termination.** Each dead lineage is **depth-capped**: at most `(MINIMUM_PAGE_SIZE − 1)/2 = 64`
events past the last seal (the seal-advance cap — a deeper event would itself have to be a
seal-advancer, privileged → `disputed` when competing), and root-condemnation makes one repair
growth-proof for the whole current fork within that cap. What closes the culprit's ability to mint a
**new** fork differs by layer. A **KEL `Rec` self-neutralizes the culprit**: it rotates the signing
**and** recovery key (both forward commitments — `rotationHash` and `recoveryHash` — are
re-committed, so both reserves persist and the next `Rec` is always authorable), locking out whoever
forked with the old key. An **IEL `Rpr` rotates no identity key** (an IEL is a threshold over member
KELs), so an **adversarial** re-forker is neutralized by the roster **`cut`** the `Rpr` carries (the
repair-and-evict fold above) — **provided the operator cuts the culprit**. The cut target is
operator-chosen (chain data cannot tell operator from adversary), so termination-by-cut assumes the
eviction removes the fork-causer; cutting the wrong member leaves the culprit able to re-fork. A
**SEL** re-forker is neutralized one layer up: a SEL is single-owner with no roster of its own, and
its repair cascade rides the owner IEL, so the owner IEL's cut is what evicts the forking member
(the cross-layer mechanics are the IEL / SEL doctrine —
[`primitives/data/event-logs/iel/`](primitives/data/event-logs/iel/), forthcoming). A **benign**
gossip-lag `Ixn` (an honest member's content on a lagging node) needs no cut: it is condemned or
seal-locked and re-issued, terminating as honest members catch up to the repaired tip. So
termination is **bounded**: each fork a sustained adversarial re-forker mints is capped at one
bounded fork window (≤ `(MINIMUM_PAGE_SIZE − 1)/2` deep), and once the neutralizing repair — the
rotation, or the cut — propagates, no new fork can be minted; a benign lag terminates as soon as its
node catches up. (The disruption — a bounded window plus an operator repair — is borne by the chain
and its operators; a signing-key re-forker itself spends nothing.) **Content-rail serialization is
an operator precondition** of the benign bound (absent it, honest content can **self-cascade** (one
honest content event, landing at a lagging node, forks a fresh divergence before the repair
propagates, and so on) — a liveness cost, not a safety one). On a **witnessed** chain the majority
floor narrows even the self-cascade to stall-and-re-issue — a competing content sibling never goes
live ([§Federation convergence](#federation-convergence)) — so the discipline is load-bearing
chiefly for **direct-mode / solo** chains.

**Finality is question-dependent.** A repair is **content-final the instant it seals**:
root-condemnation plus deadness-descends close every losing content branch, present _or_
later-grown. On the privileged side, two **distinct** properties are easy to conflate under one name
— keep them apart:

- **No-resurrection** (the property, **unconditional**): nothing archived is ever un-archived. It
  holds from the instant the repair lands — rule 1 plus the absence of any below-seal archival
  operation — and it holds **even under** the residual below.
- **Resolution-stability** (whether the repair's **reading stands**, **conditional**): the repaired
  prefix stays non-`disputed`. A consumer may treat it as stable once (a) the minting capability is
  **neutralized** (the KEL `Rec`'s rotation; the IEL `Rpr`'s cut — vacuous for a benign repair
  carrying no roster role, where (b) alone gates) **and** (b) the witness beacon shows no omitted
  privileged branch (the beacon is a _detection_ oracle — it raises confidence, it cannot certify
  absence). The residual is not only eclipse: a **historical rotation-reserve compromise** (an old
  rotation reserve, harvested at any time) can mint a privileged event on a dead or below-seal
  lineage years after beacon confirmation — the branch did not exist at confirmation, so the beacon
  was truthful, yet the reading flips to `disputed`. That flip stays permanently reachable, so
  resolution-stability is **stable barring that residual** — fail-secure (nothing archived is
  resurrected either way; the prefix terminalizes).

**Repair conditions** (data-driven, merge-layer-enforced, uniform across primitives):

- **Hard auth at landing.** The repair's signature / threshold check hard-fails on rejection — no
  soft-fail. (KEL `Rec`: dual-signature against the parent's rotation and recovery commitments. IEL
  / SEL `Rpr`: `t_recover` of the owner identity, anchored at tier 3.) Authority concurrence is a
  moment-in-time question: an event cannot land under-authorized and gather its authorization
  afterward.
- **The repair's `previous` is not in the locked portion.** It is at-or-after the tracked seal
  (`last_seal_advancing_event` — a seal-advancing event on a competing branch is never the lock; it
  is a privileged fork, read by the divergence rules). This restricts repairs to constructions that
  _could_ be an honest extension of the submitter's own tip — a party holding stale authority cannot
  construct a repair against an old position to rearrange the chain. When the repair's `previous` is
  the divergence ancestor `v_{d-1}` (structurally shared across all nodes), the repair validates
  uniformly regardless of which divergent contents each node received. A repair attaching at the
  submitter's own tail instead is validated against that retained tail plus the committed `fork`
  root (fetched via keep-all-data / the beacon) — both are cross-node-checkable, but only the
  `v_{d-1}` attach needs no fetch.

A **repair must commit the divergence it resolves — validated, not trusted.** Its `fork` names one
losing branch's root. **Two tests, easily conflated:** (i) a repair with **no `fork`** is
**malformed → rejected** — there is no divergence to resolve; (ii) a fork-bearing repair arriving at
a **lagging node** whose local tip looks non-divergent is **not** rejected for that — its named root
is fetched (keep-all-data / the beacon) and validated, and an as-yet-unfetchable root is condemned
**pending fetch** (fail-secure: a fetched root that proves privileged flips the reading to
`disputed`). No non-repair event ever carries `fork`. Condemnation is guarded twice:

- **No self-condemnation.** The named root must be a competing child of `v_{d-1}` **off** the
  retained chain. The verifier knows the retained chain (it walks the repair's `previous` back), so
  a root that lies on it — or `v_{d-1}` itself, which is on it — is **rejected**: a repair can never
  condemn its own retained branch, and no root's subtree includes the canonical chain. The verifier
  tests this over the **full** retained-chain walk, down to the fork point (reaching the pre-fork
  seal always suffices, at most one extra page): over a walk truncated at the divergence serial,
  `v_{d-1}` and every trunk ancestor would read as _off_ the retained chain, letting a root condemn
  a subtree containing the whole canonical chain (and the repair itself) — censorship, reachable by
  any tier-3 holder including a buggy client. Condemnation is safe because each event has one
  `previous`, so a genuinely off-chain root's subtree is disjoint from the retained chain — a
  property the verifier can test only over the full-span walk.
- **No buried rotation.** The condemned subtree must be **content-only**: the verifier walks it, and
  a **privileged** event in it means ≥ 2 privileged branches at or beyond the divergent serial →
  **`disputed`**, never archived. Nor does the verifier trust the `fork` as proof there are **no**
  privileged branches: it **independently** walks every branch off the retained walkback it holds
  (or the beacon enumerates) and **rejects the repair if any such branch carries a privileged
  event** — privileged branches are always retained (keep-all-data), so a `Rot` cannot be hidden by
  leaving its branch unnamed and letting the repair seal past it. (The walk-independent closer:
  every privileged KEL event is a seal-advancer, so a buried rotation is a competing seal — a spine
  fork → `disputed` independent of any walk bound.) A repair rejected **here** — one that passed
  hard auth (it revealed the recovery reserve, so it is a real privileged event) and failed only
  this content-only guard — is **retained as a competing privileged branch and counted**.
  Retain-and-count is the only convergent semantics **because this rejection is branch-dependent**:
  the content-only guard walks the branches a node holds, so a node that dropped it would read the
  prefix differently from one that counted it — the reading would split permanently. The contrast is
  exact: a repair that fails hard auth, carries no `fork`, is malformed, or names a self-condemning
  root is **dropped, never counted** — those rejections are **deterministic from data every node
  holds uniformly** (the repair event itself plus the retained chain), so every node drops
  identically and convergence is preserved; junk submissions cannot terminalize a prefix. So a
  reserve-revealing repair authored against a fork that turns out to hold a privileged branch
  **permanently terminalizes the prefix** → `disputed` — the fail-secure outcome of revealing tier-3
  material into a contested window.

Root-condemnation reaches no _live_ state — it marks a subtree dead, never extends or revives an
event. There is **no below-seal archival operation**, and the seal-cap stays unconditional. A race
whose retained branch's **tip** is a **terminal `Dec`** — an identity/SEL decommission, whatever
precedes it on that branch (a bare `Dec`, or a `[…, Rot, Dec]` run) — needs no repair: this is the
**tier-rank** resolution (the freeze rule's one carve-out). The terminal admits no successor to
carry a repair, so it outranks the losing content outright — the chain decommissions on the `Dec`,
the content is archived non-canonical (retained as fork evidence per the ≥ 2-per-position bound,
like any archived content — droppable only beyond that evidence set), and the resulting reading is
the ordinary **Decommissioned** one (the effective SAID is the `Dec`'s SAID — the fork is resolved,
so no fork digest applies). The rule exists because a `Dec` **admits no successor** — you cannot
author an `Rpr` after it to archive the content the normal way — so without it a benign decommission
that collided with a stray content event would be forced to reincept; tier-rank keeps the `Dec`
clean and the content **non-canonical**. It only ever lets **higher** authority (the reserve-backed
`Dec`) override **lower** (T1 content); a **second privileged** branch (`{Dec, Rot}` / `{Dec, Dec}`,
or the content branch having sealed a competing `Fld`/`Evl`) is not this case — it is two privileged
branches → **`disputed`**. To resolve a content fork _and_ decommission deliberately, repair first
(the `Rpr` carries the `fork`), then the `Dec` lands cleanly on the repaired chain. (A `Kil` is
**not** terminal — it seals a kill on a _target_, not its host IEL — so a `{Kil, content}` fork
takes the ordinary recoverable path: an `Rpr` retains the `Kil` and archives the content, exactly
like `{Evl, content}`.)

**Cross-node races converge data-locally.** Two nodes can each accept a competing event extending
`v_{d-1}` via independent clean linear landings; gossip then delivers each to the other node, where
the late arrival **lands as a competing event at serial `d`** — a fork. A seal-advancer among the
siblings does **not** win by arriving first: a seal-advancing event that is **itself one of the
competing siblings at `d`** never becomes the tracked seal (it is a privileged fork branch —
[§Terminology](#terminology)), so the tracked seal stays below `d` and the fork is **live**. (This
is distinct from a seal-advancer that extends one branch **above** the fork: that one advances the
seal and buries a content loser, resolving the fork — the burying case above.) Both arrival orders
therefore converge to the same reading, **Divergent** (identical events, identical state — the
reading is the walk's, not the arrival order's). What it resolves to follows the tier rules above:
**≤ 1 privileged branch is reconcilable** — a `Rec`/`Rpr` extends the privileged (or the entity's)
branch and archives the rest, so a mixed `{Rot, Ixn}` recovers by extending the `Rot`; **≥ 2
privileged branches are irreconcilable → `disputed`**. So each node ends up holding both branches
and **detects the divergence by a data-local walk**. The beacon's divergent witness receipts (see
[§Federation convergence](#federation-convergence)) propagate the competing branch SAIDs to a node
that has not yet received the events, but the verdict is the node's own. This is the deliberate
trade-off: relaxing the seal bound to admit a competing privileged event as a _canonical_ extension
at a sealed serial would re-open the stale-authority kill-switch surface, so the bound stays
unconditional — the chain does not extend onto the competing branch, it only retains it as the
evidence a data-local detection needs.

**Retention is bounded — keep-all-data is not keep-everything.** **Archived** is a _status_ (a
losing event is non-canonical, permanently), not a storage guarantee — a node need only **retain** a
bounded set of the archived events as evidence, the rest **droppable**. A privileged branch is
retained to **≥ 2 per spine position**: a spent preimage can sign unbounded distinct events at an
old position, but two competing privileged branches already prove the prefix terminal, so a node
retains the second and stops. Content breadth is bounded the same way: nodes keep **≥ 2 competing
events per position** as fork evidence and drop the rest — a signing-key re-forker can author more
siblings, but they sit beyond the retained set: droppable, a bounded query surface, never an
unbounded fork. On top of retention sits the **one-content-sibling witnessing rule**: a selected
witness signs the **first** structurally-valid **content** sibling at a position and **declines
every later one** — while **privileged siblings are witnessed up to two per position** (two
both-witnessed siblings are the `disputed` proof — dispute evidence, competing seals form a spine
fork, [§Forks are seal-bounded](#forks-are-seal-bounded) — and further ones are declined); the
**single repair** that lands on a content-only divergence is simply the first privileged sibling at
that position. Deterministic witness co-location fixes the witness _set_, not arrival order — with
the majority floor ([§Federation convergence](#federation-convergence)) at most one content sibling
per position is ever witnessed, arrival order deciding only which — and the retention bound rests on
retention plus kind-awareness, not on which two events arrive first; _which_ two are kept is
immaterial: any two competing events prove the fork; the bound requires keeping at least two, not a
particular two. The canonical run's bodies are kept and retrievable by prefix (the flat query
returns them); a repair's `fork` root is committed, the condemned branch being its root's
**subtree** (every dead event's ancestry passes through the named root or a below-seal first event);
only the truly **uncommitted** below-seal content flood — condemned by no repair's `fork` and beyond
the ≥ 2-per-position evidence set — is droppable, because detection is **content-independent**: a
privileged event re-validates against the prior seal's key state (reached via `previousSeal` on the
retained spine) plus its own committed fields, never against this chain's below-seal content. So the
evidence a data-local detection needs is bounded and always retained; dropping the rest is a
storage/audit tuning knob, not a detection gap. The chain's **state** — Active / forked / disputed —
is determined by the walk over the canonical chain plus the retained set; the effective SAID is then
the tip's real SAID when a single **live** tip is held, or a real digest over the **live tips** it
holds when several are — a **settled** branch (one a repair condemned, or a content sibling buried
below the seal) drops out, and the `forked` / `disputed` reading is the walk's, separate from the
value — see [§Effective-SAID comparison](#effective-said-comparison).

**Pre-seal verifiability.** A seal is **clean** while no competing privileged branch forks
at-or-below it; the **last clean seal** is the chain's most recent such seal-advancing event — on a
chain with no below-seal privileged fork (the overwhelmingly common case) it is simply
`last_seal_advancing_event`, the tracked seal. Everything at-or-below the **last clean seal** is
final in the sense that matters — **immutable** (no event rewrites it) and **canonical** (no content
divergence targets it) — and consumers verify against it indefinitely. The one thing that can move
this boundary is a **below-seal privileged fork**: it un-cleans the seal and retreats the
last-clean-seal beneath it (resolution-stability, above), flipping the reading to `disputed` without
un-archiving anything — so a position's finality here is against later **content** divergence, with
the privileged residual the sole mover. Anchors hosted at-or-below the last clean seal stay
anchored; documents issued under that state stay verifiable; audit queries on that portion return
truthful answers. Two distinct degradations could threaten sealed state, and only one of them is
possible at all: sealed events are never _rewritten_ — immutability is unconditional — but a
**privileged** branch forking below the tracked seal is a spine fork that flips the prefix's
**reading** to `disputed` (a below-seal privileged straggler is never inert); the seal it forks
under is no longer clean, and the permanence claims retreat to the last clean seal beneath the fork.
Above-seal events carry tier-1-only auth — structurally indistinguishable from signing-key-only
adversary capture — and become durable only when a later seal-advancing event lands cleanly past
them. The clean seal is the boundary the protocol can defend.

A **reconcilable** divergence resolves by a repair that seals its surviving branch, so that branch's
above-seal anchors become durable; an **irreconcilable** divergence never seals, so its post-seal
window grounds no new trust. The divergence's reach is bounded to that window — it does not
retroactively alter the below-seal portion, whose structural finality is unchanged. That finality is
**immutability, not a warrant of honest authorship**: an attacker already holding current keys can
clean-rotate and seal its own content below the seal — the current-state-compromise limit (below),
which a later divergence neither creates nor cures. Whether the **identity** survives a member KEL
going terminal is decided one layer up, by IEL threshold redundancy and a `Evl` eviction, not by
salvaging the suspect chain's own tail.

**IEL distrust is forward-only.** An IEL event is trusted only when a threshold of members anchored
it, so a single compromised member KEL cannot reach any threshold **greater than 1** on its own. (At
`t_use = 1` — legal at any roster size — or on a singleton, one member _can_ act alone; that is
precisely the tier-1 content compromise a repair recovers from — recoverable, not inert.) The quorum
withholds trust from a compromised member by not co-anchoring its acts and by evicting it with a
`Evl`; both are forward acts. There is **no retroactive per-event distrust** — a quorum that could
reach back and un-trust events it had already authorized would itself be a stale-state kill switch,
the very surface this section closes. An event the quorum co-signed stands even if a co-signer is
later found compromised; remediation is forward (revoke what the event granted, evict the member),
never retroactive invalidation. A member KEL that cannot be resolved at its own layer — an
attacker's clean multi-rotation leaves no divergence to contest — does not propagate to the
identity: the identity evicts the member and continues on its quorum.

#### Kills are sealed; validity bounds are contiguous

A **kill** — revoke, close, rescind, decommission — is **always sealed on arrival**. It is anchored
in a dedicated sealed kill-anchor (the IEL `Kil`, tier 2; an identity-kill rides a tier-3 terminal),
distinct from the roster-changing `Evl`. Because a sealed kill-anchor is privileged and
terminal-on-divergence, the kill can **never** be archived by a repair (no silent un-revoke), and
there is no unsealed window to undo. A kill is **monotone**: restoring a killed thing is **never** a
retraction — the party reincepts under a **new prefix** and is granted or issued afresh. A re-grant
of the _same_ killed prefix does not restore it; its kill locus permanently caps that prefix.

A **validity bound** (a rescission's bound, or a compromise rewind) removes a **contiguous suffix**
of a chain. By chain linearity every event builds on the prior, so only a contiguous tail can be
invalidated — never a non-contiguous subset. **Nothing past the bound is honored — grants _and_
kills alike**; there is no per-kind exception across a validity bound (honoring an event past the
bound would trust an un-anchored, invalidated event). In a compromise the invalidated suffix is
exactly the attacker's contiguous tail from the divergence point — legitimate and attacker events
never interleave into a subset worth keeping. A bound is **set once** at the rescission `Dec`: it
can't move later (no un-kill) nor be tightened earlier; a sealed kill is never retracted. Recovery
from a mis-set bound is operational (reincept and re-grant / reissue), not a rewind.

#### Inception tiers

Inception tier follows what the inception establishes:

- **KEL `Icp`** — tier 1. The root is self-authorizing; there is no chain above it.
- **IEL `Icp`** — tier 2. It establishes governance (a roster + threshold vector) — a genuine
  state-establishment.
- **SEL `Icp`** — tier 1. It establishes single-owner data, not governance, and an IEL `Ixn` anchors
  it. The `Icp` carries **no `pin`** (it must stay recomputable for lookup), so the SEL's first
  down-pin rides a **serial-1 `Pin`** batched with the `Icp`, uniformly for every SEL. A
  **credential SEL**'s `data` **is** the credential's SAID (the whole reference; the `Icp` carries
  no manifest); a **lookup SEL**'s `data` is the recompute input the verifier blind-recomputes the
  prefix from (e.g. a rescinded prefix), and its rescission kill rides a terminal `Dec` sealed by an
  IEL `Kil`@`delegate`.

A compromised tier-1 signing key can already issue content in your name, so letting it also create a
SEL adds no blast radius — tier-1 inception is sound. Issuing a credential is tier 1 because a
credential is **content** (one bounded, revocable claim); an authority-grant (a delegation, `Del`)
is tier 2 because it **expands who may act with your authority** going forward (an ongoing forgery,
not one revocable assertion).

#### Decommission and clean retirement

When a terminal `Dec` lands cleanly on a linear chain, it is a clean-retirement signal — no
compromise indicated, pre-`Dec` content keeps its meaning. Once it lands the chain is Decommissioned
and accepts nothing further. A `Dec` is privileged, so a `Dec` that would land in a divergent set is
subject to the divergence rules above (a `{Dec, content}` collision is recoverable by keeping the
`Dec` — the single privileged branch wins on tier-rank, the content is archived as non-canonical,
and **no repair is authored**: the terminal admits no successor to carry one, and none is needed
since the chain is decommissioning. A `{Dec, Dec}` or `{Dec, Rot}` collision is two privileged
branches → terminal). An IEL `Dec` freezes all the identity's SELs.

A submitter who detects compromise pre-emptively has no dedicated "compromise signal" event:
available paths are to rotate the compromised key out (chain stays alive), to `Dec` (clean
retirement — semantically loose when compromise is the cause), or to attest out-of-band under a
separate KEL. This trade-off is accepted; the chain layer has no identity concept, so a
"terminate-with-prejudice" primitive justified by submitter intent would be structurally incoherent.

#### Limit of the doctrine — current-state compromise

The doctrine closes attacks rooted in **past** state. It does **not** defend against compromise of
**current** state. An adversary holding sufficient currently-controlling authority — current KEL
rotation (+ recovery) preimages, or `t_govern`-many current IEL members across distinct custody — is
the chain's current state by every protocol-observable measure, and can rotate authority away and
lock the prior operator out. There is no protocol mechanism to distinguish "legitimately current"
from "compromise-acquired-current"; there is only a narrow detect-and-respond window before the
adversary's rotation lands.

**Defense is layered** — the layers compose; none is load-bearing alone:

- **KEL dual-signature** on `Ror` / `Rec` / `Wit` / `Dec` blocks signing- and rotation-key
  compromise regardless of where the recovery key is custodied. A single-device deployment is
  first-class.
- **IEL threshold composition** (high thresholds, `M > N` redundancy across **distinct custody
  domains**) handles total device compromise: evict the device via a `Evl`; surviving members keep
  the threshold and the identity stays alive. Two prefixes under one operator's hardware compose to
  effective threshold 1 against an adversary who breaches that hardware — composition must span
  genuine custody separation.
- **Federation witnessing** propagates a partition-or-no-partition rotation-tier race so the
  divergence is **detectable**: competing events at one position accumulate receipts that enumerate
  the branches (the beacon — see [§Federation convergence](#federation-convergence)), and any
  verifier holding both branches reads the disagreement by a **data-local walk** — the data decides,
  witnessing only delivers the branches. The rotation-tier-compromise-plus-partition case is the
  structurally unavoidable CAP failure mode — VDTI guarantees the divergence is detected
  post-resolution, not prevented.
- **Operational hardening** — monitoring for unexpected governance/rotation events, fast
  detect-to-respond, custody separation, and abandon-and-reincept as the last resort.

**Adversary patience.** A strategic adversary accumulates authority quietly (compromise key 1, wait,
key 2, …) and acts only on a satisfying combination, so the response window is bounded by the
adversary's timeline, not the operator's first detection. Policy design is therefore a budget
against patience: high thresholds + custody separation raise the accumulation cost; `M > N`
redundancy tolerates loss of `M − N` members (evict via `Evl`, no reincept); hierarchical scope
partitioning bounds blast radius. A chain whose roster permits no eviction path — a threshold equal
to `|roster|` — loses to the first compromise that reaches the threshold and forces a reincept under
a new prefix, which propagates to every consumer. Design rosters to **survive compromise instead of
catastrophically reincepting**; treat reincept as the last resort.

**Cascade-reincept honesty.** Reincept is needed only when the primitive itself is **disputed** (a
data-local verdict — [§Terminology](#terminology)), not when a referenced primitive is. Dependent
chains whose bindings reach at-or-below-seal state stay authorized.

- **A disputed IEL** → every SEL bound to it that would forward-extend its binding must reincept
  under a new prefix.
- **A disputed SEL** → the SEL is dead in place; nothing downstream cascades.
- **A disputed KEL** → dependents reincept only when the disputed KEL actually anchored their events
  **and** the resolving threshold lacks redundancy. A `M > N` roster absorbs a single member's
  dispute by evicting it via `Evl`. The expensive case is a dispute on an IEL at the root of a
  dependency tree — so partition identity hierarchies to bound any single dispute's blast radius.

---

## Part 2: Cross-Cutting Doctrines

Properties that hold across all primitives and bind them into a coherent protocol. They constrain
how the protocol composes (across nodes, across kinds, across time) rather than asserting an
authorization rule; the Part 1 rules lean on them for their cryptographic-soundness argument.

### Ordering Without Timestamps

Chain events carry **no wall-clock timestamp field**. Ordering is by serial + cryptographic chain
linkage (`previous` SAID). Wall-clock timestamps on chain events would not be cryptographically
meaningful: an author can write any timestamp, the protocol can only verify an event was _observed_
at-or-before now, and clock drift across nodes precludes timestamps as a cross-node ordering signal.
Cryptographically verifiable ordering already exists via serials and linkage; adding timestamps
would be redundant for ordering and unsound for tiebreaking — an untrusted input as a protocol
decision input, which is exactly the backdate surface to avoid.

Where timestamps appear, they serve narrow roles within a **single party's reference frame** —
peer-to-peer signed requests (a Unix timestamp + nonce checked against the receiver's own clock),
feature-level fields on the content a chain event anchors (a credential's issued/expiry times,
advisory and checked by the verifier against its own clock). None influence chain ordering.

**Federation consensus clock (the one exception).** The federation publishes a coarse,
consensus-attested clock **for freshness / staleness detection only** — the `clock` role on each
federation governance event (`Fcp` / `Wit` / `Dec`'s `manifest`, an inline timestamp value, one per
governance change), sealed and monotonic, **not** a field on any chain event. It bounds each witness
key's validity window so a closed-window key can only stamp old receipts, which makes a backdated
dormant-chain forgery read **stale** — detectable, fail-secure. It **defeats** backdating rather
than inviting it, and intra-chain ordering stays pin-based, so it honors this rule's intent; the
bytes live in a SAD, so the primitives stay timestamp-free. See
[§Federation convergence](#federation-convergence) and [`federation/`](federation/) _(forthcoming)_.

### Federation Convergence

VDTI depends on **eventual cross-node convergence**: gossip propagation paired with deterministic
effective-SAID computation ensures every chain resolves to the same semantic state on every node
that holds the same events. Concurrent privileged-event races between nodes converge
**data-locally** — keep-all-data retains a competing branch as evidence, so a node ends up holding
both branches and detects the divergence by walking them. The federation's witness receipts
**propagate** the competing branches to nodes that have not yet received the events; they do not
pronounce the verdict.

The federation is **a restricted IEL rooted at an `Fcp` inception marker** — there is no separate
consensus algorithm and no central state machine. Its roster is **witness KELs directly**; its kind
set is restricted to `Fcp` / `Wit` / `Dec` (no content, so it never has a **reconcilable** fork and
needs no `Rpr`; a competing-privileged divergence — `{Wit, Wit}` / `{Dec, Dec}` under a partition —
is still possible but **terminal** (`disputed`), which is why a federation runs a hard
recoverability ceiling and `|roster| >= 3` with serialized governance; no delegation, since trust is
per-federation and non-transitive). Its roster changes ride the `Wit`'s **roster delta**, whose
**`add` is a single prefix** — one witness added per `Wit`, the `Fcp` inception alone standing up
the founding roster wholesale (`cut` stays a list: cuts remove synced witnesses, so emergency
multi-eviction is unaffected — evict-and-replace is `cut: [..], add: one`). Standing up a witness is
deliberate infrastructure, never bulk — and structurally, a governance transition then introduces at
most **one** unsynced witness, which alone cannot reach a majority `threshold` against synced
co-selectees that decline by first-seen — so the benign two-fresh-witnesses straddle collapses into
the priced witness-compromise residual (a fresh sibling needs a byzantine synced co-signer). Its
trust root is a **config-pinned federation prefix** (a compile-time default with a runtime override)
— the prefix derives from the whole inception content `(roster, threshold, nonce)`, so it is a
binding commitment to the exact founder set. There is **no self-witnessing carve-out** — the `Fcp`
is a structural marker the verifier dispatches on, not a trust shortcut: authorization is ordinary
member-anchoring (the founders' `Rot`s anchor the federation `Fcp`), trust roots in the config-pin,
and everything post-genesis is witnessed normally.

The convergence model has three components:

- **Gossip propagates events** — anti-entropy plus submission-time fan-out push new events to all
  nodes within a bounded window (the bound is operational; the doctrine asserts only the eventual
  property).
- **Semantic state is a function of the events** — each node computes a chain's state (Active /
  Divergent / Decommissioned, with which events at which serials) deterministically from the events
  it holds, **deriving the seal from those events**
  ([§Divergence and repair](#divergence-and-repair)), so **identical event sets yield identical
  state** — arrival order does not enter.
- **Effective-SAID determinism** — the effective SAID is a deterministic function of the events a
  node holds: a hash over the **live branch tips it holds** — the canonical tip and any unresolved
  competing branch, a settled branch dropping out (a single live tip yields that tip's SAID).
  Guaranteed witnessed propagation means all nodes eventually hold the same live tips and compute
  the **same value**; until they do, their differing digests are exactly the anti-entropy signal
  that drives the exchange — fail-secure under partition, since nodes holding different live-tip
  sets never falsely agree (see [§Effective-SAID comparison](#effective-said-comparison)).

**Content-fork prevention — the majority floor.** The witness-config every federated chain carries
(`{ threshold, signers }` — the `witnesses` role) sits above a structural **majority floor:
`threshold > signers/2`**, a strict majority of the selected witnesses (a sub-majority config is
rejected as un-usable — its `witnessed` signal would no longer mean per-position exclusivity;
`threshold = 1` is usable only at `signers = 1`, the lone-witness carve-out). Witness selection is
deterministic by position, so any two threshold-quorums at one `(prefix, serial)` share at least
`2·threshold − signers >= 1` witnesses — and an honest witness signs at most **one content sibling
per position** (the ladder below) — so **two competing content events can never both be witnessed**:
a content fork on a witnessed chain is **prevented from forming**, not merely detected.
Manufacturing one costs owning the whole quorum intersection — the **fork-cost
`2·threshold − signers`**, a priced, tunable security parameter, not a free consequence of the
network (the dial trades one-for-one against receipt redundancy: `fork-cost = threshold − slack`
where `slack = signers − threshold`, so at `threshold = signers` fork resistance is maximal but one
unreachable witness stalls the position). Paying fork-cost also means exposure: two receipts by one
witness over two distinct **content** `witnessed_said`s at one position (or a third distinct
privileged sibling past the two-per-position cap) are cryptographic proof of misbehavior —
forensics, then eviction. The floor holds at KEL positions **and user-IEL positions**: a user IEL's
content events must reach a majority quorum at their own `(IEL prefix, serial)` — a fork-prevention
gate **alongside** their anchor-based authorization, closing the two-disjoint-member-sub-quorums
content fork — while the **federation IEL is exempt** (it authors no content; its every fork is
privileged → `disputed`), and a SEL rides the cross-layer theorem (a valid SEL fork implies an IEL
fork beneath it, so closing IEL content forks closes SEL content forks). What survives the floor is
the **residual**: direct-mode / no-witness chains, a witness compromise owning the intersection, and
— rarely — a roster-delta straddle (two full quorums under disjoint contexts), which under the
propagation premise below requires the new selectees cut off from the already-propagated old quorum
— an entrance to the partition/eclipse family, not a freestanding race. In the residual, the
machinery of [§Divergence and repair](#divergence-and-repair) runs unchanged.

**Witnessing is kind-scoped — the ladder; the data decides** (witnesses are reporters, not
deciders): a selected witness signs the **first** structurally-valid **content** event it sees at a
`(prefix, serial)` and **declines any later content sibling** there (first-seen, one per serial); it
signs up to **two** distinct structurally-valid **privileged** siblings per position and declines
further ones — two both-witnessed privileged siblings ARE the `disputed` proof (a third adds no
evidence, and a spent preimage can mint unbounded distinct siblings, so the witnessing duty caps
where the proof completes). On a content-only divergence the first privileged sibling at the
position is exactly the **single resolving repair** — a repair is privileged, needing no separate
clause — and a second competing repair is the proving pair `{Rec, Rec}` → `disputed`. Receipts are
indexed at the chain position `(prefix, serial)` rather than at event SAID, so competing receipts at
one position **enumerate the branches** — the **beacon**. Selection is a function of the position
over the current roster membership only — never the event's bytes or its pin, so an adversary cannot
mint sibling-specific witness sets — and the selected witnesses sub-gossip the event among
themselves, so a **privileged** event that reaches any one honest selected witness reaches
threshold: there is no stable "witnessed but sub-threshold" state for a real **privileged** event. A
losing **content** sibling, by contrast, is deliberately, permanently sub-threshold under the floor.
How a node acts on the signal splits by **provenance**: when it **holds and re-validates** two or
more privileged branches it reads **disputed** directly from the data, threshold-independent; when
it holds only a **receipt** for a **privileged** event it has not yet fetched, it waits for the
**witness threshold** before treating the signal as a real divergence — below threshold, a rogue's
receipt on a fake event is inert (the verifier independently re-checks validity; the database cannot
be trusted). For **content** the signal is a **sub-threshold competing receipt set** at a position —
a losing content sibling never reaches threshold, so waiting for threshold on it would wait forever;
the receipts enumerate, the node fetches the event (push / beacon), and the data-local walk decides
(threshold authenticates only the winning branch). Receipts tell a node it is _forked_; only the
data-local walk tells it _disputed_. This makes divergence **locally determinable** on every node,
without watcher infrastructure. **All inter-node mesh traffic is encrypted** (ML-KEM-1024 +
AES-256-GCM) — the receipts and the events they propagate alike — and the mesh is the federation
roster, so mesh contents stay within the federation.

**The propagation premise and the split stall.** Prevention's success rate — never its safety —
rests on prompt roster-wide propagation once an event is witnessed in full (the push-gossip mesh): a
roster member ordinarily sees a completed quorum before any later sibling arrives, which is what
arms the first-seen declines. A fork that forms despite the premise lands in freeze → repair;
nothing false becomes canonical on any node. First-seen-one-per-serial partitions the receipts at a
contested position (`a + b <= signers`); when neither content sibling reaches majority (an
even-`signers` tie, abstentions, or a partition) the **position stalls, fail-secure** — signed
witnesses cannot switch, so a minority partition **stalls, never forks** (consistency over
availability). The **exit is the repair**: a `Rec` / `Rpr` at the position is privileged — the first
privileged sibling there, signed by every selected witness under the two-per-position cap, including
those that signed a content sibling — and reaches majority; the stalled honest content re-issues
forward. Odd `signers` avoids the pure tie (operator guidance: with every selected witness voting,
an odd set always yields a strict majority for one sibling).

Receipts are evaluated **as-of the event's federation context** — a receipt counts iff its signer is
among the witnesses **selected** for the position,
`select(prefix, serial, roster(F @ federationPin), signers)`, the deterministic selection derived
over the as-of roster — never mere roster membership (the fork-cost intersection is over the
selection, so the counting predicate must be selection-scoped too), and never at the federation's
current tip — so an event stays witnessed forever (no re-witnessing of history), and a since-removed
witness's established receipts keep counting. A witness's receipting key-window is bounded by the
**federation clock** (above): a cut or rotated-out witness earns no new pinned window, and a witness
**wipes superseded private keys on rotation and removal** (forward secrecy; durability is unaffected
because old receipts verify with public keys). Together — wipe plus the clock — these close the
harvested-old-key forgery on a dormant chain (it reads stale → detectable). Witness rotation is
legal **only** as a synchronized federation `Wit` (the witness's KEL `Wit` is the rotation and
anchors the federation IEL `Wit`); an off-ceremony rotation produces receipts the federation does
not honor.

**Detection is eventual, not at-decision-time.** Every detection guarantee assumes the consumer can
reach enough honest witnesses / converged gossip to see the competing branch. A consumer eclipsed to
a malicious subset, or reading during an incomplete heal, sees the detection later — so a binding
made in that window can transiently trust the wrong branch. This is the standard cost of a detection
model; the multi-source freshness bar shrinks the window but does not close it, and recovery is
operational (re-verify before binding; reincept on a surfaced divergence). **Single-node deployments
forfeit convergence** and the DB-tampering-surfaces-as-divergence property — distinct from a
single-_device_ identity, which is first-class and still participates in a federation; the caveat is
a federation-less _node_, not a one-device wallet.

Full mechanics — receipt encoding, witness selection, the clock's tolerance band and upper sanity
bound — are federation doctrine ([`federation/`](federation/) — _forthcoming_).

### Extension Discipline

The protocol cannot prevent a currently-authorized party from chaining a new event onto any existing
event — `previous` validates against the structural parent, not "who authored the parent." Operator
**design discipline** closes the implicit-endorsement gap: extending an event is semantically
endorsing it (the new signed event carries the parent's content forward), so a submitter extends
**only**:

- **Their own previously-signed events.**
- **Attested-shared state** — the divergence ancestor `v_{d-1}` (the unique shared parent of all
  events at `v_d`, which every node accepts), or a deterministic dedupe-equivalent inception (any
  party's inception for the same derivation inputs produces the same SAID, so extending it is
  extending shared state).

A submitter never points `previous` at an adversary event. If an adversary captures key material and
extends the chain linearly past the legitimate party's last attested event, the legitimate party's
structurally available moves all extend their own last attested event (`v_{N-1}`): a privileged
event there would create a divergence (surfaced via witness receipts and resolved by tier), and a
repair there is available only if the adversary's extension did not advance the seal past `v_{N-1}`.
Once the adversary has rotated authority forward past `v_{N-1}`, no protocol recourse remains and
the response is reincept. The discipline is structurally identical across primitives; the shapes of
"own tip" and "attested-shared state" instantiate per primitive, but the principle holds without
exception.

---

## Part 3: Verification Mechanics

The implementation invariants that make Part 1 enforceable. Verification and use happen in the same
pass, under the same lock, against the same trusted context — this is how "the database cannot be
trusted" becomes a safe operation.

### Verification tokens as proof of verification

Functions that consume chain data accept a verification token (`&KelVerification` /
`&IelVerification` / `&SelVerification`). Holding the token proves the chain was verified; token
fields are private with no public constructor, so the only way to obtain one is through the
corresponding verifier. A token exposes per-primitive specifics plus the cross-cutting signals: the
structural-validity result, which registered SAIDs were found anchored on the canonical branch,
per-position divergence (carrying the competing SAIDs when true), and witnessing status (`witnessed`
/ `minority_dissent`).

**Token reuse is transitive.** A cached token's reusability gates on the effective-SAID of **every**
chain it transitively leans on — the KEL(s) beneath an IEL, the IEL beneath a SEL, every delegator
above it, and the federation that witnesses it — not on that one chain alone. A lower-layer repair
that breaks an upper event must be visible to a holder of the upper token, so a loss-of-trust
decision confirms each dependency's effective-SAID **multi-source** (a witness-signed effective-SAID
is multi-source by construction; an unwitnessed chain degrades to single-source, flagged). "Is this
chain forked / disputed?" is itself a loss-of-trust question — a one-branch holder computes a
normal-looking tip and never sees a fork, so divergence detection is in the multi-source bucket.

### Walk semantics

Every walk is preloaded with the SAIDs the caller cares about. The **baseline is a full walk** that
returns which sought SAIDs were found and the chain's divergence status. Whether the tip must be
reached depends on the question: _"is the chain valid?"_ walks to tip; _"is this SAID anchored?"_
may end once all sought digests are found, **provided the chain is non-divergent up to that point**.
A `search_only` walk ends when all digests are found and the token points at the reached position; a
`resume` takes that token forward to a later tip. **`resume` must re-run the to-tip negative
checks** (revocation / rescission / divergence) against the new tip whenever any transitively-pinned
chain moves — an incremental resume that only extended chain state would advance the token past a
revocation without surfacing it.

Chain verification **streams** events page by page rather than loading whole chains; the verifier
walks in generations (all events at a serial), and a generation spanning a page boundary re-fetches
rather than being processed half-observed.

### Structural problems error; everything else is reported

A **structural** problem — an invalid chain, a divergence, broken linkage, tamper, a SAID or prefix
mismatch — produces a descriptive **error**. A **non-structural** condition — a sought SAID not
anchored, a document's policy unsatisfied, an expired credential — is returned as **contextual
information** in the result, never raised. Callers must distinguish "the data is broken" from "the
answer is no"; conflating them is a correctness and fail-secure hazard. (Policy lives in the
document layer, so there is no chain-layer "policy satisfaction" — document-policy evaluation is the
policy layer's concern, [`primitives/policy/evaluation.md`](primitives/policy/evaluation.md). The
chain verifier reports structural validity and anchoring; the policy layer composes those token
answers.)

The verifier and the merge layer share the same walk but compose its result differently: the
**verifier** reads through pathology to expose it (it must surface the at-or-below-seal portion even
on a chain with above-seal divergence), reserving hard-fail for structural-integrity violations; the
**merge layer** gates writes — it runs the same verifier under a lock and rejects a submission whose
post-batch walk reports a structural failure, with no per-kind carve-out.

### Negative checks are positive lookups

"Is X rescinded / revoked / closed?" is answered by recomputing **one derived lookup-SEL address**
`derive(owner, topic, data)` and reading it (present → yes, O(1)), **never** by scanning a chain or
list for the absence of a kill. A scan-for-absence forces deep-inspecting everything it touches; the
positive lookup is O(1) and tamper-evident. This is why rescission and closure are lookup-SELs
rather than list-walks. Logs are referenced **by prefix**; a SAID is an integrity commitment, not a
global lookup key — there is no SAID→event index — so a SAID harvested off a public chain does not
invert to a private chain's prefix **for any party outside the federation mesh** (the witness beacon
pairs a prefix with its `said(Icp)`, so a federation witness can correlate — a standing
confidentiality property of mesh membership; see
[§Federation convergence](#federation-convergence)). A prefix-bearing request likewise keeps the
prefix out of the **address** — it rides in the request **body** (a safe, body-carrying read like
HTTP QUERY), never the request line or query string, since a URL-encoded prefix leaks into common
access and proxy logs that aren't otherwise privacy-controlled.

### Merge verification and advisory locking

All verify-then-write paths hold a **database advisory lock** for the duration of both verification
and write: the submit handler verifies the entire existing chain under the lock, obtains a trusted
token, verifies the incoming events against that token's data, and writes — never re-querying the
database between verification and use. The verifier supports **registering SAIDs of interest before
the walk** so the walk records what it observed without a second pass. The pattern is uniform across
KEL, IEL, and SEL.

### Federation witnessing in verification

Federation witnessing surfaces in verification as the per-token witnessing signals and as the set of
witnessed anchors that IEL / SEL anchor resolution consults on a KEL. IEL and SEL events
authenticate via their KEL anchors, but federation context attaches **per layer**: a **KEL** carries
it (the most-recent `Icp` / `Wit`); a user **IEL records its own** authoritative binding
(`federation` / `federationPin` on its `Icp`/`Wit`, field-matched to its members' KEL `Wit`s); a
**SEL** carries no federation field and inherits its owner IEL's. The KEL is the leaf of trust
composition — witnessed-anchor resolution resolves each leaf-anchor to its KEL event, while the
federation **binding** is read from the layer that owns it (above). A consumer refuses to bind under
a divergent position or insufficient attestation, and grounds trust in the **config-pinned
federation prefix set** (compile-time-baked + runtime override) — for a chain that transferred
federations via `Wit`, each federation in its history must be independently in the trusted set (no
transitive trust). The full witnessing rules are federation doctrine ([`federation/`](federation/) —
_forthcoming_).

### Effective-SAID comparison

The effective SAID is the canonical chain-state fingerprint across KEL, IEL, and SEL — it lets nodes
recognize each other's state cheaply and is the universal "has state changed?" comparison behind
token reuse, deferred-dependency draining, anti-entropy, and divergence handling. It is a **hash
over the live branch tips a node holds** — the canonical tip and any unresolved competing branch — a
fingerprint of the node's _live_ state, never of the trust reading:

- **A single live tip** (Active / Recovered / Decommissioned) — that tip's real SAID (a
  decommissioned chain's is its `Dec`).
- **Several live tips** (an unresolved fork — a live content fork, or a privileged branch past it) —
  a **domain-separated hash of all the live tip SAIDs, sorted**: sort ascending, length-prefix,
  concatenate, hash, apply the domain tag (distinct from a single-tip SAID, so a linear and a forked
  state cannot collide). Every live tip enters, the canonical one included — not a selected subset
  among them. The construction is a conformance requirement: two implementations that disagree on
  the bytes produce a permanent digest mismatch.

A **settled** branch does not enter the digest: one a landed repair **condemned** (its `fork` root,
or dead by descent below it), or a content sibling **buried** below the derived seal (inert). These
are forensic — reached by the on-chain `fork` commitment and a by-prefix fetch, never gossiped
through the digest — so a resolved fork returns to its **canonical tip** on every node, the
condemned branch a node happens to retain not perturbing the value, and anti-entropy never chases
settled evidence.

Both the digest and the reading are **pure functions of the events a node holds** — the walk derives
the seal from those events, not from arrival order — so two nodes holding the same events compute
the same digest **and** read the same region. The `forked` / `disputed` / trusted **reading value is
separate and is never in the digest**: a data-local walk over the retained branches reads `forked`
(at most one privileged branch past the fork — reconcilable, pending its repair; only content `Ixn`
produces a reconcilable fork, so a federation IEL, which carries no content, never reads `forked`)
or `disputed` (two or more privileged branches — terminal, reincept). A settled fork drops out of
both at once: its condemned or buried loser leaves the live-tip set, so the digest returns to the
canonical tip and the reading returns to Active, in lockstep, on every node.

The digest is **tip-sensitive** — it moves the instant a node's held tip set changes — and that is
load-bearing: the anti-entropy trigger is the effective-SAID delta, so a tip a node lacks must move
the value to drive the fetch that assembles it. A node fetches `since: {its own last seal}` —
pulling everything from that seal forward (the canonical tip, every competing branch above it, a
resolving repair) **plus the seal's own siblings**, so it also learns if the seal it anchors on is
itself forked — and SAID-addressed dedupe reconciles cleanly. Convergence is **conditional on
propagation**: witnessed events always propagate and are never dropped, so all nodes eventually hold
the same tips and compute the same value; the un-witnessed flood a node may briefly hold is declined
by witnesses and droppable, so it self-limits. **Fail-secure under partition** — two nodes holding
different tip sets compute different digests, so disagreement drives a fetch where the peer is
reachable and reads as distrust where it is not; nodes never falsely agree. The one thing the
fingerprint cannot carry is a privileged branch a node does not hold at all — most sharply, one
minted **below its own seal** (a reserve harvested long after that position sealed): the node that
holds it reads `disputed` directly, and a node without it learns it from the witness beacon (or is
eclipsed until it does) — the standing eclipse limit, not a false agreement. Differently-forked
nodes **converge by exchanging the branches they each lack**, while the **repair** resolves the
fork: sync propagates, repair resolves.
