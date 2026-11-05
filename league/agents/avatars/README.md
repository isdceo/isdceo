# 에이전트 캐릭터

애칭에 맞춘 **창작 캐리커처 캐릭터**입니다(큰 머리, 과장된 눈·코·웃음, 굵은 외곽선과 명암). 실존 투자자와 관계없고, 누구의 얼굴도 본뜨지 않았습니다(리그 규칙: 실존 인물의 추천처럼 보이게 하지 않음).

- `characters.html`: 14명 SVG 정의(`#av-<이름>`, viewBox 0 0 120 120)와 미리보기. 현황판 페이지에 같은 정의가 들어 있다.
- `characters.png`: 미리보기 캡처.
- 명단 파일의 `avatar` 값이 캐릭터 이름이다 (`league/agents/roster.json`, `league/imports/shushu/roster.json`).

| 이름 | 애칭 | 캐릭터 |
|---|---|---|
| ttukshim | 뚝심이 | 거북이 등껍질 배낭을 멘 대머리 할아버지 |
| balgul | 발굴왕 | 헤드랜턴 안전모의 광부 |
| keun | 큰그림 | 지구본을 든 은발 교수(반달 안경, 나비넥타이) |
| mirae | 미래광 | 고글 쓴 발명가 |
| ppittak | 삐딱이 | 비스듬한 중절모의 회의론자 |
| pado | 파도타기 | 선글라스 서퍼 |
| gyesan | 계산기 | 네모 안경에 계산기를 든 숫자광 |
| dandan | 단단이 | 방패 든 기사 |
| alzza | 알짜 | 보석 감정사 |
| dotbogi | 돋보기 | 돋보기 든 탐정 |
| ssuk | 쑥쑥이 | 머리에 새싹 난 아이 |
| banjeon | 반전이 | 흑백 반반 머리의 장난꾸러기 |
| nachim | 나침반 | 나침반 목걸이의 선장 |
| sunpung | 순풍 | 바람에 머리가 날리는 선원 |

그림은 `src/`의 생성기로 만든 SVG입니다(`gen.py` 공통 얼굴 틀, `chars.py` 캐릭터별 머리·모자·소품). `src/` 안에서 `python3 chars.py`를 실행하면 `defs.svg`(현황판에 넣는 정의)와 `preview.html`이 나온다. 현황판 페이지(`docs/dashboard/operator-dashboard-page.html`)의 정의와 같다.
