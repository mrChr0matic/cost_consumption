from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import json
from databricks.sdk.runtime import *
import os


try:
    dbutils
except NameError:
    from pyspark.sql import SparkSession
    from pyspark.dbutils import DBUtils

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)

SA_INFO = json.loads(
        dbutils.secrets.get(
            scope="llm-secrets",
            key="GOOGLE_DRIVE_SA_JSON"
        )
    )

def get_or_create_folder(service, folder_name, parent_id):
    query = (
        f"name='{folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed=false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get("files", [])

    if files:
        return files[0]["id"]

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()

    return folder["id"]


# -----------------------------
# Ensure ADLS-style path
# root/client_name/use_case_name
# -----------------------------
def ensure_drive_path(service, root_folder_id, client_name, use_case_name):
    client_folder_id = get_or_create_folder(
        service,
        client_name,
        root_folder_id
    )

    use_case_folder_id = get_or_create_folder(
        service,
        use_case_name,
        client_folder_id
    )

    return use_case_folder_id


# -----------------------------
# Upload file to Drive (Shared Drive safe)
# -----------------------------
def upload_file_to_drive(service, file_path, file_name, parent_folder_id):
    file_name = os.path.basename(file_name)  
    media = MediaFileUpload(
        file_path,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True
    )

    file_metadata = {
        "name": file_name,
        "parents": [parent_folder_id]
    }

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True
    ).execute()

    return {
        "file_id": uploaded["id"],
        "view_link": uploaded["webViewLink"],
        "download_link": uploaded.get("webContentLink")
    }


# -----------------------------
# Validate Shared Drive access (recommended)
# -----------------------------
# In validate_shared_drive_access
def validate_shared_drive_access(service, folder_id):
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields="id, name, driveId",
            supportsAllDrives=True
        ).execute()

        print("Shared Drive access confirmed:", folder["name"])

    except HttpError as e:
        # Check if the error is the 404 "File not found"
        if e.resp.status == 404:
            raise RuntimeError(
                f"Google Drive Root Folder ID '{folder_id}' not found. "
                f"Please check your DRIVE_FOLDER_ID environment variable and ensure the "
                f"Service Account has access to that folder."
            ) from e
        else:
            raise


# -----------------------------
# Main upload function
# -----------------------------
def upload_to_drive(
    file_path,
    file_name,
    root_folder_id,
    client_name,
    use_case_name
):
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    sa_info = SA_INFO

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=SCOPES
    )

    service = build("drive", "v3", credentials=creds)

    validate_shared_drive_access(service, root_folder_id)

    final_folder_id = ensure_drive_path(
        service,
        root_folder_id,
        client_name,
        use_case_name
    )

    # Upload file
    return upload_file_to_drive(
        service,
        file_path,
        file_name,
        final_folder_id
    )