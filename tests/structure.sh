#!/bin/sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf 'pass: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'fail: %s\n' "$1"; }
file() { [ -f "$1" ] && pass "$2" || fail "$2"; }
has() { grep -qF -- "$2" "$1" 2>/dev/null && pass "$3" || fail "$3"; }

file "$ROOT/SKILL.md" "SKILL.md exists"
has "$ROOT/SKILL.md" "name: dopa-kernel" "frontmatter name"
has "$ROOT/SKILL.md" 'Use only when the user explicitly says `Dopa mode`' "explicit trigger"
has "$ROOT/SKILL.md" "Dopa mode: Work carefully and persist" "activation sentence"
LINES=$(wc -l < "$ROOT/SKILL.md" | tr -d ' ')
[ "$LINES" -le 110 ] && pass "kernel is at most 110 lines" || fail "kernel is at most 110 lines"
has "$ROOT/SKILL.md" "K1" "K1 present"
has "$ROOT/SKILL.md" "K2" "K2 present"
has "$ROOT/SKILL.md" "K3" "K3 present"
has "$ROOT/SKILL.md" "K4" "K4 present"
has "$ROOT/SKILL.md" "K5" "K5 present"
has "$ROOT/SKILL.md" "K6" "K6 present"
has "$ROOT/SKILL.md" "K7" "K7 present"
has "$ROOT/SKILL.md" "freeze the authorized envelope before acting" "envelope precedes action"
has "$ROOT/SKILL.md" "invoke exactly one domain adapter before work" "domain routing mandatory"
has "$ROOT/SKILL.md" "must not be implemented without authorization" "unauthorized substitution forbidden"
has "$ROOT/SKILL.md" "captured prior state, prepared rollback, and verification" "state-change gate"
has "$ROOT/SKILL.md" "fresh evidence for every envelope item" "completion evidence gate"
has "$ROOT/SKILL.md" "never enter the deliverable" "private process gate"
has "$ROOT/SKILL.md" "failure to invoke a module never authorizes" "invocation failure is safe"

for module in artifact decision execution combined proposal rollback stall-or-replan completion; do
  file "$ROOT/modules/$module.md" "$module module exists"
  has "$ROOT/SKILL.md" "modules/$module.md" "$module route exists"
done

has "$ROOT/SKILL.md" "BEFORE PERSISTENT STATE CHANGE" "state-change transition"
has "$ROOT/SKILL.md" "OUTSIDE-ENVELOPE ALTERNATIVE DETECTED" "proposal transition"
has "$ROOT/SKILL.md" "NO VERIFIED PROGRESS" "stall transition"
has "$ROOT/SKILL.md" "BEFORE FINAL RESPONSE" "completion transition"
has "$ROOT/SKILL.md" "unconditionally" "completion is unconditional"

has "$ROOT/modules/artifact.md" "expect[r]:" "artifact prediction"
has "$ROOT/modules/decision.md" "eliminated on a cited constraint" "decision evidence"
has "$ROOT/modules/execution.md" "exit status" "execution exit-status evidence"
has "$ROOT/modules/execution.md" "file hashes" "execution hash evidence"
has "$ROOT/modules/combined.md" "must match the commitment" "decision-execution binding"
has "$ROOT/modules/proposal.md" "Discovery never confers authorization" "proposal authority rule"
has "$ROOT/modules/proposal.md" "reduced, hedged, or disguised version" "partial adoption forbidden"
has "$ROOT/modules/rollback.md" "captured prior state" "rollback prior-state requirement"
has "$ROOT/modules/rollback.md" "verified restoration" "rollback restoration evidence"
has "$ROOT/modules/completion.md" "one line per envelope item" "per-item completion ledger"
has "$ROOT/modules/stall-or-replan.md" '`r = 0 ∧ i = 0`' "stall classification"
has "$ROOT/modules/stall-or-replan.md" "information loop" "information-loop guard"

file "$ROOT/reference/matrix.md" "matrix reference exists"
file "$ROOT/reference/quantities.md" "quantities reference exists"
has "$ROOT/reference/matrix.md" "2 × 3 × 3 = 18" "18-cell matrix preserved"
has "$ROOT/reference/matrix.md" "Lexicographic gate" "lexicographic gate"
has "$ROOT/reference/matrix.md" "Pareto partial order" "Pareto partial order"
has "$ROOT/reference/quantities.md" "never reconstruct it from hindsight" "hindsight calibration forbidden"
has "$ROOT/reference/quantities.md" '`i` can never close the gate' "information cannot complete work"

if grep -RIlE '/Users/|\.claude/evaluations|auth\.env|OAuth' \
  "$ROOT/SKILL.md" "$ROOT/modules" "$ROOT/reference" >/dev/null 2>&1; then
  fail "public engine contains no private paths or credentials"
else
  pass "public engine contains no private paths or credentials"
fi

printf '\n%d passed; %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
