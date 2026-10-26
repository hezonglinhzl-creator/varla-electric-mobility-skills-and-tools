# Shopify KOL 订单浏览器工具 / Shopify KOL Browser Order Tool

**简体中文** | [English](README.en.md)

Excel 单条订单检查、地址核对、fill 和独立提交步骤。

## 运行环境

Python 3.11+、AdsPower Local API、自己的 Shopify 后台权限。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 运行 `python -m pip install -r requirements.txt`，再运行 `python -m playwright install chromium`。
2. 把 `.env.example` 复制为 `.env`，填写自己的 AdsPower API、环境 ID 和 SHOPIFY_ADMIN_URL。
3. 按本目录说明准备 `KOL_order.xlsx`，先只放一条你自己的测试资料。
4. 先运行 `python main.py --step adspower`，再运行 `python main.py --step browser`，在自己的浏览器里登录。
5. 运行 `python main.py --step fill`，停在提交前核对；真实提交步骤只在明确授权后执行。

## 成功后应该看到什么

浏览器填入目标订单，CLI 报告核验结果；不会因此自动创建运单。

## 当前功能边界

私密配置、登录会话和订单 Excel 由使用者自己准备；公开包不附带。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 黑窗口闪退 / 找不到 Python | 在当前目录打开 PowerShell，执行 `python --version`。需要安装时从 python.org 安装并勾选 Add Python to PATH，然后重新运行本文命令看具体错误。 |
| 提示缺少模块 | 用启动程序的同一个 Python 安装该程序 requirements 中的依赖。 |
| 页面打不开 / 端口占用 | 对照本文地址和服务日志；先关闭自己正在使用的冲突工具。浏览器扩展不能替代后端。 |
| Excel 保存失败 | 关闭 Excel/WPS 中的文件，检查输出路径后重试一次。 |
| 登录或飞书权限失败 | 使用自己的配置，检查目标资源权限；不要复制别人的 Token。 |

## 本地数据

账号配置、会话、台账和运行结果由使用者在自己电脑生成或配置。公开源码不附带真实客户/KOL 数据、邮箱内容、合同或已登录账号。
