// App shell: activation gate + tabs, then wire each tool.
import { $, $$, setMsg, bindRangeOutputs, bindDropZones } from "./util.js";
import { initTikTok } from "./tiktok.js";
import { initVariants } from "./variants.js";
import { initImages } from "./images.js";
import { initUpscale } from "./upscale.js";
import { initChat } from "./chat.js";

const KEY = "allapp_token";
const store = {
  get() { try { return localStorage.getItem(KEY) || ""; } catch { return ""; } },
  set(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch { /* private mode */ } },
};

export let TOKEN = "";

function setUrlToken(tok) {
  const u = new URL(location.href);
  if (tok) u.searchParams.set("token", tok); else u.searchParams.delete("token");
  history.replaceState(null, "", u);
}

async function verify(tok) {
  if (!tok) return false;
  try {
    const r = await fetch(`/api/verify?token=${encodeURIComponent(tok)}`);
    return r.ok && (await r.json()).ok === true;
  } catch {
    return false;
  }
}

function showApp(tok) {
  TOKEN = tok;
  store.set(tok);
  setUrlToken(tok);
  $("#gate").hidden = true;
  $("#app").hidden = false;
}

function showGate() {
  $("#app").hidden = true;
  $("#gate").hidden = false;
  $("#gate-code").focus();
}

$("#gate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const code = $("#gate-code").value.trim().toUpperCase();
  const msg = $("#gate-msg");
  if (!code) return;
  try {
    const r = await fetch("/api/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok && j.token) {
      setMsg(msg, "✅ Activated! Bookmark this page URL — it gives you lifetime access.", "ok");
      setTimeout(() => showApp(j.token), 600);
    } else {
      setMsg(msg, `❌ ${j.error || "Invalid code. Contact the admin to get one."}`, "err");
    }
  } catch {
    setMsg(msg, "❌ Could not reach the server. Check your connection and try again.", "err");
  }
});

$("#logout").addEventListener("click", (e) => {
  e.preventDefault();
  store.set("");
  setUrlToken("");
  location.reload();
});

// Tabs
function selectTab(name) {
  for (const b of $$(".tabs button")) b.setAttribute("aria-selected", String(b.dataset.tab === name));
  for (const p of $$(".panel")) p.hidden = p.dataset.panel !== name;
  try { sessionStorage.setItem("allapp_tab", name); } catch { /* ignore */ }
}
for (const b of $$(".tabs button")) b.addEventListener("click", () => selectTab(b.dataset.tab));
for (const c of $$("[data-go]")) c.addEventListener("click", () => selectTab(c.dataset.go));
try { const t = sessionStorage.getItem("allapp_tab"); if (t) selectTab(t); } catch { /* ignore */ }

bindRangeOutputs();
bindDropZones();
initTikTok(() => TOKEN);
initVariants();
initImages();
initUpscale();
initChat(() => TOKEN);

// Boot: URL token (bookmark) wins, then this browser's saved token.
(async () => {
  const urlTok = new URL(location.href).searchParams.get("token") || "";
  for (const tok of [urlTok, store.get()]) {
    if (tok && (await verify(tok))) return showApp(tok);
  }
  showGate();
})();
