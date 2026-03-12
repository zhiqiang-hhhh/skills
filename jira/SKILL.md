---
name: jira
description: Access Jira issues, search tickets, create and update issues using Jira REST API.
---

# Jira Skill

Use this skill when interacting with Jira tickets.

Capabilities:

- Search Jira issues
- Get issue details
- Create new issues
- Create Epic issues
- Add comments
- Transition issue status
- Link issues
- Set Epic Link
- Query Jira fields (find customfield IDs)

## Common Tasks

### Search Issues

Run:
  python jira_client.py search "query"


Example:
  python jira_client.py search "project = DORIS AND status = Open"


### Get Issue
  python jira_client.py get ISSUE-123

### Create Issue
  python jira_client.py create "title" "description" [PROJECT_KEY] [ISSUE_TYPE]

### Create Epic
  python jira_client.py create_epic "半结构化值班 2026-0309-0315" [PROJECT_KEY] [EPIC_NAME] [REPORTER]

Note:
  - `create_epic` defaults assignee to the creator (same as reporter) when `REPORTER` is omitted.


### Add Comment
  python jira_client.py comment ISSUE-123 "comment text"

### Transition Issue
  python jira_client.py transition ISSUE-123 "Done"

### Link Issues
  python jira_client.py link INWARD-ISSUE OUTWARD-ISSUE [LINK_TYPE] [COMMENT]

Example:
  python jira_client.py link CIR-10739 CIR-19652 "Issue split" "自动关联本周值班 Epic"

### Set Epic Link
  python jira_client.py set_epic_link ISSUE-123 EPIC-456

### One-Command Oncall Epic Flow
  python jira_client.py create_oncall_epic ISSUE-123 [WEEK_LABEL] [PARENT_ISSUE] [PROJECT_KEY] [REPORTER]

Example:
  python jira_client.py create_oncall_epic CIR-19618 2026-0309-0315 CIR-10739 CIR hezhiqiang

Note:
  - This command does not add workflow comments automatically; it only performs linking actions.

### List Fields
  python jira_client.py fields [pattern]

Example:
  python jira_client.py fields epic

## 半结构化值班 Historical Pattern

- 母任务：`CIR-10739`（任务类型为 Task，不是 Epic）。
- 周 Epic：每周创建一个 `Epic`，命名通常为 `半结构化值班 YYYY-MMDD-MMDD`。
- 母任务关联：使用 issue link type `Issue split`，方向为 `CIR-10739 -> 当周Epic`（split to）。
- 具体问题单（如故障单）：通过 `Epic Link` 关联到当周 Epic（字段 `customfield_10101`）。

Recommended flow:
  1) `python jira_client.py create_oncall_epic <ISSUE_KEY> [WEEK_LABEL]`
  2) If manual steps are needed:
     `python jira_client.py create_epic "半结构化值班 2026-0309-0315" CIR`
     `python jira_client.py link CIR-10739 <NEW_EPIC_KEY> "Issue split" "自动关联本周值班 Epic"`
     `python jira_client.py set_epic_link <ISSUE_KEY> <NEW_EPIC_KEY>`


## Notes

Authentication uses environment variables:

  JIRA_URL
  JIRA_USER
  JIRA_TOKEN
  JIRA_AUTH_MODE   # optional: auto (default), bearer, or basic
  JIRA_API_VERSION # optional: 2 (default) or 3

Default config targets Jira Server/Data Center with REST API v2.
`JIRA_AUTH_MODE=auto` tries `bearer` first, then falls back to `basic` on 401/403.
