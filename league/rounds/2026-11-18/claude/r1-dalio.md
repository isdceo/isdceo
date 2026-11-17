# 2026-11-18 라운드 r1 — dalio (v2)

## 국면 판단
미 10년물 11/17 5.103%(research 도구, 200일선 4.59% 위), KOSPI 52주 고점 대비 -44%(stock_data, 11/16), NVDA 고점 대비 -35%, 원·달러 1334.9(원화 강세). 성장 기대 하락 + 금리 높음 사분면(AI 자산 디레버리징). KOSPI 11/17 종가는 research 도구 '기준일 행 없음' — 확인 못함.

## 구간 안 촉매
NVIDIA 11/17 장 마감 후 8-K: 매출 115.8B(컨센서스 109.3B, S&P Global 11/12 프리뷰), 4Q 가이던스 130.0B±3%, GM 가이던스 71~72%(3Q 74.8%). 시간외 반응 확인 못함. 미국 10월 주택착공 08:30 ET(진행자 일정표 기준).

## 시나리오(오늘 종가까지)
- AI 수요 확인 → 반도체 상대강세: 55%
- 마진 가이던스 하락에 sell-the-news: 30%
- 지수 동조로 초과수익 ~0: 15%

## 분산 메모
KR 하이닉스·US NVDA 두 카드가 같은 AI 설비투자 요인에 노출 — 집중을 인정하고 확률을 0.55로 제한.

## JSON
```json
{
 "agent_id": "dalio",
 "candidates": [
  {
   "market": "KR",
   "ticker": "000660",
   "name": "SK하이닉스",
   "rationale": "국면: 미 10년물 11/17 5.103%(research 도구), 200일선(4.59%) 위이고 KOSPI는 52주 고점 대비 -44%(stock_data, 11/16 기준)로 '성장 기대 하락 + 금리 높음' 사분면(AI 자산 디레버리징). 성장주에 불리한 국면이나 구간 안 확인된 촉매가 있다: NVIDIA가 11/17 장 마감 후 8-K로 3분기 매출 115.8B달러(데이터센터 107.6B)를 발표했고 이는 S&P Global 프리뷰의 Visible Alpha 컨센서스 109.3B를 약 6% 상회, 4분기 가이던스 130.0B(중국 데이터센터 제외)다. HBM 공급사 하이닉스가 AI 설비투자 민감도가 가장 크다. 11/17 종가 1098000원(research 도구), 52주 고점 대비 -62%, 50일선 1522700원 아래(stock_data)로 과매도 상태에서 수요 확인 신호가 들어온다. 원·달러 11/17 1334.9(research 도구), 52주 고점 대비 원화 강세는 외국인 수급에 우호적 참고 신호. 공통 자료 disclosures(11/04~)에 하이닉스 공시 없음. KOSPI 11/17 종가는 도구에서 '기준일 행 없음'으로 확인 못함. 바깥 관점(일반론): 미국 대형 AI 실적 서프라이즈 다음 날 한국 메모리주는 동조하는 경향이 있으나 시초 갭 후 되밀림도 흔하다. 리스크 패리티 관점: 하이닉스는 KOSPI 내 비중이 커 지수와 상관이 높아 초과수익 폭은 제한적이고, 변동성 92%로 한 베팅의 위험 기여가 크다.",
   "risks": [
    "NVIDIA 4분기 총이익률 가이던스 71~72%로 3분기 74.8%에서 하락 — 시장이 마진 피크/가격 압박으로 해석하면 메모리주에 역풍",
    "미 10년물 5.1% 고금리 국면의 디레버리징이 이어지면 실적 호재에도 외국인 반도체 매도가 지속될 수 있음",
    "하이닉스의 KOSPI 비중이 커 지수와 같이 움직여 초과수익이 0 근처에 머물 가능성",
    "NVIDIA 시간외 반응을 직접 확인하지 못함 — 시장이 이미 기대치를 더 높게 잡았다면 sell-the-news"
   ],
   "catalyst": "NVIDIA 11/17 장 마감 후 3분기 실적(매출 115.8B달러, 4분기 가이던스 130.0B달러) — 11/18 한국 정규장에 첫 반영",
   "flip_condition": "장 초반 NVIDIA 시간외/야간 선물이 하락으로 확인되거나, 하이닉스가 시초가 대비 KOSPI보다 약하게 출발하고 외국인 반도체 순매도가 확대되면 판단 철회",
   "p_beat": 0.55,
   "exp_excess": 0.5,
   "sources": [
    {
     "url": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000088/q3fy27pr.htm",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:08:54+09:00"
    },
    {
     "url": "https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/11/nvidia-earnings-preview-q3-2027",
     "as_of": "2026-11-12",
     "retrieved_at": "2026-11-18T07:08:54+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/000660.KS?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:08:46+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/KRW%3DX?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:07:52+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:07:52+09:00"
    }
   ]
  },
  {
   "market": "US",
   "ticker": "NVDA",
   "name": "Nvidia",
   "rationale": "원칙1 국면: 10년물 11/17 5.103%(research 도구), SPY 11/17 종가 732.44(research 도구). 고금리 속 AI 성장 기대가 꺾이는 사분면이라 NVDA는 11/17 종가 155.46달러(research 도구)로 1개월 -28%, 52주 고점 대비 -35%, 50일선 211.75 아래(stock_data)까지 밀렸다. 원칙2 오늘 구간에서 가격을 움직이는 것은 거시가 아니라 이 회사 자체의 '수요 데이터'이며, 이는 AI 설비투자 사이클(이번 신용·성장 사이클의 핵심 엔진)에 대한 거시 신호이기도 하다. 8-K(11/17): 매출 115.8B(전분기 +20%, 전년 +103%), 데이터센터 107.6B, GAAP EPS 2.70, 4분기 가이던스 130.0B±3%(중국 데이터센터 제외), 자사주 한도 150B 추가. 컨센서스 109.3B(S&P Global 11/12 프리뷰, Visible Alpha) 대비 약 6% 상회. 바깥 관점(일반론): 큰 폭 하락 뒤 실적이 컨센서스를 분명히 넘으면 다음 거래일 숏커버·리밸런싱으로 반등하는 경향이 있으나, 최근 분기들처럼 시간외 반전도 흔하다. 시간외 반응은 확인 못함, 4분기 가이던스 대비 컨센서스도 확인 못함 — 그래서 확률을 0.55로 제한한다. 구간 안 거시: 10월 주택착공 08:30 ET(진행자 일정표 기준) 외 금리 충격 일정은 확인 못함. 분산 관점: NVDA는 SPY 내 최대 비중군이라 지수와 상관이 높고, 같은 베팅을 KR 하이닉스로도 하고 있어 두 카드가 같은 AI 요인에 집중된다는 점을 명시한다.",
   "risks": [
    "4분기 총이익률 가이던스 71~72%로 3분기 74.8%에서 하락 — 마진 피크 해석 시 실적 호재에도 하락 가능",
    "매수측 기대(위스퍼)가 130B보다 높았다면 sell-the-news, 시간외 반응을 확인하지 못함",
    "10년물 5.1% 고금리 국면에서 금리 추가 상승 시 고밸류 성장주 일괄 디레이팅",
    "NVDA의 SPY 내 높은 비중으로 초과수익 폭이 제한되고, KR 하이닉스 카드와 같은 요인에 노출되어 분산 효과가 작음"
   ],
   "catalyst": "NVIDIA 11/17 장 마감 후 3분기 실적 발표(매출 115.8B달러, 4분기 가이던스 130.0B달러, 자사주 한도 150B 추가) — 11/18 정규장에서 첫 반영. 그 외 10월 주택착공 08:30 ET(진행자 일정표 기준)",
   "flip_condition": "장 전 NVDA 프리마켓이 SPY 선물보다 약하거나, 4분기 가이던스가 컨센서스를 밑돌았다는 확인 보도가 나오면 판단 철회; 10년물이 5.2% 위로 급등하면 확률 하향",
   "p_beat": 0.55,
   "exp_excess": 0.6,
   "sources": [
    {
     "url": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000088/q3fy27pr.htm",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:08:54+09:00"
    },
    {
     "url": "https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/11/nvidia-earnings-preview-q3-2027",
     "as_of": "2026-11-12",
     "retrieved_at": "2026-11-18T07:08:54+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/NVDA?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:08:50+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:07:52+09:00"
    },
    {
     "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?range=3mo&interval=1d",
     "as_of": "2026-11-17",
     "retrieved_at": "2026-11-18T07:07:52+09:00"
    }
   ]
  }
 ]
}
```
