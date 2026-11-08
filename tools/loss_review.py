"""손실 복기 — 로로 팀 종목이 확정 마이너스 점수를 받으면 그 종목을 고른 에이전트가 스스로 원인을 분석한다.

  python3 tools/loss_review.py due [--dir league] [--json]      → 아직 복기가 없는 마이너스 확정 종목
  python3 tools/loss_review.py due --bundle <results.json> --team 슈슈 --reviews <복기 폴더> [--mode 실전]
                                                               → 결과 묶음(원장 없이)으로 대상 찾기 — 슈슈 팀 안전 사본용
  python3 tools/loss_review.py check <복기 파일>...              → 형식·금지 표현 검사
  python3 tools/loss_review.py list [--dir league] [--week 2026-W46] → 작성된 복기 목록
  python3 tools/loss_review.py summary --week 2026-W46 [--dir league] [--weeks 2] [--out 파일.md] [--json]
                                                               → 에이전트별 판정 횟수·근거 pick_id·'바꿀 점' 모음(주간 복기 입력)

복기 파일: league/reviews/losses/<라운드>/<에이전트>-<시장>.md (연습은 league/sandbox/reviews/losses/…)
- 확정(final) 점수만 대상이다. 잠정·보류·무효와 관망(지수 추종)은 제외한다.
- 복기는 기록일 뿐 지침을 바꾸지 않는다. 바꿀 점은 주간 복기(league-review)가 모아 운영자 승인 절차로 올린다.
- 숫자는 뜻을 확인할 수 있는 것만 쓴다: 수익률(%)·지수 대비(%p)·억·조 회사 금액·날짜·단위 붙은 개수. 원 가격·지표 수준값은 쓰지 않는다.
"""
from __future__ import annotations

import argparse, json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402

TEAM = "claude"
VERDICTS = ("분석 실수", "시장 전체 움직임", "구간 밖 사건", "예측 못한 새 소식", "운·잡음")
SECTIONS = ("## 1. 그때의 논리", "## 2. 실제로 무슨 일이 있었나", "## 3. 판정", "## 4. 놓친 신호·틀린 가정", "## 5. 다음에 바꿀 점")
# ── 숫자 검사(허용 목록, 운영자 결정 2026-11-08) ──────────────────────────────────────────
# 본문의 숫자는 '뜻'을 확인할 수 있을 때만 허용한다. 뜻을 확인하지 못한 숫자는 모두 막는다(막는 쪽으로 실패).
#  · 수익률·변화: %, %p, bp (범위 1~2% 포함)          · 회사 금액: 억·조 단위(원·달러 포함, '주당'은 제외)
#  · 날짜·시각·연도·주차: 11/4, 2026-11-05, 3월 5일, 15:30, +09:00, 2026년, 2026-W46
#  · 단위가 붙은 개수·기간·배수: 120만 대, 1,200명, 52주, 5거래일, 3분기, 1.2배, 2위
#  · 이름·코드 속 숫자: HBM3E, S&P 500, 코스피 200, Q3, v2, (000660), 000660.KS
#  · 지표 이름표가 바로 붙은 비율 값: 베타 1.2, 상관계수 0.65, RSI 28, PER 12.5, 확률 0.62
#  · 목록 번호(1. 2)), 0~10의 작은 정수
# 막는 것(예): 원·달러 가격(1,250,000원·$182·126만 원), 주가·종가 숫자, 지표 수준값(환율 1,442·WTI 78.4 → 변화율로 쓴다),
#            단위 없는 큰 숫자(1,264,000·94.73), 주당 금액(주당 1,444원 → 배당수익률 %로 쓴다)
_NUM = r"(?>\d{1,3}(?:,\d{3})+(?![\d])|\d+)"                     # 숫자 한 덩어리(원자: 긴 쉼표 줄에서 되돌아가지 않음)
_RNG = r"(?:\s*[~∼]\s*|(?<=\d)[–-](?=\d))"                          # 범위는 '~' 또는 숫자에 붙은 '-'만('94,700 -3.2%'는 범위가 아님)
_END = r"(?!\d|[,.]\d)"                                             # 숫자 끝: 천 단위 쉼표·소수점만 막고 문장부호는 허용
# 단위 뒤: 조사·접미사 하나 다음 낱말 끝, 또는 한글이 아닌 글자
_TAIL = r"(?:간|째|씩|여|가량|쯤|경|에서|에|으로|로|은|는|이|가|을|를|도|의|와|과|만|부터|까지|이다|이었다|였다|이며|이고|이상|이하|미만|안팎|동안|새|만에|봉|대|급)?(?![가-힣])"
_PRICEW = r"(?<!주가\s)(?<!종가\s)(?<!지수\s)(?<!코스피\s)(?<!코스닥\s)(?<!환율\s)(?<!가격\s)"
_DT = (r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:~\d{2}(?::\d{2})?)?(?:[+-]\d{2}:\d{2}|Z)?)?|\d{4}-W\d{2}"
       r"|(?<![\d,.])(?:19|20)\d{2}\.\s?\d{1,2}\.\s?\d{1,2}\.?(?![\d,])|(?<![\d,.])(?:19|20)\d{2}/\d{1,2}/\d{1,2}" + _END +
       r"|(?:19|20)\d{2}\s*(?:년도?|회계연도)(?:\s*\d{1,2}\s*월(?:\s*\d{1,2}\s*일)?)?|(?<![\d,.])\d{1,2}\s*월(?:\s*\d{1,2}(?:\s*[~∼]\s*\d{1,2})?\s*일)?"
       r"|" + _PRICEW + r"(?<![\d,.])(?:19|20)\d{2}\s*[~∼–-]\s*(?:19|20)?\d{2}(?=\s*(?:년|회계연도))"
       r"|(?<![\d,.])\d{1,2}/\d{1,2}(?:/\d{2,4})?" + _END + r"|(?<![\d,.])\d{1,2}:\d{2}(?::\d{2})?" + _END + r"|[+-]\d{2}:\d{2}"
       r"|(?<![\d,.])(?:[01]?\d|2[0-4])\s*시(?![간장작점총가세초])(?:\s*(?:[0-5]?\d\s*분|반))?")
_AMT = (r"(?<!주당)(?<!주당\s)(?<![\d,.$₩])" + _NUM + r"(?:\.\d+)?\s*(?:조(?:\s*" + _NUM + r"(?:\.\d+)?\s*(?:천\s*)?억)?|(?:천\s*)?억)(?:\s*" + _NUM + r"\s*만)?(?:\s*" + _NUM + r"\s*천)?"
        r"(?:\s*(?:원|달러|USD|KRW|엔|유로|위안)(?:어치)?)?")
_PCT = r"[+−-]?" + _NUM + r"(?:\.\d+)?(?:" + _RNG + r"[+−-]?" + _NUM + r"(?:\.\d+)?)?\s*(?:%p|%\s*포인트|%|퍼센트(?:\s*포인트)?|bps?(?![A-Za-z]))"
# 개수·기간·배수 단위 — 숫자에 '붙여' 쓴 경우만. 낱말이 되는 조합(평가·주가·초과·회의·단가·편이·배당…)은 단위로 보지 않는다. '대'는 아래 판매 문맥에서만.
_UNIT = (r"(?:명|개(?:사|국|월|년)?|건|곳|척|주(?:일|간|년|차)?(?!가|도|식|주|요|변|당|력|택)|거래일|년물|분기|반기|시간|분(?!석|야|할|위|명|배|산|쟁|기)"
         r"|초(?!과|반|기|점|래|안)|배(?!당|럴|분|제|송|경|터|치|정|출|상|열)|회(?!의|복|사|계|장|피|수|담|전|생|귀|원)|번(?:째)?|가지|단(?!가|위|계|기|일|독|순|체|기|속|점)"
         r"|층(?!이)|세대|종목|기업|팀|쪽|편(?!이|입|성|중|차|의)|권(?!고|리|역|한|유)|나노|인치|톤|리터|평(?!가|균|년|소|면)|㎡|가구|TEU|nm)")
_DAE_OLD = r"대(?=\s*$|\s*[,.)]|\s+(?:판매|생산|출하|인도|공급|수주|규모|분량|증산|감산|목표|계획|생산능력)|를\s*(?:팔|판매|생산|인도|공급|출하)|로\s*(?:(?!밀|떨|내렸|내려|하락|빠|올랐|상승|반등|급|회복|마감)[^.\n]){0,20}?(?:늘|줄|증가|감소|확대|축소)|에\s*(?:그쳤|못\s*미|달했|이르)|까지\s*(?:늘|확대|증산))"
_CNT = (r"(?<![\d,.$₩])(?:" + _NUM + r"(?:\.\d+)?(?:" + _RNG + _NUM + r"(?:\.\d+)?)?(?:여\s*)?)" + _UNIT + _TAIL
        + r"|(?<![\d,.$₩])\d{1,3}(?:일(?:선|간|째)?|년(?:간|째|차)?)(?!\s*(?:때|땐|경우|것|거|걸|게|건|리|줄|까지|가능성|듯|수(?![가-힣])|지(?![가-힣])|뿐|수록|텐|당시|무렵|시점|즈음|적))" + _TAIL
        + r"|(?<![\d,.$₩])" + _NUM + r"(?:\.\d+)?\s*[천만](?:\s*" + _NUM + r"\s*천?)?\s*(?:여\s*)?(?:명|개|건|곳|척|주(?!가|의|도)|장(?![가-힣])|권|편|가구|세대|톤|리터|평|배럴|계좌|TEU)" + _TAIL)
_IDX = r"(?:500|400|600|200|150|100|50|40|30|225|300|1000|2000|3000)" + _END
_INDEXN = r"(?:S&P|KOSPI|KOSDAQ|NASDAQ|Nasdaq|Russell|FTSE|Nikkei|Stoxx|STOXX|Dow(?:\s*Jones)?|DAX|CAC|KRX|KODEX|TIGER|ACE|RISE|SOL|코스피|코스닥|나스닥|러셀|닛케이|다우|유로스톡스)"
_NOCUR = r"(?!\s*(?:달러|원|유로|엔|위안|불|\$|USD|KRW))"
_NAME = (r"(?<![A-Za-z])" + _INDEXN + r"[\s-]*" + _IDX
         + r"|(?<![A-Za-z])(?:iPhone|아이폰|Galaxy|갤럭시|Pixel)\s*\d{1,2}" + _END + _NOCUR
         + r"|(?<![A-Za-z])(?:RTX|GTX)\s*[1-9]\d{3}" + _END + _NOCUR + r"|(?<![A-Za-z])(?:보잉|Boeing)\s*7[0-8]7" + _END + _NOCUR
         + r"|(?<![A-Za-z])(?:에어버스|Airbus)\s*A?3\d0" + _END + _NOCUR + r"|(?<![A-Za-z])(?:Gemini|Llama|Windows)\s*\d{1,2}(?:\.\d)?" + _END + _NOCUR
         + r"|(?<![\d,.])\d{1,4}(?=\s+(?:MAX|Pro|Ultra|Plus)(?![A-Za-z]))|(?<![A-Za-z0-9])3M(?![A-Za-z0-9])|(?<![\d,.])13F(?:-HR)?(?![A-Za-z])|(?<![\d,.])(?:10|8)-[KQ](?![A-Za-z])"
         + r"|(?<![\d,.])\d{6}\.K[SQ](?![A-Za-z])"
         + r"|(?<![A-Za-z&])(?!" + _INDEXN + r")(?!(?:KRW|USD|W)\d)[A-Za-z]{1,8}(?<=[A-Za-z])\d{1,4}(?:\.\d)?" + _END + _NOCUR   # HBM3E·H100·Q3·v2·FY2026
         + r"|(?<![\d,.$₩€¥£])(?:[1-4](?=Q)|[12](?=H)|(?:19|20)\d{2}(?=[EH]\d?)|[3-6](?=G)|\d{1,2}(?=D)|\d{1,2}(?:\.\d)?(?=x)|\d{1,2}(?=th|st|nd|rd)|(?:100|200|400|800|1\.6|3\.2)(?=[GT])"
         + r"|\d{1,4}(?:\.\d)?(?=nm|Gb|GB|TB|Tb|MB|GWh|MWh|GW|MW|kW|km|mm))(?=(?:Q|H\d?|E|G|T|D|x|th|st|nd|rd|nm|Gb|GB|TB|Tb|MB|GWh|MWh|GW|MW|kW|km|mm)(?![A-Za-z]))")                             # 3nm·25x·16Gb·3Q·5G
_LNUM = r"[+−-]?\d{1,2}(?:\.\d+)?(?!\d|[,.]\d|\s*(?:[만천억조]|원|달러|\$))"
_LABEL = (r"(?:베타|상관계수|상관|RSI|PER|PBR|PSR|EV/EBITDA|확률|가능성|p_beat|p\s*beat|샤프\s*지수|p\s*값|z\s*값)\s*(?:\((?:[^)\d\n]|\d{1,2}(?![\d,.])){0,40}\))?\s*(?:은|는|이|가|:|=|를|을)?\s*(?:약\s*)?"
          + _LNUM + r"(?:\s*(?:→|->|~)\s*" + _LNUM + r"|\s*에서\s*" + _LNUM + r"\s*(?:으로|로))*")
_LABEL += r"|(?<![A-Za-z])PEG\s*(?:은|는|이|가|:|=)?\s*(?:약\s*)?\d(?:\.\d+)?(?:\s*[~→]\s*\d(?:\.\d+)?)?(?!\d|[,.]\d|\s*(?:[만천억조]|원|달러|\$))"   # PEG는 10 미만만(티커 PEG의 주가와 구분)
_LIST = r"^[ \t]*(?:[-*][ \t]*)?\(?\d{1,2}[.)]\s|^#+[ \t]*\d+(?:[.-]\d+)*\.?\s"
_SMALL = (r"(?<![\d,.$₩€¥£])(?:10|\d)(?!\d|[,.]\d|\s*(?:[천만억조]|달러|원|센트|엔|유로|위안|불|파운드|USD|KRW|EUR|JPY|GBP))"
          r"|(?<![\d,.])\d{1,3}(?:위권?|등|차)(?![가-힣])")   # 작은 정수, 순위·차수(2위·20위권·1차)
_ALLOW = re.compile("|".join(f"(?:{x})" for x in (_DT, _AMT, _PCT, _NAME, _LABEL, _CNT, _LIST, _SMALL)), re.M)
_KR_CODES = None


_US_TICKERS = None
# 영문자에 붙은 숫자가 지표·통화·종목 티커의 수준값·가격일 수 있는 앞 글자(대소문자 무시)
_TICKER_NAMES = {"GS25", "ARM64", "ARM32", "USB3", "USB4", "GEN2", "GEN3", "GEN4", "GEN5", "GE9X"}
_INDEX_PFX = {"SP", "KOSPI", "KOSDAQ", "NASDAQ", "RUSSELL", "NIKKEI", "FTSE", "STOXX", "DOW", "DAX", "CAC", "KRX", "KODEX", "TIGER", "미국SP"}
_BAD_PFX = {"SPX", "NDX", "SOX", "VIX", "DJIA", "DJI", "WTI", "BRENT", "DUBAI", "KRW", "USD", "EUR", "JPY", "GBP", "CNY", "CHF", "HKD", "AUD", "CAD", "W", "X",
            "BTC", "ETH", "DXY", "BRK", "SPY", "QQQ", "SOXX", "DIA", "IWM", "TLT", "GLD", "XAU", "XAG", "GOLD", "SILVER", "COPPER", "OIL", "NDQ", "SPXL", "TQQQ", "KOSPI", "KOSDAQ", "NASDAQ", "SP", "RUSSELL", "NIKKEI", "FTSE", "STOXX", "DOW", "DAX", "CAC", "KRX", "PEG"}


def _kr_codes() -> dict:
    """대상 종목 목록의 한국 코드 → 종목명."""
    global _KR_CODES, _US_TICKERS
    if _KR_CODES is None:
        _KR_CODES, _US_TICKERS = {}, set()
        for f in [L.ROOT / "league/universe.json", *sorted((L.ROOT / "league/universe").glob("*.json"))]:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                _KR_CODES.update({k: v for k, v in (d.get("KR") or {}).items() if isinstance(v, str)})
                _US_TICKERS |= {k.upper() for k in (d.get("US") or {}) if len(k) >= 2}
            except (OSError, ValueError, AttributeError):
                pass
    return _KR_CODES


_DAE_RE = re.compile(r"(?<![\d,.$₩])" + _NUM + r"(?:\.\d+)?\s*[천만](?:\s*" + _NUM + r"\s*천?)?\s*(?:여\s*)?대(?!비|\s*(?:초반|중반|후반))")
# '만 대'가 대수라는 증거: 판매·생산 낱말이 숫자 바로 앞에 붙거나(판매 120만 대·판매량은 46만 대에서 …) '대' 바로 뒤에 판매 동사가 붙을 때(120만 대를 팔았다)만.
_SALES = r"(?:판매|생산|출하|인도|공급|수출(?!주)|내수|등록|수주|증산|감산)(?:량|대수|실적|능력)?"
_SALES = r"(?:판매|생산|출하|인도|공급|수출(?!주)|내수|등록|수주|증산|감산|연산|리콜(?:\s*대상)?)(?:량|대수|실적|능력)?"
_PERIOD = r"(?:(?:약|연간|월간|월|올해|모두|누적|(?:19|20)?\d{2}년|\d{1,2}(?:분기|월)|[1-4]Q|상반기|하반기)\s*)*"
_DAE_TAIL = (r"\s*(?:은|는|이|가|도|을|를|:|\(|\|)?\s*" + _PERIOD +
             r"(?:[\d,.]+\s*[천만](?:\s*[\d,]+\s*천?)?\s*(?:여\s*)?대(?:에서|→|->|~)\s*" + _PERIOD + r")?$")
# 강한 증거: 판매·생산 낱말(또는 '판매 목표'·'연간 목표')이 숫자 바로 앞에 붙음
_DAE_PRE = re.compile(r"(?:" + _SALES + r"(?:\s*(?:목표|계획|전망치|예상치|컨센서스))?|(?:연간|올해|월간)\s*(?:판매\s*|생산\s*)?(?:목표|계획))" + _DAE_TAIL)
# 약한 증거: 제품·시설 낱말(낱말 시작) — 판매 동사·판매 낱말이 함께 있을 때만
_DAE_WEAK = re.compile(r"(?<![가-힣])(?:공장|누적|전기차|자동차|스마트폰|로봇|드론|차량|PC)(?:의)?\s*" + _DAE_TAIL)
_DAE_POST = re.compile(r"(?:를|가|도|씩)?\s*(?:팔았|팔린|팔아|팔렸|판매|생산|출하|인도(?!\s*(?:증시|시장|경제|루피))|공급했|수출했|넘게\s*팔|리콜)")
_DAE_POST2 = re.compile(r"(?:로|까지)\s*(?:늘린|줄인|늘리|줄이|증산|감산)|\s*(?:판매\s*|생산\s*)?(?:목표|계획|생산능력|캐파|보급|규모의\s*리콜)")   # 판매 낱말·약한 증거와 함께일 때만
_DAE_NO = re.compile(r"주가|종가|시가(?!총액)|목표가|목표주가|환율|지수|가격|시세|코스피|코스닥|나스닥|고점|저점|매수가|매도가|평단|증권가|증권사|애널리스트|리포트|투자의견|컨센서스|매수|매도|비중|단가|진입|분할")
_DAE_MOVE = re.compile(r"밀렸|밀린|밀려|내려|내린|떨어|하락|상승|올랐|오른|반등|출발|마감|미끄러|주저앉|회복|이탈|횡보|머물|저항|지지|버티|초입|낮아|높아|하향|상향|무너|붕괴|추락|돌파|급락|빠졌|빠지|깨|후퇴|되돌|내줬|올려|낮춰|제시|시작|잡았")
_SENT = re.compile(r"(?<!\d)[.!?](?!\d)|\n")


def number_issues(t: str, limit: int = 3) -> list[str]:
    """뜻을 확인하지 못한 숫자들(앞뒤 문맥과 함께). 첫 줄 pick_id와 URL은 보지 않는다."""
    body = re.sub(r"https?://[A-Za-z0-9\-._~:/?#@!$&'*+=%]+", " ", t)             # URL은 URL 글자(쉼표·괄호 제외)까지만 지운다
    body = re.sub(r"\A# 손실 복기 — .*$", " ", body, flags=re.M)
    masked = list(body)
    codes = _kr_codes()
    head = re.search(r"\A(?:.*\n){0,6}?- 종목:[^\n]*", body)                    # 머리글의 '- 종목:' 줄(첫 절 앞): 첫 괄호의 티커 하나만
    if head and "## " not in head.group(0):
        m = re.search(r"\(\s*([0-9][0-9A-Z]{5}|[A-Z]{1,5}(?:\.[A-Z])?)\s*\)", head.group(0))
        if m and (not m.group(1)[0].isdigit() or m.group(1) in codes):
            for k in range(m.start(1), m.end(1)):
                masked[k] = " "
    for m in re.finditer(r"\(\s*([0-9A-Z]{6})\s*\)", body):                     # 괄호 속 종목코드: 바로 앞이 그 코드의 종목명일 때만
        nm = codes.get(m.group(1))
        if nm and body[:m.start()].rstrip().endswith(nm):
            for k in range(m.start(1), m.end(1)):
                masked[k] = " "
    import bisect
    bounds = [x.end() for x in _SENT.finditer(body)]                            # 문장 경계는 한 번만 계산(긴 글에서 제곱 시간 방지)
    for m in _DAE_RE.finditer(body):                                            # '만 대': 판매 낱말이 붙어 있고, 문장에 가격 낱말·'대' 뒤 가격 움직임이 없을 때만 대수
        k = bisect.bisect_right(bounds, m.start())
        ls = bounds[k - 1] if k else 0
        k2 = bisect.bisect_left(bounds, m.end() + 1)
        le = bounds[k2] - 1 if k2 < len(bounds) else len(body)
        sent, pre, post = body[ls:le], body[ls:m.start()], body[m.end():le]
        has_sales = re.search(_SALES, sent)
        weak = _DAE_WEAK.search(pre[-28:])
        yearly = re.search(r"(?:연간|올해|월간)\s*$", pre)
        exp = re.search(r"(?:예상치|전망치|예상)\s*(?:은|는|인|\()?\s*$", pre) and has_sales     # '인도량은 …, 예상치 47만 대'
        pm = _DAE_PRE.search(pre[-32:])
        strong = pm or _DAE_POST.match(post)
        loose = ((re.match(r"\s*로\s*집계", post) and has_sales) or (_DAE_POST2.match(post) and (has_sales or weak or yearly))
                 or (weak and has_sales) or exp)
        near = pre[-(len(pm.group(0)) + 4):] if pm else pre[-6:]
        price = _DAE_NO.search(near) if strong else _DAE_NO.search(sent)                 # 판매 낱말이 붙어 있으면 가격 낱말은 그 사이만 본다
        if (strong or loose) and not price and not _DAE_MOVE.search(post[:12]):
            for k in range(m.start(), m.end()):
                masked[k] = " "
    for m in _ALLOW.finditer("".join(masked)):
        for k in range(m.start(), m.end()):
            masked[k] = " "
    _kr_codes()
    for m in re.finditer(r"(?<![A-Za-z&])(?<!\d{4}-)([A-Za-z&]{1,8})(\d[\d.]*)", body):     # 지표·통화·종목 티커에 붙은 숫자는 식별자로 보지 않는다
        pf, num = m.group(1).upper(), m.group(2).rstrip(".")
        fx = len(pf) == 6 and pf[:3] in _BAD_PFX and pf[3:] in _BAD_PFX                   # USDJPY 같은 통화쌍
        if pf.replace("&", "") in _INDEX_PFX and re.fullmatch(_IDX[:_IDX.index(")") + 1], num):
            continue                                                                   # S&P500·KOSPI200은 지수 이름
        tick = (pf in (_US_TICKERS or ()) and (len(num) >= 2 or "." in num) and pf + num not in _TICKER_NAMES   # KO96은 막고 GS25·ARM64는 이름
                and not (pf in ("RTX", "GTX") and re.fullmatch(r"[1-9]\d{3}", num)))    # RTX5090은 제품명
        if pf.replace("&", "") in _BAD_PFX or tick or fx:
            for k in range(m.start(2), m.end(2)):
                masked[k] = body[k]
    out, ms = [], "".join(masked)
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", ms):
        a, b = m.start(), m.end()
        ctx = " ".join(body[max(0, a - 14):min(len(body), b + 10)].split())
        out.append(f"{body[a:b]!r} (… {ctx} …)")
        if len(out) >= limit:
            break
    return out


def review_dir(d: Path) -> Path:
    return d / "reviews" / "losses"


def review_path(d: Path, p: dict) -> Path:
    return review_dir(d) / p["round_date"] / f"{p['agent_id']}-{p['market']}.md"


def first_id(f: Path) -> str:
    """복기 파일 첫 줄의 pick_id(없으면 빈 문자열)."""
    try:
        line = f.read_text(encoding="utf-8").split("\n", 1)[0]
    except (OSError, UnicodeDecodeError):
        return ""
    m = re.fullmatch(r"# 손실 복기 — (\S+)\s*", line)
    return m.group(1) if m else ""


def done(f: Path, pid: str) -> bool:
    """이 종목의 복기가 끝났나: 파일이 있고, 검사를 통과하고, 첫 줄 pick_id가 이 종목(팀·모드 포함)과 정확히 같다.
    같은 경로에 다른 팀·모드(연습 sandbox-) 복기가 있으면 끝난 것으로 보지 않는다(슈슈 검수 2026-11-08 C)."""
    return f.exists() and first_id(f) == pid and not check(f)


def due(d: Path) -> list[dict]:
    cfg = L.load_config(d)
    scores = L.latest_scores(d)
    roster = L.load_roster(d)
    nick = {a["id"]: a for a in roster.get(TEAM, []) + roster.get("bench", [])}
    out = []
    for p in L.read_ledger(d, "picks"):
        if p.get("team") not in (TEAM, f"sandbox-{TEAM}") or L.is_watch(p, cfg):
            continue
        s = scores.get(p["pick_id"]) or {}
        if s.get("status") != "final" or s.get("score") is None or s["score"] >= 0:
            continue
        f = review_path(d, p)
        if done(f, p["pick_id"]):
            continue   # 검사를 통과한 이 종목의 복기가 있으면 끝. 쓰다 만·실패·다른 ID 파일은 다시 대상

        a = nick.get(p["agent_id"], {})
        out.append({"pick_id": p["pick_id"], "agent_id": p["agent_id"], "nickname": a.get("nickname", ""), "label": p.get("agent_label") or a.get("label", ""),
                    "agent_version": p.get("agent_version"), "round_date": p["round_date"], "market": p["market"], "ticker": p["ticker"], "name": p.get("name", ""),
                    "base_session": p.get("base_session"), "eval_session": s.get("eval_session") or p.get("eval_session"),
                    "score": s["score"], "benchmark": s.get("benchmark"), "benchmark_return": s.get("benchmark_return"), "score_excess": s.get("score_excess"),
                    "rationale": p.get("rationale", ""), "risks": p.get("risks", []), "sources": [x.get("url") for x in p.get("sources", []) if isinstance(x, dict)],
                    "path": str(f.relative_to(L.ROOT)) if f.is_relative_to(L.ROOT) else str(f)})
    return sorted(out, key=lambda x: (x["round_date"], x["agent_id"], x["market"]))


def due_bundle(bundle: Path, team: str, reviews: Path, mode: str = "실전") -> list[dict]:
    """공개 결과 묶음(results.json)만으로 마이너스 확정 종목을 찾는다(원장이 없는 슈슈 팀 안전 사본용).
    team은 묶음의 팀 이름 일부(예: '슈슈', '로로'). 관망·잠정·보류 제외, 복기 파일이 있으면 제외."""
    kind = _layout(reviews / "0000-00-00" / "x-KR.md")
    if (mode == "연습" and kind == "real") or (mode == "실전" and kind == "sandbox"):
        raise SystemExit(f"--mode {mode}와 복기 폴더 {reviews}가 맞지 않음 — 실전은 <리그>/reviews/losses, 연습은 <리그>/sandbox/reviews/losses(또는 모드별 별도 폴더)")
    data = json.loads(bundle.read_text(encoding="utf-8"))
    out = []
    for p in data.get("picks", []):
        if team not in str(p.get("team", "")) or (mode and p.get("mode") != mode) or p.get("watch"):
            continue
        if p.get("status") != "final" or p.get("score") is None or p["score"] >= 0:
            continue
        f = reviews / p["round_date"] / f"{p['agent_id']}-{p['market']}.md"
        if done(f, p["pick_id"]):
            continue
        other = first_id(f) if f.exists() else ""
        out.append({"pick_id": p["pick_id"], "agent_id": p["agent_id"], "agent": p.get("agent", ""), "round_date": p["round_date"], "market": p["market"],
                    "ticker": p.get("ticker"), "name": p.get("name", ""), "score": p["score"], "score_excess": p.get("score_excess"), "path": str(f),
                    **({"occupied_by": other} if other and other != p["pick_id"] else {})})
    return sorted(out, key=lambda x: (x["round_date"], x["agent_id"], x["market"]))


def _known_closes(path: Path) -> list[str]:
    """복기 파일 경로(<리그>/reviews/losses/<라운드>/<에이전트>-<시장>.md)로 그 종목의 원장 종가를 찾아, 본문에 나올 수 있는 표기들을 돌려준다.
    숫자 뜻 검사(number_issues)와 별도로, 실제 기록된 원 가격은 어떤 꼴로 써도 막기 위한 정확한 안전장치다(원장이 없으면 빈 목록)."""
    try:
        d = path.resolve().parents[3]
        rd = path.parent.name; aid, mk = path.stem.rsplit("-", 1)
        picks = [p for p in L.read_ledger(d, "picks") if p.get("round_date") == rd and p.get("agent_id") == aid and p.get("market") == mk]
        if not picks:
            return []
        tk = picks[-1]["ticker"]
        out = set()
        for r in L.read_ledger(d, "prices"):
            if r.get("market") == mk and r.get("ticker") == tk and r.get("close"):
                c = float(r["close"])
                # 정수 종가: 쉼표 표기(1,264,000·2,026)는 늘, 쉼표 없는 표기는 1만 이상만(2026·150 같은 연도·셈과 부딪히지 않게)
                if c == int(c):
                    if c >= 1000:
                        out.add(f"{c:,.0f}")
                    if c >= 10000:
                        out.add(f"{c:.0f}")
                    out |= {f"{c:,.2f}", f"{c:.2f}", f"{c:,.1f}", f"{c:.1f}"}   # 180.00 · 1,396,000.0 같은 소수 표기
                    if c >= 10000:   # 만 단위 표기: 126.4만, 126만 4천, 126만4천
                        a, r = divmod(int(c), 10000)
                        out.add(f"{c / 10000:.4f}".rstrip("0").rstrip(".") + "만")
                        if r and r % 1000 == 0:
                            out |= {f"{a:,}만 {r // 1000}천", f"{a:,}만{r // 1000}천", f"{a}만 {r // 1000}천", f"{a}만{r // 1000}천"}
                        if r:   # 126만 4,000 · 9만 2,150
                            out |= {f"{a}만 {r:,}", f"{a}만{r:,}", f"{a}만 {r}", f"{a}만{r}"}
                else:
                    out |= {f"{c:,.2f}", f"{c:.2f}", f"{c:,.2f}".rstrip("0"), f"{c:.2f}".rstrip("0")}
        return sorted(out, key=len, reverse=True)
    except Exception:
        return []


def check(path: Path) -> list[str]:
    errs = []
    if not path.is_file():
        return [f"{path}: 파일 없음"]
    try:
        t = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [f"읽을 수 없는 파일(UTF-8 아님 등): {type(e).__name__}"]
    m = re.match(r"(\d{4}-\d{2}-\d{2})/([a-z0-9]+)-(KR|US)\.md$", "/".join(path.parts[-2:]))
    if not m:
        errs.append("경로는 reviews/losses/<라운드>/<에이전트>-<KR|US>.md")
    if not t.startswith("# 손실 복기 — "):
        errs.append("첫 줄은 '# 손실 복기 — <pick_id>'")
    elif m and not re.fullmatch(rf"# 손실 복기 — {m.group(1)}-(?:sandbox-)?[a-z]+-{m.group(2)}-{m.group(3)}\s*", t.splitlines()[0]):
        errs.append("첫 줄 pick_id(<라운드>-<팀>-<에이전트>-<시장>)가 파일 경로와 다름")
    pos = [t.find(s) for s in SECTIONS]
    for s, i in zip(SECTIONS, pos):
        if i < 0:
            errs.append(f"절 없음: {s}")
    if all(i >= 0 for i in pos) and pos != sorted(pos):
        errs.append("절 순서가 다름")
    if m and t.startswith("# 손실 복기 — "):
        sb = first_id(path).startswith(f"{m.group(1)}-sandbox-")
        kind = _layout(path)
        under_sb = kind == "sandbox"
        if sb and kind == "real":
            errs.append("연습(sandbox-) 복기는 연습 폴더(league/sandbox/reviews/losses)에 둔다")
        elif under_sb and not sb:
            errs.append("연습 폴더의 복기는 첫 줄 pick_id가 '<라운드>-sandbox-<팀>-…'이어야 한다")
    vs = re.findall(r"^판정:[ \t]*(.*?)[ \t]*$", t, re.M)
    if len(vs) != 1:
        errs.append(f"'판정:' 줄은 정확히 하나 — 지금 {len(vs)}개")
    elif not re.search(r"^판정:", _section(t, "## 3. 판정"), re.M):
        errs.append("'판정:' 줄은 3절(## 3. 판정) 안에 둔다")
    elif vs[0] not in VERDICTS:
        errs.append(f"판정 줄에는 판정 이름 하나만: <{' | '.join(VERDICTS)}> (이유·부정 표현은 다음 줄에) — 지금 {vs[0]!r}")
    tb = re.sub(r"https?://[^\s가-힣]+", "", t)
    tb = re.sub(r"\A((?:.*\n){0,6}?- 종목:[^\n(]*)\([^)\n]*\)", r"\1", tb, count=1)   # 머리글 '- 종목:' 줄의 티커 괄호·출처 URL 숫자는 대조하지 않음
    for c in _known_closes(path):
        unit = r"%|배|만|억|조|주(?![변가당요간])|개|명|척|건|곳|거래일" + ("" if "," in c else r"|일|대|년")
        if re.search(r"(?<![\d.,\-/:])" + re.escape(c) + r"(?![\d]|[.,]\d|[\-/:T]\d|\s*(?:" + unit + r"))", tb):
            errs.append(f"원장에 기록된 이 종목의 종가와 같은 숫자 {c!r} — 원 가격 금지")
            break
    if not (600 <= len(t) <= 6000):
        errs.append(f"길이 {len(t)}자 — 600~6000자")
    bad = number_issues(t) if len(t) <= 6000 else []
    if bad:
        errs.append("뜻을 확인할 수 없는 숫자(원 가격·지표 수준값·단위 없는 숫자 금지 — 수익률 %·%p, 억·조 금액, 날짜, 단위 붙은 개수로 쓴다): " + "; ".join(bad))
    s2 = t[t.find("## 2."):t.find("## 3.")] if "## 2." in t and "## 3." in t else ""
    if s2:
        url_lines = [x for x in s2.splitlines() if _URL.search(x)]
        if not url_lines and "출처 확인 못함" not in s2:
            errs.append("2절에 확인한 출처 URL(https://도메인/…)이 하나 이상 필요(못 찾았으면 '출처 확인 못함'과 이유를 적는다)")
        nostamp = [x for x in url_lines if not _STAMP.search(x)]
        if nostamp:
            errs.append(f"2절 출처마다 확보 시각(YYYY-MM-DDTHH:MM(:SS)+09:00)이 필요 — 시각 없는 출처 줄 {len(nostamp)}개")
    s5 = _section(t, "## 5. 다음에 바꿀 점")
    fr = next((x for x in _FIXED_RULE.finditer(s5) if _is_fixed(s5, x)), None)
    if fr:
        errs.append(f"5절에 특정 종목·업종을 고정으로 넣거나 빼는 규칙으로 보이는 표현: {fr.group(0)!r} — 판단 습관(점검 항목)으로 쓴다")
    return errs


_URL = re.compile(r"https?://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?:[/?#]\S*)?")
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:~\d{2}(?::\d{2})?)?\+09:00")
# 경험칙: '항상·영구·절대·무조건·앞으로 계속 … 제외/빼/넣/편입/사지 않/피한' (형식 검사일 뿐 — 의미 검수는 주간 복기가 한다)
_FX_ALWAYS = r"(?:항상|영구히?|절대|무조건|앞으로|당분간|다시는|더는|더\s*이상)"
_FX_TARGET = r"[가-힣A-Za-z&]{2,12}(?:은|는|을|를|도)(?![가-힣])|종목|업종|섹터|티커|테마|[가-힣]{1,6}(?<!매)주(?![가-힣])|[가-힣]{1,6}주(?=[는은를을도만])"
_FX_VERB = r"(?:제외|빼|뺀|뺄|넣|편입|사지\s*않|고르지\s*않|담지\s*않|추천하지\s*않|안\s*산|매수하지\s*않|피한|피하)"
_FIXED_RULE = re.compile(_FX_ALWAYS + r"[^.\n]{0,25}?(?P<t1>" + _FX_TARGET + r")[^.\n]{0,20}?" + _FX_VERB
                         + r"|(?P<t2>" + _FX_TARGET + r")[^.\n]{0,20}?" + _FX_ALWAYS + r"[^.\n]{0,20}?" + _FX_VERB)
_HABIT = re.compile(r"관망|베팅|원인|신호|정보|공시|뉴스|요소|카드|선택지|판단|계산|비교|흐름|수급|숫자|이유|사례|이벤트|촉매|낙폭|증폭|베타|점검|체크리스트|항목|근거|논리|기준|확인|가정|일정|지표|데이터|자료|위험|변수|시나리오|(?<!무)조건|요인|비중|가중|후보군에서\s*빼지")


def _is_fixed(text: str, x) -> bool:
    """대상 명사구(조사 앞 낱말)만 보고 판단 습관(점검·근거·흐름…)이면 규칙이 아님. '촉매가 없는 종목'처럼 조건이 붙은 대상도 습관."""
    k = "t1" if x.group("t1") else "t2"
    tgt, st = x.group(k), x.start(k)
    if k == "t1":   # 매치 안의 마지막 대상(동사에 가장 가까운 명사구)
        for y in re.finditer(_FX_TARGET, text[st:x.end()]):
            tgt, st = y.group(0), st + y.start() if False else x.start(k) + y.start()
    pre = text[max(0, st - 12):st]
    if re.search(r"(?:항목|목록|체크리스트|점검)(?:에|으로)\s|뒤에만|(?:모르|없으|있으|않으|오|나오|크|작|높으|낮으)면\s|(?:근거|논리|판단|후보\s*근거)에서\s*(?:빼|뺀|뺄)", x.group(0)):
        return False
    cond = re.search(r"(?:없는|있는|낮은|높은|약한|강한|큰|작은|못한|않은|고른|본|산|인|[가-힣](?:는|은|던|한|된|진|린|운|른|둔|온|난|간|낸|친|든)|의)\s*$", pre) \
        and not re.search(_FX_ALWAYS + r"\s*(?:는|은)?\s*$", pre)          # '앞으로는 테슬라를'의 '는'은 조건 수식이 아님
    return not _HABIT.search(tgt + " " + pre) and not cond


def _layout(path: Path) -> str:
    """리그 표준 배치(<리그>/reviews/losses/<라운드>/<파일>)면 'sandbox'·'real', 아니면 'other'(별도 폴더 — 폴더 검사 안 함)."""
    rp = path.resolve()
    if len(rp.parents) > 3 and rp.parents[1].name == "losses" and rp.parents[2].name == "reviews":
        return "sandbox" if rp.parents[3].name == "sandbox" else "real"
    return "other"


def listing(d: Path, week: str | None = None) -> list[dict]:
    out = []
    for f in sorted(review_dir(d).glob("*/*.md")):
        rd = f.parent.name
        try:
            if week and L.iso_week(date.fromisoformat(rd)) != week:
                continue
        except ValueError:
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            t = ""
        v = re.search(r"^판정:\s*(.+)$", t, re.M)
        out.append({"round_date": rd, "file": f.name, "path": str(f), "verdict": v.group(1).strip() if v else ""})
    return out


def _section(t: str, head: str) -> str:
    i = t.find(head)
    if i < 0:
        return ""
    j = t.find("\n## ", i + len(head))
    return t[i + len(head): j if j >= 0 else None].split("\n", 1)[-1].strip()


def _weeks_back(week: str, n: int) -> set[str]:
    y, w = week.split("-W")
    mon = date.fromisocalendar(int(y), int(w), 1)
    return {L.iso_week(date.fromordinal(mon.toordinal() - 7 * k)) for k in range(n)}


def _status_lookup(d: Path, bundle: Path | None, team: str | None, mode: str | None):
    """pick_id → (집계 여부, 사유). 최신 결과(원장 또는 결과 묶음)로 '지금도 확정 손실인가'를 다시 확인한다."""
    if bundle:
        data = json.loads(Path(bundle).read_text(encoding="utf-8"))
        picks = {p.get("pick_id"): p for p in data.get("picks", [])}
        def look(pid):
            p = picks.get(pid)
            if not p:
                return None, "결과 묶음에 없음"
            if (team and team not in str(p.get("team", ""))) or (mode and p.get("mode") != mode):
                return False, "다른 팀·모드"
            if p.get("watch"):
                return False, "관망"
            if p.get("status") != "final" or p.get("score") is None:
                return False, f"확정 아님({p.get('status') or '점수 없음'})"
            return (True, "") if p["score"] < 0 else (False, f"정정됨({p['score']:+.2f}%)")
        return look, "결과 묶음"
    if (d / "ledger").exists():
        scores, cfg = L.latest_scores(d), L.load_config(d)
        picks = {p["pick_id"]: p for p in L.read_ledger(d, "picks")}
        def look(pid):
            p, sc = picks.get(pid), scores.get(pid) or {}
            if not p:
                return None, "원장에 없음"
            if p.get("team") not in (TEAM, f"sandbox-{TEAM}"):
                return False, "다른 팀"
            if L.is_watch(p, cfg):
                return False, "관망"
            if sc.get("status") != "final" or sc.get("score") is None:
                return False, f"확정 아님({sc.get('status') or '점수 없음'})"
            return (True, "") if sc["score"] < 0 else (False, f"정정됨({sc['score']:+.2f}%)")
        return look, "원장"
    return (lambda pid: (None, "최신 결과 자료 없음(--bundle 필요)")), "없음"


def summary(d: Path, week: str, weeks: int = 1, reviews: Path | None = None, bundle: Path | None = None,
            team: str | None = None, mode: str | None = None) -> dict:
    """에이전트별: 복기 수, 판정별 개수와 pick_id, '바꿀 점' 항목, 반복 신호.
    집계에는 '검사 통과 + 첫 줄 pick_id가 경로와 맞음 + 최신 결과로 지금도 확정 손실'인 복기만 넣는다.
    정정·확정 아님(corrected), 검사 불합격(invalid), 결과로 확인 못함(pending)은 따로 적는다(원래 파일은 그대로 둔다).
    반복 신호 = 같은 판정이 2건 이상(특히 '분석 실수') — v2.1 규칙의 '같은 유형 오류 pick_id 2건 이상' 후보. 최종 판단은 주간 복기가 한다."""
    want = _weeks_back(week, max(1, weeks))
    agents: dict[str, dict] = {}
    look, source = _status_lookup(d, bundle, team, mode)
    corrected, invalid, pending = [], [], []
    for f in sorted((reviews or review_dir(d)).glob("*/*.md")):
        rd = f.parent.name
        try:
            if L.iso_week(date.fromisoformat(rd)) not in want:
                continue
        except ValueError:
            continue
        m = re.match(r"([a-z0-9]+)-(KR|US)$", f.stem)
        if not m:
            continue
        aid, mk = m.groups()
        errs = check(f)
        if errs:
            invalid.append({"path": str(f), "errors": [re.sub(r"\d", "#", e) for e in errs[:3]]})   # 요약은 커밋되므로 막힌 숫자를 싣지 않는다
            continue
        t = f.read_text(encoding="utf-8")
        pid = first_id(f)
        ok, why = look(pid)
        if ok is None:
            pending.append({"pick_id": pid, "reason": why})
            continue
        if not ok:
            corrected.append({"pick_id": pid, "reason": why})
            continue
        verdict = re.search(r"^판정:[ \t]*(.*?)[ \t]*$", t, re.M).group(1)
        res = re.search(r"^- 결과:\s*([+−-]?\d+(?:\.\d+)?)%", t, re.M)
        score = float(res.group(1).replace("−", "-")) if res else None
        fixes = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", x).strip() for x in _section(t, "## 5. 다음에 바꿀 점").splitlines()]
        fixes = [x for x in fixes if len(x) >= 8 and not x.startswith(("(", "（", ">"))][:4]
        a = agents.setdefault(aid, {"agent_id": aid, "reviews": 0, "verdicts": {}, "fixes": [], "scores": []})
        a["reviews"] += 1
        a["verdicts"].setdefault(verdict, []).append(pid)
        a["fixes"] += [{"pick_id": pid, "text": x} for x in fixes]
        if score is not None:
            a["scores"].append(score)
    for a in agents.values():
        a["repeated"] = {k: v for k, v in a["verdicts"].items() if len(v) >= 2}
        a["mistakes"] = len(a["verdicts"].get("분석 실수", []))
    rows = sorted(agents.values(), key=lambda a: (-a["mistakes"], -a["reviews"], a["agent_id"]))
    return {"week": week, "weeks": sorted(want), "source": source, "agents": rows, "corrected": corrected, "invalid": invalid, "pending": pending,
            "totals": {k: sum(len(a["verdicts"].get(k, [])) for a in rows) for k in VERDICTS}}


def summary_md(s: dict, names: dict | None = None) -> str:
    names = names or {}
    L_ = [f"# 손실 복기 요약 — {s['week']}" + (f" (최근 {len(s['weeks'])}주: {', '.join(s['weeks'])})" if len(s["weeks"]) > 1 else ""), ""]
    extra = []
    if s.get("corrected"):
        extra += [f"- 정정·확정 아님(집계 제외, 원래 복기는 보존): " + ", ".join(f"{c['pick_id']} ({c['reason']})" for c in s["corrected"])]
    if s.get("invalid"):
        extra += [f"- 검사 불합격(집계 제외): " + "; ".join(f"{Path(x['path']).parent.name}/{Path(x['path']).name} — {x['errors'][0]}" for x in s["invalid"])]
    if s.get("pending"):
        extra += [f"- 최신 결과로 확인 못함(검토 대기, 집계 제외): " + ", ".join(f"{x['pick_id'] or '(ID 없음)'} ({x['reason']})" for x in s["pending"])]
    extra = (["집계 밖:", *extra, ""] if extra else []) + [f"> 대조한 최신 결과: {s.get('source', '?')}. 집계는 형식 검사 통과 + 지금도 확정 손실인 복기만. 형식 검사 '통과'는 내용(근거의 진위·사후 정보·고정 규칙)을 보증하지 않는다.", ""]
    if not s["agents"]:
        return "\n".join(L_ + ["이 기간에 집계할 손실 복기가 없습니다.", ""] + extra)
    L_ += ["| 에이전트 | 복기 | " + " | ".join(VERDICTS) + " | 반복 신호 |", "|---|---:|" + "---:|" * len(VERDICTS) + "---|"]
    for a in s["agents"]:
        rep_ = ", ".join(f"{k} {len(v)}건" for k, v in a["repeated"].items()) or "—"
        L_.append(f"| {names.get(a['agent_id'], a['agent_id'])} | {a['reviews']} | " + " | ".join(str(len(a["verdicts"].get(k, []))) for k in VERDICTS) + f" | {rep_} |")
    L_ += ["", "판정별 합계: " + " · ".join(f"{k} {n}" for k, n in s["totals"].items() if n), "",
           *extra,
           "> 반복 신호는 '같은 판정 2건 이상'일 뿐이다. 개선안 근거가 되려면 주간 복기가 원인이 같은 유형인지 확인한다(규칙 v2.1). '시장 전체 움직임'·'운·잡음'은 지침 수정 근거가 아니다.", ""]
    for a in s["agents"]:
        L_.append(f"## {names.get(a['agent_id'], a['agent_id'])}")
        for k, v in a["verdicts"].items():
            L_.append(f"- {k}: {', '.join(v)}")
        if a["fixes"]:
            L_.append("- 바꿀 점(복기 제안):")
            L_ += [f"  - {x['text']} ({x['pick_id']})" for x in a["fixes"]]
        L_.append("")
    return "\n".join(L_)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["due", "check", "list", "summary"])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dir", default="league")
    ap.add_argument("--week")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--weeks", type=int, default=1, help="summary: 이번 주 포함 최근 몇 주")
    ap.add_argument("--out", help="summary: 마크다운 저장 경로")
    ap.add_argument("--bundle", help="due·summary: 원장 대신 결과 묶음(results.json)으로 찾기·대조(슈슈 안전 사본용)")
    ap.add_argument("--team", default="로로", help="--bundle: 팀 이름 일부")
    ap.add_argument("--reviews", help="due --bundle / summary: 복기 폴더(기본 <dir>/reviews/losses)")
    ap.add_argument("--mode", default="실전", help="--bundle: 실전|연습")
    a = ap.parse_args()
    d = (L.ROOT / a.dir) if not Path(a.dir).is_absolute() else Path(a.dir)
    if a.cmd == "due":
        rows = due_bundle(Path(a.bundle), a.team, Path(a.reviews) if a.reviews else review_dir(d), a.mode) if a.bundle else due(d)
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                print(f"{r['pick_id']}  {r.get('nickname') or r.get('agent') or r['agent_id']}  {r['market']} {r['name']}  {r['score']:+.2f}%  → {r['path']}")
            print(f"복기 필요 {len(rows)}건")
        return
    if a.cmd == "summary":
        if not a.week:
            sys.exit("--week 필요 (예: 2026-W46)")
        s = summary(d, a.week, a.weeks, Path(a.reviews) if a.reviews else None, Path(a.bundle) if a.bundle else None,
                    a.team if a.bundle else None, a.mode if a.bundle else None)
        try:
            roster = L.load_roster(d)
        except Exception:
            roster = {}
        names = {x["id"]: f"{x.get('nickname') or x['id']} ({x['id']})" for x in roster.get(TEAM, []) + roster.get("bench", [])}
        md = summary_md(s, names)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(md + "\n", encoding="utf-8")
        print(json.dumps(s, ensure_ascii=False, indent=1) if a.json else md)
        return
    if a.cmd == "list":
        rows = listing(d, a.week)
        print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else "\n".join(f"{r['round_date']} {r['file']}  {r['verdict']}" for r in rows) or "없음")
        return
    bad = 0
    for p in a.paths:
        errs = check(Path(p))
        for e in errs:
            print(f"{p}: {e}")
        bad += bool(errs)
        if not errs:
            print(f"{p}: 통과")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
