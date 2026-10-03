// TikTok extractor & downloader (server: /api/tiktok/*).
import { $, esc, formatNumber, fmtDur, setMsg, stamp, downloadButton, uniqueNamer } from "./util.js";

export function initTikTok(getToken) {
  let videos = [];
  const selected = new Set();
  const list = $("#dl-list");

  const authHeaders = () => ({ "X-Access-Token": getToken() });

  $("#dl-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = $("#dl-url").value.trim();
    const msg = $("#dl-msg");
    if (!url || !url.includes("tiktok.com")) return setMsg(msg, "Please enter a valid TikTok URL.", "err");
    const btn = $("#dl-extract");
    btn.disabled = true;
    setMsg(msg, "⏳ Extracting … this can take up to a minute for big profiles.");
    try {
      const r = await fetch("/api/tiktok/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ url }),
      });
      const j = await r.json().catch(() => ({ error: `Server error (${r.status})` }));
      if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
      if (!j.videos.length) {
        setMsg(msg, "No videos found. Check the URL or profile privacy.", "warn");
        return;
      }
      videos = j.videos;
      selected.clear();
      setMsg(msg, `✅ Found <b>${videos.length}</b> videos!`, "ok");
      $("#dl-step2").hidden = false;
      $("#dl-status").innerHTML = "";
      render();
    } catch (err) {
      setMsg(msg, `Extraction failed: ${esc(err.message)}`, "err");
    } finally {
      btn.disabled = false;
    }
  });

  $("#dl-all").onclick = () => { videos.forEach((v) => selected.add(v.id)); render(); };
  $("#dl-none").onclick = () => { selected.clear(); render(); };
  $("#dl-view").onchange = render;
  $("#dl-filter").oninput = render;

  list.addEventListener("click", (e) => {
    const el = e.target.closest("[data-id]");
    if (!el) return;
    const id = el.dataset.id;
    selected.has(id) ? selected.delete(id) : selected.add(id);
    render();
  });

  function render() {
    const q = $("#dl-filter").value.trim().toLowerCase();
    const shown = q ? videos.filter((v) => (v.title || "").toLowerCase().includes(q)) : videos;
    const stats = (v) => `👁️ ${formatNumber(v.views)} &nbsp; ❤️ ${formatNumber(v.likes)} &nbsp; ⏱️ ${fmtDur(v.duration)}`;
    if ($("#dl-view").value === "Grid") {
      list.className = "vgrid";
      list.innerHTML = shown.map((v) => {
        const s = selected.has(v.id);
        return `<div class="vcard${s ? " sel" : ""}">
          ${v.thumbnail ? `<img loading="lazy" referrerpolicy="no-referrer" src="${esc(v.thumbnail)}" alt="" onerror="this.remove()">` : ""}
          <div>${s ? "✅" : "⬜"}</div>
          <div class="t">${esc((v.title || "").slice(0, 55))}</div>
          <div class="vstats">${stats(v)}</div>
          <button class="btn small" data-id="${esc(v.id)}">${s ? "Deselect" : "Select"}</button>
        </div>`;
      }).join("");
    } else {
      list.className = "vlist";
      list.innerHTML = shown.map((v) => {
        const s = selected.has(v.id);
        return `<div class="vrow${s ? " sel" : ""}">
          <div class="ic">${s ? "✅" : "⬜"}</div>
          <div class="tx"><b>${esc((v.title || "").slice(0, 90))}</b><span class="vstats">${stats(v)}</span></div>
          <button class="btn small" data-id="${esc(v.id)}">${s ? "Deselect" : "Select"}</button>
        </div>`;
      }).join("");
    }
    const n = selected.size;
    $("#dl-count").innerHTML = `<b>${n}</b> video(s) selected`;
    const go = $("#dl-go");
    go.textContent = `📥 Download ${n} Video(s) as ZIP`;
    go.disabled = n === 0;
  }

  $("#dl-go").addEventListener("click", async () => {
    const go = $("#dl-go");
    const chosen = videos.filter((v) => selected.has(v.id));
    const total = chosen.length;
    const prog = $("#dl-prog"), bar = prog.firstElementChild, status = $("#dl-status");
    prog.hidden = false;
    go.disabled = true;
    status.className = "msg";
    const zip = new JSZip();
    const uniq = uniqueNamer();
    let ok = 0;
    const failures = [];
    for (let i = 0; i < total; i++) {
      const v = chosen[i];
      status.innerHTML = `⬇️ <b>${i + 1}/${total}</b> — <code>${esc(v.id)}</code>`;
      bar.style.width = `${(i / total) * 100}%`;
      try {
        const qs = new URLSearchParams({ id: v.id, url: v.url || "" });
        const r = await fetch(`/api/tiktok/download?${qs}`, { headers: authHeaders() });
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          throw new Error(j.error || `HTTP ${r.status}`);
        }
        const cd = r.headers.get("Content-Disposition") || "";
        const name = (/filename="([^"]+)"/.exec(cd) || [])[1] || `${v.id}.mp4`;
        zip.file(uniq(name), await r.blob());
        ok++;
      } catch (err) {
        failures.push(`${v.id}: ${err.message}`);
      }
      bar.style.width = `${((i + 1) / total) * 100}%`;
    }
    go.disabled = false;
    if (!ok) {
      setMsg(status, `No videos downloaded successfully.<br><span class="tiny">${esc(failures.join(" · "))}</span>`, "err");
      return;
    }
    status.innerHTML = "📦 Building ZIP…";
    const blob = await zip.generateAsync({ type: "blob" });
    setMsg(status, `✅ ${ok} video(s) ready!${failures.length ? ` (${failures.length} failed)` : ""}`, "ok");
    status.appendChild(downloadButton(blob, `tiktok_${stamp(true)}.zip`, `⬇️ Save ZIP (${ok} videos)`));
  });
}
