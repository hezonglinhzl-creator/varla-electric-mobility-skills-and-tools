# 电摩 AI 内容资料与验证工具 / eMoto AI Content Resources and Validation

**简体中文** | [English](README.en.md)

剧情导演与产品视频工作流资料，配合提示词结构验证。

## 运行环境

Codex；可选 Python 用于验证提示词文件。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 这是内容工具资料集合，先使用完整包根目录的 `安装Skill.cmd`。
2. 把自己的产品图和已确认参数交给 Codex，使用 emoto-ugc-story-director。
3. 先检查分镜和提示词，再选择自己的视频生成平台。
4. 需要结构检查时运行 `python skills/emoto-ugc-story-director/scripts/validate_prompt.py C:/path/prompt.md`。

## 成功后应该看到什么

可审核的分镜和提示词，验证器输出结构检查结果。

## 当前功能边界

没有独立的桌面视频生成程序或预装生成账号。

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
