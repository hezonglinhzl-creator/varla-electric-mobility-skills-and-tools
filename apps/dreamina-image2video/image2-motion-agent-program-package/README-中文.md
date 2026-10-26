# Image2 Motion Agent 完整分发包

这是给其他电脑使用的 Windows 分发包，包含：

- `image2-motion-agent` Codex skill
- 一键安装入口 `install.cmd`
- PowerShell 安装脚本 `install.ps1`
- Dreamina/即梦 CLI 下载、安装和 PATH 检查
- GPT 生成提示词后，先 dry-run 预览命令，再确认提交的安全流程

## 使用方法

1. 解压整个压缩包。
2. 双击 `install.cmd`。
3. 安装完成后，重启 Codex。
4. 打开新的 PowerShell，运行：

```powershell
dreamina login
```

5. 登录对方自己的即梦/Dreamina 账号后，就可以在 Codex 里这样用：

```text
使用 image2-motion-agent，分析这张 VARLA 广告图，先给英文提示词和中文检查版，我确认后再导入即梦生成。
```

## 默认工作流

- 先看图，再生成提示词。
- 英文提示词用于即梦/Dreamina。
- 中文检查版用于人工确认。
- 用户确认后才提交任务，避免浪费 credits。
- 字幕/文案默认从画外移入或做干净入场。
- Logo 默认可做发光或扫光。
- 场景和骑行动作要有运动感。
- 原文字、参数、Logo、产品外形不能乱改。
- 临时质量检查帧可以生成，但分析完成后只删除明确的单个文件路径，不批量删除目录。

## 注意

- 这个包不包含任何个人登录状态、cookie、token 或账号信息。
- 生成视频会消耗使用者自己即梦/Dreamina 账号的 credits。
- 如果对方电脑已经安装 Dreamina CLI，安装器会复用已有文件。
