# Chrome Extension Map

Use this reference when changing UX, OCR behavior, or browser-surface behavior.

## Main Product Surface

- Primary surface: `chrome-extension/contentScript.js`
- The extension injects a floating widget into supported sites:
  - Instagram
  - TikTok
  - Meta Business Suite
  - Gmail

## Current Behavior

- Small collapsed launcher labeled `KOL`
- Click expands the panel
- Drag moves the launcher
- Panel is designed as a compact right-side helper
- Reply output is grouped into:
  - Natural 2
  - Formal 2
  - Short 2

## OCR Flow

- OCR assets are bundled locally under `chrome-extension/vendor/`
- Screenshot intake paths:
  - click OCR zone then paste
  - drag image into OCR zone
  - explicit read-from-clipboard button
  - file-picker fallback
- When OCR breaks on target pages, check:
  - `manifest.json` permissions
  - `web_accessible_resources`
  - Tesseract import shape
  - worker startup mode
  - language path

## High-Risk Files

- `contentScript.js`: easy to break interaction state, drag state, OCR state, or insert behavior
- `manifest.json`: permission and resource exposure changes affect OCR and host behavior

## Validation

- Run JS syntax checks after any `contentScript.js` or `popup.js` edits
- Validate manifest JSON after permission/resource edits
- Ask the user to reload the Chrome extension before retesting
