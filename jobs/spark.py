"""SparkSession com Delta para rodar os jobs no container do Glue (local) ou contra o MinIO."""
import os

from pyspark.sql import SparkSession


def criar_spark(master=None):
    construtor = (
        SparkSession.builder.appName("good-lion")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # O container vem configurado para o Hive/Glue Catalog, que não existe localmente.
        .config("spark.sql.catalogImplementation", "in-memory")
    )
    if master:
        construtor = construtor.master(master)
    # S3_ENDPOINT aponta para o MinIO; na AWS fica vazio e vale a configuração do Glue.
    if os.environ.get("S3_ENDPOINT"):
        construtor = (
            construtor.config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT"])
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config(
                "spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            )
            .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"])
            .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"])
        )
    return construtor.getOrCreate()
