# 2026-11-16 라운드 일정표 (Claude 팀 진행자 작성)

평가 구간: KR 11/13 종가 → 11/16(월) 종가 · US 11/13 종가 → 11/16(월, 미국시간) 종가 (KST 11/17 06:00)
확인 시각: 2026-11-16T07:07:02+09:00

## 거시 일정
- 미국 11월 뉴욕 엠파이어스테이트 제조업지수: 11/16 08:30 ET — **평가 구간 안**(US). 직전값 25.5, 컨센서스 확인 못함. 출처: https://finviz.com/calendar/economic?dateFrom=2026-11-16 (as_of 확인 못함), https://www.forexcracked.com/economic-calendar/usd-ny-fed-empire-state-manufacturing-index/ (as_of 확인 못함)
- 미국 10월 산업생산·설비가동률: 11/16 09:15 ET로 한 곳(MarketNews, https://marketnews.com/us-economic-data-calendar-2646790173, as_of 확인 못함)에 나옴 — 날짜 교차 확인 못함.
- Finviz에 같은 날 필라델피아 연준·캔자스시티 연준 지표도 표시되나 교차 확인 못함.
- 미국 10월 소매판매: 11/17 08:30 ET 예정 — 구간 밖(지난 라운드 일정표 기준).
- 11/13(금) 미국장 움직임과 10월 PPI 결과는 KR 기준 종가(11/13 15:30) 뒤 정보 — KR 판단에 쓸 수 있는 새 정보.
- 한국 금통위·한국 지표·FOMC: 구간 안 확인 못함.
## 실적 발표·배당락 (대상 종목, 구간 안)
- 진행자 검색으로 11/16 실적 발표 확정 목록을 찾지 못함 — 각 에이전트가 후보 종목의 11/16 실적·배당락 여부를 직접 확인. 한국 종목은 공통 자료 DART 공시로 확인.
## 공통 자료 상태
- snapshot.json sha256 211733504c1564c0e9c25ccada9f089677f8adf35adb2374ca8b3cbee581d3e5 (06:51 생성)
- DART 공시(disclosures): ok, 396건
## 도구 메모
- research.py는 Yahoo HTTP 429가 날 수 있다. 실패하면 잠시 뒤 1~2회 재시도하고, 그래도 안 되면 "기준 종가 확인 못함".
- research.py dart는 DART_API_KEY가 없어 동작하지 않는다 — 공통 자료 disclosures와 DART 원문 URL을 쓴다.
- check-csv 대조를 위해 근거에 "11/13 종가 OOO원(research 도구)" 형식을 쓴다(쉼표 넣지 말 것). 기준일(11/13)이 아닌 날의 종가는 꼭 필요할 때만, 출처를 붙여 인용.
- retrieved_at은 실제로 자료를 받은 뒤 잰 시각만 쓴다(스냅숏 생성 시각 금지).
