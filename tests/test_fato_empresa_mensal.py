"""fato_empresa_mensal e dimensões da Gold pelo executor local. Roda no container do Glue:

    make test-spark
"""
import csv
import decimal

import pytest

pytest.importorskip("pyspark")

from ingest.receita import COLUNAS  # noqa: E402
from jobs import local  # noqa: E402

ANO_MES = "2026-09"


def _gravar(raiz, tabela, linhas, ano_mes=ANO_MES):
    pasta = raiz / "raw" / tabela / f"ano_mes={ano_mes}"
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / f"{tabela}.csv", "w", encoding="utf-8", newline="") as f:
        f.write(";".join(COLUNAS[tabela]) + "\n")
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        for linha in linhas:
            escritor.writerow([linha.get(coluna, "") for coluna in COLUNAS[tabela]])


def _empresa(raiz, cnpj, porte, mei=None, capital="1000,00", municipio="0139", ano_mes=ANO_MES, filiais=()):
    """Empresa com matriz ativa no município, filiais (situação de cada uma) e, se `mei`, linha no Simples
    (sem `mei`, o Simples do mês fica vazio)."""
    empresa = {"cnpj_basico": cnpj, "razao_social": "FULANO 12345678901", "natureza_juridica": "2135",
               "capital_social": capital, "porte": porte}
    _gravar(raiz, "empresas", [empresa], ano_mes)
    estabs = [{"cnpj_basico": cnpj, "cnpj_ordem": "0001", "identificador_matriz_filial": "1",
               "situacao_cadastral": "02", "sigla_uf": "AC", "id_municipio_rf": municipio,
               "cnae_fiscal_principal": "4711302", "data_inicio_atividade": "20200115"}]
    for i, situacao in enumerate(filiais, start=2):
        estabs.append({"cnpj_basico": cnpj, "cnpj_ordem": f"{i:04d}", "identificador_matriz_filial": "2",
                       "situacao_cadastral": situacao, "sigla_uf": "AP", "id_municipio_rf": "0605"})
    _gravar(raiz, "estabelecimentos", estabs, ano_mes)
    simples = []
    if mei:
        opcao, exclusao = mei
        simples = [{"cnpj_basico": cnpj, "opcao_simples": "S", "opcao_mei": opcao,
                    "data_opcao_mei": "20200115", "data_exclusao_mei": exclusao}]
    _gravar(raiz, "simples", simples, ano_mes)


def _rodar(spark, raiz, ano_mes=ANO_MES):
    r, b, s, g = (str(raiz / camada) for camada in ("raw", "bronze", "silver", "gold"))
    for tabela in ("estabelecimentos", "empresas", "simples"):
        if (raiz / "raw" / tabela / f"ano_mes={ano_mes}").exists():
            getattr(local, f"bronze_{tabela}")(spark, r, b, ano_mes)
            getattr(local, f"silver_{tabela}")(spark, b, s, ano_mes)
    local.gold_fato_empresa_mensal(spark, s, g, ano_mes)
    return spark.read.format("delta").load(f"{g}/fato_empresa_mensal")


def _categorias(fato):
    return sorted((r["ano_mes"], r["cnpj_basico"], r["id_categoria"]) for r in fato.collect())


def test_categoria_mei_primeiro_e_depois_o_porte(spark, tmp_path):
    # Cada empresa num mês próprio: o raw de cada tabela tem um arquivo por mês neste teste.
    casos = [
        ("00000001", "01", ("S", "00000000"), "2026-01"),  # MEI ativo (porte 01, como todo MEI)
        ("00000002", "01", ("S", "20250301"), "2026-02"),  # saiu do MEI: vale o porte, ME
        ("00000003", "01", ("N", "00000000"), "2026-03"),  # ME
        ("00000004", "03", None, "2026-04"),               # EPP
        ("00000005", "05", None, "2026-05"),               # Demais
        ("00000006", "", None, "2026-06"),                 # porte vazio vira 00: Demais
    ]
    for cnpj, porte, mei, ano_mes in casos:
        _empresa(tmp_path, cnpj, porte, mei, ano_mes=ano_mes)
        fato = _rodar(spark, tmp_path, ano_mes)
    esperado = [
        ("2026-01", "00000001", "MEI"), ("2026-02", "00000002", "ME"), ("2026-03", "00000003", "ME"),
        ("2026-04", "00000004", "EPP"), ("2026-05", "00000005", "DEMAIS"), ("2026-06", "00000006", "DEMAIS"),
    ]
    assert _categorias(fato) == esperado


def test_empresa_ativa_pela_matriz_com_municipio_da_matriz_e_estabelecimentos_ativos(spark, tmp_path):
    # Filiais em outro município: uma ativa, uma baixada (08).
    _empresa(tmp_path, "00000001", "05", capital="2500,50", municipio="0139", filiais=("02", "08"))

    linha = _rodar(spark, tmp_path).first()

    assert (linha["id_municipio_rf"], linha["qtd_estabelecimentos"], linha["capital_social"],
            linha["id_cnae"], linha["id_natureza_juridica"], str(linha["data_inicio_atividade"])) == (
        "0139", 2, decimal.Decimal("2500.50"), "4711302", "2135", "2020-01-15",
    )


def test_matriz_baixada_fica_fora_da_fato(spark, tmp_path):
    _gravar(tmp_path, "empresas", [{"cnpj_basico": "00000001", "porte": "01", "capital_social": "0,00"}])
    _gravar(tmp_path, "estabelecimentos", [{"cnpj_basico": "00000001", "cnpj_ordem": "0001",
                                            "identificador_matriz_filial": "1", "situacao_cadastral": "08"}])
    _gravar(tmp_path, "simples", [])

    assert _rodar(spark, tmp_path).count() == 0


def test_reprocessar_o_mes_da_o_mesmo_resultado(spark, tmp_path):
    _empresa(tmp_path, "00000001", "01", ("S", "00000000"))

    primeira = _categorias(_rodar(spark, tmp_path))
    segunda = _categorias(_rodar(spark, tmp_path))

    assert primeira == segunda == [("2026-09", "00000001", "MEI")]


def test_dimensoes_fixas_e_do_dominio(spark, tmp_path):
    _empresa(tmp_path, "00000001", "01")
    _gravar(tmp_path, "cnaes", [{"codigo": "4711302", "descricao": " Comércio varejista "}])
    _gravar(tmp_path, "naturezas", [{"codigo": "2135", "descricao": "Empresário (Individual)"}])
    r, b, s, g = (str(tmp_path / camada) for camada in ("raw", "bronze", "silver", "gold"))
    _rodar(spark, tmp_path)
    local.bronze_dominios(spark, r, b, ANO_MES, dominios=["cnaes", "naturezas"])

    local.gold_dimensoes(spark, s, g, ANO_MES)

    def ler(dimensao):
        return sorted(tuple(r) for r in spark.read.format("delta").load(f"{g}/{dimensao}").collect())

    assert ler("dim_categoria") == [("DEMAIS", "Demais", 4), ("EPP", "EPP", 3), ("ME", "ME", 2), ("MEI", "MEI", 1)]
    assert ler("dim_cnae") == [("4711302", "Comércio varejista")]
    assert ler("dim_natureza_juridica") == [("2135", "Empresário (Individual)")]
    assert ler("dim_tempo") == [("2026-09", 2026, 9, 3)]


def test_cnpj_repetido_no_arquivo_de_empresas_vira_uma_linha_so(spark, tmp_path):
    # Como o 08314885 na base completa de 2026-09: uma linha com porte, outra sem.
    _gravar(tmp_path, "empresas", [{"cnpj_basico": "00000001", "porte": "", "capital_social": "0,00"},
                                   {"cnpj_basico": "00000001", "porte": "05", "capital_social": "0,00"}])
    _gravar(tmp_path, "estabelecimentos", [{"cnpj_basico": "00000001", "cnpj_ordem": "0001",
                                            "identificador_matriz_filial": "1", "situacao_cadastral": "02"}])
    _gravar(tmp_path, "simples", [])

    assert _categorias(_rodar(spark, tmp_path)) == [("2026-09", "00000001", "DEMAIS")]
    porte = spark.read.format("delta").load(str(tmp_path / "silver" / "empresas")).collect()
    assert [r["porte"] for r in porte] == ["05"]

