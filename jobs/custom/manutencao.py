# ruff: noqa: F706, F821
# Corpo do Custom Transform Manutencao (o Glue o embrulha numa função). Fim do Workflow (PRD, 5.8):
# OPTIMIZE compacta os arquivos pequenos e VACUUM apaga os que saíram do histórico há mais de 7 dias.
# As tabelas são descobertas pela pasta _delta_log em cada bucket: tabela nova não fica sem manutenção.
# Com mês (--ano_mes ou o mês do Workflow), o OPTIMIZE só compacta essa partição nas tabelas particionadas: na base
# completa, compactar tudo a cada execução custou 35 min com 10 workers (~US$ 1,60). Sem mês, compacta tudo.
# A entrada do nó só cumpre a exigência do grafo.
import sys
import time

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["JOB_NAME", "buckets", "ambiente"])
if "--ano_mes" in sys.argv:
    ano_mes = getResolvedOptions(sys.argv, ["ano_mes"])["ano_mes"]
elif "--WORKFLOW_RUN_ID" in sys.argv:
    workflow = getResolvedOptions(sys.argv, ["WORKFLOW_NAME", "WORKFLOW_RUN_ID"])
    ano_mes = boto3.client("glue").get_workflow_run_properties(
        Name=workflow["WORKFLOW_NAME"], RunId=workflow["WORKFLOW_RUN_ID"]
    )["RunProperties"].get("ano_mes")
else:
    ano_mes = None
spark = glueContext.spark_session
Caminho = spark.sparkContext._jvm.org.apache.hadoop.fs.Path
configuracao = spark.sparkContext._jsc.hadoopConfiguration()
prefixo = "sample/" if args["ambiente"] == "sample" else ""
tabelas = 0
for bucket in args["buckets"].split(","):
    raiz = Caminho(f"s3://{bucket}/{prefixo}")
    fs = raiz.getFileSystem(configuracao)
    if not fs.exists(raiz):
        continue
    for item in fs.listStatus(raiz):
        caminho = item.getPath().toString()
        if not fs.exists(Caminho(f"{caminho}/_delta_log")):
            continue
        antes = spark.sql(f"DESCRIBE DETAIL delta.`{caminho}`").first()
        so_o_mes = f" WHERE ano_mes = '{ano_mes}'" if ano_mes and "ano_mes" in antes["partitionColumns"] else ""
        spark.sql(f"OPTIMIZE delta.`{caminho}`{so_o_mes}")
        spark.sql(f"VACUUM delta.`{caminho}` RETAIN 168 HOURS")
        depois = spark.sql(f"DESCRIBE DETAIL delta.`{caminho}`").first()
        tabelas += 1
        print(
            f"manutencao tabela={caminho} arquivos_antes={antes['numFiles']} arquivos_depois={depois['numFiles']} "
            f"bytes={depois['sizeInBytes']}"
        )
segundos = int(time.time() - spark.sparkContext.startTime / 1000)
print(f"resumo job={args['JOB_NAME']} segundos={segundos} linhas=0 meses=- tabelas={tabelas}")
return dfc
