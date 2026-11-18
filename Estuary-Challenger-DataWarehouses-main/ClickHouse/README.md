# ClickHouse Query Performance Benchmarking Script

## Overview

This repository contains a Python script to execute SQL queries sequentially against a ClickHouse database and an environment file for credentials and configuration.

| Sno | File Name   | Comment                          |
|-----|------------|----------------------------------|
| 1   | `main.py`  | Runs all SQL queries sequentially |
| 2   | `.env`     | Stores your ClickHouse credentials and config |

## Getting Started

To run the ClickHouse benchmark, set your credentials and configuration in the environment variables:

```bash
# ClickHouse credentials
HOST=your_clickhouse_host -> looks like 'abcd.ap-south-1.aws.clickhouse.cloud'
PORT=your_clickhouse_port -> Ideally 8443
USER=your_username
PASSWORD=your_password

# ClickHouse configuration
DATABASE=your_database -> looks like 'TPCH_SF100'
WAREHOUSE='Replica 2 max 8' -> Use it as a tag

```

## Setup

Install the required dependencies listed in the ClickHouse folder:

```bash
pip install -r requirements.txt
```

## Running the Code

Inside the ClickHouse folder, run:

```bash
python main.py
```

Queries used for the benchmark report can be found in [queries.py](queries.py).

Benchmark report response times will be recorded in the `query_stats.csv` file.


