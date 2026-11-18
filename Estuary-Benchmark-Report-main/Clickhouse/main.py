import clickhouse_connect
from dotenv import load_dotenv
import os
from queries import queries
import time
import csv

# Load environment variables from .env file
load_dotenv()

def run_query_and_save_metrics(client, query_description, query, warehouse, database):
    try:
        print(f"\nExecuting: {query_description}\n")

        settings = {
            'max_memory_usage': 12000000000,
            'max_bytes_before_external_group_by': 10000000000,
            'join_use_nulls': 1,
            'join_algorithm': 'partial_merge'
        }

        result = client.query(query,settings=settings)
        elapsed_ns = int(result.summary['elapsed_ns'])
        response_time_ms = elapsed_ns / 1_000_000

        # Prepare data to append
        query_metrics = {
            'query_description': query_description,
            'response_time_ms': response_time_ms,
            'warehouse': warehouse,
            'run_type': 'Linear',
            'query_tag': result.summary['query_id']
        }

    except Exception as e:
        print(f"Error executing query '{query_description}': {e}")
        # In case of error, set response_time_ms to -1
        query_metrics = {
            'query_description': query_description,
            'response_time_ms': '-1',
            'warehouse': warehouse,
            'run_type': 'Linear',
            'query_tag': 'N/A'
        }

    finally:
        output_file = 'query_stats.csv'

        # Check if the file exists
        file_exists = os.path.isfile(output_file)

        # Open the CSV file in append mode and write the data
        with open(output_file, mode='a', newline='') as file:
            fieldnames = ['query_description', 'response_time_ms', 'warehouse', 'run_type', 'query_tag']

            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # If the file doesn't exist, write the header row
            if not file_exists:
                writer.writeheader()

            # Write the query metrics to the CSV
            writer.writerow(query_metrics)







def main():
    # Retrieve values from .env
    database = os.getenv("DATABASE")
    host = os.getenv("HOST")
    port = os.getenv("PORT")
    user = os.getenv("CLICKHOUSE_USER")
    password = os.getenv("PASSWORD")
    warehouse = os.getenv("WAREHOUSE")
    
    # Establish connection
    client = clickhouse_connect.get_client(
            host=host,
            port=int(port),
            user=user,
            password=password,
            secure=True
        )

    try:

        for query_description, query in queries:
            run_query_and_save_metrics(client,query_description,query,warehouse,database)
            
            
    except Exception as e:
        print(f"\nError executing query: {e}\n")
    
    
    finally:
        # Close the connection
        client.close()
        print("Connection closed.")






if __name__ == "__main__":
    main()