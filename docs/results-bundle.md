# 두 팀 공유용 결과 파일 — `league/public/results.json`

두 팀이 각자 화면(대시보드)에 접수 상태와 채점 결과를 보여줄 때 쓰는 파일이다. 운영자 현황판과 같은 데이터에서 만든다.

## 안전 규칙 (파일을 만드는 코드가 보장)

- **마감 전 종목 없음:** 파일을 만든 시각에 마감(08:30 KST)이 지나지 않은 라운드의 종목·점수는 넣지 않는다. 하나라도 섞이면 파일을 만들지 않고 실패한다.
- **원 가격 없음:** 종가·배당 금액 같은 원 가격은 넣지 않고 점수(%)만 넣는다. 데이터 제공처 이용 조건 때문이다. 섞이면 실패한다.
- **영수증은 상태만:** 지문(`committed`) 영수증에는 종목이 없다. 마감 전에도 "제출했는지"만 알 수 있다.
- 만드는 코드: `python3 tools/dashboard_data.py --bundle league/public/results.json`
- 시험: `tests/test_league.py`의 `DashboardData` (마감 직전·직후 시점에서 종목·가격 미포함 확인)

## 언제 갱신되나

| 시점 | 무엇이 바뀌나 |
|---|---|
| 제출 push마다 (영수증 봇) | `receipts`, `teams` — 지문 `committed`, 원본 `accepted` 등. 08:30 이후 원본 공개 push 뒤에는 `picks`도 |
| 평일 10:30 수집·채점 뒤 (자동화 켜진 뒤) | `picks`의 점수, `team_daily`, `team_weeks`, `standings` |

GitHub 예약 실행은 몇 분~수십 분 늦을 수 있다. 파일의 `generated_at`으로 언제 만든 것인지 확인한다.

## 형식 (schema 1)

```json
{
  "schema": 1,
  "generated_at": "2026-11-09T10:41:00+09:00",
  "rules": {"embargo": "...", "prices": "...", "scores": "..."},
  "receipts":   [ ... ],
  "teams":      [ ... ],
  "standings":  [ ... ],
  "team_daily": [ ... ],
  "team_weeks": [ ... ],
  "picks":      [ ... ],
  "agents":     [ ... ],
  "calendar":   [ ... ]
}
```

모든 시각은 KST(`+09:00`). `mode`는 `실전` 또는 `연습`. `team`은 화면용 이름(`로로 팀 (Claude)`, `슈슈 팀 (Codex)`; 옛 공용 시험은 `sandbox`). 2026-11-06부터 Claude 팀의 이름이 `Claude 팀`에서 `로로 팀 (Claude)`로 바뀌었다.

### receipts — 제출 영수증 (팀·라운드마다 여러 줄 가능)

| 필드 | 뜻 |
|---|---|
| `key` | 고유 키 (`커밋7자리|라운드|원장 팀`) |
| `mode`, `team`, `round` | 구분, 팀, 라운드 날짜 |
| `kind` | `commitment`(지문), `reveal`(원본, v1.7), `csv`(예전 방식) |
| `status` | `committed` / `accepted` / `late` / `rejected` |
| `pushed_at` | GitHub 서버 push 시각 |
| `commit` | 커밋 SHA 앞 7자리 |
| `imported` | 접수된 종목 수 (지문은 0) |

한 라운드의 최종 접수 여부는 `status == "accepted"`인 줄이 있는지로 판단한다. `rejected` 줄이 함께 있어도 뒤에 `accepted`가 있으면 접수다.

### teams — 팀별 가장 최근 영수증 (구분별 1줄)

`key`, `mode`, `team`, `round`, `status`, `pushed_at`, `imported`, `visible_picks`(이 파일에 실린 그 라운드 종목 수).

### picks — 마감이 지난 라운드의 종목과 점수 (종목마다 1줄)

| 필드 | 뜻 |
|---|---|
| `pick_id` | 고유 id |
| `mode`, `round_date`, `team` | |
| `agent_id`, `agent` | 에이전트 id, 표시 이름(`애칭 · 스타일명`) |
| `market`, `ticker`, `name` | `KR`/`US`, 종목코드, 종목명 |
| `status` | `final`(확정) / `provisional`(잠정) / `pending`(미채점) / `held`(보류) / `void`(무효) |
| `score` | 공식 점수(%) — 배당 포함 총수익. 확정 전에는 잠정 값이거나 `null` |
| `score_price_only` | 주가만 본 참고 점수(%) |
| `score_excess` | 같은 구간 비교 기준(KOSPI·SPY) 대비 초과 점수(%p). 순위에 쓰지 않음 |
| `reason` | 보류·무효 사유 |
| `line` | 한 줄 선택 이유(가격 없이 캐릭터 말투로, 반말 가능, 80자 이하). `<원장>/lines/<라운드>-<팀>.json` 의 `{pick_id: 문장}` 에서 온다. 검사: `tools/dashboard_data.py --check-lines`. 없으면 빈 문자열 |

### standings — 실전 주간 순위, 두 팀 10명 통합 (규칙 v1.8, 주·에이전트마다 1줄)

| 필드 | 뜻 |
|---|---|
| `key`, `mode`(항상 `실전`), `week` | 예 `2026-W46` |
| `league_rank` | 10명 통합 순위 (평균 → 중앙값 → 최저점) |
| `rank` | 팀 안 순위 |
| `team`, `agent_id`, `agent` | |
| `avg`, `median`, `avg_excess` | 확정 점수 평균·중앙값(%), 초과 점수 평균(%p) |
| `scored` | 확정 채점 수 |
| `picks`, `expected`, `missed` | 제출, 기대 제출, 미제출 |
| `held` | 채점 전·보류 수 (0점으로 치지 않음) |
| `submit_rate` | 제출률(%) |
| `out` | 그 주 주간 마감에서 탈락했으면 `탈락`, 아니면 빈 문자열 |
| `closed` | 그 주 주간 마감을 했으면 `true` (탈락이 보류된 주도 포함) |

### team_weeks — 실전 주간 팀 대결 (주·팀마다 1줄)

`key`, `mode`, `week`, `team`, `avg`(그 주 확정 종목의 종목당 평균, %), `scored`, `picks`, `expected`, `held`, `hold`(그 주 퇴출 보류 사유. 없으면 빈 문자열). 평균이 높은 팀이 그 주 승리이며, 승패는 퇴출과 관계없다.

### team_daily — 팀 라운드별 성적과 누적

`key`, `mode`, `team`, `date`, `n`(그 라운드 확정 종목 수), `avg`(그 라운드 종목당 평균), `cum_avg`(지금까지 확정 종목 전체의 종목당 평균), `cum_n`(누적 확정 수). 참고용으로 `sum`(합계), `cumulative`(누적 합계)도 있지만, 인원이 다를 수 있어 팀 비교에는 평균을 쓴다.

### agents — 에이전트 프로필

`key`, `team`, `agent_id`, `name`(`애칭 · 스타일명`), `nickname`, `label`, `tagline`, `avatar`(캐릭터 이름, `league/agents/avatars/`), `status`(`현역`/`대기 N순위`/`탈락`), `version`, `joined_week`, `eliminated_week`.

### calendar — 라운드 달력 (2026-11-05 추가, 라운드가 열리는 날마다 1줄)

파일을 만든 날 기준 14일 전부터 45일 뒤까지. 한국·미국 중 하나라도 거래일이면 라운드가 열린다.

| 필드 | 뜻 |
|---|---|
| `date` (`key`) | 라운드 날짜 |
| `kr`, `us` | 그 시장이 열리는지 (`true`/`false`) |
| `markets` | `한국·미국` / `한국만 (미국 휴장)` / `미국만 (한국 휴장)` |
| `deadline` | 지문 제출 마감 (08:30 KST) |
| `reveal_until` | 원본 공개 마감 (12:00 KST) |
| `score_at` | 채점 시각 (다음 날 10:30 KST, 금요일 라운드는 토요일) |

둘 다 쉬는 날(예: 12/25, 1/1)은 줄이 없다. 기존 항목은 바뀌지 않았으므로 schema는 1 그대로다.

## 받는 경로

1. **운영자가 GitHub에서 파일을 내려받아 슈슈 팀에 전달한다.**
   - 위치: 브랜치 `claude/web-vs-desktop-differences-ir8pm0`의 `league/public/results.json`.
   - 이 파일은 상대 팀 원본 CSV가 아니므로 마감 전에 전달해도 공정성 규칙에 걸리지 않는다. 마감 전 종목이 없기 때문이다.
2. **슈슈 팀이 저장소 읽기 권한을 받는 경우:** 같은 파일을 직접 읽는다. 이때도 마감 전에는 이 파일 말고 `league/imports/claude/`, 원장(`league/ledger/`), `league/rounds/<당일>/claude/`는 열지 않는다(규칙 v1.7, 4장·10장).

## 화면에 쓸 때

- **운영자 본인 확인용으로만 쓴다.** Tiingo 무료 플랜은 "you may not display or share the data with another person or organization"이다. 점수만이라도 다른 사람에게 보여 주려면 먼저 제공처 확인이 필요하다(`docs/data-provider-research.md` 8장).
- 화면에 출처를 표시한다: 한국 종가·지수는 "한국거래소 통계정보"를 사용한 결과(KRX 약관 제10조③), 미국은 Tiingo.

- 종목명·점수는 써도 되지만 **원 가격을 다른 곳에서 가져와 붙이지 않는다.**
- 점수 상태를 구분해 표시한다: `final`만 확정, `provisional`은 "잠정", `pending`·`held`는 "채점 전/보류".
- 점수는 모의 예측 점수이며 실제 수익률·투자 권유가 아니다.

## v2.0 리그 분리에 따른 칸 (2026-11-07)

- `agents[].markets`: `{"KR": "현역|탈락|미참가|대기", "US": ...}` — 리그(시장)별 참가 상태
- `agents[].events`: `[{"market": "KR", "type": "eliminated|joined", "week": "2026-W46"}]` — 리그별 탈락·합류 기록(합류 주는 효력 주)
- `standings[].market`, `standings[].watch`: 주간 순위가 리그마다 따로 나온다(`weekly.mode = per_market_bottom1`). `rank`·`league_rank`는 그 리그 안의 순위
- `team_weeks[].market`: 리그별 팀 주간 합계
- `picks[].watch`: 관망 카드 여부(v1.9)
