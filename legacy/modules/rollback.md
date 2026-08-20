# Procedure — safeguard before a persistent state change

Invoked from the router before a persistent state change. K4 has
already blocked the action; this module says how to make it safe. It
elaborates K4 and never waives it.

## Before acting

1. Require a captured prior state — the bytes, the hash, the copy, or the
   recorded values that will let you prove restoration later. A memory of the
   prior state is not a captured prior state.
2. **State the rollback** in the process channel: the exact steps that would
   undo this action, written before the action, not improvised after it.
3. **Confirm reversibility.** If the step cannot be undone, or if restoration
   could not be verified afterwards, it is ineligible. Irreversible or
   unverifiable damage is never justified by what might be learned.

## After acting

4. Verify the intended new state and check for regression. A successful
   authorized change is retained; rollback is protection, not an instruction
   to undo correct work.
5. If the action regressed state or failed its check, execute the prepared
   rollback and require verified restoration by observation — re-hash, re-read,
   or re-run the check. Restoration asserted is restoration unproven.
6. Classify the outcome only after the new state passes verification or the
   prior state has been verified restored.

## Regression floor

Never prefer an outcome expected to regress the work over a non-regressing one
merely because it offers more information. If a regression has already
happened, restoring or repairing it comes before any further improvement.

## If restoration fails

Stop. Do not continue improving on top of a known-worse state. Record what was
captured, what was attempted, and what remains broken, and surface it — an
unrestored regression is a gate failure, not a detail.
