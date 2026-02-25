import os
import base64
import requests
import streamlit as st
from dotenv import load_dotenv
from summarizer import summarize_user_prompt, summarize_image_file, summarize_document_file

load_dotenv()

from config.arch_component import ARCH_COMPONENT_MAP
from config.use_case import use_case
from config.cloud_options import cloud_options

from config.data_migration.migration_type import migration_type
from config.data_migration.pipeline_mode import pipeline_mode
from config.data_migration.transformation_complexity import transformation_complexity

from config.machine_learning.workload_type import work_load_type
from config.machine_learning.training_frequency import training_frequency
from config.reporting.reporting_tool import reporting_tool
from config.reporting.user_subscription import user_subscription

from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.storage.filedatalake import DataLakeServiceClient
from datetime import datetime, timedelta

# ======================================================
# CONFIG
# ======================================================

API_BASE_URL = "http://localhost:8051"


def get_forwarded_token() -> str:
    return "localhost-trusted"


def is_html_response(response: requests.Response) -> bool:
    """Detect when Databricks Apps redirects to the login page instead of the API."""
    content_type = response.headers.get("Content-Type", "")
    return "text/html" in content_type or response.text.strip().startswith("<!doctype")


# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Consumption Estimate Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    div[data-testid="stAlert"] {
        border-left: 5px solid #D7263D !important;
        border-radius: 10px;
        overflow: hidden;
    }
    div[data-testid="stAlert"] > div {
        background-color: #fff1f1 !important;
        padding: 14px 16px;
    }
    div[data-testid="stAlert"] * {
        color: #D7263D !important;
        font-weight: 500;
    }
    div.stButton > button {
        background-color: #D7263D !important;
        color: #ffffff !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# SESSION STATE INITIALIZATION
# ======================================================
defaults = {
    "data_migration_store": {},
    "ml_store": {},
    "reporting_store": {},
    "llm_store": {},
    "final_prompt": "",
    "raw_prompt": "",
    "gdrive_link": None,
    "summary": "",
    "adls_paths": [],
    "image_urls": [],
    "pdf_urls": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ======================================================
# LOAD CSS
# ======================================================
def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ======================================================
# BRANDING
# ======================================================
def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_image("./assets/sigmoid-logo.jpeg")

# ======================================================
# HERO
# ======================================================
st.markdown(
    """
    <div class="hero-section">
        <h1 class="hero-title">Consumption Estimate Calculator</h1>
        <p class="hero-subtitle-strong">An AI-powered calculator</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{logo_base64}" class="sidebar-logo">
            <p class="sidebar-text">Powered by <span class="db-red">AI</span></p>
        </div>
        <hr class="sidebar-divider">
        """,
        unsafe_allow_html=True
    )

    st.header("User Input")

    client_name = st.text_input("Client Name", placeholder="Acme Corp")
    use_case_name = st.text_input("Use Case Name", placeholder="Annual Budget Planning")

    # =========================
    # BUDGET
    # =========================
    st.subheader("Budget")
    annual_budget = st.number_input(
        "Annual Cloud Budget (USD)", min_value=0, value=0, step=10000
    )

    # =========================
    # MARKET CONFIG
    # =========================
    st.subheader("Global Consumption Multiplier")
    global_consumption_multiplier = st.number_input(
        "Consumption Multiplier", min_value=0.0, value=1.0, step=0.1
    )
    st.session_state["global_consumption_multiplier"] = global_consumption_multiplier

    st.subheader("Market Configuration")
    number_of_markets = st.number_input("Number of Markets", min_value=0, max_value=10, value=0)

    markets = []
    for i in range(int(number_of_markets)):
        markets.append({
            "market": f"M{i+1}",
            "start_month": st.selectbox(
                f"Market Entry Month (M{i+1})",
                list(range(1, 13)),
                key=f"m_month_{i}"
            )
        })

    use_case_type = st.selectbox("Use Case Type", use_case)

    # =========================
    # DATA MIGRATION
    # =========================
    if use_case_type == "Data Migration":
        dm = st.session_state.data_migration_store
        st.subheader("Data Migration Inputs")
        dm["cloud_type"] = st.multiselect("Cloud Type", cloud_options, default=[])
        dm["migration_type"] = st.radio("Migration Type", migration_type)
        dm["pipeline_mode"] = st.radio("Pipeline Mode", pipeline_mode)
        dm["historical_data_gb"] = st.number_input("Historical Data Size (GB)", min_value=0, value=0)
        dm["daily_incremental_gb"] = st.number_input("Daily Incremental Data (GB/day)", min_value=0, value=0)
        dm["pipelines"] = st.number_input("Number of Pipelines", min_value=0, value=0)
        dm["runs_per_day"] = st.number_input("Pipeline Runs per Day", min_value=0, value=0)
        dm["avg_runtime_hours"] = st.number_input("Avg Runtime per Pipeline (hours)", min_value=0.0, value=0.0)
        dm["source_systems"] = st.number_input("Source Systems", min_value=0, value=0)
        dm["destination_systems"] = st.number_input("Destination Systems", min_value=0, value=0)
        dm["transformation_complexity"] = st.selectbox("Transformation Complexity", transformation_complexity)
        dm["concurrent_pipelines"] = st.number_input("Max Concurrent Pipelines", min_value=0, value=0)
        dm["storage_retention_days"] = st.number_input("Raw Data Retention (days)", min_value=0, value=0)

    # =========================
    # MACHINE LEARNING
    # =========================
    if use_case_type == "Data Science & Machine Learning":
        ml = st.session_state.ml_store
        st.subheader("Data Science & Machine Learning Inputs")
        ml["cloud_type"] = st.multiselect("Cloud Type", cloud_options, default=[])
        ml["workload_types"] = st.multiselect("Workload Type", work_load_type, default=[])
        ml["training_data_gb"] = st.number_input("Training Data Size (GB)", min_value=0, value=0)
        ml["training_frequency"] = st.selectbox("Training Frequency", training_frequency)
        ml["avg_training_hours"] = st.number_input("Avg Training Duration (hours)", min_value=0.0, value=0.0)
        ml["models_count"] = st.number_input("Number of Models", min_value=0, value=0)
        ml["inference_requests_per_day"] = st.number_input("Inference Requests per Day", min_value=0, value=0)
        ml["peak_concurrency"] = st.number_input("Peak Concurrent Inference Requests", min_value=0, value=0)
        ml["use_gpu"] = st.radio("Use GPU?", ["No", "Yes"])
        ml["gpu_hours_per_day"] = (
            st.number_input("GPU Usage (hours/day)", min_value=0, value=0)
            if ml["use_gpu"] == "Yes" else 0
        )
        ml["model_retention_days"] = st.number_input("Model Retention (days)", min_value=0, value=0)

    # =========================
    # REPORTING
    # =========================
    if use_case_type == "Reporting":
        rp = st.session_state.reporting_store
        st.subheader("Reporting Inputs")
        rp["cloud_type"] = st.multiselect("Cloud Type", cloud_options, default=[])
        rp["tool"] = st.selectbox("Reporting Tool", reporting_tool)
        rp["user_type"] = st.radio("User Subscription", user_subscription)
        rp["number_of_users"] = st.number_input("Number of Users", min_value=0, value=0)

    # =========================
    # GEN AI
    # =========================
    if use_case_type == "GEN AI":
        llm = st.session_state.llm_store
        st.subheader("LLM Inputs")
        llm["architectural_component"] = st.selectbox(
            "Architectural Component", list(ARCH_COMPONENT_MAP.keys())
        )
        llm["platform"] = st.selectbox(
            "Platform", list(ARCH_COMPONENT_MAP[llm["architectural_component"]].keys())
        )
        llm["llm_type"] = st.selectbox(
            "LLM Type",
            list(ARCH_COMPONENT_MAP[llm["architectural_component"]][llm["platform"]].keys())
        )
        llm["llm_version"] = st.selectbox(
            "LLM Model Version",
            ARCH_COMPONENT_MAP[llm["architectural_component"]][llm["platform"]][llm["llm_type"]]
        )
        llm["requests_per_day"] = st.number_input("Requests per Day", min_value=0, value=0)
        llm["avg_tokens_per_request"] = st.number_input("Avg Tokens per Request", min_value=0, value=0)
        llm["concurrent_users"] = st.number_input("Concurrent Users", min_value=0, value=0)
        llm["data_retention_days"] = st.number_input("Prompt / Response Retention (days)", min_value=0, value=0)


# ======================================================
# ADLS HELPERS
# ======================================================

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


def upload_to_adls(uploaded_file, adls_path):
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("ACCOUNT_KEY")
    file_system = os.getenv("AZURE_BLOB_CONTAINER")

    if not all([account_name, account_key, file_system]):
        raise RuntimeError(
            f"Missing ADLS config. "
            f"AZURE_STORAGE_ACCOUNT={account_name}, "
            f"ACCOUNT_KEY={'SET' if account_key else None}, "
            f"AZURE_BLOB_CONTAINER={file_system}"
        )

    service_client = DataLakeServiceClient(
        account_url=f"https://{account_name}.dfs.core.windows.net",
        credential=account_key
    )
    fs_client = service_client.get_file_system_client(file_system)
    file_client = fs_client.get_file_client(adls_path)
    uploaded_file.seek(0)
    file_client.upload_data(uploaded_file.read(), overwrite=True)
    return generate_sas_url(adls_path)


def delete_from_adls(adls_path):
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("ACCOUNT_KEY")
    file_system = os.getenv("AZURE_BLOB_CONTAINER")
    service_client = DataLakeServiceClient(
        account_url=f"https://{account_name}.dfs.core.windows.net",
        credential=account_key
    )
    fs_client = service_client.get_file_system_client(file_system)
    fs_client.get_file_client(adls_path).delete_file()


# ======================================================
# UPLOAD ARTIFACTS
# ======================================================
st.header("Upload Artifacts")
st.info("Upload PNG, JPG, JPEG, or PDF files. Files are optional — you can also generate estimates from the prompt alone.")

uploaded_files = st.file_uploader(
    "Select files",
    accept_multiple_files=True,
    type=["png", "jpg", "jpeg", "pdf"]
)

if st.button("Upload Files"):
    if not uploaded_files:
        st.warning("Please select files first.")
    else:
        with st.spinner("Uploading..."):
            for file in uploaded_files:
                ext = file.name.lower()
                if ext.endswith((".pdf", ".docx", ".doc")):
                    adls_path = f"uploads/pdfs/{file.name}"
                    file_url = upload_to_adls(file, adls_path)
                    st.session_state.pdf_urls.append(file_url)
                    st.session_state.adls_paths.append(adls_path)
                    st.success(f"PDF uploaded: {file.name}")
                elif ext.endswith((".png", ".jpg", ".jpeg")):
                    adls_path = f"uploads/images/{file.name}"
                    img_url = upload_to_adls(file, adls_path)
                    st.session_state.image_urls.append(img_url)
                    st.session_state.adls_paths.append(adls_path)
                    st.success(f"Image uploaded: {file.name}")

# ======================================================
# ANALYZE FILES
# ======================================================
summary = ""

if st.button("Analyze Files"):
    if not uploaded_files:
        st.warning("Please select files first.")
    else:
        with st.spinner("Analyzing..."):
            for file in uploaded_files:
                if file.name.lower().endswith((".pdf", ".docx")):
                    summary += summarize_document_file(file)
                else:
                    summary += summarize_image_file(file)
        st.session_state.summary = summary

# ======================================================
# AI ANALYSIS
# ======================================================
st.header("AI Analysis & Cost Estimation")

if st.button("Generate LLM Summary & Update Prompt", type="secondary"):
    with st.spinner("Generating professional summary using AI..."):
        try:
            st.session_state.raw_prompt = f"""
DATA MIGRATION:
{st.session_state.data_migration_store}

DATA SCIENCE & MACHINE LEARNING:
{st.session_state.ml_store}

REPORTING:
{st.session_state.reporting_store}

GEN AI:
{st.session_state.llm_store}
""".strip()

            llm_summary = summarize_user_prompt(st.session_state.raw_prompt)
            st.session_state.final_prompt = llm_summary + "\n \n Summary: \n" + st.session_state.summary

        except Exception as e:
            st.error(f"Summary generation failed: {str(e)}")

prompt_input = st.text_area(
    "User Prompt",
    value=st.session_state.final_prompt or "Extract cloud resources and estimate consumption. Output JSON only.",
    height=260
)

st.markdown("---")
col1, col2 = st.columns([3, 1])

with col1:
    if st.button("Generate Cost Estimate with AI", type="primary"):
        if not client_name or not use_case_name:
            st.error("Please enter Client Name and Use Case Name before generating.")
            st.stop()

        with st.spinner("Analyzing and estimating... this may take a few minutes."):
            clean_prompt = prompt_input.split("Summary:")[0].strip()

            try:
                token = get_forwarded_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-Access-Token": token,
                }

                response = requests.post(
                    f"{API_BASE_URL}/estimate",
                    headers=headers,
                    json={
                        "image_uris": st.session_state.image_urls,
                        "file_uris": st.session_state.pdf_urls,
                        "client_name": client_name,
                        "use_case_name": use_case_name,
                        "markets": markets,
                        "global_consumption_multiplier": st.session_state["global_consumption_multiplier"],
                        "user_prompt": clean_prompt,
                        "budget": annual_budget if annual_budget > 0 else None,
                    },
                    timeout=600,
                )

                # Detect Databricks auth redirect (returns 200 + HTML login page)
                if is_html_response(response):
                    st.error(
                        "Authentication failed: the API returned a login page instead of a response. "
                        "Your token may be expired or invalid. Please refresh the page and try again."
                    )
                    st.stop()

                if response.status_code != 200:
                    st.error(f"API error {response.status_code}: {response.text}")
                    st.stop()

                try:
                    result = response.json()
                except Exception as e:
                    st.error(f"JSON parsing failed: {str(e)}\n\nRaw response:\n{response.text[:500]}")
                    st.stop()

                st.session_state.gdrive_link = result["drive_link"]

            except requests.exceptions.Timeout:
                st.error("Request timed out. The pipeline is taking longer than expected.")
                st.stop()

            except Exception as e:
                st.error(f"Cost estimation failed: {str(e)}")
                st.stop()

            finally:
                for path in st.session_state.get("adls_paths", []):
                    try:
                        delete_from_adls(path)
                    except Exception as cleanup_err:
                        print(f"Cleanup failed for {path}: {cleanup_err}")
                st.session_state.adls_paths.clear()


if st.session_state.gdrive_link:
    st.markdown("---")
    st.link_button(
        "Open Result in Google Drive",
        st.session_state.gdrive_link,
        use_container_width=True
    )
