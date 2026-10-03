// ffmpeg.wasm wrapper: lazy load, one job at a time, log + progress hooks.
import { FFmpeg } from "/vendor/ffmpeg/index.js";

let ff = null;
let loading = null;
let queue = Promise.resolve();
let logSink = null;

export const isMultiThread = () => self.crossOriginIsolated === true;

export function loadFF() {
  if (ff) return Promise.resolve(ff);
  if (!loading) {
    loading = (async () => {
      const f = new FFmpeg();
      f.on("log", ({ message }) => logSink && logSink(message));
      const mt = isMultiThread();
      const base = `${location.origin}/vendor/${mt ? "ffmpeg-core-mt" : "ffmpeg-core"}`;
      await f.load({
        coreURL: `${base}/ffmpeg-core.js`,
        wasmURL: `${base}/ffmpeg-core.wasm`,
        ...(mt ? { workerURL: `${base}/ffmpeg-core.worker.js` } : {}),
      });
      ff = f;
      return f;
    })().catch((e) => { loading = null; throw e; });
  }
  return loading;
}

// Serialize all ffmpeg work (the wasm instance can only run one command).
export function withFF(fn) {
  const run = queue.then(async () => fn(await loadFF()));
  queue = run.catch(() => {});
  return run;
}

const TIME_RE = /time=(\d+):(\d+):(\d+(?:\.\d+)?)/;

// Run ffmpeg args; onLog(line), onProgress(pct 0-100) using expected duration.
export async function run(f, args, { totalSecs = 0, onLog, onProgress } = {}) {
  logSink = (line) => {
    onLog && onLog(line);
    const m = TIME_RE.exec(line);
    if (m && totalSecs && onProgress) {
      const t = +m[1] * 3600 + +m[2] * 60 + parseFloat(m[3]);
      onProgress(Math.max(0, Math.min(99, Math.floor((t / totalSecs) * 100))));
    }
  };
  try {
    const rc = await f.exec(args);
    onProgress && onProgress(rc === 0 ? 100 : 0);
    return rc;
  } finally {
    logSink = null;
  }
}

// Probe a file already written to the FS: duration, size, fps, audio presence.
export async function probe(f, name) {
  const lines = [];
  logSink = (l) => lines.push(l);
  try { await f.exec(["-hide_banner", "-i", name]); } finally { logSink = null; }
  const txt = lines.join("\n");
  const meta = { duration: 0, width: null, height: null, fps: null, hasAudio: /Stream #\d+:\d+.*: Audio:/.test(txt) };
  const d = /Duration: (\d+):(\d+):(\d+(?:\.\d+)?)/.exec(txt);
  if (d) meta.duration = +d[1] * 3600 + +d[2] * 60 + parseFloat(d[3]);
  const v = /Stream #\d+:\d+.*: Video:.*?(\d{2,5})x(\d{2,5})/.exec(txt);
  if (v) { meta.width = +v[1]; meta.height = +v[2]; }
  const fr = /, ([\d.]+) fps/.exec(txt) || /, ([\d.]+) tbr/.exec(txt);
  if (fr) meta.fps = parseFloat(fr[1]);
  // Rotated phone videos report coded size; swap for display orientation.
  if (/rotation of -?90|rotate\s*:\s*-?90|rotate\s*:\s*270/.test(txt) && meta.width) {
    [meta.width, meta.height] = [meta.height, meta.width];
  }
  return meta;
}

export async function writeFile(f, name, file) {
  await f.writeFile(name, new Uint8Array(await file.arrayBuffer()));
}

export async function rm(f, ...names) {
  for (const n of names) { try { await f.deleteFile(n); } catch { /* not there */ } }
}

// Job card UI used by both video tools.
export function jobCard(parent, title) {
  const el = document.createElement("div");
  el.className = "job";
  el.innerHTML = `<h4></h4><div class="progress"><div></div></div><div class="st"></div>
    <details><summary class="tiny">FFmpeg logs</summary><pre></pre></details>`;
  el.querySelector("h4").textContent = title;
  parent.appendChild(el);
  const bar = el.querySelector(".progress > div"), st = el.querySelector(".st"), pre = el.querySelector("pre");
  let buf = [];
  return {
    el,
    progress(p) { bar.style.width = `${p}%`; },
    status(html) { st.innerHTML = html; },
    log(line) {
      buf.push(line);
      if (buf.length > 400) buf = buf.slice(-300);
      pre.textContent = buf.join("\n");
    },
  };
}
