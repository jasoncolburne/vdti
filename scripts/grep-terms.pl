#!/usr/bin/env perl
# grep-terms — decoration- and wrap-tolerant phrase search over Markdown.
#
# Markdown emphasis/code markers (* _ ` ~) sit at word boundaries, so a plain
# grep for a multi-word term misses its decorated forms:  "governance Evl"  does
# not match  "governance **`Evl`**".  Line-wrapping hides them the same way.  This
# tool widens each whitespace gap in a term so it also matches the marker-padded
# and line-wrapped forms, then reports file:line like grep.  Each word's initial
# letter is also matched in either case (so "governance" finds a sentence-start
# "Governance" too) without going fully case-insensitive.
#
# Direct use (literal phrases; the reason this exists — one-shot straggler sweeps):
#   scripts/grep-terms.pl [-i] [-w] PHRASE [PHRASE ...] [-- PATH ...]
#     scripts/grep-terms.pl "governance Evl" "sealing kind"
#   Paths default to every tracked *.md; pass files/dirs to narrow.
#
# Lint use (ERE patterns from a file; report only the forms a same-line grep
# misses, so it complements — never double-reports — the line-based pass):
#   scripts/grep-terms.pl --regex --novel -f PATTERNS -F FILES
#
# Exit 0 if any match, 1 if none (grep-like), 2 on a usage error.

use strict;
use warnings;
use utf8;
use open qw(:std :encoding(UTF-8));
use Encode qw(decode_utf8);
use Getopt::Long qw(:config bundling no_ignore_case);

# Split trailing paths off at the first "--" BEFORE GetOptions (which would
# otherwise consume the separator itself). Everything after "--" is a path.
my @paths;
for my $i (0 .. $#ARGV) {
    if ($ARGV[$i] eq '--') {
        @paths = @ARGV[$i + 1 .. $#ARGV];
        @ARGV  = @ARGV[0 .. $i - 1];
        last;
    }
}

my %o;
GetOptions(\%o, 'i', 'w', 'regex|r', 'novel', 'f=s', 'F=s') or exit 2;

# --- patterns: from -f FILE (one per line) and/or the remaining positional args ---
my @phrases;
if ($o{f}) {
    open my $h, '<', $o{f} or die "grep-terms: cannot read $o{f}: $!\n";
    push @phrases, grep { length } map { chomp; $_ } <$h>;
    close $h;
}
# Command-line args arrive as raw BYTES; file contents are read as CHARACTERS (the
# `use open` layer above). Matching an undecoded byte-string pattern against a decoded
# subject can never hit, so any phrase containing a non-ASCII character — "≥ 2",
# "(MIN − 2)/4", an arrow, a ★ — returned ZERO SILENTLY, which reads as "clean".
# Decode the phrases only: paths and -f/-F filenames stay bytes, which is what open()
# and -f want. Phrases from -f are already decoded by the layer.
push @phrases, map { decode_utf8($_) } @ARGV;
die "grep-terms: no phrases (give them positionally or via -f)\n" unless @phrases;

# --- files: from -F FILE, else the given paths (dirs/globs expanded via git), else all tracked *.md ---
my @files;
if ($o{F}) {
    open my $h, '<', $o{F} or die "grep-terms: cannot read $o{F}: $!\n";
    @files = grep { length } map { chomp; $_ } <$h>;
    close $h;
} elsif (@paths) {
    for my $p (@paths) {
        if    (-f $p) { push @files, $p; }
        elsif (-d $p) {
            # A directory of UNTRACKED files (e.g. .working/) expands to nothing via git —
            # fall back to a filesystem walk so the sweep searches what the caller named.
            my @g = grep { length } split /\n/, `git ls-files -- '$p/**/*.md' '$p/*.md' 2>/dev/null`;
            @g = grep { length } split /\n/, `find '$p' -type f -name '*.md' 2>/dev/null` unless @g;
            push @files, @g;
        }
        else          { push @files, split /\n/, `git ls-files -- '$p' 2>/dev/null`; }
    }
} else {
    @files = split /\n/, `git ls-files -- '*.md' 2>/dev/null`;
}
@files = grep { length } @files;

# An EMPTY file list must never look like a clean sweep. A nonexistent path, an unsplit
# shell variable of paths, or a directory whose files are untracked all resolved to zero
# files and exited 1 with no output — indistinguishable from "searched everything, found
# nothing". Same silent-wrong-clean class as the byte/char defect. Fail as a usage error.
die "grep-terms: no files to search"
  . (@paths ? " (paths resolved to nothing: @paths)" : "")
  . " — a zero-file sweep is not a clean sweep\n"
  unless @files;

# --- build a marker+wrap-tolerant regex per phrase ---
my $MK  = '[*_`~]*';              # an optional run of emphasis/code markers
# The gap must also cross a BLOCKQUOTE continuation prefix ("> ", nested "> > "): a phrase that
# wraps inside a blockquote puts "\n> " between two of its words, and a gap of bare \s+ returned
# ZERO SILENTLY — the third silent-wrong-clean defect, and it bites hardest on exactly the material
# that lives in blockquotes (normative rules, constants). Mid-line "a > b" now also matches "a b";
# over-reporting is the correct failure direction for a sweep tool.
my $GAP = $MK . '(?:\s+(?:>[ \t]*)*)+' . $MK;   # inter-token gap: markers, whitespace (+ "> " prefixes), markers
sub build {
    my ($p) = @_;
    my @tok = grep { length } split /\s+/, $p;   # only literal-space phrases get widened
    return undef unless @tok;
    @tok = map { $o{regex} ? $_ : quotemeta } @tok;   # --regex keeps ERE tokens; default is literal
    # First-letter case variant per word: match either case at each word's initial
    # letter, so "sealing kind" also finds "Sealing kind" / "Sealing Kind" (sentence
    # starts, headings, bold labels) without going fully case-insensitive.
    s/^([A-Za-z])/'[' . lc($1) . uc($1) . ']'/e for @tok;
    my $re = $MK . join($GAP, @tok);                  # allow leading markers
    $re = '(?<!\w)' . $re . '(?!\w)' if $o{w};        # -w: word-ish boundaries
    return $o{i} ? qr/$re/i : qr/$re/;
}
my @res = grep { defined } map { build($_) } @phrases;
exit 1 unless @res;

# --- search (slurp each file so \s+ can cross newlines) ---
my $hits = 0;
for my $file (@files) {
    next unless -f $file && !-B $file;
    open my $fh, '<', $file or next;
    local $/; my $c = <$fh>; close $fh;
    for my $re (@res) {
        while ($c =~ /$re/g) {
            my ($off, $m) = ($-[0], $&);
            # --novel: skip a plain same-line hit (no newline, no marker) — the
            # caller's line-based pass already reports those.
            next if $o{novel} && $m !~ /\n/ && $m !~ /[*_`~]/;
            my $line = 1 + (substr($c, 0, $off) =~ tr/\n//);
            # Show the full source line(s) the match sits on (grep-style context), not
            # just the matched term — a bare-term report forces a second grep to tell,
            # say, the "band" constant from "out-of-band". A wrap-spanning match shows
            # both lines, whitespace-collapsed to one.
            my $ls = rindex($c, "\n", $off) + 1;
            my $le = index($c, "\n", $+[0]);
            $le = length($c) if $le < 0;
            (my $show = substr($c, $ls, $le - $ls)) =~ s/\s+/ /g;
            $show =~ s/^ | $//g;
            print "$file:$line: $show\n";
            $hits = 1;
        }
    }
}
exit($hits ? 0 : 1);
