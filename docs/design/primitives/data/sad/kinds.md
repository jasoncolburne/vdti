# SAD Kinds — the identifier catalogue

Every SAD carries a **`kind`** — a versioned string naming its type, which drives structural
validation, tier dispatch, and the role vocabulary it may carry. This doc is the canonical
enumeration of every kind in the system, alongside the related identifier families that share the
same naming scheme.

## The naming convention

Every identifier is **`vdti/{component}/v1/{category}/{name}`** — four segments, always:

- **`component`** — the subsystem that owns it: `kel` / `iel` / `sel` / `event` / `witness` / `log`
  / `doc` / `exchange` / `cred` / `policy` / `gossip`.
- **`v1`** — the schema version.
- **`category`** — the family within the component: `events` / `grants` / `receipts` / `roles` /
  `schemas` / `protocols` / `targets` / `states` / `topics`.
- **`name`** — the specific member.

A `*` below marks a family whose members are listed inline or defined by a feature. There is
**never** a fifth segment: grouping is carried by descriptive names, not extra path depth.

## 1. SAD kinds — the `kind` field

Every SAD carries one of these. **The chain events:**

| Log | Kind                | Members                                               |
| --- | ------------------- | ----------------------------------------------------- |
| KEL | `…/kel/v1/events/*` | `fcp` `icp` `ixn` `rot` `wit` `trm`                   |
| IEL | `…/iel/v1/events/*` | `icp` `ixn` `evl` `ath` `rev` `dth` `trm` `wit` `fcp` |
| SEL | `…/sel/v1/events/*` | `icp` `ixn` `pin` `gnt` `trm` `sea`                   |

**The commitment SADs events reference:**

| Kind                            | What it is                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| `vdti/event/v1/roles/manifest`  | the role-grouped commitment SAD an event names                                        |
| `vdti/event/v1/roles/roster`    | a roster / threshold delta                                                            |
| `vdti/event/v1/roles/witnesses` | a witness-config `{ threshold, signers }`                                             |
| `vdti/event/v1/roles/pins`      | the participating member KEL event SAIDs (an IEL's down-pins)                         |
| `vdti/sel/v1/grants/*`          | a grant-value a SEL `Gnt` seals: `exchange-ml-kem-1024`, `shared-document-governance` |
| `vdti/witness/v1/receipts/*`    | a witness receipt, by witnessed chain: `kel` / `iel` / `sel`                          |

The remaining manifest roles — `anchors`, `delegates`, `payload`, `kills`, and the scalar `clock` —
are carried **inline** in the manifest SAD, so they are not separate SADs and have no kind of their
own.

**The feature / application SADs:**

| Kind                              | What it is                            |
| --------------------------------- | ------------------------------------- |
| `vdti/doc/v1/schemas/*`           | shared-document SADs (`comment`, …)   |
| `vdti/exchange/v1/schemas/*`      | exchange SADs                         |
| `vdti/exchange/v1/protocols/essr` | the ESSR envelope                     |
| `vdti/cred/v1/schemas/*`          | credential SADs (application-defined) |
| `vdti/policy/v1/{group}/*`        | policy documents, grouped by domain   |

## 2. Derivation type-tags

**Not** SADs — the type prefix in a domain-qualified digest `hash('{tag}:…')`, so every conforming
node derives byte-identical output.

| Tag                              | Derivation                                                                                                            |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `vdti/iel/v1/targets/commitment` | an issuer's `Ixn`-anchored commitment to an immutable SAD (a credential is one use) — `hash('…:{issuer}:{sad.said}')` |
| `vdti/sel/v1/targets/revocation` | a `Rev`-anchored kill's target + its lookup-SEL — `hash('…:{owner}:{data}')`                                          |
| `vdti/sel/v1/targets/rescission` | a `Dth`-anchored kill's target + its lookup-SEL                                                                       |
| `vdti/log/v1/states/active`      | a single-tip chain — uses that tip's real SAID; no synthetic                                                          |
| `vdti/log/v1/states/forked`      | the effective-SAID synthetic for a forked chain — `hash('…:{prefix}:{position}')`                                     |
| `vdti/log/v1/states/disputed`    | the effective-SAID synthetic for a disputed chain                                                                     |
| `vdti/log/v1/states/terminated`  | a terminated chain — uses its real `Trm` SAID; no synthetic                                                           |

`revocation` and `rescission` carry **no feature name** — a delegate rescission and a
document-member rescission share `rescission` and never collide, because the `data` (the
grant-instance) differs in `hash('{tag}:{owner}:{data}')`. The primitive never hears "delegate" or
"document." `active` and `terminated` are formalized for a complete enumeration, though only
`forked` / `disputed` are ever derived (the other two states carry a real SAID).

## 3. SEL topics — the `topic` in `derive(owner, topic, data)`

A lookup / content SEL's application discriminator. These are **feature-owned** — a primitive never
enumerates them, keeping features out of the primitive layer.

| Topic                       | Feature                                               |
| --------------------------- | ----------------------------------------------------- |
| `vdti/doc/v1/topics/*`      | shared documents (`comment`, `governance`, `version`) |
| `vdti/exchange/v1/topics/*` | exchange (`exchange`, `receive-key`)                  |

## 4. Gossip topics — mesh channels

The pub-sub channels the witness mesh carries. **Not** SADs, **not** derivation inputs.

- `vdti/gossip/v1/*` — `witness/receipt`, `kel/event`, `iel/event`, `sel/event`, …

## Cross-references

- [`sad.md`](sad.md) — the SAD layer: what a SAD is, the `kind`-required rule.
- [`said.md`](said.md) — the two-pass digest that turns a SAD's canonical content into a SAID, and
  the domain-qualified `hash('{tag}:…')` derivations the type-tags above feed.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the event taxonomy and the
  manifest role model these kinds instantiate.
