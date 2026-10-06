// AI chat (server: /api/chat → Vercel AI Gateway, streamed as plain text).
import { $, esc, setMsg } from "./util.js";

export function initChat(getToken) {
  const log = $("#chat-log"), input = $("#chat-input"), send = $("#chat-send"), msg = $("#chat-msg");
  let history = [];
  let busy = false;

  fetch("/api/chat/info").then((r) => r.json()).then((j) => { if (j.model) $("#chat-model").textContent = j.model; }).catch(() => {});

  function bubble(role, text) {
    const d = document.createElement("div");
    d.className = `bubble ${role}`;
    d.textContent = text;
    log.append(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }

  async function submit() {
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true;
    send.disabled = true;
    setMsg(msg, "");
    input.value = "";
    history.push({ role: "user", content: text });
    bubble("user", text);
    const out = bubble("assistant", "");
    out.classList.add("pending");
    let reply = "";
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Access-Token": getToken() },
        body: JSON.stringify({ messages: history }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${r.status}`);
      }
      const reader = r.body.getReader(), dec = new TextDecoder();
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        reply += dec.decode(value, { stream: true });
        out.textContent = reply;
        log.scrollTop = log.scrollHeight;
      }
      if (!reply) throw new Error("The model returned an empty reply.");
      history.push({ role: "assistant", content: reply });
    } catch (e) {
      history.pop();
      out.remove();
      input.value = text;
      setMsg(msg, `❌ ${esc(e.message)}`, "err");
    } finally {
      out.classList.remove("pending");
      busy = false;
      send.disabled = false;
      input.focus();
    }
  }

  $("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); }
  });
  $("#chat-new").addEventListener("click", () => {
    if (busy) return;
    history = [];
    log.replaceChildren();
    setMsg(msg, "");
    input.focus();
  });
}
