"""Dispara um job do DataBrew e espera terminar: é como o DataBrew entra no Glue Workflow (PRD, 5.10).

Compatível com Python 3.9 (job Python shell do Glue): só biblioteca padrão + boto3.
"""
import time

ESTADOS_FINAIS = {"SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT"}


def executar(databrew, nome, intervalo=15):
    """Inicia o job `nome` e consulta até um estado final. Qualquer coisa diferente de SUCCEEDED levanta erro,
    para o job do Glue falhar (e o Workflow parar e o alerta chegar)."""
    execucao = databrew.start_job_run(Name=nome)["RunId"]
    while True:
        resposta = databrew.describe_job_run(Name=nome, RunId=execucao)
        estado = resposta["State"]
        if estado in ESTADOS_FINAIS:
            break
        time.sleep(intervalo)
    if estado != "SUCCEEDED":
        raise RuntimeError(f"job {nome} do DataBrew terminou em {estado}: {resposta.get('ErrorMessage', '')}")
    return estado


def main(argv=None):
    import argparse

    import boto3

    parser = argparse.ArgumentParser(description="Dispara um job do DataBrew e espera terminar.")
    parser.add_argument("--job_databrew", required=True)
    args, _ = parser.parse_known_args(argv)  # o Glue acrescenta os próprios argumentos

    inicio = time.time()
    executar(boto3.client("databrew"), args.job_databrew)
    # Linha lida pelo dashboard do CloudWatch (duração por execução).
    print(f"resumo job=trigger_databrew segundos={int(time.time() - inicio)} linhas=0 meses=-")


if __name__ == "__main__":
    main()
