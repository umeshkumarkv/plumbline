#!/usr/bin/env python3
"""Fail a PR that touches the controls that judge it (approval-matrix.md, separation of duties).

  protected_paths.py <base_ref> [head_ref]     run in the OMS repo; exits 1 on violation

Applies to EVERY PR, whatever its branch name (branch names are chosen by whoever opens the PR, including agents).
A PR may change protected paths only when PLUMBLINE_POLICY_PR=1, which the workflow sets when the PR carries the
`plumbline-policy-change` label; every protected path must also require CODEOWNERS review in branch protection
(template: packs/governance/CODEOWNERS.template), so a named human owner signs every policy change.
Renames are reported as delete + add (--no-renames), so moving a protected file is caught.
"""
import fnmatch
import os
import re
import subprocess
import sys

PROTECTED = [
    # CI, ownership, agent prompts and critic definitions
    ".github/workflows/*", ".github/CODEOWNERS", "CODEOWNERS", ".github/prompts/*", ".github/agents/*",
    ".claude/*", ".claude/**/*", ".agentic-sdlc/*", ".guardrails/*", ".plumbline/*",
    ".github/copilot-instructions.md", ".github/instructions/*", "**/AGENTS.md",
    # anything that can hide code from a scanner or relax a linter
    "**/.semgrepignore", "**/.semgrepignore*", ".semgrep.yml", ".semgrep/*",
    # attributes can re-encode or filter files on checkout, so scanners see something other than what is stored
    ".gitattributes", "**/.gitattributes",
    "**/checkstyle*.xml", "**/pmd*.xml", "**/spotbugs*.xml", "**/*suppressions*.xml", "**/lombok.config",
    # rulebooks and scanner pins
    "CLAUDE*.md", "**/CLAUDE*.md", "security/tool-versions.env",
    # Maven settings that can skip tests or coverage without touching pom.xml
    ".mvn/*", "**/.mvn/*", "**/maven.config", "**/jvm.config", "**/settings.xml",
    # build wrappers: a rewritten wrapper or distributionUrl runs a different build tool
    "**/mvnw", "**/mvnw.cmd", "**/gradlew", "**/gradlew.bat", "**/gradle/wrapper/*",
]
# In pom.xml only the test/coverage controls are protected: the jacoco, surefire and failsafe plugin blocks and
# test-related properties. Any change to them is a violation; other pom edits (dependencies) are allowed.
GUARDED_PLUGINS = ("jacoco-maven-plugin", "maven-surefire-plugin", "maven-failsafe-plugin",
                   "build-helper-maven-plugin")   # add-source: compiled code outside src/ that no gate scans
GUARDED_PROPS = re.compile(r"<(skipTests|maven\.test\.skip|maven\.test\.failure\.ignore|testFailureIgnore|"
                           r"jacoco[\w.-]*|surefire[\w.-]*|failsafe[\w.-]*|skipITs|sourceDirectory|testSourceDirectory)>.*?</\1>", re.S)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def changed(base, head):
    out = subprocess.run(["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
                         capture_output=True, text=True, check=True)
    return [l for l in out.stdout.splitlines() if l]


def match(path, pattern):
    """fnmatch, where a leading **/ also matches at the repo root."""
    return fnmatch.fnmatch(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))


def guarded_pom_parts(text):
    # normalise whitespace between and inside tags first, so `<artifactId>\n  maven-surefire-plugin\n</artifactId>`
    # (which Maven trims) still matches, and allow attributes on <plugin ...>
    text = re.sub(r"\s*(<[^>]+>)\s*", r"\1", re.sub(r"<!--.*?-->", "", text, flags=re.S))
    plugins = [b for b in re.findall(r"<plugin\b[^>]*>.*?</plugin>", text, re.S)
               if any(f"<artifactId>{p}</artifactId>" in b for p in GUARDED_PLUGINS)]
    norm = lambda x: re.sub(r"\s+", " ", x).strip()
    return sorted(map(norm, plugins)), sorted(map(norm, (m.group(0) for m in GUARDED_PROPS.finditer(text))))


def main():
    base = sys.argv[1]
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    if os.environ.get("PLUMBLINE_POLICY_PR") == "1":
        print("protected-paths: policy-change PR (label plumbline-policy-change) — CODEOWNERS review required instead")
        return 0
    merge_base = git("merge-base", base, head).strip() or base
    bad = []
    for f in changed(base, head):
        if any(match(f, p) for p in PROTECTED):
            bad.append(f"{f}: protected control file (needs a plumbline-policy-change PR)")
        elif f.endswith("pom.xml"):
            old = git("show", f"{merge_base}:{f}")
            new = git("show", f"{head}:{f}")
            if guarded_pom_parts(old) != guarded_pom_parts(new):
                bad.append(f"{f}: changes jacoco/surefire/failsafe configuration or test properties")
    for b in bad:
        print("PROTECTED", b)
    print(f"protected-paths: {len(bad)} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
