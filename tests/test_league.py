"""AI 투자 리그 규칙 테스트.  실행: python3 -m unittest discover -s tests -v"""
import json, shutil, sys, tempfile, unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import league as L  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def new_league():
    d = Path(tempfile.mkdtemp())
    (d / "ledger").mkdir()
    (d / "agents").mkdir()
    for f in ("config.json", "universe.json"):
        shutil.copy(ROOT / "league" / f, d / f)
    shutil.copy(ROOT / "league" / "agents" / "roster.json", d / "agents" / "roster.json")
    return d


def price(d, m, t, s, close, **kw):
    L.append(d, "prices", {"market": m, "ticker": t, "session": s, "close": close, "basis": "unadjusted",
                           "halted": False, "status": "final", **kw})


def checked(d, m, t, frm="2026-11-01", to="2026-11-30"):
    L.append(d, "corporate_actions", {"type": "checked", "market": m, "ticker": t, "from": frm, "to": to, "source": "test"})


def ca(d, **kw):
    L.append(d, "corporate_actions", {"source": "test", **kw})


def pick(d, agent, rd, m, t, locked="08:00", team="claude"):
    cfg = L.load_config(d)
    rec = L.make_pick(team, agent, 1, rd, m, t, t, f"{rd}T{locked}:00+09:00", "근거", ["위험"],
                      [{"url": "https://example.com", "as_of": rd}], cfg)
    return L.submit_pick(d, rec)


class Score(unittest.TestCase):
    def test_formula_examples(self):
        self.assertEqual(L.compute_score(100, 102.3), 2.3)
        self.assertEqual(L.compute_score(100, 98.9), -1.1)

    def test_split_adjustment(self):
        # 1→4 분할: 기준 400, 평가 101 → 실질 404 → +1%
        self.assertEqual(L.compute_score(400, 101, split_factor=4), 1.0)

    def test_total_and_price_only(self):
        # 배당락 1원: 총수익 0점, 주가만 −1점
        self.assertEqual(L.compute_scores(100, 99, dividend=1), (0.0, -1.0))


class Calendar(unittest.TestCase):
    cfg = {"calendar_overrides": {}}

    def test_round_sessions_normal(self):
        # 2026-11-10(화) 라운드: 기준 11/9, 평가 11/10 (두 시장 모두)
        for m in ("KR", "US"):
            self.assertEqual(L.round_sessions(m, date(2026, 11, 10), self.cfg), (date(2026, 11, 9), date(2026, 11, 10)))

    def test_monday_uses_friday_base(self):
        self.assertEqual(L.round_sessions("KR", date(2026, 11, 16), self.cfg)[0], date(2026, 11, 13))

    def test_us_holiday_blocks_us_picks_only(self):
        d = date(2026, 11, 26)  # 추수감사절: 미국 휴장, 한국 개장
        self.assertIsNone(L.round_sessions("US", d, self.cfg))
        self.assertIsNotNone(L.round_sessions("KR", d, self.cfg))
        # 다음 날 미국 라운드의 기준일은 휴장일을 건너뛴 11/25
        self.assertEqual(L.round_sessions("US", date(2026, 11, 27), self.cfg)[0], date(2026, 11, 25))

    def test_kr_year_end_closure(self):
        self.assertIsNone(L.round_sessions("KR", date(2026, 12, 31), self.cfg))

    def test_manual_override(self):
        cfg = {"calendar_overrides": {"KR": {"closed": ["2026-11-10"]}}}
        self.assertIsNone(L.round_sessions("KR", date(2026, 11, 10), cfg))
        self.assertEqual(L.round_sessions("KR", date(2026, 11, 11), cfg)[0], date(2026, 11, 9))


class Ledger(unittest.TestCase):
    def test_tamper_detected(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        pick(d, "lynch", "2026-11-10", "US", "AAPL")
        self.assertEqual(L.verify(d), [])
        p = d / "ledger" / "picks.jsonl"
        lines = p.read_text().splitlines()
        lines[0] = lines[0].replace("005930", "000660")       # 과거 추천 종목 바꿔치기
        p.write_text("\n".join(lines) + "\n")
        self.assertTrue(any("picks.jsonl:1" in e for e in L.verify(d)))

    def test_deleted_line_detected(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        pick(d, "lynch", "2026-11-10", "US", "AAPL")
        p = d / "ledger" / "picks.jsonl"
        p.write_text(p.read_text().splitlines()[1] + "\n")
        self.assertTrue(L.verify(d))


class Validation(unittest.TestCase):
    def test_after_deadline_rejected(self):
        d = new_league()
        with self.assertRaisesRegex(ValueError, "마감"):
            pick(d, "buffett", "2026-11-10", "KR", "005930", locked="08:31")

    def test_outside_universe_rejected(self):
        d = new_league()
        with self.assertRaisesRegex(ValueError, "대상 범위"):
            pick(d, "buffett", "2026-11-10", "US", "GME")

    def test_holiday_market_rejected(self):
        d = new_league()
        with self.assertRaisesRegex(ValueError, "휴장"):
            pick(d, "buffett", "2026-11-26", "US", "AAPL")

    def test_one_pick_per_agent_per_market(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        pick(d, "buffett", "2026-11-10", "US", "AAPL")           # 시장이 다르면 허용
        with self.assertRaisesRegex(ValueError, "이미"):
            pick(d, "buffett", "2026-11-10", "KR", "000660")
        self.assertEqual({p["pick_id"] for p in L.read_ledger(d, "picks")},
                         {"2026-11-10-claude-buffett-KR", "2026-11-10-claude-buffett-US"})

    def test_same_stock_allowed_for_different_agents(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        pick(d, "lynch", "2026-11-10", "KR", "005930")
        self.assertEqual(len(L.read_ledger(d, "picks")), 2)


class Scoring(unittest.TestCase):
    def test_pending_then_final(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 102300)
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 10)), [])          # 아직 평가일 장중
        w = L.run_scoring(d, today=date(2026, 11, 11))
        self.assertEqual((w[0]["status"], w[0]["score"]), ("final", 2.3))
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 12)), [])          # 변화 없으면 기록 안 함

    def test_missing_price_is_held_not_zero(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        w = L.run_scoring(d, today=date(2026, 11, 11))
        self.assertEqual(w[0]["status"], "held")
        self.assertIsNone(w[0]["score"])

    def test_provisional_until_price_final(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 101000, status="provisional")
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 11))[0]["status"], "provisional")
        price(d, "KR", "005930", "2026-11-10", 101000)          # 다음 날 공식 확정
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 12))[0]["status"], "final")

    def test_correction_after_final_is_appended(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 101000)
        L.run_scoring(d, today=date(2026, 11, 11))
        price(d, "KR", "005930", "2026-11-10", 100500)          # 제공처 정정
        w = L.run_scoring(d, today=date(2026, 11, 12))
        self.assertEqual(w[0]["score"], 0.5)
        self.assertIn("correction_of", w[0])
        self.assertEqual(L.read_ledger(d, "corrections")[0]["before"], 1.0)
        self.assertEqual(len(L.read_ledger(d, "scores")), 2)    # 원래 기록 보존
        self.assertEqual(L.verify(d), [])

    def test_halt_delayed_scoring(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", None, halted=True)
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 11))[0]["status"], "held")
        price(d, "KR", "005930", "2026-11-11", 97000)
        w = L.run_scoring(d, today=date(2026, 11, 12))[0]
        self.assertEqual((w["status"], w["score"], w["delayed"]), ("final", -3.0, True))

    def test_long_halt_void(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        cfg = L.load_config(d)
        s = date(2026, 11, 10)
        for _ in range(7):
            price(d, "KR", "005930", s.isoformat(), None, halted=True)
            s = L.next_session("KR", s, cfg)
        w = L.run_scoring(d, today=date(2026, 11, 25))[0]
        self.assertEqual(w["status"], "void")


class Dividends(unittest.TestCase):
    def setUp(self):
        self.d = new_league()
        pick(self.d, "buffett", "2026-11-10", "KR", "005930")       # 기준 11/9, 평가 11/10
        price(self.d, "KR", "005930", "2026-11-09", 100000)
        price(self.d, "KR", "005930", "2026-11-10", 99000)

    def score(self):
        return L.run_scoring(self.d, today=date(2026, 11, 11))[0]

    def test_unverified_corporate_actions_held(self):
        w = self.score()
        self.assertEqual((w["status"], w["score"]), ("held", None))
        self.assertIn("배당", w["reason"])

    def test_exdate_on_eval_session_included(self):
        checked(self.d, "KR", "005930")
        ca(self.d, type="dividend", market="KR", ticker="005930", ex_date="2026-11-10", amount=1000, pay_date="2027-04-20")
        w = self.score()
        self.assertEqual((w["score"], w["score_price_only"]), (0.0, -1.0))

    def test_exdate_on_base_session_not_included(self):
        # 기준일 종가에 산 사람은 그날이 배당락일이면 배당을 못 받는다
        checked(self.d, "KR", "005930")
        ca(self.d, type="dividend", market="KR", ticker="005930", ex_date="2026-11-09", amount=1000, pay_date="2026-11-10")
        self.assertEqual(self.score()["score"], -1.0)

    def test_pay_date_alone_does_not_count(self):
        checked(self.d, "KR", "005930")
        ca(self.d, type="dividend", market="KR", ticker="005930", ex_date="2026-09-29", amount=1000, pay_date="2026-11-10")
        self.assertEqual(self.score()["score"], -1.0)

    def test_dividend_and_split_same_window_held(self):
        checked(self.d, "KR", "005930")
        ca(self.d, type="dividend", market="KR", ticker="005930", ex_date="2026-11-10", amount=1000)
        ca(self.d, type="split", market="KR", ticker="005930", ex_date="2026-11-10", ratio=2)
        self.assertEqual(self.score()["status"], "held")

    def test_adjusted_prices_not_double_counted(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 99000, basis="adjusted_total")   # 배당 반영된 수정 기준가
        price(d, "KR", "005930", "2026-11-10", 99000, basis="adjusted_total")
        ca(d, type="dividend", market="KR", ticker="005930", ex_date="2026-11-10", amount=1000)
        w = L.run_scoring(d, today=date(2026, 11, 11))[0]
        self.assertEqual((w["score"], w["score_price_only"]), (0.0, None))

    def test_mixed_price_basis_held(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 99000, basis="adjusted_total")
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 11))[0]["status"], "held")


class Timing(unittest.TestCase):
    def test_base_close_before_deadline_before_eval_open_for_a_year(self):
        """2026-11 ~ 2027-10 모든 라운드에서: 기준 종가 확정 < 08:30 마감 < 평가 세션 개장 (KR·US 각각)"""
        cfg = L.load_config(ROOT / "league")
        bad, n = [], 0
        for r in L.schedule(date(2026, 11, 2), date(2027, 10, 29), cfg):   # 달력 라이브러리 제공 범위(약 1년) 안
            for m in ("KR", "US"):
                if r[m]:
                    n += 1
                    if not r[m]["ok"]:
                        bad.append(r[m])
        self.assertGreater(n, 400)
        self.assertEqual(bad, [])

    def test_us_base_is_previous_us_session_not_same_day(self):
        cfg = L.load_config(ROOT / "league")
        t = L.timing("US", date(2026, 11, 10), cfg)
        self.assertEqual(t["base_session"], "2026-11-09")
        self.assertEqual(t["base_close_kst"], "2026-11-10T06:00+09:00")   # 미국 11/9 16:00 EST
        self.assertEqual(t["eval_open_kst"], "2026-11-10T23:30+09:00")


class Receipts(unittest.TestCase):
    """임시 git 저장소에서 push 이벤트를 흉내 내 영수증 처리 검증."""
    def setUp(self):
        import subprocess
        self.repo = Path(tempfile.mkdtemp())
        lg = self.repo / "league"
        (lg / "ledger").mkdir(parents=True)
        (lg / "agents").mkdir()
        for f in ("config.json", "universe.json"):
            shutil.copy(ROOT / "league" / f, lg / f)
        shutil.copy(ROOT / "league" / "agents" / "roster.json", lg / "agents" / "roster.json")
        self.run = lambda *a: subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True, text=True).stdout.strip()
        self.run("init", "-q"); self.run("config", "user.email", "t@t"); self.run("config", "user.name", "t")
        self.run("add", "."); self.run("commit", "-qm", "init")

    def push(self, rd, rows, pushed_at, locked="07:50"):
        before = self.run("rev-parse", "HEAD")
        p = self.repo / "league" / "imports" / "shushu" / f"{rd}.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        body = "round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources\n"
        for a, m, t in rows:
            body += f"{rd},{a},1,{m},{t},{t},{rd}T{locked}:00+09:00,근거,위험,https://x|{rd}\n"
        p.write_text(body)
        self.run("add", "."); self.run("commit", "-qm", "submit")
        after = self.run("rev-parse", "HEAD")
        ts = int(datetime.fromisoformat(pushed_at).timestamp())
        ev = {"before": before, "after": after, "ref": "refs/heads/main", "pusher": {"name": "shushu"},
              "repository": {"pushed_at": ts}, "commits": []}
        return L.process_push(ev, run_id="1", run_created_at=None, cwd=self.repo)

    def test_on_time_accepted_with_hash_and_commit(self):
        r = self.push("2026-11-10", [("s1", "KR", "005930"), ("s1", "US", "AAPL")], "2026-11-10T08:29:59+09:00")[0]
        self.assertEqual((r["status"], r["imported"]), ("accepted", 2))
        self.assertEqual(len(r["csv_sha256"]), 64)
        picks = L.read_ledger(self.repo / "league", "picks")
        self.assertEqual(picks[0]["submission"]["commit"], r["commit"])

    def test_receipt_hash_matches_raw_bytes_with_crlf(self):
        import hashlib
        before = self.run("rev-parse", "HEAD")
        p = self.repo / "league" / "imports" / "shushu" / "2026-11-10.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        body = ("round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources\r\n"
                + "".join(f"2026-11-10,s1,1,{m},{t},{t},2026-11-10T07:50:00+09:00,근거,위험,https://x|2026-11-09\r\n"
                          for m, t in (("KR", "005930"), ("US", "AAPL"))))
        p.write_bytes(body.encode())
        self.run("add", "."); self.run("commit", "-qm", "crlf")
        ev = {"before": before, "after": self.run("rev-parse", "HEAD"), "ref": "refs/heads/main", "pusher": {"name": "x"},
              "repository": {"pushed_at": int(datetime.fromisoformat("2026-11-10T08:00:00+09:00").timestamp())}, "commits": []}
        r = L.process_push(ev, run_id="1", cwd=self.repo)[0]
        self.assertEqual(r["status"], "accepted")
        self.assertEqual(r["csv_sha256"], hashlib.sha256(body.encode()).hexdigest())

    def test_late_push_not_accepted_even_if_csv_claims_early(self):
        r = self.push("2026-11-10", [("s1", "KR", "005930"), ("s1", "US", "AAPL")], "2026-11-10T08:30:01+09:00", locked="08:00")[0]
        self.assertEqual(r["status"], "late")
        self.assertEqual(L.read_ledger(self.repo / "league", "picks"), [])

    def test_resubmission_after_acceptance_rejected(self):
        self.push("2026-11-10", [("s1", "KR", "005930"), ("s1", "US", "AAPL")], "2026-11-10T08:00:00+09:00")
        r = self.push("2026-11-10", [("s1", "KR", "000660"), ("s1", "US", "MSFT")], "2026-11-10T08:10:00+09:00")[0]
        self.assertEqual(r["status"], "rejected")
        self.assertEqual(len(L.read_ledger(self.repo / "league", "picks")), 2)

    def test_locked_at_after_push_rejected(self):
        r = self.push("2026-11-10", [("s1", "KR", "005930"), ("s1", "US", "AAPL")], "2026-11-10T08:00:00+09:00", locked="08:20")[0]
        self.assertEqual(r["status"], "rejected")

    def test_append_only_guard(self):
        self.push("2026-11-10", [("s1", "KR", "005930"), ("s1", "US", "AAPL")], "2026-11-10T08:00:00+09:00")
        self.run("add", "."); self.run("commit", "-qm", "ledger")
        base = self.run("rev-parse", "HEAD")
        p = self.repo / "league" / "ledger" / "picks.jsonl"
        p.write_text(p.read_text().replace("005930", "000660"))
        self.run("commit", "-qam", "tamper")
        self.assertTrue(L.append_only_violations(base, "HEAD", cwd=self.repo))


class Weekly(unittest.TestCase):
    def _week(self, d, results, team="claude"):
        """results: {agent: [점수...]} → W46 월~금 라운드, 하루 KR·US 순서로 최대 10건 기록"""
        days = ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
        slots = [(rd, m) for rd in days for m in ("KR", "US")]
        cfg = L.load_config(d)
        for agent, scores in results.items():
            for (rd, m), sc in zip(slots, scores):
                t = "005930" if m == "KR" else "AAPL"
                rec = L.make_pick(team, agent, 1, rd, m, t, t, f"{rd}T08:00:00+09:00",
                                  "", [], [{"url": "x", "as_of": rd}], cfg)
                L.append(d, "picks", rec)
                if sc is not None:
                    L.append(d, "scores", {"pick_id": rec["pick_id"], "status": "final", "score": sc})
        return L.weekly(d, "2026-W46", team)

    def test_bottom_eliminated(self):
        d = new_league()
        w = self._week(d, {"buffett": [1] * 6, "lynch": [2] * 6, "dalio": [0] * 6,
                           "wood": [1, 0] * 3, "burry": [-1] * 6})
        self.assertEqual(w["decision"]["eliminate"], "burry")
        self.assertIsNone(w["decision"]["replacement"])              # 승인 전에는 투입 불가

    def test_only_approved_bench_replaces(self):
        d = new_league()
        L.append(d, "approvals", {"type": "bench", "team": "claude", "agent_id": "quant", "decision": "approved"})
        w = self._week(d, {"buffett": [1] * 6, "lynch": [2] * 6, "dalio": [0] * 6,
                           "wood": [1, 0] * 3, "burry": [-1] * 6})
        self.assertEqual(w["decision"]["replacement"], "quant")      # 1순위 momentum 미승인 → 승인된 quant

    def test_hold_when_bottom_has_too_few_scores(self):
        d = new_league()
        w = self._week(d, {"buffett": [1] * 8, "lynch": [2] * 8, "dalio": [0] * 8,
                           "wood": [1, 0] * 4, "burry": [-1] * 5 + [None] * 5})
        self.assertIsNone(w["decision"]["eliminate"])
        self.assertTrue(any("5건 < 6건" in r for r in w["decision"]["hold_reasons"]))

    def test_tiebreak_by_median(self):
        d = new_league()
        # dalio, burry 평균 0 동점 → 중앙값: dalio 0, burry -0.5 → burry 탈락
        w = self._week(d, {"buffett": [1] * 6, "lynch": [2] * 6, "dalio": [0] * 6,
                           "wood": [1] * 6, "burry": [3, -1, -1, -1, 0, 0]})
        self.assertEqual(w["decision"]["eliminate"], "burry")

    def test_full_tie_holds(self):
        d = new_league()
        w = self._week(d, {"buffett": [1] * 6, "lynch": [2] * 6, "dalio": [0] * 6,
                           "wood": [1] * 6, "burry": [0] * 6})
        self.assertIsNone(w["decision"]["eliminate"])
        self.assertTrue(any("동점" in r for r in w["decision"]["hold_reasons"]))


class CsvImport(unittest.TestCase):
    H = "round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources\n"

    def run_csv(self, body):
        d = new_league()
        f = d / "in.csv"
        f.write_text(self.H + body)
        return d, *L.import_csv(d, f, "shushu")

    def test_import_ok_both_markets(self):
        d, ok, bad = self.run_csv(
            "2026-11-10,s1,1,KR,005930,삼성전자,2026-11-10T08:10:00+09:00,근거,위험1|위험2,https://x|2026-11-09\n"
            "2026-11-10,s1,1,US,AAPL,Apple,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09\n")
        self.assertEqual(bad, [])
        ps = L.read_ledger(d, "picks")
        self.assertEqual([(p["market"], p["base_session"], p["eval_session"]) for p in ps],
                         [("KR", "2026-11-09", "2026-11-10"), ("US", "2026-11-09", "2026-11-10")])

    def test_missing_market_rejected(self):
        d, ok, bad = self.run_csv(
            "2026-11-10,s1,1,US,AAPL,Apple,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09\n")
        self.assertTrue(any("KR 종목 누락" in e for b in bad for e in b["errors"]))
        self.assertEqual(L.read_ledger(d, "picks"), [])

    def test_us_holiday_only_kr_required(self):
        d, ok, bad = self.run_csv(       # 11/26 추수감사절: 미국 휴장 → 한국 1종목만
            "2026-11-26,s1,1,KR,005930,삼성전자,2026-11-26T08:10:00+09:00,근거,위험,https://x|2026-11-25\n")
        self.assertEqual(bad, [])

    def test_import_all_or_nothing(self):
        d, ok, bad = self.run_csv(
            "2026-11-10,s1,1,KR,005930,삼성전자,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09\n"
            "2026-11-10,s1,1,US,AAPL,Apple,2026-11-10T08:45:00+09:00,근거,위험,https://x|2026-11-09\n")
        self.assertTrue(any("마감" in e for b in bad for e in b["errors"]))
        self.assertEqual(L.read_ledger(d, "picks"), [])         # 오류가 하나라도 있으면 아무것도 기록 안 함

    def test_more_than_five_agents_rejected(self):
        rows = "".join(f"2026-11-10,s{i},1,{m},{t},{t},2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09\n"
                       for i in range(1, 7) for m, t in (("KR", "005930"), ("US", "AAPL")))
        d, ok, bad = self.run_csv(rows)
        self.assertTrue(any("5명 초과" in e for b in bad for e in b["errors"]))


class Rules12(unittest.TestCase):
    def test_submit_rate_counts_missed_slots(self):
        d = new_league()
        cfg = L.load_config(d)
        for rd in ("2026-11-09", "2026-11-10"):            # W46 중 2일만, 각 2건 제출 → 10건 중 4건
            for m, t in (("KR", "005930"), ("US", "AAPL")):
                L.append(d, "picks", L.make_pick("claude", "buffett", 1, rd, m, t, t, f"{rd}T08:00:00+09:00",
                                                 "", [], [], cfg))
        r = [x for x in L.weekly(d, "2026-W46")["ranking"] if x["agent_id"] == "buffett"][0]
        self.assertEqual((r["expected"], r["picks"], r["missed"], r["submit_rate"]), (10, 4, 6, 40.0))

    def test_source_retrieved_after_deadline_rejected(self):
        d = new_league()
        f = d / "in.csv"
        f.write_text(CsvImport.H +
            "2026-11-10,s1,1,KR,005930,삼성전자,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09|2026-11-10T08:40:00+09:00\n"
            "2026-11-10,s1,1,US,AAPL,Apple,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09|2026-11-10T07:15:00+09:00\n")
        ok, bad = L.import_csv(d, f, "shushu")
        self.assertTrue(any("확보 시각" in e for b in bad for e in b["errors"]))

    def test_external_roster_and_bench(self):
        d = new_league()
        (d / "imports" / "shushu").mkdir(parents=True)
        (d / "imports" / "shushu" / "roster.json").write_text(json.dumps(
            {"members": [{"id": f"s{i}", "label": f"L{i}", "version": 1} for i in range(1, 6)],
             "bench": [{"id": "s6", "label": "대기"}]}))
        r = L.load_roster(d)
        self.assertEqual([a["id"] for a in r["shushu"]], ["s1", "s2", "s3", "s4", "s5"])
        self.assertEqual(r["bench_shushu"][0]["id"], "s6")


class Excess(unittest.TestCase):
    def test_excess_vs_benchmark(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 102000)
        price(d, "KR", "KOSPI", "2026-11-09", 2500.0)
        price(d, "KR", "KOSPI", "2026-11-10", 2525.0)            # 지수 +1%
        w = L.run_scoring(d, today=date(2026, 11, 11))[0]
        self.assertEqual((w["score"], w["benchmark_return"], w["score_excess"]), (2.0, 1.0, 1.0))

    def test_missing_benchmark_does_not_hold(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "US", "AAPL")
        checked(d, "US", "AAPL")
        price(d, "US", "AAPL", "2026-11-09", 200.0)
        price(d, "US", "AAPL", "2026-11-10", 199.0)
        w = L.run_scoring(d, today=date(2026, 11, 11))[0]
        self.assertEqual((w["status"], w["score"], w["score_excess"]), ("final", -0.5, None))


if __name__ == "__main__":
    unittest.main()


class Embargo(unittest.TestCase):
    """마감(08:30 KST) 전 라운드의 추천은 내보내기 파일에 들어가지 않는다."""

    def _setup(self):
        d = new_league()
        cfg = L.load_config(d)
        for team, agent, t in (("claude", "buffett", "AAPL"), ("shushu", "s1", "MSFT")):
            rec = L.make_pick(team, agent, 1, "2026-11-10", "US", t, t, "2026-11-10T08:00:00+09:00",
                              "근거", ["위험"], [{"url": "x", "as_of": "2026-11-10"}], cfg)
            L.append(d, "picks", rec)
        return d

    def _export(self, d, now):
        out = d / "out.js"
        L.export(d, out, public=True, now=datetime.fromisoformat(now))
        return out.read_text(), json.loads(out.read_text().split("window.LEAGUE = ", 1)[1].rstrip().rstrip(";"))

    def test_hidden_before_deadline(self):
        d = self._setup()
        ids = [p["pick_id"] for p in L.read_ledger(d, "picks")]
        txt, data = self._export(d, "2026-11-10T08:29:59+09:00")
        self.assertEqual(data["picks"], [])
        for i in ids:
            self.assertNotIn(i, txt)
        self.assertEqual(data["embargoed"], {"claude|2026-11-10": 1, "shushu|2026-11-10": 1})

    def test_shown_at_deadline(self):
        _, data = self._export(self._setup(), "2026-11-10T08:30:00+09:00")
        self.assertEqual(sorted(p["ticker"] for p in data["picks"]), ["AAPL", "MSFT"])
        self.assertEqual(data["embargoed"], {})

    def test_private_export_also_hidden(self):
        d = self._setup()
        out = d / "out.js"
        L.export(d, out, public=False, now=datetime.fromisoformat("2026-11-10T07:00:00+09:00"))
        txt = out.read_text()
        for p in L.read_ledger(d, "picks"):
            self.assertNotIn(p["pick_id"], txt)
        self.assertIn('"picks": []', txt)


class DashboardData(unittest.TestCase):
    """운영자 현황판 데이터도 마감 전 라운드 종목을 싣지 않는다."""

    def test_calendar_holidays(self):
        """진행 표시용 달력: 한쪽 휴장은 남은 시장만, 둘 다 쉬면 라운드 없음, 채점은 다음 날 10:30."""
        import dashboard_data as D
        rows = {r["date"]: r for r in D.calendar(datetime.fromisoformat("2026-12-10T12:00:00+09:00"), back=20, ahead=30)}
        self.assertEqual(rows["2026-11-26"]["markets"], "한국만 (미국 휴장)")
        self.assertEqual(rows["2026-12-31"]["markets"], "미국만 (한국 휴장)")
        self.assertNotIn("2026-12-25", rows)
        self.assertNotIn("2026-12-12", rows)                      # 토요일
        self.assertEqual(rows["2026-12-11"]["deadline"], "2026-12-11T08:30+09:00")
        self.assertEqual(rows["2026-12-11"]["score_at"], "2026-12-12T10:30+09:00")   # 금요일 라운드 → 토요일 채점

    def test_no_picks_before_deadline(self):
        import dashboard_data as D
        for now in ("2026-11-05T08:29:00+09:00", "2026-11-05T09:00:00+09:00", "2026-11-06T09:00:00+09:00"):
            t = datetime.fromisoformat(now)
            out = D.build(t)
            cfg = L.load_config(L.ROOT / "league")
            for p in out["picks"]:
                self.assertGreaterEqual(t, L.lock_deadline(date.fromisoformat(p["round_date"]), cfg), p["pick_id"])
            self.assertNotIn("ticker", json.dumps(out["teams"] + out["receipts"] + out["checklist"]))

    def test_bundle_has_no_early_picks_or_prices(self):
        import dashboard_data as D
        for now in ("2026-11-05T08:29:00+09:00", "2026-11-06T08:29:00+09:00", "2026-11-07T09:00:00+09:00"):
            t = datetime.fromisoformat(now)
            b = D.bundle(t)
            cfg = L.load_config(L.ROOT / "league")
            for p in b["picks"]:
                self.assertGreaterEqual(t, L.lock_deadline(date.fromisoformat(p["round_date"]), cfg))
            self.assertNotRegex(json.dumps(b), r'"(base_close|eval_close|close|amount)"\s*:')
            self.assertEqual(set(D.BUNDLE_KEYS) - set(b), set())


class CommitReveal(Receipts):
    """마감 전 지문(.sha256)만 push, 원본 CSV는 08:30~12:00에 공개."""
    ROWS = [("s1", "KR", "005930"), ("s1", "US", "AAPL")]

    def _csv(self, rd, rows, locked="07:50"):
        body = "round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources\n"
        for a, m, t in rows:
            body += f"{rd},{a},1,{m},{t},{t},{rd}T{locked}:00+09:00,근거,위험,https://x|{rd}\n"
        return body

    def _push_files(self, files: dict, pushed_at):
        before = self.run("rev-parse", "HEAD")
        for name, text in files.items():
            p = self.repo / "league" / "imports" / "shushu" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        self.run("add", "."); self.run("commit", "-qm", "push")
        ev = {"before": before, "after": self.run("rev-parse", "HEAD"), "ref": "refs/heads/main", "pusher": {"name": "x"},
              "repository": {"pushed_at": int(datetime.fromisoformat(pushed_at).timestamp())}, "commits": []}
        return L.process_push(ev, run_id="1", cwd=self.repo)

    def _commit(self, rd, body, pushed_at, sha=None):
        import hashlib
        sha = sha or hashlib.sha256(body.encode()).hexdigest()
        return self._push_files({f"{rd}.sha256": f"{sha}  {rd}.csv\n"}, pushed_at)[0]

    def test_commit_then_reveal_accepted(self):
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        c = self._commit(rd, body, "2026-11-10T08:20:00+09:00")
        self.assertEqual(c["status"], "committed")
        self.assertEqual(L.read_ledger(self.repo / "league", "picks"), [])
        r = self._push_files({f"{rd}.csv": body}, "2026-11-10T08:40:00+09:00")[0]
        self.assertEqual((r["status"], r["imported"]), ("accepted", 2))
        self.assertEqual(r["commitment_commit"], c["commit"])
        pk = L.read_ledger(self.repo / "league", "picks")[0]
        self.assertEqual(pk["submission"]["committed_at"], "2026-11-10T08:20:00+09:00")

    def test_reveal_hash_mismatch_rejected_then_retry(self):
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        self._commit(rd, body, "2026-11-10T08:20:00+09:00")
        bad = self._push_files({f"{rd}.csv": self._csv(rd, [("s1", "KR", "000660"), ("s1", "US", "MSFT")])},
                               "2026-11-10T08:40:00+09:00")[0]
        self.assertEqual(bad["status"], "rejected")
        self.assertIn("지문", bad["errors"][0])
        ok = self._push_files({f"{rd}.csv": body}, "2026-11-10T08:45:00+09:00")[0]
        self.assertEqual(ok["status"], "accepted")

    def test_late_commitment(self):
        rd = "2026-11-10"
        c = self._commit(rd, self._csv(rd, self.ROWS), "2026-11-10T08:30:01+09:00")
        self.assertEqual(c["status"], "late")

    def test_reveal_without_commitment_after_deadline_is_late(self):
        rd = "2026-11-10"
        r = self._push_files({f"{rd}.csv": self._csv(rd, self.ROWS)}, "2026-11-10T08:40:00+09:00")[0]
        self.assertEqual(r["status"], "late")
        self.assertIn("지문 제출 없음", r["errors"][0])

    def test_reveal_after_reveal_deadline_rejected(self):
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        self._commit(rd, body, "2026-11-10T08:20:00+09:00")
        r = self._push_files({f"{rd}.csv": body}, "2026-11-10T12:00:01+09:00")[0]
        self.assertEqual(r["status"], "rejected")

    def test_second_commitment_rejected(self):
        rd = "2026-11-10"
        self._commit(rd, self._csv(rd, self.ROWS), "2026-11-10T08:00:00+09:00")
        c2 = self._commit(rd, self._csv(rd, [("s1", "KR", "000660"), ("s1", "US", "MSFT")]), "2026-11-10T08:10:00+09:00")
        self.assertEqual(c2["status"], "rejected")

    def test_early_reveal_flagged(self):
        rd = "2026-11-10"
        r = self._push_files({f"{rd}.csv": self._csv(rd, self.ROWS)}, "2026-11-10T08:10:00+09:00")[0]
        self.assertEqual(r["status"], "accepted")
        self.assertTrue(r.get("early_reveal"))

    def test_locked_at_after_commitment_rejected(self):
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS, locked="08:25")
        self._commit(rd, body, "2026-11-10T08:20:00+09:00")
        r = self._push_files({f"{rd}.csv": body}, "2026-11-10T08:40:00+09:00")[0]
        self.assertEqual(r["status"], "rejected")

    def test_before_start_date_commitment_not_used(self):
        rd = "2026-11-06"
        c = self._commit(rd, self._csv(rd, self.ROWS), "2026-11-06T08:00:00+09:00")
        self.assertEqual(c["status"], "rejected")

    def test_write_commitment_matches_raw_bytes(self):
        import hashlib
        p = self.repo / "x" / "2026-11-10.csv"; p.parent.mkdir()
        p.write_bytes("a,b\r\n1,2\r\n".encode())
        out = L.write_commitment(p)
        self.assertEqual(out.name, "2026-11-10.sha256")
        self.assertEqual(out.read_text().split()[0], hashlib.sha256(p.read_bytes()).hexdigest())

    def test_commit_and_csv_in_same_push_before_deadline_flagged(self):
        import hashlib
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        sha = hashlib.sha256(body.encode()).hexdigest()
        rs = self._push_files({f"{rd}.sha256": f"{sha}  {rd}.csv\n", f"{rd}.csv": body}, "2026-11-10T08:10:00+09:00")
        self.assertEqual([r["status"] for r in rs], ["committed", "accepted"])
        self.assertTrue(rs[1].get("early_reveal"))


class LeagueBottom(unittest.TestCase):
    """규칙 v1.8: 두 팀 10명 통합 순위의 꼴등 1명만 퇴출."""
    CLAUDE = ["buffett", "lynch", "dalio", "wood", "burry"]
    SHUSHU = ["s1", "s2", "s3", "s4", "s5"]

    def _league(self):
        d = new_league()
        imp = d / "imports" / "shushu"; imp.mkdir(parents=True)
        (imp / "roster.json").write_text(json.dumps({
            "members": [{"id": s, "label": f"{s}형", "version": 1} for s in self.SHUSHU],
            "bench": [{"id": "s6", "label": "s6형", "version": 1}]}, ensure_ascii=False))
        L.append(d, "approvals", {"type": "bench", "team": "shushu", "agent_id": "s6", "decision": "approved"})
        return d

    def _scores(self, d, team, results):
        days = ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
        slots = [(rd, m) for rd in days for m in ("KR", "US")]
        cfg = L.load_config(d)
        for agent, scores in results.items():
            for (rd, m), sc in zip(slots, scores):
                t = "005930" if m == "KR" else "AAPL"
                rec = L.make_pick(team, agent, 1, rd, m, t, t, f"{rd}T08:00:00+09:00", "", [], [{"url": "x", "as_of": rd}], cfg)
                L.append(d, "picks", rec)
                if sc is not None:
                    L.append(d, "scores", {"pick_id": rec["pick_id"], "status": "final", "score": sc})

    def test_bottom_from_other_team_eliminated(self):
        d = self._league()
        self._scores(d, "claude", {a: [1.0 + i] * 10 for i, a in enumerate(self.CLAUDE)})
        self._scores(d, "shushu", {s: [0.5 + i] * 10 for i, s in enumerate(self.SHUSHU)})
        lg = L.weekly_league(d, "2026-W46")
        self.assertEqual(len(lg["ranking"]), 10)
        self.assertEqual((lg["decision"]["eliminate_team"], lg["decision"]["eliminate"]), ("shushu", "s1"))
        self.assertEqual(lg["decision"]["replacement"], "s6")
        self.assertIsNone(L.weekly(d, "2026-W46", "claude")["decision"]["eliminate"])
        self.assertEqual(L.weekly(d, "2026-W46", "shushu")["decision"]["eliminate"], "s1")

    def test_team_below_ratio_holds(self):
        d = self._league()
        self._scores(d, "claude", {a: [1.0] * 10 for a in self.CLAUDE})
        self._scores(d, "shushu", {s: [2.0 + i] * 5 + [None] * 5 for i, s in enumerate(self.SHUSHU)})   # 25/50 < 30
        lg = L.weekly_league(d, "2026-W46")
        self.assertIsNone(lg["decision"]["eliminate"])
        self.assertTrue(any("25건 < 30건" in r for r in lg["decision"]["hold_reasons"]))

    def test_unscored_not_counted_as_zero(self):
        d = self._league()
        self._scores(d, "claude", {a: [1.0] * 10 for a in self.CLAUDE[:4]} | {"burry": [0.9] * 7 + [None] * 3})
        self._scores(d, "shushu", {s: [2.0] * 10 for s in self.SHUSHU})
        r = next(x for x in L.weekly_league(d, "2026-W46")["ranking"] if x["agent_id"] == "burry")
        self.assertEqual((r["scored"], r["avg"], r["held_or_pending"]), (7, 0.9, 3))

    def test_close_applies_to_roster(self):
        d = self._league()
        self._scores(d, "claude", {a: [1.0 + i] * 10 for i, a in enumerate(self.CLAUDE)})
        self._scores(d, "shushu", {s: [0.5 + i] * 10 for i, s in enumerate(self.SHUSHU)})
        recs = L.weekly_close(d, "2026-W46", now="2026-11-16T06:30:00+09:00")
        self.assertEqual(sorted((r["team"], r["eliminate"]) for r in recs), [("claude", None), ("shushu", "s1")])
        self.assertEqual(L.weekly_close(d, "2026-W46"), [])
        ro = L.load_roster(d)
        self.assertEqual(next(a for a in ro["shushu"] if a["id"] == "s1")["status"], "eliminated")
        self.assertEqual(next(a for a in ro["shushu"] if a["id"] == "s6")["joined_week"], "2026-W47")
        self.assertTrue(all(a["status"] == "active" for a in ro["claude"]))

    def test_ratio_threshold_for_holiday_week(self):
        w = {"min_scored_ratio": 0.6}
        self.assertEqual((L._min_needed(10, w, "x"), L._min_needed(9, w, "x"), L._min_needed(45, w, "x")), (6, 6, 27))
