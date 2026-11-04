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


def _gravar_dimensao(df, caminho):
    # Dimensão: regravada inteira.
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(caminho)


def _bronze(spark, origem, destino, ano_mes, tabela):
    raw = _ler_raw(spark, origem, tabela, ano_mes)
    saida = _sql(spark, f"bronze/{tabela}", **{f"raw_{tabela}": raw})
    _gravar_delta(saida, f"{destino}/{tabela}", ano_mes)


def _silver(spark, origem, destino, ano_mes, tabela):
    entrada = _ler_delta(spark, f"{origem}/{tabela}", ano_mes)
    saida = _sql(spark, f"silver/{tabela}", **{f"bronze_{tabela}": entrada})
    _gravar_delta(saida, f"{destino}/{tabela}", ano_mes)


def bronze_estabelecimentos(spark, origem, destino, ano_mes):
    _bronze(spark, origem, destino, ano_mes, "estabelecimentos")


def bronze_empresas(spark, origem, destino, ano_mes):
    _bronze(spark, origem, destino, ano_mes, "empresas")


def bronze_simples(spark, origem, destino, ano_mes):
    _bronze(spark, origem, destino, ano_mes, "simples")


def bronze_dominios(spark, origem, destino, ano_mes, dominios=DOMINIOS):
    for dominio in dominios:
        _bronze(spark, origem, destino, ano_mes, dominio)


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
    _silver(spark, origem, destino, ano_mes, "estabelecimentos")


def silver_empresas(spark, origem, destino, ano_mes):
    _silver(spark, origem, destino, ano_mes, "empresas")


def silver_simples(spark, origem, destino, ano_mes):
    _silver(spark, origem, destino, ano_mes, "simples")


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
    _gravar_dimensao(saida, f"{destino}/dim_municipio")


def gold_dimensoes(spark, origem, destino, ano_mes):
    bronze = _camada(origem, "bronze")
    entradas = {
        "bronze_cnaes": spark.read.format("delta").load(f"{bronze}/cnaes"),
        "bronze_naturezas": spark.read.format("delta").load(f"{bronze}/naturezas"),
        "silver_estabelecimentos": spark.read.format("delta").load(f"{origem}/estabelecimentos"),
    }
    for dimensao in ("dim_categoria", "dim_cnae", "dim_natureza_juridica", "dim_tempo"):
        _gravar_dimensao(_sql(spark, f"gold/{dimensao}", **entradas), f"{destino}/{dimensao}")


def gold_fato_empresa_mensal(spark, origem, destino, ano_mes):
    entradas = {
        f"silver_{t}": _ler_delta(spark, f"{origem}/{t}", ano_mes) for t in ("estabelecimentos", "empresas", "simples")
    }
    saida = _sql(spark, "gold/fato_empresa_mensal", **entradas)
    _gravar_delta(saida, f"{destino}/fato_empresa_mensal", ano_mes)


# Na ordem em que rodam. O bucket de origem é o da camada anterior (o silver_ibge_municipios lê o raw:
# na AWS ele é a receita do DataBrew).
JOBS = {
    "bronze_estabelecimentos": bronze_estabelecimentos,
    "bronze_empresas": bronze_empresas,
    "bronze_simples": bronze_simples,
    "bronze_dominios": bronze_dominios,
    "silver_estabelecimentos": silver_estabelecimentos,
    "silver_empresas": silver_empresas,
    "silver_simples": silver_simples,
    "silver_ibge_municipios": silver_ibge_municipios,
    "gold_dim_municipio": gold_dim_municipio,
    "gold_dimensoes": gold_dimensoes,
    "gold_fato_empresa_mensal": gold_fato_empresa_mensal,
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
