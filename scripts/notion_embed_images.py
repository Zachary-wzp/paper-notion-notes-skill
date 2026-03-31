#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import requests
from PIL import Image


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = os.environ.get("NOTION_VERSION", "2026-03-11")
MAX_SMALL_FILE_BYTES = 20 * 1024 * 1024


class NotionUploadError(RuntimeError):
    pass


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload local images to Notion and append them as image blocks.",
    )
    parser.add_argument(
        "page_id",
        help="Target Notion page/block ID that will receive the image blocks.",
    )
    parser.add_argument(
        "--figure",
        action="append",
        metavar="PATH[::CAPTION]",
        help=(
            "Local image path, optionally followed by ::caption. "
            "Repeat this flag for multiple figures."
        ),
    )
    parser.add_argument(
        "--heading",
        default="Key Figures",
        help="Optional heading inserted before the figures. Use an empty string to skip.",
    )
    parser.add_argument(
        "--heading-level",
        type=int,
        choices=(1, 2, 3),
        default=2,
        help="Heading level for the section title.",
    )
    parser.add_argument(
        "--skip-figure-headings",
        action="store_true",
        help="Do not insert Figure 1 / Figure 2 subheadings above each image.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--from-pdf",
        help="Optional source PDF path. When provided with --figure-number, figures are auto-cropped from pages.",
    )
    parser.add_argument(
        "--figure-number",
        action="append",
        type=int,
        metavar="N",
        help="Figure number to auto-crop from the PDF. Repeat for multiple figures.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI used when auto-cropping figures from PDF pages.",
    )
    return parser.parse_args()


def split_figure_spec(spec: str) -> tuple[Path, str]:
    path_str, sep, caption = spec.partition("::")
    path = Path(path_str).expanduser().resolve()
    return path, caption.strip() if sep else ""


def safe_stem(path: Path) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._")
    if cleaned:
        return cleaned[:80]
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]


def build_headers(api_key: str, *, json_body: bool = True) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def ensure_success(response: requests.Response, context: str) -> dict:
    if response.ok:
        if response.content:
            return response.json()
        return {}

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}

    raise NotionUploadError(f"{context} failed: {response.status_code} {payload}")


def create_file_upload(session: requests.Session, api_key: str, timeout: int) -> dict:
    response = session.post(
        f"{NOTION_API_BASE}/file_uploads",
        headers=build_headers(api_key),
        json={},
        timeout=timeout,
    )
    return ensure_success(response, "Create file upload")


def send_file_upload(
    session: requests.Session,
    api_key: str,
    upload_id: str,
    path: Path,
    timeout: int,
) -> dict:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as fh:
        response = session.post(
            f"{NOTION_API_BASE}/file_uploads/{upload_id}/send",
            headers=build_headers(api_key, json_body=False),
            files={"file": (path.name, fh, content_type)},
            timeout=timeout,
        )
    return ensure_success(response, f"Upload file {path.name}")


def rich_text(text: str) -> list[dict]:
    if not text:
        return []
    return [{"type": "text", "text": {"content": text}}]


def heading_block(text: str, level: int) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": rich_text(text)},
    }


def paragraph_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text(text)},
    }


def image_block(upload_id: str, caption: str) -> dict:
    return {
        "object": "block",
        "type": "image",
        "image": {
            "type": "file_upload",
            "caption": rich_text(caption),
            "file_upload": {"id": upload_id},
        },
    }


def chunked(items: Iterable[dict], size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def append_blocks(
    session: requests.Session,
    api_key: str,
    page_id: str,
    blocks: list[dict],
    timeout: int,
) -> None:
    for batch in chunked(blocks, 100):
        response = session.patch(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            headers=build_headers(api_key),
            json={"children": batch},
            timeout=timeout,
        )
        ensure_success(response, "Append block children")


def bbox_pages(pdf_path: Path, temp_dir: Path) -> Path:
    bbox_path = temp_dir / "bbox.html"
    subprocess.run(
        [
            r"C:\texlive\2021\bin\win32\pdftotext.exe",
            "-bbox-layout",
            "-enc",
            "UTF-8",
            str(pdf_path),
            str(bbox_path),
        ],
        check=True,
    )
    return bbox_path


def page_renders(pdf_path: Path, temp_dir: Path, dpi: int) -> list[Path]:
    prefix = temp_dir / "render"
    subprocess.run(
        [
            r"C:\texlive\2021\bin\win32\pdftoppm.exe",
            "-r",
            str(dpi),
            "-png",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
    )
    return sorted(temp_dir.glob("render-*.png"))


def parse_bbox_html(bbox_path: Path) -> list[dict]:
    text = bbox_path.read_text(encoding="utf-8")
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text)
    text = text.replace(' xmlns="http://www.w3.org/1999/xhtml"', "")
    root = ET.fromstring(text)
    pages: list[dict] = []
    for page in root.findall(".//page"):
        words = []
        for word in page.findall(".//word"):
            words.append(
                {
                    "text": (word.text or "").strip(),
                    "x_min": float(word.attrib["xMin"]),
                    "x_max": float(word.attrib["xMax"]),
                    "y_min": float(word.attrib["yMin"]),
                    "y_max": float(word.attrib["yMax"]),
                }
            )
        pages.append(
            {
                "width": float(page.attrib["width"]),
                "height": float(page.attrib["height"]),
                "words": words,
            }
        )
    return pages


def find_figure_caption(page: dict, figure_number: int) -> dict | None:
    words = page["words"]
    pattern = f"Figure {figure_number}:"
    for idx in range(len(words)):
        parts = []
        for inner in range(idx, min(idx + 5, len(words))):
            parts.append(words[inner]["text"])
            joined = " ".join(parts)
            if joined.startswith(pattern):
                chunk = words[idx : inner + 1]
                return {
                    "x_min": min(w["x_min"] for w in chunk),
                    "x_max": max(w["x_max"] for w in chunk),
                    "y_min": min(w["y_min"] for w in chunk),
                    "y_max": max(w["y_max"] for w in chunk),
                }
    return None


def crop_region_for_caption(page: dict, caption_box: dict) -> tuple[float, float, float, float]:
    page_width = page["width"]
    column_mid = page_width / 2
    caption_width = caption_box["x_max"] - caption_box["x_min"]
    full_width_caption = (
        caption_width >= page_width * 0.55
        or (caption_box["x_min"] <= 70 and caption_box["x_max"] >= column_mid)
    )
    same_band = [
        w
        for w in page["words"]
        if caption_box["y_min"] - 3 <= w["y_min"] <= caption_box["y_max"] + 6
    ]
    if full_width_caption:
        x0, x1 = 36.0, page_width - 36.0
    elif same_band:
        col_center = sum((w["x_min"] + w["x_max"]) / 2 for w in same_band) / len(same_band)
        if col_center < column_mid:
            x0, x1 = 36.0, column_mid - 6.0
        else:
            x0, x1 = column_mid + 6.0, page_width - 36.0
    else:
        col_center = (caption_box["x_min"] + caption_box["x_max"]) / 2
        if col_center < column_mid:
            x0, x1 = 36.0, column_mid - 6.0
        else:
            x0, x1 = column_mid + 6.0, page_width - 36.0

    y1 = max(36.0, caption_box["y_min"] - 6.0)
    search_words = [
        w
        for w in page["words"]
        if x0 <= (w["x_min"] + w["x_max"]) / 2 <= x1 and w["y_max"] < caption_box["y_min"] - 4
    ]
    if search_words:
        top_y = min(w["y_min"] for w in search_words)
    else:
        top_y = 72.0

    top_limit = max(36.0, top_y - 8.0)
    return x0, top_limit, x1, y1


def crop_figure_from_pdf(
    pdf_path: Path,
    figure_number: int,
    dpi: int,
    output_dir: Path,
) -> tuple[Path, str]:
    with tempfile.TemporaryDirectory() as temp_str:
        temp_dir = Path(temp_str)
        bbox_path = bbox_pages(pdf_path, temp_dir)
        renders = page_renders(pdf_path, temp_dir, dpi)
        pages = parse_bbox_html(bbox_path)

        for page_index, page in enumerate(pages, start=1):
            caption = find_figure_caption(page, figure_number)
            if not caption:
                continue

            x0, y0, x1, y1 = crop_region_for_caption(page, caption)
            render_path = renders[page_index - 1]
            image = Image.open(render_path)
            scale_x = image.width / page["width"]
            scale_y = image.height / page["height"]
            crop_box = (
                max(0, int(x0 * scale_x)),
                max(0, int(y0 * scale_y)),
                min(image.width, int(x1 * scale_x)),
                min(image.height, int(y1 * scale_y)),
            )
            cropped = image.crop(crop_box)
            out_path = output_dir / f"{safe_stem(pdf_path)}_figure_{figure_number}.png"
            cropped.save(out_path)
            return out_path, f"Figure {figure_number}"

    raise NotionUploadError(f"Could not locate Figure {figure_number} in {pdf_path}")


def main() -> int:
    args = parse_args()
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing NOTION_API_KEY. Set it in the environment or in a .env file "
            "next to notion_embed_images.py."
        )

    figure_specs = [split_figure_spec(spec) for spec in (args.figure or [])]
    if args.figure_number:
        if not args.from_pdf:
            raise SystemExit("--from-pdf is required when using --figure-number.")
        pdf_path = Path(args.from_pdf).expanduser().resolve()
        if not pdf_path.exists():
            raise SystemExit(f"PDF not found: {pdf_path}")
        output_dir = Path(__file__).resolve().parent
        for figure_number in args.figure_number:
            figure_specs.append(
                crop_figure_from_pdf(
                    pdf_path=pdf_path,
                    figure_number=figure_number,
                    dpi=args.dpi,
                    output_dir=output_dir,
                )
            )
    if not figure_specs:
        raise SystemExit("Provide at least one --figure or one --figure-number with --from-pdf.")
    for path, _ in figure_specs:
        if not path.exists():
            raise SystemExit(f"Figure not found: {path}")
        if not path.is_file():
            raise SystemExit(f"Figure is not a file: {path}")
        if path.stat().st_size > MAX_SMALL_FILE_BYTES:
            raise SystemExit(
                f"Figure exceeds 20 MB small-upload limit: {path} "
                f"({path.stat().st_size} bytes)"
            )

    session = requests.Session()
    blocks: list[dict] = []
    if args.heading:
        blocks.append(heading_block(args.heading, args.heading_level))

    for index, (path, caption) in enumerate(figure_specs, start=1):
        upload = create_file_upload(session, api_key, args.timeout)
        upload_id = upload["id"]
        uploaded = send_file_upload(session, api_key, upload_id, path, args.timeout)

        if uploaded.get("status") != "uploaded":
            raise NotionUploadError(
                f"Unexpected upload status for {path.name}: {uploaded.get('status')}"
            )

        if not args.skip_figure_headings:
            blocks.append(heading_block(f"Figure {index}", 3))
        if caption:
            blocks.append(paragraph_block(f"Caption: {caption}"))
        blocks.append(image_block(upload_id, caption))

    append_blocks(session, api_key, args.page_id, blocks, args.timeout)

    print("Uploaded figures and appended blocks successfully.")
    print(f"Target page: {args.page_id}")
    for path, caption in figure_specs:
        suffix = f" :: {caption}" if caption else ""
        print(f"- {path}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
