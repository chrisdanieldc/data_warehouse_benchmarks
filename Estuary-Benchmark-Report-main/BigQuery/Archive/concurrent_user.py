try:
    from google.cloud import bigquery
except ImportError as e:
    print(f"Error importing bigquery: {e}")
    print("Try reinstalling with: pip install google-cloud-bigquery==3.11.4 numpy==1.24.3")
    raise

import time
import csv
import os
import sys
from dotenv import load_dotenv
from queries import queries
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import certifi
load_dotenv()

os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()
# Lock for thread-safe CSV writing
csv_lock = Lock()

def run_query_and_save_metrics(query_description, query, project_id, dataset, user_id, query_tag):
    try:
        # Create a new client for each thread
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        client = bigquery.Client.from_service_account_json(
            credentials_path,
            project=project_id
        )
        
        print(f"Running query: {query_description} for {user_id}")


        # Configure the job
        job_config = bigquery.QueryJobConfig(
            use_query_cache=False,  # Don't use cached results
            labels={
                "query_tag": query_tag.replace("-", "_").lower(),  # BigQuery labels can't contain dashes
                "user_id": user_id.replace("-", "_").lower()
            }
        )
        start_time = time.time() * 1000  # Convert to milliseconds
        # Execute the query
        query_job = client.query(query, job_config=job_config)
        result = query_job.result()  # Wait for the query to complete

        # Record query end time
        end_time = time.time() * 1000  # Convert to milliseconds
        response_time = end_time - start_time

        job_id = query_job.job_id

        # Get query performance metrics
        job = client.get_job(job_id)
        
        # Extract relevant metrics
        bytes_scanned = job.total_bytes_processed
        mb_scanned = bytes_scanned / 1024 / 1024 if bytes_scanned else 0
        rows_produced = job.total_rows if hasattr(job, 'total_rows') else 0
        job_duration = job.ended.timestamp() * 1000 - job.started.timestamp() * 1000 if job.ended and job.started else None

        query_metrics = {
            'user_id': user_id,  # Add user_id to metrics
            'query_description': query_description,
            'response_time_ms': response_time,
            'bigquery_official_time_in_milli_sec': job_duration,
            'mb_scanned': round(mb_scanned, 4),
            'rows_produced': rows_produced,
            'project_id': project_id,
            'job_id': job_id,
            'run_type': 'concurrent_users',
            'query_tag': query_tag
        }

        output_file = 'query_stats_concurrent_users.csv'
        with csv_lock:
            file_exists = os.path.isfile(output_file)
            with open(output_file, mode='a', newline='') as file:
                fieldnames = ['user_id', 'query_description', 'response_time_ms', 'bigquery_official_time_in_milli_sec',
                              'mb_scanned', 'rows_produced', 'project_id', 'job_id', 'run_type', 'query_tag']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(query_metrics)

        print(f"Metrics saved for: {query_description} ({user_id})")

    except Exception as e:
        print(f"Error for query {query_description} ({user_id}): {e}")


def main():
    try:
        # Check for user_id argument
        if len(sys.argv) < 2:
            print("Error: Please provide a user_id as an argument (e.g., user-1)")
            sys.exit(1)
        user_id = sys.argv[1]

        project_id = os.getenv("BIGQUERY_PROJECT_ID")
        dataset = os.getenv("BIGQUERY_DATASET")
        query_tag = os.getenv("QUERY_TAG")

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            executor.map(lambda q: run_query_and_save_metrics(q[0], q[1], project_id, dataset, user_id, query_tag), queries)

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 