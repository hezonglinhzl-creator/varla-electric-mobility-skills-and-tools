"use strict";

const state = {
  paused: false,
  activeView: "overview",
  tasks: [],
  manualTasks: [],
  sentTasks: [],
  audit: [],
  pendingConfirmation: null,
  classificationTask: null,
  busyTaskIds: new Set(),
  dirtyTaskIds: new Set(),
  busyCount: 0,
  activeGroupFilter: null,
};

const viewTitles = {
  overview: "今日运营总览",
  manual: "人工处理",
  sent: "已发送",
  kol: "KOL 合作组",
  junk: "垃圾清理",
  "reply-assistant": "KOL 回复助手",
  knowledge: "知识与同步",
  settings: "系统设置",
  audit: "审计记录",
};

const groupLabels = {
  kol: "KOL 合作",
  "pre-sales": "售前",
  "order-logistics": "订单物流",
  "after-sales": "售后",
  manual: "人工处理",
};

const stateLabels = {
  new: "新任务",
  classified: "已分类",
  previewed: "待确认",
  approved: "已批准",
  replied: "已回复",
  forwarded: "已转发",
  labeled: "已加标签",
  ignored: "已忽略",
  manual_review: "人工处理",
  needs_knowledge: "缺少知识",
  needs_reclassification: "需重新分类",
  retryable: "可重试",
};

const taskActionPaths = Object.freeze({
  "generate-preview": "/generate-preview",
  "save-preview": "/save-preview",
  "reclassify": "/reclassify",
  "confirm-label": "/confirm-label",
  "confirm-reply": "/confirm-reply",
  "confirm-forward": "/confirm-forward",
  "ignore": "/ignore",
  "manual-review": "/manual-review",
});

const terminalTaskStates = new Set([
  "replied",
  "forwarded",
  "ignored",
  "completed",
]);

function byId(id) {
  return document.getElementById(id);
}

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function safeText(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  if (Array.isArray(value)) return value.map((item) => safeText(item, "")).filter(Boolean).join("、") || fallback;
  if (typeof value === "object") {
    const known = value.body || value.text || value.content || value.message || value.name || value.email;
    if (known) return safeText(known, fallback);
    try {
      return JSON.stringify(value, null, 2);
    } catch (_error) {
      return fallback;
    }
  }
  return String(value);
}

function payloadOf(task) {
  return task && task.payload && typeof task.payload === "object" ? task.payload : {};
}

function previewOf(task) {
  const payload = payloadOf(task);
  const candidate = payload.preview || payload.reply_preview || payload.draft;
  return candidate ? safeText(candidate, "") : "";
}

function riskFlagsOf(task) {
  const payload = payloadOf(task);
  const flags = payload.risk_flags || payload.source_risk_flags || [];
  if (Array.isArray(flags)) return flags.map((item) => safeText(item, "")).filter(Boolean);
  return flags ? [safeText(flags, "")] : [];
}

function isHardBlocked(task) {
  const capabilities = capabilitiesOf(task);
  return capabilities.hard_blocked === true;
}

function requiresOperatorReview(task) {
  const capabilities = capabilitiesOf(task);
  return capabilities.requires_operator_override === true;
}

function citationsOf(task) {
  const payload = payloadOf(task);
  const preview = payload.preview && typeof payload.preview === "object" ? payload.preview : {};
  return payload.citations || preview.citations || payload.sources || [];
}

function knowledgeVersionOf(task) {
  const payload = payloadOf(task);
  const preview = payload.preview && typeof payload.preview === "object" ? payload.preview : {};
  return safeText(
    payload.knowledge_version ||
    preview.knowledge_version ||
    payload.source_version ||
    payload.summary,
    "本地已验证版本"
  );
}

function capabilitiesOf(task) {
  return task && task.capabilities && typeof task.capabilities === "object"
    ? task.capabilities
    : {
        can_reply: false,
        can_manual_reply: false,
        can_forward: false,
        forward_recipient: null,
        can_label: false,
        blocked_reason: "capabilities_missing",
      };
}

function gmailThreadUrl(threadId) {
  const normalized = safeText(threadId, "");
  if (!/^[0-9A-Za-z_-]+$/.test(normalized)) return null;
  return `https://mail.google.com/mail/u/0/#all/${encodeURIComponent(normalized)}`;
}

function openExternalUrl(url) {
  if (!/^https:\/\/(?:mail\.google\.com|your-workspace\.feishu\.cn)\//.test(url)) {
    showMessage("该外部入口未通过安全检查。", "error");
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

async function openServiceCard(card) {
  const url = card.dataset.serviceUrl;
  if (url) {
    openExternalUrl(url);
    return;
  }
  const target = card.dataset.localTarget;
  if (!target) return;
  await openLocalTarget(target);
}

async function openLocalTarget(target) {
  try {
    await apiFetch(`/api/system/open/${encodeURIComponent(target)}`, {
      method: "POST",
      body: {},
    });
    showMessage("已在文件资源管理器中打开对应位置。", "success");
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

function showMessage(message, tone = "info") {
  const box = byId("global-message");
  box.textContent = message;
  box.dataset.tone = tone;
  box.hidden = false;
}

function clearMessage() {
  byId("global-message").hidden = true;
}

function friendlyError(error) {
  if (error && error.userMessage) return error.userMessage;
  if (error && error.name === "TypeError") return "本地服务暂时无法连接，请确认总控台仍在运行。";
  return "操作没有完成。请刷新任务后重试，或转为人工处理。";
}

async function apiFetch(path, options = {}) {
  const request = {
    method: options.method || "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  };
  if (options.body !== undefined) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, request);
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const error = new Error("unexpected_response");
    error.userMessage = "本地服务返回了无法识别的内容，请刷新页面后重试。";
    throw error;
  }
  let data;
  try {
    data = await response.json();
  } catch (_error) {
    const error = new Error("invalid_json");
    error.userMessage = "本地服务返回的数据不完整，请稍后重试。";
    throw error;
  }
  if (!response.ok) {
    const error = new Error(`request_failed_${response.status}`);
    error.status = response.status;
    error.userMessage = safeText(data && data.detail, "操作被安全规则停止，请刷新后重试。");
    throw error;
  }
  return data;
}

async function withBusy(control, operation) {
  if (control && control.disabled) return undefined;
  state.busyCount += 1;
  if (control) {
    control.disabled = true;
    control.setAttribute("aria-busy", "true");
  }
  try {
    return await operation();
  } finally {
    state.busyCount = Math.max(0, state.busyCount - 1);
    if (control) {
      control.disabled = false;
      control.removeAttribute("aria-busy");
    }
    applyPauseState();
  }
}

function cardSafetyContext(card) {
  return {
    paused: state.paused,
    busy: state.busyTaskIds.has(card.dataset.taskId),
    dirty: state.dirtyTaskIds.has(card.dataset.taskId),
    hasDraft: card.dataset.hasDraft === "true",
    hardBlocked: card.dataset.hardBlocked === "true",
    terminal: card.dataset.terminal === "true",
    confirmable: card.dataset.confirmable === "true",
    forwardAvailable: card.dataset.forwardAvailable === "true",
    labelAvailable: card.dataset.labelAvailable === "true",
    saveAvailable: card.dataset.saveAvailable === "true",
    manualReplyAvailable: card.dataset.manualReplyAvailable === "true",
    hasPreview: card.dataset.hasPreview === "true",
  };
}

function applyTaskCardConstraints(card) {
  const context = cardSafetyContext(card);
  card.setAttribute("aria-busy", String(context.busy));
  card.querySelectorAll("[data-task-action]").forEach((button) => {
    const disabled = window.VarlaTaskSafety.buttonDisabled(
      context,
      button.dataset.taskAction
    );
    button.disabled = disabled;
    if (context.busy) button.setAttribute("aria-busy", "true");
    else button.removeAttribute("aria-busy");
  });
}

function setTaskBusy(taskId, busy) {
  if (busy) {
    if (state.busyTaskIds.has(taskId)) return false;
    state.busyTaskIds.add(taskId);
  } else {
    state.busyTaskIds.delete(taskId);
  }
  document.querySelectorAll(".task-card[data-task-id]").forEach((card) => {
    if (card.dataset.taskId === taskId) applyTaskCardConstraints(card);
  });
  return true;
}

function applyTaskConstraints(taskId) {
  document.querySelectorAll(".task-card[data-task-id]").forEach((card) => {
    if (card.dataset.taskId === taskId) applyTaskCardConstraints(card);
  });
}

function setTaskDirty(taskId, card, dirty) {
  card.dataset.previewDirty = String(dirty);
  card.dataset.hasDraft = String(dirty);
  if (dirty) state.dirtyTaskIds.add(taskId);
  else state.dirtyTaskIds.delete(taskId);
  applyTaskConstraints(taskId);
}

function discardTaskDraft(taskId) {
  document.querySelectorAll(".task-card[data-task-id]").forEach((card) => {
    if (card.dataset.taskId !== taskId) return;
    const editor = card.querySelector(".preview-editor");
    if (editor && card.dataset.hasDraft === "true") {
      editor.value = editor.dataset.originalValue;
      const note = card.querySelector(".preview-dirty");
      if (note) note.hidden = true;
    }
    card.dataset.previewDirty = "false";
    card.dataset.hasDraft = "false";
  });
  state.dirtyTaskIds.delete(taskId);
  applyTaskConstraints(taskId);
  showMessage("已放弃未保存修改，恢复为服务器中的预览。", "info");
}

function confirmDiscardAllDrafts(message) {
  if (state.dirtyTaskIds.size === 0) return true;
  if (!window.confirm(message)) return false;
  Array.from(state.dirtyTaskIds).forEach(discardTaskDraft);
  return true;
}

async function withTaskBusy(task, operation) {
  if (!setTaskBusy(task.id, true)) {
    showMessage("该任务已有操作正在执行，请等待完成。", "error");
    return undefined;
  }
  try {
    return await operation();
  } finally {
    setTaskBusy(task.id, false);
    applyPauseState();
  }
}

function setServiceStatus(name, tone, detail) {
  const card = document.querySelector(`[data-service="${name}"]`);
  if (!card) return;
  const dot = card.querySelector(".status-dot");
  const label = card.querySelector("em");
  dot.className = `status-dot status-dot--${tone}`;
  label.textContent = detail;
}

function applyPauseState() {
  const pauseButton = byId("pause-button");
  pauseButton.textContent = state.paused ? "全部恢复" : "全部暂停";
  pauseButton.classList.toggle("button--danger-quiet", !state.paused);
  pauseButton.classList.toggle("button--primary", state.paused);
  document.querySelectorAll(
    "#recognize-button, #sync-button, #junk-cleanup-button"
  ).forEach((button) => {
    button.disabled = state.paused || button.getAttribute("aria-busy") === "true";
  });
  document.querySelectorAll(".task-card[data-task-id]").forEach(
    applyTaskCardConstraints
  );
  document.body.dataset.paused = String(state.paused);
}

function switchView(view) {
  if (!viewTitles[view]) return;
  if (
    view !== state.activeView &&
    !confirmDiscardAllDrafts(
      "仍有未保存的回复修改。切换页面将放弃这些修改，确定继续吗？"
    )
  ) {
    return;
  }
  state.activeView = view;
  document.querySelectorAll(".nav-item").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.panel === view);
  });
  byId("view-title").textContent = viewTitles[view];
  if (view === "audit") loadAudit();
  if (view === "manual") loadManual();
  if (view === "sent") {
    const refresh = document.querySelector('[data-refresh-list="sent"]');
    syncSentTasks(refresh);
  }
  if (view === "kol") loadKol();
  byId("main-content").focus({ preventScroll: true });
}

function appendFact(list, label, value) {
  const row = makeElement("div");
  row.append(makeElement("dt", "", label), makeElement("dd", "", safeText(value)));
  list.append(row);
}

function makeBadge(text, tone = "") {
  return makeElement("span", `badge${tone ? ` badge--${tone}` : ""}`, text);
}

function actionButton(label, action, className = "") {
  const button = makeElement("button", `button ${className}`.trim(), label);
  button.type = "button";
  button.dataset.taskAction = action;
  return button;
}

function makeTaskCard(task, options = {}) {
  const readOnly = options.readOnly === true;
  const hardBlocked = isHardBlocked(task);
  const reviewRequired = requiresOperatorReview(task);
  const payload = payloadOf(task);
  const decision = payload.decision && typeof payload.decision === "object"
    ? payload.decision
    : {};
  const relevance = payload.preview &&
    typeof payload.preview === "object" &&
    payload.preview.relevance &&
    typeof payload.preview.relevance === "object"
    ? payload.preview.relevance
    : {};
  const capabilities = capabilitiesOf(task);
  const card = makeElement("article", "task-card");
  card.dataset.taskId = safeText(task.id, "");
  card.dataset.hardBlocked = String(hardBlocked);
  card.dataset.previewDirty = "false";
  card.dataset.hasDraft = "false";
  card.dataset.terminal = String(terminalTaskStates.has(task.state));
  card.dataset.confirmable = String(
    capabilities.can_reply === true || capabilities.can_forward === true
  );
  card.dataset.forwardAvailable = String(capabilities.can_forward === true);
  card.dataset.labelAvailable = String(capabilities.can_label === true);
  card.dataset.saveAvailable = String(task.state === "previewed");
  card.dataset.manualReplyAvailable = String(
    capabilities.can_manual_reply === true
  );

  const header = makeElement("header", "task-card__header");
  const titleBlock = makeElement("div");
  const taskTime = window.VarlaTaskDisplay.formatTaskTime(task);
  titleBlock.append(
    makeElement("p", "eyebrow", safeText(payload.sender || payload.from, "未知发件人")),
    makeElement("h4", "", safeText(payload.subject, "无主题邮件")),
    makeElement("p", "", safeText(payload.snippet, "等待读取邮件摘要"))
  );
  titleBlock.insertBefore(
    makeElement("p", "task-message-time", `${taskTime.label}：${taskTime.value}`),
    titleBlock.children[1]
  );
  const meta = makeElement("div", "task-card__meta");
  meta.append(
    makeBadge(groupLabels[task.group] || safeText(task.group, "未分类"), task.group === "kol" ? "green" : "amber"),
    makeBadge(stateLabels[task.state] || safeText(task.state), hardBlocked ? "red" : "")
  );
  if (reviewRequired) meta.append(makeBadge("需人工确认", "amber"));
  if (hardBlocked) meta.append(makeBadge("安全阻断", "red"));
  header.append(titleBlock, meta);

  const incomingMessage = makeElement("details", "incoming-message");
  const incomingSummary = makeElement("summary", "", "查看对方完整消息");
  const incomingBody = makeElement(
    "pre",
    "incoming-message__body",
    safeText(payload.message_body, "未保存可展示的正文")
  );
  incomingMessage.append(incomingSummary, incomingBody);

  const body = makeElement("div", "task-card__body");
  const facts = makeElement("dl", "task-facts");
  appendFact(
    facts,
    "AI 置信度",
    decision.confidence !== undefined
      ? `${Math.round(Number(decision.confidence) * 100)}%`
      : "—"
  );
  appendFact(facts, "合作阶段", decision.stage_id);
  appendFact(facts, "判断依据", decision.evidence);
  appendFact(
    facts,
    "内容对应检查",
    relevance.status === "matched"
      ? "对应问题"
      : relevance.status === "manual_review"
        ? "答复不完整或包含未询问内容"
        : "尚未检查"
  );
  appendFact(facts, "遗漏问题", relevance.missing_intents);
  appendFact(facts, "额外内容", relevance.unsupported_intents);
  appendFact(facts, "Gmail 标签", payload.labels);
  appendFact(facts, "风险标记", riskFlagsOf(task));
  appendFact(facts, "知识引用", citationsOf(task));

  const previewBox = makeElement("div", "preview-box");
  const editorId = `preview-${safeText(task.id, "task")}`;
  const editorLabel = makeElement("label", "", "回复预览编辑器");
  editorLabel.htmlFor = editorId;
  const editor = makeElement("textarea", "preview-editor");
  editor.id = editorId;
  editor.value = previewOf(task);
  editor.placeholder = "请在这里手动输入回复内容";
  editor.readOnly = readOnly;
  editor.dataset.originalValue = editor.value;
  card.dataset.hasPreview = String(Boolean(editor.value.trim()));
  editor.setAttribute("aria-describedby", `${editorId}-note`);
  const dirtyNote = makeElement("p", "preview-dirty", "当前修改可直接发送；系统会在后台保存正文、重读邮件并检查硬性风险。");
  dirtyNote.id = `${editorId}-note`;
  dirtyNote.hidden = true;
  editor.addEventListener("input", () => {
    const dirty = editor.value !== editor.dataset.originalValue;
    dirtyNote.hidden = !dirty;
    setTaskDirty(task.id, card, dirty);
  });
  previewBox.append(editorLabel, editor, dirtyNote);
  body.append(facts, previewBox);

  const actions = makeElement("footer", "task-card__actions");
  const gmailUrl = gmailThreadUrl(task.gmail_thread_id);
  if (gmailUrl) {
    const gmailButton = actionButton("在 Gmail 中查看", "open-gmail", "action-gmail");
    gmailButton.dataset.gmailUrl = gmailUrl;
    actions.append(gmailButton);
  }
  if (!readOnly) {
    actions.append(
      actionButton("生成并预览", "generate-preview"),
      actionButton("保存修改", "save-preview"),
      actionButton("放弃修改", "discard-preview"),
      actionButton("重新分类", "reclassify")
    );
    if (capabilities.can_label) actions.append(actionButton("确认 KOL 标签", "confirm-label"));
    if (capabilities.can_reply) {
      actions.append(actionButton("确认回复", "confirm-reply", "action-confirm"));
    } else if (capabilities.can_manual_reply) {
      actions.append(actionButton("直接发送", "confirm-manual-reply", "action-confirm"));
    }
    if (capabilities.can_forward) {
      actions.append(actionButton("确认转发", "confirm-forward", "action-forward"));
    }
    actions.append(actionButton("忽略", "ignore"));
    if (task.state !== "manual_review") {
      actions.append(actionButton("人工处理", "manual-review", "action-manual"));
    }
  }
  actions.addEventListener("click", (event) => {
    const button = event.target.closest("[data-task-action]");
    if (!button) return;
    if (button.dataset.taskAction === "open-gmail") {
      openExternalUrl(button.dataset.gmailUrl || "");
      return;
    }
    handleTaskAction(task, button.dataset.taskAction, button, card);
  });

  card.append(header, incomingMessage, body, actions);
  return card;
}

function renderTaskList(container, tasks, emptyTitle = "当前没有待确认任务", options = {}) {
  container.replaceChildren();
  if (!tasks.length) {
    const empty = makeElement("div", "empty-state");
    empty.append(
      makeElement("strong", "", emptyTitle),
      makeElement("span", "", "点击“开始识别”或“刷新列表”获取最新状态。")
    );
    container.append(empty);
    return;
  }
  tasks.forEach((task) => container.append(makeTaskCard(task, options)));
  applyPauseState();
}

function updateCounts(tasks) {
  const counts = { kol: 0, "pre-sales": 0, "order-logistics": 0, "after-sales": 0 };
  tasks.forEach((task) => {
    if (Object.hasOwn(counts, task.group)) counts[task.group] += 1;
  });
  byId("count-kol").textContent = String(counts.kol);
  byId("count-pre").textContent = String(counts["pre-sales"]);
  byId("count-order").textContent = String(counts["order-logistics"]);
  byId("count-after").textContent = String(counts["after-sales"]);
}

function renderOverviewTasks() {
  const filtered = state.activeGroupFilter
    ? state.tasks.filter((task) => task.group === state.activeGroupFilter)
    : state.tasks;
  renderTaskList(
    byId("task-list"),
    filtered,
    state.activeGroupFilter
      ? `当前没有${groupLabels[state.activeGroupFilter] || "该分类"}任务`
      : "当前没有待确认任务"
  );
  document.querySelectorAll("[data-group-filter]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.groupFilter === state.activeGroupFilter)
    );
  });
}

function toggleGroupFilter(group) {
  if (!Object.hasOwn(groupLabels, group) || group === "manual") return;
  state.activeGroupFilter = state.activeGroupFilter === group ? null : group;
  renderOverviewTasks();
}

async function loadStatus() {
  try {
    const status = await apiFetch("/api/status");
    state.paused = Boolean(status.paused);
    setServiceStatus("database", status.local_only ? "safe" : "danger", status.local_only ? "本地可用" : "异常");
    if (status.control_state_error) showMessage(status.control_state_error, "error");
    applyPauseState();
  } catch (error) {
    setServiceStatus("database", "danger", "无法连接");
    showMessage(friendlyError(error), "error");
  }
}

async function loadTasks() {
  try {
    const tasks = await apiFetch("/api/tasks?pending_only=true&limit=50");
    if (state.dirtyTaskIds.size > 0) return;
    state.tasks = tasks;
    renderOverviewTasks();
    updateCounts(state.tasks);
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

async function loadManual() {
  try {
    const tasks = await apiFetch("/api/tasks?state=manual_review&limit=50");
    if (state.dirtyTaskIds.size > 0) return;
    state.manualTasks = tasks;
    byId("manual-count").textContent = String(tasks.length);
    renderTaskList(byId("manual-list"), tasks, "当前没有人工处理任务");
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

async function loadSent() {
  try {
    const tasks = await apiFetch("/api/tasks?state=completed&limit=50");
    state.sentTasks = tasks;
    byId("sent-count").textContent = String(tasks.length);
    renderTaskList(
      byId("sent-list"),
      tasks,
      "当前没有已发送任务",
      { readOnly: true }
    );
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

async function syncSentTasks(button) {
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/tasks/sync-sent", {
        method: "POST",
        body: {},
      });
      await Promise.all([loadTasks(), loadManual(), loadSent()]);
      if (state.activeView === "kol") await loadKol();
      const checked = safeText(result && result.checked, "0");
      const synced = safeText(result && result.synced, "0");
      const failed = Number(result && result.failed) || 0;
      showMessage(
        `已核对最近 30 天 ${checked} 个已发送线程，新增同步 ${synced} 个；同一邮箱仅显示最新一封。${failed ? ` ${failed} 个线程读取失败。` : ""}`,
        failed > 0 ? "error" : "success"
      );
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function loadKol() {
  try {
    const tasks = await apiFetch("/api/tasks?group=kol&pending_only=true&limit=50");
    if (state.dirtyTaskIds.size > 0) return;
    renderTaskList(byId("kol-list"), tasks, "当前没有 KOL 合作任务");
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

async function refreshAll() {
  await Promise.all([loadStatus(), loadTasks(), loadManual(), loadSent()]);
  if (state.activeView === "kol") await loadKol();
}

async function reconcilePendingTasks(button) {
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/tasks/reconcile-pending", {
        method: "POST",
        body: {},
      });
      await refreshAll();
      const checked = safeText(result && result.checked, "0");
      const answered = safeText(result && result.answered, "0");
      const failed = Number(result && result.failed) || 0;
      const retry = failed > 0 ? `，${failed} 个线程读取失败并已保留` : "";
      showMessage(
        `已核对 ${checked} 个待处理邮件线程，隐藏 ${answered} 个已回复任务${retry}。`,
        failed > 0 ? "error" : "success"
      );
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function startRecognition(button) {
  if (!confirmDiscardAllDrafts(
    "识别完成后会刷新任务列表并放弃未保存修改，确定继续吗？"
  )) return;
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/recognize", {
        method: "POST",
        body: {},
      });
      const created = result && result.created !== undefined ? `，新增 ${safeText(result.created, "0")} 项` : "";
      const duplicates = result && result.duplicates !== undefined ? `，已存在 ${safeText(result.duplicates, "0")} 项` : "";
      const skipped = result && result.skipped !== undefined ? `，跳过 ${safeText(result.skipped, "0")} 项` : "";
      const autoTrashed = result && result.auto_trashed !== undefined
        ? `，已移入垃圾箱 ${safeText(result.auto_trashed, "0")} 项`
        : "";
      const blockedSenders = result && Number(result.blocked_senders) > 0
        ? `，已拉黑发件人 ${safeText(result.blocked_senders, "0")} 个`
        : "";
      const trashFailed = result && Number(result.trash_failed) > 0
        ? `，移入垃圾箱失败 ${safeText(result.trash_failed, "0")} 项（已转人工）`
        : "";
      const alignment = result && result.preview_alignment;
      const generated = alignment
        ? `，自动生成预览 ${safeText(alignment.generated, "0")} 项`
        : "";
      const matched = alignment
        ? `，内容已对齐 ${safeText(alignment.matched, "0")} 项`
        : "";
      const manual = alignment
        ? `，需人工复核 ${safeText(alignment.manual_review, "0")} 项`
        : "";
      showMessage(
        `最近30天合作邮件识别完成${created}${duplicates}${skipped}${autoTrashed}${blockedSenders}${trashFailed}${generated}${matched}${manual}。发送仍需逐条人工确认。`,
        "success"
      );
      await refreshAll();
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

function renderJunkCleanupResult(result) {
  byId("junk-checked").textContent = safeText(result && (result.candidates ?? result.checked), "0");
  byId("junk-auto-trashed").textContent = safeText(result && result.auto_trashed, "0");
  byId("junk-ambiguous-kept").textContent = safeText(result && result.ambiguous_kept, "0");
  byId("junk-trash-failed").textContent = safeText(result && (result.failed ?? result.trash_failed), "0");
}

async function runJunkCleanup(button) {
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/junk/cleanup", {
        method: "POST",
        body: {},
      });
      renderJunkCleanupResult(result);
      await refreshAll();
      const moved = safeText(result && result.auto_trashed, "0");
      const kept = safeText(result && result.ambiguous_kept, "0");
      const failed = Number(result && (result.failed ?? result.trash_failed)) || 0;
      showMessage(
        `垃圾清理完成：${moved} 封已移入可恢复的 Gmail 垃圾箱，${kept} 封模糊邮件已保留${failed ? `，${failed} 封处理失败` : ""}。`,
        failed ? "error" : "success"
      );
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function syncFeishu(button) {
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/feishu/sync", {
        method: "POST",
        body: { force: true },
      });
      const unavailable = ["unavailable", "error", "failed"].includes(result.status);
      setServiceStatus("feishu", unavailable ? "danger" : "safe", unavailable ? "不可用，本地库继续工作" : "同步检查完成");
      showMessage(unavailable ? "飞书暂不可用，已继续使用本地知识库。" : "飞书同步检查已完成。", unavailable ? "error" : "success");
    } catch (error) {
      setServiceStatus("feishu", "danger", "本地库继续工作");
      showMessage(`${friendlyError(error)} 本地知识库仍可使用。`, "error");
    }
  });
}

function healthTone(record) {
  const status = safeText(record && record.status, "").toLowerCase();
  return ["ok", "healthy", "ready", "available"].includes(status) ? "safe" : "danger";
}

function healthLabel(name, record) {
  const status = safeText(record && record.status, "").toLowerCase();
  if (healthTone(record) === "safe") return "可用";
  if (name === "reply" && (record && (record.drift === true || status === "drift"))) {
    return "版本待确认";
  }
  if (status === "unavailable") return "未安装或不可用";
  return "需检查";
}

function findHealthRecord(result, fragments) {
  if (!result || typeof result !== "object") return null;
  const key = Object.keys(result).find((candidate) =>
    fragments.some((fragment) => candidate.toLowerCase().includes(fragment))
  );
  return key ? result[key] : null;
}

function renderHealthResult(result) {
  const gmail = findHealthRecord(result, ["gmail"]);
  const reply = findHealthRecord(result, ["reply"]);
  const contract = findHealthRecord(result, ["contract"]);
  [
    ["gmail", gmail],
    ["reply", reply],
    ["contract", contract],
  ].forEach(([name, record]) => {
    setServiceStatus(name, healthTone(record), healthLabel(name, record));
  });
  return [gmail, reply, contract].some((record) => healthTone(record) !== "safe");
}

async function runHealth(button, options = {}) {
  if (options.clear !== false) clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/system/health", { method: "POST", body: {} });
      const hasBlockedComponent = renderHealthResult(result);
      showMessage(
        hasBlockedComponent
          ? "检测到组件更新或异常；请点击“验证并接受组件更新”，未通过的组件仍会保持停用。"
          : "外部服务检查完成，请查看顶部状态卡；点击状态卡可进入邮箱或文件位置。",
        hasBlockedComponent ? "error" : "success"
      );
    } catch (error) {
      ["gmail", "reply", "contract"].forEach((name) => setServiceStatus(name, "danger", "自检失败"));
      showMessage(friendlyError(error), "error");
    }
  });
}

async function togglePause(button) {
  await withBusy(button, async () => {
    const route = state.paused ? "/api/system/resume" : "/api/system/pause";
    try {
      const result = await apiFetch(route, { method: "POST", body: {} });
      state.paused = Boolean(result.paused);
      showMessage(state.paused ? "系统已全部暂停。只读查看和自检仍可使用。" : "系统已恢复人工点击模式。", state.paused ? "info" : "success");
      applyPauseState();
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function runDirectTaskAction(task, action, button, body, card = null) {
  const actionPath = taskActionPaths[action];
  if (!actionPath) {
    showMessage("未知操作已被安全规则阻止。", "error");
    return;
  }
  await withTaskBusy(task, async () => {
    try {
      const result = await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}${actionPath}`, {
        method: "POST",
        body,
      });
      if (
        action === "generate-preview" &&
        result &&
        ["previewed", "manual_review"].includes(result.status) &&
        result.preview &&
        typeof result.preview.body === "string" &&
        card
      ) {
        const editor = card.querySelector(".preview-editor");
        const previewBox = card.querySelector(".preview-box");
        if (editor && previewBox) {
          editor.value = result.preview.body;
          editor.dataset.originalValue = result.preview.body;
          card.dataset.hasDraft = "true";
          card.dataset.hasPreview = "true";
          card.dataset.confirmable = result.status === "previewed" ? "true" : "false";
          if (typeof result.updated_at === "string") task.updated_at = result.updated_at;
          if (!task.payload || typeof task.payload !== "object") task.payload = {};
          task.payload.preview = result.preview;
          previewBox.classList.add("is-revealed");
          editor.focus();
          editor.scrollIntoView({ behavior: "smooth", block: "center" });
          window.setTimeout(() => previewBox.classList.remove("is-revealed"), 1800);
          applyTaskCardConstraints(card);
        }
        showMessage(
          result.status === "previewed"
            ? "回复内容已生成并显示在右侧，请先人工核对。"
            : "已生成参考内容并显示在右侧。本邮件需人工复核，系统不会直接发送。",
          result.status === "previewed" ? "success" : "info",
        );
        return;
      }
      showMessage("操作已完成，任务状态已刷新。", "success");
      await refreshAll();
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function saveEditedPreview(task, button, card) {
  const editor = card.querySelector(".preview-editor");
  if (!editor || card.dataset.previewDirty !== "true") return;
  const preview = payloadOf(task).preview;
  const previewHash = preview && typeof preview === "object"
    ? preview.body_sha256
    : null;
  await withTaskBusy(task, async () => {
    try {
      await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/save-preview`, {
        method: "POST",
        body: {
          body: editor.value,
          expected_updated_at: task.updated_at,
          expected_preview_hash: previewHash,
        },
      });
      state.dirtyTaskIds.delete(task.id);
      showMessage("修改已保存。发送前仍会重新读取邮件并执行知识与风险检查。", "success");
      await refreshAll();
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

async function acceptHealthUpdates(button) {
  clearMessage();
  await withBusy(button, async () => {
    try {
      const result = await apiFetch("/api/system/health/accept", {
        method: "POST",
        body: {},
      });
      const hasBlockedComponent = renderHealthResult(result);
      showMessage(
        hasBlockedComponent
          ? "组件验证未全部通过，未通过的组件仍保持停用。"
          : "组件更新已验证并接受，Gmail、回复助手和合同工具均可用。",
        hasBlockedComponent ? "error" : "success"
      );
    } catch (error) {
      showMessage(friendlyError(error), "error");
    }
  });
}

function removeTaskFromPendingViews(taskId) {
  state.tasks = state.tasks.filter((item) => item.id !== taskId);
  document.querySelectorAll(`.task-card[data-task-id="${CSS.escape(taskId)}"]`).forEach((card) => {
    card.remove();
  });
  updateCounts(state.tasks);
  if (state.activeView === "overview") renderOverviewTasks();
}

function currentReplySnapshot(task, card, forceManual = false) {
  if (state.paused) {
    showMessage("系统已暂停，请先点击“全部恢复”。", "error");
    return null;
  }
  if (isHardBlocked(task)) {
    showMessage("该任务包含硬性安全问题，不能执行外发操作。", "error");
    return null;
  }
  const capabilities = capabilitiesOf(task);
  const preview = payloadOf(task).preview;
  const previewHash = preview && typeof preview === "object"
    ? preview.body_sha256
    : null;
  const editor = card ? card.querySelector(".preview-editor") : null;
  const dirty = Boolean(card && card.dataset.previewDirty === "true");
  const manual = forceManual || dirty;
  if (manual) {
    const body = editor && typeof editor.value === "string"
      ? editor.value
      : "";
    if (
      capabilities.can_manual_reply !== true ||
      !body.trim() ||
      typeof task.updated_at !== "string"
    ) {
      showMessage("请先填写完整回复内容；只有硬性风险会阻止手动发送。", "error");
      return null;
    }
    return {
      manual: true,
      body,
      expected_updated_at: task.updated_at,
      expected_preview_hash: typeof previewHash === "string" ? previewHash : null,
    };
  }
  if (
    capabilities.can_reply !== true ||
    typeof previewHash !== "string" ||
    typeof task.updated_at !== "string"
  ) {
    showMessage(
      safeText(capabilities.blocked_reason, "任务快照已变化，请刷新后重新预览。"),
      "error"
    );
    return null;
  }
  return {
    manual: false,
    expected_updated_at: task.updated_at,
    expected_preview_hash: previewHash,
    operator_override: true,
  };
}

async function confirmReplyInBackground(task, card, forceManual = false) {
  const snapshot = currentReplySnapshot(task, card, forceManual);
  if (!snapshot || !setTaskBusy(task.id, true)) return;
  state.dirtyTaskIds.delete(task.id);
  removeTaskFromPendingViews(task.id);
  showMessage("回复已交给后台处理；完成后会出现在“已发送”。", "success");
  try {
    let confirmation = snapshot;
    if (snapshot.manual) {
      const saved = await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/save-preview`, {
        method: "POST",
        body: {
          body: snapshot.body,
          expected_updated_at: snapshot.expected_updated_at,
          expected_preview_hash: snapshot.expected_preview_hash,
          operator_override: true,
        },
      });
      const savedHash = saved && saved.preview && saved.preview.body_sha256;
      if (
        !["previewed", "manual_review"].includes(String(saved?.status || "")) ||
        typeof saved?.updated_at !== "string" ||
        typeof savedHash !== "string"
      ) {
        throw new Error("manual_preview_not_saved");
      }
      confirmation = {
        expected_updated_at: saved.updated_at,
        expected_preview_hash: savedHash,
        operator_override: true,
      };
    }
    const result = await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/confirm-reply`, {
      method: "POST",
      body: confirmation,
    });
    if (!["sent", "already_completed"].includes(String(result?.status || ""))) {
      showMessage("Gmail 未确认发送，任务已返回待处理或人工处理，请检查。", "error");
      return;
    }
    showMessage("回复已发送，并已归入“已发送”。", "success");
  } catch (error) {
    showMessage(`后台回复未完成：${friendlyError(error)} 任务已恢复或转入人工处理。`, "error");
  } finally {
    setTaskBusy(task.id, false);
    await refreshAll();
  }
}

async function ignoreTaskInBackground(task) {
  if (!setTaskBusy(task.id, true)) return;
  state.dirtyTaskIds.delete(task.id);
  removeTaskFromPendingViews(task.id);
  showMessage("已忽略当前邮件，正在后台保存状态。", "success");
  try {
    const result = await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/ignore`, {
      method: "POST",
      body: {
        reason: "用户在本地总控台确认忽略",
        expected_updated_at: task.updated_at || null,
      },
    });
    if (String(result?.status || "") !== "ignored") {
      throw new Error("ignore_not_confirmed");
    }
  } catch (error) {
    showMessage(`忽略未完成：${friendlyError(error)} 当前任务将恢复显示。`, "error");
  } finally {
    setTaskBusy(task.id, false);
    await refreshAll();
  }
}

async function moveTaskToManualInBackground(task, card) {
  if (card && card.dataset.previewDirty === "true") {
    showMessage("请先保存或放弃当前修改，再转人工处理。", "error");
    return;
  }
  if (!setTaskBusy(task.id, true)) return;
  removeTaskFromPendingViews(task.id);
  const manualTask = { ...task, state: "manual_review" };
  state.manualTasks = [
    manualTask,
    ...state.manualTasks.filter((item) => item.id !== task.id),
  ];
  byId("manual-count").textContent = String(state.manualTasks.length);
  if (state.activeView === "manual") {
    renderTaskList(byId("manual-list"), state.manualTasks, "当前没有人工处理任务");
  }
  showMessage("该邮件已移入“人工处理”，正在后台保存状态。", "success");
  try {
    await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/manual-review`, {
      method: "POST",
      body: {
        reason: "用户在本地总控台要求人工处理",
        expected_updated_at: task.updated_at || null,
      },
    });
  } catch (error) {
    showMessage(`转人工处理未完成：${friendlyError(error)}`, "error");
  } finally {
    setTaskBusy(task.id, false);
    await refreshAll();
  }
}

function openClassification(task) {
  state.classificationTask = task;
  byId("classification-group").value = groupLabels[task.group] ? task.group : "manual";
  byId("classification-reason").value = "人工复核后调整分类";
  byId("classification-dialog").showModal();
  byId("classification-group").focus();
}

async function openConfirmation(task, action, card) {
  if (state.paused) {
    showMessage("系统已暂停，请先点击“全部恢复”。", "error");
    return;
  }
  if (isHardBlocked(task)) {
    showMessage("该任务包含发件人或来源硬性安全问题，不能执行外发操作。", "error");
    return;
  }
  if (card && card.dataset.previewDirty === "true") {
    showMessage("回复预览已在页面修改但未写回后台。为避免发送错版，请重新生成预览。", "error");
    return;
  }
  if (!setTaskBusy(task.id, true)) {
    showMessage("该任务已有操作正在执行，请等待完成。", "error");
    return;
  }
  let fresh;
  try {
    fresh = await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}`);
  } catch (error) {
    setTaskBusy(task.id, false);
    showMessage(friendlyError(error), "error");
    return;
  }
  const capabilities = capabilitiesOf(fresh);
  const allowed = action === "reply"
    ? capabilities.can_reply === true
    : capabilities.can_forward === true;
  const freshPreview = payloadOf(fresh).preview;
  const body = freshPreview && typeof freshPreview === "object"
    ? freshPreview.body
    : null;
  const previewHash = freshPreview && typeof freshPreview === "object"
    ? freshPreview.body_sha256
    : null;
  if (
    !allowed ||
    typeof body !== "string" ||
    typeof previewHash !== "string" ||
    typeof fresh.updated_at !== "string"
  ) {
    setTaskBusy(task.id, false);
    showMessage(
      safeText(capabilities.blocked_reason, "任务快照已变化，请刷新后重新预览。"),
      "error"
    );
    return;
  }
  const recipient = action === "forward"
    ? capabilities.forward_recipient
    : safeText(payloadOf(fresh).sender || payloadOf(fresh).from, "原邮件发件人");
  state.pendingConfirmation = {
    task: fresh,
    action,
    expectedUpdatedAt: fresh.updated_at,
    expectedPreviewHash: previewHash,
  };
  byId("confirm-title").textContent = action === "reply" ? "确认回复" : "确认转发";
  document.querySelector("[data-confirm-recipient-label]").textContent = action === "reply"
    ? "回复对象"
    : "转发对象";
  document.querySelector("[data-confirm-recipient]").textContent = recipient;
  document.querySelector("[data-confirm-content]").textContent = body;
  document.querySelector("[data-confirm-knowledge]").textContent = knowledgeVersionOf(fresh);
  document.querySelector("[data-confirm-hash]").textContent = previewHash;
  const flags = riskFlagsOf(fresh);
  document.querySelector("[data-confirm-warnings]").textContent = flags.length
    ? `需人工复核：${flags.join("、")}`
    : "未发现硬性阻断项；仍需人工核对完整内容。";
  const confirmationError = document.querySelector("[data-confirm-error]");
  confirmationError.hidden = true;
  confirmationError.textContent = "";
  const finalButton = byId("final-confirm-button");
  finalButton.disabled = false;
  finalButton.textContent = action === "reply" ? "确认并直接回复" : "确认并直接转发";
  byId("confirm-dialog").showModal();
  finalButton.focus();
}

async function executeConfirmation(button) {
  const pending = state.pendingConfirmation;
  if (!pending) return;
  const endpoint = pending.action === "reply" ? "/confirm-reply" : "/confirm-forward";
  await withBusy(button, async () => {
    const dialog = byId("confirm-dialog");
    dialog.setAttribute("aria-busy", "true");
    dialog.querySelectorAll('[value="cancel"]').forEach((control) => {
      control.disabled = true;
    });
    try {
      await apiFetch(`/api/tasks/${encodeURIComponent(pending.task.id)}${endpoint}`, {
        method: "POST",
        body: {
          expected_updated_at: pending.expectedUpdatedAt,
          expected_preview_hash: pending.expectedPreviewHash,
          operator_override: true,
        },
      });
      showMessage(pending.action === "reply" ? "回复已完成并写入审计记录。" : "转发已完成并写入审计记录。", "success");
      dialog.close();
      await refreshAll();
    } catch (error) {
      const message = friendlyError(error);
      const confirmationError = document.querySelector("[data-confirm-error]");
      confirmationError.textContent = `未发送到 Gmail：${message}`;
      confirmationError.hidden = false;
      showMessage(message, "error");
      button.textContent = pending.action === "reply" ? "确认并直接回复" : "确认并直接转发";
    } finally {
      dialog.removeAttribute("aria-busy");
      dialog.querySelectorAll('[value="cancel"]').forEach((control) => {
        control.disabled = false;
      });
    }
  });
}

function handleTaskAction(task, action, button, card) {
  clearMessage();
  if (action === "generate-preview") {
    runDirectTaskAction(task, action, button, {
      tone: "natural",
      expected_updated_at: task.updated_at || null,
    }, card);
  } else if (action === "save-preview") {
    saveEditedPreview(task, button, card);
  } else if (action === "discard-preview") {
    discardTaskDraft(task.id);
  } else if (action === "reclassify") {
    openClassification(task);
  } else if (action === "confirm-label") {
    runDirectTaskAction(task, action, button, {
      expected_updated_at: task.updated_at || null,
    });
  } else if (action === "confirm-reply") {
    void confirmReplyInBackground(task, card);
  } else if (action === "confirm-manual-reply") {
    void confirmReplyInBackground(task, card, true);
  } else if (action === "confirm-forward") {
    openConfirmation(task, "forward", card);
  } else if (action === "ignore") {
    void ignoreTaskInBackground(task);
  } else if (action === "manual-review") {
    void moveTaskToManualInBackground(task, card);
  }
}

async function submitClassification(event) {
  event.preventDefault();
  const task = state.classificationTask;
  if (!task) return;
  const button = byId("classification-submit");
  await withTaskBusy(task, async () => {
    await withBusy(button, async () => {
      try {
        await apiFetch(`/api/tasks/${encodeURIComponent(task.id)}/reclassify`, {
          method: "POST",
          body: {
            group: byId("classification-group").value,
            reason: byId("classification-reason").value.trim(),
            expected_updated_at: task.updated_at || null,
          },
        });
        byId("classification-dialog").close();
        state.classificationTask = null;
        showMessage("分类已更新，请重新生成并检查预览。", "success");
        await refreshAll();
      } catch (error) {
        showMessage(friendlyError(error), "error");
      }
    });
  });
}

async function loadAudit() {
  try {
    state.audit = await apiFetch("/api/audit?limit=50");
    const body = byId("audit-list");
    body.replaceChildren();
    if (!state.audit.length) {
      const row = makeElement("tr");
      const cell = makeElement("td", "", "尚无审计记录");
      cell.colSpan = 5;
      row.append(cell);
      body.append(row);
      return;
    }
    state.audit.forEach((record) => {
      const row = makeElement("tr");
      [
        record.created_at,
        record.action,
        record.actor,
        record.task_id,
        record.details,
      ].forEach((value) => row.append(makeElement("td", "", safeText(value))));
      body.append(row);
    });
  } catch (error) {
    showMessage(friendlyError(error), "error");
  }
}

function handleRiskAction(action) {
  if (action === "refresh") {
    if (confirmDiscardAllDrafts(
      "刷新任务将放弃未保存修改，确定继续吗？"
    )) refreshAll();
  }
  else if (action === "knowledge" || action === "routes") switchView("knowledge");
  else if (action === "issues") switchView("manual");
  else if (action === "audit") switchView("audit");
  else if (action === "sync") syncFeishu(byId("sync-button"));
}

function tickClock() {
  byId("local-clock").textContent = new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
}

function bindEvents() {
  document.querySelectorAll("[data-group-filter]").forEach((button) => {
    button.addEventListener("click", () => toggleGroupFilter(button.dataset.groupFilter));
  });
  document.querySelectorAll(".service-status--clickable").forEach((card) => {
    card.addEventListener("click", () => openServiceCard(card));
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      openServiceCard(card);
    });
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  byId("recognize-button").addEventListener("click", (event) => startRecognition(event.currentTarget));
  byId("junk-cleanup-button").addEventListener("click", (event) => runJunkCleanup(event.currentTarget));
  byId("sync-button").addEventListener("click", (event) => syncFeishu(event.currentTarget));
  byId("health-button").addEventListener("click", (event) => runHealth(event.currentTarget));
  byId("health-accept-button").addEventListener("click", (event) => acceptHealthUpdates(event.currentTarget));
  byId("pause-button").addEventListener("click", (event) => togglePause(event.currentTarget));
  byId("refresh-button").addEventListener("click", (event) => {
    if (confirmDiscardAllDrafts(
      "刷新列表将放弃未保存修改，确定继续吗？"
    )) reconcilePendingTasks(event.currentTarget);
  });
  byId("audit-refresh-button").addEventListener("click", loadAudit);
  byId("reply-assistant-open").addEventListener("click", () => openLocalTarget("reply"));
  document.querySelectorAll("[data-refresh-list]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!confirmDiscardAllDrafts(
        "刷新列表将放弃未保存修改，确定继续吗？"
      )) return;
      if (button.dataset.refreshList === "issues") loadManual();
      if (button.dataset.refreshList === "manual") loadManual();
      if (button.dataset.refreshList === "sent") syncSentTasks(button);
      if (button.dataset.refreshList === "kol") reconcilePendingTasks(button);
    });
  });
  document.querySelectorAll("[data-risk-action]").forEach((button) => {
    button.addEventListener("click", () => handleRiskAction(button.dataset.riskAction));
  });
  byId("final-confirm-button").addEventListener("click", (event) => executeConfirmation(event.currentTarget));
  byId("classification-form").addEventListener("submit", submitClassification);
  window.addEventListener("beforeunload", (event) => {
    if (state.dirtyTaskIds.size > 0) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  byId("confirm-dialog").addEventListener("close", () => {
    const pending = state.pendingConfirmation;
    if (pending) setTaskBusy(pending.task.id, false);
    state.pendingConfirmation = null;
    applyPauseState();
  });
  byId("confirm-dialog").addEventListener("cancel", (event) => {
    if (byId("confirm-dialog").getAttribute("aria-busy") === "true") {
      event.preventDefault();
    }
  });
}

async function initialize() {
  bindEvents();
  tickClock();
  window.setInterval(tickClock, 1000);
  await refreshAll();
  await runHealth(null, { clear: false });
}

document.addEventListener("DOMContentLoaded", initialize);
