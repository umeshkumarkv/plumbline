---
name: plumbline-doc-writer
description: Drafts the exact API-spec and CLAUDE.md text an open PR needs, for dev to apply in the same PR.
tools: ['read/readFile', 'search', 'edit']
user-invocable: false
---

First read `.claude/agents/plumbline-doc-writer.md` (skip its frontmatter) and follow it exactly: it is your full instructions.
Then do the task in the request.
