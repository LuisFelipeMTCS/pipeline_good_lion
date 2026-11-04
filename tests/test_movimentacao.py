"""silver_empresa_consolidada (MERGE + Change Data Feed) e fato_movimentacao_empresa, pelo executor local.
Roda no container do Glue contra o MinIO (o MERGE e a leitura do CDF são os Custom Transforms da AWS):

    make test-spark
"""
import uuid

import pytest

pytest.importorskip("awsglue")

from jobs import local  # noqa: E402


def _estado(cnpj, porte="01", mei=False, situacao="02"):
    return {"cnpj": cnpj, "porte": porte, "mei": mei, "situacao": situacao}


@pytest.fixture
def cdc(spark):
    """Grava a Silver de um mês num prefixo exclusivo do MinIO, roda o MERGE e a fato e devolve os eventos."""
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    id_teste = uuid.uuid4().hex[:8]
    silver, gold, tabela = f"s3a://silver/teste-{id_teste}", f"s3a://gold/teste-{id_teste}", f"teste{id_teste}"

    def _rodar(ano_mes, empresas):
        estab = [(e["cnpj"], 1, e["situacao"], e["situacao"] == "02", "0139", ano_mes) for e in empresas]
        tabelas = {
            "estabelecimentos": (estab, "cnpj_basico string, identificador_matriz_filial int, "
                                        "situacao_cadastral string, empresa_ativa boolean, id_municipio_rf string, "
                                        "ano_mes string"),
            "empresas": ([(e["cnpj"], e["porte"], ano_mes) for e in empresas],
                         "cnpj_basico string, porte string, ano_mes string"),
            "simples": ([(e["cnpj"], e["mei"], ano_mes) for e in empresas],
                        "cnpj_basico string, mei_ativo boolean, ano_mes string"),
        }
        for nome, (linhas, esquema) in tabelas.items():
            local._gravar_delta(spark.createDataFrame(linhas, esquema), f"{silver}/{nome}", ano_mes)
        local.silver_empresa_consolidada(spark, None, silver, ano_mes, tabela=tabela)
        local.gold_fato_movimentacao_empresa(spark, silver, gold, ano_mes, tabela=tabela)
        eventos = spark.read.format("delta").load(f"{gold}/fato_movimentacao_empresa").where(f"ano_mes = '{ano_mes}'")
        return sorted((r["cnpj_basico"], r["tipo_evento"], r["id_categoria"]) for r in eventos.collect())

    _rodar.consolidada = lambda: sorted(
        r["cnpj_basico"] for r in spark.read.format("delta").load(f"s3://silver/sample/{tabela}").collect()
    )
    yield _rodar
    import boto3

    s3 = boto3.resource("s3", endpoint_url="http://minio:9000")
    s3.Bucket("silver").objects.filter(Prefix=f"teste-{id_teste}/").delete()
    s3.Bucket("silver").objects.filter(Prefix=f"sample/{tabela}/").delete()
    s3.Bucket("gold").objects.filter(Prefix=f"teste-{id_teste}/").delete()


SETEMBRO = [
    _estado("00000001", mei=True),       # não muda
    _estado("00000002"),                 # passa a EPP
    _estado("00000003", mei=True),       # sai do MEI
    _estado("00000004"),                 # entra no MEI
    _estado("00000005"),                 # é baixada
    _estado("00000006"),                 # some do arquivo
]
OUTUBRO = [
    _estado("00000001", mei=True),
    _estado("00000002", porte="03"),
    _estado("00000003"),
    _estado("00000004", mei=True),
    _estado("00000005", situacao="08"),
    _estado("00000007"),                 # nova e ativa: abertura
    _estado("00000008", situacao="08"),  # nova mas já baixada: não é abertura
]
EVENTOS_OUTUBRO = [
    ("00000002", "mudanca_porte", "EPP"),
    ("00000003", "saida_mei", "ME"),
    ("00000004", "entrada_mei", "MEI"),
    ("00000005", "baixa", "ME"),
    ("00000007", "abertura", "ME"),
]


def test_carga_inicial_nao_gera_eventos_e_o_mes_seguinte_gera_os_cinco_tipos(cdc):
    assert cdc("2026-09", SETEMBRO) == []

    assert cdc("2026-10", OUTUBRO) == EVENTOS_OUTUBRO
    # O que deixou de existir sai da consolidada (whenNotMatchedBySource), sem virar evento.
    assert cdc.consolidada() == ["00000001", "00000002", "00000003", "00000004", "00000005", "00000007", "00000008"]


def test_rodar_o_merge_do_mesmo_mes_de_novo_nao_duplica_eventos(cdc):
    cdc("2026-09", SETEMBRO)
    cdc("2026-10", OUTUBRO)

    assert cdc("2026-10", OUTUBRO) == EVENTOS_OUTUBRO
