# Data Warehouse Benchmarking Framework - Technical Overview

## Executive Summary

This document details the architecture, implementation, and technical decisions behind a comprehensive data warehouse benchmarking framework that evaluates 12 enterprise-grade analytical databases across AWS, Google Cloud, Microsoft Azure, and next-generation platforms.

The framework provides standardized performance comparison, cost analysis, and query optimization insights for organizations selecting data warehouse technology.

## System Architecture

### High-Level Design

The benchmarking framework follows a modular architecture with three distinct project scopes:

1. **Estuary Benchmark Report** - Comprehensive evaluation of 8 mature enterprise platforms
2. **Estuary Challenger Data Warehouses** - Analysis of 4 next-generation disruptors
3. **Estuary Big-5 Data Warehouses** - In-depth comparison of market leaders

**Core Components:**
- Database abstraction layer supporting 12+ platforms
- Performance metrics collection engine
- Query normalization and execution framework
- Cost correlation analysis system
- Automated result aggregation pipeline

### Infrastructure Design

**Deployment Environment:**
- Upcloud Ubuntu Server (Sweden datacenter)
- 2 Core CPU, 8 GB RAM, 10 GB storage
- Python 3.12 virtual environment
- tmux for background execution and session persistence

**Design Rationale:**
Intentionally resource-constrained to simulate realistic analytics workstation environments and stress-test query optimization capabilities of each platform.

## Technical Implementation

### 1. Multi-Platform Database Abstraction

**Challenge:** Each data warehouse has different connection protocols, authentication methods, and Python SDKs.

**Solution:** Implemented platform-specific connection managers with unified interface:

```
Snowflake: Native connector with OAuth2/password auth
Databricks: SQL connector with token authentication
BigQuery: google-cloud-bigquery SDK with service account JSON
Redshift: PyODBC with Amazon Redshift x64 driver
Azure Synapse: PyODBC with ODBC Driver 18 for SQL Server
ClickHouse: clickhouse-connect with TLS/SSL
Firebolt: firebolt-sdk with ClientCredentials OAuth2
SingleStore: singlestoredb native connector
MotherDuck: DuckDB with token-based cloud authentication
```

**Key Implementation Details:**

**BigQuery Service Account Authentication:**
```python
credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json',
    scopes=["https://www.googleapis.com/auth/bigquery"]
)
client = bigquery.Client(credentials=credentials, project=project_id)
```

**Snowflake Session-Level Cache Control:**
```python
cur.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
```

**ClickHouse Memory Management:**
```python
settings = {
    'max_memory_usage': 12_000_000_000,  # 12GB
    'max_bytes_before_external_group_by': 10_000_000_000,  # 10GB
    'join_use_nulls': 1,
    'join_algorithm': 'partial_merge'
}
client = clickhouse_connect.get_client(host=host, settings=settings)
```

**Firebolt Cache Invalidation:**
```python
cursor.execute("SET enable_result_cache = FALSE")
cursor.execute("SET enable_subresult_cache = FALSE")
```

### 2. Performance Metrics Collection

**Dual-Measurement Strategy:**

1. **Client-side timing** - Python-level execution measurement
2. **Database-native query history** - Platform-specific query metadata

**Platform-Specific Query History Integration:**

**Snowflake:**
```sql
SELECT
    TOTAL_ELAPSED_TIME,
    BYTES_SCANNED/1024/1024 AS MB_SCANNED,
    ROWS_PRODUCED,
    CREDITS_USED_CLOUD_SERVICES
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE QUERY_ID = ?
```

**BigQuery:**
```python
job = client.query(sql, job_config=job_config)
execution_time = (job.ended.timestamp() - job.started.timestamp()) * 1000
bytes_scanned = job.total_bytes_processed
```

**Redshift:**
```sql
SELECT
    execution_time,
    elapsed_time,
    queue_time,
    planning_time
FROM SYS_QUERY_HISTORY
WHERE query_id = {query_id}
```

**ClickHouse:**
```python
result = client.query(sql)
elapsed_ns = result.summary['elapsed_ns']
bytes_scanned = result.summary.get('read_bytes', 0)
```

**Metrics Captured:**
- Query execution time (milliseconds)
- Data scanned (bytes converted to MB)
- Rows produced (output cardinality)
- Credits/costs (platform-specific)
- Queue time (Redshift, Synapse)
- Planning time vs execution time

### 3. Query Complexity Progression

**TPC-H Benchmark Schema (100GB scale factor):**

Core tables: CUSTOMER, ORDERS, LINEITEM, PART, PARTSUPP, SUPPLIER, NATION, REGION

Semi-structured variants: jLINEITEM, jORDERS, jCUSTOMER (JSON format)

**Query Suite Design:**

**Query-1: Baseline Aggregation**
- Simple SUM, AVG aggregations
- Tests scan performance on large fact tables
- Establishes baseline for columnar compression efficiency

**Query-2: JSON Extraction**
- Nested JSON parsing
- Platform-specific functions (JSON_EXTRACT_PATH_TEXT, JSON_VALUE, etc.)
- Tests semi-structured data handling performance

**Query-3 through Query-5: Intermediate Complexity**
- Multi-table joins (2-3 tables)
- GROUP BY with HAVING clauses
- Date filtering and aggregations

**Query-6 through Query-11: Advanced Analytics**
- Window functions: LEAD, LAG, RANK, ROW_NUMBER, DENSE_RANK
- Complex CTEs with 3-5 levels
- String processing: REGEXP_REPLACE, SPLIT_PART, SUBSTR
- JSON extraction with aggregation
- 4-5 table joins with multiple predicates

**Query-F: Enterprise Supplier Analysis (18 CTEs)**

Demonstrates production-grade analytical query with:
- Multi-level aggregation pipeline
- Risk scoring calculations
- Delivery performance metrics
- Seasonal trend analysis
- Text sentiment analysis on comments
- Supplier ranking with multiple dimensions

**Technical Highlights:**
- 18 Common Table Expressions in dependency chain
- Window functions across multiple dimensions
- Complex CASE statements for scoring logic
- Text processing on VARCHAR columns
- Multiple join strategies (hash, merge, nested loop)

**Failure Analysis:**
Query-F intentionally stresses resource limits on some platforms (ClickHouse, MotherDuck) to identify scalability boundaries.

### 4. Cost Analysis Infrastructure

**Challenge:** Most cloud data warehouses have delayed billing (24-48 hours).

**Solution:** Query tagging and delayed cost retrieval.

**Implementation Pattern:**

1. Tag each query execution with unique identifier
2. Wait 24 hours for billing data to populate
3. Query cost/usage tables to correlate charges

**Snowflake Cost Correlation:**
```sql
SELECT
    SUM(CREDITS_USED_CLOUD_SERVICES) as total_credits
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE QUERY_TAG = 'benchmark_run_20250604'
  AND START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
```

**BigQuery Cost Estimation:**
```python
# Bytes billed correlates to cost ($5 per TB in US multi-region)
bytes_billed = job.total_bytes_billed
estimated_cost = (bytes_billed / 1_000_000_000_000) * 5.0
```

### 5. SQL Dialect Normalization

**Challenge:** Each platform has different SQL syntax for identical operations.

**Example - JSON Extraction:**

```sql
-- Snowflake
JSON_EXTRACT_PATH_TEXT(json_column, 'field')

-- BigQuery
JSON_VALUE(json_column, '$.field')

-- Redshift
JSON_EXTRACT_PATH_TEXT(json_column, 'field')

-- ClickHouse
JSONExtractString(json_column, 'field')

-- Databricks
json_column:field
```

**Solution:** Maintain platform-specific query templates with parameterized differences.

**Example - Window Function with NULL Handling:**

```sql
-- Most platforms
LEAD(order_date, 1) OVER (PARTITION BY customer_id ORDER BY order_date)

-- ClickHouse (requires explicit NULL handling)
LEAD(order_date, 1, NULL) OVER (PARTITION BY customer_id ORDER BY order_date)
```

### 6. Error Handling and Retry Logic

**Failure Scenarios:**
- Resource exhaustion (memory limits)
- Timeout on complex queries
- Connection drops during long-running queries
- Authentication token expiration

**Handling Strategy:**

```python
try:
    result = execute_query(sql, timeout=3600)
    metrics = collect_metrics(result)
except MemoryError:
    log_failure("Query exceeded memory limits")
    skip_to_next_query()
except TimeoutError:
    log_failure("Query exceeded 1-hour timeout")
    skip_to_next_query()
except ConnectionError:
    reconnect_with_backoff()
    retry_query()
```

**Graceful Degradation:**
- Queries that fail on one platform are logged but don't halt entire benchmark
- Results files include "FAILED" markers for failed queries
- Post-processing identifies platform limitations

## Architectural Decisions and Trade-offs

### Decision 1: Client-Side vs Server-Side Timing

**Choice:** Dual measurement (both client and server)

**Rationale:**
- Client-side: Includes network latency, real-world user experience
- Server-side: Pure query execution, eliminates network variance

**Trade-off:** Additional complexity in query history retrieval, but provides comprehensive performance picture.

### Decision 2: Cache Invalidation Strategy

**Choice:** Disable all caching mechanisms at session/query level

**Rationale:**
- Fair comparison requires cold cache performance
- Production workloads often hit uncached data
- Identifies true query optimization capabilities

**Implementation Challenges:**
- Each platform has different cache control mechanisms
- Some platforms (MotherDuck) don't expose cache control
- Required platform-specific research and testing

### Decision 3: 100GB Dataset Size

**Choice:** TPC-H Scale Factor 100 (100GB raw data)

**Rationale:**
- Large enough to stress I/O and network
- Small enough to complete in reasonable time
- Industry-standard benchmark for comparability

**Trade-off:**
- Some queries run very long (10+ minutes)
- Smaller dataset wouldn't expose scalability issues
- Larger dataset would be cost-prohibitive for multiple runs

### Decision 4: Resource-Constrained Test Environment

**Choice:** 2-core, 8GB RAM virtual machine

**Rationale:**
- Simulates analytics workstation environment
- Tests platforms' ability to offload computation
- Cloud data warehouses should not depend on client resources

**Result:** Validates that all platforms successfully offload computation (client CPU/RAM not bottleneck).

### Decision 5: Python as Implementation Language

**Choice:** Python 3.12 with platform-specific SDKs

**Rationale:**
- Native SDKs available for all 12 platforms
- Pandas integration for result processing
- Rich ecosystem for data manipulation
- Industry standard for data engineering

**Trade-off:**
- Some platforms have faster native CLI tools
- Python GIL can limit concurrency (addressed with multiprocessing in future versions)

## Performance Optimization Techniques

### 1. ClickHouse Memory Management

**Problem:** Complex queries with large intermediate results exceeded default memory limits.

**Solution:**
```python
settings = {
    'max_memory_usage': 12_000_000_000,
    'max_bytes_before_external_group_by': 10_000_000_000,
    'join_algorithm': 'partial_merge'
}
```

**Impact:**
- Enabled external sorting for group-by operations
- Allowed queries to spill to disk when RAM exceeded
- Partial merge joins reduced memory footprint

### 2. Snowflake Warehouse Sizing

**Strategy:** Test multiple warehouse sizes (X-Small through X-Large)

**Findings:**
- Larger warehouses reduce execution time linearly up to a point
- Diminishing returns beyond Large for most queries
- Cost increases faster than performance improvement

**Recommendation:** Medium warehouse provides best cost/performance for TPC-H workload.

### 3. BigQuery Slot Optimization

**Observation:** BigQuery auto-scales slots based on query complexity

**Analysis:**
- Simple queries: 50-100 slots
- Complex queries: 200-500 slots
- Massive parallelization on large scans

**Insight:** BigQuery's slot allocation algorithm is highly efficient for ad-hoc analytics.

### 4. Redshift Distribution Keys

**Testing Methodology:**
- Tested queries on tables with different distribution strategies
- EVEN distribution: Baseline
- KEY distribution on join columns: 2-3x faster joins
- ALL distribution for dimension tables: Eliminated network shuffle

**Recommendation:** Proper distribution key selection critical for Redshift performance.

## Technical Challenges and Solutions

### Challenge 1: Firebolt Authentication

**Problem:** Firebolt SDK changed from username/password to OAuth2 ClientCredentials flow.

**Solution:**
```python
from firebolt.client import ClientCredentials
from firebolt.db import connect

auth = ClientCredentials(client_id=client_id, client_secret=client_secret)
connection = connect(
    auth=auth,
    database=database,
    engine_name=engine_name,
    account_name=account_name
)
```

**Lesson:** Cloud data warehouse authentication patterns are evolving toward OAuth2/OIDC standards.

### Challenge 2: Azure Synapse ODBC Configuration

**Problem:** Multiple ODBC driver versions with incompatible connection strings.

**Solution:**
```python
# ODBC Driver 18 requires explicit trust server certificate
connection_string = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server={server};"
    f"Database={database};"
    f"Uid={username};"
    f"Pwd={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)
```

**Lesson:** ODBC connections require platform-specific SSL/TLS configuration.

### Challenge 3: MotherDuck Token Management

**Problem:** MotherDuck uses shared DuckDB client with token-based cloud connection.

**Solution:**
```python
import duckdb

# Token stored in environment variable
con = duckdb.connect(f"motherduck:{database}?motherduck_token={token}")
```

**Lesson:** Serverless platforms favor token-based authentication over traditional credentials.

### Challenge 4: Query Result Size Limits

**Problem:** Some queries return millions of rows, exceeding Python memory.

**Solution:**
- Fetch results in batches using cursor.fetchmany(size=10000)
- Write results directly to CSV without loading into memory
- For metrics collection, only retrieve summary statistics

**Implementation:**
```python
cursor.execute(query)
with open('results.csv', 'w') as f:
    while True:
        rows = cursor.fetchmany(10000)
        if not rows:
            break
        write_to_csv(f, rows)
```

## Multi-Cloud Platform Expertise

### AWS Integration

**Services Used:**
- Redshift (data warehouse)
- S3 (data loading, Redshift Spectrum external tables)
- IAM (credential management)

**Technical Implementation:**
- PyODBC connection with Amazon Redshift x64 driver
- Query history via SYS_QUERY_HISTORY system view
- WLM (Workload Management) queue analysis

**Key Insights:**
- Redshift requires distribution and sort key optimization
- VACUUM and ANALYZE maintenance critical for performance
- Redshift Spectrum allows querying S3 data without loading

### Google Cloud Platform Integration

**Services Used:**
- BigQuery (data warehouse)
- Cloud Storage (data loading)
- Service Accounts (authentication)

**Technical Implementation:**
```python
from google.cloud import bigquery
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json'
)
client = bigquery.Client(credentials=credentials, project=project_id)
```

**Key Insights:**
- BigQuery's slot-based pricing model differs from traditional compute pricing
- Automatic query optimization with no manual tuning required
- Columnar storage with automatic partitioning and clustering recommendations

### Microsoft Azure Integration

**Services Used:**
- Azure Synapse Analytics (data warehouse)
- Azure Data Lake Storage (data loading)
- Azure Active Directory (authentication)

**Technical Implementation:**
- ODBC Driver 18 for SQL Server
- Distributed query execution across compute nodes
- Dedicated SQL pools with DWU scaling

**Key Insights:**
- Synapse requires explicit table distribution strategy
- Statistics management critical for query optimization
- Integration with Azure ecosystem (ADF, Databricks, Power BI)

### Multi-Cloud Platforms

**Snowflake:**
- Runs on AWS, GCP, Azure (architecture-agnostic)
- Separate compute and storage pricing
- Automatic scaling and optimization

**Databricks:**
- Lakehouse architecture on Delta Lake
- Runs on AWS, GCP, Azure
- Unified batch and streaming processing

## Key Technical Achievements

### 1. Cross-Platform SQL Normalization
Developed query templates supporting 12 different SQL dialects with platform-specific optimizations.

### 2. Automated Performance Profiling
Built metrics collection engine that extracts execution time, bytes scanned, rows produced, and costs from each platform's native query history.

### 3. Cost-Performance Analysis Framework
Implemented 24-hour delayed cost correlation using query tagging and billing API integration.

### 4. Scalability Testing Infrastructure
Designed resource-constrained environment to validate cloud data warehouse offloading capabilities.

### 5. Production-Grade Error Handling
Implemented graceful degradation with retry logic, timeout handling, and comprehensive logging.

## Interview Talking Points

### On Architecture Decisions

"I designed a modular benchmarking framework with platform-specific adapters, allowing me to test 12 different data warehouses with minimal code duplication. The key challenge was abstracting connection management, authentication, and query history retrieval across vastly different APIs."

### On Performance Engineering

"I implemented dual-measurement performance tracking—client-side timing for real-world latency and server-side query history for pure execution time. This revealed interesting insights, like network latency being negligible for cloud data warehouses but significant for on-premise deployments."

### On Query Optimization

"I wrote complex analytical queries with up to 18 CTEs, testing window functions, JSON extraction, and multi-table joins across platforms. Query-F, our enterprise supplier analysis query, exposed scalability limits on some platforms while others handled it efficiently through automatic query optimization."

### On Multi-Cloud Expertise

"I've integrated with AWS Redshift, Google BigQuery, Azure Synapse, and multi-cloud platforms like Snowflake and Databricks. Each has different authentication patterns—service accounts for GCP, IAM for AWS, OAuth2 for modern platforms—and I've implemented secure credential management for all of them."

### On Cost Analysis

"I built cost correlation infrastructure using query tagging and 24-hour delayed billing retrieval. For example, Snowflake's QUERY_HISTORY table provides credits consumed, while BigQuery estimates cost based on bytes scanned. This helps organizations understand the true TCO of different platforms."

### On Handling Complexity

"When testing ClickHouse, I encountered memory limit errors on complex queries. I implemented custom memory management settings, enabling external sorting and partial merge joins. This allowed queries to complete by spilling to disk when RAM was exceeded—a production-relevant optimization technique."

### On Error Handling

"I designed the framework to gracefully handle failures—timeouts, memory errors, connection drops—logging failures without halting the entire benchmark. This is critical because some platforms have hard limits that specific queries will exceed."

## Results and Insights

### Performance Comparison (Sample Data)

Query-1 (Simple Aggregation - 100GB scan):
- ClickHouse: 11-17 seconds
- Snowflake: 8-12 seconds (Medium warehouse)
- BigQuery: 6-9 seconds (auto-scaling)
- Redshift: 15-25 seconds

Query-F (Complex 18-CTE Enterprise Query):
- Snowflake: 180 seconds
- BigQuery: 145 seconds
- Databricks: 220 seconds
- ClickHouse: Failed (resource limits)
- Redshift: 290 seconds

### Platform Strengths Identified

**BigQuery:**
- Best for ad-hoc analytics with unpredictable workloads
- Automatic optimization eliminates tuning overhead
- Serverless model simplifies infrastructure

**Snowflake:**
- Excellent balance of performance and ease of use
- Separation of compute/storage enables flexible scaling
- Strong support for semi-structured data

**ClickHouse:**
- Fastest for simple aggregations on large datasets
- Requires manual optimization for complex queries
- Ideal for real-time analytics dashboards

**Databricks:**
- Best for mixed batch/streaming workloads
- Strong integration with ML workflows
- Delta Lake provides ACID transactions

**Redshift:**
- Cost-effective for predictable workloads
- Deep AWS integration
- Requires tuning (distribution keys, sort keys)

## Lessons Learned

### Technical Lessons

1. **Cache invalidation is platform-specific** - Required research for each platform
2. **Query history APIs vary widely** - Some provide microsecond precision, others only seconds
3. **Authentication patterns are evolving** - Industry moving toward OAuth2/OIDC
4. **Resource limits differ dramatically** - Some platforms handle complex queries easily, others fail
5. **Cost models are complex** - Per-query pricing, slot-based, compute-hour-based all require different analysis

### Engineering Lessons

1. **Start simple, add complexity incrementally** - Basic queries first, then advanced analytics
2. **Log everything** - Comprehensive logging critical for diagnosing failures
3. **Expect failures** - Resource limits, timeouts, connection drops are inevitable
4. **Automate metric collection** - Manual performance tracking doesn't scale
5. **Document platform quirks** - Each database has unique behaviors worth documenting

## Future Enhancements

### Planned Improvements

1. **Concurrent User Simulation**
   - Multi-threaded query execution
   - Stress test with 10-100 concurrent users
   - Measure queue times and resource contention

2. **Streaming Workload Testing**
   - Continuous data ingestion during queries
   - Test real-time analytics capabilities
   - Measure data freshness vs query performance

3. **Cost Optimization Recommendations**
   - Automated cost/performance Pareto frontier analysis
   - Recommend optimal warehouse size per workload
   - Query cost prediction models

4. **Extended Query Suite**
   - TPC-DS benchmark queries (99 queries)
   - Custom business intelligence workload simulations
   - Machine learning feature engineering queries

5. **Automated Reporting Dashboard**
   - Real-time performance visualization
   - Cost trend analysis
   - Platform comparison scorecards

## Technical Stack Summary

**Languages:**
- Python 3.12

**Database Connectors:**
- snowflake-connector-python 3.0.3
- databricks-sql-connector
- google-cloud-bigquery 3.0.0+
- clickhouse-connect
- firebolt-sdk
- singlestoredb
- duckdb (MotherDuck)
- pyodbc (Redshift, Azure Synapse)

**Data Processing:**
- pandas 2.0.3-2.1
- CSV for result persistence

**Infrastructure:**
- python-dotenv (environment management)
- certifi (SSL certificates)
- tmux (session management)

**Cloud Platforms:**
- AWS (Redshift, S3, IAM)
- Google Cloud (BigQuery, Cloud Storage, Service Accounts)
- Microsoft Azure (Synapse, ADLS, AAD)

**Data Warehouses Tested:**
1. Snowflake
2. Databricks
3. BigQuery
4. Redshift
5. Azure Synapse
6. ClickHouse
7. SingleStore
8. MotherDuck
9. Firebolt
10. Microsoft Fabric (future)

## Conclusion

This benchmarking framework represents production-grade data engineering work, demonstrating expertise in:

- Multi-cloud data warehouse architecture
- Complex SQL query optimization
- Performance engineering at scale
- Cost analysis and TCO modeling
- Cross-platform integration
- Cloud-native authentication patterns
- Error handling and system reliability

The framework provides actionable insights for enterprise technology selection while showcasing advanced data engineering capabilities applicable to senior-level roles in data platform engineering, analytics engineering, and data warehouse architecture.
