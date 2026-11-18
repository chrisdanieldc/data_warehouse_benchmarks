# Redshift Query Performance Benchmarking Tool

## Overview

This tool provides a comprehensive suite of scripts for testing and measuring Amazon Redshift query performance. The repository contains three main Python scripts designed to run SQL queries against a Redshift database and collect detailed performance metrics.

| Script | Description |
|--------|-------------|
| `main.py` | Executes all SQL queries sequentially |
| `run_sql_in_parallel.py` | Executes all SQL queries concurrently |
| `concurrent_user_trigger.py` | Simulates multiple users executing queries concurrently |

## Features

- Sequential and parallel query execution
- Multi-user simulation
- Detailed performance metrics collection
- Query caching control
- Redshift-native execution time measurements
- CSV output for easy analysis

## Requirements

- Python 3.8+
- Amazon Redshift cluster with appropriate permissions
- Redshift ODBC driver installed

## Installation

1. Clone this repository
2. Install required packages: `pip install -r requirements.txt`
3. Copy `.env.template` to `.env` and fill in your Redshift credentials

## Configuration

Update the `.env` file with your Redshift connection details:
```
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password
REDSHIFT_HOST=your-cluster.region.redshift.amazonaws.com
REDSHIFT_DATABASE=your_database
REDSHIFT_PORT=5439
NUMBERS_OF_USERS=5
QUERY_TAG=redshift_benchmark

```

## Usage

### Running Queries Sequentially

```bash
python main.py
```

### Running Queries in Parallel

```bash
python run_sql_in_parallel.py
```

### Simulating Multiple Users

```bash
python concurrent_user_trigger.py
```

## Output

- Results from `main.py` and `run_sql_in_parallel.py` are stored in `query_stats.csv`
- Results from `concurrent_user_trigger.py` are stored in `query_stats_concurrent_users.csv`

The metrics collected include:
- Query description
- Response time (ms)
- Redshift official execution time (ms)
- Number of rows produced
- Run type (Linear/Parallel/concurrent_users)
- Query tag
- Database name
- Query ID

## Customizing Queries

Edit the `queries.py` file to add or modify the SQL queries you want to benchmark.
