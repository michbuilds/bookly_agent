let history = [];

const log = document.getElementById("log");
const emptyState = document.getElementById("empty-state");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const historyList = document.getElementById("history-list");
const activityLog = document.getElementById("activity-log");
const activityPanel = document.getElementById("activity-panel");
const newConversationBtn = document.getElementById("new-conversation");
const toggleActivityBtn = document.getElementById("toggle-activity");

function addBubble(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function showChatView() {
  emptyState.style.display = "none";
  log.classList.add("visible");
}

function tagFor(outcome) {
  if (!outcome) return "ok";
  const warnStates = ["outside_refund_window", "not_yet_delivered", "escalated", "already_refunded", "needs_human_review", "repeat_no_evidence_claim"];
  const errorStates = ["not_found", "email_does_not_match_order", "no_order_with_that_id"];
  if (errorStates.includes(outcome)) return "error";
  if (warnStates.includes(outcome)) return "warn";
  return "ok";
}

function renderEvents(events) {
  if (!events || events.length === 0) return;
  const empty = activityLog.querySelector(".activity-empty");
  if (empty) empty.remove();

  events.forEach((e) => {
    const card = document.createElement("div");
    card.className = "event-card";

    const inputStr = Object.entries(e.input || {})
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · ");

    const outcome = e.output?.outcome || e.output?.status || (e.output?.found !== undefined
      ? (e.output.found ? "found" : "not_found")
      : "done");

    card.innerHTML = `
      <div class="event-tool">🛠 ${e.tool}</div>
      <div class="event-input">${inputStr}</div>
      <span class="event-tag ${tagFor(outcome)}">${outcome}</span>
    `;
    activityLog.appendChild(card);
  });
  activityLog.scrollTop = activityLog.scrollHeight;
}

function addHistoryEntry(label) {
  const empty = historyList.querySelector(".history-empty");
  if (empty) empty.remove();
  const item = document.createElement("div");
  item.className = "history-item";
  item.textContent = label;
  historyList.prepend(item);
}

async function sendMessage(text) {
  showChatView();
  addBubble("user", text);
  if (history.length === 0) {
    addHistoryEntry(text.length > 40 ? text.slice(0, 40) + "…" : text);
  }
  history.push({ role: "user", content: text });

  const thinking = addBubble("assistant thinking", "…");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const data = await res.json();
    history = data.messages;
    thinking.remove();
    addBubble("assistant", data.reply);
    renderEvents(data.events);
  } catch (err) {
    thinking.remove();
    addBubble("assistant error", "Something went wrong reaching the server.");
    console.error(err);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.disabled = true;
  await sendMessage(text);
  input.disabled = false;
  input.focus();
});

document.querySelectorAll(".quick-card").forEach((card) => {
  card.addEventListener("click", async () => {
    const prompt = card.dataset.prompt;
    await sendMessage(prompt);
  });
});

newConversationBtn.addEventListener("click", () => {
  history = [];
  log.innerHTML = "";
  log.classList.remove("visible");
  emptyState.style.display = "flex";
  input.value = "";
  input.focus();
});

toggleActivityBtn.addEventListener("click", () => {
  activityPanel.classList.toggle("hidden");
});
