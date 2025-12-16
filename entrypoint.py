import sys
import json
import logging
from llm.llm import run_llm_pipeline

# -------------------------
# Logging configuration
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def _get_user_json_arg() -> dict:
    """
    Databricks injects internal flags (e.g. -f).
    User parameters are passed as positional JSON strings.
    """
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


def main():
    params = _get_user_json_arg()

    # -------------------------
    # Validate inputs
    # -------------------------
    required_keys = ("image_uri", "client_name", "use_case_name")
    for key in required_keys:
        if key not in params:
            raise ValueError(f"Missing required parameter: {key}")

    image_uri = params["image_uri"]
    client_name = params["client_name"]
    use_case_name = params["use_case_name"]
    markets = params.get("markets", [])
    user_prompt = params.get("user_prompt")
    budget = params.get("budget")

    logger.info("Starting LLM pipeline")
    logger.info("Client: %s | Use case: %s", client_name, use_case_name)
    logger.info("Image URI: %s", image_uri)
    logger.info("Markets: %s", markets)

    # -------------------------
    # Run LLM pipeline
    # -------------------------
    result = run_llm_pipeline(
        image_uri=image_uri,
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


if __name__ == "__main__":
    main()
