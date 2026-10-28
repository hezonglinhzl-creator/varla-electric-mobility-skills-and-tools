# Meta 客服回复与社媒发布流程 / Meta Reply and Social Publishing Workflow

**简体中文** | [English](README.en.md)

整理 Meta 客服/KOL 回复规则，并附带本地社媒发布原型源码。

## 功能特性

- 客服、售后和 KOL 路由规则
- 人工接管与回复草稿
- 本地排期与 Mock 发布原型

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 社媒排期与模拟发布原型 | [varla-social-publisher](../../apps/varla-social-publisher/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 社媒排期与模拟发布原型 (`varla-social-publisher`)

Node.js 22、npm、Redis；Docker 可提供 Redis/MinIO，FFmpeg 用于媒体。

先进入 `../../apps/varla-social-publisher`。本地仪表板、任务验证、BullMQ Worker 和 Mock adapter。

1. 安装系统 Node.js 22+，在当前程序目录运行 npm install。
2. 双击 START_VARLA.bat，只打开静态仪表板；也可运行 powershell -File tools/start_varla.ps1 -CheckOnly 只检查，不启动。
3. 默认不启动 Redis 或 Worker。需要调试 Mock Worker 时另行准备自己的 Redis，并按开发文档显式配置 RUN_WORKER、MOCK_PUBLISHING 和 REDIS_URL。
4. 页面尚不能完成上传、审核和排期。/api/health 是固定 503 占位接口，不能据此判断真实依赖状态。

本地地址：`http://127.0.0.1:3000`

[查看完整程序与浏览器插件安装说明](../../apps/varla-social-publisher/README.md)

一键入口仅打开仪表板，使用系统 Node.js 22+ 和 npm 依赖，不会自动启动 Worker。可用 `powershell -File tools/start_varla.ps1 -CheckOnly` 检查。真实平台 adapter、OAuth、发布审核和上传/排期闭环仍未实现。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 消息内容、当前产品知识、平台与已批准回复规则。 |
| 输出 | 待审核回复、路由建议或本地模拟发布任务。 |

```text
使用 meta-auto-reply-skill，给这条私信分类并生成待审核回复；不要发送，也不要安排真实发布。
```


## 当前限制与常见问题

附带发布程序当前真实平台适配器未配置；启动网页或 Mock 任务成功不代表内容已发布。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
