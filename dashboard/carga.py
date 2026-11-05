"""Carga do dashboard (PRD, seção 9): Gold (Delta) → Postgres → visões materializadas do Metabase."""
from pathlib import Path

import psycopg
import pyarrow.dataset as ds
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

ESQUEMA = Path(__file__).with_name("schema.sql")
FATO = (
    "ano_mes", "cnpj_basico", "id_municipio_rf", "id_categoria", "id_cnae", "id_natureza_juridica",
    "data_inicio_atividade", "capital_social", "qtd_estabelecimentos",
)
MOVIMENTACAO = ("ano_mes", "cnpj_basico", "tipo_evento", "id_municipio_rf", "id_categoria")
DIMENSOES = {
    "dim_municipio": ("id_municipio_rf", "id_municipio_ibge", "nome", "sigla_uf", "regiao"),
    "dim_categoria": ("id_categoria", "nome", "ordem"),
}
VISOES = (
    "mv_categorias_municipio", "mv_categorias_uf", "mv_categorias_regiao",
    "mv_capital_municipio", "mv_capital_uf", "mv_capital_regiao",
    "mv_movimentacao_municipio", "mv_movimentacao_uf", "mv_movimentacao_regiao",
)


def _copiar(conexao, tabela, colunas, lotes):
    with conexao.cursor().copy(f"COPY {tabela} ({', '.join(colunas)}) FROM STDIN") as copia:
        for lote in lotes:
            for linha in zip(*(lote.column(coluna).to_pylist() for coluna in colunas)):
                copia.write_row(linha)


def carregar_mes(gold, ano_mes, conninfo, storage_options=None):
    def ler(tabela, colunas, ano_mes=None):
        """Lotes do Arrow, sem trazer a tabela inteira para a memória: na base completa a fato do mês tem
        dezenas de milhões de linhas."""
        conjunto = DeltaTable(f"{gold}/{tabela}", storage_options=storage_options).to_pyarrow_dataset()
        filtro = (ds.field("ano_mes") == ano_mes) if ano_mes else None
        return conjunto.to_batches(columns=list(colunas), filter=filtro, batch_size=200_000)

    try:
        DeltaTable(f"{gold}/fato_movimentacao_empresa", storage_options=storage_options)
        movimentacao = ler("fato_movimentacao_empresa", MOVIMENTACAO, ano_mes)
    except TableNotFoundError:  # antes do primeiro MERGE com mudanças a tabela ainda não existe
        movimentacao = []
    with psycopg.connect(conninfo) as conexao:
        conexao.execute(ESQUEMA.read_text(encoding="utf-8"))
        # Idempotência: tudo numa transação; o mês da fato é apagado e reinserido, as dimensões inteiras.
        for tabela, colunas in DIMENSOES.items():
            conexao.execute(f"DELETE FROM {tabela}")
            _copiar(conexao, tabela, colunas, ler(tabela, colunas))
        conexao.execute("DELETE FROM fato_empresa_mensal WHERE ano_mes = %s", [ano_mes])
        _copiar(conexao, "fato_empresa_mensal", FATO, ler("fato_empresa_mensal", FATO, ano_mes))
        conexao.execute("DELETE FROM fato_movimentacao_empresa WHERE ano_mes = %s", [ano_mes])
        _copiar(conexao, "fato_movimentacao_empresa", MOVIMENTACAO, movimentacao)
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
