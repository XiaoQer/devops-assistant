const promptInput = document.querySelector("#prompt");
const sendButton = document.querySelector("#sendButton");
const toast = document.querySelector("#toast");
const suggestions = document.querySelectorAll(".suggestion");

let toastTimer;

function submitTask() {
  const task = promptInput.value.trim();
  if (!task) {
    promptInput.focus();
    return;
  }

  sendButton.innerHTML = "已提交 ✓";
  sendButton.style.background = "linear-gradient(135deg, #4fcf95, #2e9f70)";
  toast.querySelector("span").textContent = `“${task}”正在整理上下文并生成执行计划…`;
  toast.classList.add("visible");

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("visible");
    sendButton.innerHTML = `执行
      <svg viewBox="0 0 24 24"><path d="m5 12 14-7-5 14-2-6-7-1Z"></path></svg>`;
    sendButton.style.background = "";
    promptInput.value = "";
  }, 3500);
}

suggestions.forEach((button) => {
  button.addEventListener("click", () => {
    promptInput.value = button.dataset.prompt;
    promptInput.focus();
  });
});

sendButton.addEventListener("click", submitTask);
promptInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    submitTask();
  }
});
