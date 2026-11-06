# 지인 공유판 배포 안내 (Cloudflare Pages + Access)

> 상태: **준비만 됨, 꺼져 있음.** (`league/config.json` → `deploy_enabled: false`)
> 목표: 지인 10명 이하만 이메일 인증으로 보는 비공개 화면, 비용 0원.
> Cloudflare 화면 메뉴 이름은 바뀔 수 있다. 아래는 2026-11 기준 일반적인 경로이며, 무료 한도는 설정 전에 Cloudflare 요금 페이지에서 다시 확인한다.

## 무엇이 올라가나

`python3 tools/league.py build-site`가 만드는 `site/` 폴더만 올라간다. 원시 가격이 들어가면 빌드가 실패하도록 되어 있다.

| 파일 | 내용 |
|---|---|
| `index.html` | 게임 화면(카지노 테이블 로비·카드 쪼이기·한 줄 이유 말풍선·메뉴 창 4개). 원본 `league/play/src.html`, 만드는 곳 `tools/build_play.py` |
| `av/*.webp` | 3D 캐릭터 그림 14장(원본 `league/play/av/`) |
| `data/table.js` | 두 팀 공유용 결과 묶음과 같은 내용 + 라운드 달력 (종가·배당 금액·회사 로고 없음, 마감 전 종목 없음) |

지인에게는 게임 화면만 보인다(2026-11-05 운영자 결정). 표 화면 `league.html`과 시장 대시보드는 올리지 않고 운영자 확인용으로 저장소에만 둔다.
게임 화면을 고치려면 `league/play/src.html`을 고치면 다음 빌드에 같이 반영된다(2026-11-06 로로 팀 2.5D 화면 채택). 운영 현황판 페이지에서는 3D 그림이 없는 캐릭터용 2D 정의만 가져온다.
화면 글꼴(도현·Noto Sans KR, OFL)은 `fonts/`에 함께 올린다. 외부 요청이 없다(`league/play/fonts/README.md`).

**배포를 켜기 전에 데이터 제공처 조건을 정리한다.** 미국 종가·배당은 2026-11-06부터 Alpha Vantage로 받는다. 무료 키는 개인·비상업 이용이라, 점수를 지인에게 보여 주는 것이 "개인 범위"에 드는지 확인이 필요하다(`docs/data-provider-research.md` 10장). Tiingo를 그만 쓴 이유는 같은 문서 8장에 있다.

## 0. 운영자 혼자 보기 — 비밀번호 잠금 (2026-11-07 결정, 카드 등록 없음)

데이터 제공처 약관(KRX·Alpha Vantage·OpenDART)은 모두 개인·비상업 이용을 허용하므로, 운영자 혼자 보는 화면은 허락 회신을 기다리지 않고 켤 수 있다. Cloudflare Access(2장)는 카드 등록을 요구할 수 있어 쓰지 않고, **Pages Functions 비밀번호 잠금**을 쓴다.

- 잠금 코드: `league/site-functions/_middleware.js`. 배포 때 `functions/`로 함께 올라가 모든 요청(그림·데이터 파일 포함)에 아이디·비밀번호 창을 띄운다. 비밀번호가 설정돼 있지 않으면 아무도 못 들어온다. 시험: `node tests/test_site_lock.mjs`
- 배포 작업은 (1) Pages 프로젝트에 `SITE_PASSWORD`(비밀 유형)가 있는지 확인하고 없으면 배포하지 않으며, (2) 배포 뒤 주소·데이터 파일이 401(로그인 필요)인지 확인하고 아니면 실패로 알린다.

순서
1. 1단계(Pages 프로젝트 `isdceo-league`, 직접 업로드)를 한다. **Git 연결은 쓰지 않는다**(배포 작업의 안전장치를 거치지 않게 됨).
2. Pages 프로젝트 → **설정** → **변수 및 비밀**(Variables and Secrets) → 추가
   - 유형 **비밀**(Secret/암호화), 이름 `SITE_PASSWORD`, 값: 16자 이상 비밀번호. 프로덕션(Production) 환경에 넣는다.
   - 아이디를 바꾸려면 `SITE_USER`도 넣는다(없으면 `operator`).
   - 비밀번호는 휴대폰 비밀번호 관리자에 저장한다. 저장소·채팅에 적지 않는다.
3. 3단계(GitHub Secrets 두 개)를 한다.
4. `deploy_enabled: true` → Actions **league-deploy** 실행.
5. 휴대폰에서 주소를 열어 아이디 `operator`와 비밀번호로 들어가지는지, 틀린 비밀번호로 막히는지 확인한다. "홈 화면에 추가"로 앱처럼 쓴다.

지킬 것: 비밀번호·링크·화면 캡처를 남에게 주지 않는다. 지인에게 보여 주려면 제공처 허락 회신이 먼저다(4단계 0번).

## 1. Cloudflare 계정과 Pages 프로젝트

1. Cloudflare에 가입하고 로그인한다(무료 플랜).
2. **Workers & Pages** → **Create** → **Pages** → **Upload assets**(직접 업로드)를 고른다.
3. 프로젝트 이름은 `isdceo-league`로 한다. 다른 이름을 쓰면 `league/config.json`의 `cloudflare_project`도 같이 바꾼다.
4. 첫 업로드는 빈 폴더나 아무 파일로 해도 된다. 이후 배포는 GitHub Actions가 한다.
5. 주소는 `https://isdceo-league.pages.dev` 형태가 된다.

## 2. (선택) 지인만 보이게: Cloudflare Access (Zero Trust)

> 2026-11-07부터 기본은 0장의 비밀번호 잠금이다. 아래는 지인 공개 허락을 받은 뒤 이메일 인증으로 바꾸고 싶을 때 쓴다(카드 등록이 필요할 수 있음). Access로 바꿔도 비밀번호 잠금은 그대로 남는다.

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

0. **지인을 넣을 때는 먼저 제공처 회신을 받는다.** Alpha Vantage(약관 2.a 서면 합의, 메일 초안 `docs/provider-requests/alphavantage-permission-email.md`)와 KRX(제11조② 제3자 제공 금지, 문의 문안 `docs/provider-inquiries.md` 1번). 운영자 혼자 보기(0장)는 회신 없이 켜도 된다.
1. `league/config.json`에서 `"deploy_enabled": true`로 바꾸고 커밋한다.
2. Actions → **league-deploy** → Run workflow로 첫 배포를 한다. 배포 전에 `SITE_PASSWORD` 설정을 확인하고, 배포 뒤 주소가 비밀번호를 요구하는지 확인한다. 둘 중 하나라도 아니면 실패로 멈춘다.
3. 이후에는 매일(월~토) 11:00 KST에 자동 배포된다. 10:30 채점 뒤다.

## 5. 배포 뒤 점검

- 시크릿 창에서 주소를 열었을 때 Access 로그인 화면이 먼저 나오는가
- 화면 상단에 "지인 공유판 · 원시 가격 미포함" 표시가 있는가
- 추천 상세를 펼쳐도 "종가 (기준 → 평가)" 줄이 없는가
- 데이터 제공처 사용권 문의 결과가 "점수 표시 불가"로 오면 즉시 `deploy_enabled: false`로 끄고, Pages 프로젝트의 배포를 삭제한다

## 끄기 / 지우기

- 자동 배포 중지: `deploy_enabled: false`
- 공개 중지: Cloudflare Pages 프로젝트 → Settings에서 프로젝트를 삭제하거나, Access 정책에서 모든 이메일을 지운다
