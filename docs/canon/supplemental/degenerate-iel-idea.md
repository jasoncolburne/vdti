# vdti — supplemental: the degenerate-IEL idea (considered, not built)

**Status: an idea explored for the federation mesh, then NOT built (2026-07-15).** The federation's
inter-node channel is an **ephemeral, signature-authenticated handshake** (forward secrecy —
`docs/design/substrate/infrastructure/mesh-transport.md`), so there is **no published per-witness key
to own**, and this mechanism has no consumer. It is captured here because the thinking is sound and
someone may reach for it — together with the reason it is deliberately **not** general-purpose.

## The problem it solved

A **SEL is owned by an IEL** — a bare KEL cannot own one. So a bare device KEL (a federation witness,
say) that needed to own a value-bearing SEL — a published encryption key — had nothing to root that
SEL on. The idea: give the bare KEL a minimal **degenerate IEL** to own the SEL.

## The mechanism

- A **degenerate IEL** is a single-member IEL — `members = [the one KEL]`, all thresholds `1` — a
  **restricted** IEL whose kind set excludes `Evl` (≈ `{Icp, Ixn, Trm}`). With no `Evl`, and the
  general **post-delta `|roster| ≥ 1`** rule (a lone-member `cut` computes `1 + 0 − 1 = 0`, rejected),
  its roster can neither grow nor shrink — **immutable**, a general rule, no new field.
- It is **derived, not separately incepted**, so it does not break the founder (`Fcp`) bootstrap: the
  device KEL exists first, the degenerate IEL derives from it, and that IEL owns the key SEL.
  "reincept" = re-derive from the recovered KEL (the KEL carries the rotation/recovery story).
- **Deterministic, discoverable derivation.** For the derived IEL to be _found_ (not just
  established), its inception nonce is a deterministic function of the KEL prefix — trading the
  normal nonce's unpredictability for recomputability:

  ```
  nonce = hash('vdti/iel/v1/derivations/degenerate-nonce:{kel_prefix}')
  ```

  Over the **KEL prefix alone** — not the rostered IEL — so a device that sits in several rosters
  reuses **one** degenerate IEL. (Binding to the rostered IEL would multiply IELs per device for no
  security return: the device is the shared trust unit either way, and cross-context key separation
  already comes from the KDF context, not from separate keypairs.) Discovery is then: hold a KEL
  prefix → derive its degenerate IEL → read its key SEL.

## The load-bearing caveat — no privacy

Deriving the nonce from the KEL prefix makes the degenerate IEL **fully enumerable**: anyone holding a
KEL prefix computes its degenerate IEL and key SEL, so the nonce's usual **unpredictability is gone**.
That is acceptable **only** for a value that is _meant_ to be discoverable — a published encryption key
with no privacy to lose. **The security implications of the technique for any other use — anywhere an
IEL must stay unpredictable or private — are NOT considered.** A private variant would have to fold a
**shared secret** into the nonce (so only members can compute it), which this idea does not do.

## Why it is not built

Its one intended consumer — the federation's mesh encryption — moved to an **ephemeral,
ML-DSA-authenticated handshake**: each connection runs a fresh `ML-KEM` exchange and both sides sign
the transcript against their **witnessed** identity
(`docs/design/substrate/infrastructure/mesh-transport.md`). That authenticates the peer from its
witnessed **signing** key and gains **forward secrecy** by using ephemeral key material — so there is
**no persistent published witness key**, and nothing to own via a degenerate IEL. The exchange layer's
other participants are **people**, who already have their own identity IELs (`vdti-area-exchange.md`
§7a). So the degenerate IEL has no live consumer; it is kept here as an idea, deliberately un-built,
and **not** offered as a general-purpose primitive.
