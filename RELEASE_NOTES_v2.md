# Release Notes: v2 Initial Public Release

## English

This is the first public release of `paper-notion-notes` version 2.

### Highlights

- Added explicit two-mode workflow:
  - `MCP-only` for text-only Notion notes
  - `API+Images` for full note + key figure upload
- Added upstream routing rules for paper digestion:
  - PDF / abstract / pasted text -> `paper-glance`
  - arXiv URL with structured extraction needs -> `read-arxiv-paper`
- Added `paper_note_create.py` to create a paper record and write metadata into the Notion database
- Added `paper_note_figures.py` to crop requested figure numbers from a PDF and upload them into the note page
- Added `notion_embed_images.py` as the low-level helper for dotenv loading, figure cropping, image upload, and page block insertion
- Added open-source repository basics:
  - `README.md`
  - `README.zh-CN.md`
  - `.env.example`
  - `.gitignore`
  - `LICENSE`
  - `agents/openai.yaml`

### Known limitations

- Figure auto-cropping is heuristic and may be imperfect for complex two-column or wide figures
- The workflow assumes a pre-existing Notion database schema compatible with the skill
- `API+Images` mode requires a valid `NOTION_API_KEY` and proper page/database sharing with the integration

### Positioning

Version 2 is the first public release that treats `paper-notion-notes` as a Notion workflow orchestration skill rather than a standalone paper-reading skill.

## 中文

这是 `paper-notion-notes` 第二版（v2）的第一次公开发布。

### 重点更新

- 明确拆分为两种工作模式：
  - `MCP-only`：仅写入文本笔记
  - `API+Images`：写入文本笔记并上传关键图片
- 明确接入上游读论文 skill 路由：
  - 普通 PDF / 摘要 / 粘贴正文 -> `paper-glance`
  - 需要更结构化抽取的 arXiv 链接 -> `read-arxiv-paper`
- 新增 `paper_note_create.py`：在 Notion 数据库中创建论文记录并写入元数据
- 新增 `paper_note_figures.py`：从 PDF 中裁剪指定图号并上传到笔记页面
- 新增 `notion_embed_images.py`：负责 `.env` 读取、figure 裁剪、图片上传和页面 block 写入
- 补齐公开仓库基础文件：
  - `README.md`
  - `README.zh-CN.md`
  - `.env.example`
  - `.gitignore`
  - `LICENSE`
  - `agents/openai.yaml`

### 已知限制

- 图片自动裁剪仍然是启发式逻辑，对复杂双栏图或跨栏图可能不够理想
- 这套流程默认目标 Notion 数据库结构已经准备好并与 skill 兼容
- `API+Images` 模式需要有效的 `NOTION_API_KEY`，并且需要将页面或数据库共享给对应 integration

### 版本定位

v2 是第一次公开发布的版本，它将 `paper-notion-notes` 明确定位为 Notion 工作流编排 skill，而不是单独的读论文 skill。
