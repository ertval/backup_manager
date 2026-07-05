from cli.config import SERVICE_LOG_FILE
from cli.backup import do_backup

def create_backup(path, name):
    do_backup(path, name, log_file=SERVICE_LOG_FILE)
    return True
