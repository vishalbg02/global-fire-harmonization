# Task prompt: T-042 follow-up, the verdict map is black over land on real data

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 14bfacb
> Source of truth: the Lead's review of PR #49 (colour-only neutrals need a non-colour cue; accepted "pattern, outline or clearly separated tone") and my finding on PR #53, agreed by the user on 2026-11-15. A defect found in my own merged T-042 work; no new scope, no tracker row of its own (the Lead marks T-042).

## 1. The problem (observed on the real T-014 products)

In #49 I gave "no detected activity" cells in the Verdict layer a dark 1.5 px outline so they are not told apart by a pale fill alone. With the raw-only data those cells were rare. In the real products 65% of cell-months have no detected activity, so at world zoom the outlines of those half-degree cells merge and the land looks almost black.

## 2. The fix

- "No detected activity" gets a clearly separated pale blue tone instead of the outline (the icon stays at zoom, and the label is in the legend): [190, 215, 235], chosen by measuring CIEDE2000 against the land colour under normal vision and the three simulations (12.3 or more in all four; the earlier pale grey was 2.3). The dark outline stays only for "no data" in the activity layers (rare).
- The colour-vision tests are updated to match, and the legend shows the same cue.
- One pair stays just below the project's threshold (10): the new tone against the light grey of CANNOT_DETERMINE under protanopia (about 8.9). They differ by icon and label, and the test pins it as before.

## 3. Out of scope

Anything else in the map, the contract, the products.

## 4. Acceptance

- The Verdict layer on the real products is readable at world zoom (before and after screenshots).
- Lint, typecheck, tests and build pass; the colour-vision tests pass with the pinned pair.
