# 2026-11-20 라운드 — wood (캐시 우드 철학 분석가, 지침 v2)

작성: 2026-11-20 07:1x KST. 공통 자료 snapshot.json sha256 899d5156...8c85 확인. 진행자 일정표 확인(미시간대 심리·Waller/Cook 발언·월간 옵션 만기, 진행자 일정표 기준).

## 구간
- KR: 11/19 15:30 종가 → 11/20 15:30 종가 (KOSPI 대비). research macro: KOSPI 기준일 행 없음(기준 종가 확인 못함).
- US: 11/19 종가 → 11/20 종가 (SPY 대비). SPY 11/19 종가 715.87달러(research 도구, 1차 조회), 10년물 5.052%, 원달러 1334.17.

## US — KEYS (Keysight Technologies)
1. 구간: 기준 11/19 종가 281.42달러(research 도구).
2. 일정: 11/19 장후 FY26 4분기 실적 발표(IR 보도자료 11/19, 콜 1:30pm PT) → 11/20 정규장 반응이 구간 안. 배당·지수변경 확인 못함. 거시: 미시간대·연준 발언·옵션 만기(진행자 일정표 기준).
3. 바깥 관점(일반론): 가이던스 상회 실적 다음 날은 대체로 양의 반응이나 컨센서스에 따라 엇갈림.
4. 안쪽 관점(호재): 매출 $1.99B(+41%), 수주 $2.34B(+53%), 비GAAP EPS $3.61 — 8/18 회사 가이던스(매출 $1.930~1.950B, EPS $3.34~3.40) 상회. 1Q27 가이던스 매출 $2.040~2.060B, EPS $3.63~3.69. 월가 컨센서스·시간외 반응 확인 못함. 주가 1개월 -17.6%, 50일선 331달러·200일선 322달러 아래(stock_data, 11/19 기준) — 기대 낮아진 상태.
5. 반대 시나리오: 컨센서스가 회사 가이던스보다 높아 1분기 가이던스가 실망으로 읽힘.
- p_beat 0.58, exp_excess +1.5%p.

## KR — 012330 현대모비스
1. 구간: 기준 11/19 종가 341500원(research 도구; 도구가 반환한 URL이 012330.KQ 형태였음 — 값은 도구 값 그대로).
2. 일정: DART 20261119800372 — 11/20 13:10 iM증권 Corporate Day 기관 소그룹 IR(정례). 실적·배당락·보호예수 공시 없음(disclosures 기준). 한국 거시 일정 확인 못함.
3. 바깥 관점(일반론): 정례 기관 IR은 하루 주가 영향이 작다.
4. 안쪽 관점(중립~소폭 호재): 아틀라스 액추에이터 공급사(로봇 S-곡선). 직전 장 마감 뒤 새 기사·공시 확인 못함. 3개월 -34%(stock_data).
5. 반대 시나리오: IR 무소식 + 자동차 부품주 약세.
- KR 관망 소진으로 실제 종목 제출. p_beat 0.50, exp_excess 0.0%p (저확신).

참고: KR 공시 중 렌즈에 맞는 새 사건(수주·승인·실적)은 확인하지 못했다. 한미반도체 IR은 11/24(구간 밖), HLB 합병·엘앤에프 CB는 렌즈 밖/악재.

## JSON
```json
{"agent_id":"wood","candidates":[{"market":"KR","ticker":"012330","name":"현대모비스","rationale":"구간: 11/19 종가 341500원(research 도구) → 11/20 종가. 혁신 필터: 보스턴다이내믹스 아틀라스용 액추에이터(로봇 원가의 핵심 부품) 공급사로 휴머노이드 S-곡선 위에 있다(CES 2026 발표, 10월 3분기 실적 때 의왕연구소 시제품 생산 언급, 기사 요약 기준). 구간 안 사건: DART 공시(20261119800372, 11/19 접수)로 11/20 13:10 여의도 iM증권 Corporate Day 기관 소그룹 IR 확인. 새 수주·실적 공시는 없음. 바깥 관점(일반론): 정례 기관 IR은 하루 주가에 미치는 영향이 작다. 안쪽 관점: 1개월 -1.3%, 3개월 -34%(stock_data)로 이미 크게 눌린 상태라 로봇 메시지가 나오면 하방이 제한될 수 있다는 정도의 약한 근거(중립~소폭 호재). 직전 장 마감 뒤~08:30 새 기사·공시는 확인 못함. KR은 이번 주 관망을 이미 써서 렌즈에 가장 가까운 저확신 종목을 낸다. 반대 시나리오: IR에서 새 정보가 없고 자동차 부품주 약세에 휩쓸려 지수에 진다.","risks":["IR이 정례 행사라 새 정보가 없을 가능성이 높고 하루 촉매로 약함","3개월 -34% 하락 추세가 이어지고 완성차·관세 뉴스에 민감","휴머노이드 액추에이터 본 공급은 2028년 예정(기사 기준)이라 단기 실적 기여 없음"],"catalyst":"11/20 13:10 iM증권 Corporate Day 기관 IR(DART 20261119800372) — 정례 행사로 약한 촉매","flip_condition":"장 시작 전 현대차그룹·보스턴다이내믹스 관련 악재나 관세 악재, 또는 IR 뒤 로봇 일정 지연 언급이 나오면 판단 철회","p_beat":0.5,"exp_excess":0.0,"sources":[{"url":"https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261119800372","as_of":"2026-11-19","retrieved_at":"2026-11-20T07:11:44+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/012330.KQ?range=3mo&interval=1d","as_of":"2026-11-19","retrieved_at":"2026-11-20T07:11:44+09:00"},{"url":"https://biz.sbs.co.kr/amp/article/20000343232","as_of":"확인 못함","retrieved_at":"2026-11-20T07:11:44+09:00"}]},{"market":"US","ticker":"KEYS","name":"Keysight Technologies","rationale":"구간: 11/19 종가 281.42달러(research 도구) → 11/20 종가. 혁신 필터: AI 인프라(고속 광통신·데이터센터)·6G 테스트 플랫폼 공급자. 새 사건: 11/19 장 마감 뒤 FY26 4분기 실적 발표(콜 1:30pm PT, IR 보도자료). 매출 19.9억달러(+41%), 수주 23.4억달러(+53%), 비GAAP EPS 3.61달러로 회사 자체 가이던스(매출 19.3~19.5억, EPS 3.34~3.40, 8/18 발표)를 넘었다. 1분기 가이던스 매출 20.4~20.6억·EPS 3.63~3.69로 순차 성장. 수주가 매출보다 빨리 늘어 단위경제성 개선이 이어진다는 신호. 월가 컨센서스 대비와 시간외 반응은 확인 못함. 바깥 관점(일반론): 가이던스 상회 실적 다음 거래일은 대체로 양(+)의 반응이나 기대치에 따라 엇갈린다. 안쪽 관점: 1개월 -17.6%, 50일선 331달러 아래(stock_data)로 기대가 낮아진 상태라 호재. 반대 시나리오: 컨센서스가 가이던스보다 높아 1분기 가이던스가 기대 미달로 읽힌다.","risks":["월가 컨센서스와 시간외 반응을 확인 못해 이미 기대에 반영됐을 수 있음","CFO 교체(11/2 발표)와 연간 가이던스 미제시가 불확실성으로 읽힐 수 있음","옵션 만기·연준 발언 등 거시 변동성, 1년 변동성 47%로 큰 종목"],"catalyst":"11/19 장후 FY26 4분기 실적·1분기 가이던스 발표에 대한 11/20 정규장 첫 반응","flip_condition":"프리마켓에서 KEYS가 하락하거나 1분기 가이던스가 컨센서스 미달이라는 보도가 확인되면 판단 철회","p_beat":0.58,"exp_excess":1.5,"sources":[{"url":"https://investor.keysight.com/investor-news-and-events/financial-press-releases/press-release-details/2026/Keysight-Technologies-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Results/default.aspx","as_of":"2026-10-31","retrieved_at":"2026-11-20T07:11:44+09:00"},{"url":"https://investor.keysight.com/investor-news-and-events/financial-press-releases/press-release-details/2026/Keysight-Technologies-Reports-Third-Quarter-2026-Results/default.aspx","as_of":"2026-07-31","retrieved_at":"2026-11-20T07:11:44+09:00"},{"url":"https://investor.keysight.com/investor-news-and-events/financial-press-releases/default.aspx","as_of":"확인 못함","retrieved_at":"2026-11-20T07:11:44+09:00"},{"url":"https://query1.finance.yahoo.com/v8/finance/chart/KEYS?range=3mo&interval=1d","as_of":"2026-11-19","retrieved_at":"2026-11-20T07:11:44+09:00"}]}]}
```
