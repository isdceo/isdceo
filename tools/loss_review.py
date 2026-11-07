"""손실 복기 — 로로 팀 종목이 확정 마이너스 점수를 받으면 그 종목을 고른 에이전트가 스스로 원인을 분석한다.

  python3 tools/loss_review.py due [--dir league] [--json]      → 아직 복기가 없는 마이너스 확정 종목
  python3 tools/loss_review.py check <복기 파일>...              → 형식·금지 표현 검사
  python3 tools/loss_review.py list [--dir league] [--week 2026-W46] → 작성된 복기 목록(주간 복기 입력)

복기 파일: league/reviews/losses/<라운드>/<에이전트>-<시장>.md (연습은 league/sandbox/reviews/losses/…)
- 확정(final) 점수만 대상이다. 잠정·보류·무효와 관망(지수 추종)은 제외한다.
- 복기는 기록일 뿐 지침을 바꾸지 않는다. 바꿀 점은 주간 복기(league-review)가 모아 운영자 승인 절차로 올린다.
- 원 가격(₩·$·원·달러 금액)은 쓰지 않는다. 수익률(%)·지수 대비(%p)만 쓴다.
"""
from __future__ import annotations

import argparse, json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

TEAM = "claude"
VERDICTS = ("분석 실수", "시장 전체 움직임", "구간 밖 사건", "예측 못한 새 소식", "운·잡음")
SECTIONS = ("## 1. 그때의 논리", "## 2. 실제로 무슨 일이 있었나", "## 3. 판정", "## 4. 놓친 신호·틀린 가정", "## 5. 다음에 바꿀 점")
MONEY = re.compile(r"[$₩]\s*\d|\d[\d,.]*\s*(원|달러|만원|억원|조원)(?![가-힣])|목표\s*주가")


def review_dir(d: Path) -> Path:
    return d / "reviews" / "losses"


def review_path(d: Path, p: dict) -> Path:
    return review_dir(d) / p["round_date"] / f"{p['agent_id']}-{p['market']}.md"


def due(d: Path) -> list[dict]:
    cfg = L.load_config(d)
    scores = L.latest_scores(d)
    roster = L.load_roster(d)
    nick = {a["id"]: a for a in roster.get(TEAM, []) + roster.get("bench", [])}
    out = []
    for p in L.read_ledger(d, "picks"):
        if p.get("team") not in (TEAM, f"sandbox-{TEAM}") or L.is_watch(p, cfg):
            continue
        s = scores.get(p["pick_id"]) or {}
        if s.get("status") != "final" or s.get("score") is None or s["score"] >= 0:
            continue
        f = review_path(d, p)
        if f.exists():
            continue
        a = nick.get(p["agent_id"], {})
        out.append({"pick_id": p["pick_id"], "agent_id": p["agent_id"], "nickname": a.get("nickname", ""), "label": p.get("agent_label") or a.get("label", ""),
                    "agent_version": p.get("agent_version"), "round_date": p["round_date"], "market": p["market"], "ticker": p["ticker"], "name": p.get("name", ""),
                    "base_session": p.get("base_session"), "eval_session": s.get("eval_session") or p.get("eval_session"),
                    "score": s["score"], "benchmark": s.get("benchmark"), "benchmark_return": s.get("benchmark_return"), "score_excess": s.get("score_excess"),
                    "rationale": p.get("rationale", ""), "risks": p.get("risks", []), "sources": [x.get("url") for x in p.get("sources", []) if isinstance(x, dict)],
                    "path": str(f.relative_to(L.ROOT)) if f.is_relative_to(L.ROOT) else str(f)})
    return sorted(out, key=lambda x: (x["round_date"], x["agent_id"], x["market"]))


def check(path: Path) -> list[str]:
    errs = []
    if not path.exists():
        return [f"{path}: 파일 없음"]
    t = path.read_text(encoding="utf-8")
    m = re.match(r"(\d{4}-\d{2}-\d{2})/([a-z0-9]+)-(KR|US)\.md$", "/".join(path.parts[-2:]))
    if not m:
        errs.append("경로는 reviews/losses/<라운드>/<에이전트>-<KR|US>.md")
    if not t.startswith("# 손실 복기 — "):
        errs.append("첫 줄은 '# 손실 복기 — <pick_id>'")
    elif m and m.group(1) not in t.splitlines()[0]:
        errs.append("첫 줄 pick_id의 라운드 날짜가 경로와 다름")
    pos = [t.find(s) for s in SECTIONS]
    for s, i in zip(SECTIONS, pos):
        if i < 0:
            errs.append(f"절 없음: {s}")
    if all(i >= 0 for i in pos) and pos != sorted(pos):
        errs.append("절 순서가 다름")
    v = re.search(r"^판정:\s*(.+)$", t, re.M)
    if not v or not any(x in v.group(1) for x in VERDICTS):
        errs.append(f"'판정: <{' | '.join(VERDICTS)}>' 줄이 필요")
    if MONEY.search(t):
        errs.append(f"원 가격·금액 표현 금지: {MONEY.search(t).group(0)!r} (수익률 %·지수 대비 %p만)")
    if not (600 <= len(t) <= 6000):
        errs.append(f"길이 {len(t)}자 — 600~6000자")
    s2 = t[t.find("## 2."):t.find("## 3.")] if "## 2." in t and "## 3." in t else ""
    if s2 and "http" not in s2 and "출처 확인 못함" not in s2:
        errs.append("2절에 확인한 출처 URL이 하나 이상 필요(못 찾았으면 '출처 확인 못함'과 이유를 적는다)")
    return errs


def listing(d: Path, week: str | None = None) -> list[dict]:
    out = []
    for f in sorted(review_dir(d).glob("*/*.md")):
        rd = f.parent.name
        if week and L.iso_week(date.fromisoformat(rd)) != week:
            continue
        t = f.read_text(encoding="utf-8")
        v = re.search(r"^판정:\s*(.+)$", t, re.M)
        out.append({"round_date": rd, "file": f.name, "path": str(f), "verdict": v.group(1).strip() if v else ""})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["due", "check", "list"])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dir", default="league")
    ap.add_argument("--week")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = (L.ROOT / a.dir) if not Path(a.dir).is_absolute() else Path(a.dir)
    if a.cmd == "due":
        rows = due(d)
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                print(f"{r['pick_id']}  {r['nickname'] or r['agent_id']}  {r['market']} {r['name']}  {r['score']:+.2f}%  → {r['path']}")
            print(f"복기 필요 {len(rows)}건")
        return
    if a.cmd == "list":
        rows = listing(d, a.week)
        print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else "\n".join(f"{r['round_date']} {r['file']}  {r['verdict']}" for r in rows) or "없음")
        return
    bad = 0
    for p in a.paths:
        errs = check(Path(p))
        for e in errs:
            print(f"{p}: {e}")
        bad += bool(errs)
        if not errs:
            print(f"{p}: 통과")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
