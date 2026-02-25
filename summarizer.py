import base64
import mimetypes
from openai import AzureOpenAI
import os
import io
from dotenv import load_dotenv

load_dotenv()

OPEN_AI_KEY = os.getenv("OPEN_AI_API_KEY")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL")
OPEN_AI_ENDPOINT = os.getenv("OPEN_AI_ENDPOINT")



def summarize_image_file(file) -> str:
    
    client = AzureOpenAI(
        api_key=OPEN_AI_KEY,
        azure_endpoint=OPEN_AI_ENDPOINT,
        api_version="2025-03-01-preview"
    )
    
    image_bytes = file.read()
    file.seek(0)

    if not image_bytes:
        raise ValueError("Uploaded image is empty")

    mime_type, _ = mimetypes.guess_type(file.name)
    mime_type = mime_type or "image/png"

    b64 = base64.b64encode(image_bytes).decode()

    response = client.responses.create(
        model=OPEN_AI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Provide a clear, professional, and well-structured paragraph describing the architecture shown in the image. "
                            "The description should explain the overall system design, identify the major cloud services involved, and "
                            "clearly describe the data flow across ingestion, processing, storage, and consumption layers. "
                            "Where applicable, include references to compute, storage, and networking components, and explicitly state "
                            "any reasonable architectural assumptions. The response must be written in formal technical language suitable "
                            "for an enterprise architecture document and must not include bullet points, special symbols, emojis, or any "
                            "random or decorative characters."
                            "give answer in paragraphs where each parqagraph separates concerns."
                        )

                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{b64}"
                    }
                ]
            }
        ],
        max_output_tokens=1024
    )

    if not response.output_text:
        raise RuntimeError("No summary returned by Azure OpenAI")

    return response.output_text.strip()


def summarize_document_file(file) -> str:
    """
    Summarize a PDF or DOCX file using Azure OpenAI.
    """

    client = AzureOpenAI(
        api_key=OPEN_AI_KEY,
        azure_endpoint=OPEN_AI_ENDPOINT,
        api_version="2025-03-01-preview"
    )

    file_bytes = file.read()
    file.seek(0)

    if not file_bytes:
        raise ValueError("Uploaded file is empty")

    # Azure OpenAI requires a file-like object with a name
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = file.name  # REQUIRED

    # 1️⃣ Upload file to Azure OpenAI
    uploaded = client.files.create(
        file=file_obj,
        purpose="assistants"
    )

    file_id = uploaded.id

    # 2️⃣ Ask GPT to summarize the file
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
                        "text": (
                            "Provide a clear, professional, and well-structured summary of the document. "
                            "The summary should describe the overall purpose of the document, key technical "
                            "details, assumptions, constraints, and any quantitative information present. "
                            "Write in formal technical language suitable for an enterprise architecture or "
                            "cost estimation document. Do not use bullet points, special symbols, or "
                            "decorative characters. Organize the response into coherent paragraphs, "
                            "with each paragraph addressing a distinct concern."
                        )
                    }
                ]
            }
        ],
        max_output_tokens=2048
    )

    if not response.output_text:
        raise RuntimeError("No summary returned by Azure OpenAI")

    return response.output_text.strip()


def summarize_user_prompt(user_prompt: str) -> str:
    """
    Summarize structured user input text into section-wise
    professional paragraphs with headings.
    """

    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt is empty")

    client = AzureOpenAI(
        api_key=OPEN_AI_KEY,
        azure_endpoint=OPEN_AI_ENDPOINT,
        api_version="2025-03-01-preview"
    )

    response = client.responses.create(
        model=OPEN_AI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are given structured input describing multiple cloud and analytics use cases. "
                            "Summarize the information into clearly separated sections using the following rules:\n\n"
                            "1. Create a heading for each section exactly as provided in the input "
                            "(for example: DATA MIGRATION, DATA SCIENCE & MACHINE LEARNING, REPORTING, LLM).\n"
                            "2. Include a section if it contains any explicitly defined configuration choices such as "
                            "cloud provider, workload type, model name, or architectural intent, even if numeric values are zero.\n"
                            "3. Completely omit sections whose configuration is an empty object or entirely undefined.\n"
                            "4. Place the descriptive content for each included section on the line immediately following its heading, "
                            "written as a single, well-structured professional paragraph.\n"
                            "5. Each paragraph should explain the scope, configuration, and key assumptions of that section.\n"
                            "6. Use formal technical language suitable for an enterprise architecture or cost estimation document.\n"
                            "7. Do not use bullet points, numbering, special symbols, emojis, or decorative characters.\n"
                            "8. Leave exactly one blank line between sections.\n\n"
                            "Here is the input text:\n\n"
                            f"{user_prompt}"
                        )
                    }
                ]
            }
        ],
        max_output_tokens=1024
    )

    if not response.output_text:
        raise RuntimeError("No summary returned by Azure OpenAI")

    return response.output_text.strip()