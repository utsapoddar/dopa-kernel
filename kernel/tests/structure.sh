#!/bin/sh
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'pass: %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'fail: %s\n' "$1"; }
has() { grep -qF -- "$2" "$1" 2>/dev/null && pass "$3" || fail "$3"; }
absent() { grep -qF -- "$2" "$1" 2>/dev/null && fail "$3" || pass "$3"; }

K="$ROOT/SKILL.md"
[ -f "$K" ] && pass "kernel exists" || fail "kernel exists"
LINES=$(wc -l < "$K" | tr -d ' ')
[ "$LINES" -le 70 ] && pass "kernel stays under 70 lines (got $LINES)" \
                    || fail "kernel stays under 70 lines (got $LINES)"
has "$K" 'name: dopa-kernel' "frontmatter name"
has "$K" 'Dopa mode' "activation trigger"
# the six moves
has "$K" '**Frame.**' "1 frame"
has "$K" '**Predict.**' "2 predict"
has "$K" '**Act.**' "3 act"
has "$K" '**Observe.**' "4 observe"
has "$K" '**Compare.**' "5 compare"
has "$K" 'Never claim done against a failing observation' "6 the hard rule"
# the readings survive the cut
has "$K" '`r` progress' "r is defined"
has "$K" '`i` information' "i is defined"
has "$K" '`δ` surprise' "delta is defined"
has "$K" 'advanced' "r values"
has "$K" 'decision-changing' "i values"
has "$K" 'unscorable' "no hindsight delta"
has "$K" 'Never sum them' "readings are never collapsed"
has "$K" 'imp: 1-5' "stakes scale"
has "$K" 'how hard the evidence has to be to fake' "importance raises the bar"
has "$K" 'never lowers the evidence bar' "urgency cannot cut the floor"
has "$K" 'proposal, never a substitution' "out-of-frame is a proposal"
# the bloat must not come back
absent "$K" 'modules/' "no module routing table"
absent "$K" 'cell[' "no cell bookkeeping"
absent "$K" '2 × 3 × 3' "no matrix defined in the kernel"
absent "$K" 'unconditionally' "no unconditional module invocation"
[ -f "$ROOT/kernel/gate_tests.py" ] && pass "the one gate exists" || fail "the one gate exists"
has "$ROOT/kernel/gate_tests.py" 'cannot author' "the gate reads unauthored evidence"
[ -d "$ROOT/legacy" ] && pass "legacy preserved for reference" || fail "legacy preserved for reference"
printf '\n%d passed; %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
