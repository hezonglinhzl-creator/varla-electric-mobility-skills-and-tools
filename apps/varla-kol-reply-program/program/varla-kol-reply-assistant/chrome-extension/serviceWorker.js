chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    varlaSettings: {
      brandName: "Varla",
      senderName: "Team Member",
      defaultCommission: "8%",
      commissionValidity: "3 months",
      chatgptUrl: "https://chatgpt.com/"
    }
  });
});

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_WIDGET" });
  } catch {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["contentScript.js"]
    });
    await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_WIDGET" });
  }
});
