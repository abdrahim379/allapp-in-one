// Small shared helpers.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function humanSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(2)} MB`;
}

export function formatNumber(num) {
  const n = parseInt(num, 10);
  if (!Number.isFinite(n)) return num ? String(num) : "N/A";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function fmtDur(s) {
  s = Number(s) || 0;
  return s ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "—";
}

export function stamp(withSec = false) {
  const d = new Date(), p = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${withSec ? p(d.getSeconds()) : ""}`;
}

export function baseName(name) {
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(0, i) : name;
}

export function extOf(name) {
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(i).toLowerCase() : "";
}

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function downloadButton(blob, filename, label) {
  const b = document.createElement("button");
  b.className = "btn primary wide";
  b.textContent = label;
  b.dataset.filename = filename;
  b.onclick = () => saveBlob(blob, filename);
  return b;
}

export function setMsg(el, text, kind = "") {
  el.className = `msg ${kind}`;
  el.innerHTML = text;
}

export function progressBar() {
  const wrap = document.createElement("div");
  wrap.className = "progress";
  const bar = document.createElement("div");
  wrap.appendChild(bar);
  wrap.set = (pct) => { bar.style.width = `${Math.max(0, Math.min(100, pct))}%`; };
  return wrap;
}

// Range inputs with a live <output id="<id>-v">.
export function bindRangeOutputs(root = document) {
  for (const r of $$("input[type=range]", root)) {
    const out = document.getElementById(`${r.id}-v`);
    if (out) r.addEventListener("input", () => (out.textContent = r.value));
  }
}

// Show selected file names inside a .drop zone.
export function bindDropZones(root = document) {
  for (const d of $$(".drop", root)) {
    const input = $("input[type=file]", d), span = $("span", d), initial = span.textContent;
    input.addEventListener("change", () => {
      const n = input.files.length;
      span.textContent = n ? (n === 1 ? `📎 ${input.files[0].name}` : `📎 ${n} files selected`) : initial;
    });
    d.addEventListener("dragover", () => d.classList.add("over"));
    for (const ev of ["dragleave", "drop"]) d.addEventListener(ev, () => d.classList.remove("over"));
  }
}

// Keep every file in a ZIP even when two inputs share a base name (a.jpg + a.png).
export function uniqueNamer() {
  const used = new Set();
  return (name) => {
    let n = name, i = 2;
    const b = baseName(name), e = name.slice(b.length);
    while (used.has(n.toLowerCase())) n = `${b}_${i++}${e}`;
    used.add(n.toLowerCase());
    return n;
  };
}
