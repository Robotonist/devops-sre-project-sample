COMPOSE ?= docker compose
PYTHON ?= python

.PHONY: init build up down logs migrate test lint check ps reset

init:
	@test -f .env || cp .env.example .env

build: init
	$(COMPOSE) build

up: init
	$(COMPOSE) up -d --build

ps:
	$(COMPOSE) ps

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

migrate: init
	$(COMPOSE) run --rm migrate

test:
	$(PYTHON) -m pytest tests -v

lint:
	ruff check app tests

check: test lint

reset:
	$(COMPOSE) down -v --remove-orphans
