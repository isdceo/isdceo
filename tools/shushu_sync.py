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
ZERO = "0" * 40
MIRROR_DIR = "from-league"


def git(*a, cwd) -> str:
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def git_bytes(*a, cwd) -> bytes:
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True).stdout


def map_path(p: str):
    """허용 경로면 (메인 경로, 라운드 날짜, 마감 전 보류 여부, 종류). 날짜가 실제 날짜가 아니면 None."""
    for rx, tmpl, hold, kind in RULES:
        m = rx.match(p)
        if m:
            rd = re.search(r"\d{4}-\d{2}-\d{2}", m.group(1)).group(0)
            try:
                date.fromisoformat(rd)
            except ValueError:
                return None
            return tmpl.format(m.group(1)), rd, hold, kind
    return None


ACT_TYPES = {"push", "force_push", "branch_creation", "pr_merge", "merge_queue_merge"}
DELETE_TYPES = {"branch_deletion"}     # 기록만 받고 처리하지 않는다(판정 예외에 쓰지 않음)
SETTLE = timedelta(minutes=2)          # activity 목록 반영 지연: 이보다 최근 push는 다음 실행에서 (순서 꼬임 방지)
MAX_BYTES = 1_000_000
SHA_LINE = re.compile(rb"^[0-9a-f]{64}(  \S{1,80})?\n?$")


def fetch_activity(repo: str, token: str) -> list[dict]:
    """GitHub 서버가 기록한 push 계열 활동(모든 브랜치, 오래된 것부터). 전용 저장소 사용자가 바꿀 수 없는 시각이다.
    새 브랜치 첫 push(branch_creation)·강제 push·PR 병합도 받는다. Codex 클라우드처럼 작업 브랜치에 push하고 PR을 여는 방식은
    그 브랜치 push 시각으로 판정한다(병합 시각이 아님). 병합으로 같은 파일이 다시 들어오면 메인과 내용이 같아 영수증을 새로 만들지 않는다."""
    url = f"https://api.github.com/repos/{repo}/activity?per_page=100&direction=asc"
    out = []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": UA,
                                                  "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out += json.loads(r.read() or b"[]")
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link") or "")
            url = nxt.group(1) if nxt else None
    out = [a for a in out if str(a.get("ref", "refs/heads/")).startswith("refs/heads/") and (
           a.get("activity_type") in DELETE_TYPES or (a.get("activity_type", "push") in ACT_TYPES and a.get("after") and a["after"] != ZERO))]
    return sorted(out, key=lambda a: (a["timestamp"], a["id"]))


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(L.KST)


def _have(ext: Path, sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ext, capture_output=True).returncode == 0


def _changed(ext: Path, before: str, after: str, prior_main: str | None = None, first: bool = False) -> list[str]:
    for sha in (after, before, prior_main):
        if sha and sha != ZERO and not _have(ext, sha):
            subprocess.run(["git", "fetch", "-q", "origin", sha], cwd=ext, capture_output=True)
    if not _have(ext, after):
        raise RuntimeError(f"커밋 {after[:12]}를 받을 수 없음(브랜치 삭제·강제 push?)")
    base = before if before and before != ZERO and _have(ext, before) else None
    if base is None and prior_main and prior_main != after and _have(ext, prior_main):
        # 새 브랜치·강제 push: 이 push 전 마지막 기본 브랜치 상태와 갈라진 지점부터(오래된 기준의 브랜치가 옛 내용을 '수정'으로 보이지 않게)
        r = subprocess.run(["git", "merge-base", prior_main, after], cwd=ext, capture_output=True, text=True)
        mb = r.stdout.strip() if r.returncode == 0 else ""
        if mb == after:
            return []                                  # 이미 기본 브랜치에 들어 있는 커밋 — 새 파일 없음
        base = mb or None
    if base:
        return git("diff", "--no-renames", "--name-only", "--diff-filter=AMT", base, after, cwd=ext).splitlines()
    if first:                                          # 저장소의 맨 첫 push만 트리 전체
        return git("ls-tree", "-r", "--name-only", after, cwd=ext).splitlines()
    raise RuntimeError("비교 기준(이전 커밋)을 정할 수 없음 — 트리 전체로 대신하지 않음")


def _round_day(day: date, cfg: dict) -> bool:
    return day.weekday() < 5 and bool(L.open_markets(day, cfg))


def _first_round_on_or_after(day: date, cfg: dict) -> date:
    for _ in range(30):
        if _round_day(day, cfg):
            return day
        day += timedelta(days=1)
    return day


def hold_until(kind: str, rd: str, pushed: datetime, cfg: dict) -> datetime | None:
    """마감 전 공개 차단. 원본·토론·대사: 라운드 날 마감 전 push면 (그날, 파일 날짜) 중 늦은 쪽의 마감까지,
    마감 뒤 push면 파일 날짜의 마감이 아직이면 그때까지(다음 라운드 정보는 공지의 '종목 언급 금지' 정책으로 막는다).
    메시지: 라운드 날 12:00 전에 push했으면 그날 12:00까지. 지문은 보류 없음."""
    if kind == "commitment":
        return None
    if kind == "message":
        noon = pushed.replace(hour=12, minute=0, second=0, microsecond=0)
        return noon if _round_day(pushed.date(), cfg) and pushed < noon else None
    R = _first_round_on_or_after(pushed.date(), cfg)
    if pushed < L.lock_deadline(R, cfg):              # 그날 라운드 마감 전 push: 파일 날짜가 지난 날이어도 그 마감까지
        return L.lock_deadline(max(R, date.fromisoformat(rd)), cfg)
    dl = L.lock_deadline(date.fromisoformat(rd), cfg)  # 마감 뒤 push: 앞으로 올 라운드 이름이면 그 마감까지
    return dl if dl > pushed else None


def in_round_window(now: datetime, cfg: dict) -> bool:
    """라운드 날 06:50~12:00: 이 시간에는 메시지를 메인에 들이지 않는다(로로 팀 라운드 진행 중)."""
    hm = now.strftime("%H:%M")
    return _round_day(now.date(), cfg) and "06:50" <= hm < "12:00"


def _team_cfg(main: Path, dst: str) -> dict:
    team = "sandbox-shushu" if dst.startswith(("league/imports/sandbox-", "league/sandbox/")) else "shushu"
    return L.load_config(L.ledger_dir_for(team, main))


def _classify(ext: Path, act: dict, files: list[str], main: Path) -> tuple[list[dict], int, list[str]]:
    """허용 파일 → 작업 단위, 무시한 파일 수, 문제(형식·크기) 설명."""
    units, ignored, problems = [], 0, []
    for f in files:
        m = map_path(f)
        if not m:
            ignored += 1
            continue
        dst, rd, _, kind = m
        spec = f"{act['after']}:{f}"
        t = subprocess.run(["git", "cat-file", "-t", spec], cwd=ext, capture_output=True, text=True).stdout.strip()
        size = int(subprocess.run(["git", "cat-file", "-s", spec], cwd=ext, capture_output=True, text=True).stdout.strip() or 0) if t == "blob" else 0
        if t != "blob" or size > MAX_BYTES:
            problems.append(f"{f}: 일반 파일이 아니거나 {MAX_BYTES:,}바이트 초과 — 무시")
            continue
        if kind == "commitment" and not SHA_LINE.match(git_bytes("show", spec, cwd=ext)):
            problems.append(f"{f}: 지문 파일은 64자리 sha256(+ 두 칸 + 파일 이름) 한 줄만 — 무시")
            continue
        units.append({"file": f, "dst": dst, "rd": rd, "kind": kind})
    return units, ignored, problems


MAX_TRIES = 3            # 받을 수 없음 등 일시 오류는 이만큼 실행에서 다시 시도한 뒤에만 오류로 확정
TEAMS = ("shushu", "sandbox-shushu")


def _next_round(pushed: datetime, cfg: dict) -> date:
    """push 시각보다 마감이 늦은 첫 라운드(전날 저녁·금요일 오후 push도 다음 라운드의 마감 전 push로 본다)."""
    R = _first_round_on_or_after(pushed.date(), cfg)
    return R if pushed < L.lock_deadline(R, cfg) else _first_round_on_or_after(R + timedelta(days=1), cfg)


def tainted(recs: list[dict]) -> set[tuple[str, str]]:
    """(팀, 라운드): 마감 전 push 중 끝내 받을 수 없는 것이 있어 자동 접수하지 않는 라운드(운영자 확인 대기)."""
    t = {(x["team"], x["round"]) for x in recs if x.get("type") == "taint"}
    return t - {(x["team"], x["round"]) for x in recs if x.get("type") == "untaint"}


def _name(u: dict) -> str:
    """원장에 남길 이름. 메시지는 주제(파일 이름)에 내용을 담을 수 있으니 보류 중에는 해시만."""
    return u["file"] if u["kind"] != "message" else "to-roro/#" + L.hashlib.sha256(u["file"].encode()).hexdigest()[:12]


def _ledger_snapshot(main: Path) -> dict:
    out = {}
    for dd in (main / "league" / "ledger", main / "league" / "sandbox" / "ledger"):
        for f in dd.glob("*.jsonl") if dd.exists() else []:
            out[f] = f.stat().st_size
    return out


def _rollback(main: Path, prev: str, snap: dict, dsts: list[str]):
    """지금 처리하던 push 하나만 되돌린다(앞 push들의 원장 기록은 그대로)."""
    git("reset", "-q", "--soft", prev, cwd=main)
    for dst in dsts:
        subprocess.run(["git", "reset", "-q", "--", dst], cwd=main, capture_output=True)
        if subprocess.run(["git", "cat-file", "-e", f"{prev}:{dst}"], cwd=main, capture_output=True).returncode == 0:
            git("checkout", prev, "--", dst, cwd=main)
        else:
            (main / dst).unlink(missing_ok=True)
    for dd in (main / "league" / "ledger", main / "league" / "sandbox" / "ledger"):
        for f in dd.glob("*.jsonl") if dd.exists() else []:
            if f not in snap:
                f.unlink()
            elif f.stat().st_size != snap[f]:
                with f.open("r+b") as fh:
                    fh.truncate(snap[f])


def pull(main: Path, ext: Path, activities: list[dict], repo: str, now: datetime | None = None,
         run_id: str = "", run_url: str = "", base_branch: str = "main") -> list[dict]:
    """전용 저장소 push를 시각 순으로 처리한다(원장 external_pushes에 기록, 같은 push는 한 번만).
    마감 전 공개 파일은 그 파일만 뒤로 미루고(held), 나머지는 계속 처리한다. 미룬 파일은 때가 되면 원래 push 시각으로 처리한다."""
    now = now or datetime.now(L.KST)
    d = main / "league"
    cfg = L.load_config(d)
    recs = [x for x in L.read_ledger(d, "external_pushes") if x.get("repo") == repo]
    done = {x["activity_id"] for x in recs if x.get("type", "push") == "push"}
    released = {x["held_id"] for x in recs if x.get("type") == "release"}
    tries = {}
    for x in recs:
        if x.get("type") in ("push_error", "release_error"):
            tries[(x["type"], x.get("held_id") or x["activity_id"])] = tries.get((x["type"], x.get("held_id") or x["activity_id"]), 0) + 1
    groups, out = [], []
    block = None
    # 1) 새 push
    main_ref = f"refs/heads/{base_branch}"
    for i, act in enumerate(activities):
        if act.get("activity_type") in DELETE_TYPES:
            continue
        if act["id"] in done or _ts(act["timestamp"]) > now - SETTLE:
            continue
        pushed = _ts(act["timestamp"])
        R = _next_round(pushed, cfg)
        dl = L.lock_deadline(R, cfg)
        base = {"repo": repo, "activity_id": act["id"], "type": "push", "activity_type": act.get("activity_type", "push"),
                "ref_hash": L.hashlib.sha256(str(act.get("ref")).encode()).hexdigest()[:12],
                "s_after": act["after"], "pushed_at": pushed.isoformat(), "actor": (act.get("actor") or {}).get("login"),
                "run_id": str(run_id)}
        # 기준: before가 없거나 받을 수 없으면 '이 push 전 마지막 기본 브랜치 push'의 결과(서버 기록이라 결정적)
        prior_main = next((a["after"] for a in reversed(activities[:i]) if a.get("ref", main_ref) == main_ref), None)
        try:
            files = _changed(ext, act.get("before"), act["after"], prior_main, first=(i == 0))
            if files and all(f.startswith(MIRROR_DIR + "/") for f in files):
                continue                               # 메인이 보낸 사본 push — 기록하지 않음
            units, ignored, problems = _classify(ext, act, files, main)
        except Exception as e:  # noqa: BLE001  — 한 push의 문제로 동기화 전체가 멈추지 않게
            n = tries.get(("push_error", act["id"]), 0) + 1
            # '마감 전에 지워졌으니 대체됨' 같은 예외는 두지 않는다: 태그 등 기록에 안 남는 ref로 커밋을 살려 두면
            # 마감 뒤 '받을 수 있음/없음'을 골라 지문을 고를 수 있기 때문(5차 검수 S1). 받을 수 없음은 결코 유리해지지 않게 한다.
            superseded = False
            final = n >= MAX_TRIES
            L.append(d, "external_pushes", {**base, "type": "push" if final else "push_error", "status": "superseded" if superseded else "error",
                                            "attempt": n, "error": str(e)[:300]})
            out.append({**base, "status": ("superseded" if superseded else "error") if final else "retry", "error": str(e)[:300],
                        "receipts": [], "lines": []})
            if final and not superseded and now >= dl:
                # 마감이 지나도록 받을 수 없음: 뒤의 지문·원본을 자동으로 인정하면 '골라 되살리기'가 가능해진다 → 그 라운드 운영자 확인
                for t_ in TEAMS:
                    L.append(d, "external_pushes", {"repo": repo, "type": "taint", "team": t_, "round": R.isoformat(), "activity_id": act["id"],
                                                    "s_after": act["after"], "pushed_at": pushed.isoformat(), "reason": "마감 전 push를 마감 뒤까지 받을 수 없음"})
                recs = [x for x in L.read_ledger(d, "external_pushes") if x.get("repo") == repo]
            elif not final:
                block = pushed                         # 순서를 지키려고 이 뒤의 push·보류 해제는 다음 실행으로 미룬다
                break
            continue
        ready, held = [], []
        for u in units:
            until = hold_until(u["kind"], u["rd"], pushed, _team_cfg(main, u["dst"]))
            (held if (until and now <= until) or (u["kind"] == "message" and in_round_window(now, cfg)) else ready).append({**u, "until": until})
        groups.append({"act": act, "pushed": pushed, "base": base, "ready": ready, "held": held,
                       "ignored": ignored, "problems": problems})
    # 2) 미뤄 둔 파일 중 때가 된 것
    for h in [x for x in recs if x.get("type") == "held" and x["held_id"] not in released]:
        until = datetime.fromisoformat(h["until"]) if h.get("until") else None
        if h.get("taint") and (("sandbox-shushu" if str(h.get("dst", "")).startswith("league/imports/sandbox-") else "shushu"), h["rd"]) in tainted(recs):
            continue
        if (until and now <= until) or (h["kind"] == "message" and in_round_window(now, cfg)):
            continue
        groups.append({"act": {"id": h["activity_id"], "after": h["s_after"], "actor": {"login": h.get("actor")}},
                       "pushed": datetime.fromisoformat(h["pushed_at"]), "release": h, "base": None,
                       "ready": [{"file": h.get("file"), "file_hash": h.get("file_hash"), "dst": h.get("dst"), "rd": h["rd"], "kind": h["kind"]}],
                       "held": [], "ignored": 0, "problems": []})
    if block is not None:
        groups = [g for g in groups if g["pushed"] < block]
    groups.sort(key=lambda g: (g["pushed"], str(g["act"]["id"])))
    bad = tainted(recs)
    def _team_of(u):
        return "sandbox-shushu" if str(u.get("dst") or "").startswith(("league/imports/sandbox-", "league/sandbox/")) else "shushu"
    for g in groups:
        act, pushed = g["act"], g["pushed"]
        # 확인 대기 라운드의 지문·원본은 처리하지 않고 보류로 둔다(운영자가 untaint 하면 원래 push 시각으로 처리)
        stuck = [u for u in g["ready"] if u["kind"] in ("commitment", "reveal") and (_team_of(u), u["rd"]) in bad]
        if stuck:
            if g.get("release"):
                continue
            g["ready"] = [u for u in g["ready"] if u not in stuck]
            g["held"] = g["held"] + [{**u, "until": None, "taint": True} for u in stuck]
        prev, snap = git("rev-parse", "HEAD", cwd=main), _ledger_snapshot(main)
        try:
            if g.get("release"):
                _restore_held(ext, act, g["ready"])
            receipts, lines, note = _apply(main, ext, repo, act, pushed, g["ready"], run_id, run_url, bad)
        except L.CommitmentPending as e:
            _rollback(main, prev, snap, [u["dst"] for u in g["ready"] if u.get("dst")])   # 이 push만 되돌리고 다음 실행에서 다시
            out.append({"activity_id": act["id"], "status": "pending", "note": str(e), "receipts": [], "lines": []})
            break
        except Exception as e:  # noqa: BLE001
            _rollback(main, prev, snap, [u["dst"] for u in g["ready"] if u.get("dst")])
            kind = "release_error" if g.get("release") else "push_error"
            key = g["release"]["held_id"] if g.get("release") else act["id"]
            n = tries.get((kind, key), 0) + 1
            final = n >= MAX_TRIES
            rec = {"repo": repo, "activity_id": act["id"], "status": "error", "attempt": n, "error": str(e)[:300],
                   "pushed_at": pushed.isoformat(), "run_id": str(run_id)}
            if g.get("release"):
                rec.update(type="release" if final else "release_error", held_id=key)
            else:
                rec.update({**g["base"], "type": "push" if final else "push_error", "status": "error", "attempt": n, "error": str(e)[:300]})
            L.append(d, "external_pushes", rec)
            out.append({**rec, "status": "error" if final else "retry", "receipts": [], "lines": []})
            if g.get("release"):
                u = g["ready"][0]
                team = "sandbox-shushu" if str(u.get("dst") or "").startswith(("league/imports/sandbox-", "league/sandbox/")) else "shushu"
                rr = max(u["rd"], _first_round_on_or_after(pushed.date(), cfg).isoformat())
                if final and (u["kind"] in ("reveal", "debate") or g["release"].get("taint")):
                    # 보류한 원본을 끝내 꺼낼 수 없음: 같은 라운드의 다른 원본을 대신 인정하지 않는다
                    L.append(d, "external_pushes", {"repo": repo, "type": "taint", "team": team, "round": rr, "activity_id": act["id"],
                                                    "pushed_at": pushed.isoformat(), "reason": "보류한 원본을 받을 수 없음"})
                    bad.add((team, rr))
                elif not final:
                    break                              # 순서를 지키려고 뒤의 처리는 다음 실행으로
            continue
        summary = {"receipts": [{"path": r["path"], "status": r["status"], "errors": r["errors"]} for r in receipts],
                   "lines": [{"path": p_, "ok": ok} for p_, ok in lines]}
        if g.get("release"):
            u = g["ready"][0]
            L.append(d, "external_pushes", {"repo": repo, "activity_id": act["id"], "type": "release", "held_id": g["release"]["held_id"],
                                            "file": u["file"], "pushed_at": pushed.isoformat(), "run_id": str(run_id), "note": note, **summary})
            out.append({"activity_id": act["id"], "status": "released", "s_after": act["after"], "pushed_at": pushed.isoformat(),
                        "files": [u["file"]], "note": note, **summary})
            continue
        rec = {**g["base"], "status": "processed", "files": [u["file"] for u in g["ready"]],
               "held_files": [_name(u) for u in g["held"]], "ignored_count": g["ignored"], "problems": g["problems"], "note": note, **summary}
        L.append(d, "external_pushes", rec)
        for k, u in enumerate(g["held"]):
            h = {"repo": repo, "activity_id": act["id"], "type": "held", "held_id": f"{act['id']}#{k}", "rd": u["rd"], "kind": u["kind"],
                 "s_after": act["after"], "pushed_at": pushed.isoformat(), "actor": rec["actor"],
                 "until": u["until"].isoformat() if u["until"] else None, "taint": bool(u.get("taint"))}
            if u["kind"] == "message":                 # 메시지 이름은 보류 중 원장에 남기지 않는다(해시만)
                h["file_hash"] = L.hashlib.sha256(u["file"].encode()).hexdigest()
            else:
                h.update(file=u["file"], dst=u["dst"])
            L.append(d, "external_pushes", h)
        out.append(rec)
    return out


def _restore_held(ext: Path, act: dict, units: list[dict]):
    """보류 해제: 커밋을 다시 받아 오고, 메시지는 해시로 실제 이름을 찾는다."""
    if not _have(ext, act["after"]):
        subprocess.run(["git", "fetch", "-q", "origin", act["after"]], cwd=ext, capture_output=True)
    if not _have(ext, act["after"]):
        raise RuntimeError(f"보류한 파일의 커밋 {act['after'][:12]}를 받을 수 없음")
    for u in units:
        if u.get("file") is None:
            names = git("ls-tree", "-r", "--name-only", act["after"], "--", "to-roro", cwd=ext).splitlines()
            hit = next((n for n in names if L.hashlib.sha256(n.encode()).hexdigest() == u["file_hash"]), None)
            if not hit:
                raise RuntimeError("보류한 메시지 파일을 찾을 수 없음")
            u["file"], u["dst"] = hit, map_path(hit)[0]


def _apply(main: Path, ext: Path, repo: str, act: dict, pushed: datetime, units: list[dict], run_id: str, run_url: str,
           bad: set | None = None):
    """파일을 바이트 그대로 메인에 쓰고 커밋한 뒤, 전용 저장소 push 시각으로 영수증을 판정한다."""
    if not units:
        return [], [], ""
    notes, wrote = [], []
    for u in units:
        if u["kind"] in ("commitment", "reveal"):
            team = "sandbox-shushu" if u["dst"].startswith("league/imports/sandbox-") else "shushu"
            if (team, u["rd"]) in (bad or set()):
                notes.append(f"{u['file']}: {u['rd']} 라운드는 운영자 확인 대기(마감 전 push 중 받을 수 없는 것이 있음) — 자동 접수 안 함")
                continue
            subs = L.read_ledger(L.ledger_dir_for(team, main), "submissions")
            want = "committed" if u["kind"] == "commitment" else "accepted"
            if any(x.get("path") == u["dst"] and x.get("status") == want for x in subs):
                notes.append(f"{u['file']}: 이미 {want} — 메인 파일을 덮어쓰지 않음(다시 낸 것은 인정되지 않음)")
                continue
        if u["kind"] == "debate" and (main / u["dst"]).exists():
            # 원본이 접수된 라운드의 토론 기록은 처음 들어온 바이트로 고정(정정은 to-roro/ 메시지로 남긴다)
            team = "sandbox-shushu" if u["dst"].startswith("league/imports/sandbox-") else "shushu"
            csv_path = u["dst"].replace("-debate.md", ".csv")
            if any(x.get("path") == csv_path and x.get("status") == "accepted" for x in L.read_ledger(L.ledger_dir_for(team, main), "submissions")):
                notes.append(f"{u['file']}: 원본 접수 뒤의 토론 기록 변경 — 처음 기록을 유지하고 덮어쓰지 않음")
                continue
        p = main / u["dst"]
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = git_bytes("show", f"{act['after']}:{u['file']}", cwd=ext)
        p.write_bytes(raw)                                                             # 바이트 그대로
        git("add", u["dst"], cwd=main)
        u["sha256"] = L.hashlib.sha256(raw).hexdigest()
        wrote.append(u)
    if not wrote or not git("status", "--porcelain", "--", *[u["dst"] for u in wrote], cwd=main):
        return [], [], "; ".join(notes + ["메인과 같은 내용 — 변경 없음"] if wrote else notes)
    prev = git("rev-parse", "HEAD~0", cwd=main)
    git("-c", "user.name=league-bot", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit", "-q", "-m", f"league: shushu repo push {act['after'][:7]} ({pushed.isoformat(timespec='seconds')})",
        "-m", f"source: {repo}@{act['after']} activity {act['id']}", cwd=main)
    after = git("rev-parse", "HEAD", cwd=main)
    event = {"before": prev, "after": after, "ref": "refs/heads/main", "commits": [],
             "pusher": {"name": f"{repo}:{(act.get('actor') or {}).get('login')}"},
             "repository": {"pushed_at": int(pushed.timestamp())},
             "judged_by": "shushu_repo.activity.timestamp",
             # 파일마다: 원래 push가 그 파일 라운드의 마감 전이면 '봉인'(비공개 저장소에 있었고 메인에는 마감 뒤에만 들어옴).
             # 원본은 마감 전에는 늘 보류되므로 여기까지 왔다면 반입 시점은 마감 뒤다. 첫 발견이 마감 뒤인 경우도 같다.
             "sealed_paths": [u["dst"] for u in wrote if u["kind"] == "reveal"
                              and pushed <= L.lock_deadline(date.fromisoformat(u["rd"]), _team_cfg(main, u["dst"]))],
             "source": {"repo": repo, "commit": act["after"], "activity_id": act["id"]}}
    receipts = L.process_push(event, run_id=run_id, run_url=run_url, cwd=main)
    lines = [(u["dst"], _check_lines(main, u["dst"])) for u in wrote if u["kind"] == "lines"]
    notes += [f"{u['dst']} sha256 {u['sha256']}" for u in wrote if u["kind"] in ("debate", "lines", "message")]   # 출처·해시 기록
    return receipts, lines, "; ".join(notes)


def _check_lines(main: Path, dst: str) -> bool:
    base = main / ("league/sandbox" if dst.startswith("league/sandbox/") else "league")
    r = subprocess.run([sys.executable, str(main / "tools" / "dashboard_data.py"), "--check-lines", str(main / dst),
                        "--base", str(base)], cwd=main, capture_output=True, text=True)
    print(r.stdout.strip())
    return r.returncode == 0


# ───────── 메인 → 전용 저장소 사본 (원 가격 없음, 허용 목록만) ─────────
MIRROR_FILES = ["league/public/results.json", "league/agents/roster.json",
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
# 글 속 가격: "KO 95.73", "SPY: 733.00", "종가 12,345원" 같은 것 (퍼센트는 제외)
PRICE_TEXT = re.compile(r"\b[A-Z]{1,5}(?:\.[A-Z])?\s*[:=]?\s*\$?\d{1,6}\.\d{2}\b(?!\s*%)"
                        r"|종가\s*(?:는|은|:|：)?\s*\$?(?:\d[\d,]*\.\d+|\d{1,3}(?:,\d{3})+)"
                        r"|\$\s?\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?\b"
                        r"|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*원|\b\d{1,6}(?:\.\d{1,2})?\s*달러")
CONFIG_DROP = {"provider_verified", "providers", "providers_note"}


def _config_copy(cfg: dict) -> dict:
    """검증에 필요한 설정만: 메모(note)와 제공처 확인 기록(실제 종가가 적혀 있음)은 뺀다."""
    def clean(x):
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items() if k not in CONFIG_DROP and k != "note" and not k.endswith("_note")}
        return [clean(v) for v in x] if isinstance(x, list) else x
    return clean(cfg)


def mirror(main: Path, ext: Path, today: date | None = None) -> list[str]:
    today = today or datetime.now(L.KST).date()
    dst = ext / MIRROR_DIR
    if dst.exists():
        shutil.rmtree(dst)
    files = list(MIRROR_FILES) + sorted({str(p.relative_to(main)) for g in MIRROR_GLOBS for p in main.glob(g) if p.is_file()})
    for name in MIRROR_LEDGERS:
        files.append(f"league/ledger/{name}.jsonl")
    wrote, skipped = [], []
    for f in files:
        src = main / f
        if not src.exists():
            continue
        if f == "league/public/results.json":         # 대사 하나에 가격 표현이 있으면 그 대사만 비운다(묶음 전체를 빼지 않음)
            try:
                b = json.loads(src.read_text())
                for pk in b.get("picks", []):
                    if pk.get("line") and PRICE_TEXT.search(pk["line"]):
                        pk["line"] = ""
                        skipped.append(f"{f}: {pk.get('pick_id')} 대사(가격처럼 보이는 표현) 비움")
                text = json.dumps(b, ensure_ascii=False, indent=1) + "\n"
            except Exception:  # noqa: BLE001
                text = src.read_text(errors="replace")
            if NO_PRICE.search(text) or PRICE_TEXT.search(text):
                skipped.append(f"{f}: 가격처럼 보이는 글")
                continue
            (dst / f).parent.mkdir(parents=True, exist_ok=True)
            (dst / f).write_text(text)
            wrote.append(f)
            continue
        if not f.startswith("tools/"):
            text = src.read_text(errors="replace")
            if f.endswith((".json", ".jsonl")) and NO_PRICE.search(text):
                skipped.append(f"{f}: 가격처럼 보이는 칸")
                continue
            hit = PRICE_TEXT.search(text)
            if hit:                                    # 그 파일만 빼고 기록(사본 전체를 멈추면 영수증도 못 보게 됨)
                skipped.append(f"{f}: 가격처럼 보이는 글 ({hit.start()}번째 글자)")   # 가격 글 자체는 옮기지 않는다
                continue
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / f)
        wrote.append(f)
    cfg_copy = json.dumps(_config_copy(L.load_config(main / "league")), ensure_ascii=False, indent=2) + "\n"
    if PRICE_TEXT.search(cfg_copy) or NO_PRICE.search(cfg_copy):
        raise SystemExit("사본 중단: 설정 사본에 가격처럼 보이는 값이 있음")
    (dst / "league").mkdir(parents=True, exist_ok=True)
    (dst / "league" / "config.json").write_text(cfg_copy)
    wrote.append("league/config.json")
    # 슈슈 팀 영수증과 연결 기록, 업데이트 계획(이번 주·지난주)
    subs = [r for dd in (main / "league", main / "league" / "sandbox") for r in L.read_ledger(dd, "submissions")
            if r.get("team") in ("shushu", "sandbox-shushu")]
    (dst / "receipts-shushu.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in subs))
    import dashboard_data as DD                            # 대사 검사용 접수 종목 목록(원장 전체 대신)
    (dst / "shushu-picks.json").write_text(json.dumps(DD.picks_index(main / "league"), ensure_ascii=False, indent=1) + "\n")
    sync = L.read_ledger(main / "league", "external_pushes")
    (dst / "sync-log.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sync))
    plans = {}
    for wk in sorted({L.iso_week(today), L.iso_week(today - timedelta(days=7))}):
        try:
            plans[wk] = L.update_plan(main / "league", wk)
        except Exception as e:  # noqa: BLE001
            plans[wk] = {"error": str(e)}
    (dst / "update-plan.json").write_text(json.dumps(plans, ensure_ascii=False, indent=1) + "\n")
    (dst / "skipped.txt").write_text("".join(x + "\n" for x in skipped) or "없음\n")
    if skipped:
        print("::warning::사본에서 뺀 파일: " + " / ".join(skipped))
    (dst / "README.md").write_text(
        "# from-league (자동 사본, 고치지 마세요)\n\n"
        "메인 리그 저장소에서 원 가격이 없는 자료만 자동으로 복사한 폴더입니다. 여기를 고쳐도 메인에 반영되지 않고 다음 동기화 때 덮어씁니다.\n\n"
        "- `receipts-shushu.jsonl`: 슈슈 팀 제출 영수증(실전 shushu, 연습 sandbox-shushu)\n"
        "- `sync-log.jsonl`: 이 저장소 push를 메인이 처리한 기록(push 시각, 가져온 파일, 영수증)\n"
        "- `league/public/results.json`: 공유 결과 묶음(마감 전 종목·원 가격 없음)\n"
        "- `update-plan.json`: 규칙 v2.1 업데이트 계획(이번 주·지난주)\n"
        "- `shushu-picks.json`: 슈슈 팀 접수 종목 pick_id 목록(대사 검사용). 검사: `cd from-league && python3 tools/dashboard_data.py --check-lines ../lines/<날짜>-shushu.json --picks-index shushu-picks.json` (연습은 `--base league/sandbox` 추가)\n"
        "- `league/rounds/<날짜>/snapshot.json(.sha256)`: 그날 06:50 공통 자료(가격 제외판). 생성 직후 동기화가 바로 보냄\n"
        "- `docs/codex-notices/`: 로로 팀 공지·회신\n"
        "- `tools/`, `league/config.json`, `league/universe/`, `league/agents/roster.json`: CSV 사전 검증용\n"
        "  예: `cd from-league && python3 tools/league.py import-csv ../submit/<날짜>.csv --team shushu --dry-run`\n")
    return wrote


# ───────── 슈슈 깨우기: 전용 저장소 운영 채널 이슈에 @codex 댓글 (Codex 클라우드가 작업을 시작) ─────────
CHANNEL_TITLE = "리그 운영 채널 (자동)"
NOTICE_CAP = 2            # 새 공지·회신 알림은 하루 2번까지(자동 주고받기가 끝없이 돌지 않게)
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
    if mk and live and "07:00" <= hm < "08:15" and cfg.get("shushu_repo", {}).get("wake_round", True):
        add("round", rd, f"@codex 오늘({rd}) 실전 라운드를 진행해 주세요. 열린 시장: {'·'.join(mk)}. {PROC} 절차대로 분석하고, "
            f"**08:20까지 `submit/{rd}.sha256`과 `submit/{rd}.csv`·`submit/{rd}-debate.md`를 함께** push해 주세요. 원본은 이 비공개 저장소에 봉인돼 "
            f"08:30 뒤 자동으로 공개·접수됩니다. 마감 08:30 KST, 판정은 이 저장소의 push 시각입니다.")
    if mk and live and "08:30" < hm < "11:40" and "committed" in st and "accepted" not in st:
        add("reveal", rd, f"@codex 지문 영수증 `committed`를 확인했습니다. 이제 지문과 바이트가 똑같은 `submit/{rd}.csv`와 `submit/{rd}-debate.md`를 push하고, "
            f"`from-league/receipts-shushu.jsonl`에서 `accepted`를 확인한 뒤 `lines/{rd}-shushu.json`(한 줄 대사)을 push해 주세요. 원본 공개 마감 12:00 KST.")
    taint = (("shushu", rd) in tainted(L.read_ledger(d, "external_pushes")))
    if mk and live and "08:30" < hm < "11:40" and taint:
        add("taint", rd, f"@codex 오늘({rd}) 라운드는 **운영자 확인 대기**입니다(마감 전 push 중 받을 수 없는 커밋이 있음). 지문을 냈다면 그 지문과 바이트가 같은 "
            f"`submit/{rd}.csv`·`submit/{rd}-debate.md`를 **12:00 전에 그대로** push해 두세요. 확인이 끝나면 원래 push 시각으로 처리됩니다. 마감 전 push한 브랜치는 지우지 마세요.")
    if mk and live and "08:30" < hm < "11:40" and not taint and not ({"committed", "accepted"} & st):
        add("missing", rd, f"@codex 오늘({rd}) 지문 영수증이 없습니다. 08:30 전에 `submit/{rd}.sha256`을 push했다면 "
            "`from-league/sync-log.jsonl`에서 처리 결과를 확인해 주세요. 마감 뒤 지문은 인정되지 않습니다(소급 없음). 확인 결과를 `to-roro/`로 알려 주세요.")
    if today.weekday() == 5 and hm >= "10:40" and live:
        wk = L.iso_week(today)
        add("review", wk, f"@codex 이번 주({wk}) 토요일 잠정 복기를 진행해 주세요. `from-league/league/imports/shushu/weekly-review-v2.1.md` 절차와 "
            "`from-league/update-plan.json`(잠정)을 쓰고, 개선안이 있으면 `to-roro/`로 요약(근거 pick_id 포함)을 보내 주세요. 최종 자격은 월요일 06:30 마감 뒤 확정됩니다.")
    if today.weekday() == 0 and hm >= "06:35" and (today - timedelta(days=1)).isoformat() >= (cfg.get("season_start") or "9999"):   # 시즌 첫 주 마감부터
        wk = L.iso_week(today - timedelta(days=7))
        add("close", wk, f"@codex 주간 마감({wk})이 끝났습니다. `from-league/league/ledger/weekly_decisions.jsonl`과 `from-league/update-plan.json`으로 "
            "리그별 결과와 최종 업데이트 자격을 확인하고, 바뀐 점이나 승인 요청이 있으면 07:00까지 `to-roro/`로 보내 주세요.")
    # 새 공지·회신 (메인 docs/codex-notices) — 내용 해시로 판단
    new = [p for p in _notes(main) if ("notice", p.name + ":" + L._sha(p)[:12]) not in sent]
    today_notices = sum(1 for w in L.read_ledger(d, "shushu_wakes") if w["kind"] == "notice" and w.get("url") != "seeded"
                        and str(w.get("at", "")).startswith(rd))
    if new and not (mk and live and "06:50" <= hm < "12:00") and today_notices < NOTICE_CAP:   # 라운드 시간 제외, 하루 상한
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


def _marker(w: dict) -> str:
    return f"<!-- league-wake:{w['kind']}:{L.hashlib.sha256(w['key'].encode()).hexdigest()[:16]} -->"


def wake(main: Path, repo: str, token: str, now: datetime | None = None, post=None, existing=None) -> list[dict]:
    """깨우기 댓글. 댓글에 표식을 넣고, 달기 전에 채널의 기존 댓글에서 같은 표식을 찾아 GitHub 쪽 상태로도 한 번만 보장한다."""
    now = now or datetime.now(L.KST)
    d = main / "league"
    todo = due_wakes(main, now)
    if not any(w["kind"] == "notice" for w in L.read_ledger(d, "shushu_wakes")):
        # 처음 켤 때 이미 있는 공지는 보낸 것으로 표시만 한다(이전 공지는 운영자가 이미 전달함)
        for k in notice_keys(main):
            L.append(d, "shushu_wakes", {"kind": "notice", "key": k, "at": now.isoformat(timespec="seconds"), "url": "seeded"})
        todo = [w for w in todo if w["kind"] != "notice"]
    if not todo:
        return []
    if post is None:
        api = f"https://api.github.com/repos/{repo}"
        ch = next((w for w in reversed(L.read_ledger(d, "shushu_wakes")) if w["kind"] == "channel"), None)
        num = int(ch["key"]) if ch else None
        if num is None:                                # 같은 제목의 열린 이슈를 토큰 주인이 만든 게 있으면 그것(원장 push 실패 뒤 재실행 대비)
            me = (_api("GET", "https://api.github.com/user", token) or {}).get("login")
            mine = [i for i in (_api("GET", f"{api}/issues?state=open&per_page=100", token) or [])
                    if i.get("title") == CHANNEL_TITLE and "pull_request" not in i and (i.get("user") or {}).get("login") == me]
            num = min(i["number"] for i in mine) if mine else None
        if num is None:                                # 처음 한 번 채널 이슈를 만들고 번호를 원장에 고정(제목이 바뀌거나 같은 제목이 생겨도 그대로)
            num = _api("POST", f"{api}/issues", token, {"title": CHANNEL_TITLE, "body":
                       "로로 팀(메인 리그 저장소)이 자동으로 남기는 운영 채널입니다. 댓글의 @codex 요청으로 슈슈 팀 작업이 시작됩니다. 닫지 말아 주세요." + SIGN})["number"]
        if not ch:
            L.append(d, "shushu_wakes", {"kind": "channel", "key": str(num), "at": now.isoformat(timespec="seconds"), "url": f"issue {num}"})
        existing = []
        page = 1
        while True:
            cs = _api("GET", f"{api}/issues/{num}/comments?per_page=100&page={page}", token) or []
            existing += [c.get("body") or "" for c in cs]
            if len(cs) < 100:
                break
            page += 1
        post = lambda b: _api("POST", f"{api}/issues/{num}/comments", token, {"body": b})["html_url"]
    existing = existing or []
    sent = []
    for w in todo:
        mk = _marker(w)
        url = "already-posted" if any(mk in b for b in existing) else post(w["body"] + SIGN + "\n" + mk)
        for k in w.get("keys", [w["key"]]):
            L.append(d, "shushu_wakes", {"kind": w["kind"], "key": k, "at": now.isoformat(timespec="seconds"), "url": url})
        sent.append({**w, "url": url})
    return sent


def main_():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pull", "mirror", "wake", "untaint"])
    ap.add_argument("--round"); ap.add_argument("--team"); ap.add_argument("--reason")
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
        res = pull(ROOT, ext, fetch_activity(repo, tok), repo, run_id=a.run_id, run_url=a.run_url, base_branch=branch)
        for r in res:
            rs = "; ".join(f"{x['path']} {x['status']} {' '.join(x['errors'])}".strip() for x in r.get("receipts", [])) or r.get("note") or "제출 파일 없음"
            head = f"push {str(r.get('s_after') or '')[:7]} {r.get('pushed_at', '')} [{r['status']}]"
            print(f"{head} → {rs if r['status'] != 'error' else r.get('error')}")
            if r.get("held_files"):
                print(f"  마감 전 공개 파일 보류(때가 되면 이 push 시각으로 처리): {', '.join(r['held_files'])}")
            for x in r.get("problems", []):
                print(f"  무시: {x}")
            for x in r.get("lines", []):
                print(f"  대사 {x['path']}: {'통과' if x['ok'] else '검사 실패'}")
        if not res:
            print("새 push 없음")
        if any(not x["ok"] for r in res for x in r.get("lines", [])):
            sys.exit(3)
    elif a.cmd == "untaint":                            # 운영자 확인 뒤에만 (원장에 남음, 기본은 실전·연습 둘 다)
        if not (a.round and a.reason):
            sys.exit("--round --reason 필요 (reason에 운영자가 확인한 내용을 적는다)")
        for t_ in ([a.team] if a.team else TEAMS):
            L.append(ROOT / "league", "external_pushes", {"repo": repo, "type": "untaint", "team": t_, "round": a.round,
                                                          "reason": a.reason, "approved_by": "operator",
                                                          "at": datetime.now(L.KST).isoformat(timespec="seconds")})
            print(f"{t_} {a.round} 확인 대기 해제 — 다음 동기화부터 그 라운드 push를 원래 push 시각으로 처리")
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
