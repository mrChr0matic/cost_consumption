# Databricks notebook source
import sys
import json
from llm.llm import run_llm_pipeline

# COMMAND ----------

import sys
import json

def main():
    print("===== RAW sys.argv (in order) =====")
    for i, arg in enumerate(sys.argv):
        print(f"argv[{i}]: {repr(arg)}")
    print("==================================")

    # Stop here intentionally for inspection
    return


if __name__ == "__main__":
    main()


# COMMAND ----------

# import sys
# import json

# def get_job_param(param_name: str) -> str:
#     """
#     Databricks injects job params into sys.argv in arbitrary positions.
#     We must search for the key and read the value after it.
#     """
#     if param_name not in sys.argv:
#         raise ValueError(f"Missing job parameter: {param_name}")

#     idx = sys.argv.index(param_name)
#     if idx + 1 >= len(sys.argv):
#         raise ValueError(f"No value provided for job parameter: {param_name}")

#     return sys.argv[idx + 1]


# def main():
#     payload_str = get_job_param("payload")

#     try:
#         params = json.loads(payload_str)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"Invalid JSON payload: {payload_str}") from e

#     required_keys = ["image_uri", "client_name", "use_case_name"]
#     for key in required_keys:
#         if key not in params:
#             raise ValueError(f"Missing required parameter: {key}")

#     markets = params.get("markets", [])

#     print("Starting LLM pipeline with parameters:")
#     print(json.dumps(params, indent=2))

#     result = run_llm_pipeline(
#         image_uri=params["image_uri"],
#         client_name=params["client_name"],
#         use_case_name=params["use_case_name"],
#         markets=markets
#     )

#     print("PIPELINE_RESULT_JSON")
#     print(json.dumps(result))


# if __name__ == "__main__":
#     main()
