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
