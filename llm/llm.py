from openai import AzureOpenAI
from excel.excel_writer_combined import generate_cost_excel_combined
from llm.gdrive import upload_to_drive
from llm.file_parser import parse_files_to_single_text

import os
import base64
import json
import re
import requests
import tempfile
from datetime import datetime
from urllib.parse import urlparse
from typing import List

from databricks.sdk.runtime import dbutils


# ============================================================
# Azure OpenAI client
# ============================================================

OPEN_AI_KEY = dbutils.secrets.get("llm-secrets", "OPEN_AI_API_KEY")
OPEN_AI_MODEL = dbutils.secrets.get("llm-secrets", "OPEN_AI_MODEL")
OPEN_AI_ENDPOINT = dbutils.secrets.get("llm-secrets", "OPEN_AI_ENDPOINT")

client = AzureOpenAI(
    api_key=OPEN_AI_KEY,
    azure_endpoint=OPEN_AI_ENDPOINT,
    api_version="2025-03-01-preview"
)


# ============================================================
# Helpers
# ============================================================

def ensure_local_image(image_uri: str) -> str:
    """
    Ensures the image exists as a local file.
    Returns a local filesystem path suitable for openpyxl.
    """

    # Already a local file
    if os.path.exists(image_uri):
        return image_uri

    # HTTPS URL → download to temp
    if image_uri.startswith("http://") or image_uri.startswith("https://"):
        resp = requests.get(image_uri, timeout=30)
        resp.raise_for_status()

        # Infer extension (default png)
        parsed = urlparse(image_uri)
        ext = os.path.splitext(parsed.path)[1] or ".png"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(resp.content)
        tmp.close()

        return tmp.name

    raise ValueError(f"Unsupported image_uri: {image_uri}")

def load_prompt(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def _read_image_bytes(image_uri: str) -> bytes:
    resp = requests.get(image_uri, timeout=30)
    resp.raise_for_status()
    return resp.content


def analyze_image(image_uri: str) -> str:
    """
    Vision analysis for a single image.
    """
    image_bytes = _read_image_bytes(image_uri)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model=OPEN_AI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Describe this architecture image in detail."},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}
                ]
            }
        ],
        max_output_tokens=2048
    )

    return response.output_text.strip()


def architecture_text(raw_text: str) -> str:
    prompt_template = load_prompt("llm/prompts/architecture_text.txt")
    prompt = prompt_template.replace("{{architecture_raw_text}}", raw_text)

    response = client.chat.completions.create(
        model=OPEN_AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=2000,
    )

    return response.choices[0].message.content.strip()


def safe_json_parse(text: str) -> dict:
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_llm_pipeline(
    image_uris: List[str],
    file_uris: List[str],
    client_name: str,
    use_case_name: str,
    markets: list,
    global_consumption_multiplier: float,
    user_prompt: str,
    budget: int
):
    # --------------------------------------------------------
    # 1️⃣ Parse all images
    # --------------------------------------------------------
    print("Step 1: Parsing architecture images...")

    image_summaries = []

    for idx, uri in enumerate(image_uris, start=1):
        print(f"  → Analyzing image {idx}")
        vision_text = analyze_image(uri)
        cleaned_text = architecture_text(vision_text)
        image_summaries.append(cleaned_text)

    combined_image_context = "\n\n".join(image_summaries)


    # --------------------------------------------------------
    # 2️⃣ Parse all files
    # --------------------------------------------------------
    print("Step 2: Parsing input documents...")

    files_context = ""
    if file_uris:
        files_context = parse_files_to_single_text(file_uris)


    # --------------------------------------------------------
    # 3️⃣ Build final reasoning context
    # --------------------------------------------------------
    print("Step 3: Building final reasoning context...")

    full_context = f"""
ARCHITECTURE DETAILS:
{combined_image_context or "No architecture images provided."}

DOCUMENT CONSTRAINTS / INPUT FILES:
{files_context or "No additional documents provided."}

USER CONSTRAINTS:
{user_prompt or "No additional user constraints provided."}

BUDGET:
{budget if budget is not None else "No explicit budget provided."}
""".strip()


    # --------------------------------------------------------
    # 4️⃣ Cost estimation
    # --------------------------------------------------------
    print("Step 4: Generating cost JSON...")

    cost_prompt_template = load_prompt("llm/prompts/cost_estimation.txt")
    final_prompt = cost_prompt_template.replace("{{solution}}", full_context)

    response = client.chat.completions.create(
        model=OPEN_AI_MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        max_completion_tokens=6000,
    )

    cost_json_raw = response.choices[0].message.content
    cost_json = safe_json_parse(cost_json_raw)


    # --------------------------------------------------------
    # 5️⃣ Generate Excel
    # --------------------------------------------------------
    print("Step 5: Creating Excel output...")

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_excel = (
        f"{client_name}/{use_case_name}/"
        f"{client_name}_consumption_{ts}.xlsx"
    )

    # Use first image for diagram embedding (if present)
    # image_for_excel = image_uris[0] if image_uris else None

    image_for_excel = None
    if image_uris:
        image_for_excel = ensure_local_image(image_uris[0])


    generate_cost_excel_combined(
        cost_json,
        output_excel,
        client_name,
        use_case_name,
        image_for_excel,
        markets,
        global_consumption_multiplier
    )


    # --------------------------------------------------------
    # 6️⃣ Upload to Drive
    # --------------------------------------------------------
    print("Step 6: Uploading to Google Drive...")

    drive_result = upload_to_drive(
        file_path=output_excel,
        file_name=output_excel,
        root_folder_id=dbutils.secrets.get("llm-secrets", "DRIVE_FOLDER_ID"),
        client_name=client_name,
        use_case_name=use_case_name
    )

    print("Pipeline completed successfully")

    return {
        "drive_link": drive_result["view_link"]
    }
