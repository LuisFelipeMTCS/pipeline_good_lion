# ruff: noqa: F706, F821
# Corpo do Custom Transform MergeConsolidada (o Glue o embrulha numa função).
# MERGE mensal na silver_empresa_consolidada (PRD, 5.5): insere o que é novo, atualiza o que mudou e remove
# o que deixou de existir. Change Data Feed ligado: é dele que a fato_movimentacao_empresa tira os eventos.
# Cada commit leva o ano_mes no userMetadata, para a Gold achar as versões do mês.
import sys
import time

import boto3
from awsglue.utils import getResolvedOptions
from pyspark.errors import AnalysisException
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "bucket", "ambiente"])
# O mês vem do --ano_mes (execução manual) ou, dentro do Workflow, das propriedades da execução.
if "--ano_mes" in sys.argv:
    ano_mes = getResolvedOptions(sys.argv, ["ano_mes"])["ano_mes"]
else:
    workflow = getResolvedOptions(sys.argv, ["WORKFLOW_NAME", "WORKFLOW_RUN_ID"])
    ano_mes = boto3.client("glue").get_workflow_run_properties(
        Name=workflow["WORKFLOW_NAME"], RunId=workflow["WORKFLOW_RUN_ID"]
    )["RunProperties"]["ano_mes"]
if args["ambiente"] != "sample":
    raise ValueError("--ambiente full ainda não suportado")
chave = list(dfc.keys())[0]
tabela = chave.split("_node")[0].split("_", 1)[1]  # silver_empresa_consolidada -> empresa_consolidada
caminho = f"s3://{args['bucket']}/sample/{tabela}"
spark = glueContext.spark_session
novo = dfc.select(chave).toDF().withColumn("ano_mes_alteracao", F.lit(ano_mes))
spark.conf.set("spark.databricks.delta.commitInfo.userMetadata", ano_mes)
try:
    spark.sql(f"DESCRIBE HISTORY delta.`{caminho}` LIMIT 1")
    existe = True
except AnalysisException:
    existe = False
try:
    if not existe:
        # Carga inicial: é o ponto de partida, não gera eventos.
        novo.write.format("delta").save(caminho)
        spark.sql(f"ALTER TABLE delta.`{caminho}` SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    else:
        # Em SQL, não pela API Python do Delta: o módulo `delta` não vem no container local do Glue.
        # Só atualiza a linha se algo mudou: sem isso, todo mês toda a base viraria "mudança" no CDF.
        colunas = [c for c in novo.columns if c not in ("cnpj_basico", "ano_mes_alteracao")]
        mudou = " OR ".join(f"NOT (t.{c} <=> s.{c})" for c in colunas)
        novo.createOrReplaceTempView("estado_do_mes")
        spark.sql(f"""
            MERGE INTO delta.`{caminho}` AS t
            USING estado_do_mes AS s
            ON t.cnpj_basico = s.cnpj_basico
            WHEN MATCHED AND ({mudou}) THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            WHEN NOT MATCHED BY SOURCE THEN DELETE
        """)
finally:
    spark.conf.unset("spark.databricks.delta.commitInfo.userMetadata")
# Linha lida pelo dashboard do CloudWatch: linhas = inseridas + atualizadas + removidas (ou gravadas na carga inicial).
metricas = spark.sql(f"DESCRIBE HISTORY delta.`{caminho}`").where("operation IN ('MERGE', 'WRITE')").first()
m = metricas["operationMetrics"]
if metricas["operation"] == "MERGE":
    linhas = sum(int(m[c]) for c in ("numTargetRowsInserted", "numTargetRowsUpdated", "numTargetRowsDeleted"))
else:
    linhas = int(m["numOutputRows"])
segundos = int(time.time() - spark.sparkContext.startTime / 1000)
print(f"resumo job={args['JOB_NAME']} segundos={segundos} linhas={linhas} meses={ano_mes} tabela={tabela}")
return dfc
