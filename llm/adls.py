from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.storage.filedatalake import DataLakeServiceClient
from datetime import datetime, timedelta
import os


def generate_sas_url(blob_path, expiry_hours=1):
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("ACCOUNT_KEY")
    container = os.getenv("AZURE_BLOB_CONTAINER")
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
    )
    return f"https://{account_name}.blob.core.windows.net/{container}/{blob_path}?{sas_token}"


def _get_fs_client():
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("ACCOUNT_KEY")
    file_system = os.getenv("AZURE_BLOB_CONTAINER")
    if not all([account_name, account_key, file_system]):
        raise RuntimeError("Missing ADLS config env vars")
    service_client = DataLakeServiceClient(
        account_url=f"https://{account_name}.dfs.core.windows.net",
        credential=account_key
    )
    return service_client.get_file_system_client(file_system)


def upload_to_adls(file_bytes: bytes, adls_path: str) -> str:
    fs_client = _get_fs_client()
    file_client = fs_client.get_file_client(adls_path)
    file_client.upload_data(file_bytes, overwrite=True)
    return generate_sas_url(adls_path)