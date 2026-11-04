"""Executor local dos jobs: lê/grava Delta (pasta local ou MinIO) e roda os mesmos .sql do Glue Studio.

Cada job `<camada>_<tabela>` roda jobs/sql/<camada>/<tabela>.sql. A view de entrada tem o nome do
alias do nó de origem no Glue Studio (raw_estabelecimentos, bronze_estabelecimentos...).
"""
from pathlib import Path

from pyspark.sql import functions as F

from ingest.receita import DOMINIOS

PASTA_SQL = Path(__file__).parent / "sql"
CORRECOES_MUNICIPIOS = Path(__file__).parent / "referencias" / "municipios_correcoes.csv"


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


def _camada(caminho, camada):
    """Mesmo caminho em outro bucket: s3a://silver/sample -> s3a://bronze/sample (ou .../silver -> .../bronze)."""
    partes = caminho.split("/")
    for i in range(len(partes) - 1, -1, -1):
        if partes[i] in CAMADA_ANTERIOR.values() or partes[i] in CAMADA_ANTERIOR:
            partes[i] = camada
            return "/".join(partes)
    raise ValueError(f"caminho sem camada: {caminho}")


def _sem_amostra(caminho):
    # O IBGE não tem recorte de amostra: fica na raiz do bucket, como na AWS.
    return caminho.removesuffix("/sample")


def _ler_raw(spark, origem, tabela, ano_mes):
    return (
        spark.read.option("header", True)
        .option("sep", ";")
        .option("quote", '"')
        .csv(f"{origem}/{tabela}/ano_mes={ano_mes}/")
        # No Glue a coluna vem da partição do Catalog; aqui é acrescentada à mão.
        .withColumn("ano_mes", F.lit(ano_mes))
    )


def bronze_estabelecimentos(spark, origem, destino, ano_mes):
    raw = _ler_raw(spark, origem, "estabelecimentos", ano_mes)
    saida = _sql(spark, "bronze/estabelecimentos", raw_estabelecimentos=raw)
    _gravar_delta(saida, f"{destino}/estabelecimentos", ano_mes)


def bronze_dominios(spark, origem, destino, ano_mes, dominios=DOMINIOS):
    for dominio in dominios:
        raw = _ler_raw(spark, origem, dominio, ano_mes)
        saida = _sql(spark, f"bronze/{dominio}", **{f"raw_{dominio}": raw})
        _gravar_delta(saida, f"{destino}/{dominio}", ano_mes)


def silver_ibge_municipios(spark, origem, destino, ano_mes):
    """Equivalente local da receita do DataBrew (infra/databrew_receita_ibge.json), que só roda na AWS:
    achata o JSON e cria nome_normalizado (maiúsculas, sem acento)."""
    com_acento, sem_acento = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ", "AAAAAEEEEIIIIOOOOOUUUUC"
    uf = "`regiao-imediata`.`regiao-intermediaria`.UF"
    ibge = spark.read.option("multiLine", True).json(f"{_sem_amostra(origem)}/ibge_municipios/ano_mes={ano_mes}/")
    saida = ibge.select(
        F.col("id").alias("id_municipio_ibge"),
        "nome",
        F.col(f"{uf}.sigla").alias("sigla_uf"),
        F.col(f"{uf}.regiao.nome").alias("regiao"),
        F.translate(F.upper("nome"), com_acento, sem_acento).alias("nome_normalizado"),
    )
    saida.write.mode("overwrite").parquet(f"{_sem_amostra(destino)}/ibge_municipios")


def silver_estabelecimentos(spark, origem, destino, ano_mes):
    entrada = _ler_delta(spark, f"{origem}/estabelecimentos", ano_mes)
    saida = _sql(spark, "silver/estabelecimentos", bronze_estabelecimentos=entrada)
    _gravar_delta(saida, f"{destino}/estabelecimentos", ano_mes)


def gold_dim_municipio(spark, origem, destino, ano_mes):
    bronze = _camada(origem, "bronze")
    correcoes = spark.read.option("header", True).csv(str(CORRECOES_MUNICIPIOS))
    saida = _sql(
        spark,
        "gold/dim_municipio",
        bronze_municipios=spark.read.format("delta").load(f"{bronze}/municipios"),
        bronze_estabelecimentos=spark.read.format("delta").load(f"{bronze}/estabelecimentos"),
        silver_ibge_municipios=spark.read.parquet(f"{_sem_amostra(origem)}/ibge_municipios"),
        municipios_correcoes=correcoes,
    )
    # Dimensão: regravada inteira.
    saida.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(f"{destino}/dim_municipio")


def gold_ativas_por_uf(spark, origem, destino, ano_mes):
    entrada = _ler_delta(spark, f"{origem}/estabelecimentos", ano_mes)
    saida = _sql(spark, "gold/ativas_por_uf", silver_estabelecimentos=entrada)
    _gravar_delta(saida, f"{destino}/ativas_por_uf", ano_mes)


# Na ordem em que rodam. O bucket de origem é o da camada anterior (o silver_ibge_municipios lê o raw:
# na AWS ele é a receita do DataBrew).
JOBS = {
    "bronze_estabelecimentos": bronze_estabelecimentos,
    "bronze_dominios": bronze_dominios,
    "silver_estabelecimentos": silver_estabelecimentos,
    "silver_ibge_municipios": silver_ibge_municipios,
    "gold_dim_municipio": gold_dim_municipio,
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
        origem = "raw" if nome == "silver_ibge_municipios" else CAMADA_ANTERIOR[camada]
        JOBS[nome](spark, f"s3a://{origem}{prefixo}", f"s3a://{camada}{prefixo}", args.ano_mes)


if __name__ == "__main__":
    main()
