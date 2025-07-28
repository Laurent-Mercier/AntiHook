// popup.js (Chrome MV3)

const UI_STR = {
  en: {
    uiLanguageLabel:   "UI Language:",
    analyzing:         "Analyzing…",
    language:          "Language:",
    result:            "Result:",
    confidence:        "Confidence:",
    phishing:          "Phishing",
    safe:              "Legitimate",
    pleasePaste:       "Please paste some text first.",
    noEmail:           "No email content found.",
    analyzeEmail:      "Analyze Email",
    analyzePaste:      "Analyze Pasted Text",
    runAnalysis:       "Run Analysis",
    clear:             "Clear",
    manualPlaceholder: "Paste (or type) email content here..."
  },
  fr: {
    uiLanguageLabel:   "Langue de l’interface :",
    analyzing:         "Analyse en cours…",
    language:          "Langue :",
    result:            "Résultat :",
    confidence:        "Confiance :",
    phishing:          "Hameçonnage",
    safe:              "Légitime",
    pleasePaste:       "Veuillez coller du texte d'abord.",
    noEmail:           "Aucun contenu d’e‑mail trouvé.",
    analyzeEmail:      "Analyser le courriel",
    analyzePaste:      "Analyser le texte collé",
    runAnalysis:       "Lancer l'analyse",
    clear:             "Effacer",
    manualPlaceholder: "Collez (ou saisissez) le contenu du courriel ici…"
  }
};

let currentLang = localStorage.getItem("uiLang") || "en";

// DOM references
const langSelect       = document.getElementById("langSelect");
const langLabel        = document.querySelector("#lang-container label");
const checkEmailBtn    = document.getElementById("checkEmailBtn");
const toggleManualBtn  = document.getElementById("toggleManualBtn");
const analyzeManualBtn = document.getElementById("analyzeManualBtn");
const clearManualBtn   = document.getElementById("clearManualBtn");
const manualPanel      = document.getElementById("manual-panel");
const manualText       = document.getElementById("manual-text");
const resultEl         = document.getElementById("result");
const previewEl        = document.getElementById("email-preview");

langSelect.value = currentLang;
refreshUIText();

// remove that explanatory note
const note = document.querySelector(".small-note");
if (note) note.remove();

langSelect.addEventListener("change", () => {
  currentLang = langSelect.value;
  localStorage.setItem("uiLang", currentLang);
  refreshUIText();
});

function refreshUIText() {
  const T = UI_STR[currentLang];
  langLabel.textContent        = T.uiLanguageLabel;
  checkEmailBtn.textContent    = T.analyzeEmail;
  toggleManualBtn.textContent  = T.analyzePaste;
  analyzeManualBtn.textContent = T.runAnalysis;
  clearManualBtn.textContent   = T.clear;
  manualText.placeholder       = T.manualPlaceholder;
}

function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function runAnalysis(htmlContent, { highlight = true } = {}) {
  const T = UI_STR[currentLang];
  resultEl.textContent = T.analyzing;
  previewEl.innerHTML = "";

  try {
    const resp = await fetch("http://127.0.0.1:8000/analyze_html", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html: htmlContent })
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);

    const pct = data.is_phishing
      ? (data.confidence * 100)
      : (100 - data.confidence * 100);

    resultEl.innerHTML = `
      <div><strong>${T.language}</strong> ${data.language}</div>
      <div><strong>${T.result}</strong> ${
        data.is_phishing
          ? `<span style="color:red">${T.phishing}</span>`
          : `<span style="color:green">${T.safe}</span>`
      }</div>
      <div><strong>${T.confidence}</strong> ${pct.toFixed(2)}%</div>
    `;

    previewEl.innerHTML = htmlContent;

    if (highlight && Array.isArray(data.explanation)) {
      const tokens = data.explanation
        .slice(0,5)
        .sort((a,b)=> b.word.length - a.word.length);
      for (const {word, impact} of tokens) {
        if (!word.trim()) continue;
        const color = impact >= 0 ? "#c62828" : "#2e7d32";
        const walker = document.createTreeWalker(previewEl, NodeFilter.SHOW_TEXT);
        let node;
        while (node = walker.nextNode()) {
          const txt = node.nodeValue;
          const idx = txt.toLowerCase().indexOf(word.toLowerCase());
          if (idx !== -1) {
            const range = document.createRange();
            range.setStart(node, idx);
            range.setEnd(node, idx + word.length);
            const span = document.createElement("span");
            span.textContent = txt.substr(idx, word.length);
            span.style.backgroundColor = color;
            span.style.color = "#fff";
            span.style.fontWeight = "bold";
            range.deleteContents();
            range.insertNode(span);
            break;
          }
        }
      }
    }

  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
}

// 1) Analyze current open email
checkEmailBtn.addEventListener("click", async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"]
    });
    chrome.tabs.sendMessage(tab.id, { action: "extract_email" }, htmlContent => {
      if (!htmlContent) {
        resultEl.textContent = UI_STR[currentLang].noEmail;
        return;
      }
      runAnalysis(htmlContent);
    });
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
});

// 2) Toggle manual‐paste area
toggleManualBtn.addEventListener("click", () => {
  manualPanel.classList.toggle("collapsed");
});

// 3) Analyze pasted text
analyzeManualBtn.addEventListener("click", () => {
  const txt = manualText.value.trim();
  if (!txt) {
    resultEl.textContent = UI_STR[currentLang].pleasePaste;
    return;
  }
  const paragraphs = txt
    .split(/\n{2,}/)
    .map(block => `<p>${escapeHTML(block).replace(/\n/g, "<br>")}</p>`)
    .join("\n");
  runAnalysis(paragraphs);
});

// 4) Clear manual text
clearManualBtn.addEventListener("click", () => {
  manualText.value = "";
});


