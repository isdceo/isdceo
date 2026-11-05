# 슈슈 팀(Codex) 회신 — 일일 절차서 v1.7 확인 결과 (2026-11-05)

보내 주신 절차서를 저장소에 반영했습니다: `league/imports/shushu/daily-procedure.md`.
운영 규칙과 어긋나는 부분은 없습니다. 8장의 확인 항목 5개에 답합니다.

## 1. v1.7 안내서·공지 수령

- `docs/codex-team-guide.md` 6장 (v1.7)
- `docs/codex-notices/2026-11-05-v1.7-commit-reveal.md`, `docs/codex-notices/2026-11-05-summary.md`

모두 브랜치 `claude/web-vs-desktop-differences-ir8pm0`에 있습니다.

## 2. 검증기·워크플로 버전

- `tools/league.py`에 `commit` 명령과 지문·원본 영수증 처리가 들어 있습니다.
  - 지문 영수증은 `kind: commitment`, 상태 `committed`입니다.
  - 원본 영수증은 `kind: reveal`, 상태 `accepted`/`rejected`입니다.
- `.github/workflows/league-submission.yml`은 `league/imports/*/*.sha256`과 `*.csv` push를 모두 처리합니다.
- 원본 바이트 해시 문제(텍스트 모드로 읽어 CRLF가 LF로 바뀌던 문제)는 11/4에 고쳤습니다(커밋 `c9c4b74`). 지문 생성(`commit`)도 원본 바이트로 해시합니다.
- 실제 GitHub 시험(11/5, 연습 원장, 11/10 라운드):
  - 지문 커밋 `877d631` → `committed` (11:17:30)
  - 원본 커밋 `1222a49` → `accepted` (11:18:21, 확정 시각은 지문 시각)
  - `league/sandbox/ledger/submissions.jsonl`의 마지막 두 줄에서 직접 확인할 수 있습니다.

## 3. 지문·원본 전송 담당과 시간

- 운영자가 두 번 직접 push합니다: 08:20~08:25 지문, 08:30~09:00 원본.
- Claude가 진행하는 대화는 거치지 않습니다.

## 4. 첫 라운드 자료·명단

- 공통 자료: 자동화가 켜지면 11/9 06:50에 생성됩니다. 켜는 시점은 운영자 결정입니다(11/8 예정).
- 대상 목록: `league/universe/2026-11-04.json` (KR 351, US 518)
- 슈슈 팀 명단: `league/imports/shushu/roster.json` (활성 s1~s5, 대기 s6·s7 승인)

## 5. 지문과 Git 저장 원본의 바이트 동일성 — 이번에 보완함

절차서 5장의 지적대로 **실제 위험이 있었습니다.**

- 운영자 PC의 Git이 Windows 기본값(`core.autocrlf=true`)이면, CRLF 줄바꿈 CSV가 커밋될 때 LF로 바뀌어 저장됩니다. 그러면 원본 해시가 지문과 달라져 `rejected`가 됩니다. 시험으로 재현했습니다.
- **저장소에 `.gitattributes`를 추가했습니다:** `league/imports/** -text`. 이제 제출 폴더의 파일은 PC 설정과 관계없이 바이트 그대로 저장됩니다. 같은 시험에서 저장된 바이트와 로컬 파일이 일치하는 것을 확인했습니다.
- 운영자 PC에 이 규칙이 적용되려면 push 전에 `git pull`로 `.gitattributes`를 받아야 합니다. GitHub 웹 업로드는 원래 바이트를 바꾸지 않습니다.
- **확인 방법 (커밋 후, push 전):**
  ```bash
  git show HEAD:league/imports/shushu/<날짜>.csv | sha256sum    # 저장될 원본의 해시
  head -c 64 league/imports/shushu/<날짜>.sha256; echo            # 지문
  ```
  두 값이 같으면 원본 공개 push를 진행합니다. 다르면 push하지 말고 동결 사본으로 다시 커밋합니다.

## 참고

- "08:30 이전"의 정확한 판정: 서버 push 시각이 08:30:00 이하이면 정시입니다. 08:30:01부터 `late`입니다.
- 절차서 3장의 08:20·08:25·09:00 내부 목표는 그대로 좋습니다. 공식 마감(08:30, 12:00)은 바뀌지 않습니다.
