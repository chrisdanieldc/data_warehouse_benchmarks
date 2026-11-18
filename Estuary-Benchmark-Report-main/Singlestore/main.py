import singlestoredb as s2
from dotenv import load_dotenv
import os
from queries import queries
import time
import csv


def run_query_and_save_metrics(cur, query_description, query,warehouse):
    
    print(f"\nExecuting: {query_description}\n")
   
    # Record query start time
    start_time = time.time()

    cur.execute(query)
    result = cur.fetchall()
    
    # Record query end time
    end_time = time.time()
    
    # Converting to milliseconds
    start_time = start_time * 1000
    end_time = end_time * 1000
    response_time = end_time - start_time
    

    # Prepare data to append
    query_metrics = {
        'query_description': query_description,
        'response_time_ms': response_time,
        'warehouse':warehouse,
        'run_type':'Linear'
    }

    output_file = 'Singlestore/query_stats.csv'

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
    host = os.getenv("HOST")
    port = os.getenv("PORT")
    single_store_user = os.getenv("SINGLE_STORE_USER")
    password = os.getenv("PASSWORD")
    database = os.getenv("DATABASE")
    warehouse = os.getenv("WAREHOUSE")

    


    # Establish connection

    try:

        conn = s2.connect(
            host=host,
            port=int(port),
            user=single_store_user,
            password=password,
            database=database
        )
        print("Connection established successfully.")
        cur = conn.cursor()
        
        for query_description, query in queries:

            run_query_and_save_metrics(cur,query_description,query,warehouse)
        
        

    except Exception as e:
        print(f"\nError executing query: {e}\n")
    
    
    finally:
        conn.close()
        print("Connection closed.")
    







if __name__ == "__main__":
    main()