import psycopg
import pyarrow as pa
import pytest
from deltalake import write_deltalake

from dashboard.carga import carregar_mes


def _gravar_gold(raiz, linhas):
    """Gold no mesmo esquema que o Spark grava (ano_mes, sigla_uf, qtd_empresas_ativas)."""
    tabela = pa.table({
        "ano_mes": [linha[0] for linha in linhas],
        "sigla_uf": [linha[1] for linha in linhas],
        "qtd_empresas_ativas": pa.array([linha[2] for linha in linhas], pa.int64()),
    })
    write_deltalake(str(raiz / "ativas_por_uf"), tabela, partition_by=["ano_mes"], mode="overwrite")


def _painel(conninfo):
    with psycopg.connect(conninfo) as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT ano_mes, sigla_uf, qtd_empresas_ativas FROM mv_ativas_por_uf ORDER BY 1, 2")
        return cursor.fetchall()


@pytest.mark.postgres
def test_carga_do_mes_aparece_na_visao_do_dashboard(postgres, tmp_path):
    _gravar_gold(tmp_path, [("2026-09", "AC", 3), ("2026-09", "RR", 1)])

    carregar_mes(str(tmp_path), "2026-09", postgres)

    assert _painel(postgres) == [("2026-09", "AC", 3), ("2026-09", "RR", 1)]


@pytest.mark.postgres
def test_carregar_o_mesmo_mes_duas_vezes_da_o_mesmo_resultado(postgres, tmp_path):
    _gravar_gold(tmp_path, [("2026-09", "AC", 3), ("2026-09", "RR", 1)])

    carregar_mes(str(tmp_path), "2026-09", postgres)
    carregar_mes(str(tmp_path), "2026-09", postgres)

    assert _painel(postgres) == [("2026-09", "AC", 3), ("2026-09", "RR", 1)]


@pytest.mark.postgres
def test_carregar_um_mes_nao_apaga_o_outro(postgres, tmp_path):
    _gravar_gold(tmp_path, [("2026-09", "AC", 3), ("2026-10", "AC", 4)])

    carregar_mes(str(tmp_path), "2026-09", postgres)
    carregar_mes(str(tmp_path), "2026-10", postgres)

    assert _painel(postgres) == [("2026-09", "AC", 3), ("2026-10", "AC", 4)]
