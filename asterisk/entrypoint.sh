#!/usr/bin/env bash
set -euo pipefail

: "${UIS_SIP_HOST:?UIS_SIP_HOST is required}"
: "${UIS_SIP_USER:?UIS_SIP_USER is required}"
: "${UIS_SIP_PASSWORD:?UIS_SIP_PASSWORD is required}"

PJSIP_TEMPLATE="${ASTERISK_PJSIP_TEMPLATE:-/etc/asterisk-template/pjsip.conf.template}"
EXTENSIONS_TEMPLATE="${ASTERISK_EXTENSIONS_TEMPLATE:-/etc/asterisk-template/extensions.conf}"

if [ ! -f "${PJSIP_TEMPLATE}" ]; then
  echo "Missing PJSIP template: ${PJSIP_TEMPLATE}" >&2
  exit 1
fi

if [ ! -f "${EXTENSIONS_TEMPLATE}" ]; then
  echo "Missing extensions template: ${EXTENSIONS_TEMPLATE}" >&2
  exit 1
fi

mkdir -p /etc/asterisk
envsubst < "${PJSIP_TEMPLATE}" > /etc/asterisk/pjsip.conf
cp "${EXTENSIONS_TEMPLATE}" /etc/asterisk/extensions.conf

exec asterisk -f -vvv
