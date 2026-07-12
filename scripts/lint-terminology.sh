#!/usr/bin/env bash
# Walks all .terminology-forbidden files in the tree. Each file's patterns
# apply to its own subtree. Deeper files replace shallower ones — when a
# file is covered by multiple forbid files, only the closest one applies.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Collect forbid files, deepest-first.
deep_first=()
while IFS= read -r f; do
    deep_first+=("$f")
done < <(
    git ls-files \
        | grep -E '(^|/)\.terminology-forbidden$' \
        | awk -F/ '{print NF, $0}' \
        | sort -rn \
        | cut -d' ' -f2-
)

if [ ${#deep_first[@]} -eq 0 ]; then
    exit 0
fi

# All tracked files we'll potentially scan.
all_files=()
while IFS= read -r f; do
    all_files+=("$f")
done < <(git ls-files \
    ':!:Makefile' \
    ':!:.terminology-forbidden' \
    ':!:**/.terminology-forbidden' \
    ':!:scripts/lint-terminology.sh')

# Track which files have been claimed by a deeper forbid file.
claimed_marker=$(mktemp)
trap 'rm -f "$claimed_marker"' EXIT

is_claimed() {
    grep -qxF "$1" "$claimed_marker" 2>/dev/null
}

mark_claimed() {
    printf '%s\n' "$1" >> "$claimed_marker"
}

exit_code=0

for forbid in "${deep_first[@]}"; do
    dir=$(dirname "$forbid")
    if [ "$dir" = "." ]; then
        prefix=""
    else
        prefix="$dir/"
    fi

    scope=()
    for f in "${all_files[@]}"; do
        if [ -n "$prefix" ]; then
            case "$f" in
                "$prefix"*) ;;
                *) continue ;;
            esac
        fi
        if is_claimed "$f"; then
            continue
        fi
        scope+=("$f")
        mark_claimed "$f"
    done

    if [ ${#scope[@]} -eq 0 ]; then
        continue
    fi

    pattern_file=$(mktemp)
    grep -vE '^(#|$)' "$forbid" > "$pattern_file" || true

    if [ -s "$pattern_file" ]; then
        # Pass 1 (line-based): precise file:line reporting for same-line hits —
        # unchanged behavior. -I: skip binary files (e.g. docs/design/canon.tar.xz,
        # a tracked archive whose bundled canon text would otherwise trip the rules).
        if printf '%s\n' "${scope[@]}" | xargs grep -nEI -f "$pattern_file"; then
            echo "ERROR: forbidden terminology found (rules: $forbid)"
            exit_code=1
        fi

        # Pass 2 (wrap- AND decoration-tolerant): a MULTI-WORD ban can wrap a line
        # boundary OR be split by Markdown emphasis/code markers (** _ ` ~) — either
        # slips the line-based grep above (the "majority floor" line-wrap survivors, and
        # a bold-hidden "governance **`Evl`**", both used this hole). scripts/grep-terms.pl
        # widens each space in the pattern to swallow those markers + a newline; --regex
        # keeps the ERE bans intact; --novel reports only the forms pass 1 misses, so it
        # never double-reports a same-line hit. Output is grep-style: file:line: match.
        multiword_file=$(mktemp)
        grep ' ' "$pattern_file" > "$multiword_file" || true
        if [ -s "$multiword_file" ]; then
            files_list=$(mktemp)
            printf '%s\n' "${scope[@]}" > "$files_list"
            if scripts/grep-terms.pl --regex --novel -f "$multiword_file" -F "$files_list"; then
                echo "ERROR: forbidden terminology (line-wrapped or Markdown-decorated) found (rules: $forbid)"
                exit_code=1
            fi
            rm -f "$files_list"
        fi
        rm -f "$multiword_file"
    fi

    rm -f "$pattern_file"
done

exit $exit_code
