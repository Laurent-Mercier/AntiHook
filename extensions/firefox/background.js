browser.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg.action === "analyze_email" && msg.html) {
    try {
      const resp = await fetch("http://127.0.0.1:8000/analyze_html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html: msg.html })
      });
      if (!resp.ok) throw new Error(`Server error ${resp.status}`);
      const data = await resp.json();
      if (data.error) throw new Error(data.error);

      const isPhish = data.is_phishing;
      const pct = isPhish
        ? (data.confidence * 100).toFixed(2)
        : (100 - data.confidence * 100).toFixed(2);

      browser.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Phishing Check",
        message: isPhish
          ? `⚠️ Phishing Detected! (Confidence: ${pct}%)`
          : `✅ Safe Email (Confidence: ${pct}%)`
      });
    } catch (err) {
      console.error("Detection failed:", err);
      browser.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Error",
        message: `Analysis failed: ${err.message}`
      });
    }
  }
});
