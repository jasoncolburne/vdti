# IPEX — the issuance and presentation exchange

IPEX is how one party discloses one or more **anchored, compactable SADs** to another so the
receiver can trust what it got. Its one insight is that **every exchange — issuing and presenting
alike — is a disclosure from a discloser to a disclosee.** Issuance is the case where the discloser
is the disclosed SAD's issuer; presentation is the case where the discloser is its holder. One
protocol serves both, because only the _information disclosed_ differs, never the _mechanism_.

It is **thin, and generic over what it carries.** IPEX moves anchored, compactable SADs — it does
not know they are credentials. It hands its caller exactly three things: an **authenticated
discloser**, a **binding to one recipient** (so a disclosure cannot be replayed to a party it was
not made to), and the **disclosed SAD** (verifiable as issued, revealed to the promised depth).
[Credentials](../../features/credentials.md) is one caller; a shared-document capability grant could
be another. Confidentiality is **not** IPEX: to hide a disclosure from the transport, seal an IPEX
message inside an [ESSR](essr.md) envelope — integrity and attribution from IPEX, confidentiality
from ESSR, stacked at the edge.

## The model — disclosure, discloser to disclosee

Every IPEX exchange moves a disclosure from a **discloser** (who holds and reveals the SAD) to a
**disclosee** (who receives and verifies it). Two role pairs sit underneath, by exchange:

- **Presentation** — the discloser is the SAD's **holder** (its issuee, for a targeted credential);
  the disclosee is the **verifier**.
- **Issuance** — the discloser is the SAD's **issuer**; the disclosee is the party being issued to.
  Issuance is exactly the presentation whose discloser authored the anchor.

**The message set.** Six kinds, each a [kinded](../data/sad/kinds.md), signed SAD threaded to its
predecessor by `previous`:

| Message | Sender    | Role                                                                      |
| ------- | --------- | ------------------------------------------------------------------------- |
| `apply` | disclosee | Requests a disclosure of a stated type; MAY carry a challenge (below)     |
| `offer` | discloser | Offers a disclosure — a metadata or partial manifest, to induce agreement |
| `agree` | disclosee | Accepts the offer and its terms                                           |
| `grant` | discloser | **The disclosure itself** — the disclosed SAD and the freshness envelope  |
| `admit` | disclosee | Acknowledges receipt                                                      |
| `spurn` | either    | Rejects, at any step                                                      |

**The state machine.** `offer ← apply`, `agree ← offer`, `grant ← agree`, `admit ← grant`; a `spurn`
may follow any of `apply` / `offer` / `agree` / `grant`, sent by the party whose turn it is to
respond. The exchange has three entry points:

- **Full negotiated:** `apply → offer → agree → grant → admit`. The disclosee pulls; the parties
  settle terms over the metadata manifest before any content is revealed.
- **Minimal push:** `grant → admit`. The discloser pushes an unrequested disclosure — the common
  presentation baseline, a holder presenting to a verifier.
- **Discloser-initiated:** `offer → agree → grant → admit`. The discloser starts by offering.

Only `grant` carries content and the freshness envelope; the rest are lightweight negotiation and
acknowledgement, each signed by its sender over its own SAID.

## The two proofs

A disclosee validating a disclosure needs two independent proofs. IPEX names them; VDTI supplies
each from a **primitive it already has**.

- **Proof of issuance — the [anchor](../data/event-logs/iel/events.md).** The disclosed SAD is
  authentic-as-issued because its issuer **anchored** it on the issuer's witnessed chain — an
  interaction event carrying a commitment to the credential's fully-compacted SAID (the commitment,
  not the raw SAID, is what the chain records). The anchor is **witnessed** (the federation attests
  it) and **positioned** (a point in the issuer's chain, so it is time-ordered and can be revoked in
  place by a later event); the consumer's as-issued check reads it **as-of that anchoring
  position**, which the disclosed SAD locates directly. This is strictly stronger than a bare issuer
  signature: a signature is unwitnessed, unpositioned, and cannot be revoked where it stands.
- **Proof of disclosure — [compaction](../data/sad/compaction.md).** A SAD commits its nested
  sections by SAID (VDTI's compaction is a recursive self-addressing commitment), so the issuer's
  commitment to the fully-compacted SAID is at the same time a commitment to every faithful
  expansion of it. The disclosee verifies the compact SAD against the anchored SAID, then verifies
  each revealed nested SAD against the SAID that stood in its place. **Graduated disclosure** —
  reveal the compact form, then expand only the sections the disclosure promised — is exactly this
  recursive check. Because the fully-compacted SAID is the canonical, always-re-derivable form, one
  anchored SAID proves issuance of any faithful variant the discloser chooses to reveal.

## Presentation freshness — the single-round-trip envelope

A credential is long-lived — its freshness is the anchor, revocation, and an advisory expiry. A
**presentation** must be fresh **per use**, or a captured `grant` replays. The two timescales must
not be conflated: the **envelope** is fresh-within-tolerance, never the credential.

**The `grant` envelope.** A `grant` binds the disclosure to one use:

```
grant = {
  said,        // commits every field below; the signature is over the SAID recomputed from this body
  kind,        // vdti/ipex/v1/schemas/grant
  previous,    // SAID of the agree (absent for a minimal push)
  discloser,   // the discloser's IEL prefix — for a targeted disclosure, MUST equal the SAD's committed issuee
  audience,    // the verifier's IEL prefix — binds this disclosure to one recipient
  nonce,       // discloser-generated, per-presentation, high-entropy — the replay-dedup entropy
  created,     // = now; bounds cache retention, never a trust input (see below)
  challenge,   // OPTIONAL — echoes the verifier's apply-challenge (stronger-liveness mode only)
  disclosed,   // the disclosed SAD (or, at a graduated step, the SAID it committed earlier)
}
```

signed over the recomputed `grant.said` by the **presenter's current-tip `t_use` quorum**. That one
signature does **double duty**. It proves **ownership** — for a targeted disclosure the required
signer is the disclosed SAD's committed **issuee** (not the self-declared `discloser`), so a valid
signature means the presenter controls the issuee's `t_use` threshold, which answers "who may
present" structurally, with no separate challenge — **and** it binds the disclosure to
`{ audience, nonce, created }` so it cannot be replayed. That is why the baseline is a single round
trip.

**Signed, not anchored.** A `grant` is **signed**, never anchored — a presentation writes
**nothing** to the chain. Anchoring every presentation would be infeasible (a witnessed chain event
per use) and self-surveilling (every use would surface on the presenter's own witnessed chain — who
presented, when, how often). The verifier's replay defence is entirely local: dedup, the `audience`
binding, and the current-tip signature, resolved over a chain **read**, never a write. Only the
**credential** is anchored, once, at issuance. The one exception is opt-in: a high-value,
non-repudiable presentation MAY additionally anchor its `grant.said` on the presenter's chain,
trading that correlation for third-party-provable liveness. Baseline presentations do not.

**The verifier's gate.** Accept the disclosure only if **all** hold, in order:

- the message `kind` is `vdti/ipex/v1/schemas/grant`;
- `said` equals the SAID **recomputed** over the body — reject on mismatch; the signature is over
  that recomputed `said`, which is what binds it to every field (`audience`, `nonce`, `created`,
  `disclosed`, …);
- the signature resolves, at the signer's **current witnessed tip** (read from any source), to the
  **required signer** — for a **targeted** disclosed SAD, the SAD's committed **`issuee`** (and
  `discloser` equals it); for an **untargeted** SAD, the `discloser` (a bearer — no ownership
  binding). Presenting is a live **`t_use` action**, so it is **frozen on any divergence**
  (`iel/verification.md`): a **forked, disputed, or terminated** signer cannot present — a fork
  freezes actions pending any **T2 seal-out** (`iel/verification.md`), a dispute is unreconcilable,
  a retired identity is done — and the gate refuses (fail-secure);
- `audience` is the verifier's own prefix;
- `created` is within tolerance on **both** sides — `|now − created| ≤ tolerance`, rejecting stale
  **and** future — the tolerance absorbing clock skew;
- `nonce` is **not** already in the dedup cache, keyed on `(signer, nonce)`; then **insert and
  consume** it, retaining it until `created + tolerance`;
- the disclosed SAD passes its own type's **as-issued** validity check — a check IPEX **delegates**
  to the caller (for a credential: the anchor on the issuer chain the SAD commits, located by its
  `issuerPin`, not revoked, not expired);
- **(negotiated flow only)** `previous` equals the `agree` the verifier issued, binding the
  disclosure to the accepted terms; absent for a minimal push;
- **(stronger-liveness mode only)** `challenge` equals the value the verifier's `apply` issued.

IPEX supplies only the freshness envelope; it relies on the disclosed SAD committing whatever its
as-issued check needs (its issuer's prefix), which is how a verifier locates the issuer chain for a
disclosed SAD it treats generically.

**Why it holds.** Replay **to me** → the nonce is already consumed. Replay **elsewhere** →
`audience` mismatches. **Present someone else's targeted credential** → the required signer is that
credential's committed issuee, whose `t_use` key the impersonator lacks. **Swap the credential**
into a captured envelope → the recomputed `said` no longer matches the body, and the signature is
over that recomputed `said`, so it breaks. **Forge** → no `t_use` key. A targeted credential's
copy-and-replay is closed **within a single `grant`** — no verifier-issued challenge required.

**The timestamp is a cache bound, never a trust input.** `created` is self-asserted and forgeable,
so it **only** bounds how long the dedup cache must retain a nonce. The acceptance test is two-sided
(rejecting both stale and future), and retention is measured from `created` and set to at least the
tolerance — so an envelope leaves the acceptance window and the cache **together**. A replay still
inside the window is still cached; a replay outside it is rejected on the timestamp. Trust never
rests on `created`.

**Optional stronger liveness — the verifier's challenge.** For high-assurance uses, the verifier
issues an `apply` carrying a fresh challenge; the `grant` echoes it in `challenge`, and the gate
adds the clause "`challenge` equals the value the verifier issued." This proves the presentation is
live **in response to this verifier's challenge**, not merely fresh, addressed to it, and
un-replayed. It is a mode, not the baseline.

## Targeted vs untargeted disclosures

- **Targeted** — the disclosed SAD names an **issuee**. The verifier's gate requires the `grant`
  signature to resolve to that committed issuee's current-tip `t_use` quorum (and `discloser` to
  equal it), so only the issuee can present — enforced against the committed field, never the
  self-declared `discloser`.
- **Untargeted (bearer)** — the SAD names no issuee. Any holder presents it; there is no ownership
  binding to check, so that step is skipped. The freshness envelope still binds
  `{ audience, nonce }`, so a captured bearer presentation cannot be replayed to a different
  verifier — but a bearer credential copied by an observer can be re-presented by the copier. That
  is inherent to bearer credentials, stated in the credential residuals, not an IPEX defect.

The "who may present" step is an **authentication of the issuee** — satisfy its `t_use` threshold
(presenting a credential is a **use** act, like issuing one, so it draws on the issuee's `t_use`
slot) — **not a policy**, and not part of the disclosed SAD's own authorization. IPEX realizes it as
the `grant`'s `t_use`-quorum signature; a caller never writes a policy for it.

## The boundary — what IPEX is not

Everything below sits **outside** IPEX:

- **Confidentiality.** IPEX proves _who disclosed what, to whom, freshly_. Hiding the disclosure
  from the transport is [ESSR](essr.md) at the edge — a private disclosure is an IPEX message sealed
  inside an ESSR envelope. IPEX carries cleartext-structured SADs; the choice to seal is the
  caller's.
- **Transport and delivery.** Routing, store-and-forward, the serve-time gate — the
  [exchange / mail](../../features/exchange.md) feature. IPEX defines the messages; the feature
  moves them.
- **Revocation status.** Whether the disclosed credential is still live is the **caller's**
  fail-secure check — the issuer's revocation declaration plus its lookup log
  ([`../data/event-logs/iel/events.md`](../data/event-logs/iel/events.md)) — read at verification
  time. IPEX surfaces the disclosed SAD; the caller runs the status check.
- **Key resolution.** Turning `discloser` into a verify key at its current tip is the caller's chain
  read. IPEX is handed the resolved key state.
- **The replay cache.** The dedup state behind the freshness gate is a storage capability the
  verifier supplies — not an IPEX data structure. IPEX is defined over the capability (a
  check-and-consume on a nonce), so its freshness state is pluggable and bounded, not baked in.
- **What is disclosed.** IPEX is generic; the meaning of the SAD — a credential, a capability grant
  — is the caller's. Credentials is one caller.

## Credit and prior art

IPEX — Issuance and Presentation Exchange — is **Samuel M. Smith and Philip Feairheller's** protocol
([draft-ssmith-ipex-00](https://datatracker.ietf.org/doc/html/draft-ssmith-ipex-00)). VDTI adopts
its disclosure model, its six-message set, graduated disclosure, and the targeted / untargeted
distinction, as an **independent, non-wire-compatible adaptation** over VDTI's own primitives — the
anchor for proof of issuance, compaction for proof of disclosure, and the presentation-freshness
envelope for per-use liveness — stated here in VDTI's own terms. The messages are VDTI SADs, not the
original serialization.

## Residuals

- **Bearer copy-replay.** An untargeted (bearer) credential copied by an observer can be
  re-presented by the copier; the freshness envelope stops cross-verifier replay but not a fresh
  presentation by a copy-holder. Inherent to bearer credentials; the fix is to target the credential
  to an issuee.
- **Verifier freshness state.** Correct rejection of replays needs the dedup cache to be live and
  retained at least as long as the acceptance tolerance; a verifier that loses its cache within the
  acceptance window reopens the replay it was closing. Bounded and operational, not a protocol
  break.

## Cross-references

- [`essr.md`](essr.md) — the sealed envelope a private disclosure rides inside.
- [`../data/sad/compaction.md`](../data/sad/compaction.md) — the recursive self-addressing
  commitment that is proof of disclosure.
- [`../data/sad/sad.md`](../data/sad/sad.md) / [`../data/sad/kinds.md`](../data/sad/kinds.md) — the
  SAD layer and the naming convention the `vdti/ipex/v1/*` message kinds follow.
- [`../data/event-logs/iel/events.md`](../data/event-logs/iel/events.md) — the anchor that is proof
  of issuance, the `t_use` quorum the `grant` signature resolves against, and the revocation
  declaration the status check reads.
- [`../../substrate/federation/witnessing.md`](../../substrate/federation/witnessing.md) — why the
  anchor is witnessed and how the current tip is read from any source.
- [`../policy/evaluation.md`](../policy/evaluation.md) — as-issued evaluation, the same discipline
  the disclosed SAD's validity check follows.
- [`../../features/credentials.md`](../../features/credentials.md) — the first caller: what a
  disclosed SAD means, and the revocation and expiry checks IPEX delegates.
