import os
import base64
import requests
import time
import streamlit as st
from dotenv import load_dotenv

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


API_BASE_URL = "http://localhost:8051"


def get_forwarded_token() -> str:
    return "localhost-trusted"


def is_html_response(response: requests.Response) -> bool:
    content_type = response.headers.get("Content-Type", "")
    return "text/html" in content_type or response.text.strip().startswith("<!doctype")



def upload_file_to_backend(file) -> dict:
    """Upload a file to the backend /upload endpoint. Returns {url, adls_path, file_type}."""
    token = get_forwarded_token()
    file.seek(0)
    resp = requests.post(
        f"{API_BASE_URL}/upload",
        headers={"Authorization": f"Bearer {token}", "X-Forwarded-Access-Token": token},
        files={"file": (file.name, file.read(), _mime(file.name))},
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Upload failed ({resp.status_code}): {resp.text}")
    return resp.json()



def summarize_file_via_backend(file) -> str:
    token = get_forwarded_token()
    file.seek(0)
    resp = requests.post(
        f"{API_BASE_URL}/summarize/file",
        headers={"Authorization": f"Bearer {token}", "X-Forwarded-Access-Token": token},
        files={"file": (file.name, file.read(), _mime(file.name))},
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Summarize failed ({resp.status_code}): {resp.text}")
    return resp.json()["summary"]


def summarize_prompt_via_backend(user_prompt: str) -> str:
    token = get_forwarded_token()
    resp = requests.post(
        f"{API_BASE_URL}/summarize/prompt",
        headers={"Authorization": f"Bearer {token}", "X-Forwarded-Access-Token": token},
        json={"user_prompt": user_prompt},
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Prompt summarize failed ({resp.status_code}): {resp.text}")
    return resp.json()["summary"]


def _mime(filename: str) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


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

defaults = {
    "data_migration_store": {},
    "ml_store": {},
    "reporting_store": {},
    "llm_store": {},
    "final_prompt": "",
    "raw_prompt": "",
    "gdrive_link": None,
    "summary": "",
    "image_urls": [],
    "pdf_urls": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_image("./assets/sigmoid-logo.jpeg")

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

    st.subheader("Budget")
    annual_budget = st.number_input("Annual Cloud Budget (USD)", min_value=0, value=0, step=10000)

    st.subheader("Global Consumption Multiplier")
    global_consumption_multiplier = st.number_input("Consumption Multiplier", min_value=0.0, value=1.0, step=0.1)
    st.session_state["global_consumption_multiplier"] = global_consumption_multiplier

    st.subheader("Market Configuration")
    number_of_markets = st.number_input("Number of Markets", min_value=0, max_value=10, value=0)

    markets = []
    for i in range(int(number_of_markets)):
        markets.append({
            "market": f"M{i+1}",
            "start_month": st.selectbox(f"Market Entry Month (M{i+1})", list(range(1, 13)), key=f"m_month_{i}")
        })

    use_case_type = st.selectbox("Use Case Type", use_case)

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
            st.number_input("GPU Usage (hours/day)", min_value=0, value=0) if ml["use_gpu"] == "Yes" else 0
        )
        ml["model_retention_days"] = st.number_input("Model Retention (days)", min_value=0, value=0)

    if use_case_type == "Reporting":
        rp = st.session_state.reporting_store
        st.subheader("Reporting Inputs")
        rp["cloud_type"] = st.multiselect("Cloud Type", cloud_options, default=[])
        rp["tool"] = st.selectbox("Reporting Tool", reporting_tool)
        rp["user_type"] = st.radio("User Subscription", user_subscription)
        rp["number_of_users"] = st.number_input("Number of Users", min_value=0, value=0)

    if use_case_type == "GEN AI":
        llm = st.session_state.llm_store
        st.subheader("LLM Inputs")
        llm["architectural_component"] = st.selectbox("Architectural Component", list(ARCH_COMPONENT_MAP.keys()))
        llm["platform"] = st.selectbox("Platform", list(ARCH_COMPONENT_MAP[llm["architectural_component"]].keys()))
        llm["llm_type"] = st.selectbox("LLM Type", list(ARCH_COMPONENT_MAP[llm["architectural_component"]][llm["platform"]].keys()))
        llm["llm_version"] = st.selectbox("LLM Model Version", ARCH_COMPONENT_MAP[llm["architectural_component"]][llm["platform"]][llm["llm_type"]])
        llm["requests_per_day"] = st.number_input("Requests per Day", min_value=0, value=0)
        llm["avg_tokens_per_request"] = st.number_input("Avg Tokens per Request", min_value=0, value=0)
        llm["concurrent_users"] = st.number_input("Concurrent Users", min_value=0, value=0)
        llm["data_retention_days"] = st.number_input("Prompt / Response Retention (days)", min_value=0, value=0)


# UPLOAD ARTIFACTS 
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
                try:
                    result = upload_file_to_backend(file)
                    already_tracked = (
                        result["url"] in st.session_state.image_urls or
                        result["url"] in st.session_state.pdf_urls
                    )
                    if not already_tracked:
                        if result["file_type"] == "pdf":
                            st.session_state.pdf_urls.append(result["url"])
                        else:
                            st.session_state.image_urls.append(result["url"])
                        st.success(f"Uploaded: {file.name}")
                    else:
                        st.info(f"Already uploaded: {file.name}")
                except RuntimeError as e:
                    st.error(str(e))

# ANALYZE FILES —
if st.button("Analyze Files"):
    if not uploaded_files:
        st.warning("Please select files first.")
    else:
        summary = ""
        with st.spinner("Analyzing..."):
            for file in uploaded_files:
                try:
                    summary += summarize_file_via_backend(file)
                except RuntimeError as e:
                    st.error(f"Failed to summarize {file.name}: {e}")
        st.session_state.summary = summary

# AI ANALYSIS 
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
            llm_summary = summarize_prompt_via_backend(st.session_state.raw_prompt)
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

        clean_prompt = prompt_input.split("Summary:")[0].strip()
        token = get_forwarded_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Forwarded-Access-Token": token,
        }

        try:
            submit_resp = requests.post(
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
                timeout=15,
            )

            if is_html_response(submit_resp):
                st.error("Authentication failed. Please refresh and try again.")
                st.stop()

            if submit_resp.status_code != 200:
                st.error(f"API error {submit_resp.status_code}: {submit_resp.text}")
                st.stop()
                
            st.session_state["gdrive_link"] = None
            st.session_state["current_job_id"] = submit_resp.json()["job_id"]

        except requests.exceptions.Timeout:
            st.error("Job submission timed out. Please try again.")
            st.stop()
        except Exception as e:
            st.error(f"Failed to submit job: {e}")
            st.stop()

    if st.session_state.get("current_job_id") and not st.session_state.get("gdrive_link"):
        job_id = st.session_state["current_job_id"]
        token = get_forwarded_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Forwarded-Access-Token": token,
        }
        poll_placeholder = st.empty()

        with st.spinner("Processing... this may take a few minutes."):
            for attempt in range(150):
                try:
                    status_resp = requests.get(
                        f"{API_BASE_URL}/status/{job_id}",
                        headers=headers,
                        timeout=10,
                    )

                    if is_html_response(status_resp):
                        poll_placeholder.error("Authentication failed while polling. Please refresh and try again.")
                        st.session_state["current_job_id"] = None
                        st.stop()

                    if status_resp.status_code == 404:
                        poll_placeholder.error("Job not found. It may have expired — please re-submit.")
                        st.session_state["current_job_id"] = None
                        st.stop()

                    if status_resp.status_code != 200:
                        poll_placeholder.warning(f"Unexpected status {status_resp.status_code} — retrying...")
                        time.sleep(4)
                        continue

                    data = status_resp.json()

                except requests.exceptions.Timeout:
                    poll_placeholder.warning(f"Poll timed out (attempt {attempt + 1}) — retrying...")
                    time.sleep(4)
                    continue
                except Exception as e:
                    poll_placeholder.warning(f"Polling error (attempt {attempt + 1}): {e} — retrying...")
                    time.sleep(4)
                    continue

                if data["status"] == "done":
                    st.session_state.gdrive_link = data["drive_link"]
                    st.session_state["current_job_id"] = None
                    st.rerun()

                elif data["status"] == "error":
                    st.error(f"Estimation failed: {data.get('error', 'Unknown error')}")
                    st.session_state["current_job_id"] = None
                    st.stop()

                else:
                    poll_placeholder.info(f"Estimating... (check {attempt + 1}/150 — refreshing every 4s)")
                    time.sleep(4)

            else:
                st.error("Timed out waiting for the result after ~10 minutes. Please refresh to check again.")
                st.session_state["current_job_id"] = None

if st.session_state.gdrive_link:
    st.markdown("---")
    st.link_button("Open Result in Google Drive", st.session_state.gdrive_link, use_container_width=True)