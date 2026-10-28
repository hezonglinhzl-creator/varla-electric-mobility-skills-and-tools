# 社媒排期与模拟发布原型 / Social Scheduling and Mock Publishing Prototype

**简体中文** | [English](README.en.md)

本地仪表板、任务验证、BullMQ Worker 和 Mock adapter。

## 运行环境

Node.js 22、npm、Redis；Docker 可提供 Redis/MinIO，FFmpeg 用于媒体。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 安装系统 Node.js 22+，在当前程序目录运行 npm install。
2. 双击 START_VARLA.bat，只打开静态仪表板；也可运行 powershell -File tools/start_varla.ps1 -CheckOnly 只检查，不启动。
3. 默认不启动 Redis 或 Worker。需要调试 Mock Worker 时另行准备自己的 Redis，并按开发文档显式配置 RUN_WORKER、MOCK_PUBLISHING 和 REDIS_URL。
4. 页面尚不能完成上传、审核和排期。/api/health 是固定 503 占位接口，不能据此判断真实依赖状态。

浏览器打开：`http://127.0.0.1:3000`

## 成功后应该看到什么

当前页面是静态仪表板原型；`/api/health` 固定返回 503 占位结果，不会实际探测依赖。验证接口和 Mock Worker 可单独调试，页面尚无完整上传/排期闭环。

## 当前功能边界

一键入口仅打开仪表板，使用系统 Node.js 22+ 和 npm 依赖，不会自动启动 Worker。可用 `powershell -File tools/start_varla.ps1 -CheckOnly` 检查。真实平台 adapter、OAuth、发布审核和上传/排期闭环仍未实现。

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
