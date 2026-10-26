# Shipping Evidence Gate

Run this gate before creating a Shopify draft. It is a submission gate, not a cleanup step.

| Field | Required source | Pass condition | Stop condition |
|---|---|---|---|
| Name and email | Current contract | Exact creator identity | Missing or conflicting identity |
| Phone | Current contract or direct creator message | US number normalizes to 10 digits | Blank, illegible, historical, searched, or inferred number |
| Street and house number | Contract plus creator message when available | Exact textual agreement | Map-derived replacement or ambiguity |
| Unit / apartment | Contract plus creator message when available | Exact textual agreement; preserve in `address2` | Missing or conflict |
| City, state, ZIP, country | Contract plus creator message when available | Exact textual agreement | Any absent or conflict component |
| Model / color / extras | Contract | Exact assignment | Unapproved inference |

## Decision rule

- Every required field passes: set `MATCH`, stage one order, then proceed.
- Any source is absent, unreadable, or different: set `REVIEW`, record the original text and the conflict, and stop. Do not ask Maps, old Shopify customer records, billing details, or browser autofill to choose an answer.
- Google Maps is a formatting validator only after the evidence gate passes. It must not generate a street/city/ZIP answer.

## Shopify or Maps conflict recovery

1. Stop the automated flow before submission; do not accept the conflicting value.
2. Open the current contract or direct creator message that supplied the shipping data.
3. Manually transcribe street number/name, unit, city, state, ZIP, and country into the staging row and Shopify shipping-address editor.
4. Compare the visible Shopify shipping card against the source again. If it differs, retain `REVIEW` and stop; do not substitute a Maps result.
5. Record the conflict and source text in `address_verification_note` for audit.

## Post-order discovery

If later evidence proves the staged phone or address was wrong, do not create a replacement shipment. Keep the original `#VARLA` code, clear invented values in the local audit row, mark `STOPPED - logistics correction required`, then inspect the real fulfillment/tracking state before any external change.
