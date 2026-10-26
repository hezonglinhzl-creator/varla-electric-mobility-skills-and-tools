# image2-motion-agent

Shareable Codex skill for turning ad/product images into Dreamina/Jimeng image-to-video prompts.

## What It Does

- Analyzes ad, poster, product, and social media images.
- Protects original text, logo, product claims, rider, and product shape.
- Produces English prompts for Dreamina/Jimeng plus Chinese check notes for review.
- Defaults Himiway/Varla ads to moving copy/subtitles, logo glow, moving scene/background, and active riding/product motion.
- Requires user confirmation before submitting tasks that consume credits.
- Adds a dry-run-first Dreamina/Jimeng CLI wrapper for image-to-video jobs.
- Allows temporary QA frames/contact sheets, then deletes them one explicit file at a time after analysis.

## Install

Unzip the package, then double-click `install.cmd`.

The installer copies this skill to:

```text
C:\Users\<your-user>\.codex\skills\image2-motion-agent
```

Restart Codex after installing if the skill does not appear immediately.

## GPT Prompt + Dreamina CLI Flow

1. Codex/GPT inspects the source image and writes the English motion prompt plus Chinese check notes.
2. User confirms the prompt.
3. Save the final prompt as a JSON job file.
4. Dry-run the exact CLI command:

```powershell
python "%USERPROFILE%\.codex\skills\image2-motion-agent\scripts\dreamina_image2video.py" --job "C:\path\job.json"
```

5. After confirmation, submit the task:

```powershell
python "%USERPROFILE%\.codex\skills\image2-motion-agent\scripts\dreamina_image2video.py" --job "C:\path\job.json" --execute
```

The wrapper returns JSON and does not consume credits unless `--execute` is used.

## Example Trigger

```text
Use image2-motion-agent. Analyze this VARLA ad image and create Dreamina image-to-video prompts. Show English prompt and Chinese check version first; submit only after I confirm.
```
