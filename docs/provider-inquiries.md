# 데이터 제공처 문의 문안 (초안)

> 상태: **초안, 발송 전.** 운영자가 이름·연락처를 채워 직접 보낸다.
> 2026-11-05 홈페이지 재확인 결과(`docs/data-provider-research.md` 8장): 운영자 전용 화면은 약관 범위 안이라 지금은 발송하지 않아도 된다. **지인 공개 전에 Tiingo(4번)는 필수, KRX(1번)는 권장.** KIS(2번)·Alpaca(3번)는 쓰지 않으므로 보내지 않는다.
> 목적: 사용 형태 ①~④별로 허용 여부를 확인한다 (`docs/data-provider-research.md` 6장).
> 받은 답변은 이 파일 아래 "회신 기록"에 날짜와 함께 원문 그대로 남긴다.

| 제공처 | 언어 | 보낼 곳 (확인 후 기입) |
|---|---|---|
| 한국거래소 KRX Open API | 한국어 | krxdata@krx.co.kr (조사 문서 기준, 발송 전 KRX 사이트에서 재확인) |
| 한국투자증권 KIS Developers | 한국어 | KIS Developers 포털 문의 게시판 또는 고객센터 (포털에서 확인) |
| Alpaca | 영어 | Alpaca 지원 센터 문의 양식 (support 페이지에서 확인) |
| Tiingo | 영어 | Tiingo 지원 이메일 또는 문의 양식 (사이트에서 확인) |

---

## 1. 한국거래소 (KRX Open API)

**제목:** KRX Open API 데이터의 비상업 개인 이용 범위 문의

안녕하세요. KRX Open API 이용(신청 예정)과 관련해 이용 범위를 여쭙고자 합니다.

**이용 목적**
비상업 개인 프로젝트로, 두 개의 AI 분석 도구가 매 거래일 한국 주식 1종목씩을 고르고, 다음 거래일 종가 수익률로 점수를 매기는 모의 예측 게임을 운영하려 합니다. 실제 매매, 투자 권유, 유료 서비스, 광고는 없습니다. 하루 조회량은 20종목 내외입니다.

**문의 사항**
1. 유가증권·코스닥 일별매매정보의 종가와 KOSPI 지수 종가를 매일 자동으로 조회해, 비공개 저장소에 보관하고 제가 직접 점수 계산에 써도 되는지요?
2. 같은 종가 정보를 제가 사용하는 외부 AI 분석 서비스 두 곳에 분석 자료로 입력해도 되는지요? 이 경우 약관 제11조 ②항의 "제3자 제공"에 해당하는지 알고 싶습니다.
3. 지인 10명 이하만 접속하는 비공개 웹 화면에 다음을 표시해도 되는지요?
   (a) 종가 등 원시 가격
   (b) 원시 가격 없이, 종가로 계산한 수익률 점수(%)와 순위, 종목명만
   (b)가 가능하다면 약관 제10조 ③항에 따라 "한국거래소 통계정보" 출처를 표시하겠습니다.
4. 전 영업일 종가 데이터는 다음 영업일 몇 시부터 조회할 수 있는지요?
5. 위 이용에 별도 계약이나 비용이 필요한지요?

허용되지 않는 부분이 있다면 허용되는 대안 방식도 알려주시면 감사하겠습니다.

[이름] / [연락처]

---

## 2. 한국투자증권 (KIS Developers)

**제목:** KIS Developers 시세 데이터의 비상업 개인 이용 범위 문의

안녕하세요. KIS Developers 이용(계좌 개설 및 신청 예정) 전에 이용 범위를 확인하고 싶어 문의드립니다.

**이용 목적**
비상업 개인 프로젝트로, AI 분석 도구 두 개가 매 거래일 국내 주식 1종목씩을 고르고, 다음 거래일 종가 수익률로 점수를 매기는 모의 예측 게임을 운영하려 합니다. 실제 매매 주문은 하지 않습니다. 하루 조회량은 20종목 내외입니다.

**문의 사항**
1. 국내주식 기간별 시세(일봉) API로 전 거래일 종가를 매일 자동 조회해, 비공개 저장소에 보관하고 제가 직접 점수 계산에 써도 되는지요? 매매 없이 시세 조회만 하는 이용도 허용되는지요?
2. 같은 종가 정보를 제가 사용하는 외부 AI 분석 서비스 두 곳에 분석 자료로 입력해도 되는지요? 이 경우 "제3자 제공"에 해당하는지 알고 싶습니다.
3. 지인 10명 이하만 접속하는 비공개 웹 화면에 다음을 표시해도 되는지요?
   (a) 종가 등 원시 가격
   (b) 원시 가격 없이, 계산된 수익률 점수(%)와 순위, 종목명만
4. 전 거래일 종가는 다음 날 오전 7시(KST)에 조회할 수 있는지요? 호출 한도는 어떻게 되는지요?
5. 계좌 유지, API 이용, 시세 조회에 비용이 드는지요?

허용되지 않는 부분이 있다면 허용되는 대안 방식도 알려주시면 감사하겠습니다.

[이름] / [연락처]

---

## 3. Alpaca (English)

**Subject:** Permitted use of historical market data for a non-commercial personal project

Hello,

I am planning to use Alpaca Market Data and would like to confirm the permitted scope before setting up automation.

**Purpose**
A non-commercial personal project: two AI analysis tools each pick one US stock per trading day, and I score each pick by its next-session closing-price return. There is no trading, no investment advice, no paid service, and no advertising. Volume is about 20 symbols per day.

**Questions**
1. May I automatically request the previous session's daily bars (SIP, raw/unadjusted) each day, store them in a private repository, and use them myself to compute scores?
2. Does a free or paper-trading account have access to historical SIP daily bars older than 15 minutes, or only IEX? Is `feed=sip` available on that account?
3. May I give the same closing prices to two external AI analysis services that I personally use, as input for their analysis? Would that count as redistribution?
4. May I show the following on a private web page viewed by fewer than 10 friends?
   (a) raw prices
   (b) only derived return scores (%), rankings, and symbols, with no raw prices
5. Are there any fees, separate agreements, or rate limits that would apply to this use?

If some of this is not permitted, I would appreciate guidance on an acceptable alternative.

Thank you,
[Name] / [Contact]

---

## 4. Tiingo (English)

**Subject:** Permitted use of end-of-day data for a non-commercial personal project

Hello,

I am planning to use Tiingo's end-of-day API on a free account and would like to confirm the permitted scope.

**Purpose**
A non-commercial personal project: two AI analysis tools each pick one US stock per trading day, and I score each pick by its next-session total return (unadjusted close plus `divCash` on the ex-date, adjusted by `splitFactor`). There is no trading, no investment advice, no paid service, and no advertising. Volume is about 20 symbols per day.

**Questions**
1. May I automatically request daily prices each day, store them in a private repository, and use them myself to compute scores?
2. May I give the same prices to two external AI analysis services that I personally use, as input for their analysis? Would that count as redistribution?
3. May I show the following on a private web page viewed by fewer than 10 friends?
   (a) raw prices
   (b) only derived return scores (%), rankings, and symbols, with no raw prices
4. Your documentation says most US equity prices are available at 5:30 PM ET, with corrections until 8 PM ET. After what time are previous-session closes final in practice?
5. Is this use within the free plan's terms, or would a paid plan or separate agreement be required?

If some of this is not permitted, I would appreciate guidance on an acceptable alternative.

Thank you,
[Name] / [Contact]

---

## 회신 기록

| 날짜 | 제공처 | 질문 번호별 답변 요지 | 원문 위치 |
|---|---|---|---|
| | | | |
