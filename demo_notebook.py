# Databricks notebook source
import requests
import json
from pyspark.sql import Row
from pyspark.sql.functions import col, avg, min, max, year, month, round, date_format
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configs

# COMMAND ----------

def automount(databricks_scope,sa_name, sa_key, api):
    storage_account_name = dbutils.secrets.get(databricks_scope, sa_name)

    spark.conf.set(
        f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
        dbutils.secrets.get(scope=databricks_scope, key=sa_key))
    
    API_KEY = dbutils.secrets.get(databricks_scope, api)

    return API_KEY, storage_account_name

API_KEY, storage_account_name = automount("my-keyvault-scope", "storageAccountName", "storageAccountKey", "weather-api")

daily_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/daily_weather_air_data"
aggregated_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/aggregated_weather_air_data"

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
    # Fetch Weather Data
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    weather_response = requests.get(weather_url)

    if weather_response.status_code == 200:
        weather_json = weather_response.json()
        lat, lon = weather_json["coord"]["lat"], weather_json["coord"]["lon"]

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
            print(f"Error fetching air pollution data for {city}: {air_pollution_response.status_code}")
    else:
        print(f"Error fetching weather data for {city}: {weather_response.status_code}")

# Convert today's data to DataFrame
daily_df = spark.createDataFrame(daily_data)

# Try to read existing historical daily data
try:
    historical_daily_df = spark.read.format("parquet").load(daily_data_path)
    combined_daily_df = historical_daily_df.union(daily_df) 
except Exception:
    combined_daily_df = daily_df  # If table doesn't exist, just use today's data

# Store the updated daily data (overwrite ensures full history is maintained)
combined_daily_df.write.mode("overwrite").format("parquet").save(daily_data_path)

print(f"Daily weather and air quality data successfully stored.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Monthly aggregated weather and air quality data, including temperature, humidity, and AQI

# COMMAND ----------

# Aggregate Monthly Statistics
df_temp = spark.read.format("parquet").load(daily_data_path) # Reloading the table

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
aggregated_df.write.mode("overwrite").format("parquet").save(aggregated_data_path)

print(f"Aggregated data updated successfully.")

# COMMAND ----------

# Load and display the daily and aggregated data

daily = spark.read.format("parquet").load(daily_data_path)
aggregated = spark.read.format("parquet").load(aggregated_data_path)

display(daily)
display(aggregated)