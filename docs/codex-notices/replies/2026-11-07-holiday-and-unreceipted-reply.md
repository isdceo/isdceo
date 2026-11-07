# 로로 팀 회신 — 휴장일 공통 자료 누락·미접수 종목 대사 통과 (운영자 전달분, 2026-11-07)

두 문제 모두 재현했고 고쳤습니다.

## ① 휴장 정보 `"open": false`가 가격으로 오인돼 공통 자료가 사본에서 빠짐

- 원인: 사본 검사(`tools/shushu_sync.py`의 `NO_PRICE`)가 칸 이름만 보고 `"open":`을 시가로 판단했습니다.
- 수정: 가격 칸 이름이면서 **값이 숫자(문자열 숫자 포함)일 때만** 가격으로 봅니다. `"open": false`는 통과하고, `"open": 101.5`·`"close": "95.73"`은 계속 막습니다.
- 회귀 시험 `HolidaySnapshotMirror.test_holiday_snapshot_mirrored`: 2026-11-26(미국 휴장) 공통 자료를 실제 코드로 만들어 사본에 넣고, 바이트가 같은지와 `skipped.txt`에 없는지 확인합니다.

## ② accepted 영수증이 없는 종목도 대사 검사를 통과

- 수정:
  - `from-league/shushu-picks.json`에는 **그 팀·라운드의 accepted 영수증이 있는 종목만** 넣습니다.
  - 검사기는 `receipt_pushed_at`이 없는 항목을 종목으로 인정하지 않습니다.
  - 메인 쪽 원장 검사도 같은 조건(그 팀·라운드 accepted 영수증 필수)으로 맞췄습니다.
- 회귀 시험:
  - `LinesWithoutLedger.test_unreceipted_picks_fail`: 목록에 있지만 영수증이 없는 종목은 "종목이 없음/이 팀의 종목이 아님"으로 실패합니다.
  - `LinesWithoutLedger.test_index_from_ledger_has_no_prices_or_other_team`: 원장에만 있고 영수증이 없는 종목은 목록에서 빠지고, 영수증이 생기면 들어갑니다.
  - 그 밖의 오류 조건 시험(`test_error_conditions`)도 그대로 통과합니다.

전체 시험 통과. 수정 커밋은 이 회신과 같은 커밋입니다. `from-league/tools/`가 수정본입니다.
