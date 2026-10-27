# Comandos do ambiente local. Uso: make <alvo> [ANO_MES=AAAA-MM]
ANO_MES ?= 2026-09
PY := .venv/bin/python
S3_LOCAL := S3_ENDPOINT=http://localhost:9000 AWS_ACCESS_KEY_ID=goodlion AWS_SECRET_ACCESS_KEY=goodlion123 AWS_REGION=us-east-1

.PHONY: setup up down test lint ingest amostra

setup:  ## cria o .venv com as dependências de desenvolvimento
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt

up:  ## sobe MinIO, Postgres, Metabase (localhost:3001) e o container do Glue
	docker compose up -d

down:
	docker compose down

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check .

ingest:  ## baixa o mês da Receita para o bucket raw do MinIO
	$(S3_LOCAL) $(PY) -m ingest.receita --ano_mes $(ANO_MES) --bucket raw

amostra:  ## gera a amostra AC/AP/RR do mês em raw/sample/
	$(S3_LOCAL) $(PY) -m amostra.gerar_amostra --ano_mes $(ANO_MES)
