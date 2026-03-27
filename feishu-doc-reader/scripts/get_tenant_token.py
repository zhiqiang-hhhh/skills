#!/usr/bin/env python3
"""Fetch Feishu tenant_access_token via app credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_ENDPOINT = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"


def fetch_token(app_id: str, app_secret: str, endpoint: str) -> dict:
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Get Feishu tenant access token")
    parser.add_argument("--app-id", default=os.getenv("FEISHU_APP_ID"))
    parser.add_argument("--app-secret", default=os.getenv("FEISHU_APP_SECRET"))
    parser.add_argument("--endpoint", default=os.getenv("FEISHU_AUTH_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--json", action="store_true", help="Print full JSON response")
    args = parser.parse_args()

    if not args.app_id or not args.app_secret:
        print("Missing FEISHU_APP_ID or FEISHU_APP_SECRET", file=sys.stderr)
        sys.exit(2)

    try:
        data = fetch_token(args.app_id, args.app_secret, args.endpoint)
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    token = data.get("tenant_access_token")
    if not token:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(token)


if __name__ == "__main__":
    main()
