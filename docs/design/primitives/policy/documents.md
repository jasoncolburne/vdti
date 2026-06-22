# Documents — where policy lives

Part of the policy layer — see [`policy.md`](policy.md) for the language and the two
authorization mechanisms.

Policy lives on **documents**, never on a chain event. A document is a [SAD](../data/sad/sad.md):
an application-defined payload (a credential, an attestation, a signed declaration) that carries,
alongside its content, the policy that authorizes it. This doc states the generic shape every
policy-bearing document shares — the two conditions it can carry, the pin that fixes its issuer
context, and how that pin is anchored so it cannot name a more permissive past. The lifecycle of
any specific document kind (how a **credential** is issued and revoked, for instance) is a feature
layered above this one — see [`../../features/credentials/`](../../features/credentials/).

## A document's two conditions

A policy-bearing document carries up to two policy references (each the SAID of a policy SAD —
[`policy.md`](policy.md)):

- **The authorizing condition — who could issue it.** When a single identity issues the document,
  this condition is **structural**: the issuer's own IEL threshold authorizes the issuance, and
  there is no policy expression to evaluate (the structural mechanism, [`policy.md`](policy.md),
  covers it). The condition becomes an explicit policy only when issuance **spans separate
  identities** (for example `thr(2, [id(A), id(B), id(C)])` — any two of three institutions) —
  there it is evaluated **as-issued** ([`evaluation.md`](evaluation.md)).
- **The acceptance condition — who may present it.** The rule for who may later present or act on
  the document. This is evaluated **current** — against live proof at the time of presentation
  ([`evaluation.md`](evaluation.md)).

The composing logic is the same language in both cases; only how each leaf is resolved differs by
mode.

## The pin — fixing the issuer context

A document carries a **`pin`**: the SAID of the issuer identity's IEL event **prior to** the
issuance. The pin does two things at once:

- It **commits the point-in-time** so a verifier can find and verify the issuer's context — that
  one event transitively commits the issuer's identity state (its members and threshold) and its
  whole delegation chain, because each of those is committed by the events the pinned event builds
  on.
- It is **checked, never trusted.** The document is committed to the chain by an **anchoring
  event** on the issuer's IEL — the event whose `manifest` references the document
  ([`../data/event-logs/event-shape.md`](../data/event-logs/event-shape.md)). The verifier enforces

  ```
  pin == (the anchoring event).previous
  ```

  so the pinned context is exactly the state immediately before the anchoring position. The
  anchoring position is append-only — it cannot be inserted into the past — so the pin cannot
  select a more permissive past while the issuance actually anchors in the restrictive present.

This is why **authority-affecting resolution is judged by the anchoring position, not by the
self-asserted pin.** The pin lives inside the document, where its issuer chose it; the anchoring
position lives on the append-only chain, where it cannot be backdated. Tying the two together with
`pin == anchor.previous` makes the document's claimed context and its real, on-chain context the
same thing. There is no separate machinery to establish "when" — the append-only chain is the
clock.

### Non-circular

The pin is the issuer IEL's tip at issuance. The document's SAID is fixed from its content
(including the pin), and only **then** does the issuer author the anchoring event with `previous
== pin` and a `manifest` naming the document's SAID. So the document commits to a position that
already exists, and the anchoring event commits to a document that is already fixed — no cycle.

## Multi-identity authorization — one pin per authorizing identity

A document whose **authorizing** condition spans separate identities cannot collapse to a single
joint identity (a threshold over devices is not a threshold over identities). It carries **one pin
per authorizing identity**, and **each authorizing identity independently anchors the document**:
each authors its own anchoring IEL event naming the document, and the verifier checks **each
party's `pin == that party's own anchoring event's `previous``**.

- A co-authorizer that does **not** anchor contributes no checkable position and is **not
  credited** — so a malicious primary cannot set a co-author's pin to a permissive past on the
  co-author's behalf. Per-party anchoring closes that the same way single-issuer anchoring does.
- Because each check is `pin == that party's own anchor's `previous``, a co-author's anchoring
  event must be its **very next IEL event** after the document's pins are fixed. Any intervening
  event on that party's IEL moves its tip, so its pin no longer equals its anchor's `previous` and
  its anchor is rejected (the document must be re-cut against the new pin). For an `N`-party
  document, the `N` issuers therefore **quiesce their identities between finalizing the document
  and anchoring it** — a coordination constraint, not a soundness gap.

Single-issuer documents stay single-`pin`; per-party pins exist only for multi-identity
authorization.

## Recursive pinning

A document issued under another document pins, just as a credential pins its issuer. A document
`D` issued under credential `C` carries its own pin to `C`'s position; the verifier finds and
verifies `C`'s context through that pin, and judges authority by `D`'s own anchoring position
(verified `== pin`). The same append-only-chain-is-the-clock rule applies at every level.

## Delegation in a document

A document may be authorized by a **delegate** of an identity — the `del(X, N)` leaf
([`policy.md`](policy.md)). The document commits the **one authorizing path** it was issued under:
each hop's delegating link is recorded on the delegate's own identity, pinning up to `X`, so the
verifier **derives** the authorizing chain from committed data and walks it (up to `N` hops, and
never beyond the verifier-wide work cap — exceeding either denies, fail-secure) — the presenter
furnishes nothing to prune. Per hop the verifier checks that the delegation was granted, that the
grant has not been **rescinded** (a positive lookup, [`policy.md`](policy.md)), and that the
document's anchoring position is an **ancestor of** the rescission cut-off (the grandfather rule:
a document authored before trust was withdrawn stays valid; one authored after does not). To give
several delegators kill-authority over a document, issue it under a threshold spanning their
legs, so every leg lands in the committed chain. The delegation mechanics — the delegate list, the
rescission lookup, and the cut-off — are the IEL primitive's; see
[`../data/event-logs/iel/`](../data/event-logs/iel/).

## Timestamps are advisory

A document may carry feature-level timestamps (an issued time, an expiry). They are **advisory**:
they never decide a structural or cryptographic check. An expired document is *expired* — the
caller inspects that and decides — but all ordering and grandfather questions use the **anchoring
position** (append-only ancestry, with the pin verified `== anchor.previous`), never a clock. The
chain primitives themselves carry no timestamps at all; only feature layers do, and only as
feature semantics.

## Public versus private issuance

Whether an outside observer can tell that an identity issued a particular document is a property
of how the document is located and disclosed, not of the policy layer. A document whose locating
address is derivable from its public content is **discoverable**; one whose content carries a
high-entropy nonce derives an unguessable address and stays **private** until its holder discloses
it. Either way the policy that authorizes the document, and the pin that fixes its context, work
identically. The addressing and privacy rules live with the SEL primitive and the credentials
feature — [`../data/event-logs/sel/`](../data/event-logs/sel/).
