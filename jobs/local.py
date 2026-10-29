"""Executor local dos jobs: lê/grava Delta (pasta local ou MinIO) e roda os mesmos .sql do Glue Studio.

Cada job `<camada>_<tabela>` roda jobs/sql/<camada>/<tabela>.sql. A view de entrada tem o nome do
alias do nó de origem no Glue Studio (raw_estabelecimentos, bronze_estabelecimentos...).
"""
from pathlib import Path

from pyspark.sql import functions as F

PASTA_SQL = Path(__file__).parent / "sql"


def _sql(spark, arquivo, **entradas):
    for alias, df in entradas.items():
        df.createOrReplaceTempView(alias)
    return spark.sql((PASTA_SQL / f"{arquivo}.sql").read_text(encoding="utf-8"))


def _ler_delta(spark, caminho, ano_mes):
    return spark.read.format("delta").load(caminho).where(F.col("ano_mes") == ano_mes)


def _gravar_delta(df, caminho, ano_mes):
    # Idempotência: só a partição do mês é substituída.
    (
        df.write.format("delta")
        .mode("overwrite")
        .partitionBy("ano_mes")
        .option("replaceWhere", f"ano_mes = '{ano_mes}'")
        .save(caminho)
    )


def bronze_estabelecimentos(spark, origem, destino, ano_mes):
    raw = (
        spark.read.option("header", True)
        .option("sep", ";")
        .option("quote", '"')
        .csv(f"{origem}/estabelecimentos/ano_mes={ano_mes}/")
        # No Glue a coluna vem da partição do Catalog; aqui é acrescentada à mão.
        .withColumn("ano_mes", F.lit(ano_mes))
    )
    saida = _sql(spark, "bronze/estabelecimentos", raw_estabelecimentos=raw)
    _gravar_delta(saida, f"{destino}/estabelecimentos", ano_mes)


def silver_estabelecimentos(spark, origem, destino, ano_mes):
    entrada = _ler_delta(spark, f"{origem}/estabelecimentos", ano_mes)
    saida = _sql(spark, "silver/estabelecimentos", bronze_estabelecimentos=entrada)
    _gravar_delta(saida, f"{destino}/estabelecimentos", ano_mes)


def gold_ativas_por_uf(spark, origem, destino, ano_mes):
    entrada = _ler_delta(spark, f"{origem}/estabelecimentos", ano_mes)
    saida = _sql(spark, "gold/ativas_por_uf", silver_estabelecimentos=entrada)
    _gravar_delta(saida, f"{destino}/ativas_por_uf", ano_mes)


# Na ordem em que rodam. O bucket de origem é o da camada anterior.
JOBS = {
    "bronze_estabelecimentos": bronze_estabelecimentos,
    "silver_estabelecimentos": silver_estabelecimentos,
    "gold_ativas_por_uf": gold_ativas_por_uf,
}
CAMADA_ANTERIOR = {"bronze": "raw", "silver": "bronze", "gold": "silver"}


def main(argv=None):
    """Roda os jobs no container do Glue contra o MinIO: s3a://<bucket da camada>/[sample/]<tabela>/..."""
    import argparse

    from jobs.spark import criar_spark

    parser = argparse.ArgumentParser(description="Roda os jobs do pipeline localmente.")
    parser.add_argument("--ano_mes", required=True, help="AAAA-MM")
    parser.add_argument("--ambiente", default="sample", choices=["sample", "full"])
    parser.add_argument("--jobs", default=",".join(JOBS), help="lista separada por vírgula; padrão = todos")
    args = parser.parse_args(argv)

    # Amostra no prefixo sample/; base completa na raiz do bucket.
    prefixo = "/sample" if args.ambiente == "sample" else ""
    spark = criar_spark()
    for nome in args.jobs.split(","):
        camada = nome.split("_", 1)[0]
        JOBS[nome](spark, f"s3a://{CAMADA_ANTERIOR[camada]}{prefixo}", f"s3a://{camada}{prefixo}", args.ano_mes)


if __name__ == "__main__":
    main()
