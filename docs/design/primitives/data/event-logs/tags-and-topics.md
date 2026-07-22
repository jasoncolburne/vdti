# Derivation tags and topics — the discriminator catalogue

A content-derived identifier carries a **discriminator** — a namespace-qualifying value that keeps
identifiers minted in different domains from colliding. Neither is a SAD; a SAD's own type is its
`kind` ([`kinds.md`](../sad/kinds.md)). This doc catalogues the two kinds, both on the shared naming
convention `vdti/{component}/v1/{category}/{name}`
([`kinds.md` §The naming convention](../sad/kinds.md#the-naming-convention)):

- a **tag** — the `tag` in a domain-qualified digest `hash('{tag}:…')`, so every conforming node
  derives byte-identical output. Primitive-owned.
- a **SEL topic** — the `topic` field of a SEL inception, one of the values the inception's prefix
  commits to. Feature-owned — or, for a stateful protocol primitive like group-key, that
  primitive's.

## Tags — the `tag` in `hash('{tag}:…')`

Primitive-owned. The `tag` that qualifies the digest so derivations in different domains never
collide.

| Tag                               | Derivation                                                                                                                                                                                                                                                                                   |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vdti/iel/v1/actions/commitment`  | an owner's `Ixn`-anchored commitment to an immutable owned SAD — the direct custody anchor (a credential is one use, `owner` = `issuer`) — `hash('…:{owner}:{sad.said}')`                                                                                                                    |
| `vdti/sel/v1/actions/revocation`  | a `Rev`-anchored kill's target + its lookup-SEL — `hash('…:{owner}:{data}')`                                                                                                                                                                                                                 |
| `vdti/sel/v1/actions/rescission`  | a `Dth`-anchored kill's target + its lookup-SEL                                                                                                                                                                                                                                              |
| `vdti/sel/v1/actions/delegation`  | the topic of a `del(X, N)` hop's positive **delegating-link** lookup SEL — locus derived from the delegator + delegate, pinning the `Ath` grant                                                                                                                                              |
| `vdti/sel/v1/actions/attestation` | the topic of a multi-identity **attestation** content SEL — locus derived from the whole `Icp` (`owner` = the attesting identity, `data` = the attested SAD's `said`, `content: true`), the attestation the policy layer looks up ([`../../policy/documents.md`](../../policy/documents.md)) |
| `vdti/log/v1/states/active`       | a single-tip chain — uses that tip's real SAID; no synthetic                                                                                                                                                                                                                                 |
| `vdti/log/v1/states/forked`       | the effective-SAID synthetic for a forked chain — `hash('…:{prefix}:{position}')`                                                                                                                                                                                                            |
| `vdti/log/v1/states/disputed`     | the effective-SAID synthetic for a disputed chain                                                                                                                                                                                                                                            |
| `vdti/log/v1/states/terminated`   | a terminated chain — uses its real `Trm` SAID; no synthetic                                                                                                                                                                                                                                  |

`revocation` and `rescission` carry **no feature name** — a delegate rescission and a
document-member rescission share `rescission` and never collide, because the `data` (the
grant-instance) differs in `hash('{tag}:{owner}:{data}')`. The primitive never hears "delegate" or
"document." `delegation` and `attestation` differ from those two: each serves **only** as a SEL
inception **topic** (`delegation` derives the delegating-link lookup SEL; `attestation` a
discoverable **content** SEL — the multi-identity attestation), never as a flat kills-target the way
`revocation` / `rescission` also do — but each is a primitive-owned derivation string all the same,
catalogued here with them. `active` and `terminated` are formalized for a complete enumeration,
though only `forked` / `disputed` are ever derived (the other two states carry a real SAID).

Every `hash('{tag}:…')` derivation above hashes the **bytes of its fields in canonical form** — each
`prefix` / `said` as its qualified representation ([`../sad/said.md`](../sad/said.md)), each
`serial` as its **minimal base-10 ASCII** form (no leading zeros) — concatenated `':'`-joined as raw
bytes (the join is its own byte convention, not the JSON/JCS canonicalization `said.md` governs), so
every conforming node computes byte-identical output. The input is specified as **bytes**, not a
fixed text encoding: the canonical form is text today (so the bytes are its UTF-8), but speccing
bytes keeps the derivation stable if the canonical encoding later moves to binary. In the `forked` /
`disputed` synthetic, `{position}` is the **SAID of the fork point**: the verification token's
`divergence_ancestor` for **both** `forked` and `disputed` — the field is **defined
verdict-coupled** (`forked`: the first divergence; `disputed`: the **earliest divergence carrying ≥
2 accepted sealed branches** — the divergence, not the seal positions, so every node computes the
same value wherever the two seals sit; the two coincide except in a nested fork). The synthetic is
content-independent — never a digest over the competing tips — so it is flood-stable. Its **encoded
token carries a distinct type qualifier** — a `states/*` state code, not a SAID's digest code — so a
synthetic and a real tip SAID differ **structurally** (a qualifier mismatch), and the inequality
that fires anti-entropy is never a probabilistic hash collision; the exact qualified byte form is
pinned by the encoding library.

## SEL topics — a SEL inception field

A lookup / content SEL's application discriminator — the `topic` field of its inception, one of the
values the inception's prefix commits to. Opaque to the chain; [`sel/log.md`](sel/log.md) owns the
full derivation and its optional fields. These are **feature-owned** — a base primitive never
enumerates them, keeping features out of the primitive layer. The exceptions are **shared-core
primitives that are themselves stateful**: the group-key primitive (its epoch + roster SELs) and the
receive-key directory (its lookup SEL) own the SELs they ride, so they enumerate their own topics
(the `vdti/groupkey/v1/topics/*` and `vdti/directory/v1/topics/*` rows).

| Topic                        | Owner                                                                                                                                                                                                                       |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vdti/doc/v1/topics/*`       | shared documents (`edit-membership`, `comment-membership`, `read-membership`, `rescission`)                                                                                                                                 |
| `vdti/exchange/v1/topics/*`  | exchange (`chat-membership` — the chat store-auth grant chain; `rescission` — its removal lookup; the `exchange` **message topic** is a ciphertext payload discriminator, **not** a SEL — see the feature's reserved names) |
| `vdti/directory/v1/topics/*` | the receive-key directory (`receive-key`)                                                                                                                                                                                   |
| `vdti/groupkey/v1/topics/*`  | the group-key primitive (`key-epoch`, `roster`)                                                                                                                                                                             |

## Cross-references

- [`../sad/kinds.md`](../sad/kinds.md) — the SAD `kind` field and the shared naming convention.
- [`../sad/said.md`](../sad/said.md) — the two-pass digest that turns a SAD's canonical content into
  a SAID, and the domain-qualified `hash('{tag}:…')` derivations the tags above feed.
- [`sel/log.md`](sel/log.md) — where a SEL inception's derivation is defined and its `topic` field
  consumed.
- [`event-shape.md`](event-shape.md) — the event taxonomy these derivations instantiate.
- [`../../../substrate/federation/topics.md`](../../../substrate/federation/topics.md) — gossip
  topics (the mesh channels), the third non-SAD identifier family on the same convention.
