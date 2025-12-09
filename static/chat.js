// Minimal chat UI (Japanese)
document.addEventListener("DOMContentLoaded", function () {
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const showLogs = document.getElementById("showLogs");
  const clearBtn = document.getElementById("clear");

  function append(role, text) {
    const d = document.createElement("div");
    d.className = "msg " + (role === "user" ? "user" : "bot");
    d.innerHTML = "<div class='meta'>" + (role === "user" ? "あなた" : "ELIZA") + "</div><div>" + escapeHtml(text) + "</div>";
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(s) {
    return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  }

  async function sendMessage() {
    const val = input.value.trim();
    if (!val) return;
    append("user", val);
    input.value = "";
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: val })
      });
      const data = await res.json();
      if (data.reply) {
        append("bot", data.reply);
      } else if (data.error) {
        append("bot", "エラー: " + data.error);
      } else {
        append("bot", "返信がありません");
      }
    } catch (e) {
      append("bot", "ネットワークエラー: " + e.toString());
    }
  }

  send.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });

  showLogs.addEventListener("click", async function () {
    try {
      const res = await fetch("/api/logs?limit=100");
      const logs = await res.json();
      chat.innerHTML = "";
      logs.reverse().forEach(l => append(l.role, l.text));
    } catch (e) {
      append("bot", "ログ取得に失敗: " + e.toString());
    }
  });

  clearBtn.addEventListener("click", function () {
    chat.innerHTML = "";
  });

});
