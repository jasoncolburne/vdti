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
  wFcp["witness KEL: Fcp"]:::kel --> wRot["Rot"]:::kel
  wWit["witness KEL: Wit"]:::kel
  fFcp["federation IEL: Fcp"]:::iel --> fWit["Wit"]:::iel
  wRot ==>|manifest.anchors, T2↔T2| fFcp
  wWit ==>|manifest.anchors, T3↔T3| fWit
  classDef kel fill:#3b1717,stroke:#e03131,color:#fff
  classDef iel fill:#12331c,stroke:#2f9e44,color:#fff
```

The federation is a restricted IEL (`Fcp` / `Wit` / `Trm` only). Solid arrows are chain order (each
event's `previous` points back to the prior); thick arrows are `manifest.anchors`.

## Rebinding — a user identity binds to a federation

A user identity's initial federation binding rides its IEL `Icp` (`federation` prefix +
`federationPin` SAID). A later IEL `Wit` **rebinds** it to a new federation, anchored by the
members' KEL `Wit`s (kind-strict, tier-3). Trust is **per-federation and non-transitive** — each
event is witnessed by whichever federation was current when it landed.

```mermaid
flowchart TB
  uIcp["user IEL: Icp"]:::iel --> uWit["Wit — rebind"]:::iel
  kWit["member KEL: Wit"]:::kel
  F1["federation F1"]:::iel
  F2["federation F2"]:::iel
  uIcp -.->|federation / federationPin| F1
  uWit -.->|federation / federationPin| F2
  kWit ==>|manifest.anchors, T3↔T3| uWit
  classDef kel fill:#3b1717,stroke:#e03131,color:#fff
  classDef iel fill:#12331c,stroke:#2f9e44,color:#fff
```

Solid arrows are chain order (`previous` points back); dotted arrows are the `federation` /
`federationPin` binding; the thick arrow is `manifest.anchors`.
