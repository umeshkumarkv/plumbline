#!/usr/bin/env python3
"""Time the dependency map and per-PR impact on a large git monorepo.

  run_scale.py <repo> <cache_dir> <out.json> <base_branch> <pr_branch> [<pr_branch> ...]

1. cold: build the map of <base_branch> with an empty cache (the one-off cost in CI)
2. per PR: check out the branch and run impact in git mode with the warm cache (the per-PR cost)
"""
import json
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import depmap  # noqa: E402
import impact  # noqa: E402


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main():
    repo, cache, out, base = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    prs = sys.argv[5:]
    shutil.rmtree(cache, ignore_errors=True)
    loc = sum(len(f.read_text(errors="replace").splitlines()) for f in (repo / "services").rglob("*.java"))
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", base], check=True)
    t = time.time()
    dm = depmap.build(repo, cache, base)
    cold = time.time() - t
    res = {"services": len(dm["services"]), "java_lines": loc, "topics": len(dm["topics"]),
           "rest_endpoints": sum(len(u["provides"]) for u in dm["services"].values()),
           "cold_build_s": round(cold, 1), "cold_peak_rss_mb": round(rss_mb()), "prs": []}
    t = time.time()
    depmap.build(repo, cache, base)
    res["warm_build_s"] = round(time.time() - t, 1)
    # raw-blob extraction (used when the revision is not the clean checkout, or the repo has .gitattributes)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", prs[0]], check=True)
    raw_cache = cache.parent / (cache.name + "-raw")
    shutil.rmtree(raw_cache, ignore_errors=True)
    t = time.time()
    depmap.build(repo, raw_cache, base)
    res["cold_build_raw_blobs_s"] = round(time.time() - t, 1)
    shutil.rmtree(raw_cache, ignore_errors=True)
    # deterministic gates on the services the first PR changed
    gates = Path(__file__).resolve().parents[2] / "gates" / "run_gates.py"
    t = time.time()
    g = subprocess.run([sys.executable, str(gates), str(repo), "--changed-from", base], capture_output=True, text=True)
    res["gates_changed_only_s"] = round(time.time() - t, 1)
    res["gates_changed_only_note"] = (f"{prs[0]}: {g.stdout.splitlines()[0] if g.stdout else g.stderr[-200:]} "
                                      "(no baseline for the synthetic repo, so its pre-existing findings show as NEW)")
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", base], check=True)
    for pr in prs:
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", pr], check=True)
        t = time.time()
        r = impact.analyse_git(repo, base, "HEAD", cache)
        el = time.time() - t
        b = impact.bundle(r, repo)
        res["prs"].append({"branch": pr, "seconds": round(el, 1), "changed": r["changed_units"],
                           "affected": len(r["affected"]), "affected_units": sorted(r["affected"])[:12],
                           "breaking": len(r["breaking"]), "bundle_kb": round(len(b) / 1024, 1),
                           "units_scanned": r["stats"]["depmap_scanned"], "units_cached": r["stats"]["depmap_cached"]})
        print(json.dumps(res["prs"][-1]))
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", base], check=True)
    res["peak_rss_mb"] = round(rss_mb())
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "prs"}))


if __name__ == "__main__":
    main()
