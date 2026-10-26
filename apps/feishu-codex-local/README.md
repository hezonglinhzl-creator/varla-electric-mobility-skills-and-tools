# 飞书本地 OpenAPI 工具包 / Local Feishu OpenAPI Toolkit

**简体中文** | [English](README.en.md)

文档、原生表格、Base 和附件操作，带配置与检查脚本。

## 运行环境

Windows、Python、自己的飞书应用权限；聊天桥接可选。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 先打开 `配置OpenAPI.bat`，按提示填写自己的 App ID 和 App Secret。
2. 配置保存在 `%USERPROFILE%\.feishu-docs\config.json`，只留在自己电脑。
3. 运行 `检查OpenAPI.bat`，如果权限不足，到自己的飞书开发者后台补权限并发布应用版本。
4. 在本目录运行 `python scripts/feishu_docs.py --help` 查看当前支持命令，或让已安装 Skill 的 Codex先只读指定文档。
5. 要从飞书聊天调用 Codex，才另行使用安装/配置/启动桥接入口，并准备 cc-connect；OpenAPI 资料操作可单独使用。

## 成功后应该看到什么

检查返回真实授权状态，读取任务能输出指定文档或字段。

## 当前功能边界

不能访问未授权资源；配置文件不要上传 GitHub，也不要把失败检查当同步成功。

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
