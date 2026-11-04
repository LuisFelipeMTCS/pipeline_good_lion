# ruff: noqa: F706, F821
# Corpo do Custom Transform LerMudancas da fato_movimentacao_empresa (o Glue o embrulha numa função).
# Lê o Change Data Feed da silver_empresa_consolidada nas versões de MERGE do --ano_mes (marcadas no
# userMetadata). Rodar o MERGE do mesmo mês de novo cria uma versão sem mudanças: nada se repete.
# A entrada do nó (a própria consolidada, silver_<tabela>) só dá o nome da tabela; o bucket vem do --bucket_silver.
import sys

import boto3
from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection
from awsglue.utils import getResolvedOptions
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["bucket_silver"])
# O mês vem do --ano_mes (execução manual) ou, dentro do Workflow, das propriedades da execução.
if "--ano_mes" in sys.argv:
    ano_mes = getResolvedOptions(sys.argv, ["ano_mes"])["ano_mes"]
else:
    workflow = getResolvedOptions(sys.argv, ["WORKFLOW_NAME", "WORKFLOW_RUN_ID"])
    ano_mes = boto3.client("glue").get_workflow_run_properties(
        Name=workflow["WORKFLOW_NAME"], RunId=workflow["WORKFLOW_RUN_ID"]
    )["RunProperties"]["ano_mes"]
spark = glueContext.spark_session
tabela = list(dfc.keys())[0].split("_node")[0].split("_", 1)[1]  # silver_empresa_consolidada -> empresa_consolidada
caminho = f"s3://{args['bucket_silver']}/sample/{tabela}"
versoes = [
    r["version"]
    for r in spark.sql(f"DESCRIBE HISTORY delta.`{caminho}`")
    .where(F.col("operation") == "MERGE")
    .where(F.col("userMetadata") == ano_mes)
    .collect()
]
leitor = spark.read.format("delta").option("readChangeFeed", "true")
if versoes:
    mudancas = leitor.option("startingVersion", min(versoes)).option("endingVersion", max(versoes)).load(caminho)
else:
    # Mês sem MERGE (carga inicial): lote vazio, com as colunas do CDF.
    ultima = spark.sql(f"DESCRIBE HISTORY delta.`{caminho}` LIMIT 1").first()["version"]
    mudancas = leitor.option("startingVersion", ultima).load(caminho).limit(0)
mudancas = mudancas.withColumn("ano_mes", F.lit(ano_mes))
return DynamicFrameCollection({"mudancas": DynamicFrame.fromDF(mudancas, glueContext, "mudancas")}, glueContext)
