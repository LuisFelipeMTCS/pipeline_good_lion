"""Custom Transform que grava a Bronze em Delta. Roda no container do Glue contra o MinIO: make test-spark"""
import sys
import textwrap
import uuid
from pathlib import Path

import pytest

pytest.importorskip("awsglue")

from awsglue.context import GlueContext  # noqa: E402
from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection  # noqa: E402

CODIGO = (Path(__file__).parent.parent / "jobs" / "custom" / "gravar_delta.py").read_text()


@pytest.fixture
def gravar(spark, monkeypatch):
    # No Glue o caminho é s3://; aqui o s3:// vai para o MinIO pelo s3a.
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    glue = GlueContext(spark.sparkContext)
    tabela = f"teste{uuid.uuid4().hex[:8]}"
    argv = ["job", "--JOB_NAME", f"bronze_{tabela}", "--bucket", "bronze", "--ambiente", "sample"]
    monkeypatch.setattr(sys, "argv", argv)
    # Igual ao script gerado pelo Glue: o arquivo é o corpo da função.
    escopo = {}
    exec("def GravarDelta(glueContext, dfc):\n" + textwrap.indent(CODIGO, "    "), escopo)

    def _gravar(linhas):
        df = spark.createDataFrame(linhas, "cnpj_basico string, ano_mes string")
        escopo["GravarDelta"](glue, DynamicFrameCollection({"lote": DynamicFrame.fromDF(df, glue, "lote")}, glue))
        return sorted(tuple(r) for r in spark.read.format("delta").load(f"s3://bronze/sample/{tabela}").collect())

    yield _gravar
    import boto3

    s3 = boto3.resource("s3", endpoint_url="http://minio:9000")
    s3.Bucket("bronze").objects.filter(Prefix=f"sample/{tabela}/").delete()


def test_substitui_so_os_meses_do_lote_e_ignora_lote_vazio(gravar):
    gravar([("00000001", "2026-09")])
    gravar([("00000002", "2026-10"), ("00000003", "2026-10")])
    esperado = [("00000002", "2026-10"), ("00000003", "2026-10"), ("00000004", "2026-09")]
    assert gravar([("00000004", "2026-09")]) == esperado
    assert gravar([]) == esperado


def test_lote_vazio_do_bookmark_ganha_as_colunas_do_catalog(spark, monkeypatch):
    import boto3

    glue = GlueContext(spark.sparkContext)
    monkeypatch.setattr(sys, "argv", ["job", "--JOB_NAME", "bronze_estabelecimentos"])
    tabela = {"StorageDescriptor": {"Columns": [{"Name": "cnpj_basico"}, {"Name": "sigla_uf"}]},
              "PartitionKeys": [{"Name": "ano_mes"}]}
    # A API do Glue é fronteira externa: o Catalog de verdade só existe na AWS.
    catalog = type("Glue", (), {"get_table": lambda *_, **__: {"Table": tabela}})()
    monkeypatch.setattr(boto3, "client", lambda *_: catalog)
    codigo = (Path(__file__).parent.parent / "jobs" / "custom" / "garantir_esquema.py").read_text()
    escopo = {}
    exec("def GarantirEsquema(glueContext, dfc):\n" + textwrap.indent(codigo, "    "), escopo)
    sem_colunas = spark.createDataFrame([], "")

    lote = DynamicFrameCollection({"x": DynamicFrame.fromDF(sem_colunas, glue, "x")}, glue)
    saida = escopo["GarantirEsquema"](glue, lote)

    df = saida.select(list(saida.keys())[0]).toDF()
    assert (df.columns, df.count()) == (["cnpj_basico", "sigla_uf", "ano_mes"], 0)
