# TASK-005: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for herdr-auto-name`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `python3 -m py_compile herdr/plugins/auto-name/*.py` and `bash -n install.sh` pass
- [ ] `python3 -m unittest discover -s herdr/plugins/auto-name/tests -v` passes (or every failing-to-run criterion is explicitly listed as CI-pending — see implement-plan's "When CI is the test gate")
- [ ] Tests match what `tdd-plan` committed, with no stickers left: `python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py herdr-auto-name --final` prints `tdd=none` or `violations=0`
- [ ] The plugin imports only the Python standard library and its own modules
- [ ] Manual smoke test performed: after `herdr server stop` and a fresh `herdr`, one daemon is running and unnamed tabs get names without any action
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

