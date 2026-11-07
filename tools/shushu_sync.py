"""슈슈 팀 전용 제출 저장소 연결 (규칙 v2.x, B안).

슈슈 팀은 전용 저장소에만 push한다. 이 도구는 메인 저장소의 워크플로(league-shushu-sync)에서 돈다.

  pull   : 전용 저장소의 push 기록(GitHub 서버 activity 시각)을 차례로 읽어, 허용 경로의 파일만 메인으로 가져오고
           그 push 시각으로 영수증을 판정한다. 마감(08:30) 전 원본·토론·대사가 든 push는 마감까지 보류한다
           (메인 저장소에 마감 전 종목이 들어오지 않게). 같은 push는 한 번만 처리한다(원장 external_pushes).
  mirror : 원 가격이 없는 결과 묶음·영수증·공지·검증 도구 사본을 전용 저장소의 from-league/ 에 넣는다.

전용 저장소 경로 → 메인 경로
  submit/<날짜>.sha256 | .csv | -debate.md     → league/imports/shushu/
  practice/<날짜>.sha256 | .csv | -debate.md   → league/imports/sandbox-shushu/
  lines/<날짜>-shushu.json                     → league/lines/
  practice-lines/<날짜>-sandbox-shushu.json    → league/sandbox/lines/
그 밖의 경로는 무시하고 기록만 남긴다.

토큰은 워크플로 환경변수(SHUSHU_REPO_TOKEN)로만 받고 출력하지 않는다. 전용 저장소에는 비밀값을 두지 않는다.
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

ROOT = L.ROOT
UA = "league-shushu-sync/0.1"
D = r"(\d{4}-\d{2}-\d{2})"
RULES = [  # (전용 저장소 경로, 메인 경로 틀, 마감 전 보류 여부, 종류)
    (re.compile(rf"^submit/{D}\.sha256$"), "league/imports/shushu/{0}.sha256", False, "commitment"),
    (re.compile(rf"^submit/{D}\.csv$"), "league/imports/shushu/{0}.csv", True, "reveal"),
    (re.compile(rf"^submit/{D}-debate\.md$"), "league/imports/shushu/{0}-debate.md", True, "debate"),
    (re.compile(rf"^practice/{D}\.sha256$"), "league/imports/sandbox-shushu/{0}.sha256", False, "commitment"),
    (re.compile(rf"^practice/{D}\.csv$"), "league/imports/sandbox-shushu/{0}.csv", True, "reveal"),
    (re.compile(rf"^practice/{D}-debate\.md$"), "league/imports/sandbox-shushu/{0}-debate.md", True, "debate"),
    (re.compile(rf"^lines/{D}-shushu\.json$"), "league/lines/{0}-shushu.json", True, "lines"),
    (re.compile(rf"^practice-lines/{D}-sandbox-shushu\.json$"), "league/sandbox/lines/{0}-sandbox-shushu.json", True, "lines"),
    (re.compile(rf"^to-roro/({D}-[a-z0-9-]{{1,60}})\.md$"), "league/inbox/shushu/{0}.md", True, "message"),
]
MSG_HOLD = "12:00"          # 슈슈 → 로로 메시지는 그날 원본 공개 마감(12:00) 뒤에만 메인에 들인다(당일 종목 정보 차단)
ZERO = "0" * 40
MIRROR_DIR = "from-league"


def git(*a, cwd) -> str:
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def git_bytes(*a, cwd) -> bytes:
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True).stdout


def map_path(p: str):
    for rx, tmpl, hold, kind in RULES:
        m = rx.match(p)
        if m:
            return tmpl.format(m.group(1)), m.group(m.lastindex), hold, kind
    return None


def fetch_activity(repo: str, token: str) -> list[dict]:
    """GitHub 서버가 기록한 push 목록(모든 브랜치, 오래된 것부터). 전용 저장소 사용자가 바꿀 수 없는 시각이다.
    Codex 클라우드처럼 작업 브랜치에 push하고 PR을 여는 방식도 그 브랜치 push 시각으로 판정한다(병합 시각이 아님).
    병합으로 같은 파일이 다시 들어오면 메인과 내용이 같아 영수증을 새로 만들지 않는다."""
    url = f"https://api.github.com/repos/{repo}/activity?activity_type=push&per_page=100&direction=asc"
    out = []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": UA,
                                                  "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out += json.loads(r.read() or b"[]")
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link") or "")
            url = nxt.group(1) if nxt else None
    out = [a for a in out if str(a.get("ref", "refs/heads/")).startswith("refs/heads/") and a.get("after") and a["after"] != ZERO]
    return sorted(out, key=lambda a: (a["timestamp"], a["id"]))


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(L.KST)


def _have(ext: Path, sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ext, capture_output=True).returncode == 0


def _changed(ext: Path, before: str, after: str) -> list[str]:
    for sha in (after, before):
        if sha and sha != ZERO and not _have(ext, sha):
            subprocess.run(["git", "fetch", "-q", "origin", sha], cwd=ext, capture_output=True)
    if before and before != ZERO:
        try:
            return git("diff", "--name-only", "--diff-filter=AM", before, after, cwd=ext).splitlines()
        except subprocess.CalledProcessError:
            pass                                       # 강제 push 등으로 이전 커밋이 없으면 전체 목록
    return git("ls-tree", "-r", "--name-only", after, cwd=ext).splitlines()


def pull(main: Path, ext: Path, activities: list[dict], repo: str, now: datetime | None = None,
         run_id: str = "", run_url: str = "") -> list[dict]:
    """전용 저장소 push를 차례로 처리한다. 반환: 이번에 처리한 push 요약(원장 external_pushes에도 기록)."""
    now = now or datetime.now(L.KST)
    d = main / "league"
    done = {x["activity_id"] for x in L.read_ledger(d, "external_pushes") if x.get("repo") == repo}
    out = []
    for act in activities:
        if act["id"] in done:
            continue
        pushed = _ts(act["timestamp"])
        files = _changed(ext, act.get("before"), act["after"])
        if files and all(f.startswith(MIRROR_DIR + "/") for f in files):
            continue                                   # 메인이 보낸 사본 push — 기록하지 않음(기록하면 사본·기록이 끝없이 반복)
        mapped, ignored, held = [], [], []
        for f in files:
            m = map_path(f)
            if not m:
                ignored.append(f)
                continue
            dst, rd, hold, kind = m
            team = "sandbox-shushu" if dst.startswith(("league/imports/sandbox-", "league/sandbox/")) else "shushu"
            cfg = L.load_config(L.ledger_dir_for(team, main))
            if kind == "message":                      # 메시지: push한 날 12:00 뒤에만 (파일 이름 날짜와 무관)
                h_, m_ = map(int, MSG_HOLD.split(":"))
                if now <= pushed.replace(hour=h_, minute=m_, second=0, microsecond=0):
                    held.append(f)
            elif hold and now <= L.lock_deadline(date.fromisoformat(rd), cfg):
                held.append(f)
            mapped.append((f, dst, kind))
        if held:
            # 마감 전 원본·토론·대사: 메인에 들이지 않고 이 push부터 마감 뒤까지 보류(뒤 push도 순서대로 기다린다)
            out.append({"activity_id": act["id"], "status": "held_until_deadline", "files": held})
            break
        rec = {"repo": repo, "activity_id": act["id"], "ref": act.get("ref"), "s_before": act.get("before"), "s_after": act["after"],
               "pushed_at": pushed.isoformat(), "actor": (act.get("actor") or {}).get("login"),
               "files": [f for f, _, _ in mapped], "ignored": ignored, "run_id": str(run_id), "run_url": run_url}
        receipts, lines = [], []
        if mapped:
            prev = git("rev-parse", "HEAD", cwd=main)
            for f, dst, kind in mapped:
                p = main / dst
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(git_bytes("show", f"{act['after']}:{f}", cwd=ext))      # 바이트 그대로
                git("add", dst, cwd=main)
            if git("status", "--porcelain", "--", *[dst for _, dst, _ in mapped], cwd=main):
                git("-c", "user.name=league-bot", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                    "commit", "-q", "-m", f"league: shushu repo push {act['after'][:7]} ({pushed.isoformat(timespec='seconds')})",
                    "-m", f"source: {repo}@{act['after']} activity {act['id']}", cwd=main)
                after = git("rev-parse", "HEAD", cwd=main)
                event = {"before": prev, "after": after, "ref": "refs/heads/main", "commits": [],
                         "pusher": {"name": f"{repo}:{rec['actor']}"},
                         "repository": {"pushed_at": int(pushed.timestamp())},
                         "judged_by": "shushu_repo.activity.timestamp",
                         "source": {"repo": repo, "commit": act["after"], "activity_id": act["id"]}}
                try:
                    receipts = L.process_push(event, run_id=run_id, run_url=run_url, cwd=main)
                except L.CommitmentPending as e:       # 순서대로 처리하므로 보통 생기지 않음
                    rec["note"] = str(e)
                lines = [(dst, _check_lines(main, dst)) for _, dst, kind in mapped if kind == "lines"]
                rec["main_commit"] = after
            else:
                rec["note"] = "메인과 같은 내용 — 변경 없음"
        rec["receipts"] = [{"path": r["path"], "status": r["status"], "errors": r["errors"]} for r in receipts]
        rec["lines"] = [{"path": p_, "ok": ok} for p_, ok in lines]
        L.append(d, "external_pushes", rec)
        out.append({**rec, "status": "processed"})
    return out


def _check_lines(main: Path, dst: str) -> bool:
    base = main / ("league/sandbox" if dst.startswith("league/sandbox/") else "league")
    r = subprocess.run([sys.executable, str(main / "tools" / "dashboard_data.py"), "--check-lines", str(main / dst),
                        "--base", str(base)], cwd=main, capture_output=True, text=True)
    print(r.stdout.strip())
    return r.returncode == 0


# ───────── 메인 → 전용 저장소 사본 (원 가격 없음, 허용 목록만) ─────────
MIRROR_FILES = ["league/public/results.json", "league/config.json", "league/agents/roster.json",
                "league/imports/shushu/roster.json", "docs/codex-team-guide.md", "docs/results-bundle.md",
                "requirements.txt", ".gitattributes"]
MIRROR_GLOBS = ["docs/codex-notices/*.md", "league/universe/*.json", "tools/*.py",
                "league/rounds/*/snapshot.json", "league/rounds/*/snapshot.json.sha256",
                "league/sandbox/rounds/*/snapshot.json", "league/sandbox/rounds/*/snapshot.json.sha256",
                "league/imports/shushu/daily-procedure.md", "league/imports/shushu/watch-procedure-v1.9.md",
                "league/imports/shushu/weekly-review-v2.1.md", "league/imports/shushu/rule-conformance.md",
                "league/imports/shushu/agents/**/*", "docs/codex-notices/replies/*.md"]
MIRROR_LEDGERS = ["weekly_decisions", "guidelines", "approvals", "outages"]      # 원 가격이 없는 원장만
NO_PRICE = re.compile(r'"(base_close|eval_close|close|amount|adj_close|open|high|low)"\s*:')


def mirror(main: Path, ext: Path, today: date | None = None) -> list[str]:
    today = today or datetime.now(L.KST).date()
    dst = ext / MIRROR_DIR
    if dst.exists():
        shutil.rmtree(dst)
    files = list(MIRROR_FILES) + sorted({str(p.relative_to(main)) for g in MIRROR_GLOBS for p in main.glob(g) if p.is_file()})
    for name in MIRROR_LEDGERS:
        files.append(f"league/ledger/{name}.jsonl")
    wrote = []
    for f in files:
        src = main / f
        if not src.exists():
            continue
        if f.endswith((".json", ".jsonl")) and NO_PRICE.search(src.read_text(errors="replace")) and not f.startswith("tools/"):
            raise SystemExit(f"사본 중단: {f} 에 가격처럼 보이는 칸이 있음")
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / f)
        wrote.append(f)
    # 슈슈 팀 영수증과 연결 기록, 업데이트 계획(이번 주·지난주)
    subs = [r for dd in (main / "league", main / "league" / "sandbox") for r in L.read_ledger(dd, "submissions")
            if r.get("team") in ("shushu", "sandbox-shushu")]
    (dst / "receipts-shushu.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in subs))
    sync = L.read_ledger(main / "league", "external_pushes")
    (dst / "sync-log.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sync))
    plans = {}
    for wk in sorted({L.iso_week(today), L.iso_week(today - timedelta(days=7))}):
        try:
            plans[wk] = L.update_plan(main / "league", wk)
        except Exception as e:  # noqa: BLE001
            plans[wk] = {"error": str(e)}
    (dst / "update-plan.json").write_text(json.dumps(plans, ensure_ascii=False, indent=1) + "\n")
    (dst / "README.md").write_text(
        "# from-league (자동 사본, 고치지 마세요)\n\n"
        "메인 리그 저장소에서 원 가격이 없는 자료만 자동으로 복사한 폴더입니다. 여기를 고쳐도 메인에 반영되지 않고 다음 동기화 때 덮어씁니다.\n\n"
        "- `receipts-shushu.jsonl`: 슈슈 팀 제출 영수증(실전 shushu, 연습 sandbox-shushu)\n"
        "- `sync-log.jsonl`: 이 저장소 push를 메인이 처리한 기록(push 시각, 가져온 파일, 영수증)\n"
        "- `league/public/results.json`: 공유 결과 묶음(마감 전 종목·원 가격 없음)\n"
        "- `update-plan.json`: 규칙 v2.1 업데이트 계획(이번 주·지난주)\n"
        "- `docs/codex-notices/`: 로로 팀 공지·회신\n"
        "- `tools/`, `league/config.json`, `league/universe/`, `league/agents/roster.json`: CSV 사전 검증용\n"
        "  예: `cd from-league && python3 tools/league.py import-csv ../submit/<날짜>.csv --team shushu --dry-run`\n")
    return wrote


# ───────── 슈슈 깨우기: 전용 저장소 운영 채널 이슈에 @codex 댓글 (Codex 클라우드가 작업을 시작) ─────────
CHANNEL_TITLE = "리그 운영 채널 (자동)"
SIGN = "\n\n— 로로 팀 자동 메시지 (메인 리그 저장소 league-shushu-sync). 답이나 질문은 `to-roro/<날짜>-<주제>.md` 파일로 push해 주세요."
PROC = "`from-league/league/imports/shushu/daily-procedure.md`"


def _notes(main: Path) -> list[Path]:
    n = main / "docs" / "codex-notices"
    return sorted(list(n.glob("*.md")) + list((n / "replies").glob("*.md")))


def notice_keys(main: Path) -> list[str]:
    return [p.name + ":" + L._sha(p)[:12] for p in _notes(main)]


def due_wakes(main: Path, now: datetime) -> list[dict]:
    """지금 보낼 깨우기 목록. 같은 종류·날짜는 한 번만(원장 shushu_wakes)."""
    d = main / "league"
    cfg = L.load_config(d)
    sent = {(w["kind"], w["key"]) for w in L.read_ledger(d, "shushu_wakes")}
    today, hm = now.date(), now.strftime("%H:%M")
    rd = today.isoformat()
    out = []
    add = lambda kind, key, body: (kind, key) not in sent and out.append({"kind": kind, "key": key, "body": body})
    mk = sorted(L.open_markets(today, cfg)) if today.weekday() < 5 else []
    live = rd >= (cfg.get("season_start") or "9999")
    subs = [s for s in L.read_ledger(d, "submissions") if s.get("team") == "shushu" and s.get("round_date") == rd]
    st = {s["status"] for s in subs}
    if mk and live and "07:00" <= hm < "08:00":
        add("round", rd, f"@codex 오늘({rd}) 실전 라운드를 진행해 주세요. 열린 시장: {'·'.join(mk)}. {PROC} 절차대로 분석하고, "
            f"**08:20까지 `submit/{rd}.sha256` 하나만** push해 주세요(원본·토론·대사는 넣지 않음). 마감 08:30 KST, 판정은 이 저장소의 push 시각입니다.")
    if mk and live and "08:30" < hm < "11:40" and "committed" in st and "accepted" not in st:
        add("reveal", rd, f"@codex 지문 영수증 `committed`를 확인했습니다. 이제 지문과 바이트가 똑같은 `submit/{rd}.csv`와 `submit/{rd}-debate.md`를 push하고, "
            f"`from-league/receipts-shushu.jsonl`에서 `accepted`를 확인한 뒤 `lines/{rd}-shushu.json`(한 줄 대사)을 push해 주세요. 원본 공개 마감 12:00 KST.")
    if mk and live and "08:30" < hm < "11:40" and not ({"committed", "accepted"} & st):
        add("missing", rd, f"@codex 오늘({rd}) 지문 영수증이 없습니다. 08:30 전에 `submit/{rd}.sha256`을 push했다면 "
            "`from-league/sync-log.jsonl`에서 처리 결과를 확인해 주세요. 마감 뒤 지문은 인정되지 않습니다(소급 없음). 확인 결과를 `to-roro/`로 알려 주세요.")
    if today.weekday() == 5 and hm >= "10:40":
        wk = L.iso_week(today)
        add("review", wk, f"@codex 이번 주({wk}) 토요일 잠정 복기를 진행해 주세요. `from-league/league/imports/shushu/weekly-review-v2.1.md` 절차와 "
            "`from-league/update-plan.json`(잠정)을 쓰고, 개선안이 있으면 `to-roro/`로 요약(근거 pick_id 포함)을 보내 주세요. 최종 자격은 월요일 06:30 마감 뒤 확정됩니다.")
    if today.weekday() == 0 and hm >= "06:35":
        wk = L.iso_week(today - timedelta(days=7))
        add("close", wk, f"@codex 주간 마감({wk})이 끝났습니다. `from-league/league/ledger/weekly_decisions.jsonl`과 `from-league/update-plan.json`으로 "
            "리그별 결과와 최종 업데이트 자격을 확인하고, 바뀐 점이나 승인 요청이 있으면 07:00까지 `to-roro/`로 보내 주세요.")
    # 새 공지·회신 (메인 docs/codex-notices) — 내용 해시로 판단
    new = [p for p in _notes(main) if ("notice", p.name + ":" + L._sha(p)[:12]) not in sent]
    if new and not (mk and live and "06:50" <= hm < "12:00"):          # 라운드 시간에는 보내지 않는다
        names = ", ".join(f"`{p.relative_to(main / 'docs')}`" for p in new[:10])
        out.append({"kind": "notice", "key": "|".join(p.name + ":" + L._sha(p)[:12] for p in new),
                    "keys": [p.name + ":" + L._sha(p)[:12] for p in new],
                    "body": f"@codex 로로 팀 공지·회신이 새로 왔습니다: {names} (`from-league/docs/` 아래). 읽고 슈슈 팀 절차에 반영할 것이 있으면 반영하고, "
                            "답이나 이견은 `to-roro/<날짜>-<주제>.md`로 push해 주세요. 운영자 승인이 필요한 결정은 그렇게 표시해 주세요."})
    return out


def _api(method: str, url: str, token: str, body: dict | None = None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": UA, "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def wake(main: Path, repo: str, token: str, now: datetime | None = None, post=None) -> list[dict]:
    now = now or datetime.now(L.KST)
    todo = due_wakes(main, now)
    if not any(w["kind"] == "notice" for w in L.read_ledger(main / "league", "shushu_wakes")):
        # 처음 켤 때 이미 있는 공지는 보낸 것으로 표시만 한다(이전 공지는 운영자가 이미 전달함)
        for k in notice_keys(main):
            L.append(main / "league", "shushu_wakes", {"kind": "notice", "key": k, "at": now.isoformat(timespec="seconds"), "url": "seeded"})
        todo = [w for w in todo if w["kind"] != "notice"]
    if not todo:
        return []
    api = f"https://api.github.com/repos/{repo}"
    if post is None:
        issues = _api("GET", f"{api}/issues?state=open&per_page=100", token) or []
        num = next((i["number"] for i in issues if i.get("title") == CHANNEL_TITLE and "pull_request" not in i), None)
        if num is None:
            num = _api("POST", f"{api}/issues", token, {"title": CHANNEL_TITLE, "body":
                       "로로 팀(메인 리그 저장소)이 자동으로 남기는 운영 채널입니다. 댓글의 @codex 요청으로 슈슈 팀 작업이 시작됩니다." + SIGN})["number"]
        post = lambda b: _api("POST", f"{api}/issues/{num}/comments", token, {"body": b})["html_url"]
    sent = []
    for w in todo:
        url = post(w["body"] + SIGN)
        for k in w.get("keys", [w["key"]]):
            L.append(main / "league", "shushu_wakes", {"kind": w["kind"], "key": k, "at": now.isoformat(timespec="seconds"), "url": url})
        sent.append({**w, "url": url})
    return sent


def main_():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pull", "mirror", "wake"])
    ap.add_argument("--ext", required=True, help="전용 저장소 체크아웃 폴더")
    ap.add_argument("--repo", help="owner/name (기본: config shushu_repo.repo)")
    ap.add_argument("--branch")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--run-url", default="")
    a = ap.parse_args()
    cfg = (L.load_config(ROOT / "league").get("shushu_repo") or {})
    repo, branch = a.repo or cfg.get("repo"), a.branch or cfg.get("branch", "main")
    ext = Path(a.ext).resolve()
    if a.cmd == "pull":
        tok = os.environ.get("SHUSHU_REPO_TOKEN")
        if not (repo and tok):
            sys.exit("저장소 이름 또는 SHUSHU_REPO_TOKEN 없음")
        res = pull(ROOT, ext, fetch_activity(repo, tok), repo, run_id=a.run_id, run_url=a.run_url)
        for r in res:
            if r["status"] == "held_until_deadline":
                print(f"보류(마감 전 공개 파일): {', '.join(r['files'])} — 08:30 뒤 다음 실행에서 처리")
            else:
                rs = "; ".join(f"{x['path']} {x['status']} {' '.join(x['errors'])}".strip() for x in r["receipts"]) or r.get("note") or "제출 파일 없음"
                print(f"push {r['s_after'][:7]} {r['pushed_at']} → {rs}")
                for x in r["lines"]:
                    print(f"  대사 {x['path']}: {'통과' if x['ok'] else '검사 실패'}")
        if not res:
            print("새 push 없음")
        if any(not x["ok"] for r in res for x in r.get("lines", [])):
            sys.exit(3)
    elif a.cmd == "wake":
        tok = os.environ.get("SHUSHU_REPO_TOKEN")
        if not (repo and tok):
            sys.exit("저장소 이름 또는 SHUSHU_REPO_TOKEN 없음")
        for w in wake(ROOT, repo, tok):
            print(f"깨우기 {w['kind']} {w['key'][:40]} → {w['url']}")
    else:
        print(f"사본 {len(mirror(ROOT, ext))}개 파일")


if __name__ == "__main__":
    main_()
