#!/usr/bin/env python3
"""세계 주요 투자사의 SEC 13F 보유 현황 수집 (표준 라이브러리만 사용).

사용법:
  python3 tools/fetch_13f.py            # data/holdings.json + data/holdings.js 갱신
  python3 tools/fetch_13f.py --top 60   # 운용사별 상위 N개 종목 저장 (기본 50)

13F 참고:
- 운용자산 1억 달러 이상 기관이 분기 종료 후 45일 안에 제출하는 미국 상장 증권 롱 포지션 공시.
- 한국 주식, 공매도, 현금, 채권 대부분은 포함되지 않음. 최대 45일 늦은 스냅샷.
- value 단위는 달러가 원칙이지만 천 달러로 내는 기관도 있어 자동 감지한다 (unit()).
"""
import argparse, json, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

UA = "isdceo-dashboard research-bot admin@example.com"   # SEC는 식별 가능한 User-Agent를 요구함
FUNDS = [
    # (CIK, 표시 이름, 대표 인물, 토론 에이전트)
    (1067983, "Berkshire Hathaway", "워런 버핏", "buffett"),
    (1350694, "Bridgewater Associates", "레이 달리오", "dalio"),
    (1697748, "ARK Investment Management", "캐시 우드", "wood"),
    (1649339, "Scion Asset Management", "마이클 버리", "burry"),
    (1336528, "Pershing Square", "빌 애크먼", None),
    (1061768, "Baupost Group", "세스 클라먼", None),
    (1029160, "Soros Fund Management", "조지 소로스", None),
    (1709323, "Himalaya Capital", "리 루", None),
    (1536411, "Duquesne Family Office", "스탠리 드러켄밀러", None),
    (1608046, "국민연금 (NPS)", "국민연금공단", None),
]

def get(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:
            if i == 3:
                raise
            time.sleep(2 ** i)
        finally:
            time.sleep(0.15)   # SEC 요청 제한(초당 10회) 준수

def filings(cik, n=2):
    d = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
    r = d["filings"]["recent"]
    out = [{"acc": a, "period": p, "filed": f}
           for form, a, p, f in zip(r["form"], r["accessionNumber"], r["reportDate"], r["filingDate"])
           if form == "13F-HR"]
    out.sort(key=lambda x: (x["period"], x["filed"]), reverse=True)
    seen, uniq = set(), []
    for x in out:                       # 같은 분기 중복 제출은 최신 것만
        if x["period"] not in seen:
            seen.add(x["period"]); uniq.append(x)
    return uniq[:n]

def strip_ns(tag):
    return tag.split("}")[-1]

def info_table(cik, acc):
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
    idx = json.loads(get(base + "/index.json"))
    xmls = [i["name"] for i in idx["directory"]["item"]
            if i["name"].lower().endswith(".xml") and "primary_doc" not in i["name"].lower()]
    rows = {}
    for name in xmls:
        root = ET.fromstring(get(f"{base}/{name}"))
        if strip_ns(root.tag) != "informationTable":
            continue
        for it in root:
            f = {}
            for el in it.iter():
                f[strip_ns(el.tag)] = (el.text or "").strip()
            key = (f.get("cusip", "").upper(), f.get("putCall", ""))
            r = rows.setdefault(key, {"name": f.get("nameOfIssuer", ""), "class": f.get("titleOfClass", ""),
                                      "cusip": key[0], "putCall": key[1], "value": 0, "shares": 0})
            r["value"] += float(f.get("value") or 0)
            r["shares"] += float(f.get("sshPrnamt") or 0)
    return rows, f"{base}/"

def unit(rows):
    """값 단위 자동 감지: 일부 기관은 2023년 이후에도 천 달러 단위로 제출한다.
    주식 포지션의 '평가액/주식수'(=주당가격) 중앙값이 1달러 미만이면 천 달러 단위로 본다."""
    px = sorted(r["value"] / r["shares"] for r in rows.values() if r["shares"] and not r["putCall"])
    return 1000 if px and px[len(px) // 2] < 1 else 1

def build(top):
    out = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "source": "SEC EDGAR Form 13F-HR", "funds": []}
    for cik, label, person, agent in FUNDS:
        print(f"· {label} ...", file=sys.stderr)
        fs = filings(cik)
        if not fs:
            continue
        cur, url = info_table(cik, fs[0]["acc"])
        prev = info_table(cik, fs[1]["acc"])[0] if len(fs) > 1 else {}
        cm, pm = unit(cur), unit(prev)
        total = sum(r["value"] for r in cur.values()) * cm
        ptotal = sum(r["value"] for r in prev.values()) * pm
        holds = []
        for k, r in cur.items():
            p = prev.get(k)
            if not p:
                chg = "new"
            elif r["shares"] > p["shares"] * 1.005:
                chg = "add"
            elif r["shares"] < p["shares"] * 0.995:
                chg = "reduce"
            else:
                chg = "hold"
            holds.append({**r, "value": r["value"] * cm, "weight": r["value"] * cm / total * 100 if total else 0,
                          "change": chg,
                          "shares_chg_pct": round((r["shares"] / p["shares"] - 1) * 100, 1) if p and p["shares"] else None})
        holds.sort(key=lambda h: -h["value"])
        sold = sorted(({**p, "value": p["value"] * pm, "change": "sold"} for k, p in prev.items() if k not in cur),
                      key=lambda h: -h["value"])
        cnt = {c: sum(1 for h in holds if h["change"] == c) for c in ("new", "add", "reduce", "hold")}
        out["funds"].append({
            "cik": cik, "name": label, "person": person, "agent": agent,
            "period": fs[0]["period"], "filed": fs[0]["filed"], "prev_period": fs[1]["period"] if len(fs) > 1 else None,
            "filing_url": url, "total_value": total, "prev_total_value": ptotal,
            "positions": len(holds), "counts": {**cnt, "sold": len(sold)},
            "top10_weight": round(sum(h["weight"] for h in holds[:10]), 1),
            "holdings": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in h.items()} for h in holds[:top]],
            "sold": [{k: v for k, v in s.items() if k in ("name", "cusip", "putCall", "value", "shares")} for s in sold[:15]],
        })
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    a = ap.parse_args()
    data = build(a.top)
    d = Path(__file__).resolve().parent.parent / "data"
    d.mkdir(exist_ok=True)
    js = json.dumps(data, ensure_ascii=False)
    (d / "holdings.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    (d / "holdings.js").write_text(f"// 자동 생성: python3 tools/fetch_13f.py\nwindow.HOLDINGS = {js};\n")
    for f in data["funds"]:
        print(f"{f['name']:<28} {f['period']}  ${f['total_value']/1e9:8.1f}B  {f['positions']:>4}종목  "
              f"신규 {f['counts']['new']} / 매도 {f['counts']['sold']}")
