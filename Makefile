COMPOSE ?= docker compose
DEV_RUN = $(COMPOSE) run --rm --build --no-deps dev

.PHONY: init build up down logs migrate test lint check smoke infra-check ps reset

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

test: init
	$(DEV_RUN) python -m pytest tests -v

lint: init
	$(DEV_RUN) ruff check app tests

check: init
	$(DEV_RUN) sh -c "python -m pytest tests -v && ruff check app tests && cd ansible && ansible-playbook -i inventory/ci.ini deploy.yml --syntax-check && ansible-lint --project-dir . ."

smoke: init
	$(COMPOSE) run --rm --build --no-deps \
		-e SMOKE_BASE_URL=http://api:8000 \
		dev python -m pytest tests/integration/test_vertical_slice.py -v

reset:
	$(COMPOSE) down -v --remove-orphans

infra-check: init
	$(DEV_RUN) sh -c "cd ansible && ansible-playbook -i inventory/ci.ini deploy.yml --syntax-check && ansible-lint --project-dir . ."

deploy:
	ansible-playbook -i ansible/inventory/local.ini ansible/deploy.yml

verify-appliance:
	ansible-playbook -i ansible/inventory/local.ini ansible/verify.yml
