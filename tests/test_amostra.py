import csv

import pytest

from amostra.gerar_amostra import gerar_amostra
from ingest.receita import COLUNAS, DOMINIOS

ANO_MES = "2026-09"


def _gravar(raiz, tabela, linhas, arquivo="Parte0.csv"):
    pasta = raiz / tabela / f"ano_mes={ANO_MES}"
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / arquivo, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        f.write(";".join(COLUNAS[tabela]) + "\n")
        for linha in linhas:
            escritor.writerow([linha.get(coluna, "") for coluna in COLUNAS[tabela]])


def _ler(raiz, tabela):
    linhas = []
    for arquivo in sorted((raiz / tabela / f"ano_mes={ANO_MES}").glob("*.csv")):
        with open(arquivo, encoding="utf-8", newline="") as f:
            linhas += list(csv.DictReader(f, delimiter=";"))
    return linhas


@pytest.fixture
def raw(tmp_path):
    raiz = tmp_path / "raw"
    _gravar(raiz, "estabelecimentos", [
        {"cnpj_basico": "00000001", "cnpj_ordem": "0001", "sigla_uf": "AC"},
        {"cnpj_basico": "00000001", "cnpj_ordem": "0002", "sigla_uf": "SP"},  # filial fora do recorte
        {"cnpj_basico": "00000002", "cnpj_ordem": "0001", "sigla_uf": "SP"},
    ], "Estabelecimentos0.csv")
    _gravar(raiz, "estabelecimentos", [
        {"cnpj_basico": "00000003", "cnpj_ordem": "0001", "sigla_uf": "RR"},
        {"cnpj_basico": "00000004", "cnpj_ordem": "0001", "sigla_uf": "AP"},
    ], "Estabelecimentos1.csv")
    _gravar(raiz, "empresas", [
        {"cnpj_basico": f"0000000{i}", "razao_social": f"EMPRESA {i}", "porte": "01"}
        for i in range(1, 6)  # 00000005 não tem estabelecimento
    ])
    _gravar(raiz, "simples", [
        {"cnpj_basico": "00000001", "opcao_mei": "S"},
        {"cnpj_basico": "00000002", "opcao_mei": "S"},
        {"cnpj_basico": "00000003", "opcao_mei": "N"},
    ], "Simples.csv")
    _gravar(raiz, "municipios", [
        {"codigo": "0139", "descricao": "RIO BRANCO"},
        {"codigo": "7107", "descricao": "SAO PAULO"},
    ], "Municipios.csv")
    for dominio in set(DOMINIOS) - {"municipios"}:
        _gravar(raiz, dominio, [{"codigo": "1", "descricao": "QUALQUER"}])
    return raiz


def test_amostra_tem_so_estabelecimentos_de_ac_ap_rr(raw, tmp_path):
    destino = tmp_path / "sample"

    gerar_amostra(str(raw), str(destino), ANO_MES)

    estabelecimentos = _ler(destino, "estabelecimentos")
    assert sorted((e["cnpj_basico"], e["cnpj_ordem"], e["sigla_uf"]) for e in estabelecimentos) == [
        ("00000001", "0001", "AC"),
        ("00000003", "0001", "RR"),
        ("00000004", "0001", "AP"),
    ]


def test_amostra_tem_as_empresas_dos_estabelecimentos_do_recorte(raw, tmp_path):
    destino = tmp_path / "sample"

    gerar_amostra(str(raw), str(destino), ANO_MES)

    empresas = _ler(destino, "empresas")
    assert sorted(e["cnpj_basico"] for e in empresas) == ["00000001", "00000003", "00000004"]


def test_amostra_tem_o_simples_das_empresas_do_recorte(raw, tmp_path):
    destino = tmp_path / "sample"

    gerar_amostra(str(raw), str(destino), ANO_MES)

    simples = _ler(destino, "simples")
    assert sorted(s["cnpj_basico"] for s in simples) == ["00000001", "00000003"]


def test_amostra_copia_os_dominios_inteiros(raw, tmp_path):
    destino = tmp_path / "sample"

    gerar_amostra(str(raw), str(destino), ANO_MES)

    assert _ler(destino, "municipios") == [
        {"codigo": "0139", "descricao": "RIO BRANCO"},
        {"codigo": "7107", "descricao": "SAO PAULO"},
    ]
