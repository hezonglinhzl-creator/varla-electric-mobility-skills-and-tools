export const stageRules = [
  { id: "initial_outreach", label: "Initial outreach", keywords: ["collaboration", "collab", "work with you", "partnership"], riskRules: ["do_not_overpromise"], nextAction: "Introduce Varla and ask if they are interested", defaultTone: "casual" },
  { id: "interested_reply", label: "Creator is interested", keywords: ["i would love", "i'm interested", "im interested", "interested", "negotiate a deal", "sounds good", "i'd love", "yes"], riskRules: ["do_not_promise_sponsorship"], nextAction: "Ask for social links and analytics", defaultTone: "casual" },
  { id: "ask_sponsorship", label: "Creator asks for sponsorship", keywords: ["sponsorship", "sponsor me", "sponsor", "free bike", "give me a bike", "can i get"], riskRules: ["do_not_promise_sponsorship", "ask_for_analytics_first"], nextAction: "Ask for social links and basic analytics", defaultTone: "casual" },
  { id: "low_followers", label: "Low followers or follower target", keywords: ["followers", "3k", "5k", "10k", "when i reach", "if i get", "when i hit"], riskRules: ["no_follower_count_guarantee"], nextAction: "Encourage and explain full review criteria", defaultTone: "casual" },
  { id: "ask_post_private_chat", label: "Creator wants to post private chat", keywords: ["post this chat", "post that", "screenshot", "screen shot", "share this conversation", "private chat"], riskRules: ["never_approve_private_chat_post"], nextAction: "Decline posting private brand conversation", defaultTone: "casual" },
  { id: "ask_ai_video", label: "Creator asks about AI video", keywords: ["ai generated", "ai video", "why do you post ai", "fake video", "real product"], riskRules: ["do_not_sound_defensive"], nextAction: "Explain AI-assisted concept videos and real product content", defaultTone: "casual" },
  { id: "provide_email", label: "Creator provides email", keywords: ["@", "email", "gmail.com", "outlook.com", "hotmail.com", "send me"], riskRules: [], nextAction: "Confirm receipt and send details by email", defaultTone: "casual" },
  { id: "email_bounced", label: "Email bounced", keywords: ["bounce", "bounced", "undelivered", "delivery failed", "address not found", "mail delivery"], riskRules: [], nextAction: "Ask creator to confirm email address", defaultTone: "casual" },
  { id: "ask_partnership_details", label: "Creator asks for details", keywords: ["details", "how does it work", "requirements", "what do i need", "tell me more", "partnership details"], riskRules: ["avoid_unapproved_terms"], nextAction: "Explain product exchange and ask for analytics", defaultTone: "semi_formal" },
  { id: "provide_analytics", label: "Creator provides analytics", keywords: ["average views", "engagement", "audience", "top countries", "demographics", "analytics", "insights"], riskRules: ["review_before_confirming"], nextAction: "Review fit and decide structure", defaultTone: "semi_formal" },
  { id: "ask_paid_collab", label: "Creator asks for paid collaboration", keywords: ["paid collaboration", "paid collab", "rate", "rates", "fee", "payment", "budget", "how much do you pay"], riskRules: ["do_not_say_no_budget"], nextAction: "Steer toward product exchange or commission", defaultTone: "warm" },
  { id: "ask_second_bike", label: "Creator asks for second bike", keywords: ["second bike", "another bike", "cameraman", "photographer", "my friend", "two bikes"], riskRules: ["do_not_promise_second_unit"], nextAction: "Focus on first collaboration first", defaultTone: "formal" },
  { id: "confirm_product_exchange", label: "Confirm product exchange", keywords: ["product exchange", "we can move forward", "confirm exchange", "send the product", "requirements form"], riskRules: ["only_after_approval"], nextAction: "Move to form or contract stage", defaultTone: "semi_formal" },
  { id: "confirm_exchange_commission", label: "Confirm exchange plus commission", keywords: ["8%", "commission", "discount code", "shopify code", "affiliate"], riskRules: ["only_if_commission_approved"], nextAction: "Collect payment method and form details", defaultTone: "formal" },
  { id: "send_contract_form", label: "Send contract or form", keywords: ["contract", "agreement", "requirements form", "shipping address", "payment method"], riskRules: [], nextAction: "Ask creator to fill the form", defaultTone: "semi_formal" },
  { id: "signed_contract_received", label: "Signed contract received", keywords: ["signed", "agreement attached", "completed contract", "i filled", "submitted"], riskRules: [], nextAction: "Confirm receipt and review", defaultTone: "formal" },
  { id: "shipping_timeline", label: "Shipping timeline", keywords: ["ship", "shipping", "delivery", "when will", "tracking", "arrive", "july"], riskRules: ["do_not_promise_specific_date"], nextAction: "Give approximate timeline only", defaultTone: "formal" },
  { id: "follow_up", label: "Follow up", keywords: ["follow up", "checking in", "any update", "reminder"], riskRules: ["keep_non_pushy"], nextAction: "Send a short polite follow-up", defaultTone: "casual" },
  { id: "reject_or_close", label: "Reject or close", keywords: ["not a fit", "decline", "not interested", "maybe later", "cannot work"], riskRules: ["protect_brand_image"], nextAction: "Close politely and keep relationship warm", defaultTone: "warm" },
  { id: "unknown", label: "Unknown", keywords: [], riskRules: ["manual_review"], nextAction: "Ask a safe clarifying question", defaultTone: "casual" }
];

export function classifyStage(text) {
  const source = String(text || "").toLowerCase();
  let best = stageRules[stageRules.length - 1];
  let bestMatches = [];
  for (const rule of stageRules) {
    if (rule.id === "unknown") continue;
    const matches = rule.keywords.filter((keyword) => source.includes(keyword.toLowerCase()));
    if (matches.length > bestMatches.length) {
      best = rule;
      bestMatches = matches;
    }
  }
  const confidence = bestMatches.length === 0 ? 0.2 : Math.min(0.95, 0.45 + bestMatches.length * 0.18);
  return { detectedStage: best.id, confidence, matchedKeywords: bestMatches, rule: best };
}
