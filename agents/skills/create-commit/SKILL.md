---
name: create-commit
description: Create a git commit from the staged changes following the project's Conventional Commits format, with the ticket reference derived from the branch name. Use whenever the user asks to commit ("commit this", "save my work to git"), or another skill needs a commit created.
---

# Create Commit

Create a well-structured git commit from the currently staged changes, following the project's Conventional Commits conventions.

## Workflow

### Step 1: Gather context

Run the helper script to collect branch info, ticket number, and the staged diff:

```bash
bash ~/.claude/skills/create-commit/scripts/get_commit_context.sh
```

If the helper script reports there is nothing to commit, stop and tell the user there are no changes.

If it reports **no staged changes** but lists unstaged/untracked files (exit 3), do NOT
`git add -A` or `git add .`. Stage explicitly (`git add <paths>`) only the files you
changed in this session, then re-run the script. If any listed changes are not yours,
leave them unstaged and ask the user whether to include them.

### Step 2: Craft the commit message

Compose a commit message using this format:

#### Subject line

```
type(scope): description #TICKET
```

| Part          | Rule                                                                 |
|---------------|----------------------------------------------------------------------|
| **type**      | Pick by what the diff changes: `feat` (new user-facing behaviour), `fix` (bug fix), `refactor` (restructuring, no behaviour change), `test` (tests only), `docs` (documentation only), `style` (formatting/imports, no logic), `chore` (tooling, config, dependency bumps), `perf` (performance), `ci` (CI pipeline files), `build` (build system / external deps). A feature plus its tests is `feat`; separate pure test additions as `test`. |
| **scope**     | Optional. Short name of the module or feature area, e.g. `offer-config`, `search`, `profile`. Omit if the change spans many areas. |
| **description** | Lowercase, imperative mood ("add filter", not "added filter" or "adds filter"). No trailing period. |
| **#TICKET**   | The ticket number extracted from the branch name. If the script could not find one, ask the user or omit. **If the script reports a `(linear: …)` line, the branch is Linear-tracked — omit `#ticket` entirely; the branch and the PR's `Closes` line already link the issue, and a per-commit ref would spray duplicate links onto it.** |

The full subject line (including type, scope, and ticket) should stay under 72 characters.

#### Body (optional — use when the change is non-trivial)

- Separate from the subject with a blank line.
- Explain **what** was changed and **why**, not how (the diff shows how).
- Use imperative mood.
- Wrap lines at 72 characters.

#### Examples

**Simple (no body):**
```
fix(search): correct airport code mapping for Bratislava #29517
```

**With body:**
```
feat(offer-config): add departure time range filters for flights #30202

Add outbound and inbound departure time range slider filters to the
flight filters sheet. Updates the filter model, cubit,
state extensions, and UI to support the new filter type. Wraps filter
content in a scrollable container to accommodate the additional filters.
```

**Test commit:**
```
test(offer-config): add unit tests for OfferConfigurationStateExtensions #30202
```

**Refactor:**
```
refactor(offer-config): use existing DateTime extensions instead of local functions #30202
```

### Step 3: Create the commit

Run the commit script with the composed message:

```bash
bash ~/.claude/skills/create-commit/scripts/create_commit.sh "<subject>" "<body>"
```

Omit the second argument if there is no body.

### Step 4: Confirm

Show the user the commit hash and subject that was created.