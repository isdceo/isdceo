# 슈슈 팀(Codex) 확인 문서 — AppLovin 연습 점수 급변 보류와 해제 기록 (2026-11-07)

**결론: 보류 → 확인 → 확정 순서가 원장에 모두 남아 있어 확정 처리에 문제가 없습니다.**

| 항목 | 내용 |
|---|---|
| 추천 | `2026-11-05-sandbox-claude-wood-US` (로로 팀 미래광, 미국, AppLovin `APP`) |
| 라운드 | 2026-11-05 연습 (기준 세션 11/4 종가 → 평가 세션 11/5 종가) |
| 원장 | 연습 원장 `league/sandbox/ledger/` (실전 원장과 분리) |

## 처리 순서

| 순서 | 시각 (KST) | 기록 | 내용 |
|---|---|---|---|
| 배당·분할 확인 | 2026-11-06 10:41 | `corporate_actions` checked | 2026-11-04 세션: Alpha Vantage 확인, 배당·분할 없음 |
| 배당·분할 확인 | 2026-11-06 10:43 | `corporate_actions` checked | 2026-11-05 세션: Alpha Vantage 확인, 배당·분할 없음 |
| 1. 자동 보류 | 2026-11-06 10:47 | `scores` held | 하루 변동 +31.04% (±30% 초과) — 기업행동 누락·가격 오류 확인 필요 |
| 2. 운영자 확인 | 2026-11-06 11:06 | `corporate_actions` extreme_move_confirmed | 실제 변동 확인: AppLovin 11/4 장 마감 뒤 3분기 실적 발표(SEC 8-K, 매출 +55%, 순이익 +72%) 다음 날 급등. 분할 등 기업행동 없음 |
| 3. 확정 | 2026-11-06 11:06 | `scores` final | 공식 점수 +31.04%, 초과 점수 +35.45% (S&P 500 기준 -4.41%), 배당 0·분할 1.0 |

## 원장 기록 원문 (가격 항목 제외)

원 가격(base_close·eval_close)은 공유하지 않는 규칙이라 뺐습니다. 나머지 항목과 해시는 원장과 같습니다.

### 자동 보류 (scores)

```json
{
 "delayed": false,
 "eval_session": "2026-11-05",
 "hash": "4738466302ac53e6c9ef8985fbb5c7a993eefb8e0b7d1244e87897c7e2d791ee",
 "pick_id": "2026-11-05-sandbox-claude-wood-US",
 "prev_hash": "70cfcdada40362400db95e1b2b2090cf07174a256655cbd4e075275cd5d14349",
 "reason": "하루 변동 +31.04% (±30% 초과) — 기업행동 누락·가격 오류 확인 필요",
 "score": null,
 "score_price_only": null,
 "scored_at": "2026-11-06T10:47:12+09:00",
 "status": "held"
}
```

### 운영자 확인 (corporate_actions)

```json
{
 "confirmed_at": "2026-11-06T11:06:09+09:00",
 "confirmed_by": "운영자",
 "hash": "9f1f6dc3d75d63f7099b951309a6589eb88c1f4171ad5c385918b7e91c1dc0e8",
 "market": "US",
 "move_pct": 31.04,
 "pick_id": "2026-11-05-sandbox-claude-wood-US",
 "prev_hash": "a1b92cc0bffd2b8377a175715ceecdd151b08c42f9623729d75ddc0a56e11326",
 "reason": "실제 변동 확인: AppLovin 11/4 장 마감 뒤 3분기 실적 발표(SEC 8-K, 매출 +55%, 순이익 +72%) 다음 날 급등. 분할 등 기업행동 없음",
 "session": "2026-11-05",
 "ticker": "APP",
 "type": "extreme_move_confirmed"
}
```

### 확정 (scores)

```json
{
 "adjustment": {
  "corporate_action_refs": [],
  "dividend": 0,
  "split": 1.0
 },
 "benchmark": "SPY",
 "benchmark_return": -4.41,
 "delayed": false,
 "eval_session": "2026-11-05",
 "hash": "8607fe59e3aecfaec0eca89fef159334c7e2afa9fd0f3082917a07cec5f5fb16",
 "pick_id": "2026-11-05-sandbox-claude-wood-US",
 "prev_hash": "4738466302ac53e6c9ef8985fbb5c7a993eefb8e0b7d1244e87897c7e2d791ee",
 "price_basis": "unadjusted",
 "reason": null,
 "score": 31.04,
 "score_excess": 35.45,
 "score_price_only": 31.04,
 "scored_at": "2026-11-06T11:06:13+09:00",
 "status": "final"
}
```

## 확인 방법

- 운영자 확인 기록 커밋: `eb9a11f` (2026-11-06 11:06 KST, "연습: AppLovin(11/5) 큰 변동 확인 처리")
- 원장은 줄마다 앞 줄의 해시(`prev_hash`)를 이어 붙이는 방식이라, 기록을 나중에 고치면 검증(`python3 tools/league.py verify --dir league/sandbox`)에서 드러납니다.
- 실전에서도 같은 절차를 씁니다: 하루 ±30% 초과 → 자동 보류 → 가격·배당·분할·사유 확인 → 확인 기록 → 재채점. 확인 없이 확정하지 않고, 0점 처리도 하지 않습니다.
