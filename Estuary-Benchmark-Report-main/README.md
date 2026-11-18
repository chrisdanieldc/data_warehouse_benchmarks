# **Estuary Benchmark Report**  

Our goal with this benchmark report is to equip you with the technical tools and insights needed to run your own tests and determine which data warehouse best fits your specific needs.<br><br>
We’ve designed this repo so that even semi-technical users can easily run the benchmarks and draw meaningful insights.<br><br>
If you have any questions about running the benchmark, don’t hesitate to get in touch. We’re here to help.<br><br>

This repository contains Python  code to run and measure SQL queries on the following data warehouses:  

- [**Snowflake**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Snowflake)  
- [**Databricks**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Databricks)
- [**MotherDuck**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Motherduck)
- [**ClickHouse**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Clickhouse)
- [**SingleStore**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Singlestore)
- [**Big Query**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/BigQuery)
- [**Azure Synapse**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Azure)
- [**Redshift**](https://github.com/cdevairakkam7/Estuary-Benchmark-Report/tree/main/Redshift)


For instructions on running Python  code for a specific data warehouse, refer to its respective `README` file.

## **Notes:**

- To ensure accurate performance measurement, the code bypasses cached results from previous queries, guaranteeing a fresh execution each time.
- We initially attempted to extract query execution times from system query history logs, where such metadata was programmatically accessible.
- For data warehouses that did not support programmatic access to query metadata, we measured elapsed time using Python logic.


