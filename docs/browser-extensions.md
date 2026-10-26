# 浏览器插件安装 / Browser Extension Installation

[简体中文](browser-extensions.md) | [English](browser-extensions.en.md)

先按任务选择一个扩展；同时加载多个采集器版本可能出现重复悬浮面板。使用自己的浏览器账号。

## KOL 记录器 Chrome 插件

`apps/kol-recorder-extension/chrome_kol_recorder_extension`

在 Instagram/TikTok 创作者主页读取可见字段并写入本地 Excel。

Windows、Python 3.10+、Chrome 或 Edge、openpyxl。

### 安装浏览器扩展

1. 打开 Chrome，在地址栏输入 `chrome://extensions/`（Edge 用 `edge://extensions/`）。
2. 打开右上角**开发者模式**，点**加载已解压的扩展程序**。
3. 从当前程序目录进入 `apps/kol-recorder-extension/chrome_kol_recorder_extension`，选择里面直接能看到 `manifest.json` 的文件夹；不要选择 ZIP 或项目最外层。
4. 已打开的网站要刷新一次，再打开插件或侧边面板。支持网站以 manifest 声明为准。
5. 显示本地服务离线时，按上面的步骤启动服务，并保持服务窗口开启。


[程序启动和第一次使用](../apps/kol-recorder-extension/README.md)

## KOL 与爆款视频完整采集器

`apps/varla-kol-collector/chrome_extension`

同时启动 KOL 记录服务和视频采集中心，配套右侧 Varla 浏览器面板。

Windows、Python 3.10+、Chrome/Edge；首次安装依赖需要网络。

### 安装浏览器扩展

1. 打开 Chrome，在地址栏输入 `chrome://extensions/`（Edge 用 `edge://extensions/`）。
2. 打开右上角**开发者模式**，点**加载已解压的扩展程序**。
3. 从当前程序目录进入 `apps/varla-kol-collector/chrome_extension`，选择里面直接能看到 `manifest.json` 的文件夹；不要选择 ZIP 或项目最外层。
4. 已打开的网站要刷新一次，再打开插件或侧边面板。支持网站以 manifest 声明为准。
5. 显示本地服务离线时，按上面的步骤启动服务，并保持服务窗口开启。


[程序启动和第一次使用](../apps/varla-kol-collector/README.md)

## Varla 统一采集 Chrome 插件

`apps/unified-collector-extension/varla_unified_collector_extension_无Moto版`

在同一面板切换 KOL 记录与视频采集。

Chrome/Edge；同时运行本地 8765 和 8766 后端。

### 安装浏览器扩展

1. 打开 Chrome，在地址栏输入 `chrome://extensions/`（Edge 用 `edge://extensions/`）。
2. 打开右上角**开发者模式**，点**加载已解压的扩展程序**。
3. 从当前程序目录进入 `apps/unified-collector-extension/varla_unified_collector_extension_无Moto版`，选择里面直接能看到 `manifest.json` 的文件夹；不要选择 ZIP 或项目最外层。
4. 已打开的网站要刷新一次，再打开插件或侧边面板。支持网站以 manifest 声明为准。
5. 显示本地服务离线时，按上面的步骤启动服务，并保持服务窗口开启。


[程序启动和第一次使用](../apps/unified-collector-extension/README.md)

## KOL 网页回复 Chrome 插件

`apps/varla-kol-reply-program/program/varla-kol-reply-assistant/chrome-extension`

网页右侧 KOL 面板、消息读取、6 条分组回复、手动复制和 ChatGPT Prompt。

Chrome/Edge；备用本地窗口需要 Python。

### 安装浏览器扩展

1. 打开 Chrome，在地址栏输入 `chrome://extensions/`（Edge 用 `edge://extensions/`）。
2. 打开右上角**开发者模式**，点**加载已解压的扩展程序**。
3. 从当前程序目录进入 `apps/varla-kol-reply-program/program/varla-kol-reply-assistant/chrome-extension`，选择里面直接能看到 `manifest.json` 的文件夹；不要选择 ZIP 或项目最外层。
4. 已打开的网站要刷新一次，再打开插件或侧边面板。支持网站以 manifest 声明为准。
5. 显示本地服务离线时，按上面的步骤启动服务，并保持服务窗口开启。


[程序启动和第一次使用](../apps/varla-kol-reply-program/README.md)

## 电摩爆款视频采集中心

`apps/viral-video-finder-extension/chrome_viral_collector_extension`

公开链接采集、本地视频列表和结果导出，含 Chrome 采集扩展。

Python 3.10+、openpyxl、Chrome/Edge。

### 安装浏览器扩展

1. 打开 Chrome，在地址栏输入 `chrome://extensions/`（Edge 用 `edge://extensions/`）。
2. 打开右上角**开发者模式**，点**加载已解压的扩展程序**。
3. 从当前程序目录进入 `apps/viral-video-finder-extension/chrome_viral_collector_extension`，选择里面直接能看到 `manifest.json` 的文件夹；不要选择 ZIP 或项目最外层。
4. 已打开的网站要刷新一次，再打开插件或侧边面板。支持网站以 manifest 声明为准。
5. 显示本地服务离线时，按上面的步骤启动服务，并保持服务窗口开启。


[程序启动和第一次使用](../apps/viral-video-finder-extension/README.md)

## Codex 本地回复插件

之前的三选回复聊天插件不是 Chrome 扩展，见[它自己的安装说明](../plugins/varla-kol-reply/README.md)。
