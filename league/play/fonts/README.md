# 게임 화면 글꼴 (사이트에 함께 올림)

외부(Google Fonts) 요청 없이 화면을 띄우려고 글꼴 파일을 함께 둔다.

| 글꼴 | 쓰는 곳 | 저작권 | 라이선스 |
|---|---|---|---|
| Do Hyeon(도현) | 제목·이름표·점수·말풍선·버튼 | Copyright 2018 The Do Hyeon Project Authors | SIL Open Font License 1.1 |
| Noto Sans KR 400·700 | 작은 안내 글씨 | (c) 2014-2021 Adobe, with Reserved Font Name 'Source' | SIL Open Font License 1.1 |

- 라이선스 전문: https://openfontlicense.org/open-font-license-official-text/
- Google Fonts에서 받은 웹 글꼴을 글자 범위로 나눈 것이다(한글 KS X 1001 2,350자 + 영문·기호, 글꼴마다 5개 파일). 글꼴 이름은 원래 이름 그대로 쓴다.
- 이 범위 밖의 드문 글자는 기기의 기본 글꼴로 보인다.
- `fonts.css`가 글자 범위(unicode-range)별로 파일을 연결하므로, 화면에 실제로 쓰인 글자가 든 파일만 내려받는다.
