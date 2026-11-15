# r1-lynch 2026-11-16 (v2)

분석 요약: KR은 관망(WATCH), US는 EW(Edwards Lifesciences)를 낸다. 근거·위험·출처는 아래 JSON에 있다.

```json
{
    "agent_id": "lynch",
    "candidates": [
        {
            "market": "KR",
            "ticker": "WATCH",
            "name": "관망",
            "rationale": "구간은 11/13 종가에서 11/16 15:30 종가까지다. KOSPI 11/13 종가 5290.53(research 도구). 공통 자료의 DART 공시를 11/13~11/15로 걸러 보니, 대상 종목 가운데 이익 전망을 올려 줄 실적·수주 공시는 현대해상 영업(잠정)실적(11/13, 접수 시각 확인 못함)과 TKG휴켐스·원익QnC 잠정실적 정도였다. 그 밖에는 IR 안내, 배당 기준일 결정(POSCO홀딩스·현대엘리베이터, 배당락은 구간 밖으로 판단하지만 기준일은 공시 원문에서 확인하지 못함), 자기주식 관련 공시였다. 내 렌즈(실적이 이익 전망을 올렸는데 주가가 아직 덜 따라온 종목)에 맞는 확인된 오늘 촉매가 없다. 반도체 대형주는 이익 전망이 아직 매우 높지만 주가는 고점에서 크게 내려와 있다. 삼성전자는 11/13 종가 206000원(research 도구)으로 52주 고점 대비 -42%, 50일·200일 이평선 아래다(stock_data). SK하이닉스는 11/13 종가 1216000원(research 도구)으로 6개월 -35%다(stock_data). 경기순환주에서 낮은 PER은 고점 신호일 수 있어 PEG로 싸다고 단정할 수 없다. 그리고 11/13 금요일 미국장 결과를 확인하지 못했다. 근거 없이 하루 방향을 거는 대신 KR은 관망을 쓴다.",
            "risks": [
                "관망은 지수 수익률이라 확인 못한 금요일 미국장·주말 뉴스에 반도체가 급반등하면 기회를 놓친다",
                "현대해상·TKG휴켐스 잠정실적 등 내가 본문을 확인하지 못한 공시에 실제 서프라이즈가 있었을 수 있다",
                "주 1회 관망 카드를 월요일에 써서 이번 주 KR에서는 더 쓸 수 없다"
            ],
            "catalyst": "없음 (구간 안 대상 종목의 실적 발표·배당락은 확인 못함, 금통위 일정은 구간 안에서 확인 못함)",
            "flip_condition": "장 시작 전 대상 종목에서 이익 전망을 올리는 공시(잠정실적 서프라이즈·대형 수주)가 DART로 확인되고, 주가 반영이 덜 된 경우",
            "p_beat": 0.5,
            "exp_excess": 0.0,
            "sources": [
                {
                    "url": "https://query1.finance.yahoo.com/v8/finance/chart/005930.KS?range=3mo&interval=1d",
                    "as_of": "2026-11-13",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                },
                {
                    "url": "https://query1.finance.yahoo.com/v8/finance/chart/000660.KS?range=3mo&interval=1d",
                    "as_of": "2026-11-13",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                },
                {
                    "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261113800595",
                    "as_of": "2026-11-13",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                }
            ]
        },
        {
            "market": "US",
            "ticker": "EW",
            "name": "Edwards Lifesciences",
            "rationale": "유형은 고성장에 가까운 대형우량주(의료기기)다. 2분 스토리: 고령화로 대동맥판막 시술(TAVR)이 늘고, 승모판·삼첨판(TMTT) 신제품이 새 성장 엔진이 된다. 11/4 장 마감 뒤 발표한 3분기 실적은 매출 1.72B달러로 추정치 1.68B를, 조정 EPS 0.80달러로 추정치 0.74를 넘었다(247wallst). TMTT 매출은 +44%였다. 회사는 연간 매출 성장 가이던스를 약 11.5%(기존 10~11%)로, TAVR 성장 가이던스를 9.0~9.5%(기존 8~9%)로, 조정 EPS 가이던스를 2.97~3.05달러로 올렸다(SEC 8-K 및 검색 요약, EPS 성장 18%는 미검증). 실적 뒤 이익 전망 상향 흐름에 맞는 종목이다. 11/13 종가 107.15달러(research 도구), 1개월 +21.6%로 52주 고점(stock_data)이며 50일선 90.42달러 위다. PER은 내 추정으로 가이던스 중간값 대비 약 35.6배, 성장 18%를 쓰면 PEG 약 2.0이다. 린치 기준으로는 비싼 편이라 확신도를 낮게 둔다. 구간 안 종목 고유 촉매는 없다.",
            "risks": [
                "PEG 약 2.0(추정)으로 비싸다. 한 달 +21.6% 뒤라 차익 실현성 되돌림이 나올 수 있다",
                "11/16 엠파이어스테이트 지수·산업생산 결과나 10년물 5.15%(11/13, research 도구) 금리 움직임에 따른 성장주·헬스케어 섹터 순환",
                "금요일 미국장 결과와 주말 뉴스를 확인하지 못했다"
            ],
            "catalyst": "없음 (종목 고유 촉매 없음. 거시: 11/16 08:30 ET 엠파이어스테이트 제조업지수)",
            "flip_condition": "장 시작 전 EW에 부정적인 뉴스(리콜·CMS 정책 후퇴·애널리스트 하향)가 나오거나, 프리마켓에서 SPY 대비 -1% 이상으로 약하면 판단을 철회한다",
            "p_beat": 0.52,
            "exp_excess": 0.1,
            "sources": [
                {
                    "url": "https://www.sec.gov/Archives/edgar/data/0001099800/000109980026000053/ex-991q32026.htm",
                    "as_of": "2026-11-04",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                },
                {
                    "url": "https://247wallst.com/cards/a-guidance-raise-from-the-structural-heart-leader-lands-whil-ew-quote-01m6ma219kvq5dyph2zge18vhq",
                    "as_of": "2026-11-04",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                },
                {
                    "url": "https://www.medtechdive.com/news/edwards-bumps-up-sales-forecast-on-tavr-strength-in-q3/873876/",
                    "as_of": "확인 못함",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                },
                {
                    "url": "https://query1.finance.yahoo.com/v8/finance/chart/EW?range=3mo&interval=1d",
                    "as_of": "2026-11-13",
                    "retrieved_at": "2026-11-16T07:09:44+09:00"
                }
            ]
        }
    ]
}
```
