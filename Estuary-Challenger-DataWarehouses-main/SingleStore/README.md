# SingleStore Query Performance Benchmarking Script

## Overview

This repo has one Python script to execute the SQL queries linearly and an environment file to plug in credentials.

| Sno | File Name   | Comment          |
|-----|------------|------------------|
| 1   | `main.py`  | Runs all SQL queries linearly |
| 2   | `.env`  | Takes in your credentials |



## Getting Started

To run the SingleStore benchmark, plug in your own credentials by setting the following environment variables:

```bash
# SingleStore credentials and configuration
DATABASE='db_tpch_sf100'
HOST='abcd-shared-dml.aws-virginia-6.svc.singlestore.com'
PORT='3333'
SINGLE_STORE_USER='tpch_user'
PASSWORD='your_password_here'
WAREHOUSE='wh_tpch_sf100'


```

## Setup

Install the required dependencies mentioned inside the SingleStore folder.

```bash
pip install -r requirements.txt
```
## Running the code 

Inside the SingleStore folder run

```bash
python main.py
```




Queries used for the Benchmark Report can be found [here](queries.py).


Benchmark report response time will be recorded in `query_stats.csv` file.


