"""Custom Transform Manutencao (OPTIMIZE + VACUUM) pelo executor local, contra o MinIO: make test-spark"""
import uuid

import pytest

pytest.importorskip("awsglue")

from jobs import local  # noqa: E402


def test_compacta_as_tabelas_delta_do_bucket_e_ignora_o_que_nao_e_delta(spark):
    import boto3

    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    s3 = boto3.resource("s3", endpoint_url="http://minio:9000")
    bucket = f"teste-{uuid.uuid4().hex[:8]}"
    s3.create_bucket(Bucket=bucket)
    try:
        caminho = f"s3://{bucket}/sample/estabelecimentos"
        for mes in ("2026-09", "2026-10"):
            for lote in range(3):  # 3 gravações por mês = 3 arquivos pequenos por partição
                linhas = [(f"{lote:08d}", mes)]
                spark.createDataFrame(linhas, "cnpj_basico string, ano_mes string").write.format("delta") \
                    .mode("append").partitionBy("ano_mes").save(caminho)
        s3.Object(bucket, "sample/ibge_municipios/parte.parquet").put(Body=b"nao e delta")

        local.manutencao(spark, None, None, None, buckets=bucket)

        detalhe = spark.sql(f"DESCRIBE DETAIL delta.`{caminho}`").first()
        assert detalhe["numFiles"] == 2  # um arquivo por partição
        assert spark.read.format("delta").load(caminho).count() == 6
    finally:
        s3.Bucket(bucket).objects.delete()
        s3.Bucket(bucket).delete()
