# 电摩 UGC 剧情编导 / eMoto UGC Story Director

**简体中文** | [English](README.en.md)

把电摩创意整理为可执行的双段剧情、人物资产、首帧和连续镜头提示词。

## 功能特性

- 人物表情与身体反应
- 产品外形和对白说话者固定
- 时间块分镜与提示词结构检查

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 电摩 AI 内容资料与验证工具 | [electric-moto-ai-workflow](../../apps/electric-moto-ai-workflow/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 电摩 AI 内容资料与验证工具 (`electric-moto-ai-workflow`)

Codex；可选 Python 用于验证提示词文件。

先进入 `../../apps/electric-moto-ai-workflow`。剧情导演与产品视频工作流资料，配合提示词结构验证。

1. 这是内容工具资料集合，先使用完整包根目录的 `安装Skill.cmd`。
2. 把自己的产品图和已确认参数交给 Codex，使用 emoto-ugc-story-director。
3. 先检查分镜和提示词，再选择自己的视频生成平台。
4. 需要结构检查时运行 `python skills/emoto-ugc-story-director/scripts/validate_prompt.py C:/path/prompt.md`。

[查看完整程序与浏览器插件安装说明](../../apps/electric-moto-ai-workflow/README.md)

没有独立的桌面视频生成程序或预装生成账号。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 产品参考图、目标市场、剧情方向和时长。 |
| 输出 | 剧情、人物三视图提示词、首帧、视频提示词和发布文案。 |

```text
用 emoto-ugc-story-director，基于这张电摩参考图做双 10 秒车库惊喜剧情，先交分镜和中文核对版。
```


## 当前限制与常见问题

配套 electric-moto-ai-workflow 是脚本与 Skill 资料集合，不是双击即可生成视频的桌面软件。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
