// 리그 게임 화면 자동 플레이테스트 (스크린샷 + 기본 동작 점검)
//
//   python3 league/play/build.py <폴더>
//   node league/play/playtest.js <폴더> [--scale 1|2]
//
// 기기 크기마다: 첫 화면 → 캐릭터 누르기 → 카드 끝까지 밀어 올리기(공개) → 닫기 → 메뉴 창 → 결과 쇼 버튼
// 을 차례로 해 보고, 단계마다 스크린샷을 <폴더>/playtest/ 에 남긴다.
// 끝에 기기별 결과(자바스크립트 오류, 가로 스크롤, 화면 밖으로 나간 버튼, 작은 터치 영역)를 표로 출력한다.
// 그림 판단(겹침·가독성·무게감)은 스크린샷을 직접 보고 한다. 이 스크립트는 그 전에 걸러낼 기계적 문제만 잡는다.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const R = path.resolve(process.argv[2] || '.');
const scale = Number((process.argv.find((a, i) => process.argv[i - 1] === '--scale')) || 1);
const OUT = path.join(R, 'playtest');
fs.mkdirSync(OUT, { recursive: true });

const DEVICES = [
  ['폰세로', 390, 844, true],
  ['폰가로', 844, 390, true],
  ['작은폰', 375, 667, true],
  ['큰폰', 430, 932, true],
  ['데스크톱', 1280, 800, false],
];

// 화면에 보이는 버튼 중 너무 작거나 화면 밖으로 나간 것
const audit = () => {
  const vw = innerWidth, vh = innerHeight, small = [], outside = [];
  document.querySelectorAll('button, [role=button], .plate').forEach((el) => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (!r.width || !r.height || s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0 || s.pointerEvents === 'none') return;
    const name = (el.id ? '#' + el.id : el.className.toString().split(' ')[0]) + (el.textContent.trim() ? ':' + el.textContent.trim().slice(0, 8) : '');
    if (r.width < 24 || r.height < 24)     // WCAG 2.2 최소 터치 크기(24px). 이름판은 CSS로 누르는 영역을 넓혀 두어 실제보다 작게 잡힐 수 있음
      small.push(`${name}(${Math.round(r.width)}x${Math.round(r.height)})`);
    if (r.right > vw + 1 || r.bottom > vh + 1 || r.left < -1 || r.top < -1) outside.push(name);
  });
  return { hscroll: document.documentElement.scrollWidth > vw + 1, small: [...new Set(small)].slice(0, 6), outside: [...new Set(outside)].slice(0, 6) };
};

(async () => {
  const b = await chromium.launch();
  const rows = [];
  for (const [tag, w, h, mobile] of DEVICES) {
    for (const reduced of [false, true]) {
      if (reduced && tag !== '폰세로') continue;           // 동작 줄이기는 대표 기기 하나만
      const t = tag + (reduced ? '-동작줄임' : '');
      const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, deviceScaleFactor: scale, reducedMotion: reduced ? 'reduce' : 'no-preference' });
      const p = await ctx.newPage();
      const errs = [];
      p.on('pageerror', (e) => errs.push(e.message));
      const shot = (s) => p.screenshot({ path: path.join(OUT, `${t}-${s}.png`) });
      const row = { 기기: t, 오류: errs, 단계: [] };
      const step = async (name, fn) => { try { await fn(); row.단계.push(name + ' ✓'); } catch (e) { row.단계.push(name + ' ✗ ' + e.message.split('\n')[0].slice(0, 60)); } };

      await p.goto('file://' + path.join(R, 'index.html'));
      await p.waitForTimeout(3500);                         // 첫 방문 카드 돌리기 연출이 끝날 때까지
      await shot('1-첫화면');
      row.첫화면 = await p.evaluate(audit);
      row.밀림 = await p.evaluate(async () => {            // 아이폰 사파리는 포커스 때 게임 틀을 옆으로 민 적이 있다(2026-11-07)
        const g = document.querySelector('.game'); g.scrollLeft = 200; g.scrollTop = 200; window.scrollTo(200, 200);
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
        return [g.scrollLeft, g.scrollTop, window.scrollX, window.scrollY].some((v) => v !== 0);
      });

      await step('캐릭터 열기', async () => {
        await p.click('.plate >> nth=0', { timeout: 3000 });
        await p.waitForTimeout(700);
        if (!(await p.evaluate(() => document.querySelector('.game').classList.contains('zoomed')))) throw new Error('확대 화면이 안 열림');
        await shot('2-확대');
      });
      await step('카드 공개', async () => {
        const c = await p.$('.big'); const bb = await c.boundingBox();
        const x = bb.x + bb.width / 2, y0 = bb.y + bb.height * 0.85;
        await p.mouse.move(x, y0); await p.mouse.down();
        for (let k = 1; k <= 12; k++) { await p.mouse.move(x, y0 - bb.height * 0.8 * k / 12); await p.waitForTimeout(16); }
        await p.mouse.up(); await p.waitForTimeout(1800);
        const done = await p.evaluate(() => { const c = document.querySelector('.big'); return c && c._t ? c._t() : -1; });
        if (done < 0.99) throw new Error('끝까지 안 젖혀짐(' + done.toFixed(2) + ')');
        await shot('3-공개');
        row.공개 = await p.evaluate(audit);
      });
      await step('닫기', async () => {
        await p.keyboard.press('Escape'); await p.waitForTimeout(600);
        if (await p.evaluate(() => document.querySelector('.game').classList.contains('zoomed'))) throw new Error('Esc로 안 닫힘');
      });
      await step('메뉴 창', async () => {
        const n = await p.$$eval('[data-open]', (a) => a.length);
        if (!n) throw new Error('메뉴 버튼 없음');
        await p.click('[data-open] >> nth=0'); await p.waitForTimeout(600);
        await shot('4-메뉴');
        row.메뉴 = await p.evaluate(audit);
        await p.keyboard.press('Escape'); await p.waitForTimeout(400);
      });
      await step('결과 쇼', async () => {
        if (await p.$eval('#showbtn', (e) => e.hidden)) { row.단계.push('결과 쇼 버튼 없음(채점된 라운드 없음)'); return; }
        await p.click('#showbtn'); await p.waitForTimeout(reduced ? 1500 : 6000);
        await shot('5-결과쇼');
        row.결과쇼 = await p.evaluate(audit);
        await p.keyboard.press('Escape');
      });
      rows.push(row);
      await ctx.close();
    }
  }
  await b.close();

  let bad = 0;
  for (const r of rows) {
    const issues = [];
    if (r.오류.length) issues.push('JS오류: ' + r.오류.join(' / ').slice(0, 120));
    if (r.밀림) { issues.push('게임 틀이 옆으로 밀림(스크롤 가능)'); bad++; }
    for (const k of ['첫화면', '공개', '메뉴', '결과쇼']) {
      const a = r[k]; if (!a) continue;
      if (a.hscroll) issues.push(`${k} 가로 스크롤`);
      if (a.outside.length) issues.push(`${k} 화면 밖: ${a.outside.join(', ')}`);
      if (a.small.length) issues.push(`${k} 작은 터치 영역: ${a.small.join(', ')}`);
    }
    const fail = r.단계.filter((s) => s.includes('✗'));
    bad += fail.length + (r.오류.length ? 1 : 0);
    console.log(`\n[${r.기기}] ${r.단계.join(' · ')}`);
    issues.forEach((s) => console.log('  - ' + s));
  }
  console.log(`\n스크린샷: ${OUT}`);
  console.log(bad ? `실패 ${bad}건` : '동작 점검 통과 (그림 판단은 스크린샷으로)');
  process.exit(bad ? 1 : 0);
})();
