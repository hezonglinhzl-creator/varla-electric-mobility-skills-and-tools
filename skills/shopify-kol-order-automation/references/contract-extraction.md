# Varla Contract Fast Extraction

Extract the whole batch before opening Shopify. Search text/OOXML first; use OCR or visual inspection
only for scanned or handwritten fields.

## Fast anchor order

1. Search for `E-Mail`, `Email`, or `Signing Party / Influencer` to find the creator email.
2. Search for `Shipping Information`, `Shipping information`, or `Shipping Information and Signature`.
3. Inside that section, read:
   - `Full Name`
   - `Shipping Address`
   - `Phone Number`
   - `Code Name`
   - `Impact ID Number`
4. Search the opening information table for `Bike / Product Model`.
5. Record the source filename for audit.

This order is faster and more reliable than reading the contract linearly because Varla contracts keep
operational shipment data near the final signature section.

## Field mapping

| Contract label | Workbook field |
|---|---|
| E-Mail / Signing Party email | `email` |
| Full Name | `name` |
| Shipping Address | `address`, `address2`, `city`, `state`, `zipcode`, `country` |
| Phone Number | `phone` after 10-digit US normalization |
| Code Name | `kol_code_name` |
| Impact ID Number | `impact_id` as text |
| Bike / Product Model | vehicle assignment and first Notes line |

## Parsing the shipping line

Split a one-line US shipping address into:

- primary street line;
- apartment/suite/unit/floor/building detail;
- city;
- state;
- ZIP.

Do not guess a missing ZIP from memory. Verify it using Google Maps before marking `MATCH`.

## Handwriting and image rules

- Compare ambiguous handwritten numbers against the email/contract context and Google Maps.
- Common confusions include `3/8`, `1/7`, `0/6`, and street suffixes.
- If two plausible readings remain, store `REVIEW` and show both possibilities to the user.
- Do not let an old Shopify customer record override the contract.

## Example

Given a contract containing:

```text
Signing Party / Influencer: @example_creator / creator@example.com
Full Name: Example Creator
Shipping Address: 123 Example St, Example City, CA 00000
Phone Number: 202 555 0100
Code Name: examplecreator
Impact ID Number: 0000000
```

Stage:

```text
name=Example Creator
email=creator@example.com
phone=2025550100
address=123 Example St
city=Example City
state=California
country=United States
zipcode=00000
kol_code_name=examplecreator
impact_id=0000000
```

