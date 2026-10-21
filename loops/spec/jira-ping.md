<!-- @copilot -->
---
agent: agent
description: Read-only check that Copilot can reach JIRA through the Atlassian MCP server
---

<!-- @end -->
# JIRA Ping — Plumbline

Verify that this session can reach JIRA through the Atlassian MCP server.
Single pass, read-only. No eval loop.

## Usage
```
/jira-ping
/jira-ping SCRUM-12      ← also fetch one specific ticket
```

<!-- @copilot -->
Issue key to fetch (optional): ${input:issueKey:SCRUM-1}
<!-- @end -->
<!-- @claude -->
Issue key to fetch (optional): `$ARGUMENTS` — if empty, use `SCRUM-1`.
<!-- @end -->

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: calling read-only Atlassian tools and reporting whether each call worked.

This agent **NEVER**:
- Creates, edits, comments on, labels, or transitions any JIRA issue or Confluence page
- Calls any Atlassian tool whose name starts with create, edit, add, update, or transition
- Prints API tokens, OAuth tokens, or any credential value
- Guesses a result: if a call fails, report the failure

---

## Step 0 — Tools Present? (prove it with a real call)

Do NOT decide from memory or from the tool list whether the Atlassian tools exist.
Prove it by calling one.

Tool names may carry a server prefix depending on the IDE, for example
`getAccessibleAtlassianResources`, `atlassian_getAccessibleAtlassianResources`,
`mcp_atlassian_getAccessibleAtlassianResources` or `atlassian/getAccessibleAtlassianResources`.
Treat any tool whose name ENDS WITH `getAccessibleAtlassianResources` as the right one.
Apply the same rule to every tool named below.

1. List the tool names you can see whose name contains `atlassian` or `Jira` (names only).
2. Call the `getAccessibleAtlassianResources` tool.
   - If the call returns data: Step 0 PASSES. Use the result as Step 1.
   - If the call returns an auth or sign-in error: Step 0 PASSES (the tool exists). Go to Step 1's auth handling.
   - Only if no such tool exists at all: STOP and print:

```
JIRA PING — FAILED AT STEP 0
Atlassian MCP tools are not loaded in this session.
Tools visible containing "atlassian" or "Jira": {list, or "none"}
Check:
<!-- @copilot -->
  1. Copilot Chat is in Agent mode (Ask and Edit modes cannot call tools)
  2. The "atlassian" server is in Copilot's mcp.json and is running and signed in
       IntelliJ : Copilot Chat → tools icon → Add MCP Tools → Edit mcp.json
       VS Code  : .vscode/mcp.json → Start
  3. The Atlassian tools are ticked in the chat's tools picker
  4. Your org's Copilot policy "MCP servers in Copilot" is enabled
<!-- @end -->
<!-- @claude -->
  1. An Atlassian MCP server is configured for Claude Code (`claude mcp list` shows it as connected)
  2. You completed the Atlassian sign-in for that server
  3. The server's tools are allowed in this project's permissions
<!-- @end -->
```

## Step 1 — Resolve cloudId

Use the result of the Step 0 call (do not call it twice).

- If exactly one site is returned: record `cloudId` and the site URL.
- If several sites are returned: list them (name + URL only) and ask which to use. Wait for the answer.
- If the call returns an auth error: STOP and tell the user to complete the Atlassian sign-in for the Atlassian MCP server (Copilot: click Auth/Start above the atlassian entry in mcp.json; Claude Code: re-authenticate the server), then re-run.

Every later call MUST pass this `cloudId`.

## Step 2 — Who am I

Call `atlassianUserInfo`. Record the display name only (not email or account ID).

## Step 3 — Project visibility

Call `getVisibleJiraProjects` with the `cloudId`.
Check whether project key `SCRUM` is in the result.

## Step 4 — Fetch one issue

Call `getJiraIssue` with the `cloudId` and the issue key chosen above (default `SCRUM-1`).
Record: key, summary, status, and labels.

## Step 5 — JQL search

Call `searchJiraIssuesUsingJql` with the `cloudId` and:
```
project = SCRUM ORDER BY updated DESC
```
Limit the results to 5. Record how many issues came back and their keys.

---

## Report

Print exactly this:
```
JIRA PING — {PASSED | FAILED AT STEP n}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Site        : {site URL}
cloudId     : {first 8 chars}…
Signed in as: {display name}

  Step 0 Tools present       : {PASS — tool name used: {name} | FAIL}
  Step 1 Resolve cloudId     : {PASS | FAIL — error}
  Step 2 User info           : {PASS | FAIL — error}
  Step 3 SCRUM visible       : {PASS | FAIL — not in project list}
  Step 4 getJiraIssue {key}  : {PASS — "{summary}" [{status}] | FAIL — error}
  Step 5 JQL search          : {PASS — {n} issues: {keys} | FAIL — error}

Verdict: {JIRA reachable — Plumbline eval loops can read JIRA | see failed step}
```

If any step fails, keep running the later steps where possible, so the report shows every problem at once.
Report each error as the tool returned it. Do not invent a cause.
