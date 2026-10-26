# Varla KOL 回复助手 Skill 单文件指引

## 这个包是干什么的

这个 skill 用来让 Codex 在其他项目里维护 Varla KOL 智能回复系统，包括：

- 更新 Chrome 插件回复逻辑。
- 更新本地小窗口 UI。
- 更新 KOL / 售前售后 / 经销商服务商分类知识库。
- 更新 Word playbook 和小文档。
- 检查 OCR、本地模板、邮箱路由、Instagram/TikTok/Gmail 回复规则。
- 打包或迁移回复助手到其他电脑/项目。

## 安装方式

推荐把整个 `.skill` 文件交给 Codex 安装，或者解压后放到：

```text
C:\Users\<your-user>\.codex\skills\varla-kol-reply-assistant
```

如果是其他电脑，路径里的用户名可能不是 `Administrator`，按实际用户目录调整。

## 触发方式

在 Codex 里可以直接说：

```text
更新 Varla KOL 回复程序
```

```text
把 KOL 回复知识库同步到本地
```

```text
回复系统重新打包
```

```text
把售前售后问题加到回复助手
```

```text
检查 OCR 粘贴截图是否可用
```

## 推荐项目结构

回复助手项目一般长这样：

```text
varla-kol-reply-assistant
  chrome-extension
    contentScript.js
    manifest.json
    vendor
  src
    app.js
    stageRules.js
  knowledge_seed
    templates.json
    product_specs.json
    Varla_KOL_常见问题回复库.md
    split_playbooks
      knowledge_index.json
      kol_templates.json
      presales_aftersales_templates.json
      dealer_service_partner_templates.json
      kol_playbook.md
      presales_aftersales_playbook.md
      dealer_service_partner_playbook.md
      shared_core_rules.md
```

如果项目目录不同，先让 Codex 搜索这些文件名，不要直接照抄旧路径。

## 当前统一发货口径

以后所有回复、文档、模板都统一使用：

```text
For collaboration orders, shipping is usually arranged within 1-3 days after the collaboration is confirmed.
For regular purchases, shipping is usually arranged within 1-3 days after purchase.
We will share tracking information once it is available.
```

中文理解：

```text
合作确认后通常 1-3 天安排发货。
普通购买后通常 1-3 天安排发货。
tracking 出来后同步。
不承诺具体到货日期。
```

不要再写：

- July
- 7月
- around July
- July 10-15
- July 15-25
- 上市时间
- pre-order / preorder
- launch timing

## 常用邮箱规则

```text
美国售前邮箱：support@varlascooter.com
美国售后邮箱：customer@varlascooter.com
```

售前：价格、库存、优惠、购买、订单、地址、运费、付款、人工核实。

售后：维修、保修、退款、坏车、配件、ZIP code 维修点、产品故障、客服问题。

## 内容分类

### 纯 KOL

使用：

```text
kol_templates.json
kol_playbook.md
```

适合：

- KOL 合作
- 达人邀约
- 内容需求
- 合同
- 发布审核
- raw footage
- 官方 tag / hashtag / 共创

### 售前售后问题

使用：

```text
presales_aftersales_templates.json
presales_aftersales_playbook.md
```

适合：

- 价格
- 折扣
- 库存
- 发货
- 维修
- 退款
- 刹车线
- 坏车要照片视频
- support/customer 邮箱路由

### 服务商 / 经销商合作

使用：

```text
dealer_service_partner_templates.json
dealer_service_partner_playbook.md
```

适合：

- dealer
- service partner
- reseller
- distributor
- wholesale
- bulk purchase
- 门店/业务合作
- 不知道对方意图，需要先澄清

## 维护原则

1. 先找本地文件，不凭空写新系统。
2. 改回复时同时改：
   - `chrome-extension/contentScript.js`
   - `src/app.js`
   - `src/stageRules.js`
   - `knowledge_seed` 里的模板和小文档
3. 改文档时同步 Word playbook 和 Markdown 小文档。
4. OCR 要本地可用，优先检查 `chrome-extension/vendor`。
5. 不自动发送消息，只生成回复供人工复制或插入。
6. 不批量删除文件。

## 验证清单

让 Codex 改完后至少检查：

```text
node --check src/app.js
node --check src/stageRules.js
node --check chrome-extension/contentScript.js
JSON 文件能解析
旧词 July / 7月 / 上市 / pre-order 已清零
```

如果改了 Word 文档：

```text
DOCX 能用 python-docx 打开
OOXML 里没有旧词
如果本机没有 soffice，就说明没有做页面截图渲染 QA
```

## 给 Codex 的一句话

```text
使用 varla-kol-reply-assistant skill，先检查当前项目文件，再同步 Chrome 插件、本地 UI、知识库、Word 文档；统一使用合作确认后或购买后 1-3 天发货口径，不要自动发送，不要批量删除。
```
