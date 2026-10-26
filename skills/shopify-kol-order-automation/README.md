# Shopify KOL 订单填写工具 / Shopify KOL Order Entry Automation

**简体中文** | [English](README.en.md)

使用 AdsPower 与浏览器界面填写 KOL 订单，先核对资料，按授权执行提交。

## 功能特性

- Excel 订单字段检查
- 浏览器登录复用和地址核对
- 默认只填写，提交有独立步骤

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
| 输入 | 你自己的 KOL_order.xlsx、店铺后台地址、AdsPower 环境。 |
| 输出 | 填写后的订单页面与核验结果；获授权后可创建订单。 |

```text
使用 shopify-kol-order-automation，检查我提供的测试订单，只运行资料核对和 fill，停在提交前给我检查。
```


## 当前限制与常见问题

创建订单不等于物流发货；工具不会自动购买运单。遇到地址冲突、验证码或账户不匹配应停止。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
