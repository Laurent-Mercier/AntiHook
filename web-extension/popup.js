document.getElementById("check").addEventListener("click", () => {
  browser.runtime.sendMessage({ action: "start_check" });
});