"""Carrega um mês da Gold da AWS no Postgres do dashboard, com o papel `analista` (só lê a Gold; PRD, 7.4).

    uv run --env-file .env python -m scripts.carga_aws --ano_mes 2026-10 [--ambiente full]

O papel é assumido na hora, com credenciais temporárias: nada muda no ~/.aws/config. A sessão vem do perfil
`default` de propósito, porque o .env põe no ambiente as credenciais do MinIO.
"""
import argparse
import os

import boto3

from dashboard.carga import carregar_mes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ano_mes", required=True)
    parser.add_argument("--ambiente", default="sample", choices=["sample", "full"])
    parser.add_argument("--perfil", default="default", help="perfil da AWS que pode assumir o papel analista")
    args = parser.parse_args()

    sessao = boto3.Session(profile_name=args.perfil, region_name="us-east-1")
    conta = sessao.client("sts").get_caller_identity()["Account"]
    credenciais = sessao.client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{conta}:role/analista", RoleSessionName="dashboard-load"
    )["Credentials"]
    storage_options = {
        "AWS_ACCESS_KEY_ID": credenciais["AccessKeyId"],
        "AWS_SECRET_ACCESS_KEY": credenciais["SecretAccessKey"],
        "AWS_SESSION_TOKEN": credenciais["SessionToken"],
        "AWS_REGION": "us-east-1",
    }
    prefixo = "sample/" if args.ambiente == "sample" else ""
    conninfo = (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} port=5432 dbname=dashboard "
        f"user={os.environ['POSTGRES_USER']} password={os.environ['POSTGRES_PASSWORD']}"
    )
    carregar_mes(f"s3://goodlion-gold-{conta}/{prefixo}".rstrip("/"), args.ano_mes, conninfo, storage_options)
    print(f"carregado: {args.ano_mes} ({args.ambiente}) da Gold da AWS")


if __name__ == "__main__":
    main()
