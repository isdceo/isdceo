// 리그 정시 호출기 (Cloudflare Worker, 1분마다 깨어남).
// GitHub Actions 예약(cron)이 이 저장소에서 1~7시간 늦거나 빠져서(2026-11-05~09 확인), 정해진 KST 시각에
// 해당 워크플로를 workflow_dispatch로 직접 부른다. 워크플로는 같은 입력을 여러 번 받아도 결과가 같다(동기화·영수증은
// 같은 push·파일을 한 번만 처리, 공통 자료는 이미 있으면 그 판을 채택, 수집은 확정값이 있으면 건너뜀).
// 외부 요청으로는 아무것도 실행하지 않는다(fetch 는 상태 문구만).
const REPO = "isdceo/isdceo";
const REF = "claude/web-vs-desktop-differences-ir8pm0";
const WD = [1, 2, 3, 4, 5], MS = [1, 2, 3, 4, 5, 6];   // 요일(0=일): 월~금, 월~토

// [요일 목록, "HH:MM"(KST), 워크플로 파일, 입력]
const PLAN = [
  [[1], "06:30", "league-daily.yml", { task: "weekly", target: "league" }],
  [WD, "06:50", "league-daily.yml", { task: "snapshot", target: "league" }],
  [WD, "08:35", "league-daily.yml", { task: "collect", target: "league" }],
  [MS, "10:30", "league-daily.yml", { task: "collect", target: "league" }],
  [WD, "08:45", "league-deploy.yml"], [WD, "09:15", "league-deploy.yml"],
  [MS, "11:00", "league-deploy.yml"], [MS, "12:10", "league-deploy.yml"],
  [[1], "06:40", "league-shushu-sync.yml"],
  ...["06:57", "07:05", "07:35", "08:00", "08:10", "08:20", "08:31", "08:40", "08:50",
      "09:00", "09:10", "09:20", "09:30", "09:40", "09:50", "10:05", "11:05", "12:05", "18:05"].map((t) => [WD, t, "league-shushu-sync.yml"]),
  [[6], "10:50", "league-shushu-sync.yml"],
  [[0, 6], "12:05", "league-shushu-sync.yml"], [[0, 6], "18:05", "league-shushu-sync.yml"],
];

export function due(date) {
  const k = new Date(date.getTime() + 9 * 3600e3);              // KST
  const hm = String(k.getUTCHours()).padStart(2, "0") + ":" + String(k.getUTCMinutes()).padStart(2, "0");
  return PLAN.filter(([days, t]) => t === hm && days.includes(k.getUTCDay()));
}

async function dispatch(env, wf, inputs) {
  const body = JSON.stringify(inputs ? { ref: REF, inputs } : { ref: REF });
  for (let i = 0; i < 2; i++) {
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
      method: "POST", body,
      headers: { Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`, Accept: "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "league-cron-worker" } });
    if (r.status === 204) return console.log(`dispatched ${wf} ${JSON.stringify(inputs || {})}`);
    console.error(`dispatch ${wf} failed ${r.status} ${(await r.text()).slice(0, 200)}`);
  }
}

export default {
  async scheduled(event, env, ctx) {
    for (const [, , wf, inputs] of due(new Date(event.scheduledTime))) ctx.waitUntil(dispatch(env, wf, inputs));
  },
  async fetch() {
    return new Response("league cron worker: scheduled only\n", { status: 200 });
  },
};
