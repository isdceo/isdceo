"""표본 관찰판 (개선안 docs/proposals/2026-11-18-sample-and-pbeat-observation.md 2장, 시범 도구).

원장을 **읽기만** 한다. 점수·순위·탈락·제출 판정·화면에 영향이 없다. 지침을 자동으로 바꾸지 않는다.
두 팀을 같은 정의로 집계한다.

- 두 축: 선택 유형(real 실제 종목 / watch 관망) × 채점 상태(final 확정 / pending 채점 대기 / held 보류 / void 무효).
  확정된 관망은 한 칸에만 들어간다.
- 미제출은 따로 센다: 지문 마감이 지난 라운드 중 그 시장이 실제로 열렸고, 그 에이전트가 그 리그 출전 명단(당시 주 기준)에
  있었는데 종목이 없을 때 1건. 운영 장애 기록(outages)이 있으면 그 건수도 따로 보인다.
- 채점 규칙 구간(regime): 관망 채점 규칙이 다르면 같은 지침 버전이라도 나눈다
  (watch_index = 지수 수익률 관망, watch_cash = v2.2 0% 관망. `round_snapshot`의 고정값 기준).
- 정정(correction_of)은 최신 값으로 반영하고 정정 건수는 따로 보인다.
- 주간 표는 실제 건수만, 누적 표에는 표본 구간(<10, 10-29, 30+)을 함께 표시한다. 구간은 신뢰도를 보장하지 않는다.

사용:
  python3 tools/sample_board.py                      # 누적 + 최근 주
  python3 tools/sample_board.py --week 2026-W47      # 그 주
  python3 tools/sample_board.py --json out.json --md out.md
  python3 tools/sample_board.py --at 2026-11-23T06:30:00+09:00   # 집계 기준 시각(두 팀 같은 시각으로)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

START = "2026-11-09"            # 실전 시작(지문 방식 첫 라운드)
STATUS = ("final", "pending", "held", "void")


def _status(score: dict | None) -> str:
    st = (score or {}).get("status")
    if st == "final":
        return "final"
    if st == "void":
        return "void"
    if st == "held":
        return "held"
    return "pending"             # 점수 없음·provisional·pending은 채점 대기


def band(n: int) -> str:
    return "<10" if n < 10 else ("10-29" if n < 30 else "30+")


def regime(rd: str, cfg: dict, d: Path) -> str:
    return "watch_cash" if L.watch_is_cash(rd, cfg, d) else "watch_index"


def collect(d: Path, at: datetime, start: str = START) -> dict:
    cfg = L.load_config(d)
    roster = L.load_roster(d)
    scores = L.latest_scores(d)
    corrections = defaultdict(int)
    for s in L.read_ledger(d, "scores"):
        if s.get("correction_of"):
            corrections[s["pick_id"]] += 1
    outages = {(o["team"], o["round_date"], o.get("agent_id")) for o in L.read_ledger(d, "outages")}
    picks = [p for p in L.read_ledger(d, "picks") if p["round_date"] >= start
             and L.lock_deadline(date.fromisoformat(p["round_date"]), cfg) <= at]
    have = {(p["team"], p["agent_id"], p["market"], p["round_date"]) for p in picks}

    rows = []                    # 종목 1건 = 1행
    for p in picks:
        sc = scores.get(p["pick_id"])
        rows.append({"team": p["team"], "agent_id": p["agent_id"], "market": p["market"], "version": p.get("agent_version"),
                     "round_date": p["round_date"], "week": L.iso_week(date.fromisoformat(p["round_date"])),
                     "regime": regime(p["round_date"], cfg, d),
                     "type": "watch" if L.is_watch(p, cfg) else "real", "status": _status(sc),
                     "score": sc.get("score") if sc and sc.get("status") == "final" else None,
                     "corrections": corrections.get(p["pick_id"], 0)})

    missed = []                  # 미제출 1건 = 1행
    day = date.fromisoformat(start)
    while L.lock_deadline(day, cfg) <= at:
        wk = L.iso_week(day)
        for mk in sorted(L.open_markets(day, cfg)):
            for team, members in roster.items():
                if team not in cfg.get("teams", {}):
                    continue
                for a in members:
                    on = L.active_in(a, mk, wk) and L.mstatus(a, mk).get("status") != "bench"
                    if not on or (team, a["id"], mk, day.isoformat()) in have:
                        continue
                    out = any((team, day.isoformat(), x) in outages for x in (None, a["id"]))
                    missed.append({"team": team, "agent_id": a["id"], "market": mk, "round_date": day.isoformat(),
                                   "week": wk, "regime": regime(day.isoformat(), cfg, d), "outage": out})
        day += timedelta(days=1)
    return {"rows": rows, "missed": missed}


def summarize(data: dict, week: str | None = None) -> list[dict]:
    """팀 × 에이전트 × 시장 × 지침 버전 × 채점 규칙 구간마다 1줄."""
    g = defaultdict(lambda: {"cells": defaultdict(int), "rounds": set(), "finals": [], "corrections": 0,
                             "missed": 0, "missed_outage": 0, "versions": set()})
    for r in data["rows"]:
        if week and r["week"] != week:
            continue
        k = (r["team"], r["agent_id"], r["market"], r["version"], r["regime"])
        x = g[k]
        x["cells"][f"{r['type']}_{r['status']}"] += 1
        x["rounds"].add(r["round_date"])
        x["corrections"] += r["corrections"]
        if r["status"] == "final" and r["score"] is not None:
            x["finals"].append(r["score"])
    for m in data["missed"]:
        if week and m["week"] != week:
            continue
        ks = [k for k in g if k[:3] == (m["team"], m["agent_id"], m["market"]) and k[4] == m["regime"]]
        k = ks[-1] if ks else (m["team"], m["agent_id"], m["market"], None, m["regime"])   # 버전은 그 구간의 마지막 버전에 붙인다
        g[k]["missed"] += 1
        g[k]["missed_outage"] += int(m["outage"])
    out = []
    for (team, agent, mk, ver, reg), x in sorted(g.items(), key=lambda kv: tuple(str(v) for v in kv[0])):
        cells = {f"{t}_{s}": x["cells"].get(f"{t}_{s}", 0) for t in ("real", "watch") for s in STATUS}
        n_final = cells["real_final"] + cells["watch_final"]
        out.append({"team": team, "agent_id": agent, "market": mk, "version": ver, "regime": reg, **cells,
                    "submitted": sum(cells.values()), "missed": x["missed"], "missed_outage": x["missed_outage"],
                    "rounds": len(x["rounds"]), "final": n_final,
                    "avg": round(statistics.mean(x["finals"]), 2) if x["finals"] else None,
                    "median": round(statistics.median(x["finals"]), 2) if x["finals"] else None,
                    "corrections": x["corrections"], "band": None if week else band(n_final)})
    return out


def to_md(rows: list[dict], title: str) -> str:
    head = ("| 팀 | 에이전트 | 시장 | 버전 | 구간 | 종목 확정 | 종목 대기 | 종목 보류 | 관망 확정 | 관망 대기 | 무효 | 미제출(장애) | "
            "라운드 | 확정 평균 | 중앙값 | 정정 | 표본 구간 |")
    lines = [f"### {title}", "", head, "|" + "---|" * 17]
    for r in rows:
        lines.append(f"| {r['team']} | {r['agent_id']} | {r['market']} | {r['version']} | {r['regime']} | {r['real_final']} | "
                     f"{r['real_pending']} | {r['real_held']} | {r['watch_final']} | {r['watch_pending'] + r['watch_held']} | "
                     f"{r['real_void'] + r['watch_void']} | {r['missed']}({r['missed_outage']}) | {r['rounds']} | "
                     f"{'' if r['avg'] is None else r['avg']} | {'' if r['median'] is None else r['median']} | {r['corrections']} | "
                     f"{r['band'] or '—'} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="표본 관찰판(읽기 전용, 점수 영향 없음)")
    ap.add_argument("--dir", default=str(L.ROOT / "league"))
    ap.add_argument("--week", help="이 주만(실제 건수). 없으면 누적 + 가장 최근 주")
    ap.add_argument("--at", help="집계 기준 시각(ISO, +09:00). 기본: 지금")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args()
    d = Path(a.dir)
    at = datetime.fromisoformat(a.at) if a.at else datetime.now(L.KST)
    data = collect(d, at)
    weeks = sorted({r["week"] for r in data["rows"]} | {m["week"] for m in data["missed"]})
    wk = a.week or (weeks[-1] if weeks else None)
    res = {"at": at.isoformat(timespec="seconds"), "note": "관찰 전용. 점수·순위·판정·지침에 쓰지 않는다. 표본 구간은 신뢰도를 보장하지 않는다.",
           "week": wk, "weekly": summarize(data, wk) if wk else [], "cumulative": [] if a.week else summarize(data)}
    md = f"기준 시각 {res['at']} · {res['note']}\n\n"
    if wk:
        md += to_md(res["weekly"], f"주간 {wk} (실제 건수)") + "\n"
    if not a.week:
        md += to_md(res["cumulative"], f"누적 {START}~ (표본 구간 표시)")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    if a.md:
        Path(a.md).write_text(md)
    if not (a.json or a.md):
        print(md)


if __name__ == "__main__":
    main()
