"""DART 연결 테스트 (네트워크 없이). 실행: python3 -m unittest discover -s tests -v"""
import os, sys, unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import league as L  # noqa: E402
import dart as D  # noqa: E402
from test_league import new_league, pick, price  # noqa: E402

UNI = {"033780": "KT&G", "005930": "삼성전자"}


def item(code, name, dt, no):
    return {"stock_code": code, "report_nm": name, "rcept_dt": dt, "rcept_no": no, "flr_nm": "회사"}


class Categorize(unittest.TestCase):
    def test_filter_and_categories(self):
        items = [item("033780", "기업설명회(IR)개최(안내공시)", "20261030", "1"),
                 item("033780", "연결재무제표기준영업(잠정)실적(공정공시)", "20261104", "2"),
                 item("005930", "임원ㆍ주요주주특정증권등소유상황보고서", "20261104", "3"),   # 분류 밖
                 item("999999", "현금ㆍ현물배당결정", "20261104", "4")]                       # 대상 밖
        out = D.filter_universe(items, UNI)
        self.assertEqual([(x["ticker"], x["category"]) for x in out], [("033780", "IR"), ("033780", "실적")])
        self.assertTrue(out[0]["url"].endswith("rcpNo=1"))


class Dividend(unittest.TestCase):
    TEXT = "현금ㆍ현물배당 결정 1. 배당구분 분기배당 2. 배당종류 현금배당 3. 1주당 배당금(원) 보통주식 1,200 종류주식 - 4. 배당기준일 2026-11-06 5. 배당금지급 예정일자 2026-11-20"

    def test_parse(self):
        self.assertEqual(D.parse_dividend(self.TEXT), {"record_date": "2026-11-06", "amount": 1200.0})
        self.assertIsNone(D.parse_dividend("배당 관련 내용 없음"))

    def test_ex_date_is_previous_session(self):
        cfg = L.load_config(L.ROOT / "league")
        self.assertEqual(D.kr_ex_date(date(2026, 11, 6), cfg), date(2026, 11, 5))   # 금 기준일 → 목 배당락
        self.assertEqual(D.kr_ex_date(date(2026, 11, 9), cfg), date(2026, 11, 6))   # 월 기준일 → 금 배당락

    def test_dividend_in_window_recorded_and_scored(self):
        d = new_league()
        pick(d, "buffett", "2026-11-05", "KR", "033780")                # 기준 11/4 → 평가 11/5
        price(d, "KR", "033780", "2026-11-04", 191900)
        price(d, "KR", "033780", "2026-11-05", 190800)                   # 배당락으로 하락
        items = [item("033780", "현금ㆍ현물배당결정", "20261020", "R1")]
        res = D.check_kr_corporate_actions(d, "033780", date(2026, 11, 4), date(2026, 11, 5), key="x",
                                           items=items, fetch_text=lambda no, key=None: self.TEXT)
        self.assertTrue(res["checked"])
        self.assertEqual(res["dividends"][0]["ex_date"], "2026-11-05")
        D.record_kr_ca(d, res)
        w = L.run_scoring(d, today=date(2026, 11, 6))[0]
        self.assertEqual(w["status"], "final")
        self.assertEqual(w["score"], round(((190800 + 1200) / 191900 - 1) * 100, 2))

    def test_old_dividend_outside_window_still_checks(self):
        d = new_league()
        old = "1주당 배당금(원) 보통주식 1,200 배당기준일 2026-06-30"
        res = D.check_kr_corporate_actions(d, "033780", date(2026, 11, 4), date(2026, 11, 5), key="x",
                                           items=[item("033780", "현금ㆍ현물배당결정", "20260806", "R0")],
                                           fetch_text=lambda no, key=None: old)
        self.assertTrue(res["checked"])
        self.assertEqual(res["dividends"], [])

    def test_unparseable_or_split_stays_unchecked(self):
        d = new_league()
        r1 = D.check_kr_corporate_actions(d, "033780", date(2026, 11, 4), date(2026, 11, 5), key="x",
                                          items=[item("033780", "현금ㆍ현물배당결정", "20261020", "R1")],
                                          fetch_text=lambda no, key=None: "형식이 다른 본문")
        r2 = D.check_kr_corporate_actions(d, "033780", date(2026, 11, 4), date(2026, 11, 5), key="x",
                                          items=[item("033780", "주식분할결정", "20261020", "R2")])
        self.assertFalse(r1["checked"]); self.assertFalse(r2["checked"])
        self.assertFalse(D.record_kr_ca(d, r1))
        self.assertEqual(L.read_ledger(d, "corporate_actions"), [])      # 아무것도 기록 안 함 → 채점 보류

    def test_no_related_disclosure_checks(self):
        d = new_league()
        res = D.check_kr_corporate_actions(d, "005930", date(2026, 11, 4), date(2026, 11, 5), key="x", items=[])
        self.assertTrue(res["checked"])


class SnapshotWithoutKey(unittest.TestCase):
    def test_not_configured(self):
        os.environ.pop("DART_API_KEY", None)
        snap, _ = L.snapshot(L.ROOT / "league", date(2026, 11, 5), "price-free", now="2026-11-05T06:50:00+09:00")
        self.assertEqual(snap["disclosures"]["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
