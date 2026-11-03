#!/usr/bin/env python3
"""주가 데이터 수집 + 기본 지표 계산 (표준 라이브러리만 사용).

사용법:
  python3 tools/stock_data.py 005930.KS            # 요약 지표(JSON)
  python3 tools/stock_data.py AAPL --range 5y      # 기간 지정 (1y, 2y, 5y, 10y, max)
  python3 tools/stock_data.py NVDA --csv out.csv   # 일별 종가 CSV 저장

티커 규칙(Yahoo Finance): 코스피 '005930.KS', 코스닥 '035720.KQ', 미국 'AAPL',
지수 '^KS11'(KOSPI) '^KQ11'(KOSDAQ) '^GSPC'(S&P500) '^IXIC'(NASDAQ).
"""
import argparse, csv, json, math, statistics, sys, urllib.request
from datetime import datetime, timezone

def fetch(ticker, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    res = data["chart"]["result"]
    if not res:
        sys.exit(f"데이터 없음: {data['chart'].get('error')}")
    res = res[0]
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or q["close"]
    rows = []
    for t, c, a, v in zip(res["timestamp"], q["close"], adj, q["volume"]):
        if c is None or a is None:
            continue
        rows.append({"date": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
                     "close": c, "adj": a, "volume": v or 0})
    return res["meta"], rows

def pct(a, b):
    return round((a / b - 1) * 100, 2) if b else None

def metrics(meta, rows):
    px = [r["adj"] for r in rows]
    last = px[-1]
    def ret(n):
        return pct(last, px[-n - 1]) if len(px) > n else None
    daily = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    peak, mdd = px[0], 0.0
    for p in px:
        peak = max(peak, p); mdd = min(mdd, p / peak - 1)
    yr = px[-252:]
    ma = lambda n: round(sum(px[-n:]) / n, 2) if len(px) >= n else None
    vol_1y = statistics.stdev(daily[-252:]) * math.sqrt(252) if len(daily) > 20 else None
    return {
        "ticker": meta.get("symbol"), "name": meta.get("longName") or meta.get("shortName"),
        "currency": meta.get("currency"), "exchange": meta.get("exchangeName"),
        "as_of": rows[-1]["date"], "last_close": round(rows[-1]["close"], 2),
        "return_pct": {"1m": ret(21), "3m": ret(63), "6m": ret(126), "1y": ret(252),
                       "3y": ret(756), "5y": ret(1260), "period": pct(last, px[0])},
        "cagr_pct_period": round(((last / px[0]) ** (252 / max(len(px) - 1, 1)) - 1) * 100, 2),
        "volatility_1y_pct": round(vol_1y * 100, 2) if vol_1y else None,
        "max_drawdown_pct_period": round(mdd * 100, 2),
        "high_52w": round(max(yr), 2), "low_52w": round(min(yr), 2),
        "from_52w_high_pct": pct(last, max(yr)),
        "ma50": ma(50), "ma200": ma(200),
        "above_ma200": (last > ma(200)) if ma(200) else None,
        "avg_volume_3m": round(sum(r["volume"] for r in rows[-63:]) / min(63, len(rows))),
        "trading_days": len(rows),
        "note": "수익률/변동성/MDD는 수정주가(배당·분할 반영) 기준. 재무지표(PER, ROE 등)는 포함되지 않음.",
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--range", default="5y")
    ap.add_argument("--csv")
    a = ap.parse_args()
    meta, rows = fetch(a.ticker, a.range)
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "close", "adj", "volume"]); w.writeheader(); w.writerows(rows)
    print(json.dumps(metrics(meta, rows), ensure_ascii=False, indent=2))
