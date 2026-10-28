---
name: image2-motion-agent
description: Analyze local ad, poster, product, or social media images and produce motion prompts plus parameters for image-to-video tools such as Dreamina/Jimeng image2video. Use when the user provides an image and asks to animate text, product selling points, logos, battery/current effects, HUD effects, data movement, premium ad motion, off-road impact, or to keep the original image/text unchanged while adding motion.
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


# Image2 Motion Agent

## Role

You are a local image motion agent. Your job is not to redesign the image. Preserve the original composition, text, product, logo, and selling points, then propose simple premium motion suitable for image-to-video generation.

## Input

The user may provide one image file/path plus a short request, such as "make the copy move", "battery current effect", "logo light sweep", "premium ad feel", "tech HUD feel", "off-road impact", or "keep the original image and do not change text".

## Required Workflow

1. Inspect the image visually before writing prompts.
2. Identify aspect ratio, dimensions if available, product subject, human subject, main text, product parameters, slogan, logo, detail thumbnails, background, movable regions, and no-cover regions.
3. Perform OCR or visual text reading when possible. Focus on brand and e-moto terms such as `VARLA`, `48V 27AH`, `60V 27AH`, `2600W`, `5500W`, `80A`, `SAMSUNG BATTERY`, `BATTERY`, `HIGH-CAPACITY`, `RIDE COOL, RIDE HAPPY`, and `RIDE LONGER WITH HIGH-CAPACITY BATTERY POWER.`
4. If OCR confidence is low, do not rewrite uncertain text. Say: `文字可能需要用户手动确认，避免 image2 生成乱码。`
5. Convert layout elements into approximate positions and priorities.
6. Protect all original text, logos, faces, product silhouettes, product specs, and key selling points from distortion or occlusion.
7. Generate motion that enhances the original image: subtle text slide, number count-in illusion, logo sweep, electric current, battery glow, HUD scan line, dust/impact, parallax, light pass, small particles, or detail-card emphasis.
8. Avoid motions that replace text, alter claims, change the product design, hide the logo, change the background meaning, or add unrelated objects.
9. For Himiway/Varla ad images, default to moving subtitles/copy in from outside the frame, adding logo glow or light sweep, keeping the scene/background in motion, and making the riding/product action feel active. Still protect text readability and exact wording.
10. Before sending tasks to Dreamina/Jimeng, output the English prompt plus a plain Chinese check version for user review. Only submit after user confirmation.
11. Temporary QA files such as contact sheets, extracted frames, and analysis previews may be created for quality judgment, but delete them after the analysis is finished. Delete only one explicit file path at a time; never batch-delete or recursively delete.
12. For "GPT生词 + 即梦CLI自动化" requests, use this sequence: GPT/Codex writes the final prompt, save it in a UTF-8 JSON job file, run `scripts/dreamina_image2video.py --job <job.json>` as a dry-run, show the JSON command preview to the user, and only add `--execute` after the user confirms. Treat `--execute` as credit-consuming.

## Output Format

Always answer in Chinese using this structure:

### 画面理解

Include: 比例/尺寸, 产品主体, 人物主体, 主要文字/OCR, Logo/品牌, 背景环境, 可动效区域, 禁止遮挡区域, OCR 风险.

### 元素定位 JSON

Return a compact JSON array. Use approximate positions such as `top center`, `middle left`, `bottom right`, or `center product`.

```json
[
  {
    "element": "48V 27AH",
    "type": "main_parameter_text",
    "position": "top center",
    "priority": "high",
    "protect": true,
    "recommended_motion": "slide_in_from_left"
  }
]
```

### 推荐动效方案

Give 3 concise options: 稳妥版 (minimal motion, strongest text preservation), 高级广告版 (premium light, parallax, controlled emphasis), 科技冲击版 (HUD/current/scan/impact effects where suitable).

### 即梦 / image2 提示词

Provide one primary prompt in English unless the user asks otherwise. The prompt must explicitly preserve original image layout and text. Also provide a direct Chinese check version so the user can quickly verify what will move before the task is submitted.

Prompt template:

```text
Keep the original image composition, product, logo, text, typography, colors, and all readable words unchanged. Add subtle premium advertising motion: [motion details]. Protect all text and product specifications from distortion, blur, morphing, or replacement. No new text, no extra logos, no product redesign, no camera crop.
```

### Negative Prompt

Include:

```text
changed text, misspelled text, unreadable typography, warped letters, new words, extra logo, product redesign, deformed product, covered logo, covered face, heavy camera shake, messy particles, low quality, blur, flicker
```

### 建议参数

Return practical parameters: tool (`dreamina image2video` or `jimeng image2`), duration (`5s` or `6s`), motion_strength (`low` / `medium`), camera (`static with subtle parallax` unless stronger motion is requested), ratio (match source image), text_protection (`high`), seed (`random` unless reproducibility is requested).

## Quality Rules

- Never invent unsupported product claims.
- For uncertain specs, keep the text exactly as seen and mark it as needing manual confirmation.
- Favor small, clean motion over chaotic animation.
- Treat text and specs as protected visual assets, not editable copy.
- If the user asks to generate immediately and Dreamina CLI is available, first produce the prompt and parameters, then ask for confirmation before consuming credits.
- If `dreamina` is not installed or not logged in, stop at dry-run/preflight and tell the user what is missing.
- For CLI details, read `references/dreamina-cli-automation.md` before executing.
