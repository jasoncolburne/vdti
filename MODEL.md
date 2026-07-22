# VDTI in plain english

**What this is.** Plain-language statements of the design rules — the _narrative_ layer: the
concepts, not the structural encoding. The structural detail lives in the canon (`docs/canon/`).

---

## The shape of the thing

An identity is a **chain**: a numbered list of events that only its controller can extend. Some
events are ordinary activity; some change which keys are in control. **Witnesses** — servers that
vouch for events by signing off on them — make the history hard to rewrite: an event is trusted once
enough witnesses have vouched for it. A **federation** is a group of witnesses that serves a set of
identities together. **Every identity is federation-witnessed — there is no unwitnessed mode**;
witnessing is what every guarantee below rests on.

## Identities and devices

An identity isn't a single key, and it isn't a group of independent people — it's **one controller's
identity** (a person, or an organization acting as one), an **IEL**: a threshold over the **devices
that controller runs**. The smallest one is a single device (a _degenerate_ identity — what a
witness spins up from one key just to send and receive messages). That's the valid floor.

For a real identity you want **three or more devices.** That's where resilience comes from: if a
device is lost or compromised, the survivors vote it out and carry the identity forward — which
needs a governing majority still standing after you lose one, so three is the floor (at two, the
lone survivor can't reach it, and you're frozen into starting over). There's no separate "cold
reserve" doing this job — the guarantee comes from having other live devices on the same identity.
You _could_ hold one device's rotation key somewhere separate, but it doesn't help — it just makes
your own recovery slower. More devices, not split-up keys.

Two boundaries to be clear about. **The threshold is over _devices_, not people** — an IEL's roster
is your own device set, and a device-threshold is not an identity-threshold. Multiple _independent
identities_ — a team of separate people, or several orgs — compose at the **policy** layer (below),
not as members of one IEL; a single controller's device set (one person's, or one organization's) is
one IEL. And these are _recommendations_, not walls the system enforces: nothing can stop two people
from sharing a key or one device from hosting several identities — but the intended model is **one
controller (a person, or an organization acting as one) ↔ one IEL ↔ its devices.**

## The two keys on a device

Each device holds two secrets, both in its hardware — no cold storage, no separate custody:

- The **signing key** — the everyday key, for ordinary activity.
- The **rotation key** — lets _that device_ change its own signing key, e.g. if you suspect the
  signing key has leaked.

The split lets a device heal a suspected signing-key leak by itself. But healing a _fully_
compromised device — where an attacker can use both keys — is the **identity's** job, not the
device's: the surviving devices vote it out. That needs a governing majority still standing after
one is gone, so it works only at **three or more**. On a single-device identity a full compromise is
the point of no return; at two you're still stuck — the lone survivor can't reach the majority to
evict, freezing you into reinception. Three is the floor, and that's why you bind that many.

## The core rule: conflicts

Normally there's one event per step in a chain. Sometimes two show up claiming the same step — a
**conflict**. What happens next is the heart of the design, and it turns on a single question — but
first, one distinction that trips people up:

**Witnesses aren't "the group."** Witnesses are the servers that attest to _every_ event; they're
the ones _applying_ these rules. Where "the group" matters below, it means the identity's **own keys
that had to agree** to author the event — a user's own devices, or the federation's own members —
never the witnesses.

**The question — is the conflict over ordinary activity, or over a key change?**

- **Ordinary activity (content)** → **recoverable.** Witnesses take the first version they see and
  decline the rest, so a second only gets backed if an attacker corrupts enough witnesses to force
  it — and even then the next key change **buries** the loser and the chain reads clean again. An
  ordinary conflict never has to alarm.
- **A key change (sealed)** → **possibly terminal.** You can't un-change a key. Witnesses take the
  first here too — the first-seen rule is the same for key changes as for ordinary activity — so a
  _second_ key change gets backed only when an attacker corrupts enough witnesses to force it,
  leaving their double-signature in the data as proof. When two key changes are both backed, the
  chain is **Disputed**: unrecoverable, and you start over under a new identifier.

That's the whole line: **content is recoverable; a key change can be terminal.** It does **not**
matter whether _one_ key or a whole _group_ authorized the key change — two backed key changes are
terminal either way. A single device rotating its own key and a federation changing its roster are
handled the same at the conflict: first-seen, and terminal if a second is forced through.

**So what is the "one key versus a group" distinction for?** It is what a dispute _proves_ afterward
— the forensics, not the rule. Two backed device rotations (`{rotate, rotate}`) prove the attacker
held that device's signing key _and_ colluded with witnesses. Two backed group acts
(`{roster-change, roster-change}`) prove the attacker subverted the group's quorum _and_ colluded
with witnesses. Same outcome — Disputed, reincept — but the proof tells you _who_ to evict versus
_who_ to walk away from.

**The federation is the pure case** — no ordinary activity, every decision a key-level group act —
so _every_ federation conflict is a potential dispute, never a recoverable one.

(From a single honest witness's seat it's simpler still: it checks its own history and won't sign
twice at one step. We only plan for a second getting backed because we can't assume every witness is
honest — and a corrupted one that signs twice leaves its signature on both as the evidence.)

## What "disputed" means

**Disputed** is when a conflict is visible to everyone in the data — both versions have enough
backing to be trusted. Same word on every kind of chain. Honest witnesses take only the first
version at any step — key changes included — so a second reaching backing means an attacker
_corrupted enough witnesses_ to force it, leaving their double-signatures in the data as proof. What
you _do_ about it depends on which kind of event conflicted:

- **Two pieces of ordinary activity** → recoverable. Your next key change keeps the real line and
  drops the other.
- **Two key changes** → not recoverable. You can't un-change a key, so you start a fresh identity.

## The fingerprint of a conflict

Every chain has a short **fingerprint** of its current state — a compact value two people can
compare to check they're looking at the same identity in the same state. When the chain is healthy
there's a single current tip, and the fingerprint is just _that tip_ — its real identifier. When
there's a conflict there's no single tip, so the fingerprint becomes a **marker** that says _"no
single tip here, and which kind of conflict"_ — temporary or permanent. That's all it needs to say:

- **A temporary conflict** (ordinary activity — recoverable): the marker says _"conflict here, the
  recoverable kind."_ It clears itself — the next key change buries the loser and the fingerprint
  drops back to the single surviving tip.
- **A permanent conflict** (two key changes — not recoverable): the marker says _"conflict here, the
  terminal kind"_ — start a fresh identity. Everyone holding the two clashing key changes reads the
  same verdict, so it doesn't matter _which_ versions each one saw; the outcome (start fresh) is the
  same.

Crucially the marker does **not** try to spell out the competing versions. It can't, safely: if
enough witnesses are corrupted they can keep minting fresh competing versions, so any value that
_listed_ them would keep changing and two honest parties would never settle on the same fingerprint.
A plain marker is **stable** — it doesn't move when a corrupt witness adds another version, and it
doesn't need to, because nobody has to assemble the full set: a recoverable conflict is cleared by
the owner's key change (which buries _every_ losing version at once), and a permanent one just means
"start fresh." Hiding a version still can't help an attacker — someone who has only seen the single
tip computes a _different_ fingerprint from someone who has seen the conflict, so the difference
itself triggers a fetch and the conflict surfaces.

One line: **healthy → the fingerprint is the single tip; conflict → a stable marker of "no single
tip, and which kind" — never a list of the competing versions (that couldn't be kept stable, and
isn't needed).**

## Recovery is just a key change

There's no special "recover" or "repair" operation. When your signing key is stolen, you rotate to a
fresh key, and that single rotation does everything: it locks the thief out (they don't have the new
key) and it buries their activity (anything not on the line leading to your rotation is discarded,
and so is anything built on it). You rotate at the **first** event that isn't yours, so however long
a run the thief piled on, it all hangs off that one point and dies at once — you go for the root,
not their tip. Burying is automatic and complete — everything below your key change that isn't on
the surviving line is dead, and anything grown from a dead point is dead too. No recovery key, no
special event, nothing to prove.

That's the single-device story — you rotating your own key. On a multi-device identity there's a
second kind: when a whole _device_ is compromised (an attacker can use both its keys), the _other_
devices remove it — and that removal is itself a key change too (next section). Same idea at two
levels: **recovery is always just a key change that buries what came before.**

## Kicking out a bad member

On a group identity, when one member is compromised the others remove them with a single governance
change — a change to who's on the roster. Because a roster change is itself a key change, it drops
the bad member and buries whatever mess they made in one step; there's no window where they're
half-out but still dangerous. (This needs at least three members — with two, a compromised member
can freeze you, so two-member identities are flagged "add a third key.")

## Your devices, other people, extended reach — three different layers

Three distinct things get confused as "adding someone," and the design keeps them apart:

- **Your devices → the roster.** An identity's roster is the **devices you control** — a small,
  bounded set of co-signers that can change keys and govern. It is a threshold over _devices_, and
  it stays small on purpose: governance is easy to reason about and cheap to verify. It is
  **hard-capped at 32** as a DoS backstop — the verifier rebuilds the roster in memory as it walks,
  so an unbounded pile of adds would be a resource-exhaustion attack; any change that would push the
  live set past the cap is rejected. The intended size is _small_; the cap is just the backstop.
- **Other people → policy.** A team or an org is **not** members of one IEL — a device-threshold
  isn't an identity-threshold, and you can't collapse several people into one roster. Multiple
  parties are composed one layer up, in **policy**: it builds satisfaction rules like _"any 2 of
  Alice, Bob, Carol"_ or weighted thresholds over the individual identities, and **each identity
  attests independently** on its own chain. That's where richer, weighted, multi-party governance
  lives.
- **Extended reach → delegation.** To hand authority to _many_ downstream parties — sub-delegates,
  document editors, an org's wider reach — you don't grow the roster or write one big policy; you
  **delegate**: a separate, **unbounded** tree of grants, each revocable, with the root always able
  to pull the plug on anything below it.

Rule of thumb: **your devices = the roster (bounded); other people = policy (composed identities);
unbounded reach = delegation.** The roster stays small by design, which pushes scale onto policy and
delegation — the layers built for it.

## An issued artifact rides its owner's identity

A document has its own little log, but every event on it is **anchored** to the identity that issued
it — each artifact event must be pinned to, _and named by,_ a fresh event on the owner's identity
log. The identity log is both the artifact's clock and its authorization: an artifact event isn't
valid unless a matching identity event vouches for it, and an already-recorded identity event can't
take on a new artifact after the fact. Two things fall out, and they're the whole story:

- **An artifact can't go wrong on its own.** To write a competing artifact event, an attacker who
  stole the owner's key has to author a _fresh_ identity event to anchor it — there's no way to hang
  new artifact content off an old, already-sealed identity point. So the attack always shows up as
  activity on the _identity_, at or after the point of compromise — never as a lone artifact fork
  the identity doesn't already reflect.
- **And it heals for free.** Because that malicious anchor sits at or above the compromise, the
  owner's recovery — a single key change at the first bad point — buries it, and every artifact
  event the anchor named dies with it: deadness spreads downward and crosses the anchor. No separate
  repair for artifacts, ever; recovering the artifact _is_ recovering the identity.

So a stolen artifact-signing key is exactly as recoverable as a stolen identity signing key — it
reduces to the identity's own "rotate at the root and bury." Nothing new to learn.

## A credential is a document the issuer anchored, and revocation is a declaration on the issuer's own log

A credential is a one-time, immutable document. The issuer **anchors it** to its own identity log —
one ordinary entry that commits a **domain-tagged hash** of the credential's fingerprint (a tag that
says "this is an issuance," then the fingerprint). That anchor _is_ the proof it was validly issued:
a credential with no matching anchor on the issuer's current log was never really issued. There's no
separate credential-log to maintain and nothing to append (a thief who tries to scribble more
achieves nothing). Issuing is ordinary activity, the cheapest key. **A private credential stays
private because its fingerprint never appears in the clear** — everything on the public log (the
issuance entry, and later a revocation entry) is a _hash_ of it, and a private cred's fingerprint is
unguessable, so an onlooker can't work backward to it.

Revocation is a **declaration the issuer writes on its own identity log** — the same public,
witnessed log a verifier already walks and confirms is current in order to trust the issuer at all.
To revoke, the issuer signs an entry that names the credential (by a matching domain-tagged hash)
and, for a delegate cutoff, how far back to still honor. To check a credential you walk the issuer's
**current** log and look for that name:

- **Named in a revocation entry** → revoked.
- **Not named anywhere on the fully-walked current log** → not revoked. This is a real answer, not a
  guess: being named is the _definition_ of revoked, so "named nowhere" is exactly "not revoked".
  The only way to hide a revocation is to show you a **stale** log — and refusing a stale log is
  exactly what you already do before trusting the issuer at all. So revocation is **fail-secure by
  default**, riding the same freshness check as everything else.

There's also a **fast lookup**: the revocation entry doubles as a small content-addressed object a
verifier can fetch directly (one hop, no walk). A verifier can deliberately **opt down** to it for
speed — the authoritative node (which owns the data) uses it as its fast path, and a busy
third-party server can fall back to it under a time budget. That fast path _can_ miss a withheld
object (it fails open), so it's a chosen trade, never the default: you opt down to it, never up.

This is **better** than the usual decentralized ceiling — KERI writes a revocation event to a log a
verifier reads locally, and a withheld one reads as "issued"; the web's OCSP soft-fails the same
way. Here the revocation lives on the issuer's already-witnessed log, so a careful verifier who
confirms the log is current can't be fooled about revocation without being fooled about the issuer's
whole current state — and if it can't confirm that, it refuses.

## The one guarantee to remember: no silent forgery

The whole point of the system is this: **a break-in big enough to _force a forged branch_ can't
happen quietly.** To make two competing versions both look real, an attacker has to get enough
witnesses to double-sign — and that is exactly what leaves the evidence behind: the witnesses that
had to sign both are sitting in the data doing so. So a forced fork is **always evidenced in the
data** — the double-signed receipts exist and can't be erased from the record. _Delivering_ that
evidence to a given party rides receipt gossip: on a live identity it surfaces as a visible conflict
(disputed); on a quiet one, an old harvested signature can't be replayed onto a live chain (witness
sign-offs only ever move forward in time). The one caveat is **delivery, not existence** — a party
eclipsed from the second branch stays locally unaware until the receipts reach it, so the honest
claim is "the evidence always exists," not "no party can be unaware."

Be precise about what this does _not_ cover. If an attacker steals the deepest reserve — the point
of no return — they don't need to fork at all: they can just _extend_ the chain with a rotation to
their own key. Witnesses sign it willingly, as an ordinary next event. Nothing is forced, so nothing
double-signs — it isn't a conflict, and it isn't stale (the receipts are fresh). The owner has no
way to turn it into a visible dispute — there is no forced fork to surface. Watching the chain
doesn't change that; it only means the owner notices sooner. To a third party the takeover reads as
an ordinary rotation either way. So the honest guarantee is narrower: **no silent _forgery_** (no
forced fork). Catching a reserve-theft takeover rests on **owner vigilance**, not on the witnesses —
watched or not — and reserve theft is unrecoverable regardless, so the answer there is to start
fresh and tell the people who rely on you.

And the outer edge, as always: an attacker who has corrupted _every_ witness vouching for you at
once leaves no honest witness to trace it. That's the same limit every system of this kind has — if
everyone vouching for the truth is compromised, you've lost the trust you were building on.
