#!/usr/bin/env python3
"""Plumbline benchmark stage — deterministic checks between the ORIGINATOR (agent) and the JUDGE (isolated critic).

  run.py <agent> [--artifact FILE] [--repo DIR] [--base REF] [--story FILE] [--facts FILE] [--results FILE]
                 [--service NAME] [--branch NAME] [--pr N] [--out-dir .plumbline/review] [--name PREFIX] [--replay]

agents: pm ba arch dev code-review qa devops sm doc onboard
Writes <out-dir>/<name>-benchmark.json and -benchmark.md (the judge reads the .md). Exit 0 PASS, 1 FAIL, 2 usage.
On FAIL the loop returns to the originator with the failing checks; the judge is NOT called for that attempt.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Report, Repo, UsageError, read  # noqa: E402

PACKS = {"pm": "pm", "ba": "ba", "arch": "arch", "dev": "dev", "code-review": "code_review", "qa": "qa",
         "devops": "devops", "sm": "sm", "doc": "doc", "onboard": "onboard"}
NEEDS_ARTIFACT = {"pm", "ba", "arch", "sm", "onboard"}


class Ctx:
    pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("agent", choices=sorted(PACKS))
    ap.add_argument("--artifact")
    ap.add_argument("--repo")
    ap.add_argument("--base", help="git base ref (dev/code-review default: develop; doc: required; devops: optional)")
    ap.add_argument("--story")
    ap.add_argument("--facts")
    ap.add_argument("--results")
    ap.add_argument("--service")
    ap.add_argument("--branch")
    ap.add_argument("--pr")
    ap.add_argument("--test-cmd")
    ap.add_argument("--min-coverage", type=float, default=80.0)
    ap.add_argument("--cache")
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--out-dir", default=".plumbline/review")
    ap.add_argument("--name")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if a.agent in NEEDS_ARTIFACT and not a.artifact:
        ap.error(f"{a.agent} needs --artifact")
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or a.agent
    for ext in ("json", "md"):           # never leave a previous attempt's report behind
        (out / f"{name}-benchmark.{ext}").unlink(missing_ok=True)
    c = Ctx()
    c.text = read(a.artifact) if a.artifact else ""
    if a.artifact and not c.text.strip():
        print(f"benchmark: artifact {a.artifact} is empty or missing", file=sys.stderr)
        return 2
    c.repo = Repo(a.repo)
    c.base, c.service, c.branch, c.pr, c.cache = a.base, a.service, a.branch, a.pr, a.cache
    c.story_text = read(a.story) if a.story else ""
    try:
        c.facts = json.loads(read(a.facts)) if a.facts else None
    except ValueError:
        print(f"benchmark: --facts {a.facts} is not valid JSON", file=sys.stderr)
        return 2
    c.results, c.replay, c.test_cmd, c.min_coverage = a.results, a.replay, a.test_cmd, a.min_coverage
    c.workdir = out
    if a.repo and not Path(a.repo).is_dir():
        print(f"benchmark: --repo {a.repo} is not a directory", file=sys.stderr)
        return 2
    r = Report(a.agent, a.artifact or a.repo or "")
    try:
        importlib.import_module(f"packs.{PACKS[a.agent]}").run(r, c)
    except UsageError as e:
        print(f"benchmark usage error (exit 2, not a gap): {e}", file=sys.stderr)
        return 2
    except Exception as e:   # a crash is a benchmark defect, never a PASS/FAIL of the artifact
        import traceback
        traceback.print_exc()
        print(f"benchmark crashed (exit 2): {type(e).__name__}: {e} — report this as a benchmark defect", file=sys.stderr)
        return 2
    (out / f"{name}-benchmark.json").write_text(json.dumps(r.to_json(), indent=1))
    (out / f"{name}-benchmark.md").write_text(r.to_md())
    if not a.quiet:
        for ch in r.checks:
            print(f"{ch.result:4} {ch.id:7} {ch.title} — {ch.detail[:110]}")
        j = r.to_json()
        print(f"BENCHMARK {a.agent}: {j['verdict']} ({j['counts']}) -> {out / (name + '-benchmark.md')}")
    return 1 if r.verdict == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
