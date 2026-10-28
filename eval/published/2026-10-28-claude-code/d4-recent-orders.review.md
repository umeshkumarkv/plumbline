`FAIL`. The judge found two blockers, so this branch should not merge as it stands.

I couldn't write the metrics line because the write permission was denied. The line is below. Nothing was posted, and the tracker has no row for this branch, so I reviewed against the CLAUDE.md files only.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| blocker | `OrderService.java` (`listRecent`) | `listRecent` passes the request's `limit` straight to `findByCustomerAfter`. `listForCustomer` caps it with `Math.min(limit, maxLimit)`. This breaks the `src/CLAUDE.md` rule that lists are always bounded by max-limit, and it leaves the query unbounded. | Cap at `orderdesk.list.max-limit`, as `listForCustomer` does, and add a test for a limit above the maximum. |
| blocker | `OrderServiceTest.java:48` | The diff removes `listCapsLimitAtMaximum`, which checked `findByCustomer(3L, 100)`, and puts an unrelated `listRecentPassesTheDate` in its place. This breaks the rule against deleting or weakening tests. | Restore the old test unchanged and add the new tests beside it. Cover the cap on `listRecent`, a limit below 1, and controller access for the owner, another customer and ADMIN. |
| major | `OrderService.java` (`listRecent`) | `listRecent` throws `IllegalArgumentException("limit must be at least 1")`. The judge didn't confirm a handler that turns this into a 400 `ApiError`, so it may come back as a 500 (confidence 0.6). | Return a 400 `VALIDATION_FAILED` in the `ApiError` format, using an exception the handler already maps. Add a test. |
| major | `OrderServiceTest.java` | The PR says it "tidies the old list test", but the diff deletes it. There is also no controller or authorization test for the new endpoint. | Keep the original test and add the owner, other-customer and ADMIN tests. |
| minor | `OrderController.java` `recent()` | `after` is a required `Instant` with no validation. A malformed value probably gets Spring's default type-mismatch error rather than an `ApiError` (confidence 0.4). | Check that a bad `after` gives an `ApiError` 400, and add a test. |

The judge did not flag the owner-or-ADMIN check or the SQL (parameterised), and the diff has no schema changes.

I did not run the build or tests, only the judge's review of the diff. This was one attempt.

**For you:**
- **Metrics line.** I didn't write `.plumbline-drafts/metrics.csv`. I would have appended `2026-10-28,pl-code-review,case/d4-recent-orders,1,FAIL,no,1,` after creating the file with the header `date,command,target,attempts,verdict,tests_run,minutes,human_decision`. I would also have added a `.gitignore` containing `*` in `.plumbline-drafts/`.
- **PR comment.** If you want these findings posted as a PR review comment, say so and I'll show the exact text first. I won't approve or merge.