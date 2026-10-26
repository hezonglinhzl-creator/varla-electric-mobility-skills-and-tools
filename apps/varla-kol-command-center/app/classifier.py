"""Deterministic, evidence-producing message classification."""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import getaddresses, parseaddr
import re
import unicodedata
from typing import Iterable

from pydantic import BaseModel, Field

from app.schemas import TASK_GROUPS, TaskGroup


INTERNAL_DOMAIN = "varlascooter.com"

GROUP_ROUTES: dict[TaskGroup, dict[str, str | None]] = {
    "kol": {"label": "KOL", "department": None},
    "pre-sales": {"label": None, "department": "support@varlascooter.com"},
    "order-logistics": {"label": None, "department": "support@varlascooter.com"},
    "after-sales": {"label": None, "department": "customer@varlascooter.com"},
    "manual": {"label": None, "department": None},
}


class Classification(BaseModel):
    """A validated routing decision with the exact matching evidence."""

    primary_group: TaskGroup
    secondary_group: TaskGroup | None = None
    confidence: float = Field(strict=True, ge=0.0, le=1.0)
    matched_rules: list[str] = Field(default_factory=list)
    suggested_label: str | None = None
    suggested_department: str | None = None
    risk_flags: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    id: str
    group: TaskGroup
    confidence: float
    patterns: tuple[re.Pattern[str], ...]


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


# Rules are intentionally narrow. English tokens use boundaries, while Chinese
# rules use exact phrases because CJK text does not have whitespace word breaks.
CLASSIFICATION_RULES: tuple[Rule, ...] = (
    Rule(
        "kol.product_exchange",
        "kol",
        0.99,
        _compile(r"\bproduct[- ]exchange collaboration\b", r"产品置换合作", r"置换合作"),
    ),
    Rule(
        "kol.creator_identity",
        "kol",
        0.98,
        _compile(
            r"\b(?:content |video |tiktok |youtube )?creators?(?: partner)?\b",
            r"\binfluencers?\b",
            r"\bcreator partner\b",
            r"(?<![a-z0-9_])koc(?![a-z0-9_])",
            r"(?<![a-z0-9_])ugc(?: creators?)?(?![a-z0-9_])",
            r"创作者",
            r"内容达人",
            r"视频达人",
            r"达人",
            r"博主",
            r"网红",
        ),
    ),
    Rule(
        "kol.collaboration",
        "kol",
        0.97,
        _compile(
            r"\b(?:creator |brand |paid )?(?:collaborat(?:e|ion)|partnership)\b",
            r"\bsponsor(?:ship)?\b",
            r"\baffiliates?\b",
            r"\bcommission(?: rate)?\b",
            r"\bmedia kit\b",
            r"\baudience insights?\b",
            r"合作测评",
            r"达人合作",
            r"品牌合作",
            r"佣金",
            r"媒体包",
            r"受众洞察",
            r"粉丝画像",
            r"用户生成内容",
        ),
    ),
    Rule(
        "after-sales.refund_warranty",
        "after-sales",
        0.99,
        _compile(
            r"\brefund\b",
            r"\bwarrant(?:y|ies)\b",
            r"\breturn label\b",
            r"退款",
            r"保修",
            r"退货",
        ),
    ),
    Rule(
        "after-sales.failure_repair",
        "after-sales",
        0.98,
        _compile(
            r"\b(?:failed|failure|broken|defective|malfunction(?:ing)?)\b",
            r"\b(?:repair|replacement)\b",
            r"\bwon['’]?t (?:start|charge|turn on)\b",
            r"\bbrakes?\b",
            r"\b(?:caught|catch|catches) fire\b",
            r"\bbattery fire\b",
            r"\b(?:bike|scooter|battery) (?:is|was|went) on fire\b",
            r"\b(?:serious |major )?(?:injury|injuries|safety incident)\b",
            r"\b(?:serious|major) accident\b",
            r"故障",
            r"坏了",
            r"损坏",
            r"维修",
            r"刹车",
            r"起火",
            r"着火",
            r"爆炸",
            r"受伤",
            r"安全事故",
        ),
    ),
    Rule(
        "order.tracking",
        "order-logistics",
        0.99,
        _compile(
            r"\btracking(?: number| update| information)?\b",
            r"\bshipment status\b",
            r"\bdelivery status\b",
            r"\bwhere is (?:my|the) (?:order|package|shipment)\b",
            r"\bwhen will (?:my|the )?order ship(?:ped)?\b",
            r"物流",
            r"追踪",
            r"快递",
        ),
    ),
    Rule(
        "order.order_reference",
        "order-logistics",
        0.98,
        _compile(
            r"\bmy order\b",
            r"\border\s*(?:#|no\.?|number)?\s*\d+\b",
            r"\b(?:package|shipment) (?:for|from) (?:my )?order\b",
            r"\bhas (?:my|the) order shipped\b",
            r"我的订单",
            r"订单号",
            r"什么时候发货",
            r"包裹",
            r"到货",
        ),
    ),
    Rule(
        "pre-sales.price_question",
        "pre-sales",
        0.98,
        _compile(
            r"\bprice\b",
            r"\bhow much\b",
            r"\bshipping cost\b",
            r"\bcost before (?:i|we) order\b",
            r"多少钱",
            r"价格",
            r"运费",
        ),
    ),
    Rule(
        "pre-sales.purchase_specs",
        "pre-sales",
        0.97,
        _compile(
            r"\b(?:buy|purchase) (?:this|the|a|your)\b",
            r"\b(?:product )?specifications?\b",
            r"\b(?:top speed|battery range)\b",
            r"\b(?:product|model|stock|inventory) availability\b",
            r"\b(?:is|are) (?:the )?(?:m5s|m7s|scooter|bike|model|product)s? available\b",
            r"\bavailable (?:in stock|to (?:buy|order|purchase))\b",
            r"\bbefore (?:i|we) (?:buy|order)\b",
            r"购买",
            r"参数",
            r"续航",
            r"最高速度",
            r"有货",
        ),
    ),
)


RISK_PATTERNS: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        "minor_creator",
        _compile(
            r"\b(?:[0-9]|1[0-7])(?:\s*-\s*year\s*-\s*old|\s+years?\s+old)\b",
            r"\bunder\s+(?:the\s+age\s+of\s+)?18\b",
            r"\bminor\s+(?:creator|influencer|child|son|daughter)\b",
        ),
    ),
    (
        "price_negotiation",
        _compile(
            r"\b(?:negotiate|renegotiate|lower|change)\s+(?:the\s+)?price\b",
            r"\bprice negotiation\b",
            r"砍价",
            r"降价",
            r"重新谈价",
        ),
    ),
    (
        "commission_change",
        _compile(
            r"\b(?:change|increase|decrease|raise|lower)\s+(?:(?:the|your|our)\s+)?commission(?: rate)?\b",
            r"\bcommission rate change\b",
            r"调整佣金",
            r"提高佣金",
            r"降低佣金",
        ),
    ),
    (
        "free_product",
        _compile(
            r"\bfree (?:bike|scooter|product|m5s|m7s|e-?bike)\b",
            r"免费(?:车|产品|M5S|M7S)",
            r"赠送(?:车|产品|M5S|M7S)",
        ),
    ),
    (
        "shipping_commitment",
        _compile(
            r"\bwe (?:will|promise to|guarantee to) ship\b",
            r"\b(?:approve|promise|guarantee)\w*\s+(?:the\s+)?(?:shipment|shipping|delivery)\b",
            r"\bship (?:today|tomorrow|immediately)\b",
            r"承诺发货",
            r"批准发货",
            r"保证到货",
        ),
    ),
    (
        "contract_terms",
        _compile(
            r"\b(?:contract|agreement) terms?\b",
            r"\bcontract\b",
            r"\bagreement\b",
            r"合同条款",
            r"协议条款",
        ),
    ),
    (
        "refund",
        _compile(r"\brefund\b", r"退款"),
    ),
    (
        "warranty",
        _compile(r"\bwarrant(?:y|ies)\b", r"保修"),
    ),
    (
        "legal",
        _compile(
            r"\b(?:lawyer|attorney|lawsuit|legal settlement|legal claim)\b",
            r"律师",
            r"诉讼",
            r"法律责任",
        ),
    ),
    (
        "personal_data",
        _compile(
            r"\b(?:passport|social security number|ssn|identity card)\b",
            r"\b(?:phone number|home address)\b",
            r"护照",
            r"身份证",
            r"电话号码",
            r"家庭住址",
        ),
    ),
    (
        "payment_dispute",
        _compile(
            r"\bchargebacks?\b",
            r"\brefus(?:e|es|ed|ing) to pay\b",
            r"\brefusal to pay\b",
            r"\b(?:will not|won['’]?t) pay\b",
            r"信用卡拒付",
            r"拒付",
            r"拒绝付款",
            r"不会付款",
        ),
    ),
    (
        "privacy_request",
        _compile(
            r"\bprivacy (?:complaint|request|violation|concern)\b",
            r"\b(?:delete|erase|remove) (?:my|our) (?:personal )?data\b",
            r"\bdata deletion (?:request|demand)\b",
            r"\bright to (?:erasure|be forgotten)\b",
            r"\b(?:gdpr|ccpa) (?:request|complaint)\b",
            r"隐私投诉",
            r"隐私问题",
            r"删除我的(?:个人信息|数据)",
            r"删除个人数据",
            r"数据删除",
        ),
    ),
    (
        "safety_incident",
        _compile(
            r"\b(?:serious|major) safety incident\b",
            r"\b(?:caught|catch|catches) fire\b",
            r"\bbattery fire\b",
            r"\b(?:bike|scooter|battery) (?:is|was|went) on fire\b",
            r"\b(?:serious |major )?(?:injury|injuries|injured)\b",
            r"\bexplod(?:e|ed|es|ing)\b",
            r"\bhospitali[sz]ed\b",
            r"\b(?:serious|major) accident\b",
            r"安全事故",
            r"起火",
            r"着火",
            r"爆炸",
            r"受伤",
            r"住院",
            r"严重事故",
        ),
    ),
)


ATTACHMENT_ONLY_PATTERNS = _compile(
    r"^(?:please\s+)?(?:see|check)\s+(?:the\s+)?attach(?:ed|ment)\.?$",
    r"^attach(?:ed|ment)\.?$",
    r"^附件(?:请)?(?:查收|查看)?[。.]?$",
)


def normalize_text(*parts: str | None) -> str:
    """Normalize user text without erasing word boundaries used by rules."""

    present = [unicodedata.normalize("NFKC", part) for part in parts if part]
    return re.sub(r"\s+", " ", " ".join(present)).strip().casefold()


def _matches_any(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


MAILBOX_PATTERN = re.compile(
    r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}",
    re.IGNORECASE,
)


def parse_mailbox(value: str | None) -> str | None:
    """Return one canonical mailbox, rejecting ambiguity and header injection."""

    if not isinstance(value, str) or not value.strip() or "\r" in value or "\n" in value:
        return None

    parsed = getaddresses([value])
    if len(parsed) != 1:
        return None
    _, address = parsed[0]
    _, parseaddr_address = parseaddr(value)
    if not address or address.casefold() != parseaddr_address.casefold():
        return None

    raw = value.strip()
    if "<" in raw or ">" in raw:
        if raw.count("<") != 1 or raw.count(">") != 1 or not raw.endswith(">"):
            return None
        display, enclosed = raw.split("<", 1)
        if not display.strip() or enclosed[:-1].strip().casefold() != address.casefold():
            return None
    elif raw.casefold() != address.casefold():
        return None

    canonical = address.casefold()
    if not MAILBOX_PATTERN.fullmatch(canonical):
        return None
    local, domain = canonical.rsplit("@", 1)
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return None
    if any(label.startswith("-") or label.endswith("-") for label in domain.split(".")):
        return None
    return canonical


def is_internal_sender(value: str | None) -> bool:
    address = parse_mailbox(value)
    return bool(address) and address.rsplit("@", 1)[-1] == INTERNAL_DOMAIN


def _risk_flags(text: str) -> list[str]:
    return [
        flag
        for flag, patterns in RISK_PATTERNS
        if _matches_any(text, patterns)
    ]


def _manual(
    *,
    confidence: float,
    matched_rules: list[str] | None = None,
    risk_flags: list[str] | None = None,
) -> Classification:
    return Classification(
        primary_group="manual",
        confidence=confidence,
        matched_rules=matched_rules or [],
        risk_flags=risk_flags or [],
    )


def classify_message(
    text: str | None = None,
    *,
    subject: str | None = None,
    body: str | None = None,
    thread_context: str | None = None,
    sender: str | None = None,
    latest_sender: str | None = None,
) -> Classification:
    """Classify subject, body, and optional context using fixed precedence.

    ``text`` is retained as a convenient one-argument form. When structured
    fields are supplied, all available content is normalized and evaluated.
    """

    normalized = normalize_text(subject, body if body is not None else text, thread_context)
    flags = _risk_flags(normalized)

    sender_value = latest_sender if latest_sender is not None else sender
    sender_address = parse_mailbox(sender_value) if sender_value is not None else None
    if sender_value is not None and sender_address is None:
        return _manual(
            confidence=0.99,
            matched_rules=["guard.invalid_sender"],
            risk_flags=[*flags, "invalid_sender"],
        )
    if is_internal_sender(sender_address):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.internal_sender"],
            risk_flags=[*flags, "internal_sender"],
        )

    sender_local = (
        sender_address.split("@", 1)[0] if sender_address is not None else ""
    )
    sender_domain = (
        sender_address.rsplit("@", 1)[1] if sender_address is not None else ""
    )
    if sender_domain in {"secomapp.com", "uppromote.com"} and re.search(
        r"\b(?:affiliate|marketing|merchant|e-?commerce|software)\b",
        normalized,
    ):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.vendor_promotion"],
            risk_flags=[*flags, "vendor_promotion"],
        )
    if sender_local in {"noreply", "no-reply"} or sender_local.startswith(
        ("noreply-", "no-reply-")
    ):
        if re.search(
            r"\b(?:newsletter|unsubscribe|unlock the report|marketing roi|"
            r"product searches|youtube unlocked)\b",
            normalized,
        ):
            return _manual(
                confidence=0.99,
                matched_rules=["guard.bulk_marketing"],
                risk_flags=[*flags, "bulk_marketing"],
            )
    if re.search(
        r"\b(?:latest websites? (?:i|we) have available|guest posts?|"
        r"backlinks?|link insertion|link building|seo services?)\b",
        normalized,
    ):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.vendor_promotion"],
            risk_flags=[*flags, "vendor_promotion"],
        )
    if re.search(
        r"\bseo\b.{0,100}\b(?:agency|outreach|link building|guest post|"
        r"editorial promotion)\b",
        normalized,
    ):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.vendor_promotion"],
            risk_flags=[*flags, "vendor_promotion"],
        )
    if any(
        pattern.search(normalized)
        for pattern in _compile(
            r"\bwebsite (?:details?|inventory|resource library|catalog)\b"
            r".{0,180}\b(?:traffic|domain authority|domain rating|da\s*\d|"
            r"dr\s*\d|publication placements?|links?)\b",
            r"\bdetails? (?:about|for) websites?\b.{0,180}\b(?:traffic|"
            r"da\s*:?\s*\d|dr\s*:?\s*\d|sample posts?)\b",
            r"\b(?:publication|publisher|editorial) (?:placements?|outreach|"
            r"opportunit(?:y|ies))\b.{0,180}\b(?:website|guest articles?|"
            r"guest posts?|links?|placements?)\b",
            r"(?:网站详情|网站流量|网站资源库).{0,100}(?:da\s*\d|dr\s*\d|"
            r"链接投放|出版物投放|客座文章)",
            r"(?:出版物投放|客座文章).{0,100}(?:网站资源库|链接投放|投放服务)",
        )
    ):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.vendor_promotion"],
            risk_flags=[*flags, "vendor_promotion"],
        )
    if any(
        pattern.search(normalized)
        for pattern in _compile(
            r"\b(?:shopify|e-?commerce)(?:\s+and\s+(?:shopify|e-?commerce))?\s+"
            r"expert\b.{0,100}\b(?:store owners?|increase|boost|grow)\b",
            r"\bfound your (?:online )?store\b.{0,120}\b(?:shopify community|"
            r"optimi[sz]e|increase|boost|grow)\b",
            r"\b(?:visited|browsed) your (?:online )?(?:shop|store)\b.{0,120}"
            r"\b(?:founder|store operator|store owner)\b",
            r"\bshopify\b.{0,120}\b(?:sales optimization|conversion rates?|"
            r"conversion optimization|advertising agency|run ads?|free trial)\b",
            r"\b(?:conversion rate optimization|sales optimization)\b.{0,120}"
            r"\b(?:agency|shopify|online store|run ads?)\b",
            r"\breviewing your (?:online )?store\b.{0,180}\bnoticed\b.{0,180}"
            r"\b(?:visitors? turn into buyers?|not a sales pitch)\b",
            r"\bbrowsed your (?:online )?store\b.{0,180}\bfound\b.{0,180}"
            r"\bwebsite performing as well as you expect\b",
            r"\blooking through your store\b.{0,180}\bfound myself asking\b"
            r".{0,180}\bwebsite performing the way you expected\b.{0,180}"
            r"\bopportunities\b.{0,100}\bimprove (?:the )?customer experience\b",
        )
    ):
        return _manual(
            confidence=0.99,
            matched_rules=["guard.vendor_promotion"],
            risk_flags=[*flags, "vendor_promotion"],
        )

    if not normalized:
        return _manual(confidence=0.05, risk_flags=flags)

    if _matches_any(normalized, ATTACHMENT_ONLY_PATTERNS):
        return _manual(
            confidence=0.98,
            matched_rules=["guard.attachment_only"],
            risk_flags=flags,
        )

    evidence: dict[TaskGroup, list[Rule]] = {
        group: [] for group in TASK_GROUPS if group != "manual"
    }
    for rule in CLASSIFICATION_RULES:
        if _matches_any(normalized, rule.patterns):
            evidence[rule.group].append(rule)

    present = {group for group, rules in evidence.items() if rules}
    if not present:
        return _manual(confidence=0.20, risk_flags=flags)

    if "kol" in present:
        primary: TaskGroup = "kol"
        secondary = next(
            (group for group in ("after-sales", "order-logistics", "pre-sales") if group in present),
            None,
        )
    else:
        primary = next(
            group
            for group in ("after-sales", "order-logistics", "pre-sales")
            if group in present
        )
        secondary = None

    routed_group = secondary if primary == "kol" and secondary else primary
    matched = [
        rule.id
        for group in ("kol", "after-sales", "order-logistics", "pre-sales")
        for rule in evidence[group]
    ]
    confidence = max(rule.confidence for rules in evidence.values() for rule in rules)

    return Classification(
        primary_group=primary,
        secondary_group=secondary,
        confidence=confidence,
        matched_rules=matched,
        suggested_label=GROUP_ROUTES[primary]["label"],
        suggested_department=GROUP_ROUTES[routed_group]["department"],
        risk_flags=flags,
    )
