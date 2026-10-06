"""
ALL APP IN ONE — Vercel serverless API (Flask / WSGI).

Routes
  POST /api/activate            {code}          -> {token}
  GET  /api/verify?token=...                    -> {ok}
  POST /api/tiktok/extract      {url}           -> {videos:[...]}
  GET  /api/tiktok/download?url=...&id=...      -> video/mp4
  POST /api/chat                {messages}      -> text/plain stream (AI Gateway)

TikTok and chat routes require the access token (header X-Access-Token or ?token=).
All video/image processing runs in the browser (ffmpeg.wasm), not here.
"""

import hashlib
import os
import shutil
import tempfile

from flask import Flask, Response, jsonify, request

# ── Activation codes ──────────────────────────────────────────
# Same 10 codes as the Streamlit app. Override in Vercel with the
# ALLAPP_CODES env var (comma-separated) to rotate them without a commit.
DEFAULT_CODES = [
    "ALLAPP-7K3M-X9QR", "ALLAPP-2P8N-W4YZ", "ALLAPP-5T6V-B1DF",
    "ALLAPP-9H2L-C7KJ", "ALLAPP-4R1S-E3MN", "ALLAPP-8G5F-A6PW",
    "ALLAPP-3J7D-Q2VT", "ALLAPP-6B4X-H8ZL", "ALLAPP-1W9U-K5RY",
    "ALLAPP-0N3E-G7CS",
]
VALID_CODES = [c.strip().upper() for c in
               os.environ.get("ALLAPP_CODES", ",".join(DEFAULT_CODES)).split(",") if c.strip()]


def _make_token(code: str) -> str:
    # Identical to auth.py so existing bookmarked ?token= links keep working.
    return hashlib.sha256(code.encode()).hexdigest()[:20]


TOKENS = {_make_token(c) for c in VALID_CODES}

app = Flask(__name__)


def _token_ok() -> bool:
    tok = request.headers.get("X-Access-Token") or request.args.get("token", "")
    return tok in TOKENS


def _deny():
    return jsonify(error="Not activated. Enter a valid activation code."), 401


@app.post("/api/activate")
def activate():
    code = (request.get_json(silent=True) or {}).get("code", "").strip().upper()
    if code in VALID_CODES:
        return jsonify(token=_make_token(code))
    return jsonify(error="Invalid code. Contact the admin to get one."), 403


@app.get("/api/verify")
def verify():
    return jsonify(ok=_token_ok())


@app.get("/api/health")
def health():
    try:
        import yt_dlp
        ytv = yt_dlp.version.__version__
    except Exception as e:  # pragma: no cover
        ytv = f"missing ({e})"
    return jsonify(ok=True, yt_dlp=ytv)


# ── TikTok ────────────────────────────────────────────────────
def _is_tiktok(url: str) -> bool:
    return isinstance(url, str) and "tiktok.com" in url


@app.route("/api/tiktok/extract", methods=["GET", "POST"])
def tiktok_extract():
    if not _token_ok():
        return _deny()
    url = ((request.get_json(silent=True) or {}).get("url") or request.args.get("url", "")).strip()
    if not _is_tiktok(url):
        return jsonify(error="Please enter a valid TikTok URL."), 400

    import yt_dlp
    opts = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "extract_flat": "in_playlist", "playlistend": 9999,
        "extractor_retries": 3, "nocheckcertificate": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify(error=f"Extraction failed: {e}"), 502

    entries = info.get("entries") if info else None
    items = list(entries) if entries is not None else ([info] if info else [])
    videos = []
    for it in items:
        if not it or not it.get("id"):
            continue
        thumbs = it.get("thumbnails") or []
        videos.append({
            "id": it["id"],
            "title": it.get("title") or it.get("description") or "TikTok Video",
            "thumbnail": it.get("thumbnail") or (thumbs[-1].get("url") if thumbs else ""),
            "views": it.get("view_count") or 0,
            "likes": it.get("like_count") or 0,
            "duration": it.get("duration") or 0,
            "url": it.get("webpage_url") or it.get("url") or "",
        })
    return jsonify(videos=videos)


@app.get("/api/tiktok/download")
def tiktok_download():
    if not _token_ok():
        return _deny()
    url = request.args.get("url", "").strip()
    vid = "".join(ch for ch in request.args.get("id", "video") if ch.isalnum() or ch in "-_") or "video"
    if not _is_tiktok(url):
        url = f"https://www.tiktok.com/@x/video/{vid}"

    import yt_dlp
    tmpdir = tempfile.mkdtemp(prefix="tt_", dir="/tmp" if os.path.isdir("/tmp") else None)
    opts = {
        "quiet": True, "no_warnings": True, "nocheckcertificate": True,
        "extractor_retries": 3,
        # Single-file formats only (no ffmpeg on Vercel); prefer H.264 for playback.
        "format": "best[vcodec!=none][acodec!=none]/best",
        "format_sort": ["vcodec:h264", "res", "br"],
        "outtmpl": os.path.join(tmpdir, f"{vid}.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = [f for f in os.listdir(tmpdir) if not f.endswith(".part")]
        if not files:
            raise RuntimeError("no file produced")
        path = os.path.join(tmpdir, files[0])
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify(error=f"Download failed: {e}"), 502

    size = os.path.getsize(path)
    name = os.path.basename(path)

    def stream():
        try:
            with open(path, "rb") as f:
                while chunk := f.read(256 * 1024):
                    yield chunk
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    return Response(stream(), mimetype="video/mp4", headers={
        "Content-Length": str(size),
        "Content-Disposition": f'attachment; filename="{name}"',
        "Cache-Control": "no-store",
    })


# ── AI Chat (Vercel AI Gateway) ───────────────────────────────
GATEWAY_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
CHAT_MODEL = os.environ.get("CHAT_MODEL", "stealth/pixel-canary")


def _gateway_key() -> str:
    # On Vercel the per-request OIDC token arrives as a header; locally use
    # AI_GATEWAY_API_KEY or a pulled VERCEL_OIDC_TOKEN.
    return (os.environ.get("AI_GATEWAY_API_KEY")
            or request.headers.get("x-vercel-oidc-token")
            or os.environ.get("VERCEL_OIDC_TOKEN", ""))


@app.post("/api/chat")
def chat():
    if not _token_ok():
        return _deny()
    body = request.get_json(silent=True) or {}
    msgs = [
        {"role": m["role"], "content": str(m["content"])[:20000]}
        for m in (body.get("messages") or [])[-40:]
        if isinstance(m, dict) and m.get("role") in ("system", "user", "assistant") and m.get("content")
    ]
    if not msgs:
        return jsonify(error="Empty conversation."), 400
    key = _gateway_key()
    if not key:
        return jsonify(error="AI Gateway is not configured (no OIDC token or AI_GATEWAY_API_KEY)."), 500

    import json
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        GATEWAY_URL,
        data=json.dumps({"model": CHAT_MODEL, "messages": msgs, "stream": True}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        upstream = urllib.request.urlopen(req, timeout=280)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except Exception:
            pass
        return jsonify(error=f"AI Gateway {e.code}: {detail}"), 502
    except Exception as e:
        return jsonify(error=f"AI Gateway unreachable: {e}"), 502

    def stream():
        # Re-emit the OpenAI SSE stream as plain text deltas.
        with upstream:
            for raw in upstream:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                except Exception:
                    continue
                if delta:
                    yield delta

    return Response(stream(), mimetype="text/plain; charset=utf-8",
                    headers={"Cache-Control": "no-store", "X-Chat-Model": CHAT_MODEL})


@app.get("/api/chat/info")
def chat_info():
    return jsonify(model=CHAT_MODEL)


# ── Local development: serve the static site too ─────────────
if __name__ == "__main__":
    from flask import send_from_directory
    PUBLIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

    @app.after_request
    def _isolation(resp):  # mirror vercel.json headers (NO_ISOLATION=1 → single-thread path)
        if not os.environ.get("NO_ISOLATION"):
            resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            resp.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
        return resp

    @app.get("/")
    @app.get("/<path:p>")
    def _static(p="index.html"):
        return send_from_directory(PUBLIC, p)

    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 3000)), threaded=True)
