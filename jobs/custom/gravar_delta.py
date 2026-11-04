# ruff: noqa: F706, F821
# Corpo do Custom Transform GravarDelta dos jobs Bronze. O Glue o embrulha em
# `def GravarDelta(glueContext, dfc) -> DynamicFrameCollection:`, por isso o `return` solto e o `dfc`.
# Grava em Delta substituindo só os meses que vieram no lote: com Job Bookmarks o lote tem só os
# arquivos novos, que podem ser de mais de um mês.
import sys
import time

from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["JOB_NAME", "bucket", "ambiente"])
# shortcut: a origem (Catalog do raw) só tem a amostra; liberar o full junto com o crawler
# da base completa (ticket 17).
if args["ambiente"] != "sample":
    raise ValueError("--ambiente full ainda não suportado na Bronze")
tabela = args["JOB_NAME"].split("_", 1)[1]  # bronze_estabelecimentos -> estabelecimentos
df = dfc.select(list(dfc.keys())[0]).toDF()
meses = sorted(r["ano_mes"] for r in df.select("ano_mes").distinct().collect())
linhas = 0
if meses:  # lote vazio: o Bookmark não achou arquivos novos
    caminho = f"s3://{args['bucket']}/sample/{tabela}"
    (
        df.write.format("delta")
        .mode("overwrite")
        .partitionBy("ano_mes")
        .option("replaceWhere", "ano_mes IN ({})".format(", ".join(f"'{m}'" for m in meses)))
        .save(caminho)
    )
    # O número vem do histórico Delta, sem ler os dados de novo.
    historico = glueContext.spark_session.sql(f"DESCRIBE HISTORY delta.`{caminho}` LIMIT 1").first()
    linhas = historico["operationMetrics"]["numOutputRows"]
# Linha lida pelo dashboard do CloudWatch (duração e linhas por execução).
segundos = int(time.time() - glueContext.spark_session.sparkContext.startTime / 1000)
print(f"resumo job={args['JOB_NAME']} segundos={segundos} linhas={linhas} meses={','.join(meses) or '-'}")
return dfc
