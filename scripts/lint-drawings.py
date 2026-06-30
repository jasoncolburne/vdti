#!/usr/bin/env python3
"""Lint Excalidraw drawings: every arrow must be anchored at both ends.

A *dangling* arrow has an endpoint that is not bound to a live element — a loose
end that does not track its shape and almost always marks an out-of-date diagram
(an element was moved or deleted and the arrow detached). The chain-linkage
diagrams are load-bearing documentation, so a detached arrow is a real defect.
This dangling check is the gate behind `make lint-drawings`.

The same tool can **describe** the linkages (`--describe`): for each `example N`
group it first lists the **nodes** (the kind-labelled boxes — `Icp`, `Rot`,
`Fed`, …) and then every arrow and what it connects (resolved to the nearest kind
label). That is a review aid for checking a diagram against the design canon — the
node list answers "which event kinds does this example contain?" directly, without
hand-parsing the JSON.

`isDeleted` elements — and any binding that points at one — are always excluded
from the check/describe (Excalidraw keeps deleted elements in the JSON). `--prune`
deletes them from the file outright: a hygiene pass that shrinks the JSON and drops
the undo carcasses. It only removes `isDeleted` elements — it never rewrites a live
element or its bindings — so it can never change a lint verdict (a dangling *live*
arrow is still flagged by the check; pruning is not a fix for it).

Usage:
    scripts/lint-drawings.py [PATH ...]       # check; default: all tracked *.excalidraw
    scripts/lint-drawings.py -v               # check, listing every dangling arrow
    scripts/lint-drawings.py --describe        # print resolved linkages (all files)
    scripts/lint-drawings.py --describe FILE   # ... for one file
    scripts/lint-drawings.py --prune           # delete isDeleted elements (rewrites files)

Exit status: 0 when no arrow dangles (check) / on a clean prune, 1 otherwise.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys

# Short free-text labels (the event-kind tags placed on the boxes). Resolution
# is generic — any text this short near an endpoint — but anchoring the regex to
# a known vocabulary keeps `--describe` readable and avoids snapping to prose.
KIND_RE = re.compile(r"^[A-Z][A-Za-z0-9]{0,4}$")
EXAMPLE_RE = re.compile(r"example\s+\d+", re.IGNORECASE)
LABEL_RADIUS = 90  # px: how far a free-text label may sit from an endpoint
SHAPE_TYPES = ("rectangle", "diamond", "ellipse")  # the boxes that carry kind labels


def repo_root():
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def collect_drawings(root, paths):
    if paths:
        return [os.path.relpath(os.path.abspath(p), root) for p in paths]
    out = subprocess.check_output(["git", "ls-files", "*.excalidraw"], text=True)
    return [p for p in out.splitlines() if p]


def load_elements(path):
    """Return the list of *live* (non-deleted) elements, or None on parse error."""
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR  {path}: cannot parse — {exc}", file=sys.stderr)
        return None
    elements = doc.get("elements", doc) if isinstance(doc, dict) else doc
    if not isinstance(elements, list):
        print(f"ERROR  {path}: no elements array", file=sys.stderr)
        return None
    return [e for e in elements if not e.get("isDeleted")]


def center(el):
    return (el.get("x", 0) + el.get("width", 0) / 2,
            el.get("y", 0) + el.get("height", 0) / 2)


def endpoint_status(arrow, which, byid):
    """('ok', el) | ('unbound', None) | ('dangling', elementId).

    'dangling' means the binding names an element that is deleted or absent.
    """
    binding = arrow.get(which)
    if not binding or not binding.get("elementId"):
        return ("unbound", None)
    eid = binding["elementId"]
    el = byid.get(eid)
    if el is None:
        return ("dangling", eid)  # bound to a deleted / missing element
    return ("ok", el)


def arrow_dangles(arrow, byid):
    """An arrow is bad unless BOTH ends bind to a live element. Returns a list of
    (end, reason) problems; empty list means fully anchored."""
    problems = []
    for which, end in (("startBinding", "start"), ("endBinding", "end")):
        status, info = endpoint_status(arrow, which, byid)
        if status == "unbound":
            problems.append((end, "not bound to any element"))
        elif status == "dangling":
            problems.append((end, f"bound to deleted/missing element {info}"))
    return problems


# ---- describe mode helpers -------------------------------------------------

def text_of(el):
    return (el.get("text", "") or "").replace("\n", "/")


def label_for(el, texts):
    """Human name for an arrow endpoint element."""
    if el.get("type") == "text":
        return text_of(el)
    # A label bound to this element (containerId) wins.
    for t in texts:
        if t.get("containerId") == el.get("id"):
            return text_of(t)
    # Else the nearest short kind-label.
    cx, cy = center(el)
    best, bestd = None, LABEL_RADIUS
    for t in texts:
        if t.get("containerId"):
            continue
        s = (t.get("text", "") or "").strip()
        if not KIND_RE.match(s):
            continue
        tx, ty = center(t)
        d = math.hypot(tx - cx, ty - cy)
        if d < bestd:
            best, bestd = s, d
    return best or el.get("type", "?")


def endpoint_label(arrow, which, byid, texts):
    status, el = endpoint_status(arrow, which, byid)
    if status == "ok":
        return label_for(el, texts)
    pts = arrow.get("points") or []
    if pts:
        p = pts[0] if which == "startBinding" else pts[-1]
        pt = (arrow.get("x", 0) + p[0], arrow.get("y", 0) + p[1])
        # nearest kind label to a free endpoint, marked as unbound
        near = label_for({"type": "?", "x": pt[0], "y": pt[1], "width": 0, "height": 0}, texts)
        return f"<{status}:{near}>"
    return f"<{status}>"


def arrow_label(arrow, texts):
    for t in texts:
        if t.get("containerId") == arrow.get("id"):
            return text_of(t)
    return ""


def nearest_example_pt(x, y, titles):
    """The example a point belongs to: the nearest title that sits ABOVE it
    (examples are laid out title-on-top, content below — so only a title with
    ty <= y is a candidate). Falls back to the nearest title overall only if none
    sits above (shouldn't happen for well-formed examples)."""
    if not titles:
        return ""
    pool = [(t, tx, ty) for (t, tx, ty) in titles if ty <= y] or titles
    best, bestd = "", 1e18
    for title, tx, ty in pool:
        d = math.hypot(tx - x, ty - y)
        if d < bestd:
            best, bestd = title, d
    return best


def nearest_example(arrow, titles):
    return nearest_example_pt(arrow.get("x", 0), arrow.get("y", 0), titles)


def describe(path):
    live = load_elements(path)
    if live is None:
        return
    byid = {e["id"]: e for e in live if "id" in e}
    texts = [e for e in live if e.get("type") == "text"]
    arrows = [e for e in live if e.get("type") == "arrow"]
    titles = [(text_of(t), *center(t)) for t in texts if EXAMPLE_RE.search(t.get("text", ""))]

    print(f"\n# {path} — {len(arrows)} arrow(s), {len(live)} live element(s)")

    # Nodes: every kind-labelled box, grouped by the example title above it.
    nodes_by_ex = {}
    node_rows = [
        (nearest_example_pt(*center(e), titles), center(e)[1], center(e)[0], label_for(e, texts))
        for e in live if e.get("type") in SHAPE_TYPES
    ]
    for ex, _y, _x, lab in sorted(node_rows, key=lambda r: (r[0], r[1], r[2])):
        nodes_by_ex.setdefault(ex, []).append(lab)

    # Arrows: grouped by the example title above the arrow's origin.
    arrows_by_ex = {}
    arrow_rows = [
        (
            nearest_example(a, titles),
            a.get("y", 0),
            a.get("x", 0),
            endpoint_label(a, "startBinding", byid, texts),
            arrow_label(a, texts),
            endpoint_label(a, "endBinding", byid, texts),
        )
        for a in arrows
    ]
    for r in sorted(arrow_rows, key=lambda r: (r[0], r[1], r[2])):
        arrows_by_ex.setdefault(r[0], []).append(r)

    for ex in sorted(set(nodes_by_ex) | set(arrows_by_ex)):
        print(f"\n  ── {ex or '(no example title nearby)'} ──")
        if nodes_by_ex.get(ex):
            print(f"    nodes: {', '.join(nodes_by_ex[ex])}")
        for _ex, _y, _x, s, lab, e in arrows_by_ex.get(ex, []):
            lab = f" --[{lab}]-->" if lab else " -->"
            print(f"    {s:>22}{lab} {e}")


# ---- check mode ------------------------------------------------------------

def check(path):
    """Return (n_arrows, list_of_dangling) where each dangling is (arrow, problems)."""
    live = load_elements(path)
    if live is None:
        return (0, None)
    byid = {e["id"]: e for e in live if "id" in e}
    texts = [e for e in live if e.get("type") == "text"]
    arrows = [e for e in live if e.get("type") == "arrow"]
    dangling = []
    for a in arrows:
        problems = arrow_dangles(a, byid)
        if problems:
            dangling.append((a, problems, texts))
    return (len(arrows), dangling)


# ---- prune mode (jq-backed, byte-faithful) ---------------------------------

# jq preserves key order and (jq >= 1.7) number literals, so it rewrites ONLY the
# pruned elements and leaves every other byte intact — verified by running the
# filter on a clean drawing and diffing (identical). A Python json round-trip would
# reformat numbers/exponents and noise up the diff, so prune shells out to jq.
_JQ_PRUNE = ('if type=="object" then .elements |= map(select(.isDeleted != true)) '
             'else map(select(.isDeleted != true)) end')
_JQ_COUNT = ('if type=="object" then .elements else . end '
             '| map(select(.isDeleted == true)) | length')


def prune(path):
    """Delete isDeleted elements from `path` in place via jq. Returns the count
    removed, or None on error. Removes carcasses only — never rewrites a live
    element or its bindings, so it can never change a lint verdict."""
    try:
        n = int(subprocess.check_output(["jq", _JQ_COUNT, path], text=True).strip())
    except FileNotFoundError:
        print("ERROR  --prune needs `jq` on PATH (not found)", file=sys.stderr)
        return None
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR  {path}: jq count failed — {exc}", file=sys.stderr)
        return None
    if n == 0:
        print(f"  {path}: already clean (0 isDeleted)")
        return 0
    tmp = path + ".prune.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            subprocess.check_call(["jq", "--indent", "2", _JQ_PRUNE, path], stdout=f)
        os.replace(tmp, path)
    except subprocess.CalledProcessError as exc:
        if os.path.exists(tmp):
            os.remove(tmp)
        print(f"ERROR  {path}: jq prune failed — {exc}", file=sys.stderr)
        return None
    print(f"  {path}: pruned {n} isDeleted element(s)")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint / describe Excalidraw arrow linkages.")
    ap.add_argument("paths", nargs="*", help="files (default: all tracked *.excalidraw)")
    ap.add_argument("--describe", action="store_true",
                    help="print resolved linkages instead of checking")
    ap.add_argument("--prune", action="store_true",
                    help="delete isDeleted elements from each drawing (rewrites files, via jq)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="in check mode, list every dangling arrow")
    args = ap.parse_args(argv)

    root = repo_root()
    os.chdir(root)
    drawings = collect_drawings(root, args.paths)

    if not drawings:
        print("no .excalidraw files found")
        return 0

    if args.describe:
        for path in drawings:
            describe(path)
        return 0

    if args.prune:
        total = 0
        errors = 0
        for path in drawings:
            n = prune(path)
            if n is None:
                errors += 1
            else:
                total += n
        print(f"\npruned {total} isDeleted element(s) across {len(drawings)} drawing(s)"
              + (f" | errors: {errors}" if errors else ""))
        return 1 if errors else 0

    total_arrows = 0
    total_dangling = 0
    parse_errors = 0
    for path in drawings:
        n, dangling = check(path)
        if dangling is None:
            parse_errors += 1
            continue
        total_arrows += n
        total_dangling += len(dangling)
        if dangling and args.verbose:
            print(f"\n{path}:", file=sys.stderr)
        for a, problems, texts in dangling:
            lab = arrow_label(a, texts)
            where = f"@({int(a.get('x', 0))},{int(a.get('y', 0))})"
            tag = f" «{lab}»" if lab else ""
            reasons = "; ".join(f"{end} {why}" for end, why in problems)
            print(f"ERROR  {path}  arrow {a.get('id', '?')[:8]} {where}{tag} — {reasons}",
                  file=sys.stderr)

    status = total_dangling or parse_errors
    print(
        f"\nchecked {len(drawings)} drawing(s) | arrows: {total_arrows} | "
        f"dangling: {total_dangling}" + (f" | parse-errors: {parse_errors}" if parse_errors else "")
    )
    return 1 if status else 0


if __name__ == "__main__":
    sys.exit(main())
