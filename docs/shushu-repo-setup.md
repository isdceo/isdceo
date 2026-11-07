# 슈슈 팀 전용 제출 저장소 설정 (B안, 운영자용)

슈슈 팀(Codex)이 운영자 손을 거치지 않고 직접 제출하게 하는 설정입니다. 슈슈 팀은 **전용 저장소에만** 읽기·쓰기 권한을 받고, 메인 리그 저장소(`isdceo/isdceo`)는 볼 수 없습니다.

## 어떻게 돌아가나

1. 슈슈 팀이 전용 저장소에 지문(`submit/<날짜>.sha256`)을 push합니다. 원본(`submit/<날짜>.csv`, `-debate.md`)과 한 줄 대사(`lines/<날짜>-shushu.json`)도 같은 방식입니다.
2. 메인 저장소의 `league-shushu-sync` 워크플로가 예약 시각마다 전용 저장소의 **GitHub 서버 push 기록 시각**을 읽습니다.
3. 허용 경로의 파일만 메인의 `league/imports/shushu/` 등으로 바이트 그대로 가져오고, 그 push 시각으로 영수증을 판정합니다.
   - 판정 기준은 지금과 같습니다: 지문 08:30, 원본 12:00, 지문과 같은 원본.
   - 예약 실행이 몇 분 늦게 돌아도 판정 시각은 바뀌지 않습니다.
4. 마감 전에 원본·토론·대사를 push하면, 08:30이 지날 때까지 메인에 들이지 않습니다. 로로 팀 세션이 볼 수 없게 하기 위해서입니다. 마감 뒤 처리하면 지금처럼 '마감 전 공개(early_reveal)'로 기록됩니다.
5. 원 가격이 없는 자료만 전용 저장소의 `from-league/`로 돌려보냅니다: 결과 묶음, 슈슈 팀 영수증, 공지, update-plan, 검증 도구.

예약 시각(KST)은 다음과 같습니다.

| 언제 | 시각 |
|---|---|
| 평일 | 08:00–09:50 10분마다, 10:05·11:05·12:05·18:05 |
| 토요일 | 10:50 |
| 월요일 | 06:40 |

Actions 탭에서 수동 실행도 됩니다.

## 운영자가 할 일 (한 번)

1. **전용 저장소 만들기**
   - GitHub에서 새 저장소를 만듭니다. 예: `isdceo/isdceo-shushu`, 비공개, README 포함.
   - 저장소 Settings → Actions → General에서 Actions를 꺼 두기를 권합니다. 전용 저장소의 워크플로는 쓸 일이 없습니다.
2. **슈슈 팀(Codex)에게 이 저장소만 연결**
   - Codex 설정의 GitHub 연결에서 저장소 선택을 **전용 저장소 하나만**으로 둡니다.
   - Codex CLI를 운영자 PC에서 쓰는 경우에는 그 PC의 git 로그인으로 push합니다.
   - Codex 클라우드처럼 작업 브랜치에 push하고 PR을 여는 방식도 됩니다. 판정은 **브랜치 push 시각**이고, 병합 시각이 아닙니다. 병합으로 같은 파일이 다시 들어와도 영수증을 새로 만들지 않습니다.
3. **메인 저장소용 토큰 만들기** (GitHub → Settings → Developer settings → Fine-grained tokens)
   - Repository access: **Only select repositories → 전용 저장소 하나**
   - Permissions: **Contents: Read and write** (Metadata: Read는 자동)
   - 만료: 시즌 끝 이후 날짜
4. **토큰을 메인 저장소 Secrets에 넣기**
   - `isdceo/isdceo` → Settings → Secrets and variables → Actions → New repository secret
   - 이름은 `SHUSHU_REPO_TOKEN`입니다.
   - 토큰은 **채팅에 붙여 넣지 마세요.** 전용 저장소에도 넣지 않습니다.
5. **로로(Claude)에게 저장소 이름만 알려 주기**
   - 로로가 `league/config.json`의 `shushu_repo.repo`를 적고 `enabled`를 켭니다.
   - 그다음 연습 경로로 시험합니다: `practice/<날짜>.sha256` push → 수동 실행 → `from-league/receipts-shushu.jsonl` 확인.

## 지켜지는 것

- 슈슈 팀은 메인 저장소의 원장(점수·가격·영수증), 워크플로, 설정, 로로 팀 지침을 볼 수도 바꿀 수도 없습니다.
- 메인으로 가져오는 경로는 아래 표가 전부입니다. 그 밖의 파일은 무시하고 연결 기록(`external_pushes` 원장)에만 남깁니다.

| 전용 저장소 | 메인 저장소 |
|---|---|
| `submit/<날짜>.sha256` · `.csv` · `-debate.md` | `league/imports/shushu/` |
| `practice/<날짜>.sha256` · `.csv` · `-debate.md` | `league/imports/sandbox-shushu/` |
| `lines/<날짜>-shushu.json` | `league/lines/` |
| `practice-lines/<날짜>-sandbox-shushu.json` | `league/sandbox/lines/` |

- `from-league/` 사본은 허용 목록의 파일만 담습니다. 가격·점수 원장과 가격 포함 공통 자료는 넣지 않고, 가격처럼 보이는 칸이 섞이면 사본 작업이 멈춥니다.
- 로로 팀 세션은 전용 저장소를 열지 않습니다. 메인으로는 마감 전에 지문만 들어옵니다.

## 비상시

- 동기화가 실패하면 Actions의 `league-shushu-sync` 실행이 빨간색으로 남습니다. 수동 실행으로 다시 돌릴 수 있습니다. 판정은 전용 저장소 push 시각이라, 늦게 돌려도 결과가 같습니다.
- 예전 방식(운영자가 메인에 직접 업로드)도 그대로 됩니다. 한 라운드에 두 경로를 섞지는 마세요. 먼저 접수된 쪽이 유효하고, 같은 날짜를 다시 내면 거부됩니다.
- 토큰이 만료되거나 지워지면 동기화가 실패로 알립니다. 3·4단계를 다시 하면 됩니다.
