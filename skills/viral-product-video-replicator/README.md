# 产品视频拆解与分镜复刻 / Product Video Breakdown and Storyboard Adaptation

**简体中文** | [English](README.en.md)

用本地拆镜头程序生成关键帧和分镜表，再由 Skill 设计产品替换、人物、提示词和社媒文案。

## 功能特性

- 镜头切分和关键帧
- CSV / Excel / Markdown 导出
- 产品替换与电摩 UGC 分镜

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 本地视频拆镜头与分镜表 | [video-storyboard-tool](../../apps/video-storyboard-tool/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 本地视频拆镜头与分镜表 (`video-storyboard-tool`)

Python 3.11+、FFmpeg/FFprobe；语音识别可选 Whisper。

先进入 `../../apps/video-storyboard-tool`。视频上传、镜头切分、关键帧、可编辑分镜表和表格导出。

1. 在本目录运行 `python -m venv .venv`。
2. 运行 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`。
3. 确认 `ffmpeg -version` 可用；如需台词识别，再用该 Python 安装 `requirements-whisper.txt`。
4. 运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787`。
5. 打开页面上传自己的短测试视频，检查镜头和台词，修改表格后导出。飞书功能另填自己的 `.env`。

本地地址：`http://127.0.0.1:8787`

[查看完整程序与浏览器插件安装说明](../../apps/video-storyboard-tool/README.md)

部分画面说明是模板或占位，不代表已完成视觉理解；Whisper 未安装时台词可能为空。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 有权使用的参考视频、产品图、参数和目标平台。 |
| 输出 | 关键帧、可编辑镜头表、视频改编脚本及生成提示词。 |

```text
使用 viral-product-video-replicator，先拆解我的参考视频并导出镜头表，再给电摩产品替换方案，禁止改动产品外形和参数。
```


## 当前限制与常见问题

语音识别需另装 Whisper 和 FFmpeg；画面说明有模板/占位部分，必须人工核对，飞书同步需配置自己的权限。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
