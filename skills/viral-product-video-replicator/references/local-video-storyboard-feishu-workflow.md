# Local Video Storyboard and Feishu Workflow

Use this workflow when operating or modifying the local video storyboard tool, or when the user asks for a simple evidence-based shot breakdown rather than a full creative replication package.

## Known local tool

- Project: `E:\codex数据\自动拆解脚本\video-storyboard-tool`
- One-click launcher: `E:\codex数据\自动拆解脚本\video-storyboard-tool\launch_video_storyboard_tool.bat`
- Local URL: `http://127.0.0.1:8787/`
- Health check: verify the real process and HTTP endpoint before reporting that the tool is running.

If the path changes, locate the project by `launch_video_storyboard_tool.bat`, `START_HERE.bat`, or `app/main.py`. Do not create a second copy merely because the saved path is unavailable.

## Bundled software

The same Skill includes `assets/software/video-storyboard-tool-portable.zip`. It contains the application source, static frontend, prompts, launchers, dependency files, and installation guide. It intentionally excludes credentials, local virtual environments, logs, uploaded videos, and generated outputs.

For a new Windows computer, extract the ZIP to a normal writable folder and double-click `START_HERE.bat`. The first launch creates a local `.venv`, installs dependencies, and creates `.env` from the blank `.env.example`. Install Python 3.10+ first; install FFmpeg in PATH when audio transcription is needed.

## Request routing

Use the simple local workflow when the user says any equivalent of:

- upload or drag one or more videos and split them automatically
- break down the script or shots
- export Excel, Markdown, or a Feishu-native table
- sync the result to a supplied Feishu Docx or Wiki URL
- fix missing frames, blank rows, slow loading, duplicate shots, or unsupported descriptions

Do not add Banana, Jimeng, character bibles, product replacement, marketing logic, or social copy unless requested.

## Processing flow

1. Confirm the selected files are readable video files. Preserve their order.
2. Give a rough completion-time estimate before a large batch starts.
3. Process videos sequentially so each video has an independent result and failure state.
4. Detect visual changes and extract representative frames. Remove accidental duplicate or near-empty shots, but do not merge visibly different actions merely to reduce the count.
5. Inspect every representative frame before writing semantic text. Use neighboring frames only to disambiguate motion.
6. Show lightweight thumbnails in the browser. Keep the original frame file for export and Feishu upload.
7. If a Feishu Docx or Wiki URL is present, append the finished storyboard automatically after that video's local export succeeds.
8. Continue to the next video if one video or one Feishu sync fails. Report the exact failed video and real error.

## Evidence-first description rules

The selected frame is the primary source of truth. Do not infer a rider, motorcycle, road, product part, stunt, or feature from shot position, file name, previous video, or a rotating template.

Write `画面说明` as one short factual sentence, normally 4-16 Chinese characters:

- `骑手在山路骑车。`
- `汽车从画面右侧驶过。`
- `人物拿起桌上的产品。`
- `镜头展示车辆前轮。`
- `黑场转场。`

Write `备注` as one short reproduction instruction, normally 4-18 Chinese characters:

- `跟拍骑手经过。`
- `低机位拍车辆前轮。`
- `固定机位拍人物拿起产品。`
- `横向移动拍汽车。`

Avoid unsupported or verbose text such as:

- invented component names, model features, or product claims
- generic filler about atmosphere, visual impact, mechanical texture, or composition
- advice that is not needed to reproduce the visible shot
- repeated wording that ignores visible differences between shots

If evidence is insufficient, prefer `主体在画面中移动。`, `拍摄主体局部。`, or a blank optional field. Never turn uncertainty into a specific claim.

## Camera fields

Only assign shot size or camera method when visual evidence supports it. Use stable, familiar labels:

- Shot size: `远景`, `全景`, `中景`, `近景`, `特写`
- Camera method: `固定机位`, `手持跟拍`, `跟拍`, `推镜`, `拉镜`, `横移`, `低机位`, `俯拍`, `POV`

Do not cycle these labels by shot number. If uncertain, use the least specific truthful label.

## Table behavior

- Keep each video's shots in one continuous logical storyboard.
- Do not insert blank rows above the header, above images, between shots, or between chunked native tables.
- Trim leading and trailing whitespace from every text cell. Collapse accidental repeated spaces and line breaks.
- Keep images inside the image cell without an empty paragraph above them.
- Preserve shot order and do not silently drop rows.
- The current Feishu Docx API path uses at most 6 shot rows per physical native table. When a video exceeds 6 shots, create consecutive native tables in one operation and treat them as one logical storyboard.
- For multiple videos, append each video's complete logical storyboard in upload order. Do not interleave their rows.

## Feishu synchronization

- Treat the document or Wiki URL as a per-run input because it may change every time.
- Never hardcode a changing document token, Wiki token, user token, or access token into the Skill.
- Append to the supplied document; do not overwrite unrelated content.
- Use native Docx table blocks for the storyboard. Do not downgrade the result to plain Markdown when native tables are requested.
- Upload original frame images to Feishu even when the browser uses thumbnails.
- A successful local export does not prove Feishu sync succeeded. Report them separately.
- After synchronization, verify the returned result and, when tooling allows, read back the created blocks or native-table status before reporting success.

## Performance rules

- Generate thumbnails lazily and use browser lazy loading.
- Do not embed every full-resolution frame into the initial page payload.
- Keep original frames on disk for Excel, Word, copy, and Feishu operations.
- For multiple videos, update progress per video instead of freezing the page until the whole batch ends.

## Failure diagnosis

- Missing browser image but visible in Feishu: check thumbnail URL generation, lazy loading, and static-route permissions; do not regenerate all frames first.
- Text unrelated to the frame: confirm whether a hardcoded template or shot-index rule produced it; compare representative frames before changing thresholds.
- Only six rows appear: check whether additional native tables were created and whether the batch request stopped after the first table.
- HTTP 400 `1770001 invalid param`: inspect table dimensions, child blocks, insertion index, and image block payload; do not label it a permission problem without evidence.
- Slow loading: compare thumbnail request sizes and counts with full-resolution frames.

## Completion checks

Before reporting completion:

1. Start the real launcher or server entrypoint.
2. Confirm the health endpoint responds.
3. Run at least one real sample video through analysis.
4. Check that representative frame images load in the browser.
5. Read several descriptions and confirm each is short and supported by its frame.
6. For batch changes, test at least two videos in sequence.
7. For Feishu changes, distinguish local export success from verified remote sync success.

Do not claim visual-semantic accuracy if the implementation only uses brightness, edges, shot index, or other OpenCV heuristics. Accurate object and action naming requires actual frame inspection or a vision-capable model.
