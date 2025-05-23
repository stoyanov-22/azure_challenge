# Databricks notebook source
# MAGIC %md
# MAGIC ### Run Configs

# COMMAND ----------

# MAGIC %run "/Workspace/Shared/utils"

# COMMAND ----------

start_time = time.time()

logger.info("Starting notebook execution.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Daily weather and air quality data

# COMMAND ----------

DEBUG_MODE = True

daily_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/daily_weather_air_data_delta"
aggregated_data_path = f"abfss://databricks@{storage_account_name}.dfs.core.windows.net/aggregated_weather_air_data_delta"

# Cities to fetch data for
cities_file_location = "/dbfs/FileStore/tables/cities.json"

with open(cities_file_location, 'r') as f:
    config_data = json.load(f)
    cities = config_data.get("target_cities", [])

# Initialize list for combined data
daily_data = []

def fetch_city_data(city):
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        weather_json = fetch_api_data(weather_url)
        if not weather_json:
            logger.warning(f"Failed to fetch weather data for {city}")
            return None

        lat, lon = weather_json["coord"]["lat"], weather_json["coord"]["lon"]
        air_pollution_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        air_pollution_json = fetch_api_data(air_pollution_url)
        if not air_pollution_json:
            logger.warning(f"Failed to fetch air pollution data for {city}")
            return None

        return Row(
            city=city,
            date=datetime.now().strftime("%Y-%m-%d"),
            temperature=float(weather_json["main"]["temp"]),
            humidity=float(weather_json["main"]["humidity"]),
            weather=weather_json["weather"][0]["description"],
            wind_speed=float(weather_json["wind"]["speed"]),
            air_quality_index=float(air_pollution_json["list"][0]["main"]["aqi"]),
            pm2_5=float(air_pollution_json["list"][0]["components"]["pm2_5"]),
            pm10=float(air_pollution_json["list"][0]["components"]["pm10"]),
            co2=float(air_pollution_json["list"][0]["components"]["co"])
        )

    except Exception as e:
        logger.error(f"Error fetching data for {city}: {e}")
        return None

# Threaded fetching
with ThreadPoolExecutor(max_workers=8) as executor:
    future_to_city = {executor.submit(fetch_city_data, city): city for city in cities}
    for future in as_completed(future_to_city):
        result = future.result()
        if result:
            daily_data.append(result)
logger.info("Data is fetched for all cities successfully!")

# Convert today's data to DataFrame
logger.info("Converting data to Spark DataFrame.")
if not daily_data:
    logger.warning("No daily data fetched, skipping merge operation for daily data.")
else:
    daily_df = spark.createDataFrame(daily_data)
    logger.info("Attempting to merge daily data into Delta Lake.")

    try:
        # Get a DeltaTable object for the target path
        target_daily_table = DeltaTable.forPath(spark, daily_data_path)

        # Perform the MERGE
        # Alias target as 't' and source (today's data) as 's'
        target_daily_table.alias("t") \
            .merge(
                daily_df.alias("s"),
                # Condition to check if a row for the same city and exact timestamp already exists
                "t.city = s.city AND t.date = s.date"
            ) \
            .whenNotMatchedInsertAll().execute() # Insert the row from source ('s') if no match is found in target ('t')


        logger.info(f"Daily weather and air quality data successfully merged into {daily_data_path}")

    except Exception as e:
        # Check if the error is because the table doesn't exist yet
        if "is not a Delta table" in str(e) or "Path does not exist" in str(e):
             logger.info(f"Delta table {daily_data_path} not found. Creating new table.")
             daily_df.write.format("delta").save(daily_data_path) # Create table on first run
             logger.info(f"New daily data table created at {daily_data_path}")
        else:
            logger.error(f"Error merging data into Delta table {daily_data_path}: {e}")
            raise e # Re-throw other errors


# COMMAND ----------

# MAGIC %md
# MAGIC ### Check for weather anomalies in collected data

# COMMAND ----------

for row in daily_data:
    alerts = detect_anomalies(row)
    for alert in alerts:
        logger.warning(alert)  # Log alert

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

logger.info("Notebook Execution Completed Successfully!")

end_time = time.time()
execution_time = __builtins__.round(end_time - start_time, 2)

logger.info(f"Notebook execution completed in {execution_time} seconds.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Preview

# COMMAND ----------

# Load and display the daily and aggregated data
if DEBUG_MODE:
    daily = spark.read.format("delta").load(daily_data_path)
    aggregated = spark.read.format("delta").load(aggregated_data_path)

    display(daily.orderBy("date", ascending=False))
    display(aggregated.orderBy("month", ascending=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Logs Preview
# MAGIC

# COMMAND ----------

# Load and display the logs data ordered by timestamp in descending order
if DEBUG_MODE:
    logs = spark.read.format("delta").load(log_table_path)

    display(logs.orderBy(desc("timestamp")))