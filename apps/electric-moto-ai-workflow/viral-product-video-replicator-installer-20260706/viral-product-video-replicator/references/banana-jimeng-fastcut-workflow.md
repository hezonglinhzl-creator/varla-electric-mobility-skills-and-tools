# Banana to Jimeng Fast-Cut Workflow

Use this reference when the user wants Banana images first, then Jimeng videos, especially when Jimeng cannot accept long prompts.

## Recommended Deliverables

Create a folder containing:

- Cropped segment images with numbered time ranges.
- Matching `.txt` prompt files with the same prefix.
- A short overview `.md` mapping image -> prompt -> time range.

Example naming:

- `01_video1_00-04s_startline_pov.jpg`
- `01_video1_00-04s_startline_pov.txt`
- `02_video1_04-08s_flag_launch_tires.jpg`
- `02_video1_04-08s_flag_launch_tires.txt`

## Segment Sizing

If Jimeng has a 15 second clip limit:

- 20-25s output: split into 2 main clips or 5-6 micro-segments.
- 25s race ad: `00-04s`, `04-08s`, `08-13s`, `13-17s`, `17-21s`, `21-25s`.
- Each micro-segment prompt should stay under the user's text limit.
- If the user says the prompt input limit is 2K characters, write one `.txt` per image segment and keep each prompt compact. Add Chinese operator notes outside or before the prompt only if they do not push the text over the limit.

## Banana Storyboard Prompts

Banana prompts should generate reference images, not final video:

- For vertical short video, the Banana storyboard canvas must be `9:16`.
- If using 16 panels, prefer a `4x4 grid on a 9:16 vertical canvas`; each small panel should be a vertical 9:16 video frame, not a horizontal frame.
- If using 18 panels for easier cropping, prefer `6 columns x 3 rows on a 9:16 vertical canvas`; each row becomes one 6-shot Jimeng segment. This keeps the whole deliverable easy to split into three image prompts.
- If the user needs larger panel detail, use `3 columns x 6 rows` and crop rows `1-2`, `3-4`, `5-6`, but warn that each panel may look less vertical unless the prompt strongly says every panel is a vertical smartphone frame.
- Explicitly say: `each panel is a vertical 9:16 smartphone video frame`.
- Avoid `2 columns x many rows` when it makes each panel horizontal; this often changes the generated look away from the video reference.
- Use 2-row or 3-row segment grids for clarity.
- Do not put the whole story in one huge image if the user will crop it anyway.
- Avoid empty establishing panels unless the user explicitly wants a location shot.
- Every panel should show a rider, vehicle, hands, wheel, spectators reacting, or the key product result.
- Use negative controls for repeated failure modes: `no empty track`, `no blue ring`, `no duplicate riders`, `no bicycle`, `no pedals`.

## Direct GPT-Image Storyboard Prompts

When the user explicitly wants GPT-image or direct image generation instead of Banana prompts, keep the same storyboard logic but avoid language that makes the model create a design board.

Use:

- `photorealistic image collage`
- `18 separate vertical smartphone video stills`
- `6 columns x 3 rows`
- `thin black borders`
- `no text anywhere`
- `only realistic video stills`

Avoid:

- `storyboard plan`
- `template`
- `table`
- `chart`
- `infographic`
- `labels`
- `project title`
- `notes`
- `layout with sections`

If direct generation returns maps, posters, charts, education pages, UI, or unrelated objects, mark the attempt as failed and retry once with a shorter prompt that begins with:

```text
Only generate a realistic photo collage. No text. No poster. No infographic. No map. No UI.
```

Do not hand off the wrong image as a usable reference. The output image must visibly match the requested product-video story before producing Jimeng prompts.

## Jimeng Short Prompt Shape

Each short prompt should include:

1. Strong reference lock: `Strictly follow the uploaded Banana reference image. Use it as the main visual guide. Do not redesign the scene.`
2. Format and duration: `vertical 9:16`, realistic style, seconds.
3. One or two sentence action description.
4. Ordered sound design: one dominant sound per cut.
5. Dialogue or voiceover only when needed.
6. Compact negative prompt.

For Chinese users, include a short Chinese label before the prompt, e.g. `01_00-04s_起跑线POV`, but keep the prompt itself concise.

## Ordered Sound Design

Avoid messy audio. For each cut:

- `Main sound:` one prominent sound.
- `Light background:` optional, quiet.

Good examples:

- `Main sound: sharp flag flap. Light background: crowd low.`
- `Main sound: weak motor sputter. Light background: tire slowing on dirt.`
- `Dialogue main sound: White rider, native American male voice: "Where did you get that bike?" Light background: very soft outdoor ambience.`

Bad example:

- `crowd, motor, dirt, heartbeat, wind, voiceover, tire, barrier rattle all at once.`

## Cropping Storyboards

For a successful 16-panel Banana image:

- Prefer `4x4` on a vertical 9:16 canvas, with every panel also a vertical frame.
- Split into 3 images when the user wants fewer Jimeng prompts:
  - rows 1-2 -> segment 1
  - row 3 -> segment 2
  - row 4 -> segment 3
- If the 16-grid is arranged differently, crop by story beat rather than equal size.

For a successful 18-panel Banana image:

- Preferred easy-crop layout: `6 columns x 3 rows`, vertical `9:16` canvas.
  - row 1 -> segment 1
  - row 2 -> segment 2
  - row 3 -> segment 3
- Larger-panel fallback layout: `3 columns x 6 rows`.
  - rows 1-2 -> segment 1
  - rows 3-4 -> segment 2
  - rows 5-6 -> segment 3
- In either layout, add a strong instruction that every panel is a vertical smartphone video frame, and avoid empty panels.

When a user has a 2-column by 6-row storyboard and wants six prompt segments, crop every 2 rows into one image:

- rows 1-2 -> segment 1
- rows 3-4 -> segment 2
- rows 5-6 -> segment 3

For two source images, this yields six segment images.

Use `scripts/split_storyboard.py` when possible instead of manual cropping.

Example crop commands:

```powershell
# 16-grid 4x4, split into 3 images: rows 1-2, row 3, row 4
python <path-to-skill>\scripts\split_storyboard.py input.jpg out_dir --prefix video1 --rows 4 --cols 4 --row-groups 1-2,3,4

# 18-grid 6x3, split into 3 images: each row is one segment
python <path-to-skill>\scripts\split_storyboard.py input.jpg out_dir --prefix video1 --rows 3 --cols 6 --row-groups 1,2,3

# 18-grid 3x6, split into 3 images: rows 1-2, 3-4, 5-6
python <path-to-skill>\scripts\split_storyboard.py input.jpg out_dir --prefix video1 --rows 6 --cols 3 --row-groups 1-2,3-4,5-6
```
