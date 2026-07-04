# Federation bootstrap and binding

_Forthcoming._ The full federation doctrine lands here (genesis, witnessing, rebinding); the
cross-primitive framing is in
[`../protocol-doctrine.md` §Federation convergence](../protocol-doctrine.md#federation-convergence).
This stub carries the diagrams ahead of the prose.

## Genesis — a federation is a restricted IEL

A federation is a **restricted IEL** rooted at an `Fcp` inception marker (`Fcp` / `Wit` / `Trm`
only); its roster is witness KELs directly. Each founder witness KEL is `Fcp`-rooted infrastructure
(governed **into** the roster, never self-bound), and its genesis `Fcp → Rot` anchors the federation
IEL's `Fcp` marker (kind-strict, tier-2 ↔ tier-2). Post-genesis governance — add/cut a witness,
rotate — rides a federation `Wit`, anchored by the participating witnesses' KEL `Wit`s (tier-3) and
carrying the federation `clock`.

```mermaid
flowchart TB
  subgraph fed["federation IEL (restricted: Fcp / Wit / Trm)"]
    fFcp["Fcp — inception marker (roster = witness KELs)"]
    fWit["Wit — governance: rotate / add / cut a witness (+ clock)"]
    fFcp -->|previous| fWit
  end
  subgraph w["founder witness KEL (Fcp-rooted infra)"]
    wFcp["Fcp"] -->|previous| wRot["Rot"]
  end
  wRot ==>|anchors, T2↔T2| fFcp
  wWit["witness KEL Wit (t_govern)"] ==>|anchors, T3↔T3| fWit
```

## Rebinding — a user identity binds to a federation

A user identity's initial federation binding rides its IEL `Icp` (`federation` prefix +
`federationPin` SAID). A later IEL `Wit` **rebinds** it to a new federation, anchored by the
members' KEL `Wit`s (kind-strict, tier-3). Trust is **per-federation and non-transitive** — each
event is witnessed by whichever federation was current when it landed.

```mermaid
flowchart TB
  subgraph user["user IEL"]
    uIcp["Icp — federation = F1, federationPin = F1 tip"]
    uWit["Wit — rebind: federation = F2, federationPin = F2 tip"]
    uIcp -->|previous| uWit
  end
  F1["federation F1 (Fcp-rooted)"]
  F2["federation F2 (Fcp-rooted)"]
  uIcp -.->|federation / federationPin| F1
  uWit -.->|federation / federationPin| F2
  kWit["member KEL Wit (t_govern)"] ==>|anchors, T3↔T3| uWit
```
