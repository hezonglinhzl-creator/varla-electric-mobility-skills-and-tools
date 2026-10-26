# 社媒排期与模拟发布原型 / Social Scheduling and Mock Publishing Prototype

**简体中文** | [English](README.en.md)

本地仪表板、任务验证、BullMQ Worker 和 Mock adapter。

## 运行环境

Node.js 22、npm、Redis；Docker 可提供 Redis/MinIO，FFmpeg 用于媒体。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 在本目录打开 PowerShell，运行 `Copy-Item .env.example .env`，自行填写本地密钥，保持 `MOCK_PUBLISHING=true`。
2. 运行 `npm install`，随后 `npm run db:generate` 和 `npm run db:push`。
3. 启动自己的 Redis，确认 `.env` 中 REDIS_URL 正确，然后运行 `npm run dev`。
4. 第二个终端运行 `$env:RUN_WORKER='true'; $env:MOCK_PUBLISHING='true'; $env:REDIS_URL='redis://127.0.0.1:6379'; npm run worker`。
5. 打开仪表板，只做模拟任务。健康检查显示依赖未就绪时先检查数据库、Redis、存储和 Worker。

浏览器打开：`http://127.0.0.1:3000`

## 成功后应该看到什么

仪表板和模拟任务可用于验证流程；接口状态以 `/api/health` 返回为准。

## 当前功能边界

源码明确拒绝未配置的真实平台 adapter。Meta/TikTok 发布、OAuth、审核和外部媒体 URL 尚需集成，不能把 Mock 成功当成真实发布。

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
