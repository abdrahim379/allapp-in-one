# 🎄 Christmas Survey Showdown: client edition

The browser game, hosted on Vercel behind an activation code.

- `/`: activation page. A buyer enters their code once per browser.
- `/play`: the game (`private/game.html`). It is only served with a valid code, and a
  wrong code or no code redirects to `/`.
- `/dl/my-rounds-original-50.txt`, `/dl/rounds-50.csv`: rounds backups (also code-gated).

The code checks run in `api/index.py`, which stores only SHA-256 hashes of the
codes. The codes themselves are not in this repository.

## Adding or blocking codes (no redeploy of code needed)
- **New codes:** add their SHA-256 hashes, comma-separated, to the Vercel env var
  `GAME_CODE_HASHES`, then redeploy.
  `python3 -c "import hashlib;print(hashlib.sha256(b'CSS-ABCD-EFGH').hexdigest())"`
- **Block a code** (refund, leaked code): add its hash to `GAME_REVOKED_HASHES`.

## Vercel project settings
- Root Directory: `christmas-survey-showdown`, Framework preset: Other
