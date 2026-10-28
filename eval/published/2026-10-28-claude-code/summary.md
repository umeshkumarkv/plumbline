| Case | Kind | Verdict | Result | Time | Cost | Model |
|---|---|---|---|---|---|---|
| c1-max-lines | clean | PASS | 0 false alarms, 1 minor | 40s | $0.175 | claude-sonnet-5-5 |
| c2-status-history | clean | PASS | 0 false alarms, 2 minor | 46s | $0.205 | claude-sonnet-5-5 |
| c3-owner-check-refactor | clean | PASS | 0 false alarms, 0 minor | 52s | $0.169 | claude-sonnet-5-5 |
| c4-status-counts | clean | PASS | 0 false alarms, 2 minor | 47s | $0.18 | claude-sonnet-5-5 |
| c5-max-quantity | clean | PASS | 0 false alarms, 1 minor | 44s | $0.179 | claude-sonnet-5-5 |
| d1-email-search | defects | FAIL | 3/3 found | 57s | $0.182 | claude-sonnet-5-5 |
| d2-refund | defects | FAIL | 3/3 found | 48s | $0.17 | claude-sonnet-5-5 |
| d3-bulk-ship | defects | FAIL | 3/3 found | 70s | $0.17 | claude-sonnet-5-5 |
| d4-recent-orders | defects | FAIL | 2/2 found | 41s | $0.167 | claude-sonnet-5-5 |
| d5-discount | defects | FAIL | 2/2 found | 51s | $0.185 | claude-sonnet-5-5 |

**Recall:** 13/13 planted defects found. **False alarms:** 0 blocker/major findings on clean changes. **Decoys flagged:** 0. **Total cost:** $1.78.
