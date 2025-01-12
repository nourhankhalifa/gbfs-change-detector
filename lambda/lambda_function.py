import boto3
import requests
import json
import pymysql  # For MySQL, or use psycopg2 for PostgreSQL
from datetime import datetime
import os

# AWS Clients
s3_client = boto3.client("s3")

# Configuration
S3_BUCKET_NAME = "gbfs-data-storage"
RDS_HOST = "gbfs-database.cn0gw6o6coo5.us-east-1.rds.amazonaws.com"
RDS_PORT = 3306  # Default port for MySQL
RDS_USER = "admin"
RDS_PASSWORD = os.getenv('rds_password')
RDS_DATABASE = "gbfs-database"

# Load provider configuration from environment variable
providers = json.loads(os.getenv("providers", "[]"))

if not providers:
    raise ValueError("No providers configured. Set the PROVIDERS environment variable.")


# Relevant feeds to fetch
relevant_feeds = ["station_status"]

# Establish a database connection
def get_db_connection():
    connection = pymysql.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DATABASE,
        port=RDS_PORT
    )
    return connection

# Fetch GBFS JSON
def fetch_gbfs(provider):
    response = requests.get(provider['url'])
    if response.status_code == 200:
        data = response.json()
        timestamp = datetime.now().isoformat()
        return {"provider": provider["name"], "timestamp": timestamp, "data": data}
    else:
        print(f"Failed to fetch GBFS data for {provider['name']}")
        return None

# Extract the feed URL
def get_feed_url(feeds, feed_name):
    for feed in feeds:
        if feed['name'] == feed_name:
            return feed['url']
    return None

# Fetch specific feed data
def fetch_feed_data(feed_url):
    response = requests.get(feed_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch feed data from {feed_url}")
        return None

# Extract stats
def extract_stats(feed_name, feed_data):
    if feed_name == "station_status":
        stations = feed_data.get("data", {}).get("stations", [])
        total_bikes = sum(station.get("num_bikes_available", 0) for station in stations)
        available_docks = sum(station.get("num_docks_available", 0) for station in stations)
        return {"total_bikes": total_bikes, "available_docks": available_docks}
    return {}

# Save raw JSON to S3
def save_to_s3(bucket_name, key, data):
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data),
        ContentType="application/json"
    )
    print(f"Saved {key} to S3 bucket {bucket_name}")

# Save stats to RDS
def save_to_rds(connection, provider_name, feed_name, stats):
    try:
        with connection.cursor() as cursor:
            # Create table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS gbfs_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                provider VARCHAR(255),
                feed VARCHAR(255),
                timestamp DATETIME,
                total_bikes INT,
                available_docks INT
            )
            """
            cursor.execute(create_table_query)

            # Insert stats
            insert_query = """
            INSERT INTO gbfs_stats (provider, feed, timestamp, total_bikes, available_docks)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                provider_name,
                feed_name,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                stats["total_bikes"],
                stats["available_docks"]
            ))
        connection.commit()
        print(f"Saved stats for {provider_name} ({feed_name}) to RDS")
    except Exception as e:
        print(f"Failed to save stats to RDS: {e}")

# Lambda entry point
def lambda_handler(event, context):
    connection = get_db_connection()
    try:
        for provider in providers:
            # Fetch GBFS JSON
            result = fetch_gbfs(provider)
            if result:
                # Save raw GBFS data to S3
                gbfs_key = f"{provider['name']}/gbfs.json"
                save_to_s3(S3_BUCKET_NAME, gbfs_key, result)

                # Extract relevant feeds
                feeds = result['data']['data']['en']['feeds']
                for feed_name in relevant_feeds:
                    feed_url = get_feed_url(feeds, feed_name)
                    if feed_url:
                        # Fetch feed data
                        feed_data = fetch_feed_data(feed_url)
                        if feed_data:
                            # Save raw feed data to S3
                            feed_key = f"{provider['name']}/{feed_name}.json"
                            save_to_s3(S3_BUCKET_NAME, feed_key, feed_data)

                            # Extract and save stats
                            stats = extract_stats(feed_name, feed_data)
                            if stats:
                                save_to_rds(connection, provider["name"], feed_name, stats)
    finally:
        connection.close()
