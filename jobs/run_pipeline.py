from llm.llm import run_llm_pipeline
import json
import sys

if __name__ == "__main__":
    params = json.loads(sys.argv[1])

    result = run_llm_pipeline(
        image_uri=params["image_uri"],
        client_name=params["client_name"],
        use_case_name=params["use_case_name"],
        markets=params["markets"]
    )

    print(json.dumps(result))
