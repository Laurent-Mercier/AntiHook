browser.runtime.onMessage.addListener((msg, sender) => {
  if (msg.action === "extract_email") {
    const selectors = [
      '[role="document"]',
      'div.a3s.aiL',
      'div.gs',
      'div[data-message-id]'
    ];
    let emailDiv = null;
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.innerHTML.trim()) {
        emailDiv = el;
        break;
      }
    }
    if (!emailDiv) {
      alert("⚠️ Could not find the email content. Are you viewing an email?");
      return Promise.resolve("");
    }
    const clone = emailDiv.cloneNode(true);
    clone.querySelectorAll("script").forEach(s => s.remove());
    return Promise.resolve(clone.innerHTML);
  }
});


