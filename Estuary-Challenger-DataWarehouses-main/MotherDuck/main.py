import duckdb
from dotenv import load_dotenv
import os
from queries import queries
import time
import csv

# Load environment variables from .env file
load_dotenv()

def run_query_and_save_metrics(con, query_description, query, database, warehouse, replica):
    
    try:
        print(f"\nExecuting: {query_description}\n")

        start_time = time.time()

        result = con.execute(query).fetchdf()

        # Record query end time
        end_time = time.time()

        # Converting to milliseconds
        start_time = start_time * 1000
        end_time = end_time * 1000
        response_time_ms = end_time - start_time

        run_type = f'{warehouse} - {replica}'
        # Prepare data to append
        query_metrics = {
            'query_description': query_description,
            'response_time_ms': response_time_ms,
            'warehouse': warehouse,
            'run_type': run_type
        }

        output_file = 'query_stats.csv'

        # Check if the file exists
        file_exists = os.path.isfile(output_file)

        # Open the CSV file in append mode and write the data
        with open(output_file, mode='a', newline='') as file:
            fieldnames = ['query_description', 'response_time_ms', 'warehouse', 'run_type']

            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # If the file doesn't exist, write the header row
            if not file_exists:
                writer.writeheader()

            # Write the query metrics to the CSV
            writer.writerow(query_metrics)

    except Exception as e:
        print(f"Error while executing query '{query_description}': {e}")

        run_type = f'{warehouse} - {replica}'
        query_metrics = {
            'query_description': query_description,
            'response_time_ms': '-1',
            'warehouse': warehouse,
            'run_type': run_type
        }

        output_file = 'query_stats.csv'

        # Check if the file exists
        file_exists = os.path.isfile(output_file)

        # Open the CSV file in append mode and write the data
        with open(output_file, mode='a', newline='') as file:
            fieldnames = ['query_description', 'response_time_ms', 'warehouse', 'run_type']

            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # If the file doesn't exist, write the header row
            if not file_exists:
                writer.writeheader()

            # Write the query metrics to the CSV
            writer.writerow(query_metrics)








def main():
    # Retrieve values from .env
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    database = os.getenv("DATABASE")
    schema = os.getenv("SCHEMA")
    warehouse = os.getenv("WAREHOUSE")
    replica = os.getenv("REPLICA")
    
    # Establish connection
    con = duckdb.connect("md:?motherduck_token=" + motherduck_token)

    try:

        for query_description, query in queries:
            run_query_and_save_metrics(con,query_description,query,database,warehouse,replica)
            
            
    except Exception as e:
        print(f"\nError executing query: {e}\n")
    
    
    finally:
        # Close the connection
        con.close()
        print("Connection closed.")






if __name__ == "__main__":
    main()