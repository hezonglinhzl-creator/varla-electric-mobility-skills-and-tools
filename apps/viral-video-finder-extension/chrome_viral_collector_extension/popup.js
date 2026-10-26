const serverEl = document.getElementById("server");
const tabEl = document.getElementById("tab");
const recordButton = document.getElementById("record");
const collectReelsButton = document.getElementById("collectReels");
const searchButton = document.getElementById("search");

let currentTab = null;
let serverOk = false;

async function getCurrentTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function isSupportedVideoUrl(url) {
  if (!url) return false;
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    const path = u.pathname.toLowerCase();
    if (host.includes("tiktok.com")) return /\/@[^/]+\/video\//.test(path) || /\/t\//.test(path);
    if (host.includes("instagram.com")) return /\/reel\//.test(path) || /\/p\//.test(path);
    if (host.includes("youtube.com")) return path === "/watch" || path.startsWith("/shorts/");
    if (host.includes("youtu.be")) return true;
    if (host === "127.0.0.1" || host === "localhost") return false;
  } catch {}
  return false;
}

function inferPlatform(url) {
  const low = (url || "").toLowerCase();
  if (low.includes("tiktok.com")) return "TikTok";
  if (low.includes("instagram.com")) return "Instagram";
  if (low.includes("youtube.com") || low.includes("youtu.be")) return "YouTube";
  return "";
}

async function checkServer() {
  try {
    const res = await fetch("http://127.0.0.1:8766/health", { cache: "no-store" });
    serverOk = res.ok;
  } catch {
    serverOk = false;
  }
  serverEl.className = "status " + (serverOk ? "ok" : "bad");
  serverEl.textContent = serverOk ? "Local server connected." : "Local server not running. Start start_viral_video_finder.bat first.";
}

async function refresh() {
  currentTab = await getCurrentTab();
  const url = currentTab?.url || "";
  if (/^https?:\/\/(127\.0\.0\.1|localhost)/i.test(url)) {
    tabEl.textContent = "当前是本地工具页。请切回 Instagram / TikTok / YouTube 视频页，或直接使用页面右侧的“爆款采集”悬浮按钮。";
  } else {
    tabEl.textContent = currentTab ? `${currentTab.title || ""}\n${url}` : "No active tab found.";
  }
  await checkServer();
  recordButton.disabled = !(serverOk && isSupportedVideoUrl(url));
  collectReelsButton.disabled = !(serverOk && /instagram\.com/i.test(url));
  if (!isSupportedVideoUrl(url)) {
    tabEl.textContent += "\n\nOpen a TikTok / Instagram / YouTube video page before collecting, or open Instagram search/tag/Reels page to collect visible Reels.";
  }
}

function parseCompactNumber(text) {
  if (!text) return "";
  const raw = String(text).replace(/,/g, "").trim();
  const match = raw.match(/(\d+(?:\.\d+)?)\s*([KMB万亿]?)/i);
  if (!match) return "";
  let n = Number(match[1]);
  const unit = (match[2] || "").toUpperCase();
  if (unit === "K") n *= 1000;
  if (unit === "M") n *= 1000000;
  if (unit === "B") n *= 1000000000;
  if (unit === "万") n *= 10000;
  if (unit === "亿") n *= 100000000;
  if (!Number.isFinite(n)) return "";
  if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1000) return (n / 1000).toFixed(n >= 100000 ? 0 : 1).replace(/\.0$/, "") + "K";
  return String(Math.round(n));
}

function scrapePageData() {
  const bodyText = document.body?.innerText || "";
  const title = document.title || "";
  const url = location.href;

  function pick(patterns) {
    for (const pattern of patterns) {
      const match = bodyText.match(pattern) || title.match(pattern) || url.match(pattern);
      if (match) return match[1] || match[0];
    }
    return "";
  }

  const account = pick([
    /tiktok\.com\/@([A-Za-z0-9._-]+)/i,
    /instagram\.com\/([A-Za-z0-9._-]+)\/(?:reel|p)\//i,
    /@([A-Za-z0-9._-]{2,})/i
  ]);

  const likes = pick([
    /([\d,.]+[KMB万亿]?)\s*(?:likes|like|赞)/i,
    /(?:likes|like|赞)\s*([\d,.]+[KMB万亿]?)/i
  ]);

  const views = pick([
    /([\d,.]+[KMB万亿]?)\s*(?:views|view|观看|播放)/i,
    /(?:views|view|观看|播放)\s*([\d,.]+[KMB万亿]?)/i
  ]);

  return {
    platform: inferPlatform(url),
    account: account ? "@" + String(account).replace(/^@/, "") : "",
    likes: parseCompactNumber(likes),
    views: parseCompactNumber(views),
    body_text: bodyText.slice(0, 1500)
  };
}

async function scrapeVisibleInstagramReels() {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const seen = new Set();

  function collectOnce() {
    const bodyText = document.body?.innerText || "";
    const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"]'));
    const items = [];
    for (const a of anchors) {
      const href = new URL(a.getAttribute("href"), location.origin).href.split("?")[0].replace(/\/$/, "");
      if (!/instagram\.com\/reel\//i.test(href) || seen.has(href)) continue;
      seen.add(href);

      let card = a.closest("article, div");
      for (let i = 0; i < 4 && card && (card.innerText || "").length < 30; i++) {
        card = card.parentElement;
      }
      const text = (card?.innerText || a.getAttribute("aria-label") || document.title || "").slice(0, 1000);
      const accountMatch =
        text.match(/@([A-Za-z0-9._-]{2,})/) ||
        href.match(/instagram\.com\/([A-Za-z0-9._-]+)\/reel/i);
      const likesMatch = text.match(/([\d,.]+[KMB]?)\s*(?:likes|like)/i);
      const viewsMatch = text.match(/([\d,.]+[KMB]?)\s*(?:views|view)/i);
      items.push({
        url: href,
        title: document.title || "Instagram Reel",
        platform: "Instagram",
        account: accountMatch ? "@" + accountMatch[1].replace(/^@/, "") : "",
        likes: likesMatch ? parseCompactNumber(likesMatch[1]) : "",
        views: viewsMatch ? parseCompactNumber(viewsMatch[1]) : "",
        keyword: "",
        body_text: text || bodyText.slice(0, 600),
        notes: "Chrome logged-in page bulk Reel collection"
      });
    }
    return items;
  }

  let all = collectOnce();
  for (let i = 0; i < 4; i++) {
    window.scrollBy(0, Math.round(window.innerHeight * 1.6));
    await sleep(900);
    all = all.concat(collectOnce());
    if (all.length >= 25) break;
  }
  return all.slice(0, 25);
}

recordButton.addEventListener("click", async () => {
  if (!currentTab) return;
  let extra = "";
  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: currentTab.id },
      func: scrapePageData
    });
    const data = result?.result || {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== undefined && value !== null && String(value).trim()) {
        extra += `&${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`;
      }
    }
  } catch (err) {
    extra += `&notes=${encodeURIComponent("Scrape failed: " + err.message)}`;
  }
  const target = `http://127.0.0.1:8766/add?url=${encodeURIComponent(currentTab.url || "")}&title=${encodeURIComponent(currentTab.title || "")}${extra}`;
  await chrome.tabs.create({ url: target });
});

collectReelsButton.addEventListener("click", async () => {
  if (!currentTab) return;
  collectReelsButton.disabled = true;
  collectReelsButton.textContent = "Collecting...";
  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: currentTab.id },
      func: scrapeVisibleInstagramReels
    });
    const items = result?.result || [];
    if (!items.length) {
      tabEl.textContent += "\n\nNo visible Instagram Reels found. Open a Reels/search/tag results page and scroll once.";
      return;
    }
    const res = await fetch("http://127.0.0.1:8766/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items })
    });
    const data = await res.json();
    tabEl.textContent += `\n\nSaved ${data.saved || 0}, duplicates ${data.duplicates || 0}, failed ${data.failed || 0}.`;
  } catch (err) {
    tabEl.textContent += `\n\nBulk collect failed: ${err.message}`;
  } finally {
    collectReelsButton.textContent = "Collect Visible Reels";
    collectReelsButton.disabled = !(serverOk && /instagram\.com/i.test(currentTab?.url || ""));
  }
});

searchButton.addEventListener("click", async () => {
  await chrome.tabs.create({ url: "http://127.0.0.1:8766" });
});

refresh();
