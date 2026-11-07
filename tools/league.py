#!/usr/bin/env python3
"""AI 투자 리그 엔진: 원장(append-only + 해시 체인), 거래일 달력, 채점, 주간 순위, CSV 가져오기.

모든 계산은 결정적이다 (LLM 미사용). 규칙은 docs/ai-league-proposal.md 와 league/config.json.

사용법:
  python3 tools/league.py verify   [--dir league]        # 원장 해시 체인 검증
  python3 tools/league.py score    [--dir league]        # 미확정 추천 채점 → scores.jsonl 에 추가
  python3 tools/league.py weekly 2026-W46 [--dir league] # 주간 순위·교체 판정 출력
  python3 tools/league.py import-csv FILE --team shushu  # 외부 팀(Codex) 추천 가져오기
  python3 tools/league.py sample   --dir league/sample   # 예시 데이터 생성 (화면·계산 검증용)
  python3 tools/league.py export   [--dir league]        # 화면용 league.js 생성
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, statistics, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
KST = ZoneInfo("Asia/Seoul")
LEDGERS = ("picks", "prices", "scores", "corrections", "corporate_actions", "submissions", "approvals", "price_checks",
           "weekly_decisions", "guidelines", "outages", "external_pushes", "shushu_wakes")

# ───────────────────────── 설정 ─────────────────────────

def load_config(d: Path) -> dict:
    p = d / "config.json"
    if not p.exists():
        p = ROOT / "league" / "config.json"
    return json.loads(p.read_text())

# ───────────────────────── 원장 (append-only + 해시 체인) ─────────────────────────

def _canon(rec: dict) -> str:
    return json.dumps({k: v for k, v in rec.items() if k not in ("hash",)}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))

def read_ledger(d: Path, name: str) -> list[dict]:
    p = d / "ledger" / f"{name}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def append(d: Path, name: str, rec: dict) -> dict:
    """원장 끝에 한 줄 추가. 기존 줄은 절대 수정하지 않는다."""
    rows = read_ledger(d, name)
    rec = dict(rec)
    rec["prev_hash"] = rows[-1]["hash"] if rows else "0" * 64
    rec["hash"] = hashlib.sha256(_canon(rec).encode()).hexdigest()
    p = d / "ledger" / f"{name}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return rec

def verify(d: Path) -> list[str]:
    errors = []
    for name in LEDGERS:
        prev = "0" * 64
        for i, r in enumerate(read_ledger(d, name), 1):
            if r.get("prev_hash") != prev:
                errors.append(f"{name}.jsonl:{i} prev_hash 불일치 (앞 줄이 수정·삭제됨)")
            if hashlib.sha256(_canon(r).encode()).hexdigest() != r.get("hash"):
                errors.append(f"{name}.jsonl:{i} 내용 해시 불일치 (이 줄이 수정됨)")
            prev = r.get("hash")
    return errors

# ───────────────────────── 거래일 달력 ─────────────────────────

_CAL = {}
CAL_CODE = {"KR": "XKRX", "US": "XNYS"}

def _cal(market):
    if market not in _CAL:
        import exchange_calendars as xc
        _CAL[market] = xc.get_calendar(CAL_CODE[market])
    return _CAL[market]

def is_session(market: str, day: date, cfg: dict) -> bool:
    if day.isoformat() in cfg.get("calendar_overrides", {}).get(market, {}).get("closed", []):
        return False
    return bool(_cal(market).is_session(day.isoformat()))

def prev_session(market: str, day: date, cfg: dict) -> date:
    d = day - timedelta(days=1)
    while not is_session(market, d, cfg):
        d -= timedelta(days=1)
    return d

def next_session(market: str, day: date, cfg: dict) -> date:
    d = day + timedelta(days=1)
    while not is_session(market, d, cfg):
        d += timedelta(days=1)
    return d

def round_sessions(market: str, round_date: date, cfg: dict):
    """라운드 D (KST 08:30 마감)의 기준·평가 세션.
    해당 시장이 D에 열릴 때만 그 시장 종목을 고를 수 있다 → 평가 = D, 기준 = D 직전 세션.
    (KST 08:30 시점에 한국 D-1 종가와 미국 현지 D-1 종가가 모두 확정, 두 시장 모두 D 세션 시작 전)"""
    if not is_session(market, round_date, cfg):
        return None
    return prev_session(market, round_date, cfg), round_date

# ───────────────────────── 채점 ─────────────────────────
# 규칙 (2026-11-03 운영 기준 확정):
#   총수익 점수 = ((평가 종가 + 귀속 현금배당) × 분할비율 ÷ 기준 종가 − 1) × 100     ← 공식 점수
#   주가 점수   = (평가 종가 × 분할비율 ÷ 기준 종가 − 1) × 100                       ← 참고용
#   - 가격은 비수정 종가(basis "unadjusted")가 기본. 수정주가("adjusted_total")면 배당·분할을 다시 더하지 않는다.
#   - 배당 귀속: 배당락일이 (기준 세션, 평가 세션] 안에 있을 때만. 지급일은 보지 않는다.
#     (기준일 종가에 산 사람은 다음 날이 배당락일이면 배당을 받는다)
#   - 배당금은 평가 세션 기준 주식 1주당 금액(세전)으로 기록한다.
#   - 배당·분할 정보가 해당 구간에 대해 '확인됨(checked)' 기록이 없으면 보류. 0점 처리하지 않는다.

def compute_scores(base_close: float, eval_close: float, split: float = 1.0, dividend: float = 0.0) -> tuple[float, float]:
    """(총수익 점수, 주가 점수). split: 기준→평가 사이 분할 비율 (1→4 분할이면 4, 10→1 병합이면 0.1)."""
    if base_close <= 0:
        raise ValueError("기준 종가가 0 이하")
    total = round(((eval_close + dividend) * split / base_close - 1) * 100, 2)
    price = round((eval_close * split / base_close - 1) * 100, 2)
    return total, price

def compute_score(base_close: float, eval_close: float, split_factor: float = 1.0, dividend: float = 0.0) -> float:
    return compute_scores(base_close, eval_close, split_factor, dividend)[0]

def price_index(d: Path) -> dict:
    """(market, ticker, session) → 최신 가격 레코드 (뒤에 추가된 정정이 우선)."""
    idx = {}
    for r in read_ledger(d, "prices"):
        idx[(r["market"], r["ticker"], r["session"])] = r
    return idx

def corporate_actions(d: Path) -> list[dict]:
    """corporate_actions.jsonl 행 유형:
    {"type":"dividend","market","ticker","ex_date","amount","currency","pay_date","source"}
    {"type":"split","market","ticker","ex_date","ratio","source"}           # ratio: 1→4 분할이면 4
    {"type":"checked","market","ticker","from","to","source","checked_at"}  # 이 구간의 배당·분할을 확인 완료"""
    return read_ledger(d, "corporate_actions")

def ca_for(cas: list[dict], m: str, t: str, after: date, upto: date, cfg: dict | None = None):
    """(after, upto] 구간의 배당 합계·분할 비율·확인 여부.
    확인 여부: 구간 안의 모든 '거래일'이 어떤 checked 기록의 [from, to] 범위에 들어가야 한다 (주말·휴장일은 볼 필요 없음)."""
    mine = [c for c in cas if c["market"] == m and c["ticker"] == t]
    ranges = [(date.fromisoformat(c["from"]), date.fromisoformat(c["to"])) for c in mine if c["type"] == "checked"]
    sessions, x = [], after
    while True:
        x = next_session(m, x, cfg or {"calendar_overrides": {}})
        if x > upto:
            break
        sessions.append(x)
    checked = bool(sessions) and all(any(a <= s_ <= b for a, b in ranges) for s_ in sessions)
    inwin = lambda c: after < date.fromisoformat(c["ex_date"]) <= upto
    divs = [c for c in mine if c["type"] == "dividend" and inwin(c)]
    splits = [c for c in mine if c["type"] == "split" and inwin(c)]
    ratio = 1.0
    for s in splits:
        ratio *= float(s["ratio"])
    return checked, round(sum(float(c["amount"]) for c in divs), 6), ratio, divs, splits

def latest_scores(d: Path) -> dict:
    out = {}
    for r in read_ledger(d, "scores"):
        out[r["pick_id"]] = r
    return out

def is_watch(p: dict, cfg: dict) -> bool:
    """'관망' 카드(v1.9): 종목 대신 비교 지수를 따라가는 제출."""
    return str(p.get("ticker", "")).upper() == (cfg.get("watch") or {}).get("ticker", "WATCH")

def evaluate_pick(p: dict, prices: dict, cfg: dict, today: date, cas: list[dict] | None = None) -> dict:
    """추천 1건의 현재 채점 상태를 계산한다 (원장에 쓰지는 않음)."""
    w = cfg["weekly"]
    cas = cas or []
    m, t = p["market"], p["ticker"]
    watch = is_watch(p, cfg)
    if watch:                                   # 관망: 비교 지수 가격 수익률이 점수(초과 0). 지수라 배당·분할 확인 없음
        t = cfg.get("benchmarks", {}).get(m)
    base_s, eval_s = date.fromisoformat(p["base_session"]), date.fromisoformat(p["eval_session"])
    out = {"pick_id": p["pick_id"], "eval_session": p["eval_session"], "status": "pending", "score": None,
           "score_price_only": None, "reason": None, "delayed": False}
    base = prices.get((m, t, base_s.isoformat()))
    if today <= eval_s:
        out["reason"] = "평가일 종가 대기"
        return out
    if not base or base.get("close") is None:
        out.update(status="held", reason="기준 종가 미확인")
        return out
    # 평가일 거래정지 → 재개 후 첫 종가, 정해진 세션 수 초과 시 무효
    s, tries = eval_s, 0
    ev = prices.get((m, t, s.isoformat()))
    while ev and ev.get("halted"):
        tries += 1
        if tries > w["halt_void_after_sessions"]:
            out.update(status="void", reason=f"거래정지 {w['halt_void_after_sessions']}세션 초과")
            return out
        s = next_session(m, s, cfg)
        if s >= today:
            out.update(status="held", reason="거래정지 — 재개 대기")
            return out
        ev = prices.get((m, t, s.isoformat()))
    if not ev or ev.get("close") is None:
        waited, x = 0, eval_s
        while x < today and waited <= w["missing_price_wait_sessions"]:
            x = next_session(m, x, cfg); waited += 1
        out.update(status="held", reason="평가 종가 미확인" + (" — 수동 확인 필요" if waited > w["missing_price_wait_sessions"] else ""))
        return out
    bb, eb = base.get("basis", "unadjusted"), ev.get("basis", "unadjusted")
    if bb != eb:
        out.update(status="held", reason=f"기준·평가 가격 기준 불일치 ({bb} / {eb})")
        return out
    if bb == "adjusted_total":
        # 배당·분할이 이미 반영된 수정주가: 다시 더하지 않는다. 주가 점수는 별도로 계산 불가.
        total = round((ev["close"] / base["close"] - 1) * 100, 2)
        price_only, div, ratio, refs = None, 0.0, 1.0, []
    else:
        checked, div, ratio, divs, splits = (True, 0.0, 1.0, [], []) if watch else ca_for(cas, m, t, base_s, s, cfg)
        if not checked:
            out.update(status="held", reason="배당·분할 정보 미확인")
            return out
        if divs and splits:
            out.update(status="held", reason="배당과 분할이 같은 구간에 발생 — 수동 확인 필요")
            return out
        total, price_only = compute_scores(base["close"], ev["close"], ratio, div)
        refs = [c["hash"] for c in divs + splits]
        lim = cfg.get("extreme_move_hold_pct", 30)
        if abs(total) > lim and not watch and not p.get("extreme_move_confirmed"):
            # 기업행동 누락·가격 오류 가능성: 운영자 확인 전까지 보류 (확인 기록은 corrections 원장 또는 별도 승인으로)
            confirmed = any(c.get("type") == "extreme_move_confirmed" and c.get("pick_id") == p["pick_id"]
                            for c in cas)
            if not confirmed:
                out.update(status="held", reason=f"하루 변동 {total:+.2f}% (±{lim}% 초과) — 기업행동 누락·가격 오류 확인 필요")
                return out
    # 참고: 시장 대비 초과 점수 = 공식 점수 − 같은 구간 벤치마크 지수 수익률 (지수는 가격지수)
    bench = cfg.get("benchmarks", {}).get(m)
    bb_, be_ = prices.get((m, bench, base_s.isoformat())), prices.get((m, bench, s.isoformat()))
    bench_ret = excess = None
    if bench and bb_ and be_ and bb_.get("close") and be_.get("close"):
        bench_ret = round((be_["close"] / bb_["close"] - 1) * 100, 2)
        excess = 0.0 if watch else round(total - bench_ret, 2)
    final = base.get("status") == "final" and ev.get("status") == "final"
    out.update(status="final" if final else "provisional", score=total, score_price_only=price_only,
               benchmark=bench, benchmark_return=bench_ret, score_excess=excess,
               eval_session=s.isoformat(), delayed=s != eval_s, reason="거래정지 후 지연 채점" if s != eval_s else None,
               base_close=base["close"], eval_close=ev["close"], price_basis=bb,
               adjustment={"split": ratio, "dividend": div, "corporate_action_refs": refs})
    return out

def run_scoring(d: Path, today: date | None = None, now: str | None = None) -> list[dict]:
    """상태가 바뀐 추천만 scores.jsonl 에 추가. final 이후 값이 바뀌면 correction 으로 기록."""
    cfg = load_config(d)
    today = today or datetime.now(KST).date()
    prices, prev, cas = price_index(d), latest_scores(d), corporate_actions(d)
    written = []
    for p in read_ledger(d, "picks"):
        cur = evaluate_pick(p, prices, cfg, today, cas)
        old = prev.get(p["pick_id"])
        keys = ("status", "score", "score_price_only", "score_excess", "reason", "eval_session")
        if old and all(old.get(k) == cur.get(k) for k in keys):
            continue
        if old is None and cur["status"] == "pending":
            continue
        cur["scored_at"] = now or datetime.now(KST).isoformat(timespec="seconds")
        if old and old["status"] == "final":
            cur["correction_of"] = old["hash"]
            append(d, "corrections", {"pick_id": p["pick_id"], "before": old.get("score"), "after": cur.get("score"),
                                      "reason": "확정 후 가격·배당 정정", "at": cur["scored_at"]})
        written.append(append(d, "scores", cur))
    return written

# ───────────────────────── 주간 순위 ─────────────────────────

def iso_week(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"

def load_roster(d: Path) -> dict:
    """league/agents/roster.json + 외부 팀이 제출한 league/imports/<팀>/roster.json (해당 팀 키가 없을 때)."""
    p = d / "agents" / "roster.json"
    roster = json.loads((p if p.exists() else ROOT / "league" / "agents" / "roster.json").read_text())
    for rp in sorted((d / "imports").glob("*/roster.json")) if (d / "imports").exists() else []:
        team = rp.parent.name
        if team in roster or team == "sandbox":
            continue
        data = json.loads(rp.read_text())
        roster[team] = [{"status": "active", "joined_week": None, "eliminated_week": None, **a} for a in (data.get("members", []) if isinstance(data, dict) else data)
                        if isinstance(a, dict)]
        if isinstance(data, dict) and data.get("bench"):
            roster.setdefault("bench_" + team, data["bench"])
    # 주간 마감 기록을 순서대로 적용: 탈락 → 상태 변경, 대체자 → 대기 명단에서 현역으로 (합류 주 = 다음 주)
    for dec in read_ledger(d, "weekly_decisions"):
        team, wk = dec["team"], dec["week"]
        members = roster.setdefault(team, [])
        bench_key = "bench" if team == "claude" else f"bench_{team}"
        if dec.get("market"):                       # v2.0 리그별 결정: 그 시장 자리만 바뀐다
            _apply_market_decision(members, roster.get(bench_key, []), dec)
            continue
        if dec.get("eliminate"):
            for a in members:
                if a["id"] == dec["eliminate"]:
                    a["status"], a["eliminated_week"] = "eliminated", wk
        if dec.get("replacement"):
            bench = roster.get(bench_key, [])
            b = next((x for x in bench if x["id"] == dec["replacement"]), {"id": dec["replacement"], "label": dec["replacement"]})
            roster[bench_key] = [x for x in bench if x["id"] != dec["replacement"]]
            members.append({**{k: v for k, v in b.items() if k not in ("approved", "approved_at")}, "status": "active",
                            "joined_week": dec["effective_week"], "eliminated_week": None, "version": b.get("version", 1)})
    return roster

MARKETS = ("KR", "US")

def mstatus(a: dict, mk: str) -> dict:
    """시장별 참가 상태 {status: active|eliminated|bench, joined_week, eliminated_week}.
    리그별 결정이 없던 멤버는 두 시장 모두 같은 상태(예전 방식)."""
    ms = (a.get("markets") or {}).get(mk)
    if ms:
        return ms
    return {"status": a.get("status", "active"), "joined_week": a.get("joined_week"), "eliminated_week": a.get("eliminated_week")}

def active_in(a: dict, mk: str, week: str) -> bool:
    """그 주에 그 시장에서 뛰는가 (탈락한 주까지는 포함, 합류 주부터 포함)."""
    ms = mstatus(a, mk)
    if ms.get("status") == "bench":
        return False
    if ms.get("joined_week") and ms["joined_week"] > week:
        return False
    return ms.get("status") == "active" or (ms.get("eliminated_week") or "") >= week

def _sync_overall(a: dict):
    sts = [mstatus(a, m) for m in MARKETS]
    if any(x.get("status") == "active" for x in sts):
        a["status"], a["eliminated_week"] = "active", None
    else:
        a["status"] = "eliminated"
        a["eliminated_week"] = max((x.get("eliminated_week") or "" for x in sts), default=None) or None
    # 합류 주: 참가 중인 시장 중 가장 이른 합류(원래 멤버처럼 합류 기록이 없는 시장이 있으면 없음)
    live = [x for x in sts if x.get("status") != "bench"]
    a["joined_week"] = None if any(not x.get("joined_week") for x in live) else min((x["joined_week"] for x in live), default=None)

def _apply_market_decision(members: list, bench: list, dec: dict):
    mk, wk = dec["market"], dec["week"]
    def materialize(a):
        a["markets"] = {m: dict(mstatus(a, m)) for m in MARKETS}
    if dec.get("eliminate"):
        for a in members:
            if a["id"] == dec["eliminate"]:
                materialize(a)
                a["markets"][mk].update(status="eliminated", eliminated_week=wk)
                _sync_overall(a)
    if dec.get("replacement"):
        rid = dec["replacement"]
        a = next((x for x in members if x["id"] == rid), None)
        if a is None:
            b = next((x for x in bench if x["id"] == rid), {"id": rid, "label": rid})
            a = {**{k: v for k, v in b.items() if k not in ("approved", "approved_at", "markets")}, "version": b.get("version", 1),
                 "markets": {m: {"status": "bench", "joined_week": None, "eliminated_week": None} for m in MARKETS}}
            members.append(a)
        else:
            materialize(a)
        a["markets"][mk] = {"status": "active", "joined_week": dec["effective_week"], "eliminated_week": None}
        _sync_overall(a)

def bench_available(d: Path, roster: dict, team: str, mk: str) -> list[dict]:
    """그 시장 빈자리에 넣을 수 있는 승인된 대기 후보(순서대로). 이미 그 시장에서 뛰었거나 탈락한 사람은 제외."""
    members = {a["id"]: a for a in roster.get(team, [])}
    return [b for b in _approved_bench(d, roster, team)
            if b["id"] not in members or mstatus(members[b["id"]], mk).get("status") == "bench"]

def _avg(v):
    return round(statistics.mean(v), 2) if v else None

def _min_needed(expected: int, w: dict, fixed_key: str) -> int:
    """최소 확정 채점 수. min_scored_ratio가 있으면 기대 제출 수의 비율(올림), 없으면 고정값."""
    if w.get("min_scored_ratio") is not None:
        return max(1, math.ceil(expected * w["min_scored_ratio"])) if expected else 0
    return w[fixed_key]

def weekly(d: Path, week: str, team: str = "claude", _rows_only: bool = False) -> dict:
    cfg = load_config(d)
    w = cfg["weekly"]
    roster = load_roster(d)
    members = [a for a in roster.get(team, []) if any(active_in(a, mk, week) for mk in MARKETS)]
    scores = latest_scores(d)
    picks = [p for p in read_ledger(d, "picks") if p["team"] == team and iso_week(date.fromisoformat(p["round_date"])) == week]
    # 이 주의 기대 제출 수 = 라운드별 열린 시장 수 (에이전트 합류 이후)
    y, wk = map(int, week.split("-W"))
    week_days = [date.fromisocalendar(y, wk, i) for i in range(1, 6)]
    outages = read_ledger(d, "outages")
    rows = []
    for a in members:
        mine = [p for p in picks if p["agent_id"] == a["id"]]
        outs = [o for o in outages if (o["team"] == team) and (o.get("agent_id") in (None, a["id"]))
                and iso_week(date.fromisoformat(o["round_date"])) == week]
        exp_m = {mk: sum(1 for dd in week_days if mk in open_markets(dd, cfg) and active_in(a, mk, week)) for mk in MARKETS}
        expected = sum(exp_m.values())
        fin = [(p, scores[p["pick_id"]]) for p in mine
               if p["pick_id"] in scores and scores[p["pick_id"]]["status"] == "final"]
        vals = [sc["score"] for _, sc in fin]
        exc = [sc["score_excess"] for _, sc in fin if sc.get("score_excess") is not None]
        by_m = {mk: [sc["score"] for p, sc in fin if p["market"] == mk] for mk in ("KR", "US")}
        exc_m = {mk: [sc["score_excess"] for p, sc in fin if p["market"] == mk and sc.get("score_excess") is not None]
                 for mk in ("KR", "US")}
        held = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") in ("held", "pending", "provisional", None))
        void = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") == "void")
        rows.append({"agent_id": a["id"], "label": a["label"], "version": max((int(p["agent_version"]) for p in mine if p.get("agent_version") is not None), default=a.get("version", 1)),
                     "picks": len(mine), "expected": expected, "missed": max(expected - len(mine), 0),
                     "submit_rate": round(len(mine) / expected * 100, 1) if expected else None,
                     "outage_rounds": sorted({o["round_date"] for o in outs}),
                     "outage_reasons": sorted({o["reason"] for o in outs}),
                     "void_rate": round(void / len(mine) * 100, 1) if mine else None,
                     "scored": len(vals), "held_or_pending": held, "void": void,
                     "avg": round(statistics.mean(vals), 2) if vals else None,
                     "median": round(statistics.median(vals), 2) if vals else None,
                     "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                     "sum": round(sum(vals), 2) if vals else 0.0, "new_this_week": a.get("joined_week") == week,
                     "avg_excess": _avg(exc),
                     "markets": {mk: {"avg": _avg(by_m[mk]), "scored": len(by_m[mk]), "avg_excess": _avg(exc_m[mk]),
                                      "sum_raw": sum(by_m[mk]),          # 팀 평균은 반올림 전 합으로 낸다
                                      "median": round(statistics.median(by_m[mk]), 2) if by_m[mk] else None,
                                      "min": min(by_m[mk]) if by_m[mk] else None, "expected": exp_m[mk],
                                      "picks": sum(1 for p in mine if p["market"] == mk),
                                      "watch": sum(1 for p in mine if p["market"] == mk and is_watch(p, cfg)),
                                      "held_or_pending": sum(1 for p in mine if p["market"] == mk and scores.get(p["pick_id"], {}).get("status") in ("held", "pending", "provisional", None)),
                                      "active": active_in(a, mk, week), "new_this_week": mstatus(a, mk).get("joined_week") == week}
                                 for mk in MARKETS}})
    nz = lambda v: -1e9 if v is None else v      # 0점은 유효한 값이므로 `or`를 쓰면 안 됨
    key = lambda r: (nz(r["avg"]), nz(r["median"]), nz(r["min"]))
    rows.sort(key=key, reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    if _rows_only:
        return {"week": week, "team": team, "ranking": rows}
    if w.get("mode") == "per_market_bottom1":
        decision = {"mode": "per_market_bottom1", "markets": {}}
        for mk in MARKETS:
            dec = weekly_market_league(d, week, mk)["decision"]
            mine = dec.get("eliminate_team") == team
            decision["markets"][mk] = {"eliminate": dec["eliminate"] if mine else None, "replacement": dec["replacement"] if mine else None,
                                       "hold_reasons": dec["hold_reasons"], "notes": dec.get("notes", []) if mine else [],
                                       "league_bottom": dec.get("bottom"), "closed_at": dec.get("closed_at")}
        return {"week": week, "team": team, "ranking": rows, "decision": decision}
    if w.get("mode") == "combined_bottom1":
        lg = weekly_league(d, week)
        dec = lg["decision"]
        mine = dec.get("eliminate_team") == team
        decision = {"eliminate": dec["eliminate"] if mine else None,
                    "replacement": dec["replacement"] if mine else None,
                    "hold_reasons": dec["hold_reasons"], "notes": dec.get("notes", []),
                    "mode": "combined_bottom1", "league_bottom": dec.get("bottom")}
        closed = next((x for x in read_ledger(d, "weekly_decisions") if x["team"] == team and x["week"] == week), None)
        if closed:
            decision.update(eliminate=closed["eliminate"], replacement=closed["replacement"],
                            hold_reasons=closed.get("hold_reasons", []), notes=closed.get("notes", []),
                            closed_at=closed.get("closed_at"))
        return {"week": week, "team": team, "ranking": rows, "decision": decision}
    decision = {"eliminate": None, "hold_reasons": []}
    total = sum(r["scored"] for r in rows)
    if rows:
        bottom = rows[-1]
        tied = [r for r in rows if key(r) == key(bottom)]
        need_t = _min_needed(sum(r["expected"] for r in rows), w, "min_total_scored_in_week")
        need_a = _min_needed(bottom["expected"], w, "min_scored_for_elimination")
        if total < need_t:
            decision["hold_reasons"].append(f"주간 채점 완료 {total}건 < {need_t}건 (데이터 부족 주간)")
        if bottom["scored"] < need_a:
            decision["hold_reasons"].append(f"최하위 {bottom['label']} 채점 {bottom['scored']}건 < {need_a}건")
        if w["protect_first_week"] and bottom["new_this_week"]:
            decision["hold_reasons"].append(f"최하위 {bottom['label']}는 이번 주 합류 (첫 주 보호)")
        if len(tied) > 1:
            decision["hold_reasons"].append("최하위 동점 (평균·중앙값·최저점 모두 같음)")
        if not decision["hold_reasons"]:
            decision["eliminate"] = bottom["agent_id"]
    approved = {(x["team"], x["agent_id"]) for x in read_ledger(d, "approvals")
                if x.get("type") == "bench" and x.get("decision") == "approved"}
    bench = [b for b in roster.get("bench" if team == "claude" else f"bench_{team}", [])
             if (team, b["id"]) in approved]                       # 운영자 승인된 대기 후보만, 순서대로 투입
    if decision["eliminate"] and not bench:
        decision.setdefault("notes", []).append("승인된 대기 후보 없음 — 탈락 후 자리 비움 (빈자리는 미제출로 세지 않음)")
    decision["replacement"] = bench[0]["id"] if decision["eliminate"] and bench else None
    # 이미 마감한 주는 기록된 결정을 그대로 쓴다 (마감 뒤 명단·대기 순서가 바뀌어도 결정은 고정)
    closed = next((x for x in read_ledger(d, "weekly_decisions") if x["team"] == team and x["week"] == week), None)
    if closed:
        decision = {"eliminate": closed["eliminate"], "replacement": closed["replacement"],
                    "hold_reasons": closed.get("hold_reasons", []), "notes": closed.get("notes", []),
                    "closed_at": closed.get("closed_at")}
    return {"week": week, "team": team, "ranking": rows, "decision": decision}

def _approved_bench(d: Path, roster: dict, team: str) -> list[dict]:
    approved = {(x["team"], x["agent_id"]) for x in read_ledger(d, "approvals")
                if x.get("type") == "bench" and x.get("decision") == "approved"}
    return [b for b in roster.get("bench" if team == "claude" else f"bench_{team}", []) if (team, b["id"]) in approved]

def weekly_league(d: Path, week: str) -> dict:
    """두 팀 현역 전원을 한 줄로 세운 주간 순위와 '통합 꼴등 1명' 퇴출 결정 (weekly.mode = combined_bottom1).
    보류: 팀마다 확정 채점이 그 팀 기대 제출의 min_scored_ratio 미만, 꼴등의 확정 채점이 자기 기대 제출의
    min_scored_ratio 미만, 꼴등 동점. 채점 안 된 추천은 0점이 아니라 제외한다."""
    cfg = load_config(d)
    w = cfg["weekly"]
    nz = lambda v: -1e9 if v is None else v
    key = lambda r: (nz(r["avg"]), nz(r["median"]), nz(r["min"]))
    rows, teams = [], {}
    for team in cfg["teams"]:
        t = weekly(d, week, team, _rows_only=True)["ranking"]
        if not t:
            continue
        sc = sum(r["scored"] for r in t)
        teams[team] = {"scored": sc, "expected": sum(r["expected"] for r in t),
                       "picks": sum(r["picks"] for r in t), "held_or_pending": sum(r["held_or_pending"] for r in t),
                       "avg": round(sum(r["avg"] * r["scored"] for r in t if r["avg"] is not None) / sc, 2) if sc else None}
        rows += [{**r, "team": team, "team_rank": r["rank"]} for r in t]
    rows.sort(key=key, reverse=True)
    for i, r in enumerate(rows, 1):
        r["league_rank"] = i
    decision = {"eliminate": None, "eliminate_team": None, "replacement": None, "hold_reasons": [], "notes": [],
                "bottom": None, "thresholds": {}}
    if rows:
        for team, s_ in teams.items():
            need = _min_needed(s_["expected"], w, "min_total_scored_in_week")
            decision["thresholds"][team] = need
            if s_["scored"] < need:
                decision["hold_reasons"].append(f"{cfg['teams'][team]['label']} 주간 확정 채점 {s_['scored']}건 < {need}건 (기대 {s_['expected']}건 기준, 데이터 부족)")
        bottom = rows[-1]
        decision["bottom"] = {"team": bottom["team"], "agent_id": bottom["agent_id"], "label": bottom["label"]}
        need_a = _min_needed(bottom["expected"], w, "min_scored_for_elimination")
        if bottom["scored"] < need_a:
            decision["hold_reasons"].append(f"꼴등 {bottom['label']} 채점 {bottom['scored']}건 < {need_a}건")
        if w.get("protect_first_week") and bottom["new_this_week"]:
            decision["hold_reasons"].append(f"꼴등 {bottom['label']}는 이번 주 합류 (첫 주 보호)")
        if sum(1 for r in rows if key(r) == key(bottom)) > 1:
            decision["hold_reasons"].append("꼴등 동점 (평균·중앙값·최저점 모두 같음)")
        if not decision["hold_reasons"]:
            decision.update(eliminate=bottom["agent_id"], eliminate_team=bottom["team"])
            bench = _approved_bench(d, load_roster(d), bottom["team"])
            if bench:
                decision["replacement"] = bench[0]["id"]
            else:
                decision["notes"].append("승인된 대기 후보 없음 — 탈락 후 자리 비움 (빈자리는 미제출로 세지 않음)")
    closed = [x for x in read_ledger(d, "weekly_decisions") if x["week"] == week]
    if closed:
        hit = next((x for x in closed if x.get("eliminate")), None)
        decision.update(eliminate=hit["eliminate"] if hit else None, eliminate_team=hit["team"] if hit else None,
                        replacement=hit["replacement"] if hit else None,
                        hold_reasons=closed[0].get("hold_reasons", []), closed_at=closed[0].get("closed_at"))
    return {"week": week, "mode": "combined_bottom1", "ranking": rows, "teams": teams, "decision": decision}

def weekly_market_league(d: Path, week: str, mk: str) -> dict:
    """v2.0 리그별 순위: 그 시장에서 뛴 두 팀 에이전트를 한 줄로 세우고 꼴등 1명을 그 시장에서만 뺀다.
    보류: 팀마다 그 시장 확정 채점 < 그 팀 그 시장 기대 제출의 min_scored_ratio, 꼴등 확정 < 자기 기대의 비율, 꼴등 동점."""
    cfg = load_config(d)
    w = cfg["weekly"]
    nz = lambda v: -1e9 if v is None else v
    key = lambda r: (nz(r["avg"]), nz(r["median"]), nz(r["min"]))
    rows, teams = [], {}
    for team in cfg["teams"]:
        t = [r for r in weekly(d, week, team, _rows_only=True)["ranking"] if r["markets"][mk]["active"]]
        if not t:
            continue
        mr = [{"agent_id": r["agent_id"], "label": r["label"], "version": r["version"], "team": team, "market": mk,
               **{k: r["markets"][mk][k] for k in ("avg", "median", "min", "scored", "expected", "picks", "watch",
                                                   "held_or_pending", "avg_excess", "new_this_week", "sum_raw")}} for r in t]
        sc = sum(r["scored"] for r in mr)
        raw = sum(r["sum_raw"] for r in mr)
        teams[team] = {"scored": sc, "expected": sum(r["expected"] for r in mr), "picks": sum(r["picks"] for r in mr),
                       "held_or_pending": sum(r["held_or_pending"] for r in mr), "sum_raw": raw,
                       "avg": round(raw / sc, 2) if sc else None}
        rows += mr
    rows.sort(key=key, reverse=True)
    for i, r in enumerate(rows, 1):
        r["league_rank"] = i
    decision = {"eliminate": None, "eliminate_team": None, "replacement": None, "hold_reasons": [], "notes": [],
                "bottom": None, "thresholds": {}, "market": mk}
    lab = {"KR": "한국", "US": "미국"}[mk]
    if rows:
        for team, s_ in teams.items():
            need = _min_needed(s_["expected"], w, "min_total_scored_in_week")
            decision["thresholds"][team] = need
            if s_["scored"] < need:
                decision["hold_reasons"].append(f"{lab} 리그 {cfg['teams'][team]['label']} 확정 채점 {s_['scored']}건 < {need}건 (기대 {s_['expected']}건 기준, 데이터 부족)")
        bottom = rows[-1]
        decision["bottom"] = {"team": bottom["team"], "agent_id": bottom["agent_id"], "label": bottom["label"]}
        need_a = _min_needed(bottom["expected"], w, "min_scored_for_elimination")
        if bottom["scored"] < need_a:
            decision["hold_reasons"].append(f"{lab} 리그 꼴등 {bottom['label']} 채점 {bottom['scored']}건 < {need_a}건")
        if w.get("protect_first_week") and bottom["new_this_week"]:
            decision["hold_reasons"].append(f"{lab} 리그 꼴등 {bottom['label']}는 이번 주 합류 (첫 주 보호)")
        if sum(1 for r in rows if key(r) == key(bottom)) > 1:
            decision["hold_reasons"].append(f"{lab} 리그 꼴등 동점 (평균·중앙값·최저점 모두 같음)")
        if not decision["hold_reasons"]:
            decision.update(eliminate=bottom["agent_id"], eliminate_team=bottom["team"])
            bench = bench_available(d, load_roster(d), bottom["team"], mk)
            if bench:
                decision["replacement"] = bench[0]["id"]
            else:
                decision["notes"].append(f"{lab} 리그에 넣을 승인된 대기 후보 없음 — 자리 비움 (빈자리는 미제출로 세지 않음)")
    closed = [x for x in read_ledger(d, "weekly_decisions") if x["week"] == week and x.get("market") == mk]
    if closed:
        hit = next((x for x in closed if x.get("eliminate")), None)
        decision.update(eliminate=hit["eliminate"] if hit else None, eliminate_team=hit["team"] if hit else None,
                        replacement=hit["replacement"] if hit else None,
                        hold_reasons=closed[0].get("hold_reasons", []), closed_at=closed[0].get("closed_at"))
    return {"week": week, "mode": "per_market_bottom1", "market": mk, "ranking": rows, "teams": teams, "decision": decision}

def update_plan(d: Path, week: str) -> dict:
    """규칙 v2.1 주간 지침 업데이트 계획. 그 주 리그별 순위(마감 기록이 있으면 그 값)로 에이전트마다
    frozen(어느 리그 1등) / cooldown(이번 주에 새 버전으로 뛴 경우) / out(두 리그 모두 탈락) / eligible(근거가 있으면 작게 업데이트)."""
    cfg = load_config(d)
    gu = cfg.get("guideline_updates") or {}
    per_market = cfg["weekly"].get("mode") == "per_market_bottom1"
    ranks: dict = {}
    if per_market:
        leagues = {mk: weekly_market_league(d, week, mk) for mk in MARKETS}
    else:
        leagues = {"ALL": weekly_league(d, week)}
    for mk, lg in leagues.items():
        dec = lg["decision"]
        best = lg["ranking"][0] if lg["ranking"] else None
        same = lambda r: best is not None and r["scored"] and (r["avg"], r["median"], r["min"]) == (best["avg"], best["median"], best["min"])
        for r in lg["ranking"]:
            ranks.setdefault((r["team"], r["agent_id"]), {})[mk] = {
                "rank": r["league_rank"], "of": len(lg["ranking"]), "scored": r["scored"], "avg": r["avg"],
                "top": bool(same(r)),                                   # 공동 1등도 모두 1등
                "out": dec.get("eliminate_team") == r["team"] and dec.get("eliminate") == r["agent_id"]}
    picks = read_ledger(d, "picks")
    roster = load_roster(d)
    rows = []
    for (team, aid), rk in sorted(ranks.items()):
        mine = [p for p in picks if p["team"] == team and p["agent_id"] == aid and p.get("agent_version") is not None]
        cur_v = max((int(p["agent_version"]) for p in mine), default=1)
        first_cur = min((p["round_date"] for p in mine if int(p["agent_version"]) == cur_v), default=None)
        v_week = iso_week(date.fromisoformat(first_cur)) if first_cur else None
        top = [mk for mk, x in rk.items() if x["top"]]
        outs = [mk for mk, x in rk.items() if x["out"]]
        # 완전 탈락은 명단 기준: 이번 주까지 두 리그 모두에서 빠졌으면(다른 주에 나뉘어 빠진 경우 포함) out
        mem = next((a for a in roster.get(team, []) if a["id"] == aid), None)
        gone = lambda mk: (mk in outs) or (mem is not None and mstatus(mem, mk).get("status") == "eliminated"
                                          and (mstatus(mem, mk).get("eliminated_week") or "") <= week)
        all_out = all(gone(mk) for mk in MARKETS) if per_market else bool(outs)
        if top:
            st, why = "frozen", f"{'·'.join({'KR': '한국', 'US': '미국', 'ALL': '통합'}[m] for m in top)} 리그 1등 — 이번 주 지침 동결"
        elif all_out:
            st, why = "out", "두 리그 모두 탈락 — 업데이트 없음"
        elif cur_v > 1 and v_week and v_week >= week and int(gu.get("cooldown_weeks", 1)) > 0:
            st, why = "cooldown", f"v{cur_v}로 이번 주({v_week})부터 뜀 — 다음 마감까지 새 버전 표본을 모은다"
        else:
            st, why = "eligible", (f"같은 유형 판단 오류가 pick_id {gu.get('min_evidence_picks', 2)}건 이상일 때만 작게(최대 {gu.get('max_changes', 2)}곳) 업데이트"
                                   + (f" · {'·'.join({'KR': '한국', 'US': '미국'}[m] for m in outs)} 리그에서는 교체됨" if outs else ""))
        rows.append({"team": team, "agent_id": aid, "version": cur_v, "ranks": rk, "status": st, "reason": why})
    order = {"frozen": 0, "eligible": 1, "cooldown": 2, "out": 3}
    rows.sort(key=lambda r: (r["team"], order[r["status"]], r["agent_id"]))
    return {"week": week, "rule": gu.get("rule"), "max_changes": gu.get("max_changes", 2),
            "min_evidence_picks": gu.get("min_evidence_picks", 2), "closed": any(x["week"] == week for x in read_ledger(d, "weekly_decisions")),
            "agents": rows}

def next_week(week: str) -> str:
    y, w = map(int, week.split("-W"))
    return iso_week(date.fromisocalendar(y, w, 1) + timedelta(days=7))

def weekly_close(d: Path, week: str, now: str | None = None) -> list[dict]:
    """주간 마감: 팀별 순위·교체 결정을 weekly_decisions 원장에 고정한다 (이미 마감된 팀·주는 건너뜀).
    이후 명단은 load_roster 가 이 기록을 적용해 계산한다."""
    cfg = load_config(d)
    done = {(x["team"], x["week"]) for x in read_ledger(d, "weekly_decisions")}
    out = []
    if cfg.get("season_start") and week < iso_week(date.fromisoformat(cfg["season_start"])):
        return out                                  # 시즌 시작 전 주는 마감하지 않는다(빈 보류 기록이 원장에 남지 않게)
    if cfg["weekly"].get("mode") == "per_market_bottom1":
        # 두 리그를 같은 명단 기준으로 계산한 뒤 기록한다(먼저 기록한 리그의 교체가 다른 리그 계산에 섞이지 않게)
        plan = [(mk, weekly_market_league(d, week, mk)) for mk in MARKETS
                if not any(x["week"] == week and x.get("market") == mk for x in read_ledger(d, "weekly_decisions"))]
        at = now or datetime.now(KST).isoformat(timespec="seconds")
        for mk, lg in plan:
            if not lg["ranking"]:
                continue
            dec = lg["decision"]
            for team in lg["teams"]:
                mine = dec["eliminate_team"] == team
                rec = {"team": team, "week": week, "market": mk, "effective_week": next_week(week), "mode": "per_market_bottom1",
                       "eliminate": dec["eliminate"] if mine else None, "replacement": dec["replacement"] if mine else None,
                       "hold_reasons": dec["hold_reasons"], "notes": dec["notes"] if mine else [], "league_bottom": dec["bottom"],
                       "ranking": [{k: r[k] for k in ("league_rank", "agent_id", "avg", "avg_excess", "scored", "expected",
                                                       "picks", "watch", "held_or_pending")}
                                   for r in lg["ranking"] if r["team"] == team],
                       "closed_at": at}
                out.append(append(d, "weekly_decisions", rec))
        return out
    if cfg["weekly"].get("mode") == "combined_bottom1":
        if any(wk == week for _, wk in done):
            return out
        lg = weekly_league(d, week)
        if not lg["ranking"]:
            return out
        dec = lg["decision"]
        at = now or datetime.now(KST).isoformat(timespec="seconds")
        for team in lg["teams"]:
            mine = dec["eliminate_team"] == team
            rec = {"team": team, "week": week, "effective_week": next_week(week), "mode": "combined_bottom1",
                   "eliminate": dec["eliminate"] if mine else None, "replacement": dec["replacement"] if mine else None,
                   "hold_reasons": dec["hold_reasons"], "notes": dec["notes"] if mine else [],
                   "league_bottom": dec["bottom"],
                   "ranking": [{k: r[k] for k in ("league_rank", "team_rank", "agent_id", "avg", "avg_excess", "scored",
                                                   "expected", "picks", "held_or_pending", "submit_rate", "void")}
                               for r in lg["ranking"] if r["team"] == team],
                   "closed_at": at}
            out.append(append(d, "weekly_decisions", rec))
        return out
    for team in cfg["teams"]:
        if (team, week) in done:
            continue
        w = weekly(d, week, team)
        if not w["ranking"]:
            continue
        rec = {"team": team, "week": week, "effective_week": next_week(week),
               "eliminate": w["decision"]["eliminate"], "replacement": w["decision"]["replacement"],
               "hold_reasons": w["decision"]["hold_reasons"], "notes": w["decision"].get("notes", []),
               "ranking": [{k: r[k] for k in ("rank", "agent_id", "avg", "avg_excess", "scored", "expected", "submit_rate", "void")}
                           for r in w["ranking"]],
               "closed_at": now or datetime.now(KST).isoformat(timespec="seconds")}
        out.append(append(d, "weekly_decisions", rec))
    return out

# ───────────────────────── 지침 버전 / 주간 복기 자료 ─────────────────────────
# Claude 팀 지침: 현재 파일 .claude/agents/<id>.md, 버전 보관본 league/agents/claude/<id>/v<N>.md
# guidelines 원장: 버전별 해시와 적용 시작 라운드. 승인 = 해당 버전이 들어간 PR 머지.

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def guideline_paths(agent_id: str, version: int, root: Path = ROOT) -> tuple[Path, Path]:
    return root / ".claude" / "agents" / f"{agent_id}.md", root / "league" / "agents" / "claude" / agent_id / f"v{version}.md"

def guideline_check(d: Path, round_date: date | None = None, root: Path = ROOT, register: bool = True) -> list[dict]:
    """Claude 팀 현역·대기 에이전트마다: 현재 지침 파일 == roster 버전의 보관본 인지 확인.
    - 같고 원장에 그 버전 기록이 없으면 (승인된 새 버전) 적용 시작 라운드와 함께 기록한다.
    - 다르면 '승인되지 않은 수정'으로 보고한다 (라운드를 진행하지 말 것)."""
    roster = load_roster(d)
    seen = {(g["agent_id"], g["version"]): g for g in read_ledger(d, "guidelines")}
    out = []
    approved = {x["agent_id"] for x in read_ledger(d, "approvals")
                if x.get("team") == "claude" and x.get("type") == "bench" and x.get("decision") == "approved"}
    for a in roster.get("claude", []) + [b for b in roster.get("bench", []) if b["id"] in approved]:
        if a.get("status") == "eliminated":
            continue
        latest = int(a.get("version", 1))
        v = (version_for_round(a, round_date.isoformat()) or latest) if round_date else latest
        cur, arch = guideline_paths(a["id"], v, root)
        row = {"agent_id": a["id"], "version": v}
        if v < latest:   # 명단에 새 버전이 있지만 이 라운드에는 아직 적용 전: 보관본만 확인하고 기록하지 않는다
            _, new_arch = guideline_paths(a["id"], latest, root)
            if not arch.exists() or not cur.exists() or not new_arch.exists():
                row.update(status="missing", detail=f"{'현재 파일' if not cur.exists() else f'v{v} 보관본' if not arch.exists() else f'v{latest} 보관본'} 없음")
            elif (a["id"], v) in seen and seen[(a["id"], v)].get("sha256") not in (None, _sha(arch)):
                row.update(status="unapproved_edit", detail=f"v{v} 보관본이 원장에 기록된 해시와 다름 — 승인 안 된 수정")
            elif _sha(cur) != _sha(new_arch):
                row.update(status="unapproved_edit", detail=f"{cur.relative_to(root)} 가 v{latest} 보관본과 다름 — 승인 안 된 수정")
            else:
                row.update(status="not_yet", detail=f"이 라운드는 v{v}(보관본 {arch.relative_to(root)}) — v{latest}는 적용 전")
            out.append(row)
            continue
        if not cur.exists() or not arch.exists():
            row.update(status="missing", detail=f"{'현재 파일' if not cur.exists() else '보관본'} 없음")
        elif _sha(cur) != _sha(arch):
            row.update(status="unapproved_edit", detail=f"{cur.relative_to(root)} 가 v{v} 보관본과 다름 — 승인 안 된 수정")
        elif (a["id"], v) in seen and seen[(a["id"], v)].get("sha256") not in (None, _sha(arch)):
            row.update(status="unapproved_edit", detail=f"v{v} 보관본이 원장에 기록된 해시와 다름 — 승인 안 된 수정")
        elif (a["id"], v) in seen:
            row.update(status="ok", effective_round=seen[(a["id"], v)].get("effective_round"))
        else:
            row.update(status="registered" if register else "new_version")
            if register:
                append(d, "guidelines", {"team": "claude", "agent_id": a["id"], "version": v, "sha256": _sha(arch),
                                         "path": str(arch.relative_to(root)),
                                         "effective_round": round_date.isoformat() if round_date else None,
                                         "registered_at": datetime.now(KST).isoformat(timespec="seconds")})
        out.append(row)
    return out

def review_data(d: Path, week: str, team: str = "claude") -> dict:
    """주간 복기용 자료: 에이전트별 추천·결과(확정/잠정 구분)·근거 요약."""
    w = weekly(d, week, team)
    scores = latest_scores(d)
    picks = [p for p in read_ledger(d, "picks") if p["team"] == team and iso_week(date.fromisoformat(p["round_date"])) == week]
    agents = []
    for r in w["ranking"]:
        rows = []
        for p in sorted((p for p in picks if p["agent_id"] == r["agent_id"]), key=lambda x: (x["round_date"], x["market"])):
            s_ = scores.get(p["pick_id"], {})
            rows.append({"pick_id": p["pick_id"], "round_date": p["round_date"], "market": p["market"], "ticker": p["ticker"],
                         "name": p["name"], "agent_version": p.get("agent_version"),
                         "status": s_.get("status", "pending"), "score": s_.get("score"),
                         "score_price_only": s_.get("score_price_only"), "score_excess": s_.get("score_excess"),
                         "benchmark_return": s_.get("benchmark_return"), "reason": s_.get("reason"),
                         "rationale": p.get("rationale"), "risks": p.get("risks"),
                         "sources": [x.get("url") for x in p.get("sources", [])]})
        agents.append({**{k: r[k] for k in ("rank", "agent_id", "label", "version", "avg", "avg_excess", "scored", "expected",
                                            "submit_rate", "held_or_pending", "void", "markets")},
                       "picks": rows, "provisional_or_pending": sum(1 for x in rows if x["status"] != "final")})
    plan = {r["agent_id"]: {k: r[k] for k in ("status", "reason", "ranks")} for r in update_plan(d, week)["agents"] if r["team"] == team}
    for a_ in agents:
        a_["update_plan"] = plan.get(a_["agent_id"])
    return {"week": week, "team": team, "decision": w["decision"], "agents": agents,
            "caution": "한 주 표본(에이전트당 최대 10건)은 운의 영향이 크다. 결과 하나에 맞춘 지침 변경을 피하고, 반복되는 판단 오류만 다룬다."}

def record_outage(d: Path, team: str, round_date: str, reason: str, agent_id: str | None = None,
                  kind: str = "operator", now: str | None = None) -> dict:
    """운영 장애로 인한 미제출 기록 (두 팀 동일 기준: 미제출로 집계, 소급 제출 없음, 사유만 남겨 화면에 표시).
    kind: operator(운영 측 — Claude 사용 한도, GitHub 장애 등) / team(팀 측)."""
    date.fromisoformat(round_date)
    if team not in load_config(d)["teams"]:
        raise ValueError(f"알 수 없는 팀: {team}")
    return append(d, "outages", {"team": team, "round_date": round_date, "agent_id": agent_id, "reason": reason,
                                 "kind": kind, "counted_as": "missed",
                                 "recorded_at": now or datetime.now(KST).isoformat(timespec="seconds")})

# ───────────────────────── 팀 비교 ─────────────────────────

def team_summary(d: Path) -> dict:
    scores = latest_scores(d)
    out = {}
    for p in read_ledger(d, "picks"):
        s = scores.get(p["pick_id"])
        t = out.setdefault(p["team"], {"daily": {}, "markets": {"KR": [], "US": []}, "all": [],
                                       "excess": {"KR": [], "US": []}})
        if s and s["status"] == "final":
            t["daily"].setdefault(p["round_date"], []).append(s["score"])
            t["markets"][p["market"]].append(s["score"])
            t["all"].append(s["score"])
            if s.get("score_excess") is not None:
                t["excess"][p["market"]].append(s["score_excess"])
    res = {}
    for team, t in out.items():
        days = sorted(t["daily"])
        cum, series, seen = 0.0, [], []
        for dd in days:
            daysum = round(sum(t["daily"][dd]), 2); cum = round(cum + daysum, 2)
            seen += t["daily"][dd]
            series.append({"date": dd, "sum": daysum, "cumulative": cum, "n": len(t["daily"][dd]),
                           "avg": _avg(t["daily"][dd]), "cum_avg": _avg(seen), "cum_n": len(seen)})
        res[team] = {"cumulative": cum, "avg": _avg(t["all"]), "scored": len(t["all"]), "series": series,
                     "avg_excess": _avg(t["excess"]["KR"] + t["excess"]["US"]),
                     "markets": {m: {"avg": _avg(v), "scored": len(v), "sum": round(sum(v), 2),
                                     "avg_excess": _avg(t["excess"][m])}
                                 for m, v in t["markets"].items()}}
    return res

# ───────────────────────── 추천 확정 / CSV 가져오기 ─────────────────────────

def lock_deadline(round_date: date, cfg: dict) -> datetime:
    hh, mm = map(int, cfg["lock_deadline"].split(":"))
    return datetime(round_date.year, round_date.month, round_date.day, hh, mm, tzinfo=KST)

def universe_for(d: Path, round_date: date) -> dict:
    """라운드 날짜에 적용되는 대상 목록: <d>/universe/<적용일>.json 중 적용일 ≤ 라운드 날짜인 최신 판 → 없으면 universe.json."""
    for base in (d, ROOT / "league"):
        ud = base / "universe"
        if ud.exists():
            cands = sorted(p for p in ud.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem) and p.stem <= round_date.isoformat())
            if cands:
                return json.loads(cands[-1].read_text())
        if (base / "universe.json").exists():
            return json.loads((base / "universe.json").read_text())
    return {}

def version_for_round(m: dict, round_date: str) -> int | None:
    """그 라운드에 써야 하는 지침 버전 (규칙 v2.1: 07:05 전 승인은 그날부터, 07:05 이후 승인은 다음 라운드부터).
    명단 항목의 versions: [{"version": 2, "from_round": "YYYY-MM-DD"}] 가 있으면 그 라운드에 시작된 가장 높은 버전,
    시작 전이면 그 아래 버전. 기록이 없으면 명단의 version."""
    hist = sorted((int(x["version"]), x["from_round"]) for x in (m.get("versions") or []) if x.get("from_round"))
    if not hist:
        return int(m["version"]) if m.get("version") is not None else None
    started = [v for v, fr in hist if fr <= round_date]
    return max(started) if started else min(v for v, _ in hist) - 1 or 1

def validate_pick(rec: dict, d: Path, cfg: dict, existing: list[dict]) -> list[str]:
    errs = []
    uni = universe_for(d, date.fromisoformat(rec["round_date"]))
    rd = date.fromisoformat(rec["round_date"])
    wcfg = cfg.get("watch") or {}
    if rec["market"] not in ("KR", "US"):
        errs.append("market은 KR 또는 US")
    elif is_watch(rec, cfg):
        if not wcfg.get("from") or rd < date.fromisoformat(wcfg["from"]):
            errs.append(f"관망은 {wcfg.get('from') or '(미정)'} 라운드부터 낼 수 있음")
        if not round_sessions(rec["market"], rd, cfg):
            errs.append(f"{rec['round_date']}은 {rec['market']} 휴장일 — 이 시장 제출 불가")
        if not str(rec.get("rationale") or "").strip():
            errs.append("관망도 근거(rationale)가 필요함")
        wk = iso_week(rd)
        used = [p for p in existing if p["team"] == rec["team"] and p["agent_id"] == rec["agent_id"]
                and is_watch(p, cfg) and iso_week(date.fromisoformat(p["round_date"])) == wk]
        per_m = wcfg.get("max_per_week_per_market")
        if per_m is not None:                       # v2.0: 리그(시장)별 주 N회
            used_m = [p for p in used if p["market"] == rec["market"]]
            if len(used_m) + 1 > int(per_m):
                errs.append(f"{rec['agent_id']} {rec['market']} 관망은 주 {per_m}회까지 ({wk} 이미 {len(used_m)}회)")
        else:
            cap = int(wcfg.get("max_per_week", 2))
            if len(used) + 1 > cap:
                errs.append(f"{rec['agent_id']} 관망은 주 {cap}회까지 ({wk} 이미 {len(used)}회)")
    elif rec["ticker"] not in uni[rec["market"]]:
        errs.append(f"대상 범위 밖 종목: {rec['market']} {rec['ticker']}")
    elif not round_sessions(rec["market"], rd, cfg):
        errs.append(f"{rec['round_date']}은 {rec['market']} 휴장일 — 이 시장 종목 선택 불가")
    locked = datetime.fromisoformat(rec["locked_at"])
    if locked.tzinfo is None:
        errs.append("locked_at에 시간대 필요 (예: +09:00)")
    elif locked > lock_deadline(rd, cfg):
        errs.append(f"마감({cfg['lock_deadline']} KST) 이후 확정: {rec['locked_at']}")
    # 지침 버전·현역 여부: 팀 명단이 있을 때만 검사 (연습용 sandbox 등은 건너뜀)
    team_roster = load_roster(d).get(rec["team"])
    if team_roster:
        wk = iso_week(rd)
        m = next((x for x in team_roster if x["id"] == rec["agent_id"]), None)
        if not m:
            errs.append(f"{rec['agent_id']}는 {rec['team']} 팀 명단에 없음")
        else:
            ms = mstatus(m, rec["market"]) if rec["market"] in MARKETS else {}
            lab = {"KR": "한국", "US": "미국"}.get(rec["market"], rec["market"])
            if ms.get("status") == "bench":
                errs.append(f"{rec['agent_id']}는 {lab} 리그 참가 전 — 이 시장 제출 불가")
            elif ms.get("status") == "eliminated" and (ms.get("eliminated_week") or "") < wk:
                errs.append(f"{rec['agent_id']}는 {ms.get('eliminated_week')}에 {lab} 리그에서 탈락 — 이 시장 제출 불가")
            if ms.get("joined_week") and ms["joined_week"] > wk:
                errs.append(f"{rec['agent_id']}는 {ms['joined_week']}부터 {lab} 리그 참가")
            need_v = version_for_round(m, rec["round_date"])
            if rec.get("agent_version") is not None and need_v is not None and int(rec["agent_version"]) != need_v:
                errs.append(f"{rec['agent_id']} 지침 버전 불일치: 제출 v{rec['agent_version']} / {rec['round_date']} 라운드 승인 v{need_v}")
    same = [p for p in existing if p["team"] == rec["team"] and p["round_date"] == rec["round_date"]]
    if any(p["agent_id"] == rec["agent_id"] and p["market"] == rec["market"] for p in same):
        errs.append(f"{rec['agent_id']}는 이 라운드 {rec['market']} 종목을 이미 추천함")
    # 인원은 시장(리그)별로 센다(v2.0): 한 리그에서만 빠진 에이전트와 그 리그에 합류한 후보가 같은 라운드에 함께 낼 수 있다
    same_m = [p for p in same if p["market"] == rec["market"]]
    if len({p["agent_id"] for p in same_m} | {rec["agent_id"]}) > cfg["agents_per_team"]:
        errs.append(f"{rec['market']} 팀 인원 {cfg['agents_per_team']}명 초과")
    return errs

def open_markets(round_date: date, cfg: dict) -> set[str]:
    return {m for m in ("KR", "US") if round_sessions(m, round_date, cfg)}

def make_pick(team, agent_id, agent_version, round_date, market, ticker, name, locked_at,
              rationale, risks, sources, cfg, snapshot_sha256=None, agent_label=None) -> dict:
    rd = date.fromisoformat(round_date)
    rs = round_sessions(market, rd, cfg)
    return {"pick_id": f"{round_date}-{team}-{agent_id}-{market}", "team": team, "agent_id": agent_id,
            "agent_version": agent_version, "agent_label": agent_label, "round_date": round_date,
            "market": market, "ticker": ticker, "name": name, "locked_at": locked_at,
            "base_session": rs[0].isoformat() if rs else None, "eval_session": rs[1].isoformat() if rs else None,
            "rationale": rationale, "risks": risks, "sources": sources, "snapshot_sha256": snapshot_sha256}

def submit_pick(d: Path, rec: dict) -> dict:
    cfg = load_config(d)
    errs = validate_pick(rec, d, cfg, read_ledger(d, "picks"))
    if errs:
        raise ValueError("; ".join(errs))
    return append(d, "picks", rec)

def import_csv(d: Path, path: Path, team: str, dry_run: bool = False) -> tuple[list, list]:
    """CSV 열: round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources
    risks는 ' | '로 구분, sources는 'url|기준일;url|기준일'. 가격은 입력받지 않는다 (공통 가격 원장 사용)."""
    cfg = load_config(d)
    ok, bad = [], []
    existing = read_ledger(d, "picks")
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), 2):
            srcs = [dict(zip(("url", "as_of", "retrieved_at"), s.split("|"))) for s in (row.get("sources") or "").split(";") if s.strip()]
            ver = (row.get("agent_version") or "").strip()
            rec = make_pick(team, row["agent_id"].strip(), int(ver) if ver.isdigit() else None, row["round_date"].strip(), row["market"].strip().upper(),
                            row["ticker"].strip(), row.get("name", "").strip(), row["locked_at"].strip(),
                            row.get("rationale", ""), [r.strip() for r in (row.get("risks") or "").split("|") if r.strip()],
                            srcs, cfg)
            if is_watch(rec, cfg):
                rec["ticker"] = (cfg.get("watch") or {}).get("ticker", "WATCH")
                rec["name"] = (cfg.get("watch") or {}).get("name", "관망")
            errs = validate_pick(rec, d, cfg, existing + ok)
            if not srcs and not is_watch(rec, cfg):
                errs.append("데이터 출처(sources) 없음")
            for sx in srcs:
                if sx.get("retrieved_at"):
                    try:
                        ra = datetime.fromisoformat(sx["retrieved_at"])
                        if ra.tzinfo is None or ra > lock_deadline(date.fromisoformat(rec["round_date"]), cfg):
                            errs.append(f"출처 확보 시각이 마감 이후이거나 시간대 없음: {sx['retrieved_at']}")
                    except ValueError:
                        errs.append(f"출처 확보 시각 형식 오류: {sx['retrieved_at']}")
            if not (row.get("rationale") or "").strip():
                errs.append("선정 근거(rationale) 없음")
            if not rec["risks"] and not is_watch(rec, cfg):      # 관망은 위험 요인 선택
                errs.append("위험 요인(risks) 없음")
            if not ver.isdigit():
                errs.append("agent_version 없음 (정수)")
            (bad if errs else ok).append({"line": i, "pick": rec, "errors": errs} if errs else rec)
    # 파일 단위 검사: 에이전트마다 그날 열린 시장(KR·US)에서 각 1종목 필수
    rows = ok + [b["pick"] for b in bad]
    team_roster = {a["id"]: a for a in load_roster(d).get(team, [])}
    for (agent, rd) in sorted({(r["agent_id"], r["round_date"]) for r in rows}):
        need = open_markets(date.fromisoformat(rd), cfg)
        if agent in team_roster:                    # v2.0: 그 리그에서 뛰는 시장만 필수
            wk = iso_week(date.fromisoformat(rd))
            need = {mk for mk in need if active_in(team_roster[agent], mk, wk) and (mstatus(team_roster[agent], mk).get("status") == "active")}
        have = {r["market"] for r in rows if r["agent_id"] == agent and r["round_date"] == rd}
        if need - have:
            bad.append({"line": 0, "pick": {"agent_id": agent, "round_date": rd},
                        "errors": [f"{agent}: {rd}에 열린 시장 {'·'.join(sorted(need))} 중 {'·'.join(sorted(need - have))} 종목 누락"]})
    if not dry_run and not bad:
        for rec in ok:
            append(d, "picks", rec)
    return ok, bad

CSV_COLUMNS = ["round_date", "agent_id", "agent_version", "market", "ticker", "name", "locked_at",
               "rationale", "risks", "sources"]

def make_csv(picks: list[dict], round_date: str, out: Path) -> Path:
    """확정 추천(JSON 목록)을 제출 CSV로 변환. 각 항목:
    {agent_id, agent_version, market, ticker, name, locked_at, rationale, risks:[...], sources:[{url, as_of, retrieved_at?}]}"""
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(CSV_COLUMNS)
        for p in sorted(picks, key=lambda x: (x["agent_id"], x["market"])):
            srcs = ";".join("|".join(x for x in (s_["url"], s_["as_of"], s_.get("retrieved_at")) if x) for s_ in p["sources"])
            w.writerow([round_date, p["agent_id"], p["agent_version"], p["market"], str(p["ticker"]), p["name"],
                        p["locked_at"], " ".join(str(p["rationale"]).split()), " | ".join(p["risks"]), srcs])
    return out

# ───────────────────────── 시간 정합성 / 일정 안내 ─────────────────────────

def _kst(ts) -> datetime:
    return ts.to_pydatetime().astimezone(KST)

def timing(market: str, round_date: date, cfg: dict) -> dict | None:
    """라운드 D의 시장별 기준·평가 세션과 실제 시각(KST). 기준 종가 < 마감 < 평가 세션 개장 이어야 한다.
    시각은 거래소 달력의 정규장 기준 (조기 폐장·지연 개장 반영). 시간외·대체거래소(NXT) 가격은 쓰지 않는다."""
    rs = round_sessions(market, round_date, cfg)
    if not rs:
        return None
    cal = _cal(market)
    base_s, eval_s = rs
    base_close = _kst(cal.session_close(base_s.isoformat()))
    eval_open = _kst(cal.session_open(eval_s.isoformat()))
    eval_close = _kst(cal.session_close(eval_s.isoformat()))
    dl = lock_deadline(round_date, cfg)
    return {"market": market, "round_date": round_date.isoformat(),
            "base_session": base_s.isoformat(), "base_close_kst": base_close.isoformat(timespec="minutes"),
            "deadline_kst": dl.isoformat(timespec="minutes"),
            "eval_session": eval_s.isoformat(), "eval_open_kst": eval_open.isoformat(timespec="minutes"),
            "eval_close_kst": eval_close.isoformat(timespec="minutes"),
            "ok": base_close < dl < eval_open}

def schedule(start: date, end: date, cfg: dict) -> list[dict]:
    rows, d = [], start
    while d <= end:
        if d.weekday() < 5:
            kr, us = timing("KR", d, cfg), timing("US", d, cfg)
            rows.append({"round_date": d.isoformat(), "weekday": "월화수목금"[d.weekday()], "KR": kr, "US": us})
        d += timedelta(days=1)
    return rows

# ───────────────────────── 제출 영수증 (GitHub 서버 push 시각 기준) ─────────────────────────
# 정시 판정은 커밋 작성 시각(수정 가능)이 아니라 push 이벤트 페이로드의 repository.pushed_at
# (GitHub 서버가 기록한 push 시각)으로 한다. 워크플로 실행 생성 시각(서버)도 함께 남긴다.

import re, subprocess
SUBMISSION_RE = re.compile(r"^league/imports/([a-z0-9_-]+)/(\d{4}-\d{2}-\d{2})\.csv$")
COMMIT_RE = re.compile(r"^league/imports/([a-z0-9_-]+)/(\d{4}-\d{2}-\d{2})\.sha256$")
SHA_RE = re.compile(r"^\s*([0-9a-f]{64})\b")

def commit_reveal_applies(round_date: str, cfg: dict) -> bool:
    """지문 먼저·원본 나중 제출 방식이 이 라운드에 적용되는가 (config.commit_reveal.from 이후 라운드)."""
    cr = cfg.get("commit_reveal") or {}
    return bool(cr.get("from")) and round_date >= cr["from"]

def reveal_deadline(round_date: date, cfg: dict) -> datetime:
    hh, mm = map(int, (cfg.get("commit_reveal") or {}).get("reveal_deadline", "12:00").split(":"))
    return datetime(round_date.year, round_date.month, round_date.day, hh, mm, tzinfo=KST)

def write_commitment(csv_path: Path) -> Path:
    """제출 CSV의 원본 바이트 sha256을 같은 폴더의 <날짜>.sha256 에 쓴다. 이 파일만 마감 전에 push한다."""
    sha = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()
    out = Path(csv_path).with_suffix(".sha256")
    out.write_text(f"{sha}  {Path(csv_path).name}\n")
    return out
ZERO_SHA = "0" * 40

def _git(*args, cwd=ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout

def changed_submission_files(event: dict, cwd=ROOT) -> list[str]:
    before, after = event.get("before", ZERO_SHA), event["after"]
    if before and before != ZERO_SHA:
        try:
            files = _git("diff", "--name-only", "--diff-filter=AM", before, after, cwd=cwd).split()
        except subprocess.CalledProcessError:
            files = []
    else:
        files = []
    if not files:
        for c in event.get("commits", []):
            files += c.get("added", []) + c.get("modified", [])
    return sorted({f for f in files if SUBMISSION_RE.match(f) or COMMIT_RE.match(f)},
                  key=lambda f: (0 if f.endswith(".sha256") else 1, f))     # 같은 push면 지문 먼저 처리

def ledger_dir_for(team: str, cwd=ROOT) -> Path:
    """sandbox 및 sandbox-<팀> 은 시험용 원장(league/sandbox)에 기록해 실제 원장을 오염시키지 않는다.
    팀별 연습 경로(예: league/imports/sandbox-claude/)를 쓰면 다른 연습 제출과 섞이지 않는다."""
    return Path(cwd) / "league" / ("sandbox" if team == "sandbox" or team.startswith("sandbox-") else "")

class CommitmentPending(Exception):
    """원본을 판정하려는데, 같은 라운드 지문 파일은 저장소에 있으나 지문 영수증이 아직 원장에 없다.
    (지문과 원본을 연달아 push해 원본 작업이 먼저 돈 경우) 늦음으로 굳히지 않고 잠시 뒤 최신 원장에서 다시 처리한다."""

def _commitment_file_pending(event, team, rd, d, cwd) -> bool:
    path = f"league/imports/{team}/{rd}.sha256"
    if subprocess.run(["git", "cat-file", "-e", f"{event['after']}:{path}"], cwd=cwd, capture_output=True).returncode:
        return False                                   # 지문 파일 자체가 없음 → 정말 지문 없이 낸 것
    return not any(s.get("kind") == "commitment" and s.get("path") == path for s in read_ledger(d, "submissions"))

def process_push(event: dict, run_id: str = "", run_url: str = "", run_created_at: str | None = None,
                 cwd=ROOT) -> list[dict]:
    pushed_ts = (event.get("repository") or {}).get("pushed_at")
    pushed_at = datetime.fromtimestamp(int(pushed_ts), KST) if pushed_ts else None
    run_at = datetime.fromisoformat(run_created_at.replace("Z", "+00:00")).astimezone(KST) if run_created_at else None
    # 판정 시각: push 서버 시각. 없으면 워크플로 생성 시각(항상 push 이후라 보수적)
    judged_at, judged_src = (pushed_at, "push_event.repository.pushed_at") if pushed_at else (run_at, "workflow_run.created_at")
    if pushed_at and event.get("judged_by"):         # 전용 제출 저장소에서 가져온 push: 그 저장소의 서버 push 기록 시각
        judged_src = event["judged_by"]
    receipts = []
    for path in changed_submission_files(event, cwd):
        # 같은 push(커밋)·같은 파일의 영수증이 이미 있으면 다시 만들지 않는다(재실행·충돌 재처리 때 중복 방지)
        m_ = (COMMIT_RE.match(path) or SUBMISSION_RE.match(path))
        if m_ and any(x.get("path") == path and x.get("commit") == event["after"]
                      for x in read_ledger(ledger_dir_for(m_.group(1), cwd), "submissions")):
            continue
        if COMMIT_RE.match(path):
            receipts.append(_process_commitment(event, path, pushed_at, judged_at, judged_src, run_id, run_url, run_at, cwd))
            continue
        team, rd = SUBMISSION_RE.match(path).groups()
        d = ledger_dir_for(team, cwd)
        cfg = load_config(d)
        # 원본 바이트 그대로 해시 (텍스트 모드로 읽으면 CRLF가 LF로 바뀌어 제출 파일과 해시가 달라진다)
        raw = subprocess.run(["git", "show", f"{event['after']}:{path}"], cwd=cwd, check=True, capture_output=True).stdout
        sha = hashlib.sha256(raw).hexdigest()
        content = raw.decode("utf-8-sig", "replace")
        deadline = lock_deadline(date.fromisoformat(rd), cfg)
        rec = {"team": team, "round_date": rd, "path": path, "commit": event["after"], "before": event.get("before"),
               "ref": event.get("ref"), "pusher": (event.get("pusher") or {}).get("name"),
               "csv_sha256": sha, "pushed_at": pushed_at.isoformat() if pushed_at else None,
               "run_id": str(run_id), "run_url": run_url, "run_created_at": run_at.isoformat() if run_at else None,
               "judged_by": judged_src, "deadline": deadline.isoformat(), "errors": [], "imported": 0}
        if event.get("source"):
            rec["source"] = event["source"]
        subs = [s for s in read_ledger(d, "submissions") if s["team"] == team and s["round_date"] == rd]
        prior = [s for s in subs if s["status"] == "accepted"]
        cr = commit_reveal_applies(rd, cfg)
        commitment = next((s for s in subs if s["status"] == "committed"), None) if cr else None
        lock_time = judged_at            # 추천이 '확정'된 것으로 보는 시각: 보통 push 시각, 지문 방식이면 지문 push 시각
        if cr:
            rec["kind"] = "reveal"
        if judged_at is None:
            rec.update(status="rejected", errors=["서버 push 시각을 확인할 수 없음"])
        elif prior:
            rec.update(status="rejected", errors=[f"이미 접수된 제출이 있음 ({prior[0]['commit'][:7]}) — 확정 후 변경 불가"])
        elif cr and commitment and sha != commitment["committed_sha256"]:
            rec.update(status="rejected", errors=[f"원본 해시 {sha[:12]}가 마감 전 지문 {commitment['committed_sha256'][:12]}와 다름 — "
                                                   f"지문과 같은 파일을 다시 push하면 됨 (공개 마감 {reveal_deadline(date.fromisoformat(rd), cfg).strftime('%H:%M')} KST)"])
        elif cr and commitment and judged_at > reveal_deadline(date.fromisoformat(rd), cfg):
            rec.update(status="rejected", errors=[f"원본 공개 마감 {reveal_deadline(date.fromisoformat(rd), cfg).strftime('%H:%M')} KST 경과"])
        elif judged_at > deadline and cr and not commitment and _commitment_file_pending(event, team, rd, d, cwd):
            raise CommitmentPending(f"{team} {rd}: 지문 파일은 있으나 지문 영수증이 아직 없음 — 잠시 뒤 다시 처리")
        elif judged_at > deadline and not (cr and commitment):
            why = " (마감 전 지문 제출 없음)" if cr else ""
            rec.update(status="late", errors=[f"마감 {cfg['lock_deadline']} KST 이후 push ({judged_at.isoformat(timespec='seconds')}){why}"])
        else:
            if cr and commitment:
                lock_time = datetime.fromisoformat(commitment["judged_at"])
                rec.update(commitment_commit=commitment["commit"], commitment_pushed_at=commitment["judged_at"])
                if judged_at <= deadline and path in (event.get("sealed_paths") or []):
                    rec["sealed"] = True       # 비공개 전용 저장소에 마감 전 보관 → 마감 뒤에만 메인에 반입(상대가 볼 수 없었음)
                elif judged_at <= deadline:
                    rec["early_reveal"] = True
            elif cr:
                if path in (event.get("sealed_paths") or []):
                    rec["sealed"] = True
                else:
                    rec["early_reveal"] = True     # 마감 전에 원본을 바로 올림: 접수는 하되 상대가 볼 수 있었음을 기록
            tmp = d / ".tmp_submission.csv"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(raw)
            try:
                ok, bad = import_csv(d, tmp, team, dry_run=True)
                errs = [f"{b['line']}행: {'; '.join(b['errors'])}" for b in bad]
                errs += [f"round_date {r['round_date']}가 파일명 {rd}와 다름" for r in ok if r["round_date"] != rd]
                errs += [f"locked_at {r['locked_at']}가 서버 push 시각보다 늦음" for r in ok
                         if datetime.fromisoformat(r["locked_at"]) > lock_time]
                if errs or not ok:
                    rec.update(status="rejected", errors=errs or ["추천 없음"])
                else:
                    meta = {"commit": event["after"], "csv_sha256": sha, "pushed_at": rec["pushed_at"], "run_id": str(run_id)}
                    if rec.get("commitment_commit"):
                        meta.update(commitment_commit=rec["commitment_commit"], committed_at=rec["commitment_pushed_at"])
                    for r in ok:
                        append(d, "picks", {**r, "submission": meta})
                    rec.update(status="accepted", imported=len(ok))
            finally:
                tmp.unlink(missing_ok=True)
        receipts.append(append(d, "submissions", rec))
    return receipts

def _process_commitment(event, path, pushed_at, judged_at, judged_src, run_id, run_url, run_at, cwd) -> dict:
    """마감 전 지문(<날짜>.sha256) push. 첫 유효 지문만 인정하고, 원본은 마감 뒤 공개 마감까지 올린다."""
    team, rd = COMMIT_RE.match(path).groups()
    d = ledger_dir_for(team, cwd)
    cfg = load_config(d)
    raw = subprocess.run(["git", "show", f"{event['after']}:{path}"], cwd=cwd, check=True, capture_output=True).stdout
    m = SHA_RE.match(raw.decode("utf-8-sig", "replace").lower())
    deadline = lock_deadline(date.fromisoformat(rd), cfg)
    rec = {"team": team, "round_date": rd, "path": path, "kind": "commitment", "commit": event["after"],
           "before": event.get("before"), "ref": event.get("ref"), "pusher": (event.get("pusher") or {}).get("name"),
           "committed_sha256": m.group(1) if m else None, "csv_sha256": None,
           "pushed_at": pushed_at.isoformat() if pushed_at else None,
           "judged_at": judged_at.isoformat() if judged_at else None,
           "run_id": str(run_id), "run_url": run_url, "run_created_at": run_at.isoformat() if run_at else None,
           "judged_by": judged_src, "deadline": deadline.isoformat(), "errors": [], "imported": 0}
    if event.get("source"):
        rec["source"] = event["source"]
    subs = [s for s in read_ledger(d, "submissions") if s["team"] == team and s["round_date"] == rd]
    if not commit_reveal_applies(rd, cfg):
        rec.update(status="rejected", errors=["이 라운드는 지문 제출 대상이 아님 — CSV를 마감 전에 push"])
    elif judged_at is None:
        rec.update(status="rejected", errors=["서버 push 시각을 확인할 수 없음"])
    elif not m:
        rec.update(status="rejected", errors=["지문 파일 첫 줄이 64자리 sha256(소문자 16진수)이 아님"])
    elif any(s["status"] in ("committed", "accepted") for s in subs):
        rec.update(status="rejected", errors=["이미 지문 또는 접수된 제출이 있음 — 첫 지문만 유효"])
    elif judged_at > deadline:
        rec.update(status="late", errors=[f"마감 {cfg['lock_deadline']} KST 이후 지문 push ({judged_at.isoformat(timespec='seconds')})"])
    else:
        rec["status"] = "committed"
    return append(d, "submissions", rec)

def append_only_violations(base: str, head: str, cwd=ROOT) -> list[str]:
    """base→head 사이 원장(jsonl) 변경이 '끝에 줄 추가'뿐인지 검사. 기존 줄 수정·삭제·파일 삭제를 잡는다."""
    errs = []
    changed = _git("diff", "--name-status", base, head, "--", "league", cwd=cwd).splitlines()
    for line in changed:
        st, *paths = line.split("\t")
        path = paths[-1]
        if not re.search(r"/ledger/[^/]+\.jsonl$", path) or path.startswith("league/sample/"):
            continue      # 예시 데이터는 매번 새로 생성하므로 제외
        if st.startswith("D"):
            errs.append(f"{path}: 원장 파일 삭제")
            continue
        if st.startswith("A"):
            continue
        old = _git("show", f"{base}:{path}", cwd=cwd)
        new = _git("show", f"{head}:{path}", cwd=cwd)
        if not new.startswith(old):
            errs.append(f"{path}: 기존 줄이 수정되거나 삭제됨 (끝에 추가만 허용)")
    return errs

def readiness(d: Path, root: Path = ROOT) -> list[dict]:
    """리그 시작 준비 점검. 저장소 안에서 확인 가능한 것은 자동 판정, 나머지는 '수동 확인'으로 표시."""
    cfg = load_config(d)
    items = []
    def add(area, item, ok, detail, who="Claude"):
        items.append({"area": area, "item": item, "status": "done" if ok is True else ("todo" if ok is False else "manual"),
                      "detail": detail, "who": who})
    today = datetime.now(KST).date()
    u = universe_for(d, today)
    kr, us = len(u.get("KR", {})), len(u.get("US", {}))
    add("대상 종목", "미국 S&P 500 + NASDAQ-100", 480 <= us <= 620, f"{us}종목")
    add("대상 종목", "한국 KOSPI200 + KOSDAQ150", 330 <= kr <= 360, f"{kr}종목" + (" (예시)" if kr < 330 else ""), "운영자: KRX 파일")
    prov = cfg.get("providers", {})
    ver = cfg.get("provider_verified", {})
    def prov_item(m, label, who):
        name = prov.get(m, {}).get("final")
        v = ver.get(name)
        add("데이터", label, True if v else None,
            f"{name} · {v['date']} 수신 확인" if v else f"{name} · league-provider-check 로 시험 필요", who)
    prov_item("KR", "한국 종가 제공처 연결", "운영자: 승인")
    prov_item("US", "미국 종가·배당 제공처 연결", "운영자: 키")
    inq = (root / "docs" / "provider-inquiries.md")
    replied = False
    if inq.exists():
        t = inq.read_text().split("## 회신 기록")[-1]
        replied = any(re.match(r"\|\s*\d{4}-\d{2}-\d{2}", ln) for ln in t.splitlines())
    add("데이터", "제공처 사용권 문의 회신", replied or False, "회신 기록 있음" if replied else "docs/provider-inquiries.md 회신 기록 비어 있음", "운영자: 발송")
    g = guideline_check(d, None, root, register=False)
    bad = [x for x in g if x["status"] in ("unapproved_edit", "missing")]
    add("Claude 팀", "지침 버전 일치", not bad, "모두 일치" if not bad else ", ".join(f"{x['agent_id']}:{x['status']}" for x in bad))
    rehearsal = list((root / "league" / "imports").glob("sandbox*/*-debate.md"))
    add("Claude 팀", "연습 라운드 1회 이상 (/league-round sandbox)", bool(rehearsal), f"{len(rehearsal)}회", "Claude (운영자 승인 후)")
    roster = load_roster(d)
    appr = {(x["team"], x["agent_id"]) for x in read_ledger(d, "approvals") if x.get("decision") == "approved"}
    for team in cfg["teams"]:
        mem = [a for a in roster.get(team, []) if a.get("status") == "active"]
        bench = roster.get("bench" if team == "claude" else f"bench_{team}", [])
        nb = sum(1 for b_ in bench if (team, b_["id"]) in appr)
        add(f"{cfg['teams'][team]['label']}", "현역 5명 · 승인된 대기 후보 2명 이상", len(mem) == 5 and nb >= 2, f"현역 {len(mem)} · 승인 대기 {nb}")
    add("운영", "자동화 스위치 (automation_enabled)", bool(cfg.get("automation_enabled")), str(cfg.get("automation_enabled")), "운영자 결정")
    add("운영", "운영자 보기 배포 (deploy_enabled + 비밀번호 잠금)", bool(cfg.get("deploy_enabled")), "docs/deploy-cloudflare.md 0장 · 지인 공개는 제공처 회신 뒤", "운영자: 계정")
    add("운영", "리그 시작일", bool(cfg.get("season_start")), cfg.get("season_start") or "미정", "운영자 결정")
    return items

# ───────────────────────── 화면용 내보내기 ─────────────────────────

PRIVATE_SCORE_FIELDS = ("base_close", "eval_close")       # 원시 가격: 지인 공유판에서 제외

def _strip_prices(sc: dict) -> dict:
    sc = {k: v for k, v in sc.items() if k not in PRIVATE_SCORE_FIELDS}
    if isinstance(sc.get("adjustment"), dict):
        sc["adjustment"] = {k: v for k, v in sc["adjustment"].items() if k != "dividend"} | \
                           {"dividend_applied": bool(sc["adjustment"].get("dividend"))}
    return sc

def embargo_picks(picks: list[dict], cfg: dict, now: datetime | None = None,
                  subs: list[dict] | None = None) -> tuple[list[dict], dict]:
    """마감(08:30 KST) 전 라운드의 추천은 내보내기에서 뺀다. 팀별로 몇 건이 가려졌는지만 남긴다.
    동시 공개(지문 방식 라운드): 그 라운드에 지문을 낸(committed) 팀이 모두 원본 접수(accepted)될 때까지,
    또는 원본 공개 마감(12:00)이 될 때까지 그 라운드의 종목은 어느 팀 것도 내보내지 않는다.
    한 팀 카드만 먼저 화면에 뜨지 않게 하기 위해서다. 지문을 내지 않은 팀은 기다리지 않는다."""
    now = now or datetime.now(KST)
    waiting = {}
    if subs is not None:
        for rd in {p["round_date"] for p in picks}:
            day = date.fromisoformat(rd)
            if not commit_reveal_applies(rd, cfg) or now >= reveal_deadline(day, cfg):
                continue
            mine = [s_ for s_ in subs if s_.get("round_date") == rd]
            committed = {s_["team"] for s_ in mine if s_.get("status") == "committed"}
            accepted = {s_["team"] for s_ in mine if s_.get("status") == "accepted"}
            if committed - accepted:
                waiting[rd] = sorted(committed - accepted)
    shown, hidden = [], {}
    for p in picks:
        if now < lock_deadline(date.fromisoformat(p["round_date"]), cfg) or p["round_date"] in waiting:
            key = f'{p["team"]}|{p["round_date"]}'
            hidden[key] = hidden.get(key, 0) + 1
        else:
            shown.append(p)
    return shown, hidden

def export(d: Path, out: Path, public: bool = False, now: datetime | None = None):
    cfg = load_config(d)
    now = now or datetime.now(KST)
    if (d / "SAMPLE").exists():                     # 예시 원장: 실제 추천이 아니므로 가리지 않음
        picks, embargoed = read_ledger(d, "picks"), {}
    else:
        picks, embargoed = embargo_picks(read_ledger(d, "picks"), cfg, now, read_ledger(d, "submissions"))
    shown_ids = {p.get("pick_id") for p in picks}
    weeks = sorted({iso_week(date.fromisoformat(p["round_date"])) for p in picks})
    roster = load_roster(d)
    data = {"generated": now.isoformat(timespec="seconds"), "config": cfg, "roster": roster,
            "picks": picks, "embargoed": embargoed,
            "scores": [x for x in latest_scores(d).values() if x.get("pick_id") in shown_ids], "corrections": read_ledger(d, "corrections"),
            "weekly": {team: {wk: weekly(d, wk, team) for wk in weeks} for team in cfg["teams"]},
            "league": ({wk: weekly_league(d, wk) for wk in weeks} if cfg.get("weekly", {}).get("mode") == "combined_bottom1" else {}),
            "teams": team_summary(d), "submissions": read_ledger(d, "submissions"),
            "approvals": read_ledger(d, "approvals"),
            "outages": read_ledger(d, "outages"),
            "ledger_ok": not verify(d), "sample": (d / "SAMPLE").exists(), "public": public}
    if public:
        # 지인 공유판: 원시 가격·배당 금액·내부 원장 경로 제외. 점수(%)·순위·종목명·근거만 남긴다.
        data["scores"] = [_strip_prices(x) for x in data["scores"]]
        data["submissions"] = [{**{k: v for k, v in x.items() if k in ("team", "round_date", "kind", "status", "pushed_at", "imported",
                                                                         "commit", "csv_sha256", "errors", "sealed", "early_reveal", "judged_by")},
                                **({"source_commit": str((x.get("source") or {}).get("commit") or "")[:7]} if x.get("source") else {})}
                               for x in data["submissions"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("// 자동 생성: python3 tools/league.py export\nwindow.LEAGUE = "
                   + json.dumps(data, ensure_ascii=False) + ";\n")

def build_site(d: Path, out: Path, now: datetime | None = None) -> list[str]:
    """지인 배포용 정적 폴더. 게임 화면(테이블)만 올린다: index.html + data/table.js.
    (2026-11-05 운영자 결정: 지인에게는 게임 스타일 화면만 보인다. 표 화면 league.html·시장 대시보드는 올리지 않는다.)
    원시 가격·마감 전 종목·회사 로고가 들어가면 실패한다."""
    import shutil
    import build_play
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    html, js = build_play.build(out, now=now, base=d)
    html.rename(out / "index.html")
    leaked = [f for f in out.rglob("*.js") if re.search(r'"(base_close|eval_close|close|amount)"\s*:', f.read_text())]
    if leaked:
        raise RuntimeError(f"원시 가격 필드가 배포 파일에 남음: {leaked}")
    cfg = load_config(d)
    built = json.loads(js.read_text().split("window.TABLE = ", 1)[1].rstrip().rstrip(";"))
    gen = datetime.fromisoformat(built["generated_at"])
    early = [p.get("pick_id") for p in built["picks"] if gen < lock_deadline(date.fromisoformat(p["round_date"]), cfg)]
    if early:
        raise RuntimeError(f"마감 전 추천이 배포 파일에 남음: {early}")
    if "data:image/png" in (out / "index.html").read_text() or "logos" in built:
        raise RuntimeError("회사 로고가 배포 파일에 남음")
    return sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())

# ───────────────────────── 공통 자료 (07:00 snapshot) ─────────────────────────

def _snapshot_disclosures(round_date: date, universe_kr: dict) -> dict:
    """OpenDART 최근 공시(대상 종목). 키가 없거나 오류면 상태만 기록하고 공통 자료 생성은 계속한다."""
    import os
    if not os.environ.get("DART_API_KEY"):
        return {"status": "not_configured", "note": "DART_API_KEY 없음"}
    try:
        import dart
        return dart.recent_for_snapshot(round_date, universe_kr)
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)[:200]}"}

def snapshot(d: Path, round_date: date, variant: str = "price-free", now: str | None = None) -> tuple[dict, str]:
    """두 팀에 같은 시점의 같은 자료를 준다. variant:
    - price-free: 공개·자유 이용 가능한 자료만 (거래일·대상 범위 참조·기업행동 일정·SEC 13F). 사용권 확인 전 기본값.
    - with-prices: 위 + 기준 세션 종가(원장에 있는 값, 출처·상태 표시). 제공처 사용권(사용 형태 ②) 확인 후에만 사용."""
    assert variant in ("price-free", "with-prices")
    cfg = load_config(d)
    uni_p = d / "universe.json" if (d / "universe.json").exists() else ROOT / "league" / "universe.json"
    uni = json.loads(uni_p.read_text())
    markets = {m: timing(m, round_date, cfg) for m in ("KR", "US")}
    cas = corporate_actions(d)
    upcoming = []
    open_src = set(cfg.get("open_license_sources", []))
    for c in cas:
        if variant == "price-free" and c.get("source") not in open_src:
            continue          # 가격 제외판: 이용 제한 없는 출처의 기업행동 일정만
        if c["type"] in ("dividend", "split") and c.get("ex_date"):
            ex = date.fromisoformat(c["ex_date"])
            if round_date <= ex <= round_date + timedelta(days=10):
                upcoming.append({k: c[k] for k in ("type", "market", "ticker", "ex_date") if k in c}
                                | ({"amount": c["amount"]} if c["type"] == "dividend" else {"ratio": c.get("ratio")}))
    holdings = None
    hp = ROOT / "data" / "holdings.json"
    if hp.exists():
        h = json.loads(hp.read_text())
        holdings = {"source": h.get("source"), "generated": h.get("generated"),
                    "funds": [{"name": f["name"], "period": f["period"], "filed": f["filed"],
                               "top10": [{"name": x["name"], "cusip": x["cusip"], "put_call": x.get("putCall") or None,
                                          "weight_pct": round(x["weight"], 2), "change": x["change"]} for x in f["holdings"][:10]]}
                              for f in h.get("funds", [])]}
    snap = {
        "round_date": round_date.isoformat(), "variant": variant,
        "generated_at": now or datetime.now(KST).isoformat(timespec="seconds"),
        "deadline_kst": lock_deadline(round_date, cfg).isoformat(),
        "markets": {m: (t if t else {"open": False, "note": "휴장 — 이 시장 종목 선택 불가"}) for m, t in markets.items()},
        "universe": {"file": str(uni_p.relative_to(d.parent) if uni_p.is_relative_to(d.parent) else uni_p.name),
                     "sha256": hashlib.sha256(uni_p.read_bytes()).hexdigest(), "status": uni.get("status"),
                     "counts": {m: len(uni.get(m, {})) for m in ("KR", "US")}},
        "corporate_actions_upcoming": sorted(upcoming, key=lambda x: (x["ex_date"], x["market"], x["ticker"])),
        "corporate_actions_sources": sorted(open_src) if variant == "price-free" else "all",
        "institutional_13f": holdings,
        "disclosures": _snapshot_disclosures(round_date, uni.get("KR", {})),
        "rules": {"scoring": cfg["scoring"]["formula"], "benchmarks": cfg.get("benchmarks")},
        "notes": ["이 자료 이후 08:30 KST 전까지 추가 검색은 허용되며 출처·기준일·확보 시각을 기록한다."],
    }
    if variant == "with-prices":
        idx = price_index(d)
        rows = []
        for m, t in markets.items():
            if not t:
                continue
            for tk in list(uni.get(m, {})) + [cfg.get("benchmarks", {}).get(m)]:
                r = idx.get((m, tk, t["base_session"]))
                if r and r.get("close") is not None:
                    rows.append({"market": m, "ticker": tk, "session": t["base_session"], "close": r["close"],
                                 "status": r.get("status"), "source": r.get("source")})
        snap["base_closes"] = rows
        snap["notes"].append("base_closes는 비공개 공통 자료 전용. 지인 화면·외부 재배포 금지.")
    body = json.dumps(snap, ensure_ascii=False, sort_keys=True, indent=1)
    return snap, body

def write_snapshot(d: Path, round_date: date, variant: str, now: str | None = None) -> tuple[Path, str]:
    snap, body = snapshot(d, round_date, variant, now)
    out = d / "rounds" / round_date.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    name = "snapshot.json" if variant == "price-free" else "snapshot-with-prices.json"
    (out / name).write_text(body)
    sha = hashlib.sha256(body.encode()).hexdigest()
    (out / (name + ".sha256")).write_text(f"{sha}  {name}\n")
    return out / name, sha

# ───────────────────────── 예시 데이터 ─────────────────────────

def make_sample(d: Path, close_week: bool = True):
    """화면·계산 검증용 가상 데이터. 실제 시세 아님. 분할·배당·거래정지·가격 누락 사례를 일부러 포함."""
    import random, shutil
    if d.exists():
        shutil.rmtree(d)
    (d / "ledger").mkdir(parents=True)
    (d / "agents").mkdir()
    (d / "SAMPLE").write_text("이 폴더는 가상 예시 데이터입니다.\n")
    for f in ("config.json", "universe.json"):
        (d / f).write_text((ROOT / "league" / f).read_text())
    roster = json.loads((ROOT / "league" / "agents" / "roster.json").read_text())
    sh = json.loads((ROOT / "league" / "imports" / "shushu" / "roster.json").read_text())   # 슈슈 팀 실제 명단(애칭·소개 문구)
    roster["shushu"] = [{**m, "status": "active", "joined_week": "2026-W46", "eliminated_week": None, "version": m.get("version", 1)}
                        for m in sh["members"]]
    roster["bench_shushu"] = [dict(m) for m in sh["bench"]]
    (d / "agents" / "roster.json").write_text(json.dumps(roster, ensure_ascii=False, indent=1))
    cfg = load_config(d)
    uni = json.loads((d / "universe.json").read_text())
    rnd = random.Random(46)
    start = date(2026, 11, 9)                  # 2026-W46 월요일
    days = [start + timedelta(days=i) for i in range(5)]
    base_px = {**{("KR", t): rnd.randint(30, 400) * 1000 for t in uni["KR"]},
               **{("US", t): round(rnd.uniform(50, 600), 2) for t in uni["US"]}}
    written = set()

    def put_price(m, t, s, close, **kw):
        if (m, t, s) in written:
            return
        written.add((m, t, s))
        append(d, "prices", {"market": m, "ticker": t, "session": s, "close": close, "basis": "unadjusted",
                             "halted": False, "source": "SAMPLE", "status": "final",
                             "fetched_at": f"{s}T18:00:00+09:00", **kw})

    def put_ca(**kw):
        append(d, "corporate_actions", {"source": "SAMPLE", **kw})
    agents = {"claude": [a["id"] for a in roster["claude"]], "shushu": [a["id"] for a in roster["shushu"]]}
    members = {(t, a_["id"]): a_ for t in ("claude", "shushu") for a_ in roster[t]}
    skill = {"buffett": .25, "lynch": .1, "dalio": 0, "wood": -.1, "burry": -.35, "s1": .2, "s2": 0, "s3": .05, "s4": -.2, "s5": .1}
    # 예외 사례 전용 종목 (다른 추천과 가격이 섞이지 않도록 무작위 선택에서 제외)
    # 예외 사례 전용 종목 (다른 추천과 가격이 섞이지 않도록 무작위 선택에서 제외). 키: (팀, 에이전트, 일, 시장)
    special_cases = {
        ("claude", "lynch", 11, "US"): ("KO", "split"),         # 평가일 1→4 분할
        ("claude", "dalio", 12, "KR"): ("105560", "dividend"),  # 평가일 배당락
        ("shushu", "s4", 13, "KR"): ("068270", "halt"),         # 평가일 거래정지 → 다음 세션 지연 채점
        ("claude", "wood", 13, "US"): ("JPM", "missing"),       # 평가 종가 누락 → 보류
        ("claude", "buffett", 12, "US"): ("AMZN", "unchecked"), # 배당·분할 확인 기록 없음 → 보류
    }
    reserved = {(k[3], t) for k, (t, _) in special_cases.items()}
    dec = lambda m: 2 if m == "US" else -1
    # 벤치마크 지수: 세션별 시장 수익률 (종목 수익률 = 시장 + 에이전트 성향 + 개별 잡음)
    bench = cfg["benchmarks"]
    mret, level = {}, {"KR": 2650.0, "US": 680.0}
    for m in ("KR", "US"):
        x = date(2026, 11, 2)
        while x <= date(2026, 11, 20):
            if is_session(m, x, cfg):
                mret[(m, x.isoformat())] = rnd.gauss(0.0005, 0.009)
                level[m] = round(level[m] * (1 + mret[(m, x.isoformat())]), 2)
                put_price(m, bench[m], x.isoformat(), level[m])
            x += timedelta(days=1)
    for rd in days:
        for team, ids in agents.items():
            for aid in ids:
                for m in sorted(open_markets(rd, cfg)):
                    case = special_cases.get((team, aid, rd.day, m))
                    if case:
                        t, kind = case
                    else:
                        kind = None
                        t = rnd.choice(sorted(x for x in uni[m] if (m, x) not in reserved))
                    rec = make_pick(team, aid, version_for_round(members[(team, aid)], rd.isoformat()) or 1, rd.isoformat(), m, t, uni[m][t],
                                    f"{rd.isoformat()}T08:{rnd.randint(5, 29):02d}:00+09:00",
                                    f"[예시] {uni[m][t]} 선정 근거 요약", ["[예시] 실적 하회 위험", "[예시] 환율 변동"],
                                    [{"title": "예시 출처", "url": "https://example.com", "as_of": prev_session(m, rd, cfg).isoformat()}],
                                    cfg, agent_label=aid)
                    bs, es = rec["base_session"], rec["eval_session"]
                    b = base_px[(m, t)]
                    put_price(m, t, bs, b)
                    r = mret[(m, es)] * rnd.uniform(0.7, 1.4) + rnd.gauss(skill[aid] / 100, 0.015)
                    close = round(b * (1 + r), dec(m))
                    if kind == "split":
                        put_price(m, t, es, round(close / 4, dec(m)))
                        put_ca(type="split", market=m, ticker=t, ex_date=es, ratio=4.0)
                    elif kind == "dividend":
                        div = round(b * 0.01, 0)
                        put_price(m, t, es, round(close - div, dec(m)))
                        put_ca(type="dividend", market=m, ticker=t, ex_date=es, amount=div, currency="KRW",
                               pay_date="2026-12-10")
                    elif kind == "halt":
                        put_price(m, t, es, None, halted=True)
                        put_price(m, t, next_session(m, date.fromisoformat(es), cfg).isoformat(), round(b * 0.985, dec(m)))
                    elif kind != "missing":
                        put_price(m, t, es, close)
                        base_px[(m, t)] = close
                    submit_pick(d, rec)
    for team, bid in (("claude", "momentum"), ("claude", "quant"), ("shushu", "s6"), ("shushu", "s7")):
        append(d, "approvals", {"type": "bench", "team": team, "agent_id": bid, "decision": "approved", "source": "SAMPLE"})
    # 배당·분할 확인 기록 (AMZN은 일부러 누락)
    for m in ("KR", "US"):
        for t in sorted(uni[m]):
            if (m, t) != ("US", "AMZN"):
                put_ca(type="checked", market=m, ticker=t, **{"from": "2026-11-01", "to": "2026-11-30"},
                       checked_at="2026-11-16T06:50:00+09:00")
    # 금요일(11/13) 미국분 일부는 아직 잠정 상태로 남기기 위해 채점 기준일을 11/16(월) 아침으로
    run_scoring(d, today=date(2026, 11, 16), now="2026-11-16T07:00:00+09:00")
    if close_week:
        weekly_close(d, "2026-W46", now="2026-11-16T06:30:00+09:00")

# ───────────────────────── CLI ─────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["verify", "score", "weekly", "import-csv", "sample", "export", "schedule", "receipt", "append-only", "build-site", "snapshot", "make-csv", "weekly-close", "collect-due", "review-data", "guideline-check", "readiness", "outage", "commit", "update-plan"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--dir", default=str(ROOT / "league"))
    ap.add_argument("--team", default="claude")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--to", help="schedule: 끝 날짜")
    ap.add_argument("--public", action="store_true", help="export: 지인 공유판 (원시 가격 제외)")
    ap.add_argument("--variant", default="price-free", choices=["price-free", "with-prices"])
    ap.add_argument("--reason", help="outage: 미제출 사유")
    ap.add_argument("--agent", help="outage: 특정 에이전트만 해당하면 id")
    ap.add_argument("--kind", default="operator", choices=["operator", "team"])
    ap.add_argument("--run-id", default="")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--run-created-at")
    a = ap.parse_args()
    d = Path(a.dir)
    if a.cmd == "verify":
        errs = verify(d)
        print("\n".join(errs) if errs else "원장 정상 (해시 체인 일치)")
        sys.exit(1 if errs else 0)
    elif a.cmd == "score":
        for r in run_scoring(d):
            print(r["pick_id"], r["status"], r.get("score"), r.get("reason") or "")
    elif a.cmd == "weekly":
        print(json.dumps(weekly(d, a.arg or iso_week(datetime.now(KST).date()), a.team), ensure_ascii=False, indent=1))
    elif a.cmd == "import-csv":
        ok, bad = import_csv(d, Path(a.arg), a.team, a.dry_run)
        for b in bad:
            print(f"✗ {b['line']}행: {'; '.join(b['errors'])}")
        print(f"검증 통과 {len(ok)}건, 오류 {len(bad)}건" + (" — 오류가 있어 아무것도 기록하지 않음" if bad else
                                                        (" (dry-run)" if a.dry_run else " — 기록 완료")))
        sys.exit(1 if bad else 0)
    elif a.cmd == "sample":
        make_sample(d)
        print(f"예시 데이터 생성: {d}")
    elif a.cmd == "weekly-close":
        wk = a.arg or iso_week(datetime.now(KST).date() - timedelta(days=7))
        res = weekly_close(d, wk)
        for r in res:
            print(f"{r['team']} {r['week']}{(' ' + r['market']) if r.get('market') else ''}: 탈락 {r['eliminate'] or '없음'} → 대체 {r['replacement'] or '없음'}"
                  + (f" · 보류: {'; '.join(r['hold_reasons'])}" if r['hold_reasons'] else ""))
        if not res:
            print(f"{wk}: 새로 마감할 팀 없음 (이미 마감했거나 기록 없음)")
    elif a.cmd == "outage":
        if not (a.arg and a.reason):
            sys.exit("사용법: league.py outage <라운드 날짜> --team <팀> --reason <사유> [--agent <id>] [--kind operator|team]")
        r = record_outage(d, a.team, a.arg, a.reason, a.agent, a.kind)
        print(f"기록: {r['team']} {r['round_date']} {r.get('agent_id') or '팀 전체'} — {r['reason']} (미제출로 집계)")
    elif a.cmd == "readiness":
        mark = {"done": "✅", "todo": "⬜", "manual": "🔎"}
        items = readiness(d)
        cur = None
        for it in items:
            if it["area"] != cur:
                cur = it["area"]; print(f"\n[{cur}]")
            print(f" {mark[it['status']]} {it['item']} — {it['detail']}  ({it['who']})")
        n = sum(1 for x in items if x["status"] == "done")
        print(f"\n완료 {n}/{len(items)} · ✅ 완료 ⬜ 남음 🔎 GitHub·사이트에서 확인 필요")
    elif a.cmd == "update-plan":
        wk = a.arg or iso_week(datetime.now(KST).date() - timedelta(days=7))      # 기본: 지난주(월요일 마감 뒤 실행)
        print(json.dumps(update_plan(d, wk), ensure_ascii=False, indent=1))
    elif a.cmd == "review-data":
        wk = a.arg or iso_week(datetime.now(KST).date())
        print(json.dumps(review_data(d, wk, a.team), ensure_ascii=False, indent=1))
    elif a.cmd == "guideline-check":
        rd = date.fromisoformat(a.arg) if a.arg else None
        res = guideline_check(d, rd, register=not a.dry_run)
        for r in res:
            print(f"{r['agent_id']:<10} v{r['version']}  {r['status']}  {r.get('detail', '') or r.get('effective_round', '') or ''}")
        sys.exit(1 if any(r["status"] in ("unapproved_edit", "missing") for r in res) else 0)
    elif a.cmd == "collect-due":
        import collectors as C
        today = date.fromisoformat(a.arg) if a.arg else datetime.now(KST).date()
        rep = C.collect_due(d, today)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    elif a.cmd == "make-csv":
        src = json.loads(Path(a.arg).read_text())
        out = make_csv(src["picks"], src["round_date"], Path(a.out))
        print(out)
    elif a.cmd == "commit":
        out = write_commitment(Path(a.arg))
        print(f"지문: {out}  ({out.read_text().split()[0]})")
        print("마감(08:30) 전에는 이 .sha256 파일만 push하고, CSV·토론 기록·rounds 폴더는 08:30 이후 push한다.")
    elif a.cmd == "build-site":
        out = Path(a.out or (ROOT / "site"))
        for f in build_site(d, out):
            print(f)
        print(f"배포 폴더: {out} (원시 가격 없음 확인)")
    elif a.cmd == "snapshot":
        p, sha = write_snapshot(d, date.fromisoformat(a.arg) if a.arg else datetime.now(KST).date(), a.variant)
        print(f"{p}\nsha256 {sha}")
    elif a.cmd == "schedule":
        cfg = load_config(d)
        start = date.fromisoformat(a.arg) if a.arg else datetime.now(KST).date()
        end = date.fromisoformat(a.to) if a.to else start + timedelta(days=13)
        hm = lambda x: x[5:10].replace("-", "/") + " " + x[11:16]
        print(f"마감: 매 라운드 당일 {cfg['lock_deadline']} KST · 시각은 모두 KST · 정규장 기준")
        for r in schedule(start, end, cfg):
            line = f"{r['round_date']}({r['weekday']}) "
            for m in ("KR", "US"):
                t = r[m]
                line += f"| {m}: " + (f"기준 {t['base_session'][5:]} 종가({hm(t['base_close_kst'])}) → 평가 {t['eval_session'][5:]} 종가({hm(t['eval_close_kst'])}){'' if t['ok'] else ' ⚠시간 불일치'} "
                                      if t else "휴장 — 선택 불가 ")
            print(line)
    elif a.cmd == "append-only":
        errs = append_only_violations(a.arg, a.to or "HEAD")
        print("\n".join(errs) if errs else "원장 변경은 모두 끝에 추가된 줄뿐입니다")
        sys.exit(1 if errs else 0)
    elif a.cmd == "receipt":
        event = json.loads(Path(a.arg).read_text())
        try:
            rs = process_push(event, a.run_id, a.run_url, a.run_created_at)
        except CommitmentPending as e:
            print(f"대기: {e}")
            sys.exit(75)                               # 워크플로가 최신 원장을 받아 다시 시도한다
        for r in rs:
            print(f"{r['team']} {r['round_date']} {r['status']} push={r['pushed_at']} sha256={(r.get('csv_sha256') or r.get('committed_sha256') or '')[:12]} {'; '.join(r['errors'])}")
    elif a.cmd == "export":
        out = Path(a.out or (ROOT / "data" / ("league-public.js" if a.public else "league.js")))
        export(d, out, public=a.public)
        print(f"내보내기: {out}")

if __name__ == "__main__":
    main()
