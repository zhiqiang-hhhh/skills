# Feishu Endpoints (doc-read flow)

Base: `https://open.feishu.cn`

- Tenant access token:
  - `POST /open-apis/auth/v3/tenant_access_token/internal`
- Wiki node resolve:
  - `GET /open-apis/wiki/v2/spaces/get_node?token=<wiki_token>`
- Docx metadata:
  - `GET /open-apis/docx/v1/documents/{document_id}`
- Docx raw content:
  - `GET /open-apis/docx/v1/documents/{document_id}/raw_content`
- Docx blocks (paginated):
  - `GET /open-apis/docx/v1/documents/{document_id}/blocks?page_size=...&page_token=...`

Notes:
- Keep endpoint paths configurable in scripts because some tenants use updated routes.
- Confirm official docs if fields differ.
