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
    argv = ["job", "--JOB_NAME", "bronze_qualquer", "--bucket", "bronze", "--ambiente", "sample"]
    monkeypatch.setattr(sys, "argv", argv)
    # Igual ao script gerado pelo Glue: o arquivo é o corpo da função.
    escopo = {}
    exec("def GravarDelta(glueContext, dfc):\n" + textwrap.indent(CODIGO, "    "), escopo)

    def _gravar(linhas, esquema="cnpj_basico string, ano_mes string"):
        df = spark.createDataFrame(linhas, esquema)
        # Chave como o Glue gera: "<nome do nó SQL>_<id do nó>"; o nome do nó dá a tabela.
        lote = {f"bronze_{tabela}_nodesql": DynamicFrame.fromDF(df, glue, "lote")}
        escopo["GravarDelta"](glue, DynamicFrameCollection(lote, glue))
        return sorted(tuple(r) for r in spark.read.format("delta").load(f"s3://bronze/sample/{tabela}").collect())

    yield _gravar
    import boto3

    s3 = boto3.resource("s3", endpoint_url="http://minio:9000")
    s3.Bucket("bronze").objects.filter(Prefix=f"sample/{tabela}/").delete()


def test_substitui_so_os_meses_do_lote_e_ignora_lote_vazio(gravar, capsys):
    gravar([("00000001", "2026-09")])
    gravar([("00000002", "2026-10"), ("00000003", "2026-10")])
    assert "linhas=2 meses=2026-10" in capsys.readouterr().out
    esperado = [("00000002", "2026-10"), ("00000003", "2026-10"), ("00000004", "2026-09")]
    assert gravar([("00000004", "2026-09")]) == esperado
    assert gravar([]) == esperado


def test_tabela_sem_ano_mes_e_regravada_inteira(gravar, capsys):
    gravar([("0001", "GUAJARA-MIRIM"), ("0002", "PORTO VELHO")], "codigo string, descricao string")

    assert gravar([("0001", "GUAJARA-MIRIM")], "codigo string, descricao string") == [("0001", "GUAJARA-MIRIM")]
    assert "linhas=1 meses=- tabela=" in capsys.readouterr().out


def test_lote_vazio_do_bookmark_ganha_as_colunas_do_catalog(spark, monkeypatch):
    import boto3

    glue = GlueContext(spark.sparkContext)
    tabela = {"StorageDescriptor": {"Columns": [{"Name": "cnpj_basico"}, {"Name": "sigla_uf"}]},
              "PartitionKeys": [{"Name": "ano_mes"}]}
    # A API do Glue é fronteira externa: o Catalog de verdade só existe na AWS.
    pedidos = []
    catalog = type("Glue", (), {"get_table": lambda _, **kw: pedidos.append(kw) or {"Table": tabela}})()
    monkeypatch.setattr(boto3, "client", lambda *_: catalog)
    codigo = (Path(__file__).parent.parent / "jobs" / "custom" / "garantir_esquema.py").read_text()
    escopo = {}
    exec("def GarantirEsquema(glueContext, dfc):\n" + textwrap.indent(codigo, "    "), escopo)
    sem_colunas = spark.createDataFrame([], "")

    lote = DynamicFrameCollection({"raw_estabelecimentos_noderaw": DynamicFrame.fromDF(sem_colunas, glue, "x")}, glue)
    saida = escopo["GarantirEsquema"](glue, lote)

    df = saida.select(list(saida.keys())[0]).toDF()
    assert (df.columns, df.count()) == (["cnpj_basico", "sigla_uf", "ano_mes"], 0)
    assert pedidos == [{"DatabaseName": "goodlion_raw", "Name": "estabelecimentos"}]
