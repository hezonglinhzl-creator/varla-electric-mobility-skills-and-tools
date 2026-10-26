"""FastAPI entrypoint for the local video storyboard tool."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import OUTPUT_DIR, ROOT_DIR, STATIC_DIR
from .exporters import export_csv, export_excel, export_feishu_bundle, export_markdown, export_word, export_word_batch
from .feishu_sync import sync_all, test_bitable_connection, test_doc_connection
from .models import Storyboard, SyncRequest
from .utils import read_json, safe_stem, write_json
from .video_processing import make_job_dir, process_video


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
CACHE_REPORT_DIR = ROOT_DIR / "cache_reports"
THUMB_MAX_WIDTH = 128
THUMB_MAX_HEIGHT = 190

app = FastAPI(title="本地视频拆镜头脚本工具", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


def ensure_inside_outputs(path: Path) -> Path:
    resolved = path.resolve()
    output_root = OUTPUT_DIR.resolve()
    if resolved != output_root and output_root not in resolved.parents:
        raise HTTPException(status_code=400, detail="拒绝清理项目 outputs 以外的路径")
    return resolved


def output_cache_report() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, object]] = []
    total_images = 0
    total_bytes = 0
    for job_dir in sorted([item for item in OUTPUT_DIR.iterdir() if item.is_dir()], key=lambda item: item.stat().st_mtime, reverse=True):
        ensure_inside_outputs(job_dir)
        frames_dir = job_dir / "frames"
        images = []
        if frames_dir.exists() and frames_dir.is_dir():
            ensure_inside_outputs(frames_dir)
            images = [item for item in frames_dir.iterdir() if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        image_bytes = sum(item.stat().st_size for item in images)
        total_images += len(images)
        total_bytes += image_bytes
        jobs.append(
            {
                "job_id": job_dir.name,
                "path": str(job_dir),
                "frames_path": str(frames_dir),
                "image_count": len(images),
                "image_mb": round(image_bytes / 1024 / 1024, 2),
            }
        )
    return {
        "outputs_dir": str(OUTPUT_DIR),
        "report_dir": str(CACHE_REPORT_DIR),
        "job_count": len(jobs),
        "image_count": total_images,
        "image_mb": round(total_bytes / 1024 / 1024, 2),
        "jobs": jobs,
    }


def write_cache_report_files() -> dict[str, object]:
    report = output_cache_report()
    CACHE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = CACHE_REPORT_DIR / "cache_report.json"
    md_path = CACHE_REPORT_DIR / "cache_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 视频拆镜头工具缓存清单",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"outputs目录：{report['outputs_dir']}",
        f"任务文件夹数量：{report['job_count']}",
        f"静帧图片数量：{report['image_count']}",
        f"静帧图片占用：{report['image_mb']} MB",
        "",
        "| 任务文件夹 | 静帧数量 | 图片大小MB | frames路径 |",
        "|---|---:|---:|---|",
    ]
    for job in report["jobs"]:
        lines.append(
            f"| {job['job_id']} | {job['image_count']} | {job['image_mb']} | {job['frames_path']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        **report,
        "report_markdown": str(md_path),
        "report_json": str(json_path),
    }


def cleanup_old_frames(keep_job_ids: set[str]) -> dict[str, object]:
    """Remove only old generated frame images inside this project's outputs directory."""
    report = {"cleaned_frame_dirs": 0, "cleaned_images": 0, "skipped": []}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for job_dir in OUTPUT_DIR.iterdir():
        if not job_dir.is_dir() or job_dir.name in keep_job_ids:
            continue
        ensure_inside_outputs(job_dir)
        frames_dir = job_dir / "frames"
        if not frames_dir.exists() or not frames_dir.is_dir():
            continue
        ensure_inside_outputs(frames_dir)
        images = [item for item in frames_dir.iterdir() if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        for image in images:
            ensure_inside_outputs(image)
            image.unlink()
            report["cleaned_images"] += 1
        try:
            frames_dir.rmdir()
            report["cleaned_frame_dirs"] += 1
        except OSError:
            report["skipped"].append(str(frames_dir))
    return report


def ensure_thumb(frame_path: Path) -> Path:
    job_dir = frame_path.parent.parent
    thumb_dir = job_dir / "thumbs"
    ensure_inside_outputs(frame_path)
    ensure_inside_outputs(thumb_dir)
    if not frame_path.exists() or frame_path.parent.name != "frames":
        raise HTTPException(status_code=404, detail="静帧不存在")
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / frame_path.name
    if thumb_path.exists() and thumb_path.stat().st_mtime >= frame_path.stat().st_mtime:
        return thumb_path
    try:
        from PIL import Image

        with Image.open(frame_path) as image:
            image.thumbnail((THUMB_MAX_WIDTH, THUMB_MAX_HEIGHT))
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.save(thumb_path, "JPEG", quality=72, optimize=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"缩略图生成失败: {exc}") from exc
    return thumb_path


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/analyze")
async def analyze_video(
    video: UploadFile = File(...),
    mode: str = Form("breakdown"),
    product_model: str = Form(""),
) -> Storyboard:
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"只支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    job_dir = make_job_dir()
    file_name = safe_stem(video.filename or "video") + suffix
    video_path = job_dir / file_name
    with video_path.open("wb") as f:
        shutil.copyfileobj(video.file, f)

    return process_video(video_path, job_dir, mode=mode, product_model=product_model)


@app.post("/api/save")
async def save_storyboard(storyboard: Storyboard) -> dict[str, str]:
    job_dir = OUTPUT_DIR / storyboard.job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="job 不存在")
    write_json(job_dir / "storyboard.json", json.loads(storyboard.json()))
    return {"ok": "true", "path": str(job_dir / "storyboard.json")}


@app.post("/api/export/{fmt}")
async def export_storyboard(fmt: str, storyboard: Storyboard) -> dict[str, object]:
    job_dir = OUTPUT_DIR / storyboard.job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="job 不存在")
    safe_name = safe_stem(storyboard.video_info.file_name)
    if fmt == "csv":
        path = export_csv(storyboard, job_dir / f"{safe_name}_storyboard.csv")
    elif fmt == "xlsx":
        path = export_excel(storyboard, job_dir / f"{safe_name}_storyboard.xlsx")
    elif fmt == "docx":
        path = export_word(storyboard, job_dir / f"{safe_name}_storyboard.docx")
    elif fmt == "md":
        path = export_markdown(storyboard, job_dir / f"{safe_name}_storyboard.md")
        bundle = export_feishu_bundle(storyboard, job_dir, f"{safe_name}_storyboard")
        files = [
            {
                "name": path.name,
                "path": str(path),
                "download_url": f"/api/download/{storyboard.job_id}/{path.name}",
                "reveal_url": f"/api/reveal/{storyboard.job_id}/{path.name}",
            },
            {
                "name": bundle["feishu_md"].name,
                "path": str(bundle["feishu_md"]),
                "download_url": f"/api/download/{storyboard.job_id}/{bundle['feishu_md'].name}",
                "reveal_url": f"/api/reveal/{storyboard.job_id}/{bundle['feishu_md'].name}",
            },
            {
                "name": bundle["feishu_tsv"].name,
                "path": str(bundle["feishu_tsv"]),
                "download_url": f"/api/download/{storyboard.job_id}/{bundle['feishu_tsv'].name}",
                "reveal_url": f"/api/reveal/{storyboard.job_id}/{bundle['feishu_tsv'].name}",
            },
            {
                "name": bundle["payload_json"].name,
                "path": str(bundle["payload_json"]),
                "download_url": f"/api/download/{storyboard.job_id}/{bundle['payload_json'].name}",
                "reveal_url": f"/api/reveal/{storyboard.job_id}/{bundle['payload_json'].name}",
            },
        ]
        return {"files": files, "download_url": files[0]["download_url"], "reveal_url": files[0]["reveal_url"], "path": str(path)}
    else:
        raise HTTPException(status_code=400, detail="fmt 只能是 csv / xlsx / md / docx")
    return {
        "download_url": f"/api/download/{storyboard.job_id}/{path.name}",
        "reveal_url": f"/api/reveal/{storyboard.job_id}/{path.name}",
        "path": str(path),
    }


@app.post("/api/export-batch/docx")
async def export_storyboard_batch_docx(storyboards: list[Storyboard]) -> dict[str, object]:
    if not storyboards:
        raise HTTPException(status_code=400, detail="没有可导出的分镜表")
    job_dir = OUTPUT_DIR / storyboards[0].job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="job 不存在")
    safe_name = safe_stem(storyboards[0].video_info.file_name)
    path = export_word_batch(storyboards, job_dir / f"{safe_name}_batch_storyboards.docx")
    return {
        "download_url": f"/api/download/{storyboards[0].job_id}/{path.name}",
        "reveal_url": f"/api/reveal/{storyboards[0].job_id}/{path.name}",
        "path": str(path),
    }


@app.get("/api/download/{job_id}/{file_name}")
async def download_file(job_id: str, file_name: str) -> FileResponse:
    path = OUTPUT_DIR / job_id / file_name
    if not path.exists() or path.parent != OUTPUT_DIR / job_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=file_name)


@app.get("/api/thumb/{job_id}/{file_name}")
async def thumbnail_file(job_id: str, file_name: str) -> FileResponse:
    frame_path = (OUTPUT_DIR / job_id / "frames" / file_name).resolve()
    expected_dir = (OUTPUT_DIR / job_id / "frames").resolve()
    if frame_path.parent != expected_dir:
        raise HTTPException(status_code=404, detail="静帧不存在")
    return FileResponse(ensure_thumb(frame_path), media_type="image/jpeg")


@app.post("/api/reveal/{job_id}/{file_name}")
async def reveal_file(job_id: str, file_name: str) -> dict[str, str]:
    job_dir = (OUTPUT_DIR / job_id).resolve()
    path = (job_dir / file_name).resolve()
    if not path.exists() or path.parent != job_dir:
        raise HTTPException(status_code=404, detail="文件不存在")
    subprocess.Popen(["explorer.exe", f"/select,{path}"])
    return {"ok": "true", "path": str(path)}


@app.get("/api/cache/report")
async def cache_report() -> dict[str, object]:
    return output_cache_report()


@app.post("/api/cache/report-file")
async def cache_report_file() -> dict[str, object]:
    return write_cache_report_files()


@app.post("/api/cache/reveal")
async def reveal_cache_dir() -> dict[str, str]:
    path = CACHE_REPORT_DIR.resolve()
    if ROOT_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=400, detail="拒绝打开项目以外的路径")
    path.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer.exe", str(path)])
    return {"ok": "true", "path": str(path)}


@app.post("/api/sync")
async def sync_feishu(request: SyncRequest):
    overrides = {
        "doc_url": request.feishu_doc_url,
        "wiki_parent_url": request.feishu_doc_url,
        "bitable_url": request.feishu_bitable_url,
        "user_access_token": request.feishu_user_access_token,
    }
    result = sync_all(request.storyboard, request.target, overrides)
    job_dir = OUTPUT_DIR / request.job_id
    if job_dir.exists():
        write_json(job_dir / "storyboard.json", json.loads(request.storyboard.json()))
    if request.cleanup_after_sync and result.ok:
        keep_job_ids = set(request.keep_job_ids or [request.job_id])
        keep_job_ids.add(request.job_id)
        result.details["cleanup"] = cleanup_old_frames(keep_job_ids)
    return result


@app.get("/api/feishu/test/doc")
async def test_feishu_doc(doc_url: str = "", user_access_token: str = ""):
    return test_doc_connection({"doc_url": doc_url, "wiki_parent_url": doc_url, "user_access_token": user_access_token})


@app.get("/api/feishu/test/bitable")
async def test_feishu_bitable(bitable_url: str = "", user_access_token: str = ""):
    return test_bitable_connection({"bitable_url": bitable_url, "user_access_token": user_access_token})


@app.get("/api/job/{job_id}")
async def get_job(job_id: str) -> Storyboard:
    path = OUTPUT_DIR / job_id / "storyboard.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="job 不存在")
    return Storyboard(**read_json(path))


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "true", "root": str(ROOT_DIR)}
