// popup.js (Firefox MV2)

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

// load or default to English
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

// initialize UI
langSelect.value = currentLang;
refreshUIText();

// remove the explanatory “small-note” completely
const smallNote = document.querySelector(".small-note");
if (smallNote) smallNote.remove();

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

async function runAnalysis(htmlContent, highlight = true) {
  const T = UI_STR[currentLang];
  resultEl.textContent = T.analyzing;
  resultEl.classList.add("loading");
  previewEl.innerHTML = "";

  try {
    const resp = await fetch("http://localhost:8000/analyze_html", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html: htmlContent })
    });
    const data = await resp.json();
    resultEl.classList.remove("loading");

    if (data.error) {
      resultEl.textContent = "Error: " + data.error;
      return;
    }

    const pct = data.is_phishing
      ? (data.confidence * 100)
      : (100 - data.confidence * 100);

    resultEl.innerHTML = `
      <div><span>${T.language}</span> ${data.language}</div>
      <div><span>${T.result}</span> ${
        data.is_phishing
          ? `<strong style="color:#d13438">${T.phishing}</strong>`
          : `<strong style="color:#107c10">${T.safe}</strong>`
      }</div>
      <div><span>${T.confidence}</span> ${pct.toFixed(2)}%</div>
    `;

    previewEl.innerHTML = htmlContent;

    if (highlight && data.explanation?.length) {
      const toks = data.explanation
        .slice(0,5)
        .sort((a,b)=> b.word.length - a.word.length);
      for (let tok of toks) {
        const word = tok.word;
        if (!word) continue;
        const color = tok.impact >= 0 ? "#c62828" : "#2e7d32";
        const walker = document.createTreeWalker(previewEl, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const idx = node.nodeValue.toLowerCase().indexOf(word.toLowerCase());
          if (idx >= 0) {
            const range = document.createRange();
            range.setStart(node, idx);
            range.setEnd(node, idx + word.length);
            const span = document.createElement("span");
            span.style.backgroundColor = color;
            span.style.color = "#fff";
            span.style.fontWeight = "bold";
            span.textContent = node.nodeValue.substr(idx, word.length);
            range.deleteContents();
            range.insertNode(span);
            break;
          }
        }
      }
    }
  } catch (err) {
    resultEl.classList.remove("loading");
    resultEl.textContent = "Error: " + err.message;
  }
}

// 1) Analyze current email
checkEmailBtn.addEventListener("click", async () => {
  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    const html = await browser.tabs.sendMessage(tab.id, { action: "extract_email" });
    if (!html) {
      resultEl.textContent = UI_STR[currentLang].noEmail;
      return;
    }
    runAnalysis(html, true);
  } catch (e) {
    resultEl.textContent = "Error: " + e.message;
  }
});

// 2) Toggle manual panel
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
  const paras = txt
    .split(/\n{2,}/)
    .map(b => `<p>${escapeHTML(b).replace(/\n/g,"<br>")}</p>`)
    .join("\n");
  runAnalysis(paras, true);
});

// 4) Clear manual text
clearManualBtn.addEventListener("click", () => {
  manualText.value = "";
});











