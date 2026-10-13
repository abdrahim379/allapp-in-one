# 🎃 Halloween After Dark: client edition

A spooky party game (12 mini-games, 127 questions and prompts) hosted on Vercel behind an
activation code. Live: https://halloween-after-dark.vercel.app

- `/`: activation page. A buyer enters their code once per browser.
- `/play`: the game (`private/game.html`). It is only served with a valid code.
- `api/index.py` stores only SHA-256 hashes of the codes. Add codes with the env var
  `GAME_CODE_HASHES` and block one with `GAME_REVOKED_HASHES` (comma-separated hashes).

Changes from the seller's original HTML: fixed broken Word Scramble answers (HALLOWEEN was
marked with a misspelling, CHTWIBOER had duplicate choices, SPIDER had an extra letter),
replaced a misleading octopus fact, 40 new checked questions, a real date-based daily
challenge, a memorise-then-hide step for Monster Memory, a correct "3 right in a row"
achievement, a live score after each answer, fixed point plurals, Quick play starting a
game instead of an empty results page, and a phone layout that hides the menu during a game.
