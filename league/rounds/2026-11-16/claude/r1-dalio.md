# r1-dalio — 2026-11-16(월) 라운드 (지침 v2)

## 0. 구간
- KR: 11/13 15:30 종가 → 11/16 15:30 종가 (KOSPI 대비)
- US: 11/13 종가 → 11/16 종가, KST 11/17 06:00 (SPY 대비)

## 1. 국면 (4분면)
- 인플레이션 ↑: 10월 CPI가 강해 11/10 증시 하락, 금리 인상 우려(Star-Advertiser 11/10). 미 10년물 11/13 5.154%(research 도구). 10/9 investinglive 보도의 4.95%(2023년 10월 이후 최고)보다 높다.
- 성장: 엇갈림. 엠파이어 직전값 25.5(강함). 반면 S&P500은 고점 대비 -3.29%로 50일선 아래(stock_data 11/13).
- 결론: 인플레↑ / 성장 혼재. 실물·에너지에 상대적으로 유리하고, 장기 듀레이션 자산에는 불리하다.
- 한국: KOSPI 11/13 종가 5290.53(research 도구), 52주 고점 대비 -41.96%, 1년 변동성 56.42%(stock_data). 디레버리징형 고변동 국면. 원/달러 11/13 1333.78(research 도구).
- 유가: 이란 긴장 완화로 브렌트가 11/9~10에 90달러 아래로 내렸다가 11/11 92~93달러(oilprice 11/10, tradingeconomics). 주말(11/14~15) 뉴스는 확인 못함.

## 2. 일정 점검
- US: 엠파이어스테이트 11/16 08:30 ET(구간 안). 산업생산 09:15 ET는 교차 확인 못함. 소매판매 11/17은 구간 밖.
- KR: 금통위·수출 지표 등 구간 안 일정 확인 못함. S-Oil 관련 DART 공시는 공통 자료에서 찾지 못함(공시 미확인).
- XOM 실적·배당락 11/16: 확인 못함.

## 3. 바깥 관점 (일반론)
- 인플레이션이 오르고 금리가 높은 국면에서 에너지는 장기 성장주보다 상대적으로 강한 경향이 있다(일반론, 숫자 없음).
- 지정학 이벤트가 주도하는 유가는 하루 단위 방향 예측력이 낮다(일반론).

## 4. 판단
- KR: WATCH. 거시 우위가 없다. 정유(S-Oil 11/13 종가 104200원(research 도구))를 검토했지만, 유가 방향이 주말 이란 뉴스에 달린 동전 던지기라 보류했다. 주간 관망 카드 1회를 쓴다.
- US: XOM, p_beat 0.52, exp_excess +0.15%p. 인플레·고금리 국면의 헤지이고 SPY와 상관이 낮다. XOM 11/13 종가 170.59달러(research 도구).

## 5. 내가 틀릴 시나리오 (확률은 주관 추정)
- 미-이란 합의 진전으로 유가 추가 급락, 에너지 부진: 약 30%
- 엠파이어 약세로 금리 하락, 기술주 주도 반등, XOM 상대 부진: 약 20%
- KR 급반등에서 관망 기회비용 발생: 판단 불가(대칭)

## JSON
```json
{"agent_id":"dalio","candidates":[{"market":"KR","ticker":"WATCH","name":"관망","rationale":"원칙 1: 국면을 모르면 베팅 크기를 줄인다. 국면 판단은 인플레이션 상승(미국 10월 CPI 강세로 11/10 증시 하락 보도, 미 10년물 11/13 5.154%(research 도구)) 쪽이고 성장은 엇갈린다. 한국은 KOSPI 11/13 종가 5290.53(research 도구)이며 52주 고점 대비 -41.96%, 1년 변동성 56.42%, 50일·200일선 모두 아래에 있다(stock_data, 11/13 기준). 디레버리징 국면에 가까운 고변동 장세다. 평가 구간(11/16 15:30까지) 안에 금통위나 수출 지표 같은 한국 거시 촉매는 확인하지 못했다. 원/달러 11/13 1333.78(research 도구)도 방향 신호가 약하다. 가장 유력한 업종 후보는 정유(S-Oil 11/13 종가 104200원(research 도구))였다. 하지만 브렌트는 이란 긴장 완화로 11/9~10에 90달러 아래까지 밀렸다가 11/11에 92~93달러로 반등한 상태다(tradingeconomics, oilprice 11/10). 주말 이란 관련 뉴스는 확인 못했다. 결국 하루 방향은 지정학 동전 던지기라서, 거시 우위가 없는 개별 베팅 대신 지수 수익을 받는 관망을 쓴다. S-Oil 관련 공시는 공통 자료 disclosures에서 찾지 못했다(공시 미확인).","risks":["관망이라 KOSPI가 급반등해도 초과수익이 0으로 고정된다(기회비용)","주말 사이 이란 긴장이 다시 높아져 유가가 오르면 정유·에너지주가 지수를 크게 이길 수 있는데, 그 기회를 놓친다","주간 관망 카드 1회를 여기서 써서, 이번 주 뒤에 더 불확실한 날에는 쓸 수 없다"],"catalyst":"없음 (구간 안 한국 거시 일정 확인 못함)","flip_condition":"장 시작 전에 주말 이란·호르무즈 관련 유가 급등 뉴스나 한국 거시 서프라이즈가 확인되면 정유(S-Oil) 매수로 바꾼다","p_beat":0.5,"exp_excess":0.0,"sources":[{"url":"https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=3mo&interval=1d","as_of":"2026-11-13","retrieved_at":"2026-11-16T07:07:50+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/KRW%3DX?range=3mo&interval=1d","as_of":"2026-11-13","retrieved_at":"2026-11-16T07:07:51+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=3mo&interval=1d","as_of":"2026-11-13","retrieved_at":"2026-11-16T07:07:50+09:00"},{"url":"https://oilprice.com/Energy/Crude-Oil/Oil-Falls-to-Lowest-Level-Since-August.html","as_of":"2026-11-10","retrieved_at":"2026-11-16T07:09:26+09:00"},{"url":"https://tradingeconomics.com/commodity/brent-crude-oil/news/600509","as_of":"확인 못함","retrieved_at":"2026-11-16T07:09:26+09:00"},{"url":"https://www.staradvertiser.com/2026/11/10/breaking-news/wall-street-falls-as-hot-inflation-fuels-fed-rate-hike-fears/","as_of":"2026-11-10","retrieved_at":"2026-11-16T07:09:26+09:00"}]},{"market":"US","ticker":"XOM","name":"ExxonMobil","rationale":"원칙 1: 국면 확인이 먼저다. 미국은 인플레이션 상승 국면이다. 10월 CPI가 강해 금리 인상 우려로 11/10 증시가 하락했다(Star-Advertiser 11/10). 미 10년물은 11/13 5.154%(research 도구)로, 10/9에 2023년 10월 이후 최고로 보도된 4.95%보다 더 높다(investinglive 10/9). S&P500은 52주 고점 대비 -3.29%이고 50일선 아래다(stock_data 11/13). 원칙 2: 인플레이션이 오르고 금리가 높은 국면에서는 할인율에 민감한 장기 성장주보다 실물 원자재 현금흐름을 가진 에너지가 상대적으로 유리하다(일반론). 포트폴리오에서는 주식 듀레이션 위험을 상쇄하는 인플레이션 헤지 역할을 하며 SPY와 상관이 낮다. 평가 구간 안의 거시 이벤트는 11/16 08:30 ET 엠파이어스테이트 제조업지수다(직전값 25.5, 진행자 일정표). 강하게 나오면 금리가 오르고 성장주에 부담이 되어 에너지에 상대적으로 유리하다. XOM 11/13 종가 170.59달러(research 도구), 1개월 -2.34%, 1년 +48.61%(stock_data). 최근 유가가 이란 긴장 완화로 90달러 안팎까지 떨어진 상태가 반영된 가격이다. 확신은 낮다. 유가 방향이 지정학에 달려 있어 p_beat는 기준선을 약간 넘는 수준만 준다. XOM의 11/16 실적·배당락은 확인 못함.","risks":["주말이나 월요일 미-이란 협상 진전 뉴스로 유가가 다시 급락하면 에너지가 지수보다 부진하다","엠파이어스테이트 지수가 약하게 나와 금리가 내리면 성장주와 기술주 반등 속에 에너지가 상대적으로 뒤처진다","AI·대형 기술주 중심의 지수 반등이 오면 저베타 에너지는 초과수익을 내기 어렵다"],"catalyst":"11/16 08:30 ET 뉴욕 엠파이어스테이트 제조업지수(구간 안). 산업생산 09:15 ET는 날짜 교차 확인 못함","flip_condition":"미국 장 시작 전에 브렌트가 3% 넘게 급락하거나(이란 합의 등), 10년물이 크게 하락해 성장주 주도 장세가 확인되면 판단을 뒤집는다","p_beat":0.52,"exp_excess":0.15,"sources":[{"url":"https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=3mo&interval=1d","as_of":"2026-11-13","retrieved_at":"2026-11-16T07:07:50+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=3mo&interval=1d","as_of":"2026-11-13","retrieved_at":"2026-11-16T07:07:50+09:00"},{"url":"https://www.staradvertiser.com/2026/11/10/breaking-news/wall-street-falls-as-hot-inflation-fuels-fed-rate-hike-fears/","as_of":"2026-11-10","retrieved_at":"2026-11-16T07:09:26+09:00"},{"url":"https://investinglive.com/stocks/us-stocks-close-lower-as-rising-yields-and-100-oil-prices-pressure-the-indices/","as_of":"2026-10-09","retrieved_at":"2026-11-16T07:09:26+09:00"},{"url":"https://oilprice.com/Energy/Crude-Oil/Oil-Falls-to-Lowest-Level-Since-August.html","as_of":"2026-11-10","retrieved_at":"2026-11-16T07:09:26+09:00"},{"url":"https://finviz.com/calendar/economic?dateFrom=2026-11-16","as_of":"확인 못함","retrieved_at":"2026-11-16T07:09:26+09:00"}]}]}
```
