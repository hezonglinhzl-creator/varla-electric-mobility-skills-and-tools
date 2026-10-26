# UpPromote KOL 联盟流程 / UpPromote KOL Affiliate Workflow

**简体中文** | [English](README.en.md)

从飞书 KOL 记录出发，核对联盟资料、优惠码、链接与邮件阶段，复用当前浏览器状态。

## 功能特性

- 按准确记录和邮箱定位
- 优惠码和已有链接去重
- dry-run、邮件草稿与阶段恢复

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| Shopify KOL 订单浏览器工具 | [shopify-order-bot](../../apps/shopify-order-bot/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

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
| 输入 | 你自己的 Base/记录链接、准确 code、AdsPower 登录环境及服务配置。 |
| 输出 | 经核验的 code/link、飞书回写与邮件草稿或回执。 |

```text
使用 varla-uppromote-affiliate-automation，先对我给的记录做 dry-run，检查已有 code 和链接，只报告缺失配置，不创建、不发邮件。
```

## 先做只读检查

在 `skill/varla-uppromote-affiliate-automation` 中运行；先配置自己的飞书和浏览器环境。占位链接必须换成你有权限的链接。

```powershell
python scripts/run_varla_affiliate.py --feishu-url "YOUR_FEISHU_BASE_URL" --code-name "YOUR_APPROVED_CODE" --dry-run
```

## 当前限制与常见问题

依赖自己的飞书、AdsPower、Shopify/UpPromote 登录和 Gmail 设置；优惠规则以当前已确认政策为准。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
