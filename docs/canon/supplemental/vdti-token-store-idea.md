# vdti — token store (client-side verification-token cache) — idea capture

**Status.** Idea (Jason, 2026-06-18). Captured for later; not yet spec'd. Composes with the "pin everything to
current state" log-primitive reshape (same session) — see notes at the bottom.

## The idea

A **token store**: a client-side cache of **verification tokens** (`KelVerification` / `IelVerification` /
`SelVerification` — the proof-of-verification objects in `protocol-doctrine.md §Verification tokens`), **keyed by
prefix**, with the **chain tip SAID encoded into the token**.

When a client needs to consume a chain (walk it for a security decision), instead of pulling and walking the
whole chain every time:

1. **Look up** the cached token for that prefix.
2. **Check the effective-SAID at the server** (cheap — one SAID, no full pull/walk).
3. **Match** (server effective-SAID == the token's encoded tip): the chain hasn't moved → **reuse the cached
   token**. Done — no walk.
4. **Mismatch**: the chain advanced → **`since` query** for the new events past the token's tip, and **`resume`**
   the existing token over just those new events to produce a fresh token (incremental verification, not a
   re-walk from genesis).

## Why it fits the existing model

- Verification tokens already exist as the *only* gate to consumed data (`§Operation Categories → Consuming`):
  the cache stores objects that were obtained by full verification, so reuse doesn't bypass the trust boundary.
- **Effective-SAID comparison is already a first-class "resolving" operation** (`§Operation Categories →
  Resolving`, `§Effective-SAID synthetic comparison`): "a wrong answer triggers an unnecessary sync, not a
  security hole." The token-store uses exactly that comparison to decide whether to refresh.
- `resume`-on-an-existing-token is the incremental form of the paged streaming walk (`§Streaming`).

## Soundness caveat to carry into the spec (load-bearing)

The effective-SAID comparison is safe as a **resolving** check (decide whether to sync). But the token-store
uses its result to **skip a walk for a consuming decision** — and some consuming decisions run **to tip**
(loss-of-trust: `del` rescission, credential withdrawal — `leaf-semantics.md`, the rescission/withdrawal walks).
If the effective-SAID the client compares against comes from a **single, possibly-malicious server**, that
server can report a **stale** effective-SAID (matching the old tip) to make the client reuse an outdated token
and **miss a loss-of-trust event** — a freshness attack, not merely an unnecessary-sync miss.

So: the effective-SAID the token-store trusts for a loss-of-trust-sensitive reuse must be as **fresh and
attested** as that decision requires — i.e. sourced from **federation-witnessed / gossiped** effective-SAIDs
(multiple sources), not a single server's claim. This is the same freshness bar the credential non-revocation
proof already carries (`vdti-creds-issuance-revocation-model.md §4.2`). For decisions that don't run to tip the
plain comparison is fine.

## Composition with the pin-everything reshape

The reshape (pin every IEL/SEL event back to the current tip of all dependencies, floored per-chain) makes the
effective-SAID check *more* meaningful: a pin **encodes the dependency tip it was verified against**, so a
cached token's validity reduces to "has any pinned dependency's effective-SAID moved?" The token-store is the
performance complement to pin-everything's correctness: pin-everything adds verification work (a floored pin per
dependency per event); the token-store avoids re-paying it when nothing moved.
