import subprocess
import sys
import os

def clean_install():
    """Install only the minimal requirements needed"""
    print("Installing minimal requirements...")
    
    # First uninstall potentially problematic packages
    try:
        subprocess.run([
            sys.executable, 
            "-m", 
            "pip", 
            "uninstall", 
            "-y",
            "numpy",
            "pandas",
            "google-cloud-bigquery"
        ], check=False)
    except Exception as e:
        print(f"Warning during uninstall: {e}")
    
    # Install packages in correct order
    try:
        # First install dotenv
        subprocess.run([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "--no-cache-dir",
            "python-dotenv==1.0.0"
        ], check=True)
        
        # Install BigQuery without pandas
        os.environ["SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL"] = "True"
        subprocess.run([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "--no-cache-dir",
            "google-cloud-bigquery"
        ], check=True)
        
        print("Requirements installed successfully!")
        return True
    except Exception as e:
        print(f"Error during installation: {e}")
        return False

def check_bigquery():
    """Test if we can import just the bigquery library"""
    try:
        from google.cloud import bigquery
        print("✓ Successfully imported google.cloud.bigquery")
        return True
    except ImportError as e:
        print(f"✗ Error importing google.cloud.bigquery: {e}")
        return False

def main():
    print("BigQuery Environment Setup Helper")
    print("=================================")
    
    if check_bigquery():
        print("\nYour environment is set up correctly!")
        print("You can run benchmark queries with:")
        print("  python main.py")
        return
        
    print("\nThe BigQuery library could not be imported correctly.")
    answer = input("Would you like to install the minimal requirements? (y/n): ")
    
    if answer.lower() in ['y', 'yes']:
        if clean_install():
            if check_bigquery():
                print("\nSetup successful! Your environment is now ready.")
                print("You can run benchmark queries with:")
                print("  python main.py")
            else:
                print("\nInstallation succeeded but import still failing.")
                print("Try manually running:")
                print("  pip install --no-deps google-cloud-bigquery")
        else:
            print("\nInstallation failed. Try these manual steps:")
            print("1. pip uninstall numpy pandas google-cloud-bigquery")
            print("2. pip install --no-deps google-cloud-bigquery")
    else:
        print("Setup cancelled. You'll need to install the requirements manually.")

if __name__ == "__main__":
    main() 