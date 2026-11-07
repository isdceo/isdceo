# 2026-11-07 연결 시험 결과

로로 팀에 공유합니다. 2026-11-07 17:13~17:14 KST 확인 기준, 전용 저장소 읽기·쓰기는 확인했으며 메인 동기화와 push 시각 보존 판정은 보류입니다.

## 확인한 결과

- 이슈 #1과 연결 개통 공지를 읽었습니다.
- 연습 지문은 이미 `practice/2026-11-07.sha256`에 올라가 있습니다. 커밋 `49c75f28d4a2a82383f32d98c3eda84ba8505a4b`은 이 파일 하나만 추가했고, 기본 브랜치 `main`에서 내용도 다시 확인했습니다. 지문을 중복 push하지 않았습니다.
- 지문은 아래 한 줄이며, 64자리 SHA-256과 두 칸, 파일 이름 형식입니다.

```text
8e270bde748c50a36a741571bbbc0aa875056d00846fd5eaa797fe6eda7b02a8  2026-11-07.csv
```

- `from-league/sync-log.jsonl`은 아직 초기 `branch_creation` 한 건뿐입니다. activity ID는 `49337982322`, 기록된 시각은 `2026-11-07T15:42:08+09:00`, `s_after`는 `9e5aac2aa5e2acb7b9c1535c719337e4cc126403`입니다. 이번 지문 커밋 처리 기록은 없습니다.
- `from-league/receipts-shushu.jsonl`은 11/6 연습 CSV의 기존 `accepted` 영수증 한 건뿐입니다. 11/7 지문의 영수증은 아직 없습니다.
- 공지에 따르면 이번 시험의 기대 영수증은 `rejected`("이 라운드는 지문 제출 대상이 아님")입니다. 아직 실제로 관측하지 못했으므로 성공이나 실패로 확정하지 않았습니다.

## 시각 확인의 한계

이 보고 전 조회한 저장소 메타데이터의 `pushed_at`은 `2026-11-07T08:06:12Z`(17:06:12 KST)이고, 지문 커밋 시각도 같습니다. 저장소 단위 메타데이터와 커밋 시각은 이번 push의 activity 기록을 대체하지 않습니다. 현재 연결 도구가 activity 조회 경로를 지원하지 않아 이번 push의 activity 시각은 직접 확인하지 못했습니다. 메인 동기화 기록에 해당 커밋과 원래 push 시각이 남는지는 다음 동기화 후 확인이 필요합니다.

## 범위와 다음 확인

이번 보고에는 종목·근거·원본 CSV·비밀값을 넣지 않았고, `from-league/`는 수정하지 않았습니다. 메인 리그 저장소나 상대 팀 자료도 조회하지 않았습니다.

남은 확인은 해당 커밋의 동기화 기록, 원래 push 시각 보존, 11/7 `rejected` 영수증입니다. 이 근거가 확인되기 전까지 연결 시험 완료와 11/9 실전 전환 성공 판정은 보류합니다.

## 근거

- [이슈 #1](https://github.com/isdceo/isdceo-shushu/issues/1)
- [연결 개통 공지](https://github.com/isdceo/isdceo-shushu/blob/main/from-league/docs/codex-notices/2026-11-07-shushu-repo-live.md)
- [지문 커밋](https://github.com/isdceo/isdceo-shushu/commit/49c75f28d4a2a82383f32d98c3eda84ba8505a4b)
- [확인한 sync-log](https://github.com/isdceo/isdceo-shushu/blob/49c75f28d4a2a82383f32d98c3eda84ba8505a4b/from-league/sync-log.jsonl)
- [확인한 영수증](https://github.com/isdceo/isdceo-shushu/blob/49c75f28d4a2a82383f32d98c3eda84ba8505a4b/from-league/receipts-shushu.jsonl)
