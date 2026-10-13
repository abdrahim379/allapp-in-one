// Web answers (server: /api/ask → Perplexity Agent API with web_search).
// Follow-ups continue the thread with previous_response_id.
import { $, esc, setMsg } from "./util.js";

export function initAsk(getToken) {
  const log = $("#ask-log"), input = $("#ask-input"), send = $("#ask-send"), msg = $("#ask-msg");
  let prevId = "";
  let busy = false;

  function bubble(role, text) {
    const d = document.createElement("div");
    d.className = `bubble ${role}`;
    d.textContent = text;
    log.append(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }

  function addSources(el, links) {
    const safe = links.filter((l) => /^https?:\/\//i.test(l.url || ""));
    if (!safe.length) return;
    const ol = document.createElement("ol");
    ol.className = "ask-sources";
    for (const l of safe.slice(0, 10)) {
      const a = document.createElement("a");
      a.href = l.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = l.title || new URL(l.url).hostname;
      const li = document.createElement("li");
      li.append(a);
      ol.append(li);
    }
    el.append(ol);
  }

  async function submit() {
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true;
    send.disabled = true;
    setMsg(msg, "");
    input.value = "";
    bubble("user", text);
    const out = bubble("assistant", "Searching the web…");
    out.classList.add("pending");
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Access-Token": getToken() },
        body: JSON.stringify({ question: text, previous_response_id: prevId || undefined }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
      if (!j.answer) throw new Error("The model returned an empty answer.");
      out.textContent = j.answer;
      addSources(out, j.citations && j.citations.length ? j.citations : j.sources || []);
      prevId = j.id || "";
    } catch (e) {
      out.remove();
      log.lastElementChild?.remove();
      input.value = text;
      setMsg(msg, `❌ ${esc(e.message)}`, "err");
    } finally {
      out.classList.remove("pending");
      log.scrollTop = log.scrollHeight;
      busy = false;
      send.disabled = false;
      input.focus();
    }
  }

  $("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); }
  });
  $("#ask-new").addEventListener("click", () => {
    if (busy) return;
    prevId = "";
    log.replaceChildren();
    setMsg(msg, "");
    input.focus();
  });
}
