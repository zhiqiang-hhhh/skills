#!/usr/bin/env python3
"""Fetch Feishu docx metadata, raw content, or blocks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


DOC_META_ENDPOINT = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}"
DOC_RAW_ENDPOINT = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/raw_content"
DOC_BLOCKS_ENDPOINT = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks"


def http_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_blocks(document_id: str, token: str, endpoint: str, page_size: int) -> dict:
    items = []
    page_token = None

    while True:
        q = {"page_size": page_size}
        if page_token:
            q["page_token"] = page_token
        url = f"{endpoint.format(document_id=document_id)}?{urllib.parse.urlencode(q)}"
        data = http_get(url, token)

        chunk = data.get("data", {}).get("items", [])
        items.extend(chunk)

        has_more = data.get("data", {}).get("has_more")
        page_token = data.get("data", {}).get("page_token")
        if not has_more or not page_token:
            return {"items": items, "last_response": data}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Feishu docx content")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--tenant-access-token", default=os.getenv("FEISHU_TENANT_ACCESS_TOKEN"))
    parser.add_argument("--mode", choices=["meta", "raw", "blocks"], default="raw")
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--output", help="Write JSON to file")
    parser.add_argument("--meta-endpoint", default=os.getenv("FEISHU_DOC_META_ENDPOINT", DOC_META_ENDPOINT))
    parser.add_argument("--raw-endpoint", default=os.getenv("FEISHU_DOC_RAW_ENDPOINT", DOC_RAW_ENDPOINT))
    parser.add_argument("--blocks-endpoint", default=os.getenv("FEISHU_DOC_BLOCKS_ENDPOINT", DOC_BLOCKS_ENDPOINT))
    args = parser.parse_args()

    if not args.tenant_access_token:
        print("Missing tenant access token", file=sys.stderr)
        sys.exit(2)

    try:
        if args.mode == "meta":
            data = http_get(args.meta_endpoint.format(document_id=args.document_id), args.tenant_access_token)
        elif args.mode == "raw":
            data = http_get(args.raw_endpoint.format(document_id=args.document_id), args.tenant_access_token)
        else:
            blocks = fetch_blocks(
                document_id=args.document_id,
                token=args.tenant_access_token,
                endpoint=args.blocks_endpoint,
                page_size=args.page_size,
            )
            data = {
                "code": 0,
                "msg": "ok",
                "data": {
                    "document_id": args.document_id,
                    "items": blocks["items"],
                    "total_items": len(blocks["items"]),
                    "last_response": blocks["last_response"],
                },
            }
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
