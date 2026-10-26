# Technical Plan

## 1. Product Direction

This tool is a local short-form video scoring workspace for overseas social media operations. It should help decide whether a video is ready for TikTok, Instagram Reels, and YouTube Shorts paid or organic use.

## 2. Architecture

MVP:

- Browser UI served from local Python HTTP server
- FFprobe for metadata
- FFmpeg for frame extraction and audio extraction
- Pillow for frame quality heuristics
- File exports for reports

Target architecture:

- Frontend: React + TypeScript + Tailwind
- Backend: FastAPI
- Workers: FFmpeg + OpenCV + model connectors
- Database: SQLite
- Visualization: Recharts or ECharts
- AI connectors: OpenAI API and local vision endpoint
- External data connectors: CSV import first, then Apify / yt-dlp / YouTube API / browser automation

## 3. Database Design

Future SQLite tables:

- videos: id, file_name, path, duration, width, height, fps, has_audio, created_at
- analyses: id, video_id, total_score, advice, biggest_problem, payload_json, created_at
- frames: id, analysis_id, timestamp, image_path, clarity_score, composition_score, product_score, visual_score
- shots: id, analysis_id, start_time, end_time, score, issue, suggestion, keep
- competitors: id, platform, title, url, account, views, likes, comments, shares, saves, duration, posted_at
- benchmarks: id, keyword, platform, payload_json, created_at

## 4. API Design

MVP:

- GET /: local UI
- GET /api/health
- POST /api/analyze: multipart video upload; returns full report
- GET /reports/:job_id/frames/:file
- GET /exports/:file

Future:

- POST /api/videos
- GET /api/analyses/:id
- POST /api/competitors/import-csv
- POST /api/competitors/search
- POST /api/compare
- POST /api/export/pdf

## 5. Frontend Pages

- Dashboard: total score, platform score, ad recommendation
- Timeline: frame thumbnails, low/high score marks, cut points
- Golden 3 Seconds: first 3 seconds, risk, replacement opening
- Shot Analysis: shot start/end, issue, keep/remove suggestion
- Competitor: imported external data table
- Compare: my video vs benchmark averages
- Export: Markdown, CSV, JSON, PDF later

## 6. Scoring Algorithm

Total score uses:

- Golden 3 seconds: 25%
- Structure: 15%
- Shot rhythm: 15%
- Product exposure: 15%
- Emotional value: 10%
- Visual quality: 10%
- Platform fit: 5%
- CTA / conversion: 5%

MVP proxies:

- Product exposure = central subject activity + contrast
- Visual quality = sharpness + exposure + contrast
- Rhythm = average shot length vs short-form target
- Golden 3 seconds = opening visual score + early product score + motion/change + audio hook

Phase 2 replaces these proxies with real model labels.

## 7. MVP Development Steps

1. Build local upload and analysis server.
2. Extract metadata with FFprobe.
3. Extract frames with FFmpeg.
4. Score frames using Pillow.
5. Detect rough cut points from frame differences.
6. Generate golden 3 seconds report.
7. Render local dashboard.
8. Export JSON / Markdown / CSV.
