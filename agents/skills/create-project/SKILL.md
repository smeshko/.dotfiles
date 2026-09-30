---
name: create-project
description: Group several related epics under one project umbrella — a local charter plus an optional Linear Project — the tier above create-epic. Use when the user says "start a project", "group these epics under a project", or frames the work as a larger initiative spanning multiple epics. Skip for a single feature-bound epic — go straight to create-epic.
argument-hint: [<title-or-brief>]
---

# Create Project

Bundle several related epics under one **project** — a themed umbrella (e.g. a
redesign spanning many screens) that sits one tier **above** an epic. A project
is a local charter under `docs/artifacts/projects/` plus, optionally, a matching
**Linear Project** that its member epics (parent issues) and their phases
(sub-issues) roll up into automatically.

This is the front of the flow: `create-project` → `create-epic --project <slug>`
→ `create-plan` → `tdd-plan` → `implement-plan` → `ship-plan`.

## When to use

- Several epics share one theme and should be tracked and shipped together
  (a redesign, a migration, a major initiative).

## When to skip

- A single, feature-bound epic. It does not need an umbrella — run `create-epic`
  directly and leave its `Project:` field as `none`. Projects are additive; the
  rest of the flow works unchanged without one.

## Linear mapping

The full local↔Linear model — the mapping table, milestones, project updates,
team resolution, and the "Linear is optional" rule — lives in
`~/.claude/skills/shared/linear-integration.md`; read it before Phase 4. Short
version: this skill creates the Linear **Project**; `create-epic` creates the
member issues and milestones; `archive-plan` posts project updates; closing the
Project stays a manual call.

## Workflow

### Phase 1 — Frame the project

Establish, from the conversation or a brief passed as the argument:

- **Title + theme** — the one line that ties the epics together.
- **Member epics** — which existing or planned epics belong under it. Some may
  not exist yet; they can be linked later as `create-epic --project <slug>` runs.
- **Goal / scope / non-goals** — at the altitude of epics, not phases.

Use `AskUserQuestion` for genuinely open points; do not scaffold until the theme
and the initial epic set are settled.

### Phase 2 — Scaffold the charter

```bash
python3 ~/.claude/skills/create-project/scripts/init_project.py \
  --title "<title>" [--slug <slug>]
```

Creates `docs/artifacts/projects/PROJECTS.md` from the template if absent, writes
`docs/artifacts/projects/<slug>.md`, and appends a row to the index. Prints the
slug. Then open the charter and fill in **Goal**, **Scope**, and **Out of scope**.

### Phase 3 — Link member epics

For each epic that already exists, link it both ways (sets the epic's `Project:`
field and adds it to the charter's member list):

```bash
python3 ~/.claude/skills/create-project/scripts/link_epic.py <slug> --epic <NN>
```

Epics created later are linked automatically by `create-epic --project <slug>`
(which calls this same script). Re-running is idempotent — it will not duplicate.

### Phase 4 — Create the Linear Project (only if Linear is wired)

Skip this phase entirely if the Linear GitHub integration is not connected for
this repo — the local charter is still fully usable, and the id can be backfilled
later. Otherwise:

1. Resolve the team once with `mcp__linear-server__list_teams`; if the workspace
   has more than one team, ask the user which one — never guess.
2. Create the Linear Project with `mcp__linear-server__save_project` — `name` =
   the project title, `description` = the charter Goal, `teamId` = the team id.
3. Record the returned id (and URL) back onto the charter and index:

```bash
python3 ~/.claude/skills/create-project/scripts/set_project_linear.py <slug> \
  --id <linear-project-id> [--url <linear-url>]
```

4. For any **already-linked** epics whose parent issue exists in Linear, set that
   issue's `project` to the new Linear Project id via `mcp__linear-server__save_issue`.
   (Epics linked later inherit it at `create-epic` time.)

### Phase 5 — Handoff

Report the charter path and (if created) the Linear Project URL, then point to the
next step:

```
Created project '<slug>' with <N> member epic(s).
Add an epic:  create-epic --project <slug>
```

## Behaviour Constraints

- **Projects group epics; epics group phases.** Keep the charter at the altitude
  of "which epics and why", never phase- or task-level detail.
- **The scripts own the linkage.** Do not hand-edit the epic's `Project:` field,
  the charter's member-epics list, or the `linear_project:` line — `link_epic.py`
  and `set_project_linear.py` own them (both idempotent).
- **Never edit source files.** The only writes are under `docs/artifacts/`.
- **Closing the Linear Project is manual.** When the last member epic ships, the
  user decides when to mark the Linear Project Completed — `archive-plan` will not
  close it automatically (it only closes epic and phase issues).
- **Linear is optional.** Every script works with no Linear connection; the
  `linear_project:` field simply stays `none` until backfilled.
