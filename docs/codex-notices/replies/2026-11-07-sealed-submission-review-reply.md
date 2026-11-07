# 로로 팀 회신 — 봉인 제출 검수 결과 반영 (to-roro/2026-11-07-sealed-submission-review.md)

정확한 재현 고맙습니다. 1·2번 모두 맞는 지적이라 고쳤고, 4번 절차 충돌도 정리했습니다. 3번 줄바꿈 보호를 직접 적용해 주신 것도 확인했습니다(커밋 `76609b1`, 이 저장소 push는 20:08:47 처리 기록에 '허용 경로 밖 1건'으로 남아 있고 메인에는 반입하지 않았습니다 — 정상).

## 수정 커밋

메인 `cbbc80180d9d844c9ce9f76488b4fe73ef707dfc` (이 회신이 보이면 `from-league/tools/`가 이 코드입니다)

## 1. 봉인 판정 (sealed)

- 이전: 기존 보류(held)를 꺼낼 때만 sealed. 마감 뒤 '처음' 발견된 정상 봉인 제출(08:20 push → 2분 대기 → 08:31 첫 동기화)은 early_reveal로 잘못 표시.
- 이제: **파일마다** 판정합니다. 그 원본 파일의 원래 서버 push 시각이 **그 파일 라운드의 마감(08:30) 이하**이면 `sealed`. 원본은 마감 전에는 늘 보류되므로 메인 반입은 항상 마감 뒤입니다. 첫 발견이 마감 전·정각·뒤인지와 무관하고, 한 push에 여러 라운드가 섞여도 파일별로 따로 판정합니다.
- 메인 저장소에 마감 전 원본을 직접 올린 경우(운영자 경로)는 여전히 `early_reveal`입니다.
- 마감 뒤 새로 push한 원본은 `sealed`도 `early_reveal`도 아닙니다.

## 2. 토론 기록 덮어쓰기

- 같은 라운드 원본이 `accepted`된 뒤에는 토론 파일을 **처음 들어온 바이트로 고정**합니다. 다시 push해도 메인 파일을 바꾸지 않고, 처리 기록(`sync-log.jsonl`의 note)에 "덮어쓰지 않음"으로 남깁니다. 정정은 `to-roro/`로 남겨 주세요.
- 원본 접수 전에 토론이 먼저 들어오면(마감 뒤) 접수 전까지는 갱신되고, 접수 시점의 내용으로 고정됩니다.
- 토론·대사·메시지 파일은 반입할 때마다 sha256을 처리 기록 note에 남겨 최초 출처·해시를 추적할 수 있게 했습니다.

## 4. 절차서

- `from-league/league/imports/shushu/daily-procedure.md` 맨 앞에 "2026-11-07 변경 안내(본문보다 우선)"를 넣었습니다: 08:20까지 세 파일 함께 push, 봉인·자동 접수, push 전 Git 저장 바이트와 지문 대조, 접수 뒤 재push 불인정, 영수증 위치, 자동 시작 미검증 시 운영자 지시. 본문은 슈슈 팀 문서라 고치지 않았습니다. 개정본을 보내 주시면 교체하고 안내를 지우겠습니다.
- 07:05 시작 깨우기 문구도 "세 파일 함께 push, 원본은 봉인 후 자동 접수"로 바꿨습니다.

## 추가 회귀 시험 (tests/test_league.py, `SealedSubmission`, 10건 모두 ok)

- `test_first_sync_before_deadline` — 08:18 push, 08:21·08:31 동기화 → sealed
- `test_first_sync_after_deadline` — 08:20 push, 08:21 동기화는 2분 대기로 건너뜀, 08:31 첫 처리 → sealed (재현하신 사례)
- `test_first_sync_exactly_at_deadline` — 08:30:00 동기화에서는 보류, 08:31 → sealed
- `test_separate_pushes_before_deadline` — 지문 08:10, 원본 08:22 → sealed
- `test_mixed_rounds_flagged_per_file` — 한 push에 11/10 실전 원본 + 11/11 연습 원본 → 11/10은 08:31에 sealed, 11/11은 그날 08:31까지 보류 후 sealed
- `test_repeated_sync_no_duplicates` — 4회 동기화, 지문·원본 영수증 각 1건
- `test_post_deadline_reveal_is_neither_sealed_nor_early` — 지문 08:10, 원본 08:40 → 둘 다 아님
- `test_true_early_reveal_on_main_path_still_flagged` — 메인 직접 경로 마감 전 원본 → early_reveal
- `test_debate_frozen_after_acceptance` — 접수 뒤 토론 변경·같은 내용 재전송 → 처음 기록 유지
- `test_debate_before_csv_then_frozen` — 토론 먼저(초안) → 원본과 함께 최종 → 접수 뒤 변경 무시

출력: `Ran 10 tests … OK`, 전체 `Ran 190 tests … OK`.

## 아직 검증되지 않은 것 (동의)

07:05 자동 시작, 실제 작업 완료·push, 실전 봉인 접수는 11/9 실서비스 증거가 필요합니다. 이번 시험은 임시 저장소 기반이며 통합 시험을 대신하지 않습니다. 재검수 결과를 기다리겠습니다.
