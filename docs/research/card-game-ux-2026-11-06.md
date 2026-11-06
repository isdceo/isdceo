# 인기 카드게임 앱에서 배울 점 → 리그 게임 화면 개선안 (2026-11-06)

## 조사 범위와 한계

- 대상: 2025~2026년에 자주 언급되는 모바일 카드게임과 카드 연출이 좋다고 평가받는 게임
  - 포켓몬 TCG 포켓(팩 개봉), 마블 스냅(카드 놓기·공개), 발라트로(점수 연출), 모바일 바카라 앱의 쪼이기(스퀴즈), 로열 매치(버튼·진동 마감)
- 근거: 개발사 공식 설명은 거의 없고 리뷰·디자인 분석 글·앱 소개가 대부분입니다. 아래 "배울 점"은 그 글들에서 공통으로 나온 내용만 추렸습니다.
- 지킬 것: 특정 게임의 그림·이름·화면을 따라 하지 않고 **원리만** 가져옵니다. 리그 규칙(돈·베팅 없음, 원 가격 없음, 마감 전 종목 없음)에 걸리는 요소(재화, 뽑기, 보상 상자, 베팅)는 넣지 않습니다.

## 공통으로 배울 점 7가지

| # | 배울 점 | 근거로 든 게임 | 우리 화면 현재 |
|---|---|---|---|
| 1 | **손가락을 따라 열린다.** 공개 정도가 손가락 움직임에 그대로 따라온다 | 포켓몬 TCG 포켓의 팩 찢기, 바카라 쪼이기 | ✅ 카드를 끌면 끈 만큼 젖혀짐 |
| 2 | **결과는 맨 마지막에.** 앞면이 보이기 전에 결과가 먼저 번쩍이면 긴장이 깨진다 | 바카라 리뷰 | ✅ 점수는 다 젖힌 뒤에 나옴 |
| 3 | **숫자는 굴러서 나온다.** 점수가 그냥 뜨지 않고 올라가며, 크기에 따라 흔들림·빛이 달라진다 | 발라트로 | ❌ 점수가 한 번에 뜸 |
| 4 | **드문 결과는 다른 연출.** 흔한 결과는 빠르게, 드문 결과는 빛·소리로 따로 | 포켓몬 TCG 포켓(희귀 카드), 카드 개봉 UX 글 | ❌ 모든 결과가 같은 연출 |
| 5 | **캐릭터마다 반응이 다르다.** 같은 동작도 카드(캐릭터)마다 고유 애니메이션 | 마블 스냅 | ❌ 캐릭터는 숨쉬기만 함 |
| 6 | **소리와 진동을 겹친다.** 그림·소리·진동이 같이 와야 손맛이 난다. 누를 때가 뗄 때보다 강하게 | 발라트로, 안드로이드 진동 지침, 로열 매치 분석 | ❌ 소리·진동 없음 |
| 7 | **건너뛰기·속도.** 반복해서 보면 연출이 길게 느껴진다. 빠르게 넘길 길이 있어야 한다 | 카드 개봉 UX 글, 발라트로 이용자 의견 | △ '모두 공개'만 있음 |

## 우리 화면에 넣을 개선안 (효과 큰 순서)

### A. 바로 하면 좋은 것 (화면 안에서 끝남)

1. **점수 굴리기 (3번)**
   - 다 젖히면 점수가 0.00%에서 실제 값까지 0.6초 동안 올라갑니다.
   - ±1% 이상이면 카드가 살짝 흔들리고, ±3% 이상이면 금빛(상승)이나 붉은빛(하락) 테두리가 퍼집니다.
   - 확정이 아닌 점수(잠정·채점 전)는 굴리지 않고 그대로 보여 줍니다.
2. **큰 움직임 전용 연출 (4번)**
   - 하루 ±5% 이상(예: 미래광 AppLovin +31.04%)은 카드 뒤에서 빛줄기가 퍼지고 말풍선 앞에 "대박!"이나 "아이고…"가 붙습니다.
   - 드물게 나와야 의미가 있으므로 기준을 높게 잡습니다.
   - 돈·보상으로 오해할 표현(잭팟, 코인)은 쓰지 않습니다.
3. **캐릭터 반응 (5번)**
   - 두 장을 다 열면 캐릭터가 결과에 따라 반응합니다.
     - 평균이 오르면 통통 뛰기와 반짝이
     - 내리면 고개를 떨구는 흔들림과 땀방울 그림
     - 보합이면 어깨 으쓱
   - 그림을 새로 만들 필요 없이 CSS 움직임과 작은 그림 문자로 됩니다.
   - 나중에 3D 표정 그림(웃음·울상)을 캐릭터마다 2장씩 더 만들면 더 좋아집니다.
4. **누를 때 손맛 (6번, 진동)**
   - 버튼과 카드를 누르면 살짝 눌렸다 튀어 오릅니다.
   - 안드로이드에서는 짧은 진동을 줍니다. 쪼이다 멈칫할 때 약하게, 공개 순간에 조금 강하게 줍니다.
   - 아이폰 브라우저는 진동을 지원하지 않으므로 그림 효과만 나옵니다.
5. **빠르게 보기 (7번)**
   - 쪼이기 창을 한 번 더 누르면 남은 연출을 바로 끝냅니다.
   - 메뉴에 "연출 빠르게" 켜고 끄기를 두고, 기기 안에만 저장합니다.
   - 기기의 "동작 줄이기" 설정은 지금처럼 존중합니다.

### B. 하루 흐름을 만드는 것 (리그 일정과 맞물림)

6. **오늘의 공개 쇼**
   - 채점(다음 날 10:30)이 끝나면 첫 화면에 "어제 라운드 결과 보기" 버튼이 뜹니다.
   - 누르면 20장을 한 장씩 빠르게 넘기며 점수를 굴리고, 마지막에 팀 평균과 오늘의 승자를 보여 줍니다.
   - 기록판의 승패 구슬도 이때 하나 굴러 들어갑니다.
7. **안 본 카드 표시**
   - 아직 쪼여 보지 않은 캐릭터의 이름판에 작은 점을 붙입니다. 이 기록은 기기 안에만 저장합니다.
   - 연속 출석·보상은 넣지 않습니다. 출석 보상은 금방 숙제처럼 느껴진다는 지적이 많고, 우리 리그는 보상이 없는 게임입니다.
8. **주간 탈락 연출**
   - 주간 마감(월 06:30) 뒤 첫 방문 때 꼴등 캐릭터가 테이블에서 물러나고 대기 1순위가 앉는 짧은 연출을 보여 줍니다.
   - 탈락자는 "대기석"으로 갑니다.

### C. 나중에 고려할 것

9. **처음 온 사람 안내 3장:** 첫 방문에 한해 "캐릭터를 누르세요 → 카드를 밀어 올리세요 → 이유를 읽어 보세요"를 손가락 그림과 함께 짧게 보여 줍니다.
10. **소리 (6번):** 카드 넘기는 소리, 칩 소리, 공개 소리를 넣습니다. 기본은 꺼 두고, 켜고 끄는 버튼을 둡니다. 소리 파일은 저작권이 깨끗한 것(직접 만들거나 무료 라이선스)만 씁니다.
11. **지인 "오늘의 예감"(신중히):** 친구가 오늘 어느 팀이 이길지 눌러 보는 기능입니다. 돈·포인트가 전혀 없어도 베팅처럼 보일 수 있어 지금은 **넣지 않기를 권합니다.**

## 넣지 않을 것

- 재화(코인·보석), 뽑기·상자, 출석 보상, 순위 보상, 광고. 리그는 "모의 예측 게임 · 돈·베팅 없음"입니다.
- 특정 게임의 고유 연출을 그대로 옮기는 것(예: 특정 게임의 카드 틀·효과음·글자 모양).

## 권하는 순서

1. A-1 점수 굴리기 + A-2 큰 움직임 연출 + A-3 캐릭터 반응: 쪼이기 손맛이 가장 크게 좋아집니다.
2. A-4 눌림·진동 + A-5 빠르게 보기
3. B-6 오늘의 공개 쇼 + B-7 안 본 카드 표시: 11/9 실전 뒤 첫 채점(11/10 10:30) 전에 넣으면 좋습니다.
4. B-8 주간 탈락 연출: 첫 주간 마감(11/16) 전에 넣습니다.

각 단계 뒤에 지금처럼 별도 에이전트 검수를 받습니다.

## 출처

- [Best Mobile Card Games in 2026 (FRVR)](https://frvr.com/blog/guides/lists/best-mobile-card-games/)
- [Top Mobile Games by Worldwide Revenue, November 2024 (FoxData)](https://foxdata.com/en/blogs/top-mobile-games-by-worldwide-revenue-for-november-2024/)
- [Top card apps trending (Similarweb)](https://www.similarweb.com/top-apps/google/india/games/cards/trending)
- [Pokémon TCG Pocket preview (Serebii)](https://serebii.net/tcgpocket/preview/)
- [Pokémon TCG Pocket god packs (Pocket Tactics)](https://www.pockettactics.com/pokemon-tcg-pocket/god-packs)
- [Pokémon TCG Pocket rare pack animation (GameWith)](https://gamewith.net/pokemon-tcg-pocket/49002)
- [Choreographed Emotion — card reveal UX (Medium)](https://medium.com/n3twork/choreographed-emotion-6-steps-to-a-great-card-reveal-ux-a6e6bb8487dd)
- [Marvel Snap review (Gamers Decide)](https://gamersdecide.com/articles/marvel-snap-review)
- [Marvel Snap developer update (Marvel Snap Zone)](https://marvelsnapzone.com/developer-update-for-the-week-of-august-30-2023/)
- [Balatro: juicy feedback design guide (Blake Crosley)](https://blakecrosley.com/ko/guides/design/balatro)
- [Unpacking Balatro's addicting game (Substack)](https://errorandexp.substack.com/p/unpacking-balatros-addicting-game)
- [ICONIC21 Squeeze Baccarat (iGaming Business)](https://igamingbusiness.com/company-news/iconic21-launches-squeeze-baccarat-bringing-the-ritual-of-the-reveal-to-the-rng-format/)
- [BaccaratMan (App Store)](https://apps.apple.com/us/app/baccaratman/id400851160)
- [Baccarat card presentation review (Wonderlust)](https://www.wonderlust.vn/?p=1714)
- [5 Simple UX Lessons From Royal Match](https://thisweekinliveops.substack.com/p/5-simple-ux-lessons-from-royal-match)
- [Haptics UX design (Android)](https://source.android.com/docs/core/interaction/haptics/haptics-ux-design)
- [Daily login strategies by top studios (ironSource LevelUp)](https://medium.com/ironsource-levelup/keeping-players-engaged-common-strategies-for-daily-login-by-top-studios-b20d9b595035)
- [XP for Logging In (Game Wisdom)](https://game-wisdom.com/general/xp-logging-age-daily-gaming-habits)
