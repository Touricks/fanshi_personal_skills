#!/usr/bin/env python3
"""
probe_pdf.py - Automated PDF reconnaissance script.

Outputs a structured report about a PDF to help Claude decide the optimal
reading strategy BEFORE consuming any context window budget.

Usage:
    python probe_pdf.py <input.pdf> [--json]

Output (text mode):
    Human-readable report with reading strategy recommendation.

Output (--json mode):
    JSON dict suitable for programmatic consumption.
"""

import sys
import os
import json
import subprocess
import re


def get_page_count(pdf_path):
    """Get page count using pdfinfo."""
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except Exception:
        pass
    # Fallback: use pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception:
        return None


def get_file_size_mb(pdf_path):
    return os.path.getsize(pdf_path) / (1024 * 1024)


def get_metadata(pdf_path):
    """Extract basic metadata via pdfinfo."""
    meta = {}
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
    except Exception:
        pass
    return meta


def extract_sample_text(pdf_path, first_n=3):
    """Extract text from first few pages to assess content type."""
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", str(first_n), pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception:
        return ""


def detect_toc(text):
    """Heuristic: detect if text contains a table of contents."""
    toc_patterns = [
        r'(?i)table\s+of\s+contents',
        r'(?i)contents\s*\n',
        r'(?i)目\s*录',
        r'\.{3,}\s*\d+',
    ]
    for pat in toc_patterns:
        if re.search(pat, text):
            return True
    return False


def assess_content_density(pdf_path, page_count):
    """
    Sample a few pages to estimate chars-per-page.
    Returns (avg_chars_per_page, is_likely_scanned, content_type).
    """
    sample_pages = min(5, page_count)
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", str(sample_pages), pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        text = result.stdout
    except Exception:
        return 0, True, "unknown"

    total_chars = len(text.strip())
    avg_chars = total_chars / sample_pages if sample_pages > 0 else 0

    if avg_chars < 50:
        return avg_chars, True, "scanned/image-heavy"
    elif avg_chars < 500:
        return avg_chars, False, "slides/sparse"
    elif avg_chars < 2000:
        return avg_chars, False, "mixed"
    else:
        return avg_chars, False, "text-dense"


def detect_chapter_structure(pdf_path, page_count):
    """Try to detect chapter/section headings from text."""
    chapters = []
    try:
        limit = min(20, page_count)
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", str(limit), pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        text = result.stdout

        patterns = [
            r'^(Chapter\s+\d+[.:]\s*.+)$',
            r'^(CHAPTER\s+\d+[.:]\s*.+)$',
            r'^(\d+\.\s+[A-Z].{5,60})$',
            r'^(\d+\s+[A-Z][A-Za-z\s]{5,60})$',
            r'^(第[一二三四五六七八九十\d]+[章节部分].*)$',
            r'^(Abstract|Introduction|Conclusion|References|Bibliography|Acknowledgments)\s*$',
        ]
        for line in text.splitlines():
            line = line.strip()
            for pat in patterns:
                if re.match(pat, line):
                    chapters.append(line[:80])
                    break
    except Exception:
        pass
    return chapters[:20]


def recommend_strategy(page_count, avg_chars, is_scanned, content_type, has_toc):
    """Generate a reading strategy recommendation."""
    est_total_chars = avg_chars * page_count
    est_tokens = int(est_total_chars / 3)

    strategy = {
        "method": "",
        "reasoning": "",
        "steps": [],
        "estimated_total_tokens": est_tokens,
    }

    if is_scanned:
        strategy["method"] = "ocr"
        strategy["reasoning"] = "PDF appears to be scanned/image-based. pdftotext produces empty/garbled output."
        strategy["steps"] = [
            "Use OCR (pytesseract + pdf2image) to extract text in small batches (5-10 pages)",
            "If OCR quality is poor, fall back to reading pages as images (limit to 10 pages per batch)",
        ]
    elif page_count <= 10:
        strategy["method"] = "direct_read"
        strategy["reasoning"] = f"Small PDF ({page_count} pages). Safe to read directly."
        strategy["steps"] = [
            "Read PDF directly with the Read tool",
        ]
    elif page_count <= 50 and est_tokens < 30000:
        strategy["method"] = "pdftotext_full"
        strategy["reasoning"] = f"Medium PDF ({page_count} pages, ~{est_tokens:,} tokens). Full text extraction fits in context."
        strategy["steps"] = [
            "Extract full text: pdftotext <file.pdf> <file.txt>",
            "Read the .txt file",
        ]
    elif content_type == "slides/sparse" and est_tokens < 50000:
        strategy["method"] = "pdftotext_full"
        strategy["reasoning"] = f"Sparse/slide PDF ({page_count} pages, ~{est_tokens:,} tokens). Full extraction manageable."
        strategy["steps"] = [
            "Extract full text: pdftotext <file.pdf> <file.txt>",
            "Read the .txt file (may need chunked reading if over 40k tokens)",
        ]
    else:
        strategy["method"] = "chunked_smart_read"
        strategy["reasoning"] = f"Large/dense PDF ({page_count} pages, ~{est_tokens:,} est. tokens). Must read in chunks."
        strategy["steps"] = [
            "Extract overview (first 3-5 pages): pdftotext -f 1 -l 5 <file.pdf> overview.txt",
            "Read overview.txt to understand document structure",
            "Extract specific sections by page range as needed: pdftotext -f <start> -l <end> <file.pdf> section.txt",
        ]
        if has_toc:
            strategy["steps"].insert(1, "TOC detected — parse it to build a page-range index for each chapter/section")
        strategy["steps"].append(
            "For full coverage: python smart_read.py <file.pdf> --output-dir <dir> to auto-generate per-chapter summaries"
        )

    return strategy


def probe(pdf_path, as_json=False):
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    page_count = get_page_count(pdf_path)
    if page_count is None:
        print("Error: Could not determine page count.", file=sys.stderr)
        sys.exit(1)

    file_size_mb = get_file_size_mb(pdf_path)
    metadata = get_metadata(pdf_path)
    sample_text = extract_sample_text(pdf_path)
    has_toc = detect_toc(sample_text)
    avg_chars, is_scanned, content_type = assess_content_density(pdf_path, page_count)
    chapters = detect_chapter_structure(pdf_path, page_count)
    strategy = recommend_strategy(page_count, avg_chars, is_scanned, content_type, has_toc)

    report = {
        "file": os.path.basename(pdf_path),
        "file_size_mb": round(file_size_mb, 2),
        "page_count": page_count,
        "title": metadata.get("Title", ""),
        "author": metadata.get("Author", ""),
        "content_type": content_type,
        "is_likely_scanned": is_scanned,
        "avg_chars_per_page": int(avg_chars),
        "has_toc": has_toc,
        "detected_sections": chapters,
        "strategy": strategy,
    }

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print(f"PDF PROBE REPORT: {report['file']}")
        print("=" * 60)
        print(f"  File size:       {report['file_size_mb']} MB")
        print(f"  Pages:           {report['page_count']}")
        print(f"  Title:           {report['title'] or '(none)'}")
        print(f"  Author:          {report['author'] or '(none)'}")
        print(f"  Content type:    {report['content_type']}")
        print(f"  Likely scanned:  {report['is_likely_scanned']}")
        print(f"  Avg chars/page:  {report['avg_chars_per_page']}")
        print(f"  Has TOC:         {report['has_toc']}")
        if chapters:
            print(f"  Detected sections ({len(chapters)}):")
            for ch in chapters:
                print(f"    - {ch}")
        print()
        print(f"RECOMMENDED STRATEGY: {strategy['method']}")
        print(f"  Reasoning: {strategy['reasoning']}")
        print(f"  Est. total tokens: ~{strategy['estimated_total_tokens']:,}")
        print("  Steps:")
        for i, step in enumerate(strategy['steps'], 1):
            print(f"    {i}. {step}")
        print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.pdf> [--json]", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    as_json = "--json" in sys.argv
    probe(pdf_path, as_json)
