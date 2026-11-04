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
  환경변수: KRX_AUTH_KEY, TIINGO_TOKEN, ALPACA_KEY_ID, ALPACA_SECRET_KEY
"""
from __future__ import annotations

import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request
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


PROVIDERS = {"mock": MockProvider, "krx_openapi": KRXOpenAPI, "tiingo": Tiingo, "alpaca": Alpaca, "kis": KIS}


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


def collect(d: Path, provider: Provider, market: str, tickers: list[str], session: date, role: str,
            now: str | None = None) -> dict:
    """공통 검사를 거쳐 prices(및 기업행동) 원장에 기록. 결과 요약을 돌려준다."""
    assert role in ("provisional", "final")
    now = now or datetime.now(L.KST).isoformat(timespec="seconds")
    idx = L.price_index(d)
    res = {"recorded": [], "failed": [], "skipped": [], "discrepancies": []}
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
        if provider.supplies_corporate_actions and role == "final":
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


def due_sessions(d: Path, today: date) -> dict:
    """채점·공통 자료에 필요한 (시장, 세션) → 종목 집합. 아직 확정 값이 없는 것만.
    - 추천의 기준·평가 세션 중 오늘 이전에 끝난 세션
    - 각 세션의 비교 지수(benchmarks)"""
    cfg = L.load_config(d)
    idx = L.price_index(d)
    need: dict[tuple, set] = {}
    for p in L.read_ledger(d, "picks"):
        for s_ in (p.get("base_session"), p.get("eval_session")):
            if s_ and date.fromisoformat(s_) < today:
                need.setdefault((p["market"], s_), set()).add(p["ticker"])
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
        if p["market"] != "KR" or not p.get("eval_session"):
            continue
        b, e = date.fromisoformat(p["base_session"]), date.fromisoformat(p["eval_session"])
        if e >= today or L.ca_for(cas, "KR", p["ticker"], b, e, cfg)[0]:
            continue
        todo[(p["ticker"], b, e)] = True
    if not todo:
        return []
    lo = min(b for _, b, _ in todo) - timedelta(days=120)
    hi = max(e for _, _, e in todo)
    try:
        items = dart.list_disclosures(lo, hi, key)
    except Exception as ex:
        return [{"error": f"{type(ex).__name__}: {str(ex)[:200]}"}]
    out = []
    for (t, b, e) in sorted(todo):
        res = dart.check_kr_corporate_actions(d, t, b, e, key, items=[i for i in items if i.get("rcept_dt", "") <= e.strftime("%Y%m%d")])
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
    for (m, s_), tks in due_sessions(d, today).items():
        name = provs.get(m, {}).get("final")
        if not name:
            report["skipped"].append({"market": m, "session": s_, "reason": "config.providers 에 확정 제공처 없음"})
            continue
        try:
            prov = PROVIDERS[name]()
        except NotConfigured as e:
            report["skipped"].append({"market": m, "session": s_, "provider": name, "reason": str(e)})
            continue
        r = collect(d, prov, m, tks, date.fromisoformat(s_), "final")
        report["collected"].append({"market": m, "session": s_, "provider": name, "recorded": r["recorded"],
                                    "failed": r["failed"], "provider_errors": r.get("provider_errors", []),
                                    "discrepancies": len(r["discrepancies"])})
    report["kr_corporate_actions"] = kr_corporate_actions_due(d, today)
    for w in L.run_scoring(d, today=today):
        report["scoring"].append({"pick_id": w["pick_id"], "status": w["status"], "score": w.get("score"), "reason": w.get("reason")})
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["collect"])
    ap.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    ap.add_argument("--market", required=True, choices=["KR", "US"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--tickers", required=True, help="쉼표 구분")
    ap.add_argument("--role", default="provisional", choices=["provisional", "final"])
    ap.add_argument("--fixture")
    ap.add_argument("--dir", default=str(L.ROOT / "league"))
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
