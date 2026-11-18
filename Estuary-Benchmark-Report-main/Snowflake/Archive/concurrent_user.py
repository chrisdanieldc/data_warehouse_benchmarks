import snowflake.connector
import time
import csv
import os
import sys
from dotenv import load_dotenv
from queries import queries
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

load_dotenv()

# Lock for thread-safe CSV writing
csv_lock = Lock()

def run_query_and_save_metrics(query_description, query, warehouse, snowflake_database, user_id,query_tag):
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=warehouse,
            session_parameters={
                                'QUERY_TAG': query_tag
                                }
        )
        cur = conn.cursor()

        cur.execute(f"USE WAREHOUSE {warehouse};")
        cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
        
        print(f"Running query: {query_description} for {user_id}")

        start_time = time.time() * 1000
        cur.execute(query)
        result = cur.fetchall()
        end_time = time.time() * 1000
        response_time = end_time - start_time

        query_id = cur.sfqid

        cur.execute(f"""
            SELECT QUERY_ID, TOTAL_ELAPSED_TIME, BYTES_SCANNED/1024/1024 AS mb_scanned,
                   ROWS_PRODUCED, CREDITS_USED_CLOUD_SERVICES
            FROM TABLE({snowflake_database}.INFORMATION_SCHEMA.QUERY_HISTORY())
            WHERE QUERY_ID = '{query_id}'
        """)
        metrics = cur.fetchone()

        query_metrics = {
            'user_id': user_id,  # Add user_id to metrics
            'query_description': query_description,
            'response_time_ms': response_time,
            'snowflake_official_time_in_milli_sec': metrics[1] if metrics else None,
            'mb_scanned': round(metrics[2], 4) if metrics and metrics[2] else 0,
            'rows_produced': metrics[3] if metrics else None,
            'credits_used': metrics[4] if metrics else None,
            'warehouse': warehouse,
            'query_id': query_id,
            'run_type': 'concurrent_users',
            'query_tag': query_tag
        }

        output_file = 'query_stats_concurrent_users.csv'
        with csv_lock:
            file_exists = os.path.isfile(output_file)
            with open(output_file, mode='a', newline='') as file:
                fieldnames = ['user_id', 'query_description', 'response_time_ms', 'snowflake_official_time_in_milli_sec',
                              'mb_scanned', 'rows_produced', 'credits_used', 'warehouse', 'query_id', 'run_type','query_tag']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(query_metrics)

        print(f"Metrics saved for: {query_description} ({user_id})")

    except Exception as e:
        print(f"Error for query {query_description} ({user_id}): {e}")
    finally:
        cur.close()
        conn.close()

def main():
    try:
        # Check for user_id argument
        if len(sys.argv) < 2:
            print("Error: Please provide a user_id as an argument (e.g., user-1)")
            sys.exit(1)
        user_id = sys.argv[1]

        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        snowflake_database = os.getenv("SNOWFLAKE_DATABASE")
        query_tag=os.getenv("QUERY_TAG")

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            executor.map(lambda q: run_query_and_save_metrics(q[0], q[1], warehouse, snowflake_database, user_id,query_tag), queries)

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()