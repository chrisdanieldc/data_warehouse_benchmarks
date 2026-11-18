import pyodbc
import random
from datetime import datetime, timedelta
import string

def generate_random_string(length):
    """Generate random string with exact length"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))[:length]

def generate_random_date(start_year=2020, end_year=2023):
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def insert_sample_data(cursor):
    # Insert REGION data
    region_names = ['AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST']
    for i in range(5):
        cursor.execute("""
        INSERT INTO REGION (R_REGIONKEY, R_NAME, R_COMMENT)
        VALUES (?, ?, ?)
        """, (i, region_names[i].ljust(25)[:25], generate_random_string(50)))

    # Insert NATION data
    for i in range(25):
        cursor.execute("""
        INSERT INTO NATION (N_NATIONKEY, N_NAME, N_REGIONKEY, N_COMMENT)
        VALUES (?, ?, ?, ?)
        """, (i, f'Nation_{i}'.ljust(25)[:25], random.randint(0, 4), generate_random_string(50)))

    # Insert SUPPLIER data
    for i in range(400):
        cursor.execute("""
        INSERT INTO SUPPLIER (S_SUPPKEY, S_NAME, S_ADDRESS, S_NATIONKEY, 
                            S_PHONE, S_ACCTBAL, S_COMMENT)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (i, f'Supplier_{i}'.ljust(25)[:25], generate_random_string(40), 
              random.randint(0, 24), f'{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}'[:15],
              random.uniform(1000, 100000), generate_random_string(100)))

    # Insert PART data
    for i in range(400):
        cursor.execute("""
        INSERT INTO PART (P_PARTKEY, P_NAME, P_MFGR, P_BRAND, P_TYPE, 
                         P_SIZE, P_CONTAINER, P_RETAILPRICE, P_COMMENT)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, f'Part_{i}'[:55], f'Manufacturer_{i%10}'.ljust(25)[:25], 
              f'Brand_{i%5}'.ljust(10)[:10], f'Type_{i%3}'[:25],
              random.randint(1, 50), f'CONT_{i%3}'.ljust(10)[:10],
              random.uniform(100, 1000), generate_random_string(23)))

    # Insert PARTSUPP data
    for i in range(400):
        cursor.execute("""
        INSERT INTO PARTSUPP (PS_PARTKEY, PS_SUPPKEY, PS_AVAILQTY, 
                             PS_SUPPLYCOST, PS_COMMENT)
        VALUES (?, ?, ?, ?, ?)
        """, (i % 400, i % 400, random.randint(1, 1000),
              random.uniform(100, 1000), generate_random_string(199)))

    # Insert CUSTOMER data
    for i in range(400):
        cursor.execute("""
        INSERT INTO CUSTOMER (C_CUSTKEY, C_NAME, C_ADDRESS, C_NATIONKEY,
                            C_PHONE, C_ACCTBAL, C_MKTSEGMENT, C_COMMENT)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, f'Customer_{i}'[:25], generate_random_string(40),
              random.randint(0, 24), f'{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}'[:15],
              random.uniform(1000, 100000), f'SEGMENT_{i%5}'.ljust(10)[:10], generate_random_string(117)))

    # Insert ORDERS data
    for i in range(400):
        cursor.execute("""
        INSERT INTO ORDERS (O_ORDERKEY, O_CUSTKEY, O_ORDERSTATUS, O_TOTALPRICE,
                          O_ORDERDATE, O_ORDERPRIORITY, O_CLERK, O_SHIPPRIORITY, O_COMMENT)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, i % 400, random.choice(['O', 'F', 'P']),
              random.uniform(1000, 100000), generate_random_date(),
              f'Priority_{i%3}'.ljust(15)[:15], f'Clerk_{i%10}'.ljust(15)[:15], 
              random.randint(0, 5), generate_random_string(79)))

    # Insert LINEITEM data
    for i in range(400):
        cursor.execute("""
        INSERT INTO LINEITEM (L_ORDERKEY, L_PARTKEY, L_SUPPKEY, L_LINENUMBER,
                            L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT, L_TAX,
                            L_RETURNFLAG, L_LINESTATUS, L_SHIPDATE, L_COMMITDATE,
                            L_RECEIPTDATE, L_SHIPINSTRUCT, L_SHIPMODE, L_COMMENT)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i % 400, i % 400, i % 400, i % 7,
              random.uniform(1, 50), random.uniform(1000, 100000),
              random.uniform(0, 0.1), random.uniform(0, 0.08),
              random.choice(['R', 'A']), random.choice(['O', 'F']),
              generate_random_date(), generate_random_date(),
              generate_random_date(), f'SHIP_INST_{i%5}'.ljust(25)[:25],
              f'MODE_{i%3}'.ljust(10)[:10], generate_random_string(44)))

def main():
    conn_str = '''Driver={Amazon Redshift (x64)}; 
    Server=snowflakequerybenchmark.975050169736.us-east-1.redshift-serverless.amazonaws.com; 
    Database=dev;
    UID=admin;
    PWD=Neel2004;
    PORT=5439;
    '''

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Starting data insertion...")
        insert_sample_data(cursor)
        
        conn.commit()
        print("Sample data inserted successfully!")

    except pyodbc.Error as db_err:
        print(f"Database error: {db_err}")
        if conn:
            conn.rollback()

    except Exception as ex:
        print(f"Unexpected error: {ex}")
        if conn:
            conn.rollback()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()