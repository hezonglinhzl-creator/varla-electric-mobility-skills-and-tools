# 本地视频拆镜头脚本工具 MVP

这是一个本地 FastAPI + 简单网页前端工具，用于短视频拆镜头、抽静帧、提取台词、生成分镜表，并同步到飞书多维表格 / 飞书文档。

## 已实现功能

- 上传 `mp4 / mov / webm / m4v`
- 自动镜头切分：优先 PySceneDetect，失败时降级 OpenCV
- 每个镜头抽取 1 张关键帧：`outputs/<job_id>/frames/shot_001.jpg`
- 音频提取：检测到 `ffmpeg` 时自动提取
- 台词识别：安装 `openai-whisper` 后自动启用；未安装时台词留空并显示提醒
- 表格字段严格包含：镜号、景别、拍摄手法、画面、画面说明、备注、台词、英文台词
- 前端可手动修改单元格
- 导出 CSV / Excel / Markdown
- Excel 插图：优先把静帧插入到“画面”列，同时保留本地图片路径
- 飞书同步模块：支持多维表格记录、图片上传尝试、文档创建
- 参考生成电摩脚本模式：按参考视频镜头结构生成电摩 / 电动越野车 / 骑行产品分镜

## 安装

在 PowerShell 进入本目录：

```powershell
cd "C:\Users\<your-user>\Documents\New project 9\项目\视频拆镜头工具"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果需要语音识别，再安装 Whisper：

```powershell
python -m pip install -r requirements-whisper.txt
```

并确保系统能使用 `ffmpeg`：

```powershell
ffmpeg -version
```

## 启动

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

浏览器打开：

```text
http://127.0.0.1:8787
```

也可以双击：

```text
start_video_storyboard_tool.bat
```

## 飞书配置

复制 `.env.example` 为 `.env`，填写：

```dotenv
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_BITABLE_APP_TOKEN=
FEISHU_BITABLE_TABLE_ID=
FEISHU_FOLDER_TOKEN=
FEISHU_DOC_FOLDER_TOKEN=
FEISHU_WIKI_PARENT_NODE_TOKEN=FyXOwMNkUi895Dkvo77cF2QqnHg
FEISHU_WIKI_PARENT_URL=https://m9kzgsiucj.feishu.cn/wiki/FyXOwMNkUi895Dkvo77cF2QqnHg
FEISHU_ENABLE_SYNC=true
```

如果你已经用过本地飞书工具，程序也会读取：

```text
C:\Users\<your-user>\.feishu-docs\config.json
```

飞书文档同步现在会优先使用知识库父节点：

```text
https://m9kzgsiucj.feishu.cn/wiki/FyXOwMNkUi895Dkvo77cF2QqnHg
```

同步时会在该知识库页面下面创建一篇新的 docx 子页面，并把分镜表写成飞书原生表格块，而不是 Markdown 管道表或纯文本。

多维表格建议提前建这些字段：

| 字段 | 类型建议 |
|---|---|
| 镜号 | 文本 |
| 景别 | 文本 / 单选 |
| 拍摄手法 | 文本 / 单选 |
| 画面 | 附件；如果权限不足会写入本地图片路径 |
| 画面说明 | 多行文本 |
| 备注 | 多行文本 |
| 台词 | 多行文本 |
| 英文台词 | 多行文本 |
| 开始时间 | 文本 |
| 结束时间 | 文本 |
| 时长 | 文本 |
| 视频名称 | 文本 |
| 状态 | 单选，默认 To Do |
| 创建时间 | 文本 |

## 输出结构

```text
outputs/
  <job_id>/
    input_video.mp4
    audio.wav
    storyboard.json
    frames/
      shot_001.jpg
      shot_002.jpg
    demo_storyboard.csv
    demo_storyboard.xlsx
    demo_storyboard.md
```

## 说明

- 画面说明目前是可编辑占位/电摩模板，不做复杂 AI 营销分析。
- OCR 已预留扩展位置，第一版重点先跑通稳定拆镜头、台词、静帧、表格和飞书同步。
- 飞书图片上传依赖应用权限；若上传失败，工具会保留本地图片路径，保证记录不会因为图片权限中断。
