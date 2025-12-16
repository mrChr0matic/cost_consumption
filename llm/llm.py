from openai import AzureOpenAI
from excel.excel_writer_combined import generate_cost_excel_combined
from llm.gdrive import upload_to_drive
from llm.adls import upload_to_blob_with_sas
import os
import base64
import json
import re
import requests
from databricks.sdk.runtime import *
from datetime import datetime
import tempfile
from urllib.parse import urlparse

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


try:
    dbutils
except NameError:
    from pyspark.sql import SparkSession
    from pyspark.dbutils import DBUtils

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)



OPEN_AI_KEY = dbutils.secrets.get("llm-secrets", "OPEN_AI_API_KEY")
OPEN_AI_MODEL = dbutils.secrets.get("llm-secrets", "OPEN_AI_MODEL")
OPEN_AI_ENDPOINT = dbutils.secrets.get("llm-secrets", "OPEN_AI_ENDPOINT")

api_version = "2025-03-01-preview"  


client = AzureOpenAI(
    api_key=OPEN_AI_KEY,
    azure_endpoint=OPEN_AI_ENDPOINT,
    api_version=api_version
)

def load_prompt(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

def _read_image_bytes(image_uri: str) -> bytes:
    if image_uri.startswith("http://") or image_uri.startswith("https://"):
        resp = requests.get(image_uri, timeout=30)
        resp.raise_for_status()
        return resp.content

def analyze_image(image_uri):
    image_bytes = _read_image_bytes(image_uri)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model=OPEN_AI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Describe this image."},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}
                ]
            }
        ],
        max_output_tokens=2048
    )

    return response.output_text

def architecture_text(architecture_raw_text):
    
    prompt_template = load_prompt("llm/prompts/architecture_text.txt")
    prompt = prompt_template.replace("{{architecture_raw_text}}", architecture_raw_text)

    response = client.chat.completions.create(
        model=OPEN_AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=2000,
    )

    return response.choices[0].message.content


def generate_cost_json_azure(final_prompt, solution):
    
    final_input = final_prompt.replace("{{solution}}", solution)

    try:
        response = client.chat.completions.create(
            model=OPEN_AI_MODEL,
            messages=[
                {"role": "user", "content": final_input}
            ],
            max_completion_tokens=6000,
        )

        output = response.choices[0].message.content
        return output
    
    except Exception as e:
        return f"LLM Error: {str(e)}"
    
def safe_json_parse(text):
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)


    
def run_llm_pipeline(image_uri, client_name, use_case_name, markets, user_prompt, budget):
    print("Step 1: Analyzing architecture image...")
    arch_diag = analyze_image(image_uri)
    
    print("Step 2: Cleaning architecture text...")
    solution = architecture_text(arch_diag)
    
    prompt_template = load_prompt("llm/prompts/cost_estimation.txt")
    final_prompt = (
        prompt_template
            .replace("{{solution}}", solution)
            .replace("{{user_prompt}}", user_prompt or "No additional user constraints provided.")
            .replace("{{budget}}", str(budget) if budget is not None else "No explicit budget provided.")
    )

    
    print("Step 3: Generating cost JSON...")
    final_out = generate_cost_json_azure(final_prompt, solution)

    print("Step 4: Parsing JSON output...")
    cost_json = safe_json_parse(final_out)

    print("Step 5: Creating Excel file...")
    consumption_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    output_excel = (
        f"{client_name}/{use_case_name}/"
        f"{client_name}_consumption_{consumption_timestamp}.xlsx"
    )
    local_image_path = ensure_local_image(image_uri)



    generate_cost_excel_combined(cost_json, output_excel, client_name, use_case_name, local_image_path, markets)
    print(f"Excel generated: {output_excel}")

    print("Step 6: Uploading file to Azure Blob Storage with SAS...")
    sas_url = upload_to_blob_with_sas(output_excel, client_name, use_case_name, output_excel)

    if not sas_url:
        raise RuntimeError("Azure upload failed – SAS URL not generated")

    print("Azure SAS URL:")
    print(sas_url)

    print("Step 8: Uploading file to Google Drive...")
    drive_result = upload_to_drive(
        file_path=output_excel,
        file_name=output_excel,
        root_folder_id=dbutils.secrets.get("llm-secrets", "DRIVE_FOLDER_ID"),
        client_name=client_name,
        use_case_name=use_case_name
    )

    print("Google Drive upload successful")
    print("Drive file link:", drive_result["view_link"])

    print("Pipeline completed successfully")

    return {
        "azure_sas_url": sas_url,
        "drive_link": drive_result["view_link"]
    }