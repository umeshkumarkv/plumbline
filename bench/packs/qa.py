"""QA benchmark — verifies the QA agent's EVIDENCE, so a PASS cannot be claimed without proof.

Input: --results .plumbline/review/{ticket}-qa-results.json written by the QA originator (Step E):
  {"ticket": "SCRUM-n", "results": [
     {"ac": "<AC text or 'EDGE: ...'>", "kind": "REST|UI|EDGE", "command": "curl ...", "expected_status": 200,
      "http_status": 200, "response": "<raw body>", "verdict": "PASS|FAIL", "screenshot": "path (UI)"} ]}
Judge keeps: are the ACs really proven (right data, right assertions), risk coverage beyond the ACs."""
import json
import re
import shlex
import subprocess
from pathlib import Path

from common import UsageError, bullets, read, section

MONEY = re.compile(r"(price|amount|notional|total|fee|cost|balance|cash|value|exposure|pnl)$", re.I)
EDGES = {"unknown id -> 404": r"\b404\b", "missing auth -> 401": r"\b401\b",
         "envelope structure": r"envelope|meta\.timestamp|requestId", "money as string": r"money|monetary|string"}


def norm(s):
    return re.sub(r"[^a-z0-9/{} ]", "", s.lower()).strip()


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, o


def as_int(v):
    try:
        return int(str(v).strip()[:3])
    except (TypeError, ValueError):
        return None


def run(r, ctx):
    if not ctx.results:
        raise UsageError("pass --results .plumbline/review/{ticket}-qa-results.json")
    try:
        data = json.loads(read(ctx.results))
        res = data["results"]
        assert isinstance(res, list) and all(isinstance(x, dict) for x in res)
    except (ValueError, KeyError, TypeError, AssertionError):
        raise UsageError(f"{ctx.results} is not results JSON: {{\"results\": [{{...}}]}}")
    r.add("QA-0", "QA results file parses", True, f"{len(res)} results")

    if ctx.story_text:   # 1:1 — each AC needs its own result whose `ac` is that AC's text
        acs = bullets(section(ctx.story_text, "acceptance criteria"))
        pool = [norm(x.get("ac", "")) for x in res]
        unproven = []
        for a in acs:
            if norm(a) in pool:
                pool.remove(norm(a))
            else:
                unproven.append(a)
        r.add("QA-1", "Every story AC has its own recorded result (ac = the AC text)", bool(acs) and not unproven,
              f"{len(acs)} ACs, {len(unproven)} without a result", unproven)
    else:
        r.skip("QA-1", "AC traceability", "no --story given")

    incomplete, lying, bad_env, num_money, shots = [], [], [], [], []
    for x in res:
        tag = x.get("ac", "?")[:70]
        if x.get("kind", "REST") in ("REST", "EDGE"):
            got, exp = as_int(x.get("http_status")), as_int(x.get("expected_status"))
            if not (x.get("command") and got is not None and str(x.get("response", "")).strip()):
                incomplete.append(tag)
                continue
            should = "PASS" if exp is not None and exp == got else "FAIL"
            if exp is not None and x.get("verdict") != should:
                lying.append(f"{tag}: expected {exp}, got {got}, recorded {x.get('verdict')}")
            try:
                body = json.loads(x["response"]) if isinstance(x["response"], str) else x["response"]
            except ValueError:
                body = None
            if body is not None and str(got).startswith("2"):
                if not (isinstance(body, dict) and "data" in body and isinstance(body.get("meta"), dict)
                        and "timestamp" in body["meta"] and "requestId" in body["meta"]):
                    bad_env.append(tag)
                for pth, v in walk(body):
                    if MONEY.search(pth.split(".")[-1].split("[")[0]) and isinstance(v, (int, float)) and not isinstance(v, bool):
                        num_money.append(f"{tag}: {pth} = {v}")
        if x.get("kind") == "UI" and not (x.get("screenshot") and (Path(ctx.repo.path or ".") / x["screenshot"]).exists()):
            shots.append(tag)
    r.add("QA-2", "Every REST result has command, status and full response", not incomplete, f"{len(incomplete)} incomplete", incomplete)
    r.add("QA-3", "Recorded verdicts agree with expected vs actual status", not lying, f"{len(lying)} inconsistent", lying)
    r.add("QA-4", "2xx responses use the standard envelope (data, meta.timestamp, meta.requestId)", not bad_env,
          f"{len(bad_env)} without envelope", bad_env)
    r.add("QA-5", "Monetary values are JSON strings, never numbers", not num_money, f"{len(num_money)} numeric", num_money)
    r.add("QA-6", "UI results have a screenshot on disk", not shots, f"{len(shots)} missing", shots)

    # mandatory edge cases: recorded AND showing the status they are about
    edges = [x for x in res if x.get("kind") == "EDGE" or x.get("ac", "").upper().startswith("EDGE")]
    def has(pattern, ok):
        return any(re.search(pattern, x.get("ac", ""), re.I) and ok(x) for x in edges)
    def money_string(x):
        try:
            b = json.loads(x.get("response", ""))
        except (ValueError, TypeError):
            return False
        return any(MONEY.search(p.split(".")[-1].split("[")[0]) and isinstance(v, str) for p, v in walk(b))
    need = {"unknown id -> 404": has(r"\b404\b|unknown", lambda x: as_int(x.get("http_status")) == 404),
            "missing auth -> 401": has(r"\b401\b|auth", lambda x: as_int(x.get("http_status")) == 401),
            "envelope structure": has(r"envelope|requestId", lambda x: str(as_int(x.get("http_status"))).startswith("2")),
            "money as string": has(r"money|monetary", money_string)}
    miss = [k for k, ok in need.items() if not ok]
    r.add("QA-7", "Mandatory edge cases recorded with the status/value they assert", not miss, f"missing or unproven: {miss}" if miss else "4/4")
    fails = [x.get("ac", "")[:70] for x in res if x.get("verdict") != "PASS"]
    r.add("QA-8", "All recorded results PASS", not fails, f"{len(fails)} failing", fails)

    if ctx.replay:   # re-run recorded GET curls through bash (env vars such as $TOKEN expand); never mutating calls
        mism, replayed = [], 0
        for x in res:
            cmd = x.get("command", "")
            if not cmd.startswith("curl") or re.search(r"-X\s*(POST|PUT|PATCH|DELETE)|--data|\s-d\s|-F\s", cmd):
                continue
            if re.search(r"[;|&`<>]|\$\(|\n", cmd):   # one plain curl only: no chaining/substitution that could fake output
                mism.append(f"{x.get('ac', '')[:60]}: command is not a single plain curl — not replayable")
                continue
            try:
                p = subprocess.run(["bash", "-c", cmd + " -s -w '\\n%{http_code}'"], capture_output=True, text=True, timeout=20)
                body, _, code = p.stdout.rpartition("\n")
            except (OSError, subprocess.TimeoutExpired):
                body, code = "", "ERR"
            replayed += 1
            if code.strip() != str(as_int(x.get("http_status"))):
                mism.append(f"{x.get('ac', '')[:60]}: recorded {x.get('http_status')}, replay {code.strip()}")
                continue
            try:   # same shape: the top-level keys of `data` must match the recorded body
                rec, now = json.loads(x.get("response", "")), json.loads(body)
                if isinstance(rec, dict) and isinstance(now, dict) and isinstance(rec.get("data"), dict) \
                        and sorted(rec["data"]) != sorted((now.get("data") or {}) if isinstance(now.get("data"), dict) else {}):
                    mism.append(f"{x.get('ac', '')[:60]}: recorded data keys {sorted(rec['data'])}, replay {sorted(now.get('data') or {})}")
            except (ValueError, TypeError):
                pass
        r.add("QA-9", "Replayed GET evidence reproduces status and response shape", replayed > 0 and not mism,
              f"{replayed} replayed, {len(mism)} mismatches" + ("" if replayed else " — nothing replayable: record at least one GET"), mism)
    else:
        r.skip("QA-9", "Replay of recorded GET calls", "run with --replay while the stack is up")
