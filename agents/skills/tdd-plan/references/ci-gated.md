# CI-gated projects

Where the tests cannot build or run locally (a platform-bound toolchain — `AGENTS.md`/`CLAUDE.md` says so), CI does the proving, so Steps 5–8 reorder around the draft PR:

1. Write the stubs and tests as Step 4 says, but **without stickers**. Commit the stubs, then the tests as `test(<scope>): add tests for <slug>`.
2. Push and open the draft PR now (Step 8's commands). Its first CI run is the red proof: every new test fails on its assertion (`gh run view <run-id> --log-failed`). Build errors and unrelated failures get fixed first, in their own commits. Save the failures to `docs/artifacts/plans/<slug>/tdd/red.txt`.
3. Add the stickers (`references/stickers.md`) and commit as `test(<scope>): mark <slug> tests pending` — this is the tests commit Step 7 records. `check_tests.py` treats the two test commits as one baseline. Push; CI goes green with the stickered tests skipped — the sticker proof.
4. Finish Step 7 (record, status, `## Tests` sections, record commit) and push the record commit.

Step 9's report names the red and green run URLs as the evidence.
