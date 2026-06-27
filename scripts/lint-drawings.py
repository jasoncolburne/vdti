#!/usr/bin/env python3
"""Lint Excalidraw drawings: every arrow must be anchored at both ends.

A *dangling* arrow has an endpoint that is not bound to a live element — a loose
end that does not track its shape and almost always marks an out-of-date diagram
(an element was moved or deleted and the arrow detached). The chain-linkage
diagrams are load-bearing documentation, so a detached arrow is a real defect.
This dangling check is the gate behind `make lint-drawings`.

The same tool can **describe** the linkages (`--describe`): for each arrow, what
it connects — resolved to the nearest kind label (`Icp`, `Pin`, `Dec`, `Kil`,
`Ixn`, …) — grouped by the nearest `example N` title. That is a review aid for
checking a diagram against the design canon.

`isDeleted` elements — and any binding that points at one — are always excluded
(Excalidraw keeps deleted elements in the JSON).

Usage:
    scripts/lint-drawings.py [PATH ...]       # check; default: all tracked *.excalidraw
    scripts/lint-drawings.py -v               # check, listing every dangling arrow
    scripts/lint-drawings.py --describe        # print resolved linkages (all files)
    scripts/lint-drawings.py --describe FILE   # ... for one file

Exit status: 0 when no arrow dangles, 1 otherwise.
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


def nearest_example(arrow, titles):
    if not titles:
        return ""
    ax, ay = arrow.get("x", 0), arrow.get("y", 0)
    best, bestd = "", 1e18
    for title, tx, ty in titles:
        d = math.hypot(tx - ax, ty - ay)
        if d < bestd:
            best, bestd = title, d
    return best


def describe(path):
    live = load_elements(path)
    if live is None:
        return
    byid = {e["id"]: e for e in live if "id" in e}
    texts = [e for e in live if e.get("type") == "text"]
    arrows = [e for e in live if e.get("type") == "arrow"]
    titles = [(text_of(t), *center(t)) for t in texts if EXAMPLE_RE.search(t.get("text", ""))]

    print(f"\n# {path} — {len(arrows)} arrow(s), {len(live)} live element(s)")
    rows = []
    for a in arrows:
        rows.append((
            nearest_example(a, titles),
            a.get("y", 0),
            a.get("x", 0),
            endpoint_label(a, "startBinding", byid, texts),
            arrow_label(a, texts),
            endpoint_label(a, "endBinding", byid, texts),
        ))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    group = None
    for ex, _y, _x, s, lab, e in rows:
        if ex != group:
            group = ex
            print(f"\n  ── {ex or '(no example title nearby)'} ──")
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint / describe Excalidraw arrow linkages.")
    ap.add_argument("paths", nargs="*", help="files (default: all tracked *.excalidraw)")
    ap.add_argument("--describe", action="store_true",
                    help="print resolved linkages instead of checking")
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
