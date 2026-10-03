// Image Optimizer (Lanczos upscale + unsharp + color boost) and → WebP converter.
// Runs entirely in the browser: pica (Lanczos3), @jsquash/webp (libwebp), UTIF (TIFF).
import { $, esc, humanSize, baseName, extOf, stamp, setMsg, downloadButton, uniqueNamer } from "./util.js";

let picaInst = null;
const getPica = () => (picaInst ||= window.pica({ features: ["js", "wasm", "ww"] }));

let webpEncode = null;
async function encodeWebp(imageData, opts) {
  if (!webpEncode) webpEncode = (await import("/vendor/jsquash-webp/encode.js")).default;
  return new Blob([await webpEncode(imageData, opts)], { type: "image/webp" });
}

function makeCanvas(w, h) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

// Decode any supported file to a canvas (TIFF via UTIF, everything else native).
export async function decodeToCanvas(file) {
  const ext = extOf(file.name);
  if (ext === ".tif" || ext === ".tiff" || file.type === "image/tiff") {
    const buf = await file.arrayBuffer();
    const ifds = UTIF.decode(buf);
    UTIF.decodeImage(buf, ifds[0]);
    const rgba = UTIF.toRGBA8(ifds[0]);
    const c = makeCanvas(ifds[0].width, ifds[0].height);
    c.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(rgba.buffer), c.width, c.height), 0, 0);
    return c;
  }
  let bmp;
  try {
    bmp = await createImageBitmap(file);
  } catch {
    // Fallback through <img> for formats createImageBitmap rejects in some browsers.
    bmp = await new Promise((res, rej) => {
      const img = new Image();
      img.onload = () => res(img);
      img.onerror = () => rej(new Error("unsupported or corrupt image"));
      img.src = URL.createObjectURL(file);
    });
  }
  const c = makeCanvas(bmp.width || bmp.naturalWidth, bmp.height || bmp.naturalHeight);
  c.getContext("2d").drawImage(bmp, 0, 0);
  bmp.close && bmp.close();
  return c;
}

// Same math as PIL ImageEnhance.Color(1.15) then ImageEnhance.Contrast(1.05).
function colorBoost(ctx, w, h) {
  const id = ctx.getImageData(0, 0, w, h), d = id.data;
  const cf = 1.15;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) {
    const g = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    d[i] = g + (d[i] - g) * cf;
    d[i + 1] = g + (d[i + 1] - g) * cf;
    d[i + 2] = g + (d[i + 2] - g) * cf;
    sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  }
  const mean = Math.round(sum / (w * h));
  const k = 1.05;
  for (let i = 0; i < d.length; i += 4) {
    d[i] = mean + (d[i] - mean) * k;
    d[i + 1] = mean + (d[i + 1] - mean) * k;
    d[i + 2] = mean + (d[i + 2] - mean) * k;
  }
  ctx.putImageData(id, 0, 0);
}

const toBlob = (canvas, type, q) =>
  new Promise((res, rej) => canvas.toBlob((b) => (b ? res(b) : rej(new Error("encode failed (image too large?)"))), type, q));

async function encode(canvas, fmt, quality, lossless = false) {
  const ctx = canvas.getContext("2d");
  if (fmt === "WEBP") {
    const id = ctx.getImageData(0, 0, canvas.width, canvas.height);
    return encodeWebp(id, lossless ? { lossless: 1, quality: 100, method: 6, exact: 1 } : { quality, method: 6 });
  }
  if (fmt === "PNG") return toBlob(canvas, "image/png");
  // JPEG has no alpha: flatten onto white.
  const flat = makeCanvas(canvas.width, canvas.height);
  const fctx = flat.getContext("2d");
  fctx.fillStyle = "#fff";
  fctx.fillRect(0, 0, flat.width, flat.height);
  fctx.drawImage(canvas, 0, 0);
  return toBlob(flat, "image/jpeg", quality / 100);
}

export async function optimizeImage(file, { scale, sharpen, sharpenAmount, enhanceColor, fmt, quality }) {
  const src = await decodeToCanvas(file);
  const ow = src.width, oh = src.height;
  const nw = Math.max(1, Math.round(ow * scale)), nh = Math.max(1, Math.round(oh * scale));
  const dst = makeCanvas(nw, nh);
  await getPica().resize(src, dst, {
    filter: "lanczos3",
    ...(sharpen ? { unsharpAmount: Math.round(sharpenAmount * 0.6), unsharpRadius: 1.0, unsharpThreshold: 3 } : {}),
  });
  if (enhanceColor) colorBoost(dst.getContext("2d"), nw, nh);
  const blob = await encode(dst, fmt, quality);
  return { blob, orig: [ow, oh], size: [nw, nh] };
}

export async function convertToWebp(file, { quality, lossless }) {
  const c = await decodeToCanvas(file);
  return encode(c, "WEBP", quality, lossless);
}

const pyFloat = (x) => (Number.isInteger(x) ? x.toFixed(1) : String(x));

export function initImages() {
  // ── Optimizer ──────────────────────────────────────────
  const modeRadios = document.querySelectorAll("input[name=io-mode]");
  for (const r of modeRadios) r.onchange = () => {
    const custom = $("input[name=io-mode]:checked").value === "custom";
    $("#io-factor-wrap").hidden = custom;
    $("#io-custom-wrap").hidden = !custom;
  };
  $("#io-sharp").onchange = (e) => ($("#io-sa").disabled = !e.target.checked);

  $("#io-go").addEventListener("click", async () => {
    const files = [...$("#io-files").files];
    const msg = $("#io-msg"), out = $("#io-out");
    out.innerHTML = "";
    if (!files.length) return setMsg(msg, "Upload one or more images above, then click Optimize All.", "warn");
    const custom = $("input[name=io-mode]:checked").value === "custom";
    const fmt = $("#io-fmt").value, ext = { JPEG: "jpg", PNG: "png", WEBP: "webp" }[fmt];
    const opts = {
      sharpen: $("#io-sharp").checked, sharpenAmount: +$("#io-sa").value,
      enhanceColor: $("#io-color").checked, fmt, quality: +$("#io-q").value,
    };
    const btn = $("#io-go");
    btn.disabled = true;
    const zip = new JSZip();
    const uniq = uniqueNamer();
    let ok = 0;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setMsg(msg, `⏳ Optimizing ${i + 1}/${files.length}: ${esc(file.name)}`);
      try {
        let scale = +$("#io-factor").value;
        if (custom) {
          const probe = await decodeToCanvas(file);
          scale = Math.min(+$("#io-w").value / probe.width, +$("#io-h").value / probe.height);
        }
        const { blob, orig, size } = await optimizeImage(file, { ...opts, scale });
        const outName = uniq(`${baseName(file.name)}_x${pyFloat(scale)}.${ext}`);
        zip.file(outName, blob);
        ok++;
        const fig = document.createElement("figure");
        fig.innerHTML = `<img alt=""><figcaption><b>${esc(file.name.slice(0, 28))}</b><br>
          <code>${orig[0]}×${orig[1]}</code> → <code>${size[0]}×${size[1]}</code><br>
          ${humanSize(file.size)} → ${blob.size > file.size ? "📈" : "📉"} <b>${humanSize(blob.size)}</b></figcaption>`;
        fig.querySelector("img").src = URL.createObjectURL(blob);
        fig.dataset.name = outName;
        out.appendChild(fig);
      } catch (err) {
        out.insertAdjacentHTML("beforeend", `<figure><figcaption class="msg err">❌ ${esc(file.name)}: ${esc(err.message || err)}</figcaption></figure>`);
      }
    }
    btn.disabled = false;
    if (!ok) return setMsg(msg, "❌ No images could be optimized.", "err");
    const zblob = await zip.generateAsync({ type: "blob" });
    setMsg(msg, `✅ ${ok} image(s) optimized!`, "ok");
    msg.appendChild(downloadButton(zblob, `optimized_${stamp()}.zip`, "⬇️ Download All (ZIP)"));
  });

  // ── WebP converter ────────────────────────────────────
  $("#wp-go").addEventListener("click", async () => {
    const files = [...$("#wp-files").files];
    const msg = $("#wp-msg"), out = $("#wp-out");
    out.innerHTML = "";
    if (!files.length) return setMsg(msg, "Upload images above to convert them to WebP.", "warn");
    const quality = +$("#wp-q").value, lossless = $("#wp-lossless").checked;
    const btn = $("#wp-go");
    btn.disabled = true;
    const zip = new JSZip();
    const rows = [];
    const uniq = uniqueNamer();
    let tOrig = 0, tNew = 0, ok = 0;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setMsg(msg, `⏳ Converting ${i + 1}/${files.length}: ${esc(file.name)}`);
      tOrig += file.size;
      try {
        const blob = await convertToWebp(file, { quality, lossless });
        tNew += blob.size;
        ok++;
        zip.file(uniq(`${baseName(file.name)}.webp`), blob);
        const saved = Math.round((1 - blob.size / file.size) * 1000) / 10;
        rows.push([file.name, humanSize(file.size), humanSize(blob.size), `${saved}%`, "✅"]);
      } catch (err) {
        rows.push([file.name, humanSize(file.size), "—", "—", `❌ ${err.message || err}`]);
      }
    }
    btn.disabled = false;
    const totalSaved = tOrig ? Math.round((1 - tNew / tOrig) * 1000) / 10 : 0;
    out.innerHTML = `<div class="tbl-wrap"><table class="tbl" id="wp-table"><tr><th>File</th><th>Original</th><th>WebP</th><th>Saved</th><th>Status</th></tr>
      ${rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</table></div>
      <div class="metrics">
        <div class="metric"><span>Total original</span><b>${humanSize(tOrig)}</b></div>
        <div class="metric"><span>Total WebP</span><b>${humanSize(tNew)}</b></div>
        <div class="metric"><span>Space saved</span><b>${totalSaved}%</b></div>
      </div>`;
    if (!ok) return setMsg(msg, "❌ No images could be converted.", "err");
    setMsg(msg, `✅ ${ok} image(s) converted!`, "ok");
    const zblob = await zip.generateAsync({ type: "blob" });
    out.appendChild(downloadButton(zblob, `webp_converted_${stamp()}.zip`, "⬇️ Download All WebP (ZIP)"));
  });
}
