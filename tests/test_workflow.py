"""Como os jobs recebem o mês dentro do Glue Workflow (propriedades da execução)."""
import datetime

import pytest

from ingest import receita
from ingest.definir_mes import definir


class GlueFalso:
    """A API do Glue é fronteira externa: guarda as propriedades de uma execução do Workflow."""

    def __init__(self, propriedades):
        self.propriedades = dict(propriedades)

    def get_workflow_run_properties(self, Name, RunId):
        return {"RunProperties": dict(self.propriedades)}

    def put_workflow_run_properties(self, Name, RunId, RunProperties):
        self.propriedades.update(RunProperties)


def test_gatilho_mensal_sem_mes_usa_o_mes_corrente():
    glue = GlueFalso({})

    assert definir(glue, "goodlion", "wr_1", hoje=datetime.date(2026, 11, 20)) == "2026-11"
    assert glue.propriedades == {"ano_mes": "2026-11"}


def test_sob_demanda_o_mes_informado_vale():
    glue = GlueFalso({"ano_mes": "2026-09", "ingestao": "nao"})

    assert definir(glue, "goodlion", "wr_1", hoje=datetime.date(2026, 11, 20)) == "2026-09"
    assert glue.propriedades == {"ano_mes": "2026-09", "ingestao": "nao"}


def test_mes_mal_escrito_para_o_workflow_no_primeiro_passo():
    with pytest.raises(ValueError, match="ano_mes inválido"):
        definir(GlueFalso({"ano_mes": "09/2026"}), "goodlion", "wr_1")


def test_fora_do_workflow_nao_ha_propriedades():
    assert receita.propriedades_do_workflow(["--ano_mes", "2026-09"]) == {}


def test_dentro_do_workflow_le_as_propriedades_da_execucao():
    argv = ["--WORKFLOW_NAME", "goodlion", "--WORKFLOW_RUN_ID", "wr_1", "--bucket", "raw"]

    assert receita.propriedades_do_workflow(argv, GlueFalso({"ano_mes": "2026-10"})) == {"ano_mes": "2026-10"}


def test_ingestao_nao_pula_o_download(monkeypatch, capsys):
    monkeypatch.setattr(receita, "propriedades_do_workflow", lambda argv: {"ano_mes": "2026-09", "ingestao": "nao"})
    monkeypatch.setattr(receita, "ingerir_mes", lambda *a, **k: pytest.fail("não devia baixar"))

    receita.main(["--bucket", "raw", "--WORKFLOW_NAME", "goodlion", "--WORKFLOW_RUN_ID", "wr_1"])

    assert "meses=2026-09" in capsys.readouterr().out
