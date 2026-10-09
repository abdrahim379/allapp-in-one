"""
Christmas Survey Showdown: activation-gated game host (Vercel, Flask).

  POST /api/activate {code}   -> sets the access cookie
  GET  /play                  -> the game (needs a valid access cookie)
  GET  /dl/<file>             -> rounds backup files (needs the cookie)
  POST /api/logout            -> clears the cookie

Only SHA-256 hashes of the activation codes are stored here, so reading this
file does not reveal a working code. The cookie holds the buyer's own code;
every request re-checks its hash. Add codes without a commit by setting the
GAME_CODE_HASHES env var (comma-separated hashes, added to the built-in ones).
"""

import hashlib
import os

from flask import Flask, Response, jsonify, redirect, request, send_file

HERE = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(os.path.dirname(HERE), "private")
PUBLIC = os.path.join(os.path.dirname(HERE), "public")

CODE_HASHES = {
    "06afea9c717fe5fb79a8383faabccfe4293e1394f6b7f14590e13376e75b69f7",
    "bc9f041cdad3922925e72ff2697bc60ba3e009c51a6fc781637310be9db9085f",
    "bd0ae6dfba7d9a09c829403423b6f4e2d97fe6dbdecb61b7e4ad692b5a6d5552",
    "db36c51ced523b8971d442f1e85db85155b7d913dc20f405218304e7f8fb48bb",
    "c07b595a6f5d16c9bd18647c8e2ade46397eeec291ee74f5d86301a5ad531d43",
    "cf87c297fc672c98898d15819cc191c65f1676063c2530bd6b7da07a5b2c9323",
    "a7faaa7dc40d7cffc5c31379ee0519393cb5251054e1341169e0ca2d274878bb",
    "e12d3a9bd09bf896a8f681f048db09cdb9f8f1a583c37d38a3e1a5620b4ad698",
    "eb33106f9d31edd8e0099e01991235382617a2ee4a3181a62893b754c65440da",
    "475b2ecd3f7aaddb0f362073bfd38be4e64f528e51f04f7537d67ded859a3f51",
} | {h.strip().lower() for h in os.environ.get("GAME_CODE_HASHES", "").split(",") if h.strip()}
REVOKED = {h.strip().lower() for h in os.environ.get("GAME_REVOKED_HASHES", "").split(",") if h.strip()}

COOKIE = "css_access"
DOWNLOADS = {"my-rounds-original-50.txt": "text/plain", "rounds-50.csv": "text/csv"}

app = Flask(__name__)


def _valid(code: str) -> bool:
    h = hashlib.sha256((code or "").strip().upper().encode()).hexdigest()
    return h in CODE_HASHES and h not in REVOKED


def _ok() -> bool:
    return _valid(request.cookies.get(COOKIE, ""))


@app.post("/api/activate")
def activate():
    code = ((request.get_json(silent=True) or {}).get("code") or "").strip().upper()
    if not _valid(code):
        return jsonify(error="Invalid activation code. Check it and try again."), 403
    resp = jsonify(ok=True)
    resp.set_cookie(COOKIE, code, max_age=60 * 60 * 24 * 400, httponly=True,
                    secure=request.is_secure or request.headers.get("x-forwarded-proto") == "https",
                    samesite="Lax")
    return resp


@app.get("/api/status")
def status():
    return jsonify(ok=_ok())


@app.post("/api/logout")
def logout():
    resp = jsonify(ok=True)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/")
def home():
    # Normally served from public/ by the CDN; this is the fallback.
    return send_file(os.path.join(PUBLIC, "index.html"), mimetype="text/html")


@app.get("/play")
def play():
    if not _ok():
        return redirect("/", code=302)
    resp = send_file(os.path.join(PRIVATE, "game.html"), mimetype="text/html")
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@app.get("/dl/<name>")
def download(name):
    if not _ok():
        return redirect("/", code=302)
    if name not in DOWNLOADS:
        return Response("Not found", status=404)
    resp = send_file(os.path.join(PRIVATE, name), mimetype=DOWNLOADS[name], as_attachment=True, download_name=name)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


# Local development
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 3000)))
