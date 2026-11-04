# 연습 영수증 해시 기준 정정 메모 (2026-11-04)

아래 두 연습 영수증(`league/sandbox/ledger/submissions.jsonl`)의 `csv_sha256`은 제출 파일의 원본 바이트가 아니라
**줄 끝(CRLF)을 LF로 바꾼 내용**의 SHA-256이다. 영수증 기능이 파일을 텍스트 모드로 읽은 버그 때문이며,
원장은 수정할 수 없으므로 이 메모로 남긴다. 판정(accepted)과 서버 push 시각에는 영향이 없다.

| 팀 | 라운드 | 커밋 | 영수증 기록 해시 (LF 변환) | 원본 파일 해시 (CRLF) |
|---|---|---|---|---|
| sandbox-claude | 2026-11-05 | 3330048 | dd7fbafdd7a2… | 6602d1927d55… |
| sandbox-shushu | 2026-11-06 | bbc2d5c | 7af282693968… | 41172f9dd95bb4682a31adbbd3f338b3a3825fe917f5150c03bfed336a014fec |

- 슈슈 팀이 보고한 CSV 해시(41172f9d…)는 원본 파일 해시와 일치한다.
- 수정: 이후 영수증은 원본 바이트 그대로 해시한다 (tools/league.py process_push, CRLF 파일 테스트 추가).
