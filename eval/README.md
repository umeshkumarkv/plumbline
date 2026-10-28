# Plumbline eval set — check the reviewer yourself

A small, original sample service (**Order Desk**, `sample-app/`) and ten pull requests against it. Five carry planted
defects with an answer key; five are clean, correct changes. Run `/pl-code-review` on them — in Claude Code or
Copilot — and score the reviews. Nothing here comes from a real company's code, so you can share the results.

| Case | Change | Planted |
|---|---|---|
| `d1-email-search` | Back office: find orders by customer e-mail | 3 (SQL injection, e-mail in logs, unbounded list) |
| `d2-refund` | Refund part of an order | 3 (no ADMIN check, money as `double`, test that asserts nothing) |
| `d3-bulk-ship` | Ship several orders at once | 3 (bypasses the status rules, swallows errors with 200, wrong error body) |
| `d4-recent-orders` | List orders created after a date | 2 + 1 decoy (uncapped limit, deleted test; the decoy is correct code) |
| `d5-discount` | Percentage discount on a new order | 2 (integer division, `BigDecimal.equals`) |
| `c1`…`c5` | Max lines per order, status history, owner-check refactor, status counts, max quantity | none — clean |

What a good reviewer does: finds the planted defects (**recall**), raises **no blocker or major finding on the clean
changes** (false alarms), and leaves the decoy alone. Extra true findings on defect cases are fine.

## Run one case by hand (Claude Code or Copilot)
```bash
bash eval/setup-case.sh d2-refund ~/eval/d2-refund     # builds a git repo: main + branch case/d2-refund
cd ~/eval/d2-refund                                      # open it in Claude Code, or in VS Code for Copilot
#   /pl-code-review case/d2-refund
# save the review's final reply to review.md, then:
python3 <plumbline>/eval/score.py d2-refund review.md
```
Read the review too: the score matches findings by file name and key words, and is meant to save time, not to be
the last word. Correct it by hand when it is wrong, and note that in your results.

## Run all ten headless (Claude Code)
```bash
bash eval/run.sh                  # or: bash eval/run.sh d1-email-search c3-owner-check-refactor
MODEL=<model> bash eval/run.sh    # same, on another model
```
Each run uses the recommended permission settings (the case repository gets `examples/claude-settings.json` as its
`.claude/settings.json`). Results, transcripts and a `summary.md` table go to `eval/results/<timestamp>/`.

## Check the eval material itself
`bash eval/check-cases.sh` (needs Java 21 and Maven) applies every case, compiles it, and runs the clean cases' tests.
`bash tests/validate.sh` checks every case applies (no build).

## Add your own cases
Add `cases/<id>/case.json` (`title`, `pr`, `kind`: `defects` or `clean`, `edits`: find/replace on sample-app files,
`new_files`) and, for defects, `answer.json` (each defect: `id`, `severity`, `files`, `keywords`, `desc`; optional
`decoys`). The best cases come from someone who did not write Plumbline: plant the defects your own reviews catch.

**Note on `run.sh`:** each case runs in a fresh temporary folder that Claude Code has never trusted, so headless runs
ignore the `allow` list there (the `deny` list and normal prompts still apply; unanswered prompts are refused). That
is stricter than your project. A case whose run fails (for example a usage limit) is reported as not scored, never as
0 found.

## Compare two Plumbline versions (A/B)
```bash
REPEAT=3 bash eval/ab.sh v2.6.0 HEAD      # code-review eval on both versions, same cases and scorer, 3 runs each
```
`ab-summary.md` shows recall, false alarms, decoys and cost per run. One run per version is anecdotal.

To measure a command on **your own** repository (e.g. whether 2.7+ really reads less code than 2.6):
```bash
bash eval/ab-command.sh v2.6.0 HEAD ~/work/your-repo "/pl-ba <a requirement in plain English>"
```
The repository is copied for each run and never changed; nothing is posted. The table counts `Read`/`Grep`/`Glob`
calls, tokens, cost and time per version. Read both hand-overs too — fewer tokens only counts if the output is as good.
