#!/usr/bin/env bash
set -euo pipefail

: "${UIS_SIP_HOST:?UIS_SIP_HOST is required}"
: "${UIS_SIP_USER:?UIS_SIP_USER is required}"
: "${UIS_SIP_PASSWORD:?UIS_SIP_PASSWORD is required}"

mkdir -p /etc/asterisk
envsubst < /etc/asterisk-template/pjsip.conf.template > /etc/asterisk/pjsip.conf
cp /etc/asterisk-template/extensions.conf /etc/asterisk/extensions.conf

exec asterisk -f -vvv
