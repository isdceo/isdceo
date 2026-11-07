#!/usr/bin/env python3
"""가격·기업행동 수집기 골격.

상태: **골격 + 가짜 응답 테스트만 완료.** 실제 제공처 연결부(KRX·Tiingo·Alpaca)는 공개 문서 기준으로 작성했고,
API 키를 받은 뒤 실제 응답으로 필드명·시각을 검증해야 한다. KIS는 인증 절차가 달라 아직 구현하지 않았다.
사용권은 확인되지 않았다 (docs/data-provider-research.md 6장, docs/provider-inquiries.md).

공통 규칙 (collect):
  - 응답의 거래일이 요청한 세션과 다르면 기록하지 않고 '오래된 값/누락'으로 실패 처리한다.
  - 종가가 없거나 0 이하이면 실패.
  - 같은 (시장, 종목, 세션)에 이미 확정(final) 값이 있으면 잠정(provisional) 값은 기록하지 않는다.
  - 확정 값을 기록할 때 기존 잠정 값과 다르면 price_checks 원장에 차이를 남긴다. 채점에는 마지막(확정) 값만 쓰인다.
  - 원시 가격은 비공개 저장소의 원장에만 저장한다. 지인 공유판(export --public)에는 들어가지 않는다.

사용법:
  python3 tools/collectors.py collect --provider tiingo --market US --session 2026-11-10 --tickers AAPL,MSFT --role final
  python3 tools/collectors.py collect --provider mock --fixture tests/fixtures/x.json ...
  환경변수: KRX_AUTH_KEY, ALPHAVANTAGE_API_KEY, TIINGO_TOKEN, ALPACA_KEY_ID, ALPACA_SECRET_KEY
"""
from __future__ import annotations

import argparse, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402


class NotConfigured(RuntimeError):
    """API 키가 없거나 아직 구현되지 않은 제공처."""


@dataclass
class Quote:
    market: str
    ticker: str
    session: str            # 응답이 말하는 거래일 (YYYY-MM-DD)
    close: float | None
    basis: str = "unadjusted"
    halted: bool = False
    dividends: list = field(default_factory=list)   # [{"ex_date","amount","currency"}]
    splits: list = field(default_factory=list)      # [{"ex_date","ratio"}]
    ca_checked: bool = True                         # False면 배당·분할을 확인하지 않은 값(기업행동 기록 안 남김)


class Provider:
    name = "base"
    markets: tuple = ()
    supplies_corporate_actions = False

    def __init__(self):
        self.errors: list[dict] = []     # 호출 단위 오류 (어느 API가 어떤 응답으로 실패했는지)

    def _try_get(self, label: str, url: str, headers: dict | None = None):
        """오류가 나도 멈추지 않고 기록. 응답 본문 앞부분을 남겨 원인(미승인·키 오류 등)을 구분한다. 키·토큰은 남기지 않는다."""
        try:
            return self._get(url, headers)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            self.errors.append({"api": label, "http": e.code, "body": body})
        except Exception as e:  # 네트워크 오류 등
            self.errors.append({"api": label, "error": type(e).__name__, "detail": str(e)[:200]})
        return None

    def fetch(self, market: str, tickers: list[str], session: date) -> list[Quote]:
        raise NotImplementedError

    def _get(self, url: str, headers: dict | None = None) -> dict | list:
        req = urllib.request.Request(url, headers={"User-Agent": "league-collector/0.1", **(headers or {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)


class MockProvider(Provider):
    """테스트용: 미리 만든 응답(JSON)을 그대로 돌려준다."""
    name = "mock"
    markets = ("KR", "US")
    supplies_corporate_actions = True

    def __init__(self, fixture: dict | str | Path):
        super().__init__()
        self.data = fixture if isinstance(fixture, dict) else json.loads(Path(fixture).read_text())

    def fetch(self, market, tickers, session):
        out = []
        for q in self.data.get(market, []):
            if q["ticker"] in tickers:
                out.append(Quote(market=market, **{k: v for k, v in q.items() if k != "market"}))
        return out


class KRXOpenAPI(Provider):
    """KRX Open API — 유가증권/코스닥 일별매매정보, KOSPI 지수 일별시세.
    미검증: 엔드포인트·필드명(BAS_DD, ISU_CD, TDD_CLSPRC, CLSPRC_IDX)은 공개 문서 기준. 키 발급 후 실제 응답으로 확인할 것."""
    name = "krx_openapi"
    markets = ("KR",)
    BASE = "https://data-dbg.krx.co.kr/svc/apis"

    def __init__(self):
        super().__init__()
        self.key = os.environ.get("KRX_AUTH_KEY")
        if not self.key:
            raise NotConfigured("KRX_AUTH_KEY 환경변수 없음")

    def fetch(self, market, tickers, session):
        d = session.strftime("%Y%m%d")
        rows = []
        for label, path in (("유가증권 일별매매정보", "sto/stk_bydd_trd"), ("코스닥 일별매매정보", "sto/ksq_bydd_trd")):
            res = self._try_get(label, f"{self.BASE}/{path}?basDd={d}", {"AUTH_KEY": self.key})
            rows += (res or {}).get("OutBlock_1", [])
        out = []
        want = set(tickers)
        for r in rows:
            code = str(r.get("ISU_CD", "")).strip()[-6:]
            if code in want:
                out.append(Quote("KR", code, _ymd(r.get("BAS_DD")), _num(r.get("TDD_CLSPRC"))))
        if "KOSPI" in want:
            res = self._try_get("KOSPI 시리즈 일별시세정보", f"{self.BASE}/idx/kospi_dd_trd?basDd={d}", {"AUTH_KEY": self.key})
            for r in (res or {}).get("OutBlock_1", []):
                if str(r.get("IDX_NM", "")).strip() == "코스피":
                    out.append(Quote("KR", "KOSPI", _ymd(r.get("BAS_DD")), _num(r.get("CLSPRC_IDX"))))
        return out


class Tiingo(Provider):
    """Tiingo EOD — 비수정 close + divCash(ex-date 기준) + splitFactor 를 한 번에 받는다.
    미검증: 키 발급 후 실제 응답으로 확인할 것. S&P 500 비교 기준은 SPY 종가로 대체한다 (benchmarks.US = SPY 권장)."""
    name = "tiingo"
    markets = ("US",)
    supplies_corporate_actions = True

    def __init__(self):
        super().__init__()
        self.token = os.environ.get("TIINGO_TOKEN")
        if not self.token:
            raise NotConfigured("TIINGO_TOKEN 환경변수 없음")

    def fetch(self, market, tickers, session):
        out = []
        for t in tickers:
            q = urllib.parse.urlencode({"startDate": session.isoformat(), "endDate": session.isoformat(), "token": self.token})
            sym = t.replace(".", "-").lower()          # Tiingo 표기: BRK.B → brk-b
            rows = self._try_get(f"Tiingo {t}", f"https://api.tiingo.com/tiingo/daily/{urllib.parse.quote(sym)}/prices?{q}")
            for r in rows or []:
                s = str(r.get("date", ""))[:10]
                qt = Quote("US", t, s, _num(r.get("close")))
                if _num(r.get("divCash")):
                    qt.dividends.append({"ex_date": s, "amount": _num(r["divCash"]), "currency": "USD"})
                sf = _num(r.get("splitFactor"))
                if sf and sf != 1.0:
                    qt.splits.append({"ex_date": s, "ratio": sf})
                out.append(qt)
        return out


class AlphaVantage(Provider):
    """Alpha Vantage 무료 키 — 비수정 일봉(TIME_SERIES_DAILY) + 배당(DIVIDENDS, 배당락일·금액) + 분할(SPLITS).
    약관(alphavantage.co/terms_of_service): 개인·비상업 이용. 저장·파생 결과물 제한 조항 없음, 상업 활동으로 남에게 정보를 제공하는 것만 상업 이용.
    무료 한도 하루 25회: 종목마다 일봉 1회(100일치라 기준·평가 세션을 함께 받음) + 배당 1회, 비교 지수(SPY)는 일봉만 → 미국 10종목 + SPY면 21회.
    기준 종가는 평가 종가와 같은 날 받는다(due_sessions defer_base) — 같은 종목을 이틀 연속 부르지 않게.
    분할은 전 거래일 대비 종가가 40% 넘게 움직였을 때만 SPLITS를 부른다(분할이 있으면 원 가격이 크게 바뀌므로).
    같은 실행 안에서는 응답을 다시 쓰고(세션이 둘이어도 호출 1회), 호출 사이에 AV_PACE_SEC(기본 13초)를 쉰다."""
    name = "alphavantage"
    markets = ("US",)
    supplies_corporate_actions = True
    BASE = "https://www.alphavantage.co/query"
    _cache: dict = {}                                   # (function, symbol) → 응답 (실행 동안 공유)
    _last_call: float = 0.0                             # 마지막 호출 시각(모든 인스턴스 공유) — 세션마다 새 인스턴스여도 간격 유지

    def __init__(self):
        super().__init__()
        self.key = os.environ.get("ALPHAVANTAGE_API_KEY")
        if not self.key:
            raise NotConfigured("ALPHAVANTAGE_API_KEY 환경변수 없음")
        self.pace = float(os.environ.get("AV_PACE_SEC", "13"))
        self.calls = 0
        self.price_only: set = set()                    # 비교 지수(SPY) 등 가격만 쓰는 종목: 배당·분할 조회를 건너뛴다

    def _q(self, function: str, symbol: str):
        k = (function, symbol)
        if k in AlphaVantage._cache:
            return AlphaVantage._cache[k]
        if self.pace and AlphaVantage._last_call:
            wait = self.pace - (time.monotonic() - AlphaVantage._last_call)
            if wait > 0:
                time.sleep(wait)
        self.calls += 1
        AlphaVantage._last_call = time.monotonic()
        q = urllib.parse.urlencode({"function": function, "symbol": symbol, "apikey": self.key})
        res = self._try_get(f"AlphaVantage {function} {symbol}", f"{self.BASE}?{q}")
        if isinstance(res, dict) and not ({"Time Series (Daily)", "data"} & set(res)):
            note = res.get("Information") or res.get("Note") or res.get("Error Message") or str(res)[:200]
            self.errors.append({"api": f"AlphaVantage {function} {symbol}", "body": str(note)[:300]})   # 한도 초과·기호 오류 등
            return None
        AlphaVantage._cache[k] = res
        return res

    def fetch(self, market, tickers, session):
        out, s = [], session.isoformat()
        for t in tickers:
            sym = t.replace(".", "-")                    # Alpha Vantage 표기: BRK.B → BRK-B
            daily = (self._q("TIME_SERIES_DAILY", sym) or {}).get("Time Series (Daily)") or {}
            if s not in daily:
                continue
            close = _num(daily[s].get("4. close"))
            qt = Quote("US", t, s, close)
            prev = sorted(d_ for d_ in daily if d_ < s)
            pc = _num(daily[prev[-1]].get("4. close")) if prev else None
            if t in self.price_only:                      # 가격만 쓰는 종목(비교 지수): 호출 절약, 기업행동 기록 없음
                qt.ca_checked = False
                out.append(qt)
                continue
            divs = self._q("DIVIDENDS", sym)
            if divs is None:                              # 배당을 확인하지 못하면 이 종목은 기록하지 않는다(확인 없이 '확인됨'을 남기지 않게)
                continue
            for r in divs.get("data") or []:
                if r.get("ex_dividend_date") == s and _num(r.get("amount")):
                    qt.dividends.append({"ex_date": s, "amount": _num(r["amount"]), "currency": "USD",
                                         "pay_date": r.get("payment_date")})
            if close and pc and not (0.6 < close / pc < 1.4):
                sp = self._q("SPLITS", sym)
                if sp is None:                            # 분할 여부를 확인하지 못하면 기록하지 않는다
                    continue
                for r in sp.get("data") or []:
                    if r.get("effective_date") == s and _num(r.get("split_factor")):
                        qt.splits.append({"ex_date": s, "ratio": _num(r["split_factor"])})
            out.append(qt)
        return out


class Alpaca(Provider):
    """Alpaca Market Data v2 — 일봉(raw, feed=sip). 잠정값·대조용.
    미검증: 무료/paper 계정에서 feed=sip 과거 일봉이 되는지 실제 계정으로 시험할 것."""
    name = "alpaca"
    markets = ("US",)

    def __init__(self):
        super().__init__()
        self.kid, self.sec = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
        if not (self.kid and self.sec):
            raise NotConfigured("ALPACA_KEY_ID / ALPACA_SECRET_KEY 환경변수 없음")

    def fetch(self, market, tickers, session):
        q = urllib.parse.urlencode({"symbols": ",".join(tickers), "timeframe": "1Day", "start": session.isoformat(),
                                    "end": session.isoformat(), "adjustment": "raw", "feed": "sip"})
        res = self._try_get("Alpaca bars", f"https://data.alpaca.markets/v2/stocks/bars?{q}",
                            {"APCA-API-KEY-ID": self.kid, "APCA-API-SECRET-KEY": self.sec}) or {}
        out = []
        for sym, bars in (res.get("bars") or {}).items():
            for b in bars:
                out.append(Quote("US", sym, str(b.get("t", ""))[:10], _num(b.get("c"))))
        return out


class KIS(Provider):
    name = "kis"
    markets = ("KR",)

    def __init__(self):
        raise NotConfigured("KIS는 OAuth 토큰 발급 절차가 필요해 아직 구현하지 않음 (사용권 확인 후 결정)")


PROVIDERS = {"mock": MockProvider, "krx_openapi": KRXOpenAPI, "tiingo": Tiingo, "alphavantage": AlphaVantage, "alpaca": Alpaca, "kis": KIS}


def _num(v):
    if v in (None, "", "-"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _ymd(v):
    v = str(v or "")
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) == 8 and v.isdigit() else v[:10]


NASDAQ_DIV_URL = "https://api.nasdaq.com/api/calendar/dividends?date={d}"


def nasdaq_dividends(session: date) -> dict | None:
    """Nasdaq 배당 달력(공개 JSON, 비공식) — 그날이 배당락일인 미국 종목 {티커: 1주당 배당(달러)}.
    채점용 값으로 쓰지 않고 Alpha Vantage 배당 누락을 잡는 내부 대조에만 쓴다. 받지 못하면 None."""
    req = urllib.request.Request(NASDAQ_DIV_URL.format(d=session.isoformat()),
                                 headers={"User-Agent": "league-collector/0.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception:  # noqa: BLE001 — 대조 실패는 수집을 멈추지 않는다(경고만)
        return None
    rows = (((data or {}).get("data") or {}).get("calendar") or {}).get("rows")
    if rows is None:
        return None
    want = session.strftime("%m/%d/%Y")
    out = {}
    for x in rows:
        sym = str(x.get("symbol") or "").replace("/", ".").strip()
        amt = _num(x.get("dividend_Rate"))
        if sym and amt and x.get("dividend_Ex_Date") == want:
            out[sym] = out.get(sym, 0) + amt
    return out


def dividend_mismatch(av_amount: float, nq_amount: float | None) -> str | None:
    """Alpha Vantage 배당 합계와 Nasdaq 일정 비교. 문제면 사유, 아니면 None.
    Nasdaq에 없고 Alpha Vantage에만 있으면 문제로 보지 않는다(Alpha Vantage가 더 많이 아는 경우)."""
    if not nq_amount:
        return None
    if not av_amount:
        return f"Nasdaq 일정에 배당 {nq_amount:g}달러가 있는데 Alpha Vantage 기록 없음"
    if abs(av_amount - nq_amount) / nq_amount > 0.02:
        return f"배당 금액 불일치: Alpha Vantage {av_amount:g} / Nasdaq {nq_amount:g}"
    return None


def collect(d: Path, provider: Provider, market: str, tickers: list[str], session: date, role: str,
            now: str | None = None) -> dict:
    """공통 검사를 거쳐 prices(및 기업행동) 원장에 기록. 결과 요약을 돌려준다."""
    assert role in ("provisional", "final")
    now = now or datetime.now(L.KST).isoformat(timespec="seconds")
    idx = L.price_index(d)
    res = {"recorded": [], "failed": [], "skipped": [], "discrepancies": [], "dividend_holds": [], "warnings": []}
    nq = None
    if market == "US" and role == "final" and provider.supplies_corporate_actions and provider.name != "mock":
        nq = nasdaq_dividends(session)
        if nq is None:
            res["warnings"].append(f"Nasdaq 배당 일정({session})을 받지 못해 배당 대조를 못 함 — Alpha Vantage 값만으로 기록")
    got = {}
    for q in provider.fetch(market, tickers, session):
        got.setdefault(q.ticker, []).append(q)
    res["provider_errors"] = list(getattr(provider, "errors", []))
    for t in tickers:
        qs = got.get(t, [])
        q = next((x for x in qs if x.session == session.isoformat()), None)
        if not q:
            seen = sorted({x.session for x in qs})
            res["failed"].append({"ticker": t, "reason": f"요청 거래일 {session} 값 없음" + (f" (응답 거래일 {', '.join(seen)})" if seen else "")})
            continue
        if not q.halted and (q.close is None or q.close <= 0):
            res["failed"].append({"ticker": t, "reason": "종가 없음 또는 0 이하"})
            continue
        prev = idx.get((market, t, session.isoformat()))
        if prev and prev.get("status") == "final" and role == "provisional":
            res["skipped"].append({"ticker": t, "reason": "이미 확정 값 있음"})
            continue
        if prev and prev.get("close") is not None and q.close is not None and prev["close"] != q.close:
            diff = round((q.close / prev["close"] - 1) * 100, 4)
            chk = {"market": market, "ticker": t, "session": session.isoformat(), "previous": prev["close"],
                   "previous_source": prev.get("source"), "previous_status": prev.get("status"),
                   "new": q.close, "new_source": provider.name, "new_status": role, "diff_pct": diff, "at": now}
            L.append(d, "price_checks", chk)
            res["discrepancies"].append(chk)
        if prev and prev.get("close") == q.close and prev.get("status") == role and prev.get("source") == provider.name:
            res["skipped"].append({"ticker": t, "reason": "같은 값 이미 기록됨"})
            continue
        L.append(d, "prices", {"market": market, "ticker": t, "session": session.isoformat(), "close": q.close,
                               "basis": q.basis, "halted": q.halted, "source": provider.name, "status": role,
                               "fetched_at": now})
        if provider.supplies_corporate_actions and role == "final" and getattr(q, "ca_checked", True):
            why = dividend_mismatch(sum(float(x["amount"]) for x in q.dividends), (nq or {}).get(t)) if nq is not None else None
            if why:
                # 배당이 맞는지 모르면 '확인 완료'를 남기지 않는다 → 채점 보류(0점 아님). 운영자가 확인 뒤 manual-dividend 로 기록
                res["dividend_holds"].append({"ticker": t, "session": session.isoformat(), "reason": why})
                res["recorded"].append(t)
                continue
            for dv in q.dividends:
                L.append(d, "corporate_actions", {"type": "dividend", "market": market, "ticker": t, **dv,
                                                  "source": provider.name})
            for sp in q.splits:
                L.append(d, "corporate_actions", {"type": "split", "market": market, "ticker": t, **sp,
                                                  "source": provider.name})
            L.append(d, "corporate_actions", {"type": "checked", "market": market, "ticker": t, "from": session.isoformat(),
                                              "to": session.isoformat(), "source": provider.name, "checked_at": now})
        res["recorded"].append(t)
    return res


def due_sessions(d: Path, today: date, defer_base: set | None = None) -> dict:
    """채점·공통 자료에 필요한 (시장, 세션) → 종목 집합. 아직 확정 값이 없는 것만.
    - 추천의 기준·평가 세션 중 오늘 이전에 끝난 세션
    - 각 세션의 비교 지수(benchmarks)"""
    cfg = L.load_config(d)
    idx = L.price_index(d)
    need: dict[tuple, set] = {}
    defer_base = defer_base or set()
    for p in L.read_ledger(d, "picks"):
        ev = p.get("eval_session")
        for s_ in (p.get("base_session"), ev):
            if p["market"] in defer_base and s_ == p.get("base_session") and not (ev and date.fromisoformat(ev) < today):
                continue                                # 호출 한도가 빠듯한 제공처: 기준 종가는 평가 종가와 같은 날 한 번에(일봉 1회로 둘 다 받음)
            if s_ and date.fromisoformat(s_) < today:
                tk = need.setdefault((p["market"], s_), set())
                if not L.is_watch(p, cfg):                 # 관망은 비교 지수만 있으면 된다(아래에서 추가)
                    tk.add(p["ticker"])
    for (m, s_), tks in list(need.items()):
        b = cfg.get("benchmarks", {}).get(m)
        if b:
            tks.add(b)
    out = {}
    for (m, s_), tks in sorted(need.items()):
        left = sorted(t for t in tks if (idx.get((m, t, s_)) or {}).get("status") != "final")
        if left:
            out[(m, s_)] = left
    return out


def kr_corporate_actions_due(d: Path, today: date) -> list[dict]:
    """한국 추천 중 배당·분할 확인 기록이 없는 구간을 DART 공시로 확인한다. 키가 없으면 건너뛴다(채점 보류 유지)."""
    try:
        import dart
        key = dart._key()
    except Exception as e:
        return [{"skipped": True, "reason": str(e)}]
    cfg = L.load_config(d)
    cas = L.corporate_actions(d)
    todo = {}
    for p in L.read_ledger(d, "picks"):
        if p["market"] != "KR" or not p.get("eval_session") or L.is_watch(p, cfg):
            continue
        b, e = date.fromisoformat(p["base_session"]), date.fromisoformat(p["eval_session"])
        if e >= today or L.ca_for(cas, "KR", p["ticker"], b, e, cfg)[0]:
            continue
        todo[(p["ticker"], b, e)] = True
    if not todo:
        return []
    out = []
    for (t, b, e) in sorted(todo):
        try:                                    # 종목별 조회 (DART 고유번호 기준, 최근 120일)
            res = dart.check_kr_corporate_actions(d, t, b, e, key)
        except Exception as ex:
            out.append({"ticker": t, "error": f"{type(ex).__name__}: {str(ex)[:200]}"})
            continue
        recorded = dart.record_kr_ca(d, res)
        out.append({"ticker": t, "window": res["window"], "checked": res["checked"], "recorded": recorded,
                    "dividends": res["dividends"], "unresolved": res["unresolved"]})
    return out


def collect_due(d: Path, today: date) -> dict:
    """설정된 제공처(config.providers.<시장>.final / provisional)로 필요한 값을 받고 채점까지 돌린다.
    키가 없으면 그 시장은 건너뛰고 사유를 남긴다 (실패로 멈추지 않음)."""
    cfg = L.load_config(d)
    provs = cfg.get("providers", {})
    report = {"today": today.isoformat(), "collected": [], "skipped": [], "scoring": []}
    defer = {m for m, v in provs.items() if (v or {}).get("final") == "alphavantage"}
    for (m, s_), tks in due_sessions(d, today, defer).items():
        name = provs.get(m, {}).get("final")
        if not name:
            report["skipped"].append({"market": m, "session": s_, "reason": "config.providers 에 확정 제공처 없음"})
            continue
        try:
            prov = PROVIDERS[name]()
        except NotConfigured as e:
            report["skipped"].append({"market": m, "session": s_, "provider": name, "reason": str(e)})
            continue
        bench = cfg.get("benchmarks", {}).get(m)
        if bench and hasattr(prov, "price_only"):
            prov.price_only = {bench}                    # 비교 지수는 가격 수익률만 쓴다(배당 조회 불필요)
        r = collect(d, prov, m, tks, date.fromisoformat(s_), "final")
        report["collected"].append({"market": m, "session": s_, "provider": name, "recorded": r["recorded"],
                                    "failed": r["failed"], "provider_errors": r.get("provider_errors", []),
                                    "discrepancies": len(r["discrepancies"]),
                                    "dividend_holds": r.get("dividend_holds", []), "warnings": r.get("warnings", [])})
    report["kr_corporate_actions"] = kr_corporate_actions_due(d, today)
    for w in L.run_scoring(d, today=today):
        report["scoring"].append({"pick_id": w["pick_id"], "status": w["status"], "score": w.get("score"), "reason": w.get("reason")})
    return report


def manual_dividend(d: Path, market: str, ticker: str, session: date, amount: float, note: str,
                    pay_date: str | None = None, now: str | None = None) -> list[dict]:
    """배당 보류 해소: 운영자가 공식 발표로 확인한 배당(없으면 amount=0)을 기록하고 그 세션을 '확인 완료'로 남긴다."""
    if not note.strip():
        raise ValueError("note(확인한 공식 출처)는 비울 수 없다")
    now = now or datetime.now(L.KST).isoformat(timespec="seconds")
    src = f"manual: {note.strip()}"
    out = []
    if amount > 0:
        rec = {"type": "dividend", "market": market, "ticker": ticker, "ex_date": session.isoformat(), "amount": amount,
               "currency": "USD" if market == "US" else "KRW", "pay_date": pay_date, "source": src}
        L.append(d, "corporate_actions", rec)
        out.append(rec)
    chk = {"type": "checked", "market": market, "ticker": ticker, "from": session.isoformat(), "to": session.isoformat(),
           "source": src, "checked_at": now}
    L.append(d, "corporate_actions", chk)
    out.append(chk)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["collect", "manual-dividend"])
    ap.add_argument("--dir", default=str(L.ROOT / "league"))
    ap.add_argument("--market", required=True, choices=["KR", "US"])
    ap.add_argument("--session", required=True)
    if len(sys.argv) > 1 and sys.argv[1] == "manual-dividend":
        ap.add_argument("--ticker", required=True)
        ap.add_argument("--amount", required=True, type=float, help="1주당 배당(없으면 0)")
        ap.add_argument("--note", required=True, help="확인한 공식 출처(회사 발표 URL 등)")
        ap.add_argument("--pay-date")
        a = ap.parse_args()
        print(json.dumps(manual_dividend(Path(a.dir), a.market, a.ticker, date.fromisoformat(a.session), a.amount,
                                         a.note, a.pay_date), ensure_ascii=False, indent=1))
        return
    ap.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    ap.add_argument("--tickers", required=True, help="쉼표 구분")
    ap.add_argument("--role", default="provisional", choices=["provisional", "final"])
    ap.add_argument("--fixture")
    a = ap.parse_args()
    try:
        prov = MockProvider(a.fixture) if a.provider == "mock" else PROVIDERS[a.provider]()
    except NotConfigured as e:
        sys.exit(f"설정 안 됨: {e}")
    r = collect(Path(a.dir), prov, a.market, [t.strip() for t in a.tickers.split(",") if t.strip()],
                date.fromisoformat(a.session), a.role)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(1 if r["failed"] else 0)


if __name__ == "__main__":
    main()
