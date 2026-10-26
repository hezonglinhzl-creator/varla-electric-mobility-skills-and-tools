# Browser Extension Installation / 浏览器插件安装

[简体中文](browser-extensions.md) | [English](browser-extensions.en.md)

Choose one task-specific extension first; installing multiple collector variants can create duplicate floating panels. Use your own browser account.

## KOL Recorder Chrome Extension

`apps/kol-recorder-extension/chrome_kol_recorder_extension`

Read visible Instagram/TikTok creator fields and write a local Excel tracker.

Windows, Python 3.10+, Chrome/Edge and openpyxl.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `apps/kol-recorder-extension/chrome_kol_recorder_extension` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


[Program setup and first task](../apps/kol-recorder-extension/README.en.md)

## KOL and Viral Video Collector Kit

`apps/varla-kol-collector/chrome_extension`

Start the KOL recorder and video center together with the floating Varla browser panel.

Windows, Python 3.10+, Chrome/Edge; network access for initial dependencies.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `apps/varla-kol-collector/chrome_extension` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


[Program setup and first task](../apps/varla-kol-collector/README.en.md)

## Varla Unified Collector Extension

`apps/unified-collector-extension/varla_unified_collector_extension_无Moto版`

Switch between KOL records and video collection in one panel.

Chrome/Edge plus the local services on ports 8765 and 8766.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `apps/unified-collector-extension/varla_unified_collector_extension_无Moto版` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


[Program setup and first task](../apps/unified-collector-extension/README.en.md)

## KOL Browser Reply Extension

`apps/varla-kol-reply-program/program/varla-kol-reply-assistant/chrome-extension`

A floating KOL panel, message reading, six grouped replies, manual copy and a ChatGPT prompt.

Chrome/Edge; the optional local-window mode requires Python.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `apps/varla-kol-reply-program/program/varla-kol-reply-assistant/chrome-extension` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


[Program setup and first task](../apps/varla-kol-reply-program/README.en.md)

## eMoto Viral Video Collection Center

`apps/viral-video-finder-extension/chrome_viral_collector_extension`

Public-link collection, a local video list and exports with a Chrome capture extension.

Python 3.10+, openpyxl and Chrome/Edge.

### Load the browser extension

1. Open Chrome and enter `chrome://extensions/` in its address bar (Edge: `edge://extensions/`).
2. Turn **Developer mode** on, then choose **Load unpacked**.
3. Select `apps/viral-video-finder-extension/chrome_viral_collector_extension` relative to this program folder. Select the folder containing `manifest.json`, not a ZIP or the parent project.
4. Refresh an already-open supported website and open the extension/panel. The extension only works on the sites listed in its manifest.
5. If backend status is offline, start the local service described above and keep its window open.


[Program setup and first task](../apps/viral-video-finder-extension/README.en.md)

## Codex local reply plugin

The earlier three-option chat plugin is not a Chrome extension. See [its own instructions](../plugins/varla-kol-reply/README.en.md).
