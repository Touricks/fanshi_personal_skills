---
name: ppt-generator
description: "AI-powered PPT image and video generation using Google Gemini (Nano Banana Pro). Generates high-quality 16:9 PPT slide images with gradient glass or vector illustration styles, optional AI transition videos via Kling AI, and interactive HTML viewers. Use when the user wants to create PPT slides from documents or text content."
---

# PPT Generator Pro (NanoBanana PPT Skills)

## Overview

Generate high-quality PPT slide images using Google Nano Banana Pro (Gemini 3 Pro Image Preview), with optional AI transition videos via Kling AI.

**Tool location**: `/Users/carrick/tools_devop/NanoBanana-PPT-Skills/`
**Python venv**: `/Users/carrick/tools_devop/NanoBanana-PPT-Skills/venv/`

## Available Styles

- `styles/gradient-glass.md` - Gradient frosted glass card style (tech/business)
- `styles/vector-illustration.md` - Vector illustration style (education/creative)

## Execution Workflow

### Phase 1: Collect User Input

1. **Document content**: Read from file path or accept direct text
2. **Style selection**: Ask user to choose from available styles
3. **Page count**: Ask user (5 / 5-10 / 10-15 / 20-25 pages)
4. **Resolution**: 2K (2752x1536, recommended) or 4K (5504x3072)
5. **Video**: If Kling AI keys are configured, ask if transition videos are wanted

### Phase 2: Content Planning

Analyze the document and create `slides_plan.json`:

```json
{
  "title": "Document Title",
  "total_slides": 5,
  "slides": [
    {
      "slide_number": 1,
      "page_type": "cover",
      "content": "Title\nSubtitle"
    },
    {
      "slide_number": 2,
      "page_type": "content",
      "content": "Key points\n- Point 1\n- Point 2"
    }
  ]
}
```

Page types: `cover`, `content`, `data`

Save this file to: `/Users/carrick/tools_devop/NanoBanana-PPT-Skills/slides_plan.json`

**Visual Continuity (Video Mode)**: If video transitions are requested, adjacent slides MUST share the same background style and color scheme. Kling AI's first-last frame feature requires similar images for smooth 5s transitions — large visual differences trigger hard camera cuts instead of smooth morphing. Use transition buffer pages between visually distinct sections if needed.

### Phase 3: Generate PPT Images

```bash
cd /Users/carrick/tools_devop/NanoBanana-PPT-Skills && source venv/bin/activate && python3 generate_ppt.py \
  --plan slides_plan.json \
  --style styles/gradient-glass.md \
  --resolution 2K
```

Parameters:
- `--plan`: Path to slides plan JSON
- `--style`: Path to style template
- `--resolution`: 2K or 4K
- `--output`: Custom output directory (default: outputs/TIMESTAMP)

### Phase 4: Generate Transition Prompts (Video Mode)

If video mode is selected, analyze generated PPT images and create `transition_prompts.json`. For each adjacent pair of slides:

1. **Classify**: Determine A-type (similar — same style/layout) or B-type (different — e.g. cover→content)
2. **A-type strategy**: "In-place evolution" — changes happen on subjects/environment, minimal camera movement. Prioritize: background gradient flow, 3D object rotation/morphing, card content fade in/out, lighting shifts
3. **B-type strategy**: "Camera-driven transition" — use explicit camera movement (push/pull/pan/rotate) as a bridge between different scenes

**Kling AI first-last frame prompt rules:**
- Follow formula: `subject + motion, background + motion`
- Keep prompts simple and concrete — describe what we SEE, not what we FEEL
- All motion must be achievable within 5 seconds
- Motion must follow physics — avoid complex physics (bouncing, throwing)
- **MUST** end every prompt with text handling declaration (e.g. "text content transitions via fade, remaining clear and stable")
- Avoid descriptions like "text changes/moves/rotates" — video models blur text

Refer to the full transition template at `/Users/carrick/tools_devop/NanoBanana-PPT-Skills/prompts/transition_template.md` for detailed creative framework.

Save prompts to the output directory as `transition_prompts.json`.

### Phase 5: Generate Transition Videos (Video Mode)

```bash
cd /Users/carrick/tools_devop/NanoBanana-PPT-Skills && source venv/bin/activate && python3 generate_ppt_video.py \
  --slides-dir outputs/TIMESTAMP/images \
  --output-dir outputs/TIMESTAMP_video \
  --prompts-file outputs/TIMESTAMP/transition_prompts.json
```

### Phase 6: Return Results

After generation, tell the user:
- Output directory location
- How to open the HTML viewer: `open outputs/TIMESTAMP/index.html`
- Keyboard shortcuts: Arrow keys to navigate, Space for auto-play, ESC for fullscreen

## Content Planning Guidelines

**5 pages**: Cover + 3 key points + Summary
**5-10 pages**: Cover + Introduction + 3-4 key points + Cases/Data + Summary
**10-15 pages**: Cover + TOC + 3 chapters (3 pages each) + Data visualization + Summary
**20-25 pages**: Cover + TOC + Introduction + 3 parts (4 pages each) + Case studies + Analysis + Summary

## Kling AI Video Configuration

- Model: `kling-v2-6`
- Core feature: First-last frame (image-to-video) — upload start+end frame, generates transition
- Mode: `pro` (high quality, 35 inspiration/5s) — **first-last frame REQUIRES `pro` mode** (`std` returns error 1201)
- Duration: `5` seconds (recommended for PPT) or `10` seconds (×2 cost)
- Aspect ratio: 16:9 (matches PPT images)
- Prompt formula: `subject + motion, background + motion`

**Inspiration cost estimate:**
- 10-page PPT (9 transitions + 1 preview): 350 inspiration points (pro only)
- Error `1102 Account balance not enough`: Top up at https://klingai.kuaishou.com/

## Performance

- Image generation: ~30s/page (2K), ~60s/page (4K)
- Transition video: ~30-60s/segment
- Image size: ~2.5MB/page (2K), ~8MB/page (4K)
