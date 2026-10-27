from pathlib import Path

from ingest.receita import arquivos_do_mes

PROPFIND_2026_09 = (Path(__file__).parent / "fixtures" / "propfind_2026-09.xml").read_bytes()


def test_lista_os_arquivos_do_mes_por_tabela_sem_socios():
    arquivos = arquivos_do_mes(PROPFIND_2026_09)

    esperado = {
        **{f"Empresas{i}.zip": "empresas" for i in range(10)},
        **{f"Estabelecimentos{i}.zip": "estabelecimentos" for i in range(10)},
        "Simples.zip": "simples",
        "Cnaes.zip": "cnaes",
        "Motivos.zip": "motivos",
        "Municipios.zip": "municipios",
        "Naturezas.zip": "naturezas",
        "Paises.zip": "paises",
        "Qualificacoes.zip": "qualificacoes",
    }
    assert arquivos == esperado
