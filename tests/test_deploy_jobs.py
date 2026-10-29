import json

from scripts import deploy_jobs, exportar_job


def test_deploy_troca_marcadores_pelo_conteudo_dos_arquivos():
    job = deploy_jobs.montar(json.loads((deploy_jobs.RAIZ / "glue/jobs/bronze_estabelecimentos.json").read_text()))

    nos = job["CodeGenConfigurationNodes"]
    sql = (deploy_jobs.RAIZ / "jobs/sql/bronze/estabelecimentos.sql").read_text()
    assert nos["node-sql"]["SparkSQL"]["SqlQuery"] == sql
    assert "replaceWhere" in nos["node-gravar"]["CustomCode"]["Code"]
    assert "@arquivo:" not in json.dumps(job)


def test_exportar_grava_no_arquivo_o_sql_editado_e_devolve_o_marcador(tmp_path, monkeypatch):
    monkeypatch.setattr(exportar_job, "RAIZ", tmp_path)
    (tmp_path / "jobs").mkdir()
    atual = {"Nos": {"n1": {"SqlQuery": {"SqlQuery": "@arquivo:jobs/x.sql", "Name": "x"}}}}
    vindo_do_glue = {"Nos": {"n1": {"SqlQuery": {"SqlQuery": "SELECT 2", "Name": "x"}}}}

    assert exportar_job.devolver_marcadores(vindo_do_glue, atual) == atual
    assert (tmp_path / "jobs/x.sql").read_text() == "SELECT 2"
