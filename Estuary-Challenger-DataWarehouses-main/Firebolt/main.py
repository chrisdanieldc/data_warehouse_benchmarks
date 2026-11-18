import os
from dotenv import load_dotenv
from firebolt.db import connect
from firebolt.client.auth import ClientCredentials
import time
import csv
from queries import queries  # Assuming this is defined elsewhere

def run_query_and_save_metrics(cur, query_description, query, engine_name):
    print(f"\nExecuting: {query_description}\n")

    # Measure client-side response time
    start_time = time.time()
    cur.execute(query)
    result = cur.fetchall()  # Fetch results if applicable
    end_time = time.time()
    client_response_time = (end_time - start_time) * 1000  # Convert to milliseconds

    # Skip official Firebolt query statistics for now
    official_time_ms = None

    row_produced = len(result)
    query_metrics = {
        'query_description': query_description,
        'response_time_ms': client_response_time,
        'official_time_ms': official_time_ms,
        'row_produced': row_produced,
        'warehouse': engine_name,
        'run_type': 'Linear',
        'error': None  # No error for successful execution
    }

    output_file = 'query_stats.csv'
    file_exists = os.path.isfile(output_file)
    with open(output_file, mode='a', newline='') as file:
        fieldnames = ['query_description', 'response_time_ms', 'official_time_ms', 'row_produced', 'warehouse', 'run_type', 'error']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(query_metrics)

    print(f"Client-side response time: {client_response_time:.2f} ms")
    print(f"Official Firebolt time: Not retrieved (skipped)")
    print(f"Rows produced: {row_produced}")

def disable_caching(cur):
    try:
        print("Disabling result cache...")
        cur.execute("SET enable_result_cache = FALSE")

        print("Disabling subresult cache...")
        cur.execute("SET enable_subresult_cache = FALSE")
    except Exception as e:
        print(f"Error disabling cache: {e}")

def log_failed_query(query_description, engine_name, error_message):
    output_file = 'query_stats.csv'
    file_exists = os.path.isfile(output_file)
    with open(output_file, mode='a', newline='') as file:
        fieldnames = ['query_description', 'response_time_ms', 'official_time_ms', 'row_produced', 'warehouse', 'run_type', 'error']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'query_description': query_description,
            'response_time_ms': None,
            'official_time_ms': None,
            'row_produced': None,
            'warehouse': engine_name,
            'run_type': 'Linear',
            'error': error_message
        })

def main():
    load_dotenv()

    account_name = os.getenv("FIREBOLT_ACCOUNT")
    client_id = os.getenv("FIREBOLT_CLIENT_ID")
    client_secret = os.getenv("FIREBOLT_CLIENT_SECRET")
    database = os.getenv("FIREBOLT_DATABASE")
    engine_name = os.getenv("FIREBOLT_ENGINE")

    print(f"Account Name: {account_name}")
    print(f"Client ID: {client_id}")
    print(f"Database: {database}")
    print(f"Engine Name: {engine_name}")

    auth = ClientCredentials(client_id, client_secret)
    test_conn = None

    try:
        test_conn = connect(
            engine_name=engine_name,
            database=database,
            account_name=account_name,
            auth=auth
        )
        test_cur = test_conn.cursor()
        test_cur.execute("SELECT 1")
        print("Database connection successful.")
    except Exception as e:
        print(f"Error testing database connection: {e}")
    finally:
        if test_conn:
            test_conn.close()

    conn = None
    try:
        conn = connect(
            engine_name=engine_name,
            database=database,
            account_name=account_name,
            auth=auth
        )
        cur = conn.cursor()

        for query_description, query in queries:
            try:
                disable_caching(cur)
                run_query_and_save_metrics(cur, query_description, query, engine_name)
            except Exception as query_error:
                print(f"Error executing {query_description}: {query_error}")
                log_failed_query(query_description, engine_name, str(query_error))

    except Exception as e:
        print(f"\nError executing query: {e}\n")
    finally:
        if conn:
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    main()