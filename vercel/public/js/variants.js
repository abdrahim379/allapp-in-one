// TikTok Variant Generator — port of the Streamlit ffmpeg pipeline to ffmpeg.wasm.
import { $, $$, esc, extOf, baseName, stamp, humanSize, downloadButton, uniqueNamer } from "./util.js";
import { withFF, run, probe, writeFile, rm, jobCard, isMultiThread } from "./ff.js";

const TW = 1080, TH = 1920, BITRATE = 4000;

const PRESETS = {
  custom: null,
  quick: { variants: ["1"], zoom: "zoom + crop" },
  viral: { variants: ["1", "2", "3", "4"], zoom: "zoom + crop" },
  ultra: { variants: ["1", "2", "3", "4", "5"], zoom: "zoom + crop" },
};

const VARIANT_DEFS = {
  1: { name: "1", hdur: 0.3, intro: false, isec: 0.0, audio: "normal" },
  2: { name: "2", hdur: 0.1, intro: true, isec: 0.01, audio: "normal" },
  3: { name: "3", hdur: 0.1, intro: true, isec: 0.01, audio: "pitch +1%" },
  4: { name: "4", hdur: 0.1, intro: true, isec: 0.01, audio: "pitch -1%" },
  5: { name: "5", hdur: 0.3, intro: false, isec: 0.0, audio: "normal" },
};

const norm = (fps) =>
  `scale=${TW}:${TH}:force_original_aspect_ratio=decrease,pad=${TW}:${TH}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,fps=${fps}`;

export function buildVf(zoom, w, h, fps) {
  const base = [];
  if (zoom === "zoom + crop") base.push("scale=iw*1.01:ih*1.01,crop=iw/1.01:ih/1.01");
  else if (zoom === "zoom inverse + pad") base.push("scale=iw*0.99:ih*0.99,pad=iw/0.99:ih/0.99:(ow-iw)/2:(oh-ih)/2");
  const n = w === TW && h === TH && zoom === "none" ? `setsar=1,format=yuv420p,fps=${fps}` : norm(fps);
  return [...base, n].join(",");
}

// Audio chain from an input label; resample first so pitch math is exact.
function audioChain(mode, label) {
  const fmt = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo";
  if (mode === "pitch +1%") return `${label}aresample=44100,asetrate=44100*1.01,aresample=44100,${fmt}`;
  if (mode === "pitch -1%") return `${label}aresample=44100,asetrate=44100*0.99,aresample=44100,${fmt}`;
  return `${label}aresample=44100,${fmt}`;
}

const silence = (secs) => `anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration=${secs.toFixed(3)},`;

// Audio label for input #idx — real track if present, otherwise silence of same length.
const audioIn = (idx, meta, mode) =>
  meta.hasAudio ? audioChain(mode, `[${idx}:a]`) : audioChain(mode, silence(meta.duration || 1));

/**
 * Build ffmpeg args for one variant. Inputs already in FS:
 *   inp (main), himg / hvid / ovl (optional). metas: probe results.
 * Returns { args, est } where est = expected output seconds.
 */
export function buildArgs(o) {
  const { inp, out, v, fps, zoom, htype, himg, hvid, hkeep, ovl, meta, hmeta } = o;
  const baseVf = buildVf(zoom, meta.width, meta.height, fps);
  const vc = ["-b:v", `${BITRATE}k`, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
    "-threads", isMultiThread() ? "4" : "1",
    "-map_metadata", "-1", "-metadata", `title=Variant_${v.name}`, "-metadata", `creation_time=${new Date().toISOString()}`];
  const ao = ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"];
  const tail = ["-map", "[vout]", "-map", "[aout]", ...vc, ...ao, "-movflags", "+faststart", out];
  const dur = meta.duration || 0;
  const A0 = audioIn(0, meta, v.audio);

  if (v.name === "5" && ovl) {
    // Looped still + shortest=1: a single-frame PNG input deadlocks ffmpeg.wasm when audio is mapped.
    const fc = `[0:v]${baseVf}[base];[1:v]scale=${TW}:${TH}[ov];[base][ov]overlay=0:0:shortest=1[vout];${A0}[aout]`;
    return { args: ["-i", inp, "-loop", "1", "-i", ovl, "-filter_complex", fc, ...tail], est: dur };
  }

  if (htype === "None") {
    if (v.intro && v.isec > 0) {
      const s = v.isec;
      const fc = `color=size=${TW}x${TH}:color=black:rate=${fps}:duration=${s},format=yuv420p,setsar=1[iv];` +
        `${silence(s)}aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[ia];` +
        `[0:v]${baseVf}[vm];${A0}[am];[iv][ia][vm][am]concat=n=2:v=1:a=1[vout][aout]`;
      return { args: ["-i", inp, "-filter_complex", fc, ...tail], est: s + dur };
    }
    const fc = `[0:v]${baseVf}[vout];${A0}[aout]`;
    return { args: ["-i", inp, "-filter_complex", fc, ...tail], est: dur };
  }

  if (htype === "Image overlay" && himg) {
    const fc = `[0:v]${baseVf}[base];[1:v][base]scale2ref=w=iw:h=ih[img][b2];` +
      `[b2][img]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,${v.hdur})'[vout];${A0}[aout]`;
    return { args: ["-i", inp, "-loop", "1", "-t", String(v.hdur), "-i", himg, "-filter_complex", fc, ...tail], est: dur };
  }

  if (htype === "Video prepend" && hvid) {
    const hd = hmeta.duration || 1;
    const ah = hkeep && hmeta.hasAudio ? audioChain(v.audio, "[0:a]") : `${silence(hd)}aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo`;
    const am = meta.hasAudio ? audioChain(v.audio, "[1:a]") : audioChain(v.audio, silence(dur || 1));
    const fc = `[0:v]${norm(fps)}[vh];[1:v]${baseVf}[vm];${ah}[ah];${am}[am];[vh][ah][vm][am]concat=n=2:v=1:a=1[vout][aout]`;
    return { args: ["-i", hvid, "-i", inp, "-filter_complex", fc, ...tail], est: hd + dur };
  }

  if (htype === "Video overlay" && hvid) {
    const fc = `[0:v]${baseVf}[base];[1:v]${norm(fps)}[hv];` +
      `[base][hv]overlay=(W-w)/2:(H-h)/2:eof_action=pass:enable='between(t,0,${v.hdur})'[vout];${A0}[aout]`;
    return { args: ["-i", inp, "-i", hvid, "-filter_complex", fc, ...tail], est: dur };
  }

  // Hook type chosen but no hook file uploaded → plain variant.
  const fc = `[0:v]${baseVf}[vout];${A0}[aout]`;
  return { args: ["-i", inp, "-filter_complex", fc, ...tail], est: dur };
}

export function initVariants() {
  const htypeSel = $("#vg-htype");
  const syncHooks = () => {
    const h = htypeSel.value;
    $("#vg-himg-wrap").hidden = h !== "Image overlay";
    $("#vg-hvid-wrap").hidden = !(h === "Video prepend" || h === "Video overlay");
    $("#vg-hkeep-wrap").hidden = h !== "Video prepend";
    if (h !== "None") $("#vg-hooks").open = true;
  };
  htypeSel.onchange = syncHooks;
  syncHooks();

  $("#vg-preset").onchange = (e) => {
    const p = PRESETS[e.target.value];
    if (!p) return;
    for (const c of $$(".vg-v")) c.checked = p.variants.includes(c.value);
    for (const r of $$("input[name=vg-zoom]")) r.checked = r.value === p.zoom;
  };

  $("#vg-go").addEventListener("click", async () => {
    const files = [...$("#vg-files").files];
    const out = $("#vg-out");
    out.innerHTML = "";
    if (!files.length) { out.innerHTML = `<div class="msg err">Upload videos above, then click Generate.</div>`; return; }
    const sel = $$(".vg-v").filter((c) => c.checked).map((c) => c.value);
    if (!sel.length) { out.innerHTML = `<div class="msg err">Select at least one variant.</div>`; return; }

    const zoom = $("input[name=vg-zoom]:checked").value;
    const fps = +$("#vg-fps").value;
    const htype = htypeSel.value;
    const himgF = $("#vg-himg").files[0], hvidF = $("#vg-hvid").files[0], ovlF = $("#vg-ovl").files[0];
    const hkeep = $("#vg-hkeep").checked;
    const variants = sel.map((k) => VARIANT_DEFS[k]);
    const totalTasks = files.length * variants.length;

    const btn = $("#vg-go");
    btn.disabled = true;
    $("#vg-help").hidden = true;
    const overall = document.createElement("div");
    overall.innerHTML = `<div class="progress"><div></div></div><div class="st msg">⏳ Loading video engine…</div>`;
    out.appendChild(overall);
    const oBar = overall.querySelector(".progress > div"), oSt = overall.querySelector(".st");
    const results = [];
    const uniq = uniqueNamer();
    let done = 0;

    try {
      await withFF(async (f) => {
        if (!isMultiThread()) oSt.innerHTML += `<br><span class="tiny">Single-thread mode (this browser) — encoding will be slower.</span>`;
        const hookNames = {};
        if (himgF) { hookNames.himg = `hook_img${extOf(himgF.name) || ".png"}`; await writeFile(f, hookNames.himg, himgF); }
        if (hvidF) { hookNames.hvid = `hook_vid${extOf(hvidF.name) || ".mp4"}`; await writeFile(f, hookNames.hvid, hvidF); }
        if (ovlF) { hookNames.ovl = "overlay.png"; await writeFile(f, hookNames.ovl, ovlF); }
        const hmeta = hookNames.hvid ? await probe(f, hookNames.hvid) : null;

        for (let vi = 0; vi < files.length; vi++) {
          const file = files[vi];
          const h = document.createElement("h3");
          h.textContent = `🎬 Video ${vi + 1}/${files.length}: ${file.name}`;
          out.appendChild(h);
          const inp = `input${extOf(file.name) || ".mp4"}`;
          await writeFile(f, inp, file);
          const meta = await probe(f, inp);

          for (const v of variants) {
            const outName = uniq(`${baseName(file.name)}_v${v.name}.mp4`);
            oSt.innerHTML = `Video <b>${vi + 1}</b> · Variant <b>${v.name}</b> · <b>${done}/${totalTasks}</b> done`;
            const job = jobCard(out, `▶️ Variant ${v.name}`);
            try {
              const { args, est } = buildArgs({
                inp, out: "out.mp4", v, fps, zoom, htype,
                himg: hookNames.himg, hvid: hookNames.hvid, ovl: hookNames.ovl, hkeep, meta, hmeta,
              });
              job.log(`$ ffmpeg ${args.join(" ")}`);
              const t0 = performance.now();
              const rc = await run(f, ["-y", "-hide_banner", ...args], {
                totalSecs: est,
                onLog: job.log,
                onProgress: (p) => { job.progress(p); job.status(`<b>${p}%</b>`); },
              });
              if (rc === 0) {
                const data = await f.readFile("out.mp4");
                const blob = new Blob([data.buffer], { type: "video/mp4" });
                results.push({ name: outName, blob });
                job.status(`✅ Variant ${v.name} done — ${humanSize(blob.size)} in ${((performance.now() - t0) / 1000).toFixed(0)}s`);
              } else {
                job.status(`<span style="color:var(--err)">FFmpeg error code ${rc}</span> — open the logs for details.`);
              }
            } catch (err) {
              job.status(`<span style="color:var(--err)">Error: ${esc(err.message || err)}</span>`);
            } finally {
              await rm(f, "out.mp4");
            }
            done++;
            oBar.style.width = `${(done / totalTasks) * 100}%`;
          }
          await rm(f, inp);
        }
        await rm(f, ...Object.values(hookNames));
      });
    } catch (err) {
      oSt.className = "st msg err";
      oSt.textContent = `Could not start the video engine: ${err.message || err}`;
      btn.disabled = false;
      return;
    }

    btn.disabled = false;
    const h = document.createElement("h2");
    h.textContent = "📦 All Done";
    out.appendChild(h);
    if (!results.length) {
      out.insertAdjacentHTML("beforeend", `<div class="msg err">No variants generated successfully.</div>`);
      oSt.textContent = "Finished with errors.";
      return;
    }
    oSt.className = "st msg ok";
    oSt.innerHTML = `🎉 ${results.length} variant(s) ready!`;
    const zip = new JSZip();
    for (const r of results) zip.file(r.name, r.blob);
    const zblob = await zip.generateAsync({ type: "blob", compression: "STORE" });
    out.appendChild(downloadButton(zblob, `TikTok_Variants_${stamp()}.zip`, `⬇️ Download All (${results.length} files)`));
    for (const r of results) {
      const b = downloadButton(r.blob, r.name, `⬇️ ${r.name} (${humanSize(r.blob.size)})`);
      b.className = "btn small";
      b.style.margin = "4px";
      out.appendChild(b);
    }
  });
}
