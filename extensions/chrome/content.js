// Chrome content script: extract email HTML
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action !== "extract_email") return;
  const selectors = [
    '[role="document"]',
    'div.a3s.aiL',
    'div.ii.gt',
    'div.adn.ads',
    'div[data-message-id]'
  ];
  let container = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerHTML.trim()) { container = el; break; }
  }
  if (!container) container = document.body;
  const clone = container.cloneNode(true);
  clone.querySelectorAll("script, style, iframe, head").forEach(n => n.remove());
  sendResponse(clone.innerHTML);
  return true;  // keep message channel open for sendResponse
});





