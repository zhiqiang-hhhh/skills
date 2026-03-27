---
name: feishu-doc-reader
description: Read and normalize Feishu/Lark wiki or docx content through Open Platform APIs. Use when a user asks to access a Feishu wiki/doc link, extract document content, convert Feishu content to Markdown/JSON, or troubleshoot token/permission issues for document reads.
---

# Feishu Doc Reader

## Follow this workflow

1. Validate credentials from environment variables:
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

2. Parse link/token first:
- Run `scripts/parse_feishu_url.py --url <feishu-url>`.
- Distinguish `wiki` node token vs `docx` document id.

3. Fetch access token:
- Run `scripts/get_tenant_token.py` unless a valid token is already provided.

4. Resolve and fetch content:
- If URL is wiki: run `scripts/fetch_wiki_node.py` to resolve `obj_token`/`obj_type`.
- If resolved object is `docx`: run `scripts/fetch_docx_content.py`.

5. Normalize output:
- Keep full API response in JSON for debugging.
- Generate compact markdown via `scripts/render_markdown.py` when user requests readable output.

## Use bundled references only when needed

- Endpoint list: `references/api-endpoints.md`
- Required permission scopes: `references/scopes.md`
- Error handling playbook: `references/error-handling.md`

## Guardrails

- Never hardcode app secret or access token.
- Never print secrets in logs.
- If API response conflicts with assumptions, trust API payload and surface raw JSON to user.
- When endpoint behavior differs by tenant or API version, ask user to confirm scope and app type (self-built vs marketplace).

## Minimal command sequence

```bash
# 1) Parse URL
scripts/parse_feishu_url.py --url 'https://tenant.feishu.cn/wiki/xxxx'

# 2) Get tenant token
export FEISHU_APP_ID='cli_xxx'
export FEISHU_APP_SECRET='xxx'
export FEISHU_TENANT_ACCESS_TOKEN="$(scripts/get_tenant_token.py)"

# 3a) Resolve wiki node
scripts/fetch_wiki_node.py --wiki-token '<wiki_token>' --json

# 3b) Fetch docx content
scripts/fetch_docx_content.py --document-id '<doc_token>' --mode raw --output /tmp/doc.json

# 4) Render markdown
scripts/render_markdown.py --input /tmp/doc.json --output /tmp/doc.md
```
