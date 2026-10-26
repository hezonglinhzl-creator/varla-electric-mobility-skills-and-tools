# Dreamina/Jimeng CLI Automation

This skill uses a review-first workflow:

1. The agent inspects the image and writes the English motion prompt plus a Chinese check version.
2. The agent saves the approved prompt as a small UTF-8 JSON job file.
3. The agent runs `scripts/dreamina_image2video.py` without `--execute` to dry-run the exact CLI command.
4. Only after the user confirms, the agent reruns the same command with `--execute`.

## Recommended CLI Source

Prefer the official Dreamina CLI when available:

```powershell
dreamina -h
dreamina user_credit
dreamina image2video --image "C:\path\image.png" --prompt "slow premium camera push in" --duration 5 --poll 30
```

Useful GitHub references checked on 2026-07-06:

- `simonjiang99/dreamina-cli`: official CLI guide and command examples.
- `yuyou-dev/dreamina-cli-skill`: agent-friendly Python wrappers with dry-run and JSON output.
- `Algovate/jimeng-cli`: non-official multi-region CLI. Use only when official `dreamina` does not meet the workflow.

## Job File Shape

```json
{
  "image": "C:\\path\\source.png",
  "prompt": "Keep the original image composition, product, logo, text, typography, colors, and all readable words unchanged. Add subtle premium advertising motion...",
  "duration": 5,
  "poll": 30,
  "video_resolution": "720p"
}
```

## Dry Run

```powershell
python "%USERPROFILE%\.codex\skills\image2-motion-agent\scripts\dreamina_image2video.py" --job "C:\path\job.json"
```

Dry-run output includes `will_consume_credits: false` and the exact command array.

## Execute After Confirmation

```powershell
python "%USERPROFILE%\.codex\skills\image2-motion-agent\scripts\dreamina_image2video.py" --job "C:\path\job.json" --execute
```

The script returns JSON containing stdout, stderr, return code, and the exact command used.

## Safety Rules

- Never execute a generation command before showing the prompt and dry-run command to the user.
- Treat all generation as credit-consuming.
- If `dreamina` is not found, stop after dry-run and tell the user to install/login first.
- If model flags are uncertain, run `dreamina image2video -h` and follow the installed CLI help.
