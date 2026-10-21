# Run 2 adjudication — summary

## Planted-defect recall
| kind | n | gate recall | critic recall | either recall |
|---|---|---|---|---|
| mechanical | 10 | 4/10 (40%) | 10/10 (100%) | 10/10 (100%) |
| judgement | 10 | 1/10 (10%) | 10/10 (100%) | 10/10 (100%) |
| domain | 10 | 0/10 (0%) | 10/10 (100%) | 10/10 (100%) |
| **all defects** | 30 | 5/30 (16%) | 30/30 (100%) | 30/30 (100%) |

## Controls (n=10)
| metric | value |
|---|---|
| controls with any critic false_alarm | 0 |
| controls with any gate false_alarm | 0 |
| controls with only legit extra findings | 5 (Q02, Q03, Q06, Q08, Q10) |
| controls with no findings at all | 5 (Q01, Q04, Q05, Q07, Q09) |

## Extra (non-planted) findings, all 40 PRs
| source | legit | false_alarm | precision |
|---|---|---|---|
| critic | 29 | 2 | 93% |
| gate | 4 | 2 | 67% |
| total | 33 | 4 | |

Notes: critic findings restating part of the planted defect (P04 SMALLINT column, P06 static executor, P10 TIMESTAMP columns) are folded into the planted catch, not counted as extras. Most legit extras are missing-test findings (§10/§15). Critic false alarms: P15 TRADER-visibility (pre-existing filter policy), P19 Map/@RequestParam (no rule; pre-existing pattern). Gate false alarms: C2-class-suffix on ServiceTokenInterceptor (P03) and ExecutionEventKeyStrategy (P29). Q08/Q03 "controls" contain real build-breaking test regressions the critic correctly flagged.
