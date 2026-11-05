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


def test_todos_os_jobs_montam_e_o_no_antes_do_gravar_delta_da_o_nome_da_tabela():
    for arquivo in sorted((deploy_jobs.RAIZ / "glue/jobs").glob("*.json")):
        # montar() falha se um marcador aponta para arquivo inexistente.
        job = deploy_jobs.montar(json.loads(arquivo.read_text()))
        nos = job["CodeGenConfigurationNodes"]
        camada = job["Name"].split("_", 1)[0]
        for no in nos.values():
            if no.get("CustomCode", {}).get("ClassName", "").startswith("GravarDelta"):
                anterior = next(iter(nos[no["CustomCode"]["Inputs"][0]].values()))["Name"]
                assert anterior.startswith(f"{camada}_"), (arquivo.name, anterior)


def test_full_aponta_os_mesmos_jobs_para_a_base_completa():
    def ler(nome):
        return deploy_jobs.para_full(json.loads((deploy_jobs.RAIZ / f"glue/jobs/{nome}.json").read_text()))

    bronze, silver, dominios = ler("bronze_estabelecimentos"), ler("silver_empresas"), ler("bronze_dominios")

    assert bronze["CodeGenConfigurationNodes"]["node-raw"]["CatalogSource"]["Table"] == "full_estabelecimentos"
    assert (bronze["DefaultArguments"]["--ambiente"], bronze["NumberOfWorkers"], bronze["Timeout"]) == ("full", 10, 180)
    assert silver["CodeGenConfigurationNodes"]["node-empresas"]["S3DeltaSource"]["Paths"] == [
        "s3://goodlion-bronze-724793286570/empresas/"]
    assert "/sample/" not in json.dumps(silver)
    assert dominios["NumberOfWorkers"] == 2

