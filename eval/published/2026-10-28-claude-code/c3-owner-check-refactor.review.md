PASS (the metrics line wasn't written; see below)

The judge passed `case/c3-owner-check-refactor` against `main` on the first attempt. It found nothing above minor. The author's "no behaviour change" claim holds on what the judge checked.

No feature-tracker rows exist for this branch and nobody could be asked, so I reviewed against the root `CLAUDE.md` and `src/CLAUDE.md` only. The story/design check (item 10) is N/A. I did not run the build or tests.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| minor (confidence 0.4) | `src/main/java/com/example/orderdesk/security/CurrentUser.java:18` | `requireOwnerOrAdmin(long customerId)` takes a primitive `long`, but the callers pass boxed `Long` values. A null would now throw an NPE where the old `String.valueOf` comparison would not. The judge considers this unreachable, because the request field is `@NotNull` and the stored value is non-null. | Optionally take `Long`, or add a test for null. |

- **Behaviour:** the new condition `!isAdmin() && !id().equals(String.valueOf(customerId))` matches all the inline checks it replaces. The exception type is the same. Only the internal exception message changed, and clients never see it because `GlobalExceptionHandler.forbidden` always returns "Not allowed".
- **Security:** the owner-or-ADMIN check is still enforced in this service at every call site.
- **Tests:** `CurrentUserTest` adds owner, other-customer and admin cases. No existing test was deleted or changed.
- **Scope:** the diff touches only `OrderController`, `CurrentUser` and the new test.

Both writes were blocked for lack of permission, so no `.plumbline-drafts/` files exist and no tracker row was updated. This run's metrics line was therefore not recorded. I did not post anything.

Questions for you:
1. Should I write the metrics line (`2026-10-28,pl-code-review,case/c3-owner-check-refactor,1,PASS,no,1,`) to `.plumbline-drafts/metrics.csv`, with a `.gitignore` containing `*` beside it? That needs write permission on that folder.
2. Do you want me to post the review as a PR comment? I'd need the PR number for `gh pr review <n> --comment --body "<the table above>"`. I will not approve or merge.