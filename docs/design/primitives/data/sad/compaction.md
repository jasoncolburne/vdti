# SAD Compaction

**SAD compaction** is the structural transform between a fully-expanded SAD and its
**fully-compacted** representation, which replaces nested sub-SADs with their SAIDs. A SAD's
[SAID](said.md) is **defined over the fully-compacted canonical form** (Rule 1 in
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation));
every wire form **re-derives to that one canonical SAID by compacting down** (verifying each child),
so a differently-compacted wire form is checked against the committed SAID, never assumed equal to
it. A verifier can validate the compacted shape and fetch sub-SADs on demand when full content is
needed.

This doc states the compaction rule, the SAID-preservation invariant that makes the rule
load-bearing, and the resource-amplification defense that constrains compactor implementations.

## The transform

A SAD that nests another SAD as a field value can carry that child either inline (the full child
object embedded in the parent) or by reference (only the child's SAID embedded in the parent).
Compaction is the rewrite that replaces an inline child with its SAID; expansion is the reverse,
re-fetching the child by SAID and substituting it back in.

Both shapes are valid SAD representations of the same logical content. A consumer that needs only
the SAIDs of nested children can stop at the compacted form; a consumer that needs full content of a
specific child walks the reference and fetches it from the SAD object store (or from gossip, or from
a peer). Other children stay compacted — disclosure is partial at the granularity of individual
sub-SADs.

## SAID-preservation invariant

Every wire form of a SAD **re-derives to the same canonical (fully-compacted) SAID by compacting
down** — wire forms embed sub-SADs differently, but Rule 1 (the canonical form represents nested
SADs by SAID) in
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation) fixes
the canonical bytes as the **fully-compacted** form's, and a verifier reaches them from any wire
form by compacting (verifying each child per Rule 2). The SAID — defined over the fully-compacted
canonical form, not read off the wire bytes — is therefore the value already committed in `previous`
pointers, anchor SAIDs, signatures, and custody references, and it does not change when sub-SADs are
compacted or re-expanded. This is what makes compaction operationally useful.

The invariant is a direct corollary of the two rules in
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation):

- **Rule 1** says the canonical form the hash sees always represents nested SADs by SAID. Both
  compacted and expanded wire forms **compact down to the same canonical bytes**, and therefore
  re-derive the same SAID — the fully-compacted form's.
- **Rule 2** says a verifier receiving an expanded form must verify each embedded child's declared
  SAID against the child's own bytes before substituting it into the parent's canonical form.
  Tamper-evidence recurses down through inline embedding, so an expanded form cannot lie about what
  its children are.

A verifier handed a compacted SAD recomputes the parent's SAID directly from the SAID-referenced
form. A verifier handed an expanded SAD walks the embedded children (verifying each per Rule 2),
substitutes their SAIDs into the canonical form, and recomputes the same parent SAID. The two wire
forms are interchangeable as far as SAID-level tamper-evidence is concerned.

## Partial disclosure

Compaction is the structural prerequisite for partial disclosure of nested content.

- **Credentials.** A credential SAD can carry nested claim SADs; a disclosure presents the
  credential's claims in compacted form, with only the disclosed claims expanded. The verifier
  checks the credential's SAID (matching the issuer's issuance-commitment anchor on its IEL) and
  then verifies that each expanded claim is the SAD whose SAID appears at that position. Undisclosed
  claims remain represented by their SAIDs alone, revealing nothing about the disclosed content
  beyond what is presented.
- **Policy SADs.** A policy declaration with nested sub-policies can be transmitted compacted;
  verifiers expand only the leaves they need to evaluate.
- **Exchange envelopes.** An envelope containing a payload SAD plus metadata SADs can be transmitted
  in any partially-compacted shape; receivers expand on demand.

The SAID-preservation invariant is what lets disclosed and undisclosed positions coexist in one
verifiable structure without forcing the producer to commit to a separate compacted-shape SAID.

## Privacy contract

Compaction interacts with custody. Under canonical form every sub-SAD is represented by SAID —
meaning every sub-SAD is a separately-addressable stored unit, fetchable by anyone who has its SAID.
**A parent SAD's `readPolicy` does not transitively protect its referenced sub-SADs.** If a parent
has `readPolicy` but a referenced sub-SAD does not, the sub-SAD's content is publicly fetchable by
SAID, even though the parent gates read access to its own content.

### The propagation rule

A sub-SAD inherits no protection from its parent's `readPolicy`. To be private, it MUST declare its
own `readPolicy`. Otherwise it is publicly fetchable by SAID.

### Expansion-time enforcement

When the storage service serves a SAD in expanded form, each sub-SAD reference resolved during
expansion is independently subject to that sub-SAD's own `readPolicy`. Expansion is operationally a
sequence of per-SAD fetches; a requester satisfying the parent's `readPolicy` does not automatically
gain access to children's gated content. Sub-SADs whose `readPolicy` is not satisfied by the request
remain represented by their SAID in the expanded response — the same shape the requester would see
if they fetched the parent compacted and walked the references themselves. Expansion is a round-trip
convenience, not a privilege-escalation surface.

### Intentional disconnection

The permissive rule is by design. A client MAY deliberately leave a sub-SAD without `readPolicy`
under a parent with `readPolicy`, intending the child to be publicly addressable independently of
the parent's gate — "disconnecting" the child from the parent's protection. Use cases include
selectively publishing a previously-gated artifact, attaching a public commitment alongside private
content, or any pattern where the child SHOULD be accessible without the parent's gate.

### App-builder responsibility

Apps built on VDTI SHOULD bake the propagation rule into their compaction and SAD-construction logic
so end users do not have to choose. The pattern: when an app constructs a sub-SAD whose content the
parent semantically owns, the app automatically applies an equivalent `readPolicy` to the child
unless the application explicitly intends disconnection. End users compose data; the app handles the
privacy propagation. This is a thin contract — the framework provides the mechanism; correct privacy
semantics in user-facing apps live in those apps' construction logic.

## Adversarial framing

Compaction does not weaken tamper-evidence. The reference graph composes the same way it does for
any SAID-referenced sub-SAD ([`sad.md` §Composition by reference](sad.md#composition-by-reference)):

- **Substitution at a compacted position is structurally infeasible.** Replacing a sub-SAD's SAID
  with a different SAID changes the parent's canonical bytes at that position, which changes the
  parent's SAID (and, for chain inception events with nested sub-SADs, also the parent's prefix).
  The parent's SAID is committed to upstream (in `previous`, in anchors, in signatures), so the
  substitution surfaces at the next verifier walk.
- **Expansion is recompute-and-check.** A verifier expanding a compacted position fetches the named
  sub-SAD from any source — local store, peer, gossip — and re-derives the sub-SAD's SAID from its
  content. The expansion is accepted only when the recomputed SAID equals the named one. A hostile
  expansion source can deliver the wrong bytes; the verifier rejects them.
- **Undisclosed positions reveal no content.** A SAID is a hash output; the only information a
  non-expanding consumer learns is that some content with that SAID exists somewhere. The content
  itself is not derivable from the SAID.
- **Sub-SAD reachability is per-SAD-policy-gated, not parent-policy-gated.** A parent's `readPolicy`
  does not transitively protect referenced sub-SADs (see [§Privacy contract](#privacy-contract)).
  The attack surface — an adversary learning a sub-SAD's SAID can fetch it directly, even when its
  parent is gated — is structural and acknowledged. Protection composes one layer up: apps SHOULD
  attach `readPolicy` to children where the parent semantically owns them, so the policy gates ride
  with the content. The framework provides the mechanism (per-SAD `readPolicy`); apps provide the
  policy.

## Resource-amplification defense

A deeply-nested adversarial SAD — one whose expansion graph fans out across many levels with high
branching — can be used as an amplification vector against a naive expander. A submit handler or
replicating peer that recursively expands every nested SAD on receipt would do unbounded fetch /
parse / store work for one submitted byte of input.

Compactor implementations defend by enforcing structural bounds at the storage layer:

- **Two-phase storage.** A SAD object received for storage is parsed and validated in one pass
  without recursive expansion of its sub-SAD references; the second pass dedupes against
  already-stored SAIDs and persists only what is new. Recursive expansion of children is deferred
  until a consumer explicitly requests them.
- **Existence-check before write.** A SAID already present in the object store is idempotently
  accepted without re-storing; an adversary cannot inflate storage by repeatedly submitting the same
  SAD.
- **Bounded fan-out per request.** Replication and expansion paths cap the number of sub-SADs
  traversed in any one operation. A consumer requesting expansion gets the named SAD plus a bounded
  set of its immediate referents; deeper traversal requires further explicit requests.

These bounds are implementation surfaces on the SAD object store and on expanders; they do not
change the structural model in this doc. The model is: compact form and expanded form share a SAID;
expansion is a verifier-controlled operation that fetches named sub-SADs and checks each SAID before
accepting. Which side performs each transform — compaction by the submitting client; expansion
served by the storage service as a convenience — is a service-architecture decision documented in
[`../../../substrate/infrastructure/vdtid.md`](../../../substrate/infrastructure/vdtid.md)
(forward-ref; forthcoming).
