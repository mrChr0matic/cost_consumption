from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from datetime import datetime, timedelta, timezone
import os
from databricks.sdk.runtime import *


try:
    dbutils
except NameError:
    from pyspark.sql import SparkSession
    from pyspark.dbutils import DBUtils

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)

CONN_STR = dbutils.secrets.get(
        scope="llm-secrets",
        key="AZURE_STORAGE_CONNECTION_STRING"
    )

def upload_to_blob_with_sas(file_path, client_name, use_case_name, file_name):
    connect_str = CONN_STR

    if not connect_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")

    conn_parts = dict(
        item.split("=", 1)
        for item in connect_str.split(";")
        if "=" in item
    )

    account_name = conn_parts.get("AccountName")
    account_key = conn_parts.get("AccountKey")

    if not account_name or not account_key:
        raise ValueError("Connection string missing AccountName or AccountKey")

    blob_service = BlobServiceClient.from_connection_string(connect_str)
    container_name = "finops-output"
    container = blob_service.get_container_client(container_name)

    try:
        container.create_container()
    except:
        pass

    blob_path = f"{client_name}/{use_case_name}/{file_name}"

    with open(file_path, "rb") as f:
        container.upload_blob(
            name=blob_path,
            data=f,
            overwrite=True
        )

    sas_token = generate_blob_sas(
        account_name=account_name,
        account_key=account_key,
        container_name=container_name,
        blob_name=blob_path,
        permission=BlobSasPermissions(read=True),
        start=datetime.now(timezone.utc) - timedelta(minutes=5),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_path}?{sas_token}" 