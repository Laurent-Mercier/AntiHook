// Chrome MV3 background service-worker
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.action === "analyze_email" && msg.html) {
    (async () => {
      try {
        const resp = await fetch("http://127.0.0.1:8000/analyze_html", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ html: msg.html })
        });
        if (!resp.ok) throw new Error("Server error");
        const result = await resp.json();
        if (result.error) throw new Error(result.error);

        const isPhish = result.is_phishing;
        const pct = isPhish
          ? (result.confidence * 100).toFixed(2)
          : (100 - result.confidence * 100).toFixed(2);

        chrome.notifications.create({
          type: "basic",
          iconUrl: "icon.png",
          title: "Phishing Check",
          message: isPhish
            ? `⚠️ Phishing Detected! (Confidence: ${pct}%)`
            : `✅ Safe Email (Confidence: ${pct}%)`
        });
      } catch (err) {
        console.error("Detection failed:", err);
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icon.png",
          title: "Error",
          message: `Phishing analysis failed: ${err.message}`
        });
      }
    })();
  }
});

