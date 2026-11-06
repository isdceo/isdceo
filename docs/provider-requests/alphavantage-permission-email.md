# Alpha Vantage 사용 허락 요청 메일 (초안, 운영자가 보냄)

- 받는 곳: premium@alphavantage.co (약관 2.a가 안내하는 상업·예외 이용 문의처). 참고로 support@alphavantage.co 도 있음.
- 보내는 사람: 운영자 본인 메일(무료 키를 받은 메일 주소)
- 목적: 약관 2.a "unless you and Alpha Vantage have agreed otherwise in writing"에 따라, 계산된 점수(%)만 지인 30명 이내에게 보여 주는 것을 서면으로 허락받는다.

---

**Subject:** Permission request: showing computed daily return scores (no raw prices) to a small private group — non-commercial

Hello Alpha Vantage team,

I use a free Alpha Vantage API key (registered with this email address) for a personal, non-commercial hobby project, and I would like to confirm that my planned use is acceptable under Section 2.a of your Terms of Service, or obtain your written permission if needed.

**What the project is**
- A mock stock-picking game run by me as an individual. Two AI assistants each pick a few US and Korean stocks per trading day, and I score each pick by its one-day total return (close-to-close, including dividends).
- About 11 US tickers per day. I call TIME_SERIES_DAILY and DIVIDENDS once each per ticker (about 22 calls a day), and SPLITS only when a price moves more than 40%.

**What would be shown to others**
- Only the computed percentage scores (for example "+1.15%") and rankings derived from them. **No raw prices, dividend amounts, or other Alpha Vantage data** would be displayed or downloadable.
- Viewers: a small private group of up to about 30 friends, via an unlisted static web page.
- No ads, no fees, no subscriptions, no betting or prizes, no investment advice. I am not affiliated with any financial firm, and I am acting as an individual, not on behalf of a company.
- The page would credit "US closing prices and dividends: Alpha Vantage".

**My question**
Is showing these computed scores to this small private group acceptable under your free-tier terms? If it is not, could you grant written permission for this specific non-commercial use, or tell me which plan would be required?

Thank you for providing the API.

Best regards,
[운영자 이름]

---

## 한국어 요약 (운영자 확인용)

- 개인 취미 프로젝트, 모의 종목 고르기 게임. 미국 종목 하루 약 11개, 호출 약 22회.
- 남에게 보이는 것: 계산된 % 점수와 순위만. 원 가격·배당 금액은 보이지도 내려받지도 않음.
- 대상: 지인 30명 이내, 검색에 안 나오는 정적 페이지. 광고·요금·베팅·상금·투자 권유 없음. 금융회사와 관계없는 개인.
- 질문: 무료 약관으로 괜찮은지, 아니면 서면 허락을 주거나 필요한 요금제를 알려 달라.
- 금융업 종사·소속이 있으면(약관 2.a.iv) 이 메일 내용이 사실과 달라지므로 보내기 전에 확인할 것.
