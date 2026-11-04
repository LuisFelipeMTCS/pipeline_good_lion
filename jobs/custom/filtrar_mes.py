# ruff: noqa: F706, F821
# Corpo do Custom Transform FiltrarMes da Silver e da Gold (o Glue o embrulha numa função).
# Os nós visuais não aceitam parâmetro do job (ARQUITETURA, "Padrão dos jobs visuais"), então o limite
# por --ano_mes (PRD, 5.4) fica aqui. Sobre Delta particionado por ano_mes, o filtro só lê a partição.
import sys

import boto3
from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection
from awsglue.utils import getResolvedOptions
from pyspark.sql import functions as F

# O mês vem do --ano_mes (execução manual) ou, dentro do Workflow, das propriedades da execução.
if "--ano_mes" in sys.argv:
    ano_mes = getResolvedOptions(sys.argv, ["ano_mes"])["ano_mes"]
else:
    workflow = getResolvedOptions(sys.argv, ["WORKFLOW_NAME", "WORKFLOW_RUN_ID"])
    ano_mes = boto3.client("glue").get_workflow_run_properties(
        Name=workflow["WORKFLOW_NAME"], RunId=workflow["WORKFLOW_RUN_ID"]
    )["RunProperties"]["ano_mes"]
chave = list(dfc.keys())[0]
df = dfc.select(chave).toDF().where(F.col("ano_mes") == ano_mes)
return DynamicFrameCollection({chave: DynamicFrame.fromDF(df, glueContext, chave)}, glueContext)
