---
name: create-plan
description: Author an implementation plan — a PLAN.md dashboard plus per-task files under docs/artifacts/plans/<slug>/ — before writing code. Use when the task is ambiguous, spans multiple files, or carries non-trivial risk, when the user asks to plan first, or to turn one epic phase into a plan (--epic/--phase). Skip for single-line fixes with obvious scope.
argument-hint: "[--epic <NN> --phase <NN.M>] [<path-to-existing-exploration-file>]"
---

# Create Plan

Author an implementation plan under `docs/artifacts/plans/<slug>/`: explore the code, interview the user, resolve every open question, then scaffold `PLAN.md` plus one file per task. The plan is optionally hardened by `validate-plan`, gets its tests written first by `tdd-plan`, then is executed task-by-task by `implement-plan`.

## Arguments

- `--epic <NN>` and `--phase <NN.M>` *(optional, used together)* — the epic and phase this plan implements (an epic file under `docs/artifacts/epics/`). When provided, the plan is linked to the epic phase both ways in Phase 4.
- `<path-to-existing-exploration-file>` *(optional)* — path to a previously created exploration file

## Workflow

### Phase 1 — Exploration

Before interviewing the user, gather enough context to ask intelligent questions and avoid false assumptions.

1. Read `AGENTS.md` (project root) and `CLAUDE.md` if present — understand project conventions, module boundaries, and constraints.
2. If `--epic`/`--phase` were provided, read the epic file `docs/artifacts/epics/<NN>-*.md` in full — especially that phase's Goal, `### What to build`, and `### Acceptance criteria`. The plan must satisfy them, and they pre-fill much of the plan's Goal, Scope, and Acceptance Criteria.
3. If `<path-to-existing-exploration-file>` was provided, load the file and extract relevant context. Use this as the primary source of truth for the user's intent and pre-fill as many interview answers as possible.
4. Locate the relevant entry points, types, services, and tests for the requested change.
5. Follow imports/calls enough to understand how the pieces connect.
6. Check recent git log for related changes: `git log --oneline -20`.
7. Note: files likely to change, existing patterns to follow, constraints, and any uncertainty.

Prefer the `Explore` subagent for broad or cross-file research.

Do **not** start the user interview until exploration is complete.

---

### Phase 2 — Requirements Interview

Use `AskUserQuestion` (structured questions with choices) rather than prose open questions. Never list unresolved questions in text — if something is unclear, ask it directly via the tool.

Gather at minimum:
- **Goal** — what outcome the user wants, not just what to build
- **Constraints** — deadlines, backward-compat, platform limits, API contracts
- **Non-goals** — what is explicitly out of scope
- **Risk tolerance** — how careful to be (e.g. is this on a critical path?)
- **Success criteria** — how the user will know it worked

Only ask about genuinely open points. Ask follow-up questions if answers surface new ambiguity. Do not produce the plan until all open questions are resolved.

---

### Phase 3 — Plan Authoring

Before writing artifacts, maintain a running working document (in your context, not written to disk) with:

- **Decisions made** — each with rationale
- **Open questions** — with resolution status
- **Assumptions** — explicit statements of what is taken as given
- **Risks** — and mitigations
- **Rejected ideas** — and why

Walk design branches. If two approaches exist, reason through both and pick one with rationale. Do not leave ambiguity in the plan.

#### Risk Classification

| Risk | Description |
|------|-------------|
| `tiny` | < 30 min, single file, no tests needed |
| `small` | < 2 h, isolated change, existing tests cover it |
| `medium` | Half-day, cross-file, new tests required |
| `large` | Multi-day, architectural change, significant test work |
| `high` | Critical path, infrastructure, or breaking change |

RESEARCH.md is required for `medium`, `large`, and `high` risk plans. `init_plan.py` creates it automatically based on `--risk`.

#### Task Numbering

Handled by `scripts/add_task.py` and `scripts/add_final_task.py` — they read existing files in `tasks/` and assign the next `TASK-NNN`. The final-validation task takes the next sequential number, not a fixed `TASK-999`. Do not invent numbers yourself.

---

### Phase 4 — Scaffold, then Fill In

File and directory creation is handled by helper scripts in `scripts/`. Your job is to invoke them in order, then fill in the prose content the scripts can't write.

#### Step 1: Scaffold the plan

```bash
python3 ~/.claude/skills/create-plan/scripts/init_plan.py \
  --title "<title>" --risk <tier> [--slug <slug>]
```

Creates `docs/artifacts/plans/<slug>/PLAN.md` with metadata pre-filled (Status, Risk, Created), plus `RESEARCH.md` when the risk warrants it, and an empty `tasks/` directory. Prints the slug used.

#### Step 2: Add tasks

For each task in your decomposition, run:

```bash
python3 ~/.claude/skills/create-plan/scripts/add_task.py <slug> \
  --type <impl|checklist> --title "<task title>" [--depends TASK-001,TASK-002]
```

Use `--type impl` for code work (RED/GREEN/REFACTOR template) or `--type checklist` for non-code work. The script picks the next `TASK-NNN`, stamps out the task file, and appends a checkbox line to `PLAN.md`. It prints the assigned id.

#### Step 3: Add the final-validation task

```bash
python3 ~/.claude/skills/create-plan/scripts/add_final_task.py <slug>
```

#### Step 3b: Link the plan to its epic phase (only if `--epic`/`--phase` were given)

```bash
python3 ~/.claude/skills/create-epic/scripts/link_plan.py <NN> \
  --phase <NN.M> --plan <slug> --status planned
```

This writes the link both ways: it fills `PLAN.md`'s `Epic:` and `Phase:` fields with the resolved epic/phase titles and a relative link to the epic, and sets the epic phase's `**Plan**:` line to point back at this plan with `status: planned`. If the phase carries a Linear sub-issue id (its `**Linear**:` line), that id is also copied into `PLAN.md`'s `Linear:` field — which is what `implement-plan` reads to name the branch and `create-pr` reads for the `Closes` line. Skip this step for standalone plans not tied to an epic (their `Epic:`/`Phase:`/`Linear:` stay `none`). The phase status is later advanced by `implement-plan` (`in-progress`) and the final-validation task (`done`).

**Linear (only if wired — see `~/.claude/skills/shared/linear-integration.md`):** if the link copied a sub-issue id into `PLAN.md`'s `Linear:` field (not `none`), update that sub-issue's description so its **Tasks** section lists this plan's tasks — one bullet per task, using the titles from `PLAN.md`'s `## Tasks` list (including the final-validation task). This replaces the placeholder from `create-epic`'s phase template; leave the Goal and Acceptance criteria sections intact. Use `mcp__linear-server__save_issue`. In the same update, move the sub-issue to **Todo** if it isn't already (skip if the team has no Todo state) — a planned phase should sit in Todo, not Backlog. Skip for standalone plans (`Linear: none`).

#### Step 4: Fill in content

Open each stamped file and replace placeholder content with real values:

- **`PLAN.md`** — Goal, Scope, Out of Scope, Research Summary, Decisions, Risks, Acceptance Criteria. (Status, Risk, Created, and the task list are already populated.)
- **`RESEARCH.md`** (if created) — curated findings from Phase 1.
- **`DECISIONS.md`** (write manually only when ≥2 real options were weighed) — copy `references/template-decisions.md` and link from `PLAN.md`'s `## Decisions` section instead of restating.
- **Each task file** — Goal, Files, Acceptance, Steps. Delete the `## Notes` section if empty.

This step is complete only when a grep across the plan dir finds **no remaining template placeholder text** (`TODO`, angle-bracket stubs) — every hit is either replaced with real content or deliberately deleted.

#### Rules

- Do not run the scripts until all open questions are resolved.
- For `medium`/`large`/`high` risk plans, confirm the final plan with the user before scaffolding.
- Run scripts in order: `init_plan.py` → `add_task.py` (×N) → `add_final_task.py` → (if linked) `link_plan.py`. Never invent task numbers.
- Don't hand-edit `PLAN.md`'s `Epic:`/`Phase:` fields or the epic's `**Plan**:` line — `link_plan.py` owns both sides of the link.
- A plan implements exactly one epic phase. If the work spans several phases, it's mis-scoped — split it, or revisit the epic's phase boundaries with `create-epic`.
- Task state lives only in `PLAN.md`'s `## Tasks` checkboxes. Do not add `Status:` fields back to task files.
- Use `--type impl` for code work, `--type checklist` for non-code work — not both for the same task.
- All tests must pass before checking off a task in `PLAN.md` (on projects where CI is the only test gate, see `implement-plan`'s "When CI is the test gate"). Each task produces exactly one commit.
- `RESEARCH.md` contains curated findings, not raw conversation transcripts.
- `DECISIONS.md` is written only when ≥2 real options were weighed. When it exists, `PLAN.md`'s `## Decisions` section links to it instead of restating.

---

### Phase 5 — Handoff

Report the plan path, task count, and risk tier, then point to the next step:

```
Plan '<slug>' created: <N> tasks, risk <tier>.
Validate it:   validate-plan <slug>    (recommended for medium+ risk)
Write tests:   tdd-plan <slug>         (recommended for medium+ risk)
Implement it:  implement-plan <slug>
```

---

## Directory Layout

```
docs/artifacts/plans/<slug>/
  PLAN.md              # task checkbox dashboard + Epic:/Phase: link fields (single source of task state)
  RESEARCH.md          # medium/large/high only
  DECISIONS.md         # optional — only when ≥2 real options were weighed
  tasks/
    TASK-001-<slug>.md
    TASK-002-<slug>.md
    TASK-00N-final-validation.md
```

When linked to an epic, `PLAN.md` carries `Epic:` and `Phase:` fields pointing at `docs/artifacts/epics/<NN>-*.md`, and that epic's phase block points back at this plan. See `create-epic`.

---

## Behaviour Constraints

- Never edit source files during planning. Read-only access only.
- Never produce a plan with unresolved questions.
- Always reference concrete file paths and function names, not vague descriptions.
- Keep task scope small enough that each task produces one commit.
- Prefer additive, incremental steps over large rewrites.
- If context is insufficient after exploration, ask the user rather than guessing.
