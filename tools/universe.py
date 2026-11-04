#!/usr/bin/env python3
"""대상 종목 목록(universe) 관리.

- 미국: S&P 500 은 Wikipedia(CC BY-SA 4.0) 표, NASDAQ-100 은 Nasdaq 공개 목록 JSON(비공식)에서 가져온다. 리그 내부 자격 검증 전용이며
  화면에 목록을 재게시하지 않는다. 문서 판(revision) 번호를 함께 기록한다.
- 한국: KOSPI200 + KOSDAQ150 은 KRX 정보데이터시스템 파일(로그인 필요)을 운영자가 내려받아 가져온다:
    python3 tools/universe.py import-kr --kospi200 FILE.csv --kosdaq150 FILE.csv
  (CSV에서 '종목코드'와 '종목명' 열을 찾는다. 인코딩은 UTF-8 또는 CP949)
- 저장: league/universe/<적용일>.json (판별 기록) + league/universe.json (현재 판). 검증은 라운드 날짜 기준 판을 쓴다.

사용법:
  python3 tools/universe.py fetch-us [--effective 2026-11-04]
  python3 tools/universe.py import-kr --kospi200 a.csv --kosdaq150 b.csv [--effective 2026-11-04]
  python3 tools/universe.py show [--date 2026-11-10]
"""
from __future__ import annotations

import argparse, csv, io, json, re, sys, time, urllib.parse, urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UDIR = ROOT / "league" / "universe"
UA = "league-universe/0.1 (private research)"


class TableParser(HTMLParser):
    """id="constituents" 표의 행을 셀 텍스트 목록으로 모은다."""
    def __init__(self, table_id="constituents"):
        super().__init__()
        self.tid, self.depth, self.rows, self.row, self.cell, self.in_cell = table_id, 0, [], None, [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table" and (self.depth or a.get("id") == self.tid):
            self.depth += 1
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in ("td", "th") and self.row is not None:
            self.in_cell, self.cell = True, []

    def handle_endtag(self, tag):
        if tag == "table" and self.depth:
            self.depth -= 1
        elif self.depth == 1 and tag in ("td", "th") and self.in_cell:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip()); self.in_cell = False
        elif self.depth == 1 and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)


def wiki_table(page: str) -> tuple[list[list[str]], dict]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "text|revid", "format": "json", "formatversion": 2})
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == 4:
                raise
            time.sleep(5 * (i + 1))
    p = TableParser()
    p.feed(data["parse"]["text"])
    meta = {"source": f"https://en.wikipedia.org/wiki/{page}", "revid": data["parse"].get("revid"),
            "license": "CC BY-SA 4.0", "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    return p.rows, meta


def nasdaq100() -> tuple[dict, dict]:
    """Nasdaq 공개 목록 JSON (비공식). 종목 코드·이름만 쓰고 함께 오는 가격 필드는 버린다.
    (Wikipedia Nasdaq-100 문서에는 2026-11 현재 구성 종목 표가 없음)"""
    url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
        data = json.load(r)["data"]
    rows = data["data"]["rows"]
    out = {x["symbol"].replace("/", "."): re.sub(r"\s+(Common Stock|Class [A-C] .*|Ordinary Shares.*|American Depositary.*)$", "", x["companyName"]).strip()
           for x in rows if x.get("symbol")}
    return out, {"source": url, "as_of": data.get("date"), "note": "비공식 공개 JSON. 목록(코드·이름)만 사용, 가격 필드 미저장",
                 "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}


def parse_constituents(rows: list[list[str]], symbol_cols=("Symbol", "Ticker"), name_cols=("Security", "Company")) -> dict:
    head = rows[0]
    si = next(i for i, h in enumerate(head) if h in symbol_cols)
    ni = next(i for i, h in enumerate(head) if h in name_cols)
    out = {}
    for r in rows[1:]:
        if len(r) > max(si, ni) and re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", r[si]):
            out[r[si]] = r[ni]
    return out


def current() -> dict:
    p = ROOT / "league" / "universe.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save(u: dict, effective: str):
    UDIR.mkdir(parents=True, exist_ok=True)
    u["effective"] = effective
    (UDIR / f"{effective}.json").write_text(json.dumps(u, ensure_ascii=False, indent=1, sort_keys=True))
    (ROOT / "league" / "universe.json").write_text(json.dumps(u, ensure_ascii=False, indent=1, sort_keys=True))


def fetch_us(effective: str) -> dict:
    sp_rows, sp_meta = wiki_table("List_of_S&P_500_companies")
    nd, nd_meta = nasdaq100()
    sp = parse_constituents(sp_rows)
    if not (480 <= len(sp) <= 520) or not (95 <= len(nd) <= 110):
        raise SystemExit(f"구성 종목 수가 이상함: S&P {len(sp)}, NDX {len(nd)} — 표 구조 변경 의심, 저장하지 않음")
    u = current()
    u.pop("_note", None)
    u["US"] = dict(sorted({**nd, **sp}.items()))
    u.setdefault("indices", {})["US"] = {"S&P 500": sorted(sp), "NASDAQ-100": sorted(nd)}
    u.setdefault("sources", {})["US"] = {"S&P 500": sp_meta, "NASDAQ-100": nd_meta,
                                         "use": "내부 자격 검증 전용. 화면에 목록 재게시 안 함",
                                         "ticker_format": "Wikipedia 표기(예: BRK.B). 제공처별 변환은 수집기에서"}
    u["status"] = "US real / KR " + ("real" if u.get("sources", {}).get("KR") else "sample")
    save(u, effective)
    return u


def read_krx_csv(path: str) -> dict:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    code_k = next(k for k in rows[0] if "종목코드" in k or k.strip().lower() in ("code", "isu_srt_cd"))
    name_k = next(k for k in rows[0] if "종목명" in k or k.strip().lower() in ("name", "isu_abbrv"))
    return {r[code_k].strip().zfill(6): r[name_k].strip() for r in rows if r.get(code_k, "").strip()}


def import_kr(k200: str, kq150: str, effective: str) -> dict:
    a, b = read_krx_csv(k200), read_krx_csv(kq150)
    if not (190 <= len(a) <= 210) or not (140 <= len(b) <= 160):
        raise SystemExit(f"구성 종목 수가 이상함: KOSPI200 {len(a)}, KOSDAQ150 {len(b)} — 파일 확인 필요, 저장하지 않음")
    u = current()
    u.pop("_note", None)
    u["KR"] = dict(sorted({**a, **b}.items()))
    u.setdefault("indices", {})["KR"] = {"KOSPI200": sorted(a), "KOSDAQ150": sorted(b)}
    u.setdefault("sources", {})["KR"] = {"source": "KRX 정보데이터시스템 지수구성종목 (운영자 수동 다운로드)",
                                         "files": [Path(k200).name, Path(kq150).name],
                                         "imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                                         "use": "내부 자격 검증 전용. 화면에 목록 재게시 안 함"}
    u["status"] = ("US real" if u.get("sources", {}).get("US") else "US sample") + " / KR real"
    save(u, effective)
    return u


def for_date(d: date) -> dict:
    """라운드 날짜에 적용되는 판: league/universe/<적용일>.json 중 적용일 ≤ d 인 가장 최근 것."""
    if UDIR.exists():
        cands = sorted(p for p in UDIR.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem) and p.stem <= d.isoformat())
        if cands:
            return json.loads(cands[-1].read_text())
    return current()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["fetch-us", "import-kr", "show"])
    ap.add_argument("--effective", default=date.today().isoformat())
    ap.add_argument("--kospi200"); ap.add_argument("--kosdaq150")
    ap.add_argument("--date")
    a = ap.parse_args()
    if a.cmd == "fetch-us":
        u = fetch_us(a.effective)
    elif a.cmd == "import-kr":
        u = import_kr(a.kospi200, a.kosdaq150, a.effective)
    else:
        u = for_date(date.fromisoformat(a.date)) if a.date else current()
    print(json.dumps({"effective": u.get("effective"), "status": u.get("status"),
                      "counts": {m: len(u.get(m, {})) for m in ("KR", "US")},
                      "indices": {m: {k: len(v) for k, v in u.get("indices", {}).get(m, {}).items()} for m in ("KR", "US")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import urllib.error  # noqa: E402
    main()
