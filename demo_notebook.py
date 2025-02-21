# Databricks notebook source
# MAGIC %pip install loguru

# COMMAND ----------

import requests
import time
import json

from loguru import logger
from pyspark.sql import Row
from pyspark.sql.functions import col, avg, min, max, year, month, round, date_format, desc
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configs

# COMMAND ----------

def automount(databricks_scope, sa_name, sa_key, api):
    storage_account_name = dbutils.secrets.get(databricks_scope, sa_name)

    spark.conf.set(
        f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
        dbutils.secrets.get(scope=databricks_scope, key=sa_key))
    
    API_KEY = dbutils.secrets.get(databricks_scope, api)

    return API_KEY, storage_account_name

API_KEY, storage_account_name = automount("my-keyvault-scope", "storageAccountName", "storageAccountKey", "weather-api")

daily_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/daily_weather_air_data_delta"
aggregated_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/aggregated_weather_air_data_delta"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Logger

# COMMAND ----------

# Initialize Logger
log_table_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/logs/databricks_logs"

# Function to write logs immediately to Delta
def log_sink(message):
    parts = message.split(" - ", 2)  # Splitting into time, level, and message
    if len(parts) == 3:
        log_row = [Row(timestamp=parts[0], level=parts[1], message=parts[2])]
        log_df = spark.createDataFrame(log_row)
        log_df.write.mode("append").format("delta").save(log_table_path)  # Append log entry to Delta

# Configure Loguru to use log_sink
logger.remove()
logger.add(lambda msg: print(msg, end=""), format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}", level="INFO")
logger.add(log_sink, format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}")

logger.info("Logger initialized!")


# COMMAND ----------

# MAGIC %md
# MAGIC ### Daily weather and air quality data

# COMMAND ----------

# Cities list
cities = ["Sliven", "London", "Paris", "Berlin", "Edinburgh", "New York"]

# Initialize list for combined data
daily_data = []

# Fetch data from APIs
for city in cities:
    logger.info(f"Fetching weather data for {city}.")
    # Fetch Weather Data
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    weather_response = requests.get(weather_url)

    if weather_response.status_code == 200:
        weather_json = weather_response.json()
        lat, lon = weather_json["coord"]["lat"], weather_json["coord"]["lon"]

        logger.info(f"Fetching air pollution data for {city}.")
        # Fetch Air Pollution Data
        air_pollution_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        air_pollution_response = requests.get(air_pollution_url)

        if air_pollution_response.status_code == 200:
            air_pollution_json = air_pollution_response.json()

            # Append data to list
            daily_data.append(Row(
                city=city,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                temperature=float(weather_json["main"]["temp"]),
                humidity=float(weather_json["main"]["humidity"]),
                weather=weather_json["weather"][0]["description"],
                wind_speed=float(weather_json["wind"]["speed"]),
                air_quality_index=float(air_pollution_json["list"][0]["main"]["aqi"]),
                pm2_5=float(air_pollution_json["list"][0]["components"]["pm2_5"]),
                pm10=float(air_pollution_json["list"][0]["components"]["pm10"]),
                co2=float(air_pollution_json["list"][0]["components"]["co"]) 
            ))
        else:
            logger.warning(f"Failed to fetch air pollution data for {city}, Status Code: {air_pollution_response.status_code}")
    else:
        logger.warning(f"Failed to fetch weather data for {city}, Status Code: {weather_response.status_code}")

# Convert today's data to DataFrame
logger.info("Converting data to Spark DataFrame.")
daily_df = spark.createDataFrame(daily_data)

# Try to read existing historical daily data
try:
    historical_daily_df = spark.read.format("delta").load(daily_data_path)
    combined_daily_df = historical_daily_df.union(daily_df)
    logger.info("Merged new data with existing historical data.")
except Exception:
    combined_daily_df = daily_df
    logger.info("No existing data found. Creating new dataset.")  # If table doesn't exist, just use today's data

# Store the updated daily data (overwrite ensures full history is maintained)
logger.info("Writing daily data to Delta Lake.")
combined_daily_df.write.mode("overwrite").format("delta").save(daily_data_path)
logger.info(f"Daily weather and air quality data successfully stored.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Monthly aggregated weather and air quality data, including temperature, humidity, and AQI

# COMMAND ----------

# Aggregate Monthly Statistics
logger.info("Calculating monthly aggregates.")
df_temp = spark.read.format("delta").load(daily_data_path) # Reloading the table

aggregated_df = (
    df_temp.withColumn("year", year(col("date")))
    .withColumn("month", date_format(col("date"), "MMMM"))
    .groupBy("city", "year", "month")
    .agg(
        min("temperature").alias("min_temp"),
        max("temperature").alias("max_temp"),
        round(avg("temperature"), 2).alias("avg_temp"),
        min("humidity").alias("min_humidity"),
        max("humidity").alias("max_humidity"),
        round(avg("humidity"), 2).alias("avg_humidity"),
        min("wind_speed").alias("min_wind_speed"),
        max("wind_speed").alias("max_wind_speed"),
        round(avg("wind_speed"), 2).alias("avg_wind_speed"),
        min("air_quality_index").alias("min_aqi"),
        max("air_quality_index").alias("max_aqi"),
        round(avg("air_quality_index"), 2).alias("avg_aqi"),
        min("pm2_5").alias("min_pm2_5"),
        max("pm2_5").alias("max_pm2_5"),
        round(avg("pm2_5"), 2).alias("avg_pm2_5"),
        min("pm10").alias("min_pm10"),
        max("pm10").alias("max_pm10"),
        round(avg("pm10"), 2).alias("avg_pm10"),
        min("co2").alias("min_co2"),
        max("co2").alias("max_co2"),
        round(avg("co2"), 2).alias("avg_co2")
    )
)

# Store Aggregated Data
logger.info("Writing aggregated data to Delta Lake.")
aggregated_df.write.mode("overwrite").format("delta").save(aggregated_data_path)
logger.info(f"Aggregated data updated successfully.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Preview

# COMMAND ----------

# Load and display the daily and aggregated data

daily = spark.read.format("delta").load(daily_data_path)
aggregated = spark.read.format("delta").load(aggregated_data_path)

display(daily)
display(aggregated)

# COMMAND ----------

logger.info("Notebook Execution Completed Successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Logs Preview
# MAGIC

# COMMAND ----------

logs = spark.read.format("delta").load(log_table_path)
logs.orderBy(desc("timestamp")).display()