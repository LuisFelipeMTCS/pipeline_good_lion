"""Gera a amostra de desenvolvimento (PRD, seção 9): recorte de AC, AP e RR com joins consistentes.

Lê e grava no mesmo layout do raw (<tabela>/ano_mes=AAAA-MM/*.csv), em disco local ou s3://.
"""
import os

import duckdb

from ingest.receita import DOMINIOS

UFS_AMOSTRA = ("AC", "AP", "RR")


def gerar_amostra(origem, destino, ano_mes, ufs=UFS_AMOSTRA, con=None):
    con = con or duckdb.connect()

    def ler(tabela):
        return (
            f"read_csv('{origem}/{tabela}/ano_mes={ano_mes}/*.csv', "
            # hive_partitioning=false: sem isso o DuckDB cria a coluna ano_mes a partir da pasta.
            "delim=';', quote='\"', header=true, all_varchar=true, hive_partitioning=false)"
        )

    def gravar(tabela, consulta):
        pasta = f"{destino}/{tabela}/ano_mes={ano_mes}"
        if "://" not in pasta:
            os.makedirs(pasta, exist_ok=True)
        con.execute(
            f"COPY ({consulta}) TO '{pasta}/{tabela}.csv' "
            "(HEADER, DELIMITER ';', QUOTE '\"', FORCE_QUOTE *)"
        )

    lista_ufs = ", ".join(f"'{uf}'" for uf in ufs)
    con.execute(
        "CREATE OR REPLACE TEMP TABLE estab_amostra AS "
        f"SELECT * FROM {ler('estabelecimentos')} WHERE sigla_uf IN ({lista_ufs})"
    )
    gravar("estabelecimentos", "SELECT * FROM estab_amostra")
    for tabela in ("empresas", "simples"):
        gravar(
            tabela,
            f"SELECT * FROM {ler(tabela)} "
            "WHERE cnpj_basico IN (SELECT cnpj_basico FROM estab_amostra)",
        )
    for dominio in DOMINIOS:
        gravar(dominio, f"SELECT * FROM {ler(dominio)}")


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Gera a amostra AC/AP/RR de um mês do raw.")
    parser.add_argument("--ano_mes", required=True, help="AAAA-MM")
    parser.add_argument("--origem", default="s3://raw")
    parser.add_argument("--destino", default="s3://raw/sample")
    args = parser.parse_args(argv)

    con = duckdb.connect()
    endpoint = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
    con.execute(
        "CREATE SECRET minio (TYPE s3, KEY_ID ?, SECRET ?, ENDPOINT ?, URL_STYLE 'path', USE_SSL ?)",
        [
            os.environ.get("AWS_ACCESS_KEY_ID", "goodlion"),
            os.environ.get("AWS_SECRET_ACCESS_KEY", "goodlion123"),
            endpoint.split("://", 1)[-1],
            endpoint.startswith("https"),
        ],
    )
    gerar_amostra(args.origem, args.destino, args.ano_mes, con=con)


if __name__ == "__main__":
    main()
