FAIL after 1 attempt. The metrics line was not written, because permission to write `.plumbline-drafts/` was denied. Nothing was posted. The tests were not run, since this was a review only.

This was a review with no writer, so one judge attempt was the whole run.

The judge found no matching feature-tracker row and no story was given. I reviewed against the root `CLAUDE.md` and `src/CLAUDE.md` only. I re-read the diff and it confirms the SQL, logging and limit findings (F1–F3).

## Verdict: FAIL

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| blocker | `OrderRepository.java:31` | **SQL injection.** `findByCustomerEmail` builds SQL by concatenating `email` into the query. This breaks the "SQL only through `JdbcTemplate` with `?` parameters" rule, and the endpoint is reachable with user input. | Use `jdbc.query("… WHERE c.email = ? ORDER BY o.created_at DESC LIMIT ?", this::map, email, limit)`. |
| major | `OrderService.java:35` | **Personal data in logs.** `log.info("… email={}", email)` logs the e-mail address. The rules say logs carry IDs and statuses only. | Log the admin's user ID and the result count instead. |
| major | `OrderRepository.java:30-33`, `OrderController.java` | **Unbounded list.** The query has no `LIMIT`, the endpoint takes no `limit`, and `orderdesk.list.max-limit` is not applied. | Add a `limit` parameter (default 20, capped at `orderdesk.list.max-limit`) and pass it to the query, as `listForCustomer` does. |
| major | `OrderServiceTest.java:41-46` | **Weak tests.** The only new test is a service test that mocks the repository. It covers neither the SQL, the limit, nor the 403 for non-ADMIN users. No tests were removed. | Add a repository test with a malicious email, a controller test for 403 as CUSTOMER, and a limit test. |
| minor | `OrderService.java:36`, `OrderController.java:37` | **Blank email and case handling.** A blank `email` is not rejected, and `toLowerCase()` may not match how `customer.email` is stored (the judge was 60% confident). | Return 400 `VALIDATION_FAILED` for a blank email. Check the stored case, or compare case-insensitively. |

The judge passed these checks:
- The ADMIN-only `@PreAuthorize` is in place.
- There is no schema change.
- The change touches no files outside the four code and test files.

The `src/CLAUDE.md` API section does not list the new endpoint, which is a small documentation gap for `/pl-doc`.

## Hand-over
- The tracker rows were not updated, because there is no row for this branch and the result was not a PASS.
- **Metrics:** I could not write `.plumbline-drafts/` (permission denied), so the metrics line was skipped. Say yes if you want me to write it. The command would create `.plumbline-drafts/metrics.csv` and `.plumbline-drafts/.gitignore` (containing `*`). The line is: `2026-10-28,pl-code-review,case/d1-email-search,1,FAIL,no,1,`.
- **Posting:** nobody was available to answer, so nothing was posted as a PR review comment. If you want it posted, I would send the table above as a review comment with `gh pr review --comment`, and only after you approve the exact text. I will not approve or merge.