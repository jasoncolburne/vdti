# Monitoring — detecting silent takeover

Some compromises leave a fork to trip over; a verifier walking the chain sees the disagreement and
refuses. The dangerous ones leave **nothing structural to catch**: a thief who steals a rotation
reserve can simply extend the chain to their own key, and — on a chain nobody is actively watching —
witnesses sign it as an ordinary next event. There is no competing branch, no dispute, no veto. The
owner finds out late, if at all.

Monitoring is the owner-side answer to that class. It does not prevent the takeover — a structurally
valid rotation cannot be vetoed — but it converts a **silent, indefinitely-undetected** takeover
into a **promptly-detected** one, so the owner reincepts and warns relying parties before the
attacker's key is trusted for long. It is cheap in VDTI because the thing worth watching is already
a first-class, queryable value.

## The one-line detector

Every prefix has an **effective SAID** — a single value that summarizes its current chain state: the
tip when the chain has one clean tip, and a distinct forked/disputed marker when it does not. It is
[locally determinable on any node and queryable by prefix](protocol-doctrine.md#federation-convergence)
— no watcher network, no out-of-band inference.

An owner knows what their effective SAID **should** be: it follows from their own key state and the
last event they authored. So the whole detector is a comparison:

> Fetch the effective SAID for your prefix. If it matches what you expect, nothing has happened. If
> it does not, something advanced your chain that you did not author — a stolen-reserve rotation, an
> unexpected governance change, or a fork. **A mismatch is the alarm.**

That is the entire mechanism. There is no duplicity to reconstruct, no log to diff — the network
already computes and serves the value; the owner only has to notice it changed out from under them.

## Modes

- **Poll.** Fetch-and-compare on a schedule. The simplest form; detection latency is the poll
  interval. Adequate for low-stakes or dormant identities.
- **Persistent connection.** A service holds an open connection with a heartbeat and pushes the
  moment the effective SAID changes. Detection latency drops to propagation time; the heartbeat
  distinguishes "nothing changed" from "the monitor went dark."

Either can run on the owner's own device or on a service acting for them. The service is **untrusted
for correctness** — the owner (or their wallet) still verifies the observed state end-to-end from
the data; the service is trusted only for liveness and to deliver the alert. A lying or absent
monitor costs detection speed, never a false sense of safety.

## Response

On a mismatch, the tool **alerts the owner** — a push to their phone or wallet — and, because the
correct next move is derivable from the owner's key state plus the observed event, it can **prompt
the resolution directly** rather than leaving the owner to diagnose:

> _An unexpected rotation appeared on your identity. Reincept under a new prefix and notify your
> relying parties?_

The key state determines which resolution is correct — reincept after a reserve theft, evict a
compromised member, rotate ahead of a suspected signing-key leak — so the prompt offers the right
action for the situation instead of a raw warning.

## What it does, and what it does not

- **Detects, does not prevent.** A stolen-reserve rotation is a valid event; monitoring cannot stop
  it, and reserve theft remains the point of no return — the prefix is lost and recovery is
  reinception under a new one. What monitoring changes is the **window**: the span in which relying
  parties trust the attacker's key before the owner learns and warns them shrinks from unbounded to
  the monitor's detection latency.
- **Covers the silent class.** The residuals that leave no fork — a stolen-reserve takeover, a
  rotation landing at your next position before yours, a clean adversarial multi-rotation of a
  member chain, a forge-extension of a dormant chain — all surface the same way: an effective SAID
  that no longer matches the owner's expectation.
- **Not a chain rule.** Monitoring is operational hardening, a deployment capability and a piece of
  wallet/service tooling. An owner who does not monitor loses only fast detection, never a
  structural guarantee; nothing in the verification of the chain depends on anyone having watched
  it.

## Relationship to a watcher

This is VDTI's analog of the observer role other systems call a **watcher** — an independent party
that watches an identity's log for activity the owner would not have authored and raises the alarm.
The difference is cost. Where a system that cannot determine divergence locally must stand up
watcher infrastructure to infer it, VDTI's divergence and tip state are a first-class queryable
value, so "watching" collapses to fetching one value and comparing it. The capability is the same;
the machinery it needs is a comparison, not a network.

## Status

The effective SAID and its queryability exist today; this note describes the owner-side layer that
consumes them. The wallet/service tooling — the poller, the persistent-connection service, the
alert-and-prompt flow — is a build item, not a protocol change.
