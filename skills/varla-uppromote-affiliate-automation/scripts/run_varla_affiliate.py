#!/usr/bin/env python3
"""Run the VarlaAffiliateAutomation package linked into this skill."""
from pathlib import Path
import runpy


entrypoint = Path(__file__).resolve().parent / "VarlaAffiliateAutomation" / "varla_affiliate.py"
if not entrypoint.is_file():
    raise SystemExit(f"脚本链接无效：{entrypoint}")
runpy.run_path(str(entrypoint), run_name="__main__")
