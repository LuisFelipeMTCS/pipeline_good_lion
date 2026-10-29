# Comandos do ambiente local. Uso: make <alvo> [ANO_MES=AAAA-MM]
ANO_MES ?= 2026-09
TABELAS ?=
# Variáveis do .env (credenciais do MinIO, endpoint S3). Crie com: cp .env.example .env
PY := uv run --env-file .env python

.PHONY: setup up down test test-spark lint ingest amostra amostra-aws pipeline dashboard-load deploy-jobs

setup:  ## cria o .venv e instala as dependências travadas no uv.lock
	uv sync

up:  ## sobe MinIO, Postgres, Metabase (localhost:3001) e o container do Glue
	docker compose up -d

down:
	docker compose down

test:
	uv run --env-file .env pytest -q

test-spark:  ## testes que precisam de Spark, dentro do container do Glue
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 glue python3 -m pytest -q -p no:cacheprovider tests/test_pipeline_estabelecimentos.py tests/test_gravar_delta.py

lint:
	uv run ruff check .

ingest:  ## baixa o mês da Receita para o raw do MinIO (TABELAS=simples,cnaes restringe)
	$(PY) -m ingest.receita --ano_mes $(ANO_MES) --bucket raw --tabelas "$(TABELAS)"

amostra:  ## gera a amostra AC/AP/RR do mês em raw/sample/
	$(PY) -m amostra.gerar_amostra --ano_mes $(ANO_MES)

amostra-aws:  ## envia a amostra do MinIO para s3://goodlion-raw-<conta>/sample/ (perfil default da AWS)
	rm -rf /tmp/goodlion-amostra
	uv run --env-file .env sh -c 'aws --endpoint-url "$$S3_ENDPOINT" s3 sync s3://raw/sample /tmp/goodlion-amostra'
	aws s3 sync --delete /tmp/goodlion-amostra s3://goodlion-raw-$$(aws sts get-caller-identity --query Account --output text)/sample
	rm -rf /tmp/goodlion-amostra

pipeline:  ## bronze → silver → gold de Estabelecimentos da amostra, no container do Glue
	docker compose exec -T glue python3 -m jobs.local --ano_mes $(ANO_MES)

dashboard-load:  ## carrega o mês da Gold no Postgres e atualiza as visões do Metabase
	$(PY) -m dashboard.carga --ano_mes $(ANO_MES)

deploy-jobs:  ## publica os jobs visuais de glue/jobs/ na AWS (perfil default; sem o .env, que é do MinIO)
	uv run python scripts/deploy_jobs.py
