UNVERIFIED: the tests were not run, and I couldn't write the metrics line. The write to `.plumbline-drafts/metrics.csv` was denied. The judge returned PASS on its first attempt.

**Verdict: PASS** for `case/c1-max-lines` against `main`. No tracker row exists for this branch, and no story or design was given. The review was therefore against `CLAUDE.md` and `src/CLAUDE.md` only. I did not update the feature tracker, and nothing was posted.

The diff adds `@Size(max = 50)` to `lines` in `CreateOrderRequest`, plus a new `CreateOrderRequestTest`. The judge found:
- 50 lines are accepted and 51 are rejected, and the existing `@NotEmpty` still covers null and empty.
- `OrderController.create` already uses `@Valid`, and `GlobalExceptionHandler` maps `MethodArgumentNotValidException` to 400 `VALIDATION_FAILED`, so the error body is unchanged.
- No tests were removed or weakened, and the diff touches only those two files.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| minor | `src/test/java/com/example/orderdesk/order/CreateOrderRequestTest.java:1` | The tests validate the record directly. None goes through the controller to check the HTTP 400 `VALIDATION_FAILED` body. The judge's confidence in this finding was 0.4. | Optionally add a MockMvc test that posts 51 lines and asserts a 400 with code `VALIDATION_FAILED`. |

**Hand-over questions**
1. Should I record this run in the metrics file once write permission is granted? It would append `2026-10-28,pl-code-review,case/c1-max-lines,1,PASS,no,1,` to `.plumbline-drafts/metrics.csv`, creating the file with its header first.
2. Do you want this posted as a PR review comment? The task said not to post, so I haven't. The text would be: "Code review: PASS. `@Size(max = 50)` on `lines` is correct and tested at the 50/51 boundary. Minor: consider a MockMvc test asserting the 400 `VALIDATION_FAILED` response."