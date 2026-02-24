#!/usr/bin/env python3
"""
smart_read.py - Chunked PDF text extraction with per-chunk summaries.

Splits a PDF into page-range chunks, extracts text for each chunk,
and produces an index file that maps chunk IDs to page ranges and
character counts. This allows Claude to read the index first (~small),
then selectively read only the chunks it needs.

Usage:
    python smart_read.py <input.pdf> --output-dir <dir> [--chunk-size 15] [--layout]

Output structure in <dir>/:
    index.json          - Chunk manifest with page ranges and stats
    chunk_001.txt       - Text for pages 1-15
    chunk_002.txt       - Text for pages 16-30
    ...

The index.json format:
{
  "source": "filename.pdf",
  "total_pages": 120,
  "total_chars": 245000,
  "chunk_size": 15,
  "chunks": [
    {
      "id": "chunk_001",
      "pages": "1-15",
      "start_page": 1,
      "end_page": 15,
      "chars": 18234,
      "first_line": "Chapter 1: Introduction ...",
      "file": "chunk_001.txt"
    },
    ...
  ]
}
"""

import sys
import os
import json
import subprocess
import argparse


def get_page_count(pdf_path):
    """Get page count."""
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
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return None


def extract_text_range(pdf_path, start_page, end_page, layout=False):
    """Extract text for a page range using pdftotext."""
    cmd = ["pdftotext"]
    if layout:
        cmd.append("-layout")
    cmd.extend(["-f", str(start_page), "-l", str(end_page), pdf_path, "-"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout
    except Exception as e:
        return f"[Error extracting pages {start_page}-{end_page}: {e}]"


def get_first_meaningful_line(text, max_len=100):
    """Get the first non-empty line as a preview."""
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) > 5:
            return stripped[:max_len]
    return "(empty or whitespace only)"


def smart_read(pdf_path, output_dir, chunk_size=15, layout=False):
    page_count = get_page_count(pdf_path)
    if page_count is None:
        print("Error: Could not determine page count.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    chunks = []
    total_chars = 0
    chunk_num = 0

    for start in range(1, page_count + 1, chunk_size):
        end = min(start + chunk_size - 1, page_count)
        chunk_num += 1
        chunk_id = f"chunk_{chunk_num:03d}"
        chunk_file = f"{chunk_id}.txt"
        chunk_path = os.path.join(output_dir, chunk_file)

        text = extract_text_range(pdf_path, start, end, layout)

        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(text)

        char_count = len(text.strip())
        total_chars += char_count

        chunks.append({
            "id": chunk_id,
            "pages": f"{start}-{end}",
            "start_page": start,
            "end_page": end,
            "chars": char_count,
            "est_tokens": int(char_count / 3),
            "first_line": get_first_meaningful_line(text),
            "file": chunk_file,
        })

        print(f"  {chunk_id}: pages {start}-{end}, {char_count:,} chars, ~{int(char_count/3):,} tokens")

    index = {
        "source": os.path.basename(pdf_path),
        "total_pages": page_count,
        "total_chars": total_chars,
        "total_est_tokens": int(total_chars / 3),
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "chunks": chunks,
    }

    index_path = os.path.join(output_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(chunks)} chunks written to {output_dir}/")
    print(f"Total: {total_chars:,} chars, ~{int(total_chars/3):,} est. tokens")
    print(f"Index: {index_path}")

    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart chunked PDF text extraction")
    parser.add_argument("pdf_path", help="Path to the input PDF")
    parser.add_argument("--output-dir", required=True, help="Output directory for chunks and index")
    parser.add_argument("--chunk-size", type=int, default=15, help="Pages per chunk (default: 15)")
    parser.add_argument("--layout", action="store_true", help="Preserve layout with pdftotext -layout")

    args = parser.parse_args()
    smart_read(args.pdf_path, args.output_dir, args.chunk_size, args.layout)
