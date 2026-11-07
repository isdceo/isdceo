"""대기 후보(새 캐릭터) 추가 — 운영자 상시 위임(2026-11-07)에 따라 검사를 통과하면 자동 반영.

  python3 tools/add_character.py need                     → 팀·리그별 남은 대기 후보 수와 보충 필요 여부
  python3 tools/add_character.py from-message <md>        → 슈슈 메시지(to-roro/…bench-proposal.md)의 ```json 블록과 '## 지침' 절로 추가
  python3 tools/add_character.py add <spec.json>          → 사양 파일로 추가 (로로 팀 후보는 지침 .md 경로를 함께)
  공통 옵션: --dry-run (검사만)

사양(JSON):
  {"team": "shushu"|"claude", "id": "s8", "nickname": "등대", "label": "배당성장형",
   "style_ref": "<공개된 투자 원칙 참고 — 실존 인물의 추천처럼 쓰지 않음>", "tagline": "<40자 이하>",
   "look": {"name": "deungdae", "skin": "light|tan|deep|pale|brown", "hair": "none|short|long|curly", "hairc": "#rrggbb",
            "hat": "none|cap|beanie", "hatc": "#rrggbb", "brows": "up|skeptic|worry|angry|bushy",
            "nose": "bulb|long|button", "mouth": "grin|smirk|laugh|tongue|gap",
            "glasses": null|"round"|"half"|"square"|"sun"|"goggles"|"loupe", "outfit": "#rrggbb", "collar": "shirt|sailor|hood"}}
반영: 명단 대기 목록(버전 1) + 승인 원장(approvals, 상시 위임 표시) + 지침 보관본 + 캐릭터 그림(SVG 생성기·현황판 정의·README).
3D 그림은 없으면 게임 화면이 SVG 캐릭터로 대신 보여 준다.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

ROOT = L.ROOT
SRC = ROOT / "league" / "agents" / "avatars" / "src"
PAGE = ROOT / "docs" / "dashboard" / "operator-dashboard-page.html"
README = ROOT / "league" / "agents" / "avatars" / "README.md"
CHOICES = {"skin": {"light", "tan", "deep", "pale", "brown"}, "hair": {"none", "short", "long", "curly"},
           "hat": {"none", "cap", "beanie"}, "brows": {"up", "skeptic", "worry", "angry", "bushy"},
           "nose": {"bulb", "long", "button"}, "mouth": {"grin", "smirk", "laugh", "tongue", "gap"},
           "glasses": {None, "round", "half", "square", "sun", "goggles", "loupe"}, "collar": {"shirt", "sailor", "hood"}}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TICKERISH = re.compile(r"(?<!\d)\d{6}(?!\d)|(?<![A-Za-z])[A-Z]{2,5}(?![A-Za-z])")   # 한글이 붙어도 잡는다
REAL_PERSON_CLAIM = re.compile(r"(본인|직접|실제로) .*(추천|발언)|사진|초상|닮은")


def rosters():
    sh_p = ROOT / "league" / "imports" / "shushu" / "roster.json"
    cl_p = ROOT / "league" / "agents" / "roster.json"
    return sh_p, json.loads(sh_p.read_text()), cl_p, json.loads(cl_p.read_text())


def need(threshold: int | None = None) -> dict:
    """팀·리그별 승인된 대기 후보 수. 어느 리그든 threshold 이하면 보충 필요."""
    d = ROOT / "league"
    cfg = L.load_config(d)
    th = threshold if threshold is not None else int((cfg.get("bench_auto") or {}).get("min_available", 1))
    roster = L.load_roster(d)
    out = {}
    for team in cfg["teams"]:
        avail = {mk: len(L.bench_available(d, roster, team, mk)) for mk in L.MARKETS}
        out[team] = {"available": avail, "need": min(avail.values()) <= th}
    return out


def validate(spec: dict) -> list[str]:
    errs = []
    sh_p, sh, cl_p, cl = rosters()
    team = spec.get("team")
    if team not in ("shushu", "claude"):
        return ["team은 shushu 또는 claude"]
    everyone = sh.get("members", []) + sh.get("bench", []) + cl.get("claude", []) + cl.get("bench", [])
    if not re.fullmatch(r"[a-z][a-z0-9]{1,15}", str(spec.get("id", ""))):
        errs.append("id: 영문 소문자로 시작, 소문자·숫자 2~16자")
    if any(a.get("id") == spec.get("id") for a in everyone):
        errs.append(f"id {spec.get('id')} 이미 있음")
    for k, n in (("nickname", 12), ("label", 16), ("tagline", 40), ("style_ref", 80)):
        v = str(spec.get(k, "")).strip()
        if not v or len(v) > n:
            errs.append(f"{k}: 1~{n}자")
    if any(a.get("nickname") == spec.get("nickname") for a in everyone):
        errs.append("애칭이 기존 캐릭터와 같음")
    if any(a.get("label") == spec.get("label") for a in everyone):
        errs.append("스타일(label)이 기존 에이전트와 같음 — 다른 관점이어야 함")
    if "공개" not in str(spec.get("style_ref", "")):
        errs.append("style_ref는 '공개된 … 원칙 참고' 형식(실존 인물 사칭 금지)")
    blob = " ".join(str(spec.get(k, "")) for k in ("nickname", "label", "tagline"))
    if TICKERISH.search(blob):
        errs.append("애칭·스타일·소개에 종목 코드처럼 보이는 표현 금지(특정 종목 고정 금지)")
    if REAL_PERSON_CLAIM.search(blob + " " + str(spec.get("style_ref", ""))):
        errs.append("실존 인물의 얼굴·발언처럼 보이는 표현 금지")
    lk = spec.get("look") or {}
    if not re.fullmatch(r"[a-z]{3,12}", str(lk.get("name", ""))):
        errs.append("look.name: 영문 소문자 3~12자")
    extra = json.loads((SRC / "extra.json").read_text()) if (SRC / "extra.json").exists() else []  # noqa: E501
    chars = (SRC / "chars.py").read_text() if (SRC / "chars.py").exists() else ""      # 슈슈 쪽 사본에는 생성기가 없다
    existing_av = {a.get("avatar") for a in everyone} | {e["name"] for e in extra} | set(re.findall(r'^CH\["([a-z]+)"\]', chars, re.M))
    if lk.get("name") in existing_av:
        errs.append("look.name 이미 있음")
    for k, allowed in CHOICES.items():
        if k in lk and lk[k] not in allowed:
            errs.append(f"look.{k}: {sorted(x for x in allowed if x)} 중 하나")
    for k in ("skin", "hairc", "outfit"):
        if k not in lk:
            errs.append(f"look.{k} 필요")
    for k in ("hairc", "outfit", "hatc"):
        if k in lk and not HEX.match(str(lk[k])):
            errs.append(f"look.{k}: #rrggbb")
    if team == "claude" and not (spec.get("guideline") or "").strip():
        errs.append("로로 팀 후보는 지침 본문(guideline)이 필요")
    return errs


def regenerate_avatars() -> None:
    subprocess.run([sys.executable, "chars.py"], cwd=SRC, check=True, capture_output=True)
    defs = (SRC / "defs.svg").read_text()
    page = PAGE.read_text()
    m = re.search(r'(<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>)(.*?)(</defs></svg>)', page, re.S)
    if not m:
        raise SystemExit("현황판 페이지에서 캐릭터 정의 블록을 찾지 못함")
    PAGE.write_text(page[:m.start(2)] + "\n    " + defs + "\n    " + page[m.end(2):])


def apply(spec: dict, source: str, dry: bool = False) -> list[str]:
    errs = validate(spec)
    if errs or dry:
        return errs
    cfg = L.load_config(ROOT / "league")
    auto = (cfg.get("bench_auto") or {}).get("enabled", False)
    sh_p, sh, cl_p, cl = rosters()
    lk = dict(spec["look"])
    entry = {"id": spec["id"], "label": spec["label"], "style_ref": spec["style_ref"], "version": 1,
             "nickname": spec["nickname"], "avatar": lk["name"], "tagline": spec["tagline"]}
    if spec["team"] == "shushu":
        sh.setdefault("bench", []).append(entry)
        sh_p.write_text(json.dumps(sh, ensure_ascii=False, indent=2) + "\n")
        if spec.get("guideline"):
            g = ROOT / "league" / "imports" / "shushu" / "agents" / spec["id"] / "v1.md"
            g.parent.mkdir(parents=True, exist_ok=True); g.write_text(spec["guideline"].rstrip() + "\n")
    else:
        entry.update(guideline=f".claude/agents/{spec['id']}.md")
        cl.setdefault("bench", []).append(entry)
        cl_p.write_text(json.dumps(cl, ensure_ascii=False, indent=2) + "\n")
        body = spec["guideline"].rstrip() + "\n"
        (ROOT / ".claude" / "agents" / f"{spec['id']}.md").write_text(body)
        arch = ROOT / "league" / "agents" / "claude" / spec["id"] / "v1.md"
        arch.parent.mkdir(parents=True, exist_ok=True); arch.write_text(body)
    if auto:
        L.append(ROOT / "league", "approvals", {"type": "bench", "team": spec["team"], "agent_id": spec["id"], "decision": "approved",
                                                "approved_by": "운영자 상시 위임(2026-11-07, 검사 통과 시 자동)", "source": source,
                                                "at": datetime.now(L.KST).isoformat(timespec="seconds")})
    ex_p = SRC / "extra.json"
    ex = json.loads(ex_p.read_text()) if ex_p.exists() else []
    ex.append({**lk, "team": "s" if spec["team"] == "shushu" else "c", "nickname": spec["nickname"]})
    ex_p.write_text(json.dumps(ex, ensure_ascii=False, indent=1) + "\n")
    regenerate_avatars()
    with README.open("a") as f:
        f.write(f"| {lk['name']} | {spec['nickname']} | 자동 추가({spec['team']}, {spec['label']}) — 선택지형 캐릭터 |\n")
    return []


def spec_from_message(md: str) -> dict:
    m = re.search(r"```json\s*(\{.*?\})\s*```", md, re.S)
    if not m:
        raise SystemExit("```json 블록이 없음")
    spec = json.loads(m.group(1))
    g = re.search(r"^## 지침\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    if g:
        spec["guideline"] = g.group(1).strip()
    spec.setdefault("team", "shushu")
    return spec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["need", "add", "from-message"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "need":
        print(json.dumps(need(), ensure_ascii=False, indent=1))
        return
    if not a.path:
        sys.exit("파일 경로 필요")
    if a.cmd == "from-message":
        spec = spec_from_message(Path(a.path).read_text())
        if spec.get("team") != "shushu":
            sys.exit("슈슈 메시지로는 슈슈 팀 후보만 추가")
    else:
        spec = json.loads(Path(a.path).read_text())
    errs = apply(spec, source=str(a.path), dry=a.dry_run)
    for e in errs:
        print("문제:", e)
    print(("검사 통과" if a.dry_run else f"추가함: {spec['team']} {spec['id']} ({spec['nickname']})") if not errs else f"문제 {len(errs)}건 — 반영 안 함")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
