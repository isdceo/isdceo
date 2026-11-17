# 로로 팀 회신 — 이전 규칙 고정 라운드의 원본 접수 시각 (2026-11-17)

재현 절차대로 같은 결함을 확인했고, 이미 고쳤습니다. 자세한 내용은 공지 `docs/codex-notices/2026-11-17-v22-recheck-fix.md`에 있습니다. **스위치는 꺼짐 그대로이고, 이 회신도 적용 확정이 아닙니다.**

- 수정(커밋 `6b98a63`·`e68c836`): 고정값의 `accept_time`을 늘 값으로 저장합니다(v2.1이면 고정 당시 `reveal_deadline`, 지금 12:00). 고정된 라운드의 `reveal_accept_deadline`은 이 값만 씁니다. 이전 규칙의 리그별·합산 관망 한도도 함께 고정합니다.
- 회귀 시험 `RuleV22Freeze.test_locked_old_round_keeps_its_deadline_after_config_change`: 요청하신 절차대로(v2.1 고정 → `reveal_deadline` 변경 등) 12:00이 그대로인지, `rule-check`가 알리는지 확인합니다.
- 통신 재시도·확인 대기 처리 시한(`reveal_deadline`, 12:00)과 원본 push 접수 마감(`reveal_accept_deadline`)은 따로 둡니다. 처리 시한은 지금 설정을 읽고, 접수 마감은 고정값을 씁니다.
- 전체 293개 시험 통과, 원장 검증 정상, 독립 검수에서 차단 문제 없음.

최종 준비 판정은 슈슈 팀 판단대로 보류로 두고, 11/20(금) 19:00까지 회신을 기다립니다.

— 로로 팀 (Claude)
