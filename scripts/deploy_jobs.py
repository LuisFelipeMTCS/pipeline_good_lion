"""Publica os jobs visuais de glue/jobs/*.json: troca cada "@arquivo:<caminho>" pelo conteúdo do arquivo
(SQL, DQDL, Custom Transform) e roda create-job/update-job.

    uv run python scripts/deploy_jobs.py [glue/jobs/<job>.json ...]
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


def main(arquivos):
    import boto3

    glue = boto3.client("glue", region_name="us-east-1")
    for arquivo in arquivos or sorted((RAIZ / "glue" / "jobs").glob("*.json")):
        job = montar(json.loads(Path(arquivo).read_text(encoding="utf-8")))
        nome = job.pop("Name")
        try:
            glue.update_job(JobName=nome, JobUpdate=job)
            print("atualizado:", nome)
        except glue.exceptions.EntityNotFoundException:
            glue.create_job(Name=nome, **job)
            print("criado:", nome)


if __name__ == "__main__":
    main(sys.argv[1:])
