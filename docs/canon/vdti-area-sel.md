# vdti — area note: SEL (single-owner data log)

**Status: FIRST CUT (2026-06-20).** This note **supersedes design-pass §3** (and the SEL-inception parts of
§2.1/§2.2) for the SEL primitive — it folds in `inv 15` (inception tier + the fallback serial-1 floor) and the document-layer
decisions (cred-as-a-SEL, SEL `Trm`, no registry). **Note:** §2.1's `≤1 Ixn per SEL` rule + seal-bounding still
*hold* — only its inception-pair description changes. Driven *down* from the document/policy area, exactly as the
document-first sequencing intended.
**Invariants referenced:** [inv 2] single-locus, [inv 3] layers-isolated, [inv 4] manifest-up/pin-down,
[inv 5] pin-floored, [inv 10] lookup-SELs, [inv 13] divergence-scoped-to-T1-content, [inv 15] inception/pin.

## Sources
- `vdti-log-primitive-reshape-design-pass.md` §2.1, §3 — the prior SEL model; **partially superseded here**
  (the "every SEL is `Icp`+`Evl`" + "no SEL `Trm`" claims).
- `vdti-area-document-policy.md` §A/§F + `inv 15` — the driving decisions.

## 1. Locked-candidate — the current SEL model
- **SEL = a single-owner data log.** Owner = exactly one **IEL** (its prefix). No policy, no roster, no
  multi-party governance internally [inv 2]. Layers isolated: a SEL pins/anchors only its owner IEL [inv 3].
- **Prefix = the `Icp`'s whole-content digest** over its populated fields — **`owner`** + `topic` + `data`
  (shorthand `derive(owner, topic, data)`, **not** a side-tuple hash: it's the same whole-content prefix every
  event has, so **any** field on the `Icp` enters it — adding a `pin` would break recomputation). **`owner`** =
  the owner IEL prefix, **`Icp`-only and immutable** (a SEL has one owner for life). `topic` = an application
  discriminator; `data` (**optional**) = nonce (non-discoverable / private) or meaningful bytes (discoverable /
  recomputable — e.g. a rescission's `data=P`). **`topic` + derivation replace KERI's registry identifier** — no
  registry object exists.
- **★ `data` entropy is load-bearing (clear rule, Jason 2026-06-20).** When `data` is used for an **unpredictable**
  prefix (a *private* SEL — the nonce that makes the prefix unguessable), it **MUST be high-entropy**. Otherwise an
  attacker brute-forces it, recomputes the prefix, and **confirms / de-anonymizes** the locus (and a predictable
  prefix weakens collision/uniqueness too). **Digesting `data` does NOT substitute** — a hash of low-entropy input
  is still brute-forceable; the *input* must carry the entropy. (Parallels the IEL `Icp` `nonce` requirement.)
  Where `data` is **deliberately discoverable** (a lookup-SEL `data = said(grant-instance)`, e.g. `data=P`), unpredictability is
  *not* the goal — the protection there is **owner-rooting** (only the owner IEL anchors events at the locus →
  prediction ≠ forgery), not entropy. *(Propagate to the doctrine prefix-derivation rules.)*
- **Classification criterion = blind-recomputability, NOT discoverability (F10).** A SEL is a **lookup SEL**
  *iff* a verifier **blind-recomputes its prefix** `derive(owner, topic, data)` from data it already holds; a
  **content SEL** is one you are *handed*. **A credential is neither — it is a direct-anchored SAD, not a SEL**
  (issuance SEL dropped, B1 fail-secure rework 2026-07-09; the cred block below): the issuer anchors an **issuance
  commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** on its own IEL via an `Ixn`, and *that* anchor is
  the validity proof — the holder **presents** the cred, it is **never looked up by address**. **Revocation** is read
  from a **`kills[]` declaration** on the issuer's **witnessed** IEL `Rev`/`Dth` (fail-secure by default, riding
  inv 8's freshness gate), with a content-addressed **lookup SEL** giving a fail-open fast path — never by walking a
  cred-SEL (there is none). *(This **reverses** the create-on-revoke two-SEL model — cold/warm re-review-2 F1 broke
  its `attribute-all` fail-secure escape hatch, so revocation moved onto the witnessed log where the fresh walk
  already reaches it; see the cred block.)*
  - **A credential is an anchored SAD — no issuance SEL (B1 fail-secure rework 2026-07-09).** A cred is an
    **immutable SAD**, issued once, never appended to, **never looked up by address** — so, unlike revocation, it
    needs **no lookup object and no cred-SEL**.
    - **Issue** = the issuer anchors the **issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`**
      (a flat, `:`-delimited, domain-qualified hash — **no two-pass**, there is no SEL) on its own IEL via an **`Ixn`**
      (`manifest.anchors` names it). **That anchor is the validity proof** — an issuance commitment with no resolvable
      anchor on the issuer's **fresh** IEL is **not validly issued**. **As-of = the anchoring position** (append-only,
      backdate-proof — inv 5). The cred body is a SAD, **presented by the holder** (or stored by SAID for a public
      cred). Issuance stays **T1 content** (`t_use`; forging one is a single revocable assertion — inv 15 F-I) riding
      an ordinary IEL `Ixn`. **Custody rule (written down):** **direct-anchor an immutable SAD that is *presented*;
      SEL-wrap anything *mutable* or *looked-up-by-address*** — the cred is the first direct-anchor case (not an
      arbitrary exception); the revocation/rescission lookup SELs stay SEL-wrapped (they're looked up). *(Drops the
      `Icp`/`Pin`/`v1` cred-SEL scaffolding **and the "inert serial ≥ 2" DoS machinery** — no cred-SEL to junk;
      **keep-condition:** a cred needing mutable per-cred state beyond revocation would need a log — the model is
      immutable + binary-revocable, so nothing to log.)*
    - **Revocation = a `kills[]` declaration on the issuer's witnessed IEL + a content-addressed lookup SEL.** To
      revoke, the issuer signs a **`Rev`** on its own IEL and **declares** the target in a flat **`kills[] =
      [{ target, bound? }]`** entry (area-iel §1; a cred revocation has **no `bound`** — binary), **alongside** the
      unchanged `anchors[] = [said(Trm)]`. **`target = hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`** — a
      flat, `:`-delimited, domain-qualified hash the walk computes directly (hash a string) and matches. **The lookup
      SEL** is a separate `{Icp, Trm}` (inv 15 forces two events) built from `Icp{owner, topic, data}` (same fields),
      its **prefix** and **said** computed the **usual two-pass** (pass-1 digest = the fetch prefix; pass-2 = the
      said). **`target` (flat hash) ≠ `prefix` (pass-1) ≠ `said` (pass-2)** — all computable by a holder from
      `{owner, topic, data}`, **none derivable from another** (decorrelated), so the public `kills[]` target does
      **not** reveal the SEL's address. `kills[]` carries the **flat target**, not `said(Trm)` (which isn't
      precomputable — the `Trm`'s pin points at the not-yet-authored `Rev`; that non-precomputability is *why* `kills`
      is a distinct role from `anchors`). The `Trm` (recomputable-`Icp` address, no pin/anchor; the `Trm` is the
      anchored v1) carries **only its pin** (`Trm.pin = Rev.previous` — one-before, since the `Rev`'s SAID doesn't
      exist yet when the `Trm` is authored), sealed on arrival via the `Rev`'s `anchors[]`. Legitimacy = the issuer's
      **witnessed** `Rev` — a non-issuer can't declare it (**no forged revocation**), and a witnessed `Rev` + a
      sealed monotone `Trm` can't be rolled back (**no silent un-revocation**). A `Trm` whose target is in **no**
      `kills[]` is a terminated SEL that **isn't a revocation** → reads not-revoked; "not in any `kills[]`" **is** the
      definition of not-revoked (no coverage rule, no hole).
    - **Two reads; fail-secure is the DEFAULT.** (Both are the **verifier's** read strategy over structurally-valid
      data — revocation is **not the store's concern**; R6.) **Found-fast-path (shared, both modes):** try the
      content-addressed lookup first — **found + validated → fast refuse** (early-exit, skip the manifest scan;
      *validated* = the `Trm` sits under a real, sealed, owner-authored `Rev`/`Dth` of the right kind — R2 — and a
      validated kill is monotone, so refusing on it is fail-safe, needing only the roster up to that `Rev`/`Dth`);
      **not-found → fall back** to the `kills[]` walk (fail-secure default) — or best-effort not-revoked **only** if
      the verifier has opted fail-open / timed out. **`Trm`-existence is a *conservative proxy* for the authoritative
      `kills[]`-membership** — `kills[]` (the declaration) and `anchors[said(Trm)]` (the lookup object) are two
      independent roles on the `Rev`/`Dth`, coinciding **only for a canonical revocation** (both authored together) —
      so the fast-path is **not walk-equivalent**: a `Trm` with no matching `kills[]` entry → over-refuse (fail-safe);
      a `kills[]` with no `Trm` → the fast-path misses it, but the authoritative `kills[]` walk catches it (both
      divergences are issuer-self-inflicted and land safe). Not an IEL/SEL rule, not a `vdtid` obligation.
      - **Fail-secure walk (default):** walk the issuer's **fresh** IEL over `[issuance-position .. tip]`,
        forward-matching your computed `target` against each `Rev`/`Dth`'s `kills[]` (reading `bound` from the same
        entry for a rescission). **In some `kills[]` → revoked/rescinded; in none on the fully-walked fresh chain →
        not revoked** — being in a `kills[]` **is** the definition of revoked, so "in none" is exactly "not revoked",
        nothing to miss. **Both range ends are load-bearing (R1):** the floor is the **earliest** issuance-commitment
        anchor — the **cred feature layer** resolves it as the *first* match on the fresh inception→tip walk and
        treats a later re-anchor as **inert** (never trusting a supplied/cached later position), else a T1 `Ixn`
        re-anchor after a T2 `Rev` would move the floor past the kill (a tier inversion the fresh tip can't catch);
        the ceiling is the **fresh tip**. The IEL still *accepts* the re-anchoring `Ixn` as structurally valid — the
        floor rule is a **cred-layer** rule (§Layering — the chain stays topic-opaque), cred-only (grant-epoch-scoped
        kinds get a fresh locus, not a moved floor). **The cred walk also enforces topic↔kind (R2):** a
        `CRED_REVOCATION_TOPIC` target counts **only** in a `Rev` (`t_govern`) — a match found only in a `Dth` is
        **rejected** (the IEL/SEL stay topic-opaque; this is a cred-layer check). This **rides inv 8's freshness
        gate**: the only way to hide a revocation is to show a **stale** IEL, which is exactly what a verifier already
        refuses when trusting the issuer at all — so kill-freshness == authority-freshness, no better and no worse.
        Streamed with the subject(s)-in-scope (delegation pattern, §1 imposes / area-iel:153), O(subjects) memory,
        O(range) time, **no lossy cap**. **Self-contained for cred + delegate** (the `bound` is public on the IEL,
        un-withholdable — never fetches the lookup SEL); a **doc-member** rescission's `bound` is **gated** (its `Trm`
        commits the rescind-doc), so *that* walk **fetches** the gated doc for the bound (withheld → conservative
        don't-honor — R3; multi-party §1).
      - **Fail-open lookup (opt-out):** build the `Icp{owner, topic, data}` → two-pass → the SEL **prefix** → fetch
        the lookup SEL (content-addressed, no index). **Found + validated → revoked** — validate the `Trm`'s anchoring
        event (a real, sealed, owner-authored `Rev`/`Dth` of the **right kind** — a `CRED_REVOCATION_TOPIC` object's
        `Trm` must sit under a `Rev`, R2); **not-found → best-effort not-revoked** (a withheld / unreachable object
        reads not-found). For a rescission's `bound`: follow `Trm.pin` (= the `Rev`/`Dth`'s `previous`) → the event
        that **extends** it → confirm its `anchors[]` names this `Trm` → read its `kills[]` entry. A verifier opts
        **down** to fail-open (an app server on a walk-timeout — document-policy §F); it never opts up.
    - **Addressing + privacy — `cred.said` appears NOWHERE raw on the public IEL (F2 / F3, inv 16).** Everything is a
      hash of it: the issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`, the kill target
      `hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`, the lookup SEL's prefix/said (two-pass over an `Icp`
      whose `data = cred.said`), and `said(Trm)` (opaque — needs the `Trm` body). A non-holder recovers none of them
      without the **preimage** `cred.said`, and a **private** cred's `cred.said` is high-entropy (body `nonce`) → not
      brute-forceable; the kill target derives from the **preimage**, never from a public hash, so seeing the issuance
      commitment doesn't yield the kill target. The read is **confirm-a-known-subject, not bulk-enumerate:** you can
      only *confirm* a subject whose cred you hold; you can't invert. A **private** cred's body is **not published**;
      a **public** cred's is, and public revocation status is correct. **The private cred's lookup-SEL `Icp` is never
      published either (R4):** the `Icp` carries `data = cred.said` **raw**, so it must never be stored/served — a
      holder **recomputes** it locally (it holds the cred → knows `cred.said`) to derive the prefix, then fetches
      **only the pin-only `Trm`** by address. So no replica ever holds `cred.said` raw, and the "CLOSED" claim rests
      on **both** halves: a non-holder can't *compute* the address **and** the data-bearing `Icp` is never *published*
      for a replica to hold. *(Build-constraint — a **submission/serve** discipline distinct from the §1j by-SAID
      `kind` filter: the `vdtid` write/serve path stores/serves only the pin-only `Trm`, so a **by-prefix** fetch of a
      revocation/rescission lookup SEL returns the `Trm`, never the data-bearing `Icp`. The §1j filter closes the
      separate by-SAID event-harvest vector; it does not itself block an `Icp` submission — but only a
      `cred.said`-holder can produce that `Icp`, so a stray submission self-reveals only.)* *(Neither the cred anchor
      nor the lookup SEL is witnessed directly — §2c Decision 1; the fail-secure guarantee rides the issuer IEL's own
      witnessing.)*
  - **Lookup SEL** (revocation / rescission): built from `Icp{owner, topic, data}` with the **usual two-pass**
    prefix/said — the `data` is the **grant-instance** (cred: `cred.said` @ `CRED_REVOCATION_TOPIC`; delegate:
    `said({ grant: said(Ath), delegate: P })` @ `DLG_RSC_TOPIC`; doc-member: `hash(G | said_b)` @ `DOC_RSC_TOPIC`),
    so a **re-grant** after a kill gets a **fresh** locus (each grant epoch → its own). The `kills[]` **target** is
    the separate flat hash `hash('{topic}:{owner}:{data}')` (≠ prefix ≠ said — decorrelated; §cred block). The `Icp`
    can't carry a pin — the **universal** recompute constraint — so the lookup-SEL is `{Icp, Trm}` — the **`Trm` is
    the kill**, `Trm.pin = (Rev/Dth).previous` (one-before, since the anchor's SAID doesn't exist yet at authoring).
    **Bound placement is per-feature (R3) — the primitive says only: a `Trm` commits whatever its manifest commits.**
    **Cred — no bound**, the `Trm` carries **only its pin**. **Delegate — bound public in the `Rev`/`Dth`'s
    `kills[]`** entry (un-withholdable — the fail-secure walk reads it directly), the `Trm` carries only its pin.
    **Doc-member — bound in a gated rescind-doc *committed by the `Trm`*** (`kills[]` carries only the **blind
    target** — a public bound would identify the member), so *that* `Trm` legitimately commits a manifest and its
    walk **fetches** the gated doc for the bound (withheld → conservative don't-honor). So "the `Trm` carries only its
    pin" / "self-contained, never fetches" are **cred+delegate** statements, **not** universal. **Count = `t_govern`** (revocation, `Rev`) /
    **`t_authorize`** (rescission, `Dth`). **Always sealed:** the `Trm` is **IEL-`Rev`/`Dth`-anchored** (the
    kill-anchor's `manifest.anchors` names the `Trm`), sealed on arrival — a kill is monotone, so there is **no
    delayed un-kill**. Restoring the subject is a **fresh grant** (a fresh locus), never a retraction. Protected by
    **owner-rooting**, not entropy. *(Buried events are still retained (keep-all-data) — see vdtid §5 — but never as
    an un-kill mechanism.)*

### The three axes — never conflate them (count⊥tier kept; delayed-`Trm` reversed 2026-06-21)
1. **Count** = how many owner-IEL members must authorize (delivered via the **anchoring IEL event's** signatures):
   `t_use` (content / issue) · `t_govern` (terminate / revoke / close) · `t_authorize` (grant / rescind a delegate or doc-member).
   *(No `t_recover` — there is no repair.)*
2. **Tier** = is the **rotation reserve** required? (the reserve held *apart* from the signing key) —
   **T1** = signing key only (**content only**) · **T2** = + rotation reserve (establishment-mutation /
   authority-grant / **any kill** — a kill must be *sealed*, and a seal is a governance act). Set by
   **danger-of-forgery OR need-for-permanence**, **⊥ count** — count is a dial, tier is set by kind (a content `Ixn`
   is T1 even at a high `t_use`). *(No T3 — the recovery reserve is gone; every key change is T2.)*
3. **Anchor → finality follows the KIND (2026-06-21)**: a content **`Ixn`** rides an IEL **`Ixn`** → **first-seen /
   buriable** (the **divergeable content kind**, as is the floor `Pin` §4 — an unsealed window is fine, content is recoverable anyway); a
   **kill** (`Trm`) rides an IEL **`Rev`/`Dth`** → **sealed on arrival** (it *must* be — a kill is
   monotone). **There is no delayed kill.** The anchor **kind** matches the event kind (kind-strict, inv 4); tier-elevation is then a trivial floor, not the check. *(The round-3 `content: user |
   governing` flag is **removed** — its only intended user was the federation clock, which is **not a SEL kind**:
   it's an **inline timestamp on each federation `Wit`'s manifest** (federation §1f). `Ixn` is plain content. Finding 8/9.)*

### Exhaustive taxonomy

  | SEL kind | Count | Tier | Anchored by (IEL) | Finality | |
  |---|---|---|---|---|---|
  | `Icp` | `t_use` | **T1** | — (not anchored; v1 via `previous`) | delayed | `owner` (the owner IEL prefix, immutable) + `topic` + `data` (opt — the recompute input for a lookup SEL, e.g. `said(grant-instance)` for a kill locus); **no manifest, no `pin`** (stays recomputable for lookup). Establishes the SEL; the pin rides the serial-1 v1 (a `Trm` for a lookup SEL, a `Pin` for an incept-and-sit doc author). |
  | `Ixn` (content) | `t_use` | T1 | `Ixn` | delayed | content SAD(s) + re-`pin`; **≤1 per SEL per IEL `Ixn`**; the **divergeable/first-seen content kind** (tier-1/buriable — as is the floor `Pin`, §4). |
  | `Trm` | **`t_govern`** (revoke) · **`t_authorize`** (rescind) | **T2** | **`Rev`** (`t_govern`) / **`Dth`** (`t_authorize`) | **sealed on arrival** | The SEL **kill** (the kill-anchor's `manifest.anchors` names the `Trm`). `Rev` = a **revocation lookup-SEL** `Trm` (a cred's revocation) / app-SEL closure; `Dth` = a delegation **or doc-membership** **rescission** (lookup-SEL `{Icp, Trm}`). The `bound` is **per-feature (R3)**: cred **none**; **delegate** — the `Trm` carries only its pin, `bound` public in the `Dth`'s `kills[]`; **doc-member** — `bound` in a **gated rescind-doc committed by that `Trm`** (`kills[]` carries only the blind target). **Always sealed** — monotone, terminal-on-divergence (can't be overturned **F-B** / un-done **LF1**). The killed thing = which SEL its `Trm` extends, named by `kills[].target`. |
  | `Gnt` (grant) | `t_authorize` | **T2** | **`Ath`** | **sealed on arrival** | The doc-governance **grant** — the **additive twin of `Trm`** (opens editor/commenter validity periods; the `Gnt`'s `manifest` names the gated grant-doc `G`). Anchored by the owner IEL's **`Ath`** (kind-strict — an `Ath` anchors **only** `Gnt`s). Sealed / seal-advancing, **non-buriable** — walked back by a rescission (a SEL `Trm` via `Dth`, or reincept), never overturned. Doc-governance SELs only (a plain SEL has no membership). |
  | `Pin` (floor re-pin) | `t_use` | **T1** | `Ixn` | delayed | Re-pins the SEL→owner-IEL floor, carrying only the top-level `pin` (no manifest/seal). The **fallback serial-1 floor** — used only when inception batches no other event (the `Icp` can't hold a pin). **Not** seal-advancing — promotes nothing; buriable like content. |

**Dropped in the first-seen pivot (2026-07-08):** `Fld` (the SEL re-seal — no repair ⇒ no page-atomicity
requirement ⇒ no `Fld` bounding; finality still floors to the owner IEL via the `pin`) and `Rpr` (no repair event).
So the SEL is **5 kinds** — `Icp`/`Ixn`/`Pin`/`Gnt`/`Trm` — with `Gnt`/`Trm` the seal-advancers and `Ixn`/`Pin`
the tier-1 buriable kinds.

- **Imposes on the IEL side:** an IEL **`Ixn`** anchors a SEL's **serial-1 (v1) event** (a `Pin` for issue-and-sit,
  the first content `Ixn` otherwise) via `manifest.anchors` — the **`Icp` is never anchored**, it rides via
  `v1.previous` — **and, for a credential, anchors the issuance commitment `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`** (an immutable SAD, no cred-SEL — the
  anchor *is* the validity proof; issuance SEL dropped 2026-07-09); a SEL **kill** is anchored by an IEL
  **`Rev`/`Dth`** via `manifest.anchors` — a revocation lookup-SEL `Trm` (a cred's revocation) by a `Rev`
  (`t_govern`), a rescission lookup-SEL `Trm` by a `Dth` (`t_authorize`), sealed; the `Rev`/`Dth` also carries the
  **`kills[]`** declaration (`{target, bound?}`) naming the killed locus (area-iel §1). **The kill rides
  a `Rev`/`Dth` because the back-check demands it** (a SEL `Trm` is valid only anchored by a `Rev`/`Dth` — inv 4), not
  a role label. So **content rides the IEL `Ixn` rail; kills ride the IEL `Rev`/`Dth` rail** (roster/threshold changes ride
  `Evl`). **The matrix is kind-strict (C1):** a `Rev`/`Dth` anchors **only** `Trm`s, an `Ath` **only** `Gnt`s, an `Ixn` **only** content/v1
  — tier-elevation is an *additional* floor, not the check (else a
  T2 `Rev`/`Dth` could host T1 content onto the durable rail — inv 4). The IEL `Ixn` stays **T1**, the `Rev`/`Dth` is **T2** — count ⊥ tier still holds. *(The federation clock is not
  an SEL event at all — it's an inline timestamp on each federation `Wit`'s manifest; federation §1f.)*
- **The SEL's seal-advancers are `Gnt`/`Trm`; trust-finality floors to the owner IEL.** A content `Ixn` sits in the
  SEL's unsealed window until the SEL's next **`Gnt`/`Trm`** — then permanent (and buriable until then); `Gnt`/`Trm`
  are the SEL's seal-advancers (`previousSeal`). A **plain** content SEL (no `Gnt`/`Trm`) never self-seals — its
  **trust-finality floors to the owner IEL's seal via its `pin`** (it holds no trust-seal of its own), and a content
  fork on it resolves **cross-layer** (the owner IEL buries the fork and the dead line descends across the anchor —
  below). *(There is no SEL `Fld` re-seal — no repair ⇒ no page-atomicity requirement ⇒ no `Fld`; finality floors down.)*
  A **kill** is **`Rev`/`Dth`-anchored → sealed on arrival**, owner-proof immediately and terminal-on-divergence.
  **There is no delayed kill.**
- **Divergence resolution — first-seen + cross-layer** [inv 13]: **content `Ixn` and the floor `Pin` are
  buriable** (both T1, first-seen); a `Gnt`/`Trm` (the seal-advancing SEL kinds) is **never overturned**. A content
  fork resolves cross-layer: the **owner IEL's burying seal** drops the loser and the dead line **descends across the
  anchor edge** (deadness-descends) — there is no SEL repair event. Node-agnostic, **data-local** condition: **≥ 2
  branches each carrying an accepted sealed event past the fork → disputed** (any verifier walks it — inv 13/17; the beacon
  propagates the branches, it does not decide). E.g. `{Trm, Ixn}` → the `Trm` is the single sealed branch and **wins
  on tier-rank**: the kill stands, the content buried non-canonical. An adversary's `Trm` in a competing branch → a
  second sealed branch → disputed → reincept.
- **Cross-layer anchor rules — the IEL is the SEL's clock (2026-07-01, closes cold F1).** A SEL is anchored to its
  owner IEL (kind-strict — content `Ixn` ↔ IEL `Ixn`, etc.). Two rules govern the cross-layer:
  - **Anchor-monotonicity** — a SEL event is valid **only if it extends its SEL's latest IEL-anchored tip** (computed
    over the **canonical/retained IEL walk**). The check runs at SEL-validation over the anchors a node can
    **attribute** (holds the body for); the anchor SAID is *opaque* (inv 16), so an anchor whose body a node lacks is
    **skipped, not blocking** (*skip-unattributable* — else a withheld/lost/private body would wedge the SEL). A
    re-anchor at an already-attributed serial is **malformed → inert** (the carrying IEL event stays valid; an inert
    anchor never advances the tip). So a node extends each SEL it can attribute correctly.
  - **Cross-layer deadness-descends** — a SEL event whose anchoring IEL event is dead (condemned / below-seal-inert)
    is itself dead (the **IEL→SEL** anchor edge only — not KEL→IEL, which is forward-only).
  **Content-fork prevention rides the theorem transitively (2026-07-02):** a witnessed SEL content fork would force
  its two same-serial siblings to anchor at IEL content siblings at one IEL position — which the witnessing floor +
  option (b) prevent on the witnessed owner IEL (federation §1e / inv 4) — so a witnessed SEL content fork carries
  the **same fork-cost** and needs **no SEL-local witness gate**; the residual (witness-compromise / roster-delta
  straddle) is the IEL's residual inherited.
  These give the theorem *a valid SEL fork implies an IEL fork beneath it* (§7): a SEL **never forks under a linear
  IEL** (no deadlock — skip-unattributable prevents the wedge; cold-r5 F2's transient withheld-body split
  auto-resolves by seal order), and every genuine SEL fork rides an **IEL fork** — resolved by the owner IEL's burying
  seal (an `Evl`, or a `cut` `Evl` when it also evicts), the losing IEL branch buried → its SEL events die **by
  descent across the anchor edge**. A **signing-key (T1) compromise is fully deadenable**: no reserve → no sealed SEL
  `Trm` (needs a `Rev`/`Dth`) → one recovery rotation buries the whole tail (all content) → every anchored SEL event
  dead by descent, no reincept. The benign residual (two owner devices racing) is inert by anchor-monotonicity;
  serialize the content rail (area-iel §5) as the operator answer.

## 2. Superseded — do NOT carry (from design-pass §3)
- **"Every SEL is `Icp`+`Evl`"** → **lookup-SELs** are `Icp` + `Trm` (the revocation/rescission kill); content SELs are `Icp` + a serial-1 event (the first `Ixn`, or a bare `Pin` when incept-and-sit) + `Ixn`s. The serial-1-event floor is universal; the old SEL `Evl` / rescission-`Pin` is gone. *(A credential is **not** a SEL — it is an anchored SAD; issuance SEL dropped 2026-07-09.)*
- **"No SEL `Trm`; soft-close only"** → SEL **`Trm`** is back — **`t_govern` count, T2, always sealed (via `Rev`/`Dth`)** =
  revoke/close. The removal was premised on a now-retired anchor problem in the **pre-first-seen recovery-reserve
  tier** that the **count⊥tier** decoupling — and the two-tier collapse — sidesteps.
  *(The "T2, sealed-on-arrival via a dedicated kill-anchor" framing was right all along; the F3 **delayed-`Trm`** was the error and
  is **reversed** 2026-06-21 — a kill is monotone, so it can't be unsealed.)*
- **Registry SEL / registry identifier** → gone; a cred is a **direct-anchored SAD** (issuance SEL dropped 2026-07-09), its revocation/rescission **lookup SEL** built from `Icp{owner, topic, data}` (usual two-pass), with distinct per-kind topics (`CRED_REVOCATION_TOPIC` / `DLG_RSC_TOPIC` / `DOC_RSC_TOPIC`) and a flat `kills[]` target `hash('{topic}:{owner}:{data}')`.

## 3. Requirements satisfied / imposed
- Satisfies **R1** (no policy on the SEL — auth is the owner IEL's structural threshold), **R2** (SEL
  verification must be tokenizable — position-addressable), **R3** (a `pin` to a SEL position yields the state
  token + committed-anchor proof).
- **Imposes on the IEL:** the IEL anchors (a) a content SEL's **v1** (a serial-1 `Pin`, or the first content `Ixn`) via an IEL `Ixn` (`t_use`, ≤1/SEL —
  the `Icp` rides `v1.previous`, never anchored — inv 4) **and a credential's issuance commitment
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` directly** (an immutable SAD, no cred-SEL — issuance SEL dropped
  2026-07-09; `said(cred)` is never raw on the IEL, R5; the anchor is the validity proof), (b) a
  lookup `Icp` + its `Trm` (rescission kill) via an IEL `Dth` (sealed), (c) a **revocation lookup-SEL** `Trm` (a cred's revocation) via an IEL
  `Rev` (sealed) — the `Rev`/`Dth` also carrying the **`kills[]`** declaration naming the killed locus, (d) a doc-governance **`Gnt`** (grant) via an IEL **`Ath`** (sealed — the
  additive twin of the `Dth`-rescission; the `@`-slot notation is retired — the count is implied by the kind). **Kills ride the IEL `Rev`/`Dth` rail; grants the IEL `Ath` rail; content the
  IEL `Ixn` rail.** *(There is no SEL `Fld`/`Rpr` — no re-seal, no repair; a content fork resolves cross-layer.)*
- **Count travels with the anchored event's KIND — re-scoped: every IEL kind prices itself (Jason 2026-06-20/21).**
  The required count for an anchored SEL event is set by **its kind** (`t_use` content · `t_govern` `Trm`-kill ·
  `t_authorize` `Gnt` grant / lookup-SEL `Trm` rescind) and checked as a **parameter of the anchor-verification call**: when the walk
  resolves the anchor it already holds both the anchored event (kind ⇒ required count) and the anchoring IEL event
  (counts its sigs), so it checks in one pass. Content rides an IEL `Ixn` (T1); a kill rides an IEL **`Rev`/`Dth`** (T2,
  sealed), whose kind (`Rev` = `t_govern`, `Dth` = `t_authorize`) names the count — **backed** by the kill-anchor's own
  sigs and **demanded** by the anchored kill's kind. **Re-scoped (2026-06-21):** the rule is safe because **every
  IEL kind does exactly one job** ([inv 12]); the old IEL `Evl`-anchors-a-kill conflation (a roster change riding
  at a kill's count, **S1**) is gone — `Evl` is roster-only. *(IEL + vdtid-services notes to absorb.)*

## 4. Open / for the adversarial pass
- **`Fld` (the SEL re-seal) is DROPPED (first-seen, 2026-07-08).** The `Fld` existed to cap the content run for
  **page-atomic repair**. With no repair event, there is **no page-atomicity requirement**, so `Fld` bounds nothing
  and is removed — the earlier "the SEL must fold itself; 'just don't fold the SEL' was a rejected carve-out"
  (area-sel §4's NOT-transitive finding, Jason 2026-06-27) is superseded: rejecting it was correct *when a SEL
  divergence needed a page-atomic repair*; there is no such repair now, so a plain content SEL simply never self-seals
  and its **finality floors to the owner IEL via its `pin`**. The `Pin` (floor re-pin, `t_use`/**T1**, not
  seal-advancing) stays for the incept-and-sit serial-1 floor. SEL seal-advancers = **`Gnt`/`Trm`**; tier-1/buriable =
  `Ixn`/`Pin`. A **rescission** is a terminal **`Trm`** (`t_authorize`, T2, sealed); bound placement is **per-feature**
  (R3) — a **delegate** `Trm` carries only its pin (`bound` public in the `Dth`'s `kills[]`); a **doc-member** `Trm`
  commits a gated rescind-doc carrying the `bound` (2026-07-09/10).
- **Cred body `pin` — DROPPED (Jason 2026-06-26).** The body `pin` was redundant with the anchoring position (the
  as-of is the **anchoring position**, inv 5, not a self-asserted value). So the cred body carries **no `pin`**; the
  doc-layer as-of is read from the **anchoring IEL `Ixn`** that commits the cred's **issuance commitment**
  `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')` (the cred is anchored directly — no cred-SEL as of 2026-07-09;
  `said(cred)` never appears raw on the IEL, R5). Propagated to documents.md / protocol-doctrine / inv 5 / inv 15.
- **Naming — RESOLVED (Finding 12; refined 2026-06-27; first-seen 2026-07-08):** the SEL **floor re-pin** kind is
  **`Pin`** (carries only the `pin`); the rescission `bound` rides the `Dth`'s **`kills[]`** (moved off the `Trm` —
  2026-07-09; the `Trm` carries only its pin — **the delegate case**; a **doc-member** bound is participant-identifying
  and instead rides a **gated rescind-doc committed by the `Trm`**, R3 / multi-party §1). The old SEL `Evl` is
  fully retired; its re-seal job (`Fld`) is **dropped** with the repair machinery — a plain content SEL floors down to
  the owner IEL instead. Cross-layer `Trm` (KEL/SEL/IEL) is **not** renamed (same act at three layers) — the docs
  just **qualify it by layer** (`KEL-Trm` / `SEL-Trm` / `IEL-Trm`).
- **Public-cred uniqueness — RESOLVED (G4, refined 2026-06-21; cred = direct-anchored SAD 2026-07-09).**
  **`cred.said`** is the preimage the issuer commits (issuance = `hash('{CRED_ISSUANCE_TOPIC}:{issuer}:{cred.said}')`,
  the validity proof) **and** the `data` for the revocation kill-target
  (`hash('{CRED_REVOCATION_TOPIC}:{issuer}:{cred.said}')`); the body holds (`nonce` if private). Because the SAID is over the
  **whole** body, **any two non-identical creds get distinct `said(cred)`** — it differs whenever *any* body field
  differs (`claims`, `policy`, `issuee`, `expires`, `nonce`). So the public-cred collision is closed **by
  construction**: two public creds differing in `policy` have different SADs → different `said(cred)` → distinct
  anchors + distinct kill loci; only **byte-identical** creds share a SAID → **dedup** (content-addressed, idempotent
  submit). Private creds get unpredictability from the `nonce`-in-body. *(Supersedes the round-4 `data = {pin,
  body-digest}` fix and the create-on-revoke "`data` = the issuance-SEL derivation" — there is no issuance SEL; the
  cred is anchored directly.)*
- **Lookup-SEL rescission = `{Icp, Trm}` — RESOLVED (Jason 2026-06-26).** The rescission's terminal event **is** a
  `Trm` (a kill — `Trm` is the kill kind; symmetric with cred revocation: both → a SEL `Trm` under a kill-anchor, differing
  only by kind — a `Rev` for the revocation, a `Dth` for the rescission). Sealed on arrival, monotone — you never un-rescind (restoring a delegate is a **fresh grant**). The
  `Trm` carries **only its pin**; the **`bound` moved to the `Dth`'s `kills[]`** entry (`{target, bound}`,
  un-withholdable on the witnessed IEL — B1 fail-secure rework 2026-07-09; area-iel §1), and the `Dth`'s
  `manifest.anchors` names the `Trm`. **This is the cred+delegate case** — a **doc-member** rescission's `bound` is
  participant-identifying, so it rides a **gated rescind-doc committed by the `Trm`** and `kills[]` carries only the
  blind target (R3 / multi-party §1); "the `Trm` carries only its pin / the bound rides `kills[]`" is **not**
  universal. *(Supersedes the earlier "no `Trm` needed, the pin-carrier is the kill" — the
  kill is correctly a `Trm`; the `Pin` is the floor re-pin. Also supersedes "the `Trm` carries the `bound`" — the
  bound is now on `kills[]` so the fail-secure walk reads it without fetching the object.)*
- **Content `Icp` collision/divergence — RESOLVED (2026-06-20): rests on the high-entropy-`data` rule (§1).**
  "Collision needs a Blake3 preimage → no" is **insufficient alone** — it silently assumes high-entropy `data`.
  With low-entropy/predictable `data` the prefix is guessable and collision/camping/de-anon reopen. The actual
  guarantee is the **`data`-entropy rule** (§1) for unpredictable prefixes **+ owner-rooting** for discoverable ones.

## 5. Drift → land backlog
- **Reconcile design-pass §3** (+ the §2.2 SEL-inception row) to this note (the `Icp`+`Evl`-always + no-`Trm`
  claims). §2.1's `≤1 Ixn` rule is unchanged.
- Write `docs/design/primitives/data/event-logs/sel/` fresh from this note.

## 6. Confidence
- §1 — high (direct consequence of `inv 15` + the document-layer decisions, which Jason drove this session).
- §4 — the field-placement + content-window items are detail for the adversarial pass; not load-bearing blockers.
