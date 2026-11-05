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
--cds-shadow-popover:0 4px 16px rgba(0,0,0,.25);--cds-dur-slow:.3s;
--room:#070f1f;--hud:#0b1426;--hud-line:#2a3f66;--btn-top:#2d4f82;--btn-bot:#16294a;--btn-line:#4f74ad;--gold:#f4d27a;--ink:#e8f0ff;--ink-soft:#b9c7dd;color-scheme:dark}
html,body{margin:0;height:100%;overflow:hidden;background:var(--room);color:var(--ink);font-family:var(--font-anthropic-sans);font-size:14px;overscroll-behavior:none}
/* 한 화면 게임: 위 HUD · 가운데 테이블(고정) · 아래 버튼. 메뉴는 아래에서 올라오는 창 */
.app{height:100%;display:grid;grid-template-rows:auto minmax(0,1fr) auto;box-sizing:border-box;
  padding-top:env(safe-area-inset-top,0px);padding-left:env(safe-area-inset-left,0px);padding-right:env(safe-area-inset-right,0px)}
.app .hudbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 14px;background:linear-gradient(var(--hud),rgba(11,20,38,.6));border-bottom:1px solid var(--hud-line)}
.app .hudbar h1{margin:0;font-family:var(--font-anthropic-serif);font-weight:400;font-size:19px;color:var(--gold);letter-spacing:.04em;white-space:nowrap}
.app .mini{display:grid;grid-template-columns:auto auto;column-gap:8px;align-items:baseline;text-align:right;background:#050a14;border:1px solid var(--btn-line);border-radius:10px;padding:4px 10px;font-variant-numeric:tabular-nums;cursor:pointer;font:inherit;color:inherit}
.app .mini small{grid-column:1/-1;font-size:10.5px;color:var(--ink-soft)}
.app .mini b{font-family:var(--font-anthropic-serif);font-size:19px;color:#ffd65a;font-weight:400}
.app .mini i{font-style:normal;font-size:10.5px;color:#9ff0b8}
.app .stage{min-height:0;display:flex;flex-direction:column;overflow:hidden}
.app .stage > .lg{display:block;flex:1;min-height:0;gap:0}
.app .stage .lg .felt,.app .stage .lg .felt .tablewrap,.app .stage .lg .felt .tablebox{height:100%}
.app .stage .lg .felt{padding:0;border:0;border-radius:0;box-shadow:none;background:transparent;display:block}
.app .stage .lg .felt .tablewrap{overflow:hidden;margin:0}
.app .stage .lg .felt .tablebox{min-width:0;display:flex;align-items:center;justify-content:center}
.app .stage .lg .felt .tablebox svg{width:100%;height:100%;max-height:100%}
.app .stage .note{margin:0;padding:2px 12px 4px;text-align:center;font-size:10px;color:rgba(217,227,242,.75)}
.app .dock{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:8px 10px calc(8px + env(safe-area-inset-bottom,0px));background:linear-gradient(rgba(11,20,38,.6),var(--hud));border-top:1px solid var(--hud-line)}
.app .dock button{font:inherit;font-size:13.5px;font-weight:600;color:var(--ink);padding:11px 4px;border-radius:10px;cursor:pointer;
  background:linear-gradient(var(--btn-top),var(--btn-bot));border:1px solid var(--btn-line);box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 3px 0 #050a14}
.app .dock button[aria-expanded="true"]{background:linear-gradient(#2e9e48,#1f7a35);border-color:#7dff9c}
.app .dock button:active{transform:translateY(2px);box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 1px 0 #050a14}
.app button:focus-visible,.app .seat:focus-visible{outline:2px solid #ffd65a;outline-offset:2px}
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.5);opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;max-height:78%;display:flex;flex-direction:column;z-index:45;margin:0 auto;max-width:760px;
  background:#0d1a33;border:1px solid var(--btn-line);border-bottom:0;border-radius:18px 18px 0 0;box-shadow:0 -12px 30px rgba(0,0,0,.5);
  transform:translateY(105%);visibility:hidden;transition:transform .25s ease-out,visibility 0s .25s}
.sheet.open{transform:none;visibility:visible;transition:transform .25s ease-out}
.sheet header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 8px;border-bottom:1px solid var(--hud-line)}
.sheet header b{color:var(--gold);font-size:15px;letter-spacing:.04em}
.sheet .x{font:inherit;color:var(--ink);background:none;border:1px solid var(--btn-line);border-radius:8px;padding:4px 12px;cursor:pointer}
.sheet .body{overflow-y:auto;-webkit-overflow-scrolling:touch;padding:12px 14px calc(16px + env(safe-area-inset-bottom,0px));overscroll-behavior:contain}
.sheet .body .felt{background:transparent;border:0;box-shadow:none;padding:0;border-radius:0}
.sheet .rules{line-height:1.65;color:#d9e3f2}
.sheet .rules ul{margin:0 0 12px;padding-left:20px}
.sheet .rules p{margin:0 0 8px;font-size:12px;color:var(--ink-soft)}
.app .lg .profile.open{position:fixed;left:0;right:0;bottom:0;top:auto;max-height:80%;overflow-y:auto;margin:0 auto;max-width:760px;border-radius:18px 18px 0 0;z-index:60;
  box-shadow:0 -10px 30px rgba(0,0,0,.45);padding-top:22px;background:var(--color-panel);color:var(--color-fg);padding-left:16px;padding-right:16px;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}
@media (prefers-reduced-motion:reduce){.sheet,.scrim{transition:none}}
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
    phase = _between(cards, '<div class="phase"', "</div>", include_end=True)
    table = _between(cards, '<div class="tablewrap">', "</div></div>", include_end=True)
    road = _between(cards, '<div class="road">', '      <div class="rail">').rstrip()
    rails = _between(cards, '<div class="rail">', '      <div class="fine">').rstrip()
    script = _between(src, "<script>", "</script>", include_end=True)
    for part in (phase, table, road, rails):
        if "회사 로고" in part:
            raise RuntimeError("공개 화면에 로고 안내가 섞임")
    when = generated_at[:16].replace("T", " ")
    sheet = lambda key, title, body: (f'<section class="sheet" id="s-{key}" role="dialog" aria-modal="true" aria-labelledby="t-{key}">'
                                      f'<header><b id="t-{key}">{title}</b><button type="button" class="x" data-close>닫기</button></header>'
                                      f'<div class="body"><div class="lg"><div class="felt">{body}</div></div></div></section>')
    rules = f"""<div class="rules"><ul>
      <li>두 팀(Claude 팀·슈슈 팀) 에이전트가 평일마다 한국·미국 종목을 1개씩 고릅니다. 마감은 08:30 KST입니다.</li>
      <li>점수는 그날 종가 기준 하루 수익률(배당 포함, %)이고 다음 날 10:30에 채점합니다. 원 가격은 보여 주지 않습니다.</li>
      <li>마감이 지난 라운드의 종목만 공개합니다. 한쪽 시장이 쉬는 날은 남은 시장만, 둘 다 쉬면 라운드가 없습니다.</li>
      <li>매주 두 팀 10명을 한 줄로 세워 꼴등 1명이 탈락하고 대기 후보가 들어옵니다. 채점이 모자라면 탈락을 미룹니다.</li>
      <li>캐릭터는 창작 캐릭터이며, 에이전트는 투자 스타일 이름만 씁니다. 실존 인물의 추천이 아닙니다.</li>
    </ul>
    <p>모의 예측 게임입니다. 돈이나 베팅은 없고, 실제 수익률·투자 권유가 아닙니다.</p>
    <p>데이터 출처: 한국 종가·지수 — <b>한국거래소 통계정보</b>(KRX Open API)를 사용한 결과 · 미국 종가·배당 — Tiingo · 한국 공시 — 금융감독원 OpenDART. 원 가격은 표시하지 않고 계산된 점수만 표시합니다.</p>
    <p>갱신 {when} KST</p></div>"""
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>AI 투자 리그 테이블</title>
<meta name="description" content="두 AI 팀의 모의 종목 예측 리그. 돈이나 베팅은 없습니다.">
<meta name="theme-color" content="#0b1426">
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<style>{TOKENS}</style>
{style}
</head><body>
<div class="app">
  <div class="hudbar"><h1>AI 투자 리그</h1><button type="button" class="mini" data-open="phase" aria-label="라운드 진행 보기" data-draw="phase-mini" data-source="calendar"></button></div>
  <main class="stage"><div class="lg">
    {defs}
    {profile}
    <div class="felt">{table}</div>
  </div><p class="note">모의 예측 게임 · 돈·베팅 없음 · 한국 시세: 한국거래소 통계정보</p></main>
  <nav class="dock" aria-label="메뉴">
    <button type="button" data-open="phase" aria-expanded="false">진행</button><button type="button" data-open="road" aria-expanded="false">기록판</button><button type="button" data-open="picks" aria-expanded="false">종목</button><button type="button" data-open="rules" aria-expanded="false">규칙</button>
  </nav>
</div>
<div class="scrim" data-close></div>
{sheet("phase", "라운드 진행", phase)}
{sheet("road", "기록판", road)}
{sheet("picks", "고른 종목 · 대기석", rails)}
{sheet("rules", "규칙 · 안내", rules)}
<script src="data/table.js"></script>
{RUNTIME}
{script}
<script>drawAll();
(() => {{
  const scrim = document.querySelector('.scrim');
  const closeAll = () => {{
    document.querySelectorAll('.sheet.open').forEach((s) => s.classList.remove('open'));
    document.querySelectorAll('[data-open]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
    scrim.classList.remove('on');
  }};
  document.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => {{
    const s = document.getElementById('s-' + b.dataset.open), was = s.classList.contains('open');
    closeAll();
    if (was) return;
    s.classList.add('open'); scrim.classList.add('on');
    document.querySelectorAll(`.dock [data-open="${{b.dataset.open}}"]`).forEach((x) => x.setAttribute('aria-expanded', 'true'));
    s.querySelector('.body').scrollTop = 0;
  }}));
  document.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', closeAll));
  document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') closeAll(); }});
}})();</script>
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
