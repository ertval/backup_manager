from cli.utils import init
from daemon.service import main

if __name__ == "__main__":
    init()
    try:
        main()
    except Exception as e:
        from cli.config import SERVICE_LOG_FILE
        from cli.logger import log
        log(f"Error: daemon unexpected crash: {e}", SERVICE_LOG_FILE)
