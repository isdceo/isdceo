# 2026-11-13 라운드 일정표 (Claude 팀 진행자 작성)

평가 구간: KR 11/12 종가 → 11/13(금) 종가 · US 11/12 종가 → 11/13(금, 미국시간) 종가 (KST 11/14 06:00)
확인 시각: 2026-11-13T07:07:18+09:00

## 거시 일정
- 미국 10월 PPI: 11/13 08:30 ET 발표 예정 — **평가 구간 안**(US). 컨센서스 확인 못함. 출처: https://economics.td.com/domains/economics.td.com/documents/reports/bottom-line/tables/2026-11-06/upcoming.htm (as_of 2026-11-06), https://www.catacal.com/catalyst/october-producer-price-index-report (as_of 확인 못함)
- 미국 10월 소매판매: 11/17 08:30 ET 예정 — 구간 밖(fedratecalc 월간 표, https://fedratecalc.com/us-economic-calendar/november-2026/, as_of 확인 못함).
- 11/12(목) 발표된 미국 실업수당 청구·기존주택판매는 US 기준 종가 전 정보(KR에는 11/12 종가 뒤 나온 정보).
- 한국 금통위·한국 지표·FOMC: 구간 안 확인 못함.
## 실적 발표·배당락 (대상 종목, 구간 안)
- 진행자 검색에서 11/13 실적 발표 확정 목록을 확인하지 못함(제3자 캘린더 한 곳에 장전 ECC·MIST·NDLS·RMIX·SBC·USAS — 대상 종목 여부는 각자 확인).
- 주간 프리뷰에 Applied Materials 실적이 11/9–13 주간으로 나오나 날짜 확인 못함(https://stockhub.kr/en/insights/macro-weekly-20261109). 11/12 장 마감 뒤 발표였다면 KR 반도체에는 기준 종가 뒤 정보 — 해당 종목을 다루면 직접 확인.
- 그 밖에는 각 에이전트가 후보 종목의 11/13 실적·배당락 여부를 직접 확인. 한국 종목은 공통 자료 DART 공시로 확인.
## 공통 자료 상태
- snapshot.json sha256 ad642eec35c0ce93008a3a35e764e8f9f23fcf1c1e9412e594c1f42fc72662a5 (06:51 생성)
- DART 공시(disclosures): ok, 415건
## 도구 메모
- research.py는 Yahoo HTTP 429가 날 수 있다. 실패하면 잠시 뒤 1~2회 재시도하고, 그래도 안 되면 "기준 종가 확인 못함".
- research.py dart는 DART_API_KEY가 없어 동작하지 않는다 — 공통 자료 disclosures와 DART 원문 URL을 쓴다.
- research.py check-csv는 근거 문장을 "11/12 종가 OOO원(research 도구)" 형식으로 쓰면 정상 대조된다("종가, research 도구"처럼 쉼표를 넣지 말 것). 기준일(11/12)이 아닌 날의 종가를 인용하면 경고가 나니, 꼭 필요할 때만 쓰고 출처를 붙인다.
- retrieved_at은 실제로 자료를 받은 뒤 잰 시각만 쓴다(스냅숏 생성 시각을 쓰지 말 것).
