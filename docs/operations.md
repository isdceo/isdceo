# AI 투자 리그 운영 안내 (운영자용)

시작 준비 상태는 언제든 `python3 tools/league.py readiness`로 확인한다.

## 하루 일정 (평일, KST)

| 시각 | 무엇이 | 자동/수동 | 확인할 것 |
|---|---|---|---|
| (월) 06:30 | 주간 마감 (순위·탈락·교체 고정) | 자동 | `league/ledger/weekly_decisions.jsonl` |
| 06:50 | 공통 자료 생성 (`league-daily`) | 자동 | `league/rounds/<날짜>/snapshot.json` 생성 커밋 |
| 07:05–08:20 | 로로(Claude) 팀 라운드 (`/league-round <날짜> official`, 예약 세션) | 자동 | 진행 보고 |
| 10분마다 | 슈슈 팀 전용 제출 저장소 동기화 (`docs/shushu-repo-setup.md`) | 자동 | `league/ledger/external_pushes.jsonl`, 동기화 커밋 |
| **08:30** | **지문 마감** (`<날짜>.sha256`만, 영수증 `committed`) | – | 두 팀 지문 영수증이 `committed`인지 |
| 08:30–**12:00** | 원본 공개 (CSV·토론 기록, 지문과 같은 파일이면 `accepted`) | 자동 | 두 팀 원본 영수증이 `accepted`인지 |
| 08:35 · 11:35 | 현황판 갱신 | 자동 | 화면 확인 |
| 08:45 · 09:15 · 11:00 · 12:10 | 공유판 배포 (토요일은 11:00·12:10) | 자동 (`deploy_enabled`) | 화면 확인 |
| 10:30 | 종가 수집 → 채점 → 결과 묶음 | 자동 | 커밋 메시지의 수집 실패·보류 목록 |
| 11:23 | 손실 복기 (`/league-loss-review`) | 자동 (예약 세션) | `league/reviews/losses/` |
| 12:40 · 19:10 | 슈슈 팀 메시지 확인·회신 | 자동 (예약 세션) | `docs/codex-notices/replies/` |

일요일 14:43에 주간 복기(`/league-review`)가 돈다. 지침 개선안은 PR로 오며, 머지가 운영자 승인이다.

## 매주

- **월 06:30 이후:** `league/ledger/weekly_decisions.jsonl` 확인. 탈락·교체가 있으면 두 팀에 알린다.
- **일:** `/league-review` (14:43 예약 세션). PR이 오면 개선안을 검토해 머지(승인)하거나 닫는다.
- **다음 주 초:** 복기 때 잠정이던 결과가 확정되면 복기 보완 문서가 추가됐는지 확인한다.

## 정기 점검

| 주기 | 할 일 |
|---|---|
| 월 1회 | KRX Open API 이용 신청 **만료일** 확인 (신청 기간 1·3·6·12개월). 만료 전에 재신청 |
| 6월·12월 | KOSPI200·KOSDAQ150 정기변경 → KRX 파일 받아 `python3 tools/universe.py import-kr ... --effective <적용일>` |
| 분기 | S&P 500·NASDAQ-100 변경 반영: `python3 tools/universe.py fetch-us --effective <적용일>` |
| 수시 | 데이터 제공처 약관 변경, 문의 회신 → `docs/provider-inquiries.md` 회신 기록 |

## 제출 경로 (공정성)

- 슈슈 팀은 **전용 제출 저장소**에 지문(08:30 전)과 원본(08:30~12:00)을 push하고, 동기화 작업이 그 저장소의 서버 push 시각으로 영수증을 만든다(`docs/shushu-repo-setup.md`). 원본은 마감 전에 메인 저장소로 들어오지 않는다(봉인). 슈슈 팀 파일을 Claude가 진행하는 대화에 붙여넣지 않는다.
- Claude 팀 라운드는 별도 예약 세션(`/league-round <날짜> official`)에서 돈다. 그 세션은 마감 전 상대 팀 당일 파일을 열지 않는다.
- 마감(08:30) 뒤에는 어느 쪽 파일이든 열람·공유해도 된다.

## 운영 장애로 미제출일 때

```bash
python3 tools/league.py outage 2026-11-10 --team claude --reason "Claude 사용 한도 도달로 라운드 미실행" --kind operator
python3 tools/league.py outage 2026-11-10 --team shushu --agent s3 --reason "분석 시간 초과" --kind team
```
- 두 팀 모두 미제출로 집계(소급 제출 없음). 사유는 화면 제출률 옆과 기록 탭에 표시된다.

## 문제가 생기면

| 증상 | 원인 후보 | 대응 |
|---|---|---|
| 영수증이 `late` | 지문 push가 08:30 이후 | 소급 인정 없음. 그날은 미제출 |
| 영수증이 `rejected` | CSV 형식, 대상 범위, 버전 불일치, 재제출, 원본 해시가 지문과 다름 | 사유 확인. 해시 불일치는 12:00 전 지문과 같은 원본으로만 다시 push. 이미 `accepted`면 재제출 불가 |
| 채점이 `held` (가격 미확인) | 제공처 지연·누락 | 다음 수집 때 자동 재시도. 3거래일 넘으면 수동 확인 |
| 채점이 `held` (배당·분할 미확인) | 기업행동 확인 기록 없음 | 제공처 응답 확인, 필요하면 수동으로 확인 기록 추가 |
| 채점이 `held` (±30% 초과) | 분할 누락·가격 오류 의심 | 공시 확인 후 정정 또는 확인 기록 추가 |
| 수집 401 | 인증키·API 승인 문제 | KRX 마이페이지 승인 상태, Secrets 값 확인 |
| 수집 403 Access Denied | 반복 실패로 인한 일시 차단 또는 GitHub 서버 차단 | 반복 호출 중지. 사이트 샘플 테스트로 구분 |
| 라운드가 `unapproved_edit`로 멈춤 | 지침 파일이 승인 없이 수정됨 | 수정 내용 확인 → 되돌리거나 PR로 정식 승인 |
| 원장 검사 실패 (`league-ledger-guard`) | 원장 기존 줄 수정·삭제 | 해당 커밋 되돌리기. 정정은 새 줄로만 |

## 스위치

| 설정 (`league/config.json`) | 의미 | 지금 |
|---|---|---|
| `automation_enabled` | 06:50 공통 자료 · 10:30 수집·채점 · 월 06:30 마감 | 켜짐 |
| `deploy_enabled` | 공유판 배포 | 켜짐 |
| `season_start` | 리그 시작일 (YYYY-MM-DD) | 2026-11-09 |

지금 값은 `python3 tools/league.py readiness`로 확인한다.

## 마감 전 추천 가리기 (내보내기)

- `python3 tools/league.py export`와 `build-site`는 생성 시각이 그 라운드의 마감(08:30 KST)보다 이르면 해당 라운드 추천(`picks`)과 그 점수를 파일에 넣지 않는다. 두 팀, 운영자용·공유판 모두 같다.
- 가려진 건수만 `embargoed`에 `팀|라운드: 건수`로 남는다. 08:30 이후 다시 내보내면 들어간다.
- `build-site`는 마감 전 추천이 남아 있으면 실패한다. 예시 원장(`SAMPLE`)은 실제 추천이 아니라 예외.
- 원장(`league/ledger/picks.jsonl`)과 `league/imports/` 원본 CSV는 저장소에 그대로 있으므로, 마감 전에는 라운드 세션이 상대 팀 경로를 열지 않는 규칙(league-round 스킬)이 계속 필요하다.

## 지문 먼저, 원본 나중 제출 (운영 기준 v1.7, 2026-11-09 라운드부터)

- 08:30 전에는 `<날짜>.sha256`(CSV 원본 바이트의 sha256)만 push → 영수증 `committed`. 원본 CSV·토론 기록은 08:30~12:00에 push → 해시가 같으면 `accepted`.
- 설정: `league/config.json`의 `commit_reveal` (`from`, `reveal_deadline`). 연습 원장도 같은 설정을 쓴다.
- 지문 파일 만들기: `python3 tools/league.py commit <CSV>`.
- 마감 전 원본 push는 접수하되 `early_reveal: true`로 기록한다.
- 동시 공개: 지문을 낸 팀(또는 아직 영수증이 없는 팀)의 원본이 모두 접수되거나 12:00이 지나야 그 라운드 종목이 어느 팀 것이든 화면·결과 묶음에 나온다. 늦음·반려로 결론 난 팀은 기다리지 않는다.
