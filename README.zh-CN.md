# paper-notion-notes

`paper-notion-notes` 是一个用于将论文整理为 Notion 结构化笔记的 Codex skill。

它适用于已经存在目标 Notion 数据库与笔记模板的论文阅读工作流。这个 skill 的核心职责不是单独“读懂论文”，而是负责 Notion 工作流层：创建文献记录、写入元数据、生成结构化笔记，并在需要时从 PDF 中裁剪关键图片并上传到同一篇 Notion 笔记页面。

## 功能

- 在 Notion 数据库中创建论文记录
- 填写 `Name`、`Title`、`Author`、`Year`、`Publication`、`Date`、`DOI`、`URL`、`Tag` 等元数据字段
- 在 `Name` 对应打开的页面中写入结构化阅读笔记
- 将论文阅读步骤路由到已有读论文 skill，而不是重复实现
- 从 PDF 自动裁剪 1 到 3 张关键图片
- 将裁剪后的图片上传到同一篇 Notion 笔记页面

## 当前版本

这个仓库对应的是 skill 的第二个版本（v2）。

v2 的核心变化是明确引入上游论文阅读 skill 路由：

- 普通 PDF / 摘要 / 粘贴正文 -> `paper-glance`
- arXiv 链接且需要更结构化抽取 -> `read-arxiv-paper`

## 两种模式

### 1. MCP-only

适用于只想把文字笔记和元数据写入 Notion，不需要嵌入图片的情况。

特点：

- 不需要 `NOTION_API_KEY`
- 使用 Notion MCP 工具
- 适合纯文本论文笔记流程

### 2. API+Images

适用于希望将 PDF 里的关键图片裁剪后嵌入同一篇 Notion 笔记页面的情况。

特点：

- 需要 `NOTION_API_KEY`
- 使用本地 Python 脚本和 Notion HTTP API
- 适合“文本总结 + 图片笔记”的完整流程

## 仓库结构

```text
.
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── .env.example
├── .gitignore
└── scripts/
    ├── notion_embed_images.py
    ├── paper_note_create.py
    └── paper_note_figures.py
```

## 脚本说明

### `scripts/paper_note_create.py`

用于在目标 Notion 数据库中创建一条新的论文记录，并写入元数据。

示例：

```powershell
python scripts/paper_note_create.py \
  --name "Kai Greshake et al." \
  --title "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" \
  --author "Kai Greshake; Sahar Abdelnabi; Shailesh Mishra; Christoph Endres; Thorsten Holz; Mario Fritz" \
  --year 2023 \
  --publication "arXiv" \
  --date 2026-03-31 \
  --url "https://arxiv.org/abs/2302.12173" \
  --doi "https://doi.org/10.48550/arXiv.2302.12173" \
  --tag "对抗攻击" \
  --template
```

### `scripts/paper_note_figures.py`

用于从论文 PDF 中裁剪指定图号，并将图片上传到指定 Notion 笔记页。

示例：

```powershell
python scripts/paper_note_figures.py \
  <page_id> \
  "<pdf_path>" \
  --figure-number 1 \
  --figure-number 2 \
  --figure-number 3
```

### `scripts/notion_embed_images.py`

底层辅助脚本，负责：

- 读取 `.env`
- 上传图片到 Notion
- 从 PDF 页面中自动裁剪 figure 区域
- 将图片追加到指定 Notion 页面

## 配置

请先基于 `.env.example` 创建本地 `.env` 文件：

```env
NOTION_API_KEY=your_notion_integration_token
NOTION_VERSION=2026-03-11
```

注意：

- `.env` 只在 `API+Images` 模式下需要
- 如果你只用 Notion MCP 工具而不通过本地脚本上传图片，则不需要 `NOTION_API_KEY`

## 运行依赖

- Python 3
- `requests`
- `Pillow`
- 本地 PDF 工具：
  - `pdftotext`
  - `pdftoppm`

当前实现是在 Windows 环境下编写和测试的，默认依赖系统可用的 TeX Live PDF 工具。

## 关于图片裁剪

v2 的图片裁剪仍然是启发式逻辑。

这意味着：

- 对常见论文版式通常可用
- 对复杂双栏图或跨栏宽图仍可能裁得不够理想
- 上传后建议人工复查一下图片效果

## 推荐工作流

1. 用上游读论文 skill 完成论文理解
2. 将输出规范化为固定笔记结构
3. 创建 Notion 数据库记录
4. 写入正文笔记
5. 按需裁剪并上传 1 到 3 张关键图片
6. 将记录标记为完成

## License

当前仓库还没有附带 license 文件。如果你希望公开明确复用条件，建议后续补充。