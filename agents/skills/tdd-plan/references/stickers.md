# Stickers

A **sticker** is one whole line containing `TDD-PENDING <task-id>` that keeps a test skipped. Deleting that line — and nothing else — makes the test run. `strip_stickers.py` performs exactly that deletion and `check_tests.py` allows no other test edit, so pick a form where the bare deletion leaves valid code.

| Stack | Sticker line | Placement |
|---|---|---|
| pytest | `@pytest.mark.skip(reason="TDD-PENDING TASK-003")` | own decorator line above the test |
| XCTest | `throw XCTSkip("TDD-PENDING TASK-003")` | first line of a `throws` test method |
| Swift Testing | `.disabled("TDD-PENDING TASK-003")` | own line inside a multi-line `@Test(` … `)` |
| Vitest | `ctx.skip(); // TDD-PENDING TASK-003` | first line of a `(ctx) => {` body |
| xUnit | `Skip = "TDD-PENDING TASK-003"` | own line inside a multi-line `[Fact(` … `)]` |
| NUnit | `Assert.Ignore("TDD-PENDING TASK-003");` | first line of the test body |

The multi-line forms:

```swift
@Test(
    .disabled("TDD-PENDING TASK-003")
)
func excludesPastDepartures() { … }
```

```csharp
[Fact(
    Skip = "TDD-PENDING TASK-003"
)]
public void ExcludesPastDepartures() { … }
```

Another stack: pick a form by the same rule — Step 6's red proof confirms it, since stripping must leave a test that runs and fails. A framework with no whole-line form (Jest: `test.skip` can't be undone by deleting a line) → ask the user before writing tests.
