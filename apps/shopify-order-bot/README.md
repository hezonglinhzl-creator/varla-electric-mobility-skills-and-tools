# Shopify KOL 订单自动创建工具 V1

这是 Varla 内部使用的最小可运行版本。它读取 `KOL_order.xlsx` 的第一条有效订单，通过 AdsPower Local API 启动指定浏览器环境，再由 Playwright 通过 CDP 接管页面，填写 Shopify Create order，并使用 Shopify 页面提示和 Google Maps 网页辅助校对地址。

## 安全边界

- 不使用 Shopify API 或 Google Maps API。
- AdsPower Local API 只用于启动和连接本机浏览器环境。
- 不使用固定坐标点击。
- Shopify 页面已经打开时直接接管并点击页面按钮，不主动刷新。
- 一次只处理一条测试订单。
- 地址不一致、不确定、出现验证码或结果不唯一时立即停止。
- 不自动修改冲突地址。
- 默认 `fill` 只填写并停留页面，不提交。
- 只有显式使用 `--step submit-test` 才会在严格核对姓名、邮箱、完整地址、
  产品、Note、Tag 和 `$0.00` 总额后执行 `Mark as paid`。
- 创建成功后只核验 `Paid / Unfulfilled`，不会标记发货或创建物流标签。

## 1. 安装环境

准备条件：

- Python 3.11 或更高版本。
- AdsPower 已启动，并已开启 Local API。
- AdsPower 中至少有一个用于 Shopify 的浏览器环境。

在本文件所在目录打开 PowerShell：

```powershell
pip install -r requirements.txt
playwright install chromium
```

如系统中有多个 Python，可将命令中的 `pip` 和 `playwright` 改为：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 2. 配置 AdsPower 和 Shopify

项目内的 `.env` 是本机私密配置，已被 `.gitignore` 排除。不要把它发送给其他人。

配置项：

```text
ADSPOWER_API_URL=AdsPower 本地服务地址
ADSPOWER_API_KEY=AdsPower Local API 密钥
ADSPOWER_PROFILE_ID=要使用的环境 ID
SHOPIFY_ADMIN_URL=Shopify 后台 /admin 地址
```

先查看安全的环境列表：

```powershell
python main.py --step adspower
```

把目标环境的 ID 写入 `.env` 中：

```text
ADSPOWER_PROFILE_ID=目标环境ID
```

如果 AdsPower 只有一个环境，可以暂时留空，程序会自动使用唯一环境。若有多个环境，程序会安全停止并要求明确指定，避免打开错误账号。

### 修改 Shopify 后台地址

推荐：打开 `.env`，把下面的示例地址改成真实后台地址：

```text
https://your-store.myshopify.com/admin
```

也可以只对当前 PowerShell 窗口设置：

```powershell
$env:SHOPIFY_ADMIN_URL="https://你的店铺.myshopify.com/admin"
```

请勿把 Shopify 账号、密码或 Cookie 写入代码。

## 3. 第一次运行和登录状态

执行：

```powershell
python main.py --step browser
```

浏览器打开后，第一次由你人工登录 Shopify。登录完成后回到 PowerShell 按 Enter。登录状态保存在指定 AdsPower 环境中，后续运行会复用。

注意：

- AdsPower 环境包含登录状态，不要导出或发送给无关人员。
- 工具结束时只断开 Playwright，不会自动关闭 AdsPower 环境。
- Shopify 若要求重新验证身份，按页面提示人工完成即可。

## 4. Excel 格式

文件名必须是 `KOL_order.xlsx`，表头必须包含：

```text
name
email
phone
address
city
state
country
zipcode
product
note
tag
address2
```

`address2` 为可选字段，用于 Apartment、Suite、Unit、楼栋、楼层等补充地址；
没有时留空。V1 跳过完全空白行，只读取第一条有效订单。电话、邮编、SKU 和
订单号应按文本保存。

Note 固定两行，支持以下四种车型颜色码：

```text
V-M5S-BK-US  # M5S 黑色
V-M5S-RD-US  # M5S 红色
V-M7S-BK-US  # M7S 黑色
V-M7S-RD-US  # M7S 红色
```

第二行必须是：

```text
VAR-GIFTSET-002
```

先单独测试 Excel：

```powershell
python main.py --step excel
```

它只读取和显示数据，不打开浏览器。

## 5. 分步测试

先测试 AdsPower 本地服务并查看环境：

```powershell
python main.py --step adspower
```

打开后台并测试 AdsPower 登录复用：

```powershell
python main.py --step browser
```

只进入 Shopify Create order 页面：

```powershell
python main.py --step create-order
```

完整填写一条测试订单：

```powershell
python main.py
```

或：

```powershell
python main.py --step fill
```

确认需要真实创建一条测试订单时，才使用：

```powershell
python main.py --step submit-test
```

成功后 Excel 会新增/更新 `varla_order_code`，并且只回写姓名和邮箱同时唯一匹配
的那一行。已有不同订单号时程序会停止，避免覆盖。

新客户流程固定为：

1. 填写姓名、邮箱和 10 位美国电话，三个营销许可保持未勾选。
2. 客户 Tags 添加 `KOL`。
3. 点击 `Add address`，填写主地址、补充地址、城市、州、邮编和电话。
4. 保存客户后等待 Shopify 自动挂载，不刷新页面。

美国电话在 Excel 和程序输入中始终是纯 10 位数字，例如 `4155550176`。
Shopify 保存美国电话后会在后台页面强制按 E.164 显示为
`+1 415-555-0176`；这不会改写 Excel 中的 10 位原始数据。

## 6. 地址校对规则

流程为：

1. 主街道地址写入 Shopify 的 `Address`，优先使用 Shopify 自动识别结果。
2. `address2` 原样写入 `Apartment, suite, etc`，不让 Google Maps 改写。
3. 读取 Shopify 页面中可见的建议、冲突或无法验证提示。
4. Shopify 已确认完整主地址一致时跳过 Google Maps。
5. Shopify 报错、无法确认或没有明确反馈时，新标签页打开 Google Maps。
6. Google Maps 只对比门牌街道、城市、州、邮编和国家，不判断公寓/单元号。
7. 复制并完成比对后自动关闭 Google Maps 标签页，继续使用原 Shopify 页面。

结果：

- `match`：Google Maps 可见地址的主要字段都能对应。
- `mismatch`：发现明确的门牌号或邮编等冲突。
- `uncertain`：结果缺字段、返回多个地点、页面结构无法识别或遇到验证码。
- `no_visible_feedback`：Shopify 没有显示校验提示；继续用 Google Maps。

只有 Shopify 已确认一致，或 Shopify 无明确冲突且 Google Maps 为 `match` 时，
工具才继续填写 Notes 和 Tags。只要 Excel 有 `address2`，提交前还必须在
Shopify 页面看到相同补充地址。

地址网页校对只是辅助人工判断，不代表邮政可投递性或收件人身份验证。

本项目不执行飞书导入或同步；Excel 结果由后续独立 skill 读取。

## 7. 日志和截图

运行日志保存在：

```text
logs/
```

失败时会生成：

```text
logs/error_<步骤>_<时间>.png
debug_screenshot.png
```

地址需要人工确认时会生成：

```text
logs/address_mismatch_<时间>.png
```

如果 Shopify 更新了页面、按钮文字或后台语言不是英文，工具可能无法定位元素。请保留日志和截图，用于调整语义定位器。

## 8. 常见问题

### 浏览器打不开

确认 AdsPower 已启动、Local API 已开启，并且 `.env` 中的服务地址、密钥和环境 ID 属于当前电脑。

Playwright 安装异常时可重新安装：

```powershell
python -m playwright install chromium
```

### 提示后台地址未配置

修改 `config.py`，或在当前 PowerShell 设置 `SHOPIFY_ADMIN_URL`。

### Google Maps 要求验证码

这是安全停止条件。请在浏览器里人工完成验证，再重新运行；工具不会绕过验证码。

### Shopify 显示 “Your connection needs to be verified”

程序会立刻停止，不会继续点击。这个提示通常属于当前浏览器环境或网络连接验证，
请在 AdsPower 环境中人工完成 Shopify 验证后再运行。工具不会清 Cookie、绕过验证
或切换账号。

### 产品搜索不到

确认 Excel 的 `product` 与 Shopify 后台产品名称一致。失败时查看 `debug_screenshot.png`。

### 会不会自动发货

不会。`submit-test` 只创建已付款订单，最终状态必须是 `Paid / Unfulfilled`。
程序不会点击 `Mark as fulfilled`、不会创建运输标签，也不会自动发货。
