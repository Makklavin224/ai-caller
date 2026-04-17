#!/usr/bin/env bash
# Trigger outbound call via UIS trunk; on answer Asterisk runs [outbound-bot] → AudioSocket → Pipecat.
# Usage: ./scripts/originate.sh 79001234567
set -euo pipefail
NUM="${1:?Usage: $0 <phone-number-without-plus>}"
CID="${UIS_CALLER_ID:-}"

echo "→ Originating PJSIP/${NUM}@uis-endpoint  (CID=${CID:-<endpoint default>})"
docker compose exec -T asterisk asterisk -rx \
  "channel originate PJSIP/${NUM}@uis-endpoint extension s@outbound-bot"
