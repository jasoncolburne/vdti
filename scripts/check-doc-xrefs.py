#!/usr/bin/env python3
"""Check Markdown cross-references across the docs tree.

For every inline link in a tracked Markdown file:

  - relative links must resolve to an existing file or directory;
  - a `#anchor` must match a heading slug (GitHub-compatible) or an explicit
    `<a id="...">` / `<a name="...">` in the target file;
  - same-file `#anchor` links are validated against the file's own headings.

Links inside fenced code blocks are skipped (ASCII diagrams, sample shapes).
External links (`http:`, `mailto:`, ...) are ignored.

Forward-references to files that do not exist yet (later sub-issues) are
tolerated via `.docs-xref-ignore` at the repo root: one glob per line, matched
against the resolved repo-relative path, `#` for comments. Use `--strict` to
treat those ignored-missing targets as errors too.

Usage:
    scripts/check-doc-xrefs.py [PATH ...]   # default: all tracked *.md
    scripts/check-doc-xrefs.py docs/design  # restrict to a subtree
    scripts/check-doc-xrefs.py --strict     # ignored forward-refs become errors
    scripts/check-doc-xrefs.py -v           # also list resolved (OK) links

Exit status: 0 when there are no errors, 1 otherwise.
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys

# Inline link: [text](target).  text may contain backticks/spaces; target is
# captured up to the closing paren.  Image links (![]) are matched too.
LINK_RE = re.compile(r"!?\[(?:[^\]]*)\]\(\s*([^)]+?)\s*\)")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
EXPLICIT_ANCHOR_RE = re.compile(r'<a\s+(?:id|name)\s*=\s*"([^"]+)"')
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def repo_root():
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def slugify(text):
    """GitHub-compatible heading slug: lowercase, drop punctuation other than
    word chars / hyphen / space, then spaces to hyphens (no hyphen collapsing)."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    s = s.replace(" ", "-")
    return s


def _iter_content_lines(path):
    """Yield non-fenced lines of a file, tracking ``` / ~~~ fences."""
    in_fence = False
    fence_char = None
    try:
        text = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return
    for lineno, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if m:
            char = m.group(1)[0]
            if not in_fence:
                in_fence, fence_char = True, char
            elif char == fence_char:
                in_fence, fence_char = False, None
            continue
        if in_fence:
            continue
        yield lineno, line


def anchors_of(path):
    """The set of valid in-file anchors, matching GitHub's slug + dedup rules
    (a repeated heading slug gets `-1`, `-2`, ... appended)."""
    anchors = set()
    seen = {}
    for _lineno, line in _iter_content_lines(path):
        m = ATX_RE.match(line)
        if m:
            base = slugify(m.group(2))
            n = seen.get(base, 0)
            anchors.add(base if n == 0 else f"{base}-{n}")
            seen[base] = n + 1
        for am in EXPLICIT_ANCHOR_RE.finditer(line):
            anchors.add(am.group(1))
    return anchors


def links_of(path):
    """Yield (lineno, target) for each inline link outside fenced code."""
    for lineno, line in _iter_content_lines(path):
        scrubbed = INLINE_CODE_RE.sub("", line)
        for m in LINK_RE.finditer(scrubbed):
            target = m.group(1).strip()
            if target.startswith("<") and ">" in target:
                target = target[1 : target.index(">")]
            else:
                # drop an optional link title:  ](url "title")
                parts = target.split(None, 1)
                if parts:
                    target = parts[0]
            yield lineno, target


def collect_md_files(root, paths):
    if not paths:
        out = subprocess.check_output(["git", "ls-files", "*.md"], text=True)
        return [p for p in out.splitlines() if p]
    files = []
    for p in paths:
        ap = os.path.abspath(p)
        if os.path.isdir(ap):
            for dirpath, _dirs, names in os.walk(ap):
                for name in names:
                    if name.endswith(".md"):
                        files.append(os.path.relpath(os.path.join(dirpath, name), root))
        elif p.endswith(".md"):
            files.append(os.path.relpath(ap, root))
    return files


def load_ignore(root):
    patterns = []
    path = os.path.join(root, ".docs-xref-ignore")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                patterns.append(line)
    return patterns


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check Markdown cross-references.")
    ap.add_argument("paths", nargs="*", help="files or directories (default: all tracked *.md)")
    ap.add_argument("--strict", action="store_true",
                    help="treat ignored (forward-ref) missing targets as errors")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="also print resolved links and skipped forward-refs")
    args = ap.parse_args(argv)

    root = repo_root()
    os.chdir(root)

    ignore = load_ignore(root)
    md_files = collect_md_files(root, args.paths)

    anchor_cache = {}

    def anchors(path):
        if path not in anchor_cache:
            anchor_cache[path] = anchors_of(path)
        return anchor_cache[path]

    errors = []        # (src, lineno, target, message)
    forward_refs = []  # (src, lineno, target, resolved)
    ok = 0

    for src in md_files:
        srcdir = os.path.dirname(src)
        for lineno, target in links_of(src):
            if not target or SCHEME_RE.match(target):
                continue

            path_part, _, anchor = target.partition("#")

            # Same-file anchor link.
            if path_part == "":
                if anchor and anchor not in anchors(src):
                    errors.append((src, lineno, target, "same-file anchor not found"))
                else:
                    ok += 1
                continue

            resolved = os.path.normpath(os.path.join(srcdir, path_part))

            if not os.path.exists(resolved):
                ignored = any(fnmatch.fnmatch(resolved, pat) for pat in ignore)
                if ignored and not args.strict:
                    forward_refs.append((src, lineno, target, resolved))
                else:
                    suffix = " (forward-ref, --strict)" if ignored else ""
                    errors.append((src, lineno, target, f"target not found: {resolved}{suffix}"))
                continue

            if anchor:
                if os.path.isfile(resolved):
                    if anchor not in anchors(resolved):
                        errors.append((src, lineno, target, f"anchor not found in {resolved}"))
                    else:
                        ok += 1
                else:
                    # anchor against a directory — can't validate; accept the path.
                    ok += 1
            else:
                ok += 1

    if args.verbose:
        for src, lineno, target, resolved in forward_refs:
            print(f"  forward-ref  {src}:{lineno}  {target}  -> {resolved}")

    for src, lineno, target, msg in errors:
        print(f"ERROR  {src}:{lineno}  {target}  — {msg}", file=sys.stderr)

    print(
        f"\nchecked {len(md_files)} file(s) | "
        f"OK: {ok} | errors: {len(errors)} | forward-refs: {len(forward_refs)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
