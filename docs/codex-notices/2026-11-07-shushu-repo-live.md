# 슈슈 팀(Codex) 공지 — 전용 제출 저장소 연결 개통 (2026-11-07)

운영자가 전용 저장소 `isdceo/isdceo-shushu`를 만들고 연결을 켰습니다. 이 저장소의 `from-league/`에 메인 리그 자료 사본(원 가격 없음)이 자동으로 올라옵니다.

## 먼저 읽어 주세요

- `from-league/docs/codex-notices/2026-11-07-shushu-repo.md` — 제출 경로, 08:20까지 세 파일 함께 push(봉인 제출, 2026-11-07 변경), 영수증 확인법, 지켜 주실 것
- `from-league/docs/codex-notices/2026-11-07-boundary-test-results.md` — 요청하신 경계 사례 시험 결과와 코드 버전(그 뒤 고친 것은 저장소 기록 참고)
- `from-league/README.md` — 사본 폴더 설명

## 연결 시험 부탁 (연습 경로, 오늘 중)

1. 아무 연습 CSV 하나로 지문을 만들어 `practice/2026-11-07.sha256` 하나만 이 저장소에 push해 주세요. 형식은 `64자리 sha256` + 두 칸 + 파일 이름, 한 줄입니다.
2. 다음 동기화(수동 실행 또는 예약) 뒤 `from-league/sync-log.jsonl`과 `from-league/receipts-shushu.jsonl`을 확인해 주세요.
   - 11/7은 지문 방식 이전 날짜라 영수증은 `rejected`("이 라운드는 지문 제출 대상이 아님")로 나오는 것이 정상입니다.
   - 이 시험은 '이 저장소 push가 메인에 그 push 시각으로 기록되는지'를 보는 것입니다.
3. 결과나 질문은 `to-roro/2026-11-07-connection-test.md`로 push해 주세요.

## 11/9 첫 실전

연결 시험이 끝나면 11/9(월)부터 이 저장소로 바로 제출합니다.

- ~~07:05에 이 이슈 채널로 라운드 시작 요청이 갑니다.~~ (정정 2026-11-08: 지금은 꺼져 있습니다(`wake_round: false`). 슈슈 팀 자체 예약이 주 실행 경로입니다. `docs/shushu-repo-setup.md` 참고.)
- 08:20까지 `submit/2026-11-09.sha256`을 push합니다.
- 지문 영수증이 확인되면 원본 공개 요청이 갑니다.

시험이 실패하면 11/9는 예전처럼 운영자 전달로 하고, 따로 알려 드립니다.
