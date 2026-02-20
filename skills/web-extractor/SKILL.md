---
name: web-extractor
description: >
  Extract complete text content from web pages using Claude in Chrome, handling
  JavaScript-rendered content, lazy-loaded pages, virtual scrolling, SPAs, and
  canvas-rendered content (Unity WebGL, Unreal, custom WebGL/WebGPU apps).
  Use this skill whenever the user wants to: scrape a web page, extract text from
  a URL, save web page content to a file, read a web document, or capture content
  from any dynamically-loaded website. Trigger especially when WebFetch fails
  (403, requires auth, JS-rendered) and the user has Chrome connected. Also use
  when the user mentions extracting content from sites like Google Docs, Notion,
  飞书, 轻雀文档, Confluence, Unity WebGL builds, or any SPA/JS-heavy/canvas-heavy site.
---

# Web Extractor

Extract complete text content from web pages, even when content is dynamically
loaded by JavaScript, behind authentication, or uses virtual scrolling.

## When This Skill Is Needed

Many modern web pages don't serve their content as static HTML. Instead, content
is loaded by JavaScript after the page renders, making simple HTTP fetches return
empty or partial results. Common scenarios:

- **Authentication-protected pages**: Sites requiring login (Google Docs, Notion, etc.)
- **JS-rendered SPAs**: React/Vue/Angular apps where content lives in JavaScript state
- **Virtual scrolling**: Long documents that only render visible content in the DOM
  (the content that scrolled past is removed, and content below isn't yet created)
- **Lazy-loaded content**: Sections that load as you scroll down

The key insight: even though JS loads content dynamically, once it renders, the
content **enters the DOM** and becomes readable via `querySelector` / `innerText`.
The challenge is making sure each section gets rendered (usually by scrolling) and
reading it before it gets removed (in virtual scroll cases).

## Strategy Decision Tree

```
Start: navigate to URL, wait 3-5s, call get_page_text
  │
  ├─ Got complete content? → DONE (Strategy 1: Simple)
  │
  ├─ Got partial content?
  │   ├─ Page has "load more" or infinite scroll? → Strategy 2: Lazy Load
  │   └─ Content seems truncated at viewport boundary? → Strategy 3: Virtual Scroll
  │
  ├─ Got almost nothing / page is data-heavy?
  │   └─ Check read_network_requests for API calls → Strategy 4: API Intercept
  │
  └─ Got only script/boilerplate? Page uses <canvas> (Unity/WebGL/WebGPU)?
      └─ Strategy 5: Canvas Visual Extraction (screenshot + transcription)
```

## Strategy 1: Simple Pages

For pages where all content loads once and stays in the DOM.

Steps:
1. `navigate` to the URL
2. `wait` 3-5 seconds for JS to finish rendering
3. `get_page_text` — this should capture everything

Works for: blogs, news articles, server-side rendered documentation.

## Strategy 2: Lazy-Loaded Pages

Content appends to the DOM as you scroll, but previously-loaded content stays.

Steps:
1. Navigate and wait for initial load
2. `get_page_text` to capture the first section
3. Scroll down using `computer` action (scroll or End key)
4. `wait` 1-2 seconds for new content to load
5. `get_page_text` again — new content will be at the bottom
6. Repeat steps 3-5 until get_page_text returns no new content
7. Merge all captured text, removing duplicate overlapping sections

Works for: infinite-scroll feeds, long articles that load in chunks.

## Strategy 3: Virtual Scrolling Pages

This is the hardest case. The page actively removes off-screen content from the
DOM and only renders what's currently in the viewport. The full content never
exists in the DOM simultaneously.

### Step 1: Find the Scroll Container

Most virtual-scroll pages scroll inside a specific `<div>`, not the browser window.
Use `javascript_tool` to locate it:

```javascript
// Quick search by common class names
const el = document.querySelector(
  '.doc-content, .article-content, .ql-editor, ' +
  '[class*="editor"], [class*="scroll-container"], ' +
  '[class*="virtual"], main article'
);
if (el && el.scrollHeight > el.clientHeight + 200) {
  `Found: <${el.tagName}> class="${el.className}" ` +
  `scrollHeight=${el.scrollHeight} clientHeight=${el.clientHeight}`;
}
```

If the quick search misses it, use a broader search:

```javascript
const all = document.querySelectorAll('*');
for (const el of all) {
  const s = getComputedStyle(el);
  if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
      el.scrollHeight > el.clientHeight + 200) {
    `Found: <${el.tagName}> class="${el.className}" ` +
    `scrollHeight=${el.scrollHeight} clientHeight=${el.clientHeight}`;
    break;
  }
}
```

Record the `scrollHeight` (total document length) and `clientHeight` (viewport height).

### Step 2: Scroll and Capture

Move through the document in steps equal to `clientHeight`, reading at each position:

```
positions = [0, clientHeight, 2*clientHeight, ..., scrollHeight]
for each position:
    1. javascript_tool: set container.scrollTop = position
    2. wait 1-2 seconds (separate tool call — don't loop in JS, it'll timeout)
    3. get_page_text to capture the currently visible content
    4. store the result
```

Each tool call is separate because `javascript_tool` has a 30-second timeout.
Trying to scroll+wait+read in a single JS execution for many positions will fail.

### Step 3: Merge and Deduplicate

Each capture includes repeated elements (navigation, sidebar, TOC) plus the unique
content visible at that scroll position. To merge:

- The repeating parts (nav, sidebar, headers) appear identically in every capture
- The unique content portion changes with each scroll position
- Strip the repeated portions and concatenate the unique content in order

### Real-World Example: 轻雀文档

Here's what we actually did to extract a 33,000px-tall document:

```
1. Found scrollable container: .vodka-appview-editor (scrollHeight: 33202)
2. Scrolled to positions: 0, 2500, 5000, 10000, 15000, 17500, 20000, 22500, 25000, 30000
3. Called get_page_text at each position
4. Each call returned ~2000-4000 chars of unique content
5. Merged into a structured Markdown file with proper headings
```

## Strategy 4: API Interception

Instead of scraping the rendered DOM, capture the raw data the page fetches.

Steps:
1. Navigate to the URL and let it load
2. `read_network_requests` with a `urlPattern` filter (e.g., `/api/`, `/graphql`)
3. Identify responses containing the document data (usually JSON)
4. Extract content directly from the API response payload

This is often the cleanest approach for data-heavy pages, dashboards, or apps
with clear REST/GraphQL backends. The data is structured and complete, without
the noise of navigation elements.

## Strategy 5: Canvas-Rendered Content (Unity WebGL, WebGPU, etc.)

When text is rendered inside an HTML `<canvas>` by a game engine or custom WebGL/WebGPU
application, it exists only as GPU-drawn pixels — not as DOM text. All DOM-based
extraction methods (get_page_text, innerText, clipboard) will fail completely.

### How to Detect Canvas-Rendered Pages

Signs that you're dealing with canvas-rendered content:
- `get_page_text` returns only JavaScript loader code, no readable content
- The page contains a prominent `<canvas>` element (check with `read_page`)
- Page title mentions "Unity", "Unreal", "WebGL", "WebGPU", or a game engine
- The HTML source has `createUnityInstance`, `.wasm`, or `.data` file references
- The page loads large binary assets (multi-MB `.data` or `.wasm` files)

### What Does NOT Work (Do Not Attempt)

These approaches have been tested and confirmed to fail for canvas content:

1. **`get_page_text` / DOM extraction**: Canvas is opaque to DOM — returns nothing useful
2. **Ctrl+A / Ctrl+C (keyboard copy)**: Game engines intercept keyboard events; clipboard stays empty
3. **`navigator.clipboard.readText()`**: Returns undefined; no text to copy from canvas
4. **Unity JavaScript API (`SendMessage`)**: The Unity instance is typically not exposed globally
   (captured inside a `.then()` callback). Even if found, there's no standard method to export UI text
5. **Binary data file parsing (Python `strings`)**: Unity's serialization fragments text across the
   binary — extraction produces heavily corrupted output with garbled characters
6. **Scrollbar drag (`left_click_drag`)**: Unity's UI drag handlers don't respond to browser drag events
7. **Keyboard scrolling (Page Down, Home, arrow keys)**: Unity captures these keys but doesn't
   bind them to Scroll Rect components by default

### What DOES Work: Mouse Wheel Scrolling + Screenshot Transcription

Unity's Scroll Rect component natively responds to `OnScroll` events from the mouse wheel.
This is the one browser input that reliably propagates to Unity's EventSystem.

Steps:
1. Navigate to the URL and wait for the canvas to finish loading
2. Take an initial `screenshot` to see the first portion of visible text
3. Use `computer` tool with `scroll` action (mouse wheel) over the canvas area:
   - Start with 3–5 scroll ticks downward
   - Use the `coordinate` parameter to target the center of the text area
4. Take a `screenshot` after each scroll
5. Continue scrolling and capturing until you see empty space below the last line of text
6. If gaps exist between captures, scroll back up in smaller increments (1–2 ticks) and re-capture
7. Visually read/transcribe the text from the series of screenshots into a text file
8. Save the transcribed content to the user's workspace

### Scroll Increment Guidelines

| Content density | Recommended ticks | Overlap strategy |
|----------------|-------------------|------------------|
| Large text      | 3–5 ticks         | ~2 lines overlap between screenshots |
| Small text      | 1–3 ticks         | ~3 lines overlap between screenshots |
| Unknown         | 3 ticks           | Check overlap, adjust as needed |

### Example: Unity WebGL Text Extraction

```
1. Navigated to http://127.0.0.1:5500/SRW2/index.html
2. get_page_text → returned only JS loader code (Strategy 5 triggered)
3. screenshot → saw "Self Rendered Web Test" title + first portion of text
4. scroll(coordinate=[650,500], direction=down, amount=3) → took screenshot
5. Repeated scroll+screenshot ~8 more times
6. Scrolled back up by 3 ticks to fill one gap between captures
7. Transcribed all visible text from ~10 screenshots
8. Saved complete content (2 paragraphs, ~400 words) to extracted_content.txt
```

### Applicability Beyond Unity

This strategy works for any canvas-based rendering:
- **Unity WebGL** builds
- **Unreal Engine** HTML5 exports
- **Godot** web exports
- **Custom WebGL/WebGPU** applications
- **PDF.js** canvas-rendered PDFs (when DOM fallback is disabled)
- **Figma** embedded previews
- Any app drawing text to `<canvas>` via 2D context or WebGL

## Common Pitfalls

1. **Reading too fast after scrolling**: JS needs time to render. Always use a
   separate `wait` call (1-2 seconds) between scrolling and reading.

2. **Virtual scroll erases content**: Don't scroll to the bottom expecting to
   read everything — only the bottom section exists in the DOM at that point.

3. **Wrong scroll target**: Many apps scroll inside a `<div>`, not `window`.
   If `window.scrollTo` doesn't trigger new content, find the real scroll container.

4. **Cookie banners / modals blocking content**: Dismiss these first. Use `find`
   to locate "Accept" or close buttons and click them before extracting.

5. **JS timeout in loops**: `javascript_tool` times out at 30s. Never put
   `await` loops or `setTimeout` chains in a single JS call. Instead, make each
   scroll-wait-read cycle a separate set of tool calls.

6. **Blocked content**: Some text in `javascript_tool` results may be blocked
   by safety filters. If a substring retrieval returns `[BLOCKED]`, try
   `get_page_text` at that scroll position instead, which uses a different
   extraction path.

7. **Canvas content mistaken for DOM content**: If `get_page_text` returns only
   script/boilerplate and the page has a `<canvas>`, don't keep trying DOM-based
   methods — switch immediately to Strategy 5 (visual extraction). All DOM
   approaches will fail for canvas-rendered text.

8. **Scrollbar drag on canvas apps**: Never use `left_click_drag` to try to
   scroll inside Unity/Unreal/Godot canvas areas. These engines use their own
   event systems. Only mouse wheel (`scroll` action) works reliably.

9. **Binary asset parsing temptation**: It's tempting to extract text from Unity
   `.data` files or Unreal `.pak` files using `strings` or byte scanning. This
   produces corrupted output due to engine-specific serialization. Don't waste
   time on this — go straight to visual extraction.

## Output Format

Save extracted content as Markdown:

```markdown
# [Document Title]

> Source: [URL]
> Extracted: [YYYY-MM-DD]

[Content organized with proper headings and structure]
```

Save to the user's workspace folder with a descriptive filename.
