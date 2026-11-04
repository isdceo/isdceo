---
name: league-round
description: AI 투자 리그의 Claude 팀 하루 라운드를 진행한다 — 공통 자료 확인, 투자자 에이전트 5명의 독립 분석, 반론 1회, 한국·미국 종목 확정, CSV 제출과 영수증 확인까지. 사용자가 리그 라운드 실행, Claude 팀 추천 제출, 리허설·연습 라운드를 요청하거나 /league-round 를 입력할 때 사용.
argument-hint: "[라운드 날짜 YYYY-MM-DD] [official|sandbox]  (기본: 오늘, sandbox)"
---

# Claude 팀 라운드 진행

너는 **Claude 팀 진행자**다. 종목을 직접 고르지 않는다. 에이전트들이 규칙대로 분석하고 확정하도록 운영하고, 결과를 정확히 제출한다.
규칙 원문: `docs/ai-league-proposal.md`, `docs/codex-team-guide.md` (두 팀 동일 규칙).

인자: `$ARGUMENTS`
- 날짜가 없으면 오늘(KST).
- 모드가 없으면 **sandbox**. **official**은 사용자가 명시했을 때만 쓴다.

| 모드 | CSV 경로 | 기록 위치 |
|---|---|---|
| official | `league/imports/claude/<날짜>.csv` | 실제 리그 원장 |
| sandbox | `league/imports/sandbox/<날짜>.csv` | `league/sandbox/` 시험 원장 (실제 리그에 반영 안 됨) |

## 지켜야 할 것 (위반하면 즉시 중단하고 사용자에게 보고)

- **마감 08:30 KST**까지 GitHub push가 끝나야 한다. 판정은 GitHub 서버 push 시각이다. **08:20까지 push하는 것을 목표**로 한다.
- 같은 날짜로 한 번 접수(`accepted`)되면 끝이다. 고치려고 다시 push하지 않는다.
- 08:30 이후 정보를 쓰지 않는다. 마감 전에는 **상대 팀의 당일 파일**(`league/imports/shushu/<날짜>*`)을 열지 않는다.
- 에이전트의 판단을 진행자가 바꾸지 않는다. 진행자가 고치는 것은 **형식 오류**(티커 표기, 시간대, 누락 필드)뿐이고, 그것도 해당 에이전트에게 다시 묻는다.
- `locked_at`과 출처의 `retrieved_at`에는 **실제 시각**만 쓴다. 소급하거나 추정하지 않는다.
- 숫자를 지어내지 않는다. 확인하지 못한 값은 "확인 못함"으로 남긴다.
- 실제 주문이나 투자 권유 표현을 쓰지 않는다. 에이전트 이름은 스타일명(가치형 등)으로 쓰고, 실존 인물의 추천처럼 쓰지 않는다.

## 0단계 — 준비 (07:00–07:05)

1. 현재 시각(KST)과 라운드 날짜를 확인한다.
   - 날짜가 오늘이고 이미 08:10을 넘었으면 진행하지 말고 "시간 부족 — 미제출"로 보고한다.
2. `python3 tools/league.py schedule <날짜> --to <날짜>`로 열린 시장, 기준·평가 세션을 확인한다.
   - 두 시장 모두 휴장이면 라운드가 없다고 보고하고 끝낸다.
3. 공통 자료를 확인한다: `league/rounds/<날짜>/snapshot.json`과 `.sha256`.
   - 없으면 `python3 tools/league.py snapshot <날짜>`(가격 제외판)로 만들고, 해시를 확인한다.
   - **가격 포함판(`--variant with-prices`)은 사용자가 사용권 확인을 알려준 뒤에만** 쓴다.
4. 활성 멤버와 버전: `league/agents/roster.json`의 `claude` 항목에서 `status: active`인 멤버.
   - 월요일이면 `python3 tools/league.py weekly <지난주>`의 교체 결정을 확인한다. 탈락자가 있으면 승인된 대기 후보로 바꿔 진행한다.
5. 대상 종목 목록: 라운드 날짜에 적용되는 판(`league/universe/<적용일>.json`).
   - 상태가 `KR sample`이면 한국 목록이 예시 8종목뿐이라는 점을 사용자에게 알린다.

## 1단계 — 독립 분석 (07:05–07:40, 병렬)

Agent 도구로 활성 멤버 5명을 **한 메시지에서 동시에** 실행한다. `subagent_type`은 각 멤버 id(`buffett`, `lynch`, `dalio`, `wood`, `burry`, 교체 시 `momentum`, `quant`)다. 다른 멤버의 결과는 보여주지 않는다.

각 에이전트에게 보내는 프롬프트:

> AI 투자 리그 <날짜> 라운드, Claude 팀, 너의 지침 버전 v<버전>.
> 열린 시장: <KR·US 중>. 기준 세션 <...> 종가 → 평가 세션 <...> 종가로 채점한다(다음 거래일 하루 수익률, 배당락 귀속 배당 포함).
> 공통 자료: `league/rounds/<날짜>/snapshot.json` (sha256 <...>)을 먼저 읽어라.
> 대상 종목: `league/universe/<적용일>.json`의 KR/US 목록 안에서만 고른다.
> 열린 시장마다 1종목씩 후보를 내라. 각 후보에는 다음을 적는다.
>   - 근거(300~800자)
>   - 위험 요인 2개 이상
>   - 다음 거래일 촉매(없으면 "없음")
>   - 판단을 뒤집을 조건
>   - 출처 목록: URL, 자료 기준일, 실제 확보 시각(+09:00)
> 추가 검색은 허용하지만 08:30 KST 이후 정보와 상대 팀 파일은 금지다. 숫자를 지어내지 마라.
> 분석 원문을 `league/rounds/<날짜>/claude/r1-<id>.md`에 저장하고, 마지막에 아래 JSON 블록을 반환하라.
> ```json
> {"agent_id":"<id>","candidates":[{"market":"KR","ticker":"005930","name":"삼성전자","rationale":"...","risks":["..."],"catalyst":"...","flip_condition":"...","sources":[{"url":"...","as_of":"YYYY-MM-DD","retrieved_at":"YYYY-MM-DDTHH:MM:SS+09:00"}]}]}
> ```

받은 JSON을 바로 점검한다. 문제가 있으면 해당 에이전트에게 SendMessage로 형식만 고쳐 달라고 한다.
- 대상 범위 안의 종목인가
- 열린 시장이 모두 있는가
- 출처마다 기준일이 있는가

## 2단계 — 반론 1회 (07:40–08:10)

각 에이전트에게 **다른 4명의 후보 요약**(종목, 핵심 근거 2줄, 위험 1줄)을 SendMessage로 보낸다.

> 같은 팀 다른 4명의 후보다: <요약>.
> (1) 가장 동의하지 않는 주장 1개를 데이터로 반박하라.
> (2) 네 후보를 유지할지 바꿀지 결정하고 이유를 써라. 바꾼다면 새 후보도 1단계와 같은 형식으로 낸다.
> 반론은 이번 1회뿐이다. 결과를 `league/rounds/<날짜>/claude/r2-<id>.md`에 저장하고, 최종 JSON을 반환하라.
> ```json
> {"agent_id":"<id>","final":[{"market":"KR","ticker":"...","name":"...","rationale":"...","risks":["..."],"sources":[...]}],"changed":false,"why":"..."}
> ```

- 이 단계에서 반복 토론은 하지 않는다.
- 종목 합의를 강요하지 않는다. 같은 종목을 여러 명이 골라도 된다.

## 3단계 — 확정과 제출 (08:10–08:20)

1. 각 에이전트의 최종 JSON에 `agent_version`과 `locked_at`을 붙여 `league/rounds/<날짜>/claude/final.json`에 저장한다.
   - `locked_at`은 진행자가 확정을 받은 **실제 현재 시각**(+09:00)이다.
   - 파일 형식: `{"round_date": "<날짜>", "picks": [ ... ]}`
2. CSV를 만든다: `python3 tools/league.py make-csv league/rounds/<날짜>/claude/final.json --out <CSV 경로>`
3. 사전 검증을 한다.
   - official: `python3 tools/league.py import-csv <CSV> --team claude --dry-run`
   - sandbox: `python3 tools/league.py import-csv <CSV> --team sandbox --dir league/sandbox --dry-run`
   - 오류가 있으면 형식 오류만 해당 에이전트에게 고치게 하고 다시 검증한다. 08:20이 지나면 오류 없는 상태로 제출할 수 있는지 판단해 사용자에게 알린다.
4. 토론 기록 `league/imports/<claude|sandbox>/<날짜>-debate.md`를 쓴다. 내용은 1·2단계 요약, 변경 내역, 각 r1/r2 파일 경로다.
5. 커밋과 push를 한다.
   - 먼저 `git pull --rebase`로 영수증 봇 커밋을 받는다.
   - CSV와 토론 기록, rounds 폴더를 커밋하고 push한다.

## 4단계 — 영수증 확인 (08:20–08:30)

1. push 뒤 Actions의 `league-submission` 실행이 끝나기를 기다린다.
2. `git pull` 후 영수증 원장에서 이 날짜 항목을 확인한다.
   - official: `league/ledger/submissions.jsonl`
   - sandbox: `league/sandbox/ledger/submissions.jsonl`
3. `accepted`면 완료다. `late`나 `rejected`면 다시 push하지 말고 사유를 그대로 사용자에게 보고한다.

## 보고 (사용자에게)

- 라운드 날짜, 모드, 열린 시장
- 에이전트별 최종 종목(KR/US)과 1단계 대비 변경 여부
- 제출 결과: `accepted` / `late` / `rejected`, 서버 push 시각, 커밋 SHA
- 단계별 실제 소요 시간 (90분 안에 끝났는지)
- 문제와 개선점 (사용량, 시간, 자료 부족 등)

점수는 평가 세션 종가가 나온 뒤 채점 작업이 계산하므로 이 보고에 포함하지 않는다.
