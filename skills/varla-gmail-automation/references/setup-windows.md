# Windows Setup and Migration

## Requirements

- Windows 10 or 11
- Python 3.11 or newer
- Chrome
- A Google Cloud project with Gmail API enabled
- An OAuth 2.0 Desktop app client
- The intended Gmail account added as a test user while the OAuth app is in Testing

## Install from the private GitHub repository

1. Install Git and GitHub CLI.
2. Authenticate GitHub CLI to the account that can access the private repository.
3. Clone the dedicated skill repository.
4. Run the installer from the cloned repository:

```powershell
git clone https://github.com/hezonglinhzl-creator/varla-gmail-automation.git
Set-Location .\varla-gmail-automation
powershell -ExecutionPolicy Bypass -File `
  .\scripts\install_skill.ps1
```

The installer refuses to overwrite an existing skill. Restart Codex after installation.

## OAuth preparation

In Google Cloud:

1. Enable Gmail API.
2. Configure the OAuth consent screen.
3. Add the intended mailbox as a test user when the app is in Testing.
4. Create an OAuth client ID of type **Desktop app**.
5. Download the JSON to a private folder outside the Git repository.

Recommended local paths:

```text
C:\Users\<user>\AppData\Local\VarlaGmail\credentials.json
C:\Users\<user>\AppData\Local\VarlaGmail\token.json
```

Never copy a token from another computer as the normal migration method. Reauthorize on the new computer.

## Chrome profile selection

Use `--manual-browser` when the automatic browser opens the wrong Chrome profile. Copy the printed authorization URL into the Chrome profile signed in to the intended Gmail account.

If `localhost` shows `ERR_BLOCKED_BY_CLIENT`:

1. Temporarily disable the blocking extension for localhost.
2. Keep the CLI process running.
3. Retry the authorization URL.
4. Confirm that the CLI prints an authorization success result.

The browser error page alone does not prove whether authorization succeeded; verify with the CLI `verify` command.

## Proxy handling

If command-line access to Google or GitHub times out while Chrome works, copy the local proxy address from Windows proxy settings and set it only for the current PowerShell session:

```powershell
$env:HTTPS_PROXY = "http://127.0.0.1:PORT"
$env:HTTP_PROXY = "http://127.0.0.1:PORT"
```

Do not hard-code a machine-specific proxy address into the skill.

## Install Python dependencies

```powershell
python -m pip install -r `
  "$env:USERPROFILE\.codex\skills\varla-gmail-automation\scripts\requirements.txt"
```

Run `authorize`, then `verify`. Do not test migration by sending a live email until the account and recipient are explicitly confirmed.
