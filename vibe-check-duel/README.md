# ✨ Vibe Check Duel: client edition

A two-player browser game hosted on Vercel behind an activation code. It is
adapted for phones, and its progress is saved on the device.

- `/`: activation page. A buyer enters their code once per browser.
- `/play`: the game (`private/game.html`). It is only served with a valid code.
- Add-to-home-screen support: `manifest.webmanifest` plus icons in `public/`.

`api/index.py` stores only SHA-256 hashes of the codes. Add codes with the env
var `GAME_CODE_HASHES` and block one with `GAME_REVOKED_HASHES` (both
comma-separated hashes).

Changes from the seller's original HTML: phone layout (pinned button bar,
safe-area padding, bigger tap targets), save and resume, tap a score to choose
who gets the bank, "Reveal all" no longer double-counts an awarded bank, the
"Works offline" claim was removed (the hosted game needs internet to load),
and "Target-style store" became "Big-box store" (no brand names).
