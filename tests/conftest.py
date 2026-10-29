import io
import os
import threading
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
import pytest
from botocore.exceptions import EndpointConnectionError


@pytest.fixture
def s3_raw():
    """Cliente do MinIO local e um prefixo exclusivo do teste no bucket raw (apagado ao final)."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "goodlion"),
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "goodlion123"),
        region_name="us-east-1",
    )
    try:
        s3.head_bucket(Bucket="raw")
    except EndpointConnectionError:
        pytest.skip("MinIO fora do ar: rode `docker compose up -d minio minio-init`")
    prefixo = f"teste-{uuid.uuid4().hex[:8]}/"
    yield s3, "raw", prefixo
    for obj in s3.list_objects_v2(Bucket="raw", Prefix=prefixo).get("Contents", []):
        s3.delete_object(Bucket="raw", Key=obj["Key"])


@pytest.fixture(scope="session")
def spark():
    """SparkSession local com Delta (só no container do Glue)."""
    pytest.importorskip("pyspark")
    from jobs.spark import criar_spark

    sessao = criar_spark(master="local[1]")
    sessao.conf.set("spark.sql.shuffle.partitions", "1")
    yield sessao
    sessao.stop()


def _zip(conteudo_latin1):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ARQUIVO.CSV", conteudo_latin1)
    return buffer.getvalue()


@pytest.fixture
def receita_falsa():
    """WebDAV falso com o mês 2026-09: Empresas0, Simples e Socios0. Devolve a URL base."""
    arquivos = {
        "Empresas0.zip": _zip('"00000001";"PADARIA SÃO JOÃO";"2135";"50";"1000,00";"01";""\n'.encode("latin1")),
        "Simples.zip": _zip(b'"00000001";"S";"20200101";"00000000";"S";"20200101";"00000000"\n'),
        "Socios0.zip": _zip(b'"00000001";"2";"FULANO";"***123456**"\n'),
    }
    hrefs = "".join(
        f"<d:response><d:href>/webdav/2026-09/{nome}</d:href></d:response>" for nome in arquivos
    )
    propfind = (
        '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">'
        f"<d:response><d:href>/webdav/2026-09/</d:href></d:response>{hrefs}</d:multistatus>"
    ).encode()

    class Handler(BaseHTTPRequestHandler):
        def _responder(self, corpo, status=200):
            self.send_response(status)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_PROPFIND(self):
            self._responder(propfind, 207)

        def do_GET(self):
            self._responder(arquivos[self.path.rsplit("/", 1)[-1]])

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}/webdav"
    servidor.shutdown()


@pytest.fixture
def postgres():
    """Banco exclusivo do teste no Postgres do docker compose (apagado ao final). Devolve o conninfo."""
    psycopg = pytest.importorskip("psycopg")
    base = (
        f"host=localhost port=5432 user={os.environ.get('POSTGRES_USER', 'goodlion')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'goodlion123')}"
    )
    try:
        admin = psycopg.connect(f"{base} dbname=dashboard", autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("Postgres fora do ar: rode `docker compose up -d postgres`")
    nome = f"teste_{uuid.uuid4().hex[:8]}"
    admin.execute(f"CREATE DATABASE {nome}")
    yield f"{base} dbname={nome}"
    admin.execute(f"DROP DATABASE {nome} WITH (FORCE)")
    admin.close()
