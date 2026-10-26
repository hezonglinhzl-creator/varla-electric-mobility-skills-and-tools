"""Immutable, dependency-free content approved for the four-stage Gmail test."""

STAGE_SLUGS = ("invitation", "communication", "agreement", "maintenance")

STAGES = (
    (
        "Collaboration invitation",
        """Hi KOL Test Creator,

This is a controlled Varla KOL workflow test sent only to the designated test mailbox.

We are testing the invitation stage of a potential creator collaboration. If this were a real outreach, we would ask the creator to share:

- Social profile links
- Media kit or audience insights
- Recent average views
- Top audience countries
- Shipping country and state

No collaboration, product, commission, shipping, or deadline is approved by this test message.

Best,
Varla Marketing Team

Test run: {run_id}
Stage: 1 of 4 - Invitation
""",
    ),
    (
        "Collaboration information follow-up",
        """Hi KOL Test Creator,

This is a controlled Varla KOL workflow test sent only to the designated test mailbox.

Thank you for sharing the initial creator information. We are testing the communication and evaluation stage. The following items would still need to be confirmed before any real collaboration could be approved:

- Final platform and content direction
- Product model
- Deliverables and timing
- Shipping information
- Commercial terms, if applicable

This message does not approve a collaboration, product shipment, commission, payment, or deadline.

Best,
Varla Marketing Team

Test run: {run_id}
Stage: 2 of 4 - Communication
""",
    ),
    (
        "Test agreement and content requirements",
        """Hi KOL Test Creator,

This is a controlled Varla KOL workflow test sent only to the designated test mailbox.

Attached are:

1. A TEST-ONLY Varla KOL collaboration agreement
2. The Varla KOL Content Creation Requirements

The agreement is clearly marked "TEST ONLY - NOT LEGALLY BINDING" and must not be used or signed for a real collaboration. All unconfirmed commercial, product, payment, and shipping fields remain "To be confirmed."

This email validates the contract-delivery stage only. It does not approve a real collaboration, product shipment, commission, payment, or deadline.

Best,
Varla Marketing Team

Test run: {run_id}
Stage: 3 of 4 - Agreement package
""",
    ),
    (
        "Content workflow follow-up",
        """Hi KOL Test Creator,

This is a controlled Varla KOL workflow test sent only to the designated test mailbox.

We are testing the post-agreement content-maintenance stage. The normal workflow would be:

- Confirm the content direction before filming
- Submit drafts before posting
- Keep product information accurate
- Follow the safety requirements
- Use approved tags, links, music, and calls to action
- Send the published links and agreed raw footage after posting

Any change to product, timing, payment, commission, shipping, or contract terms would require separate written confirmation.

Best,
Varla Marketing Team

Test run: {run_id}
Stage: 4 of 4 - Content maintenance
""",
    ),
)


def exact_subject(stage: int, run_id: str) -> str:
    suffix = STAGES[stage - 1][0]
    return f"[VARLA TEST][Stage {stage}/4][{run_id}] {suffix}"


def exact_body(stage: int, run_id: str) -> str:
    return STAGES[stage - 1][1].format(run_id=run_id)
