# Firebolt Query Performance Benchmarking Script

## Overview

This repo has one Python script to execute the SQL queries linearly and an environment file to plug in credentials.

| Sno | File Name   | Comment          |
|-----|------------|------------------|
| 1   | `main.py`  | Runs all SQL queries linearly |
| 2   | `.env`  | Takes in your credentials |



## Getting Started

To run the Firebolt benchmark, plug in your own credentials by setting the following environment variables:

```bash
# Firebolt credentials and configuration
FIREBOLT_ACCOUNT='account-1'
FIREBOLT_CLIENT_ID='abcd'
FIREBOLT_CLIENT_SECRET='abcdrJblEU6lkqP1Ulhx55V4ei9M8ZiIltA_yK6NbXTMsBo3rvyw1TG5PQVUUJQDq2Dj'
FIREBOLT_DATABASE='tpch_sf100'
FIREBOLT_SCHEMA='public'
FIREBOLT_ENGINE='my_engine'

```

## Setup

Install the required dependencies mentioned inside the Firebolt folder.

```bash
pip install -r requirements.txt

```
## Running the code 

Inside the Firebolt folder run

```bash
python main.py
```




Queries used for the Benchmark Report can be found [here](queries.py).


Benchmark report response time will be recorded in `query_stats.csv` file.


