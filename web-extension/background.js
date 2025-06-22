browser.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg.action === "analyze_email" && msg.html) {
    try {
      const response = await fetch("http://127.0.0.1:8000/analyze_html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html: msg.html })
      });

      if (!response.ok) throw new Error("Server error");

      const result = await response.json();

      if (result.error) throw new Error(result.error);

      const isPhishing = result.is_phishing;
      const confidence = isPhishing
        ? (result.confidence * 100).toFixed(2)
        : (100 - result.confidence * 100).toFixed(2);

      browser.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Phishing Check",
        message: isPhishing
          ? `⚠️ Phishing Detected! (Confidence: ${confidence}%)`
          : `✅ Safe Email (Confidence: ${confidence}%)`,
      });
    } catch (err) {
      console.error("Phishing detection failed:", err);
      browser.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Error",
        message: `Phishing analysis failed: ${err.message}`
      });
    }
  }
});