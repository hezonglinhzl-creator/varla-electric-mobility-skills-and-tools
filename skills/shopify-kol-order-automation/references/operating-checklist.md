# Operating Checklist

## Before browser work

- [ ] Extract the entire supplied batch.
- [ ] Confirm required fields: name, email, phone, address, city, state, ZIP, model/color.
- [ ] Treat a standalone `To be confirmed` model or address component as a stop; a real value later on the same line may be used only when unambiguous.
- [ ] Build an evidence comparison before Shopify: current contract versus direct creator message for street number/name, unit, city, state, ZIP, country, and phone.
- [ ] Require an exact match on every address component. A missing or conflicting component is `REVIEW` and stops the row.
- [ ] Require `shipping_phone_source` = `CONTRACT` or `CREATOR_MESSAGE`; do not use a historical, inferred, searched, or copied phone.
- [ ] Require `shipping_address_source` = `CONTRACT_EXACT`, `CREATOR_MESSAGE`, or `CONTRACT_AND_CREATOR`; `MAPS_INFERRED` is prohibited.
- [ ] Confirm every US phone is exactly 10 digits in Excel.
- [ ] Confirm Notes code and `VAR-GIFTSET-002`.
- [ ] Confirm order tag is `KOL-PETER`.
- [ ] Confirm old canceled/test rows are clearly separated.
- [ ] Run all project tests.

## Address verification

- [ ] Compare Shopify shipping address, never billing address.
- [ ] Use Google Maps only to validate an already sourced exact address; never use it to infer or replace a missing/conflicting address.
- [ ] If Shopify or Maps conflicts, reopen the source contract/creator message and manually enter the source address; do not accept the conflicting value.
- [ ] Match street number/name, city, state, and ZIP.
- [ ] Preserve apartment/suite/unit/floor/building details in `address2`.
- [ ] Mark uncertain handwritten addresses for human review.
- [ ] Close the Maps tab after confirmation.

## Per-order pre-submit gate

- [ ] User explicitly authorized real submission in the current conversation.
- [ ] Evidence comparison is complete and exact; phone and address source fields passed their hard gate.
- [ ] Name matches the current Excel row.
- [ ] Email matches the current Excel row.
- [ ] Normalized shipping phone matches the current Excel row.
- [ ] Shipping address and address2 match.
- [ ] Product is `Aftersale-KOL/KOC Exclusive`, quantity 1.
- [ ] Notes contain the correct model/color code and gift-set line.
- [ ] `KOL-PETER` is present.
- [ ] No marketing checkbox was selected.
- [ ] No test customer or previous customer's data is visible.

## After clicking Create order

- [ ] Capture `#VARLA`.
- [ ] If only `#D...` appears but the live page confirms Paid / Unfulfilled, record it as provisional, skip re-submission, and queue `#VARLA` reconciliation.
- [ ] Capture paid/fulfillment status.
- [ ] Capture direct order URL and draft code when available.
- [ ] Write the result to the same identity's pending row immediately.
- [ ] Confirm writeback before starting the next person.

## Failure handling

- Connection/CAPTCHA/risk verification: stop and wait for the user; do not refresh.
- Locator failure before submission: inspect screenshot and current DOM; do not restart the entire batch.
- Failure after possible submission: search Shopify first; do not retry until duplicates are ruled out.
- A visible `#D...` plus Paid / Unfulfilled is a successful provisional order, not an unknown submission. Do not create another order.
- Address/phone mismatch: stop before submitting and correct from the confirmed source.
- Missing phone, missing ZIP, unreadable handwritten component, or contract/message conflict: mark `REVIEW`, do not create a customer, draft, order, or fulfillment.
- Ambiguous Excel identity: stop and show the conflicting rows.
- A post-order evidence error: do not create a replacement or re-ship. Preserve the order code, mark `STOPPED - logistics correction required`, clear invented data, and obtain a logistics decision after reading fulfillment/tracking state.

## Final reconciliation

- [ ] Read the current Shopify orders list.
- [ ] Map results by email/name rather than row position.
- [ ] Update statuses if fulfillment/tracking automation changed them.
- [ ] Verify one intended new order per person.
- [ ] Render workbook data and result previews.
- [ ] Scan formula errors.
- [ ] Run all tests.
- [ ] Return a person → model → `#VARLA` → status table and clickable workbook/folder links.
