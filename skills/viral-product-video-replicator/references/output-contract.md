# Output Contract

Use this structure for full production packages.

## 1. 爆款结构拆解

Include:

- Video type
- Target audience
- Hook
- Emotional promise
- Proof mechanism
- Conversion mechanism
- Originality warning

## 2. 本地分镜表

Use a table:

| Shot | Time | Benchmark Picture | Function | Replacement Visual | On-Screen Text | Voiceover | Jimeng Input |
|---|---:|---|---|---|---|---|---|

For `Benchmark Picture`, describe the visual if no image is embedded.

## 3. 产品替换方案

Include:

- Product identity phrase
- Core selling points
- Visual proof points
- Required product assets
- Scenes where product must appear
- Scenes where product should not appear

## 4. 欧美真人感人物参数

Provide:

```json
{
  "character_id": "western_host_001",
  "role": "host",
  "age_range": "28-35",
  "appearance": "",
  "wardrobe": "",
  "personality": "",
  "continuity_phrase": "",
  "negative_prompt": ""
}
```

## 5. 成片脚本

Separate:

- Narration
- Subtitle text
- On-screen label text
- CTA

## 6. 即梦提示词

For each shot:

```text
Shot 01 / 3s / 9:16
Prompt:
...
Negative:
...
Reference assets:
...
```

## 7. TikTok/INS 文案

Include:

- TikTok caption
- Instagram caption
- Hashtags
- First comment idea
- Pinned comment idea

## 8. 复用记忆

Include:

```json
{
  "product_memory": {},
  "character_memory": {},
  "style_memory": {},
  "benchmark_pattern_memory": {}
}
```

