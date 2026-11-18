import pyodbc
import time
import csv
import os
import concurrent.futures
from dotenv import load_dotenv
from queries import queries

load_dotenv()

def run_query(query_description, query, workspace_url, database, auth_method, tenant_id=None, client_id=None, client_secret=None, sql_username=None, sql_password=None, query_tag=None):
    try:
        print(f"\n\nRunning this query in parallel = {query_description}\n")
        server = workspace_url.replace('https://', '')

        if auth_method.lower() == "sql":
            connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={database};UID={sql_username};PWD={sql_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        else:
            connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={database};Authentication=ActiveDirectoryServicePrincipal;UID={client_id}@{tenant_id};PWD={client_secret};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        start_time = time.time() * 1000
        cursor.execute(query)

        rows = []
        if cursor.description:
            rows = cursor.fetchall()
            print(f"Query {query_description} returned {len(rows)} rows")
        else:
            print(f"Query {query_description} executed successfully but returned no result set")

        end_time = time.time() * 1000
        response_time = end_time - start_time
        rows_produced = len(rows)
        job_id = f"synapse_parallel_{int(time.time())}_{query_description.replace(' ', '_')}"
        time.sleep(1)

        official_time = None
        try:
            stats_queries = [
                "SELECT TOP 1 total_elapsed_time FROM sys.dm_pdw_exec_requests WHERE CONVERT(VARCHAR(50), session_id) = CONVERT(VARCHAR(50), @@SPID) ORDER BY submit_time DESC",
                "SELECT TOP 1 total_elapsed_time FROM sys.dm_exec_requests WHERE CONVERT(VARCHAR(50), session_id) = CONVERT(VARCHAR(50), @@SPID) ORDER BY start_time DESC",
                "SELECT TOP 1 total_elapsed_time FROM sys.dm_pdw_exec_requests ORDER BY submit_time DESC",
                "SELECT TOP 1 elapsed_time_in_ms FROM sys.dm_exec_query_stats ORDER BY last_execution_time DESC"
            ]
            for i, stats_query in enumerate(stats_queries):
                try:
                    cursor.execute(stats_query)
                    stats_row = cursor.fetchone()
                    if stats_row and stats_row[0] is not None:
                        official_time = stats_row[0]
                        print(f"Found official time using approach #{i+1}: {official_time} ms")
                        break
                except Exception as e:
                    print(f"Stats query approach #{i+1} failed: {e}")
            if official_time is not None:
                print(f"Query {query_description} official time: {official_time} ms")
        except Exception as e:
            print(f"Error getting official time for query {query_description}: {e}")

        mb_scanned = None
        try:
            io_stats_query = "SELECT SUM(reads) * 8 / 1024.0 AS mb_read FROM sys.dm_exec_requests r JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id WHERE s.session_id = @@SPID"
            cursor.execute(io_stats_query)
            mb_stats = cursor.fetchone()
            mb_scanned = round(float(mb_stats[0]), 2) if mb_stats and mb_stats[0] is not None else None
            if mb_scanned is not None:
                print(f"Query {query_description} MB scanned: {mb_scanned}")
        except Exception as e:
            print(f"Error getting MB scanned for query {query_description}: {e}")

        if official_time is None:
            official_time = ""
        if mb_scanned is None:
            mb_scanned = ""

        cursor.close()
        conn.close()
        
        return {
            'query_description': query_description,
            'response_time_ms': round(response_time, 2),
            'synapse_official_time_in_milli_sec': official_time,
            'mb_scanned': mb_scanned,
            'rows_produced': rows_produced,
            'database': database,
            'job_id': job_id,
            'run_type': 'Parallel',
            'query_tag': query_tag
        }
    except Exception as e:
        print(f"Unexpected error in 'run_query' for {query_description}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    try:
        workspace_url = os.getenv("AZURE_SYNAPSE_WORKSPACE_URL")
        database = os.getenv("AZURE_SYNAPSE_DATABASE")
        auth_method = os.getenv("AUTH_METHOD", "SQL")
        query_tag = os.getenv("QUERY_TAG", "benchmark_testing")

        if auth_method.lower() == "sql":
            sql_username = os.getenv("SQL_USERNAME")
            sql_password = os.getenv("SQL_PASSWORD")
            tenant_id = None
            client_id = None
            client_secret = None
            if not sql_username or not sql_password:
                raise ValueError("SQL_USERNAME and SQL_PASSWORD required for SQL authentication")
        else:
            tenant_id = os.getenv("AZURE_TENANT_ID")
            client_id = os.getenv("AZURE_CLIENT_ID")
            client_secret = os.getenv("AZURE_CLIENT_SECRET")
            sql_username = None
            sql_password = None
            if not all([tenant_id, client_id, client_secret]):
                raise ValueError("AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET required for Service Principal authentication")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    run_query, 
                    query_description, 
                    query, 
                    workspace_url,
                    database,
                    auth_method,
                    tenant_id,
                    client_id,
                    client_secret,
                    sql_username,
                    sql_password,
                    query_tag
                ) 
                for query_description, query in queries
            ]
            
            output_dir = 'AzureSynapseAnalytics'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'query_stats_run_in_parallel.csv')
            file_exists = os.path.isfile(output_file)

            with open(output_file, mode='a', newline='') as file:
                fieldnames = [
                    'query_description', 'response_time_ms', 'synapse_official_time_in_milli_sec', 
                    'mb_scanned', 'rows_produced', 'database', 'job_id', 'run_type', 'query_tag'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        writer.writerow(result)
                        print(f"Metrics saved to {output_file} for query {result['query_description']}")
        
        print(f"\nAll parallel queries completed. Results saved to {output_file}")
        
    except Exception as e:
        print(f"Unexpected error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
