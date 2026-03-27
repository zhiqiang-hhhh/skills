# Error handling playbook

## 401 / invalid tenant token
- Regenerate token with app id + app secret.
- Confirm app secret is current and not rotated.

## 403 / permission denied
- Confirm app has required scopes.
- Confirm document/wiki is accessible to app identity.
- Confirm app is installed in the same tenant as the document.

## 404 / object not found
- Re-parse URL token.
- For wiki links, resolve wiki token to actual object token before reading docx.

## 429 / rate limited
- Retry with exponential backoff and jitter.
- Reduce page size for blocks API.

## Empty content
- Check whether object is docs, sheet, bitable, or file.
- Fallback to metadata call and report object type to user.
