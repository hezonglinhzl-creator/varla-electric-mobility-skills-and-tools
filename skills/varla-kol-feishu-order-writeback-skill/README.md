# KOL 订单飞书回写 / KOL Order Feishu Writeback

**简体中文** | [English](README.en.md)

把已核实的 Shopify 订单号和 KOL code/Impact ID 回写到用户指定的飞书记录，再读取核验。

## 功能特性

- 邮箱优先精确匹配
- 订单字段窄范围更新
- 回写后读取检查

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 飞书本地 OpenAPI 工具包 | [feishu-codex-local](../../apps/feishu-codex-local/README.md) |
| Shopify KOL 订单浏览器工具 | [shopify-order-bot](../../apps/shopify-order-bot/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 飞书本地 OpenAPI 工具包 (`feishu-codex-local`)

Windows、Python、自己的飞书应用权限；聊天桥接可选。

先进入 `../../apps/feishu-codex-local`。文档、原生表格、Base 和附件操作，带配置与检查脚本。

1. 先打开 `配置OpenAPI.bat`，按提示填写自己的 App ID 和 App Secret。
2. 配置保存在 `%USERPROFILE%\.feishu-docs\config.json`，只留在自己电脑。
3. 运行 `检查OpenAPI.bat`，如果权限不足，到自己的飞书开发者后台补权限并发布应用版本。
4. 在本目录运行 `python scripts/feishu_docs.py --help` 查看当前支持命令，或让已安装 Skill 的 Codex先只读指定文档。
5. 要从飞书聊天调用 Codex，才另行使用安装/配置/启动桥接入口，并准备 cc-connect；OpenAPI 资料操作可单独使用。

[查看完整程序与浏览器插件安装说明](../../apps/feishu-codex-local/README.md)

不能访问未授权资源；配置文件不要上传 GitHub，也不要把失败检查当同步成功。

### Shopify KOL 订单浏览器工具 (`shopify-order-bot`)

Python 3.11+、AdsPower Local API、自己的 Shopify 后台权限。

先进入 `../../apps/shopify-order-bot`。Excel 单条订单检查、地址核对、fill 和独立提交步骤。

1. 运行 `python -m pip install -r requirements.txt`，再运行 `python -m playwright install chromium`。
2. 把 `.env.example` 复制为 `.env`，填写自己的 AdsPower API、环境 ID 和 SHOPIFY_ADMIN_URL。
3. 按本目录说明准备 `KOL_order.xlsx`，先只放一条你自己的测试资料。
4. 先运行 `python main.py --step adspower`，再运行 `python main.py --step browser`，在自己的浏览器里登录。
5. 运行 `python main.py --step fill`，停在提交前核对；真实提交步骤只在明确授权后执行。

[查看完整程序与浏览器插件安装说明](../../apps/shopify-order-bot/README.md)

私密配置、登录会话和订单 Excel 由使用者自己准备；公开包不附带。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 当前飞书 Base 链接、确认后的订单结果和更新范围。 |
| 输出 | 创作者与订单映射表、更新回执和读取核验结果。 |

```text
使用 varla-kol-feishu-order-writeback-skill，先只读我给的 Base，按邮箱核对这笔已确认订单，列出准备更新的字段，暂不写入。
```


## 当前限制与常见问题

不根据截图位置或姓名猜测记录；创建订单与标记发货是不同操作，只有确认了相应事实才能写状态。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
