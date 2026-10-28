# Releasing Plumbline

A release is a fast-forward of `main` plus an annotated tag `vX.Y.Z`. Version numbers: **major** when a command is
renamed or removed or an install step changes; **minor** for new behaviour in commands or agents; **patch** for
documentation and wording fixes.

## Checklist
1. **Self-test passes:** `bash tests/validate.sh` (also runs in CI on every PR).
2. **Version:** `.github/plumbline/VERSION` and the top entry of `CHANGELOG.md` say the same version; the changelog
   entry says what changed and how it was tested.
3. **Regression runs** — for any change to a command or agent, re-run on a real repository, with the recommended
   permission settings (never bypassed), at least:
   - the changed command(s), one positive run each;
   - `/pl-code-review` on a branch with known planted defects (record found / missed / false alarms);
   - one negative case for each changed checklist (the judge must FAIL deliberately flawed work).
   Record model, Claude Code version, cost and time per run, and keep the transcripts.
4. **Test report:** add a dated section to `TEST-REPORT.md` with the results above. Every number must come from a kept
   transcript or log; anything else is marked as the author's statement.
5. **Review:** a person who did not make the change reads the diff of `.claude/` and `.github/`. In repositories that
   use Plumbline, such PRs carry the `plumbline-policy-change` label.
6. **Publish:** fast-forward `main`, tag `vX.Y.Z` (annotated), push both. Never move a published tag.

## After a release
Teams upgrade by copying `.claude` and `.github` again and re-merging `examples/claude-settings.json` (README →
Upgrade). Note anything that needs a manual step at the top of the changelog entry.
