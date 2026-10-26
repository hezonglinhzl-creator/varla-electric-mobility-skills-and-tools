# Varla KOL 智能回复器 MVP

## 怎么打开

双击 `打开小窗口.bat` 或 `打开UI.bat`。

它会自动启动一个本地小服务，再优先用 Chrome / Edge 的小窗口模式打开。脚本会避开你已经在用的 `127.0.0.1:8766`，并从 `8765/8767/8768...` 里自动选择空闲端口。

## Chrome 插件安装

1. 打开 Chrome，进入 `chrome://extensions/`。
2. 打开右上角 `开发者模式`。
3. 点击 `加载已解压的扩展程序`。
4. 选择这个目录：`D:\项目\himiway\KOL回复训练\脚本\varla-kol-reply-assistant\chrome-extension`
5. 打开 Instagram / TikTok / Meta Business Suite / Gmail 后，网页右侧会出现一个 `KOL` 小按钮。
6. 点击 `KOL` 小按钮会动画展开右侧小界面；再次点击 Chrome 插件图标或面板里的 `×` 可以收起。
7. 选中一段 KOL 文本，点面板里的 `读取`，再点 `生成 6 条回复`。
8. 生成结果会放在一个总的 `回复结果` 折叠区里，默认打开；里面按 `自然 2条 / 正式 2条 / 简短 2条` 分区展示，方便一键收起后使用 ChatGPT Prompt。

正式插件版是网页右侧悬浮窗，不需要本地 IP 或端口。只有备用本地小窗口会使用 `127.0.0.1`，脚本会跳过 `8766` 并自动找空闲端口。

## 怎么用

1. 把 Instagram / TikTok / Gmail 里的 KOL 消息粘贴到文本框。
2. 点击 `自动识别阶段`。
3. 选择语气和产品。
4. 点击 `生成 6 条回复`。
5. 从折叠分组里展开需要的类型，挑一个回复，点击 `Copy`。

## ChatGPT 桥接模式

点击 `Generate ChatGPT Prompt`，再点 `Copy Prompt for ChatGPT`，然后点 `Open ChatGPT` 手动粘贴。这个模式不调用 API，也不会自动发送消息。

## 文件说明

- `index.html`: 本地 UI 入口。
- `src/app.js`: 回复生成、阶段识别、Prompt 生成逻辑。
- `src/stageRules.js`: 20 个合作阶段规则。
- `knowledge_seed/templates.json`: 本地回复模板。
- `knowledge_seed/product_specs.json`: M5S / M7S 参数。
- `knowledge_seed/Varla_KOL_常见问题回复库.md`: 内部常见问题话术库，按自然 / 正式 / 简短整理。
- `tools/extract_training_data.py`: 从训练目录抽取 docx / xlsx 文本的辅助脚本。
- `chrome-extension/`: Chrome 插件 MVP 壳。
