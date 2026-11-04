# AI 모의 투자 리그 — 데이터 제공처 조사

- 조사일: 2026-11-03 (KST). 약관·한도는 바뀔 수 있으므로 연결 직전에 다시 확인한다.
- 전제: 지인 10명 이하 비공개 리그, 실주문 없음, 비용 0원 목표. 매 평일 KST 07:00 수집 → 08:30 확정 (`docs/ai-league-proposal.md` 기준).
- 표기: **확인됨** = 공식 페이지·약관 원문에서 직접 확인 / **2차 자료** = 서드파티 문서·검색 요약에서만 확인 / **확인 못함** / **해석 필요**.
- 이 문서는 법률 자문이 아니다. "지인 공유 가능" 판단은 모두 운영자가 직접 확인하거나 제공처에 문의해야 확정된다.

---

## 1. 요약 추천

### 1-0. 먼저 알아둘 핵심 사실 3가지

1. **공공데이터포털(금융위원회) 시세는 시간 조건을 못 맞춘다.** 공식 페이지에 "데이터 갱신은 기준일자로부터 영업일 하루 뒤 오후 1시 이후"라고 적혀 있다. D일 종가는 D+1일 13:00 이후에야 들어온다. KST 07:00 수집에도, "당일 저녁" 조건에도 맞지 않는다. 또한 시세 데이터는 공공누리 **제4유형(변경금지)** 이고 "상업적 목적 여부와 상관 없이 제3자 무단 제공 및 재배포가 엄격히 금지"된다.
2. **무료 시세 제공처는 거의 모두 "개인·비상업·재배포 금지" 조건이다.** 지인에게 **원시 시세(종가)를 보여주는 것은 사실상 모든 후보에서 "불가" 또는 "해석 필요"** 다. 수익률 점수만 보여주는 방식이 허용되는지 명시한 약관은 찾지 못했다. 따라서 화면에는 **종목명·점수·순위만** 표시하고(기존 제안서 6-1과 같음), 원시 가격은 저장소 내부에만 둔다. 이 방식도 "허용"이 아니라 "위험을 줄이는 것"이다.
3. **Tiingo의 미국 종가는 겨울(EST)에 KST 07:00보다 늦다.** 공식 문서상 "Most US Equity prices are available at 5:30 PM EST, however exchanges may send corrections until 8 PM EST"이다. 17:30 EST는 KST 07:30이고, 정정은 KST 10:00까지 이어질 수 있다. 서머타임 기간에는 KST 06:30이다.

### 1-1. 데이터 종류별 추천 조합

| 데이터 | 1순위 | 2순위 | 이유 | 비용 |
|---|---|---|---|---|
| 한국 일별 종가 (비수정) | **KRX Open API** (유가증권/코스닥 일별매매정보). 공식 API, 비상업 이용 허용, 1일 10,000회 | **KIS Developers** (한국투자증권). 장 마감 직후 조회 가능, 원주가(비수정) 옵션 | KRX가 원천 소유자다. 단, 데이터 반영 시각(2차 자료로는 익일 08:00)이 07:00 수집보다 늦을 수 있다. 그때는 KIS를 **잠정값**, KRX를 **확정값**으로 쓰는 구조를 권한다 | 0원 (KIS는 계좌 개설 필요) |
| 미국 일별 종가 (비수정) | **Tiingo** (무료 계정). raw `close` + `divCash` + `splitFactor`를 한 번 호출로 받고, 배당은 ex-date 기준이다 | **Alpaca Market Data 무료** (SIP 과거 일봉, 최근 15분 제외) 또는 **Massive(구 Polygon.io) Stocks Basic** (EOD, 분당 5회) | Tiingo는 한 응답에 필요한 필드가 다 있다. 무료 1,000회/일, 500종목/월로 하루 20종목에 충분하다. 겨울철 07:00 수집과 맞지 않으므로 미국 수집을 07:45 이후로 옮기거나 2순위를 잠정값으로 쓴다 | 0원 |
| 지수 종가 KOSPI | **KRX Open API** KOSPI 시리즈 일별시세 | KIS 업종기간별시세 | 원천 공식 데이터 | 0원 |
| 지수 종가 S&P 500 | **SPY ETF 종가로 대체** (Tiingo로 수집, 참고 지표 전용) | Alpha Vantage `INDEX_DATA`는 Premium 표시라 무료로는 안 된다. Yahoo `^GSPC`는 비공식이다 | S&P 500 지수값은 S&P DJI 라이선스 대상이다. FRED의 SP500 시리즈에도 "reproduction ... prohibited except with the prior written permission" 고지가 있다(2차 자료). 순위에 쓰지 않는 참고 지표라면 ETF 대체가 가장 안전하다 | 0원 |
| 한국 기업행동 (현금배당) | **공공데이터포털「금융위원회_공시정보」배당공시정보조회** (이용허락범위 **제한 없음**) | **「금융위원회_주식권리일정정보」**(예탁원, 제2유형) 또는 **OpenDART 공시검색 + 원문 파싱** | 배당은 기준일 2주 전쯤 공시되므로 D+1 13:00 반영이어도 늦지 않다. 배당락일 필드는 없고 **배당기준일**만 있다. 배당락일 = 기준일의 직전 영업일(T+2 결제)로 계산한다 | 0원 |
| 한국 기업행동 (분할·병합) | **OpenDART 공시검색**("주식분할결정"·"주식병합결정"·"감자결정") + 원문 파싱 | 「금융위원회_주식권리일정정보」(권리 사유에 액면분할이 포함되는지 **확인 못함**), KIS 예탁원정보(**확인 못함**) | OpenDART의 구조화 API(DS005)에는 무상증자·감자 결정은 있지만 **주식분할결정·현금배당결정 API는 없다**(목록에서 확인) | 0원 |
| 미국 기업행동 | **Tiingo** `divCash`(ex-date 기준)·`splitFactor` | Alpha Vantage `DIVIDENDS`·`SPLITS` (25회/일), Alpaca corporate actions | 종가와 같은 응답이라 추가 호출이 없다 | 0원 |
| 구성 종목 (미국) | **ETF 보유종목 파일** (SPY xlsx 접속 확인, QQQ는 Invesco) + **Wikipedia**(CC BY-SA, 변경 이력 확인용) | Nasdaq.com 비공식 JSON (`api.nasdaq.com/.../nasdaq100`) | S&P DJI 공식 구성종목은 라이선스 대상이다. 리그는 목록을 **내부 자격 검증에만** 쓰고 화면에 재게시하지 않으므로 위험이 낮다 | 0원 |
| 구성 종목 (한국) | **KRX 정보데이터시스템 지수구성종목** (수동 다운로드, 연 2회) + **KRX 정기변경 보도자료** | KODEX 200·KOSDAQ150 ETF의 PDF(구성종목) | KRX Open API 서비스 목록에는 구성종목 API가 없다. 정기변경은 6월·12월 연 2회라 **수동 갱신으로 충분**하다 | 0원 |

**예상 비용: 0원.** 유료 전환이 필요한 항목은 없다. 단, KIS를 쓰려면 한국투자증권 계좌 개설이 필요하고, 미국 제공처는 각각 무료 계정 가입(이메일)이 필요하다.

### 1-2. 권장 운영 형태 (요약)

- 원시 종가는 **비공개 저장소 내부에만** 저장한다. 지인 화면에는 점수(%)·순위·종목명만 보여준다. 출처 표시("한국거래소 통계정보" 등)는 화면 하단에 둔다.
- 한국은 KRX Open API(확정)와 KIS(잠정)의 이중 수집, 미국은 Tiingo(확정)와 Alpaca/Massive(잠정·대조)의 이중 수집을 권한다. 수집 시각은 운영자가 정해야 한다(4장).
- 기업행동은 "공시 기반 일정표"를 미리 만들어 둔다. 채점 날 배당락·분할이 있는 종목만 보정한다.

---

## 2. 후보별 비교표

범례: 지인 공유 가능성은 **원시 시세를 지인 화면에 표시하는 경우** 기준이다. 괄호 안은 "점수만 표시"하는 경우다.

### 2-1. 한국

| 후보 | 무료 범위 | 종가 제공 시점 | 범위 (비수정·지수·기업행동) | 이용 조건 요지 | 지인 공유 가능성 | 안정성 | 접속 테스트 (HTTP) |
|---|---|---|---|---|---|---|---|
| 공공데이터포털 「금융위원회_주식시세정보」 | 무료, 키 필요, 개발계정 10,000회(트래픽 단위). **확인됨** | **기준일 다음 영업일 13:00 이후** (금요일분은 월요일). **확인됨** | 일별 시가·종가 등. 비수정 여부는 가이드 문서로 확인 필요. 기업행동 없음 | 공공누리 **제4유형**(출처표시+상업적 이용금지+변경금지). "상업적 목적 여부와 상관 없이 제3자 무단 제공 및 재배포가 엄격히 금지" | **불가** (점수만: **해석 필요**. 변경금지 조항이 파생값에도 걸리는지 불명) | 공식 API | 상세페이지 200 / 키 없는 API 호출 401 |
| 「금융위원회_지수시세정보」 | 위와 같음 | 위와 같음 | KOSPI·KOSDAQ 등 지수 | 제4유형, 위와 같은 재배포 금지 문구 | **불가** (점수만: 해석 필요) | 공식 API | 키 없는 API 호출 401 |
| **KRX Open API** (openapi.krx.co.kr) | 무료, 회원가입·인증키 신청 후 **API별 이용신청·승인** 필요, **키당 1일 10,000회**. 2010-01-04 이후 데이터. **확인됨** | **확인 못함**. 2차 자료는 "매일 오전 8시(KST) 갱신"(전 영업일분)이라고 설명한다 | 유가증권·코스닥 일별매매정보(종가), KOSPI·KOSDAQ 시리즈 지수 일별시세, 종목기본정보. **구성종목·배당·분할 API는 서비스 목록에 없음** | 약관 제6조②: "비상업적인 목적으로만 이용", 제10조③: 화면 제작 시 "한국거래소 통계정보" 명시, 제11조②: "제공받은 정보를 제3자에게 제공할 수 없다" | **불가** (점수만: **해석 필요**. 제10조③은 화면 제작을 전제하지만 제11조②와 충돌) | 공식 API | 메인 200 / 키 없는 API 호출 401 |
| KRX 정보데이터시스템 (data.krx.co.kr) | 웹 조회·다운로드 무료. 2차 자료: 2024-12-27부터 데이터 조회에 로그인 필요 | 웹 화면 기준 당일 장 마감 후로 알려짐 (**확인 못함**) | 종가·지수·**지수구성종목**·기업행동 일부 | 사이트 고지: "No information and data owned by KRX ... may be reproduced, transmitted digitally, distributed to a third party ... without the prior permission of KRX" | **불가** | 웹 화면. 자동 수집은 비공식 | 메인 200 / 내부 JSON 엔드포인트(GET) 403 |
| pykrx | 무료 오픈소스. 최신 1.2.9 (PyPI 업로드 2026-09-19). README상 **KRX 로그인 ID·비밀번호(`KRX_ID`, `KRX_PW`) 필수** | KRX 사이트와 같음 (**확인 못함**) | 비수정·수정 종가, 지수, 구성종목 | 원천은 KRX 사이트 → 위 KRX 고지가 그대로 적용됨 | **불가** | **비공식 스크래핑**. 사이트 변경 시 중단될 수 있음(2024년 말 로그인 도입 때 실제로 중단) | PyPI 200 |
| **KIS Developers** (한국투자증권) | 무료. **한국투자증권 계좌 + 서비스 신청** 필요. 호출 유량은 **확인 못함** | 실시간 시세 API라 장 마감(15:30) 직후 조회 가능 (공식 명세로 재확인 필요) | 기간별시세에 수정/원주가 선택(`FID_ORG_ADJ_PRC`, 2차 자료), 업종(지수) 시세. 예탁원정보(배당·액면교체 일정) API는 **확인 못함** | 개인은 "본인 자산으로 자기만의 전략을 통하여 매매". 제3자 서비스는 제휴 대상이다. 코스콤 계약 없이 앱 화면에 시세 표시는 "불가하다고" 안내함 | **불가** (점수만: **해석 필요**) | 공식 API (증권사) | 포털 302 (리다이렉트) |
| OpenDART (opendart.fss.or.kr) | 무료, 인증키 필요. 일 20,000회 (2차 자료 다수, 공식 오류코드 020 "요청 제한 초과") | 공시 접수 즉시 | 공시검색(거래소공시 포함) + 원문. 정기보고서 "배당에 관한 사항"(연간 요약이라 ex-date 이벤트용으로 부족). 주요사항보고서 API에 감자·무상증자 결정은 있으나 **현금배당결정·주식분할결정 구조화 API는 없음**(목록 확인) | 약관 제11조 "원칙적으로 무료", 제16조④ "저작권법 및 공공데이터법에 따릅니다". 비상업 한정·재배포 금지 조항은 **찾지 못함** | **해석 필요** (명시적 금지 조항은 못 찾음. 공시 사실 자체는 공개 정보) | 공식 API | 메인 200 / 키 없는 API 302 |
| 「금융위원회_공시정보」 (배당공시정보조회 등 32개 오퍼레이션) | 무료, 개발계정 10,000 | 기준일 다음 영업일 13:00 이후 | 배당공시·무상증자·감자·합병·분할 결정 공시. **주식분할(액면분할)결정 오퍼레이션은 목록에 없음** | **이용허락범위 제한 없음** | **가능** (이 데이터셋 한정. 단, 필드에 배당기준일·주당배당금이 있는지는 활용가이드로 확인 필요) | 공식 API | (상세페이지 200) |
| 「금융위원회_주식배당정보」 / 「주식권리일정정보」 (원천: 한국예탁결제원) | 무료, 개발계정 10,000 | 다음 영업일 13:00 이후 | 배당기준일자·현금배당지급일자·주당배당금 / 권리 사유별 기준일·지급일(배당·무상증자·감자 등) | 공공누리 **제2유형**(출처표시+상업적 이용금지). 변경금지는 없음 | **해석 필요** (비상업이면 출처 표시 후 이용 가능한 유형이다. "제3자 제공 금지" 문구는 없음) | 공식 API | (상세페이지 200) |

### 2-2. 미국

| 후보 | 무료 범위 | 종가 제공 시점 | 범위 | 이용 조건 요지 | 지인 공유 가능성 | 안정성 | 접속 테스트 (HTTP) |
|---|---|---|---|---|---|---|---|
| **Tiingo** | 무료 계정. 50회/시간, 1,000회/일, 500종목/월, 1GB/월 (2차 자료 다수, 공식 문서는 pricing 페이지 참조). 키 필요 | **17:30 EST 대부분 반영, 20:00 EST까지 정정** (KST 겨울 07:30~10:00, 여름 06:30~09:00). **확인됨** | raw `close`·`adjClose`, `divCash`(ex-date 기준), `splitFactor`. **확인됨**. 지수는 문서에 언급 없음 | "For Basic and Power accounts, data is for internal and personal use only. You may not redistribute the data in any form." | **불가** (점수만: **해석 필요**) | 공식 API | 루트 301 / 키 없는 호출 403 |
| Alpha Vantage | 무료 **25회/일**. 키 필요 (가입 시 이메일) | "end of each trading day" | `TIME_SERIES_DAILY`는 raw(as-traded), `DIVIDENDS`·`SPLITS` 엔드포인트. 지수(`INDEX_DATA`)는 **Premium** 표시 | "personal, non-commercial use". 상업 이용에 "allows individuals or entities other than User to access information directly or indirectly"가 포함됨 | **해석 필요** (비상업 지인 화면은 상업 정의에 직접 해당하지 않지만, "private and individual in nature"를 넘는지 불명) | 공식 API | demo 키 호출 200 (2026-11-03까지 데이터) |
| Massive (구 Polygon.io, 2025-10 명칭 변경) | Stocks Basic: 분당 5회, EOD, 2년 (2차 자료). 키 필요 | EOD (정확한 시각 **확인 못함**) | 일봉(조정 여부 선택), 배당·분할 참조 데이터 (무료 포함 여부 2차 자료) | Individuals ToS: "personal, individual, non-business, or non-commercial use". Market Data ToS: "may not be copied, reproduced, republished ... publicly displayed ... or distributed in any way" | **불가** | 공식 API | polygon.io 301 → massive.com 200 / api.polygon.io 키 없음 401 |
| Financial Modeling Prep | 무료 250회/일, EOD (2차 자료·FMP 블로그). 키 필요 | **확인 못함** | EOD, 배당·분할 엔드포인트 존재 | "may not share FMP Services or Data ... integrate the Data or Services into any tools or applications accessible by any third parties, or use the Services to host, share, display, or provide content for others" | **불가** (명시적) | 공식 API | 사이트 301 / `/stable/` 401 |
| EODHD | 무료 20회/일, EOD 1년 (2차 자료). 키 필요 (demo 키는 일부 종목만) | **확인 못함** | `close`(비수정)와 `adjusted_close` 동시 제공(demo 응답 확인). 배당·분할 API 있음 | Non-Professional은 "private, non-commercial purposes". "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information" 금지 | **불가** (명시적) | 공식 API | demo 키 AAPL 200 |
| Stooq | 키 없는 CSV 다운로드로 알려짐 | **확인 못함** | 지수(^SPX) 포함으로 알려짐 | 약관 **확인 못함** | **확인 못함** | 비공식 성격 (공식 API 문서 없음) | **000 (프록시 경유 연결 리셋)**. 이 환경에서는 접속 판단 불가 |
| Nasdaq Data Link | 일부 무료 데이터셋 | — | 무료 미국 개별종목 EOD 데이터셋은 이번 조사에서 **확인 못함** | 데이터셋별 라이선스 | **확인 못함** | 공식 API | 메인 200 |
| Alpaca Market Data (무료) | 과거 데이터 200회/분, 7년 이상. 무료는 **최근 15분 SIP 데이터 조회 불가**(공식 문서). 계정·키 필요 | 마감 15분 후부터 SIP 일봉 조회 가능 (일봉 최종 확정 시각은 **확인 못함**) | 일봉(조정 옵션), corporate actions 엔드포인트(무료 포함 여부 **확인 못함**) | 2차 자료: 지원 문서에 "you cannot redistribute Alpaca API data" | **불가** (2차 자료) | 공식 API | 키 없는 호출 401 |
| Yahoo Finance (비공식) | 키 없음 | 마감 직후 | 종가·조정종가·배당·분할·지수(^GSPC) | 약관: "access or collect data ... using any automated means ... for any purpose without our express ... permission" 금지 | **불가** | **비공식**. 차단·변경 위험 | chart API 200 |
| FRED (SP500) | 무료, API는 키 필요 | 다음 날 | S&P 500 지수 일별값 | 시리즈 고지(2차 자료): "reproduction of S&P 500 in any form is prohibited except with the prior written permission of S&P Dow Jones Indices LLC" | **불가** | 공식 | **000 (HTTP/2 스트림 오류)**. 이 환경에서는 판단 불가 |

### 2-3. 지수 구성 종목

| 후보 | 무료 범위 | 반영 시점 | 이용 조건 요지 | 지인 공유 가능성 | 접속 테스트 (HTTP) |
|---|---|---|---|---|---|
| S&P DJI 공식 | 웹 지수 페이지 일부. 전체 구성종목은 유료·라이선스 | 분기 리밸런싱: 3·6·9·12월 셋째 금요일 다음 월요일 개장 전 반영, 금요일 장후 발표 (2차 자료) + 수시 변경 | 지수 데이터 표시·재배포는 별도 라이선스 (2차 자료) | **불가** | 지수 페이지 403 |
| SPY 보유종목 (State Street) | 일별 xlsx, 키 없음 | ETF 보유 기준이라 지수 변경 반영 후 다음 날 | 약관 **확인 못함** | **해석 필요** (내부 자격 검증 용도라면 화면 게시 불필요) | 301 → 200 (xlsx 수신) |
| IVV 보유종목 (iShares) | CSV 링크 | 위와 같음 | 약관 **확인 못함** | 해석 필요 | 200이지만 **CSV가 아니라 HTML 수신** (자동 수집 차단 또는 동의 페이지로 추정, 확인 못함) |
| QQQ 보유종목 (Invesco) | 다운로드 링크 | 위와 같음 | 약관 **확인 못함** | 해석 필요 | **406** (헤더 요구, 자동 수집 어려움) |
| Nasdaq 공식 | nasdaq.com 목록 화면 + 비공식 JSON | 연 1회 12월 재구성(셋째 금요일 이후 반영) + 분기 리밸런싱. 2026년 규칙 변경설은 2차 자료만 있어 **확인 못함** | nasdaq.com 이용약관 페이지 **확인 못함**(404) | 해석 필요 | `api.nasdaq.com/.../nasdaq100` 200 (101행 JSON) |
| Wikipedia | 무료 | 편집자 갱신 (지연·오류 가능) | 본문 **CC BY-SA 4.0** (출처 표시·동일조건변경허락) | **가능** (라이선스 조건 준수 시. 정확성 보증 없음) | S&P 500 목록 200 / Nasdaq-100 200 |
| KRX 지수구성종목 (정보데이터시스템) | 웹 다운로드 (로그인 필요하다는 2차 자료) | KOSPI200·KOSDAQ150 정기변경 **6월·12월**. 2026년 6월분은 5/21 위원회, 5/22 발표, **6/12 반영**(2차 자료·언론) | KRX 사이트 고지상 무단 재배포 금지 | **불가** (내부 검증만) | 정보데이터시스템 메인 200, index.krx.co.kr 200 |
| KODEX 200·KOSDAQ150 ETF 구성종목(PDF) | 운용사 웹 | ETF 기준 | 약관 **확인 못함** | 해석 필요 | kodex.com 301 |

---

## 3. 근거 인용과 URL

### 한국

- **공공데이터포털 「금융위원회_주식시세정보」** — https://www.data.go.kr/data/15094808/openapi.do
  - "금융위원회에서 제공하는 모든 서비스는 실시간이 아니며, 데이터 갱신은 기준일자로부터 영업일 하루 뒤 오후 1시 이후에 업데이트됩니다. 예를 들어, 금요일 데이터는 차주 월요일에 제공됩니다."
  - "이용허락범위 제4유형 : 출처표시 + 상업적 이용금지 + 변경금지 본 데이터는 상업적 목적 여부와 상관 없이 제3자 무단 제공 및 재배포가 엄격히 금지됩니다."
  - "트래픽 개발계정 : 10,000 / 운영계정 : 활용사례 등록시 신청하면 트래픽 증가 가능", "비용부과유무 무료"
- **「금융위원회_지수시세정보」** — https://www.data.go.kr/data/15094807/openapi.do — 같은 갱신 문구, 같은 제4유형·재배포 금지 문구.
- **「금융위원회_공시정보」** — https://www.data.go.kr/data/15059649/openapi.do
  - "배당공시정보조회, 유상증자결정공시정보조회, 무상증자결정공시정보조회, … 감자결정공시정보조회, … 회사분할결정공시정보조회 …"
  - "이용허락범위 이용허락범위 제한 없음"
- **「금융위원회_주식배당정보」** — https://www.data.go.kr/data/15043284/openapi.do
  - "제공 항목에는 배당기준일자, 현금배당지급일자, 주식교부일자, 주식일반배당금액, 차등배당금액, 배당률 …"
  - "이용허락범위 제2유형 : 출처표시 + 상업적 이용금지 해당 데이터를 상업적으로 활용하고자 하는 이용자는 데이터 원천 소유자인 한국예탁결제원과 … 정보이용계약이 필요합니다."
- **「금융위원회_주식권리일정정보」** — https://www.data.go.kr/data/15059609/openapi.do
  - "배당, 무상증자, 유상증자, 주식교환, 감자 등 다양한 권리행사를 사유별로 권리일, 기준일, 지급일 등의 세부 일정을 조회" / 제2유형.
- **KRX Open API 이용약관** — https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp
  - 제6조②: "API 이용자는 API 서비스를 비상업적인 목적으로만 이용할 수 있으며, API 서비스를 이용한 결과에 대한 대가를 제3자에게 청구해서는 아니된다."
  - 제6조④: "하나의 키당 1일(매일 0시~24시) 10,000회 이하의 요청으로 제한하며 …"
  - 제10조③: "API 이용자가 API 서비스를 이용한 결과를 사용하여 화면을 제작한 경우, 해당 화면에 "한국거래소 통계정보"를 사용한 결과임을 명시해야 한다."
  - 제11조②: "API 이용자는 한국거래소로부터 제공받은 정보를 제3자에게 제공할 수 없다."
- **KRX Open API 서비스 목록** — https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd
  - "※ 데이터 제공 대상기간 : 2010년 이후", "KOSPI 시리즈 일별시세정보", "유가증권 일별매매정보", "코스닥 일별매매정보", "종목기본정보". 구성종목·배당·분할 항목은 목록에 없음.
- **KRX Open API 이용방법** — https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp — "인증키 신청 (관리자 승인 후 사용 가능)", "API 활용 신청 후 관리자 승인대기".
- **KRX Open API 갱신 시각 (2차 자료)** — https://github.com/RealYoungk/openkrx-mcp — "매일 오전 8시(KST)에 갱신". 공식 확인 못함.
- **KRX 정보데이터시스템 고지** — https://data.krx.co.kr/templets/mdc/disclaimer_p1.jsp
  - "No information and data owned by KRX, in whole or in part, may be reproduced, transmitted digitally, distributed to a third party, and published or broadcast, without the prior permission of KRX."
- **pykrx README** — https://github.com/sharebook-kr/pykrx — "KRX 로그인이 필요한 API를 사용하려면 아래 두 환경변수를 반드시 설정해야 합니다. | `KRX_ID` | … | `KRX_PW` |". PyPI: https://pypi.org/project/pykrx/ (1.2.9)
- **KIS Developers 제휴 안내** — https://apiportal.koreainvestment.com/provider
  - "시세정보 API 이용의 경우, KRX 및 해외거래소와의 정보이용계약을 체결하셨는지 확인을 부탁드립니다."
  - "API를 이용해서 제휴사 브랜드 어플리케이션(또는 앱)화면으로 시세정보를 이용하는 것도 불가하다고" (코스콤 통보로 소개됨)
  - 개인: "개인 본인 자산으로 자기만의 전략을 통하여 매매를 하고자 하는 개인고객"
- **KIS 기간별시세 수정/원주가 (2차 자료)** — https://algolab.co.kr/blog/kis-api-daily-chart-fhkst03010100-2026 — `FID_ORG_ADJ_PRC` 0=수정주가, 1=원주가(공식 예제와 설명이 엇갈린다는 지적 포함).
- **OpenDART 이용약관** — https://opendart.fss.or.kr/intro/terms.do
  - 제11조①: "금융감독원이 제공하는 서비스는 원칙적으로 무료입니다."
  - 제16조①: "오픈API 서비스 및 관련 프로그램의 저작권은 금융감독원에 있습니다." ④ "약관에 명시되지 않은 저작권과 관련된 사항은 저작권법 및 공공데이터법에 따릅니다."
- **OpenDART API 목록** — https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS002 ("배당에 관한 사항 — 정기보고서 내"), https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS005 ("무상증자 결정", "감자 결정", "회사분할 결정" 등. 현금배당결정·주식분할결정 없음)
- **KOSPI200 정기변경 (언론)** — https://www.smarttoday.co.kr/ko-kr/articles/107787 , https://news.bizwatch.co.kr/article/market/2026/05/22/0039 — 2026년 6월 변경 6/12 반영.

### 미국

- **Tiingo 일반 문서** — https://www.tiingo.com/documentation/general
  - "For Basic and Power accounts, data is for internal and personal use only. You may not redistribute the data in any form."
  - "Daily Requests - Reset every day at midnight EST."
- **Tiingo EOD 문서** — https://www.tiingo.com/documentation/end-of-day
  - "Most US Equity prices are available at 5:30 PM EST, however exchanges may send corrections until 8 PM EST."
  - divCash: "note that "date" will be the "exDate" for the dividend"
- **Tiingo 무료 한도 (2차 자료)** — https://www.quantstart.com/articles/evaluating-data-coverage-with-tiingo/ , https://api.tiingo.com/products/forex-api — 50/시간, 1,000/일, 500종목/월.
- **Alpha Vantage 약관 (PDF)** — https://www.alphavantage.co/terms_of_service/
  - "for personal, non-commercial use"; 상업 이용 기준 i: "any purpose that goes beyond investment analysis, research, testing, monitoring, and any other activities that are private and individual in nature"; iii: "commercial activity that allows individuals or entities other than User to access information directly or indirectly"
- **Alpha Vantage 지원·문서** — https://www.alphavantage.co/support/ ("free stock API service covering the majority of our datasets for 25 API requests per day"), https://www.alphavantage.co/documentation/ ("raw (as-traded) daily time series", "Index Data APIs Premium")
- **Massive** — 약관 목록 https://massive.com/terms , 개인 약관 https://massive.com/legal/individuals-terms-of-service ("personal, individual, non-business, or non-commercial use"), 시장데이터 약관 https://massive.com/legal/market-data-terms-of-service ("The Market Data may not be copied, reproduced, republished, uploaded, posted, publicly displayed … or distributed in any way …"). 명칭 변경·무료 한도(2차 자료): https://qveris.ai/guides/stock-api-free-comparison/
- **FMP 약관** — https://site.financialmodelingprep.com/terms-of-service
  - 2.2.1: "integrate the Data or Services into any tools or applications accessible by any third parties, or use the Services to host, share, display, or provide content for others"
  - 2.2.2: "prohibited from showcasing FMP Services or Data on platforms … designed for utilization by multiple individuals, irrespective of whether such usage is complimentary or paid"
- **EODHD 약관** — https://eodhd.com/financial-apis/terms-conditions
  - "Non-Professional Users are permitted to store, manipulate, and analyze the data for private, non-commercial purposes."
  - "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information" 금지.
  - 무료 20회/일(2차 자료): https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis
- **Alpaca** — https://docs.alpaca.markets/docs/about-market-data-api ("it is not allowed to query the latest 15-minute data", 2차 요약), https://alpaca.markets/data (Free $0, 200 API calls/min, 7+ years), 재배포 금지(2차 자료): https://hawkalpha.gitbook.io/what-is-hawkalpha/alpaca-broker/regarding-market-data-licensing
- **Yahoo 약관** — https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html — "access or collect data, or attempt to access or collect data, from our Services using any automated means … for any purpose without our express … permission"
- **FRED SP500 (2차 자료)** — https://fred.stlouisfed.org/series/SP500 — "reproduction of S&P 500 in any form is prohibited except with the prior written permission of S&P Dow Jones Indices LLC"
- **S&P DJI** — https://www.spglobal.com/spdji/en/spice-terms-of-use (웹 이용 라이선스는 "non-exclusive, non-transferable, limited, revocable", 2차 요약)
- **Nasdaq-100 방법론** — https://indexes.nasdaqomx.com/docs/Methodology_NDX.pdf , 2025년 재구성 발표: https://www.nasdaq.com/press-release/annual-changes-nasdaq-100-indexr-2025-12-13
- **Wikipedia 라이선스** — https://en.wikipedia.org/wiki/Wikipedia:Text_of_the_Creative_Commons_Attribution-ShareAlike_4.0_International_License

### 접속 테스트 원본 (2026-11-03, User-Agent: 일반 이름, 키 없음)

```
200 https://www.data.go.kr/data/15094808/openapi.do
401 https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo
401 https://apis.data.go.kr/1160100/service/GetMarketIndexInfoService/getStockMarketIndex
200 https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd
403 https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd (GET)
200 https://openapi.krx.co.kr/contents/OPP/MAIN/main/index.cmd
401 https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd?basDd=20261030
200 https://opendart.fss.or.kr/
302 https://opendart.fss.or.kr/api/alotMatter.json
302 https://apiportal.koreainvestment.com/
200 https://pypi.org/pypi/pykrx/json
301 https://api.tiingo.com/            403 https://api.tiingo.com/tiingo/daily/aapl/prices
200 https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo
301 https://polygon.io/ -> https://massive.com/ (200)
401 https://api.polygon.io/v2/aggs/ticker/AAPL/prev
301 https://financialmodelingprep.com/  401 https://financialmodelingprep.com/stable/
200 https://eodhd.com/api/eod/AAPL.US?api_token=demo&fmt=json
000 https://stooq.com/ (connection reset by peer, 프록시 터널 종료)
200 https://data.nasdaq.com/
401 https://data.alpaca.markets/v2/stocks/AAPL/bars
200 https://query1.finance.yahoo.com/v8/finance/chart/AAPL
403 https://www.spglobal.com/spdji/en/indices/equity/sp-500/
301->200 SSGA SPY holdings-daily-us-en-spy.xlsx (xlsx 수신)
200 iShares IVV holdings ajax (CSV 아닌 HTML 수신)
406 Invesco QQQ holdings download
200 https://api.nasdaq.com/api/quote/list-type/nasdaq100
200 https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
200 https://en.wikipedia.org/wiki/Nasdaq-100
000 https://fred.stlouisfed.org/ (HTTP/2 stream INTERNAL_ERROR)
200 https://index.krx.co.kr/  200 https://indices.krx.co.kr/
```

---

## 4. 운영자가 직접 확인·문의할 항목

**결정이 필요한 것**

1. **수집 시각.** 현재 설계는 KST 07:00 수집이다.
   - 한국: KRX Open API 반영이 08:00이면(2차 자료) 07:00에 D일 종가가 없다.
   - 미국: Tiingo는 겨울철 07:30 KST 이후에 반영된다.
   - 선택지: (a) 수집을 08:05로 옮기고 확정 08:30 유지 (b) 07:00은 KIS·Alpaca로 **잠정 수집**, 08:05에 KRX·Tiingo로 **확정 대조** (c) 채점만 하루 늦춤.
2. **KIS 사용 여부.** 한국투자증권 계좌 개설(개인정보 제공)이 필요하다. 쓰지 않으면 한국 당일 저녁 종가를 공식 경로로 받을 방법이 없다(비공식 스크래핑뿐).
3. **S&P 500 지수 대신 SPY 사용.** "시장 대비 초과 점수"를 SPY 기준으로 바꾸는 데 동의하는지 정해야 한다. KOSPI도 같은 이유로 KODEX 200 같은 ETF 대체를 검토할 수 있다.
4. **점수만 표시 원칙의 확정.** 원시 종가·차트를 지인 화면에서 완전히 빼는 데 동의하는지 정해야 한다.

**문의·확인이 필요한 것**

5. **KRX(krxdata@krx.co.kr)에 문의:** 비공개 지인 10명 이하에게 KRX Open API 종가로 계산한 **수익률 점수만** 보여주는 것이 제11조②의 "제3자 제공"에 해당하는지 묻는다. 일별매매정보의 **정확한 갱신 시각**도 함께 묻는다.
6. **KRX Open API 승인 후 직접 확인:** 일별매매정보의 `TDD_CLSPRC`가 비수정 종가인지(정규장 공식 종가인지) 샘플로 확인한다.
7. **공공데이터포털 활용가이드(docx) 확인:** 「금융위원회_공시정보」 배당공시정보조회 응답에 **배당기준일·1주당 배당금(보통주/우선주)·배당 종류(분기/중간/결산)** 필드가 있는지, 「주식권리일정정보」의 권리 사유 코드에 **액면분할·액면병합**이 있는지 확인한다.
8. **Tiingo 무료 한도·약관 원문:** https://www.tiingo.com/about/pricing 와 약관 페이지에서 확인한다(이번 조사에서 약관 URL은 404, pricing 본문은 스크립트 렌더링이라 읽지 못함). 지인 화면에 점수만 표시하는 것이 "redistribute"인지 support에 문의한다.
9. **Alpha Vantage에 문의(선택):** 비영리 지인 리그의 점수 표시가 "private and individual in nature"에 포함되는지 묻는다.
10. **KIS Developers:** 호출 유량, 기간별시세의 원주가 옵션 값, 예탁원정보(배당일정·액면교체일정) API 존재 여부, 개인 고객이 조회 결과(점수)를 지인에게 보여줘도 되는지 확인한다.
11. **ETF 보유종목 파일 이용조건:** SSGA·Invesco 사이트 이용약관에서 자동 다운로드 허용 여부를 확인한다. IVV는 이번 테스트에서 CSV가 아니라 HTML이 왔다.
12. **Nasdaq-100 2026년 규칙:** 분기별 편입 점검 도입설(2차 자료)이 사실인지 공식 방법론 PDF로 확인한다. 12월 재구성 반영일도 함께 확인한다.
13. **KOSPI200·KOSDAQ150 2026년 12월 정기변경 일정:** KRX 발표(보통 11월 하순 위원회)를 확인하고 구성종목 파일을 갱신한다.
14. **Stooq·FRED:** 이 컨테이너에서는 접속이 안 됐다(프록시 연결 오류). 다른 환경에서 접속과 약관을 확인한다.

---

## 5. 위험과 대안

| 위험 | 영향 | 대안 |
|---|---|---|
| **한국 종가가 07:00까지 안 들어옴** (KRX Open API 08:00 반영 시) | 그날 토론 스냅샷과 전날 추천 채점에 한국 종가가 비어 있음 | ① KIS로 잠정 수집 → KRX로 확정 대조 ② 수집을 08:05로 이동 ③ 한국 채점만 "보류 후 다음 라운드 확정"(기존 잠정→확정 구조) |
| **Tiingo 겨울철 반영 지연·정정** (KST 07:30~10:00) | 07:00 수집값이 정정 전 값일 수 있음 | 08:30 확정 직전 재조회. Alpaca 무료 SIP 일봉과 교차 검증한 뒤, 차이가 0.5% 넘으면 보류 |
| **한국 배당락일 데이터 없음** (모든 공식 소스가 "배당기준일"만 제공) | 배당 보정일 오류 | 배당락일 = **배당기준일의 직전 영업일**(T+2 결제 기준)로 계산하고 KRX 휴장일 달력을 적용. 2023년 이후 "배당액 확정 후 기준일" 제도로 기준일이 2~4월로 흩어져 있으니 공시 기반 일정표를 매일 갱신 |
| **한국 주식분할·병합 구조화 데이터 부족** | 분할일 수익률 급변(예: -80%)으로 점수 왜곡 | ① OpenDART 공시검색에서 "주식분할결정"·"주식병합결정"·"감자결정" 제목을 매일 조회 → 원문에서 비율·신주상장예정일 추출 ② **안전장치**: 일간 수익률이 ±30%를 넘으면 자동 보류하고 운영자가 확인 ③ KRX Open API의 전일 대비(`CMPPREVDD_PRC`)·기준가와 비교해 비정상을 탐지(필드 의미는 확인 필요) |
| **현금배당 금액 오류(우선주·차등배당)** | 배당 가산 오류 | 보통주·우선주 종목코드 매핑을 확인. 차등배당은 「주식배당정보」의 차등배당금액 필드로 교차 확인 |
| **약관상 지인 공유 불허 판정** | 리그 화면 운영 불가 | ① 원시 시세 비표시·점수만 표시 유지 ② 지인 각자가 **본인 무료 키**를 넣어 자기 브라우저에서 계산하는 구조(Tiingo는 "users supply their own API token" 방식이면 재배포가 아니라고 안내함, 2차 요약) ③ 「공시정보」(제한 없음)처럼 허용 범위가 넓은 데이터만 화면에 사용 |
| **비공식 소스 중단** (pykrx·Yahoo·Nasdaq JSON) | 수집 실패 | 운영 경로에는 쓰지 않고, 장애 시 수동 대조용으로만 사용 |
| **제공처 무료 정책 변경** (예: Polygon→Massive 개편, Alpha Vantage 한도 축소 이력) | 갑작스런 중단 | 미국은 Tiingo·Alpaca·Massive 3곳의 어댑터를 미리 만들어 두고 설정으로 전환. 유료 자동 전환은 하지 않음 |
| **구성종목 정기변경 누락** | 비대상 종목 추천 허용 또는 대상 종목 거부 | 연 2회(한국 6·12월), 분기(미국) 일정을 캘린더에 넣고, 변경 반영일 전날 목록 교체를 사람이 확인. Wikipedia 변경 이력으로 교차 검증 |
| **API 키 노출** (비공개 저장소라도) | 약관 위반·차단 | GitHub Actions Secrets에 저장하고 로그 출력 금지 |

---

## 6. 검토 반영 (2026-11-04)

외부 검토 의견을 반영해 상태를 바로잡는다.

- **KIS + Alpaca는 "확정 추천"이 아니라 "기술 검증 후보 (사용권 미확인)"이다.**
  - KIS: 전 거래일 종가를 다음 날 07:00까지 제공한다는 공식 보장을 확인하지 못했다. 시세는 계좌 보유 개인의 자기 투자용이고 제3자 제공 금지로 안내된다. 이용료 전체가 무료인지도 확인하지 못했다.
  - Alpaca: 15분 지난 SIP 과거 데이터는 무료로 안내되지만, paper 계정은 IEX만이라는 안내도 있다. 실제 계정으로 시험해야 한다. 재배포 금지로 안내된다.
- **제3자 제공 제약은 조사한 시세 제공처 거의 전부에 공통이다** (KRX Open API 제11조②, Tiingo, 공공데이터 시세 제4유형 등). 사용 형태별로 나눠 확인한다.

| 사용 형태 | 위험도 | 상태 |
|---|---|---|
| ① 운영자 본인이 비공개 저장소에서 채점 | 낮음 | 개인 이용에 가장 가까움 |
| ② 두 AI 팀에 공통 자료로 전달 (외부 AI 서비스 경유) | 해석 필요 | 제공처 문의 필요 |
| ③ 지인 화면에 원시 종가 표시 | 높음 | 하지 않음 |
| ④ 지인 화면에 점수·순위만 표시 | 해석 필요 | 제공처 문의 필요 |

- **진행 방침**
  - 지인 화면은 점수·순위·종목명만 내보낸다(③ 차단).
  - 공통 자료는 "가격 포함판"(②가 허용될 때)과 "가격 제외판"(공시·13F·달력·대상 목록 등 공개 자료만) 두 가지로 준비한다.
  - 수집기는 응답 거래일을 검사해 오래되거나 누락된 값은 실패로 처리한다. 잠정 출처와 확정 출처의 종가 차이를 기록하고, 확정 출처 값만 채점한다.
  - 일봉 종가와 거래소 공식 종가를 표본으로 대조한 뒤에 정식 데이터원으로 정한다.
- **제공처 문의 항목** (KIS·KRX는 한국어, Alpaca·Tiingo는 영어)
  1. 개인 계정으로 받은 전 거래일 종가를 비공개 공통 자료에 저장하고, 운영자가 사용하는 두 AI 팀의 분석·채점에 써도 되는가?
  2. 소수 지인이 보는 대시보드에 (a) 원시 가격, (b) 계산된 점수만 표시할 수 있는가?
  3. 외부 AI 서비스로 데이터가 전달되는 방식, 보관 기간, 매일 자동 수집이 허용되는가?
  4. 이용료·별도 계약·호출 제한은 무엇인가? 전 거래일 종가는 다음 날 몇 시부터 조회 가능한가?

---

## 7. 연결 시험 기록

| 날짜 | 제공처 | 결과 | 비고 |
|---|---|---|---|
| 2026-11-04 | KRX Open API | ✅ 유가증권·코스닥 일별매매정보, KOSPI 시리즈 일별시세정보 수신 | 2026-11-03 종가: 삼성전자 219,500 / 에코프로비엠 87,600 / KOSPI 5,648.79. 응답 기준일 검사 통과, 비수정 종가로 판단(Yahoo 계산값과 일치). 상장폐지 종목은 '값 없음' 실패로 정상 처리. **갱신 시각은 미확인** (11/5 아침 확인 예정) |
| 2026-11-04 | KRX Open API | 참고 | 승인 전 반복 호출 뒤 403 Access Denied(일시 차단)를 겪음. 승인 전에는 호출하지 않는다 |
