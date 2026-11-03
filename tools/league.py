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

import argparse, csv, hashlib, json, statistics, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
KST = ZoneInfo("Asia/Seoul")
LEDGERS = ("picks", "prices", "scores", "corrections", "corporate_actions", "submissions")

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

def ca_for(cas: list[dict], m: str, t: str, after: date, upto: date):
    """(after, upto] 구간의 배당 합계·분할 비율·확인 여부."""
    mine = [c for c in cas if c["market"] == m and c["ticker"] == t]
    checked = any(c["type"] == "checked" and date.fromisoformat(c["from"]) <= after + timedelta(days=1)
                  and date.fromisoformat(c["to"]) >= upto for c in mine)
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

def evaluate_pick(p: dict, prices: dict, cfg: dict, today: date, cas: list[dict] | None = None) -> dict:
    """추천 1건의 현재 채점 상태를 계산한다 (원장에 쓰지는 않음)."""
    w = cfg["weekly"]
    cas = cas or []
    m, t = p["market"], p["ticker"]
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
        checked, div, ratio, divs, splits = ca_for(cas, m, t, base_s, s)
        if not checked:
            out.update(status="held", reason="배당·분할 정보 미확인")
            return out
        if divs and splits:
            out.update(status="held", reason="배당과 분할이 같은 구간에 발생 — 수동 확인 필요")
            return out
        total, price_only = compute_scores(base["close"], ev["close"], ratio, div)
        refs = [c["hash"] for c in divs + splits]
    # 참고: 시장 대비 초과 점수 = 공식 점수 − 같은 구간 벤치마크 지수 수익률 (지수는 가격지수)
    bench = cfg.get("benchmarks", {}).get(m)
    bb_, be_ = prices.get((m, bench, base_s.isoformat())), prices.get((m, bench, s.isoformat()))
    bench_ret = excess = None
    if bench and bb_ and be_ and bb_.get("close") and be_.get("close"):
        bench_ret = round((be_["close"] / bb_["close"] - 1) * 100, 2)
        excess = round(total - bench_ret, 2)
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
    return roster

def _avg(v):
    return round(statistics.mean(v), 2) if v else None

def weekly(d: Path, week: str, team: str = "claude") -> dict:
    cfg = load_config(d)
    w = cfg["weekly"]
    roster = load_roster(d)
    members = [a for a in roster.get(team, []) if a["status"] == "active" or a.get("eliminated_week") == week]
    scores = latest_scores(d)
    picks = [p for p in read_ledger(d, "picks") if p["team"] == team and iso_week(date.fromisoformat(p["round_date"])) == week]
    # 이 주의 기대 제출 수 = 라운드별 열린 시장 수 (에이전트 합류 이후)
    y, wk = map(int, week.split("-W"))
    week_days = [date.fromisocalendar(y, wk, i) for i in range(1, 6)]
    rows = []
    for a in members:
        mine = [p for p in picks if p["agent_id"] == a["id"]]
        expected = sum(len(open_markets(dd, cfg)) for dd in week_days
                       if not a.get("joined_week") or iso_week(dd) >= a["joined_week"])
        fin = [(p, scores[p["pick_id"]]) for p in mine
               if p["pick_id"] in scores and scores[p["pick_id"]]["status"] == "final"]
        vals = [sc["score"] for _, sc in fin]
        exc = [sc["score_excess"] for _, sc in fin if sc.get("score_excess") is not None]
        by_m = {mk: [sc["score"] for p, sc in fin if p["market"] == mk] for mk in ("KR", "US")}
        exc_m = {mk: [sc["score_excess"] for p, sc in fin if p["market"] == mk and sc.get("score_excess") is not None]
                 for mk in ("KR", "US")}
        held = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") in ("held", "pending", "provisional", None))
        void = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") == "void")
        rows.append({"agent_id": a["id"], "label": a["label"], "version": a.get("version", 1),
                     "picks": len(mine), "expected": expected, "missed": max(expected - len(mine), 0),
                     "submit_rate": round(len(mine) / expected * 100, 1) if expected else None,
                     "void_rate": round(void / len(mine) * 100, 1) if mine else None,
                     "scored": len(vals), "held_or_pending": held, "void": void,
                     "avg": round(statistics.mean(vals), 2) if vals else None,
                     "median": round(statistics.median(vals), 2) if vals else None,
                     "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                     "sum": round(sum(vals), 2) if vals else 0.0, "new_this_week": a.get("joined_week") == week,
                     "avg_excess": _avg(exc),
                     "markets": {mk: {"avg": _avg(by_m[mk]), "scored": len(by_m[mk]), "avg_excess": _avg(exc_m[mk])}
                                 for mk in ("KR", "US")}})
    nz = lambda v: -1e9 if v is None else v      # 0점은 유효한 값이므로 `or`를 쓰면 안 됨
    key = lambda r: (nz(r["avg"]), nz(r["median"]), nz(r["min"]))
    rows.sort(key=key, reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    decision = {"eliminate": None, "hold_reasons": []}
    total = sum(r["scored"] for r in rows)
    if rows:
        bottom = rows[-1]
        tied = [r for r in rows if key(r) == key(bottom)]
        if total < w["min_total_scored_in_week"]:
            decision["hold_reasons"].append(f"주간 채점 완료 {total}건 < {w['min_total_scored_in_week']}건 (데이터 부족 주간)")
        if bottom["scored"] < w["min_scored_for_elimination"]:
            decision["hold_reasons"].append(f"최하위 {bottom['label']} 채점 {bottom['scored']}건 < {w['min_scored_for_elimination']}건")
        if w["protect_first_week"] and bottom["new_this_week"]:
            decision["hold_reasons"].append(f"최하위 {bottom['label']}는 이번 주 합류 (첫 주 보호)")
        if len(tied) > 1:
            decision["hold_reasons"].append("최하위 동점 (평균·중앙값·최저점 모두 같음)")
        if not decision["hold_reasons"]:
            decision["eliminate"] = bottom["agent_id"]
    bench = roster.get("bench" if team == "claude" else f"bench_{team}", [])   # 사전 승인된 대기 후보 (순서대로 투입)
    decision["replacement"] = bench[0]["id"] if decision["eliminate"] and bench else None
    return {"week": week, "team": team, "ranking": rows, "decision": decision}

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
        cum, series = 0.0, []
        for dd in days:
            daysum = round(sum(t["daily"][dd]), 2); cum = round(cum + daysum, 2)
            series.append({"date": dd, "sum": daysum, "cumulative": cum, "n": len(t["daily"][dd])})
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

def validate_pick(rec: dict, d: Path, cfg: dict, existing: list[dict]) -> list[str]:
    errs = []
    uni = json.loads((d / "universe.json").read_text()) if (d / "universe.json").exists() \
        else json.loads((ROOT / "league" / "universe.json").read_text())
    rd = date.fromisoformat(rec["round_date"])
    if rec["market"] not in ("KR", "US"):
        errs.append("market은 KR 또는 US")
    elif rec["ticker"] not in uni[rec["market"]]:
        errs.append(f"대상 범위 밖 종목: {rec['market']} {rec['ticker']}")
    elif not round_sessions(rec["market"], rd, cfg):
        errs.append(f"{rec['round_date']}은 {rec['market']} 휴장일 — 이 시장 종목 선택 불가")
    locked = datetime.fromisoformat(rec["locked_at"])
    if locked.tzinfo is None:
        errs.append("locked_at에 시간대 필요 (예: +09:00)")
    elif locked > lock_deadline(rd, cfg):
        errs.append(f"마감({cfg['lock_deadline']} KST) 이후 확정: {rec['locked_at']}")
    same = [p for p in existing if p["team"] == rec["team"] and p["round_date"] == rec["round_date"]]
    if any(p["agent_id"] == rec["agent_id"] and p["market"] == rec["market"] for p in same):
        errs.append(f"{rec['agent_id']}는 이 라운드 {rec['market']} 종목을 이미 추천함")
    if len({p["agent_id"] for p in same} | {rec["agent_id"]}) > cfg["agents_per_team"]:
        errs.append(f"팀 인원 {cfg['agents_per_team']}명 초과")
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
            errs = validate_pick(rec, d, cfg, existing + ok)
            if not srcs:
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
            if not rec["risks"]:
                errs.append("위험 요인(risks) 없음")
            if not ver.isdigit():
                errs.append("agent_version 없음 (정수)")
            (bad if errs else ok).append({"line": i, "pick": rec, "errors": errs} if errs else rec)
    # 파일 단위 검사: 에이전트마다 그날 열린 시장(KR·US)에서 각 1종목 필수
    rows = ok + [b["pick"] for b in bad]
    for (agent, rd) in sorted({(r["agent_id"], r["round_date"]) for r in rows}):
        need = open_markets(date.fromisoformat(rd), cfg)
        have = {r["market"] for r in rows if r["agent_id"] == agent and r["round_date"] == rd}
        if need - have:
            bad.append({"line": 0, "pick": {"agent_id": agent, "round_date": rd},
                        "errors": [f"{agent}: {rd}에 열린 시장 {'·'.join(sorted(need))} 중 {'·'.join(sorted(need - have))} 종목 누락"]})
    if not dry_run and not bad:
        for rec in ok:
            append(d, "picks", rec)
    return ok, bad

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
    return sorted({f for f in files if SUBMISSION_RE.match(f)})

def ledger_dir_for(team: str, cwd=ROOT) -> Path:
    """sandbox 팀은 시험용 원장(league/sandbox)에 기록해 실제 원장을 오염시키지 않는다."""
    return Path(cwd) / "league" / ("sandbox" if team == "sandbox" else "")

def process_push(event: dict, run_id: str = "", run_url: str = "", run_created_at: str | None = None,
                 cwd=ROOT) -> list[dict]:
    pushed_ts = (event.get("repository") or {}).get("pushed_at")
    pushed_at = datetime.fromtimestamp(int(pushed_ts), KST) if pushed_ts else None
    run_at = datetime.fromisoformat(run_created_at.replace("Z", "+00:00")).astimezone(KST) if run_created_at else None
    # 판정 시각: push 서버 시각. 없으면 워크플로 생성 시각(항상 push 이후라 보수적)
    judged_at, judged_src = (pushed_at, "push_event.repository.pushed_at") if pushed_at else (run_at, "workflow_run.created_at")
    receipts = []
    for path in changed_submission_files(event, cwd):
        team, rd = SUBMISSION_RE.match(path).groups()
        d = ledger_dir_for(team, cwd)
        cfg = load_config(d)
        content = _git("show", f"{event['after']}:{path}", cwd=cwd)
        sha = hashlib.sha256(content.encode()).hexdigest()
        deadline = lock_deadline(date.fromisoformat(rd), cfg)
        rec = {"team": team, "round_date": rd, "path": path, "commit": event["after"], "before": event.get("before"),
               "ref": event.get("ref"), "pusher": (event.get("pusher") or {}).get("name"),
               "csv_sha256": sha, "pushed_at": pushed_at.isoformat() if pushed_at else None,
               "run_id": str(run_id), "run_url": run_url, "run_created_at": run_at.isoformat() if run_at else None,
               "judged_by": judged_src, "deadline": deadline.isoformat(), "errors": [], "imported": 0}
        prior = [s for s in read_ledger(d, "submissions") if s["team"] == team and s["round_date"] == rd and s["status"] == "accepted"]
        if judged_at is None:
            rec.update(status="rejected", errors=["서버 push 시각을 확인할 수 없음"])
        elif prior:
            rec.update(status="rejected", errors=[f"이미 접수된 제출이 있음 ({prior[0]['commit'][:7]}) — 확정 후 변경 불가"])
        elif judged_at > deadline:
            rec.update(status="late", errors=[f"마감 {cfg['lock_deadline']} KST 이후 push ({judged_at.isoformat(timespec='seconds')})"])
        else:
            tmp = d / ".tmp_submission.csv"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(content)
            try:
                ok, bad = import_csv(d, tmp, team, dry_run=True)
                errs = [f"{b['line']}행: {'; '.join(b['errors'])}" for b in bad]
                errs += [f"round_date {r['round_date']}가 파일명 {rd}와 다름" for r in ok if r["round_date"] != rd]
                errs += [f"locked_at {r['locked_at']}가 서버 push 시각보다 늦음" for r in ok
                         if datetime.fromisoformat(r["locked_at"]) > judged_at]
                if errs or not ok:
                    rec.update(status="rejected", errors=errs or ["추천 없음"])
                else:
                    meta = {"commit": event["after"], "csv_sha256": sha, "pushed_at": rec["pushed_at"], "run_id": str(run_id)}
                    for r in ok:
                        append(d, "picks", {**r, "submission": meta})
                    rec.update(status="accepted", imported=len(ok))
            finally:
                tmp.unlink(missing_ok=True)
        receipts.append(append(d, "submissions", rec))
    return receipts

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

# ───────────────────────── 화면용 내보내기 ─────────────────────────

def export(d: Path, out: Path):
    cfg = load_config(d)
    picks = read_ledger(d, "picks")
    weeks = sorted({iso_week(date.fromisoformat(p["round_date"])) for p in picks})
    roster = load_roster(d)
    data = {"generated": datetime.now(KST).isoformat(timespec="seconds"), "config": cfg, "roster": roster,
            "picks": picks, "scores": list(latest_scores(d).values()), "corrections": read_ledger(d, "corrections"),
            "weekly": {wk: weekly(d, wk) for wk in weeks}, "teams": team_summary(d),
            "ledger_ok": not verify(d), "sample": (d / "SAMPLE").exists()}
    out.write_text("// 자동 생성: python3 tools/league.py export\nwindow.LEAGUE = "
                   + json.dumps(data, ensure_ascii=False) + ";\n")

# ───────────────────────── 예시 데이터 ─────────────────────────

def make_sample(d: Path):
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
    roster["shushu"] = [{"id": f"s{i}", "label": f"Codex {i}", "style_ref": "슈슈 팀 (Codex)", "status": "active",
                         "joined_week": "2026-W46", "eliminated_week": None, "version": 1} for i in range(1, 6)]
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
    mret, level = {}, {"KR": 2650.0, "US": 6800.0}
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
                    rec = make_pick(team, aid, 1, rd.isoformat(), m, t, uni[m][t],
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
    # 배당·분할 확인 기록 (AMZN은 일부러 누락)
    for m in ("KR", "US"):
        for t in sorted(uni[m]):
            if (m, t) != ("US", "AMZN"):
                put_ca(type="checked", market=m, ticker=t, **{"from": "2026-11-01", "to": "2026-11-30"},
                       checked_at="2026-11-16T06:50:00+09:00")
    # 금요일(11/13) 미국분 일부는 아직 잠정 상태로 남기기 위해 채점 기준일을 11/16(월) 아침으로
    run_scoring(d, today=date(2026, 11, 16), now="2026-11-16T07:00:00+09:00")

# ───────────────────────── CLI ─────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["verify", "score", "weekly", "import-csv", "sample", "export", "schedule", "receipt", "append-only"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--dir", default=str(ROOT / "league"))
    ap.add_argument("--team", default="claude")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--to", help="schedule: 끝 날짜")
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
        for r in process_push(event, a.run_id, a.run_url, a.run_created_at):
            print(f"{r['team']} {r['round_date']} {r['status']} push={r['pushed_at']} sha256={r['csv_sha256'][:12]} {'; '.join(r['errors'])}")
    elif a.cmd == "export":
        out = Path(a.out or (ROOT / "data" / "league.js"))
        export(d, out)
        print(f"내보내기: {out}")

if __name__ == "__main__":
    main()
