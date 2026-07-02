#!/usr/bin/env python3
"""Lint Excalidraw drawings: every arrow must be anchored at both ends.

A *dangling* arrow has an endpoint that is not bound to a live element — a loose
end that does not track its shape and almost always marks an out-of-date diagram
(an element was moved or deleted and the arrow detached). The chain-linkage
diagrams are load-bearing documentation, so a detached arrow is a real defect.
This dangling check is the gate behind `make lint-diagrams`.

The same tool can **describe** the linkages (`--describe`): for each `example N`
group it first lists the **nodes** (the kind-labelled boxes — `Icp`, `Rot`,
`Fed`, …) and then every arrow and what it connects (resolved to the nearest kind
label). That is a review aid for checking a diagram against the design canon — the
node list answers "which event kinds does this example contain?" directly, without
hand-parsing the JSON.

`isDeleted` elements are undo carcasses Excalidraw keeps in the JSON. The **check
fails if any are present** — we want a byte-clean file every commit — and `--prune`
is the fix (`make lint-diagrams-prune`): it deletes them, rewriting only the pruned
elements (never a live element or its bindings), so it clears the isDeleted gate but
can never mask a dangling *live* arrow (that is still flagged on its own). `--describe`
*excludes* deleted elements (a review aid, not the gate); and for the dangling check a
deleted element never counts as live, so an arrow bound to one reads as dangling (its
anchor is gone).

Usage:
    scripts/lint-diagrams.py [PATH ...]       # check (dangling + isDeleted); all tracked *.excalidraw
    scripts/lint-diagrams.py -v               # check, listing every dangling arrow
    scripts/lint-diagrams.py --describe        # print resolved linkages (all files)
    scripts/lint-diagrams.py --describe FILE   # ... for one file
    scripts/lint-diagrams.py --prune           # delete isDeleted elements (rewrites files)

Exit status: 0 when the file is clean — no dangling arrow AND no isDeleted carcass
(check) / on a clean prune; 1 otherwise.
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
# A free prose block sitting below an example title (the example's description) —
# distinguished from kind labels / layer headers ("KEL X", "flat") by length: the
# real descriptions run 100+ chars, the labels ≤ ~6, so any threshold in between works.
DESCRIPTION_MIN_LEN = 20
LABEL_RADIUS = 90  # px: how far a free-text label may sit from an endpoint
SHAPE_TYPES = ("rectangle", "diamond", "ellipse")  # the boxes that carry kind labels

# The box stroke colour encodes which log a node belongs to. Arrows are drawn in
# the default near-black (#1e1e1e) and carry no colour of their own, so an arrow's
# layer is inferred from the boxes it binds (same layer both ends, else cross-layer).
COLOR_LAYER = {
    "#e03131": "KEL",   # red
    "#2f9e44": "IEL",   # green
    "#1971c2": "SEL",   # blue
    "#f08c00": "DOC",   # orange — creds / SADs / content-version nodes
}
LAYER_ORDER = ["KEL", "IEL", "SEL", "DOC", "cross-layer", "misc"]


def layer_of(el):
    """Map an endpoint element to its log via box stroke colour; 'misc' when the
    colour is unmapped or the endpoint is unbound/dangling (el is None)."""
    if el is None:
        return "misc"
    return COLOR_LAYER.get(el.get("strokeColor"), "misc")


def repo_root():
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def collect_drawings(root, paths):
    if paths:
        return [os.path.relpath(os.path.abspath(p), root) for p in paths]
    out = subprocess.check_output(["git", "ls-files", "*.excalidraw"], text=True)
    return [p for p in out.splitlines() if p]


def parse_elements(path):
    """Return the raw elements list (live AND isDeleted), or None on parse error."""
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR  {path}: cannot parse — {exc}", file=sys.stderr)
        return None
    elements = doc.get("elements", doc) if isinstance(doc, dict) else doc
    if not isinstance(elements, list):
        print(f"ERROR  {path}: no elements array", file=sys.stderr)
        return None
    return elements


def load_elements(path):
    """Return the list of *live* (non-deleted) elements, or None on parse error."""
    elements = parse_elements(path)
    return None if elements is None else [e for e in elements if not e.get("isDeleted")]


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


def is_description(t):
    """A free (unbound) prose block below an example title — not a title, not a kind
    label / layer header. Length is the discriminator (see DESCRIPTION_MIN_LEN)."""
    if t.get("type") != "text" or t.get("containerId"):
        return False
    s = (t.get("text", "") or "")
    if EXAMPLE_RE.search(s):
        return False
    stripped = s.strip()
    return not KIND_RE.match(stripped) and len(stripped) >= DESCRIPTION_MIN_LEN


def description_text(t):
    """The prose flattened to a single line (Excalidraw wraps with literal \\n)."""
    return " ".join(((t.get("originalText") or t.get("text", "")) or "").split())


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


def assign_node_names(live, texts, titles, byid, ex_of):
    """Map shape id -> a name unique within its example, and a per-shape chain-order
    sort key. When several boxes in one example share a kind label (e.g. three
    `Ixn`), each gets a suffix `#1`, `#2`, … in **chain order** — depth along
    `previous` (distance from inception), ties broken by position — so `Rec#1` is
    the first repair and the listing reads in sequence. A label used once stays
    bare. Returns (names, orderkey) where orderkey[id] = (depth, y, x)."""
    parent = {}  # child id -> its `previous` target id
    for a in live:
        if a.get("type") != "arrow" or (arrow_label(a, texts) or "").strip() != "previous":
            continue
        s = (a.get("startBinding") or {}).get("elementId")
        t = (a.get("endBinding") or {}).get("elementId")
        if s and t:
            parent[s] = t

    def depth(nid):
        d, seen = 0, set()
        while True:
            p = parent.get(nid)
            if not p or p not in byid or p in seen:
                return d
            seen.add(nid)
            nid, d = p, d + 1

    shapes_by_ex = {}
    orderkey = {}
    for e in live:
        if e.get("type") not in SHAPE_TYPES or "id" not in e:
            continue
        ex = ex_of.get(e["id"]) or nearest_example_pt(*center(e), titles)
        cx, cy = center(e)
        orderkey[e["id"]] = (depth(e["id"]), cy, cx)
        shapes_by_ex.setdefault(ex, []).append(e)

    names = {}
    for shapes in shapes_by_ex.values():
        groups = {}
        for e in shapes:
            groups.setdefault(label_for(e, texts), []).append(e)
        for lab, items in groups.items():
            if len(items) == 1:
                names[items[0]["id"]] = lab
            else:
                for i, e in enumerate(sorted(items, key=lambda e: orderkey[e["id"]]), 1):
                    names[e["id"]] = f"{lab}#{i}"
    return names, orderkey


def endpoint_label(arrow, which, byid, texts, names=None):
    status, el = endpoint_status(arrow, which, byid)
    if status == "ok":
        if names is not None:
            return names.get(el.get("id"), label_for(el, texts))
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


def shape_example_map(live, titles, byid):
    """Assign each shape to an example by CONNECTED COMPONENT, not per-box proximity.
    Shapes joined by arrows form one cluster (one example's diagram), and the whole
    cluster takes the example most of its members sit under — so a box drawn nearer a
    neighbouring example's title no longer bleeds into it (the old per-box nearest-title
    trap). Isolated shapes fall back to their own nearest title. Returns id -> example."""
    shape_ids = [e["id"] for e in live if e.get("type") in SHAPE_TYPES and "id" in e]
    idset = set(shape_ids)
    parent = {sid: sid for sid in shape_ids}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path-compress
            parent[x], x = root, parent[x]
        return root

    for a in live:
        if a.get("type") != "arrow":
            continue
        s = (a.get("startBinding") or {}).get("elementId")
        t = (a.get("endBinding") or {}).get("elementId")
        if s in idset and t in idset:
            parent[find(s)] = find(t)

    comps = {}
    for sid in shape_ids:
        comps.setdefault(find(sid), []).append(sid)

    ex_of = {}
    for members in comps.values():
        votes = {}
        for sid in members:
            ex = nearest_example_pt(*center(byid[sid]), titles)
            votes[ex] = votes.get(ex, 0) + 1
        top = max(votes.values())
        winners = [ex for ex, n in votes.items() if n == top]
        if len(winners) == 1:
            chosen = winners[0]
        else:  # tie — break by the cluster centroid's nearest title
            cx = sum(center(byid[s])[0] for s in members) / len(members)
            cy = sum(center(byid[s])[1] for s in members) / len(members)
            chosen = nearest_example_pt(cx, cy, titles)
        for sid in members:
            ex_of[sid] = chosen
    return ex_of


def arrow_example(arrow, ex_of, titles):
    """An arrow's example is that of a bound endpoint shape (both ends share a
    component, so either works), falling back to nearest-title for an unbound end."""
    for which in ("startBinding", "endBinding"):
        sid = (arrow.get(which) or {}).get("elementId")
        if sid in ex_of:
            return ex_of[sid]
    return nearest_example(arrow, titles)


def describe(path):
    live = load_elements(path)
    if live is None:
        return
    byid = {e["id"]: e for e in live if "id" in e}
    texts = [e for e in live if e.get("type") == "text"]
    arrows = [e for e in live if e.get("type") == "arrow"]
    titles = [(text_of(t), *center(t)) for t in texts if EXAMPLE_RE.search(t.get("text", ""))]
    ex_of = shape_example_map(live, titles, byid)
    names, orderkey = assign_node_names(live, texts, titles, byid, ex_of)
    FAR = (10**9,)

    # Descriptions: prose blocks below a title. A default-coloured (misc) block
    # describes the WHOLE example (printed under the title); a layer-coloured block
    # (KEL/IEL/SEL/DOC by stroke colour) describes just THAT layer (printed in its box).
    desc_by = {}
    for t in texts:
        if not is_description(t):
            continue
        ex = nearest_example_pt(*center(t), titles)
        desc_by.setdefault((ex, layer_of(t)), []).append((center(t)[1], description_text(t)))

    print(f"\n# {path} — {len(arrows)} arrow(s), {len(live)} live element(s)")
    print("  layers by box colour: KEL=red  IEL=green  SEL=blue  DOC=orange"
          "  (arrows inherit their endpoints' layer; cross-layer listed apart)")
    print("  #N suffix = chain order (depth along `previous`); arrows sorted the same")

    # Nodes: every kind-labelled box, grouped by (example, layer via box colour).
    nodes_by = {}
    for e in live:
        if e.get("type") not in SHAPE_TYPES:
            continue
        ex = ex_of.get(e.get("id")) or nearest_example_pt(*center(e), titles)
        ok = orderkey.get(e.get("id"), FAR)
        nodes_by.setdefault((ex, layer_of(e)), []).append(
            (ok, names.get(e.get("id"), label_for(e, texts))))

    # Arrows: grouped by (example, layer). An arrow's layer is its endpoints' shared
    # layer, else 'cross-layer' (annotated start→end so inter-log bindings stand out).
    # Sorted by the start node's chain-order key so the listing follows the chain.
    arrows_by = {}
    for a in arrows:
        ex = arrow_example(a, ex_of, titles)
        _, s_el = endpoint_status(a, "startBinding", byid)
        _, e_el = endpoint_status(a, "endBinding", byid)
        sl, el_ = layer_of(s_el), layer_of(e_el)
        lay = sl if sl == el_ else "cross-layer"
        tag = f"   [{sl}→{el_}]" if lay == "cross-layer" else ""
        sk = orderkey.get(s_el.get("id"), FAR) if s_el else FAR
        row = (
            sk,
            endpoint_label(a, "startBinding", byid, texts, names),
            arrow_label(a, texts),
            endpoint_label(a, "endBinding", byid, texts, names),
            tag,
        )
        arrows_by.setdefault((ex, lay), []).append(row)

    all_ex = {ex for (ex, _lay) in list(nodes_by) + list(arrows_by) + list(desc_by)}
    for ex in sorted(all_ex):
        print(f"\n  ── {ex or '(no example title nearby)'} ──")
        for _cy, desc in sorted(desc_by.get((ex, "misc"), [])):  # whole-example (default colour)
            print(f"\n    {desc}\n")
        for lay in LAYER_ORDER:
            nlist = nodes_by.get((ex, lay))
            alist = arrows_by.get((ex, lay))
            dlist = desc_by.get((ex, lay)) if lay != "misc" else None  # layer-scoped note
            if not nlist and not alist and not dlist:
                continue
            print(f"    [{lay}]")
            for _cy, desc in sorted(dlist or []):
                print(f"      note: {desc}")
            if nlist:
                labs = [lab for _ok, lab in sorted(nlist)]
                print(f"      nodes: {', '.join(labs)}")
            for _sk, s, lab, e, tag in sorted(alist or []):
                arr = f" --[{lab}]-->" if lab else " -->"
                print(f"      {s:>20}{arr} {e}{tag}")


# ---- check mode ------------------------------------------------------------

def check(path):
    """Return (n_arrows, list_of_dangling, n_deleted). Each dangling is
    (arrow, problems, texts); n_deleted counts isDeleted carcasses (the clean-file
    gate — a clean commit has zero). Returns (0, None, 0) on parse error."""
    elements = parse_elements(path)
    if elements is None:
        return (0, None, 0)
    n_deleted = sum(1 for e in elements if e.get("isDeleted"))
    live = [e for e in elements if not e.get("isDeleted")]
    byid = {e["id"]: e for e in live if "id" in e}
    texts = [e for e in live if e.get("type") == "text"]
    arrows = [e for e in live if e.get("type") == "arrow"]
    dangling = []
    for a in arrows:
        problems = arrow_dangles(a, byid)
        if problems:
            dangling.append((a, problems, texts))
    return (len(arrows), dangling, n_deleted)


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
    element or its bindings — so it clears the isDeleted gate but cannot mask a
    dangling live arrow."""
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
    total_deleted = 0
    parse_errors = 0
    for path in drawings:
        n, dangling, n_deleted = check(path)
        if dangling is None:
            parse_errors += 1
            continue
        total_arrows += n
        total_dangling += len(dangling)
        total_deleted += n_deleted
        if dangling and args.verbose:
            print(f"\n{path}:", file=sys.stderr)
        for a, problems, texts in dangling:
            lab = arrow_label(a, texts)
            where = f"@({int(a.get('x', 0))},{int(a.get('y', 0))})"
            tag = f" «{lab}»" if lab else ""
            reasons = "; ".join(f"{end} {why}" for end, why in problems)
            print(f"ERROR  {path}  arrow {a.get('id', '?')[:8]} {where}{tag} — {reasons}",
                  file=sys.stderr)
        if n_deleted:
            print(f"ERROR  {path}  has {n_deleted} isDeleted element(s) — "
                  f"run `make lint-diagrams-prune` to clean", file=sys.stderr)

    status = total_dangling or parse_errors or total_deleted
    print(
        f"\nchecked {len(drawings)} drawing(s) | arrows: {total_arrows} | "
        f"dangling: {total_dangling}"
        + (f" | isDeleted: {total_deleted}" if total_deleted else "")
        + (f" | parse-errors: {parse_errors}" if parse_errors else "")
    )
    return 1 if status else 0


if __name__ == "__main__":
    sys.exit(main())
