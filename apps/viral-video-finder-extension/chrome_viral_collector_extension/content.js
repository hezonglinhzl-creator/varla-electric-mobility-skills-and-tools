(function () {
  if (window.__viralCollectorInjected) return;
  window.__viralCollectorInjected = true;

  const SERVER = "http://127.0.0.1:8766";

  function inferPlatform(url) {
    const low = (url || "").toLowerCase();
    if (low.includes("tiktok.com")) return "TikTok";
    if (low.includes("instagram.com")) return "Instagram";
    if (low.includes("youtube.com") || low.includes("youtu.be")) return "YouTube";
    return "";
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

  function currentItem() {
    const url = location.href.split("?")[0].replace(/\/$/, "");
    const bodyText = document.body?.innerText || "";
    const title = document.title || "";
    const accountMatch =
      url.match(/tiktok\.com\/@([A-Za-z0-9._-]+)/i) ||
      url.match(/instagram\.com\/([A-Za-z0-9._-]+)\/(?:reel|p|tv)/i) ||
      bodyText.match(/@([A-Za-z0-9._-]{2,})/);
    const likesMatch = bodyText.match(/([\d,.]+[KMB万亿]?)\s*(?:likes|like|赞)/i);
    const viewsMatch = bodyText.match(/([\d,.]+[KMB万亿]?)\s*(?:views|view|播放|观看)/i);
    return {
      url,
      platform: inferPlatform(url),
      title,
      account: accountMatch ? "@" + accountMatch[1].replace(/^@/, "") : "",
      likes: likesMatch ? parseCompactNumber(likesMatch[1]) : "",
      views: viewsMatch ? parseCompactNumber(viewsMatch[1]) : "",
      body_text: bodyText.slice(0, 1200),
      notes: ""
    };
  }

  function collectVisibleReels() {
    const seen = new Set();
    const items = [];
    const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"]'));
    for (const a of anchors) {
      const href = new URL(a.getAttribute("href"), location.origin).href.split("?")[0].replace(/\/$/, "");
      if (!/instagram\.com\/reel\//i.test(href) || seen.has(href)) continue;
      seen.add(href);
      let card = a.closest("article, div");
      for (let i = 0; i < 4 && card && (card.innerText || "").length < 30; i++) {
        card = card.parentElement;
      }
      const text = (card?.innerText || a.getAttribute("aria-label") || document.title || "").slice(0, 1000);
      const accountMatch = text.match(/@([A-Za-z0-9._-]{2,})/);
      const likesMatch = text.match(/([\d,.]+[KMB万亿]?)\s*(?:likes|like|赞)/i);
      const viewsMatch = text.match(/([\d,.]+[KMB万亿]?)\s*(?:views|view|播放|观看)/i);
      items.push({
        url: href,
        platform: "Instagram",
        title: document.title || "Instagram Reel",
        account: accountMatch ? "@" + accountMatch[1].replace(/^@/, "") : "",
        likes: likesMatch ? parseCompactNumber(likesMatch[1]) : "",
        views: viewsMatch ? parseCompactNumber(viewsMatch[1]) : "",
        body_text: text,
        notes: ""
      });
      if (items.length >= 30) break;
    }
    return items;
  }

  async function postItems(items) {
    const res = await fetch(`${SERVER}/bulk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items })
    });
    return await res.json();
  }

  async function checkServer() {
    try {
      const res = await fetch(`${SERVER}/health`, { cache: "no-store" });
      return res.ok;
    } catch {
      return false;
    }
  }

  function setStatus(text, ok = true) {
    const el = document.getElementById("vc-status");
    if (!el) return;
    el.textContent = text;
    el.style.color = ok ? "#0f7b3f" : "#b42318";
  }

  function makeButton(text, onClick) {
    const btn = document.createElement("button");
    btn.textContent = text;
    btn.style.cssText = "border:0;border-radius:6px;padding:7px 9px;background:#245bdb;color:white;font-weight:700;cursor:pointer;font-size:12px;";
    btn.addEventListener("click", onClick);
    return btn;
  }

  function injectPanel() {
    if (document.getElementById("viral-collector-panel")) return;
    const panel = document.createElement("div");
    panel.id = "viral-collector-panel";
    panel.style.cssText = [
      "position:fixed",
      "right:18px",
      "top:150px",
      "z-index:2147483647",
      "width:168px",
      "background:white",
      "border:1px solid #ccd2df",
      "box-shadow:0 8px 28px rgba(0,0,0,.18)",
      "border-radius:8px",
      "padding:10px",
      "font-family:Arial,'Microsoft YaHei',sans-serif",
      "color:#1f2329"
    ].join(";");

    const title = document.createElement("div");
    title.textContent = "爆款采集";
    title.style.cssText = "font-weight:800;font-size:14px;margin-bottom:8px;";
    const status = document.createElement("div");
    status.id = "vc-status";
    status.textContent = "检测服务中...";
    status.style.cssText = "font-size:12px;line-height:1.35;margin:6px 0;color:#646a73;";
    const row = document.createElement("div");
    row.style.cssText = "display:grid;gap:7px;";

    row.appendChild(makeButton("采集当前", async () => {
      const ok = await checkServer();
      if (!ok) return setStatus("本地服务未启动", false);
      try {
        const data = await postItems([currentItem()]);
        setStatus(`新增 ${data.saved || 0} / 重复 ${data.duplicates || 0} / 失败 ${data.failed || 0}`, data.failed === 0);
      } catch (err) {
        setStatus(`采集失败：${err.message}`, false);
      }
    }));

    row.appendChild(makeButton("采集本页Reels", async () => {
      const ok = await checkServer();
      if (!ok) return setStatus("本地服务未启动", false);
      const items = collectVisibleReels();
      if (!items.length) return setStatus("没找到可见 Reel 链接，先滚动页面", false);
      try {
        const data = await postItems(items);
        setStatus(`新增 ${data.saved || 0} / 重复 ${data.duplicates || 0} / 失败 ${data.failed || 0}`, data.failed === 0);
      } catch (err) {
        setStatus(`批量失败：${err.message}`, false);
      }
    }));

    const open = makeButton("打开控制台", () => window.open(SERVER, "_blank"));
    open.style.background = "#43546f";
    row.appendChild(open);

    const hide = document.createElement("button");
    hide.textContent = "×";
    hide.title = "隐藏";
    hide.style.cssText = "position:absolute;right:6px;top:5px;border:0;background:transparent;color:#646a73;font-size:16px;cursor:pointer;";
    hide.addEventListener("click", () => panel.remove());

    panel.appendChild(hide);
    panel.appendChild(title);
    panel.appendChild(status);
    panel.appendChild(row);
    document.body.appendChild(panel);

    checkServer().then(ok => setStatus(ok ? "服务已连接" : "本地服务未启动", ok));
  }

  injectPanel();
  let lastHref = location.href;
  setInterval(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      setTimeout(injectPanel, 800);
    }
  }, 1000);
})();
