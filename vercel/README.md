# 🚀 ALL APP IN ONE — Vercel edition

A copy of the Streamlit app, rebuilt to run on **Vercel**. Every tool from the
Streamlit version is here, behind the same activation codes.

| Tool | Where it runs |
|---|---|
| 📥 TikTok Downloader | Vercel Python function (`api/index.py`, yt-dlp) |
| 🎛️ Variant Generator | In the browser: ffmpeg.wasm |
| 🖼️ Image Optimizer | In the browser: pica (Lanczos3 + unsharp) |
| 🔄 → WebP | In the browser: libwebp (wasm) |
| 🎬 Video Upscaler | In the browser: ffmpeg.wasm |

**Why the browser?** Vercel Functions cap uploads at 4.5 MB and ship no
ffmpeg, so heavy video and image work can't run there. Doing it in the
browser has no size limit, costs nothing in function time, and keeps users'
files on their own device. In Chrome, Edge and Firefox, ffmpeg runs
multi-threaded (the `vercel.json` headers turn on cross-origin isolation).
Safari falls back to single-thread mode, which is slower.

## Layout
```
vercel/
├── api/index.py          Flask app: /api/activate, /api/verify, /api/tiktok/*
├── public/               Static UI (index.html, style.css, js/*)
├── scripts/copy-vendor.mjs  Copies ffmpeg.wasm & libs from node_modules → public/vendor
├── requirements.txt      Python deps for the function
├── package.json          Browser libs + build script
└── vercel.json           Build, rewrites, COOP/COEP headers, 300s function limit
```

## Vercel project settings
- **Root Directory:** `vercel`
- Framework preset: Other (`vercel.json` sets the build command and output directory)
- Optional env var `ALLAPP_CODES`: a comma-separated list that replaces the
  built-in activation codes.

## Run locally
```bash
cd vercel
npm install
pip install -r requirements.txt
npm run dev            # http://127.0.0.1:3000
```
