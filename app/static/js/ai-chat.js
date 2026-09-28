/* Platform-X — Floating AI Assistant */

window.PX = window.PX || {};

PX.initAIChat = function () {
  var fab = document.getElementById("px-ai-fab");
  var panel = document.getElementById("px-ai-panel");
  var close = document.getElementById("px-ai-panel-close");
  var form = document.getElementById("px-ai-form");
  var input = document.getElementById("px-ai-input");
  var body = document.getElementById("px-ai-body");
  if (!fab || !panel || !form) return;

  var history = [];  // {role, content}

  fab.addEventListener("click", function () {
    panel.classList.toggle("is-open");
    if (panel.classList.contains("is-open")) input.focus();
  });
  close.addEventListener("click", function () {
    panel.classList.remove("is-open");
  });

  function append(role, text) {
    var div = document.createElement("div");
    div.className = "px-ai-msg px-ai-msg-" + role;
    div.textContent = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function appendTyping() {
    var div = document.createElement("div");
    div.className = "px-ai-msg px-ai-msg-assistant px-ai-typing";
    div.id = "px-ai-typing";
    div.textContent = "…";
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function removeTyping() {
    var t = document.getElementById("px-ai-typing");
    if (t) t.remove();
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    var msg = input.value.trim();
    if (!msg) return;
    append("user", msg);
    input.value = "";
    appendTyping();

    try {
      var res = await fetch("/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          history: history.slice(-10),
        }),
      });
      var data = await res.json();
      removeTyping();
      if (!res.ok) {
        append("assistant", data.detail || "Sorry, I couldn't respond right now.");
        return;
      }
      append("assistant", data.content);
      history.push({ role: "user", content: msg });
      history.push({ role: "assistant", content: data.content });
    } catch (e) {
      removeTyping();
      append("assistant", "Network error. Please try again.");
    }
  });
};

document.addEventListener("DOMContentLoaded", function () {
  PX.initAIChat();
});
