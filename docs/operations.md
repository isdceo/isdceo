# AI 투자 리그 운영 안내 (운영자용)

시작 준비 상태는 언제든 `python3 tools/league.py readiness`로 확인한다.

## 하루 일정 (평일, KST)

| 시각 | 무엇이 | 자동/수동 | 확인할 것 |
|---|---|---|---|
| 06:50 | 공통 자료 생성 (`league-daily`) | 자동 | `league/rounds/<날짜>/snapshot.json` 생성 커밋 |
| 07:05–08:20 | Claude 팀 라운드 (`/league-round <날짜> official`) | 예약 세션 또는 수동 | 진행 보고 |
| ~08:28 | 슈슈 팀 CSV push (운영자가 업로드) | 수동 | Actions `league-submission` 결과 |
| **08:30** | **제출 마감** | – | 두 팀 영수증이 `accepted`인지 |
| 10:30 | 종가 수집 → 채점 → 운영자용 화면 데이터 | 자동 | 커밋 메시지의 수집 실패·보류 목록 |
| 11:00 | 지인 공유판 배포 | 자동 (켠 경우) | 화면 확인 |

월요일에는 06:30에 주간 마감(순위·탈락·교체 고정)이 먼저 돈다. 토요일에는 주간 복기(`/league-review`)를 한다.

## 매주

- **월 06:30 이후:** `league/ledger/weekly_decisions.jsonl` 확인. 탈락·교체가 있으면 두 팀에 알린다.
- **토:** `/league-review`. PR이 오면 개선안을 검토해 머지(승인)하거나 닫는다.
- **다음 주 초:** 토요일에 잠정이던 결과가 확정되면 복기 보완 문서가 추가됐는지 확인한다.

## 정기 점검

| 주기 | 할 일 |
|---|---|
| 월 1회 | KRX Open API 이용 신청 **만료일** 확인 (신청 기간 1·3·6·12개월). 만료 전에 재신청 |
| 6월·12월 | KOSPI200·KOSDAQ150 정기변경 → KRX 파일 받아 `python3 tools/universe.py import-kr ... --effective <적용일>` |
| 분기 | S&P 500·NASDAQ-100 변경 반영: `python3 tools/universe.py fetch-us --effective <적용일>` |
| 수시 | 데이터 제공처 약관 변경, 문의 회신 → `docs/provider-inquiries.md` 회신 기록 |

## 제출 경로 (공정성)

- 슈슈 팀 당일 CSV는 운영자가 **GitHub에 직접** 올린다(웹 업로드 또는 push). Claude가 진행하는 대화에 붙여넣지 않는다.
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
| 영수증이 `late` | push가 08:30 이후 | 소급 인정 없음. 그날은 미제출 |
| 영수증이 `rejected` | CSV 형식, 대상 범위, 버전 불일치, 재제출 | 사유 확인. 같은 날 이미 `accepted`면 재제출 불가 |
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
| `automation_enabled` | 06:50 공통 자료 · 10:30 수집·채점 · 월 06:30 마감 | 꺼짐 |
| `deploy_enabled` | 11:00 지인 공유판 배포 | 꺼짐 |
| `season_start` | 리그 시작일 (YYYY-MM-DD) | 미정 |

## 마감 전 추천 가리기 (내보내기)

- `python3 tools/league.py export`와 `build-site`는 생성 시각이 그 라운드의 마감(08:30 KST)보다 이르면 해당 라운드 추천(`picks`)과 그 점수를 파일에 넣지 않는다. 두 팀, 운영자용·공유판 모두 같다.
- 가려진 건수만 `embargoed`에 `팀|라운드: 건수`로 남는다. 08:30 이후 다시 내보내면 들어간다.
- `build-site`는 마감 전 추천이 남아 있으면 실패한다. 예시 원장(`SAMPLE`)은 실제 추천이 아니라 예외.
- 원장(`league/ledger/picks.jsonl`)과 `league/imports/` 원본 CSV는 저장소에 그대로 있으므로, 마감 전에는 라운드 세션이 상대 팀 경로를 열지 않는 규칙(league-round 스킬)이 계속 필요하다.

## 지문 먼저, 원본 나중 제출 (v1.7, 2026-11-09 라운드부터)

- 08:30 전에는 `<날짜>.sha256`(CSV 원본 바이트의 sha256)만 push → 영수증 `committed`. 원본 CSV·토론 기록은 08:30~12:00에 push → 해시가 같으면 `accepted`.
- 설정: `league/config.json`의 `commit_reveal` (`from`, `reveal_deadline`). 연습 원장도 같은 설정을 쓴다.
- 지문 파일 만들기: `python3 tools/league.py commit <CSV>`.
- 마감 전 원본 push는 접수하되 `early_reveal: true`로 기록한다.
- 현황판의 종목 공개(08:35 갱신)는 원본 공개 뒤라야 보이므로, 원본을 늦게 올린 팀은 그 다음 갱신에 나타난다.
