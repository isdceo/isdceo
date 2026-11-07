"""손실 복기 — 로로 팀 종목이 확정 마이너스 점수를 받으면 그 종목을 고른 에이전트가 스스로 원인을 분석한다.

  python3 tools/loss_review.py due [--dir league] [--json]      → 아직 복기가 없는 마이너스 확정 종목
  python3 tools/loss_review.py due --bundle <results.json> --team 슈슈 --reviews <복기 폴더> [--mode 실전]
                                                               → 결과 묶음(원장 없이)으로 대상 찾기 — 슈슈 팀 안전 사본용
  python3 tools/loss_review.py check <복기 파일>...              → 형식·금지 표현 검사
  python3 tools/loss_review.py list [--dir league] [--week 2026-W46] → 작성된 복기 목록
  python3 tools/loss_review.py summary --week 2026-W46 [--dir league] [--weeks 2] [--out 파일.md] [--json]
                                                               → 에이전트별 판정 횟수·근거 pick_id·'바꿀 점' 모음(주간 복기 입력)

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
# 원 가격·금액 검사(경험칙). 세 가지만 막는다.
#  1) 통화가 붙은 금액: 1,393,000원에서 · 1,393,000 원 · 45달러로 · 245불에 · 5만 원 · $45 · ₩1000 · 13만~14만원
#  2) 가격 단서(종가·주가·목표가·매수가·단가 …) 뒤의 '가격 꼴 숫자'(쉼표·세 자리 이상·소수·천/만 단위)인데 그 뒤가 가격다울 때
#     (끝·문장부호·이었·으로·까지·에서·선·원·대로·아래 …). 단서와 숫자 사이에 조사·기호(**·|·=·→)·괄호 날짜·짧은 낱말 1~3개가 껴도 본다.
#  3) 가격 꼴 숫자 + '…에 마감·출발·시작·끝났다·거래됐다'
# 막지 않는 것: 작은 정수(3상·5대 악재·2시), 물량·셈(120척·10만 장·1,000대가), 이름 속 숫자(러셀 2000·보잉 737·HBM4), 연도(2026 가이던스),
# 날짜·시각(11/4·15:30), %·배수, 종목코드(000660.KS), 베타·상관계수 같은 지표.
_G = r"(?<![\d/:.\-~A-Za-z&])"                                     # 날짜(11/4)·시각(15:30)·범위(2~3)·이름(S&P500·HBM4)의 뒷숫자가 아님
_GU = r"(?<![\d/:.\-A-Za-z&])"                                    # 통화가 붙은 금액은 범위 끝(13만~14만원)도 잡는다
_N = r"(?>\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?+(?:\s*(?:천|만|억|조)(?:\s*\d++)?+)*+"            # 아무 숫자(원자 묶음: 되돌아가지 않음)
_NP = (r"(?!0\d{5}(?!\d))(?!(?:19|20)\d{2}(?!\d|[,.]\d))(?>\d{1,3}(?:,\d{3})+|\d{3,}|\d+\.\d+|\d+(?=\s*(?:천|만|억|조)))"  # 가격 꼴 숫자(6자리 0시작 = 종목코드 제외)
       r"(?:\.\d+)?+(?:\s*(?:천|만|억|조)(?:\s*\d++)?+)*+")
_RIGHT = (r"(?![./:\-]\d)(?=대로|대(?=\s*(?:$|[.,;)]|초반|중반|후반|로|에|까지|에서|을|를|이었|였))"
          r"|\s*(?:$|[.,;()|\]~→*`≈]|->|이었|였|이다|이며|이고|이던|이라|으로|로|까지|에서|에|을|를|과|와|은|는|도|의|이(?![가-힣])|가(?![가-힣])|선|원|달러)"
          r"|\s+(?:/|부근|근처|근방|안팎|수준|언저리|정도|전후|아래|밑|위|이하|이상|초반|중반|후반|선|대로|대에|대까지|대(?=\s*(?:$|[(.,;)]))|대비|기준|이탈|돌파|붕괴|회복|기록"
          r"|지지|저항|터치|도달|마감|출발|하회|상회|하락|상승|vs))")
# 중간 낱말이 낀 갈래용 좁은 뒤 문맥: 맨 조사(은·는·의·과·와·을·를)와 띄어 쓴 '대에·대로'는 빼서 모델 번호·물량(보잉 737의, 35만 대에)을 살린다
_RIGHT_F = (r"(?![./:\-]\d)(?=대로|대(?=\s*(?:$|[.,;)]))|\s*(?:$|[.,;()|\]~→*`≈]|->|이었|였|이다|이며|이고|이던|이라|으로|로|까지|에서|에|선|원|달러)"
            r"|\s+(?:/|부근|근처|근방|안팎|수준|언저리|정도|전후|아래|밑|이하|선|대비|기준|이탈|돌파|붕괴|회복|기록|하회|상회|vs))")
_CUE = (r"(?:종가|(?:(?<![가-힣])|(?<=[최신]))(?:시가|고가|저가)|(?<![가-힣])주가|시초가|현재가|최고가|최저가|고점|저점|주당|가격|목표\s*주?가"
        r"|평균\s*단가|(?<![가-힣])(?<!외국인 )(?<!기관 )(?<!개인 )(?<!연기금 )(?:매수가|매입가|매도가|진입가|체결가|기준가|손절가|적정주가|적정가|평단|단가|마감가|공모가))")
_DATE = r"(?:\d{1,2}/\d{1,2}|\d{1,2}월\s*\d{1,2}일|\d{4}-\d{2}-\d{2})"
_PART = (r"(?:\s*(?:는|은|가|이|도|을|를|으로|로|의|기준|약|대략|한때|장중|장\s*초반|이날|다음\s*날|:|：|\||=|＝|\*|`|—|→|->|~|≈|\(\s*" + _DATE
         + r"\s*\)|\())*+\s*")
_FILL = (r"(?:\s+(?:(?!코스피|코스닥|나스닥|다우|러셀|포춘|닛케이|지수|환율|금리|거래량|거래대금|관객|가입자|계좌|판매|수주|누적|앨범|차량|객실|증설|미분양"
         r"|물량|매출|규모|베타|상관|계수|변동성|회전율|비율|배수|순위|점수)[가-힣]{1,4}|\d{1,2}월|\d{1,2}일|" + _DATE
         + r"|\d{1,2}(?:주일?|개월|거래일)|[+−-]?\d+(?:\.\d+)?%p?)){1,3}")
_DIR = r"(?:(?:상승|하락|강세|약세|보합|급등|급락)\s*)"
MONEY = re.compile(
    r"[$₩￦]\s*\d|" + _GU + _N + r"\s*\$"
    + r"|" + _GU + r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:(?:\s*(?:천|만|억|조))+\s*원|\s*원)(?![인칙화자유래전천본격리론소형점문장]|가(?!량|까이))"
    + r"|" + _GU + _N + r"\s*(?:달러|USD|KRW)(?![A-Za-z])|" + _GU + _N + r"불(?:(?![가-힣])|(?=에|로|으로|선|대|을|까지|도|이(?![가-힣])))|(?:USD|KRW)\s*\d"
    + r"|" + _CUE + _PART + _NP + _RIGHT                                     # 단서 바로 뒤(조사·기호만 낌)
    + r"|" + _CUE + r"(?:는|은|가|이|도)?" + _FILL + r"\s+" + _NP + _RIGHT_F     # 단서와 숫자 사이에 짧은 낱말 1~3개
    + r"|" + _G + _N + r"\**(?:\s*선?\s*(?:에서|에|으로|로)\s*(?:" + _DIR + r"?(?:장\s*)?마감|" + _DIR + r"출발|(?:거래|장)을?를?\s*(?:마쳤|마치|마감|끝냈|끝))|\s+마감)"
    + r"|(?<![\d/:.\-~A-Za-z&가-힣])(?:\d{1,3}(?:,\d{3})+|\d{3,})(?:\.\d+)?\**\s*(?:에|으로|로)\s*(?:출발|시작|끝났|끝냈|끝마|거래됐|거래되었|마쳤|마무리|(?:거래|장)을?를?\s*(?:시작|종료)|종료)")


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
        if f.exists() and not check(f):
            continue   # 검사를 통과한 복기가 있으면 끝. 쓰다 만·실패한 파일은 다시 대상

        a = nick.get(p["agent_id"], {})
        out.append({"pick_id": p["pick_id"], "agent_id": p["agent_id"], "nickname": a.get("nickname", ""), "label": p.get("agent_label") or a.get("label", ""),
                    "agent_version": p.get("agent_version"), "round_date": p["round_date"], "market": p["market"], "ticker": p["ticker"], "name": p.get("name", ""),
                    "base_session": p.get("base_session"), "eval_session": s.get("eval_session") or p.get("eval_session"),
                    "score": s["score"], "benchmark": s.get("benchmark"), "benchmark_return": s.get("benchmark_return"), "score_excess": s.get("score_excess"),
                    "rationale": p.get("rationale", ""), "risks": p.get("risks", []), "sources": [x.get("url") for x in p.get("sources", []) if isinstance(x, dict)],
                    "path": str(f.relative_to(L.ROOT)) if f.is_relative_to(L.ROOT) else str(f)})
    return sorted(out, key=lambda x: (x["round_date"], x["agent_id"], x["market"]))


def due_bundle(bundle: Path, team: str, reviews: Path, mode: str = "실전") -> list[dict]:
    """공개 결과 묶음(results.json)만으로 마이너스 확정 종목을 찾는다(원장이 없는 슈슈 팀 안전 사본용).
    team은 묶음의 팀 이름 일부(예: '슈슈', '로로'). 관망·잠정·보류 제외, 복기 파일이 있으면 제외."""
    data = json.loads(bundle.read_text(encoding="utf-8"))
    out = []
    for p in data.get("picks", []):
        if team not in str(p.get("team", "")) or (mode and p.get("mode") != mode) or p.get("watch"):
            continue
        if p.get("status") != "final" or p.get("score") is None or p["score"] >= 0:
            continue
        f = reviews / p["round_date"] / f"{p['agent_id']}-{p['market']}.md"
        if f.exists() and not check(f):
            continue
        out.append({"pick_id": p["pick_id"], "agent_id": p["agent_id"], "agent": p.get("agent", ""), "round_date": p["round_date"], "market": p["market"],
                    "ticker": p.get("ticker"), "name": p.get("name", ""), "score": p["score"], "score_excess": p.get("score_excess"), "path": str(f)})
    return sorted(out, key=lambda x: (x["round_date"], x["agent_id"], x["market"]))


_CUE_HEAD = re.compile(r"종가|주가|시가|고가|저가|가격|단가|매수가|매도가|목표\s*주?가|평단|기준가|현재가")
_NP_RE = re.compile(r"(?<![\d.,%+\-−▲▼△▽])" + _NP + r"(?![\d.,]|\s*%)")
_HEAD_SKIP = re.compile(r"%|률|비율|PER|PBR|총액|시가총액|배|수익비율|순자산")


def _table_prices(t: str) -> str | None:
    """세로형 마크다운 표: 머리글 칸에 가격 단서가 있으면 그 칸 아래의 가격 꼴 숫자를 원 가격으로 본다."""
    rows = [l for l in t.splitlines()]
    i = 0
    while i < len(rows):
        if rows[i].lstrip().startswith("|") and i + 1 < len(rows) and re.match(r"^\s*\|?\s*:?-{2,}", rows[i + 1]):
            head = [c.strip() for c in rows[i].strip().strip("|").split("|")]
            cols = [k for k, c in enumerate(head) if _CUE_HEAD.search(c) and not _HEAD_SKIP.search(c)]
            j = i + 2
            while j < len(rows) and rows[j].lstrip().startswith("|"):
                cells = [c.strip() for c in rows[j].strip().strip("|").split("|")]
                for k in cols:
                    if k < len(cells) and _NP_RE.search(cells[k]):
                        return f"{head[k]}: {cells[k]}"
                j += 1
            i = j
        else:
            i += 1
    return None


def _known_closes(path: Path) -> list[str]:
    """복기 파일 경로(<리그>/reviews/losses/<라운드>/<에이전트>-<시장>.md)로 그 종목의 원장 종가를 찾아, 본문에 나올 수 있는 표기들을 돌려준다.
    경험칙(MONEY)과 별도로, 실제 기록된 원 가격은 어떤 문장 꼴로 써도 막기 위한 정확한 안전장치다(원장이 없으면 빈 목록)."""
    try:
        d = path.resolve().parents[3]
        rd = path.parent.name; aid, mk = path.stem.rsplit("-", 1)
        picks = [p for p in L.read_ledger(d, "picks") if p.get("round_date") == rd and p.get("agent_id") == aid and p.get("market") == mk]
        if not picks:
            return []
        tk = picks[-1]["ticker"]
        out = set()
        for r in L.read_ledger(d, "prices"):
            if r.get("market") == mk and r.get("ticker") == tk and r.get("close"):
                c = float(r["close"])
                if c >= 100 or c != int(c):
                    for s in ({f"{c:,.0f}", f"{c:.0f}"} if c == int(c) else {f"{c:,.2f}", f"{c:.2f}", f"{c:,.2f}".rstrip("0"), f"{c:.2f}".rstrip("0")}):
                        out.add(s)
        return sorted(out, key=len, reverse=True)
    except Exception:
        return []


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
    elif m and not re.fullmatch(rf"# 손실 복기 — {m.group(1)}-(?:sandbox-)?[a-z]+-{m.group(2)}-{m.group(3)}\s*", t.splitlines()[0]):
        errs.append("첫 줄 pick_id(<라운드>-<팀>-<에이전트>-<시장>)가 파일 경로와 다름")
    pos = [t.find(s) for s in SECTIONS]
    for s, i in zip(SECTIONS, pos):
        if i < 0:
            errs.append(f"절 없음: {s}")
    if all(i >= 0 for i in pos) and pos != sorted(pos):
        errs.append("절 순서가 다름")
    v = re.search(r"^판정:\s*(.+)$", t, re.M)
    if v and sum(x in v.group(1) for x in VERDICTS) > 1:
        errs.append("판정은 하나만")
    elif not v or not any(x in v.group(1) for x in VERDICTS):
        errs.append(f"'판정: <{' | '.join(VERDICTS)}>' 줄이 필요")
    for c in _known_closes(path):
        if re.search(r"(?<![\d.,])" + re.escape(c) + r"(?![\d]|[.,]\d|\s*%|\s*배)", t):
            errs.append(f"원장에 기록된 이 종목의 종가와 같은 숫자 {c!r} — 원 가격 금지")
            break
    te = _table_prices(t)
    if te:
        errs.append(f"표의 가격 칸에 원 가격 금지: {te!r}")
    if not (600 <= len(t) <= 6000):
        errs.append(f"길이 {len(t)}자 — 600~6000자")
    mm = MONEY.search(t[:6000]) if len(t) <= 6000 else None
    if mm:
        errs.append(f"원 가격·금액 표현 금지: {mm.group(0)!r} (수익률 %·지수 대비 %p만)")
    s2 = t[t.find("## 2."):t.find("## 3.")] if "## 2." in t and "## 3." in t else ""
    if s2 and "http" not in s2 and "출처 확인 못함" not in s2:
        errs.append("2절에 확인한 출처 URL이 하나 이상 필요(못 찾았으면 '출처 확인 못함'과 이유를 적는다)")
    return errs


def listing(d: Path, week: str | None = None) -> list[dict]:
    out = []
    for f in sorted(review_dir(d).glob("*/*.md")):
        rd = f.parent.name
        try:
            if week and L.iso_week(date.fromisoformat(rd)) != week:
                continue
        except ValueError:
            continue
        t = f.read_text(encoding="utf-8")
        v = re.search(r"^판정:\s*(.+)$", t, re.M)
        out.append({"round_date": rd, "file": f.name, "path": str(f), "verdict": v.group(1).strip() if v else ""})
    return out


def _section(t: str, head: str) -> str:
    i = t.find(head)
    if i < 0:
        return ""
    j = t.find("\n## ", i + len(head))
    return t[i + len(head): j if j >= 0 else None].split("\n", 1)[-1].strip()


def _weeks_back(week: str, n: int) -> set[str]:
    y, w = week.split("-W")
    mon = date.fromisocalendar(int(y), int(w), 1)
    return {L.iso_week(date.fromordinal(mon.toordinal() - 7 * k)) for k in range(n)}


def summary(d: Path, week: str, weeks: int = 1, reviews: Path | None = None) -> dict:
    """에이전트별: 복기 수, 판정별 개수와 pick_id, '바꿀 점' 항목, 반복 신호.
    반복 신호 = 같은 판정이 2건 이상(특히 '분석 실수') — v2.1 규칙의 '같은 유형 오류 pick_id 2건 이상' 후보. 최종 판단은 주간 복기가 한다."""
    want = _weeks_back(week, max(1, weeks))
    agents: dict[str, dict] = {}
    scores = L.latest_scores(d) if (d / "ledger").exists() else {}
    corrected = []
    for f in sorted((reviews or review_dir(d)).glob("*/*.md")):
        rd = f.parent.name
        try:
            if L.iso_week(date.fromisoformat(rd)) not in want:
                continue
        except ValueError:
            continue
        t = f.read_text(encoding="utf-8")
        m = re.match(r"([a-z0-9]+)-(KR|US)$", f.stem)
        if not m:
            continue
        aid, mk = m.groups()
        pid = (t.splitlines()[0].split("— ", 1)[-1].strip() if t else "") or f"{rd}-{aid}-{mk}"
        sc_now = (scores.get(pid) or {}).get("score")
        if sc_now is not None and sc_now >= 0:
            corrected.append({"pick_id": pid, "score": sc_now})   # 확정 뒤 정정돼 손실이 아니게 됨 — 집계에서 뺀다
            continue
        v = re.search(r"^판정:\s*(.+)$", t, re.M)
        verdict = next((x for x in VERDICTS if v and x in v.group(1)), "판정 없음")
        res = re.search(r"^- 결과:\s*([+−-]?\d+(?:\.\d+)?)%", t, re.M)
        score = float(res.group(1).replace("−", "-")) if res else None
        fixes = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", x).strip() for x in _section(t, "## 5. 다음에 바꿀 점").splitlines()]
        fixes = [x for x in fixes if len(x) >= 8 and not x.startswith(("(", "（", ">"))][:4]
        a = agents.setdefault(aid, {"agent_id": aid, "reviews": 0, "verdicts": {}, "fixes": [], "scores": []})
        a["reviews"] += 1
        a["verdicts"].setdefault(verdict, []).append(pid)
        a["fixes"] += [{"pick_id": pid, "text": x} for x in fixes]
        if score is not None:
            a["scores"].append(score)
    for a in agents.values():
        a["repeated"] = {k: v for k, v in a["verdicts"].items() if len(v) >= 2}
        a["mistakes"] = len(a["verdicts"].get("분석 실수", []))
    rows = sorted(agents.values(), key=lambda a: (-a["mistakes"], -a["reviews"], a["agent_id"]))
    return {"week": week, "weeks": sorted(want), "agents": rows, "corrected": corrected,
            "totals": {k: sum(len(a["verdicts"].get(k, [])) for a in rows) for k in VERDICTS + ("판정 없음",)}}


def summary_md(s: dict, names: dict | None = None) -> str:
    names = names or {}
    L_ = [f"# 손실 복기 요약 — {s['week']}" + (f" (최근 {len(s['weeks'])}주: {', '.join(s['weeks'])})" if len(s["weeks"]) > 1 else ""), ""]
    if not s["agents"]:
        return "\n".join(L_ + ["이 기간에 손실 복기가 없습니다.", ""])
    L_ += ["| 에이전트 | 복기 | " + " | ".join(VERDICTS) + " | 반복 신호 |", "|---|---:|" + "---:|" * len(VERDICTS) + "---|"]
    for a in s["agents"]:
        rep_ = ", ".join(f"{k} {len(v)}건" for k, v in a["repeated"].items()) or "—"
        L_.append(f"| {names.get(a['agent_id'], a['agent_id'])} | {a['reviews']} | " + " | ".join(str(len(a["verdicts"].get(k, []))) for k in VERDICTS) + f" | {rep_} |")
    L_ += ["", "판정별 합계: " + " · ".join(f"{k} {n}" for k, n in s["totals"].items() if n), "",
           *([f"정정돼 손실이 아니게 된 복기(집계 제외): {', '.join(c['pick_id'] for c in s['corrected'])}", ""] if s.get("corrected") else []),
           "> 반복 신호는 '같은 판정 2건 이상'일 뿐이다. 개선안 근거가 되려면 주간 복기가 원인이 같은 유형인지 확인한다(규칙 v2.1). '시장 전체 움직임'·'운·잡음'은 지침 수정 근거가 아니다.", ""]
    for a in s["agents"]:
        L_.append(f"## {names.get(a['agent_id'], a['agent_id'])}")
        for k, v in a["verdicts"].items():
            L_.append(f"- {k}: {', '.join(v)}")
        if a["fixes"]:
            L_.append("- 바꿀 점(복기 제안):")
            L_ += [f"  - {x['text']} ({x['pick_id']})" for x in a["fixes"]]
        L_.append("")
    return "\n".join(L_)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["due", "check", "list", "summary"])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dir", default="league")
    ap.add_argument("--week")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--weeks", type=int, default=1, help="summary: 이번 주 포함 최근 몇 주")
    ap.add_argument("--out", help="summary: 마크다운 저장 경로")
    ap.add_argument("--bundle", help="due: 원장 대신 결과 묶음(results.json)으로 찾기")
    ap.add_argument("--team", default="로로", help="due --bundle: 팀 이름 일부")
    ap.add_argument("--reviews", help="due --bundle / summary: 복기 폴더(기본 <dir>/reviews/losses)")
    ap.add_argument("--mode", default="실전", help="due --bundle: 실전|연습")
    a = ap.parse_args()
    d = (L.ROOT / a.dir) if not Path(a.dir).is_absolute() else Path(a.dir)
    if a.cmd == "due":
        rows = due_bundle(Path(a.bundle), a.team, Path(a.reviews) if a.reviews else review_dir(d), a.mode) if a.bundle else due(d)
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                print(f"{r['pick_id']}  {r.get('nickname') or r.get('agent') or r['agent_id']}  {r['market']} {r['name']}  {r['score']:+.2f}%  → {r['path']}")
            print(f"복기 필요 {len(rows)}건")
        return
    if a.cmd == "summary":
        if not a.week:
            sys.exit("--week 필요 (예: 2026-W46)")
        s = summary(d, a.week, a.weeks, Path(a.reviews) if a.reviews else None)
        try:
            roster = L.load_roster(d)
        except Exception:
            roster = {}
        names = {x["id"]: f"{x.get('nickname') or x['id']} ({x['id']})" for x in roster.get(TEAM, []) + roster.get("bench", [])}
        md = summary_md(s, names)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(md + "\n", encoding="utf-8")
        print(json.dumps(s, ensure_ascii=False, indent=1) if a.json else md)
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
