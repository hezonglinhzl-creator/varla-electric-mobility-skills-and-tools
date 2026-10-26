const stageRules = [
  { id: "initial_outreach", label: "Initial outreach", keywords: ["collaboration", "collab", "work with you", "partnership"], nextAction: "Introduce Varla and ask if they are interested" },
  { id: "interested_reply", label: "Creator is interested", keywords: ["i would love", "i'm interested", "im interested", "interested", "negotiate a deal", "sounds good", "i'd love", "yes"], nextAction: "Ask for social links and analytics" },
  { id: "ask_sponsorship", label: "Creator asks for sponsorship", keywords: ["sponsorship", "sponsor me", "sponsor", "free bike", "give me a bike", "can i get"], nextAction: "Ask for social links and basic analytics" },
  { id: "low_followers", label: "Low followers or follower target", keywords: ["followers", "3k", "5k", "10k", "when i reach", "if i get", "when i hit"], nextAction: "Encourage and explain full review criteria" },
  { id: "ask_post_private_chat", label: "Private chat screenshot", keywords: ["post this chat", "post that", "screenshot", "screen shot", "share this conversation", "private chat"], nextAction: "Decline posting private brand conversation" },
  { id: "ask_ai_video", label: "AI video question", keywords: ["ai generated", "ai video", "why do you post ai", "fake video", "real product"], nextAction: "Explain AI concept videos and real product content" },
  { id: "provide_email", label: "Creator provides email", keywords: ["@", "email", "gmail.com", "outlook.com", "hotmail.com", "send me"], nextAction: "Confirm receipt and send details by email" },
  { id: "email_bounced", label: "Email bounced", keywords: ["bounce", "bounced", "undelivered", "delivery failed", "address not found", "mail delivery"], nextAction: "Ask creator to confirm email address" },
  { id: "ask_partnership_details", label: "Partnership details", keywords: ["details", "how does it work", "requirements", "what do i need", "tell me more", "partnership details"], nextAction: "Explain product exchange and ask for analytics" },
  { id: "provide_analytics", label: "Creator provides analytics", keywords: ["average views", "engagement", "audience", "top countries", "demographics", "analytics", "insights"], nextAction: "Review fit and decide structure" },
  { id: "ask_paid_collab", label: "Paid collaboration", keywords: ["paid collaboration", "paid collab", "rate", "rates", "fee", "payment", "budget", "how much do you pay"], nextAction: "Steer toward product exchange or commission" },
  { id: "ask_second_bike", label: "Second bike request", keywords: ["second bike", "another bike", "cameraman", "photographer", "my friend", "two bikes"], nextAction: "Focus on first collaboration first" },
  { id: "confirm_product_exchange", label: "Confirm product exchange", keywords: ["product exchange", "we can move forward", "confirm exchange", "send the product", "requirements form"], nextAction: "Move to form or contract stage" },
  { id: "confirm_exchange_commission", label: "Exchange + commission", keywords: ["8%", "commission", "discount code", "shopify code", "affiliate"], nextAction: "Collect payment method and form details" },
  { id: "send_contract_form", label: "Send contract / form", keywords: ["contract", "agreement", "requirements form", "shipping address", "payment method"], nextAction: "Ask creator to fill the form" },
  { id: "signed_contract_received", label: "Signed contract received", keywords: ["signed", "agreement attached", "completed contract", "i filled", "submitted"], nextAction: "Confirm receipt and review" },
  { id: "shipping_timeline", label: "Shipping timeline", keywords: ["ship", "shipping", "delivery", "when will", "tracking", "arrive", "july"], nextAction: "Give approximate timeline only" },
  { id: "follow_up", label: "Follow up", keywords: ["follow up", "checking in", "any update", "reminder"], nextAction: "Send a short polite follow-up" },
  { id: "reject_or_close", label: "Reject or close", keywords: ["not a fit", "decline", "not interested", "maybe later", "cannot work"], nextAction: "Close politely and keep relationship warm" },
  { id: "unknown", label: "Unknown", keywords: [], nextAction: "Ask a safe clarifying question" }
];

const templates = [
  ["interested_reply", "Awesome, thanks for your interest! Could you send over your social links, average views, and top audience countries? That will help us better understand the right collaboration structure.", "Ask for social links and audience data", ["Do not promise sponsorship or a free bike yet"]],
  ["ask_sponsorship", "Thanks for reaching out! Could you send over your TikTok/Instagram links, average views, and top audience countries? We usually review creator fit, content quality, and audience match before confirming any collaboration.", "Ask for social links and audience data", ["Do not promise sponsorship"]],
  ["low_followers", "Totally understand, and we really appreciate your interest. Just to clarify, sponsorship decisions are not based only on follower count. We also look at content quality, engagement, audience fit, and brand alignment. Keep creating strong content, and we would be happy to review again as your account grows.", "Encourage creator and explain review criteria", ["Never say a follower target guarantees sponsorship"]],
  ["ask_post_private_chat", "Thanks for asking! Please do not post screenshots of private brand conversations, even if the brand name is removed. You are welcome to post about your own content goals and tag us, but please make sure it does not sound like a guaranteed sponsorship or confirmed collaboration.", "Protect private conversation and clarify allowed content", ["Do not approve posting private chat screenshots"]],
  ["ask_ai_video", "We use some AI-assisted concept videos to explore creative ideas and show the vibe of the product faster. The product is real, and we will also be posting more real riding footage, creator content, and customer videos soon.", "Reassure creator that real product content is coming", []],
  ["provide_email", "Thanks! I will send over the details by email. Please keep an eye on your inbox.", "Send details by email", []],
  ["email_bounced", "I tried sending the email, but it looks like the address did not go through. Could you double-check the email address for me?", "Ask creator to confirm email", []],
  ["ask_partnership_details", "Thanks for reaching out. Our current collaboration model is mainly product exchange, and in some cases we may add affiliate commission depending on creator fit, content quality, audience, and performance. Could you share your social links, audience demographics, average views, top audience countries, and any previous campaign data?", "Ask for analytics and campaign data", ["Do not guarantee paid collaboration"]],
  ["ask_paid_collab", "Thanks for sharing. Right now, our main focus is product exchange partnerships, sometimes with affiliate commission depending on creator fit and performance. If the content performs well, we would definitely be open to discussing a longer-term partnership later on.", "Keep door open while steering to exchange or commission", ["Do not say there is no budget"]],
  ["ask_second_bike", "Thanks for sharing the idea. Regarding a second bike for your cameraman, let us focus on getting the first collaboration rolling and seeing how the initial content performs. We can revisit the idea of a second unit once we have some traction with the first collaboration.", "Move forward with the first unit first", ["Do not promise a second bike"]],
  ["confirm_product_exchange", "Great, we are happy to move forward with a product exchange collaboration. We would love to see authentic riding, unboxing, review, and short-form content from you. The next step is to complete the contract / requirements form so we can collect the needed details.", "Send contract or requirements form", ["Only use after Team Member confirms exchange"]],
  ["confirm_exchange_commission", "Thanks for sending over the details and analytics. Everything looks solid. We are happy to move forward with a product exchange + affiliate commission model. We will provide the product, and we can offer an 8% commission on sales generated through your discount code. The default commission period is 3 months.", "Send form and collect payment/shipping details", ["Use only when commission is approved"]],
  ["send_contract_form", "Could you please fill out the contract / content requirements form? We will need your shipping address, preferred payment method or ID, social accounts, planned content format, and expected posting timeline.", "Collect form details", []],
  ["signed_contract_received", "Thanks for sending the signed agreement. We have received it and will review everything on our end. Once everything looks good, we will move forward with the next steps and keep you updated on the shipping schedule.", "Review agreement and prepare next steps", []],
  ["shipping_timeline", "Thanks again for your support. The product is expected to be available around July. We hope to ship it out in July and will keep you updated once the shipping schedule is confirmed.", "Keep creator updated when schedule is confirmed", ["Do not promise a specific shipping date"]],
  ["follow_up", "Hi {{name}}, just wanted to follow up and see if you had a chance to check my last message. Happy to answer any questions.", "Wait for reply", ["Keep it light and non-pushy"]],
  ["reject_or_close", "Thanks so much for your interest and for sharing your information. At this moment, it may not be the best fit for our current campaign, but we really appreciate your support and would be happy to stay connected for future opportunities.", "Close politely and keep relationship warm", ["Do not criticize the creator"]]
].map(([stage, template, nextAction, riskNotes], index) => ({ id: `template_${index + 1}`, stage, template, nextAction, riskNotes }));

const productSpecs = {
  M5S: "Motor: 2600W 48V\nBattery: 48V 27Ah lithium battery\nMax speed: 40 mph\nRange: 25 miles\nSeat height: 710 mm\nLoading capacity: 100 kg",
  M7S: "Motor: 5500W 60V\nBattery: 60V 27Ah lithium battery\nMax speed: 50 mph\nRange: 30 miles\nSeat height: 800 mm\nLoading capacity: 100 kg"
};

const $ = (id) => document.getElementById(id);
let settings = { chatgptUrl: "https://chatgpt.com/", defaultCommission: "8%", commissionValidity: "3 months" };

function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 1500);
}

function cleanText(text) {
  const raw = String(text || "").replace(/\r/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  const emails = [...raw.matchAll(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi)].map((m) => m[0]);
  return { raw, emails: [...new Set(emails)] };
}

function classifyStage(text) {
  const source = String(text || "").toLowerCase();
  let best = stageRules.find((rule) => rule.id === "unknown");
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

function selectValue(targetId, value) {
  $(targetId).value = value;
  document.querySelectorAll(`.pill[data-target="${targetId}"]`).forEach((button) => {
    button.classList.toggle("active", button.dataset.value === value);
  });
}

function detectProduct(text) {
  const selected = $("product").value;
  if (selected !== "Auto") return selected;
  const lower = text.toLowerCase();
  if (lower.includes("m5s")) return "M5S";
  if (lower.includes("m7s")) return "M7S";
  return "Auto";
}

function collectContext() {
  const cleaned = cleanText($("conversation").value);
  const auto = classifyStage(cleaned.raw);
  const context = {
    platform: $("platform").value,
    stage: $("stage").value || auto.detectedStage,
    tone: $("tone").value,
    product: detectProduct(cleaned.raw),
    creatorName: $("creatorName").value.trim(),
    creatorEmail: $("creatorEmail").value.trim() || cleaned.emails[0] || "",
    conversationText: cleaned.raw,
    auto
  };
  $("creatorEmail").value = context.creatorEmail;
  $("detectedMeta").textContent = `Stage: ${auto.detectedStage} | Confidence: ${Math.round(auto.confidence * 100)}% | Keywords: ${auto.matchedKeywords.join(", ") || "none"}`;
  return context;
}

function resolveVariables(text, context) {
  return String(text)
    .replaceAll("{{name}}", context.creatorName || "there")
    .replaceAll("{{commission}}", settings.defaultCommission)
    .replaceAll("{{commissionValidity}}", settings.commissionValidity);
}

function safetyCheck(reply, context) {
  const risks = [];
  const lower = reply.toLowerCase();
  if (lower.includes("guarantee") || lower.includes("guaranteed")) risks.push("Avoid guaranteed cooperation or sponsorship language.");
  if (lower.includes("free bike") && context.stage !== "confirm_product_exchange") risks.push("Avoid promising a free bike before approval.");
  if (context.stage === "shipping_timeline") risks.push("Use approximate shipping timing only.");
  if (context.stage === "ask_post_private_chat") risks.push("Never approve private chat screenshots.");
  return risks;
}

function retrieveTemplate(context) {
  return templates.find((item) => item.stage === context.stage) || templates[0];
}

function makeVariant(base, context, index) {
  const name = context.creatorName || "there";
  const prefix = context.platform === "gmail" ? `Hey ${name},\n\n` : "";
  const suffixes = [
    "",
    context.platform === "gmail" ? "\n\nBest,\nTeam Member\nVarla Marketing Team" : "",
    "\n\nThis will help us review the best next step.",
    context.platform === "gmail" ? "\n\nNo rush. Please send whatever information you have available.\n\nBest,\nTeam Member\nVarla Marketing Team" : "\n\nNo rush, just send what you have."
  ];
  if (index === 1) return `${prefix}${base}${suffixes[1]}`.trim();
  if (index === 2) return `${prefix}${base.replace(/^Thanks/, "Thanks so much")}${suffixes[2]}`.trim();
  if (index === 3) return `${base}${context.product !== "Auto" ? `\n\nFor this campaign, we are reviewing fit around the ${context.product}.` : ""}`.trim();
  return `${prefix}${base}${suffixes[3]}`.trim();
}

function generateLocalReplies(context) {
  const template = retrieveTemplate(context);
  const base = resolveVariables(template.template, context);
  return [1, 2, 3, 4].map((index) => {
    const reply = makeVariant(base, context, index);
    return {
      id: index,
      title: ["Balanced", "Warmer", "Direct", "Soft follow-up"][index - 1],
      reply,
      nextAction: template.nextAction,
      riskNotes: [...new Set([...(template.riskNotes || []), ...safetyCheck(reply, context)])]
    };
  });
}

function buildChatGPTPrompt(context) {
  const template = retrieveTemplate(context);
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

Relevant product specs:
"""
${productSpecs[context.product] || "No confirmed product specs selected. Do not invent specs."}
"""

Brand context:
Varla is currently focusing on product exchange partnerships. In some cases, Varla may add affiliate commission depending on creator fit, content quality, audience, engagement, and performance.

Rules:
1. Instagram, TikTok, and Meta Business Suite replies should be short, natural, and human.
2. Gmail replies should be professional, clear, and structured.
3. Never promise sponsorship, free bikes, paid collaboration, or guaranteed cooperation unless Team Member explicitly confirms it.
4. Never say reaching a follower count automatically guarantees sponsorship.
5. Never approve posting private brand conversations or screenshots.
6. Never invent product specs.
7. Never promise a specific shipping date unless provided in the context.

Please generate 4 reply options:
1. Short casual version
2. Warm professional version
3. More direct version
4. Softer relationship-building version

For each option, include Reply, Why this works, Next action, and Risk notes.`;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function readPageContext() {
  const tab = await getActiveTab();
  if (!tab?.id) return;
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { type: "READ_CONTEXT" });
    if (response?.selectionText) $("conversation").value = response.selectionText;
    if (response?.url?.includes("instagram.com")) selectValue("platform", "instagram");
    else if (response?.url?.includes("tiktok.com")) selectValue("platform", "tiktok");
    else if (response?.url?.includes("business.facebook.com")) selectValue("platform", "meta_business");
    else if (response?.url?.includes("mail.google.com") || response?.url?.includes("gmail.com")) selectValue("platform", "gmail");
    const context = collectContext();
    $("stage").value = context.auto.detectedStage;
    toast(response?.selectionText ? "Read selected text." : "No selected text found.");
  } catch {
    toast("Refresh the page once, then try Read again.");
  }
}

async function insertReply(text) {
  await navigator.clipboard.writeText(text);
  const tab = await getActiveTab();
  if (!tab?.id) {
    toast("Copied reply.");
    return;
  }
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { type: "INSERT_REPLY", text });
    toast(response?.ok ? "Inserted reply. Please send manually." : "Copied reply. Paste manually.");
  } catch {
    toast("Copied reply. Paste manually.");
  }
}

function renderReplies(replies) {
  $("replyOutput").innerHTML = replies.map((item) => `
    <article class="reply-card">
      <div class="reply-head">
        <strong>${item.id}. ${item.title}</strong>
        <div class="reply-actions">
          <button class="secondary" data-copy="${item.id}">Copy</button>
          <button data-insert="${item.id}">Insert</button>
        </div>
      </div>
      <textarea id="reply-${item.id}">${item.reply}</textarea>
      <div class="next"><b>Next:</b> ${item.nextAction || "Manual review"}</div>
      <div class="risk">${item.riskNotes.length ? item.riskNotes.join(" | ") : "No obvious risk flagged."}</div>
    </article>
  `).join("");

  replies.forEach((item) => {
    document.querySelector(`[data-copy="${item.id}"]`).addEventListener("click", async () => {
      await navigator.clipboard.writeText($(`reply-${item.id}`).value);
      toast("Copied reply.");
    });
    document.querySelector(`[data-insert="${item.id}"]`).addEventListener("click", () => insertReply($(`reply-${item.id}`).value));
  });
}

function renderStages() {
  $("stage").innerHTML = stageRules.map((rule) => `<option value="${rule.id}">${rule.label}</option>`).join("");
}

async function loadSettings() {
  const stored = await chrome.storage.local.get("varlaSettings");
  settings = { ...settings, ...(stored.varlaSettings || {}) };
  $("chatgptUrl").value = settings.chatgptUrl;
  $("commission").value = settings.defaultCommission;
  $("commissionValidity").value = settings.commissionValidity;
}

async function saveSettings() {
  settings.chatgptUrl = $("chatgptUrl").value || "https://chatgpt.com/";
  settings.defaultCommission = $("commission").value || "8%";
  settings.commissionValidity = $("commissionValidity").value || "3 months";
  await chrome.storage.local.set({ varlaSettings: settings });
  toast("Settings saved.");
}

function bindEvents() {
  document.querySelectorAll(".pill").forEach((button) => {
    button.addEventListener("click", () => selectValue(button.dataset.target, button.dataset.value));
  });
  $("readPage").addEventListener("click", readPageContext);
  $("detectStage").addEventListener("click", () => {
    const context = collectContext();
    $("stage").value = context.auto.detectedStage;
    selectValue("product", context.product);
    toast("Detected.");
  });
  $("generateReplies").addEventListener("click", () => renderReplies(generateLocalReplies(collectContext())));
  $("generatePrompt").addEventListener("click", () => {
    $("promptPreview").value = buildChatGPTPrompt(collectContext());
    toast("Prompt generated.");
  });
  $("copyPrompt").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("promptPreview").value || buildChatGPTPrompt(collectContext()));
    toast("Copied prompt.");
  });
  $("openChatGPT").addEventListener("click", () => chrome.tabs.create({ url: settings.chatgptUrl || "https://chatgpt.com/" }));
  $("saveSettings").addEventListener("click", saveSettings);
}

renderStages();
bindEvents();
loadSettings();
