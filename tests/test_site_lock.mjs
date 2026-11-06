// 비밀번호 잠금(league/site-functions/_middleware.js) 시험: node tests/test_site_lock.mjs
import assert from 'node:assert/strict';
import { onRequest } from '../league/site-functions/_middleware.js';

const page = () => new Response('<h1>league</h1>', { headers: { 'Content-Type': 'text/html' } });
const call = (env, auth) => onRequest({
  request: new Request('https://isdceo-league.pages.dev/', { headers: auth ? { Authorization: auth } : {} }),
  env, next: async () => page(),
});
const basic = (u, p) => 'Basic ' + Buffer.from(`${u}:${p}`).toString('base64');
const env = { SITE_PASSWORD: 'correct horse battery staple' };

let r = await call({}, basic('operator', 'x'));
assert.equal(r.status, 503, '비밀번호 미설정이면 잠긴 채 실패');
assert.match(r.headers.get('WWW-Authenticate'), /Basic/);

r = await call(env);
assert.equal(r.status, 401, '로그인 없이 거부');
assert.equal(await r.text(), '로그인이 필요합니다.');

r = await call(env, basic('operator', 'wrong'));
assert.equal(r.status, 401, '틀린 비밀번호 거부');
r = await call(env, basic('someone', env.SITE_PASSWORD));
assert.equal(r.status, 401, '틀린 아이디 거부');
r = await call(env, 'Basic !!!not-base64');
assert.equal(r.status, 401, '깨진 헤더 거부');

r = await call(env, basic('operator', env.SITE_PASSWORD));
assert.equal(r.status, 200, '맞으면 통과');
assert.equal(await r.text(), '<h1>league</h1>');
assert.equal(r.headers.get('Cache-Control'), 'private, no-store');
assert.match(r.headers.get('X-Robots-Tag'), /noindex/);

r = await call({ ...env, SITE_USER: 'me' }, basic('me', env.SITE_PASSWORD));
assert.equal(r.status, 200, 'SITE_USER 지정');

r = await call(env, basic('operator', '한글:비밀:번호'));
assert.equal(r.status, 401);
r = await call({ SITE_PASSWORD: '한글:비밀:번호' }, 'Basic ' + Buffer.from('operator:한글:비밀:번호').toString('base64'));
assert.equal(r.status, 200, '콜론·한글 비밀번호');
console.log('site lock: 통과');
