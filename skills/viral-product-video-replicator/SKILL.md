---
name: viral-product-video-replicator
description: Use when the user provides benchmark videos, product materials, product links, images, scripts, subtitles, or asks to 脚本拆解、本地视频拆镜头、批量视频拆分、同步飞书原生表格、拆解爆款、复刻产品视频、替换产品、生成分镜、生成香蕉图片提示词、生成即梦提示词、拆分即梦短提示词、生成欧美真人感人物、制作电摩原生 UGC 剧情、沉淀人物参数、生成 TikTok/INS 文案。Outputs evidence-based concise storyboard breakdowns, local multi-video processing and Feishu-native-table handoff, localized copy analysis, product-substitution scripts, realistic character assets, electric-motorcycle UGC story prompts, Banana storyboard prompts, Jimeng image-to-video prompts, short prompt segments under tool limits, ordered sound design notes, and social post copy.
---

## Portable distribution paths / 完整包程序位置

Before running a program, read `PACKAGE-LOCATION.json` beside this installed SKILL.md.
Its `apps` object maps each bundled program name to the real extracted directory;
`package_root` points to the complete bundle. Use those paths first. Absolute paths
in older examples below are historical examples, not automatic defaults.
If this file is missing or the bundle was moved, rerun the complete project's
install.ps1 to refresh the mapping. Keep the extracted program directory.
Never treat YOUR_* placeholders as configured credentials or resource IDs.

运行程序前先读取本 SKILL.md 旁边的 `PACKAGE-LOCATION.json`：`apps` 是实际程序目录，
`package_root` 是完整包位置。下文旧电脑绝对路径只作为历史示例，不能自动照用。
缺少映射或完整包搬家后，重新运行完整包 install.ps1；保留解压后的程序目录。
YOUR_* 占位符不代表已配置账号或资源；真实写入前必须使用自己的授权和目标链接。


# Viral Product Video Replicator

## Core Workflow

Use this skill to turn benchmark short videos or storyboard images into a reusable product-video production package.

First route the request by scope:

- If the user only wants to upload videos, split shots, describe what each frame is doing, export a table, or sync to Feishu, use `references/local-video-storyboard-feishu-workflow.md`. Keep the result operational and concise; do not generate the full replication package.
- If the user asks for benchmark persuasion analysis, product replacement, AI image/video prompts, character continuity, or social copy, continue with the full workflow below.

1. Ingest local benchmark assets first: video, storyboard image, product image, subtitles, captions, product page, or existing prompts.
2. Extract visual structure. Use `ffprobe` for metadata and `ffmpeg` for contact sheets/keyframes when a video file is available.
3. Read copy locally. Use subtitles, visible on-screen text, transcript files, OCR/ASR outputs, or user-provided captions. If no transcript exists, infer from frames and mark it as inferred.
4. Build a shot-by-shot replacement plan. Preserve the persuasion structure, but rewrite story, copy, product logic, and character identity.
5. Generate the production package: storyboard table, script, captions, TikTok/INS post copy, Jimeng prompts, Banana prompts, product notes, character continuity, and reusable memory JSON.
6. For AI video production, use a two-stage flow: Banana images lock visual frames; Jimeng animates those frames.
7. If a target tool has a prompt length limit, split output into numbered image+prompt pairs with time ranges.
8. Update or propose character/product memory records when the user wants continued accumulation.
9. When the user asks for realness, 原生感, UGC, local user style, or says the output feels too AI/commercial, switch from ad-shot logic to Native UGC Realness mode.
10. When the user explicitly asks for a generated storyboard image, image reference, 9-grid, 16-grid, or 18-grid, produce the image first and verify it is visually on-brief before writing the rest of the package.
11. When the request is an electric motorcycle/e-bike family story, one-take contrast story, vehicle reveal, rider-skill reaction, or relationship comedy, use the Electric-Motorcycle UGC Story Mode below.
12. For electric-motorcycle narrative prompts, default to the proven clear two-second narrative-block and multi-cut action structure in `references/emoto-ugc-story-workflow.md`: capture lock, compact character lock, one prose paragraph per approximately two seconds, explicit dialogue ownership, continuous cause and effect, visible facial change, micro-actions, body reaction, shot-scale variation, action/gaze/sound bridges, camera-movement continuity, and a clear handoff into the next block. Unless a continuous take is requested, use about 3 shots for 6 seconds, 4 shots for 8 seconds, and 4-5 shots for 10 seconds. Validate every adjacent pair as shot A end position/direction/speed -> cut bridge -> shot B start position/direction/speed.

Do not default to external API calls. Generate the planning package directly unless the user explicitly asks to call an external image/video API.

## Local Video Storyboard and Feishu Mode

Use this mode for requests such as `脚本拆解`, `视频丢进去自动拆解`, `批量上传视频`, `导出分镜表`, `同步飞书文档`, or complaints that the local storyboard text is verbose, unsupported by the frame, slow to load, missing images, split incorrectly, or contains blank rows.

Read and follow `references/local-video-storyboard-feishu-workflow.md` before operating or modifying the local tool. This mode is evidence-first: inspect the selected frame before naming a person, product, vehicle, action, environment, or camera behavior. If the frame does not prove a detail, use a neutral phrase or leave the field blank instead of guessing.

The packaged Windows software is bundled at `assets/software/video-storyboard-tool-portable.zip`. Use it when the user asks to install, migrate, restore, or run the local tool on another computer. Read `assets/software/README.md` before extraction. Never package or restore a user's `.env`, access tokens, logs, uploaded videos, generated outputs, or machine-specific `.venv`.

Keep the two main text fields short:

- `画面说明`: state only what is visibly happening, usually one short sentence.
- `备注`: state only how to reproduce the shot, usually one short sentence.

Do not expand a simple breakdown request into product strategy, persuasion analysis, feature claims, replacement ideas, safety lectures, or AI prompts unless the user asks for them.

## Direct Image Storyboard Generation

Use this path when the user says `生图`, `生成18宫格`, `给我图`, `gpt-image2`, `image故事版`, or wants a reference image before Jimeng.

Priority:

1. First create the storyboard image requested by the user.
2. Only after the image is visually on-brief, create Jimeng prompts, subtitles, TikTok/INS captions, and usage notes.
3. If the generated image is off-brief, such as becoming a map, infographic, poster, educational chart, UI, unrelated product, or non-video layout, do not present it as the deliverable. State that it failed, tighten the prompt, and retry once with simpler image-only wording.
4. If the second attempt is still off-brief, stop image generation attempts and return a corrected prompt plus the failure note. Do not bury the user in unrelated files.

For grid storyboards:

- Prefer `6 columns x 3 rows` for 18-grid when the user wants three Jimeng segments.
- Each panel must be described as a vertical smartphone video still, not as a design board cell.
- Avoid words that make image generators create posters: `plan`, `infographic`, `chart`, `table`, `template`, `presentation`, `diagram`, `labels`, `text`.
- Use direct wording: `one single photorealistic image collage made of 18 separate vertical smartphone video stills`.
- Strong negative controls must include: `no text`, `no typography`, `no map`, `no infographic`, `no poster`, `no UI`, `no labels`.
- For product videos, every panel must show the product, the person interacting with it, a product detail, or a proof moment. Avoid empty establishing shots.

Direct image output contract:

- Save or copy the final image into the project folder when possible.
- Then create matching segment prompts only if the image is usable.
- If the user asked only for the image, do not create extra Markdown files unless they asked for the full package.

## Required Inputs

Accept partial inputs and continue with reasonable assumptions. Ask only when missing information blocks product replacement.

- Benchmark asset: `.mp4`, `.mov`, storyboard grid image, exported frames, subtitles, or transcript.
- Product material: product name, photo, landing page, selling points, target audience, price, use scenario, brand tone.
- Platform target: TikTok, Instagram Reels, ads, organic post, influencer style, or marketplace listing.
- Output target: script, Banana prompts, Jimeng prompts, split prompts, social captions, or full production pack.

If product details are thin, create a short `Product Assumption Card` and mark assumptions clearly.

## Breakdown Rules

For each benchmark, identify:

- Hook type: curiosity, transformation, product proof, race/competition, problem-solution, tutorial, trust hook.
- Timeline beats: opening, setup, proof, failure/objection, product reveal, feature proof, payoff, CTA.
- Frame logic: camera angle, subject, product position, action, text overlay, transition, proof element.
- Copy logic: claim, objection handling, credibility cue, urgency cue, viewer payoff, CTA.
- Replaceability: what can be copied structurally, what must change for originality.
- Risk notes: exact face/person mimicry, brand/logo copying, stereotypes, unsafe scenes, misleading claims.

For simple local shot breakdowns, the frame itself is the source of truth. Do not reuse a motorcycle, rider, road, product-part, or camera-action template merely because earlier videos contained those subjects. A description must be supported by the current frame and neighboring frames.

Use `references/seedance-codex-reference-breakdown.md` when the user references the Codex/Seedance tutorial video.

## Product Replacement

Do not only swap product names. Rewrite the beat so the product naturally belongs in the scene.

For each shot, specify:

- Original role: what the benchmark shot does psychologically.
- New product role: how the user's product creates the same persuasion effect.
- Visual substitution: product angle, interaction, scale, texture, usage context.
- Copy substitution: new claim, proof, objection response.
- Required assets: product photo, logo-free close-up, lifestyle shot, packaging, before/after, user scenario.

If a product image is provided, keep identity stable across prompts by repeating persistent details: shape, material, color, distinctive edges, buttons, tires, forks, frame, packaging, texture. If a model invents unwanted details, add both positive and negative controls, e.g. `clean black side panel` and `no blue ring`.

## Realistic Western Characters

When the user asks for 欧美人物, 真人感, or long-term character continuity, create a reusable character bible instead of a one-off prompt.

Each character should include:

- Identity: age range, ethnicity/region cue, body type, face shape, hair, skin texture, wardrobe, personality.
- Realism controls: natural asymmetry, non-plastic skin, imperfect hair, normal pores, documentary lighting, no over-smoothed beauty filter.
- Continuity tokens: stable hairstyle, outfit palette, accessory, environment, lens style.
- Negative controls: no doll-like face, no AI gloss, no extra fingers, no changing identity, no uncanny smile.
- Usage role: rider, host, customer, expert, friend, demo model, before/after subject.

For single-character reference sheets, state: one person only, same identity repeated across angles, no second person, no group, no product unless needed.

For a three-view character asset, require front, full side, and back views of the same identity, full body with feet visible, equal scale, identical clothes/accessories, neutral pose, plain light background, no text, and no props unless explicitly requested. Do not let a safety prop needed in the final riding scene leak into a separate no-prop character sheet.

## Native UGC Realness Mode

Use this mode when the user wants 美国真实用户手机随拍, 原生感, less AI feeling, less commercial lighting, or ordinary TikTok/Reels UGC.

Core visual direction:

- Ordinary user phone video, not advertising or studio production.
- Real household or backyard context: imperfect rooms, patio clutter, party tables, packaging paper, cups, tools, grills, chairs, normal suburban background.
- Phone camera behavior: handheld, slight shake, imperfect framing, occasional partial crop, natural auto exposure, slight uneven brightness, mild motion blur.
- Lens/texture controls when useful: `35mm lens`, `f/1.8 shallow depth of field`, `subtle cinematic grain`, natural hard light, real shadows.
- Human behavior: people do specific tasks, pause, glance, hesitate, misread, smile awkwardly, check each other's reaction; avoid model poses and perfect smiles.
- Keep dialogue short, casual, local-market, and scene-motivated. Avoid slogans unless it is the final product line.

Native UGC negative controls:

- `no commercial ad look`, `no studio lighting`, `no beauty filter`, `no actor-like overreaction`, `no perfect model faces`, `no cinematic hero pose`, `no subtitles`, `no UI`, `no app interface`, `no strange overlay`.
- For household comedy, avoid unsafe physical harm. Prefer harmless comedic taps, startled reactions, misunderstanding, or exaggerated sound without injury.

When the user wants the high-quality real-skin front-camera selfie look, load the `High-Fidelity Front-Camera Selfie Texture` section in `references/native-ugc-realness-workflow.md`. In that mode, prefer phone front-camera wide-angle perspective and readable environmental depth; do not combine it with `35mm`, `f/1.8`, portrait mode, or cinematic background blur.

Product proof in Native UGC:

- Show the product doing one concrete job, not only being held.
- For tools, show clear mechanical contact: bit, screw slot, hole, bracket, alignment, before/after stability.
- Avoid vague action like drilling into blank wood or letting the tool block the connection point.
- Split proof shots by distinct task locations, not repeated close-ups of the same area.

For detailed examples, load `references/native-ugc-realness-workflow.md`.

## Electric-Motorcycle UGC Story Mode

Use this mode for 电摩/电动越野车/e-bike stories involving family surprise, garage reveal, social comedy, one-take contrast, crowd reaction, rider skill, or a product-led meet-cute.

1. Read `references/emoto-ugc-story-workflow.md` before writing the final production prompt.
2. Separate the user's dramatic premise from production constraints. Preserve the emotional turn, but rewrite unsafe, discriminatory, or implausibly dense execution details.
3. Lock the actual vehicle from user-provided product references. Do not transfer M5S, M7S, ignition, controller, lighting, logo, brake, chain, or color details between models without evidence.
4. For a one-take prompt, design one continuous camera path and a small number of readable beats. Keep spoken dialogue within the available runtime instead of compressing a multi-scene script into one impossible generation.
5. When a minor is present, keep the child out of stunts and dangerous riding. Prefer observer/reaction roles, a stopped vehicle for close interaction, and visible protective gear when riding is shown.
6. Do not provide real-world stunt technique. For risky-looking footage, use a qualified adult rider, closed course, protective equipment, and compositing/VFX where appropriate. Never promise platform approval; describe the safer version and remaining moderation risk.
7. Treat ethnicity, body type, sweat, age, disability cues, or awkwardness as individual character details, not as the cause of incompetence, dirtiness, danger, or ridicule.
8. Deliver TikTok and Instagram copy separately: TikTok should lead with the reveal/reaction; Instagram may add warmer context. Keep claims consistent with what the video visibly proves.

## Banana-to-Jimeng Fast-Cut Pipeline

Use this pipeline when the user mentions 香蕉, 即梦, image-to-video, prompt limits, split generation, or fast-cut short-video production.

1. Generate Banana storyboard prompts first. Banana is used to lock visual frames; Jimeng is used to animate them.
2. Banana storyboard images for vertical short video must be `9:16`. If using multi-grid storyboards, specify that the whole canvas is vertical `9:16` and each panel is also a vertical video frame, not a horizontal frame.
3. Prefer segment storyboard images over one giant storyboard. For a 20-30 second short video, split into 2-6 segments with clear time ranges.
4. A successful 16-panel or 18-panel Banana image can be used, then cropped into 3 segment images for Jimeng.
   - For a `4x4` 16-grid, common crops are rows `1-2`, row `3`, and row `4`.
   - For an 18-grid, prefer `6 columns x 3 rows` on a vertical `9:16` canvas when the user wants three easy crops; crop each row into one 6-shot segment.
   - If single-panel clarity matters more than vertical panel purity, use `3 columns x 6 rows` and crop rows `1-2`, `3-4`, `5-6`.
5. For each segment, produce a matching image filename and prompt filename, e.g. `01_video1_00-04s_startline.jpg` and `01_video1_00-04s_startline.txt`.
6. Keep each Jimeng prompt under the user's tool limit. If the user says 2K characters, create separate short prompts instead of one complete prompt.
7. Add short Chinese operator labels for the user, but keep the actual prompt compact.
8. Give every segment a clear start/end state so clips can join smoothly.
9. When a generated storyboard is a grid, crop it into segment images when helpful. Use `scripts/split_storyboard.py` for deterministic crops.

For detailed examples, load `references/banana-jimeng-fastcut-workflow.md`.

## Native UGC Banana-to-Jimeng Pipeline

Use this variant instead of the fast-cut race/demo pipeline when the goal is "真实用户随拍" rather than high-energy ad pacing.

1. Banana image should lock a believable real-life sequence, not a glossy hero storyboard.
2. Prefer fewer panels and clearer continuity: 6-10 panels for a 15 second clip, often 2-3 Jimeng segments.
3. Segment by natural action continuity: setup/misunderstanding, product proof/use, result/payoff.
4. Each Jimeng segment should remain under tool limits, commonly under 2K characters.
5. Each segment should upload the matching cropped reference image when possible.
6. Use strong reference lock, then concise identity locks for only the main characters and product.
7. Add "no subtitles, no UI, no strange interface/overlay" when the user reports weird frames.
8. Sound should be diegetic: room tone, paper rustle, footsteps, party chatter, drill motor, key jingle, soft family laughter. Avoid music unless requested.

## Fast-Cut Editing Rules

For TikTok/Reels race, demo, or contrast ads:

- Keep runtime tight: usually 20-30 seconds.
- Split around tool limits: e.g. 13s + 12s for a 25s video when one generation is limited to 15s.
- Use short shots: 0.4-1.1s for high-energy race or short-drama pacing.
- Use impact angles deliberately: POV, ground-level upward angle, ultra-wide close pass, tire close-up, spectator reaction, whip pan, finish-line wide shot.
- Do not make the comparison mean-spirited. Attribute the difference to the product/machine, not the person or ethnicity.
- If a clip already works, iterate prompts around the successful frames instead of returning to generic descriptions.

## Jimeng Prompting

Generate Jimeng prompts as production prompts, not abstract art prompts.

Each Jimeng prompt should include:

- Uploaded reference image to use.
- Shot or segment duration.
- Scene and environment.
- Character continuity phrase.
- Product identity phrase.
- Camera and motion: framing, movement, lens feel, focus behavior.
- Action: start state and end state.
- Lighting and texture.
- Platform format: vertical `9:16` unless requested otherwise.
- Ordered sound design when audio is needed.
- Compact negative prompt.

For split prompts, prefer concise segment prompts under the user's input limit. Include exact filenames and time ranges.

For Jimeng prompts based on Banana images, start every segment with a strong reference lock such as:

`Strictly follow the uploaded Banana reference image. Use it as the main visual guide for composition, riders, bikes, track, camera angles, and scene order. Do not redesign the scene.`

## Ordered Sound Design

Do not stack every sound in every shot. Use ordered sound design:

- Each cut has one dominant sound and at most one light background sound.
- Start-line tension: heartbeat or low motor idle.
- Flag shot: flag flap.
- Launch: electric motor acceleration.
- Tire close-up: tire grip, dirt scrape, or dirt spray.
- Spectator cutaway: crowd reaction.
- Weak product failure: motor sputter, dashboard beep, motor cutout, smoke hiss.
- Hero product action: strong motor hum, suspension thump, tire bite.
- Dialogue shot: dialogue is the main sound; ambience stays low.
- Product end card: native-market male ad voice or clean product line; ambience stays low.

If the user asks for local-market dialogue, specify voice region and delivery, e.g. `native American male voice, casual curious tone`.

## Output Contract

Default output in Chinese unless the user requests English.

Produce only the sections needed for the user's stage. Common sections:

- `爆款结构拆解`: concise timeline and persuasion logic.
- `本地分镜表`: shot table with time, picture, action, copy, product replacement.
- `产品替换方案`: assumptions, visual proof points, required materials.
- `欧美真人感人物参数`: character bible and continuity rules.
- `香蕉图片提示词`: storyboard prompts for image generation.
- `即梦图生视频提示词`: animation prompts, split when needed.
- `分段文件清单`: image/prompt filename pairs with time ranges.
- `成片脚本`: narration, dialogue, subtitles, CTA.
- `TikTok/INS 文案`: caption, hashtags, first comment, pinned comment.
- `复用记忆`: product memory JSON and character memory JSON.
- `本地拆镜与飞书同步`: concise shot table, local exports, and verified Feishu native-table result according to `references/local-video-storyboard-feishu-workflow.md`.

See `references/output-contract.md` for the detailed schema and formatting.

## Quality Bar

- Keep the benchmark's conversion structure, but change story, wording, product logic, and character identity enough to avoid thin copying.
- Prefer concrete visuals over generic adjectives.
- Keep generated people photorealistic and consistent, but never claim they are real customers unless the user provides evidence.
- Avoid overclaiming product results. Use compliant phrasing for safety and performance claims.
- Flag missing materials that would make the video weaker.
- When the user is beginner/non-programmer, create ready-to-use local files with clear names instead of only explaining.

## Native UGC Update: Texture Reference Only

When the user provides a reference video for "quality", "texture", "parameters", "native feel", "原生感", or "真实手机随拍", do not automatically copy the reference story. Extract only texture and production parameters, then apply them to the user's requested plot.

Reuse from texture references:

- handheld phone movement
- phone auto exposure
- slight uneven brightness
- slight hand shake
- imperfect framing
- 35mm lens feel
- f/1.8 shallow depth of field
- subtle grain
- natural household, garage, patio, or backyard light
- real room tone, footsteps, key jingles, door clicks, garage ambience, tool sounds

Do not reuse unless explicitly requested:

- reference characters
- reference product
- reference joke or conflict
- reference dialogue
- reference timeline
- reference scene if the user specified another scene

## Native UGC Update: Single-Subject Stability

Use this pattern when the user wants fewer AI mistakes or a more realistic one-person story.

- Keep only one fully visible main character.
- Supporting people should appear only as a hand, voice, silhouette, or partial off-camera presence.
- Use hard visibility controls: `Only the boy is fully visible`, `one adult hand only`, `no adult face`, `no adult body`, `no extra people`.
- Keep one continuous action path: hand gives key, boy walks to garage, boy opens door, boy discovers product, boy starts product.
- Use ordinary cluttered spaces: hallway, garage door, shelves, boxes, tools, storage bins, mixed garage light.
- For vehicle-start scenes, require a visible ignition/key slot, the key clearly inserted, the boy turning the key to start, the left-side handlebar instrument/controller lighting up, the headlight turning on, and soft startup sound. Avoid vague "press start" language unless the real product only uses a button.

## Native UGC Compact Jimeng Prompt Pattern

When the user needs a 15 second Jimeng prompt under a strict character limit, create a compact `2k内` version and verify character count.

Compact structure:

```text
Strictly follow uploaded Banana reference image. [User's plot, not benchmark plot]. Only [main subject] fully visible. [Supporting presence] only. Do not redesign.

9:16 vertical, [duration]. Real American family phone video, handheld UGC, ordinary home, phone auto exposure, uneven brightness, slight shake, imperfect framing, 35mm, f/1.8 shallow depth, subtle grain, natural light, no commercial lighting, no subtitles, no UI.

Subject lock: [short identity and outfit].
Product lock: [short product identity and stable details].
Action: [time-coded beats].
Sound: No music unless requested. [diegetic sounds].
Negative: no extra people, no duplicate subject, no face drift, no UI, no overlay, no ad look, no wrong product.
```

## Persistent Product Identity

When the user says the product must stay the same or they do not want to re-upload product photos every time, create or reuse a local product memory file near the project output.

For each recurring product, keep:

- reference image paths
- fixed identity prompt
- feature checklist
- negative prompt
- scene-specific dirt/proof requirements

Always reuse this memory before generating Banana or Jimeng prompts for that product. If exact product fidelity matters, state that the reference images should still be uploaded to the image/video tool when possible, but the local memory is the default prompt source.

For recurring product-specific tasks, reuse the local product memory files supplied by the user in the current project folder, for example:

- `<project-output-folder>/<product-name>_fixed_product_prompt.md`
- `<project-output-folder>/<product-name>_product_memory.json`
## Exact Product Fidelity Rule

Use this rule when the user says the product must be identical, complains that the generated product changed, or points out wrong logos, front face, calipers, chain, foot pegs, controller, color, or vehicle category.

Do not rely on text-only image generation or a rough composited placeholder as the final reference. Product reference photos are the source of truth.

Required workflow:

1. Create or reuse a product lock file with exact reference image paths and non-negotiable visual features.
2. Tell the user to upload the product reference photos with Banana/Jimeng whenever product fidelity matters.
3. Generate a production prompt package: full storyboard, split Banana prompts, split Jimeng prompts, and a detail checklist.
4. If a preview image is crude or synthetic, label it as a planning aid only; never present it as the final visual reference.
5. Add specific negative controls for the known failure: no wrong logo, no changed front face, no missing chain, no missing foot pegs, no missing red calipers, no wrong controller location, no bicycle, no scooter, no gasoline motorcycle.

For cleaning videos, require a visible transformation: extremely dirty opening, functional cleaner application, detailed scrubbing, water rinse, towel wipe, and clean final shot. Detail shots should cover tire tread, chain/sprocket, foot pegs, brake discs, red calipers, lower body panels, side logo panel, seat, handlebar/controller, and headlight. If colored cleaners are requested, assign colors by function and state that cleaner color must not recolor or redesign the product.

Planning diagrams are allowed only as internal planning aids. If the user asks for a generated image to feed into an image-to-video tool, the deliverable must be a photorealistic storyboard/reference image, not a drawn diagram, placeholder collage, or labeled chart.
