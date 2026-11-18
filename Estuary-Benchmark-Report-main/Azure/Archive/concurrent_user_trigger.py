import os
import sys
from dotenv import load_dotenv
from concurrent_user import run_concurrent_users

load_dotenv()

def main():
    try:
        
        num_users_str = os.getenv("NUMBERS_OF_USERS", "5")
        
        try:
            
            if len(sys.argv) > 1:
                num_users = int(sys.argv[1])
            else:
                num_users = int(num_users_str)
        except ValueError:
            print(f"Invalid number of users specified. Using default: {num_users_str}")
            num_users = int(num_users_str)
        
        print(f"Starting benchmark with {num_users} concurrent users")
        
        
        auth_method = os.getenv("AUTH_METHOD", "ServicePrincipal")
        
        
        common_vars = ["AZURE_SYNAPSE_WORKSPACE_URL", "AZURE_SYNAPSE_DATABASE"]
        
        if auth_method.lower() == "sql":
            
            required_vars = common_vars + ["SQL_USERNAME", "SQL_PASSWORD"]
        else:
            
            required_vars = common_vars + ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"Error: The following required environment variables are not set: {', '.join(missing_vars)}")
            print("Please set these variables in the .env file or environment before running.")
            return
        
        
        run_concurrent_users(num_users)
        
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main() 