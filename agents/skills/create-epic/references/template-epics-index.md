# Implementation Epics

This document tracks the implementation epics for **<project>**. Each epic is a
self-contained unit of functionality; each phase within an epic is sized to fit a
small-to-medium pull request and maps to exactly one plan under
[`../plans/`](../plans/).

## Status legend

| Status | Meaning |
|---|---|
| Planned | Defined but not started |
| Ready for dev | All dependencies met; can be picked up |
| In progress | At least one phase has been merged |
| Done | All phases complete and validated against the acceptance criteria |
| Blocked | Waiting on a prerequisite epic |

## Epic status

| # | Epic | Phases | Dependencies | Status |
|---|------|--------|--------------|--------|

## How to work with these epics

1. Confirm this epic's dependencies are `Done` in the table above.
2. Open the epic file and start with its first phase.
3. Turn a phase into a plan: `create-plan` with `--epic <NN> --phase <NN>.<M>`
   (links the plan to the phase both ways). Then `validate-plan` →
   `tdd-plan` → `implement-plan` → `review-plan` → `ship-plan`.
4. Each phase lands as its own pull request.
5. The plan's final-validation task ticks the phase + epic-level acceptance
   criteria and updates this table — promote the row to `In progress` after the
   first phase merges, and to `Done` when the last one does.
