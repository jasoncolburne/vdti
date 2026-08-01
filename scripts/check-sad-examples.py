#!/usr/bin/env python3
"""Re-derive every example SAID in the SAD shape catalogue from the doc itself.

Each fenced json block in shapes.md is an example SAD whose `said` is derived from its own
content ([`said.md` §Derivation](docs/design/primitives/data/sad/said.md)). This check reads the
published bytes and recomputes:

  - canonicalize with JCS (RFC 8785): sorted keys, no whitespace, integers only;
  - `said` set to the fixed-value placeholder — 44 '#';
  - Blake3-256 over the canonical bytes, base64url, qualified with the `V` digest code;
  - on a prefix-deriving SAD (a chain inception, the document V0), the two-hash algorithm —
    both `said` and `prefix` at the placeholder to derive `prefix`, then the real `prefix` in
    place with only `said` at the placeholder to derive `said`.

Which class a SAD is in is decided by its **kind**, not by field-presence (said.md §Derivation),
so the two-hash check is keyed on PREFIX_DERIVING_KINDS below and is never a fallback from a
failed attempt: a prefix-deriving SAD passes the single-hash test trivially — that IS step 2 of
its own algorithm — so treating the prefix as best-effort would let a stale `prefix` beside a
recomputed `said` pass clean. The guard runs both ways: a kind NOT in the set whose prefix does
derive from its own content is an inception kind missing from the set, and errors as one.

A block whose `said` matches an already-verified block's, and whose every field equals that
block's, is a SLICE of it (the wrapper example shows four fields lifted from a whole SAD), not a
whole SAD, and is reported as such.

The examples are produced by scripts/generate-sad-examples.py; this check shares no code with
it, so a wrong derivation on either side shows up as a mismatch here.

Usage:
    scripts/check-sad-examples.py            # every tracked Markdown file
    scripts/check-sad-examples.py PATH ...   # restrict to these files
    scripts/check-sad-examples.py -v         # list every block, not just failures

Exit status: 0 when every example recomputes, 1 otherwise.

Requires Blake3-256: the `b3sum` binary, or the `blake3` Python module.
"""

import argparse
import base64
import json
import re
import subprocess
import sys

PLACEHOLDER = "#" * 44
DIGEST_CODE = "V"
JSON_BLOCK = re.compile(r"```json\n(.*?)```", re.S)

# The prefix-deriving kinds: every chain inception event, plus the shared-document constitution
# V0 (said.md §Derivation). Membership is by kind — a SAD that merely carries a `prefix` field
# (a version, a rooting pointer) derives single-hash like any other.
PREFIX_DERIVING_KINDS = frozenset(
    {
        "vdti/kel/v1/events/icp",
        "vdti/kel/v1/events/fcp",
        "vdti/iel/v1/events/icp",
        "vdti/iel/v1/events/fcp",
        "vdti/sel/v1/events/icp",
        "vdti/doc/v1/schemas/inception",
    }
)


def _blake3_impl():
    """Blake3-256 over bytes — the b3sum binary, else the blake3 module. Never a silent skip."""
    try:
        subprocess.run(["b3sum", "--version"], capture_output=True, check=True)

        def via_b3sum(data: bytes) -> bytes:
            return subprocess.run(
                ["b3sum", "--no-names", "--raw", "--length", "32"],
                input=data,
                capture_output=True,
                check=True,
            ).stdout

        return via_b3sum
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        import blake3 as _blake3 # type: ignore

        return lambda data: _blake3.blake3(data).digest()
    except ImportError:
        sys.exit(
            "no Blake3-256 available — install the b3sum binary "
            "(brew install b3sum / apt-get install b3sum) or the blake3 Python module"
        )


blake3 = _blake3_impl()


def qualify(raw: bytes) -> str:
    """A 32-byte primitive as 44 chars: the code replaces the leading pad character."""
    return DIGEST_CODE + base64.urlsafe_b64encode(b"\x00" + raw).decode()[1:]


def jcs(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def derive_said(obj) -> str:
    probe = dict(obj)
    probe["said"] = PLACEHOLDER
    return qualify(blake3(jcs(probe)))


def derive_prefix_and_said(obj):
    probe = dict(obj)
    probe["said"] = PLACEHOLDER
    probe["prefix"] = PLACEHOLDER
    prefix = qualify(blake3(jcs(probe)))
    probe["prefix"] = prefix
    return prefix, qualify(blake3(jcs(probe)))


def check_file(path, verbose):
    """-> (checked, prefix_deriving, slices, errors)."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        # Deliberately an error, including a tracked file deleted but not yet staged: this check
        # is worthless if it can pass having read less than it was asked to. Stage the deletion.
        print(f"ERROR  {path}  — {exc}", file=sys.stderr)
        return 0, 0, 0, [(path, "unreadable")]

    checked = prefix_deriving = 0
    errors, deferred, verified = [], [], {}

    for index, raw in enumerate(JSON_BLOCK.findall(text), 1):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append((f"{path} block {index}", f"not valid JSON — {exc}"))
            continue
        if not isinstance(obj, dict) or "said" not in obj:
            if verbose:
                print(f"  skip  {path} block {index}  — no said")
            continue
        label = obj.get("kind", "<no kind>")
        where = f"{path} block {index}"

        if derive_said(obj) != obj["said"]:
            deferred.append((index, label, obj))
            continue

        if label in PREFIX_DERIVING_KINDS:
            if "prefix" not in obj:
                errors.append((where, f"{label} — prefix-deriving kind carries no prefix"))
                continue
            derived = derive_prefix_and_said(obj)
            if derived != (obj["prefix"], obj["said"]):
                errors.append((where, f"{label} — prefix does not recompute (expected {derived[0]})"))
                continue
            prefix_deriving += 1
            mode = "said + prefix (two-hash)"
        else:
            # The other direction: a kind outside the set whose prefix DOES derive from its own
            # content is an inception kind missing from PREFIX_DERIVING_KINDS, not a coincidence.
            if "prefix" in obj and derive_prefix_and_said(obj) == (obj["prefix"], obj["said"]):
                errors.append(
                    (where, f"{label} — prefix derives from content; add it to PREFIX_DERIVING_KINDS")
                )
                continue
            mode = "said" if "prefix" not in obj else "said (prefix inherited / foreign reference)"

        checked += 1
        verified[obj["said"]] = (index, obj)
        if verbose:
            print(f"  ok    {where}  {label}  — {mode}")

    slices = 0
    for index, label, obj in deferred:
        where = f"{path} block {index}"
        parent = verified.get(obj["said"])
        if parent is not None:
            parent_index, parent_obj = parent
            # A slice is a subset of its parent, not merely something wearing its said.
            differing = [k for k, v in obj.items() if parent_obj.get(k, ...) != v]
            if differing:
                errors.append(
                    (where, f"{label} — carries block {parent_index}'s said but differs at {differing}")
                )
            else:
                slices += 1
                if verbose:
                    print(f"  ok    {where}  {label}  — slice of block {parent_index}")
            continue
        # Name the field that is actually wrong: a bad `prefix` on a prefix-deriving SAD also
        # breaks `said` (the prefix is in the said's canonical bytes), which reads as the wrong
        # diagnosis unless the two-hash derivation is consulted.
        why = "said does not recompute"
        if "prefix" in obj:
            derived_prefix, derived_said = derive_prefix_and_said(obj)
            if derived_said == obj["said"] and derived_prefix != obj["prefix"]:
                why = f"prefix does not recompute (expected {derived_prefix})"
        errors.append((where, f"{label} — {why}"))

    return checked, prefix_deriving, slices, errors


def collect_md_files(paths):
    """Given paths, use them; otherwise every tracked Markdown file (as check-doc-xrefs.py does),
    so an example landing in a doc other than the shape catalogue is covered on arrival."""
    if paths:
        return paths
    out = subprocess.check_output(["git", "ls-files", "*.md"], text=True)
    return [p for p in out.splitlines() if p]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every block")
    args = parser.parse_args()

    checked = prefix_deriving = slices = 0
    errors = []
    for path in collect_md_files(args.paths):
        c, p, s, e = check_file(path, args.verbose)
        checked, prefix_deriving, slices = checked + c, prefix_deriving + p, slices + s
        errors += e

    # A vacuous pass is the failure mode this check cannot have: reading nothing and reporting
    # clean is indistinguishable from verifying everything. On the default (whole-tree) run the
    # catalogue's examples must be found, so zero means the sweep broke, not that the tree is empty.
    if not args.paths and checked + slices == 0:
        errors.append(("(sweep)", "found no examples at all — the enumeration or the fences broke"))

    for where, msg in errors:
        print(f"ERROR  {where}  — {msg}", file=sys.stderr)

    print(
        f"\nexamples: {checked + slices} | derived: {checked} "
        f"(prefix-deriving: {prefix_deriving}) | slices: {slices} | errors: {len(errors)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
