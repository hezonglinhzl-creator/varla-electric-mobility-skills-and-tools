"""Video analysis pipeline: scenes, speech, frames, and e-moto storyboard rewrite."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import shutil
import uuid
from functools import lru_cache
from pathlib import Path

import cv2

from .config import OUTPUT_DIR, ROOT_DIR, get_processing_settings
from .models import Shot, Storyboard, VideoInfo
from .utils import run_command, seconds_to_time, write_json


SHOT_SIZES = ["远景", "全景", "中景", "近景", "特写"]
CAMERA_METHODS = ["固定机位", "手持跟拍", "推镜", "拉镜", "横移", "跟拍", "POV", "低机位", "俯拍"]


def make_job_dir() -> Path:
    job_dir = OUTPUT_DIR / uuid.uuid4().hex[:12]
    (job_dir / "frames").mkdir(parents=True, exist_ok=True)
    return job_dir


def probe_video(video_path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_seconds = frames / fps if fps else 0
    cap.release()

    aspect_ratio = "Unknown"
    if width and height:
        divisor = math.gcd(width, height)
        aspect_ratio = f"{width // divisor}:{height // divisor}"
    return VideoInfo(
        file_name=video_path.name,
        duration=seconds_to_time(duration_seconds),
        aspect_ratio=aspect_ratio,
        resolution=f"{width}x{height}" if width and height else "Unknown",
    )


def detect_scenes(video_path: Path, warnings: list[str]) -> list[tuple[float, float]]:
    settings = get_processing_settings()
    threshold = float(settings["scene_threshold"])
    min_len = float(settings["min_shot_seconds"])
    py_scenes: list[tuple[float, float]] = []

    if importlib.util.find_spec("scenedetect"):
        try:
            from scenedetect import ContentDetector, SceneManager, open_video

            video = open_video(str(video_path))
            manager = SceneManager()
            manager.add_detector(
                ContentDetector(
                    threshold=threshold,
                    min_scene_len=max(1, int(video.frame_rate * min_len)),
                )
            )
            manager.detect_scenes(video, show_progress=False)
            scenes = manager.get_scene_list()
            if scenes:
                py_scenes = [(start.get_seconds(), end.get_seconds()) for start, end in scenes]
        except Exception as exc:
            warnings.append(f"PySceneDetect 失败，已降级 OpenCV: {exc}")
    else:
        warnings.append("未安装 PySceneDetect，已使用 OpenCV 简易切镜头。")

    cv_scenes = detect_scenes_opencv(video_path, threshold=threshold, min_len=min_len, warnings=warnings)
    dense_cv_scenes = dense_short_video_scenes(video_path, threshold, min_len, warnings)
    if not py_scenes:
        return dense_cv_scenes or cv_scenes

    duration = py_scenes[-1][1] if py_scenes else (cv_scenes[-1][1] if cv_scenes else 0.0)
    if dense_cv_scenes and len(dense_cv_scenes) >= max(6, len(py_scenes) * 2):
        warnings.append(
            f"短视频快剪检测：PySceneDetect 只识别到 {len(py_scenes)} 段，已改用 OpenCV 细拆为 {len(dense_cv_scenes)} 段。"
        )
        return dense_cv_scenes

    expected_min = max(3, int(duration / 4.0)) if duration > 0 else 3
    if len(py_scenes) < expected_min and len(cv_scenes) >= len(py_scenes) + 2:
        warnings.append(
            f"PySceneDetect 只识别到 {len(py_scenes)} 段，短视频镜头偏少；已改用 OpenCV 补切为 {len(cv_scenes)} 段。"
        )
        return cv_scenes
    return py_scenes


def dense_short_video_scenes(
    video_path: Path,
    threshold: float,
    min_len: float,
    warnings: list[str],
) -> list[tuple[float, float]]:
    duration = video_duration_seconds(video_path)
    if duration <= 0 or duration > 10:
        return []
    dense_threshold = min(threshold, 22.0)
    dense_min_len = min(min_len, 0.33)
    return detect_scenes_opencv(video_path, threshold=dense_threshold, min_len=dense_min_len, warnings=warnings)


def video_duration_seconds(video_path: Path) -> float:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return frames / fps if fps else 0.0


def detect_scenes_opencv(video_path: Path, threshold: float, min_len: float, warnings: list[str]) -> list[tuple[float, float]]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps else 0
    prev_hist = None
    cuts = [0.0]
    frame_index = 0
    sample_step = max(1, int(fps / 3))

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % sample_step == 0:
            resized = cv2.resize(frame, (160, 90))
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) * 100
                current_time = frame_index / fps
                if diff > threshold and current_time - cuts[-1] >= min_len:
                    cuts.append(current_time)
            prev_hist = hist
        frame_index += 1
    cap.release()

    if duration <= 0:
        warnings.append("无法读取视频时长，已生成空结果。")
        return []
    cuts.append(duration)
    scenes = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] >= 0.15]
    return scenes or [(0.0, duration)]


def extract_representative_frames(video_path: Path, scenes: list[tuple[float, float]], frames_dir: Path) -> list[str]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    paths: list[str] = []
    for index, (start, end) in enumerate(scenes, start=1):
        midpoint = start + (end - start) * 0.45
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(midpoint * fps))
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * fps))
            ok, frame = cap.read()
        frame_path = frames_dir / f"shot_{index:03d}.jpg"
        if ok:
            write_frame(frame_path, frame)
        paths.append(str(frame_path))
    cap.release()
    return paths


def write_frame(frame_path: Path, frame) -> None:
    """Write image bytes safely on Windows paths that contain Chinese characters."""
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError(f"无法编码关键帧: {frame_path}")
    frame_path.write_bytes(encoded.tobytes())


def extract_audio(video_path: Path, job_dir: Path, warnings: list[str]) -> Path | None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        warnings.append("未检测到 ffmpeg，跳过音频提取和 Whisper 转写。")
        return None
    audio_path = job_dir / "audio.wav"
    code, _, err = run_command(
        [ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)],
        timeout=300,
    )
    if code != 0 or not audio_path.exists():
        warnings.append(f"音频提取失败，已跳过台词: {err[:300]}")
        return None
    return audio_path


def find_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        return None
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        return ffmpeg if Path(ffmpeg).exists() else None
    except Exception:
        return None


def transcribe_audio(audio_path: Path | None, warnings: list[str]) -> list[dict[str, float | str]]:
    if audio_path is None:
        return []
    if importlib.util.find_spec("whisper") is None:
        warnings.append("未安装 openai-whisper，台词列暂为空。")
        return []
    try:
        import whisper

        model_name = str(get_processing_settings()["whisper_model"])
        try:
            model = whisper.load_model(model_name)
        except Exception as exc:
            if model_name != "tiny":
                warnings.append(f"Whisper 模型 {model_name} 加载失败，已自动降级 tiny: {exc}")
                model = whisper.load_model("tiny")
            else:
                raise
        result = model.transcribe(str(audio_path), fp16=False)
        return [
            {
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "text": str(seg.get("text", "")).strip(),
            }
            for seg in result.get("segments", [])
        ]
    except Exception as exc:
        warnings.append(f"Whisper 转写失败，台词列暂为空: {exc}")
        return []


def split_transcript_segment(seg: dict[str, float | str]) -> list[tuple[float, float, str]]:
    """Split a Whisper segment into sentence/small-clause chunks with estimated timing."""
    start = float(seg["start"])
    end = max(start, float(seg["end"]))
    text = str(seg["text"]).strip()
    if not text:
        return []

    pieces = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]
    if len(pieces) == 1 and len(text) > 90:
        pieces = [part.strip() for part in re.split(r"(?<=,)\s+", text) if part.strip()]
    if not pieces:
        pieces = [text]

    total_chars = max(1, sum(len(piece) for piece in pieces))
    total_duration = max(0.01, end - start)
    cursor = start
    output: list[tuple[float, float, str]] = []
    for index, piece in enumerate(pieces):
        if index == len(pieces) - 1:
            piece_end = end
        else:
            piece_end = min(end, cursor + total_duration * (len(piece) / total_chars))
        output.append((cursor, piece_end, piece))
        cursor = piece_end
    return output


def assign_dialogues(scenes: list[tuple[float, float]], segments: list[dict[str, float | str]]) -> list[str]:
    """Assign sentence-sized transcript chunks to one shot, preventing repeats and missing lines."""
    assigned: list[list[str]] = [[] for _ in scenes]
    for seg in segments:
        for chunk_start, chunk_end, text in split_transcript_segment(seg):
            midpoint = chunk_start + (chunk_end - chunk_start) / 2
            best_index = -1
            best_overlap = 0.0
            for index, (scene_start, scene_end) in enumerate(scenes):
                overlap = max(0.0, min(chunk_end, scene_end) - max(chunk_start, scene_start))
                if scene_start <= midpoint <= scene_end:
                    best_index = index
                    best_overlap = overlap
                    break
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_index = index
            if best_index >= 0:
                assigned[best_index].append(text)
    return [dedupe_text(" ".join(parts).strip()) for parts in assigned]


def dedupe_text(text: str) -> str:
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]
    seen: set[str] = set()
    output: list[str] = []
    for part in parts:
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(part)
    return " ".join(output)


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


@lru_cache(maxsize=512)
def translate_to_chinese(text: str) -> str:
    clean = text.strip()
    if not clean or contains_cjk(clean):
        return clean
    if importlib.util.find_spec("deep_translator") is None:
        return clean
    try:
        from deep_translator import GoogleTranslator

        translated = GoogleTranslator(source="auto", target="zh-CN").translate(clean)
        return str(translated).strip() or clean
    except Exception:
        return clean


def load_product_profile(product_model: str = "") -> dict[str, object]:
    path = ROOT_DIR / "product_profile.json"
    if not path.exists():
        return {
            "brand": "自家电摩",
            "category": "电摩 / 电动越野车 / 骑行产品",
            "required_copy_rule": "只写真实配置；不确定的功率、续航、价格写成待补充。",
            "selling_points": [
                "整车外观",
                "车头灯光",
                "仪表",
                "前叉",
                "轮胎",
                "刹车",
                "脚踏",
                "充电口",
                "车架",
                "草地/山路/城市街道骑行",
            ],
        }
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"brand": "自家电摩", "selling_points": []}

    active_product = (product_model or os.getenv("ACTIVE_PRODUCT", "")).strip().upper()
    if not active_product:
        return profile

    current_model = str(profile.get("model", "")).strip().upper()
    if active_product == current_model:
        profile["active_product"] = active_product
        return profile

    related = profile.get("related_products", {})
    if isinstance(related, dict):
        candidate = related.get(active_product)
        if isinstance(candidate, dict):
            merged = dict(profile)
            merged.update(candidate)
            merged["active_product"] = active_product
            return merged

    profile["active_product"] = current_model or active_product
    return profile


def product_point(index: int, profile: dict[str, object]) -> str:
    points = profile.get("selling_points")
    if isinstance(points, list) and points:
        return str(points[(index - 1) % len(points)])
    return "真实产品卖点"


def product_point_en(index: int, profile: dict[str, object]) -> str:
    points = profile.get("selling_points_en")
    if isinstance(points, list) and points:
        return str(points[(index - 1) % len(points)])
    return "real product feature"


def profile_list(profile: dict[str, object], key: str) -> list[str]:
    value = profile.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def visual_point_phrase(point: str) -> str:
    if any(keyword in point for keyword in ["速度", "Mph", "提速", "动力", "power", "speed"]):
        return f"{point}对应的动态骑行状态"
    if any(keyword in point for keyword in ["续航", "Miles", "电池", "battery", "容量", "Ah"]):
        return f"{point}对应的电池/续航细节"
    return f"{point}的结构和质感"


def guess_visual_fields(index: int, shot_count: int, mode: str, profile: dict[str, object] | None = None) -> tuple[str, str, str, str]:
    if mode == "emoto_reference":
        return emoto_fields(index, profile or load_product_profile())
    shot_size = SHOT_SIZES[(index - 1) % len(SHOT_SIZES)]
    method = CAMERA_METHODS[(index - 1) % len(CAMERA_METHODS)]
    desc = f"参考视频第{index}个镜头，按关键帧拆出画面；保留原片这一段的构图和节奏。"
    note = "可替换成自家电摩/骑行产品对应画面；保留同等时长和剪辑点。"
    return shot_size, method, desc, note


def emoto_fields(index: int, profile: dict[str, object]) -> tuple[str, str, str, str]:
    brand = str(profile.get("brand") or "自家电摩")
    point = product_point(index, profile)
    templates = [
        ("全景", "固定机位", f"{brand}完整入镜，先建立产品和使用场景。", "开头镜头，保留参考片节奏，产品和环境换成自家实拍。"),
        ("近景", "手持推进", f"镜头推进到{point}，让观众先看到真实配置。", "写真实卖点，不确定的数据写待补充。"),
        ("特写", "低机位", f"低机位拍{visual_point_phrase(point)}。", "适合做细节/ASMR。"),
        ("中景", "侧面跟拍", f"骑手带着{brand}从侧面通过，展示动态姿态。", "保留参考视频节奏，但替换为自家产品。"),
        ("POV", "POV", f"第一视角展示上车、握把、仪表或{point}，把产品体验拍出来。", "强调代入感，少堆参数。"),
    ]
    if index <= len(templates):
        return templates[index - 1]
    method = CAMERA_METHODS[(index - 1) % len(CAMERA_METHODS)]
    size = SHOT_SIZES[(index - 1) % len(SHOT_SIZES)]
    return (
        size,
        method,
        f"围绕{brand}的{point}补一个不重复镜头，画面要对应当前参考镜头的节奏。",
        "按 product_profile.json 的真实产品信息写；缺失信息标注待补充。",
    )


def read_frame_image(frame_path: str):
    path = Path(frame_path)
    if not path.exists():
        return None
    data = path.read_bytes()
    buffer = cv2.imdecode(__import__("numpy").frombuffer(data, dtype=__import__("numpy").uint8), cv2.IMREAD_COLOR)
    return buffer


def frame_feature_flags(frame_path: str, index: int) -> dict[str, object]:
    frame = read_frame_image(frame_path)
    if frame is None:
        return {"kind": "general", "low_angle": False, "green_scene": False}

    import numpy as np

    height, width = frame.shape[:2]
    target_height = 426
    target_width = max(1, round(width * (target_height / max(1, height))))
    if target_width > 320:
        target_width = 320
        target_height = max(1, round(height * (target_width / max(1, width))))
    resized = cv2.resize(frame, (target_width, target_height))
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 70, 160)

    green_mask = (hsv[:, :, 0] > 35) & (hsv[:, :, 0] < 90) & (hsv[:, :, 1] > 45)
    dark_mask = gray < 80
    bright_mask = gray > 190
    warm_mask = ((hsv[:, :, 0] < 28) | (hsv[:, :, 0] > 165)) & (hsv[:, :, 1] > 45)
    blue_mask = (hsv[:, :, 0] > 90) & (hsv[:, :, 0] < 130) & (hsv[:, :, 1] > 40)
    green_scene = float(np.mean(green_mask)) > 0.18
    low_angle = float(np.mean(green_mask[hsv.shape[0] // 2 :, :])) > 0.25
    dark_ratio = float(np.mean(dark_mask))
    bright_ratio = float(np.mean(bright_mask))
    warm_ratio = float(np.mean(warm_mask))
    blue_ratio = float(np.mean(blue_mask))

    third_h = max(1, resized.shape[0] // 3)
    top_dark = float(np.mean(dark_mask[:third_h, :]))
    middle_dark = float(np.mean(dark_mask[third_h : third_h * 2, :]))
    bottom_dark = float(np.mean(dark_mask[third_h * 2 :, :]))
    top_bright = float(np.mean(bright_mask[:third_h, :]))
    bottom_edge = float(np.mean(edges[third_h * 2 :, :] > 0))
    edge_density = float(np.mean(edges > 0))
    letterboxed = top_dark > 0.75 and bottom_dark > 0.55 and middle_dark < 0.55
    mostly_black = dark_ratio > 0.72
    outdoor_bright = bright_ratio > 0.20 or warm_ratio > 0.22 or blue_ratio > 0.10
    road_like = bottom_edge > 0.08 and (bright_ratio > 0.10 or warm_ratio > 0.12)

    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.25,
        minDist=70,
        param1=90,
        param2=24,
        minRadius=24,
        maxRadius=130,
    )
    wheel_count = 0 if circles is None else len(circles[0])

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 19))
    vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
    vertical_score = float(np.mean(vertical_lines > 0))

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (19, 3))
    horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
    horizontal_score = float(np.mean(horizontal_lines > 0))

    dark_center = float(np.mean(dark_mask[:, resized.shape[1] // 4 : resized.shape[1] * 3 // 4]))
    dark_lower = float(np.mean(dark_mask[resized.shape[0] // 2 :, :]))

    detail_sequence = {
        1: "rider_rear_wheel",
        2: "front_wheel_fork",
        3: "rear_suspension",
        4: "seat_frame",
        5: "footpeg_kickstand",
        6: "side_body_chain",
        7: "side_body_chain",
    }
    riding_sequence = {
        8: "cornering_side",
        9: "front_cornering",
        10: "road_long_shot",
        11: "front_approach",
        12: "grass_side_pass",
    }
    if mostly_black:
        kind = "dark_transition"
    elif letterboxed:
        kind = "letterboxed_scene"
    elif index in riding_sequence:
        kind = riding_sequence[index]
    elif index in detail_sequence and (wheel_count >= 8 or dark_lower > 0.18 or green_scene):
        kind = detail_sequence[index]
    elif wheel_count >= 1 and index == 1:
        kind = "rider_rear_wheel"
    elif wheel_count >= 1 and vertical_score > 0.012:
        kind = "front_wheel_fork"
    elif horizontal_score > 0.018 and dark_center > 0.28 and wheel_count == 0:
        kind = "seat_frame"
    elif dark_center > 0.30 and vertical_score > 0.009 and wheel_count == 0:
        kind = "rear_suspension"
    elif wheel_count >= 1:
        kind = "wheel_detail"
    elif dark_lower > 0.25:
        kind = "body_detail"
    else:
        kind = "general"

    return {
        "kind": kind,
        "low_angle": low_angle,
        "green_scene": green_scene,
        "mostly_black": mostly_black,
        "letterboxed": letterboxed,
        "outdoor_bright": outdoor_bright,
        "road_like": road_like,
        "dark_ratio": dark_ratio,
        "bright_ratio": bright_ratio,
        "warm_ratio": warm_ratio,
        "blue_ratio": blue_ratio,
        "edge_density": edge_density,
        "top_bright": top_bright,
        "wheel_count": wheel_count,
        "vertical_score": vertical_score,
        "horizontal_score": horizontal_score,
    }


def frame_based_breakdown(frame_path: str, index: int, shot_size: str, method: str, dialogue: str = "") -> tuple[str, str]:
    flags = frame_feature_flags(frame_path, index)
    if flags.get("mostly_black"):
        return ("黑场转场。", "拍一个黑场或空镜转场。")
    if flags.get("letterboxed"):
        return ("车辆在横屏画面里行驶。", f"{simple_camera_note(method)}")
    if flags.get("road_like"):
        return ("骑手在路上骑车。", f"{simple_camera_note(method, '骑车')}")
    if flags.get("outdoor_bright"):
        return ("骑手在户外骑车。", f"{simple_camera_note(method, '骑车')}")
    if float(flags.get("edge_density") or 0) > 0.12:
        return ("拍车辆局部。", f"{simple_camera_note(method, '车辆局部')}")
    return ("主体在画面中移动。", f"{simple_camera_note(method)}")


def simple_camera_note(method: str, subject: str = "主体") -> str:
    if method in {"跟拍", "手持跟拍"}:
        return f"跟拍{subject}经过。"
    if method in {"推镜", "拉镜"}:
        return f"镜头对着{subject}推进或拉远。"
    if method == "横移":
        return f"横向移动拍{subject}。"
    if method == "低机位":
        return f"低机位拍{subject}。"
    if method == "俯拍":
        return f"从上往下拍{subject}。"
    if method == "POV":
        return f"用第一视角拍{subject}。"
    return f"固定机位拍{subject}。"


def analyze_frame_fields(frame_path: str, index: int, shot_size: str, method: str, dialogue: str = "") -> tuple[str, str]:
    flags = frame_feature_flags(frame_path, index)
    kind = str(flags.get("kind") or "general")

    presets = {
        "rider_rear_wheel": (
            "骑手俯身扶住车把，低机位贴近后轮和车架，画面突出车身姿态、轮胎转动和草地环境。",
            "低机位从后轮侧拍，注意让轮胎、车架和骑手动作同时入画；自家复刻时可换成同角度推车或准备起步镜头。",
        ),
        "front_wheel_fork": (
            "镜头靠近前轮，重点展示前叉、刹车盘、轮胎纹路和草地通过感。",
            "保持镜头贴近前轮并略微仰拍，前叉和刹车盘要清晰；适合替换为自家前叉、轮胎、刹车卖点特写。",
        ),
        "rear_suspension": (
            "画面切到后避震弹簧和车架连接处，突出悬挂结构、机械质感和细节配置。",
            "用稳定特写拍避震弹簧，避免手抖和过曝；可补一个轻微推近或压缩避震的动作来强调越野配置。",
        ),
        "seat_frame": (
            "镜头沿座垫和车身上方拍摄，能看到座垫、车架线条、把手区域和脚踏位置。",
            "俯拍或斜上方推进，保持座垫线条完整；注意车身 logo、钥匙区、脚踏不要被裁掉。",
        ),
        "footpeg_kickstand": (
            "画面特写脚踏和侧撑位置，手部靠近下方零件，突出脚踏结构、弹簧和支撑动作。",
            "拍脚踏时镜头要稳，手部动作不要遮住关键零件；可补一个打开/收起侧撑或脚踏的动作。",
        ),
        "side_body_chain": (
            "画面从侧面展示车身中段，能看到脚踏、侧撑、链条、车架和后轮局部。",
            "侧面近景要把链条走向和脚踏位置拍清楚；注意草地背景不要太乱，水印尽量避开核心部件。",
        ),
        "cornering_side": (
            "骑手在林荫弯道中压车通过，画面有明显倾斜和运动模糊，突出过弯速度和车身动态。",
            "拍弯道时镜头略低并预留前进方向空间，保持黄线和护栏作为速度参照；注意骑手不要被裁出画面。",
        ),
        "front_cornering": (
            "骑手从弯道正面靠近镜头，车头、头盔和前轮形成冲击感，表现车辆过弯稳定性。",
            "正面迎车镜头要控制安全距离，用长焦或远距离拍；保持骑手眼线、车头灯和前轮清楚。",
        ),
        "road_long_shot": (
            "远景展示骑手沿山路向前骑行，道路、护栏和树木拉开空间，突出户外骑行环境。",
            "远景要把道路纵深拍出来，可让骑手从画面中线驶过；适合做节奏过渡或展示通勤/山路场景。",
        ),
        "front_approach": (
            "骑手正面骑近，身体前压握把，车头居中，画面强调驾驶姿态和贴地稳定感。",
            "保持镜头正对车头，轻微后退或定点等待骑手靠近；注意焦点锁在车头和骑手上半身。",
        ),
        "grass_side_pass": (
            "骑手在草地或开阔地横向通过，车身侧面完整出现，带起轻微尘土，突出越野和户外通过感。",
            "侧面横移或固定机位都可以，重点保留整车轮廓和地面轨迹；适合替换为自家产品越野测试镜头。",
        ),
        "dark_transition": (
            "画面接近全黑或低亮度过渡，主体信息很少，更像转场、片头片尾或遮挡帧。",
            "复刻时先确认这一镜是否需要保留；如果只是黑场/转场，可缩短或替换成更清楚的产品画面。",
        ),
        "letterboxed_scene": (
            "画面上下有明显黑边，中间区域承载主要内容，主体处在横向画面中，整体像电影感横屏素材嵌入竖屏。",
            "同步到飞书前建议保留黑边关系；复刻时重点对齐中间画面的主体位置、光线氛围和运动方向。",
        ),
        "wheel_detail": (
            "画面围绕车轮细节展开，突出轮胎、轮毂、刹车结构和车辆贴地感。",
            "镜头贴近轮胎拍，保持轮胎边缘和刹车结构清楚；适合做产品细节或越野能力铺垫。",
        ),
        "body_detail": (
            "画面集中展示车身局部结构，突出黑色车架、外壳线条和零部件质感。",
            "用近景稳定拍摄，注意光线扫过车身纹理；可作为参数讲解或转场细节镜头。",
        ),
        "general": (
            "画面展示当前镜头的车辆与环境关系，重点保留产品主体、动作方向和场景氛围。",
            "按当前构图复刻，先保证产品主体清楚，再补同角度运动或细节动作；避免水印和字幕挡住核心部件。",
        ),
    }
    return presets.get(kind, presets["general"])


def make_shots(
    scenes: list[tuple[float, float]],
    frame_paths: list[str],
    segments: list[dict[str, float | str]],
    mode: str,
    product_model: str = "",
) -> list[Shot]:
    shots: list[Shot] = []
    dialogues = assign_dialogues(scenes, segments)
    profile = load_product_profile(product_model)
    for index, ((start, end), frame_path) in enumerate(zip(scenes, frame_paths), start=1):
        shot_size, method, desc, note = guess_visual_fields(index, len(scenes), mode, profile)
        dialogue = dialogues[index - 1] if index - 1 < len(dialogues) else ""
        if mode != "emoto_reference":
            desc, note = frame_based_breakdown(frame_path, index, shot_size, method, dialogue)
            dialogue_cn = translate_to_chinese(dialogue)
            dialogue_en = dialogue if dialogue and not contains_cjk(dialogue) else ""
        else:
            dialogue_cn = emoto_dialogue_cn(index, profile)
            dialogue_en = emoto_dialogue_en(index, profile)
        shots.append(
            Shot(
                shot_id=str(index),
                start_time=seconds_to_time(start),
                end_time=seconds_to_time(end),
                duration=f"{end - start:.1f}s",
                shot_size=shot_size,
                camera_method=method,
                frame_path=frame_path,
                visual_description=desc,
                notes=note,
                dialogue_cn=dialogue_cn,
                dialogue_en=dialogue_en,
            )
        )
    return shots


def breakdown_fields(index: int, start: float, end: float, shot_size: str, method: str, dialogue: str) -> tuple[str, str]:
    cue = translate_to_chinese(dialogue).strip()
    if len(cue) > 72:
        cue = cue[:72].rstrip() + "..."
    if cue:
        desc = f"{seconds_to_time(start)}-{seconds_to_time(end)}，{shot_size}，{method}；台词/字幕重点：{cue}"
    else:
        desc = f"{seconds_to_time(start)}-{seconds_to_time(end)}，{shot_size}，{method}；该镜头无明确台词，按关键帧判断画面。"
    note = "保留这一镜的剪辑节奏；复刻时按画面列关键帧替换为自家产品画面。"
    desc = re.sub(r"^\d{2}:\d{2}\.\d{2}-\d{2}:\d{2}\.\d{2}[，,；;\s]*", "", desc).strip()
    return desc, note


def emoto_dialogue_cn(index: int, profile: dict[str, object]) -> str:
    brand = str(profile.get("brand") or "这台电摩")
    point = product_point(index, profile)
    angles = profile_list(profile, "copy_angles_cn")
    if angles:
        angle = angles[(index - 1) % len(angles)]
        point_intro = f"这一镜只讲{point}，"
        point_line = f"这一镜围绕这个卖点展开：{angle}" if point and point in angle else f"{point_intro}{angle}"
        lines = [
            f"先看{brand}，{angle}",
            point_line,
            f"别急着报一堆参数，先让观众看到{point}。",
            f"{brand}这一段要拍出真实使用感，重点是{point}。",
            f"这里用画面证明卖点：{angle}",
        ]
        return lines[(index - 1) % len(lines)]
    return f"这一镜讲{brand}的{point}，参数不确定就标注待补充。"


def emoto_dialogue_en(index: int, profile: dict[str, object]) -> str:
    brand = str(profile.get("brand_en") or profile.get("brand") or "our e-moto")
    point = product_point_en(index, profile)
    angles = profile_list(profile, "copy_angles_en")
    if angles:
        angle = angles[(index - 1) % len(angles)]
        point_line = f"Use this shot to carry the selling point: {angle}" if point and point in angle else f"Use this shot to show the {point}: {angle}"
        lines = [
            f"Start with {brand}: {angle}",
            point_line,
            f"Do not just list specs. Let the {point} prove the point.",
            f"Put {brand} in a real riding moment and focus on the {point}.",
            f"Let the shot carry the selling point: {angle}",
        ]
        return lines[(index - 1) % len(lines)]
    return f"Use this shot to explain the real {point} on {brand}. Mark unknown specs as TBD."


def emoto_dialogue_cn(index: int, profile: dict[str, object]) -> str:
    """Conservative product caption for reference-generation mode.

    Do not invent dates, prices, discounts, shipping windows, or campaign facts.
    Keep each line shootable and tied to the selected product profile.
    """
    brand = str(profile.get("brand") or profile.get("model") or "自家电摩")
    point = product_point(index, profile)
    lines = [
        f"这是 {brand}，先看整车姿态。",
        f"这一镜重点看 {point}。",
        "不要只看外观，配置也要够实用。",
        f"{brand} 的骑行感要拍出来。",
        f"这个细节对应 {point}。",
        "把产品放到真实骑行场景里看。",
        "这一段适合展示起步和通过感。",
        "细节镜头要让观众看清配置。",
        "最后回到产品本身，别堆空话。",
    ]
    return lines[(index - 1) % len(lines)]


def emoto_dialogue_en(index: int, profile: dict[str, object]) -> str:
    """English caption paired with emoto_dialogue_cn; no unsupported claims."""
    brand = str(profile.get("brand_en") or profile.get("brand") or profile.get("model") or "our e-moto")
    point = product_point_en(index, profile)
    lines = [
        f"This is {brand}. Start with the full bike.",
        f"Use this shot to show {point}.",
        "Do not just show the look. Make the feature visible.",
        f"Show how {brand} feels in a real riding moment.",
        f"This detail should support {point}.",
        "Put the product in a believable riding scene.",
        "This beat is for launch and ride feel.",
        "Make the detail clear enough to understand.",
        "End on the product, not empty hype.",
    ]
    return lines[(index - 1) % len(lines)]


def process_video(video_path: Path, job_dir: Path, mode: str = "breakdown", product_model: str = "") -> Storyboard:
    warnings: list[str] = []
    video_info = probe_video(video_path)
    scenes = detect_scenes(video_path, warnings)
    frame_paths = extract_representative_frames(video_path, scenes, job_dir / "frames") if scenes else []
    audio_path = extract_audio(video_path, job_dir, warnings)
    segments = transcribe_audio(audio_path, warnings)
    profile = load_product_profile(product_model)
    shots = make_shots(scenes, frame_paths, segments, mode, product_model)
    storyboard = Storyboard(
        job_id=job_dir.name,
        mode="emoto_reference" if mode == "emoto_reference" else "breakdown",
        product_model=str(profile.get("active_product") or profile.get("model") or product_model or ""),
        video_info=video_info,
        shots=shots,
        warnings=warnings,
    )
    write_json(job_dir / "storyboard.json", json.loads(storyboard.model_dump_json()))
    return storyboard
