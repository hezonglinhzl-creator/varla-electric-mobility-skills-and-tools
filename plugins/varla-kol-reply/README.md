# Varla KOL 本地回复插件 / Reply Plugin

**简体中文** | [English](README.en.md)

这是从本机已安装的 Varla KOL回复 插件（0.5.1）整理的可分享指令源码副本。分发清单使用通用名称，省略原账户元数据、缓存 ID 和个人作者字段。不会修改或重新安装本机原插件。

## 能做什么

处理赞助/合作询问时，给出自然、温暖专业、直接三种短回复；索要主页、平均播放和受众国家，不承诺未经确认的送车或赞助。该插件没有 Gmail/Shopify 工具，也不自动发消息。

## 在支持本地插件的 Codex 中安装

1. 下载并解压完整仓库或 KOL 回复完整包，保留 `.agents/plugins/marketplace.json` 和 `plugins/` 的相对位置。
2. 在该根目录的 Codex 终端运行 `codex plugin marketplace add .`（前提是本机版本提供此命令）。
3. 重启桌面应用，打开插件目录，选择 **Varla 本地工具 / Local Tools** 来源，安装或启用 **Varla KOL回复 / KOL Reply**，然后新建对话。
4. 不同客户端支持情况不同；来源未显示时，可打开 `skills/instructions/SKILL.md`，把指令正文和当前创作者消息一起粘贴到聊天使用，不把这种方式当成插件已安装。

## 第一次使用

```text
使用 Varla KOL 回复。创作者问：Could you give me a sponsorship? 请给 3 个英文私信回复，不承诺送车，索要主页、平均播放和受众国家。
```

每次把例子里的消息、平台和产品改为当前任务。复制回复前，用当前已批准知识核对商业条款。

## 和 Chrome 网页插件有什么区别

本插件在 Codex 聊天里输出 3 个回复；apps/varla-kol-reply-program 里的 Chrome 扩展会在网页上显示面板并输出 6 条分组回复。安装一个不会自动装上另一个。

安装方式参考 [OpenAI 本地插件官方说明](https://developers.openai.com/plugins/build/plugins)。本次检查了源码和包结构，尚未在第二个账号/客户端完成实际安装测试。
