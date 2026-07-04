# KERI/ACDC vs vdti — how the comparable system handles ex-member issuance / backdating

Ground truth = keripy (`/Users/jason/github.com/WebOfTrust/keripy`), read directly (the sandboxed
research agent couldn't reach it). Specs not re-read this pass; KERI core semantics cited from the code +
foundational model, flagged where corroborated rather than directly read.

## The question
Group X authorizes members to issue credentials. Member A is removed. Can A forge a **new** cred today
claiming old authority? Does closing it force reissuing the legit old creds, or lean on out-of-band infra?

## Q1 — authority-by-membership: chained ACDCs + edge operators (and multisig group AIDs)
ACDC expresses "issuer authorized via X" two ways:
- **Chained credentials** with edge operators **I2I / NI2I / DI2I** — `vdr/verifying.py:336 verifyChain()`.
  **I2I** ("issuer-to-issuee"): the downstream cred's **issuer must equal the upstream (authority) cred's
  issuee** (`verifying.py:365` — `if op == 'I2I' and issuer != creder.attrib['i']: return None`). So "X
  granted A a membership/authority ACDC; A issues downstream creds edged back to it." This is the
  `del`-analog (delegation). (`DI2I` = delegated-issuer; `raise NotImplementedError()` at `:369`.)
- **Multisig group AID** — the group issues **as the group** from the group's own KEL/registry (see Q3).

## Q2 — revocation timing: gate-current (TEL tip), retroactive
`verifyChain` resolves the node (authority) cred's status as **`tever.vcState(nodeSaid)`**
(`verifying.py:376`) — the **current** TEL state, i.e. the latest registry event (`vdr/eventing.py:526
vcstate()` / `:422 state()` build state from the **latest** `sn`/`eilk` ∈ {iss, bis, rev, brv}). There is
**no "as-of the downstream cred's issuance" parameter** — it's read at tip. So **revoking the upstream
authority cred fails the edge for every downstream cred, old and new alike** — gate-current, retroactive,
all-or-nothing per authority-cred. Identical to our DQ1 gate-current floor behaviour.

## Q3 — backdating (the crux): the chained model has the fork; the multisig model resolves it
- **Chained-ACDC model: same fork, not specially closed.** Nothing binds *when* A issued a downstream cred
  to A's authority being current then. `verifyChain` checks only (a) the I2I issuer==issuee link and (b) the
  authority cred's **current** status. So if A's authority cred is **not revoked**, A keeps issuing valid
  downstream creds forever (no issuance-time bound). To stop A you **revoke the authority cred → gate-current
  → kills A's legit old downstream creds too.** No grandfathering. = the fork.
- **Multisig group-AID model: resolves it structurally.** Issue **as the group**: the issuance (TEL `iss`)
  is anchored in the **group's own append-only KEL** via a seal, signed by the group's **current** signing
  threshold. Then:
  - **member rotation** = a group KEL rotation dropping A's key;
  - **old creds** anchored at pre-rotation KEL positions validate **as-of that anchoring key state** (which
    included A) → **stay valid, no reissue**;
  - **A forging new creds** would need to anchor in the group KEL and satisfy the **current** threshold — A
    is out, and A **cannot append to the group KEL's past** (append-only + witnessed) → **blocked**.
  No revocation-kill, no reissue. *(Rests on KERI's foundational as-of-anchoring-key-state validation —
  corroborated from the model + the seal-anchoring in `vcstate`'s `a` seal, not a line I re-read this pass.)*

## Q4 — watcher/first-seen: an equivocation tool, NOT a credential-issuance-time tool
KERI's temporal/ordering anchor is the **first-seen number** (`fn`, `FirstSeenReplayCouples` —
`core/counting.py:62,221`; `core/parsing.py:1837+`), assigned **locally** by each observer when it first
sees a KEL event, used for **duplicity/equivocation detection** (`core/eventing.py:4189+` "maybe
duplicitous"). It is **watcher/witness-local out-of-band state**, and — critically — **the credential
authority/revocation path (`verifyChain`) never consults it.** So KERI does **not** use first-seen to bound
*when a credential was issued*; first-seen solves KEL equivocation, a different problem. KERI has **no**
magic issuance-time tool for the backdating question.

## Bottom line
KERI/ACDC's **chained-credential** authority makes the **exact same gate-current tradeoff** as our
foreign-`grp` fork: block an ex-member only by revoking their authority cred, which retroactively kills
their legit old creds (forced reissue). It has **no** out-of-band trick that beats this — first-seen is for
equivocation, not issuance-time. **But KERI's multisig group-AID model resolves Jason's actual requirement**
(rotate the issuing set without reissue, block ex-members) by making issuance a **governed write on the
group's own append-only chain**, validated **as-of its anchoring position** — old creds grandfather across
rotation, removed members can't append. That is exactly the "issue as the aggregate from its own chain"
direction. **vdti mapping (reshape):** revocable-without-reissue issuance ⇒ **per-cred SELs issued by the issuer
IEL** — issuance = the cred-SEL `Icp` (T1), pinned to the issuer-IEL's position so it validates **as-of issuance**
and grandfathers across rotation; revocation = the cred-SEL `Trm`. **Not** a foreign-`grp(X, group)` splice (the
reshape dropped foreign-`grp` and `policyPin` entirely): a unilateral-claim splice can't be made forgery-proof
end-verifiably; issuing-as-the-aggregate — each cred its own SEL under the issuer IEL — sidesteps the whole fork.
