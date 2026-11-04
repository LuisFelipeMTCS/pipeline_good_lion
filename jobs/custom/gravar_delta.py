# ruff: noqa: F706, F821
# Corpo do Custom Transform GravarDelta. O Glue o embrulha em
# `def GravarDelta(glueContext, dfc) -> DynamicFrameCollection:`, por isso o `return` solto e o `dfc`.
# Grava em Delta substituindo só os meses que vieram no lote: com Job Bookmarks o lote tem só os
# arquivos novos, que podem ser de mais de um mês. Tabela sem ano_mes (dimensão) é regravada inteira.
import sys
import time

from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["JOB_NAME", "bucket", "ambiente"])
# shortcut: a origem (Catalog do raw) só tem a amostra; liberar o full junto com o crawler
# da base completa (ticket 17).
if args["ambiente"] != "sample":
    raise ValueError("--ambiente full ainda não suportado")
# O Glue chama a entrada de "<nome do nó anterior>_<id do nó>". O nó anterior se chama <camada>_<tabela>
# (bronze_cnaes -> cnaes): é assim que um job só (bronze_dominios) grava várias tabelas.
chave = list(dfc.keys())[0]
tabela = chave.split("_node")[0].split("_", 1)[1]
# O nó Detect Sensitive Data acrescenta DetectedEntities (onde mascarou o quê); fica fora da tabela.
df = dfc.select(chave).toDF().drop("DetectedEntities")
caminho = f"s3://{args['bucket']}/sample/{tabela}"
linhas = 0
meses = []
if "ano_mes" not in df.columns:
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(caminho)
else:
    meses = sorted(r["ano_mes"] for r in df.select("ano_mes").distinct().collect())
    if meses:  # lote vazio: o Bookmark não achou arquivos novos
        (
            df.write.format("delta")
            .mode("overwrite")
            .partitionBy("ano_mes")
            .option("replaceWhere", "ano_mes IN ({})".format(", ".join(f"'{m}'" for m in meses)))
            .save(caminho)
        )
if meses or "ano_mes" not in df.columns:
    # O número vem do histórico Delta, sem ler os dados de novo.
    historico = glueContext.spark_session.sql(f"DESCRIBE HISTORY delta.`{caminho}` LIMIT 1").first()
    linhas = historico["operationMetrics"]["numOutputRows"]
# Linha lida pelo dashboard do CloudWatch (duração e linhas por execução).
segundos = int(time.time() - glueContext.spark_session.sparkContext.startTime / 1000)
print(
    f"resumo job={args['JOB_NAME']} segundos={segundos} linhas={linhas} "
    f"meses={','.join(meses) or '-'} tabela={tabela}"
)
return dfc
