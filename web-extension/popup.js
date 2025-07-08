document.getElementById("check").addEventListener("click", async () => {
  const resultEl = document.getElementById("result");
  const shapEl = document.getElementById("shap");
  resultEl.textContent = "Analyzing...";
  shapEl.innerHTML = "";

  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    const htmlContent = await browser.tabs.sendMessage(tab.id, { action: "extract_email" });

    const response = await fetch("http://localhost:8000/analyze_html", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html: htmlContent })
    });

    const data = await response.json();

    if (data.error) {
      resultEl.textContent = "Error: " + data.error;
      return;
    }

    resultEl.innerHTML = `
      <div><span>Language:</span> ${data.language}</div>
      <div><span>Result:</span> ${data.is_phishing ? "Phishing" : "Legitimate"}</div>
      <div><span>Confidence:</span> ${data.is_phishing ? (data.confidence * 100).toFixed(2) : (100 - data.confidence * 100).toFixed(2)}%</div>
    `;

    if (data.explanation && data.explanation.length > 0) {
      shapEl.innerHTML = "<strong>Explanation:</strong>";
      data.explanation.slice(0, 5).forEach(item => {
        const token = document.createElement("div");
        token.className = `token ${item.impact >= 0 ? "positive" : "negative"}`;
        token.innerHTML = `
          <span>${item.word}</span>
          <span class="impact">${item.impact >= 0 ? "+" : ""}${item.impact.toFixed(4)}</span>
        `;
        shapEl.appendChild(token);
      });
    }

  } catch (err) {
    resultEl.textContent = "Error: " + err.message;
  }
});

