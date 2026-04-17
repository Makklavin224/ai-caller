#!/usr/bin/env bash
set -euo pipefail

echo "=== PJSIP registrations (UIS trunk must be 'Registered') ==="
docker compose exec -T asterisk asterisk -rx "pjsip show registrations"
echo
echo "=== PJSIP endpoints ==="
docker compose exec -T asterisk asterisk -rx "pjsip show endpoints"
echo
echo "=== PJSIP transports ==="
docker compose exec -T asterisk asterisk -rx "pjsip show transports"
