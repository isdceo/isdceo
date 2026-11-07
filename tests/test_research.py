"""자료 조회 도구 시험(네트워크 없음).  실행: python3 -m unittest discover -s tests"""
import json, sys, tempfile, unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import league as L  # noqa: E402
import research as R  # noqa: E402

CFG = L.load_config(L.ROOT / "league")


def fake(rows_by):
    return lambda m, t, s: (f"https://example/{t}", json.dumps(rows_by.get(t, [])).encode(), rows_by.get(t, []))


class Research(unittest.TestCase):
    def test_close_returns_only_base_session_row(self):
        rows = {"033780": [("2026-11-05", 194200.0), ("2026-11-06", 189900.0)], "000660": [("2026-11-05", 1264000.0)]}
        out = R.close("KR", ["033780", "000660"], date(2026, 11, 9), CFG, fake(rows))   # 11/9 라운드 기준 세션 = 11/6
        self.assertEqual((out[0]["session"], out[0]["value"]), ("2026-11-06", 189900.0))
        self.assertIsNone(out[1]["value"])                                                # 11/5로 메우지 않음
        self.assertIn("가장 최근 행 2026-11-05", out[1]["note"])
        self.assertTrue(out[0]["sha256"] and out[0]["retrieved_at"].endswith("+09:00"))

    def test_holiday_round(self):
        out = R.close("KR", ["005930"], date(2026, 11, 7), CFG, fake({}))                 # 토요일
        self.assertIn("휴장", out[0]["note"])

    def test_yahoo_rows_meta_fallback_only_after_close(self):
        def body(meta_time, end):
            return json.dumps({"chart": {"result": [{"meta": {"gmtoffset": 32400, "regularMarketTime": meta_time, "regularMarketPrice": 189900,
                                                               "currentTradingPeriod": {"regular": {"end": end}}},
                                                      "timestamp": [int(datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc).timestamp())],
                                                      "indicators": {"quote": [{"close": [194200]}]}}]}}).encode()
        t_close = int(datetime(2026, 11, 6, 6, 30, tzinfo=timezone.utc).timestamp())       # 15:30 KST
        end = int(datetime(2026, 11, 6, 6, 30, tzinfo=timezone.utc).timestamp())
        self.assertEqual(dict(R.yahoo_rows(body(t_close, end))).get("2026-11-06"), 189900.0)
        self.assertIsNone(dict(R.yahoo_rows(body(t_close - 3600, end))).get("2026-11-06"))  # 장중 값은 쓰지 않음

    def test_check_csv_warnings(self):
        d = Path(tempfile.mkdtemp())
        log = d / "log.jsonl"
        R.write_log(log, [R._rec("close", "KR", "033780", "2026-11-06", 189900.0, "u", b"x")])
        f = d / "x.csv"
        f.write_text("round_date,agent_id,agent_version,market,ticker,name,locked_at,rationale,risks,sources\n"
                     "2026-11-09,buffett,1,KR,033780,KT&G,2026-11-09T08:10:00+09:00,\"11/06 종가 189,900원 기준 배당수익률 4.2%\",위험,https://a|2026-11-06|2026-11-09T07:30:00+09:00\n"
                     "2026-11-09,lynch,1,KR,033780,KT&G,2026-11-09T08:10:00+09:00,\"11/06 종가 190,700원, 11/05 종가 194,200원\",위험,https://b|2026-11-10|2026-11-09T07:30:00+09:00\n",
                     encoding="utf-8")
        w = R.check_csv(f, log, CFG)
        self.assertFalse(any(x.startswith("2행") for x in w))                            # 일치 → 경고 없음
        self.assertTrue(any("3행" in x and "190,700" in x and "다름" in x for x in w))      # 통합 시세 → 다름
        self.assertTrue(any("3행" in x and "11/05" in x and "기준 세션" in x for x in w))   # 다른 날 종가
        self.assertTrue(any("3행" in x and "늦음" in x for x in w))                        # 출처 기준일 > 라운드


if __name__ == "__main__":
    unittest.main()
