---
name: tiktok-pov-product-seeding
description: Build a first-person TikTok POV product seeding workflow for electric off-road bikes, e-bikes, and tech gear. Use when the user needs storyboard-first English scripts, Chinese translation, compliance word checks, native English polishing, CosyVoice/local voiceover handoff, rhythm captions, word or phrase caption timelines, beat-to-shot alignment, separated BGM/SFX tracks, HyperFrames transparent tech text overlays, and editable Jianying Pro draft planning without modifying source media.
---

# TikTok POV Product Seeding

## Use This For

Use this skill for first-person TikTok creator-style product videos where the product is an electric off-road bike, e-bike, scooter, power station, tool, camera gear, or similar tech/mechanical product.

The target feel is:
- cinematic POV
- product detail focused
- mechanical aesthetic
- realistic and immersive
- TikTok-native pacing
- non-commercial, calm creator voice

Reference videos are style directions, not permanent rules. Treat each reference as one preset for the current job. Future jobs can use other directions such as raw POV fast cut, quiet cinematic garage detail, night ride neon, clean tech HUD, outdoor trail documentary, or creator vlog review.

Do not turn the output into a brand ad, official product page, speed challenge, danger edit, or exaggerated claim video.

## Hard Rules

- Start from `storyboard.json`, then script, voiceover, captions, shot matching, BGM/SFX, and Jianying draft.
- Every voiceover sentence must map to one visual beat.
- Every beat needs duration, shot intent, visual action, subtitle segments, audio intent, SFX notes, and editorial notes.
- Keep BGM as one continuous main track and SFX as independent event tracks.
- Preserve environment audio unless the user explicitly wants it removed.
- Do not modify original source video or audio files.
- Do not edit encrypted or currently-open Jianying drafts in place. Create a new draft folder or a draft blueprint.
- If the script text changes, regenerate voiceover with CosyVoice before editing. Do not reuse an old voiced file against new copy.
- If reusing an existing voiced file, keep the script text from that voiceover or transcribe it first; do not silently swap in a different script.
- For this workflow, use the saved `ryan` cloned voice when requested. Preferred source is `D:\项目\Cosyvoice\custom_voices\ryan_prompt.wav` and `ryan_prompt.txt`, via the local CosyVoice WebUI/API.
- Source footage must stay true 9:16 in the final draft. If a selected clip appears letterboxed, sideways, or not filling the vertical canvas, reject it or crop/transform it before delivery.
- Reject meaningless or mismatched shots: no hand-blocked frames, no black/empty frames, no accidental ground-only shots, no repeated same-action shots, and no clip that does not prove the current voiceover beat.
- Repeated action rule: one complete action can appear once, and the editor may cut inside that action. Do not use two separate clips showing the same action, such as two separate key-turn/power-on shots.
- Avoid unsafe or exaggerated words: `dirt bike`, `motorcycle`, `motocross`, `crazy fast`, `insane speed`, `dangerous`, `race`, `wheelie`, `top speed`, `max speed`.
- Prefer safer wording: `off-road bike`, `off-road machine`, `powerful`, `smooth`, `solid`, `well built`, `performance`, `fun ride`.

## Default Workflow

1. Scan product info, source videos, voice sample or voiceover, and optional BGM/SFX library.
2. Generate `storyboard.json` first using the beat schema in `references/storyboard_schema.json`.
3. Generate natural American TikTok English copy, then Chinese translation.
4. Run compliance checks before caption or draft creation.
5. Prepare voiceover:
   - If script was newly generated or rewritten, use CosyVoice `ryan` to generate new audio first.
   - If a finished narration file is provided and the user wants to keep it, transcribe or preserve that narration text; do not replace it with unrelated copy.
   - If CosyVoice is available, call the local WebUI/API or write a `voiceover_manifest.json` with exact `ryan` prompt voice path and text.
   - Never build account-registration, quota-bypass, or free-API abuse workflows.
6. If GPT is enabled, use it to generate or polish beat-level copy and add a compliance summary, but keep the storyboard-first structure and output files unchanged.
7. Generate rhythm captions by phrase and breath, not one word per line.
8. Generate `captions.srt`, `subtitle_segments.json`, and `word_or_phrase_captions.ass`.
9. Align selected footage to beats in `edit_plan.md` and draft blueprint files.
10. For TikTok-native pacing, run `scripts/build_peak_matched_shot_plan.py` to split each voiceover beat into multiple unique shots and place cut points near audio peaks.
11. Review selected shots against the reference feel. Remove hand-blocked, letterboxed, repeated same-action, or semantically mismatched clips before writing the draft.
12. Generate `bgm_selected.json` and separate SFX event metadata.
13. If an actual plaintext Jianying/CapCut draft is generated, append BGM with `scripts/append_jianying_audio_layers.py` so existing voiceover is preserved.
14. Replace generated draft captions from `subtitle_segments.json` with `scripts/replace_jianying_captions.py` when exact rhythm subtitles matter.
15. When HyperFrames is requested, generate a transparent tech-style overlay HTML that reads the beat/subtitle timing.

## Main Script

Run:

```powershell
python C:\Skills\tiktok-pov-product-seeding\scripts\tiktok_pov_workflow.py `
  --media-dir "D:\项目\himiway\视频" `
  --output-dir "D:\项目\himiway\TK自动化" `
  --project-name "himiway_tiktok_pov" `
  --product-name "Himiway off-road e-bike" `
  --llm-provider openai `
  --openai-model "gpt-4.1-mini" `
  --voiceover-source "D:\项目\himiway\配音男.mp3" `
  --voice-speed 1.2 `
  --bgm-source "D:\项目\himiway\bgm.MP3" `
  --reference-video "D:\项目\himiway\m5.mp4" `
  --style-preset "capcut_native_fast_pov" `
  --fit-duration-to-voiceover
```

If `OPENAI_API_KEY` is not set, the workflow falls back to the local rule-based script generator and still produces the same output files.

The script writes:
- `storyboard.json`
- `script_en.txt`
- `script_zh.txt`
- `compliance_report.md`
- `subtitle_segments.json`
- `captions.srt`
- `word_or_phrase_captions.ass`
- `voiceover.mp3`
- `voiceover.wav`
- `voiceover_manifest.json`
- `gpt_generation.json` when GPT generation is enabled
- `bgm_selected.json`
- `edit_plan.md`
- `style_reference_note.md`
- `jianying_draft/`
- `hyperframes_overlay/index.html`

## Output Gate

Before calling the workflow successful, inspect:
- No banned words appear in script or captions.
- Storyboard beat count equals caption beat coverage.
- Voiceover duration is close to storyboard duration, or the storyboard was scaled to the provided narration.
- If the script was changed, `voiceover_manifest.json` must prove a fresh CosyVoice `ryan` generation. A copied or retimed old voice file is not acceptable for new copy.
- The `power_on` beat may use one complete key/power action only. It can cut inside one source file, but it must not use multiple separate key-turn clips.
- Source clips must be semantically tagged or manually approved for the line they support. Do not rely on filename order or duration alone.
- Reject shots with hands covering the product, black/empty frames, accidental ground-only composition, or detail shots that do not prove the current line.
- Phone-vertical clips with landscape dimensions plus rotation metadata must be verified in the draft so the final Jianying canvas fills 9:16 without black bars.
- BGM and SFX appear as separate metadata tracks.
- The draft folder contains multiple independent video beat entries, not a single flattened video.
- Source files are only referenced or copied as output voice/BGM assets; original media files are not modified.

Run the audit before delivery:

```powershell
python C:\Skills\tiktok-pov-product-seeding\scripts\audit_tiktok_pov_run.py `
  --output-dir "D:\项目\himiway\TK自动化" `
  --plan-file "D:\项目\himiway\TK自动化\jianying_draft\retrieval_plan.semantic_peakcut.generated.json" `
  --draft-dir "C:\Users\<your-user>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\himiway_tiktok_pov_120x_v3_semantic_peakcut"
```
