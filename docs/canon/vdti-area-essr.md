# vdti — area note: ESSR (the 1:1 authenticated-encryption primitive)

**Status: FIRST CUT — carved from `vdti-area-exchange.md` §1 into a standalone protocol primitive
(2026-07-16). Grounded on the primary spec (below), not on the kels implementation alone; the
divergence ledger records where we deliberately differ.** ESSR is a **protocol primitive** in the
`protocols/` tier: the one-to-one **sealed, authenticated envelope**. Given a sender, a recipient, and
a plaintext, it produces one message that **only the recipient can read** and that is **provably from
the sender**, resisting both key-compromise impersonation and sender-impersonation of the ciphertext.

**It is thin.** ESSR holds no key material, performs no chain lookup, and does not inspect the payload
it seals. Identity→key resolution, sender-key currency, delivery, identity-hiding, and group keying are
**not** ESSR — they belong to the exchange / mail feature or the consumer. This is what lets credentials
and the presentation exchange compose ESSR at the edge without pulling a feature's infrastructure along.

## Attribution

ESSR is prior art we adopt, adapt for our identity model, and credit — we design against the primary
spec, keeping only the mods our own crypto and reference model require.

- **Origin — Jee Hea An (2001), "Authenticated Encryption in the Public-Key Setting: Security Notions
  and Analyses"** (`https://eprint.iacr.org/2001/079`; local copy `.working/2001-079.ps`). The paper
  proves that the generic compositions (encrypt-and-sign, sign-then-encrypt, encrypt-then-sign) do **not**
  in general meet all its authenticity/confidentiality notions, and constructs **ESSR** as the scheme that
  does. The four structural guarantees below are that paper's notions, stated in plain terms.
- **Identity-chain adaptation — Samuel M. Smith, in the Trust Spanning Protocol.** Smith adapts ESSR so
  that the sender and recipient are named by their **chain identifiers** (their prefixes), with the actual
  public keys looked up from their logs rather than carried in the message. Sources:
  `https://weboftrust.github.io/WOT-terms/docs/glossary/ESSR`, the TSP spec
  (`https://trustoverip.github.io/tswg-tsp-specification/`), and his SPAC whitepaper
  (`.working/SPAC_Message.md`). vdti's prefix-named form follows this adaptation directly.
- **Reference implementation — kels** `lib/exchange/src/essr.rs` (+ `message.rs`). Adopted for the
  construction; two kels-specific choices are corrected in the divergence ledger.

## What ESSR is, and why the shape is load-bearing

Strong 1:1 messaging needs two things at once: **confidentiality** (encrypt to the recipient) and
**authenticity** (sign by the sender). The order and the identity placement are not cosmetic:

- **Plain encrypt-then-sign is not enough.** Signing only the ciphertext lets a malicious receiver (or a
  third party) **strip the signature and re-sign the same ciphertext** with another key, purporting that
  the sender authored a plaintext it never saw.
- **ESSR fixes this with two bindings:** bind the **sender's identity _inside_ the ciphertext**, and bind
  the **recipient's identity in the _signed cleartext_**. The first stops sender-impersonation of the
  ciphertext; the second makes any recipient-key substitution detectable (the ciphertext must decrypt
  under the intended recipient's key, or the signature is invalid — anti-KCI).

**The four guarantees** (An 2001, in vdti words — two axes: _who_ would forge, an outside third party or
the receiver itself, × _what_ they'd forge, the plaintext or the ciphertext):

- **A third party cannot forge the plaintext** — no outsider can produce a message that verifies as the
  sender's carrying a plaintext of their choosing.
- **A third party cannot forge the ciphertext** — no outsider can produce a _ciphertext_ that verifies as
  the sender's. (Anyone _can_ encapsulate to the recipient — the KEM is a public operation — but not a
  ciphertext authenticated as from the sender.)
- **The receiver cannot forge the ciphertext** — a malicious recipient has no signing key, so it cannot
  produce a new ciphertext that verifies as the sender's. This holds from the signature alone (plain
  encrypt-then-sign).
- **The receiver cannot forge the plaintext** — a malicious recipient cannot make the sender's message
  appear to carry a plaintext the sender never authored (the non-repudiation case). **This is the one
  guarantee ESSR adds**, and it takes **both** bindings: the **recipient bound in the signed cleartext**
  stops a key-substitution (the ciphertext must decrypt under the intended recipient's key, or the signature
  is invalid), and the **sender bound inside the ciphertext** stops a strip-and-re-sign (a re-signed envelope
  naming a different sender fails the `inner.sender == envelope.sender` check). Plain encrypt-then-sign gives
  the other three.

**One strengthening from the identity model:** because sender and recipient are **chain prefixes** whose
keys come from their logs, a malicious recipient cannot substitute an arbitrary key — only a key that
actually appears in its own chain (at worst a stale one). Naming identities by prefix makes the anti-KCI
binding harder to attack than naming raw keys.

## The construction (full ESSR — no protection traded away)

We use the **full** ESSR message. The spec permits "sourceless / destinationless" variants that omit a
binding to save a field, each trading away one guarantee; we take **none** of those tradeoffs.

**The confidential inner** (AEAD-encrypted; ESSR defines only the sender binding, the rest is opaque):

```
inner = {
  said,
  kind,      // vdti/essr/v1/schemas/inner
  sender,    // the sender's IEL prefix — the binding that rides INSIDE the ciphertext
  payload,   // opaque application bytes — ESSR never inspects them
}
```

**The signed envelope** (cleartext; only what ESSR structurally needs):

```
envelope = {
  said,             // commits every field below; the signature is over this
  kind,             // vdti/essr/v1/schemas/envelope
  sender,           // the sender's IEL prefix — cleartext: locates the chain, routes, fetches the verify key
  senderPin,        // SAID of the sender's establishment event current at signing — which key-state verifies the signature
  recipient,        // the recipient's IEL prefix — bound by the signature (anti-KCI); the transport also routes on it
  kemCiphertext,    // lattice-KEM encapsulation to the recipient's receive key
  encryptedPayload, // AEAD( inner ) under the key derived from the KEM shared secret
  nonce,            // AEAD nonce — fresh random; a per-message key ⇒ single use
}
```

**The signed message** (handed to transport):

```
message = {
  said,
  kind,       // vdti/essr/v1/schemas/message
  envelope,   // the SAD above
  signature,  // lattice signature by the sender over envelope.said
}
```

**Seal:** encapsulate to the recipient's receive key → shared secret → KDF (domain-separation context
`vdti/essr/v1/protocols/kdf`) → AEAD key → encrypt `inner` with a fresh nonce → assemble `envelope` and
compute `said` → sign `said`.

**Open:** **recompute `envelope.said` from the envelope fields and reject on any mismatch** (the standard
SAD check — this is what makes the signature, which is over `said`, bind every field) → verify `signature`
over `said` against the sender's verify-key (**handed to ESSR**, resolved by the caller from `sender` +
`senderPin` — ESSR does no lookup; see the boundary) → **assert `envelope.recipient` is the opener's own
prefix** → decapsulate → derive the AEAD key → decrypt → **assert `inner.sender == envelope.sender`**.

Only `envelope.said` is signed, so only its recompute gates trust. `inner.said` and `message.said` are
ordinary SAD content-addresses, present by the universal SAD rule — `inner`'s bytes are integrity-protected
by the AEAD tag and the message by the envelope signature, so neither is separately security-load-bearing.

**Crypto by what it is** (strength-paired; the tier is a parameter, not a code path): a **lattice KEM**
(ML-KEM-768 / -1024), a **lattice signature** (ML-DSA-65 / -87), an **AEAD** (AES-256-GCM), a **KDF**
(blake3). Users may run the lighter tier; infrastructure runs the heavier one.

**Why the sender appears twice — by design.** The sender prefix is in the ciphertext (the
anti-impersonation binding) **and** in the cleartext envelope (so the transport can route and the
recipient can fetch the right verify-key). This is the full-ESSR baseline, not redundancy. The recipient
prefix is in the signed cleartext for the anti-KCI binding and for routing.

**Why the nonce is safe.** Each message derives a **fresh** shared secret → a **fresh** AEAD key used
**exactly once**, so a random nonce never repeats under a key. No cross-message nonce/key-scope discipline
is required — the key is per-message.

## The boundary — thin, payload-agnostic, no chain resolution

ESSR is deliberately narrow. Everything below is **not** ESSR:

- **Payload contents.** ESSR seals opaque bytes. A message timestamp, a protocol/topic multiplexer, the
  actual content — all shaped by the **application**, inside `payload`, confidential and signed. ESSR does
  not define or inspect them.
- **Key resolution.** Turning `recipient` (a prefix) into a receive key, or `sender` (a prefix) into a
  verify key, is the **exchange feature's** published-receive-key lookup and the caller's chain read. ESSR
  is handed the keys.
- **Sender-key currency.** "Is `senderPin`'s key-state still current / trusted, or superseded?" is the
  **consumer's** check against the sender's current witnessed chain. ESSR only needs the pin to verify the
  signature at all.
- **Identity hiding.** The sender and recipient prefixes are visible on a held message. Hiding them is
  **nested routing** — an outer message whose confidential payload is a nested ESSR message — a **mail /
  exchange feature** concern, not the primitive.
- **Delivery + the serve-time gate.** Storing and routing the opaque message, and gating delivery on a
  **live check of the recipient prefix** (prove you control it before the store serves you), are the
  **mail feature's** — they limit store-side harvesting even though the prefix is on the message.
- **Group keying.** Sealing an epoch key to many members, ratcheting, per-sender subkeys — the **exchange
  feature**, built on top of the 1:1 primitive.
- **Replay / freshness.** A sealed message can be re-delivered verbatim; ESSR does not detect replays —
  that is the **consumer's** (the presentation-freshness cache, or a mail dedup-by-SAID window). ESSR's
  fresh nonce buys **AEAD key-uniqueness**, not replay resistance.

**Keys enter through capabilities, not raw material.** ESSR is defined over what you can *do* with a key —
a signing capability on the sender side, a decapsulation capability on the recipient side — so it holds no
private key and is agnostic to where keys live. (The concrete interface is implementation; see the marked
section below.)

## Divergence ledger (vs. the primary spec)

**Faithful (no change):** the full-ESSR construction — sender bound inside the ciphertext, recipient bound
in the signed cleartext, encrypt-then-sign, the four guarantees. Naming sender and recipient by **chain
prefix with key-lookup from their logs** is the identity-chain adaptation's baseline, not a divergence.

**Required vdti mods (kept, with reason):**

- **Post-quantum crypto suite** — lattice KEM / lattice signature / AES-256-GCM / blake3, in place of the
  spec's illustrative primitives. The construction is primitive-agnostic; only the algorithms change.
- **Sign the SAID.** The signature is over the envelope's **SAID** (a commitment over every field) rather
  than over concatenated bytes — the universal vdti rule that all data is a kinded, SAID-addressed SAD.
  Signing a commitment that binds all fields is equivalent to signing the fields.
- **Pin the signing key-state by SAID (`senderPin`).** vdti names a point-in-time by **SAID pin**, not by a
  sequence number: a SAID names **one specific event** (specific bytes), so — unlike a serial, which two
  forks share — the pin is never ambiguous about _which_ event it means. It does **not** let verification
  survive a fork: `senderPin` resolves against the sender's **canonical** chain, and a fork **freezes** that
  chain (resolution undefined until the fork resolves — the same limit as any signature). The SAID removes
  the serial's ambiguity, not the fork's freeze.

**kels artifacts corrected (dropped / changed):**

- **Exposed plaintext timestamp — removed.** kels carried a `created` timestamp in the **cleartext**
  envelope, exposing message timing. A message timestamp is application payload: it rides **inside the
  ciphertext** (confidential and signed), or a *receive*-time is the mail service's own field in its outer
  wrapper. ESSR carries no timestamp.
- **Establishment serial → SAID pin.** kels pinned the signing key-state by an establishment **serial** (a
  sequence-number idiom); vdti pins by **SAID** (`senderPin`), consistent with refs-by-SAID. The gain is
  **disambiguation**, not fork-survival — a serial is identical on both sides of a fork, a SAID names one
  side; neither pin verifies against a frozen (forked) chain.

**Variants not used:** the sourceless / destinationless ESSR variants (omit a binding, trade a guarantee).
We use full ESSR; any future variant would have to explicate the tradeoff it accepts.

## [Implementation — not for design encoding]

_This section is guidance for the implementer; it is **not** promoted to the greenfield design docs. The
design encode states only the boundary property above (keys enter through capabilities; ESSR holds no key
material and does no chain resolution)._

- The seal side takes a **signing capability** (produces the lattice signature over the envelope SAID); the
  open side takes a **decapsulation capability** (recovers the KEM shared secret). Neither exposes a raw
  private key, so key custody — a hardware token, an enclave, or memory — is abstracted behind the
  interface. Public material (the recipient's receive key, the sender's verify key, the prefixes) is passed
  as values, or fetched by a resolver the caller supplies.
- The reference impl (`kels/lib/exchange/src/essr.rs`) passes concrete key types directly; vdti composes
  capability traits instead — the same house pattern as the replay-cache trait in the presentation-freshness
  design. Exact trait names/signatures are a code detail; the load-bearing statement is the capability seam.

## Residuals

- **Identity exposure on a held message.** `sender` and `recipient` prefixes are visible to anyone holding
  the bytes (required for routing + the anti-KCI binding). Mitigated at the feature layer by nested routing
  (full hiding) and the serve-time recipient-prefix delivery-gate (limits harvesting). Not an ESSR concern.
- **Sender-key currency is the consumer's.** ESSR verifies the signature against `senderPin`; whether that
  key-state is still trusted is checked outside ESSR, against the sender's current witnessed chain.

## Drift → land

- Write `docs/design/primitives/protocols/essr.md` fresh from this note (greenfield voice), alongside
  `protocols/ipex.md`.
- **Re-namespace the ESSR kinds** from the pre-carve `vdti/exchange/v1/protocols/essr` to
  `vdti/essr/v1/schemas/{envelope,inner,message}` in `kinds.md` (currently line 55) and `shapes.md`; register
  the **`essr` component** + the `vdti/essr/v1/protocols/kdf` context in `kinds.md`.
- **Correct the `shapes.md` envelope table** to this note's shape: `sender_serial` → **`senderPin`** (a SAID,
  not a serial — the fork-frozen axis); **drop the `created` field** (the divergence ledger removed the
  exposed plaintext timestamp); inner → **`{ said, kind, sender, payload }`** (`topic` rides _inside_
  `payload`, not an ESSR field); camelCase throughout.
- **Fix `vdti-area-exchange.md` §8** so the ESSR envelope + inner are no longer listed under
  `vdti/exchange/v1/schemas/*` (they moved to `vdti/essr/v1/schemas/*`); leave only the exchange-message
  shapes there.
