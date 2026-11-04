#!/usr/bin/env python3
"""OpenDART 연결: 대상 종목 공시 목록(공통 자료용)과 한국 배당·분할 확인(채점용).

상태: 공개 문서 기준으로 작성. DART_API_KEY 를 받은 뒤 실제 응답으로 검증해야 한다.
원칙: 공시를 해석하지 못하면 '확인 못함'으로 두고 채점은 보류된다 (0점 처리하지 않음).

환경변수: DART_API_KEY (OpenDART 인증키)

사용법:
  python3 tools/dart.py check --date 2026-11-05          # 연결 확인: 최근 공시 중 대상 종목 건수와 예시
  python3 tools/dart.py recent --date 2026-11-05          # 공통 자료에 들어갈 공시 목록(JSON)
"""
from __future__ import annotations

import argparse, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

API = "https://opendart.fss.or.kr/api"

# 공통 자료에 표시할 공시 분류 (보고서명에 포함된 문구 기준)
CATEGORIES = [
    ("실적", ("영업(잠정)실적", "잠정실적", "매출액또는손익구조")),
    ("배당", ("현금ㆍ현물배당", "현금배당", "배당결정")),
    ("분할·병합", ("주식분할", "주식병합", "액면분할", "무상증자", "감자결정")),
    ("IR", ("기업설명회",)),
    ("자사주", ("자기주식",)),
    ("주요사항", ("유상증자", "전환사채", "합병", "회사분할", "영업양수", "영업양도", "최대주주변경")),
]
CA_KEYWORDS = ("배당", "주식분할", "주식병합", "액면분할", "무상증자", "감자")


class NotConfigured(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("DART_API_KEY")
    if not k:
        raise NotConfigured("DART_API_KEY 환경변수 없음")
    return k


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "league-dart/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


_CORP_CODES: dict | None = None


def corp_code_map(key: str | None = None) -> dict:
    """종목코드(6자리) → DART 고유번호(8자리). corpCode.xml(zip)을 한 번 받아 메모리에 둔다."""
    global _CORP_CODES
    if _CORP_CODES is None:
        import xml.etree.ElementTree as ET
        raw = _get(f"{API}/corpCode.xml?" + urllib.parse.urlencode({"crtfc_key": key or _key()}))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            root = ET.fromstring(z.read(z.namelist()[0]))
        _CORP_CODES = {}
        for c in root.iter("list"):
            sc = (c.findtext("stock_code") or "").strip()
            if sc:
                _CORP_CODES[sc] = (c.findtext("corp_code") or "").strip()
    return _CORP_CODES


def list_disclosures(start: date, end: date, key: str | None = None, sleep: float = 0.1,
                     corp_code: str | None = None) -> list[dict]:
    """기간 내 공시 목록 (페이지 넘김). corp_code 를 주면 그 회사만 (긴 기간도 빠름).
    회사 미지정 전체 조회는 시장 전체라 14일에 약 3분 걸린다(2026-11-04 실측)."""
    key = key or _key()
    out, page = [], 1
    while True:
        params = {"crtfc_key": key, "bgn_de": start.strftime("%Y%m%d"), "end_de": end.strftime("%Y%m%d"),
                  "page_no": page, "page_count": 100}
        if corp_code:
            params["corp_code"] = corp_code
        q = urllib.parse.urlencode(params)
        data = json.loads(_get(f"{API}/list.json?{q}"))
        st = data.get("status")
        if st == "013":                 # 조회된 데이터 없음
            break
        if st != "000":
            raise RuntimeError(f"DART 오류 {st}: {data.get('message')}")
        out += data.get("list", [])
        if page >= int(data.get("total_page", 1)):
            break
        page += 1
        time.sleep(sleep)
    return out


def categorize(report_nm: str) -> str | None:
    name = re.sub(r"\s+", "", report_nm)
    for cat, keys in CATEGORIES:
        if any(k in name for k in keys):
            return cat
    return None


def filter_universe(items: list[dict], universe_kr: dict) -> list[dict]:
    """대상 종목(6자리 코드) 공시만, 분류 가능한 것만. 공통 자료에는 제목·날짜·링크만 남긴다."""
    out = []
    for it in items:
        code = (it.get("stock_code") or "").strip()
        if code not in universe_kr:
            continue
        cat = categorize(it.get("report_nm", ""))
        if not cat:
            continue
        out.append({"ticker": code, "name": universe_kr[code], "category": cat,
                    "title": re.sub(r"\s+", " ", it.get("report_nm", "")).strip(),
                    "rcept_dt": f"{it['rcept_dt'][:4]}-{it['rcept_dt'][4:6]}-{it['rcept_dt'][6:]}",
                    "rcept_no": it.get("rcept_no"), "filer": it.get("flr_nm"),
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it.get('rcept_no')}"})
    return sorted(out, key=lambda x: (x["rcept_dt"], x["ticker"], x["rcept_no"] or ""))


def recent_for_snapshot(round_date: date, universe_kr: dict, days: int = 14, key: str | None = None) -> dict:
    """공통 자료용: 라운드 전날까지 최근 N일 공시 중 대상 종목·주요 분류."""
    end = round_date - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    items = filter_universe(list_disclosures(start, end, key), universe_kr)
    return {"status": "ok", "source": "OpenDART 공시검색", "from": start.isoformat(), "to": end.isoformat(),
            "count": len(items), "items": items,
            "note": "제목·접수일·링크만. 본문은 링크에서 확인. 라운드 당일 07:00 이후 공시는 포함되지 않음"}


# ───────── 한국 배당·분할 확인 (채점용) ─────────

def document_text(rcept_no: str, key: str | None = None) -> str:
    """공시 원문(zip 안의 XML)을 평문으로."""
    key = key or _key()
    raw = _get(f"{API}/document.xml?" + urllib.parse.urlencode({"crtfc_key": key, "rcept_no": rcept_no}))
    texts = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            t = z.read(n).decode("utf-8", "replace")
            texts.append(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t\r\n]+", " ", " ".join(texts))


_DATE = r"(\d{4})\s*[-.년]\s*(\d{1,2})\s*[-.월]\s*(\d{1,2})"


def parse_dividend(text: str) -> dict | None:
    """현금ㆍ현물배당결정 본문에서 배당기준일과 보통주 1주당 배당금. 둘 다 못 찾으면 None."""
    m = re.search(r"배당기준일\s*" + _DATE, text)
    a = re.search(r"1주당\s*배당금\s*\(\s*원\s*\)\s*보통주식?\s*([\d,]+)", text)
    if not (m and a):
        return None
    return {"record_date": date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat(),
            "amount": float(a.group(1).replace(",", ""))}


def kr_ex_date(record_date: date, cfg: dict) -> date:
    """한국 배당락일 = 기준일의 직전 거래일 (T+2 결제)."""
    return L.prev_session("KR", record_date, cfg)


def check_kr_corporate_actions(d: Path, ticker: str, after: date, upto: date, key: str | None = None,
                               lookback_days: int = 120, items: list[dict] | None = None,
                               fetch_text=document_text) -> dict:
    """(after, upto] 구간의 한국 배당·분할을 DART 공시로 확인.
    - 최근 lookback 기간에 배당·분할 관련 공시가 없으면: 확인 완료(해당 없음).
    - 배당결정 공시가 있으면 원문에서 기준일·금액을 읽어, 배당락일이 구간 안이면 배당 기록.
    - 분할·병합·무상증자·감자 공시가 있거나 원문 해석에 실패하면: 확인 못함 (채점 보류 → 운영자 확인)."""
    cfg = L.load_config(d)
    if items is None:
        cc = corp_code_map(key).get(ticker)
        if not cc:
            return {"ticker": ticker, "window": [after.isoformat(), upto.isoformat()], "checked": False, "dividends": [],
                    "splits": [], "unresolved": [{"reason": "DART 고유번호를 찾지 못함"}], "related": []}
        items = list_disclosures(upto - timedelta(days=lookback_days), upto, key, corp_code=cc)
    mine = [it for it in items if (it.get("stock_code") or "").strip() == ticker
            and any(k in re.sub(r"\s+", "", it.get("report_nm", "")) for k in CA_KEYWORDS)]
    res = {"ticker": ticker, "window": [after.isoformat(), upto.isoformat()], "checked": False,
           "dividends": [], "splits": [], "unresolved": [], "related": [it.get("rcept_no") for it in mine]}
    for it in mine:
        name = re.sub(r"\s+", "", it.get("report_nm", ""))
        if "배당" in name:
            try:
                p = parse_dividend(fetch_text(it["rcept_no"], key) if key else fetch_text(it["rcept_no"]))
            except Exception as e:  # 원문 조회 실패
                p, err = None, str(e)[:100]
            if not p:
                res["unresolved"].append({"rcept_no": it["rcept_no"], "title": it.get("report_nm"), "reason": "배당기준일·금액 해석 실패"})
                continue
            ex = kr_ex_date(date.fromisoformat(p["record_date"]), cfg)
            if after < ex <= upto:
                res["dividends"].append({"ex_date": ex.isoformat(), "amount": p["amount"], "record_date": p["record_date"],
                                         "rcept_no": it["rcept_no"]})
        else:
            res["unresolved"].append({"rcept_no": it["rcept_no"], "title": it.get("report_nm"), "reason": "분할·병합류 공시 — 수동 확인"})
    res["checked"] = not res["unresolved"]
    return res


def record_kr_ca(d: Path, res: dict, now: str | None = None):
    """확인 결과를 corporate_actions 원장에 기록. 확인 못 하면 아무것도 쓰지 않는다(→ 채점 보류)."""
    if not res["checked"]:
        return False
    now = now or datetime.now(L.KST).isoformat(timespec="seconds")
    for dv in res["dividends"]:
        L.append(d, "corporate_actions", {"type": "dividend", "market": "KR", "ticker": res["ticker"], "ex_date": dv["ex_date"],
                                          "amount": dv["amount"], "currency": "KRW", "record_date": dv["record_date"],
                                          "source": "opendart", "rcept_no": dv["rcept_no"]})
    L.append(d, "corporate_actions", {"type": "checked", "market": "KR", "ticker": res["ticker"], "from": res["window"][0],
                                      "to": res["window"][1], "source": "opendart",
                                      "method": "최근 120일 배당·분할 공시 확인", "related": res["related"], "checked_at": now})
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "recent", "ca"])
    ap.add_argument("--tickers", default="", help="ca: 쉼표 구분 종목코드. 구간은 --date 라운드의 (기준 세션, 평가 세션]")
    ap.add_argument("--date", default=datetime.now(L.KST).date().isoformat())
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    try:
        _key()
    except NotConfigured as e:
        sys.exit(f"설정 안 됨: {e}")
    rd = date.fromisoformat(a.date)
    uni = L.universe_for(L.ROOT / "league", rd).get("KR", {})
    if a.cmd == "ca":
        cfg = L.load_config(L.ROOT / "league")
        rs = L.round_sessions("KR", rd, cfg)
        if not rs:
            sys.exit(f"{rd}는 한국 휴장일")
        t0 = time.time()
        for t in [x.strip() for x in a.tickers.split(",") if x.strip()]:
            cc = corp_code_map().get(t)
            items = list_disclosures(rs[1] - timedelta(days=120), rs[1], corp_code=cc) if cc else []
            print(f"[{t} {uni.get(t, '')}] DART 고유번호 {cc} · 최근 120일 공시 {len(items)}건")
            for it in items[:12]:
                print(f"  {it['rcept_dt']} {it['report_nm'].strip()}")
            res = check_kr_corporate_actions(L.ROOT / "league", t, rs[0], rs[1], items=items)
            print(f"  → 구간 ({rs[0]}, {rs[1]}] 확인={res['checked']} 배당={res['dividends']} 미해결={res['unresolved']}")
        print(f"소요 {time.time() - t0:.1f}초")
        return
    try:
        snap = recent_for_snapshot(rd, uni, a.days)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read()[:200]!r}")
    if a.cmd == "recent":
        print(json.dumps(snap, ensure_ascii=False, indent=1))
        return
    from collections import Counter
    print(f"기간 {snap['from']} ~ {snap['to']} · 대상 종목 공시 {snap['count']}건")
    print("분류별:", dict(Counter(x["category"] for x in snap["items"])))
    for x in snap["items"][-8:]:
        print(f"  {x['rcept_dt']} {x['ticker']} {x['name']} [{x['category']}] {x['title']}")


if __name__ == "__main__":
    main()
