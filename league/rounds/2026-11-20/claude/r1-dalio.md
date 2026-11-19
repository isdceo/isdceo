# r1-dalio (2026-11-20 라운드, v2)

## 국면 판단 (원칙)
- 원칙 1: 국면을 먼저 정한다. 연준은 9월 인상 이후 긴축, 미 10년물 5.05%(11/19), 브렌트 90달러대 -> 물가 고착. 동시에 SPY 4일 연속 하락(11/19 715.87, -2.0%), KOSPI 52주 고점 대비 -44%, AI주 디레버리징 -> 성장 우려. 4분면: 성장↓ x 인플레이션↑(고착) 쪽, 단기적으로는 금리·유가가 내려오는 위험회피 국면.
- 원칙 2: 한 베팅에 몰지 않는다. KR은 환율·유가(수입비용) 요인, US는 금리 요인으로 서로 다른 거시 위험에 노출시킨다. 둘 다 지수의 주된 하락 요인(반도체/AI)과 상관이 낮은 종목.
- 원칙 3: 틀릴 시나리오를 확률로 둔다.
  - KR 대한항공: 원화 강세·유가 하락 유지 + 지수 약세(이길 확률 높음) 약 45%, 지수 반도체 주도 반등(질 확률 높음) 약 30%, 급등 뒤 차익실현 약 25%. 종합 p_beat 0.53.
  - US DUK: 위험회피 지속·금리 하락(유리) 약 45%, 저가매수 반등(불리) 약 35%, 매파 발언 금리 반등(불리) 약 20%. 종합 p_beat 0.53.

## 데이터(기준 시각 2026-11-20T07:12:47+09:00)
- research 도구: 대한항공 11/19 종가 32450원(도구가 003490.KQ URL을 반환, 값은 .KS stock_data와 같음), DUK 11/19 종가 128.86달러, USD/KRW 1333.92. KOSPI 11/19 기준일 행 없음, SPY·^TNX는 research 도구에서 429(stock_data로 별도 확인).
- stock_data: BZ=F 11/18 91.95 -> 11/19 90.05, ^TNX 11/13 5.15 -> 11/19 5.05, DXY 103.93, ES=F 7182.5(11/19 행, 시각 확인 못함).

## 후보 JSON
```json
{
 "agent_id": "dalio",
 "candidates": [
  {
   "market": "KR",
   "ticker": "003490",
   "name": "대한항공",
   "rationale": "국면 판단: 미국 10년물 5% 위, 연준 9월 인상 뒤 긴축 지속(성장 둔화 우려+물가 고착 = 스태그 쪽 4분면). 위험자산 디레버리징 구간에서 KOSPI는 11/18 5067.44(stock_data, 52주 고점 대비 -44%), SPY는 11/19 715.87달러(stock_data)로 하루 -2% 밀려 오늘 한국은 약세 출발 가능성이 크다(추정). 이 환경에서 반도체 베타를 피하고 거시 변수 두 개가 동시에 유리한 업종을 고른다: 원화 강세(USD/KRW 11/19 1333.92 research 도구, 200일선 1439 아래)와 유가 하락(브렌트 11/18 91.95→11/19 90.05달러 stock_data, 한국 마감 뒤 추가 하락분이 오늘 반영). 항공은 달러 비용(연료·리스) 비중이 커 두 변수 민감도가 가장 큰 업종이며 대한항공 11/19 종가 32450원(research 도구), 1개월 +19%로 KOSPI와 역상관 흐름. 바깥 관점(일반론): 지수 급락일에 지수와 다른 거시 요인을 가진 종목은 상대 방어가 되기 쉽다. 안쪽: 11/18 IR 개최 안내공시 외 특이 공시 없음(내용 확인 못함), 직전 장 마감 뒤 뉴스 중립.",
   "risks": [
    "1개월 +19% 급등 뒤 차익 실현, 지수 급반등(반도체 주도) 시 상대 열세",
    "원/달러 급반등(위험회피 달러 강세)이나 유가 반등 시 거시 근거 소멸",
    "IR 내용·일정 확인 못함 — 예상 밖 내용 가능"
   ],
   "catalyst": "없음(확정 촉매 없음). 한국 마감 뒤 브렌트 하락분 반영과 원화 강세 유지가 거시 순풍. 한국 거시 일정 확인 못함(진행자 일정표 기준)",
   "flip_condition": "장 초반 원/달러가 1345원 위로 급등하거나 브렌트가 92달러 위로 반등, 또는 외국인 반도체 순매수로 KOSPI가 1% 넘게 반등하는 위험선호 전환",
   "p_beat": 0.53,
   "exp_excess": 0.3,
   "sources": [
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/003490.KS?range=3mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/KRW%3DX?range=3mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?range=1mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=1mo&interval=1d",
     "as_of": "2026-11-18",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261118800330",
     "as_of": "2026-11-18",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://www.ajc.com/news/2026/11/nvidia-and-other-ai-stocks-hold-steady-following-their-latest-sell-off/",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    }
   ]
  },
  {
   "market": "US",
   "ticker": "DUK",
   "name": "Duke Energy",
   "rationale": "국면: 성장 우려 확대+물가 고착. SPY 11/19 715.87달러로 하루 -2.0%, 4거래일 연속 하락(stock_data), AI·반도체 주도 매도(AP 11/17 기사). 같은 기간 10년물은 5.15%(11/13)→5.05%(11/19)로 내려와(stock_data ^TNX) 위험회피형 금리 하락이 진행 중이다. 이 조합(주가↓·금리↓)에서 가장 유리한 업종은 금리 민감·저베타 유틸리티. DUK 11/19 종가 128.86달러(research 도구), 11/19 하루 -0.9%로 SPY 대비 +1.1%p 방어, 1년 변동성 낮음. 오늘 연준 Waller·Cook 발언과 미시간대 심리지수(진행자 일정표 기준, 시각 확인 못함)가 금리 방향을 정하는데, 성장 둔화 신호가 나오면 금리↓→유틸리티 상대 강세. 월간 옵션 만기로 지수 변동 확대 가능 — 저베타가 유리. 바깥 관점(일반론): 하락 추세 지속일에 유틸리티는 지수 대비 방어적이지만 반등일엔 뒤처진다. 안쪽: 3분기 실적(11/5) 뒤 노스캐롤라이나 요금 판결이 11월 중순 예정이라는 보도(검색 요약, 확인 못함). 배당락일 확인 못함.",
   "risks": [
    "지수 반등(엔비디아 등 AI 저가매수) 시 저베타 탓에 상대 열세",
    "연준 매파 발언으로 금리 재상승 시 유틸리티 동반 하락",
    "노스캐롤라이나 요금 판결 결과 불확실(일정·내용 확인 못함)"
   ],
   "catalyst": "연준 Waller·Cook 발언, 미시간대 소비자심리(11/20, 시각 확인 못함 — 진행자 일정표 기준). 종목 고유 확정 촉매 없음",
   "flip_condition": "장 전 선물이 1% 넘게 반등하거나 연준 발언이 추가 인상 쪽으로 기울어 10년물이 5.10% 위로 반등",
   "p_beat": 0.53,
   "exp_excess": 0.3,
   "sources": [
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/DUK?range=3mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=1mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=1mo&interval=1d",
     "as_of": "2026-11-19",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://www.ajc.com/news/2026/11/nvidia-and-other-ai-stocks-hold-steady-following-their-latest-sell-off/",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    },
    {
     "url": "https://finviz.com/news/416697/duke-energy-reports-third-quarter-2026-financial-results",
     "as_of": "확인 못함",
     "retrieved_at": "2026-11-20T07:12:47+09:00"
    }
   ]
  }
 ]
}
```
