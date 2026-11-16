# r1-buffett (2026-11-17 라운드, US, 지침 v2)

## 1. 구간
US 기준 11/16 종가(KST 11/17 06:00) → 평가 11/17 종가(KST 11/18 06:00). 벤치마크 SPY 11/16 종가 739.95(research 도구), 하루 -1.91%(stock_data).

## 2. 일정 점검
- TJX 3분기(FY27) 실적: 11/18(수) 장전, 콜 11:00 ET (boerse-express, Business Wire 공지 요약) → 구간 밖.
- 배당락: 확인 못함. 지수 변경·대주주 매도: 확인 못함.
- 거시: 10월 소매판매 11/17 08:30 ET(구간 안), 산업생산 09:15 ET(한 출처). HD 실적 11/17 장전(출처 충돌, 진행자 일정표).

## 3. 바깥 관점 (일반론)
큰 지수 하락 다음 날 방어적 우량주의 초과수익 방향은 일정하지 않다. 실적 전날 정리 매도도 흔하다. 숫자 근거 없음.

## 4. 안쪽 관점
후보 스크리닝(stock_data, 11/16 기준): TJX 1d -2.44 / 5d -5.10 / 1mo -11.04, ROST 1d -3.75 / 5d -5.91, GOOGL 1d -4.07 / 1mo -17.57(사유 기사 날짜 확인 못함 → 제외), KO·PG·BRK-B·V·MA는 하락 없음 → 렌즈 밖.
TJX: 2분기 comps +4%, 조정 EPS 1.22(+11%), 연간 GAAP EPS 가이던스 5.31~5.36으로 상향 (sgbonline, just-style, 2026-08). 조정 EPS 가이던스 5.15~5.20 중간값 기준 PER 약 25배(추정). 직전 장 마감 뒤 회사 고유 뉴스: 찾지 못함(중립). 최근 낙폭 원인은 Marmaxx 부진 우려(barchart, 날짜 확인 못함)와 시장 급락으로 추정.

## 5. 반대 시나리오
소매판매 부진 또는 HD의 소비 둔화 경고로 소매주 전반이 밀리고, 실적 전날 회피 매도가 이어지는 경우.

## 판단 JSON
```json
{"agent_id":"buffett","candidates":[{"market":"US","ticker":"TJX","name":"TJX Companies","rationale":"오프프라이스 1위 TJX는 구매력·재고 회전이라는 원가우위 해자를 가진 이해하기 쉬운 사업이다. 2분기(FY27, 8/19 발표) 동일점 매출 +4%, 조정 EPS 1.22달러(+11%), 연간 EPS 가이던스 상향(GAAP 5.31~5.36달러). 그런데 주가는 11/16 종가 131.09달러(research 도구)로 하루 -2.44%, 5거래일 -5.1%, 1개월 -11.0%(stock_data 계산)이다. 확인된 회사 고유 악재는 없고, Marmaxx 부진 우려와 11/16 시장 급락(SPY 11/16 종가 739.95달러 research 도구, 하루 -1.91%)이 겹친 일시적 낙폭으로 본다. 3분기 실적은 11/18(수) 장전이라 평가 구간(11/17 종가) 밖이므로 구간 안에 실적 악재가 나올 일정이 없다. 조정 EPS 가이던스 중간값 대비 PER 약 25배(추정)로 싸지는 않지만, 질 좋은 회사가 시장과 함께 과하게 밀린 뒤 실적 전날 되돌림 여지를 본다. 바깥 관점(일반론): 큰 지수 하락 다음 날 방어적 우량주의 초과수익은 방향이 일정하지 않으며, 실적 전날 포지션 정리가 이어질 수도 있다.","risks":["11/17 장전 Home Depot 실적과 08:30 ET 10월 소매판매가 약하면 소매 업종 전체가 함께 밀릴 수 있다","실적 전날 불확실성 회피 매도(Marmaxx 부진 우려 지속)로 낙폭이 이어질 수 있다","시장이 기술주 중심으로 급반등하면 방어 소비주는 상대적으로 뒤처질 수 있다"],"catalyst":"회사 고유 촉매 없음(실적은 11/18 장전으로 구간 밖). 구간 안 간접 변수: 10월 소매판매(11/17 08:30 ET), HD 실적(11/17 장전)","flip_condition":"소매판매가 크게 부진하거나 HD가 소비 둔화를 경고해 소매주 전반이 장전 급락하면, 또는 TJX 실적 일정이 11/17로 앞당겨졌거나 사전 악재 공시가 확인되면 판단을 철회한다","p_beat":0.53,"exp_excess":0.3,"sources":[{"url":"https://query1.finance.yahoo.com/v8/finance/chart/TJX?range=3mo&interval=1d","as_of":"2026-11-16","retrieved_at":"2026-11-17T07:09:40+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=3mo&interval=1d","as_of":"2026-11-16","retrieved_at":"2026-11-17T07:09:40+09:00"},{"url":"https://www.boerse-express.com/news/articles/tjx-aktie-q3-zahlen-kommen-am-18-november-959218","as_of":"확인 못함","retrieved_at":"2026-11-17T07:09:40+09:00"},{"url":"https://sgbonline.com/tjxs-lifts-fy-eps-outlook-despite-q2-sales-shortfal-at-marmaxxl-sierra-opens-three-stores-in-quarter/","as_of":"2026-08","retrieved_at":"2026-11-17T07:09:40+09:00"},{"url":"https://www.just-style.com/news/tjx-q2-fy27-result/","as_of":"2026-08","retrieved_at":"2026-11-17T07:09:40+09:00"},{"url":"https://www.barchart.com/story/news/3986726/ross-stores-just-flipped-the-off-price-retail-story-after-tjx-s-marmaxx-miss","as_of":"확인 못함","retrieved_at":"2026-11-17T07:09:40+09:00"}]}]}
```
