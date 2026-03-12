import os
import sys
import requests
import json
from datetime import datetime, timedelta

JIRA_URL = os.environ["JIRA_URL"].rstrip("/")
USER = os.environ.get("JIRA_USER", "")
TOKEN = os.environ["JIRA_TOKEN"]
API_VERSION = os.environ.get("JIRA_API_VERSION", "2")
AUTH_MODE = os.environ.get("JIRA_AUTH_MODE", "auto").lower()

BASE_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
LAST_AUTH_MODE = None

def _usage():
    print(
        "Usage:\n"
        "  python jira_client.py search \"<jql>\"\n"
        "  python jira_client.py get <ISSUE-KEY>\n"
        "  python jira_client.py comment <ISSUE-KEY> \"<text>\"\n"
        "  python jira_client.py create \"<summary>\" \"<description>\" [project_key] [issue_type]\n"
        "  python jira_client.py create_epic \"<summary>\" [project_key] [epic_name] [reporter]\n"
        "  python jira_client.py set_epic_link <ISSUE-KEY> <EPIC-KEY>\n"
        "  python jira_client.py link <INWARD-ISSUE-KEY> <OUTWARD-ISSUE-KEY> [link_type] [comment]\n"
        "  python jira_client.py create_oncall_epic <ISSUE-KEY> [week_label] [parent_issue] [project_key] [reporter]\n"
        "  python jira_client.py transition <ISSUE-KEY> \"<transition-name-or-id>\"\n"
        "  python jira_client.py fields [name_pattern]\n"
    )

def _auth_config(mode):
    headers = dict(BASE_HEADERS)
    if mode == "basic":
        return (USER, TOKEN), headers
    if mode == "bearer":
        headers["Authorization"] = f"Bearer {TOKEN}"
        return None, headers
    raise ValueError("auth mode must be 'bearer' or 'basic'")

def _request(method, url, **kwargs):
    global LAST_AUTH_MODE
    if AUTH_MODE == "auto":
        modes = ["bearer", "basic"]
    elif AUTH_MODE in ("bearer", "basic"):
        modes = [AUTH_MODE]
    else:
        raise ValueError("JIRA_AUTH_MODE must be 'auto', 'bearer', or 'basic'")

    last = None
    for i, mode in enumerate(modes):
        auth, headers = _auth_config(mode)
        req_kwargs = dict(kwargs)
        req_kwargs["auth"] = auth
        req_kwargs["headers"] = headers
        r = requests.request(method, url, **req_kwargs)
        LAST_AUTH_MODE = mode
        # Retry with next mode only for common auth failures.
        if i < len(modes) - 1 and r.status_code in (401, 403):
            last = r
            continue
        return r
    return last

def _print_response(r):
    if LAST_AUTH_MODE:
        print(f"[auth_mode={LAST_AUTH_MODE}]")
    try:
        print(f"[status={r.status_code}]")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except requests.exceptions.JSONDecodeError:
        print(f"HTTP {r.status_code}")
        print(r.text)

def _request_ok(method, url, **kwargs):
    r = _request(method, url, **kwargs)
    _print_response(r)
    return r

def _summary_body(r):
    try:
        return r.json()
    except requests.exceptions.JSONDecodeError:
        return {"status": r.status_code, "text": r.text}

def _get_transition_id(issue, transition_name_or_id):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{issue}/transitions"
    r = _request("GET", url)
    if r.status_code != 200:
        _print_response(r)
        return None
    data = r.json()
    transitions = data.get("transitions", [])
    for t in transitions:
        if str(t.get("id")) == str(transition_name_or_id):
            return t.get("id")
    name_lower = transition_name_or_id.lower()
    for t in transitions:
        if (t.get("name") or "").lower() == name_lower:
            return t.get("id")
    print("[status=404]")
    print(json.dumps({"error": f"Transition '{transition_name_or_id}' not found", "transitions": transitions}, indent=2, ensure_ascii=False))
    return None

def search(query):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/search"
    payload = {"jql": query}
    _request_ok("POST", url, json=payload)

def get_issue(key):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{key}"
    _request_ok("GET", url)

def comment(issue, text):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{issue}/comment"
    payload = {"body": text}
    _request_ok("POST", url, json=payload)

def create(summary, description, project_key="TEST", issue_type="Task"):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type}
        }
    }
    _request_ok("POST", url, json=payload)

def create_epic(summary, project_key="CIR", epic_name=None, reporter=None):
    if epic_name is None:
        epic_name = summary
    if reporter is None:
        reporter = USER
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "issuetype": {"name": "Epic"},
            "summary": summary,
            "customfield_10103": epic_name,  # Epic Name
            "reporter": {"name": reporter},
            "assignee": {"name": reporter}
        }
    }
    _request_ok("POST", url, json=payload)

def set_epic_link(issue, epic_key):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{issue}"
    payload = {
        "fields": {
            "customfield_10101": epic_key  # Epic Link
        }
    }
    _request_ok("PUT", url, json=payload)

def link(inward_issue, outward_issue, link_type="Issue split", comment_text=None):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issueLink"
    payload = {
        "type": {"name": link_type},
        "inwardIssue": {"key": inward_issue},
        "outwardIssue": {"key": outward_issue}
    }
    if comment_text:
        payload["comment"] = {"body": comment_text}
    _request_ok("POST", url, json=payload)

def transition(issue, transition_name_or_id):
    transition_id = _get_transition_id(issue, transition_name_or_id)
    if transition_id is None:
        return
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{issue}/transitions"
    payload = {"transition": {"id": str(transition_id)}}
    _request_ok("POST", url, json=payload)

def fields(pattern=None):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/field"
    r = _request("GET", url)
    if r.status_code != 200:
        _print_response(r)
        return
    data = r.json()
    if pattern:
        lower = pattern.lower()
        data = [f for f in data if lower in (f.get("name") or "").lower() or lower in (f.get("id") or "").lower()]
    if LAST_AUTH_MODE:
        print(f"[auth_mode={LAST_AUTH_MODE}]")
    print("[status=200]")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def _default_week_label():
    # Monday-Sunday of current week.
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    if monday.year == sunday.year:
        return f"{monday.year}-{monday:%m%d}-{sunday:%m%d}"
    return f"{monday.year}-{monday:%m%d}-{sunday.year}-{sunday:%m%d}"

def _find_epic_by_summary(project_key, summary):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/search"
    jql = f'project = {project_key} AND issuetype = Epic AND summary ~ "{summary}" ORDER BY created DESC'
    r = _request("POST", url, json={"jql": jql, "maxResults": 5, "fields": ["summary"]})
    if r.status_code != 200:
        _print_response(r)
        return None
    for issue in r.json().get("issues", []):
        if (issue.get("fields", {}).get("summary") or "").strip() == summary.strip():
            return issue.get("key")
    return None

def _issue_links(issue_key):
    url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue/{issue_key}"
    r = _request("GET", url, params={"fields": "issuelinks"})
    if r.status_code != 200:
        _print_response(r)
        return []
    return r.json().get("fields", {}).get("issuelinks", [])

def _has_link(inward_issue, outward_issue, link_type):
    links = _issue_links(inward_issue)
    for lk in links:
        t = lk.get("type", {})
        if t.get("name") != link_type:
            continue
        out = lk.get("outwardIssue")
        if out and out.get("key") == outward_issue:
            return True
    return False

def create_oncall_epic(issue_key, week_label=None, parent_issue="CIR-10739",
                       project_key="CIR", reporter=None):
    if week_label is None:
        week_label = _default_week_label()
    if reporter is None:
        reporter = USER

    summary = f"半结构化值班 {week_label}"
    epic_key = _find_epic_by_summary(project_key, summary)
    created = False

    if not epic_key:
        url = f"{JIRA_URL}/rest/api/{API_VERSION}/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "issuetype": {"name": "Epic"},
                "summary": summary,
                "customfield_10103": summary,
                "reporter": {"name": reporter},
                "assignee": {"name": reporter}
            }
        }
        r = _request("POST", url, json=payload)
        if r.status_code >= 300:
            _print_response(r)
            return
        epic_key = r.json().get("key")
        created = True

    link_created = False
    if not _has_link(parent_issue, epic_key, "Issue split"):
        url = f"{JIRA_URL}/rest/api/{API_VERSION}/issueLink"
        payload = {
            "type": {"name": "Issue split"},
            "inwardIssue": {"key": parent_issue},
            "outwardIssue": {"key": epic_key},
            "comment": {"body": f"自动关联本周值班 Epic：{epic_key}"}
        }
        r = _request("POST", url, json=payload)
        if r.status_code in (200, 201, 204):
            link_created = True
        else:
            # Non-fatal: continue linking issue to epic.
            print("[warn] failed to create Issue split link")
            _print_response(r)

    set_epic_link(issue_key, epic_key)

    if LAST_AUTH_MODE:
        print(f"[auth_mode={LAST_AUTH_MODE}]")
    print("[status=200]")
    print(json.dumps({
        "issue": issue_key,
        "epic": epic_key,
        "epic_summary": summary,
        "epic_created": created,
        "split_link_created": link_created,
        "epic_link_set": True
    }, indent=2, ensure_ascii=False))

if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
    _usage()
    sys.exit(0)

cmd = sys.argv[1]

if cmd == "search" and len(sys.argv) >= 3:
    search(sys.argv[2])
elif cmd == "get" and len(sys.argv) >= 3:
    get_issue(sys.argv[2])
elif cmd == "comment" and len(sys.argv) >= 4:
    comment(sys.argv[2], sys.argv[3])
elif cmd == "create" and len(sys.argv) >= 4:
    project = sys.argv[4] if len(sys.argv) >= 5 else "TEST"
    issue_type = sys.argv[5] if len(sys.argv) >= 6 else "Task"
    create(sys.argv[2], sys.argv[3], project, issue_type)
elif cmd == "create_epic" and len(sys.argv) >= 3:
    project = sys.argv[3] if len(sys.argv) >= 4 else "CIR"
    epic_name = sys.argv[4] if len(sys.argv) >= 5 else None
    reporter = sys.argv[5] if len(sys.argv) >= 6 else None
    create_epic(sys.argv[2], project, epic_name, reporter)
elif cmd == "set_epic_link" and len(sys.argv) >= 4:
    set_epic_link(sys.argv[2], sys.argv[3])
elif cmd == "link" and len(sys.argv) >= 4:
    link_type = sys.argv[4] if len(sys.argv) >= 5 else "Issue split"
    comment_text = sys.argv[5] if len(sys.argv) >= 6 else None
    link(sys.argv[2], sys.argv[3], link_type, comment_text)
elif cmd == "create_oncall_epic" and len(sys.argv) >= 3:
    week_label = sys.argv[3] if len(sys.argv) >= 4 else None
    parent_issue = sys.argv[4] if len(sys.argv) >= 5 else "CIR-10739"
    project_key = sys.argv[5] if len(sys.argv) >= 6 else "CIR"
    reporter = sys.argv[6] if len(sys.argv) >= 7 else None
    create_oncall_epic(sys.argv[2], week_label, parent_issue, project_key, reporter)
elif cmd == "transition" and len(sys.argv) >= 4:
    transition(sys.argv[2], sys.argv[3])
elif cmd == "fields":
    pattern = sys.argv[2] if len(sys.argv) >= 3 else None
    fields(pattern)
else:
    _usage()
    sys.exit(1)
