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
- 원 가격(₩·$·원·달러 금액)은 쓰지 않는다. 수익률(%)·지수 대비(%p)만 쓴다.
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
# 원 가격·금액 검사(경험칙). 세 가지만 막는다.
#  1) 통화가 붙은 금액: 1,393,000원에서 · 1,393,000 원 · 45달러로 · 245불에 · 5만 원 · $45 · ₩1000 · 13만~14만원
#  2) 가격 단서(종가·주가·목표가·매수가·단가 …) 뒤의 '가격 꼴 숫자'(쉼표·세 자리 이상·소수·천/만 단위)인데 그 뒤가 가격다울 때
#     (끝·문장부호·이었·으로·까지·에서·선·원·대로·아래 …). 단서와 숫자 사이에 조사·기호(**·|·=·→)·괄호 날짜·짧은 낱말 1~3개가 껴도 본다.
#  3) 가격 꼴 숫자 + '…에 마감·출발·시작·끝났다·거래됐다'
# 막지 않는 것: 작은 정수(3상·5대 악재·2시), 물량·셈(120척·10만 장·1,000대가), 이름 속 숫자(러셀 2000·보잉 737·HBM4), 연도(2026 가이던스),
# 날짜·시각(11/4·15:30), %·배수, 종목코드(000660.KS), 베타·상관계수 같은 지표.
_G = r"(?<![\d/:.\-~A-Za-z&])"                                     # 날짜(11/4)·시각(15:30)·범위(2~3)·이름(S&P500·HBM4)의 뒷숫자가 아님
_GU = r"(?<![\d/:.\-A-Za-z&])"                                    # 통화가 붙은 금액은 범위 끝(13만~14만원)도 잡는다
_N = r"(?>\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?+(?:\s*(?:천|만|억|조)(?:\s*\d++)?+){0,4}+"            # 아무 숫자(원자 묶음: 되돌아가지 않음)
_NP = (r"(?!0\.\d)(?!0\d{5}(?!\d))(?!\d{6}(?:\.K[SQ](?![A-Za-z])|\s*\)))(?!(?:19|20)\d{2}(?!\d|[,.]\d))(?>\d{1,3}(?:,\d{3})+|\d{3,}|\d+\.\d+|\d+(?=\s*(?:천|만|억|조)))"  # 가격 꼴 숫자(6자리 0시작 = 종목코드 제외)
       r"(?:\.\d+)?+(?:\s*(?:천|만|억|조)(?:\s*\d++)?+){0,4}+")
_RIGHT = (r"(?![./:\-]\d)(?=대로|대(?=\s*(?:$|[.,;)]|초반|중반|후반|로|에|까지|에서|을|를|이었|였))"
          r"|\s*(?:$|[.,;()|\]~→*`≈…]|->|이었|였|이다|이며|이고|이던|이라|으로|로|까지|에서|에|을|를|과|와|은|는|도|의|이(?![가-힣])|가(?![가-힣])|선|원|달러)"
          r"|\s+(?:/|부근|근처|근방|안팎|수준|언저리|정도|전후|아래|밑|위|이하|이상|초반|중반|후반|선|대로|대에|대까지|대(?=\s*(?:$|[(.,;)]))|대비|기준|이탈|돌파|붕괴|회복|기록"
          r"|지지|저항|터치|도달|마감|출발|하회|상회|하락|상승|vs|주변|내외|인근|구간|레벨|박스권|라인|사이)|인\s+상태|쯤|보다|부터|마저|조차|일\s*때)")
# 중간 낱말이 낀 갈래용 좁은 뒤 문맥: 맨 조사(은·는·의·과·와·을·를)와 띄어 쓴 '대에·대로'는 빼서 모델 번호·물량(보잉 737의, 35만 대에)을 살린다
_RIGHT_F = (r"(?![./:\-]\d)(?=대로|대(?=\s*(?:$|[.,;)]))|\s*(?:$|[.,;()|\]~→*`≈…]|->|이었|였|이다|이며|이고|이던|이라|으로|로|까지|에서|에|선|원|달러)"
            r"|\s+(?:/|부근|근처|근방|안팎|수준|언저리|정도|전후|아래|밑|이하|선|대비|기준|이탈|돌파|붕괴|회복|기록|하회|상회|vs|주변|내외|인근|구간|레벨|박스권|라인|사이)|쯤|보다|부터|일\s*때)")
_CUE = (r"(?:종가|(?:(?<![가-힣])|(?<=[최신]))(?:시가|고가|저가)|(?<![가-힣])주가|시초가|현재가|최고가|최저가|고점|저점|주당|가격대?|시장가|목표\s*주?가"
        r"|평균\s*단가|지지선|저항선|(?<![\d.])\d{1,3}일선|(?<![가-힣])(?<!외국인 )(?<!기관 )(?<!개인 )(?<!연기금 )(?:매수가|매입가|매도가|진입가|체결가|기준가|손절가|적정주가|적정가|평단|단가|마감가|공모가))")
_DATE = r"(?:(?:19|20)\d{2}년(?:\s*\d{1,2}월(?:\s*\d{1,2}일)?)?|\d{1,2}/\d{1,2}|\d{1,2}월\s*\d{1,2}일|\d{4}-\d{2}-\d{2})"
_PART = (r"(?:\s*(?:(?:이)?라(?:고|는|던)?(?=\s)|이었던|이던|였던|인(?![가-힣])|" + _DATE + r"(?:에는|에|엔|의)?|는|은|가|이|도|을|를|으로|로|의|기준|약|대략|한때|장중|장\s*초반|이날|다음\s*날|:|：|\||=|＝|\*|`|—|–|-(?=\s)|→|->|~|≈|≒|\((?![\s\d,.]+\))(?![^()\n]*?(?<![\d/:.\-])(?:\d{1,3},\d{3}|(?!(?:19|20)\d{2}년)\d{3,}|\d+\.\d+|\d+\s*[천만억조]))[^()\n]{1,12}\)|\(\s*" + _DATE
         + r"\s*\)|\())*+\s*")
_FILL = (r"(?:\s+(?:(?!코스피|코스닥|나스닥|다우|러셀|포춘|닛케이|지수|환율|금리|거래량|거래대금|관객|가입자|계좌|판매|수주|누적|앨범|차량|객실|증설|미분양"
         r"|물량|매출|규모|베타|상관|계수|변동성|회전율|비율|배수|순위|점수|확률|가능성|위험|쪽|탄력성|민감도|이격도|기여도|신뢰도|확신도|괴리도|크기|속도|대비|종목|품목|기업|업체|회사|구독|이용|사용|이탈|고객|주주|소액주주|출하|재고|잔고|대차|공매도|해지|조회|팔로워|표본|기간|선행|후행|Forward"
         r"|[가-힣]{0,6}(?:자|량|고|수|객)(?:는|은|가|이|도|를|을)?(?![가-힣]))[가-힣]{1,7}|(?!(?:S&P|KOSPI|KOSDAQ|NASDAQ|Nasdaq|Russell|FTSE|Nikkei|Stoxx|STOXX|KRX|Dow|MSCI|DXY|US10Y|Beta|Sharpe)(?![A-Za-z]))(?!(?:Forward\s+)?(?:PER|PBR|PSR|PCR|PEG|EV|EPS|BPS|ROE|ROA|ROIC|RSI|MACD|ATR|VIX|SOX)(?![A-Za-z]))[A-Za-z][A-Za-z0-9&.]{0,15}[가-힣]{0,4}"
         + r"|\d{1,2}월(?:에는|에|엔|의)?|\d{1,2}일(?:에는|에|엔|의)?|" + _DATE + r"(?:에는|에|엔|의)?|\d{1,2}(?:주일?|개월|거래일)|[+−-]?\d+(?:\.\d+)?%p?)){1,3}")
_NPS = r"(?!0\.\d)(?!\d{6}(?:\.K[SQ](?![A-Za-z])|\s*\)))(?<![\d.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+(?:\.\d+)?\s*만(?:\s*\d+\s*천|\s*\d+(?:,\d{3})*)?)(?![\d.,])(?!\s*(?:만|억|조|천))"
_DIR = r"(?:(?:상승|하락|강세|약세|보합|급등|급락)\s*)"
MONEY = re.compile(
    r"[$₩￦]\s*\d|" + _GU + _N + r"\s*\$"
    + r"|" + _GU + r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:(?:\s*(?:천|만|억|조))+\s*원|\s*원)(?![인칙화자유래전천본격리론소형점문장]|가(?!량|까이))"
    + r"|" + _GU + _N + r"\s*(?:달러|USD|KRW)(?![A-Za-z])|" + _GU + _N + r"불(?:(?![가-힣])|(?=에|로|으로|선|대|을|까지|도|이(?![가-힣])))|(?:USD|KRW)\s*\d"
    + r"|" + _CUE + _PART + _NP + _RIGHT                                     # 단서 바로 뒤(조사·기호만 낌)
    + r"|" + _CUE + r"(?:(?:이)?라(?:고|는|던)?|이었던|이던|였던|인|으로|로|는|은|가|이|도|를|을)?" + _FILL + r"(?:\s+|\s*[(:：]\s*)" + r"(?![\d,.]+\s*(?:억|조))" + _NP + _RIGHT_F
    + r"|" + _CUE + r"(?:(?:이)?라(?:고|는|던)?|이었던|이던|였던|인|으로|로|는|은|가|이|도|를|을)?" + _FILL + r"(?:\s+|\s*[(:：]\s*)" + r"(?![\d,.]+\s*(?:억|조))" + _NPS + r"(?=\s*(?:을|를|이(?![가-힣])|가(?![가-힣])))"     # 단서와 숫자 사이에 짧은 낱말 1~3개
    + r"|" + _G + _N + r"\**(?:\s*\([^()\n]{1,12}\))?(?:\s*선?\s*(?:에서|에|으로|로)\s*(?:" + _DIR + r"?(?:장\s*)?마감|" + _DIR + r"출발|(?:거래|장)을?를?\s*(?:마쳤|마치|마감|끝냈|끝))|\s+마감)"
    + r"|(?<![\d/:.\-~A-Za-z&가-힣])(?:\d{1,3}(?:,\d{3})+|\d{3,})(?:\.\d+)?\**\s*(?:에|으로|로)\s*(?:출발|시작|끝났|끝냈|끝마|거래됐|거래되었|마쳤|마무리|(?:거래|장)을?를?\s*(?:시작|종료)|종료)"
    + r"|" + _G + _NP + r"(?<![억조])(?![\d.,]|\s*(?:%|억|조))(?:\s*\(\s*" + _DATE + r"\s*\))?\s*에서\s*(?:[가-힣]{1,4}\s*만에\s*)?(?:" + _DATE + r"\s+)?" + _NP
    + r"(?<![억조])(?![\d.,]|\s*(?:%|억|조))(?:\s*\(\s*" + _DATE + r"\s*\))?\s*(?:(?:으로|로|까지)\s*(?:[+−-]?\d+(?:\.\d+)?%p?\s*)?(?:내렸|올랐|빠졌|밀렸|떨어졌|뛰었|급등|급락|하락|상승|반등|미끄러|내려앉|주저앉|추락|후퇴|올라섰|됐|되었)|(?:이|가)\s*(?:됐|되었))"
    + r"|" + _G + _NP + r"(?<![억조])(?![\d.,]|\s*(?:%|억|조))\**\s*(?:→|->)\s*\**(?:" + _DATE + r"\s+)?" + _NP + r"(?<![억조])(?!\d|[.,]\d|\s*(?:%|억|조))"
    + r"|" + _G + _NP + r"(?<![천만억조])(?![\d.,]|\s*(?:%|억|조|만|천))\s*(?:고점|저점|종가|최고가|최저가)", re.M)


# 경험칙 뒤 거름: 문맥상 가격이 아닌 매치(셈·지표 주어의 'A에서 B로', 품목 가격, 주당 지표)는 버리고 그 다음부터 다시 찾는다
_MOVE = re.compile(r"에서|→|->")
_SUBJ = re.compile(r"량|(?<![가-힣])수(?![가-힣])|자\s*수|재고|판매|출하|인도|가입자|주문|수주|매출|이익|부채|(?<![가-힣])배당금?|베타|RSI|비중|지분율|(?<![가-힣A-Za-z0-9&])[금은](?=\s*(?:선물|값|가격))|(?<![가-힣A-Za-z0-9&])금값|천연가스|팔라듐|백금|이익률|마진|(?:원|달러|엔|유로|위안)\s*[·/]\s*(?:원|달러|엔|유로|위안)|\d+년물|근월물|현물가|고정가|계약가|브렌트유?|두바이유|원유|구리|수익률|실업률|가동률|상관|변동성|배수|인원|직원|점수|순위|건수|환율|금리|지수|코스피|코스닥|나스닥"
                   r"|(?<![A-Za-z])(?:EPS|DPS|BPS|PER|PBR|ROE|SOX|VIX|KOSPI|S&P|DXY|ASP|WTI|CPI|PPI|PCE|PMI|GDP|LME|EBITDA)(?![A-Za-z])|컨센서스|인덱스|국채|(?<![가-힣A-Za-z])유가|브렌트")
_COMMOD = re.compile(r"(?:D램|DRAM|DDR\d|LPDDR\d?|낸드|NAND|플래시|메모리|HBM\w*|칩|구리|(?<![가-힣A-Za-z0-9&])금|(?<![가-힣A-Za-z0-9&])은|니켈|리튬|코발트|알루미늄|철광석|원자재|현물|고정거래|계약|판매|제품|평균판매|ASP|원유|WTI|브렌트유?|두바이유|(?<![가-힣A-Za-z])유가|(?<![가-힣A-Za-z])가스|(?<![가-힣A-Za-z])전력|운임|선물)(?:\s*\([^)\n]{0,20}\)|\s+(?:현물|고정거래|계약|선물|근월물|평균|범용|서버용|모바일|PC용|\d+\s*[GT]b|\d+단|DDR\d\w*|LPDDR\d\w*|플래시)){0,3}\s*$")
_PER_UNIT = re.compile(r"(?:톤|온스|배럴|kg|파운드|개|GB|Gb|MWh|kWh)\s*당")
_CUE_IN = re.compile(_CUE)
_SENT_END = re.compile(r"[!?\n。]|\.(?!\d)")
# 지표·품목 이름 바로 뒤의 단서(WTI 종가·환율 고점·금 선물 종가·EPS 컨센서스 고점)는 주가가 아님
_IND_PRE = re.compile(r"(?:" + _SUBJ.pattern + r"|" + _COMMOD.pattern[:-4] + r")(?:\s*(?:선물|근월물|현물|컨센서스|추정치|금리))?\s*(?:\([^)\n]*\))?(?:\s*(?:은|는|이|가|도|의))?(?:\s*(?:장중|52주|한때))?\s*$")
_CUE_START = re.compile(r"(?:종가|고점|저점|시가|고가|저가|최고가|최저가|가격|단가)")
_CLOSE_VERB = re.compile(r"마감|마쳤|마치|끝냈|끝났|출발|시작|종료|거래됐|거래되었|마무리")
_COMMOD_PRICE = re.compile(_COMMOD.pattern[:-4] + r"\s*(?:가격|단가)")
# 이동 매치는 셈·지표 주어나 품목 가격이 숫자 바로 앞에 붙어 있을 때만 버린다('배당 기대에 1,264,000에서…'처럼 원인을 말하는 낱말은 거르지 않음)
_ATTACHED = re.compile(r"(?:" + _SUBJ.pattern + r"|" + _COMMOD_PRICE.pattern + r")(?:\s*(?:선물|근월물|현물|\d+(?:개월|년)물|\d+단))?(?:\s*(?:추정치|전망치|예상치|컨센서스|가이던스|전망|추정|예상|단가|가격|종가|고점|저점))?(?:\s*(?:하향|상향|조정))?\s*(?:\([^)]*\))?\s*(?:은|는|이|가|도|의)?\s*(?:\([^)]*\))?"
                       r"(?:\s*(?:전년비|전월비|YoY|QoQ|전년|지난해|작년|같은|동기|분기|\d분기|연간|월간|전월|전분기|대비))*(?:\s*(?:톤|온스|배럴|kg|파운드|개|GB|Gb|MWh|kWh)\s*당)?(?:\s*(?:" + _DATE + r"|[가-힣]{1,4}\s*만에|장중|한때))*\s*\(?\s*(?:[\d,.]+\s*(?:→|->|에서|(?:으로|로)\s*(?:출발|시작)해)\s*(?:" + _DATE + r"\s*)?)*[\d,.]*$")
_CO_AMT = re.compile(r"\d(?:\s*[천만])?\s*[억조](?:\s*[\d,.]*\s*[천만억])*\s*(?:원|달러|USD(?![A-Za-z]))")


def money_hit(t: str):
    """MONEY 매치 가운데 문맥 거름을 통과한 첫 매치(없으면 None)."""
    pos = 0
    while True:
        m = MONEY.search(t, pos)
        if not m:
            return None
        g = m.group(0)
        w = max(0, m.start() - 120)
        ls = max([w] + [x.end() for x in _SENT_END.finditer(t, w, m.start())])
        before = t[max(ls, m.start() - 14):m.start()]
        skip = False
        if not _CUE_IN.search(g) and (_MOVE.search(g) or _CLOSE_VERB.search(g)) and _ATTACHED.search(t[max(ls, m.start() - 60):m.start()]):
            skip = True
        elif re.fullmatch(r"[\d,.]+\s*(?:고점|저점|종가|최고가|최저가)", g) and _ATTACHED.search(t[max(ls, m.start() - 60):m.start()]):
            skip = True
        elif _CUE_START.match(g) and _IND_PRE.search(t[max(ls, m.start() - 30):m.start()]):
            skip = True
        elif g.startswith(("가격", "단가")) and (_COMMOD.search(t[max(ls, m.start() - 30):m.start()]) or _PER_UNIT.search(g)):
            skip = True
        elif not _CUE_IN.search(g) and _CO_AMT.search(g):
            skip = True   # 회사 금액(억·조 + 원·달러)은 허용(운영자 결정 2026-11-08). 주당 금액·종가와 원 단위 가격(126만 원)은 계속 막는다
        elif re.search(r"원|달러|\$|USD", g) and not _MOVE.search(g) and re.search(r"배당|DPS", t[max(ls, m.start() - 20):m.start()] + g[:6]) \
                and not re.search(r"종가|주가|시가|고가|저가|목표|가격|단가|고점|저점", g):
            skip = True   # 주당 배당금(원·달러)은 가격이 아님
        elif g.startswith("주당") and (re.match(r"주당\s*(?:배당|순이익|순자산|이익|현금흐름|매출)", g) or re.search(r"배당", t[max(ls, m.start() - 12):m.start()])):
            skip = True
        if not skip:
            return m
        pos = m.start() + 1


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


_CUE_HEAD = re.compile(r"(?<![A-Za-z])(?:Close|Adj\.?\s*Close|Price)(?![A-Za-z])|고점|저점|지지선|저항선|종가|주가|시가|고가|저가|가격|단가|매수가|매도가|목표\s*주?가|평단|기준가|현재가")
_NP_RE = re.compile(r"(?<![\d.,%+\-−▲▼△▽A-Za-z])(?<![A-Za-z&]\s)(?<!나스닥 )(?<!코스피 )(?<!코스닥 )(?<!러셀 )(?<!다우 )(?<!보잉 )(?<!에어버스 )" + _NP + r"(?![\d.,]|\s*%|\s*(?!원|달러)[가-힣A-Za-z])")
# 표 머리글: '/ · ( [ → , 와 및'으로 나눈 조각 가운데 '가격 단서만 있고 지표·셈·기간·비율 낱말이 없는' 조각이 하나라도 있으면 가격 열.
# 단, 머리글에 단위 괄호((%)·(일)·(거래일)·(조원)…)가 붙으면 그 열은 지표·셈 열로 본다.
_UNIT_PAREN = r"\(\s*(?:%p?|배|일|회|건|주|bp|조\s*원?|억\s*원?|거래일|개월|년|명|개)\s*\)"
_HEAD_SKIP = re.compile(r"베타|민감도|탄력성|기여도|RSI|이격도|샤프|상관|회전율|가중치|모멘텀|ATR|MACD|대비|수\s*$|건수|횟수|개수|일수|표본|기간|거래일|이동평균"
                        r"|%|률|율|비율|(?<![A-Za-z])(?:PER|PBR)(?![A-Za-z])|총액|시가총액|(?<![가-힣])배(?![가-힣])|배수|순자산"
                        r"|반응|흐름|영향|요인|기대|관계|변동성|순위|경쟁력|결정력|거래량|거래대금|순매수|순매도")
# 행 이름이 지표면 그 행은 가격 행이 아님(단위 괄호면 건너뜀, 종목코드·티커·요일 괄호는 지우고 본다, 낱말 속 글자(GE Vernova의 EV)는 보지 않음)
_ROW_SKIP = re.compile(r"(?<![A-Za-z])(?:PER|PBR|PSR|PCR|PEG|PFCR|EV|EPS|BPS|ROE|ROA|ROIC|RSI|MACD|ATR)(?![A-Za-z])|시총|시가총액|샤프|토빈|베타|상관|변동성|이격도"
                       r"|민감도|탄력성|기여도|회전율|가중치|모멘텀|비율|(?<=[가-힣])[률율]|배수|점수|확률|일수|주수|지분|마진|비중|거래량|거래대금|순매수|순매도|%|(?<![A-Za-z])P/?[EBS](?![A-Za-z])|[Yy]ield")
_ROW_TIME = re.compile(r"기준|평가|직전|시작|끝|마지막|당일|뒤|후|전|D\s*[+-]")


def _price_col(h: str) -> bool:
    if re.search(_UNIT_PAREN, h) or _PER_UNIT.search(h) or _COMMOD_PRICE.search(h):
        return False   # 단위 괄호 열, 품목 가격 열(구리 가격(톤당), D램 가격)은 주가 열이 아님
    cs = list(_CUE_HEAD.finditer(h))
    if len(cs) == 1 and _IND_PRE.search(h[:cs[0].start()]):
        return False   # '엔·달러 종가'처럼 지표 이름이 앞에 붙은 단서 하나뿐인 열
    for frag in re.split(r"[/·(\[\]→,)]|\s+(?:와|및)\s+", h):
        c = _CUE_HEAD.search(frag)
        if c and not _HEAD_SKIP.search(frag) and not _IND_PRE.search(frag[:c.start()]):   # 'WTI 종가'·'10년물 종가'는 지표 열
            return True
    return False


def _skip_row(label: str) -> bool:
    if re.search(_UNIT_PAREN, label):
        return True
    lb = re.sub(r"\([^)]*\)", "", label)
    if _ROW_SKIP.search(lb) or _IND_PRE.search(lb.strip()) or _COMMOD_PRICE.search(lb):   # 행 이름 자체가 지표·품목(WTI·금 선물·D램 현물가·10년물·DPS)
        return True
    return bool(re.search(r"거래일|기간", lb)) and not _ROW_TIME.search(lb)   # '기준 거래일'·'평가 기간 끝'은 시점 행이라 본다


_TBL_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")


def _table_prices(t: str) -> str | None:
    """세로형 마크다운 표: 가격 열(_price_col) 아래의 가격 꼴 숫자를 원 가격으로 본다. 지표 행(_skip_row)과 억·조 금액 칸은 건너뛴다."""
    rows = [l for l in t.splitlines()]
    i = 0
    while i < len(rows):
        if "|" in rows[i] and i + 1 < len(rows) and _TBL_SEP.match(rows[i + 1]):     # 맨 앞 '|'가 없는 GFM 표도
            lead = rows[i].lstrip().startswith("|")
            head = [c.strip() for c in rows[i].strip().strip("|").split("|")]
            cols = [k for k, c in enumerate(head) if _price_col(c)]
            j = i + 2
            while j < len(rows) and (rows[j].lstrip().startswith("|") if lead else ("|" in rows[j] and rows[j].strip())):
                cells = [c.strip() for c in rows[j].strip().strip("|").split("|")]
                if cells and _skip_row(cells[0]):
                    j += 1
                    continue
                for k in cols:
                    if k < len(cells) and not re.search(r"\d\s*(?:억|조)", cells[k]) and _NP_RE.search(cells[k]):
                        return f"{head[k]}: {cells[k]}"
                j += 1
            i = j
        else:
            i += 1
    return None


def _known_closes(path: Path) -> list[str]:
    """복기 파일 경로(<리그>/reviews/losses/<라운드>/<에이전트>-<시장>.md)로 그 종목의 원장 종가를 찾아, 본문에 나올 수 있는 표기들을 돌려준다.
    경험칙(MONEY)과 별도로, 실제 기록된 원 가격은 어떤 문장 꼴로 써도 막기 위한 정확한 안전장치다(원장이 없으면 빈 목록)."""
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
    tb = re.sub(r"^- 종목:.*$", "", re.sub(r"https?://\S+", "", t), flags=re.M)   # 머리글의 종목코드·출처 URL 숫자는 대조하지 않음
    for c in _known_closes(path):
        unit = r"%|배|만|억|조|주(?![변가당요간])|개|명|척|건|곳|거래일" + ("" if "," in c else r"|일|대|년")
        if re.search(r"(?<![\d.,\-/:])" + re.escape(c) + r"(?![\d]|[.,]\d|[\-/:T]\d|\s*(?:" + unit + r"))", tb):
            errs.append(f"원장에 기록된 이 종목의 종가와 같은 숫자 {c!r} — 원 가격 금지")
            break
    te = _table_prices(t)
    if te:
        errs.append(f"표의 가격 칸에 원 가격 금지: {te!r}")
    if not (600 <= len(t) <= 6000):
        errs.append(f"길이 {len(t)}자 — 600~6000자")
    mm = money_hit(t[:6000]) if len(t) <= 6000 else None
    if mm:
        errs.append(f"원 가격·금액 표현 금지: {mm.group(0)!r} (수익률 %·지수 대비 %p만)")
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
_FX_ALWAYS = r"(?:항상|영구히?|절대|무조건|앞으로)"
_FX_TARGET = r"[가-힣A-Za-z&]{2,12}(?:은|는|을|를|도)(?![가-힣])|종목|업종|섹터|티커|테마|[가-힣]{1,6}(?<!매)주(?![가-힣])|[가-힣]{1,6}주(?=[는은를을도만])"
_FX_VERB = r"(?:제외|빼|뺀|뺄|넣|편입|사지\s*않|안\s*산|매수하지\s*않|피한|피하)"
_FIXED_RULE = re.compile(_FX_ALWAYS + r"[^.\n]{0,25}?(?P<t1>" + _FX_TARGET + r")[^.\n]{0,20}?" + _FX_VERB
                         + r"|(?P<t2>" + _FX_TARGET + r")[^.\n]{0,20}?" + _FX_ALWAYS + r"[^.\n]{0,20}?" + _FX_VERB)
_HABIT = re.compile(r"원인|신호|정보|공시|뉴스|요소|카드|선택지|판단|계산|비교|흐름|수급|숫자|이유|사례|이벤트|촉매|낙폭|증폭|베타|점검|체크리스트|항목|근거|논리|기준|확인|가정|일정|지표|데이터|자료|위험|변수|시나리오|(?<!무)조건|요인|비중|가중|후보군에서\s*빼지")


def _is_fixed(text: str, x) -> bool:
    """대상 명사구(조사 앞 낱말)만 보고 판단 습관(점검·근거·흐름…)이면 규칙이 아님. '촉매가 없는 종목'처럼 조건이 붙은 대상도 습관."""
    k = "t1" if x.group("t1") else "t2"
    tgt, st = x.group(k), x.start(k)
    pre = text[max(0, st - 12):st]
    if re.search(r"(?:항목|목록|체크리스트|점검)(?:에|으로)\s", x.group(0)):
        return False
    return not _HABIT.search(tgt) and not re.search(r"(?:없는|있는|낮은|높은|약한|강한|큰|작은|못한|않은|고른|본|산|인)\s*$", pre)


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
            invalid.append({"path": str(f), "errors": errs[:3]})
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
