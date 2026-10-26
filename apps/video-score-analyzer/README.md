# Varla Video Score Analyzer

本地短视频投流评分分析工具 MVP。当前版本优先实现可运行闭环：

- 本地视频上传
- FFprobe 基础信息分析
- FFmpeg 抽帧
- 0-3 秒黄金三秒评分
- 时间轴缩略图
- 简易镜头切点和剪辑建议
- 音频波形和静音段检测
- JSON / Markdown / CSV 导出

## 一键启动

双击：

```powershell
start_video_score_analyzer.bat
```

或在 PowerShell 运行：

```powershell
cd "C:\Users\<your-user>\Documents\New project 9\项目\video-score-analyzer"
python server.py
```

打开地址：

```text
http://127.0.0.1:8765
```

## 环境要求

- Python 3.11+
- FFmpeg / FFprobe 已加入 PATH
- Pillow

当前机器已检测到 FFmpeg 和 Pillow，可以直接跑。

## 目录结构

```text
video-score-analyzer/
  app/                 核心分析逻辑
  static/              本地网页界面
  uploads/             上传的视频副本
  reports/             抽帧和中间分析结果
  exports/             JSON / Markdown / CSV 导出
  docs/                技术方案和后续开发设计
  server.py            本地 Web 服务入口
```

## MVP 评分权重

- 黄金三秒：25%
- 视频结构：15%
- 镜头节奏：15%
- 产品露出：15%
- 情绪价值：10%
- 画面质量：10%
- 平台适配：5%
- CTA / 转化潜力：5%

当前评分是本地启发式算法，后续可以把 `app/analyzer.py` 里的帧评分替换成 OpenAI API、本地视觉模型或人工标注模型。

## 后续阶段

Phase 2：接入 OpenAI / 本地视觉模型，识别产品、人物、字幕、logo、场景和情绪价值。

Phase 3：导入或抓取 TikTok / Instagram / YouTube Shorts 竞品数据，做爆款基准库。

Phase 4：升级 React + FastAPI + SQLite + 桌面封装。
