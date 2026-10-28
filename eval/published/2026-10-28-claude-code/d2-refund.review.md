FAIL after 1 review. The judge found two blockers. I did not run the build or tests, since the review only reads the diff.

I could not write the metrics line to `.plumbline-drafts/metrics.csv` because write permission was denied. The line would have been `2026-10-28,pl-code-review,case/d2-refund,1,FAIL,no,1,`.

No tracker rows exist for this branch, so I reviewed against the root `CLAUDE.md` and `src/CLAUDE.md` only. The tracker was not updated, since the review did not pass. Nothing was posted anywhere.

| Severity | File | Finding | Fix |
|---|---|---|---|
| blocker | `OrderController.java` (new `refund` endpoint) | There is no `@PreAuthorize` and no role check, so any user can refund. `src/CLAUDE.md:9` says refunds are ADMIN only. | Add `@PreAuthorize("hasRole('ADMIN')")` and a test that a CUSTOMER gets 403. |
| blocker | `OrderController.java`, `OrderService.java`, `OrderRepository.java` | Amounts use `double`, but `src/CLAUDE.md:9` says money is `BigDecimal` and never `double`. | Use `BigDecimal` throughout. Compare with `compareTo` against zero and against the remaining refundable amount. |
| major | `OrderService.java` | The check is `amount > total`, which ignores amounts already refunded, and `addRefund` accumulates. Repeated refunds can exceed the order total. Zero, negative, NaN and Infinity are not rejected cleanly. | Check `amount <= total - refunded`, and make the check and update atomic (for example a conditional UPDATE). Add `refundedAmount` to the `Order` record. |
| major | `OrderServiceTest.java` | `refundPaidOrder` only asserts `isNotNull()` and does not verify `addRefund`. There are no tests for an order not in a paid state, a zero or negative amount, an amount over the total, or authorization. This breaks the "tests that fail without the change" rule. | Verify `addRefund` is called with the right amount. Add tests for the rejection cases and the 403. |
| minor | `OrderService.java`, `schema.sql` | The method returns the order as loaded before the refund, so the response doesn't show the refund. `refundedAmount` is also not exposed on the `Order` record or in `src/CLAUDE.md`. | Return `get(id)` after the update and expose `refundedAmount`. |

The judge passed the data, API, performance, scope and logging items. For logging, it did not confirm that `IllegalArgumentException` maps to a 400.

Open questions: none were put to anyone. Nobody could answer which story this implements. If there is one, I can re-run the review with it to also check the acceptance criteria. I can also post these findings as a PR review comment on a yes, once you've seen the exact text.