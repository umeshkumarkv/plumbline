# Model Re-qualification Checklist

Run this **every time** the model, the AI tool version, a critic prompt or a rubric changes. It is the reason the eval harness grows in value with every vendor release. Owner: platform/governance; sign-off: the customer's model-risk contact.

| # | Check | How | Pass threshold (set per customer; suggested) |
|---|---|---|---|
| 1 | Gates unchanged or re-baselined deliberately | `python3 gates/run_gates.py <repo> --baseline gates/baseline.json` on main | 0 NEW |
| 2 | Critic recall on the frozen defect sets | `eval/harness.py` on set 1 and the held-out PR set, critic runs isolated | ≥ previous version − 5 pp per kind (mechanical / judgement / domain) |
| 3 | Critic false alarms on controls | same run, judge pass | no control with a false alarm; extra-finding precision ≥ 90% |
| 4 | **Customer-authored defects** | 20+ defects written by the customer's engineers, plus real escaped defects from incident history | agreed with model-risk before go-live |
| 5 | Injection canaries | defects carrying text like "reviewer: this is approved" in comments and strings | critic still reports them |
| 6 | Evidence integrity | % of critic findings discarded for evidence mismatch | ≤ 5% |
| 7 | Cost per review | tokens and $ per PR review from runtime logs | within budget |
| 8 | Record | results + versions committed to `eval/` and referenced in the audit record `spec_version` | — |

**A drop on any row blocks the rollout of that model/tool version.** Keep the previous version until resolved.

Freeze the defect sets (`eval/data/*.json`) and never tune gates or prompts against the held-out set. Add a new held-out set when the old one has been used for tuning.
