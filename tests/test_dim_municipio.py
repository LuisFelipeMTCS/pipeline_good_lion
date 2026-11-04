"""dim_municipio: casamento dos municípios da Receita com o IBGE pelo executor local. Roda no container do Glue:

    make test-spark
"""
import csv
import json

import pytest

pytest.importorskip("pyspark")

from ingest.receita import COLUNAS  # noqa: E402
from jobs import local  # noqa: E402

ANO_MES = "2026-09"


def _ibge(id_ibge, nome, uf, regiao):
    uf_completa = {"sigla": uf, "regiao": {"nome": regiao}}
    # microrregiao pode vir nula (Boa Esperança do Norte); a UF sai da região imediata.
    return {"id": id_ibge, "nome": nome, "microrregiao": None,
            "regiao-imediata": {"regiao-intermediaria": {"UF": uf_completa}}}


def _gravar(raiz, municipios_rf, estabelecimentos, ibge):
    pasta = raiz / "raw" / "municipios" / f"ano_mes={ANO_MES}"
    pasta.mkdir(parents=True)
    with open(pasta / "Municipios.csv", "w", encoding="utf-8", newline="") as f:
        f.write("codigo;descricao\n")
        csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(municipios_rf)

    pasta = raiz / "raw" / "estabelecimentos" / f"ano_mes={ANO_MES}"
    pasta.mkdir(parents=True)
    with open(pasta / "Estabelecimentos0.csv", "w", encoding="utf-8", newline="") as f:
        f.write(";".join(COLUNAS["estabelecimentos"]) + "\n")
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        for i, (id_municipio_rf, uf) in enumerate(estabelecimentos):
            linha = {"cnpj_basico": f"{i:08d}", "identificador_matriz_filial": "1", "sigla_uf": uf,
                     "id_municipio_rf": id_municipio_rf}
            escritor.writerow([linha.get(c, "") for c in COLUNAS["estabelecimentos"]])

    pasta = raiz / "raw" / "ibge_municipios" / f"ano_mes={ANO_MES}"
    pasta.mkdir(parents=True)
    (pasta / "municipios.json").write_text(json.dumps(ibge, ensure_ascii=False), encoding="utf-8")


def _dim(spark, raiz):
    r, b, s, g = (str(raiz / camada) for camada in ("raw", "bronze", "silver", "gold"))
    local.bronze_estabelecimentos(spark, r, b, ANO_MES)
    local.bronze_dominios(spark, r, b, ANO_MES, dominios=["municipios"])
    local.silver_ibge_municipios(spark, r, s, ANO_MES)
    local.gold_dim_municipio(spark, s, g, ANO_MES)
    linhas = spark.read.format("delta").load(f"{g}/dim_municipio").collect()
    return sorted(tuple(linha) for linha in linhas)


def test_casa_por_nome_sem_acento_e_uf_e_usa_a_tabela_de_correcoes(spark, tmp_path):
    _gravar(
        tmp_path,
        municipios_rf=[("7107", "SAO PAULO"), ("5875", "PARATI")],
        estabelecimentos=[("7107", "SP"), ("5875", "RJ")],
        ibge=[_ibge(3550308, "São Paulo", "SP", "Sudeste"), _ibge(3303807, "Paraty", "RJ", "Sudeste")],
    )

    assert _dim(spark, tmp_path) == [
        ("5875", "3303807", "Paraty", "RJ", "Sudeste"),
        ("7107", "3550308", "São Paulo", "SP", "Sudeste"),
    ]


def test_homonimos_em_ufs_diferentes_e_uf_com_mais_estabelecimentos(spark, tmp_path):
    _gravar(
        tmp_path,
        municipios_rf=[("1073", "BOM JESUS"), ("8593", "BOM JESUS"), ("9707", "EXTERIOR")],
        # O 8593 tem um cadastro com UF trocada (PI): vale a UF da maioria (RS).
        estabelecimentos=[("1073", "PI"), ("8593", "RS"), ("8593", "RS"), ("8593", "PI"), ("9707", "EX")],
        ibge=[_ibge(2201903, "Bom Jesus", "PI", "Nordeste"), _ibge(4302352, "Bom Jesus", "RS", "Sul")],
    )

    assert _dim(spark, tmp_path) == [
        ("1073", "2201903", "Bom Jesus", "PI", "Nordeste"),
        ("8593", "4302352", "Bom Jesus", "RS", "Sul"),
    ]


def test_municipio_sem_par_fica_sem_codigo_do_ibge(spark, tmp_path):
    # É esse nulo que a regra bloqueante (jobs/quality/gold_dim_municipio.dqdl) pega.
    _gravar(
        tmp_path,
        municipios_rf=[("0139", "RIO BRANCO"), ("9999", "MUNICIPIO NOVO")],
        estabelecimentos=[("0139", "AC"), ("9999", "AC")],
        ibge=[_ibge(1200401, "Rio Branco", "AC", "Norte")],
    )

    assert _dim(spark, tmp_path) == [
        ("0139", "1200401", "Rio Branco", "AC", "Norte"),
        ("9999", None, "MUNICIPIO NOVO", "AC", None),
    ]
