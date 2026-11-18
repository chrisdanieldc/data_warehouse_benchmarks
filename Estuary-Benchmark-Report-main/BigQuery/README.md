# BigQuery Performance Benchmarking Tool

This tool is designed to run SQL queries against BigQuery and collect performance metrics. It provides similar functionality to the Snowflake benchmarking tool, including:

1. Running queries sequentially
2. Running queries in parallel
3. Simulating concurrent users

## Setup

1. **Environment Setup**:
   There's a helper script to set up your environment properly:
   ```
   python setup_env.py
   ```
   This will check if your environment is correctly set up and install only the necessary dependencies.

   If you prefer to install dependencies manually:
   ```
   pip install google-cloud-bigquery python-dotenv
   ```

2. Create a `.env` file based on the `.env.template`:
   ```
   cp .env.template .env
   ```

3. Update the `.env` file with your BigQuery credentials:
   - Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of your service account key JSON file
   - Set `BIGQUERY_PROJECT_ID` to your Google Cloud project ID
   - Set `BIGQUERY_DATASET` to the dataset you want to query
   - Set `BIGQUERY_LOCATION` to your dataset's location (e.g., "US")
   - Set `QUERY_TAG` to tag your benchmark queries (e.g., "benchmark_test")
   - Set `NUMBERS_OF_USERS` for concurrent user simulation

4. Add your queries to `queries.py`

## Usage

### Run Queries Sequentially
```
python main.py
```

### Run Queries in Parallel
```
python run_sql_in_parallel.py
```

### Run Concurrent User Simulation
```
python concurrent_user_trigger.py
```

## Output

Results are saved to CSV files:
- `query_stats.csv` for sequential and parallel runs
- `query_stats_concurrent_users.csv` for concurrent user simulation

## Troubleshooting

If you encounter dependency issues, try:

1. Run the setup helper: `python setup_env.py`
2. If that doesn't work, try manually uninstalling problematic packages:
   ```
   pip uninstall -y numpy pandas google-cloud-bigquery
   pip install google-cloud-bigquery python-dotenv
   ```
3. Consider creating a fresh virtual environment:
   ```
   python -m venv bq_benchmark_env
   # On Windows
   bq_benchmark_env\Scripts\activate
   # On Linux/Mac
   source bq_benchmark_env/bin/activate
   pip install google-cloud-bigquery python-dotenv
   ``` 