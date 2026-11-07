#!/usr/bin/env bash
# 제출 영수증 처리(league-submission 워크플로용). 늘 최신 원장(origin) 위에서 판정한다.
# 지문 영수증이 아직 원장에 없어 판정을 미룬 경우(종료 코드 75) 잠시 기다렸다 최신 원장을 받아 다시 처리한다.
#   tools/receipt_retry.sh <run_id> <run_url> <run_created_at>   → receipt.txt 에 결과
set -uo pipefail
for i in $(seq 1 15); do
  git fetch -q origin "$GITHUB_REF_NAME"
  git reset -q --hard "origin/$GITHUB_REF_NAME"
  python3 tools/league.py receipt "$GITHUB_EVENT_PATH" --run-id "$1" --run-url "$2" --run-created-at "$3" > receipt.txt
  rc=$?
  cat receipt.txt
  [ "$rc" -ne 75 ] && exit "$rc"
  echo "지문 영수증 기다리는 중 ($i/15)"; sleep 20
done
echo "::error::지문 파일은 있는데 5분이 지나도 지문 영수증이 기록되지 않음 — 지문 push의 league-submission 실행을 확인한 뒤 이 실행을 다시 돌릴 것"
exit 1
