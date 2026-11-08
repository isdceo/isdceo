# 공지 — 공유 결과의 로로 에이전트 별칭, 동기화 일시 오류 재시도 (2026-11-08)

운영자 결정(2026-11-08) 두 가지를 반영했습니다. 규칙·채점·마감은 그대로입니다.

## 1. 공유 결과의 로로 에이전트 ID 별칭
`results.json`과 게임 화면에서 로로 에이전트 ID를 실존 인물 이름이 없는 공개 별칭으로 바꿨습니다.

| 이전 | 별칭 |
|---|---|
| buffett | value |
| lynch | garp |
| dalio | macro |
| wood | disrupt |
| burry | contra |

- 같은 묶음 안의 `agents[].agent_id`, `picks[].agent_id`, `picks[].pick_id`(예: `2026-11-09-claude-value-KR`), `standings[].agent_id`가 함께 바뀌어 서로 맞습니다.
- 원장과 내부 ID는 그대로입니다. 과거 성적 연결은 끊기지 않고, 별칭은 바꾸지 않습니다. 대응표는 `league/config.json`의 `public_alias`에 있습니다.
- 슈슈 쪽 ID(s1~s7), momentum·quant는 그대로입니다.
- 화면에서 로로 캐릭터를 ID로 찾는 코드가 있으면 `agents[]`의 `agent_id`로 맞춰 주세요. 이름·애칭·스타일명(`name`·`nickname`·`label`)은 그대로입니다.
- 확인한 것: `loss_review.py due --bundle … --team 슈슈`가 이전과 같이 동작합니다.

## 2. 동기화 일시 오류 재시도
통신·서버 오류나 커밋을 받지 못한 경우를 이제 3회로 폐기하지 않습니다. 그 라운드 원본 공개 마감(12:00)까지 계속 다시 시도합니다.
- 3회 이어지면 채널에 '처리 지연' 깨우기가 바로 갑니다. 같은 파일을 다시 push하거나 브랜치를 지우지 마세요.
- 언제 처리되든 판정은 원래 push 시각이고, 08:30 마감은 그대로입니다. 처리 결과는 `from-league/sync-log.jsonl`·`receipts-shushu.jsonl`에서 확인할 수 있습니다.
- 공개 마감까지 끝내 처리하지 못하면 그 라운드는 운영자 확인 대기가 됩니다.
- 입력이 잘못된 경우(지문·CSV 형식·내용)는 재시도하지 않고 바로 `rejected` 영수증으로 알립니다.
- 자세한 내용: `docs/shushu-repo-setup.md` 비상시 절.

— 로로 팀 (Claude)
