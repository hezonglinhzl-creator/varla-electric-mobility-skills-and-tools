# 广告图动效与即梦视频助手 / Image Motion and Dreamina Video Assistant

**简体中文** | [English](README.en.md)

分析广告或产品图，保留原文、Logo 和产品外形，先预览提示词与命令，再按授权生成视频。

## 功能特性

- 英文提示词加中文核对版
- Logo 扫光、文字入场和产品动效
- 不消耗点数的 dry-run

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 即梦图生视频命令包装器 | [dreamina-image2video](../../apps/dreamina-image2video/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 即梦图生视频命令包装器 (`dreamina-image2video`)

Python、你自己的 Dreamina CLI 和登录；仅预览不要求执行生成。

先进入 `../../apps/dreamina-image2video`。从 JSON 任务生成 CLI 命令，默认 dry-run，--execute 才执行。

1. 先安装对应 image2-motion-agent Skill；包装脚本在 `image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py`。
2. 用自己的图片创建 job.json，包含 image、prompt、duration、poll 和 video_resolution。
3. 先运行 `python image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py --job C:/path/job.json`。
4. 检查输出 `will_consume_credits: false` 和英文/中文提示词。
5. 准备真实生成前运行 `dreamina -h` 核对本机版本并登录；只有明确批准后，才对同一命令加 `--execute`。

[查看完整程序与浏览器插件安装说明](../../apps/dreamina-image2video/README.md)

第三方 CLI 版本和服务额度由使用者自行管理；包装器不提供账号或免费点数。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 一张图片、需要的运动方式、时长和输出比例。 |
| 输出 | 画面分析、英文/中文提示词、JSON 任务文件和生成命令。 |

```text
用 image2-motion-agent，让这张广告图文案从画外进入、Logo 扫光；原文字和电摩外形不变，先给提示词和 dry-run。
```


## 当前限制与常见问题

dry-run 不生成视频；真实执行需自己的 Dreamina CLI、登录状态和点数，并明确使用 --execute。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
