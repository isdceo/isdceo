# 운영 현황판 페이지 사본

`operator-dashboard-page.html`은 운영자 전용 현황판(claude.ai 비공개 대시보드)의 페이지 코드 사본(한 파일)이다. 현황판 문서 하나는 256KB까지라, 올릴 때는 `python3 tools/dashboard_split.py --out <폴더>`로 `index.html`(화면·캐릭터 그림)·`style.css`·`app.js` 세 파일로 나눠 대시보드 저장소의 `files/`에 각각 올린다(2026-11-07부터). 게임 화면 빌드(`league/play/build.py`, `tools/build_play.py`)는 이 한 파일 사본을 읽는다.
- 현황판용 데이터 파일(`dashboard_data.py --out`)은 줄바꿈·들여쓰기 없이 압축해 쓴다.

- 데이터는 `tools/dashboard_data.py`가 만든다(마감 전 종목·원 가격 제외).
- 탭: 운영 / 테이블(반원 바카라 테이블, 캐릭터 10명, 출목표, 선수 카드, 대기석) / 팀 대결 / 리그 순위 / 추천·점수
- 캐릭터는 `league/agents/avatars/`의 창작 캐릭터(실존 인물과 무관). 카지노 테이블은 화면 연출이며 돈·베팅 요소는 없다.
- 이 파일은 기록용 사본이다. 현황판에서 직접 고친 내용이 있으면 이 사본이 뒤처질 수 있다.
