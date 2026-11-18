try:
    from google.cloud import bigquery
except ImportError as e:
    print(f"Error importing bigquery: {e}")
    print("Try reinstalling with: pip install google-cloud-bigquery==3.11.4 numpy==1.24.3")
    raise

import time
import csv
import os
from dotenv import load_dotenv
from queries import queries
from concurrent.futures import ThreadPoolExecutor
import certifi

load_dotenv()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()
def run_query_and_save_metrics(query_description, query, project_id, dataset, query_tag):
    try:
        # Create a new client for each thread
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        client = bigquery.Client.from_service_account_json(
            credentials_path,
            project=project_id
        )
        
        print(f"\n\nRunning query: {query_description}\n")

       

        # Configure the job
        job_config = bigquery.QueryJobConfig(
            use_query_cache=False,  # Don't use cached results
            labels={"query_tag": query_tag.replace("-", "_").lower()}  # BigQuery labels can't contain dashes
        )
         # Record query start time
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
            'query_description': query_description,
            'response_time_ms': response_time,
            'bigquery_official_time_in_milli_sec': job_duration,
            'mb_scanned': round(mb_scanned, 4),
            'rows_produced': rows_produced,
            'project_id': project_id,
            'job_id': job_id,
            'run_type': 'Parallel',
            'query_tag': query_tag
        }

        output_file = 'query_stats_run_in_parallel.csv'
        file_exists = os.path.isfile(output_file)
        
        with open(output_file, mode='a', newline='') as file:
            fieldnames = ['query_description', 'response_time_ms', 'bigquery_official_time_in_milli_sec',
                          'mb_scanned', 'rows_produced', 'project_id', 'job_id', 'run_type', 'query_tag']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(query_metrics)

        print(f"Metrics saved for query: {query_description}")

    except Exception as e:
        print(f"Error in 'run_query_and_save_metrics' for query {query_description}: {e}")


def main():
    try:
        project_id = os.getenv("BIGQUERY_PROJECT_ID")
        dataset = os.getenv("BIGQUERY_DATASET")
        query_tag = os.getenv("QUERY_TAG")

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            # Submit all queries to the thread pool
            executor.map(lambda q: run_query_and_save_metrics(q[0], q[1], project_id, dataset, query_tag), queries)
    
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 