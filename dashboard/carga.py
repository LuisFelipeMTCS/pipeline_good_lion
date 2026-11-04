"""Carga do dashboard (PRD, seção 9): Gold (Delta) → Postgres → visões materializadas do Metabase."""
from pathlib import Path

import psycopg
from deltalake import DeltaTable

ESQUEMA = Path(__file__).with_name("schema.sql")
FATO = (
    "ano_mes", "cnpj_basico", "id_municipio_rf", "id_categoria", "id_cnae", "id_natureza_juridica",
    "data_inicio_atividade", "capital_social", "qtd_estabelecimentos",
)
DIMENSOES = {
    "dim_municipio": ("id_municipio_rf", "id_municipio_ibge", "nome", "sigla_uf", "regiao"),
    "dim_categoria": ("id_categoria", "nome", "ordem"),
}
VISOES = (
    "mv_categorias_municipio", "mv_categorias_uf", "mv_categorias_regiao",
    "mv_capital_municipio", "mv_capital_uf", "mv_capital_regiao",
)


def _copiar(conexao, tabela, colunas, linhas):
    with conexao.cursor().copy(f"COPY {tabela} ({', '.join(colunas)}) FROM STDIN") as copia:
        for linha in linhas:
            copia.write_row([linha[coluna] for coluna in colunas])


def carregar_mes(gold, ano_mes, conninfo, storage_options=None):
    def ler(tabela, colunas, filtros=None):
        delta = DeltaTable(f"{gold}/{tabela}", storage_options=storage_options)
        return delta.to_pyarrow_table(filters=filtros, columns=list(colunas)).to_pylist()

    fato = ler("fato_empresa_mensal", FATO, [("ano_mes", "=", ano_mes)])
    dimensoes = {tabela: ler(tabela, colunas) for tabela, colunas in DIMENSOES.items()}
    with psycopg.connect(conninfo) as conexao:
        conexao.execute(ESQUEMA.read_text(encoding="utf-8"))
        # Idempotência: tudo numa transação; o mês da fato é apagado e reinserido, as dimensões inteiras.
        for tabela, colunas in DIMENSOES.items():
            conexao.execute(f"DELETE FROM {tabela}")
            _copiar(conexao, tabela, colunas, dimensoes[tabela])
        conexao.execute("DELETE FROM fato_empresa_mensal WHERE ano_mes = %s", [ano_mes])
        _copiar(conexao, "fato_empresa_mensal", FATO, fato)
        for visao in VISOES:
            conexao.execute(f"REFRESH MATERIALIZED VIEW {visao}")


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
