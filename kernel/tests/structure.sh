#!/bin/sh
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'pass: %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'fail: %s\n' "$1"; }
has() { grep -qF -- "$2" "$1" 2>/dev/null && pass "$3" || fail "$3"; }
absent() { grep -qF -- "$2" "$1" 2>/dev/null && fail "$3" || pass "$3"; }
exists() { [ -f "$1" ] && pass "$2" || fail "$2"; }

K="$ROOT/SKILL.md"
exists "$K" "kernel exists"
has "$K" 'name: dopa-kernel' "frontmatter name"
has "$K" 'Dopa mode' "explicit activation trigger"
has "$K" '**Frame.**' "frame retained"
has "$K" '**Predict.**' "predict retained"
has "$K" '**Act.**' "act retained"
has "$K" '**Observe.**' "observe retained"
has "$K" '**Compare.**' "compare retained"
has "$K" '`r` progress' "progress channel retained"
has "$K" '`i` information' "information channel retained"
has "$K" '`δ` surprise' "prediction error retained"
has "$K" 'Never sum them' "progress and information stay separate"
has "$K" 'goal contract' "goal contract required"
has "$K" 'decide.py start' "durable goal start named"
has "$K" 'requirement_id' "candidate must serve a requirement"
has "$K" 'decision-critical' "research must be decision critical"
has "$K" 'decide.py verify' "frozen verifier command named"
has "$K" 'fresh' "fresh evidence required"
has "$K" 'mutation generation' "post-verification mutation is handled"
has "$K" 'dopa-outcome.json' "observed semantic outcome is persisted"
has "$K" 'decide.py block' "impossible has a supported transition"
has "$K" 'decide.py evaluate' "independent evaluator named"
has "$K" 'met / not_met / impossible' "terminal verdicts documented"
has "$K" 'proposal, never a substitution' "out-of-frame proposal boundary"
has "$K" 'native permission prompt' "terminal transitions require native approval"
absent "$K" 'modules/' "legacy module bureaucracy not restored"
absent "$K" '4/5' "burned evaluation score not claimed in skill"

for file in model.py policy.py evaluator.py decide.py gate_decide.py gate_tests.py; do
  exists "$ROOT/kernel/$file" "$file exists"
done
has "$ROOT/kernel/gate_decide.py" 'state_lock' "mutation authorization is atomic"
has "$ROOT/kernel/gate_decide.py" 'Unknown shell commands are mutations' "unknown shell fails conservative"
has "$ROOT/kernel/gate_tests.py" 'never' "stop gate rejects transcript prose"
has "$ROOT/kernel/gate_tests.py" 'evaluator.evaluate' "stop routes to evaluator"
exists "$ROOT/reference/goal-contract.md" "goal contract reference exists"
has "$ROOT/reference/goal-contract.md" 'cannot target `.dopa/`' "verifiers cannot use controller state"
absent "$ROOT/reference/goal-contract.md" '"user_authorized": true' "cancel schema has no self-asserted authorization"
exists "$ROOT/adapters/claude/SKILL.md" "Claude loader adapter exists"
has "$ROOT/adapters/claude/SKILL.md" '../../SKILL.md' "adapter routes to canonical skill"
has "$ROOT/README.md" '"matcher": "*"' "Claude hook covers every tool name"
has "$ROOT/README.md" 'cooperative but fallible' "semantic threat model is explicit"
has "$ROOT/README.md" 'Host sandbox and permissions own execution authority' "platform owns execution security"
has "$ROOT/README.md" 'Dabney' "distributional RPE grounds the unsummed axes"
has "$ROOT/README.md" 'Bayer' "separate negative encoding grounds the regression channel"
has "$ROOT/README.md" 'Tobler' "cue-set gain grounds declared importance"
has "$ROOT/README.md" 'Niv' "pacing derivation is recorded even though it was cut"
has "$ROOT/README.md" 'promoted into the kernel' "unadopted pacing is not presented as live"
has "$ROOT/README.md" 'Three of four results survived that filter' "adoption filter is stated"
exists "$ROOT/legacy/README.md" "legacy preserved for reference"

# ---- publication hygiene ----
# legacy/tests/structure.sh guards the v0.1 tree only. This repository is
# public, so the live tree needs the same check: no personal machine paths and
# no credentials in anything shipped.
# --exclude is required: this file spells the pattern out, so without it the
# check matches itself and fails forever.
if grep -RIlE --exclude=structure.sh \
  '/Users/|/home/[a-z]|\.claude/evaluations|auth\.env|OAuth|api[_-]?key *=|BEGIN [A-Z ]*PRIVATE KEY' \
  "$ROOT/SKILL.md" "$ROOT/README.md" "$ROOT/reference" "$ROOT/kernel" "$ROOT/adapters" \
  >/dev/null 2>&1; then
  fail "live tree contains no private paths or credentials"
else
  pass "live tree contains no private paths or credentials"
fi

# .dopa/goal.json holds the user's real objectives, notes and attempt history.
# It must never be committable.
if grep -qF '.dopa/' "$ROOT/.gitignore" 2>/dev/null; then
  pass "controller state is gitignored"
else
  fail "controller state is gitignored"
fi

printf '\n%d passed; %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
