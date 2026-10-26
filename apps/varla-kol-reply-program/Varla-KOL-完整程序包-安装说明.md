# Varla KOL Reply Assistant 完整程序包安装说明

这个程序包适合发给别的电脑完整使用，里面包含：

- 完整 Chrome 插件项目
- 可选的 Codex skill
- 本说明文件

## 目录结构

- `program/varla-kol-reply-assistant/`
  - Chrome 插件完整项目
  - 本地小窗口备用 UI
- `skill/varla-kol-reply-assistant/`
  - Codex skill

## 直接使用 Chrome 插件

1. 解压完整程序包 zip
2. 打开 Chrome，进入 `chrome://extensions/`
3. 打开右上角“开发者模式”
4. 点击“加载已解压的扩展程序”
5. 选择：
   - `program/varla-kol-reply-assistant/chrome-extension`
6. 安装后，打开以下任一页面：
   - Instagram
   - TikTok
   - Meta Business Suite
   - Gmail
7. 页面右侧会出现 `KOL` 小按钮
8. 点击后展开面板，即可读取文本、生成回复、OCR 粘贴截图

## OCR 使用方式

- 复制聊天截图
- 点击插件里的“截图识别区”
- 按 `Ctrl+V`

如果目标页面不稳定，也可以：

- 点击“读取剪贴板截图”
- 或点击“选择图片文件”

## 本地小窗口备用模式

如果对方不想先装 Chrome 插件，也可以先使用备用本地界面：

- 双击 `program/varla-kol-reply-assistant/打开小窗口.bat`
- 或双击 `program/varla-kol-reply-assistant/打开UI.bat`

说明：

- 这是备用模式
- 主产品形态仍然是 Chrome 插件悬浮窗

## 安装 Codex skill（可选）

如果对方也要继续维护这个工具，可以把 skill 一起装上：

1. 把 `skill/varla-kol-reply-assistant` 整个文件夹复制到：
   - `C:\Users\<用户名>\.codex\skills\`
2. 重启 Codex

这样 Codex 就能识别这套 KOL 回复工具的维护 skill。

## 推荐交付方式

如果对方只是“使用程序”：

- 只看 `program/`

如果对方还要“继续维护 / 改代码 / 调话术”：

- `program/` + `skill/` 一起给

## 注意

- Chrome 插件是主要使用方式
- skill 不是程序本体，而是给 Codex 的维护说明包
- 如果对方修改了项目路径，不影响插件使用；只要能正常加载 `chrome-extension` 文件夹即可
