---
name: kol建联数据表格skill
description: 维护 Varla KOL 建联 XLSX 台账，记录和核对 Instagram、TikTok、YouTube 创作者主页、粉丝/订阅数、近期视频平均播放、联系方式和建联状态。用户提到 KOL 建联数据表、达人台账、记录当前 KOL、补充粉丝或平均播放、核查建联表时使用。
---

## Portable distribution paths / 完整包程序位置

Before running a program, read `PACKAGE-LOCATION.json` beside this installed SKILL.md.
Its `apps` object maps each bundled program name to the real extracted directory;
`package_root` points to the complete bundle. Use those paths first. Absolute paths
in older examples below are historical examples, not automatic defaults.
If this file is missing or the bundle was moved, rerun the complete project's
install.ps1 to refresh the mapping. Keep the extracted program directory.
Never treat YOUR_* placeholders as configured credentials or resource IDs.

运行程序前先读取本 SKILL.md 旁边的 `PACKAGE-LOCATION.json`：`apps` 是实际程序目录，
`package_root` 是完整包位置。下文旧电脑绝对路径只作为历史示例，不能自动照用。
缺少映射或完整包搬家后，重新运行完整包 install.ps1；保留解压后的程序目录。
YOUR_* 占位符不代表已配置账号或资源；真实写入前必须使用自己的授权和目标链接。


# KOL 建联数据表格

用于维护本地 `varla_kol_tracker.xlsx` 建联台账。收集对象是创作者账号主页及公开资料；不要与飞书视频分析表、爆款视频库或邮件总控混用。

## 工作簿定位

1. 优先使用用户当前指定的收集器目录。
2. 默认文件为 `KOL_recorder/outputs/varla_kol_tracker.xlsx`，工作表优先选 `KOL建联台账`。
3. 通过 Chrome 扩展的“记录当前KOL”写入；写入后直接打开或读取 XLSX 核对，不能只凭扩展提示认定成功。
4. 如果服务未启动、工作簿被 Excel/WPS 占用或写入报错，按页面提示恢复后重试；不要改写到另一个同名工作簿。

## 固定字段

保持现有 16 列及次序，不新增列、不改表头：

`Num`, `Date`, `KOL Name`, `Platform`, `Handle`, `Profile URL`, `Email`, `Country`, `Followers`, `Avg Views`, `Best Video Views`, `Contact Status`, `Cooperation Type`, `Quote`, `Internal Rating`, `Next Follow-up Date`

## 采集流程

1. 打开 Instagram、TikTok 或 YouTube 的创作者主页，确认地址栏是账号主页，不是单条视频、搜索页或推荐内容。
2. 点击一次“记录当前KOL”。先等页面信息加载完成；若粉丝数或视频播放数缺失，检查当前页面是否公开显示、切到账号主页后再采集。
3. 按 `Platform + Handle + Profile URL` 核对目标记录。跨平台同名账号是不同记录，不得只凭名称合并。
4. 检查记录后的 `Followers`、`Avg Views`、`Best Video Views`、`Profile URL`，并确认 Email/Country 只在页面有明确证据时填写。
5. 复核 `Contact Status` 和商业跟进字段，再保存并读回文件确认值正确。

## 指标口径

- `Followers`：Instagram/TikTok 粉丝数；YouTube 订阅者数也写入此列。保留来源页面显示的数量级，统一格式为 `K`/`M`，例如 `31.8K`。
- `Avg Views`：只代表采集时主页上成功识别到的视频播放量平均值，不等于账号所有历史视频的平均值。当前扩展对 Instagram 和 YouTube 最多取页面中前 10 个可见视频卡片计算；采集前如需“近期”口径，先在平台上切到最新排序并确认卡片确实对应近期视频。
- `Best Video Views`：本次成功识别的视频卡片中的最高播放量；不可见时留空。
- 当前扩展不会给 TikTok 主页计算 `Avg Views` / `Best Video Views`；不要把视频列表的零散数字误当成平均值。
- 未公开、未加载或无法辨认的数值留空，不写 `0`，不根据截图之外的信息估算。
- `Email` 只记主页公开展示或明确链接的邮箱；`Country` 只记有明确证据的国家，不根据语言、受众或所在地猜测。

## 建联状态与人工字段

- 记录主页不等于已发私信、已回复或已合作。只有实际确认的建联进展才可写入 `Contact Status`。
- 当前收集器在未传入状态时会默认写“已私信”。如果本次只是建档，写后检查并纠正该状态，不能把默认值当成事实。
- `Cooperation Type`、`Quote`、`Internal Rating`、`Next Follow-up Date` 属于人工业务字段。更新账号数据时保留已有值，除非用户明确要求修改。
- 不以 KOL 名称去重。先核对平台、Handle 和主页链接；发现同 Handle 跨平台或多个候选行时暂停写入并报告冲突。

## 已知收集器限制

- 当前 XLSX 表头在第 1 行，第一条数据从第 2 行开始；收集器部分查重、编号和最近记录逻辑从第 3 行起步。因此必须直接检查工作簿中的第 2 行，不能仅依赖 WebUI 的最近记录或自动查重结果。
- 收集器的重复查找逻辑可能仅按主页链接或 Handle 命中，跨平台同 Handle 有覆盖风险。遇到此类记录时先检查 XLSX，不要重复点击写入。
- 收集器可能给 Instagram 的 Country 预填 `United States`。没有主页证据时应视为未验证值，不要把默认值当作确认信息。
- 若同一账号已存在，只更新用户要求的账号数据；保留联系状态、报价、合作类型、评分和跟进日期。

## 完成汇报

简要说明写入的工作簿路径、平台/Handle、实际读回的粉丝数和平均播放数，以及留空字段的原因。若发现默认状态、国家或重复覆盖风险，明确指出并纠正能确认的错误；不声称未验证的数据已采集。
