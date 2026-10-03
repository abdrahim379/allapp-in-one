// Video Upscaler — 5-stage ffmpeg pipeline (denoise → pre-sharpen → lanczos → post-sharpen → color).
import { $, esc, extOf, baseName, humanSize, downloadButton } from "./util.js";
import { withFF, run, probe, writeFile, rm, jobCard, isMultiThread } from "./ff.js";

const AUTO_CRF = { 720: 16, 1080: 16, 1440: 15, 2160: 14 };
const AUTO_BITRATE = { 720: 6000, 1080: 10000, 1440: 16000, 2160: 22000 };
const MODES = {
  max: { denoise: 1.5, pre: 1.0, post: 0.6, contrast: 1.06, sat: 1.10, bright: 0.01, preset: "slow", label: "🔥 Maximum" },
  bal: { denoise: 0.8, pre: 0.6, post: 0.4, contrast: 1.03, sat: 1.05, bright: 0.0, preset: "medium", label: "⚡ Balanced" },
  light: { denoise: 0.3, pre: 0.3, post: 0.2, contrast: 1.01, sat: 1.02, bright: 0.0, preset: "fast", label: "🌿 Light" },
};
// Advanced slider defaults — a slider only overrides the preset when moved off these.
const ADV_DEFAULTS = { denoise: 1.5, pre: 1.0, post: 0.6, contrast: 1.06, sat: 1.10, bright: 0.01, preset: "medium" };

export function autoTarget(h) {
  if (h <= 360) return [1280, 720];
  if (h <= 720) return [1920, 1080];
  if (h <= 1080) return [2560, 1440];
  return [3840, 2160];
}

export function buildFilters(tw, th, s) {
  const r = (x, n = 2) => Math.round(x * 10 ** n) / 10 ** n;
  const f = [];
  if (s.denoise > 0) f.push(`hqdn3d=${r(s.denoise)}:${r(s.denoise * 0.75)}:${r(s.denoise * 4)}:${r(s.denoise * 3)}`);
  if (s.pre > 0) f.push(`unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=${r(s.pre)}:chroma_msize_x=5:chroma_msize_y=5:chroma_amount=${r(s.pre * 0.4)}`);
  f.push(`scale=${tw}:${th}:flags=lanczos+accurate_rnd+full_chroma_inp+full_chroma_int:force_original_aspect_ratio=decrease,pad=${tw}:${th}:(ow-iw)/2:(oh-ih)/2:black,setsar=1`);
  if (s.post > 0) f.push(`unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount=${r(s.post)}:chroma_msize_x=3:chroma_msize_y=3:chroma_amount=${r(s.post * 0.3)}`);
  f.push(`eq=contrast=${r(s.contrast, 3)}:brightness=${r(s.bright, 3)}:saturation=${r(s.sat, 3)}:gamma=1.02`);
  f.push("format=yuv420p");
  return f.join(",");
}

export function initUpscale() {
  $("#up-go").addEventListener("click", async () => {
    const file = $("#up-file").files[0];
    const out = $("#up-out");
    out.innerHTML = "";
    if (!file) { out.innerHTML = `<div class="msg warn">⬆️ Upload a video above — the app will automatically analyze and enhance it.</div>`; return; }

    const s = { ...MODES[$("#up-mode").value] };
    const adv = {
      denoise: +$("#up-dn").value, pre: +$("#up-pre").value, post: +$("#up-post").value,
      contrast: +$("#up-con").value, sat: +$("#up-sat").value, bright: +$("#up-br").value, preset: $("#up-preset").value,
    };
    for (const k of Object.keys(ADV_DEFAULTS)) if (adv[k] !== ADV_DEFAULTS[k]) s[k] = adv[k];

    const btn = $("#up-go");
    btn.disabled = true;
    const job = jobCard(out, `🎬 ${file.name}`);
    job.status("⏳ Loading video engine…");
    try {
      await withFF(async (f) => {
        const inp = `up_in${extOf(file.name) || ".mp4"}`, outF = "up_out.mp4";
        await writeFile(f, inp, file);
        const meta = await probe(f, inp);
        const ow = meta.width || 1280, oh = meta.height || 720, ofps = meta.fps || 30, dur = meta.duration || 0;
        const tv = $("#up-target").value;
        const [tw, th] = tv === "auto" ? autoTarget(oh) : tv.split(":").map(Number);
        const crf = AUTO_CRF[th] ?? 16, bitrate = AUTO_BITRATE[th] ?? 10000;
        const info = document.createElement("div");
        info.className = "card-info";
        info.innerHTML = `<b>🔎 Auto Analysis Result</b><br>
          Source: <code>${ow}×${oh}</code> @ <code>${ofps.toFixed(1)}fps</code> · <code>${dur.toFixed(1)}s</code>${meta.hasAudio ? "" : " · no audio"}<br>
          Target: <b><code>${tw}×${th}</code></b> · Scale factor: <b>${Math.round((tw / ow) * 100) / 100}×</b><br>
          Enhancement: <b>${s.label}</b> · CRF: <b>${crf}</b> · Preset: <b>${s.preset}</b>
          ${isMultiThread() ? "" : `<br><span class="tiny">Single-thread mode (this browser) — large targets like 4K can take a long time.</span>`}`;
        out.insertBefore(info, job.el);

        const args = ["-y", "-hide_banner", "-i", inp, "-vf", buildFilters(tw, th, s),
          "-c:v", "libx264", "-preset", s.preset, "-crf", String(crf),
          "-maxrate", `${bitrate}k`, "-bufsize", `${bitrate * 2}k`, "-pix_fmt", "yuv420p",
          "-threads", isMultiThread() ? "4" : "1",
          ...(meta.hasAudio ? ["-c:a", "aac", "-ar", "44100", "-ac", "2"] : ["-an"]),
          "-map_metadata", "-1", "-movflags", "+faststart", outF];
        job.log(`$ ffmpeg ${args.join(" ")}`);
        const stages = ["🧹 Stage 1: Deblocking & denoising compression artifacts…", "✨ Stage 2: Pre-sharpening text & edges…",
          "🔍 Stage 3: LANCZOS upscaling pixels…", "🎯 Stage 4: Post-sharpening to restore detail…", "🎨 Stage 5: Color & contrast enhancement…"];
        const rc = await run(f, args, {
          totalSecs: dur,
          onLog: job.log,
          onProgress: (p) => { job.progress(p); job.status(`<b>${stages[Math.min(4, Math.floor(p / 20))]}</b><br>⚙️ Overall: <b>${p}%</b> complete`); },
        });
        if (rc === 0) {
          const data = await f.readFile(outF);
          const blob = new Blob([data.buffer], { type: "video/mp4" });
          const name = `${baseName(file.name)}_enhanced_${tw}x${th}.mp4`;
          job.progress(100);
          job.status(`✅ Enhancement complete! <b>${esc(name)}</b> — ${humanSize(blob.size)}`);
          out.appendChild(downloadButton(blob, name, `⬇️ Download Enhanced Video  ${tw}×${th}  (${humanSize(blob.size)})`));
        } else {
          job.status(`<span style="color:var(--err)">❌ Enhancement failed (exit code ${rc}). Check the log above.</span>`);
        }
        await rm(f, inp, outF);
      });
    } catch (err) {
      job.status(`<span style="color:var(--err)">❌ ${esc(err.message || err)}</span>`);
    } finally {
      btn.disabled = false;
    }
  });
}
