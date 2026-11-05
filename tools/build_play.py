#!/usr/bin/env python3
"""지인 공개용 게임 화면(play.html)을 만든다.

  python3 tools/build_play.py <출력 폴더>      # play.html 과 data/table.js

- 화면: 운영 현황판 페이지(docs/dashboard/operator-dashboard-page.html)의 "테이블" 탭과 캐릭터 프로필만 가져온다.
  운영 탭·영수증 세부·제공처 상태·회사 로고는 넣지 않는다.
- 데이터: 두 팀 공유용 결과 묶음(dashboard_data.bundle)과 라운드 달력만 싣는다.
  bundle()이 마감 전 종목·원 가격이 섞이면 실패하므로 같은 안전장치를 그대로 쓴다.
- 지인 공개(deploy_enabled)는 데이터 제공처 확인 뒤에 켠다(docs/data-provider-research.md 8장).
"""
import json, re, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league as L  # noqa: E402
import dashboard_data as D  # noqa: E402

PAGE = L.ROOT / "docs" / "dashboard" / "operator-dashboard-page.html"

TOKENS = """:root{--color-fg:#1f1e1d;--color-fg-muted:#6b6862;--color-bg:#faf9f5;--color-panel:#ffffff;--color-border-line:#e6e3da;--color-ok:#2f7d4f;--color-warn:#a8650b;--color-bad:#b3261e;
--font-anthropic-sans:system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;--font-anthropic-serif:Georgia,"Noto Serif KR",serif;
--cds-font-size-caption:12px;--cds-font-size-body:14px;--cds-font-size-heading:17px;--cds-font-size-title:26px;--cds-font-weight-medium:600;
--cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:12px;--cds-gap-lg:20px;--cds-gap-xl:28px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:16px;--cds-radius:6px;
--cds-shadow-popover:0 4px 16px rgba(0,0,0,.25);--cds-dur-slow:.3s}
html,body{margin:0;background:#070f1f;color:#f4ecd6;font-family:var(--font-anthropic-sans);font-size:14px}
.play{max-width:1280px;margin:0 auto;padding:16px}
.play .top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin:4px 4px 12px}
.play .top h1{font-family:var(--font-anthropic-serif);font-weight:400;font-size:24px;margin:0;color:#f4d27a;letter-spacing:.04em}
.play .top small{color:#b9c7dd}
.play .lg .card{background:var(--color-panel);color:var(--color-fg);border-radius:12px;padding:16px}
.play .lg .note{color:var(--color-fg-muted)}
.play .rules{margin-top:16px;background:#0b1426;border:1px solid #2a3f66;border-radius:12px;padding:12px 16px;color:#d9e3f2;line-height:1.6}
.play .rules summary{cursor:pointer;color:#f4d27a;font-weight:600}
.play .rules ul{margin:8px 0 0;padding-left:20px}
.play footer{margin:16px 4px;font-size:12px;color:#93a3bd;line-height:1.6}
.play .lg .tablewrap{scrollbar-color:#4f74ad #0b1426}
"""

RUNTIME = """<script>
const DATA = window.TABLE || {};
const calcs = {}, draws = {}, onDatas = []; let params = {};
window.dash = {
  colors: ['#c96442', '#3b6fb6', '#7a8b3a', '#8a5cb8', '#c49a2c', '#2f8f8a', '#b5487a', '#6b6862'],
  data(id) {
    if (calcs[id]) { const c = calcs[id]; const ins = c.inputs.map((i) => dash.data(i)); if (ins.some((x) => x.status !== 'ok')) return {status: 'missing', data: []}; return {status: 'ok', data: c.fn(...ins.map((x) => x.data))}; }
    return Array.isArray(DATA[id]) ? {status: 'ok', data: DATA[id]} : {status: 'missing', data: []};
  },
  calc(id, o) { calcs[id] = o; }, loader() {},
  draw(name, fn) { draws[name] = fn; },
  onData(fn) { onDatas.push(fn); },
  params() { return params; },
  setParams(p) { params = {...params, ...p}; for (const k in p) if (p[k] == null) delete params[k]; drawAll(); },
  resetParams() { params = {}; drawAll(); }, setLink() {}, refresh() {},
};
function drawAll() {
  onDatas.forEach((f) => f());
  for (const [n, fn] of Object.entries(draws)) document.querySelectorAll(`[data-draw="${n}"]`).forEach((el) => {
    if (el.closest('[hidden]')) return;
    try { (typeof fn === 'function' ? fn : (x) => { const m = fn.mount(x); fn.update(x, m); })(el); } catch (e) { console.error(n, e); }
  });
}
</script>"""


def _between(text: str, start: str, end: str, include_end=False) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b + (len(end) if include_end else 0)]


def page_html(generated_at: str) -> str:
    src = PAGE.read_text()
    style = _between(src, "<style>", "</style>", include_end=True)
    defs = _between(src, '<svg width="0" height="0"', "</defs></svg>", include_end=True)
    profile = _between(src, '<section class="card profile"', "</section>", include_end=True)
    cards = _between(src, '<section class="page board" id="cards"', "  <!-- 팀 대결 -->")
    cards = cards.replace(' data-page="cards" hidden>', ' data-page="cards">', 1)
    cards = re.sub(r'\s*<div class="hud">.*?</div>\n', "\n", cards, count=1, flags=re.S)
    script = _between(src, "<script>", "</script>", include_end=True)
    if "회사 로고" in cards:
        raise RuntimeError("공개 화면에 로고 안내가 섞임")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 투자 리그 테이블</title>
<meta name="description" content="두 AI 팀의 모의 종목 예측 리그. 돈이나 베팅은 없습니다.">
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<style>{TOKENS}</style>
{style}
</head><body>
<div class="play">
  <div class="top"><h1>AI 투자 리그</h1><small>갱신 {generated_at[:16].replace('T', ' ')} KST</small></div>
  <div class="lg">
  {defs}
  {profile}
  {cards}
  </div>
  <details class="rules"><summary>규칙 한눈에 보기</summary><ul>
    <li>두 팀(Claude 팀·슈슈 팀) 에이전트가 평일마다 한국·미국 종목을 1개씩 고릅니다. 마감은 08:30 KST입니다.</li>
    <li>점수는 그날 종가 기준 하루 수익률(배당 포함, %)이고 다음 날 10:30에 채점합니다. 원 가격은 보여 주지 않습니다.</li>
    <li>마감이 지난 라운드의 종목만 공개합니다. 한쪽 시장이 쉬는 날은 남은 시장만, 둘 다 쉬면 라운드가 없습니다.</li>
    <li>매주 두 팀 10명을 한 줄로 세워 꼴등 1명이 탈락하고 대기 후보가 들어옵니다. 채점이 모자라면 탈락을 미룹니다.</li>
    <li>캐릭터는 창작 캐릭터이며, 에이전트는 투자 스타일 이름만 씁니다. 실존 인물의 추천이 아닙니다.</li>
  </ul></details>
  <footer>
    모의 예측 게임입니다. 돈이나 베팅은 없고, 실제 수익률·투자 권유가 아닙니다.<br>
    데이터 출처: 한국 종가·지수 — <b>한국거래소 통계정보</b>(KRX Open API)를 사용한 결과 · 미국 종가·배당 — Tiingo · 한국 공시 — 금융감독원 OpenDART. 원 가격은 표시하지 않고 계산된 점수만 표시합니다.
  </footer>
</div>
<script src="data/table.js"></script>
{RUNTIME}
{script}
<script>drawAll();</script>
</body></html>
"""


def table_data(now: datetime | None = None) -> dict:
    now = now or datetime.now(L.KST)
    b = D.bundle(now)                                   # 마감 전 종목·원 가격이 섞이면 여기서 실패
    out = {k: b[k] for k in D.BUNDLE_KEYS}
    out["calendar"] = D.calendar(now)
    out["generated_at"] = b["generated_at"]
    return out


def build(out: Path, now: datetime | None = None) -> list[Path]:
    data = table_data(now)
    (out / "data").mkdir(parents=True, exist_ok=True)
    js = out / "data" / "table.js"
    js.write_text("window.TABLE = " + json.dumps(data, ensure_ascii=False) + ";\n")
    html = out / "play.html"
    html.write_text(page_html(data["generated_at"]))
    return [html, js]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for p in build(Path(sys.argv[1])):
        print(p)
