(function exposeTaskDisplay(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.VarlaTaskDisplay = api;
}(typeof globalThis === "object" ? globalThis : this, function buildTaskDisplay() {
  "use strict";

  function validDate(value) {
    return value instanceof Date && Number.isFinite(value.getTime());
  }

  function formatDate(date, locale) {
    return new Intl.DateTimeFormat(locale || undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    }).format(date);
  }

  function formatTaskTime(task, locale) {
    const payload = task && task.payload && typeof task.payload === "object"
      ? task.payload
      : {};
    const milliseconds = Number(payload.message_internal_date);
    const gmailDate = new Date(milliseconds);
    if (milliseconds > 0 && validDate(gmailDate)) {
      return Object.freeze({
        label: "邮件时间",
        value: formatDate(gmailDate, locale),
        source: "gmail"
      });
    }

    const headerDate = new Date(payload.message_date || "");
    if (validDate(headerDate)) {
      return Object.freeze({
        label: "邮件时间",
        value: formatDate(headerDate, locale),
        source: "gmail-header"
      });
    }

    const createdDate = new Date(task && task.created_at ? task.created_at : "");
    if (validDate(createdDate)) {
      return Object.freeze({
        label: "收录时间",
        value: formatDate(createdDate, locale),
        source: "task"
      });
    }
    return Object.freeze({label: "时间", value: "—", source: "missing"});
  }

  return Object.freeze({ formatTaskTime });
}));
