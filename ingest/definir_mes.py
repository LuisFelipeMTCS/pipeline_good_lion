"""Primeiro passo do Glue Workflow (PRD, 7.1): fixa o mês da execução nas propriedades do Workflow.

Sob demanda o mês vem de fora (`aws glue start-workflow-run --run-properties ano_mes=2026-09`); no gatilho
mensal ninguém informa, e vale o mês corrente. Os jobs seguintes leem o `ano_mes` dessas propriedades.
Compatível com Python 3.9 (job Python shell do Glue): só biblioteca padrão + boto3.
"""
import datetime
import re


def definir(glue, workflow, execucao, hoje=None):
    propriedades = glue.get_workflow_run_properties(Name=workflow, RunId=execucao)["RunProperties"]
    ano_mes = propriedades.get("ano_mes") or (hoje or datetime.date.today()).strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", ano_mes):
        raise ValueError(f"ano_mes inválido nas propriedades do Workflow: {ano_mes!r}")
    glue.put_workflow_run_properties(Name=workflow, RunId=execucao, RunProperties={"ano_mes": ano_mes})
    return ano_mes


def main(argv=None):
    import argparse

    import boto3

    parser = argparse.ArgumentParser(description="Fixa o ano_mes da execução do Workflow.")
    parser.add_argument("--WORKFLOW_NAME", required=True)
    parser.add_argument("--WORKFLOW_RUN_ID", required=True)
    args, _ = parser.parse_known_args(argv)
    ano_mes = definir(boto3.client("glue"), args.WORKFLOW_NAME, args.WORKFLOW_RUN_ID)
    print(f"resumo job=definir_mes segundos=0 linhas=0 meses={ano_mes}")


if __name__ == "__main__":
    main()
