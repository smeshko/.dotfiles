# Linear integration — shared reference

How the plan-lifecycle skills (`create-project`, `create-epic`, `create-plan`, `tdd-plan`, `implement-plan`, `create-pr`, `archive-plan`) mirror local artifacts into Linear. This is a shared reference loaded on demand by those skills, not a skill itself.

## Linear is optional — always

Every Linear step in every skill is conditional on Linear being **wired**: the Linear MCP server is available in the session *and* this repo's work is actually tracked in Linear. When not wired, skip every Linear step silently — the local artifacts are fully self-sufficient, all `Linear:` / `Milestone:` / `linear_project:` fields stay `none`, and ids can be backfilled later by re-running the relevant step. Never treat a missing Linear connection as an error, and never push the user to set Linear up.

Detection: if no `mcp__linear-server__*` tools are available, Linear is not wired. If the tools exist but no existing artifact carries a Linear id and the repo gives no signal (no convention in `AGENTS.md`/`CLAUDE.md`, no issue ids in git history), ask the user once whether to mirror this work into Linear and follow that answer for the rest of the session.

## Team resolution

Resolve the team once per session with `mcp__linear-server__list_teams`. If the workspace has more than one team and nothing in the repo names one, ask the user — never guess. The product itself is the Linear **team**; Linear Projects group epics *inside* it.

## Mapping

| Local artifact | Linear object | Created by |
|---|---|---|
| Project charter (`docs/artifacts/projects/<slug>.md`) | **Project** | `create-project` |
| Epic (`docs/artifacts/epics/<NN>-<slug>.md`) | parent **Issue** (its `project` set to the Linear Project) | `create-epic` |
| Epic (the same one) | **Project Milestone** of the same name, no target date | `create-epic` |
| Phase (`<NN>.<M>`) | **sub-issue** of the epic issue, assigned to the milestone | `create-epic` |
| Plan tasks | **Tasks** bullet list in the sub-issue description | `create-plan` |

## The automation spine

The phase **sub-issue id** drives status downstream with no manual writes:

- The skill that cuts the branch (`tdd-plan`, or `implement-plan` when tests-first is skipped — see `shared/plan-branch.md`) embeds the lowercased id in the branch name (`<prefix>/<id>-<slug>`) → Linear moves the sub-issue to **In Progress** on push.
- `create-pr` puts the id in the PR title and `Closes <ID>` in the body, then confirms the PR is attached to the issue → Linear moves it to **Done** on merge.
- The milestone's progress bar fills on its own as the phase sub-issues close.

Linear does **not** cascade status upward. The deliberate manual writes, in full:

1. `create-plan` moves the phase sub-issue to **Todo** when the plan is authored, and `validate-plan` re-asserts it (move to Todo if not already there or further along) — a planned phase must not sit in Backlog. Skip if the team has no Todo state.
2. The skill that cuts the branch (`tdd-plan` or `implement-plan`) sets the sub-issue to In Progress at start (and, for the epic's first phase, the epic parent issue too) — the board should reflect started work before the first push.
3. `review-plan` moves the sub-issue to **In Review** once its preconditions pass and the adversarial review begins (skip if the team has no such state).
4. `validate-plan` / `review-plan` file every `defer` finding as a **Backlog issue** when writing their summary file (dedupe by title; always apply the `code-review` label from the Source group, plus other existing labels that fit) — the defer bucket must not evaporate.
5. `archive-plan`, when an epic's final phase merges: close the **epic parent issue**, and if the epic belongs to a project, post one **project status update** — epic granularity, never per phase.
6. Marking the Linear **Project** itself Completed is always the user's call — remind them when the last epic ships; never do it automatically.

## Labels

Discover existing labels with `mcp__linear-server__list_issue_labels` and apply the ones that genuinely fit. **Never create labels.** If a useful label is missing, suggest it to the user at the end and move on.
