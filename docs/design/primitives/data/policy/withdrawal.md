Part of the policy primitive group — see [`policy.md`](policy.md) for the DSL surface, grammar, and reading order.

## Withdrawal

A credential can be **withdrawn** — invalidated after issuance — without mutating the credential
itself (it is immutable and content-addressed). Withdrawal works by anchoring a derived digest,
exactly the way the credential's own SAID was anchored:

```
withdrawal_digest = qb64( Blake3-256( "vdti/withdrawal:" ‖ said(credential) ) )
```

To withdraw credential `C`, an authorized party anchors `withdrawal_digest(C)` on a KEL. The
verifier — having already walked the issuer's KEL(s) during the anchored check — scans that same
verified walk **to tip** for the digest. Because the digest is itself anchored and tamper-evident,
withdrawal inherits the same end-verifiability as issuance: no revocation list, no online check.
All withdrawal checks are **identity-current (tip)** — consistent with F evaluating `del` at tip;
no credential-committed pinning is needed (pinning only ever served frozen *issuance* evidence).

Withdrawal is configured by **two fields on the credential itself** — *not* on the generic `Policy`
SAD (which has no withdrawal state, so identical Policy expressions still dedup): an optional
`withdrawal: Option<String>` DSL expression and an `immune: bool` flag. The three modes mirror the
kels poison model:

- **`withdrawal: None`, `immune: false`** (default) → **soft, per-contribution.** A withdrawal
  anchor by one of the **issuer's own authentication KELs** removes *that* contribution; `C` is
  withdrawn only when withdrawals drop the issuer's authentication below its threshold. A single
  key removes only its own anchor (no griefing surface), revocation still works once enough
  withdrawals cross the threshold, and it is symmetric with issuance.
- **`withdrawal: Some(expr)`** → **hard.** `expr` is evaluated as a full policy against the
  withdrawal anchors found at tip; if satisfied, the **whole** credential is unsatisfied. This is
  where admin / third-party kill lives ("2-of-3 admins withdraw") — a named authority that is
  **not** the issuer can hold the withdrawal right.
- **`immune: true`** → **no withdrawal checks ever.** The verifier does not scan for a withdrawal
  digest at all. For credentials whose validity must not depend on a later anchor (e.g. a one-shot
  attestation); permanent and unrevocable, a stated trade-off.

`immune` gates **only** this withdrawal scan. It is **orthogonal to delegation**: the F rescission
tip-walk (confirming no `Rsc` removed a presented delegate, inside `self_traverses`) is **always**
performed, even for an immune credential. The two are independent tip-walks — F is a structural
validity check that never opts out; the withdrawal scan is the one and only thing `immune` skips.

When the verifier finds a satisfying withdrawal anchor (soft: enough to cross the issuer's
authentication threshold; hard: `expr` satisfied), `evaluate_anchored_policy` returns `Ok(None)`:
the credential is structurally well-formed and validly issued, but withdrawn — so no proof token is
minted (a withdrawn credential must not yield a `PolicyVerification`).

> **TODO (pending [event-shape.md](../event-logs/event-shape.md) and the credential shape).** The
> withdrawal-digest label (`"vdti/withdrawal:"`), the anchor-scan step (reading the issuer-KEL
> walk's token for the digest), and the `withdrawal` / `immune` field placement on the credential
> are provisional pending the settled credential shape. The three modes (soft / hard / immune) are
> grounded in the kels poison model (kels `docs/design/features/creds.md` §Poisoning).

