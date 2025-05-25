browser.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg.action === "start_check") {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });

    browser.tabs.captureVisibleTab(tab.windowId, { format: "png" }).then(async (dataUrl) => {
      const response = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: dataUrl })
      });
      const result = await response.json();
      if (result.error) {
        browser.notifications.create({
            type: "basic",
            iconUrl: "icon.png",
            title: "Error",
            message: result.error
        });
        return;
      }
      const isPhishing = result.is_phishing;
      console.log("Extracted text:", result.extracted_text);
      browser.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Phishing Check",
        message: isPhishing ? "⚠️ Phishing Email Detected!" : "✅ Email looks safe"
      });
    });
  }
});