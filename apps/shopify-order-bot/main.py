from __future__ import annotations

import argparse
import sys

try:
    from .config import SETTINGS, configure_logging
    from .excel_reader import (
        OrderDataError,
        read_first_order,
        save_order_result,
    )
    from .shopify_browser import (
        AddressCheckResult,
        AddressNeedsReview,
        AutomationStepError,
        ShopifyOrderBrowser,
    )
except ImportError:
    from config import SETTINGS, configure_logging
    from excel_reader import (
        OrderDataError,
        read_first_order,
        save_order_result,
    )
    from shopify_browser import (
        AddressCheckResult,
        AddressNeedsReview,
        AutomationStepError,
        ShopifyOrderBrowser,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shopify KOL 订单浏览器自动填写工具 V1"
    )
    parser.add_argument(
        "--step",
        choices=(
            "excel",
            "adspower",
            "browser",
            "create-order",
            "fill",
            "submit-test",
        ),
        default="fill",
        help="单独测试某一步；默认 fill 为完整填写流程",
    )
    return parser.parse_args()


def print_order_summary(order: dict[str, str]) -> None:
    print("\nExcel 第一条有效订单：")
    print(f"- 姓名: {order['name']}")
    print(f"- 邮箱: {order['email']}")
    print(f"- 电话: {order['phone']}")
    print(
        "- 地址: "
        f"{order['address']}, {order['city']}, {order['state']} "
        f"{order['zipcode']}, {order['country']}"
    )
    if order.get("address2"):
        print(f"- 补充地址: {order['address2']}")
    print(f"- 产品: {order['product']}")
    print(f"- Note:\n{order['note']}")
    print(f"- Tag: {order['tag']}")


def wait_before_close(message: str) -> None:
    try:
        input(f"\n{message}\n按 Enter 关闭自动化浏览器...")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> int:
    args = parse_args()
    SETTINGS.ensure_runtime_dirs()
    logger, log_path = configure_logging(SETTINGS)

    if args.step == "excel":
        try:
            order = read_first_order(SETTINGS.excel_path)
        except OrderDataError as exc:
            logger.error("读取 Excel | 失败 | %s", exc)
            print(f"\nExcel 读取失败：{exc}")
            print(f"日志：{log_path}")
            return 1
        else:
            print_order_summary(order)
            logger.info("读取 Excel | 成功 | 已读取第一条有效订单")
            print(f"\n日志：{log_path}")
            return 0

    browser = ShopifyOrderBrowser(SETTINGS, logger)
    try:
        if args.step == "adspower":
            profiles = browser.run_step(
                "读取 AdsPower 环境列表",
                browser.list_adspower_profiles,
            )
            print("\nAdsPower 可用环境：")
            for item in profiles:
                print(
                    f"- 编号: {item.profile_no or '-'} | "
                    f"名称: {item.name or '-'} | "
                    f"ID: {item.profile_id}"
                )
            if not profiles:
                print("- 未发现浏览器环境")
                return 1
            print("\n请把要使用的 ID 写入 .env 的 ADSPOWER_PROFILE_ID。")
            return 0

        order: dict[str, str] | None = None
        if args.step in ("fill", "submit-test"):
            try:
                order = read_first_order(SETTINGS.excel_path)
            except OrderDataError as exc:
                logger.error("读取 Excel | 失败 | %s", exc)
                print(f"\nExcel 读取失败：{exc}")
                print(f"日志：{log_path}")
                return 1

        browser.run_step("连接 AdsPower 浏览器环境", browser.start)
        browser.run_step("打开 Shopify 后台", browser.open_admin)

        browser._current_order = order

        if args.step == "browser":
            print("\n当前浏览器由 AdsPower 保存登录状态。")
            wait_before_close("Shopify 后台已打开。")
            return 0

        browser.run_step("进入 Create order 页面", browser.go_to_create_order)

        if args.step == "create-order":
            wait_before_close("已进入 Create order 页面，未填写、未提交。")
            return 0

        if order is None:
            raise RuntimeError("完整填单流程缺少 Excel 订单数据")

        browser.run_step(
            "添加产品",
            lambda: browser.add_product(order["product"], order.get("quantity", "1")),
        )
        browser.run_step(
            "填写客户和收货地址",
            lambda: browser.fill_customer_and_shipping(order),
        )
        shopify_result = browser.run_step(
            "读取 Shopify 地址提示",
            browser.inspect_shopify_address_feedback,
        )
        externally_verified = (
            order.get("address_verification_status", "").strip().upper()
            == "MATCH"
        )
        if shopify_result.status == "match":
            google_result = shopify_result
            logger.info("Google Maps 地址校对 | Shopify 已确认一致，本次跳过")
        elif shopify_result.status in ("mismatch", "uncertain"):
            raise AddressNeedsReview(
                shopify_result,
                AddressCheckResult(
                    status="uncertain",
                    source="Source evidence",
                    reason=(
                        "Shopify address conflicts with or cannot confirm the source; "
                        "open the contract/creator message and manually re-enter the address"
                    ),
                ),
            )
        elif externally_verified:
            google_result = AddressCheckResult(
                status="match",
                source="External verification",
                visible_address=order.get("address_verification_note", ""),
                reason="Address was independently verified before Shopify submission",
            )
            logger.info("地址校对 | 使用已记录的独立地址核验")
        else:
            google_result = browser.run_step(
                "Google Maps 地址校对",
                lambda: browser.check_google_maps(order),
            )
        browser.run_step(
            "地址一致性决策",
            lambda: browser.require_address_match(shopify_result, google_result),
        )
        browser.run_step(
            "填写 Notes 和 Tags",
            lambda: browser.fill_notes_and_tags(order),
        )
        browser.run_step(
            "提交前严格核对姓名、邮箱、地址和订单内容",
            lambda: browser.verify_order_identity(order),
        )

        if args.step == "submit-test":
            order_code = browser.run_step(
                "创建并标记为已付款",
                lambda: browser.submit_paid_order_and_get_code(order),
            )
            row_index = browser.run_step(
                "回写 VARLA 订单号到 Excel",
                lambda: save_order_result(
                    SETTINGS.excel_path,
                    name=order["name"],
                    email=order["email"],
                    order_code=order_code,
                    order_status="Paid / Unfulfilled",
                    order_url=browser.page.url if browser.page else "",
                    draft_order_code=browser.last_draft_order_code,
                    feishu_sync_status="",
                ),
            )
            print(
                f"\n测试订单已创建：{order_code}；"
                f"已回写 Excel 第 {row_index} 行。"
            )
            print("状态已核验：Paid / Unfulfilled。")
            print(f"日志：{log_path}")
            return 0

        print("\n已填写并校验，未提交。请人工检查所有字段。")
        print(f"日志：{log_path}")
        wait_before_close("请确认后自行决定是否在 Shopify 后台提交订单。")
        return 0

    except AddressNeedsReview as exc:
        print("\n地址不一致或无法确认，自动化已安全停止。")
        print(f"- Shopify: {exc.shopify_result.status} / {exc.shopify_result.reason}")
        print(f"- Google Maps: {exc.google_result.status} / {exc.google_result.reason}")
        if exc.google_result.visible_address:
            print(f"- Google Maps 可见地址: {exc.google_result.visible_address}")
        print("工具未修改冲突地址，也未提交订单。")
        print(f"日志：{log_path}")
        wait_before_close("请打开当前合同或本人消息，人工逐项填入地址后再继续。")
        return 2
    except (AutomationStepError, ValueError) as exc:
        print(f"\n自动化失败：{exc}")
        if browser.final_submission_attempted:
            print(
                "已尝试最终确认。请先在 Shopify Drafts/Orders 中按姓名和邮箱"
                "核对是否已创建，避免重复运行。"
            )
        else:
            print("已保存日志和调试截图；没有提交订单。")
        print(f"日志：{log_path}")
        wait_before_close("请检查页面和错误截图。")
        return 1
    except KeyboardInterrupt:
        print("\n用户已中止；没有提交订单。")
        return 130
    finally:
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
