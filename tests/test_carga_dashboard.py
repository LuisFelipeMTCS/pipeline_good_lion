import datetime
import decimal

import psycopg
import pyarrow as pa
import pytest
from deltalake import write_deltalake

from dashboard.carga import carregar_mes

pytestmark = pytest.mark.postgres

MUNICIPIOS = [("0139", "1200401", "Rio Branco", "AC", "Norte"), ("0605", "1600303", "Macapá", "AP", "Norte")]
CATEGORIAS = [("MEI", "MEI", 1), ("ME", "ME", 2), ("EPP", "EPP", 3), ("DEMAIS", "Demais", 4)]


def _gravar_gold(raiz, fato, capitais=None):
    """Gold no esquema que o Spark grava. `fato`: (ano_mes, cnpj_basico, id_municipio_rf, id_categoria);
    `capitais`: capital social de cada linha (padrão R$ 1.000)."""
    capitais = capitais or ["1000.00"] * len(fato)
    write_deltalake(str(raiz / "dim_municipio"), pa.table({
        nome: [m[i] for m in MUNICIPIOS]
        for i, nome in enumerate(["id_municipio_rf", "id_municipio_ibge", "nome", "sigla_uf", "regiao"])
    }), mode="overwrite")
    write_deltalake(str(raiz / "dim_categoria"), pa.table({
        "id_categoria": [c[0] for c in CATEGORIAS], "nome": [c[1] for c in CATEGORIAS],
        "ordem": pa.array([c[2] for c in CATEGORIAS], pa.int32()),
    }), mode="overwrite")
    write_deltalake(str(raiz / "fato_empresa_mensal"), pa.table({
        "cnpj_basico": [f[1] for f in fato],
        "id_municipio_rf": [f[2] for f in fato],
        "id_categoria": [f[3] for f in fato],
        "id_cnae": ["4711302"] * len(fato),
        "id_natureza_juridica": ["2135"] * len(fato),
        "data_inicio_atividade": [datetime.date(2020, 1, 15)] * len(fato),
        "capital_social": pa.array([decimal.Decimal(c) for c in capitais], pa.decimal128(18, 2)),
        "qtd_estabelecimentos": pa.array([1] * len(fato), pa.int64()),
        "ano_mes": [f[0] for f in fato],
    }), partition_by=["ano_mes"], mode="overwrite")


def _painel(conninfo, visao="mv_categorias_uf"):
    with psycopg.connect(conninfo) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            f"SELECT ano_mes, sigla_uf, categoria, qtd_empresas, proporcao FROM {visao} ORDER BY 1, 2, ordem"
        )
        return [(a, uf, c, q, float(p)) for a, uf, c, q, p in cursor.fetchall()]


FATO = [
    ("2026-09", "00000001", "0139", "MEI"),
    ("2026-09", "00000002", "0139", "MEI"),
    ("2026-09", "00000003", "0139", "ME"),
    ("2026-09", "00000004", "0605", "DEMAIS"),
    ("2026-10", "00000001", "0139", "MEI"),
]


def test_carga_mostra_quantidade_e_proporcao_por_categoria(postgres, tmp_path):
    _gravar_gold(tmp_path, FATO)

    carregar_mes(str(tmp_path), "2026-09", postgres)

    assert _painel(postgres) == [
        ("2026-09", "AC", "MEI", 2, 0.6667),
        ("2026-09", "AC", "ME", 1, 0.3333),
        ("2026-09", "AP", "Demais", 1, 1.0),
    ]
    with psycopg.connect(postgres) as conexao:
        regiao = conexao.execute(
            "SELECT regiao, categoria, qtd_empresas FROM mv_categorias_regiao ORDER BY ordem"
        ).fetchall()
        municipio = conexao.execute(
            "SELECT municipio, qtd_empresas FROM mv_categorias_municipio WHERE categoria = 'MEI'"
        ).fetchall()
    assert regiao == [("Norte", "MEI", 2), ("Norte", "ME", 1), ("Norte", "Demais", 1)]
    assert municipio == [("Rio Branco", 2)]


def test_carregar_o_mesmo_mes_duas_vezes_da_o_mesmo_resultado(postgres, tmp_path):
    _gravar_gold(tmp_path, FATO)

    carregar_mes(str(tmp_path), "2026-09", postgres)
    primeira = _painel(postgres)
    carregar_mes(str(tmp_path), "2026-09", postgres)

    assert _painel(postgres) == primeira


def test_carregar_um_mes_nao_apaga_o_outro(postgres, tmp_path):
    _gravar_gold(tmp_path, FATO)

    carregar_mes(str(tmp_path), "2026-09", postgres)
    carregar_mes(str(tmp_path), "2026-10", postgres)

    assert [linha[:4] for linha in _painel(postgres)] == [
        ("2026-09", "AC", "MEI", 2), ("2026-09", "AC", "ME", 1), ("2026-09", "AP", "Demais", 1),
        ("2026-10", "AC", "MEI", 1),
    ]


def test_capital_social_com_mediana_e_soma_por_uf_e_regiao(postgres, tmp_path):
    # Um valor extremo (erro de cadastro na casa do bilhão) mexe na soma, não na mediana.
    _gravar_gold(tmp_path, FATO, capitais=["1.00", "5000.00", "20000.00", "1000000000.00", "10.00"])

    carregar_mes(str(tmp_path), "2026-09", postgres)

    with psycopg.connect(postgres) as conexao:
        uf = conexao.execute(
            "SELECT sigla_uf, qtd_empresas, mediana_capital_social, soma_capital_social FROM mv_capital_uf ORDER BY 1"
        ).fetchall()
        regiao = conexao.execute("SELECT regiao, mediana_capital_social FROM mv_capital_regiao").fetchall()
    assert uf == [
        ("AC", 3, decimal.Decimal("5000.00"), decimal.Decimal("25001.00")),
        ("AP", 1, decimal.Decimal("1000000000.00"), decimal.Decimal("1000000000.00")),
    ]
    assert regiao == [("Norte", decimal.Decimal("12500.00"))]

