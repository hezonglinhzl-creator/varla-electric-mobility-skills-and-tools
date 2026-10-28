# 安装包检查与修复 / Package Review — 2026-10-28

本次检查对象是公开分发版；没有改动本机正在使用的原业务程序、账号或台账。

| 项目 | 修复内容 |
| --- | --- |
| KOL 总控台 | 后台垃圾邮件清理默认关闭，显式设置 `VARLA_ENABLE_JUNK_CLEANUP=true` 才启用定时线程；手动识别与清理仍可能修改邮箱。 |
| 总控台首次启动 | 未提供业务知识时可进入设置界面，使用空知识索引，回复返回 `needs_knowledge` / 人工处理。已有知识包仍执行完整哈希校验。 |
| 配置说明 | 修正 Gmail OAuth 文件实际路径，明确 config.example.json 仅为参考；支持通过环境变量设置数据目录、核验邮箱和回复程序位置。 |
| Skill 安装器 | 为 20 个 Skill 写入实际程序位置映射 `PACKAGE-LOCATION.json`；搬家后重跑安装器即可刷新，默认保留已有 Skill 内容。 |
| KOL 回复扩展 | 补齐 OCR 所需的 Tesseract 主脚本、Worker 与许可文件。 |
| KOL 台账 | 修正空白台账首条记录行号，避免重复采集时忽略首条；仅采集主页默认记为“待建联”。 |
| 发布原型 | 启动脚本改用系统 Node/npm，不依赖未提供的便携 Node/Redis；默认只打开静态页面，不启动 Worker。 |
| 文档与脱敏 | 移除当前文件中遗留的短 view ID；明确发布器没有完整上传/排期闭环，health 为固定 503 占位接口。 |

## 已验证

- 35 个 ZIP 的内容与源码清单一致。
- 20 个独立完整包以及合集安装器在隔离目录安装成功；重装保留用户改动并刷新路径。
- 7 个扩展清单中的 20 处资源引用均存在。
- 两个台账程序通过虚构记录的新增、状态更新和重复记录检查。
- 总控台假服务测试：默认后台清理调用为 0；显式启用后才调用。缺少知识时不会产生已核验业务回复。
- PowerShell 语法与发布器启动前诊断已检查。

## 验证边界

已有同名 Skill 时，默认安装会保留旧正文，只刷新程序路径。如果需要用本版指令替换旧版，在完整包目录运行以下命令；安装器会先复制旧目录为带时间戳的备份，再合并更新，不删除旧文件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Overwrite
```

首次安装不用加 `-Overwrite`。保留整个解压目录；安装器不会把程序依赖或账号一起装进 Codex。

没有操作真实邮箱、下单、写飞书业务数据或发布社媒内容；也没有在第二个账号完成浏览器 OCR 的完整界面测试。外部平台权限、第三方服务和自己的运行依赖仍需配置。发布程序当前仍是静态/Mock 原型。

本次修正当前分支和新下载包，不重写 Git 历史。维护者应独立审查历史提交是否仍保留旧标识，再决定是否需要清理历史。

## English

This review changes the public distribution, not the operator's original live tools or business data. It disables background mail cleanup by default, allows a knowledge-empty setup UI with no verified replies, corrects configuration documentation, records real program locations during Skill installation, restores OCR runtime scripts, fixes first-record handling and contact-status defaults, and makes the publishing launcher use system Node/npm for a static dashboard only.

Checks cover all 35 ZIPs, isolated installation of 20 Skills plus the hub installer, 20 resource references across seven extension manifests, synthetic workbook updates, fake-service lifecycle checks, PowerShell parsing and launcher diagnostics. No live mail, order, Feishu or publishing operations were executed. Full OCR interaction on a second account was not tested. History is not rewritten by this update.
