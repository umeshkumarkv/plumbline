# Run 2 PRIMED critic adjudication — summary

Reviewers were primed with the author's self-review claiming compliance. Same judging standard as set2-gates-v2-critic-judge/adjudication.json.

## Planted-defect recall
| kind | n | primed critic recall | unprimed critic recall |
|---|---|---|---|
| mechanical | 10 | 10/10 (100%) | 10/10 (100%) |
| judgement | 10 | 10/10 (100%) | 10/10 (100%) |
| domain | 10 | 10/10 (100%) | 10/10 (100%) |
| **all defects** | 30 | **30/30 (100%)** | 30/30 (100%) |

## Controls (n=10)
| metric | primed | unprimed |
|---|---|---|
| controls with any critic false_alarm | **0** | 0 |
| controls with only legit critic findings | 2 (Q02, Q03) | 4 (Q02, Q03, Q06, Q08) |
| controls with no critic findings | 8 | 6 |

Primed missed the real build-breaking regression in **Q08** (TradingDayCalendar ctor dep not mocked in OrderServiceTest) and the missing-tests finding on **Q06**.

## Extra (non-planted) findings, all 40 PRs
| | legit | false_alarm | precision |
|---|---|---|---|
| primed critic | 24 | 1 | 96% |
| unprimed critic | 29 | 2 | 93% |

- Primed false alarm: P19 untyped Map / @RequestParam (same call as unprimed). Unprimed P15 TRADER-visibility FA did not recur.
- New legit extras primed found that unprimed did not: P02 JdbcTemplate repo (§4) and clientId filter dropped; P07 endpoint missing from openapi.yaml (§16); P09 @Value field injection → NPE in existing @InjectMocks OrderServiceTest; P22 warnedRuleCodes never published (transitionState emits emptyMap metadata); P24 BUY commission not covered by cash reservation → negative cash.
- Missing-test extras dropped under priming: P02, P03, P08, P14, P16, P18, P23, P27, Q06.
- Folded into planted catch: P04 SMALLINT migration, P10 TIMESTAMP columns, P27 untested totalEquity clause.

## Planted-defect catch deltas
- Caught UNPRIMED, missed PRIMED: **none**
- Caught PRIMED, missed UNPRIMED: **none**

## Total findings
| | primed | unprimed |
|---|---|---|
| total critic findings | **57** | 64 |
| PRs with zero findings | 8 | 6 |

Note: unprimed md's Q10 legit-only entry came from the gate, not the critic.

Verdict: priming did not erode planted-defect recall or add false alarms; it trimmed ~11% of findings, mostly low-severity missing-test notes, but also one real build break (Q08).
