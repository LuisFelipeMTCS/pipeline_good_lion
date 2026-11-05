"""Ingestão da API de localidades do IBGE (municípios) para o bucket raw.

Compatível com Python 3.9 (job Python shell do Glue): só biblioteca padrão + boto3.
"""
import gzip
import json
import time
import urllib.request

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
TIMEOUT_SEGUNDOS = 60


def _baixar(url, tentativas):
    for tentativa in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resposta:
                corpo = resposta.read()
            # A API responde em gzip mesmo sem Accept-Encoding; o raw guarda o JSON aberto.
            return gzip.decompress(corpo) if corpo[:2] == b"\x1f\x8b" else corpo
        except OSError as erro:  # URLError e timeout são OSError
            print(f"API do IBGE, tentativa {tentativa}: {erro}", flush=True)
            if tentativa == tentativas:
                raise
            time.sleep(10)


def _ultimo_retrato(s3, bucket, prefixo):
    """Corpo do municipios.json mais recente já gravado no raw, ou None."""
    objetos = []
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=f"{prefixo}ibge_municipios/"):
        objetos += [o for o in pagina.get("Contents", []) if o["Key"].endswith("/municipios.json")]
    if not objetos:
        return None
    mais_recente = max(objetos, key=lambda o: o["Key"])
    print("usando o retrato anterior:", mais_recente["Key"], flush=True)
    return s3.get_object(Bucket=bucket, Key=mais_recente["Key"])["Body"].read()


def ingerir(ano_mes, s3, bucket, prefixo="", url=URL, tentativas=3):
    """Grava o JSON da API em <prefixo>ibge_municipios/ano_mes=<ano_mes>/municipios.json.

    Uma chave fixa por mês: rodar de novo substitui o arquivo. Se a API não responder (de dentro da AWS ela deu
    timeout), copia o retrato mais recente do raw para o mês: a lista de municípios quase nunca muda, e a cópia
    renova o arquivo antes da expiração de 30 dias do raw. Sem retrato anterior, a falha segue.
    """
    try:
        corpo = _baixar(url, tentativas)
    except OSError:
        corpo = _ultimo_retrato(s3, bucket, prefixo)
        if corpo is None:
            raise
    municipios = len(json.loads(corpo))
    chave = f"{prefixo}ibge_municipios/ano_mes={ano_mes}/municipios.json"
    s3.put_object(Bucket=bucket, Key=chave, Body=corpo, ContentType="application/json")
    print("gravado:", chave, flush=True)
    return municipios


def propriedades_do_workflow(argv, glue=None):
    """Propriedades da execução do Glue Workflow (ano_mes, ingestao), ou {} fora dele: dentro de um Workflow
    o Glue passa --WORKFLOW_NAME e --WORKFLOW_RUN_ID ao job."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--WORKFLOW_NAME")
    parser.add_argument("--WORKFLOW_RUN_ID")
    args, _ = parser.parse_known_args(argv)
    if not args.WORKFLOW_RUN_ID:
        return {}
    if glue is None:
        import boto3

        glue = boto3.client("glue")
    resposta = glue.get_workflow_run_properties(Name=args.WORKFLOW_NAME, RunId=args.WORKFLOW_RUN_ID)
    return resposta["RunProperties"]


def main(argv=None):
    import argparse
    import os
    import time

    import boto3

    parser = argparse.ArgumentParser(description="Grava os municípios do IBGE no raw.")
    parser.add_argument("--ano_mes", help="AAAA-MM; dentro do Workflow vem das propriedades da execução")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefixo", default="")
    args, _ = parser.parse_known_args(argv)  # o Glue acrescenta os próprios argumentos
    ano_mes = args.ano_mes or propriedades_do_workflow(argv)["ano_mes"]

    # S3_ENDPOINT aponta para o MinIO local; na AWS fica vazio e o boto3 usa o S3.
    s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT") or None)
    inicio = time.time()
    municipios = ingerir(ano_mes, s3, args.bucket, args.prefixo)
    # Linha lida pelo dashboard do CloudWatch (duração por execução).
    print(f"resumo job=ingest_ibge segundos={int(time.time() - inicio)} linhas={municipios} meses={ano_mes}")


if __name__ == "__main__":
    main()
