# KOL 合作合同更新器 / KOL Collaboration Contract Updater

**简体中文** | [English](README.en.md)

从自己的 Word 合同模板生成独立副本，替换创作者、车型、佣金、日期与收货资料并检查旧数据。

## 功能特性

- 保留 DOCX 原排版
- 输出独立合同副本
- 替换资料后复核交付条款

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| Skill 指令 | [SKILL.md](./SKILL.md) |

本项目是 Codex 工作流/脚本 Skill，没有另外一套需要启动的网页后台。

## 1. 先准备程序

无需另装程序。准备已登录的 Codex 和下方输入资料即可；带 Python 脚本的项目再按本页脚本说明安装依赖。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 自己的 DOCX 模板和已确认的合同字段。 |
| 输出 | 新的 DOCX；PDF 需用 Word/WPS/LibreOffice 导出或另行处理。 |

```text
使用 varla-kol-contract-updater，先列出这份模板可替换字段，使用虚构资料生成预览副本，保留原模板。
```

## 合同脚本

在 `skill/varla-kol-contract-updater` 中运行。示例资料是虚构的，输入必须是你自己的 DOCX 模板。

```powershell
python -m pip install python-docx
python scripts/update_contract.py --input C:/path/template.docx --output C:/path/preview.docx --name "Sample Creator" --email creator@example.com
```

## 当前限制与常见问题

脚本依赖 python-docx；公开包不含真实合同和签名。商业条款必须来自确认资料。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
