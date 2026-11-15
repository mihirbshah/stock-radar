#!/usr/bin/env python3
"""Free daily US-stock momentum scanner. Technical signals only, not advice."""
import csv
import io
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"


def universe():
    result = []
    for line in (ROOT / "tickers.txt").read_text(encoding="utf-8").splitlines():
        value = line.strip().upper()
        if value and not value.startswith("#") and value not in result:
            result.append(value)
    return result


def download_yahoo(symbol):
    """Yahoo chart endpoint, unofficial/no key, subject to throttling and change."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + quote(symbol, safe="") + "?range=2y&interval=1d")
    request = Request(url, headers={"User-Agent": "stock-radar-personal-research/0.1",
                                    "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("chart", {}).get("result") or []
    if not results:
        raise ValueError("Yahoo chart returned no results")
    record = results[0]
    timestamps = record.get("timestamp") or []
    quotes = record.get("indicators", {}).get("quote") or []
    if not quotes:
        raise ValueError("Missing Yahoo quote bars")
    data = quotes[0]
    closes = data.get("close") or []
    volumes = data.get("volume") or []
    rows = []
    for ts, close, volume in zip(timestamps, closes, volumes):
        try:
            price = float(close)
            vol = float(volume)
            if not (price > 0 and vol >= 0 and math.isfinite(price) and math.isfinite(vol)):
                continue
            day = datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")
            rows.append({"date": day, "close": price, "volume": vol})
        except (ValueError, TypeError, OverflowError, OSError):
            continue
    rows.sort(key=lambda r: r["date"])
    rows = [r for i, r in enumerate(rows) if i == 0 or r["date"] != rows[i - 1]["date"]]
    if len(rows) < 210:
        raise ValueError("Yahoo provided fewer than 210 usable trading days")
    return rows[-270:]


def download(symbol):
    # Unofficial free endpoint. CSV history may be unavailable or adjusted.
    query = symbol.lower().replace(".", "-") + ".us"
    request = Request(
        "https://stooq.com/q/d/l/?s=" + query + "&i=d",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/csv"},
    )
    with urlopen(request, timeout=25) as response:
        content = response.read().decode("utf-8-sig")
    rows = []
    for row in csv.DictReader(io.StringIO(content)):
        try:
            dt = row["Date"]
            datetime.strptime(dt, "%Y-%m-%d")
            close, volume = float(row["Close"]), float(row["Volume"])
            if close > 0 and volume >= 0 and math.isfinite(close) and math.isfinite(volume):
                rows.append({"date": dt, "close": close, "volume": volume})
        except (KeyError, ValueError, TypeError):
            continue
    rows.sort(key=lambda r: r["date"])
    rows = [r for i, r in enumerate(rows) if not i or r["date"] != rows[i - 1]["date"]]
    if len(rows) < 210:
        raise ValueError("Fewer than 210 usable trading days")
    return rows[-270:]


def percentage(a, b):
    return round(100 * (a / b - 1), 2) if b else None


def analyze(symbol, rows):
    if len(rows) < 210:
        raise ValueError("Need 210 or more observations")
    prices = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    last = prices[-1]
    r1 = percentage(last, prices[-22])
    r3 = percentage(last, prices[-64])
    r6 = percentage(last, prices[-127])
    avg_volume = sum(volumes[-21:-1]) / 20
    relative_volume = round(volumes[-1] / avg_volume, 2) if avg_volume else None
    ma50 = sum(prices[-50:]) / 50
    ma200 = sum(prices[-200:]) / 200
    above50, above200 = last > ma50, last > ma200
    accelerating = r1 > 0 and r3 > 0 and 3 * r1 > r3
    breakout = (r1 > 15 and r3 > 30 and relative_volume is not None
                and relative_volume > 1.5 and above50 and above200)
    score = (
        min(25, max(0, r1 * 0.8))
        + min(25, max(0, r3 * 0.45))
        + min(15, max(0, ((relative_volume or 1) - 1) * 12))
        + (15 if above50 else 0)
        + (10 if above200 else 0)
        + (10 if accelerating else 0)
    )
    return {
        "ticker": symbol, "date": rows[-1]["date"],
        "price": round(last, 2), "return_1m": r1,
        "return_3m": r3, "return_6m": r6,
        "relative_volume": relative_volume,
        "above_50d": above50, "above_200d": above200,
        "ma50": round(ma50, 2), "ma200": round(ma200, 2),
        "score": round(score, 1),
        "signal": "Breakout candidate" if breakout else "Monitor",
        "extended": r3 > 100,
        "history": [{"date": r["date"], "close": round(r["close"], 3)}
                    for r in rows[-180:]],
    }


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, data):
    # Avoid truncated JSON on interrupted local runs.
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = universe()
    if not symbols:
        raise RuntimeError("No tickers configured")
    old = load_json(OUT / "latest.json", {})
    previous = {row["ticker"]: row for row in old.get("stocks", [])}
    results, failures = [], {}
    provider_counts = {"Yahoo": 0, "Stooq": 0}
    for ticker in symbols:
        try:
            try:
                bars = download_yahoo(ticker)
                provider = "Yahoo"
            except Exception as yahoo_error:
                try:
                    bars = download(ticker)
                    provider = "Stooq"
                except Exception as stooq_error:
                    raise ValueError("Yahoo: %s; Stooq: %s" % (yahoo_error, stooq_error))
            result = analyze(ticker, bars)
            result["provider"] = provider
            provider_counts[provider] += 1
            prev = previous.get(ticker)
            result["score_change"] = round(result["score"] - prev["score"], 1) if prev else None
            results.append(result)
        except Exception as exc:
            failures[ticker] = str(exc)
        time.sleep(0.3)
    required = max(1, math.ceil(len(symbols) * 0.7))
    if len(results) < required:
        raise RuntimeError(
            "Only %d/%d tickers succeeded; need %d, preserving prior data. Errors: %s"
            % (len(results), len(symbols), required, dict(list(failures.items())[:6]))
        )
    results.sort(key=lambda row: row["score"], reverse=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    market_date = max(r["date"] for r in results)
    latest = {
        "generated_at": now, "latest_market_date": market_date,
        "source": "Yahoo chart / Stooq daily CSV (unofficial; delayed/unadjusted/limited)",
        "providers": provider_counts,
        "universe_size": len(symbols), "scanned": len(results),
        "errors": failures, "stocks": results,
        "disclaimer": "Technical screening only. Scores are not forecasts or buy recommendations.",
    }
    history_path = OUT / "snapshots.json"
    snapshots = load_json(history_path, [])
    today = now[:10]
    snapshots = [item for item in snapshots if item["date"] != today]
    snapshots.append({
        "date": today, "market_date": market_date, "scanned": len(results),
        "top": [{"ticker": r["ticker"], "score": r["score"], "price": r["price"]}
                for r in results[:15]],
    })
    snapshots.sort(key=lambda row: row["date"])
    save_json(history_path, snapshots[-365:])
    save_json(OUT / "latest.json", latest)
    print("Finished %d/%d tickers; %d errors; market date %s"
          % (len(results), len(symbols), len(failures), market_date))


if __name__ == "__main__":
    main()
