"""Atalhos para coletar evidências na AWS (us-east-1, perfil default):

    uv run python scripts/aws.py job <nome> [--ano_mes AAAA-MM] [--arg chave=valor ...]
        dispara o job do Glue, espera terminar e imprime estado, tempo, DPU-s e erro
    uv run python scripts/aws.py athena "<SQL>"
        roda no workgroup goodlion e imprime as linhas, o volume lido e o tempo
"""
import sys
import time

import boto3

REGIAO = "us-east-1"
FINAIS_JOB = {"SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED", "ERROR"}


def rodar_job(nome, argumentos):
    glue = boto3.client("glue", region_name=REGIAO)
    # Logo depois de uma execução terminar, o Glue ainda pode recusar outra (uma por vez): tenta de novo.
    for _ in range(10):
        try:
            execucao = glue.start_job_run(JobName=nome, Arguments=argumentos)["JobRunId"]
            break
        except glue.exceptions.ConcurrentRunsExceededException:
            time.sleep(30)
    else:
        raise SystemExit(f"{nome}: outra execução não termina")
    while True:
        r = glue.get_job_run(JobName=nome, RunId=execucao)["JobRun"]
        if r["JobRunState"] in FINAIS_JOB:
            break
        time.sleep(20)
    dpu = r.get("DPUSeconds") or r.get("ExecutionTime", 0) * 2
    print(f"{nome} {r['JobRunState']} {r.get('ExecutionTime', 0)}s dpu_s={dpu:.0f} id={r['Id']} "
          f"{(r.get('ErrorMessage') or '')[:400]}")
    return r["JobRunState"] == "SUCCEEDED"


def athena(sql):
    cliente = boto3.client("athena", region_name=REGIAO)
    consulta = cliente.start_query_execution(QueryString=sql, WorkGroup="goodlion")["QueryExecutionId"]
    while True:
        q = cliente.get_query_execution(QueryExecutionId=consulta)["QueryExecution"]
        if q["Status"]["State"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(2)
    s = q["Statistics"]
    print(f"-- {q['Status']['State']} lidos={s.get('DataScannedInBytes', 0) / 1e6:.2f}MB "
          f"tempo={s.get('EngineExecutionTimeInMillis', 0) / 1000:.2f}s {q['Status'].get('StateChangeReason', '')}")
    if q["Status"]["State"] == "SUCCEEDED":
        for pagina in cliente.get_paginator("get_query_results").paginate(QueryExecutionId=consulta):
            for linha in pagina["ResultSet"]["Rows"]:
                print(",".join(c.get("VarCharValue", "") for c in linha["Data"]))
    return q["Status"]["State"] == "SUCCEEDED"


def main(argv):
    if len(argv) >= 2 and argv[0] == "job":
        argumentos = {}
        resto = argv[2:]
        while resto:
            opcao, valor, *resto = resto
            if opcao == "--ano_mes":
                argumentos["--ano_mes"] = valor
            elif opcao == "--arg":
                chave, _, v = valor.partition("=")
                argumentos[f"--{chave}"] = v
            else:
                raise SystemExit(__doc__)
        return rodar_job(argv[1], argumentos)
    if len(argv) == 2 and argv[0] == "athena":
        return athena(argv[1])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
