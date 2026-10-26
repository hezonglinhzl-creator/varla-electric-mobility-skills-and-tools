# 即梦图生视频命令包装器 / Dreamina Image-to-Video Command Wrapper

**简体中文** | [English](README.en.md)

从 JSON 任务生成 CLI 命令，默认 dry-run，--execute 才执行。

## 运行环境

Python、你自己的 Dreamina CLI 和登录；仅预览不要求执行生成。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 先安装对应 image2-motion-agent Skill；包装脚本在 `image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py`。
2. 用自己的图片创建 job.json，包含 image、prompt、duration、poll 和 video_resolution。
3. 先运行 `python image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py --job C:/path/job.json`。
4. 检查输出 `will_consume_credits: false` 和英文/中文提示词。
5. 准备真实生成前运行 `dreamina -h` 核对本机版本并登录；只有明确批准后，才对同一命令加 `--execute`。

## 成功后应该看到什么

预览返回命令数组和不消耗点数标记；真实执行返回 CLI 结果。

## 当前功能边界

第三方 CLI 版本和服务额度由使用者自行管理；包装器不提供账号或免费点数。

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
