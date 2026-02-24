---
name: pdf
description: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see REFERENCE.md. If you need to fill out a PDF form, read FORMS.md and follow its instructions.

---

## CRITICAL: Smart PDF Reading — Avoid Context Overflow

Claude's Read tool converts each PDF page into an image. The API has a **hard limit of 100 images per conversation**. A 90+ page PDF will fail outright, and even smaller PDFs can consume enormous context budget (each page-image costs far more tokens than equivalent plain text).

**This is the #1 cause of failures when processing PDFs. Always think before you read.**

### Step 0: Probe First, Read Later

For any PDF the user uploads or asks you to read, **run the probe script first** to understand what you're dealing with:

```bash
python scripts/probe_pdf.py <file.pdf>
```

This costs zero context tokens and gives you: page count, content type (text-dense / slides / scanned), estimated token cost, whether a TOC exists, and a recommended reading strategy. Follow the recommended strategy.

If probe_pdf.py is not available (e.g. running outside the skill directory), do the manual equivalent:

```bash
pdfinfo <file.pdf> | grep Pages
pdftotext -f 1 -l 3 <file.pdf> - | head -100
```

This tells you the page count and whether pdftotext produces real text (vs. empty output for scanned PDFs).

### Decision Tree

```
Is page count known?
  No  → Run: pdfinfo <file.pdf> | grep Pages
  Yes ↓

Is the PDF likely scanned (pdftotext produces < 50 chars/page)?
  Yes → Go to "Scanned PDF Path" below
  No  ↓

Page count?
  ≤ 10 pages
    → Read directly with Read tool. Safe.

  11-50 pages AND content is sparse (slides, < 500 chars/page)
    → pdftotext full extraction, read the .txt

  11-50 pages AND content is dense (> 500 chars/page)
    → pdftotext full extraction
    → Check: if .txt file > 40k tokens (~120k chars), read in chunks
    → Otherwise read the .txt in full

  51-150 pages
    → NEVER read the PDF directly
    → pdftotext -f 1 -l 5 → read overview/TOC first
    → Then extract specific sections by page range as needed
    → If user needs full coverage: python scripts/smart_read.py

  > 150 pages
    → NEVER read the PDF directly
    → MUST use chunked smart reading
    → python scripts/smart_read.py <file.pdf> --output-dir <dir>
    → Read index.json first (~small), then read specific chunks on demand
```

### Scanned PDF Path

When pdftotext produces empty or garbled output (< 50 chars/page average), the PDF is likely scanned or image-based:

1. **Try OCR first** (if pytesseract and pdf2image are available):
   ```python
   from pdf2image import convert_from_path
   import pytesseract

   # Process in small batches to control memory
   for start in range(0, total_pages, 5):
       images = convert_from_path(pdf_path, first_page=start+1, last_page=min(start+5, total_pages))
       for i, img in enumerate(images):
           text = pytesseract.image_to_string(img)
           # Save text to file...
   ```

2. **If OCR is not available or quality is poor**, fall back to reading pages as images with the Read tool — but **strictly limit to 10 pages per batch**. Ask the user which pages matter most.

### Chunked Smart Reading (for large PDFs)

For PDFs over ~50 dense pages where the user needs comprehensive understanding:

```bash
python scripts/smart_read.py <file.pdf> --output-dir <dir> --chunk-size 15
```

This produces:
- `index.json` — A manifest listing every chunk with page ranges, character counts, estimated tokens, and a preview of the first line
- `chunk_001.txt`, `chunk_002.txt`, ... — The actual text, split by page range

**Workflow:**
1. Read `index.json` (small, fits easily in context)
2. Identify which chunks are relevant based on the user's question
3. Read only those specific chunk files
4. If the user needs a full summary, process chunks one at a time and build up notes incrementally — do NOT try to read all chunks into context simultaneously

### Delegating to Subagents

When spawning Task agents to process PDF content, **always extract text BEFORE spawning the agent** and pass the .txt path instead. Use strong prohibitions in the prompt:

```
MANDATORY: Do NOT read any .pdf file with the Read tool. ONLY read the .txt files provided.
PDF files: {list of .txt paths}
```

Agents tend to ignore soft preferences ("prefer reading the text file") but will obey strong prohibitions. This single pattern prevents subagents from accidentally consuming the image budget.

---

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")
c.line(100, height - 140, 400, height - 140)
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

doc.build(story)
```

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Extract Text from Scanned PDFs
```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path('scanned.pdf')
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"
print(text)
```

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)

writer.encrypt("userpassword", "ownerpassword")
with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| **Probe PDF** | probe_pdf.py | `python scripts/probe_pdf.py <file.pdf>` |
| **Smart chunked read** | smart_read.py | `python scripts/smart_read.py <file.pdf> --output-dir <dir>` |
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | See FORMS.md | See FORMS.md |

## Next Steps

- For advanced pypdfium2 usage, see REFERENCE.md
- For JavaScript libraries (pdf-lib), see REFERENCE.md
- If you need to fill out a PDF form, follow the instructions in FORMS.md
- For troubleshooting guides, see REFERENCE.md
