# Common scopes for read-only doc access

Use exact names from Feishu Open Platform UI because scope labels can change.

Typical minimum set:
- Auth/token scope for app credential flow
- Wiki read scope (for resolving wiki token)
- Docx read scope (for document content)
- Drive file read scope (when document is treated as drive resource)

Checklist:
- App is installed to target tenant.
- Document is shared to app/account context.
- Scope changes are published and approved in tenant.
