[English](./README.md) | [简体中文](./README.zh-CN.md)

# paper-notion-notes

`paper-notion-notes` is a Codex skill for turning research papers into structured Notion notes.

It is designed for a paper-reading workflow that already has a target Notion database and note template. The skill focuses on the Notion layer: creating a paper record, writing metadata, storing a structured note, and optionally extracting and uploading key figures from the PDF.

## Current Version

This repository currently publishes the first public release of version 2.

Version 2 introduces:

- explicit two-mode workflow: `MCP-only` and `API+Images`
- upstream paper-reading routing:
  - ordinary PDF / abstract / pasted body text -> `paper-glance`
  - arXiv URL with structured extraction needs -> `read-arxiv-paper`
- local scripts for record creation, figure cropping, and figure upload

## Features

- Create a paper record in a Notion database
- Fill metadata fields such as `Name`, `Title`, `Author`, `Year`, `Publication`, `Date`, `DOI`, `URL`, and `Tag`
- Write a structured reading note into the page opened from the `Name` field
- Route paper digestion to existing reading skills instead of duplicating them
- Auto-crop 1 to 3 key figures from a PDF
- Upload cropped figures into the same Notion note page

## Modes

### 1. MCP-only

Use this mode when you only want text notes and metadata written to Notion.

Characteristics:

- does not require `NOTION_API_KEY`
- uses Notion MCP tools
- good for text-only note workflows

### 2. API+Images

Use this mode when you want key figures cropped from the PDF and embedded into the same Notion note page.

Characteristics:

- requires `NOTION_API_KEY`
- uses local Python scripts plus the Notion HTTP API
- good for full text + image paper notes

## Repository Structure

```text
.
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── .env.example
├── .gitignore
├── LICENSE
├── agents/
│   └── openai.yaml
└── scripts/
    ├── notion_embed_images.py
    ├── paper_note_create.py
    └── paper_note_figures.py
```

## Scripts

### `scripts/paper_note_create.py`

Creates a new paper record in the target Notion database and fills metadata fields.

### `scripts/paper_note_figures.py`

Crops requested figures from a paper PDF and uploads them into the target Notion note page.

### `scripts/notion_embed_images.py`

Low-level helper for:

- loading `.env`
- uploading image files to Notion
- auto-cropping figure regions from full PDF pages
- appending uploaded images to a Notion page

## Configuration

Create a local `.env` file from `.env.example`.

```env
NOTION_API_KEY=your_notion_integration_token
NOTION_VERSION=2026-03-11
```

Notes:

- `.env` is only required for `API+Images` mode
- if you only use Notion MCP tools and do not upload images through local scripts, you do not need `NOTION_API_KEY`

## Requirements

- Python 3
- `requests`
- `Pillow`
- local PDF tools available to the scripts:
  - `pdftotext`
  - `pdftoppm`

The current implementation was built and tested in a Windows environment with TeX Live PDF utilities available in the system.

## Notes on Figure Cropping

Figure cropping is heuristic in version 2.

That means:

- it works for many common paper layouts
- it can still crop imperfectly for complex two-column or wide figures
- manual review is recommended after upload

## Intended Workflow

1. Read the paper with an upstream reading skill
2. Normalize the extracted content into the note structure
3. Create the Notion record
4. Write the textual note
5. Crop and upload 1 to 3 key figures when needed
6. Mark the note as complete

## License

This repository uses the [MIT License](./LICENSE).
