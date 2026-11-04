"""수집기·공유판·공통 자료 테스트.  실행: python3 -m unittest discover -s tests -v"""
import json, re, shutil, sys, tempfile, unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import league as L  # noqa: E402
import collectors as C  # noqa: E402
from test_league import new_league, pick, price, checked  # noqa: E402


def mock(market, rows):
    return C.MockProvider({market: rows})


class Collect(unittest.TestCase):
    def test_wrong_trade_date_is_failure_not_recorded(self):
        d = new_league()
        r = C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-09", "close": 200.0}]),
                      "US", ["AAPL"], date(2026, 11, 10), "provisional")
        self.assertEqual(r["recorded"], [])
        self.assertIn("응답 거래일 2026-11-09", r["failed"][0]["reason"])
        self.assertEqual(L.read_ledger(d, "prices"), [])

    def test_missing_ticker_and_bad_close_fail(self):
        d = new_league()
        r = C.collect(d, mock("KR", [{"ticker": "005930", "session": "2026-11-10", "close": 0}]),
                      "KR", ["005930", "000660"], date(2026, 11, 10), "provisional")
        self.assertEqual(sorted(f["ticker"] for f in r["failed"]), ["000660", "005930"])

    def test_provisional_not_written_after_final(self):
        d = new_league()
        C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-10", "close": 201.0}]), "US", ["AAPL"], date(2026, 11, 10), "final")
        r = C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-10", "close": 200.5}]), "US", ["AAPL"], date(2026, 11, 10), "provisional")
        self.assertEqual(r["skipped"][0]["reason"], "이미 확정 값 있음")
        self.assertEqual(L.price_index(d)[("US", "AAPL", "2026-11-10")]["close"], 201.0)

    def test_final_differs_from_provisional_records_discrepancy(self):
        d = new_league()
        C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-10", "close": 200.0}]), "US", ["AAPL"], date(2026, 11, 10), "provisional")
        r = C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-10", "close": 201.0}]), "US", ["AAPL"], date(2026, 11, 10), "final")
        self.assertEqual(r["discrepancies"][0]["diff_pct"], 0.5)
        self.assertEqual(L.read_ledger(d, "price_checks")[0]["previous_status"], "provisional")
        self.assertEqual(L.price_index(d)[("US", "AAPL", "2026-11-10")]["status"], "final")
        self.assertEqual(L.verify(d), [])

    def test_final_collection_writes_corporate_actions_and_check(self):
        d = new_league()
        C.collect(d, mock("US", [{"ticker": "KO", "session": "2026-11-10", "close": 70.0,
                                  "dividends": [{"ex_date": "2026-11-10", "amount": 0.51, "currency": "USD"}]}]),
                  "US", ["KO"], date(2026, 11, 10), "final")
        types = [c["type"] for c in L.read_ledger(d, "corporate_actions")]
        self.assertEqual(types, ["dividend", "checked"])

    def test_end_to_end_mock_scoring_over_weekend(self):
        # 월요일 라운드: 기준 금요일(11/13) → 평가 월요일(11/16). 확인 기록은 거래일(11/16)만 있으면 됨
        d = new_league()
        pick(d, "buffett", "2026-11-16", "US", "AAPL")
        C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-13", "close": 200.0}]), "US", ["AAPL"], date(2026, 11, 13), "final")
        C.collect(d, mock("US", [{"ticker": "AAPL", "session": "2026-11-16", "close": 203.0}]), "US", ["AAPL"], date(2026, 11, 16), "final")
        w = L.run_scoring(d, today=date(2026, 11, 17))[0]
        self.assertEqual((w["status"], w["score"]), ("final", 1.5))

    def test_unconfigured_providers_raise(self):
        for name in ("krx_openapi", "tiingo", "alpaca", "kis"):
            with self.assertRaises(C.NotConfigured):
                C.PROVIDERS[name]()


class MakeCsv(unittest.TestCase):
    def test_round_trip_through_import(self):
        d = new_league()
        picks = [{"agent_id": "buffett", "agent_version": 1, "market": m, "ticker": t, "name": n,
                  "locked_at": "2026-11-10T08:15:00+09:00", "rationale": "근거, 쉼표와 \"따옴표\" 포함\n줄바꿈",
                  "risks": ["위험1", "위험2"], "sources": [{"url": "https://x", "as_of": "2026-11-09",
                                                         "retrieved_at": "2026-11-10T07:10:00+09:00"}]}
                 for m, t, n in (("KR", "005930", "삼성전자"), ("US", "AAPL", "Apple"))]
        out = L.make_csv(picks, "2026-11-10", d / "x.csv")
        ok, bad = L.import_csv(d, out, "claude", dry_run=True)
        self.assertEqual(bad, [])
        self.assertEqual(ok[0]["sources"][0]["retrieved_at"], "2026-11-10T07:10:00+09:00")
        self.assertEqual(ok[0]["risks"], ["위험1", "위험2"])


class WeeklyCloseAndDue(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()) / "sample"
        L.make_sample(self.d, close_week=False)        # W46 예시: 마감 전 상태

    def test_close_fixes_decision_and_updates_roster(self):
        before = L.weekly(self.d, "2026-W46", "claude")["decision"]
        recs = L.weekly_close(self.d, "2026-W46", now="2026-11-16T06:30:00+09:00")
        self.assertEqual({r["team"] for r in recs}, {"claude", "shushu"})
        c = next(r for r in recs if r["team"] == "claude")
        self.assertEqual((c["eliminate"], c["replacement"], c["effective_week"]),
                         (before["eliminate"], before["replacement"], "2026-W47"))
        r = L.load_roster(self.d)
        out = next(a for a in r["claude"] if a["id"] == before["eliminate"])
        new = next(a for a in r["claude"] if a["id"] == before["replacement"])
        self.assertEqual((out["status"], out["eliminated_week"]), ("eliminated", "2026-W46"))
        self.assertEqual((new["status"], new["joined_week"]), ("active", "2026-W47"))
        self.assertNotIn(before["replacement"], [b["id"] for b in r["bench"]])
        # 마감한 주의 순위표에는 탈락자가 남고 신규 합류자는 없다
        ids = [x["agent_id"] for x in L.weekly(self.d, "2026-W46", "claude")["ranking"]]
        self.assertIn(before["eliminate"], ids)
        self.assertNotIn(before["replacement"], ids)
        # 다시 마감해도 중복 기록 없음
        self.assertEqual(L.weekly_close(self.d, "2026-W46"), [])
        self.assertEqual(L.verify(self.d), [])

    def test_due_sessions_lists_only_missing_finals(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        due = C.due_sessions(d, date(2026, 11, 11))
        self.assertEqual(due, {("KR", "2026-11-09"): ["KOSPI"], ("KR", "2026-11-10"): ["005930", "KOSPI"]})
        self.assertEqual(C.due_sessions(d, date(2026, 11, 10)), {("KR", "2026-11-09"): ["KOSPI"]})

    def test_collect_due_skips_without_keys(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "US", "AAPL")
        rep = C.collect_due(d, date(2026, 11, 11))
        self.assertTrue(rep["skipped"])
        self.assertTrue(all("환경변수" in x["reason"] for x in rep["skipped"]))
        self.assertEqual(rep["collected"], [])


class Safeguards(unittest.TestCase):
    def test_extreme_move_held(self):
        d = new_league()
        pick(d, "buffett", "2026-11-10", "KR", "005930")
        checked(d, "KR", "005930")
        price(d, "KR", "005930", "2026-11-09", 100000)
        price(d, "KR", "005930", "2026-11-10", 50000)        # −50%: 분할 누락 의심
        w = L.run_scoring(d, today=date(2026, 11, 11))[0]
        self.assertEqual(w["status"], "held")
        self.assertIn("±30%", w["reason"])


class PublicAndSnapshot(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()) / "sample"
        L.make_sample(self.d)

    def test_public_export_has_no_raw_prices(self):
        out = self.d / "pub.js"
        L.export(self.d, out, public=True)
        txt = out.read_text()
        self.assertNotRegex(txt, r'"(base_close|eval_close|close)"\s*:')
        self.assertIn('"public": true', txt)
        self.assertIn('"score"', txt)

    def test_private_export_keeps_prices(self):
        out = self.d / "priv.js"
        L.export(self.d, out)
        self.assertIn('"base_close"', out.read_text())

    def test_build_site_contains_only_public_data(self):
        out = Path(tempfile.mkdtemp()) / "site"
        files = L.build_site(self.d, out)
        self.assertIn("data/league.js", files)
        for f in out.rglob("*.js"):
            self.assertNotRegex(f.read_text(), r'"(base_close|eval_close|close)"\s*:')

    def test_price_free_snapshot(self):
        snap, body = L.snapshot(self.d, date(2026, 11, 10), "price-free", now="2026-11-10T07:00:00+09:00")
        self.assertNotIn('"close"', body)
        self.assertEqual(snap["corporate_actions_upcoming"], [])            # SAMPLE 출처는 공개 이용 출처 아님
        self.assertEqual(snap["markets"]["KR"]["base_session"], "2026-11-09")

    def test_with_prices_snapshot_and_hash_file(self):
        p, sha = L.write_snapshot(self.d, date(2026, 11, 10), "with-prices", now="2026-11-10T07:00:00+09:00")
        body = p.read_text()
        self.assertIn('"base_closes"', body)
        import hashlib
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), sha)
        self.assertTrue((p.parent / (p.name + ".sha256")).read_text().startswith(sha))

    def test_snapshot_deterministic(self):
        a = L.snapshot(self.d, date(2026, 11, 10), "price-free", now="2026-11-10T07:00:00+09:00")[1]
        b = L.snapshot(self.d, date(2026, 11, 10), "price-free", now="2026-11-10T07:00:00+09:00")[1]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
