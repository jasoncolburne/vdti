# SAD Kinds — the identifier catalogue

Every SAD carries a **`kind`** — a versioned string naming its type, which drives structural
validation, tier dispatch, and the role vocabulary it may carry. This doc is the canonical
enumeration of every SAD kind. Two sibling identifier families share the same naming scheme and live
in their own catalogues: **derivation tags and SEL topics**
([`../event-logs/tags-and-topics.md`](../event-logs/tags-and-topics.md)) and **gossip topics**
([`../../../substrate/federation/topics.md`](../../../substrate/federation/topics.md)).

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

## SAD kinds — the `kind` field

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

## Cross-references

- [`sad.md`](sad.md) — the SAD layer: what a SAD is, the `kind`-required rule.
- [`said.md`](said.md) — the two-pass digest that turns a SAD's canonical content into a SAID.
- [`../event-logs/tags-and-topics.md`](../event-logs/tags-and-topics.md) — the derivation tags and
  SEL topics that share this convention.
- [`../../../substrate/federation/topics.md`](../../../substrate/federation/topics.md) — the gossip
  topics (mesh channels) that share this convention.
- [`../event-logs/event-shape.md`](../event-logs/event-shape.md) — the event taxonomy and the
  manifest role model these kinds instantiate.
