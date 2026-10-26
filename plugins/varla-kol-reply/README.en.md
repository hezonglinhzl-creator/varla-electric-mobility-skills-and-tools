# Varla KOL Reply / 本地回复插件

[简体中文](README.md) | **English**

This is a shareable instruction-source copy based on the locally installed Varla KOL回复 plugin (0.5.1). Its distribution manifest uses a generic identity and omits the original account metadata, cache ID and personal author fields. It does not modify or reinstall the original plugin.

## What it does

For sponsorship inquiries it drafts three options: casual, warm-professional and direct. It asks for profile links, average views and audience countries, and avoids unconfirmed free-bike promises. It has no Gmail/Shopify tool or automatic send action.

## Install in a supported local Codex client

1. Download and extract the whole repository or complete reply-assistant bundle, keeping `.agents/plugins/marketplace.json` and `plugins/` together.
2. In a Codex terminal at that root, run `codex plugin marketplace add .` if the command is available.
3. Restart the desktop app, open the Plugins Directory, select **Varla Local Tools**, then install/enable **Varla KOL Reply** and start a new chat.
4. Availability varies by client. If the source is not shown, open `skills/instructions/SKILL.md` and paste its instruction body plus your new creator message into your chat; this uses the same rules without claiming a plugin install.

## Try it

```text
Use Varla KOL Reply. A creator asks: Could you give me a sponsorship? Draft three English DM replies. Do not promise a free bike. Ask for profile links, average views and audience countries.
```

Replace the example message/platform/product with the current task. Check commercial terms against current approved knowledge before copying a reply.

## Different from the Chrome extension

This plugin works in a Codex chat and produces three replies. The browser extension in apps/varla-kol-reply-program adds a webpage panel and six grouped options. Installing one does not install the other.

[Official local-plugin packaging/install reference](https://developers.openai.com/plugins/build/plugins). Source/package structure was checked; installation in a second account/client has not been exercised.
