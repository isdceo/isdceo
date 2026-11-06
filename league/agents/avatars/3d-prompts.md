# 3D 캐릭터 생성 문구 (이미지 생성 도구용)

ChatGPT 앱으로 만들 때는 복사용 순서 문서 `3d-chatgpt.md` 를 쓰세요. 이 문서는 다른 도구(영문 문구)용입니다.

운영자가 보낸 참고 그림 3장(카지노 테이블에 앉은 3D 애니메이션 캐릭터)의 **화풍만** 따릅니다. 참고 그림 속 인물을 그대로 따라 그리지 않고, 리그 창작 캐릭터 14명을 이 화풍으로 새로 만듭니다.

## 지킬 것

- **실존 인물을 닮지 않게.** 특히 투자 스타일과 연결된 실존 투자자(가치·역발상·거시·혁신 투자로 유명한 사람들)를 떠올리게 하는 얼굴·안경·머리 모양을 피합니다. 결과가 누군가를 닮았으면 버리고 다시 만듭니다.
- 글자·로고·브랜드·실제 카지노 이름이 그림에 들어가지 않게 합니다.
- 생성 도구 이용약관에서 **만든 그림을 다른 사람에게 보여 줘도 되는지**(공유·게시 허용) 확인합니다.
- 슈슈 팀도 같은 캐릭터를 쓰므로, 확정되면 슈슈 팀에 새 그림을 전달합니다.

## 만드는 법

1. 아래 **공통 문구** 뒤에 캐릭터별 문구를 붙여 넣습니다.
2. 정사각형(1:1)으로 만듭니다. 가슴 위까지 보이게(흉상), 얼굴이 화면 가운데 위쪽에 오게 합니다. 1024×1024 이상.
3. 마음에 드는 것을 골라 `league/agents/avatars/3d/<이름>.png` 로 GitHub에 올립니다(예: `3d/ttukshim.png`). 이름은 아래 표의 영문 이름입니다. B판(카지노 배경)을 만들었다면 `3d/<이름>-scene.png` 로 올립니다.
4. 올리면 Claude가 잘라서 압축하고(장당 약 30~60KB) 명패·쪼이기 창·프로필에 넣습니다.

같은 날 같은 도구로 14명을 한 번에 만들어야 화풍이 고르게 나옵니다. 도구에 "스타일 참조"나 "시드 고정" 기능이 있으면 첫 그림을 기준으로 씁니다.

## 공통 문구 (맨 앞에 붙임)

참고 그림 5장의 공통점은 다음과 같습니다. 이 점을 살렸습니다.
- 3D 애니메이션 영화 같은 질감
- 큰 눈과 과장된 얼굴
- 정장 차림
- 카드를 든 손이나 팔짱 낀 자세

**A. 명패·쪼이기 창용 (먼저 이것으로 만드세요)**

배경 없이 인물만 있어야 작은 명패(휴대폰에서 약 50px)에서도 얼굴이 또렷합니다. 참고 그림 중 흰 배경 3장과 같은 구도입니다.

리그와 맞추기 위해 **양손에 카드를 한 장씩** 들게 합니다. 왼손에는 빨간 다이아몬드(♦) 카드, 오른손에는 검은 클럽(♣) 카드입니다. 리그 화면의 한국 ♦ · 미국 ♣ 표시와 같아서, 캐릭터가 그날의 한국·미국 종목 2장을 쥔 모습이 됩니다.

```
Stylized 3D animated movie character, soft clay-like shading, big expressive eyes, exaggerated caricature proportions with a big head and stocky body, confident card-player attitude, holding one playing card in each hand at chest height: a red diamond suit card in the left hand and a black club suit card in the right hand, chest-up portrait, character centered with head in the upper half, plain pure white background, isolated, no scenery, soft studio lighting, square 1:1, high detail, original character
```

자세를 바꾸고 싶으면 `holding one playing card in each hand ...` 부분을 아래로 바꿔도 됩니다.
- 팔짱 낀 자세(흰 배경 참고 그림): `arms resting crossed on the padded edge of a casino table in the foreground, small stacks of poker chips on the table edge`

옷은 캐릭터별 문구를 따르되, 문구에 옷이 없으면 정장, 나비넥타이, 색 조끼 같은 카지노 손님 차림으로 만듭니다.

**B. 프로필·소개 화면용 (선택)**

카지노 테이블 배경까지 넣은 판입니다. 첫 참고 그림 3장과 같은 분위기입니다.

```
Stylized 3D animated movie character, soft clay-like shading, big expressive eyes, exaggerated caricature proportions, sitting at a casino baccarat table with green felt, a few poker chips and playing cards in front, warm bokeh casino lights and chandelier in the background, cinematic soft lighting, shallow depth of field, waist-up portrait, 2:3 vertical, high detail, original character
```

**빼고 싶은 것(negative prompt 칸이 있으면):**

```
photorealistic, real person, celebrity likeness, text, letters, logo, watermark, brand, extra fingers, deformed hands, nudity, cigarette
```

## 캐릭터별 문구

| 영문 이름 | 애칭 · 스타일 | 팀 |
|---|---|---|
| ttukshim | 뚝심이 · 가치형 | 로로 |
| balgul | 발굴왕 · 성장형 | 로로 |
| keun | 큰그림 · 거시형 | 로로 |
| mirae | 미래광 · 혁신형 | 로로 |
| ppittak | 삐딱이 · 역발상형 | 로로 |
| pado | 파도타기 · 모멘텀형 | 로로 대기 |
| gyesan | 계산기 · 퀀트 팩터형 | 로로 대기 |
| dandan | 단단이 · 안전마진형 | 슈슈 |
| alzza | 알짜 · 사업품질형 | 슈슈 |
| dotbogi | 돋보기 · 성장검증형 | 슈슈 |
| ssuk | 쑥쑥이 · 성장지속형 | 슈슈 |
| banjeon | 반전이 · 위험역발상형 | 슈슈 |
| nachim | 나침반 · 거시사이클형 | 슈슈 대기 |
| sunpung | 순풍 · 추세모멘텀형 | 슈슈 대기 |

로로 팀은 따뜻한 주황·갈색 옷 색, 슈슈 팀은 푸른 계열 옷 색으로 맞추면 테이블에서 팀이 바로 구분됩니다(명패 테두리 색과 같음).

### 뚝심이 (ttukshim)
```
a stubborn but kind old grandpa, completely bald shiny head, huge fluffy white walrus mustache, thick white eyebrows, NO glasses, wearing a big green turtle-shell backpack with leather straps, olive-green cardigan over a cream shirt, arms crossed confidently, warm orange-brown color accents
```

### 발굴왕 (balgul)
```
an enthusiastic treasure-hunting miner in his 30s, yellow hard hat with a glowing headlamp, light stubble, dirt smudges on cheeks, big laughing smile, blue plaid flannel shirt with orange suspenders, holding a small shiny gem nugget, warm orange-brown color accents
```

### 큰그림 (keun)
```
a cheerful absent-minded professor in his 60s, wild silver hair swept back, small white goatee, half-moon reading glasses pushed down the nose, red bow tie, brown tweed jacket with elbow patches, holding a small desk globe, warm orange-brown color accents
```

### 미래광 (mirae)
```
an excited young inventor, spiky dark purple hair, teal round workshop goggles on the forehead, white lab coat with a teal shirt, tiny glowing gadget in hand with little sparkles around, wide amazed eyes, warm orange-brown color accents
```

### 삐딱이 (ppittak)
```
a sly skeptic in his 40s, tilted black fedora with a red band, one eyebrow raised high, one eye winking, smug half smile, dark pinstripe suit with red tie, light stubble, warm orange-brown color accents
```

### 파도타기 (pado)
```
a laid-back surfer in his 20s, sun-bleached messy blond hair, tanned skin, reflective sporty sunglasses pushed on top of the head, Hawaiian shirt with wave pattern, a small surfboard leaning behind, relaxed grin, warm orange-brown color accents
```

### 계산기 (gyesan)
```
a neat number-loving analyst, perfectly combed side-parted black hair, square black-rimmed glasses, tidy white shirt with pocket protector and pens, holding a big retro calculator, focused smile, warm orange-brown color accents
```

### 단단이 (dandan)
```
a sturdy friendly knight, shiny steel helmet with the visor raised showing a round kind face, short beard, steel armor over blue tunic, holding a big round blue shield with a gold rim, calm protective smile, cool blue color accents
```

### 알짜 (alzza)
```
a sharp elegant jewelry appraiser woman in her 40s, short sleek violet bob hair, jeweler's loupe monocle over one eye, dark navy blazer with a small gem brooch, holding a sparkling cut gemstone between two fingers, confident knowing smile, cool blue color accents
```

### 돋보기 (dotbogi)
```
a curious detective, brown deerstalker hat, short tidy mustache, checked brown cape coat, holding a large magnifying glass that enlarges one eye comically, focused squint, cool blue color accents
```

### 쑥쑥이 (ssuk)
```
a bright cheerful young girl around 10 years old, short brown bob hair with a small green sprout with two leaves growing from the top of her head, freckles, big happy smile, green striped sweater, holding a tiny watering can, cool blue color accents
```

### 반전이 (banjeon)
```
a playful prankster in his 20s, hair split half black half white down the middle, mischievous wink with tongue slightly out, black and white striped shirt, holding a playing card flipping in the air, cool blue color accents
```

### 나침반 (nachim)
```
a wise old sea captain, white captain's cap, full white beard, navy double-breasted coat with gold buttons, brass compass hanging from a chain on the chest, calm weathered smile, cool blue color accents
```

### 순풍 (sunpung)
```
a lively young sailor woman, long auburn hair blowing sideways in the wind, white sailor shirt with a blue collar and red neckerchief, rope coil over her shoulder, bright determined smile, cool blue color accents
```

## 바뀌는 점 (2D 캐릭터와 비교)

- 알짜·쑥쑥이·순풍을 여성 캐릭터로 바꿔 14명의 성별을 섞었습니다. 기존 2D 캐릭터와 소품(돋보기, 새싹, 바람에 날리는 머리 등)은 그대로라 누군지 알아볼 수 있습니다.
- 뚝심이는 실존 가치투자자를 떠올리지 않게 안경을 빼고 큰 흰 콧수염을 넣었습니다.
- 미래광은 혁신 투자로 유명한 실존 인물을 떠올리지 않게 젊은 남성 발명가로 둡니다.
