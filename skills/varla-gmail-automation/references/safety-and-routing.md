# Safety and Reply Routing

## Permission model

`gmail.modify` can read mail and attachments, create drafts, send replies, and modify mailbox labels/state. Treat the token as a high-value secret.

The OAuth access token is an authentication credential, not a consumable balance. Gmail API calls consume Gmail quota units. AI reading and generation consume the selected AI provider's tokens or credits.

## Human control levels

### Low risk

- Thank a creator.
- Request social links, media kit, audience insights, average views, top audience countries, or shipping country/state.
- Confirm receipt of files without approving cooperation.

Default to a draft. Automatic sending may be enabled later only for a narrowly defined rule and a tested sender/thread guard.

### Medium risk

- Content direction
- Product model discussion
- Deliverables
- Timing
- Draft feedback
- Follow-up after incomplete information

Always require human review.

### High risk

- Price or paid sponsorship
- Commission
- Free product
- Shipping approval or delivery promise
- Contract terms
- Refund, warranty, or legal language
- Account credentials or personal data

Never auto-send. Generate a draft and escalate.

## Loop and duplication prevention

Before sending:

1. Confirm the latest message is from the external creator.
2. Confirm the same source message ID has not already been processed.
3. Confirm no teammate replied after the source message.
4. Confirm the reply recipient resolved from `Reply-To` or `From`.
5. Preserve the Gmail thread ID and RFC `In-Reply-To`/`References` headers.
6. Record source message ID, outgoing message ID, thread ID, timestamp, rule, and approver.

The authenticated mailbox `info@varlascooter.com` is always the outbound sender, not the reply recipient. The reply recipient is the canonical sender of the latest verified external message. For an existing conversation, never switch to a standalone compose action. A quoted self-address display name is valid only when it exactly matches the enclosed address; an address-like mismatch is ambiguous and must stop.

## Delivery and classification

Gmail API sending places the outgoing message in the authenticated sender's Sent mailbox. Recipient-side Primary/Promotions classification is controlled by the recipient's Gmail classifier and cannot be guaranteed by the sender.

Prefer one-to-one, relevant copy. Avoid unsupported claims, excessive marketing language, unnecessary links, and image-heavy first outreach.

## Failure behavior

- Wrong authenticated account: stop.
- Missing recipient or ambiguous thread: stop.
- OAuth or quota error: do not retry indefinitely; use bounded exponential backoff.
- Uncertain business term: preserve it as pending and request human direction.
- Partial send uncertainty: search Sent by thread/message before retrying to avoid duplicates.

## Guarded vendor-promotion Trash disposition

- Applies only to deterministic `vendor_promotion` evidence: unsolicited guest-post, backlink, link-insertion, SEO-service, website-inventory, Shopify, or e-commerce growth-service sales; an exact locally blocked sender is also eligible.
- Does not apply to ordinary KOL cooperation, creator pitches, no-reply newsletters, or ambiguous marketing mail.
- In the current local command center, standing user authorization permits this guarded rule every 600 seconds and during bounded historical scans. Other installations remain manual until separately authorized.
- Verify `info@varlascooter.com`, exact thread ID, latest external message ID, and canonical sender immediately before mutation.
- Stop if a Varla teammate replied after the source message.
- Move the exact thread to Gmail `TRASH`, read back the thread, and require `TRASH` with no `INBOX`. Never permanently delete the message.
- Persist the lowercase bare sender in the local blocklist only after Gmail verification succeeds.
- Store only IDs, rule, result, and timestamp in the command-center audit; do not store message content in the mutation audit.
- Never permanently empty Trash. Cap newly created Gmail sender-block filters at 40 per daily run and keep ambiguous/KOL/dealer mail untouched.
