"""에이전트용 공용 자료 조회 도구 — 같은 출처에서 같은 숫자를, 출처·확보 시각·응답 해시와 함께.

  python3 tools/research.py close --round 2026-11-09 --market KR --tickers 005930,033780
  python3 tools/research.py close --round 2026-11-09 --market US --tickers AAPL,BRK.B
  python3 tools/research.py macro --round 2026-11-09
  python3 tools/research.py dart  --round 2026-11-09 --ticker 005930 [--days 14]
  python3 tools/research.py check-csv league/imports/claude/2026-11-09.csv [--log 파일]

- 기준 종가는 **그 라운드의 기준 세션 행만** 돌려준다(한국·미국 모두 Yahoo 일봉, 한국은 .KS/.KQ). 행이 없으면
  "기준일 행 없음"과 가장 최근 행 날짜를 알려 주고 다른 날 값으로 메우지 않는다.
- 받은 자료는 모두 기록 파일에 남는다. 에이전트는 --agent <id>로 자기 파일(league/rounds/<라운드>/claude/research-<id>.jsonl)만 쓴다
  (1단계 독립 분석 중 서로의 후보를 보지 않게). 연습은 --dir league/sandbox.
  **이 파일에는 검토한 종목이 들어 있으므로 마감(08:30) 전에는 커밋하지 않는다** (rounds/<날짜>/claude 폴더와 같은 규칙).
- 라운드 마감(08:30 KST)이 지나면 조회를 거부한다(마감 뒤 정보 차단). 사후 감사는 --audit 로만.
- 네이버 일별 시세(siseJson)는 개별 종목 종가가 넥스트레이드 시간외 거래를 합친 통합 가격이라 KRX 정규장 종가와 다르다
  (2026-11-07 대조: 13건 중 12건 불일치, 최대 3.4%). 그래서 한국 종목은 KRX 공식 종가와 13건 모두 같았던 Yahoo(.KS/.KQ)를 쓴다.
  지수(KOSPI)는 두 곳 모두 KRX와 같았다.
- Yahoo는 공개 JSON(비공식)이다. 에이전트 분석 참고용이며, 채점은 운영 쪽 공식 자료(KRX·Alpha Vantage)로 따로 한다.
  우리 이름(User-Agent: league-research)으로만 요청하고, 막히면 그대로 실패를 알린다(우회하지 않음).
- check-csv 는 제출을 막지 않는다. 근거(rationale)에 쓴 "MM/DD 종가 숫자"를 기록과 대조해 경고만 낸다.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

UA = "league-research/0.1"
NAVER = "https://api.finance.naver.com/siseJson.naver?symbol={sym}&requestType=1&startTime={a}&endTime={b}&timeframe=day"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d"


def now_kst() -> datetime:
    return datetime.now(L.KST)


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _rec(kind, market, ticker, session, value, url, raw: bytes, note=None, as_of=None, retrieved=None) -> dict:
    return {"kind": kind, "market": market, "ticker": ticker, "session": session, "value": value,
            "url": url, "as_of": as_of or session or "확인 못함",
            "retrieved_at": (retrieved or now_kst()).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(raw).hexdigest() if raw else None, "note": note}


def naver_rows(raw: bytes) -> list[tuple[str, float]]:
    """네이버 siseJson: [['날짜','시가','고가','저가','종가',...], ['20261106', ...], ...] (작은따옴표·공백 섞임)."""
    txt = raw.decode("utf-8", "replace").strip().replace("'", '"')
    rows = json.loads(txt) if txt.startswith("[") else []
    out = []
    for r in rows[1:]:
        if len(r) >= 5 and re.fullmatch(r"\d{8}", str(r[0]).strip()):
            d = str(r[0]).strip()
            out.append((f"{d[:4]}-{d[4:6]}-{d[6:]}", float(r[4])))
    return out


def yahoo_rows(raw: bytes) -> list[tuple[str, float]]:
    res = (json.loads(raw).get("chart") or {}).get("result") or []
    if not res:
        return []
    r = res[0]
    off = int((r.get("meta") or {}).get("gmtoffset") or 0)
    ts = r.get("timestamp") or []
    cl = (((r.get("indicators") or {}).get("quote") or [{}])[0].get("close")) or []
    out = []
    for t, c in zip(ts, cl):
        if c is not None:
            out.append((datetime.fromtimestamp(t + off, timezone.utc).date().isoformat(), round(float(c), 4)))
    meta = r.get("meta") or {}
    # 장 마감 직후 일봉 행이 아직 없을 때: 정규장 종가(meta)를 그날 값으로 (장 상태가 끝난 뒤의 값만)
    mt, mp = meta.get("regularMarketTime"), meta.get("regularMarketPrice")
    if mt and mp is not None:
        md_ = datetime.fromtimestamp(int(mt) + off, timezone.utc)
        cp = meta.get("currentTradingPeriod") or {}
        end = ((cp.get("regular") or {}).get("end"))
        if md_.date().isoformat() not in {d_ for d_, _ in out} and (end is None or int(mt) >= int(end)):
            out.append((md_.date().isoformat(), round(float(mp), 4)))
    return out


def _yahoo(sym: str) -> tuple[str, bytes, list]:
    url = YAHOO.format(sym=urllib.parse.quote(sym))
    raw = _get(url)
    return url, raw, yahoo_rows(raw)


def fetch_rows(market: str, ticker: str, session: date) -> tuple[str, bytes, list]:
    """한국: KRX 정규장 종가와 맞는 Yahoo .KS(유가증권) → 없으면 .KQ(코스닥). 지수 KOSPI는 ^KS11. 미국: Yahoo(점은 하이픈)."""
    if market == "KR":
        if ticker in ("KOSPI", "^KS11"):
            return _yahoo("^KS11")
        last = None
        for suf in (".KS", ".KQ"):
            try:
                url, raw, rows = _yahoo(ticker + suf)
            except urllib.error.HTTPError as e:   # 없는 기호는 404
                last = e
                continue
            if rows:
                return url, raw, rows
            last = (url, raw, rows)
        if isinstance(last, tuple):
            return last
        raise last or RuntimeError("조회 실패")
    return _yahoo(ticker.replace(".", "-"))


def base_session(market: str, round_date: date, cfg: dict) -> date | None:
    rs = L.round_sessions(market, round_date, cfg)
    return rs[0] if rs else None


def close(market: str, tickers: list[str], round_date: date, cfg: dict, fetch=fetch_rows) -> list[dict]:
    s = base_session(market, round_date, cfg)
    if not s:
        return [_rec("close", market, t, None, None, None, b"", note=f"{round_date}은 {market} 휴장 — 라운드 없음") for t in tickers]
    out = []
    for t in tickers:
        try:
            url, raw, rows = fetch(market, t, s)
        except Exception as e:  # noqa: BLE001 — 실패는 그대로 알린다
            out.append(_rec("close", market, t, s.isoformat(), None, None, b"", note=f"조회 실패: {e}"))
            continue
        hit = [v for d_, v in rows if d_ == s.isoformat()]
        if hit:
            out.append(_rec("close", market, t, s.isoformat(), hit[-1], url, raw, note="기준 세션 종가"))
        else:
            last = max((d_ for d_, _ in rows if d_ <= s.isoformat()), default=None)
            out.append(_rec("close", market, t, s.isoformat(), None, url, raw,
                            note=f"기준일 행 없음 — 가장 최근 행 {last or '없음'}. 다른 날 값으로 메우지 말 것"))
    return out


def macro(round_date: date, cfg: dict, fetch=fetch_rows) -> list[dict]:
    """기준 세션의 지수·환율·금리. KR 기준 세션: KOSPI / US 기준 세션: SPY·^TNX(10년물 ×10 아님, 그대로 %)·KRW=X."""
    out = []
    for m, tks in (("KR", ["KOSPI"]), ("US", ["SPY", "^TNX", "KRW=X"])):
        out += close(m, tks, round_date, cfg, fetch)
    for r in out:
        r["kind"] = "macro"
    return out


def dart_list(ticker: str, round_date: date, days: int = 14) -> list[dict]:
    import dart as DT
    try:
        key = DT._key()
    except Exception as e:  # noqa: BLE001
        return [_rec("dart", "KR", ticker, None, None, None, b"", note=f"공시 조회 불가(not_configured): {e}")]
    corp = DT.corp_code_map(key).get(ticker)
    if not corp:
        return [_rec("dart", "KR", ticker, None, None, None, b"", note="DART 고유번호 없음")]
    end = min(round_date, now_kst().date())
    items = DT.list_disclosures(end - timedelta(days=days), end, key, corp_code=corp)
    raw = json.dumps(items, ensure_ascii=False).encode()
    return [_rec("dart", "KR", ticker, x.get("rcept_dt"), x.get("report_nm"),
                 f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x.get('rcept_no')}", raw,
                 as_of=f"{x['rcept_dt'][:4]}-{x['rcept_dt'][4:6]}-{x['rcept_dt'][6:]}" if x.get("rcept_dt") else None)
            for x in items] or [_rec("dart", "KR", ticker, None, None, None, raw, note=f"최근 {days}일 공시 없음")]


def default_log(round_date: date, d: Path = L.ROOT / "league", agent: str | None = None) -> Path:
    """에이전트마다 따로(research-<id>.jsonl): 1단계 독립 분석 중 서로의 후보를 보지 않게."""
    return d / "rounds" / round_date.isoformat() / "claude" / (f"research-{agent}.jsonl" if agent else "research-log.jsonl")


def read_logs(path: Path) -> list[dict]:
    """파일이면 그 파일, 폴더면 그 안의 research-*.jsonl 전부."""
    files = sorted(path.glob("research-*.jsonl")) if path.is_dir() else ([path] if path.exists() else [])
    return [json.loads(x) for f in files for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_log(path: Path, recs: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


PRICE_CLAIM = re.compile(r"(\d{1,2})/(\d{1,2})\s*(?:일\s*)?(?:종가|마감)\s*\(?\s*\$?\s*([\d,]+(?:\.\d+)?)")
# "종가 219,500원(11/6)"처럼 날짜가 뒤에 오는 형태
PRICE_CLAIM_AFTER = re.compile(r"(?:종가|마감)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(?:원|달러|포인트|pt)?\s*\(\s*(\d{1,2})/(\d{1,2})\s*\)")


def check_csv(path: Path, log: Path, cfg: dict) -> list[str]:
    """근거의 'MM/DD 종가 숫자'를 기록과 대조하고, 출처 기준일이 라운드보다 늦지 않은지 본다. 경고 목록만 돌려준다."""
    recs = read_logs(log)
    closes = {(r["market"], r["ticker"], r["session"]): r["value"] for r in recs if r.get("kind") in ("close", "macro") and r.get("value") is not None}
    by_day: dict = {}                                 # (시장, 날짜) → [(종목, 값)]
    for (m_, t_, s_), v_ in closes.items():
        by_day.setdefault((m_, s_), []).append((t_, v_))
    MACRO = {"KOSPI", "^KS11", "SPY", "^TNX", "KRW=X"}
    bench = {"KR": "KOSPI", "US": "SPY"}
    warns = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), 2):
            rd = date.fromisoformat(row["round_date"].strip())
            m, t, who = row["market"].strip().upper(), row["ticker"].strip(), f"{i}행 {row['agent_id']}-{row['market']}"
            bs = base_session(m, rd, cfg)
            if t.upper() == "WATCH":                     # 관망은 비교 지수 기록과 대조
                t = bench.get(m, t)
            text = row.get("rationale") or ""
            claims = PRICE_CLAIM.findall(text) + [(mm, dd, num) for num, mm, dd in PRICE_CLAIM_AFTER.findall(text)]
            for mm, dd, num in claims:
                try:
                    claim_d = date(rd.year if int(mm) <= rd.month else rd.year - 1, int(mm), int(dd))
                except ValueError:
                    continue
                v = float(num.replace(",", ""))
                if bs and claim_d != bs:
                    warns.append(f"{who}: 근거의 {mm}/{dd} 종가는 기준 세션({bs.isoformat()})이 아님")
                ref = closes.get((m, t, claim_d.isoformat()))
                day = by_day.get((m, claim_d.isoformat()), [])
                hit = lambda pool: next((t_ for t_, x in pool if x and abs(v / x - 1) <= 0.001), None)
                other = hit([(t_, x) for t_, x in day if t_ != t and t_ not in MACRO])
                if hit([(t_, x) for t_, x in day if t_ in MACRO]) and (ref is None or abs(v / ref - 1) > 0.001):
                    continue                                  # 지수·환율·금리 인용(근거에 지수 종가를 함께 쓴 경우)
                if ref is not None:                           # 자기 종목 기록이 있으면 그 값과만 비교(다른 종목 값과 같아도 통과 안 함)
                    if abs(v / ref - 1) > 0.001:
                        warns.append(f"{who}: {mm}/{dd} 종가 {num}가 조사 기록({ref:g})과 다름"
                                     + (f" — 다른 종목({other}) 값과 같음, 종목을 바꿔 쓴 것 아닌지 확인" if other else ""))
                elif other:
                    warns.append(f"{who}: {mm}/{dd} 종가 {num}는 이 종목 기록이 없고 다른 종목({other}) 값과 같음 — 확인 필요")
                else:
                    warns.append(f"{who}: {mm}/{dd} 종가 {num}는 조사 기록에 없음 — 직접 확인 필요")
            for s in (row.get("sources") or "").split(";"):
                parts = s.split("|")
                if len(parts) >= 2 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[1].strip()) and parts[1].strip() > rd.isoformat():
                    warns.append(f"{who}: 출처 기준일 {parts[1].strip()}이 라운드 날짜보다 늦음 — 마감 뒤 정보 의심")
    return warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["close", "macro", "dart", "check-csv"])
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--round")
    ap.add_argument("--market", choices=["KR", "US"])
    ap.add_argument("--tickers", default="")
    ap.add_argument("--ticker")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--dir", default=str(L.ROOT / "league"))
    ap.add_argument("--log")
    ap.add_argument("--agent", help="에이전트 id — 기록을 research-<id>.jsonl 로 따로 남김(독립 분석)")
    ap.add_argument("--audit", action="store_true", help="마감 뒤 사후 감사용 조회(기록 파일에 audit 표시)")
    a = ap.parse_args()
    d = Path(a.dir)
    cfg = L.load_config(d)
    if a.cmd == "check-csv":
        if not a.csv:
            sys.exit("CSV 경로가 필요합니다")
        rows = list(csv.DictReader(open(a.csv, newline="", encoding="utf-8-sig")))
        rd = date.fromisoformat(rows[0]["round_date"].strip()) if rows else now_kst().date()
        log = Path(a.log) if a.log else default_log(rd, d).parent      # 폴더: 에이전트별 기록 전부
        w = check_csv(Path(a.csv), log, cfg)
        print("\n".join(w) if w else "조사 기록 대조: 경고 없음")
        print(f"(기록: {log}{'' if log.exists() else ' — 없음'}) 경고는 제출을 막지 않습니다. 진행자가 해당 에이전트에게 확인을 요청합니다.")
        return
    if not a.round:
        sys.exit("--round 날짜가 필요합니다")
    rd = date.fromisoformat(a.round)
    if now_kst() >= L.lock_deadline(rd, cfg) and not a.audit:
        sys.exit(f"{rd} 라운드 마감({cfg['lock_deadline']} KST)이 지났습니다 — 마감 뒤 정보는 조회하지 않습니다(사후 감사는 --audit)")
    if a.cmd == "close":
        if not a.market or not a.tickers:
            sys.exit("--market 과 --tickers 가 필요합니다")
        recs = close(a.market, [t.strip() for t in a.tickers.split(",") if t.strip()], rd, cfg)
    elif a.cmd == "macro":
        recs = macro(rd, cfg)
    else:
        if not a.ticker:
            sys.exit("--ticker 가 필요합니다")
        recs = dart_list(a.ticker, rd, a.days)
    if a.audit:
        for r in recs:
            r["audit"] = True
    log = Path(a.log) if a.log else default_log(rd, d, a.agent)
    write_log(log, recs)
    print(json.dumps(recs, ensure_ascii=False, indent=1))
    print(f"(기록: {log})", file=sys.stderr)


if __name__ == "__main__":
    main()
