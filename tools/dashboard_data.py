#!/usr/bin/env python3
"""운영자 전용 현황판(비공개 Artifact)에 올릴 데이터 파일을 만든다.

  python3 tools/dashboard_data.py --out <폴더>

- 실전(league)과 연습(league/sandbox) 원장을 모두 읽는다.
- 종목·점수는 export()와 같은 규칙을 쓴다: 라운드 마감(08:30 KST) 전 추천은 넣지 않고, 원시 가격은 빼고 점수(%)만 남긴다.
- 만드는 파일: checklist, receipts, teams, standings, team_daily, picks, notices, agents, team_weeks, calendar(라운드 날짜·휴장), logos(--out 에서만, 공개 종목의 회사 로고) (각각 {"rows": [...]} JSON)
"""
import argparse, json, re, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

LEAGUE = L.ROOT / "league"


def modes(base: Path):
    """(구분, 원장 폴더). 실전은 base, 연습은 base/sandbox."""
    return (("실전", base), ("연습", base / "sandbox"))
TEAM_LABEL = {"claude": "로로 팀 (Claude)", "shushu": "슈슈 팀 (Codex)"}   # 화면·결과 파일의 팀 이름 (애칭 팀 (모델))


def team_of(t: str) -> str:
    """sandbox-claude → claude. 'sandbox'(옛 공용 연습)는 그대로."""
    return t.split("sandbox-", 1)[1] if t.startswith("sandbox-") else t


def label(t: str) -> str:
    return TEAM_LABEL.get(team_of(t), t)


def _load(d: Path, now: datetime) -> dict:
    tmp = Path(L.ROOT / ".dashboard_tmp.js")
    try:
        L.export(d, tmp, public=True, now=now)
        return json.loads(tmp.read_text().split("window.LEAGUE = ", 1)[1].rstrip().rstrip(";"))
    finally:
        tmp.unlink(missing_ok=True)


PRICE_LIKE = re.compile(r"[$₩]\s*\d|\d[\d,.]*\s*(원|달러|만원|억원|조원)|종가|목표주가")


def load_lines(d: Path) -> dict:
    """<원장>/lines/*.json — 종목별 한 줄 선택 이유(캐릭터 말투, 가격 숫자 없이). {pick_id: 문장}
    팀마다 따로 쓴다: <라운드>-<팀>.json (예: lines/2026-11-09-claude.json). 예전 파일 <라운드>.json 도 읽는다.
    마감 뒤 공개된 종목에만 붙는다(picks 가 이미 마감 전 종목을 뺀다). 가격처럼 보이는 문장·80자 초과는 버린다."""
    out = {}
    for f in sorted((d / "lines").glob("*.json")):
        for k, v in json.loads(f.read_text()).items():
            v = " ".join(str(v).split())
            if v and len(v) <= 80 and not PRICE_LIKE.search(v):
                out[k] = v
    return out


def check_lines(path: Path, base: Path | None = None, now: datetime | None = None) -> list[str]:
    """한 줄 이유 파일 검사. 문제 목록을 돌려준다(빈 목록이면 통과).
    - 파일 이름 <라운드>-<팀>.json, 내용 {pick_id: 문장}
    - pick_id 가 원장의 그 라운드·그 팀 종목이어야 한다(다른 팀 종목에 대사를 쓰지 않는다)
    - 라운드 마감(08:30 KST)이 지난 뒤에만 쓴다
    - 문장: 비어 있지 않음, 80자 이하, 가격처럼 보이는 표현(₩·$·원·달러·종가·목표주가) 없음"""
    path = Path(path)
    base = Path(base or LEAGUE)
    now = now or datetime.now(L.KST)
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-([a-z-]+)\.json", path.name)
    if not m:
        return [f"파일 이름은 <라운드>-<팀>.json 이어야 함: {path.name}"]
    rd, team = m.groups()
    from datetime import date as _date
    errs = []
    if now < L.lock_deadline(_date.fromisoformat(rd), L.load_config(base)):
        errs.append(f"{rd} 라운드 마감(08:30 KST) 전에는 쓰지 않는다")
    try:
        lines = json.loads(path.read_text())
    except Exception as e:
        return errs + [f"JSON 읽기 실패: {e}"]
    if not isinstance(lines, dict) or not lines:
        return errs + ["{pick_id: 문장} 형태의 내용이 없음"]
    ids = {p["pick_id"] for p in L.read_ledger(base, "picks") if p["round_date"] == rd and p["team"] == team}
    if not ids:
        errs.append(f"원장에 {rd} {team} 종목이 없음 (원본 공개 뒤 영수증이 accepted 인지 확인)")
    for k, v in lines.items():
        if k not in ids:
            errs.append(f"{k}: 이 라운드·이 팀의 종목이 아님")
        v = " ".join(str(v).split())
        if not v:
            errs.append(f"{k}: 문장이 비어 있음")
        elif len(v) > 80:
            errs.append(f"{k}: 80자 초과({len(v)}자)")
        elif PRICE_LIKE.search(v):
            errs.append(f"{k}: 가격처럼 보이는 표현이 있음 — {v}")
    missing = sorted(ids - set(lines))
    if ids and missing:
        errs.append("한 줄 이유가 없는 종목: " + ", ".join(missing))
    return errs


def build(now: datetime | None = None, logos: bool = False, base: Path | None = None) -> dict:
    """base: 실전 원장 폴더(기본 league/). 연습은 base/sandbox."""
    now = now or datetime.now(L.KST)
    base = Path(base or LEAGUE)
    out = {k: [] for k in ("checklist", "receipts", "teams", "standings", "team_daily", "picks", "agents", "team_weeks")}

    names = {}                                            # (팀, id) → 스타일명 (예: claude, buffett → 가치형)
    for key, members in L.load_roster(base).items():
        team = "claude" if key == "bench" else key.replace("bench_", "")
        for m in members:
            lbl = m.get("label") or m["id"]
            names[(team, m["id"])] = f'{m["nickname"]} · {lbl}' if m.get("nickname") else lbl

    # 에이전트 프로필 (애칭을 누르면 열리는 카드). 승인된 대기 후보만 싣는다.
    approved = {(x["team"], x["agent_id"]) for x in L.read_ledger(base, "approvals")
                if x.get("type") == "bench" and x.get("decision") == "approved"}
    for key, members in L.load_roster(base).items():
        team = "claude" if key == "bench" else key.replace("bench_", "")
        if team not in TEAM_LABEL:
            continue
        bench = key.startswith("bench")
        for i, m in enumerate(members, 1):
            if bench and (team, m["id"]) not in approved:
                continue
            status = (f"대기 {i}순위" if bench else
                      "탈락" if m.get("status") == "eliminated" else "현역")
            out["agents"].append({"key": f"{TEAM_LABEL[team]}|{names[(team, m['id'])]}", "team": TEAM_LABEL[team],
                                  "agent_id": m["id"], "name": names[(team, m["id"])],
                                  "nickname": m.get("nickname") or "", "label": m.get("label") or m["id"],
                                  "tagline": m.get("tagline") or "", "avatar": m.get("avatar") or "", "status": status,
                                  "version": m.get("version", 1), "joined_week": m.get("joined_week") or "",
                                  "eliminated_week": m.get("eliminated_week") or ""})

    state = {"done": "완료", "todo": "남음", "manual": "확인 필요"}
    for r in L.readiness(base):
        out["checklist"].append({"state": state[r["status"]], "area": r["area"], "item": r["item"],
                                 "detail": r["detail"], "who": r["who"]})

    for mode, d in modes(base):
        if not (d / "ledger").exists():
            continue
        data = _load(d, now)
        scores = {s["pick_id"]: s for s in data["scores"]}

        for s in data["submissions"]:
            out["receipts"].append({"key": s["commit"][:7] + "|" + s["round_date"] + "|" + s["team"],
                                    "mode": mode, "team": label(s["team"]), "round": s["round_date"],
                                    "kind": s.get("kind") or "csv",
                                    "status": s["status"], "pushed_at": s["pushed_at"], "commit": s["commit"][:7],
                                    "imported": s.get("imported", 0)})

        lines = load_lines(d)
        cfg_w = L.load_config(d)
        for p in data["picks"]:
            if team_of(p["team"]) not in TEAM_LABEL:      # 옛 공용 시험(sandbox) 기록은 제외
                continue
            s = scores.get(p["pick_id"], {})
            out["picks"].append({"pick_id": p["pick_id"], "mode": mode, "round_date": p["round_date"],
                                 "team": label(p["team"]), "agent_id": p["agent_id"],
                                 "agent": names.get((team_of(p["team"]), p["agent_id"])) or p.get("agent_label") or p["agent_id"],
                                 "market": p["market"], "ticker": p["ticker"], "name": p.get("name") or "",
                                 "status": s.get("status") or "pending", "score": s.get("score"),
                                 "score_price_only": s.get("score_price_only"), "score_excess": s.get("score_excess"),
                                 "reason": s.get("reason") or "", "line": lines.get(p["pick_id"], ""),
                                 "watch": L.is_watch(p, cfg_w)})

        for team, t in data["teams"].items():
            for x in t["series"]:
                out["team_daily"].append({"key": f"{mode}|{team}|{x['date']}", "mode": mode, "team": label(team),
                                          "date": x["date"], "sum": x["sum"], "cumulative": x["cumulative"], "n": x["n"],
                                          "avg": x.get("avg"), "cum_avg": x.get("cum_avg"), "cum_n": x.get("cum_n")})

        if mode == "실전":                       # 주간 순위: 두 팀 10명 통합 (규칙 v1.8)
            weeks = sorted({L.iso_week(datetime.fromisoformat(p["round_date"]).date()) for p in data["picks"]})
            for wk in weeks:
                lg = L.weekly_league(d, wk)
                dec = lg["decision"]
                for r in lg["ranking"]:
                    out["standings"].append({"key": f"{mode}|{wk}|{r['team']}|{r['agent_id']}", "mode": mode, "week": wk,
                                             "league_rank": r["league_rank"], "rank": r["team_rank"],
                                             "team": label(r["team"]), "agent_id": r["agent_id"],
                                             "agent": names.get((r["team"], r["agent_id"]), r["label"]),
                                             "avg": r["avg"], "median": r["median"], "avg_excess": r["avg_excess"],
                                             "scored": r["scored"], "picks": r["picks"], "expected": r["expected"],
                                             "missed": r["missed"], "held": r["held_or_pending"], "submit_rate": r["submit_rate"],
                                             "closed": bool(dec.get("closed_at")),
                                             "out": "탈락" if (dec.get("closed_at") and dec["eliminate_team"] == r["team"]
                                                            and dec["eliminate"] == r["agent_id"]) else ""})   # 주간 마감 뒤에만
                for team, t in lg["teams"].items():
                    out["team_weeks"].append({"key": f"{mode}|{wk}|{team}", "mode": mode, "week": wk, "team": label(team),
                                              "avg": t["avg"], "scored": t["scored"], "picks": t["picks"],
                                              "expected": t["expected"], "held": t["held_or_pending"],
                                              "hold": " / ".join(dec["hold_reasons"])})

    # 팀 요약: 모드·팀별 마지막 영수증
    last = {}
    for r in out["receipts"]:
        if r["team"] in TEAM_LABEL.values():
            last[(r["mode"], r["team"])] = r
    picks_n = {}
    for p in out["picks"]:
        picks_n[(p["mode"], p["team"], p["round_date"])] = picks_n.get((p["mode"], p["team"], p["round_date"]), 0) + 1
    for (mode, team), r in sorted(last.items()):
        out["teams"].append({"key": f"{mode}|{team}", "mode": mode, "team": team, "round": r["round"],
                             "status": r["status"], "pushed_at": r["pushed_at"], "imported": r["imported"],
                             "visible_picks": picks_n.get((mode, team, r["round"]), 0)})
    if logos:   # 공개된(마감이 지난) 종목만. 운영자 전용 현황판용, 공유 결과 묶음에는 넣지 않는다
        import logos as LG
        seen = sorted({(p["market"], p["ticker"]) for p in out["picks"] if not p.get("watch")})
        out["logos"] = [{"key": f"{m}|{t}", "market": m, "ticker": t, "logo": LG.fetch_logo(m, t) or ""} for m, t in seen]
    out["calendar"] = calendar(now, base=base)
    out["notices"] = [{"file": f.name} for f in sorted((L.ROOT / "docs" / "codex-notices").glob("*.md"), reverse=True)]
    return out


def calendar(now: datetime, back: int = 14, ahead: int = 45, base: Path | None = None) -> list[dict]:
    """라운드가 열리는 날(한국·미국 중 하나라도 거래일)과 마감·채점 시각. 현황판 진행 표시용.
    채점은 다음 날 10:30 KST 수집·채점(월~토)에서 한다: 평가 세션이 라운드 당일 종가이기 때문."""
    cfg = L.load_config(Path(base or LEAGUE))
    rows, today = [], now.astimezone(L.KST).date()
    for i in range(-back, ahead + 1):
        d = today + timedelta(days=i)
        kr, us = L.is_session("KR", d, cfg), L.is_session("US", d, cfg)
        if not (kr or us):
            continue
        dl = L.lock_deadline(d, cfg)
        rows.append({"key": d.isoformat(), "date": d.isoformat(), "kr": kr, "us": us,
                     "markets": "한국·미국" if kr and us else "한국만 (미국 휴장)" if kr else "미국만 (한국 휴장)",
                     "deadline": dl.isoformat(timespec="minutes"),
                     "reveal_until": dl.replace(hour=12, minute=0).isoformat(timespec="minutes"),
                     "score_at": (dl + timedelta(days=1)).replace(hour=10, minute=30).isoformat(timespec="minutes")})
    return rows


BUNDLE_KEYS = ("receipts", "teams", "standings", "team_daily", "team_weeks", "picks", "agents", "calendar")
BUNDLE_SCHEMA = 1


def bundle(now: datetime | None = None, base: Path | None = None) -> dict:
    """두 팀 공유용 결과 묶음 (league/public/results.json).
    마감(08:30 KST) 전 라운드 종목·점수와 원 가격은 들어가지 않는다. 섞이면 만들지 않고 실패한다."""
    now = now or datetime.now(L.KST)
    base = Path(base or LEAGUE)
    data = build(now, base=base)
    out = {"schema": BUNDLE_SCHEMA, "generated_at": now.isoformat(timespec="seconds"),
           "rules": {"embargo": "각 라운드 마감(08:30 KST)이 지난 뒤에만 종목·점수를 싣는다",
                     "prices": "원 가격(종가·배당 금액)은 싣지 않고 점수(%)만 싣는다",
                     "scores": "status가 final인 점수만 확정. provisional은 잠정, pending·held는 미채점"}}
    out.update({k: data[k] for k in BUNDLE_KEYS})
    cfg = L.load_config(base)
    early = [p["pick_id"] for p in out["picks"]
             if now < L.lock_deadline(datetime.fromisoformat(p["round_date"]).date(), cfg)]
    if early:
        raise RuntimeError(f"마감 전 종목이 결과 묶음에 섞임: {early}")
    text = json.dumps(out, ensure_ascii=False)
    if re.search(r'"(base_close|eval_close|close|amount)"\s*:', text):
        raise RuntimeError("원 가격 필드가 결과 묶음에 섞임")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="현황판용 파일 폴더 (dataset마다 하나)")
    ap.add_argument("--bundle", help="두 팀 공유용 결과 묶음 파일 경로 (예: league/public/results.json)")
    ap.add_argument("--no-logos", action="store_true", help="--out 에서 회사 로고(logos.json)를 받지 않는다")
    ap.add_argument("--check-lines", metavar="FILE", help="한 줄 이유 파일 검사 (예: league/lines/2026-11-09-claude.json)")
    ap.add_argument("--base", help="--check-lines 의 원장 폴더 (기본 league/, 연습은 league/sandbox)")
    a = ap.parse_args()
    if a.check_lines:
        errs = check_lines(Path(a.check_lines), Path(a.base) if a.base else None)
        for e in errs:
            print("문제:", e)
        print("통과" if not errs else f"문제 {len(errs)}건")
        sys.exit(1 if errs else 0)
    if not (a.out or a.bundle):
        ap.error("--out 또는 --bundle 이 필요하다")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in build(logos=not a.no_logos).items():
            (out / f"{name}.json").write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1))
            print(f"{name}: {len(rows)}행")
    if a.bundle:
        p = Path(a.bundle)
        p.parent.mkdir(parents=True, exist_ok=True)
        b = bundle()
        p.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n")
        print(f"결과 묶음: {p} ({b['generated_at']}, " + ", ".join(f"{k} {len(b[k])}" for k in BUNDLE_KEYS) + ")")


if __name__ == "__main__":
    main()
