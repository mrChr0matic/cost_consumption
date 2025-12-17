# import sys
# import json
# import logging
# from llm.llm import run_llm_pipeline
# import os
# from pathlib import Path
# import tempfile
# from datetime import datetime, timedelta, timezone
# from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

# CONN_STR = dbutils.secrets.get(
#         scope="llm-secrets",
#         key="AZURE_STORAGE_CONNECTION_STRING"
#     )

# def upload_result_json_to_blob(
#     result: dict,
#     client_name: str,
#     use_case_name: str,
#     connection_string: str
# ) -> str:
#     """
#     Uploads result.json to Azure Blob Storage and returns a SAS URL.
#     """

#     # -------------------------
#     # Parse connection string
#     # -------------------------
#     conn_parts = dict(
#         item.split("=", 1)
#         for item in connection_string.split(";")
#         if "=" in item
#     )

#     account_name = conn_parts.get("AccountName")
#     account_key = conn_parts.get("AccountKey")

#     if not account_name or not account_key:
#         raise ValueError("Invalid Azure storage connection string")

#     blob_service = BlobServiceClient.from_connection_string(connection_string)
#     container_name = "finops-output"
#     container = blob_service.get_container_client(container_name)

#     # Create container if missing
#     try:
#         container.create_container()
#     except Exception:
#         pass

#     # -------------------------
#     # Write JSON to temp file
#     # -------------------------
#     with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
#         json.dump(result, tmp, indent=2)
#         tmp_path = tmp.name

#     # -------------------------
#     # Upload to Blob
#     # -------------------------
#     blob_path = f"{client_name}/{use_case_name}/result.json"

#     with open(tmp_path, "rb") as f:
#         container.upload_blob(
#             name=blob_path,
#             data=f,
#             overwrite=True
#         )

#     # -------------------------
#     # Generate SAS URL
#     # -------------------------
#     sas_token = generate_blob_sas(
#         account_name=account_name,
#         account_key=account_key,
#         container_name=container_name,
#         blob_name=blob_path,
#         permission=BlobSasPermissions(read=True),
#         start=datetime.now(timezone.utc) - timedelta(minutes=5),
#         expiry=datetime.now(timezone.utc) + timedelta(hours=1),
#     )

#     return (
#         f"https://{account_name}.blob.core.windows.net/"
#         f"{container_name}/{blob_path}?{sas_token}"
#     )


# # -------------------------
# # Logging configuration
# # -------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s"
# )
# logger = logging.getLogger(__name__)


# def _get_user_json_arg() -> dict:
#     """
#     Databricks injects internal flags (e.g. -f).
#     User parameters are passed as positional JSON strings.
#     """
#     user_args = [
#         arg for arg in sys.argv[1:]
#         if not arg.startswith("-")
#     ]

#     if not user_args:
#         raise ValueError("Missing job parameters JSON")

#     try:
#         return json.loads(user_args[0])
#     except json.JSONDecodeError as e:
#         raise ValueError(
#             f"Invalid JSON parameters: {user_args[0]}"
#         ) from e


# def main():
#     params = _get_user_json_arg()

#     # -------------------------
#     # Validate inputs
#     # -------------------------
#     required_keys = ("image_uri", "client_name", "use_case_name")
#     for key in required_keys:
#         if key not in params:
#             raise ValueError(f"Missing required parameter: {key}")

#     image_uri = params["image_uri"]
#     client_name = params["client_name"]
#     use_case_name = params["use_case_name"]
#     markets = params.get("markets", [])
#     user_prompt = params.get("user_prompt")
#     budget = params.get("budget")

#     logger.info("Starting LLM pipeline")
#     logger.info("Client: %s | Use case: %s", client_name, use_case_name)
#     logger.info("Image URI: %s", image_uri)
#     logger.info("Markets: %s", markets)

#     # -------------------------
#     # Run LLM pipeline
#     # -------------------------
#     result = run_llm_pipeline(
#         image_uri=image_uri,
#         client_name=client_name,
#         use_case_name=use_case_name,
#         markets=markets,
#         user_prompt=user_prompt,
#         budget=budget
#     )

#     # -------------------------
#     # Emit final result
#     # -------------------------
#     print("PIPELINE_RESULT_JSON")
#     print(json.dumps(result, indent=2))
    
    
#     result_sas_url = upload_result_json_to_blob(
#         result=result,
#         client_name=client_name,
#         use_case_name=use_case_name,
#         connection_string=CONN_STR
#     )

#     logger.info("Result JSON uploaded to Blob")
#     logger.info("Result SAS URL: %s", result_sas_url)

# if __name__ == "__main__":
#     main()

import sys
import json
import logging
from llm.llm import run_llm_pipeline
from datetime import datetime, timedelta, timezone
import tempfile

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas
)

from databricks.sdk.runtime import dbutils


# ============================================================
# Azure Storage
# ============================================================

CONN_STR = dbutils.secrets.get(
    scope="llm-secrets",
    key="AZURE_STORAGE_CONNECTION_STRING"
)


def upload_result_json_to_blob(
    result: dict,
    client_name: str,
    use_case_name: str,
    connection_string: str
) -> str:
    """
    Uploads result.json to Azure Blob Storage and returns a SAS URL.
    """
    conn_parts = dict(
        item.split("=", 1)
        for item in connection_string.split(";")
        if "=" in item
    )

    account_name = conn_parts.get("AccountName")
    account_key = conn_parts.get("AccountKey")

    if not account_name or not account_key:
        raise ValueError("Invalid Azure storage connection string")

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_name = "finops-output"
    container = blob_service.get_container_client(container_name)

    try:
        container.create_container()
    except Exception:
        pass

    blob_path = f"{client_name}/{use_case_name}/result.json"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(result, tmp, indent=2)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
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

    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{container_name}/{blob_path}?{sas_token}"
    )


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# Job argument handling
# ============================================================

def _get_user_json_arg() -> dict:
    user_args = [
        arg for arg in sys.argv[1:]
        if not arg.startswith("-")
    ]

    if not user_args:
        raise ValueError("Missing job parameters JSON")

    try:
        return json.loads(user_args[0])
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON parameters: {user_args[0]}"
        ) from e


# ============================================================
# Main
# ============================================================

def main():
    params = _get_user_json_arg()

    # -------------------------
    # Validate inputs
    # -------------------------
    required_keys = ("client_name", "use_case_name")
    for key in required_keys:
        if key not in params:
            raise ValueError(f"Missing required parameter: {key}")

    image_uris = params.get("image_uris", [])
    file_uris = params.get("file_uris", [])

    if not image_uris and not file_uris:
        raise ValueError(
            "At least one of image_uris or file_uris must be provided"
        )

    client_name = params["client_name"]
    use_case_name = params["use_case_name"]
    markets = params.get("markets", [])
    user_prompt = params.get("user_prompt")
    budget = params.get("budget")

    logger.info("Starting LLM pipeline")
    logger.info("Client: %s | Use case: %s", client_name, use_case_name)
    logger.info("Image URIs: %s", image_uris)
    logger.info("File URIs: %s", file_uris)
    logger.info("Markets: %s", markets)

    # -------------------------
    # Run LLM pipeline
    # -------------------------
    result = run_llm_pipeline(
        image_uris=image_uris,
        file_uris=file_uris,
        client_name=client_name,
        use_case_name=use_case_name,
        markets=markets,
        user_prompt=user_prompt,
        budget=budget
    )

    # -------------------------
    # Emit final result
    # -------------------------
    print("PIPELINE_RESULT_JSON")
    print(json.dumps(result, indent=2))

    result_sas_url = upload_result_json_to_blob(
        result=result,
        client_name=client_name,
        use_case_name=use_case_name,
        connection_string=CONN_STR
    )

    logger.info("Result JSON uploaded to Blob")
    logger.info("Result SAS URL: %s", result_sas_url)


if __name__ == "__main__":
    main()

