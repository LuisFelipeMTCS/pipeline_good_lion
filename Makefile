# Comandos do ambiente local. Uso: make <alvo> [ANO_MES=AAAA-MM]
ANO_MES ?= 2026-09
# Variáveis do .env (credenciais do MinIO, endpoint S3). Crie com: cp .env.example .env
PY := uv run --env-file .env python

.PHONY: setup up down test lint ingest amostra

setup:  ## cria o .venv e instala as dependências travadas no uv.lock
	uv sync

up:  ## sobe MinIO, Postgres, Metabase (localhost:3001) e o container do Glue
	docker compose up -d

down:
	docker compose down

test:
	uv run --env-file .env pytest -q

lint:
	uv run ruff check .

ingest:  ## baixa o mês da Receita para o bucket raw do MinIO
	$(PY) -m ingest.receita --ano_mes $(ANO_MES) --bucket raw

amostra:  ## gera a amostra AC/AP/RR do mês em raw/sample/
	$(PY) -m amostra.gerar_amostra --ano_mes $(ANO_MES)
