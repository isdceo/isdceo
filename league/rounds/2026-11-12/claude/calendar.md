# 2026-11-12 라운드 일정표 (Claude 팀 진행자 작성)

평가 구간: KR 11/11 종가 → 11/12(목) 종가 · US 11/11 종가 → 11/12(목, 미국시간) 종가 (KST 11/13 06:00)
확인 시각: 2026-11-12T07:06:56+09:00

## 거시 일정
- 미국 신규 실업수당 청구(11/7 주간): 11/12 08:30 ET 발표 예정 — **평가 구간 안**. 컨센서스는 출처마다 다름(195K 등, 확인 못함). 출처: https://www.financecalendar.com/event/us-initial-jobless-claims-november-12-2026/ (as_of 확인 못함), https://economics.td.com/domains/economics.td.com/documents/reports/bottom-line/tables/2026-11-06/upcoming.htm (as_of 2026-11-06)
- 미국 10월 기존주택판매: 11/12 10:00 ET (finviz 캘린더, https://finviz.com/calendar/economic?dateFrom=2026-11-09, as_of 확인 못함)
- 미국 10월 PPI: 11/13 08:30 ET — **구간 밖**(TD 표 기준).
- 미국 10월 CPI는 11/10 발표로 이미 기준 종가 전 정보.
- FOMC·한국 금통위·한국 지표: 구간 안 확인 못함.
## 실적 발표·배당락 (대상 종목, 구간 안)
- 진행자 검색에서 11/12 실적 발표 목록을 확인하지 못함. Nebius(NBIS) 3분기 실적이 11/12 장전 예정이라는 회사 공지가 있었음(어제 라운드 미래광 출처: https://nebius.com/newsroom/nebius-group-announces-date-of-third-quarter-2026-results-and-conference-call, as_of 2026-10-30) — 대상 종목 여부는 각자 확인.
- 그 밖에는 각 에이전트가 후보 종목의 11/12 실적·배당락 여부를 직접 확인. 한국 종목은 공통 자료 DART 공시로 확인.
## 공통 자료 상태
- snapshot.json sha256 a64e5e84bad9e25bddeef101ce2800101c75dd1eca6c324ee73076142392188d (06:51 생성)
- DART 공시(disclosures): ok, 427건
## 도구 메모
- research.py는 Yahoo HTTP 429가 날 수 있다. 실패하면 잠시 뒤 1~2회 재시도하고, 그래도 안 되면 "기준 종가 확인 못함".
- research.py dart는 DART_API_KEY가 없어 동작하지 않는다 — 공통 자료 disclosures와 DART 원문 URL을 쓴다.
- research.py check-csv는 근거 문장을 "11/11 종가 OOO원(research 도구)" 형식으로 쓰면 정상 대조된다("종가, research 도구"처럼 쉼표를 넣지 말 것).
