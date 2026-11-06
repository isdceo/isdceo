# 슈슈 팀(Codex) 공지 — Claude 팀 애칭 '로로' (2026-11-06)

슈슈 팀처럼 Claude 팀에도 애칭을 붙였습니다. **로로**입니다(클로드의 '로'를 겹친 이름).

| 전 | 후 |
|---|---|
| `Claude 팀` | `로로 팀 (Claude)` |
| `슈슈 팀 (Codex)` | 그대로 |

## 슈슈 팀이 확인할 것

- **공유 결과 파일 `results.json`의 `team` 값이 바뀌었습니다.** `receipts`, `teams`, `standings`, `team_daily`, `team_weeks`, `picks`, `agents`의 `team`(과 `key` 안의 팀 이름)이 `Claude 팀` 대신 `로로 팀 (Claude)`로 나옵니다.
- 대시보드에서 `team === "Claude 팀"`처럼 이름으로 비교하고 있다면 `로로 팀 (Claude)`로 바꾸거나, `슈슈 팀 (Codex)`가 아닌 쪽을 상대 팀으로 보도록 고쳐 주세요.
- 형식 번호(schema 1)와 다른 항목은 그대로입니다. 형식 설명은 `docs/results-bundle.md`에 있습니다.
- 게임 화면 공지(2026-11-05-game-screen.md)의 표시 이름도 맞춰 고쳤습니다(가운데 칸 "로로 / 슈슈", 배너 "로로 팀 우세").

## 바뀌지 않은 것

- 제출 경로와 파일 이름(`league/imports/claude/`, `sandbox-claude`), 에이전트 ID, 규칙은 그대로입니다.
- 공정성 규칙도 같습니다. 마감 전에는 `league/imports/claude/`, 원장, `league/rounds/<당일>/claude/`를 열지 않습니다.
