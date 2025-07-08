browser.runtime.onMessage.addListener((msg, sender) => {
  if (msg.action === "extract_email") {
    const selectors = [
      '[role="document"]',         // Outlook Web App
      'div.a3s.aiL',               // Gmail (standard emails)
      'div.gs',                    // Gmail (sometimes used for grouped conversations)
      'div[data-message-id]'       // Fallback: any Gmail message container
    ];

    let emailDiv = null;
    for (const selector of selectors) {
      const candidate = document.querySelector(selector);
      if (candidate && candidate.innerHTML.trim().length > 0) {
        emailDiv = candidate;
        break;
      }
    }

    const html = emailDiv ? emailDiv.innerHTML : '';

    if (!html) {
      alert("⚠️ Could not find the email content. Are you viewing an email?");
    }

    // 🔧 FIX: send result back to the popup
    return Promise.resolve(html);
  }
});

