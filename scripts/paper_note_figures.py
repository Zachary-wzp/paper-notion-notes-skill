#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import notion_embed_images as embed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Paper reading workflow helper: auto-crop key figures from a PDF "
            "and append them to an existing Notion paper note page."
        ),
    )
    parser.add_argument("page_id", help="Target Notion note page ID.")
    parser.add_argument("pdf", help="Source paper PDF path.")
    parser.add_argument(
        "--figure-number",
        action="append",
        type=int,
        required=True,
        metavar="N",
        help="Figure number to crop and upload. Repeat for multiple figures.",
    )
    parser.add_argument(
        "--heading",
        default="Key Figures",
        help="Section heading inserted before uploaded figures.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI used during auto-cropping.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    embed.load_dotenv(script_dir / ".env")

    api_key = embed.os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing NOTION_API_KEY. Set it in .env next to this script or in the environment."
        )

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    figure_specs = []
    for number in args.figure_number:
        figure_specs.append(
            embed.crop_figure_from_pdf(
                pdf_path=pdf_path,
                figure_number=number,
                dpi=args.dpi,
                output_dir=script_dir,
            )
        )

    session = embed.requests.Session()
    blocks = []
    if args.heading:
        blocks.append(embed.heading_block(args.heading, 2))

    for index, (path, caption) in enumerate(figure_specs, start=1):
        upload = embed.create_file_upload(session, api_key, args.timeout)
        upload_id = upload["id"]
        uploaded = embed.send_file_upload(session, api_key, upload_id, path, args.timeout)
        if uploaded.get("status") != "uploaded":
            raise embed.NotionUploadError(
                f"Unexpected upload status for {path.name}: {uploaded.get('status')}"
            )
        blocks.append(embed.heading_block(f"Figure {index}", 3))
        blocks.append(embed.image_block(upload_id, caption))

    embed.append_blocks(session, api_key, args.page_id, blocks, args.timeout)

    print("Paper note figure workflow completed.")
    print(f"Target page: {args.page_id}")
    print(f"PDF: {pdf_path}")
    for path, caption in figure_specs:
        print(f"- {caption}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
