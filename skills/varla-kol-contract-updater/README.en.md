# KOL Collaboration Contract Updater / KOL 合作合同更新器

[简体中文](README.md) | **English**

Create a separate copy of your Word contract, update creator/product/commission/date/address details and check for leftover data.

## Features

- Preserve DOCX layout
- Write a separate output copy
- Review deliverables and replaced details

## What is included

| Part | Location |
| --- | --- |
| Skill instructions | [SKILL.md](./SKILL.md) |

This project is a Codex skill/workflow with its own instructions or scripts; it has no separate app server to launch.

## 1. Set up the program first

No app installation is required. Prepare Codex and the input listed below. If the skill includes Python scripts, install the stated script dependency before running them.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Your DOCX template and confirmed agreement fields. |
| Output | A new DOCX; PDF export needs Word/WPS/LibreOffice or a separate conversion step. |

```text
Use varla-kol-contract-updater to inspect replaceable fields and generate a preview copy using synthetic details while preserving my template.
```

## Contract script

Run inside `skill/varla-kol-contract-updater`. Example details are synthetic; supply your own DOCX template.

```powershell
python -m pip install python-docx
python scripts/update_contract.py --input C:/path/template.docx --output C:/path/preview.docx --name "Sample Creator" --email creator@example.com
```

## Limits and troubleshooting

Requires python-docx. Real contracts/signatures are excluded, and commercial terms must come from confirmed inputs.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
