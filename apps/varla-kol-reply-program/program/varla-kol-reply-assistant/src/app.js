import { stageRules, classifyStage } from "./stageRules.js";

const state = {
  templates: [],
  specs: {},
  settings: {
    brandName: "Varla",
    senderName: "Team Member",
    signature: "Best,\nTeam Member\nVarla Marketing Team",
    defaultCommission: "8%",
    commissionValidity: "3 months",
    chatgptUrl: "https://chatgpt.com/",
    defaultProduct: "Auto"
  }
};

const toneMap = {
  formal: "Business formal",
  casual: "Natural casual",
  short: "Short and quick",
  semi_formal: "Semi-formal",
  warm: "Warm professional"
};

const $ = (id) => document.getElementById(id);

async function loadJson(path, fallback) {
  try {
    const res = await fetch(path);
    return await res.json();
  } catch {
    return fallback;
  }
}

function cleanText(text) {
  const raw = String(text || "").replace(/\r/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  const emails = [...raw.matchAll(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi)].map((m) => m[0]);
  const links = [...raw.matchAll(/https?:\/\/[^\s)]+/gi)].map((m) => m[0]);
  const followers = [...raw.matchAll(/\b\d+(?:\.\d+)?\s?(?:k|m)?\s?(?:followers|subs|fans)?\b/gi)].map((m) => m[0]);
  return { raw, emails: [...new Set(emails)], links: [...new Set(links)], followers: [...new Set(followers)] };
}

function detectPlatform() {
  const url = $("pageUrl").value.toLowerCase();
  if (url.includes("instagram.com")) return "instagram";
  if (url.includes("tiktok.com")) return "tiktok";
  if (url.includes("business.facebook.com")) return "meta_business";
  if (url.includes("mail.google.com") || url.includes("gmail.com")) return "gmail";
  return $("platform").value || "unknown";
}

function detectProduct(text) {
  const selected = $("product").value;
  if (selected !== "Auto") return selected;
  const t = text.toLowerCase();
  if (t.includes("m7s")) return "M7S";
  if (t.includes("m5s")) return "M5S";
  return "M7S";
}

function platformMatches(template, platform) {
  return template.platform.includes(platform) || template.platform.includes("unknown");
}

function scoreTemplate(template, context) {
  let score = 0;
  if (template.stage === context.stage) score += 8;
  if (platformMatches(template, context.platform)) score += 3;
  if (template.tone === context.tone) score += 3;
  if (template.tone === "casual" && ["instagram", "tiktok", "meta_business"].includes(context.platform)) score += 1;
  if (template.tone === "formal" && context.platform === "gmail") score += 1;
  return score;
}

function retrieveKnowledge(context) {
  return [...state.templates]
    .map((template) => ({ template, score: scoreTemplate(template, context) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map((item) => item.template);
}

function resolveVariables(text, context) {
  const name = context.creatorName || "there";
  return String(text)
    .replaceAll("{{name}}", name)
    .replaceAll("{{brandName}}", state.settings.brandName)
    .replaceAll("{{senderName}}", state.settings.senderName)
    .replaceAll("{{commission}}", state.settings.defaultCommission)
    .replaceAll("{{commissionValidity}}", state.settings.commissionValidity);
}

function makeVariant(base, context, index) {
  const isDm = ["instagram", "tiktok", "meta_business", "unknown"].includes(context.platform);
  const name = context.creatorName || "there";
  const productLine = context.product === "Auto" ? "" : ` For this campaign, we are reviewing fit around the ${context.product}.`;
  const endings = [
    isDm ? "Could you send those details when you have a chance?" : "Could you please send those details when you have a chance?",
    isDm ? "That will help us review the best next step." : "That will help us review the best next step and avoid missing anything important.",
    isDm ? "Happy to take a look once you send them over." : "I am happy to review everything once you send it over.",
    isDm ? "No rush, just send what you have." : "No rush. Please send whatever information you have available."
  ];
  const openers = [
    "",
    isDm ? `Hi ${name}, ` : `Hey ${name},\n\n`,
    isDm ? "Thanks for the message! " : `Hey ${name},\n\nThanks for the message. `,
    isDm ? "Quick note: " : `Hey ${name},\n\nQuick note from our side: `
  ];
  let reply = base;
  if (index === 1 && isDm) reply = reply.replace(/^Thanks/, "Thanks so much");
  if (index === 2) reply = `${openers[index]}${reply}${productLine ? " " + productLine : ""}`;
  if (index === 3) reply = `${reply}\n\n${endings[0]}`;
  if (index === 4) reply = `${openers[index - 1]}${reply}\n\n${endings[3]}`;
  return reply.trim();
}

function safetyCheck(reply, context) {
  const risks = [];
  const lower = reply.toLowerCase();
  if (lower.includes("guarantee") || lower.includes("guaranteed")) risks.push("Check: avoid guaranteed cooperation or sponsorship language.");
  if (lower.includes("free bike") && context.stage !== "confirm_product_exchange") risks.push("Check: avoid promising a free bike before approval.");
  if (lower.includes("ship") && /\b(june|july|august|\d{1,2}\/\d{1,2})\b/i.test(reply)) risks.push("Shipping: only use approximate timing unless Team Member confirmed a date.");
  if (context.stage === "ask_post_private_chat" && /yes|sure|okay/i.test(reply)) risks.push("Private chat: do not approve posting screenshots.");
  return risks;
}

function generateLocalReplies(context) {
  const matched = retrieveKnowledge(context);
  const baseTemplate = matched[0] || {
    template: "Thanks for reaching out! Could you send over your social links, average views, top audience countries, and a little more context about what kind of content you would like to create?",
    nextAction: "Collect creator details",
    riskNotes: ["Manual review recommended"]
  };
  const base = resolveVariables(baseTemplate.template, context);
  return [1, 2, 3, 4].map((i) => {
    const reply = makeVariant(base, context, i);
    return {
      id: i,
      title: ["Option 1 - balanced", "Option 2 - warmer", "Option 3 - clearer", "Option 4 - softer follow-up"][i - 1],
      reply,
      nextAction: baseTemplate.nextAction,
      riskNotes: [...new Set([...(baseTemplate.riskNotes || []), ...safetyCheck(reply, context)])]
    };
  });
}

function productSpecsText(product) {
  const specs = state.specs[product] || {};
  const keys = Object.keys(specs);
  if (!keys.length) return "No confirmed product specs selected. Do not invent specs.";
  return keys.map((key) => `${key}: ${specs[key]}`).join("\n");
}

function buildChatGPTPrompt(context) {
  const templates = retrieveKnowledge(context)
    .map((t) => `- ${t.id}: ${resolveVariables(t.template, context)}`)
    .join("\n\n");
  return `You are my Varla KOL reply assistant.

Your job is to help Team Member from the Varla Marketing Team write natural, professional replies to creators on Instagram, TikTok, Meta Business Suite, and Gmail.

Current context:

* Platform: ${context.platform}
* Tone: ${toneMap[context.tone] || context.tone}
* Stage: ${context.stage}
* Product: ${context.product}
* Creator name: ${context.creatorName || "Unknown"}
* Creator email: ${context.creatorEmail || "Unknown"}

Creator message / conversation:
"""
${context.conversationText}
"""

Relevant local templates:
"""
${templates || "No exact local template found. Use the brand rules below."}
"""

Relevant product specs:
"""
${productSpecsText(context.product)}
"""

Brand context:
Varla is currently focusing on product exchange partnerships. In some cases, Varla may add affiliate commission depending on creator fit, content quality, audience, engagement, and performance.

Default partnership position:

* Product exchange first
* Affiliate commission can be added for stronger creators
* Default commission can be ${state.settings.defaultCommission} if confirmed
* Commission is usually tracked through a discount code or Shopify code
* Default commission validity is ${state.settings.commissionValidity} if provided in the context

Rules:

1. Match the platform style.
2. Instagram, TikTok, and Meta Business Suite replies should be short, natural, and human.
3. Gmail replies should be professional, clear, and structured.
4. Never promise sponsorship, free bikes, paid collaboration, or guaranteed cooperation unless Team Member explicitly confirms it.
5. Never say reaching a follower count automatically guarantees sponsorship.
6. Never approve posting private brand conversations or screenshots.
7. Never invent product specs.
8. Never promise a specific shipping date unless provided in the context.
9. Do not sound like a mass template.
10. Always move the conversation toward the next practical step.

Please generate 4 reply options:

1. Short casual version
2. Warm professional version
3. More direct version
4. Softer relationship-building version

For each option, include:

* Reply
* Why this works
* Next action
* Risk notes if any`;
}

function collectContext() {
  const cleaned = cleanText($("conversation").value);
  const platform = detectPlatform();
  const auto = classifyStage(cleaned.raw);
  const selectedStage = $("stage").value || auto.detectedStage;
  const context = {
    platform,
    pageUrl: $("pageUrl").value,
    stage: selectedStage,
    tone: $("tone").value,
    product: detectProduct(cleaned.raw),
    creatorName: $("creatorName").value.trim(),
    creatorEmail: $("creatorEmail").value.trim() || cleaned.emails[0] || "",
    socialLinks: cleaned.links,
    conversationText: cleaned.raw,
    auto
  };
  $("platform").value = platform;
  syncSegmented("platform", platform);
  $("creatorEmail").value = context.creatorEmail;
  $("detectedMeta").textContent = `Detected stage: ${auto.detectedStage} | Confidence: ${Math.round(auto.confidence * 100)}% | Keywords: ${auto.matchedKeywords.join(", ") || "none"}`;
  return context;
}

function renderStages() {
  $("stage").innerHTML = stageRules.map((rule) => `<option value="${rule.id}">${rule.label}</option>`).join("");
}

function syncSegmented(targetId, value) {
  document.querySelectorAll(`.segmented[data-target="${targetId}"] .chip`).forEach((button) => {
    button.classList.toggle("active", button.dataset.value === value);
  });
}

function setupSegmentedControls() {
  document.querySelectorAll(".segmented").forEach((group) => {
    const target = $(group.dataset.target);
    group.querySelectorAll(".chip").forEach((button) => {
      button.addEventListener("click", () => {
        target.value = button.dataset.value;
        syncSegmented(group.dataset.target, target.value);
      });
    });
    target.addEventListener("change", () => syncSegmented(group.dataset.target, target.value));
    syncSegmented(group.dataset.target, target.value);
  });
}

function renderReplies(replies) {
  $("replyOutput").innerHTML = replies.map((item) => `
    <article class="reply-card">
      <div class="reply-head">
        <strong>${item.title}</strong>
        <button data-copy="${item.id}">Copy</button>
      </div>
      <textarea id="reply-${item.id}">${item.reply}</textarea>
      <div class="meta"><b>Next:</b> ${item.nextAction || "Manual review"}</div>
      <div class="risk">${item.riskNotes.length ? item.riskNotes.join(" | ") : "No obvious risk flagged."}</div>
    </article>
  `).join("");
  replies.forEach((item) => {
    document.querySelector(`[data-copy="${item.id}"]`).addEventListener("click", async () => {
      await navigator.clipboard.writeText($(`reply-${item.id}`).value);
      toast("Copied reply.");
    });
  });
}

function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 1600);
}

function saveSettings() {
  state.settings.brandName = $("brandName").value || "Varla";
  state.settings.senderName = $("senderName").value || "Team Member";
  state.settings.signature = $("signature").value || state.settings.signature;
  state.settings.defaultCommission = $("commission").value || "8%";
  state.settings.commissionValidity = $("commissionValidity").value || "3 months";
  state.settings.chatgptUrl = $("chatgptUrl").value || "https://chatgpt.com/";
  localStorage.setItem("varlaSettings", JSON.stringify(state.settings));
  toast("Settings saved locally.");
}

function loadSettings() {
  const saved = localStorage.getItem("varlaSettings");
  if (saved) Object.assign(state.settings, JSON.parse(saved));
  $("brandName").value = state.settings.brandName;
  $("senderName").value = state.settings.senderName;
  $("signature").value = state.settings.signature;
  $("commission").value = state.settings.defaultCommission;
  $("commissionValidity").value = state.settings.commissionValidity;
  $("chatgptUrl").value = state.settings.chatgptUrl;
}

async function init() {
  renderStages();
  setupSegmentedControls();
  state.templates = await loadJson("./knowledge_seed/templates.json", []);
  state.specs = await loadJson("./knowledge_seed/product_specs.json", {});
  loadSettings();
  $("kbCount").textContent = `${state.templates.length} templates, ${Object.keys(state.specs).length} products`;
  $("generateReplies").addEventListener("click", () => renderReplies(generateLocalReplies(collectContext())));
  $("autoDetect").addEventListener("click", () => {
    const context = collectContext();
    $("stage").value = context.auto.detectedStage;
    $("product").value = context.product;
    toast("Detected stage and product.");
  });
  $("generatePrompt").addEventListener("click", () => {
    $("promptPreview").value = buildChatGPTPrompt(collectContext());
    toast("Prompt generated.");
  });
  $("copyPrompt").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("promptPreview").value || buildChatGPTPrompt(collectContext()));
    toast("Copied ChatGPT prompt.");
  });
  $("openChatGPT").addEventListener("click", () => window.open(state.settings.chatgptUrl, "_blank"));
  $("copyFinal").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("finalReply").value);
    toast("Copied final reply. Paste it manually into the platform.");
  });
  $("clearConversation").addEventListener("click", () => {
    $("conversation").value = "";
    $("detectedMeta").textContent = "Cleared.";
  });
  $("saveSettings").addEventListener("click", saveSettings);
  $("exportKnowledge").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify({ templates: state.templates, specs: state.specs }, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "varla_knowledge_export.json";
    a.click();
  });
}

init();
