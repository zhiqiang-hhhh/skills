#!/usr/bin/env python3
"""Parse Feishu/Lark wiki/doc URLs into structured identifiers."""

from __future__ import annotations

import argparse
import json
import re
from urllib.parse import urlparse


WIKI_PATTERNS = [
    re.compile(r"/wiki/([A-Za-z0-9]+)"),
]

DOCX_PATTERNS = [
    re.compile(r"/docx/([A-Za-z0-9]+)"),
    re.compile(r"/docs/([A-Za-z0-9]+)"),
]


def parse_url(url: str) -> dict:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path

    result = {
        "url": url,
        "host": host,
        "kind": "unknown",
        "wiki_token": None,
        "document_id": None,
    }

    for pattern in WIKI_PATTERNS:
        m = pattern.search(path)
        if m:
            result["kind"] = "wiki"
            result["wiki_token"] = m.group(1)
            return result

    for pattern in DOCX_PATTERNS:
        m = pattern.search(path)
        if m:
            result["kind"] = "docx"
            result["document_id"] = m.group(1)
            return result

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Feishu URL")
    parser.add_argument("--url", required=True, help="Feishu wiki/doc URL")
    args = parser.parse_args()

    print(json.dumps(parse_url(args.url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
