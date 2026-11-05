# 지인 공유판 배포 안내 (Cloudflare Pages + Access)

> 상태: **준비만 됨, 꺼져 있음.** (`league/config.json` → `deploy_enabled: false`)
> 목표: 지인 10명 이하만 이메일 인증으로 보는 비공개 화면, 비용 0원.
> Cloudflare 화면 메뉴 이름은 바뀔 수 있다. 아래는 2026-11 기준 일반적인 경로이며, 무료 한도는 설정 전에 Cloudflare 요금 페이지에서 다시 확인한다.

## 무엇이 올라가나

`python3 tools/league.py build-site`가 만드는 `site/` 폴더만 올라간다. 원시 가격이 들어가면 빌드가 실패하도록 되어 있다.

| 파일 | 내용 |
|---|---|
| `league.html` | 리그 화면. 화면에 "지인 공유판 · 원시 가격 미포함" 표시 |
| `data/league.js` | 점수·순위·종목명·근거·영수증 요약 (종가·배당 금액 없음) |
| `index.html`, `data/holdings.js` | 시장 대시보드(예시 시세)와 SEC 13F 보유 현황(미국 정부 공개 자료) |

## 1. Cloudflare 계정과 Pages 프로젝트

1. Cloudflare에 가입하고 로그인한다(무료 플랜).
2. **Workers & Pages** → **Create** → **Pages** → **Upload assets**(직접 업로드)를 고른다.
3. 프로젝트 이름은 `isdceo-league`로 한다. 다른 이름을 쓰면 `league/config.json`의 `cloudflare_project`도 같이 바꾼다.
4. 첫 업로드는 빈 폴더나 아무 파일로 해도 된다. 이후 배포는 GitHub Actions가 한다.
5. 주소는 `https://isdceo-league.pages.dev` 형태가 된다.

## 2. 지인만 보이게: Cloudflare Access (Zero Trust)

**이 단계를 끝내기 전에는 배포를 켜지 않는다.** Access를 걸지 않으면 주소를 아는 누구나 볼 수 있다.

1. Cloudflare 대시보드 → **Zero Trust**로 들어간다. 처음이면 팀 이름을 정하고 **Free** 플랜을 고른다. 결제 수단 입력을 요구할 수 있지만, 무료 범위에서는 청구되지 않는다(가입 시 화면에서 확인).
2. **Access** → **Applications** → **Add an application** → **Self-hosted**를 고른다.
3. 도메인에 `isdceo-league.pages.dev`를 입력한다. 미리보기 주소까지 막으려면 `*.isdceo-league.pages.dev`도 추가한다.
4. 정책(Policy)
   - 이름: `friends`, 동작: **Allow**
   - 조건: **Emails**에 지인 이메일을 하나씩 입력한다(10명 이하).
5. 로그인 방법: **One-time PIN**(이메일로 받는 일회용 코드)만 켠다.
6. 저장 뒤 시크릿 창에서 주소를 열어 확인한다.
   - 등록하지 않은 이메일로는 들어갈 수 없어야 한다.
   - 등록한 이메일로는 코드를 받아 들어갈 수 있어야 한다.

> 지인 이메일 목록은 Cloudflare에만 둔다. 저장소에는 적지 않는다.

## 3. GitHub Secrets

저장소 → Settings → Secrets and variables → Actions → **New repository secret**

| Name | 값 |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens → Create Token → 권한 **Account / Cloudflare Pages / Edit**만 준 토큰 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 대시보드 오른쪽(또는 Workers & Pages 개요)에 보이는 Account ID |

## 4. 켜기

0. **먼저 Tiingo 회신을 받는다.** Tiingo 무료 플랜은 "you may not display or share the data with another person or organization"이라 지인 공개는 회신 전에는 켜지 않는다(`docs/data-provider-research.md` 8장). KRX 회신도 받는 것을 권장한다.
1. `league/config.json`에서 `"deploy_enabled": true`로 바꾸고 커밋한다.
2. Actions → **league-deploy** → Run workflow로 첫 배포를 한다.
3. 이후에는 매일(월~토) 11:00 KST에 자동 배포된다. 10:30 채점 뒤다.

## 5. 배포 뒤 점검

- 시크릿 창에서 주소를 열었을 때 Access 로그인 화면이 먼저 나오는가
- 화면 상단에 "지인 공유판 · 원시 가격 미포함" 표시가 있는가
- 추천 상세를 펼쳐도 "종가 (기준 → 평가)" 줄이 없는가
- 데이터 제공처 사용권 문의 결과가 "점수 표시 불가"로 오면 즉시 `deploy_enabled: false`로 끄고, Pages 프로젝트의 배포를 삭제한다

## 끄기 / 지우기

- 자동 배포 중지: `deploy_enabled: false`
- 공개 중지: Cloudflare Pages 프로젝트 → Settings에서 프로젝트를 삭제하거나, Access 정책에서 모든 이메일을 지운다
