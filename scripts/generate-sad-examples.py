#!/usr/bin/env python3
"""Generate the example JSON blocks in docs/design/primitives/data/sad/shapes.md.

Every example's `said` (and `prefix`, on the prefix-deriving SADs) is DERIVED from the exact
JSON printed in the doc, per said.md §Derivation:

  - canonicalize with JCS (RFC 8785): sorted keys, no whitespace, integers only
  - `said` (and `prefix`, when prefix-deriving) set to the fixed-value placeholder — 44 '#'
  - Blake3-256 over the canonical bytes, base64url, qualified with the code table's digest code

Code table: cesr-rs, with `V` in place of `K` for Blake3-256 digests.

Values that name something NOT printed in the doc (an owner IEL prefix, a pin, an epoch) are
arbitrary tokens of the right shape; keys, signatures, and ciphertexts print elided, and the
enclosing `said` derives over the elided text exactly as shown. Examples that compose share
values, so the cross-references between blocks recompute too.

Regenerating does NOT rewrite the doc — it prints the blocks for a human to place. The published
examples are checked in the gate by scripts/check-sad-examples.py, which re-derives every SAID
from the doc itself.

Usage:
    scripts/generate-sad-examples.py            # every block, section by section
    scripts/generate-sad-examples.py file       # one block, by section key
    scripts/generate-sad-examples.py --json     # {section key: markdown} for scripted insertion

Requires the `b3sum` binary (Blake3-256).
"""

import base64
import json
import subprocess
import sys
from collections import OrderedDict

PLACEHOLDER = "#" * 44


# --- primitives ---------------------------------------------------------------------------


def blake3(data: bytes, length: int = 32) -> bytes:
    try:
        return subprocess.run(
            ["b3sum", "--no-names", "--raw", "--length", str(length)],
            input=data,
            capture_output=True,
            check=True,
        ).stdout
    except FileNotFoundError:
        sys.exit("b3sum not found — install it (brew install b3sum / apt-get install b3sum)")


def qualify(raw: bytes, code: str) -> str:
    """1-char code + 43 base64url chars for a 32-byte primitive (pad byte replaced by the code)."""
    return code + base64.urlsafe_b64encode(b"\x00" + raw).decode()[1:]


def jcs(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def token(label: str, code: str = "V") -> str:
    """An arbitrary token of the right shape — names something not printed in the doc."""
    return qualify(blake3(label.encode()), code)


def nonce(label: str) -> str:
    return token(label, "N")


def gcm_nonce(label: str) -> str:
    """AES-GCM-256 nonce: 12 bytes, 4-char code, 20 chars total."""
    return "1AAN" + base64.urlsafe_b64encode(blake3(label.encode(), 12)).decode()


def elided(label: str, code: str, total: int) -> str:
    """A key / signature / ciphertext printed elided, with its real qualified length."""
    raw = blake3(label.encode(), 96)
    body = base64.urlsafe_b64encode(raw).decode()
    return f"{code}{body[:5]}…{total} chars…{body[-4:]}"


def said_of(fields) -> str:
    """Derive `said` over the canonical form, `said` at the placeholder."""
    obj = OrderedDict(fields)
    obj["said"] = PLACEHOLDER
    return qualify(blake3(jcs(obj)), "V")


def prefix_and_said(fields):
    """The two-hash derivation for a prefix-deriving SAD (said.md §Derivation)."""
    obj = OrderedDict(fields)
    obj["said"] = PLACEHOLDER
    obj["prefix"] = PLACEHOLDER
    prefix = qualify(blake3(jcs(obj)), "V")
    obj["prefix"] = prefix
    said = qualify(blake3(jcs(obj)), "V")
    return prefix, said


def sad(*pairs):
    """Build a SAD in display order with its derived `said` in place."""
    fields = OrderedDict(pairs)
    fields["said"] = said_of(fields)
    return OrderedDict([("said", fields["said"])] + [(k, v) for k, v in pairs if k != "said"])


def prefix_sad(*pairs):
    """Build a prefix-deriving SAD; `prefix` must appear in the pairs (its slot is display order)."""
    fields = OrderedDict(pairs)
    prefix, said = prefix_and_said(fields)
    out = OrderedDict()
    out["said"] = said
    for k, v in pairs:
        if k == "said":
            continue
        out[k] = prefix if k == "prefix" else v
    return out


BLOCKS = []


def block(section: str, lead: str, obj):
    BLOCKS.append((section, lead, json.dumps(obj, indent=2, ensure_ascii=False)))


# --- shared references (things the doc does not print) -------------------------------------

owner_iel = token("owner-iel-prefix")
owner_pin = token("owner-iel-ixn-previous")
reader_edit = token("doc-edit-membership-sel")
reader_comment = token("doc-comment-membership-sel")
reader_read = token("doc-read-membership-sel")
doc_readers = sorted([reader_edit, reader_comment, reader_read])
file_readers = sorted([token("inbox-read-sel"), token("archive-read-sel")])

# --- the blob bundle and the file SAD it commits -------------------------------------------

BLOB_LEN = 2456079  # payload = bundle.said (44 bytes) ‖ blob  ->  size 2456123
blob = blake3(b"quarterly-report-blob", BLOB_LEN)

bundle = sad(
    ("kind", "vdti/sad/v1/schemas/sealed-blob-metadata"),
    ("nonce", nonce("bundle-nonce")),
    ("blobDigest", qualify(blake3(blob), "V")),
    ("access", token("blob-access-descriptor")),
    ("expiry", "2027-05-01T00:00:00Z"),
)

payload = bundle["said"].encode() + blob
storage_key = qualify(blake3(payload), "V")

file_custody = OrderedDict(
    [("owner", owner_iel), ("pin", owner_pin), ("readers", file_readers)]
)
file_sad = sad(
    ("kind", "vdti/sad/v1/schemas/file"),
    ("custody", file_custody),
    ("availability", OrderedDict([("expiry", "2027-05-01T00:00:00Z")])),
    ("digest", storage_key),
    ("size", len(payload)),
    ("mediaType", "application/pdf"),
    ("name", "quarterly-report.pdf"),
    ("nonce", nonce("file-nonce")),
)

wrapper = OrderedDict(
    [
        ("said", file_sad["said"]),
        ("kind", file_sad["kind"]),
        ("custody", file_custody),
        ("availability", file_sad["availability"]),
    ]
)

block(
    "wrapper",
    "The wrapper of a private file SAD — an attested write, read gated to the union of two sets, "
    "bytes retained until a stated instant (§The file payload shows the same SAD in full):",
    wrapper,
)
block(
    "file",
    "A file SAD naming an encrypted attachment — the storage key its `said` commits, the advisory "
    "size and labels, and the mandatory nonce:",
    file_sad,
)
block(
    "bundle",
    "The bundle stored with that file's payload — the encrypted kind, a gated read, and a GC "
    "horizon its committing SAD's own availability covers:",
    bundle,
)

# --- rooting --------------------------------------------------------------------------------

# forward references resolved below (credential); build the pointers first
event_root = sad(
    ("kind", "vdti/rooting/v1/iel/event"),
    ("prefix", owner_iel),
    ("event", owner_pin),
    ("field", "manifest"),
)

submission = sad(
    ("kind", "vdti/rooting/v1/submission/envelope"),
    ("sad", file_sad["said"]),
    ("root", event_root["said"]),
)

# --- chain events ---------------------------------------------------------------------------

witness_config = sad(
    ("kind", "vdti/event/v1/roles/witnesses"),
    ("threshold", 3),
    ("signers", 5),
)

icp_manifest = sad(
    ("kind", "vdti/event/v1/roles/manifest"),
    ("witnesses", witness_config["said"]),
)

kel_icp = prefix_sad(
    ("prefix", None),
    ("serial", 0),
    ("kind", "vdti/kel/v1/events/icp"),
    ("publicKey", elided("device-verification-key", "Q", 2604)),
    ("rotationHash", token("next-rotation-reserve-commitment")),
    ("federation", token("federation-iel-prefix")),
    ("federationPin", token("federation-position")),
    ("manifest", icp_manifest["said"]),
)

kel_rot = sad(
    ("prefix", kel_icp["prefix"]),
    ("serial", 1),
    ("previous", kel_icp["said"]),
    ("kind", "vdti/kel/v1/events/rot"),
    ("publicKey", elided("rotated-verification-key", "Q", 2604)),
    ("rotationHash", token("next-next-rotation-reserve-commitment")),
    ("previousSeal", kel_icp["said"]),
)

roster = sad(
    ("kind", "vdti/event/v1/roles/roster"),
    (
        "add",
        sorted([token("member-kel-laptop"), token("member-kel-phone"), token("member-kel-token")]),
    ),
    ("threshold", OrderedDict([("use", 1), ("authorize", 2), ("govern", 2)])),
    ("t_live", 2),
)

pins = sad(
    ("kind", "vdti/event/v1/roles/pins"),
    ("pins", sorted([token("member-kel-laptop-tip"), token("member-kel-phone-tip")])),
)

# --- receipts and freshness -------------------------------------------------------------------

receipt = sad(
    ("kind", "vdti/witness/v1/receipts/iel"),
    ("threshold", 3),
    ("signers", 5),
    ("federationPin", token("federation-position")),
    ("chainPrefix", owner_iel),
    ("eventSaid", token("witnessed-iel-event")),
    ("eventSerial", 17),
    ("timestamp", "2026-11-04T18:22:07Z"),
    ("witnessPrefix", token("witness-kel-prefix")),
)

statements = sorted(
    [
        OrderedDict([("prefix", owner_iel), ("effectiveSaid", token("effective-said-a"))]),
        OrderedDict(
            [("prefix", token("another-iel-prefix")), ("effectiveSaid", token("effective-said-b"))]
        ),
    ],
    key=lambda s: s["prefix"],
)

freshness = sad(
    ("kind", "vdti/witness/v1/states/freshness"),
    ("statements", statements),
    ("timestamp", "2026-11-04T18:22:09Z"),
    ("nonce", nonce("freshness-challenge")),
    ("witnessPrefix", token("witness-kel-prefix")),
)

# --- grant values -------------------------------------------------------------------------

directory_kem = sad(
    ("kind", "vdti/sel/v1/grants/directory-kem"),
    ("receiveKey", elided("device-receive-key", "M", 1580)),
    ("receivers", sorted([token("mail-service-iel"), token("backup-inbox-iel")])),
)

block_marker = sad(
    ("kind", "vdti/sel/v1/grants/block"),
    ("reason", "sustained malformed submissions"),
)

trusted_federation = sad(
    ("kind", "vdti/sel/v1/grants/trusted-federation"),
    ("remotePrefix", token("remote-federation-iel")),
    ("bound", token("remote-federation-governance-event")),
)

# --- ESSR ------------------------------------------------------------------------------------

essr_envelope = sad(
    ("kind", "vdti/essr/v1/schemas/envelope"),
    ("sender", token("essr-sender-iel")),
    ("senderPin", token("essr-sender-position")),
    ("recipient", token("essr-recipient-iel")),
    ("kemCiphertext", elided("essr-kem-ciphertext", "Y", 1452)),
    ("payloadDigest", token("essr-payload-storage-key")),
    ("payloadSize", 4192),
    ("nonce", gcm_nonce("essr-sealing-nonce")),
)

essr_inner = sad(
    ("kind", "vdti/essr/v1/schemas/inner"),
    ("sender", token("essr-sender-iel")),
    ("payload", elided("essr-inner-payload", "", 3128)),
)

essr_message = sad(
    ("kind", "vdti/essr/v1/schemas/message"),
    ("envelope", essr_envelope["said"]),
    ("signature", elided("essr-sender-signature", "1AAQ", 4416)),
)

# --- credentials -----------------------------------------------------------------------------

claim_program = sad(
    ("kind", "vdti/cred/v1/claims/blinded-string"),
    ("nonce", nonce("claim-program-nonce")),
    ("data", "Bachelor of Science, Mathematics"),
)

claim_honours = sad(
    ("kind", "vdti/cred/v1/claims/blinded-boolean"),
    ("nonce", nonce("claim-honours-nonce")),
    ("data", True),
)

claims = sad(
    ("kind", "vdti/cred/v1/claims/diploma"),
    ("program", claim_program["said"]),
    ("honours", claim_honours["said"]),
)

credential = sad(
    ("kind", "edu.example/cred/v1/schemas/diploma"),
    ("issuer", token("issuer-iel-prefix")),
    ("issuerPin", token("issuer-iel-ixn-previous")),
    ("issuee", token("graduate-iel-prefix")),
    ("claims", claims["said"]),
    ("issued", "2026-06-12T00:00:00Z"),
    ("nonce", nonce("credential-nonce")),
)

sad_field_root = sad(
    ("kind", "vdti/rooting/v1/sad/field"),
    ("parent", credential["said"]),
    ("field", "claims"),
)

# --- IPEX -------------------------------------------------------------------------------------

ipex_grant = sad(
    ("kind", "vdti/ipex/v1/schemas/grant"),
    ("previous", token("ipex-agree")),
    ("discloser", token("graduate-iel-prefix")),
    ("audience", token("verifier-iel-prefix")),
    ("nonce", nonce("presentation-nonce")),
    ("created", "2027-02-19T14:05:00Z"),
    ("challenge", nonce("verifier-challenge")),
    ("disclosed", credential["said"]),
)

# --- shared documents ---------------------------------------------------------------------------

doc_v0 = prefix_sad(
    ("kind", "vdti/doc/v1/schemas/inception"),
    ("creator", token("creator-iel-prefix")),
    ("prefix", None),
    ("custody", OrderedDict([("readers", doc_readers)])),
    ("nonce", nonce("doc-nonce")),
)

doc_custody = OrderedDict(
    [("owner", token("editor-iel-prefix")), ("pin", token("editor-ixn-previous")), ("readers", doc_readers)]
)

doc_version = sad(
    ("kind", "vdti/doc/v1/schemas/version"),
    ("custody", doc_custody),
    ("ancestors", [token("prior-version")]),
    ("prefix", doc_v0["prefix"]),
    ("grant", token("edit-membership-grant")),
    ("content", token("version-body-sad")),
    ("edited", "2027-01-22T16:41:12Z"),
    ("nonce", nonce("version-nonce")),
)

comment_custody = OrderedDict(
    [
        ("owner", token("commenter-iel-prefix")),
        ("pin", token("commenter-ixn-previous")),
        ("readers", doc_readers),
    ]
)

comment = sad(
    ("kind", "vdti/doc/v1/schemas/comment"),
    ("custody", comment_custody),
    ("prefix", doc_v0["prefix"]),
    ("target", doc_version["said"]),
    ("locator", "cGFyYToxNy1yYW5nZTo0MDgsNDQx"),
    ("content", "VGhpcyBjbGF1c2UgY29udHJhZGljdHMgwqcyLg"),
    ("nonce", nonce("comment-nonce")),
)

resolution = sad(
    ("kind", "vdti/doc/v1/schemas/comment-resolution"),
    ("custody", doc_custody),
    ("prefix", doc_v0["prefix"]),
    ("comment", comment["said"]),
    ("resolved", True),
    ("nonce", nonce("resolution-nonce")),
)

# --- exchange ------------------------------------------------------------------------------------

chat = sad(
    ("kind", "vdti/exchange/v1/schemas/message"),
    ("previous", token("prior-lane-message")),
    ("epoch", token("group-key-epoch")),
    ("payloadDigest", token("chat-payload-storage-key")),
    ("payloadSize", 1184),
    ("timestamp", "2027-03-08T21:14:33Z"),
    ("nonce", nonce("chat-nonce")),
)

# --- emit -------------------------------------------------------------------------------------

block("rooting-envelope", "A submission admitting the file SAD above under an event root:", submission)
block(
    "rooting-event",
    "The event-root pointer it carries — the owner IEL `Ixn` at `event`'s serial + 1 commits the SAD "
    "in its `manifest`:",
    event_root,
)
block(
    "rooting-field",
    "A SAD-field-root pointer instead, when an accepted parent commits the child — here a "
    "credential's claims SAD:",
    sad_field_root,
)
block(
    "events-icp",
    "A KEL inception — `serial` 0, no `previous`, and a `prefix` derived from the whole inception "
    "content by the two-hash algorithm:",
    kel_icp,
)
block(
    "events-rot",
    "The rotation that follows it — the inherited `prefix`, `previous` to the inception, and the "
    "`previousSeal` back-link that renders the spine:",
    kel_rot,
)
block(
    "manifest",
    "The manifest that inception names — one role, the witness-config SAD below:",
    icp_manifest,
)
block("witnesses", "A witness-config — five signers selected per event, three receipts required:", witness_config)
block(
    "roster",
    "An initial roster and threshold vector, carried by a user IEL `Icp` — three member devices, "
    "content at one, authority at two:",
    roster,
)
block("pins", "The down-pins of an IEL event two of its members participated in:", pins)
block("receipt", "A witness receipt over an IEL event at serial 17:", receipt)
block(
    "freshness",
    "A freshness statement answering a consumer's challenge, attesting the state it holds for two "
    "chains:",
    freshness,
)
block(
    "directory-kem",
    "A published receive key and the services that hold a message sealed to it:",
    directory_kem,
)
block("block-marker", "A prefix-block marker:", block_marker)
block(
    "trusted-federation",
    "A trusted-federation grant value — the remote federation and the governance horizon acceptance "
    "is bounded by:",
    trusted_federation,
)
block(
    "essr-envelope",
    "An ESSR envelope — the signed cleartext, committing its sealed inner by storage key:",
    essr_envelope,
)
block("essr-inner", "The inner it seals:", essr_inner)
block("essr-message", "And the message handed to transport:", essr_message)
block(
    "ipex-grant",
    "An IPEX grant disclosing a credential to one verifier, echoing that verifier's challenge:",
    ipex_grant,
)
block(
    "credential",
    "A credential — issued to a named issuee, its claims committed as a nested SAD:",
    credential,
)
block("claims", "The claims SAD it commits, each position a blinded claim:", claims)
block("claim", "And one of those blinded claims, disclosed:", claim_program)
block(
    "doc-v0",
    "A document constitution — the prefix derived from V0's whole content, read gated to the three "
    "membership sets:",
    doc_v0,
)
block("doc-version", "A version of that document, attributed to its editor:", doc_version)
block("doc-comment", "A comment on that version:", comment)
block("doc-resolution", "And the resolution that closes it:", resolution)
block(
    "chat",
    "A chat message on its writer's lane — no sender field, because the lane is the writer:",
    chat,
)

def rendered():
    """key -> the markdown to insert (lead-in paragraph + fenced json)."""
    return {s: f"{lead}\n\n```json\n{body}\n```" for s, lead, body in BLOCKS}


if __name__ == "__main__":
    if "--json" in sys.argv:
        print(json.dumps(rendered(), ensure_ascii=False, indent=2))
    else:
        only = sys.argv[1] if len(sys.argv) > 1 else None
        for section, lead, body in BLOCKS:
            if only and section != only:
                continue
            print(f"### {section}")
            print(lead)
            print("```json")
            print(body)
            print("```")
            print()
