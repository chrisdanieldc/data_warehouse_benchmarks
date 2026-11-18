import pyodbc
import time
import csv
import os
import json
from dotenv import load_dotenv
from queries import queries
import threading
import random

load_dotenv()

class ConcurrentUser(threading.Thread):
    def __init__(self, user_id, workspace_url, database, auth_method, tenant_id=None, client_id=None, client_secret=None, sql_username=None, sql_password=None, query_tag=None, queries=None, results=None):
        threading.Thread.__init__(self)
        self.user_id = user_id
        self.workspace_url = workspace_url
        self.database = database
        self.auth_method = auth_method
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sql_username = sql_username
        self.sql_password = sql_password
        self.query_tag = query_tag
        self.queries = queries
        self.results = results

    def run(self):
        try:
            print(f"\nUser {self.user_id} started execution")
            server = self.workspace_url.replace('https://', '')
            if self.auth_method.lower() == "sql":
                connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={self.database};UID={self.sql_username};PWD={self.sql_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            else:
                connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={self.database};Authentication=ActiveDirectoryServicePrincipal;UID={self.client_id}@{self.tenant_id};PWD={self.client_secret};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            conn = pyodbc.connect(connection_string)
            for query_description, query in self.queries:
                try:
                    print(f"\nUser {self.user_id} running query {query_description}")
                    cursor = conn.cursor()
                    start_time = time.time() * 1000
                    cursor.execute(query)
                    rows = []
                    if cursor.description:
                        rows = cursor.fetchall()
                    end_time = time.time() * 1000
                    response_time = end_time - start_time
                    rows_produced = len(rows)
                    job_id = f"synapse_concurrent_user{self.user_id}_{int(time.time())}_{query_description.replace(' ', '_')}"
                    time.sleep(1)
                    try:
                        stats_queries = [
                            """SELECT TOP 1 total_elapsed_time FROM sys.dm_pdw_exec_requests WHERE CONVERT(VARCHAR(50), session_id) = CONVERT(VARCHAR(50), @@SPID) ORDER BY submit_time DESC""",
                            """SELECT TOP 1 total_elapsed_time FROM sys.dm_exec_requests WHERE CONVERT(VARCHAR(50), session_id) = CONVERT(VARCHAR(50), @@SPID) ORDER BY start_time DESC""",
                            """SELECT TOP 1 total_elapsed_time FROM sys.dm_pdw_exec_requests ORDER BY submit_time DESC"""
                        ]
                        official_time = None
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
                    except Exception as e:
                        print(f"Error getting query stats for user {self.user_id}: {e}")
                        official_time = None
                    try:
                        io_stats_query = """
                        SELECT 
                            SUM(reads) * 8 / 1024.0 AS mb_read
                        FROM 
                            sys.dm_exec_requests r
                        JOIN 
                            sys.dm_exec_sessions s ON r.session_id = s.session_id
                        WHERE 
                            s.session_id = @@SPID
                        """
                        cursor.execute(io_stats_query)
                        mb_stats = cursor.fetchone()
                        mb_scanned = round(float(mb_stats[0]), 2) if mb_stats and mb_stats[0] is not None else None
                    except Exception as e:
                        print(f"Error getting MB scanned for user {self.user_id}: {e}")
                        mb_scanned = None
                    if official_time is None:
                        official_time = ""
                    if mb_scanned is None:
                        mb_scanned = ""
                    result = {
                        'user_id': self.user_id,
                        'query_description': query_description,
                        'response_time_ms': round(response_time, 2),
                        'synapse_official_time_in_milli_sec': official_time,
                        'mb_scanned': mb_scanned,
                        'rows_produced': rows_produced,
                        'database': self.database,
                        'job_id': job_id,
                        'run_type': f'Concurrent-User-{self.user_id}',
                        'query_tag': self.query_tag
                    }
                    self.results.append(result)
                    cursor.close()
                    time.sleep(random.uniform(0.5, 2.0))
                except Exception as e:
                    print(f"Error in user {self.user_id} executing query {query_description}: {e}")
                    import traceback
                    traceback.print_exc()
            conn.close()
            print(f"\nUser {self.user_id} finished execution")
        except Exception as e:
            print(f"Error in user {self.user_id}: {e}")
            import traceback
            traceback.print_exc()

def run_concurrent_users(num_users):
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
        results = []
        users = []
        for i in range(num_users):
            user = ConcurrentUser(
                i+1, 
                workspace_url, 
                database, 
                auth_method,
                tenant_id, 
                client_id, 
                client_secret,
                sql_username,
                sql_password,
                query_tag, 
                queries, 
                results
            )
            users.append(user)
            user.start()
            time.sleep(0.5)
        for user in users:
            user.join()
        output_dir = 'AzureSynapseAnalytics'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'query_stats_concurrent_users.csv')
        file_exists = os.path.isfile(output_file)
        with open(output_file, mode='a', newline='') as file:
            fieldnames = [
                'user_id', 'query_description', 'response_time_ms', 
                'synapse_official_time_in_milli_sec', 'mb_scanned', 
                'rows_produced', 'database', 'job_id', 'run_type', 'query_tag'
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for result in results:
                final_result = result.copy()
                final_result['user_id'] = f"user-{result['user_id']}"
                writer.writerow(final_result)
        print(f"\nAll metrics saved to {output_file}")
    except Exception as e:
        print(f"Unexpected error in 'run_concurrent_users': {e}")
        import traceback
        traceback.print_exc()

def main():
    try:
        num_users_str = os.getenv("NUMBERS_OF_USERS", "5")
        num_users = int(num_users_str)
        print(f"Starting benchmark with {num_users} concurrent users")
        run_concurrent_users(num_users)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
