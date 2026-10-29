"""Carga do dashboard (PRD, seção 9): Gold (Delta) → Postgres → visões materializadas do Metabase."""
from pathlib import Path

import psycopg
from deltalake import DeltaTable

ESQUEMA = Path(__file__).with_name("schema.sql")
COLUNAS = ("ano_mes", "sigla_uf", "qtd_empresas_ativas")


def carregar_mes(gold, ano_mes, conninfo, storage_options=None):
    tabela = DeltaTable(f"{gold}/ativas_por_uf", storage_options=storage_options).to_pyarrow_table(
        filters=[("ano_mes", "=", ano_mes)], columns=list(COLUNAS)
    )
    with psycopg.connect(conninfo) as conexao:
        conexao.execute(ESQUEMA.read_text(encoding="utf-8"))
        # Idempotência: o mês é apagado e reinserido na mesma transação.
        conexao.execute("DELETE FROM ativas_por_uf WHERE ano_mes = %s", [ano_mes])
        with conexao.cursor().copy(f"COPY ativas_por_uf ({', '.join(COLUNAS)}) FROM STDIN") as copia:
            for linha in tabela.to_pylist():
                copia.write_row([linha[coluna] for coluna in COLUNAS])
        conexao.execute("REFRESH MATERIALIZED VIEW mv_ativas_por_uf")


def main(argv=None):
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Carrega um mês da Gold no Postgres do dashboard.")
    parser.add_argument("--ano_mes", required=True, help="AAAA-MM")
    parser.add_argument("--gold", default="s3://gold/sample")
    args = parser.parse_args(argv)

    # S3_ENDPOINT aponta para o MinIO; na AWS fica vazio e vale o perfil `analista` (AWS_PROFILE).
    storage_options = None
    if os.environ.get("S3_ENDPOINT"):
        storage_options = {
            "AWS_ENDPOINT_URL": os.environ["S3_ENDPOINT"],
            "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
            "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
            "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1"),
            "AWS_ALLOW_HTTP": "true",
        }
    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} port=5432 dbname=dashboard "
        f"user={os.environ['POSTGRES_USER']} password={os.environ['POSTGRES_PASSWORD']}"
    )
    carregar_mes(args.gold, args.ano_mes, conninfo, storage_options)


if __name__ == "__main__":
    main()
