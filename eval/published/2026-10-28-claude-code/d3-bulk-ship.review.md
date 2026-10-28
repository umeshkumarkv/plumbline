FAIL (code review)

The judge's verdict on `case/d3-bulk-ship` against `main` is FAIL. I confirmed the diff matches the judge's findings. I did not build or run the tests.

No tracker rows matched this branch and nobody was available to ask. I reviewed against the root `CLAUDE.md` and `src/CLAUDE.md` only, with no story or design in scope. The tracker was not updated because the verdict is not PASS.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| blocker | `OrderService.java`, `shipAll` | It never checks that an order is PAID. It calls `updateStatus` and then reports the order as shipped whether or not it moved. | Call `changeStatus(id, SHIPPED, changedBy)` for each id. Reject orders that are not PAID with 409 INVALID_STATE. |
| blocker | `OrderService.java`, `shipAll` | It calls `repository.updateStatus` directly. `src/CLAUDE.md` says only `changeStatus` may do that, and it must never change status outside `changeStatus`. This also risks skipping the `order_status_history` write. | Route every status change through `changeStatus`. |
| major | `OrderController.java`, `shipBatch` | `catch (Exception e)` returns 200 with `{error, shipped: []}` and no logging. Real failures look like success. | Remove the catch and let `GlobalExceptionHandler` return the error. Log the batch outcome with IDs. |
| major | `OrderController.java`, `shipBatch` | It returns `Object` with an ad-hoc error map. `src/CLAUDE.md` says never to change the error body format. | Return `List<Order>` and use `ApiError` through the exception handler. |
| major | `OrderService.java`, `shipAll` | There is no null, empty or duplicate-id validation. A null body causes an NPE that the catch hides as 200. `IllegalArgumentException` for more than 50 ids may not map to 400. The 50 limit is hard-coded. | Validate the list and throw the validation exception that maps to 400 VALIDATION_FAILED. Make the limit a constant. |
| major | `OrderServiceTest.java` | The only new test ships one PAID order. There are no tests for more than 50 ids, a non-PAID order, null or empty input, or that non-admins are rejected. | Add those tests. They should fail against the current code. |

The ADMIN `@PreAuthorize` is present. The batch is capped at 50 orders, so performance is fine. The diff touches only the controller, service and test.

**Hand-over questions**
- Do you want this posted as a PR review comment? I can't post it without a PR number and your yes. The command would be `gh pr review <n> --request-changes -b "<the table above>"`.
- The Write tool refused to create `.plumbline-drafts/metrics.csv` and its `.gitignore` because permission wasn't granted. This run is still unlogged. The line it would write is `2026-10-28,pl-code-review,case/d3-bulk-ship,1,FAIL,no,1,`.