<p align="center">
  <a href="README.md">中文</a> | <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="assets/readme/hero.svg" alt="Zuoyebang Mistake Worksheet Suite" width="100%"/>
</p>

<p align="center">
  Two Python skills: process Zuoyebang PDFs → generate handouts → crop into individual question images
</p>

<p align="center">
  <a href="https://note.edsionc.top">📚 Knowledge Notes</a> ·
  <a href="#quick-start">🚀 Quick Start</a> ·
  <a href="#full-example">📖 Full Example</a>
</p>

---

## One-click Setup

If you don't want to configure manually, paste this prompt into your Coding Agent (Trae / Codex / Claude Code) and let it do the rest:

```text
Please install and configure https://github.com/ECdison6227/zuoyebang-pdf-cropper:

1. Git clone the repo into a temporary directory
2. Install dependencies: pip install -r requirements.txt
3. Tell me what the two skills do and their trigger words
4. Open process_mistake.py and guide me to customize the header/footer/tips to my own info
5. If a sample PDF is available, demo how to generate the handout and crop the questions
```

---

## Why I built this

I run small-group online tutoring for primary and middle-school math, physics, and chemistry, plus occasional English. I also work with A level and IB students. In a small class, every student gets different questions wrong, so I don't want everyone grinding the same worksheet — redoing problems you already know is a waste of time.

I classify problems into three levels:

- **Level 1**: You can solve it after reviewing the textbook knowledge point.
- **Level 2**: You can figure it out if given enough time after reviewing.
- **Level 3**: You can only solve it if you've seen it before; otherwise it's nearly impossible (many are university concepts pushed down).

These two skills are built for **Level 3** problems: take a Zuoyebang error-notebook PDF, turn it into a handout, then split each problem into a standalone image so I can compose a personalized wrong-question booklet per student. Practice what you don't know; skip what you do.

Currently the knowledge-point recognition mainly covers **math, physics, and chemistry**. English logic is written but not yet tested. A level and IB are too niche to include for now. (If you're in a niche track, drop me an email — address at the bottom.)

## Two Skills

This repo is a **package of two skills**. They work independently or as a pipeline:

| # | Skill | What it does | Input | Output |
|---|-------|-------------|-------|--------|
| 1 | [mistake-notebook-processor](skills/mistake-notebook-processor/) | Process Zuoyebang PDF: remove branding, add header/footer, generate handout with cover | Zuoyebang error-notebook PDF | Personalized handout PDF |
| 2 | [pdf-question-cropper](skills/pdf-question-cropper/) | Split handout PDF into individual question images by number | Handout PDF | PNGs per question + report |

### Recommended workflow

```
┌─────────────┐     ┌─────────────────────────────┐     ┌─────────────────┐
│  Zuoyebang  │ ──→ │  mistake-notebook-processor │ ──→ │ Handout PDF     │
│  Export PDF │     │  (customize on first run)   │     │                 │
└─────────────┘     └─────────────────────────────┘     └────────┬────────┘
                                                                 │
                                                                 ↓
┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│ Each student│ ←── │ Compose booklet │ ←── │   pdf-question-cropper  │
│ gets a      │     │ (only practice  │     │   Crop into PNGs        │
│ custom one  │     │  what you miss) │     │                         │
└─────────────┘     └─────────────────┘     └─────────────────────────┘
```

> Too lazy to read? Just paste this repo URL `https://github.com/ECdison6227/zuoyebang-pdf-cropper` to your AI and ask it to install, configure, and run it for you.

### About the header/footer

On the first run of **mistake-notebook-processor**, open `process_mistake.py` and change the header/footer text and tips to your own information (e.g. your knowledge site, contact). After that, every subsequent call will reuse the same config.

## What it does / What it doesn't

### What it does

| Scenario | Result |
|----------|--------|
| Raw Zuoyebang single-column PDF | Removes top logo and bottom page number |
| Pre-processed Zuoyebang handout | Removes header/footer, detects layout |
| Cross-page questions | Stitches them into one complete image |
| Questions with bottom diagrams | Keeps the full bottom when content ends near it |
| Last question on last page | Crops to actual content bottom, not the whole page |
| Knowledge points | Auto-detects math/physics/chemistry/biology topics for the cover |
| Personalized handout | Auto-generates cover (tips, topics, mastery checklist) + header/footer |

### What it doesn't

- **Must be a single-column Zuoyebang error-notebook PDF**. The cropper's question-number regex and branding areas are hardcoded for Zuoyebang; other platforms won't be split (but the handout generator can still detect knowledge points).
- **Scanned PDFs** without a text layer are not supported; you'd need OCR.
- **Handwritten** questions are not supported.
- **Multi-column layouts** are not handled.
- **English, A level, IB**: English logic exists but is untested; A level and IB are not yet included.

## Quick start

### Prerequisites

```bash
pip install pymupdf Pillow
```

### Skill 1: mistake-notebook-processor (generate handout)

Before first use, customize the header/footer in `skills/mistake-notebook-processor/process_mistake.py`:

```python
# Example default
ftr = "edsionc.top  |  2014184720@qq.com"  # Change to your site/contact
```

You can also adjust `SUBJECT_RULES` and `SUBJECT_TIPS`.

Then run:

```bash
cd skills/mistake-notebook-processor
python3 process_mistake.py your_workbook.pdf
```

Generates `数学讲义-20260617.pdf` in the same directory (subject and date parsed from filename).

### Skill 2: pdf-question-cropper (split questions)

```bash
cd skills/pdf-question-cropper
python3 crop_questions.py handout.pdf
```

Without an output directory, it creates `<PDF_name>_题目图片/`:

```
handout_题目图片/
├── 题目_01.png
├── 题目_02.png
├── ...
└── 裁剪报告.txt
```

### Prefer direct code over skills?

Each skill directory contains a standalone Python script you can run directly. But using them as skills is recommended because the SKILL.md files contain triggers, configs, and all the lessons learned.

## Standard prompts

To ask an AI to use these skills:

### Generate handout

> Please use the mistake-notebook-processor skill to handle this Zuoyebang error-notebook PDF:
> - Remove the top logo and bottom page number.
> - Generate a handout with a cover containing: date, study tips, knowledge points, and a mastery checklist.
> - Header format: date | knowledge points | subject; footer: my site edsionc.top.
> - Output filename: 学科讲义-日期.pdf.

### Split questions

> Please use the pdf-question-cropper skill to split this handout PDF into individual question images:
> - Skip the cover page automatically.
> - Merge cross-page questions.
> - Don't cut off diagrams at the bottom.
> - Crop the last question to its real content bottom.
> - Output one PNG per question plus a report.

## Full example: a 6-page, 15-question math handout

Input: [examples/输入/数学讲义-20260616.pdf](examples/输入/数学讲义-20260616.pdf)

This is a pre-processed handout: page 1 is the cover, pages 2-6 contain 15 math questions.

Generate then split:

```bash
# Generate handout (if processing a raw Zuoyebang PDF)
python3 skills/mistake-notebook-processor/process_mistake.py examples/输入/数学讲义-20260616.pdf

# Split questions
python3 skills/pdf-question-cropper/crop_questions.py examples/输入/数学讲义-20260616.pdf examples/输出
```

Output: 15 question images + report.

```
源PDF文件: 数学讲义-20260616.pdf
PDF类型: 已处理讲义
学科: 数学
总页数: 6
跳过封面页: [1]
裁剪题目总数: 15
识别知识点: 立体几何、角、线段、正方形

  题目_01.png - 第2页 [第1题]
  ...
  题目_04.png - 第2页 [第4题] (跨页合并: 第2页-第3页)
  ...
  题目_15.png - 第6页 [第15题]
```

### Three tricky cropping cases

#### 1. Cross-page question: Question 4

Globally sort question numbers and measure the distance from the next page's first number to the page header. Near the top → new question; far below → continuation.

![Cross-page merge](examples/效果对比/跨页合并_第4题.png)

#### 2. Diagram at the bottom: Question 7

When text ends close to the page bottom, keep the full bottom to avoid cutting the diagram.

![Bottom diagram protection](examples/效果对比/底部图片保护_第7题.png)

#### 3. Last question: Question 15

Scan text spans to find the real content bottom and leave only a 30px margin.

![Last question](examples/效果对比/最后一题_第15题.png)

## How it works

### Skill 1: mistake-notebook-processor

1. **Read full text**: Scan pages, regex-match knowledge-point dictionary.
2. **Create cover**: Generate cover with subject, date, tips, knowledge points, mastery checklist.
3. **Remove branding**: Use `redaction` to delete top logo (y=0~68) and bottom page number (y=795~842).
4. **Add header/footer**: Draw centered header, tip line, and footer.
5. **Merge output**: Cover first, body pages after, saved as `学科讲义-日期.pdf`.

### Skill 2: pdf-question-cropper

1. **Detect PDF type**: raw Zuoyebang, pre-processed handout, or generic PDF.
2. **Find question numbers**: Use `get_text("dict")` at line/span level, merge same-line spans, then match patterns.
3. **Global sort**: Sort non-cover question numbers by `(page_index, y)`.
4. **Cross-page decision**: If next page's first question number is >= 80px from header, treat as continuation.
5. **Content boundary protection**: For non-cross-page questions without a same-page successor, scan text bottom; if <120px from page bottom, keep full bottom.
6. **Crop and stitch**: Crop page regions and vertically stitch cross-page questions.

## Key configuration

To adapt for other platforms, edit constants in `crop_questions.py`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `ZYB_TOP_BRAND` | 68 | Raw Zuoyebang top logo height |
| `ZYB_BOTTOM_FOOTER` | 47 | Raw Zuoyebang bottom page-number height |
| `PROCESSED_HEADER` | 68 | Pre-processed handout header height |
| `PROCESSED_FOOTER` | 33 | Pre-processed handout footer height |
| `CROSS_PAGE_THRESHOLD` | 80 | Cross-page decision threshold |
| `BOTTOM_MARGIN_THRESHOLD` | 120 | Content-bottom proximity threshold |

## Lessons learned

- **Text-block granularity**: Early `get_text("blocks")` split "第 1 题" and body text into separate blocks, producing 30 images from 15 questions. Switched to `get_text("dict")`.
- **Sub-question markers**: `(1)` and `①` were mistaken for new questions; added `SUBQUESTION_PATTERN` to exclude them.
- **Cover page cropping**: Cover checklist contains "第 X 题" strings; added `COVER_PATTERN` to skip cover pages.
- **Cross-page detection**: Questions 7 and 14 were wrongly merged with the next page. Fixed with global sequence + distance threshold.
- **Bottom diagrams**: Question 7's diagram was cut in half. Added "keep full bottom when near page edge" logic.

## Related

- **[Note.edsionc.top](https://note.edsionc.top)**: My knowledge-point notes. Knowledge points identified in handouts link here; cropped question images will also be organized here.

## Connect

If you also run small-group tutoring or build wrong-question workflows, feel free to use this repo.

Our studio enrolls primary and middle-school students in **math, physics, chemistry, and English**, and also handles **A level and IB**. The A level/IB content is too niche to open-source for now, but happy to discuss if there's interest.

📮 Email: **2014184720@qq.com**

## Limitations and future

- Tuned for A4 pages; other sizes need cropping adjustments.
- Multi-column layouts not yet handled.
- Cropper only supports Zuoyebang-exported PDFs; handout generator still works for non-Zuoyebang PDFs.
- English recognition logic exists but is untested; cases will be added later.

## License

MIT
