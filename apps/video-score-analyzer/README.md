# 本地短视频评分分析 / Local Short Video Score Analyzer

**简体中文** | [English](README.en.md)

前三秒、剪辑节奏、抽帧、波形和启发式评分导出。

## 运行环境

Python 3.11+、FFmpeg/FFprobe、Pillow。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 运行 `python -m pip install -r requirements.txt`。
2. 确认 `ffmpeg -version` 与 `ffprobe -version` 可运行。
3. 双击 `start_video_score_analyzer.bat`，或运行 `python server.py`。
4. 打开页面上传自己的视频，查看评分、缩略图和建议，再导出报告。

浏览器打开：`http://127.0.0.1:8765`

## 成功后应该看到什么

导出位于 `exports/`；分析中间文件位于 `reports/`。

## 当前功能边界

评分是启发式参考，不是投放效果预测；端口 8765 与 KOL 记录器冲突，避免同时启动。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 黑窗口闪退 / 找不到 Python | 在当前目录打开 PowerShell，执行 `python --version`。需要安装时从 python.org 安装并勾选 Add Python to PATH，然后重新运行本文命令看具体错误。 |
| 提示缺少模块 | 用启动程序的同一个 Python 安装该程序 requirements 中的依赖。 |
| 页面打不开 / 端口占用 | 对照本文地址和服务日志；先关闭自己正在使用的冲突工具。浏览器扩展不能替代后端。 |
| Excel 保存失败 | 关闭 Excel/WPS 中的文件，检查输出路径后重试一次。 |
| 登录或飞书权限失败 | 使用自己的配置，检查目标资源权限；不要复制别人的 Token。 |

## 本地数据

账号配置、会话、台账和运行结果由使用者在自己电脑生成或配置。公开源码不附带真实客户/KOL 数据、邮箱内容、合同或已登录账号。
