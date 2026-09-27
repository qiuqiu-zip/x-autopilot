# x-autopilot 🤖

**I let an AI fully run my X (Twitter) account for 24 hours.** It cleaned my recommendation feed, redesigned the profile, posted a 6-post thread, scheduled 8 posts, and left 16 replies under posts from @AnthropicAI, @OpenAI, @simonw and @dotey.

The platform's anti-bot system killed my session **three times** in the process.

This repo is the exact toolkit that survived.

## What's inside

| Script | What it does |
|---|---|
| `src/xjs.py` | Core channel: execute JavaScript in your logged-in x.com tab (macOS + Chrome) |
| `src/post_tweet.py` | Post a tweet through the real compose UI |
| `src/reply_tweet.py` | Reply to any post through the real UI |
| `src/schedule_post.py` | Schedule posts via X's native scheduler (survives logout) |
| `n8n/content-pipeline.json` | **Importable n8n workflow**: news RSS → LLM drafts your posts → Google Sheets approval queue → auto-post at 20:00. The full content pipeline in one file. |
| `docs/survival-notes.md` | The hard-won rules: what gets you flagged, what doesn't |

## Why the "real UI channel"?

Calling X's internal GraphQL endpoints directly gets rejected with error 226 ("This request looks like it might be automated") — X fingerprints its own frontend.

Instead of faking fingerprints, this toolkit types into the real compose box and clicks the real buttons, letting **X's own frontend generate the valid credentials**. From the server's perspective, you are just a user.

```
you ──▶ python ──▶ AppleScript ──▶ Chrome tab (logged in)
                                        │
                                        ▼
                          real input events on real DOM
                                        │
                                        ▼
                          X's own JS builds valid requests
```

## The n8n pipeline (zero-code mode)

Prefer a visual pipeline over scripts? Import `n8n/content-pipeline.json` into your n8n instance:

```
Daily 08:00 → AI News RSS → Score Topics → LLM drafts 5 posts → Google Sheets (approval queue) → Telegram ping
Daily 20:00 → Read approved rows → Post to X (max 3/day) → Mark posted
```

You bring: an n8n instance, an LLM API key (the example uses GLM's OpenAI-compatible endpoint — swap in any), a Google Sheet, and X credentials on the Twitter node. The "approval queue" pattern means **a human signs off every post** — that's the design, not a limitation.

## Setup

1. macOS + Google Chrome, logged into your X account
2. Chrome menu: **View → Developer → Allow JavaScript from Apple Events** ✅
3. Keep an x.com tab open

```bash
python3 src/post_tweet.py "My first AI-driven post"
python3 src/schedule_post.py "See you tomorrow" October 8 2026 20 30
python3 src/reply_tweet.py "https://x.com/someone/status/123" "great point!"
```

## The survival rules (learned the hard way)

- **Machines get caught by rhythm, not IQ.** Randomize intervals (8–18s), never fire identical text twice.
- **Profile edits are tripwires.** Changing avatar/name/banner via automation = forced logout. Do identity changes manually, batched in one sitting.
- **Never automate credentials.** Passwords, codes, payments — always human hands.
- **Verify every action.** Read the page state after posting; unverified automation is blind driving.
- **Compose box has content? Never navigate away.** You'll trigger a native confirm dialog that wedges your whole channel.

Full battle notes: [docs/survival-notes.md](docs/survival-notes.md)

## Disclaimer

- Use on **your own account**, at **human-like volumes**. This tool performs the same clicks you would perform manually — it does not bypass any platform security.
- Aggressive automation violates the X Rules and can get accounts suspended. The authors take no responsibility for bans.
- Built as a research artifact documenting how far native-JS UI automation can go before the platform pushes back.

## License

MIT — but if this helps you build something, a follow [@qiuBuildsAI](https://x.com/qiuBuildsAI) is the cheapest thank-you. This account is run with this exact toolkit, in public.
