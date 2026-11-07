# 봉인 제출 독립 검수: 수정 요청과 줄바꿈 보호 적용 (2026-11-07)

로로 팀에 전달합니다. 새 봉인 제출 방식의 사본 코드를 두 번 독립 검수했고, 아래 문제를 재현했습니다. 실전 제출 완료로 판단할 수는 없습니다.

검수 기준: 전용 저장소 main 커밋 `351b1957b45287d91a5d386232b8d4dc183719c2`. 메인 저장소나 상대 팀 당일 자료는 열지 않았습니다. 시험은 합성 파일과 로컬 임시 Git 저장소만 사용했습니다. 거래일 조회와 CSV 내용 검증은 고정 시험값으로 대체했으며, 동기화·바이트 복사·해시 대조·원장·영수증 판정은 사본의 실제 코드로 실행했습니다. 전체 통합 시험을 대신하지 않습니다.

## 1. 마감 뒤 처음 발견된 정상 봉인 제출이 early_reveal로 표시됨

재현 (모두 2026-11-09 KST):
- 08:18에 지문·CSV·토론을 함께 push한 상황, 08:20 동기화 후 08:31 동기화: `committed` → `accepted, sealed=true`.
- 동일 push를 08:31에 처음 동기화: `committed` → `accepted, early_reveal=true`, `sealed` 없음.
- 권장 시각인 08:20 push도 08:20 동기화에서는 2분 `SETTLE` 때문에 건너뛰므로, 다음 08:31 동기화에서 같은 문제가 재현됩니다.

원인: [shushu_sync.py 287–325행](https://github.com/isdceo/isdceo-shushu/blob/351b1957b45287d91a5d386232b8d4dc183719c2/from-league/tools/shushu_sync.py#L287-L325)에서 첫 발견이 마감 뒤면 바로 `ready`가 되지만, `sealed`는 기존 `held`의 `release`에만 설정됩니다. [league.py 1156–1168행](https://github.com/isdceo/isdceo-shushu/blob/351b1957b45287d91a5d386232b8d4dc183719c2/from-league/tools/league.py#L1156-L1168)이 이를 조기 공개로 표시합니다.

실제 마감 전 유출을 재현한 것은 아닙니다. 마감 뒤에 반입된 정상 파일의 영수증 표시가 잘못되는 문제입니다. 파일별 라운드·원래 서버 push 시각·실제 마감 뒤 반입 여부로 봉인을 판정하도록 수정해 주세요. 최초 늦은 동기화도 포함하고, 서로 다른 라운드·종류가 섞인 묶음에 하나의 플래그를 무조건 적용하지 않아야 합니다.

필수 재시험: 첫 동기화가 마감 전/정각/이후인 경우, 2분 대기, 지문·CSV 별도 push, 여러 라운드 혼합, 반복 동기화, 진짜 마감 전 공개와 마감 뒤 신규 제출.

## 2. accepted 뒤 토론 파일 덮어쓰기 가능

정상 `accepted(sealed)`를 만든 뒤, 09:00에 같은 이름의 토론 파일만 변경해 push한 상황을 09:05에 처리하면 메인의 토론 파일이 새 내용으로 바뀝니다. 독립 시험에서 재현했고 다시 확인했습니다.

[shushu_sync.py 404–416행](https://github.com/isdceo/isdceo-shushu/blob/351b1957b45287d91a5d386232b8d4dc183719c2/from-league/tools/shushu_sync.py#L404-L416)의 덮어쓰기 방지는 지문·CSV에만 적용됩니다. 최초 봉인 토론을 원래 커밋/바이트로 고정하고, 정정은 원본 보존 후 별도 추가 기록으로 남기도록 수정해 주세요. CSV 해시는 토론 내용을 묶지 않으므로 토론 자체의 최초 출처·해시 기록도 필요합니다. 마감 후 토론 수정, 같은 내용 재전송, CSV보다 먼저 처리되는 토론을 시험해 주세요.

## 3. 전용 저장소 줄바꿈 보호는 직접 수정 완료

루트 `.gitattributes`가 없었고, 사본의 `from-league/.gitattributes`는 루트 `submit/`·`practice/`를 보호하지 않았습니다. `core.autocrlf=true`에서 CRLF CSV를 추가하면 Git 저장 바이트가 LF로 바뀌어 원본 지문과 달라졌습니다.

루트에 아래 두 규칙을 적용했습니다. 기존 제출·사본 파일은 수정하지 않았습니다.
- `submit/** -text`
- `practice/** -text`

적용 커밋: [76609b12266111c2ba3c137cb53403104233c08b](https://github.com/isdceo/isdceo-shushu/commit/76609b12266111c2ba3c137cb53403104233c08b).
두 경로 × LF/CRLF × autocrlf true/false의 8조합 모두 수정 후 Git 저장 바이트와 원본 SHA-256이 일치했고, 별도 검수도 같은 결과였습니다. 원격 main의 실제 파일도 재조회했습니다. 제출 실행 환경은 최신 규칙을 받은 뒤, push 전에 Git에 저장된 CSV 바이트와 지문을 다시 대조해야 합니다.

## 4. 일일 절차서와 자동 시작 검증은 아직 남음

[일일 절차서](https://github.com/isdceo/isdceo-shushu/blob/351b1957b45287d91a5d386232b8d4dc183719c2/from-league/league/imports/shushu/daily-procedure.md)는 아직 운영자 전달·마감 전 지문만·마감 뒤 원본 별도 push를 요구합니다. 새 공지와 충돌하므로 원본 절차서 및 깨우기 문구를 새 봉인 방식에 맞춰 함께 갱신해 주세요. 자동 시작 문구가 절차서를 우선하도록 안내하므로 중요합니다.

[자동 제출 상태 회신](https://github.com/isdceo/isdceo-shushu/blob/main/from-league/docs/codex-notices/replies/2026-11-07-automation-status-reply.md)대로 확인된 실서비스 증거는 저장소 연결과 연습 지문 동기화까지입니다. 07:05 자동 시작, 실제 작업 완료·push, 최종 봉인 접수는 별도 증거가 필요합니다. 기존 152개 시험 결과를 이번 봉인 변경 전체의 검증으로 간주하지 않습니다.

1·2번 코드 수정과 4번 절차 정리 후, 수정 커밋·추가 회귀시험 이름/출력·최신 안전한 사본을 회신해 주세요. 이를 다시 독립 검수하겠습니다. 이 보고에는 실제 종목·원 가격·CSV·비밀값을 넣지 않았고, 실전 제출이나 메인 저장소 변경도 하지 않았습니다.
