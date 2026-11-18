import pyodbc
import sys

# Update with your actual Redshift connection details
conn_str = '''Driver={Amazon Redshift (x64)}; 
Server=snowflakequerybenchmark.x.us-east-1.redshift-serverless.amazonaws.com; 
Database=dev;
UID=admin;
PWD=x;
PORT=5439;
'''

conn = None
cursor = None

try:
    # Connect to Redshift
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Create tables
    create_tables_sql = """
    -- Create PART table
    CREATE TABLE IF NOT EXISTS PART (
        P_PARTKEY BIGINT PRIMARY KEY,
        P_NAME VARCHAR(55),
        P_MFGR CHAR(25),
        P_BRAND CHAR(10),
        P_TYPE VARCHAR(25),
        P_SIZE INTEGER,
        P_CONTAINER CHAR(10),
        P_RETAILPRICE DECIMAL(18,2),
        P_COMMENT VARCHAR(23)
    );

    -- Create SUPPLIER table
    CREATE TABLE IF NOT EXISTS SUPPLIER (
        S_SUPPKEY BIGINT PRIMARY KEY,
        S_NAME CHAR(25),
        S_ADDRESS VARCHAR(40),
        S_NATIONKEY BIGINT,
        S_PHONE CHAR(15),
        S_ACCTBAL DECIMAL(18,2),
        S_COMMENT VARCHAR(101)
    );

    -- Create PARTSUPP table
    CREATE TABLE IF NOT EXISTS PARTSUPP (
        PS_PARTKEY BIGINT,
        PS_SUPPKEY BIGINT,
        PS_AVAILQTY INTEGER,
        PS_SUPPLYCOST DECIMAL(18,2),
        PS_COMMENT VARCHAR(199),
        PRIMARY KEY (PS_PARTKEY, PS_SUPPKEY)
    );

    -- Create CUSTOMER table
    CREATE TABLE IF NOT EXISTS CUSTOMER (
        C_CUSTKEY BIGINT PRIMARY KEY,
        C_NAME VARCHAR(25),
        C_ADDRESS VARCHAR(40),
        C_NATIONKEY BIGINT,
        C_PHONE CHAR(15),
        C_ACCTBAL DECIMAL(18,2),
        C_MKTSEGMENT CHAR(10),
        C_COMMENT VARCHAR(117)
    );

    -- Create ORDERS table
    CREATE TABLE IF NOT EXISTS ORDERS (
        O_ORDERKEY BIGINT PRIMARY KEY,
        O_CUSTKEY BIGINT,
        O_ORDERSTATUS CHAR(1),
        O_TOTALPRICE DECIMAL(18,2),
        O_ORDERDATE DATE,
        O_ORDERPRIORITY CHAR(15),
        O_CLERK CHAR(15),
        O_SHIPPRIORITY INTEGER,
        O_COMMENT VARCHAR(79)
    );

    -- Create LINEITEM table
    CREATE TABLE IF NOT EXISTS LINEITEM (
        L_ORDERKEY BIGINT,
        L_PARTKEY BIGINT,
        L_SUPPKEY BIGINT,
        L_LINENUMBER INTEGER,
        L_QUANTITY DECIMAL(18,2),
        L_EXTENDEDPRICE DECIMAL(18,2),
        L_DISCOUNT DECIMAL(18,2),
        L_TAX DECIMAL(18,2),
        L_RETURNFLAG CHAR(1),
        L_LINESTATUS CHAR(1),
        L_SHIPDATE DATE,
        L_COMMITDATE DATE,
        L_RECEIPTDATE DATE,
        L_SHIPINSTRUCT CHAR(25),
        L_SHIPMODE CHAR(10),
        L_COMMENT VARCHAR(44),
        PRIMARY KEY (L_ORDERKEY, L_LINENUMBER)
    );

    -- Create NATION table
    CREATE TABLE IF NOT EXISTS NATION (
        N_NATIONKEY BIGINT PRIMARY KEY,
        N_NAME CHAR(25),
        N_REGIONKEY BIGINT,
        N_COMMENT VARCHAR(152)
    );

    -- Create REGION table
    CREATE TABLE IF NOT EXISTS REGION (
        R_REGIONKEY BIGINT PRIMARY KEY,
        R_NAME CHAR(25),
        R_COMMENT VARCHAR(152)
    );
    """

    # Execute create tables statements
    cursor.execute(create_tables_sql)
    conn.commit()
    print("Tables created successfully.")

except pyodbc.Error as db_err:
    print(f"Database error: {db_err}")
    sys.exit(1)

except Exception as ex:
    print(f"Unexpected error: {ex}")
    sys.exit(1)

finally:
    # Always close the cursor and connection
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    print("Database connection closed.")
