"""Ingestão da Receita Federal (CNPJ) para o bucket raw.

Compatível com Python 3.9 (job Python shell do Glue): só biblioteca padrão + boto3.
"""
import base64
import contextlib
import io
import re
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

BASE_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav"
# Compartilhamento público da Receita: usuário = token, senha vazia.
TOKEN = "YggdBLfdninEJX9"
TIMEOUT_SEGUNDOS = 600

DOMINIOS = ["cnaes", "motivos", "municipios", "naturezas", "paises", "qualificacoes"]

# Nomes do SDK da Base dos Dados (br_me_cnpj), na ordem física dos arquivos da Receita.
COLUNAS = {
    "empresas": [
        "cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel",
        "capital_social", "porte", "ente_federativo",
    ],
    "estabelecimentos": [
        "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial", "nome_fantasia",
        "situacao_cadastral", "data_situacao_cadastral", "motivo_situacao_cadastral",
        "nome_cidade_exterior", "id_pais", "data_inicio_atividade", "cnae_fiscal_principal",
        "cnae_fiscal_secundaria", "tipo_logradouro", "logradouro", "numero", "complemento",
        "bairro", "cep", "sigla_uf", "id_municipio_rf", "ddd_1", "telefone_1", "ddd_2",
        "telefone_2", "ddd_fax", "fax", "email", "situacao_especial", "data_situacao_especial",
    ],
    "simples": [
        "cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
        "opcao_mei", "data_opcao_mei", "data_exclusao_mei",
    ],
    **{dominio: ["codigo", "descricao"] for dominio in DOMINIOS},
}

TAMANHO_BLOCO = 1024 * 1024

# Sócios fica fora do escopo (PRD, seção 3).
TABELAS_IGNORADAS = {"socios"}


def arquivos_do_mes(propfind_xml):
    """Mapeia cada ZIP listado no PROPFIND do mês para o nome da tabela (Empresas3.zip -> empresas)."""
    arquivos = {}
    for href in ET.fromstring(propfind_xml).iter("{DAV:}href"):
        nome = href.text.rstrip("/").rsplit("/", 1)[-1]
        if not nome.endswith(".zip"):
            continue
        tabela = re.sub(r"\d*\.zip$", "", nome).lower()
        if tabela not in TABELAS_IGNORADAS:
            arquivos[nome] = tabela
    return arquivos


class _FluxoDeBlocos(io.RawIOBase):
    """Expõe um gerador de blocos de bytes como arquivo binário legível."""

    def __init__(self, blocos):
        self._blocos = blocos
        self._resto = b""

    def readable(self):
        return True

    def readinto(self, buffer):
        while not self._resto:
            self._resto = next(self._blocos, b"")
            if not self._resto:
                return 0
        n = min(len(buffer), len(self._resto))
        buffer[:n] = self._resto[:n]
        self._resto = self._resto[n:]
        return n


@contextlib.contextmanager
def abrir_convertido(zip_path, tabela):
    """Abre o CSV de dentro do ZIP da Receita já em UTF-8 e com cabeçalho, em fluxo."""
    with zipfile.ZipFile(zip_path) as z, z.open(z.namelist()[0]) as membro:
        texto = io.TextIOWrapper(membro, encoding="latin1", newline="")

        def blocos():
            yield (";".join(COLUNAS[tabela]) + "\n").encode("utf-8")
            while True:
                pedaco = texto.read(TAMANHO_BLOCO)
                if not pedaco:
                    return
                yield pedaco.encode("utf-8")

        yield io.BufferedReader(_FluxoDeBlocos(blocos()), TAMANHO_BLOCO)


def _abrir_url(url, metodo="GET"):
    credencial = base64.b64encode(f"{TOKEN}:".encode()).decode()
    pedido = urllib.request.Request(
        url, method=metodo, headers={"Authorization": f"Basic {credencial}", "Depth": "1"}
    )
    return urllib.request.urlopen(pedido, timeout=TIMEOUT_SEGUNDOS)


def _limpar_prefixo(s3, bucket, prefixo):
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefixo):
        objetos = [{"Key": obj["Key"]} for obj in pagina.get("Contents", [])]
        if objetos:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objetos})


def ingerir_mes(ano_mes, s3, bucket, prefixo="", base_url=BASE_URL):
    """Baixa o mês da Receita e grava cada arquivo em <prefixo><tabela>/ano_mes=<ano_mes>/ no bucket."""
    with _abrir_url(f"{base_url}/{ano_mes}/", "PROPFIND") as resposta:
        arquivos = arquivos_do_mes(resposta.read())

    # Idempotência: a partição do mês é substituída inteira, sem sobras de rodadas anteriores.
    for tabela in set(arquivos.values()):
        _limpar_prefixo(s3, bucket, f"{prefixo}{tabela}/ano_mes={ano_mes}/")

    for nome, tabela in sorted(arquivos.items()):
        with tempfile.NamedTemporaryFile(suffix=".zip") as zip_local:
            with _abrir_url(f"{base_url}/{ano_mes}/{nome}") as resposta:
                shutil.copyfileobj(resposta, zip_local, TAMANHO_BLOCO)
            zip_local.flush()
            chave = f"{prefixo}{tabela}/ano_mes={ano_mes}/{nome[:-len('.zip')]}.csv"
            with abrir_convertido(zip_local.name, tabela) as csv_utf8:
                s3.upload_fileobj(csv_utf8, bucket, chave)


def main(argv=None):
    import argparse
    import os

    import boto3

    parser = argparse.ArgumentParser(description="Ingere um mês da Receita (CNPJ) no bucket raw.")
    parser.add_argument("--ano_mes", required=True, help="AAAA-MM")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefixo", default="")
    args, _ = parser.parse_known_args(argv)  # o Glue injeta argumentos próprios

    # S3_ENDPOINT aponta para o MinIO local; na AWS fica vazio e o boto3 usa o S3.
    s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT") or None)
    ingerir_mes(args.ano_mes, s3, args.bucket, args.prefixo)


if __name__ == "__main__":
    main()
