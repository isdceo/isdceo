// node tools/cron-worker/test.mjs — 시각표가 GitHub 예약과 같은지 몇 지점 확인
import { due } from "./worker.js";
const at = (iso) => due(new Date(iso)).map((x) => x[2] + (x[3] ? ":" + x[3].task : ""));
const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) { console.error("FAIL", m, a, b); process.exit(1); } };
eq(at("2026-11-10T06:50:00+09:00"), ["league-daily.yml:snapshot"], "화 06:50");
eq(at("2026-11-10T08:35:00+09:00"), ["league-daily.yml:collect"], "화 08:35");
eq(at("2026-11-14T08:35:00+09:00"), [], "토 08:35 없음");
eq(at("2026-11-14T10:30:00+09:00"), ["league-daily.yml:collect"], "토 10:30");
eq(at("2026-11-16T06:30:00+09:00"), ["league-daily.yml:weekly"], "월 06:30");
eq(at("2026-11-16T06:40:00+09:00"), ["league-shushu-sync.yml"], "월 06:40");
eq(at("2026-11-10T08:31:00+09:00"), ["league-shushu-sync.yml"], "화 08:31");
eq(at("2026-11-10T08:45:00+09:00"), ["league-deploy.yml"], "화 08:45");
eq(at("2026-11-15T12:05:00+09:00"), ["league-shushu-sync.yml"], "일 12:05");
eq(at("2026-11-10T12:05:00+09:00"), ["league-shushu-sync.yml"], "화 12:05");
eq(at("2026-11-10T12:10:00+09:00"), ["league-deploy.yml"], "화 12:10");
eq(at("2026-11-10T08:36:00+09:00"), [], "화 08:36 없음");
console.log("cron-worker 시각표 OK");
