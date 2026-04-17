# Voice bot Vectra — dev ops shortcuts.
# Prereq on VPS: docker + docker compose plugin, .env filled from .env.example.

.PHONY: build up down restart logs logs-asterisk logs-bot status originate shell-asterisk shell-bot

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

logs-asterisk:
	docker compose logs -f --tail=200 asterisk

logs-bot:
	docker compose logs -f --tail=200 bot

# Check UIS trunk registration + endpoints.
status:
	./scripts/check-trunk.sh

# Usage: make originate NUM=79001234567
originate:
	./scripts/originate.sh $(NUM)

# Interactive Asterisk CLI.
shell-asterisk:
	docker compose exec asterisk asterisk -rvvv

shell-bot:
	docker compose exec bot /bin/bash
