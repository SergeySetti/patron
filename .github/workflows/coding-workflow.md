---
on: issues
engine: gemini

safe-outputs:
    create-agent-session:
        base: "main"
        max: 1
    create-pull-request:
        title-prefix: "[ai] "
        labels: [ automation ]
    push-to-pull-request-branch:
        target: "*"
        title-prefix: "[bot] "     
---

# Edit code directly based on issues with prefix `gh-aw:` in the issue title or comments

**Load when**: User has created an issue with `gh-aw:` prefix indicating a direct code edit is needed, or has commented
on an issue with `gh-aw:` indicating a direct code edit is needed
**Prompt file**: `ROOT/.github/aw/edit-code-agentic-workflow.md`

## Commit and Push Changes

Commit the changes to the new branch with a descriptive commit message. The branch name should follow the format
`edit-code-<issue-number>` to clearly associate it with the issue being addressed.
