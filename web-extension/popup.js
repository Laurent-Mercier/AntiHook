document.getElementById("check").addEventListener("click", async () => {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });

  // Send a message to the content script to trigger extraction
  browser.tabs.sendMessage(tab.id, { action: "extract_email" });
});

