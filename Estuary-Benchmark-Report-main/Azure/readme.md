To use this project, you need a Microsoft driver. On Ubuntu, follow these steps to deploy the driver:

1. Import the public repository GPG keys:
    ```bash
    curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
    ```

2. Register the Microsoft Ubuntu repository:
    ```bash
    sudo add-apt-repository "$(curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list)"
    ```

3. Update the package list:
    ```bash
    sudo apt-get update
    ```

4. Install the Microsoft ODBC driver:
    ```bash
    sudo apt-get install -y msodbcsql18
    ```

Refer to the [official Microsoft documentation](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) for more details.