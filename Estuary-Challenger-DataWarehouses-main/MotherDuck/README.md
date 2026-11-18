# MotherDuck Query Performance Benchmarking Script

## Overview

This repo has one Python script to execute SQL queries linearly and an environment file to plug in credentials.

| Sno | File Name   | Comment          |
|-----|------------|------------------|
| 1   | `main.py`  | Runs all SQL queries linearly |
| 2   | `.env`  | Takes in your credentials |



## Getting Started

To run the MotherDuck benchmark, plug in your own credentials by setting the following environment variables:

```bash
# MotherDuck credentials and configuration
MOTHERDUCK_TOKEN="eyJhbGciOiJIU"
DATABASE='tpch_sf100'
SCHEMA='main'
WAREHOUSE='standard'
REPLICA='2'

```

## Setup

Install the required dependencies mentioned inside the MotherDuck folder.

```bash
pip install -r requirements.txt
```
## Running the code 

Inside the MotherDuck folder run

```bash
python main.py
```




Queries used for the Benchmark Report can be found [here](queries.py).


Benchmark report response time will be recorded in `query_stats.csv` file.


