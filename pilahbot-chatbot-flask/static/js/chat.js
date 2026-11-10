(() => {
  const messages = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const sendButton = form.querySelector("button");

  function addMessage(sender, text, detail) {
    const row = document.createElement("div");
    row.className = `message message-${sender}`;

    if (sender === "bot") {
      const avatar = document.createElement("span");
      avatar.className = "message-avatar";
      avatar.setAttribute("aria-hidden", "true");
      avatar.textContent = "P";
      row.appendChild(avatar);
    }

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    if (detail) {
      const meta = document.createElement("span");
      meta.className = "message-meta";
      meta.textContent = detail;
      bubble.appendChild(meta);
    }
    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return row;
  }

  async function sendMessage(text) {
    addMessage("user", text);
    const pending = addMessage("bot", "Sebentar ya, Pilahbot sedang mencari jawabannya...");
    input.disabled = true;
    sendButton.disabled = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await response.json();
      pending.remove();
      if (!response.ok) {
        addMessage("bot", data.error || "Pesan belum bisa diproses. Coba lagi ya.");
        return;
      }
      addMessage("bot", data.reply, data.intent_name);
    } catch (error) {
      pending.remove();
      addMessage("bot", "Sepertinya koneksi terputus. Coba kirim pesanmu lagi.");
      console.error("Gagal menghubungi Pilahbot:", error);
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || input.disabled) return;
    input.value = "";
    sendMessage(text);
  });

  document.querySelectorAll(".suggestion-chip").forEach((button) => {
    button.addEventListener("click", () => {
      if (!input.disabled) sendMessage(button.textContent.trim());
    });
  });

  addMessage("bot", window.PILAHBOT_CONFIG.greeting);
})();
