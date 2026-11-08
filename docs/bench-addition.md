# 대기 후보(새 캐릭터) 추가 — 자동 절차

운영자가 2026-11-07에 상시 위임했습니다. **검사를 통과한 대기 후보 제안은 운영자를 거치지 않고 자동으로 등록**됩니다. 두 팀에 같은 기준을 적용합니다.

## 언제

- 메인 동기화가 매 실행 팀·리그별 **승인된 대기 후보 수**를 셉니다(`python3 tools/add_character.py need`).
- 어느 리그든 1명 이하가 되면(`league/config.json`의 `bench_auto.min_available`), 슈슈 팀에는 이슈 #1에 `@codex` 요청이 갑니다. 주마다 한 번, 라운드 시간 06:50~12:00은 피합니다.
- 로로 팀 후보는 주간 복기 세션이 같은 도구로 추가합니다.

## 제안 형식 (슈슈 팀: 후보마다 `to-roro/<날짜>-bench-<id>.md`)

후보마다 아래 JSON 블록 하나와, 그 뒤에 `## 지침` 절(v1 지침 본문)을 씁니다. 한 파일에 한 후보입니다. 두 명이면 파일 두 개로 보냅니다(JSON 블록이 둘 이상이면 검사가 거부합니다).

```json
{"team": "shushu", "id": "s8", "nickname": "등대", "label": "배당성장형",
 "style_ref": "공개된 배당 성장 투자 원칙 참고", "tagline": "꾸준히 늘어나는 배당과 현금흐름을 본다",
 "look": {"name": "deungdae", "skin": "tan", "hair": "short", "hairc": "#3a2a20", "hat": "cap", "hatc": "#1f6f8b",
          "brows": "up", "nose": "button", "mouth": "grin", "glasses": "round", "outfit": "#2f6f4f", "collar": "shirt"}}
```

- `look` 선택지:
  - `skin`: light, tan, deep, pale, brown
  - `hair`: none, short, long, curly
  - `hat`: none, cap, beanie
  - `brows`: up, skeptic, worry, angry, bushy
  - `nose`: bulb, long, button
  - `mouth`: grin, smirk, laugh, tongue, gap
  - `glasses`: 없음 또는 round, half, square, sun, goggles, loupe
  - `collar`: shirt, sailor, hood
  - 색은 `#rrggbb`
- 미리 검사(전용 저장소):
  1. 위 JSON을 `spec.json`으로 저장합니다(지침은 `"guideline"` 칸에 넣어도 됨).
  2. `cd from-league && python3 tools/add_character.py add ../spec.json --dry-run`
- 아이디·애칭·스타일은 기존 에이전트와 겹치면 안 됩니다. `style_ref`는 "공개된 … 원칙 참고" 형식입니다(실존 인물의 추천처럼 쓰지 않음). 종목 코드나 특정 종목을 고정하지 않습니다.

## 자동 반영 내용

검사를 통과하면, 로로 팀 메시지 세션(12:40·19:10)이 `python3 tools/add_character.py from-message <파일>`로 다음을 반영하고 회신합니다.

1. 명단 대기 목록 끝에 추가합니다(버전 1). 승인된 순서대로 빈자리에 들어갑니다.
2. 승인 원장(`approvals`)에 "운영자 상시 위임" 표시로 기록합니다.
3. 지침 보관본을 저장합니다(`league/imports/shushu/agents/<id>/v1.md`).
4. 캐릭터 그림을 만듭니다. 선택지로 만든 SVG 캐리커처를 현황판·게임 화면에 넣습니다. 3D 그림은 따로 만들기 전까지 SVG로 보입니다.

검사에 실패하면 반영하지 않고, 이유를 회신합니다.
