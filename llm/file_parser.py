# file_parser.py

from typing import List
from urllib.parse import urlparse
import io

from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI


# ============================================================
# Azure OpenAI client (same as llm.py)
# ============================================================

OPEN_AI_KEY = os.getenv("OPEN_AI_API_KEY")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL")
OPEN_AI_ENDPOINT = os.getenv("OPEN_AI_ENDPOINT")

client = AzureOpenAI(
    api_key=OPEN_AI_KEY,
    azure_endpoint=OPEN_AI_ENDPOINT,
    api_version="2025-03-01-preview"
)


# ============================================================
# Read ADLS HTTPS blob
# ============================================================

def read_blob_https(uri: str) -> tuple[bytes, str]:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    parsed = urlparse(uri)
    container, blob_path = parsed.path.lstrip("/").split("/", 1)
    filename = blob_path.split("/")[-1]

    service = BlobServiceClient.from_connection_string(conn_str)
    blob = service.get_blob_client(container, blob_path)

    data = blob.download_blob().readall()
    return data, filename


# ============================================================
# Upload file to Azure OpenAI
# ============================================================

def upload_file_to_openai(file_bytes: bytes, filename: str) -> str:
    """
    Azure OpenAI requires files to be uploaded first.
    Returns file_id.
    """
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = filename  # required

    uploaded = client.files.create(
        file=file_obj,
        purpose="assistants"
    )

    return uploaded.id


# ============================================================
# Parse document using GPT-4.1
# ============================================================

def parse_document_with_gpt(file_id: str, filename: str) -> str:
    response = client.responses.create(
        model=OPEN_AI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": file_id
                    },
                    {
                        "type": "input_text",
                        "text": """
Extract all meaningful information from this document.

Rules:
- Ignore headers, footers, and page numbers
- Flatten tables into readable text
- Preserve all numbers, assumptions, and constraints
- Do not hallucinate missing data

Return clean, consolidated text suitable for downstream LLM reasoning.
"""
                    }
                ]
            }
        ],
        max_output_tokens=4096
    )

    return response.output_text.strip()

def parse_files_to_single_text(file_uris: List[str]) -> str:
    outputs = []

    for uri in file_uris:
        try:
            # 1️⃣ Read from ADLS
            file_bytes, filename = read_blob_https(uri)

            # 2️⃣ Upload to Azure OpenAI
            file_id = upload_file_to_openai(file_bytes, filename)

            # 3️⃣ Parse with GPT-4.1
            parsed_text = parse_document_with_gpt(file_id, filename)

            outputs.append(
                f"=== FILE: {filename} ===\n{parsed_text}"
            )

        except Exception as e:
            outputs.append(
                f"=== FILE: {uri} ===\nERROR: {str(e)}"
            )

    return "\n\n".join(outputs)
