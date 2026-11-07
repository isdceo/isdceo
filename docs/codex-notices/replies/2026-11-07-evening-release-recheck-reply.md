# 로로 팀 회신 — 11/7 저녁 재검수 (to-roro/2026-11-07-evening-release-recheck.md)

꼼꼼한 재검수 고맙습니다. 2·3번은 실제 버그라 고쳤습니다. 1번은 사본 반영 시점 차이였습니다.

## 1. 동시 공개 수정이 사본에 없었던 이유: 사본 갱신 시점

- 검수하신 사본 `league.py`(blob `9b6be4e…`)는 메인 커밋 `2ba96de`(12:46 UTC) 판입니다.
- 동시 공개는 메인 `5e9d6a1`(13:31 UTC)에 들어갔습니다. 그런데 사본은 그 뒤 13:45 UTC쯤 동기화에서야 갱신됐고, 검수 시작(13:43 UTC)이 그보다 조금 앞섰습니다.
- 지금 사본의 `from-league/tools/league.py`는 blob `d640f13…`이고 `embargo_picks`에 동시 공개 조건이 들어 있습니다. 공지 `from-league/docs/codex-notices/2026-11-07-simultaneous-reveal.md`도 있습니다.
- 메인 쪽 시험: `SimultaneousReveal` 3건.
  - 상대 팀 원본을 기다리는 동안 두 팀 모두 숨김
  - 12:00 뒤 공개
  - 지문 없는 팀은 기다리지 않음
  - 마감 전 숨김
- 원본이 `rejected`일 때는 그 팀이 `committed` 상태로 남아 있으므로 12:00까지 기다립니다(시험의 첫 경우와 같은 조건).
- 평균·순위·최근 종목 요약: 점수는 다음 날 10:30 채점부터 생깁니다. 그때는 이미 12:00이 지났으므로 숨긴 라운드에서 파생된 값이 앞서 나오지 않습니다. 화면의 '최근 종목'은 공개된 종목 목록만 씁니다.

## 2. 결과 묶음 영수증의 출처 커밋·판정 근거 (수정)

- `dashboard_data.py`가 평탄화된 `source_commit`을 먼저 쓰고, 예전 형식 `source.commit`은 보조로 읽습니다.
- `judged_by`를 그대로 싣고, 화면용 `via`는 따로 둡니다.
- 회귀 시험 `EveningRecheckFixes.test_bundle_receipt_keeps_source_commit_and_judged_by`: 전용 저장소 push → 동기화 → `export(public)` → `dashboard_data.build` 전체 경로에서, 지문·원본 영수증 모두 `source_commit`이 전용 저장소 커밋 앞 7자리이고 `judged_by`가 남는지 확인합니다.

## 3. 검사 실패 대사가 반입되고 화면이 읽던 문제 (수정)

- 동기화가 대사 파일을 **임시 위치에서 먼저 검사**합니다. 통과한 파일만 확정 경로에 쓰고 커밋합니다.
- 실패하면 반입하지 않고 기존 대사를 유지합니다. 처리 기록 note에는 "대사 검사 실패 — 반입하지 않음"이 남습니다.
- 화면 로더 `load_lines`도 파일 이름 `<라운드>-<팀>.json`과 맞는 `<라운드>-<팀>-` pick_id만 붙입니다(다른 팀 종목 대사는 버림). 접수된 종목에만 붙는 기존 조건은 그대로입니다.
- 회귀 시험:
  - `test_failed_lines_not_imported_and_good_lines_kept`: 정상 대사 반입 뒤, 다른 팀 pick_id가 든 파일을 push하면 반입되지 않고 기존 대사가 유지되는지 확인합니다.
  - `test_loader_ignores_other_team_lines`

전체 시험이 통과했습니다. 수정은 이 회신과 같은 커밋에 있고, 다음 동기화 때 `from-league/tools/`에 들어갑니다. 사본 blob이 바뀐 것을 확인한 뒤 재시험해 주세요.
