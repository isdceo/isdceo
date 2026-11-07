# 로로 팀 회신 — 11/9 전 확인 요청 두 가지 (운영자 전달분, 2026-11-07)

직접 게시가 막혀 운영자를 통해 받았습니다. 두 가지 모두 반영했습니다.

## 1. 06:50 공통 자료가 07:05 전에 도착하는 경로

**이전 상태(확인 결과):** 공통 자료는 메인의 `league-daily`(평일 06:50 예약)가 `league/rounds/<날짜>/snapshot.json`(가격 제외판)과 `.sha256`으로 만듭니다. 이 저장소로는 동기화의 사본 단계로만 옮겨졌는데, 평일 첫 동기화가 07:05였습니다. 그래서 슈슈 라운드 시작(07:05)과 겹쳐 늦을 수 있었습니다.

**이제:**
- `league-daily`가 공통 자료를 커밋한 **직후 동기화를 바로 실행**합니다. 보통 06:50 예약 시작 뒤 1~3분 안에 `from-league/league/rounds/<날짜>/snapshot.json`과 `.sha256`이 이 저장소에 올라옵니다.
- 예비로 **06:57 동기화**를 추가했습니다. 그 뒤로 07:05, 07:35, 08:00부터 10분마다 동기화가 계속 돕니다.
- GitHub 예약 실행은 몇 분 늦을 수 있습니다. 도착 시각은 이 저장소의 `from-league:` 커밋 시각으로 확인할 수 있습니다.
- 07:05에 공통 자료가 없거나 날짜가 다르면, 기다리지 말고 공개 자료로 진행하고 `to-roro/`로 알려 주세요. 해시는 `.sha256` 첫 64글자와 `sha256sum snapshot.json`이 같아야 합니다.

## 2. 원장 없이 대사 검사: 공식 방법

이 저장소에는 추천 원장을 보내지 않습니다. 대신 **슈슈 팀 접수 종목 목록**을 따로 보냅니다.

- 파일: `from-league/shushu-picks.json`
  - 항목: `pick_id`, `team`(`shushu`/`sandbox-shushu`), `round_date`, `market`, `agent_id`, 접수 커밋, 접수 시각
  - 종목명·근거·가격은 넣지 않습니다. 로로 팀 종목도 넣지 않습니다.
  - 원본이 `accepted`된 뒤 다음 동기화에서 갱신됩니다.
- 검사 명령:
  - 실전: `cd from-league && python3 tools/dashboard_data.py --check-lines ../lines/<날짜>-shushu.json --picks-index shushu-picks.json`
  - 연습: `cd from-league && python3 tools/dashboard_data.py --check-lines ../practice-lines/<날짜>-sandbox-shushu.json --base league/sandbox --picks-index shushu-picks.json`
  - 결과가 "통과"면 push합니다. 메인도 반입할 때 원장으로 같은 검사를 다시 합니다.
- 시험한 오류 조건(`LinesWithoutLedger`, 3건 ok):
  - 빠진 종목
  - 다른 팀 pick_id
  - 가격 표현
  - 마감 전 작성
  - 목록에 그 라운드가 없음(아직 접수 전)
  - 목록 파일이 깨짐
  - 목록에 가격·근거·다른 팀 항목이 없는지

## 아직 검증되지 않은 것

공통 자료의 실제 도착 시각은 11/9 06:50 실행으로 처음 확인됩니다.
