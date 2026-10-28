PASS

The independent judge passed `case/c5-max-quantity` against `main` on attempt 1. The review was read-only, and I didn't build or run the tests.

**Scope:** the feature tracker doesn't exist and has no row for this branch, so I reviewed against the root `CLAUDE.md` and `src/CLAUDE.md` only. The story/design checklist item is N/A. I didn't update the tracker because there is no row to update.

**What the diff changes:** `OrderLine.java` (quantity is now `@Min(1) @Max(1000)`) and a new `OrderLineTest.java`.

The judge confirmed these points:
- **Bounds:** both are inclusive, and a primitive `int` can't be null.
- **400 path:** `OrderController` uses `@Valid @RequestBody`, and `CreateOrderRequest` cascades to each line. `GlobalExceptionHandler` turns that into 400 `VALIDATION_FAILED` with the unchanged error body.
- **Tests:** they cover 1000 accepted, 1001 rejected and 0 still rejected. The 1001 test would fail without `@Max`. No existing test was changed.
- **Rules and data:** no money, SQL, status or authorization code is touched, and there is no schema change.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| minor | `src/test/java/com/example/orderdesk/order/OrderLineTest.java` | Tests call the `Validator` directly. Nothing checks that `POST /api/orders` with quantity 1001 returns 400 `VALIDATION_FAILED`. The judge rated this low risk (confidence 0.5). | Optionally add a MockMvc test for that response. |

**Left undone:**
- **Metrics:** I couldn't write `.plumbline-drafts/metrics.csv` or `.plumbline-drafts/.gitignore` because the write permission was denied. This is the line it would have held:
  `2026-10-28,pl-code-review,case/c5-max-quantity,1,PASS,no,1,`
  The header is `date,command,target,attempts,verdict,tests_run,minutes,human_decision`. `.gitignore` would contain `*`.
- **PR comment:** this is a non-interactive run, so I didn't post anything. The text I'd offer to post, if you say yes: "Code review: PASS. `@Min(1) @Max(1000)` on `OrderLine.quantity` is correct and tested, and the 400 `VALIDATION_FAILED` path goes through the existing handler. Minor: consider a MockMvc test for the 400 response on quantity 1001."