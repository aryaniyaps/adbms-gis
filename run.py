import subprocess
import sys
import os

def run_app():
    """Run the Streamlit application"""
    try:
        # Change to the app directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Run streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
    except KeyboardInterrupt:
        print("\nApplication stopped by user")

if __name__ == "__main__":
    run_app()