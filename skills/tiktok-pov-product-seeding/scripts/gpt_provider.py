from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENAI_API_URL = "https://api.openai.com/v1/responses"


class GptProviderError(RuntimeError):
    pass


@dataclass
class GptStoryPack:
    beats: list[dict[str, Any]]
    compliance_summary: str
    raw_response: dict[str, Any]


def _http_post_json(url: str, payload: dict[str, Any], api_key: str, timeout: int = 120) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GptProviderError(f"OpenAI HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise GptProviderError(f"OpenAI connection failed: {exc}") from exc


def _extract_output_text(payload: dict[str, Any]) -> str:
    text = payload.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                value = content.get("text")
                if isinstance(value, str):
                    parts.append(value)
    joined = "".join(parts).strip()
    if not joined:
        raise GptProviderError("OpenAI response did not contain output_text.")
    return joined


def _build_prompt(
    product_name: str,
    style_preset: str,
    duration: float,
    product_info: dict[str, Any],
    beat_skeleton: list[dict[str, Any]],
) -> str:
    safe_product_info = json.dumps(product_info, ensure_ascii=False, indent=2) if product_info else "{}"
    safe_beats = json.dumps(beat_skeleton, ensure_ascii=False, indent=2)
    return (
        "You are writing a TikTok POV product seeding storyboard package.\n"
        "Return valid JSON only.\n\n"
        "Goal:\n"
        "- first-person creator tone\n"
        "- calm, conversational, native American English\n"
        "- cinematic POV, product detail focused, mechanical aesthetic\n"
        "- realistic, immersive, TikTok-native pacing\n"
        "- non-commercial tone\n\n"
        "Hard rules:\n"
        "- do not exaggerate\n"
        "- avoid dangerous or stunt framing\n"
        "- avoid these terms: dirt bike, motorcycle, motocross, crazy fast, insane speed, dangerous, race, wheelie, top speed, max speed\n"
        "- prefer: off-road bike, off-road machine, powerful, smooth, solid, well built, performance, fun ride\n"
        "- subtitle_segments must be phrase-based, short, breathable, not one word per line unless a single emphasis word is necessary\n"
        "- every beat must align to one visual beat\n"
        "- keep copy natural, not like a spec sheet\n\n"
        f"Product name: {product_name}\n"
        f"Style preset: {style_preset}\n"
        f"Total duration seconds: {duration}\n"
        f"Product info JSON:\n{safe_product_info}\n\n"
        f"Beat skeleton JSON:\n{safe_beats}\n\n"
        "Return this JSON shape:\n"
        "{\n"
        '  "beats": [\n'
        "    {\n"
        '      "id": 1,\n'
        '      "type": "hook",\n'
        '      "voiceover": "",\n'
        '      "zh": "",\n'
        '      "subtitle_segments": ["", ""],\n'
        '      "visual_action": "",\n'
        '      "audio_intent": "",\n'
        '      "notes": ""\n'
        "    }\n"
        "  ],\n"
        '  "compliance_summary": ""\n'
        "}\n"
    )


def generate_story_pack(
    *,
    api_key: str,
    model: str,
    product_name: str,
    style_preset: str,
    duration: float,
    product_info: dict[str, Any],
    beat_skeleton: list[dict[str, Any]],
) -> GptStoryPack:
    prompt = _build_prompt(
        product_name=product_name,
        style_preset=style_preset,
        duration=duration,
        product_info=product_info,
        beat_skeleton=beat_skeleton,
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "text": {
            "format": {
                "type": "json_object",
            }
        },
    }
    raw_response = _http_post_json(OPENAI_API_URL, payload, api_key=api_key)
    output_text = _extract_output_text(raw_response)
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise GptProviderError(f"OpenAI returned non-JSON content: {output_text[:400]}") from exc
    beats = parsed.get("beats")
    if not isinstance(beats, list) or not beats:
        raise GptProviderError("OpenAI JSON did not include a non-empty beats array.")
    compliance_summary = str(parsed.get("compliance_summary") or "").strip()
    return GptStoryPack(beats=beats, compliance_summary=compliance_summary, raw_response=raw_response)


def load_openai_api_key(env_name: str) -> str | None:
    value = os.getenv(env_name, "").strip()
    return value or None
