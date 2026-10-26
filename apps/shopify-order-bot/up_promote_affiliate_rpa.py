"""One-record UpPromote affiliate setup through an existing AdsPower profile.

Safe defaults: this script only previews a Feishu record.  ``--apply`` is
required before it writes Shopify/UpPromote or Feishu.  Email is a separate,
explicit ``--send --confirm SEND`` action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Frame, Locator, Page

try:
    from .config import Settings, configure_logging
    from .shopify_browser import AutomationStepError, ShopifyOrderBrowser
except ImportError:  # allows direct execution from the bot folder
    from config import Settings, configure_logging
    from shopify_browser import AutomationStepError, ShopifyOrderBrowser


UPPROMOTE_AFFILIATES_URL = (
    "https://admin.shopify.com/store/varla-scooterus/apps/"
    "affliate-by-secomapp/admin/affiliates?menu=true"
)
DESTINATION_URL = "https://varlascooter.com/collections/electric-dirt-bike"
PROGRAM_NAME = "KOL - $100"
COLLECTION_NAME = "Electric Dirt Bike"
APP_TOKEN = "VZ58b0AKdaJNiAs3kc7cOOGZncc"
TABLE_ID = "tblKwzo7QwvYhtjy"


@dataclass(frozen=True)
class AffiliateCandidate:
    record_id: str
    name: str
    email: str
    code: str


@dataclass(frozen=True)
class AffiliateSetupPlan:
    candidate: AffiliateCandidate
    existing_link: str
    needs_browser_setup: bool
    needs_feishu_writeback: bool
    needs_email_send: bool


def normalize_code_link(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("link", "")
    return str(value or "").strip()


def record_matches_lookup(fields: dict[str, Any], lookup: str) -> bool:
    """Match a creator by an exact email, KOL name, or code name."""
    needle = lookup.strip().casefold()
    return bool(needle) and needle in {
        str(fields.get("Email") or "").strip().casefold(),
        str(fields.get("KOL Name") or "").strip().casefold(),
        str(fields.get("code name") or "").strip().casefold(),
    }


def eligible_candidates(records: list[dict]) -> list[AffiliateCandidate]:
    candidates: list[AffiliateCandidate] = []
    for record in records:
        fields = record.get("fields", {})
        name = str(fields.get("KOL Name") or "").strip()
        email = str(fields.get("Email") or "").strip().casefold()
        code = str(fields.get("code name") or "").strip()
        if name and email and code and not normalize_code_link(fields.get("code link")):
            candidates.append(AffiliateCandidate(str(record["record_id"]), name, email, code))
    return candidates


def _validate_candidate(candidate: AffiliateCandidate) -> None:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", candidate.email):
        raise ValueError("Affiliate email is not valid.")
    if not re.fullmatch(r"[A-Za-z0-9-]{2,64}", candidate.code):
        raise ValueError("Affiliate code may contain only letters, numbers, hyphens.")
    if not candidate.name.strip():
        raise ValueError("Affiliate name is required.")


def make_setup_plan(candidate: AffiliateCandidate, code_link: object) -> AffiliateSetupPlan:
    _validate_candidate(candidate)
    existing_link = normalize_code_link(code_link)
    return AffiliateSetupPlan(
        candidate=candidate,
        existing_link=existing_link,
        needs_browser_setup=not bool(existing_link),
        needs_feishu_writeback=not bool(existing_link),
        needs_email_send=not bool(existing_link),
    )


def build_affiliate_email(name: str, code: str, link: str) -> tuple[str, str]:
    name, code, link = name.strip(), code.strip(), link.strip()
    if not name or not code or not link:
        raise ValueError("Affiliate email needs name, code, and link.")
    subject = "Your Varla affiliate code and link"
    body = f"""Hi {name},

Thank you so much for your support and for partnering with Varla! 🙌

Your personal affiliate information is below:

Discount Code: {code}

Affiliate Link: {link}

Your audience can use this code to receive a discount, and any successful orders through your link or code will be tracked automatically.

You can check your sales performance, orders, and commission results through this tracking system.

When we created your account on the affiliate platform, an automated system email was sent to you with your UpPromote platform access link, account information, and login details.

Please check your inbox for that email. If you don't see it, please also check your spam, junk, or promotions folder, as it may have been filtered there.

If you still cannot find it, please let us know and we'll help you check it.

We truly appreciate your support and the effort you put into creating content for Varla. We're excited to see the impact we can create together and look forward to building a long-term partnership with you!

Thank you again! ❤️

Best regards,
Team Member
Varla Team"""
    return subject, body


class FeishuBase:
    """Small adapter around the approved local Feishu OpenAPI helper."""

    def __init__(self, app_token: str, table_id: str) -> None:
        skill_scripts = Path.home() / ".codex" / "skills" / "feishu-codex-local" / "scripts"
        sys.path.insert(0, str(skill_scripts))
        from feishu_docs import get_tenant_access_token, http_json, load_config  # type: ignore

        self._http_json = http_json
        config = load_config()
        self._token = get_tenant_access_token(config)
        self.app_token, self.table_id = app_token, table_id

    def find_one(self, lookup: str) -> tuple[AffiliateCandidate, object]:
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records?page_size=500"
        payload = self._http_json("GET", url, token=self._token)
        matches = []
        for record in payload.get("data", {}).get("items", []):
            fields = record.get("fields", {})
            if record_matches_lookup(fields, lookup):
                matches.append(record)
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one Feishu record for {lookup}; found {len(matches)}.")
        record = matches[0]
        fields = record.get("fields", {})
        candidate = AffiliateCandidate(
            str(record["record_id"]), str(fields.get("KOL Name") or "").strip(),
            str(fields.get("Email") or "").strip().casefold(), str(fields.get("code name") or "").strip(),
        )
        return candidate, fields.get("code link")

    def write_link_and_verify(self, record_id: str, link: str) -> None:
        if urlparse(link).scheme != "https":
            raise ValueError("Only an HTTPS shortened link can be written to Feishu.")
        endpoint = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        value = {"link": link, "text": link}
        self._http_json("PUT", endpoint, token=self._token, payload={"fields": {"code link": value}})
        reread = self._http_json("GET", endpoint, token=self._token)
        actual = normalize_code_link(reread.get("data", {}).get("record", {}).get("fields", {}).get("code link"))
        if actual != link:
            raise RuntimeError("Feishu write verification failed; email was not sent.")


class UpPromoteBrowser:
    """Idempotent UI actions inside the Shopify-hosted UpPromote iframe."""

    def __init__(self, page: Page, logger: logging.Logger) -> None:
        self.page, self.logger = page, logger

    def _frame(self) -> Frame:
        for _ in range(30):
            frames = [f for f in self.page.frames if "uppromote" in f.url or "af.uppromote" in f.url]
            if not frames:
                frames = [f for f in self.page.frames if f != self.page.main_frame]
            if frames:
                return frames[-1]
            self.page.wait_for_timeout(500)
        raise AutomationStepError("UpPromote iframe", "UpPromote frame did not load within 15 seconds.")

    def _click_center(self, target: Locator, page: Page | None = None) -> None:
        target.scroll_into_view_if_needed()
        box = target.bounding_box()
        if not box:
            raise RuntimeError("Target has no clickable bounds.")
        (page or self.page).mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    def _save_shopify_shell(self) -> None:
        button = self.page.get_by_role("button", name="Save", exact=True)
        button.wait_for(state="visible", timeout=15_000)
        button.click()
        self.page.wait_for_timeout(1_500)

    def _select_ant(self, frame: Frame, selector_index: int, option: str) -> None:
        selectors = frame.locator("div.ant-select-selector")
        indices = [selector_index] + [i for i in range(selectors.count()) if i != selector_index]
        option_pattern = re.compile(rf"^{re.escape(option)}\s*$")
        for index in indices:
            selectors.nth(index).click()
            self.page.wait_for_timeout(200)
            candidates = [
                frame.locator(".ant-select-item-option").filter(has_text=option_pattern),
                frame.get_by_title(re.compile(re.escape(option), re.I)),
                frame.get_by_text(option, exact=True),
            ]
            for item in candidates:
                if item.count() and item.first.is_visible():
                    item.first.click()
                    return
            self.page.keyboard.press("Escape")
        self.page.screenshot(
            path=str(Path(__file__).resolve().parent / "logs" / "upromote_dropdown_not_found.png"),
            full_page=True,
        )
        raise AutomationStepError("UpPromote dropdown", f"Option was not found: {option}")

    def _select_after_label(self, frame: Frame, label: str, option: str) -> None:
        """Select a value from the dropdown belonging to a visible field label."""
        labels = frame.get_by_text(label, exact=True)
        for index in range(labels.count()):
            selector = labels.nth(index).locator(
                "xpath=following::div[contains(@class, 'ant-select-selector')][1]"
            )
            if selector.count() and selector.first.is_visible():
                selector.first.click()
                self.page.wait_for_timeout(200)
                search_box = frame.locator(
                    ".ant-select-dropdown:not(.ant-select-dropdown-hidden) input, "
                    "input[placeholder*='search' i]"
                )
                if search_box.count() and search_box.first.is_visible():
                    search_box.first.fill(option)
                    self.page.wait_for_timeout(350)
                    matching = frame.locator(".ant-select-item-option").filter(
                        has_text=re.compile(re.escape(option), re.I)
                    )
                    if matching.count() and matching.first.is_visible():
                        matching.first.click()
                        return
                # Status/password fields can be non-searchable; select their
                # exact option after opening the same field dropdown.
                matching = frame.locator(".ant-select-item-option").filter(
                    has_text=re.compile(rf"^{re.escape(option)}\s*$", re.I)
                )
                if matching.count() and matching.first.is_visible():
                    matching.first.click()
                    return
                self.page.keyboard.press("Escape")
                break
        raise AutomationStepError("UpPromote dropdown", f"Field was not found: {label}")

    def ensure_affiliate(self, candidate: AffiliateCandidate) -> None:
        self.page.goto(UPPROMOTE_AFFILIATES_URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1_500)
        frame = self._frame()
        body = frame.locator("body")
        if candidate.email.casefold() in body.inner_text().casefold():
            self.logger.info("Affiliate already exists: %s", candidate.email)
            return
        frame.get_by_role("button", name=re.compile(r"add affiliate", re.I)).click()
        self.page.wait_for_timeout(700)
        frame = self._frame()
        self._select_after_label(frame, "Program", PROGRAM_NAME)
        first = frame.get_by_text("First name", exact=True).locator("xpath=following::input[1]")
        last = frame.get_by_text("Last name", exact=True).locator("xpath=following::input[1]")
        email = frame.get_by_text("Email", exact=True).locator("xpath=following::input[1]")
        first.fill(candidate.name)
        last.fill("-")
        email.fill(candidate.email)
        self._select_after_label(frame, "Status", "Active")
        self._select_after_label(frame, "Password type", "Auto generated password")
        self._save_shopify_shell()
        self.page.wait_for_timeout(1_000)

    def ensure_coupon_and_path(self, candidate: AffiliateCandidate) -> None:
        """Create the coupon and custom path only when they are absent.

        The app’s coupon editor is version-sensitive, so selectors deliberately
        use visible labels and stop instead of guessing if a label changes.
        """
        self.page.goto(UPPROMOTE_AFFILIATES_URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1_500)
        frame = self._frame()
        row = frame.locator("tr", has=frame.get_by_text(candidate.email, exact=True)).first
        row.wait_for(state="visible", timeout=15_000)
        row.get_by_text("Manage", exact=True).click()
        self.page.wait_for_timeout(800)
        frame = self._frame()
        custom_path = frame.locator('input[placeholder="Enter your custom path here"]')
        if custom_path.count() and not custom_path.input_value().strip():
            custom_path.fill(candidate.code)
            self._save_shopify_shell()
            self.page.wait_for_timeout(700)
        coupon_rows = frame.locator("tr", has=frame.get_by_text(candidate.code, exact=True))
        if coupon_rows.count():
            self.logger.info("Coupon appears configured for %s", candidate.code)
            return
        add_coupon = frame.get_by_role("button", name=re.compile(r"add.*coupon", re.I))
        add_coupon.click()
        self.page.wait_for_timeout(500)
        frame = self._frame()
        frame.locator('input[placeholder="Enter coupon code"]').fill(candidate.code)
        frame.locator('input[placeholder="0.00"]').fill("100")
        for item in frame.locator("input[type=checkbox]").all()[:3]:
            if not item.is_checked():
                item.check()
        self._select_ant(frame, 3, "Specific collections")
        self._select_ant(frame, 4, COLLECTION_NAME)
        self._save_shopify_shell()
        self.page.wait_for_timeout(1_000)

    def create_short_link(self, candidate: AffiliateCandidate) -> str:
        frame = self._frame()
        login = frame.get_by_role("button", name=re.compile(r"login as affiliate", re.I))
        login.click()
        self.page.wait_for_timeout(1_000)
        dashboard = [p for p in self.page.context.pages if "af.uppromote" in p.url]
        affiliate_page = dashboard[-1] if dashboard else self.page
        affiliate_page.bring_to_front()
        affiliate_page.get_by_role("button", name=re.compile(r"get product link", re.I)).click()
        modal = affiliate_page.locator("#productLinkModal")
        modal.wait_for(state="visible", timeout=15_000)
        modal.locator("#input-link").fill(DESTINATION_URL)
        self._click_center(modal.locator("#gen_link_btn"), affiliate_page)
        affiliate_page.wait_for_timeout(800)
        self._click_center(modal.locator("#get_product_short_link"), affiliate_page)
        affiliate_page.wait_for_timeout(800)
        short = modal.locator("input").filter(has_value=re.compile(r"^https://"))
        values = [short.nth(i).input_value().strip() for i in range(short.count())]
        links = [v for v in values if "bit.ly/" in v]
        if len(links) != 1:
            raise AutomationStepError("Get shortened link", "Expected exactly one bit.ly link.")
        self._click_center(modal.locator("#copy-and-save-product-link"), affiliate_page)
        return links[0]


def _send_email(candidate: AffiliateCandidate, link: str, args: argparse.Namespace) -> None:
    if not (args.send and args.confirm == "SEND"):
        return
    subject, body = build_affiliate_email(candidate.name, candidate.code, link)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as output:
        output.write(body)
        body_path = Path(output.name)
    try:
        raw = body.encode("utf-8")
        command = [
            str(args.gmail_script), "--credentials", str(args.gmail_credentials), "--token", str(args.gmail_token),
            "--expected-account", "info@varlascooter.com", "compose", "--to", candidate.email,
            "--subject", subject, "--body-file", str(body_path), "--expected-body-sha256", hashlib.sha256(raw).hexdigest(),
            "--expected-body-bytes", str(len(raw)), "--mode", "send", "--confirm", "SEND",
        ]
        dependency_dir = Path(__file__).resolve().parents[1] / "artifacts" / "gmail-deps"
        environment = dict(**__import__("os").environ)
        environment["PYTHONPATH"] = str(dependency_dir) + ";" + environment.get("PYTHONPATH", "")
        subprocess.run([sys.executable, *command], check=True, env=environment)
    finally:
        body_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default="", help="Exact KOL email in Feishu")
    parser.add_argument("--lookup", default="", help="Exact Feishu KOL name, email, or code")
    parser.add_argument("--apply", action="store_true", help="Allow Shopify and Feishu mutations")
    parser.add_argument("--send", action="store_true", help="Send the email after verified Feishu write-back")
    parser.add_argument("--confirm", default="", help="Must be SEND when --send is used")
    parser.add_argument("--app-token", default=APP_TOKEN)
    parser.add_argument("--table-id", default=TABLE_ID)
    parser.add_argument("--gmail-script", type=Path, default=Path.home() / ".codex/skills/varla-gmail-automation/scripts/gmail_automation.py")
    parser.add_argument("--gmail-credentials", type=Path, default=Path.home() / "AppData/Local/VarlaKOLCommandCenter/gmail-credentials.json")
    parser.add_argument("--gmail-token", type=Path, default=Path.home() / "AppData/Local/VarlaKOLCommandCenter/gmail-token.json")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    if args.send and args.confirm != "SEND":
        raise SystemExit("Refusing to send: add --confirm SEND.")
    lookup = args.lookup or args.email
    if not lookup:
        raise SystemExit("Provide --email or --lookup.")
    base = FeishuBase(args.app_token, args.table_id)
    candidate, code_link = base.find_one(lookup)
    plan = make_setup_plan(candidate, code_link)
    print(json.dumps({"plan": asdict(plan)}, ensure_ascii=False, indent=2))
    if not args.apply:
        print("Dry run only. Re-run with --apply after checking the plan.")
        return 0
    if plan.existing_link:
        _send_email(candidate, plan.existing_link, args)
        return 0
    settings = Settings()
    logger, log_path = configure_logging(settings)
    browser = ShopifyOrderBrowser(settings, logger)
    upromote_page: Page | None = None
    try:
        browser.start()
        assert browser.context is not None
        # Do not navigate the user's currently open Shopify tab. A clean tab in
        # the same persistent AdsPower context retains the authorized session.
        upromote_page = browser.context.new_page()
        workflow = UpPromoteBrowser(upromote_page, logger)
        workflow.ensure_affiliate(candidate)
        workflow.ensure_coupon_and_path(candidate)
        link = workflow.create_short_link(candidate)
        base.write_link_and_verify(candidate.record_id, link)
        _send_email(candidate, link, args)
        print(json.dumps({"status": "complete", "code": candidate.code, "link": link, "log": str(log_path)}, ensure_ascii=False))
    finally:
        if upromote_page is not None:
            try:
                upromote_page.close()
            except Exception:
                pass
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
