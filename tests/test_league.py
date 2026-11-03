"""AI 투자 리그 규칙 테스트.  실행: python3 -m unittest discover -s tests -v"""
import json, shutil, sys, tempfile, unittest
from datetime import date
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
    L.append(d, "prices", {"market": m, "ticker": t, "session": s, "close": close, "split_factor": 1.0,
                           "cash_dividend_exdate": 0.0, "halted": False, "status": "final", **kw})


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

    def test_dividend_modes(self):
        self.assertEqual(L.compute_score(100, 99, dividend=1, dividend_mode="include"), 0.0)
        self.assertEqual(L.compute_score(100, 99, dividend=1, dividend_mode="exclude"), -1.0)


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

    def test_one_pick_per_agent_per_round(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        with self.assertRaisesRegex(ValueError, "이미"):
            pick(d, "buffett", "2026-11-10", "US", "AAPL")

    def test_same_stock_allowed_for_different_agents(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        pick(d, "lynch", "2026-11-10", "KR", "005930")
        self.assertEqual(len(L.read_ledger(d, "picks")), 2)


class Scoring(unittest.TestCase):
    def test_pending_then_final(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 102300)
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 10)), [])          # 아직 평가일 장중
        w = L.run_scoring(d, today=date(2026, 11, 11))
        self.assertEqual((w[0]["status"], w[0]["score"]), ("final", 2.3))
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 12)), [])          # 변화 없으면 기록 안 함

    def test_missing_price_is_held_not_zero(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        w = L.run_scoring(d, today=date(2026, 11, 11))
        self.assertEqual(w[0]["status"], "held")
        self.assertIsNone(w[0]["score"])

    def test_provisional_until_price_final(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 101000, status="provisional")
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 11))[0]["status"], "provisional")
        price(d, "KR", "005930", "2026-11-10", 101000)          # 다음 날 공식 확정
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 12))[0]["status"], "final")

    def test_correction_after_final_is_appended(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
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
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", None, halted=True)
        self.assertEqual(L.run_scoring(d, today=date(2026, 11, 11))[0]["status"], "held")
        price(d, "KR", "005930", "2026-11-11", 97000)
        w = L.run_scoring(d, today=date(2026, 11, 12))[0]
        self.assertEqual((w["status"], w["score"], w["delayed"]), ("final", -3.0, True))

    def test_long_halt_void(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        cfg = L.load_config(d)
        s = date(2026, 11, 10)
        for _ in range(7):
            price(d, "KR", "005930", s.isoformat(), None, halted=True)
            s = L.next_session("KR", s, cfg)
        w = L.run_scoring(d, today=date(2026, 11, 25))[0]
        self.assertEqual(w["status"], "void")


class Weekly(unittest.TestCase):
    def _week(self, d, results, team="claude"):
        """results: {agent: [점수...]} → W46 월~금 라운드로 기록"""
        days = ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
        cfg = L.load_config(d)
        for agent, scores in results.items():
            for rd, sc in zip(days, scores):
                rec = L.make_pick(team, agent, 1, rd, "KR", "005930", "삼성전자", f"{rd}T08:00:00+09:00",
                                  "", [], [{"url": "x", "as_of": rd}], cfg)
                L.append(d, "picks", rec)
                if sc is not None:
                    L.append(d, "scores", {"pick_id": rec["pick_id"], "status": "final", "score": sc})
        return L.weekly(d, "2026-W46", team)

    def test_bottom_eliminated(self):
        d = new_league()
        w = self._week(d, {"buffett": [1, 1, 1], "lynch": [2, 2, 2], "dalio": [0, 0, 0],
                           "wood": [1, 0, 1], "burry": [-1, -1, -1]})
        self.assertEqual(w["decision"]["eliminate"], "burry")
        self.assertEqual(w["decision"]["replacement"], "momentum")

    def test_hold_when_bottom_has_too_few_scores(self):
        d = new_league()
        w = self._week(d, {"buffett": [1, 1, 1], "lynch": [2, 2, 2], "dalio": [0, 0, 0],
                           "wood": [1, 0, 1], "burry": [-1, -1, None, None, None]})
        self.assertIsNone(w["decision"]["eliminate"])
        self.assertTrue(any("2건" in r for r in w["decision"]["hold_reasons"]))

    def test_tiebreak_by_median(self):
        d = new_league()
        # dalio, burry 평균 0 동점 → 중앙값: dalio 0, burry -1 → burry 탈락
        w = self._week(d, {"buffett": [1, 1, 1], "lynch": [2, 2, 2], "dalio": [0, 0, 0],
                           "wood": [1, 1, 1], "burry": [2, -1, -1]})
        self.assertEqual(w["decision"]["eliminate"], "burry")

    def test_full_tie_holds(self):
        d = new_league()
        w = self._week(d, {"buffett": [1, 1, 1], "lynch": [2, 2, 2], "dalio": [0, 0, 0],
                           "wood": [1, 1, 1], "burry": [0, 0, 0]})
        self.assertIsNone(w["decision"]["eliminate"])
        self.assertTrue(any("동점" in r for r in w["decision"]["hold_reasons"]))


class CsvImport(unittest.TestCase):
    def test_import_all_or_nothing(self):
        d = new_league()
        f = d / "in.csv"
        f.write_text("round_date,agent_id,market,ticker,name,locked_at,rationale,risks,sources\n"
                     "2026-11-10,s1,US,AAPL,Apple,2026-11-10T08:10:00+09:00,근거,위험1|위험2,https://x|2026-11-09\n"
                     "2026-11-10,s2,KR,005930,삼성전자,2026-11-10T08:45:00+09:00,근거,위험,https://x|2026-11-09\n")
        ok, bad = L.import_csv(d, f, "shushu")
        self.assertEqual((len(ok), len(bad)), (1, 1))
        self.assertIn("마감", bad[0]["errors"][0])
        self.assertEqual(L.read_ledger(d, "picks"), [])         # 오류가 하나라도 있으면 아무것도 기록 안 함

    def test_import_ok(self):
        d = new_league()
        f = d / "in.csv"
        f.write_text("round_date,agent_id,market,ticker,name,locked_at,rationale,risks,sources\n"
                     "2026-11-10,s1,US,AAPL,Apple,2026-11-10T08:10:00+09:00,근거,위험,https://x|2026-11-09\n")
        ok, bad = L.import_csv(d, f, "shushu")
        self.assertEqual(bad, [])
        p = L.read_ledger(d, "picks")[0]
        self.assertEqual((p["team"], p["base_session"], p["eval_session"]), ("shushu", "2026-11-09", "2026-11-10"))


if __name__ == "__main__":
    unittest.main()
