# **Estuary’s 2025 Benchmark Report on Challenger Data Warehouses**  

The data warehouse market is currently dominated by a few mature players who have reached saturation. These robust, battle-tested platforms effectively meet the complex needs of large enterprises, especially Fortune 500 companies, who rarely look beyond established options.

However, a new wave of challengers is emerging, rethinking data warehousing from the ground up. These newcomers are redefining the stack by bypassing traditional ETL pipelines, pulling data directly from production systems with minimal friction, and even running full-featured data warehouses locally with remarkable ease. Their approach is leaner, faster, and more aligned with modern developer workflows, marking a bold shift in how we think about analytics infrastructure.

The rise of challenger data warehouses has piqued our interest—and we know the data community is just as eager to put them to the test. With this benchmark report, our goal is to equip you with the technical insights and practical tools needed to evaluate these new platforms on your own terms. Whether you're exploring alternatives for speed, cost, flexibility, or developer experience, this report will help you determine which data warehouse aligns best with your needs—and which ones have the potential to lead the next era of data infrastructure.<br><br>

This repo is designed for accessibility, allowing even semi-technical users to easily run benchmarks and extract meaningful insights.<br><br>

If you have any questions about running the benchmark, don’t hesitate to get in touch. We’re here to help.<br><br>

This repository contains Python  code to run and measure SQL queries on the following data warehouses:  

- [**MotherDuck**](MotherDuck/)  
- [**ClickHouse**](ClickHouse/)  
- [**Firebolt**](Firebolt/)  
- [**SingleStore**](SingleStore/)  



For instructions on running Python  code for a specific data warehouse, refer to its respective `README` file.

## **Implementation Details:**

- To ensure accurate performance measurement, the code bypasses cached results from previous queries, guaranteeing a fresh execution each time.
- We initially attempted to extract query execution times from system query history logs, where such metadata was programmatically accessible.
- For data warehouses that did not support programmatic access to query metadata, we measured elapsed time using Python logic.

## **Architecutre:**
<img width="779" alt="image" src="Python code flow.png" />


## **Deployed Environment:**

- The Python code was deployed in a Upcloud Ubutu Server hosted in Sweden. 
- The server had 2 Core, 8 GB of memory, and 10GB of storage.
- We pulled the code from Github, activated a virtual Python environment, and installed only the necessary modules to run the code.
- We ran the code using `tmux` logic and did not modify or alter the code during or after runtime.
- We waited 24 hours to retrieve the cost to run queries.

## **Repository Tree:**
```
.
├── MotherDuck/
│   ├── .env
│   ├── benchmark_queries/
│   ├── main.py
│   ├── queries.py
│   ├── readme.md
│   └── requirements.txt
│
│
├── ClickHouse/
│   ├── .env
│   ├── README.md
│   ├── benchmark_queries/
│   ├── main.py
│   ├── queries.py
│   └── requirements.txt
│
│
├── Firebolt/
│   ├── .env
│   ├── README.md
│   ├── benchmark_queries/
│   ├── main.py
│   ├── queries.py
│   └── requirements.txt
│
│
├── SingleStore/
│   ├── .env
│   ├── README.md
│   ├── benchmark_queries/
│   ├── main.py
│   ├── queries.py
│   └── requirements.txt
└── README.md
```

# **About Estuary**  

* Estuary is one of the fastest and the most reliable realtime streaming and ETL tool in the market
* Estuary has 200+ built-in connectors to cater to almost all popular needs
* Estuary moves 1 petabyte per month while maintaining 99.9% uptime and less than 100 milliseconds of latency

## We have a best in class enterprise grade architecture 


<img width="572" alt="image" src="https://github.com/user-attachments/assets/be04d71c-0cc5-4973-993d-6795bdc44646" />

## Interested in trying out Estuary?

[Get a 30-day credit card free trial here](https://estuary.dev/) 

