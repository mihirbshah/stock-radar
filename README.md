# Stock Radar

**$0-subscription** stock momentum dashboard for personal research. Built with Python standard library, public GitHub Pages, GitHub Actions and free unofficial Stooq historical data. No credit card, API key or paid AI subscription required.

## What you get

- Phone/laptop responsive Opportunity Radar, stock deep dive chart, searchable/sortable rankings and scan history.
- Editable curated universe of **49** US-listed symbols in [tickers.txt](tickers.txt); this is NOT a scan of the entire market.
- One-month and three-month performance, relative volume, 50/200-day moving averages, an interpretable 0–100 technical score, breakout flags and extended-price warnings.
- A scheduled weekday scan after the US close, with failures counted and day-by-day leaderboard snapshots.
- Tests runnable without internet or extra Python packages.

## Deployment to your free GitHub Pages site

1. Merge the feature PR into main.
2. Open repository **Settings → Pages**. Under **Build and deployment**, select **Deploy from a branch**; branch **main**, directory **/docs**; Save.
3. Go to **Actions → Daily market scan → Run workflow**, select **main**, and run the workflow once. Inspect logs for errors.
4. Open **https://mihirbshah.github.io/stock-radar/** and check its last-updated status.
5. If the workflow cannot push data, set **Settings → Actions → General → Workflow permissions** to allow read/write. Do not add secrets to this project.

Public Pages content and scan output are public. Never commit private portfolios, account numbers or personal data. GitHub Free Pages requires a public repository.

## Local development

Python 3.10+ is required. No pip install is necessary.

    python3 -m unittest discover -s tests -v
    python3 scripts/scanner.py
    python3 -m http.server 8000 --directory docs

Visit http://localhost:8000.

## Screening logic

Breakout requires:
- 1M return > 15%
- 3M return > 30%
- Latest day's volume > 1.5x the prior 20-session average
- Price > 50-day average and price > 200-day average

The score allocates 25 points each for 1M and 3M return, 15 for relative volume, 15 for 50D trend, 10 for 200D trend, and 10 for momentum acceleration. A stock with 3M return >100% is flagged **extended**. This is a heuristic, not a probability or trading recommendation.

The windows are approximately 21, 63 and 126 trading days. Stooq may provide split/dividend-adjusted prices, delayed data or unexpected symbol gaps. The scan fails without overwriting previously published data if fewer than 70% of symbols return usable history. A successful scan can still contain ticker-level errors; inspect them on the dashboard.

## Free usage limitations

There are **no paid subscriptions**, but all services have limits and availability restrictions. GitHub may delay or skip scheduled jobs, and scheduled workflows on inactive public repositories can be disabled. Stooq is an unofficial free source with no availability guarantee. Revisit data sourcing if its download endpoint becomes unreliable.

**Not yet implemented:** whole-market discovery, market-cap screening, true dollar-liquidity filtering, financial fundamentals, analyst revisions, institutional ownership, news/Reddit signals, point-in-time backtesting, private synchronized watchlists or AI-generated stock recommendations. All would need separate free data-source validation before being claimed.

This application is research software. It does not give financial advice or execute trades.
