import gzip
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ingest.ibge import ingerir

pytestmark = pytest.mark.minio

MUNICIPIOS = [{"id": 1200401, "nome": "Rio Branco"}, {"id": 1600303, "nome": "Macapá"}]


@pytest.fixture
def ibge_falso():
    # A API de verdade responde em gzip mesmo sem Accept-Encoding.
    corpo = gzip.compress(json.dumps(MUNICIPIOS, ensure_ascii=False).encode("utf-8"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json;charset=UTF-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}/municipios"
    servidor.shutdown()


def test_grava_o_json_da_api_na_particao_do_mes(s3_raw, ibge_falso):
    s3, bucket, prefixo = s3_raw

    ingerir("2026-09", s3, bucket, prefixo, url=ibge_falso)
    ingerir("2026-09", s3, bucket, prefixo, url=ibge_falso)

    chaves = [o["Key"] for o in s3.list_objects_v2(Bucket=bucket, Prefix=prefixo)["Contents"]]
    assert chaves == [f"{prefixo}ibge_municipios/ano_mes=2026-09/municipios.json"]
    corpo = s3.get_object(Bucket=bucket, Key=chaves[0])["Body"].read().decode("utf-8")
    assert json.loads(corpo) == MUNICIPIOS
