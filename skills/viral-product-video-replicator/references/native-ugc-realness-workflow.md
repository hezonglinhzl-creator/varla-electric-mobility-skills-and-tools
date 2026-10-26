# Native UGC Realness Workflow

Use this reference when the output needs to feel like real American local-user phone footage instead of an AI ad.

## When To Use

- User says the clip feels too AI, too commercial, too staged, or too clean.
- User asks for 原生感, 美国真实用户手机随拍, ordinary TikTok, UGC, home video, or local user perspective.
- The scene is a family surprise, product gift, home DIY, backyard BBQ, party, garage, patio, workshop, living room, or ordinary household use.

## Visual Recipe

Use concrete realism controls:

`real handheld smartphone video, ordinary American home, phone auto exposure, slight uneven brightness, slight handheld shake, imperfect framing, mild motion blur, 35mm lens, f/1.8 shallow depth of field, subtle cinematic grain, hard natural light, real shadows, no commercial lighting`

Do not overuse cinematic language. `subtle cinematic grain` is acceptable for texture; avoid `cinematic commercial`, `hero shot`, `studio lighting`, and `perfect beauty lighting` unless the user asks for an ad.

## High-Fidelity Front-Camera Selfie Texture

Use this mode when the user asks for the realistic skin and phone-selfie quality shown in `../assets/real-skin-iphone-selfie-reference.png`, or says 后面参考这种提示词、有真实皮肤感觉、前置自拍、边走边口播.

Treat the reference as a texture and capture-language source only. Do not automatically copy its Latino male character, tool-store location, wardrobe, gesture, product, price complaint, or story.

For this mode, override generic cinematic lens language:

- Use `real smartphone front-camera wide-angle selfie`, not `35mm lens` or `f/1.8 shallow depth of field`.
- Frame from chest or upper torso to waist at arm's length. The phone stays outside the image.
- Preserve mild front-camera perspective: the face and gesturing hand may appear slightly closer, while body proportions remain believable.
- Keep the environment readable with moderate depth and ordinary phone focus. Do not blur the background into cinematic bokeh.
- Use practical indoor ceiling light or natural available light, ordinary auto white balance, small exposure variation, and restrained phone sharpening.
- Add only subtle handheld imperfection: slight tilt, tiny movement, and candid framing. Do not simulate heavy shake or degraded low-quality footage.

Real-skin controls:

- visible pores and fine skin microtexture
- slight natural variation in skin tone
- believable under-eye texture, forehead lines, smile lines, and beard/stubble edges when relevant
- natural highlights on forehead, nose, cheeks, and lips from the actual light source
- realistic facial asymmetry and normal human proportions
- no beauty filter, no airbrushed smoothing, no waxy skin, no plastic shine, no glossy AI skin, no over-sharpened pores, no fashion retouching

Expression and performance should remain restrained. Use a slightly raised eyebrow, small mouth tension, quiet disbelief, mild annoyance, or a natural half-smile. Avoid exaggerated comedy faces and actor-like gesturing.

When creating a later storyboard frame in the same location, force a real spatial change instead of repeating the first image:

- name the new store zone or aisle type
- specify what appears on each side and in the far background
- change the person's side of frame, crop, distance, and background direction
- describe how the space becomes narrower, deeper, busier, or more fragmented
- preserve the same character identity and wardrobe while changing only staging and camera position

Recommended prompt block:

```text
9:16竖屏、超写实手机前置自拍画面。严格锁定已上传人物参考图中的同一人物、脸部、年龄、肤色、发型、胡须、体型和服装，不换脸、不换衣服、不模特化。

使用真实智能手机前置广角自拍质感，手臂长度拍摄，手机不入镜，人物以胸部以上到腰部为主，轻微手持倾斜和自然自动曝光。背景保持清楚可辨，具有普通手机景深，不使用35mm电影镜头，不使用f/1.8浅景深，不使用人像模式，不制造电影散景。

皮肤必须保留真实毛孔、细小纹理、轻微肤色不均、眼下纹理、额头与表情细纹、真实胡茬边缘，以及室内实际光源造成的自然高光。不要磨皮、蜡像皮肤、塑料反光、过度锐化毛孔或时尚精修。

当前画面必须与上一张在空间区域、人物站位、裁切距离、背景方向和视觉重心上明显不同；保持同一个地点体系，但不能生成重复构图。

人物自然看向前置镜头，一只手在画外持手机，另一只手做与口播内容一致的克制手势。表情自然、略带真实情绪，不夸张搞笑，不表演过度。

不要电影感，不要商业广告布光，不要棚拍，不要卡通，不要CG，不要海报，不要文字，不要UI，不要额外人物抢镜。
```

## Human Realness

People should behave like real family members or ordinary customers:

- They pause before reacting.
- They glance at each other rather than constantly looking at camera.
- They do small concrete actions: open a box, touch a handlebar, pull a cloth, hand over keys, place tools, tighten a screw, hold a cup.
- They show micro-emotions: half-smile, confusion, awkward laugh, quiet disbelief, proud-but-shy, trying not to laugh.
- Wardrobe should be normal and specific, not model-like.

Prompt against AI/model behavior:

`no beauty filter, no perfect model faces, no fake perfect smiles, no actor-like overreaction, no commercial hero pose, no face drift, no duplicate family members`

## Banana Image Logic

For native UGC, Banana prompts should prioritize continuity over spectacle.

Recommended grids:

- 6 panels for one 8-12 second scene.
- 9 or 10 panels for one 15 second story.
- Crop the generated grid into 2-3 segment images for Jimeng.

Each panel should be a real phone frame:

- same house and camera feel
- same people and outfits
- same product
- action changes between panels
- background can move naturally, but main identity stays locked

## Jimeng Segment Logic

Keep each prompt compact, usually under 2K characters when the user has a limit.

Segment template:

```text
Strictly follow uploaded reference image. Same [location], same [main people], same [product]. Do not redesign or change identities.

9:16 vertical, [duration]. Real handheld smartphone video, ordinary U.S. home/yard, phone auto exposure, slight shake, imperfect framing, hard natural light, real shadows, subtle grain, no commercial look.

People/product lock: [short but specific identity and wardrobe/product details].

Action: [time-coded natural action beats].

Dialogue: [short casual local-market lines].

Sound: No music. [diegetic sounds only].

Negative: no subtitles, no UI, no app interface, no strange overlay, no beauty filter, no duplicate people, no face drift, no wrong product.
```

## Product Proof Rules

For tools and DIY products, the product must visibly do work.

Good proof:

- drill bit fully seated in screw slot
- screw goes through a visible bracket hole
- connection point is not hidden
- each proof shot uses a different screw/position
- result shot shows the finished useful object

Bad proof:

- drilling into blank wood
- drill blocks the screw and hole
- same close-up repeated
- tool only held for beauty shot
- product logo missing or product changes color/type

## Safety And Comedy

If a benchmark or draft includes hitting, falling, or impact comedy, keep it harmless:

- use a light tap, shoulder tap, startled reaction, or implied slap sound
- no injury, blood, crying, pain, or real violence
- keep it family-safe and TikTok-friendly

## Common Negative Additions

Use these when the model produces weird frames:

`no subtitles, no UI, no app interface, no phone screen overlay, no floating buttons, no progress bar, no strange icons, no text boxes, no duplicate people, no background guest becoming the main character, no extra product, no wrong product, no glossy AI skin`

## Texture Reference Only

If the user gives a video and says to reference its quality, texture, parameters, or 原生感, do not copy its plot. Copy only the production feel.

Use:

- handheld UGC phone movement
- phone auto exposure
- slight uneven brightness
- imperfect framing
- slight shake
- 35mm lens feel
- f/1.8 shallow depth of field
- subtle grain
- natural household, garage, patio, or backyard light
- realistic room tone and local diegetic sounds

Do not use unless asked:

- the reference video's characters
- the reference video's product
- the reference video's conflict
- the reference video's dialogue
- the reference video's full timeline

Always keep the user's requested plot as the source of truth.

## Single-Subject Native Story

When character drift is likely, reduce the cast.

Recommended story shape:

1. One adult hand gives the boy a key.
2. Adult voice says, "Go check the garage."
3. Camera follows the boy through the hallway.
4. Boy opens the garage.
5. Boy finds the product.
6. Boy inserts the key into the ignition/key slot and turns the key to start.
7. The left-side handlebar instrument/controller lights up, then the headlight turns on.
8. Boy reacts naturally.

Hard controls:

`Only the boy is fully visible. One adult hand only. No adult face. No adult body. No extra people.`

This pattern is useful for garage gifts, vehicle reveals, Father's Day surprises, and product-start scenes.
