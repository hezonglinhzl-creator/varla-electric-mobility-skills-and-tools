# KOL 采集器与建联台账 / KOL Collector and Outreach Tracker

**简体中文** | [English](README.en.md)

从创作者主页记录可见数据，写入本地 16 列 Excel 台账，并维护建联状态。

## 功能特性

- KOL 记录器和 Chrome 扩展
- 采集服务与台账初始化
- 粉丝、近期播放、联系方式和进度核对

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| KOL 与爆款视频完整采集器 | [varla-kol-collector](../../apps/varla-kol-collector/README.md) |
| KOL 记录器 Chrome 插件 | [kol-recorder-extension](../../apps/kol-recorder-extension/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

推荐先只启动完整 varla-kol-collector 采集器。独立 KOL 记录器是备用入口，不要再同时占用 8765 端口；同类采集扩展也先只加载一个版本。

### KOL 与爆款视频完整采集器 (`varla-kol-collector`)

Windows、Python 3.10+、Chrome/Edge；首次安装依赖需要网络。

先进入 `../../apps/varla-kol-collector`。同时启动 KOL 记录服务和视频采集中心，配套右侧 Varla 浏览器面板。

1. 双击 `Install_Environment.bat` 安装环境。
2. 在 `KOL_recorder` 内运行 `python create_blank_workbook.py` 创建自己的空白台账。
3. 回到本目录，双击 `Start_Varla_Collector.bat`。
4. 保留两个服务窗口：KOL 8765、视频 8766。
5. 加载 `chrome_extension`，打开目标网站，检查面板内容后记录。

本地地址：`http://127.0.0.1:8766`

[查看完整程序与浏览器插件安装说明](../../apps/varla-kol-collector/README.md)

没有预装真实联系人或结果 Excel；首次需自行初始化台账。

### KOL 记录器 Chrome 插件 (`kol-recorder-extension`)

Windows、Python 3.10+、Chrome 或 Edge、openpyxl。

先进入 `../../apps/kol-recorder-extension`。在 Instagram/TikTok 创作者主页读取可见字段并写入本地 Excel。

1. 在本目录打开 PowerShell，运行 `python -m pip install -r requirements.txt`。
2. 先运行 `python create_blank_workbook.py`，只在没有台账时生成空白 16 列文件。
3. 双击 `start_kol_recorder.bat`，保留服务窗口。
4. 安装下方扩展后打开创作者主页，先检查识别字段，再点击记录。

本地地址：`http://127.0.0.1:8765`

[查看完整程序与浏览器插件安装说明](../../apps/kol-recorder-extension/README.md)

只读页面可见内容，隐藏邮箱和缺失指标应留空。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 创作者公开主页以及你自己的空白或现有台账。 |
| 输出 | 本地 outputs/varla_kol_tracker.xlsx，不含仓库预置联系人。 |

```text
使用 kol建联数据表格skill，核对这个创作者主页的粉丝和近期播放，先给可见证据，再记录到我的本地台账；看不到的留空。
```


## 当前限制与常见问题

平台页面变化会影响解析；看不到邮箱或播放量时留空。修改 Excel 前先关闭 Excel/WPS。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
