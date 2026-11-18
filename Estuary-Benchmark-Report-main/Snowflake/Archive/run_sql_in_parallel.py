import snowflake.connector
import time
import csv
import os
from dotenv import load_dotenv
from queries import queries
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

def run_query_and_save_metrics(query_description, query, warehouse, snowflake_database, query_tag):
    try:
        
        # Establish a new connection for each thread
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

        cur.execute(f"""USE WAREHOUSE {warehouse};""")
        cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
        
        print(f"\n\nRunning query: {query_description}\n")

        # Record query start time
        start_time = time.time() * 1000  # Convert to milliseconds

        cur.execute(query)
        result = cur.fetchall()

        # Record query end time
        end_time = time.time() * 1000  # Convert to milliseconds
        response_time = end_time - start_time

        query_id = cur.sfqid

        # Get query performance metrics
        cur.execute(f"""
            SELECT QUERY_ID, TOTAL_ELAPSED_TIME, BYTES_SCANNED/1024/1024 AS mb_scanned,
                   ROWS_PRODUCED, CREDITS_USED_CLOUD_SERVICES
            FROM TABLE({snowflake_database}.INFORMATION_SCHEMA.QUERY_HISTORY())
            WHERE QUERY_ID = '{query_id}'
        """)
        metrics = cur.fetchone()

        query_metrics = {
            'query_description': query_description,
            'response_time_ms': response_time,
            'snowflake_official_time_in_milli_sec': metrics[1] if metrics else None,
            'mb_scanned': round(metrics[2], 4) if metrics and metrics[2] else 0,
            'rows_produced': metrics[3] if metrics else None,
            'credits_used': metrics[4] if metrics else None,
            'warehouse': warehouse,
            'query_id': query_id,
            'run_type': 'Parallel',
            'query_tag': query_tag
        }

        output_file = 'query_stats.csv'
        file_exists = os.path.isfile(output_file)
        
        with open(output_file, mode='a', newline='') as file:
            fieldnames = ['query_description', 'response_time_ms', 'snowflake_official_time_in_milli_sec',
                          'mb_scanned', 'rows_produced', 'credits_used', 'warehouse', 'query_id', 'run_type', 'query_tag']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(query_metrics)

        print(f"Metrics saved for query: {query_description}")

    except Exception as e:
        print(f"Error in 'run_query_and_save_metrics' for query {query_description}: {e}")
    finally:
        cur.close()
        conn.close()


def main():
    try:
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        snowflake_database = os.getenv("SNOWFLAKE_DATABASE")
        query_tag = os.getenv("QUERY_TAG")

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            # Correcting the passing of query_tag and queries list to the function
            executor.map(lambda q: run_query_and_save_metrics(q[0], q[1], warehouse, snowflake_database, query_tag), queries)
    
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
