#!/usr/bin/env python3
"""Resolve Feishu wiki token to underlying object."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_ENDPOINT = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"


def fetch_node(token: str, tenant_access_token: str, endpoint: str) -> dict:
    query = urllib.parse.urlencode({"token": token})
    url = f"{endpoint}?{query}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {tenant_access_token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Feishu wiki node")
    parser.add_argument("--wiki-token", required=True)
    parser.add_argument("--tenant-access-token", default=os.getenv("FEISHU_TENANT_ACCESS_TOKEN"))
    parser.add_argument("--endpoint", default=os.getenv("FEISHU_WIKI_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--json", action="store_true", help="Print full response")
    args = parser.parse_args()

    if not args.tenant_access_token:
        print("Missing tenant access token", file=sys.stderr)
        sys.exit(2)

    try:
        data = fetch_node(args.wiki_token, args.tenant_access_token, args.endpoint)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<failed to decode response body>"
        print(f"Request failed: HTTP {e.code} {e.reason}", file=sys.stderr)
        print(f"Response body: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    node = data.get("data", {}).get("node", {})
    summary = {
        "obj_type": node.get("obj_type"),
        "obj_token": node.get("obj_token"),
        "title": node.get("title"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
