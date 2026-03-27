---
name: doris-binary-upload
description: Package and upload Doris FE lib and BE doris_be binary to COS with change summary.
---

# Doris Binary Upload

Use this skill when you need to package and upload Doris build artifacts after a successful build.

## Preconditions

- Doris artifacts already exist under `output/`.
- `curl` and `jq` are available in your environment.
- COS bucket `justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq` is publicly writable.

## Workflow

1. Generate a UUID for this upload:

```bash
UUID="$(cat /proc/sys/kernel/random/uuid)"
echo "Upload UUID: ${UUID}"
```

2. Collect code change context:

```bash
GIT_DIFF="$(git diff --stat HEAD 2>/dev/null || echo 'No uncommitted changes')"
RECENT_COMMITS="$(git log --oneline -5 2>/dev/null || echo 'No commit history')"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
TIMESTAMP="$(date -Iseconds)"

echo "=== Code Change Summary ==="
echo "Branch: ${CURRENT_BRANCH}"
echo "Timestamp: ${TIMESTAMP}"
echo "Recent commits:"
echo "${RECENT_COMMITS}"
echo "Uncommitted changes:"
echo "${GIT_DIFF}"
```

3. Package and upload FE `lib`:

```bash
cd "${DORIS_HOME}/output/fe"
tar czf "/tmp/fe-lib-${UUID}.tar.gz" lib/

curl -X PUT -T "/tmp/fe-lib-${UUID}.tar.gz" \
  "http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/fe-lib.tar.gz"

echo "FE lib uploaded to: http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/fe-lib.tar.gz"
```

4. Package and upload BE `doris_be`:

```bash
cd "${DORIS_HOME}/output/be/lib"
tar czf "/tmp/be-doris_be-${UUID}.tar.gz" doris_be

curl -X PUT -T "/tmp/be-doris_be-${UUID}.tar.gz" \
  "http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/be-doris_be.tar.gz"

echo "BE doris_be uploaded to: http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/be-doris_be.tar.gz"
```

5. Clean temporary files:

```bash
rm -f "/tmp/fe-lib-${UUID}.tar.gz" "/tmp/be-doris_be-${UUID}.tar.gz"
```

6. Persist upload summary locally:

```bash
MEMORY_DIR="${HOME}/.local/share/opencode"
MEMORY_FILE="${MEMORY_DIR}/doris-binary-uploads.json"

mkdir -p "${MEMORY_DIR}"

NEW_ENTRY="$(jq -n \
  --arg uuid "${UUID}" \
  --arg branch "${CURRENT_BRANCH}" \
  --arg timestamp "${TIMESTAMP}" \
  --arg commits "${RECENT_COMMITS}" \
  --arg diff "${GIT_DIFF}" \
  --arg fe_url "http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/fe-lib.tar.gz" \
  --arg be_url "http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/${UUID}/be-doris_be.tar.gz" \
  '{uuid: $uuid, branch: $branch, timestamp: $timestamp, recent_commits: $commits, uncommitted_changes: $diff, fe_lib_url: $fe_url, be_binary_url: $be_url}')"

if [ -f "${MEMORY_FILE}" ]; then
  jq --argjson entry "${NEW_ENTRY}" '. += [$entry]' "${MEMORY_FILE}" > "${MEMORY_FILE}.tmp" \
    && mv "${MEMORY_FILE}.tmp" "${MEMORY_FILE}"
else
  echo "[${NEW_ENTRY}]" | jq '.' > "${MEMORY_FILE}"
fi

echo "Change summary saved to: ${MEMORY_FILE}"
```

7. Print upload output:

```text
Upload UUID: <UUID>
Branch: <CURRENT_BRANCH>
Timestamp: <TIMESTAMP>

Recent commits:
<RECENT_COMMITS>

Uncommitted changes:
<GIT_DIFF>

Download URLs:
FE lib:     http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/<UUID>/fe-lib.tar.gz
BE binary:  http://justtmp-bj-1308700295.cos.ap-beijing.myqcloud.com/hzq/<UUID>/be-doris_be.tar.gz

Change summary saved to: ~/.local/share/opencode/doris-binary-uploads.json
```

## Notes

- `${DORIS_HOME}` should point to the Doris repo root.
- FE and BE artifacts are uploaded under the same UUID directory for traceability.
- If you only need FE or BE upload, skip the corresponding step.
- Query upload history with:

```bash
jq '.[] | select(.branch == "master")' ~/.local/share/opencode/doris-binary-uploads.json
```
