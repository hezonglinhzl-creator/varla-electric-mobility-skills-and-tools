# KOL Browser Reply Extension / KOL 网页回复 Chrome 插件

[简体中文](README.md) | **English**

A floating KOL panel, message reading, six grouped replies, manual copy and a ChatGPT prompt.

## Requirements

Chrome/Edge; the optional local-window mode requires Python.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Load the Chrome extension folder below containing manifest.json.
2. Open Instagram, TikTok, Meta Business Suite or Gmail and refresh existing tabs.
3. Open the KOL panel, select a message, use Read and check platform, stage, tone and product.
4. Generate six replies, verify current product/policy facts and copy one manually.
5. For ChatGPT, generate/copy the prompt and paste it yourself. The fallback local window starts with `program/varla-kol-reply-assistant/打开UI.bat`.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `program/varla-kol-reply-assistant/chrome-extension` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


## Expected result

The page shows casual, formal and short reply groups. The browser extension does not require a local server port.

## Current limits

Templates may contain historical product facts; verify them against current knowledge. It assists drafting/copying and does not send automatically.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Window closes / Python missing | Open PowerShell in this directory, run `python --version`, install Python from python.org with Add Python to PATH if needed, then rerun the documented command. |
| Missing module | Install the program's requirements using the same Python executable used to launch it. |
| Page does not open / port occupied | Check the URL and service log; stop your own conflicting tool before retrying. A browser extension cannot replace its local backend. |
| Workbook cannot be saved | Close the file in Excel/WPS, verify the output path and retry once. |
| Account or Feishu permission failure | Use your own configuration and check resource permissions. Do not copy another person's tokens. |

## Local data

Your credentials, browser sessions, workbooks and outputs are created/configured locally. The public source does not include real customer/creator records, mailboxes, contracts or logged-in accounts.
