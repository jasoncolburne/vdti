# vdti — area note: IPEX (the issuance & presentation exchange protocol)

**Status: FIRST CUT — new protocol primitive in the `protocols/` tier (2026-07-17). Grounded on the
primary spec (draft-ssmith-ipex-00, Smith & Feairheller) as an independent, non-wire-compatible
adaptation; the divergence ledger records where we deliberately differ.** IPEX is a **protocol
primitive**: the mechanism by which one party discloses one or more **anchored, compactable SADs** to
another in a securely attributable way. Its one insight — **every exchange, issuance and presentation
alike, is a disclosure from a Discloser to a Disclosee.** Issuance is the case where the Discloser is the
disclosed SAD's issuer; presentation is the case where the Discloser is its holder. One protocol serves
both because only the _information disclosed_ differs, never the _mechanism_.

**It is thin, and generic over its payload.** IPEX carries anchored, compactable SADs — it does **not**
know they are credentials. It exposes to its consumer exactly three things: an **authenticated
discloser**, a **challenge / audience binding** (so a disclosure cannot be replayed to a party it was not
made to), and the **disclosed SAD** (verifiable as issued, revealed to the promised depth). Credentials is
one consumer; a shared-document capability grant could be another. Confidentiality is **not** IPEX — a
private disclosure rides IPEX **inside** an ESSR envelope ([`vdti-area-essr.md`](vdti-area-essr.md)),
stacked at the edge: integrity and attribution from IPEX, confidentiality from ESSR.

**Invariants:** [inv 8] multi-source freshness (the verifier reads the discloser's current witnessed tip),
[inv 16] addressing by prefix, [inv 17] chain validity is content-independent (IPEX is generic over the
SAD it carries). Composes: the **anchor** (proof-of-issuance) and **compaction** (proof-of-disclosure) SAD
primitives; the ESSR primitive (§Boundary); the exchange feature for transport
([`vdti-area-exchange.md`](vdti-area-exchange.md) §7).

## Attribution

IPEX is prior art we adopt for its **name and shape**, adapt for our own trust model, and credit. We take
the message set and the disclosure model; the security model is our own (the spec's is unspecified — see
§Presentation freshness). We translate the spec's vocabulary into vdti terms and never lift its text.

- **Origin — Samuel M. Smith & Philip Feairheller, "Issuance and Presentation Exchange Protocol"**
  (`draft-ssmith-ipex-00`; `https://datatracker.ietf.org/doc/html/draft-ssmith-ipex-00`; local copy
  `.working/draft-ssmith-ipex.md`). IPEX is defined there over the authors' own credential container and
  identifier formats; vdti adopts the **protocol** (the disclosure model, the message set, graduated
  disclosure, targeted / untargeted) over **vdti's** primitives (IEL-prefix identities, anchored SADs,
  compaction). This is an **independent, non-wire-compatible** adaptation — the messages are vdti SADs, not
  the spec's serialization.
- **Reference implementation — keripy** `src/keri/vc/protocoling.py` (the message set + the previous-message
  state machine). Consulted for the state transitions; the shapes here are vdti SADs.
- **We diverge deliberately** on the two proofs (anchor, not a detached signature; compaction, not a
  Merkle-tree over variants) and **add** the presentation-freshness envelope — see the divergence ledger.

## The model — disclosure, Discloser → Disclosee

Every IPEX exchange moves a disclosure from a **Discloser** (who holds and reveals the SAD) to a
**Disclosee** (who receives and verifies it). Two role pairs sit underneath, depending on the exchange:

- **Presentation** — the Discloser is the SAD's **holder** (its issuee, for a targeted credential); the
  Disclosee is the **verifier**.
- **Issuance** — the Discloser is the SAD's **issuer**; the Disclosee is the party being issued to (the
  issuee). Issuance is exactly the presentation whose Discloser authored the anchor.

**The message set.** Six kinds, each a **kinded, signed SAD** threaded to its predecessor by `previous`:

| Message  | Sender    | Role                                                                     |
| -------- | --------- | ------------------------------------------------------------------------ |
| `apply`  | Disclosee | Requests a disclosure of a stated type; MAY carry a challenge (see below) |
| `offer`  | Discloser | Offers a disclosure — a metadata / partial manifest, to induce agreement  |
| `agree`  | Disclosee | Accepts the offer (and its terms-of-use)                                  |
| `grant`  | Discloser | **The disclosure itself** — the disclosed SAD + the freshness envelope    |
| `admit`  | Disclosee | Acknowledges receipt                                                      |
| `spurn`  | either    | Rejects, at any step                                                      |

**The state machine.** `offer ← apply`, `agree ← offer`, `grant ← agree`, `admit ← grant`; `spurn` may
follow any of `{apply, offer, agree, grant}`, sent by the party **receiving** the message it rejects (the
one whose turn it is to respond). The exchange has three entry points:

- **Full negotiated:** `apply → offer → agree → grant → admit`. The Disclosee pulls; the parties negotiate
  terms via the metadata manifest before any content is revealed.
- **Minimal push:** `grant → admit`. The Discloser pushes an unrequested disclosure (the common
  presentation baseline — the holder presents to a verifier).
- **Discloser-initiated:** `offer → agree → grant → admit`. The Discloser starts by offering.

Only `grant` carries content and the freshness envelope; the other messages are lightweight
negotiation / acknowledgement, each signed by its sender over its own SAID.

## The two proofs

A Disclosee validating a disclosure needs two independent proofs. IPEX names them; vdti supplies each from
a **primitive it already has**, which is where our two divergences from the spec live.

- **Proof of issuance — the _anchor_.** The disclosed SAD is authentic-as-issued because its issuer
  **anchored** its fully-compacted SAID on the issuer's **witnessed** chain (an interaction event, T1).
  The anchor is **witnessed** (federation-attested), **positioned** (a point in the issuer's chain, so it
  is time-ordered and revocable in place by a later event), and read **as-of its anchoring position**
  (which the disclosed SAD locates directly). This is strictly stronger than a detached issuer signature: a
  signature is unwitnessed, unpositioned, and cannot be revoked where it stands. **vdti does not use the
  detached-signature issuance proof** (see the ledger).
- **Proof of disclosure — _compaction_.** The disclosed SAD commits its nested sections by **SAID**
  (vdti's compaction is a **recursive SAID commitment**). So the issuer's commitment to the fully-compacted
  SAID is simultaneously a commitment to every faithful expansion of it: the Disclosee verifies the
  compact SAD against the anchored SAID, then verifies each revealed nested SAD against the SAID that
  stood in its place. **Graduated disclosure** — revealing the compact form, then recursively expanding
  the sections the disclosure promised — is exactly this recursive check. Because the fully-compacted SAID
  is the canonical, always-re-derivable form, a single anchored SAID proves issuance of any faithful
  variant the Discloser chooses to reveal.

## Presentation freshness — the single-round-trip envelope

The spec leaves its Security Considerations unspecified; vdti supplies the model. A credential is
long-lived (its freshness is the anchor + revocation + an advisory `expires`); a **presentation** must be
fresh **per use**, or a captured `grant` replays. The two timescales must not be conflated — the
_envelope_ is fresh-within-tolerance, never the credential.

**The `grant` envelope.** A `grant` binds the disclosure to one use:

```
grant = {
  said,       // commits every field below; the signature is over the SAID recomputed from this body
  kind,       // vdti/ipex/v1/schemas/grant
  previous,   // SAID of the agree (absent for a minimal push)
  discloser,  // the discloser's IEL prefix — MUST equal the disclosed SAD's committed issuee for a targeted disclosure
  audience,   // the Disclosee's (verifier's) IEL prefix — binds this disclosure to one recipient
  nonce,      // discloser-generated, per-presentation, ≥128-bit CSPRNG — the replay-dedup entropy
  created,    // = now; bounds cache retention, NEVER a trust input (see below)
  challenge,  // OPTIONAL — echoes the verifier's apply-challenge nonce (stronger-liveness mode only)
  disclosed,  // the disclosed SAD (or, at a graduated step, the SAID it committed earlier)
}
```

signed over the recomputed `grant.said` by the **presenter's current-tip `t_use` quorum**. That one
signature does **double duty**: it proves **ownership** — for a targeted disclosure the required signer is
the disclosed SAD's committed **issuee** (not the self-declared `discloser`), so a valid signature means
the presenter controls the issuee's `t_use` threshold (the "who may present" question, satisfied
structurally, not by a separate live challenge) — **and** it binds the disclosure to `{audience, nonce,
created}` so it cannot be replayed. This is why the baseline is a single round trip.

**Signed, not anchored.** The `grant` is **signed**, never anchored — a presentation writes **nothing** to
the chain. Anchoring every presentation would be **infeasible** (a witnessed chain event per credential
use) and **correlating** (every use would surface on the presenter's own witnessed chain — who presented,
when, how often). The verifier's replay-protection is entirely local: dedup + `audience` + the current-tip
signature, resolved over a chain **read**, never a write. Only the **credential** is anchored, once, at
issuance. The **one** exception is opt-in — a high-value, non-repudiable presentation MAY additionally
**anchor** `grant.said` on the presenter's chain (an interaction event), trading that correlation for
**third-party-provable** liveness (the presentation existed at a witnessed position, so a stale key cannot
backdate it). Baseline presentations do not.

**The verifier's gate.** Accept the disclosure iff **all** hold, in order:

- the message `kind` is `vdti/ipex/v1/schemas/grant`;
- `said` equals the SAID **recomputed** over the envelope body — reject on mismatch; the signature is over
  that recomputed `said`, which is what binds it to every field (`audience`, `nonce`, `created`,
  `disclosed`, …);
- the signature resolves, at its **current witnessed tip** (multi-source, [inv 8]), to the **required
  signer** — for a **targeted** disclosed SAD, the SAD's committed **`issuee`** (and `discloser` equals
  it); for an **untargeted** SAD, the `discloser` (bearer — no ownership binding). Presenting is a live
  **`t_use` action**, **frozen on any divergence** (`iel/verification.md`): a **forked, disputed, or
  terminated** signer cannot present — a fork freezes actions pending governance recovery, a dispute
  is unreconcilable, a retired identity is done — REFUSE;
- `audience` is the verifier's own prefix;
- `created` is within tolerance on **both** sides: `|now − created| ≤ tolerance` (reject stale **and**
  future; the tolerance absorbs clock skew);
- `nonce` is **not** already in the dedup cache — keyed on `(signer, nonce)` — then **insert-and-consume**
  it; retention is measured **from `created`** (evict at `created + tolerance`);
- the disclosed SAD passes its type's **as-issued** verification — a **delegation** to the
  disclosed-SAD-type's own check (the consumer's: the anchor on the issuer chain the SAD commits, located
  by its `issuerPin`, not revoked, not expired);
- **(negotiated flow only)** `previous` equals the `agree` the verifier issued, binding the disclosure to
  the accepted terms; absent for a minimal push;
- **(stronger-liveness mode only)** `challenge` equals the nonce the verifier's `apply` issued.

IPEX supplies only the freshness envelope; it relies on the disclosed SAD committing whatever the as-issued
check needs (its issuer's prefix), which is how a verifier locates the issuer chain for a **generic**
(credential-agnostic) disclosed SAD.

**Why it holds (adversary).** Replay **to me** → the nonce is already consumed (dedup). Replay
**elsewhere** → `audience` mismatches. **Present someone else's targeted credential** → the required signer
is that credential's committed `issuee`, whose `t_use` key the impersonator lacks. **Swap the credential**
into a captured envelope → the recomputed `said` no longer matches the body, and the signature is over the
recomputed `said`, so it breaks. **Forge** → no `t_use` key. A targeted credential's copy-and-replay is
closed **within a single `grant`** — no verifier-issued challenge is required.

**The timestamp is a cache bound, never a trust input.** `created` is self-asserted and forgeable, so it
**only** bounds how long the dedup cache must retain a nonce. The **alignment invariant**: the acceptance
test is two-sided (`|now − created| ≤ tolerance`, rejecting both stale and future), and dedup retention is
measured **from `created`** and set **≥ tolerance** — so an envelope leaves the acceptance window and the
cache **together**. A replay still inside the window is still cached; a replay outside it is rejected by
the timestamp gate. Trust never rests on the timestamp.

**Optional stronger liveness — the verifier's challenge.** For high-assurance uses, the verifier issues an
`apply` carrying a fresh challenge nonce; the `grant` echoes it in its optional **`challenge`** field, and
the gate adds the clause `challenge == the nonce the verifier issued`. This proves the presentation is live
**in response to _this_ verifier's challenge**, not merely fresh-and-audience-bound-and-un-replayed. It is
a mode, **not** the baseline.

## Targeted vs untargeted

- **Targeted** — the disclosed SAD names an **issuee**. The verifier's gate requires the `grant` signature
  to resolve to that **committed issuee**'s current-tip `t_use` quorum (and `discloser` to equal it) — so only
  the issuee can present, enforced against the committed field, never the self-declared `discloser`.
- **Untargeted (bearer)** — the SAD names no issuee. Any holder presents it; there is no ownership binding
  to check (the ownership step is **skipped**). The freshness envelope still binds `{audience, nonce}`, so
  a captured bearer presentation cannot be replayed to a different verifier — but a bearer credential
  copied by an observer can be re-presented by the copier (the inherent bearer trade-off, stated in the
  credential residuals, not an IPEX defect).

The "who may present" ownership step is an **authentication of the issuee** (satisfy its `t_use` threshold),
**not a policy** and not part of the disclosed SAD's authorization. IPEX realizes it as the `grant`'s
`t_use`-quorum signature; a consumer never writes a policy for it.

## The boundary — thin, payload-agnostic

Everything below is **not** IPEX:

- **Confidentiality.** IPEX proves _who disclosed what, to whom, freshly_. Hiding the disclosure from the
  transport is **ESSR at the edge** — a private disclosure is an IPEX message sealed inside an ESSR
  envelope. IPEX carries cleartext-structured SADs; the choice to seal is the consumer's, made where the
  exchange is wired.
- **Transport and delivery.** Routing, store-and-forward, the serve-time gate — the **exchange / mail
  feature** ([`vdti-area-exchange.md`](vdti-area-exchange.md) §5, §7). IPEX defines the messages; the
  feature moves them.
- **Revocation status.** Whether the disclosed credential is still live is the **consumer's** fail-secure
  walk (the issuer's `kills[]` + the lookup SEL), read at verification time. IPEX surfaces the disclosed
  SAD; the consumer runs the status check.
- **Key resolution.** Turning `discloser` (a prefix) into a verify-key at its current tip is the caller's
  chain read. IPEX is handed the resolved key-state (multi-source, [inv 8]).
- **The replay cache.** The dedup state behind the freshness gate is a **storage capability** the verifier
  supplies — not an IPEX data structure (see the marked section).
- **What is disclosed.** IPEX is generic; the meaning of the SAD (a credential, a capability grant) is the
  **consumer's**. Credentials is one consumer.

## Divergence ledger (vs. the primary spec)

**Faithful (no change):** the disclosure model (Discloser → Disclosee, issuance as the Discloser-is-issuer
case); the six-message set (`apply / offer / agree / grant / admit / spurn`) and its state machine;
graduated disclosure (reveal the compact form, then expand); targeted / untargeted disclosures; two proofs
(issuance, disclosure).

**Required vdti mods (kept, with reason):**

- **Proof of issuance = the anchor, not a detached signature.** The spec proves issuance with the issuer's
  signature over the compact SAID (equivalent to signing a Merkle root over variants). vdti proves it with
  the **anchor** on the issuer's witnessed chain — witnessed, positioned, revocable-in-place,
  earliest-floored. The detached-signature issuance model is **dropped** (redundant with, and weaker than,
  the anchor).
- **Proof of disclosure = compaction (recursive SAID commitment), not a Merkle-tree over variants.** The
  spec frames graduated disclosure as a hash-tree of variants analogous to a Merkle tree. vdti's
  **compaction** primitive is the same property expressed as a recursive SAID commitment; we state it in
  those terms, over the canonical fully-compacted SAID.
- **The presentation-freshness envelope on `grant`** — `{audience, nonce, created}` signed by the
  discloser's `t_use` quorum. The spec's Security Considerations are unspecified; this is the model vdti
  supplies. The **`audience`** binding (defeating cross-verifier replay) is the addition over the kels
  fetch-freshness precedent, which bound only the fetched object.
- **Post-quantum crypto + sign-the-SAID.** Messages are vdti SADs; signatures are lattice signatures over
  the message SAID (the universal vdti rule), in place of the spec's illustrative primitives.
- **Identities by IEL prefix; no status-registry identifier.** Senders and audiences are IEL prefixes, not
  the spec's identifiers. There is **no** credential-status-registry field — revocation is the issuer's
  `kills[]` on its witnessed chain plus a lookup SEL, checked by the consumer.

**Dropped / not adopted:** the detached-signature (CESR-proof) apparatus; the status-registry identifier.

**Secondary — modeled here, owned by a consumer (credentials):** the full negotiated flow
(`apply / offer / agree`, terms-of-use); **chain-link confidentiality** (terms-of-use carried across a
chain of successive Disclosees); credential **edges / chaining** (the disclosure DAG); **bulk issuance**.
These extend `grant / admit` and the freshness envelope without changing the core, and the credentials
note now settles their shapes. In particular **bulk issuance is the ordinary anchor at width** — N
individual per-credential commitments co-located in one anchoring event (`vdti-area-credentials.md`
§Bulk issuance), **not** a set-commitment anchor over blinded SAIDs: each credential is committed
individually, so there is no set-membership proof to build and no blinding. The privacy trade is
batch-linkability, chosen per issue (single issuance = unlinkable, bulk = cheap).

## [Implementation — not for design encoding]

_Guidance for the implementer; **not** promoted to the greenfield design docs. The design encode states
only the boundary property (the replay cache is a supplied capability; IPEX holds no verifier state)._

- The verifier's freshness gate needs a **bounded, evictable dedup cache** — a
  `check_and_consume(nonce, now) -> fresh?` behind a storage trait the caller supplies (in-memory, or a
  shared store such as Redis for a multi-process verifier). IPEX is defined over the capability, not a
  concrete cache — the same house pattern as ESSR's signing / decapsulation capabilities. Retention is set
  from the `created` tolerance (the alignment invariant above). Exact trait names / signatures are a code
  detail; the load-bearing statement is that verifier freshness state is pluggable and bounded.

## Residuals

- **Bearer copy-replay.** An untargeted (bearer) credential copied by an observer can be re-presented by
  the copier; the freshness envelope stops cross-verifier replay but not a fresh presentation by a
  copy-holder. Inherent to bearer credentials; the mitigation is to target the credential to an issuee.
- **Verifier freshness state.** Correct rejection of replays requires the dedup cache to be live and
  retained ≥ the `created` tolerance; a verifier that loses its cache within the acceptance window reopens
  the replay it was closing. Bounded and operational, not a protocol break.

## Drift → land

- Write `docs/design/primitives/protocols/ipex.md` fresh from this note (greenfield voice), alongside
  `protocols/essr.md`.
- **Reserved names** (`vdti/ipex/v1/<category>/<name>`): message kinds
  `vdti/ipex/v1/schemas/{apply,offer,agree,grant,admit,spurn}`; the transport topic is the exchange
  feature's (`vdti/exchange/v1/topics/exchange`), not IPEX's. Register the `ipex` component + these kinds
  in `kinds.md` at the encode.
- **Composition:** ship the canonical **IPEX-over-ESSR** reference composition (the private-disclosure
  adapter) so consumers don't re-wire the security-critical glue; credentials depends on IPEX, and reaches
  ESSR only through that composition.
