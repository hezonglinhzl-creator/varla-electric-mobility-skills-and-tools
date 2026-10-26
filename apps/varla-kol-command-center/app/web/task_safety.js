(function exposeTaskSafety(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.VarlaTaskSafety = api;
}(typeof globalThis === "object" ? globalThis : this, function buildTaskSafety() {
  "use strict";

  function buttonDisabled(context, action) {
    if (action === "open-gmail") return false;
    if (context.paused || context.busy || context.terminal) return true;
    if (
      context.dirty &&
      action !== "save-preview" &&
      action !== "discard-preview" &&
      action !== "confirm-reply" &&
      action !== "confirm-manual-reply" &&
      action !== "ignore"
    ) {
      return true;
    }
    if (action === "discard-preview") return !context.dirty;
    if (action === "confirm-label" && context.labelAvailable === false) {
      return true;
    }
    if (
      action === "save-preview" &&
      (!context.saveAvailable || !context.dirty || !context.hasDraft)
    ) {
      return true;
    }
    if (action === "confirm-reply") {
      if (context.hardBlocked) return true;
      if (context.dirty) {
        return !context.manualReplyAvailable || !context.hasDraft;
      }
      return !context.confirmable;
    }
    if (action === "confirm-manual-reply") {
      if (context.hardBlocked || !context.manualReplyAvailable) return true;
      return context.dirty ? !context.hasDraft : !context.hasPreview;
    }
    if (action === "confirm-forward") {
      if (context.dirty || context.hardBlocked || !context.confirmable) return true;
    }
    if (action === "confirm-forward" && !context.forwardAvailable) return true;
    return false;
  }

  return Object.freeze({ buttonDisabled });
}));
