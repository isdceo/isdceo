// Cloudflare Pages 비밀번호 잠금 (운영자 혼자 보기, 카드 등록 없는 무료 방식)
//
// 배포 작업(.github/workflows/league-deploy.yml)이 이 폴더를 functions/ 로 복사해 사이트와 함께 올린다.
// 모든 요청(정적 파일 포함)이 이 함수를 먼저 거친다.
// - 비밀번호: Cloudflare Pages 프로젝트 → 설정 → 변수 및 비밀 → SITE_PASSWORD (비밀 유형). 저장소에 두지 않는다.
// - 아이디: SITE_USER (없으면 "operator")
// - SITE_PASSWORD 가 없으면 아무도 들어오지 못한다(잠긴 채로 실패).

const enc = new TextEncoder();

// 길이가 달라도 시간이 새지 않게 해시끼리 비교
async function same(a, b) {
  const [x, y] = await Promise.all([a, b].map((s) => crypto.subtle.digest('SHA-256', enc.encode(s))));
  const u = new Uint8Array(x), v = new Uint8Array(y);
  let d = 0;
  for (let i = 0; i < u.length; i++) d |= u[i] ^ v[i];
  return d === 0;
}

const deny = (status, msg) => new Response(msg, {
  status,
  headers: {
    'WWW-Authenticate': 'Basic realm="league", charset="UTF-8"',
    'Content-Type': 'text/plain; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Robots-Tag': 'noindex, nofollow',
  },
});

export async function onRequest({ request, env, next }) {
  const pw = env.SITE_PASSWORD;
  if (!pw) return deny(503, '잠금 비밀번호가 설정되지 않아 열 수 없습니다.');
  const user = env.SITE_USER || 'operator';
  const h = request.headers.get('Authorization') || '';
  let ok = false;
  if (h.startsWith('Basic ')) {
    let raw = '';
    try { raw = new TextDecoder().decode(Uint8Array.from(atob(h.slice(6)), (c) => c.charCodeAt(0))); } catch (e) { raw = ''; }
    const i = raw.indexOf(':');
    if (i >= 0) {
      const u = await same(raw.slice(0, i), user), p = await same(raw.slice(i + 1), pw);   // 둘 다 계산
      ok = u && p;
    }
  }
  if (!ok) return deny(401, '로그인이 필요합니다.');
  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set('Cache-Control', 'private, no-store');
  out.headers.set('X-Robots-Tag', 'noindex, nofollow');
  return out;
}
