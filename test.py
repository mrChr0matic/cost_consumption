# Databricks notebook source
print(dbutils.secrets.listScopes())

# COMMAND ----------

dbutils.secrets.get("llm-secrets", "OPEN_AI_API_KEY")

# COMMAND ----------

import json
sa_info = json.loads(
        dbutils.secrets.get(
            scope="llm-secrets",
            key="GOOGLE_DRIVE_SA_JSON"
        )
    )

# COMMAND ----------

image_path = "images/arch1.png"

import os
assert os.path.exists(image_path), "Image not found"
print("Image exists and is accessible")


# COMMAND ----------

from llm.llm import run_llm_pipeline

result = run_llm_pipeline(
    image_uri="images/arch1.png",
    client_name="demo_client",
    use_case_name="demo_usecase",
    markets=[
        {"market": "M1", "multiplier": 1.0, "start_month": 1},
        {"market": "M2", "multiplier": 1.3, "start_month": 6}
    ]
)

result


# COMMAND ----------

# MAGIC %pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

from llm.llm import run_llm_pipeline
import json
import sys

if __name__ == "__main__":
    params = json.loads(sys.argv[1])

    result = run_llm_pipeline(
        image_uri=params["image_uri"],
        client_name=params["client_name"],
        use_case_name=params["use_case_name"],
        markets=params["markets"],
    )

    print(json.dumps(result))
