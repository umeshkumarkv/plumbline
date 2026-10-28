The judge returned FAIL, and I couldn't write the metrics line because the permission request was denied. I'm giving the final report now.

**FAIL after 1 attempt.** This is a review, so there is no retry loop. The tracker was not updated because it only changes on PASS. Nothing was posted. Both `.plumbline-drafts/metrics.csv` and its `.gitignore` are missing.

Scope: `git diff main...case/d5-discount`, checked against the root `CLAUDE.md` and `src/CLAUDE.md`. No tracker rows or stories were found, so checklist item 10 is N/A.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| blocker | `OrderService.java`, `applyDiscount` | `BigDecimal.valueOf(1 - percent / 100)` uses integer division. For 1–90 the factor is always 1, so no discount is ever applied. | Compute the factor in `BigDecimal`: `BigDecimal.valueOf(100 - percent).divide(BigDecimal.valueOf(100))`, or multiply by `(100 - percent)` and divide by 100 with rounding. |
| major | `OrderService.java`, `applyDiscount` | `discounted.equals(BigDecimal.ZERO)` never matches, because `0.00` has scale 2. The "reject a zero total" requirement is therefore dead code. | `discounted.compareTo(BigDecimal.ZERO) <= 0` |
| major | `OrderService.java`, `applyDiscount` | Breaks the Money rule in `src/CLAUDE.md` §9: compare with `compareTo`, never `equals`. | Same fix as the row above. |
| major | `OrderServiceTest.java` | Only two tests were added: out-of-range percent, and non-NEW orders. Nothing covers a successful discount, the new total, the zero-total rejection, or the `updateTotal` call. A happy-path test would have caught the blocker. | Add tests for the happy path (new total and `updateTotal` call), zero-total rejection, and percent bounds 1 and 90. Add a controller test for ADMIN-only access. |
| minor | `src/CLAUDE.md` §4 | The endpoint list does not include `/discount`. | Add it. `/pl-doc` can do this after merge. |

**Passed or N/A:**
- **Security:** the endpoint has `@PreAuthorize` ADMIN, the SQL is parameterised, the log line carries only the order ID and percent, and errors use the generic handler.
- **Errors and logging:** the error mapping is correct (400 for invalid input, 409 for wrong state).
- **API, performance, scope:** the endpoint is additive, there is one read and one update, and only the four expected files changed.
- **Data:** N/A, there are no schema changes.

Tests were not run; the review is read-only.

**Hand-over for the user:**
- Ask the author to fix F1–F4 and re-run `/pl-code-review`.
- Metrics line I could not write: `2026-10-28,pl-code-review,case/d5-discount,1,FAIL,no,1,`. I can create the file if you approve the write.
- Posting this as a PR review comment needs your yes. I have not drafted `gh pr review` text yet, and I will never approve or merge.