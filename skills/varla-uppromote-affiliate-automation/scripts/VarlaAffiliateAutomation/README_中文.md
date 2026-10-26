# Varla UpPromote Affiliate 一键自动化

双击 `check_environment.bat` 检查环境；全部为 `true` 后，双击 `run_varla_affiliate.bat` 开始。

## 自动执行内容

1. 从你粘贴的飞书 Base 链接读取表格，并按 KOL Name 或邮箱精确匹配一条记录。
2. 读取 `KOL Name`、`Email`、`code name`；已有 `code link` 时默认停止，避免重复。
3. 连接当前运行的 AdsPower 浏览器，打开 Shopify 的 UpPromote Affiliate。
4. 按邮箱查重；没有才创建 Affiliate，并选择 `KOL - $100`、Active、自动密码。
5. 创建或核验 `$100` Electric Dirt Bike 优惠码，启用三种优惠组合。
6. 保存自定义 Affiliate path，Login as affiliate，依次执行 Generate → Get shortened link → Copy & save。
7. 把精确 code 和短链写回原飞书记录，并立即回读验证。
8. 读取 Skill 包内 `assets\Varla KOL Code.docx` 的文字作为邮件模板，替换姓名、code、link；不附加 DOCX。也可使用 `--docx` 指定其他模板。
9. 验证发件人为 `info@varlascooter.com`。输入 `DRAFT` 只建草稿；输入 `SEND` 且再次输入 `SEND` 才真实发送。

## 命令行示例

只读检查，不写入任何系统：

```powershell
python .\varla_affiliate.py --feishu-url "飞书链接" --kol-name "Big Tdtto" --dry-run --resume-existing-link
```

新建邮件草稿（默认）：

```powershell
python .\varla_affiliate.py --feishu-url "飞书链接" --kol-name "Creator Name"
```

明确发送：

```powershell
python .\varla_affiliate.py --feishu-url "飞书链接" --kol-name "Creator Name" --send --confirm SEND
```

如果 UpPromote/飞书已完成、只需要补邮件，可加 `--resume-existing-link`。该模式不会再次操作 UpPromote 或覆盖短链。

## 安全停止条件

- 飞书匹配不到或匹配到多条记录。
- `code name`、邮箱或 KOL Name 缺失。
- 已有短链但未明确使用恢复参数。
- AdsPower 未打开、登录失效、出现验证码、页面控件变化或优惠码冲突。
- 短链没有出现在 Saved link 表格，或飞书回读值不一致。
- Gmail 登录账号不是 `info@varlascooter.com`。

运行日志保存在本文件夹的 `logs` 子文件夹。日志不保存密码、Cookie、OAuth token 或飞书密钥。
# 速度优化版（2026-08-10）

- AdsPower 端口改为并行快速探测，实测 8 个候选端口约 0.15 秒完成连接。
- 页面操作改为等待真实控件/保存结果，不再依赖大量固定等待时间。
- 每个阶段即时显示时间和进度，不会再长时间无输出。
- Gmail 草稿/已发送去重改为服务器端精确搜索，不再逐封扫描 100 个草稿。
- 可直接用飞书 `code name` 定位：`--code-name urbanrider5`。
- 已知 record ID 时使用 `--record-id rec...`，跳过整表扫描，速度最快。
- Electric Dirt Bike 使用精确匹配，避免误选 Accessories。
- 每次关键点击给网页 5–7 秒响应时间，再按真实状态判断成功或失败。
- 正常创建优惠券时直接进入 `Add coupon`；只有点击 Save 后结果不明确，才检查一次 `View assigned coupons`，发现精确 code 已绑定就继续，禁止重复创建。
- 每位 KOL 完成后关闭对应 Affiliate dashboard 标签页；失败时关闭该 KOL 的残留页面并重新打开 Affiliate 列表，避免下一位继承未保存表单。
- 自动识别当前停留阶段并原地续跑，不再每次退回 Affiliate 列表。
- Coupon 的 Manage 只从精确邮箱所在表格行点击，不会误抓搜索标签。
- Collection 点击外层选择框；详情页必须等姓名/邮箱加载完成后才保存。
- 已存在并核验的 Gmail 草稿在收到 SEND 确认后直接发送，不会另建重复邮件。

推荐从 `run_varla_affiliate.bat` 启动，它会自动选择包含完整依赖的 Varla Python 环境。命令行示例：

```powershell
.\run_varla_affiliate.bat --feishu-url "飞书链接" --code-name "OWBEN"
```

最快恢复已完成记录：

```powershell
.\run_varla_affiliate.bat --feishu-url "飞书链接" --record-id "rec..." --resume-existing-link
```
