import json
from pathlib import Path

from ingest.receita import COLUNAS


def test_tabelas_do_catalog_do_raw_tem_as_colunas_da_ingestao():
    # O Terraform cria as tabelas do raw a partir deste JSON; a ingestão grava o cabeçalho a partir do COLUNAS.
    assert json.loads((Path(__file__).parent.parent / "infra" / "colunas_raw.json").read_text()) == COLUNAS
