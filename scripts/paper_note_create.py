#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests

import notion_embed_images as embed


NOTION_API_BASE = "https://api.notion.com/v1"
DATABASE_ID = "966d2a1c19144c2cb7d69fd1f6833b35"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a new record in Paper Reading Database and populate the metadata fields."
        ),
    )
    parser.add_argument("--name", required=True, help="Short clickable note title, e.g. 'Kai Greshake et al.'")
    parser.add_argument("--title", required=True, help="Full paper title.")
    parser.add_argument("--author", required=True, help="Full author list as plain text.")
    parser.add_argument("--year", type=int, required=True, help="Publication year.")
    parser.add_argument("--publication", required=True, help="Journal, conference, or archive name.")
    parser.add_argument("--date", required=True, help="Reading date in YYYY-MM-DD format.")
    parser.add_argument("--doi", help="DOI URL, e.g. https://doi.org/10.xxxx/xxxx")
    parser.add_argument("--url", help="Paper URL, e.g. arXiv abstract or publisher page.")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Database tag option. Repeat for multiple tags.",
    )
    parser.add_argument(
        "--reading-status",
        default="In progress",
        help="Reading Status value. Default: 'In progress'.",
    )
    parser.add_argument("--abstract", help="Optional abstract text.")
    parser.add_argument("--problem", help="Optional Problem or Purpose summary.")
    parser.add_argument("--methods", help="Optional Methods summary.")
    parser.add_argument("--key-findings", help="Optional Key Findings summary.")
    parser.add_argument("--comments", help="Optional My Comments summary.")
    parser.add_argument(
        "--template",
        action="store_true",
        help="Append the default paper-note section skeleton to the new page body.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": os.environ.get("NOTION_VERSION", "2026-03-11"),
        "Content-Type": "application/json",
    }


def title_prop(text: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": text}}]}


def rich_text_prop(text: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


def number_prop(value: int) -> dict:
    return {"number": value}


def url_prop(value: str) -> dict:
    return {"url": value}


def date_prop(value: str) -> dict:
    return {"date": {"start": value}}


def status_prop(value: str) -> dict:
    return {"status": {"name": value}}


def multi_select_prop(values: list[str]) -> dict:
    return {"multi_select": [{"name": value} for value in values]}


def note_template_blocks() -> list[dict]:
    headings = [
        "One-line Summary",
        "Research Problem",
        "Core Method",
        "Method Details",
        "Experimental Setup",
        "Key Results",
        "Key Figures",
        "Innovations",
        "Limitations",
        "My Understanding",
        "My Questions",
        "Follow-up Directions",
    ]
    blocks: list[dict] = []
    for heading in headings:
        blocks.append(embed.heading_block(heading, 1))
        blocks.append(embed.paragraph_block("- "))
    return blocks


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    embed.load_dotenv(script_dir / ".env")

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise SystemExit("Missing NOTION_API_KEY. Set it in .env or the environment.")

    properties = {
        "Name": title_prop(args.name),
        "Title": rich_text_prop(args.title),
        "Author": rich_text_prop(args.author),
        "Year": number_prop(args.year),
        "Publication": rich_text_prop(args.publication),
        "Date": date_prop(args.date),
        "Reading Status": status_prop(args.reading_status),
    }

    if args.doi:
        properties["DOI"] = url_prop(args.doi)
    if args.url:
        properties["URL"] = url_prop(args.url)
    if args.tag:
        properties["Tag"] = multi_select_prop(args.tag)
    if args.abstract:
        properties["Abstract"] = rich_text_prop(args.abstract)
    if args.problem:
        properties["Problem or Purpose"] = rich_text_prop(args.problem)
    if args.methods:
        properties["Methods"] = rich_text_prop(args.methods)
    if args.key_findings:
        properties["Key Findings"] = rich_text_prop(args.key_findings)
    if args.comments:
        properties["My Comments"] = rich_text_prop(args.comments)

    payload: dict = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties,
    }
    if args.template:
        payload["children"] = note_template_blocks()

    response = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=build_headers(api_key),
        data=json.dumps(payload),
        timeout=args.timeout,
    )
    data = embed.ensure_success(response, "Create paper note record")

    print("Created paper note record successfully.")
    print(f"Page ID: {data['id']}")
    print(f"URL: {data['url']}")
    print(f"Name: {args.name}")
    print(f"Title: {args.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
