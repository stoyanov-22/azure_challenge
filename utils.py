# Databricks notebook source
# MAGIC %pip install loguru==0.7.3 logtail-python

# COMMAND ----------

import requests
import time
import json

from loguru import logger
from logtail import LogtailHandler
from pyspark.sql import Row
from pyspark.sql.functions import col, avg, min, max, year, month, round, date_format, desc
from datetime import datetime

# COMMAND ----------

def get_secret_scope():
    """Retrieve the first available Databricks secret scope dynamically."""
    scopes = dbutils.secrets.listScopes()
    
    if scopes:
        scope_name = scopes[0].name  # Get the first available scope
        print(f"Using secret scope: {scope_name}")
        return scope_name
    else:
        print("No secret scopes found!")
        return None

# COMMAND ----------

def automount(databricks_scope, sa_name, sa_key, api):
    """Retrieve storage credentials and API keys from Key Vault."""
    try:
        storage_account_name = dbutils.secrets.get(databricks_scope, sa_name)
        spark.conf.set(
            f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
            dbutils.secrets.get(scope=databricks_scope, key=sa_key)
        )
        API_KEY = dbutils.secrets.get(databricks_scope, api)
        print(f"Successfully mounted ADLS Gen2 and retrieved API key.")
        return API_KEY, storage_account_name
    except Exception as e:
        print(f"Failed to retrieve secrets: {e}")
        raise

databricks_scope = get_secret_scope()
API_KEY, storage_account_name = automount(databricks_scope, "storageAccountName", "storageAccountKey", "weather-api")

# COMMAND ----------

log_table_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/logs/databricks_logs"
logs_token = dbutils.secrets.get(databricks_scope, "weather-logs")
host = "s1233140.eu-nbg-2.betterstackdata.com"

def log_sink(message):
    """Write log messages to Delta."""
    parts = message.split(" - ", 2)  # Splitting into time, level, and message
    if len(parts) == 3:
        log_row = [Row(timestamp=parts[0], level=parts[1], message=parts[2])]
        log_df = spark.createDataFrame(log_row)
        log_df.write.mode("append").format("delta").save(log_table_path)  # Append log entry to Delta

# Configure Loguru to use log_sink
logger.remove()
logger.add(lambda msg: print(msg, end=""), format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}", level="INFO")
logger.add(log_sink, format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}")
logger.add(handler, format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}")

logger.info("Logger initialized!")

# COMMAND ----------

def fetch_api_data(url, max_retries=3, backoff_factor=2):
    """Fetch API data with retries for better reliability."""
    for attempt in range(max_retries):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"API request failed (attempt {attempt + 1}/{max_retries}): {response.status_code}")
            time.sleep(backoff_factor ** attempt) 

    logger.error(f"API request failed after {max_retries} retries: {url}")
    return None

# COMMAND ----------

logger.info("Utils initialized successfully.")