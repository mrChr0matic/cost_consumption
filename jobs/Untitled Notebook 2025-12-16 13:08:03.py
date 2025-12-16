# Databricks notebook source
OPEN_AI_KEY = dbutils.secrets.get("llm-secrets", "OPEN_AI_API_KEY")
OPEN_AI_MODEL = dbutils.secrets.get("llm-secrets", "OPEN_AI_MODEL")
OPEN_AI_ENDPOINT = dbutils.secrets.get("llm-secrets", "OPEN_AI_ENDPOINT")
AZURE_CONN_STR = dbutils.secrets.get("llm-secrets", "AZURE_STORAGE_CONNECTION_STRING")
DRIVE_FOLDER_ID = dbutils.secrets.get("llm-secrets", "DRIVE_FOLDER_ID")
GOOGLE_SA_JSON = dbutils.secrets.get("llm-secrets", "GOOGLE_DRIVE_SA_JSON")


# COMMAND ----------

secrets = {
    "OPEN_AI_KEY": OPEN_AI_KEY,
    "OPEN_AI_MODEL": OPEN_AI_MODEL,
    "OPEN_AI_ENDPOINT": OPEN_AI_ENDPOINT,
    "AZURE_STORAGE_CONNECTION_STRING": AZURE_CONN_STR,
    "DRIVE_FOLDER_ID": DRIVE_FOLDER_ID,
    "GOOGLE_SA_JSON": GOOGLE_SA_JSON
}

# COMMAND ----------



# COMMAND ----------

