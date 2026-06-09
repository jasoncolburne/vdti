Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

#### Delegation handshake — self-recording

A delegate `D` is born under delegator `X` and **self-records** the link on its own chain, so the
verifier can walk *up* from `D` to `X` without enumerating `X`'s (unbounded, delegate-side)
delegated set:

- `D.Icp.delegating = X`'s **prefix**. `X`'s prefix is known a-priori (no SAID cycle) and
  participates in `D`'s prefix derivation, so `D`'s identity is cryptographically **bound to `X`**.
- A **serial-1 `Evl`, batched with the `Icp`**, evolves `delegating` to the **SAID of `X`'s `Del`
  event** (the event on `X`'s chain that lists `D`'s prefix — known only after `X.Del` exists, and
  still identifying `X` because the SAID resolves to an event on `X`'s chain). Reusing the
  privileged `Evl` avoids the IEL no-local-divergence break a content event would cause; the `Del`
  SAID is one of the things an `Evl` may change (alongside `governance` / `delegation`).

Two structural rules make the handshake unforgeable and keep it atomic (a merge-layer rule
parallel to the SEL `[Icp, Est]` pairing):

- `delegating`-as-SAID appears **only** on a serial-1 `Evl` that follows a `delegating`-`Icp`.
- A `delegating`-`Icp` **must** batch with that serial-1 `Evl` — the two land together or not at all.

Sequencing across the two chains needs **no cross-chain atomic transaction**: `X.Del` (listing
`D`'s prefix) lands first, then `D`'s atomic `[Icp, Evl]` batch references it. The verifier
**consistency-checks** that the serial-1 `Evl`'s `Del` SAID resolves to an event on the chain
`D.Icp.delegating` names.

Both the issuer set and the per-issuer anchor pinning ride on the credential. Say the credential
is issued by `dlg_prefix`, a direct delegate of `iel_prefix_2`, whose IEL authentication is
`kel(dlg_kel_prefix)`.

#### Self-traversing verification

The issuance policy names *delegators*, never their delegates, so the issuer — a delegate — is
**named on the credential**, not pinned into the issuance policy. The verifier confirms delegation
by self-traversal (walking *up* the issuer's own chain) and proves the anchor by a single pinning
rooted at the issuer's own IEL:

```
  issuance policy                              self-traversal (no pinning)
  ──────────────────────────────────────      ────────────────────────────
  thr(1)
  ├─ del(iel_prefix_1, 1)                      (not claimed)
  ├─ del(iel_prefix_2, 1)  ◀── dlg_prefix self-traverses 1 hop up to iel_prefix_2:
  │      dlg_prefix.Icp.delegating   == iel_prefix_2            (consent)
  │      dlg_prefix.Evl[1].delegating == said(iel_prefix_2.Del) (consent, the back-pointer)
  │      iel_prefix_2.Del lists dlg_prefix                      (authorization)
  │      no Rsc of dlg_prefix to iel_prefix_2's TIP            (F — always checked)
  └─ del(iel_prefix_3, 1)                      (not claimed)

  dlg_prefix (the issuer) is NAMED on the credential, not a pinned slot. Its anchor
  rides in a separate pinning, rooted at the issuer's own IEL so the anchoring KEL is
  bound to the delegated identity:

  iel(dlg_prefix)  (identity → authentication → anchor)  anchor pinning
  ─────────────────────────────────────────────────     ────────────────
  iel(dlg_prefix)                       ▷ slot 0  {dlg_iel_marker_said}
  └─ authentication kel(dlg_kel_prefix) ▷ slot 1  {dlg_kel_prior_kel_said}
        └─ prior event (surviving branch); its child anchors the credential at the required tier
```

**No issuance pinning.** The issuance policy's `del(iel_prefix_2, 1)` placeholder is **not
expanded** and pins nothing — the issuer is named, and the verifier confirms delegation by
self-traversing `dlg_prefix`'s own chain (above). The only pinning the credential carries is the
anchor pinning.

**Anchor pinning.** The issuer's IEL policy `iel(dlg_prefix)` walks to two slots in pre-order —
the issuer's `Evl`/`Icp` state-marker (the verifier reconstructs the snapshot that fixes which
authentication state applies) and, through that authentication `kel(dlg_kel_prefix)`, the KEL event
just *prior* to the anchoring event (the anchoring event commits to the credential, so its own SAID
is unconstructable here; see the SAID-cycle note):

```
{
    "said": "{anchor_pinning_said}",
    "pins": [
        "{dlg_iel_marker_said}",     // slot 0 — dlg_prefix state-marker fixing the authentication snapshot
        "{dlg_kel_prior_kel_said}"   // slot 1 — dlg_kel_prefix prior event; its surviving-branch child anchors the credential
    ]
}
```

(slots in pre-order walk order; per issuer there is one anchor pinning.)

**Verifying.** The credential is valid iff *both* hold:

- **Delegation (self-traversal)** — `dlg_prefix` self-traverses 1 hop up its own chain to
  `iel_prefix_2`: its `Icp.delegating` names `iel_prefix_2` and its serial-1 `Evl.delegating`
  names `said(iel_prefix_2.Del)`; the verifier direct-looks-up that `Del` (no enumeration),
  confirms it lists `dlg_prefix`, and walks `iel_prefix_2` to **tip** confirming no `Rsc` of
  `dlg_prefix` (F — always, even for an immune credential). One satisfied delegate clears the
  `thr(1, ...)`. Under `del(X, N)` with `N > 1` the verifier keeps walking up (`X`'s own
  delegator, …) until it reaches the named delegator within `N` hops or denies.
- **Anchor** — evaluating `iel(dlg_prefix)` against the anchor pinning, the `iel(dlg_prefix)`
  leaf reads its pinned `Evl`/`Icp` state-marker (reconstructing the snapshot that binds the issuer
  to its authentication `kel(dlg_kel_prefix)`) and recurses into that authentication policy; the
  `kel(dlg_kel_prefix)` leaf resolves the
  anchoring event `S` (`S.previous == dlg_kel_prior_kel_said`) **on the surviving branch** and
  checks `S` is at the required tier and anchors the credential SAID. Because the anchor is
  reached *through* the delegated issuer's IEL, the anchoring KEL is bound to the delegated
  identity rather than asserted by the credential.

For a multi-issuer policy (`thr(2, [del(A), del(B)])`), the credential names two distinct issuers,
each self-traversing to `A` or `B` and each carrying its own anchor pinning; the composer counts
**distinct issuers** (see *Leaf semantics → `del`*). Verification groups the pinned SAIDs (one
anchor pinning per issuer) by the log they fall on and checks each log's set inline in that log's
single paged verification walk: the SAIDs to check are the positions supplied up front, the walk
validates each event as it pages through, and the caller confirms every required SAID was reached.
So a chain reached on several paths is paged once, not repeatedly.

