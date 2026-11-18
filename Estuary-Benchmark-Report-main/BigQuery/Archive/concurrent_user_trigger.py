import os
import subprocess
import concurrent.futures
from dotenv import load_dotenv

def run_python_script(user_id):
    print("Starting run_python_script...")
    user_label = f"user-{user_id}"
    
    try:
        print(f"Executing script for {user_label}...")
        result = subprocess.run(
            ["python", "concurrent_user.py", user_label],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Execution for {user_label} completed successfully.\nOutput:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Execution for {user_label} failed: {e}\nOutput:\n{e.output}\nError:\n{e.stderr}")
    finally:
        print("Finished run_python_script...")

def main():
    # Load .env file
    load_dotenv()

    num_users_str = os.getenv("NUMBERS_OF_USERS")
    if not num_users_str:
        print("Error: Environment variable NUMBERS_OF_USERS is not set.")
        print("Please create a .env file with NUMBERS_OF_USERS=N or set the environment variable directly.")
        return

    try:
        num_users = int(num_users_str)
    except ValueError:
        print(f"Error: NUMBERS_OF_USERS must be a valid integer, got '{num_users_str}'")
        return

    # Run scripts concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        print(f"Starting concurrent execution for {num_users} users...")
        futures = [executor.submit(run_python_script, i) for i in range(1, num_users + 1)]
        concurrent.futures.wait(futures)

    print("All iterations completed. Results saved to query_stats_concurrent_users.csv")

if __name__ == "__main__":
    main() 