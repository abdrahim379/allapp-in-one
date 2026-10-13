"""
Halloween After Dark: activation-gated game host (Vercel, Flask).

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
    "7d1c446d06873bc97380fd02a80e02d3a86e88eaeccb69bf2d46d0b27bb23a24",
    "457b1101d560adbfe842cb8e0ca12688db183042067b788f6efcecd85e6ae27a",
    "77ee6ae08b98051592c9eee84255093f943053b0fef12f1bddc8ea3349f707ae",
    "397210ad754ca39e1ca3b3734d18100e8dd10021e073621b956771d6209d9657",
    "521365135b2dec278d98b5645e047ba3fc086b316716dd88bb8b91dbb59c4b47",
    "bb6996d6e866a42cb6724fd2fa3bc9a5bcea82eefa84b799b8eda86ec660e7bf",
    "e3c1f06e0b979ee12961bdb6e155f7734b51f7cd53d90c3f2ee685d09a26b0bc",
    "5331563dc446aaa93bad314b7398afcb854b7d1f6f5c60b50eb7a14b11ec0233",
    "a272cb949c926946822b24aa0e7d0180826cefe5621f2f9e78333edf27771f0f",
    "8ff2342e9bd63666a60e7495d4a623f929754f32015a6f9fadf6471f13cd858f",
    # Shared code printed in the Etsy download PDF (block it with GAME_REVOKED_HASHES if it leaks)
    "3a3f04b4c7f3da657eb92750821e53228d9225c00483926a6a9854c126bde043",
} | {h.strip().lower() for h in os.environ.get("GAME_CODE_HASHES", "").split(",") if h.strip()}
REVOKED = {h.strip().lower() for h in os.environ.get("GAME_REVOKED_HASHES", "").split(",") if h.strip()}

COOKIE = "had_access"

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
