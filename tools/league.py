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
LEDGERS = ("picks", "prices", "scores", "corrections")

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

def compute_score(base_close: float, eval_close: float, split_factor: float = 1.0,
                  dividend: float = 0.0, dividend_mode: str = "include") -> float:
    """점수 = ((평가 종가 × 분할보정 + 평가일 현금배당) ÷ 기준 종가 − 1) × 100, 소수 둘째 자리.
    split_factor: 기준일→평가일 사이 분할 비율 (1→10 분할이면 10, 10→1 병합이면 0.1)."""
    if base_close <= 0:
        raise ValueError("기준 종가가 0 이하")
    adj = eval_close * split_factor + (dividend if dividend_mode == "include" else 0.0)
    return round((adj / base_close - 1) * 100, 2)

def price_index(d: Path) -> dict:
    """(market, ticker, session) → 최신 가격 레코드 (뒤에 추가된 정정이 우선)."""
    idx = {}
    for r in read_ledger(d, "prices"):
        idx[(r["market"], r["ticker"], r["session"])] = r
    return idx

def latest_scores(d: Path) -> dict:
    out = {}
    for r in read_ledger(d, "scores"):
        out[r["pick_id"]] = r
    return out

def evaluate_pick(p: dict, prices: dict, cfg: dict, today: date) -> dict:
    """추천 1건의 현재 채점 상태를 계산한다 (원장에 쓰지는 않음)."""
    w = cfg["weekly"]
    m, t = p["market"], p["ticker"]
    base_s, eval_s = date.fromisoformat(p["base_session"]), date.fromisoformat(p["eval_session"])
    out = {"pick_id": p["pick_id"], "eval_session": p["eval_session"], "status": "pending", "score": None,
           "reason": None, "delayed": False}
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
        waited = 0
        x = eval_s
        while x < today and waited <= w["missing_price_wait_sessions"]:
            x = next_session(m, x, cfg); waited += 1
        out.update(status="held", reason="평가 종가 미확인" + (" — 수동 확인 필요" if waited > w["missing_price_wait_sessions"] else ""))
        return out
    split = 1.0
    div = 0.0
    if s == eval_s:   # 기업행동은 평가 세션 기준 기록값 사용
        split = float(ev.get("split_factor", 1.0))
        div = float(ev.get("cash_dividend_exdate", 0.0))
    score = compute_score(base["close"], ev["close"], split, div, cfg["dividend_mode"])
    final = base.get("status") == "final" and ev.get("status") == "final"
    out.update(status="final" if final else "provisional", score=score, eval_session=s.isoformat(),
               delayed=s != eval_s, reason="거래정지 후 지연 채점" if s != eval_s else None,
               base_close=base["close"], eval_close=ev["close"],
               adjustment={"split": split, "dividend": div if cfg["dividend_mode"] == "include" else 0.0})
    return out

def run_scoring(d: Path, today: date | None = None, now: str | None = None) -> list[dict]:
    """상태가 바뀐 추천만 scores.jsonl 에 추가. final 이후 값이 바뀌면 correction 으로 기록."""
    cfg = load_config(d)
    today = today or datetime.now(KST).date()
    prices, prev = price_index(d), latest_scores(d)
    written = []
    for p in read_ledger(d, "picks"):
        cur = evaluate_pick(p, prices, cfg, today)
        old = prev.get(p["pick_id"])
        keys = ("status", "score", "reason", "eval_session")
        if old and all(old.get(k) == cur.get(k) for k in keys):
            continue
        if old is None and cur["status"] == "pending":
            continue
        cur["scored_at"] = now or datetime.now(KST).isoformat(timespec="seconds")
        if old and old["status"] == "final":
            cur["correction_of"] = old["hash"]
            append(d, "corrections", {"pick_id": p["pick_id"], "before": old.get("score"), "after": cur.get("score"),
                                      "reason": "확정 후 가격 정정", "at": cur["scored_at"]})
        written.append(append(d, "scores", cur))
    return written

# ───────────────────────── 주간 순위 ─────────────────────────

def iso_week(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"

def weekly(d: Path, week: str, team: str = "claude") -> dict:
    cfg = load_config(d)
    w = cfg["weekly"]
    roster = json.loads((d / "agents" / "roster.json").read_text()) if (d / "agents" / "roster.json").exists() \
        else json.loads((ROOT / "league" / "agents" / "roster.json").read_text())
    members = [a for a in roster.get(team, []) if a["status"] == "active" or a.get("eliminated_week") == week]
    scores = latest_scores(d)
    picks = [p for p in read_ledger(d, "picks") if p["team"] == team and iso_week(date.fromisoformat(p["round_date"])) == week]
    rows = []
    for a in members:
        mine = [p for p in picks if p["agent_id"] == a["id"]]
        vals = [scores[p["pick_id"]]["score"] for p in mine
                if p["pick_id"] in scores and scores[p["pick_id"]]["status"] == "final"]
        held = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") in ("held", "pending", "provisional", None))
        void = sum(1 for p in mine if scores.get(p["pick_id"], {}).get("status") == "void")
        rows.append({"agent_id": a["id"], "label": a["label"], "version": a.get("version", 1),
                     "picks": len(mine), "scored": len(vals), "held_or_pending": held, "void": void,
                     "avg": round(statistics.mean(vals), 2) if vals else None,
                     "median": round(statistics.median(vals), 2) if vals else None,
                     "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                     "sum": round(sum(vals), 2) if vals else 0.0, "new_this_week": a.get("joined_week") == week})
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
    bench = roster.get("bench", [])
    decision["replacement"] = bench[0]["id"] if decision["eliminate"] and bench else None
    return {"week": week, "team": team, "ranking": rows, "decision": decision}

# ───────────────────────── 팀 비교 ─────────────────────────

def team_summary(d: Path) -> dict:
    scores = latest_scores(d)
    out = {}
    for p in read_ledger(d, "picks"):
        s = scores.get(p["pick_id"])
        t = out.setdefault(p["team"], {"daily": {}, "markets": {"KR": [], "US": []}, "all": []})
        if s and s["status"] == "final":
            t["daily"].setdefault(p["round_date"], []).append(s["score"])
            t["markets"][p["market"]].append(s["score"])
            t["all"].append(s["score"])
    res = {}
    for team, t in out.items():
        days = sorted(t["daily"])
        cum, series = 0.0, []
        for dd in days:
            daysum = round(sum(t["daily"][dd]), 2); cum = round(cum + daysum, 2)
            series.append({"date": dd, "sum": daysum, "cumulative": cum, "n": len(t["daily"][dd])})
        res[team] = {"cumulative": cum, "avg": round(statistics.mean(t["all"]), 2) if t["all"] else None,
                     "scored": len(t["all"]), "series": series,
                     "markets": {m: {"avg": round(statistics.mean(v), 2) if v else None, "scored": len(v), "sum": round(sum(v), 2)}
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
    if any(p["agent_id"] == rec["agent_id"] for p in same):
        errs.append(f"{rec['agent_id']}는 이 라운드에 이미 추천함")
    if len({p["agent_id"] for p in same} | {rec["agent_id"]}) > cfg["agents_per_team"]:
        errs.append(f"팀 인원 {cfg['agents_per_team']}명 초과")
    return errs

def make_pick(team, agent_id, agent_version, round_date, market, ticker, name, locked_at,
              rationale, risks, sources, cfg, snapshot_sha256=None, agent_label=None) -> dict:
    rd = date.fromisoformat(round_date)
    rs = round_sessions(market, rd, cfg)
    return {"pick_id": f"{round_date}-{team}-{agent_id}", "team": team, "agent_id": agent_id,
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
    """CSV 열: round_date,agent_id,market,ticker,name,locked_at,rationale,risks,sources
    risks는 ' | '로 구분, sources는 'url|기준일;url|기준일'. 가격은 입력받지 않는다 (공통 가격 원장 사용)."""
    cfg = load_config(d)
    ok, bad = [], []
    existing = read_ledger(d, "picks")
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), 2):
            srcs = [dict(zip(("url", "as_of"), s.split("|"))) for s in (row.get("sources") or "").split(";") if s.strip()]
            rec = make_pick(team, row["agent_id"].strip(), None, row["round_date"].strip(), row["market"].strip().upper(),
                            row["ticker"].strip(), row.get("name", "").strip(), row["locked_at"].strip(),
                            row.get("rationale", ""), [r.strip() for r in (row.get("risks") or "").split("|") if r.strip()],
                            srcs, cfg)
            errs = validate_pick(rec, d, cfg, existing + ok)
            if not srcs:
                errs.append("데이터 출처(sources) 없음")
            (bad if errs else ok).append({"line": i, "pick": rec, "errors": errs} if errs else rec)
    if not dry_run and not bad:
        for rec in ok:
            append(d, "picks", rec)
    return ok, bad

# ───────────────────────── 화면용 내보내기 ─────────────────────────

def export(d: Path, out: Path):
    cfg = load_config(d)
    picks = read_ledger(d, "picks")
    weeks = sorted({iso_week(date.fromisoformat(p["round_date"])) for p in picks})
    roster = json.loads((d / "agents" / "roster.json").read_text()) if (d / "agents" / "roster.json").exists() \
        else json.loads((ROOT / "league" / "agents" / "roster.json").read_text())
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
        append(d, "prices", {"market": m, "ticker": t, "session": s, "close": close, "split_factor": 1.0,
                             "cash_dividend_exdate": 0.0, "halted": False, "source": "SAMPLE", "status": "final",
                             "fetched_at": f"{s}T18:00:00+09:00", **kw})
    agents = {"claude": [a["id"] for a in roster["claude"]], "shushu": [a["id"] for a in roster["shushu"]]}
    skill = {"buffett": .25, "lynch": .1, "dalio": 0, "wood": -.1, "burry": -.35, "s1": .2, "s2": 0, "s3": .05, "s4": -.2, "s5": .1}
    # 예외 사례 전용 종목 (다른 추천과 가격이 섞이지 않도록 무작위 선택에서 제외)
    special_cases = {
        ("claude", "lynch", 11): ("US", "KO", "split"),        # 평가일 1→4 분할
        ("claude", "dalio", 12): ("KR", "105560", "dividend"), # 평가일 배당락
        ("shushu", "s4", 13): ("KR", "068270", "halt"),        # 평가일 거래정지 → 다음 세션 지연 채점
        ("claude", "wood", 13): ("US", "JPM", "missing"),      # 평가 종가 누락 → 보류
    }
    reserved = {(m, t) for m, t, _ in special_cases.values()}
    dec = lambda m: 2 if m == "US" else -1
    for rd in days:
        for team, ids in agents.items():
            for aid in ids:
                case = special_cases.get((team, aid, rd.day))
                if case:
                    m, t, kind = case
                else:
                    kind = None
                    m = rnd.choice(["KR", "US"])
                    if not round_sessions(m, rd, cfg):
                        m = "KR" if m == "US" else "US"
                    t = rnd.choice(sorted(x for x in uni[m] if (m, x) not in reserved))
                rec = make_pick(team, aid, 1, rd.isoformat(), m, t, uni[m][t],
                                f"{rd.isoformat()}T08:{rnd.randint(5, 29):02d}:00+09:00",
                                f"[예시] {uni[m][t]} 선정 근거 요약", ["[예시] 실적 하회 위험", "[예시] 환율 변동"],
                                [{"title": "예시 출처", "url": "https://example.com", "as_of": prev_session(m, rd, cfg).isoformat()}],
                                cfg, agent_label=aid)
                bs, es = rec["base_session"], rec["eval_session"]
                b = base_px[(m, t)]
                put_price(m, t, bs, b)
                close = round(b * (1 + rnd.gauss(skill[aid] / 100, 0.018)), dec(m))
                if kind == "split":
                    put_price(m, t, es, round(close / 4, dec(m)), split_factor=4.0)
                elif kind == "dividend":
                    div = round(b * 0.01, 0)
                    put_price(m, t, es, round(close - div, dec(m)), cash_dividend_exdate=div)
                elif kind == "halt":
                    put_price(m, t, es, None, halted=True)
                    put_price(m, t, next_session(m, date.fromisoformat(es), cfg).isoformat(), round(b * 0.985, dec(m)))
                elif kind != "missing":
                    put_price(m, t, es, close)
                    base_px[(m, t)] = close
                submit_pick(d, rec)
    # 금요일(11/13) 미국분 일부는 아직 잠정 상태로 남기기 위해 채점 기준일을 11/16(월) 아침으로
    run_scoring(d, today=date(2026, 11, 16), now="2026-11-16T07:00:00+09:00")

# ───────────────────────── CLI ─────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["verify", "score", "weekly", "import-csv", "sample", "export"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--dir", default=str(ROOT / "league"))
    ap.add_argument("--team", default="claude")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out")
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
    elif a.cmd == "export":
        out = Path(a.out or (ROOT / "data" / "league.js"))
        export(d, out)
        print(f"내보내기: {out}")

if __name__ == "__main__":
    main()
