<!--
Fallback for the DESCRIPTION of a Linear phase sub-issue (not a file on disk),
used when the workspace has no `Phase` issue template. It mirrors that template;
when the template exists, follow it instead (create-epic Step 3c, 0b).

- Title (set separately): `Phase <NN.M> — <phase title>`, the short name from the
  phase heading.
- Goal: the phase's one-sentence goal.
- Acceptance criteria: ALWAYS a plain bullet list (one bullet per criterion) —
  copy every item from the phase's `### Acceptance criteria` block, dropping the
  `- [ ]` checkbox syntax. The list ends with the standing `Lint and tests pass.`
- Tasks: leave the placeholder line as-is at epic time. create-plan replaces it
  with the plan's task list (one bullet per TASK) once the plan exists.
- Footer: name the epic by its Linear title, `<NN> — <Epic Title In Title Case>`.
-->

## Goal

<one-sentence goal>

## Acceptance criteria

- <criterion 1>
- <criterion 2>
- Lint and tests pass.

## Tasks

_Filled in from the plan once `create-plan` runs._

---

Phase `<NN.M>` of epic **<NN> — <Epic Title In Title Case>**. Local plan lives at
`docs/artifacts/plans/<slug>/PLAN.md`
