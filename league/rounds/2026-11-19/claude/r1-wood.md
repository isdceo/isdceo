# 2026-11-19 라운드 R1 — wood (캐시 우드 철학 분석가, 지침 v2)

작성: 2026-11-19 07:1x KST. 교육·토론용 분석이며 투자 권유 아님.

## 1. 구간
- KR: 11/18 종가 → 11/19 15:30 종가 (KOSPI 대비)
- US: 11/18 종가 → 11/19 정규장 종가(KST 11/20 06:00) (SPY 대비)

## 2. 일정 점검
- 미국: 주간 실업수당 청구 08:30 ET, Walmart 3분기 실적(시각 확인 못함), Intuit(시각 확인 못함) — 진행자 일정표 기준. NVIDIA 실적(11/17 장후) 반응 2일차.
- 한국: 금통위·수출 지표 확인 못함. 공통 자료 disclosures에서 SK하이닉스 11/17~18 공시 없음. corporate_actions_upcoming 비어 있음.
- 배당락: NVDA 배당 기준일 12/2(구간 밖). SK하이닉스 확인 못함(공시 미확인).
- research macro(KOSPI·SPY·금리)는 Yahoo 429로 조회 실패.

## 3. 데이터
- research close: 000660 11/18 종가 1144000원, NVDA 11/18 종가 150.96달러.
- Yahoo 10일 일봉(직접 조회): 000660 11/17 1098000 → 11/18 1144000(+4.2%). NVDA 11/17 155.46 → 11/18 150.96(-2.9%), 11/5 181.60부터 하락 추세.
- stock_data: NVDA 1m -29.4%, 52주 고점 대비 -36%, MA50 210.34 아래. 한미반도체 1m -16%(후보 제외: IR 안내공시뿐, 일시·내용 확인 못함).
- 주의: stock_data의 NVDA last_close 152.82는 research 도구 150.96과 불일치 — research 값을 기준으로 씀.

## 4. 판단 요지
혁신 필터: 두 종목 모두 AI 컴퓨팅 S-곡선(가속기·HBM) 위. 하루 근거는 엔비디아 3분기 FY27 실적(매출 1158억달러, 4Q 가이던스 1300억달러, Rubin 최단기 램프, 메모리 가격 상승으로 마진 가이던스 하락). 다만 2일차라 새 사건 강도가 약하고 밤사이 NVDA가 하락해 확률은 기준선 근처(0.51~0.52).

## 5. 결과 JSON
```json
{"agent_id":"wood","candidates":[
{"market":"KR","ticker":"000660","name":"SK하이닉스","rationale":"AI 메모리 S-곡선의 중심(HBM). 구간 안 확인된 사건: 엔비디아가 11/17 장후(미국 동부) 3분기 FY27 실적을 냈다. 매출 1158억달러(+103% YoY), 데이터센터 1076억달러, 4분기 가이던스 1300억달러±3%, Vera Rubin NVL72 출하가 '회사 역사상 가장 빠른 램프'라고 밝혔다(보도자료). 또 4분기 총마진 하락(71~72%) 이유로 메모리 가격 상승이 거론됐다(StockTitan) — 메모리 공급사의 가격 결정력을 확인해 준 신호다. 11/18 종가 1144000원(research 도구)은 전일 1098000원(stock_data/Yahoo) 대비 약 +4.2%로 1차 반응은 이미 반영됐다. 바깥 관점(일반론): 핵심 고객 실적 호재의 2일차는 추가 상승 탄력이 약해지는 경향. 안쪽 관점: 밤사이 NVDA 정규장 -2.9%(155.46→150.96, research/Yahoo)로 중립~약악재. 11/18~19 아침 SK하이닉스 자체 공시는 공통 자료에서 확인 못함(공시 미확인). 한국 거시 일정 확인 못함. 확률은 기준선 근처로 둔다.","risks":["밤사이 NVDA 정규장 -2.9% 하락으로 한국 AI 반도체 동반 차익실현","전일 +4.2% 반등 뒤 2일차 되돌림, 외국인 매도 지속 시 KOSPI 대비 열위","엔비디아 CEO 공백(젠슨 황 사임, 11/12 발표) 관련 불확실성 재부각"],"catalyst":"구간 안 자체 촉매 없음. 엔비디아 3분기 실적(11/17 미국 장후) 2일차 반응, 메모리 가격 상승 언급.","flip_condition":"장 초반 외국인 대규모 순매도로 -2% 이상 갭하락하거나, HBM 공급 관련 부정적 공시·보도가 나오면 판단 철회.","p_beat":0.51,"exp_excess":0.1,"sources":[
{"url":"https://query1.finance.yahoo.com/v8/finance/chart/000660.KQ?range=3mo&interval=1d","as_of":"2026-11-18","retrieved_at":"2026-11-19T07:09:14+09:00"},
{"url":"https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2027","as_of":"2026-10-25","retrieved_at":"2026-11-19T07:10:48+09:00"},
{"url":"https://www.stocktitan.net/articles/nvidia-q3-fiscal-2027-earnings-revenue-outlook","as_of":"2026-11-17","retrieved_at":"2026-11-19T07:10:48+09:00"},
{"url":"https://query1.finance.yahoo.com/v8/finance/chart/000660.KS?range=10d&interval=1d","as_of":"2026-11-18","retrieved_at":"2026-11-19T07:10:48+09:00"}]},
{"market":"US","ticker":"NVDA","name":"NVIDIA","rationale":"AI 가속 컴퓨팅 S-곡선의 플랫폼 기업. 구간 직전 확인된 사건: 11/17 장후 3분기 FY27 실적 매출 1158억달러(+103% YoY, 컨센서스 약 1087억~1090억달러는 검색 요약 기준), 4분기 가이던스 1300억달러±3%(중국 데이터센터 매출 0 가정, 1주 추가 포함), Rubin 최단기 램프(보도자료). 장후 최대 +4%였으나 11/18 정규장 종가 150.96달러(research 도구)로 전일 155.46달러 대비 -2.9%, 10/6 고점 대비 약 -35%, 52주 최저권(stock_data). 바깥 관점(일반론): 실적 서프라이즈에도 첫날 하락한 대형주는 2일차에 방향이 엇갈리며 뚜렷한 우위는 약하다. 안쪽 관점: 매출 성장·가이던스는 호재, 총마진 가이던스 하락(71~72%)·CEO 공백·매출채권 일수 증가·파트너 보증 1180억달러는 악재로 시장이 후자에 반응 중. 과매도 반등 여지에 기대지만 확인된 반전 신호는 없어 기준선 바로 위로 둔다. 구간 안 미국 거시: 주간 실업수당 청구 08:30 ET, Walmart 실적(시각 확인 못함) — 진행자 일정표 기준.","risks":["CEO 공백·마진 하락·파트너 보증 우려로 실적 후 매도 흐름 3일째 지속","반도체 전반 위험회피로 SPY 대비 고베타 하락","수출 규제 조사(Megaspeed) 관련 추가 보도"],"catalyst":"실적 발표(11/17 장후) 2일차 반응. 구간 안 자체 새 촉매는 없음(후임 CEO 발표 여부 확인 못함).","flip_condition":"개장 30분 내 150달러 아래로 밀리며 반도체 지수 동반 약세면 판단 철회. 후임 CEO 발표 등 새 사건이 나오면 재평가.","p_beat":0.52,"exp_excess":0.2,"sources":[
{"url":"https://query1.finance.yahoo.com/v8/finance/chart/NVDA?range=3mo&interval=1d","as_of":"2026-11-18","retrieved_at":"2026-11-19T07:08:45+09:00"},
{"url":"https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2027","as_of":"2026-10-25","retrieved_at":"2026-11-19T07:10:48+09:00"},
{"url":"https://www.stocktitan.net/articles/nvidia-q3-fiscal-2027-earnings-revenue-outlook","as_of":"2026-11-17","retrieved_at":"2026-11-19T07:10:48+09:00"},
{"url":"https://query1.finance.yahoo.com/v8/finance/chart/NVDA?range=10d&interval=1d","as_of":"2026-11-18","retrieved_at":"2026-11-19T07:10:48+09:00"}]}
]}
```
