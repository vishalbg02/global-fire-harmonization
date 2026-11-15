# Task prompt: T-091 Scroll-hint test passes on every platform

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 (T-089, T-090, T-091 batch; "T-091, the Windows/Linux test fix", moved from Member 3).

## Task
`app/src/components/map/mapUx.test.tsx` "the scroll hint is on the map" builds a regular expression from `SCROLL_HINT` (`Use Ctrl + scroll to zoom the map`). In a regular expression `+` is an operator, so the pattern needs two spaces and fails wherever `navigator.platform` is not a Mac (Windows, Linux). Fix the test and run it with `navigator.platform` set to Win32, Linux and MacIntel.

## Files
Modify: `app/src/components/map/mapUx.test.tsx` only. The component (`mapOverlays.tsx`) is correct and is not changed.

## Requirements
Plain string checks, no regular expression built from the hint. For each of Win32, Linux and MacIntel the stub of `navigator.platform` is restored afterwards. Win32 and Linux show `SCROLL_HINT`, MacIntel shows `SCROLL_HINT_MAC`, and the touch hint is always present. A mutation check: the old pattern fails on the Win32 stub.

## Git
Branch `frontend/T-091-scroll-hint-test` from the latest `main`; first commit: this prompt; PR with the template; never merge; human identity, no AI attribution (D-020).
