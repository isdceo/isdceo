---
name: league-round
description: AI 투자 리그의 Claude 팀 하루 라운드를 진행한다 — 공통 자료 확인, 투자자 에이전트 5명의 독립 분석, 반론 1회, 한국·미국 종목 확정, 마감 전 지문 제출, 마감 뒤 원본 공개와 영수증 확인까지. 사용자가 리그 라운드 실행, Claude 팀 추천 제출, 리허설·연습 라운드를 요청하거나 /league-round 를 입력할 때 사용.
argument-hint: "[라운드 날짜 YYYY-MM-DD] [official|sandbox]  (기본: 오늘, sandbox)"
---

# Claude 팀 라운드 진행

너는 **Claude 팀 진행자**다. 종목을 직접 고르지 않는다. 에이전트들이 규칙대로 분석하고 확정하도록 운영하고, 결과를 정확히 제출한다.
규칙 원문: `docs/ai-league-proposal.md`, `docs/codex-team-guide.md` (두 팀 동일 규칙, v1.7).
보고와 기록은 모두 한국어로 쓴다.

인자: `$ARGUMENTS`
- 날짜가 없으면 오늘(KST).
- 모드가 없으면 **sandbox**. **official**은 사용자가 명시했을 때만 쓴다.

| 모드 | 제출 폴더 | 기록 위치 |
|---|---|---|
| official | `league/imports/claude/` | 실제 리그 원장 |
| sandbox | `league/imports/sandbox-claude/` | `league/sandbox/` 시험 원장 (실제 리그에 반영 안 됨) |

sandbox 모드에서는 공통 자료·분석 기록도 `league/rounds/` 대신 `league/sandbox/rounds/<날짜>/`에 둔다(`snapshot <날짜> --dir league/sandbox`). 아래 경로의 `league/rounds/`를 그렇게 바꿔 읽는다.

## 제출 방식: 지문 먼저, 원본 나중

`league/config.json`의 `commit_reveal.from`(2026-11-09) 이후 라운드는 다음 순서다.

1. 08:30 전: CSV 원본의 sha256 **지문 파일(`<날짜>.sha256`)만** push → 영수증 `committed`
2. 08:30~12:00: 원본 CSV, 토론 기록, `league/rounds/<날짜>/claude/` 폴더 push → 영수증 `accepted`

**마감 전에는 종목이 들어 있는 파일(CSV, debate.md, r1/r2/final.json, timing.json 등)을 커밋에 넣지도 push하지도 않는다.** 지문 커밋에는 `.sha256` 파일 하나만 들어간다.
`commit_reveal.from` 이전 날짜의 라운드(연습)는 예전 방식대로 08:30 전에 CSV를 바로 push한다.

## 지켜야 할 것 (위반하면 즉시 중단하고 사용자에게 보고)

- **official 모드는 별도 예약 세션에서 돈다.** 운영자가 슈슈 팀 CSV를 다루는 대화와 섞지 않는다. 이 세션에서 슈슈 팀 당일 파일이나 그 내용을 받았다면 진행을 멈추고 운영자에게 알린다.
- 마감 전에는 `league/imports/shushu/`, `league/imports/sandbox-shushu/`의 **라운드 날짜 파일**을 읽지 않는다. `git pull` 뒤에도 그 경로는 열지 않는다(Grep·Glob 대상에서도 제외). 상대 팀 `.sha256` 지문은 열어도 내용이 없지만, 열 이유도 없으니 열지 않는다. 자기 팀 영수증이 `committed` 이상이고 08:30이 지난 뒤에만 열람 가능.
- **마감 08:30 KST**까지 지문 push가 끝나야 한다. 판정은 GitHub 서버 push 시각이다. **08:20까지 지문 push를 목표**로 한다.
- 지문을 만든 뒤에는 CSV를 고치거나 다시 저장하지 않는다. 한 글자만 바뀌어도 원본이 지문과 맞지 않아 거부된다.
- 같은 날짜로 한 번 `committed`/`accepted`되면 끝이다. 종목을 고치려고 다시 push하지 않는다.
- 08:30 이후 정보를 쓰지 않는다.
- 에이전트의 판단을 진행자가 바꾸지 않는다. 진행자가 고치는 것은 **형식 오류**(티커 표기, 시간대, 누락 필드)뿐이고, 그것도 해당 에이전트에게 다시 묻는다.
- `locked_at`과 출처의 `retrieved_at`에는 **실제 시각**만 쓴다. 소급하거나 추정하지 않는다.
- 숫자를 지어내지 않는다. 확인하지 못한 값은 "확인 못함"으로 남긴다.
- 실제 주문이나 투자 권유 표현을 쓰지 않는다. 에이전트 이름은 스타일명(가치형 등)으로 쓰고, 실존 인물의 추천처럼 쓰지 않는다.

## 시간 기록 (모든 단계)

단계마다 시작·끝 **실제 시각**(`date -Iseconds`, KST)을 `league/rounds/<날짜>/claude/timing.json`에 남긴다. 추정해서 채우지 않는다.

```json
{"round_date": "<날짜>", "mode": "official|sandbox", "stages": [
  {"stage": "준비", "start": "...+09:00", "end": "...+09:00"},
  {"stage": "독립 분석", "start": "...", "end": "..."},
  {"stage": "반론 1회", "start": "...", "end": "..."},
  {"stage": "확정·CSV·검증", "start": "...", "end": "..."},
  {"stage": "지문 push", "start": "...", "end": "...", "receipt": "committed"},
  {"stage": "원본 공개", "start": "...", "end": "...", "receipt": "accepted"}],
 "notes": ["사용량 경고, 재시도, 지연 사유 등"]}
```

이 파일도 종목 정보와 같은 폴더에 있으므로 08:30 이후에 push한다.

## 사용량 한도·장애

- 에이전트 실행이 사용량 한도나 오류로 멈추면 **같은 에이전트를 한 번만** 다시 실행한다. 그래도 안 되면 그 에이전트는 제외하고 나머지로 진행한다(빈 시장 행은 만들지 않는다 — 그 에이전트는 미제출).
- 팀 전체가 08:20까지 지문을 만들 수 없으면 시도를 멈추고, 사용자에게 사유를 보고하고 `python3 tools/league.py outage <날짜> --team claude --reason <사유>` 기록 여부를 묻는다. 예약 세션이라 답을 못 받으면 기록하지 않고 보고만 남긴다.
- 원인을 `timing.json`의 `notes`에 그대로 적는다.

## 0단계 — 준비 (07:00–07:05)

1. 현재 시각(KST)과 라운드 날짜를 확인하고 `timing.json`에 "준비" 시작을 적는다.
   - 날짜가 오늘이고 이미 08:10을 넘었으면 진행하지 말고 "시간 부족 — 미제출"로 보고한다.
2. `python3 tools/league.py schedule <날짜> --to <날짜>`로 열린 시장, 기준·평가 세션을 확인한다.
   - 두 시장 모두 휴장이면 라운드가 없다고 보고하고 끝낸다.
3. 공통 자료를 확인한다: `league/rounds/<날짜>/snapshot.json`과 `.sha256`.
   - 없으면 `python3 tools/league.py snapshot <날짜>`(가격 제외판)로 만들고, 해시를 확인한다.
   - **가격 포함판(`--variant with-prices`)은 사용자가 사용권 확인을 알려준 뒤에만** 쓴다.
   - `disclosures`(DART 최근 14일 공시)의 상태와 건수를 확인한다. `not_configured`나 오류면 에이전트에게 "공통 자료 공시 없음"이라고 알린다.
   - 참고: KRX 전일 종가는 **08:00 KST 전후**에 공개된다(2026-11-05 확인). 07:00대에는 KRX에서 전일 종가를 받을 수 없으므로, 에이전트가 가격이 필요하면 공개 웹 자료에서 찾고 출처를 남긴다.
4. 지침 확인: `python3 tools/league.py guideline-check <날짜>`
   - 결과가 `unapproved_edit` 또는 `missing`이면 **진행하지 않고** 운영자에게 보고한다(승인 안 된 지침 수정).
   - 승인(PR 머지)된 새 버전은 이때 적용 시작일과 함께 자동으로 기록된다.
   - 실제 제출(official)일 때만 이 기록을 커밋한다(08:30 이후 원본 공개 커밋에 함께). 연습(sandbox)에서는 `--dry-run`으로 실행한다.
5. 활성 멤버와 버전: `league/agents/roster.json`의 `claude` 항목에서 `status: active`인 멤버. 주간 마감 기록이 반영된 명단은 `python3 tools/league.py export` 결과의 roster와 같다.
   - 월요일이면 `python3 tools/league.py weekly <지난주>`의 교체 결정을 확인한다. 탈락자가 있으면 승인된 대기 후보로 바꿔 진행한다.
6. 대상 종목 목록: 라운드 날짜에 적용되는 판(`league/universe/<적용일>.json`).

## 1단계 — 독립 분석 (07:05–07:40, 병렬)

Agent 도구로 활성 멤버 5명을 **한 메시지에서 동시에** 실행한다. `subagent_type`은 각 멤버 id(`buffett`, `lynch`, `dalio`, `wood`, `burry`, 교체 시 `momentum`, `quant`)다. 다른 멤버의 결과는 보여주지 않는다.

각 에이전트에게 보내는 프롬프트:

> AI 투자 리그 <날짜> 라운드, Claude 팀, 너의 지침 버전 v<버전>.
> 열린 시장: <KR·US 중>. 기준 세션 <...> 종가 → 평가 세션 <...> 종가로 채점한다(다음 거래일 하루 수익률, 배당락 귀속 배당 포함).
> 공통 자료: `league/rounds/<날짜>/snapshot.json` (sha256 <...>)을 먼저 읽어라.
> - 한국 종목의 실적·배당·분할·IR·자사주 같은 이벤트는 **먼저 공통 자료의 DART 공시(`disclosures`)로 확인**한다. 기사에만 있고 공시로 확인되지 않으면 "공시 미확인"이라고 쓴다.
> 대상 종목: `league/universe/<적용일>.json`의 KR/US 목록 안에서만 고른다.
> 열린 시장마다 1종목씩 후보를 내라. 각 후보에는 다음을 적는다.
>   - 근거(300~800자)
>   - 위험 요인 2개 이상
>   - 다음 거래일 촉매(없으면 "없음")
>   - 판단을 뒤집을 조건
>   - 출처 목록: URL, 자료 기준일(`as_of`), 실제 확보 시각(`retrieved_at`, +09:00)
> 출처 규칙:
>   - 기준일을 확인하지 못한 출처는 `as_of`에 "확인 못함"이라고 쓴다. 자료를 받은 날짜로 채우지 않는다. 월까지만 알면 `2026-10`처럼 아는 만큼만 쓴다.
>   - 확보 시각은 출처마다 따로 재지 않아도 된다. 여러 자료를 받은 직후 `date -Iseconds`로 실제로 잰 시각 하나를 공통으로 적어도 된다(실제 확보 시각과 같거나 늦은 상한값). 받기 전 시각이나 추정 시각은 쓰지 않는다.
> 추가 검색은 허용하지만 08:30 KST 이후 정보와 상대 팀 파일은 금지다. 숫자를 지어내지 마라.
> 분석 원문을 `league/rounds/<날짜>/claude/r1-<id>.md`에 저장하고, 마지막에 아래 JSON 블록을 반환하라.
> ```json
> {"agent_id":"<id>","candidates":[{"market":"KR","ticker":"005930","name":"삼성전자","rationale":"...","risks":["..."],"catalyst":"...","flip_condition":"...","sources":[{"url":"...","as_of":"YYYY-MM-DD 또는 확인 못함","retrieved_at":"YYYY-MM-DDTHH:MM:SS+09:00"}]}]}
> ```

받은 JSON을 바로 점검한다. 문제가 있으면 해당 에이전트에게 SendMessage로 형식만 고쳐 달라고 한다.
- 대상 범위 안의 종목인가
- 열린 시장이 모두 있는가
- 출처마다 `as_of`가 있는가("확인 못함" 허용), `retrieved_at`에 +09:00이 있고 지금보다 늦지 않은가

## 2단계 — 반론 1회 (07:40–08:05)

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

## 3단계 — 확정, 검증, 지문 push (08:05–08:20)

1. 각 에이전트의 최종 JSON에 `agent_version`과 `locked_at`을 붙여 `league/rounds/<날짜>/claude/final.json`에 저장한다.
   - `locked_at`은 진행자가 확정을 받은 **실제 현재 시각**(+09:00)이다.
   - 파일 형식: `{"round_date": "<날짜>", "picks": [ ... ]}`
2. CSV를 만든다: `python3 tools/league.py make-csv league/rounds/<날짜>/claude/final.json --out <제출 폴더>/<날짜>.csv`
3. 사전 검증을 한다.
   - official: `python3 tools/league.py import-csv <CSV> --team claude --dry-run`
   - sandbox: `python3 tools/league.py import-csv <CSV> --team sandbox-claude --dir league/sandbox --dry-run`
   - 오류가 있으면 형식 오류만 해당 에이전트에게 고치게 하고 다시 검증한다. 08:20이 지나면 오류 없는 상태로 지문을 낼 수 있는지 판단해 사용자에게 알린다.
4. 지문을 만든다: `python3 tools/league.py commit <CSV>` → 같은 폴더에 `<날짜>.sha256`. **이후 CSV를 건드리지 않는다.**
5. 지문만 커밋하고 push한다.
   ```
   git pull --rebase                       # 영수증 봇 커밋 받기 (상대 팀 당일 파일은 열지 않음)
   git add <제출 폴더>/<날짜>.sha256         # 이 파일 하나만
   git commit -m "league: claude <날짜> commitment"
   git push
   ```
   - `git status`로 CSV·rounds 폴더가 **커밋에 들어가지 않았는지** 확인한다(추적 안 된 상태로 남아 있어야 함).
   - `git pull --rebase`가 추적 안 된 파일 때문에 막히면 `git stash -u`로 잠시 치우고 pull한 뒤 `git stash pop`한다.
6. `timing.json`에 "지문 push" 시각을 적는다.

## 4단계 — 지문 영수증 (08:20–08:30)

1. push 뒤 Actions의 `league-submission` 실행이 끝나기를 기다린다.
2. `git pull` 후 영수증 원장에서 이 날짜의 지문 항목을 확인한다.
   - official: `league/ledger/submissions.jsonl`
   - sandbox: `league/sandbox/ledger/submissions.jsonl`
3. `committed`면 다음 단계로 간다. `late`나 `rejected`면 다시 push하지 말고 사유를 그대로 사용자에게 보고한다.

## 5단계 — 원본 공개 (08:30 이후, 12:00 전)

1. 현재 시각이 08:30 KST를 지났는지 확인한다. 지나지 않았으면 기다린다.
2. 토론 기록 `<제출 폴더>/<날짜>-debate.md`를 쓴다. 내용은 1·2단계 요약, 변경 내역, 각 r1/r2 파일 경로다.
3. CSV가 지문과 같은지 확인한다: `sha256sum <CSV>`의 값이 `.sha256` 첫 단어와 같아야 한다. 다르면 push하지 말고 사용자에게 보고한다.
4. `timing.json`을 마무리하고, CSV·토론 기록·`league/rounds/<날짜>/claude/` 폴더(official이면 지침 기록 포함)를 커밋해 push한다.
5. 영수증이 `accepted`인지 확인한다. `rejected`(해시 불일치)면 사유를 보고한다. 12:00 전이라면 **지문과 같은 원본**으로만 다시 push할 수 있다.

## 보고 (사용자에게)

- 라운드 날짜, 모드, 열린 시장
- 에이전트별 최종 종목(KR/US)과 1단계 대비 변경 여부
- 제출 결과: 지문 `committed`/`late`/`rejected`와 서버 push 시각, 원본 `accepted`/`rejected`와 커밋 SHA
- 단계별 실제 소요 시간(`timing.json`)과 90분 안에 끝났는지
- 문제와 개선점 (사용량, 시간, 자료 부족, DART 공시 상태 등)

점수는 평가 세션 종가가 나온 뒤 채점 작업이 계산하므로 이 보고에 포함하지 않는다.
