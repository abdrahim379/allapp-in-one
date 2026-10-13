// Refresh Metadata: wipe every old tag from photos and videos, then write fresh
// phone-camera metadata (Saudi location, Saudi time +03:00, chosen phone model).
// Photos are re-encoded to a clean JPEG with a new EXIF block; videos are
// remuxed with ffmpeg.wasm (no re-encode, so quality is untouched).
import { $, esc, extOf, stamp, humanSize, downloadButton, uniqueNamer } from "./util.js";
import { withFF, run, probe, writeFile, rm, jobCard } from "./ff.js";

// lat, lon, altitude (m)
const CITIES = {
  riyadh: ["Riyadh", 24.7136, 46.6753, 612],
  jeddah: ["Jeddah", 21.5433, 39.1728, 12],
  makkah: ["Makkah", 21.3891, 39.8579, 277],
  madinah: ["Madinah", 24.5247, 39.5692, 608],
  dammam: ["Dammam", 26.4207, 50.0888, 10],
  khobar: ["Al Khobar", 26.2172, 50.1971, 5],
  taif: ["Taif", 21.2703, 40.4158, 1879],
  abha: ["Abha", 18.2465, 42.5117, 2270],
  tabuk: ["Tabuk", 28.3835, 36.5662, 770],
  buraydah: ["Buraydah", 26.3592, 43.9818, 605],
};

// make, model, software, photo lens, focal mm, f-number, Android video handler names
const PHONES = {
  ip16pm: { make: "Apple", model: "iPhone 16 Pro Max", sw: "18.0.1", lens: "iPhone 16 Pro Max back triple camera 6.765mm f/1.78", f: 6.765, fn: 1.78, apple: true },
  ip16p: { make: "Apple", model: "iPhone 16 Pro", sw: "18.0.1", lens: "iPhone 16 Pro back triple camera 6.765mm f/1.78", f: 6.765, fn: 1.78, apple: true },
  ip15pm: { make: "Apple", model: "iPhone 15 Pro Max", sw: "17.6.1", lens: "iPhone 15 Pro Max back triple camera 6.765mm f/1.78", f: 6.765, fn: 1.78, apple: true },
  ip15: { make: "Apple", model: "iPhone 15", sw: "17.6.1", lens: "iPhone 15 back dual wide camera 6.024mm f/1.6", f: 6.024, fn: 1.6, apple: true },
  s24u: { make: "samsung", model: "SM-S928B", sw: "S928BXXS3AXI1", f: 6.3, fn: 1.7, apple: false, android: "14", label: "Galaxy S24 Ultra" },
  s23: { make: "samsung", model: "SM-S911B", sw: "S911BXXS6CXI1", f: 5.4, fn: 1.8, apple: false, android: "14", label: "Galaxy S23" },
};

const rnd = (a, b) => a + Math.random() * (b - a);
const pick = (o) => { const k = Object.keys(o); return k[Math.floor(Math.random() * k.length)]; };
const p2 = (x) => String(x).padStart(2, "0");

// Saudi time (UTC+3, no daylight saving) parts for a UTC epoch.
function ksa(ms) {
  const d = new Date(ms + 3 * 3600_000);
  return { Y: d.getUTCFullYear(), M: p2(d.getUTCMonth() + 1), D: p2(d.getUTCDate()), h: p2(d.getUTCHours()), m: p2(d.getUTCMinutes()), s: p2(d.getUTCSeconds()) };
}

// One fresh identity per file: city point jittered ~2.5 km, time, phone.
function identity(cityKey, phoneKey, baseMs, i) {
  const ck = cityKey === "random" ? pick(CITIES) : cityKey;
  const pk = phoneKey === "random" ? pick(PHONES) : phoneKey;
  const [city, lat0, lon0, alt0] = CITIES[ck];
  const lat = +(lat0 + rnd(-0.022, 0.022)).toFixed(6);
  const lon = +(lon0 + rnd(-0.024, 0.024)).toFixed(6);
  const alt = +(alt0 + rnd(-4, 9)).toFixed(3);
  const ms = baseMs - i * Math.round(rnd(45, 400)) * 1000 - Math.round(rnd(0, 20)) * 1000;
  return { city, lat, lon, alt, ms, phone: PHONES[pk], subsec: String(Math.floor(rnd(100, 999))) };
}

// Phone-style file name (IMG_1234.JPG / 20261013_154210.jpg).
function phoneName(id, video, counter) {
  if (id.phone.apple) return `IMG_${String(counter).padStart(4, "0")}.${video ? "MOV" : "JPG"}`;
  const t = ksa(id.ms);
  return `${t.Y}${t.M}${t.D}_${t.h}${t.m}${t.s}.${video ? "mp4" : "jpg"}`;
}

// ---------------------------------------------------------------- EXIF writer
// Minimal big-endian TIFF/EXIF builder (IFD0 + Exif IFD + GPS IFD).
const T = { BYTE: 1, ASCII: 2, SHORT: 3, LONG: 4, RATIONAL: 5, UNDEF: 7, SRATIONAL: 10 };
const SIZE = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 10: 8 };

function ascii(s) { return [...new TextEncoder().encode(s), 0]; }
function rat(x, den = 10000) { return [Math.round(x * den), den]; }
function dms(v) {
  const a = Math.abs(v), d = Math.floor(a), mf = (a - d) * 60, m = Math.floor(mf), s = (mf - m) * 60;
  return [[d, 1], [m, 1], rat(s, 10000)];
}

function buildExif(id, w, h) {
  const t = ksa(id.ms), u = new Date(id.ms);
  const dt = `${t.Y}:${t.M}:${t.D} ${t.h}:${t.m}:${t.s}`;
  const ph = id.phone;
  const iso = [32, 40, 50, 64, 80, 100][Math.floor(rnd(0, 6))];
  const exp = [60, 100, 120, 125, 250, 500][Math.floor(rnd(0, 6))];
  const ifd0 = [
    [0x010f, T.ASCII, ascii(ph.make)], [0x0110, T.ASCII, ascii(ph.model)], [0x0112, T.SHORT, [1]],
    [0x011a, T.RATIONAL, [[72, 1]]], [0x011b, T.RATIONAL, [[72, 1]]], [0x0128, T.SHORT, [2]],
    [0x0131, T.ASCII, ascii(ph.sw)], [0x0132, T.ASCII, ascii(dt)],
    ...(ph.apple ? [[0x013c, T.ASCII, ascii(ph.model)]] : []),
    [0x8769, T.LONG, ["EXIF"]], [0x8825, T.LONG, ["GPS"]],
  ];
  const exif = [
    [0x829a, T.RATIONAL, [[1, exp]]], [0x829d, T.RATIONAL, [rat(ph.fn, 100)]], [0x8822, T.SHORT, [2]],
    [0x8827, T.SHORT, [iso]], [0x9000, T.UNDEF, [...new TextEncoder().encode("0232")]],
    [0x9003, T.ASCII, ascii(dt)], [0x9004, T.ASCII, ascii(dt)],
    [0x9010, T.ASCII, ascii("+03:00")], [0x9011, T.ASCII, ascii("+03:00")], [0x9012, T.ASCII, ascii("+03:00")],
    [0x9207, T.SHORT, [5]], [0x9209, T.SHORT, [16]], [0x920a, T.RATIONAL, [rat(ph.f, 1000)]],
    [0x9291, T.ASCII, ascii(id.subsec)], [0x9292, T.ASCII, ascii(id.subsec)],
    [0xa001, T.SHORT, [1]], [0xa002, T.LONG, [w]], [0xa003, T.LONG, [h]],
    [0xa402, T.SHORT, [0]], [0xa403, T.SHORT, [0]],
    ...(ph.lens ? [[0xa433, T.ASCII, ascii(ph.make)], [0xa434, T.ASCII, ascii(ph.lens)]] : []),
  ];
  const gps = [
    [0x0000, T.BYTE, [2, 2, 0, 0]], [0x0001, T.ASCII, ascii("N")], [0x0002, T.RATIONAL, dms(id.lat)],
    [0x0003, T.ASCII, ascii("E")], [0x0004, T.RATIONAL, dms(id.lon)],
    [0x0005, T.BYTE, [0]], [0x0006, T.RATIONAL, [rat(id.alt, 1000)]],
    [0x0007, T.RATIONAL, [[u.getUTCHours(), 1], [u.getUTCMinutes(), 1], [u.getUTCSeconds(), 1]]],
    [0x000c, T.ASCII, ascii("K")], [0x000d, T.RATIONAL, [[0, 1]]],
    [0x0010, T.ASCII, ascii("T")], [0x0011, T.RATIONAL, [rat(rnd(0, 359.9), 100)]],
    [0x001d, T.ASCII, ascii(`${u.getUTCFullYear()}:${p2(u.getUTCMonth() + 1)}:${p2(u.getUTCDate())}`)],
    [0x001f, T.RATIONAL, [rat(rnd(3, 14), 100)]],
  ];

  // Layout: header(8) | IFD0 | Exif IFD | GPS IFD | data area
  const ifdLen = (n) => 2 + n * 12 + 4;
  const off = { IFD0: 8 };
  off.EXIF = off.IFD0 + ifdLen(ifd0.length);
  off.GPS = off.EXIF + ifdLen(exif.length);
  let dataOff = off.GPS + ifdLen(gps.length);
  const bytes = [];
  const u16 = (v) => [(v >> 8) & 255, v & 255];
  const u32 = (v) => [(v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255];
  const data = [];

  function encodeVals(type, vals) {
    const out = [];
    for (const v of vals) {
      if (type === T.SHORT) out.push(...u16(v));
      else if (type === T.LONG) out.push(...u32(typeof v === "string" ? off[v] : v));
      else if (type === T.RATIONAL || type === T.SRATIONAL) out.push(...u32(v[0]), ...u32(v[1]));
      else out.push(v & 255);
    }
    return out;
  }
  function ifd(entries) {
    entries.sort((a, b) => a[0] - b[0]);
    const out = [...u16(entries.length)];
    for (const [tag, type, vals] of entries) {
      const enc = encodeVals(type, vals);
      const count = type === T.RATIONAL || type === T.SRATIONAL ? vals.length : enc.length / SIZE[type];
      out.push(...u16(tag), ...u16(type), ...u32(count));
      if (enc.length <= 4) {
        out.push(...enc, ...new Array(4 - enc.length).fill(0));
      } else {
        out.push(...u32(dataOff));
        data.push(...enc);
        dataOff += enc.length;
        if (enc.length % 2) { data.push(0); dataOff += 1; }
      }
    }
    out.push(...u32(0));
    return out;
  }
  bytes.push(0x4d, 0x4d, 0x00, 0x2a, ...u32(8));
  bytes.push(...ifd(ifd0), ...ifd(exif), ...ifd(gps), ...data);
  const head = [...new TextEncoder().encode("Exif"), 0, 0];
  const payload = [...head, ...bytes];
  return new Uint8Array([0xff, 0xe1, ...u16(payload.length + 2), ...payload]);
}

// Re-encode to a clean JPEG (drops every old marker) and insert the new EXIF.
async function refreshPhoto(file, id) {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const c = document.createElement("canvas");
  c.width = bmp.width;
  c.height = bmp.height;
  const g = c.getContext("2d");
  g.fillStyle = "#fff";
  g.fillRect(0, 0, c.width, c.height);
  g.drawImage(bmp, 0, 0);
  bmp.close?.();
  const jpg = new Uint8Array(await (await new Promise((r) => c.toBlob(r, "image/jpeg", 0.95))).arrayBuffer());
  // Skip SOI and any APPn segments the encoder added (JFIF), keep the rest.
  let i = 2;
  while (jpg[i] === 0xff && jpg[i + 1] >= 0xe0 && jpg[i + 1] <= 0xef) i += 2 + ((jpg[i + 2] << 8) | jpg[i + 3]);
  const exif = buildExif(id, c.width, c.height);
  const out = new Uint8Array(2 + exif.length + jpg.length - i);
  out.set([0xff, 0xd8], 0);
  out.set(exif, 2);
  out.set(jpg.subarray(i), 2 + exif.length);
  return { blob: new Blob([out], { type: "image/jpeg" }), w: c.width, h: c.height };
}

// ---------------------------------------------------------------- video
function iso6709(id, withAlt) {
  const f = (v, w) => `${v >= 0 ? "+" : "-"}${Math.abs(v).toFixed(4).padStart(w + 5, "0")}`;
  return `${f(id.lat, 2)}${f(id.lon, 3)}${withAlt ? `+${id.alt.toFixed(3)}` : ""}/`;
}

function videoArgs(inp, out, id, codec) {
  const t = ksa(id.ms), ph = id.phone;
  const utc = new Date(id.ms).toISOString().replace(/\.\d{3}Z$/, ".000000Z");
  // Video is copied untouched; H.264 "user data" SEI notes (encoder name and
  // settings, e.g. x264/CapCut) are dropped. Audio becomes a clean AAC track.
  const a = ["-i", inp, "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy",
    ...(codec === "h264" ? ["-bsf:v", "filter_units=remove_types=6"] : []),
    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
    "-map_metadata", "-1", "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1", "-map_chapters", "-1",
    "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
    "-metadata", `creation_time=${utc}`, "-metadata:s", `creation_time=${utc}`,
    "-metadata:s:v", `handler_name=${ph.apple ? "Core Media Video" : "VideoHandle"}`,
    "-metadata:s:a", `handler_name=${ph.apple ? "Core Media Audio" : "SoundHandle"}`,
    "-metadata:s:v", "language=und", "-metadata:s:a", "language=und"];
  if (ph.apple) {
    a.push("-movflags", "+use_metadata_tags+faststart",
      "-metadata", `com.apple.quicktime.location.accuracy.horizontal=${rnd(4, 15).toFixed(6)}`,
      "-metadata", `com.apple.quicktime.location.ISO6709=${iso6709(id, true)}`,
      "-metadata", `com.apple.quicktime.make=${ph.make}`,
      "-metadata", `com.apple.quicktime.model=${ph.model}`,
      "-metadata", `com.apple.quicktime.software=${ph.sw}`,
      "-metadata", `com.apple.quicktime.creationdate=${t.Y}-${t.M}-${t.D}T${t.h}:${t.m}:${t.s}+0300`,
      "-f", "mov");
  } else {
    a.push("-movflags", "+use_metadata_tags+faststart", "-brand", "mp42",
      "-metadata", `location=${iso6709(id, false)}`,
      "-metadata", `com.android.version=${ph.android}`,
      "-metadata", "com.android.capture.fps=30.000000", "-f", "mp4");
  }
  a.push(out);
  return a;
}

// ffmpeg's MOV writer hard-codes "FFMP" as the sample-entry vendor; iPhones write
// "appl". Patch it inside the moov box only (never in the media data).
function patchVendor(buf, vendor) {
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const want = [0x46, 0x46, 0x4d, 0x50], rep = [...vendor].map((c) => c.charCodeAt(0));
  for (let pos = 0; pos + 8 <= buf.length;) {
    let size = dv.getUint32(pos);
    const type = String.fromCharCode(...buf.subarray(pos + 4, pos + 8));
    if (size === 1) size = Number(dv.getBigUint64(pos + 8));
    else if (size === 0) size = buf.length - pos;
    if (size < 8) break;
    if (type === "moov") {
      for (let i = pos; i + 4 <= pos + size; i++) {
        if (buf[i] === want[0] && buf[i + 1] === want[1] && buf[i + 2] === want[2] && buf[i + 3] === want[3]) buf.set(rep, i);
      }
    }
    pos += size;
  }
  return buf;
}

// ---------------------------------------------------------------- UI
export function initMeta() {
  const btn = $("#md-go"), out = $("#md-out"), msg = $("#md-msg");
  btn.addEventListener("click", async () => {
    const files = [...$("#md-files").files];
    out.replaceChildren();
    msg.className = "msg";
    msg.textContent = "";
    if (!files.length) { msg.className = "msg err"; msg.textContent = "Upload at least one photo or video first."; return; }
    const cityKey = $("#md-city").value, phoneKey = $("#md-phone").value;
    const when = $("#md-when").value;
    const baseMs = when ? new Date(`${when}:00+03:00`).getTime() : Date.now() - Math.round(rnd(60, 600)) * 1000;
    if (!Number.isFinite(baseMs)) { msg.className = "msg err"; msg.textContent = "The date is not valid."; return; }
    btn.disabled = true;
    const uniq = uniqueNamer();
    let counter = Math.floor(rnd(1200, 8900));
    const results = [];
    const rows = [];
    const videos = [], photos = [];
    files.forEach((f, i) => ((f.type.startsWith("video/") || /\.(mp4|mov|m4v|3gp)$/i.test(f.name)) ? videos : photos).push([f, i]));

    for (const [file, i] of photos) {
      const id = identity(cityKey, phoneKey, baseMs, i);
      try {
        const r = await refreshPhoto(file, id);
        const name = uniq(phoneName(id, false, counter++));
        results.push({ name, blob: r.blob });
        rows.push([file.name, name, id, `${r.w}×${r.h}`, r.blob.size]);
      } catch (e) {
        rows.push([file.name, null, id, `could not read this image (${esc(e.message || e)})`, 0]);
      }
    }

    if (videos.length) {
      try {
        await withFF(async (f) => {
          for (const [file, i] of videos) {
            const id = identity(cityKey, phoneKey, baseMs, i);
            const name = uniq(phoneName(id, true, counter++));
            const job = jobCard(out, `🎬 ${file.name}`);
            const inp = `md_in${extOf(file.name) || ".mp4"}`, tmp = id.phone.apple ? "md_out.mov" : "md_out.mp4";
            try {
              await writeFile(f, inp, file);
              const meta = await probe(f, inp);
              const head = [];
              await run(f, ["-hide_banner", "-i", inp], { onLog: (l) => head.push(l) });
              const codec = (/Stream #\d+:\d+.*?: Video: (\w+)/.exec(head.join("\n")) || [])[1] || "";
              const args = videoArgs(inp, tmp, id, codec);
              job.log(`$ ffmpeg ${args.join(" ")}`);
              const rc = await run(f, ["-y", "-hide_banner", ...args], { totalSecs: meta.duration, onLog: job.log, onProgress: (p) => job.progress(p) });
              if (rc !== 0) throw new Error(`FFmpeg error code ${rc} — open the logs for details`);
              let data = await f.readFile(tmp);
              if (id.phone.apple) data = patchVendor(data, "appl");
              const blob = new Blob([data.buffer], { type: id.phone.apple ? "video/quicktime" : "video/mp4" });
              results.push({ name, blob });
              rows.push([file.name, name, id, meta.width ? `${meta.width}×${meta.height}` : "", blob.size]);
              job.status(`✅ ${esc(name)} · ${humanSize(blob.size)}`);
            } catch (e) {
              rows.push([file.name, null, id, esc(e.message || e), 0]);
              job.status(`<span style="color:var(--err)">${esc(e.message || e)}</span>`);
            } finally {
              await rm(f, inp, tmp);
            }
          }
        });
      } catch (e) {
        msg.className = "msg err";
        msg.textContent = `Could not start the video engine: ${e.message || e}`;
      }
    }

    btn.disabled = false;
    const tbl = document.createElement("table");
    tbl.className = "tbl";
    tbl.innerHTML = `<tr><th>Original</th><th>New file</th><th>Phone</th><th>Place</th><th>Date (Saudi time)</th></tr>` + rows.map(([o, n, id, info, sz]) => {
      const t = ksa(id.ms);
      return n
        ? `<tr><td>${esc(o)}</td><td><b>${esc(n)}</b><br><span class="tiny">${esc(info)} · ${humanSize(sz)}</span></td><td>${esc(id.phone.label || id.phone.model)}</td>
           <td>${esc(id.city)}<br><span class="tiny">${id.lat.toFixed(5)}, ${id.lon.toFixed(5)}</span></td><td>${t.D}/${t.M}/${t.Y} ${t.h}:${t.m}</td></tr>`
        : `<tr><td>${esc(o)}</td><td colspan="4" style="color:var(--err)">❌ ${info}</td></tr>`;
    }).join("");
    const wrap = document.createElement("div");
    wrap.style.overflowX = "auto";
    wrap.append(tbl);
    out.prepend(wrap);
    if (!results.length) { msg.className = "msg err"; msg.textContent = "No files could be processed."; return; }
    msg.className = "msg ok";
    msg.innerHTML = `✅ ${results.length} file(s) refreshed: all old metadata removed, new phone + Saudi location written.`;
    if (results.length > 1) {
      const zip = new JSZip();
      for (const r of results) zip.file(r.name, r.blob, { date: new Date() });
      const zblob = await zip.generateAsync({ type: "blob", compression: "STORE" });
      out.prepend(downloadButton(zblob, `Refreshed_${stamp()}.zip`, `⬇️ Download All (${results.length} files)`));
    }
    for (const r of results) {
      const b = downloadButton(r.blob, r.name, `⬇️ ${r.name} (${humanSize(r.blob.size)})`);
      b.className = "btn small";
      b.style.margin = "4px";
      out.append(b);
    }
  });
}
