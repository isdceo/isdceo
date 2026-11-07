"""AI 투자 리그 규칙 테스트.  실행: python3 -m unittest discover -s tests -v"""
import json, re, shutil, sys, tempfile, unittest
from datetime import date, datetime, timezone
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
    pin_roster_v1(d / "agents" / "roster.json")
    return d


def pin_roster_v1(dst):
    """시험 고정값: 실제 명단의 지침 버전(실전 v2 등)과 무관하게 v1로 둔다. 버전 규칙 시험은 따로 버전을 넣는다."""
    r = json.loads((ROOT / "league" / "agents" / "roster.json").read_text())
    for key in r:
        for a in r[key] if isinstance(r[key], list) else []:
            if isinstance(a, dict) and "version" in a:
                a["version"] = 1
                a.pop("versions", None)
    Path(dst).write_text(json.dumps(r, ensure_ascii=False))


def use_mode(d, mode="combined_bottom1", **watch):
    """시험용 설정 바꾸기: 주간 방식(예전 통합 방식 시험용)·관망 한도."""
    p = d / "config.json"
    c = json.loads(p.read_text())
    c["weekly"]["mode"] = mode
    if watch:
        c.setdefault("watch", {}).update(watch)
    p.write_text(json.dumps(c, ensure_ascii=False))
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
        pin_roster_v1(lg / "agents" / "roster.json")
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
        use_mode(d)                                                # 예전 통합 방식(v1.8) 시험
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

    def test_pick_lines_drop_prices(self):
        """한 줄 선택 이유: 가격처럼 보이는 문장·너무 긴 문장은 버리고 나머지는 그대로 싣는다."""
        import dashboard_data as D, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "lines").mkdir()
            (Path(tmp) / "lines" / "2026-11-05.json").write_text(json.dumps({
                "a": "불닭이 해외 매출 84%! 이익은 47% 늘었어요.", "b": "종가 191,900원이면 싸죠.", "c": "$245에 샀어요",
                "d": "목표주가까지 간다", "e": "가" * 81}, ensure_ascii=False))
            self.assertEqual(D.load_lines(Path(tmp)), {"a": "불닭이 해외 매출 84%! 이익은 47% 늘었어요."})
        for v in D.load_lines(L.ROOT / "league" / "sandbox").values():
            self.assertIsNone(D.PRICE_LIKE.search(v))

    def test_check_lines(self):
        """한 줄 이유 검사: 마감 전·다른 팀 종목·가격 표현·빠진 종목을 잡고, 정상 파일은 통과."""
        import dashboard_data as D, tempfile
        base = L.ROOT / "league" / "sandbox"
        ok = D.check_lines(base / "lines" / "2026-11-05-sandbox-claude.json", base, datetime.fromisoformat("2026-11-05T09:00:00+09:00"))
        self.assertEqual(ok, [])
        early = D.check_lines(base / "lines" / "2026-11-05-sandbox-claude.json", base, datetime.fromisoformat("2026-11-05T08:00:00+09:00"))
        self.assertTrue(any("마감" in e for e in early))
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "2026-11-05-sandbox-claude.json"
            f.write_text(json.dumps({"2026-11-05-sandbox-claude-buffett-KR": "종가 191,900원이면 싸지.",
                                     "2026-11-06-sandbox-shushu-s1-KR": "남의 종목"}, ensure_ascii=False))
            errs = D.check_lines(f, base, datetime.fromisoformat("2026-11-05T09:00:00+09:00"))
            self.assertTrue(any("가격" in e for e in errs))
            self.assertTrue(any("이 팀의 종목이 아님" in e for e in errs))
            self.assertTrue(any("한 줄 이유가 없는 종목" in e for e in errs))
            bad = Path(tmp) / "lines.json"; bad.write_text("{}")
            self.assertTrue(D.check_lines(bad, base))

    def test_play_page_public_only(self):
        """지인 공개용 게임 화면: 마감 전 종목·원 가격·회사 로고·운영 탭이 없다."""
        import build_play as B, tempfile
        cfg = L.load_config(L.ROOT / "league")
        for now in ("2026-11-05T08:29:00+09:00", "2026-11-05T09:00:00+09:00"):
            t = datetime.fromisoformat(now)
            with tempfile.TemporaryDirectory() as tmp:
                html, js = B.build(Path(tmp), t)
                data = json.loads(js.read_text().split("window.TABLE = ", 1)[1].rstrip().rstrip(";"))
                for p in data["picks"]:
                    self.assertGreaterEqual(t, L.lock_deadline(date.fromisoformat(p["round_date"]), cfg), p["pick_id"])
                self.assertNotIn("logos", data)
                self.assertIsNone(re.search(r'"(base_close|eval_close|close|amount)"\s*:', js.read_text()))
                page = html.read_text()
                self.assertNotIn('data-page="ops"', page)
                self.assertNotIn("data:image/png", page)
                self.assertIn("한국거래소 통계정보", page)

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

    def test_same_push_processed_twice_records_once(self):
        """3차 검수: 겹친 영수증을 최신 원장 위에서 다시 처리하거나 재실행해도 같은 push는 한 번만 기록."""
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        self._commit(rd, body, "2026-11-10T08:20:00+09:00")
        before = self.run("rev-parse", "HEAD")
        p = self.repo / "league" / "imports" / "shushu" / f"{rd}.csv"; p.write_text(body)
        self.run("add", "."); self.run("commit", "-qm", "reveal")
        ev = {"before": before, "after": self.run("rev-parse", "HEAD"), "ref": "refs/heads/main", "pusher": {"name": "x"},
              "repository": {"pushed_at": int(datetime.fromisoformat("2026-11-10T08:40:00+09:00").timestamp())}, "commits": []}
        first = L.process_push(ev, run_id="1", cwd=self.repo)
        again = L.process_push(ev, run_id="2", cwd=self.repo)
        self.assertEqual((first[0]["status"], again), ("accepted", []))
        self.assertEqual(len(L.read_ledger(self.repo / "league", "picks")), 2)

    def test_reveal_before_commitment_receipt_waits_not_late(self):
        """4차 검수: 지문·원본을 연달아 push해 원본 판정이 지문 영수증보다 먼저 돌아도 '늦음'으로 굳지 않는다."""
        import hashlib
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        sha = hashlib.sha256(body.encode()).hexdigest()
        # 지문 push (아직 영수증 처리 전)
        c_before = self.run("rev-parse", "HEAD")
        p = self.repo / "league" / "imports" / "shushu"; p.mkdir(parents=True, exist_ok=True)
        (p / f"{rd}.sha256").write_text(f"{sha}  {rd}.csv\n")
        self.run("add", "."); self.run("commit", "-qm", "commit")
        c_ev = {"before": c_before, "after": self.run("rev-parse", "HEAD"), "ref": "refs/heads/main", "pusher": {"name": "x"},
                "repository": {"pushed_at": int(datetime.fromisoformat("2026-11-10T08:20:00+09:00").timestamp())}, "commits": []}
        # 원본 push가 먼저 처리됨 → 대기 신호, 원장에는 아무것도 안 남음
        r_before = c_ev["after"]
        (p / f"{rd}.csv").write_text(body)
        self.run("add", "."); self.run("commit", "-qm", "reveal")
        r_ev = {"before": r_before, "after": self.run("rev-parse", "HEAD"), "ref": "refs/heads/main", "pusher": {"name": "x"},
                "repository": {"pushed_at": int(datetime.fromisoformat("2026-11-10T08:31:00+09:00").timestamp())}, "commits": []}
        with self.assertRaises(L.CommitmentPending):
            L.process_push(r_ev, run_id="2", cwd=self.repo)
        self.assertEqual(L.read_ledger(self.repo / "league", "submissions"), [])
        # 지문 영수증이 기록된 뒤 다시 처리하면 접수
        self.assertEqual(L.process_push(c_ev, run_id="1", cwd=self.repo)[0]["status"], "committed")
        self.assertEqual(L.process_push(r_ev, run_id="2", cwd=self.repo)[0]["status"], "accepted")

    def test_reveal_after_late_commitment_is_late_not_pending(self):
        """지문 자체가 늦어 영수증이 late면 원본은 기다리지 않고 늦음."""
        rd = "2026-11-10"; body = self._csv(rd, self.ROWS)
        self.assertEqual(self._commit(rd, body, "2026-11-10T08:30:05+09:00")["status"], "late")
        r = self._push_files({f"{rd}.csv": body}, "2026-11-10T08:40:00+09:00")[0]
        self.assertEqual(r["status"], "late")

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
        return use_mode(d)                                         # 예전 통합 방식(v1.8) 시험

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


class DashboardSplit(unittest.TestCase):
    def test_split_files_fit_and_keep_code(self):
        """현황판은 세 파일로 올린다: 각 256KB 이하, 스타일·스크립트가 사본과 그대로 같음."""
        import dashboard_split as DS
        src = DS.SRC.read_text()
        parts = DS.split(src)
        self.assertEqual(set(parts), {"index.html", "style.css", "app.js"})
        for name, body in parts.items():
            self.assertLess(len(body.encode()), DS.LIMIT, name)
        self.assertIn(parts["style.css"], src); self.assertIn(parts["app.js"], src)
        self.assertTrue(parts["index.html"].startswith('<meta name="dash-one-writer">'))
        self.assertIn('<script src="app.js"></script>', parts["index.html"])
        self.assertNotIn("<script>", parts["index.html"]); self.assertNotIn("<style>", parts["index.html"])


class ShushuRepoSync(unittest.TestCase):
    """B안: 슈슈 전용 저장소 push를 그 저장소의 서버 push 시각으로 판정해 메인으로 가져온다."""
    def setUp(self):
        Receipts.setUp(self)                                   # 임시 메인 저장소 (Receipts 시험은 다시 돌리지 않음)
        import subprocess, hashlib
        self.sh = hashlib
        base = Path(tempfile.mkdtemp())
        self.bare, self.work, self.ext = base / "s.git", base / "work", base / "ext"
        g = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
        self.g = g
        g(base, "init", "-q", "--bare", str(self.bare))
        g(base, "clone", "-q", str(self.bare), str(self.work))
        g(self.work, "config", "user.email", "s@s"); g(self.work, "config", "user.name", "s")
        (self.work / "README.md").write_text("x"); g(self.work, "add", "."); g(self.work, "commit", "-qm", "init")
        g(self.work, "push", "-q", "origin", "HEAD:main")
        g(base, "clone", "-q", str(self.bare), str(self.ext))
        self.acts, self.last = [], g(self.work, "rev-parse", "HEAD")
        import shushu_sync as X
        self.X = X
        self.set_wake_round(True)                              # 깨우기 시험은 라운드 시작 깨우기를 켠 상태로

    def set_wake_round(self, on):
        cp = self.repo / "league" / "config.json"; c = json.loads(cp.read_text())
        c.setdefault("shushu_repo", {})["wake_round"] = on; cp.write_text(json.dumps(c, ensure_ascii=False))

    def spush(self, files: dict, at: str):
        for name, text in files.items():
            p = self.work / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        self.g(self.work, "add", "."); self.g(self.work, "commit", "-qm", "p"); self.g(self.work, "push", "-q", "origin", "HEAD:main")
        after = self.g(self.work, "rev-parse", "HEAD")
        utc = datetime.fromisoformat(at).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.acts.append({"id": len(self.acts) + 1, "before": self.last, "after": after, "timestamp": utc,
                          "activity_type": "push", "actor": {"login": "shushu-bot"}})
        self.last = after

    def sync(self, now):
        return self.X.pull(self.repo, self.ext, self.acts, "o/shushu", now=datetime.fromisoformat(now), run_id="9")

    def csv(self, rd):
        return CommitReveal._csv(self, rd, CommitReveal.ROWS)

    def test_commit_then_reveal_judged_by_source_push_time(self):
        rd = "2026-11-10"; body = self.csv(rd); h = self.sh.sha256(body.encode()).hexdigest()
        self.spush({f"submit/{rd}.sha256": f"{h}  {rd}.csv\n"}, f"{rd}T08:20:00+09:00")
        self.spush({f"submit/{rd}.csv": body}, f"{rd}T08:40:00+09:00")
        out = self.sync(f"{rd}T08:55:00+09:00")                # 동기화가 늦게 돌아도 판정은 전용 저장소 push 시각
        self.assertEqual([r["receipts"][0]["status"] for r in out], ["committed", "accepted"])
        subs = L.read_ledger(self.repo / "league", "submissions")
        self.assertEqual(subs[0]["pushed_at"], f"{rd}T08:20:00+09:00")
        self.assertEqual(subs[0]["judged_by"], "shushu_repo.activity.timestamp")
        self.assertEqual(subs[1]["source"]["repo"], "o/shushu")
        self.assertEqual((self.repo / "league/imports/shushu" / f"{rd}.csv").read_bytes(), body.encode())
        self.assertEqual(self.sync(f"{rd}T09:00:00+09:00"), [])                       # 같은 push는 한 번만
        self.assertEqual(len(L.read_ledger(self.repo / "league", "external_pushes")), 2)

    def test_late_commitment_by_source_time(self):
        rd = "2026-11-10"; h = self.sh.sha256(self.csv(rd).encode()).hexdigest()
        self.spush({f"submit/{rd}.sha256": f"{h}  {rd}.csv\n"}, f"{rd}T08:30:05+09:00")
        self.assertEqual(self.sync(f"{rd}T08:31:00+09:00"), [])                     # 반영 지연 여유(2분) 전
        self.assertEqual(self.sync(f"{rd}T08:33:00+09:00")[0]["receipts"][0]["status"], "late")

    def test_csv_before_deadline_held_out_of_main(self):
        """마감 전 원본은 메인에 들이지 않는다(로로 팀 세션이 볼 수 없게). 마감 뒤 처리하면 마감 전 공개로 기록."""
        rd = "2026-11-10"; body = self.csv(rd)
        self.spush({f"submit/{rd}.csv": body}, f"{rd}T08:10:00+09:00")
        out = self.sync(f"{rd}T08:15:00+09:00")
        self.assertEqual(out[0]["held_files"], [f"submit/{rd}.csv"])
        self.assertFalse((self.repo / "league/imports/shushu" / f"{rd}.csv").exists())
        r = self.sync(f"{rd}T08:35:00+09:00")[0]["receipts"][0]
        self.assertEqual(r["status"], "accepted")
        last = L.read_ledger(self.repo / "league", "submissions")[-1]
        self.assertTrue(last.get("sealed")); self.assertFalse(last.get("early_reveal"))   # 비공개 저장소에 봉인 보관 → 마감 전 공개 아님

    def test_only_allowed_paths_copied(self):
        rd = "2026-11-10"; h = self.sh.sha256(self.csv(rd).encode()).hexdigest()
        self.spush({f"submit/{rd}.sha256": f"{h}  {rd}.csv\n", ".github/workflows/x.yml": "on: push",
                    "league/ledger/scores.jsonl": "{}", "from-league/league/config.json": "{}"}, f"{rd}T08:20:00+09:00")
        out = self.sync(f"{rd}T08:23:00+09:00")
        self.assertEqual(out[0]["ignored_count"], 3)
        self.assertFalse((self.repo / ".github").exists())
        self.assertFalse((self.repo / "league/ledger/scores.jsonl").exists())

    def test_branch_push_then_merge_counts_once(self):
        """Codex 클라우드처럼 작업 브랜치에 지문을 push한 뒤 늦게 병합해도, 판정은 브랜치 push 시각 한 번뿐."""
        rd = "2026-11-10"; h = self.sh.sha256(self.csv(rd).encode()).hexdigest()
        self.spush({f"submit/{rd}.sha256": f"{h}  {rd}.csv\n"}, f"{rd}T08:22:00+09:00")
        self.acts[-1]["ref"] = "refs/heads/codex/submit"
        self.spush({"README.md": "merge"}, f"{rd}T08:45:00+09:00")       # 병합 push(같은 지문이 main에 들어옴)
        self.acts[-1]["before"] = self.acts[0]["before"]                  # main 기준으로는 지문+README 변경
        out = self.sync(f"{rd}T08:50:00+09:00")
        self.assertEqual(out[0]["receipts"][0]["status"], "committed")
        self.assertEqual(out[1]["receipts"], [])                         # 같은 내용 → 영수증 없음
        self.assertEqual([s["status"] for s in L.read_ledger(self.repo / "league", "submissions")], ["committed"])

    def test_message_to_roro_held_until_noon(self):
        """슈슈 → 로로 메시지는 push한 날 12:00 뒤에만 메인에 들어온다(로로 팀이 당일 종목 정보를 미리 보지 않게)."""
        self.spush({"to-roro/2026-11-10-question.md": "질문"}, "2026-11-10T08:10:00+09:00")
        self.assertEqual(len(self.sync("2026-11-10T11:50:00+09:00")[0]["held_files"]), 1)
        self.assertFalse((self.repo / "league/inbox/shushu/2026-11-10-question.md").exists())
        self.assertEqual(self.sync("2026-11-10T12:05:00+09:00")[0]["status"], "released")
        self.assertEqual((self.repo / "league/inbox/shushu/2026-11-10-question.md").read_text(), "질문")

    def test_wakes_once_each(self):
        """슈슈 깨우기: 라운드 시작·원본 공개·새 공지를 한 번씩만, 처음 켤 때 기존 공지는 보내지 않음."""
        shutil.copytree(ROOT / "docs" / "codex-notices", self.repo / "docs" / "codex-notices")
        posted = []
        post = lambda b: posted.append(b) or f"u{len(posted)}"
        w = self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat("2026-11-10T07:05:00+09:00"), post=post)
        self.assertEqual([x["kind"] for x in w], ["round"])
        self.assertIn("submit/2026-11-10.sha256", posted[0]); self.assertTrue(posted[0].startswith("@codex"))
        self.assertEqual(self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat("2026-11-10T07:15:00+09:00"), post=post), [])
        rd = "2026-11-10"; h = self.sh.sha256(self.csv(rd).encode()).hexdigest()
        self.spush({f"submit/{rd}.sha256": f"{h}  {rd}.csv\n"}, f"{rd}T08:20:00+09:00"); self.sync(f"{rd}T08:31:00+09:00")
        w = self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat("2026-11-10T08:31:00+09:00"), post=post)
        self.assertEqual([x["kind"] for x in w], ["reveal"])
        (self.repo / "docs" / "codex-notices" / "replies").mkdir(exist_ok=True)
        (self.repo / "docs" / "codex-notices" / "replies" / "2026-11-10-answer.md").write_text("답")
        self.assertEqual(self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat("2026-11-10T10:00:00+09:00"), post=post), [])  # 라운드 시간엔 보내지 않음
        w = self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat("2026-11-10T12:30:00+09:00"), post=post)
        self.assertEqual([x["kind"] for x in w], ["notice"]); self.assertIn("2026-11-10-answer.md", posted[-1])
        self.assertNotIn("v2.0-market-leagues", posted[-1])                      # 기존 공지는 처음 켤 때 표시만

    # ── 검수 1차 재현 사례 ──
    def _sha_line(self, rd):
        return f"{self.sh.sha256(self.csv(rd).encode()).hexdigest()}  {rd}.csv\n"

    def test_rename_into_submit_is_seen(self):
        rd = "2026-11-10"; body = self.csv(rd)
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd), f"practice/{rd}.csv": body}, f"{rd}T08:20:00+09:00")
        self.g(self.work, "mv", f"practice/{rd}.csv", f"submit/{rd}.csv"); self.spush({}, f"{rd}T08:40:00+09:00")
        out = self.sync(f"{rd}T08:50:00+09:00")
        self.assertIn("accepted", [x["status"] for r in out for x in r["receipts"]])

    def test_commitment_with_extra_text_not_imported(self):
        rd = "2026-11-10"
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd) + "KR 005930 오늘 픽\n"}, f"{rd}T08:05:00+09:00")
        out = self.sync(f"{rd}T08:10:00+09:00")
        self.assertEqual(out[0]["receipts"], []); self.assertTrue(out[0]["problems"])
        self.assertFalse((self.repo / "league/imports/shushu" / f"{rd}.sha256").exists())

    def test_past_dated_file_still_held_before_deadline(self):
        rd = "2026-11-10"
        self.spush({"submit/2026-11-09-debate.md": "오늘 005930", "lines/2026-11-09-shushu.json": "{}"}, f"{rd}T08:00:00+09:00")
        out = self.sync(f"{rd}T08:10:00+09:00")
        self.assertEqual(sorted(out[0]["held_files"]), ["lines/2026-11-09-shushu.json", "submit/2026-11-09-debate.md"])
        self.assertFalse((self.repo / "league/imports/shushu/2026-11-09-debate.md").exists())

    def test_ignored_names_not_written_to_ledger(self):
        rd = "2026-11-10"
        self.spush({"notes/KR-005930-US-NVDA.txt": "x", f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:00:00+09:00")
        self.sync(f"{rd}T08:05:00+09:00")
        self.assertNotIn("005930", (self.repo / "league/ledger/external_pushes.jsonl").read_text())

    def test_bad_date_and_missing_commit_do_not_stop_sync(self):
        rd = "2026-11-10"
        self.spush({"submit/2026-02-30.sha256": "x"}, f"{rd}T08:00:00+09:00")
        self.acts.append({"id": 99, "before": self.last, "after": "f" * 40, "timestamp": "2026-11-09T23:01:00Z",
                          "activity_type": "push", "actor": {"login": "x"}})
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:20:00+09:00")
        out = self.sync(f"{rd}T08:25:00+09:00")
        # 마감 전 push를 받을 수 없으면: 순서를 지키려고 뒤의 push는 기다린다
        self.assertEqual(sorted(r["status"] for r in out), ["processed", "retry"])
        self.assertEqual([r["status"] for r in self.sync(f"{rd}T08:35:00+09:00")], ["retry"])
        # 3번째에 확정 → 그 라운드는 운영자 확인 대기, 뒤 지문은 자동 접수하지 않음(골라 되살리기 차단)
        out3 = self.sync(f"{rd}T08:45:00+09:00")
        self.assertEqual([r["status"] for r in out3], ["error", "processed"])
        self.assertEqual(out3[1]["receipts"], []); self.assertEqual(len(out3[1]["held_files"]), 1)
        self.assertEqual(L.read_ledger(self.repo / "league", "submissions"), [])
        # 운영자 확인 뒤 해제하면 원래 push 시각(08:20)으로 판정
        L.append(self.repo / "league", "external_pushes", {"repo": "o/shushu", "type": "untaint", "team": "shushu", "round": rd, "reason": "확인"})
        r = self.sync(f"{rd}T09:00:00+09:00")
        self.assertEqual(r[0]["receipts"][0]["status"], "committed")
        self.assertEqual(L.read_ledger(self.repo / "league", "submissions")[0]["pushed_at"], f"{rd}T08:20:00+09:00")

    def test_held_file_does_not_block_later_commitment(self):
        """다음 날 토론 파일이 보류돼도 뒤의 당일 지문은 바로 처리되고, 원본 공개 깨우기가 나간다."""
        rd = "2026-11-10"
        self.spush({"submit/2026-11-11-debate.md": "준비"}, f"{rd}T07:50:00+09:00")
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:20:00+09:00")
        out = self.sync(f"{rd}T08:40:00+09:00")
        self.assertEqual(out[1]["receipts"][0]["status"], "committed")
        posted = []
        w = self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat(f"{rd}T08:41:00+09:00"), post=lambda b: posted.append(b) or "u")
        self.assertEqual([x["kind"] for x in w], ["reveal"])

    def test_message_in_round_window_waits_until_noon(self):
        self.spush({"to-roro/2026-11-09-note.md": "전날 저녁"}, "2026-11-09T20:00:00+09:00")
        held = self.sync("2026-11-10T07:05:00+09:00")[0]["held_files"]
        self.assertEqual(len(held), 1); self.assertNotIn("note", held[0])                         # 보류 중에는 이름 대신 해시
        self.assertNotIn("2026-11-09-note", (self.repo / "league/ledger/external_pushes.jsonl").read_text())
        self.assertFalse((self.repo / "league/inbox/shushu/2026-11-09-note.md").exists())
        self.assertEqual(self.sync("2026-11-10T12:05:00+09:00")[0]["status"], "released")

    def test_new_branch_diffs_against_main(self):
        """새 브랜치 첫 push(before=0)는 기본 브랜치에서 갈라진 뒤의 파일만 본다."""
        rd = "2026-11-10"
        self.spush({"README.md": "y"}, f"{rd}T07:00:00+09:00")
        self.g(self.work, "checkout", "-q", "-b", "codex/x")
        (self.work / "submit").mkdir(exist_ok=True); (self.work / "submit" / f"{rd}.sha256").write_text(self._sha_line(rd))
        self.g(self.work, "add", "."); self.g(self.work, "commit", "-qm", "b"); self.g(self.work, "push", "-q", "origin", "codex/x")
        after = self.g(self.work, "rev-parse", "HEAD")
        self.acts.append({"id": 50, "before": "0" * 40, "after": after, "timestamp": "2026-11-09T23:20:00Z",
                          "activity_type": "branch_creation", "ref": "refs/heads/codex/x", "actor": {"login": "c"}})
        self.g(self.ext, "fetch", "-q", "origin")
        out = self.sync(f"{rd}T08:30:00+09:00")
        self.assertEqual(out[-1]["files"], [f"submit/{rd}.sha256"])
        self.assertEqual(out[-1]["receipts"][0]["status"], "committed")

    def test_accepted_file_not_overwritten(self):
        rd = "2026-11-10"; body = self.csv(rd)
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:20:00+09:00")
        self.spush({f"submit/{rd}.csv": body}, f"{rd}T08:40:00+09:00")
        self.spush({f"submit/{rd}.csv": body.replace("005930", "000660")}, f"{rd}T08:50:00+09:00")
        out = self.sync(f"{rd}T09:00:00+09:00")
        self.assertIn("덮어쓰지 않음", out[-1]["note"])
        self.assertEqual((self.repo / "league/imports/shushu" / f"{rd}.csv").read_text(), body)

    def test_round_wake_off_when_shushu_runs_own_schedule(self):
        """슈슈 요청(2026-11-07): 자체 예약으로 실행하므로 07:05 시작 댓글은 보내지 않는다(중복 실행 방지)."""
        self.set_wake_round(False)
        w = self.X.due_wakes(self.repo, datetime.fromisoformat("2026-11-10T07:05:00+09:00"))
        self.assertNotIn("round", [x["kind"] for x in w])

    def test_wake_not_reposted_when_marker_exists(self):
        """push 충돌로 원장 기록이 사라져 다시 돌아도, 채널에 같은 표식 댓글이 있으면 다시 달지 않는다."""
        posted = []
        now = datetime.fromisoformat("2026-11-10T07:05:00+09:00")
        mk = self.X._marker({"kind": "round", "key": "2026-11-10"})
        w = self.X.wake(self.repo, "o/shushu", "t", now=now, post=lambda b: posted.append(b) or "u", existing=["앞 댓글 " + mk])
        self.assertEqual((posted, w[0]["url"]), ([], "already-posted"))

    def test_pending_rollback_keeps_earlier_receipts(self):
        """지문 대기로 한 push를 되돌려도, 같은 실행에서 앞서 처리한 push의 영수증은 남는다(원장 추적 중인 실제 상황)."""
        rd = "2026-11-10"
        (self.repo / "league/ledger/submissions.jsonl").write_text("")                     # 원장이 이미 추적되는 상태
        (self.repo / "league/ledger/external_pushes.jsonl").write_text("")
        self.run("add", "."); self.run("commit", "-qm", "ledgers")
        self.spush({f"practice/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:10:00+09:00")
        self.spush({f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:40:00+09:00")
        real = L.process_push
        def fake(ev, **kw):
            if any("submit/" in f or "imports/shushu/" in f for f in L.changed_submission_files(ev, kw["cwd"])):
                raise L.CommitmentPending("대기")
            return real(ev, **kw)
        L.process_push = fake
        try:
            out = self.sync(f"{rd}T08:50:00+09:00")
        finally:
            L.process_push = real
        self.assertEqual([r["status"] for r in out], ["processed", "pending"])
        subs = L.read_ledger(self.repo / "league" / "sandbox", "submissions")
        self.assertEqual([x["status"] for x in subs], ["committed"])                         # 앞 push 영수증 유지
        self.assertFalse((self.repo / "league/imports/shushu" / f"{rd}.csv").exists())       # 대기한 push만 되돌림
        self.assertEqual(L.verify(self.repo / "league"), [])

    def test_cannot_pick_commitment_by_hiding_branches(self):
        """3차 검수 N8: 지문 두 개를 다른 브랜치로 올리고 지운 뒤 하나만 되살려도 고를 수 없다."""
        rd = "2026-11-10"
        h1 = self._sha_line(rd)
        h2 = f"{self.sh.sha256(b'other').hexdigest()}  {rd}.csv\n"
        self.spush({f"submit/{rd}.sha256": h1}, f"{rd}T08:20:00+09:00")
        self.acts[-1]["after"] = "a" * 40                                     # 지운 브랜치 a (받을 수 없음)
        self.spush({f"submit/{rd}.sha256": h2}, f"{rd}T08:21:00+09:00")       # 되살린 브랜치 b
        for t in ("08:30", "08:40"):
            self.assertEqual([r["status"] for r in self.sync(f"{rd}T{t}:00+09:00")], ["retry"])
        self.sync(f"{rd}T08:50:00+09:00")
        self.assertEqual(L.read_ledger(self.repo / "league", "submissions"), [])           # b 자동 접수 없음

    def test_cannot_pick_held_reveal_by_hiding_branch(self):
        """3차 검수 N9: 보류된 마감 전 원본 둘 중 하나를 지워도 다른 하나가 대신 접수되지 않는다."""
        rd = "2026-11-10"
        self.spush({f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:10:00+09:00")
        self.spush({f"submit/{rd}.csv": CommitReveal._csv(self, rd, [("s1", "KR", "000660"), ("s1", "US", "MSFT")])}, f"{rd}T08:15:00+09:00")
        self.sync(f"{rd}T08:20:00+09:00")                                     # 둘 다 보류
        real = self.X._restore_held
        def fake(ext, act, units):
            if act["id"] == 1:
                raise RuntimeError("받을 수 없음")
            return real(ext, act, units)
        self.X._restore_held = fake
        try:
            for t in ("08:40", "08:50", "09:00", "09:10"):
                self.sync(f"{rd}T{t}:00+09:00")
        finally:
            self.X._restore_held = real
        self.assertEqual([x for x in L.read_ledger(self.repo / "league", "submissions") if x["status"] == "accepted"], [])

    def test_evening_push_hidden_then_restored_cannot_be_picked(self):
        """4차 검수 G1: 전날 저녁 지문 둘을 숨겼다가 마감 뒤 하나만 되살려도 접수되지 않는다(예약이 밀린 경우)."""
        rd = "2026-11-10"
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, "2026-11-09T20:00:00+09:00")
        self.acts[-1]["after"] = "a" * 40
        self.spush({f"submit/{rd}.sha256": f"{self.sh.sha256(b'x').hexdigest()}  {rd}.csv\n"}, "2026-11-09T20:01:00+09:00")
        b_after = self.acts[-1]["after"]; self.acts[-1]["after"] = "b" * 40
        for t in ("08:05", "08:25"):
            self.assertEqual([r["status"] for r in self.sync(f"{rd}T{t}:00+09:00")], ["retry"])
        self.acts[-1]["after"] = b_after                                       # 마감 뒤 b만 되살림
        self.sync(f"{rd}T08:45:00+09:00"); self.sync(f"{rd}T08:55:00+09:00")
        self.assertEqual([x for x in L.read_ledger(self.repo / "league", "submissions") if x["status"] == "committed"], [])

    def test_failure_settled_before_deadline_does_not_taint(self):
        """마감 전에 오류로 확정된 push는 다시 처리되지 않으니 고를 여지가 없다 → 확인 대기로 돌리지 않음."""
        rd = "2026-11-10"
        self.acts.append({"id": 77, "before": self.last, "after": "c" * 40, "timestamp": "2026-11-09T21:00:00Z",
                          "activity_type": "push", "ref": "refs/heads/main", "actor": {"login": "x"}})       # 06:00 KST
        for t in ("07:05", "07:35", "08:00"):
            self.sync(f"{rd}T{t}:00+09:00")
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:20:00+09:00")
        out = self.sync(f"{rd}T08:30:00+09:00")
        self.assertEqual(out[0]["receipts"][0]["status"], "committed")
        self.assertFalse(any(x.get("type") == "taint" for x in L.read_ledger(self.repo / "league", "external_pushes")))

    def test_deleted_branch_kept_by_tag_cannot_be_picked(self):
        """5차 검수 S1: 브랜치를 마감 전에 지우고 태그로 커밋을 살려 둔 뒤 마감 뒤 '받을 수 있음/없음'을 골라도
        두 경우 모두 첫 지문만 인정되거나 확인 대기 — 뒤 지문 H2가 접수되는 길이 없다."""
        rd = "2026-11-10"
        for keep in (True, False):
            self.setUp()
            self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:29:00+09:00")
            a_after = self.acts[-1]["after"]; self.acts[-1]["ref"] = "refs/heads/a"
            self.acts.append({"id": 90, "before": a_after, "after": "0" * 40, "timestamp": "2026-11-09T23:29:30Z",
                              "activity_type": "branch_deletion", "ref": "refs/heads/a", "actor": {"login": "c"}})
            self.spush({f"submit/{rd}.sha256": f"{self.sh.sha256(b'h2').hexdigest()}  {rd}.csv\n"}, f"{rd}T08:29:20+09:00")
            if not keep:
                self.acts[0]["after"] = "e" * 40                                  # 태그를 지워 받을 수 없게 함
            for t in ("08:40", "08:50", "09:00"):
                self.sync(f"{rd}T{t}:00+09:00")
            got = [x["committed_sha256"] for x in L.read_ledger(self.repo / "league", "submissions") if x["status"] == "committed"]
            self.assertNotIn(self.sh.sha256(b"h2").hexdigest(), got)

    def test_taint_wake_tells_to_reveal_anyway(self):
        rd = "2026-11-10"
        L.append(self.repo / "league", "external_pushes", {"repo": "o/shushu", "type": "taint", "team": "shushu", "round": rd, "reason": "t"})
        posted = []
        w = self.X.wake(self.repo, "o/shushu", "t", now=datetime.fromisoformat(f"{rd}T08:41:00+09:00"), post=lambda b: posted.append(b) or "u")
        self.assertEqual([x["kind"] for x in w], ["taint"]); self.assertIn("12:00 전에", posted[0])

    def test_sealed_commit_and_reveal_in_one_push(self):
        """지문과 원본을 08:30 전 한 번에 비공개 저장소에 push: 지문은 바로 committed, 원본은 마감 뒤 자동 accepted(봉인 보관)."""
        rd = "2026-11-10"; body = self.csv(rd)
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd), f"submit/{rd}.csv": body, f"submit/{rd}-debate.md": "토론"}, f"{rd}T08:15:00+09:00")
        out = self.sync(f"{rd}T08:20:00+09:00")
        self.assertEqual(out[0]["receipts"][0]["status"], "committed")
        self.assertFalse((self.repo / "league/imports/shushu" / f"{rd}.csv").exists())          # 마감 전에는 메인에 없음
        out = self.sync(f"{rd}T08:31:00+09:00")
        r = [x for o in out for x in o["receipts"]]
        self.assertEqual([x["status"] for x in r], ["accepted"])
        sub = [x for x in L.read_ledger(self.repo / "league", "submissions") if x["status"] == "accepted"][0]
        self.assertTrue(sub["sealed"]); self.assertNotIn("early_reveal", sub)
        self.assertEqual(sub["commitment_pushed_at"], f"{rd}T08:15:00+09:00")

    def test_mirror_push_not_recorded(self):
        """메인이 보낸 사본(from-league/) push는 기록하지 않는다 — 기록하면 사본·기록이 매 실행 되풀이된다."""
        self.spush({"from-league/README.md": "copy"}, "2026-11-10T08:00:00+09:00")
        self.assertEqual(self.sync("2026-11-10T08:05:00+09:00"), [])
        self.assertEqual(L.read_ledger(self.repo / "league", "external_pushes"), [])

    def test_mirror_has_no_prices(self):
        """사본에는 원 가격이 든 원장(prices·scores·corporate_actions·picks)과 가격 포함 공통 자료가 없다."""
        import tempfile as T
        ext = Path(T.mkdtemp())
        wrote = self.X.mirror(ROOT, ext, today=date(2026, 11, 7))
        bad = [f for f in wrote if re.search(r"ledger/(prices|scores|corporate_actions|picks|price_checks|corrections)\.jsonl$|with-prices", f)]
        self.assertEqual(bad, [])
        self.assertTrue((ext / "from-league" / "receipts-shushu.jsonl").exists())
        cfg = (ext / "from-league" / "league" / "config.json").read_text()
        self.assertNotIn("provider_verified", cfg); self.assertNotRegex(cfg, r"\b[A-Z]{1,5} \d+\.\d{2}\b")
        for f in (ext / "from-league").rglob("*"):
            if f.is_file() and "tools" not in f.parts:
                self.assertIsNone(self.X.PRICE_TEXT.search(f.read_text(errors="replace")), str(f))
        self.assertTrue((ext / "from-league" / "tools" / "league.py").exists())


class SealedSubmission(unittest.TestCase):
    """슈슈 검수(2026-11-07 sealed-submission-review) 재시험: 봉인 판정은 파일마다(원래 push 시각 vs 그 파일 라운드 마감)."""
    RD = "2026-11-10"
    setUp = ShushuRepoSync.setUp
    spush, sync, csv, _sha_line = ShushuRepoSync.spush, ShushuRepoSync.sync, ShushuRepoSync.csv, ShushuRepoSync._sha_line
    set_wake_round = ShushuRepoSync.set_wake_round

    def _sub(self, path_end, status="accepted"):
        return [x for x in L.read_ledger(self.repo / "league", "submissions") + L.read_ledger(self.repo / "league" / "sandbox", "submissions")
                if x["path"].endswith(path_end) and x["status"] == status]

    def _one_push(self, at):
        rd = self.RD
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd), f"submit/{rd}.csv": self.csv(rd), f"submit/{rd}-debate.md": "토론"}, f"{rd}T{at}+09:00")

    def test_first_sync_before_deadline(self):
        self._one_push("08:18:00"); self.sync(f"{self.RD}T08:21:00+09:00"); self.sync(f"{self.RD}T08:31:00+09:00")
        a = self._sub(f"{self.RD}.csv")[0]; self.assertTrue(a.get("sealed")); self.assertNotIn("early_reveal", a)

    def test_first_sync_after_deadline(self):
        """버그 재현 사례: 08:20 push가 2분 대기로 08:31 동기화에서 처음 발견돼도 봉인."""
        self._one_push("08:20:00")
        self.assertEqual(self.sync(f"{self.RD}T08:21:00+09:00"), [])                       # 2분 대기
        self.sync(f"{self.RD}T08:31:00+09:00")
        a = self._sub(f"{self.RD}.csv")[0]; self.assertTrue(a.get("sealed")); self.assertNotIn("early_reveal", a)

    def test_first_sync_exactly_at_deadline(self):
        self._one_push("08:20:00")
        out = self.sync(f"{self.RD}T08:30:00+09:00")
        self.assertEqual(len(out[0]["held_files"]), 2)                                     # 정각에는 아직 보류
        self.sync(f"{self.RD}T08:31:00+09:00")
        self.assertTrue(self._sub(f"{self.RD}.csv")[0].get("sealed"))

    def test_separate_pushes_before_deadline(self):
        rd = self.RD
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:10:00+09:00")
        self.spush({f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:22:00+09:00")
        self.sync(f"{rd}T08:40:00+09:00")
        self.assertTrue(self._sub(f"{rd}.csv")[0].get("sealed"))

    def test_mixed_rounds_flagged_per_file(self):
        """한 push에 오늘(11/10) 원본과 연습 다음 날(11/11) 원본: 파일마다 자기 라운드 마감으로 판정."""
        rd, nx = self.RD, "2026-11-11"
        nbody = self.csv(nx).replace(f"{nx}T07:50:00", f"{rd}T08:00:00")                    # 다음 날 원본을 전날 확정
        nsha = f"{self.sh.sha256(nbody.encode()).hexdigest()}  {nx}.csv\n"
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd), f"submit/{rd}.csv": self.csv(rd),
                    f"practice/{nx}.sha256": nsha, f"practice/{nx}.csv": nbody}, f"{rd}T08:20:00+09:00")
        self.sync(f"{rd}T08:31:00+09:00")
        self.assertTrue(self._sub(f"shushu/{rd}.csv")[0].get("sealed"))
        self.assertEqual(self._sub(f"sandbox-shushu/{nx}.csv"), [])                         # 11/11 원본은 아직 보류
        self.sync(f"{nx}T08:31:00+09:00")
        b = self._sub(f"sandbox-shushu/{nx}.csv")[0]; self.assertTrue(b.get("sealed")); self.assertNotIn("early_reveal", b)

    def test_repeated_sync_no_duplicates(self):
        self._one_push("08:15:00")
        for t in ("08:20", "08:31", "08:40", "09:00"):
            self.sync(f"{self.RD}T{t}:00+09:00")
        self.assertEqual(len(self._sub(f"{self.RD}.csv")), 1)
        self.assertEqual(len(self._sub(f"{self.RD}.sha256", "committed")), 1)

    def test_post_deadline_reveal_is_neither_sealed_nor_early(self):
        rd = self.RD
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:10:00+09:00")
        self.spush({f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:40:00+09:00")
        self.sync(f"{rd}T08:50:00+09:00")
        a = self._sub(f"{rd}.csv")[0]; self.assertNotIn("sealed", a); self.assertNotIn("early_reveal", a)

    def test_true_early_reveal_on_main_path_still_flagged(self):
        """메인 저장소에 마감 전 원본을 바로 올린 경우(운영자 경로)는 여전히 '마감 전 공개'."""
        rd = self.RD
        r = CommitReveal._push_files(self, {f"{rd}.csv": self.csv(rd)}, f"{rd}T08:10:00+09:00")[0]
        self.assertEqual(r["status"], "accepted"); self.assertTrue(r.get("early_reveal")); self.assertNotIn("sealed", r)

    def test_debate_frozen_after_acceptance(self):
        rd = self.RD
        self._one_push("08:15:00"); self.sync(f"{rd}T08:20:00+09:00"); self.sync(f"{rd}T08:31:00+09:00")
        dpath = self.repo / "league/imports/shushu" / f"{rd}-debate.md"
        self.assertEqual(dpath.read_text(), "토론")
        self.spush({f"submit/{rd}-debate.md": "고친 토론"}, f"{rd}T09:00:00+09:00")
        out = self.sync(f"{rd}T09:05:00+09:00")
        self.assertIn("덮어쓰지 않음", out[0]["note"]); self.assertEqual(dpath.read_text(), "토론")
        self.spush({f"submit/{rd}-debate.md": "토론", "README.md": "x2"}, f"{rd}T09:10:00+09:00")   # 같은 내용 재전송
        self.sync(f"{rd}T09:15:00+09:00"); self.assertEqual(dpath.read_text(), "토론")

    def test_debate_before_csv_then_frozen(self):
        """토론이 원본보다 먼저 처리되면 원본 접수 전까지는 갱신, 접수 뒤에는 고정."""
        rd = self.RD
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:10:00+09:00")
        self.spush({f"submit/{rd}-debate.md": "초안"}, f"{rd}T08:35:00+09:00")
        self.sync(f"{rd}T08:40:00+09:00")
        self.spush({f"submit/{rd}-debate.md": "최종", f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:45:00+09:00")
        self.sync(f"{rd}T08:50:00+09:00")
        dpath = self.repo / "league/imports/shushu" / f"{rd}-debate.md"
        self.assertEqual(dpath.read_text(), "최종"); self.assertEqual(len(self._sub(f"{rd}.csv")), 1)
        self.spush({f"submit/{rd}-debate.md": "나중"}, f"{rd}T09:30:00+09:00"); self.sync(f"{rd}T09:40:00+09:00")
        self.assertEqual(dpath.read_text(), "최종")


class HolidaySnapshotMirror(unittest.TestCase):
    """슈슈 시험 ①: 휴장 시장 표시("open": false)가 든 공통 자료가 가격으로 오인돼 사본에서 빠지지 않는다."""
    def test_holiday_snapshot_mirrored(self):
        import shushu_sync as X
        self.assertIsNone(X.NO_PRICE.search('{"markets": {"US": {"open": false, "note": "휴장"}}}'))
        self.assertIsNotNone(X.NO_PRICE.search('{"open": 101.5}')); self.assertIsNotNone(X.NO_PRICE.search('{"close":"95.73"}'))
        main = Path(tempfile.mkdtemp())
        shutil.copytree(L.ROOT / "tools", main / "tools"); (main / "league").mkdir()
        shutil.copy(L.ROOT / "league" / "config.json", main / "league" / "config.json")
        shutil.copytree(L.ROOT / "league" / "agents", main / "league" / "agents")
        r = main / "league" / "rounds" / "2026-11-26"; r.mkdir(parents=True)              # 11/26: 미국 휴장(추수감사절)
        snap, body = L.snapshot(L.ROOT / "league", date(2026, 11, 26), "price-free", now="2026-11-26T06:50:00+09:00")
        self.assertIn('"open": false', body.replace('"open":false', '"open": false'))
        (r / "snapshot.json").write_text(body); (r / "snapshot.json.sha256").write_text("x  snapshot.json\n")
        ext = Path(tempfile.mkdtemp())
        wrote = X.mirror(main, ext, today=date(2026, 11, 26))
        self.assertIn("league/rounds/2026-11-26/snapshot.json", wrote)
        self.assertEqual((ext / "from-league/league/rounds/2026-11-26/snapshot.json").read_text(), body)
        self.assertNotIn("snapshot", (ext / "from-league" / "skipped.txt").read_text())


class LinesWithoutLedger(unittest.TestCase):
    """슈슈 요청: 원장 없이(전용 저장소 사본) 접수 종목 목록으로 대사 검사 + 오류 조건."""
    def setUp(self):
        import dashboard_data as D
        self.D = D
        self.tmp = Path(tempfile.mkdtemp())
        self.idx = self.tmp / "shushu-picks.json"
        rcpt = {"receipt_commit": "abc1234", "receipt_pushed_at": "2026-11-09T08:20:00+09:00"}
        self.idx.write_text(json.dumps([
            {"pick_id": "2026-11-09-shushu-s1-KR", "team": "shushu", "round_date": "2026-11-09", **rcpt},
            {"pick_id": "2026-11-09-shushu-s1-US", "team": "shushu", "round_date": "2026-11-09", **rcpt},
            {"pick_id": "2026-11-09-sandbox-shushu-s1-KR", "team": "sandbox-shushu", "round_date": "2026-11-09", **rcpt},
            {"pick_id": "2026-11-12-shushu-s1-KR", "team": "shushu", "round_date": "2026-11-12"}]))     # 접수 영수증 없음
        self.after = datetime.fromisoformat("2026-11-09T09:00:00+09:00")

    def check(self, lines, name="2026-11-09-shushu.json", now=None):
        f = self.tmp / name; f.write_text(json.dumps(lines, ensure_ascii=False))
        return self.D.check_lines(f, L.ROOT / "league", now or self.after, index=self.idx)

    def test_pass(self):
        self.assertEqual(self.check({"2026-11-09-shushu-s1-KR": "튼튼한 회사야.", "2026-11-09-shushu-s1-US": "꾸준히 크는 중."}), [])

    def test_error_conditions(self):
        e = self.check({"2026-11-09-shushu-s1-KR": "괜찮아."})
        self.assertTrue(any("한 줄 이유가 없는 종목" in x for x in e))                              # 빠진 종목
        e = self.check({"2026-11-09-claude-buffett-KR": "남의 종목", "2026-11-09-shushu-s1-KR": "a", "2026-11-09-shushu-s1-US": "b"})
        self.assertTrue(any("이 라운드·이 팀의 종목이 아님" in x for x in e))                       # 다른 팀 pick_id
        e = self.check({"2026-11-09-shushu-s1-KR": "종가 7만원 돌파", "2026-11-09-shushu-s1-US": "b"})
        self.assertTrue(any("가격처럼" in x for x in e))                                          # 가격 표현
        e = self.check({"2026-11-09-shushu-s1-KR": "a", "2026-11-09-shushu-s1-US": "b"}, now=datetime.fromisoformat("2026-11-09T08:00:00+09:00"))
        self.assertTrue(any("마감" in x for x in e))                                              # 마감 전
        e = self.check({"2026-11-10-shushu-s1-KR": "a"}, name="2026-11-10-shushu.json")
        self.assertTrue(any("종목이 없음" in x for x in e))                                        # 목록에 그 라운드 없음
        self.idx.write_text("{깨진 JSON")
        self.assertTrue(any("목록을 읽지 못함" in x for x in self.check({"x": "y"})))               # 목록 파일 오류

    def test_unreceipted_picks_fail(self):
        """슈슈 시험 ②: accepted 영수증이 없는 종목은 목록에 있어도 대사 검사를 통과하지 못한다."""
        e = self.check({"2026-11-12-shushu-s1-KR": "아무 말"}, name="2026-11-12-shushu.json",
                       now=datetime.fromisoformat("2026-11-12T09:00:00+09:00"))
        self.assertTrue(any("종목이 없음" in x for x in e)); self.assertTrue(any("이 라운드·이 팀의 종목이 아님" in x for x in e))

    def test_index_from_ledger_has_no_prices_or_other_team(self):
        t = MarketLeagues(); d = t._league(); t._fill(d)
        self.assertEqual(self.D.picks_index(d), [])                                    # 영수증 없이 원장에만 있는 종목은 제외
        for rd in ("2026-11-09", "2026-11-10"):
            L.append(d, "submissions", {"team": "shushu", "round_date": rd, "status": "accepted", "commit": "c" * 40,
                                        "pushed_at": f"{rd}T08:20:00+09:00", "path": f"league/imports/shushu/{rd}.csv"})
        rows = self.D.picks_index(d)
        self.assertEqual({r["round_date"] for r in rows}, {"2026-11-09", "2026-11-10"})
        self.assertTrue(rows); self.assertEqual({r["team"] for r in rows}, {"shushu"})
        self.assertNotRegex(json.dumps(rows), r'"(rationale|close|base_close|ticker|name)"')


class AgentsV2(unittest.TestCase):
    def test_current_guidelines_match_roster_version(self):
        """현재 지침 파일 = 명단 버전의 보관본(다음 버전이 와도 그대로 유효)."""
        r = {a["id"]: a for a in json.loads((ROOT / "league/agents/roster.json").read_text())["claude"]}
        for aid in ("buffett", "lynch", "dalio", "wood", "burry"):
            cur, arch = L.guideline_paths(aid, int(r[aid]["version"]))
            self.assertEqual(cur.read_text(), arch.read_text(), aid)

    def test_v2_guideline_content_and_rounds(self):
        r = {a["id"]: a for a in json.loads((ROOT / "league/agents/roster.json").read_text())["claude"]}
        for aid in ("buffett", "lynch", "dalio", "wood", "burry"):
            txt = L.guideline_paths(aid, 2)[1].read_text()
            self.assertIn("평가 세션 종가 = 라운드 당일 종가", txt); self.assertNotIn("내일 종가", txt)
            self.assertIn("0~1 소수", txt)
            self.assertEqual((L.version_for_round(r[aid], "2026-11-06"), L.version_for_round(r[aid], "2026-11-09")), (1, 2))

    def test_real_roster_accepts_v2_csv_on_first_round(self):
        """실제 명단: 11/9 CSV는 agent_version 2만 통과, 1은 거부."""
        d = Path(tempfile.mkdtemp()); (d / "ledger").mkdir(); (d / "agents").mkdir()
        for f in ("config.json", "universe.json"):
            shutil.copy(ROOT / "league" / f, d / f)
        shutil.copy(ROOT / "league/agents/roster.json", d / "agents/roster.json")
        cfg = L.load_config(d)
        mk = lambda v: L.make_pick("claude", "buffett", v, "2026-11-09", "KR", "005930", "005930", "2026-11-09T08:00:00+09:00", "근거", ["위험"], [{"url": "x", "as_of": "2026-11-06"}], cfg)
        self.assertEqual(L.validate_pick(mk(2), d, cfg, []), [])
        self.assertTrue(any("버전 불일치" in e for e in L.validate_pick(mk(1), d, cfg, [])))
class SimultaneousReveal(unittest.TestCase):
    """운영자 요청(2026-11-07): 지문을 낸 팀이 모두 원본 접수될 때까지(또는 12:00) 그 라운드 종목은 어느 팀 것도 공개하지 않는다."""
    def setUp(self):
        self.cfg = L.load_config(L.ROOT / "league")
        mk = lambda team, rd: {"pick_id": f"{rd}-{team}-a-KR", "team": team, "round_date": rd}
        self.picks = [mk("claude", "2026-11-10"), mk("shushu", "2026-11-10")]

    def shown(self, subs, at):
        return [p["team"] for p in L.embargo_picks(self.picks, self.cfg, datetime.fromisoformat(f"2026-11-10T{at}+09:00"), subs)[0]]

    def test_wait_for_other_team(self):
        rd = "2026-11-10"
        subs = [{"team": "claude", "round_date": rd, "status": "committed"}, {"team": "shushu", "round_date": rd, "status": "committed"},
                {"team": "claude", "round_date": rd, "status": "accepted"}]
        self.assertEqual(self.shown(subs, "08:40:00"), [])                                    # 슈슈 원본 대기 → 둘 다 숨김
        self.assertEqual(self.shown(subs + [{"team": "shushu", "round_date": rd, "status": "accepted"}], "08:41:00"), ["claude", "shushu"])
        self.assertEqual(self.shown(subs, "12:00:00"), ["claude", "shushu"])                  # 공개 마감이 되면 공개

    def test_team_without_commitment_does_not_block(self):
        rd = "2026-11-10"
        subs = [{"team": "claude", "round_date": rd, "status": "committed"}, {"team": "claude", "round_date": rd, "status": "accepted"},
                {"team": "shushu", "round_date": rd, "status": "late"}]
        self.assertEqual(self.shown(subs, "08:40:00"), ["claude", "shushu"])

    def test_before_deadline_still_hidden(self):
        rd = "2026-11-10"
        subs = [{"team": t, "round_date": rd, "status": st} for t in ("claude", "shushu") for st in ("committed", "accepted")]
        self.assertEqual(self.shown(subs, "08:29:00"), [])


class EveningRecheckFixes(unittest.TestCase):
    """슈슈 재검수(2026-11-07 evening-release-recheck) 2·3번 회귀 시험."""
    setUp = ShushuRepoSync.setUp
    spush, sync, csv, _sha_line = ShushuRepoSync.spush, ShushuRepoSync.sync, ShushuRepoSync.csv, ShushuRepoSync._sha_line
    set_wake_round = ShushuRepoSync.set_wake_round

    def _practice_accept(self):
        """연습 11/5(지문 방식 이전): 원본이 마감 뒤 반입돼 accepted."""
        rd = "2026-11-05"
        self.spush({f"practice/{rd}.csv": self.csv(rd)}, f"{rd}T08:00:00+09:00")
        self.sync(f"{rd}T08:31:00+09:00")
        subs = L.read_ledger(self.repo / "league" / "sandbox", "submissions")
        self.assertEqual([x["status"] for x in subs], ["accepted"])
        return rd

    def test_bundle_receipt_keeps_source_commit_and_judged_by(self):
        """export(public) → dashboard_data.build 전체 경로: 출처 커밋·판정 근거가 결과 묶음 영수증에 남는다."""
        import dashboard_data as D
        rd = "2026-11-10"
        self.spush({f"submit/{rd}.sha256": self._sha_line(rd), f"submit/{rd}.csv": self.csv(rd)}, f"{rd}T08:20:00+09:00")
        self.sync(f"{rd}T08:31:00+09:00")
        out = D.build(datetime.fromisoformat(f"{rd}T09:00:00+09:00"), base=self.repo / "league")
        rs = [r for r in out["receipts"] if r["round"] == rd]
        self.assertEqual({r["kind"] for r in rs}, {"commitment", "reveal"})
        for r in rs:
            self.assertEqual(r["source_commit"], self.acts[-1]["after"][:7])
            self.assertEqual(r["judged_by"], "shushu_repo.activity.timestamp")
        self.assertTrue([r for r in rs if r["kind"] == "reveal"][0]["sealed"])

    def test_failed_lines_not_imported_and_good_lines_kept(self):
        shutil.copytree(L.ROOT / "tools", self.repo / "tools")              # 동기화가 메인의 검사기를 부른다
        rd = self._practice_accept()
        good = {f"{rd}-sandbox-shushu-s1-KR": "튼튼해.", f"{rd}-sandbox-shushu-s1-US": "꾸준해."}
        self.spush({f"practice-lines/{rd}-sandbox-shushu.json": json.dumps(good, ensure_ascii=False)}, f"{rd}T09:00:00+09:00")
        self.sync(f"{rd}T09:05:00+09:00")
        dst = self.repo / "league/sandbox/lines" / f"{rd}-sandbox-shushu.json"
        self.assertEqual(json.loads(dst.read_text()), good)
        bad = dict(good); bad[f"{rd}-sandbox-claude-buffett-KR"] = "남의 종목"
        self.spush({f"practice-lines/{rd}-sandbox-shushu.json": json.dumps(bad, ensure_ascii=False)}, f"{rd}T09:10:00+09:00")
        out = self.sync(f"{rd}T09:15:00+09:00")
        self.assertIn("대사 검사 실패", out[0]["note"]); self.assertEqual(out[0]["lines"][0]["ok"], False)
        self.assertEqual(json.loads(dst.read_text()), good)                    # 실패 파일은 반입 안 됨, 기존 대사 유지

    def test_reveal_and_lines_in_same_push(self):
        """슈슈 재검수: 원본과 대사를 같은 push에 넣어도 원본을 먼저 접수한 뒤 대사를 검사해 반입한다."""
        shutil.copytree(L.ROOT / "tools", self.repo / "tools")
        cp = self.repo / "league/config.json"; c = json.loads(cp.read_text())
        c["commit_reveal"]["from"] = "2026-11-01"; cp.write_text(json.dumps(c, ensure_ascii=False))   # 지난 날짜로 지문 방식 시험
        (self.repo / "league/sandbox").mkdir(parents=True, exist_ok=True)
        (self.repo / "league/sandbox/config.json").write_text(json.dumps(c, ensure_ascii=False))            # 연습 원장 설정도 같게
        rd = "2026-11-05"
        self.spush({f"practice/{rd}.sha256": self._sha_line(rd)}, f"{rd}T08:10:00+09:00")
        lines = {f"{rd}-sandbox-shushu-s1-KR": "튼튼해.", f"{rd}-sandbox-shushu-s1-US": "꾸준해."}
        self.spush({f"practice/{rd}.csv": self.csv(rd), f"practice-lines/{rd}-sandbox-shushu.json": json.dumps(lines, ensure_ascii=False)},
                   f"{rd}T08:40:00+09:00")
        out = self.sync(f"{rd}T08:50:00+09:00")
        last = out[-1]
        self.assertEqual([x["status"] for x in last["receipts"]], ["accepted"])
        self.assertEqual(last["lines"], [{"path": f"league/sandbox/lines/{rd}-sandbox-shushu.json", "ok": True}])
        self.assertEqual(json.loads((self.repo / f"league/sandbox/lines/{rd}-sandbox-shushu.json").read_text()), lines)

    def test_loader_ignores_other_team_lines(self):
        import dashboard_data as D
        d = Path(tempfile.mkdtemp()); (d / "lines").mkdir()
        (d / "lines" / "2026-11-10-shushu.json").write_text(json.dumps({"2026-11-10-shushu-s1-KR": "내 대사", "2026-11-10-claude-buffett-KR": "남의 대사"}, ensure_ascii=False))
        self.assertEqual(D.load_lines(d), {"2026-11-10-shushu-s1-KR": "내 대사"})


class AddCharacter(unittest.TestCase):
    """대기 후보 자동 추가(운영자 상시 위임): 검사 → 명단·승인 원장·지침·캐릭터 그림 반영, 실패 시 반영 안 함."""
    def setUp(self):
        import add_character as AC
        self.AC = AC
        self.root = Path(tempfile.mkdtemp())
        for rel in ("league/config.json", "league/universe.json", "league/agents/roster.json", "league/imports/shushu/roster.json",
                    "docs/dashboard/operator-dashboard-page.html", "league/agents/avatars/README.md"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(L.ROOT / rel, self.root / rel)
        shutil.copytree(L.ROOT / "league/agents/avatars/src", self.root / "league/agents/avatars/src",
                        ignore=shutil.ignore_patterns("__pycache__", "extra.json", "defs.svg", "preview.html"))
        (self.root / "league/ledger").mkdir(parents=True)
        self.saved = (AC.ROOT, AC.SRC, AC.PAGE, AC.README)
        AC.ROOT, AC.SRC = self.root, self.root / "league/agents/avatars/src"
        AC.PAGE, AC.README = self.root / "docs/dashboard/operator-dashboard-page.html", self.root / "league/agents/avatars/README.md"

    def tearDown(self):
        self.AC.ROOT, self.AC.SRC, self.AC.PAGE, self.AC.README = self.saved

    def spec(self, **kw):
        sp = {"team": "shushu", "id": "s8", "nickname": "등대", "label": "배당성장형", "style_ref": "공개된 배당 성장 투자 원칙 참고",
              "tagline": "꾸준히 늘어나는 배당을 본다", "guideline": "# 등대 지침\n배당 성장.",
              "look": {"name": "deungdae", "skin": "tan", "hair": "short", "hairc": "#3a2a20", "hat": "cap", "hatc": "#1f6f8b",
                       "brows": "up", "nose": "button", "mouth": "grin", "glasses": "round", "outfit": "#2f6f4f", "collar": "shirt"}}
        sp.update(kw); return sp

    def test_add_ok(self):
        self.assertEqual(self.AC.apply(self.spec(), source="test"), [])
        sh = json.loads((self.root / "league/imports/shushu/roster.json").read_text())
        self.assertEqual(sh["bench"][-1]["id"], "s8")
        ap = L.read_ledger(self.root / "league", "approvals")
        self.assertEqual((ap[-1]["agent_id"], ap[-1]["decision"]), ("s8", "approved")); self.assertIn("상시 위임", ap[-1]["approved_by"])
        self.assertIn('id="av-deungdae"', (self.root / "docs/dashboard/operator-dashboard-page.html").read_text())
        self.assertTrue((self.root / "league/imports/shushu/agents/s8/v1.md").exists())
        self.assertEqual(L.verify(self.root / "league"), [])

    def test_rejects_bad_specs(self):
        bad = [self.spec(id="s1"), self.spec(label="안전마진형"), self.spec(style_ref="그레이엄처럼"),
               self.spec(tagline="005930만 산다"), self.spec(look={**self.spec()["look"], "name": "dandan"}),
               self.spec(look={**self.spec()["look"], "hat": "crown"})]
        for sp in bad:
            self.assertTrue(self.AC.apply(sp, source="t"), sp)
        self.assertEqual(json.loads((self.root / "league/imports/shushu/roster.json").read_text())["bench"][-1]["id"], "s7")

    def test_message_parse(self):
        sp = self.spec(); g = sp.pop("guideline")
        md = "제안\n```json\n" + json.dumps(sp, ensure_ascii=False) + "\n```\n## 지침\n" + g + "\n"
        out = self.AC.spec_from_message(md)
        self.assertEqual((out["id"], out["guideline"].splitlines()[0]), ("s8", "# 등대 지침"))


class BoundaryCases(unittest.TestCase):
    """슈슈 팀 확인 질문(v2.0·v2.1)의 경계 사례."""

    def test_first_v1_and_bench_first_join_not_cooldown(self):
        """시즌 최초 v1, 처음 합류한 대기 후보의 v1은 냉각이 아니다."""
        t = MarketLeagues(); d = t._league(); t._fill(d)
        L.weekly_close(d, "2026-W46")
        cfg = L.load_config(d)
        for rd in ("2026-11-16", "2026-11-17"):
            L.append(d, "picks", L.make_pick("claude", "momentum", 1, rd, "KR", "005930", "005930", f"{rd}T08:00:00+09:00", "", [], [{"url": "x", "as_of": rd}], cfg))
        plan = {(r["team"], r["agent_id"]): r for r in L.update_plan(d, "2026-W47")["agents"]}
        self.assertNotEqual(plan[("claude", "momentum")]["status"], "cooldown")
        plan46 = {(r["team"], r["agent_id"]): r for r in L.update_plan(d, "2026-W46")["agents"]}
        self.assertFalse(any(r["status"] == "cooldown" for r in plan46.values()))

    def test_remaining_league_csv_version_must_match(self):
        """한 리그에서만 빠진 에이전트도 남은 리그 CSV 버전은 명단 버전과 같아야 한다."""
        t = MarketLeagues(); d = t._league(); t._fill(d)
        L.weekly_close(d, "2026-W46")                                  # burry 한국 리그 탈락, 미국은 계속
        cfg = L.load_config(d)
        mk = lambda v: L.make_pick("claude", "burry", v, "2026-11-16", "US", "AAPL", "AAPL", "2026-11-16T08:00:00+09:00", "", ["r"], [{"url": "x", "as_of": "2026-11-13"}], cfg)
        self.assertEqual(L.validate_pick(mk(1), d, cfg, []), [])
        self.assertTrue(any("버전 불일치" in e for e in L.validate_pick(mk(2), d, cfg, [])))

    def test_approval_after_0705_applies_next_round(self):
        """07:05 이후 승인(from_round = 다음 라운드)이면 그날 라운드는 이전 버전으로 접수, 다음 라운드부터 새 버전."""
        m = {"id": "lynch", "version": 2, "versions": [{"version": 2, "from_round": "2026-11-17"}]}
        self.assertEqual(L.version_for_round(m, "2026-11-16"), 1)
        self.assertEqual(L.version_for_round(m, "2026-11-17"), 2)
        self.assertEqual(L.version_for_round({"id": "x", "version": 3}, "2026-11-16"), 3)
        m3 = {"id": "x", "version": 3, "versions": [{"version": 2, "from_round": "2026-11-16"}, {"version": 3, "from_round": "2026-11-23"}]}
        self.assertEqual([L.version_for_round(m3, r) for r in ("2026-11-13", "2026-11-16", "2026-11-23")], [1, 2, 3])
        t = MarketLeagues(); d = t._league(); t._fill(d)
        ro = json.loads((d / "agents" / "roster.json").read_text())
        for a in ro["claude"]:
            if a["id"] == "lynch":
                a.update(version=2, versions=[{"version": 2, "from_round": "2026-11-13"}])
        (d / "agents").mkdir(parents=True, exist_ok=True); (d / "agents" / "roster.json").write_text(json.dumps(ro, ensure_ascii=False))
        cfg = L.load_config(d)
        mk = lambda rd, v: L.make_pick("claude", "lynch", v, rd, "US", "AAPL", "AAPL", f"{rd}T08:00:00+09:00", "", ["r"], [{"url": "x", "as_of": rd}], cfg)
        self.assertEqual(L.validate_pick(mk("2026-11-12", 1), d, cfg, []), [])
        self.assertTrue(any("버전 불일치" in e for e in L.validate_pick(mk("2026-11-12", 2), d, cfg, [])))
        self.assertEqual(L.validate_pick(mk("2026-11-13", 2), d, cfg, []), [])


class Watch(unittest.TestCase):
    """규칙 v1.9 관망 카드: 비교 지수 수익률이 점수, 초과 0, 주 2회, 11/16부터."""
    def test_watch_scores_benchmark_and_limits(self):
        d = new_league()
        # 11/16(월) 라운드: KR 기준 11/13 → 평가 11/16
        price(d, "KR", "KOSPI", "2026-11-13", 2000.0); price(d, "KR", "KOSPI", "2026-11-16", 1960.0)
        p = pick(d, "buffett", "2026-11-16", "KR", "WATCH")
        w = L.evaluate_pick(p, L.price_index(d), L.load_config(d), date(2026, 11, 17), L.corporate_actions(d))
        self.assertEqual((w["status"], w["score"], w["benchmark_return"], w["score_excess"]), ("final", -2.0, -2.0, 0.0))
        # 지수만 있으면 되므로 배당·분할 확인이 없어도 보류되지 않는다
        self.assertIsNone(w["reason"])
        with self.assertRaisesRegex(ValueError, "KR 관망은 주 1회"):
            pick(d, "buffett", "2026-11-17", "KR", "WATCH")                 # v2.0: 같은 리그 같은 주 2회째 거부
        pick(d, "buffett", "2026-11-18", "US", "WATCH")                     # 다른 리그는 따로 1회
        pick(d, "buffett", "2026-11-23", "KR", "WATCH")                     # 다음 주는 다시 가능
        pick(d, "lynch", "2026-11-17", "KR", "WATCH")                       # 다른 에이전트는 따로 셈

    def test_watch_combined_cap_when_configured(self):
        d = use_mode(new_league(), "per_market_bottom1", max_per_week_per_market=None)
        c = json.loads((d / "config.json").read_text()); c["watch"].pop("max_per_week_per_market"); (d / "config.json").write_text(json.dumps(c))
        pick(d, "buffett", "2026-11-16", "KR", "WATCH"); pick(d, "buffett", "2026-11-17", "KR", "WATCH")
        with self.assertRaisesRegex(ValueError, "주 2회"):
            pick(d, "buffett", "2026-11-18", "US", "WATCH")

    def test_watch_not_before_start_and_needs_reason(self):
        d = new_league()
        with self.assertRaisesRegex(ValueError, "부터 낼 수 있음"):
            pick(d, "buffett", "2026-11-13", "KR", "WATCH")
        cfg = L.load_config(d)
        rec = L.make_pick("claude", "buffett", 1, "2026-11-16", "KR", "WATCH", "관망", "2026-11-16T08:00:00+09:00",
                          " ", [], [], cfg)
        self.assertTrue(any("근거" in e for e in L.validate_pick(rec, d, cfg, [])))

    def test_watch_csv_without_sources_and_due_sessions(self):
        import collectors as C
        d = new_league()
        f = d / "w.csv"
        L.make_csv([{"agent_id": "buffett", "agent_version": 1, "market": "KR", "ticker": "watch", "name": "",
                     "locked_at": "2026-11-16T08:00:00+09:00", "rationale": "지수 급락 뒤라 하루 방향이 불확실해 관망",
                     "risks": [], "sources": []},
                    {"agent_id": "buffett", "agent_version": 1, "market": "US", "ticker": "AAPL", "name": "Apple",
                     "locked_at": "2026-11-16T08:00:00+09:00", "rationale": "근거", "risks": ["위험"],
                     "sources": [{"url": "https://example.com", "as_of": "2026-11-13"}]}], "2026-11-16", f)
        ok, bad = L.import_csv(d, f, "claude")
        self.assertEqual(bad, []); w = [x for x in ok if x["market"] == "KR"][0]; self.assertEqual((w["ticker"], w["name"]), ("WATCH", "관망"))
        due = C.due_sessions(d, date(2026, 11, 17))
        self.assertEqual(due[("KR", "2026-11-13")], ["KOSPI"])               # WATCH가 아니라 지수만 받는다


class MarketLeagues(unittest.TestCase):
    """규칙 v2.0: 한국·미국 리그를 따로 세워 리그마다 꼴등 1명을 그 시장에서만 뺀다."""
    CLAUDE = ["buffett", "lynch", "dalio", "wood", "burry"]
    SHUSHU = ["s1", "s2", "s3", "s4", "s5"]

    def _league(self):
        d = new_league()
        shutil.copytree(ROOT / "league" / "imports" / "shushu", d / "imports" / "shushu",
                        ignore=shutil.ignore_patterns("*.csv", "*.sha256", "*.md"))
        for t, a in (("claude", "momentum"), ("claude", "quant"), ("shushu", "s6")):
            L.append(d, "approvals", {"type": "bench", "team": t, "agent_id": a, "decision": "approved"})
        return use_mode(d, "per_market_bottom1")

    def _scores(self, d, team, kr: dict, us: dict, week_days=("2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13")):
        cfg = L.load_config(d)
        for m, res in (("KR", kr), ("US", us)):
            for agent, scores in res.items():
                for rd, sc in zip(week_days, scores):
                    t = "005930" if m == "KR" else "AAPL"
                    rec = L.make_pick(team, agent, 1, rd, m, t, t, f"{rd}T08:00:00+09:00", "", [], [{"url": "x", "as_of": rd}], cfg)
                    L.append(d, "picks", rec)
                    if sc is not None:
                        L.append(d, "scores", {"pick_id": rec["pick_id"], "status": "final", "score": sc})

    def _fill(self, d, kr_bottom=("claude", "burry"), us_bottom=("shushu", "s1")):
        for team, ids in (("claude", self.CLAUDE), ("shushu", self.SHUSHU)):
            kr = {a: [-5.0 if (team, a) == kr_bottom else 1.0 + i] * 5 for i, a in enumerate(ids)}
            us = {a: [-5.0 if (team, a) == us_bottom else 1.0 + i] * 5 for i, a in enumerate(ids)}
            self._scores(d, team, kr, us)

    def test_each_league_eliminates_its_own_bottom(self):
        d = self._league(); self._fill(d)
        kr, us = L.weekly_market_league(d, "2026-W46", "KR"), L.weekly_market_league(d, "2026-W46", "US")
        self.assertEqual(len(kr["ranking"]), 10)
        self.assertEqual((kr["decision"]["eliminate_team"], kr["decision"]["eliminate"], kr["decision"]["replacement"]), ("claude", "burry", "momentum"))
        self.assertEqual((us["decision"]["eliminate_team"], us["decision"]["eliminate"], us["decision"]["replacement"]), ("shushu", "s1", "s6"))
        w = L.weekly(d, "2026-W46", "claude")["decision"]
        self.assertEqual((w["markets"]["KR"]["eliminate"], w["markets"]["US"]["eliminate"]), ("burry", None))

    def test_dashboard_league_rows_and_team_total(self):
        """현황판: 주간 순위는 리그별(market KR/US) 줄, 팀 대결에는 두 시장 합친 통합(ALL) 줄."""
        import dashboard_data as D
        d = self._league(); self._fill(d)
        out = D.build(datetime.fromisoformat("2026-11-15T12:00:00+09:00"), base=d)
        st = [r for r in out["standings"] if r["week"] == "2026-W46"]
        self.assertEqual({r["market"] for r in st}, {"KR", "US"})
        self.assertEqual(sorted(r["league_rank"] for r in st if r["market"] == "KR"), list(range(1, 11)))
        tw = {(r["market"], r["team"]): r for r in out["team_weeks"] if r["week"] == "2026-W46"}
        for team in {r["team"] for r in tw.values()}:
            kr, us, al = tw[("KR", team)], tw[("US", team)], tw[("ALL", team)]
            self.assertEqual(al["scored"], kr["scored"] + us["scored"])

    def test_team_average_uses_raw_scores_not_rounded(self):
        """검수: 시장별 반올림 평균을 다시 평균하면 팀 승패가 뒤집힐 수 있다 → 원점수 합으로 계산."""
        import dashboard_data as D
        d = self._league()
        # 시장별로 먼저 반올림하면 로로 0.00 < 슈슈 0.01, 원점수로는 둘 다 0.01 (2차 검수: 반올림 순서로 결과가 갈리는 값)
        self._scores(d, "claude", {a: [0.004, 0.004, 0.004, 0.004, None] for a in self.CLAUDE},
                     {a: [0.016, None, None, None, None] for a in self.CLAUDE})
        self._scores(d, "shushu", {a: [0.009] * 5 for a in self.SHUSHU}, {a: [0.009] * 5 for a in self.SHUSHU})
        sc = {s["pick_id"]: s["score"] for s in L.read_ledger(d, "scores")}
        out = D.build(datetime.fromisoformat("2026-11-15T12:00:00+09:00"), base=d)
        al = {r["team"]: r for r in out["team_weeks"] if r["market"] == "ALL"}
        for team in ("claude", "shushu"):
            raw = [v for k, v in sc.items() if f"-{team}-" in k]
            self.assertEqual(al[D.label(team)]["avg"], round(sum(raw) / len(raw), 2))
        self.assertEqual((al[D.label("claude")]["avg"], al[D.label("shushu")]["avg"]), (0.01, 0.01))
        us = L.weekly_market_league(d, "2026-W46", "US")["teams"]
        self.assertEqual(us["claude"]["avg"], round(0.016, 2))

    def test_close_updates_only_that_market(self):
        d = self._league(); self._fill(d)
        recs = L.weekly_close(d, "2026-W46", now="2026-11-16T06:30:00+09:00")
        self.assertEqual(sorted((r["market"], r["team"], r["eliminate"]) for r in recs),
                         [("KR", "claude", "burry"), ("KR", "shushu", None), ("US", "claude", None), ("US", "shushu", "s1")])
        self.assertEqual(L.weekly_close(d, "2026-W46"), [])                              # 다시 마감해도 중복 없음
        ro = L.load_roster(d)
        burry = next(a for a in ro["claude"] if a["id"] == "burry")
        self.assertEqual((L.mstatus(burry, "KR")["status"], L.mstatus(burry, "US")["status"], burry["status"]), ("eliminated", "active", "active"))
        mom = next(a for a in ro["claude"] if a["id"] == "momentum")
        self.assertEqual((L.mstatus(mom, "KR")["status"], L.mstatus(mom, "KR")["joined_week"], L.mstatus(mom, "US")["status"]), ("active", "2026-W47", "bench"))
        # W47 제출: burry는 미국만, momentum은 한국만
        cfg = L.load_config(d)
        mk = lambda a, m, t: L.make_pick("claude", a, 1, "2026-11-16", m, t, t, "2026-11-16T08:00:00+09:00", "근거", ["위험"], [{"url": "x", "as_of": "2026-11-13"}], cfg)
        self.assertTrue(any("한국 리그에서 탈락" in e for e in L.validate_pick(mk("burry", "KR", "005930"), d, cfg, [])))
        self.assertEqual(L.validate_pick(mk("burry", "US", "AAPL"), d, cfg, []), [])
        self.assertTrue(any("미국 리그 참가 전" in e for e in L.validate_pick(mk("momentum", "US", "AAPL"), d, cfg, [])))
        self.assertEqual(L.validate_pick(mk("momentum", "KR", "005930"), d, cfg, []), [])
        # CSV 필수 시장: burry는 미국만 내도 누락 아님
        f = d / "w47.csv"
        L.make_csv([{"agent_id": "burry", "agent_version": 1, "market": "US", "ticker": "AAPL", "name": "Apple", "locked_at": "2026-11-16T08:00:00+09:00",
                     "rationale": "근거", "risks": ["위험"], "sources": [{"url": "https://e.com", "as_of": "2026-11-13"}]}], "2026-11-16", f)
        ok, bad = L.import_csv(d, f, "claude", dry_run=True)
        self.assertEqual(bad, [])
        # 검수 지적(치명): W47 라운드 전체 CSV — burry(미국만)+momentum(한국만)+나머지 4명(두 시장) = 서로 다른 6명이어도 시장별 5명이라 통과
        rows = []
        for a in ("buffett", "lynch", "dalio", "wood"):
            for m, t in (("KR", "005930"), ("US", "AAPL")):
                rows.append({"agent_id": a, "agent_version": 1, "market": m, "ticker": t, "name": t, "locked_at": "2026-11-16T08:00:00+09:00",
                             "rationale": "근거", "risks": ["위험"], "sources": [{"url": "https://e.com", "as_of": "2026-11-13"}]})
        rows.append({**rows[1], "agent_id": "burry"}); rows.append({**rows[0], "agent_id": "momentum"})
        f2 = d / "w47-full.csv"; L.make_csv(rows, "2026-11-16", f2)
        ok, bad = L.import_csv(d, f2, "claude")
        self.assertEqual((len(ok), bad), (10, []))
        # 다음 주 순위: 한국 리그에는 momentum, burry 없음 / 미국 리그에는 burry
        rows47 = {r["agent_id"]: r for r in L.weekly(d, "2026-W47", "claude", _rows_only=True)["ranking"]}
        self.assertFalse(rows47["burry"]["markets"]["KR"]["active"]); self.assertTrue(rows47["burry"]["markets"]["US"]["active"])
        self.assertTrue(rows47["momentum"]["markets"]["KR"]["active"]); self.assertFalse(rows47["momentum"]["markets"]["US"]["active"])
        self.assertEqual(rows47["momentum"]["expected"], 5)

    def test_same_bench_can_fill_other_market_later_and_full_elimination(self):
        d = self._league(); self._fill(d)
        L.weekly_close(d, "2026-W46", now="2026-11-16T06:30:00+09:00")
        # W47: 미국 리그 꼴등이 burry → claude 미국 빈자리에는 아직 미국에 없는 momentum(한국에서 뛰는 중)이 우선
        days47 = ("2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20")
        kr = {a: [1.0 + i] * 5 for i, a in enumerate(["buffett", "lynch", "dalio", "wood", "momentum"])}
        us = {a: [-5.0 if a == "burry" else 1.0 + i] * 5 for i, a in enumerate(self.CLAUDE)}
        self._scores(d, "claude", kr, us, days47)
        self._scores(d, "shushu", {a: [2.0 + i] * 5 for i, a in enumerate(self.SHUSHU)},
                     {a: [2.0 + i] * 5 for i, a in enumerate(["s2", "s3", "s4", "s5", "s6"])}, days47)
        us_dec = L.weekly_market_league(d, "2026-W47", "US")["decision"]
        self.assertEqual((us_dec["eliminate"], us_dec["replacement"]), ("burry", "momentum"))
        L.weekly_close(d, "2026-W47", now="2026-11-23T06:30:00+09:00")
        ro = L.load_roster(d)
        burry = next(a for a in ro["claude"] if a["id"] == "burry")
        self.assertEqual((burry["status"], burry["eliminated_week"]), ("eliminated", "2026-W47"))   # 두 리그 모두 탈락 → 완전 탈락
        # 검수 지적(중간): 다른 주에 나뉘어 두 리그에서 빠져도 업데이트 계획은 out
        plan = {(r["team"], r["agent_id"]): r for r in L.update_plan(d, "2026-W47")["agents"]}
        self.assertEqual(plan[("claude", "burry")]["status"], "out")
        mom = next(a for a in ro["claude"] if a["id"] == "momentum")
        self.assertEqual((L.mstatus(mom, "KR")["status"], L.mstatus(mom, "US")["status"], L.mstatus(mom, "US")["joined_week"]), ("active", "active", "2026-W48"))

    def test_hold_is_per_league(self):
        d = self._league()
        for team, ids in (("claude", self.CLAUDE), ("shushu", self.SHUSHU)):
            kr = {a: [-5.0 if (team, a) == ("claude", "burry") else 1.0 + i] * 5 for i, a in enumerate(ids)}
            us = {a: ([1.0 + i] * 2 + [None] * 3) for i, a in enumerate(ids)}            # 미국 확정 10/25 < 15
            self._scores(d, team, kr, us)
        self.assertEqual(L.weekly_market_league(d, "2026-W46", "KR")["decision"]["eliminate"], "burry")
        us = L.weekly_market_league(d, "2026-W46", "US")["decision"]
        self.assertIsNone(us["eliminate"])
        self.assertTrue(any("미국 리그" in r and "10건 < 15건" in r for r in us["hold_reasons"]))


class UpdatePlan(unittest.TestCase):
    """규칙 v2.1: 어느 리그 1등은 동결, 2~9등은 근거가 있을 때만 작게, 새 버전으로 뛴 주는 쉼, 두 리그 탈락은 없음."""
    def test_plan(self):
        t = MarketLeagues(); d = t._league(); t._fill(d, kr_bottom=("claude", "wood"))   # 한국 꼴등 wood, 미국 꼴등 s1
        plan = {(r["team"], r["agent_id"]): r for r in L.update_plan(d, "2026-W46")["agents"]}
        # 한국 1등 s5(5.0) 단독, 미국 1등 burry·s5 공동(5.0) → 공동 1등도 동결
        self.assertEqual(plan[("shushu", "s5")]["status"], "frozen")
        self.assertEqual(plan[("claude", "burry")]["status"], "frozen")
        self.assertEqual(plan[("claude", "wood")]["status"], "eligible")               # 한국만 빠짐 → 미국에서 계속, 업데이트 가능
        self.assertIn("한국 리그에서는 교체됨", plan[("claude", "wood")]["reason"])
        self.assertEqual(plan[("claude", "lynch")]["status"], "eligible")
        self.assertEqual(sorted(k for k, r in plan.items() if r["status"] == "frozen"), [("claude", "burry"), ("shushu", "s5")])

    def test_cooldown_after_new_version(self):
        t = MarketLeagues(); d = t._league(); t._fill(d)
        cfg = L.load_config(d)
        rec = L.make_pick("claude", "lynch", 2, "2026-11-12", "US", "AAPL", "AAPL", "2026-11-12T08:00:00+09:00", "", [], [{"url": "x", "as_of": "2026-11-11"}], cfg)
        rec["pick_id"] += "-v2"; L.append(d, "picks", rec)                              # 이번 주 중간부터 v2로 뜀
        plan = {(r["team"], r["agent_id"]): r for r in L.update_plan(d, "2026-W46")["agents"]}
        self.assertEqual((plan[("claude", "lynch")]["status"], plan[("claude", "lynch")]["version"]), ("cooldown", 2))
