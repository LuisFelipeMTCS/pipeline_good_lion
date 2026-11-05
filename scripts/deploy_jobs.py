"""Publica os jobs visuais de glue/jobs/*.json: troca cada "@arquivo:<caminho>" pelo conteúdo do arquivo
(SQL, DQDL, Custom Transform) e roda create-job/update-job.

    uv run python scripts/deploy_jobs.py [--ambiente full] [glue/jobs/<job>.json ...]

Os JSON descrevem a amostra. Com --ambiente full (rodada final, ticket 17) os mesmos jobs são publicados para a
base completa: caminhos sem o prefixo sample/, tabelas full_<tabela> do raw no Catalog, --ambiente full, até 10
workers (PRD, 5.3) e timeout maior. Para voltar à amostra, publique de novo sem a opção.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCADOR = "@arquivo:"


def montar(valor):
    if isinstance(valor, dict):
        return {chave: montar(v) for chave, v in valor.items()}
    if isinstance(valor, list):
        return [montar(v) for v in valor]
    if isinstance(valor, str) and valor.startswith(MARCADOR):
        return (RAIZ / valor[len(MARCADOR):]).read_text(encoding="utf-8")
    return valor


# Jobs pequenos (domínios e dimensões fixas) ficam com 2 workers mesmo na base completa.
WORKERS_FULL = {"bronze_dominios": 2, "gold_dimensoes": 2}


def para_full(job):
    """O mesmo job, apontado para a base completa."""
    def trocar(valor):
        if isinstance(valor, dict):
            return {chave: trocar(v) for chave, v in valor.items()}
        if isinstance(valor, list):
            return [trocar(v) for v in valor]
        if isinstance(valor, str) and valor.startswith("s3://"):
            return valor.replace("/sample/", "/")
        return valor

    job = trocar(job)
    for no in job.get("CodeGenConfigurationNodes", {}).values():
        origem = no.get("CatalogSource")
        if origem and origem["Database"] == "goodlion_raw":
            origem["Table"] = f"full_{origem['Table']}"
    job["DefaultArguments"]["--ambiente"] = "full"
    if job["Command"]["Name"] == "glueetl":
        job["NumberOfWorkers"] = WORKERS_FULL.get(job["Name"], 10)
        job["Timeout"] = 180
    return job


def main(arquivos):
    import boto3

    glue = boto3.client("glue", region_name="us-east-1")
    full = "--ambiente" in arquivos and arquivos[arquivos.index("--ambiente") + 1] == "full"
    arquivos = [a for a in arquivos if a not in ("--ambiente", "full", "sample")]
    for arquivo in arquivos or sorted((RAIZ / "glue" / "jobs").glob("*.json")):
        job = montar(json.loads(Path(arquivo).read_text(encoding="utf-8")))
        if full:
            job = para_full(job)
        nome = job.pop("Name")
        try:
            glue.update_job(JobName=nome, JobUpdate=job)
            print("atualizado:", nome)
        except glue.exceptions.EntityNotFoundException:
            glue.create_job(Name=nome, **job)
            print("criado:", nome)


if __name__ == "__main__":
    main(sys.argv[1:])
