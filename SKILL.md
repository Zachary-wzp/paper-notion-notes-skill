---
name: paper-notion-notes
description: Read a research paper, create a record in the Paper Reading Database, write a structured Notion reading note, auto-crop 1-3 key figures from the PDF, and upload those figures into the same Notion note page. Use when the user asks to read a paper and store the summary in Notion, especially for PDF or arXiv papers.
metadata:
  short-description: Read papers into Notion with figures
---

# Paper Notion Notes

Use this skill when the user wants a paper digested into the Notion workflow already set up in this workspace.

This is version 2 of the skill. The workflow is usable now, and this version explicitly composes with existing paper-reading skills instead of treating paper digestion as a standalone responsibility. The figure auto-cropping logic is still heuristic and should be treated as an iteration surface for future refinement.

## Modes

This skill has two execution modes.

### Mode 1: `MCP-only`

Use this mode when the user wants a Notion paper note without embedded figures, or when only the Notion MCP connection is available.

Characteristics:

- No `NOTION_API_KEY` required
- Use Notion MCP tools to create or update the database record and note page
- Suitable for text-only notes and metadata updates

### Mode 2: `API+Images`

Use this mode when the user wants key figures cropped from the PDF and inserted into the Notion note page.

Characteristics:

- Requires `NOTION_API_KEY` in [`.env`](../../.env)
- Uses local Python scripts plus the Notion HTTP API
- Suitable for the full pipeline: metadata, note text, key figure cropping, and image upload

## What this skill does

1. Create a database record in `Paper Reading Database`
2. Fill metadata fields such as `Name`, `Title`, `Author`, `Year`, `Publication`, `Date`, `DOI`, `URL`, and `Tag`
3. Delegate paper understanding to an existing paper-reading skill when applicable
4. Write a structured reading note into the page opened from the `Name` field
5. Auto-crop 1 to 3 key figures from the paper PDF
6. Upload those figures into the same Notion note page

## Upstream Reading Skill Routing

This skill is the Notion workflow layer, not the only paper-reading layer.

Route paper digestion as follows:

- For ordinary PDF, abstract, or pasted body text: prefer `paper-glance`
- For arXiv URLs when more structured extraction is desired: prefer `read-arxiv-paper`

After upstream reading is complete, this skill takes over and performs the Notion steps.

Do not duplicate a full paper-reading workflow inside this skill if one of the upstream skills already matches the input better.

## Required local files

- Config: [`.env`](../../.env)
- Record creation script: [`scripts/paper_note_create.py`](scripts/paper_note_create.py)
- Figure workflow script: [`scripts/paper_note_figures.py`](scripts/paper_note_figures.py)
- Image upload helper: [`scripts/notion_embed_images.py`](scripts/notion_embed_images.py)

The `.env` file only matters in `API+Images` mode. `MCP-only` mode does not require it.

## Database contract

This skill assumes the Notion database already exists and matches this schema:

- `Name`: title field used to open the note page
- `Title`: plain-text full title
- `Author`: full author list
- `Year`
- `Publication`
- `Date`
- `DOI`
- `URL`
- `Tag`
- `Reading Status`
- Optional summary fields such as `Abstract`, `Problem or Purpose`, `Methods`, `Key Findings`, `My Comments`

## Workflow Selection

1. If the user only wants a paper summary stored in Notion and does not need figures, use `MCP-only`.
2. If the user wants figures embedded in the note, use `API+Images`.
3. Before writing to Notion, route the paper-reading step:
   - PDF / abstract / pasted text -> `paper-glance`
   - arXiv URL with structured extraction needs -> `read-arxiv-paper`
4. If the user does not specify, default to `MCP-only` unless a PDF is available and figures would materially improve the note.

## Workflow

### 1. Gather paper inputs

Collect or infer:

- PDF path if available
- `Name` in the form `First Author et al.`
- Full `Title`
- Full `Author` list
- `Year`
- `Publication`
- `Date`
- `DOI` and `URL` when available
- 1 to 5 existing database tags

Prefer a PDF when the user wants figures inserted.

### 2. Run the upstream reading skill

Choose one:

- `paper-glance` for ordinary PDF, abstract, or pasted body text
- `read-arxiv-paper` for arXiv links when structured extraction is preferred

Expected output from the upstream skill:

- high-confidence title and author metadata
- one-line summary
- problem statement
- core method
- method details
- experimental setup
- key results
- innovations and limitations
- open questions or follow-up directions

Normalize the extracted output into the note template used below.

### 3. Create the database record

In `API+Images` mode, run:

```powershell
python scripts/paper_note_create.py --name "<Name>" --title "<Full Title>" --author "<Full Authors>" --year <Year> --publication "<Publication>" --date <YYYY-MM-DD> --template
```

Add `--doi`, `--url`, `--tag`, and optional summary fields when known.

This returns a `Page ID` and `URL`.

In `MCP-only` mode, create the record with Notion MCP tools instead of the local script.

### 4. Write the textual note

Open the created page and fill or update these sections:

- `One-line Summary`
- `Research Problem`
- `Core Method`
- `Method Details`
- `Experimental Setup`
- `Key Results`
- `Key Figures`
- `Innovations`
- `Limitations`
- `My Understanding`
- `My Questions`
- `Follow-up Directions`

### 5. Select key figures

Skip this step in `MCP-only` mode.

Extract 1 to 3 figures only when they materially improve comprehension.

Priority order:

1. Method overview or architecture
2. Main pipeline or workflow
3. Threat model or taxonomy
4. Core result figure
5. Ablation or comparison figure

### 6. Crop and upload figures

Skip this step in `MCP-only` mode.

Run:

```powershell
python scripts/paper_note_figures.py <page_id> "<pdf_path>" --figure-number 1 --figure-number 2
```

This script:

- auto-crops figure regions from full PDF pages
- uploads them through the Notion API
- appends them to the same note page

### 7. Finish state

Set `Reading Status` to `Done` only after:

- metadata is complete
- textual note is complete
- figures are uploaded or explicitly noted as unavailable in `API+Images` mode

## Notes

- The current auto-crop logic is heuristic. For complex two-column figures, verify the crop quality after upload.
- If a figure is not cropped well, keep the figure explanation in text and note that manual review is needed.
- If the Notion API returns `object_not_found`, the page or database has not been shared with the integration in `.env`.
- This skill should prefer composition over duplication: use upstream reading skills first, then perform Notion-specific workflow steps here.
