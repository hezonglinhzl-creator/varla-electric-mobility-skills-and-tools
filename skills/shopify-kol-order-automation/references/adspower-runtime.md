# AdsPower Runtime and Playwright Attachment

Use the existing implementation:

- `shopify_order_bot/config.py`
- `shopify_order_bot/adspower_client.py`
- `shopify_order_bot/shopify_browser.py`

Do not place the AdsPower API key, profile cookie, or WebSocket endpoint in this Skill or in chat output.

## Required local configuration

The project `.env` supplies:

```text
SHOPIFY_ADMIN_URL=...
ADSPOWER_API_URL=http://local.adspower.net:50325
ADSPOWER_API_KEY=<read from local .env>
ADSPOWER_PROFILE_ID=...
```

Read these through `config.SETTINGS`. Never print `ADSPOWER_API_KEY`.

## Diagnose the configured environment

From the project folder:

```powershell
& ".\.venv\Scripts\python.exe" main.py --step adspower
```

This calls the Local API through `AdsPowerClient.list_profiles()`:

1. Prefer `POST /api/v2/browser-profile/list`.
2. Fall back to `GET /api/v1/user/list`.
3. If multiple profiles exist and `.env` has no `ADSPOWER_PROFILE_ID`, stop and report the safe profile
   names/numbers/IDs; never guess.

## Start or reuse the browser

```powershell
& ".\.venv\Scripts\python.exe" main.py --step browser
```

The runtime:

1. Checks `GET /api/v1/browser/active` for the configured profile.
2. Reuses the returned CDP endpoint when the browser is already active.
3. Otherwise prefers `POST /api/v2/browser-profile/start` with:

```json
{"profile_id": "<configured id>", "last_opened_tabs": "0", "proxy_detection": "0"}
```

4. Falls back to `GET /api/v1/browser/start` with `open_tabs=0` and `ip_tab=0`.
5. Extracts the returned Puppeteer/CDP WebSocket endpoint.
6. Calls Playwright `chromium.connect_over_cdp(...)`.
7. Reuses the existing Shopify Admin page when present; otherwise uses another normal page or opens one.

The client throttles real Local API requests to about one request per second and sets `trust_env=False`
so system proxies do not intercept localhost calls.

## Browser lifecycle

- Keep the AdsPower browser profile running between orders so login cookies persist.
- Disconnect Playwright after a command without destroying the profile session.
- Do not call `stop_browser` at the end of each order.
- Stop the profile only when the user explicitly asks to close AdsPower; stopping closes the browser
  process but must not delete profile data.
- Do not launch `chromium.launch()` or a new persistent profile alongside AdsPower for Shopify work.

## Page selection and recovery

- Prefer the existing page whose URL contains `admin.shopify.com`.
- Do not refresh an already open Shopify page to recover from a locator failure.
- Inspect the current DOM and saved screenshot, then continue from the current stage.
- If Shopify shows connection verification/CAPTCHA/risk verification, stop automation and leave the
  AdsPower window open for the user.
- After the user confirms verification is complete, reconnect to the same profile and resume from the
  first unfinished Excel row.

## Safe errors

AdsPower failures must report the failed operation/path without authorization headers, API keys,
cookies, or raw CDP credentials.
