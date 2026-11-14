# Task prompts

This folder holds one implementation prompt per assigned task: `T-XXX-<short-name>.md`.

- **Who writes them:** the assigned teammate's Claude session, from the template in [`../TEAM_WORKFLOW.md`](../TEAM_WORKFLOW.md) §4. They are generated only after the Project Lead has assigned the task in `../TASK_TRACKER.md`.
- **Where they're committed:** as the **first commit** on the task branch, so the Lead can compare the PR against the prompt.
- **Scope:** a prompt never adds work beyond the tracker entry. Ambiguities are listed in its §15 for the Lead to resolve.
- **Self-contained:** a prompt must work in any Claude Code session or account without chat history.

- **Relation to the workstream prompts:** `../prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` and `../prompts/MEMBER_3_APPLICATION_PROMPT.md` describe each member's whole workstream. A task prompt here may reference their sections instead of repeating them, but it must still state the task's exact files, outputs, tests and acceptance criteria.

No task prompts exist yet. No implementation task has been assigned. Stack-dependent tasks wait for D-008, and contract-dependent tasks for D-016.
