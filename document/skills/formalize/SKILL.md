---
name: formalize
version: 1.0.0
description: "Transform a rough, multilingual, or internally-annotated draft document into a polished, submission-ready version. Use when the user says \"clean up\", \"polish\", \"make it ready for submission\", or asks to remove a specific language, icons, or internal annotations from a document."
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Draft-to-Clean Document Transformation

## Overview

Transform a rough, multilingual, or internally-annotated draft document into a polished, submission-ready version. This skill covers the full pipeline from reading the source to producing a clean output, including what to strip, what to normalize, and what to preserve.

## When to Use

- User says "clean up", "polish", "make it ready for [professor / reviewer / submission]"
- User asks to remove a specific language, icons, or internal annotations
- User wants to convert an internal working document into an external-facing draft
- User asks for a "final version" or "clean version" of an existing document

## Process

### Phase 1: Audit the Source

Before making any changes, read the full document end-to-end and build an inventory of what needs to change. Do not start editing mid-read.

**Identify these categories:**

| Category | What to Look For | Example |
|----------|-----------------|---------|
| Emoji / Icons | Any Unicode emoji used as visual markers | Checkmarks, crosses, colored circles, warning signs, chart icons |
| Non-target language | Sections, headings, or inline parentheticals in a language the user wants removed | Full Chinese parallel section, inline "(数据锚定型幻觉)" after English terms |
| Unicode decoration | Box-drawing characters, fancy arrows, special bullets | `┌─────┐`, `→`, `●` |
| Internal annotations | Comments, TODOs, editor notes, version markers | `> **Note to self:**`, `<!-- TODO -->`, `v2 draft` in title |
| Inconsistent formatting | Mixed conventions within the same document | Some tables use "Yes/No", others use checkmark/cross icons |

**Key rule: Do NOT audit selectively.** Skim every line. Icons and inline foreign-language fragments hide in places you don't expect — inside table cells, code block comments, bullet sub-items, blockquotes.

### Phase 2: Define the Transformation Spec

Before writing the output, lock down a concrete spec. This prevents mid-edit drift where early sections get one treatment and later sections get another.

**Spec template** (fill in based on user request):

```
Target language:    [e.g., English only]
Remove languages:   [e.g., Chinese sections, Chinese parentheticals]
Icon policy:        [e.g., replace all emoji with plain text equivalents]
Diagram policy:     [e.g., ASCII-only, no Unicode box-drawing]
Arrow style:        [e.g., --> for flow, "to" in prose]
Table cell policy:  [e.g., "Yes" / "No" instead of checkmarks/crosses]
Bullet style:       [e.g., Markdown hyphens, no custom Unicode bullets]
Content changes:    [e.g., NONE — structure and substance must be identical]
```

**Critical constraint: Content preservation.** Unless the user explicitly asks for content edits, the transformation is purely cosmetic. Every claim, every table row, every citation must survive intact. The output should diff against the input as substitution-only, never deletion of substantive content.

### Phase 3: Execute the Transformation

Work through the document **in section order**, applying the spec consistently. The specific operations, in priority order:

#### 3a. Remove non-target language blocks

- Delete entire parallel-language sections (e.g., a full "Chinese Version" after the English)
- Delete bilingual titles (keep target language only)
- Delete inline foreign-language parentheticals after terms: `Data-Grounded Hallucination (数据锚定型幻觉)` becomes `Data-Grounded Hallucination`

#### 3b. Replace emoji and icons

Common substitutions:

| Original | Replacement |
|----------|-------------|
| Colored circle emoji (green/red/orange/gray) used as legend markers | Bold color name in text: **Green**, **Red**, **Orange**, **Gray** |
| Checkmark / cross in table cells | "Yes" / "No" or "Only valid combination" / "Does not exist" (match the semantic meaning) |
| Warning / chart / prohibition emoji used as category markers | Remove entirely; the surrounding text already names the category |
| Bullet-point emoji (●, ▸, ◆) | Standard Markdown list syntax (`-` or `*`) |

**Do not** mechanically find-and-replace. Each emoji has context. A checkmark in a comparison table means "Yes / supported", but a checkmark in a task list means "done". Read the surrounding sentence.

#### 3c. Normalize diagrams and ASCII art

- Replace Unicode box-drawing (`┌ ─ ┐ │ └ ┘ ├ ┤`) with ASCII equivalents (`+ - | +`)
- Replace Unicode arrows (`→ ←`) with ASCII (`-->`, `<--`)
- Replace Unicode bullets in code blocks (`●`) with hyphens (`-`)
- Test that the diagram still reads correctly after substitution — alignment matters in monospace blocks

#### 3d. Strip internal annotations

- Remove `<!-- HTML comments -->` unless they serve a rendering purpose
- Remove `> **Note:**` blocks that are author-to-author, not author-to-reader
- Remove version markers from the title (e.g., "v2", "DRAFT")
- Remove any `TODO`, `FIXME`, `TBD` markers

#### 3e. Consistency pass

After all substitutions, scan the full document once more for:

- Mixed icon/text in the same table (e.g., one row says "Yes", another still has a checkmark)
- Orphaned references to removed content (e.g., "see the Chinese section below" when Chinese was deleted)
- Broken Markdown formatting from removal (e.g., empty table cells, dangling list items)
- Misaligned ASCII diagrams after character substitution

### Phase 4: Deliver

1. Write the clean file to `/mnt/user-data/outputs/`
2. Use `present_files` to share it
3. Provide a **brief change summary** listing what was removed/replaced — no more than 5-6 bullet points. The user needs to know what changed, not a paragraph-by-paragraph walkthrough.

**Change summary template:**

```
Changes from [source] to [output]:
- [Language] section removed — English only throughout
- All emoji/icons replaced with plain text (Yes/No in tables, color names in legends)
- [Language] parentheticals stripped from technical terms
- Unicode box-drawing replaced with ASCII in diagrams and mockups
- Arrow symbols standardized to --> in diagrams
- Content and structure unchanged
```

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Start editing before reading the full document | Read everything first, build the inventory |
| Apply different standards to early vs. late sections | Lock the spec before writing, apply uniformly |
| Delete substantive content during cleanup | Preserve every claim, citation, table row, and code block |
| Describe every change in exhaustive detail | Give a 5-6 item change summary |
| Guess what the user wants removed | If ambiguous, ask: "Should I keep the Chinese parentheticals after English terms, or strip those too?" |
| Produce partial output (e.g., "I've cleaned sections 1-4, shall I continue?") | Deliver the complete document in one pass |
| Leave the old file in place without explanation | Overwrite or clearly name the new file, explain what replaced what |

## Edge Cases

**User says "clean up" but doesn't specify what to remove.** Ask one focused question before starting. A good default question: "Should I keep this English-only, or preserve the bilingual format? And should I strip emoji/icons to plain text?" Two answers unlock the full spec.

**Document has emoji that carry semantic meaning not present in surrounding text.** For example, a colored circle is the *only* indicator of which category a row belongs to. In this case, add a text label rather than simply deleting. The goal is zero information loss.

**Diagrams break after ASCII substitution because alignment shifts.** Unicode box-drawing characters are typically full-width or have different glyph widths than ASCII. After substituting, visually inspect the diagram in a monospace context. Adjust spacing if needed.

**User later asks for the bilingual version back.** This is why we do not overwrite the source. If the source was a project file (read-only in `/mnt/project/`), it's already preserved. If the source was user-uploaded, confirm before replacing.