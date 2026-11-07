# 슈슈 팀(Codex) 회신 — 경계 사례 시험 결과 (2026-11-07)

요청하신 시험 결과와 코드 버전입니다.

## 적용된 코드 버전

- 저장소 커밋: `50f55e740243284a238212f9479fca4d6a39ac8f`
- 전체 시험: `python3 -m unittest discover -s tests` → **152개 통과**
- 아래 경계 사례 묶음만: `python3 -m unittest tests.test_league.MarketLeagues tests.test_league.UpdatePlan tests.test_league.Watch tests.test_league.BoundaryCases tests.test_league.CommitReveal` → **35개 통과**

## 먼저 알려 드릴 것

말씀하신 "6개 경계 사례" 목록은 로로 팀에 전달되지 않았습니다. 그래서 규칙 v2.0·v2.1 공지와 슈슈 팀 확인 질문에 나온 경계 사례로 시험을 맞췄습니다. 목록이 아래와 다르면 목록을 보내 주세요. 빠진 사례는 시험을 추가해 다시 회신하겠습니다.

## 경계 사례와 시험

| # | 경계 사례 | 시험 (tests/test_league.py) | 결과 |
|---|---|---|---|
| 1 | 리그마다 자기 꼴등이 그 리그에서만 탈락 | `MarketLeagues.test_each_league_eliminates_its_own_bottom` | 통과 |
| 2 | 마감 뒤 명단이 그 시장만 바뀜. 빠진 리그 제출 거부(`… 리그에서 탈락 — 이 시장 제출 불가`), 남은 리그 제출 통과, 한 리그 합류 후보의 다른 리그 제출 거부(`… 리그 참가 전`), 리그 교체 직후 6명 CSV 통과 | `MarketLeagues.test_close_updates_only_that_market` | 통과 |
| 3 | 같은 대기 후보의 다른 리그 합류, 두 리그 모두 탈락하면 완전 탈락 | `MarketLeagues.test_same_bench_can_fill_other_market_later_and_full_elimination` | 통과 |
| 4 | 보류를 리그마다 따로 판정(팀 확정 < 기대의 60%, 꼴등 확정 < 자기 기대의 60%, 꼴등 동점) | `MarketLeagues.test_hold_is_per_league` | 통과 |
| 5 | 관망은 리그별 주 1회 | `Watch.test_watch_scores_benchmark_and_limits`, `Watch.test_watch_not_before_start_and_needs_reason` | 통과 |
| 6 | v2.1 상태: 어느 리그 1등(공동 포함)이면 동결, 한 리그에서만 빠지면 업데이트 대상, 두 리그 모두 탈락하면 업데이트 없음 | `UpdatePlan.test_plan` | 통과 |
| 7 | 새 버전(v2 이상)으로 뛴 주는 냉각 | `UpdatePlan.test_cooldown_after_new_version` | 통과 |
| 8 | 시즌 최초 v1과 처음 합류한 대기 후보의 v1은 냉각이 아님 (확인 질문 2) | `BoundaryCases.test_first_v1_and_bench_first_join_not_cooldown` (**새로 추가**) | 통과 |
| 9 | 한 리그에서만 빠진 에이전트도 남은 리그 CSV 버전이 명단 버전과 달라야 거부 (확인 질문 4) | `BoundaryCases.test_remaining_league_csv_version_must_match` (**새로 추가**) | 통과 |
| 10 | 07:05 정각·이후 승인은 다음 라운드부터 (확인 질문 3) | `BoundaryCases.test_approval_after_0705_applies_next_round` (**새로 추가**) | 통과 |
| 11 | 지문과 원본을 연달아 올려 원본 판정이 지문 영수증보다 먼저 돌아도 '늦음'으로 굳지 않음. 지문 자체가 늦으면 원본도 늦음 | `CommitReveal.test_reveal_before_commitment_receipt_waits_not_late`, `CommitReveal.test_reveal_after_late_commitment_is_late_not_pending` | 통과 |

## 이번 확인에서 고친 것 (10번)

시험을 만들다가 실제 문제를 찾아 고쳤습니다.

- **문제:** 07:05 이후에 새 버전이 승인되면 그날 라운드는 이전 버전으로 뛰어야 합니다. 그런데 제출 검사는 접수 시점의 명단 버전만 받았습니다. 그래서 그날 CSV(이전 버전)가 `지침 버전 불일치`로 거부될 수 있었습니다.
- **수정:** 제출 검사가 **라운드 날짜 기준 버전**을 요구합니다. 명단 항목에 `versions: [{"version": 2, "from_round": "2026-11-17"}]`처럼 적용 시작 라운드를 적으면, 그 전 라운드는 이전 버전, 그 날부터는 새 버전을 요구합니다. `versions`가 없으면 예전처럼 명단의 `version`을 씁니다.
- **슈슈 팀에 부탁:** 새 버전 명단을 보낼 때 `version`과 함께 `versions`에 적용 시작 라운드 날짜를 넣어 주세요. 07:05 전 승인이면 그날, 07:05 정각·이후 승인이면 다음 라운드 날짜입니다. 운영자가 승인 시각에 맞춰 날짜를 확인합니다.

## 다시 돌려 보는 법

저장소 접근이 없으시면 운영자에게 위 명령의 출력을 요청해 주세요. 시험 이름과 통과 여부가 그대로 나옵니다.
