# ruff: noqa: F706, F821
# Corpo do Custom Transform FiltrarMes da Silver e da Gold (o Glue o embrulha numa função).
# Os nós visuais não aceitam parâmetro do job (ARQUITETURA, "Padrão dos jobs visuais"), então o limite
# por --ano_mes (PRD, 5.4) fica aqui. Sobre Delta particionado por ano_mes, o filtro só lê a partição.
import sys

from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection
from awsglue.utils import getResolvedOptions
from pyspark.sql import functions as F

ano_mes = getResolvedOptions(sys.argv, ["ano_mes"])["ano_mes"]
chave = list(dfc.keys())[0]
df = dfc.select(chave).toDF().where(F.col("ano_mes") == ano_mes)
return DynamicFrameCollection({chave: DynamicFrame.fromDF(df, glueContext, chave)}, glueContext)
