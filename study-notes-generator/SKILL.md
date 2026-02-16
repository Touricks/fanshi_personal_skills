---
name: study-notes-generator
description: Transform documents into interactive HTML study notes with key concepts, problem-solution pairs, examples, and self-quiz questions. Use when asked to create study notes, summarize lecture slides, or generate learning materials from documents in slides/ folder. Output goes to notes/ folder.
---

# Study Notes Generator

Transform documents from `slides/` into feature-rich HTML study notes saved to `notes/`.

## Workflow

1. **Read the source document** from `slides/` (see PDF Handling below for large files)
2. **Extract and organize content** into learning-focused sections
3. **Generate HTML** using the template structure from `assets/template.html`
4. **Save** to `notes/` with filename `{original-name}-notes.html`

## PDF Handling (CRITICAL)

The Claude API has a hard limit of **100 images/documents per conversation**. PDF pages are converted to images when read, so any PDF over ~90 pages will fail.

### For PDFs over 50 pages:
1. **Always extract text first** using `pdftotext`:
   ```bash
   /opt/homebrew/bin/pdftotext "slides/filename.pdf" "slides/filename.txt"
   ```
2. Generate notes from the `.txt` file only
3. **Do NOT read the PDF file directly** — only read the extracted `.txt`

### For PDFs under 50 pages:
- Read the PDF directly with the Read tool (using `pages` parameter for 10+ pages)

## Parallel Processing (Multiple Documents)

When processing multiple documents at once:

1. **Validate with one agent first**: Spawn 1 background Task agent, wait for it to succeed, then spawn the rest. This avoids wasting tokens on a batch of agents that all fail the same way.

2. **Use `Task` tool with `run_in_background: true`** for independent per-file agents. Do NOT use TeamCreate — team agents require message-driven coordination and will idle without producing output when tasks are independent.

3. **Batch size**: Spawn at most **4 agents in parallel** to avoid rate limits. If more files remain, wait for the first batch to complete before launching the next.

4. **Strong negative constraints in agent prompts**: When instructing agents, use explicit prohibitions:
   - GOOD: "Do NOT read any PDF files. ONLY read the .txt file."
   - BAD: "Prefer reading the text file over the PDF."
   Agents ignore weak preferences but obey strong negations.

## Content Extraction Guidelines

When analyzing the document, identify and extract:

### Key Concepts & Definitions
- Core terminology and their meanings
- Fundamental principles being taught
- Mark with `<div class="concept"><strong>Term</strong>Definition...</div>`

### Problem-Solution Pairs
- What problem/challenge does each concept address?
- How does the method/technique solve it?
- Mark with:
```html
<div class="problem-solution">
  <div class="problem">Problem: What challenge exists?</div>
  <div class="solution">Solution: How this concept/method addresses it</div>
</div>
```

### Examples & Applications
- Concrete examples from the document
- Real-world applications mentioned
- Mark with `<div class="example">...</div>`

### Important Notes
- Warnings, common mistakes, or critical points
- Mark with `<div class="important">...</div>`

## CRITICAL: Mandatory Examples Rule

**For ANY content that is NOT a pure definition, you MUST provide at least one concrete example.**

### What requires examples:

| Content Type | Example Required? | Reason |
|--------------|-------------------|--------|
| Pure definition (e.g., "X is defined as Y") | Optional | Definition is self-contained |
| Properties/Characteristics | **YES** | Need to show how property manifests |
| Theorems/Claims | **YES** | Need to illustrate what theorem means |
| Comparisons (X vs Y) | **YES** | Need concrete case showing difference |
| Security properties | **YES** | Need attack scenario or counterexample |
| Algorithms/Procedures | **YES** | Need step-by-step walkthrough |
| "Why" questions | **YES** | Need counterexample or motivation case |

### Example format:

```html
<div class="concept">
    <strong>Collision Resistance (抗碰撞性)</strong>
    Nobody can find x and y such that x ≠ y and H(x) = H(y).
</div>

<div class="example">
    <strong>Why this matters:</strong> Consider H(x) = last 4 bits of x.
    <br>Finding collision is trivial: H("00001010") = H("11111010") = "1010"
    <br>This H is NOT collision resistant - bad for security!
</div>
```

### Counterexample pattern for "Why not X?" questions:

When explaining why a definition/property is formulated a certain way, ALWAYS provide a counterexample showing what goes wrong with the alternative:

```html
<div class="problem-solution">
    <div class="problem">Why require H(x₁)=Y rather than x₁=x in one-wayness?</div>
    <div class="solution">
        <strong>Counterexample:</strong> Let H(x) = LSB(x) (last n bits).
        <ul>
            <li>Given Y, can you find the original x? NO (2^n possibilities)</li>
            <li>Given Y, can you find ANY x' with H(x')=Y? YES, trivially!</li>
        </ul>
        If we used x₁=x, this insecure function would be called "one-way"!
    </div>
</div>
```

## HTML Structure

Generate HTML following this structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Document Title} - Study Notes</title>
    <!-- Copy full <style> block from assets/template.html -->
</head>
<body>
    <h1>{Document Title}</h1>

    <nav class="toc">
        <h2>Table of Contents</h2>
        <ul>
            <li><a href="#section-1">Section 1 Title</a></li>
            <!-- ... more sections -->
        </ul>
    </nav>

    <section id="section-1">
        <h2>Section 1 Title</h2>
        <!-- Content with concepts, problem-solutions, examples -->
    </section>

    <!-- More sections -->

    <!-- End with summary and quiz -->
    <div class="summary">
        <h3>Key Takeaways</h3>
        <ul>
            <li>Main point 1</li>
            <li>Main point 2</li>
        </ul>
    </div>

    <section>
        <h2>Self-Check Quiz</h2>
        <!-- Quiz questions -->
    </section>
</body>
</html>
```

## Collapsible Sections

Use `<details>` for content that benefits from progressive disclosure:

```html
<details>
    <summary>Detailed Explanation of X</summary>
    <div>
        Extended content here...
    </div>
</details>
```

## Self-Quiz Questions

End each major topic or the document with quiz questions:

```html
<div class="quiz">
    <div class="quiz-question">What is the main purpose of X?</div>
    <details>
        <summary>Show Answer</summary>
        <div>The answer explanation here...</div>
    </details>
</div>
```

Generate 3-5 quiz questions per major section covering:
- Definitions (What is...?)
- Application (When would you use...?)
- Comparison (How does X differ from Y?)
- Problem-solving (Given scenario Z, what approach...?)

**Quiz answers should also include examples** when explaining non-trivial concepts.

## Output Checklist

Before saving, verify the notes include:
- [ ] Clear title and table of contents
- [ ] All major topics from source document
- [ ] Key concepts highlighted with definitions
- [ ] **Concrete examples for ALL non-definition content** (MANDATORY)
- [ ] Problem-solution pairs explaining the "why"
- [ ] Counterexamples for "why not X?" type questions
- [ ] Collapsible sections for detailed content
- [ ] Summary of key takeaways
- [ ] Self-quiz questions with hidden answers (including examples in answers)

## Resources

### assets/
- `template.html` - Full HTML template with CSS styles. Copy the `<style>` block into generated notes.
