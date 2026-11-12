# 2026-11-13 라운드 · wood (지침 v2) · Claude 팀

교육·토론용 분석이며 투자 권유가 아님.

## 1. 구간
- KR: 11/12 종가(15:30) → 11/13 종가(15:30), 지수 KOSPI. US: 11/12 종가(KST 11/13 06:00) → 11/13 종가(KST 11/14 06:00), 지수 SPY.
- 진행자 일정표 확인: 미국 10월 PPI 11/13 08:30 ET 구간 안(US). AMAT 실적 날짜는 직접 확인 — 11/12 16:30 ET 컨퍼런스콜(장후). US에는 기준 종가 뒤·평가 세션 전, KR에는 기준 종가 뒤 정보.

## 2. 일정 점검
- AMAT: FY4Q26 실적 11/12 장후 발표(구간 안 첫 반영). 배당락·지수변경: 확인 못함.
- 원익IPS(240810): 3분기 잠정실적은 11/09 DART 공시(rcpNo 20261109900411)로 이미 반영. 공통 자료 disclosures에서 11/10~11/13 추가 공시 없음. 배당락·보호예수·대주주 매도: 확인 못함. MarketScreener 일정상 실적 이벤트 11/17 전후 표기(as_of 확인 못함, 구간 밖).
- 거시: 미국 10월 PPI 11/13(구간 안, 컨센서스 확인 못함). 한국 금통위 등 구간 안 확인 못함.
- research 도구: KOSPI 기준일 행 없음, SPY 조회 실패(429) — 지수 기준값 확인 못함.

## 3. 바깥 관점 (일반론, 숫자 없음)
실적·가이던스 동반 상회 다음 거래일은 대체로 양(+) 반응이 우세하지만, 장후 상승분 일부가 정규장에서 되돌려지는 경우도 흔하다. 대형 장비사 호실적의 동종 해외 장비주 파급은 방향은 같지만 크기는 작은 편이다.

## 4. 안쪽 관점
- AMAT(호재, 11/12 16:11~16:24 ET 보도): 매출 104.1억달러(+53%), 반도체 시스템 80억달러(+64%), 조정 EPS 4.16달러. 1Q FY27 가이던스 매출 111억달러±5억, EPS 4.35달러±0.20 — Investing.com·Crypto Briefing 기준 예상치 상회. Benzinga는 컨센서스를 108.9억달러·4.26달러로 잡아 4분기 미달로 보도(출처 간 충돌). 장후 +1.5%(Investing.com)~+3%(Crypto Briefing). 11/12 종가 380.95달러(research 도구). stock_data(11/12 기준): 1개월 -14.71%, 52주 고점 대비 -47.25%, 50일선 439.22달러 아래, 1년 변동성 63.65%.
- 원익IPS(간접 호재): 11/12 종가 79200원(research 도구). stock_data(11/12 기준): 1개월 -34.81%, 52주 고점 대비 -56.79%, 50일선 108860원 아래. 자체 새 공시는 없고, 근거는 AMAT의 증착·AI 생산능력 해석 하나뿐이라 확률을 낮게 잡음.
- 혁신 필터(점수 근거 아님): 두 종목 모두 AI 반도체 생산능력이라는 S-곡선의 장비 레이어에 속함. AMAT의 매출 성장 가속(+21% 연간 → 4분기 +53%)은 단위경제성보다는 수요 곡선 확인 신호.

## 5. 반대 시나리오
- AMAT: 컨센서스 해석 충돌(Benzinga '미달')과 PPI 상회가 겹쳐 장후 상승분이 정규장에서 사라지고 고베타로 SPY보다 더 빠짐.
- 원익IPS: 한 달 -35% 하락을 만든 국내 고객 투자 관련 우려(원인 확인 못함)가 AMAT 해석보다 강하게 작용.

## 6. 결론 (JSON)
```json
{"agent_id":"wood","candidates":[
{"market":"KR","ticker":"240810","name":"원익IPS","rationale":"AI 메모리 투자 S-곡선 위의 국내 증착 장비주. 새 사건은 KR 기준 종가 뒤에 나온 Applied Materials(AMAT)의 11/12 장후(미 동부 16:00대) FY4Q26 실적이다. 매출 104.1억달러(전년비 +53%, 반도체 시스템 +64%), 조정 EPS 4.16달러로 컨센서스(약 103억달러·4.06달러)를 넘었고, 1Q FY27 매출 가이던스 111억달러가 예상치(108.4억~108.9억달러)를 웃돌았다(Investing.com·Crypto Briefing, 컨센서스 수치는 출처마다 다름). 세계 1위 장비사가 AI 칩 생산능력 확대를 근거로 가이던스를 올렸으니, 같은 공정(증착) 국내 장비주에는 오늘 장에 긍정적 해석이 반영될 여지가 있다. 원익IPS는 11/12 종가 79200원(research 도구)으로 1개월 -34.8%, 52주 고점 대비 -56.8%, 50일선 108860원 아래(stock_data, 11/12 기준) — 며칠 오른 테마 추격이 아니라 급락한 장비주에 새 사건이 생긴 경우다. 3분기 잠정실적은 11/09 공시로 이미 반영됨(DART 20261109900411). 구간 안 원익IPS 고유 공시·배당락은 공통 자료에서 확인 못함. 5년 TAM 관점(메모리 장비 사이클)은 혁신 기업 필터용일 뿐 오늘 점수 근거는 AMAT 해석 하나다.","risks":["AMAT 장후 상승폭이 크지 않아(+1.5~3%, 출처마다 다름) KR 장비주에 해석이 약하게 전달되거나, 한 달 -35% 급락을 만든 원인(삼성 투자 지연 등, 확인 못함)이 다시 부각될 수 있음","1Q 가이던스 범위(±5억달러)와 컨센서스 정의가 출처마다 달라 '미달'로 해석되는 기사가 나올 수 있음(Benzinga는 매출·EPS 미달로 보도)","코스닥 수급·외국인 반도체 매도로 KOSPI 대비 하락. KOSPI 11/12 값은 research 도구에서 기준일 행 없음"],"catalyst":"AMAT FY4Q26 실적·1Q FY27 가이던스 상향(11/12 장후, KR 기준 종가 뒤) — 11/13 KR 장에서 처음 반영. 원익IPS 자체 구간 안 촉매는 없음","flip_condition":"장 시작 전 AMAT 장후 주가가 하락 전환하거나 컨퍼런스콜에서 메모리·한국 고객 투자 축소 언급이 확인되면, 또는 원익IPS 악재 공시(대주주 매도·유상증자)가 나오면 판단 철회","p_beat":0.56,"exp_excess":0.6,"sources":[{"url":"https://www.investing.com/news/earnings/applied-materials-shares-trade-lower-depite-q4-beat-5023202","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://cryptobriefing.com/applied-materials-earnings-record-q4-revenue-2026-11/","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://www.benzinga.com/markets/earnings/26/11/63224703/applied-materials-reports-q4-earnings-raises-guidance-as-ai-drives-strong-chip-demand","as_of":"2026-11","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/240810.KQ?range=3mo&interval=1d","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261109900411","as_of":"2026-11-09","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://www.marketscreener.com/quote/stock/WONIK-IPS-CO-LTD-27891168/calendar/","as_of":"확인 못함","retrieved_at":"2026-11-13T07:09:38+09:00"}]},
{"market":"US","ticker":"AMAT","name":"Applied Materials","rationale":"AI 칩 생산능력 확대라는 S-곡선의 '곡괭이' 기업. 새 사건은 11/12 장 마감 직후(Investing.com 16:11, Crypto Briefing 16:24 EST 게재) 발표된 FY4Q26 실적이다. 매출 104.1억달러(+53% YoY, 반도체 시스템 80억달러 +64%), 조정 EPS 4.16달러(예상 약 4.06달러), FY26 매출 344.5억달러(+21%)·EPS 12.89달러(+37%). 1Q FY27 가이던스 매출 111억달러±5억·EPS 4.35달러±0.20로 예상치(매출 108.4억~108.9억, EPS 4.25~4.26)를 웃돌았다. 장후 주가는 +1.5%(Investing.com)~+3%(Crypto Briefing). 채점 기준은 11/12 종가 380.95달러(research 도구)이므로 장후 반응이 평가 세션에 그대로 들어온다. 주가는 1개월 -14.7%, 52주 고점 대비 -47.3%, 50일선(439.22달러) 아래(stock_data, 11/12 기준) — 며칠 연속 오른 상태가 아니라 눌린 상태에서 '매출 성장 가속+가이던스 상향'이 확인됐다. 바깥 관점(일반론): 실적·가이던스 동반 상회 다음 거래일은 대체로 양(+)의 반응이 우세하나 장후 상승분이 정규장에서 일부 되돌려지는 경우도 흔하다.","risks":["Benzinga는 컨센서스를 108.9억달러·4.26달러로 잡아 4분기 '미달'로 보도 — 컨센서스 해석 차이로 장후 상승분이 정규장에서 되돌려질 수 있음","11/13 08:30 ET 미국 10월 PPI(구간 안, 컨센서스 확인 못함)가 높게 나오면 고변동성(1년 변동성 63.7%) 반도체 장비주가 SPY보다 더 크게 빠질 수 있음","11/12 정규장에서 이미 약세였다는 표시(Investing.com 페이지 -3.58%, 시점 불명)처럼 섹터 매도세(중국 수출규제 등, 확인 못함)가 이어질 수 있음"],"catalyst":"FY4Q26 실적·1Q FY27 가이던스 상향(11/12 장후 발표, 11/13 정규장에서 첫 반영). 거시: 10월 PPI 11/13 08:30 ET","flip_condition":"11/13 프리마켓에서 AMAT가 11/12 종가 아래로 내려오거나, 컨퍼런스콜에서 중국 매출 급감·2027 상반기 WFE 둔화 언급이 부각되면, 또는 PPI 쇼크로 나스닥 급락 시 판단 철회","p_beat":0.59,"exp_excess":1.2,"sources":[{"url":"https://www.investing.com/news/earnings/applied-materials-shares-trade-lower-depite-q4-beat-5023202","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://cryptobriefing.com/applied-materials-earnings-record-q4-revenue-2026-11/","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://www.benzinga.com/markets/earnings/26/11/63224703/applied-materials-reports-q4-earnings-raises-guidance-as-ai-drives-strong-chip-demand","as_of":"2026-11","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://www.panabee.com/news/applied-materials-earnings-q4-2026","as_of":"확인 못함","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-fourth-quarter-and-fiscal-year-2026","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/AMAT?range=3mo&interval=1d","as_of":"2026-11-12","retrieved_at":"2026-11-13T07:09:38+09:00"}]}
]}
```
