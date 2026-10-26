(function () {
  if (window.__varlaKolReplyAssistantLoaded) return;
  window.__varlaKolReplyAssistantLoaded = true;

  const STAGE_RULES = [
    { id: "creative_direction_script", label: "创意方向 / 脚本规划", keywords: ["creative direction", "key selling points", "script/concept", "script", "concept", "filming", "after approval", "brand's goals", "brand goals", "content around"], nextAction: "Confirm direction, suggest content angle, and ask for next planning details" },
    { id: "initial_outreach", label: "首次邀约", keywords: ["collaboration", "collab", "work with you", "partnership"], nextAction: "Introduce Varla and ask if they are interested" },
    { id: "interested_reply", label: "对方表示感兴趣", keywords: ["i would love", "i'm interested", "im interested", "interested", "negotiate a deal", "sounds good", "i'd love", "yes"], nextAction: "Ask for social links and analytics" },
    { id: "ask_sponsorship", label: "对方索要赞助", keywords: ["sponsorship", "sponsor me", "sponsor", "free bike", "give me a bike", "can i get"], nextAction: "Ask for social links and basic analytics" },
    { id: "low_followers", label: "粉丝少 / 粉丝数目标", keywords: ["followers", "3k", "5k", "10k", "when i reach", "if i get", "when i hit"], nextAction: "Encourage and explain full review criteria" },
    { id: "ask_post_private_chat", label: "想发布私聊截图", keywords: ["post this chat", "post that", "screenshot", "screen shot", "share this conversation", "private chat"], nextAction: "Decline posting private brand conversation" },
    { id: "ask_ai_video", label: "询问 AI 视频", keywords: ["ai generated", "ai video", "why do you post ai", "fake video", "real product"], nextAction: "Explain AI concept videos and real product content" },
    { id: "provide_email", label: "对方提供邮箱", keywords: ["@", "email", "gmail.com", "outlook.com", "hotmail.com", "send me"], nextAction: "Confirm receipt and send details by email" },
    { id: "email_bounced", label: "邮箱退信", keywords: ["bounce", "bounced", "undelivered", "delivery failed", "address not found", "mail delivery"], nextAction: "Ask creator to confirm email address" },
    { id: "ask_partnership_details", label: "询问合作细节", keywords: ["details", "how does it work", "requirements", "what do i need", "tell me more", "partnership details"], nextAction: "Explain product exchange and ask for analytics" },
    { id: "provide_analytics", label: "对方提供数据", keywords: ["average views", "engagement", "audience", "top countries", "demographics", "analytics", "insights"], nextAction: "Review fit and decide structure" },
    { id: "need_us_confirmation", label: "确认是否美国地区", keywords: ["based in", "located in", "where are you based", "are you in the us", "u.s.", "united states"], nextAction: "Confirm whether the creator is US-based before moving forward" },
    { id: "europe_market_delay", label: "欧洲 / 非美国市场", keywords: ["france", "germany", "netherlands", "europe", "eu", "european", "based in europe"], nextAction: "Politely explain US-first rollout and keep the contact warm" },
    { id: "rate_too_high_decline", label: "报价太高 / 礼貌拒绝", keywords: ["$5,000", "$5000", "5000", "start at", "starts at", "our collabs start", "pricing", "rate", "rates", "fee", "outside of our current budget", "outside our current budget", "too high"], nextAction: "Politely decline the paid rate and keep door open for product exchange or future cooperation" },
    { id: "ask_paid_collab", label: "要求付费合作", keywords: ["paid collaboration", "paid collab", "payment", "budget", "how much do you pay"], nextAction: "Steer toward product exchange or commission" },
    { id: "ask_second_bike", label: "要求第二台车", keywords: ["second bike", "another bike", "cameraman", "photographer", "my friend", "two bikes"], nextAction: "Focus on first collaboration first" },
    { id: "confirm_product_exchange", label: "确认置换合作", keywords: ["product exchange", "we can move forward", "confirm exchange", "send the product", "requirements form"], nextAction: "Move to form or contract stage" },
    { id: "confirm_exchange_commission", label: "置换 + 佣金", keywords: ["8%", "commission", "discount code", "shopify code", "affiliate"], nextAction: "Collect payment method and form details" },
    { id: "send_contract_form", label: "发送合同 / 表格", keywords: ["contract", "agreement", "requirements form", "shipping address", "payment method"], nextAction: "Ask creator to fill the form" },
    { id: "signed_contract_received", label: "已收到签署合同", keywords: ["signed", "agreement attached", "completed contract", "i filled", "submitted"], nextAction: "Confirm receipt and review" },
    { id: "shipping_timeline", label: "发货时间说明", keywords: ["ship", "shipping", "delivery", "when will", "tracking", "arrive", "july"], nextAction: "Give approximate timeline only" },
    { id: "support_or_refund", label: "售后 / 退款 / 客服", keywords: ["refund", "return", "support", "factory inspection", "inspection", "tracking issue", "damaged", "broken", "customer service"], nextAction: "Keep the reply evidence-based and route to support" },
    { id: "follow_up", label: "跟进催回复", keywords: ["follow up", "checking in", "any update", "reminder"], nextAction: "Send a short polite follow-up" },
    { id: "reject_or_close", label: "拒绝 / 暂不匹配", keywords: ["not a fit", "decline", "not interested", "maybe later", "cannot work"], nextAction: "Close politely and keep relationship warm" },
    { id: "unknown", label: "未知场景", keywords: [], nextAction: "Ask a safe clarifying question" }
  ];

  const TEMPLATES = [
    ["creative_direction_script", "Thanks for sharing your approach. That sounds good. Right now, we are mainly focusing on cycling, instructional, and practical riding videos. Since your content can also connect with family and kids-at-home scenarios, we could build the concept around both adults and children while still keeping the product benefits clear. I also checked the social link you shared, and the data looks promising. Once we align on the key selling points, we can move forward with the script/concept review before filming.", "Align on content angle and key selling points before script approval", ["Do not approve filming before the concept/script is reviewed"]],
    ["initial_outreach", "Hi! We are from the Varla Marketing Team and we like your content style. We are currently exploring product exchange partnerships with creators who can make authentic riding, review, unboxing, or instructional short videos. Would you be open to learning more?", "Ask whether the creator is open to collaboration", ["Do not promise sponsorship in the first message"]],
    ["interested_reply", "Awesome, thanks for your interest! Could you send over your social links, average views, and top audience countries? That will help us better understand the right collaboration structure.", "Ask for social links and audience data", ["Do not promise sponsorship or a free bike yet"]],
    ["ask_sponsorship", "Thanks for reaching out! Could you send over your TikTok/Instagram links, average views, and top audience countries? We usually review creator fit, content quality, and audience match before confirming any collaboration.", "Ask for social links and audience data", ["Do not promise sponsorship"]],
    ["low_followers", "Totally understand, and we really appreciate your interest. Just to clarify, sponsorship decisions are not based only on follower count. We also look at content quality, engagement, audience fit, and brand alignment. Keep creating strong content, and we would be happy to review again as your account grows.", "Encourage creator and explain review criteria", ["Never say a follower target guarantees sponsorship"]],
    ["ask_post_private_chat", "Thanks for asking! Please do not post screenshots of private brand conversations, even if the brand name is removed. You are welcome to post about your own content goals and tag us, but please make sure it does not sound like a guaranteed sponsorship or confirmed collaboration.", "Protect private conversation and clarify allowed content", ["Do not approve posting private chat screenshots"]],
    ["ask_ai_video", "We use some AI-assisted concept videos to explore creative ideas and show the vibe of the product faster. The product is real, and we will also be posting more real riding footage, creator content, and customer videos soon.", "Reassure creator that real product content is coming", []],
    ["provide_email", "Thanks! I will send over the details by email. Please keep an eye on your inbox.", "Send details by email", []],
    ["email_bounced", "I tried sending the email, but it looks like the address did not go through. Could you double-check the email address for me?", "Ask creator to confirm email", []],
    ["ask_partnership_details", "Thanks for reaching out. Our current collaboration model is mainly product exchange, and in some cases we may add affiliate commission depending on creator fit, content quality, audience, and performance. Could you share your social links, audience demographics, average views, top audience countries, and any previous campaign data?", "Ask for analytics and campaign data", ["Do not guarantee paid collaboration"]],
    ["need_us_confirmation", "Thanks for your interest. At this stage, we are mainly focusing on U.S.-based collaborations. May I ask if you are currently based in the United States?", "Confirm US location before continuing", ["Do not promise non-US collaboration yet"]],
    ["europe_market_delay", "Thanks so much for your interest. At the moment, our current creator rollout is mainly focused on the U.S. market first. We would still love to stay in touch and revisit a possible collaboration once the Europe side is confirmed internally.", "Explain US-first rollout and keep contact warm", ["Do not promise Europe launch timing unless internally confirmed"]],
    ["rate_too_high_decline", "Thanks for being upfront with your pricing. We completely understand your rates and respect the value of your content. At the moment, that campaign fee is outside of our current collaboration budget, so we may not be able to move forward with a paid campaign at that level right now. Our current model is mainly product exchange plus possible affiliate commission. We would still love to stay in touch and revisit a potential partnership in the future as the brand continues to grow.", "Politely decline the high paid rate and keep the relationship open", ["Do not sound dismissive", "Do not say the creator is overpriced"]],
    ["ask_paid_collab", "Thanks for sharing. Right now, our main focus is product exchange partnerships, sometimes with affiliate commission depending on creator fit and performance. If the content performs well, we would definitely be open to discussing a longer-term partnership later on.", "Keep door open while steering to exchange or commission", ["Do not say there is no budget"]],
    ["ask_second_bike", "Thanks for sharing the idea. Regarding a second bike for your cameraman, let us focus on getting the first collaboration rolling and seeing how the initial content performs. We can revisit the idea of a second unit once we have some traction with the first collaboration.", "Move forward with the first unit first", ["Do not promise a second bike"]],
    ["confirm_product_exchange", "Great, we are happy to move forward with a product exchange collaboration. We would love to see authentic riding, unboxing, review, and short-form content from you. The next step is to complete the contract / requirements form so we can collect the needed details.", "Send contract or requirements form", ["Only use after Team Member confirms exchange"]],
    ["confirm_exchange_commission", "Thanks for sending over the details and analytics. Everything looks solid. We are happy to move forward with a product exchange + affiliate commission model. We will provide the product, and we can offer an 8% commission on sales generated through your discount code. The default commission period is 3 months.", "Send form and collect payment/shipping details", ["Use only when commission is approved"]],
    ["send_contract_form", "Could you please fill out the contract / content requirements form? We will need your shipping address, preferred payment method or ID, social accounts, planned content format, and expected posting timeline.", "Collect form details", []],
    ["signed_contract_received", "Thanks for sending the signed agreement. We have received it and will review everything on our end. Once everything looks good, we will move forward with the next steps and keep you updated on the shipping schedule.", "Review agreement and prepare next steps", []],
    ["shipping_timeline", "Thanks again for your support. The product is expected to be available around July. We hope to ship it out in July and will keep you updated once the shipping schedule is confirmed.", "Keep creator updated when schedule is confirmed", ["Do not promise a specific shipping date"]],
    ["support_or_refund", "Thanks for reaching out. We want to make sure this is handled accurately. Please send the order email, any relevant screenshots, and a short summary of the issue so our support team can review the case properly.", "Collect evidence and route to support", ["Do not promise refund or resolution before support review"]],
    ["follow_up", "Hi {{name}}, just wanted to follow up and see if you had a chance to check my last message. Happy to answer any questions.", "Wait for reply", ["Keep it light and non-pushy"]],
    ["reject_or_close", "Thanks so much for your interest and for sharing your information. At this moment, it may not be the best fit for our current campaign, but we really appreciate your support and would be happy to stay connected for future opportunities.", "Close politely and keep relationship warm", ["Do not criticize the creator"]]
  ].map(([stage, template, nextAction, riskNotes], index) => ({ id: `template_${index + 1}`, stage, template, nextAction, riskNotes }));

  const DEFAULT_SETTINGS = {
    chatgptUrl: "https://chatgpt.com/",
    defaultCommission: "8%",
    commissionValidity: "3 months"
  };

  const PRODUCT_CANON = {
    M5S: {
      price: "$1,199",
      shortIntro: "The M5S is our default first-stage creator collaboration bike. It is designed to feel fun, approachable, and easy to enjoy for outdoor, family, POV, and daily-use content.",
      guidance: "Default creator collaboration bike. Product exchange first. Best for family, teen, lifestyle, POV, first-impression, riding and light off-road content."
    },
    M7S: {
      price: "$1,999",
      shortIntro: "The M7S is our higher-performance model for stronger creators, more aggressive riding scenes, FPV content, and adult riders.",
      guidance: "Upgrade-tier bike for stronger KOLs, high-power riding, FPV chase shots, adult riders, stunts and aggressive off-road content."
    },
    Mavericks: {
      price: "$1,199",
      shortIntro: "Mavericks is a legacy or related model reference. Keep it separate from M5S in external replies.",
      guidance: "If a creator confuses Mavericks and M5S, clarify that current priority is M5S and M7S."
    }
  };

  const INTERNAL_PLAYBOOK = {
    coreRules: [
      "US market first. Europe stays future-stage unless internally confirmed.",
      "Product exchange is the default first collaboration model.",
      "Affiliate commission can be added for qualified creators, commonly 8% for stronger KOLs.",
      "M5S is the default first-stage collaboration bike. M7S needs stronger fit or internal approval.",
      "Prefer authentic riding, POV, talking, daily-use, family/outdoor, and real-world content over hard ads."
    ],
    deliverables: [
      "Default creator package: 2 short vertical videos plus 2 sets of usable original raw footage.",
      "Main posting platforms: TikTok, Instagram Reels/Feed/Story, and YouTube Shorts when applicable.",
      "Typical video length: 15-35 seconds. Some pieces can extend to 40-60 seconds if needed.",
      "9:16 vertical format. 4K preferred; 2K or 1080p acceptable.",
      "Product feature videos should use English voiceover and clearly explain 2-4 selling points."
    ],
    postingRules: [
      "Post only after draft approval.",
      "Instagram posts should add @varla_adventure as collaborator whenever possible.",
      "TikTok posts should tag or mention @varla_sport in the caption.",
      "YouTube videos and Shorts should include @VarlaScooter in the description.",
      "Approved posts should stay live and should not be deleted, hidden, archived, or made private without written approval."
    ],
    rawFootageRules: [
      "Provide all usable original clips for each video, organized by Video 1 and Video 2.",
      "Include riding clips, detail shots, environment shots, alternative takes, and useful B-roll.",
      "Keep original resolution and avoid heavy compression."
    ],
    safetyRules: [
      "Show proper safety gear and safe permitted riding areas.",
      "Do not show reckless public-road racing, illegal road behavior, or dangerous stunts.",
      "Do not exaggerate speed, range, price, discount, or product claims.",
      "Use commercially usable or platform-safe music."
    ]
  };

  let root;
  let shadow;
  let settings = { ...DEFAULT_SETTINGS };
  let tesseractModulePromise;
  let pendingDragState = null;
  let dragState = null;
  let dragLauncher = null;
  let ocrDropActive = false;
  const DRAG_MOVE_THRESHOLD = 8;
  const DRAG_HOLD_DELAY = 180;

  function getSelectionText() {
    const selected = window.getSelection()?.toString()?.trim();
    if (selected) return selected;

    const active = document.activeElement;
    if (active && (active.tagName === "TEXTAREA" || active.tagName === "INPUT")) {
      const start = active.selectionStart || 0;
      const end = active.selectionEnd || 0;
      return active.value.slice(start, end).trim() || active.value.trim();
    }

    return "";
  }

  function getEditableTarget() {
    const active = document.activeElement;
    if (active && (active.tagName === "TEXTAREA" || active.tagName === "INPUT" || active.isContentEditable)) return active;
    const selectors = ["textarea", "input[type='text']", "[contenteditable='true']", "[role='textbox']"];
    return selectors.map((selector) => document.querySelector(selector)).find(Boolean);
  }

  function insertText(text) {
    const target = getEditableTarget();
    if (!target) return { ok: false, reason: "No editable input found. Reply was copied instead." };

    target.focus();
    if (target.tagName === "TEXTAREA" || target.tagName === "INPUT") {
      const start = target.selectionStart ?? target.value.length;
      const end = target.selectionEnd ?? target.value.length;
      target.value = `${target.value.slice(0, start)}${text}${target.value.slice(end)}`;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
      return { ok: true };
    }

    document.execCommand("insertText", false, text);
    target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
    return { ok: true };
  }

  function detectPlatform() {
    const url = location.href.toLowerCase();
    if (url.includes("instagram.com")) return "instagram";
    if (url.includes("tiktok.com")) return "tiktok";
    if (url.includes("business.facebook.com")) return "meta_business";
    if (url.includes("mail.google.com") || url.includes("gmail.com")) return "gmail";
    return "unknown";
  }

  function cleanText(text) {
    const raw = String(text || "").replace(/\r/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
    const emails = [...raw.matchAll(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi)].map((m) => m[0]);
    return { raw, emails: [...new Set(emails)] };
  }

  function classifyStage(text) {
    const source = String(text || "").toLowerCase();
    let best = STAGE_RULES.find((rule) => rule.id === "unknown");
    let bestMatches = [];
    for (const rule of STAGE_RULES) {
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

  function selectValue(target, value) {
    const input = shadow.getElementById(target);
    if (input) input.value = value;
    shadow.querySelectorAll(`[data-target="${target}"]`).forEach((button) => {
      button.classList.toggle("active", button.dataset.value === value);
    });
  }

  function detectProduct(text) {
    const selected = shadow.getElementById("product").value;
    if (selected !== "Auto") return selected;
    const lower = text.toLowerCase();
    if (lower.includes("m5s")) return "M5S";
    if (lower.includes("m7s")) return "M7S";
    if (lower.includes("mavericks")) return "Mavericks";
    return "Auto";
  }

  function collectContext() {
    const cleaned = cleanText(shadow.getElementById("conversation").value);
    const auto = classifyStage(cleaned.raw);
    const platform = shadow.getElementById("platform").value || detectPlatform();
    const context = {
      platform,
      stage: shadow.getElementById("stage").value || auto.detectedStage,
      tone: shadow.getElementById("tone").value,
      product: detectProduct(cleaned.raw),
      creatorName: shadow.getElementById("creatorName").value.trim(),
      creatorEmail: shadow.getElementById("creatorEmail").value.trim() || cleaned.emails[0] || "",
      conversationText: cleaned.raw,
      auto
    };
    shadow.getElementById("creatorEmail").value = context.creatorEmail;
    shadow.getElementById("detectedMeta").textContent = `识别场景：${auto.rule.label} | ${Math.round(auto.confidence * 100)}% | ${auto.matchedKeywords.join(", ") || "无关键词"}`;
    return context;
  }

  function resolveVariables(text, context) {
    return String(text)
      .replaceAll("{{name}}", context.creatorName || "there")
      .replaceAll("{{commission}}", settings.defaultCommission)
      .replaceAll("{{commissionValidity}}", settings.commissionValidity);
  }

  function retrieveTemplate(context) {
    return TEMPLATES.find((item) => item.stage === context.stage) || TEMPLATES[0];
  }

  function makeVariant(base, context, toneKey, index) {
    const name = context.creatorName || "there";
    const isEmail = context.platform === "gmail";
    const productLine = context.product !== "Auto" ? ` We are reviewing this around the ${context.product}.` : "";
    const custom = getStageSpecificVariants(context, name);
    if (custom?.[toneKey]?.[index - 1]) return custom[toneKey][index - 1];
    const natural = [
      base,
      `${base.replace(/^Thanks/, "Thanks so much")}\n\nThat will help us review the best next step.`,
      `${base}${productLine}`,
      `${base}\n\nNo rush, just send what you have.`
    ];
    const formal = [
      `Hi ${name},\n\nThank you for your message. ${base}\n\nBest,\nTeam Member\nVarla Marketing Team`,
      `Hi ${name},\n\nThanks for reaching out. ${base}\n\nThis will help us review the collaboration fit more accurately.\n\nBest,\nTeam Member\nVarla Marketing Team`,
      `Hi ${name},\n\nThank you for the update. ${base}${productLine}\n\nBest,\nTeam Member\nVarla Marketing Team`,
      `Hi ${name},\n\nThank you. ${base}\n\nPlease send the available details when convenient, and we will review the next step.\n\nBest,\nTeam Member\nVarla Marketing Team`
    ];
    const short = [
      base.split(". ").slice(0, 2).join(". ").replace(/\.$/, "") + ".",
      "Thanks! Could you send your social links, average views, and top audience countries so we can review the fit?",
      "Appreciate your interest. Please send your basic creator stats and links, and we will take a look.",
      "Thanks! Send over the key details when you can, and we will review the next step."
    ];
    const bank = { casual: natural, formal, short };
    const selected = bank[toneKey] || natural;
    const reply = selected[index - 1] || selected[0];
    if (isEmail && toneKey !== "short") return reply;
    return reply.replace(/^Hi there,\n\n/, "").trim();
  }

  function getStageSpecificVariants(context, name) {
    if (context.stage === "need_us_confirmation") {
      return {
        casual: [
          "Thanks for your interest. At this stage, we are mainly focusing on U.S.-based collaborations first. May I ask if you are currently based in the United States?",
          "Appreciate the interest. We are currently prioritizing U.S. creators for this rollout, so could you confirm whether you are based in the U.S.?"
        ],
        formal: [
          `Hi ${name},\n\nThank you for your interest. At this stage, our current creator rollout is mainly focused on U.S.-based collaborations. Could you please confirm whether you are currently based in the United States?\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nWe appreciate your message. Before moving forward, could you please confirm whether you are currently located in the U.S.? Our current creator collaboration stage is mainly focused on the U.S. market first.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Thanks! We are mainly focusing on U.S.-based collaborations right now. Are you currently based in the U.S.?",
          "Could you confirm whether you are in the U.S.? This rollout is mainly U.S. first for now."
        ]
      };
    }

    if (context.stage === "europe_market_delay") {
      return {
        casual: [
          "Thanks so much for your interest. Right now, our current creator rollout is mainly focused on the U.S. market first. We would still love to stay in touch and revisit a possible collaboration once the Europe side is confirmed internally.",
          "Really appreciate your interest. At the moment, we are mainly pushing the U.S. launch first, so Europe is not fully open on our side yet. Let us stay connected and revisit it later."
        ],
        formal: [
          `Hi ${name},\n\nThank you for your interest. At the moment, our current creator rollout is primarily focused on the U.S. market first, so we may not be able to confirm a Europe collaboration yet.\n\nWe would still be happy to stay in touch and revisit a potential partnership once the Europe side is confirmed internally.\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nWe appreciate your message. Our current collaboration stage is mainly U.S.-focused, so Europe is not fully open for this rollout yet. We would still love to keep your contact and reconnect once there is confirmed progress on the Europe side.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Thanks for your interest. We are mainly U.S.-first right now, but we would love to stay in touch for Europe later.",
          "At the moment this rollout is mainly U.S.-focused. Let us keep in touch and revisit Europe when it opens."
        ]
      };
    }

    if (context.stage === "rate_too_high_decline") {
      return {
        casual: [
          "Thanks for being upfront with your pricing. You definitely have a strong presence in the space, and we completely understand your rates. At the moment, a paid campaign at that level is outside of our current budget, so our current model is mainly product exchange + affiliate commission. Hopefully we can revisit a paid opportunity in the future as the brand continues to grow.",
          "Thanks for sharing your rate. We really respect the value of your content. Right now, that fee is a bit outside what we can support for this campaign, so we are mainly moving forward with product exchange and possible affiliate commission partnerships. We would still love to stay connected for future opportunities."
        ],
        formal: [
          `Hi ${name},\n\nThank you for being transparent about your pricing. We appreciate your content quality and understand the value behind your rate.\n\nAt this stage, a paid campaign at that level is outside of our current collaboration budget. Our current partnership model is mainly product exchange, sometimes with affiliate commission depending on fit and performance.\n\nWe would still be happy to stay connected and revisit a potential paid opportunity in the future as the brand continues to grow.\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nThank you for sharing your rate with us. We respect your pricing and the work that goes into your content.\n\nFor this campaign, we may not be able to move forward with a paid collaboration at that level. At the moment, we are mainly focusing on product exchange and affiliate commission partnerships.\n\nWe appreciate your time and would love to keep the door open for future opportunities.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Thanks for sharing your rate. It is outside our current campaign budget, so we are mainly focusing on product exchange + possible affiliate commission right now.",
          "Appreciate the transparency. We cannot move forward with a paid campaign at that level right now, but we would love to stay connected for future opportunities."
        ]
      };
    }

    if (context.stage === "support_or_refund") {
      return {
        casual: [
          "Thanks for reaching out. We want to make sure this is handled accurately. Could you send your order email, a short summary of the issue, and any screenshots or photos that can help us review it properly?",
          "Sorry you are dealing with that. Please send the order email plus any relevant screenshots or photos, and we will make sure the support team can review the case clearly."
        ],
        formal: [
          `Hi ${name},\n\nThank you for reaching out. We would like to make sure this case is reviewed accurately. Could you please send the order email, a short summary of the issue, and any relevant screenshots or photos?\n\nOnce we have those details, the support team can review the case properly.\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nThank you for your message. To help our support team review the issue correctly, please share the order email, a brief explanation of the problem, and any relevant screenshots, photos, or tracking details.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Please send the order email, issue summary, and any screenshots so support can review it properly.",
          "Thanks for reaching out. Send the key details and screenshots, and we will have support review the case."
        ]
      };
    }

    if (context.stage === "confirm_product_exchange") {
      return {
        casual: [
          "Great, we are happy to move forward with a product exchange collaboration. The current plan is usually 2 short vertical videos plus the original raw footage, and we will review the draft before anything goes live. For posting, Instagram should add @varla_adventure as collaborator when possible, and TikTok should tag or mention @varla_sport in the caption.",
          "Awesome, we are good to move forward. We are mainly looking for 2 short videos plus usable raw footage, and we would like to review the drafts before posting. On Instagram, please add @varla_adventure as collaborator when possible, and on TikTok please tag or mention @varla_sport."
        ],
        formal: [
          `Hi ${name},\n\nWe are happy to move forward with a product exchange collaboration. At this stage, the standard content package is usually 2 short vertical videos plus the original usable raw footage for each video.\n\nPlease send drafts for review before posting. For publishing, Instagram posts should add @varla_adventure as collaborator whenever possible, and TikTok posts should tag or mention @varla_sport in the caption.\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nThank you. We are ready to proceed with the product exchange collaboration. The standard deliverables are generally 2 short videos and the related raw footage, and all content should be reviewed before it is posted.\n\nFor platform tagging, please add @varla_adventure as an Instagram collaborator when possible, and please tag or mention @varla_sport on TikTok.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Great, we can move forward. Standard deliverables are usually 2 short videos + raw footage, with draft review before posting.",
          "Happy to proceed. Please plan for 2 short videos, raw footage, draft approval first, plus @varla_adventure on IG and @varla_sport on TikTok."
        ]
      };
    }

    if (context.stage === "send_contract_form") {
      return {
        casual: [
          "Could you please fill out the contract / content requirements form? We will need your shipping details, posting info, and content plan. As a reminder, the usual package is 2 short videos plus raw footage, and posts should go live only after draft approval. Instagram should add @varla_adventure as collaborator when possible, and TikTok should tag or mention @varla_sport.",
          "Please complete the contract / requirements form when you can. It helps us confirm the shipping details and content setup. We usually review drafts before posting, and the normal creator package is 2 short videos plus the original raw footage."
        ],
        formal: [
          `Hi ${name},\n\nCould you please fill out the contract / content requirements form? We will need your shipping details, payment information if applicable, and basic content plan.\n\nAs a reminder, the standard package is usually 2 short vertical videos plus the original usable raw footage. All drafts should be reviewed before posting. Instagram posts should add @varla_adventure as collaborator whenever possible, and TikTok posts should tag or mention @varla_sport in the caption.\n\nBest,\nTeam Member\nVarla Marketing Team`,
          `Hi ${name},\n\nPlease complete the contract / content requirements form when convenient. This will help us finalize the shipping and collaboration details.\n\nFor content execution, we usually request 2 short videos plus raw footage, with draft approval before posting. Please also keep the platform tagging requirements in mind: @varla_adventure on Instagram when possible, and @varla_sport on TikTok.\n\nBest,\nTeam Member\nVarla Marketing Team`
        ],
        short: [
          "Please fill out the contract / requirements form when you can. Standard package is usually 2 videos + raw footage, with draft approval first.",
          "Thanks. Please complete the form, and keep in mind the draft review plus IG @varla_adventure / TikTok @varla_sport tagging rules."
        ]
      };
    }

    if (context.stage !== "creative_direction_script") return null;
    return {
      casual: [
        "Thanks for sharing your approach. That sounds good. Right now, we are mainly focusing on cycling and instructional videos, so we could build the concept around practical riding, safety, and clear product use cases. Since you mentioned building around the brand goals first, that works well for us.",
        "Sure, that direction makes sense. We are currently focusing on cycling and instructional content, and your family/kids-at-home angle could also be interesting if we keep the product benefits clear for both adults and children.",
        "Thanks, I like that approach. Let us first align on the creative direction and key selling points, then you can prepare a script/concept for review before filming.",
        "That works. I also checked the social link you shared, and the data looks pretty good. For the concept, we would prefer practical riding, instructional scenes, and family-friendly use cases rather than only lifestyle shots."
      ],
      formal: [
        `Hi ${name},\n\nThank you for sharing your approach. That sounds good to us. At the moment, we are mainly focusing on cycling and instructional videos, so we would like the content direction to highlight practical riding, clear product benefits, and real-use scenarios.\n\nSince you mentioned preparing a script/concept after we align on the direction, that process works well. Please share the proposed concept for review before filming.\n\nBest,\nTeam Member\nVarla Marketing Team`,
        `Hi ${name},\n\nThanks for the clarification. We agree that the creative direction should be aligned first before moving into the script and filming stage. For this campaign, we would prefer content around cycling, instruction, product use cases, and key selling points that are easy for viewers to understand.\n\nBest,\nTeam Member\nVarla Marketing Team`,
        `Hi ${name},\n\nThank you. I checked the social link you shared, and the data looks promising. For the content direction, we can explore cycling and instructional videos, and possibly include a family-use angle if it naturally fits the product story.\n\nPlease prepare the script/concept for review once we confirm the key selling points.\n\nBest,\nTeam Member\nVarla Marketing Team`,
        `Hi ${name},\n\nThat approach sounds good. Before filming, let us align on the campaign goals, key selling points, and the content angle. We are currently leaning toward practical riding, instructional scenes, and clear product demonstrations.\n\nBest,\nTeam Member\nVarla Marketing Team`
      ],
      short: [
        "Thanks, that works. We are mainly focusing on cycling and instructional videos right now.",
        "Sounds good. Let us align on the key selling points first, then you can prepare the script/concept for review.",
        "I checked the link you shared, and the data looks promising. We can build the content around practical riding and product use cases.",
        "For the direction, we prefer cycling, instructional scenes, and clear product benefits before moving into filming."
      ]
    };
  }

  function safetyCheck(reply, context) {
    const risks = [];
    const lower = reply.toLowerCase();
    if (lower.includes("guarantee") || lower.includes("guaranteed")) risks.push("Avoid guaranteed sponsorship/cooperation.");
    if (lower.includes("free bike") && context.stage !== "confirm_product_exchange") risks.push("Avoid promising a free bike before approval.");
    if (context.stage === "shipping_timeline") risks.push("Use approximate shipping timing only.");
    if (context.stage === "ask_post_private_chat") risks.push("Never approve private chat screenshots.");
    return risks;
  }

  function generateLocalReplies(context) {
    const template = retrieveTemplate(context);
    const base = resolveVariables(template.template, context);
    const groups = [
      { key: "casual", label: "自然", titles: ["自然平衡版", "自然热情版", "自然清晰版", "自然柔和版"] },
      { key: "formal", label: "正式", titles: ["正式标准版", "正式说明版", "正式推进版", "正式跟进版"] },
      { key: "short", label: "简短", titles: ["简短直接版", "简短索要数据", "简短评估版", "简短跟进版"] }
    ];

    return groups.flatMap((group) => [1, 2].map((index) => {
      const reply = makeVariant(base, context, group.key, index);
      return {
        id: `${group.key}-${index}`,
        group: group.label,
        title: group.titles[index - 1],
        reply,
        nextAction: template.nextAction,
        riskNotes: [...new Set([...(template.riskNotes || []), ...safetyCheck(reply, context)])]
      };
    }));
  }

  function buildInternalKnowledge(context) {
    const lines = [
      "Core brand rules:",
      ...INTERNAL_PLAYBOOK.coreRules.map((line) => `- ${line}`),
      "",
      "Deliverables and content direction:",
      ...INTERNAL_PLAYBOOK.deliverables.map((line) => `- ${line}`),
      "",
      "Posting requirements:",
      ...INTERNAL_PLAYBOOK.postingRules.map((line) => `- ${line}`),
      "",
      "Raw footage requirements:",
      ...INTERNAL_PLAYBOOK.rawFootageRules.map((line) => `- ${line}`),
      "",
      "Safety and claim rules:",
      ...INTERNAL_PLAYBOOK.safetyRules.map((line) => `- ${line}`)
    ];
    if (context.product === "M7S") {
      lines.push("", "- For M7S, lean more into performance, power, FPV, and adult-rider positioning.");
    }
    if (context.product === "M5S" || context.product === "Auto") {
      lines.push("", "- For M5S/default first-stage collabs, lean into approachable riding, family/outdoor, first-impression, and practical use cases.");
    }
    return lines.join("\n");
  }

  function buildChatGPTPrompt(context) {
    const template = retrieveTemplate(context);
    const productInfo = PRODUCT_CANON[context.product]
      ? `${context.product}: ${PRODUCT_CANON[context.product].shortIntro} Price reference: ${PRODUCT_CANON[context.product].price}.`
      : "Default brand rule: M5S is the default first-stage collaboration bike. M7S is for stronger creators after approval.";
    return `You are my Varla KOL reply assistant.

Current context:
* Platform: ${context.platform}
* Tone: ${context.tone}
* Stage: ${context.stage}
* Product: ${context.product}
* Creator name: ${context.creatorName || "Unknown"}
* Creator email: ${context.creatorEmail || "Unknown"}

Creator message / conversation:
"""
${context.conversationText}
"""

Relevant local template:
"""
${resolveVariables(template.template, context)}
"""

Product canon:
"""
${productInfo}
"""

Internal playbook:
"""
${buildInternalKnowledge(context)}
"""

Rules:
1. Instagram, TikTok, and Meta Business Suite replies should be short, natural, and human.
2. Gmail replies should be professional, clear, and structured.
3. Product exchange is the default first collaboration model.
4. M5S is the default first-stage collaboration bike. M7S should only be offered to stronger creators after approval.
5. Never promise sponsorship, free bikes, paid collaboration, guaranteed cooperation, or immediate shipment unless Team Member explicitly confirms it.
6. Never say reaching a follower count automatically guarantees sponsorship.
7. Never approve posting private brand conversations or screenshots.
8. Never invent product specs.
9. Never promise a specific shipping date unless provided in the context.
10. Europe and non-US rollout should stay cautious unless internally confirmed.
11. If you mention content requirements, keep them aligned with the internal playbook: 2 short videos + raw footage, draft approval first, correct collaborator/tag handles, and safe accurate claims.

Please generate 6 reply options grouped like this:

Natural:
1. Natural option A
2. Natural option B

Formal:
1. Formal option A
2. Formal option B

Short:
1. Short option A
2. Short option B`;
  }

  function toast(message) {
    const toastEl = shadow.getElementById("toast");
    toastEl.textContent = message;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 1500);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  async function loadTesseract() {
    if (!tesseractModulePromise) {
      tesseractModulePromise = import(chrome.runtime.getURL("vendor/tesseract.js/dist/tesseract.esm.min.js")).then((module) => {
        const api = module?.default || module;
        if (typeof api?.recognize === "function") return api;
        if (typeof module?.recognize === "function") return module;
        throw new Error("Tesseract module loaded, but recognize() is unavailable");
      });
    }
    return tesseractModulePromise;
  }

  function appendConversationText(text) {
    const box = shadow.getElementById("conversation");
    const cleaned = String(text || "").replace(/\n{3,}/g, "\n\n").trim();
    if (!cleaned) return;
    box.value = box.value.trim() ? `${box.value.trim()}\n\n[OCR]\n${cleaned}` : cleaned;
  }

  async function recognizeImage(file) {
    const status = shadow.getElementById("ocrStatus");
    try {
      status.textContent = "OCR识别中，请稍等...";
      const tesseractApi = await loadTesseract();
      const result = await tesseractApi.recognize(file, "eng", {
        workerPath: chrome.runtime.getURL("vendor/tesseract.js/dist/worker.min.js"),
        corePath: chrome.runtime.getURL("vendor/tesseract-core/tesseract-core-simd-lstm.wasm.js"),
        langPath: chrome.runtime.getURL("vendor/tessdata/"),
        workerBlobURL: true,
        gzip: false,
        logger: (message) => {
          if (message.status) {
            const progress = message.progress ? ` ${Math.round(message.progress * 100)}%` : "";
            status.textContent = `OCR: ${message.status}${progress}`;
          }
        }
      });
      appendConversationText(result?.data?.text || "");
      status.textContent = "OCR完成，文字已加入对话框。";
      const context = collectContext();
      shadow.getElementById("stage").value = context.auto.detectedStage;
      renderReplies(generateLocalReplies(collectContext()));
      toast("截图文字已识别");
    } catch (error) {
      status.textContent = `OCR失败：${error?.message || "请确认截图清晰，或改用拖拽上传。"}`;
      console.warn("Varla OCR failed", error);
    }
  }

  function handlePaste(event) {
    const items = [...(event.clipboardData?.items || [])];
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem) {
      shadow.getElementById("ocrStatus").textContent = "未检测到截图图片。请先复制截图，再点这里按 Ctrl+V。";
      return;
    }
    const file = imageItem.getAsFile();
    if (!file) {
      shadow.getElementById("ocrStatus").textContent = "截图读取失败，请重试复制截图，或拖拽图片到这里。";
      return;
    }
    event.preventDefault();
    recognizeImage(file);
  }

  async function readClipboardImage() {
    const status = shadow.getElementById("ocrStatus");
    try {
      status.textContent = "正在读取剪贴板截图...";
      const items = await navigator.clipboard.read();
      for (const item of items) {
        const imageType = item.types.find((type) => type.startsWith("image/"));
        if (!imageType) continue;
        const blob = await item.getType(imageType);
        const file = new File([blob], `clipboard-${Date.now()}.png`, { type: imageType });
        await recognizeImage(file);
        return;
      }
      status.textContent = "剪贴板里没有截图。请先复制截图，再点这里按 Ctrl+V，或点按钮重新读取。";
    } catch (error) {
      status.textContent = `读取剪贴板失败：${error?.message || "请改用 Ctrl+V 或拖拽截图。"}`;
      console.warn("Varla clipboard read failed", error);
    }
  }

  function setDropzoneActive(active) {
    ocrDropActive = active;
    shadow.getElementById("ocrDropzone")?.classList.toggle("active", active);
  }

  function handleDropzoneDragOver(event) {
    event.preventDefault();
    setDropzoneActive(true);
  }

  function handleDropzoneDragLeave(event) {
    event.preventDefault();
    const zone = shadow.getElementById("ocrDropzone");
    if (zone && !zone.contains(event.relatedTarget)) setDropzoneActive(false);
  }

  function handleDropzoneDrop(event) {
    event.preventDefault();
    setDropzoneActive(false);
    const files = [...(event.dataTransfer?.files || [])];
    const image = files.find((file) => file.type.startsWith("image/"));
    if (!image) {
      shadow.getElementById("ocrStatus").textContent = "未检测到图片文件，请拖拽截图图片。";
      return;
    }
    recognizeImage(image);
  }

  function handleOcrFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    recognizeImage(file);
    event.target.value = "";
  }

  async function copyOrInsert(text) {
    await copyText(text);
    const result = insertText(text);
    toast(result.ok ? "已插入，仍需你手动发送" : "已复制，请手动粘贴");
  }

  function renderReplies(replies) {
    const output = shadow.getElementById("replyOutput");
    const groups = [...new Set(replies.map((item) => item.group))];
    output.innerHTML = `
      <details class="reply-details" open>
        <summary>回复结果 · ${replies.length}条</summary>
        ${groups.map((group) => {
          const groupReplies = replies.filter((item) => item.group === group);
          return `
          <section class="reply-section">
            <h2 class="reply-group-title">${group} · ${groupReplies.length}条</h2>
            ${groupReplies.map((item) => `
            <article class="reply-card">
              <div class="reply-head">
                <strong>${item.title}</strong>
                <div class="reply-actions">
                  <button class="mini secondary" data-copy="${item.id}">Copy</button>
                  <button class="mini" data-insert="${item.id}">Insert</button>
                </div>
              </div>
              <textarea id="reply-${item.id}">${item.reply}</textarea>
              <p class="next"><b>Next:</b> ${item.nextAction || "Manual review"}</p>
              <p class="risk">${item.riskNotes.length ? item.riskNotes.join(" | ") : "No obvious risk flagged."}</p>
            </article>
            `).join("")}
          </section>
          `;
        }).join("")}
      </details>
    `;

    replies.forEach((item) => {
      shadow.querySelector(`[data-copy="${item.id}"]`).addEventListener("click", async () => {
        await copyText(shadow.getElementById(`reply-${item.id}`).value);
        toast("已复制回复");
      });
      shadow.querySelector(`[data-insert="${item.id}"]`).addEventListener("click", () => {
        copyOrInsert(shadow.getElementById(`reply-${item.id}`).value);
      });
    });
  }

  function setExpanded(expanded) {
    if (expanded) {
      const rect = root.getBoundingClientRect();
      const left = clamp(rect.left, 4, window.innerWidth - 382);
      const top = clamp(rect.top, 4, window.innerHeight - 120);
      root.style.left = `${left}px`;
      root.style.top = `${top}px`;
      root.style.right = "auto";
    }
    root.classList.toggle("varla-expanded", expanded);
    root.classList.toggle("varla-collapsed", !expanded);
  }

  function toggleWidget() {
    setExpanded(!root.classList.contains("varla-expanded"));
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function saveWidgetPosition(left, top) {
    chrome.storage.local.set({ varlaWidgetPosition: { left, top } });
  }

  function applyWidgetPosition(position) {
    if (!position) return;
    const left = clamp(position.left, 4, window.innerWidth - 58);
    const top = clamp(position.top, 4, window.innerHeight - 58);
    root.style.left = `${left}px`;
    root.style.top = `${top}px`;
    root.style.right = "auto";
  }

  function cleanupPendingDrag() {
    if (!pendingDragState) return;
    if (pendingDragState.timer) clearTimeout(pendingDragState.timer);
    window.removeEventListener("pointermove", handlePendingDragMove, true);
    window.removeEventListener("pointerup", handlePendingDragEnd, true);
    window.removeEventListener("pointercancel", handlePendingDragEnd, true);
    window.removeEventListener("blur", handlePendingDragEnd, true);
    pendingDragState = null;
  }

  function beginActiveDrag(pending, event) {
    if (root.classList.contains("varla-expanded")) return;
    cleanupPendingDrag();
    event.preventDefault();
    dragLauncher = pending.launcher;
    dragState = {
      pointerId: pending.pointerId,
      startX: pending.startX,
      startY: pending.startY,
      left: pending.left,
      top: pending.top,
      activated: true,
      moved: false
    };
    if (dragLauncher?.setPointerCapture) {
      try {
        dragLauncher.setPointerCapture(pending.pointerId);
      } catch {}
    }
    root.classList.add("varla-dragging");
    window.addEventListener("pointermove", moveDrag, true);
    window.addEventListener("pointerup", endDrag, true);
    window.addEventListener("pointercancel", endDrag, true);
    window.addEventListener("blur", endDrag, true);
    moveDrag(event);
  }

  function startDrag(event) {
    if (root.classList.contains("varla-expanded")) return;
    cleanupPendingDrag();
    const rect = root.getBoundingClientRect();
    pendingDragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: rect.left,
      top: rect.top,
      launcher: event.currentTarget,
      timer: setTimeout(() => {
        if (!pendingDragState || pendingDragState.pointerId !== event.pointerId) return;
        beginActiveDrag(pendingDragState, {
          pointerId: pendingDragState.pointerId,
          clientX: pendingDragState.startX,
          clientY: pendingDragState.startY,
          buttons: 1,
          preventDefault() {}
        });
      }, DRAG_HOLD_DELAY)
    };
    window.addEventListener("pointermove", handlePendingDragMove, true);
    window.addEventListener("pointerup", handlePendingDragEnd, true);
    window.addEventListener("pointercancel", handlePendingDragEnd, true);
    window.addEventListener("blur", handlePendingDragEnd, true);
  }

  function handlePendingDragMove(event) {
    if (!pendingDragState) return;
    if (event.pointerId !== pendingDragState.pointerId) return;
    if (event.buttons === 0) {
      cleanupPendingDrag();
      return;
    }
    const dx = event.clientX - pendingDragState.startX;
    const dy = event.clientY - pendingDragState.startY;
    if (Math.abs(dx) + Math.abs(dy) >= DRAG_MOVE_THRESHOLD) {
      beginActiveDrag(pendingDragState, event);
    }
  }

  function handlePendingDragEnd(event) {
    if (!pendingDragState) return;
    if (event?.pointerId != null && event.pointerId !== pendingDragState.pointerId) return;
    cleanupPendingDrag();
  }

  function moveDrag(event) {
    if (!dragState) return;
    if (event.pointerId !== dragState.pointerId) return;
    if (event.buttons === 0) {
      endDrag(event);
      return;
    }
    const dx = event.clientX - dragState.startX;
    const dy = event.clientY - dragState.startY;
    if (Math.abs(dx) + Math.abs(dy) >= DRAG_MOVE_THRESHOLD) dragState.moved = true;
    const left = clamp(dragState.left + dx, 4, window.innerWidth - 58);
    const top = clamp(dragState.top + dy, 4, window.innerHeight - 58);
    root.style.left = `${left}px`;
    root.style.top = `${top}px`;
    root.style.right = "auto";
  }

  function endDrag(event) {
    if (!dragState) return;
    if (event?.pointerId != null && event.pointerId !== dragState.pointerId) return;
    const rect = root.getBoundingClientRect();
    saveWidgetPosition(rect.left, rect.top);
    if (dragState.activated || dragState.moved) {
      root.dataset.justDragged = "1";
      setTimeout(() => delete root.dataset.justDragged, 180);
    }
    root.classList.remove("varla-dragging");
    if (dragLauncher?.releasePointerCapture) {
      try {
        dragLauncher.releasePointerCapture(dragState.pointerId);
      } catch {}
    }
    dragLauncher = null;
    dragState = null;
    window.removeEventListener("pointermove", moveDrag, true);
    window.removeEventListener("pointerup", endDrag, true);
    window.removeEventListener("pointercancel", endDrag, true);
    window.removeEventListener("blur", endDrag, true);
  }

  function readSelectionIntoPanel() {
    const selection = getSelectionText();
    if (selection) shadow.getElementById("conversation").value = selection;
    selectValue("platform", detectPlatform());
    const context = collectContext();
    shadow.getElementById("stage").value = context.auto.detectedStage;
    toast(selection ? "已读取选中文本" : "没有选中文本，可手动粘贴");
  }

  function render() {
    root = document.createElement("div");
    root.id = "varla-kol-reply-root";
    root.className = "varla-collapsed";
    shadow = root.attachShadow({ mode: "open" });
    document.documentElement.appendChild(root);

    shadow.innerHTML = `
      <style>
        :host {
          all: initial;
          position: fixed;
          right: 12px;
          top: 84px;
          z-index: 2147483647;
          font-family: Arial, "Microsoft YaHei", sans-serif;
          color: #172033;
          pointer-events: none;
        }
        * { box-sizing: border-box; }
        .launcher {
          position: absolute;
          right: 0;
          top: 0;
          width: 46px;
          height: 46px;
          border: 0;
          border-radius: 14px;
          background: #2563eb;
          color: white;
          font-weight: 900;
          font-size: 12px;
          box-shadow: 0 8px 24px rgba(37, 99, 235, .28);
          cursor: pointer;
          transition: transform .2s ease, opacity .2s ease;
          pointer-events: auto;
        }
        .launcher:hover {
          transform: translateX(-2px) scale(1.03);
        }
        :host(.varla-dragging) .launcher {
          cursor: grabbing;
        }
        .shell {
          width: 364px;
          max-height: calc(100vh - 110px);
          overflow: auto;
          background: #f7f9fd;
          border: 1px solid #d9e2f0;
          border-radius: 10px;
          box-shadow: 0 12px 34px rgba(17, 24, 39, .22);
          transform: translateX(394px) scale(.98);
          opacity: 0;
          pointer-events: none;
          transition: transform .24s ease, opacity .2s ease;
        }
        :host(.varla-expanded) .shell {
          transform: translateX(0) scale(1);
          opacity: 1;
          pointer-events: auto;
        }
        :host(.varla-expanded) .launcher {
          transform: translateX(56px) scale(.85);
          opacity: .2;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: start;
          gap: 8px;
          padding: 12px 12px 8px;
          background: #fff;
          border-bottom: 1px solid #e3e9f4;
          position: sticky;
          top: 0;
          z-index: 2;
        }
        .brand { margin: 0; color: #667085; font-size: 12px; font-weight: 800; }
        h1 { margin: 2px 0 0; font-size: 17px; letter-spacing: 0; color: #111827; }
        .close {
          border: 0;
          background: transparent;
          color: #667085;
          font-size: 22px;
          line-height: 1;
          cursor: pointer;
        }
        .body { padding: 10px; }
        .row, .grid2, .actions { display: grid; gap: 8px; }
        .row { grid-template-columns: repeat(5, 1fr); }
        .grid2 { grid-template-columns: 1fr 1fr; }
        .actions { grid-template-columns: .8fr 1.2fr; margin-top: 8px; }
        button {
          border: 0;
          border-radius: 8px;
          padding: 9px 10px;
          background: #2563eb;
          color: white;
          font-weight: 900;
          cursor: pointer;
          font-size: 13px;
        }
        button.secondary, .pill {
          background: #e9eef6;
          color: #111827;
          border: 1px solid #d7dfeb;
        }
        .pill { padding: 8px 5px; font-size: 12px; white-space: nowrap; }
        .pill.active {
          background: #e8f1ff;
          border-color: #9cc1ff;
          color: #1557c0;
          box-shadow: inset 0 0 0 1px #9cc1ff;
        }
        label, .choice-title {
          display: block;
          margin: 8px 0 5px;
          color: #667085;
          font-size: 12px;
          font-weight: 900;
        }
        textarea, input, select {
          width: 100%;
          border: 1px solid #d7dfeb;
          border-radius: 8px;
          padding: 9px;
          font: 13px/1.45 Arial, "Microsoft YaHei", sans-serif;
          color: #172033;
          background: white;
        }
        #conversation { min-height: 118px; resize: vertical; }
        select { height: 38px; }
        .tone-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .product-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .helper { margin: 8px 0 0; color: #667085; font-size: 12px; line-height: 1.35; }
        .ocr-box {
          margin-top: 8px;
          padding: 10px;
          border: 1px dashed #9cc1ff;
          border-radius: 8px;
          background: #f3f7ff;
          color: #1557c0;
          font-size: 12px;
          line-height: 1.35;
        }
        .ocr-box.active,
        .ocr-box:focus-within,
        .ocr-dropzone:focus {
          border-color: #2f6feb;
          box-shadow: 0 0 0 2px rgba(47, 111, 235, 0.14);
        }
        .ocr-actions {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-top: 8px;
        }
        .ocr-dropzone {
          margin-top: 8px;
          min-height: 72px;
          border: 1px dashed #9cc1ff;
          border-radius: 8px;
          background: white;
          padding: 10px;
          color: #3b4a67;
          outline: none;
          cursor: text;
          display: flex;
          align-items: center;
          line-height: 1.5;
        }
        .ocr-dropzone strong {
          color: #1557c0;
        }
        .ocr-dropzone.active {
          background: #edf4ff;
        }
        .ocr-file {
          display: none;
        }
        .reply-stack { display: grid; gap: 9px; margin-top: 10px; }
        .reply-details {
          margin-top: 8px;
          background: white;
          border: 1px solid #d9e2f0;
          border-radius: 9px;
          padding: 0;
          overflow: hidden;
        }
        .reply-details > summary {
          cursor: pointer;
          padding: 10px;
          background: #e8f1ff;
          color: #1557c0;
          font-weight: 900;
          font-size: 14px;
          letter-spacing: 0;
        }
        .reply-details[open] > summary {
          border-bottom: 1px solid #d9e2f0;
        }
        .reply-section {
          padding: 8px 10px 2px;
        }
        .reply-group-title {
          margin: 4px 0 8px;
          color: #1557c0;
          font-size: 14px;
          font-weight: 900;
          letter-spacing: 0;
        }
        .reply-card {
          background: white;
          border: 1px solid #edf1f7;
          border-radius: 8px;
          padding: 10px;
          margin-bottom: 8px;
        }
        .reply-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          margin-bottom: 7px;
        }
        .reply-head strong { font-size: 13px; }
        .reply-actions { display: flex; gap: 6px; }
        .mini { padding: 6px 8px; font-size: 12px; }
        .reply-card textarea { min-height: 118px; resize: vertical; }
        .next { margin: 7px 0 0; color: #667085; font-size: 12px; line-height: 1.35; }
        .risk {
          margin: 6px 0 0;
          padding: 7px;
          border-radius: 7px;
          background: #fff5d7;
          color: #805300;
          font-size: 12px;
          line-height: 1.35;
        }
        details:not(.reply-details) {
          margin-top: 10px;
          background: white;
          border: 1px solid #d9e2f0;
          border-radius: 9px;
          padding: 9px;
        }
        details:not(.reply-details) > summary { cursor: pointer; font-weight: 900; font-size: 13px; }
        #promptPreview { min-height: 170px; margin-top: 8px; }
        .toast {
          position: fixed;
          right: 14px;
          bottom: 14px;
          opacity: 0;
          transform: translateY(8px);
          background: #172033;
          color: white;
          border-radius: 8px;
          padding: 9px 12px;
          font: 13px Arial, "Microsoft YaHei", sans-serif;
          transition: .18s ease;
          pointer-events: none;
        }
        .toast.show { opacity: 1; transform: translateY(0); }
      </style>
      <button class="launcher" id="launcher" title="打开 Varla KOL 回复器">KOL</button>
      <section class="shell">
        <header class="header">
          <div>
            <p class="brand">Varla回复</p>
            <h1>KOL Reply Assistant</h1>
          </div>
          <button class="close" id="close" title="收起">×</button>
        </header>
        <div class="body">
          <div class="row">
            <button class="pill" data-target="platform" data-value="unknown">Unknown</button>
            <button class="pill" data-target="platform" data-value="instagram">Ins</button>
            <button class="pill" data-target="platform" data-value="tiktok">TikTok</button>
            <button class="pill" data-target="platform" data-value="meta_business">Meta</button>
            <button class="pill" data-target="platform" data-value="gmail">Gmail</button>
          </div>
          <input id="platform" type="hidden" value="unknown" />

          <textarea id="conversation" placeholder="选中网页文字后点读取，或把 KOL 消息粘贴到这里"></textarea>
          <div class="grid2">
            <label>Creator <input id="creatorName" placeholder="optional"></label>
            <label>Email <input id="creatorEmail" placeholder="auto detect"></label>
          </div>
          <label>Stage <select id="stage"></select></label>

          <div class="choice-title">Tone</div>
          <div class="tone-row">
            <button class="pill" data-target="tone" data-value="casual">自然</button>
            <button class="pill" data-target="tone" data-value="formal">正式</button>
            <button class="pill" data-target="tone" data-value="short">简短</button>
          </div>
          <input id="tone" type="hidden" value="casual" />

          <div class="choice-title">Product</div>
          <div class="product-row">
            <button class="pill" data-target="product" data-value="Auto">Auto</button>
            <button class="pill" data-target="product" data-value="M5S">M5S</button>
            <button class="pill" data-target="product" data-value="M7S">M7S</button>
            <button class="pill" data-target="product" data-value="Other">Other</button>
          </div>
          <input id="product" type="hidden" value="Auto" />

          <div class="actions">
            <button class="secondary" id="readBtn">读取</button>
            <button id="generateBtn">生成 6 条回复</button>
          </div>
          <p id="detectedMeta" class="helper">检测服务中，可选中文本后点读取。</p>
          <div class="ocr-box" id="ocrPanel">
            <div id="ocrStatus">OCR：点击下方识别框后，可直接 Ctrl+V 粘贴截图。</div>
            <div
              class="ocr-dropzone"
              id="ocrDropzone"
              tabindex="0"
              role="button"
              aria-label="OCR 截图识别框"
              title="点击这里后按 Ctrl+V，或拖拽截图到这里"
            ><span><strong>截图识别区</strong><br>复制截图后，先点这里，再按 Ctrl+V。也支持拖拽图片到此处。</span></div>
            <div class="ocr-actions">
              <button class="secondary" id="readClipboardBtn">读取剪贴板截图</button>
              <button class="secondary" id="pickImageBtn">选择图片文件</button>
            </div>
            <input class="ocr-file" id="ocrFileInput" type="file" accept="image/*" />
          </div>

          <div id="replyOutput" class="reply-stack"></div>

          <details>
            <summary>ChatGPT Bridge</summary>
            <button class="secondary" id="promptBtn" style="width:100%;margin-top:8px;">生成 Prompt</button>
            <textarea id="promptPreview" placeholder="Prompt preview"></textarea>
            <button class="secondary" id="copyPromptBtn" style="width:100%;margin-top:8px;">复制 Prompt</button>
          </details>
        </div>
      </section>
      <div id="toast" class="toast"></div>
    `;

    shadow.getElementById("stage").innerHTML = STAGE_RULES.map((rule) => `<option value="${rule.id}">${rule.label}</option>`).join("");
    shadow.querySelectorAll(".pill").forEach((button) => {
      button.addEventListener("click", () => selectValue(button.dataset.target, button.dataset.value));
    });
    shadow.getElementById("launcher").addEventListener("pointerdown", startDrag);
    shadow.getElementById("launcher").addEventListener("click", () => {
      if (root.dataset.justDragged === "1") return;
      toggleWidget();
    });
    shadow.getElementById("close").addEventListener("click", () => setExpanded(false));
    shadow.getElementById("readBtn").addEventListener("click", readSelectionIntoPanel);
    const ocrDropzone = shadow.getElementById("ocrDropzone");
    const ocrFileInput = shadow.getElementById("ocrFileInput");
    ocrDropzone.addEventListener("click", () => {
      ocrDropzone.focus();
      shadow.getElementById("ocrStatus").textContent = "识别框已激活。现在直接按 Ctrl+V 粘贴截图。";
    });
    ocrDropzone.addEventListener("paste", handlePaste);
    ocrDropzone.addEventListener("dragover", handleDropzoneDragOver);
    ocrDropzone.addEventListener("dragleave", handleDropzoneDragLeave);
    ocrDropzone.addEventListener("drop", handleDropzoneDrop);
    shadow.getElementById("readClipboardBtn").addEventListener("click", readClipboardImage);
    shadow.getElementById("pickImageBtn").addEventListener("click", () => ocrFileInput.click());
    ocrFileInput.addEventListener("change", handleOcrFileChange);
    shadow.getElementById("generateBtn").addEventListener("click", () => renderReplies(generateLocalReplies(collectContext())));
    shadow.getElementById("promptBtn").addEventListener("click", () => {
      shadow.getElementById("promptPreview").value = buildChatGPTPrompt(collectContext());
      toast("Prompt 已生成");
    });
    shadow.getElementById("copyPromptBtn").addEventListener("click", async () => {
      const prompt = shadow.getElementById("promptPreview").value || buildChatGPTPrompt(collectContext());
      await copyText(prompt);
      toast("Prompt 已复制");
    });

    selectValue("platform", detectPlatform());
    selectValue("tone", "casual");
    selectValue("product", "Auto");
  }

  chrome.storage.local.get(["varlaSettings", "varlaWidgetPosition"], (stored) => {
    settings = { ...DEFAULT_SETTINGS, ...(stored.varlaSettings || {}) };
    applyWidgetPosition(stored.varlaWidgetPosition);
  });

  render();

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "READ_CONTEXT") {
      sendResponse({
        selectionText: getSelectionText(),
        url: location.href,
        title: document.title
      });
      return;
    }

    if (message.type === "INSERT_REPLY") {
      sendResponse(insertText(message.text || ""));
      return;
    }

    if (message.type === "TOGGLE_WIDGET") {
      toggleWidget();
      sendResponse({ ok: true });
    }
  });
})();
