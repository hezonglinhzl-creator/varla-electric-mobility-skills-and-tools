from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, TypeVar

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    TimeoutError,
    sync_playwright,
)

try:
    from .adspower_client import AdsPowerClient, AdsPowerError, AdsPowerProfile
    from .config import Settings
except ImportError:
    from adspower_client import AdsPowerClient, AdsPowerError, AdsPowerProfile
    from config import Settings


AddressStatus = Literal["match", "mismatch", "uncertain", "no_visible_feedback"]
T = TypeVar("T")


class AutomationStepError(RuntimeError):
    def __init__(self, step: str, details: str):
        super().__init__(f"{step}: {details}")
        self.step = step
        self.details = details


class AddressNeedsReview(RuntimeError):
    def __init__(
        self,
        shopify_result: "AddressCheckResult",
        google_result: "AddressCheckResult",
    ):
        self.shopify_result = shopify_result
        self.google_result = google_result
        reasons = [
            f"Shopify={shopify_result.status} ({shopify_result.reason})",
            f"Google Maps={google_result.status} ({google_result.reason})",
        ]
        super().__init__("；".join(reasons))


@dataclass(frozen=True)
class AddressCheckResult:
    status: AddressStatus
    source: str
    visible_address: str = ""
    differences: tuple[str, ...] = ()
    reason: str = ""


TOKEN_ALIASES = {
    "street": "st",
    "st": "st",
    "road": "rd",
    "rd": "rd",
    "avenue": "ave",
    "ave": "ave",
    "boulevard": "blvd",
    "blvd": "blvd",
    "drive": "dr",
    "dr": "dr",
    "lane": "ln",
    "ln": "ln",
    "court": "ct",
    "ct": "ct",
    "place": "pl",
    "pl": "pl",
    "parkway": "pkwy",
    "pkwy": "pkwy",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "northeast": "ne",
    "northwest": "nw",
    "southeast": "se",
    "southwest": "sw",
    "united states of america": "us",
    "united states": "us",
    "usa": "us",
    "u s a": "us",
}

US_STATE_CODES = {
    "alabama": "al",
    "alaska": "ak",
    "arizona": "az",
    "arkansas": "ar",
    "california": "ca",
    "colorado": "co",
    "connecticut": "ct",
    "delaware": "de",
    "florida": "fl",
    "georgia": "ga",
    "hawaii": "hi",
    "idaho": "id",
    "illinois": "il",
    "indiana": "in",
    "iowa": "ia",
    "kansas": "ks",
    "kentucky": "ky",
    "louisiana": "la",
    "maine": "me",
    "maryland": "md",
    "massachusetts": "ma",
    "michigan": "mi",
    "minnesota": "mn",
    "mississippi": "ms",
    "missouri": "mo",
    "montana": "mt",
    "nebraska": "ne",
    "nevada": "nv",
    "new hampshire": "nh",
    "new jersey": "nj",
    "new mexico": "nm",
    "new york": "ny",
    "north carolina": "nc",
    "north dakota": "nd",
    "ohio": "oh",
    "oklahoma": "ok",
    "oregon": "or",
    "pennsylvania": "pa",
    "rhode island": "ri",
    "south carolina": "sc",
    "south dakota": "sd",
    "tennessee": "tn",
    "texas": "tx",
    "utah": "ut",
    "vermont": "vt",
    "virginia": "va",
    "washington": "wa",
    "west virginia": "wv",
    "wisconsin": "wi",
    "wyoming": "wy",
    "district of columbia": "dc",
}


def normalize_address_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for phrase in sorted(
        {**TOKEN_ALIASES, **US_STATE_CODES},
        key=len,
        reverse=True,
    ):
        replacement = TOKEN_ALIASES.get(phrase, US_STATE_CODES.get(phrase, phrase))
        text = re.sub(rf"\b{re.escape(phrase)}\b", replacement, text)

    return re.sub(r"\s+", " ", text).strip()


def _component_present(component: str, visible_normalized: str) -> bool:
    normalized = normalize_address_text(component)
    if not normalized:
        return False
    padded_visible = f" {visible_normalized} "
    return all(f" {token} " in padded_visible for token in normalized.split())


def compare_google_address(
    order: dict[str, str],
    visible_address: str,
) -> AddressCheckResult:
    if not visible_address.strip():
        return AddressCheckResult(
            status="uncertain",
            source="Google Maps",
            reason="页面没有返回可识别的标准地址",
        )

    visible_normalized = normalize_address_text(visible_address)
    required = {
        "address": order.get("address", ""),
        "city": order.get("city", ""),
        "state": order.get("state", ""),
        "zipcode": order.get("zipcode", ""),
        "country": order.get("country", ""),
    }
    missing = [
        field
        for field, value in required.items()
        if value and not _component_present(value, visible_normalized)
    ]

    differences: list[str] = []
    expected_zip = normalize_address_text(required["zipcode"])
    if expected_zip and "zipcode" in missing:
        visible_zips = re.findall(r"\b\d{5}(?:-\d{4})?\b", visible_normalized)
        if visible_zips and expected_zip not in visible_zips:
            differences.append("zipcode")

    expected_house = re.search(r"\b\d+[a-z]?\b", normalize_address_text(required["address"]))
    if expected_house and "address" in missing:
        visible_house = re.search(r"\b\d+[a-z]?\b", visible_normalized)
        if visible_house and visible_house.group(0) != expected_house.group(0):
            differences.append("address")

    if differences:
        return AddressCheckResult(
            status="mismatch",
            source="Google Maps",
            visible_address=visible_address,
            differences=tuple(differences),
            reason=f"明确冲突字段: {', '.join(differences)}",
        )

    # A precise street, state and ZIP match can have an accepted postal-city
    # alias (for example a nearby municipality versus the contract's mailing
    # city). It is safe only when city is the sole absent component; keep the
    # original source city in the order and record the Maps display separately.
    if missing == ["city"]:
        return AddressCheckResult(
            status="match",
            source="Google Maps",
            visible_address=visible_address,
            reason="street, state, ZIP and country match; Maps uses a postal-city alias",
        )

    if missing:
        return AddressCheckResult(
            status="uncertain",
            source="Google Maps",
            visible_address=visible_address,
            differences=tuple(missing),
            reason=f"无法从页面明确确认: {', '.join(missing)}",
        )

    return AddressCheckResult(
        status="match",
        source="Google Maps",
        visible_address=visible_address,
        reason="街道、城市、州、邮编和国家均可对应",
    )


def extract_shipping_address_text(visible_text: str) -> str:
    """Return only the shipping block so billing data cannot satisfy checks."""

    match = re.search(
        r"\bshipping address\b(?P<shipping>[\s\S]*?)"
        r"(?=\bbilling address\b|\bmarkets\b|\btags\b|$)",
        visible_text or "",
        re.IGNORECASE,
    )
    return match.group("shipping").strip() if match else ""


def shipping_phone_matches(expected_phone: str, shipping_text: str) -> bool:
    expected_digits = re.sub(r"\D", "", expected_phone or "")
    if len(expected_digits) == 11 and expected_digits.startswith("1"):
        expected_digits = expected_digits[1:]
    if len(expected_digits) != 10:
        return False
    visible_digits = re.sub(r"\D", "", shipping_text or "")
    return expected_digits in visible_digits


def is_test_email(email: str) -> bool:
    normalized = (email or "").strip().casefold()
    return (
        normalized.endswith("@example.com")
        or ".test@" in normalized
        or "+test@" in normalized
    )


def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


class ShopifyOrderBrowser:
    """Browser-only Shopify KOL order automation controlled through AdsPower."""

    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self._playwright: Playwright | None = None
        self._adspower_client: AdsPowerClient | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.maps_page: Page | None = None
        self.final_submission_attempted = False
        self.last_draft_order_code = ""

    def list_adspower_profiles(self) -> list[AdsPowerProfile]:
        self.settings.validate_adspower()
        with AdsPowerClient(
            self.settings.adspower_api_url,
            self.settings.adspower_api_key,
            self.settings.adspower_api_timeout_seconds,
        ) as client:
            return client.list_profiles()

    def _resolve_profile_id(self, client: AdsPowerClient) -> str:
        configured = self.settings.adspower_profile_id.strip()
        if configured:
            return configured
        profiles = client.list_profiles()
        if not profiles:
            raise AdsPowerError("AdsPower 中没有可用的浏览器环境")
        if len(profiles) == 1:
            return profiles[0].profile_id
        safe_profiles = "；".join(
            f"编号={item.profile_no or '-'}, 名称={item.name or '-'}, "
            f"ID={item.profile_id}"
            for item in profiles
        )
        raise AdsPowerError(
            "检测到多个 AdsPower 环境。请在 .env 设置 "
            f"ADSPOWER_PROFILE_ID。可选环境：{safe_profiles}"
        )

    def start(self) -> None:
        self.settings.ensure_runtime_dirs()
        self.settings.validate_adspower()
        self._adspower_client = AdsPowerClient(
            self.settings.adspower_api_url,
            self.settings.adspower_api_key,
            self.settings.adspower_api_timeout_seconds,
        )
        profile_id = self._resolve_profile_id(self._adspower_client)
        start_result = self._adspower_client.start_browser(profile_id)
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.connect_over_cdp(
            start_result.websocket_url,
            timeout=self.settings.default_timeout_ms,
        )
        if not self.browser.contexts:
            raise AdsPowerError("AdsPower 浏览器没有可接管的浏览器上下文")
        self.context = self.browser.contexts[0]
        self.context.set_default_timeout(self.settings.default_timeout_ms)
        normal_pages = [
            page
            for page in self.context.pages
            if page.url.startswith(("https://", "http://"))
        ]
        shopify_pages = [
            page for page in normal_pages if "admin.shopify.com" in page.url
        ]
        self.page = (
            shopify_pages[0]
            if shopify_pages
            else normal_pages[0]
            if normal_pages
            else self.context.new_page()
        )
        self.logger.info("AdsPower 环境已连接 | profile_id=%s", profile_id)

    def close(self) -> None:
        self.maps_page = None
        self.page = None
        self.context = None
        self.browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        if self._adspower_client is not None:
            self._adspower_client.close()
            self._adspower_client = None

    def run_step(self, step: str, action: Callable[[], T]) -> T:
        self.logger.info("%s | 开始", step)
        try:
            result = action()
        except AddressNeedsReview:
            self.logger.warning("%s | 需要人工确认", step)
            raise
        except Exception as exc:
            screenshot = self.capture_error(step)
            self.logger.error("%s | 失败 | %s | 截图=%s", step, exc, screenshot)
            if isinstance(exc, AutomationStepError):
                raise
            raise AutomationStepError(step, str(exc)) from exc
        self.logger.info("%s | 成功", step)
        return result

    def _require_page(self) -> Page:
        if self.page is None:
            raise RuntimeError("浏览器尚未启动")
        return self.page

    def _raise_if_shopify_verification(self) -> None:
        page = self._require_page()
        try:
            title = page.title().casefold()
            visible_text = page.locator("body").inner_text().casefold()
        except Exception:
            return
        if (
            "just a moment" in title
            or "your connection needs to be verified" in visible_text
        ):
            raise AutomationStepError(
                "Shopify 连接验证",
                "Shopify 要求先验证当前连接；程序已停止且未提交订单",
            )

    def _visible_locator(self, candidates: list[Locator]) -> Locator | None:
        for candidate in candidates:
            try:
                count = min(candidate.count(), 8)
                for index in range(count):
                    current = candidate.nth(index)
                    if current.is_visible():
                        return current
            except Exception:
                continue
        return None

    def _click_first(self, step: str, candidates: list[Locator]) -> Locator:
        target = self._visible_locator(candidates)
        if target is None:
            raise AutomationStepError(step, "未找到可见的目标按钮或链接")
        target.scroll_into_view_if_needed()
        target.click()
        return target

    def _fill_first(
        self,
        step: str,
        candidates: list[Locator],
        value: str,
    ) -> Locator:
        target = self._visible_locator(candidates)
        if target is None:
            raise AutomationStepError(step, "未找到可见的输入框")
        target.scroll_into_view_if_needed()
        target.fill(value)
        return target

    def _fill_optional(self, candidates: list[Locator], value: str) -> bool:
        target = self._visible_locator(candidates)
        if target is None:
            return False
        target.scroll_into_view_if_needed()
        target.fill(value)
        return True

    def _select_or_fill(
        self,
        step: str,
        candidates: list[Locator],
        value: str,
    ) -> None:
        target = self._visible_locator(candidates)
        if target is None:
            raise AutomationStepError(step, "未找到国家或州字段")
        target.scroll_into_view_if_needed()
        try:
            tag_name = target.evaluate("(element) => element.tagName.toLowerCase()")
        except Exception:
            tag_name = ""
        if tag_name == "select":
            try:
                target.select_option(label=value)
                return
            except Exception:
                target.select_option(value=value)
                return
        target.click()
        try:
            target.fill(value)
        except Exception:
            target.press("Control+A")
            target.type(value)
        target.press("Enter")

    def open_admin(self) -> None:
        self.settings.validate_admin_url()
        page = self._require_page()
        current_url = page.url.rstrip("/")
        target_url = self.settings.shopify_admin_url.rstrip("/")
        if current_url.startswith("https://admin.shopify.com/store/"):
            page.bring_to_front()
            try:
                self._raise_if_shopify_verification()
            except AutomationStepError:
                page.reload(wait_until="domcontentloaded")
                page.wait_for_timeout(3_000)
        else:
            page.goto(
                self.settings.shopify_admin_url,
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(1_500)
        self._raise_if_shopify_verification()

        login_text = page.get_by_text(
            re.compile(r"log in|sign in|登录", re.IGNORECASE)
        )
        login_needed = "/auth/login" in page.url or "/login" in page.url
        try:
            login_needed = login_needed or (
                login_text.count() > 0 and login_text.first.is_visible()
            )
        except Exception:
            pass

        if login_needed:
            print("\n首次运行：请在浏览器中人工登录 Shopify。")
            input("登录完成并进入后台后，按 Enter 继续...")
            page.wait_for_timeout(1_000)

        if "/admin" not in page.url:
            raise AutomationStepError(
                "打开 Shopify 后台",
                f"当前页面不是 Shopify /admin：{page.url}",
            )

    def go_to_create_order(self) -> None:
        page = self._require_page()
        current_order = getattr(self, "_current_order", None)
        if current_order and "/draft_orders/new" in page.url:
            body = page.locator("body").inner_text().casefold()
            target_email = current_order["email"].casefold()
            if target_email not in body:
                # The open draft belongs to another identity. It is unsaved,
                # so discard it before starting the next creator's draft.
                # A product/address picker can leave a backdrop over the page;
                # close that transient dialog first so it cannot intercept
                # Discard. This draft has no target identity selected.
                transient_dialog = page.get_by_role("dialog").last
                if transient_dialog.count() and transient_dialog.is_visible():
                    close_button = self._visible_locator(
                        [
                            transient_dialog.locator('button[aria-label="Close"]'),
                            transient_dialog.get_by_role(
                                "button", name=re.compile(r"^(close|cancel)$", re.I)
                            ),
                        ]
                    )
                    if close_button is not None:
                        close_button.click()
                        page.wait_for_timeout(300)
                discard_button = self._visible_locator(
                    [
                        page.get_by_role("button", name=re.compile(r"^discard$", re.I)),
                        page.get_by_text(re.compile(r"^discard$", re.I), exact=True),
                    ]
                )
                if discard_button is not None:
                    try:
                        discard_button.click()
                        page.wait_for_timeout(500)
                    except Exception:
                        # Shopify can finish discarding while its old button is
                        # detaching. The fresh-route check below is authoritative.
                        pass
                # Shopify can keep the previous draft route mounted after
                # Discard. Force a fresh Create order page and verify it no
                # longer contains the previous customer's email.
                if target_email not in page.locator("body").inner_text().casefold():
                    page.goto(page.url.split("/draft_orders", 1)[0] + "/draft_orders/new", wait_until="domcontentloaded")
                    page.wait_for_timeout(800)
        already_ready = self._visible_locator(
            [
                page.get_by_role(
                    "button", name=re.compile(r"add products?", re.I)
                )
            ]
        )
        if "/draft_orders/new" in page.url and already_ready is not None:
            self.logger.info("Create order | 复用当前已打开页面，不刷新")
            return

        configured = self.settings.shopify_admin_url.rstrip("/")
        if "/draft_orders" in configured:
            drafts_url = configured.split("/draft_orders", 1)[0] + "/draft_orders"
        else:
            store_match = re.search(
                r"^(https?://admin\.shopify\.com/store/[^/]+)",
                configured,
            )
            if not store_match:
                raise AutomationStepError(
                    "进入 Create order 页面",
                    f"无法从后台地址识别店铺: {configured}",
                )
            drafts_url = store_match.group(1) + "/draft_orders"

        create_on_current_page = self._visible_locator(
            [
                page.get_by_role(
                    "link", name=re.compile(r"^create order$", re.I)
                ),
                page.get_by_role(
                    "button", name=re.compile(r"^create order$", re.I)
                ),
                page.get_by_text(
                    re.compile(r"^create order$", re.I), exact=True
                ),
            ]
        )

        # Orders 与 Drafts 页面都有 Create order。当前页面能直接点击时不导航。
        if create_on_current_page is None and page.url.rstrip("/") != drafts_url:
            page.goto(drafts_url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            self._raise_if_shopify_verification()

        try:
            self._click_first(
                "点击 Create order",
                [
                    page.get_by_role(
                        "link", name=re.compile(r"^create order$", re.I)
                    ),
                    page.get_by_role(
                        "button", name=re.compile(r"^create order$", re.I)
                    ),
                    page.get_by_text(
                        re.compile(r"^create order$", re.I), exact=True
                    ),
                    page.locator(
                        's-internal-button[href$="/draft_orders/new"]'
                    ),
                ],
            )
        except AutomationStepError:
            page.goto(
                f"{drafts_url}/new",
                wait_until="domcontentloaded",
            )

        page.wait_for_timeout(800)
        self._raise_if_shopify_verification()

        # Create order 是异步页面：URL/标题会先切换，旧 Drafts 列表和加载遮罩
        # 可能还会停留数秒。产品按钮可见后页面才真正可操作。
        product_button_candidates = [
            page.get_by_role(
                "button", name=re.compile(r"add products?", re.I)
            ),
            page.get_by_role(
                "button", name=re.compile(r"browse products?", re.I)
            ),
            page.get_by_text(
                re.compile(r"^(add|browse) products?$", re.I), exact=True
            ),
        ]
        product_button = None
        for candidate in product_button_candidates:
            try:
                candidate.first.wait_for(state="visible", timeout=15_000)
                product_button = candidate.first
                break
            except TimeoutError:
                continue

        heading = self._visible_locator(
            [
                page.get_by_role(
                    "heading", name=re.compile(r"create order", re.I)
                ),
                page.get_by_text(
                    re.compile(r"^create order$", re.I), exact=True
                ),
            ]
        )
        if product_button is None or (
            heading is None and "/draft_orders/new" not in page.url
        ):
            raise AutomationStepError(
                "进入 Create order 页面",
                f"Create order 页面尚未完成加载，当前 URL: {page.url}",
            )

    def add_product(self, product_name: str, quantity_value: str = "1") -> None:
        page = self._require_page()
        expected_quantity = str(quantity_value or "1")
        existing_product = self._visible_locator(
            [page.get_by_text(product_name, exact=True)]
        )
        if existing_product is not None:
            self.logger.info("Product already present in current draft; skipping selector")
            quantity = self._visible_locator(
                [
                    page.get_by_label(re.compile(r"quantity", re.I)),
                    page.locator('input[name*="quantity" i]'),
                ]
            )
            if quantity is not None and quantity.input_value().strip() != expected_quantity:
                quantity.fill(expected_quantity)
            return
        self._click_first(
            "打开产品选择器",
            [
                page.get_by_role(
                    "button", name=re.compile(r"add products?", re.I)
                ),
                page.get_by_role(
                    "button", name=re.compile(r"browse products?", re.I)
                ),
                page.get_by_text(
                    re.compile(r"^(add|browse) products?$", re.I), exact=True
                ),
            ],
        )

        dialog = page.get_by_role("dialog").last
        if dialog.count() == 0 or not dialog.is_visible():
            raise AutomationStepError("添加产品", "产品选择弹窗未出现")

        search = self._fill_first(
            "搜索产品",
            [
                dialog.get_by_role("textbox", name=re.compile(r"search", re.I)),
                dialog.get_by_placeholder(re.compile(r"search products?", re.I)),
                dialog.locator('input[type="search"]'),
            ],
            product_name,
        )
        search.press("Enter")
        product_candidates = [
            dialog.get_by_text(product_name, exact=True),
            dialog.get_by_role("option", name=re.compile(re.escape(product_name), re.I)),
            dialog.get_by_text(re.compile(re.escape(product_name), re.I)),
        ]
        # The picker loads inventory results asynchronously.  A fixed one
        # second pause can race its visible loading indicator, especially
        # immediately after a Shopify connection verification.
        try:
            product_candidates[0].last.wait_for(state="visible", timeout=12_000)
        except TimeoutError:
            pass
        product_row = self._visible_locator(product_candidates)
        if product_row is None:
            raise AutomationStepError("添加产品", f"未找到产品: {product_name}")

        already_added = self._visible_locator(
            [dialog.get_by_text(re.compile(r"item already added", re.I))]
        )
        if already_added is not None:
            self._click_first(
                "关闭已添加产品弹窗",
                [
                    dialog.get_by_role("button", name=re.compile(r"^(close|cancel)$", re.I)),
                    dialog.locator('button[aria-label="Close"]'),
                ],
            )
            page.wait_for_timeout(300)
            return

        selectable_row = self._visible_locator(
            [
                dialog.locator(
                    f'[aria-label="Select: {product_name}"]'
                ),
                product_row.locator(
                    "xpath=ancestor::*[@aria-label][starts-with(@aria-label, "
                    "'Select:')][1]"
                ),
                # Shopify's current picker renders the result as a table row
                # with an unlabeled checkbox instead of a Select: aria label.
                product_row.locator(
                    "xpath=ancestor::*[.//input[@type='checkbox']][1]"
                ).get_by_role("checkbox"),
                dialog.get_by_role("checkbox").first,
            ]
        )
        if selectable_row is None:
            raise AutomationStepError(
                "添加产品",
                f"未找到产品对应的可选择行: {product_name}",
            )
        selectable_row.click()
        page.wait_for_timeout(250)

        self._click_first(
            "确认添加产品",
            [
                dialog.get_by_role("button", name=re.compile(r"^add$", re.I)),
                dialog.get_by_role(
                    "button", name=re.compile(r"add \d+ products?", re.I)
                ),
            ],
        )

        page.wait_for_timeout(700)
        if self._visible_locator([page.get_by_text(product_name, exact=True)]) is None:
            raise AutomationStepError("添加产品", "产品未出现在订单行中")

        quantity = self._visible_locator(
            [
                page.get_by_label(re.compile(r"quantity", re.I)),
                page.locator('input[name*="quantity" i]'),
            ]
        )
        if quantity is not None and quantity.input_value().strip() != expected_quantity:
            quantity.fill(expected_quantity)

    def _fill_address_form(
        self,
        dialog: Locator,
        order: dict[str, str],
    ) -> None:
        page = self._require_page()
        first_name, last_name = split_name(order["name"])
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"first name", re.I)),
                dialog.locator('input[name*="firstName" i]'),
            ],
            first_name,
        )
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"last name", re.I)),
                dialog.locator('input[name*="lastName" i]'),
            ],
            last_name,
        )
        address_input = self._fill_first(
            "填写地址",
            [
                dialog.get_by_label(
                    re.compile(r"address$", re.I), exact=False
                ),
                dialog.locator('input[name*="address1" i]'),
            ],
            order["address"],
        )
        page.wait_for_timeout(600)
        street_number = normalize_address_text(order["address"]).split(" ", 1)[0]
        suggestion = self._visible_locator(
            [
                page.get_by_role("option").filter(
                    has_text=re.compile(
                        rf"\b{re.escape(street_number)}\b",
                        re.I,
                    )
                ),
                page.get_by_role("listbox").get_by_text(
                    re.compile(re.escape(order["address"]), re.I)
                ),
            ]
        )
        if suggestion is not None:
            suggestion.click()
            page.wait_for_timeout(400)
        if address_input.input_value().strip().casefold() != order[
            "address"
        ].casefold():
            address_input.fill(order["address"])

        address2 = order.get("address2", "").strip()
        if address2:
            self._fill_first(
                "填写公寓/楼栋补充地址",
                [
                    dialog.get_by_label(
                        re.compile(r"apartment|suite|unit|address 2", re.I)
                    ),
                    dialog.locator('input[name*="address2" i]'),
                    dialog.locator(
                        'input[placeholder*="Apartment" i], '
                        'input[placeholder*="suite" i]'
                    ),
                ],
                address2,
            )
        self._fill_first(
            "填写城市",
            [
                dialog.get_by_label(re.compile(r"city", re.I)),
                dialog.locator('input[name*="city" i]'),
            ],
            order["city"],
        )
        self._select_or_fill(
            "填写国家",
            [
                dialog.get_by_label(re.compile(r"country", re.I)),
                dialog.locator('select[name*="country" i]'),
                dialog.locator('input[name*="country" i]'),
            ],
            order["country"],
        )
        self._select_or_fill(
            "填写州",
            [
                dialog.get_by_label(
                    re.compile(r"^(state|province|state/province)$", re.I)
                ),
                dialog.locator('select[name*="zone" i]'),
                dialog.locator('input[name*="province" i]'),
            ],
            order["state"],
        )
        self._fill_first(
            "填写邮编",
            [
                dialog.get_by_label(re.compile(r"zip|postal", re.I)),
                dialog.locator('input[name*="zip" i]'),
            ],
            order["zipcode"],
        )
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"phone", re.I)),
                dialog.locator('input[type="tel"]'),
            ],
            order["phone"],
        )

    def _create_or_select_customer(self, order: dict[str, str]) -> None:
        page = self._require_page()
        open_customer_dialog = self._visible_locator(
            [
                page.get_by_role("dialog").filter(
                    has_text=re.compile(r"New customer", re.I)
                )
            ]
        )
        if open_customer_dialog is not None:
            self._click_first(
                "关闭残留的新客户窗口",
                [
                    open_customer_dialog.get_by_role(
                        "button", name=re.compile(r"^close$", re.I)
                    ),
                    open_customer_dialog.locator('button[aria-label="Close"]'),
                ],
            )
            page.wait_for_timeout(400)
        existing_body = page.locator("body").inner_text()
        existing_normalized = normalize_address_text(existing_body)
        # A freshly created customer may already be attached while Shopify
        # abbreviates the street type (for example, "Drive" -> "Dr").  Email
        # plus full customer name is the durable identity here; the following
        # shipping-address step still verifies/repairs the address itself.
        if all(
            part and part in existing_normalized
            for part in (
                normalize_address_text(order["name"]),
                normalize_address_text(order["email"]),
            )
        ):
            self.logger.info("Customer already selected in current draft; skipping selector")
            return
        customer_dialog: Locator | None = None
        direct_search = self._visible_locator(
            [
                page.locator(
                    'input[placeholder="Search or create a customer"]'
                ),
                page.get_by_placeholder(
                    re.compile(r"search or create a customer", re.I)
                ),
            ]
        )
        if direct_search is not None:
            direct_search.fill(order["email"])
            page.wait_for_timeout(800)
            option = self._visible_locator(
                [
                    page.get_by_role("option").filter(
                        has_text=re.compile(re.escape(order["email"]), re.I)
                    ),
                    page.get_by_role("listbox").get_by_text(
                        order["email"], exact=True
                    ),
                    page.get_by_text(order["email"], exact=True),
                ]
            )
            if option is not None:
                option.click()
                try:
                    page.get_by_text(
                        order["address"], exact=False
                    ).wait_for(state="visible", timeout=12_000)
                except TimeoutError:
                    page.wait_for_timeout(600)
                visible_text = page.locator("body").inner_text()
                if (
                    order["email"].casefold() not in visible_text.casefold()
                    or order["name"].casefold() not in visible_text.casefold()
                ):
                    raise AutomationStepError(
                        "选择已有客户",
                        "选择后未同时看到匹配的姓名和邮箱",
                    )
                return
            self._click_first(
                "新建客户",
                [
                    page.get_by_text("Create a new customer", exact=True),
                    page.get_by_role(
                        "button", name=re.compile(r"create a new customer", re.I)
                    ),
                ],
            )
            customer_dialog = page.get_by_role("dialog").last
        else:
            self._click_first(
                "打开客户选择器",
                [
                    page.get_by_role(
                        "button", name=re.compile(r"add customer", re.I)
                    ),
                    page.get_by_text(
                        re.compile(r"^add customer$", re.I), exact=True
                    ),
                ],
            )
            dialog = page.get_by_role("dialog").last
            if dialog.count() == 0 or not dialog.is_visible():
                raise AutomationStepError("添加客户", "客户选择弹窗未出现")
            search = self._visible_locator(
                [
                    dialog.get_by_role(
                        "textbox", name=re.compile(r"search", re.I)
                    ),
                    dialog.get_by_placeholder(re.compile(r"search", re.I)),
                ]
            )
            if search is not None:
                search.fill(order["email"])
                page.wait_for_timeout(700)
                exact_email = self._visible_locator(
                    [dialog.get_by_text(order["email"], exact=True)]
                )
                if exact_email is not None:
                    exact_email.click()
                    return
            self._click_first(
                "新建客户",
                [
                    dialog.get_by_role(
                        "button",
                        name=re.compile(r"create (a )?new customer", re.I),
                    ),
                    dialog.get_by_text(
                        re.compile(r"create (a )?new customer", re.I)
                    ),
                ],
            )
            customer_dialog = page.get_by_role("dialog").last

        # Shopify 会先保留客户搜索下拉层，再异步打开 New customer 面板。
        # 不能直接使用当时的“最后一个 dialog”，否则可能误取 Resize Sidebar。
        customer_dialog = page.get_by_role("dialog").filter(
            has_text=re.compile(r"New customer", re.I)
        ).last
        try:
            customer_dialog.wait_for(state="visible", timeout=15_000)
        except TimeoutError as exc:
            raise AutomationStepError(
                "新建客户", "等待 New customer 面板超时"
            ) from exc

        if (
            customer_dialog is None
            or customer_dialog.count() == 0
            or not customer_dialog.is_visible()
        ):
            raise AutomationStepError("新建客户", "新建客户弹窗未出现")

        first_name, last_name = split_name(order["name"])
        self._fill_first(
            "填写客户名",
            [
                customer_dialog.get_by_label(re.compile(r"first name", re.I)),
                customer_dialog.locator('input[name*="firstName" i]'),
            ],
            first_name,
        )
        if last_name:
            self._fill_optional(
                [
                    customer_dialog.get_by_label(re.compile(r"last name", re.I)),
                    customer_dialog.locator('input[name*="lastName" i]'),
                ],
                last_name,
            )
        self._fill_first(
            "填写客户邮箱",
            [
                customer_dialog.get_by_label(re.compile(r"email", re.I)),
                customer_dialog.locator('input[type="email"]'),
            ],
            order["email"],
        )
        self._fill_optional(
            [
                customer_dialog.get_by_label(re.compile(r"phone", re.I)),
                customer_dialog.locator('input[type="tel"]'),
            ],
            order["phone"],
        )

        # 三个营销许可都保持未勾选，测试客户不会被订阅营销消息。
        marketing_checkboxes = customer_dialog.get_by_role("checkbox")
        for index in range(marketing_checkboxes.count()):
            checkbox = marketing_checkboxes.nth(index)
            if checkbox.is_checked():
                checkbox.uncheck()

        customer_tag = self._visible_locator(
            [
                customer_dialog.locator('input[name="tags"]'),
                customer_dialog.get_by_label(
                    re.compile(r"^tags?$", re.I)
                ),
            ]
        )
        if customer_tag is None:
            raise AutomationStepError("新建客户", "未找到客户 Tags 输入框")
        customer_tag.fill("KOL")
        customer_tag.press("Enter")
        page.wait_for_timeout(300)

        self._click_first(
            "添加客户默认地址",
            [
                customer_dialog.get_by_role(
                    "button", name=re.compile(r"^add address$", re.I)
                ),
                customer_dialog.get_by_text(
                    re.compile(r"^add address$", re.I), exact=True
                ),
            ],
        )
        address_dialog = page.get_by_role("dialog").filter(
            has_text=re.compile(r"Add default address", re.I)
        ).last
        try:
            address_dialog.wait_for(state="visible", timeout=15_000)
        except TimeoutError as exc:
            raise AutomationStepError(
                "添加客户默认地址", "等待 Add default address 弹窗超时"
            ) from exc
        self._fill_address_form(address_dialog, order)
        # Shopify can open a nested address-choice dialog after a new address
        # is entered.  Its backdrop blocks the parent dialog's Save button.
        # Keep the contract-entered address when it is a verified real address;
        # never auto-accept Shopify's different suggestion.
        address_choice = page.get_by_role("dialog").filter(
            has_text=re.compile(r"Choose shipping address", re.I)
        ).last
        try:
            address_choice.wait_for(state="visible", timeout=4_000)
        except TimeoutError:
            pass
        if address_choice.count() and address_choice.is_visible():
            self._click_first(
                "保留合同填写的地址",
                [
                    address_choice.get_by_text(
                        re.compile(r"^your edit$", re.I), exact=True
                    ),
                    address_choice.get_by_role(
                        "radio", name=re.compile(r"your edit", re.I)
                    ),
                    address_choice.locator("label").filter(
                        has_text=re.compile(r"your edit", re.I)
                    ),
                ],
            )
            page.wait_for_timeout(150)
            self._click_first(
                "确认合同填写的地址",
                [
                    address_choice.get_by_role(
                        "button", name=re.compile(r"^use", re.I)
                    ),
                ],
            )
            address_choice.wait_for(state="hidden", timeout=15_000)
        self._click_first(
            "保存客户默认地址",
            [
                address_dialog.get_by_role(
                    "button", name=re.compile(r"^save$", re.I)
                ),
            ],
        )
        try:
            address_dialog.wait_for(state="hidden", timeout=15_000)
        except TimeoutError as exc:
            raise AutomationStepError(
                "保存客户默认地址", "默认地址弹窗未关闭"
            ) from exc

        self._click_first(
            "保存客户",
            [
                customer_dialog.get_by_role(
                    "button", name=re.compile(r"^create customer$", re.I)
                ),
                customer_dialog.get_by_role(
                    "button", name=re.compile(r"^save$", re.I)
                ),
            ],
        )
        try:
            customer_dialog.wait_for(state="hidden", timeout=15_000)
        except TimeoutError as exc:
            raise AutomationStepError("保存客户", "New customer 面板未关闭") from exc

        # Shopify 保存客户后会先显示骨架屏，再异步把客户附加到草稿。
        # 先等待自动挂载，避免在索引尚未完成时重复搜索或误判失败。
        auto_attached = False
        try:
            page.get_by_text(order["email"], exact=True).wait_for(
                state="visible", timeout=15_000
            )
            page.get_by_text(order["address"], exact=False).wait_for(
                state="visible", timeout=15_000
            )
            auto_attached = True
        except TimeoutError:
            pass

        # 仅当自动挂载确实没有完成时，再搜索刚创建的客户。
        if not auto_attached:
            direct_search = self._visible_locator(
                [
                    page.locator(
                        'input[placeholder="Search or create a customer"]'
                    ),
                    page.get_by_placeholder(
                        re.compile(r"search or create a customer", re.I)
                    ),
                ]
            )
            if direct_search is None:
                raise AutomationStepError(
                    "选择新建客户", "新客户创建后未找到客户搜索框"
                )
            direct_search.fill(order["email"])
            page.wait_for_timeout(1_000)
            option = self._visible_locator(
                [
                    page.get_by_role("option").filter(
                        has_text=re.compile(re.escape(order["email"]), re.I)
                    ),
                    page.get_by_text(order["email"], exact=True),
                ]
            )
            if option is None:
                raise AutomationStepError(
                    "选择新建客户",
                    "客户已创建，但等待和搜索后仍没有对应邮箱",
                )
            option.click()
        try:
            page.get_by_text(order["address"], exact=False).wait_for(
                state="visible", timeout=15_000
            )
        except TimeoutError as exc:
            raise AutomationStepError(
                "选择新建客户", "订单页未显示新客户的默认收货地址"
            ) from exc

    def _fill_shipping_address(self, order: dict[str, str]) -> None:
        page = self._require_page()
        visible_text = page.locator("body").inner_text()
        shipping_text = extract_shipping_address_text(visible_text)
        existing = compare_google_address(order, shipping_text)
        if existing.status == "match" and shipping_phone_matches(
            order["phone"], shipping_text
        ):
            self.logger.info("收货地址 | 已有客户地址与 Excel 一致，无需修改")
            return

        # New Shopify UI can show a saved address card without the legacy
        # Add/Edit shipping address control. Accept it when all identity
        # fields are visibly present and match the current order.
        visible_normalized = normalize_address_text(visible_text)
        expected_parts = (
            normalize_address_text(order["name"]),
            normalize_address_text(order["address"]),
            normalize_address_text(order["city"]),
            normalize_address_text(order["zipcode"]),
        )
        if all(part and part in visible_normalized for part in expected_parts):
            self.logger.info("Saved Shopify address card matches current order")
            return

        self._click_first(
            "打开收货地址",
            [
                page.get_by_role(
                    "button", name=re.compile(r"add shipping address", re.I)
                ),
                page.get_by_role(
                    "button", name=re.compile(r"edit shipping address", re.I)
                ),
                page.get_by_text(
                    re.compile(r"(add|edit) shipping address", re.I)
                ),
            ],
        )

        dialog = page.get_by_role("dialog").last
        if dialog.count() == 0 or not dialog.is_visible():
            raise AutomationStepError("填写收货地址", "收货地址弹窗未出现")

        first_name, last_name = split_name(order["name"])
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"first name", re.I)),
                dialog.locator('input[name*="firstName" i]'),
            ],
            first_name,
        )
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"last name", re.I)),
                dialog.locator('input[name*="lastName" i]'),
            ],
            last_name,
        )
        address_input = self._fill_first(
            "填写地址",
            [
                dialog.get_by_label(
                    re.compile(r"address$", re.I), exact=False
                ),
                dialog.locator('input[name*="address1" i]'),
            ],
            order["address"],
        )
        page.wait_for_timeout(600)
        street_number = normalize_address_text(order["address"]).split(" ", 1)[0]
        suggestion = self._visible_locator(
            [
                page.get_by_role("option").filter(
                    has_text=re.compile(
                        rf"\b{re.escape(street_number)}\b",
                        re.I,
                    )
                ),
                page.get_by_role("listbox").get_by_text(
                    re.compile(re.escape(order["address"]), re.I)
                ),
            ]
        )
        if suggestion is not None:
            suggestion.click()
            page.wait_for_timeout(400)
        if address_input.input_value().strip().casefold() != order[
            "address"
        ].casefold():
            address_input.fill(order["address"])

        address2 = order.get("address2", "").strip()
        if address2:
            self._fill_first(
                "填写公寓/楼栋补充地址",
                [
                    dialog.get_by_label(
                        re.compile(r"apartment|suite|unit|address 2", re.I)
                    ),
                    dialog.locator('input[name*="address2" i]'),
                    dialog.locator(
                        'input[placeholder*="Apartment" i], '
                        'input[placeholder*="suite" i]'
                    ),
                ],
                address2,
            )
        self._fill_first(
            "填写城市",
            [
                dialog.get_by_label(re.compile(r"city", re.I)),
                dialog.locator('input[name*="city" i]'),
            ],
            order["city"],
        )
        self._select_or_fill(
            "填写国家",
            [
                dialog.get_by_label(re.compile(r"country", re.I)),
                dialog.locator('select[name*="country" i]'),
                dialog.locator('input[name*="country" i]'),
            ],
            order["country"],
        )
        self._select_or_fill(
            "填写州",
            [
                dialog.get_by_label(
                    re.compile(r"^(state|province|state/province)$", re.I)
                ),
                dialog.locator('select[name*="zone" i]'),
                dialog.locator('input[name*="province" i]'),
            ],
            order["state"],
        )
        self._fill_first(
            "填写邮编",
            [
                dialog.get_by_label(
                    re.compile(r"zip|postal", re.I)
                ),
                dialog.locator('input[name*="zip" i]'),
            ],
            order["zipcode"],
        )
        self._fill_optional(
            [
                dialog.get_by_label(re.compile(r"phone", re.I)),
                dialog.locator('input[type="tel"]'),
            ],
            order["phone"],
        )

        self._click_first(
            "保存收货地址",
            [
                dialog.get_by_role("button", name=re.compile(r"^save$", re.I)),
                dialog.get_by_role(
                    "button", name=re.compile(r"apply|use this address", re.I)
                ),
            ],
        )
        page.wait_for_timeout(1_000)

    def fill_customer_and_shipping(self, order: dict[str, str]) -> None:
        self._current_order = order
        self._create_or_select_customer(order)
        self._fill_shipping_address(order)

    def inspect_shopify_address_feedback(self) -> AddressCheckResult:
        page = self._require_page()
        visible_text = page.locator("body").inner_text()
        normalized = visible_text.casefold()
        shipping_text = extract_shipping_address_text(visible_text)

        expected_order = getattr(self, "_current_order", None)
        if expected_order:
            visible_result = compare_google_address(
                expected_order, shipping_text
            )
            if visible_result.status == "match" and shipping_phone_matches(
                expected_order["phone"], shipping_text
            ):
                return AddressCheckResult(
                    status="match",
                    source="Shopify",
                    visible_address=visible_result.visible_address,
                    reason="Shopify 页面中的收货地址与 Excel 一致",
                )

        mismatch_patterns = (
            "suggested address",
            "use suggested address",
            "address is invalid",
            "invalid address",
            "address error",
        )
        uncertain_patterns = (
            "couldn't verify",
            "could not verify",
            "unable to verify",
            "address can't be verified",
            "address cannot be verified",
        )
        if any(pattern in normalized for pattern in mismatch_patterns):
            return AddressCheckResult(
                status="mismatch",
                source="Shopify",
                visible_address=visible_text[-1_500:],
                reason="Shopify 页面出现建议地址或地址冲突提示",
            )
        if any(pattern in normalized for pattern in uncertain_patterns):
            return AddressCheckResult(
                status="uncertain",
                source="Shopify",
                visible_address=visible_text[-1_500:],
                reason="Shopify 表示无法确认该地址",
            )
        return AddressCheckResult(
            status="no_visible_feedback",
            source="Shopify",
            reason="Shopify 页面未提供可见地址提示，继续使用 Google Maps 校对",
        )

    def check_google_maps(self, order: dict[str, str]) -> AddressCheckResult:
        if self.context is None:
            raise RuntimeError("浏览器尚未启动")
        self.maps_page = self.context.new_page()
        maps_page = self.maps_page
        maps_page.goto(self.settings.google_maps_url, wait_until="domcontentloaded")

        body_text = maps_page.locator("body").inner_text().casefold()
        blocked_terms = (
            "unusual traffic",
            "before you continue",
            "verify you are human",
            "captcha",
        )
        if any(term in body_text for term in blocked_terms):
            return AddressCheckResult(
                status="uncertain",
                source="Google Maps",
                reason="Google Maps 出现验证或同意页面",
            )

        query = ", ".join(
            order[field]
            for field in ("address", "city", "state", "zipcode", "country")
            if order.get(field)
        )
        search = self._visible_locator(
            [
                maps_page.locator("#searchboxinput"),
                maps_page.locator('input[name="q"]'),
                maps_page.get_by_role(
                    "textbox", name=re.compile(r"search google maps", re.I)
                ),
            ]
        )
        if search is None:
            return AddressCheckResult(
                status="uncertain",
                source="Google Maps",
                reason="未找到 Google Maps 搜索框",
            )

        search.fill(query)
        search.press("Enter")
        try:
            maps_page.wait_for_selector(
                'button[data-item-id="address"], div[role="main"] h1, a.hfpxzc',
                timeout=self.settings.maps_result_timeout_ms,
            )
        except TimeoutError:
            return AddressCheckResult(
                status="uncertain",
                source="Google Maps",
                reason="Google Maps 搜索结果等待超时",
            )
        maps_page.wait_for_timeout(1_500)

        refreshed_body_text = maps_page.locator("body").inner_text()
        refreshed_body = refreshed_body_text.casefold()
        if any(term in refreshed_body for term in blocked_terms):
            return AddressCheckResult(
                status="uncertain",
                source="Google Maps",
                reason="Google Maps 要求验证码或额外确认",
            )

        address_button = self._visible_locator(
            [
                maps_page.locator('button[data-item-id="address"]'),
                maps_page.locator('[data-item-id="address"]'),
                maps_page.get_by_role("button").filter(
                    has_text=re.compile(re.escape(order["address"]), re.I)
                ),
            ]
        )
        visible_address = ""
        if address_button is not None:
            visible_address = address_button.inner_text().strip()
            if not visible_address:
                visible_address = (
                    address_button.get_attribute("aria-label") or ""
                ).removeprefix("Address:").strip()

        if not visible_address:
            heading = self._visible_locator(
                [
                    maps_page.get_by_role(
                        "heading",
                        name=re.compile(re.escape(order["address"]), re.I),
                    )
                ]
            )
            if heading is not None:
                visible_address = heading.inner_text().strip()

        if visible_address and (
            "united states" in refreshed_body
            or "usa" in refreshed_body
            or "美国" in refreshed_body_text
        ):
            visible_address = f"{visible_address}, United States"

        # 地图标题经常只有街道名；优先复制正文中同时包含街道和邮编的
        # 完整标准地址，例如 “123 Example St, Example City, CA 00000”。
        normalized_street = normalize_address_text(order["address"])
        expected_zip = order.get("zipcode", "").strip()
        for line in refreshed_body_text.splitlines():
            normalized_line = normalize_address_text(line)
            if (
                normalized_street
                and expected_zip
                and _component_present(normalized_street, normalized_line)
                and expected_zip in normalized_line
            ):
                visible_address = line.strip()
                if (
                    order.get("country", "").casefold() == "united states"
                    and "united states" not in visible_address.casefold()
                ):
                    visible_address = f"{visible_address}, United States"
                break

        result_links = maps_page.locator("a.hfpxzc")
        try:
            if not visible_address and result_links.count() > 1:
                maps_page.close()
                self.maps_page = None
                return AddressCheckResult(
                    status="uncertain",
                    source="Google Maps",
                    reason="Google Maps 返回多个候选地址",
                )
        except Exception:
            pass

        result = compare_google_address(order, visible_address)
        if not maps_page.is_closed():
            maps_page.close()
        self.maps_page = None
        return result

    def require_address_match(
        self,
        shopify_result: AddressCheckResult,
        google_result: AddressCheckResult,
    ) -> None:
        shopify_safe = shopify_result.status in ("match", "no_visible_feedback")
        google_safe = google_result.status == "match"
        if shopify_safe and google_safe:
            self.logger.info(
                "地址校对 | 通过 | Shopify=%s | Google Maps=%s",
                shopify_result.status,
                google_result.status,
            )
            return

        screenshot = self.capture_address_review()
        self.logger.warning(
            "地址校对 | 停止等待人工确认 | Shopify=%s | Google Maps=%s "
            "| 差异=%s | 截图=%s",
            shopify_result.status,
            google_result.status,
            ",".join(google_result.differences) or "无明确差异",
            screenshot,
        )
        raise AddressNeedsReview(shopify_result, google_result)

    def fill_notes_and_tags(self, order: dict[str, str]) -> None:
        page = self._require_page()
        note_input = self._visible_locator(
            [
                page.get_by_role("textbox", name=re.compile(r"notes?", re.I)),
                page.locator('textarea[name*="note" i]'),
            ]
        )
        if note_input is None:
            note_modal = page.locator(
                's-internal-modal[heading="Add note"], '
                's-internal-modal[heading="Edit note"]'
            )
            visible_modal = self._visible_locator(
                [
                    note_modal,
                    page.get_by_role("dialog").filter(
                        has_text=re.compile(r"Add note|Edit note", re.I)
                    ),
                ]
            )
            if visible_modal is None:
                notes_section = page.locator(
                    's-internal-section[heading="Notes"]'
                )
                self._click_first(
                    "打开 Notes 菜单",
                        [
                        notes_section.get_by_role(
                            "button", name=re.compile(r"more actions", re.I)
                        ),
                        page.get_by_role(
                            "button", name=re.compile(r"edit notes?", re.I)
                        ),
                        page.locator('button[aria-label="Edit notes"]'),
                    ],
                )
                page.wait_for_timeout(300)
                visible_modal = self._visible_locator(
                    [
                        note_modal,
                        page.get_by_role("dialog").filter(
                            has_text=re.compile(r"Add note|Edit note", re.I)
                        ),
                        ]
                    )
                if visible_modal is None:
                    menu_item = self._visible_locator(
                    [
                        page.get_by_role("menu", name="More actions").get_by_role(
                            "menuitem"
                        ),
                        page.get_by_role("menuitem"),
                    ]
                )
                    if menu_item is None:
                        raise AutomationStepError(
                        "填写 Notes", "Notes 编辑菜单未出现"
                    )
                    menu_item.click()
                    page.wait_for_timeout(400)
                visible_modal = self._visible_locator(
                    [
                        note_modal,
                        page.get_by_role("dialog").filter(
                            has_text=re.compile(r"Add note|Edit note", re.I)
                        ),
                    ]
                )
            if visible_modal is None:
                raise AutomationStepError("填写 Notes", "Notes 编辑弹窗未出现")
            note_input = self._visible_locator(
                [
                    visible_modal.locator("textarea"),
                    visible_modal.get_by_role("textbox"),
                    # Shopify 新版把 textarea 作为 slot 放在 dialog 外层。
                    page.locator("textarea"),
                ]
            )
            if note_input is None:
                raise AutomationStepError("填写 Notes", "Notes 输入框未出现")
            note_input.fill(order["note"])
            self._click_first(
                "保存 Notes",
                [
                    visible_modal.locator(
                        's-internal-button[variant="primary"]'
                    ),
                    visible_modal.get_by_role(
                        "button", name=re.compile(r"^done$|^save$", re.I)
                    ),
                    visible_modal.locator("button").filter(
                        has_text=re.compile(r"^done$|^save$", re.I)
                    ),
                    page.get_by_role(
                        "button", name=re.compile(r"^done$", re.I)
                    ),
                ],
            )
            try:
                visible_modal.wait_for(state="hidden", timeout=5_000)
            except TimeoutError as exc:
                raise AutomationStepError(
                    "保存 Notes", "Notes 编辑窗口未关闭"
                ) from exc
        else:
            note_input.fill(order["note"])

        if not order["tag"]:
            return

        # A rerun may already have placed the intended order tag.  Do not add
        # a second tag, and never allow an open Notes textarea to be mistaken
        # for the Tags input.
        if order["tag"].casefold() in page.locator("body").inner_text().casefold():
            return

        tag_input = self._visible_locator(
            [
                page.get_by_role("textbox", name=re.compile(r"tags?", re.I)),
                page.locator('input[name*="tag" i]'),
                page.locator('input[placeholder*="tag" i]'),
            ]
        )
        if tag_input is None:
            self._click_first(
                "打开 Tags",
                [
                    page.get_by_role(
                        "button", name=re.compile(r"add tags?|manage tags?", re.I)
                    ),
                    page.get_by_text(
                        re.compile(r"^(add|manage) tags?$", re.I), exact=True
                    ),
                ],
            )
            dialog = page.get_by_role("dialog").last
            if dialog.count() == 0 or not dialog.is_visible():
                raise AutomationStepError("填写 Tags", "Tags 弹窗未出现")
            tag_input = self._visible_locator(
                [
                    dialog.get_by_role("textbox"),
                    dialog.locator('input[type="text"]'),
                ]
            )
            if tag_input is None:
                raise AutomationStepError("填写 Tags", "未找到 Tags 输入框")
            tag_input.fill(order["tag"])
            tag_input.press("Enter")
            self._click_first(
                "确认 Tags",
                [
                    dialog.get_by_role(
                        "button", name=re.compile(r"^done$|^add$", re.I)
                    )
                ],
            )
            return

        tag_input.fill(order["tag"])
        tag_input.press("Enter")

    def verify_order_identity(self, order: dict[str, str]) -> None:
        """Refuse submission unless every critical value is visibly matched."""

        page = self._require_page()
        self._current_order = order
        if is_test_email(order["email"]):
            raise AutomationStepError(
                "提交前严格校验",
                "测试邮箱禁止用于真实订单提交",
            )
        visible_text = page.locator("body").inner_text()
        normalized = visible_text.casefold()
        missing = [
            label
            for label, value in (
                ("姓名", order["name"]),
                ("邮箱", order["email"]),
                ("产品", order["product"]),
                ("Tag", order["tag"]),
            )
            if value and value.casefold() not in normalized
        ]
        for line in order["note"].splitlines():
            if line.strip() and line.strip().casefold() not in normalized:
                missing.append(f"Note:{line.strip()}")
        address2 = order.get("address2", "").strip()
        if address2 and address2.casefold() not in normalized:
            missing.append("公寓/楼栋补充地址")

        shipping_text = extract_shipping_address_text(visible_text)
        address_result = compare_google_address(order, shipping_text)
        if address_result.status != "match":
            card_result = compare_google_address(order, visible_text)
            if card_result.status == "match":
                address_result = card_result
                shipping_text = visible_text
        if address_result.status != "match":
            missing.append("完整收货地址")

        if not shipping_phone_matches(order["phone"], shipping_text):
            missing.append("收货电话")

        if not re.search(r"\btotal\b[\s\S]{0,80}\$0\.00\b", visible_text, re.I):
            missing.append("订单总额 $0.00")

        if missing:
            raise AutomationStepError(
                "提交前严格校验",
                f"页面缺少或不一致: {', '.join(missing)}",
            )

    def submit_paid_order_and_get_code(
        self,
        order: dict[str, str],
    ) -> str:
        """Create exactly the verified $0 KOL order and return #VARLA code."""

        page = self._require_page()
        self.verify_order_identity(order)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        page.screenshot(
            path=str(self.settings.log_dir / f"before_paid_submit_{timestamp}.png"),
            full_page=True,
        )

        self._click_first(
            "打开 Collect payment 菜单",
            [
                page.get_by_role(
                    "button", name=re.compile(r"collect payment", re.I)
                ),
                page.get_by_text(
                    re.compile(r"^collect payment$", re.I), exact=True
                ),
            ],
        )
        page.wait_for_timeout(300)
        self._click_first(
            "选择 Mark as paid",
            [
                page.get_by_role(
                    "menuitem", name=re.compile(r"mark as paid", re.I)
                ),
                page.get_by_text(
                    re.compile(r"^mark as paid$", re.I), exact=True
                ),
            ],
        )
        create_button = page.get_by_role(
            "button",
            name=re.compile(r"^create order$", re.I),
        )
        try:
            create_button.wait_for(
                state="visible",
                timeout=self.settings.default_timeout_ms,
            )
        except TimeoutError:
            raise AutomationStepError(
                "确认标记已付款",
                "未出现最终确认弹窗；为避免误操作已停止",
            )
        draft_text = f"{page.title()} {page.locator('body').inner_text()}"
        draft_match = re.search(r"#D\d+", draft_text, re.I)
        self.last_draft_order_code = (
            draft_match.group(0).upper() if draft_match else ""
        )

        self.final_submission_attempted = True
        self._click_first(
            "最终创建已付款订单",
            [
                create_button,
                page.locator(
                    's-internal-modal[heading*="Mark as paid" i] '
                    's-internal-button[variant="primary"]'
                ),
            ],
        )

        try:
            page.wait_for_url(
                re.compile(r"/orders/[^/?#]+"),
                timeout=self.settings.default_timeout_ms,
            )
        except TimeoutError:
            page.wait_for_timeout(2_000)

        page.wait_for_timeout(2_500)
        visible_text = page.locator("body").inner_text()
        heading_text = " ".join(
            page.locator("s-internal-heading").all_inner_texts()
        )
        result_text = f"{page.title()} {visible_text} {heading_text}"
        match = re.search(r"#VARLA\d+", result_text, re.I)
        if not match:
            raise AutomationStepError(
                "提取 VARLA 订单号",
                f"订单页面未找到 #VARLA 编号，当前 URL: {page.url}",
            )
        order_code = match.group(0).upper()
        if not re.search(r"\bPaid\b", result_text, re.I):
            raise AutomationStepError("核验订单状态", "订单页面未显示 Paid")
        if not re.search(r"\bUnfulfilled\b", result_text, re.I):
            raise AutomationStepError("核验订单状态", "订单页面未显示 Unfulfilled")

        page.screenshot(
            path=str(
                self.settings.log_dir
                / f"completed_{order_code.removeprefix('#')}_{timestamp}.png"
            ),
            full_page=True,
        )
        return order_code

    def capture_error(self, step: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_step = re.sub(r"[^a-zA-Z0-9_-]+", "_", step).strip("_") or "step"
        output = self.settings.log_dir / f"error_{safe_step}_{timestamp}.png"
        page = self.maps_page or self.page
        if page is None:
            return output
        try:
            page.screenshot(path=str(output), full_page=True)
            page.screenshot(
                path=str(self.settings.debug_screenshot_path),
                full_page=True,
            )
        except Exception as exc:
            self.logger.error("保存错误截图失败: %s", exc)
        return output

    def capture_address_review(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = self.settings.log_dir / f"address_mismatch_{timestamp}.png"
        page = self.maps_page or self.page
        if page is not None:
            try:
                page.screenshot(path=str(output), full_page=True)
            except Exception as exc:
                self.logger.error("保存地址校对截图失败: %s", exc)
        return output
