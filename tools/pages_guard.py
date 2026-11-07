"""Cloudflare Pages 배포 잠금 확인과 안전한 되돌리기 (league-deploy 워크플로가 쓴다).

  python3 tools/pages_guard.py verify   --project isdceo-league --deploy-log deploy.log
  → 본 주소와 이번 배포의 고유 주소(<hash>.<project>.pages.dev)가 모두 비밀번호(401)를 요구하는지 확인.
    아니면: 고유 주소가 실제로 401인 직전 배포를 골라 되돌리고, 되돌린 뒤 본 주소가 401인지 다시 확인하고,
    실패한 이번 배포를 지운 뒤 종료 코드 1.

환경변수: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID. 토큰·비밀값은 출력하지 않는다.
"""
from __future__ import annotations

import argparse, json, os, re, sys, time, urllib.error, urllib.request

API = "https://api.cloudflare.com/client/v4/accounts/{acct}/pages/projects/{proj}"
PATHS = ("/", "/data/table.js", "/av/")


def status(url: str, auth: str | None = None) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "league-deploy-guard/0.1"})
    if auth:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return 0


def locked(base: str) -> bool:
    """로그인 없이도, 틀린 비밀번호로도 모든 경로가 401이어야 잠긴 것."""
    return all(status(base + p) == 401 and status(base + p, "operator:wrong") == 401 for p in PATHS)


def api(method: str, path: str, tok: str, acct: str, proj: str):
    req = urllib.request.Request(API.format(acct=acct, proj=proj) + path, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "User-Agent": "league-deploy-guard/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:  # noqa: BLE001
            return e.code, {}


def this_deploy_url(log_text: str, proj: str) -> str | None:
    # 배포별 고유 주소는 16진수 해시(예: 1a2b3c4d)다. "main" 같은 브랜치 별칭 주소는 제외한다
    m = re.findall(rf"https://([0-9a-f]{{8,}})\.{re.escape(proj)}\.pages\.dev", log_text)
    return f"https://{m[-1]}.{proj}.pages.dev" if m else None


def verify(proj: str, log_path: str | None) -> int:
    main = f"https://{proj}.pages.dev"
    mine = this_deploy_url(open(log_path, encoding="utf-8", errors="replace").read(), proj) if log_path and os.path.exists(log_path) else None
    time.sleep(int(os.environ.get("GUARD_WAIT", "20")))
    targets = [main] + ([mine] if mine else [])
    bad = [t for t in targets if not locked(t)]
    for t in targets:
        print(f"{t} → {'잠김(401)' if t not in bad else '잠기지 않음'}")
    if not mine:
        print("::warning::이번 배포의 고유 주소를 배포 기록에서 찾지 못함 — 본 주소만 확인")
    if not bad:
        return 0
    tok, acct = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    print("::error::잠기지 않은 주소가 있음 — 잠금이 확인되는 직전 배포로 되돌린다")
    if not (tok and acct):
        print("::error::Cloudflare 자격 정보가 없어 되돌리지 못함 — deploy_enabled 를 끄고 Cloudflare 에서 배포를 지울 것")
        return 1
    code, res = api("GET", "/deployments?env=production&per_page=10", tok, acct, proj)
    deps = (res or {}).get("result") or []
    cur = next((x for x in deps if mine and x.get("url", "").rstrip("/") == mine), None)
    target = None
    for x in deps:
        if cur and x["id"] == cur["id"]:
            continue
        u = (x.get("url") or "").rstrip("/")
        if u and u != mine and locked(u):
            target = x
            break
    if target:
        c, _ = api("POST", f"/deployments/{target['id']}/rollback", tok, acct, proj)
        time.sleep(10)
        ok = locked(main)
        print(f"되돌리기: 배포 {target['id']} (HTTP {c}) → 본 주소 {'잠김(401)' if ok else '여전히 잠기지 않음'}")
        if not ok:
            print("::error::되돌린 뒤에도 본 주소가 잠기지 않음 — deploy_enabled 를 끄고 Cloudflare 에서 배포를 지울 것")
    else:
        print("::error::잠금이 확인되는 직전 배포가 없음 — deploy_enabled 를 끄고 Cloudflare 에서 배포를 지울 것")
    if cur:                                            # 실패한 이번 배포(고유 주소 포함)를 지운다
        c, _ = api("DELETE", f"/deployments/{cur['id']}?force=true", tok, acct, proj)
        print(f"실패한 배포 {cur['id']} 삭제: HTTP {c}")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["verify"])
    ap.add_argument("--project", required=True)
    ap.add_argument("--deploy-log")
    a = ap.parse_args()
    sys.exit(verify(a.project, a.deploy_log))


if __name__ == "__main__":
    main()
