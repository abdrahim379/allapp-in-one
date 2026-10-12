"""
Vibe Check Duel: activation-gated game host (Vercel, Flask).

  POST /api/activate {code}   -> sets the access cookie
  GET  /play                  -> the game (needs a valid access cookie)
  POST /api/logout            -> clears the cookie

Only SHA-256 hashes of the activation codes are stored here, so reading this
file does not reveal a working code. The cookie holds the buyer's own code;
every request re-checks its hash. Add codes without a commit by setting the
GAME_CODE_HASHES env var (comma-separated hashes, added to the built-in ones).
"""

import hashlib
import os

from flask import Flask, jsonify, redirect, request, send_file

HERE = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(os.path.dirname(HERE), "private")
PUBLIC = os.path.join(os.path.dirname(HERE), "public")

CODE_HASHES = {
    "9d220a43f17149297b04be69eafa0c3fe553a1e200260bfe3fc2e715516da150",
    "382b3ac655b1cbb38448890161cc30e9430768ac4447a44cdbb3a4674d03016b",
    "2e81a788936d2b9f7e59b52f8ffc0c12a60e627f059b7e08ea2708791e598eac",
    "99fe188b31a5ac32775f4768d57da5ae77524a4e9cf807117100e60728b8cca9",
    "ee9af207ae7ebce9ef67d193bf243bcacaf368b9d1b4fcc4e30398a291ce8e87",
    "76a71a3da02ad90895d021d0a1ad2cde2ddf45fc9c6eb36c885d06dab3fd444b",
    "e9db6c3175b95a2e4e862ebf95609734fd2b3fcb91e0d7e83283dc3efe99f878",
    "de087923d4af995df5306c14e42fcd2c6bf02e3b895b04ab46270fe59c3c5b0c",
    "16fe06bbcca82c43147e49bbe568f70cdedd0875aaf02e5754ac5f1e53d20372",
    "e154363b933bd63d3cbba8115458f8b6750aa3736b7a3984d26d642d021d69fc",
} | {h.strip().lower() for h in os.environ.get("GAME_CODE_HASHES", "").split(",") if h.strip()}
REVOKED = {h.strip().lower() for h in os.environ.get("GAME_REVOKED_HASHES", "").split(",") if h.strip()}

COOKIE = "vcd_access"

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


# Local development
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 3000)))
