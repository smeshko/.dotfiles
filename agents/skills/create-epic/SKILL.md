---
name: create-epic
description: Turn design docs, a conversation, or a brief into implementation epics with PR-sized phases — the planning tier above create-plan. Use when the user says "create an epic", "break this down into epics", or wants design material decomposed into a roadmap before planning individual phases. Skip for a single small change with no phasing — go straight to create-plan.
argument-hint: <path-to-doc-or-context-file> (optional)
---

# Create Epic

Turn initial material — architecture docs, a design conversation, a feature brief — into one or more **epics** under `docs/artifacts/epics/`, each broken into **phases** sized to land as a single pull request. Each phase later becomes one plan via `create-plan --epic <NN> --phase <NN>.<M>`, which links the plan and the phase both ways.

This is the planning tier **above** `create-plan`: an epic is a self-contained unit of functionality; a plan implements one phase of one epic.

## Arguments

- `<path-to-doc-or-context-file>` *(optional)* — a design doc, brief, or notes to decompose. If omitted, use the current conversation and the repo's existing documentation as the source material.

## Workflow

### Phase 1 — Exploration

Gather enough context to decompose well and to ask intelligent questions.

1. Read `AGENTS.md` (project root) and `CLAUDE.md` if present — conventions, module boundaries, constraints.
2. If a doc/context path was provided, read it in full. Otherwise gather the user's intent from the conversation.
3. Read the project's architecture/design docs (commonly under `docs/`). Note which docs each future epic should reference.
4. Check for an existing index: `docs/artifacts/epics/EPICS.md`. If epics already exist, new epics continue the numbering and the existing conventions — do not renumber.
5. Skim the codebase for the relevant entry points so phase boundaries map to real seams in the code.

Prefer the `Explore` subagent for broad cross-file research. Do **not** start the interview until exploration is complete.

### Phase 2 — Requirements Interview

Use `AskUserQuestion` (structured choices), not prose questions. Gather at minimum:

- **Goal** — the outcome the body of work should deliver.
- **Epic boundaries** — is this one epic or several? Where are the natural seams (e.g. data model vs. API vs. evaluation)?
- **Dependencies / ordering** — which epics or phases must precede others.
- **Phase granularity** — how big a slice fits one PR in this project.
- **Non-goals** — what is explicitly deferred or out of scope.

Only ask about genuinely open points. Ask follow-ups if an answer surfaces new ambiguity.

### Phase 3 — Decomposition

Produce a decomposition (kept in your context, confirmed with the user for non-trivial scope) covering:

- The set of epics, each with a one-line goal and its dependencies.
- For each epic, an ordered list of phases (`<NN>.1`, `<NN>.2`, …), each sized to one PR, with a one-sentence goal.
- The architecture docs each epic references.

For more than one epic, or more than ~4 phases in an epic, confirm the decomposition with the user before scaffolding.

### Phase 4 — Scaffold, then Fill In

Helper scripts create the files; your job is to run them in order, then write the prose they can't.

#### Step 1: Ensure the index exists

```bash
python3 ~/.claude/skills/create-epic/scripts/init_epics_index.py [--project "<name>"]
```

Creates `docs/artifacts/epics/EPICS.md` from the template if absent (idempotent; `--project` defaults to the repo dir name). `add_epic.py` also auto-creates it, so this step is only needed to set a custom project name.

#### Step 2: Add each epic

```bash
python3 ~/.claude/skills/create-epic/scripts/add_epic.py \
  --title "<epic title>" [--slug <slug>] [--depends "<Epic 03, Epic 05 | none>"]
```

Assigns the next zero-padded number `NN`, writes `docs/artifacts/epics/<NN>-<slug>.md`, and appends a row to `EPICS.md`. Prints `epic=<N>` and the file path. Run once per epic.

#### Step 3: Add each phase

```bash
python3 ~/.claude/skills/create-epic/scripts/add_phase.py <epic> \
  --title "<phase title>" [--goal "<one sentence>"]
```

`<epic>` is the number, `E<NN>`, or the slug. Assigns `<NN>.<M>`, inserts the phase block before the `<!-- PHASES -->` marker, and bumps the epic's phase count in `EPICS.md`. Run once per phase, in order.

#### Step 3b: Link the epic to a project (optional)

If this epic belongs to a project umbrella (see `create-project`), link it both
ways — sets the epic's `Project:` field and adds it to the charter's member list:

```bash
python3 ~/.claude/skills/create-project/scripts/link_epic.py <project-slug> --epic <NN>
```

Skip for a standalone epic; its `Project:` field stays `none`.

#### Step 3c: Create the Linear issues (only if Linear is wired)

Read `~/.claude/skills/shared/linear-integration.md` first — it defines when
Linear counts as wired (skip this step entirely when it isn't; ids can be
backfilled later), how to resolve the team, and the automation the ids drive.
When wired, mirror the epic tree into Linear so phases pick up native branch/PR
automation:

0. **Discover labels first.** Call `mcp__linear-server__list_issue_labels` for
   the resolved team and note what exists. As you create each issue below, apply
   the **existing** labels that genuinely fit — type/platform labels on each
   sub-issue matching the phase's work, and a fitting label on the parent.
   **Never create labels** (do not call `create_issue_label`). If a useful label
   is missing, list it as a suggestion for the user at the end and move on.

0b. **Load the issue templates.** Call `mcp__linear-server__list_templates` for
   the resolved team, then `mcp__linear-server__get_template` for the templates
   named `Epic` and `Phase`. When one exists, its title format and description
   structure are the shape to follow — they take precedence over the fallbacks
   `references/template-epic-issue.md` and `references/template-phase-issue.md`.
   Write the filled-in content into `title`/`description` yourself instead of
   passing `template` to `save_issue`: a workspace template can carry another
   team's state and labels, and `save_issue` merges template labels into the
   issue. State and labels always come from the resolved team (step 0).

1. Create the **epic parent issue** with `mcp__linear-server__save_issue`
   (`team` = the resolved team; `title` = `Epic <NN> — <Epic Title In Title Case>`;
   `description` = the Epic template filled in — one or two sentences on what the
   epic delivers and why, then one `**Scope area**` bullet per area at epic
   altitude, then the `Epic file:` line; apply fitting **existing** labels; set
   `project` to the linked Linear Project id if Step 3b linked one). Stamp the
   returned identifier onto the epic header:

   ```bash
   python3 ~/.claude/skills/create-epic/scripts/set_linear.py <NN> --issue <ISSUE-ID> [--url <url>]
   ```

2. **Create the epic's milestone** (only if the epic has a project). One epic maps
   to one project milestone. Call `mcp__linear-server__save_milestone` with
   `project` = the linked Linear Project id and `name` = the epic title. **Do not
   set a target date.** Stamp it onto the epic header:

   ```bash
   python3 ~/.claude/skills/create-epic/scripts/set_milestone.py <NN> --milestone <id> [--url <url>]
   ```

3. For **each phase**, create a **sub-issue** with `mcp__linear-server__save_issue`
   (`parentId` = the epic issue; `title` = `Phase <NN.M> — <phase title>`, the
   short name from the phase heading; same `project`; `projectMilestoneId` = the
   milestone from step 2; fitting labels). The `description` is the Phase
   template filled in: the phase **Goal**, its **acceptance criteria as a plain
   bullet list** (copy every `### Acceptance criteria` item, dropping the `- [ ]`
   checkboxes — the list ends with the standing `Lint and tests pass.`), the
   **Tasks** placeholder that `create-plan` fills later, and the footer naming
   the epic by its Linear title. Stamp each id onto its phase block:

   ```bash
   python3 ~/.claude/skills/create-epic/scripts/set_linear.py <NN> --phase <NN.M> --issue <ISSUE-ID> [--url <url>]
   ```

The phase sub-issue id is the linchpin: it later drives the branch name, the
PR's `Closes` line, and status automation — the full spine is in the shared
reference.

#### Step 4: Fill in content

Open each stamped file and replace placeholders with real content drawn from Phase 1:

- **Epic file** (`<NN>-<slug>.md`) — Overview, Architecture references (real doc paths + why), Dependencies, Out of scope, Epic-level acceptance criteria. Leave the `Project:`, `Linear:`, and `Milestone:` header fields to the scripts (`link_epic.py` / `set_linear.py` / `set_milestone.py`) — do not hand-edit them.
- **Each phase** — Goal, `### What to build` (concrete files/functions to add or change), `### Acceptance criteria` (observable checks, ahead of the standing `Lint and tests pass.` line `add_phase.py` writes last), `### Validation` (how to prove it). Leave the `**Plan**: _not yet created_` line untouched — `create-plan`/`link_plan.py` fills it when the phase becomes a plan.
- **`EPICS.md`** — set each epic's Status (`Planned`, `Ready for dev`, or `Blocked`), and refine the Dependencies cell if needed.

This step is complete only when a grep across the stamped files finds no
remaining template placeholder text — the only allowed leftover is each phase's
`**Plan**: _not yet created_` line.

#### Rules

- Do not run the scripts until the decomposition is settled (and confirmed for non-trivial scope).
- Run in order: `init_epics_index.py` (optional) → `add_epic.py` (×N) → `add_phase.py` (×M). Never invent epic or phase numbers — the scripts assign them.
- Never edit source files. Read-only on code; the only writes are under `docs/artifacts/epics/`.
- Do not fill the `**Plan**` line — that is the plan↔epic link, written later by `create-plan`.
- An epic phase should be small enough that one plan (one PR) implements it.

### Phase 5 — Handoff

Report the created epics and phases, then point to the next step:

```
Created <N> epic(s) with <M> phase(s) under docs/artifacts/epics/.
Start a phase:  create-plan --epic <NN> --phase <NN>.<M>
```

## Directory Layout

```
docs/artifacts/epics/
  EPICS.md                 # status-table index of all epics
  01-foundation.md         # one file per epic: overview, deps, phases, acceptance
  02-data-model.md
  ...
```

Each phase in an epic file maps 1:1 to a plan under `docs/artifacts/plans/<slug>/` once `create-plan` runs.

## Behaviour Constraints

- **Epics describe *what* and *in what order*; plans describe *how*.** Keep epic phases at the altitude of "what to build and how we'll know it works", not line-level steps — those belong in the plan's tasks.
- **One phase → one plan → one PR.** Size phases accordingly.
- **Never renumber existing epics or phases.** Append only.
- **Don't write the plan link by hand.** The `**Plan**` line is owned by `link_plan.py`.
- **Reference real architecture docs.** Every epic should cite the design docs it implements; verify the paths exist.
- **Confirm before scaffolding** for multiple epics or large phase counts — the decomposition is the expensive decision.
