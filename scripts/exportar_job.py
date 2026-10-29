"""Traz de volta para o repositório um job editado no Glue Studio (get-job → glue/jobs/<job>.json).

O texto dos campos que no JSON atual são "@arquivo:<caminho>" é gravado nesses arquivos (assim uma edição
de SQL feita no editor vai para o .sql) e o marcador volta para o JSON.

    uv run python scripts/exportar_job.py <nome do job>
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCADOR = "@arquivo:"
# Campos que o update-job aceita; o resto do get-job é só leitura (datas, capacidade calculada...).
CAMPOS = [
    "Name", "Description", "Role", "GlueVersion", "WorkerType", "NumberOfWorkers", "ExecutionClass",
    "MaxRetries", "Timeout", "Command", "DefaultArguments", "CodeGenConfigurationNodes",
]


def devolver_marcadores(novo, atual):
    """Onde o JSON atual tem marcador, grava o texto vindo do Glue no arquivo e põe o marcador de volta."""
    if isinstance(atual, str) and atual.startswith(MARCADOR):
        (RAIZ / atual[len(MARCADOR):]).write_text(novo, encoding="utf-8")
        return atual
    if isinstance(novo, dict) and isinstance(atual, dict):
        return {chave: devolver_marcadores(v, atual.get(chave)) for chave, v in novo.items()}
    if isinstance(novo, list) and isinstance(atual, list) and len(novo) == len(atual):
        return [devolver_marcadores(n, a) for n, a in zip(novo, atual)]
    return novo


def main(nome):
    import boto3

    job = boto3.client("glue", region_name="us-east-1").get_job(JobName=nome)["Job"]
    caminho = RAIZ / "glue" / "jobs" / f"{nome}.json"
    atual = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    exportado = devolver_marcadores({c: job[c] for c in CAMPOS if c in job}, atual)
    caminho.write_text(json.dumps(exportado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("exportado:", caminho.relative_to(RAIZ))


if __name__ == "__main__":
    main(sys.argv[1])
