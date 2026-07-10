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

        # Pass 2 (wrap-tolerant): a MULTI-WORD ban can wrap a line boundary and slip
        # past the line-based grep above (the exact hole the "majority floor" survivors
        # used). Take the space-containing patterns, widen each space to \s+ (which
        # matches a newline), and slurp-match each file with perl — whose \s spans
        # newlines, unlike BSD grep -z. Reports only genuinely-wrapped hits (same-line
        # ones are already covered by pass 1), grep-style: file:line: term.
        wrap_file=$(mktemp)
        grep ' ' "$pattern_file" | sed 's/ /\\s+/g' > "$wrap_file" || true
        if [ -s "$wrap_file" ]; then
            files_list=$(mktemp)
            printf '%s\n' "${scope[@]}" > "$files_list"
            if perl -e '
                my ($pf, $lf) = @ARGV;
                open(my $h, "<", $pf) or die; my @pats = grep { length } map { chomp; $_ } <$h>; close $h;
                open(my $l, "<", $lf) or die; my @files = grep { length } map { chomp; $_ } <$l>; close $l;
                my $hits = 0;
                for my $file (@files) {
                    next unless -f $file; next if -B $file;
                    open(my $f, "<", $file) or next; local $/; my $c = <$f>; close $f;
                    for my $p (@pats) {
                        while ($c =~ /$p/g) {
                            my $off = $-[0]; my $m = $&; next unless $m =~ /\n/;
                            my $line = (substr($c, 0, $off) =~ tr/\n//) + 1;
                            (my $show = $m) =~ s/\s+/ /g;
                            print "$file:$line: forbidden (line-wrapped): \"$show\"\n";
                            $hits = 1;
                        }
                    }
                }
                exit($hits ? 0 : 1);
            ' "$wrap_file" "$files_list"; then
                echo "ERROR: line-wrapped forbidden terminology found (rules: $forbid)"
                exit_code=1
            fi
            rm -f "$files_list"
        fi
        rm -f "$wrap_file"
    fi

    rm -f "$pattern_file"
done

exit $exit_code
