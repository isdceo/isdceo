# 2026-11-12 라운드 r1 — wood (v2)

구간: KR 11/11 종가 → 11/12 종가 / US 11/11 종가 → 11/12 종가. 벤치마크 KOSPI·SPY. macro 도구는 KOSPI·SPY 조회 실패(HTTP 429)로 지수 기준값 확인 못함.

## KR 042700 한미반도체

렌즈: HBM용 TC 본더는 AI 메모리 S-곡선 위의 핵심 장비이고, 한미반도체는 이 장비 분야 선두 업체다. 오늘 새로 확인된 사건은 11/11 DART에 올라온 기업설명회(IR) 개최 안내공시 2건(20261111800075, 20261111800077)이다. 다만 DART 본문에서 IR 일시·내용은 확인하지 못했다. 3분기 실적(매출 1,810억원, 영업이익 908억원, 10/30 보도)은 이미 기준 종가 전에 알려진 정보다. 가격을 보면 11/11 종가 184,000원(research 도구)으로, stock_data 기준 1개월 -19.65%, 52주 고점 대비 -55.07%, 50일선 약 218,714원 아래에 있다. 며칠 연속 오른 테마를 쫓는 상황이 아니고 오히려 크게 빠진 상태다. 일반론: 큰 낙폭 뒤 IR 일정이 공시되면 소통 기대로 하루 반등이 나올 수 있지만, 출처가 있는 통계는 없다. 구간 안에서 확인된 촉매가 약하므로 확률은 기준선 근처로 둔다. 5년 TAM 관점(HBM4/5 패키징 장비 수요)은 종목을 고르는 필터로만 쓴다.

- 위험: IR 공시 본문(일시·내용)을 확인하지 못했다. 단순 NDR이면 가격 영향이 없을 수 있다 / 한화세미텍 등 경쟁사의 SK하이닉스향 TC 본더 공급으로 점유율 우려가 계속되고 있다 / 11/12 미국 장전 Nebius 실적 등 AI 인프라 재료는 한국 장 마감 뒤에 나온다. 반도체 업종 전체가 KOSPI보다 약할 수 있다 / 하락 추세(200일선 약 250,941원 아래)가 이어질 수 있다
- 촉매: 없음(구간 안에서 확정된 실적·계약 발표는 확인 못함. 11/11 IR 개최 안내공시가 있으나 IR 일시는 확인 못함)
- 뒤집을 조건: 장중 경쟁사 TC 본더 대량 수주나 HBM 고객 이탈 보도가 나오거나, IR 내용이 단순 해외 NDR로 확인되고 반도체 업종이 KOSPI보다 1%p 넘게 약하게 움직이면 판단을 철회한다
- p_beat 0.51, exp_excess 0.2%p
- 출처:
  - https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261111800075 (as_of 2026-11-11, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261111800077 (as_of 2026-11-11, retrieved_at 2026-11-12T06:51:14+09:00)
  - https://query1.finance.yahoo.com/v8/finance/chart/042700.KS?range=3mo&interval=1d (as_of 2026-11-11, retrieved_at 2026-11-12T07:08:39+09:00)
  - https://biz.sbs.co.kr/amp/article/20000343257 (as_of 확인 못함, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://www.heraldk.com/article/2026060814505772425 (as_of 2026-06, retrieved_at 2026-11-12T07:09:15+09:00)

## US NBIS Nebius Group

렌즈: Nebius는 AI 추론·학습용 GPU 클라우드(neocloud)다. 2분기 매출은 5.823억달러로 전년 대비 454% 늘었다(Zacks/Earnings Whispers 인용). 이는 컴퓨팅 비용이 떨어지면서 수요가 폭발하는 라이트의 법칙형 S-곡선의 한가운데다. 평가 구간 안 촉매는 확정돼 있다. 회사 공지(2026-10-30)에 따르면 3분기 실적은 11/12 장전, 콜은 8:00 ET로, 오늘 정규장 종가에 그대로 반영된다. 가격을 보면 11/11 종가 154.69달러(research 도구)로, stock_data 기준 1개월 -25.22%, 52주 고점 286.69달러 대비 -46.04%, 50일선 198달러 아래에 있다. 기대가 이미 크게 꺾인 상태라 실적 확인이 반등 계기가 될 수 있다. 일반론: 고변동 성장주는 실적 다음 날 움직임이 양방향으로 크고, 사전 낙폭이 클수록 '덜 나쁜' 결과에도 반등하는 경우가 있다(출처 없음). 반대 측면으로, 컨센서스 매출은 약 9.17억달러(Zacks·Earnings Whispers)인데 연간 컨센서스 34.8억달러가 회사 가이던스 상단 34억달러를 웃돈다. 바가 높다. 방향 불확실성이 크므로 p_beat는 기준선을 소폭 웃도는 수준으로 둔다.

- 위험: 연간 컨센서스(약 34.8억달러)가 가이던스 상단(34억달러)을 웃돈다. 가이던스를 유지하거나 하향하면 급락할 수 있다(1년 변동성 110%) / capex 확대에 따른 자금조달(전환사채·증자) 발표 가능성, 그리고 CoreWeave 경고 이후 neocloud 섹터의 심리가 약하다 / 실업수당 청구(08:30 ET) 결과로 금리가 오르면 고밸류 성장주가 SPY보다 약할 수 있다
- 촉매: 11/12 장전 3분기 실적 발표 및 8:00 ET 콘퍼런스콜(회사 공지, 구간 안). 거시: 11/12 08:30 ET 신규 실업수당 청구
- 뒤집을 조건: 3분기 매출이 컨센서스(약 9.17억달러)를 밑돌거나, 2026 연간 가이던스를 하향하거나, 대규모 주식 관련 자금조달을 동시에 발표하면 판단이 틀린 것이다(평가 종가까지 반영). 실적 직후 장전 거래에서 -10% 이상이면 철회 사유다
- p_beat 0.52, exp_excess 0.5%p
- 출처:
  - https://nebius.com/newsroom/nebius-group-announces-date-of-third-quarter-2026-results-and-conference-call (as_of 2026-10-30, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://www.zacks.com/stock/news/3026147/nebius-stock-ahead-of-q3-earnings-should-you-buy-hold-or-sell (as_of 확인 못함, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://www.earningswhispers.com/article/NBIS/22887 (as_of 확인 못함, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://finviz.com/news/416069/nebius-must-show-its-billion-dollar-ai-deals-can-outrun-losses-and-a-street-above-guidance (as_of 확인 못함, retrieved_at 2026-11-12T07:09:15+09:00)
  - https://query1.finance.yahoo.com/v8/finance/chart/NBIS?range=3mo&interval=1d (as_of 2026-11-11, retrieved_at 2026-11-12T07:08:35+09:00)
  - https://www.financecalendar.com/event/us-initial-jobless-claims-november-12-2026/ (as_of 확인 못함, retrieved_at 2026-11-12T07:06:56+09:00)

## JSON

```json
{"agent_id": "wood", "candidates": [{"market": "KR", "ticker": "042700", "name": "한미반도체", "rationale": "렌즈: HBM용 TC 본더는 AI 메모리 S-곡선 위의 핵심 장비이고, 한미반도체는 이 장비 분야 선두 업체다. 오늘 새로 확인된 사건은 11/11 DART에 올라온 기업설명회(IR) 개최 안내공시 2건(20261111800075, 20261111800077)이다. 다만 DART 본문에서 IR 일시·내용은 확인하지 못했다. 3분기 실적(매출 1,810억원, 영업이익 908억원, 10/30 보도)은 이미 기준 종가 전에 알려진 정보다. 가격을 보면 11/11 종가 184,000원(research 도구)으로, stock_data 기준 1개월 -19.65%, 52주 고점 대비 -55.07%, 50일선 약 218,714원 아래에 있다. 며칠 연속 오른 테마를 쫓는 상황이 아니고 오히려 크게 빠진 상태다. 일반론: 큰 낙폭 뒤 IR 일정이 공시되면 소통 기대로 하루 반등이 나올 수 있지만, 출처가 있는 통계는 없다. 구간 안에서 확인된 촉매가 약하므로 확률은 기준선 근처로 둔다. 5년 TAM 관점(HBM4/5 패키징 장비 수요)은 종목을 고르는 필터로만 쓴다.", "risks": ["IR 공시 본문(일시·내용)을 확인하지 못했다. 단순 NDR이면 가격 영향이 없을 수 있다", "한화세미텍 등 경쟁사의 SK하이닉스향 TC 본더 공급으로 점유율 우려가 계속되고 있다", "11/12 미국 장전 Nebius 실적 등 AI 인프라 재료는 한국 장 마감 뒤에 나온다. 반도체 업종 전체가 KOSPI보다 약할 수 있다", "하락 추세(200일선 약 250,941원 아래)가 이어질 수 있다"], "catalyst": "없음(구간 안에서 확정된 실적·계약 발표는 확인 못함. 11/11 IR 개최 안내공시가 있으나 IR 일시는 확인 못함)", "flip_condition": "장중 경쟁사 TC 본더 대량 수주나 HBM 고객 이탈 보도가 나오거나, IR 내용이 단순 해외 NDR로 확인되고 반도체 업종이 KOSPI보다 1%p 넘게 약하게 움직이면 판단을 철회한다", "p_beat": 0.51, "exp_excess": 0.2, "sources": [{"url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261111800075", "as_of": "2026-11-11", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261111800077", "as_of": "2026-11-11", "retrieved_at": "2026-11-12T06:51:14+09:00"}, {"url": "https://query1.finance.yahoo.com/v8/finance/chart/042700.KS?range=3mo&interval=1d", "as_of": "2026-11-11", "retrieved_at": "2026-11-12T07:08:39+09:00"}, {"url": "https://biz.sbs.co.kr/amp/article/20000343257", "as_of": "확인 못함", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://www.heraldk.com/article/2026060814505772425", "as_of": "2026-06", "retrieved_at": "2026-11-12T07:09:15+09:00"}]}, {"market": "US", "ticker": "NBIS", "name": "Nebius Group", "rationale": "렌즈: Nebius는 AI 추론·학습용 GPU 클라우드(neocloud)다. 2분기 매출은 5.823억달러로 전년 대비 454% 늘었다(Zacks/Earnings Whispers 인용). 이는 컴퓨팅 비용이 떨어지면서 수요가 폭발하는 라이트의 법칙형 S-곡선의 한가운데다. 평가 구간 안 촉매는 확정돼 있다. 회사 공지(2026-10-30)에 따르면 3분기 실적은 11/12 장전, 콜은 8:00 ET로, 오늘 정규장 종가에 그대로 반영된다. 가격을 보면 11/11 종가 154.69달러(research 도구)로, stock_data 기준 1개월 -25.22%, 52주 고점 286.69달러 대비 -46.04%, 50일선 198달러 아래에 있다. 기대가 이미 크게 꺾인 상태라 실적 확인이 반등 계기가 될 수 있다. 일반론: 고변동 성장주는 실적 다음 날 움직임이 양방향으로 크고, 사전 낙폭이 클수록 '덜 나쁜' 결과에도 반등하는 경우가 있다(출처 없음). 반대 측면으로, 컨센서스 매출은 약 9.17억달러(Zacks·Earnings Whispers)인데 연간 컨센서스 34.8억달러가 회사 가이던스 상단 34억달러를 웃돈다. 바가 높다. 방향 불확실성이 크므로 p_beat는 기준선을 소폭 웃도는 수준으로 둔다.", "risks": ["연간 컨센서스(약 34.8억달러)가 가이던스 상단(34억달러)을 웃돈다. 가이던스를 유지하거나 하향하면 급락할 수 있다(1년 변동성 110%)", "capex 확대에 따른 자금조달(전환사채·증자) 발표 가능성, 그리고 CoreWeave 경고 이후 neocloud 섹터의 심리가 약하다", "실업수당 청구(08:30 ET) 결과로 금리가 오르면 고밸류 성장주가 SPY보다 약할 수 있다"], "catalyst": "11/12 장전 3분기 실적 발표 및 8:00 ET 콘퍼런스콜(회사 공지, 구간 안). 거시: 11/12 08:30 ET 신규 실업수당 청구", "flip_condition": "3분기 매출이 컨센서스(약 9.17억달러)를 밑돌거나, 2026 연간 가이던스를 하향하거나, 대규모 주식 관련 자금조달을 동시에 발표하면 판단이 틀린 것이다(평가 종가까지 반영). 실적 직후 장전 거래에서 -10% 이상이면 철회 사유다", "p_beat": 0.52, "exp_excess": 0.5, "sources": [{"url": "https://nebius.com/newsroom/nebius-group-announces-date-of-third-quarter-2026-results-and-conference-call", "as_of": "2026-10-30", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://www.zacks.com/stock/news/3026147/nebius-stock-ahead-of-q3-earnings-should-you-buy-hold-or-sell", "as_of": "확인 못함", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://www.earningswhispers.com/article/NBIS/22887", "as_of": "확인 못함", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://finviz.com/news/416069/nebius-must-show-its-billion-dollar-ai-deals-can-outrun-losses-and-a-street-above-guidance", "as_of": "확인 못함", "retrieved_at": "2026-11-12T07:09:15+09:00"}, {"url": "https://query1.finance.yahoo.com/v8/finance/chart/NBIS?range=3mo&interval=1d", "as_of": "2026-11-11", "retrieved_at": "2026-11-12T07:08:35+09:00"}, {"url": "https://www.financecalendar.com/event/us-initial-jobless-claims-november-12-2026/", "as_of": "확인 못함", "retrieved_at": "2026-11-12T07:06:56+09:00"}]}]}
```
