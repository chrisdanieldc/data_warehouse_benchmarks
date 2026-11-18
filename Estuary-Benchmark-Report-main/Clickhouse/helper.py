import clickhouse_connect
from dotenv import load_dotenv
import os
from queries import queries # Assuming queries is a list of (description, query_string) tuples
import time
import csv

# Load environment variables from .env file
load_dotenv()

# Note: This function is modified to write the query details to a CSV file.
def log_query_details_to_csv(query_description, query, output_file='query_details.csv'):
    """
    Writes the query description and the query string to a CSV file.

    Args:
        query_description (str): A description of the query.
        query (str): The SQL query string to write.
        output_file (str): The name of the CSV file to write to.
    """
    # Prepare data to append
    query_details = {
            'query_description': query_description,
            'query_string': query
        }

    # Check if the file exists
    file_exists = os.path.isfile(output_file)

    # Open the CSV file in append mode and write the data
    # Use 'utf-8' encoding to handle potential special characters in queries
    with open(output_file, mode='a', newline='', encoding='utf-8') as file:
        fieldnames = ['query_description', 'query_string']

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # If the file doesn't exist, write the header row
        if not file_exists:
            writer.writeheader()

        # Write the query details to the CSV
        writer.writerow(query_details)

    print(f"Logged details for '{query_description}' to {output_file}")


def main():
    # Retrieve values from .env (still loaded, but not used for writing to CSV)
    database = os.getenv("DATABASE") # Not used for CSV logging
    host = os.getenv("HOST") # Not used for CSV logging
    port = os.getenv("PORT") # Not used for CSV logging
    user = os.getenv("CLICKHOUSE_USER") # Not used for CSV logging
    password = os.getenv("PASSWORD") # Not used for CSV logging
    warehouse = os.getenv("WAREHOUSE") # Not used for CSV logging

    # Connection establishment is removed as we are only logging queries to CSV
    # client = clickhouse_connect.get_client(
    #         host=host,
    #         port=int(port),
    #         user=user,
    #         password=password,
    #         secure=True
    #     )

    try:
        # Loop through the queries and log them to CSV
        for query_description, query in queries:
            log_query_details_to_csv(query_description, query)

    except Exception as e:
        # Keep error handling in case something goes wrong during iteration or file writing
        print(f"\nError processing query or writing to CSV: {e}\n")

    finally:
        # Connection closing is removed as no connection is established
        # client.close()
        print("\nScript finished (queries were logged to CSV).")


if __name__ == "__main__":
    main()
