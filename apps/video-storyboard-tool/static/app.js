let currentMode = "breakdown";
let storyboard = null;
let storyboards = [];
let selectMode = true;
let dragStartCell = null;
let dragCurrentCell = null;
let isDraggingCells = false;
let isAnalyzing = false;

const $ = (selector) => document.querySelector(selector);
const statusEl = $("#status");
const syncResult = $("#syncResult");
const videoInput = $("#videoInput");
const preview = $("#preview");
const productModel = $("#productModel");
const selectModeBtn = $("#selectModeBtn");
const outputFormat = $("#outputFormat");
const feishuDocUrl = $("#feishuDocUrl");
const feishuBitableUrl = $("#feishuBitableUrl");
const feishuUserToken = $("#feishuUserToken");
const cacheReportBtn = $("#cacheReportBtn");
const uploadPanel = $(".upload-panel");

function ensureRichCopyButton() {
  const existing = $("#copyRichTableBtn");
  if (existing) return existing;
  const button = document.createElement("button");
  button.id = "copyRichTableBtn";
  button.type = "button";
  button.className = "";
  button.textContent = "复制飞书原生表格";
  $("#copyMarkdownBtn").insertAdjacentElement("afterend", button);
  return button;
}

const copyRichTableBtn = ensureRichCopyButton();

function setStatus(text) {
  statusEl.textContent = text;
}

function outputUrl(path) {
  if (!path) return "";
  const normalized = path.replaceAll("\\", "/");
  const marker = "/outputs/";
  const idx = normalized.lastIndexOf(marker);
  if (idx >= 0) return normalized.slice(idx);
  return normalized;
}

function outputThumbUrl(path) {
  if (!path) return "";
  const normalized = path.replaceAll("\\", "/");
  const match = normalized.match(/\/outputs\/([^/]+)\/frames\/([^/]+)$/);
  if (match) {
    return `/api/thumb/${encodeURIComponent(match[1])}/${encodeURIComponent(match[2])}`;
  }
  return outputUrl(path);
}

function setTableEditable(enabled) {
  document.querySelectorAll(".story-table [data-key]").forEach((cell) => {
    cell.contentEditable = enabled ? "true" : "false";
  });
  document.querySelectorAll(".story-table").forEach((table) => table.classList.toggle("manual-select-mode", !enabled));
  if (selectModeBtn) {
    selectModeBtn.classList.toggle("active", !enabled);
    selectModeBtn.textContent = enabled ? "开放框选" : "退出框选";
  }
  if (enabled) clearCellSelection();
}

function selectableCell(target) {
  const cell = target.closest("td");
  if (!cell || !cell.closest(".story-table")) return null;
  return cell;
}

function cellPosition(cell) {
  return {
    row: cell.parentElement.rowIndex,
    col: cell.cellIndex,
  };
}

function clearCellSelection() {
  document.querySelectorAll(".story-table td.cell-selected").forEach((cell) => {
    cell.classList.remove("cell-selected");
  });
}

function updateCellSelection() {
  clearCellSelection();
  if (!dragStartCell || !dragCurrentCell) return;
  const start = cellPosition(dragStartCell);
  const end = cellPosition(dragCurrentCell);
  const minRow = Math.min(start.row, end.row);
  const maxRow = Math.max(start.row, end.row);
  const minCol = Math.min(start.col, end.col);
  const maxCol = Math.max(start.col, end.col);
  document.querySelectorAll(".story-table tbody tr").forEach((row) => {
    const rowIndex = row.rowIndex;
    if (rowIndex < minRow || rowIndex > maxRow) return;
    [...row.cells].forEach((cell) => {
      if (cell.cellIndex >= minCol && cell.cellIndex <= maxCol) {
        cell.classList.add("cell-selected");
      }
    });
  });
}

function selectedCellsText() {
  const selected = [...document.querySelectorAll(".story-table td.cell-selected")];
  if (!selected.length) return "";
  const rows = new Map();
  selected.forEach((cell) => {
    const rowIndex = cell.parentElement.rowIndex;
    if (!rows.has(rowIndex)) rows.set(rowIndex, []);
    rows.get(rowIndex).push(cell);
  });
  return [...rows.keys()]
    .sort((a, b) => a - b)
    .map((rowIndex) =>
      rows
        .get(rowIndex)
        .sort((a, b) => a.cellIndex - b.cellIndex)
        .map((cell) => cell.innerText.replace(/\n+/g, " ").trim())
        .join("\t"),
    )
    .join("\n");
}

function cleanMarkdownCell(value) {
  return String(value || "")
    .replaceAll("\r\n", " ")
    .replaceAll("\n", " ")
    .replaceAll("\t", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replaceAll("|", "｜");
}

function cleanTableCell(value) {
  return String(value || "")
    .replaceAll("\r\n", " ")
    .replaceAll("\n", " ")
    .replaceAll("\t", " ")
    .replace(/\s+/g, " ")
    .trim();
}

function stripLeadingTimeRange(value) {
  return cleanTableCell(value).replace(/^\d{2}:\d{2}\.\d{2}-\d{2}:\d{2}\.\d{2}[,，;；\s]*/, "");
}

function activeStoryboards() {
  if (storyboards.length) return storyboards;
  return storyboard ? [storyboard] : [];
}

async function imageToDataUrl(path) {
  if (!path) return "";
  const response = await fetch(outputUrl(path));
  if (!response.ok) return "";
  const blob = await response.blob();
  return await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      const maxWidth = 160;
      const maxHeight = 280;
      const scale = Math.min(maxWidth / image.naturalWidth, maxHeight / image.naturalHeight, 1);
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", 0.82));
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("无法读取图片"));
    };
    image.src = url;
  });
}

function storyboardPlainTable(item = storyboard) {
  if (!item) return "";
  const header = ["镜号", "景别", "拍摄手法", "画面", "画面说明", "备注", "台词", "英文台词"];
  const lines = [header.join("\t")];
  item.shots.forEach((shot) => {
    lines.push(
      [
        shot.shot_id,
        shot.shot_size,
        shot.camera_method,
        shot.frame_path ? "[图片]" : "",
        stripLeadingTimeRange(shot.visual_description),
        shot.notes,
        shot.dialogue_cn,
        shot.dialogue_en,
      ]
        .map(cleanTableCell)
        .join("\t"),
    );
  });
  return lines.join("\n");
}

async function storyboardRichHtmlTable(item = storyboard, includeTitle = false) {
  const headers = ["镜号", "景别", "拍摄手法", "画面", "画面说明", "备注", "台词", "英文台词"];
  const rows = [];
  for (const shot of item.shots) {
    let imageUrl = "";
    try {
      imageUrl = await imageToDataUrl(shot.frame_path);
    } catch {
      imageUrl = "";
    }
    const imageHtml = imageUrl
      ? `<img src="${escapeHtml(imageUrl)}" alt="shot ${escapeHtml(shot.shot_id)}" width="96" style="width:96px;max-height:170px;object-fit:contain;display:block;">`
      : "";
    rows.push(`
      <tr>
        <td>${escapeHtml(cleanTableCell(shot.shot_id))}</td>
        <td>${escapeHtml(cleanTableCell(shot.shot_size))}</td>
        <td>${escapeHtml(cleanTableCell(shot.camera_method))}</td>
        <td>${imageHtml}</td>
        <td>${escapeHtml(stripLeadingTimeRange(shot.visual_description))}</td>
        <td>${escapeHtml(cleanTableCell(shot.notes))}</td>
        <td>${escapeHtml(cleanTableCell(shot.dialogue_cn))}</td>
        <td>${escapeHtml(cleanTableCell(shot.dialogue_en))}</td>
      </tr>
    `);
  }
  return `
    ${includeTitle ? `<h2 style="font-family:Arial,'Microsoft YaHei',sans-serif;font-size:18px;margin:18px 0 8px;">${escapeHtml(item.video_info?.file_name || "分镜表")}</h2>` : ""}
    <table style="border-collapse:collapse;font-family:Arial,'Microsoft YaHei',sans-serif;font-size:13px;line-height:1.45;margin-bottom:18px;">
      <thead>
        <tr>
          ${headers.map((header) => `<th style="border:1px solid #d8dde3;background:#eef3f2;padding:8px;text-align:left;">${header}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows.join("")}
      </tbody>
    </table>
  `.replaceAll("<td>", '<td style="border:1px solid #d8dde3;padding:8px;vertical-align:top;">');
}

function allStoryboardsPlainTables() {
  return activeStoryboards()
    .map((item) => `${item.video_info?.file_name || "分镜表"}\n${storyboardPlainTable(item)}`)
    .join("\n\n");
}

async function allStoryboardsRichHtmlTables() {
  const items = activeStoryboards();
  const tables = [];
  for (const item of items) {
    tables.push(await storyboardRichHtmlTable(item, items.length > 1));
  }
  return tables.join('<p style="margin:16px 0;"></p>');
}

async function waitForImages(root) {
  const images = [...root.querySelectorAll("img")];
  await Promise.all(
    images.map(
      (img) =>
        new Promise((resolve) => {
          if (img.complete && img.naturalWidth > 0) {
            resolve();
            return;
          }
          img.onload = () => resolve();
          img.onerror = () => resolve();
        }),
    ),
  );
}

async function copyHtmlBySelection(html) {
  const container = document.createElement("div");
  container.contentEditable = "true";
  container.style.position = "fixed";
  container.style.left = "-10000px";
  container.style.top = "0";
  container.style.width = "1200px";
  container.innerHTML = html;
  document.body.appendChild(container);
  await waitForImages(container);

  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(container);
  selection.removeAllRanges();
  selection.addRange(range);
  const ok = document.execCommand("copy");
  selection.removeAllRanges();
  container.remove();
  return ok;
}

async function copyRichStoryboardTable() {
  if (!activeStoryboards().length) {
    syncResult.textContent = "请先拆解视频。";
    return;
  }
  setStatus("复制中");
  syncResult.textContent = `正在准备 ${activeStoryboards().length} 个飞书原生表格...`;
  const html = await allStoryboardsRichHtmlTables();
  const text = allStoryboardsPlainTables();

  if (await copyHtmlBySelection(html)) {
    setStatus("已复制");
    syncResult.textContent = `已复制 ${activeStoryboards().length} 个飞书原生表格。现在去飞书文档空白处直接 Ctrl+V。`;
    return;
  }

  if (window.ClipboardItem) {
    await navigator.clipboard.write([
      new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      }),
    ]);
    setStatus("已复制");
    syncResult.textContent = `已复制 ${activeStoryboards().length} 个飞书原生表格。现在去飞书文档空白处直接 Ctrl+V。`;
    return;
  }

  await navigator.clipboard.writeText(text);
  setStatus("已复制文字");
  syncResult.textContent = "浏览器不支持图文剪贴板，已复制纯文字表格。建议用新版 Chrome / Edge 打开本地工具。";
}

function storyboardMarkdownTable(item = storyboard) {
  if (!item) return "";
  const header = ["时间", "画面参考（竖屏9:16）", "画面描述", "角色动作 / 镜头运动", "对话 / 声音", "备注"];
  const lines = [
    `| ${header.join(" | ")} |`,
    "|---|---|---|---|---|---|",
  ];
  item.shots.forEach((shot) => {
    lines.push(
      `| ${[
        `${shot.start_time || ""}-${shot.end_time || ""}`,
        shot.frame_path || "",
        shot.visual_description || "",
        `${shot.shot_size || ""}；${shot.camera_method || ""}`,
        shot.dialogue_cn || shot.dialogue_en || "",
        shot.notes || "",
      ]
        .map(cleanMarkdownCell)
        .join(" | ")} |`,
    );
  });
  return lines.join("\n");
}

function allStoryboardsMarkdownTables() {
  return activeStoryboards()
    .map((item) => `## ${item.video_info?.file_name || "分镜表"}\n\n${storyboardMarkdownTable(item)}`)
    .join("\n\n");
}

async function copySelectedCells() {
  const text = selectedCellsText();
  if (!text) {
    syncResult.textContent = "请先拖选要复制的多个格子。";
    return;
  }
  await navigator.clipboard.writeText(text);
  syncResult.textContent = `已复制 ${document.querySelectorAll(".story-table td.cell-selected").length} 个格子，可直接粘贴到 Excel / 飞书表格。`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bindRevealButtons(root = syncResult) {
  root.querySelectorAll("[data-reveal]").forEach((button) => {
    button.addEventListener("click", async () => {
      const revealUrl = button.dataset.reveal;
      if (!revealUrl) return;
      button.disabled = true;
      button.textContent = "正在打开...";
      const revealResponse = await fetch(revealUrl, { method: "POST" });
      button.textContent = revealResponse.ok ? "已打开位置" : "打开失败";
      button.disabled = false;
    });
  });
}

function renderExportResult(data) {
  const files = data.files || [
    {
      name: data.path?.split(/[\\/]/).pop() || "导出文件",
      path: data.path,
      download_url: data.download_url,
      reveal_url: data.reveal_url,
    },
  ];
  syncResult.innerHTML = `
    <div><strong>导出成功，生成 ${files.length} 个文件：</strong></div>
    <ul class="file-list">
      ${files
        .map(
          (file) => `
            <li>
              <div>${escapeHtml(file.name)}</div>
              <div class="path">${escapeHtml(file.path)}</div>
              <div class="export-actions">
                <a class="button-link" href="${file.download_url}" target="_blank">下载文件</a>
                <button type="button" data-reveal="${file.reveal_url || ""}">打开文件位置</button>
              </div>
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
  bindRevealButtons();
}

function resultLine(title, result) {
  if (!result) return `<div class="sync-line muted">${title}：未执行</div>`;
  const chunks = Number(result.details?.fallback_chunks || 0);
  const status = result.ok && chunks > 0 ? `成功，已按飞书接口限制拆成 ${chunks} 个原生表格` : result.ok ? "成功" : "失败";
  const errors = (result.errors || []).join("；");
  return `<div class="sync-line ${result.ok ? "ok" : "fail"}">${title}：${status}${errors ? `｜${escapeHtml(errors)}` : ""}</div>`;
}

function renderSyncResult(data) {
  const details = data.details || {};
  syncResult.innerHTML = `
    <div><strong>同步结果</strong></div>
    <div class="sync-line ok">本地导出：${details.local_export?.success ? "成功" : "未执行"}</div>
    ${resultLine("同步飞书原生表格", details.doc)}
    ${resultLine("多维表格同步", details.bitable)}
    ${data.doc_url ? `<div>文档：<a href="${data.doc_url}" target="_blank">${data.doc_url}</a></div>` : ""}
    ${data.bitable_url ? `<div>多维表格：<a href="${data.bitable_url}" target="_blank">${data.bitable_url}</a></div>` : ""}
    ${details.log_path ? `<div class="path">日志：${escapeHtml(details.log_path)}</div>` : ""}
    <pre class="debug-json">${escapeHtml(JSON.stringify(details, null, 2))}</pre>
  `;
}

function renderWarnings(warnings) {
  const box = $("#warnings");
  if (!warnings || warnings.length === 0) {
    box.style.display = "none";
    box.textContent = "";
    return;
  }
  box.style.display = "block";
  box.textContent = warnings.join("\n");
}

function renderTable() {
  const tbody = $("#storyTable tbody");
  tbody.innerHTML = "";
  if (!storyboard) return;

  const productText = storyboard.product_model ? ` · ${storyboard.product_model}` : "";
  $("#videoInfo").textContent = `${storyboard.video_info.file_name} · ${storyboard.video_info.duration} · ${storyboard.video_info.aspect_ratio} · ${storyboard.video_info.resolution}${productText}`;
  $("#shotCount").textContent = `${storyboard.shots.length} 镜`;
  renderWarnings(storyboard.warnings);

  storyboard.shots.forEach((shot, index) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td contenteditable="true" data-key="shot_id">${shot.shot_id || ""}</td>
      <td contenteditable="true" data-key="shot_size">${shot.shot_size || ""}</td>
      <td contenteditable="true" data-key="camera_method">${shot.camera_method || ""}</td>
      <td>
        ${shot.frame_path ? `<img class="frame" loading="lazy" decoding="async" src="${outputThumbUrl(shot.frame_path)}" alt="shot ${shot.shot_id}">` : ""}
        <div class="path" contenteditable="true" data-key="frame_path">${shot.frame_path || ""}</div>
      </td>
      <td contenteditable="true" data-key="visual_description">${shot.visual_description || ""}</td>
      <td contenteditable="true" data-key="notes">${shot.notes || ""}</td>
      <td contenteditable="true" data-key="dialogue_cn">${shot.dialogue_cn || ""}</td>
      <td contenteditable="true" data-key="dialogue_en">${shot.dialogue_en || ""}</td>
    `;
    tr.querySelectorAll("[contenteditable='true']").forEach((cell) => {
      cell.addEventListener("input", () => {
        const key = cell.dataset.key;
        storyboard.shots[index][key] = cell.textContent.trim();
      });
    });
    tbody.appendChild(tr);
  });
  setTableEditable(!selectMode);
}

function renderAllTables() {
  const items = activeStoryboards();
  const wrap = document.querySelector(".table-wrap");
  if (!items.length) {
    renderTable();
    return;
  }

  wrap.innerHTML = "";
  const totalShots = items.reduce((sum, item) => sum + item.shots.length, 0);
  const productText = items[0].product_model ? ` · ${items[0].product_model}` : "";
  $("#videoInfo").textContent =
    items.length === 1
      ? `${items[0].video_info.file_name} · ${items[0].video_info.duration} · ${items[0].video_info.aspect_ratio} · ${items[0].video_info.resolution}${productText}`
      : `${items.length} 个视频 · 共 ${totalShots} 镜${productText}`;
  $("#shotCount").textContent = `${totalShots} 镜`;
  renderWarnings(items.flatMap((item) => item.warnings || []));

  items.forEach((item, itemIndex) => {
    const section = document.createElement("section");
    section.className = "storyboard-section";
    section.innerHTML = `
      ${items.length > 1 ? `<h3>${escapeHtml(item.video_info.file_name)} · ${escapeHtml(item.video_info.duration)} · ${escapeHtml(item.video_info.aspect_ratio)} · ${escapeHtml(item.video_info.resolution)}</h3>` : ""}
      <table class="story-table" ${itemIndex === 0 ? 'id="storyTable"' : ""}>
        <thead>
          <tr>
            <th>镜号</th>
            <th>景别</th>
            <th>拍摄手法</th>
            <th>画面</th>
            <th>画面说明</th>
            <th>备注</th>
            <th>台词</th>
            <th>英文台词</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    `;
    const tbody = section.querySelector("tbody");
    item.shots.forEach((shot, index) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td contenteditable="true" data-key="shot_id">${shot.shot_id || ""}</td>
        <td contenteditable="true" data-key="shot_size">${shot.shot_size || ""}</td>
        <td contenteditable="true" data-key="camera_method">${shot.camera_method || ""}</td>
        <td>
          ${shot.frame_path ? `<img class="frame" loading="lazy" decoding="async" src="${outputThumbUrl(shot.frame_path)}" alt="shot ${shot.shot_id}">` : ""}
          <div class="path" contenteditable="true" data-key="frame_path">${shot.frame_path || ""}</div>
        </td>
        <td contenteditable="true" data-key="visual_description">${shot.visual_description || ""}</td>
        <td contenteditable="true" data-key="notes">${shot.notes || ""}</td>
        <td contenteditable="true" data-key="dialogue_cn">${shot.dialogue_cn || ""}</td>
        <td contenteditable="true" data-key="dialogue_en">${shot.dialogue_en || ""}</td>
      `;
      tr.querySelectorAll("[contenteditable='true']").forEach((cell) => {
        cell.addEventListener("input", () => {
          const key = cell.dataset.key;
          item.shots[index][key] = cell.textContent.trim();
        });
      });
      tbody.appendChild(tr);
    });
    wrap.appendChild(section);
  });
  setTableEditable(!selectMode);
}

document.querySelectorAll(".mode").forEach((button) => {
  button.addEventListener("click", () => {
    currentMode = button.dataset.mode;
    document.querySelectorAll(".mode").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  });
});

if (selectModeBtn) {
  selectModeBtn.addEventListener("click", () => {
    if (selectMode && document.querySelector(".story-table td.cell-selected")) {
      copySelectedCells();
      return;
    }
    selectMode = !selectMode;
    setTableEditable(!selectMode);
    syncResult.textContent = selectMode
      ? "已开放系统框选：现在可以直接拖选表格文字和图片后 Ctrl+C。需要多格复制时，按住 Alt 再拖选单元格。"
      : "已回到表格编辑模式。";
  });
}

$("#storyTable").addEventListener("mousedown", (event) => {
  if (!selectMode || !event.altKey) return;
  const cell = selectableCell(event.target);
  if (!cell) return;
  event.preventDefault();
  isDraggingCells = true;
  dragStartCell = cell;
  dragCurrentCell = cell;
  updateCellSelection();
});

$("#storyTable").addEventListener("mouseover", (event) => {
  if (!selectMode || !isDraggingCells) return;
  const cell = selectableCell(event.target);
  if (!cell || cell === dragCurrentCell) return;
  dragCurrentCell = cell;
  updateCellSelection();
});

document.querySelector(".table-wrap").addEventListener("mousedown", (event) => {
  if (!selectMode || !event.altKey) return;
  const cell = selectableCell(event.target);
  if (!cell) return;
  event.preventDefault();
  isDraggingCells = true;
  dragStartCell = cell;
  dragCurrentCell = cell;
  updateCellSelection();
});

document.querySelector(".table-wrap").addEventListener("mouseover", (event) => {
  if (!selectMode || !isDraggingCells) return;
  const cell = selectableCell(event.target);
  if (!cell || cell === dragCurrentCell) return;
  dragCurrentCell = cell;
  updateCellSelection();
});

document.addEventListener("mouseup", () => {
  isDraggingCells = false;
});

document.addEventListener("copy", (event) => {
  if (!selectMode || !document.querySelector(".story-table td.cell-selected")) return;
  const text = selectedCellsText();
  if (!text) return;
  event.preventDefault();
  event.clipboardData.setData("text/plain", text);
  syncResult.textContent = `已复制 ${document.querySelectorAll(".story-table td.cell-selected").length} 个格子。`;
});

function formatEstimate(seconds) {
  const safe = Math.max(1, Math.round(seconds || 1));
  if (safe < 60) return `${safe} 秒`;
  const minutes = Math.floor(safe / 60);
  const rest = safe % 60;
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;
}

function estimateSecondsFromFile(file, durationSeconds = 0) {
  const sizeMb = file.size / 1024 / 1024;
  const byDuration = durationSeconds ? durationSeconds * 1.8 + 18 : 0;
  const bySize = sizeMb * 1.5 + 20;
  return Math.max(25, byDuration, bySize);
}

function readVideoDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      const duration = Number.isFinite(video.duration) ? video.duration : 0;
      URL.revokeObjectURL(url);
      resolve(duration);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(0);
    };
    video.src = url;
  });
}

async function estimateFiles(files) {
  const durations = await Promise.all(files.map(readVideoDuration));
  const seconds = files.reduce((sum, file, index) => sum + estimateSecondsFromFile(file, durations[index]), 0);
  return { seconds, durations };
}

async function handleSelectedVideos(files) {
  if (!files.length) return;
  preview.src = URL.createObjectURL(files[0]);
  const estimate = await estimateFiles(files);
  syncResult.textContent = `已选择 ${files.length} 个视频，预计拆解耗时约 ${formatEstimate(estimate.seconds)}。现在开始自动拆解${feishuDocUrl.value.trim() ? "，拆完后会自动同步飞书原生表格。" : "。"}`;
  window.setTimeout(() => $("#analyzeBtn")?.click(), 150);
}

videoInput.addEventListener("change", async () => {
  await handleSelectedVideos([...videoInput.files]);
});

function setInputFiles(files) {
  const transfer = new DataTransfer();
  files.forEach((file) => transfer.items.add(file));
  videoInput.files = transfer.files;
}

function droppedVideoFiles(event) {
  return [...(event.dataTransfer?.files || [])].filter((file) => {
    const name = file.name.toLowerCase();
    return file.type.startsWith("video/") || [".mp4", ".mov", ".webm", ".m4v"].some((suffix) => name.endsWith(suffix));
  });
}

["dragenter", "dragover"].forEach((type) => {
  document.addEventListener(type, (event) => {
    event.preventDefault();
    uploadPanel?.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((type) => {
  document.addEventListener(type, (event) => {
    event.preventDefault();
    if (type === "drop") return;
    uploadPanel?.classList.remove("drag-over");
  });
});

document.addEventListener("drop", async (event) => {
  uploadPanel?.classList.remove("drag-over");
  const files = droppedVideoFiles(event);
  if (!files.length) {
    syncResult.textContent = "请拖入 mp4 / mov / webm / m4v 视频文件。";
    return;
  }
  setInputFiles(files);
  await handleSelectedVideos(files);
});

videoInput.addEventListener("click", () => {
  const file = videoInput.files[0];
  if (!file) preview.src = "";
});

$("#analyzeBtn").addEventListener("click", async () => {
  const file = videoInput.files[0];
  if (!file) {
    syncResult.textContent = "请先选择视频。";
    return;
  }
  setStatus("处理中");
  syncResult.textContent = "正在上传和拆镜头，视频越长耗时越久...";
  const form = new FormData();
  form.append("video", file);
  form.append("mode", currentMode);
  form.append("product_model", productModel.value || "");
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    storyboard = await response.json();
    renderTable();
    setStatus("已完成");
    syncResult.textContent = `完成：${storyboard.shots.length} 个镜头。`;
  } catch (error) {
    setStatus("失败");
    syncResult.textContent = `拆解失败：${error.message}`;
  }
});

function setupBatchAnalyzeButton() {
  const oldButton = $("#analyzeBtn");
  const button = oldButton.cloneNode(true);
  oldButton.replaceWith(button);
  button.addEventListener("click", async () => {
    if (isAnalyzing) return;
    const files = [...videoInput.files];
    if (!files.length) {
      syncResult.textContent = "请先选择视频。";
      return;
    }
    isAnalyzing = true;
    button.disabled = true;
    setStatus("处理中");
    const estimate = await estimateFiles(files);
    const startedAt = Date.now();
    syncResult.textContent = `正在处理 ${files.length} 个视频，预计还需约 ${formatEstimate(estimate.seconds)}。`;
    const results = [];
    try {
      for (let index = 0; index < files.length; index += 1) {
        const file = files[index];
        const elapsed = (Date.now() - startedAt) / 1000;
        const remainingByPlan = Math.max(1, estimate.seconds - elapsed);
        const avgDone = index > 0 ? elapsed / index : 0;
        const remainingByAverage = avgDone ? avgDone * (files.length - index) : remainingByPlan;
        const remaining = index > 0 ? remainingByAverage : remainingByPlan;
        syncResult.textContent = `正在处理 ${index + 1}/${files.length}：${file.name}\n预计剩余：约 ${formatEstimate(remaining)}。`;
        const form = new FormData();
        form.append("video", file);
        form.append("mode", currentMode);
        form.append("product_model", productModel.value || "");
        const response = await fetch("/api/analyze", { method: "POST", body: form });
        if (!response.ok) throw new Error(`${file.name}: ${await response.text()}`);
        results.push(await response.json());
      }
      storyboards = results;
      storyboard = results[0] || null;
      renderAllTables();
      setStatus("已完成");
      const elapsed = (Date.now() - startedAt) / 1000;
      syncResult.textContent = `完成：${results.length} 个视频，共 ${results.reduce((sum, item) => sum + item.shots.length, 0)} 个镜头。实际耗时 ${formatEstimate(elapsed)}。点击“复制飞书原生表格”会一次复制 ${results.length} 个标题和表格。`;
      if (feishuDocUrl.value.trim()) {
        await syncStoryboardsToFeishu({ automatic: true });
      }
    } catch (error) {
      setStatus("失败");
      syncResult.textContent = `拆解失败：${error.message}`;
    } finally {
      isAnalyzing = false;
      button.disabled = false;
    }
  });
}

setupBatchAnalyzeButton();

$("#saveBtn")?.addEventListener("click", async () => {
  if (!storyboard) return;
  setStatus("保存中");
  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(storyboard),
  });
  setStatus(response.ok ? "已保存" : "保存失败");
});

$("#copyMarkdownBtn").addEventListener("click", async () => {
  if (!storyboard) {
    syncResult.textContent = "请先拆解视频。";
    return;
  }
  const markdown = allStoryboardsMarkdownTables();
  await navigator.clipboard.writeText(markdown);
  setStatus("已复制");
  syncResult.textContent = "已复制飞书原生 Markdown 表格，可直接粘贴到普通飞书文档。";
});

copyRichTableBtn.addEventListener("click", copyRichStoryboardTable);

cacheReportBtn?.addEventListener("click", async () => {
  setStatus("检查缓存");
  const response = await fetch("/api/cache/report-file", { method: "POST" });
  const data = await response.json();
  const jobs = data.jobs || [];
  syncResult.innerHTML = `
    <div><strong>缓存清单</strong></div>
    <div>清单文件夹：${escapeHtml(data.report_dir || "")}</div>
    <div>outputs目录：${escapeHtml(data.outputs_dir || "")}</div>
    <div>任务数：${data.job_count || 0}；旧图片：${data.image_count || 0} 张；约 ${data.image_mb || 0} MB</div>
    <div class="path">Markdown：${escapeHtml(data.report_markdown || "")}</div>
    <div class="path">JSON：${escapeHtml(data.report_json || "")}</div>
    <div class="export-actions">
      <button type="button" id="openCacheDirBtn">打开缓存清单文件夹</button>
    </div>
    <ul class="file-list">
      ${jobs
        .slice(0, 20)
        .map(
          (job) => `
            <li>
              <strong>${escapeHtml(job.job_id)}</strong>：
              ${escapeHtml(String(job.image_count || 0))} 张，${escapeHtml(String(job.image_mb || 0))} MB
              <div class="path">${escapeHtml(job.frames_path || "")}</div>
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
  $("#openCacheDirBtn")?.addEventListener("click", async () => {
    await fetch("/api/cache/reveal", { method: "POST" });
  });
  setStatus("缓存清单");
});

document.querySelectorAll("[data-export]").forEach((button) => {
  button.addEventListener("click", async () => {
    if (!storyboard) {
      syncResult.textContent = "请先拆解视频。";
      return;
    }
    setStatus("导出中");
    let fmt = button.dataset.export;
    if (outputFormat.value === "tsv" || outputFormat.value === "json" || outputFormat.value === "feishu_native") {
      fmt = "md";
    }
    if (button.dataset.export === "docx") {
      fmt = "docx";
    }
    const boards = activeStoryboards();
    if (fmt === "docx" && boards.length > 1) {
      const response = await fetch("/api/export-batch/docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(boards),
      });
      if (!response.ok) {
        setStatus("导出失败");
        syncResult.textContent = await response.text();
        return;
      }
      const data = await response.json();
      setStatus("已导出");
      renderExportResult(data);
      return;
    }
    const response = await fetch(`/api/export/${fmt}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(storyboard),
    });
    if (!response.ok) {
      setStatus("导出失败");
      syncResult.textContent = await response.text();
      return;
    }
    const data = await response.json();
    setStatus("已导出");
    renderExportResult(data);
  });
});

async function syncStoryboardsToFeishu({ automatic = false } = {}) {
  const boards = activeStoryboards();
  if (!boards.length) {
    syncResult.textContent = "请先拆解视频。";
    return;
  }
  if (!feishuDocUrl.value.trim()) {
    if (!automatic) syncResult.textContent = "请先填写飞书文档 / Wiki URL。";
    return;
  }
  setStatus(automatic ? "自动同步中" : "同步中");
  const results = [];
  for (let index = 0; index < boards.length; index += 1) {
    const item = boards[index];
    const shouldCleanupAfterSync = index === boards.length - 1 && results.every((result) => result.ok);
    syncResult.textContent = `${automatic ? "拆解完成，正在自动同步飞书原生表格" : "正在同步飞书原生表格"} ${index + 1}/${boards.length}：${item.video_info?.file_name || "未命名视频"}\n会追加到目标文档末尾，不覆盖原内容。`;
    const response = await fetch("/api/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: item.job_id,
        keep_job_ids: boards.map((board) => board.job_id),
        storyboard: item,
        target: "doc",
        feishu_doc_url: feishuDocUrl.value.trim(),
        feishu_bitable_url: feishuBitableUrl?.value.trim() || "",
        feishu_user_access_token: feishuUserToken.value.trim(),
        cleanup_after_sync: shouldCleanupAfterSync,
      }),
    });
    const data = await response.json();
    results.push({ file_name: item.video_info?.file_name || `视频 ${index + 1}`, ...data });
    if (!data.ok || !response.ok) break;
  }
  const successCount = results.filter((item) => item.ok).length;
  const failedCount = results.length - successCount;
  setStatus(failedCount ? "同步异常" : "同步完成");
  if (boards.length === 1) {
    renderSyncResult(results[0]);
    return;
  }
  syncResult.innerHTML = `
    <div><strong>${automatic ? "自动" : "批量"}同步结果：${successCount}/${boards.length} 个视频成功</strong></div>
    <div class="sync-line ok">所有成功项都已追加到目标文档末尾，不覆盖原内容。</div>
    <ul class="file-list">
      ${results
        .map(
          (item) => `
            <li>
              <strong>${escapeHtml(item.file_name)}</strong>：
              <span class="${item.ok ? "sync-line ok" : "sync-line fail"}">${item.ok ? "成功" : "失败"}</span>
              ${item.errors?.length ? `<div class="sync-line fail">${escapeHtml(item.errors.join("；"))}</div>` : ""}
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
}

document.querySelectorAll("[data-sync]").forEach((button) => {
  button.addEventListener("click", () => syncStoryboardsToFeishu());
});

async function runFeishuTest(kind) {
  setStatus("测试中");
  syncResult.textContent = `正在测试${kind === "doc" ? "飞书文档" : "多维表格"}连接...`;
  const params = new URLSearchParams();
  if (kind === "doc" && feishuDocUrl.value.trim()) params.set("doc_url", feishuDocUrl.value.trim());
  if (kind === "bitable" && feishuBitableUrl?.value.trim()) params.set("bitable_url", feishuBitableUrl.value.trim());
  if (feishuUserToken.value.trim()) params.set("user_access_token", feishuUserToken.value.trim());
  const response = await fetch(`/api/feishu/test/${kind}?${params.toString()}`);
  const data = await response.json();
  setStatus(data.ok ? "测试通过" : "测试失败");
  syncResult.innerHTML = `
    <div><strong>${kind === "doc" ? "飞书文档" : "多维表格"}连接测试：${data.ok ? "通过" : "失败"}</strong></div>
    <pre class="debug-json">${escapeHtml(JSON.stringify(data.checks || data, null, 2))}</pre>
  `;
}

$("#testDocBtn").addEventListener("click", () => runFeishuTest("doc"));
$("#testBitableBtn")?.addEventListener("click", () => runFeishuTest("bitable"));
