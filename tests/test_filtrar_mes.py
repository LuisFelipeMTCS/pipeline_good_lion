"""Custom Transform FiltrarMes (Silver e Gold). Roda no container do Glue: make test-spark"""
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("awsglue")

from awsglue.context import GlueContext  # noqa: E402
from awsglue.dynamicframe import DynamicFrame, DynamicFrameCollection  # noqa: E402

CODIGO = (Path(__file__).parent.parent / "jobs" / "custom" / "filtrar_mes.py").read_text()


def test_deixa_passar_so_o_mes_do_parametro(spark, monkeypatch):
    glue = GlueContext(spark.sparkContext)
    monkeypatch.setattr(sys, "argv", ["job", "--JOB_NAME", "silver_empresas", "--ano_mes", "2026-10"])
    escopo = {}
    exec("def FiltrarMes(glueContext, dfc):\n" + textwrap.indent(CODIGO, "    "), escopo)
    df = spark.createDataFrame([("1", "2026-09"), ("2", "2026-10")], "cnpj_basico string, ano_mes string")

    lote = DynamicFrameCollection({"bronze_empresas_node": DynamicFrame.fromDF(df, glue, "x")}, glue)
    saida = escopo["FiltrarMes"](glue, lote)

    chave = list(saida.keys())[0]
    assert chave == "bronze_empresas_node"
    assert [tuple(r) for r in saida.select(chave).toDF().collect()] == [("2", "2026-10")]
