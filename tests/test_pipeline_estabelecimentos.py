"""Jobs de Estabelecimentos (bronze → silver) pelo executor local. Roda no container do Glue:

    make test-spark
"""
import csv
import datetime

import pytest

pytest.importorskip("pyspark")

from ingest.receita import COLUNAS  # noqa: E402
from jobs import local  # noqa: E402

ANO_MES = "2026-09"


def _gravar_raw(raiz, linhas, ano_mes=ANO_MES):
    pasta = raiz / "estabelecimentos" / f"ano_mes={ano_mes}"
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "Estabelecimentos0.csv", "w", encoding="utf-8", newline="") as f:
        f.write(";".join(COLUNAS["estabelecimentos"]) + "\n")
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        for linha in linhas:
            escritor.writerow([linha.get(coluna, "") for coluna in COLUNAS["estabelecimentos"]])


def _estab(cnpj_basico, uf, matriz=True, situacao="02", **extra):
    return {
        "cnpj_basico": cnpj_basico,
        "cnpj_ordem": "0001" if matriz else "0002",
        "cnpj_dv": "00",
        "identificador_matriz_filial": "1" if matriz else "2",
        "situacao_cadastral": situacao,
        "sigla_uf": uf,
        **extra,
    }


def _rodar_pipeline(spark, raiz, ano_mes=ANO_MES):
    local.bronze_estabelecimentos(spark, str(raiz / "raw"), str(raiz / "bronze"), ano_mes)
    local.silver_estabelecimentos(spark, str(raiz / "bronze"), str(raiz / "silver"), ano_mes)


def _ativas(spark, raiz):
    linhas = spark.read.format("delta").load(str(raiz / "silver" / "estabelecimentos")).collect()
    return sorted((r["ano_mes"], r["cnpj_basico"], r["cnpj_ordem"], r["empresa_ativa"]) for r in linhas)


def test_silver_marca_como_ativa_so_a_matriz_com_situacao_02(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [
        _estab("00000001", "AC"),
        _estab("00000001", "AP", matriz=False),  # filial ativa
        _estab("00000002", "AC", situacao="08"),  # baixada
        _estab("00000003", "RR", situacao="04"),  # inapta
    ])

    _rodar_pipeline(spark, tmp_path)

    assert _ativas(spark, tmp_path) == [
        ("2026-09", "00000001", "0001", True),
        ("2026-09", "00000001", "0002", False),
        ("2026-09", "00000002", "0001", False),
        ("2026-09", "00000003", "0001", False),
    ]


def _bronze(spark, raiz):
    return spark.read.format("delta").load(str(raiz / "bronze" / "estabelecimentos"))


def test_bronze_converte_datas_aaaammdd_e_zeros_viram_nulo(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [_estab(
        "00000001", "AC",
        data_inicio_atividade="20200115",
        data_situacao_cadastral="20200115",
        data_situacao_especial="00000000",
    )])

    local.bronze_estabelecimentos(spark, str(tmp_path / "raw"), str(tmp_path / "bronze"), ANO_MES)

    linha = _bronze(spark, tmp_path).first()
    assert (linha["data_inicio_atividade"], linha["data_situacao_cadastral"], linha["data_situacao_especial"]) == (
        datetime.date(2020, 1, 15), datetime.date(2020, 1, 15), None,
    )


def test_bronze_mantem_zeros_a_esquerda_dos_codigos(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [_estab("00000001", "AC", id_municipio_rf="0139")])

    local.bronze_estabelecimentos(spark, str(tmp_path / "raw"), str(tmp_path / "bronze"), ANO_MES)

    linha = _bronze(spark, tmp_path).first()
    assert (linha["cnpj_basico"], linha["cnpj_ordem"], linha["id_municipio_rf"], linha["situacao_cadastral"]) == (
        "00000001", "0001", "0139", "02",
    )


def test_reprocessar_um_mes_nao_duplica_nem_apaga_o_outro_mes(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [_estab("00000001", "AC")], ano_mes="2026-09")
    _gravar_raw(tmp_path / "raw", [_estab("00000001", "AC"), _estab("00000002", "RR")], ano_mes="2026-10")

    _rodar_pipeline(spark, tmp_path, "2026-09")
    _rodar_pipeline(spark, tmp_path, "2026-10")
    _rodar_pipeline(spark, tmp_path, "2026-09")

    assert _ativas(spark, tmp_path) == [
        ("2026-09", "00000001", "0001", True),
        ("2026-10", "00000001", "0001", True),
        ("2026-10", "00000002", "0001", True),
    ]


def test_bronze_descarta_o_endereco(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [_estab(
        "00000001", "AC",
        tipo_logradouro="RUA", logradouro="DAS FLORES", numero="10", complemento="CASA 2",
        bairro="CENTRO", cep="69900000",
    )])

    local.bronze_estabelecimentos(spark, str(tmp_path / "raw"), str(tmp_path / "bronze"), ANO_MES)

    colunas = set(_bronze(spark, tmp_path).columns)
    assert colunas.isdisjoint({"tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep"})
    assert {"email", "nome_fantasia", "sigla_uf", "id_municipio_rf"} <= colunas


def test_silver_troca_email_vazio_por_nulo(spark, tmp_path):
    _gravar_raw(tmp_path / "raw", [_estab("00000001", "AC"), _estab("00000002", "AC", email="X@Y.COM")])

    _rodar_pipeline(spark, tmp_path)

    linhas = spark.read.format("delta").load(str(tmp_path / "silver" / "estabelecimentos")).collect()
    # E-mail preenchido chega mascarado da Bronze; só o vazio vira nulo.
    assert sorted((r["cnpj_basico"], r["email"]) for r in linhas) == [("00000001", None), ("00000002", "*****")]


def test_bronze_mascara_email_e_cpf_que_escapam_do_detector(spark, tmp_path):
    # Formatos que o Detect Sensitive Data não reconheceu na AWS: ponto antes do @ e CPF colado ao nome.
    _gravar_raw(tmp_path / "raw", [
        _estab("00000001", "AC", email="FULANO.@GMAIL.COM", nome_fantasia="JOSE DA SILVA12345678901"),
        _estab("00000002", "AC", email="", nome_fantasia="PADARIA 2 IRMAOS"),
    ])

    local.bronze_estabelecimentos(spark, str(tmp_path / "raw"), str(tmp_path / "bronze"), ANO_MES)

    linhas = sorted((r["cnpj_basico"], r["email"], r["nome_fantasia"]) for r in _bronze(spark, tmp_path).collect())
    assert linhas == [("00000001", "*****", "JOSE DA SILVA*****"), ("00000002", None, "PADARIA 2 IRMAOS")]

