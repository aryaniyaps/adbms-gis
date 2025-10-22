from setup_db import setup_database
from run import run_app
import sys

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_database()
    else:
        run_app()

if __name__ == "__main__":
    main()
