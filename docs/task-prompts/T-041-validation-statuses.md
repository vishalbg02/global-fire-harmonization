# Task prompt: T-041 follow-up, the methods page now that the real validation results are in

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 18715dc
> Source of truth: the Lead's reminders on #62 and #48 ("the methods page must show the T-027 statuses (18 PASS, 18 FAIL, 2 INCONCLUSIVE) once #70 lands ... confirm and attach a screenshot") and Member 2's note on #48 ("in the Calibration and Aqua drift sections, the sentences 'Test B3 ... has not been run' and 'test D1 ... has not been run' stay true until the recorded results are merged; reword them then"). No new scope.

## What I found (main after #70)
- `data/products/validation_results.json` has 38 tests: 18 PASS, 18 FAIL, 2 INCONCLUSIVE, none NOT_RUN, `synthetic: false`, method version 0.1.0. The page reads it unchanged and shows all 38 (statuses as text plus an icon, counts first, FAIL and INCONCLUSIVE with the heavier border), including the A1 family FAIL and D1-REGIONS-EACH and D1-NIGHT.
- Four passages of the page are no longer true: "test D1 ... has not been run", "Test B3 ... has not been run", "the recorded validation test D1, which stays 'not run'", and "OPEN: test D1 ... has not been run"; and the plan section is titled "Planned tests (not run yet)" although every test has a result.

## The change
Reword those passages to point to the recorded results below (no new claim about what they mean), drop the OPEN label that no longer applies, and retitle the plan section "Test plan: the pass rules fixed in advance" (still no statuses in it; the note says the results are above). Tests updated.
