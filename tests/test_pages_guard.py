"""배포 잠금 확인·되돌리기 시험(네트워크 없음)."""
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pages_guard as G  # noqa: E402


class Guard(unittest.TestCase):
    def setUp(self):
        self._st, self._api = G.status, G.api
        os.environ.update(GUARD_WAIT="0", CLOUDFLARE_API_TOKEN="t", CLOUDFLARE_ACCOUNT_ID="a")
        self._sleep = G.time.sleep
        G.time.sleep = lambda s: None

    def tearDown(self):
        G.status, G.api = self._st, self._api
        G.time.sleep = self._sleep

    def _log(self, text):
        f = Path(tempfile.mkdtemp()) / "deploy.log"; f.write_text(text); return str(f)

    def test_parse_url(self):
        log = "Take a peek over at https://ab12cd34.p.pages.dev\nDeployment alias URL: https://main.p.pages.dev\n"
        self.assertEqual(G.this_deploy_url(log, "p"), "https://ab12cd34.p.pages.dev")     # 별칭(main) 제외

    def test_ok_when_both_locked(self):
        G.status = lambda url, auth=None: 401
        self.assertEqual(G.verify("p", self._log("https://0e1a2b3c.p.pages.dev")), 0)

    def test_rollback_skips_unlocked_previous_and_deletes_failed(self):
        open_hosts = {"https://0e1a2b3c.p.pages.dev", "https://old1.p.pages.dev"}      # 이번 배포와 직전 배포(이전 실패)는 열림
        state = {"rolled": None}
        def st(url, auth=None):
            host = url.split("/", 3)[:3]; base = "/".join(host)
            if base == "https://p.pages.dev":
                return 401 if state["rolled"] == "d3" else 200
            return 200 if base in open_hosts else 401
        calls = []
        def api(method, path, tok, acct, proj):
            calls.append((method, path))
            if method == "GET":
                return 200, {"result": [{"id": "d1", "url": "https://0e1a2b3c.p.pages.dev"}, {"id": "d2", "url": "https://old1.p.pages.dev"},
                                        {"id": "d3", "url": "https://good.p.pages.dev"}]}
            if method == "POST":
                state["rolled"] = path.split("/")[2]
            return 200, {}
        G.status, G.api = st, api
        self.assertEqual(G.verify("p", self._log("https://0e1a2b3c.p.pages.dev")), 1)
        self.assertIn(("POST", "/deployments/d3/rollback"), calls)                 # 잠금 확인된 d3로(열린 d2는 건너뜀)
        self.assertIn(("DELETE", "/deployments/d1?force=true"), calls)             # 실패한 이번 배포 삭제


if __name__ == "__main__":
    unittest.main()
