# ruff: noqa: F706, F821
# Corpo do Custom Transform GarantirEsquema dos jobs Bronze (o Glue o embrulha numa função).
# Com Job Bookmarks e nenhum arquivo novo, a origem vem sem colunas e o SQL seguinte falharia:
# aqui o lote vazio ganha as colunas da tabela do raw no Catalog (tudo texto).
import sys

import boto3
from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection
from awsglue.utils import getResolvedOptions
from pyspark.sql.types import StringType, StructField, StructType

if dfc.select(list(dfc.keys())[0]).toDF().columns:
    return dfc
tabela = getResolvedOptions(sys.argv, ["JOB_NAME"])["JOB_NAME"].split("_", 1)[1]
t = boto3.client("glue").get_table(DatabaseName="goodlion_raw", Name=tabela)["Table"]
colunas = [c["Name"] for c in t["StorageDescriptor"]["Columns"] + t["PartitionKeys"]]
vazio = glueContext.spark_session.createDataFrame([], StructType([StructField(c, StringType()) for c in colunas]))
return DynamicFrameCollection({"vazio": DynamicFrame.fromDF(vazio, glueContext, "vazio")}, glueContext)
