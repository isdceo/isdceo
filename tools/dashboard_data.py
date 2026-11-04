#!/usr/bin/env python3
"""운영자 전용 현황판(비공개 Artifact)에 올릴 데이터 파일을 만든다.

  python3 tools/dashboard_data.py --out <폴더>

- 실전(league)과 연습(league/sandbox) 원장을 모두 읽는다.
- 종목·점수는 export()와 같은 규칙을 쓴다: 라운드 마감(08:30 KST) 전 추천은 넣지 않고, 원시 가격은 빼고 점수(%)만 남긴다.
- 만드는 파일: checklist, receipts, teams, standings, team_daily, picks, notices (각각 {"rows": [...]} JSON)
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

MODES = (("실전", L.ROOT / "league"), ("연습", L.ROOT / "league" / "sandbox"))
TEAM_LABEL = {"claude": "Claude 팀", "shushu": "슈슈 팀 (Codex)"}


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


def build(now: datetime | None = None) -> dict:
    now = now or datetime.now(L.KST)
    out = {k: [] for k in ("checklist", "receipts", "teams", "standings", "team_daily", "picks")}

    state = {"done": "완료", "todo": "남음", "manual": "확인 필요"}
    for r in L.readiness(L.ROOT / "league"):
        out["checklist"].append({"state": state[r["status"]], "area": r["area"], "item": r["item"],
                                 "detail": r["detail"], "who": r["who"]})

    for mode, d in MODES:
        if not (d / "ledger").exists():
            continue
        data = _load(d, now)
        scores = {s["pick_id"]: s for s in data["scores"]}

        for s in data["submissions"]:
            out["receipts"].append({"key": s["commit"][:7] + "|" + s["round_date"] + "|" + s["team"],
                                    "mode": mode, "team": label(s["team"]), "round": s["round_date"],
                                    "status": s["status"], "pushed_at": s["pushed_at"], "commit": s["commit"][:7],
                                    "imported": s.get("imported", 0)})

        for p in data["picks"]:
            if team_of(p["team"]) not in TEAM_LABEL:      # 옛 공용 시험(sandbox) 기록은 제외
                continue
            s = scores.get(p["pick_id"], {})
            out["picks"].append({"pick_id": p["pick_id"], "mode": mode, "round_date": p["round_date"],
                                 "team": label(p["team"]), "agent": p.get("agent_label") or p["agent_id"],
                                 "market": p["market"], "ticker": p["ticker"], "name": p.get("name") or "",
                                 "status": s.get("status") or "pending", "score": s.get("score"),
                                 "score_price_only": s.get("score_price_only"), "score_excess": s.get("score_excess"),
                                 "reason": s.get("reason") or ""})

        for team, t in data["teams"].items():
            for x in t["series"]:
                out["team_daily"].append({"key": f"{mode}|{team}|{x['date']}", "mode": mode, "team": label(team),
                                          "date": x["date"], "sum": x["sum"], "cumulative": x["cumulative"], "n": x["n"]})

        for team, weeks in (data["weekly"].items() if mode == "실전" else ()):   # 주간 순위는 실전만
            for wk, w in weeks.items():
                for r in w["ranking"]:
                    out["standings"].append({"key": f"{mode}|{team}|{wk}|{r['agent_id']}", "mode": mode,
                                             "team": label(team), "week": wk, "rank": r["rank"], "agent": r["label"],
                                             "picks": r["picks"], "expected": r["expected"], "scored": r["scored"],
                                             "avg": r["avg"], "median": r["median"], "avg_excess": r["avg_excess"],
                                             "submit_rate": r["submit_rate"]})

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
    out["notices"] = [{"file": f.name} for f in sorted((L.ROOT / "docs" / "codex-notices").glob("*.md"), reverse=True)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in build().items():
        (out / f"{name}.json").write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1))
        print(f"{name}: {len(rows)}행")


if __name__ == "__main__":
    main()
