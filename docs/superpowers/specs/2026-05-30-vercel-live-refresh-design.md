# Vercel Live-Refresh — Design Spec

**Date:** 2026-05-30 · **Author:** Tayakorn + Claude · **Status:** Approved (brainstorm)

## Goal
Give the KMUTT (มจธ.) badminton results website a real **in-page "🔄 refresh" button**
that pulls the latest schedule/results **directly from the source** (bat.tournamentsoftware.com)
without the user running Python on a PC. Manual point-scores stay editable in the existing Google Sheet.

Tournament window: **31 May – 4 Jun 2026** (starts the day after this spec). De-risking for that
deadline is a first-class constraint.

## Why Vercel
GitHub Pages is static — it cannot run server-side code and the browser cannot scrape
tournamentsoftware (CORS + required POST headers). Vercel serverless functions run server-side
Python, so they can scrape and merge, and the website calls them same-origin (no CORS).
This removes the need for a GitHub Actions scraper or an Apps Script port.

## Architecture

```
tournamentsoftware ──scrape──▶ /api/matches (Vercel Python serverless)
                                   │  + read scores from Google Sheet (gviz CSV), merge by match_id
                                   ▼
                              JSON (CDN-cached ~60s)
                                   │
index.html ──fetch /api/matches──▶ render   (🔄 = ?fresh=1)
            └ fallback: Google Sheet → data.js  (so github.io still works as a safety net)
```

### Components
- **`scraper.py`** — pure scraping/parsing logic refactored out of `extract.py`.
  Exposes `scrape(use_cache=False) -> dict` returning the existing `kmutt_data.json` structure.
  Fetches the ~25 KMUTT player profile pages **in parallel** (`ThreadPoolExecutor`) to stay
  well under the serverless time limit (~5s vs ~40s sequential).
- **`extract.py`** — thin CLI wrapper: `scrape()` → write `kmutt_data.json` (behaviour unchanged
  for the existing local build pipeline).
- **`api/matches.py`** — Vercel serverless handler (`BaseHTTPRequestHandler`):
  1. `scrape()` the source.
  2. Read the Google Sheet gviz CSV; build `match_id → score` map.
  3. Flatten to the website's match objects (same shape as `data.js`), applying preserved scores.
  4. Respond JSON with `Cache-Control: s-maxage=60, stale-while-revalidate=120`.
     `?fresh=1` sets `s-maxage=0` to force a re-scrape.
- **`vercel.json`** — Python runtime + `maxDuration` (e.g. 30s) for `/api/matches`; static serving
  for the rest.
- **`index.html`** — data loader tries `/api/matches` first; on any failure falls back to the
  Google Sheet (existing `DEFAULT_SHEET_URL`) then `data.js`. 🔄 button forces `?fresh=1`.

### Data ownership / merge
- Source-owned (overwritten each refresh): schedule, court, event, round, opponents, **ผล (win/loss/bye)**.
- User-owned (preserved): **สกอร์** (point score), keyed by **รหัสแมตช์ (match_id)**.
- Byes have no match_id and no score — nothing to preserve.
- **Known limitation (accepted):** a brand-new match not yet present as a row in the Sheet has
  nowhere to hold a score until the user adds a row (match_id + score). The Sheet currently
  seeds all 36 matches.

## Safety / failure handling
- The website degrades gracefully: `/api/matches` fail → Sheet → `data.js`. The site never shows blank.
- `github.io` keeps working unchanged (its `/api/` 404s → falls back to Sheet) as a live safety net
  during the tournament. We do **not** take GitHub Pages down.
- The serverless function validates it scraped a sane match count (≥10) before returning; otherwise
  it returns an error status so the client falls back instead of rendering an empty table.
- CDN cache (s-maxage 60) protects the source from request floods.

## Verification (before handing the deploy steps to the user)
1. `scraper.py` run locally must produce the **same 36 matches** as the current `extract.py`/`kmutt_data.json`.
2. Score-merge logic verified locally against the real Sheet gviz CSV (scores land on the right rows).
3. Row order / column mapping identical to `build_site.py` output so the rendered site is unchanged.

## Out of scope (YAGNI for this deadline)
- Scheduled/auto refresh (manual button only).
- Moving score entry off the Google Sheet into an in-app admin UI.
- Custom domain (accept the `*.vercel.app` URL; github.io stays as the old link).
- Vercel KV / database for scores.

## Deploy (user performs the browser auth)
Claude prepares all code + `vercel.json`. User logs into Vercel and "Import" the GitHub repo
(`tayakorn221/kmutt-swu-games-42`); Vercel auto-detects the Python function. Claude provides a
step-by-step guide. GitHub Pages remains live as fallback.
