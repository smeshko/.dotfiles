# Shipping lanes

Read when the user asks the orchestrator to run `ship-plan`. Being asked is the go-ahead to merge the lanes they named, nothing more.

`ship-plan` runs as a fork: it sees only its arguments, so every argument carries the facts below. It hands back when it needs a decision. Answer from what you can verify, then invoke it again with the answer.

## Every ship-plan call carries

- The lane's worktree path. Every git, gh and push step runs there: while a worktree has the branch checked out, the main checkout cannot check it out.
- `--root <main checkout>` when `docs/` is gitignored, since plan files live only there.
- The lock command for its push: `scripts/with-verify-lock.sh <lock-dir> <lane> git push`.
- `verify` in the foreground with a 600000 ms timeout. A fork that waits on a background run never resumes.
- Approval, up front, to remove the clean worktree and delete the local branch after the merge.
- The tracker route: list tracker writes, don't attempt them. You apply them after the merge.

## Order

Ship one lane at a time. A protected base needs each PR head to contain the latest base, so every later lane goes through `gh pr update-branch`, a fresh CI run, and maybe a conflict. Print the board after each ship step.

## Hand-backs you can settle

- **Test-lock violations after a base merge.** `check_tests.py --final` miscounts in two ways:
  - Run from the main checkout, it compares against the base's tree.
  - After `update-branch`, it counts other plans' test commits that arrived through the merge.

  The real check: `git log --no-merges --first-parent <tests-commit>..HEAD` names only this lane's commits, and `git diff origin/<base> HEAD -- test` shows only this plan's tests. When both hold, answer "accept as false positive".
- **Integration amendment.** A test merged from another phase now fails because this phase changed behaviour on purpose, for example a fixture that writes a document the new checks reject. Accept it when it keeps every assertion and only feeds valid input. Read the diff before you answer.
- **`git push` exit 141 after a green hook.** That is a SIGPIPE between git and the hook, not a failed test. When `verify` passed on that exact sha, push with `--no-verify` yourself, and say so in the report. CI gates the merge either way.
- **CI red but local green.** Compare the runtime CI pins with the local one first. Hand the lane to a fix stage (opus, high) that reproduces the failure on CI's version.

## After the merge

Set the issue to Done unless the PR's `Closes` line already did. Confirm the worktree and local branch are gone, and give the epic's progress.
