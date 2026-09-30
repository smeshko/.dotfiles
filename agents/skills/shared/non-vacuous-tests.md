# Non-vacuous tests — shared reference

The bar for every test the plan-lifecycle skills write: `tdd-plan` always, `implement-plan` on plans that skip `tdd-plan`. Read it before writing or reviewing a test.

A **non-vacuous** test would actually fail if the behaviour it claims to check were broken. A **vacuous** test passes whether the code works or not — worse than no test, because it reports coverage that isn't there.

## The litmus

Break the code on purpose — revert the fix, flip a condition, return a constant — and the test goes **red**. A test that stays green is vacuous. `tdd-plan`'s stubs apply this break up front: every test is red against them before any real code exists.

## Vacuous smells

Hunt for each in every test before it is committed:

- Asserting on a mock the test configured itself — stub `getUser()` to return X, then assert X came back.
- Tautologies — `assert result == result`, or the expected value computed with the code under test.
- Weak assertions — not-null, "doesn't throw", `len(x) >= 0` — where the exact value was knowable.
- Loops or parametrized cases over an empty collection, so zero assertions run.
- Swallowed failures — a broad `try/catch`, an async test that never awaits.
- A bug-fix test that also passed before the fix.

## Tight

Quality over quantity — a small suite where every test earns its place:

- One test per behaviour in the task's Acceptance criteria. A second test for the same behaviour earns its place only by covering a branch that breaks independently — a boundary, an error path.
- Assert the exact expected value.
- Test through the public surface the plan names; private helpers, framework behaviour and trivial accessors get covered through it.
- Name each test after the behaviour it proves (`excludesPastDepartures`), so a red run reads as a bug report.
- Run real code wherever the test can; mock only what it cannot run for real — network, clock, disk.
