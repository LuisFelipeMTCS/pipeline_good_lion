import pytest

from ingest.receita import ingerir_mes

pytestmark = pytest.mark.minio


def _chaves(s3, bucket, prefixo):
    resposta = s3.list_objects_v2(Bucket=bucket, Prefix=prefixo)
    return sorted(obj["Key"][len(prefixo):] for obj in resposta.get("Contents", []))


def test_grava_cada_tabela_na_particao_do_mes_sem_socios(s3_raw, receita_falsa):
    s3, bucket, prefixo = s3_raw

    ingerir_mes("2026-09", s3, bucket, prefixo, base_url=receita_falsa)

    assert _chaves(s3, bucket, prefixo) == [
        "empresas/ano_mes=2026-09/Empresas0.csv",
        "simples/ano_mes=2026-09/Simples.csv",
    ]
    empresas = s3.get_object(Bucket=bucket, Key=f"{prefixo}empresas/ano_mes=2026-09/Empresas0.csv")
    assert empresas["Body"].read().decode("utf-8").splitlines()[1] == (
        '"00000001";"PADARIA SÃO JOÃO";"2135";"50";"1000,00";"01";""'
    )


def test_reprocessar_o_mes_substitui_a_particao_inteira(s3_raw, receita_falsa):
    s3, bucket, prefixo = s3_raw
    # Sobra de uma rodada anterior em que a Receita publicou mais arquivos.
    s3.put_object(Bucket=bucket, Key=f"{prefixo}empresas/ano_mes=2026-09/Empresas9.csv", Body=b"velho")
    # Outro mês não pode ser tocado.
    s3.put_object(Bucket=bucket, Key=f"{prefixo}empresas/ano_mes=2026-08/Empresas0.csv", Body=b"agosto")

    ingerir_mes("2026-09", s3, bucket, prefixo, base_url=receita_falsa)
    ingerir_mes("2026-09", s3, bucket, prefixo, base_url=receita_falsa)

    assert _chaves(s3, bucket, prefixo) == [
        "empresas/ano_mes=2026-08/Empresas0.csv",
        "empresas/ano_mes=2026-09/Empresas0.csv",
        "simples/ano_mes=2026-09/Simples.csv",
    ]
