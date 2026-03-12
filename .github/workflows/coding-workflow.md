---
on:
    issues:
        types: [ opened, edited ]
engine: gemini

safe-outputs:
    create-agent-session:
        base: "main"
        max: 1
    create-pull-request:
        title-prefix: "[ai] "
        labels: [ automation ]
        protected-files: fallback-to-issue
    push-to-pull-request-branch:
        target: "*"
        title-prefix: "[agentic-session] "
    add-comment:
        max: 3
        target: "*" 
---

# Edit session on issue opened or edited

**Load when**: User has created an issue indicating a direct code edit is needed, or has commented
on an issue indicating a direct code edit is needed
**Prompt file**: `ROOT/.github/aw/edit-code-agentic-workflow.md`

## Commit and Push Changes

Commit the changes to the new branch with a descriptive commit message. The branch name should follow the format
`edit-code-<issue-number>` to clearly associate it with the issue being addressed.
