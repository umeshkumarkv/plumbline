PASS

The judge passed `case/c2-status-history` on the first attempt, with two minor findings. I didn't build or run the tests. I couldn't write the metrics line or the tracker. The tracker has no row for this branch, so there was nothing to update. The permission to write `.plumbline-drafts/` wasn't granted. There was nobody to ask, so I stopped there.

**Scope:** there is no feature tracker and no story was given, so the review is against the root `CLAUDE.md` and `src/CLAUDE.md` only. Checklist item 10 (stories and designs) is N/A.

I re-read the diff and `schema.sql` myself and they match the judge's report. The `order_status_history.id` column exists, which the `ORDER BY changed_at, id` relies on.

| Severity | File:line | Finding | Fix |
|---|---|---|---|
| minor | `src/test/java/com/example/orderdesk/order/OrderServiceTest.java` | Only service-level tests were added. Nothing covers the ADMIN-only restriction on `GET /{id}/history`, or the SQL ordering and the null `from_status`. The repo has no controller or JDBC test setup, and the root rule says tests must fail without the change. | Add a 403 test for non-ADMIN and an oldest-first ordering test once such a setup exists. |
| minor | `src/CLAUDE.md` §4 and §5 | The API list doesn't include the new endpoint. The §5 table also omits the `id` column of `order_status_history`. | Add the endpoint and the column, preferably with `/pl-doc` after merge. |

**What the judge confirmed passes:**
- **Authorization:** `@PreAuthorize("hasRole('ADMIN')")` is on the new endpoint.
- **SQL:** the query is parameterised.
- **Limit:** results are capped at `maxLimit`.
- **404:** the existence check goes through `get(id)`, so an unknown order returns 404.
- **Rules and scope:** nothing calls `updateStatus`, nothing is logged, no tests were deleted or weakened, and the diff touches no `.claude/`, `.github/` or `CLAUDE.md` files.

**Questions I couldn't ask:**
1. Post this as a PR review comment? Nothing was posted, per the run instructions. If you say yes, I'd send the table above with `gh pr review --comment` (never approve or merge).
2. Allow me to write `.plumbline-drafts/metrics.csv` with this line, and a `.gitignore` containing `*` in the same folder?
   `2026-10-28,pl-code-review,case/c2-status-history,1,PASS,no,1,`