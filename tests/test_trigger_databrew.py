import pytest

from ingest.trigger_databrew import executar


class DataBrewFalso:
    """A API do DataBrew é fronteira externa: devolve os estados em sequência a cada consulta."""

    def __init__(self, estados):
        self.estados = list(estados)
        self.iniciados = []

    def start_job_run(self, Name):
        self.iniciados.append(Name)
        return {"RunId": "run-1"}

    def describe_job_run(self, Name, RunId):
        estado = self.estados.pop(0)
        return {"State": estado, "ErrorMessage": "coluna nome não existe" if estado == "FAILED" else ""}


def test_dispara_o_job_e_espera_terminar():
    databrew = DataBrewFalso(["STARTING", "RUNNING", "SUCCEEDED"])

    assert executar(databrew, "goodlion-limpeza-ibge", intervalo=0) == "SUCCEEDED"
    assert databrew.iniciados == ["goodlion-limpeza-ibge"]
    assert databrew.estados == []


def test_falha_do_databrew_falha_o_job_do_glue():
    databrew = DataBrewFalso(["RUNNING", "FAILED"])

    with pytest.raises(RuntimeError, match="FAILED: coluna nome não existe"):
        executar(databrew, "goodlion-limpeza-ibge", intervalo=0)
