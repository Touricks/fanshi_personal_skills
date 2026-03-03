---
name: prompt-criteria
description: 8-module prompt framework distilled from the GLM-5 training report
---

### 1. Persona and Audience Definition

- **Shared logic**: Prevent the AI from staying in an amorphous "general assistant" state. Instead, define a specific professional identity and target audience to lock in the right terminology and tone.

- **Prompt 1 example**: Senior Wall Street analyst + Python expert.

- **Prompt 2 example**: Target audience is institutional / semi-professional investors.


### 2. Core Objective and Deliverable

- **Shared logic**: Define "what to do" and "what format the final output should be" in a single clear sentence, eliminating any ambiguity.

- **Prompt 1 example**: Generate an error-free Python script that produces an `.xlsx` file.

- **Prompt 2 example**: Write a professional research report in a text format suitable for direct PDF rendering.


### 3. Data Grounding and External Inputs

- **Shared logic**: Strictly limit AI hallucination by requiring all output to be anchored to given external facts or tools.

- **Prompt 1 example**: Hard-bind to the uploaded `GOOG-10-K-2025.pdf`.

- **Prompt 2 example**: Hard-bind to uploaded trend chart images and require web search to obtain real-time accurate stock prices.


### 4. Information Density and Writing Constraints

- **Shared logic**: Strongly reject AI-generated filler and verbosity. Enforce high data density and de-emotionalized, objective expression.

- **Prompt 1 example**: No more than 20 words per line; use data instead of text wherever possible; mandatory bullet points.

- **Prompt 2 example**: Distinguish facts from assumptions; ban marketing language; require fully traceable logic.


### 5. Visual and Design System

- **Shared logic**: Control not just content but also visual presentation -- embed designer-level UI/UX specifications directly into the prompt.

- **Both prompts overlap heavily**: Both specify investment-bank-style color schemes (navy primary + gold accent), alternating row background colors, and even pixel-level requirements for font types (Calibri, etc.) and layout prohibitions (no red-green dual colors, no merging large cells).


### 6. Modular Micro-Structure

- **Shared logic**: Refuse to let the AI freestyle the document structure. Instead, plan the exact content composition for each section or sheet, like a fill-in-the-blank exercise.

- **Prompt 1 example**: Precisely specifies contents for Sheet 1 through Sheet 4 (e.g., Sheet 3 must contain CapEx table + AI two-column short-sentence table).

- **Prompt 2 example**: Precisely specifies which chart or matrix must accompany each of the 5 sections ("Executive Summary", "Industry Competition", etc.).


### 7. Medium-Specific Technical Rules

- **Shared logic**: Provide low-level technical constraints tailored to the final delivery medium (Excel software or PDF renderer) to ensure the output is not only viewable but also usable.

- **Prompt 1 example**: Code must include auto-fit column widths, single-page print area setup, and thousand-separator formatting.

- **Prompt 2 example**: No mid-sentence line breaks, limit complex Unicode symbols, left-align bullet points.


### 8. Top-Tier Quality Bar

- **Shared logic**: Set an extremely high real-world benchmark in the prompt, leveraging the LLM's alignment properties to force it to draw from its highest-quality training corpus.

- **Prompt 1 example**: "Meet Goldman Sachs / Morgan Stanley tier investment bank delivery standards", "visually stunning".

- **Prompt 2 example**: "Meet institutional-grade investment research delivery standards", "usable without post-editing".
