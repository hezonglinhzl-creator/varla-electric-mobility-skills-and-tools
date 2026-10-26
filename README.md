# 电摩社媒与 KOL 完整工具箱 / Varla Electric Mobility Toolkit

**简体中文** | [English](README.en.md)

用于电摩内容制作、海外社媒运营、KOL 建联与回复、订单协作和社媒报表的本地工具集合。先按业务找到程序，再用对应 Skill；完整项目 ZIP 已把两者放在一起。

[完整项目下载](独立下载清单.md) · [已公开独立仓库](独立仓库清单.md) · [浏览器插件安装](docs/browser-extensions.md) · [之前的本地回复插件](plugins/varla-kol-reply/README.md)

## 先按你要做的事选择

| 我想做什么 | 从哪里开始 |
| --- | --- |
| 记录 KOL 和视频表现 | KOL 完整采集器 / KOL 视频监控 |
| 给创作者写回复 | KOL 回复助手，可用 Chrome 面板或本地三选回复插件 |
| 查邮件、审核待处理任务 | Gmail 自动化 / KOL 总控台 |
| 填订单或改合同 | Shopify KOL 订单工具 / 合同更新器 |
| 写剧情或拆参考视频 | UGC 剧情导演 / 视频拆镜头工具 |
| 做社媒周报和核对指标 | 周报 Skill / 社媒洞察核对 |

## 使用前要准备什么

| 类型 | 要准备的东西 |
| --- | --- |
| Windows 本地程序 | Windows、对应程序要求的 Python/Node，以及可以保存文件的目录 |
| 浏览器扩展 | Chrome 或 Edge，以及直接包含 manifest.json 的扩展文件夹 |
| Codex 工作流 | 已登录 Codex，并按项目说明安装 Skill |
| 外部平台功能 | 只为要使用的功能准备自己的 Gmail/飞书/Shopify/AdsPower/即梦权限 |

## 小白第一次使用

1. 打开**完整项目下载清单**，按程序/任务找到对应行，下载该行的**完整项目 ZIP**。ZIP 就是压缩包，已经保存在本合集的 packages 目录，不需要等另建一个 GitHub 仓库。
2. 右键下载的 ZIP，选择**全部解压**，保留整个目录；不要只拿一个 bat 或 exe 文件。
3. 先进入 `apps/<程序名>/README.md`，按说明准备环境、配置自己的账号并启动程序。模板/提示词型项目没有另外的程序后台。
4. 回到完整包根目录，双击 `安装Skill.cmd`，重新打开 Codex。同名 Skill 已存在时会跳过，留意窗口显示。
5. 复制项目 README 中的第一次使用示例，换成自己的文件或链接。先用短测试输入，看到说明中的预期结果后再用于业务。

## 浏览器插件与之前的本地插件

[浏览器插件安装指南](docs/browser-extensions.md)列出了 KOL 记录器、统一采集、网页回复、爆款视频采集的准确目录、支持网站、所需端口、安装步骤和首次使用检查。加载时选能直接看到 manifest.json 的文件夹。

之前的 **Varla KOL回复** 本地插件已补入 `plugins/varla-kol-reply/`，包含仓库插件目录和安装说明。它在 Codex 聊天里给 3 个短回复；Chrome 回复面板提供 6 条分组回复。云端账号身份和登录状态不随源码转移。

## 程序和资料入口

| 程序 / Program | 用途 | 说明 |
| --- | --- | --- |
| KOL 记录器 Chrome 插件 / KOL Recorder Chrome Extension | 在 Instagram/TikTok 创作者主页读取可见字段并写入本地 Excel。 | [README](apps/kol-recorder-extension/README.md) |
| KOL 与爆款视频完整采集器 / KOL and Viral Video Collector Kit | 同时启动 KOL 记录服务和视频采集中心，配套右侧 Varla 浏览器面板。 | [README](apps/varla-kol-collector/README.md) |
| Varla 统一采集 Chrome 插件 / Varla Unified Collector Extension | 在同一面板切换 KOL 记录与视频采集。 | [README](apps/unified-collector-extension/README.md) |
| Instagram 当前指标监控核心 / Instagram Current Metrics Core | 按 shortcode 维护当前指标、首次发现和最后检查时间，再聚合 KOL。 | [README](apps/varla-instagram-monitor/README.md) |
| KOL 网页回复 Chrome 插件 / KOL Browser Reply Extension | 网页右侧 KOL 面板、消息读取、6 条分组回复、手动复制和 ChatGPT Prompt。 | [README](apps/varla-kol-reply-program/README.md) |
| KOL 邮件总控台程序 / KOL Command Center App | 本地 WebUI、四类邮件路由、知识检索、回复预览、人工确认与暂停。 | [README](apps/varla-kol-command-center/README.md) |
| Shopify KOL 订单浏览器工具 / Shopify KOL Browser Order Tool | Excel 单条订单检查、地址核对、fill 和独立提交步骤。 | [README](apps/shopify-order-bot/README.md) |
| 本地视频拆镜头与分镜表 / Local Shot Detection and Storyboards | 视频上传、镜头切分、关键帧、可编辑分镜表和表格导出。 | [README](apps/video-storyboard-tool/README.md) |
| 本地短视频评分分析 / Local Short Video Score Analyzer | 前三秒、剪辑节奏、抽帧、波形和启发式评分导出。 | [README](apps/video-score-analyzer/README.md) |
| 电摩爆款视频采集中心 / eMoto Viral Video Collection Center | 公开链接采集、本地视频列表和结果导出，含 Chrome 采集扩展。 | [README](apps/viral-video-finder-extension/README.md) |
| 社媒排期与模拟发布原型 / Social Scheduling and Mock Publishing Prototype | 本地仪表板、任务验证、BullMQ Worker 和 Mock adapter。 | [README](apps/varla-social-publisher/README.md) |
| 飞书本地 OpenAPI 工具包 / Local Feishu OpenAPI Toolkit | 文档、原生表格、Base 和附件操作，带配置与检查脚本。 | [README](apps/feishu-codex-local/README.md) |
| 即梦图生视频命令包装器 / Dreamina Image-to-Video Command Wrapper | 从 JSON 任务生成 CLI 命令，默认 dry-run，--execute 才执行。 | [README](apps/dreamina-image2video/README.md) |
| 电摩 AI 内容资料与验证工具 / eMoto AI Content Resources and Validation | 剧情导演与产品视频工作流资料，配合提示词结构验证。 | [README](apps/electric-moto-ai-workflow/README.md) |
| 社媒周报模板资料 / Social Reporting Templates | 按平台汇总、日期核对和周月报工作流指引。 | [README](apps/varla-weekly-report/README.md) |

## 哪些能做，哪些还要配置

- 这里分发程序源码；Python/Node 依赖和外部平台账号需要在自己的电脑配置。
- Instagram 监控当前处理采集输入文件，程序成功运行本身不证明刚刚实时抓取过。
- 社媒发布程序是**模拟发布原型**，真实 Meta/TikTok adapter 尚未配置。
- 下单、发邮件、联盟变更和飞书写入按对应项目权限与审核规则执行；此次文档核对没有执行这些业务操作。

## 常见问题

| 问题 | 怎么处理 |
| --- | --- |
| 不知道下哪个 ZIP | 下载对应行的完整项目包，全部解压后再使用。 |
| 浏览器找不到插件 | 开启开发者模式，选直接有 manifest.json 的文件夹，再刷新支持的网站。 |
| 插件显示服务离线 | 启动对应 Python 后端，保持窗口开启，对照 README 检查端口。 |
| 找不到 KOL 台账 | 在 KOL_recorder 或记录器目录运行 create_blank_workbook.py；它不会覆盖已有文件。 |
| 提示端口被占用 | KOL 记录器和短视频评分工具都用 8765，避免同时启动。 |
| 缺少模块或命令 | 按对应程序 README，用同一个运行环境安装依赖。 |

## 隐私和数据

公开包包含指令、源码、安全模板和必要的公开运行资源，不附带真实密钥、登录浏览器、创作者/客户台账、订单、合同、邮件导出和业务媒体。使用自己的数据与配置，并保留在本机；当前分发文件中的内部资源 ID 与邀请链接已替换为占位示例。

## 排版参考

说明结构参考 [GitHub 汉化插件](https://github.com/52cik/github-hans)的功能、环境、安装、使用和常见问题写法。该汉化工具只是文档参考，不是 Varla 包内组件。
