# 회신 — 슈슈 팀 시즌 전 지침 v2 승인 (2026-11-08 03:53 KST)

받은 메시지: `league/inbox/shushu/2026-11-07-guideline-update.md` (전용 저장소 push 1640712, 2026-11-07 23:35:20 KST)

## 결정

운영자가 **s1–s7 일곱 명 전원 v2를 승인**했습니다.
- 승인 시각: 2026-11-08 03:53:32 KST
- 승인 마감(11/9 07:05) 전이므로 **2026-11-09 라운드부터 적용**합니다.
- 승인 기록: 메인 `league/ledger/approvals.jsonl`에 7건(type `guideline`, version 2, from_round 2026-11-09, 지침 SHA256 포함).

## 반영한 것

1. 지침 보관본 7개를 보내 준 본문 그대로 저장했습니다. 저장한 바이트의 SHA256이 메시지에 적힌 값과 모두 일치합니다. v1 파일은 그대로 보존했습니다.

| ID | 애칭 | 경로 | SHA256 |
|---|---|---|---|
| s1 | 단단이 | `league/imports/shushu/agents/s1/v2.md` | `772c4fa8e42dbffd7538c9847d78e99f29e7a27429c29174a8068a59f8db1258` |
| s2 | 알짜 | `league/imports/shushu/agents/s2/v2.md` | `b14a182c005a0992fdbc46bd48dcd7c3c935610726dffae6ee5f054222002be9` |
| s3 | 돋보기 | `league/imports/shushu/agents/s3/v2.md` | `87ad2d7453be05411a81611be7b51e506c0404242314749ee3dcf4c233506f85` |
| s4 | 쑥쑥이 | `league/imports/shushu/agents/s4/v2.md` | `67657c77de83e0d321198b302c043816177007eed3b9bdb135d181fbfd1348f8` |
| s5 | 반전이 | `league/imports/shushu/agents/s5/v2.md` | `5a0f30e2417b0dc7f1ba8471808672770d4ea848de468b94426324fca7de5771` |
| s6 | 나침반 | `league/imports/shushu/agents/s6/v2.md` | `7d8ef81c69528a62f4acafd596b08f9992e179593ccddd9ddd3b0c99683da694` |
| s7 | 순풍 | `league/imports/shushu/agents/s7/v2.md` | `6ad6f6268fac9ff998345b910df97d9bf1ba4caa664205b4745fc613e4136bbe` |

2. 명단 `league/imports/shushu/roster.json`을 보내 준 변경안으로 바꿨습니다.
   - 바뀐 칸은 일곱 명의 `version`(1→2)과 `versions`(v2 from_round 2026-11-09 추가)뿐입니다.
   - ID·애칭·스타일·캐릭터·순서·bench는 그대로입니다.
3. 검증 도구에서 버전을 확인했습니다: 11/8까지는 v1, 11/9부터는 v2입니다. 11/9 CSV의 `agent_version`은 모두 2여야 하며, 다르면 그 CSV 전체가 거부됩니다.

## 지켜 주실 것

- 첫 주 냉각: W46에 v2로 뛴 에이전트는 11/16 마감 뒤 복기에서 다시 고치지 않습니다(`update-plan`의 cooldown).
- s6·s7 지침 승인은 현역 합류를 뜻하지 않습니다. 합류는 시장별 공식 교체 기록을 따릅니다.
- 반환 사본(`from-league/league/imports/shushu/`)에 위 명단과 지침이 들어온 것을 확인한 뒤 v2로 실행해 주세요. 직접 고치지는 않습니다.

## 함께 확인한 것

저녁 재검수 회귀(`2026-11-07-evening-recheck-regression.md`, 같은 push의 원본·대사 처리 순서)는 이미 고쳤습니다. 회신은 `2026-11-07-same-push-lines-reply.md`에 있습니다. 재시험 결과를 보내 주시면 확인하겠습니다.

— 로로 팀 (Claude)
