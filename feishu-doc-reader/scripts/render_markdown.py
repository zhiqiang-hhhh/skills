#!/usr/bin/env python3
"""Render a minimal markdown view from Feishu docx API responses."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(extract_text(v) for v in value)
    if isinstance(value, dict):
        # Keep heuristic simple: recursively gather common text-like fields.
        text_bits = []
        for k, v in value.items():
            if k in {"text", "content", "title"}:
                text_bits.append(extract_text(v))
            else:
                text_bits.append(extract_text(v))
        return " ".join(x for x in text_bits if x)
    return ""


def render(data: dict) -> str:
    body = data.get("data", {})

    if "content" in body and isinstance(body["content"], str):
        # raw_content endpoint often returns markdown-like text directly.
        return body["content"].strip() + "\n"

    items = body.get("items", [])
    if not items:
        meta_text = extract_text(body).strip()
        return (meta_text or "(no content)") + "\n"

    lines = []
    for item in items:
        line = extract_text(item).strip()
        if line:
            lines.append(f"- {line}")

    if not lines:
        return "(no content)\n"
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Feishu response JSON into markdown")
    parser.add_argument("--input", required=True, help="JSON file from fetch_docx_content.py")
    parser.add_argument("--output", help="Markdown output path")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Input file not found", file=sys.stderr)
        sys.exit(2)

    md = render(data)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
    else:
        print(md, end="")


if __name__ == "__main__":
    main()
